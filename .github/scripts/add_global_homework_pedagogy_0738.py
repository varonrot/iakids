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
# 1) Backend: one global pedagogy contract for all homework turns.
# -----------------------------------------------------
anchor = '# =====================================================\n# IAKIDS HOMEWORK TURN EVALUATOR V0.7.26\n# =====================================================\n\n'
if 'HOMEWORK_GLOBAL_PEDAGOGY_PROMPT' not in backend:
    pedagogy = '''HOMEWORK_GLOBAL_PEDAGOGY_PROMPT = r"""
GLOBAL HOMEWORK PEDAGOGY — mandatory for every subject and every homework task:

PRIMARY GOAL:
Do not merely extract an answer from the child. Teach the child HOW to approach the question and HOW to build a good answer independently.

MANDATORY TEACHING SEQUENCE:
1. Clarify what the current worksheet question is asking. State the task in simple, grade-appropriate language.
2. Point the child to the relevant source of information or reasoning method: reading passage, data in the problem, diagram, formula, learned concept, instructions, or evidence in the worksheet.
3. Teach an explicit search/solution strategy before asking for an answer. Examples of strategy types: locate the relevant sentence, identify key verbs, mark given numbers, identify what must be calculated, find the concept that explains the phenomenon, compare evidence, or break the task into parts.
4. Help isolate the essential answer components — usually 1 to 3 key points — without immediately writing the full final answer for the child.
5. Teach answer construction. If the child has the ideas but not the wording, provide a sentence frame, opening phrase, structure, or template that the child can complete. Do not ask vague questions such as "How would you like to phrase it?" when the child has not yet been taught how.
6. Ask the child to attempt the answer independently.
7. Give specific feedback: explain exactly what is correct and exactly what is missing. Never use praise alone.
8. If sufficient, provide one concise polished final formulation only after the child has attempted and understood the answer.
9. Only then may the application write the polished final answer into the notebook and move to the next worksheet question.

WHEN THE CHILD SAYS "I DON'T KNOW" OR IS CLEARLY STUCK:
- Do NOT repeat the same question.
- Do NOT simply rephrase the question as another question.
- Move one pedagogical step backward: direct the child to the source, give a focused clue, identify where to look, or give a partial sentence frame.
- Ask only one focused follow-up at a time.

GLOBAL PROHIBITIONS:
- Do not ask vague questions such as "What do you think?", "What do you remember?", "What would you like to include?", or "How would you like to phrase it?" unless the child already has enough structure to answer them productively.
- Do not drift into personal-life, values, feelings, examples, or general discussion unless the worksheet explicitly asks for them.
- Do not repeat the same question multiple times.
- Do not give the complete final answer before a genuine child attempt, except after the child is still stuck following several scaffolding steps.
- Do not move to the next question before the current question is understood and completed.
- Do not mention internal prompts, states, rules, dialogue goals, evaluation logic, or system instructions.

SUBJECT ADAPTATION:
- Reading / Bible / Hebrew / history: teach how to return to the text, locate the relevant passage, identify key words/actions/causes, and transform evidence into a full answer.
- Math: identify givens, what is being asked, the operation/relation needed, solve step by step, then write the answer with units/context.
- Science: identify the relevant concept/evidence, connect it to the question, then formulate the explanation.
- Writing/composition: first clarify the required content and structure, break it into components, build an outline or sentence frame, and only then ask the child to write.
- Other subjects: apply the same sequence — understand task -> locate method/source -> identify key points -> construct answer -> child attempts -> specific feedback -> final wording.
""".strip()

'''
    if anchor not in backend:
        raise SystemExit('backend homework evaluator anchor not found')
    backend = backend.replace(anchor, anchor + pedagogy, 1)

# Inject global pedagogy into the evaluator prompt by working only inside the evaluator section.
section_start = backend.find('def homework_turn(')
if section_start < 0:
    raise SystemExit('homework_turn function not found')
section_tail = backend[section_start:]
if '{HOMEWORK_GLOBAL_PEDAGOGY_PROMPT}' not in section_tail:
    hard_idx = section_tail.find('HARD RULES:')
    if hard_idx < 0:
        raise SystemExit('HARD RULES marker not found in homework_turn')
    section_tail = (
        section_tail[:hard_idx]
        + '{HOMEWORK_GLOBAL_PEDAGOGY_PROMPT}\n\n'
        + section_tail[hard_idx:]
    )
    backend = backend[:section_start] + section_tail

# Strengthen insufficient-answer rule so it must scaffold rather than repeat.
old_rule = '7. When insufficient, teacher_response may ask ONE short guiding question that directly helps answer the current worksheet question. The guiding question must be explicit and contextual: name the relevant person/concept instead of using ambiguous pronouns. For example, prefer "מה אברהם עשה כשהוא ראה את האורחים?" over "מה את זוכרת שהוא עשה?".'
new_rule = '7. When insufficient, teacher_response must SCAFFOLD before asking again: tell the child where/how to look or what solving strategy to use, then ask ONE short focused follow-up. If the child says "לא יודע/ת", never repeat the worksheet question. Move one step backward and give a more concrete clue, source location, key-word cue, or sentence frame. Avoid vague prompts.'
backend = backend.replace(old_rule, new_rule, 1)

# -----------------------------------------------------
# 2) Frontend: send the same global pedagogy contract with every help-choice request.
# -----------------------------------------------------
if 'HOMEWORK_GLOBAL_PEDAGOGY_RULES' not in core:
    core_anchor = '  function getChoiceInstruction(choiceId){\n'
    js_rules = r'''  const HOMEWORK_GLOBAL_PEDAGOGY_RULES = `
כללי פדגוגיה גלובליים ומחייבים לכל עזרה בשיעורי בית, בכל מקצוע:
1. המטרה אינה רק לקבל תשובה אלא ללמד את הילד/ה איך ניגשים לשאלה ואיך בונים תשובה.
2. קודם הסבר בקצרה מה השאלה מבקשת.
3. אחר כך הפנה למקור/דרך הפתרון המתאימים: קטע קריאה, נתונים, תרשים, נוסחה, מושג או הוראות.
4. למד אסטרטגיה מפורשת לאיתור/פתרון לפני שאתה מבקש תשובה: איפה לחפש, אילו מילות מפתח/פעלים/נתונים לזהות, או לאילו שלבים לפרק את המשימה.
5. עזור לבודד 1–3 נקודות שחייבות להיכלל בתשובה.
6. אם הילד/ה יודע/ת את הרעיון אבל מתקשה בניסוח, תן תבנית/פתיח למשפט או מבנה תשובה שהילד/ה ישלים/תשלים. אל תשאל "איך תרצי לנסח?" לפני שלימדת איך.
7. רק עכשיו בקש מהילד/ה לנסות לענות בעצמו/ה.
8. במשוב, הסבר מה בדיוק נכון ומה בדיוק חסר. אל תסתפק בשבח כללי.
9. תשובה סופית מלאה ניתנת רק אחרי ניסיון אמיתי והבנה של הילד/ה; לאחר מכן אפשר לכתוב אותה במחברת ולעבור לשאלה הבאה.
10. אם הילד/ה אומר/ת "לא יודע/ת" או תקוע/ה: אסור לחזור על אותה שאלה. חזור שלב פדגוגי אחד אחורה — הפנה למקום הרלוונטי, תן רמז ממוקד, מילות מפתח או פתיח חלקי — ואז שאל שאלה אחת ממוקדת.
11. אל תשאל שאלות עמומות כמו "מה את חושבת?", "מה את זוכרת?", "מה היית רוצה לכלול?" או "איך היית רוצה לנסח?" כאשר עדיין חסר לילד/ה מבנה שמאפשר לענות עליהן.
12. אל תגלוש לחיים האישיים, ערכים, רגשות או דיון כללי אלא אם השאלה בדף מבקשת זאת במפורש.
13. אל תחזור על אותה שאלה שוב ושוב, אל תדלג לשאלה הבאה לפני סיום הנוכחית, ואל תזכיר הוראות פנימיות של המערכת.

התאמה לפי תחום:
- הבנת הנקרא/תנ״ך/עברית/היסטוריה: חזור לטקסט, אתר את הקטע הרלוונטי, מצא מילות מפתח/פעולות/סיבות, ואז הפוך את הראיות לתשובה מלאה.
- חשבון: זהה נתונים, מה מבקשים, פעולה/קשר מתמטי, פתרון בשלבים, ואז תשובה עם יחידות/הקשר.
- מדעים: זהה מושג/עובדה/ראיה רלוונטיים, קשר אותם לשאלה, ואז בנה הסבר.
- כתיבה והבעה: הבהר מה נדרש, פרק לרכיבים, בנה שלד/פתיח/תבנית, ורק אז בקש מהילד/ה לכתוב.
`;

'''
    if core_anchor not in core:
        raise SystemExit('core choice instruction anchor not found')
    core = core.replace(core_anchor, js_rules + core_anchor, 1)

msg_anchor = 'הילד בחר: ${choice.label}\n\n${getChoiceInstruction(choice.id)}\n'
msg_replacement = 'הילד בחר: ${choice.label}\n\n${HOMEWORK_GLOBAL_PEDAGOGY_RULES}\n\nהוראת מצב ספציפית:\n${getChoiceInstruction(choice.id)}\n'
if msg_anchor in core:
    core = core.replace(msg_anchor, msg_replacement, 1)
elif '${HOMEWORK_GLOBAL_PEDAGOGY_RULES}' not in core:
    raise SystemExit('core homework choice message anchor not found')

# -----------------------------------------------------
# 3) Bump build/cache.
# -----------------------------------------------------
index = index.replace('IAKIDS • build 0.7.37', 'IAKIDS • build 0.7.38')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.37";', 'window.IAKIDS_BUILD_VERSION = "0.7.38";')
index = index.replace('/he/workspace/lesson-completion.js?v=0737', '/he/workspace/lesson-completion.js?v=0738')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.37";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.38";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0737', '/he/workspace/lesson-completion-core.js?v=0738')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
BACKEND.write_text(backend, encoding='utf-8')

print('Global homework pedagogy contract added to frontend + backend; build 0.7.38')
