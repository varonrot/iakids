from pathlib import Path

path = Path('he/parent-panel/index.html')
text = path.read_text(encoding='utf-8')

repls = [
    ('<title>פאנל הורים | חבר לימודים AI</title>', '<title>פאנל הורים | חבר לימודים AI</title>\n<!-- IAKIDS parent panel build 0.7.1 -->'),
    ('.from("kid_lesson_progress")', '.from("kid_unit_lesson_progress")'),
    ('בדקו את הרשאות הגישה לטבלת kid_lesson_progress.', 'בדקו את הרשאות הגישה לטבלת kid_unit_lesson_progress.'),
    ('.map(row => row.lesson_id)', '.map(row => row.unit_lesson_id)'),
    ('.from("learning_lessons")\n      .select(`\n        id,\n        grade,\n        subject,\n        category,\n        lesson_order,\n        lesson_name,\n        is_checkpoint\n      `)', '.from("lesson_units_content")\n      .select(`\n        id,\n        learning_lesson_id,\n        grade,\n        subject,\n        parent_lesson,\n        unit_order,\n        unit_name,\n        lesson_order,\n        lesson_name\n      `)'),
    ('const lesson=lessonMap.get(row.lesson_id);', 'const lesson=lessonMap.get(row.unit_lesson_id);'),
]

for old, new in repls:
    if old not in text:
        raise SystemExit(f'missing target: {old[:100]!r}')
    text = text.replace(old, new)

# Avoid falsely classifying untouched 0/0 rows as weak merely because the new per-unit table is not yet updating mastery/progress mid-lesson.
old_weak = '''  const weak=progress\n    .filter(r=>\n      safeNumber(r.mastery_score)<55 ||\n      safeNumber(r.consecutive_failures)>=2 ||\n      safeNumber(r.hints_used)>=3\n    )'''
new_weak = '''  const weak=progress\n    .filter(r=>\n      (safeNumber(r.mastery_score)>0 && safeNumber(r.mastery_score)<55) ||\n      safeNumber(r.consecutive_failures)>=2 ||\n      safeNumber(r.hints_used)>=3\n    )'''
if old_weak not in text:
    raise SystemExit('missing weak insights target')
text = text.replace(old_weak, new_weak)

path.write_text(text, encoding='utf-8')
print('patched parent panel to kid_unit_lesson_progress build 0.7.1')
