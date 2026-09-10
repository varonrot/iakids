from pathlib import Path

p = Path('he/workspace/index.html')
text = p.read_text(encoding='utf-8')

old = '''    <!-- משימות -->
    <button
      class="side-item"
      onclick="window.location.href='/he/tasks/'"
    >
'''
new = '''    <!-- משימות -->
    <button
      class="side-item"
      id="tasksSidebarBtn"
      type="button"
    >
'''

if old in text:
    text = text.replace(old, new, 1)
elif 'id="tasksSidebarBtn"' not in text:
    raise SystemExit('Tasks sidebar block not found')

script = '<script src="/he/workspace/tasks-internal.js?v=0765"></script>'
if script not in text:
    marker = '</body>'
    if marker not in text:
        raise SystemExit('Closing body not found')
    text = text.replace(marker, script + '\n' + marker, 1)

p.write_text(text, encoding='utf-8')
print('Internal tasks view patched successfully')
