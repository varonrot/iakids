from pathlib import Path
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
old='''function openStudentLessonProgressPanel(){
  const stage=document.querySelector(".lesson-visual-stage"); if(!stage) return;
  document.getElementById("studentLessonProgressPanel")?.remove();
  const rows=window.LESSON_SIDEBAR_ROWS||[]; const pmap=new Map((window.LESSON_SIDEBAR_PROGRESS_ROWS||[]).map(r=>[Number(r.unit_lesson_id),r]));'''
new='''async function openStudentLessonProgressPanel(){
  const stage=document.querySelector(".lesson-visual-stage"); if(!stage) return;
  document.getElementById("studentLessonProgressPanel")?.remove();
  const rows=window.LESSON_SIDEBAR_ROWS||[];

  if(CURRENT_KID?.id && rows.length){
    const lessonIds = rows.map(row => Number(row.id)).filter(Boolean);
    const { data: freshProgressRows, error: freshProgressError } = await sb
      .from("kid_unit_lesson_progress")
      .select("unit_lesson_id,status,progress_percent,current_stage,last_part_number,mastery_score,best_mastery_score,attempts_count,last_activity_at,completed_at")
      .eq("kid_id", CURRENT_KID.id)
      .in("unit_lesson_id", lessonIds);

    if(freshProgressError){
      console.warn("STUDENT PROGRESS PANEL FRESH LOAD WARNING:", freshProgressError);
    }
    else{
      window.LESSON_SIDEBAR_PROGRESS_ROWS = Array.isArray(freshProgressRows)
        ? freshProgressRows
        : [];
    }
  }

  const pmap=new Map((window.LESSON_SIDEBAR_PROGRESS_ROWS||[]).map(r=>[Number(r.unit_lesson_id),r]));'''
if old not in s:
    raise SystemExit('progress panel function anchor not found')
s=s.replace(old,new,1)
if 'IAKIDS • build 0.8.7' not in s:
    raise SystemExit('build 0.8.7 stamp not found')
s=s.replace('IAKIDS • build 0.8.7','IAKIDS • build 0.8.8',1)
p.write_text(s,encoding='utf-8')
out=p.read_text(encoding='utf-8')
assert 'async function openStudentLessonProgressPanel()' in out
assert 'STUDENT PROGRESS PANEL FRESH LOAD WARNING' in out
assert 'IAKIDS • build 0.8.8' in out
print('v0.8.8 fresh progress panel refresh applied')
