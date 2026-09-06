from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# -----------------------------------------------------
# 1) Hebrew display normalization for detected subject/topic
# -----------------------------------------------------
anchor = '''  function getHomeworkDetectionSentence(analysis){\n'''
helpers = r'''  function normalizeHomeworkSubjectForDisplay(value){
    const raw = cleanHomeworkValue(value);
    const lower = raw.toLowerCase();

    if(!raw) return "";
    if(/תנ[״\"]?ך|bible|biblical|scripture/.test(lower) || /תנ[״\"]?ך/.test(raw)) return "תנ״ך";
    if(/science|מדע/.test(lower) || raw.includes("מדעים")) return "מדעים";
    if(/math|mathematics|מתמט/.test(lower) || raw.includes("חשבון")) return "מתמטיקה";
    if(/hebrew|עברית/.test(lower)) return "עברית";
    if(/english|אנגלית/.test(lower)) return "אנגלית";
    if(/history|היסטור/.test(lower)) return "היסטוריה";
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

    return raw;
  }

'''
if 'function normalizeHomeworkSubjectForDisplay' not in core:
    if anchor not in core:
        raise SystemExit('detection function anchor not found')
    core = core.replace(anchor, helpers + anchor, 1)

old = '''  function getHomeworkDetectionSentence(analysis){\n    const subject = cleanHomeworkValue(analysis?.subject);\n    const topic = cleanHomeworkValue(analysis?.topic);\n'''
new = '''  function getHomeworkDetectionSentence(analysis){\n    const subject = normalizeHomeworkSubjectForDisplay(analysis?.subject);\n    const topic = normalizeHomeworkTopicForDisplay(analysis?.topic);\n'''
if old not in core:
    raise SystemExit('detection value block not found')
core = core.replace(old, new, 1)

# -----------------------------------------------------
# 2) Add premium status/detection card styles
# -----------------------------------------------------
style_anchor = '''      .homework-help-options-row{\n'''
style_css = r'''      .homework-reading-status-row,
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
'''
if '.homework-reading-status-card' not in core:
    if style_anchor not in core:
        raise SystemExit('help styles anchor not found')
    core = core.replace(style_anchor, style_css + style_anchor, 1)

# -----------------------------------------------------
# 3) Add card renderers before getHomeworkMessagesContainer
# -----------------------------------------------------
render_anchor = '''  function getHomeworkMessagesContainer(){\n'''
renderers = r'''  function removeHomeworkReadingStatus(){
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

    const subject = normalizeHomeworkSubjectForDisplay(analysis?.subject);
    const topic = normalizeHomeworkTopicForDisplay(analysis?.topic);
    const sentence = getHomeworkIntroByGrade(analysis);
    const parts = sentence.split('\n');
    const mainLine = parts[0] || 'זיהיתי את שיעורי הבית.';
    const helpLine = parts.slice(1).join(' ') || 'איך תרצה שאעזור?';

    const row = document.createElement('div');
    row.className = 'homework-detection-row';
    row.innerHTML = `
      <div class="homework-detection-card">
        <div class="homework-detection-icon"><i class="fa-solid fa-check"></i></div>
        <div class="homework-detection-copy">
          <div class="homework-detection-title">${mainLine}</div>
          <div class="homework-detection-text">${helpLine}</div>
          <div class="homework-detection-tags">
            ${subject ? `<span class="homework-detection-tag">${subject}</span>` : ''}
            ${topic ? `<span class="homework-detection-tag">${topic}</span>` : ''}
          </div>
        </div>
      </div>`;

    messages.appendChild(row);
    return true;
  }

'''
if 'function showHomeworkReadingStatus' not in core:
    if render_anchor not in core:
        raise SystemExit('messages container anchor not found')
    core = core.replace(render_anchor, renderers + render_anchor, 1)

# -----------------------------------------------------
# 4) Replace analysis intro bubble with premium detection card
# -----------------------------------------------------
old = '''    setHomeworkSidebarStep(2);\n    addMessage("assistant", getHomeworkIntroByGrade(analysis));\n    renderHomeworkHelpOptions();\n'''
new = '''    setHomeworkSidebarStep(2);\n    removeHomeworkReadingStatus();\n    renderHomeworkDetectionCard(analysis);\n    renderHomeworkHelpOptions();\n'''
if old not in core:
    raise SystemExit('smart intro render block not found')
core = core.replace(old, new, 1)

# -----------------------------------------------------
# 5) Override old generic white status bubble
# -----------------------------------------------------
export_anchor = '''  window.getHomeworkIntroByGrade = getHomeworkIntroByGrade;\n'''
override = '''  window.showHomeworkStatus = function(){\n    return showHomeworkReadingStatus();\n  };\n\n'''
if 'window.showHomeworkStatus = function' not in core:
    if export_anchor not in core:
        raise SystemExit('export anchor not found')
    core = core.replace(export_anchor, override + export_anchor, 1)

# -----------------------------------------------------
# 6) Bump versions/cache keys
# -----------------------------------------------------
index = index.replace('IAKIDS • build 0.7.14', 'IAKIDS • build 0.7.15')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.14";', 'window.IAKIDS_BUILD_VERSION = "0.7.15";')
index = index.replace('/he/workspace/lesson-completion.js?v=0714', '/he/workspace/lesson-completion.js?v=0715')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.14";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.15";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0714', '/he/workspace/lesson-completion-core.js?v=0715')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')

print('Homework status/detection 0.7.15 patch applied')
