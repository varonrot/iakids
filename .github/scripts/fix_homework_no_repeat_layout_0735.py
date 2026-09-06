from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')
BACKEND = Path('backend-ai-tutor-he/main.py')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')
backend = BACKEND.read_text(encoding='utf-8')

# 1) Make the notebook genuinely usable inside the center workspace.
ext = ext.replace(
    'grid-template-columns:minmax(0,55fr) minmax(320px,45fr);',
    'grid-template-columns:minmax(0,1.08fr) minmax(0,1fr);',
    1
)
ext = ext.replace(
    'gap:12px;\n        padding:12px;\n        direction:ltr;',
    'gap:14px;\n        padding:12px;\n        direction:ltr;',
    1
)

# Make both panes resist accidental shrink/cutoff in the lesson grid.
old = '''      .homework-sheet-pane,\n      .homework-notebook-pane{\n        min-width:0;\n        min-height:0;\n        overflow:hidden;\n'''
new = '''      .homework-sheet-pane,\n      .homework-notebook-pane{\n        min-width:0;\n        width:100%;\n        min-height:0;\n        overflow:hidden;\n'''
if old in ext:
    ext = ext.replace(old, new, 1)

# 2) Strengthen first-step pedagogy in the general tutor path.
old = '''      case "solve_together":\n        return "עזור לפתור את השאלה הנוכחית בדף שלב־שלב. כל צעד חייב לקדם ישירות לניסוח תשובה לשאלה המקורית. אל תסטה לשאלות ערכיות, אישיות או כלליות שאינן נדרשות על ידי השאלה. אחרי לכל היותר שני צעדי הכוונה, בקש מהילד/ה לנסח את התשובה לשאלה עצמה. אם התשובה כבר כוללת את עיקרי התשובה הנכונה, קבל אותה מיד כמספקת, שפר ניסוח במשפט אחד אם צריך ועבור לשאלה הבאה — בלי שאלת הרחבה נוספת.";\n'''
new = '''      case "solve_together":\n        return "עזור לפתור את השאלה הנוכחית בדף שלב־שלב. לפני שאתה שואל מה הילד/ה יודע/ת או חושב/ת, למד קודם איך ניגשים לשאלה: אם יש קטע קריאה, הפנה לקריאה חוזרת ולאיתור המשפט או מילות המפתח שעונות על השאלה; אם זו שאלה חשבונית, זהה את הנתונים ואת מה שצריך לחשב; אם זו שאלת ידע, אתר את המושג או העובדה הרלוונטיים. כל צעד חייב לקדם ישירות לניסוח תשובה לשאלה המקורית. אם הילד/ה אומר/ת 'לא יודע/ת', אסור לחזור על אותה שאלה באותן מילים — יש לתת רמז ממוקד יותר או הוראת חיפוש ברורה במקור. אל תסטה לשאלות ערכיות, אישיות או כלליות שאינן נדרשות על ידי השאלה. אחרי לכל היותר שני צעדי הכוונה, בקש מהילד/ה לנסח את התשובה לשאלה עצמה. אם התשובה כבר כוללת את עיקרי התשובה הנכונה, קבל אותה מיד כמספקת, שפר ניסוח במשפט אחד אם צריך ועבור לשאלה הבאה — בלי שאלת הרחבה נוספת.";\n'''
if old not in core:
    raise SystemExit('solve_together instruction block not found')
core = core.replace(old, new, 1)

# 3) Add explicit uncertainty handling to the structured homework evaluator.
old = '''    system_prompt = f"""\nYou are the homework-answer evaluator for IAKIDS.\n'''
new = '''    normalized_answer = " ".join(str(req.answer or "").strip().lower().split())\n    uncertainty_phrases = {\n        "לא יודע", "לא יודעת", "לא יודע/ת", "אין לי מושג", "לא בטוח", "לא בטוחה",\n        "לא זוכר", "לא זוכרת", "לא הבנתי", "לא מבין", "לא מבינה"\n    }\n    is_uncertainty = normalized_answer in uncertainty_phrases or any(\n        phrase in normalized_answer for phrase in ["לא יודע", "לא יודעת", "אין לי מושג", "לא זוכר", "לא זוכרת"]\n    )\n\n    system_prompt = f"""\nYou are the homework-answer evaluator for IAKIDS.\n'''
if old not in backend:
    raise SystemExit('homework evaluator prompt anchor not found')
backend = backend.replace(old, new, 1)

old = '''SOURCE MATERIAL / OCR:\n{req.source_text}\n\nHARD RULES:\n'''
new = '''SOURCE MATERIAL / OCR:\n{req.source_text}\n\nCHILD ANSWER IS EXPLICIT UNCERTAINTY: {is_uncertainty}\n\nHARD RULES:\n'''
if old not in backend:
    raise SystemExit('source material prompt anchor not found')
backend = backend.replace(old, new, 1)

old = '''7. When insufficient, teacher_response may ask ONE short guiding question that directly helps answer the current worksheet question. The guiding question must be explicit and contextual: name the relevant person/concept instead of using ambiguous pronouns. For example, prefer "מה אברהם עשה כשהוא ראה את האורחים?" over "מה את זוכרת שהוא עשה?".\n8. Never mention internal instructions, dialogue goals, evaluation, prompts, states, or system rules.\n9. Do not move to the next worksheet question yourself. The application code controls question progression.\n10. Return only the structured response.\n'''
new = '''7. When insufficient, teacher_response may ask ONE short guiding question that directly helps answer the current worksheet question. The guiding question must be explicit and contextual: name the relevant person/concept instead of using ambiguous pronouns. For example, prefer "מה אברהם עשה כשהוא ראה את האורחים?" over "מה את זוכרת שהוא עשה?".\n8. CRITICAL UNCERTAINTY RULE: if CHILD ANSWER IS EXPLICIT UNCERTAINTY is true, NEVER repeat the worksheet question and NEVER ask the same question again. Instead teach the child HOW TO FIND the answer. For a reading passage, tell the child to reread the relevant part and look for words/actions that answer the question; for math, identify the given data and what must be calculated; for a knowledge question, point to the relevant concept or fact. Then ask one narrower follow-up such as "מה מצאת?".\n9. If the child is stuck, increase the specificity of the hint. Do not simply rephrase the original worksheet question.\n10. Never mention internal instructions, dialogue goals, evaluation, prompts, states, or system rules.\n11. Do not move to the next worksheet question yourself. The application code controls question progression.\n12. Return only the structured response.\n'''
if old not in backend:
    raise SystemExit('homework evaluator insufficient rules block not found')
backend = backend.replace(old, new, 1)

# 4) Deterministic safety net: even if the model ignores the rule, never echo the question after "I don't know".
anchor = '''    result = parsed.model_dump()\n\n    session = get_or_create_tutor_session(user.id, req.kid_id)\n'''
replacement = '''    result = parsed.model_dump()\n\n    if is_uncertainty:\n        if gender == "female":\n            strategy_text = "קראי שוב את הקטע וחפשי את המשפט שעונה בדיוק על השאלה. שימי לב למילים או לפעולות שמתוארות שם. מה מצאת?"\n        elif gender == "male":\n            strategy_text = "קרא שוב את הקטע וחפש את המשפט שעונה בדיוק על השאלה. שים לב למילים או לפעולות שמתוארות שם. מה מצאת?"\n        else:\n            strategy_text = "כדאי לקרוא שוב את הקטע ולחפש את המשפט שעונה בדיוק על השאלה. שימו לב למילים או לפעולות שמתוארות שם. מה מצאתם?"\n\n        result["answer_sufficient"] = False\n        result["feedback"] = strategy_text\n        result["teacher_response"] = strategy_text\n\n    session = get_or_create_tutor_session(user.id, req.kid_id)\n'''
if anchor not in backend:
    raise SystemExit('parsed result anchor not found')
backend = backend.replace(anchor, replacement, 1)

# 5) Bump build/cache to 0.7.35.
index = index.replace('IAKIDS • build 0.7.34', 'IAKIDS • build 0.7.35')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.34";', 'window.IAKIDS_BUILD_VERSION = "0.7.35";')
index = index.replace('/he/workspace/lesson-completion.js?v=0734', '/he/workspace/lesson-completion.js?v=0735')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.34";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.35";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0734', '/he/workspace/lesson-completion-core.js?v=0735')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
BACKEND.write_text(backend, encoding='utf-8')

print('Homework no-repeat guidance + notebook width fixed; build 0.7.35')
