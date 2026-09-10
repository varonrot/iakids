from pathlib import Path
import re

workspace = Path('he/workspace/index.html')
tasks = Path('he/workspace/tasks-internal.js')

text = workspace.read_text(encoding='utf-8')
original = text

# Cache-bust the internal tasks bundle.
text = text.replace('/he/workspace/tasks-internal.js?v=0765', '/he/workspace/tasks-internal.js?v=0767')
text = text.replace('/he/workspace/tasks-internal.js?v=0766', '/he/workspace/tasks-internal.js?v=0767')

# Bump any visible workspace build label currently on an older 0.7.x build.
text = re.sub(r'(IAKIDS\s*[•·-]?\s*build\s*)0\.7\.\d+', r'\g<1>0.7.67', text, flags=re.I)
text = re.sub(r'(build\s*)0\.7\.62', r'\g<1>0.7.67', text, flags=re.I)

if text == original:
    raise SystemExit('No workspace version/cache-bust changes were found to apply')
workspace.write_text(text, encoding='utf-8')

js = tasks.read_text(encoding='utf-8')
js_original = js
js = js.replace('/* IAKIDS internal tasks view 0.7.66 */', '/* IAKIDS internal tasks view 0.7.67 */')
js = js.replace('window.__IAKIDS_INTERNAL_TASKS_0766', 'window.__IAKIDS_INTERNAL_TASKS_0767')
js = js.replace('0.7.66', '0.7.67')

if js != js_original:
    tasks.write_text(js, encoding='utf-8')
