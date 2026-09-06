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


/* IAKIDS_AI_WAITING_PANEL_V051 */
function ensureAiTeacherWaitingPanelStyles(){
  if(document.getElementById('iakidsAiWaitingPanelStyles')) return;
  const style = document.createElement('style');
  style.id = 'iakidsAiWaitingPanelStyles';
  style.textContent = `
    .lesson-chat-workspace{position:relative!important;overflow:hidden!important;}
    .lesson-ai-waiting-panel{position:absolute;inset:0;z-index:9999;display:flex;align-items:stretch;justify-content:center;padding:14px;background:radial-gradient(circle at 50% 34%,rgba(74,68,255,.18),transparent 36%),linear-gradient(180deg,#041127 0%,#020b1d 100%);direction:rtl;color:#fff;}
    .lesson-ai-waiting-card{position:relative;width:100%;height:100%;overflow:hidden;border:1px solid rgba(90,159,255,.55);border-radius:24px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:30px 20px 24px;background:radial-gradient(circle at 50% 12%,rgba(112,64,255,.24),transparent 34%),linear-gradient(180deg,rgba(8,22,52,.98),rgba(2,10,27,.99));box-shadow:inset 0 0 0 1px rgba(137,74,255,.13),inset 0 0 38px rgba(60,72,255,.12),0 0 22px rgba(43,120,255,.26),0 0 34px rgba(125,56,255,.18);}
    .lesson-ai-waiting-kicker{position:relative;z-index:5;font-size:17px;font-weight:850;color:#dceaff;margin-bottom:2px;}
    .lesson-ai-waiting-title{position:relative;z-index:5;font-size:34px;line-height:1.05;font-weight:950;margin:0;color:#63d8ff;text-shadow:0 0 18px rgba(70,180,255,.40);}
    .lesson-ai-waiting-subtitle{position:relative;z-index:5;margin-top:10px;color:rgba(223,232,250,.82);font-size:14px;font-weight:650;}
    .lesson-ai-waiting-orbit{position:relative;z-index:4;width:272px;height:272px;flex:0 0 272px;margin:24px 0 20px;display:grid;place-items:center;border-radius:50%;background:radial-gradient(circle,rgba(24,53,117,.70),rgba(8,19,54,.95) 67%);border:3px solid #38c9ff;box-shadow:0 0 0 6px rgba(126,67,255,.28),0 0 32px rgba(51,202,255,.82),0 0 62px rgba(116,56,255,.52),inset 0 0 34px rgba(61,135,255,.26);}
    .lesson-ai-waiting-orbit img{width:244px;height:244px;border-radius:50%;object-fit:cover;object-position:center 18%;position:relative;z-index:3;}
    .lesson-ai-waiting-wave{position:absolute;z-index:2;left:-12%;right:-12%;top:49%;height:190px;pointer-events:none;opacity:.94;filter:drop-shadow(0 0 5px rgba(47,201,255,.80)) drop-shadow(0 0 9px rgba(142,57,255,.70));overflow:visible;}
    .lesson-ai-waiting-wave svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible;}
    .lesson-ai-waiting-wave .wave-line{fill:none;stroke-linecap:round;vector-effect:non-scaling-stroke;stroke-width:2.1;opacity:.88;animation:iakidsWaitingSvgShift 6.8s ease-in-out infinite alternate;}
    .lesson-ai-waiting-wave .wave-line:nth-child(2){animation-duration:7.6s;animation-direction:alternate-reverse;opacity:.70;}
    .lesson-ai-waiting-wave .wave-line:nth-child(3){animation-duration:8.4s;opacity:.54;}
    .lesson-ai-waiting-wave.wave-b{top:51%;opacity:.62;transform:scaleX(1.08);}
    .lesson-ai-waiting-wave.wave-b .wave-line{animation-duration:9s;animation-direction:alternate-reverse;opacity:.45;}
    .lesson-completion-card.partial{border-color:rgba(242,189,85,.55)!important;box-shadow:inset 0 0 0 1px rgba(242,189,85,.10)!important;}
    .lesson-completion-card.partial .lesson-completion-card-status{color:#f2bd55!important;}
    .lesson-ai-waiting-status{position:relative;z-index:5;display:flex;align-items:center;gap:9px;margin-top:4px;padding:10px 18px;border-radius:999px;border:1px solid rgba(74,157,255,.28);background:rgba(7,27,58,.72);color:#cfe5ff;font-size:13px;font-weight:750;}
    .lesson-ai-waiting-dot{width:9px;height:9px;border-radius:50%;background:#42e8a1;box-shadow:0 0 12px #42e8a1;animation:iakidsWaitingPulse 1.8s ease-in-out infinite;}
    @keyframes iakidsWaitingSvgShift{0%{transform:translateX(-10px)}50%{transform:translateX(8px)}100%{transform:translateX(18px)}}
    @keyframes iakidsWaitingPulse{0%,100%{opacity:.55;transform:scale(.8)}50%{opacity:1;transform:scale(1.18)}}
  `;
  document.head.appendChild(style);
}

function showAiTeacherWaitingPanel(){
  const chat = document.querySelector('.lesson-chat-workspace');
  if(!chat) return false;
  ensureAiTeacherWaitingPanelStyles();
  chat.querySelector('.lesson-ai-waiting-panel')?.remove();
  const panel = document.createElement('section');
  panel.className = 'lesson-ai-waiting-panel';
  panel.innerHTML = `
    <div class="lesson-ai-waiting-card">
      <div class="lesson-ai-waiting-kicker">✦ מורה AI ✦</div>
      <h2 class="lesson-ai-waiting-title">בהמתנה ✨</h2>
      <div class="lesson-ai-waiting-subtitle">אני כאן כשתרצו להמשיך ללמוד</div>
      <div class="lesson-ai-waiting-wave" aria-hidden="true">
        <svg viewBox="0 0 1000 190" preserveAspectRatio="none">
          <defs>
            <linearGradient id="iakidsWaveGradientA" x1="0" x2="1">
              <stop offset="0%" stop-color="#36cfff" stop-opacity="0"/>
              <stop offset="18%" stop-color="#36cfff" stop-opacity=".95"/>
              <stop offset="52%" stop-color="#9f57ff" stop-opacity=".95"/>
              <stop offset="84%" stop-color="#36cfff" stop-opacity=".95"/>
              <stop offset="100%" stop-color="#36cfff" stop-opacity="0"/>
            </linearGradient>
          </defs>
          <path class="wave-line" stroke="url(#iakidsWaveGradientA)" d="M0 95 C70 28 140 162 210 95 S350 28 420 95 S560 162 630 95 S770 28 840 95 S930 150 1000 95"/>
          <path class="wave-line" stroke="#8c54ff" d="M0 104 C78 48 145 148 218 96 S360 42 430 100 S572 150 642 96 S782 42 852 99 S942 142 1000 101"/>
          <path class="wave-line" stroke="#37cfff" d="M0 84 C86 142 150 50 224 91 S366 139 438 88 S580 46 650 94 S790 140 858 88 S944 52 1000 90"/>
        </svg>
      </div>
      <div class="lesson-ai-waiting-wave wave-b" aria-hidden="true">
        <svg viewBox="0 0 1000 190" preserveAspectRatio="none">
          <path class="wave-line" stroke="#744dff" d="M0 96 C92 36 170 154 252 96 S420 38 502 96 S668 154 748 96 S914 40 1000 96"/>
          <path class="wave-line" stroke="#2ecfff" d="M0 110 C88 154 164 56 246 102 S410 146 492 98 S656 54 738 102 S906 146 1000 102"/>
          <path class="wave-line" stroke="#a45cff" d="M0 80 C94 128 170 46 252 88 S418 132 500 86 S668 44 750 90 S916 130 1000 88"/>
        </svg>
      </div>
      <div class="lesson-ai-waiting-orbit"><img src="/assets/lesson/lesson-teacher.webp" alt="המורה AI"></div>
      <div class="lesson-ai-waiting-status"><span class="lesson-ai-waiting-dot"></span><span>מוכנה כשתרצו להמשיך</span></div>
    </div>`;
  chat.appendChild(panel);
  return true;
}

function hideAiTeacherWaitingPanel(){
  document.querySelectorAll('.lesson-ai-waiting-panel').forEach(el => el.remove());
}

window.showAiTeacherWaitingPanel = showAiTeacherWaitingPanel;
window.hideAiTeacherWaitingPanel = hideAiTeacherWaitingPanel;

async function refreshKidUnitLessonProgressRows(){
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

  const savedProgressRows =
    Array.isArray(window.LESSON_SIDEBAR_PROGRESS_ROWS)
      ? window.LESSON_SIDEBAR_PROGRESS_ROWS
      : [];

  const progressByLessonId =
    new Map(
      savedProgressRows.map(
        row => [Number(row?.unit_lesson_id || 0), row]
      )
    );

  const completedCount =
    lessons.filter(
      lesson =>
        String(
          progressByLessonId.get(Number(lesson?.id || 0))?.status
          || "not_started"
        ) === "completed"
    ).length;

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

              const savedProgress =
                progressByLessonId.get(
                  Number(lesson?.id || 0)
                ) || null;

              const savedStatus =
                String(
                  savedProgress?.status
                  || "not_started"
                );

              const isCompleted =
                savedStatus === "completed";

              const isPartial =
                savedStatus === "partial"
                || savedStatus === "in_progress";

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

  visualArea
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

  showAiTeacherWaitingPanel();

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


function updateLessonUnitProgressGauge(){
  const gauge =
    document.getElementById("lessonProgressGauge");

  const scoreEl =
    document.getElementById("lessonProgressScore");

  const labelEl =
    document.getElementById("lessonProgressUnitLabel");

  if(!gauge || !scoreEl){
    return;
  }

  const lessons =
    Array.isArray(window.LESSON_SIDEBAR_ROWS)
      ? window.LESSON_SIDEBAR_ROWS
      : [];

  const currentOrder =
    Math.max(
      1,
      Number(
        window.SELECTED_UNIT_LESSON?.lesson_order
        || 1
      )
    );

  const totalLessons =
    Math.max(
      lessons.length,
      currentOrder
    );

  const savedProgressRows =
    Array.isArray(window.LESSON_SIDEBAR_PROGRESS_ROWS)
      ? window.LESSON_SIDEBAR_PROGRESS_ROWS
      : [];

  const completedIds =
    new Set(
      savedProgressRows
        .filter(row => String(row?.status || "") === "completed")
        .map(row => Number(row?.unit_lesson_id || 0))
    );

  const completedCount =
    lessons.filter(
      lesson => completedIds.has(Number(lesson?.id || 0))
    ).length;

  const progress =
    totalLessons > 0
      ? Math.round(
          completedCount / totalLessons * 100
        )
      : 0;

  gauge.style.setProperty(
    "--value",
    String(progress)
  );

  scoreEl.textContent =
    `${progress}%`;

  if(labelEl){
    labelEl.textContent =
      `${completedCount} מתוך ${totalLessons} שיעורים`;
  }
}

if(!window.UNIT_PROGRESS_GAUGE_SYNC_STARTED){
  window.UNIT_PROGRESS_GAUGE_SYNC_STARTED = true;

  window.setInterval(
    updateLessonUnitProgressGauge,
    500
  );
}


/* =====================================================
   HOMEWORK SMART INTRO + HELP CHOICES V1
   Loaded after the main workspace script so it can safely
   override the original homework hand-off function.
===================================================== */
(function(){

  const HELP_CHOICES = [
    {
      id: "understand_question",
      icon: "fa-magnifying-glass",
      label: "להבין מה מבקשים בשאלה",
      childText: "אני רוצה להבין מה מבקשים בשאלה"
    },
    {
      id: "explain_topic",
      icon: "fa-book-open",
      label: "לקבל הסבר על החומר",
      childText: "אני רוצה הסבר על החומר"
    },
    {
      id: "hint",
      icon: "fa-lightbulb",
      label: "לקבל רמז קטן",
      childText: "אני רוצה רמז קטן"
    },
    {
      id: "solve_together",
      icon: "fa-list-ol",
      label: "לפתור יחד שלב־שלב",
      childText: "בואי נפתור יחד שלב־שלב"
    },
    {
      id: "check_answer",
      icon: "fa-circle-check",
      label: "לבדוק תשובה שכתבתי",
      childText: "אני רוצה לבדוק תשובה שכתבתי"
    }
  ];

  let activeHomeworkAnalysis = null;
  let homeworkChoiceBusy = false;

  function cleanHomeworkValue(value){
    const text = String(value || "").trim();
    if(!text || /^(לא ידוע|unknown|null|undefined)$/i.test(text)){
      return "";
    }
    return text;
  }

  function getHomeworkGrade(){
    const raw =
      window.CURRENT_KID?.grade
      ?? window.CURRENT_KID?.age
      ?? 4;

    const grade = Number(raw);
    return Number.isFinite(grade)
      ? Math.max(1, Math.min(6, Math.round(grade)))
      : 4;
  }

  function getHomeworkDetectionSentence(analysis){
    const subject = cleanHomeworkValue(analysis?.subject);
    const topic = cleanHomeworkValue(analysis?.topic);

    const rawConfidence = Number(
      analysis?.confidence
      ?? analysis?.classification_confidence
      ?? analysis?.subject_confidence
    );

    const uncertain =
      Number.isFinite(rawConfidence)
      && rawConfidence > 0
      && rawConfidence < 0.65;

    const verb = uncertain ? "נראה שזה" : "זיהיתי שזה";

    if(subject && topic){
      return `${verb} שיעורי בית ב־${subject} בנושא ${topic}.`;
    }

    if(subject){
      return `${verb} שיעורי בית ב־${subject}.`;
    }

    if(topic){
      return `${verb} שיעורי בית בנושא ${topic}.`;
    }

    return "קראתי את שיעורי הבית שלך.";
  }

  function getHomeworkIntroByGrade(analysis){
    const grade = getHomeworkGrade();
    const detection = getHomeworkDetectionSentence(analysis);

    if(grade <= 2){
      return `${detection}\nאני יכולה לעזור להבין מה מבקשים, להסביר, לתת רמז או לפתור איתך יחד.`;
    }

    if(grade <= 4){
      return `${detection}\nאני יכולה להסביר את השאלה או את החומר, לתת רמז, לפתור יחד או לבדוק תשובה.`;
    }

    return `${detection}\nאפשר להבין את השאלה, לקבל הסבר, רמז, לפתור יחד או לבדוק תשובה.`;
  }

  function ensureHomeworkHelpStyles(){
    if(document.getElementById("iakidsHomeworkHelpChoicesStyles")){
      return;
    }

    const style = document.createElement("style");
    style.id = "iakidsHomeworkHelpChoicesStyles";
    style.textContent = `
      .homework-help-options-row{
        width:100%;
        display:flex;
        justify-content:flex-start;
        direction:rtl;
        padding:0 2px 4px;
      }
      .homework-help-options{
        width:min(100%,390px);
        display:grid;
        gap:7px;
        padding:10px;
        border:1px solid rgba(104,146,226,.25);
        border-radius:16px;
        background:rgba(5,17,38,.72);
        box-shadow:inset 0 0 22px rgba(72,93,255,.07);
      }
      .homework-help-options-title{
        color:#dceaff;
        font-size:12px;
        font-weight:800;
        text-align:right;
        padding:0 3px 2px;
      }
      .homework-help-choice{
        width:100%;
        min-height:39px;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        gap:9px;
        direction:rtl;
        border:1px solid rgba(128,91,255,.62);
        border-radius:11px;
        background:linear-gradient(135deg,rgba(55,35,123,.92),rgba(22,45,91,.92));
        color:#f3f6ff;
        padding:8px 11px;
        font-family:"Heebo",Arial,sans-serif;
        font-size:12px;
        font-weight:800;
        text-align:right;
        cursor:pointer;
        transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease;
      }
      .homework-help-choice:hover{
        transform:translateY(-1px);
        border-color:#5fd8ff;
        box-shadow:0 0 15px rgba(79,173,255,.18);
      }
      .homework-help-choice:disabled{
        opacity:.56;
        cursor:wait;
        transform:none;
      }
      .homework-help-choice i{
        width:20px;
        color:#69d7ff;
        text-align:center;
      }
      body:not(.lesson-theme-science) .homework-help-options{
        background:#fff;
        border-color:#e1dcfb;
        box-shadow:0 8px 24px rgba(65,58,130,.07);
      }
      body:not(.lesson-theme-science) .homework-help-options-title{
        color:#34406b;
      }
      body:not(.lesson-theme-science) .homework-help-choice{
        background:linear-gradient(135deg,#f8f6ff,#eef5ff);
        border-color:#d6ccff;
        color:#3c3973;
      }
    `;

    document.head.appendChild(style);
  }

  function getHomeworkMessagesContainer(){
    return (
      document.querySelector(".lesson-chat-workspace .messages")
      || document.querySelector(".workspace .messages")
      || document.querySelector(".messages")
    );
  }

  function scrollHomeworkChatToBottom(){
    const messages = getHomeworkMessagesContainer();
    if(messages){
      requestAnimationFrame(() => {
        messages.scrollTop = messages.scrollHeight;
      });
    }
  }

  function removeHomeworkHelpOptions(){
    document
      .querySelectorAll(".homework-help-options-row")
      .forEach(el => el.remove());
  }

  function renderHomeworkHelpOptions(){
    const messages = getHomeworkMessagesContainer();
    if(!messages){
      console.warn("HOMEWORK HELP OPTIONS — messages container not found");
      return false;
    }

    ensureHomeworkHelpStyles();
    removeHomeworkHelpOptions();

    const row = document.createElement("div");
    row.className = "homework-help-options-row";

    const panel = document.createElement("div");
    panel.className = "homework-help-options";

    const title = document.createElement("div");
    title.className = "homework-help-options-title";
    title.textContent = "איך תרצה שאעזור?";
    panel.appendChild(title);

    HELP_CHOICES.forEach(choice => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "homework-help-choice";
      button.dataset.helpChoice = choice.id;
      button.innerHTML = `<i class="fa-solid ${choice.icon}" aria-hidden="true"></i><span>${choice.label}</span>`;
      button.addEventListener("click", () => {
        selectHomeworkHelpOption(choice.id);
      });
      panel.appendChild(button);
    });

    row.appendChild(panel);
    messages.appendChild(row);
    scrollHomeworkChatToBottom();
    return true;
  }

  function buildHomeworkContextMessage(analysis){
    return `
הילד העלה צילום של שיעורי הבית.

מקצוע שזוהה:
${cleanHomeworkValue(analysis?.subject) || "לא ידוע"}

נושא שזוהה:
${cleanHomeworkValue(analysis?.topic) || "לא ידוע"}

כיתה:
${getHomeworkGrade()}

תוכן התרגיל שפוענח:
${analysis?.extracted_text || ""}

זהו רק הקשר פנימי לשיחה. אל תיתן עדיין תשובה לתרגיל.
המתן לבחירת סוג העזרה של הילד.
`.trim();
  }

  async function primeHomeworkTutorContext(analysis){
    try{
      const { data: sessionData } = await sb.auth.getSession();
      const session = sessionData.session;
      if(!session || !CURRENT_KID?.id){
        return;
      }

      const response = await fetch(
        `${TUTOR_API_BASE}/api/tutor/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${session.access_token}`
          },
          body: JSON.stringify({
            message: buildHomeworkContextMessage(analysis),
            kid_id: CURRENT_KID.id
          })
        }
      );

      if(!response.ok){
        console.warn("HOMEWORK CONTEXT PRIME FAILED:", response.status);
        return;
      }

      const data = await response.json();
      if(data?.session_id && typeof currentSessionId !== "undefined"){
        currentSessionId = data.session_id;
      }
    }
    catch(error){
      console.warn("HOMEWORK CONTEXT PRIME WARNING:", error);
    }
  }

  function getChoiceInstruction(choiceId){
    switch(choiceId){
      case "understand_question":
        return "עזור לילד להבין מה בדיוק מבקשים בשאלה. פרק את הדרישה למילים קצרות וברורות. אל תפתור את התרגיל במקומו.";
      case "explain_topic":
        return "הסבר בקצרה ובשפה המתאימה לכיתה את החומר שצריך לדעת כדי לענות. אחר כך שאל שאלה קצרה שבודקת הבנה.";
      case "hint":
        return "תן רמז קטן אחד בלבד שמקדם את הילד בלי לחשוף את התשובה. המתן לתשובה שלו.";
      case "solve_together":
        return "פתור יחד עם הילד שלב־שלב. בכל פעם תן רק צעד אחד ושאל אותו מה לדעתו הצעד הבא.";
      case "check_answer":
        return "בקש מהילד לכתוב או לומר את התשובה שכבר הכין. אל תנסח תשובה במקומו לפני ששלח את התשובה שלו.";
      default:
        return "עזור לילד להבין ולפתור בעצמו, בלי לתת מיד את התשובה הסופית.";
    }
  }

  async function runHomeworkChoiceWithTutor(choice){
    const analysis = activeHomeworkAnalysis || window.CURRENT_HOMEWORK_ANALYSIS;
    if(!analysis){
      addMessage("assistant", "לא מצאתי את התרגיל שהעלית. אפשר להעלות אותו שוב?");
      return;
    }

    const { data: sessionData } = await sb.auth.getSession();
    const session = sessionData.session;
    if(!session){
      throw new Error("No active session");
    }

    const message = `
אנחנו ממשיכים עם שיעורי הבית שכבר נותחו.

מקצוע: ${cleanHomeworkValue(analysis.subject) || "לא ידוע"}
נושא: ${cleanHomeworkValue(analysis.topic) || "לא ידוע"}
כיתה: ${getHomeworkGrade()}

הילד בחר: ${choice.label}

${getChoiceInstruction(choice.id)}

תוכן התרגיל:
${analysis.extracted_text || ""}

דבר בעברית קצרה וברורה המותאמת לכיתה ${getHomeworkGrade()}.
`.trim();

    const response = await fetch(
      `${TUTOR_API_BASE}/api/tutor/chat`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          message,
          kid_id: CURRENT_KID.id
        })
      }
    );

    if(!response.ok){
      const errorText = await response.text();
      console.error("HOMEWORK HELP CHOICE ERROR:", response.status, errorText);
      throw new Error("Homework help choice failed");
    }

    const data = await response.json();

    if(data?.session_id && typeof currentSessionId !== "undefined"){
      currentSessionId = data.session_id;
    }

    if(
      data?.sequence
      && Array.isArray(data.sequence)
      && window.lessonRenderer
    ){
      await unlockLessonAudio();
      await window.lessonRenderer.run({
        sequence: data.sequence,
        wait_for_answer: data.wait_for_answer,
        speech: data.speech
      });
      return;
    }

    if(data?.message || data?.text || data?.response){
      addMessage("assistant", data.message || data.text || data.response);
      return;
    }

    console.error("Invalid homework tutor response:", data);
    addMessage("assistant", "אני כאן. נסה לבחור שוב איך תרצה שאעזור.");
  }

  async function selectHomeworkHelpOption(choiceId){
    if(homeworkChoiceBusy){
      return;
    }

    const choice = HELP_CHOICES.find(item => item.id === choiceId);
    if(!choice){
      return;
    }

    homeworkChoiceBusy = true;

    const buttons = document.querySelectorAll(".homework-help-choice");
    buttons.forEach(button => {
      button.disabled = true;
    });

    addMessage("user", choice.childText);
    removeHomeworkHelpOptions();

    try{
      await runHomeworkChoiceWithTutor(choice);
    }
    catch(error){
      console.error("HOMEWORK HELP OPTION FAILED:", error);
      addMessage("assistant", "לא הצלחתי להתחיל את העזרה. נסה שוב בעוד רגע.");
      renderHomeworkHelpOptions();
    }
    finally{
      homeworkChoiceBusy = false;
    }
  }

  async function smartHomeworkAnalysisIntro(analysis){
    activeHomeworkAnalysis = analysis || null;
    window.CURRENT_HOMEWORK_ANALYSIS = analysis || null;

    addMessage("user", "📷 העליתי צילום של שיעורי הבית");
    addMessage("assistant", getHomeworkIntroByGrade(analysis));
    renderHomeworkHelpOptions();

    /*
      שומרים גם את הפענוח בהקשר של מנוע המורה כדי שהילד יוכל
      לכתוב תשובה חופשית במקום ללחוץ על כפתור ועדיין המורה תדע
      לאיזה דף שיעורי בית הוא מתייחס.
    */
    await primeHomeworkTutorContext(analysis);
  }

  window.getHomeworkIntroByGrade = getHomeworkIntroByGrade;
  window.renderHomeworkHelpOptions = renderHomeworkHelpOptions;
  window.selectHomeworkHelpOption = selectHomeworkHelpOption;
  window.sendHomeworkAnalysisToTutor = smartHomeworkAnalysisIntro;

  console.log("HOMEWORK SMART INTRO V1 READY");

})();
