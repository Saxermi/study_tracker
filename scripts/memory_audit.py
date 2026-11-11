#!/usr/bin/env python3
"""Local profile size audit; reports only totals, never account or task content."""
import json,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
data=Path(os.environ.get('STUDYTRACKER_DATA_DIR',root/'data')).expanduser()
files=sorted((data/'profiles').glob('*.json'))
total_bytes=total_tasks=total_sessions=0
for path in files:
 try:
  size=path.stat().st_size
  d=json.loads(path.read_text(encoding='utf-8'))
  total_bytes+=size
  total_tasks+=len(d.get('tasks',[]))
  total_sessions+=len(d.get('sessions',[]))
 except (OSError,ValueError) as e:
  print('Could not inspect a profile:',type(e).__name__)
print('Profiles:',len(files))
print('Tasks:',total_tasks,'Sessions:',total_sessions)
print('On-disk JSON total: %.2f MiB'%(total_bytes/1048576))
print('Browser RAM and running server RSS are not measured by this script.')
