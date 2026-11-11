"""Regression tests for separate self- and GPT-based exercise ratings."""
import csv,io,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
class SourceSeparationTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.data=mock.patch.object(server,'DATA_DIR',Path(self.tmp.name)/'data')
  self.backup=mock.patch.object(server,'BACKUP_DIR',Path(self.tmp.name)/'backup')
  self.data.start();self.backup.start();server.SESSIONS.clear()
  self.user=server.create_user({'display_name':'User','username':'student','password':'strongpassword123'},first=True)['id']
  self.tid=server.mutate(self.user,'POST','/api/tasks',{'title':'Simplex','subject_id':'mathe'})['task_id']
 def tearDown(self):
  self.backup.stop();self.data.stop();server.SESSIONS.clear();self.tmp.cleanup()
 def patch(self,payload):return server.mutate(self.user,'PATCH','/api/tasks/'+self.tid+'/review',payload)
 def saved(self):return server.task(server.load_profile(self.user),self.tid)
 def test_independent_fields(self):
  self.patch({'self':{'difficulty':2},'gpt':{'difficulty':3,'outcome':'partial','issue':'concept','help_total':4,'help_chatgpt':4}})
  task=self.saved()
  self.assertEqual(task['exercise_review']['difficulty'],2)
  self.assertEqual(task['exercise_review_gpt']['difficulty'],3)
  self.patch({'difficulty':4})
  self.assertEqual(self.saved()['exercise_review_gpt']['difficulty'],3)
 def test_gpt_only_and_clear(self):
  self.patch({'gpt':{'difficulty':3}})
  self.assertIsNone(self.saved()['exercise_review'])
  self.patch({'self':{'help_total':0}})
  self.assertEqual(self.saved()['exercise_review_gpt']['difficulty'],3)
  self.patch({'gpt':None})
  self.assertIsNone(self.saved()['exercise_review_gpt'])
 def test_invalid_combined_request_is_atomic(self):
  self.patch({'self':{'difficulty':2},'gpt':{'difficulty':3}})
  with self.assertRaises(server.ClientError):self.patch({'self':{'difficulty':5},'gpt':{'difficulty':6}})
  self.assertEqual(self.saved()['exercise_review']['difficulty'],2)
 def test_export_and_backup(self):
  self.patch({'self':{'difficulty':2},'gpt':{'difficulty':3,'help_total':4,'help_chatgpt':4}})
  state=server.load_profile(self.user)
  backup=server.validate_backup(state)
  self.assertEqual(server.task(backup,self.tid)['exercise_review_gpt']['difficulty'],3)
  old=server.load_profile(self.user);old['tasks'][0].pop('exercise_review_gpt',None)
  self.assertIsNone(server.task(server.validate_backup(old),self.tid)['exercise_review_gpt'])
  rows=list(csv.reader(io.StringIO(server.export_csv(state,'tasks').decode('utf-8-sig')),delimiter=';'))
  idx={k:i for i,k in enumerate(rows[0])}
  self.assertEqual(rows[1][idx['Schwierigkeit (1-5)']],'2')
  self.assertEqual(rows[1][idx['GPT Schwierigkeit (1-5)']],'3')
if __name__=='__main__':unittest.main()
