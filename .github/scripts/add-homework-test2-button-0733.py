from pathlib import Path
import re

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')
marker = 'IAKIDS_HOMEWORK_TEST2_0733'
if marker not in s:
    anchor = '''    </button>\n\n\n    <!-- הכנה למבחן -->'''
    block = '''    </button>\n\n\n    <!-- IAKIDS_HOMEWORK_TEST2_0733 -->\n    <button\n      class="side-item"\n      id="homeworkSidebarBtn2"\n      style="border:1px dashed rgba(89,199,255,.55);background:rgba(16,55,103,.55);"\n      onclick="event.preventDefault(); event.stopPropagation(); if (typeof window.showHomeworkLessonWorkspace === 'function') { window.showHomeworkLessonWorkspace(); } else { alert('בדיקה: מנגנון שיעורי הבית לא נטען'); }"\n    >\n      <i class="fa-solid fa-flask"></i>\n      <div class="side-text">\n        <span class="side-title">עזרה בשיעורי בית 2</span>\n      </div>\n    </button>\n\n\n    <!-- הכנה למבחן -->'''
    if anchor not in s:
        raise RuntimeError('homework sidebar anchor not found')
    s = s.replace(anchor, block, 1)

s = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.33', s, count=1)
s = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.33";', s, count=1)
p.write_text(s, encoding='utf-8')
print('Added diagnostic homework button 2; build 0.7.33')
