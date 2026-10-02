"""Shared, country-neutral mathematics discovery map for the 2027 product."""
import json
from pathlib import Path

TABLE = '2027_curriculum_map'
VERSION = 1

def bundled_nodes():
    return json.loads((Path(__file__).parent / 'data/2027_math_curriculum.json').read_text())

def nodes(sb):
    try:
        rows = sb.table(TABLE).select('id,parent_id,level,title,sort_order,subject').eq('active', True).order('sort_order').limit(1000).execute().data
        if rows:
            return rows
    except Exception:
        pass
    # Same versioned seed keeps discovery usable during a database outage.
    return bundled_nodes()

def tree(sb):
    rows = nodes(sb)
    def children(parent):
        return [{**row, 'children': children(row['id'])} for row in sorted(rows, key=lambda r: r['sort_order']) if row['parent_id'] == parent]
    return children(None)

def selection(sb, topic_id):
    rows = nodes(sb)
    topic = next((r for r in rows if r['id'] == topic_id and r['level'] == 2), None)
    if not topic:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail='Choose an available curriculum topic.')
    domain = next(r for r in rows if r['id'] == topic['parent_id'])
    skills = sorted((r for r in rows if r['parent_id'] == topic_id), key=lambda r: r['sort_order'])
    return {'version': VERSION, 'subject': 'Math', 'domain_id': domain['id'], 'domain': domain['title'],
            'topic_id': topic_id, 'topic': topic['title'], 'skills': [{'id': r['id'], 'title': r['title']} for r in skills]}

def guidance(scope):
    return ('\nCurriculum scope: ' + json.dumps(scope) +
        '\nUse this country-neutral topic map as the coverage checklist. Grade guides language and starting difficulty, '
        'not a rigid national syllabus. Cover all listed skills in a prerequisite-safe sequence; scaffold harder skills. '
        'Choose the number of units and lessons freely within the response limits. Do not expand into sibling topics '
        'except necessary prerequisite review. Keep mathematical questions unambiguous: expanding a fraction means '
        'multiplying BOTH numerator and denominator by the same nonzero number, not multiplying its value. '
        'Include varied practice and checks for understanding.') if scope else ''
