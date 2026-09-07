from pathlib import Path
import re

index = Path('he/workspace/index.html')
text = index.read_text(encoding='utf-8')
marker = 'IAKIDS MY LESSONS DASHBOARD 0.7.46'

if marker not in text:
    block = r'''
<style id="iakidsMyLessonsDashboardStyles">
/* IAKIDS MY LESSONS DASHBOARD 0.7.46 */
.iakids-my-lessons-overlay{
  position:fixed;
  top:78px;
  left:248px;
  right:300px;
  bottom:16px;
  z-index:2600;
  display:flex;
  flex-direction:column;
  overflow:hidden;
  direction:rtl;
  color:#eef6ff;
  border:1px solid rgba(81,151,255,.34);
  border-radius:24px;
  background:
    radial-gradient(circle at 52% 0%,rgba(65,86,225,.20),transparent 34%),
    linear-gradient(180deg,rgba(5,20,43,.995),rgba(3,13,31,.995));
  box-shadow:0 24px 70px rgba(0,0,0,.48), inset 0 0 0 1px rgba(116,176,255,.04);
}
.iakids-my-lessons-head{
  display:flex;align-items:center;justify-content:space-between;gap:18px;
  padding:22px 24px 18px;border-bottom:1px solid rgba(75,133,204,.22);
}
.iakids-my-lessons-title h2{margin:0;font-size:26px;font-weight:900;color:#fff}
.iakids-my-lessons-title p{margin:5px 0 0;color:#91a9ca;font-size:13px;font-weight:650}
.iakids-my-lessons-close{
  width:42px;height:42px;border-radius:13px;border:1px solid rgba(94,161,255,.35);
  background:rgba(14,43,81,.72);color:#dcecff;cursor:pointer;font-size:20px
}
.iakids-my-lessons-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding:16px 24px 10px}
.iakids-my-lessons-stat{padding:14px 16px;border:1px solid rgba(73,136,220,.24);border-radius:16px;background:linear-gradient(180deg,rgba(13,43,79,.82),rgba(7,27,55,.86));}
.iakids-my-lessons-stat span{display:block;color:#89a5c8;font-size:11px;font-weight:800}
.iakids-my-lessons-stat strong{display:block;margin-top:4px;color:#fff;font-size:24px;font-weight:900}
.iakids-my-lessons-filters{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:6px 24px 14px}
.iakids-my-lessons-filter{height:38px;padding:0 13px;border-radius:11px;border:1px solid rgba(76,143,232,.28);background:#0a2446;color:#dcecff;font-weight:800;outline:none}
.iakids-my-lessons-list{flex:1;overflow:auto;padding:0 24px 24px}
.iakids-my-lessons-day{margin-top:16px}
.iakids-my-lessons-day-title{display:flex;align-items:center;gap:9px;margin-bottom:9px;color:#aac2e2;font-size:13px;font-weight:900}
.iakids-my-lessons-day-title:after{content:"";height:1px;flex:1;background:linear-gradient(90deg,rgba(75,140,220,.25),transparent)}
.iakids-my-lessons-card{display:grid;grid-template-columns:minmax(150px,1.25fr) minmax(120px,.9fr) minmax(120px,.85fr) minmax(120px,.8fr);gap:12px;align-items:center;margin-bottom:9px;padding:13px 15px;border:1px solid rgba(72,135,216,.22);border-radius:15px;background:linear-gradient(180deg,rgba(10,34,65,.92),rgba(6,24,48,.94))}
.iakids-my-lessons-card:hover{border-color:rgba(88,171,255,.46);transform:translateY(-1px)}
.iakids-my-lessons-main strong{display:block;color:#fff;font-size:14px;font-weight:900}
.iakids-my-lessons-main small,.iakids-my-lessons-cell small{display:block;color:#7f99bd;font-size:10px;font-weight:750;margin-bottom:3px}
.iakids-my-lessons-cell{color:#d7e8fb;font-size:12px;font-weight:800}
.iakids-my-lessons-progress{height:7px;margin-top:7px;border-radius:999px;background:#07192f;overflow:hidden;border:1px solid rgba(63,116,182,.22)}
.iakids-my-lessons-progress > i{display:block;height:100%;background:linear-gradient(90deg,#6b52ff,#39cef6);border-radius:999px}
.iakids-my-lessons-status{display:inline-flex;align-items:center;justify-content:center;min-width:88px;height:30px;padding:0 10px;border-radius:999px;font-size:11px;font-weight:900}
.iakids-my-lessons-status.completed{color:#8dffc1;border:1px solid rgba(56,220,125,.35);background:rgba(32,145,83,.18)}
.iakids-my-lessons-status.in_progress{color:#ffd58a;border:1px solid rgba(255,183,70,.34);background:rgba(180,113,24,.16)}
.iakids-my-lessons-status.abandoned{color:#ffadad;border:1px solid rgba(255,99,99,.30);background:rgba(170,47,47,.14)}
.iakids-my-lessons-empty,.iakids-my-lessons-loading{display:grid;place-items:center;min-height:280px;text-align:center;color:#9bb4d4;font-weight:800;line-height:1.7}
@media(max-width:1180px){.iakids-my-lessons-overlay{left:16px;right:16px}.iakids-my-lessons-card{grid-template-columns:1fr 1fr}.iakids-my-lessons-stats{grid-template-columns:1fr 1fr}}
</style>
<script id="iakidsMyLessonsDashboardScript">
(function(){
  const MARKER = "IAKIDS MY LESSONS DASHBOARD 0.7.46";
  if(window.__IAKIDS_MY_LESSONS_DASHBOARD_0746) return;
  window.__IAKIDS_MY_LESSONS_DASHBOARD_0746 = true;

  let rows = [];
  let subjectFilter = "all";
  let statusFilter = "all";

  function getClient(){
    try{
      if(typeof sb !== "undefined" && sb?.from) return sb;
      if(window.sb?.from) return window.sb;
      if(window.supabaseClient?.from) return window.supabaseClient;
    }catch(e){}
    return null;
  }

  function getKid(){
    try{
      if(typeof CURRENT_KID !== "undefined" && CURRENT_KID) return CURRENT_KID;
    }catch(e){}
    return window.CURRENT_KID || window.currentKid || null;
  }

  function esc(value){
    return String(value ?? "").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch]));
  }

  function dateKey(value){
    const d = new Date(value || Date.now());
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
  }

  function dateLabel(value){
    const d = new Date(value || Date.now());
    const today = new Date();
    const yesterday = new Date(); yesterday.setDate(today.getDate()-1);
    if(dateKey(d) === dateKey(today)) return "היום";
    if(dateKey(d) === dateKey(yesterday)) return "אתמול";
    return d.toLocaleDateString("he-IL",{weekday:"long",day:"numeric",month:"long",year:"numeric"});
  }

  function statusText(status){
    if(status === "completed") return "הושלם";
    if(status === "abandoned") return "לא הושלם";
    return "בתהליך";
  }

  function filteredRows(){
    return rows.filter(row =>
      (subjectFilter === "all" || (row.subject || "לא זוהה") === subjectFilter) &&
      (statusFilter === "all" || row.status === statusFilter)
    );
  }

  function renderStats(){
    const total = rows.length;
    const completed = rows.filter(r=>r.status === "completed").length;
    const inProgress = rows.filter(r=>r.status === "in_progress").length;
    const percent = total ? Math.round(completed/total*100) : 0;
    const host = document.getElementById("iakidsMyLessonsStats");
    if(!host) return;
    host.innerHTML = `
      <div class="iakids-my-lessons-stat"><span>סה״כ שיעורי בית</span><strong>${total}</strong></div>
      <div class="iakids-my-lessons-stat"><span>הושלמו</span><strong>${completed}</strong></div>
      <div class="iakids-my-lessons-stat"><span>עדיין בתהליך</span><strong>${inProgress}</strong></div>
      <div class="iakids-my-lessons-stat"><span>אחוז השלמה</span><strong>${percent}%</strong></div>`;
  }

  function renderFilters(){
    const subjects = [...new Set(rows.map(r=>r.subject || "לא זוהה"))].sort((a,b)=>a.localeCompare(b,"he"));
    const subject = document.getElementById("iakidsMyLessonsSubject");
    const status = document.getElementById("iakidsMyLessonsStatus");
    if(subject){
      subject.innerHTML = `<option value="all">כל המקצועות</option>` + subjects.map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join("");
      subject.value = subjectFilter;
    }
    if(status) status.value = statusFilter;
  }

  function renderList(){
    const host = document.getElementById("iakidsMyLessonsList");
    if(!host) return;
    const data = filteredRows();
    if(!data.length){
      host.innerHTML = `<div class="iakids-my-lessons-empty">עדיין אין שיעורי בית שמתאימים לסינון הזה.<br>אחרי שתעלי ותפתרי שיעורי בית הם יופיעו כאן.</div>`;
      return;
    }
    const groups = new Map();
    data.forEach(row=>{
      const key = dateKey(row.started_at || row.created_at);
      if(!groups.has(key)) groups.set(key,[]);
      groups.get(key).push(row);
    });
    host.innerHTML = [...groups.entries()].map(([key,items])=>{
      const cards = items.map(row=>{
        const total = Number(row.total_questions || 0);
        const done = Number(row.completed_questions || 0);
        const pct = total ? Math.min(100,Math.round(done/total*100)) : (row.status === "completed" ? 100 : 0);
        const time = new Date(row.started_at || row.created_at).toLocaleTimeString("he-IL",{hour:"2-digit",minute:"2-digit"});
        return `<div class="iakids-my-lessons-card">
          <div class="iakids-my-lessons-main"><small>מקצוע ונושא</small><strong>${esc(row.subject || "לא זוהה")}</strong><div style="color:#9bb4d3;font-size:11px;margin-top:2px">${esc(row.topic || "ללא נושא")}</div></div>
          <div class="iakids-my-lessons-cell"><small>התקדמות</small>${done} מתוך ${total || "?"}<div class="iakids-my-lessons-progress"><i style="width:${pct}%"></i></div></div>
          <div class="iakids-my-lessons-cell"><small>שעה</small>${time}</div>
          <div class="iakids-my-lessons-cell"><small>סטטוס</small><span class="iakids-my-lessons-status ${esc(row.status || "in_progress")}">${statusText(row.status)}</span></div>
        </div>`;
      }).join("");
      return `<section class="iakids-my-lessons-day"><div class="iakids-my-lessons-day-title">${dateLabel(items[0].started_at || items[0].created_at)}</div>${cards}</section>`;
    }).join("");
  }

  function renderAll(){ renderStats(); renderFilters(); renderList(); }

  async function loadRows(){
    const host = document.getElementById("iakidsMyLessonsList");
    if(host) host.innerHTML = `<div class="iakids-my-lessons-loading">טוען את השיעורים שלך...</div>`;
    const client = getClient();
    const kid = getKid();
    const kidId = kid?.id || kid?.kid_id || kid?.uuid || null;
    if(!client){ if(host) host.innerHTML = `<div class="iakids-my-lessons-empty">לא הצלחתי להתחבר לנתוני השיעורים כרגע.</div>`; return; }
    if(!kidId){ if(host) host.innerHTML = `<div class="iakids-my-lessons-empty">לא זוהה פרופיל הילד. חזרו לדף הבית ובחרו ילד.</div>`; return; }
    try{
      const {data,error} = await client
        .from("homework_sessions")
        .select("id,subject,topic,total_questions,completed_questions,status,started_at,last_activity_at,completed_at,created_at")
        .eq("kid_id",kidId)
        .order("started_at",{ascending:false});
      if(error) throw error;
      rows = Array.isArray(data) ? data : [];
      renderAll();
    }catch(error){
      console.error("MY LESSONS LOAD ERROR",error);
      if(host) host.innerHTML = `<div class="iakids-my-lessons-empty">לא הצלחתי לטעון את השיעורים כרגע.<br>אפשר לנסות שוב בעוד רגע.</div>`;
    }
  }

  function closeDashboard(){
    document.getElementById("iakidsMyLessonsOverlay")?.remove();
    document.querySelectorAll(".side-item").forEach(el=>el.classList.remove("active-my-lessons"));
  }

  function openDashboard(){
    closeDashboard();
    const kid = getKid();
    const kidName = kid?.child_name || kid?.name || "";
    const overlay = document.createElement("div");
    overlay.id = "iakidsMyLessonsOverlay";
    overlay.className = "iakids-my-lessons-overlay";
    overlay.innerHTML = `
      <div class="iakids-my-lessons-head">
        <div class="iakids-my-lessons-title"><h2>השיעורים שלי</h2><p>${kidName ? `כל שיעורי הבית של ${esc(kidName)} לפי ימים, מקצועות והתקדמות` : "כל שיעורי הבית לפי ימים, מקצועות והתקדמות"}</p></div>
        <button class="iakids-my-lessons-close" type="button" aria-label="סגירה">×</button>
      </div>
      <div id="iakidsMyLessonsStats" class="iakids-my-lessons-stats"></div>
      <div class="iakids-my-lessons-filters">
        <select id="iakidsMyLessonsSubject" class="iakids-my-lessons-filter"><option value="all">כל המקצועות</option></select>
        <select id="iakidsMyLessonsStatus" class="iakids-my-lessons-filter"><option value="all">כל הסטטוסים</option><option value="completed">הושלם</option><option value="in_progress">בתהליך</option><option value="abandoned">לא הושלם</option></select>
      </div>
      <div id="iakidsMyLessonsList" class="iakids-my-lessons-list"></div>`;
    document.body.appendChild(overlay);
    overlay.querySelector(".iakids-my-lessons-close")?.addEventListener("click",closeDashboard);
    overlay.querySelector("#iakidsMyLessonsSubject")?.addEventListener("change",e=>{subjectFilter=e.target.value;renderList();});
    overlay.querySelector("#iakidsMyLessonsStatus")?.addEventListener("change",e=>{statusFilter=e.target.value;renderList();});
    loadRows();
  }

  document.addEventListener("click",function(event){
    const item = event.target?.closest?.("button,.side-item,[role='button']");
    if(!item) return;
    const label = String(item.textContent || "").replace(/\s+/g," ").trim();
    if(!label.includes("השיעורים שלי")) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    openDashboard();
  },true);

  window.openMyLessonsDashboard = openDashboard;
  window.closeMyLessonsDashboard = closeDashboard;
  console.log(MARKER,"READY");
})();
</script>
'''
    text = text.replace('</body>', block + '\n</body>', 1)

text = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.46', text, count=1)
index.write_text(text, encoding='utf-8')
print('Added My Lessons dashboard and wired sidebar button; build 0.7.46')
