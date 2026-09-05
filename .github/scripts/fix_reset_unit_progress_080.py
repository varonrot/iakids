from pathlib import Path

# Re-run backend reset synchronization patch.
path = Path('backend-ai-tutor-he/main.py')
text = path.read_text(encoding='utf-8')
original = text

marker = '''        # =============================================\n        # RESET MAIN PROGRESS ROW\n        #\n        # kid_lesson_progress היא רשומה אחת לנושא,\n        # לכן לא מוחקים אותה אלא מאפסים אותה\n        # ומכוונים לתת־השיעור שנבחר.\n        # =============================================\n'''

if marker not in text:
    raise SystemExit('Reset main progress marker not found')

insert = '''        # =============================================\n        # RESET UNIT LESSON PROGRESS ROW\n        #\n        # kid_unit_lesson_progress היא טבלת ההתקדמות\n        # החדשה ברמת תת־השיעור. כפתור \"להתחיל מחדש\"\n        # חייב לאפס גם אותה, אחרת השיעור נשאר completed\n        # למרות שהטבלה הראשית הישנה כבר אופסה.\n        # =============================================\n\n        unit_progress_reset = (\n            sb.table(\n                \"kid_unit_lesson_progress\"\n            )\n            .update({\n                \"status\":\n                    \"in_progress\",\n\n                \"progress_percent\":\n                    0,\n\n                \"current_stage\":\n                    LESSON_STAGE_INTRO,\n\n                \"last_part_number\":\n                    1,\n\n                \"mastery_score\":\n                    0,\n\n                \"best_mastery_score\":\n                    0,\n\n                \"attempts_count\":\n                    0,\n\n                \"started_at\":\n                    now_iso,\n\n                \"last_activity_at\":\n                    now_iso,\n\n                \"completed_at\":\n                    None,\n\n                \"updated_at\":\n                    now_iso\n            })\n            .eq(\n                \"kid_id\",\n                child[\"id\"]\n            )\n            .eq(\n                \"learning_lesson_id\",\n                lesson[\"id\"]\n            )\n            .eq(\n                \"unit_lesson_id\",\n                unit_lesson[\"id\"]\n            )\n            .execute()\n        )\n\n'''

if 'RESET UNIT LESSON PROGRESS ROW' not in text:
    text = text.replace(marker, insert + marker, 1)

text = text.replace(
    '''                    \"progress_reset\":\n                        progress is not None,\n''',
    '''                    \"progress_reset\":\n                        progress is not None,\n\n                    \"unit_progress_reset\":\n                        bool(\n                            unit_progress_reset.data\n                            or []\n                        ),\n''',
    1,
)

text = text.replace(
    '''                \"lesson_progress\":\n                    True\n''',
    '''                \"lesson_progress\":\n                    True,\n\n                \"unit_lesson_progress\":\n                    True\n''',
    1,
)

if text == original:
    raise SystemExit('No changes required')

path.write_text(text, encoding='utf-8')
print('Patched reset endpoint to reset kid_unit_lesson_progress')
