from pathlib import Path

backend = Path('backend-ai-tutor-he/main.py')
s = backend.read_text(encoding='utf-8')

old_backend = '''        # =============================================\n        # UNIT LESSON PROGRESS START\n        #\n        # lesson-intro is the real entry point used by\n        # the current workspace when a child opens an\n        # internal lesson. Persist that start here.\n        # =============================================\n\n        start_kid_unit_lesson_progress(\n            kid_id=child["id"],\n            learning_lesson_id=parent_lesson["id"],\n            unit_lesson_id=unit_lesson["id"]\n        )\n'''

new_backend = '''        # =============================================\n        # UNIT LESSON PROGRESS START\n        #\n        # lesson-intro is the authoritative lesson-open event.\n        # It carries the exact lesson selected by the child.\n        # Never use a fallback/default unit_lesson here, because\n        # that can incorrectly mark lesson 1 as in_progress.\n        # =============================================\n\n        start_kid_unit_lesson_progress(\n            kid_id=child["id"],\n            learning_lesson_id=parent_lesson["id"],\n            unit_lesson_id=body.unit_lesson_id\n        )\n'''

if old_backend in s:
    s = s.replace(old_backend, new_backend, 1)
elif 'unit_lesson_id=body.unit_lesson_id' not in s:
    raise SystemExit('backend lesson-intro progress anchor not found')

backend.write_text(s, encoding='utf-8')

front = Path('he/workspace/index.html')
f = front.read_text(encoding='utf-8')

old_front = '''function openStudentLessonProgressPanel(){\n  const stage=document.querySelector(".lesson-visual-stage"); if(!stage) return;\n  document.getElementById("studentLessonProgressPanel")?.remove();\n  const rows=window.LESSON_SIDEBAR_ROWS||[]; const pmap=new Map((window.LESSON_SIDEBAR_PROGRESS_ROWS||[]).map(r=>[Number(r.unit_lesson_id),r]));'''

new_front = '''async function openStudentLessonProgressPanel(){\n  const stage=document.querySelector(".lesson-visual-stage"); if(!stage) return;\n  document.getElementById("studentLessonProgressPanel")?.remove();\n  const rows=window.LESSON_SIDEBAR_ROWS||[];\n\n  // Always refresh progress from DB before rendering.\n  // This prevents stale cached rows from showing lesson 1\n  // as in_progress after the child has opened lesson 2/3/etc.\n  if(CURRENT_KID?.id && rows.length){\n    const lessonIds = rows.map(row => Number(row.id)).filter(Boolean);\n    const { data: freshProgressRows, error: freshProgressError } = await sb\n      .from("kid_unit_lesson_progress")\n      .select("unit_lesson_id,status,progress_percent,current_stage,last_part_number,mastery_score,best_mastery_score,attempts_count,last_activity_at,completed_at")\n      .eq("kid_id", CURRENT_KID.id)\n      .in("unit_lesson_id", lessonIds);\n\n    if(freshProgressError){\n      console.warn("STUDENT PROGRESS PANEL FRESH LOAD WARNING:", freshProgressError);\n    } else {\n      window.LESSON_SIDEBAR_PROGRESS_ROWS = Array.isArray(freshProgressRows)\n        ? freshProgressRows\n        : [];\n    }\n  }\n\n  const pmap=new Map((window.LESSON_SIDEBAR_PROGRESS_ROWS||[]).map(r=>[Number(r.unit_lesson_id),r]));'''

if old_front in f:
    f = f.replace(old_front, new_front, 1)
elif 'async function openStudentLessonProgressPanel()' not in f:
    raise SystemExit('front progress panel anchor not found')

front.write_text(f, encoding='utf-8')

out_b = backend.read_text(encoding='utf-8')
out_f = front.read_text(encoding='utf-8')
assert 'unit_lesson_id=body.unit_lesson_id' in out_b
assert 'async function openStudentLessonProgressPanel()' in out_f
assert 'STUDENT PROGRESS PANEL FRESH LOAD WARNING' in out_f
print('lesson progress fix restored')
