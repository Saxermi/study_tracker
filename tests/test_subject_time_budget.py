"""Weekly subject time-budget regressions: local-only, independent from task completion."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server


class SubjectTimeBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.p1=mock.patch.object(server,'DATA_DIR',Path(self.temp.name)/'data')
        self.p2=mock.patch.object(server,'BACKUP_DIR',Path(self.temp.name)/'backups')
        self.p1.start();self.p2.start()
        server.SESSIONS.clear()
        self.uid=server.create_user({'display_name':'Student','username':'student','password':'secure-password-123'},first=True)['id']

    def tearDown(self):
        self.p2.stop();self.p1.stop();server.SESSIONS.clear();self.temp.cleanup()

    def read(self):
        return server.load_profile(self.uid)

    def patch(self,week='2026-11-16',**fields):
        return server.mutate(self.uid,'PATCH','/api/productivity/weekly-plan',{'week_start':week,**fields})

    def test_subject_budget_requires_no_tasks_and_is_week_specific(self):
        self.patch(subject_minutes={'mathe':240,'info':120})
        plan=self.read()['productivity']['weekly_plans']['2026-11-16']
        self.assertEqual(plan['subject_minutes'],{'mathe':240,'info':120})
        self.assertEqual(plan['outcome_ids'],[])
        self.assertEqual(plan['days'],{})
        self.assertEqual(self.read()['tasks'],[])
        self.patch(week='2026-11-23',subject_minutes={'physik':90})
        self.assertEqual(self.read()['productivity']['weekly_plans']['2026-11-16']['subject_minutes']['mathe'],240)
        self.assertEqual(self.read()['productivity']['weekly_plans']['2026-11-23']['subject_minutes'],{'physik':90})

    def test_partial_weekly_patch_keeps_subject_targets_and_other_fields(self):
        tid=server.mutate(self.uid,'POST','/api/tasks',{'title':'Long math problem','subject_id':'mathe'})['task_id']
        self.patch(subject_minutes={'mathe':240},outcome_ids=[tid],days={'2026-11-18':[tid]})
        self.patch(outcome_ids=[])
        plan=self.read()['productivity']['weekly_plans']['2026-11-16']
        self.assertEqual(plan['subject_minutes'],{'mathe':240})
        self.assertEqual(plan['days'],{'2026-11-18':[tid]})
        self.assertEqual(plan['outcome_ids'],[])
        self.patch(subject_minutes={'mathe':180})
        self.assertEqual(self.read()['productivity']['weekly_plans']['2026-11-16']['subject_minutes'],{'mathe':180})

    def test_invalid_weekly_targets_rejected_without_persistence(self):
        self.patch(subject_minutes={'mathe':240})
        before=copy.deepcopy(self.read()['productivity'])
        values=[
            {'missing':60},{'mathe':-1},{'mathe':3.5},{'mathe':'invalid'},
            {'mathe':True},{'mathe':10081},{'mathe':8400,'info':1800},
            'text',[],{str(n):1 for n in range(501)}
        ]
        for value in values:
            with self.subTest(value=str(value)[:60]),self.assertRaises(server.ClientError):
                self.patch(subject_minutes=value)
            self.assertEqual(self.read()['productivity'],before)

    def test_budget_can_be_cleared_without_affecting_sessions_or_tasks(self):
        tid=server.mutate(self.uid,'POST','/api/tasks',{'title':'Hard problem','subject_id':'mathe'})['task_id']
        server.mutate(self.uid,'POST','/api/sessions',{
            'subject_id':'mathe','task_id':tid,'title':'Math study',
            'started_at':'2026-11-16T12:00:00+01:00','duration_seconds':4*3600,
            'break_seconds':600,'tags':[]
        })
        self.patch(subject_minutes={'mathe':240})
        self.patch(subject_minutes={'mathe':0,'info':None})
        state=self.read()
        self.assertEqual(state['productivity']['weekly_plans']['2026-11-16']['subject_minutes'],{})
        self.assertEqual(state['tasks'][0]['status'],'todo')
        self.assertEqual(len(state['sessions']),1)
        self.assertEqual(state['sessions'][0]['duration_seconds'],4*3600)
        self.assertEqual(state['sessions'][0]['break_seconds'],600)

    def test_backup_roundtrip_and_old_weekly_plans(self):
        self.patch(subject_minutes={'mathe':240})
        data=copy.deepcopy(self.read())
        self.assertEqual(server.validate_backup(data)['productivity'],data['productivity'])
        older=copy.deepcopy(data)
        older['productivity']['weekly_plans']['2026-11-16'].pop('subject_minutes')
        normalized=server.validate_backup(older)
        self.assertEqual(normalized['productivity']['weekly_plans']['2026-11-16']['subject_minutes'],{})
        invalid=copy.deepcopy(data)
        invalid['productivity']['weekly_plans']['2026-11-16']['subject_minutes']={'unknown':240}
        with self.assertRaises(server.ClientError):
            server.validate_backup(invalid)


if __name__=='__main__':
    unittest.main()
