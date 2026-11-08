#!/usr/bin/env python3
"""Atomic, validated drop-off of a StudyTracker agent JSON file into a user's inbox."""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get('STUDYTRACKER_DATA_DIR',ROOT/'data')).expanduser()

def main():
    p=argparse.ArgumentParser(description='StudyTracker-Task-Import: Datei sicher in die Polybox-Inbox legen')
    p.add_argument('--user',required=True,help='StudyTracker-Benutzername')
    p.add_argument('--file',required=True,type=Path,help='JSON-Quelldatei aus ChatGPT')
    args=p.parse_args()
    if not re.fullmatch('[a-z][a-z0-9_-]{2,23}',args.user):
        p.error('Benutzername ungültig')
    raw=args.file.read_bytes()
    if len(raw)>1024*1024: p.error('JSON-Datei größer als 1 MB')
    try:
        payload=json.loads(raw.decode('utf-8'))
        if not isinstance(payload,dict) or payload.get('format')!='studytracker.tasks.v1' or not isinstance(payload.get('tasks'),list):
            raise ValueError('Nicht das StudyTracker-Aufgaben-JSON-Format')
    except (UnicodeError,ValueError) as e:
        p.error(str(e))
    inbox=DATA_DIR/'inbox'/args.user
    inbox.mkdir(parents=True,exist_ok=True)
    name=f'import-{uuid.uuid4().hex[:12]}.json'
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=inbox,prefix='.incoming-',suffix='.tmp',delete=False) as f:
            temporary=Path(f.name)
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary,inbox/name)
    finally:
        if temporary and temporary.exists(): temporary.unlink()
    print(f'Abgelegt: {inbox/name}')
    print('Die laufende App importiert sie automatisch und zeigt neue Karten im Kanban-Board.')

if __name__=='__main__':main()
