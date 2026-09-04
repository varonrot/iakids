from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

css = r'''
/* =====================================================
   LESSON SIDEBAR TOP CONTROLS — exact equal width
   build 0.7.4
===================================================== */
.lesson-lessons-sidebar .lesson-sidebar-back-to-workspace,
.lesson-lessons-sidebar #lessonProgressOpenBtn,
.lesson-lessons-sidebar .lesson-sidebar-unit{
  width:auto !important;
  min-width:0 !important;
  max-width:none !important;
  align-self:stretch !important;
  margin-left:10px !important;
  margin-right:10px !important;
  box-sizing:border-box !important;
}
'''

marker = 'LESSON SIDEBAR TOP CONTROLS — exact equal width'
if marker not in s:
    idx = s.find('</style>')
    if idx == -1:
        raise SystemExit('style closing tag not found')
    s = s[:idx] + '\n' + css + '\n' + s[idx:]

for old in ['IAKIDS • build 0.7.0','IAKIDS • build 0.7.1','IAKIDS • build 0.7.2','IAKIDS • build 0.7.3']:
    s = s.replace(old, 'IAKIDS • build 0.7.4')

p.write_text(s, encoding='utf-8')
