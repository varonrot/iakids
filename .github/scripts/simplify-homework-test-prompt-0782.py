from pathlib import Path

BACKEND = Path('backend-ai-tutor-he/main.py')
INDEX = Path('he/workspace/index.html')

backend = BACKEND.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old_prompt = '''    system_prompt = (\n        "את מורה פרטית מצוינת לילדים. המטרה שלך היא ללמד את הילד איך להגיע לתשובה בעצמו. "\n        "לפני שאת שואלת משהו, הסבירי בקצרה מה השאלה מבקשת ואיך ניגשים אליה. "\n        "אחר כך עבדי שלב אחרי שלב. בכל הודעה תני רק צעד אחד ברור, הסבירי מה עושים בצעד הזה, "\n        "ואז שאלי שאלה קצרה אחת וחכי לתשובת הילד. "\n        "אל תחזרי על השאלה בלי הסבר, ואל תתני את התשובה המלאה לפני שהילד ניסה. "\n        "אם תשובת הילד כבר מספיקה, אמרי שהיא נכונה, נסחי תשובה סופית קצרה, וסיימי את השאלה."\n    )\n'''

new_prompt = '''    system_prompt = (\n        "את מורה פרטית לילדים. קראי את השאלה ואת חומר המקור. "\n        "הביני בעצמך מה הילד צריך ללמוד כדי לענות. "\n        "למדי אותו איך לפתור את השאלה בצורה ברורה וטבעית, שלב אחרי שלב, בלי לתת מיד את התשובה. "\n        "התאימי את ההסבר לגיל ולכיתה."\n    )\n'''

if old_prompt not in backend:
    raise SystemExit('simple test prompt block not found')
backend = backend.replace(old_prompt, new_prompt, 1)

old_opening = 'messages.append({"role":"user","content":"תסבירי לי קודם מה השאלה מבקשת ואיך ניגשים אליה, ואז תלמדי אותי לפתור אותה שלב אחרי שלב. תתחילי רק בצעד הראשון."})'
new_opening = 'messages.append({"role":"user","content":"תלמדי אותי איך לענות על השאלה הזאת. קודם תסבירי לי מה מחפשים ואיפה לחפש בטקסט, ואז תתחילי איתי בצעד הראשון בלבד."})'
if old_opening not in backend:
    raise SystemExit('simple test opening message not found')
backend = backend.replace(old_opening, new_opening, 1)

for oldv in ('0.7.80','0.7.81'):
    index = index.replace(f'IAKIDS • build {oldv}', 'IAKIDS • build 0.7.82')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{oldv}";', 'window.IAKIDS_BUILD_VERSION = "0.7.82";')

BACKEND.write_text(backend, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Simplified homework simple-test prompt; build 0.7.82')
