from pathlib import Path
import re

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# -----------------------------------------------------
# 1) Add notebook styles to the homework workspace.
# -----------------------------------------------------
style_anchor = '''      .homework-preview-badge{\n'''
notebook_styles = r'''      .homework-dual-workspace{
        position:absolute;
        inset:0;
        display:grid;
        grid-template-columns:minmax(0,55fr) minmax(320px,45fr);
        gap:12px;
        padding:12px;
        direction:ltr;
        background:#031022;
      }

      .homework-sheet-pane,
      .homework-notebook-pane{
        min-width:0;
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

'''
if 'homework-dual-workspace' not in ext:
    if style_anchor not in ext:
        raise SystemExit('preview badge style anchor not found')
    ext = ext.replace(style_anchor, notebook_styles + style_anchor, 1)

# -----------------------------------------------------
# 2) Replace image-only preview with worksheet + notebook.
# -----------------------------------------------------
preview_pattern = re.compile(r'''  function showHomeworkPreview\(file\)\{.*?\n  \}\n\n  \["homeworkCameraInput","homeworkFileInput"\]''', re.S)
match = preview_pattern.search(ext)
if not match:
    raise SystemExit('showHomeworkPreview block not found')

new_preview = r'''  function ensureHomeworkNotebookState(){
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

  ["homeworkCameraInput","homeworkFileInput"]'''

ext = ext[:match.start()] + new_preview + ext[match.end():]

# Reset notebook only when a genuinely new homework workspace starts, not when preserving preview.
reset_anchor = '''    if(options.keepPreview !== true){\n      renderUploadStage();\n    }\n'''
reset_replacement = '''    if(options.keepPreview !== true){\n      window.HOMEWORK_NOTEBOOK_ANSWERS = [];\n      renderUploadStage();\n    }\n'''
if reset_anchor in ext:
    ext = ext.replace(reset_anchor, reset_replacement, 1)

# -----------------------------------------------------
# 3) When an answer is accepted, write the polished final answer in notebook.
# -----------------------------------------------------
if 'function extractHomeworkNotebookFinalAnswer' not in core:
    helper_anchor = '''  async function runStructuredHomeworkTurn(answerText){\n'''
    helper = r'''  function extractHomeworkNotebookFinalAnswer(feedbackText, childAnswer){
    const feedback = String(feedbackText || "").replace(/\s+/g," ").trim();
    const answer = String(childAnswer || "").replace(/\s+/g," ").trim();

    const match = feedback.match(/(?:תשובה מלאה(?: יכולה להיות)?|ניסוח מלא)\s*[:：-]?\s*(.+)$/i);
    if(match?.[1]){
      return match[1].replace(/^['"״“”]+|['"״“”]+$/g, "").trim();
    }

    return answer;
  }

'''
    if helper_anchor not in core:
        raise SystemExit('structured turn helper anchor not found')
    core = core.replace(helper_anchor, helper + helper_anchor, 1)

# Support either 0.7.31+ sufficient branch form.
old_set = '''        setHomeworkQuestionAnswered(answer);\n        const nowCurrent = getCurrentHomeworkQuestion();\n'''
new_set = '''        const completedQuestion = setHomeworkQuestionAnswered(answer);\n        const nowCurrent = getCurrentHomeworkQuestion();\n'''
if old_set in core:
    core = core.replace(old_set, new_set, 1)
elif 'const completedQuestion = setHomeworkQuestionAnswered(answer);' not in core:
    raise SystemExit('sufficient answer state update not found')

feedback_block = '''        await Promise.all([\n          renderHomeworkStructuredTeacherMessage(feedbackText),\n          playHomeworkTeacherAudio(feedbackText)\n        ]);\n\n        // Bubble 2:'''
feedback_replacement = '''        await Promise.all([\n          renderHomeworkStructuredTeacherMessage(feedbackText),\n          playHomeworkTeacherAudio(feedbackText)\n        ]);\n\n        const notebookAnswer = extractHomeworkNotebookFinalAnswer(feedbackText, answer);\n        if(typeof window.writeHomeworkNotebookAnswer === "function"){\n          await window.writeHomeworkNotebookAnswer(\n            completedQuestion?.number || current.number,\n            notebookAnswer\n          );\n        }\n\n        // Bubble 2:'''
if feedback_block in core:
    core = core.replace(feedback_block, feedback_replacement, 1)
elif 'writeHomeworkNotebookAnswer' not in core:
    raise SystemExit('feedback render block not found')

# -----------------------------------------------------
# 4) Bump build/cache to 0.7.34 regardless of 0.7.32/33 currently landed.
# -----------------------------------------------------
index = re.sub(r'IAKIDS • build 0\.7\.\d+', 'IAKIDS • build 0.7.34', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION = "0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.34";', index)
index = re.sub(r'/he/workspace/lesson-completion\.js\?v=\d+', '/he/workspace/lesson-completion.js?v=0734', index)

ext = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.34";', ext)
ext = re.sub(r'/he/workspace/lesson-completion-core\.js\?v=\d+', '/he/workspace/lesson-completion-core.js?v=0734', ext)

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Homework worksheet/notebook split + handwriting final answers implemented; build 0.7.34')
