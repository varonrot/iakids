from pathlib import Path
import re

path = Path('he/workspace/index.html')
text = path.read_text(encoding='utf-8')
original = text

# 1) Make the progress panel opener async.
text, n1 = re.subn(
    r'(?m)^(\s*)function\s+openStudentLessonProgressPanel\s*\(\s*\)\s*\{',
    r'\1async function openStudentLessonProgressPanel(){',
    text,
    count=1,
)

# If it is already async, that is fine.
if n1 == 0 and 'async function openStudentLessonProgressPanel()' not in text:
    raise SystemExit('openStudentLessonProgressPanel function not found')

# 2) Refresh progress from Supabase immediately before the panel builds pmap.
marker = 'const pmap=new Map((window.LESSON_SIDEBAR_PROGRESS_ROWS||[]).map(r=>[Number(r.unit_lesson_id),r]));'
if marker in text and 'Always refresh progress from DB before rendering.' not in text:
    replacement = '''// Always refresh progress from DB before rendering.\n  // This prevents a stale cached progress map from showing\n  // a lesson as "not started" after it was already opened.\n  try{\n    await loadLessonSidebarProgress();\n  }catch(err){\n    console.warn("LESSON PROGRESS REFRESH WARNING:",err);\n  }\n\n  ''' + marker
    text = text.replace(marker, replacement, 1)
elif marker not in text:
    # Fallback for formatted versions: inject before the first pmap declaration inside the function.
    func_pos = text.find('async function openStudentLessonProgressPanel()')
    pmap_pos = text.find('const pmap', func_pos)
    if func_pos == -1 or pmap_pos == -1:
        raise SystemExit('Progress pmap declaration not found')
    if 'Always refresh progress from DB before rendering.' not in text[func_pos:pmap_pos]:
        inject = '''  // Always refresh progress from DB before rendering.\n  // This prevents a stale cached progress map from showing\n  // a lesson as "not started" after it was already opened.\n  try{\n    await loadLessonSidebarProgress();\n  }catch(err){\n    console.warn("LESSON PROGRESS REFRESH WARNING:",err);\n  }\n\n'''
        text = text[:pmap_pos] + inject + text[pmap_pos:]

# 3) Bump visible build number only from 0.7.7 to 0.7.8.
if '0.7.7' not in text and '0.7.8' not in text:
    raise SystemExit('Build 0.7.7 marker not found')
text = text.replace('0.7.7', '0.7.8')

if text == original:
    raise SystemExit('No changes required')

path.write_text(text, encoding='utf-8')
print('Patched progress panel refresh and bumped build to 0.7.8')
