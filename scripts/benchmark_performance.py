#!/usr/bin/env python3
"""Reproducible Linux measurements of actual StudyTracker servers, using only temporary data.

The benchmark observes process CPU ticks, RSS and per-thread context-switch
counts via /proc. Context switches are a proxy, not hardware CPU wakeups.
Python instrumentation counts selected filesystem operations, not all syscalls.
No hardware power, temperature or battery readings are inferred.
"""
from __future__ import annotations
import argparse
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from unittest import mock
import urllib.request
from http.cookiejar import CookieJar
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
USERNAME, PASSWORD = "benchmark", "temporary-benchmark-password"


def load_server(directory, name, data):
    spec = importlib.util.spec_from_file_location(name, directory / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DATA_DIR = data / "data"
    module.BACKUP_DIR = data / "backups"
    return module


def seed(module, tasks, sessions):
    user = module.create_user({"username": USERNAME, "display_name": "Benchmark", "password": PASSWORD}, first=True)
    state = module.load_profile(user["id"])
    now = datetime.now(timezone.utc)
    for i in range(tasks):
        state["tasks"].append({"id": f"task-{i}", "subject_id": "mathe", "title": f"Synthetic task {i}", "description": "",
          "status": "todo", "priority": "normal", "planned_minutes": 45, "planned_for": None, "due_date": None,
          "tags": [], "parent_id": None, "created_at": now.isoformat(), "updated_at": now.isoformat(), "completed_at": None,
          "exercise_review": None, "exercise_review_gpt": None, "next_action": "", "resume_note": ""})
    for i in range(sessions):
        start = now - timedelta(hours=2*i+1)
        end = start + timedelta(minutes=30)
        state["sessions"].append({"id": f"session-{i}", "subject_id":"mathe", "task_id":f"task-{i%tasks}" if tasks else None,
          "title":"Synthetic session", "notes":"", "tags":[], "category_tag_id":None, "started_at":start.isoformat(),
          "ended_at":end.isoformat(), "duration_seconds":1800, "break_seconds":0, "breaks":[],
          "focus_intervals":[{"started_at":start.isoformat(),"ended_at":end.isoformat()}]})
    module.atomic(module.profile_path(user["id"]), state)
    return user


def counts(pid):
    base = Path("/proc") / str(pid)
    fields = (base/"stat").read_text().rsplit(")",1)[1].split()
    cpu = (int(fields[11])+int(fields[12]))/os.sysconf("SC_CLK_TCK")
    status = (base/"status").read_text().splitlines()
    rss = int(next(l.split()[1] for l in status if l.startswith("VmRSS:")))
    switches = 0
    for task in (base/"task").iterdir():
        try:
            switches += sum(int(l.split()[1]) for l in (task/"status").read_text().splitlines()
                            if l.startswith(("voluntary_ctxt_switches:", "nonvoluntary_ctxt_switches:")))
        except FileNotFoundError:
            pass
    return cpu, rss, switches


def delta(a,b,elapsed):
    return {"seconds":round(elapsed,3),"cpu_ms":round(1000*(b[0]-a[0]),2),
        "average_cpu_percent_one_core":round(100*(b[0]-a[0])/max(elapsed,.001),3),
        "rss_kib":b[1],"context_switch_delta":b[2]-a[2]}


def filesystem_microbenchmark(module):
    # Warm directory and account cache; count selected Python Path calls on
    # exactly the same 100 empty-inbox scans, independent of scheduled cadence.
    module.ingest_inbox_once()
    names=("stat","open","mkdir","glob","read_text")
    calls={name:0 for name in names}
    originals={name:getattr(Path,name) for name in names}
    def wrap(name):
        def count(self,*args,**kwargs):
            calls[name]+=1
            return originals[name](self,*args,**kwargs)
        return count
    with contextlib.ExitStack() as stack:
        for name in names:
            stack.enter_context(mock.patch.object(Path,name,wrap(name)))
        before=time.process_time()
        for _ in range(100):
            module.ingest_inbox_once()
        elapsed=(time.process_time()-before)*1000
    return {"scans":100,"selected_path_calls":calls,"process_cpu_ms":round(elapsed,2)}


def server_bench(directory, label, args):
    with tempfile.TemporaryDirectory(prefix="studytracker-perf-") as temp:
        root=Path(temp)
        module=load_server(directory,"bench_"+label,root)
        user=seed(module,args.tasks,args.sessions)
        fs=filesystem_microbenchmark(module)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1",0))
            port=probe.getsockname()[1]
        env={**os.environ,"STUDYTRACKER_DATA_DIR":str(module.DATA_DIR),"STUDYTRACKER_BACKUP_DIR":str(module.BACKUP_DIR),
             "STUDYTRACKER_INBOX_IDLE_SECONDS":"30","PYTHONUNBUFFERED":"1"}
        log=(root/"server.log").open("w+")
        proc=subprocess.Popen([sys.executable,str(directory/"server.py"),"--no-browser","--port",str(port)],cwd=directory,env=env,stdout=log,stderr=log)
        client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        url=f"http://127.0.0.1:{port}"
        def request(endpoint,body=None):
            req=urllib.request.Request(url+endpoint,data=json.dumps(body).encode() if body is not None else None,
               headers={"Content-Type":"application/json"} if body is not None else {})
            with client.open(req,timeout=5) as response:
                return response.read()
        try:
            for _ in range(100):
                try:
                    request("/api/auth/status")
                    break
                except OSError:
                    if proc.poll() is not None: raise RuntimeError("Server exited prematurely")
                    time.sleep(.1)
            else: raise RuntimeError("Server did not start")
            # No browser, no requests during this timed section.
            before=counts(proc.pid);start=time.monotonic()
            time.sleep(args.seconds)
            idle=delta(before,counts(proc.pid),time.monotonic()-start)
            # Authenticate outside the measured request burst.
            request("/api/auth/login",{"username":USERNAME,"password":PASSWORD})
            first=json.loads(request("/api/state"))
            before=counts(proc.pid);start=time.monotonic();size=0
            for _ in range(args.requests):
                response=request("/api/profile/revision")
                size+=len(response)
            revision=delta(before,counts(proc.pid),time.monotonic()-start)
            revision.update(requests=args.requests,response_bytes=size)
            # Simulate a sync client writing a fresh file. Wait for actual
            # processing; this includes intentional quiet/stability latency.
            inbox=module.DATA_DIR/"inbox"/USERNAME
            inbox.mkdir(parents=True,exist_ok=True)
            incoming=inbox/"benchmark-import.json"
            incoming.write_text(json.dumps({"format":"studytracker.tasks.v1","batch_id":"benchmark-source",
             "tasks":[{"external_id":"benchmark-source:a","subject_id":"mathe","title":"Benchmark import"}]}),"utf-8")
            start=time.monotonic()
            while incoming.exists() and time.monotonic()-start<45:
                time.sleep(.25)
            after=json.loads(request("/api/state"))
            imported=any(t.get("external_id")=="benchmark-source:a" for t in after["state"]["tasks"])
            latency=round(time.monotonic()-start,2)
            if not imported: raise RuntimeError("Inbox import did not complete within 45s")
            print("BACKEND_BENCHMARK "+json.dumps({"version":label,"tasks":args.tasks,"sessions":args.sessions,
              "idle_no_browser":idle,"revision_burst":revision,"profile_response_bytes":len(json.dumps(first,ensure_ascii=False).encode()),
              "filesystem_microbenchmark":fs,"inbox_import_seconds_including_verification":latency,"imported":imported}),flush=True)
        finally:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill();proc.wait()
            log.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline",type=Path,help="Clean checkout of the pre-optimization commit")
    parser.add_argument("--seconds",type=float,default=35,help="Idle server measurement duration per version (use >=35 for normal measurements)")
    parser.add_argument("--requests",type=int,default=100,help="Real HTTP revision requests per burst")
    parser.add_argument("--tasks",type=int,default=1000)
    parser.add_argument("--sessions",type=int,default=5000)
    args=parser.parse_args()
    if not Path("/proc/self/stat").exists(): parser.error("This benchmark requires Linux /proc")
    if args.seconds<1 or args.requests<1 or args.tasks<1 or args.sessions<0: parser.error("Invalid workload")
    for directory,label in [(args.baseline.resolve(),"before"),(ROOT,"after")]:
        server_bench(directory,label,args)

if __name__=="__main__":
    main()
