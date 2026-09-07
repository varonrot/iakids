from pathlib import Path
import re

index = Path('he/workspace/index.html')
text = index.read_text(encoding='utf-8')

# Keep the My Lessons panel inside the main content area and clear of the left sidebar.
text, n = re.subn(
    r'(\.iakids-my-lessons-overlay\{\s*\n\s*position:fixed;\s*\n\s*top:78px;\s*\n\s*)left:248px;',
    r'\1left:300px;',
    text,
    count=1,
)
if n != 1:
    raise RuntimeError(f'expected to move My Lessons overlay once, got {n}')

# Build stamp.
text = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.47', text, count=1)

index.write_text(text, encoding='utf-8')
print('Moved My Lessons overlay clear of sidebar; bumped to 0.7.47')
