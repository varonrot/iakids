from pathlib import Path

p = Path('he/workspace/index.html')
text = p.read_text(encoding='utf-8')

old = '''  const lessons =
    Array.isArray(data)
      ? data
      : [];


  window.LESSON_SIDEBAR_ROWS =
    lessons;
'''
new = '''  const lessons =
    Array.isArray(data)
      ? data
      : [];


  /* =============================================
     התקדמות אמיתית של הילד בכל שיעור פנימי
  ============================================= */

  let unitLessonProgressRows = [];

  if(CURRENT_KID?.id){

    const {
      data: progressData,
      error: progressError
    } = await sb
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
      .eq("kid_id", CURRENT_KID.id)
      .eq("learning_lesson_id", parentLessonId);

    if(progressError){
      console.warn(
        "LESSON SIDEBAR PROGRESS LOAD WARNING:",
        progressError
      );
    }
    else{
      unitLessonProgressRows =
        Array.isArray(progressData)
          ? progressData
          : [];
    }

  }

  const progressByLessonId =
    new Map(
      unitLessonProgressRows.map(
        row => [
          Number(row.unit_lesson_id),
          row
        ]
      )
    );

  window.LESSON_SIDEBAR_PROGRESS_ROWS =
    unitLessonProgressRows;


  window.LESSON_SIDEBAR_ROWS =
    lessons;
'''
if old not in text:
    raise SystemExit('lessons marker not found')
text = text.replace(old, new, 1)

start = text.index('          const isCurrent =\n', text.index('async function loadRealLessonSidebar('))
end = text.index('          const lessonOrder =\n', start)
old_block = text[start:end]
new_block = '''          const isCurrent =
            index ===
            currentIndex;


          const lessonProgress =
            progressByLessonId.get(
              Number(lesson.id)
            ) || null;


          const savedStatus =
            String(
              lessonProgress?.status
              || "not_started"
            );


          const isCompleted =
            savedStatus ===
            "completed";


          const isPartial =
            savedStatus ===
            "partial";


          const isInProgress =
            savedStatus ===
            "in_progress";


          /*
            פתיחה סדרתית:
            - שיעור שהושלם תמיד פתוח לחזרה.
            - שיעור חלקי/בתהליך פתוח להמשך.
            - השיעור הנוכחי פתוח.
            - שיעור חדש נפתח רק אם כל הקודמים הושלמו.
          */

          const previousLessonsCompleted =
            lessons
              .slice(0, index)
              .every(
                previousLesson =>
                  String(
                    progressByLessonId.get(
                      Number(previousLesson.id)
                    )?.status
                    || "not_started"
                  ) === "completed"
              );


          const isLocked =
            !isCurrent
            &&
            !isCompleted
            &&
            !isPartial
            &&
            !isInProgress
            &&
            !previousLessonsCompleted;


          let rowClass =
            "";


          let statusHtml =
            "";


          if(isCurrent){

            rowClass =
              "current";

            statusHtml =
              isCompleted
                ? "✓"
                : isPartial
                  ? "◐"
                  : `<span></span>`;

          }
          else if(isCompleted){

            rowClass =
              "completed";

            statusHtml =
              "✓";

          }
          else if(
            isPartial
            ||
            isInProgress
          ){

            rowClass =
              "partial";

            statusHtml =
              "◐";

          }
          else if(isLocked){

            rowClass =
              "locked";

            statusHtml =
              "🔒";

          }
          else{

            rowClass =
              "available";

            statusHtml =
              "▶";

          }


'''
text = text[:start] + new_block + text[end:]

# Add small visual treatment for partial/available rows without disturbing existing sidebar CSS.
css_marker = '''</style>\n\n\n<script>\nif (navigator.userAgent.includes("Windows")) {'''
css = '''/* REAL UNIT LESSON PROGRESS STATES */
body.lesson-theme-science .lesson-sidebar-row.partial{
  opacity:.92;
}
body.lesson-theme-science .lesson-sidebar-row.partial .lesson-sidebar-status{
  color:#f2bd55;
}
body.lesson-theme-science .lesson-sidebar-row.available .lesson-sidebar-status{
  color:#66d9ff;
}

</style>


<script>
if (navigator.userAgent.includes("Windows")) {'''
if css_marker not in text:
    raise SystemExit('style marker not found')
text = text.replace(css_marker, css, 1)

text = text.replace('IAKIDS • build 0.5.6', 'IAKIDS • build 0.5.7')
text = text.replace('window.IAKIDS_BUILD_VERSION = "0.5.6";', 'window.IAKIDS_BUILD_VERSION = "0.5.7";')

p.write_text(text, encoding='utf-8')
