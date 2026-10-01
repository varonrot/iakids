"""Private preparation lifecycle, multi-topic gating and material handling (no live AI)."""
import asyncio
import copy
import importlib.util
import io
import pathlib
import sys
import types
import unittest
import zipfile
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from pydantic import BaseModel, ValidationError
from test_eng_learning_2027 import Table


class HTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail


def load():
    table = Table()
    main = types.ModuleType('main')
    main.LimitedRequest = BaseModel
    main.app = types.SimpleNamespace(get=lambda _: lambda f: f, post=lambda _: lambda f: f)
    main.authenticate_user = lambda _: types.SimpleNamespace(id='parent')
    main.get_child_by_id = lambda *_: {'age': 5, 'child_name': 'Learner'}
    main.llm_model = lambda s: s
    main.sb = types.SimpleNamespace(table=lambda _: table)
    for name in ['aclient', 'gemini_client', 'types', 'spend_daily_budget', 'homework_file_kind', 'signed_url_cached']:
        setattr(main, name, lambda *a: None)
    routes = types.ModuleType('eng_lesson_routes_2027')
    for name in ['AUDIO_BUCKET', 'VOICE_MODEL', 'VOICE_NAME', '_cached_narration', '_generate_narration']:
        setattr(routes, name, lambda *a: None)
    fastapi = types.ModuleType('fastapi')
    fastapi.HTTPException = HTTPException
    fastapi.Header = fastapi.File = fastapi.Form = lambda v=None: v
    fastapi.UploadFile = object
    concurrency = types.ModuleType('starlette.concurrency')
    async def run(fn, *args): return fn(*args)
    concurrency.run_in_threadpool = run
    spec = importlib.util.spec_from_file_location('prep_under_test', pathlib.Path(__file__).with_name('eng_test_prep_planner_2027.py'))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'main': main, 'fastapi': fastapi, 'starlette.concurrency': concurrency, 'eng_lesson_routes_2027': routes}):
        spec.loader.exec_module(module)
    return module, table


def pack():
    q = {'prompt': 'What is 1 + 1?', 'context': '', 'options': ['2', '3'], 'correct_index': 0, 'explanation': 'One and one make two.'}
    return {'title': 'Addition practice', 'overview': 'Practise addition.', 'skills': ['Addition'], 'questions': [copy.deepcopy(q) for _ in range(3)]}


class PrepTests(unittest.TestCase):
    def setUp(self):
        self.m, self.table = load()
        self.row = {'id': str(uuid4()), 'user_id': 'parent', 'child_id': 'kid', 'mode': 'topics',
                    'grade': 5, 'topic': 'Addition', 'subject': 'Math', 'source_name': '', 'source_text': '',
                    'content': pack(), 'dialogue': [], 'answers': {}, 'revision': 0, 'approved_at': None}
        self.table.rows = [self.row]

    def request(self, cls, **extra):
        return cls(kid_id='kid', session_id=self.row['id'], revision=self.row['revision'], **extra)

    def test_answers_and_source_not_exposed(self):
        self.row['source_text'] = 'private original source'
        result = self.m._public(self.row)
        self.assertNotIn('source_text', result)
        self.assertNotIn('correct_index', result['pack']['questions'][0])
        self.assertNotIn('explanation', result['pack']['questions'][0])

    def test_ownership_scopes_parent_and_child(self):
        for parent, child in [('other', 'kid'), ('parent', 'other')]:
            with self.assertRaises(HTTPException) as ctx: self.m._owned(parent, child, self.row['id'])
            self.assertEqual(ctx.exception.status_code, 404)

    def test_stale_revision_cannot_overwrite(self):
        old = copy.deepcopy(self.row)
        self.m._save(self.row, {'topic': 'New topic'})
        with self.assertRaises(HTTPException) as ctx: self.m._save(old, {'topic': 'Stale topic'})
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(self.row['topic'], 'New topic')

    def test_approval_locks_replies(self):
        asyncio.run(self.m.approve(self.request(self.m.SessionRequest)))
        with self.assertRaises(HTTPException) as ctx: asyncio.run(self.m.reply(self.request(self.m.ReplyRequest, message='Change this')))
        self.assertEqual(ctx.exception.status_code, 409)

    def test_empty_draft_cannot_be_approved(self):
        self.row['content'] = None
        with self.assertRaises(HTTPException): asyncio.run(self.m.approve(self.request(self.m.SessionRequest)))

    def test_answer_before_approval_rejected(self):
        with self.assertRaises(HTTPException): asyncio.run(self.m.answer(self.request(self.m.AnswerRequest, question_index=0, option_index=0)))

    def test_grade_answers_and_resume(self):
        asyncio.run(self.m.approve(self.request(self.m.SessionRequest)))
        result = asyncio.run(self.m.answer(self.request(self.m.AnswerRequest, question_index=0, option_index=1)))
        self.assertFalse(result['answers']['0']['correct'])
        self.assertEqual(result['answers']['0']['correct_index'], 0)
        self.assertNotIn('correct_index', result['pack']['questions'][1])
        result = asyncio.run(self.m.preparation(self.row['id'], 'kid'))
        self.assertEqual(len(result['answers']), 1)

    def test_no_skipping_questions(self):
        self.row['approved_at'] = 'now'
        with self.assertRaises(HTTPException): asyncio.run(self.m.answer(self.request(self.m.AnswerRequest, question_index=1, option_index=0)))

    def test_multiple_topics_do_not_generate_or_replace_draft(self):
        scope = self.m.Scope(message='Choose', topics=['Fractions', 'Decimals'], subject='Math', ready=True, revise=True, options=[])
        with patch.object(self.m, '_parse', AsyncMock(return_value=scope)), patch.object(self.m, '_pack', AsyncMock()) as build:
            result = asyncio.run(self.m.reply(self.request(self.m.ReplyRequest, message='Fractions and decimals')))
        build.assert_not_called()
        self.assertEqual(result['topic'], 'Addition')
        self.assertEqual(result['dialogue'][-1]['options'], ['Fractions', 'Decimals'])

    def test_subject_only_waits_for_topic(self):
        scope = self.m.Scope(message='Which math topic?', topics=[], subject='Math', ready=False, revise=False, options=['Fractions'])
        with patch.object(self.m, '_parse', AsyncMock(return_value=scope)), patch.object(self.m, '_pack', AsyncMock()) as build:
            asyncio.run(self.m.reply(self.request(self.m.ReplyRequest, message='Math')))
        build.assert_not_called()

    def test_single_topic_builds_saved_reviewable_draft(self):
        scope = self.m.Scope(message='Ready', topics=['Fractions'], subject='Math', ready=True, revise=True, options=[])
        with patch.object(self.m, '_parse', AsyncMock(return_value=scope)), patch.object(self.m, '_pack', AsyncMock(return_value=pack())):
            result = asyncio.run(self.m.reply(self.request(self.m.ReplyRequest, message='Fractions')))
        self.assertEqual(result['topic'], 'Fractions')
        self.assertIsNone(result['approved_at'])
        self.assertEqual(len(result['pack']['questions']), 3)

    def test_first_topic_starts_without_readiness_followup(self):
        self.row['content'] = None
        scope = self.m.Scope(message='Are you ready?', topics=['Fractions'], subject='Math', ready=False, revise=False, options=[])
        with patch.object(self.m, '_parse', AsyncMock(return_value=scope)), patch.object(self.m, '_pack', AsyncMock(return_value=pack())) as build:
            result = asyncio.run(self.m.reply(self.request(self.m.ReplyRequest, message='Fractions')))
        build.assert_awaited_once()
        self.assertIsNotNone(result['pack'])
        self.assertNotIn('Are you ready?', result['dialogue'][-1]['text'])

    def test_subject_is_not_mistaken_for_concrete_topic(self):
        self.row['content'] = None
        scope = self.m.Scope(message='Which topic?', topics=['Math'], subject='Math', ready=True, revise=True, options=['Fractions'])
        with patch.object(self.m, '_parse', AsyncMock(return_value=scope)), patch.object(self.m, '_pack', AsyncMock()) as build:
            asyncio.run(self.m.reply(self.request(self.m.ReplyRequest, message='Math')))
        build.assert_not_called()

    def test_failed_generation_keeps_saved_draft(self):
        old = copy.deepcopy(self.row)
        scope = self.m.Scope(message='Ready', topics=['Addition'], subject='Math', ready=True, revise=True, options=[])
        with patch.object(self.m, '_parse', AsyncMock(return_value=scope)), patch.object(self.m, '_pack', AsyncMock(side_effect=HTTPException(502, 'Retry'))):
            with self.assertRaises(HTTPException): asyncio.run(self.m.reply(self.request(self.m.ReplyRequest, message='Make it harder')))
        self.assertEqual(self.row, old)

    def test_upload_context_passed_to_generator(self):
        self.row.update(mode='file', source_text='A plant needs light and water.')
        scope = self.m.Scope(message='Ready', topics=['Plants', 'Water'], subject='Science', ready=True, revise=True, options=[])
        with patch.object(self.m, '_parse', AsyncMock(return_value=scope)), patch.object(self.m, '_pack', AsyncMock(return_value=pack())) as build:
            asyncio.run(self.m.reply(self.request(self.m.ReplyRequest, message='Build my exercises')))
        self.assertEqual(build.call_args.args[0]['source_text'], self.row['source_text'])

    def test_duplicate_or_invalid_answers_rejected(self):
        q = pack()['questions'][0]
        with self.assertRaises(ValidationError): self.m.Exercise(**{**q, 'correct_index': 3})
        with self.assertRaises(ValidationError): self.m.Exercise(**{**q, 'options': ['2', '2']})

    def test_docx_and_utf8_extraction(self):
        self.assertEqual(self.m._document_text(b'Fractions', 'test.txt'), 'Fractions')
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Plants need water.</w:t></w:r></w:p></w:document>')
        self.assertEqual(self.m._document_text(data.getvalue(), 'test.docx'), 'Plants need water.')
        with self.assertRaises(HTTPException): self.m._document_text(b'corrupt', 'test.docx')

    def test_review_failure_does_not_publish_unchecked_exercises(self):
        output = [self.m.Pack(**pack()), self.m.Review(approved=False, issues=['Wrong answer'])] * 2
        with patch.object(self.m, '_parse', AsyncMock(side_effect=output)):
            with self.assertRaises(HTTPException): asyncio.run(self.m._pack(self.row, 'Build', 'parent'))


if __name__ == '__main__': unittest.main()
