from pathlib import Path
import re
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
MARK='IAKIDS_INTERNAL_MY_LESSONS_0747'
if MARK in s:
    print('already applied'); raise SystemExit(0)
block=r'''
<style id="IAKIDS_INTERNAL_MY_LESSONS_0747_STYLES">
  .iakids-my-lessons-view{position:absolute;inset:12px;z-index:246;overflow:auto;direction:rtl;border:1px solid rgba(67,137,218,.26);border-radius:24px;background:linear-gradient(180deg,#06162d 0%,#041125 100%);color:#eef6ff;box-shadow:0 24px 70px rgba(0,0,0,.38);font-family:"Heebo",Arial,sans-serif}
  .iakids-my-lessons-view[hidden]{display:none!important}
  .iml-shell{padding:22px;max-width:1380px;margin:0 auto}
  .iml-head{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:18px}
  .iml-title h1{margin:0;font-size:31px;font-weight:950}.iml-title p{margin:4px 0 0;color:#91a8c8;font-size:13px}
  .iml-close{height:38px;padding:0 14px;border-radius:11px;border:1px solid rgba(89,150,226,.24);background:#102b50;color:#e7f2ff;font-weight:900;cursor:pointer}
  .iml-empty{min-height:290px;border:1px solid rgba(80,137,207,.18);border-radius:20px;background:linear-gradient(180deg,rgba(17,43,79,.94),rgba(9,27,55,.95));display:grid;place-items:center;text-align:center;padding:34px}
  .iml-empty i{font-size:42px;color:#69d7ff;margin-bottom:12px}.iml-empty h2{margin:0 0 8px;font-size:22px}.iml-empty p{margin:0;color:#8fa6c5;max-width:560px;line-height:1.7}
</style>
<script id="IAKIDS_INTERNAL_MY_LESSONS_0747">
(function(){
  let view=null;
  function ensureView(){
    if(view?.isConnected) return view;
    const main=document.querySelector('.main');
    if(!main) return null;
    view=document.createElement('section');
    view.id='iakidsMyLessonsInternalView';
    view.className='iakids-my-lessons-view';
    view.hidden=true;
    view.innerHTML=`<div class="iml-shell"><div class="iml-head"><div class="iml-title"><h1>השיעורים שלי</h1><p>כל השיעורים שלך יוצגו כאן בתוך סביבת הלמידה</p></div><button type="button" class="iml-close"><i class="fa-solid fa-arrow-right"></i> חזרה</button></div><div class="iml-empty"><div><i class="fa-solid fa-book-open"></i><h2>עמוד השיעורים שלי</h2><p>הכפתור מחובר עכשיו למסך פנימי בתוך ה-workspace. את תוכן העמוד עצמו נבנה בשלב הבא.</p></div></div></div>`;
    main.appendChild(view);
    view.querySelector('.iml-close')?.addEventListener('click',closeView);
    return view;
  }
  function closeView(){
    const el=ensureView(); if(el) el.hidden=true;
    document.querySelectorAll('.kid-actions .side-item').forEach(x=>{if((x.textContent||'').includes('השיעורים שלי')) x.classList.remove('active')});
  }
  function openView(item){
    try{ window.closeWorkspaceAchievements?.(); }catch(_e){}
    try{ window.closeLearningProgress?.(); }catch(_e){}
    const dash=document.getElementById('iakidsLearningDashboard'); if(dash) dash.hidden=true;
    const el=ensureView(); if(!el) return; el.hidden=false;
    document.querySelectorAll('.kid-actions .side-item').forEach(x=>x.classList.remove('active'));
    item?.classList.add('active');
  }
  document.addEventListener('click',event=>{
    const item=event.target?.closest?.('.kid-actions .side-item, .side-item');
    if(!item) return;
    const text=(item.textContent||'').replace(/\s+/g,' ').trim();
    if(!text.includes('השיעורים שלי')) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    openView(item);
  },true);
  window.openMyLessonsInternal=openView;
  window.closeMyLessonsInternal=closeView;
})();
</script>
'''
if '</body>' not in s: raise SystemExit('body end not found')
s=s.replace('</body>',block+'\n</body>',1)
s=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.47',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.47";',s,count=1)
p.write_text(s,encoding='utf-8')
print('internal my lessons route applied')
