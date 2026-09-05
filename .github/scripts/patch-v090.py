from pathlib import Path
import re

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

# 1) Restore the coach-finished transition to the pre-coins flow.
old = '''  startLessonBackgroundMusic().catch((error) => {
    console.error("NON-BLOCKING LESSON BACKGROUND MUSIC ERROR:", error);
  });

  awardPartCoins(10, currentPartNumber, Number(window.CURRENT_UNIT_LESSON_ID || CURRENT_LESSON?.id || 0)).catch((error) => {
    console.error("NON-BLOCKING COIN REWARD ERROR:", error);
  });


  if(isLastPart){'''
new = '''  await startLessonBackgroundMusic();

  if(isLastPart){'''
count = s.count(old)
if count < 1:
    raise SystemExit('coach-finished coin block not found')
s = s.replace(old, new)

# 2) Remove the coin reward helper entirely.
pattern = r'\nasync function awardPartCoins\([\s\S]*?\n\}\n\n(?=/\* =====================================================\n   LESSON RENDERER V1)'
s, helper_count = re.subn(pattern, '\n', s, count=1)
if helper_count != 1:
    raise SystemExit(f'awardPartCoins helper removal failed: {helper_count}')

# 3) Remove the +10 coin pop animation CSS only; keep the normal top stat pill.
css_pattern = r'\n\.coin-reward-pop\{[\s\S]*?\n\}\n@keyframes coinRewardPop\{[\s\S]*?\n\}\n'
s, css_count = re.subn(css_pattern, '\n', s, count=1)
if css_count != 1:
    raise SystemExit(f'coin reward CSS removal failed: {css_count}')

# 4) Bump the visible build stamp.
if 'IAKIDS • build 0.8.9' not in s:
    raise SystemExit('build 0.8.9 stamp not found')
s = s.replace('IAKIDS • build 0.8.9', 'IAKIDS • build 0.9.0', 1)

# Validation: no reward code remains in lesson flow.
if 'awardPartCoins(' in s:
    raise SystemExit('awardPartCoins still present')
if 'coin-reward-pop' in s or '@keyframes coinRewardPop' in s:
    raise SystemExit('coin reward animation still present')
if 'IAKIDS • build 0.9.0' not in s:
    raise SystemExit('build stamp not updated')

p.write_text(s, encoding='utf-8')
print(f'stabilized lesson flow; restored {count} transition block(s)')
