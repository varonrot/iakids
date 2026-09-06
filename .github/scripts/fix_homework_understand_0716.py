from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# 1) Add a helper that extracts only the first worksheet question.
anchor = '  function getChoiceInstruction(choiceId){\n'
helper = r'''  function extractFirstHomeworkQuestion(text){
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

'''
if 'function extractFirstHomeworkQuestion' not in core:
    if anchor not in core:
        raise SystemExit('getChoiceInstruction anchor not found')
    core = core.replace(anchor, helper + anchor, 1)

# 2) Make the pedagogical instruction explicit: one question only, no worksheet recap.
old = '        return "עזור לילד להבין מה בדיוק מבקשים בשאלה. פרק את הדרישה למילים קצרות וברורות. אל תפתור את התרגיל במקומו.";'
new = '        return "התמקד אך ורק בשאלה הראשונה שעדיין לא נענתה. אסור להקריא, להעתיק או לסכם את כל שאלות הדף. הסבר במשפט קצר מה השאלה מבקשת, ואם יש בה כמה חלקים ציין אותם בקצרה. לאחר מכן שאל את הילד שאלה אחת קטנה שמתחילה רק מהחלק הראשון. אל תפתור את התרגיל במקומו ואל תעבור לשאלות הבאות.";'
if old not in core:
    raise SystemExit('understand_question instruction anchor not found')
core = core.replace(old, new, 1)

# 3) Supply the first question separately to the tutor for this help mode.
old = '''    const message = `\nאנחנו ממשיכים עם שיעורי הבית שכבר נותחו.\n\nמקצוע: ${cleanHomeworkValue(analysis.subject) || "לא ידוע"}\nנושא: ${cleanHomeworkValue(analysis.topic) || "לא ידוע"}\nכיתה: ${getHomeworkGrade()}\n\nהילד בחר: ${choice.label}\n\n${getChoiceInstruction(choice.id)}\n\nתוכן התרגיל:\n${analysis.extracted_text || ""}\n\nדבר בעברית קצרה וברורה המותאמת לכיתה ${getHomeworkGrade()}.\n`.trim();\n'''
new = '''    const firstQuestion =\n      choice.id === "understand_question"\n        ? extractFirstHomeworkQuestion(analysis.extracted_text)\n        : "";\n\n    const message = `\nאנחנו ממשיכים עם שיעורי הבית שכבר נותחו.\n\nמקצוע: ${cleanHomeworkValue(analysis.subject) || "לא ידוע"}\nנושא: ${cleanHomeworkValue(analysis.topic) || "לא ידוע"}\nכיתה: ${getHomeworkGrade()}\n\nהילד בחר: ${choice.label}\n\n${getChoiceInstruction(choice.id)}\n\n${firstQuestion ? `השאלה הראשונה בלבד שעליה עובדים עכשיו:\n${firstQuestion}\n\n` : ""}תוכן התרגיל המלא הוא הקשר פנימי בלבד. אל תקריא אותו לילד ואל תעבור על כל השאלות:\n${analysis.extracted_text || ""}\n\nדבר בעברית קצרה וברורה המותאמת לכיתה ${getHomeworkGrade()}.\nבמצב \"להבין מה מבקשים בשאלה\" התגובה הראשונה חייבת להתייחס רק לשאלה הראשונה, בלי רשימה של שאלות אחרות.\n`.trim();\n'''
if old not in core:
    raise SystemExit('runHomeworkChoice message anchor not found')
core = core.replace(old, new, 1)

# 4) Bump frontend/router versions so production visibly confirms the patch.
index = index.replace('IAKIDS • build 0.7.15', 'IAKIDS • build 0.7.16')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.15";', 'window.IAKIDS_BUILD_VERSION = "0.7.16";')
index = index.replace('/he/workspace/lesson-completion.js?v=0715', '/he/workspace/lesson-completion.js?v=0716')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.15";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.16";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0715', '/he/workspace/lesson-completion-core.js?v=0716')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')

print('Homework understand-question 0.7.16 patch applied')
