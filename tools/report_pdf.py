#!/usr/bin/env python3
"""The whole picture, as a PDF: architecture, capacity, gaps, bugs, and what to do next.

    backend/.venv/bin/python tools/report_pdf.py [out.pdf]

Drawn with the helpers from tools/capacity_pdf.py so the reports stay one design. This
one supersedes the earlier readiness report: it answers the same question and four
more.

Nothing here is decided in this file. The numbers come from tools/CAPACITY.md and
tools/PERFORMANCE.md, the findings from SECURITY.md, the bugs and the plan from
TODO.md. Change those first, then redraw.
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

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'iakids-report.pdf')
DATE = '10 בספטמבר 2026'

# ------------------------------------------------------------------ measured, 2026-09-10
# wrk, two threads. The generator sat under 50% CPU at every one of these, so they are
# the service's limits and not the laptop's.
CEILINGS = [('קריאה פשוטה', 1050, AQUA), ('שליפת 20 שאלות', 550, BLUE), ('רישום תשובה', 700, ORANGE)]
MIXED_RPS = 600            # the conservative middle of the three
CALLS_BEFORE = 14          # per ten-question session, before the outbox
CALLS_NOW = 4              # after it — live since the batch migration landed
SESSION_SEC = 240          # a four-minute round
FAST_SESSION_SEC = 100     # a child racing through one


def kids(calls, seconds=SESSION_SEC):
    return int(round(MIXED_RPS / (calls / seconds) / 100.0) * 100)


def fmt(n):
    return f'{n:,}'


def step(p, n, text, color=BLUE, size=9.5, lead=14):
    """One numbered line. The number is drawn on its own: inside a bidi-reordered
    Hebrew line a leading "1." ends up at the wrong end of the sentence."""
    c = p.c
    if str(n).strip():                       # a blank number continues the item above
        c.setFillColor(color); c.circle(W - M - 5, p.y + 3, 7.5, fill=1, stroke=0)
        c.setFillColor(HexColor('#ffffff')); c.setFont('SB', 7.5)
        c.drawCentredString(W - M - 5, p.y + 0.8, str(n))
    c.setFillColor(INK2); c.setFont('S', size)
    c.drawRightString(W - M - 18, p.y, he(text))
    p.y -= lead


def checklist(c, x, y, w, items, title):
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


def bullet(p, text, color=MUTED, size=9):
    c = p.c
    c.setFillColor(color); c.circle(W - M - 4, p.y + 3, 2.2, fill=1, stroke=0)
    c.setFillColor(INK2); c.setFont('S', size)
    c.drawRightString(W - M - 14, p.y, he(text))
    p.y -= 13


# ============================================================================ 1
def page_summary(c):
    p = Page(c, 'iakids — תמונת מצב', f'{DATE} · ארכיטקטורה, תפוסה, פערים, באגים ותוכנית', 1)

    p.p('כל מספר בדוח הזה נמדד מול המערכת החיה. מה שלא נמדד — כתוב במפורש שלא נמדד.')
    p.y -= 10

    w = (W - 2 * M - 24) / 3
    hero(c, W - M - w, p.y - 70, w, fmt(kids(CALLS_NOW)),
         'ילדים משחקים בו-זמנית', 'רצפה. התקרה היא Supabase', BLUE)
    hero(c, W - M - 2 * w - 12, p.y - 70, w, '0',
         'טבלאות פתוחות לאינטרנט', 'היו חמש הבוקר', AQUA)
    hero(c, M, p.y - 70, w, '2', 'פערים חוסמים', 'שניהם לחיצת כפתור', ORANGE)
    p.y -= 92

    p.h2('איפה זה עומד')
    p.p('צד המשחקים — שהוא רוב התנועה — בשל ונמדד. מסד הנתונים נקי: כל חמש הטבלאות שהיו')
    p.p('פתוחות לכל אדם באינטרנט סגורות, וחור המנויים שאיפשר לכל בעל חשבון Google לתת לעצמו')
    p.p('מנוי בתשלום — סגור ומאומת. צד הטיוטור תוקן בקוד אבל טרם עלה לאוויר.')
    p.y -= 4
    p.p('שני דברים חוסמים יציאה לפרודקשן, ואף אחד מהם אינו כתיבת קוד.')

    p.y -= 8
    cw = (W - 2 * M - 12) / 2
    for i, (t, sub) in enumerate([
        ('deploy לשני ה-backends עם APP_ENV=prod', 'Swagger פתוח · CORS מ-localhost · async · מכסה'),
        ('כותרות אבטחה ב-Cloudflare', 'אין CSP מול iakids.app; במראה זה כבר חי ונקי'),
    ]):
        x = W - M - cw - i * (cw + 12)
        box(c, x, p.y - 48, cw, 48, HexColor('#fdf3f2'), BAD)
        c.setFillColor(INK); c.setFont('SB', 9.5)
        c.drawRightString(x + cw - 12, p.y - 20, he(t))
        c.setFillColor(MUTED); c.setFont('S', 7.5)
        c.drawRightString(x + cw - 12, p.y - 35, he(sub))
    p.y -= 62

    p.h2('מה נסגר היום')
    rows = [
        [('חמש טבלאות פתוחות', INK), 'מפתחות תשובות למבחנים, התקדמות ילדים, תוכן שיעורים', ('נסגר ואומת', GOOD)],
        [('מנוי בתשלום מהדפדפן', INK), 'חשבון חינמי הכניס plan=annual עד 2099 — התקבל', ('נסגר ואומת', GOOD)],
        [('בנק השאלות', INK), '106,096 שאלות עם התשובות, לכל מבקר', ('נסגר ואומת', GOOD)],
        [('מכסת ההודעות', INK), 'LIMIT=20 גם למשלמים, ומרוץ בין בקשות מקבילות', ('נסגר ואומת', GOOD)],
        [('14 קריאות לסשן', INK), 'תשובה אחת = קריאה אחת למסד', ('4 קריאות', GOOD)],
        [('שתי מערכות זהות', INK), 'הורה שהגיע מה-workspace התבקש להתחבר שוב', ('זהות אחת', GOOD)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['מה', 'מה היה', 'מצב'], rows, [0.26, 0.56, 0.18])
    p.y = y - 16
    p.note('"נסגר ואומת" = תוקן, והתיקון נבדק מול המערכת החיה עם חשבון זמני שנמחק אחריו.')
    c.showPage()


# ============================================================================ 2
def page_architecture(c):
    p = Page(c, 'הארכיטקטורה הנוכחית', 'מה כל חלק עושה, ומה מגביל אותו', 2)

    p.p('שני דברים חשוב להבין כאן. הראשון: רוב מה שילד עושה לא נוגע בשרת שלנו בכלל — הדפים')
    p.p('סטטיים ויושבים ב-Cloudflare, והמשחק מדבר ישירות מול Supabase. השני: Render נמצא')
    p.p('רק במסלול הטיוטור, ושם הזמן הולך למודל, לא לקוד שלנו.')
    p.y -= 12

    cw, ch = 138, 60
    top = p.y - 6
    node(c, W / 2 - cw / 2, top - ch, cw, ch, 'הדפדפן של הילד',
         ['משחקים · טיוטור · workspace', 'session ב-localStorage'], BLUE)

    mid = top - ch - 84
    node(c, W - M - cw, mid, cw, ch, 'Cloudflare → Pages',
         ['HTML, CSS, JS, תמונות', 'ללא הגבלה מעשית'], AQUA, HexColor('#f2fbf7'))
    node(c, W / 2 - cw / 2, mid, cw, ch, 'Supabase',
         ['Postgres + PostgREST', '550–1,050 בקשות/ש׳'], ORANGE, HexColor('#fef5f0'))
    node(c, M, mid, cw, ch, 'Render × 2',
         ['FastAPI, async', 'ליבה + טיוטור עברי'], BLUE)

    bot = mid - 78
    node(c, M, bot, cw, ch, 'OpenAI · Gemini',
         ['צ׳אט, TTS, תמונות', 'מגבלת קצב — לא נמדד'], MUTED, PANEL)
    node(c, W / 2 - cw / 2, bot, cw, ch, 'RLS + פונקציות',
         ['כל טבלה מסוננת לפי', 'auth.uid() של ההורה'], MUTED, PANEL)
    node(c, W - M - cw, bot, cw, ch, 'nginx (המראה)',
         ['smarts-brains.online', 'gzip, cache, CSP'], MUTED, PANEL)

    arrow(c, W / 2 + 36, top - ch, W - M - cw / 2, mid + ch, AQUA)
    arrow(c, W / 2, top - ch, W / 2, mid + ch, ORANGE, 'רוב התנועה')
    arrow(c, W / 2 - 36, top - ch, M + cw / 2, mid + ch, BLUE)
    arrow(c, M + cw / 2, mid, M + cw / 2, bot + ch, MUTED)
    arrow(c, W / 2, mid, W / 2, bot + ch, MUTED)

    p.y = bot - 30
    rows = [
        [('Cloudflare + Pages', INK), 'כל הדפים, ה-CSS וה-JS', 'אין מעשית', ('—', MUTED)],
        [('Supabase', INK), 'המסד, ה-RLS, האימות, האחסון', 'CPU של המסד', ('נמדד', GOOD)],
        [('Render — ליבה', INK), 'צ׳אט ספרדי, webhook של תשלומים', '96 חוטים, 30/דקה', ('לא נמדד', WARN)],
        [('Render — טיוטור', INK), '19 נתיבים, שיעורים, TTS, שיעורי בית', 'המודל', ('לא נמדד', WARN)],
        [('nginx (המראה)', INK), 'עותק של האתר, לא מאחורי Cloudflare', 'המכונה הזו, 2 ליבות', ('נמדד', GOOD)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['רכיב', 'מה הוא מריץ', 'מה מגביל אותו', 'מדידה'],
              rows, [0.22, 0.40, 0.24, 0.14])
    p.y = y - 16
    p.note('המראה smarts-brains.online היא nginx על שרת האפליקציה, לא Cloudflare — ולכן דחיסה,')
    p.note('קאשינג, כותרות אבטחה ומגבלת קצב מוגדרים שם בנפרד. הם הוגדרו ונבדקו.')
    c.showPage()


# ============================================================================ 3
def page_capacity(c):
    p = Page(c, 'כמה משתמשים המערכת מחזיקה', 'נמדד ב-wrk, המחולל מתחת ל-50% CPU', 3)

    p.p('הבדיקות הקודמות מדדו את מכונת הבדיקה ולא את השירות. עם כלי זול בהרבה לכל בקשה,')
    p.p('המחולל יושב מתחת לחצי עומס בזמן שהמספרים מטפסים — ואלה המספרים של Supabase עצמה.')
    p.y -= 8
    bars(c, M + 44, p.y - 118, W - 2 * M - 88, 108,
         [(he(n), v, col) for n, v, col in CEILINGS], 1200, 'סוג הקריאה', 'בקשות לשנייה')
    p.y -= 162
    p.note('מעבר לנקודות האלה התפוקה מפסיקה לעלות וההשהיה מוכפלת — שרת רווי. ההשהיה עצמה')
    p.note('היא 100 מילישניות בין אם השרת בטל ובין אם הוא ב-600 בקשות לשנייה: זה זמן ההלוך-חזור')
    p.note('לאזור, לא עבודה. השאילתה של בנק השאלות עולה כמו קריאת שורה בודדת. אין שם מה לכוונן.')

    p.y -= 14
    p.h2('מכאן למספר ילדים')
    rows = [
        [('משחקים', INK), f'{CALLS_NOW} קריאות לסשן', 'Supabase', (fmt(kids(CALLS_NOW)), AQUA), 'נמדד'],
        [('משחקים — סשן מהיר', INK), f'{CALLS_NOW} קריאות ב-100 שנ׳', 'Supabase', (fmt(kids(CALLS_NOW, FAST_SESSION_SEC)), BLUE), 'נגזר'],
        [('לפני תיבת היוצא', INK), f'{CALLS_BEFORE} קריאות לסשן', 'Supabase', (fmt(kids(CALLS_BEFORE)), MUTED), 'היסטורי'],
        [('דפים סטטיים', INK), 'Cloudflare בלבד', 'אין מעשית', ('ללא הגבלה', MUTED), '—'],
        [('צ׳אט הטיוטור', INK), 'Render → OpenAI', 'המודל', ('לא נמדד', WARN), 'חסר'],
        [('יצירת שיעור', INK), 'רקע בתוך תהליך הבקשה', 'מת ב-deploy', ('שביר', BAD), 'ידוע'],
        [('הרשמה והתחברות', INK), 'Supabase Auth', 'לא נמדד', ('לא נמדד', WARN), 'חסר'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['איזור', 'מה זה עולה', 'מה מגביל', 'בו-זמנית', 'מקור'],
              rows, [0.24, 0.24, 0.16, 0.22, 0.14])
    p.y = y - 18

    p.p(f'סשן של עשר שאלות עולה היום {CALLS_NOW} קריאות — היה {CALLS_BEFORE} לפני שהתשובות נאספות בדפדפן')
    p.p(f'ונשלחות יחד. פרוס על ארבע דקות זה 0.017 קריאות לשנייה לילד, ו-{MIXED_RPS} קריאות לשנייה')
    p.p(f'מתחלקות ל-{fmt(kids(CALLS_NOW))} ילדים. ילד שרץ מהר יותר עולה יותר: {fmt(kids(CALLS_NOW, FAST_SESSION_SEC))} במקרה הצפוף.')
    p.y -= 4
    p.note('שני המספרים הם רצפה: הם נמדדו ממכונה אחת. התקרה האמיתית גבוהה יותר בדיוק כמו')
    p.note('שמחולל גדול יותר היה מוצא.')
    c.showPage()


# ============================================================================ 4
def page_gaps(c):
    p = Page(c, 'פערים לסגירה', 'מה עומד בין המערכת לבין פרודקשן', 4)

    rows = [
        [('1', BAD), ('deploy לשני ה-backends', INK), 'כל התיקונים בריפו, אף אחד לא באוויר', 'Render', ('חוסם', BAD)],
        [('2', BAD), ('כותרות אבטחה', INK), 'אין CSP מול iakids.app', 'Cloudflare', ('חוסם', BAD)],
        [('3', WARN), ('מפתחות LemonSqueezy', INK), 'ריקים גם ב-env.prod — אין אימות webhook', 'env.prod', ('גבוה', WARN)],
        [('4', WARN), ('מכסה לפני קריאת מודל', INK), 'לצ׳אט יש; ל-TTS ולתמונות אין', 'קוד', ('גבוה', WARN)],
        [('5', WARN), ('תור לעבודה הכבדה', INK), 'אודיו ותמונות מתים בכל deploy', 'קוד', ('גבוה', WARN)],
        [('6', WARN), ('אין ניטור שגיאות', INK), 'שום דבר לא מדווח כשמשהו נשבר', 'קוד', ('בינוני', WARN)],
        [('7', MUTED), ('PKCE', INK), 'token עובר ב-fragment של ה-URL', '63 דפים', ('בינוני', MUTED)],
        [('8', MUTED), ('אין בדיקות למשחקים', INK), '100 משחקים, אפס בדיקות אוטומטיות', 'קוד', ('בינוני', MUTED)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['#', 'מה', 'למה זה משנה', 'איפה', 'דחיפות'],
              rows, [0.05, 0.24, 0.40, 0.17, 0.14])
    p.y = y - 20

    p.h2('שני החוסמים, בפירוט')
    step(p, 1, 'ה-deploy נושא: סגירת Swagger, הוצאת localhost מ-CORS, הפסקת הדפסת דברי ילדים', BAD)
    step(p, ' ', 'ללוגים, הטיוטור ב-async, מכסת ההודעות החדשה, ונתיב בריאות לטיוטור. חייב', BAD)
    step(p, ' ', 'APP_ENV=prod — בלעדיו Swagger נשאר פתוח גם אחרי ה-deploy. ובדיקת הבריאות', BAD)
    step(p, ' ', 'של Render צריכה להצביע על / בשני השירותים.', BAD)
    p.y -= 4
    step(p, 2, 'ה-session של Supabase יושב ב-localStorage ב-63 דפים, כך שכל XSS הוא השתלטות', BAD)
    step(p, ' ', 'מלאה על החשבון. GitHub Pages לא יכול לשלוח כותרות; Cloudflare כן. הנוסח המדויק', BAD)
    step(p, ' ', 'כבר חי ונבדק במראה — 0 סירובים ב-8 דפים, אחרי שתי תקלות שהבדיקה תפסה.', BAD)

    p.y -= 8
    y2 = checklist(c, M, p.y, W - 2 * M, [
        (True,  'RLS על חמש הטבלאות — הודבק ואומת מול המערכת החיה'),
        (True,  'מכסת הודעות אטומית לפי תוכנית — הודבקה ואומתה'),
        (True,  'תיבת יוצא לתשובות — קריאה אחת במקום עשר'),
        (True,  'מדינה ואזור זמן לכל חשבון'),
        (True,  'כותרות אבטחה ו-CSP — חיים ונקיים במראה'),
        (True,  'נתיב בריאות לטיוטור — נמצא בהרצה מקומית לפני ה-deploy'),
        (False, 'deploy ל-iakids-backend ול-iakids-ai-tutor-he'),
        (False, 'APP_ENV=prod בשני השירותים, ו-health check על /'),
        (False, 'CSP ו-HSTS מול iakids.app ב-Cloudflare'),
        (False, 'מגבלת קצב על games/* ב-Cloudflare'),
        (False, 'LEMON_API_KEY ו-LEMON_WEBHOOK_SECRET'),
        (False, 'בדיקה חוזרת: tools/security_check.py מחזיר אפס'),
    ], 'רשימת יציאה לאוויר')
    p.y = y2 - 16
    p.note('כל שורה מסומנת נבדקה מול המערכת החיה או בהרצה מקומית, לא רק נכתבה.')
    c.showPage()


# ============================================================================ 5
def page_bugs(c):
    p = Page(c, 'באגים', 'מה שבור עכשיו, ומה נסגר היום', 5)

    p.h2('פתוחים')
    rows = [
        [('lemon_order_id ריק', INK), 'לשני המנויים בתשלום אין הזמנה — המסד לא מסכים עם LemonSqueezy', ('גבוה', BAD)],
        [('הדשבורד האנגלי מת', INK), 'מפתח ה-anon בקובץ קטוע. הדף מעולם לא עבד', ('בינוני', WARN)],
        [('mode ו-device_type ריקים', INK), 'בכל 113 שורות tutor_sessions — אף אחד לא ממלא אותן', ('בינוני', WARN)],
        [('game_wins לא קיימת', INK), 'IAKidsCloud כותב לטבלה שאין ובולע את השגיאה', ('בינוני', WARN)],
        [('6 קריאות רצופות', INK), 'get_or_generate_unit_lesson מחכה לכל אחת, והן בלתי תלויות', ('בינוני', WARN)],
        [('וידאו חסר בדף הבית', INK), 'iakids-demo.mp4 מחזיר 404; התיקייה assets/videos ריקה', ('נמוך', MUTED)],
        [('parent-dashboard/index.com', INK), 'סיומת שגויה — שום דבר לא מגיש את הקובץ', ('נמוך', MUTED)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['הבאג', 'מה קורה', 'חומרה'], rows, [0.28, 0.54, 0.18])
    p.y = y - 20

    p.h2('נסגרו היום')
    for t in [
        'game_record_answers נפלה בכל קריאה — משתנה הלולאה וכינוי תת-שאילתה נקראו שניהם a',
        'לטיוטור לא היה נתיב שמחזיר 200 בלי token — Render היה מאתחל אותו בלולאה',
        'Font Awesome נחסם ב-CSP: כל אייקון ב-workspace ובפאנל ההורים היה ריבוע ריק',
        'כפתור הבית במשחק הציג להורה מחובר מסך התחברות',
        'המשחקים הריצו זהות שנייה (Firebase) לצד ה-Supabase של האתר',
        'המראה הגישה JS ו-CSS בלי דחיסה — 96KB ל-game-sdk.js — ובלי קאשינג',
        'דוק הכפתורים ב-workspace שמר שש עמודות אחרי שהוסתרו שניים',
        'שם המשתמש וטבלאות האלופים היו לבן-על-לבן בערכה הכהה',
    ]:
        bullet(p, t, GOOD)
    p.y -= 6
    p.note('כולם אומתו: הרצה מקומית, דפדפן אמיתי, או בדיקה מול המערכת החיה.')
    c.showPage()


# ============================================================================ 6
def page_plan(c):
    p = Page(c, 'תוכנית שיפור', 'לפי הסדר, עם מה שכל צעד נותן', 6)

    p.p('הסדר כאן הוא לפי יחס תועלת-למאמץ, לא לפי גודל. שלושת הראשונים הם דקות.')
    p.y -= 6

    rows = [
        [('1', BAD), ('deploy + APP_ENV=prod', INK), 'סוגר 6 מ-12 ממצאי האבטחה, ומשחרר את ה-async', 'דקות', ('מיידי', GOOD)],
        [('2', BAD), ('CSP ב-Cloudflare', INK), 'סוגר את 6 הנותרים; XSS מפסיק להיות השתלטות', 'דקות', ('מיידי', GOOD)],
        [('3', WARN), ('שדרוג compute ב-Supabase', INK), 'התקרה היא CPU של המסד; כל צעד מכפיל', 'דקות', ('פי 2', AQUA)],
        [('4', WARN), ('מכסה יומית לפני TTS ותמונות', INK), 'היום חשבון גנוב יכול לשרוף תקציב מודל', 'שעות', ('הגנה', BLUE)],
        [('5', WARN), ('תור לעבודה הכבדה', INK), 'אודיו ותמונות שורדים deploy, ולא גוזלים CPU מבקשות', 'יום', ('יציבות', BLUE)],
        [('6', MUTED), ('ניטור שגיאות', INK), 'לדעת שמשהו נשבר לפני שילד מספר', 'שעות', ('ראות', BLUE)],
        [('7', MUTED), ('אצווה לכתיבות הטיוטור', INK), 'מה שהמשחקים כבר עשו: 14 קריאות לארבע', 'יום', ('פי 3', AQUA)],
        [('8', MUTED), ('מדידה ממספר מכונות', INK), 'התקרה הנוכחית נמצאה ממכונה אחת', 'שעות', ('ידע', MUTED)],
        [('9', MUTED), ('read replicas', INK), 'רק אחרי שהקריאות יהיו החצי הגדול', 'יום', ('מאוחר', MUTED)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['#', 'מה', 'מה זה נותן', 'מאמץ', 'סוג'],
              rows, [0.05, 0.26, 0.42, 0.11, 0.16])
    p.y = y - 22

    p.h2('מה שלא כדאי לעשות עדיין')
    bullet(p, 'Redis לצ׳אט עצמו — הילד מחכה לתשובה, ותור לא מחזיר תשובה', BAD)
    bullet(p, 'read replicas לפני שדרוג ה-compute — פותר את הבעיה הלא נכונה', BAD)
    bullet(p, 'PKCE בחצי מהדפים — מעבר חלקי שובר התחברות לכולם', BAD)
    bullet(p, 'עוד אופטימיזציה בשאילתות — הן כבר עולות כמו קריאת שורה בודדת', BAD)

    p.y -= 10
    p.h2('מה שלא נמדד, ולכן לא נטען כאן')
    p.p('כמה שיחות טיוטור במקביל · כמה הרשמות בדקה · עומס אמיתי ממספר מכונות ·')
    p.p('האם הגיבויים של Supabase ניתנים לשחזור · כמה עולה חודש בעומס מלא.')
    p.y -= 6
    p.note('מקורות: tools/CAPACITY.md · tools/PERFORMANCE.md · SECURITY.md · TODO.md')
    p.note('כלים לבדיקה חוזרת: tools/security_check.py · tools/csp_check.py · tools/browser_check.js')
    c.showPage()


def main():
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle('iakids — status, capacity and plan')
    for fn in (page_summary, page_architecture, page_capacity, page_gaps, page_bugs, page_plan):
        fn(c)
    c.save()
    print(OUT, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()
