#!/usr/bin/env python3
"""StudyTracker 2 — local, dependency-free study tracker with per-user files.

Never expose this service on the public network: binds only to 127.0.0.1.
Polybox is file sync, NOT a multi-writer database: use one running computer at a time.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import shutil
import tempfile
import threading
import time
import uuid
import webbrowser
from datetime import date, datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("STUDYTRACKER_DATA_DIR", ROOT / "data")).expanduser().resolve()
BACKUP_DIR = Path(os.environ.get("STUDYTRACKER_BACKUP_DIR", Path.home() / ".local/share/studytracker/backups")).expanduser().resolve()
STATIC = ROOT / "static"
LOCK = threading.RLock()
SESSIONS: dict[str, str] = {}  # ephemeral browser session -> user id
MAX_REQUEST = 8 * 1024 * 1024
ITERATIONS = 450_000
COLORS = ["#7065EF", "#1AA59A", "#F4A35D", "#488FDD", "#CE6A98", "#9A78D5"]
VALID_STATES = {"todo", "doing", "done"}
PRIORITIES = {"low", "normal", "high"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso() -> str:
    return now().isoformat(timespec="seconds")


def uid() -> str:
    return uuid.uuid4().hex


def err(msg: str, status: int = 400):
    raise ClientError(msg, status)


class ClientError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.message, self.status = message, status
        super().__init__(message)


def txt(value, label="Text", limit=180, required=False) -> str:
    if not isinstance(value, str):
        err(f"{label} muss Text sein.")
    value = value.strip()
    if len(value) > limit or (required and not value):
        err(f"{label}: bitte 1 bis {limit} Zeichen verwenden.")
    return value


def number(value, label="Zahl", lo=0, hi=100000) -> int:
    if isinstance(value, bool):
        err(f"{label} ist ungültig.")
    try:
        x = int(value)
        if float(value) != x or not lo <= x <= hi:
            raise ValueError()
        return x
    except (TypeError, ValueError, OverflowError):
        err(f"{label} muss eine ganze Zahl zwischen {lo} und {hi} sein.")


def check_color(v):
    if not isinstance(v, str) or not re.fullmatch(r"#[a-fA-F0-9]{6}", v):
        err("Ungültige Farbe.")
    return v.upper()


def timestamp(v):
    try:
        if not isinstance(v, str):
            raise ValueError()
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if d.tzinfo is None:
            raise ValueError()
        return d.astimezone(timezone.utc)
    except ValueError:
        err("Datum benötigt ISO-8601 mit Zeitzone.")


def due(v):
    if v is None or v == "":
        return None
    if not isinstance(v, str):
        err("Fälligkeit muss YYYY-MM-DD sein.")
    try:
        d = date.fromisoformat(v)
        if d.isoformat() != v:
            raise ValueError()
    except ValueError:
        err("Fälligkeit muss YYYY-MM-DD sein.")
    return v


def atomic(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".write-", delete=False) as fp:
            tmp = Path(fp.name)
            fp.write(raw)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(tmp, path)
    finally:
        if tmp and tmp.exists():
            tmp.unlink()


def read_json(path: Path, default):
    return json.loads(path.read_text("utf-8")) if path.exists() else copy.deepcopy(default)


def accounts_path():
    return DATA_DIR / "accounts.json"


def profile_path(user_id: str):
    if not re.fullmatch(r"[0-9a-f]{32}", user_id):
        err("Ungültige Profil-ID.")
    return DATA_DIR / "profiles" / (user_id + ".json")


def accounts():
    data = read_json(accounts_path(), {"version": 2, "users": []})
    if data.get("version") != 2:
        err("Unbekanntes Kontoformat.", 500)
    return data


def blank_profile():
    return {"version": 2, "subjects": [
        {"id": "mathe", "name": "Mathematik", "color": COLORS[0], "weekly_goal_minutes": 300, "archived": False},
        {"id": "info", "name": "Informatik", "color": COLORS[1], "weekly_goal_minutes": 240, "archived": False},
        {"id": "physik", "name": "Physik", "color": COLORS[2], "weekly_goal_minutes": 180, "archived": False},
    ], "tags": [
        {"id": "uebungen", "name": "Übungen", "color": COLORS[0]},
        {"id": "lesen", "name": "Neuer Stoff", "color": COLORS[1]},
        {"id": "wiederholen", "name": "Wiederholung", "color": COLORS[2]},
        {"id": "pruefung", "name": "Prüfung", "color": COLORS[4]},
    ], "tasks": [], "sessions": [], "active_timer": None, "settings": {"weekly_goal_minutes": 900}, "imports": []}


def migrate_v1_if_needed() -> dict:
    """Adopt a StudyTracker v1 data/state.json on initial account setup only."""
    profile = blank_profile()
    legacy_path = DATA_DIR / "state.json"
    if not legacy_path.exists():
        return profile
    legacy = read_json(legacy_path, {})
    if legacy.get("version") != 1:
        return profile
    profile.update({"subjects": legacy.get("subjects", profile["subjects"]), "tags": legacy.get("tags", profile["tags"]),
                    "sessions": legacy.get("sessions", []), "settings": legacy.get("settings", profile["settings"])})
    for s in profile["sessions"]:
        s.setdefault("task_id", None)
        s.setdefault("break_seconds", 0)
        s.setdefault("breaks", [])
    # Never restore potentially stale live timers.
    archive = DATA_DIR / "legacy-state-v1.json"
    if not archive.exists():
        shutil.copy2(legacy_path, archive)
    return profile


def load_profile(user_id: str):
    p = profile_path(user_id)
    if not p.exists():
        err("Profil nicht gefunden.", 404)
    data = read_json(p, {})
    if data.get("version") != 2:
        err("Profilformat nicht unterstützt.", 500)
    return data


def save_profile(user_id: str, state):
    p = profile_path(user_id)
    if p.exists():
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            backup = BACKUP_DIR / f"{user_id}-{now().date().isoformat()}.json"
            if not backup.exists():
                shutil.copy2(p, backup)
            old = sorted(BACKUP_DIR.glob(f"{user_id}-????-??-??.json"))
            for item in old[:-30]:
                item.unlink(missing_ok=True)
        except OSError as e:
            print(f"WARNUNG: Backup fehlgeschlagen: {e}")
    atomic(p, state)


def hash_password(password: str, salt: bytes | None = None):
    if salt is None:
        salt = secrets.token_bytes(24)
    return salt.hex(), hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS).hex()


def validate_password(password):
    if not isinstance(password, str) or len(password) < 10 or len(password) > 150:
        err("Passwort: mindestens 10 und höchstens 150 Zeichen.")
    return password


def create_user(body, first=False):
    with LOCK:
        a = accounts()
        if first != (len(a["users"]) == 0):
            err("Kontenerstellung hier nicht erlaubt.", 403)
        name = txt(body.get("display_name", ""), "Anzeigename", 60, True)
        username = txt(body.get("username", ""), "Benutzername", 24, True).lower()
        if not re.fullmatch(r"[a-z][a-z0-9_-]{2,23}", username):
            err("Benutzername: 3–24 Zeichen, Kleinbuchstaben, Zahlen, _ oder -.")
        if any(u["username"] == username for u in a["users"]):
            err("Benutzername bereits vergeben.")
        salt, digest = hash_password(validate_password(body.get("password")))
        user_id = uid()
        record = {"id": user_id, "username": username, "display_name": name, "role": "admin" if first else "user",
                  "salt": salt, "password_hash": digest, "iterations": ITERATIONS, "created_at": iso()}
        # Write the profile first so failed account creation cannot reference a missing file.
        atomic(profile_path(user_id), migrate_v1_if_needed() if first else blank_profile())
        a["users"].append(record)
        atomic(accounts_path(), a)
        return public_user(record)


def public_user(u):
    return {k: u[k] for k in ("id", "username", "display_name", "role")}


def sign_in(username, password):
    if not isinstance(username, str) or not isinstance(password, str):
        err("Benutzername oder Passwort falsch.", 401)
    a = accounts()
    u = next((u for u in a["users"] if u["username"] == username.strip().lower()), None)
    if u is None:
        # Timing padding for nonexistent accounts; no password hash leaks.
        hashlib.pbkdf2_hmac("sha256", b"invalid", b"0" * 24, ITERATIONS)
        err("Benutzername oder Passwort falsch.", 401)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(u["salt"]), int(u.get("iterations", ITERATIONS)))
    if not hmac.compare_digest(digest, bytes.fromhex(u["password_hash"])):
        err("Benutzername oder Passwort falsch.", 401)
    token = secrets.token_urlsafe(36)
    with LOCK:
        SESSIONS[token] = u["id"]
    return public_user(u), token


def account_by_id(user_id):
    return next((u for u in accounts()["users"] if u["id"] == user_id), None)


def subject(state, sid):
    x = next((s for s in state["subjects"] if s["id"] == sid), None)
    if not x:
        err("Fach unbekannt.", 404)
    return x


def task(state, tid):
    x = next((s for s in state["tasks"] if s["id"] == tid), None)
    if not x:
        err("Aufgabe unbekannt.", 404)
    return x


def session(state, sid):
    x = next((s for s in state["sessions"] if s["id"] == sid), None)
    if not x:
        err("Lerneinheit unbekannt.", 404)
    return x


def valid_tags(state, values):
    if not isinstance(values, list) or len(values) > 30:
        err("Tags müssen eine Liste mit höchstens 30 Einträgen sein.")
    known = {t["id"] for t in state["tags"]}
    if any(not isinstance(v, str) or v not in known for v in values):
        err("Unbekannter Tag.")
    return list(dict.fromkeys(values))


def task_fields(state, body, existing=None):
    sid = txt(body.get("subject_id", existing["subject_id"] if existing else ""), "Fach-ID", 80, True)
    subject(state, sid)
    planned = number(body.get("planned_minutes", existing["planned_minutes"] if existing else 60), "Schätzung (Minuten)", 1, 100000)
    status = body.get("status", existing["status"] if existing else "todo")
    priority = body.get("priority", existing["priority"] if existing else "normal")
    if status not in VALID_STATES or priority not in PRIORITIES:
        err("Status oder Priorität ungültig.")
    fields = {"title": txt(body.get("title", existing["title"] if existing else ""), "Aufgabentitel", 180, True),
              "description": txt(body.get("description", existing["description"] if existing else ""), "Beschreibung", 3000),
              "subject_id": sid, "planned_minutes": planned, "status": status, "priority": priority,
              "due_date": due(body.get("due_date", existing["due_date"] if existing else None)),
              "tags": valid_tags(state, body.get("tags", existing["tags"] if existing else []))}
    if existing and status != existing["status"]:
        fields["completed_at"] = iso() if status == "done" else None
    return fields


def session_fields(state, body, existing=None):
    sid = txt(body.get("subject_id", existing["subject_id"] if existing else ""), "Fach-ID", 80, True)
    subject(state, sid)
    task_id = body.get("task_id", existing.get("task_id") if existing else None) or None
    if task_id is not None and task(state, task_id)["subject_id"] != sid:
        err("Aufgabe und Fach stimmen nicht überein.")
    start = timestamp(body.get("started_at", existing["started_at"] if existing else None))
    duration = number(body.get("duration_seconds", existing["duration_seconds"] if existing else None), "Lernzeit (Sekunden)", 1, 86400)
    if start > now() + timedelta(days=1):
        err("Startdatum zu weit in der Zukunft.")
    return {"subject_id": sid, "task_id": task_id,
            "title": txt(body.get("title", existing.get("title", "") if existing else ""), "Beschreibung", 180),
            "notes": txt(body.get("notes", existing.get("notes", "") if existing else ""), "Notizen", 3000),
            "tags": valid_tags(state, body.get("tags", existing["tags"] if existing else [])),
            "started_at": start.isoformat(timespec="seconds"), "ended_at": (start + timedelta(seconds=duration)).isoformat(timespec="seconds"),
            "duration_seconds": duration,
            # Edits intentionally retain original break records, and cannot change them.
            "break_seconds": existing.get("break_seconds", 0) if existing else 0,
            "breaks": existing.get("breaks", []) if existing else []}


def active_seconds(t, mode):
    base = t["focus_seconds"] if mode == "focus" else t["break_seconds"]
    if t["mode"] == mode and t["mode_since"]:
        base += max(0, int((now() - timestamp(t["mode_since"])).total_seconds()))
    return base


def timer_switch(t, to_mode):
    old_mode = t["mode"]
    moment = now()
    if old_mode == "focus":
        t["focus_seconds"] = active_seconds(t, "focus")
    if old_mode == "break":
        t["break_seconds"] = active_seconds(t, "break")
        begun = timestamp(t["mode_since"])
        t["breaks"].append({"started_at": begun.isoformat(timespec="seconds"),
                            "ended_at": moment.isoformat(timespec="seconds"),
                            "duration_seconds": max(0, int((moment - begun).total_seconds()))})
    t["mode"] = to_mode
    t["mode_since"] = moment.isoformat(timespec="seconds") if to_mode != "paused" else None


def safe_batch_key(v):
    return txt(v, "Batch-ID", 100, True)


def add_agent_tasks(state, payload):
    """Validated, idempotent per-profile import of a simple task envelope."""
    if not isinstance(payload, dict) or payload.get("format") != "studytracker.tasks.v1":
        err("Erwartet format: studytracker.tasks.v1.")
    batch_id = safe_batch_key(payload.get("batch_id"))
    items = payload.get("tasks")
    if not isinstance(items, list) or not 1 <= len(items) <= 150:
        err("Eine Importdatei braucht 1 bis 150 Aufgaben.")
    if any(i.get("batch_id") == batch_id for i in state["imports"]):
        return {"added": 0, "skipped": len(items), "batch_id": batch_id, "already_imported": True}
    staged = copy.deepcopy(state)
    known_external = {t.get("external_id") for t in staged["tasks"] if t.get("external_id")}
    added, skipped = 0, 0
    for item in items:
        if not isinstance(item, dict):
            err("Jede Aufgabe muss ein JSON-Objekt sein.")
        ext = txt(item.get("external_id", ""), "Externe Aufgaben-ID", 160, True)
        if ext in known_external:
            skipped += 1
            continue
        # Prefer exact existing subject names. Otherwise create a new subject.
        subject_name = txt(item.get("subject", ""), "Fach", 60, True)
        s = next((s for s in staged["subjects"] if s["name"].casefold() == subject_name.casefold()), None)
        if not s:
            s = {"id": uid(), "name": subject_name, "color": COLORS[len(staged["subjects"]) % len(COLORS)],
                 "weekly_goal_minutes": 0, "archived": False}
            staged["subjects"].append(s)
        tag_ids = []
        incoming_tags = item.get("tags", [])
        if not isinstance(incoming_tags, list) or len(incoming_tags) > 12:
            err("Pro Aufgabe höchstens 12 Tags.")
        for name in incoming_tags:
            name = txt(name, "Tag", 50, True)
            tg = next((t for t in staged["tags"] if t["name"].casefold() == name.casefold()), None)
            if not tg:
                tg = {"id": uid(), "name": name, "color": COLORS[len(staged["tags"]) % len(COLORS)]}
                staged["tags"].append(tg)
            if tg["id"] not in tag_ids:
                tag_ids.append(tg["id"])
        # Validate fields before committing; status always starts at todo for safe ingestion.
        row = task_fields(staged, {"subject_id": s["id"], "title": item.get("title", ""),
                                   "description": item.get("description", ""), "planned_minutes": item.get("planned_minutes", 60),
                                   "status": "todo", "priority": item.get("priority", "normal"),
                                   "due_date": item.get("due_date"), "tags": tag_ids})
        staged["tasks"].append({"id": uid(), **row, "external_id": ext,
                                "created_at": iso(), "updated_at": iso(), "completed_at": None})
        known_external.add(ext)
        added += 1
    staged["imports"].append({"batch_id": batch_id, "at": iso(), "added": added, "skipped": skipped})
    state.clear()
    state.update(staged)
    return {"added": added, "skipped": skipped, "batch_id": batch_id, "already_imported": False}


def mutate(user_id, method, path, body):
    with LOCK:
        s = load_profile(user_id)
        parts = path.strip("/").split("/")
        message = {}
        if path == "/api/subjects" and method == "POST":
            name = txt(body.get("name", ""), "Fach", 60, True)
            if any(x["name"].casefold() == name.casefold() for x in s["subjects"]):
                err("Fach existiert bereits.")
            s["subjects"].append({"id": uid(), "name": name, "color": check_color(body.get("color", COLORS[0])),
                                  "weekly_goal_minutes": number(body.get("weekly_goal_minutes", 0), "Fachziel", 0, 10080), "archived": False})
        elif len(parts) == 3 and parts[1] == "subjects" and method == "PATCH":
            sub = subject(s, parts[2])
            if "name" in body:
                sub["name"] = txt(body["name"], "Fach", 60, True)
            if "color" in body:
                sub["color"] = check_color(body["color"])
            if "weekly_goal_minutes" in body:
                sub["weekly_goal_minutes"] = number(body["weekly_goal_minutes"], "Fachziel", 0, 10080)
            if "archived" in body:
                if not isinstance(body["archived"], bool):
                    err("Archivierungswert ungültig.")
                sub["archived"] = body["archived"]
        elif path == "/api/tags" and method == "POST":
            name = txt(body.get("name", ""), "Tag", 50, True)
            if any(t["name"].casefold() == name.casefold() for t in s["tags"]):
                err("Tag existiert bereits.")
            s["tags"].append({"id": uid(), "name": name, "color": check_color(body.get("color", COLORS[0]))})
        elif len(parts) == 3 and parts[1] == "tags" and method == "DELETE":
            tid = parts[2]
            if tid not in {t["id"] for t in s["tags"]}:
                err("Tag nicht gefunden.", 404)
            s["tags"] = [t for t in s["tags"] if t["id"] != tid]
            for taskrow in s["tasks"]:
                taskrow["tags"] = [x for x in taskrow["tags"] if x != tid]
            for sr in s["sessions"]:
                sr["tags"] = [x for x in sr["tags"] if x != tid]
        elif path == "/api/settings" and method == "PATCH":
            s["settings"]["weekly_goal_minutes"] = number(body.get("weekly_goal_minutes"), "Wochenziel", 0, 10080)
        elif path == "/api/tasks" and method == "POST":
            taskrow = {"id": uid(), **task_fields(s, body), "external_id": None, "created_at": iso(), "updated_at": iso(), "completed_at": None}
            if taskrow["status"] == "done":
                taskrow["completed_at"] = iso()
            s["tasks"].append(taskrow)
            message["task_id"] = taskrow["id"]
        elif len(parts) == 3 and parts[1] == "tasks" and method == "PATCH":
            row = task(s, parts[2])
            fields = task_fields(s, body, row)
            if fields["subject_id"] != row["subject_id"] and (
                (s["active_timer"] and s["active_timer"].get("task_id") == row["id"]) or
                any(entry.get("task_id") == row["id"] for entry in s["sessions"])
            ):
                err("Fach einer Aufgabe mit erfasster Lernzeit kann nicht geändert werden.")
            row.update(fields)
            row["updated_at"] = iso()
        elif len(parts) == 3 and parts[1] == "tasks" and method == "DELETE":
            row = task(s, parts[2])
            if s["active_timer"] and s["active_timer"].get("task_id") == row["id"]:
                err("Aufgabe hat einen aktiven Timer.")
            # Historical sessions remain retained and detached for analytics.
            for sr in s["sessions"]:
                if sr.get("task_id") == row["id"]:
                    sr["task_id"] = None
            s["tasks"] = [t for t in s["tasks"] if t["id"] != row["id"]]
        elif path == "/api/timer/start" and method == "POST":
            if s["active_timer"]:
                err("Ein Timer läuft bereits.")
            tid = body.get("task_id") or None
            t = task(s, tid) if tid else None
            if t and t["status"] == "done":
                err("Abgeschlossene Aufgabe zuerst wieder öffnen.")
            sid = t["subject_id"] if t else txt(body.get("subject_id", ""), "Fach-ID", 80, True)
            if subject(s, sid)["archived"]:
                err("Archiviertes Fach.")
            if t and t["status"] == "todo":
                t["status"], t["updated_at"] = "doing", iso()
            s["active_timer"] = {"subject_id": sid, "task_id": tid, "title": t["title"] if t else txt(body.get("title", ""), "Beschreibung", 180),
                                 "tags": list(t["tags"]) if t else valid_tags(s, body.get("tags", [])), "notes": "",
                                 "first_started_at": iso(), "mode_since": iso(), "mode": "focus",
                                 "focus_seconds": 0, "break_seconds": 0, "breaks": []}
        elif path in ("/api/timer/pause", "/api/timer/resume", "/api/timer/break-start", "/api/timer/break-end") and method == "POST":
            t = s.get("active_timer")
            if not t:
                err("Kein aktiver Timer.")
            required, target = {
                "/api/timer/pause": ("focus", "paused"), "/api/timer/resume": ("paused", "focus"),
                "/api/timer/break-start": ("focus", "break"), "/api/timer/break-end": ("break", "focus")
            }[path]
            if t["mode"] != required:
                err("Timer ist nicht im richtigen Modus.")
            timer_switch(t, target)
        elif path == "/api/timer/stop" and method == "POST":
            t = s.get("active_timer")
            if not t:
                err("Kein aktiver Timer.")
            if t["mode"] in ("focus", "break"):
                timer_switch(t, "paused")
            if t["focus_seconds"] < 1:
                err("Mindestens eine Sekunde Fokuszeit nötig.")
            begun = timestamp(t["first_started_at"])
            s["sessions"].append({"id": uid(), "subject_id": t["subject_id"], "task_id": t["task_id"],
                                  "title": t["title"], "notes": t.get("notes", ""), "tags": t["tags"],
                                  "started_at": begun.isoformat(timespec="seconds"), "ended_at": iso(),
                                  "duration_seconds": t["focus_seconds"], "break_seconds": t["break_seconds"], "breaks": t["breaks"],
                                  "source": "timer", "created_at": iso()})
            s["active_timer"] = None
        elif path == "/api/timer/discard" and method == "POST":
            if not s["active_timer"]:
                err("Kein Timer aktiv.")
            s["active_timer"] = None
        elif path == "/api/sessions" and method == "POST":
            s["sessions"].append({"id": uid(), **session_fields(s, body), "source": "manual", "created_at": iso()})
        elif len(parts) == 3 and parts[1] == "sessions" and method == "PATCH":
            row = session(s, parts[2])
            row.update(session_fields(s, body, row))
        elif len(parts) == 3 and parts[1] == "sessions" and method == "DELETE":
            session(s, parts[2])
            s["sessions"] = [x for x in s["sessions"] if x["id"] != parts[2]]
        elif path == "/api/import/tasks" and method == "POST":
            message = add_agent_tasks(s, body)
        elif path == "/api/import/backup" and method == "POST":
            if body.get("app") != "StudyTracker" or body.get("version") != 2 or body.get("filtered"):
                err("Ungültiges vollständiges StudyTracker-v2-Backup.")
            restored = validate_backup(body.get("data"))
            # Active timer is deliberately not restored.
            s = restored
        else:
            err("Unbekannter API-Endpunkt.", 404)
        save_profile(user_id, s)
        return {"ok": True, "state": s, **message}


def validate_backup(v):
    if not isinstance(v, dict) or v.get("version") != 2:
        err("Backup-Version ungültig.")
    if any(not isinstance(v.get(k), list) for k in ("subjects", "tags", "tasks", "sessions")):
        err("Backup unvollständig.")
    if len(v["subjects"]) > 500 or len(v["tags"]) > 500 or len(v["tasks"]) > 50000 or len(v["sessions"]) > 150000:
        err("Backup zu groß.")
    s = {"version": 2, "subjects": [], "tags": [], "tasks": [], "sessions": [], "active_timer": None,
         "settings": {"weekly_goal_minutes": 900}, "imports": []}
    for su in v["subjects"]:
        sid = txt(su.get("id"), "Fach-ID", 80, True)
        if any(x["id"] == sid for x in s["subjects"]):
            err("Doppelte Fach-ID.")
        s["subjects"].append({"id": sid, "name": txt(su.get("name"), "Fach", 60, True),
                              "color": check_color(su.get("color")), "weekly_goal_minutes": number(su.get("weekly_goal_minutes", 0), "Ziel", 0, 10080),
                              "archived": bool(su.get("archived", False))})
    for ta in v["tags"]:
        tid = txt(ta.get("id"), "Tag-ID", 80, True)
        if any(x["id"] == tid for x in s["tags"]):
            err("Doppelte Tag-ID.")
        s["tags"].append({"id": tid, "name": txt(ta.get("name"), "Tag", 50, True), "color": check_color(ta.get("color"))})
    for tr in v["tasks"]:
        tid = txt(tr.get("id"), "Task-ID", 80, True)
        if any(x["id"] == tid for x in s["tasks"]):
            err("Doppelte Task-ID.")
        fields = task_fields(s, tr)
        s["tasks"].append({"id": tid, **fields, "external_id": txt(tr.get("external_id") or "", "Extern-ID", 160) or None,
                           "created_at": timestamp(tr.get("created_at", iso())).isoformat(timespec="seconds"),
                           "updated_at": timestamp(tr.get("updated_at", iso())).isoformat(timespec="seconds"),
                           "completed_at": timestamp(tr["completed_at"]).isoformat(timespec="seconds") if tr.get("completed_at") else None})
    for sr in v["sessions"]:
        sid = txt(sr.get("id"), "Session-ID", 80, True)
        if any(x["id"] == sid for x in s["sessions"]):
            err("Doppelte Session-ID.")
        # Validate break entries and task link.
        raw_breaks = sr.get("breaks", [])
        if not isinstance(raw_breaks, list) or len(raw_breaks) > 200:
            err("Ungültige Pausenhistorie.")
        cleaned_breaks = []
        for b in raw_breaks:
            cleaned_breaks.append({"started_at": timestamp(b.get("started_at")).isoformat(timespec="seconds"),
                                   "ended_at": timestamp(b.get("ended_at")).isoformat(timespec="seconds"),
                                   "duration_seconds": number(b.get("duration_seconds"), "Pause", 0, 86400)})
        fields = session_fields(s, sr)
        fields["break_seconds"] = number(sr.get("break_seconds", 0), "Pausenzeit", 0, 86400)
        if sr.get("ended_at"):
            original_end = timestamp(sr["ended_at"])
            if original_end < timestamp(fields["started_at"]) + timedelta(seconds=fields["duration_seconds"]):
                err("Session-Ende liegt vor Ablauf der Fokuszeit.")
            fields["ended_at"] = original_end.isoformat(timespec="seconds")
        fields["breaks"] = cleaned_breaks
        s["sessions"].append({"id": sid, **fields, "source": "timer" if sr.get("source") == "timer" else "manual",
                              "created_at": timestamp(sr.get("created_at", iso())).isoformat(timespec="seconds")})
    settings = v.get("settings", {})
    if isinstance(settings, dict):
        s["settings"]["weekly_goal_minutes"] = number(settings.get("weekly_goal_minutes", 900), "Wochenziel", 0, 10080)
    imported = v.get("imports", [])
    if isinstance(imported, list):
        for line in imported[:5000]:
            if isinstance(line, dict):
                s["imports"].append({"batch_id": txt(line.get("batch_id", ""), "Batch-ID", 100, True),
                                     "at": timestamp(line.get("at", iso())).isoformat(timespec="seconds"),
                                     "added": number(line.get("added", 0), "Importanzahl", 0, 10000),
                                     "skipped": number(line.get("skipped", 0), "Duplikate", 0, 10000)})
    return s


def export_csv(state, kind):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";")
    subjects = {x["id"]: x["name"] for x in state["subjects"]}
    tag_names = {x["id"]: x["name"] for x in state["tags"]}
    def protect(v):
        a = str(v if v is not None else "")
        return "'" + a if a.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else a
    if kind == "sessions":
        writer.writerow(["ID", "Fach", "Aufgabe ID", "Titel", "Tags", "Start UTC", "Ende UTC", "Lernminuten", "Pausenminuten", "Pausenintervalle (UTC ISO)", "Quelle", "Notizen"])
        for sr in state["sessions"]:
            writer.writerow([sr["id"], protect(subjects.get(sr["subject_id"])), sr.get("task_id") or "", protect(sr["title"]),
                             protect(", ".join(tag_names.get(t, t) for t in sr["tags"])), sr["started_at"], sr["ended_at"],
                             f'{sr["duration_seconds"]/60:.2f}'.replace(".", ","),
                             f'{sr.get("break_seconds", 0)/60:.2f}'.replace(".", ","),
                             protect(" | ".join(b["started_at"]+" bis "+b["ended_at"] for b in sr.get("breaks", []))), sr["source"], protect(sr["notes"])])
    elif kind == "tasks":
        writer.writerow(["ID", "Fach", "Titel", "Status", "Priorität", "Fällig", "Geschätzt min", "Ist min", "Abweichung min", "Abweichung %", "Tags", "Extern-ID"])
        used = {}
        for sr in state["sessions"]:
            if sr.get("task_id"):
                used[sr["task_id"]] = used.get(sr["task_id"], 0) + sr["duration_seconds"]
        for t in state["tasks"]:
            act = used.get(t["id"], 0) / 60
            planned = t["planned_minutes"]
            writer.writerow([t["id"], protect(subjects.get(t["subject_id"])), protect(t["title"]), t["status"], t["priority"], t["due_date"] or "",
                             planned, f"{act:.2f}".replace(".", ","), f"{act-planned:.2f}".replace(".", ","),
                             f"{(act-planned)/planned*100:.1f}".replace(".", ","), protect(", ".join(tag_names.get(x,x) for x in t["tags"])), protect(t.get("external_id", ""))])
    else:
        err("Nur sessions und tasks als CSV verfügbar.")
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def ingest_inbox_once() -> list[dict]:
    """Safe file polling for Polybox synced inbox; process files per username.

    Bad inputs are quarantined; duplicates produce 0 inserts; never execute commands.
    """
    results = []
    with LOCK:
        for u in accounts()["users"]:
            inbox = DATA_DIR / "inbox" / u["username"]
            inbox.mkdir(parents=True, exist_ok=True)
            for path in sorted(inbox.glob("*.json"))[:50]:
                if not path.is_file():
                    continue
                # Polybox may still be syncing. Only consume files untouched for 3 seconds.
                if time.time() - path.stat().st_mtime < 3:
                    continue
                good, error = False, None
                try:
                    if path.stat().st_size > 1024 * 1024:
                        err("Importdatei über 1 MB.")
                    payload = json.loads(path.read_text("utf-8"))
                    s = load_profile(u["id"])
                    outcome = add_agent_tasks(s, payload)
                    save_profile(u["id"], s)
                    results.append({"file": path.name, "user": u["username"], **outcome})
                    good = True
                except (OSError, ValueError, TypeError, KeyError, ClientError) as ex:
                    error = str(ex)
                    results.append({"file": path.name, "user": u["username"], "error": error})
                destination = inbox / ("processed" if good else "rejected")
                try:
                    destination.mkdir(exist_ok=True)
                    target = destination / (path.stem + "-" + uid()[:8] + path.suffix)
                    path.replace(target)
                    if error:
                        target.with_suffix(".error.txt").write_text(error, "utf-8")
                except OSError as ex:
                    print("Import-Datei konnte nicht verschoben werden:", ex)
    return results


class Handler(BaseHTTPRequestHandler):
    server_version = "StudyTracker/2.0"

    def json_response(self, status, data, headers=None):
        self.raw_response(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", headers)

    def raw_response(self, status, data, mime, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def get_user(self, mandatory=False):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            token = cookie.get("studytracker_session")
            user_id = SESSIONS.get(token.value) if token else None
            user = account_by_id(user_id) if user_id else None
        except Exception:
            user = None
        if mandatory and not user:
            err("Bitte anmelden.", 401)
        return user

    def do_GET(self):
        route = urlparse(self.path)
        try:
            if route.path == "/api/auth/status":
                a = accounts()
                u = self.get_user()
                return self.json_response(200, {"setup_required": not bool(a["users"]), "user": public_user(u) if u else None})
            if route.path == "/api/state":
                u = self.get_user(True)
                return self.json_response(200, {"state": load_profile(u["id"]), "user": public_user(u), "server_time": iso()})
            if route.path == "/api/users":
                u = self.get_user(True)
                if u["role"] != "admin":
                    err("Nur Admins können Konten verwalten.", 403)
                return self.json_response(200, {"users": [public_user(x) for x in accounts()["users"]]})
            if route.path == "/api/export":
                u = self.get_user(True)
                s = load_profile(u["id"])
                params = parse_qs(route.query)
                fmt = params.get("format", ["json"])[0]
                if fmt == "json":
                    body = json.dumps({"app": "StudyTracker", "version": 2, "exported_at": iso(), "data": {**s, "active_timer": None}}, ensure_ascii=False, indent=2).encode("utf-8")
                    name, mime = "StudyTracker-Backup.json", "application/json; charset=utf-8"
                elif fmt == "csv":
                    kind = params.get("kind", ["sessions"])[0]
                    body = export_csv(s, kind)
                    name, mime = f"StudyTracker-{kind}.csv", "text/csv; charset=utf-8"
                else:
                    err("Unbekanntes Exportformat.")
                return self.raw_response(200, body, mime, {"Content-Disposition": f'attachment; filename="{name}"'})
            if route.path in ("/", "/index.html"):
                path, mime = STATIC / "index.html", "text/html; charset=utf-8"
            elif route.path in ("/app.js", "/app.css"):
                path = STATIC / route.path.lstrip("/")
                mime = "text/javascript; charset=utf-8" if path.suffix == ".js" else "text/css; charset=utf-8"
            else:
                err("Nicht gefunden.", 404)
            return self.raw_response(200, path.read_bytes(), mime)
        except ClientError as e:
            self.json_response(e.status, {"error": e.message})
        except (ValueError, OSError, KeyError) as e:
            self.json_response(500, {"error": "Speicherfehler: " + str(e)})

    def do_POST(self): self.change("POST")
    def do_PATCH(self): self.change("PATCH")
    def do_DELETE(self): self.change("DELETE")

    def change(self, method):
        try:
            host = self.headers.get("Host", "")
            if host not in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"):
                err("Nur lokaler Zugriff erlaubt.", 403)
            origin = self.headers.get("Origin")
            if origin and origin not in (f"http://localhost:{self.server.server_port}", f"http://127.0.0.1:{self.server.server_port}"):
                err("Fremde Webanfrage blockiert.", 403)
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                err("JSON-Anfrage erforderlich.", 415)
            size = number(self.headers.get("Content-Length", "0"), "Body-Größe", 0, MAX_REQUEST)
            body = json.loads(self.rfile.read(size).decode("utf-8")) if size else {}
            if not isinstance(body, dict):
                err("JSON-Objekt erwartet.")
            path = urlparse(self.path).path
            if path == "/api/auth/setup" and method == "POST":
                user = create_user(body, first=True)
                _, token = sign_in(user["username"], body["password"])
                return self.json_response(200, {"user": user}, {"Set-Cookie": f"studytracker_session={token}; HttpOnly; SameSite=Strict; Path=/"})
            if path == "/api/auth/login" and method == "POST":
                user, token = sign_in(body.get("username"), body.get("password"))
                return self.json_response(200, {"user": user}, {"Set-Cookie": f"studytracker_session={token}; HttpOnly; SameSite=Strict; Path=/"})
            if path == "/api/auth/logout" and method == "POST":
                cookie = SimpleCookie()
                cookie.load(self.headers.get("Cookie", ""))
                if cookie.get("studytracker_session"):
                    with LOCK:
                        SESSIONS.pop(cookie["studytracker_session"].value, None)
                return self.json_response(200, {"ok": True}, {"Set-Cookie": "studytracker_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"})
            user = self.get_user(True)
            if path == "/api/users" and method == "POST":
                if user["role"] != "admin":
                    err("Nur Admins dürfen Benutzer erstellen.", 403)
                u = create_user(body, first=False)
                return self.json_response(200, {"user": u})
            result = mutate(user["id"], method, path, body)
            return self.json_response(200, result)
        except ClientError as e:
            self.json_response(e.status, {"error": e.message})
        except (OSError, ValueError, KeyError, UnicodeError, json.JSONDecodeError) as e:
            self.json_response(400, {"error": "Anfrage fehlgeschlagen: " + str(e)})

    def log_message(self, format, *args):
        if os.environ.get("STUDYTRACKER_VERBOSE") == "1":
            super().log_message(format, *args)


def run_server(port=8765, open_browser=True):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    def background_import():
        while not stop.wait(4):
            try:
                processed = ingest_inbox_once()
                for r in processed:
                    print("[Import]", r)
            except Exception as e:
                print("[Importfehler]", e)
    thread = threading.Thread(target=background_import, name="task-inbox", daemon=True)
    thread.start()
    try:
        with ThreadingHTTPServer(("127.0.0.1", port), Handler) as srv:
            print(f"StudyTracker 2 gestartet: http://127.0.0.1:{srv.server_port}")
            print(f"Polybox-Datenverzeichnis: {DATA_DIR}")
            if open_browser:
                threading.Timer(0.7, lambda: webbrowser.open(f"http://127.0.0.1:{srv.server_port}")).start()
            srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStudyTracker beendet.")
    finally:
        stop.set()


def main():
    p = argparse.ArgumentParser(description="StudyTracker 2 - Lerntracking mit Kanban & Polybox")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--import-once", action="store_true", help="Polybox-Inbox einmalig verarbeiten und beenden")
    args = p.parse_args()
    if args.import_once:
        for outcome in ingest_inbox_once():
            print(json.dumps(outcome, ensure_ascii=False))
    else:
        run_server(args.port, not args.no_browser)


if __name__ == "__main__":
    main()
