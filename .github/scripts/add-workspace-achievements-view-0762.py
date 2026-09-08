from pathlib import Path
import re

INDEX = Path('he/workspace/index.html')
LOADER = Path('he/workspace/lesson-completion.js')

index = INDEX.read_text(encoding='utf-8')
loader = LOADER.read_text(encoding='utf-8')

MARKER = 'IAKIDS_WORKSPACE_ACHIEVEMENTS_0762'

if MARKER not in index:
    injection = r'''
<style id="iakidsWorkspaceAchievementsStyles">
  .main{position:relative!important;}
  .iakids-achievements-view{
    position:absolute;inset:16px;z-index:240;
    overflow:auto;direction:rtl;
    border:1px solid rgba(72,145,235,.26);
    border-radius:26px;
    background:
      radial-gradient(circle at 15% 4%,rgba(82,95,255,.18),transparent 32%),
      radial-gradient(circle at 90% 10%,rgba(35,177,255,.13),transparent 28%),
      linear-gradient(180deg,#07162f 0%,#041022 100%);
    box-shadow:0 24px 70px rgba(0,0,0,.38), inset 0 0 0 1px rgba(117,81,255,.04);
    color:#eef5ff;
    font-family:"Heebo",Arial,sans-serif;
  }
  .iakids-achievements-view[hidden]{display:none!important;}
  .iav-shell{padding:24px;max-width:1240px;margin:0 auto;}
  .iav-head{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:20px;}
  .iav-title-wrap{display:flex;align-items:center;gap:14px;}
  .iav-title-icon{width:56px;height:56px;border-radius:18px;display:grid;place-items:center;
    background:linear-gradient(135deg,#6b4bff,#1c89dc);color:#fff;font-size:24px;box-shadow:0 9px 26px rgba(61,92,255,.25)}
  .iav-head h1{margin:0;font-size:28px;font-weight:950;}
  .iav-head p{margin:4px 0 0;color:#8fa6c8;font-size:13px;font-weight:650;}
  .iav-close{height:42px;padding:0 15px;border-radius:13px;border:1px solid rgba(94,148,222,.26);
    background:rgba(18,43,78,.76);color:#d9e8fb;font-weight:900;cursor:pointer;}
  .iav-close:hover{border-color:rgba(84,190,255,.5);}
  .iav-stats{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-bottom:18px;}
  .iav-stat{min-height:114px;padding:16px;border-radius:19px;border:1px solid rgba(76,137,214,.22);
    background:linear-gradient(180deg,rgba(17,42,76,.92),rgba(10,27,54,.92));box-shadow:0 10px 24px rgba(0,0,0,.16)}
  .iav-stat-icon{width:36px;height:36px;border-radius:12px;display:grid;place-items:center;margin-bottom:10px;
    background:rgba(64,111,201,.22);color:#74d8ff;}
  .iav-stat strong{display:block;font-size:26px;line-height:1;font-weight:950;color:#fff;}
  .iav-stat span{display:block;margin-top:7px;color:#8fa7c8;font-size:12px;font-weight:750;}
  .iav-grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(280px,.65fr);gap:14px;}
  .iav-card{border:1px solid rgba(75,133,206,.22);border-radius:20px;padding:18px;
    background:linear-gradient(180deg,rgba(14,36,68,.9),rgba(8,23,49,.93));}
  .iav-card h2{margin:0 0 14px;font-size:18px;font-weight:950;}
  .iav-subjects{display:grid;gap:10px;}
  .iav-subject-row{padding:12px 13px;border-radius:14px;background:rgba(14,34,63,.72);border:1px solid rgba(72,124,190,.16);}
  .iav-subject-top{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px;}
  .iav-subject-name{font-weight:900;color:#e8f2ff;}
  .iav-subject-value{font-size:12px;font-weight:900;color:#79d8ff;}
  .iav-bar{height:8px;border-radius:999px;background:rgba(105,132,175,.16);overflow:hidden;}
  .iav-bar>span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#406fff,#42d6e7);}
  .iav-list{display:grid;gap:9px;}
  .iav-list-item{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px;border-radius:14px;
    background:rgba(13,33,61,.72);border:1px solid rgba(75,128,193,.15);}
  .iav-list-item b{font-size:13px;color:#e8f1ff;}.iav-list-item span{font-size:12px;color:#8ca5c7;}
  .iav-empty{padding:20px;text-align:center;color:#8398b7;font-size:13px;font-weight:700;}
  .iav-loading{padding:46px;text-align:center;color:#8eb0db;font-weight:850;}
  .iav-game-note{margin-top:14px;padding:12px 14px;border-radius:14px;border:1px solid rgba(105,78,255,.2);
    background:rgba(63,47,139,.14);color:#aebcf0;font-size:12px;font-weight:700;line-height:1.6;}
  @media(max-width:1000px){.iav-stats{grid-template-columns:repeat(2,minmax(0,1fr));}.iav-grid{grid-template-columns:1fr;}}
</style>
<script id="IAKIDS_WORKSPACE_ACHIEVEMENTS_0762">
(function(){
  let view = null;

  function getClient(){
    try{ if(typeof sb !== 'undefined' && sb?.from) return sb; }catch(_e){}
    return window.sb?.from ? window.sb : (window.supabaseClient?.from ? window.supabaseClient : null);
  }

  function getKid(){
    try{ if(typeof CURRENT_KID !== 'undefined' && CURRENT_KID?.id) return CURRENT_KID; }catch(_e){}
    return window.CURRENT_KID || window.SELECTED_KID || window.currentKid || window.selectedKid || null;
  }

  function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));}

  function ensureView(){
    if(view?.isConnected) return view;
    const main = document.querySelector('.main');
    if(!main) return null;
    view = document.createElement('section');
    view.id = 'iakidsWorkspaceAchievementsView';
    view.className = 'iakids-achievements-view';
    view.hidden = true;
    main.appendChild(view);
    return view;
  }

  function closeView(){
    const el = ensureView();
    if(el) el.hidden = true;
    document.querySelectorAll('.kid-actions .side-item').forEach(x=>{
      const t=(x.textContent||'').trim();
      if(t.includes('הישגים')) x.classList.remove('active');
    });
  }

  function subjectSummary(rows){
    const map = new Map();
    (rows||[]).forEach(r=>{
      const name = String(r.subject || r.subject_name || 'למידה').trim() || 'למידה';
      if(!map.has(name)) map.set(name,{name,count:0,completed:0,progress:0,mastery:0});
      const x=map.get(name); x.count++;
      if(r.status==='completed') x.completed++;
      x.progress += Number(r.progress_percent||0);
      x.mastery += Number(r.mastery_score||0);
    });
    return [...map.values()].map(x=>({
      ...x,
      progress: x.count ? Math.round(x.progress/x.count) : 0,
      mastery: x.count ? Math.round(x.mastery/x.count) : 0
    })).sort((a,b)=>b.progress-a.progress);
  }

  async function loadAchievements(){
    const el = ensureView();
    const client = getClient();
    const kid = getKid();
    if(!el) return;
    if(!client || !kid?.id){
      el.innerHTML='<div class="iav-loading">לא הצלחתי לזהות את פרופיל הילד/ה.</div>';
      return;
    }

    el.hidden = false;
    el.innerHTML='<div class="iav-loading"><i class="fa-solid fa-spinner fa-spin"></i><br>טוענים את ההישגים שלך...</div>';

    try{
      const [lessonRes, homeworkRes, customRes] = await Promise.all([
        client.from('kid_lesson_progress').select('status,progress_percent,mastery_score,xp_earned,stars_earned,total_time_seconds,lesson_id,updated_at').eq('kid_id',kid.id),
        client.from('homework_sessions').select('status,total_questions,completed_questions,subject,topic,started_at').eq('kid_id',kid.id).order('started_at',{ascending:false}).limit(20),
        client.from('kid_custom_subjects').select('id,subject_name,status').eq('kid_id',kid.id).eq('status','active')
      ]);

      if(lessonRes.error) throw lessonRes.error;
      const lessons = lessonRes.data || [];
      const homeworks = homeworkRes.error ? [] : (homeworkRes.data || []);
      const custom = customRes.error ? [] : (customRes.data || []);

      const completed = lessons.filter(r=>r.status==='completed').length;
      const inProgress = lessons.filter(r=>r.status==='in_progress').length;
      const avgMastery = lessons.length ? Math.round(lessons.reduce((s,r)=>s+Number(r.mastery_score||0),0)/lessons.length) : 0;
      const stars = lessons.reduce((s,r)=>s+Number(r.stars_earned||0),0);
      const xp = lessons.reduce((s,r)=>s+Number(r.xp_earned||0),0);
      const hwDone = homeworks.filter(r=>r.status==='completed').length;
      const subjects = subjectSummary(lessons);

      const subjectHtml = subjects.length ? subjects.map(s=>`
        <div class="iav-subject-row">
          <div class="iav-subject-top"><span class="iav-subject-name">${esc(s.name)}</span><span class="iav-subject-value">${s.progress}% התקדמות · ${s.mastery}% שליטה</span></div>
          <div class="iav-bar"><span style="width:${Math.max(0,Math.min(100,s.progress))}%"></span></div>
        </div>`).join('') : '<div class="iav-empty">עדיין אין מספיק נתוני שיעורים להצגת התקדמות לפי מקצוע.</div>';

      const hwHtml = homeworks.length ? homeworks.slice(0,6).map(h=>`
        <div class="iav-list-item"><div><b>${esc(h.subject||'שיעורי בית')}</b><br><span>${esc(h.topic||'')}</span></div><span>${h.status==='completed'?'הושלם':'בתהליך'} · ${Number(h.completed_questions||0)}/${Number(h.total_questions||0)}</span></div>`).join('') : '<div class="iav-empty">עדיין אין שיעורי בית שנשמרו.</div>';

      el.innerHTML = `
        <div class="iav-shell">
          <div class="iav-head">
            <div class="iav-title-wrap"><div class="iav-title-icon"><i class="fa-solid fa-trophy"></i></div><div><h1>ההישגים שלי</h1><p>התקדמות לימודית, שיעורים, שליטה והישגים — בתוך סביבת הלמידה</p></div></div>
            <button type="button" class="iav-close"><i class="fa-solid fa-arrow-right"></i> חזרה</button>
          </div>
          <div class="iav-stats">
            <div class="iav-stat"><div class="iav-stat-icon"><i class="fa-solid fa-circle-check"></i></div><strong>${completed}</strong><span>שיעורים שהושלמו</span></div>
            <div class="iav-stat"><div class="iav-stat-icon"><i class="fa-solid fa-chart-line"></i></div><strong>${avgMastery}%</strong><span>שליטה ממוצעת</span></div>
            <div class="iav-stat"><div class="iav-stat-icon"><i class="fa-solid fa-star"></i></div><strong>${stars}</strong><span>כוכבים מלמידה</span></div>
            <div class="iav-stat"><div class="iav-stat-icon"><i class="fa-solid fa-bolt"></i></div><strong>${xp}</strong><span>XP מלמידה</span></div>
            <div class="iav-stat"><div class="iav-stat-icon"><i class="fa-solid fa-list-check"></i></div><strong>${hwDone}</strong><span>שיעורי בית שהושלמו</span></div>
          </div>
          <div class="iav-grid">
            <div class="iav-card"><h2>התקדמות לפי מקצוע</h2><div class="iav-subjects">${subjectHtml}</div></div>
            <div>
              <div class="iav-card"><h2>שיעורי הבית האחרונים</h2><div class="iav-list">${hwHtml}</div></div>
              <div class="iav-card" style="margin-top:14px"><h2>המערכת האישית שלי</h2><div class="iav-list"><div class="iav-list-item"><b>מקצועות אישיים פעילים</b><span>${custom.length}</span></div><div class="iav-list-item"><b>שיעורים בתהליך</b><span>${inProgress}</span></div></div><div class="iav-game-note">הישגים במשחקים נשארים בעולם המשחקים. כאן מוצגים ההישגים הלימודיים של סביבת הלמידה.</div></div>
            </div>
          </div>
        </div>`;

      el.querySelector('.iav-close')?.addEventListener('click',closeView);
    }catch(error){
      console.error('WORKSPACE ACHIEVEMENTS LOAD FAILED',error);
      el.innerHTML='<div class="iav-shell"><div class="iav-head"><div class="iav-title-wrap"><div class="iav-title-icon"><i class="fa-solid fa-trophy"></i></div><div><h1>ההישגים שלי</h1><p>לא הצלחנו לטעון את הנתונים כרגע.</p></div></div><button type="button" class="iav-close">חזרה</button></div><div class="iav-empty">אפשר לרענן ולנסות שוב.</div></div>';
      el.querySelector('.iav-close')?.addEventListener('click',closeView);
    }
  }

  document.addEventListener('click',event=>{
    const item = event.target?.closest?.('.kid-actions .side-item');
    if(!item) return;
    const text=(item.textContent||'').replace(/\s+/g,' ').trim();
    if(!text.includes('הישגים')) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    document.querySelectorAll('.kid-actions .side-item').forEach(x=>x.classList.remove('active'));
    item.classList.add('active');
    loadAchievements();
  },true);

  window.openWorkspaceAchievements = loadAchievements;
  window.closeWorkspaceAchievements = closeView;
})();
</script>
'''
    if '</body>' not in index:
        raise RuntimeError('body end not found')
    index = index.replace('</body>', injection + '\n</body>', 1)

index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.62', index, count=1)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.62";', index, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0762', index, count=1)
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.62";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0762', loader, count=1)

INDEX.write_text(index,encoding='utf-8')
LOADER.write_text(loader,encoding='utf-8')
print('Workspace achievements view added; build 0.7.62')
