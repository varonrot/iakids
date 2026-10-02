import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from eng_curriculum_map_2027 import bundled_nodes, tree, selection
from test_eng_test_prep_planner_2027 import load, pack
from uuid import uuid4

class MapTests(unittest.TestCase):
    def test_complete_connected_three_level_map(self):
        rows = bundled_nodes(); by_id = {r['id']: r for r in rows}
        self.assertEqual(len(by_id), len(rows))
        self.assertEqual([sum(r['level'] == n for r in rows) for n in (1,2,3)], [10,80,341])
        for r in rows:
            if r['level'] > 1:
                self.assertEqual(by_id[r['parent_id']]['level'], r['level'] - 1)
        sb = SimpleNamespace(table=lambda _: (_ for _ in ()).throw(RuntimeError()))
        self.assertEqual(len(tree(sb)), 10)
        scope = selection(sb, 'fractions--dividing-fractions')
        self.assertEqual(scope['topic'], 'Dividing Fractions')
        self.assertEqual(len(scope['skills']), 6)

    def test_explicit_selection_builds_without_extra_chat(self):
        m, table = load()
        row = {'id':str(uuid4()), 'user_id':'parent', 'child_id':'kid', 'grade':5, 'mode':'topics', 'topic':'', 'subject':'', 'source_text':'', 'dialogue':[], 'revision':0, 'approved_at':None, 'answers':{}}
        table.rows = [row]
        selected = {'subject':'Math', 'topic':'Dividing Fractions', 'topic_id':'fractions--dividing-fractions'}
        with patch.object(m, 'curriculum_selection', return_value=selected), patch.object(m, '_pack', new=AsyncMock(return_value=pack())) as generate, patch.object(m, '_parse', new=AsyncMock()) as chat:
            result = asyncio.run(m.reply(m.ReplyRequest(kid_id='kid',session_id=row['id'],revision=0,message='Dividing Fractions',curriculum_topic_id=selected['topic_id'])))
        chat.assert_not_called(); generate.assert_awaited_once()
        self.assertEqual(result['topic'], selected['topic'])
        self.assertEqual(row['curriculum_topic_id'], selected['topic_id'])
        self.assertNotIn('correct_index', result['pack']['questions'][0])
