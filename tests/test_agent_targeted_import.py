"""Agent-generated tasks must resolve explicitly selected existing modules and parents."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class TargetedImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = mock.patch.object(server, 'DATA_DIR', Path(self.tmp.name) / 'data')
        self.backup = mock.patch.object(server, 'BACKUP_DIR', Path(self.tmp.name) / 'backups')
        self.data.start(); self.backup.start(); server.SESSIONS.clear()
        self.uid = server.create_user({'display_name':'Learner','username':'learner','password':'strong-test-password'}, first=True)['id']
        self.subject = 'mathe'
        self.parent = server.mutate(self.uid,'POST','/api/tasks',{'subject_id':self.subject,'title':'Exercise Sheet 1'})['task_id']

    def tearDown(self):
        self.data.stop(); self.backup.stop(); server.SESSIONS.clear(); self.tmp.cleanup()

    def make_import(self, tasks, batch='source-one'):
        return server.mutate(self.uid,'POST','/api/import/tasks',{'format':'studytracker.tasks.v1','batch_id':batch,'tasks':tasks})

    def test_subject_id_only_maps_to_existing_subject_without_creating(self):
        before=server.load_profile(self.uid)
        self.make_import([{'external_id':'mail:1','subject_id':'mathe','title':'Read chapter'}])
        after=server.load_profile(self.uid)
        self.assertEqual(len(after['subjects']),len(before['subjects']))
        self.assertEqual(after['tasks'][-1]['subject_id'],'mathe')

    def test_existing_parent_id_attaches_independent_subtasks(self):
        self.make_import([{'external_id':'mail:part-b','subject_id':'mathe','parent_id':self.parent,'title':'Solve B'},
                          {'external_id':'mail:part-c','subject_id':'mathe','parent_id':self.parent,'title':'Solve C'}])
        s=server.load_profile(self.uid)
        parts=[x for x in s['tasks'] if x.get('parent_id')==self.parent]
        self.assertEqual({x['title'] for x in parts},{'Solve B','Solve C'})
        self.assertTrue(all(x['status']=='todo' for x in parts))
        self.assertEqual(self.make_import([{'external_id':'mail:part-b','subject_id':'mathe','parent_id':self.parent,'title':'Solve B'}],batch='source-two')['skipped'],1)

    def test_new_parent_uses_external_id_in_any_order(self):
        self.make_import([{'external_id':'mail:a','subject_id':'mathe','parent_external_id':'mail:sheet','title':'Solve A'},
                          {'external_id':'mail:sheet','subject_id':'mathe','title':'Sheet'}])
        tasks={x['external_id']:x for x in server.load_profile(self.uid)['tasks'] if x.get('external_id')}
        self.assertEqual(tasks['mail:a']['parent_id'],tasks['mail:sheet']['id'])

    def test_wrong_ids_and_conflicting_context_are_rejected_atomically(self):
        bad=[{'external_id':'x:1','subject_id':'does-not-exist','title':'Nope'},
             {'external_id':'x:2','subject_id':'mathe','subject':'Different name','title':'Nope'},
             {'external_id':'x:3','subject_id':'mathe','semester':'Wrong semester','title':'Nope'},
             {'external_id':'x:4','subject_id':'mathe','parent_id':'does-not-exist','title':'Nope'},
             {'external_id':'x:5','subject_id':'mathe','parent_id':self.parent,'parent_external_id':'other:parent','title':'Nope'},
             {'external_id':'x:6','title':'No subject'}]
        baseline=server.load_profile(self.uid)
        for i, item in enumerate(bad):
            with self.subTest(item=item), self.assertRaises(server.ClientError):
                self.make_import([{'external_id':f'valid:{i}','subject_id':'mathe','title':'Should not persist'},item],batch=f'bad:{i}')
            now=server.load_profile(self.uid)
            self.assertEqual(now['tasks'],baseline['tasks'])
            self.assertEqual(now['subjects'],baseline['subjects'])
            self.assertEqual(now['imports'],baseline['imports'])

    def test_cross_subject_parent_rejected(self):
        other=server.mutate(self.uid,'POST','/api/subjects',{'name':'Physics'})
        other_id=next(x['id'] for x in server.load_profile(self.uid)['subjects'] if x['name']=='Physics')
        with self.assertRaises(server.ClientError):
            self.make_import([{'external_id':'x:1','subject_id':other_id,'parent_id':self.parent,'title':'Wrong parent'}])

    def test_parent_of_parent_disallowed(self):
        self.make_import([{'external_id':'x:child','subject_id':'mathe','parent_id':self.parent,'title':'Child'}])
        child=next(t for t in server.load_profile(self.uid)['tasks'] if t.get('external_id')=='x:child')
        with self.assertRaises(server.ClientError):
            self.make_import([{'external_id':'x:grandchild','subject_id':'mathe','parent_id':child['id'],'title':'Grandchild'}],batch='second')

    def test_old_name_based_import_still_works(self):
        self.make_import([{'external_id':'legacy:1','subject':'Mathematik','title':'Old format'}])
        self.assertEqual(server.load_profile(self.uid)['tasks'][-1]['subject_id'],'mathe')

    def test_schema_accepts_both_allocation_methods(self):
        schema=json.loads((Path(__file__).parents[1]/'schemas/tasks-import.schema.json').read_text())
        fields=schema['$defs']['task']
        self.assertIn('subject_id',fields['properties'])
        self.assertIn('parent_id',fields['properties'])
        self.assertEqual(fields['anyOf'],[{'required':['subject']},{'required':['subject_id']}])

if __name__ == '__main__':unittest.main()
