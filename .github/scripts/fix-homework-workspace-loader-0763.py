from pathlib import Path
import re

LOADER = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

loader = LOADER.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old_onload = '''  core.onload = function(){\n    installHomeworkLessonWorkspace();\n  };'''
new_onload = '''  core.onload = function(){\n    let attempts = 0;\n    const tryInstallHomeworkWorkspace = function(){\n      attempts += 1;\n      const installed = installHomeworkLessonWorkspace();\n      if(installed === true || window.__HOMEWORK_LESSON_WORKSPACE_V1){\n        return;\n      }\n      if(attempts < 80){\n        setTimeout(tryInstallHomeworkWorkspace, 100);\n      }\n      else{\n        console.error("HOMEWORK WORKSPACE: showLearning was not ready after retries");\n      }\n    };\n    tryInstallHomeworkWorkspace();\n  };'''
if old_onload not in loader:
    raise RuntimeError('core.onload block not found')
loader = loader.replace(old_onload, new_onload, 1)

old_install = '''function installHomeworkLessonWorkspace(){\n  if(window.__HOMEWORK_LESSON_WORKSPACE_V1){\n    return;\n  }\n\n  window.__HOMEWORK_LESSON_WORKSPACE_V1 = true;\n\n  const originalShowLearning = window.showLearning;\n\n  if(typeof originalShowLearning !== "function"){\n    console.error("HOMEWORK WORKSPACE: showLearning was not found");\n    return;\n  }'''
new_install = '''function installHomeworkLessonWorkspace(){\n  if(window.__HOMEWORK_LESSON_WORKSPACE_V1){\n    return true;\n  }\n\n  const originalShowLearning = window.showLearning;\n\n  if(typeof originalShowLearning !== "function"){\n    console.warn("HOMEWORK WORKSPACE: showLearning is not ready yet");\n    return false;\n  }\n\n  window.__HOMEWORK_LESSON_WORKSPACE_V1 = true;'''
if old_install not in loader:
    raise RuntimeError('installHomeworkLessonWorkspace header not found')
loader = loader.replace(old_install, new_install, 1)

# Cache bust and visible version bump
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.63";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0763', loader, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0763', index, count=1)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.63', index, count=1)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.63";', index, count=1)

LOADER.write_text(loader, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Fixed homework workspace loader race; build 0.7.63')
