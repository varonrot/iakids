from pathlib import Path
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
old='async function awardPartCoins(amount = 10, explicitPartNumber = null){\n  const kidId = CURRENT_KID?.id || localStorage.getItem("active_kid_id");\n  const unitLessonId = Number(CURRENT_LESSON?.id || window.CURRENT_UNIT_LESSON_ID || window.CURRENT_LESSON_ID || 0);\n  const partNumber = Number(explicitPartNumber || window.CURRENT_LESSON_VISUAL_PART || window.CURRENT_LESSON_PART_NUMBER || 1);'
new='async function awardPartCoins(amount = 10, explicitPartNumber = null, explicitUnitLessonId = null){\n  const kidId = CURRENT_KID?.id || localStorage.getItem("active_kid_id");\n  const unitLessonId = Number(explicitUnitLessonId || 0);\n  const partNumber = Number(explicitPartNumber || 0);'
if old not in s: raise SystemExit('award function signature/body not found')
s=s.replace(old,new,1)
oldcall='awardPartCoins(10, currentPartNumber).catch((error) => {'
newcall='awardPartCoins(10, currentPartNumber, Number(window.CURRENT_UNIT_LESSON_ID || CURRENT_LESSON?.id || 0)).catch((error) => {'
if oldcall not in s: raise SystemExit('nonblocking award call not found')
s=s.replace(oldcall,newcall,1)
if 'IAKIDS • build 0.8.5' in s: s=s.replace('IAKIDS • build 0.8.5','IAKIDS • build 0.8.6',1)
elif 'IAKIDS • build 0.8.4' in s: s=s.replace('IAKIDS • build 0.8.4','IAKIDS • build 0.8.6',1)
else: raise SystemExit('expected build stamp not found')
p.write_text(s,encoding='utf-8')
out=p.read_text(encoding='utf-8')
assert 'explicitUnitLessonId' in out and 'IAKIDS • build 0.8.6' in out
print('v0.8.6 explicit unit lesson reward applied')
