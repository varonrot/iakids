#!/usr/bin/env python3
"""Draw the production-readiness report as a PDF.

    backend/.venv/bin/python tools/readiness_pdf.py [out.pdf]

Same drawing style as tools/capacity_pdf.py — it imports the helpers from there rather
than repeating them, so the two reports stay one design. What it adds is the question
that capacity alone does not answer: what is still in the way of going live.

Every number here was measured on 2026-09-10 and is written down in tools/CAPACITY.md;
every finding is in SECURITY.md and TODO.md. This file draws them, it does not decide
them — change the source of truth first.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from capacity_pdf import (
    W, H, M, he, Page, hero, axes, bars, table, box, node, arrow,
    BLUE, ORANGE, AQUA, INK, INK2, MUTED, LINE, PANEL, SURFACE, GOOD, WARN, BAD,
)

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'iakids-readiness.pdf')

# ------------------------------------------------------------------ measured, 2026-09-10
# wrk, generator under 50% CPU at every one of these, so they are the service's limits.
CEILINGS = [
    ('קריאה פשוטה', 1050, AQUA),
    ('שליפת 20 שאלות', 550, BLUE),
    ('רישום תשובה', 700, ORANGE),
]

# What one child costs per second, and therefore how many fit.
CALLS_NOW, CALLS_AFTER, SESSION_SEC = 14, 4, 240
MIXED_RPS = 600                                  # the conservative middle of the three above


def clamp(n):
    return f'{int(round(n / 100.0) * 100):,}'



def step(p, n, text, color=BLUE, size=9.5):
    """One numbered line. The number is drawn separately: inside a bidi-reordered
    Hebrew line a leading "1." ends up at the wrong end."""
    c = p.c
    if str(n).strip():                      # a blank number means "same item, next line"
        c.setFillColor(color); c.circle(W - M - 5, p.y + 3, 7.5, fill=1, stroke=0)
        c.setFillColor(HexColor('#ffffff')); c.setFont('SB', 7.5)
        c.drawCentredString(W - M - 5, p.y + 0.8, str(n))
    c.setFillColor(INK2); c.setFont('S', size)
    c.drawRightString(W - M - 18, p.y, he(text))
    p.y -= 14


def checklist(c, x, y, w, items, title):
    """The go-live list, as something a person can tick off."""
    h = 26 + len(items) * 16
    box(c, x, y - h, w, h, HexColor('#ffffff'), LINE)
    c.setFillColor(INK); c.setFont('SB', 10)
    c.drawRightString(x + w - 12, y - 18, he(title))
    yy = y - 34
    for done, t in items:
        c.setStrokeColor(GOOD if done else HexColor('#c9ced6')); c.setLineWidth(1.2)
        c.setFillColor(HexColor('#eaf6ef') if done else HexColor('#ffffff'))
        c.roundRect(x + w - 24, yy - 3, 10, 10, 2, fill=1, stroke=1)
        if done:
            c.setStrokeColor(GOOD); c.setLineWidth(1.6)
            c.line(x + w - 21.5, yy + 2, x + w - 19.5, yy - 0.5)
            c.line(x + w - 19.5, yy - 0.5, x + w - 16.5, yy + 4.5)
        c.setFillColor(INK2 if done else INK); c.setFont('S', 8.5)
        c.drawRightString(x + w - 32, yy, he(t))
        yy -= 16
    return y - h


def page1(c):
    p = Page(c, 'מוכנות לפרודקשן', 'iakids.app · 10 בספטמבר 2026 · נמדד, לא משוער', 1)

    p.p('הדוח הזה עונה על שתי שאלות: כמה ילדים המערכת מחזיקה בכל איזור, ומה עוד עומד בדרך.')
    p.p('כל מספר כאן נמדד באותו יום מול המערכת החיה. מה שלא נמדד — כתוב שלא נמדד.')
    p.y -= 8

    w = (W - 2 * M - 24) / 3
    hero(c, W - M - w, p.y - 70, w, clamp(MIXED_RPS / (CALLS_NOW / SESSION_SEC)),
         'ילדים משחקים בו-זמנית', 'היום, כפי שהמערכת עובדת עכשיו', BLUE)
    hero(c, W - M - 2 * w - 12, p.y - 70, w, clamp(MIXED_RPS / (CALLS_AFTER / SESSION_SEC)),
         'אחרי מיגרציית האצווה', 'הקוד מוכן, ה-SQL מחכה להדבקה', AQUA)
    hero(c, M, p.y - 70, w, '7', 'פערים לפני פרודקשן', 'מתוכם 3 חוסמים', ORANGE)
    p.y -= 92

    p.h2('המסקנה בשורה אחת')
    p.p('צד המשחקים בשל: התקרה היא Supabase, והיא רחוקה. צד הטיוטור לא נמדד מעולם תחת עומס אמיתי,')
    p.p('ושלושה דברים חוסמים יציאה לאוויר — כולם תיקונים של דקות, אף אחד מהם לא דורש כתיבת קוד.')

    p.h2('התקרה של מסד הנתונים, כפי שנמדדה')
    p.note('wrk, 2 threads. המחולל היה מתחת ל-50% CPU בכל אחת מהנקודות, ולכן אלה המספרים של השירות ולא של המחשב.')
    p.y -= 10
    bars(c, M + 40, p.y - 128, W - 2 * M - 80, 118,
         [(he(n), v, col) for n, v, col in CEILINGS], 1200,
         'סוג הקריאה', 'בקשות לשנייה')
    p.y -= 158
    p.note('מעבר לנקודות האלה התפוקה מפסיקה לעלות וההשהיה מוכפלת — זו ההגדרה של שרת רווי.')
    p.note('ההשהיה עצמה היא 100 מילישניות בין אם השרת בטל ובין אם הוא ב-600 בקשות לשנייה: זה זמן')
    p.note('ההלוך-חזור לאזור, לא עבודה. אין יותר מה לכוונן בשאילתות.')

    p.y -= 18
    p.h2('שלושת החוסמים')
    cw = (W - 2 * M - 24) / 3
    for i, (t, sub) in enumerate([
        ('הדבקת שתי מיגרציות', 'בלעדיהן: מנוי חינם לכל דורש'),
        ('deploy לשני ה-backends', 'כל התיקונים מחכים בריפו'),
        ('מפתח LemonSqueezy', 'אי אפשר לאמת תשלום'),
    ]):
        x = W - M - cw - i * (cw + 12)
        box(c, x, p.y - 46, cw, 46, HexColor('#fdf3f2'), BAD)
        c.setFillColor(INK); c.setFont('SB', 9)
        c.drawRightString(x + cw - 12, p.y - 20, he(t))
        c.setFillColor(MUTED); c.setFont('S', 7.5)
        c.drawRightString(x + cw - 12, p.y - 34, he(sub))
    p.y -= 58
    p.note('אף אחד מהם אינו כתיבת קוד. כולם בעמוד 4.')
    c.showPage()


def page2(c):
    p = Page(c, 'כמה משתמשים בכל איזור', 'מה כל אזור נוגע בו, ומה מגביל אותו', 2)

    p.p('משחק לא נוגע בשרתים שלנו בכלל: הדפים יושבים ב-Cloudflare והמשחק מדבר ישירות מול Supabase.')
    p.p('הטיוטור הוא ההפך — כל בקשה עוברת דרך Render ומחכה למודל.')
    p.y -= 6

    rows = [
        [('משחקים', INK), 'Cloudflare + Supabase', 'Supabase', (clamp(MIXED_RPS / (CALLS_NOW / SESSION_SEC)), BLUE), 'נמדד'],
        [('משחקים, אחרי האצווה', INK), 'Cloudflare + Supabase', 'Supabase', (clamp(MIXED_RPS / (CALLS_AFTER / SESSION_SEC)), AQUA), 'נגזר'],
        [('דפים סטטיים', INK), 'Cloudflare בלבד', 'אין מעשית', ('ללא הגבלה', MUTED), '—'],
        [('צ׳אט הטיוטור', INK), 'Render → OpenAI', 'המודל', ('לא נמדד', WARN), 'חסר'],
        [('יצירת שיעור', INK), 'Render → OpenAI/Gemini', 'תהליך הרקע', ('שביר', BAD), 'ראה להלן'],
        [('הרשמה והתחברות', INK), 'Supabase Auth', 'לא נמדד', ('לא נמדד', WARN), 'חסר'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['איזור', 'במה נוגע', 'מה מגביל', 'בו-זמנית', 'מקור'],
              rows, [0.24, 0.24, 0.18, 0.20, 0.14])
    p.y = y - 20

    p.h2('למה המשחקים מחזיקים כל כך הרבה')
    p.p(f'סשן של עשר שאלות עולה {CALLS_NOW} קריאות היום. פרוס על ארבע דקות זה 0.06 קריאות לשנייה לילד,')
    p.p(f'ו-{MIXED_RPS} קריאות לשנייה מתחלקות ל-{clamp(MIXED_RPS / (CALLS_NOW / SESSION_SEC))} ילדים.')
    p.y -= 4
    p.p(f'עם תיבת היוצא — התשובות נאספות בדפדפן ונשלחות יחד — אותו סשן עולה {CALLS_AFTER} קריאות,')
    p.p(f'וזה {clamp(MIXED_RPS / (CALLS_AFTER / SESSION_SEC))} ילדים על אותו מסד נתונים בדיוק. הקוד כבר עשה את זה; ה-SQL מחכה להדבקה.')

    p.y -= 6
    p.h2('אותו דבר, בתמונה')
    p.note('כמה משתמשים בו-זמנית בכל איזור. הטיוטור ריק כי הוא לא נמדד, לא כי הוא אפס.')
    p.y -= 8
    bars(c, M + 46, p.y - 108, W - 2 * M - 92, 98, [
        (he('משחקים היום'), 10300, BLUE),
        (he('אחרי האצווה'), 36000, AQUA),
        (he('טיוטור'), 0, MUTED),
    ], 40000, 'איזור', 'משתמשים בו-זמנית')
    p.y -= 140

    p.h2('ומה לא ידוע על הטיוטור')
    p.p('עד היום כל בקשה החזיקה thread של עובד לאורך כל קריאת המודל — שניות — ומאגר ה-threads')
    p.p('היה 40. זו הייתה התקרה: כ-40 שיחות במקביל, וכל אחת מעבר לזה חיכתה בתור.')
    p.p('היום 12 הפונקציות שמחכות למודל הן async, והבקשה משחררת את ה-thread בזמן שהמודל חושב.')
    p.p('התקרה עברה למגבלת הקצב של ספק המודל — אבל היא לא נמדדה, כי כל מדידה כזו עולה כסף אמיתי.')
    p.note('כדי למדוד: לקבוע תקרת הוצאה, להריץ ramp קצר מול חשבון בדיקה, ולקרוא את מגבלות הקצב בתשובה.')
    c.showPage()


def page3(c):
    p = Page(c, 'מה תוקן היום', 'ממצאי האבטחה שנסגרו ב-10 בספטמבר', 3)

    p.p('האודיט הראשון היה ב-9 בספטמבר. כל ממצא נבדק מחדש מול המערכת החיה, והפעם גם עם חשבון')
    p.p('זמני — כדי לענות על מה שהאודיט הראשון לא יכול היה: מה משתמש מחובר זר מצליח להגיע אליו.')
    p.y -= 6

    rows = [
        [('מנוי בתשלום מהדפדפן', INK), 'חשבון חינמי הכניס plan=annual עד 2099 — התקבל', ('נסגר', GOOD)],
        [('בנק השאלות', INK), '106,096 שורות עם התשובות, קריאות לכל מבקר', ('נסגר', GOOD)],
        [('kid_unit_lesson_progress', INK), 'בלי RLS בכלל: קריאה וכתיבה אנונימית', ('נסגר', GOOD)],
        [('מפתחות תשובות למבחנים', INK), '14 מפתחות, קריאים אנונימית', ('נסגר', GOOD)],
        [('תוכן שיעורים', INK), '150 שורות שנוצרו במודל, לכל אחד באינטרנט', ('נסגר', GOOD)],
        [('מכסת ההודעות', INK), 'LIMIT=20 גם למשלמים, ומרוץ בין בקשות', ('נסגר', GOOD)],
        [('Swagger פתוח', INK), 'כל נתיב וכל סכמה, לכל אחד', ('בקוד', WARN)],
        [('CORS מ-localhost', INK), 'בפרודקשן, עם credentials', ('בקוד', WARN)],
        [('תוכן ילדים בלוגים', INK), 'הטקסט המלא של הילד, פעמיים, ל-Render', ('נסגר', GOOD)],
        [('postMessage בלי origin', INK), 'כל חלון יכול היה לזייף סיום משחק', ('נסגר', GOOD)],
        [('מעקב בדפי ילדים', INK), 'Google Analytics בשני דפים של ילדים', ('נסגר', GOOD)],
        [('כותרות אבטחה', INK), 'אין CSP, אין HSTS, אין X-Frame-Options', ('חלקי', WARN)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['הממצא', 'מה היה', 'מצב'], rows, [0.30, 0.52, 0.18])
    p.y = y - 18

    p.note('"נסגר" = תוקן ונבדק.  "בקוד" = התיקון בריפו, נכנס לתוקף ב-deploy הבא.  "חלקי" = חי במראה,')
    p.note('ממתין להגדרה ב-Cloudflare עבור iakids.app.')

    p.h2('ומה שנמצא תקין')
    p.p('הבידוד בין משפחות מחזיק, וזה החלק שהכי חשוב. זר מחובר שביקש פרופילי ילדים, שיחות, סשנים,')
    p.p('שימוש, פניות תמיכה ורשימת מנהלים — קיבל אפס שורות מכולן.')
    p.p('בנוסף: בדיקת בעלות על ילד בכל 17 נתיבי הטיוטור, אימות token מול Supabase בכל בקשה,')
    p.p('העלאות שיעורי בית מוגבלות לתיקייה של המשתמש ב-bucket לא ציבורי, חתימת HMAC על ה-webhook,')
    p.p('צ׳אט מרונדר דרך textContent, ואין eval או SQL גולמי בשום מקום.')
    c.showPage()


def page4(c):
    p = Page(c, 'הפערים שנשארו', 'מה עומד בין המערכת לבין פרודקשן', 4)

    p.p('שבעה פערים. שלושה חוסמים, וכולם — כולל החוסמים — הם פעולה של דקות, לא כתיבת קוד.')
    p.y -= 8

    rows = [
        [('1', BAD), ('הדבקת שתי מיגרציות', INK), 'RLS על חמש טבלאות, ומכסת ההודעות', 'SQL editor', ('חוסם', BAD)],
        [('2', BAD), ('deploy לשני ה-backends', INK), 'Swagger, CORS, async, מכסה — הכל מחכה', 'Render', ('חוסם', BAD)],
        [('3', BAD), ('מפתח LemonSqueezy', INK), 'ריק. אי אפשר לאמת webhook או לקרוא תשלום', 'backend/.env', ('חוסם', BAD)],
        [('4', WARN), ('כותרות ב-Cloudflare', INK), 'CSP ו-HSTS מול iakids.app', 'Transform Rules', ('גבוה', WARN)],
        [('5', WARN), ('תור לעבודה הכבדה', INK), 'אודיו ותמונות מתים ב-deploy', 'קוד', ('גבוה', WARN)],
        [('6', WARN), ('אין ניטור שגיאות', INK), 'שום דבר לא מדווח כשמשהו נשבר', 'קוד', ('בינוני', WARN)],
        [('7', MUTED), ('אין בדיקות למשחקים', INK), '100 משחקים, אפס בדיקות אוטומטיות', 'קוד', ('בינוני', MUTED)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['#', 'מה', 'למה זה משנה', 'איפה', 'דחיפות'],
              rows, [0.05, 0.24, 0.40, 0.17, 0.14])
    p.y = y - 22

    p.h2('שלושת החוסמים, בפירוט')
    step(p, 1, 'עד שהמיגרציות לא מודבקות: כל בעל חשבון Google נותן לעצמו מנוי לכל החיים', BAD)
    step(p, ' ', 'בקריאה אחת, מפתחות התשובות למבחנים גלויים, והמכסה חוסמת דווקא משלמים', BAD)
    step(p, 2, 'הקוד שסוגר את Swagger, מוציא את localhost מ-CORS, מפסיק להדפיס דברי ילדים', BAD)
    step(p, ' ', 'ללוגים והופך את הטיוטור ל-async — כולו בריפו, אף שורה ממנו לא באוויר', BAD)
    step(p, 3, 'שני מפתחות LemonSqueezy ריקים, ולשני המנויים אין lemon_order_id: אין דרך', BAD)
    step(p, ' ', 'לאמת שתשלום קרה, ואין דרך לדעת מאיזו מדינה הלקוח', BAD)

    p.y -= 12
    y2 = checklist(c, M, p.y, W - 2 * M, [
        (True,  'RLS על חמש הטבלאות — נכתב ונבדק מול Postgres 16'),
        (True,  'מכסת הודעות אטומית לפי תוכנית — נכתבה ונבדקה'),
        (True,  'תיבת יוצא לתשובות, קריאה אחת במקום עשר'),
        (True,  'זהות אחת לאתר ולמשחקים'),
        (True,  'כותרות אבטחה ו-CSP — חיים במראה'),
        (False, 'הדבקת 20260910_rls_findings.sql ו-20260910_chat_quota.sql'),
        (False, 'הדבקת 20260910_game_bank_batch.sql ו-20260910_user_locations.sql'),
        (False, 'deploy ל-iakids-backend ול-iakids-ai-tutor-he'),
        (False, 'APP_ENV=prod בשני השירותים ב-Render'),
        (False, 'LEMON_API_KEY ו-LEMON_WEBHOOK_SECRET'),
        (False, 'CSP ו-HSTS מול iakids.app ב-Cloudflare'),
        (False, 'בדיקה חוזרת: tools/security_check.py מחזיר אפס'),
    ], 'רשימת יציאה לאוויר')
    p.y = y2 - 18

    p.h2('מה שלא נמדד, ולכן לא נטען')
    p.p('כמה שיחות טיוטור במקביל · כמה הרשמות בדקה · עומס אמיתי ממספר מכונות ·')
    p.p('האם הגיבויים של Supabase ניתנים לשחזור · כמה עולה חודש בעומס מלא.')
    c.showPage()


def page5(c):
    p = Page(c, 'איפה התקרה יושבת', 'התמונה אחרי כל התיקונים', 5)
    c.setFont('S', 9)

    cw, ch = 132, 62
    top = p.y - 40
    node(c, W / 2 - cw / 2, top, cw, ch, 'הדפדפן של הילד',
         ['משחק · טיוטור · workspace'], BLUE)

    mid = top - 96
    node(c, W - M - cw - 10, mid, cw, ch, 'Cloudflare',
         ['דפים, CSS, JS', 'ללא הגבלה מעשית'], AQUA, HexColor('#f2fbf7'))
    node(c, W / 2 - cw / 2, mid, cw, ch, 'Supabase',
         ['550–1,050 בקשות/ש׳', 'כאן התקרה'], ORANGE, HexColor('#fef5f0'))
    node(c, M + 10, mid, cw, ch, 'Render',
         ['FastAPI, async', 'מחכה למודל'], BLUE)

    bot = mid - 88
    node(c, M + 10, bot, cw, ch, 'OpenAI · Gemini',
         ['מגבלת קצב', 'לא נמדד'], MUTED, PANEL)
    node(c, W / 2 - cw / 2, bot, cw, ch, 'Postgres',
         ['אינדקס חלקי', '99 מילישניות'], MUTED, PANEL)

    arrow(c, W / 2 + 30, top, W - M - cw / 2 - 10, mid + ch, AQUA)
    arrow(c, W / 2, top, W / 2, mid + ch, ORANGE, 'רוב התנועה')
    arrow(c, W / 2 - 30, top, M + cw / 2 + 10, mid + ch, BLUE)
    arrow(c, M + cw / 2 + 10, mid, M + cw / 2 + 10, bot + ch, MUTED)
    arrow(c, W / 2, mid, W / 2, bot + ch, MUTED)

    p.y = bot - 34
    p.h2('מה זה אומר')
    p.p('רוב התנועה של האתר — כל מה שילד עושה במשחק — לא עוברת בשרת שלנו בכלל. היא נוגעת ב-Cloudflare,')
    p.p('שאי אפשר להעמיס אותו, וב-Supabase, שנמדד ורחוק מלהיות מוצף.')
    p.p('Render נמצא במסלול של הטיוטור בלבד, והוא כבר לא מוגבל ב-threads אלא במודל עצמו.')
    p.y -= 6
    p.h2('הצעד הבא לתפוסה, לפי הסדר')
    step(p, 1, 'להדביק את מיגרציית האצווה — פי שלושה וחצי ילדים, בלי לשלם על דבר', AQUA)
    step(p, 2, 'לשדרג את ה-compute ב-Supabase, ולמדוד שוב את שלושת המספרים מעמוד 1', BLUE)
    step(p, 3, 'להעמיס ממספר מכונות — התקרה הנוכחית נמצאה ממכונה אחת, ולכן היא רצפה', BLUE)
    step(p, 4, 'read replicas, רק אחרי שהקריאות יהיו באמת החצי הגדול', MUTED)
    p.y -= 10
    p.note('מקורות: tools/CAPACITY.md · tools/PERFORMANCE.md · SECURITY.md · TODO.md')
    c.showPage()


def main():
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle('iakids — production readiness')
    for fn in (page1, page2, page3, page4, page5):
        fn(c)
    c.save()
    print(OUT, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()
