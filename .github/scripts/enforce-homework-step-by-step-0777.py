from pathlib import Path

# Trigger rerun: strict step-by-step flow 0.7.77
BACKEND = Path('backend-ai-tutor-he/main.py')
INDEX = Path('he/workspace/index.html')

backend = BACKEND.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old_helper = '''def build_safe_homework_first_guidance(
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

new_helper = '''def build_safe_homework_first_guidance(
        current_question: str,
        source_text: str,
        child_gender: str | None = None,
        force_step_by_step: bool = False
) -> str:
    q = str(current_question or '').strip()
    female = str(child_gender or '').strip().lower() in ('female', 'f', 'נקבה')

    if force_step_by_step:
        if female:
            return (
                "אני אסביר לך שלב־שלב איך לענות על השאלה הזאת.\\n"
                f"שלב 1: נקרא את השאלה ונבין מה מחפשים. השאלה היא: {q}\\n"
                "שלב 2: נחזור לקטע ונמצא את המקום שבו מדברים על הדמות או הדבר שמופיעים בשאלה.\\n"
                "שלב 3: באותו מקום נחפש את הפעולה או העובדה שעונה בדיוק על מילת השאלה.\\n"
                "עכשיו נעשה את שלב 1 יחד: מה אנחנו צריכות למצוא בטקסט כדי לענות על השאלה?"
            )
        return (
            "אני אסביר לך שלב־שלב איך לענות על השאלה הזאת.\\n"
            f"שלב 1: נקרא את השאלה ונבין מה מחפשים. השאלה היא: {q}\\n"
            "שלב 2: נחזור לקטע ונמצא את המקום שבו מדברים על הדמות או הדבר שמופיעים בשאלה.\\n"
            "שלב 3: באותו מקום נחפש את הפעולה או העובדה שעונה בדיוק על מילת השאלה.\\n"
            "עכשיו נעשה את שלב 1 יחד: מה אנחנו צריכים למצוא בטקסט כדי לענות על השאלה?"
        )

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

if old_helper in backend:
    backend = backend.replace(old_helper, new_helper, 1)
elif 'force_step_by_step: bool = False' not in backend:
    raise SystemExit('build_safe_homework_first_guidance block not found')

old_guard = '''    if parsed:
        is_first_help_turn = (
            "הילד בחר:" in str(req.answer or "")
            or "HELP MODE:" in str(req.answer or "")
        )

        if is_first_help_turn and homework_response_leaks_source_answer(
                parsed.teacher_response,
                req.source_text,
                req.current_question
        ):
            print("HOMEWORK ANSWER LEAK GUARD TRIGGERED", {
                "question": req.current_question,
                "teacher_response": parsed.teacher_response
            })
            parsed.teacher_response = build_safe_homework_first_guidance(
                req.current_question,
                req.source_text,
                child.get("gender") if isinstance(child, dict) else None
            )
            parsed.feedback = ""
            parsed.answer_sufficient = False
            parsed.completed_step = None
'''

new_guard = '''    if parsed:
        answer_context = str(req.answer or "")
        is_first_help_turn = (
            "הילד בחר:" in answer_context
            or "HELP MODE:" in answer_context
        )
        is_step_by_step_mode = (
            "לפתור יחד שלב־שלב" in answer_context
            or "SOLVE TOGETHER STEP BY STEP" in answer_context.upper()
        )

        # STRICT STEP-BY-STEP ENTRY (0.7.77)
        # If the child explicitly chose step-by-step help, the first teacher
        # response is deterministic: explain the method, name the steps, and
        # begin with step 1. Do not depend on the model remembering the format.
        if is_first_help_turn and is_step_by_step_mode:
            parsed.teacher_response = build_safe_homework_first_guidance(
                req.current_question,
                req.source_text,
                child.get("gender") if isinstance(child, dict) else None,
                force_step_by_step=True
            )
            parsed.feedback = ""
            parsed.answer_sufficient = False
            parsed.completed_step = None
            parsed.next_step = "שלב 1 — להבין מה השאלה מבקשת"

        elif is_first_help_turn and homework_response_leaks_source_answer(
                parsed.teacher_response,
                req.source_text,
                req.current_question
        ):
            print("HOMEWORK ANSWER LEAK GUARD TRIGGERED", {
                "question": req.current_question,
                "teacher_response": parsed.teacher_response
            })
            parsed.teacher_response = build_safe_homework_first_guidance(
                req.current_question,
                req.source_text,
                child.get("gender") if isinstance(child, dict) else None
            )
            parsed.feedback = ""
            parsed.answer_sufficient = False
            parsed.completed_step = None
'''

if old_guard in backend:
    backend = backend.replace(old_guard, new_guard, 1)
elif 'STRICT STEP-BY-STEP ENTRY (0.7.77)' not in backend:
    raise SystemExit('homework guard block not found')

for oldv in ('0.7.75','0.7.76'):
    index = index.replace(f'IAKIDS • build {oldv}', 'IAKIDS • build 0.7.77')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{oldv}";', 'window.IAKIDS_BUILD_VERSION = "0.7.77";')

BACKEND.write_text(backend, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Enforced deterministic homework step-by-step entry; build 0.7.77')
