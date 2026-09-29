"""Checks for the English learning path without live AI or user credentials."""
import asyncio
import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import patch
from uuid import uuid4

from pydantic import BaseModel


class Table:
    def __init__(self):
        self.rows = []
        self.filters = []
        self.write = None
        self.mode = 'select'

    def select(self, *_):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, *_):
        return self

    def order(self, *_, **__):
        return self

    def insert(self, row):
        self.mode, self.write = 'insert', row
        return self

    def update(self, row):
        self.mode, self.write = 'update', row
        return self

    def execute(self):
        if self.mode == 'insert':
            row = {'id': str(uuid4()), **self.write}
            self.rows.append(row)
            result = [row]
        else:
            result = [row for row in self.rows if all(row.get(key) == value for key, value in self.filters)]
            if self.mode == 'update':
                for row in result:
                    row.update(self.write)
        self.mode, self.write, self.filters = 'select', None, []
        return types.SimpleNamespace(data=result)


def load_route(grade=5):
    table = Table()
    fake_main = types.ModuleType('main')
    fake_main.LimitedRequest = BaseModel
    fake_main.app = types.SimpleNamespace(get=lambda _: lambda fn: fn, post=lambda _: lambda fn: fn)
    fake_main.authenticate_user = lambda _: types.SimpleNamespace(id='parent-id')
    fake_main.get_child_by_id = lambda user_id, kid_id: {'id': kid_id, 'child_name': 'Alona', 'age': grade}
    fake_main.sb = types.SimpleNamespace(table=lambda name: table)
    fake_main.llm_model = lambda name: name
    for name in ('aclient', 'generate_lesson_hero_image_bytes', 'guard_reply_payload',
                 'signed_url_cached', 'spend_daily_budget'):
        setattr(fake_main, name, lambda *args: None)
    fake_routes = types.ModuleType('eng_lesson_routes_2027')
    fake_routes.BUCKET = '2027-eng-lesson-media'
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
    path = pathlib.Path(__file__).with_name('eng_learning_2027.py')
    spec = importlib.util.spec_from_file_location('eng_learning_under_test', path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'main': fake_main, 'fastapi': fake_fastapi,
                                  'starlette.concurrency': fake_concurrency,
                                  'eng_lesson_routes_2027': fake_routes}):
        spec.loader.exec_module(module)
    return module, table


class LearningTests(unittest.TestCase):
    def test_ordered_catalog_and_grade_scope(self):
        route, _ = load_route()
        result = asyncio.run(route.learning_catalog('child-id', 'Bearer token'))
        self.assertEqual(result['learner'], 'Alona')
        self.assertEqual([unit['id'] for unit in result['subjects'][0]['units']],
                         ['fractions', 'percentages'])
        self.assertEqual(result['subjects'][0]['units'][0]['skills'][0]['id'], 'equivalent-fractions')
        self.assertEqual(load_route(4)[0]._public_catalog(4), [])

    def test_start_reply_resume_isolated_to_parent_and_child(self):
        route, table = load_route()

        async def answer(*args):
            return 'Hi Alona. What do you notice about the shaded area?'

        route._generate = answer
        created = asyncio.run(route.start_learning(
            route.Start(kid_id='child-id', unit_id='fractions', skill_id='equivalent-fractions'),
            'Bearer token'))
        self.assertEqual(table.rows[0]['user_id'], 'parent-id')
        self.assertEqual(table.rows[0]['child_id'], 'child-id')
        self.assertEqual(created['turn_count'], 1)

        reply = asyncio.run(route.reply_learning(route.Reply(
            kid_id='child-id', session_id=created['session_id'], message='Both are the same size.',
            expected_turn_count=1), 'Bearer token'))
        self.assertEqual(reply['turn_count'], 3)
        resumed = asyncio.run(route.resume_learning(route.Resume(
            kid_id='child-id', session_id=created['session_id']), 'Bearer token'))
        self.assertEqual([turn['role'] for turn in resumed['turns']], ['assistant', 'user', 'assistant'])

        with self.assertRaises(route.HTTPException) as wrong_child:
            asyncio.run(route.resume_learning(route.Resume(
                kid_id='another-child', session_id=created['session_id']), 'Bearer token'))
        self.assertEqual(wrong_child.exception.status_code, 404)
        with self.assertRaises(route.HTTPException) as stale:
            asyncio.run(route.reply_learning(route.Reply(
                kid_id='child-id', session_id=created['session_id'], message='Again',
                expected_turn_count=1), 'Bearer token'))
        self.assertEqual(stale.exception.status_code, 409)

    def test_unreviewed_grade_and_skill_cannot_start(self):
        for grade, skill in [(4, 'equivalent-fractions'), (5, 'made-up')]:
            route, table = load_route(grade)
            with self.assertRaises(route.HTTPException) as invalid:
                asyncio.run(route.start_learning(route.Start(
                    kid_id='child-id', unit_id='fractions', skill_id=skill), 'Bearer token'))
            self.assertEqual(invalid.exception.status_code, 422)
            self.assertEqual(table.rows, [])


if __name__ == '__main__':
    unittest.main()
