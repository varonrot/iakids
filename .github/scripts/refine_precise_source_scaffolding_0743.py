from pathlib import Path
import re

ROOT = Path('.')
backend = ROOT / 'backend-ai-tutor-he' / 'main.py'
core = ROOT / 'he' / 'workspace' / 'lesson-completion-core.js'
loader = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index = ROOT / 'he' / 'workspace' / 'index.html'

# ---------- backend ----------
b = backend.read_text(encoding='utf-8')

old_reading = '"reading_source": "Use the provided source as the primary truth. Guide the child back to the exact relevant sentence/part, identify evidence or key words, then help turn that evidence into an answer. Never invent facts outside the source."'
new_reading = '"reading_source": "Use the provided source as the primary truth. Give a PRECISE source cue: identify the relevant sentence, paragraph, event, data region, label, or instruction and tell the child what specific feature to look for there (for example: action, cause, result, key word, comparison, value, or evidence). Avoid vague prompts such as asking what they see in the text or what the text says in general. Then ask ONE small focused question answerable from that exact source location. Never invent facts outside the source."'
if old_reading not in b:
    raise RuntimeError('backend reading_source strategy anchor not found')
b = b.replace(old_reading, new_reading, 1)

# Add a hard rule against vague source prompts, if not already present.
needle = '9. Never ask a guiding question whose answer is unsupported by the provided source when the task is source-based.\n'
insert = (
    '9. Never ask a guiding question whose answer is unsupported by the provided source when the task is source-based.\n'
    '10. For source-based tasks, guidance must be concrete rather than vague: point to the relevant part of the source and name what to search for there. Do not use generic prompts equivalent to "what do you see in the text?" or "what does the passage say about it?" when a more precise cue can be given from the source.\n'
)
if needle in b and 'For source-based tasks, guidance must be concrete rather than vague' not in b:
    b = b.replace(needle, insert, 1)
    # Renumber following structural rules if present.
    b = b.replace('10. Do not drift into personal life, values, feelings, rewards, motives, examples, or general discussion unless explicitly required by the worksheet question.\n11. Do not mention the next worksheet question; application code controls progression.\n12. Return only the structured response.',
                  '11. Do not drift into personal life, values, feelings, rewards, motives, examples, or general discussion unless explicitly required by the worksheet question.\n12. Do not mention the next worksheet question; application code controls progression.\n13. Return only the structured response.', 1)

backend.write_text(b, encoding='utf-8')

# ---------- frontend ----------
c = core.read_text(encoding='utf-8')

old_strategy = 'return {id:"reading_source", instruction:"המקור הוא הטקסט. הפנה למקום הרלוונטי, אתר ראיות/מילות מפתח, ורק מהן בנה את התשובה. אל תמציא מידע שאינו במקור."};'
new_strategy = 'return {id:"reading_source", instruction:"המקור הוא הטקסט. תן הכוונה מדויקת למקום הרלוונטי במקור — משפט, פסקה, אירוע או חלק מסוים — וציין מה בדיוק לחפש שם: פעולה, סיבה, תוצאה, מילת מפתח, השוואה או ראיה. אל תשאל שאלות כלליות כמו מה רואים בטקסט או מה כתוב על כך כאשר אפשר לכוון בצורה מדויקת יותר. לאחר מכן שאל שאלה אחת קצרה שניתנת למענה מתוך אותו חלק בלבד. אל תמציא מידע שאינו במקור."};'
if old_strategy not in c:
    raise RuntimeError('frontend reading_source strategy anchor not found')
c = c.replace(old_strategy, new_strategy, 1)

# Strengthen understand_question without any task-specific example.
pattern = re.compile(r'case "understand_question":\s*\n\s*return "[^"]*";', re.S)
match = pattern.search(c)
if not match:
    raise RuntimeError('frontend understand_question anchor not found')
replacement = '''case "understand_question":\n        return "התמקד רק בשאלה הראשונה שעדיין לא נענתה. הסבר בקצרה מה היא מבקשת. אם יש מקור, אל תסתפק בהפניה כללית אליו: כוון לחלק המדויק ביותר שאפשר לזהות מתוך המקור וציין מה בדיוק צריך לחפש שם, כגון פעולה, סיבה, תוצאה, מילת מפתח, נתון, השוואה או ראיה. לאחר מכן שאל שאלה מכוונת אחת בלבד, קצרה ומבוססת על אותו חלק. הימנע משאלות כלליות כמו 'מה את רואה בקטע?' או 'מה כתוב על כך?' כאשר אפשר לתת הכוונה מדויקת יותר. אין להמציא מידע, אין לחזור על אותה שאלה בניסוחים שונים, ואין לתת את התשובה המלאה לפני ניסיון אמיתי של הילד/ה.";'''
c = c[:match.start()] + replacement + c[match.end():]

core.write_text(c, encoding='utf-8')

# ---------- version bump ----------
l = loader.read_text(encoding='utf-8')
l = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.43";', l, count=1)
l = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0743', l, count=1)
loader.write_text(l, encoding='utf-8')

i = index.read_text(encoding='utf-8')
i = re.sub(r'IAKIDS • build 0\.7\.\d+', 'IAKIDS • build 0.7.43', i)
i = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0743', i)
index.write_text(i, encoding='utf-8')

print('Applied precise source scaffolding 0.7.43')
