from pathlib import Path

BACKEND = Path('backend-ai-tutor-he/main.py')
INDEX = Path('he/workspace/index.html')

backend = BACKEND.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old = '''        is_step_by_step_mode = (help_mode_name == "solve_together")
        is_first_help_turn = (
            is_step_by_step_mode
            and not progress_state
        )
'''
new = '''        is_step_by_step_mode = (help_mode_name == "solve_together")

        # The frontend always sends a textual progress summary, even before
        # the first child attempt (for example: "None yet"). Therefore an
        # empty-string check is not enough to identify the first help turn.
        progress_lower = progress_state.lower()
        has_child_attempt = (
            "child:" in progress_lower
            or "teacher:" in progress_lower
            or "attempt" in progress_lower
        )
        has_completed_step = not (
            not progress_state
            or "none yet" in progress_lower
            or "no earlier step state" in progress_lower
        )
        is_first_help_turn = (
            is_step_by_step_mode
            and not has_child_attempt
            and not has_completed_step
        )
'''

if old in backend:
    backend = backend.replace(old, new, 1)
elif 'has_child_attempt = (' not in backend:
    raise SystemExit('step-by-step first-turn detection anchor not found')

# Make the deterministic opening stronger and more age-appropriate. It must
# explain the method before asking the child anything, and explicitly name
# each step so the UX truly feels step-by-step.
old_female = '''                "אני אסביר לך שלב־שלב איך לענות על השאלה הזאת.\\n"
                f"שלב 1: קודם נקרא את השאלה ונבין בדיוק מה היא מבקשת: {q}\\n"
                "שלב 2: נחזור לטקסט ונחפש את המקום שבו מופיעה הדמות או מילת המפתח מהשאלה.\\n"
                "שלב 3: באותו משפט נחפש מה הדמות עשתה, מה קרה, או איזו עובדה עונה על השאלה.\\n"
                "שלב 4: נחבר את מה שמצאנו למשפט תשובה קצר וברור.\\n"
                "עכשיו נעשה את שלב 1 יחד: על מי מדברת השאלה ומה אנחנו צריכות לגלות עליו?"
'''
new_female = '''                "אני אסביר לך שלב־שלב איך עונים על השאלה הזאת.\\n\\n"
                f"שלב 1 — קוראות את השאלה: {q}\\n"
                "אנחנו בודקות על מי מדברים ומה בדיוק מבקשים לדעת.\\n\\n"
                "שלב 2 — חוזרות לטקסט: מחפשות את המקום שבו מופיעה הדמות מהשאלה.\\n\\n"
                "שלב 3 — מוצאות את המידע: מחפשות באותו חלק את הפעולה או העובדה שעונה לשאלה.\\n\\n"
                "שלב 4 — בונות תשובה: מחברות את מה שמצאנו למשפט קצר וברור.\\n\\n"
                "עכשיו מתחילות בשלב 1 בלבד: על מי מדברת השאלה ומה אנחנו צריכות לגלות עליו?"
'''
if old_female in backend:
    backend = backend.replace(old_female, new_female, 1)

old_male = '''            "אני אסביר לך שלב־שלב איך לענות על השאלה הזאת.\\n"
            f"שלב 1: קודם נקרא את השאלה ונבין בדיוק מה היא מבקשת: {q}\\n"
            "שלב 2: נחזור לטקסט ונחפש את המקום שבו מופיעה הדמות או מילת המפתח מהשאלה.\\n"
            "שלב 3: באותו משפט נחפש מה הדמות עשתה, מה קרה, או איזו עובדה עונה על השאלה.\\n"
            "שלב 4: נחבר את מה שמצאנו למשפט תשובה קצר וברור.\\n"
            "עכשיו נעשה את שלב 1 יחד: על מי מדברת השאלה ומה אנחנו צריכים לגלות עליו?"
'''
new_male = '''            "אני אסביר לך שלב־שלב איך עונים על השאלה הזאת.\\n\\n"
            f"שלב 1 — קוראים את השאלה: {q}\\n"
            "אנחנו בודקים על מי מדברים ומה בדיוק מבקשים לדעת.\\n\\n"
            "שלב 2 — חוזרים לטקסט: מחפשים את המקום שבו מופיעה הדמות מהשאלה.\\n\\n"
            "שלב 3 — מוצאים את המידע: מחפשים באותו חלק את הפעולה או העובדה שעונה לשאלה.\\n\\n"
            "שלב 4 — בונים תשובה: מחברים את מה שמצאנו למשפט קצר וברור.\\n\\n"
            "עכשיו מתחילים בשלב 1 בלבד: על מי מדברת השאלה ומה אנחנו צריכים לגלות עליו?"
'''
if old_male in backend:
    backend = backend.replace(old_male, new_male, 1)

for oldv in ('0.7.77','0.7.78'):
    index = index.replace(f'IAKIDS • build {oldv}', 'IAKIDS • build 0.7.79')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{oldv}";', 'window.IAKIDS_BUILD_VERSION = "0.7.79";')

BACKEND.write_text(backend, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Fixed first-turn detection for step-by-step homework; build 0.7.79')
