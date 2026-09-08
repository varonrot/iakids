from pathlib import Path
import re

INDEX = Path('he/workspace/index.html')
LOADER = Path('he/workspace/lesson-completion.js')

index = INDEX.read_text(encoding='utf-8')
loader = LOADER.read_text(encoding='utf-8')

# Remove the aggressive polling loop added in 0.7.59. It can keep querying/re-rendering
# when CURRENT_KID is not stable during workspace transitions.
pattern = re.compile(r'''\n\s*setInterval\(\(\)=>\{\n\s*const kid = getKid\(\);\n\s*const kidId = kid\?\.id \|\| null;\n\s*if\(kidId !== lastKidId\)\{\n\s*refreshPersonalSystems\(true\);\n\s*\}\n\s*\},900\);\n''')
index, n = pattern.subn('\n', index, count=1)
if n == 0 and 'setInterval(()=>{' in index and 'refreshPersonalSystems(true)' in index:
    raise RuntimeError('personal systems polling loop pattern changed')

# Add a lightweight explicit refresh hook on common workspace lifecycle events only.
anchor = "  window.refreshPersonalSystemsSidebar = ()=>refreshPersonalSystems(true);\n"
if anchor in index and 'IAKIDS_PERSONAL_SYSTEMS_FREEZE_FIX_0761' not in index:
    replacement = anchor + '''\n  // IAKIDS_PERSONAL_SYSTEMS_FREEZE_FIX_0761\n  document.addEventListener('iakids:kid-changed', ()=>refreshPersonalSystems(true));\n  window.addEventListener('pageshow', ()=>{\n    setTimeout(()=>refreshPersonalSystems(true), 120);\n  });\n'''
    index = index.replace(anchor, replacement, 1)

# Make sidebar clicks completely isolated from parent/global click handlers.
index = index.replace(
    "      row.querySelector('.iakids-personal-system-open')?.addEventListener('click', ()=>openPersonalSystem(subject));",
    "      row.querySelector('.iakids-personal-system-open')?.addEventListener('click', event=>{ event.preventDefault(); event.stopPropagation(); openPersonalSystem(subject); });",
    1
)

# Make modal finish idempotent so multiple close events can never double-resolve/remove.
old = '''      const finish = value => {\n        document.removeEventListener('keydown', onKeyDown);\n        backdrop.remove();\n        resolve(value);\n      };'''
new = '''      let finished = false;\n      const finish = value => {\n        if(finished) return;\n        finished = true;\n        document.removeEventListener('keydown', onKeyDown);\n        if(backdrop.isConnected) backdrop.remove();\n        resolve(value);\n      };'''
if old in index:
    index = index.replace(old, new, 1)

# Visible build bump + cache busting.
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.61', index, count=1)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.61";', index, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0761', index, count=1)
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.61";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0761', loader, count=1)

INDEX.write_text(index, encoding='utf-8')
LOADER.write_text(loader, encoding='utf-8')
print('Fixed personal systems sidebar freeze risk; build 0.7.61')
