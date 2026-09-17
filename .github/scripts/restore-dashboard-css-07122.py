from pathlib import Path
import re

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

replacement = '''<style id="IAKIDS_DASHBOARD_1280_07122">
  /* Compact desktop/tablet layout — restored to the pre-0.7.116 behaviour. */
  @media (min-width:761px) and (max-width:1450px),
         (min-width:761px) and (max-height:800px){
    body:not(.lesson-theme-science):not(.science-hierarchy-mode) .app{
      grid-template-columns:215px minmax(0,1fr)!important;
      column-gap:10px!important;
    }

    body:not(.lesson-theme-science):not(.science-hierarchy-mode) .topbar{
      grid-column:1 / 3!important;
    }

    body:not(.lesson-theme-science):not(.science-hierarchy-mode) .sidebar{
      grid-column:1!important;
      width:215px!important;
      min-height:0!important;
      overflow-x:hidden!important;
      overflow-y:auto!important;
      scrollbar-gutter:stable;
    }

    body:not(.lesson-theme-science):not(.science-hierarchy-mode) .main{
      grid-column:2!important;
      min-width:0!important;
      min-height:0!important;
    }

    .rightbar.home-rightbar{
      display:none!important;
      grid-column:auto!important;
    }

    #dashboardView.dashboard-view{
      min-height:0!important;
      overflow-x:hidden!important;
      overflow-y:auto!important;
      scrollbar-gutter:stable;
    }

    .floating-tutor-robot{
      display:none!important;
    }
  }
</style>'''

pattern = re.compile(r'<style id="IAKIDS_DASHBOARD_1280_[^"]+">.*?</style>(?=\n</body></html>)', re.S)
if not pattern.search(s):
    raise SystemExit('dashboard override block not found')
s = pattern.sub(replacement, s, count=1)

s = s.replace('IAKIDS • build 0.7.121', 'IAKIDS • build 0.7.122')
s = s.replace('window.IAKIDS_BUILD_VERSION = "0.7.121";', 'window.IAKIDS_BUILD_VERSION = "0.7.122";')
s = s.replace('/he/workspace/openai-clean-chat.js?v=07121', '/he/workspace/openai-clean-chat.js?v=07122')

p.write_text(s, encoding='utf-8')

q = Path('he/workspace/openai-clean-chat.js')
if q.exists():
    t = q.read_text(encoding='utf-8').replace("||'0.7.121'", "||'0.7.122'")
    q.write_text(t, encoding='utf-8')
