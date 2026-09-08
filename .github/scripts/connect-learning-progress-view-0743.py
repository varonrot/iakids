from pathlib import Path
import re

p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')

# Remove the temporary 0.7.42 progress route block that opened achievements.
s=re.sub(r'\n*<script id="IAKIDS_WORKSPACE_PROGRESS_ROUTE_0742">.*?</script>\n*', '\n', s, flags=re.S)

MARK='IAKIDS_LEARNING_PROGRESS_VIEW_0743'
if MARK not in s:
    block=r'''
<style id="iakidsLearningProgressStyles">
  .iakids-learning-progress-view{position:absolute;inset:16px;z-index:245;overflow:auto;direction:rtl;border:1px solid rgba(69,149,236,.28);border-radius:26px;background:radial-gradient(circle at 14% 5%,rgba(52,111,255,.17),transparent 30%),radial-gradient(circle at 90% 8%,rgba(44,216,231,.11),transparent 27%),linear-gradient(180deg,#07162f,#041022);color:#eef6ff;box-shadow:0 24px 70px rgba(0,0,0,.38)}
  .iakids-learning-progress-view[hidden]{display:none!important}
  .ilp-shell{max-width:1220px;margin:0 auto;padding:24px}
  .ilp-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:20px}
  .ilp-title{display:flex;align-items:center;gap:13px}.ilp-icon{width:54px;height:54px;border-radius:18px;display:grid;place-items:center;background:linear-gradient(135deg,#337cff,#31d2e8);font-size:23px}.ilp-title h1{margin:0;font-size:29px;font-weight:950}.ilp-title p{margin:4px 0 0;color:#8da6c8;font-size:13px;font-weight:700}
  .ilp-close{height:42px;padding:0 15px;border-radius:13px;border:1px solid rgba(92,151,225,.28);background:rgba(17,42,77,.82);color:#e2efff;font-weight:900;cursor:pointer}
  .ilp-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:18px}.ilp-summary-card{padding:16px;border-radius:18px;border:1px solid rgba(73,137,210,.22);background:linear-gradient(180deg,rgba(17,43,78,.93),rgba(9,27,54,.94))}.ilp-summary-card strong{display:block;font-size:27px;font-weight:950}.ilp-summary-card span{display:block;margin-top:6px;color:#8fa8c9;font-size:12px;font-weight:800}
  .ilp-section{margin-top:14px}.ilp-section h2{margin:0 0 12px;font-size:18px;font-weight:950}.ilp-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.ilp-card{padding:16px;border:1px solid rgba(72,133,203,.23);border-radius:18px;background:linear-gradient(180deg,rgba(15,38,72,.92),rgba(8,24,49,.94));min-height:128px}.ilp-card-top{display:flex;justify-content:space-between;align-items:center;gap:10px}.ilp-card-title{font-size:17px;font-weight:950}.ilp-card-pct{font-size:21px;font-weight:950;color:#6cddff}.ilp-meta{margin-top:8px;color:#8da5c6;font-size:12px;font-weight:700}.ilp-bar{height:8px;margin-top:14px;border-radius:999px;background:rgba(102,132,173,.16);overflow:hidden}.ilp-bar>span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#3d74ff,#38d8e6)}.ilp-card.complete .ilp-bar>span{background:linear-gradient(90deg,#31cb70,#66eb8e)}.ilp-card.complete .ilp-card-pct{color:#65e78d}.ilp-empty{padding:26px;text-align:center;color:#8399b9;font-weight:750}
  @media(max-width:1050px){.ilp-summary{grid-template-columns:repeat(2,1fr)}.ilp-grid{grid-template-columns:repeat(2,1fr)}}
  @media(max-width:700px){.ilp-grid{grid-template-columns:1fr}.ilp-shell{padding:15px}}
</style>
<script id="IAKIDS_LEARNING_PROGRESS_VIEW_0743">
(function(){
  let view=null;
  function client(){try{if(typeof sb!=='undefined'&&sb?.from)return sb}catch(e){}return window.sb?.from?window.sb:(window.supabaseClient?.from?window.supabaseClient:null)}
  function kid(){try{if(typeof CURRENT_KID!=='undefined'&&CURRENT_KID?.id)return CURRENT_KID}catch(e){}return window.CURRENT_KID||window.SELECTED_KID||window.currentKid||null}
  function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}
  function clamp(v){return Math.max(0,Math.min(100,Math.round(Number(v)||0)))}
  function ensure(){if(view?.isConnected)return view;const main=document.querySelector('.main');if(!main)return null;main.style.position='relative';view=document.createElement('section');view.id='iakidsLearningProgressView';view.className='iakids-learning-progress-view';view.hidden=true;main.appendChild(view);return view}
  function close(){const el=ensure();if(el)el.hidden=true;document.querySelectorAll('.kid-actions .side-item').forEach(x=>{if((x.textContent||'').includes('התקדמות'))x.classList.remove('active')})}
  function groupDefault(rows){const map=new Map();(rows||[]).forEach(r=>{const subject=String(r.learning_lessons?.subject||'').trim();if(!subject)return;if(!map.has(subject))map.set(subject,{name:subject,total:0,completed:0,progress:0,mastery:0});const x=map.get(subject);x.total++;if(r.status==='completed')x.completed++;x.progress+=Number(r.progress_percent||0);x.mastery+=Number(r.mastery_score||0)});return [...map.values()].map(x=>({...x,progress:x.total?Math.round(x.progress/x.total):0,mastery:x.total?Math.round(x.mastery/x.total):0}))}
  function groupCustom(subjects,lessons){return (subjects||[]).map(s=>{const ls=(lessons||[]).filter(l=>String(l.custom_subject_id)===String(s.id)&&String(l.status)!=='archived');const completed=ls.filter(l=>l.status==='completed').length;const active=ls.filter(l=>l.status==='active').length;return{name:s.subject_name,total:ls.length,completed,progress:ls.length?Math.round(completed/ls.length*100):0,mastery:null,active,personal:true}})}
  function cards(rows){if(!rows.length)return '<div class="ilp-empty">עדיין אין נתוני התקדמות להצגה.</div>';return `<div class="ilp-grid">${rows.map(x=>`<div class="ilp-card ${x.progress>=100?'complete':''}"><div class="ilp-card-top"><span class="ilp-card-title">${esc(x.name)}</span><span class="ilp-card-pct">${clamp(x.progress)}%</span></div><div class="ilp-meta">${x.completed}/${x.total} שיעורים הושלמו${x.mastery===null?'':` · ${clamp(x.mastery)}% שליטה`}</div><div class="ilp-bar"><span style="width:${clamp(x.progress)}%"></span></div></div>`).join('')}</div>`}
  async function open(){const el=ensure(),c=client(),k=kid();if(!el)return;el.hidden=false;el.innerHTML='<div class="ilp-empty">טוענים את ההתקדמות שלך...</div>';if(!c||!k?.id){el.innerHTML='<div class="ilp-empty">לא הצלחתי לזהות את פרופיל הילד/ה.</div>';return}
    try{
      const [pRes,sRes,lRes]=await Promise.all([
        c.from('kid_lesson_progress').select('status,progress_percent,mastery_score,lesson_id,learning_lessons(subject,lesson_name)').eq('kid_id',k.id),
        c.from('kid_custom_subjects').select('id,subject_name,status').eq('kid_id',k.id).eq('status','active'),
        c.from('kid_custom_lessons').select('id,custom_subject_id,status').eq('kid_id',k.id).neq('status','archived')
      ]);
      const defaults=pRes.error?[]:groupDefault(pRes.data||[]);const customs=groupCustom(sRes.error?[]:(sRes.data||[]),lRes.error?[]:(lRes.data||[]));const all=[...defaults,...customs];const total=all.reduce((a,x)=>a+x.total,0),done=all.reduce((a,x)=>a+x.completed,0),overall=total?Math.round(done/total*100):0,activeSubjects=all.filter(x=>x.total>0).length;
      el.innerHTML=`<div class="ilp-shell"><div class="ilp-head"><div class="ilp-title"><div class="ilp-icon"><i class="fa-solid fa-chart-line"></i></div><div><h1>ההתקדמות שלי</h1><p>התקדמות אמיתית במקצועות של עולם הלמידה</p></div></div><button class="ilp-close" type="button">חזרה</button></div><div class="ilp-summary"><div class="ilp-summary-card"><strong>${overall}%</strong><span>התקדמות כוללת</span></div><div class="ilp-summary-card"><strong>${done}</strong><span>שיעורים שהושלמו</span></div><div class="ilp-summary-card"><strong>${Math.max(0,total-done)}</strong><span>שיעורים שנותרו</span></div><div class="ilp-summary-card"><strong>${activeSubjects}</strong><span>מקצועות פעילים</span></div></div><div class="ilp-section"><h2>מקצועות הליבה</h2>${cards(defaults)}</div>${customs.length?`<div class="ilp-section"><h2>המערכת האישית שלי</h2>${cards(customs)}</div>`:''}</div>`;
      el.querySelector('.ilp-close')?.addEventListener('click',close)
    }catch(e){console.error('LEARNING PROGRESS LOAD FAILED',e);el.innerHTML='<div class="ilp-empty">לא הצלחנו לטעון את ההתקדמות כרגע.</div>'}
  }
  document.addEventListener('click',function(event){const item=event.target?.closest?.('.kid-actions .side-item');if(!item)return;const text=String(item.textContent||'').replace(/\s+/g,' ').trim();if(!text.includes('התקדמות'))return;event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();document.querySelectorAll('.kid-actions .side-item').forEach(x=>x.classList.remove('active'));item.classList.add('active');if(typeof window.closeWorkspaceAchievements==='function')window.closeWorkspaceAchievements();open()},true);
  window.openLearningProgress=open;window.closeLearningProgress=close;
})();
</script>
'''
    s=s.replace('</body>',block+'\n</body>',1)

s=re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+','IAKIDS • build 0.7.43',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";','window.IAKIDS_BUILD_VERSION = "0.7.43";',s,count=1)
p.write_text(s,encoding='utf-8')
print('Learning progress view connected to workspace; build 0.7.43')
