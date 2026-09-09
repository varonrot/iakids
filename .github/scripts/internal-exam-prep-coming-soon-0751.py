from pathlib import Path
import re
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
MARK='IAKIDS_EXAM_PREP_COMING_SOON_0751'
if MARK in s:
    print('already applied'); raise SystemExit(0)
block=r'''
<style id="IAKIDS_EXAM_PREP_COMING_SOON_0751_STYLES">
  .iakids-exam-soon{position:absolute;inset:12px;z-index:248;overflow:auto;direction:rtl;border:1px solid rgba(67,137,218,.26);border-radius:24px;background:linear-gradient(180deg,#06162d 0%,#041125 100%);color:#eef6ff;box-shadow:0 24px 70px rgba(0,0,0,.38);font-family:"Heebo",Arial,sans-serif}
  .iakids-exam-soon[hidden]{display:none!important}.ies-shell{padding:22px;max-width:1380px;margin:0 auto}.ies-head{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:18px}.ies-title h1{margin:0;font-size:31px;font-weight:950}.ies-title p{margin:4px 0 0;color:#91a8c8;font-size:13px}.ies-close{height:38px;padding:0 14px;border-radius:11px;border:1px solid rgba(89,150,226,.24);background:#102b50;color:#e7f2ff;font-weight:900;cursor:pointer}.ies-card{min-height:360px;border:1px solid rgba(80,137,207,.18);border-radius:22px;background:radial-gradient(circle at 50% 0%,rgba(76,92,255,.18),transparent 34%),linear-gradient(180deg,rgba(17,43,79,.94),rgba(9,27,55,.95));display:grid;place-items:center;text-align:center;padding:38px}.ies-icon{width:86px;height:86px;border-radius:24px;display:grid;place-items:center;margin:0 auto 18px;background:linear-gradient(135deg,#5d54ff,#1eb9ff);box-shadow:0 14px 34px rgba(46,117,255,.28);font-size:34px}.ies-card h2{margin:0 0 8px;font-size:26px}.ies-card p{margin:0 auto;color:#91a8c8;max-width:560px;line-height:1.7;font-size:14px}.ies-badge{display:inline-flex;align-items:center;gap:7px;margin-top:18px;padding:8px 13px;border-radius:999px;background:rgba(31,199,133,.12);border:1px solid rgba(45,220,153,.28);color:#8fffd0;font-weight:900;font-size:12px}
</style>
<script id="IAKIDS_EXAM_PREP_COMING_SOON_0751">
(function(){
  if(window.__IAKIDS_EXAM_PREP_SOON_0751)return;window.__IAKIDS_EXAM_PREP_SOON_0751=true;
  let view=null;
  function ensureView(){if(view?.isConnected)return view;const main=document.querySelector('.main');if(!main)return null;view=document.createElement('section');view.id='iakidsExamPrepComingSoon';view.className='iakids-exam-soon';view.hidden=true;view.innerHTML=`<div class="ies-shell"><div class="ies-head"><div class="ies-title"><h1>הכנה למבחן</h1><p>סביבת הכנה חכמה למבחנים</p></div><button type="button" class="ies-close"><i class="fa-solid fa-arrow-right"></i> חזרה</button></div><div class="ies-card"><div><div class="ies-icon"><i class="fa-solid fa-bullseye"></i></div><h2>עולה בקרוב</h2><p>אנחנו בונים עבורך סביבת הכנה חכמה למבחנים עם תרגול מותאם אישית, חיזוק נושאים וסימולציות.</p><span class="ies-badge"><i class="fa-solid fa-sparkles"></i> בקרוב ב-IAKIDS</span></div></div></div>`;document.querySelector('.main')?.appendChild(view);view.querySelector('.ies-close')?.addEventListener('click',closeView);return view}
  function closeView(){const el=ensureView();if(el)el.hidden=true;document.querySelectorAll('.side-item').forEach(x=>{if((x.textContent||'').includes('הכנה למבחן'))x.classList.remove('active')})}
  function openView(item){try{window.closeWorkspaceAchievements?.()}catch(_e){}try{window.closeLearningProgress?.()}catch(_e){}try{window.closeMyLessonsInternal?.()}catch(_e){}try{window.closeMyFilesInternal?.()}catch(_e){}const dash=document.getElementById('iakidsLearningDashboard');if(dash)dash.hidden=true;const el=ensureView();if(!el)return;el.hidden=false;document.querySelectorAll('.side-item').forEach(x=>x.classList.remove('active'));item?.classList.add('active')}
  document.addEventListener('click',event=>{const item=event.target?.closest?.('a,button,.side-item');if(!item)return;const text=(item.textContent||'').replace(/\s+/g,' ').trim();if(!text.includes('הכנה למבחן'))return;event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();openView(item)},true);
  window.openExamPrepComingSoon=openView;window.closeExamPrepComingSoon=closeView;
})();
</script>
'''
if '</body>' not in s: raise SystemExit('body end not found')
s=s.replace('</body>',block+'\n</body>',1)
s=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.51',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.51";',s,count=1)
p.write_text(s,encoding='utf-8')
print('exam prep coming soon applied')
