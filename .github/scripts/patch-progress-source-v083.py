from pathlib import Path

backend = Path('backend-ai-tutor-he/main.py')
s = backend.read_text(encoding='utf-8')

old = '''        # lesson-intro is the real entry point used by
        # the current workspace when a child opens an
        # internal lesson. Persist that start here.
        # =============================================

        start_kid_unit_lesson_progress(
            kid_id=child["id"],
            learning_lesson_id=parent_lesson["id"],
            unit_lesson_id=unit_lesson["id"]
        )
'''

count = s.count(old)
if count != 1:
    raise SystemExit(f'expected exactly one legacy lesson-intro progress call, found {count}')

replacement = '''        # Unit lesson progress is started only from the
        # explicit requested_unit_lesson_id path below.
        # This avoids marking a fallback/default unit lesson
        # as in_progress when the child selected another lesson.
'''
s = s.replace(old, replacement, 1)

# Safety checks: requested_unit_lesson_id source remains authoritative.
required = '''        if is_lesson_start and requested_unit_lesson_id is not None:
            start_kid_unit_lesson_progress(
                kid_id=child["id"],
                learning_lesson_id=lesson["id"],
                unit_lesson_id=requested_unit_lesson_id
            )'''
if required not in s:
    raise SystemExit('authoritative requested_unit_lesson_id progress call not found')

backend.write_text(s, encoding='utf-8')

front = Path('he/workspace/index.html')
f = front.read_text(encoding='utf-8')
if 'IAKIDS • build 0.8.2' not in f:
    raise SystemExit('build 0.8.2 stamp not found')
f = f.replace('IAKIDS • build 0.8.2', 'IAKIDS • build 0.8.3', 1)
front.write_text(f, encoding='utf-8')

# Final validation.
out = backend.read_text(encoding='utf-8')
if 'unit_lesson_id=unit_lesson["id"]' in out and old.strip() in out:
    raise SystemExit('legacy progress start call still present')
if required not in out:
    raise SystemExit('requested progress start call missing after patch')
if 'IAKIDS • build 0.8.3' not in front.read_text(encoding='utf-8'):
    raise SystemExit('build stamp validation failed')

print('v0.8.3: single authoritative unit lesson progress source applied')
