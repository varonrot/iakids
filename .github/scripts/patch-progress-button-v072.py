from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

old = '''function ensureLessonProgressButton(){
  const list = document.getElementById("lessonSidebarList");
  if(!list || document.getElementById("lessonProgressOpenBtn")) return;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.id = "lessonProgressOpenBtn";
  btn.className = "lesson-progress-open-btn lesson-progress-card-style";
  btn.innerHTML = `
    <span class="lesson-progress-card-text">ההתקדמות שלי</span>
    <span class="lesson-progress-card-image" aria-hidden="true">
      <img src="/assets/science/categories/ecology.webp" alt="">
    </span>
  `;
  btn.addEventListener("click", openStudentLessonProgressPanel);
  list.parentElement?.insertBefore(btn, list);
}'''

new = '''function ensureLessonProgressButton(){
  const list = document.getElementById("lessonSidebarList");
  if(!list || document.getElementById("lessonProgressOpenBtn")) return;

  const btn = document.createElement("button");
  btn.type = "button";
  btn.id = "lessonProgressOpenBtn";
  btn.className = "lesson-progress-open-btn lesson-progress-card-style";
  btn.innerHTML = `
    <span class="lesson-progress-card-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" focusable="false">
        <path d="M4 19V10M10 19V6M16 19V3" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M3 20h18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M5 12l4-4 4 2 6-6" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M16.5 4H19v2.5" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </span>
    <span class="lesson-progress-card-text">ההתקדמות שלי</span>
  `;

  btn.addEventListener("click", openStudentLessonProgressPanel);

  const unitCard = document.querySelector(".lesson-sidebar-unit");
  if(unitCard?.parentElement){
    unitCard.parentElement.insertBefore(btn, unitCard);
  }else{
    list.parentElement?.insertBefore(btn, list);
  }
}'''

if old not in s:
    raise SystemExit('progress button function block not found')

s = s.replace(old, new, 1)

marker = '''/* Progress button image — build 0.6.6 */'''
css = '''\n/* Progress button placement/icon — build 0.7.2 */\n.lesson-progress-card-style{\n  display:flex !important;\n  align-items:center !important;\n  justify-content:space-between !important;\n  gap:10px !important;\n}\n.lesson-progress-card-icon{\n  width:34px;\n  height:34px;\n  flex:0 0 34px;\n  display:grid;\n  place-items:center;\n  border-radius:10px;\n  color:#66d8ff;\n  background:linear-gradient(180deg,rgba(34,112,174,.34),rgba(23,73,135,.30));\n  border:1px solid rgba(82,184,255,.42);\n  box-shadow:inset 0 0 12px rgba(28,159,255,.10);\n}\n.lesson-progress-card-icon svg{\n  width:21px;\n  height:21px;\n  display:block;\n}\n.lesson-progress-card-text{\n  flex:1;\n  text-align:right;\n}\n'''

if css.strip() not in s:
    insert_at = s.find('</style>')
    if insert_at == -1:
        raise SystemExit('style close tag not found')
    s = s[:insert_at] + css + s[insert_at:]

s = s.replace('IAKIDS • build 0.7.0', 'IAKIDS • build 0.7.2')
s = s.replace('IAKIDS • build 0.7.1', 'IAKIDS • build 0.7.2')

p.write_text(s, encoding='utf-8')
