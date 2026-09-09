from pathlib import Path
import re

p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
MARK='IAKIDS_OVERALL_PROGRESS_FIX_0756'
if MARK in s:
    print('already applied')
    raise SystemExit(0)

block=r'''
<script id="IAKIDS_OVERALL_PROGRESS_FIX_0756">
(function(){
  if(window.__IAKIDS_OVERALL_PROGRESS_FIX_0756)return;
  window.__IAKIDS_OVERALL_PROGRESS_FIX_0756=true;

  function getClient(){
    try{if(typeof sb!=='undefined'&&sb?.from)return sb}catch(_e){}
    return window.sb?.from?window.sb:(window.supabaseClient?.from?window.supabaseClient:null);
  }
  function getKid(){
    try{if(typeof CURRENT_KID!=='undefined'&&CURRENT_KID?.id)return CURRENT_KID}catch(_e){}
    return window.CURRENT_KID||window.SELECTED_KID||window.currentKid||window.selectedKid||null;
  }
  function clamp(v){return Math.max(0,Math.min(100,Number(v)||0))}
  function scoreRow(r){
    const raw=clamp(r?.progress_percent);
    const st=String(r?.status||'').toLowerCase();
    if(st==='completed') return 100;
    if(st==='partial') return Math.max(raw,50);
    if(st==='in_progress'||st==='active') return Math.max(raw,25);
    if(st==='ready'||st==='pending'||st==='not_started') return raw;
    return raw;
  }

  async function loadOverall(){
    const c=getClient(),k=getKid();
    if(!c||!k?.id)return;
    try{
      const [unitRes,lessonRes,subjectRes]=await Promise.all([
        c.from('kid_unit_lesson_progress')
          .select('id,status,progress_percent,unit_lesson_id,updated_at')
          .eq('kid_id',k.id),
        c.from('kid_lesson_progress')
          .select('id,status,progress_percent,lesson_id,updated_at')
          .eq('kid_id',k.id),
        c.from('kid_custom_subjects')
          .select('id,status')
          .eq('kid_id',k.id)
          .eq('status','active')
      ]);

      const units=unitRes.error?[]:(unitRes.data||[]);
      const lessons=lessonRes.error?[]:(lessonRes.data||[]);
      const activeSubjectIds=(subjectRes.error?[]:(subjectRes.data||[])).map(x=>x.id).filter(Boolean);

      let custom=[];
      if(activeSubjectIds.length){
        const cr=await c.from('kid_custom_lessons')
          .select('id,status,custom_subject_id')
          .eq('kid_id',k.id)
          .in('custom_subject_id',activeSubjectIds)
          .neq('status','archived');
        if(!cr.error) custom=cr.data||[];
      }

      // Use the granular unit-lesson table whenever it exists. It is the real lesson engine
      // progress and avoids double-counting the parent lesson in kid_lesson_progress.
      const standard=units.length?units:lessons;
      const standardScores=standard.map(scoreRow);
      const customScores=custom.map(r=>{
        const st=String(r.status||'').toLowerCase();
        if(st==='completed')return 100;
        if(st==='active')return 50;
        if(st==='ready')return 25;
        return 0;
      });
      const allScores=[...standardScores,...customScores];
      const overall=allScores.length?Math.round(allScores.reduce((a,b)=>a+b,0)/allScores.length):0;

      const completed=standard.filter(r=>String(r.status||'').toLowerCase()==='completed').length+
        custom.filter(r=>String(r.status||'').toLowerCase()==='completed').length;
      const inProgress=standard.filter(r=>['in_progress','partial','active'].includes(String(r.status||'').toLowerCase())).length+
        custom.filter(r=>['in_progress','partial','active','ready'].includes(String(r.status||'').toLowerCase())).length;

      document.querySelectorAll('.kingdom-status-overall').forEach(card=>{
        const ring=card.querySelector('.kingdom-status-ring-inner strong');
        const accent=card.querySelector('.kingdom-status-accent');
        const ringWrap=card.querySelector('.kingdom-status-ring');
        const meta=[...card.querySelectorAll('.kingdom-status-meta span')];
        if(ring)ring.textContent=`${overall}%`;
        if(accent)accent.textContent=`${overall}%`;
        if(ringWrap)ringWrap.style.setProperty('--progress',String(overall));
        if(meta[0])meta[0].innerHTML=`<b>${completed}</b> שיעורים הושלמו`;
        if(meta[1])meta[1].innerHTML=`<b>${inProgress}</b> בתהליך`;
      });

      window.IAKIDS_OVERALL_PROGRESS={overall,completed,inProgress,standardCount:standard.length,customCount:custom.length,source:units.length?'kid_unit_lesson_progress':'kid_lesson_progress'};
    }catch(e){console.warn('OVERALL PROGRESS FIX',e)}
  }

  // Run after the legacy 0.7.55 loader so this becomes the final rendered source of truth.
  window.refreshOverallLearningProgress=loadOverall;
  document.addEventListener('DOMContentLoaded',()=>setTimeout(loadOverall,1800),{once:true});
  if(document.readyState!=='loading')setTimeout(loadOverall,1800);
  document.addEventListener('click',e=>{
    const t=(e.target?.textContent||'').trim();
    if(t.includes('דף הבית'))setTimeout(loadOverall,900);
  },false);
  setInterval(()=>{if(document.visibilityState==='visible')setTimeout(loadOverall,900)},60000);
})();
</script>
'''

if '</body>' not in s: raise SystemExit('body end not found')
s=s.replace('</body>',block+'\n</body>',1)
s=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.56',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.56";',s,count=1)
p.write_text(s,encoding='utf-8')
print('overall progress fixed; build 0.7.56')
