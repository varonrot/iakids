from pathlib import Path
import re

root = Path('.')
backend_path = root / 'backend-ai-tutor-he/main.py'
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'

backend = backend_path.read_text(encoding='utf-8')
loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

old = '    image_url: Optional[str] = None\n'
new = '    image_url: str = ""\n'
if old not in backend:
    raise SystemExit('HomeworkCoachRequest image_url field not found')
backend = backend.replace(old, new, 1)

loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.98";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0798', loader, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0798', index)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.98', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.98";', index, count=1)

backend_path.write_text(backend, encoding='utf-8')
loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
print('Fixed Homework V2 request model and bumped to 0.7.98')
