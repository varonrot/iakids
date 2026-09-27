import unittest

from eng_lessons_2027 import check_answer, public_step, teacher_messages, validate_plan


PLAN = {"version": 1, "skill_id": "division-as-groups", "steps": [
    {"phase": "see_the_idea", "teacher_text": "Two quarters form one half.",
     "visual": {"kind": "generated_image", "brief": "Three shaded quarters of a bar"},
     "interaction": {"type": "continue"}},
    {"phase": "try_together", "teacher_text": "Count the halves.",
     "visual": {"kind": "none"},
     "interaction": {"type": "multiple_choice", "prompt": "How many?", "options": ["1", "1½", "2"], "answer_index": 1}},
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

    def test_server_grades_choices_and_continue(self):
        self.assertTrue(check_answer(PLAN, 0))
        self.assertFalse(check_answer(PLAN, 1, 0))
        self.assertTrue(check_answer(PLAN, 1, 1))

    def test_bad_answer_index_is_rejected(self):
        bad = {**PLAN, "steps": [*PLAN["steps"]]}
        bad["steps"][1] = {**bad["steps"][1], "interaction": {**bad["steps"][1]["interaction"], "answer_index": 9}}
        with self.assertRaises(ValueError):
            validate_plan(bad)


if __name__ == "__main__":
    unittest.main()
