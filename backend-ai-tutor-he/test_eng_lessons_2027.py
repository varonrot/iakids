import unittest

from eng_lessons_2027 import check_answer, public_step, teacher_messages, validate_plan, validate_first_fraction_plan


PLAN = {"version": 1, "skill_id": "division-as-groups", "steps": [
    {"phase": "see_the_idea", "teacher_text": "Two quarters form one half.",
     "visual": {"kind": "generated_image", "brief": "Three shaded quarters of a bar"},
     "interaction": {"type": "continue"}},
    {"phase": "try_together", "teacher_text": "Count the halves.",
     "visual": {"kind": "none"},
     "interaction": {"type": "multiple_choice", "prompt": "How many?", "options": ["1", "2", "3"], "answer_index": 1}},
    {"phase": "your_turn", "teacher_text": "Now try.",
     "visual": {"kind": "none"},
     "interaction": {"type": "multiple_choice", "prompt": "How many?", "options": ["1", "2"], "answer_index": 1}},
]}


class EnglishLessonContractTests(unittest.TestCase):
    def test_guide_combines_subject_and_topic(self):
        messages = teacher_messages(grade=5, subject="Math", topic="Dividing fractions")
        self.assertIn("Subject guide:", messages[1]["content"])
        self.assertIn("Topic guide:", messages[1]["content"])

    def test_only_active_step_without_answers_reaches_client(self):
        validate_plan(PLAN)
        result = public_step(PLAN, 1)
        self.assertEqual(result["step_index"], 1)
        self.assertNotIn("answer_index", str(result))
        self.assertNotIn("Three shaded quarters", str(result))

    def test_approved_visual_can_be_projected_with_accessible_alt(self):
        result = public_step(PLAN, 0, "https://example.invalid/signed-image", "Three shaded quarters")
        self.assertEqual(result["step"]["visual"]["alt_text"], "Three shaded quarters")
        self.assertNotIn("brief", result["step"]["visual"])

    def test_unexpected_private_fields_are_not_projected(self):
        plan = {**PLAN, "steps": [*PLAN["steps"]]}
        plan["steps"][1] = {**plan["steps"][1], "secret_note": "server only",
                            "interaction": {**plan["steps"][1]["interaction"], "hint": "Keep trying", "private_answer": "1½"}}
        result = public_step(plan, 1)
        self.assertNotIn("server only", str(result))
        self.assertNotIn("private_answer", str(result))
        self.assertNotIn("hint", str(result))

    def test_server_grades_choices_and_continue(self):
        validate_first_fraction_plan(PLAN)
        self.assertTrue(check_answer(PLAN, 0))
        self.assertFalse(check_answer(PLAN, 1, 0))
        self.assertTrue(check_answer(PLAN, 1, 1))

    def test_bad_answer_index_is_rejected(self):
        bad = {**PLAN, "steps": [*PLAN["steps"]]}
        bad["steps"][1] = {**bad["steps"][1], "interaction": {**bad["steps"][1]["interaction"], "answer_index": 9}}
        with self.assertRaises(ValueError):
            validate_plan(bad)

    def test_wrong_fraction_answer_cannot_be_approved(self):
        bad = {**PLAN, "steps": [*PLAN["steps"]]}
        bad["steps"][1] = {**bad["steps"][1], "interaction": {**bad["steps"][1]["interaction"], "answer_index": 0}}
        with self.assertRaises(ValueError):
            validate_first_fraction_plan(bad)


if __name__ == "__main__":
    unittest.main()
