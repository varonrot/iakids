from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# Dedicated renderer for structured homework responses: dark teacher bubble + avatar + typing.
anchor = '''  async function runStructuredHomeworkTurn(answerText){\n'''
helper = r'''  function ensureHomeworkStructuredTeacherStyles(){
    if(document.getElementById("iakidsHomeworkStructuredTeacherStyles")) return;

    const style = document.createElement("style");
    style.id = "iakidsHomeworkStructuredTeacherStyles";
    style.textContent = `
      body.homework-lesson-mode .homework-structured-teacher-row{
        display:flex;
        align-items:flex-end;
        justify-content:flex-start;
        gap:12px;
        width:100%;
        margin:10px 0 14px;
        direction:rtl;
      }
      body.homework-lesson-mode .homework-structured-teacher-avatar{
        width:48px;
        height:48px;
        flex:0 0 48px;
        border-radius:50%;
        object-fit:cover;
        border:2px solid rgba(48,139,255,.55);
        box-shadow:0 0 18px rgba(39,119,255,.28);
        background:#071327;
      }
      body.homework-lesson-mode .homework-structured-teacher-bubble{
        max-width:min(82%, 560px);
        padding:15px 18px;
        border-radius:18px 18px 6px 18px;
        border:1px solid rgba(74,137,218,.36);
        background:linear-gradient(180deg,rgba(18,42,75,.98),rgba(12,31,58,.98));
        color:#eef6ff;
        font-size:15px;
        line-height:1.65;
        font-weight:650;
        white-space:pre-wrap;
        text-align:right;
        box-shadow:inset 0 0 0 1px rgba(85,154,255,.04),0 8px 22px rgba(0,0,0,.18);
      }
    `;
    document.head.appendChild(style);
  }

  async function renderHomeworkStructuredTeacherMessage(text){
    ensureHomeworkStructuredTeacherStyles();

    const messages = getHomeworkMessagesContainer?.()
      || document.querySelector('.lesson-chat-workspace .messages');

    if(!messages){
      addMessage("assistant", text);
      return;
    }

    const row = document.createElement("div");
    row.className = "homework-structured-teacher-row";

    const avatar = document.createElement("img");
    avatar.className = "homework-structured-teacher-avatar";
    avatar.src = "/assets/lesson/lesson-teacher.webp";
    avatar.alt = "המורה";

    const bubble = document.createElement("div");
    bubble.className = "homework-structured-teacher-bubble";
    bubble.textContent = "";

    row.appendChild(avatar);
    row.appendChild(bubble);
    messages.appendChild(row);

    messages.scrollTop = messages.scrollHeight;

    const value = String(text || "");
    const typingDelay = value.length > 180 ? 8 : value.length > 100 ? 11 : 14;

    for(let i=0;i<value.length;i+=1){
      bubble.textContent += value[i];
      if(i % 3 === 0){
        messages.scrollTop = messages.scrollHeight;
      }
      await new Promise(resolve => setTimeout(resolve, typingDelay));
    }

    messages.scrollTop = messages.scrollHeight;
  }

'''

if 'function renderHomeworkStructuredTeacherMessage' not in core:
    if anchor not in core:
        raise SystemExit('runStructuredHomeworkTurn anchor not found')
    core = core.replace(anchor, helper + anchor, 1)

core = core.replace(
    '        addMessage("assistant", text);\n        await playHomeworkTeacherAudio(text);',
    '        await Promise.all([\n          renderHomeworkStructuredTeacherMessage(text),\n          playHomeworkTeacherAudio(text)\n        ]);',
    1
)

core = core.replace(
    '      addMessage("assistant", teacherResponse);\n      await playHomeworkTeacherAudio(teacherResponse);',
    '      await Promise.all([\n        renderHomeworkStructuredTeacherMessage(teacherResponse),\n        playHomeworkTeacherAudio(teacherResponse)\n      ]);',
    1
)

core = core.replace(
    '      addMessage("assistant", "לא הצלחתי לבדוק את התשובה כרגע. נסי שוב בעוד רגע.");',
    '      await renderHomeworkStructuredTeacherMessage("לא הצלחתי לבדוק את התשובה כרגע. נסי שוב בעוד רגע.");',
    1
)

index = index.replace('IAKIDS • build 0.7.28', 'IAKIDS • build 0.7.29')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.28";', 'window.IAKIDS_BUILD_VERSION = "0.7.29";')
index = index.replace('/he/workspace/lesson-completion.js?v=0728', '/he/workspace/lesson-completion.js?v=0729')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.28";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.29";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0728', '/he/workspace/lesson-completion-core.js?v=0729')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')

print('Structured homework teacher rendering fixed; dark bubble + avatar + typing; build 0.7.29')

# trigger
