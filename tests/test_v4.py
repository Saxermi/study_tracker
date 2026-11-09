"""Regression tests for the new v4 categories, persistence and backwards compatibility."""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class V4Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.d=mock.patch.object(server,'DATA_DIR',Path(self.temp.name)/'data')
        self.b=mock.patch.object(server,'BACKUP_DIR',Path(self.temp.name)/'backups')
        self.d.start();self.b.start();server.SESSIONS.clear()
        self.user=server.create_user({'display_name':'Demo','username':'demo','password':'demopassword123'},first=True)
        self.uid=self.user['id']
    def tearDown(self):
        self.d.stop();self.b.stop();server.SESSIONS.clear();self.temp.cleanup()
    def test_categories_seeded(self):
        tags=server.load_profile(self.uid)['tags']
        self.assertIn('Vorlesung',[t['name'] for t in tags])
        self.assertIn('Videos',[t['name'] for t in tags])
        self.assertIn('Übungen',[t['name'] for t in tags])
    def test_existing_profile_gets_categories_without_duplicate(self):
        state=server.load_profile(self.uid)
        state['tags']=[t for t in state['tags'] if t['name'] not in ['Vorlesung','Videos']]
        state['settings'].pop('v4_default_categories_initialized',None)
        server.save_profile(self.uid,state)
        a=server.load_profile(self.uid);b=server.load_profile(self.uid)
        self.assertEqual(len([t for t in a['tags'] if t['name']=='Vorlesung']),1)
        self.assertEqual(len([t for t in b['tags'] if t['name']=='Vorlesung']),1)
        server.save_profile(self.uid,b)
        b['tags']=[tag for tag in b['tags'] if tag['name']!='Vorlesung']
        server.save_profile(self.uid,b)
        self.assertNotIn('Vorlesung',[t['name'] for t in server.load_profile(self.uid)['tags']])
    def test_manual_session_category_and_csv_export(self):
        now=datetime.now(timezone.utc).isoformat()
        result=server.mutate(self.uid,'POST','/api/sessions',{'subject_id':'mathe','title':'NumCSE lecture','started_at':now,'duration_seconds':3600,'tags':['pruefung'],'category_tag_id':'vorlesung'})
        state=server.load_profile(self.uid)
        s=state['sessions'][0]
        self.assertEqual(s['category_tag_id'],'vorlesung')
        self.assertIn('pruefung',s['tags'])
        self.assertIn('vorlesung',s['tags'])
        exported=server.export_csv(state,'sessions').decode('utf-8')
        self.assertIn('Kategorie',exported)
        self.assertIn('Vorlesung',exported)
        # An explicitly uncategorized session must not inherit an unrelated tag.
        original=state['sessions'][0]
        server.mutate(self.uid,'PATCH','/api/sessions/'+original['id'],{'category_tag_id':None})
        uncat=server.load_profile(self.uid)['sessions'][0]
        self.assertIsNone(uncat['category_tag_id'])
        self.assertIn('Ohne Kategorie',server.export_csv(server.load_profile(self.uid),'sessions').decode('utf-8'))
        restored=server.validate_backup(state)
        self.assertEqual(restored['sessions'][0]['category_tag_id'],'vorlesung')
        with self.assertRaises(server.ClientError):
            server.mutate(self.uid,'POST','/api/sessions',{'subject_id':'mathe','title':'bad','started_at':now,'duration_seconds':90,'tags':[],'category_tag_id':'nonexistent'})
    def test_deleting_a_category_clears_session_reference(self):
        now=datetime.now(timezone.utc).isoformat()
        server.mutate(self.uid,'POST','/api/sessions',{'subject_id':'mathe','title':'lecture','started_at':now,'duration_seconds':1200,'tags':['vorlesung'],'category_tag_id':'vorlesung'})
        server.mutate(self.uid,'DELETE','/api/tags/vorlesung',{})
        restored=server.load_profile(self.uid)
        self.assertIsNone(restored['sessions'][0]['category_tag_id'])
        self.assertNotIn('Vorlesung',[t['name'] for t in restored['tags']])

    def test_task_timer_category_override_and_default(self):
        tid=server.mutate(self.uid,'POST','/api/tasks',{'subject_id':'mathe','title':'Vorlesung 4','tags':['uebungen'],'planned_minutes':60})['task_id']
        server.mutate(self.uid,'POST','/api/timer/start',{'task_id':tid,'category_tag_id':'vorlesung'})
        state=server.load_profile(self.uid)
        self.assertEqual(state['active_timer']['category_tag_id'],'vorlesung')
        self.assertIn('vorlesung',state['active_timer']['tags'])
        server.mutate(self.uid,'POST','/api/timer/discard',{})
        server.mutate(self.uid,'POST','/api/timer/start',{'task_id':tid})
        self.assertEqual(server.load_profile(self.uid)['active_timer']['category_tag_id'],'uebungen')

if __name__=='__main__':unittest.main()
