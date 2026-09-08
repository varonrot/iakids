from pathlib import Path
import re

ROOT = Path('.')
core_path = ROOT / 'he' / 'workspace' / 'lesson-completion-core.js'
ext_path = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index_path = ROOT / 'he' / 'workspace' / 'index.html'

core = core_path.read_text(encoding='utf-8')
ext = ext_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

# -----------------------------------------------------
# 1) Core: never generate/play homework TTS when toggle is off.
# -----------------------------------------------------
# Guard the central homework TTS function so every existing call site is covered.
if 'HOMEWORK AUDIO TOGGLE GUARD 0.7.49' not in core:
    pattern = r'(async\s+function\s+playHomeworkTeacherAudio\s*\([^)]*\)\s*\{)'
    repl = r'''\1
    // HOMEWORK AUDIO TOGGLE GUARD 0.7.49
    if(window.HOMEWORK_AUDIO_ENABLED !== true){
      return null;
    }'''
    core, n = re.subn(pattern, repl, core, count=1)
    if n != 1:
        raise RuntimeError('playHomeworkTeacherAudio function not found')

core_path.write_text(core, encoding='utf-8')

# -----------------------------------------------------
# 2) Workspace extension: compact audio toggle in homework chat.
# -----------------------------------------------------
if 'IAKIDS HOMEWORK AUDIO TOGGLE 0.7.49' not in ext:
    anchor = 'function installHomeworkLessonWorkspace(){\n'
    if anchor not in ext:
        raise RuntimeError('installHomeworkLessonWorkspace anchor not found')

    block = r'''
/* IAKIDS HOMEWORK AUDIO TOGGLE 0.7.49 */
(function(){
  const STORAGE_KEY = "iakids_homework_audio_enabled";

  function readPreference(){
    try{
      return localStorage.getItem(STORAGE_KEY) === "1";
    }catch(error){
      return false;
    }
  }

  window.HOMEWORK_AUDIO_ENABLED = readPreference();

  function setPreference(enabled){
    window.HOMEWORK_AUDIO_ENABLED = enabled === true;
    try{
      localStorage.setItem(STORAGE_KEY, window.HOMEWORK_AUDIO_ENABLED ? "1" : "0");
    }catch(error){}
    updateToggle();
  }

  function ensureStyles(){
    if(document.getElementById("iakidsHomeworkAudioToggleStyles")) return;
    const style = document.createElement("style");
    style.id = "iakidsHomeworkAudioToggleStyles";
    style.textContent = `
      body.homework-lesson-mode .lesson-chat-workspace{position:relative!important;}
      .iakids-homework-audio-toggle{
        display:inline-flex;align-items:center;gap:7px;height:34px;padding:0 11px;
        border:1px solid rgba(94,157,244,.35);border-radius:999px;
        background:rgba(8,30,61,.88);color:#a9bdd9;
        font:800 11px "Heebo",Arial,sans-serif;cursor:pointer;
        box-shadow:inset 0 0 0 1px rgba(80,129,210,.04),0 5px 16px rgba(0,0,0,.18);
        transition:.16s ease;white-space:nowrap;
      }
      .iakids-homework-audio-toggle:hover{border-color:rgba(91,196,255,.68);transform:translateY(-1px)}
      .iakids-homework-audio-toggle .audio-dot{
        width:8px;height:8px;border-radius:50%;background:#71829a;box-shadow:none;
      }
      .iakids-homework-audio-toggle.enabled{
        color:#dff8ff;border-color:rgba(67,210,255,.62);
        background:linear-gradient(135deg,rgba(18,91,145,.92),rgba(69,49,160,.90));
        box-shadow:0 0 16px rgba(48,178,255,.16);
      }
      .iakids-homework-audio-toggle.enabled .audio-dot{
        background:#45e6a2;box-shadow:0 0 9px rgba(69,230,162,.85);
      }
      .iakids-homework-audio-slot{
        position:absolute;top:72px;right:18px;z-index:75;direction:rtl;
      }
      @media(max-width:900px){.iakids-homework-audio-slot{top:66px;right:12px}}
    `;
    document.head.appendChild(style);
  }

  function updateToggle(){
    const button = document.getElementById("iakidsHomeworkAudioToggle");
    if(!button) return;
    const enabled = window.HOMEWORK_AUDIO_ENABLED === true;
    button.classList.toggle("enabled", enabled);
    button.setAttribute("aria-pressed", enabled ? "true" : "false");
    button.title = enabled ? "כיבוי קול המורה" : "הפעלת קול המורה";
    button.innerHTML = enabled
      ? '<span class="audio-dot"></span><i class="fa-solid fa-volume-high"></i><span>אודיו פעיל</span>'
      : '<span class="audio-dot"></span><i class="fa-solid fa-volume-xmark"></i><span>ללא אודיו</span>';
  }

  function mountToggle(){
    if(!document.body.classList.contains("homework-lesson-mode")) return;
    const chat = document.querySelector(".lesson-chat-workspace");
    if(!chat) return;
    ensureStyles();

    let slot = chat.querySelector(".iakids-homework-audio-slot");
    if(!slot){
      slot = document.createElement("div");
      slot.className = "iakids-homework-audio-slot";
      chat.appendChild(slot);
    }

    let button = document.getElementById("iakidsHomeworkAudioToggle");
    if(!button){
      button = document.createElement("button");
      button.type = "button";
      button.id = "iakidsHomeworkAudioToggle";
      button.className = "iakids-homework-audio-toggle";
      button.addEventListener("click", function(event){
        event.preventDefault();
        event.stopPropagation();
        setPreference(!(window.HOMEWORK_AUDIO_ENABLED === true));
      });
      slot.appendChild(button);
    }
    updateToggle();
  }

  const observer = new MutationObserver(()=>mountToggle());
  observer.observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:["class"]});
  document.addEventListener("DOMContentLoaded", mountToggle);
  setTimeout(mountToggle, 300);
  setTimeout(mountToggle, 1000);

  window.mountHomeworkAudioToggle = mountToggle;
  window.setHomeworkAudioEnabled = setPreference;
})();

'''
    ext = ext.replace(anchor, block + anchor, 1)

# Version/cache bump.
ext = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.49";', ext, count=1)
ext = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0749', ext, count=1)

index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.49', index, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0749', index, count=1)

ext_path.write_text(ext, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')

print('Homework audio toggle added; default off; persisted preference; build 0.7.49')
