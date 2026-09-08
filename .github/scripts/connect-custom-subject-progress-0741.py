from pathlib import Path
import re

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

MARK = 'IAKIDS_CUSTOM_SUBJECT_PROGRESS_0741'
if MARK not in s:
    block = r'''
<style id="IAKIDS_CUSTOM_SUBJECT_PROGRESS_STYLES_0741">
  body.custom-subject-mode #customSubjectTree .science-tree-progress > span[data-real-progress="1"]{
    transition:width .25s ease, background .2s ease !important;
  }
  body.custom-subject-mode .science-side-donut.iakids-custom-live-progress{
    background:conic-gradient(#42df7f var(--iakids-progress-angle,0deg),rgba(70,104,141,.18) 0deg) !important;
    border-radius:50%;
    padding:6px;
  }
</style>
<script id="IAKIDS_CUSTOM_SUBJECT_PROGRESS_0741">
(function(){
  if(window.__IAKIDS_CUSTOM_SUBJECT_PROGRESS_0741) return;
  window.__IAKIDS_CUSTOM_SUBJECT_PROGRESS_0741 = true;

  let activeSubjectId = null;
  let cache = {units:[],lessons:[]};

  function getClient(){
    try{ if(typeof sb !== 'undefined' && sb?.from) return sb; }catch(_e){}
    return window.sb?.from ? window.sb : (window.supabaseClient?.from ? window.supabaseClient : null);
  }
  function getKid(){
    try{ if(typeof CURRENT_KID !== 'undefined' && CURRENT_KID?.id) return CURRENT_KID; }catch(_e){}
    return window.CURRENT_KID || window.SELECTED_KID || window.currentKid || null;
  }
  function clamp(v){return Math.max(0,Math.min(100,Math.round(Number(v)||0)));}
  function completedStatus(s){return String(s||'').toLowerCase()==='completed';}
  function currentStatus(s){return ['active','in_progress'].includes(String(s||'').toLowerCase());}
  function progressOf(rows){
    const usable=(rows||[]).filter(x=>String(x.status||'').toLowerCase()!=='archived');
    if(!usable.length) return 0;
    const done=usable.filter(x=>completedStatus(x.status)).length;
    return clamp(done/usable.length*100);
  }
  function setText(id,value){const el=document.getElementById(id); if(el) el.textContent=String(value);}
  function setBar(card,percent,status){
    if(!card) return;
    const span=card.querySelector('.science-tree-progress > span');
    if(span){
      span.dataset.realProgress='1';
      span.style.width=clamp(percent)+'%';
      span.style.background=completedStatus(status)||percent>=100
        ? 'linear-gradient(90deg,#35d66f,#65ee8e)'
        : (currentStatus(status)||percent>0
          ? 'linear-gradient(90deg,#239cff,#43d7f2)'
          : 'rgba(87,116,151,.26)');
    }
  }
  function byName(rows,key,value){return (rows||[]).filter(x=>String(x[key]||'').trim()===String(value||'').trim());}

  function paintTree(){
    const units=cache.units||[];
    const lessons=(cache.lessons||[]).filter(l=>String(l.status||'').toLowerCase()!=='archived');

    document.querySelectorAll('#customSubjectTree .custom-topic-card').forEach(card=>{
      const topic=card.dataset.topicName || card.querySelector('strong')?.textContent?.trim();
      const topicUnits=byName(units,'topic_name',topic);
      const ids=new Set(topicUnits.map(u=>String(u.id)));
      const rows=lessons.filter(l=>ids.has(String(l.custom_unit_id)));
      setBar(card,progressOf(rows), rows.length && rows.every(x=>completedStatus(x.status)) ? 'completed' : (rows.some(x=>currentStatus(x.status))?'active':'pending'));
    });

    document.querySelectorAll('#customSubjectTree .custom-unit-card').forEach(card=>{
      const unitId=card.dataset.unitId;
      const name=card.querySelector('strong')?.textContent?.trim();
      const unit=units.find(u=>String(u.id)===String(unitId)) || units.find(u=>String(u.unit_name).trim()===String(name||'').trim());
      if(!unit) return;
      const rows=lessons.filter(l=>String(l.custom_unit_id)===String(unit.id));
      setBar(card,progressOf(rows), rows.length && rows.every(x=>completedStatus(x.status)) ? 'completed' : (rows.some(x=>currentStatus(x.status))?'active':'pending'));
    });

    document.querySelectorAll('#customSubjectTree .custom-lesson-card').forEach(card=>{
      const id=card.dataset.lessonId;
      const name=card.querySelector('strong')?.textContent?.trim();
      const lesson=lessons.find(l=>String(l.id)===String(id)) || lessons.find(l=>String(l.lesson_name).trim()===String(name||'').trim());
      if(!lesson) return;
      setBar(card,completedStatus(lesson.status)?100:0,lesson.status);
    });
  }

  function paintSide(){
    const lessons=(cache.lessons||[]).filter(l=>String(l.status||'').toLowerCase()!=='archived');
    const total=lessons.length;
    const completed=lessons.filter(l=>completedStatus(l.status)).length;
    const remaining=Math.max(0,total-completed);
    const percent=total?clamp(completed/total*100):0;

    setText('customSubjectProgressPercent',percent+'%');
    setText('customSubjectLessonsTotal',total);
    setText('customSubjectLessonsCompleted',completed);
    setText('customSubjectLessonsRemaining',remaining);

    const donut=document.getElementById('customSubjectProgressPercent')?.closest('.science-side-donut');
    if(donut){
      donut.classList.add('iakids-custom-live-progress');
      donut.style.setProperty('--iakids-progress-angle',(percent*3.6)+'deg');
    }

    const next=lessons.find(l=>currentStatus(l.status)) || lessons.find(l=>!completedStatus(l.status));
    const nextEl=document.getElementById('customSubjectNextLesson');
    if(nextEl){
      nextEl.innerHTML=next
        ? `<div style="padding:14px;border:1px solid rgba(78,143,220,.22);border-radius:14px;background:rgba(12,33,61,.72)"><strong style="display:block;color:#eef6ff;font-size:14px">${String(next.lesson_name||'השיעור הבא')}</strong><span style="display:block;margin-top:5px;color:#8fa6c5;font-size:11px">${currentStatus(next.status)?'בתהליך':'מוכן להתחלה'}</span></div>`
        : `<div style="padding:14px;color:#68e58f;font-weight:800">כל השיעורים הושלמו 🎉</div>`;
    }
  }

  async function refresh(subjectId){
    const client=getClient(), kid=getKid();
    const sid=subjectId || activeSubjectId;
    if(!client || !kid?.id || !sid) return;
    activeSubjectId=sid;
    try{
      const [u,l]=await Promise.all([
        client.from('kid_custom_units').select('id,custom_subject_id,topic_name,unit_name,unit_order,status').eq('kid_id',kid.id).eq('custom_subject_id',sid).neq('status','archived').order('unit_order',{ascending:true}),
        client.from('kid_custom_lessons').select('id,custom_subject_id,custom_unit_id,lesson_name,lesson_order,status').eq('kid_id',kid.id).eq('custom_subject_id',sid).neq('status','archived').order('lesson_order',{ascending:true})
      ]);
      if(u.error) throw u.error;
      if(l.error) throw l.error;
      cache={units:Array.isArray(u.data)?u.data:[],lessons:Array.isArray(l.data)?l.data:[]};
      paintSide();
      paintTree();
      setTimeout(paintTree,40);
    }catch(e){console.warn('CUSTOM SUBJECT PROGRESS LOAD',e);}
  }

  async function markLessonStarted(card){
    const client=getClient(), kid=getKid();
    if(!client || !kid?.id || !activeSubjectId || !card) return;
    const id=card.dataset.lessonId;
    const name=card.querySelector('strong')?.textContent?.trim();
    let lesson=cache.lessons.find(l=>String(l.id)===String(id));
    if(!lesson && name) lesson=cache.lessons.find(l=>String(l.lesson_name).trim()===name);
    if(!lesson) return;
    const status=String(lesson.status||'').toLowerCase();
    if(!['pending','ready'].includes(status)) return;
    try{
      const {error}=await client.from('kid_custom_lessons').update({status:'active',updated_at:new Date().toISOString()}).eq('id',lesson.id).eq('kid_id',kid.id);
      if(error) throw error;
      lesson.status='active';
      paintSide(); paintTree();
    }catch(e){console.warn('CUSTOM LESSON START TRACK',e);}
  }

  const original=window.openCustomSubject;
  if(typeof original==='function'){
    window.openCustomSubject=async function(subjectId,subjectName){
      activeSubjectId=subjectId;
      const result=await original.apply(this,arguments);
      setTimeout(()=>refresh(subjectId),30);
      return result;
    };
  }

  document.addEventListener('click',function(event){
    if(!document.body.classList.contains('custom-subject-mode')) return;
    const card=event.target?.closest?.('#customSubjectTree .custom-topic-card,#customSubjectTree .custom-unit-card,#customSubjectTree .custom-lesson-card');
    if(!card) return;
    if(card.classList.contains('custom-lesson-card')) markLessonStarted(card);
    setTimeout(()=>{paintSide();paintTree();},60);
  },false);

  window.refreshCustomSubjectProgress=refresh;
})();
</script>
'''
    s = s.replace('</body>', block + '\n</body>', 1)

s = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.41', s, count=1)
s = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.41";', s, count=1)

p.write_text(s,encoding='utf-8')
print('custom subject progress connected; build 0.7.41')
