from pathlib import Path

p = Path('he/workspace/index.html')
text = p.read_text(encoding='utf-8')

start = text.index('          /*\n            פתיחה סדרתית:', text.index('async function loadRealLessonSidebar('))
end = text.index('\n\n          let rowClass =', start)
text = text[:start] + '''          /*
            כל השיעורים פתוחים תמיד.
            סטטוס ההתקדמות משמש להצגה ומעקב בלבד,
            ולא לחסימת גישה לשיעורים.
          */

          const isLocked = false;
''' + text[end:]

# Replace the final locked/available rendering branch so not_started is always available.
old = '''          else if(isLocked){

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
new = '''          else{

            rowClass =
              "available";

            statusHtml =
              "▶";

          }
'''
if old not in text:
    raise SystemExit('sidebar locked branch not found')
text = text.replace(old, new, 1)

text = text.replace('IAKIDS • build 0.6.0', 'IAKIDS • build 0.6.1')
text = text.replace('window.IAKIDS_BUILD_VERSION = "0.6.0";', 'window.IAKIDS_BUILD_VERSION = "0.6.1";')
p.write_text(text, encoding='utf-8')

p2 = Path('he/workspace/lesson-completion.js')
js = p2.read_text(encoding='utf-8')
old2 = '''              const previousLessonsCompleted =
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
'''
new2 = '''              const isAvailable =
                !isCompleted
                && !isPartial;

              const stateClass =
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

              const button =
                isAvailable
'''
if old2 not in js:
    raise SystemExit('completion locked logic not found')
js = js.replace(old2, new2, 1)

# Make partial lessons clickable too; completed lessons remain status-only here.
old3 = '''                  ? `
                      <button
                        type="button"
                        class="lesson-completion-card-button"
                        data-next-lesson-index="${index}"
                      >
                        המשך
                      </button>
                    `
                  : `
                      <div class="lesson-completion-card-lock">
                        ${
                          isCompleted
                            ? "✓"
                            : "🔒"
                        }
                      </div>
                    `;
'''
new3 = '''                  ? `
                      <button
                        type="button"
                        class="lesson-completion-card-button"
                        data-next-lesson-index="${index}"
                      >
                        פתיחה
                      </button>
                    `
                  : isPartial
                    ? `
                        <button
                          type="button"
                          class="lesson-completion-card-button"
                          data-next-lesson-index="${index}"
                        >
                          המשך
                        </button>
                      `
                    : `
                        <div class="lesson-completion-card-lock">✓</div>
                      `;
'''
if old3 not in js:
    raise SystemExit('completion button block not found')
js = js.replace(old3, new3, 1)
p2.write_text(js, encoding='utf-8')
