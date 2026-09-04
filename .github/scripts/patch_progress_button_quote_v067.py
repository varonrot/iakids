from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

old = '''  btn.innerHTML = "<img class="lesson-progress-button-image" src="/assets/lesson/my-progress.webp" alt="" aria-hidden="true">\n      <span>ההתקדמות שלי</span>";'''
new = '''  btn.innerHTML = `\n    <img\n      class="lesson-progress-button-image"\n      src="/assets/lesson/my-progress.webp"\n      alt=""\n      aria-hidden="true"\n    >\n    <span>ההתקדמות שלי</span>\n  `;'''

if old not in s:
    raise SystemExit('broken progress button string not found')

s = s.replace(old, new, 1)
s = s.replace('IAKIDS • build 0.6.6', 'IAKIDS • build 0.6.7')
s = s.replace('window.IAKIDS_BUILD_VERSION = "0.6.6";', 'window.IAKIDS_BUILD_VERSION = "0.6.7";')

p.write_text(s, encoding='utf-8')
print('fixed progress button syntax; build 0.6.7')
