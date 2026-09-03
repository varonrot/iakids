from pathlib import Path
import re

path = Path('he/workspace/index.html')
text = path.read_text(encoding='utf-8')
original = text

text, n1 = re.subn(
    r'/\*\s*כרגע Learning Coach 1 הוא חצי מהשיעור,\s*ולכן רק ההבנה הכוללת מקבלת חצי מהציון\.\s*\*/\s*const overallTopicScore\s*=\s*Math\.round\(\s*safeScore\s*/\s*2\s*\);',
    '''/*
  הציון הכללי אינו מחושב יותר בפרונט לפי מספר חלקים קשיח.
  מקור האמת הוא kid_lesson_progress.mastery_score.
*/

const overallTopicScore =
  normalizeLessonScore(
    window.CURRENT_OVERALL_LESSON_MASTERY_SCORE
  )
  ??
  0;''',
    text,
    count=1
)
if n1 != 1:
    raise SystemExit(f'overall block replacements: {n1}')

text, n2 = re.subn(
    r'if\(partOneSummary\)\{\s*partOneSummary\.textContent\s*=\s*`\$\{safeScore\}%`;\s*\}',
    '''if(
  partOneSummary
  &&
  Number(
    window.CURRENT_LESSON_VISUAL_PART
    ||
    1
  ) === 1
){

  partOneSummary.textContent =
    `${safeScore}%`;

}''',
    text,
    count=1
)
if n2 != 1:
    raise SystemExit(f'part 1 summary replacements: {n2}')

marker = '''/* =====================================================
   עדכון המד אחרי תשובת Coach
===================================================== */'''

helper = '''/* =====================================================
   OVERALL LESSON MASTERY FROM DB
===================================================== */
async function fetchCurrentLessonOverallMastery(){

  const kidId = CURRENT_KID?.id;

  const lessonId =
    Number(
      currentLessonId
      ||
      window.CURRENT_LESSON_ID
      ||
      0
    );

  const unitLessonId =
    Number(
      window.SELECTED_UNIT_LESSON?.unit_lesson_id
      ||
      0
    );

  if(!kidId || !lessonId || !unitLessonId){
    return null;
  }

  const { data, error } =
    await sb
      .from('kid_lesson_progress')
      .select('mastery_score')
      .eq('kid_id', kidId)
      .eq('lesson_id', lessonId)
      .eq('current_unit_lesson_id', unitLessonId)
      .limit(1);

  if(error){
    console.error('OVERALL LESSON MASTERY FETCH ERROR:', error);
    return null;
  }

  return normalizeLessonScore(
    Array.isArray(data)
      ? data[0]?.mastery_score
      : null
  );
}

'''

if 'async function fetchCurrentLessonOverallMastery' not in text:
    if marker not in text:
        raise SystemExit('score refresh marker not found')
    text = text.replace(marker, helper + marker, 1)

text, n3 = re.subn(
    r'const finalScore\s*=\s*databaseScore\s*\?\?\s*directScore;',
    '''const overallDatabaseScore =
  await fetchCurrentLessonOverallMastery();

if(overallDatabaseScore !== null){
  window.CURRENT_OVERALL_LESSON_MASTERY_SCORE =
    overallDatabaseScore;
}

const finalScore =
  databaseScore
  ??
  directScore;''',
    text,
    count=1
)
if n3 != 1:
    raise SystemExit(f'final score replacements: {n3}')

if text == original:
    raise SystemExit('No changes made')

path.write_text(text, encoding='utf-8')
