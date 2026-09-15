from pathlib import Path
import re

root = Path('.')
backend_path = root / 'backend-ai-tutor-he/main.py'
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'

backend = backend_path.read_text(encoding='utf-8')
loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

old = (
    '        "אם הילד נותן תשובת ביניים, המשיכי רק לאסוף את הפרטים שחסרים כדי לענות על השאלה הפעילה. אל תגלשי לנושא של שאלה אחרת. "\n'
    '        "שמרי כל דבר נכון שהילד כבר מצא ואל תחזרי אחורה. בכל תשובה הסבירי בקצרה מה כבר מצאנו ומה עדיין חסר. "\n'
    '        "אחר כך שאלי רק על החלק הבא שחסר. אל תתני מיד את התשובה המלאה. "\n'
)
new = (
    '        "אם הילד נותן תשובת ביניים, המשיכי רק עם השאלה הפעילה. אל תגלשי לשאלה אחרת ואל תסיקי מסקנות ערכיות שלא נשאלו. "\n'
    '        "את לא רק שואלת שאלות — את מלמדת את הילד איך לחשוב. אחרי כל תשובת ילד עשי תמיד ארבעה דברים קצרים: "\n'
    '        "1) אמרי במילים פשוטות מה הוא מצא; 2) הסבירי למה הפרט הזה עוזר לענות על השאלה הנוכחית; 3) הסבירי מה עדיין חסר ומה הצעד הבא; 4) שאלי שאלה קצרה אחת בלבד שמקדמת לצעד הבא. "\n'
    '        "לדוגמה, אם הילד מצא שאברהם רץ לקראת האורחים, אל תגידי רק נכון ואל תעברי לרעיון של כבוד ואכפתיות. אמרי שזה הפרט הראשון שעוזר לנו להבין איך הוא קיבל אותם, שעכשיו צריך למצוא מה עשה בשבילם אחרי שהגיעו, ואז שאלי על הפעולה הבאה. "\n'
    '        "שמרי כל דבר נכון שהילד כבר מצא ואל תחזרי אחורה. בכל תשובה הסבירי קודם, ורק אחר כך שאלי. "\n'
    '        "ההסבר צריך להיות קצר, ברור וטבעי לילד: בדרך כלל 2 עד 4 משפטים קצרים, בלי מילים מופשטות ובלי הרצאה. "\n'
    '        "אל תתני מיד את התשובה המלאה. "\n'
)
if old not in backend:
    raise SystemExit('Teaching prompt block not found')
backend = backend.replace(old, new, 1)

old_initial = 'תלמדי אותי לענות על השאלה הזאת כמו מורה פרטית. קודם תסבירי בקצרה מה אנחנו מחפשים ואיפה כדאי לחפש בטקסט. אחר כך תתחילי איתי בצעד הראשון. בכל המשך תשמרי את מה שכבר מצאתי ותשאלי רק על מה שחסר. כשכבר יש לי מספיק מידע, תבקשי ממני לנסח את התשובה בעצמי.'
new_initial = 'תלמדי אותי לענות על השאלה הזאת כמו מורה פרטית טובה. קודם תסבירי לי בפשטות מה השאלה מבקשת ואיך ניגשים אליה. אחר כך תני צעד ראשון אחד בלבד. אחרי כל תשובה שלי, הסבירי מה מצאתי, למה זה עוזר לשאלה, מה עדיין חסר, ואז שאלי שאלה קצרה אחת על הצעד הבא. אל תדלגי על ההסבר. כשכבר יש לי מספיק מידע, תבקשי ממני לנסח את התשובה בעצמי.'
if old_initial not in backend:
    raise SystemExit('Initial coach prompt not found')
backend = backend.replace(old_initial, new_initial, 1)

old_fallback = 'text = (text + "\\n\\nמה עוד בטקסט עוזר לנו לענות על השאלה?").strip()'
new_fallback = 'text = (text + "\\n\\nעכשיו נמשיך לצעד הבא: חפש/י בטקסט את הפעולה הבאה שעוזרת לענות על השאלה. מה מצאת?").strip()'
if old_fallback in backend:
    backend = backend.replace(old_fallback, new_fallback, 1)

loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.94";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0794', loader, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0794', index)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.94', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.94";', index, count=1)

backend_path.write_text(backend, encoding='utf-8')
loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
print('Homework coach now explains before asking; build 0.7.94')
