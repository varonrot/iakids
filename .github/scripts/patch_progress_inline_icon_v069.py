from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

old = '''  btn.innerHTML = `
    <img
      class="lesson-progress-button-image"
      src="/assets/lesson/my-progress.webp"
      alt=""
      aria-hidden="true"
    >
    <span>ההתקדמות שלי</span>
  `;'''

new = '''  btn.innerHTML = `
    <span class="lesson-progress-inline-icon" aria-hidden="true">
      <svg viewBox="0 0 32 32" focusable="false" role="img">
        <defs>
          <linearGradient id="progressBarsGradient" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stop-color="#19d8ff"/>
            <stop offset="55%" stop-color="#4f7cff"/>
            <stop offset="100%" stop-color="#a855f7"/>
          </linearGradient>
          <linearGradient id="progressArrowGradient" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stop-color="#ffd24a"/>
            <stop offset="100%" stop-color="#ff9f1a"/>
          </linearGradient>
        </defs>
        <rect x="2.5" y="2.5" width="27" height="27" rx="8" fill="rgba(8,27,66,.92)" stroke="#3bb8ff" stroke-width="1.2"/>
        <rect x="7" y="19" width="3.5" height="6" rx="1.2" fill="url(#progressBarsGradient)"/>
        <rect x="12.5" y="15" width="3.5" height="10" rx="1.2" fill="url(#progressBarsGradient)"/>
        <rect x="18" y="11" width="3.5" height="14" rx="1.2" fill="url(#progressBarsGradient)"/>
        <path d="M7 16.5c4.5-1.6 7.1-3.8 10.1-7l3-3" fill="none" stroke="url(#progressArrowGradient)" stroke-width="2.4" stroke-linecap="round"/>
        <path d="M18.8 5.9h4.7v4.7" fill="none" stroke="#ffc83d" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="24.1" cy="6.1" r="1" fill="#fff8c7"/>
      </svg>
    </span>
    <span>ההתקדמות שלי</span>
  `;'''

if old not in s:
    raise SystemExit('progress image markup not found')

s = s.replace(old, new, 1)

css = '''
/* Inline progress icon — build 0.6.9 */
.lesson-progress-inline-icon{
  width:28px;
  height:28px;
  flex:0 0 28px;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  filter:drop-shadow(0 0 5px rgba(49,171,255,.28));
}
.lesson-progress-inline-icon svg{
  width:28px;
  height:28px;
  display:block;
}
'''
if '.lesson-progress-inline-icon{' not in s:
    s = s.replace('</style>', css + '\n</style>', 1)

s = s.replace('IAKIDS • build 0.6.8', 'IAKIDS • build 0.6.9')
s = s.replace('window.IAKIDS_BUILD_VERSION = "0.6.8"', 'window.IAKIDS_BUILD_VERSION = "0.6.9"')

p.write_text(s, encoding='utf-8')
print('patched progress button to inline SVG icon; build 0.6.9')
