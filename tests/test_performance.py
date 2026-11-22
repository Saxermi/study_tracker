"""Energy-related regression tests using temporary files only."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(server, "DATA_DIR", root / "data").start()
        mock.patch.object(server, "BACKUP_DIR", root / "backups").start()
        self.user = {"id":"a"*32, "username":"bench", "display_name":"Bench", "role":"admin"}
        server.atomic(server.accounts_path(), {"version":2, "users":[self.user]})
        server.atomic(server.profile_path(self.user["id"]), server.blank_profile())

    def test_account_cache_reads_once_and_detects_same_mtime_replacement(self):
        original = server.accounts_path().stat()
        with mock.patch.object(server.json, "load", wraps=json.load) as loader:
            data = server.accounts()
            data["users"].clear()
            self.assertEqual(len(server.accounts()["users"]), 1)
            self.assertEqual(loader.call_count, 1)
            server.atomic(server.accounts_path(), {"version":2,"users":[{**self.user,"display_name":"Other"}]})
            os.utime(server.accounts_path(), ns=(original.st_atime_ns,original.st_mtime_ns))
            self.assertEqual(server.accounts()["users"][0]["display_name"],"Other")
            self.assertEqual(loader.call_count, 2)
            server.accounts_path().unlink()
            self.assertEqual(server.accounts()["users"],[])

    def test_revision_detects_external_profile_replace_with_preserved_mtime(self):
        p=server.profile_path(self.user["id"])
        original=p.stat()
        rev=server.profile_revision(self.user["id"])
        state=server.load_profile(self.user["id"])
        state["settings"]["weekly_goal_minutes"]=42
        server.atomic(p,state)
        os.utime(p,ns=(original.st_atime_ns,original.st_mtime_ns))
        self.assertNotEqual(server.profile_revision(self.user["id"]),rev)
        data,newrev=server.profile_snapshot(self.user["id"])
        self.assertEqual(data["settings"]["weekly_goal_minutes"],42)
        self.assertEqual(newrev,server.profile_revision(self.user["id"]))

    def test_adaptive_inbox_backoff_uses_fast_scan_for_pending_files(self):
        waits=[]
        class Stop:
            def wait(self,delay):
                waits.append(delay)
                return len(waits)==5
        def scan(activity):
            activity["pending"]=len(waits)==2
            return [{"file":"new.json"}] if len(waits)==3 else []
        with mock.patch.object(server,"ingest_inbox_once",side_effect=scan):
            server.background_import(Stop(),idle_seconds=30)
        self.assertEqual(waits,[4,30,4,4,30])

    def test_inbox_stability_and_duplicates_do_not_rewrite_profile(self):
        inbox=server.DATA_DIR/"inbox"/"bench"
        inbox.mkdir(parents=True)
        path=inbox/"tasks.json"
        payload={"format":"studytracker.tasks.v1","batch_id":"source-1","tasks":[{"external_id":"source-1:a","subject_id":"mathe","title":"Read"}]}
        path.write_text(json.dumps(payload),"utf-8")
        activity={}
        self.assertEqual(server.ingest_inbox_once(activity),[])
        self.assertTrue(activity["pending"])
        old=time.time()-10
        os.utime(path,(old,old))
        outcome=server.ingest_inbox_once(activity)
        self.assertEqual(outcome[0]["added"],1)
        self.assertTrue(list((inbox/"processed").glob("*.json")))
        before=server.profile_revision(self.user["id"])
        path.write_text(json.dumps(payload),"utf-8")
        os.utime(path,(old,old))
        with mock.patch.object(server,"save_profile",wraps=server.save_profile) as save:
            self.assertTrue(server.ingest_inbox_once()[0]["already_imported"])
            self.assertTrue(server.mutate(self.user["id"],"POST","/api/import/tasks",payload)["already_imported"])
            self.assertEqual(save.call_count,0)
        self.assertEqual(server.profile_revision(self.user["id"]),before)
        self.assertEqual(len(server.load_profile(self.user["id"])["tasks"]),1)
