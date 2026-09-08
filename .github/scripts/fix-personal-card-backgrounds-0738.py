from pathlib import Path
import re

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

MARK = 'IAKIDS_PERSONAL_CARD_BACKGROUNDS_0738'
if MARK not in s:
    css = r'''
<style id="IAKIDS_PERSONAL_CARD_BACKGROUNDS_0738">
/* Personal-system cards: use card images as full backgrounds like default subject cards */
body.custom-subject-mode .science-tree-card{
  position:relative !important;
  overflow:hidden !important;
  isolation:isolate !important;
  background:#08172a !important;
}

body.custom-subject-mode .science-tree-card .science-tree-card-icon{
  position:absolute !important;
  inset:0 !important;
  width:100% !important;
  height:100% !important;
  margin:0 !important;
  border-radius:inherit !important;
  overflow:hidden !important;
  z-index:0 !important;
  pointer-events:none !important;
}

body.custom-subject-mode .science-tree-card .science-tree-icon-img{
  width:100% !important;
  height:100% !important;
  max-width:none !important;
  max-height:none !important;
  object-fit:cover !important;
  object-position:center !important;
  display:block !important;
  opacity:.58 !important;
  transform:scale(1.02);
}

body.custom-subject-mode .science-tree-card::before{
  content:"";
  position:absolute;
  inset:0;
  z-index:1;
  pointer-events:none;
  background:
    linear-gradient(180deg,rgba(2,10,23,.08) 0%,rgba(2,10,23,.34) 40%,rgba(2,10,23,.92) 100%),
    linear-gradient(90deg,rgba(4,17,35,.16),rgba(4,17,35,.04));
}

body.custom-subject-mode .science-tree-card > strong,
body.custom-subject-mode .science-tree-card > small,
body.custom-subject-mode .science-tree-card > .science-tree-progress{
  position:relative !important;
  z-index:2 !important;
}

body.custom-subject-mode .science-tree-card > strong{
  text-shadow:0 2px 8px rgba(0,0,0,.85) !important;
}

body.custom-subject-mode .science-tree-card > small{
  color:rgba(232,241,255,.76) !important;
  text-shadow:0 2px 7px rgba(0,0,0,.8) !important;
}

body.custom-subject-mode .science-tree-card > .science-tree-progress{
  margin-top:auto !important;
}

body.custom-subject-mode .science-tree-card.selected{
  box-shadow:
    inset 0 0 0 1px rgba(73,230,121,.35),
    0 0 22px rgba(54,218,116,.10) !important;
}
</style>
'''
    s = s.replace('</body>', css + '\n</body>', 1)

s = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.38', s, count=1)
s = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.38";', s, count=1)
p.write_text(s, encoding='utf-8')
print('personal card images converted to full-card backgrounds; build 0.7.38')
