#!/usr/bin/env python3
"""Re-run the read-only half of the security audit.

    backend/.venv/bin/python tools/security_check.py

Everything here is a read: anonymous SELECTs with the publishable key that every
visitor's browser already holds, GETs against the two Render services, and a header
check on the site. Nothing writes, nothing signs in, nothing is attacked. The findings
and their history live in SECURITY.md.

The other half of the audit — what a *signed-in stranger* can reach — needs a real
account and so is not automated here; SECURITY.md describes how it was done.
"""
import os, sys
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend/.env'))
URL = os.environ['SUPABASE_URL']
ANON = os.environ['SUPABASE_PUBLISHABLE_KEY']

# Tables an anonymous visitor must not see. A row here is a finding.
CLOSED = [
    'kid_unit_lesson_progress', 'lesson_units_content', 'game_questions', 'subscriptions',
    'kids_profiles', 'kids_chats', 'kids_memory', 'support_messages', 'support_tickets',
    'app_admins', 'kid_question_answers', 'tutor_sessions', 'usage_summary',
    'learning_lessons', 'lesson_plans', 'kid_game_sessions', 'homework_sessions',
    'exams', 'exam_questions', 'exam_answer_keys',
]
# Tables that are public on purpose.
OPEN_BY_DESIGN = {'hebrew_nikud': 'the shared nikud dictionary'}

BACKENDS = ['https://iakids-backend.onrender.com', 'https://iakids-ai-tutor-he.onrender.com']
HEADERS_WANTED = ['content-security-policy', 'strict-transport-security', 'x-frame-options',
                  'x-content-type-options', 'referrer-policy', 'permissions-policy']

RED, GREEN, DIM, OFF = '\033[31m', '\033[32m', '\033[2m', '\033[0m'


def rows(table):
    """How many rows an anonymous caller gets, or None if the read failed."""
    r = httpx.get(f'{URL}/rest/v1/{table}?select=*&limit=1', timeout=25,
                  headers={'apikey': ANON, 'Authorization': f'Bearer {ANON}', 'Prefer': 'count=exact'})
    if r.status_code >= 400:
        return None
    total = (r.headers.get('content-range') or '*/0').split('/')[-1]
    return 0 if total in ('*', '0') else int(total)


def main():
    findings = 0

    print('\nAnonymous reads — the publishable key every visitor holds')
    for t in CLOSED:
        n = rows(t)
        if n is None:
            print(f'  {t:28} {DIM}no answer (table missing, or blocked outright){OFF}')
        elif n:
            findings += 1
            print(f'  {t:28} {RED}OPEN — {n} rows{OFF}')
        else:
            print(f'  {t:28} {GREEN}closed{OFF}')
    for t, why in OPEN_BY_DESIGN.items():
        n = rows(t)
        print(f'  {t:28} {DIM}{n} rows — public on purpose ({why}){OFF}')

    print('\nBackends')
    for b in BACKENDS:
        name = b.split('//')[1]
        for path in ('/docs', '/redoc', '/openapi.json'):
            try:
                code = httpx.get(b + path, timeout=30).status_code
            except Exception as e:
                print(f'  {name:32}{path:14} {DIM}{type(e).__name__}{OFF}')
                continue
            if code == 200:
                findings += 1
                print(f'  {name:32}{path:14} {RED}200 — public{OFF}')
            else:
                print(f'  {name:32}{path:14} {GREEN}{code}{OFF}')

    print('\nResponse headers on the site')
    r = httpx.get('https://iakids.app/he/games/workspace/', timeout=30)
    for h in HEADERS_WANTED:
        v = r.headers.get(h)
        if v:
            print(f'  {h:28} {GREEN}{v[:60]}{OFF}')
        else:
            findings += 1
            print(f'  {h:28} {RED}missing{OFF}')

    print(f'\n{findings} finding{"" if findings == 1 else "s"}. SECURITY.md has what each one means.\n')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
