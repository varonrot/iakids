from pathlib import Path
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
needle='''<div class="lesson-sidebar-unit">'''
insert='''<button\n  type="button"\n  class="lesson-sidebar-back-to-workspace"\n  onclick="window.location.href='/he/workspace/'"\n  aria-label="חזרה למערך השיעורים"\n>\n  <span aria-hidden="true">←</span>\n  <strong>חזרה למערך השיעורים</strong>\n</button>\n\n\n<div class="lesson-sidebar-unit">'''
assert needle in s
s=s.replace(needle,insert,1)
css='''\n<style id="lesson-sidebar-back-v068">\n.lesson-sidebar-back-to-workspace{\n  width:calc(100% - 20px);margin:8px 10px 10px;padding:9px 10px;\n  display:flex;align-items:center;justify-content:center;gap:7px;\n  border:1px solid rgba(84,181,255,.35);border-radius:10px;\n  background:linear-gradient(135deg,rgba(14,52,91,.92),rgba(24,38,91,.92));\n  color:#eaf6ff;cursor:pointer;font-family:inherit;font-size:11px;\n  box-shadow:inset 0 0 16px rgba(37,139,255,.08);transition:.18s ease;\n}\n.lesson-sidebar-back-to-workspace:hover{border-color:#57c9ff;transform:translateY(-1px);box-shadow:0 0 14px rgba(38,170,255,.18)}\n.lesson-sidebar-back-to-workspace span{font-size:15px;line-height:1}\n</style>\n'''
assert '</head>' in s
s=s.replace('</head>',css+'\n</head>',1)
# bump visible build only
if 'IAKIDS • build 0.6.7' in s:
    s=s.replace('IAKIDS • build 0.6.7','IAKIDS • build 0.6.8')
elif 'build 0.6.7' in s:
    s=s.replace('build 0.6.7','build 0.6.8')
else:
    raise AssertionError('build 0.6.7 marker not found')
p.write_text(s,encoding='utf-8')
