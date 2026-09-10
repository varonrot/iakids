from pathlib import Path

BACKEND = Path('backend-ai-tutor-he/main.py')
INDEX = Path('he/workspace/index.html')

backend = BACKEND.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old = '''    system_prompt = (\n        "את מורה פרטית לילדים. קראי את השאלה ואת חומר המקור. "\n        "הביני בעצמך מה הילד צריך ללמוד כדי לענות. "\n        "למדי אותו איך לפתור את השאלה בצורה ברורה וטבעית, שלב אחרי שלב, בלי לתת מיד את התשובה. "\n        "התאימי את ההסבר לגיל ולכיתה."\n    )\n'''

new = '''    system_prompt = (\n        "את מורה פרטית מצוינת לילדים. המטרה שלך היא ללמד את הילד איך להגיע לתשובה בעצמו. "\n        "קראי את השאלה ואת חומר המקור, הביני מה צריך למצוא, ולמדי את הילד בצורה טבעית שלב אחרי שלב. "\n        "שמרי כל דבר נכון שהילד כבר מצא ואל תחזרי אחורה. בכל תשובה הסבירי בקצרה מה כבר מצאנו ומה עדיין חסר. "\n        "אחר כך שאלי רק על החלק הבא שחסר. אל תתני מיד את התשובה המלאה. "\n        "כאשר הילד כבר אסף את עיקרי התשובה, אמרי שיש מספיק, חברי יחד את מה שהוא מצא לניסוח קצר וברור, וסיימי את השאלה. "\n        "התאימי את השפה לגיל ולכיתה."\n    )\n'''

if old not in backend:
    raise SystemExit('simple test prompt block not found')
backend = backend.replace(old, new, 1)

old_start = 'messages.append({"role":"user","content":"תלמדי אותי איך לענות על השאלה הזאת. קודם תסבירי לי מה מחפשים ואיפה לחפש בטקסט, ואז תתחילי איתי בצעד הראשון בלבד."})'
new_start = 'messages.append({"role":"user","content":"תלמדי אותי לענות על השאלה הזאת כמו מורה פרטית. קודם תסבירי בקצרה מה אנחנו מחפשים ואיפה כדאי לחפש בטקסט. אחר כך תתחילי איתי בצעד הראשון. בכל המשך תשמרי את מה שכבר מצאתי ותשאלי רק על מה שחסר."})'
if old_start not in backend:
    raise SystemExit('simple test initial message not found')
backend = backend.replace(old_start, new_start, 1)

for oldv in ('0.7.82','0.7.83'):
    index = index.replace(f'IAKIDS • build {oldv}', 'IAKIDS • build 0.7.84')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{oldv}";', 'window.IAKIDS_BUILD_VERSION = "0.7.84";')

BACKEND.write_text(backend, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Refined simple homework test teaching flow; build 0.7.84')
