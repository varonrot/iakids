from pathlib import Path
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
old='''  await startLessonBackgroundMusic();

  awardPartCoins(10, currentPartNumber, Number(window.CURRENT_UNIT_LESSON_ID || CURRENT_LESSON?.id || 0)).catch((error) => {
    console.error("NON-BLOCKING COIN REWARD ERROR:", error);
  });'''
new='''  startLessonBackgroundMusic().catch((error) => {
    console.error("NON-BLOCKING LESSON BACKGROUND MUSIC ERROR:", error);
  });

  awardPartCoins(10, currentPartNumber, Number(window.CURRENT_UNIT_LESSON_ID || CURRENT_LESSON?.id || 0)).catch((error) => {
    console.error("NON-BLOCKING COIN REWARD ERROR:", error);
  });'''
count=s.count(old)
if count != 1:
    raise SystemExit(f'expected exactly one coach-finished blocking music call, found {count}')
s=s.replace(old,new,1)
if 'IAKIDS • build 0.8.8' not in s:
    raise SystemExit('build 0.8.8 stamp not found')
s=s.replace('IAKIDS • build 0.8.8','IAKIDS • build 0.8.9',1)
p.write_text(s,encoding='utf-8')
out=p.read_text(encoding='utf-8')
assert 'NON-BLOCKING LESSON BACKGROUND MUSIC ERROR' in out
assert 'IAKIDS • build 0.8.9' in out
print('v0.8.9 applied: coach-finished background music no longer blocks reward/transition')
