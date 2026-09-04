from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

css = r'''
/* =====================================================
   LESSON SIDEBAR TOP CONTROLS — beat legacy specificity
   build 0.7.5
===================================================== */
body.lesson-theme-science .lesson-lessons-sidebar .lesson-sidebar-back-to-workspace,
body.lesson-theme-science .lesson-lessons-sidebar #lessonProgressOpenBtn,
body.lesson-theme-science .lesson-lessons-sidebar .lesson-sidebar-unit{
  width:calc(100% - 20px) !important;
  min-width:calc(100% - 20px) !important;
  max-width:calc(100% - 20px) !important;
  margin:8px 10px 0 !important;
  align-self:auto !important;
  transform:none !important;
  box-sizing:border-box !important;
}
'''

marker = 'LESSON SIDEBAR TOP CONTROLS — beat legacy specificity'
if marker not in s:
    idx = s.find('</style>')
    if idx == -1:
        raise SystemExit('style closing tag not found')
    s = s[:idx] + '\n' + css + '\n' + s[idx:]

for old in ['IAKIDS • build 0.7.0','IAKIDS • build 0.7.1','IAKIDS • build 0.7.2','IAKIDS • build 0.7.3','IAKIDS • build 0.7.4']:
    s = s.replace(old, 'IAKIDS • build 0.7.5')

p.write_text(s, encoding='utf-8')
