from pathlib import Path
import re

p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
MARK='IAKIDS_CHILD_KINGDOM_STATS_0755'
if MARK in s:
    print('already applied')
    raise SystemExit(0)

block=r'''
<style id="IAKIDS_CHILD_KINGDOM_STATS_0755_STYLES">
  .kingdom-status-card[data-iakids-live="1"]{transition:border-color .2s ease,box-shadow .2s ease}
  .kingdom-status-ai-live[data-active="1"]{border-color:rgba(61,221,183,.34)!important;box-shadow:0 0 24px rgba(37,190,155,.08)!important}
  .kingdom-status-ai-live[data-active="0"] .kingdom-ai-live-dot{background:#62748d!important;box-shadow:none!important}
  .kingdom-streak-day.iakids-day-active{opacity:1!important;filter:none!important}
  .kingdom-streak-day.iakids-day-inactive{opacity:.36!important;filter:saturate(.45)!important}
</style>
<script id="IAKIDS_CHILD_KINGDOM_STATS_0755">
(function(){
  if(window.__IAKIDS_CHILD_KINGDOM_STATS_0755) return;
  window.__IAKIDS_CHILD_KINGDOM_STATS_0755=true;

  function client(){
    try{ if(typeof sb!=='undefined' && sb?.from) return sb; }catch(_e){}
    return window.sb?.from ? window.sb : (window.supabaseClient?.from ? window.supabaseClient : null);
  }
  function kid(){
    try{ if(typeof CURRENT_KID!=='undefined' && CURRENT_KID?.id) return CURRENT_KID; }catch(_e){}
    return window.CURRENT_KID || window.SELECTED_KID || window.currentKid || window.selectedKid || null;
  }
  function clamp(n,min=0,max=100){return Math.max(min,Math.min(max,Number(n)||0))}
  function heSubject(v){
    const x=String(v||'').trim();
    const map={math:'מתמטיקה',mathematics:'מתמטיקה',science:'מדעים',english:'אנגלית',hebrew:'עברית',bible:'תנ״ך',history:'היסטוריה',geography:'גאוגרפיה'};
    return map[x.toLowerCase()]||x||'הלמידה';
  }
  function dayKey(v){
    const d=new Date(v); if(Number.isNaN(d.getTime())) return null;
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  }
  function daysAgoKey(n){const d=new Date();d.setHours(0,0,0,0);d.setDate(d.getDate()-n);return dayKey(d)}
  function formatLast(v){
    if(!v) return 'עדיין אין פעילות';
    const d=new Date(v), now=new Date();
    const mins=Math.max(0,Math.floor((now-d)/60000));
    if(mins<2) return 'פעילה עכשיו';
    if(mins<60) return `פעילות לפני ${mins} דקות`;
    if(dayKey(d)===dayKey(now)) return `פעילות היום ב-${d.toLocaleTimeString('he-IL',{hour:'2-digit',minute:'2-digit'})}`;
    if(dayKey(d)===daysAgoKey(1)) return 'פעילות אתמול';
    return `פעילות ב-${d.toLocaleDateString('he-IL')}`;
  }

  async function load(){
    const c=client(), k=kid();
    if(!c||!k?.id) return;
    try{
      const [lpRes, hwRes, histRes, customRes] = await Promise.all([
        c.from('kid_lesson_progress').select('lesson_id,status,progress_percent,mastery_score,last_activity_at,updated_at').eq('kid_id',k.id).order('last_activity_at',{ascending:false}),
        c.from('homework_sessions').select('status,last_activity_at,started_at,completed_at').eq('kid_id',k.id).order('last_activity_at',{ascending:false}).limit(100),
        c.from('kid_lesson_history').select('created_at').eq('kid_id',k.id).order('created_at',{ascending:false}).limit(500),
        c.from('kid_custom_lessons').select('status,updated_at').eq('kid_id',k.id).neq('status','archived')
      ]);

      const lessons=lpRes.error?[]:(lpRes.data||[]);
      const homeworks=hwRes.error?[]:(hwRes.data||[]);
      const history=histRes.error?[]:(histRes.data||[]);
      const customs=customRes.error?[]:(customRes.data||[]);

      const lessonIds=[...new Set(lessons.map(x=>x.lesson_id).filter(Boolean))];
      let lessonMeta=[];
      if(lessonIds.length){
        const mr=await c.from('learning_lessons').select('id,subject,lesson_name,category').in('id',lessonIds);
        if(!mr.error) lessonMeta=mr.data||[];
      }
      const metaMap=new Map(lessonMeta.map(x=>[String(x.id),x]));

      const completedLesson=lessons.filter(x=>x.status==='completed').length;
      const activeLesson=lessons.filter(x=>x.status==='in_progress'||x.status==='partial').length;
      const completedCustom=customs.filter(x=>x.status==='completed').length;
      const activeCustom=customs.filter(x=>x.status==='active'||x.status==='ready').length;
      const completed=completedLesson+completedCustom;
      const inProgress=activeLesson+activeCustom;
      const totalTracked=Math.max(lessons.length+customs.length,completed+inProgress);

      let overall=0;
      if(totalTracked){
        const standardProgress=lessons.reduce((sum,x)=>sum+clamp(x.progress_percent),0);
        const customProgress=customs.reduce((sum,x)=>sum+(x.status==='completed'?100:(x.status==='active'?50:0)),0);
        overall=Math.round((standardProgress+customProgress)/totalTracked);
      }

      document.querySelectorAll('.kingdom-status-overall').forEach(card=>{
        card.dataset.iakidsLive='1';
        const ring=card.querySelector('.kingdom-status-ring-inner strong'); if(ring) ring.textContent=`${overall}%`;
        const accent=card.querySelector('.kingdom-status-accent'); if(accent) accent.textContent=`${overall}%`;
        const ringWrap=card.querySelector('.kingdom-status-ring'); if(ringWrap) ringWrap.style.setProperty('--progress',String(overall));
        const meta=[...card.querySelectorAll('.kingdom-status-meta span')];
        if(meta[0]) meta[0].innerHTML=`<b>${completed}</b> שיעורים הושלמו`;
        if(meta[1]) meta[1].innerHTML=`<b>${inProgress}</b> בתהליך`;
      });

      const active=lessons.find(x=>x.status==='in_progress'||x.status==='partial')||lessons.find(x=>x.status!=='completed')||lessons[0];
      const activeMeta=active?metaMap.get(String(active.lesson_id)):null;
      const subject=heSubject(activeMeta?.subject);
      const target=5;
      const sameSubjectDone=lessons.filter(x=>x.status==='completed' && heSubject(metaMap.get(String(x.lesson_id))?.subject)===subject).length;
      const goalDone=Math.min(target,sameSubjectDone);
      const goalPct=Math.round(goalDone/target*100);
      document.querySelectorAll('.kingdom-status-goal').forEach(card=>{
        card.dataset.iakidsLive='1';
        const title=card.querySelector('.kingdom-goal-copy strong');
        if(title) title.textContent=`להשלים ${target} שיעורים ב${subject}`;
        const count=card.querySelector('.kingdom-goal-count'); if(count) count.textContent=`${goalDone}/${target}`;
        const fill=card.querySelector('.kingdom-goal-progress span'); if(fill) fill.style.width=`${goalPct}%`;
      });

      const activityDates=[];
      lessons.forEach(x=>activityDates.push(x.last_activity_at||x.updated_at));
      homeworks.forEach(x=>activityDates.push(x.last_activity_at||x.started_at||x.completed_at));
      history.forEach(x=>activityDates.push(x.created_at));
      const validDates=activityDates.filter(Boolean).map(x=>new Date(x)).filter(d=>!Number.isNaN(d.getTime()));
      validDates.sort((a,b)=>b-a);
      const lastActivity=validDates[0]||null;
      const activeNow=lastActivity ? (Date.now()-lastActivity.getTime()) <= 30*60*1000 : false;
      const activeKeys=new Set(validDates.map(dayKey).filter(Boolean));

      let streak=0;
      let startOffset=activeKeys.has(daysAgoKey(0))?0:(activeKeys.has(daysAgoKey(1))?1:null);
      if(startOffset!==null){
        for(let i=startOffset;i<90;i++){
          if(activeKeys.has(daysAgoKey(i))) streak++;
          else break;
        }
      }
      document.querySelectorAll('.kingdom-status-streak').forEach(card=>{
        card.dataset.iakidsLive='1';
        const num=card.querySelector('.kingdom-streak-number');
        if(num) num.innerHTML=`${streak}<small>ימים</small>`;
        const dayEls=[...card.querySelectorAll('.kingdom-streak-day')];
        dayEls.forEach((el,i)=>{
          const offset=Math.max(0,dayEls.length-1-i);
          const on=activeKeys.has(daysAgoKey(offset));
          el.classList.toggle('iakids-day-active',on);
          el.classList.toggle('iakids-day-inactive',!on);
        });
      });

      const dailyCounts=[];
      for(let i=6;i>=0;i--){dailyCounts.push(validDates.filter(d=>dayKey(d)===daysAgoKey(i)).length)}
      const maxCount=Math.max(1,...dailyCounts);
      document.querySelectorAll('.kingdom-status-ai-live').forEach(card=>{
        card.dataset.iakidsLive='1'; card.dataset.active=activeNow?'1':'0';
        const title=card.querySelector('.kingdom-ai-live-title'); if(title) title.textContent=activeNow?'פעילות AI בזמן אמת':'פעילות הלמידה האחרונה';
        const sub=card.querySelector('.kingdom-ai-live-sub'); if(sub) sub.textContent=formatLast(lastActivity);
        const bars=[...card.querySelectorAll('.kingdom-ai-live-bar')];
        bars.forEach((bar,i)=>{
          const v=dailyCounts[Math.max(0,dailyCounts.length-bars.length+i)]||0;
          const h=v?Math.max(18,Math.round(v/maxCount*92)):10;
          bar.style.setProperty('--h',`${h}%`);
        });
      });

      window.IAKIDS_CHILD_KINGDOM_STATS={overall,completed,inProgress,streak,subject,lastActivity:lastActivity?.toISOString()||null};
    }catch(e){console.warn('CHILD KINGDOM STATS',e)}
  }

  window.refreshChildKingdomStats=load;
  document.addEventListener('DOMContentLoaded',()=>setTimeout(load,1200),{once:true});
  if(document.readyState!=='loading') setTimeout(load,1200);
  document.addEventListener('click',e=>{
    const t=(e.target?.textContent||'').trim();
    if(t.includes('דף הבית')) setTimeout(load,450);
  },false);
  setInterval(()=>{ if(document.visibilityState==='visible') load(); },60000);
})();
</script>
'''

if '</body>' not in s:
    raise SystemExit('body end not found')
s=s.replace('</body>',block+'\n</body>',1)
s=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.55',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.55";',s,count=1)
p.write_text(s,encoding='utf-8')
print('connected child kingdom stats; build 0.7.55')
