from pathlib import Path
import re

p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
MARK='IAKIDS_HOME_RESET_FROM_CUSTOM_SUBJECT_0752'
if MARK in s:
    print('already applied')
    raise SystemExit(0)

block=r'''
<script id="IAKIDS_HOME_RESET_FROM_CUSTOM_SUBJECT_0752">
(function(){
  if(window.__IAKIDS_HOME_RESET_FROM_CUSTOM_SUBJECT_0752) return;
  window.__IAKIDS_HOME_RESET_FROM_CUSTOM_SUBJECT_0752 = true;

  function hideInternalViews(){
    const ids=[
      'iakidsMyLessonsInternalView',
      'iakidsMyFilesInternalView',
      'iakidsExamPrepComingSoon',
      'iakidsLearningProgressView',
      'iakidsLearningDashboard'
    ];
    ids.forEach(id=>{
      const el=document.getElementById(id);
      if(el && id!=='iakidsLearningDashboard') el.hidden=true;
    });
  }

  function resetCustomSubjectState(){
    try{
      if(typeof window.closeCustomSubject==='function'){
        window.closeCustomSubject();
        return true;
      }
    }catch(e){ console.warn('closeCustomSubject failed',e); }

    const customView=document.getElementById('customSubjectView');
    if(customView) customView.style.display='none';

    const rightbar=document.querySelector('.home-rightbar');
    if(rightbar) rightbar.style.display='';

    document.body.classList.remove('custom-subject-mode');

    try{ if(typeof window.showDashboard==='function') window.showDashboard(); }catch(_e){}
    return false;
  }

  document.addEventListener('click',function(event){
    const item=event.target?.closest?.('.side-item,button,a');
    if(!item) return;
    const text=(item.textContent||'').replace(/\s+/g,' ').trim();
    if(text!=='דף הבית' && !text.includes('דף הבית')) return;

    const inCustom=document.body.classList.contains('custom-subject-mode') ||
      document.getElementById('customSubjectView')?.style.display==='block';
    if(!inCustom) return;

    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    hideInternalViews();
    resetCustomSubjectState();

    document.querySelectorAll('.side-item').forEach(x=>x.classList.remove('active'));
    item.classList.add('active');
  },true);
})();
</script>
'''

if '</body>' not in s:
    raise SystemExit('body end not found')

s=s.replace('</body>',block+'\n</body>',1)
s=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.52',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.52";',s,count=1)
p.write_text(s,encoding='utf-8')
print('home reset from custom subject applied')
