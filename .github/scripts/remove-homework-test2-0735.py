from pathlib import Path
import re

path = Path('he/workspace/index.html')
text = path.read_text(encoding='utf-8')

block = '''    <!-- IAKIDS_HOMEWORK_TEST2_0733 -->\n    <button\n      class="side-item"\n      id="homeworkSidebarBtn2"\n      style="border:1px dashed rgba(89,199,255,.55);background:rgba(16,55,103,.55);"\n      onclick="event.preventDefault(); event.stopPropagation(); if (typeof window.showHomeworkLessonWorkspace === 'function') { window.showHomeworkLessonWorkspace(); } else { alert('בדיקה: מנגנון שיעורי הבית לא נטען'); }"\n    >\n      <i class="fa-solid fa-flask"></i>\n      <div class="side-text">\n        <span class="side-title">עזרה בשיעורי בית 2</span>\n      </div>\n    </button>\n\n\n'''

if block not in text:
    raise RuntimeError('Diagnostic homework button block not found')

text = text.replace(block, '', 1)
text = re.sub(r'IAKIDS • build 0\.7\.\d+', 'IAKIDS • build 0.7.35', text, count=1)
text = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.35";', text, count=1)

path.write_text(text, encoding='utf-8')
print('Removed homework diagnostic button 2; build 0.7.35')
