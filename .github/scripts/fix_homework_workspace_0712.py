from pathlib import Path

INDEX = Path('he/workspace/index.html')
EXT = Path('he/workspace/lesson-completion.js')

index = INDEX.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')

# Force browsers/CDN to load the new homework workspace router.
old_tags = [
    '<script src="/he/workspace/lesson-completion.js"></script>',
    '<script src="/he/workspace/lesson-completion.js?v=0711"></script>',
]
new_tag = '<script src="/he/workspace/lesson-completion.js?v=0712"></script>'

replaced = False
for old in old_tags:
    if old in index:
        index = index.replace(old, new_tag)
        replaced = True

if new_tag not in index:
    raise SystemExit('lesson-completion script tag not found')

# Also cache-bust the preserved core loaded by lesson-completion.js.
ext = ext.replace(
    '/he/workspace/lesson-completion-core.js?v=0711',
    '/he/workspace/lesson-completion-core.js?v=0712'
)

# Add an explicit version marker to make production verification easy.
marker = 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.12";\n'
if 'IAKIDS_HOMEWORK_WORKSPACE_VERSION' not in ext:
    ext = marker + ext

INDEX.write_text(index, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')

print('Homework workspace 0.7.12 patch applied')
