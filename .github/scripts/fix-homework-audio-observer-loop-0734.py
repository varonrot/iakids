from pathlib import Path
import re

INDEX = Path('he/workspace/index.html')
LOADER = Path('he/workspace/lesson-completion.js')

index = INDEX.read_text(encoding='utf-8')
loader = LOADER.read_text(encoding='utf-8')

old_observer = '''  const observer = new MutationObserver(()=>mountToggle());\n  observer.observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:["class"]});\n  document.addEventListener("DOMContentLoaded", mountToggle);\n  setTimeout(mountToggle, 300);\n  setTimeout(mountToggle, 1000);\n'''
new_observer = '''  // Do not observe the whole document: updateToggle() changes button.innerHTML,\n  // which can recursively trigger MutationObserver childList events and freeze the page.\n  document.addEventListener("DOMContentLoaded", mountToggle);\n  setTimeout(mountToggle, 300);\n  setTimeout(mountToggle, 1000);\n'''
if old_observer not in loader:
    raise RuntimeError('audio observer block not found')
loader = loader.replace(old_observer, new_observer, 1)

anchor = '''    clearHomeworkChat();\n    renderHomeworkSidebar();\n\n    if(options.keepPreview !== true){\n'''
replacement = '''    clearHomeworkChat();\n    renderHomeworkSidebar();\n\n    // Mount audio toggle once after homework mode is active.\n    // Avoid a document-wide MutationObserver loop.\n    setTimeout(() => window.mountHomeworkAudioToggle?.(), 0);\n\n    if(options.keepPreview !== true){\n'''
if anchor not in loader:
    raise RuntimeError('homework workspace mount anchor not found')
loader = loader.replace(anchor, replacement, 1)

# Current restored branch uses 0.7.33. Bump diagnostic fix to 0.7.34.
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.34";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0734', loader, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0734', index, count=1)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.34', index, count=1)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.34";', index, count=1)

INDEX.write_text(index, encoding='utf-8')
LOADER.write_text(loader, encoding='utf-8')
print('Fixed homework audio MutationObserver loop; build 0.7.34')
