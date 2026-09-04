from pathlib import Path
import re
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
# Replace only the progress-button emoji immediately attached to the progress label.
patterns=[
    (r'📊\s*ההתקדמות שלי', '<img class="lesson-progress-button-image" src="/assets/lesson/my-progress.webp" alt="" aria-hidden="true">\n      <span>ההתקדמות שלי</span>'),
    (r'<span([^>]*)>\s*📊\s*</span>\s*<span([^>]*)>\s*ההתקדמות שלי\s*</span>', '<img class="lesson-progress-button-image" src="/assets/lesson/my-progress.webp" alt="" aria-hidden="true">\n      <span\\2>ההתקדמות שלי</span>'),
]
changed=False
for pat,repl in patterns:
    ns,n=re.subn(pat,repl,s,count=1)
    if n:
        s=ns; changed=True; break
if not changed:
    raise SystemExit('progress button emoji/label pattern not found')
# Add scoped image styling once.
css='''\n/* Progress button image — build 0.6.6 */\n.lesson-progress-button-image{\n  width:26px;\n  height:26px;\n  object-fit:contain;\n  flex:0 0 26px;\n  display:block;\n}\n'''
if '.lesson-progress-button-image{' not in s:
    s=s.replace('</style>', css+'\n</style>',1)
s=s.replace('IAKIDS • build 0.6.5','IAKIDS • build 0.6.6')
s=s.replace('window.IAKIDS_BUILD_VERSION = "0.6.5"','window.IAKIDS_BUILD_VERSION = "0.6.6"')
p.write_text(s,encoding='utf-8')
print('patched progress image button; build 0.6.6')