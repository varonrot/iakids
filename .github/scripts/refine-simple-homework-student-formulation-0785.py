from pathlib import Path

BACKEND = Path('backend-ai-tutor-he/main.py')
INDEX = Path('he/workspace/index.html')

backend = BACKEND.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old = (
    '        "כאשר הילד כבר אסף את עיקרי התשובה, אמרי שיש מספיק, חברי יחד את מה שהוא מצא לניסוח קצר וברור, וסיימי את השאלה. "\n'
)
new = (
    '        "כאשר הילד כבר אסף מספיק מידע כדי לענות, אל תנסחי את התשובה במקומו. אמרי שיש לו מספיק מידע ובקשי ממנו לנסח בעצמו תשובה מלאה לשאלה. "\n'
    '        "רק אחרי שהילד ניסח תשובה בעצמו, בדקי אם היא מספיקה. אם היא נכונה, אשרי בקצרה; אם צריך, עזרי רק לשפר את הניסוח בלי להחליף את תשובתו. "\n'
)

if old not in backend:
    if 'אל תנסחי את התשובה במקומו' not in backend:
        raise SystemExit('target simple-test prompt sentence not found')
else:
    backend = backend.replace(old, new, 1)

# Keep the opening request focused on teaching, not answer ownership.
old_open = 'אחר כך תתחילי איתי בצעד הראשון. בכל המשך תשמרי את מה שכבר מצאתי ותשאלי רק על מה שחסר.'
new_open = 'אחר כך תתחילי איתי בצעד הראשון. בכל המשך תשמרי את מה שכבר מצאתי ותשאלי רק על מה שחסר. כשכבר יש לי מספיק מידע, תבקשי ממני לנסח את התשובה בעצמי.'
if old_open in backend:
    backend = backend.replace(old_open, new_open, 1)

for old_version in ('0.7.82','0.7.83','0.7.84'):
    index = index.replace(f'IAKIDS • build {old_version}', 'IAKIDS • build 0.7.85')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{old_version}";', 'window.IAKIDS_BUILD_VERSION = "0.7.85";')

BACKEND.write_text(backend, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Refined simple-test answer ownership; build 0.7.85')
