from pathlib import Path

p = Path('backend-ai-tutor-he/main.py')
text = p.read_text(encoding='utf-8')

needle = '''        parent_lesson = get_learning_lesson(
            unit_lesson[
                "learning_lesson_id"
            ]
        )
        # =============================================
        # TUTOR SESSION
'''
replacement = '''        parent_lesson = get_learning_lesson(
            unit_lesson[
                "learning_lesson_id"
            ]
        )

        # =============================================
        # UNIT LESSON PROGRESS START
        #
        # lesson-intro is the real entry point used by
        # the current workspace when a child opens an
        # internal lesson. Persist that start here.
        # =============================================

        start_kid_unit_lesson_progress(
            kid_id=child["id"],
            learning_lesson_id=parent_lesson["id"],
            unit_lesson_id=unit_lesson["id"]
        )

        # =============================================
        # TUTOR SESSION
'''

if needle not in text:
    raise SystemExit('lesson-intro insertion point not found')
if 'lesson-intro is the real entry point used by' in text:
    raise SystemExit('patch already applied')
text = text.replace(needle, replacement, 1)
p.write_text(text, encoding='utf-8')

p2 = Path('he/workspace/index.html')
idx = p2.read_text(encoding='utf-8')
if 'IAKIDS • build 0.5.9' not in idx:
    raise SystemExit('expected build 0.5.9 marker not found')
idx = idx.replace('IAKIDS • build 0.5.9', 'IAKIDS • build 0.6.0')
idx = idx.replace('window.IAKIDS_BUILD_VERSION = "0.5.9";', 'window.IAKIDS_BUILD_VERSION = "0.6.0";')
p2.write_text(idx, encoding='utf-8')
