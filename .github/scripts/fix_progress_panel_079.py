from pathlib import Path

# Build 0.7.9 direct Supabase progress refresh patch.
path = Path('he/workspace/index.html')
text = path.read_text(encoding='utf-8')
original = text

old = '''  try{\n    await loadLessonSidebarProgress();\n  }catch(err){\n    console.warn("LESSON PROGRESS REFRESH WARNING:",err);\n  }\n'''

new = '''  try{\n    const progressKidId = CURRENT_KID?.id || window.ACTIVE_KID_ID || null;\n    const progressParentLessonId = Number(\n      CURRENT_PARENT_LESSON?.id\n      || window.CURRENT_LESSON_ID\n      || 0\n    );\n\n    if(progressKidId && progressParentLessonId){\n      const { data: freshProgressRows, error: freshProgressError } = await sb\n        .from("kid_unit_lesson_progress")\n        .select(`\n          unit_lesson_id,\n          status,\n          progress_percent,\n          mastery_score,\n          best_mastery_score,\n          last_activity_at,\n          completed_at\n        `)\n        .eq("kid_id", progressKidId)\n        .eq("learning_lesson_id", progressParentLessonId);\n\n      if(freshProgressError){\n        console.warn("LESSON PROGRESS REFRESH WARNING:", freshProgressError);\n      }else{\n        window.LESSON_SIDEBAR_PROGRESS_ROWS = Array.isArray(freshProgressRows)\n          ? freshProgressRows\n          : [];\n      }\n    }\n  }catch(err){\n    console.warn("LESSON PROGRESS REFRESH WARNING:",err);\n  }\n'''

if old not in text:
    raise SystemExit('0.7.8 refresh call not found')
text = text.replace(old, new, 1)

if 'IAKIDS • build 0.7.8' not in text:
    raise SystemExit('Build 0.7.8 stamp not found')
text = text.replace('IAKIDS • build 0.7.8', 'IAKIDS • build 0.7.9', 1)

# Keep the nearby build comment aligned with the visible stamp when present.
text = text.replace('build 0.7.8', 'build 0.7.9', 1)

if text == original:
    raise SystemExit('No changes required')

path.write_text(text, encoding='utf-8')
print('Fixed direct progress refresh and bumped build to 0.7.9')
