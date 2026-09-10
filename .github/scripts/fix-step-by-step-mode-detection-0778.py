from pathlib import Path

BACKEND = Path('backend-ai-tutor-he/main.py')
INDEX = Path('he/workspace/index.html')

backend = BACKEND.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old = '''        answer_context = str(req.answer or "")
        is_first_help_turn = (
            "הילד בחר:" in answer_context
            or "HELP MODE:" in answer_context
        )
        is_step_by_step_mode = (
            "לפתור יחד שלב־שלב" in answer_context
            or "SOLVE TOGETHER STEP BY STEP" in answer_context.upper()
        )
'''

new = '''        answer_context = str(req.answer or "")

        # IMPORTANT: help mode is a dedicated request field. The visible/saved
        # prompt contains "הילד בחר", but req.answer itself usually does not.
        # Therefore mode detection must use req.help_mode, not answer text.
        help_mode_name = str(req.help_mode or "").strip()
        progress_state = str(req.progress_context or "").strip()

        is_step_by_step_mode = (help_mode_name == "solve_together")
        is_first_help_turn = (
            is_step_by_step_mode
            and not progress_state
        )

        if is_step_by_step_mode:
            print("HOMEWORK STEP MODE DETECTED", {
                "help_mode": help_mode_name,
                "first_turn": is_first_help_turn,
                "has_progress": bool(progress_state)
            })
'''

if old not in backend:
    raise SystemExit('step-by-step detection block not found')
backend = backend.replace(old, new, 1)

# Make the deterministic first response sound like an actual guided lesson.
old_f = '''                "אני אסביר לך שלב־שלב איך לענות על השאלה הזאת.\\n"
                f"שלב 1: נקרא את השאלה ונבין מה מחפשים. השאלה היא: {q}\\n"
                "שלב 2: נחזור לקטע ונמצא את המקום שבו מדברים על הדמות או הדבר שמופיעים בשאלה.\\n"
                "שלב 3: באותו מקום נחפש את הפעולה או העובדה שעונה בדיוק על מילת השאלה.\\n"
                "עכשיו נעשה את שלב 1 יחד: מה אנחנו צריכות למצוא בטקסט כדי לענות על השאלה?"
'''
new_f = '''                "אני אסביר לך שלב־שלב איך לענות על השאלה הזאת.\\n"
                f"שלב 1: קודם נקרא את השאלה ונבין בדיוק מה היא מבקשת: {q}\\n"
                "שלב 2: נחזור לטקסט ונחפש את המקום שבו מופיעה הדמות או מילת המפתח מהשאלה.\\n"
                "שלב 3: באותו משפט נחפש מה הדמות עשתה, מה קרה, או איזו עובדה עונה על השאלה.\\n"
                "שלב 4: נחבר את מה שמצאנו למשפט תשובה קצר וברור.\\n"
                "עכשיו נעשה את שלב 1 יחד: על מי מדברת השאלה ומה אנחנו צריכות לגלות עליו?"
'''
if old_f in backend:
    backend = backend.replace(old_f, new_f, 1)

old_m = '''            "אני אסביר לך שלב־שלב איך לענות על השאלה הזאת.\\n"
            f"שלב 1: נקרא את השאלה ונבין מה מחפשים. השאלה היא: {q}\\n"
            "שלב 2: נחזור לקטע ונמצא את המקום שבו מדברים על הדמות או הדבר שמופיעים בשאלה.\\n"
            "שלב 3: באותו מקום נחפש את הפעולה או העובדה שעונה בדיוק על מילת השאלה.\\n"
            "עכשיו נעשה את שלב 1 יחד: מה אנחנו צריכים למצוא בטקסט כדי לענות על השאלה?"
'''
new_m = '''            "אני אסביר לך שלב־שלב איך לענות על השאלה הזאת.\\n"
            f"שלב 1: קודם נקרא את השאלה ונבין בדיוק מה היא מבקשת: {q}\\n"
            "שלב 2: נחזור לטקסט ונחפש את המקום שבו מופיעה הדמות או מילת המפתח מהשאלה.\\n"
            "שלב 3: באותו משפט נחפש מה הדמות עשתה, מה קרה, או איזו עובדה עונה על השאלה.\\n"
            "שלב 4: נחבר את מה שמצאנו למשפט תשובה קצר וברור.\\n"
            "עכשיו נעשה את שלב 1 יחד: על מי מדברת השאלה ומה אנחנו צריכים לגלות עליו?"
'''
if old_m in backend:
    backend = backend.replace(old_m, new_m, 1)

for oldv in ('0.7.76','0.7.77'):
    index = index.replace(f'IAKIDS • build {oldv}', 'IAKIDS • build 0.7.78')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{oldv}";', 'window.IAKIDS_BUILD_VERSION = "0.7.78";')

BACKEND.write_text(backend, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Fixed step-by-step mode detection to use req.help_mode; build 0.7.78')
