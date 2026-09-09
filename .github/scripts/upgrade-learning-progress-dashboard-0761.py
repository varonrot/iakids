from pathlib import Path
import re

p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
MARK='IAKIDS_PROGRESS_DASHBOARD_0761'
if MARK in s:
    print('already applied')
    raise SystemExit(0)

block=r'''

<style id="IAKIDS_PROGRESS_DASHBOARD_0761_STYLES">
  .iakids-progress-pro{position:absolute;inset:14px;z-index:265;overflow:auto;direction:rtl;color:#eef6ff;border:1px solid rgba(61,143,236,.28);border-radius:24px;background:radial-gradient(circle at 8% 0%,rgba(59,94,255,.16),transparent 28%),radial-gradient(circle at 92% 0%,rgba(26,203,255,.10),transparent 25%),linear-gradient(180deg,#07162e 0%,#041025 100%);box-shadow:0 28px 75px rgba(0,0,0,.38);font-family:"Heebo",Arial,sans-serif}
  .iakids-progress-pro[hidden]{display:none!important}.ipp-shell{max-width:1420px;margin:0 auto;padding:22px}.ipp-head{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:16px}.ipp-title{display:flex;align-items:center;gap:13px}.ipp-title-icon{width:52px;height:52px;display:grid;place-items:center;border-radius:16px;background:linear-gradient(135deg,#1ab7ef,#4368ff);box-shadow:0 10px 24px rgba(34,154,255,.20);font-size:21px}.ipp-title h1{margin:0;font-size:29px;font-weight:950}.ipp-title p{margin:3px 0 0;color:#819abc;font-size:12px;font-weight:700}.ipp-back{height:40px;padding:0 15px;border-radius:12px;border:1px solid rgba(91,149,220,.28);background:#0e294c;color:#e8f3ff;font-weight:900;cursor:pointer}
  .ipp-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin-bottom:12px}.ipp-kpi{min-height:98px;padding:14px 15px;border:1px solid rgba(72,133,205,.20);border-radius:17px;background:linear-gradient(180deg,rgba(16,42,76,.92),rgba(8,25,51,.94));box-shadow:inset 0 1px 0 rgba(255,255,255,.025),0 9px 22px rgba(0,0,0,.13)}.ipp-kpi i{color:#55d5ff;font-size:17px}.ipp-kpi strong{display:block;margin-top:10px;font-size:25px;line-height:1;font-weight:950}.ipp-kpi span{display:block;margin-top:7px;color:#8299b9;font-size:11px;font-weight:750}
  .ipp-row-main{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(260px,.62fr) minmax(300px,.83fr);gap:12px;margin-bottom:12px}.ipp-card{border:1px solid rgba(73,133,205,.20);border-radius:19px;background:linear-gradient(180deg,rgba(13,37,69,.92),rgba(7,23,48,.94));padding:16px;min-width:0;box-shadow:0 10px 28px rgba(0,0,0,.13)}.ipp-card h2{margin:0;font-size:17px;font-weight:950}.ipp-card-sub{color:#8097b8;font-size:11px;font-weight:700;margin-top:3px}.ipp-week-chart{height:190px;display:flex;align-items:flex-end;gap:9px;padding:20px 6px 4px;border-bottom:1px solid rgba(85,130,187,.14)}.ipp-day{flex:1;min-width:0;height:100%;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:7px}.ipp-day-bars{height:145px;width:min(42px,84%);display:flex;align-items:flex-end;justify-content:center;gap:3px}.ipp-bar{width:12px;min-height:3px;border-radius:6px 6px 2px 2px}.ipp-bar.learn{background:linear-gradient(180deg,#39d9ff,#3875ff);box-shadow:0 0 10px rgba(53,172,255,.14)}.ipp-bar.hw{background:linear-gradient(180deg,#8f63ff,#6f42e8)}.ipp-day b{font-size:11px;color:#9eb0c9}.ipp-legend{display:flex;gap:14px;margin-top:10px;color:#8da1bc;font-size:10px;font-weight:750}.ipp-dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-left:5px}.ipp-dot.learn{background:#3bd6ff}.ipp-dot.hw{background:#8d62ff}
  .ipp-donut-wrap{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}.ipp-donut{--p:0;width:145px;height:145px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#39d7ff calc(var(--p)*1%),rgba(43,75,119,.28) 0);position:relative;box-shadow:0 0 26px rgba(46,183,255,.08)}.ipp-donut:after{content:"";position:absolute;inset:14px;border-radius:50%;background:#0a1b36;border:1px solid rgba(74,128,194,.14)}.ipp-donut strong{position:relative;z-index:2;font-size:36px;font-weight:950}.ipp-donut-label{margin-top:11px;font-weight:900}.ipp-donut-meta{margin-top:5px;color:#8398b6;font-size:11px}
  .ipp-continue{display:flex;flex-direction:column;height:100%}.ipp-continue-badge{width:max-content;margin-top:14px;padding:5px 9px;border-radius:999px;background:rgba(48,192,255,.10);border:1px solid rgba(61,189,255,.20);color:#66dcff;font-size:10px;font-weight:900}.ipp-continue h3{font-size:19px;margin:12px 0 3px}.ipp-continue p{margin:0;color:#849bbd;font-size:11px;line-height:1.55}.ipp-progressline{height:8px;border-radius:999px;background:rgba(80,110,151,.18);overflow:hidden;margin:16px 0 8px}.ipp-progressline>span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#3a79ff,#38dcf4)}.ipp-continue-btn{margin-top:auto;height:42px;border:0;border-radius:12px;background:linear-gradient(90deg,#17bff1,#4e67ff);color:white;font-weight:950;cursor:pointer}
  .ipp-row-secondary{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr);gap:12px;margin-bottom:12px}.ipp-subjects{display:grid;gap:10px;margin-top:14px}.ipp-subject{padding:10px 11px;border-radius:13px;background:rgba(10,29,56,.72);border:1px solid rgba(66,117,181,.14)}.ipp-subject-top{display:flex;justify-content:space-between;gap:12px;margin-bottom:7px}.ipp-subject b{font-size:12px}.ipp-subject span{font-size:11px;color:#55d9ff;font-weight:900}.ipp-mini-track{height:7px;background:rgba(82,110,151,.17);border-radius:999px;overflow:hidden}.ipp-mini-track i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#396eff,#42ddeb)}
  .ipp-activity{display:grid;gap:8px;margin-top:13px}.ipp-activity-item{display:flex;align-items:center;gap:10px;padding:10px;border-radius:13px;background:rgba(9,28,54,.72);border:1px solid rgba(70,122,185,.13)}.ipp-act-icon{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:rgba(50,105,184,.17);color:#62d9ff}.ipp-act-copy{min-width:0}.ipp-act-copy b{display:block;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ipp-act-copy span{display:block;margin-top:2px;color:#8198b7;font-size:10px}.ipp-empty{padding:22px;text-align:center;color:#7d93b1;font-size:11px;font-weight:750}
  .ipp-custom-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin-top:13px}.ipp-custom{padding:13px;border-radius:15px;background:linear-gradient(180deg,rgba(14,39,72,.84),rgba(8,25,51,.88));border:1px solid rgba(75,137,211,.17)}.ipp-custom-top{display:flex;justify-content:space-between;gap:10px}.ipp-custom h3{margin:0;font-size:14px}.ipp-custom .pct{color:#53dcff;font-weight:950}.ipp-custom-meta{margin-top:5px;color:#8198b8;font-size:10px}.ipp-goals{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:13px}.ipp-goal{padding:11px;border-radius:13px;background:rgba(9,28,54,.70);border:1px solid rgba(72,126,191,.13)}.ipp-goal b{font-size:11px}.ipp-goal span{float:left;color:#62dbff;font-size:11px;font-weight:900}
  @media(max-width:1180px){.ipp-kpis{grid-template-columns:repeat(3,1fr)}.ipp-row-main{grid-template-columns:1fr 1fr}.ipp-row-main>.ipp-card:first-child{grid-column:1/3}.ipp-row-secondary{grid-template-columns:1fr}}@media(max-width:760px){.iakids-progress-pro{inset:6px}.ipp-shell{padding:12px}.ipp-kpis{grid-template-columns:repeat(2,1fr)}.ipp-row-main{grid-template-columns:1fr}.ipp-row-main>.ipp-card:first-child{grid-column:auto}.ipp-goals{grid-template-columns:1fr}.ipp-title h1{font-size:22px}}
</style>
<script id="IAKIDS_PROGRESS_DASHBOARD_0761">
(function(){
  if(window.__IAKIDS_PROGRESS_DASHBOARD_0761) return;
  window.__IAKIDS_PROGRESS_DASHBOARD_0761=true;
  let view=null;
  const esc=v=>String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
  const clamp=v=>Math.max(0,Math.min(100,Number(v)||0));
  function client(){try{if(typeof sb!=='undefined'&&sb?.from)return sb}catch(_e){}return window.sb?.from?window.sb:(window.supabaseClient?.from?window.supabaseClient:null)}
  function kid(){try{if(typeof CURRENT_KID!=='undefined'&&CURRENT_KID?.id)return CURRENT_KID}catch(_e){}return window.CURRENT_KID||window.SELECTED_KID||window.currentKid||window.selectedKid||null}
  function ensure(){if(view?.isConnected)return view;const main=document.querySelector('.main');if(!main)return null;view=document.createElement('section');view.id='iakidsProgressPro';view.className='iakids-progress-pro';view.hidden=true;main.appendChild(view);return view}
  function close(){const v=ensure();if(v)v.hidden=true;document.querySelectorAll('.kid-actions .side-item').forEach(x=>{if((x.textContent||'').includes('התקדמות'))x.classList.remove('active')})}
  function statusWeight(r){const s=String(r?.status||'');const raw=clamp(r?.progress_percent);if(s==='completed')return 100;if(s==='partial')return Math.max(raw,50);if(s==='in_progress'||s==='active')return Math.max(raw,25);return raw}
  function dateKey(v){if(!v)return null;const d=new Date(v);if(Number.isNaN(d.getTime()))return null;return d.toISOString().slice(0,10)}
  function localDay(i){const d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()-i);return dateKey(d)}
  function fmtTime(sec){sec=Math.max(0,Number(sec)||0);if(sec<60)return `${Math.round(sec)} שנ׳`;const m=Math.round(sec/60);if(m<60)return `${m} דק׳`;const h=Math.floor(m/60),rm=m%60;return `${h} ש׳ ${rm?rm+' דק׳':''}`.trim()}
  function heSubject(v){const x=String(v||'').trim();const m={science:'מדעים',math:'מתמטיקה',mathematics:'מתמטיקה',hebrew:'עברית',english:'אנגלית',history:'היסטוריה',geography:'גאוגרפיה',bible:'תנ״ך'};return m[x.toLowerCase()]||x||'למידה'}

  async function open(){
    const v=ensure(),c=client(),k=kid();if(!v)return;v.hidden=false;
    try{window.closeWorkspaceAchievements?.()}catch(_e){}
    const old=document.getElementById('iakidsLearningProgressView');if(old)old.hidden=true;
    v.innerHTML='<div class="ipp-empty" style="padding-top:80px"><i class="fa-solid fa-spinner fa-spin"></i><br>טוענים את ההתקדמות שלך...</div>';
    if(!c||!k?.id){v.innerHTML='<div class="ipp-empty">לא הצלחנו לזהות את פרופיל הילד/ה.</div>';return}
    try{
      const weekStart=new Date();weekStart.setHours(0,0,0,0);weekStart.setDate(weekStart.getDate()-6);
      const [unitR,lessonR,hwR,customSubR,customLessonR,sessionR]=await Promise.all([
        c.from('kid_unit_lesson_progress').select('unit_lesson_id,learning_lesson_id,status,progress_percent,mastery_score,last_activity_at,updated_at,completed_at').eq('kid_id',k.id),
        c.from('kid_lesson_progress').select('lesson_id,status,progress_percent,mastery_score,last_activity_at,updated_at,completed_at').eq('kid_id',k.id),
        c.from('homework_sessions').select('subject,topic,status,total_questions,completed_questions,last_activity_at,started_at,completed_at').eq('kid_id',k.id).order('last_activity_at',{ascending:false}).limit(60),
        c.from('kid_custom_subjects').select('id,subject_name,status').eq('kid_id',k.id).eq('status','active'),
        c.from('kid_custom_lessons').select('id,custom_subject_id,custom_unit_id,lesson_name,status,updated_at').eq('kid_id',k.id).neq('status','archived'),
        c.from('tutor_sessions').select('started_at,last_activity_at,duration_seconds,status').eq('kid_id',k.id).gte('started_at',weekStart.toISOString())
      ]);
      const units=unitR.error?[]:(unitR.data||[]), lessons=lessonR.error?[]:(lessonR.data||[]), hws=hwR.error?[]:(hwR.data||[]), customSubs=customSubR.error?[]:(customSubR.data||[]), allCustom=customLessonR.error?[]:(customLessonR.data||[]), sessions=sessionR.error?[]:(sessionR.data||[]);
      const activeIds=new Set(customSubs.map(x=>String(x.id)));const customs=allCustom.filter(x=>activeIds.has(String(x.custom_subject_id)));
      const base=units.length?units:lessons;
      const completed=base.filter(x=>x.status==='completed').length+customs.filter(x=>x.status==='completed').length;
      const inProgress=base.filter(x=>['partial','in_progress','active'].includes(String(x.status))).length+customs.filter(x=>['active','ready','partial','in_progress'].includes(String(x.status))).length;
      const total=base.length+customs.length;
      const score=(base.reduce((s,x)=>s+statusWeight(x),0)+customs.reduce((s,x)=>s+(x.status==='completed'?100:(x.status==='active'?50:(x.status==='ready'?25:0))),0));
      const overall=total?Math.round(score/total):0;
      const weekSeconds=sessions.reduce((s,x)=>s+Number(x.duration_seconds||0),0);

      const parentIds=[...new Set(base.map(x=>x.learning_lesson_id||x.lesson_id).filter(Boolean).map(String))];let parentMeta=[];
      if(parentIds.length){const r=await c.from('learning_lessons').select('id,subject,category,lesson_name').in('id',parentIds);if(!r.error)parentMeta=r.data||[]}
      const pmap=new Map(parentMeta.map(x=>[String(x.id),x]));
      const unitIds=[...new Set(units.map(x=>x.unit_lesson_id).filter(Boolean).map(String))];let unitMeta=[];
      if(unitIds.length){const r=await c.from('lesson_units_content').select('id,unit_name,lesson_name,parent_lesson,lesson_order').in('id',unitIds);if(!r.error)unitMeta=r.data||[]}
      const umap=new Map(unitMeta.map(x=>[String(x.id),x]));

      const subjectMap=new Map();base.forEach(x=>{const pm=pmap.get(String(x.learning_lesson_id||x.lesson_id));const name=heSubject(pm?.subject);if(!subjectMap.has(name))subjectMap.set(name,{name,rows:[]});subjectMap.get(name).rows.push(x)});
      const subjects=[...subjectMap.values()].map(g=>({name:g.name,pct:Math.round(g.rows.reduce((s,x)=>s+statusWeight(x),0)/Math.max(1,g.rows.length)),completed:g.rows.filter(x=>x.status==='completed').length,total:g.rows.length,mastery:Math.round(g.rows.reduce((s,x)=>s+Number(x.mastery_score||0),0)/Math.max(1,g.rows.length))})).sort((a,b)=>b.pct-a.pct);

      const cgroups=customSubs.map(s=>{const rows=customs.filter(x=>String(x.custom_subject_id)===String(s.id));const done=rows.filter(x=>x.status==='completed').length;const pct=rows.length?Math.round(rows.reduce((sum,x)=>sum+(x.status==='completed'?100:(x.status==='active'?50:(x.status==='ready'?25:0))),0)/rows.length):0;return{name:s.subject_name,done,total:rows.length,pct}});

      const activities=[];base.forEach(x=>{const pm=pmap.get(String(x.learning_lesson_id||x.lesson_id)),um=umap.get(String(x.unit_lesson_id));activities.push({date:x.last_activity_at||x.updated_at||x.completed_at,title:um?.lesson_name||pm?.lesson_name||'שיעור לימודי',sub:`${heSubject(pm?.subject)} · ${x.status==='completed'?'הושלם':'בתהליך'}`,icon:'book-open'})});hws.forEach(x=>activities.push({date:x.last_activity_at||x.started_at,title:x.topic||x.subject||'שיעורי בית',sub:`שיעורי בית · ${x.status==='completed'?'הושלם':'בתהליך'}`,icon:'list-check'}));activities.sort((a,b)=>new Date(b.date||0)-new Date(a.date||0));
      const active=base.filter(x=>['in_progress','partial','active'].includes(String(x.status))).sort((a,b)=>new Date(b.last_activity_at||b.updated_at||0)-new Date(a.last_activity_at||a.updated_at||0))[0]||base[0];const activeP=active?pmap.get(String(active.learning_lesson_id||active.lesson_id)):null, activeU=active?umap.get(String(active.unit_lesson_id)):null;

      const learnCounts=[],hwCounts=[],dayLabels=['א׳','ב׳','ג׳','ד׳','ה׳','ו׳','ש׳'];
      for(let i=6;i>=0;i--){const key=localDay(i);learnCounts.push(base.filter(x=>dateKey(x.last_activity_at||x.updated_at||x.completed_at)===key).length);hwCounts.push(hws.filter(x=>dateKey(x.last_activity_at||x.started_at||x.completed_at)===key).length)}
      const mx=Math.max(1,...learnCounts,...hwCounts);const chart=learnCounts.map((n,i)=>`<div class="ipp-day"><div class="ipp-day-bars"><div class="ipp-bar learn" style="height:${Math.max(n?12:3,Math.round(n/mx*100))}%"></div><div class="ipp-bar hw" style="height:${Math.max(hwCounts[i]?12:3,Math.round(hwCounts[i]/mx*100))}%"></div></div><b>${dayLabels[i]}</b></div>`).join('');
      const subjHtml=subjects.length?subjects.map(x=>`<div class="ipp-subject"><div class="ipp-subject-top"><b>${esc(x.name)}</b><span>${x.pct}% · ${x.completed}/${x.total}</span></div><div class="ipp-mini-track"><i style="width:${clamp(x.pct)}%"></i></div></div>`).join(''):'<div class="ipp-empty">עדיין אין מספיק נתונים לפי מקצוע.</div>';
      const actHtml=activities.length?activities.slice(0,6).map(x=>`<div class="ipp-activity-item"><div class="ipp-act-icon"><i class="fa-solid fa-${x.icon}"></i></div><div class="ipp-act-copy"><b>${esc(x.title)}</b><span>${esc(x.sub)}</span></div></div>`).join(''):'<div class="ipp-empty">עדיין אין פעילות אחרונה.</div>';
      const customHtml=cgroups.length?cgroups.map(x=>`<div class="ipp-custom"><div class="ipp-custom-top"><h3>${esc(x.name)}</h3><span class="pct">${x.pct}%</span></div><div class="ipp-custom-meta">${x.done} מתוך ${x.total} שיעורים הושלמו</div><div class="ipp-mini-track" style="margin-top:9px"><i style="width:${clamp(x.pct)}%"></i></div></div>`).join(''):'<div class="ipp-empty">אין כרגע מערכת אישית פעילה.</div>';
      const activeName=activeU?.lesson_name||activeP?.lesson_name||'בחרו שיעור כדי להתחיל';const activeSub=activeP?`${heSubject(activeP.subject)} · ${activeU?.unit_name||activeP.category||''}`:'אין כרגע שיעור פעיל';const activePct=active?statusWeight(active):0;
      const activeDays=new Set(activities.map(x=>dateKey(x.date)).filter(Boolean));let streak=0;for(let i=0;i<60;i++){if(activeDays.has(localDay(i)))streak++;else if(i===0)continue;else break}

      v.innerHTML=`<div class="ipp-shell"><div class="ipp-head"><div class="ipp-title"><div class="ipp-title-icon"><i class="fa-solid fa-chart-line"></i></div><div><h1>ההתקדמות שלי</h1><p>תמונה מלאה של הלמידה, הפעילות ומה כדאי לעשות עכשיו</p></div></div><button class="ipp-back"><i class="fa-solid fa-arrow-right"></i> חזרה</button></div>
      <div class="ipp-kpis"><div class="ipp-kpi"><i class="fa-solid fa-book-open"></i><strong>${subjects.length+cgroups.length}</strong><span>מקצועות פעילים</span></div><div class="ipp-kpi"><i class="fa-solid fa-circle-check"></i><strong>${completed}</strong><span>שיעורים שהושלמו</span></div><div class="ipp-kpi"><i class="fa-solid fa-spinner"></i><strong>${inProgress}</strong><span>שיעורים בתהליך</span></div><div class="ipp-kpi"><i class="fa-solid fa-chart-pie"></i><strong>${overall}%</strong><span>התקדמות כוללת</span></div><div class="ipp-kpi"><i class="fa-solid fa-fire"></i><strong>${streak}</strong><span>רצף יומי</span></div><div class="ipp-kpi"><i class="fa-solid fa-clock"></i><strong>${fmtTime(weekSeconds)}</strong><span>זמן לימוד השבוע</span></div></div>
      <div class="ipp-row-main"><section class="ipp-card"><h2>התקדמות שבועית</h2><div class="ipp-card-sub">פעילות לימודית ושיעורי בית ב־7 הימים האחרונים</div><div class="ipp-week-chart">${chart}</div><div class="ipp-legend"><span><i class="ipp-dot learn"></i>שיעורים</span><span><i class="ipp-dot hw"></i>שיעורי בית</span></div></section><section class="ipp-card"><div class="ipp-donut-wrap"><div class="ipp-donut" style="--p:${overall}"><strong>${overall}%</strong></div><div class="ipp-donut-label">התקדמות כוללת</div><div class="ipp-donut-meta">${completed} הושלמו · ${inProgress} בתהליך</div></div></section><section class="ipp-card"><div class="ipp-continue"><h2>המשך מאיפה שעצרת</h2><div class="ipp-continue-badge">השיעור הפעיל</div><h3>${esc(activeName)}</h3><p>${esc(activeSub)}</p><div class="ipp-progressline"><span style="width:${clamp(activePct)}%"></span></div><p>${Math.round(activePct)}% התקדמות בשיעור</p><button class="ipp-continue-btn" data-go-home>חזרה לעולם הלמידה</button></div></section></div>
      <div class="ipp-row-secondary"><section class="ipp-card"><h2>התקדמות לפי מקצוע</h2><div class="ipp-card-sub">אחוז התקדמות ומספר שיעורים בכל מקצוע</div><div class="ipp-subjects">${subjHtml}</div></section><section class="ipp-card"><h2>פעילות אחרונה</h2><div class="ipp-card-sub">השיעורים והמשימות האחרונות</div><div class="ipp-activity">${actHtml}</div></section></div>
      <section class="ipp-card" style="margin-bottom:12px"><h2>המערכת האישית שלי</h2><div class="ipp-card-sub">מסלולים שבניתם במיוחד לילד/ה</div><div class="ipp-custom-grid">${customHtml}</div></section>
      <section class="ipp-card"><h2>יעדי למידה</h2><div class="ipp-goals"><div class="ipp-goal"><b>להשלים 3 שיעורים</b><span>${Math.min(3,completed)}/3</span><div class="ipp-mini-track" style="margin-top:9px"><i style="width:${Math.min(100,completed/3*100)}%"></i></div></div><div class="ipp-goal"><b>לשמור על רצף של 5 ימים</b><span>${Math.min(5,streak)}/5</span><div class="ipp-mini-track" style="margin-top:9px"><i style="width:${Math.min(100,streak/5*100)}%"></i></div></div><div class="ipp-goal"><b>להגיע ל־75% התקדמות</b><span>${overall}%</span><div class="ipp-mini-track" style="margin-top:9px"><i style="width:${Math.min(100,overall/75*100)}%"></i></div></div></div></section></div>`;
      v.querySelector('.ipp-back')?.addEventListener('click',close);v.querySelector('[data-go-home]')?.addEventListener('click',()=>{close();document.getElementById('homeSidebarBtn')?.click()});
    }catch(e){console.error('PROGRESS DASHBOARD 0761',e);v.innerHTML='<div class="ipp-empty" style="padding-top:70px">לא הצלחנו לטעון את נתוני ההתקדמות כרגע.</div>'}
  }
  window.openLearningProgress=open;window.closeLearningProgress=close;window.openProgressDashboard=open;
  document.addEventListener('click',function(e){const el=e.target?.closest?.('.kid-actions .side-item');if(!el)return;const t=(el.textContent||'').replace(/\s+/g,' ').trim();if(t.includes('התקדמות')){e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();document.querySelectorAll('.kid-actions .side-item').forEach(x=>x.classList.remove('active'));el.classList.add('active');open()}},true);
})();
</script>
'''

if '</body>' not in s: raise SystemExit('body end not found')
s=s.replace('</body>',block+'\n</body>',1)
s=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.61',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.61";',s,count=1)
p.write_text(s,encoding='utf-8')
print('upgraded learning progress dashboard; build 0.7.61')
