from pathlib import Path

TASKS = Path('he/tasks/index.html')
INTERNAL = Path('he/workspace/tasks-internal.js')
WORKSPACE = Path('he/workspace/index.html')

GOOD_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4bmZ6dWdsZnd5dGl5YWd1d2pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyMjk0NjUsImV4cCI6MjA4NDgwNTQ2NX0.IcmVvbboKLkJLkE31_udEtvhPl66-kmZAvmPCT_lk5o'
BAD_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJieG5menVnbGZ3eXRpeWFndXdqaiIsInJlZiI6ImJ4bmZ6dWdsZnd5dGl5YWd1d2pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyMjk0NjUsImV4cCI6MjA4NDgwNTQ2NX0.IcmVvbboKLkJLkE31_udEtvhPl66-kmZAvmPCT_lk5o'

text = TASKS.read_text(encoding='utf-8')
if BAD_KEY not in text:
    raise SystemExit('Expected bad Supabase key not found in he/tasks/index.html')
text = text.replace(BAD_KEY, GOOD_KEY)
TASKS.write_text(text, encoding='utf-8')

text = INTERNAL.read_text(encoding='utf-8')
text = text.replace('internal tasks view 0.7.67', 'internal tasks view 0.7.68')
text = text.replace('__IAKIDS_INTERNAL_TASKS_0767', '__IAKIDS_INTERNAL_TASKS_0768')
text = text.replace('/he/tasks/?embed=1', '/he/tasks/?embed=1&v=0768')
text = text.replace('`/he/tasks/?embed=1&kid_id=', '`/he/tasks/?embed=1&v=0768&kid_id=')
INTERNAL.write_text(text, encoding='utf-8')

text = WORKSPACE.read_text(encoding='utf-8')
text = text.replace('tasks-internal.js?v=0767', 'tasks-internal.js?v=0768')
text = text.replace('build 0.7.67', 'build 0.7.68')
text = text.replace('build 0.7.62', 'build 0.7.68')
WORKSPACE.write_text(text, encoding='utf-8')
