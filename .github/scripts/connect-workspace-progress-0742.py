from pathlib import Path
import re

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

MARK = 'IAKIDS_WORKSPACE_PROGRESS_ROUTE_0742'
if MARK not in s:
    block = r'''
<script id="IAKIDS_WORKSPACE_PROGRESS_ROUTE_0742">
(function(){
  function normalizeText(v){
    return String(v || '').replace(/\s+/g,' ').trim();
  }

  document.addEventListener('click', function(event){
    const item = event.target?.closest?.('.kid-actions .side-item');
    if(!item) return;

    const text = normalizeText(item.textContent);
    if(!text.includes('התקדמות')) return;

    /*
      Progress belongs to the learning workspace, not the games world.
      Capture the click before any legacy onclick/location.href handler.
    */
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    document.querySelectorAll('.kid-actions .side-item')
      .forEach(x => x.classList.remove('active'));
    item.classList.add('active');

    if(typeof window.openWorkspaceAchievements === 'function'){
      window.openWorkspaceAchievements();
      return;
    }

    console.warn('Workspace progress view is not ready yet');
  }, true);
})();
</script>
'''
    s = s.replace('</body>', block + '\n</body>', 1)

s = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.42', s, count=1)
s = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.42";', s, count=1)

p.write_text(s, encoding='utf-8')
print('workspace progress routed internally; build 0.7.42')
