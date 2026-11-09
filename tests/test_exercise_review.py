"""Exercise assessment: one optional record per task, no attempt history."""
import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class ExerciseReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = mock.patch.object(server, 'DATA_DIR', Path(self.tmp.name) / 'data')
        self.backup = mock.patch.object(server, 'BACKUP_DIR', Path(self.tmp.name) / 'backups')
        self.data.start(); self.backup.start(); server.SESSIONS.clear()
        self.uid = server.create_user({'display_name': 'Review', 'username': 'review', 'password': 'strong-enough-password'}, first=True)['id']
        self.tid = server.mutate(self.uid, 'POST', '/api/tasks', {'title': 'NumCSE - Exercise B', 'subject_id': 'mathe'})['task_id']

    def tearDown(self):
        self.backup.stop(); self.data.stop(); server.SESSIONS.clear(); self.tmp.cleanup()

    def get_review(self):
        return server.task(server.load_profile(self.uid), self.tid)['exercise_review']

    def patch(self, **kw):
        return server.mutate(self.uid, 'PATCH', f'/api/tasks/{self.tid}/review', kw)

    def test_rating_all_empty_and_individually_optional(self):
        self.assertIsNone(self.get_review())
        self.patch()
        self.assertIsNone(self.get_review())
        self.patch(help_total=3)
        self.assertEqual(self.get_review()['help_total'], 3)
        self.assertIsNone(self.get_review()['help_chatgpt'])
        self.patch(help_chatgpt=0)
        self.assertIsNone(self.get_review()['help_total'])
        self.assertEqual(self.get_review()['help_chatgpt'], 0)
        self.patch(help_chatgpt=None)
        self.assertIsNone(self.get_review())

    def test_per_task_not_per_attempt_and_status_keeps_rating(self):
        self.patch(difficulty=5, outcome='partial', issue='concept', help_total=4, help_chatgpt=3)
        self.patch(difficulty=2, outcome='correct', issue=None, help_total=0, help_chatgpt=0)
        server.mutate(self.uid, 'PATCH', f'/api/tasks/{self.tid}', {'status': 'done'})
        self.assertEqual(self.get_review()['difficulty'], 2)
        self.assertEqual(self.get_review()['outcome'], 'correct')
        self.assertEqual(self.get_review()['help_total'], 0)
        self.assertNotIn('attempts', server.task(server.load_profile(self.uid), self.tid))
        server.mutate(self.uid, 'PATCH', f'/api/tasks/{self.tid}', {'status': 'todo'})
        self.assertEqual(self.get_review()['difficulty'], 2)

    def test_invalid_values_rejected_without_modification(self):
        self.patch(help_total=3)
        for value in ({'difficulty': 6}, {'outcome': 'maybe'}, {'issue': 'other'},
                      {'help_total': 1, 'help_chatgpt': 4}, {'help_total': -1},
                      {'arbitrary': 'x'}, {'difficulty': 'abc'}):
            with self.subTest(value=value), self.assertRaises(server.ClientError):
                self.patch(**value)
        self.assertEqual(self.get_review()['help_total'], 3)

    def test_backup_and_csv_include_single_rating(self):
        self.patch(difficulty=4, outcome='partial', help_total=2, help_chatgpt=None)
        state = server.load_profile(self.uid)
        restored = server.validate_backup(state)
        self.assertEqual(server.task(restored, self.tid)['exercise_review'], self.get_review())
        old = server.load_profile(self.uid)
        old['tasks'][0].pop('exercise_review', None)
        self.assertIsNone(server.task(server.validate_backup(old), self.tid)['exercise_review'])
        values=list(csv.reader(io.StringIO(server.export_csv(state, 'tasks').decode('utf-8-sig')),delimiter=';'))
        headings=dict((s,i) for i,s in enumerate(values[0]))
        self.assertEqual(values[1][headings['Schwierigkeit (1-5)']], '4')
        self.assertEqual(values[1][headings['Gesamthilfe (0-5)']], '2')
        self.assertEqual(values[1][headings['ChatGPT-Hilfe (0-5)']], '')

    def test_each_account_has_own_review(self):
        server.create_user({'display_name': 'Second', 'username': 'second', 'password': 'strong-enough-password'}, first=False)
        self.patch(difficulty=5)
        assert len(server.accounts()['users']) == 2
        other = next(u for u in server.accounts()['users'] if u['id'] != self.uid)
        self.assertFalse(server.load_profile(other['id'])['tasks'])

if __name__ == '__main__': unittest.main()
