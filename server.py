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
REVIEW_OUTCOMES = {"correct", "partial", "incorrect"}
REVIEW_ISSUES = {"concept", "approach", "calculation", "implementation", "instructions", "careless", "time", "verification"}
REVIEW_HELP_TYPES = {"verification", "hint", "guiding_questions", "concept_explanation", "approach_selection", "step_by_step", "debugging", "calculation", "code_generation", "full_solution", "error_identification"}
REVIEW_KEYS = ("difficulty", "outcome", "issue", "help_total", "help_chatgpt", "issues", "strength", "weakness", "skill_gap", "next_action", "chatgpt_interventions")
REVIEW_TEXT_LIMITS = {"strength": 200, "weakness": 200, "skill_gap": 100, "next_action": 160}


def review_multi(value, allowed, label):
    if value in (None, ""):
        return None
    if not isinstance(value, list) or len(value) > 3 or any(not isinstance(x, str) or x not in allowed for x in value) or len(set(value)) != len(value):
        err(f"Ungültige Liste: {label} (maximal drei unterschiedliche Einträge).")
    return value or None



def validate_exercise_review(payload):
    """One optional assessment per task; every value may independently be null.

    Empty data is equivalent to no assessment. All five ratings remain separate
    from timer sessions and cannot accidentally be interpreted as retries.
    """
    if payload is None:
        return None
    if not isinstance(payload, dict):
        err("Exercise-Bewertung muss ein Objekt sein.")
    if set(payload) - set(REVIEW_KEYS):
        err("Unbekanntes Bewertungsfeld.")
    result = {}
    for k in ("difficulty", "help_total", "help_chatgpt"):
        value = payload.get(k)
        result[k] = None if value is None or value == "" else number(value, k, 0 if k != "difficulty" else 1, 5)
    for k, choices in (("outcome", REVIEW_OUTCOMES), ("issue", REVIEW_ISSUES)):
        value = payload.get(k)
        if value in (None, ""):
            result[k] = None
        elif not isinstance(value, str) or value not in choices:
            err("Ungültige Exercise-Bewertung: " + k)
        else:
            result[k] = value
    result["issues"] = review_multi(payload.get("issues"), REVIEW_ISSUES, "issues")
    if result["issue"] and result["issues"] is None:
        result["issues"] = [result["issue"]]
    if result["issue"] and result["issues"] and result["issue"] not in result["issues"]:
        err("Das Hauptproblem muss zu den ausgewählten Problemen gehören.")
    if result["issues"] and not result["issue"]:
        result["issue"] = result["issues"][0]
    for key, limit in REVIEW_TEXT_LIMITS.items():
        value = payload.get(key)
        result[key] = None if value in (None, "") else txt(value, key, limit) or None
    result["chatgpt_interventions"] = review_multi(payload.get("chatgpt_interventions"), REVIEW_HELP_TYPES, "chatgpt_interventions")
    if result["help_total"] is not None and result["help_chatgpt"] is not None and result["help_chatgpt"] > result["help_total"]:
        err("ChatGPT-Hilfe kann nicht höher als gesamte Hilfe sein.")
    return result if any(value is not None for value in result.values()) else None



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


def optional_goal(value, label="Wochenziel"):
    """No weekly target is a normal, supported state; 0 means unset for legacy data."""
    if value is None or value == "" or value == 0:
        return None
    return number(value, label, 1, 10080)


def semester_id(state, value):
    if value is None or value == "":
        return None
    sid = txt(value, "Semester-ID", 80, True)
    if not any(x["id"] == sid for x in state.get("semesters", [])):
        err("Semester nicht gefunden.", 404)
    return sid


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
        {"id": "mathe", "name": "Mathematik", "color": COLORS[0], "weekly_goal_minutes": None, "semester_id": None, "archived": False},
        {"id": "info", "name": "Informatik", "color": COLORS[1], "weekly_goal_minutes": None, "semester_id": None, "archived": False},
        {"id": "physik", "name": "Physik", "color": COLORS[2], "weekly_goal_minutes": None, "semester_id": None, "archived": False},
    ], "tags": [
        {"id": "uebungen", "name": "Übungen", "color": COLORS[0]},
        {"id": "lesen", "name": "Neuer Stoff", "color": COLORS[1]},
        {"id": "wiederholen", "name": "Wiederholung", "color": COLORS[2]},
        {"id": "pruefung", "name": "Prüfung", "color": COLORS[4]},
        {"id": "vorlesung", "name": "Vorlesung", "color": COLORS[3]},
        {"id": "videos", "name": "Videos", "color": COLORS[5]},
    ], "semesters": [], "tasks": [], "sessions": [], "active_timer": None, "settings": {"weekly_goal_minutes": None, "v4_default_categories_initialized": True}, "imports": []}


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
    # Non-destructive migration for existing v2 accounts and JSON files.
    data.setdefault("semesters", [])
    data.setdefault("settings", {}).setdefault("weekly_goal_minutes", None)
    for sub in data.get("subjects", []):
        sub.setdefault("semester_id", None)
        sub.setdefault("weekly_goal_minutes", None)
    # One-time upgrade. Users are free to delete or rename the seeded tags later.
    if not data["settings"].get("v4_default_categories_initialized"):
        for ident, name, color in (("vorlesung", "Vorlesung", COLORS[3]), ("videos", "Videos", COLORS[5])):
            if not any(t.get("name", "").casefold() == name.casefold() for t in data.setdefault("tags", [])):
                unique_id = ident if not any(t.get("id") == ident for t in data["tags"]) else uid()
                data["tags"].append({"id": unique_id, "name": name, "color": color})
        data["settings"]["v4_default_categories_initialized"] = True
    for t in data.get("tasks", []):
        t.setdefault("parent_id", None)
        t.setdefault("planned_for", None)
        t.setdefault("exercise_review", None)
        t.setdefault("exercise_review_gpt", None)
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


def validate_parent(state, parent_id, task_id=None, subject_id=None):
    """Only one level of child tasks; all children share the parent's subject."""
    if parent_id is None or parent_id == "":
        return None
    pid = txt(parent_id, "Hauptaufgaben-ID", 80, True)
    if pid == task_id:
        err("Eine Aufgabe kann nicht ihre eigene Hauptaufgabe sein.")
    parent = task(state, pid)
    if parent.get("parent_id"):
        err("Unteraufgaben können keine weiteren Unteraufgaben enthalten.")
    if task_id and any(t.get("parent_id") == task_id for t in state["tasks"]):
        err("Eine Hauptaufgabe mit Unteraufgaben kann nicht selbst Unteraufgabe werden.")
    if parent["subject_id"] != subject_id:
        err("Hauptaufgabe und Unteraufgabe müssen zum gleichen Fach gehören.")
    return pid


def update_task_status(state, row, new_status):
    """Apply bidirectional parent/child completion without changing unrelated children."""
    when = iso()
    status_changed = row["status"] != new_status
    if status_changed:
        row["status"] = new_status
        row["completed_at"] = when if new_status == "done" else None
        row["updated_at"] = when
    children = [t for t in state["tasks"] if t.get("parent_id") == row["id"]]
    if children and status_changed and new_status in ("done", "todo"):
        # Only explicitly completing or reopening the parent cascades to its children.
        # Moving it to in-progress, or editing metadata, preserves child states.
        for child in children:
            child_status = new_status
            if child["status"] != child_status:
                child["status"] = child_status
                child["completed_at"] = when if child_status == "done" else None
                child["updated_at"] = when
    if row.get("parent_id"):
        parent = task(state, row["parent_id"])
        siblings = [t for t in state["tasks"] if t.get("parent_id") == parent["id"]]
        desired = "done" if all(t["status"] == "done" for t in siblings) else "doing" if any(t["status"] != "todo" for t in siblings) else "todo"
        if parent["status"] != desired:
            parent["status"] = desired
            parent["completed_at"] = when if desired == "done" else None
            parent["updated_at"] = when


def reconcile_parent(state, parent_id):
    if not parent_id:
        return
    parent = task(state, parent_id)
    siblings = [t for t in state["tasks"] if t.get("parent_id") == parent_id]
    if siblings:
        desired = "done" if all(t["status"] == "done" for t in siblings) else "doing" if any(t["status"] != "todo" for t in siblings) else "todo"
        if parent["status"] != desired:
            parent["status"] = desired
            parent["completed_at"] = iso() if desired == "done" else None
            parent["updated_at"] = iso()


def task_fields(state, body, existing=None):
    sid = txt(body.get("subject_id", existing["subject_id"] if existing else ""), "Fach-ID", 80, True)
    subject(state, sid)
    raw_planned = body.get("planned_minutes", existing.get("planned_minutes") if existing else None)
    planned = None if raw_planned is None or raw_planned == "" else number(raw_planned, "Schätzung (Minuten)", 1, 100000)
    parent = validate_parent(state, body.get("parent_id", existing.get("parent_id") if existing else None),
                             existing["id"] if existing else None, sid)
    status = body.get("status", existing["status"] if existing else "todo")
    priority = body.get("priority", existing["priority"] if existing else "normal")
    if status not in VALID_STATES or priority not in PRIORITIES:
        err("Status oder Priorität ungültig.")
    fields = {"title": txt(body.get("title", existing["title"] if existing else ""), "Aufgabentitel", 180, True),
              "description": txt(body.get("description", existing["description"] if existing else ""), "Beschreibung", 3000),
              "subject_id": sid, "planned_minutes": planned, "parent_id": parent, "status": status, "priority": priority,
              "due_date": due(body.get("due_date", existing["due_date"] if existing else None)),
              "planned_for": due(body.get("planned_for", existing.get("planned_for") if existing else None)),
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
    selected_tags = valid_tags(state, body.get("tags", existing["tags"] if existing else []))
    primary = body.get("category_tag_id", existing.get("category_tag_id") if existing else (selected_tags[0] if selected_tags else None))
    if primary in (None, ""):
        primary = None
    elif primary not in {t["id"] for t in state["tags"]}:
        err("Kategorie nicht gefunden.")
    if primary and primary not in selected_tags:
        selected_tags.insert(0, primary)
    return {"subject_id": sid, "task_id": task_id,
            "category_tag_id": primary,
            "title": txt(body.get("title", existing.get("title", "") if existing else ""), "Beschreibung", 180),
            "notes": txt(body.get("notes", existing.get("notes", "") if existing else ""), "Notizen", 3000),
            "tags": selected_tags,
            "started_at": start.isoformat(timespec="seconds"), "ended_at": (start + timedelta(seconds=duration)).isoformat(timespec="seconds"),
            "duration_seconds": duration,
            # Edits intentionally retain original break records, and cannot change them.
            "break_seconds": existing.get("break_seconds", 0) if existing else 0,
            "breaks": existing.get("breaks", []) if existing else [],
            # Retain exact focus intervals only if the session timing was unchanged.
            "focus_intervals": (existing.get("focus_intervals", []) if existing and
                start == timestamp(existing["started_at"]) and duration == existing["duration_seconds"] else [])}


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
        t.setdefault("focus_intervals", []).append({
            "started_at": timestamp(t["mode_since"]).isoformat(timespec="seconds"),
            "ended_at": moment.isoformat(timespec="seconds")})
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
    """Atomic, idempotent import; relationships reference stable external task IDs."""
    if not isinstance(payload, dict) or payload.get("format") != "studytracker.tasks.v1":
        err("Erwartet format: studytracker.tasks.v1.")
    batch_id = safe_batch_key(payload.get("batch_id"))
    items = payload.get("tasks")
    if not isinstance(items, list) or not 1 <= len(items) <= 150:
        err("Eine Importdatei braucht 1 bis 150 Aufgaben.")
    if any(i.get("batch_id") == batch_id for i in state["imports"]):
        return {"added": 0, "skipped": len(items), "batch_id": batch_id, "already_imported": True}
    staged = copy.deepcopy(state)
    known_external = {t.get("external_id"): t for t in staged["tasks"] if t.get("external_id")}
    added, skipped, links = 0, 0, []
    for item in items:
        if not isinstance(item, dict):
            err("Jede Aufgabe muss ein JSON-Objekt sein.")
        ext = txt(item.get("external_id", ""), "Externe Aufgaben-ID", 160, True)
        if ext in known_external:
            skipped += 1
            continue
        # Agents may pin an import to an EXISTING module by its internal ID.
        # Name-based imports remain compatible, but IDs never create new modules.
        requested_sid = item.get("subject_id")
        subject_name = txt(item.get("subject") or "", "Fach", 60)
        sem_name = txt(item.get("semester") or "", "Semester", 80)
        if requested_sid is not None:
            requested_sid = txt(requested_sid, "Fach-ID", 80, True)
            sub = subject(staged, requested_sid)
            if subject_name and subject_name.casefold() != sub["name"].casefold():
                err("Fach-ID und Fachname passen nicht zusammen.")
            if sem_name:
                selected_sem = next((x for x in staged["semesters"] if x["id"] == sub.get("semester_id")), None)
                if not selected_sem or selected_sem["name"].casefold() != sem_name.casefold():
                    err("Semester passt nicht zur gewählten Fach-ID.")
        elif not subject_name:
            err("Entweder 'subject_id' oder 'subject' ist erforderlich.")
        else:
            sub = None
        sem = None
        if requested_sid is None and sem_name:
            sem = next((x for x in staged["semesters"] if x["name"].casefold() == sem_name.casefold()), None)
            if sem is None:
                sem = {"id": uid(), "name": sem_name}
                staged["semesters"].append(sem)
        if requested_sid is None:
            matches = [x for x in staged["subjects"] if x["name"].casefold() == subject_name.casefold()]
            if sem:
                sub = next((x for x in matches if x.get("semester_id") == sem["id"]), None)
            elif len(matches) > 1:
                err("Mehrere Fächer mit diesem Namen. Bitte 'semester' im Import angeben.")
            else:
                sub = matches[0] if matches else None
        if not sub:
            sub = {"id": uid(), "name": subject_name, "color": COLORS[len(staged["subjects"]) % len(COLORS)],
                   "weekly_goal_minutes": None, "semester_id": sem["id"] if sem else None, "archived": False}
            staged["subjects"].append(sub)
        tag_ids = []
        incoming_tags = item.get("tags", [])
        if not isinstance(incoming_tags, list) or len(incoming_tags) > 12:
            err("Pro Aufgabe höchstens 12 Tags.")
        for tag_name in incoming_tags:
            tag_name = txt(tag_name, "Tag", 50, True)
            tag = next((x for x in staged["tags"] if x["name"].casefold() == tag_name.casefold()), None)
            if not tag:
                tag = {"id": uid(), "name": tag_name, "color": COLORS[len(staged["tags"]) % len(COLORS)]}
                staged["tags"].append(tag)
            if tag["id"] not in tag_ids:
                tag_ids.append(tag["id"])
        row = task_fields(staged, {"subject_id": sub["id"], "title": item.get("title", ""),
                                   "description": item.get("description", ""),
                                   "planned_minutes": item.get("planned_minutes"),
                                   "status": "todo", "priority": item.get("priority", "normal"),
                                   "due_date": item.get("due_date"), "planned_for": item.get("planned_for"),
                                   "tags": tag_ids})
        created = {"id": uid(), **row, "external_id": ext,
                   "created_at": iso(), "updated_at": iso(), "completed_at": None, "exercise_review": None, "exercise_review_gpt": None}
        staged["tasks"].append(created)
        known_external[ext] = created
        parent_external = item.get("parent_external_id")
        parent_internal = item.get("parent_id")
        if parent_external and parent_internal:
            err("Nur 'parent_id' oder 'parent_external_id' angeben, nicht beide.")
        if parent_internal is not None:
            links.append((created, "internal", txt(parent_internal, "Hauptaufgaben-ID", 80, True)))
        elif parent_external:
            links.append((created, "external", txt(parent_external, "Externe Hauptaufgaben-ID", 160, True)))
        added += 1
    # Resolve parent links in a separate pass, regardless of JSON task order.
    for child, kind, parent_key in links:
        parent = known_external.get(parent_key) if kind == "external" else task(staged, parent_key)
        if not parent:
            err(f"Hauptaufgabe nicht gefunden: {parent_key}")
        child["parent_id"] = validate_parent(staged, parent["id"], child["id"], child["subject_id"])
    for parent_id in {child["parent_id"] for child, _, _ in links}:
        reconcile_parent(staged, parent_id)
    staged["imports"].append({"batch_id": batch_id, "at": iso(), "added": added, "skipped": skipped})
    state.clear()
    state.update(staged)
    return {"added": added, "skipped": skipped, "batch_id": batch_id, "already_imported": False}


def mutate(user_id, method, path, body):
    with LOCK:
        s = load_profile(user_id)
        parts = path.strip("/").split("/")
        message = {}
        if path == "/api/semesters" and method == "POST":
            name = txt(body.get("name", ""), "Semestername", 80, True)
            if any(x["name"].casefold() == name.casefold() for x in s["semesters"]):
                err("Semester existiert bereits.")
            s["semesters"].append({"id": uid(), "name": name})
        elif len(parts) == 3 and parts[1] == "semesters" and method == "PATCH":
            current = next((x for x in s["semesters"] if x["id"] == parts[2]), None)
            if current is None:
                err("Semester nicht gefunden.", 404)
            name = txt(body.get("name", current["name"]), "Semestername", 80, True)
            if any(x["id"] != current["id"] and x["name"].casefold() == name.casefold() for x in s["semesters"]):
                err("Semester existiert bereits.")
            current["name"] = name
        elif len(parts) == 3 and parts[1] == "semesters" and method == "DELETE":
            sid = semester_id(s, parts[2])
            s["semesters"] = [x for x in s["semesters"] if x["id"] != sid]
            for sub in s["subjects"]:
                if sub.get("semester_id") == sid:
                    sub["semester_id"] = None
        elif path == "/api/subjects" and method == "POST":
            name = txt(body.get("name", ""), "Fach", 60, True)
            sem = semester_id(s, body.get("semester_id"))
            if any(x["name"].casefold() == name.casefold() and x.get("semester_id") == sem for x in s["subjects"]):
                err("Fach existiert in diesem Semester bereits.")
            s["subjects"].append({"id": uid(), "name": name, "color": check_color(body.get("color", COLORS[0])),
                                  "weekly_goal_minutes": optional_goal(body.get("weekly_goal_minutes"), "Fachziel"),
                                  "semester_id": sem, "archived": False})
        elif len(parts) == 3 and parts[1] == "subjects" and method == "PATCH":
            sub = subject(s, parts[2])
            next_name = txt(body.get("name", sub["name"]), "Fach", 60, True)
            next_sem = semester_id(s, body.get("semester_id", sub.get("semester_id")))
            if any(x["id"] != sub["id"] and x["name"].casefold() == next_name.casefold() and x.get("semester_id") == next_sem for x in s["subjects"]):
                err("Fach existiert in diesem Semester bereits.")
            sub["name"] = next_name
            sub["semester_id"] = next_sem
            if "color" in body:
                sub["color"] = check_color(body["color"])
            if "weekly_goal_minutes" in body:
                sub["weekly_goal_minutes"] = optional_goal(body["weekly_goal_minutes"], "Fachziel")
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
                if sr.get("category_tag_id") == tid:
                    sr["category_tag_id"] = None
            active_timer = s.get("active_timer")
            if active_timer:
                active_timer["tags"] = [x for x in active_timer.get("tags", []) if x != tid]
                if active_timer.get("category_tag_id") == tid:
                    active_timer["category_tag_id"] = None
        elif path == "/api/settings" and method == "PATCH":
            s["settings"]["weekly_goal_minutes"] = optional_goal(body.get("weekly_goal_minutes"), "Wochenziel")
        elif path == "/api/tasks" and method == "POST":
            taskrow = {"id": uid(), **task_fields(s, body), "external_id": None, "created_at": iso(), "updated_at": iso(), "completed_at": None, "exercise_review": None}
            if taskrow["status"] == "done":
                taskrow["completed_at"] = iso()
            s["tasks"].append(taskrow)
            reconcile_parent(s, taskrow.get("parent_id"))
            message["task_id"] = taskrow["id"]
        elif len(parts) == 3 and parts[1] == "tasks" and method == "PATCH":
            row = task(s, parts[2])
            fields = task_fields(s, body, row)
            if fields["subject_id"] != row["subject_id"] and (
                (s["active_timer"] and s["active_timer"].get("task_id") == row["id"]) or
                any(entry.get("task_id") == row["id"] for entry in s["sessions"])
            ):
                err("Fach einer Aufgabe mit erfasster Lernzeit kann nicht geändert werden.")
            # Changing a task's subject must not leave its descendants behind.
            if fields["subject_id"] != row["subject_id"] and any(x.get("parent_id") == row["id"] for x in s["tasks"]):
                err("Fach einer Hauptaufgabe mit Unteraufgaben kann nicht geändert werden.")
            prior_parent = row.get("parent_id")
            desired_status = fields.pop("status")
            fields.pop("completed_at", None)
            row.update(fields)
            row["updated_at"] = iso()
            update_task_status(s, row, desired_status)
            if prior_parent != row.get("parent_id"):
                reconcile_parent(s, prior_parent)
                reconcile_parent(s, row.get("parent_id"))
        elif len(parts) == 4 and parts[1] == "tasks" and parts[3] == "review" and method == "PATCH":
            row = task(s, parts[2])
            if not isinstance(body, dict):
                err("Ungültige Bewertung.")
            # Keep student and AI ratings independently, while accepting old clients.
            if "self" in body or "gpt" in body:
                if set(body) - {"self", "gpt"}:
                    err("Unbekanntes Bewertungsfeld.")
                student = validate_exercise_review(body["self"]) if "self" in body else row.get("exercise_review")
                ai = validate_exercise_review(body["gpt"]) if "gpt" in body else row.get("exercise_review_gpt")
                row["exercise_review"] = student
                row["exercise_review_gpt"] = ai
            else:
                row["exercise_review"] = validate_exercise_review(body)
            row["updated_at"] = iso()
        elif len(parts) == 3 and parts[1] == "tasks" and method == "DELETE":
            row = task(s, parts[2])
            if s["active_timer"] and s["active_timer"].get("task_id") == row["id"]:
                err("Aufgabe hat einen aktiven Timer.")
            # Historical sessions remain retained and detached for analytics.
            for sr in s["sessions"]:
                if sr.get("task_id") == row["id"]:
                    sr["task_id"] = None
            old_parent = row.get("parent_id")
            for child in s["tasks"]:
                if child.get("parent_id") == row["id"]:
                    # Deleting a parent never deletes valuable children or their sessions.
                    child["parent_id"] = None
            s["tasks"] = [t for t in s["tasks"] if t["id"] != row["id"]]
            reconcile_parent(s, old_parent)
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
                # A parent starts work without marking every child as in progress.
                t["status"], t["updated_at"] = "doing", iso()
                reconcile_parent(s, t.get("parent_id"))
            chosen = body.get("category_tag_id", t["tags"][0] if t and t["tags"] else None)
            if chosen in (None, ""):
                chosen = None
            elif chosen not in {tag["id"] for tag in s["tags"]}:
                err("Kategorie nicht gefunden.")
            tracking_tags = list(t["tags"]) if t else valid_tags(s, body.get("tags", []))
            if chosen and chosen not in tracking_tags:
                tracking_tags.insert(0, chosen)
            s["active_timer"] = {"subject_id": sid, "task_id": tid, "title": t["title"] if t else txt(body.get("title", ""), "Beschreibung", 180),
                                 "tags": tracking_tags, "category_tag_id": chosen, "notes": "",
                                 "first_started_at": iso(), "mode_since": iso(), "mode": "focus",
                                 "focus_seconds": 0, "break_seconds": 0, "breaks": [],
                                 "focus_intervals": []}
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
                                  "category_tag_id": t.get("category_tag_id"),
                                  "started_at": begun.isoformat(timespec="seconds"), "ended_at": iso(),
                                  "duration_seconds": t["focus_seconds"], "break_seconds": t["break_seconds"], "breaks": t["breaks"],
                                  "focus_intervals": t.get("focus_intervals", []),
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
    s = {"version": 2, "subjects": [], "semesters": [], "tags": [], "tasks": [], "sessions": [], "active_timer": None,
         "settings": {"weekly_goal_minutes": None}, "imports": []}
    raw_semesters = v.get("semesters", [])
    if not isinstance(raw_semesters, list) or len(raw_semesters) > 100:
        err("Ungültige Semester im Backup.")
    for semester in raw_semesters:
        sid = txt(semester.get("id"), "Semester-ID", 80, True)
        name = txt(semester.get("name"), "Semestername", 80, True)
        if any(x["id"] == sid or x["name"].casefold() == name.casefold() for x in s["semesters"]):
            err("Doppelte Semester im Backup.")
        s["semesters"].append({"id": sid, "name": name})
    for su in v["subjects"]:
        sid = txt(su.get("id"), "Fach-ID", 80, True)
        if any(x["id"] == sid for x in s["subjects"]):
            err("Doppelte Fach-ID.")
        s["subjects"].append({"id": sid, "name": txt(su.get("name"), "Fach", 60, True),
                              "color": check_color(su.get("color")), "weekly_goal_minutes": optional_goal(su.get("weekly_goal_minutes"), "Ziel"),
                              "semester_id": semester_id(s, su.get("semester_id")),
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
        # Validate parent links in a second pass: the parent may occur later in JSON.
        fields = task_fields(s, {**tr, "parent_id": None})
        s["tasks"].append({"id": tid, **fields, "external_id": txt(tr.get("external_id") or "", "Extern-ID", 160) or None,
                           "created_at": timestamp(tr.get("created_at", iso())).isoformat(timespec="seconds"),
                           "updated_at": timestamp(tr.get("updated_at", iso())).isoformat(timespec="seconds"),
                           "completed_at": timestamp(tr["completed_at"]).isoformat(timespec="seconds") if tr.get("completed_at") else None,
                           "exercise_review": validate_exercise_review(tr.get("exercise_review")),
                           "exercise_review_gpt": validate_exercise_review(tr.get("exercise_review_gpt"))})
    for raw in v["tasks"]:
        row = task(s, raw["id"])
        row["parent_id"] = validate_parent(s, raw.get("parent_id"), row["id"], row["subject_id"])
    for parent in [x for x in s["tasks"] if not x.get("parent_id") and any(c.get("parent_id") == x["id"] for c in s["tasks"])]:
        siblings = [c for c in s["tasks"] if c.get("parent_id") == parent["id"]]
        if (parent["status"] == "done") != all(c["status"] == "done" for c in siblings):
            err("Hauptaufgabe und Unteraufgaben haben widersprüchliche Stati.")
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
        raw_focus = sr.get("focus_intervals", [])
        if not isinstance(raw_focus, list) or len(raw_focus) > 2000:
            err("Ungültige Fokusintervalle.")
        cleaned_focus = []
        total_focus_ms = 0
        for interval in raw_focus:
            if not isinstance(interval, dict):
                err("Ungültiges Fokusintervall.")
            a, b = timestamp(interval.get("started_at")), timestamp(interval.get("ended_at"))
            if b <= a or a < timestamp(fields["started_at"]) or b > timestamp(fields["ended_at"]) + timedelta(seconds=2):
                err("Fokusintervall liegt außerhalb der Lerneinheit.")
            total_focus_ms += (b - a).total_seconds() * 1000
            cleaned_focus.append({"started_at": a.isoformat(timespec="seconds"),
                                  "ended_at": b.isoformat(timespec="seconds")})
        if cleaned_focus and abs(total_focus_ms/1000 - fields["duration_seconds"]) > len(cleaned_focus) + 2:
            err("Fokusintervalle und erfasste Lernzeit stimmen nicht überein.")
        fields["focus_intervals"] = cleaned_focus
        s["sessions"].append({"id": sid, **fields, "source": "timer" if sr.get("source") == "timer" else "manual",
                              "created_at": timestamp(sr.get("created_at", iso())).isoformat(timespec="seconds")})
    settings = v.get("settings", {})
    if isinstance(settings, dict):
        s["settings"]["weekly_goal_minutes"] = optional_goal(settings.get("weekly_goal_minutes"), "Wochenziel")
        s["settings"]["v4_default_categories_initialized"] = bool(settings.get("v4_default_categories_initialized", False))
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
    semesters = {x["id"]: x["name"] for x in state.get("semesters", [])}
    semester_by_subject = {x["id"]: semesters.get(x.get("semester_id"), "") for x in state["subjects"]}
    tag_names = {x["id"]: x["name"] for x in state["tags"]}
    def protect(v):
        a = str(v if v is not None else "")
        return "'" + a if a.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else a
    if kind == "sessions":
        writer.writerow(["ID", "Fach", "Semester", "Aufgabe ID", "Titel", "Tags", "Start UTC", "Ende UTC", "Lernminuten", "Pausenminuten", "Pausenintervalle (UTC ISO)", "Quelle", "Notizen", "Kategorie"])
        for sr in state["sessions"]:
            writer.writerow([sr["id"], protect(subjects.get(sr["subject_id"])), protect(semester_by_subject.get(sr["subject_id"])), sr.get("task_id") or "", protect(sr["title"]),
                             protect(", ".join(tag_names.get(t, t) for t in sr["tags"])), sr["started_at"], sr["ended_at"],
                             f'{sr["duration_seconds"]/60:.2f}'.replace(".", ","),
                             f'{sr.get("break_seconds", 0)/60:.2f}'.replace(".", ","),
                             protect(" | ".join(b["started_at"]+" bis "+b["ended_at"] for b in sr.get("breaks", []))), sr["source"], protect(sr["notes"]), protect(tag_names.get(sr["category_tag_id"] if "category_tag_id" in sr else (sr.get("tags") or [None])[0], "Ohne Kategorie"))])
    elif kind == "tasks":
        writer.writerow(["ID", "Fach", "Semester", "Titel", "Hauptaufgabe ID", "Status", "Priorität", "Fällig", "Geplant für", "Geschätzt min", "Ist min", "Abweichung min", "Abweichung %", "Tags", "Extern-ID", "Ist gesamt inkl Unteraufgaben min", "Schätzung für Auswertung min", "Abweichung für Auswertung min", "Schwierigkeit (1-5)", "Lösungserfolg", "Hauptproblem", "Gesamthilfe (0-5)", "ChatGPT-Hilfe (0-5)", "Eigene Probleme", "Eigene Stärke", "Eigene Schwäche", "Eigene Kompetenzlücke", "Eigene nächste Aktion", "Eigene GPT-Hilfearten", "GPT Schwierigkeit (1-5)", "GPT Lösungserfolg", "GPT Hauptproblem", "GPT Gesamthilfe (0-5)", "GPT ChatGPT-Hilfe (0-5)", "GPT Probleme", "GPT Stärke", "GPT Schwäche", "GPT Kompetenzlücke", "GPT nächste Aktion", "GPT Hilfearten"])
        used = {}
        for sr in state["sessions"]:
            if sr.get("task_id"):
                used[sr["task_id"]] = used.get(sr["task_id"], 0) + sr["duration_seconds"]
        for t in state["tasks"]:
            act = used.get(t["id"], 0) / 60
            planned = t["planned_minutes"]
            children = [c for c in state["tasks"] if c.get("parent_id") == t["id"]]
            full_actual = act + sum(used.get(c["id"], 0) for c in children) / 60
            full_planned = planned if planned is not None else (
                sum(c["planned_minutes"] for c in children) if children and all(c["planned_minutes"] is not None for c in children) else None)
            writer.writerow([t["id"], protect(subjects.get(t["subject_id"])), protect(semester_by_subject.get(t["subject_id"])), protect(t["title"]), t.get("parent_id") or "", t["status"], t["priority"], t["due_date"] or "", t.get("planned_for") or "",
                             "" if planned is None else planned, f"{act:.2f}".replace(".", ","),
                             "" if planned is None else f"{act-planned:.2f}".replace(".", ","),
                             "" if not planned else f"{(act-planned)/planned*100:.1f}".replace(".", ","), protect(", ".join(tag_names.get(x,x) for x in t["tags"])), protect(t.get("external_id", "")),
                             f"{full_actual:.2f}".replace(".", ","),
                             "" if full_planned is None else full_planned,
                             "" if full_planned is None else f"{full_actual-full_planned:.2f}".replace(".", ","),
                             *[(protect(" | ".join((t.get("exercise_review") or {}).get(k))) if isinstance((t.get("exercise_review") or {}).get(k), list) else protect((t.get("exercise_review") or {}).get(k)) if isinstance((t.get("exercise_review") or {}).get(k), str) else (t.get("exercise_review") or {}).get(k)) if (t.get("exercise_review") or {}).get(k) is not None else "" for k in REVIEW_KEYS],
                             *[(protect(" | ".join((t.get("exercise_review_gpt") or {}).get(k))) if isinstance((t.get("exercise_review_gpt") or {}).get(k), list) else protect((t.get("exercise_review_gpt") or {}).get(k)) if isinstance((t.get("exercise_review_gpt") or {}).get(k), str) else (t.get("exercise_review_gpt") or {}).get(k)) if (t.get("exercise_review_gpt") or {}).get(k) is not None else "" for k in REVIEW_KEYS]])
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
    server_version = "StudyTracker/4.3"

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
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
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
                return self.json_response(200, {"state": load_profile(u["id"]), "user": public_user(u), "server_time": iso(),
                                                "revision": str(profile_path(u["id"]).stat().st_mtime_ns)})
            if route.path == "/api/profile/revision":
                u = self.get_user(True)
                return self.json_response(200, {"revision": str(profile_path(u["id"]).stat().st_mtime_ns)})
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
            elif route.path in ("/app.js", "/app.css", "/features.css", "/i18n.js", "/time_analysis.js", "/exercise_review_import.js", "/import_wizard.js", "/rich_feedback.js", "/feedback_insights.js", "/favicon.svg"):
                path = STATIC / route.path.lstrip("/")
                mime = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml"}[path.suffix]
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
            if isinstance(result, dict) and "state" in result:
                result["revision"] = str(profile_path(user["id"]).stat().st_mtime_ns)
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
            print(f"StudyTracker 4.2 gestartet: http://127.0.0.1:{srv.server_port}")
            print(f"Polybox-Datenverzeichnis: {DATA_DIR}")
            if open_browser:
                threading.Timer(0.7, lambda: webbrowser.open(f"http://127.0.0.1:{srv.server_port}")).start()
            srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStudyTracker beendet.")
    finally:
        stop.set()


def main():
    p = argparse.ArgumentParser(description="StudyTracker 4.2 - Lerntracking mit Kanban & Polybox")
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
