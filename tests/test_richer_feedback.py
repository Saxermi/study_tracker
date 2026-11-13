"""Bounded and optional structured exercise feedback."""
import unittest
import server

class RichReviewTests(unittest.TestCase):
    def test_extended_feedback_and_legacy_issue(self):
        x=server.validate_exercise_review({"difficulty":3,"outcome":"partial","issues":["concept","approach"],"strength":"Correctly found the constraints.","weakness":"Needed help choosing a pivot.","skill_gap":"Simplex pivot selection","next_action":"Retry a similar question unaided.","chatgpt_interventions":["hint","concept_explanation"]})
        self.assertEqual(x["issue"],"concept")
        self.assertEqual(x["issues"],["concept","approach"])
        self.assertEqual(server.validate_exercise_review({"issue":"calculation"})["issues"],["calculation"])
        self.assertIsNone(server.validate_exercise_review({}))
    def test_invalid_values_are_rejected(self):
        for bad in ({"issues":["concept"]*2},{"issues":["concept","approach","time","careless"]},{"issues":["bogus"]},{"issue":"approach","issues":["concept"]},{"strength":"x"*201},{"weakness":"x"*201},{"skill_gap":"a"*101},{"next_action":"x"*161},{"chatgpt_interventions":["bogus"]},{"chatgpt_interventions":["hint"]*2}):
            with self.subTest(bad=bad),self.assertRaises(server.ClientError):
                server.validate_exercise_review(bad)
if __name__=="__main__":unittest.main()
