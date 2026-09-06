window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.36";
/*
  IAKIDS workspace extension loader.
  The original lesson-completion implementation is preserved in
  lesson-completion-core.js. After it loads, this file adds the new
  homework workspace routing without duplicating the main workspace HTML.
*/
(function(){
  const core = document.createElement("script");
  core.src = "/he/workspace/lesson-completion-core.js?v=0736";
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

      .homework-dual-workspace{
        position:absolute;
        inset:0;
        display:grid;
        grid-template-columns:minmax(0,1.08fr) minmax(0,1fr);
        gap:14px;
        padding:12px;
        direction:ltr;
        background:#031022;
      }

      .homework-sheet-pane,
      .homework-notebook-pane{
        min-width:0;
        width:100%;
        min-height:0;
        overflow:hidden;
        border:1px solid rgba(72,148,238,.34);
        border-radius:18px;
        background:linear-gradient(180deg,rgba(7,24,51,.98),rgba(3,15,34,.99));
        box-shadow:inset 0 0 0 1px rgba(99,69,220,.05),0 12px 30px rgba(0,0,0,.22);
      }

      .homework-pane-toolbar{
        height:44px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        padding:0 13px;
        border-bottom:1px solid rgba(73,139,220,.20);
        color:#dcecff;
        background:rgba(8,29,60,.93);
        direction:rtl;
        font:800 12px "Heebo",Arial,sans-serif;
      }

      .homework-pane-toolbar .homework-pane-label{
        display:flex;
        align-items:center;
        gap:8px;
        min-width:0;
      }

      .homework-pane-toolbar .homework-pane-label span{
        overflow:hidden;
        text-overflow:ellipsis;
        white-space:nowrap;
      }

      .homework-pane-icon{
        width:27px;
        height:27px;
        display:grid;
        place-items:center;
        border-radius:8px;
        color:#74dcff;
        border:1px solid rgba(74,174,255,.35);
        background:rgba(24,70,126,.36);
      }

      .homework-sheet-canvas{
        position:relative;
        height:calc(100% - 44px);
        padding:12px;
        display:flex;
        align-items:center;
        justify-content:center;
        overflow:hidden;
        background:#06152b;
      }

      .homework-sheet-canvas img{
        width:100%;
        height:100%;
        object-fit:contain;
        border-radius:10px;
        filter:drop-shadow(0 12px 24px rgba(0,0,0,.34));
      }

      .homework-notebook-pane{
        display:flex;
        flex-direction:column;
        direction:rtl;
      }

      .homework-notebook-page{
        position:relative;
        flex:1;
        overflow:auto;
        padding:28px 34px 36px 46px;
        color:#18346d;
        background-color:#f9fbff;
        background-image:
          linear-gradient(90deg,transparent 0,transparent 42px,rgba(224,86,93,.33) 42px,rgba(224,86,93,.33) 44px,transparent 44px),
          repeating-linear-gradient(180deg,transparent 0,transparent 35px,rgba(79,149,205,.25) 36px,transparent 37px);
        background-size:100% 100%,100% 37px;
        box-shadow:inset 0 0 26px rgba(13,57,112,.06);
      }

      .homework-notebook-heading{
        margin:0 0 17px;
        color:#273a78;
        font-family:"Heebo",Arial,sans-serif;
        font-size:16px;
        font-weight:900;
      }

      .homework-notebook-empty{
        margin-top:12px;
        color:rgba(49,73,124,.55);
        font:700 12px/1.7 "Heebo",Arial,sans-serif;
      }

      .homework-notebook-answer{
        position:relative;
        margin:0 0 22px;
        min-height:54px;
        padding:1px 0 4px;
        color:#24408a;
        font-family:"Gveret Levin","Segoe Print","Comic Sans MS",cursive;
        font-size:20px;
        line-height:1.85;
        font-weight:500;
        letter-spacing:.1px;
        text-align:right;
        white-space:pre-wrap;
      }

      .homework-notebook-answer .homework-notebook-number{
        display:inline-block;
        margin-left:7px;
        color:#1f377f;
        font-weight:700;
      }

      .homework-notebook-answer.writing::after{
        content:"";
        display:inline-block;
        width:2px;
        height:20px;
        margin-right:3px;
        vertical-align:-3px;
        background:#3158ae;
        animation:homeworkNotebookCursor .75s steps(1) infinite;
      }

      @keyframes homeworkNotebookCursor{
        0%,48%{opacity:1}
        49%,100%{opacity:0}
      }

      .homework-notebook-clear{
        border:1px solid rgba(76,139,219,.24);
        border-radius:9px;
        padding:5px 9px;
        background:rgba(11,37,75,.55);
        color:#bcd8fb;
        font:750 10px "Heebo",Arial,sans-serif;
        cursor:pointer;
      }

      @media (max-width:1100px){
        .homework-dual-workspace{
          grid-template-columns:1fr;
          grid-template-rows:minmax(0,56fr) minmax(260px,44fr);
        }
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
      window.HOMEWORK_NOTEBOOK_ANSWERS = [];
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

  function ensureHomeworkNotebookState(){
    if(!Array.isArray(window.HOMEWORK_NOTEBOOK_ANSWERS)){
      window.HOMEWORK_NOTEBOOK_ANSWERS = [];
    }
    return window.HOMEWORK_NOTEBOOK_ANSWERS;
  }

  function renderHomeworkNotebookSavedAnswers(){
    const host = document.getElementById("homeworkNotebookAnswers");
    if(!host) return;

    const answers = ensureHomeworkNotebookState();
    host.innerHTML = "";

    const empty = document.querySelector(".homework-notebook-empty");
    if(empty) empty.style.display = answers.length ? "none" : "block";

    answers.forEach(item => {
      const row = document.createElement("div");
      row.className = "homework-notebook-answer";
      row.dataset.questionNumber = String(item.number || "");

      const number = document.createElement("span");
      number.className = "homework-notebook-number";
      number.textContent = `${item.number}.`;

      const text = document.createElement("span");
      text.className = "homework-notebook-text";
      text.textContent = String(item.text || "");

      row.appendChild(number);
      row.appendChild(text);
      host.appendChild(row);
    });
  }

  async function writeHomeworkNotebookAnswer(questionNumber, answerText){
    const number = Number(questionNumber || 0) || 1;
    const text = String(answerText || "").replace(/\s+/g," ").trim();
    if(!text) return false;

    const answers = ensureHomeworkNotebookState();
    const existingIndex = answers.findIndex(item => Number(item.number) === number);
    const item = {number, text};
    if(existingIndex >= 0) answers[existingIndex] = item;
    else answers.push(item);
    answers.sort((a,b) => Number(a.number) - Number(b.number));

    const host = document.getElementById("homeworkNotebookAnswers");
    if(!host) return true;

    const empty = document.querySelector(".homework-notebook-empty");
    if(empty) empty.style.display = "none";

    host.querySelector(`[data-question-number="${number}"]`)?.remove();

    const row = document.createElement("div");
    row.className = "homework-notebook-answer writing";
    row.dataset.questionNumber = String(number);

    const numberEl = document.createElement("span");
    numberEl.className = "homework-notebook-number";
    numberEl.textContent = `${number}.`;

    const textEl = document.createElement("span");
    textEl.className = "homework-notebook-text";
    textEl.textContent = "";

    row.appendChild(numberEl);
    row.appendChild(textEl);
    host.appendChild(row);

    const page = document.querySelector(".homework-notebook-page");
    page?.scrollTo({top:page.scrollHeight,behavior:"smooth"});

    const delay = text.length > 150 ? 13 : text.length > 85 ? 18 : 24;
    for(let i=0;i<text.length;i+=1){
      textEl.textContent += text[i];
      if(i % 4 === 0){
        page?.scrollTo({top:page.scrollHeight,behavior:"auto"});
      }
      await new Promise(resolve => setTimeout(resolve, delay));
    }
    row.classList.remove("writing");
    return true;
  }

  function clearHomeworkNotebook(){
    window.HOMEWORK_NOTEBOOK_ANSWERS = [];
    renderHomeworkNotebookSavedAnswers();
  }

  function showHomeworkPreview(file){
    if(!file || !String(file.type || "").startsWith("image/")){
      return;
    }

    const stage = document.querySelector(".lesson-visual-stage");
    if(!stage){
      return;
    }

    const url = URL.createObjectURL(file);
    const safeName = String(file.name || "שיעורי הבית").replace(/[<>]/g, "");

    stage.innerHTML = `
      <div class="homework-preview-shell homework-dual-workspace">
        <section class="homework-sheet-pane">
          <div class="homework-pane-toolbar">
            <div class="homework-pane-label">
              <span class="homework-pane-icon">▣</span>
              <span>${safeName}</span>
            </div>
            <span style="color:#7fdcff;font-weight:800">דף השיעורים</span>
          </div>
          <div class="homework-sheet-canvas">
            <div class="homework-preview-badge">✓ התמונה התקבלה — מזהה את השיעור</div>
            <img alt="שיעורי הבית שהועלו">
          </div>
        </section>

        <section class="homework-notebook-pane">
          <div class="homework-pane-toolbar">
            <div class="homework-pane-label">
              <span class="homework-pane-icon">✎</span>
              <span>המחברת שלי</span>
            </div>
            <button type="button" class="homework-notebook-clear" data-homework-notebook-clear>ניקוי</button>
          </div>
          <div class="homework-notebook-page">
            <div class="homework-notebook-heading">תשובות:</div>
            <div class="homework-notebook-empty">אחרי שתעני ותביני את התשובה, המורה תכתוב כאן את הניסוח הסופי.</div>
            <div id="homeworkNotebookAnswers"></div>
          </div>
        </section>
      </div>
    `;

    const image = stage.querySelector(".homework-sheet-canvas img");
    if(image){
      image.src = url;
      image.addEventListener("load", function(){
        URL.revokeObjectURL(url);
      }, {once:true});
    }

    stage.querySelector("[data-homework-notebook-clear]")?.addEventListener("click", clearHomeworkNotebook);
    renderHomeworkNotebookSavedAnswers();

    const steps = document.querySelectorAll(".homework-sidebar-step");
    steps.forEach(step => step.classList.remove("active"));
    steps[1]?.classList.add("active");
  }

  window.writeHomeworkNotebookAnswer = writeHomeworkNotebookAnswer;
  window.renderHomeworkNotebookSavedAnswers = renderHomeworkNotebookSavedAnswers;
  window.clearHomeworkNotebook = clearHomeworkNotebook;

  let homeworkPdfJsPromise = null;

  function loadHomeworkPdfJs(){
    if(window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    if(homeworkPdfJsPromise) return homeworkPdfJsPromise;

    homeworkPdfJsPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
      script.async = true;
      script.onload = () => {
        if(!window.pdfjsLib){
          reject(new Error("PDF.js loaded without pdfjsLib"));
          return;
        }
        window.pdfjsLib.GlobalWorkerOptions.workerSrc =
          "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
        resolve(window.pdfjsLib);
      };
      script.onerror = () => reject(new Error("Failed to load PDF.js"));
      document.head.appendChild(script);
    });

    return homeworkPdfJsPromise;
  }

  async function convertHomeworkPdfFirstPageToImage(file){
    const pdfjs = await loadHomeworkPdfJs();
    const bytes = new Uint8Array(await file.arrayBuffer());
    const pdf = await pdfjs.getDocument({data:bytes}).promise;
    if(!pdf.numPages){
      throw new Error("PDF has no pages");
    }

    const page = await pdf.getPage(1);
    const baseViewport = page.getViewport({scale:1});
    const maxSide = 1800;
    const scale = Math.min(
      2.2,
      maxSide / Math.max(baseViewport.width, baseViewport.height)
    );
    const viewport = page.getViewport({scale:Math.max(1.25, scale)});

    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    const ctx = canvas.getContext("2d", {alpha:false});
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    await page.render({canvasContext:ctx, viewport}).promise;

    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob(
        result => result ? resolve(result) : reject(new Error("PDF canvas conversion failed")),
        "image/jpeg",
        0.92
      );
    });

    const baseName = String(file.name || "homework.pdf").replace(/\.pdf$/i, "");
    return new File([blob], `${baseName}-page-1.jpg`, {type:"image/jpeg"});
  }

  async function handleHomeworkPdfUpload(file){
    showHomeworkLessonWorkspace({keepPreview:true});

    const stage = document.querySelector(".lesson-visual-stage");
    if(stage){
      stage.innerHTML = `
        <div class="homework-stage-shell">
          <section class="homework-upload-card" style="min-height:280px">
            <div class="homework-upload-icon">PDF</div>
            <h2>קוראת את קובץ ה־PDF</h2>
            <p>אני ממירה את העמוד הראשון לתמונה כדי לזהות את התרגיל.</p>
          </section>
        </div>`;
    }

    try{
      const imageFile = await convertHomeworkPdfFirstPageToImage(file);
      showHomeworkPreview(imageFile);

      if(typeof window.handleHomeworkFile === "function"){
        await window.handleHomeworkFile(imageFile);
      }
      else if(typeof handleHomeworkFile === "function"){
        await handleHomeworkFile(imageFile);
      }
      else{
        throw new Error("handleHomeworkFile is not available");
      }
    }
    catch(error){
      console.error("HOMEWORK PDF UPLOAD FAILED:", error);
      if(typeof window.renderHomeworkStructuredTeacherMessage === "function"){
        await window.renderHomeworkStructuredTeacherMessage(
          "לא הצלחתי לקרוא את קובץ ה־PDF. נסי לשמור אותו כתמונה או לצלם את העמוד."
        );
      }
      else if(typeof addMessage === "function"){
        addMessage("assistant", "לא הצלחתי לקרוא את קובץ ה־PDF. נסי לשמור אותו כתמונה או לצלם את העמוד.");
      }
    }
  }

  ["homeworkCameraInput","homeworkFileInput"].forEach(function(id){
    const input = document.getElementById(id);
    if(!input){
      return;
    }

    // The file picker supports both images and PDFs. Camera remains image-first.
    if(id === "homeworkFileInput"){
      input.setAttribute("accept", "image/*,application/pdf,.pdf");
    }

    input.addEventListener("change", function(event){
      const file = event.target.files?.[0];
      if(!file){
        return;
      }

      const isPdf =
        String(file.type || "").toLowerCase() === "application/pdf"
        || /\.pdf$/i.test(String(file.name || ""));

      if(isPdf){
        // Stop the legacy image-only handler from trying to compress a PDF.
        event.preventDefault();
        event.stopImmediatePropagation();
        handleHomeworkPdfUpload(file);
        return;
      }

      showHomeworkLessonWorkspace({keepPreview:true});
      showHomeworkPreview(file);
    }, true);
  });

  console.log("HOMEWORK LESSON WORKSPACE V1 READY");
}
