from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

old_call = '  await awardPartCoins(10);'
new_call = '  await awardPartCoins(10, currentPartNumber);'
if old_call not in s:
    raise SystemExit('reward call not found')
s = s.replace(old_call, new_call, 1)

old_sig = 'async function awardPartCoins(amount = 10){'
new_sig = 'async function awardPartCoins(amount = 10, explicitPartNumber = null){'
if old_sig not in s:
    raise SystemExit('awardPartCoins signature not found')
s = s.replace(old_sig, new_sig, 1)

old_part = '  const partNumber = Number(window.CURRENT_LESSON_VISUAL_PART || window.CURRENT_LESSON_PART_NUMBER || 1);'
new_part = '  const partNumber = Number(explicitPartNumber || window.CURRENT_LESSON_VISUAL_PART || window.CURRENT_LESSON_PART_NUMBER || 1);'
if old_part not in s:
    raise SystemExit('part number resolver not found')
s = s.replace(old_part, new_part, 1)

# Make unit lesson ID resolution explicit from the active lesson object before fallbacks.
old_unit = '  const unitLessonId = Number(window.CURRENT_UNIT_LESSON_ID || window.CURRENT_LESSON_ID || CURRENT_LESSON?.id || 0);'
new_unit = '  const unitLessonId = Number(CURRENT_LESSON?.id || window.CURRENT_UNIT_LESSON_ID || window.CURRENT_LESSON_ID || 0);'
if old_unit not in s:
    raise SystemExit('unit lesson resolver not found')
s = s.replace(old_unit, new_unit, 1)

if 'IAKIDS • build 0.8.1' not in s:
    raise SystemExit('build 0.8.1 stamp not found')
s = s.replace('IAKIDS • build 0.8.1', 'IAKIDS • build 0.8.2', 1)

p.write_text(s, encoding='utf-8')
out = p.read_text(encoding='utf-8')
for token in [
    'await awardPartCoins(10, currentPartNumber);',
    'async function awardPartCoins(amount = 10, explicitPartNumber = null){',
    'const partNumber = Number(explicitPartNumber ||',
    'IAKIDS • build 0.8.2'
]:
    if token not in out:
        raise SystemExit('validation failed: ' + token)
print('v0.8.2 explicit part reward arguments applied')
