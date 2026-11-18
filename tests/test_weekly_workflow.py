"""Regression tests for optional weekly planning, lecture attendance and focus completion."""
from __future__ import annotations
import copy
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server


class WeeklyWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p1=mock.patch.object(server,'DATA_DIR',Path(self.tmp.name)/'data')
        self.p2=mock.patch.object(server,'BACKUP_DIR',Path(self.tmp.name)/'backup')
        self.p1.start();self.p2.start()
        server.SESSIONS.clear()
        self.uid=server.create_user({'display_name':'Tester','username':'tester','password':'secure-password-123'},first=True)['id']

    def tearDown(self):
        self.p2.stop();self.p1.stop();server.SESSIONS.clear();self.tmp.cleanup()

    def create_task(self,title,parent=None):
        return server.mutate(self.uid,'POST','/api/tasks',{'title':title,'subject_id':'mathe','parent_id':parent})['task_id']

    def state(self):
        return server.load_profile(self.uid)

    def lecture_body(self,**changes):
        return dict({'title':'Analysis lecture','subject_id':'mathe','weekday':0,'start_time':'09:00',
            'end_time':'10:30','first_date':'2026-11-02','last_date':'2026-11-30',
            'timezone':'Europe/Zurich'},**changes)

    def test_week_plans_are_optional_and_do_not_affect_today_pins(self):
        a,b=self.create_task('A'),self.create_task('B')
        self.assertEqual(self.state()['productivity']['weekly_plans'],{})
        server.mutate(self.uid,'PATCH','/api/tasks/'+a,{'planned_for':'2026-11-18'})
        server.mutate(self.uid,'PATCH','/api/productivity/weekly-plan',{
            'week_start':'2026-11-16','outcome_ids':[a], 'days':{'2026-11-18':[a,b]}
        })
        s=self.state()
        self.assertEqual(s['productivity']['weekly_plans']['2026-11-16']['days']['2026-11-18'],[a,b])
        self.assertEqual(s['tasks'][0]['planned_for'],'2026-11-18')
        self.assertEqual(s['productivity']['daily_plans'],{})
        self.assertIsNone(s['productivity']['weekly_plans'].get('2026-11-23'))

    def test_invalid_week_and_task_references_are_atomic(self):
        a=self.create_task('A')
        original=copy.deepcopy(self.state()['productivity'])
        cases=[
            {'week_start':'2026-11-17','outcome_ids':[a],'days':{}},
            {'week_start':'2026-11-16','outcome_ids':['unknown'],'days':{}},
            {'week_start':'2026-11-16','outcome_ids':[a,a],'days':{}},
            {'week_start':'2026-11-16','outcome_ids':[],'days':{'2026-11-23':[a]}},
            {'week_start':'2026-11-16','outcome_ids':[],'days':{'2026-11-18':[a,a]}},
            {'week_start':'2026-11-16','outcome_ids':[],'days':{'2026-11-18':['unknown']}},
        ]
        for item in cases:
            with self.subTest(item=item),self.assertRaises(server.ClientError):
                server.mutate(self.uid,'PATCH','/api/productivity/weekly-plan',item)
        self.assertEqual(self.state()['productivity'],original)

    def test_deleting_task_cleans_week_plans_and_preserves_remaining_items(self):
        a,b=self.create_task('A'),self.create_task('B')
        server.mutate(self.uid,'PATCH','/api/productivity/weekly-plan',{
            'week_start':'2026-11-16','outcome_ids':[a,b],'days':{'2026-11-19':[a,b]}})
        server.mutate(self.uid,'DELETE','/api/tasks/'+a,{})
        plan=self.state()['productivity']['weekly_plans']['2026-11-16']
        self.assertEqual(plan['outcome_ids'],[b])
        self.assertEqual(plan['days']['2026-11-19'],[b])

    def test_recurring_lecture_validations_and_recorded_attendance(self):
        result=server.mutate(self.uid,'POST','/api/productivity/lectures',self.lecture_body())
        ident=result['lecture_id']
        lecture=self.state()['productivity']['lectures'][0]
        self.assertEqual(lecture['id'],ident)
        self.assertEqual(lecture['attendance'],{})
        with mock.patch.object(server,'now',return_value=datetime(2026,11,16,9,0,tzinfo=timezone.utc)):
            with self.assertRaises(server.ClientError):
                server.mutate(self.uid,'PATCH','/api/productivity/lectures/'+ident+'/attendance',
                    {'date':'2026-11-16','status':'attended'})
        with mock.patch.object(server,'now',return_value=datetime(2026,11,16,10,0,tzinfo=timezone.utc)):
            server.mutate(self.uid,'PATCH','/api/productivity/lectures/'+ident+'/attendance',
                {'date':'2026-11-16','status':'attended'})
        self.assertEqual(self.state()['productivity']['lectures'][0]['attendance'],{'2026-11-16':'attended'})
        server.mutate(self.uid,'PATCH','/api/productivity/lectures/'+ident+'/attendance',
            {'date':'2026-11-16','status':'excused'})
        self.assertEqual(self.state()['productivity']['lectures'][0]['attendance']['2026-11-16'],'excused')
        with self.assertRaises(server.ClientError):
            server.mutate(self.uid,'PATCH','/api/productivity/lectures/'+ident+'/attendance',
                {'date':'2026-11-17','status':'attended'})

    def test_rejects_invalid_lecture_definitions(self):
        cases=[
            {'weekday':7}, {'start_time':'25:00'}, {'end_time':'08:59'},
            {'timezone':'Not/A_Real_Timezone'}, {'first_date':'2026-11-32'},
            {'last_date':'2026-10-01'}, {'subject_id':'unknown'}, {'title':''}
        ]
        for override in cases:
            data=self.lecture_body()
            data.update(override)
            with self.subTest(item=override),self.assertRaises(server.ClientError):
                server.mutate(self.uid,'POST','/api/productivity/lectures',data)
        self.assertEqual(self.state()['productivity']['lectures'],[])

    def test_lecture_deleted_and_legacy_backup_supported(self):
        ident=server.mutate(self.uid,'POST','/api/productivity/lectures',self.lecture_body())['lecture_id']
        server.mutate(self.uid,'PATCH','/api/productivity/weekly-plan',{'week_start':'2026-11-16','days':{},'outcome_ids':[]})
        snapshot=copy.deepcopy(self.state())
        restored=server.validate_backup(snapshot)
        self.assertEqual(restored['productivity'],snapshot['productivity'])
        old=copy.deepcopy(snapshot)
        old['productivity'].pop('lectures')
        old['productivity'].pop('weekly_plans')
        restored_old=server.validate_backup(old)
        self.assertEqual(restored_old['productivity']['weekly_plans'],{})
        self.assertEqual(restored_old['productivity']['lectures'],[])
        server.mutate(self.uid,'DELETE','/api/productivity/lectures/'+ident,{})
        self.assertEqual(self.state()['productivity']['lectures'],[])

    def _start_aged_timer(self,task_id):
        server.mutate(self.uid,'POST','/api/timer/start',{'task_id':task_id})
        s=self.state()
        s['active_timer']['mode_since']=(server.now()-server.timedelta(seconds=90)).isoformat()
        server.save_profile(self.uid,s)

    def test_finish_saves_session_and_completes_task_atomically(self):
        parent=self.create_task('Parent')
        child=self.create_task('Child',parent)
        self._start_aged_timer(child)
        result=server.mutate(self.uid,'POST','/api/timer/stop',{'complete_task':True})
        self.assertEqual(result['completed_task_id'],child)
        state=self.state()
        self.assertIsNone(state['active_timer'])
        self.assertEqual(len(state['sessions']),1)
        self.assertEqual(state['sessions'][0]['task_id'],child)
        self.assertGreaterEqual(state['sessions'][0]['duration_seconds'],89)
        self.assertEqual(next(x for x in state['tasks'] if x['id']==child)['status'],'done')
        self.assertEqual(next(x for x in state['tasks'] if x['id']==parent)['status'],'done')

    def test_stop_without_finish_keeps_task_open_and_invalid_finish_is_atomic(self):
        task_id=self.create_task('Task')
        self._start_aged_timer(task_id)
        for invalid in ('yes',1,None):
            with self.subTest(value=invalid),self.assertRaises(server.ClientError):
                server.mutate(self.uid,'POST','/api/timer/stop',{'complete_task':invalid})
        state=self.state()
        self.assertEqual(state['sessions'],[])
        self.assertIsNotNone(state['active_timer'])
        server.mutate(self.uid,'POST','/api/timer/stop',{})
        self.assertNotEqual(self.state()['tasks'][0]['status'],'done')

    def test_free_timer_cannot_complete_task(self):
        server.mutate(self.uid,'POST','/api/timer/start',{'subject_id':'mathe','title':'Free'})
        s=self.state()
        s['active_timer']['mode_since']=(server.now()-server.timedelta(seconds=60)).isoformat()
        server.save_profile(self.uid,s)
        with self.assertRaises(server.ClientError):
            server.mutate(self.uid,'POST','/api/timer/stop',{'complete_task':True})
        self.assertIsNotNone(self.state()['active_timer'])
        self.assertEqual(self.state()['sessions'],[])


if __name__=='__main__':
    unittest.main()
