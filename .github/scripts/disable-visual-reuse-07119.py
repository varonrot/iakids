from pathlib import Path
import re

root = Path('.')
backend_path = root / 'backend-ai-tutor-he/main.py'
index_path = root / 'he/workspace/index.html'

backend = backend_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

old = 'VISUAL_REUSE = os.getenv("VISUAL_REUSE", "1") == "1"                # dynamic image count: segments without a new idea reuse the previous image'
new = 'VISUAL_REUSE = False  # disabled: generate a distinct image for every visual segment'
if old not in backend:
    # allow reruns or minor spacing changes
    backend, n = re.subn(r'^VISUAL_REUSE\s*=.*$', new, backend, count=1, flags=re.MULTILINE)
    if n != 1:
        raise SystemExit('VISUAL_REUSE setting not found')
else:
    backend = backend.replace(old, new, 1)

# Bump visible build only; backend deploy is triggered by main.py change.
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.119', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.119";', index, count=1)

backend_path.write_text(backend, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
print('Disabled visual reuse; every visual entry will generate its own image. Build 0.7.119')
