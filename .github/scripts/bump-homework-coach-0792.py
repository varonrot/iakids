from pathlib import Path
import re

root = Path('.')
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'

loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.92";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0792', loader, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0792', index)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.92', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.92";', index, count=1)

loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
print('Bumped homework coach frontend/cache to 0.7.92')
