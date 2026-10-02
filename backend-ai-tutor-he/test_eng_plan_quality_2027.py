import asyncio
import copy
import types
import unittest
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from test_eng_learning_2027 import load_route


class PlanQualityTests(unittest.TestCase):
    def setup_review(self, reviews):
        route, table = load_route()
        draft = route.CurriculumPlan(title='Equivalent fractions', subject='Math', topic='Equivalent Fractions',
            units=[route.CurriculumUnit(title='Find equal fractions', lessons=[route.CurriculumLesson(
                title='Expand fractions', goal='Multiply both parts by the same factor.',
                practice_questions=['Multiply both the numerator and denominator of 2/5 by 3.'])])])
        self.calls = []
        async def parse(**kwargs):
            self.calls.append(kwargs)
            value = reviews.pop(0)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(parsed=value))])
        route.aclient = types.SimpleNamespace(beta=types.SimpleNamespace(chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(parse=parse))))
        return route, table, draft

    def test_correction_is_reviewed_again_and_scope_is_preserved(self):
        reviews=[]
        route, _, draft=self.setup_review(reviews)
        reviews.extend([route.CurriculumPlanReview(approved=False, blocking_issues=['Conflicting quantities'],
            corrected_plan=draft), route.CurriculumPlanReview(approved=True)])
        content=draft.model_dump(); content['curriculum_scope']={'topic_id':'fractions--equivalent-fractions'}
        content['units'][0]['lessons'][0]['practice_questions']=['4/5 of 20 pupils is 7 pupils. How many?']
        out=asyncio.run(route._review_plan_content('parent-id',5,content))
        self.assertEqual(len(self.calls),2)
        self.assertEqual(out['curriculum_scope'],content['curriculum_scope'])
        self.assertEqual(out['plan_quality_version'],1)
        self.assertNotIn('7 pupils',str(out))

    def test_unapproved_repair_never_passes_and_retries_are_bounded(self):
        reviews=[]
        route, _, draft=self.setup_review(reviews)
        reviews.extend([route.CurriculumPlanReview(approved=False, blocking_issues=['Still incorrect'],
            corrected_plan=draft)]*3)
        with self.assertRaises(route.HTTPException):
            asyncio.run(route._review_plan_content('parent-id',5,draft.model_dump()))
        self.assertEqual(len(self.calls),3)

    def test_approved_flag_with_blocking_issues_is_rejected(self):
        reviews=[]
        route, _, draft=self.setup_review(reviews)
        reviews.append(route.CurriculumPlanReview(approved=True,blocking_issues=['Wrong answer']))
        with self.assertRaises(route.HTTPException):
            asyncio.run(route._review_plan_content('parent-id',5,draft.model_dump()))

    def test_failed_review_does_not_save_new_plan(self):
        reviews=[]
        route, table, draft=self.setup_review(reviews)
        reviews.extend([draft,route.CurriculumPlanReview(approved=False,blocking_issues=['Wrong answer'])])
        with self.assertRaises(route.HTTPException):
            asyncio.run(route.create_learning_plan(route.PlanRequest(kid_id='child-id',subject='Math',
                topic='Equivalent Fractions'),'Bearer token'))
        self.assertEqual(table.rows,[])

    def test_failed_edit_review_preserves_saved_plan_and_history(self):
        reviews=[]
        route, table, draft=self.setup_review(reviews)
        plan_id=str(uuid4())
        saved={'id':plan_id,'user_id':'parent-id','child_id':'child-id','grade':5,
            'subject':'Math','topic':'Equivalent Fractions','content':draft.model_dump(),
            'dialogue':[],'revision':0,'plan_history':[],'ready_at':None}
        table.rows=[saved]; original=copy.deepcopy(saved)
        reviews.extend([route.PlannerResponse(text='I added more practice.',revised_plan=draft),
            route.CurriculumPlanReview(approved=False,blocking_issues=['Contradictory practice'])])
        with self.assertRaises(route.HTTPException):
            asyncio.run(route.reply_to_learning_plan(route.PlanReplyRequest(kid_id='child-id',
                plan_id=plan_id,message='Add more practice questions',expected_revision=0),'Bearer token'))
        self.assertEqual(table.rows,[original])
