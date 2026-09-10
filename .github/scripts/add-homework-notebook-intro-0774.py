from pathlib import Path

EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# 1) Add notebook intro styles before existing notebook heading styles.
style_anchor = '''      .homework-notebook-heading{\n'''
intro_css = '''      .homework-notebook-intro{\n        margin:0 0 18px;\n        padding:0 0 14px;\n        border-bottom:1px dashed rgba(47,81,155,.22);\n      }\n\n      .homework-notebook-intro:empty{\n        display:none;\n      }\n\n      .homework-notebook-intro-line{\n        min-height:34px;\n        margin:0 0 6px;\n        color:#24408a;\n        font-family:\"Gveret Levin\",\"Segoe Print\",\"Comic Sans MS\",cursive;\n        font-weight:500;\n        line-height:1.75;\n        text-align:right;\n        white-space:pre-wrap;\n        letter-spacing:.1px;\n      }\n\n      .homework-notebook-intro-line.subject{\n        font-size:25px;\n        font-weight:700;\n        color:#213d83;\n      }\n\n      .homework-notebook-intro-line.topic{\n        font-size:21px;\n        color:#2c468f;\n      }\n\n      .homework-notebook-intro-line.writing::after{\n        content:\"\";\n        display:inline-block;\n        width:2px;\n        height:20px;\n        margin-right:3px;\n        vertical-align:-3px;\n        background:#3158ae;\n        animation:homeworkNotebookCursor .75s steps(1) infinite;\n      }\n\n'''
if 'homework-notebook-intro-line.subject' not in ext:
    if style_anchor not in ext:
        raise SystemExit('notebook heading style anchor not found')
    ext = ext.replace(style_anchor, intro_css + style_anchor, 1)

# 2) Add intro host at the top of the notebook page.
html_old = '''          <div class=\"homework-notebook-page\">\n            <div class=\"homework-notebook-heading\">תשובות:</div>\n'''
html_new = '''          <div class=\"homework-notebook-page\">\n            <div id=\"homeworkNotebookIntro\" class=\"homework-notebook-intro\"></div>\n            <div class=\"homework-notebook-heading\">תשובות:</div>\n'''
if 'id="homeworkNotebookIntro"' not in ext:
    if html_old not in ext:
        raise SystemExit('notebook page html anchor not found')
    ext = ext.replace(html_old, html_new, 1)

# 3) Add animated handwriting helpers after ensureHomeworkNotebookState.
helper_anchor = '''  function renderHomeworkNotebookSavedAnswers(){\n'''
helpers = r'''  function homeworkNotebookSleep(ms){
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function clearHomeworkNotebookIntro(){
    window.HOMEWORK_NOTEBOOK_INTRO = null;
    const host = document.getElementById("homeworkNotebookIntro");
    if(host){
      host.innerHTML = "";
      host.dataset.seeded = "";
    }
  }

  async function writeHomeworkNotebookIntroLine(text, className){
    const host = document.getElementById("homeworkNotebookIntro");
    const value = String(text || "").trim();
    if(!host || !value) return false;

    const row = document.createElement("div");
    row.className = `homework-notebook-intro-line ${className || ""} writing`;
    const span = document.createElement("span");
    row.appendChild(span);
    host.appendChild(row);

    const delay = value.length > 55 ? 15 : 23;
    for(let i=0;i<value.length;i+=1){
      span.textContent += value[i];
      if(i % 4 === 0) await homeworkNotebookSleep(delay);
    }
    row.classList.remove("writing");
    await homeworkNotebookSleep(110);
    return true;
  }

  async function seedHomeworkNotebookIntro(subject, topic){
    const cleanSubject = String(subject || "").replace(/^[\s:,-]+|[\s:,-]+$/g, "").trim();
    const cleanTopic = String(topic || "").replace(/^[\s:,-]+|[\s:,-]+$/g, "").trim();
    if(!cleanSubject && !cleanTopic) return false;

    window.HOMEWORK_NOTEBOOK_INTRO = {subject:cleanSubject, topic:cleanTopic};

    const host = document.getElementById("homeworkNotebookIntro");
    if(!host) return false;

    const key = `${cleanSubject}|${cleanTopic}`;
    if(host.dataset.seeded === key) return true;
    host.dataset.seeded = key;
    host.innerHTML = "";

    if(cleanSubject){
      let subjectTitle = cleanSubject;
      if(!/^שיעורים\s+ב/.test(subjectTitle)){
        subjectTitle = `שיעורים ב${subjectTitle}`;
      }
      await writeHomeworkNotebookIntroLine(subjectTitle, "subject");
    }
    if(cleanTopic){
      await writeHomeworkNotebookIntroLine(`הנושא: ${cleanTopic}`, "topic");
    }
    return true;
  }

  function restoreHomeworkNotebookIntro(){
    const saved = window.HOMEWORK_NOTEBOOK_INTRO;
    if(saved?.subject || saved?.topic){
      seedHomeworkNotebookIntro(saved.subject, saved.topic);
    }
  }

  function parseHomeworkDetectionText(text){
    const value = String(text || "").replace(/\s+/g, " ").trim();
    if(!value || !value.includes("זיהיתי")) return null;

    // Typical teacher text:
    // "זיהיתי שזה שיעורי בית בתנ״ך בנושא אברהם מכניס אורחים"
    let match = value.match(/שיעורי(?:\s+בית)?\s+ב([^.,!?:]+?)\s+בנושא\s+([^.!?\n]+)/i);
    if(!match){
      match = value.match(/(?:מקצוע|במקצוע)\s*[:\-]?\s*([^.,!?:]+?)(?:,|\s+)\s*(?:ה)?נושא\s*[:\-]?\s*([^.!?\n]+)/i);
    }
    if(!match) return null;

    let subject = String(match[1] || "").trim();
    let topic = String(match[2] || "").trim();

    topic = topic
      .replace(/\s*(?:אפשר|תרצי|תרצה|אני\s+יכולה|אני\s+יכול|בואי|בוא)\b.*$/i, "")
      .replace(/[,:;\-]+$/g, "")
      .trim();

    if(!subject || !topic) return null;
    return {subject, topic};
  }

  function installHomeworkNotebookIntroDetector(){
    if(window.__IAKIDS_HOMEWORK_NOTEBOOK_INTRO_DETECTOR_0774) return;
    window.__IAKIDS_HOMEWORK_NOTEBOOK_INTRO_DETECTOR_0774 = true;

    const inspect = root => {
      if(!document.body.classList.contains("homework-lesson-mode")) return;
      const nodes = [];
      if(root instanceof Element) nodes.push(root);
      if(root?.querySelectorAll){
        root.querySelectorAll(".lesson-chat-workspace .messages *, .lesson-chat-workspace .msg-bubble, .lesson-chat-workspace [class*='message']")
          .forEach(el => nodes.push(el));
      }
      for(const node of nodes){
        const parsed = parseHomeworkDetectionText(node.textContent || "");
        if(parsed){
          seedHomeworkNotebookIntro(parsed.subject, parsed.topic);
          break;
        }
      }
    };

    const observer = new MutationObserver(mutations => {
      for(const mutation of mutations){
        for(const node of mutation.addedNodes){
          if(node instanceof Element) inspect(node);
        }
      }
    });

    const start = () => {
      if(document.body) observer.observe(document.body,{childList:true,subtree:true});
      setTimeout(() => inspect(document), 250);
    };

    if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once:true});
    else start();
  }

  installHomeworkNotebookIntroDetector();
  window.seedHomeworkNotebookIntro = seedHomeworkNotebookIntro;
  window.clearHomeworkNotebookIntro = clearHomeworkNotebookIntro;

'''
if 'function seedHomeworkNotebookIntro(' not in ext:
    if helper_anchor not in ext:
        raise SystemExit('notebook helper anchor not found')
    ext = ext.replace(helper_anchor, helpers + helper_anchor, 1)

# 4) Restore intro whenever preview/notebook DOM is rebuilt.
restore_anchor = '''    renderHomeworkNotebookSavedAnswers();\n\n    const steps = document.querySelectorAll(\".homework-sidebar-step\");\n'''
restore_new = '''    renderHomeworkNotebookSavedAnswers();\n    restoreHomeworkNotebookIntro();\n\n    const steps = document.querySelectorAll(\".homework-sidebar-step\");\n'''
if 'renderHomeworkNotebookSavedAnswers();\n    restoreHomeworkNotebookIntro();' not in ext:
    if restore_anchor not in ext:
        raise SystemExit('preview restore anchor not found')
    ext = ext.replace(restore_anchor, restore_new, 1)

# 5) New homework upload resets the intro too.
reset_old = '''      window.HOMEWORK_NOTEBOOK_ANSWERS = [];\n      renderUploadStage();\n'''
reset_new = '''      window.HOMEWORK_NOTEBOOK_ANSWERS = [];\n      window.HOMEWORK_NOTEBOOK_INTRO = null;\n      renderUploadStage();\n'''
if reset_old in ext:
    ext = ext.replace(reset_old, reset_new, 1)

# 6) Version/cache bump.
ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.73";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.74";')
for oldv in ('0.7.72','0.7.73'):
    index = index.replace(f'IAKIDS • build {oldv}', 'IAKIDS • build 0.7.74')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{oldv}";', 'window.IAKIDS_BUILD_VERSION = "0.7.74";')
for oldcache in ('?v=0760','?v=0772','?v=0773'):
    index = index.replace(f'/he/workspace/lesson-completion.js{oldcache}', '/he/workspace/lesson-completion.js?v=0774')

EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Added animated subject/topic notebook intro; build 0.7.74')
