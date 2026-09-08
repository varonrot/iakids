from pathlib import Path
import re

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

MARK = 'IAKIDS_PERSONAL_SYSTEM_CARD_WIDTHS_0737'
if MARK not in s:
    block = r'''
<style id="IAKIDS_PERSONAL_SYSTEM_CARD_WIDTHS_0737">
  body.custom-subject-mode #customSubjectTree .science-tree-row{
    grid-template-columns:repeat(4,minmax(150px,1fr)) !important;
    gap:14px !important;
  }

  body.custom-subject-mode #customSubjectTree .science-tree-card{
    width:100% !important;
    min-width:0 !important;
  }

  @media (max-width:1450px){
    body.custom-subject-mode #customSubjectTree .science-tree-row{
      grid-template-columns:repeat(3,minmax(150px,1fr)) !important;
    }
  }

  @media (max-width:1000px){
    body.custom-subject-mode #customSubjectTree .science-tree-row{
      grid-template-columns:repeat(2,minmax(150px,1fr)) !important;
    }
  }

  @media (max-width:650px){
    body.custom-subject-mode #customSubjectTree .science-tree-row{
      grid-template-columns:1fr !important;
    }
  }
</style>
'''
    s = s.replace('</body>', block + '\n</body>', 1)

s = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.37', s, count=1)
s = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.37";', s, count=1)

p.write_text(s, encoding='utf-8')
print('personal system card widths aligned to default hierarchy; build 0.7.37')
