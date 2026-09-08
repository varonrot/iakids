from pathlib import Path
import re

INDEX = Path('he/workspace/index.html')
LOADER = Path('he/workspace/lesson-completion.js')

index = INDEX.read_text(encoding='utf-8')
loader = LOADER.read_text(encoding='utf-8')

old = '''document.getElementById("rightbarAvatar").src = avatarUrl;\ndocument.getElementById("rightbarName").textContent = kid.child_name;\n\nwindow.KID_AVATAR_URL = avatarUrl;\n\ndocument.getElementById("heroGreeting").textContent =\n  `היי ${kid.child_name}, מה נלמד היום?`;\n\ndocument.getElementById("heroAvatar").src = avatarUrl;\n\nwindow.ACTIVE_KID_ID = kid.id;\n\n  document.getElementById("rightbarAvatar").src = avatarUrl;\n  document.getElementById("rightbarName").textContent = kid.child_name;\n\n  window.KID_AVATAR_URL = avatarUrl;\n\n\n  document.getElementById("heroGreeting").textContent = `היי ${kid.child_name}, מה נלמד היום?`;\n\n  document.getElementById("heroAvatar").src = avatarUrl;\n\n\n  window.ACTIVE_KID_ID = kid.id;\n'''

new = '''const rightbarAvatarEl = document.getElementById("rightbarAvatar");\nconst rightbarNameEl = document.getElementById("rightbarName");\nconst heroGreetingEl = document.getElementById("heroGreeting");\nconst heroAvatarEl = document.getElementById("heroAvatar");\n\nif (rightbarAvatarEl) rightbarAvatarEl.src = avatarUrl;\nif (rightbarNameEl) rightbarNameEl.textContent = kid.child_name;\nif (heroGreetingEl) heroGreetingEl.textContent = `היי ${kid.child_name}, מה נלמד היום?`;\nif (heroAvatarEl) heroAvatarEl.src = avatarUrl;\n\nwindow.KID_AVATAR_URL = avatarUrl;\nwindow.ACTIVE_KID_ID = kid.id;\n'''

if old not in index:
    raise RuntimeError('unsafe dashboard DOM block not found')
index = index.replace(old, new, 1)

# visible build/cache bump
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.66', index, count=1)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.66";', index, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0766', index, count=1)
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.66";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0766', loader, count=1)

INDEX.write_text(index, encoding='utf-8')
LOADER.write_text(loader, encoding='utf-8')
print('Guarded missing dashboard DOM elements; build 0.7.66')
