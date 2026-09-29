"""Checks for the initial English Practice route without live credentials."""
import asyncio
import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import patch
from uuid import uuid4

from pydantic import BaseModel


class FakeTable:
    def __init__(self):
        self.rows = []

    def insert(self, row):
        self.rows.append(row)
        return self

    def execute(self):
        return self


def load_route(grade=5):
    table = FakeTable()
    fake_main = types.ModuleType('main')
    fake_main.LimitedRequest = BaseModel
    fake_main.app = types.SimpleNamespace(post=lambda _: lambda fn: fn)
    fake_main.authenticate_user = lambda _: types.SimpleNamespace(id='parent-id')
    fake_main.get_child_by_id = lambda user_id, kid_id: {'id': kid_id, 'child_name': 'Alona', 'age': grade}
    fake_main.sb = types.SimpleNamespace(table=lambda name: table if name == '2027_eng_practice_attempts' else None)
    fake_fastapi = types.ModuleType('fastapi')
    fake_fastapi.Header = lambda default=None: default

    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            self.status_code, self.detail = status_code, detail

    fake_fastapi.HTTPException = HTTPException
    fake_concurrency = types.ModuleType('starlette.concurrency')

    async def threadpool(fn, *args):
        return fn(*args)

    fake_concurrency.run_in_threadpool = threadpool
    path = pathlib.Path(__file__).with_name('eng_practice_2027.py')
    spec = importlib.util.spec_from_file_location('eng_practice_under_test', path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'main': fake_main, 'fastapi': fake_fastapi,
                                  'starlette.concurrency': fake_concurrency}):
        spec.loader.exec_module(module)
    return module, table


class PracticeTests(unittest.TestCase):
    def test_pack_contract_hides_answers_and_explanations(self):
        route, _ = load_route()
        result = asyncio.run(route.start_practice(route.StartPractice(kid_id='child-id', pack_id='g5-dividing-fractions'), 'Bearer token'))
        self.assertEqual(result['grade'], 5)
        self.assertEqual(len(result['pack']['questions']), 3)
        self.assertEqual(set(result['pack']['questions'][0]), {'key', 'prompt', 'options'})
        self.assertTrue(all(item['id'].startswith('g5-') for item in result['packs']))

    def test_grading_saves_attempt_for_selected_child(self):
        route, table = load_route()
        body = route.AnswerPractice(kid_id='child-id', pack_id='g5-dividing-fractions',
                                    session_id=uuid4(), question_key='half-quarters', option_index=1)
        result = asyncio.run(route.answer_practice(body, 'Bearer token'))
        self.assertTrue(result['correct'])
        self.assertEqual(table.rows[0]['child_id'], 'child-id')
        self.assertEqual(table.rows[0]['user_id'], 'parent-id')
        self.assertTrue(table.rows[0]['is_correct'])

    def test_grade_mismatch_is_rejected_before_write(self):
        route, table = load_route(grade=4)
        body = route.AnswerPractice(kid_id='child-id', pack_id='g5-dividing-fractions',
                                    session_id=uuid4(), question_key='half-quarters', option_index=1)
        with self.assertRaises(route.HTTPException) as error:
            asyncio.run(route.answer_practice(body, 'Bearer token'))
        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(table.rows, [])


if __name__ == '__main__':
    unittest.main()
