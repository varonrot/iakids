from pathlib import Path
import re

root = Path('.')
backend_path = root / 'backend-ai-tutor-he/main.py'
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'

backend = backend_path.read_text(encoding='utf-8')
loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

old = '''    context = (\n        f"כיתה: {grade or 'לא ידוע'}\\n"\n        f"השאלה שעליה עובדים עכשיו: {req.current_question}\\n"\n        f"דף העבודה / חומר המקור:\\n{req.source_text}"\n    )\n\n    worksheet_content = [{"type": "text", "text": context}]\n'''
new = '''    # V2 deliberately mirrors a clean ChatGPT conversation:\n    # short tutor prompt + original worksheet image + clean per-session history.\n    # Do NOT inject OCR, extracted question state, legacy strategies or guards here.\n    worksheet_content = [{\n        "type": "text",\n        "text": (\n            f"כיתה: {grade or 'לא ידוע'}\\n"\n            "זה דף העבודה של הילד. למדי אותו לפתור את שיעורי הבית בעצמו לפי ההוראות שלך. "\n            "התחילי מהמשימה הראשונה שעדיין לא נפתרה בתמונה, והתקדמי איתו באופן טבעי שלב אחרי שלב."\n        )\n    }]\n'''
if old not in backend:
    raise SystemExit('V2 context block not found')
backend = backend.replace(old, new, 1)

loader = re.sub(r'window\\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\\.7\\.\\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.99";', loader, count=1)
loader = re.sub(r'lesson-completion-core\\.js\\?v=\\d+', 'lesson-completion-core.js?v=0799', loader, count=1)
index = re.sub(r'lesson-completion\\.js\\?v=\\d+', 'lesson-completion.js?v=0799', index)
index = re.sub(r'IAKIDS\\s*•\\s*build\\s*0\\.7\\.\\d+', 'IAKIDS • build 0.7.99', index)
index = re.sub(r'window\\.IAKIDS_BUILD_VERSION\\s*=\\s*"0\\.7\\.\\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.99";', index, count=1)

backend_path.write_text(backend, encoding='utf-8')
loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
print('Homework V2 now mirrors clean image-chat behavior; build 0.7.99')
