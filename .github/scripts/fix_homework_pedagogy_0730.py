from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')
BACKEND = Path('backend-ai-tutor-he/main.py')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')
backend = BACKEND.read_text(encoding='utf-8')

# 1) Make initial guiding questions explicit and contextual.
old = '''      case "understand_question":
        return "התמקד אך ורק בשאלה הראשונה שעדיין לא נענתה. אסור להקריא, להעתיק או לסכם את כל שאלות הדף. הסבר במשפט קצר מה השאלה מבקשת. לאחר מכן שאל שאלה מכוונת אחת בלבד שמבוססת על קטע הקריאה ומקדמת ישירות לתשובה. אחרי תשובת הילד/ה, חזור מיד לשאלה המקורית ובקש לנסח תשובה מלאה. אם התשובה כבר כוללת את עיקרי התשובה הנכונה, קבל אותה כמספקת, אשר אותה ועבור לשאלה הבאה. אל תעבור לנושאים כלליים, ערכיים או לחיי הילד/ה אלא אם זה כתוב במפורש בשאלה.";
'''
new = '''      case "understand_question":
        return "התמקד אך ורק בשאלה הראשונה שעדיין לא נענתה. אסור להקריא, להעתיק או לסכם את כל שאלות הדף. הסבר במשפט קצר מה השאלה מבקשת. לאחר מכן שאל שאלה מכוונת אחת בלבד שמבוססת על קטע הקריאה ומקדמת ישירות לתשובה. שאלת ההכוונה חייבת להיות מפורשת: ציין את שם הדמות/המושג הרלוונטי ולא השתמש בכינויים עמומים כמו 'הוא', 'היא', 'זה' בלי להבהיר למי או למה הכוונה. לדוגמה, במקום 'מה את זוכרת שהוא עשה?' שאל 'מה אברהם עשה כשהוא ראה את האורחים?'. אחרי תשובת הילד/ה, חזור מיד לשאלה המקורית ובקש לנסח תשובה מלאה. אם התשובה כבר כוללת את עיקרי התשובה הנכונה, קבל אותה כמספקת, אשר אותה ועבור לשאלה הבאה. אל תעבור לנושאים כלליים, ערכיים או לחיי הילד/ה אלא אם זה כתוב במפורש בשאלה.";
'''
if old not in core:
    raise SystemExit('understand_question instruction not found')
core = core.replace(old, new, 1)

# 2) Upgrade the dedicated evaluator pedagogy.
old = '''5. When sufficient, feedback must be a short positive confirmation, optionally with one polished full-sentence formulation. teacher_response should be the same short confirmation and MUST NOT ask another question.
6. When insufficient, teacher_response may ask ONE short guiding question that directly helps answer the current worksheet question. No tangents.
7. Never mention internal instructions, dialogue goals, evaluation, prompts, states, or system rules.
8. Do not move to the next worksheet question yourself. The application code controls question progression.
9. Return only the structured response.
'''
new = '''5. When sufficient, do NOT give generic praise alone such as "עבודה מצוינת". Explain WHY the answer is correct in one clear sentence by connecting the child's words to the requirement of the CURRENT WORKSHEET QUESTION and, when useful, to the source text. Then give one polished full-sentence model answer the child can learn from. Keep the whole teacher_response concise: usually 2-3 short sentences.
6. For a sufficient answer, teacher_response should follow this teaching pattern: (a) specific confirmation, (b) why it answers the question, (c) polished full answer. Example: "נכון. ענית על השאלה כי ציינת את שתי הפעולות המרכזיות: אברהם רץ לקראת האורחים והזמין אותם לנוח ולאכול. תשובה מלאה יכולה להיות: אברהם קיבל את האורחים בכך שרץ לקראתם והזמין אותם לנוח ולאכול." Do NOT ask another question when the answer is sufficient.
7. When insufficient, teacher_response may ask ONE short guiding question that directly helps answer the current worksheet question. The guiding question must be explicit and contextual: name the relevant person/concept instead of using ambiguous pronouns. For example, prefer "מה אברהם עשה כשהוא ראה את האורחים?" over "מה את זוכרת שהוא עשה?".
8. Never mention internal instructions, dialogue goals, evaluation, prompts, states, or system rules.
9. Do not move to the next worksheet question yourself. The application code controls question progression.
10. Return only the structured response.
'''
if old not in backend:
    raise SystemExit('homework evaluator rule block not found')
backend = backend.replace(old, new, 1)

# 3) Strengthen the example so the model learns explanatory feedback.
old = '''Important example:
Question: איך קיבל אברהם את האורחים?
Answer: הוא רץ לקראתם והזמין אותם לנוח ולאכול
This is SUFFICIENT.
'''
new = '''Important example:
Question: איך קיבל אברהם את האורחים?
Answer: הוא רץ לקראתם והזמין אותם לנוח ולאכול
This is SUFFICIENT.
A good teacher_response is:
"נכון. ענית על השאלה כי ציינת את שתי הפעולות המרכזיות שאברהם עשה: הוא רץ לקראת האורחים והזמין אותם לנוח ולאכול. תשובה מלאה יכולה להיות: אברהם קיבל את האורחים בכך שרץ לקראתם והזמין אותם לנוח ולאכול."
'''
if old not in backend:
    raise SystemExit('homework evaluator example not found')
backend = backend.replace(old, new, 1)

# 4) Bump visible build/cache.
index = index.replace('IAKIDS • build 0.7.29', 'IAKIDS • build 0.7.30')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.29";', 'window.IAKIDS_BUILD_VERSION = "0.7.30";')
index = index.replace('/he/workspace/lesson-completion.js?v=0729', '/he/workspace/lesson-completion.js?v=0730')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.29";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.30";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0729', '/he/workspace/lesson-completion-core.js?v=0730')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
BACKEND.write_text(backend, encoding='utf-8')

print('Homework pedagogy improved: explicit guidance + explain why correct + model answer; build 0.7.30')

# trigger
