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
        if 'request_key' in row:
            row = {'revision': 0, 'plan_history': [], **row}
        self.mode, self.write = 'insert', row
        return self

    def update(self, row):
        self.mode, self.write = 'update', row
        return self

    def delete(self):
        self.mode = 'delete'
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
            if self.mode == 'delete':
                self.rows = [row for row in self.rows if row not in result]
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
    fake_routes.AUDIO_BUCKET = '2027-eng-lesson-audio'
    fake_routes.VOICE_MODEL = 'gemini-tts-test'
    fake_routes.VOICE_NAME = 'Aoede'
    fake_routes._cached_narration = lambda path: True
    fake_routes._generate_narration = lambda text, grade: b'audio'
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
    def test_curriculum_limits_and_numbered_titles(self):
        route, _ = load_route()
        lesson = route.CurriculumLesson(title='Lesson 6: A worked example', goal='Solve a two-step problem.')
        unit = route.CurriculumUnit(title='Unit 4: Applying ideas', overview='Plan and solve a problem.', lessons=[lesson])
        plan = route.CurriculumPlan(title='Word problems', subject='Math', topic='Word Problems', units=[unit])
        content = route._normalize_plan(plan)
        self.assertEqual(content['units'][0]['title'], 'Applying ideas')
        self.assertEqual(content['units'][0]['lessons'][0]['title'], 'A worked example')
        self.assertEqual(content['units'][0]['overview'], 'Plan and solve a problem.')
        with self.assertRaises(ValueError):
            route.CurriculumUnit(title='Too many lessons', lessons=[lesson] * 9)
        with self.assertRaises(ValueError):
            route.CurriculumPlan(title='Too many units', subject='Math', topic='Math', units=[unit] * 11)
        large = route.CurriculumUnit(title='Eight lessons', lessons=[lesson] * 8)
        with self.assertRaises(ValueError):
            route.CurriculumPlan(title='Too many total lessons', subject='Math', topic='Math', units=[large] * 6)

    def test_vague_knowledge_and_readiness_do_not_rewrite_curriculum(self):
        for message, needs_clarification in [('I already know', False),
                ('I know some of this already', False),
                ("okay I'm I'm ready I want to start the plan", False),
                ('Can you clarify this?', True)]:
            with self.subTest(message=message):
                route, table = load_route()
                plan_id = str(uuid4())
                old = {'title': 'Word problems', 'subject': 'Math', 'topic': 'Word Problems', 'units': [
                    {'title': 'Understand the problem', 'lessons': [{'title': 'Read the information',
                    'goal': 'Identify what is given.', 'practice_questions': []}]}]}
                table.rows.append({'id': plan_id, 'user_id': 'parent-id', 'child_id': 'child-id',
                    'grade': 5, 'subject': 'Math', 'topic': 'Word Problems', 'content': old,
                    'dialogue': [], 'revision': 0, 'plan_history': [], 'ready_at': 'approved'})
                class Completions:
                    async def parse(self, **kwargs):
                        changed = route.CurriculumPlan(title='Unexpected rewrite', subject='Math', topic='Word Problems',
                            units=[route.CurriculumUnit(title='Skip to applications', lessons=[
                                route.CurriculumLesson(title='New lesson', goal='Jump to new material.')])])
                        answer = route.PlannerResponse(text='Which parts do you already know?',
                            revised_plan=changed, needs_clarification=needs_clarification)
                        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(parsed=answer))])
                route.aclient = types.SimpleNamespace(beta=types.SimpleNamespace(chat=types.SimpleNamespace(completions=Completions())))
                route.guard_reply_payload = lambda text, *_: text
                result = asyncio.run(route.reply_to_learning_plan(route.PlanReplyRequest(kid_id='child-id',
                    plan_id=plan_id, message=message, expected_revision=0), 'Bearer token'))
                self.assertFalse(result['changed'])
                self.assertEqual(result['plan']['content'], old)
                self.assertEqual(result['plan']['ready_at'], 'approved')
                self.assertEqual(result['plan']['plan_history'], [])

    def test_ordered_catalog_and_grade_scope(self):
        route, _ = load_route()
        result = asyncio.run(route.learning_catalog('child-id', 'Bearer token'))
        self.assertEqual(result['learner'], 'Alona')
        self.assertEqual([unit['id'] for unit in result['subjects'][0]['units']],
                         ['fractions', 'percentages'])
        self.assertEqual(result['subjects'][0]['units'][0]['skills'][0]['id'], 'equivalent-fractions')
        self.assertEqual(load_route(4)[0]._public_catalog(4), [])

    def test_grade_library_and_saved_plan_reuse(self):
        route, table = load_route(5)
        library = asyncio.run(route.learning_library('child-id', 'Bearer token'))
        self.assertIn('Dividing fractions', library['subjects'][0]['topics'])
        self.assertNotIn('Dividing fractions', [t for s in
            asyncio.run(load_route(2)[0].learning_library('child-id', 'Bearer token'))['subjects']
            for t in s['topics']])

        calls = []
        class Completions:
            async def parse(self, **kwargs):
                calls.append(kwargs)
                plan = route.CurriculumPlan(title='Understanding division of fractions',
                    subject='Math', topic='Dividing fractions', units=[
                        route.CurriculumUnit(title='Understand the operation', lessons=[
                            route.CurriculumLesson(title='What division asks', goal='Interpret division in context.')])])
                return types.SimpleNamespace(choices=[types.SimpleNamespace(
                    message=types.SimpleNamespace(parsed=plan))])
        route.aclient = types.SimpleNamespace(beta=types.SimpleNamespace(chat=types.SimpleNamespace(
            completions=Completions())))
        request = route.PlanRequest(kid_id='child-id', subject='Math', topic='Dividing fractions')
        first = asyncio.run(route.create_learning_plan(request, 'Bearer token'))
        second = asyncio.run(route.create_learning_plan(request, 'Bearer token'))
        self.assertFalse(first['reused'])
        self.assertTrue(second['reused'])
        self.assertEqual(len(calls), 1)
        self.assertEqual(table.rows[0]['child_id'], 'child-id')
        self.assertEqual(table.rows[0]['grade'], 5)
        self.assertEqual(table.rows[0]['content']['units'][0]['lessons'][0]['title'], 'What division asks')
        with self.assertRaises(route.HTTPException):
            asyncio.run(route.create_learning_plan(route.PlanRequest(kid_id='child-id'), 'Bearer token'))

    def test_plan_conversation_changes_saved_plan_and_preserves_old_version(self):
        route, table = load_route()
        plan_id = str(uuid4())
        old = {'title': 'Fractions', 'subject': 'Math', 'topic': 'Fractions', 'units': [
            {'title': 'The basics', 'lessons': [{'title': 'What is a fraction?',
                                               'goal': 'Recognize equal parts.', 'practice_questions': []}]}]}
        table.rows.append({'id': plan_id, 'user_id': 'parent-id', 'child_id': 'child-id',
                           'grade': 5, 'subject': 'Math', 'topic': 'Fractions', 'content': old,
                           'dialogue': [{'role': 'assistant', 'text': 'Your plan is ready.'}],
                           'revision': 0, 'plan_history': []})
        class Completions:
            async def parse(self, **kwargs):
                revised = route.CurriculumPlan(title='Fractions', subject='Math',
                    topic='Fractions', units=[route.CurriculumUnit(title='Quick review', lessons=[
                        route.CurriculumLesson(title='Check the basics',
                            goal='Verify prior knowledge before harder work.',
                            practice_questions=['Is 2/4 equal to 1/2? Explain.'])])])
                answer = route.PlannerResponse(
                    text='I moved the basics to a quick check and added practice questions.',
                    revised_plan=revised, options=['Add another question'])
                return types.SimpleNamespace(choices=[types.SimpleNamespace(
                    message=types.SimpleNamespace(parsed=answer))])
        route.aclient = types.SimpleNamespace(beta=types.SimpleNamespace(chat=types.SimpleNamespace(
            completions=Completions())))
        route.guard_reply_payload = lambda text, *_: text
        request = route.PlanReplyRequest(kid_id='child-id', plan_id=plan_id,
                                         message='I know the basics. Add questions.', expected_revision=0)
        result = asyncio.run(route.reply_to_learning_plan(request, 'Bearer token'))
        self.assertTrue(result['changed'])
        self.assertEqual(result['plan']['revision'], 1)
        self.assertEqual(result['plan']['content']['units'][0]['lessons'][0]['practice_questions'],
                         ['Is 2/4 equal to 1/2? Explain.'])
        self.assertEqual(table.rows[0]['plan_history'][0]['content'], old)
        self.assertEqual([turn['role'] for turn in table.rows[0]['dialogue']],
                         ['assistant', 'user', 'assistant'])
        with self.assertRaises(route.HTTPException) as stale:
            asyncio.run(route.reply_to_learning_plan(request, 'Bearer token'))
        self.assertEqual(stale.exception.status_code, 409)
        with self.assertRaises(route.HTTPException) as wrong_child:
            asyncio.run(route.learning_plan_audio(route.PlanVoiceRequest(
                kid_id='another-child', plan_id=plan_id, turn_index=0), 'Bearer token'))
        self.assertEqual(wrong_child.exception.status_code, 404)

        saved_audio = {}
        class Storage:
            def from_(self, bucket):
                return self
            def upload(self, path, wav, options):
                saved_audio[path] = wav
        route.sb = types.SimpleNamespace(table=lambda name: table, storage=Storage())
        route._cached_narration = lambda path: path in saved_audio
        route._generate_narration = lambda text, grade: b'wav'
        route.signed_url_cached = lambda bucket, path, expiry: path
        voice = asyncio.run(route.learning_plan_audio(route.PlanVoiceRequest(
            kid_id='child-id', plan_id=plan_id, turn_index=2), 'Bearer token'))
        self.assertIn(f'learning-plans/v1/{plan_id}/2-', voice['url'])
        self.assertEqual(len(saved_audio), 1)
        with self.assertRaises(route.HTTPException) as child_audio:
            asyncio.run(route.learning_plan_audio(route.PlanVoiceRequest(
                kid_id='child-id', plan_id=plan_id, turn_index=1), 'Bearer token'))
        self.assertEqual(child_audio.exception.status_code, 422)

    def test_ready_approval_is_saved_and_a_plan_revision_clears_it(self):
        route, table = load_route()
        plan_id = str(uuid4())
        content = {'title': 'Decimals', 'subject': 'Math', 'topic': 'Decimals', 'units': [
            {'title': 'Place value', 'lessons': [{'title': 'Tenths and hundredths',
              'goal': 'Compare decimal place values.', 'practice_questions': []}]}]}
        table.rows.append({'id': plan_id, 'user_id': 'parent-id', 'child_id': 'child-id',
                           'grade': 5, 'subject': 'Math', 'topic': 'Decimals', 'content': content,
                           'dialogue': [{'role': 'assistant', 'text': 'Your plan is ready.'}],
                           'revision': 0, 'plan_history': [], 'ready_at': None})
        request = route.PlanReadyRequest(kid_id='child-id', plan_id=plan_id, expected_revision=0)
        approved = asyncio.run(route.approve_learning_plan(request, 'Bearer token'))['plan']
        self.assertTrue(approved['ready_at'])
        self.assertEqual(approved['revision'], 1)
        self.assertIn('approved', approved['dialogue'][-1]['text'])
        again = asyncio.run(route.approve_learning_plan(
            route.PlanReadyRequest(kid_id='child-id', plan_id=plan_id, expected_revision=1),
            'Bearer token'))['plan']
        self.assertEqual(len(again['dialogue']), 2)
        with self.assertRaises(route.HTTPException) as stale:
            asyncio.run(route.approve_learning_plan(request, 'Bearer token'))
        self.assertEqual(stale.exception.status_code, 409)
        with self.assertRaises(route.HTTPException) as wrong_child:
            asyncio.run(route.approve_learning_plan(route.PlanReadyRequest(
                kid_id='another-child', plan_id=plan_id, expected_revision=1), 'Bearer token'))
        self.assertEqual(wrong_child.exception.status_code, 404)

        class Completions:
            async def parse(self, **kwargs):
                revised = route.CurriculumPlan(title='Decimals with practice', subject='Math',
                    topic='Decimals', units=[route.CurriculumUnit(title='Place value', lessons=[
                        route.CurriculumLesson(title='Tenths and hundredths',
                            goal='Compare decimal place values with examples.')])])
                answer = route.PlannerResponse(text='I added more practice to the plan.',
                                               revised_plan=revised)
                return types.SimpleNamespace(choices=[types.SimpleNamespace(
                    message=types.SimpleNamespace(parsed=answer))])
        route.aclient = types.SimpleNamespace(beta=types.SimpleNamespace(chat=types.SimpleNamespace(
            completions=Completions())))
        route.guard_reply_payload = lambda text, *_: text
        revised = asyncio.run(route.reply_to_learning_plan(route.PlanReplyRequest(
            kid_id='child-id', plan_id=plan_id, message='Add practice.', expected_revision=1),
            'Bearer token'))['plan']
        self.assertIsNone(revised['ready_at'])
        self.assertEqual(revised['revision'], 2)

    def test_delete_plan_requires_owner_and_current_revision(self):
        route, table = load_route()
        plan_id = str(uuid4())
        other_id = str(uuid4())
        table.rows.extend([
            {'id': plan_id, 'user_id': 'parent-id', 'child_id': 'child-id',
             'revision': 2, 'dialogue': [], 'plan_history': [], 'content': {}},
            {'id': other_id, 'user_id': 'parent-id', 'child_id': 'another-child',
             'revision': 0, 'dialogue': [], 'plan_history': [], 'content': {}},
        ])
        with self.assertRaises(route.HTTPException) as wrong_child:
            asyncio.run(route.delete_learning_plan(route.PlanDeleteRequest(
                kid_id='child-id', plan_id=other_id, expected_revision=0), 'Bearer token'))
        self.assertEqual(wrong_child.exception.status_code, 404)
        with self.assertRaises(route.HTTPException) as stale:
            asyncio.run(route.delete_learning_plan(route.PlanDeleteRequest(
                kid_id='child-id', plan_id=plan_id, expected_revision=1), 'Bearer token'))
        self.assertEqual(stale.exception.status_code, 409)
        result = asyncio.run(route.delete_learning_plan(route.PlanDeleteRequest(
            kid_id='child-id', plan_id=plan_id, expected_revision=2), 'Bearer token'))
        self.assertTrue(result['deleted'])
        self.assertEqual([row['id'] for row in table.rows], [other_id])

    def test_intro_voice_covers_welcome_and_selected_subject(self):
        route, table = load_route()
        saved = {}
        class Storage:
            def from_(self, bucket):
                return self
            def upload(self, path, wav, options):
                saved[path] = wav
        route.sb = types.SimpleNamespace(table=lambda name: table, storage=Storage())
        route._cached_narration = lambda path: path in saved
        route._generate_narration = lambda text, grade: b'voice'
        route.signed_url_cached = lambda bucket, path, expiry: path
        first = asyncio.run(route.learning_plan_intro_audio(route.PlanIntroVoiceRequest(
            kid_id='child-id', stage='welcome'), 'Bearer token'))
        second = asyncio.run(route.learning_plan_intro_audio(route.PlanIntroVoiceRequest(
            kid_id='child-id', stage='welcome'), 'Bearer token'))
        subject = asyncio.run(route.learning_plan_intro_audio(route.PlanIntroVoiceRequest(
            kid_id='child-id', stage='subject', subject='Math'), 'Bearer token'))
        self.assertEqual(first, second)
        self.assertIn('learning-plans/intro/child-id/welcome-', first['url'])
        self.assertIn('subject-', subject['url'])
        self.assertEqual(len(saved), 2)
        with self.assertRaises(route.HTTPException) as invalid:
            asyncio.run(route.learning_plan_intro_audio(route.PlanIntroVoiceRequest(
                kid_id='child-id', stage='subject', subject='Astronomy'), 'Bearer token'))
        self.assertEqual(invalid.exception.status_code, 422)

    def test_start_reply_resume_isolated_to_parent_and_child(self):
        route, table = load_route()

        async def answer(*args):
            if args[5]:
                return {'text': 'Good choice. What do you notice about the shaded area?', 'options': []}
            return {'text': 'Hi Alona. Which bar shows more?', 'options': ['5/8', '3/4']}

        route._generate = answer
        created = asyncio.run(route.start_learning(
            route.Start(kid_id='child-id', unit_id='fractions', skill_id='equivalent-fractions'),
            'Bearer token'))
        self.assertEqual(table.rows[0]['user_id'], 'parent-id')
        self.assertEqual(table.rows[0]['child_id'], 'child-id')
        self.assertEqual(created['turn_count'], 1)
        self.assertEqual(created['turns'][0]['options'], ['5/8', '3/4'])

        reply = asyncio.run(route.reply_learning(route.Reply(
            kid_id='child-id', session_id=created['session_id'], message='Both are the same size.',
            expected_turn_count=1), 'Bearer token'))
        self.assertEqual(reply['turn_count'], 3)
        self.assertEqual(reply['options'], [])
        resumed = asyncio.run(route.resume_learning(route.Resume(
            kid_id='child-id', session_id=created['session_id']), 'Bearer token'))
        self.assertEqual([turn['role'] for turn in resumed['turns']], ['assistant', 'user', 'assistant'])
        self.assertEqual(resumed['turns'][0]['options'], ['5/8', '3/4'])

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

    def test_choices_are_optional_short_and_distinct(self):
        route, _ = load_route()
        self.assertEqual(route._answer_options([' 5/8 ', '3/4', '5/8']), ['5/8', '3/4'])
        self.assertEqual(route._answer_options(['Only one']), [])
        self.assertEqual(route._answer_options(['A' * 81, 'B']), [])

    def test_audio_is_only_for_owned_teacher_turns(self):
        route, table = load_route()
        session_id = str(uuid4())
        table.rows.append({'id': session_id, 'user_id': 'parent-id', 'child_id': 'child-id',
                           'turns': [{'role': 'assistant', 'text': 'Hello Alona.'},
                                     {'role': 'user', 'text': 'My private answer'}]})
        route.signed_url_cached = lambda bucket, path, expiry: f'{bucket}/{path}'
        result = asyncio.run(route.learning_audio(route.AudioRequest(
            kid_id='child-id', session_id=session_id, turn_index=0), 'Bearer token'))
        self.assertIn('2027-eng-lesson-audio/learning/v1/', result['url'])
        for kid_id, index, expected_status in [('child-id', 1, 422), ('another-child', 0, 404)]:
            with self.assertRaises(route.HTTPException) as invalid:
                asyncio.run(route.learning_audio(route.AudioRequest(
                    kid_id=kid_id, session_id=session_id, turn_index=index), 'Bearer token'))
            self.assertEqual(invalid.exception.status_code, expected_status)

    def test_audio_is_generated_once_then_reused(self):
        route, table = load_route()
        session_id = str(uuid4())
        table.rows.append({'id': session_id, 'user_id': 'parent-id', 'child_id': 'child-id',
                           'turns': [{'role': 'assistant', 'text': 'Which bar is greater?'}]})
        saved, calls = {}, []

        class Storage:
            def from_(self, bucket):
                self.bucket = bucket
                return self

            def upload(self, path, data, options):
                saved[path] = data

        route.sb = types.SimpleNamespace(table=lambda name: table, storage=Storage())
        route._cached_narration = lambda path: path in saved
        route._generate_narration = lambda text, grade: calls.append((text, grade)) or b'wav'
        route.signed_url_cached = lambda bucket, path, expiry: path
        request = route.AudioRequest(kid_id='child-id', session_id=session_id, turn_index=0)
        first = asyncio.run(route.learning_audio(request, 'Bearer token'))
        second = asyncio.run(route.learning_audio(request, 'Bearer token'))
        self.assertEqual(first, second)
        self.assertEqual(len(saved), 1)
        self.assertEqual(calls, [('Which bar is greater?', 5)])


if __name__ == '__main__':
    unittest.main()
