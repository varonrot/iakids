from pathlib import Path
import re

INDEX = Path('he/workspace/index.html')
SOURCE = Path('.github/scripts/add-workspace-achievements-view-0762.py')

index = INDEX.read_text(encoding='utf-8')
source = SOURCE.read_text(encoding='utf-8')

OLD_MARKER = 'IAKIDS_WORKSPACE_ACHIEVEMENTS_0762'
NEW_MARKER = 'IAKIDS_WORKSPACE_ACHIEVEMENTS_0739'

if OLD_MARKER not in index and NEW_MARKER not in index:
    m = re.search(r"injection\s*=\s*r'''(.*?)'''\n\s*if '</body>' not in index:", source, re.S)
    if not m:
        raise RuntimeError('Could not extract achievements injection from 0.7.62 patch')
    injection = m.group(1).replace(OLD_MARKER, NEW_MARKER)
    if '</body>' not in index:
        raise RuntimeError('body end not found')
    index = index.replace('</body>', injection + '\n</body>', 1)

# Bump only the visible workspace build. Do NOT touch homework loader/core versions.
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.39', index, count=1)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.39";', index, count=1)

INDEX.write_text(index, encoding='utf-8')
print('Workspace achievements restored safely; build 0.7.39')
