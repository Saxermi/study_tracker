"""Execution-productivity features: persistence, isolation, validation and backup compatibility."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class ProductivityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data_patch = mock.patch.object(server, "DATA_DIR", Path(self.temp.name) / "data")
        self.backup_patch = mock.patch.object(server, "BACKUP_DIR", Path(self.temp.name) / "backup")
        self.data_patch.start()
        self.backup_patch.start()
        server.SESSIONS.clear()
        self.user = server.create_user({
            "username": "student", "display_name": "Student", "password": "secure-test-password"
        }, first=True)["id"]

    def tearDown(self):
        self.backup_patch.stop()
        self.data_patch.stop()
        server.SESSIONS.clear()
        self.temp.cleanup()

    def new_task(self, title="Task", **kwargs):
        return server.mutate(self.user, "POST", "/api/tasks", {
            "title": title, "subject_id": "mathe", **kwargs
        })["task_id"]

    def state(self):
        return server.load_profile(self.user)

    def test_migration_is_non_destructive(self):
        state = self.state()
        state.pop("productivity")
        state["settings"].pop("focus_mode_enabled")
        tid = self.new_task("Migration")
        state = self.state()
        state.pop("productivity")
        state["settings"].pop("focus_mode_enabled")
        state["tasks"][0].pop("next_action")
        state["tasks"][0].pop("resume_note")
        server.save_profile(self.user, state)
        migrated = self.state()
        self.assertEqual(migrated["tasks"][0]["id"], tid)
        self.assertEqual(migrated["tasks"][0]["next_action"], "")
        self.assertEqual(migrated["productivity"]["daily_plans"], {})
        self.assertTrue(migrated["settings"]["focus_mode_enabled"])

    def test_daily_priorities_are_independent_of_today_pins(self):
        a = self.new_task("A", planned_for="2026-11-01")
        b = self.new_task("B")
        response = server.mutate(self.user, "PATCH", "/api/productivity/daily-plan", {
            "date": "2026-11-18", "priority_ids": [b, a], "capacity_minutes": 120
        })
        self.assertEqual(response["state"]["productivity"]["daily_plans"]["2026-11-18"],
                         {"priority_ids": [b, a], "capacity_minutes": 120})
        self.assertEqual(next(t for t in self.state()["tasks"] if t["id"] == a)["planned_for"], "2026-11-01")
        self.assertIsNone(next(t for t in self.state()["tasks"] if t["id"] == b)["planned_for"])
        self.assertEqual(self.state()["productivity"]["daily_plans"].get("2026-11-19"), None)

    def test_rejects_duplicate_unknown_and_excess_priorities_without_write(self):
        a = self.new_task("A")
        b = self.new_task("B")
        c = self.new_task("C")
        d = self.new_task("D")
        for ids in ([a,a], [a,"missing"], [a,b,c,d], "not-a-list"):
            with self.subTest(ids=ids), self.assertRaises(server.ClientError):
                server.mutate(self.user, "PATCH", "/api/productivity/daily-plan", {
                    "date": "2026-11-18", "priority_ids": ids
                })
        self.assertEqual(self.state()["productivity"]["daily_plans"], {})

    def test_capacity_validation_and_partial_daily_patch(self):
        a = self.new_task("A")
        server.mutate(self.user, "PATCH", "/api/productivity/daily-plan", {
            "date": "2026-11-18", "priority_ids": [a], "capacity_minutes": 90
        })
        server.mutate(self.user, "PATCH", "/api/productivity/daily-plan", {
            "date": "2026-11-18", "capacity_minutes": None
        })
        self.assertEqual(self.state()["productivity"]["daily_plans"]["2026-11-18"],
                         {"priority_ids": [a], "capacity_minutes": None})
        for capacity in (0, 1441, 3.5, -5, True):
            with self.subTest(capacity=capacity), self.assertRaises(server.ClientError):
                server.mutate(self.user, "PATCH", "/api/productivity/daily-plan", {
                    "date": "2026-11-18", "capacity_minutes": capacity
                })

    def test_delete_task_removes_priorities_only(self):
        a = self.new_task("A")
        b = self.new_task("B")
        server.mutate(self.user, "PATCH", "/api/productivity/daily-plan", {
            "date": "2026-11-18", "priority_ids": [a,b], "capacity_minutes": 60
        })
        server.mutate(self.user, "DELETE", "/api/tasks/" + a, {})
        plan = self.state()["productivity"]["daily_plans"]["2026-11-18"]
        self.assertEqual(plan["priority_ids"], [b])
        self.assertEqual(plan["capacity_minutes"], 60)

    def test_next_action_and_resume_note_survive_partial_patches(self):
        a = self.new_task("A", next_action="Open worksheet", resume_note="Continue at B")
        server.mutate(self.user, "PATCH", "/api/tasks/" + a, {"status": "doing"})
        task = self.state()["tasks"][0]
        self.assertEqual(task["next_action"], "Open worksheet")
        self.assertEqual(task["resume_note"], "Continue at B")
        server.mutate(self.user, "PATCH", "/api/tasks/" + a, {"resume_note": ""})
        self.assertEqual(self.state()["tasks"][0]["next_action"], "Open worksheet")
        self.assertEqual(self.state()["tasks"][0]["resume_note"], "")
        with self.assertRaises(server.ClientError):
            server.mutate(self.user, "PATCH", "/api/tasks/" + a, {"next_action": "x"*201})

    def test_focus_mode_setting_does_not_clear_weekly_target(self):
        server.mutate(self.user, "PATCH", "/api/settings", {"weekly_goal_minutes": 240})
        server.mutate(self.user, "PATCH", "/api/settings", {"focus_mode_enabled": False})
        self.assertEqual(self.state()["settings"]["weekly_goal_minutes"], 240)
        self.assertIs(self.state()["settings"]["focus_mode_enabled"], False)
        with self.assertRaises(server.ClientError):
            server.mutate(self.user, "PATCH", "/api/settings", {"focus_mode_enabled": "no"})
        self.assertEqual(self.state()["settings"]["focus_mode_enabled"], False)

    def test_weekly_review_monday_only_and_field_validation(self):
        data = {"week_start": "2026-11-16", "worked": "Time boxing", "obstacle": "Interruptions",
                "adjustment": "Smaller tasks", "if_then": "If interrupted, note where I stopped"}
        server.mutate(self.user, "PATCH", "/api/productivity/weekly-review", data)
        saved = self.state()["productivity"]["weekly_reviews"]["2026-11-16"]
        self.assertEqual(saved["worked"], "Time boxing")
        server.mutate(self.user, "PATCH", "/api/productivity/weekly-review", {
            "week_start": "2026-11-16", "obstacle": "Overplanning"
        })
        self.assertEqual(self.state()["productivity"]["weekly_reviews"]["2026-11-16"]["worked"], "Time boxing")
        for invalid in ({"week_start": "2026-11-17"}, {"week_start": "2026-11-16", "worked": "a"*1001},
                        {"week_start": "invalid"}):
            with self.subTest(data=invalid), self.assertRaises(server.ClientError):
                server.mutate(self.user, "PATCH", "/api/productivity/weekly-review", invalid)

    def test_backup_round_trip_retains_productivity(self):
        a = self.new_task("A", next_action="Open file", resume_note="Inspect line 8")
        server.mutate(self.user, "PATCH", "/api/productivity/daily-plan", {
            "date": "2026-11-18", "priority_ids": [a], "capacity_minutes": 150
        })
        server.mutate(self.user, "PATCH", "/api/productivity/weekly-review", {
            "week_start": "2026-11-16", "worked": "Met goals"
        })
        server.mutate(self.user, "PATCH", "/api/settings", {"focus_mode_enabled": False})
        cleaned = server.validate_backup(copy.deepcopy(self.state()))
        self.assertEqual(cleaned["productivity"], self.state()["productivity"])
        self.assertEqual(cleaned["tasks"][0]["next_action"], "Open file")
        self.assertEqual(cleaned["tasks"][0]["resume_note"], "Inspect line 8")
        self.assertFalse(cleaned["settings"]["focus_mode_enabled"])
        legacy = copy.deepcopy(self.state())
        legacy.pop("productivity")
        legacy["settings"].pop("focus_mode_enabled")
        cleaned_legacy = server.validate_backup(legacy)
        self.assertEqual(cleaned_legacy["productivity"]["daily_plans"], {})
        self.assertTrue(cleaned_legacy["settings"]["focus_mode_enabled"])
        with self.assertRaises(server.ClientError):
            broken = copy.deepcopy(self.state())
            broken["productivity"]["daily_plans"]["2026-11-18"]["priority_ids"] = ["unknown"]
            server.validate_backup(broken)


if __name__ == "__main__":
    unittest.main()
