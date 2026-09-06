from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')
BACKEND = Path('backend-ai-tutor-he/main.py')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')
backend = BACKEND.read_text(encoding='utf-8')

# Strengthen the initial homework-help strategy: teach HOW to approach the question first.
old = '''      case "understand_question":
        return "התמקד אך ורק בשאלה הראשונה שעדיין לא נענתה. אסור להקריא, להעתיק או לסכם את כל שאלות הדף. הסבר במשפט קצר מה השאלה מבקשת. לאחר מכן שאל שאלה מכוונת אחת בלבד שמבוססת על קטע הקריאה ומקדמת ישירות לתשובה. שאלת ההכוונה חייבת להיות מפורשת: ציין את שם הדמות/המושג הרלוונטי ולא השתמש בכינויים עמומים כמו 'הוא', 'היא', 'זה' בלי להבהיר למי או למה הכוונה. לדוגמה, במקום 'מה את זוכרת שהוא עשה?' שאל 'מה אברהם עשה כשהוא ראה את האורחים?'. אחרי תשובת הילד/ה, חזור מיד לשאלה המקורית ובקש לנסח תשובה מלאה. אם התשובה כבר כוללת את עיקרי התשובה הנכונה, קבל אותה כמספקת, אשר אותה ועבור לשאלה הבאה. אל תעבור לנושאים כלליים, ערכיים או לחיי הילד/ה אלא אם זה כתוב במפורש בשאלה.";
'''
new = '''      case "understand_question":
        return "התמקד אך ורק בשאלה הראשונה שעדיין לא נענתה. קודם כל למד את הילד/ה איך לגשת לשאלה, ורק אחר כך שאל שאלת הכוונה. אם יש קטע קריאה: אמור לקרוא שוב את הקטע, לחפש את המשפטים שמתייחסים ישירות לשאלה, ולשים לב למילות פעולה/מושגים מרכזיים. אם זו שאלה חשבונית: אמור לזהות את הנתונים ומה בדיוק צריך לחשב. אם זו שאלה במדעים/ידע: אמור לאתר את העובדה או המושג הרלוונטי. אסור להתחיל ב'מה את חושבת?' או 'מה את זוכרת?' כשאפשר למצוא את התשובה מתוך הדף. אחרי הוראת האסטרטגיה שאל שאלה מכוונת אחת בלבד, מפורשת ובהקשר מלא. לדוגמה: 'קראי שוב את הקטע וחפשי מה אברהם עשה כשהאורחים הגיעו. אילו פעולות כתובות שם?'. אסור להקריא או לסכם את כל שאלות הדף. אחרי תשובת הילד/ה, חזור מיד לשאלה המקורית ובקש לנסח תשובה מלאה. אם התשובה כבר כוללת את עיקרי התשובה הנכונה, קבל אותה כמספקת, אשר אותה ועבור לשאלה הבאה.";
'''
if old not in core:
    raise SystemExit('understand_question instruction not found')
core = core.replace(old, new, 1)

old = '''      case "solve_together":
        return "עזור לפתור את השאלה הנוכחית בדף שלב־שלב. כל צעד חייב לקדם ישירות לניסוח תשובה לשאלה המקורית. אל תסטה לשאלות ערכיות, אישיות או כלליות שאינן נדרשות על ידי השאלה. אחרי לכל היותר שני צעדי הכוונה, בקש מהילד/ה לנסח את התשובה לשאלה עצמה. אם התשובה כבר כוללת את עיקרי התשובה הנכונה, קבל אותה מיד כמספקת, שפ...'''
'''
# The source line may be long/truncated in earlier inspection, so patch by exact prefix if present.
if '      case "solve_together":\n' in core:
    start = core.index('      case "solve_together":\n')
    end = core.index('      case "check_answer":\n', start)
    replacement = '''      case "solve_together":
        return "עזור לפתור את השאלה הנוכחית בדף שלב־שלב, אבל השלב הראשון תמיד צריך ללמד איך ניגשים לשאלה. אם יש קטע קריאה, הפנה את הילד/ה לקרוא שוב ולמצוא את החלק שעונה על השאלה; בקש לזהות מילות פעולה, שמות או עובדות רלוונטיות. אם זו שאלה חשבונית, עזור לזהות נתונים ומה מבקשים לחשב. אם זו שאלת ידע, עזור לאתר את המושג או העובדה המתאימים. אל תתחיל בשאלה כללית כמו 'מה את חושבת?' או 'מה את זוכרת?' כשאפשר לכוון למקור המידע. אחרי שלב האיתור שאל שאלה מכוונת אחת בלבד שמקדמת ישירות לתשובה. אחרי לכל היותר שני צעדי הכוונה, בקש לנסח את התשובה לשאלה עצמה. אל תסטה לנושאים אישיים או כלליים.";
'''
    core = core[:start] + replacement + core[end:]

# Strengthen the dedicated evaluator for insufficient answers too.
old = '''7. When insufficient, teacher_response may ask ONE short guiding question that directly helps answer the current worksheet question. The guiding question must be explicit and contextual: name the relevant person/concept instead of using ambiguous pronouns. For example, prefer "מה אברהם עשה כשהוא ראה את האורחים?" over "מה את זוכרת שהוא עשה?".
'''
new = '''7. When insufficient, first teach the approach in one short sentence, then ask ONE short guiding question. If the source contains the answer, direct the child back to the relevant part of the source instead of asking "what do you think" or "what do you remember". For reading comprehension, say to reread and look for the sentence/actions that answer the question; for math, identify givens and what must be calculated; for science/knowledge, locate the relevant fact/concept. The guiding question must be explicit and contextual. Example: "קראי שוב את הקטע וחפשי מה אברהם עשה כשהאורחים הגיעו. אילו פעולות כתובות שם?"
'''
if old not in backend:
    raise SystemExit('backend insufficient-answer rule not found')
backend = backend.replace(old, new, 1)

# Add an explicit strategy rule to the initial tutor-choice prompt.
needle = '''הילד בחר: ${choice.label}\n\n${getChoiceInstruction(choice.id)}\n'''
replacement = '''הילד בחר: ${choice.label}\n\nכלל גישה לשאלה: לפני שמבקשים מהילד/ה תשובה, למד/י בקצרה איך למצוא אותה. אם יש קטע קריאה, הפנה/י לקריאה חוזרת ולאיתור המשפטים או מילות הפעולה הרלוונטיים. אל תפתח/י ב\"מה את/ה חושב/ת?\" או \"מה את/ה זוכר/ת?\" כאשר התשובה נמצאת בדף.\n\n${getChoiceInstruction(choice.id)}\n'''
if needle not in core:
    raise SystemExit('choice prompt anchor not found')
core = core.replace(needle, replacement, 1)

# Bump visible build/cache.
index = index.replace('IAKIDS • build 0.7.32', 'IAKIDS • build 0.7.33')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.32";', 'window.IAKIDS_BUILD_VERSION = "0.7.33";')
index = index.replace('/he/workspace/lesson-completion.js?v=0732', '/he/workspace/lesson-completion.js?v=0733')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.32";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.33";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0732', '/he/workspace/lesson-completion-core.js?v=0733')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
BACKEND.write_text(backend, encoding='utf-8')

print('Homework approach strategy added: teach how to find answer before asking; build 0.7.33')
