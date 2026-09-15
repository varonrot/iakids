#!/usr/bin/env python3
"""The Hebrew tutor backend, as a PDF: what each API costs, how many children a server
holds, what was measured, what was fixed, what is still open.

    backend/.venv/bin/python tools/tutor_capacity_pdf.py [out.pdf]

Same drawing helpers as the games report (tools/capacity_pdf.py), same design.
Every number comes from the 2026-09-14 runs on this box (2 vCPU / 2 GB, NYC, against
the production Supabase in eu-central). What was not measured is written as such.
Source of the numbers: handoff_perfromance.md and /var/log/iakids/{e2e,load}/.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from capacity_pdf import (
    W, H, M, he, Page, hero, bars, table, box, node, arrow,
    BLUE, ORANGE, AQUA, INK, INK2, MUTED, LINE, PANEL, SURFACE, GOOD, WARN, BAD,
)

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'iakids-tutor-report.pdf')
DATE = '14 בספטמבר 2026'
WHITE = HexColor('#ffffff')


def step(p, n, text, color=BLUE, size=9.5, lead=14):
    c = p.c
    if str(n).strip():
        c.setFillColor(color); c.circle(W - M - 5, p.y + 3, 7.5, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont('SB', 7.5)
        c.drawCentredString(W - M - 5, p.y + 0.8, str(n))
    c.setFillColor(INK2); c.setFont('S', size)
    c.drawRightString(W - M - 18, p.y, he(text))
    p.y -= lead


def bullet(p, text, color=MUTED, size=9, lead=13):
    c = p.c
    c.setFillColor(color); c.circle(W - M - 4, p.y + 3, 2, fill=1, stroke=0)
    c.setFillColor(INK2); c.setFont('S', size)
    c.drawRightString(W - M - 12, p.y, he(text))
    p.y -= lead


def checklist(c, x, y, w, items, title):
    h = 26 + len(items) * 15
    box(c, x, y - h, w, h, WHITE, LINE)
    c.setFillColor(INK); c.setFont('SB', 10)
    c.drawRightString(x + w - 12, y - 18, he(title))
    yy = y - 33
    for done, t in items:
        c.setStrokeColor(GOOD if done else HexColor('#c9ced6')); c.setLineWidth(1.2)
        c.setFillColor(HexColor('#eaf6ef') if done else WHITE)
        c.roundRect(x + w - 24, yy - 3, 10, 10, 2, fill=1, stroke=1)
        if done:
            c.setStrokeColor(GOOD); c.setLineWidth(1.6)
            c.line(x + w - 21.5, yy + 2, x + w - 19.5, yy - 0.5)
            c.line(x + w - 19.5, yy - 0.5, x + w - 16.5, yy + 4.5)
        c.setFillColor(INK2 if done else INK); c.setFont('S', 8.3)
        c.drawRightString(x + w - 32, yy, he(t))
        yy -= 15
    return y - h


# ============================================================================ 1
def page_summary(c):
    p = Page(c, 'הטיוטור העברי — קיבולת', f'{DATE} · מה נמדד, כמה השרת מחזיק, מה תוקן, מה פתוח', 1)
    p.p('כל מספר כאן נמדד היום מול Supabase של הפרודקשן, מהשרת הזה (2 ליבות, 2GB). מה שלא נמדד — כתוב.')
    p.y -= 10

    w = (W - 2 * M - 24) / 3
    hero(c, W - M - w, p.y - 70, w, '~600', 'ילדים משוחחים במקביל, שרת web אחד', 'הערכה מחושבת, לא נמדדה ישירות', BLUE)
    hero(c, W - M - 2 * w - 12, p.y - 70, w, '85', 'בקשות DB בשנייה לליבה', 'נמדד: 12ms CPU לבקשה', AQUA)
    hero(c, M, p.y - 70, w, '$0.06', 'אודיו לשיעור דרך OpenRouter', 'מדויק מהספק · 14-19 קטעי TTS', ORANGE)
    p.y -= 92

    p.h2('התשובה בקצרה')
    p.p('ה-CPU והזיכרון של השרת כמעט לא משתתפים: כל העבודה היא המתנה ל-OpenAI, Gemini ו-Supabase.')
    p.p('אחרי תיקוני היום שרת web יחיד של 512MB מספיק למאות ילדים. מה שקובע את המספר הסופי הוא')
    p.p('מכסות הספקים. מכסת ה-TTS של Gemini נגמרה עם worker אחד; דרך OpenRouter אותו מודל רץ בלי מכסה.')
    p.y -= 4
    p.p('הצינור הכבד — אודיו, תמונות, וידאו — יצא מהשרת לתור עם worker נפרד. עבודה שנופלת חוזרת לבד.')

    p.y -= 8
    cw = (W - 2 * M - 12) / 2
    for i, (t, sub, col) in enumerate([
        ('מכסת Gemini TTS נגמרה → OpenRouter', 'אותו מודל ואותו קול, בלי מכסה. נבדק ב-3 שיעורים', GOOD),
        ('72% מהפולינג נחסם → backoff', 'כל 2-8 שניות, מכבד 429. מחכה לבדיקת דפדפן', WARN),
    ]):
        x = W - M - cw - i * (cw + 12)
        box(c, x, p.y - 48, cw, 48, HexColor('#eaf6ef') if col == GOOD else HexColor('#fff7e6'), col)
        c.setFillColor(INK); c.setFont('SB', 9.5)
        c.drawRightString(x + cw - 12, p.y - 20, he(t))
        c.setFillColor(MUTED); c.setFont('S', 7.5)
        c.drawRightString(x + cw - 12, p.y - 35, he(sub))
    p.y -= 62

    p.h2('מצב האימות')
    cw = (W - 2 * M - 12) / 2
    y1 = checklist(c, W - M - cw, p.y, cw, [
        (True, 'תור עבודות: פתיחה → שורה → worker → אודיו מוכן'),
        (True, 'התאוששות מקריסת worker (עבודה יתומה חזרה)'),
        (True, 'ריטריי אוטומטי אחרי כישלון אודיו'),
        (True, 'עומס: 8 ראוטי DB, 30 במקביל'),
        (True, 'צ׳אט: 5 במקביל, 0 שגיאות'),
        (True, 'קריסה יזומה: SIGKILL באמצע, השלמה בניסיון 2'),
        (True, 'TTS דרך OpenRouter: 3 שיעורים מלאים + 8 בדיקות'),
        (True, 'רגרסיה אופליין: 10 חבילות, הכל עובר'),
    ], 'אומת מול הפרודקשן')
    y2 = checklist(c, M, p.y, cw, [
        (False, 'מיגרציית ai_calls בפרוד (עלות לכל קריאה)'),
        (False, 'פולינג חדש מהדפדפן האמיתי'),
        (False, 'unit-lesson עם ילדים שונים'),
        (False, 'ראוט audio אחרי התיקון (מול הפרוד)'),
        (False, 'Render: שירות worker + משתני סביבה'),
        (False, 'קומיט — רק אחרי כל האמור'),
    ], 'עדיין לא')
    p.y = min(y1, y2) - 14
    p.note('"אומת" = רץ מול Supabase של הפרודקשן דרך הראוטים האמיתיים, עם הילד איתן בחשבון שלך.')
    c.showPage()


# ============================================================================ 2
def page_architecture(c):
    p = Page(c, 'ארכיטקטורה', 'מה השתנה היום: הצינור הכבד יצא מהשרת', 2)
    p.p('לפני: השרת החזיר תשובה והמשיך לייצר וידאו ואודיו באותו תהליך. ריסטארט באמצע איבד הכל בשקט.')
    p.p('אחרי: הראוט רק מכניס שורה לטבלה. תהליך נפרד מריץ, מדווח, ומתאושש.')
    p.y -= 14

    top = p.y
    nw, nh, gap = 104, 62, 31            # four columns: 4*104 + 3*31 = 509 <= W - 2M
    col = [W - M - nw - i * (nw + gap) for i in range(4)]   # x of column i, right to left
    # row 1: browser -> web -> OpenAI
    node(c, col[0], top - nh, nw, nh, 'דפדפן', ['workspace', 'פולינג כל 1.5 ש׳'], BLUE)
    node(c, col[1], top - nh, nw, nh, 'tutor-web', ['FastAPI, async', '125MB · ~0% בהמתנה'], BLUE, PANEL)
    node(c, col[2], top - nh, nw, nh, 'OpenAI', ['שיעור: 70-92 ש׳', 'צ׳אט: 4.5-6 ש׳'], ORANGE)
    arrow(c, col[0], top - nh / 2, col[1] + nw + 2, top - nh / 2, BLUE, 'HTTPS')
    arrow(c, col[1], top - nh / 2, col[2] + nw + 2, top - nh / 2, ORANGE, 'await')

    # row 2: supabase <- web ; queue -> worker -> gemini
    y2 = top - nh - 70
    node(c, col[0], y2 - nh, nw, nh, 'Supabase', ['Postgres · Storage · Auth', 'HTTP/1.1, pool 100'], AQUA)
    node(c, col[1], y2 - nh, nw, nh, 'media_jobs', ['תור עם עדיפות', 'dedupe · heartbeat · reaper'], AQUA, PANEL)
    node(c, col[2], y2 - nh, nw, nh, 'tutor-worker', ['110MB + 90MB לעבודה', 'hero → אודיו ‖ תמונות'], BLUE, PANEL)
    node(c, col[3], y2 - nh, nw, nh, 'Gemini', ['TTS: 6 ש׳ לקטע', 'תמונה: 3.5-5 ש׳'], ORANGE)
    arrow(c, col[1] + nw / 2, top - nh, col[0] + nw / 2 - 20, y2 + 2, AQUA, 'DB, ~150ms')
    arrow(c, col[1] + nw / 2, top - nh, col[1] + nw / 2, y2 + 2, AQUA, 'enqueue')
    arrow(c, col[1], y2 - nh / 2, col[2] + nw + 2, y2 - nh / 2, BLUE, 'claim')
    arrow(c, col[2], y2 - nh / 2, col[3] + nw + 2, y2 - nh / 2, ORANGE, 'TTS / image')
    p.y = y2 - nh - 26

    p.h2('מה נכנס לקוד היום')
    rows = [
        [('תור media_jobs', INK), '5 פונקציות RPC: enqueue עם dedupe, claim אטומי, heartbeat, finish, reaper', ('חדש', GOOD)],
        [('worker.py', INK), 'תהליך נפרד, concurrency לפי env, SIGTERM עדין, מדדים לכל עבודה', ('חדש', GOOD)],
        [('מדדים ב-DB', INK), 'request_log לכל בקשה, service_metrics כל 30 ש׳, views לפי שעה', ('חדש', GOOD)],
        [('event loop', INK), '72 קריאות DB סינכרוניות ב-12 ראוטים async → threadpool', ('תוקן', GOOD)],
        [('לקוח Supabase', INK), 'HTTP/2 יחיד (קרס ב-30 threads) → HTTP/1.1 עם pool', ('תוקן', GOOD)],
        [('signed URLs', INK), 'cache לשעה + חתימת אודיו ב-batch: 40 קריאות לפתיחה → 0-1', ('תוקן', GOOD)],
        [('ייצור כפול', INK), 'נעילה ל-hero, ראוט audio מכניס לתור במקום לייצר בבקשה', ('תוקן', GOOD)],
        [('ריטריי', INK), 'TTS (כולל 429), Storage (ניתוקים בלבד), עבודות: 5 ניסיונות', ('תוקן', GOOD)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['מה', 'פירוט', 'מצב'], rows, [0.2, 0.66, 0.14])
    p.y = y - 12
    p.note('הקוד עובד גם בלי המיגרציות: אם הכנסה לתור נכשלת, העבודה רצה בתוך השרת כמו קודם.')
    c.showPage()


# ============================================================================ 3
def page_apis(c):
    p = Page(c, 'כל API: מה הוא עולה', '30 בקשות במקביל, 60 בקשות לראוט, 10 טוקנים, מגביל קצב מורם · 10:39', 3)
    p.p('ראוט אחרי ראוט. p50 הוא הזמן שהילד מחכה כשעוד 29 מחכים איתו. CPU הוא של תהליך ה-web, 100% = ליבה.')
    p.y -= 6
    rows = [
        [('units (GET)', INK), 'DB', '861ms', '27', '36%', 'רשימת יחידות של שיעור'],
        [('active-lesson-state', INK), 'DB', '512ms', '47', '28%', 'איפה הילד עצר'],
        [('shared-transition', INK), 'DB', '517ms', '81', '17%', 'סרטון מעבר משותף'],
        [('hero-image', INK), 'DB + cache', '1.5s', '18', '35%', 'היה 9s ו-493MB (30 ייצורים)'],
        [('visuals', INK), 'DB + cache', '3.2s', '11', '55%', 'JSON גדול לכל בקשה. היה 6.7s'],
        [('unit-lesson', INK), 'DB + תור', '7.4s', '5', '23%', 'היה 17s. אותו ילד ×30 = תחרות שורות'],
        [('lesson-intro', INK), 'DB + תור', '2.3s', '12', '66%', 'ראוט סינכרוני'],
        [('audio', INK), 'DB + תור', '—', '—', '—', 'תוקן אחרי הריצה: היה מייצר TTS בבקשה'],
        [('chat', INK), 'OpenAI', '4.5-6s', '0.7 ×5', '17%', '5 במקביל, 0 שגיאות. זמן המודל'],
        [('tts', INK), 'Gemini', '—', '—', '—', '5/5 נכשלו: מכסה (429)'],
        [('unit-lesson חדש', INK), 'OpenAI', '70-92s', '—', '2%', 'ייצור שיעור. לא תופס thread'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['ראוט', 'מחכה ל', 'p50', 'req/s', 'CPU', 'הערה'], rows,
              [0.19, 0.11, 0.09, 0.09, 0.08, 0.44], row_h=16)
    p.y = y - 14

    p.h2('מה זה אומר')
    bullet(p, 'ראוט DB עולה כ-12ms CPU. ליבה אחת: ~85 בקשות בשנייה. שתי ליבות: ~170. הזיכרון לא זז.')
    bullet(p, 'ראוטי המודל לא תופסים thread בזמן ההמתנה. התקרה שלהם היא מכסת OpenAI/Gemini, לא השרת.')
    bullet(p, 'ה-p50 של הראוטים הפשוטים הוא בעיקר סיבובי רשת ל-Supabase, ~150ms כל אחד, מהשרת הזה בניו-יורק.')
    bullet(p, 'unit-lesson ו-visuals עדיין כבדים: JSON גדול, וכתיבות progress של אותו ילד שמתחרות על שורה אחת.')
    p.y -= 6
    p.h2('קריאות וכתיבות ל-DB לפעולה (ספירה מהקוד, לא נמדדה)')
    rows = [
        [('פתיחת שיעור מה-cache', INK), '~7 קריאות', '2-3 כתיבות', '3 הכנסות לתור (dedupe) · 1 batch חתימה'],
        [('פולינג audio / visuals', INK), '3-4 קריאות', '0', 'אימות + ילד + שיעור, כל 1.5 שניות'],
        [('הודעת צ׳אט', INK), '4-5 קריאות', '2-3 כתיבות', 'סשן, היסטוריה, הודעות, usage'],
        [('שיעור חדש', INK), '~7 קריאות', '3-4 כתיבות', '+ עבודת מדיה: ~40 העלאות ל-Storage'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['פעולה', 'קריאות', 'כתיבות', 'הערה'], rows, [0.24, 0.14, 0.14, 0.48], row_h=16)
    p.y = y - 10
    p.note('כל קריאה = בקשת HTTPS ל-Supabase. הכפלה ב-150ms נותנת את זמן הרשת המינימלי של הפעולה.')
    c.showPage()


# ============================================================================ 4
def page_capacity(c):
    p = Page(c, 'כמה מחזיק כל שרת', 'עלות ללקוח, ומה יוצא מזה לכל תצורה', 4)

    p.h2('מה עולה ילד אחד', gap=4)
    rows = [
        [('שיחה שגרתית', INK), '~3 בקשות בדקה', 'הודעה כל 30-60 ש׳ + TTS לתשובה', 'זניח: ~0.6ms CPU/דקה'],
        [('פתיחת שיעור חדש', INK), 'עד 160 בקשות בדקה', 'פולינג audio + visuals + תמונה-תמונה', 'פי 50. נמדד: 72% נחסמים'],
        [('שיעור חדש (מדיה)', INK), 'פעם אחת לשיעור, לא לילד', '~130 ש׳ worker, 200MB שיא', 'משותף לכל הכיתה'],
        [('סרטוני פתיחה', INK), 'פעם אחת לילד', '3 סרטונים, ~139 ש׳', 'עדיפות נמוכה, יש fallback'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['מה', 'קצב', 'עלות', 'הערה'], rows, [0.19, 0.22, 0.31, 0.28], row_h=16)
    p.y = y - 10

    p.h2('זיכרון ו-CPU לתהליך (נמדד)')
    rows = [
        [('tutor-web', INK), '105MB → 152MB בעומס', '0-2% בהמתנה, 36-66% ב-30 במקביל', 'מקסימום שנמדד: 152MB'],
        [('tutor-worker', INK), '103MB + ~90MB לעבודה', '3-5% ממוצע, 30% שיא', 'שיא 211MB בעבודה אחת'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['תהליך', 'זיכרון', 'CPU', 'הערה'], rows, [0.16, 0.26, 0.36, 0.22], row_h=16)
    p.y = y - 14

    p.h2('מה יוצא מזה: ילדים משוחחים במקביל, לפי תצורת שרת web')
    # axes() draws category labels raw, so shape the Hebrew here
    rows = [(he('512MB / ליבה אחת'), 600, BLUE), (he('2GB / 2 ליבות'), 1200, BLUE), (he('שני מופעים 2GB'), 2400, AQUA)]
    bars(c, M + 40, p.y - 112, W - 2 * M - 60, 96, rows, 2500, '', '')
    p.y -= 142
    p.note('חישוב שמרני: 30 בקשות בשנייה לליבה ÷ 3 בקשות לדקה לילד. מעל זה הגבול הוא מכסת OpenAI, לא השרת.')
    p.y -= 6
    rows = [
        [('512MB, concurrency 3', INK), '~85', 'מספיק ליום שגרתי'],
        [('2GB, concurrency 12', INK), '~330', 'גל של כיתה חדשה'],
        [('3 מכונות × 2GB', INK), '~1,000', 'מכאן מגבילה מכסת Gemini'],
        [('מכסת Gemini TTS היום', INK), ('נגמרה', BAD), 'עם worker אחד. חובה להעלות'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['worker', 'שיעורים חדשים לשעה', 'הערה'], rows, [0.3, 0.25, 0.45], row_h=15)
    p.y = y - 8
    p.note('130 שניות לשיעור ÷ concurrency. לפי שיעורים חדשים, לא לפי ילדים: שיעור מוכן משרת את כל הכיתה.')

    p.h2('שורה תחתונה')
    step(p, 1, 'השרת אינו הגבול. אחרי היום, מופע web אחד מחזיק מאות ילדים; שניים נדרשים לשרידות, לא לקיבולת.')
    step(p, 2, 'הגבול הוא מכסות: Gemini TTS נגמרה עם worker אחד. OpenAI טרם נבדק בעומס (5 במקביל עברו).')
    step(p, 3, 'הפולינג בפרונט הוא הבזבוז הגדול: פי 50 מבקשות השיחה, ורובו נחסם. תיקון קטן, השפעה גדולה.')
    c.showPage()


# ============================================================================ 5
def page_costs(c):
    p = Page(c, 'עלויות: כמה עולה כל קריאה', 'נמדד היום, ומה נרשם מעכשיו לכל קריאה', 5)
    p.p('מהיום כל קריאת מודל נרשמת בטבלת ai_calls: ספק, מודל, מטרה, ילד, שיעור, טוקנים, שניות אודיו, latency ועלות.')
    p.p('דרך OpenRouter העלות מדויקת מהספק. ישירות מול OpenAI ו-Gemini היא הערכה מטבלת מחירים. בלי מחיר — מסומן.')
    p.y -= 8

    w = (W - 2 * M - 24) / 3
    hero(c, W - M - w, p.y - 70, w, '$0.0033', 'קטע TTS של 6 שניות', 'OpenRouter, מדויק: 165 טוקני פלט', ORANGE)
    hero(c, W - M - 2 * w - 12, p.y - 70, w, '$0.27', 'OpenRouter היום', 'כ-80 קריאות TTS, 3 שיעורים + בדיקות', BLUE)
    hero(c, M, p.y - 70, w, '$10', 'קרדיט בחשבון OpenRouter', 'ללא תקרת בקשות', AQUA)
    p.y -= 92

    p.h2('מה עולה שיעור חדש אחד (14-19 קטעי אודיו, 14-21 תמונות)')
    rows = [
        [('אודיו, OpenRouter', INK), '14-19 קריאות', '$0.05-0.06', ('נמדד', GOOD)],
        [('אודיו, Gemini ישיר', INK), 'אותן קריאות', '~$0.03-0.04 לפי $10/M', ('הערכה', WARN)],
        [('ייצור השיעור, gpt-5.6-sol', INK), '2-6 קריאות', 'לפי $5/$30 למיליון; נכנס ל-usage_summary', ('הערכה', WARN)],
        [('תמונות, flash-lite-image', INK), '14-21 + hero', 'אין מחיר בקוד — AI_IMAGE_PRICES_JSON', ('לא ידוע', BAD)],
        [('סרטוני פתיחה, לילד', INK), '3 סרטונים', 'אין מחיר בקוד', ('לא ידוע', BAD)],
        [('צ׳אט, gpt-4o-mini', INK), 'הודעה', '~$0.0003-0.001 להודעה לפי $0.15/$0.60', ('הערכה', WARN)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['מה', 'קריאות', 'עלות', 'מקור'], rows, [0.3, 0.16, 0.4, 0.14], row_h=16)
    p.y = y - 12
    p.note('"נמדד" = מהספק לכל קריאה. "הערכה" = טבלת מחירים בקוד (MODEL_PRICING_USD). "לא ידוע" = חסר מחיר; ai_costs_daily סופר.')

    p.h2('מה נרשם מעכשיו, ואיפה לראות')
    rows = [
        [('ai_calls', INK), 'שורה לכל קריאה: provider, model, purpose, kid, lesson, tokens, seconds, cost'],
        [('ai_costs_daily', INK), 'לפי יום × ספק × מודל × מטרה: קריאות, שגיאות, טוקנים, latency ממוצע, עלות'],
        [('ai_costs_per_lesson', INK), 'כמה עלה כל שיעור: מדיה לחוד, סה"כ, מתי'],
        [('ai_costs_per_kid', INK), 'כמה עלה כל ילד ליום'],
        [('usage_summary', INK), 'הסיכום הישן נשאר: OpenAI/Gemini למשתמש, עלות לסשן ב-tutor_sessions'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['טבלה / view', 'מה יש שם'], rows, [0.3, 0.7], row_h=16)
    p.y = y - 12

    p.h2('מה זה אומר לאלף ילדים')
    bullet(p, 'המדיה היא לשיעור, לא לילד. כיתה שלמה של 150 יחידות: פעם אחת ~$9 אודיו + תמונות, ואז אפס.')
    bullet(p, 'העלות המשתנה לילד היא הצ׳אט: ~30 הודעות ביום × ~$0.0005 ≈ 1.5 סנט ליום, ~$0.45 לחודש.')
    bullet(p, 'סרטון פתיחה אישי: פעם אחת לילד, 3 סרטונים. המחיר לא בקוד — למלא כדי שייספר.')
    bullet(p, 'להשלמת התמונה: להריץ את מיגרציית ai_calls, ואחרי יום אחד ai_costs_daily נותן את הכל במקום הערכות.')
    c.showPage()


# ============================================================================ 6
def page_findings(c):
    p = Page(c, 'מה נמצא ומה תוקן', 'לפי סדר הגילוי, עם המדידה שחשפה כל אחד', 6)
    rows = [
        [('עבודות רקע בתוך השרת', INK), 'ריסטארט = מדיה אבודה', 'תור + worker + reaper', ('אומת', GOOD)],
        [('worker אחד, FIFO', INK), 'אודיו חיכה 2:20 מאחורי וידאו', 'עדיפויות: אודיו 10, וידאו 60', ('אומת SQL', GOOD)],
        [('TTS 400 מזדמן', INK), 'כישלון אחד = כל האודיו נופל', 'ריטריי 4 ניסיונות', ('אומת', GOOD)],
        [('TTS 429 מכסה', INK), 'נגמר אחרי 30 ייצורים במקביל', 'OpenRouter, אותו מודל, בלי מכסה', ('אומת', GOOD)],
        [('Storage "Server disconnected"', INK), 'חיבור HTTP/2 שנזנח אחרי דקה', 'HTTP/1.1 pool + ריטריי', ('אומת', GOOD)],
        [('כישלון אודיו נבלע', INK), 'עבודה "done", שיעור בלי אודיו', 'העבודה נכשלת ורצה שוב', ('אומת', GOOD)],
        [('event loop חסום', INK), '~3 בקשות בשנייה לכל התהליך', '72 קריאות ל-threadpool', ('אומת', GOOD)],
        [('40 signed URLs לפתיחה', INK), '30 פתיחות = 18 שניות', 'cache + batch', ('אומת', GOOD)],
        [('hero: 30 ייצורים', INK), '493MB, 121% CPU, 20 ש׳', 'נעילה לשיעור', ('אומת', GOOD)],
        [('audio: TTS בבקשה ×30', INK), '27 × 500, 3 דקות, מכסה', 'תור במקום ייצור בבקשה', ('אופליין', WARN)],
        [('עבודה בלי אודיו = done', INK), 'שיעור אילם בלי retry', 'אודיו לא מוכן = כישלון, retry', ('אופליין', WARN)],
        [('"generating" לנצח', INK), 'worker מת = שיעור תקוע', 'מעל 10 דק׳ נלקח מחדש', ('אופליין', WARN)],
        [('פולינג > מגביל קצב', INK), '72% מהבקשות 429', 'backoff 2-8 ש׳, 20 ש׳ על 429', ('בקוד', WARN)],
        [('גיל מול כיתה', INK), 'ילד עם age=7 חסום מכל שיעור', 'לבדוק את המודל', ('פתוח', BAD)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['ממצא', 'מה קרה', 'תיקון', 'מצב'], rows, [0.25, 0.3, 0.29, 0.16], row_h=16)
    p.y = y - 12
    p.note('"אומת" = נבדק מול הפרודקשן. "אופליין" = נבדק עם Supabase מדומה, מחכה למכסת TTS לבדיקה אמיתית.')
    p.y -= 6
    p.h2('שלוש הריצות שהיו לפני/אחרי')
    rows = [(he('hero לפני'), 9035, BAD), (he('hero אחרי'), 1513, GOOD), (he('visuals לפני'), 6740, BAD), (he('visuals אחרי'), 3204, GOOD),
            (he('unit-lesson לפני'), 17040, BAD), (he('unit-lesson אחרי'), 7434, GOOD)]
    bars(c, M + 20, p.y - 130, W - 2 * M - 40, 110, rows, 18000, 'p50 במילישניות, 30 במקביל', '')
    p.y -= 150
    c.showPage()


# ============================================================================ 6
def page_plan(c):
    p = Page(c, 'מה הלאה', 'לפי סדר: קודם מה שחוסם, אחר כך מה שמגדיל', 7)
    p.h2('לפני שממשיכים', gap=4)
    step(p, 1, 'להריץ את מיגרציית ai_calls (יש rollback), ולמלא מחירים לתמונות ולווידאו. אז העלות מלאה.', BAD)
    step(p, 2, 'להשלים את האימות: פולינג ו-audio מהדפדפן, ילדים שונים. ואז קומיט.', BAD)
    step(p, 3, 'Render: שירות Background Worker חדש, פקודה python worker.py, אותם משתני סביבה.', BAD)
    p.y -= 8
    p.h2('שבוע ראשון')
    step(p, 4, 'TTS במקביל ב-worker: 14-19 קטעים בטור = 100-180 ש׳; 4 במקביל ≈ 40 ש׳. עם OpenRouter אין מכסה שמונעת.', WARN)
    step(p, 5, 'אודיו הדרגתי: לכתוב לפי חלקים ולהתחיל כשחלק 1 מוכן. חוצה את ההמתנה מ-105 ל-50 שניות.', WARN)
    step(p, 6, 'Render: worker עם concurrency 2+, שני מופעי web, מגביל קצב ב-Redis. שרידות, לא קיבולת.', WARN)
    step(p, 7, 'timeout מפורש על כל קריאת OpenAI. ל-Gemini TTS כבר יש 90 שניות.', WARN)
    p.y -= 8
    p.h2('כשמגיעים לאלפים')
    step(p, 8, 'מכסות OpenAI: לבדוק RPM/TPM של המודלים בשימוש ולבקש העלאה מראש. backoff על 429 בתור.', BLUE)
    step(p, 9, 'visuals ו-unit-lesson: לצמצם את ה-JSON שחוזר. היום זה 55% CPU ב-11 בקשות בשנייה.', BLUE)
    step(p, 10, 'ניטור: request_log_hourly ו-service_metrics_5min כבר בטבלאות. לחבר לוח מחוונים.', BLUE)
    step(p, 11, 'Cloud Run אם רוצים serverless. לא Lambda: הצינור והמודל של התהליך לא מתאימים לו.', BLUE)
    p.y -= 12

    p.h2('כלים שנשארים')
    rows = [
        [('tools/e2e_media_jobs.py', INK), 'מקצה לקצה: פתיחה, תור, worker, אודיו. --fresh, --kill-worker-once, --load'],
        [('tools/load_api.py', INK), 'עומס לכל ראוט, סימולציית ילדים (--children), ראוטי AI (--with-ai)'],
        [('tools/async_db_helpers.py', INK), 'מעביר קריאות DB סינכרוניות בראוטים async ל-threadpool. להריץ אחרי ראוט חדש'],
        [('/var/log/iakids/', INK), 'לוגים של כל ריצה: server, worker, resources.csv (CPU/RSS כל 2 ש׳), phases'],
        [('request_log · service_metrics', INK), 'בטבלאות Supabase, לכל בקשה ולכל תהליך. ניקוי אחרי 30 יום'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['כלי', 'מה הוא נותן'], rows, [0.3, 0.7], row_h=16)
    p.y = y - 12
    p.note('המקור לכל המספרים: handoff_perfromance.md בשורש הריפו, והלוגים תחת /var/log/iakids/.')
    c.showPage()


def main():
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle('iakids — Hebrew tutor capacity report')
    for fn in (page_summary, page_architecture, page_apis, page_capacity, page_costs, page_findings, page_plan):
        fn(c)
    c.save()
    print(OUT, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()
