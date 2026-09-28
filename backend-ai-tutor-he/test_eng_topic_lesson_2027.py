"""Critical checks for the prompt-led topic route without provider credentials."""
import importlib.util
import pathlib
import sys
import types
import unittest
import copy
from unittest.mock import patch


PLAN = {"version": 1, "skill_id": "ai-guided-introduction", "slides": [
    {"title": "What is a percent?", "narration": "A percent tells us how many parts out of one hundred we have.", "visual_label": "A grid of one hundred squares"}
] * 4, "steps": [
    {"phase": "see_the_idea", "teacher_text": "We can picture a percent with a grid of one hundred squares.",
     "visual": {"kind": "none"}, "interaction": {"type": "continue"}},
    {"phase": "try_together", "teacher_text": "Ten squares out of one hundred are ten percent.",
     "visual": {"kind": "none"}, "interaction": {"type": "multiple_choice", "prompt": "How many?", "options": ["10%", "20%"], "answer_index": 0, "hint": "Count the squares."}},
    {"phase": "your_turn", "teacher_text": "Use the same idea for twenty squares.",
     "visual": {"kind": "none"}, "interaction": {"type": "multiple_choice", "prompt": "How many?", "options": ["10%", "20%"], "answer_index": 1, "hint": "Count again."}},
]}


def teacher_draft(plan=PLAN):
    draft = copy.deepcopy(plan)
    steps = draft.pop("steps")
    draft.update(zip(("see_the_idea", "try_together", "your_turn"), steps))
    return draft


def load_topic():
    import eng_lessons_2027
    from pydantic import BaseModel, Field

    class App:
        def post(self, _):
            return lambda fn: fn

    async def threadpool(fn, *args):
        return fn(*args)

    fake_main = types.ModuleType("main")
    fake_main.LimitedRequest = BaseModel
    fake_main.app = App()
    for name in ("aclient", "authenticate_user", "generate_lesson_hero_image_bytes",
                 "get_child_by_id", "guard_reply_payload", "llm_model", "sb",
                 "signed_url_cached", "spend_daily_budget"):
        setattr(fake_main, name, lambda *args: None)
    fake_fastapi = types.ModuleType("fastapi")
    fake_fastapi.Header = lambda default=None: default
    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            self.status_code, self.detail = status_code, detail
    fake_fastapi.HTTPException = HTTPException
    fake_concurrency = types.ModuleType("starlette.concurrency")
    fake_concurrency.run_in_threadpool = threadpool
    fake_routes = types.ModuleType("eng_lesson_routes_2027")
    fake_routes.AUDIO_BUCKET = "2027-eng-lesson-audio"
    fake_routes.BUCKET = "2027-eng-lesson-media"
    fake_routes.IDEA_NARRATION = (
        "We ask how many half-sized portions fit into three quarters of one pizza.",
        "The pizza has four equal quarters, and exactly three of them are shaded.",
        "Two of the shaded quarters make one complete half-pizza portion.",
        "The final quarter is half the size of one half-pizza portion.",
        "One portion and half of another fit into three quarters of a pizza.",
    )
    for name in ("_cached_narration", "_generate_narration", "_narration_path"):
        setattr(fake_routes, name, lambda *args: None)
    path = pathlib.Path(__file__).with_name("eng_topic_lesson_2027.py")
    spec = importlib.util.spec_from_file_location("eng_topic_lesson_under_test", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"main": fake_main, "fastapi": fake_fastapi,
                                  "starlette.concurrency": fake_concurrency,
                                  "eng_lesson_routes_2027": fake_routes}):
        spec.loader.exec_module(module)
    return module


class TopicLessonTests(unittest.TestCase):
    def test_reviewed_first_fraction_plan_has_correct_math_and_answer_keys(self):
        route = load_topic()
        plan = route._first_fraction_plan()
        route._check_content(plan)
        self.assertEqual(len(plan["slides"]), 5)
        self.assertEqual([step["interaction"]["type"] for step in plan["steps"]],
                         ["continue", "multiple_choice", "multiple_choice"])
        self.assertEqual(plan["steps"][1]["interaction"]["options"][1], "One and a half")
        self.assertEqual(plan["steps"][2]["interaction"]["options"][1], "Two")
        self.assertTrue(route.check_answer(plan, 1, 1))
        self.assertTrue(route.check_answer(plan, 2, 1))
        self.assertFalse(route.check_answer(plan, 1, 2))

    def test_teacher_schema_requires_both_questions(self):
        route = load_topic()
        route.TopicPlan.model_validate(teacher_draft())
        bad = teacher_draft()
        bad["try_together"]["interaction"] = {"type": "continue"}
        with self.assertRaises(ValueError):
            route.TopicPlan.model_validate(bad)

    def test_contract_and_answer_key_stays_on_server(self):
        route = load_topic()
        route._check_content(PLAN)
        visible = route._visible({"id": "p", "content": PLAN, "grade": 5,
                                  "subject": "Math", "topic": "Percentages"}, 1)
        self.assertEqual(visible["step"]["interaction"]["options"], ["10%", "20%"])
        self.assertNotIn("answer_index", str(visible))
        self.assertNotIn("slides", visible)
        first = route._visible({"id": "p", "content": PLAN, "grade": 5,
                                "subject": "Math", "topic": "Percentages"}, 0)
        self.assertEqual(len(first["slides"]), 4)

    def test_explanation_precedes_two_questions(self):
        route = load_topic()
        bad = {**PLAN, "steps": [{**PLAN["steps"][0],
                                  "interaction": PLAN["steps"][1]["interaction"]}, *PLAN["steps"][1:]]}
        with self.assertRaises(ValueError):
            route._check_content(bad)

    def test_wrong_answer_does_not_advance(self):
        route = load_topic()
        attempts, updates = [], []
        class Table:
            def __init__(self, name): self.name = name
            def insert(self, value): attempts.append(value); return self
            def update(self, value): updates.append(value); return self
            def eq(self, *_): return self
            def execute(self): return types.SimpleNamespace(data=[updates[-1] if updates else attempts[-1]])
        route.sb = types.SimpleNamespace(table=lambda name: Table(name))
        route._owned_plan = lambda *_: {"id": "p", "content": PLAN, "grade": 5,
                                         "subject": "Math", "topic": "Percentages"}
        route._progress = lambda *_: 1
        body = types.SimpleNamespace(kid_id="child", plan_id="p", step_index=1,
                                     option_index=1, hint_used=False)
        result = route._answer("parent", body)
        self.assertFalse(result["correct"])
        self.assertFalse(attempts[0]["is_correct"])
        self.assertEqual(updates, [])
        body.option_index = 0
        result = route._answer("parent", body)
        self.assertTrue(result["correct"])
        self.assertEqual(result["step_index"], 2)
        self.assertEqual(updates[-1]["current_step"], 2)


class GenerationRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_interaction_structure_regenerates_before_review(self):
        route = load_topic()
        calls, saved = [], []
        async def parse(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                invalid = teacher_draft()
                invalid["try_together"]["interaction"] = {"type": "continue"}
                parsed = types.SimpleNamespace(model_dump=lambda **_: invalid)
            elif len(calls) == 2:
                parsed = types.SimpleNamespace(model_dump=lambda **_: teacher_draft())
            else:
                parsed = types.SimpleNamespace(approved=True, issue="")
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(parsed=parsed))])
        class Table:
            def upsert(self, value, **kwargs): saved.append(value); return self
            def execute(self): return types.SimpleNamespace(data=[])
        route.aclient = types.SimpleNamespace(beta=types.SimpleNamespace(chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(parse=parse))))
        route.sb = types.SimpleNamespace(table=lambda _: Table())
        route.spend_daily_budget = lambda *_: None
        route.llm_model = lambda value: value
        route.guard_reply_payload = lambda content, *_: content
        route._plan = lambda *_: [{"id": "corrected-plan", "content": saved[-1]}] if saved else []
        plan = await route._create_plan(5, "Math", "Dividing fractions", "parent")
        self.assertEqual(plan["id"], "corrected-plan")
        self.assertEqual(len(calls), 3)
        self.assertIn("Lesson structure invalid", calls[1]["messages"][1]["content"])
        self.assertEqual(len(saved), 1)

    async def test_review_rejection_regenerates_and_only_saves_approved_plan(self):
        route = load_topic()
        calls, saved = [], []
        async def parse(**kwargs):
            calls.append(kwargs)
            if len(calls) % 2:
                return types.SimpleNamespace(choices=[types.SimpleNamespace(
                    message=types.SimpleNamespace(parsed=types.SimpleNamespace(
                        model_dump=lambda **_: teacher_draft())))])
            verdict = types.SimpleNamespace(approved=len(calls) == 4,
                                            issue="The answer key does not match the options.")
            return types.SimpleNamespace(choices=[types.SimpleNamespace(
                message=types.SimpleNamespace(parsed=verdict))])
        class Table:
            def upsert(self, value, **kwargs):
                saved.append(value)
                return self
            def execute(self): return types.SimpleNamespace(data=[])
        route.aclient = types.SimpleNamespace(beta=types.SimpleNamespace(chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(parse=parse))))
        route.sb = types.SimpleNamespace(table=lambda _: Table())
        route.spend_daily_budget = lambda *_: None
        route.llm_model = lambda value: value
        route.guard_reply_payload = lambda content, *_: content
        route._plan = lambda *_: [{"id": "approved-plan", "content": saved[-1]}] if saved else []
        plan = await route._create_plan(5, "Math", "Percentages", "parent")
        self.assertEqual(plan["id"], "approved-plan")
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(saved), 1)
        self.assertIn("answer key", calls[2]["messages"][1]["content"])

    async def test_all_rejected_drafts_are_not_saved(self):
        route = load_topic()
        count, saved = 0, []
        async def parse(**kwargs):
            nonlocal count
            count += 1
            parsed = (types.SimpleNamespace(model_dump=lambda **_: teacher_draft()) if count % 2
                      else types.SimpleNamespace(approved=False, issue="Incorrect answer key."))
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(parsed=parsed))])
        route.aclient = types.SimpleNamespace(beta=types.SimpleNamespace(chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(parse=parse))))
        route.spend_daily_budget = lambda *_: None
        route.llm_model = lambda value: value
        route.guard_reply_payload = lambda content, *_: content
        route.sb = types.SimpleNamespace(table=lambda _: saved.append(1))
        with self.assertRaises(route.HTTPException) as failure:
            await route._create_plan(5, "Math", "Percentages", "parent")
        self.assertEqual(failure.exception.status_code, 502)
        self.assertEqual(count, route.MAX_DRAFTS * 2)
        self.assertEqual(saved, [])


if __name__ == "__main__":
    unittest.main()
