from pathlib import Path
import re

root = Path('.')
core_path = root / 'he/workspace/lesson-completion-core.js'
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'
backend_path = root / 'backend-ai-tutor-he/main.py'

core = core_path.read_text(encoding='utf-8')
loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')
backend = backend_path.read_text(encoding='utf-8')

# Backend: force the model to declare whether the current question is complete.
needle = '        "התאימי את השפה לגיל ולכיתה."\n    )\n'
replacement = '''        "התאימי את השפה לגיל ולכיתה. "\n        "כל תגובה חייבת להתחיל בסמן פנימי אחד בלבד: [[CONTINUE]] אם עדיין חסר מידע או אם הילד עדיין לא ניסח תשובה מלאה בעצמו; [[COMPLETE]] רק אם הילד עצמו כבר ניסח תשובה מלאה ומספקת לשאלה הפעילה. "\n        "תשובת ביניים נכונה כמו פרט אחד מהטקסט לעולם אינה COMPLETE. "\n        "במצב CONTINUE חובה אחרי אישור קצר לשאול שאלה אחת בלבד שמקדמת ישירות לפרט הבא שחסר בשאלה הפעילה. אסור לסיים תגובת CONTINUE רק במחמאה או באישור. "\n        "במצב COMPLETE אשרי בקצרה בלבד ואל תשאלי שאלה נוספת."\n    )\n'''
if needle not in backend:
    raise SystemExit('homework coach prompt tail not found')
backend = backend.replace(needle, replacement, 1)

old_tail = '''    text = str(response.choices[0].message.content or "").strip()\n    return {"reply": text, "model": "gpt-5.6-sol", "production_mode": True}\n'''
new_tail = '''    raw_text = str(response.choices[0].message.content or "").strip()\n    state = "complete" if raw_text.startswith("[[COMPLETE]]") else "continue"\n    text = re.sub(r"^\\s*\\[\\[(?:CONTINUE|COMPLETE)\\]\\]\\s*", "", raw_text, count=1).strip()\n    if state == "continue" and "?" not in text:\n        text = (text + "\\n\\nמה עוד בטקסט עוזר לנו לענות על השאלה?").strip()\n    return {"reply": text, "state": state, "model": "gpt-5.6-sol", "production_mode": True}\n'''
if old_tail not in backend:
    raise SystemExit('homework coach response tail not found')
backend = backend.replace(old_tail, new_tail, 1)

# Frontend: stop guessing completion from Hebrew wording. Trust the explicit backend state only.
old_final = '''    const normalizedReply = reply\n      .replace(/\\*\\*/g, "")\n      .replace(/\\s+/g, " ")\n      .trim();\n\n    const finalAnswerAccepted = Boolean(String(messageText || "").trim()) && (\n      /התשובה\\s+נכונה/.test(normalizedReply) ||\n      /נכונה[, ]+מלאה/.test(normalizedReply) ||\n      /מנוסחת\\s+היטב/.test(normalizedReply) ||\n      /ענית\\s+תשובה\\s+מלאה/.test(normalizedReply)\n    );\n'''
new_final = '''    const finalAnswerAccepted =\n      Boolean(String(messageText || "").trim())\n      && String(data?.state || "").toLowerCase() === "complete";\n'''
if old_final not in core:
    raise SystemExit('frontend final-answer heuristic block not found')
core = core.replace(old_final, new_final, 1)

# Version/cache bump.
loader = re.sub(r'window\\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\\.7\\.\\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.92";', loader, count=1)
loader = re.sub(r'lesson-completion-core\\.js\\?v=\\d+', 'lesson-completion-core.js?v=0792', loader, count=1)
index = re.sub(r'lesson-completion\\.js\\?v=\\d+', 'lesson-completion.js?v=0792', index)
index = re.sub(r'IAKIDS\\s*•\\s*build\\s*0\\.7\\.\\d+', 'IAKIDS • build 0.7.92', index)
index = re.sub(r'window\\.IAKIDS_BUILD_VERSION\\s*=\\s*"0\\.7\\.\\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.92";', index, count=1)

core_path.write_text(core, encoding='utf-8')
loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
backend_path.write_text(backend, encoding='utf-8')

print('Added explicit homework coach CONTINUE/COMPLETE state; build 0.7.92')
