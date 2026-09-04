from pathlib import Path

p = Path('he/workspace/lesson-completion.js')
text = p.read_text(encoding='utf-8')

marker = '''async function showLessonCompletionScreen(){
'''
helper = '''async function refreshKidUnitLessonProgressRows(){
  const kidId = window.CURRENT_KID?.id;
  const parentLessonId = window.CURRENT_PARENT_LESSON?.id;

  if(!kidId || !parentLessonId || !window.sb){
    return Array.isArray(window.LESSON_SIDEBAR_PROGRESS_ROWS)
      ? window.LESSON_SIDEBAR_PROGRESS_ROWS
      : [];
  }

  const { data, error } = await window.sb
    .from("kid_unit_lesson_progress")
    .select(`
      unit_lesson_id,
      status,
      progress_percent,
      mastery_score,
      best_mastery_score,
      last_activity_at,
      completed_at
    `)
    .eq("kid_id", kidId)
    .eq("learning_lesson_id", parentLessonId);

  if(error){
    console.warn("UNIT LESSON PROGRESS REFRESH WARNING:", error);
    return Array.isArray(window.LESSON_SIDEBAR_PROGRESS_ROWS)
      ? window.LESSON_SIDEBAR_PROGRESS_ROWS
      : [];
  }

  window.LESSON_SIDEBAR_PROGRESS_ROWS = Array.isArray(data) ? data : [];
  updateLessonUnitProgressGauge();
  return window.LESSON_SIDEBAR_PROGRESS_ROWS;
}

window.refreshKidUnitLessonProgressRows = refreshKidUnitLessonProgressRows;


async function showLessonCompletionScreen(){
  /*
    ה-backend כבר סימן את השיעור כ-completed.
    טוענים מחדש את מצב היחידה לפני בניית מסך הסיום,
    כדי שהסרגל/המדדים/הכרטיסים ישתמשו מיד בנתון החדש.
  */
  await refreshKidUnitLessonProgressRows();
'''
if marker not in text:
    raise SystemExit('completion marker not found')
text = text.replace(marker, helper, 1)
p.write_text(text, encoding='utf-8')

p2 = Path('he/workspace/index.html')
idx = p2.read_text(encoding='utf-8')
idx = idx.replace('IAKIDS • build 0.5.8', 'IAKIDS • build 0.5.9')
idx = idx.replace('window.IAKIDS_BUILD_VERSION = "0.5.8";', 'window.IAKIDS_BUILD_VERSION = "0.5.9";')
p2.write_text(idx, encoding='utf-8')
