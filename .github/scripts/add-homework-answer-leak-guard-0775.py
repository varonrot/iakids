from pathlib import Path

BACKEND = Path('backend-ai-tutor-he/main.py')
INDEX = Path('he/workspace/index.html')

backend = BACKEND.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

helper_anchor = 'class HomeworkTurnEvaluation(BaseModel):\n'
helper_code = r'''def _normalize_homework_guard_text(value: str) -> str:
    text = str(value or "").lower()
    text = re.sub(r'[\"\'׳״“”‘’.,!?;:()\[\]{}<>\\/|_\-–—]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def homework_response_leaks_source_answer(
        teacher_response: str,
        source_text: str,
        current_question: str,
        min_words: int = 6
) -> bool:
    response = _normalize_homework_guard_text(teacher_response)
    source = _normalize_homework_guard_text(source_text)
    question = _normalize_homework_guard_text(current_question)

    if not response or not source:
        return False

    words = response.split()
    if len(words) < min_words:
        return False

    for size in (9, 8, 7, 6):
        if size < min_words or len(words) < size:
            continue
        for i in range(0, len(words) - size + 1):
            phrase = ' '.join(words[i:i + size]).strip()
            if not phrase:
                continue
            if question and phrase in question:
                continue
            if phrase in source:
                return True

    return False


def build_safe_homework_first_guidance(
        current_question: str,
        source_text: str,
        child_gender: str | None = None
) -> str:
    q = str(current_question or '').strip()
    female = str(child_gender or '').strip().lower() in ('female', 'f', 'נקבה')

    if source_text:
        if female:
            return (
                f"בואי נפתור את זה בלי לגלות את התשובה. "
                f"כששואלים: {q} אנחנו מחפשות בטקסט את הפעולות או העובדות שעונות בדיוק על השאלה. "
                f"חפשי במשפט שבו מתחיל התיאור של מה שקרה. מה הדבר הראשון שאת מוצאת שם?"
            )
        return (
            f"בוא נפתור את זה בלי לגלות את התשובה. "
            f"כששואלים: {q} אנחנו מחפשים בטקסט את הפעולות או העובדות שעונות בדיוק על השאלה. "
            f"חפש במשפט שבו מתחיל התיאור של מה שקרה. מה הדבר הראשון שאתה מוצא שם?"
        )

    if female:
        return (
            f"בואי נפתור את זה שלב־שלב בלי לגלות את התשובה. "
            f"השאלה היא: {q} מה הצעד הראשון שצריך לעשות כדי לענות עליה?"
        )
    return (
        f"בוא נפתור את זה שלב־שלב בלי לגלות את התשובה. "
        f"השאלה היא: {q} מה הצעד הראשון שצריך לעשות כדי לענות עליה?"
    )


'''
if 'def homework_response_leaks_source_answer(' not in backend:
    if helper_anchor not in backend:
        raise SystemExit('HomeworkTurnEvaluation anchor not found')
    backend = backend.replace(helper_anchor, helper_code + helper_anchor, 1)

parsed_anchor = '    parsed = completion.choices[0].message.parsed\n'
guard_code = '''    parsed = completion.choices[0].message.parsed\n\n    # HARD ANSWER-LEAK GUARD (0.7.75)\n    # On the first help-mode response, prevent the teacher from copying a\n    # source sentence that contains the worksheet answer before the child tries.\n    if parsed:\n        is_first_help_turn = (\n            "הילד בחר:" in str(req.answer or "")\n            or "HELP MODE:" in str(req.answer or "")\n        )\n\n        if is_first_help_turn and homework_response_leaks_source_answer(\n                parsed.teacher_response,\n                req.source_text,\n                req.current_question\n        ):\n            print("HOMEWORK ANSWER LEAK GUARD TRIGGERED", {\n                "question": req.current_question,\n                "teacher_response": parsed.teacher_response\n            })\n            parsed.teacher_response = build_safe_homework_first_guidance(\n                req.current_question,\n                req.source_text,\n                child.get("gender") if isinstance(child, dict) else None\n            )\n            parsed.feedback = ""\n            parsed.answer_sufficient = False\n            parsed.completed_step = None\n'''

if 'HOMEWORK ANSWER LEAK GUARD TRIGGERED' not in backend:
    if parsed_anchor not in backend:
        raise SystemExit('homework parsed anchor not found')
    backend = backend.replace(parsed_anchor, guard_code, 1)

for oldv in ('0.7.73','0.7.74'):
    index = index.replace(f'IAKIDS • build {oldv}', 'IAKIDS • build 0.7.75')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{oldv}";', 'window.IAKIDS_BUILD_VERSION = "0.7.75";')

BACKEND.write_text(backend, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Added deterministic homework answer-leak guard; build 0.7.75')
