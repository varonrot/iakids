from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

old = '''  const btn = document.createElement("button");
  btn.type = "button";
  btn.id = "lessonProgressOpenBtn";
  btn.className = "lesson-progress-open-btn";
  btn.innerHTML = `
    <span class="lesson-progress-inline-icon" aria-hidden="true">
      <svg viewBox="0 0 32 32" focusable="false" aria-hidden="true">
        <path d="M5 25V18H10V25H5ZM13.5 25V13H18.5V25H13.5ZM22 25V8H27V25H22Z" fill="currentColor" opacity=".9"/>
        <path d="M6 14L12 9L17 11L25 4" fill="none" stroke="#ffd24a" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M21.5 4H25V7.5" fill="none" stroke="#ffd24a" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </span>
    <span>ההתקדמות שלי</span>
  `;'''

new = '''  const btn = document.createElement("button");
  btn.type = "button";
  btn.id = "lessonProgressOpenBtn";
  btn.className = "lesson-progress-open-btn lesson-progress-card-style";
  btn.innerHTML = `
    <span class="lesson-progress-card-text">ההתקדמות שלי</span>
    <span class="lesson-progress-card-image" aria-hidden="true">
      <img src="/assets/science/categories/ecology.webp" alt="">
    </span>
  `;'''

if old not in s:
    raise SystemExit('target progress button block not found')
s = s.replace(old, new, 1)

style_anchor = '''/* Progress button image — build 0.6.6 */
.lesson-progress-button-image{
  width:26px;
  height:26px;
  object-fit:contain;
  flex:0 0 26px;
  display:block;
}
'''

style_new = '''/* Progress card — build 0.7.0 */
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

if style_anchor in s:
    s = s.replace(style_anchor, style_new, 1)
else:
    marker = '</style>\n<link rel="stylesheet" href="/he/workspace/lesson-completion.css">'
    if marker not in s:
        raise SystemExit('style insertion marker not found')
    s = s.replace(marker, style_new + '\n</style>\n<link rel="stylesheet" href="/he/workspace/lesson-completion.css">', 1)

s = s.replace('IAKIDS • build 0.6.9', 'IAKIDS • build 0.7.0')
s = s.replace('IAKIDS • build 0.6.8', 'IAKIDS • build 0.7.0')

p.write_text(s, encoding='utf-8')
print('patched progress card to build 0.7.0')
