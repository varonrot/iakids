from pathlib import Path

MAIN = Path('backend-ai-tutor-he/main.py')
INDEX = Path('he/workspace/index.html')

text = MAIN.read_text(encoding='utf-8')

old = 'LEARNING_COACH_MAX_ROUNDS = 5\n'
new = '''LEARNING_COACH_MAX_ROUNDS = 5\n\n\ndef get_learning_coach_round_limit(understanding_score: int) -> int:\n    \"\"\"Adaptive diagnostic limit: do not trap a child until mastery.\n\n    High scores need very little extra probing; lower scores get a few more\n    focused turns so we can identify the weakness, then the lesson continues.\n    The score is still preserved as diagnostic evidence.\n    \"\"\"\n    score = max(0, min(100, int(understanding_score or 0)))\n\n    if score >= 90:\n        return 1\n    if score >= 70:\n        return 2\n    if score >= 40:\n        return 3\n    return 4\n'''
if old not in text:
    raise SystemExit('Could not find LEARNING_COACH_MAX_ROUNDS anchor')
text = text.replace(old, new, 1)

old = '''    max_rounds_reached = (\n        current_round\n        >= LEARNING_COACH_MAX_ROUNDS\n    )\n\n    if goal_achieved:\n        status = \"completed\"\n\n    elif max_rounds_reached:\n        status = \"max_rounds\"\n'''
new = '''    recommended_round_limit = min(\n        LEARNING_COACH_MAX_ROUNDS,\n        get_learning_coach_round_limit(understanding_score)\n    )\n\n    max_rounds_reached = (\n        current_round\n        >= recommended_round_limit\n    )\n\n    if goal_achieved:\n        status = \"completed\"\n\n    elif max_rounds_reached:\n        # Diagnostic completion: the child can continue even below mastery.\n        # We intentionally keep the existing DB-safe status value.\n        status = \"max_rounds\"\n'''
if old not in text:
    raise SystemExit('Could not find update_learning_coach_session max-rounds block')
text = text.replace(old, new, 1)

old = '''    max_rounds_reached = (\n        current_round\n        >= LEARNING_COACH_MAX_ROUNDS\n    )\n\n    coach_finished = (\n        goal_achieved\n        or max_rounds_reached\n    )\n'''
new = '''    recommended_round_limit = min(\n        LEARNING_COACH_MAX_ROUNDS,\n        get_learning_coach_round_limit(understanding_score)\n    )\n\n    max_rounds_reached = (\n        current_round\n        >= recommended_round_limit\n    )\n\n    # Separate mastery from flow completion. A child does NOT need 90+ to move on.\n    # Low/medium scores are retained as diagnostic evidence and the lesson continues\n    # after a small adaptive number of focused turns.\n    coach_finished = (\n        goal_achieved\n        or max_rounds_reached\n    )\n'''
if old not in text:
    raise SystemExit('Could not find route coach_finished block')
text = text.replace(old, new, 1)

# Expose the adaptive limit in the response for frontend/debugging if a maximum_rounds
# field already exists in the runtime response block.
text = text.replace(
    '''            \"maximum_rounds\":\n                LEARNING_COACH_MAX_ROUNDS,\n\n            \"understanding_score\":''',
    '''            \"maximum_rounds\":\n                recommended_round_limit,\n\n            \"understanding_score\":''',
    1
)

MAIN.write_text(text, encoding='utf-8')

if INDEX.exists():
    idx = INDEX.read_text(encoding='utf-8')
    idx = idx.replace('IAKIDS • build 0.7.119', 'IAKIDS • build 0.7.120')
    idx = idx.replace('window.IAKIDS_BUILD_VERSION = "0.7.119";', 'window.IAKIDS_BUILD_VERSION = "0.7.120";')
    INDEX.write_text(idx, encoding='utf-8')

print('Adaptive Learning Coach applied; build 0.7.120')
