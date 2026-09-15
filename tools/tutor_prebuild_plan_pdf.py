#!/usr/bin/env python3
"""Pre-build plan: generate every lesson up-front with only its first two images,
create the rest on demand — cost, timeline, and what has to change. Hebrew PDF.

    backend/.venv/bin/python tools/tutor_prebuild_plan_pdf.py [out.pdf]

Numbers: production Supabase on 2026-09-15 — ai_calls for lessons 1, 12, 29, 31
(gemini-3.1-flash-lite-image $0.0336/image estimated, TTS exact via OpenRouter),
the STAGE timeline logged by media_trace for lesson 29, and lesson_units_content
(150 unit lessons, all grade 5 science, 2 parts each). Same helpers as the other reports.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from capacity_pdf import (
    W, H, M, he, Page, hero, table, box, node, arrow,
    BLUE, ORANGE, AQUA, INK, INK2, MUTED, LINE, PANEL, SURFACE, GOOD, WARN, BAD,
)

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'iakids-prebuild-plan.pdf')
DATE = '15 בספטמבר 2026'
WHITE = HexColor('#ffffff')

# ------------------------------------------------------------------ measured today
LESSONS_TOTAL, LESSONS_READY = 150, 2          # lesson_units_content; 2 and 31 are ready
LESSONS_TO_BUILD = LESSONS_TOTAL - LESSONS_READY
IMG_PRICE = 0.0336                              # $ per image, gemini-3.1-flash-lite-image (estimated)
IMAGES_PER_LESSON = 21                          # hero + 20 visuals (lesson 31: 9 + 11), lesson 12: 24
TEXT_COST = 0.085                               # 4 × gpt-5.6-sol + 1 × gpt-4o-mini, direct pricing ($0.03 via OpenRouter)
AUDIO_COST = 0.10                               # 20-24 TTS segments, 175-250 s of audio ($0.06 direct est., $0.125 OpenRouter exact)
FULL_COST = TEXT_COST + IMAGES_PER_LESSON * IMG_PRICE + AUDIO_COST          # ≈ $0.89 (measured $0.81-$1.05)
LIGHT_COST = TEXT_COST + 3 * IMG_PRICE + AUDIO_COST                         # hero + 2 visuals + audio ≈ $0.29
LIGHT_NOAUDIO_COST = TEXT_COST + 3 * IMG_PRICE                              # ≈ $0.19
# timeline (lesson 29, 2026-09-15 12:49, STAGE lines) — seconds
T_TEXT = [('המורה כותב חלק 1', 17.3), ('Director חלק 1', 15.6), ('המורה כותב חלק 2', 16.1),
          ('Director חלק 2', 7.0), ('Visual Director (תוכנית תמונות)', 19.2), ('שמירה + תור', 0.5)]
T_TEXT_TOTAL = 77
T_MEDIA = [('Hero (תמונת פתיחה)', 4), ('20 תמונות, 3 במקביל', 46), ('אודיו TTS, 17 קטעים בטור', 147), ('וידאו מעבר (נכס משותף)', 0)]
T_MEDIA_TOTAL = 152                             # audio and visuals run in parallel; job 739 (lesson 29): 151.7 s
WAIT_TODAY = T_TEXT_TOTAL + T_MEDIA_TOTAL       # the child cannot hear anything before audio is ready
IMG_SECONDS = 4.8                               # p50 per image today


def money(x):
    return f'${x:,.2f}'


# ------------------------------------------------------------------ page 1: summary
def page_summary(c):
    p = Page(c, 'בנייה מוקדמת של כל השיעורים עם שתי תמונות בלבד',
             f'תשובה לשאלה: האם אפשר שהכל ייראה מהיר, ושאר התמונות ייווצרו רק כשצריך?  ·  {DATE}', 1)
    p.h2('התשובה בקצרה')
    p.p('כן, אבל עם תיקון להנחה: התמונות אינן מה שהילד מחכה לו.')
    p.p('20 התמונות נגמרות אחרי 50 שניות (3 במקביל). האודיו לוקח 147 שניות והטקסט 77.')
    p.p('לכן "רק 2 תמונות" חוסך כסף (~$0.60 לשיעור, 70% מהעלות) אבל לא זמן.')
    p.p('את הזמן חוסכים רק אם הטקסט והאודיו נבנים מראש.')
    p.p('ההמלצה: לבנות מראש לכל שיעור את הטקסט, האודיו, ה־hero ושתי התמונות הראשונות.')
    p.p('שאר התמונות נוצרות בפתיחה, והן מקדימות את ההשמעה.')
    p.p('כך הילד מתחיל מיד, ומשלמים על 18 התמונות הנוספות רק בשיעורים שבאמת נפתחים. מנגנון ההשלמה כבר קיים ועבד היום.')

    y = p.y - 8
    cw = (W - 2 * M - 3 * 10) / 4
    tiles = [
        (money(FULL_COST), 'עלות שיעור מלא היום', f'{IMAGES_PER_LESSON} תמונות = 79%', BAD),
        (money(LIGHT_COST), 'עלות "בנייה קלה" לשיעור', 'טקסט + אודיו + 3 תמונות', GOOD),
        (money(LESSONS_TO_BUILD * FULL_COST), f'{LESSONS_TO_BUILD} שיעורים, בנייה מלאה', 'הכל מראש', BAD),
        (money(LESSONS_TO_BUILD * LIGHT_COST), f'{LESSONS_TO_BUILD} שיעורים, בנייה קלה', 'השאר לפי דרישה', GOOD),
    ]
    for i, (big, label, sub, col) in enumerate(tiles):
        hero(c, W - M - (i + 1) * cw - i * 10, y - 70, cw, big, label, sub, col)
    p.y = y - 90

    p.h2('מה הילד מרגיש')
    rows = [
        ('היום (שיעור חדש)', f'{WAIT_TODAY // 60}:{WAIT_TODAY % 60:02d} דקות', 'טקסט 77 ש׳ ואז אודיו 147 ש׳ (התמונות נגמרות אחרי 50). כלום לא מושמע לפני שכל האודיו מוכן'),
        ('בנייה מלאה מראש', '0 שניות', 'הכל קיים. עולה פי 3 ולוקח ~9.5 שעות עבודה למכונה'),
        (('בנייה קלה מראש (מומלץ)', GOOD), ('~0 שניות', GOOD), 'טקסט, אודיו, hero ו־2 תמונות מוכנים. תמונה 3 נוצרת תוך ~5 ש׳ מהפתיחה, לפני שמגיעים אליה'),
        ('בנייה קלה בלי אודיו', '~2.5 דקות', 'האודיו הוא צוואר הבקבוק האמיתי (147 ש׳). בלי אודיו מראש לא חסכנו כלום'),
    ]
    p.y = table(c, M, p.y, W - 2 * M, ['מצב', 'המתנה בפתיחה', 'למה'], rows, [0.22, 0.14, 0.64], row_h=20) - 14

    p.h2('שלושת המספרים שקובעים')
    p.p(f'• תמונה אחת: {money(IMG_PRICE)} ו־{IMG_SECONDS} שניות (p50 היום, 103 תמונות). {IMAGES_PER_LESSON} תמונות לשיעור = {money(IMAGES_PER_LESSON * IMG_PRICE)}.')
    p.p(f'• אודיו לשיעור: ~{money(AUDIO_COST)} ו־147 שניות (17 קטעים בטור, ~8.5 ש׳ לקטע). זה מה שהילד מחכה לו, לא התמונות.')
    p.p(f'• טקסט לשיעור: {money(TEXT_COST)} ו־77 שניות. ניתן לקצר ל־~60 ש׳ בהרצה מקבילה של Director חלק 1 עם המורה של חלק 2 (עמוד 2).')
    c.showPage()


# ------------------------------------------------------------------ page 2: timeline today
def page_timeline(c):
    p = Page(c, 'ציר הזמן של שיעור חדש היום', 'נמדד עם הלוגים החדשים (media_trace) על שיעור 29, 15.9.2026 12:49', 2)
    p.h2('שלב א: יצירת הטקסט (בקשת הדפדפן ממתינה)')
    rows = [(n, f'{s:.0f} ש׳', '') for n, s in T_TEXT]
    rows[0] = (rows[0][0], rows[0][1], 'gpt-5.6-sol; הסבר + שאלה')
    rows[1] = (rows[1][0], rows[1][1], 'gpt-5.6-sol; מחלק את ההסבר למקטעים (תוקן היום)')
    rows[2] = (rows[2][0], rows[2][1], 'תלוי בחלק 1 בלבד, לא ב־Director שלו')
    rows[4] = (rows[4][0], rows[4][1], 'gpt-4o-mini; ~20 פרומפטים לתמונות')
    rows.append((('סה"כ', INK), (f'{T_TEXT_TOTAL} ש׳', INK), 'הכל בטור. הדפדפן מקבל תשובה רק בסוף'))
    p.y = table(c, M, p.y, W - 2 * M, ['שלב', 'משך', 'הערה'], rows, [0.34, 0.12, 0.54]) - 12

    p.h2('שלב ב: media job ברקע (הילד רואה טקסט, מחכה לקול)')
    rows = [(n, f'{s} ש׳', '') for n, s in T_MEDIA]
    rows[0] = (rows[0][0], rows[0][1], 'ראשון, כדי שיהיה מסך פתיחה')
    rows[1] = (rows[1][0], rows[1][1], 'במקביל לאודיו. תמונת ייחוס לכל חלק לשמירת סגנון')
    rows[2] = (rows[2][0], rows[2][1], 'הצוואר: קטע אחר קטע (~8.5 ש׳ לקטע); האודיו מוגש רק כשכל הקטעים מוכנים')
    rows[3] = (rows[3][0], rows[3][1], 'משתמש בסרטון מעבר משותף, אין יצירה')
    rows.append((('סה"כ', INK), (f'{T_MEDIA_TOTAL} ש׳', INK), 'job 739 של שיעור 29: 151.7 ש׳. התמונות מסתיימות ב־T+50, האודיו ב־T+151'))
    p.y = table(c, M, p.y, W - 2 * M, ['שלב', 'משך', 'הערה'], rows, [0.34, 0.12, 0.54]) - 12

    # bar: where the time goes
    p.h2('איפה הזמן הולך (שניות, מרגע הלחיצה)')
    x0, y0, w = M, p.y - 30, W - 2 * M
    total = float(WAIT_TODAY)
    segs = [('טקסט 77', 77, BLUE), ('hero 4', 4, AQUA), ('אודיו 147 (כל 20 התמונות נגמרות ב־50 הראשונות)', 147, ORANGE)]
    xx = x0 + w
    for label, s, col in segs:
        sw = w * s / total
        c.setFillColor(col); c.rect(xx - sw, y0, sw, 22, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont('SB', 7.5)
        if sw > 40:
            c.drawCentredString(xx - sw / 2, y0 + 8, he(label))
        xx -= sw
    c.setFillColor(INK2); c.setFont('S', 8.5)
    c.drawRightString(W - M, y0 - 14, he(f'סה"כ {WAIT_TODAY} שניות עד שהילד שומע את המשפט הראשון. התמונות אינן על המסלול הקריטי, האודיו כן.'))
    p.y = y0 - 34

    p.h2('שני שיפורים שהלוג חשף, בלי קשר לבנייה מוקדמת')
    p.p('1. להריץ את Director של חלק 1 במקביל למורה של חלק 2: חוסך ~16 שניות מכל שיעור חדש (77 → ~60).')
    p.p('2. להגיש את האודיו של חלק 1 ברגע שהוא מוכן: חלק 1 מוכן ב־T+73, חלק 2 ב־T+151. חוסך 78 ש׳ לילד (פתוח מ־14.9).')
    p.p('3. TTS ב־2-3 קריאות במקביל במקום בטור (בתוך מגבלת 20 לדקה): 147 → ~60 ש׳. השיפור הגדול ביותר לשיעור שלא נבנה מראש.')
    p.note('שני אלה נשארים רלוונטיים גם עם בנייה מוקדמת: הם משפרים שיעורים שלא נבנו מראש ואת זמן הבנייה עצמו.')
    c.showPage()


# ------------------------------------------------------------------ page 3: options & costs
def page_options(c):
    p = Page(c, 'שלוש אפשרויות והעלות של כל אחת', f'{LESSONS_TO_BUILD} שיעורים ריקים היום (150 סה"כ, כולם מדעים כיתה ה׳, 2 חלקים כל אחד)', 3)
    p.h2('השוואה')
    full_h = LESSONS_TO_BUILD * (T_TEXT_TOTAL + T_MEDIA_TOTAL) / 3600
    light_h = LESSONS_TO_BUILD * (T_TEXT_TOTAL + 4 + 147) / 3600
    rows = [
        ('A. בנייה מלאה מראש', money(FULL_COST), money(LESSONS_TO_BUILD * FULL_COST), f'~{full_h:.0f} שעות', '0', 'משלמים על תמונות של שיעורים שאולי לעולם לא ייפתחו'),
        (('B. בנייה קלה (מומלץ)', GOOD), (money(LIGHT_COST), GOOD), (money(LESSONS_TO_BUILD * LIGHT_COST), GOOD), f'~{light_h:.0f} שעות', '~0', 'תמונות 3+ נוצרות בפתיחה, 3 במקביל, לפני שמגיעים אליהן'),
        ('C. בנייה קלה בלי אודיו', money(LIGHT_NOAUDIO_COST), money(LESSONS_TO_BUILD * LIGHT_NOAUDIO_COST), f'~{LESSONS_TO_BUILD * 90 / 3600:.0f} שעות', '~147 ש׳', 'זול, אבל הילד עדיין מחכה לאודיו. לא עונה על המטרה'),
        ('היום (לפי דרישה)', money(FULL_COST), 'לפי שימוש', '0', f'{WAIT_TODAY} ש׳', 'הילד מחכה 3.7 דקות בכל שיעור חדש'),
    ]
    p.y = table(c, M, p.y, W - 2 * M,
                ['אפשרות', 'לשיעור', f'ל־{LESSONS_TO_BUILD}', 'זמן בנייה', 'המתנה', 'הערה'],
                rows, [0.2, 0.09, 0.1, 0.11, 0.08, 0.42], row_h=22) - 12
    p.note('זמן בנייה: worker אחד. עם 2 במקביל מתחלק בשניים, אבל מגבלת ה־TTS (20 קריאות לדקה ב־OpenRouter) קובעת רצפה של ~2.6 שעות ל־148 שיעורים.')

    p.h2('מה קורה כשילד פותח שיעור שנבנה "קל"')
    steps = [
        ('0 ש׳', 'הטקסט, ה־hero, תמונות 1-2 והאודיו כבר ב־Storage. השיעור מתחיל מיד.'),
        ('0 ש׳', 'המסלול הקיים (QUEUE BACKGROUND VISUAL CHECK) מגלה שחסרות תמונות ומתזמן job בעדיפות גבוהה.'),
        ('~5 ש׳', 'תמונה 3 מוכנה (3 במקביל, 4.8 ש׳ כל אחת). הקטע השני של ההסבר נמשך ~10-15 ש׳, אז היא מגיעה לפני שצריך אותה.'),
        ('~35 ש׳', 'כל 9 התמונות של חלק 1 מוכנות. חלק 2 ממשיך באותו קצב.'),
        ('~70 ש׳', 'כל 20 התמונות מוכנות, השיעור שלם ל־Cache. ילד שני משלם 0.'),
    ]
    p.y = table(c, M, p.y, W - 2 * M, ['זמן מהפתיחה', 'מה קורה'], steps, [0.14, 0.86], row_h=20) - 12

    p.h2('חיסכון בפועל תלוי בכמה שיעורים נפתחים')
    rows = []
    for opened in (10, 25, 50, 100, LESSONS_TO_BUILD):
        a = LESSONS_TO_BUILD * FULL_COST
        b = LESSONS_TO_BUILD * LIGHT_COST + opened * (IMAGES_PER_LESSON - 3) * IMG_PRICE
        rows.append((f'{opened} שיעורים נפתחים', money(a), money(b), money(a - b)))
    p.y = table(c, M, p.y, W - 2 * M, ['תרחיש', 'A מלא', 'B קל + השלמה', 'חיסכון'], rows, [0.34, 0.22, 0.22, 0.22]) - 8
    p.note('גם אם כל 148 השיעורים ייפתחו, B לא יקר יותר מ־A: אותן תמונות, רק מאוחר יותר. תמונה 3 נוצרת תוך ~5 ש׳ ואילו קטע הסבר נמשך 8-15 ש׳, אז היא תמיד מקדימה.')
    c.showPage()


# ------------------------------------------------------------------ page 4: how it works
def page_how(c):
    p = Page(c, 'איך זה נבנה בקוד', 'ארבעה שינויים, רובם ניצול מנגנונים קיימים', 4)
    # flow diagram
    y = p.y - 8
    nw, nh, gap = 112, 58, 14
    x = W - M
    nodes = [
        ('prebuild job', ['סוג חדש ב־media_jobs', 'עדיפות נמוכה, לילה'], BLUE),
        ('טקסט', ['generate_unit_lesson_text()', 'מוצא מהמסלול לפונקציה'], BLUE),
        ('hero + תמונות 1-2', ['max_visuals=2', 'visual_status=partial'], AQUA),
        ('אודיו מלא', ['כמו היום', '21 קטעים'], ORANGE),
        ('בפתיחה: השלמה', ['VISUAL CHECK קיים', 'עדיפות גבוהה, לפי סדר'], GOOD),
    ]
    for i, (t, sub, col) in enumerate(nodes):
        nx = x - (i + 1) * nw - i * gap
        node(c, nx, y - nh, nw, nh, t, sub, col)
        if i:
            arrow(c, nx + nw + gap, y - nh / 2, nx + nw, y - nh / 2, LINE)
    p.y = y - nh - 26

    p.h2('השינויים הנדרשים')
    rows = [
        ('1', 'להוציא את יצירת הטקסט מהמסלול לפונקציה', 'היום הטקסט נוצר רק בתוך POST /api/tutor/unit-lesson עם ילד מחובר. ה־worker צריך לקרוא לאותו קוד בלי בקשה.', 'בינוני'),
        ('2', 'פרמטר max_visuals ל־job התמונות', 'generate_all_lesson_visuals_background(id, max_visuals=2) עוצר אחרי hero + 2, ומסמן visual_generation_status=partial בשורת השיעור.', 'קטן'),
        ('3', 'job חדש: unit_lesson_prebuild', 'טקסט → hero + 2 תמונות → אודיו. run_media_job כבר יודע להריץ לפי job_type. סקריפט tools/prebuild_lessons.py מכניס 148 שורות עם priority נמוך.', 'קטן'),
        ('4', 'סדר יצירה בהשלמה', 'ה־job הקיים unit_lesson_visuals כבר עובד לפי חלק ואז לפי order. לוודא שחלק 1 קודם ושהמסלול /visuals מחזיר מה שמוכן (כבר כך).', 'אפס'),
        ('5', 'Frontend', 'כבר מתמודד עם "תמונה לא מוכנה" ומבצע poll. לתקן את קצב ה־poll (1.5 ש׳) שגורם ל־429 (פתוח מ־14.9).', 'קטן'),
    ]
    p.y = table(c, M, p.y, W - 2 * M, ['#', 'שינוי', 'פירוט', 'היקף'], rows, [0.04, 0.24, 0.62, 0.1], row_h=30) - 12

    p.h2('הרצת הבנייה המוקדמת')
    p.p('• worker אחד, בלילה: 148 × ~3.8 דקות ≈ 9.4 שעות. עם WORKER_CONCURRENCY=2 ≈ 4.7 שעות; עם TTS מקבילי ≈ 3 שעות (מגבלת 20 קריאות לדקה).')
    p.p('• ריבוי משתמשים: הבנייה הלילית רצה בעדיפות נמוכה (media_jobs.priority) ונעצרת אוטומטית מול jobs של ילדים שפתחו שיעור; המשאב המשותף היחיד הוא מכסת ה־TTS.')
    p.p('• עלות כוללת ≈ ' + money(LESSONS_TO_BUILD * LIGHT_COST) + '. נרשמת ב־ai_calls עם purpose=prebuild, כך שאפשר לראות בדיוק כמה עלה.')
    p.p('• ה־STAGE SUMMARY של כל job מדפיס פירוק זמנים (טקסט / hero / תמונות / אודיו), כך שכל חריגה נראית בלוג.')
    p.p('• אפשר להתחיל מיחידה אחת (6 שיעורים, ~$1.7, 25 דקות) ולבדוק בעיניים לפני שמריצים את כולם.')
    c.showPage()


# ------------------------------------------------------------------ page 5: risks and basis
def page_basis(c):
    p = Page(c, 'סיכונים, הנחות ומה נמדד', DATE, 5)
    p.h2('סיכונים')
    rows = [
        ('מכסת TTS', 'Google AI Studio נגמר ב־14.9 אחרי ~100 שיעורים; OpenRouter מוגבל ל־20 קריאות לדקה. הבנייה צריכה לרוץ עם TTS_PROVIDER=openrouter ובקצב מבוקר.', WARN),
        ('מחיר תמונה משוער', '$0.0336 לתמונה הוא הערכה מטבלת המחירים, לא חיוב מאומת (cost_source=estimated). לבדוק מול החשבונית של Google אחרי 20 שיעורים.', WARN),
        ('תמונה 3 לא בזמן', 'השלמה עם יצירה אחת בכל פעם (לא 3) כדי לא לגזול משאבים ממשתמשים אחרים: 4.8 ש׳ לתמונה מול 8-15 ש׳ לקטע, עדיין מקדימה את ההשמעה.', GOOD),
        ('שינוי תוכן', 'content_version נשאר 1. אם משנים פרומפט אחרי הבנייה, צריך למחוק (skill delete-lesson) ולבנות שוב. הבאג של ה־Director תוקן היום לפני הבנייה, זו הסיבה לחכות איתה עד עכשיו.', WARN),
        ('זיכרון worker', 'שיא 194 MB ל־job. שני jobs במקביל = ~400 MB על מכונה של 2 GB עם swap. בסדר, לא יותר משניים.', GOOD),
    ]
    for name, txt, col in rows:
        box(c, M, p.y - 40, W - 2 * M, 38, WHITE, col, r=6)
        c.setFillColor(col); c.setFont('SB', 9); c.drawRightString(W - M - 8, p.y - 14, he(name))
        c.setFillColor(INK2); c.setFont('S', 8.3)
        # naive wrap at ~120 chars
        words, line, lines = txt.split(' '), '', []
        for wd in words:
            if len(line) + len(wd) > 118:
                lines.append(line); line = wd
            else:
                line = (line + ' ' + wd).strip()
        lines.append(line)
        for i, ln in enumerate(lines[:2]):
            c.drawRightString(W - M - 8, p.y - 26 - i * 10, he(ln))
        p.y -= 46

    p.h2('על מה המספרים נשענים')
    p.p('• ai_calls בפרוד, 15.9.2026: שיעור 1 ($0.81, 19 תמונות), שיעור 12 ($1.00, 24 תמונות), שיעור 31 ($1.05 כולל תיקון עצמי), 103 תמונות עם p50 4.8 ש׳.')
    p.p('• ציר הזמן: שורות STAGE START/DONE של media_trace על שיעור 29 (12:49-12:53): טקסט 77.4 ש׳, job 739: hero 4.0, תמונות 45.9, אודיו 147.4, סה"כ 151.7 ש׳.')
    p.p('• מלאי: lesson_units_content, 150 שיעורים, 148 ריקים אחרי המחיקה של היום, כולם 2 חלקים, מדעים כיתה ה׳.')
    p.p('• עלות אודיו: $0.125 מדויק דרך OpenRouter (246 ש׳) לעומת $0.063 הערכה ישירה; הדוח משתמש ב־$0.10 כממוצע.')
    p.note('כל הסכומים בדולרים לפי המחירון הנוכחי. מספרי הזמן הם worker יחיד על המכונה הנוכחית (2 vCPU / 2 GB).')
    c.showPage()


def main():
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle('iakids — pre-build plan')
    for fn in (page_summary, page_timeline, page_options, page_how, page_basis):
        fn(c)
    c.save()
    print(OUT)


if __name__ == '__main__':
    main()
