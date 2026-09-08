from pathlib import Path
import re

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

MARK = 'IAKIDS_PERSONAL_CARD_WIDTHS_0740'
if MARK not in s:
    block = r'''
<style id="IAKIDS_PERSONAL_CARD_WIDTHS_0740">
/* Personal-system hierarchy cards: same visual density as default subjects (e.g. geography). */
body.custom-subject-mode #customSubjectTree .science-tree-row{
  display:grid !important;
  grid-template-columns:repeat(auto-fit,minmax(180px,220px)) !important;
  justify-content:center !important;
  align-items:stretch !important;
  gap:12px !important;
  width:100% !important;
}

body.custom-subject-mode #customSubjectTree .science-tree-card{
  width:220px !important;
  max-width:220px !important;
  min-width:0 !important;
  grid-column:auto !important;
  justify-self:center !important;
}

@media (max-width:1200px){
  body.custom-subject-mode #customSubjectTree .science-tree-row{
    grid-template-columns:repeat(auto-fit,minmax(170px,205px)) !important;
  }
  body.custom-subject-mode #customSubjectTree .science-tree-card{
    width:205px !important;
    max-width:205px !important;
  }
}

@media (max-width:760px){
  body.custom-subject-mode #customSubjectTree .science-tree-row{
    grid-template-columns:repeat(2,minmax(0,1fr)) !important;
    gap:10px !important;
  }
  body.custom-subject-mode #customSubjectTree .science-tree-card{
    width:100% !important;
    max-width:none !important;
  }
}
</style>
'''
    s = s.replace('</body>', block + '\n</body>', 1)

s = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.40', s, count=1)
s = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.40";', s, count=1)

p.write_text(s, encoding='utf-8')
print('personal system card widths tightened; build 0.7.40')
