from pathlib import Path

EXT = Path('he/workspace/lesson-completion.js')
CORE = Path('he/workspace/lesson-completion-core.js')
INDEX = Path('he/workspace/index.html')

ext = EXT.read_text(encoding='utf-8')
core = CORE.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# 1) Force true full-height side-by-side worksheet/notebook layout.
old = '''      .homework-dual-workspace{\n        position:absolute;\n        inset:0;\n        display:grid;\n        grid-template-columns:minmax(0,1.08fr) minmax(0,1fr);\n        gap:14px;\n        padding:12px;\n        direction:ltr;\n        background:#031022;\n      }\n'''
new = '''      .homework-dual-workspace{\n        position:absolute;\n        inset:0;\n        display:grid!important;\n        grid-template-columns:minmax(0,52fr) minmax(0,48fr);\n        grid-template-rows:minmax(0,1fr);\n        align-items:stretch!important;\n        justify-items:stretch!important;\n        gap:14px;\n        padding:12px;\n        box-sizing:border-box;\n        direction:ltr;\n        background:#031022;\n      }\n'''
if old not in ext:
    raise SystemExit('dual workspace style block not found')
ext = ext.replace(old, new, 1)

old = '''      .homework-sheet-pane,\n      .homework-notebook-pane{\n        min-width:0;\n        width:100%;\n        min-height:0;\n        overflow:hidden;\n'''
new = '''      .homework-sheet-pane,\n      .homework-notebook-pane{\n        min-width:0;\n        width:100%;\n        height:100%;\n        min-height:0;\n        align-self:stretch;\n        overflow:hidden;\n'''
if old not in ext:
    raise SystemExit('pane sizing block not found')
ext = ext.replace(old, new, 1)

old = '''      .homework-notebook-pane{\n        display:flex;\n        flex-direction:column;\n        direction:rtl;\n      }\n'''
new = '''      .homework-notebook-pane{\n        display:flex;\n        flex-direction:column;\n        direction:rtl;\n        height:100%;\n        min-height:0;\n      }\n'''
if old not in ext:
    raise SystemExit('notebook pane block not found')
ext = ext.replace(old, new, 1)

old = '''      .homework-notebook-page{\n        position:relative;\n        flex:1;\n        overflow:auto;\n'''
new = '''      .homework-notebook-page{\n        position:relative;\n        flex:1 1 auto;\n        min-height:0;\n        height:calc(100% - 44px);\n        overflow:auto;\n'''
if old not in ext:
    raise SystemExit('notebook page block not found')
ext = ext.replace(old, new, 1)

# 2) Hebrew-only normalization for writing/composition labels.
old = '''    if(/literature/.test(lower)) return "ספרות";\n    if(/reading comprehension/.test(lower)) return "הבנת הנקרא";\n    if(/geograph|גאוגר|גיאוגר/.test(lower)) return "גאוגרפיה";\n'''
new = '''    if(/literature/.test(lower)) return "ספרות";\n    if(/reading comprehension/.test(lower)) return "הבנת הנקרא";\n    if(/writing\\s*(and|&)\\s*composition|writing composition|composition|כתיבה|הבעה/.test(lower)) return "עברית";\n    if(/geograph|גאוגר|גיאוגר/.test(lower)) return "גאוגרפיה";\n'''
if old not in core:
    raise SystemExit('subject normalization anchor not found')
core = core.replace(old, new, 1)

old = '''    if(/ecosystem/.test(lower)) return "מערכות אקולוגיות";\n    if(/reading comprehension/.test(lower)) return "הבנת הנקרא";\n    if(/abraham/.test(lower) && /guest|hospitality/.test(lower)) return "אברהם מכניס אורחים";\n'''
new = '''    if(/ecosystem/.test(lower)) return "מערכות אקולוגיות";\n    if(/reading comprehension/.test(lower)) return "הבנת הנקרא";\n    if(/writing\\s*(and|&)\\s*composition|writing composition|composition/.test(lower)) return "כתיבה והבעה";\n    if(/abraham/.test(lower) && /guest|hospitality/.test(lower)) return "אברהם מכניס אורחים";\n'''
if old not in core:
    raise SystemExit('topic normalization anchor not found')
core = core.replace(old, new, 1)

# Ensure task type also becomes Hebrew for writing assignments.
old = '''    if(readingTask){\n      taskType = "הבנת הנקרא";\n    }\n'''
new = '''    if(readingTask){\n      taskType = "הבנת הנקרא";\n    }\n\n    const writingTask =\n      /writing\\s*(and|&)\\s*composition|writing composition|composition|כתיבה|הבעה/i.test(combined);\n    if(writingTask){\n      taskType = "כתיבה והבעה";\n      if(!topic || /writing|composition/i.test(topic)) topic = "כתיבה והבעה";\n      if(!subject || /writing|composition/i.test(subject)) subject = "עברית";\n    }\n'''
if old not in core:
    raise SystemExit('task type block not found')
core = core.replace(old, new, 1)

# 3) Keep the tutor grounded in the exact uploaded assignment, especially for writing tasks.
old = '''      case "solve_together":\n        return "עזור לפתור את השאלה הנוכחית בדף שלב־שלב. כל צעד חייב לקדם ישירות לניסוח תשובה לשאלה המקורית. אל תסטה לשאלות ערכיות, אישיות או כלליות שאינן נדרשות על ידי השאלה. אחרי לכל היותר שני צעדי הכוונה, בקש מהילד/ה לנסח את התשובה לשאלה עצמה. אם התשובה כבר כוללת את עיקרי התשובה הנכונה, קבל אותה מיד כמספקת, שפר ניסוח במשפט אחד אם צריך ועבור לשאלה הבאה — בלי שאלת הרחבה נוספת.";\n'''
new = '''      case "solve_together":\n        return "עזור לפתור את המשימה הנוכחית בדף שלב־שלב. לפני שאלת הכוונה, אמור בקצרה מה בדיוק מבקשים לעשות לפי הדף ואיך ניגשים לזה. אם זו משימת כתיבה, אל תשאל שאלות כלליות כמו 'מה היית רוצה לכלול בכתיבה שלך?'. במקום זאת, התבסס על ההוראה המדויקת בדף, חלק אותה לרכיבים הנדרשים, ועבוד על הרכיב הראשון. כל צעד חייב לקדם ישירות לתוצר שהדף מבקש. אל תסטה לנושאים אישיים שאינם נדרשים במפורש. אחרי לכל היותר שני צעדי הכוונה, בקש מהילד/ה לנסח תשובה או משפט למשימה עצמה.";\n'''
if old not in core:
    raise SystemExit('solve together instruction not found')
core = core.replace(old, new, 1)

# Add a global grounding rule to every homework choice request.
old = '''מטרת הדיאלוג המחייבת:\nלהוביל את הילד/ה לענות על השאלה הזאת עצמה. אין לסטות לשאלות כלליות או אישיות שאינן נדרשות כדי לענות עליה.\n'''
new = '''מטרת הדיאלוג המחייבת:\nלהוביל את הילד/ה לענות על השאלה או לבצע את ההוראה שמופיעה בפועל בדף. אין לסטות לשאלות כלליות או אישיות שאינן נדרשות כדי לענות עליה.\nאם זו משימת כתיבה/הבעה, יש לזהות מתוך תוכן הדף מה בדיוק התלמיד/ה נדרש/ת לכתוב, לומר זאת במפורש, ולבנות יחד את התשובה לפי רכיבי ההוראה. אסור לשאול 'מה היית רוצה לכלול?' כאשר הדף כבר מגדיר מה צריך לכלול.\n'''
if old not in core:
    raise SystemExit('dialogue goal block not found')
core = core.replace(old, new, 1)

# 4) Bump visible build/cache to 0.7.37.
index = index.replace('IAKIDS • build 0.7.36', 'IAKIDS • build 0.7.37')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.36";', 'window.IAKIDS_BUILD_VERSION = "0.7.37";')
index = index.replace('/he/workspace/lesson-completion.js?v=0736', '/he/workspace/lesson-completion.js?v=0737')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.36";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.37";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0736', '/he/workspace/lesson-completion-core.js?v=0737')

EXT.write_text(ext, encoding='utf-8')
CORE.write_text(core, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')

print('0.7.37 applied: full-height split, Hebrew writing labels, grounded writing tutor')
