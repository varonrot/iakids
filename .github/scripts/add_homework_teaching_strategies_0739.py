from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')
BACKEND = Path('backend-ai-tutor-he/main.py')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')
backend = BACKEND.read_text(encoding='utf-8')

# -----------------------------------------------------
# Backend: compact teaching strategies + deterministic resolver.
# -----------------------------------------------------
if 'HOMEWORK_TEACHING_STRATEGIES = {' not in backend:
    anchor = '""".strip()\n\nclass HomeworkTurnRequest(BaseModel):'
    if anchor not in backend:
        raise SystemExit('backend strategy insertion anchor not found')

    block = '''""".strip()\n\nHOMEWORK_TEACHING_STRATEGIES = {\n    "reading_source": "Use the provided source as the primary truth. Guide the child back to the exact relevant sentence/part, identify evidence or key words, then help turn that evidence into an answer. Never invent facts outside the source.",\n    "math_problem": "Identify givens, identify what is being asked, choose the required mathematical relation/operation, solve one step at a time, then formulate the contextual answer. Do not reveal the final result before a genuine attempt.",\n    "science_reasoning": "Identify the relevant scientific concept, observation, diagram, experiment, or evidence. Connect it explicitly to what the question asks, then help formulate the explanation.",\n    "writing_composition": "Clarify the required content and format, break the task into 2-4 components, build a short outline or sentence frame, and only then ask the child to write. Do not ask vague wording questions before giving structure.",\n    "language_skill": "Identify the target language skill (vocabulary, grammar, sentence construction, translation, reading). Teach the rule/pattern with one focused cue, then ask for a short application.",\n    "data_visual": "Treat the table/chart/diagram/data as the source of truth. First identify what needs to be read or compared, then locate the relevant values/features, then formulate the answer.",\n    "knowledge_direct": "Teach only the minimum concept needed for the current question, check one key understanding point, then ask the child to answer in their own words.",\n    "general": "Apply the global sequence: understand the task, identify the source/method, isolate key points, provide structure, child attempts, specific feedback, final wording."\n}\n\ndef resolve_homework_teaching_strategy(question: str, source_text: str) -> tuple[str, str]:\n    q = str(question or "").strip().lower()\n    s = str(source_text or "").strip().lower()\n    combined = f"{q}\\n{s}"\n\n    if any(token in combined for token in [\n        "קטע קריאה", "לפי הקטע", "על פי הקטע", "בסיפור", "בטקסט",\n        "מה אפשר ללמוד", "מה ניתן ללמוד", "מסר", "מסקנה", "תנ״ך", "פרשה"\n    ]):\n        return "reading_source", HOMEWORK_TEACHING_STRATEGIES["reading_source"]\n\n    if any(token in combined for token in [\n        "חשב", "חשבו", "כמה", "סכום", "הפרש", "כפל", "חילוק", "שבר",\n        "אחוז", "משוואה", "היקף", "שטח", "זווית"\n    ]):\n        return "math_problem", HOMEWORK_TEACHING_STRATEGIES["math_problem"]\n\n    if any(token in combined for token in [\n        "גרף", "טבלה", "תרשים", "דיאגרמה", "נתונים", "ציר"\n    ]):\n        return "data_visual", HOMEWORK_TEACHING_STRATEGIES["data_visual"]\n\n    if any(token in combined for token in [\n        "כתבו", "כתבי", "חיבור", "פסקה", "תארו", "תארי", "נמקו", "נמקי",\n        "writing", "composition"\n    ]):\n        return "writing_composition", HOMEWORK_TEACHING_STRATEGIES["writing_composition"]\n\n    if any(token in combined for token in [\n        "מדעים", "science", "ניסוי", "תהליך", "מערכת", "אנרגיה", "כוח",\n        "חומר", "סביבה", "אקולוג"\n    ]):\n        return "science_reasoning", HOMEWORK_TEACHING_STRATEGIES["science_reasoning"]\n\n    if any(token in combined for token in [\n        "grammar", "vocabulary", "דקדוק", "אוצר מילים", "תרגמו", "תרגמי",\n        "english", "אנגלית"\n    ]):\n        return "language_skill", HOMEWORK_TEACHING_STRATEGIES["language_skill"]\n\n    return "general", HOMEWORK_TEACHING_STRATEGIES["general"]\n\nclass HomeworkTurnRequest(BaseModel):'''
    backend = backend.replace(anchor, block, 1)

# Add resolved strategy to the evaluator prompt.
old = '''    system_prompt = f"""\nYou are the homework-answer evaluator for IAKIDS.\n'''
new = '''    strategy_name, strategy_instruction = resolve_homework_teaching_strategy(\n        req.current_question,\n        req.source_text\n    )\n\n    system_prompt = f"""\nYou are the homework-answer evaluator for IAKIDS.\n'''
if old in backend and 'strategy_name, strategy_instruction = resolve_homework_teaching_strategy' not in backend:
    backend = backend.replace(old, new, 1)

old = '''{HOMEWORK_GLOBAL_PEDAGOGY_PROMPT}\n\nHARD RULES:\n'''
new = '''{HOMEWORK_GLOBAL_PEDAGOGY_PROMPT}\n\nACTIVE TEACHING STRATEGY: {strategy_name}\nSTRATEGY INSTRUCTION:\n{strategy_instruction}\n\nHARD RULES:\n'''
if old in backend and 'ACTIVE TEACHING STRATEGY:' not in backend:
    backend = backend.replace(old, new, 1)

# -----------------------------------------------------
# Frontend: same compact strategy selection for the initial help-choice call.
# This is intentionally short; global pedagogy remains one shared contract.
# -----------------------------------------------------
if 'function resolveHomeworkTeachingStrategy' not in core:
    anchor = '  function getChoiceInstruction(choiceId){\n'
    if anchor not in core:
        raise SystemExit('frontend strategy insertion anchor not found')
    js = r'''  function resolveHomeworkTeachingStrategy(analysis, question){
    const q = String(question || "").toLowerCase();
    const source = String(analysis?.extracted_text || "").toLowerCase();
    const combined = `${q}\n${source}`;

    if(/קטע קריאה|לפי הקטע|על פי הקטע|בסיפור|בטקסט|מה אפשר ללמוד|מה ניתן ללמוד|מסר|מסקנה|תנ[״"]?ך|פרשה/.test(combined)){
      return {id:"reading_source", instruction:"המקור הוא הטקסט. הפנה למקום הרלוונטי, אתר ראיות/מילות מפתח, ורק מהן בנה את התשובה. אל תמציא מידע שאינו במקור."};
    }
    if(/חשב|חשבו|כמה|סכום|הפרש|כפל|חילוק|שבר|אחוז|משוואה|היקף|שטח|זווית/.test(combined)){
      return {id:"math_problem", instruction:"זהה נתונים, מה מבקשים, פעולה או קשר מתמטי, פתרון בשלבים, ורק בסוף ניסוח התשובה."};
    }
    if(/גרף|טבלה|תרשים|דיאגרמה|נתונים|ציר/.test(combined)){
      return {id:"data_visual", instruction:"הטבלה/תרשים/נתונים הם מקור האמת. אתר קודם את הערכים או המאפיינים הרלוונטיים ואז נסח תשובה."};
    }
    if(/כתבו|כתבי|חיבור|פסקה|תארו|תארי|נמקו|נמקי|writing|composition/.test(combined)){
      return {id:"writing_composition", instruction:"הבהר מה נדרש, פרק לרכיבים, בנה שלד או פתיח, ורק אז בקש מהילד/ה לכתוב."};
    }
    if(/מדעים|science|ניסוי|תהליך|מערכת|אנרגיה|כוח|חומר|סביבה|אקולוג/.test(combined)){
      return {id:"science_reasoning", instruction:"זהה מושג/ראיה/תהליך רלוונטיים, קשר אותם ישירות לשאלה, ואז בנה הסבר."};
    }
    if(/grammar|vocabulary|דקדוק|אוצר מילים|תרגמו|תרגמי|english|אנגלית/.test(combined)){
      return {id:"language_skill", instruction:"זהה מיומנות שפה, למד כלל או תבנית אחת ממוקדת, ואז בקש יישום קצר."};
    }
    return {id:"general", instruction:"פעל לפי הרצף הגלובלי: להבין משימה, למצוא מקור/שיטה, לבודד נקודות, לתת מבנה, ניסיון הילד, משוב, ניסוח סופי."};
  }

'''
    core = core.replace(anchor, js + anchor, 1)

# Inject strategy in runHomeworkChoiceWithTutor message.
old = '''    const currentQuestion = extractFirstHomeworkQuestion(analysis.extracted_text) || "לא זוהתה שאלה";\n\n    const message = `\n'''
new = '''    const currentQuestion = extractFirstHomeworkQuestion(analysis.extracted_text) || "לא זוהתה שאלה";\n    const teachingStrategy = resolveHomeworkTeachingStrategy(analysis, currentQuestion);\n\n    const message = `\n'''
if old in core and 'const teachingStrategy = resolveHomeworkTeachingStrategy' not in core:
    core = core.replace(old, new, 1)

old = '''הילד בחר: ${choice.label}\n\n${HOMEWORK_GLOBAL_PEDAGOGY_RULES}\n'''
new = '''הילד בחר: ${choice.label}\n\nאסטרטגיית הוראה פעילה: ${teachingStrategy.id}\n${teachingStrategy.instruction}\n\n${HOMEWORK_GLOBAL_PEDAGOGY_RULES}\n'''
if old in core and 'אסטרטגיית הוראה פעילה:' not in core:
    core = core.replace(old, new, 1)

# Bump frontend build/cache only. Backend auto-deploys from same commit.
index = index.replace('IAKIDS • build 0.7.38', 'IAKIDS • build 0.7.39')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.38";', 'window.IAKIDS_BUILD_VERSION = "0.7.39";')
index = index.replace('/he/workspace/lesson-completion.js?v=0738', '/he/workspace/lesson-completion.js?v=0739')
ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.38";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.39";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0738', '/he/workspace/lesson-completion-core.js?v=0739')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
BACKEND.write_text(backend, encoding='utf-8')

print('Added compact homework teaching strategies and resolver; build 0.7.39')
