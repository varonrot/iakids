from pathlib import Path
import re

p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
MARK='IAKIDS_LEARNING_DASHBOARD_0744'
if MARK not in s:
    block=r'''
<style id="IAKIDS_LEARNING_DASHBOARD_0744_STYLES">
  .main{position:relative!important}
  .iakids-learning-dashboard{position:absolute;inset:12px;z-index:245;overflow:auto;direction:rtl;border:1px solid rgba(67,137,218,.26);border-radius:24px;background:linear-gradient(180deg,#06162d 0%,#041125 100%);color:#eef6ff;box-shadow:0 24px 70px rgba(0,0,0,.38);font-family:"Heebo",Arial,sans-serif}
  .iakids-learning-dashboard[hidden]{display:none!important}
  .ild-shell{padding:18px;max-width:1400px;margin:0 auto}
  .ild-top{display:grid;grid-template-columns:1.6fr .78fr .78fr;gap:14px;margin-bottom:14px}
  .ild-card{background:linear-gradient(180deg,rgba(17,43,79,.94),rgba(9,27,55,.95));border:1px solid rgba(76,139,218,.22);border-radius:18px;box-shadow:0 10px 28px rgba(0,0,0,.16);overflow:hidden}
  .ild-welcome{padding:18px 20px}.ild-welcome h1{margin:0;font-size:27px;font-weight:950}.ild-welcome p{margin:4px 0 15px;color:#9ab0cf;font-size:13px}
  .ild-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.ild-kpi{padding:12px;border-radius:14px;background:rgba(8,27,53,.72);border:1px solid rgba(80,137,207,.18);text-align:center}.ild-kpi i{display:block;font-size:18px;margin-bottom:6px;color:#46d7ff}.ild-kpi strong{font-size:21px}.ild-kpi span{display:block;color:#91a8c8;font-size:11px;margin-top:3px}
  .ild-mini{padding:15px}.ild-mini h3,.ild-panel h3{margin:0 0 11px;font-size:16px}.ild-next-name{font-size:16px;font-weight:900;margin:8px 0 5px}.ild-muted{color:#8fa6c5;font-size:12px}.ild-btn{width:100%;height:38px;margin-top:12px;border:0;border-radius:11px;background:linear-gradient(90deg,#16b7ff,#2d63ff);color:#fff;font-weight:900;cursor:pointer}
  .ild-grid{display:grid;grid-template-columns:1.15fr .9fr .9fr;gap:14px;margin-bottom:14px}.ild-panel{padding:16px}.ild-week{height:165px;display:flex;align-items:flex-end;gap:10px;padding:10px 4px 0}.ild-day{flex:1;display:flex;flex-direction:column;align-items:center;gap:5px}.ild-bar-wrap{height:125px;width:100%;display:flex;align-items:flex-end}.ild-bar{width:100%;border-radius:7px 7px 2px 2px;background:linear-gradient(180deg,#39ddff,#1b63ff);min-height:4px}.ild-day small{font-size:10px;color:#8fa6c5}
  .ild-activity{display:grid;gap:8px}.ild-activity-item{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:12px;background:rgba(8,27,53,.66);border:1px solid rgba(75,130,198,.14)}.ild-activity-icon{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;background:rgba(61,112,199,.22);color:#60d7ff}.ild-activity-copy{flex:1}.ild-activity-copy b{display:block;font-size:12px}.ild-activity-copy span{display:block;color:#859dbd;font-size:10px;margin-top:2px}
  .ild-progress-big{font-size:30px;font-weight:950}.ild-progressbar{height:12px;border-radius:999px;background:rgba(95,123,164,.18);overflow:hidden;margin:12px 0 8px}.ild-progressbar span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#286cff,#39dbef)}
  .ild-bottom{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}.ild-goals{display:grid;gap:10px}.ild-goal{padding:10px;border-radius:12px;background:rgba(8,27,53,.66);border:1px solid rgba(74,131,203,.14)}.ild-goal-top{display:flex;justify-content:space-between;font-size:11px}.ild-goal .ild-progressbar{height:7px;margin:7px 0 0}
  .ild-steps{display:grid;gap:9px}.ild-step{display:flex;align-items:center;gap:10px;padding:10px;border-radius:12px;background:rgba(8,27,53,.66);border:1px solid rgba(74,131,203,.14)}.ild-step-num{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;background:#1a4379;color:#8fdcff;font-weight:900}
  .ild-subjects{display:grid;gap:8px}.ild-subject{padding:10px;border-radius:12px;background:rgba(8,27,53,.66);border:1px solid rgba(74,131,203,.14)}.ild-subject-head{display:flex;justify-content:space-between;gap:8px;font-size:11px}.ild-close{position:sticky;top:10px;float:left;z-index:3;height:36px;padding:0 13px;border-radius:10px;border:1px solid rgba(89,150,226,.24);background:#102b50;color:#e7f2ff;font-weight:900;cursor:pointer}
  @media(max-width:1100px){.ild-top,.ild-grid,.ild-bottom{grid-template-columns:1fr}.ild-kpis{grid-template-columns:repeat(2,1fr)}}
</style>
<script id="IAKIDS_LEARNING_DASHBOARD_0744">
(function(){
  let view=null;
  function getClient(){try{if(typeof sb!=='undefined'&&sb?.from)return sb}catch(_e){} return window.sb?.from?window.sb:(window.supabaseClient?.from?window.supabaseClient:null)}
  function getKid(){try{if(typeof CURRENT_KID!=='undefined'&&CURRENT_KID?.id)return CURRENT_KID}catch(_e){} return window.CURRENT_KID||window.SELECTED_KID||window.currentKid||null}
  function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}
  function clamp(v){return Math.max(0,Math.min(100,Math.round(Number(v)||0)))}
  function ensureButton(){const host=document.querySelector('.kid-actions');if(!host||document.getElementById('iakidsDashboardSidebarBtn'))return;const btn=document.createElement('button');btn.type='button';btn.id='iakidsDashboardSidebarBtn';btn.className='side-item';btn.innerHTML='<i class="fa-solid fa-table-columns"></i><div class="side-text"><div class="side-title">דשבורד</div></div>';const second=host.children[1]; second?host.insertBefore(btn,second):host.appendChild(btn)}
  function ensureView(){if(view?.isConnected)return view;const main=document.querySelector('.main');if(!main)return null;view=document.createElement('section');view.id='iakidsLearningDashboard';view.className='iakids-learning-dashboard';view.hidden=true;main.appendChild(view);return view}
  function close(){const el=ensureView();if(el)el.hidden=true;document.getElementById('iakidsDashboardSidebarBtn')?.classList.remove('active')}
  function weekly(rows){const out=[0,0,0,0,0,0,0],now=new Date();const start=new Date(now);start.setDate(now.getDate()-6);start.setHours(0,0,0,0);(rows||[]).forEach(r=>{const d=new Date(r.updated_at||r.started_at||r.created_at||0);if(d<start)return;const diff=Math.floor((d-start)/86400000);if(diff>=0&&diff<7)out[diff]++});return out}
  function subjectStats(progress,lessonMap){const map=new Map();(progress||[]).forEach(r=>{const meta=lessonMap.get(String(r.lesson_id));const name=meta?.subject||'למידה';if(!map.has(name))map.set(name,{name,total:0,done:0,sum:0});const x=map.get(name);x.total++;if(r.status==='completed')x.done++;x.sum+=Number(r.progress_percent||0)});return [...map.values()].map(x=>({...x,pct:x.total?Math.round(x.sum/x.total):0})).sort((a,b)=>b.pct-a.pct)}
  async function open(){ensureButton();const el=ensureView(),client=getClient(),kid=getKid();if(!el)return;el.hidden=false;el.innerHTML='<div class="ild-shell" style="padding:50px;text-align:center;color:#9db7d9"><i class="fa-solid fa-spinner fa-spin"></i><br>טוענים את הדשבורד שלך...</div>';if(!client||!kid?.id){el.innerHTML='<div class="ild-shell">לא הצלחתי לזהות את פרופיל הילד/ה.</div>';return}
    try{
      const [pr,hw,custom]=await Promise.all([
        client.from('kid_lesson_progress').select('lesson_id,status,progress_percent,mastery_score,xp_earned,stars_earned,updated_at').eq('kid_id',kid.id),
        client.from('homework_sessions').select('status,subject,topic,completed_questions,total_questions,started_at,last_activity_at').eq('kid_id',kid.id).order('started_at',{ascending:false}).limit(12),
        client.from('kid_custom_subjects').select('id,subject_name,status').eq('kid_id',kid.id).eq('status','active')
      ]);
      const progress=pr.error?[]:(pr.data||[]), homeworks=hw.error?[]:(hw.data||[]), customs=custom.error?[]:(custom.data||[]);
      const ids=[...new Set(progress.map(x=>x.lesson_id).filter(Boolean))];let lessons=[];if(ids.length){const lr=await client.from('learning_lessons').select('id,subject,lesson_name,category').in('id',ids);if(!lr.error)lessons=lr.data||[]}
      const lessonMap=new Map(lessons.map(x=>[String(x.id),x]));
      const completed=progress.filter(x=>x.status==='completed').length,total=progress.length,inprog=progress.filter(x=>x.status==='in_progress').length;const avg=total?Math.round(progress.reduce((s,x)=>s+Number(x.progress_percent||0),0)/total):0;const stars=progress.reduce((s,x)=>s+Number(x.stars_earned||0),0);const mastery=total?Math.round(progress.reduce((s,x)=>s+Number(x.mastery_score||0),0)/total):0;
      const subjects=subjectStats(progress,lessonMap);const active=progress.find(x=>x.status==='in_progress')||progress.find(x=>x.status!=='completed');const activeMeta=active?lessonMap.get(String(active.lesson_id)):null;
      const w=weekly(progress.concat(homeworks.map(x=>({...x,updated_at:x.last_activity_at||x.started_at}))));const maxW=Math.max(1,...w);const days=['א׳','ב׳','ג׳','ד׳','ה׳','ו׳','ש׳'];
      const activity=[];progress.slice().sort((a,b)=>new Date(b.updated_at||0)-new Date(a.updated_at||0)).slice(0,3).forEach(x=>{const m=lessonMap.get(String(x.lesson_id));activity.push({icon:'book-open',title:m?.lesson_name||'שיעור לימודי',sub:x.status==='completed'?'השיעור הושלם':'התקדמות בשיעור'})});homeworks.slice(0,2).forEach(x=>activity.push({icon:'list-check',title:x.topic||x.subject||'שיעורי בית',sub:x.status==='completed'?'הושלם':'בתהליך'}));
      const subjectHtml=subjects.length?subjects.slice(0,5).map(x=>`<div class="ild-subject"><div class="ild-subject-head"><b>${esc(x.name)}</b><span>${x.pct}%</span></div><div class="ild-progressbar"><span style="width:${clamp(x.pct)}%"></span></div></div>`).join(''):'<div class="ild-muted">עדיין אין מספיק נתוני מקצועות.</div>';
      const activityHtml=activity.length?activity.slice(0,5).map(x=>`<div class="ild-activity-item"><div class="ild-activity-icon"><i class="fa-solid fa-${x.icon}"></i></div><div class="ild-activity-copy"><b>${esc(x.title)}</b><span>${esc(x.sub)}</span></div></div>`).join(''):'<div class="ild-muted">עדיין אין פעילות אחרונה.</div>';
      el.innerHTML=`<div class="ild-shell"><button class="ild-close"><i class="fa-solid fa-arrow-right"></i> חזרה</button>
        <div class="ild-top">
          <section class="ild-card ild-welcome"><h1>👋 ברוך הבא למסלול הלמידה שלך</h1><p>כאן אפשר לעקוב אחרי הקורסים, ההתקדמות והשיעורים הקרובים.</p><div class="ild-kpis">
            <div class="ild-kpi"><i class="fa-solid fa-star"></i><strong>${stars}</strong><span>כוכבים</span></div>
            <div class="ild-kpi"><i class="fa-solid fa-circle-check"></i><strong>${completed}</strong><span>שיעורים שהושלמו</span></div>
            <div class="ild-kpi"><i class="fa-solid fa-chart-pie"></i><strong>${avg}%</strong><span>אחוז התקדמות</span></div>
            <div class="ild-kpi"><i class="fa-solid fa-book-open"></i><strong>${subjects.length+customs.length}</strong><span>מקצועות פעילים</span></div>
          </div></section>
          <section class="ild-card ild-mini"><h3>הקורס האחרון</h3><div class="ild-next-name">${esc(activeMeta?.subject||'מסלול הלמידה')}</div><div class="ild-muted">${esc(activeMeta?.lesson_name||'בחר שיעור כדי להתחיל')}</div><div class="ild-progressbar"><span style="width:${clamp(active?.progress_percent||0)}%"></span></div><button class="ild-btn" data-dashboard-home="1">המשך למידה</button></section>
          <section class="ild-card ild-mini"><h3>השיעור הבא</h3><div class="ild-next-name">${esc(activeMeta?.lesson_name||'עדיין לא נבחר שיעור')}</div><div class="ild-muted">${esc(activeMeta?.subject||'עולם הלמידה')}</div><button class="ild-btn" data-dashboard-home="1">המשך לשיעור</button></section>
        </div>
        <div class="ild-grid">
          <section class="ild-card ild-panel"><h3>📊 התקדמות שבועית</h3><div class="ild-week">${w.map((v,i)=>`<div class="ild-day"><div class="ild-bar-wrap"><div class="ild-bar" style="height:${Math.max(4,Math.round(v/maxW*100))}%"></div></div><small>${days[i]}</small></div>`).join('')}</div></section>
          <section class="ild-card ild-panel"><h3>🕘 פעילות אחרונה</h3><div class="ild-activity">${activityHtml}</div></section>
          <section class="ild-card ild-panel"><h3>📈 התקדמות במסלול</h3><div class="ild-progress-big">${avg}%</div><div class="ild-progressbar"><span style="width:${avg}%"></span></div><div class="ild-muted">${completed} מתוך ${total} שיעורים הושלמו · שליטה ממוצעת ${mastery}%</div></section>
        </div>
        <div class="ild-bottom">
          <section class="ild-card ild-panel"><h3>🎯 יעדי למידה</h3><div class="ild-goals"><div class="ild-goal"><div class="ild-goal-top"><b>לסיים 3 שיעורים השבוע</b><span>${Math.min(3,w.reduce((a,b)=>a+b,0))}/3</span></div><div class="ild-progressbar"><span style="width:${Math.min(100,w.reduce((a,b)=>a+b,0)/3*100)}%"></span></div></div><div class="ild-goal"><div class="ild-goal-top"><b>לשמור על שליטה 90+</b><span>${mastery}%</span></div><div class="ild-progressbar"><span style="width:${mastery}%"></span></div></div><div class="ild-goal"><div class="ild-goal-top"><b>שיעורים בתהליך</b><span>${inprog}</span></div><div class="ild-progressbar"><span style="width:${total?Math.min(100,inprog/total*100):0}%"></span></div></div></div></section>
          <section class="ild-card ild-panel"><h3>📋 הצעדים הבאים</h3><div class="ild-steps"><div class="ild-step"><div class="ild-step-num">1</div><div><b>המשך את השיעור הנוכחי</b><div class="ild-muted">${esc(activeMeta?.lesson_name||'בחר שיעור חדש')}</div></div></div><div class="ild-step"><div class="ild-step-num">2</div><div><b>סיים שיעורי בית פתוחים</b><div class="ild-muted">${homeworks.filter(x=>x.status!=='completed').length} משימות פתוחות</div></div></div><div class="ild-step"><div class="ild-step-num">3</div><div><b>חזק מקצוע חלש</b><div class="ild-muted">המערכת תציע את הנושא הבא לפי ההתקדמות</div></div></div></div></section>
          <section class="ild-card ild-panel"><h3>📚 המקצועות שלי</h3><div class="ild-subjects">${subjectHtml}${customs.length?`<div class="ild-muted" style="margin-top:8px">מערכת אישית: ${customs.map(x=>esc(x.subject_name)).join(' · ')}</div>`:''}</div></section>
        </div>
      </div>`;
      el.querySelector('.ild-close')?.addEventListener('click',close);el.querySelectorAll('[data-dashboard-home]').forEach(b=>b.addEventListener('click',()=>{close();document.getElementById('homeSidebarBtn')?.click()}));
    }catch(e){console.error('LEARNING DASHBOARD LOAD',e);el.innerHTML='<div class="ild-shell"><button class="ild-close">חזרה</button><div style="padding:40px">לא הצלחנו לטעון את הדשבורד כרגע.</div></div>';el.querySelector('.ild-close')?.addEventListener('click',close)}
  }
  document.addEventListener('DOMContentLoaded',()=>setTimeout(ensureButton,700),{once:true});if(document.readyState!=='loading')setTimeout(ensureButton,700);
  document.addEventListener('click',e=>{const btn=e.target?.closest?.('#iakidsDashboardSidebarBtn');if(!btn)return;e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();document.querySelectorAll('.kid-actions .side-item').forEach(x=>x.classList.remove('active'));btn.classList.add('active');open()},true);
  window.openLearningDashboard=open;window.closeLearningDashboard=close;
})();
</script>
'''
    s=s.replace('</body>',block+'\n</body>',1)
s=re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+','IAKIDS • build 0.7.44',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";','window.IAKIDS_BUILD_VERSION = "0.7.44";',s,count=1)
p.write_text(s,encoding='utf-8')
print('learning dashboard added; build 0.7.44')
