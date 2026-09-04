from pathlib import Path

FILES = [Path('he/workspace/index.html'), Path('he/workspace/index2.html')]

CSS = r'''
/* =====================================================
   STUDENT LESSON PROGRESS PANEL — build 0.6.5
===================================================== */
body.lesson-theme-science .lesson-progress-open-btn{
  width:100%; margin:0 0 8px; padding:8px 10px; border:1px solid rgba(57,171,255,.38);
  border-radius:10px; background:linear-gradient(135deg,rgba(13,91,164,.34),rgba(54,49,160,.30));
  color:#eaf6ff; font:800 11px/1.2 inherit; cursor:pointer; box-shadow:inset 0 1px rgba(255,255,255,.06),0 5px 16px rgba(0,65,150,.14);
}
body.lesson-theme-science .lesson-progress-open-btn:hover{border-color:rgba(86,202,255,.7);transform:translateY(-1px)}
.lesson-student-progress-panel{position:absolute;inset:0;z-index:24;overflow:auto;direction:rtl;padding:28px;background:radial-gradient(circle at 85% 0,rgba(39,124,255,.17),transparent 35%),linear-gradient(180deg,#07172d,#041020);color:#eef6ff}
.lesson-student-progress-shell{max-width:900px;margin:auto}
.lesson-student-progress-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}
.lesson-student-progress-head h2{margin:0;font-size:25px}.lesson-student-progress-close{border:1px solid rgba(132,166,218,.3);border-radius:10px;background:#0b1d39;color:#dceaff;padding:8px 13px;cursor:pointer;font-weight:800}
.lesson-progress-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}.lesson-progress-stat{padding:13px;border:1px solid rgba(94,143,215,.2);border-radius:13px;background:rgba(9,31,61,.78);text-align:center}.lesson-progress-stat strong{display:block;font-size:21px}.lesson-progress-stat span{font-size:10px;color:#9eb2d3}
.lesson-progress-filters{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px}.lesson-progress-filter{border:1px solid rgba(90,133,199,.25);border-radius:999px;background:#0a1d39;color:#aebfda;padding:7px 12px;cursor:pointer;font-weight:800;font-size:11px}.lesson-progress-filter.active{color:white;border-color:#45a9ff;background:#123d72}
.lesson-progress-unit{border:1px solid rgba(83,128,195,.22);border-radius:14px;overflow:hidden;background:rgba(5,20,42,.72)}.lesson-progress-unit-title{padding:12px 15px;border-bottom:1px solid rgba(83,128,195,.18);font-weight:900;color:#dceaff}.lesson-progress-items{max-height:430px;overflow:auto}.lesson-progress-item{display:grid;grid-template-columns:minmax(0,1fr) 105px 105px;align-items:center;gap:12px;padding:12px 15px;border-bottom:1px solid rgba(79,118,178,.13)}.lesson-progress-item:last-child{border-bottom:0}.lesson-progress-item-name{font-weight:800;font-size:13px}.lesson-progress-badge{font-size:10px;font-weight:900;text-align:center;padding:6px 8px;border-radius:999px}.lesson-progress-badge.completed{color:#7df1aa;background:rgba(34,177,92,.14)}.lesson-progress-badge.partial{color:#ffc76c;background:rgba(222,142,31,.14)}.lesson-progress-badge.in_progress{color:#70c9ff;background:rgba(35,146,225,.14)}.lesson-progress-badge.not_started{color:#a8b7ce;background:rgba(130,151,181,.10)}.lesson-progress-action{border:1px solid rgba(79,163,255,.42);border-radius:9px;background:rgba(29,105,196,.23);color:#e8f5ff;padding:7px 8px;cursor:pointer;font-weight:900;font-size:10px}.lesson-progress-empty{padding:30px;text-align:center;color:#9eb0cc}
@media(max-width:760px){.lesson-student-progress-panel{padding:16px}.lesson-progress-summary{grid-template-columns:repeat(2,1fr)}.lesson-progress-item{grid-template-columns:minmax(0,1fr) 90px}.lesson-progress-action{grid-column:1/-1}.lesson-progress-items{max-height:none}}
'''

JS = r'''

/* =====================================================
   STUDENT LESSON PROGRESS PANEL — build 0.6.5
===================================================== */
function ensureLessonProgressButton(){
  const list = document.getElementById("lessonSidebarList");
  if(!list || document.getElementById("lessonProgressOpenBtn")) return;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.id = "lessonProgressOpenBtn";
  btn.className = "lesson-progress-open-btn";
  btn.innerHTML = "📊 ההתקדמות שלי";
  btn.addEventListener("click", openStudentLessonProgressPanel);
  list.parentElement?.insertBefore(btn, list);
}

function startLessonFromProgressPanel(lessonId){
  const lesson = (window.LESSON_SIDEBAR_ROWS || []).find(item => Number(item.id) === Number(lessonId));
  if(!lesson) return;
  const pending = {
    lesson:{...lesson}, parentLesson:{...CURRENT_PARENT_LESSON}, unit:{...CURRENT_UNIT},
    category:SCIENCE_SELECTED_CATEGORY || CURRENT_PARENT_LESSON?.category || null, savedAt:Date.now()
  };
  sessionStorage.setItem("iakids_pending_sidebar_lesson", JSON.stringify(pending));
  window.location.reload();
}

function renderStudentLessonProgressList(filter="all"){
  const host = document.getElementById("lessonProgressItems");
  if(!host) return;
  const rows = window.LESSON_SIDEBAR_ROWS || [];
  const progress = new Map((window.LESSON_SIDEBAR_PROGRESS_ROWS || []).map(r => [Number(r.unit_lesson_id), r]));
  const visible = rows.filter(lesson => {
    const status = String(progress.get(Number(lesson.id))?.status || "not_started");
    if(filter === "all") return true;
    if(filter === "needs_completion") return status === "partial";
    return status === filter;
  });
  if(!visible.length){ host.innerHTML='<div class="lesson-progress-empty">אין שיעורים במצב הזה</div>'; return; }
  const labels={completed:"הושלם",partial:"צריך להשלים",in_progress:"בתהליך",not_started:"טרם התחלת"};
  host.innerHTML=visible.map(lesson=>{
    const p=progress.get(Number(lesson.id)); const status=String(p?.status||"not_started");
    const action=status==="completed"?"פתח שוב":status==="partial"?"השלם שיעור":status==="in_progress"?"חזור לשיעור":"התחל שיעור";
    return `<div class="lesson-progress-item"><div class="lesson-progress-item-name">${escapeLessonSidebarHtml(String(lesson.lesson_order||""))}. ${escapeLessonSidebarHtml(lesson.lesson_name||"")}</div><span class="lesson-progress-badge ${status}">${labels[status]||labels.not_started}</span><button class="lesson-progress-action" type="button" data-progress-lesson-id="${Number(lesson.id)}">${action}</button></div>`;
  }).join("");
  host.querySelectorAll("[data-progress-lesson-id]").forEach(btn=>btn.addEventListener("click",()=>startLessonFromProgressPanel(Number(btn.dataset.progressLessonId))));
}

function openStudentLessonProgressPanel(){
  const stage=document.querySelector(".lesson-visual-stage"); if(!stage) return;
  document.getElementById("studentLessonProgressPanel")?.remove();
  const rows=window.LESSON_SIDEBAR_ROWS||[]; const pmap=new Map((window.LESSON_SIDEBAR_PROGRESS_ROWS||[]).map(r=>[Number(r.unit_lesson_id),r]));
  const counts={completed:0,partial:0,in_progress:0,not_started:0}; rows.forEach(l=>{const s=String(pmap.get(Number(l.id))?.status||"not_started"); counts[s]=(counts[s]||0)+1;});
  const panel=document.createElement("div"); panel.id="studentLessonProgressPanel"; panel.className="lesson-student-progress-panel";
  panel.innerHTML=`<div class="lesson-student-progress-shell"><div class="lesson-student-progress-head"><div><h2>ההתקדמות שלי</h2><small>${escapeLessonSidebarHtml(CURRENT_UNIT?.unit_name||CURRENT_PARENT_LESSON?.lesson_name||"")}</small></div><button class="lesson-student-progress-close" type="button">✕ חזרה לשיעור</button></div><div class="lesson-progress-summary"><div class="lesson-progress-stat"><strong>${rows.length}</strong><span>שיעורים ביחידה</span></div><div class="lesson-progress-stat"><strong>${counts.completed}</strong><span>הושלמו</span></div><div class="lesson-progress-stat"><strong>${counts.partial}</strong><span>צריך להשלים</span></div><div class="lesson-progress-stat"><strong>${counts.in_progress}</strong><span>בתהליך</span></div></div><div class="lesson-progress-filters"><button class="lesson-progress-filter active" data-progress-filter="all">הכול</button><button class="lesson-progress-filter" data-progress-filter="in_progress">בתהליך</button><button class="lesson-progress-filter" data-progress-filter="needs_completion">צריך להשלים</button><button class="lesson-progress-filter" data-progress-filter="completed">הושלמו</button><button class="lesson-progress-filter" data-progress-filter="not_started">טרם התחלת</button></div><section class="lesson-progress-unit"><div class="lesson-progress-unit-title">${escapeLessonSidebarHtml(CURRENT_UNIT?.unit_name||"השיעורים שלי")}</div><div id="lessonProgressItems" class="lesson-progress-items"></div></section></div>`;
  stage.appendChild(panel);
  panel.querySelector(".lesson-student-progress-close")?.addEventListener("click",()=>panel.remove());
  panel.querySelectorAll("[data-progress-filter]").forEach(btn=>btn.addEventListener("click",()=>{panel.querySelectorAll(".lesson-progress-filter").forEach(b=>b.classList.remove("active"));btn.classList.add("active");renderStudentLessonProgressList(btn.dataset.progressFilter);}));
  renderStudentLessonProgressList("all");
}
'''

for p in FILES:
    text=p.read_text(encoding='utf-8')
    if 'STUDENT LESSON PROGRESS PANEL — build 0.6.5' in text:
        continue
    css_marker='/* =====================================================\n   LESSON VISUAL GENERATION\n===================================================== */'
    if css_marker not in text: raise SystemExit(f'CSS marker missing: {p}')
    text=text.replace(css_marker, CSS+'\n'+css_marker,1)
    js_marker='/* =====================================================\n   PERSONAL KID LESSON INTRO VIDEO\n===================================================== */'
    if js_marker not in text: raise SystemExit(f'JS marker missing: {p}')
    text=text.replace(js_marker, JS+'\n'+js_marker,1)
    # Ensure button after real sidebar data has loaded/rendered.
    anchor='''  list\n    .querySelectorAll(\n      "[data-sidebar-lesson-id]"\n    )'''
    if anchor not in text: raise SystemExit(f'sidebar anchor missing: {p}')
    text=text.replace(anchor, '  ensureLessonProgressButton();\n\n\n'+anchor,1)
    text=text.replace('IAKIDS • build 0.6.4','IAKIDS • build 0.6.5')
    text=text.replace('window.IAKIDS_BUILD_VERSION = "0.6.4";','window.IAKIDS_BUILD_VERSION = "0.6.5";')
    p.write_text(text,encoding='utf-8')
