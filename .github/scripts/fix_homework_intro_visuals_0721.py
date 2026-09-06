from pathlib import Path

# trigger 0.7.21
CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# -----------------------------------------------------
# 1) Make child-name detection robust.
# -----------------------------------------------------
old = '''  function getHomeworkSpokenIntro(analysis){
    const classification = resolveHomeworkClassification(analysis);
    const subject = classification.subject;
    const topic = classification.topic;

    const kidName = String(
      window.CURRENT_KID?.name
      || window.CURRENT_KID?.first_name
      || window.CURRENT_KID?.display_name
      || ""
    ).trim();

    const greeting = kidName
      ? `היי ${kidName}, `
      : "היי, ";

    if(subject && topic){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject} בנושא ${topic}. איך תרצה שאעזור?`;
    }

    if(subject){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject}. איך תרצה שאעזור?`;
    }

    if(topic){
      return `${greeting}זיהיתי את הנושא ${topic}. איך תרצה שאעזור?`;
    }

    return `${greeting}זיהיתי את שיעורי הבית. איך תרצה שאעזור?`;
  }
'''

new = '''  function getHomeworkKidName(){
    const kid =
      window.CURRENT_KID
      || window.SELECTED_KID
      || window.currentKid
      || window.selectedKid
      || {};

    const candidates = [
      kid?.name,
      kid?.first_name,
      kid?.display_name,
      kid?.full_name,
      kid?.child_name,
      kid?.kid_name,
      kid?.nickname,
      window.CURRENT_KID_NAME,
      window.currentKidName,
      window.selectedKidName
    ];

    for(const candidate of candidates){
      const value = String(candidate || "").trim();
      if(value) return value.split(/\\s+/)[0];
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
      if(value) return value.split(/\\s+/)[0];
    }

    return "";
  }

  function getHomeworkSpokenIntro(analysis){
    const classification = resolveHomeworkClassification(analysis);
    const subject = classification.subject;
    const topic = classification.topic;
    const kidName = getHomeworkKidName();

    const greeting = kidName
      ? `היי ${kidName}, `
      : "היי, ";

    if(subject && topic){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject} בנושא ${topic}. איך תרצה שאעזור?`;
    }

    if(subject){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject}. איך תרצה שאעזור?`;
    }

    if(topic){
      return `${greeting}זיהיתי את הנושא ${topic}. איך תרצה שאעזור?`;
    }

    return `${greeting}זיהיתי את שיעורי הבית. איך תרצה שאעזור?`;
  }
'''

if old not in core:
    raise SystemExit('0.7.20 homework spoken intro block not found')
core = core.replace(old, new, 1)

# -----------------------------------------------------
# 2) Add teacher avatar to the detection card.
# -----------------------------------------------------
old = '''      <div class="homework-detection-card">
        <div class="homework-detection-icon"><i class="fa-solid fa-check"></i></div>
        <div class="homework-detection-copy">
'''
new = '''      <div class="homework-detection-card">
        <img class="homework-detection-teacher" src="/assets/lesson/lesson-teacher.webp" alt="המורה AI">
        <div class="homework-detection-icon"><span aria-hidden="true">✓</span></div>
        <div class="homework-detection-copy">
'''
if old not in core:
    raise SystemExit('detection card anchor not found')
core = core.replace(old, new, 1)

# -----------------------------------------------------
# 3) Use guaranteed visible button icons instead of Font Awesome glyphs.
# -----------------------------------------------------
old = '''      button.innerHTML = `<i class="fa-solid ${choice.icon}" aria-hidden="true"></i><span>${choice.label}</span>`;
'''
new = '''      const helpIconMap = {
        understand_question: "?",
        explain_topic: "▤",
        hint: "✦",
        solve_together: "→",
        check_answer: "✓"
      };
      button.innerHTML = `<span class="homework-help-icon" aria-hidden="true">${helpIconMap[choice.id] || "•"}</span><span>${choice.label}</span>`;
'''
if old not in core:
    raise SystemExit('help button icon anchor not found')
core = core.replace(old, new, 1)

# -----------------------------------------------------
# 4) Add CSS for avatar and icon badges.
# -----------------------------------------------------
css_anchor = '''      .homework-help-choice i{
        width:20px;
        color:#69d7ff;
        text-align:center;
      }
'''
css_new = '''      .homework-help-choice i{
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
'''
if css_anchor not in core:
    raise SystemExit('help icon CSS anchor not found')
core = core.replace(css_anchor, css_new, 1)

# -----------------------------------------------------
# 5) Bump build/cache versions.
# -----------------------------------------------------
index = index.replace('IAKIDS • build 0.7.20', 'IAKIDS • build 0.7.21')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.20";', 'window.IAKIDS_BUILD_VERSION = "0.7.21";')
index = index.replace('/he/workspace/lesson-completion.js?v=0720', '/he/workspace/lesson-completion.js?v=0721')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.20";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.21";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0720', '/he/workspace/lesson-completion-core.js?v=0721')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')

print('Fixed homework child name, teacher avatar, and help icons; build 0.7.21')
