from pathlib import Path

INDEX = Path('he/workspace/index.html')
EXT = Path('he/workspace/lesson-completion.js')

index = INDEX.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')

# Make homework use the exact lesson layout/theme rules.
ext = ext.replace(
    'document.body.classList.add("homework-lesson-mode");',
    'document.body.classList.add("homework-lesson-mode", "lesson-theme-science");'
)

# Bump homework router/core version.
ext = ext.replace(
    'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.12";',
    'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.13";'
)
ext = ext.replace(
    '/he/workspace/lesson-completion-core.js?v=0712',
    '/he/workspace/lesson-completion-core.js?v=0713'
)

# Force the HTML to load the new router version.
for old in [
    '<script src="/he/workspace/lesson-completion.js"></script>',
    '<script src="/he/workspace/lesson-completion.js?v=0711"></script>',
    '<script src="/he/workspace/lesson-completion.js?v=0712"></script>',
]:
    index = index.replace(old, '<script src="/he/workspace/lesson-completion.js?v=0713"></script>')

if '<script src="/he/workspace/lesson-completion.js?v=0713"></script>' not in index:
    raise SystemExit('lesson-completion 0.7.13 script tag not found')

# Keep the visible frontend build stamp and JS constant in sync.
index = index.replace('IAKIDS • build 0.7.10', 'IAKIDS • build 0.7.13')
index = index.replace(
    'window.IAKIDS_BUILD_VERSION = "0.6.7";',
    'window.IAKIDS_BUILD_VERSION = "0.7.13";'
)

INDEX.write_text(index, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')

print('Homework workspace fixed; frontend build bumped to 0.7.13')
