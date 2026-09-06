window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.20";
/*
  IAKIDS workspace extension loader.
  The original lesson-completion implementation is preserved in
  lesson-completion-core.js. After it loads, this file adds the new
  homework workspace routing without duplicating the main workspace HTML.
*/
(function(){
  const core = document.createElement("script");
  core.src = "/he/workspace/lesson-completion-core.js?v=0720";
  core.async = false;

  core.onload = function(){
    installHomeworkLessonWorkspace();
  };

  core.onerror = function(error){
    console.error("LESSON COMPLETION CORE FAILED TO LOAD", error);
  };

  document.head.appendChild(core);
})();

function installHomeworkLessonWorkspace(){
  if(window.__HOMEWORK_LESSON_WORKSPACE_V1){
    return;
  }

  window.__HOMEWORK_LESSON_WORKSPACE_V1 = true;

  const originalShowLearning = window.showLearning;

  if(typeof originalShowLearning !== "function"){
    console.error("HOMEWORK WORKSPACE: showLearning was not found");
    return;
  }

  function ensureStyles(){
    if(document.getElementById("homeworkLessonWorkspaceStyles")){
      return;
    }

    const style = document.createElement("style");
    style.id = "homeworkLessonWorkspaceStyles";
    style.textContent = `
      body.homework-lesson-mode .lesson-visual-stage{
        position:relative!important;
        overflow:hidden!important;
        background:
          radial-gradient(circle at 50% 18%,rgba(67,124,255,.15),transparent 38%),
          linear-gradient(180deg,#07152c 0%,#031022 100%)!important;
      }

      .homework-stage-shell{
        position:absolute;
        inset:0;
        display:flex;
        align-items:center;
        justify-content:center;
        padding:28px;
        direction:rtl;
      }

      .homework-upload-card{
        width:min(720px,92%);
        min-height:390px;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        text-align:center;
        padding:36px 34px;
        border:1px solid rgba(77,158,255,.46);
        border-radius:26px;
        background:
          radial-gradient(circle at 50% 10%,rgba(104,72,255,.22),transparent 40%),
          linear-gradient(180deg,rgba(8,27,58,.97),rgba(4,15,34,.98));
        box-shadow:
          inset 0 0 0 1px rgba(131,87,255,.08),
          inset 0 0 32px rgba(40,104,255,.08),
          0 18px 46px rgba(0,4,20,.38),
          0 0 28px rgba(37,134,255,.12);
        color:#fff;
      }

      .homework-upload-icon{
        width:92px;
        height:92px;
        display:grid;
        place-items:center;
        border-radius:25px;
        margin-bottom:18px;
        border:1px solid rgba(94,191,255,.55);
        background:linear-gradient(145deg,rgba(28,72,141,.85),rgba(71,43,166,.82));
        box-shadow:0 0 28px rgba(53,177,255,.24);
        color:#75dcff;
        font-size:35px;
      }

      .homework-upload-card h2{
        margin:0;
        font-family:"Heebo",Arial,sans-serif;
        font-size:28px;
        font-weight:900;
        color:#f4f7ff;
      }

      .homework-upload-card p{
        max-width:520px;
        margin:9px 0 0;
        color:#9fb4d7;
        font:600 14px/1.65 "Heebo",Arial,sans-serif;
      }

      .homework-upload-actions{
        display:flex;
        align-items:center;
        justify-content:center;
        flex-wrap:wrap;
        gap:11px;
        margin-top:25px;
      }

      .homework-upload-action{
        min-width:158px;
        height:48px;
        display:flex;
        align-items:center;
        justify-content:center;
        gap:9px;
        border:1px solid rgba(86,162,255,.55);
        border-radius:13px;
        background:linear-gradient(135deg,#18386c,#34258c);
        box-shadow:0 7px 19px rgba(0,5,22,.28);
        color:#fff;
        font:800 13px "Heebo",Arial,sans-serif;
        cursor:pointer;
      }

      .homework-upload-action.primary{
        border-color:rgba(97,214,255,.75);
        background:linear-gradient(135deg,#1266ae,#5736d6);
        box-shadow:0 0 20px rgba(43,174,255,.18);
      }

      .homework-upload-action:hover{
        transform:translateY(-1px);
        border-color:#66dbff;
      }

      .homework-stage-note{
        display:flex;
        gap:8px;
        align-items:center;
        margin-top:19px;
        color:#70d6ff;
        font:700 12px "Heebo",Arial,sans-serif;
      }

      .homework-preview-shell{
        position:absolute;
        inset:0;
        display:flex;
        align-items:center;
        justify-content:center;
        padding:18px;
        background:#031022;
      }

      .homework-preview-shell img{
        width:100%;
        height:100%;
        object-fit:contain;
        border-radius:16px;
        filter:drop-shadow(0 14px 26px rgba(0,0,0,.38));
      }

      .homework-preview-badge{
        position:absolute;
        top:16px;
        right:16px;
        z-index:3;
        padding:8px 12px;
        border:1px solid rgba(75,204,255,.45);
        border-radius:999px;
        background:rgba(5,21,46,.90);
        color:#9feaff;
        font:800 11px "Heebo",Arial,sans-serif;
        backdrop-filter:blur(9px);
      }

      .homework-sidebar-overlay{
        position:absolute;
        inset:0;
        z-index:20;
        padding:15px 13px 150px;
        overflow:auto;
        background:
          radial-gradient(circle at 50% 0%,rgba(38,107,205,.18),transparent 34%),
          linear-gradient(180deg,rgba(4,17,36,.99),rgba(2,10,24,.99));
        direction:rtl;
        color:#fff;
      }

      .homework-sidebar-title{
        display:flex;
        align-items:center;
        gap:10px;
        margin-bottom:13px;
        padding-bottom:13px;
        border-bottom:1px solid rgba(74,137,213,.18);
      }

      .homework-sidebar-title i{
        width:34px;
        height:34px;
        display:grid;
        place-items:center;
        border-radius:10px;
        color:#76d9ff;
        background:rgba(21,82,150,.38);
      }

      .homework-sidebar-title strong{
        font:900 15px "Heebo",Arial,sans-serif;
      }

      .homework-sidebar-step{
        display:flex;
        align-items:center;
        gap:10px;
        min-height:48px;
        margin:7px 0;
        padding:8px 9px;
        border:1px solid rgba(65,119,185,.20);
        border-radius:12px;
        color:#8298ba;
        font:750 11px "Heebo",Arial,sans-serif;
      }

      .homework-sidebar-step.active{
        border-color:rgba(106,91,255,.70);
        background:linear-gradient(135deg,rgba(66,41,149,.72),rgba(15,52,101,.70));
        color:#fff;
        box-shadow:0 0 16px rgba(76,91,255,.14);
      }

      .homework-sidebar-step span:first-child{
        width:26px;
        height:26px;
        display:grid;
        place-items:center;
        flex:0 0 26px;
        border-radius:50%;
        border:1px solid rgba(97,149,212,.40);
        color:#78ccff;
      }

      body.homework-lesson-mode .lesson-loading-overlay{
        display:none!important;
      }
    `;

    document.head.appendChild(style);
  }

  function renderHomeworkSidebar(){
    const sidebar = document.querySelector(".lesson-lessons-sidebar");
    if(!sidebar){
      return;
    }

    sidebar.style.position = "relative";
    sidebar.querySelector(".homework-sidebar-overlay")?.remove();

    const overlay = document.createElement("div");
    overlay.className = "homework-sidebar-overlay";
    overlay.innerHTML = `
      <div class="homework-sidebar-title">
        <i class="fa-solid fa-camera"></i>
        <strong>עזרה בשיעורי בית</strong>
      </div>
      <div class="homework-sidebar-step active"><span>1</span><span>העלאת שיעורי הבית</span></div>
      <div class="homework-sidebar-step"><span>2</span><span>זיהוי המקצוע והנושא</span></div>
      <div class="homework-sidebar-step"><span>3</span><span>הבנת השאלה</span></div>
      <div class="homework-sidebar-step"><span>4</span><span>עזרה ופתרון יחד</span></div>
      <div class="homework-sidebar-step"><span>5</span><span>בדיקת התשובה</span></div>
    `;

    sidebar.appendChild(overlay);
  }

  function renderUploadStage(){
    const stage = document.querySelector(".lesson-visual-stage");
    if(!stage){
      return;
    }

    stage.innerHTML = `
      <div class="homework-stage-shell">
        <section class="homework-upload-card">
          <div class="homework-upload-icon"><i class="fa-solid fa-file-arrow-up"></i></div>
          <h2>העלו את שיעורי הבית</h2>
          <p>צלמו את הדף או העלו תמונה / PDF. אני אזהה את המקצוע והנושא ואעזור בלי לתת ישר את התשובה.</p>
          <div class="homework-upload-actions">
            <button type="button" class="homework-upload-action primary" data-homework-camera>
              <i class="fa-solid fa-camera"></i>
              <span>צלם שיעורי בית</span>
            </button>
            <button type="button" class="homework-upload-action" data-homework-file>
              <i class="fa-solid fa-file-arrow-up"></i>
              <span>העלה קובץ</span>
            </button>
          </div>
          <div class="homework-stage-note"><i class="fa-solid fa-sparkles"></i><span>המורה תעזור להבין ולפתור — לא רק לגלות את התשובה.</span></div>
        </section>
      </div>
    `;

    stage.querySelector("[data-homework-camera]")?.addEventListener("click", function(){
      document.getElementById("homeworkCameraInput")?.click();
    });

    stage.querySelector("[data-homework-file]")?.addEventListener("click", function(){
      document.getElementById("homeworkFileInput")?.click();
    });
  }

  function clearHomeworkChat(){
    const messages = document.querySelector(".lesson-chat-workspace .messages");
    if(messages){
      messages.innerHTML = "";
    }

    const title = document.getElementById("heroGreeting");
    if(title){
      title.textContent = "שיחה עם המורה";
    }

    const subtitle = document.getElementById("learningSubtitle");
    if(subtitle){
      subtitle.textContent = "עזרה בשיעורי בית";
    }
  }

  function setHomeworkModeVariables(){
    try{
      currentLearningMode = "homework";
      currentLessonId = null;
      clearNoResponseTimer();
    }
    catch(error){
      console.warn("HOMEWORK WORKSPACE MODE VARIABLE WARNING", error);
    }

    window.SELECTED_UNIT_LESSON = null;
  }

  function showHomeworkLessonWorkspace(options = {}){
    ensureStyles();

    document.body.classList.add("homework-lesson-mode", "lesson-theme-science");

    originalShowLearning("lesson");
    setHomeworkModeVariables();

    try{
      hideLessonLoading();
    }
    catch(error){}

    document.querySelector(".lesson-ai-waiting-panel")?.remove();

    clearHomeworkChat();
    renderHomeworkSidebar();

    if(options.keepPreview !== true){
      renderUploadStage();
    }

    return true;
  }

  function leaveHomeworkLessonMode(){
    document.body.classList.remove("homework-lesson-mode");
    document.querySelector(".homework-sidebar-overlay")?.remove();
  }

  window.showHomeworkLessonWorkspace = showHomeworkLessonWorkspace;

  window.showLearning = function(mode = "homework"){
    if(mode === "homework"){
      return showHomeworkLessonWorkspace({
        keepPreview:Boolean(document.querySelector(".homework-preview-shell"))
      });
    }

    leaveHomeworkLessonMode();
    return originalShowLearning(mode);
  };

  window.startHomeworkCamera = async function(){
    return showHomeworkLessonWorkspace();
  };

  function showHomeworkPreview(file){
    if(!file || !String(file.type || "").startsWith("image/")){
      return;
    }

    const stage = document.querySelector(".lesson-visual-stage");
    if(!stage){
      return;
    }

    const url = URL.createObjectURL(file);

    stage.innerHTML = `
      <div class="homework-preview-shell">
        <div class="homework-preview-badge">✓ התמונה התקבלה — מזהה את השיעור</div>
        <img alt="שיעורי הבית שהועלו">
      </div>
    `;

    const image = stage.querySelector("img");
    if(image){
      image.src = url;
      image.addEventListener("load", function(){
        URL.revokeObjectURL(url);
      }, {once:true});
    }

    const steps = document.querySelectorAll(".homework-sidebar-step");
    steps.forEach(step => step.classList.remove("active"));
    steps[1]?.classList.add("active");
  }

  ["homeworkCameraInput","homeworkFileInput"].forEach(function(id){
    const input = document.getElementById(id);
    if(!input){
      return;
    }

    input.addEventListener("change", function(event){
      const file = event.target.files?.[0];
      if(!file){
        return;
      }

      showHomeworkLessonWorkspace({keepPreview:true});
      showHomeworkPreview(file);
    }, true);
  });

  console.log("HOMEWORK LESSON WORKSPACE V1 READY");
}
