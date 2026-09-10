from pathlib import Path

EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old = '''      .homework-notebook-pane{\n        display:flex;\n        flex-direction:column;\n        direction:rtl;\n      }\n'''
new = '''      .homework-notebook-pane{\n        display:flex;\n        flex-direction:column;\n        direction:rtl;\n        align-self:stretch!important;\n        height:100%!important;\n        min-height:100%!important;\n      }\n'''
if old in ext:
    ext = ext.replace(old, new, 1)
elif 'align-self:stretch!important;' not in ext:
    raise SystemExit('notebook pane CSS anchor not found')

old_grid = '''      .homework-dual-workspace{\n        position:absolute;\n        inset:0;\n        display:grid;\n        grid-template-columns:minmax(0,1.08fr) minmax(0,1fr);\n        gap:14px;\n        padding:12px;\n        direction:ltr;\n        background:#031022;\n      }\n'''
new_grid = '''      .homework-dual-workspace{\n        position:absolute;\n        inset:0;\n        display:grid;\n        grid-template-columns:minmax(0,1.08fr) minmax(0,1fr);\n        grid-template-rows:minmax(0,1fr);\n        align-items:stretch;\n        gap:14px;\n        padding:12px;\n        direction:ltr;\n        background:#031022;\n      }\n'''
if old_grid in ext:
    ext = ext.replace(old_grid, new_grid, 1)

old_page = '''      .homework-notebook-page{\n        position:relative;\n        flex:1;\n        overflow:auto;\n'''
new_page = '''      .homework-notebook-page{\n        position:relative;\n        flex:1 1 auto;\n        min-height:0;\n        height:100%;\n        overflow:auto;\n'''
if old_page in ext:
    ext = ext.replace(old_page, new_page, 1)
elif 'flex:1 1 auto;' not in ext:
    raise SystemExit('notebook page CSS anchor not found')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.60";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.73";')

for oldv in ('0.7.71','0.7.72'):
    index = index.replace(f'IAKIDS • build {oldv}', 'IAKIDS • build 0.7.73')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{oldv}";', 'window.IAKIDS_BUILD_VERSION = "0.7.73";')
index = index.replace('/he/workspace/lesson-completion.js?v=0760', '/he/workspace/lesson-completion.js?v=0773')
index = index.replace('/he/workspace/lesson-completion.js?v=0772', '/he/workspace/lesson-completion.js?v=0773')

EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Stretched homework notebook to full pane height; build 0.7.73')
