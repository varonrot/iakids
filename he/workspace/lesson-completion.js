function getLessonCompletionScore(){
  const raw = String(
    document.getElementById("lessonOverallScore")?.textContent || "0"
  );

  const value = Number(
    raw.replace(/[^0-9.]/g, "")
  );

  return Number.isFinite(value)
    ? Math.max(0, Math.min(100, Math.round(value)))
    : 0;
}

async function showLessonCompletionScreen(){
  const visualArea =
    document.querySelector(".lesson-visual-stage");

  if(!visualArea){
    console.warn(
      "LESSON COMPLETION SCREEN — visual stage not found"
    );

    return false;
  }

  const lessons =
    Array.isArray(window.LESSON_SIDEBAR_ROWS)
      ? [...window.LESSON_SIDEBAR_ROWS]
          .sort(
            (a, b) =>
              Number(a?.lesson_order || 0)
              -
              Number(b?.lesson_order || 0)
          )
      : [];

  const currentOrder =
    Math.max(
      1,
      Number(
        window.SELECTED_UNIT_LESSON?.lesson_order
        || 1
      )
    );

  const currentLesson =
    lessons.find(
      item =>
        Number(item?.lesson_order || 0)
        === currentOrder
    )
    || window.SELECTED_UNIT_LESSON
    || {};

  const nextLesson =
    lessons.find(
      item =>
        Number(item?.lesson_order || 0)
        === currentOrder + 1
    )
    || null;

  const totalLessons =
    Math.max(
      lessons.length,
      currentOrder
    );

  const completedCount =
    Math.min(
      currentOrder,
      totalLessons
    );

  const unitProgress =
    totalLessons
      ? Math.round(
          completedCount
          /
          totalLessons
          * 100
        )
      : 100;

  const score =
    getLessonCompletionScore();

  const unitName =
    String(
      window.SELECTED_UNIT_LESSON?.unit_name
      || window.CURRENT_UNIT?.unit_name
      || "היחידה הנוכחית"
    );

  const lessonName =
    String(
      currentLesson?.lesson_name
      || window.SELECTED_UNIT_LESSON?.lesson_name
      || "השיעור"
    );

  const lessonCards =
    lessons.length
      ? lessons
          .map(
            (lesson, index) => {

              const order =
                Number(
                  lesson?.lesson_order
                  || index + 1
                );

              const title =
                escapeLessonSidebarHtml(
                  lesson?.lesson_name
                  || `שיעור ${order}`
                );

              const isCompleted =
                order <= currentOrder;

              const isNext =
                order === currentOrder + 1;

              const stateClass =
                isCompleted
                  ? "completed"
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

              return `
                <article
                  class="lesson-completion-card ${stateClass}"
                  data-lesson-order="${order}"
                >
                  <div class="lesson-completion-card-number">
                    ${order}
                  </div>

                  <div class="lesson-completion-card-title">
                    ${title}
                  </div>

                  <div class="lesson-completion-card-status">
                    ${status}
                  </div>

                  ${button}
                </article>
              `;

            }
          )
          .join("")
      : `
        <article class="lesson-completion-card completed">
          <div class="lesson-completion-card-number">
            ${currentOrder}
          </div>

          <div class="lesson-completion-card-title">
            ${escapeLessonSidebarHtml(lessonName)}
          </div>

          <div class="lesson-completion-card-status">
            הושלם • ${score}%
          </div>
        </article>
      `;

  visualArea.innerHTML = `
    <section
      class="lesson-completion-screen"
      aria-label="סיום שיעור"
    >
      <div class="lesson-completion-teacher">
        <img
          src="/assets/lesson/lesson-teacher-full-body.png"
          alt="המורה"
        >
      </div>

      <div class="lesson-completion-main">

        <div class="lesson-completion-top">

          <div class="lesson-completion-copy">
            <div class="lesson-completion-kicker">
              ✨ השלמת שיעור
            </div>

            <h2>
              כל הכבוד! סיימת את “${escapeLessonSidebarHtml(lessonName)}”
            </h2>

            <p>
              ממשיכים בתוך היחידה “${escapeLessonSidebarHtml(unitName)}”
            </p>
          </div>

          <div class="lesson-completion-meters">

            <div class="lesson-completion-meter">
              <div
                class="lesson-completion-ring"
                style="--progress:${score * 3.6}deg"
              >
                <strong>${score}%</strong>
              </div>

              <span>הבנה בשיעור</span>
            </div>

            <div class="lesson-completion-stat">
              <strong>${completedCount}/${totalLessons}</strong>
              <span>שיעורים הושלמו</span>
            </div>

            <div class="lesson-completion-meter">
              <div
                class="lesson-completion-ring"
                style="--progress:${unitProgress * 3.6}deg"
              >
                <strong>${unitProgress}%</strong>
              </div>

              <span>התקדמות ביחידה</span>
            </div>

          </div>

        </div>

        <div class="lesson-completion-divider"></div>

        <div class="lesson-completion-unit-title">
          <strong>
            המשך היחידה: ${escapeLessonSidebarHtml(unitName)}
          </strong>

          <small>
            ${
              totalLessons > 6
                ? `גללו כדי לראות את כל ${totalLessons} השיעורים`
                : "בחרו את השיעור הבא"
            }
          </small>
        </div>

        <div class="lesson-completion-lessons-shell">
          <div
            class="lesson-completion-lessons"
            id="lessonCompletionLessons"
          >
            ${lessonCards}
          </div>
        </div>

        <div class="lesson-completion-tip">
          💡 אפשר לחזור לשיעורים קודמים בכל עת כדי לחזק את ההבנה.
        </div>

      </div>
    </section>
  `;

  const nextButton =
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

  console.log(
    "LESSON COMPLETION SCREEN SHOWN",
    {
      currentOrder,
      totalLessons,
      score,
      unitProgress,
      nextLesson
    }
  );

  return true;
}
