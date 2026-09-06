from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')
BACKEND = Path('backend-ai-tutor-he/main.py')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')
backend = BACKEND.read_text(encoding='utf-8')

# -----------------------------------------------------
# 1) Fix child name: actual profile field is child_name.
# -----------------------------------------------------
old = '''    const candidates = [
      kid?.name,
      kid?.first_name,
      kid?.display_name,
      kid?.full_name,
      kid?.child_name,
      kid?.kid_name,
      kid?.nickname,
'''
new = '''    const candidates = [
      kid?.child_name,
      kid?.name,
      kid?.first_name,
      kid?.display_name,
      kid?.full_name,
      kid?.kid_name,
      kid?.nickname,
'''
if old not in core:
    raise SystemExit('kid name candidate block not found')
core = core.replace(old, new, 1)

# -----------------------------------------------------
# 2) Add one authoritative gender helper for Homework Help.
# -----------------------------------------------------
anchor = '''  function getHomeworkSpokenIntro(analysis){\n'''
helper = r'''  function getHomeworkKidGender(){
    const kid =
      window.CURRENT_KID
      || window.SELECTED_KID
      || window.currentKid
      || window.selectedKid
      || {};

    const raw = String(
      kid?.gender
      || kid?.sex
      || window.CURRENT_KID_GENDER
      || ""
    ).trim().toLowerCase();

    if(["female", "f", "girl", "בת", "נקבה"].includes(raw)) return "female";
    if(["male", "m", "boy", "בן", "זכר"].includes(raw)) return "male";
    return "unknown";
  }

  function getHomeworkGenderLanguage(){
    const female = getHomeworkKidGender() === "female";
    return {
      gender: female ? "נקבה" : (getHomeworkKidGender() === "male" ? "זכר" : "לא ידוע"),
      howHelp: female ? "איך תרצי שאעזור?" : "איך תרצה שאעזור?",
      tryAgain: female ? "נסי" : "נסה",
      childLabel: female ? "הילדה" : "הילד"
    };
  }

'''
if 'function getHomeworkKidGender' not in core:
    if anchor not in core:
        raise SystemExit('spoken intro anchor not found')
    core = core.replace(anchor, helper + anchor, 1)

# -----------------------------------------------------
# 3) Make spoken intro use name + correct Hebrew gender.
# -----------------------------------------------------
old = '''  function getHomeworkSpokenIntro(analysis){
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
new = '''  function getHomeworkSpokenIntro(analysis){
    const classification = resolveHomeworkClassification(analysis);
    const subject = classification.subject;
    const topic = classification.topic;
    const kidName = getHomeworkKidName();
    const language = getHomeworkGenderLanguage();

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
'''
if old not in core:
    raise SystemExit('spoken intro 0.7.21 block not found')
core = core.replace(old, new, 1)

# -----------------------------------------------------
# 4) Gender-aware UI wording.
# -----------------------------------------------------
core = core.replace(
    '    title.textContent = "איך תרצה שאעזור?";',
    '    title.textContent = getHomeworkGenderLanguage().howHelp;',
    1
)
core = core.replace(
    "    const helpLine = parts.slice(1).join(' ') || 'איך תרצה שאעזור?';",
    "    const helpLine = parts.slice(1).join(' ') || getHomeworkGenderLanguage().howHelp;",
    1
)

# -----------------------------------------------------
# 5) Send child name + gender explicitly in homework context to tutor.
# -----------------------------------------------------
old = '''  function buildHomeworkContextMessage(analysis){
    const classification = resolveHomeworkClassification(analysis);
    return `
הילד העלה צילום של שיעורי הבית.

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
המתן לבחירת סוג העזרה של הילד.
`.trim();
  }
'''
new = '''  function buildHomeworkContextMessage(analysis){
    const classification = resolveHomeworkClassification(analysis);
    const kidName = getHomeworkKidName() || "לא ידוע";
    const language = getHomeworkGenderLanguage();
    return `
הילד/ה העלה/תה צילום של שיעורי הבית.

שם הילד/ה:
${kidName}

מגדר:
${language.gender}

חובת פנייה:
אם המגדר הוא נקבה, פנה תמיד בלשון נקבה (את, תרצי, נסי, כתבי, חשבי). אם המגדר הוא זכר, פנה בלשון זכר. אל תנחש מגדר לפי השם.

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
'''
if old not in core:
    raise SystemExit('buildHomeworkContextMessage block not found')
core = core.replace(old, new, 1)

# Add gender rule to every help-choice prompt as well, so each turn is self-contained.
old = '''    const classification = resolveHomeworkClassification(analysis);

    const message = `
'''
new = '''    const classification = resolveHomeworkClassification(analysis);
    const kidName = getHomeworkKidName() || "לא ידוע";
    const language = getHomeworkGenderLanguage();

    const message = `
שם הילד/ה: ${kidName}
מגדר: ${language.gender}
חובת פנייה: פנה בהתאם למגדר הרשום. אם נקבה השתמש בלשון נקבה (את/תרצי/נסי/כתבי/חשבי); אם זכר השתמש בלשון זכר. אל תנחש מגדר לפי השם.

'''
if old not in core:
    raise SystemExit('homework choice message anchor not found')
core = core.replace(old, new, 1)

# Gender-aware generic error fallback.
core = core.replace(
    '      addMessage("assistant", "אני כאן. נסה לבחור שוב איך תרצה שאעזור.");',
    '      const language = getHomeworkGenderLanguage();\n      addMessage("assistant", `אני כאן. ${language.tryAgain} לבחור שוב ${language.howHelp}`);',
    1
)

# Expose helpers for diagnostics.
export_anchor = '''  window.playHomeworkTeacherAudio = playHomeworkTeacherAudio;\n'''
exports = '''  window.getHomeworkKidName = getHomeworkKidName;\n  window.getHomeworkKidGender = getHomeworkKidGender;\n'''
if exports not in core:
    if export_anchor not in core:
        raise SystemExit('export anchor not found')
    core = core.replace(export_anchor, exports + export_anchor, 1)

# -----------------------------------------------------
# 6) Backend: make gender authoritative for ALL regular tutor chat.
#    The database profile already contains child_name + gender.
# -----------------------------------------------------
old = '''    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)

    return prompt


def build_structured_lesson_prompt(
'''
new = '''    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)

    child_gender = str(child.get("gender") or "unknown").strip().lower()
    child_name = str(child.get("child_name") or "").strip()

    if child_gender == "female":
        gender_instruction = (
            "The child is female. In Hebrew ALWAYS address her in feminine singular "
            "forms (את, תרצי, נסי, כתבי, חשבי, הצלחת). Never use masculine forms."
        )
    elif child_gender == "male":
        gender_instruction = (
            "The child is male. In Hebrew address him in masculine singular forms."
        )
    else:
        gender_instruction = (
            "The child's gender is unknown. Avoid gendered Hebrew wording where possible; "
            "do not infer gender from the child's name."
        )

    prompt += (
        "\\n\\nAUTHORITATIVE_CHILD_PROFILE:\\n"
        f"child_name: {child_name}\\n"
        f"gender: {child_gender}\\n"
        f"{gender_instruction}"
    )

    return prompt


def build_structured_lesson_prompt(
'''
if old not in backend:
    raise SystemExit('backend build_tutor_prompt return block not found')
backend = backend.replace(old, new, 1)

# -----------------------------------------------------
# 7) Bump visible frontend build/cache version.
# -----------------------------------------------------
index = index.replace('IAKIDS • build 0.7.21', 'IAKIDS • build 0.7.22')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.21";', 'window.IAKIDS_BUILD_VERSION = "0.7.22";')
index = index.replace('/he/workspace/lesson-completion.js?v=0721', '/he/workspace/lesson-completion.js?v=0722')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.21";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.22";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0721', '/he/workspace/lesson-completion-core.js?v=0722')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
BACKEND.write_text(backend, encoding='utf-8')

print('Fixed homework child_name and authoritative gender; build 0.7.22')
