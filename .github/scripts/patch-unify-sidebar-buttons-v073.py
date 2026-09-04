from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

css = r'''
/* =====================================================
   LESSON SIDEBAR TOP CONTROLS — unified final sizing
   build 0.7.3
===================================================== */
.lesson-lessons-sidebar .lesson-sidebar-back-to-workspace,
.lesson-lessons-sidebar #lessonProgressOpenBtn,
.lesson-lessons-sidebar .lesson-sidebar-unit{
  width:calc(100% - 20px) !important;
  height:48px !important;
  min-height:48px !important;
  max-height:48px !important;
  margin:8px 10px 0 !important;
  padding:6px 10px !important;
  border-radius:12px !important;
  box-sizing:border-box !important;
  display:flex !important;
  align-items:center !important;
  justify-content:flex-start !important;
  gap:10px !important;
  direction:rtl !important;
  text-align:right !important;
  overflow:hidden !important;
}

.lesson-lessons-sidebar .lesson-sidebar-back-to-workspace,
.lesson-lessons-sidebar #lessonProgressOpenBtn{
  border:1px solid rgba(63,151,230,.62) !important;
  background:linear-gradient(180deg,rgba(18,61,111,.92),rgba(11,43,82,.94)) !important;
  color:#f5f9ff !important;
  box-shadow:inset 0 0 12px rgba(38,146,255,.08) !important;
}

.lesson-lessons-sidebar .lesson-sidebar-back-to-workspace:hover,
.lesson-lessons-sidebar #lessonProgressOpenBtn:hover{
  border-color:rgba(88,188,255,.9) !important;
  background:linear-gradient(180deg,rgba(24,78,139,.98),rgba(13,53,98,.98)) !important;
}

.lesson-lessons-sidebar .lesson-sidebar-unit{
  border:1px solid rgba(116,81,255,.82) !important;
  background:linear-gradient(135deg,rgba(71,43,155,.96),rgba(43,31,112,.96)) !important;
  color:#fff !important;
}

.lesson-lessons-sidebar .lesson-sidebar-back-to-workspace > span,
.lesson-lessons-sidebar .lesson-progress-card-icon,
.lesson-lessons-sidebar .lesson-sidebar-unit-image{
  width:34px !important;
  height:34px !important;
  min-width:34px !important;
  flex:0 0 34px !important;
  border-radius:9px !important;
  display:grid !important;
  place-items:center !important;
  margin:0 !important;
}

.lesson-lessons-sidebar .lesson-sidebar-back-to-workspace > span{
  background:rgba(30,102,167,.42) !important;
  border:1px solid rgba(92,184,255,.38) !important;
  color:#8bdcff !important;
  font-size:18px !important;
  line-height:1 !important;
}

.lesson-lessons-sidebar .lesson-progress-card-icon{
  background:rgba(30,102,167,.42) !important;
  border:1px solid rgba(92,184,255,.38) !important;
  color:#8bdcff !important;
}

.lesson-lessons-sidebar .lesson-sidebar-unit-image{
  overflow:hidden !important;
  background:rgba(6,20,45,.45) !important;
  border:1px solid rgba(167,146,255,.34) !important;
}

.lesson-lessons-sidebar .lesson-sidebar-unit-image img{
  width:100% !important;
  height:100% !important;
  object-fit:cover !important;
  border-radius:8px !important;
}

.lesson-lessons-sidebar .lesson-sidebar-back-to-workspace strong,
.lesson-lessons-sidebar .lesson-progress-card-text,
.lesson-lessons-sidebar #lessonSidebarUnitName{
  flex:1 1 auto !important;
  min-width:0 !important;
  margin:0 !important;
  padding:0 !important;
  text-align:right !important;
  font-size:12px !important;
  font-weight:800 !important;
  line-height:1.25 !important;
  color:inherit !important;
}

.lesson-lessons-sidebar .lesson-progress-card-style{
  justify-content:flex-start !important;
}
'''

marker = '/* =====================================================\n   LESSON SIDEBAR TOP CONTROLS — unified final sizing\n   build 0.7.3'
if marker not in s:
    idx = s.find('</style>')
    if idx == -1:
        raise SystemExit('style closing tag not found')
    s = s[:idx] + '\n' + css + '\n' + s[idx:]

for old in ['IAKIDS • build 0.7.0','IAKIDS • build 0.7.1','IAKIDS • build 0.7.2']:
    s = s.replace(old, 'IAKIDS • build 0.7.3')

p.write_text(s, encoding='utf-8')
