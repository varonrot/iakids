from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

start = s.find('function ensureLessonProgressButton(){')
end = s.find('\nfunction startLessonFromProgressPanel', start)
if start == -1 or end == -1:
    raise SystemExit('progress function boundaries not found')

old = s[start:end]
new = '''function ensureLessonProgressButton(){
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
}
'''
s = s[:start] + new + s[end:]

css = '''
/* Progress card — build 0.7.0 */
.lesson-progress-card-style{
  width:calc(100% - 28px) !important;
  min-height:58px;
  margin:8px 14px 10px !important;
  padding:6px 7px 6px 14px !important;
  display:flex !important;
  align-items:center !important;
  justify-content:space-between !important;
  gap:10px !important;
  border:1px solid rgba(70,137,255,.65) !important;
  border-radius:12px !important;
  background:linear-gradient(135deg,rgba(19,54,102,.96),rgba(22,63,111,.88)) !important;
  box-shadow:inset 0 0 18px rgba(28,102,255,.12),0 0 12px rgba(0,153,255,.08) !important;
  color:#fff !important;
  cursor:pointer;
  transition:.18s ease;
}
.lesson-progress-card-style:hover{
  border-color:rgba(94,174,255,.9) !important;
  transform:translateY(-1px);
}
.lesson-progress-card-text{
  flex:1 1 auto;
  text-align:center;
  font-size:13px;
  font-weight:900;
  line-height:1.2;
}
.lesson-progress-card-image{
  width:48px;
  height:48px;
  flex:0 0 48px;
  border-radius:10px;
  overflow:hidden;
  border:1px solid rgba(124,126,255,.65);
  background:#071426;
  box-shadow:0 0 10px rgba(69,76,255,.22);
}
.lesson-progress-card-image img{
  width:100%;
  height:100%;
  display:block;
  object-fit:cover;
}
'''
marker = '</style>\n<link rel="stylesheet" href="/he/workspace/lesson-completion.css">'
if css.strip() not in s:
    if marker not in s:
        raise SystemExit('style marker not found')
    s = s.replace(marker, css + '\n</style>\n<link rel="stylesheet" href="/he/workspace/lesson-completion.css">', 1)

s = s.replace('IAKIDS • build 0.6.9', 'IAKIDS • build 0.7.0')
s = s.replace('IAKIDS • build 0.6.8', 'IAKIDS • build 0.7.0')

p.write_text(s, encoding='utf-8')
print('patched progress card build 0.7.0')
