from pathlib import Path

backend = Path('backend-ai-tutor-he/main.py')
s = backend.read_text(encoding='utf-8')

needle = '''        # =============================================\n        # UNIT LESSON PROGRESS START\n        #\n        # Unit lesson progress is started only from the\n        # explicit requested_unit_lesson_id path below.\n        # This avoids marking a fallback/default unit lesson\n        # as in_progress when the child selected another lesson.\n\n        # =============================================\n        # TUTOR SESSION\n'''
replacement = '''        # =============================================\n        # UNIT LESSON PROGRESS START\n        #\n        # lesson-intro is the authoritative lesson-open event.\n        # It already carries the exact selected unit_lesson_id,\n        # so mark that lesson in_progress here.\n        # =============================================\n\n        start_kid_unit_lesson_progress(\n            kid_id=child["id"],\n            learning_lesson_id=parent_lesson["id"],\n            unit_lesson_id=body.unit_lesson_id\n        )\n\n        # =============================================\n        # TUTOR SESSION\n'''

if needle not in s:
    raise SystemExit('lesson-intro progress insertion point not found')

s = s.replace(needle, replacement, 1)
backend.write_text(s, encoding='utf-8')

front = Path('he/workspace/index.html')
f = front.read_text(encoding='utf-8')
if 'IAKIDS • build 0.8.6' in f:
    f = f.replace('IAKIDS • build 0.8.6', 'IAKIDS • build 0.8.7', 1)
elif 'IAKIDS • build 0.8.5' in f:
    f = f.replace('IAKIDS • build 0.8.5', 'IAKIDS • build 0.8.7', 1)
else:
    raise SystemExit('expected visible build stamp not found')
front.write_text(f, encoding='utf-8')

out = backend.read_text(encoding='utf-8')
assert 'lesson-intro is the authoritative lesson-open event' in out
assert 'unit_lesson_id=body.unit_lesson_id' in out
assert 'IAKIDS • build 0.8.7' in front.read_text(encoding='utf-8')
print('v0.8.7 lesson-intro progress start applied')
