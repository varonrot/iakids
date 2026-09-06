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

  function normalizeHomeworkSubjectForDisplay(value){
    const raw = cleanHomeworkValue(value);
    const lower = raw.toLowerCase();

    if(!raw) return "";
    if(/תנ[״\"]?ך|bible|biblical|scripture/.test(lower) || /תנ[״\"]?ך/.test(raw)) return "תנ״ך";
    if(/science|מדע/.test(lower) || raw.includes("מדעים")) return "מדעים";
    if(/math|mathematics|מתמט/.test(lower) || raw.includes("חשבון")) return "מתמטיקה";
    if(/hebrew|עברית/.test(lower)) return "עברית";
    if(/english|אנגלית/.test(lower)) return "אנגלית";
    if(/history|היסטור/.test(lower)) return "היסטוריה";
    if(/literature/.test(lower)) return "ספרות";
    if(/reading comprehension/.test(lower)) return "הבנת הנקרא";
    if(/geograph|גאוגר|גיאוגר/.test(lower)) return "גאוגרפיה";

    return raw;
  }

  function normalizeHomeworkTopicForDisplay(value){
    const raw = cleanHomeworkValue(value);
    const lower = raw.toLowerCase();

    if(!raw) return "";
    if((/genesis|בראשית/.test(lower) || raw.includes("בראשית")) && (/creation|בריאת/.test(lower) || raw.includes("בריאת"))){
      return "בריאת העולם";
    }
    if(/creation of the world|creation of world/.test(lower)) return "בריאת העולם";
    if(/ecosystem/.test(lower)) return "מערכות אקולוגיות";
    if(/reading comprehension/.test(lower)) return "הבנת הנקרא";
    if(/abraham/.test(lower) && /guest|hospitality/.test(lower)) return "אברהם מכניס אורחים";

    return raw;
  }

  function resolveHomeworkClassification(analysis){
    const extracted = String(analysis?.extracted_text || "").trim();
    const rawSubject = cleanHomeworkValue(analysis?.subject);
    const rawTopic = cleanHomeworkValue(analysis?.topic);
    const combined = `${extracted}\n${rawSubject}\n${rawTopic}`;
    const lower = combined.toLowerCase();

    let subject = normalizeHomeworkSubjectForDisplay(rawSubject);
    let topic = normalizeHomeworkTopicForDisplay(rawTopic);
    let taskType = "";

    /* Explicit worksheet headings/content outrank a generic AI label such as Literature. */
    const hasTanakhEvidence =
      /תנ[״"']?ך/.test(combined)
      || /שיעורי\s+בית\s+בתנ/.test(combined)
      || /פרשת\s+/.test(combined)
      || /ספר\s+(בראשית|שמות|ויקרא|במדבר|דברים)/.test(combined)
      || /\b(bible|biblical|scripture|tanakh)\b/i.test(combined);

    if(hasTanakhEvidence){
      subject = "תנ״ך";
    }

    if(
      /אברהם\s+מכניס\s+אורחים/.test(combined)
      || (combined.includes("אברהם") && /אורח/.test(combined))
    ){
      topic = "אברהם מכניס אורחים";
    }
    else if(
      (combined.includes("בראשית") || /genesis/i.test(combined))
      &&
      (combined.includes("בריאת") || /creation/i.test(combined))
    ){
      topic = "בריאת העולם";
    }

    const readingTask =
      /קטע\s+קריאה|הבנת\s+הנקרא|reading\s+comprehension|literature/i.test(combined);

    if(readingTask){
      taskType = "הבנת הנקרא";
    }

    /* Literature/Reading Comprehension describes the task, not the school subject. */
    if(
      subject
      &&
      /^(literature|reading comprehension)$/i.test(subject)
      &&
      hasTanakhEvidence
    ){
      subject = "תנ״ך";
    }

    if(
      topic
      &&
      /^(literature|reading comprehension)$/i.test(topic)
    ){
      topic = "";
    }

    return {
      subject,
      topic,
      taskType
    };
  }

  function getHomeworkDetectionSentence(analysis){
    const classification = resolveHomeworkClassification(analysis);
    const subject = classification.subject;
    const topic = classification.topic;

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
      return `${detection}\nאני יכולה להסביר, לתת רמז או לפתור איתך יחד.`;
    }

    if(grade <= 4){
      return `${detection}\nאני יכולה להסביר, לתת רמז, לפתור יחד או לבדוק תשובה.`;
    }

    return `${detection}\nאפשר לקבל הסבר, רמז, לפתור יחד או לבדוק תשובה.`;
  }

  function ensureHomeworkHelpStyles(){
    if(document.getElementById("iakidsHomeworkHelpChoicesStyles")){
      return;
    }

    const style = document.createElement("style");
    style.id = "iakidsHomeworkHelpChoicesStyles";
    style.textContent = `
      .homework-reading-status-row,
      .homework-detection-row{
        width:100%;
        display:flex;
        justify-content:flex-start;
        direction:rtl;
        padding:2px 2px 5px;
      }
      .homework-reading-status-card,
      .homework-detection-card{
        width:min(94%,350px);
        display:flex;
        align-items:flex-start;
        gap:11px;
        padding:13px 14px;
        border:1px solid rgba(85,177,255,.34);
        border-radius:17px;
        background:
          radial-gradient(circle at 88% 0%,rgba(94,72,255,.18),transparent 44%),
          linear-gradient(145deg,rgba(10,29,61,.96),rgba(5,19,43,.98));
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.035),
          0 9px 24px rgba(0,4,20,.28),
          0 0 18px rgba(50,157,255,.07);
        color:#fff;
        text-align:right;
      }
      .homework-reading-status-icon,
      .homework-detection-icon{
        width:38px;
        height:38px;
        flex:0 0 38px;
        display:grid;
        place-items:center;
        border-radius:12px;
        border:1px solid rgba(97,202,255,.36);
        background:linear-gradient(145deg,rgba(32,95,166,.66),rgba(74,48,170,.62));
        color:#77e3ff;
        box-shadow:0 0 15px rgba(70,201,255,.12);
        font-size:15px;
      }
      .homework-detection-icon{
        color:#7df0bb;
        border-color:rgba(91,231,170,.34);
        background:linear-gradient(145deg,rgba(18,102,85,.60),rgba(36,61,126,.68));
      }
      .homework-status-copy,
      .homework-detection-copy{
        flex:1;
        min-width:0;
      }
      .homework-status-title,
      .homework-detection-title{
        margin:0 0 3px;
        color:#f6f9ff;
        font:850 13px/1.35 "Heebo",Arial,sans-serif;
      }
      .homework-status-text,
      .homework-detection-text{
        color:#aecaeb;
        font:600 11.5px/1.55 "Heebo",Arial,sans-serif;
      }
      .homework-status-progress{
        width:100%;
        height:3px;
        margin-top:9px;
        overflow:hidden;
        border-radius:999px;
        background:rgba(86,126,187,.16);
      }
      .homework-status-progress::after{
        content:"";
        display:block;
        width:38%;
        height:100%;
        border-radius:inherit;
        background:linear-gradient(90deg,#5c63ff,#55d8ff);
        box-shadow:0 0 9px rgba(85,216,255,.55);
        animation:homeworkStatusScan 1.35s ease-in-out infinite;
      }
      .homework-detection-tags{
        display:flex;
        flex-wrap:wrap;
        gap:5px;
        margin-top:8px;
      }
      .homework-detection-tag{
        display:inline-flex;
        align-items:center;
        min-height:24px;
        padding:3px 8px;
        border:1px solid rgba(98,182,255,.25);
        border-radius:999px;
        background:rgba(24,57,105,.46);
        color:#d9edff;
        font:750 10.5px "Heebo",Arial,sans-serif;
      }
      @keyframes homeworkStatusScan{
        0%{transform:translateX(165%)}
        50%{transform:translateX(25%)}
        100%{transform:translateX(-165%)}
      }
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
      .homework-help-icon{
        width:24px;
        height:24px;
        flex:0 0 24px;
        display:grid;
        place-items:center;
        border-radius:8px;
        border:1px solid rgba(96,211,255,.42);
        background:linear-gradient(145deg,rgba(36,119,188,.42),rgba(94,54,191,.42));
        color:#78e1ff;
        font:900 14px/1 "Heebo",Arial,sans-serif;
        box-shadow:inset 0 0 10px rgba(76,181,255,.10),0 0 8px rgba(82,164,255,.10);
      }
      .homework-detection-teacher{
        width:44px;
        height:44px;
        flex:0 0 44px;
        border-radius:50%;
        object-fit:cover;
        object-position:center 18%;
        border:1px solid rgba(105,215,255,.58);
        background:#07182f;
        box-shadow:0 0 13px rgba(73,183,255,.24);
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

  function removeHomeworkReadingStatus(){
    document.querySelectorAll('.homework-reading-status-row').forEach(el => el.remove());
  }

  function showHomeworkReadingStatus(){
    const messages = getHomeworkMessagesContainer();
    if(!messages) return false;

    ensureHomeworkHelpStyles();
    removeHomeworkReadingStatus();

    const row = document.createElement('div');
    row.className = 'homework-reading-status-row';
    row.innerHTML = `
      <div class="homework-reading-status-card" role="status" aria-live="polite">
        <div class="homework-reading-status-icon"><i class="fa-solid fa-wand-magic-sparkles"></i></div>
        <div class="homework-status-copy">
          <div class="homework-status-title">קיבלתי את התרגיל</div>
          <div class="homework-status-text">אני קוראת את הדף ומזהה את המקצוע, הנושא ומה מבקשים.</div>
          <div class="homework-status-progress" aria-hidden="true"></div>
        </div>
      </div>`;

    messages.appendChild(row);
    requestAnimationFrame(() => { messages.scrollTop = 0; });
    return true;
  }

  function renderHomeworkDetectionCard(analysis){
    const messages = getHomeworkMessagesContainer();
    if(!messages) return false;

    ensureHomeworkHelpStyles();
    document.querySelectorAll('.homework-detection-row').forEach(el => el.remove());

    const classification = resolveHomeworkClassification(analysis);
    const subject = classification.subject;
    const topic = classification.topic;
    const taskType = classification.taskType;
    const sentence = getHomeworkIntroByGrade(analysis);
    const parts = sentence.split('\n');
    const mainLine = parts[0] || 'זיהיתי את שיעורי הבית.';
    const helpLine = parts.slice(1).join(' ') || getHomeworkGenderLanguage().howHelp;

    const row = document.createElement('div');
    row.className = 'homework-detection-row';
    row.innerHTML = `
      <div class="homework-detection-card">
        <img class="homework-detection-teacher" src="/assets/lesson/lesson-teacher.webp" alt="המורה AI">
        <div class="homework-detection-icon"><span aria-hidden="true">✓</span></div>
        <div class="homework-detection-copy">
          <div class="homework-detection-title">${mainLine}</div>
          <div class="homework-detection-text">${helpLine}</div>
          <div class="homework-detection-tags">
            ${subject ? `<span class="homework-detection-tag">${subject}</span>` : ''}
            ${topic ? `<span class="homework-detection-tag">${topic}</span>` : ''}
            ${taskType ? `<span class="homework-detection-tag">${taskType}</span>` : ''}
          </div>
        </div>
      </div>`;

    messages.appendChild(row);
    return true;
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
    title.textContent = getHomeworkGenderLanguage().howHelp;
    panel.appendChild(title);

    HELP_CHOICES.forEach(choice => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "homework-help-choice";
      button.dataset.helpChoice = choice.id;
      const helpIconMap = {
        understand_question: "?",
        explain_topic: "▤",
        hint: "✦",
        solve_together: "→",
        check_answer: "✓"
      };
      button.innerHTML = `<span class="homework-help-icon" aria-hidden="true">${helpIconMap[choice.id] || "•"}</span><span>${choice.label}</span>`;
      button.addEventListener("click", () => {
        selectHomeworkHelpOption(choice.id);
      });
      panel.appendChild(button);
    });

    row.appendChild(panel);
    messages.appendChild(row);

    /* Keep the detected subject/topic visible at the top of the chat. */
    requestAnimationFrame(() => {
      messages.scrollTop = 0;
    });

    return true;
  }

  function getHomeworkKidName(analysis=null){
    const sourceAnalysis = analysis || activeHomeworkAnalysis || window.CURRENT_HOMEWORK_ANALYSIS || {};
    const kid = window.CURRENT_KID || window.SELECTED_KID || window.currentKid || window.selectedKid || {};

    const candidates = [
      sourceAnalysis?.child_name,
      sourceAnalysis?.kid_name,
      sourceAnalysis?.profile?.child_name,
      window.CURRENT_HOMEWORK_CHILD_NAME,
      kid?.child_name,
      kid?.name,
      kid?.first_name,
      kid?.display_name,
      kid?.full_name,
      kid?.kid_name,
      kid?.nickname,
      window.CURRENT_KID_NAME,
      window.currentKidName,
      window.selectedKidName
    ];

    for(const candidate of candidates){
      const value = String(candidate || "").trim();
      if(value) return value.split(/\s+/)[0];
    }

    const selectors = [
      '#currentKidName',
      '.current-kid-name',
      '[data-current-kid-name]',
      '[data-kid-name]',
      '.kid-name'
    ];

    for(const selector of selectors){
      const element = document.querySelector(selector);
      const value = String(
        element?.dataset?.currentKidName
        || element?.dataset?.kidName
        || element?.textContent
        || ""
      ).trim();
      if(value) return value.split(/\s+/)[0];
    }

    return "";
  }

  function getHomeworkKidGender(analysis=null){
    const sourceAnalysis = analysis || activeHomeworkAnalysis || window.CURRENT_HOMEWORK_ANALYSIS || {};
    const kid = window.CURRENT_KID || window.SELECTED_KID || window.currentKid || window.selectedKid || {};

    const raw = String(
      sourceAnalysis?.gender
      || sourceAnalysis?.child_gender
      || sourceAnalysis?.profile?.gender
      || window.CURRENT_HOMEWORK_CHILD_GENDER
      || kid?.gender
      || kid?.sex
      || window.CURRENT_KID_GENDER
      || ""
    ).trim().toLowerCase();

    if(["female", "f", "girl", "בת", "נקבה"].includes(raw)) return "female";
    if(["male", "m", "boy", "בן", "זכר"].includes(raw)) return "male";
    return "unknown";
  }

  function getHomeworkGenderLanguage(analysis=null){
    const resolvedGender = getHomeworkKidGender(analysis);
    const female = resolvedGender === "female";
    return {
      gender: female ? "נקבה" : (resolvedGender === "male" ? "זכר" : "לא ידוע"),
      howHelp: female ? "איך תרצי שאעזור?" : "איך תרצה שאעזור?",
      tryAgain: female ? "נסי" : "נסה",
      childLabel: female ? "הילדה" : "הילד"
    };
  }

  function getHomeworkSpokenIntro(analysis){
    const classification = resolveHomeworkClassification(analysis);
    const subject = classification.subject;
    const topic = classification.topic;
    const kidName = getHomeworkKidName(analysis);
    const language = getHomeworkGenderLanguage(analysis);

    const greeting = kidName
      ? `היי ${kidName}, `
      : "היי, ";

    if(subject && topic){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject} בנושא ${topic}. ${language.howHelp}`;
    }

    if(subject){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject}. ${language.howHelp}`;
    }

    if(topic){
      return `${greeting}זיהיתי את הנושא ${topic}. ${language.howHelp}`;
    }

    return `${greeting}זיהיתי את שיעורי הבית. ${language.howHelp}`;
  }

  async function playHomeworkTeacherAudio(text){
    const spokenText = String(text || "")
      .replace(/\s+/g, " ")
      .trim();

    if(!spokenText){
      return false;
    }

    if(!window.lessonRenderer){
      console.warn("HOMEWORK AUDIO — lessonRenderer not ready");
      return false;
    }

    try{
      /* Use exactly the same browser audio unlock and Gemini TTS path as lessons. */
      if(typeof unlockLessonAudio === "function"){
        await unlockLessonAudio();
      }

      const audioUrl = await window.lessonRenderer.preloadAudioWithRetry(
        spokenText,
        3
      );

      if(!audioUrl){
        console.warn("HOMEWORK AUDIO — no audio URL returned");
        return false;
      }

      await window.lessonRenderer.playAudioUrl(audioUrl);
      return true;
    }
    catch(error){
      /* Audio must never block the homework flow. */
      console.warn("HOMEWORK AUDIO PLAYBACK WARNING:", error);
      return false;
    }
  }

  function buildHomeworkContextMessage(analysis){
    const classification = resolveHomeworkClassification(analysis);
    const kidName = getHomeworkKidName(analysis) || "לא ידוע";
    const language = getHomeworkGenderLanguage(analysis);
    return `
הילד/ה העלה/תה צילום של שיעורי הבית.

שם הילד/ה:
${kidName}

מגדר:
${language.gender}

חובת פנייה:
אם המגדר הוא נקבה, פנה תמיד בלשון נקבה (את, תרצי, נסי, כתבי, חשבי). אם המגדר הוא זכר, פנה בלשון זכר. אל תנחש מגדר לפי השם.

כלל שיעורי בית מחייב:
המטרה היא להגיע לתשובה על השאלה שמופיעה בדף, לא לנהל שיחה כללית סביב הנושא. כל הסבר, רמז או שאלת ביניים חייבים לקדם ישירות לתשובה לשאלה הנוכחית. אל תשאל שאלות על חיי הילד/ה, ערכים, רגשות או דוגמאות אישיות אלא אם השאלה בדף עצמה מבקשת זאת. אחרי לכל היותר 1-2 שאלות הכוונה, החזר את הילד/ה לניסוח תשובה לשאלה המקורית.

מקצוע שזוהה:
${classification.subject || "לא ידוע"}

נושא שזוהה:
${classification.topic || "לא ידוע"}

סוג משימה:
${classification.taskType || "לא ידוע"}

כיתה:
${getHomeworkGrade()}

תוכן התרגיל שפוענח:
${analysis?.extracted_text || ""}

זהו רק הקשר פנימי לשיחה. אל תיתן עדיין תשובה לתרגיל.
המתן לבחירת סוג העזרה של הילד/ה.
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

  function extractFirstHomeworkQuestion(text){
    const raw = String(text || "").replace(/\r/g, "\n").trim();
    if(!raw) return "";

    const lines = raw
      .split(/\n+/)
      .map(line => line.trim())
      .filter(Boolean);

    /* Prefer an explicitly numbered first question. */
    const numbered = lines.find(line => /^\s*(?:1[.)\-:]|1\s)[\s\S]*/.test(line));
    if(numbered){
      return numbered.replace(/^\s*1[.)\-:]?\s*/, "").trim();
    }

    /* Otherwise use the first line that is clearly a question. */
    const questionLine = lines.find(line => /[?？]$/.test(line));
    if(questionLine){
      return questionLine;
    }

    return lines[0] || "";
  }

  function getChoiceInstruction(choiceId){
    switch(choiceId){
      case "understand_question":
        return "התמקד אך ורק בשאלה הראשונה שעדיין לא נענתה. אסור להקריא, להעתיק או לסכם את כל שאלות הדף. הסבר במשפט קצר מה השאלה מבקשת. לאחר מכן שאל שאלה מכוונת אחת בלבד שמבוססת על קטע הקריאה ומקדמת ישירות לתשובה. אחרי תשובת הילד/ה, חזור מיד לשאלה המקורית ובקש לנסח תשובה מלאה. אל תעבור לנושאים כלליים, ערכיים או לחיי הילד/ה אלא אם זה כתוב במפורש בשאלה.";
      case "explain_topic":
        return "הסבר בקצרה רק את הידע שצריך כדי לענות על השאלה הנוכחית בדף. אל תפתח שיחה כללית, ערכית או אישית ואל תשאל על חיי הילד/ה. אחרי ההסבר חזור מיד לשאלה המקורית ובקש מהילד/ה לנסח תשובה קצרה אליה.";
      case "hint":
        return "תן רמז קטן אחד בלבד שמתייחס ישירות לשאלה הנוכחית בדף. אל תשאל שאלות כלליות או שאלות על חיי הילד/ה. מיד אחרי הרמז בקש מהילד/ה לנסות לענות על השאלה המקורית.";
      case "solve_together":
        return "עזור לפתור את השאלה הנוכחית בדף שלב־שלב. כל צעד חייב לקדם ישירות לניסוח תשובה לשאלה המקורית. אל תסטה לשאלות ערכיות, אישיות או כלליות שאינן נדרשות על ידי השאלה. אחרי לכל היותר שני צעדי הכוונה, בקש מהילד/ה לנסח את התשובה לשאלה עצמה.";
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

    const firstQuestion =
      choice.id === "understand_question"
        ? extractFirstHomeworkQuestion(analysis.extracted_text)
        : "";

    const classification = resolveHomeworkClassification(analysis);
    const kidName = getHomeworkKidName(analysis) || "לא ידוע";
    const language = getHomeworkGenderLanguage(analysis);
    const currentQuestion = extractFirstHomeworkQuestion(analysis.extracted_text) || "לא זוהתה שאלה";

    const message = `
שאלת שיעורי הבית הנוכחית:
${currentQuestion}

מטרת הדיאלוג המחייבת:
להוביל את הילד/ה לענות על השאלה הזאת עצמה. אין לסטות לשאלות כלליות או אישיות שאינן נדרשות כדי לענות עליה.

שם הילד/ה: ${kidName}
מגדר: ${language.gender}
חובת פנייה: פנה בהתאם למגדר הרשום. אם נקבה השתמש בלשון נקבה (את/תרצי/נסי/כתבי/חשבי); אם זכר השתמש בלשון זכר. אל תנחש מגדר לפי השם.

אנחנו ממשיכים עם שיעורי הבית שכבר נותחו.

מקצוע: ${classification.subject || "לא ידוע"}
נושא: ${classification.topic || "לא ידוע"}
סוג משימה: ${classification.taskType || "לא ידוע"}
כיתה: ${getHomeworkGrade()}

הילד בחר: ${choice.label}

${getChoiceInstruction(choice.id)}

${firstQuestion ? `השאלה הראשונה בלבד שעליה עובדים עכשיו:
${firstQuestion}

` : ""}תוכן התרגיל המלא הוא הקשר פנימי בלבד. אל תקריא אותו לילד ואל תעבור על כל השאלות:
${analysis.extracted_text || ""}

דבר בעברית קצרה וברורה המותאמת לכיתה ${getHomeworkGrade()}.
במצב "להבין מה מבקשים בשאלה" התגובה הראשונה חייבת להתייחס רק לשאלה הראשונה, בלי רשימה של שאלות אחרות.
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
      const homeworkReply = data.message || data.text || data.response;
      addMessage("assistant", homeworkReply);
      await playHomeworkTeacherAudio(homeworkReply);
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

    if(choice.id === "check_answer"){
      setHomeworkSidebarStep(5);
    }
    else if(choice.id === "understand_question"){
      setHomeworkSidebarStep(3);
    }
    else{
      setHomeworkSidebarStep(4);
    }

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

  function setHomeworkSidebarStep(stepNumber){
    const steps = document.querySelectorAll('.homework-sidebar-step');
    if(!steps.length) return;

    steps.forEach(step => step.classList.remove('active'));
    const index = Math.max(0, Math.min(steps.length - 1, Number(stepNumber || 1) - 1));
    steps[index]?.classList.add('active');
  }

  async function smartHomeworkAnalysisIntro(analysis){
    activeHomeworkAnalysis = analysis || null;
    window.CURRENT_HOMEWORK_ANALYSIS = analysis || null;

    if(analysis?.child_name){
      window.CURRENT_HOMEWORK_CHILD_NAME = String(analysis.child_name).trim();
    }
    if(analysis?.gender || analysis?.child_gender){
      window.CURRENT_HOMEWORK_CHILD_GENDER = String(analysis.gender || analysis.child_gender).trim().toLowerCase();
    }

    console.log("HOMEWORK PROFILE FROM ANALYZER:", {
      child_name: analysis?.child_name || null,
      gender: analysis?.gender || analysis?.child_gender || null
    });

    setHomeworkSidebarStep(2);
    removeHomeworkReadingStatus();
    renderHomeworkDetectionCard(analysis);
    renderHomeworkHelpOptions();

    /* Speak only the teacher's short intro — not tags/buttons/loading text. */
    playHomeworkTeacherAudio(
      getHomeworkSpokenIntro(analysis)
    );

    const messages = getHomeworkMessagesContainer();
    if(messages){
      requestAnimationFrame(() => { messages.scrollTop = 0; });
    }

    /*
      שומרים גם את הפענוח בהקשר של מנוע המורה כדי שהילד יוכל
      לכתוב תשובה חופשית במקום ללחוץ על כפתור ועדיין המורה תדע
      לאיזה דף שיעורי בית הוא מתייחס.
    */
    await primeHomeworkTutorContext(analysis);
  }

  window.showHomeworkStatus = function(){
    return showHomeworkReadingStatus();
  };

  window.getHomeworkKidName = getHomeworkKidName;
  window.getHomeworkKidGender = getHomeworkKidGender;
  window.playHomeworkTeacherAudio = playHomeworkTeacherAudio;
  window.getHomeworkIntroByGrade = getHomeworkIntroByGrade;
  window.renderHomeworkHelpOptions = renderHomeworkHelpOptions;
  window.selectHomeworkHelpOption = selectHomeworkHelpOption;
  window.sendHomeworkAnalysisToTutor = smartHomeworkAnalysisIntro;

  console.log("HOMEWORK SMART INTRO V1 READY");

})();
