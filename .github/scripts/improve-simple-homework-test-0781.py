from pathlib import Path

BACKEND = Path('backend-ai-tutor-he/main.py')
INDEX = Path('he/workspace/index.html')

backend = BACKEND.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old = '''    system_prompt = (\n        "את מורה פרטית לילדים. עזרי לילד להבין ולפתור את שיעורי הבית בעצמו. "\n        "למדי אותו שלב אחרי שלב, בשפה פשוטה שמתאימה לכיתה שלו. "\n        "בכל פעם הסבירי צעד אחד בלבד, שאלי שאלה קצרה אחת, ואז חכי לתשובה. "\n        "אל תתני את התשובה המלאה לפני שהילד ניסה."\n    )\n'''

new = '''    system_prompt = (\n        "את מורה פרטית מצוינת לילדים. המטרה שלך היא ללמד את הילד איך להגיע לתשובה בעצמו. "\n        "לפני שאת שואלת משהו, הסבירי בקצרה מה השאלה מבקשת ואיך ניגשים אליה. "\n        "אחר כך עבדי שלב אחרי שלב. בכל הודעה תני רק צעד אחד ברור, הסבירי מה עושים בצעד הזה, "\n        "ואז שאלי שאלה קצרה אחת וחכי לתשובת הילד. "\n        "אל תחזרי על השאלה בלי הסבר, ואל תתני את התשובה המלאה לפני שהילד ניסה. "\n        "אם תשובת הילד כבר מספיקה, אמרי שהיא נכונה, נסחי תשובה סופית קצרה, וסיימי את השאלה."\n    )\n'''

if old not in backend:
    raise SystemExit('simple-test prompt block not found')
backend = backend.replace(old, new, 1)

# Make the very first user instruction equally explicit but still simple.
backend = backend.replace(
    'messages.append({"role":"user","content":"תתחילי ללמד אותי את השאלה הזאת שלב אחרי שלב."})',
    'messages.append({"role":"user","content":"תסבירי לי קודם מה השאלה מבקשת ואיך ניגשים אליה, ואז תלמדי אותי לפתור אותה שלב אחרי שלב. תתחילי רק בצעד הראשון."})',
    1
)

for oldv in ('0.7.79','0.7.80'):
    index = index.replace(f'IAKIDS • build {oldv}', 'IAKIDS • build 0.7.81')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{oldv}";', 'window.IAKIDS_BUILD_VERSION = "0.7.81";')

BACKEND.write_text(backend, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Improved simple homework test prompt; build 0.7.81')
