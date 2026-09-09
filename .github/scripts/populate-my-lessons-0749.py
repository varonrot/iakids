from pathlib import Path
import re

p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
start=s.find('<style id="IAKIDS_INTERNAL_MY_LESSONS_0747_STYLES">')
end=s.find('</script>', s.find('<script id="IAKIDS_INTERNAL_MY_LESSONS_0747">', start))
if start<0 or end<0:
    raise SystemExit('internal my lessons block not found')
end += len('</script>')

block=r'''
<style id="IAKIDS_INTERNAL_MY_LESSONS_0749_STYLES">
  .iakids-my-lessons-view{position:absolute;inset:12px;z-index:246;overflow:auto;direction:rtl;border:1px solid rgba(67,137,218,.26);border-radius:24px;background:linear-gradient(180deg,#06162d 0%,#041125 100%);color:#eef6ff;box-shadow:0 24px 70px rgba(0,0,0,.38);font-family:"Heebo",Arial,sans-serif}
  .iakids-my-lessons-view[hidden]{display:none!important}.iml-shell{padding:22px;max-width:1400px;margin:0 auto}.iml-head{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:16px}.iml-title h1{margin:0;font-size:31px;font-weight:950}.iml-title p{margin:4px 0 0;color:#91a8c8;font-size:13px}.iml-close{height:38px;padding:0 14px;border-radius:11px;border:1px solid rgba(89,150,226,.24);background:#102b50;color:#e7f2ff;font-weight:900;cursor:pointer}
  .iml-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:16px}.iml-kpi{padding:15px;border-radius:16px;background:linear-gradient(180deg,rgba(17,43,79,.94),rgba(9,27,55,.95));border:1px solid rgba(80,137,207,.18)}.iml-kpi small{display:block;color:#86a0c3;font-size:11px}.iml-kpi strong{display:block;font-size:25px;margin-top:3px}.iml-grid{display:grid;grid-template-columns:1.15fr .85fr;gap:14px;margin-bottom:14px}.iml-card{background:linear-gradient(180deg,rgba(17,43,79,.94),rgba(9,27,55,.95));border:1px solid rgba(80,137,207,.18);border-radius:18px;padding:16px}.iml-card h3{margin:0 0 12px;font-size:17px}.iml-continue{display:grid;grid-template-columns:1fr auto;align-items:center;gap:14px}.iml-continue-title{font-size:19px;font-weight:950}.iml-meta{color:#8da5c5;font-size:12px;margin-top:4px}.iml-progress{height:8px;border-radius:999px;background:#091b33;overflow:hidden;margin-top:10px}.iml-progress span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#6b52ff,#39cef6)}.iml-action{border:0;border-radius:11px;background:linear-gradient(90deg,#1abaff,#3368ff);color:#fff;font-weight:900;padding:10px 14px;cursor:pointer}.iml-list{display:grid;gap:9px}.iml-row{display:grid;grid-template-columns:minmax(0,1.3fr) .7fr .7fr auto;gap:10px;align-items:center;padding:11px 12px;border-radius:13px;background:rgba(7,25,50,.64);border:1px solid rgba(74,131,203,.14)}.iml-row b{font-size:13px}.iml-row small{display:block;color:#7f99bd;font-size:10px;margin-top:2px}.iml-chip{display:inline-flex;align-items:center;justify-content:center;min-width:74px;height:28px;padding:0 9px;border-radius:999px;font-size:10px;font-weight:900;border:1px solid rgba(90,154,236,.25);background:#102c52;color:#bcd7f7}.iml-chip.done{color:#8dffc1;border-color:rgba(56,220,125,.35);background:rgba(32,145,83,.18)}.iml-chip.partial{color:#ffd58a;border-color:rgba(255,183,70,.34);background:rgba(180,113,24,.16)}.iml-section{margin-top:14px}.iml-empty{padding:26px;text-align:center;color:#8199b9}.iml-personal-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.iml-personal{padding:11px;border-radius:13px;background:rgba(7,25,50,.64);border:1px solid rgba(74,131,203,.14)}.iml-personal b{display:block;font-size:12px}.iml-personal small{color:#8199b9;font-size:10px}.iml-loading{padding:60px;text-align:center;color:#9db7d9}
  @media(max-width:1150px){.iml-grid{grid-template-columns:1fr}.iml-kpis{grid-template-columns:repeat(2,1fr)}.iml-row{grid-template-columns:1fr 1fr}.iml-personal-grid{grid-template-columns:1fr 1fr}}
</style>
<script id="IAKIDS_INTERNAL_MY_LESSONS_0749">
(function(){
  let view=null;
  function getClient(){try{if(typeof sb!=='undefined'&&sb?.from)return sb}catch(_e){}return window.sb?.from?window.sb:(window.supabaseClient?.from?window.supabaseClient:null)}
  function getKid(){try{if(typeof CURRENT_KID!=='undefined'&&CURRENT_KID?.id)return CURRENT_KID}catch(_e){}return window.CURRENT_KID||window.SELECTED_KID||window.currentKid||null}
  function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}
  function pct(v){return Math.max(0,Math.min(100,Math.round(Number(v)||0)))}
  function statusText(v){return ({completed:'הושלם',in_progress:'בתהליך',partial:'חלקי',pending:'ממתין',ready:'מוכן',active:'פעיל'})[v]||v||'לא התחיל'}
  function statusClass(v){return v==='completed'?'done':(v==='in_progress'||v==='partial'?'partial':'')}
  function dateText(v){if(!v)return '—';try{return new Date(v).toLocaleDateString('he-IL',{day:'2-digit',month:'2-digit'})}catch(_e){return '—'}}
  function closeOthers(){try{window.closeWorkspaceAchievements?.()}catch(_e){}try{window.closeLearningProgress?.()}catch(_e){}try{const d=document.getElementById('iakidsLearningDashboard');if(d)d.hidden=true}catch(_e){}try{window.closeMyFilesInternal?.()}catch(_e){}}
  function ensureView(){if(view?.isConnected)return view;const main=document.querySelector('.main');if(!main)return null;view=document.createElement('section');view.id='iakidsMyLessonsInternalView';view.className='iakids-my-lessons-view';view.hidden=true;main.appendChild(view);return view}
  function closeView(){const el=ensureView();if(el)el.hidden=true;document.querySelectorAll('.kid-actions .side-item').forEach(x=>{if((x.textContent||'').includes('השיעורים שלי'))x.classList.remove('active')})}
  function tryOpenLesson(row){closeView();try{if(typeof window.startSelectedUnitLesson==='function'){window.startSelectedUnitLesson({id:row.unit_lesson_id,learning_lesson_id:row.learning_lesson_id,lesson_name:row.lesson_name,unit_name:row.unit_name});return}}catch(e){console.warn('MY LESSONS OPEN',e)} }
  function tryOpenHomework(){closeView();try{if(typeof window.showHomeworkLessonWorkspace==='function'){window.showHomeworkLessonWorkspace();return}}catch(e){console.warn('MY HOMEWORK OPEN',e)}}
  function tryOpenCustom(subjectId,subjectName){closeView();try{if(typeof window.openCustomSubject==='function'){window.openCustomSubject(subjectId,subjectName);return}}catch(e){console.warn('MY CUSTOM OPEN',e)}}
  async function openView(item){closeOthers();const el=ensureView(),client=getClient(),kid=getKid();if(!el)return;el.hidden=false;document.querySelectorAll('.kid-actions .side-item').forEach(x=>x.classList.remove('active'));item?.classList.add('active');el.innerHTML='<div class="iml-loading"><i class="fa-solid fa-spinner fa-spin"></i><br>טוענים את השיעורים שלך...</div>';if(!client||!kid?.id){el.innerHTML='<div class="iml-shell"><div class="iml-empty">לא הצלחתי לזהות את פרופיל הילד/ה.</div></div>';return}
    try{
      const [upr,hwr,csr,clr]=await Promise.all([
        client.from('kid_unit_lesson_progress').select('unit_lesson_id,learning_lesson_id,status,progress_percent,current_stage,mastery_score,best_mastery_score,last_activity_at').eq('kid_id',kid.id).order('last_activity_at',{ascending:false}),
        client.from('homework_sessions').select('id,subject,topic,total_questions,completed_questions,status,started_at,last_activity_at').eq('kid_id',kid.id).order('last_activity_at',{ascending:false}).limit(12),
        client.from('kid_custom_subjects').select('id,subject_name,status').eq('kid_id',kid.id),
        client.from('kid_custom_lessons').select('id,custom_subject_id,lesson_name,lesson_order,status,updated_at').eq('kid_id',kid.id).neq('status','archived').order('lesson_order',{ascending:true})
      ]);
      const units=upr.error?[]:(upr.data||[]), homeworks=hwr.error?[]:(hwr.data||[]), subjects=csr.error?[]:(csr.data||[]), customLessons=clr.error?[]:(clr.data||[]);
      const unitIds=[...new Set(units.map(x=>x.unit_lesson_id).filter(Boolean))], parentIds=[...new Set(units.map(x=>x.learning_lesson_id).filter(Boolean))];
      let unitMeta=[], parentMeta=[];
      if(unitIds.length){const q=await client.from('lesson_units_content').select('id,learning_lesson_id,unit_name,lesson_name,lesson_order').in('id',unitIds);if(!q.error)unitMeta=q.data||[]}
      if(parentIds.length){const q=await client.from('learning_lessons').select('id,subject,category,lesson_name').in('id',parentIds);if(!q.error)parentMeta=q.data||[]}
      const um=new Map(unitMeta.map(x=>[String(x.id),x])), pm=new Map(parentMeta.map(x=>[String(x.id),x])), sm=new Map(subjects.map(x=>[String(x.id),x]));
      const rows=units.map(x=>{const u=um.get(String(x.unit_lesson_id))||{},p=pm.get(String(x.learning_lesson_id))||{};return {...x,lesson_name:u.lesson_name||'שיעור',unit_name:u.unit_name||'',subject:p.subject||'למידה',category:p.category||'',parent_lesson:p.lesson_name||'',mastery:Number(x.best_mastery_score||x.mastery_score||0)}});
      const active=rows.find(x=>x.status==='in_progress')||rows.find(x=>x.status==='partial')||rows[0];
      const completed=rows.filter(x=>x.status==='completed').length, inProgress=rows.filter(x=>x.status==='in_progress'||x.status==='partial').length, hwActive=homeworks.filter(x=>x.status!=='completed').length, personalPending=customLessons.filter(x=>x.status!=='completed').length;
      const regularHtml=rows.length?rows.slice(0,8).map(r=>`<div class="iml-row"><div><b>${esc(r.lesson_name)}</b><small>${esc(r.subject)}${r.unit_name?' · '+esc(r.unit_name):''}</small></div><div><span class="iml-chip ${statusClass(r.status)}">${statusText(r.status)}</span></div><div><b>${r.mastery}%</b><small>שליטה</small></div><button class="iml-action" data-unit="${r.unit_lesson_id}" style="padding:7px 10px">פתח</button></div>`).join(''):'<div class="iml-empty">עדיין לא נפתחו שיעורים רגילים.</div>';
      const hwHtml=homeworks.length?homeworks.slice(0,6).map(h=>{const t=Number(h.total_questions||0),d=Number(h.completed_questions||0),p=t?Math.round(d/t*100):(h.status==='completed'?100:0);return `<div class="iml-row"><div><b>${esc(h.topic||h.subject||'שיעורי בית')}</b><small>${esc(h.subject||'')} · ${dateText(h.last_activity_at||h.started_at)}</small></div><div><span class="iml-chip ${statusClass(h.status)}">${statusText(h.status)}</span></div><div><b>${d}/${t||'?'}</b><small>${p}% הושלם</small></div><button class="iml-action" data-homework="1" style="padding:7px 10px">פתח</button></div>`}).join(''):'<div class="iml-empty">עדיין אין שיעורי בית שמורים.</div>';
      const personalHtml=customLessons.length?customLessons.slice(0,12).map(c=>{const s=sm.get(String(c.custom_subject_id));return `<div class="iml-personal" data-custom-subject="${esc(c.custom_subject_id)}"><b>${esc(c.lesson_name)}</b><small>${esc(s?.subject_name||'מקצוע אישי')} · ${statusText(c.status)}</small></div>`}).join(''):'<div class="iml-empty">עדיין אין שיעורים במערכת האישית.</div>';
      el.innerHTML=`<div class="iml-shell"><div class="iml-head"><div class="iml-title"><h1>השיעורים שלי</h1><p>השיעורים, שיעורי הבית והמערכת האישית של ${esc(kid.child_name||kid.name||'הילד/ה')}</p></div><button type="button" class="iml-close"><i class="fa-solid fa-arrow-right"></i> חזרה</button></div>
      <div class="iml-kpis"><div class="iml-kpi"><small>שיעורים בתהליך</small><strong>${inProgress}</strong></div><div class="iml-kpi"><small>שיעורים שהושלמו</small><strong>${completed}</strong></div><div class="iml-kpi"><small>שיעורי בית פעילים</small><strong>${hwActive}</strong></div><div class="iml-kpi"><small>שיעורים אישיים</small><strong>${personalPending}</strong></div></div>
      <div class="iml-grid"><section class="iml-card"><h3>המשך מאיפה שעצרתי</h3>${active?`<div class="iml-continue"><div><div class="iml-continue-title">${esc(active.lesson_name)}</div><div class="iml-meta">${esc(active.subject)} · ${esc(active.unit_name)} · ${statusText(active.status)}</div><div class="iml-progress"><span style="width:${pct(active.progress_percent)}%"></span></div></div><button class="iml-action" data-unit="${active.unit_lesson_id}">המשך שיעור</button></div>`:'<div class="iml-empty">עדיין אין שיעור פעיל.</div>'}</section><section class="iml-card"><h3>תמונת מצב</h3><div class="iml-list"><div class="iml-row" style="grid-template-columns:1fr auto"><div><b>${rows.length} שיעורים רגילים נפתחו</b><small>${homeworks.length} סשנים של שיעורי בית</small></div><span class="iml-chip">${subjects.length} מקצועות אישיים</span></div></div></section></div>
      <section class="iml-card iml-section"><h3>השיעורים שלי</h3><div class="iml-list">${regularHtml}</div></section>
      <section class="iml-card iml-section"><h3>שיעורי הבית שלי</h3><div class="iml-list">${hwHtml}</div></section>
      <section class="iml-card iml-section"><h3>המערכת האישית שלי</h3><div class="iml-personal-grid">${personalHtml}</div></section></div>`;
      el.querySelector('.iml-close')?.addEventListener('click',closeView);
      el.querySelectorAll('[data-unit]').forEach(b=>b.addEventListener('click',()=>{const r=rows.find(x=>String(x.unit_lesson_id)===String(b.dataset.unit));if(r)tryOpenLesson(r)}));
      el.querySelectorAll('[data-homework]').forEach(b=>b.addEventListener('click',tryOpenHomework));
      el.querySelectorAll('[data-custom-subject]').forEach(b=>b.addEventListener('click',()=>{const s=sm.get(String(b.dataset.customSubject));if(s)tryOpenCustom(s.id,s.subject_name)}));
    }catch(e){console.error('MY LESSONS REAL LOAD ERROR',e);el.innerHTML='<div class="iml-shell"><div class="iml-empty">לא הצלחתי לטעון כרגע את נתוני השיעורים.</div></div>'}
  }
  document.addEventListener('click',event=>{const item=event.target?.closest?.('.kid-actions .side-item, .side-item');if(!item)return;const text=(item.textContent||'').replace(/\s+/g,' ').trim();if(!text.includes('השיעורים שלי'))return;event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();openView(item)},true);
  window.openMyLessonsInternal=openView;window.closeMyLessonsInternal=closeView;
})();
</script>
'''

s=s[:start]+block+s[end:]
s=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.49',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.49";',s,count=1)
p.write_text(s,encoding='utf-8')
print('real my lessons dashboard applied 0.7.49')
