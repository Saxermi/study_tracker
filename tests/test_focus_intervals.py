"""Exact focus timeline persistence, including pauses and JSON backups."""
import sys,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class FocusIntervalTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.d=patch.object(server,'DATA_DIR',Path(self.tmp.name)/'data');self.b=patch.object(server,'BACKUP_DIR',Path(self.tmp.name)/'backups');self.d.start();self.b.start();server.SESSIONS.clear()
  self.uid=server.create_user({'display_name':'T','username':'demo','password':'goodpassword000'},first=True)['id']
 def tearDown(self):self.d.stop();self.b.stop();self.tmp.cleanup();server.SESSIONS.clear()
 def test_timer_pause_and_resume_save_exact_intervals(self):
  server.mutate(self.uid,'POST','/api/timer/start',{'subject_id':'mathe'})
  s=server.load_profile(self.uid);old=server.now()-timedelta(hours=2,minutes=15)
  s['active_timer']['first_started_at']=old.isoformat();s['active_timer']['mode_since']=old.isoformat();server.save_profile(self.uid,s)
  with patch.object(server,'now',return_value=server.now()-timedelta(minutes=10)):
   server.mutate(self.uid,'POST','/api/timer/pause',{})
  s=server.load_profile(self.uid)
  self.assertEqual(len(s['active_timer']['focus_intervals']),1)
  self.assertTrue(s['active_timer']['focus_seconds']>7000)
  with patch.object(server,'now',return_value=server.now()-timedelta(minutes=5)):
   server.mutate(self.uid,'POST','/api/timer/resume',{})
  server.mutate(self.uid,'POST','/api/timer/stop',{})
  s=server.load_profile(self.uid);entry=s['sessions'][0]
  self.assertEqual(len(entry['focus_intervals']),2)
  self.assertTrue(entry['duration_seconds']>7200)
  restored=server.validate_backup(s)
  self.assertEqual(entry['focus_intervals'],restored['sessions'][0]['focus_intervals'])
 def test_invalid_interval_rejected_and_edit_invalidates_exact_timing(self):
  from datetime import timedelta
  at=server.now()-timedelta(hours=1)
  server.mutate(self.uid,'POST','/api/sessions',{'subject_id':'mathe','started_at':at.isoformat(),'duration_seconds':60})
  s=server.load_profile(self.uid);eid=s['sessions'][0]['id']
  s['sessions'][0]['focus_intervals']=[{'started_at':at.isoformat(),'ended_at':(at+timedelta(minutes=2)).isoformat()}]
  with self.assertRaises(server.ClientError):server.validate_backup(s)
  s['sessions'][0]['focus_intervals']=[{'started_at':at.isoformat(),'ended_at':(at+timedelta(minutes=1)).isoformat()}]
  server.save_profile(self.uid,s)
  server.mutate(self.uid,'PATCH','/api/sessions/'+eid,{'duration_seconds':120})
  self.assertEqual(server.load_profile(self.uid)['sessions'][0]['focus_intervals'],[])
if __name__=='__main__':unittest.main()
