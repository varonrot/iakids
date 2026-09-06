from pathlib import Path

INDEX = Path('he/workspace/index.html')
EXT = Path('he/workspace/lesson-completion.js')

index = INDEX.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')

# The sidebar / dashboard homework entry should open the homework workspace only.
# Choosing camera vs file happens inside the homework upload card.
index = index.replace(
    'id="homeworkSidebarBtn"\n      onclick="startHomeworkCamera()"',
    'id="homeworkSidebarBtn"\n      onclick="showLearning(\'homework\')"'
)

index = index.replace(
    'class="home-right-action home-right-homework"\n      onclick="startHomeworkCamera()"',
    'class="home-right-action home-right-homework"\n      onclick="showLearning(\'homework\')"'
)

# Make startHomeworkCamera safe as an entry helper too: it opens the workspace,
# but does not force-open any OS file/camera picker.
old = '''  window.startHomeworkCamera = async function(){\n    showHomeworkLessonWorkspace();\n\n    await new Promise(resolve => setTimeout(resolve,80));\n\n    document.getElementById("homeworkCameraInput")?.click();\n  };\n'''
new = '''  window.startHomeworkCamera = async function(){\n    return showHomeworkLessonWorkspace();\n  };\n'''
if old in ext:
    ext = ext.replace(old, new, 1)

# Keep the dedicated buttons inside the upload card unchanged:
# data-homework-camera -> camera input, data-homework-file -> file input.

# Bump visible build/cache versions.
index = index.replace('IAKIDS • build 0.7.17', 'IAKIDS • build 0.7.18')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.17";', 'window.IAKIDS_BUILD_VERSION = "0.7.18";')
index = index.replace('/he/workspace/lesson-completion.js?v=0717', '/he/workspace/lesson-completion.js?v=0718')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.17";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.18";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0717', '/he/workspace/lesson-completion-core.js?v=0718')

INDEX.write_text(index, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')

print('Homework entry now opens chooser screen only; build 0.7.18')

# trigger 0.7.18
