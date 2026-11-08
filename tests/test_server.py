"""StudyTracker 2 regression tests; run `python3 -m unittest discover -s tests -v`."""
from __future__ import annotations

import copy
import io
import json
import os
import time
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.override = mock.patch.object(server, 'DATA_DIR', self.root / 'data')
        self.backup_override = mock.patch.object(server, 'BACKUP_DIR', self.root / 'backups')
        self.override.start(); self.backup_override.start()
        server.SESSIONS.clear()
        self.u = server.create_user({'display_name': 'Alex', 'username': 'alex', 'password': 'secure-password-123'}, first=True)
        self.s = server.load_profile(self.u['id'])

    def tearDown(self):
        self.override.stop(); self.backup_override.stop()
        server.SESSIONS.clear()
        self.temp.cleanup()

    def task_data(self, title='Übungsblatt', estimate=60):
        return {'subject_id': 'mathe', 'title': title, 'planned_minutes': estimate, 'description': 'Aufgabe lösen', 'tags':['uebungen'], 'priority':'high'}

    def test_account_password_not_plaintext(self):
        raw = server.accounts_path().read_text('utf-8')
        self.assertNotIn('secure-password-123', raw)
        user, token = server.sign_in('alex','secure-password-123')
        self.assertEqual(user['username'], 'alex')
        self.assertIn(token,server.SESSIONS)
        with self.assertRaises(server.ClientError):
            server.sign_in('alex','invalid')

    def test_separate_profiles(self):
        u2=server.create_user({'display_name':'Sam','username':'sam','password':'another-password-111'}, first=False)
        server.mutate(self.u['id'],'POST','/api/tasks',self.task_data())
        self.assertEqual(len(server.load_profile(self.u['id'])['tasks']),1)
        self.assertEqual(server.load_profile(u2['id'])['tasks'],[])

    def test_tasks_kanban_and_estimation(self):
        a=server.mutate(self.u['id'],'POST','/api/tasks',self.task_data())
        tid=a['task_id']
        self.assertEqual(server.load_profile(self.u['id'])['tasks'][0]['planned_minutes'],60)
        server.mutate(self.u['id'],'PATCH','/api/tasks/'+tid,{'status':'doing'})
        self.assertEqual(server.load_profile(self.u['id'])['tasks'][0]['status'],'doing')
        server.mutate(self.u['id'],'PATCH','/api/tasks/'+tid,{'status':'done'})
        self.assertIsNotNone(server.load_profile(self.u['id'])['tasks'][0]['completed_at'])

    def test_multiple_sessions_aggregate_per_task(self):
        tid=server.mutate(self.u['id'],'POST','/api/tasks',self.task_data())['task_id']
        for sec in (25*60,45*60):
            server.mutate(self.u['id'],'POST','/api/sessions',{'subject_id':'mathe','task_id':tid,'title':'Mathe',
                           'started_at':'2026-11-04T13:00:00+01:00','duration_seconds':sec,'tags':[]})
        s=server.load_profile(self.u['id'])
        self.assertEqual(sum(r['duration_seconds'] for r in s['sessions'] if r['task_id']==tid),70*60)
        csv_bytes=server.export_csv(s,'tasks')
        self.assertIn('70,00',csv_bytes.decode('utf-8'))
        self.assertIn('10,00',csv_bytes.decode('utf-8'))

    def test_timer_focus_and_breaks(self):
        tid=server.mutate(self.u['id'],'POST','/api/tasks',self.task_data())['task_id']
        server.mutate(self.u['id'],'POST','/api/timer/start',{'task_id':tid})
        s=server.load_profile(self.u['id'])
        t=s['active_timer']
        t['mode_since']=(server.now()-server.timedelta(seconds=120)).isoformat()
        server.save_profile(self.u['id'],s)
        server.mutate(self.u['id'],'POST','/api/timer/break-start',{})
        s=server.load_profile(self.u['id']);self.assertGreaterEqual(s['active_timer']['focus_seconds'],119)
        s['active_timer']['mode_since']=(server.now()-server.timedelta(seconds=35)).isoformat()
        server.save_profile(self.u['id'],s)
        server.mutate(self.u['id'],'POST','/api/timer/break-end',{})
        s=server.load_profile(self.u['id']);self.assertGreaterEqual(s['active_timer']['break_seconds'],34)
        server.mutate(self.u['id'],'POST','/api/timer/pause',{})
        server.mutate(self.u['id'],'POST','/api/timer/resume',{})
        server.mutate(self.u['id'],'POST','/api/timer/stop',{})
        s=server.load_profile(self.u['id']);self.assertIsNone(s['active_timer'])
        self.assertEqual(s['sessions'][0]['task_id'],tid)
        self.assertEqual(len(s['sessions'][0]['breaks']),1)
        self.assertGreaterEqual(s['sessions'][0]['duration_seconds'],119)
        self.assertGreaterEqual(s['sessions'][0]['break_seconds'],34)
        csv_text=server.export_csv(s,'sessions').decode('utf-8')
        self.assertIn('Pausenintervalle',csv_text)
        self.assertIn(' bis ',csv_text)

    def test_agent_import_replay_and_external_dedup(self):
        batch={'format':'studytracker.tasks.v1','batch_id':'email-20261108-1','tasks':[
            {'external_id':'email-1:task-1','subject':'Analysis II','title':'Übungsblatt 4 lösen','planned_minutes':75,'tags':['Übung'],'due_date':'2026-11-20','priority':'high'},
            {'external_id':'email-1:task-2','subject':'Analysis II','title':'Kapitel 3 lesen','planned_minutes':40,'tags':['Lesen']} ]}
        first=server.mutate(self.u['id'],'POST','/api/import/tasks',batch)
        self.assertEqual(first['added'],2)
        second=server.mutate(self.u['id'],'POST','/api/import/tasks',batch)
        self.assertTrue(second['already_imported'])
        other=copy.deepcopy(batch);other['batch_id']='email-20261108-2'
        third=server.mutate(self.u['id'],'POST','/api/import/tasks',other)
        self.assertEqual(third['skipped'],2)
        self.assertEqual(len(server.load_profile(self.u['id'])['tasks']),2)

    def test_invalid_agent_payload_atomic(self):
        payload={'format':'studytracker.tasks.v1','batch_id':'bad-batch','tasks':[
            {'external_id':'x1','title':'Valid','subject':'Biologie','planned_minutes':45},
            {'external_id':'x2','title':'Invalid','subject':'Biologie','planned_minutes':-500}]}
        with self.assertRaises(server.ClientError):
            server.mutate(self.u['id'],'POST','/api/import/tasks',payload)
        self.assertEqual(len(server.load_profile(self.u['id'])['tasks']),0)
        self.assertNotIn('Biologie',[s['name'] for s in server.load_profile(self.u['id'])['subjects']])

    def test_agent_inbox_processed_and_rejected(self):
        folder=server.DATA_DIR/'inbox'/'alex';folder.mkdir(parents=True, exist_ok=True)
        batch={'format':'studytracker.tasks.v1','batch_id':'from-inbox-1', 'tasks':[{'external_id':'abc-1','subject':'Mathematik','title':'Ableitungen üben','planned_minutes':20}]}
        (folder/'good.json').write_text(json.dumps(batch),'utf-8')
        (folder/'bad.json').write_text('{bad json','utf-8')
        for file in (folder/'good.json',folder/'bad.json'):
            os.utime(file,(time.time()-10,time.time()-10))
        result=server.ingest_inbox_once()
        self.assertEqual(len(result),2)
        self.assertEqual(len(server.load_profile(self.u['id'])['tasks']),1)
        self.assertEqual(len(list((folder/'processed').glob('*.json'))),1)
        self.assertEqual(len(list((folder/'rejected').glob('*.json'))),1)
        self.assertTrue(list((folder/'rejected').glob('*.error.txt')))

    def test_export_backup_restore(self):
        server.mutate(self.u['id'],'POST','/api/tasks',self.task_data())
        s=server.load_profile(self.u['id'])
        body={'app':'StudyTracker','version':2,'data':{**s,'active_timer':None}}
        server.mutate(self.u['id'],'POST','/api/import/backup',body)
        self.assertEqual(len(server.load_profile(self.u['id'])['tasks']),1)
        with self.assertRaises(server.ClientError):
            server.mutate(self.u['id'],'POST','/api/import/backup',{'app':'StudyTracker','version':2,'filtered':True,'data':s})

    def test_csv_formula_injection_protection(self):
        server.mutate(self.u['id'],'POST','/api/tasks',self.task_data('=HYPERLINK("example")'))
        csv=server.export_csv(server.load_profile(self.u['id']),'tasks').decode('utf-8')
        self.assertIn("'=HYPERLINK",csv)

    def test_old_state_migration(self):
        # Simulate a first install upgrade from StudyTracker 1.
        old={"version":1,"subjects":[{"id":"chem","name":"Chemie","color":"#7766AA","weekly_goal_minutes":60,"archived":False}],
             "tags":[],"sessions":[],"settings":{"weekly_goal_minutes":300}}
        (server.DATA_DIR/'state.json').write_text(json.dumps(old),'utf-8')
        p=server.migrate_v1_if_needed()
        self.assertEqual(p['subjects'][0]['name'],'Chemie')
        self.assertTrue((server.DATA_DIR/'legacy-state-v1.json').exists())

if __name__=='__main__': unittest.main()
