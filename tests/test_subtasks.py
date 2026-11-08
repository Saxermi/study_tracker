"""Bidirectional independent subtasks, optional estimates, imports and migration."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server


class SubtaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.a=mock.patch.object(server,'DATA_DIR',Path(self.tmp.name)/'data')
        self.b=mock.patch.object(server,'BACKUP_DIR',Path(self.tmp.name)/'backup')
        self.a.start();self.b.start();server.SESSIONS.clear()
        self.uid=server.create_user({'display_name':'Test','username':'test','password':'secure-passphrase'},first=True)['id']

    def tearDown(self):
        self.b.stop();self.a.stop();server.SESSIONS.clear();self.tmp.cleanup()

    def new(self,title,parent_id=None,estimated=None):
        return server.mutate(self.uid,'POST','/api/tasks',{'title':title,'subject_id':'mathe','parent_id':parent_id,'planned_minutes':estimated})['task_id']

    def rows(self):
        return {t['id']:t for t in server.load_profile(self.uid)['tasks']}

    def patch(self,id,**data):
        return server.mutate(self.uid,'PATCH','/api/tasks/'+id,data)

    def test_children_are_individual_tasks_auto_complete_parent(self):
        p=self.new('Aufgabe 1',estimated=120)
        children=[self.new(n,p,estimated) for n,estimated in (('B',40),('C',None),('D',30))]
        for c in children[:2]:self.patch(c,status='done')
        self.assertEqual(self.rows()[p]['status'],'doing')
        self.assertIsNone(self.rows()[children[1]]['planned_minutes'])
        self.patch(children[2],status='done')
        rows=self.rows();self.assertEqual(rows[p]['status'],'done')
        self.assertIsNotNone(rows[p]['completed_at'])
        self.patch(children[1],status='todo')
        rows=self.rows();self.assertEqual(rows[p]['status'],'doing')
        self.assertEqual(rows[children[0]]['status'],'done')

    def test_parent_complete_and_reopen_cascades(self):
        p=self.new('All parts')
        cs=[self.new('B',p),self.new('C',p)]
        self.patch(p,status='done')
        self.assertEqual({self.rows()[t]['status'] for t in [p,*cs]},{'done'})
        self.patch(p,status='todo')
        self.assertEqual({self.rows()[t]['status'] for t in [p,*cs]},{'todo'})

    def test_editing_parent_metadata_does_not_reset_child_statuses(self):
        p=self.new('Assignment 1',estimated=120)
        b=self.new('Part B',p,estimated=40)
        c=self.new('Part C',p,estimated=30)
        self.patch(b,status='done')
        before={i:self.rows()[i]['status'] for i in (b,c)}
        self.assertEqual(self.rows()[p]['status'],'doing')
        # PATCH used by "For today" and by task edit dialog must be independent.
        self.patch(p,planned_for='2026-11-08',title='Assignment 1 updated',planned_minutes=140)
        after=self.rows()
        self.assertEqual({i:after[i]['status'] for i in (b,c)},before)
        self.assertEqual(after[p]['planned_for'],'2026-11-08')
        self.assertEqual(after[p]['planned_minutes'],140)

    def test_moving_parent_to_in_progress_does_not_start_children(self):
        p=self.new('Assignment')
        b=self.new('Part B',p)
        c=self.new('Part C',p)
        self.patch(p,status='doing')
        rows=self.rows()
        self.assertEqual(rows[p]['status'],'doing')
        self.assertEqual(rows[b]['status'],'todo')
        self.assertEqual(rows[c]['status'],'todo')

    def test_parent_reopen_via_new_child(self):
        p=self.new('Parent')
        c=self.new('B',p)
        self.patch(c,status='done')
        self.assertEqual(self.rows()[p]['status'],'done')
        self.new('C',p)
        self.assertEqual(self.rows()[p]['status'],'doing')

    def test_invalid_relationships_do_not_mutate_data(self):
        p=self.new('P')
        c=self.new('C',p)
        with self.assertRaises(server.ClientError):self.patch(p,parent_id=c)
        with self.assertRaises(server.ClientError):self.patch(c,parent_id=c)
        with self.assertRaises(server.ClientError):self.patch(c,subject_id='info')
        self.assertEqual(self.rows()[c]['parent_id'],p)
        self.assertEqual(self.rows()[c]['subject_id'],'mathe')

    def test_parent_delete_preserves_independent_child(self):
        p=self.new('P')
        c=self.new('C',p)
        server.mutate(self.uid,'DELETE','/api/tasks/'+p,{})
        self.assertIsNone(self.rows()[c]['parent_id'])

    def test_agent_relationships_out_of_order_and_replay(self):
        payload={'format':'studytracker.tasks.v1','batch_id':'my-mail-1','tasks':[
            {'external_id':'mail:C','subject':'Mathematik','title':'C','parent_external_id':'mail:P'},
            {'external_id':'mail:P','subject':'Mathematik','title':'Parent','planned_minutes':90},
            {'external_id':'mail:B','subject':'Mathematik','title':'B','parent_external_id':'mail:P','planned_minutes':20}]}
        outcome=server.mutate(self.uid,'POST','/api/import/tasks',payload)
        self.assertEqual(outcome['added'],3)
        rows=self.rows();root=next(t for t in rows.values() if t['external_id']=='mail:P')
        self.assertEqual(len([t for t in rows.values() if t['parent_id']==root['id']]),2)
        self.assertTrue(server.mutate(self.uid,'POST','/api/import/tasks',payload)['already_imported'])

    def test_bad_agent_parent_fails_atomically(self):
        payload={'format':'studytracker.tasks.v1','batch_id':'bad-parent','tasks':[
            {'external_id':'orphan','subject':'Analysis 3','title':'Orphan','parent_external_id':'unknown'}]}
        with self.assertRaises(server.ClientError):server.mutate(self.uid,'POST','/api/import/tasks',payload)
        self.assertEqual(self.rows(),{})
        self.assertNotIn('Analysis 3',[s['name'] for s in server.load_profile(self.uid)['subjects']])

    def test_export_backup_restores_all_links(self):
        p=self.new('P');c=self.new('B',p,estimated=None)
        data=server.load_profile(self.uid)
        server.mutate(self.uid,'POST','/api/import/backup',{'app':'StudyTracker','version':2,'data':data})
        self.assertEqual(self.rows()[c]['parent_id'],p)
        self.assertIn('Hauptaufgabe ID',server.export_csv(data,'tasks').decode('utf-8'))


if __name__=='__main__':unittest.main()
