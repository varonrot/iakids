"""Exercise the answer transition without a database or provider credentials."""

import asyncio
import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import patch

from eng_lessons_2027 import public_step
from test_eng_lessons_2027 import PLAN


def load_routes():
    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            self.status_code = status_code
            self.detail = detail

    class App:
        def post(self, path):
            return lambda fn: fn

    async def run_in_threadpool(fn, *args):
        return fn(*args)

    fake_main = types.ModuleType("main")
    fake_main.LimitedRequest = object
    fake_main.app = App()
    fake_main.authenticate_user = lambda *_: None
    fake_main.get_child_by_id = lambda *_: None
    fake_main.aclient = None
    fake_main.gemini_client = None
    fake_main.types = None
    fake_main.TTS_PROVIDER = "gemini"
    fake_main.OPENROUTER_TTS_MODEL = "google/gemini-3.1-flash-tts-preview"
    fake_main.OPENROUTER_BASE_URL = "https://example.invalid"
    fake_main.OPENROUTER_API_KEY = "test"
    fake_main._record_openrouter_tts = lambda *_: None
    fake_main.guard_reply_payload = lambda value, *_: value
    fake_main.llm_model = lambda name: name
    fake_main.spend_daily_budget = lambda *_: None
    fake_main.sb = None
    fake_main.signed_url_cached = lambda *_: ""
    fake_fastapi = types.ModuleType("fastapi")
    fake_fastapi.Header = lambda default=None: default
    fake_fastapi.HTTPException = HTTPException
    fake_pydantic = types.ModuleType("pydantic")
    fake_pydantic.Field = lambda default=None, **kwargs: default
    fake_concurrency = types.ModuleType("starlette.concurrency")
    fake_concurrency.run_in_threadpool = run_in_threadpool
    fake_prep = types.ModuleType("test_prep_2027")
    fake_prep.SUBJECT = "Math"
    fake_prep.TOPIC = "Dividing fractions"
    fake_prep._diagnostic = lambda *_: None
    path = pathlib.Path(__file__).with_name("eng_lesson_routes_2027.py")
    spec = importlib.util.spec_from_file_location("eng_lesson_routes_under_test", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"main": fake_main, "fastapi": fake_fastapi,
                                  "pydantic": fake_pydantic, "starlette.concurrency": fake_concurrency,
                                  "test_prep_2027": fake_prep}):
        spec.loader.exec_module(module)
    return module


class FakeTable:
    def __init__(self, name, state, attempts):
        self.name, self.state, self.attempts = name, state, attempts
        self.row = None

    def insert(self, row):
        self.row = row
        return self

    def update(self, row):
        self.row = row
        return self

    def eq(self, *_):
        return self

    def execute(self):
        if self.name == "2027_eng_lesson_attempts":
            self.attempts.append(self.row)
        else:
            self.state.update(self.row)
        return types.SimpleNamespace(data=[self.row])


class EnglishLessonRouteTests(unittest.TestCase):
    def test_grade_five_child_can_be_ten_years_old(self):
        route = load_routes()
        with patch.object(route, "authenticate_user", return_value=types.SimpleNamespace(id="parent-1")), \
             patch.object(route, "get_child_by_id", return_value={"age": 10}) as child_lookup, \
             patch.object(route, "_diagnostic") as diagnostic:
            self.assertEqual(route._parent_and_child("Bearer token", "child-1"), "parent-1")
        child_lookup.assert_called_once_with("parent-1", "child-1")
        diagnostic.assert_called_once_with("parent-1", "child-1")

    def test_wrong_answer_stays_put_then_correct_answer_advances(self):
        route = load_routes()
        state, attempts = {"current_step": 1}, []
        route.sb = types.SimpleNamespace(table=lambda name: FakeTable(name, state, attempts))
        route._approved_plan = lambda *_: {"id": "plan-1", "content": PLAN}
        route._progress = lambda *_: state
        route._visible_step = lambda plan_id, content, index: public_step(content, index)
        answer = types.SimpleNamespace(kid_id="child-1", plan_id="plan-1", step_index=1,
                                       option_index=0, hint_used=False)
        wrong = route._submit("parent-1", "child-1", answer)
        self.assertFalse(wrong["correct"])
        self.assertEqual(state["current_step"], 1)
        answer.option_index, answer.hint_used = 1, True
        right = route._submit("parent-1", "child-1", answer)
        self.assertTrue(right["correct"])
        self.assertEqual(state["current_step"], 2)
        self.assertEqual(right["step_index"], 2)
        self.assertEqual([(a["is_correct"], a["hint_used"]) for a in attempts],
                         [(False, False), (True, True)])
        answer.step_index = 2
        finished = route._submit("parent-1", "child-1", answer)
        self.assertTrue(finished["complete"])
        self.assertEqual(state["current_step"], 3)
        self.assertIsNotNone(state["completed_at"])


    def test_review_only_reads_completed_step(self):
        route = load_routes()
        reads = []

        class ReadOnlyTable:
            def __init__(self, name):
                self.name = name

            def select(self, *_):
                return self

            def eq(self, *args):
                return self

            def limit(self, *_):
                return self

            def execute(self):
                reads.append(self.name)
                data = ([{"current_step": 1}] if self.name == "2027_eng_lesson_progress"
                        else [{"id": "plan-1", "content": PLAN}] if self.name == "2027_eng_lesson_plans"
                        else [])
                return types.SimpleNamespace(data=data)

        route.sb = types.SimpleNamespace(table=lambda name: ReadOnlyTable(name))
        route._visible_step = lambda plan_id, content, index: public_step(content, index)
        body = types.SimpleNamespace(kid_id="child-1", plan_id="plan-1", step_index=0)
        reviewed = route._review("parent-1", "child-1", body)
        self.assertEqual(reviewed["step_index"], 0)
        self.assertNotIn("correct_option_index", str(reviewed))
        self.assertEqual(reads, ["2027_eng_lesson_progress", "2027_eng_lesson_plans"])
        body.step_index = 1
        with self.assertRaises(route.HTTPException) as error:
            route._review("parent-1", "child-1", body)
        self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(reads[-1], "2027_eng_lesson_progress")


    def test_help_only_for_current_step_and_wrong_choice(self):
        route = load_routes()
        reads = []

        class ReadOnlyTable:
            def select(self, *_):
                return self

            def eq(self, *_):
                return self

            def limit(self, *_):
                return self

            def execute(self):
                reads.append("progress")
                return types.SimpleNamespace(data=[{"current_step": 1}])

        route.sb = types.SimpleNamespace(table=lambda *_: ReadOnlyTable())
        route._approved_plan = lambda *_: {"id": "plan-1", "content": PLAN}
        body = types.SimpleNamespace(kid_id="child-1", plan_id="plan-1", step_index=1,
                                     help_kind="hint", option_index=0, reveal_phase=0)
        self.assertEqual(route._help_context("parent-1", "child-1", body), PLAN["steps"][1])
        body.option_index = 1
        with self.assertRaises(route.HTTPException) as error:
            route._help_context("parent-1", "child-1", body)
        self.assertEqual(error.exception.status_code, 422)
        body.option_index, body.step_index = 0, 2
        with self.assertRaises(route.HTTPException) as error:
            route._help_context("parent-1", "child-1", body)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(reads), 3)


    def test_ai_hint_never_reveals_correct_option(self):
        route = load_routes()
        route._parent_and_child = lambda *_: "parent-1"
        route._help_context = lambda *_: PLAN["steps"][1]

        async def model_reply(**kwargs):
            return types.SimpleNamespace(choices=[
                types.SimpleNamespace(message=types.SimpleNamespace(content="The answer is 2."))
            ])

        route.aclient = types.SimpleNamespace(chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=model_reply)))
        body = types.SimpleNamespace(kid_id="child-1", plan_id="plan-1", step_index=1,
                                     help_kind="hint", option_index=0, reveal_phase=0)
        result = asyncio.run(route.help_english_lesson(body, "Bearer token"))
        self.assertEqual(result["hint"], "Count the shaded equal pieces one at a time.")

    def test_narration_uses_approved_step_and_no_client_text(self):
        route = load_routes()
        class ReadOnlyTable:
            def select(self, *_): return self
            def eq(self, *_): return self
            def limit(self, *_): return self
            def execute(self): return types.SimpleNamespace(data=[{"current_step": 1}])
        route.sb = types.SimpleNamespace(table=lambda *_: ReadOnlyTable())
        route._approved_plan = lambda *_: {"id": "plan-1", "content": PLAN}
        body = types.SimpleNamespace(kid_id="child-1", plan_id="plan-1", step_index=0, slide_index=0)
        self.assertEqual(route._narration_context("parent-1", "child-1", body),
                         route.IDEA_NARRATION[0])
        body.slide_index = 4
        self.assertEqual(route._narration_context("parent-1", "child-1", body),
                         route.IDEA_NARRATION[4])
        body.step_index = 2
        with self.assertRaises(route.HTTPException) as error:
            route._narration_context("parent-1", "child-1", body)
        self.assertEqual(error.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
