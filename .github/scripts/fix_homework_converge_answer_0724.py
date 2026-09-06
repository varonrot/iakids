from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# 1) Keep homework help focused on the actual worksheet question.
old = '''      case "explain_topic":
        return "הסבר בקצרה ובשפה המתאימה לכיתה את החומר שצריך לדעת כדי לענות. אחר כך שאל שאלה קצרה שבודקת הבנה.";
      case "hint":
        return "תן רמז קטן אחד בלבד שמקדם את הילד בלי לחשוף את התשובה. המתן לתשובה שלו.";
      case "solve_together":
        return "פתור יחד עם הילד שלב־שלב. בכל פעם תן רק צעד אחד ושאל אותו מה לדעתו הצעד הבא.";
'''
new = '''      case "explain_topic":
        return "הסבר בקצרה רק את הידע שצריך כדי לענות על השאלה הנוכחית בדף. אל תפתח שיחה כללית, ערכית או אישית ואל תשאל על חיי הילד/ה. אחרי ההסבר חזור מיד לשאלה המקורית ובקש מהילד/ה לנסח תשובה קצרה אליה.";
      case "hint":
        return "תן רמז קטן אחד בלבד שמתייחס ישירות לשאלה הנוכחית בדף. אל תשאל שאלות כלליות או שאלות על חיי הילד/ה. מיד אחרי הרמז בקש מהילד/ה לנסות לענות על השאלה המקורית.";
      case "solve_together":
        return "עזור לפתור את השאלה הנוכחית בדף שלב־שלב. כל צעד חייב לקדם ישירות לניסוח תשובה לשאלה המקורית. אל תסטה לשאלות ערכיות, אישיות או כלליות שאינן נדרשות על ידי השאלה. אחרי לכל היותר שני צעדי הכוונה, בקש מהילד/ה לנסח את התשובה לשאלה עצמה.";
'''
if old not in core:
    raise SystemExit('choice instruction block not found')
core = core.replace(old, new, 1)

# 2) Make understand-question also converge back to answering.
old = '''        return "התמקד אך ורק בשאלה הראשונה שעדיין לא נענתה. אסור להקריא, להעתיק או לסכם את כל שאלות הדף. הסבר במשפט קצר מה השאלה מבקשת, ואם יש בה כמה חלקים ציין אותם בקצרה. לאחר מכן שאל את הילד שאלה אחת קטנה שמתחילה רק מהחלק הראשון. אל תפתור את התרגיל במקומו ואל תעבור לשאלות הבאות.";'''
new = '''        return "התמקד אך ורק בשאלה הראשונה שעדיין לא נענתה. אסור להקריא, להעתיק או לסכם את כל שאלות הדף. הסבר במשפט קצר מה השאלה מבקשת. לאחר מכן שאל שאלה מכוונת אחת בלבד שמבוססת על קטע הקריאה ומקדמת ישירות לתשובה. אחרי תשובת הילד/ה, חזור מיד לשאלה המקורית ובקש לנסח תשובה מלאה. אל תעבור לנושאים כלליים, ערכיים או לחיי הילד/ה אלא אם זה כתוב במפורש בשאלה.";'''
if old not in core:
    raise SystemExit('understand instruction not found')
core = core.replace(old, new, 1)

# 3) Strengthen the persistent homework context so future free-text turns also stay on target.
needle = '''חובת פנייה:
אם המגדר הוא נקבה, פנה תמיד בלשון נקבה (את, תרצי, נסי, כתבי, חשבי). אם המגדר הוא זכר, פנה בלשון זכר. אל תנחש מגדר לפי השם.

מקצוע שזוהה:
'''
replacement = '''חובת פנייה:
אם המגדר הוא נקבה, פנה תמיד בלשון נקבה (את, תרצי, נסי, כתבי, חשבי). אם המגדר הוא זכר, פנה בלשון זכר. אל תנחש מגדר לפי השם.

כלל שיעורי בית מחייב:
המטרה היא להגיע לתשובה על השאלה שמופיעה בדף, לא לנהל שיחה כללית סביב הנושא. כל הסבר, רמז או שאלת ביניים חייבים לקדם ישירות לתשובה לשאלה הנוכחית. אל תשאל שאלות על חיי הילד/ה, ערכים, רגשות או דוגמאות אישיות אלא אם השאלה בדף עצמה מבקשת זאת. אחרי לכל היותר 1-2 שאלות הכוונה, החזר את הילד/ה לניסוח תשובה לשאלה המקורית.

מקצוע שזוהה:
'''
if needle not in core:
    raise SystemExit('context gender anchor not found')
core = core.replace(needle, replacement, 1)

# 4) In each selected help request, send the exact current question explicitly.
needle = '''    const classification = resolveHomeworkClassification(analysis);
    const kidName = getHomeworkKidName(analysis) || "לא ידוע";
    const language = getHomeworkGenderLanguage(analysis);

    const message = `
'''
replacement = '''    const classification = resolveHomeworkClassification(analysis);
    const kidName = getHomeworkKidName(analysis) || "לא ידוע";
    const language = getHomeworkGenderLanguage(analysis);
    const currentQuestion = extractFirstHomeworkQuestion(analysis.extracted_text) || "לא זוהתה שאלה";

    const message = `
שאלת שיעורי הבית הנוכחית:
${currentQuestion}

מטרת הדיאלוג המחייבת:
להוביל את הילד/ה לענות על השאלה הזאת עצמה. אין לסטות לשאלות כלליות או אישיות שאינן נדרשות כדי לענות עליה.

'''
if needle not in core:
    raise SystemExit('choice message anchor not found')
core = core.replace(needle, replacement, 1)

# 5) Bump build/cache.
index = index.replace('IAKIDS • build 0.7.23', 'IAKIDS • build 0.7.24')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.23";', 'window.IAKIDS_BUILD_VERSION = "0.7.24";')
index = index.replace('/he/workspace/lesson-completion.js?v=0723', '/he/workspace/lesson-completion.js?v=0724')
ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.23";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.24";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0723', '/he/workspace/lesson-completion-core.js?v=0724')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Homework flow now converges to the actual worksheet answer; build 0.7.24')

# trigger
