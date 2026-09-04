from pathlib import Path

# ---------- Sidebar ----------
p = Path('he/workspace/index.html')
text = p.read_text(encoding='utf-8')

start_anchor = '          /*\n            פתיחה סדרתית:'
fn_pos = text.index('async function loadRealLessonSidebar(')
start = text.index(start_anchor, fn_pos)
end = text.index('\n\n          let rowClass =', start)
text = text[:start] + '''          /*
            כל השיעורים פתוחים תמיד.
            סטטוס ההתקדמות משמש להצגה ומעקב בלבד,
            ולא לחסימת גישה לשיעורים.
          */

          const isLocked = false;
''' + text[end:]

old_locked = '''          else if(isLocked){

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
new_unlocked = '''          else{

            rowClass =
              "available";

            statusHtml =
              "▶";

          }
'''
if old_locked not in text:
    raise SystemExit('sidebar locked branch not found')
text = text.replace(old_locked, new_unlocked, 1)

if 'IAKIDS • build 0.6.0' not in text:
    raise SystemExit('expected build 0.6.0 not found')
text = text.replace('IAKIDS • build 0.6.0', 'IAKIDS • build 0.6.1')
text = text.replace('window.IAKIDS_BUILD_VERSION = "0.6.0";', 'window.IAKIDS_BUILD_VERSION = "0.6.1";')
p.write_text(text, encoding='utf-8')

# ---------- Completion screen ----------
p2 = Path('he/workspace/lesson-completion.js')
js = p2.read_text(encoding='utf-8')

old_state = '''              const previousLessonsCompleted =
                lessons
                  .slice(0, index)
                  .every(
                    previousLesson =>
                      String(
                        progressByLessonId.get(Number(previousLesson?.id || 0))?.status
                        || "not_started"
                      ) === "completed"
                  );

              const isNext =
                !isCompleted
                && !isPartial
                && previousLessonsCompleted;

              const stateClass =
                isCompleted
                  ? "completed"
                  : isPartial
                    ? "partial"
                    : isNext
                      ? "next"
                      : "locked";

              const status =
                isCompleted
                  ? (
                      order === currentOrder
                        ? `הושלם • ${score}%`
                        : "הושלם ✓"
                    )
                  : isPartial
                    ? "התחלת את השיעור • אפשר להמשיך"
                    : isNext
                      ? "השיעור הבא"
                      : "טרם נפתח 🔒";

              const button =
                isNext
                  ? `
                    <button
                      type="button"
                      class="lesson-completion-next-btn"
                      data-next-order="${order}"
                    >
                      המשך לשיעור הבא ←
                    </button>
                  `
                  : "";
'''
new_state = '''              const stateClass =
                isCompleted
                  ? "completed"
                  : isPartial
                    ? "partial"
                    : "next";

              const status =
                isCompleted
                  ? (
                      order === currentOrder
                        ? `הושלם • ${score}%`
                        : "הושלם ✓"
                    )
                  : isPartial
                    ? "התחלת את השיעור • אפשר להמשיך"
                    : "טרם התחלת • אפשר לפתוח";

              const buttonLabel =
                isCompleted
                  ? "חזרה לשיעור"
                  : isPartial
                    ? "המשך"
                    : "פתיחה";

              const button = `
                <button
                  type="button"
                  class="lesson-completion-next-btn"
                  data-next-order="${order}"
                >
                  ${buttonLabel}
                </button>
              `;
'''
if old_state not in js:
    raise SystemExit('completion state block not found')
js = js.replace(old_state, new_state, 1)

old_listener = '''  const nextButton =
    visualArea.querySelector(
      ".lesson-completion-next-btn"
    );

  if(
    nextButton
    &&
    nextLesson
  ){

    nextButton.addEventListener(
      "click",
      async () => {

        nextButton.disabled =
          true;

        nextButton.textContent =
          "פותח את השיעור הבא…";

        try{

          await startSelectedUnitLesson(
            nextLesson
          );

        }
        catch(error){

          console.error(
            "START NEXT LESSON FROM COMPLETION FAILED:",
            error
          );

          nextButton.disabled =
            false;

          nextButton.textContent =
            "המשך לשיעור הבא ←";

        }

      }
    );

  }
'''
new_listener = '''  visualArea
    .querySelectorAll(
      ".lesson-completion-next-btn"
    )
    .forEach(button => {

      button.addEventListener(
        "click",
        async () => {

          const order =
            Number(
              button.dataset.nextOrder
            );

          const targetLesson =
            lessons.find(
              lesson =>
                Number(lesson?.lesson_order || 0)
                === order
            );

          if(!targetLesson){
            return;
          }

          const originalText =
            button.textContent;

          button.disabled = true;
          button.textContent = "פותח שיעור…";

          try{

            await startSelectedUnitLesson(
              targetLesson
            );

          }
          catch(error){

            console.error(
              "START LESSON FROM COMPLETION FAILED:",
              error
            );

            button.disabled = false;
            button.textContent = originalText;

          }

        }
      );

    });
'''
if old_listener not in js:
    raise SystemExit('completion listener block not found')
js = js.replace(old_listener, new_listener, 1)

p2.write_text(js, encoding='utf-8')
