#!/usr/bin/env python3
"""Optimization plan + curriculum economics for the Hebrew tutor, as a PDF.

    backend/.venv/bin/python tools/tutor_optimization_report_pdf.py [out.pdf]

Pages: 1 summary · 2 the curriculum (grades, subjects, lessons, units, kids) · 3 what a
unit costs and the projection per grade · 4-5 every optimization, ranked, with effect ·
6 pre-generation plan · 7 what the numbers rest on.

Numbers: production Supabase on 2026-09-14 (learning_lessons, lesson_units_content,
kids_profiles, ai_calls for unit lesson 11), the day's load runs, and ai.google.dev pricing
for the image model. Same drawing helpers as the other reports.
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

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'iakids-tutor-optimization-report.pdf')
DATE = '14 בספטמבר 2026'
WHITE = HexColor('#ffffff')

# ------------------------------------------------------------------ data (measured)
UNIT_COST = 0.82                 # $ per generated unit lesson (lesson 11: images 0.672 + audio 0.083 + text 0.060)
UNIT_IMAGES, UNIT_IMAGE_COST = 20, 0.672
UNIT_AUDIO_COST, UNIT_TEXT_COST = 0.083, 0.060
UNIT_SECONDS = 81 + 339          # generation + media, current pipeline, one worker slot
UNITS_PER_LESSON = 25            # the six lessons that have units: 4 units × 6-8 sub-lessons
GRADES = [  # grade, lessons, subjects, categories, units today, generated, with audio, subject mix
    ('א׳', 314, 5, 41, 0, 0, 0, 'מתמטיקה 144, עברית 59, מדעים 59, מולדת וחברה 36, תנ"ך 16'),
    ('ב׳', 286, 6, 40, 0, 0, 0, 'מתמטיקה 132, מדעים 43, עברית 38, אנגלית 31, מולדת 26, תנ"ך 16'),
    ('ג׳', 286, 6, 38, 0, 0, 0, 'מתמטיקה 120, עברית 46, מדעים 38, אנגלית 36, מולדת וגאוגרפיה 24, תנ"ך 22'),
    ('ד׳', 313, 7, 42, 0, 0, 0, 'מתמטיקה 116, עברית 49, מדעים 42, אנגלית 39, גאוגרפיה 29, תנ"ך 23, היסטוריה 15'),
    ('ה׳', 336, 7, 47, 150, 10, 8, 'מתמטיקה 95, אנגלית 67, עברית 49, מדעים 43, גאוגרפיה 35, תנ"ך 27, היסטוריה 20'),
    ('ו׳', 358, 7, 50, 0, 0, 0, 'מתמטיקה 108, עברית 60, מדעים 59, אנגלית 48, גאוגרפיה 35, תנ"ך 27, היסטוריה 21'),
]
KIDS_BY_AGE = {1: 1, 3: 6, 4: 2, 5: 25, 6: 17, 7: 18, 8: 8, 9: 14, 10: 18, 11: 12, 12: 6, 13: 3, 14: 1, 15: 2}


def fmt(n):
    return f'{n:,.0f}'


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


def opt(p, n, title, effect, how, status, color):
    """One optimization card: number, title, effect line, how line, status tag."""
    c = p.c
    h = 44
    box(c, M, p.y - h, W - 2 * M, h, WHITE, LINE)
    c.setFillColor(color); c.circle(W - M - 14, p.y - 15, 8, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont('SB', 8); c.drawCentredString(W - M - 14, p.y - 17.5, str(n))
    c.setFillColor(INK); c.setFont('SB', 9); c.drawRightString(W - M - 30, p.y - 17, he(title))
    c.setFillColor(GOOD if status == 'בוצע' else (WARN if status == 'בקוד' else MUTED)); c.setFont('SB', 7.5)
    c.drawString(M + 10, p.y - 17, he(status))
    c.setFillColor(INK2); c.setFont('S', 7.8); c.drawRightString(W - M - 30, p.y - 29, he('השפעה: ' + effect))
    c.setFillColor(MUTED); c.setFont('S', 7.8); c.drawRightString(W - M - 30, p.y - 40, he('איך: ' + how))
    p.y -= h + 5


# ============================================================================ 1
def page_summary(c):
    p = Page(c, 'אופטימיזציות וכלכלת הקוריקולום', f'{DATE} · מה יש, מה זה עולה, מה לשפר ובאיזה סדר', 1)
    total_lessons = sum(g[1] for g in GRADES)
    total_units = total_lessons * UNITS_PER_LESSON
    w = (W - 2 * M - 36) / 4
    hero(c, W - M - w, p.y - 70, w, fmt(total_lessons), 'שיעורי-אב, 6 כיתות', '5-7 מקצועות לכיתה', BLUE)
    hero(c, W - M - 2 * w - 12, p.y - 70, w, '150', 'יחידות קיימות', 'כיתה ה׳ מדעים · 10 נוצרו', AQUA)
    hero(c, W - M - 3 * w - 24, p.y - 70, w, f'${UNIT_COST:.2f}', 'יחידה אחת, נמדד', '82% תמונות', ORANGE)
    hero(c, M, p.y - 70, w, f'${total_units * UNIT_COST / 1000:.0f}k', 'כל הקוריקולום', f'{fmt(total_units)} יחידות', BAD)
    p.y -= 92

    p.h2('שלוש עובדות שמשנות את התוכנית')
    step(p, 1, 'התמונות הן הכסף: 20 תמונות ליחידה = $0.67 מתוך $0.82. אודיו וטקסט יחד פחות מ-15 סנט.', BAD)
    step(p, 2, 'הקטלוג כמעט ריק: 150 יחידות מתוך ~47,000 אפשריות (0.3%). ייצור הכל מראש = ~$39k ו-4,450 שעות worker.', BAD)
    step(p, 3, '82 מתוך 133 ילדים חסומים: הראוט משווה גיל לכיתה 1-6, ורוב הילדים הם בני 7-11.', BAD)

    p.h2('מה לעשות, בקצרה')
    bullet(p, 'לייצר לפי שימוש, לא לפי קטלוג: יחידה נוצרת בפתיחה הראשונה (כבר כך), ולחמם מראש רק את הפופולריות.')
    bullet(p, 'לחתוך תמונות: 20 → 8 ליחידה, hero משותף לתת-שיעורים. חוצה את העלות ליחידה ל-~$0.40.')
    bullet(p, 'TTS ותמונות במקביל: 339 ש׳ מדיה → ~100. ילד מחכה דקה וחצי במקום 7 לשיעור חדש.')
    bullet(p, 'לתקן את גיל/כיתה לפני כל דבר אחר: זה יותר ילדים מכל אופטימיזציה.')
    p.y -= 6
    p.note('עמוד 2: הקוריקולום לפי כיתה. עמוד 3: עלות לכיתה. עמודים 4-5: 18 אופטימיזציות לפי סדר. עמוד 6: תוכנית ייצור מראש.')
    c.showPage()


# ============================================================================ 2
def page_curriculum(c):
    p = Page(c, 'הקוריקולום לפי כיתה', 'learning_lessons · lesson_units_content · kids_profiles, מהפרודקשן', 2)
    rows = []
    for g, lessons, subj, cats, units, gen, audio, mix in GRADES:
        rows.append([(f'כיתה {g}', INK), str(lessons), str(subj), str(cats), str(units) if units else '0',
                     f'{gen} / {audio}' if units else '—', fmt(lessons * UNITS_PER_LESSON)])
    rows.append([('סה"כ', INK), fmt(sum(g[1] for g in GRADES)), '', '', '150', '10 / 8', fmt(sum(g[1] for g in GRADES) * UNITS_PER_LESSON)])
    y = table(c, M, p.y, W - 2 * M, ['כיתה', 'שיעורי-אב', 'מקצועות', 'קטגוריות', 'יחידות היום', 'נוצרו / אודיו', 'יחידות ב-25/שיעור'], rows,
              [0.13, 0.13, 0.12, 0.13, 0.15, 0.15, 0.19], row_h=16)
    p.y = y - 10
    p.note('"יחידות ב-25/שיעור": ששת השיעורים שיש להם יחידות מחזיקים 4 units × 6-8 תת-שיעורים = ~25. אם זה הדגם — זה הגודל.')

    p.h2('מקצועות בכל כיתה')
    rows = [[(f'כיתה {g}', INK), mix] for g, _, _, _, _, _, _, mix in GRADES]
    y = table(c, M, p.y, W - 2 * M, ['כיתה', 'שיעורי-אב לפי מקצוע'], rows, [0.13, 0.87], row_h=16)
    p.y = y - 10

    p.h2('הילדים: 133, לפי גיל')
    ages = sorted(KIDS_BY_AGE.items())
    rows = [(str(a), n, BLUE if a <= 6 else BAD) for a, n in ages if a >= 3]
    bars(c, M + 30, p.y - 110, W - 2 * M - 50, 92, rows, 30, '', '')
    p.y -= 128
    c.setFillColor(MUTED); c.setFont('S', 8)
    c.drawRightString(W - M, p.y, he('כחול = גיל 1-6, יכולים לפתוח שיעורי יחידה. אדום = גיל 7-15, חסומים: הראוט משווה kids_profiles.age ל-learning_lessons.grade (1-6).'))
    p.y -= 12
    c.drawRightString(W - M, p.y, he('51 ילדים יכולים, 82 לא. או שהשדה age מחזיק כיתה בטעות אצל חלק, או שהבדיקה צריכה מיפוי גיל→כיתה. לבדוק לפני הכל.'))
    c.showPage()


# ============================================================================ 3
def page_costs(c):
    p = Page(c, 'כמה עולה כל כיתה', f'נמדד על יחידה אחת (שיעור 11): ${UNIT_COST:.2f}. הקרנה לפי 25 יחידות לשיעור-אב', 3)
    p.h2('יחידה אחת, מה נמדד', gap=4)
    rows = [
        [('תמונות', INK), 'gemini-3.1-flash-lite-image', '20 + hero', '$0.0336 לתמונה (ai.google.dev)', f'${UNIT_IMAGE_COST:.3f}', '82%'],
        [('אודיו', INK), 'Gemini TTS דרך OpenRouter', '19 קטעים, 164 ש׳', 'מדויק מהספק', f'${UNIT_AUDIO_COST:.3f}', '10%'],
        [('טקסט', INK), 'gpt-5.6-sol ×3, gpt-4o-mini ×2', '5 קריאות', '$5/$30 ו-$0.15/$0.60 למיליון', f'${UNIT_TEXT_COST:.3f}', '7%'],
        [('סה"כ', INK), '', '44 קריאות', f'{UNIT_SECONDS} ש׳ במסלול הנוכחי', f'${UNIT_COST:.2f}', '100%'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['רכיב', 'מודל', 'כמות', 'מחיר', 'עלות', 'חלק'], rows, [0.1, 0.27, 0.16, 0.27, 0.1, 0.1], row_h=16)
    p.y = y - 12

    p.h2('הקרנה לכל כיתה (25 יחידות לשיעור-אב)')
    rows = []
    tot_u = tot_c = tot_h = 0
    for g, lessons, *_ in GRADES:
        units = lessons * UNITS_PER_LESSON
        cost = units * UNIT_COST
        hours = units * UNIT_SECONDS / 3600
        tot_u += units; tot_c += cost; tot_h += hours
        rows.append([(f'כיתה {g}', INK), fmt(units), f'${fmt(units * UNIT_IMAGE_COST)}', f'${fmt(units * UNIT_AUDIO_COST)}',
                     f'${fmt(units * UNIT_TEXT_COST)}', f'${fmt(cost)}', f'{fmt(hours)} ש׳'])
    rows.append([('סה"כ', INK), fmt(tot_u), f'${fmt(tot_u * UNIT_IMAGE_COST)}', f'${fmt(tot_u * UNIT_AUDIO_COST)}',
                 f'${fmt(tot_u * UNIT_TEXT_COST)}', f'${fmt(tot_c)}', f'{fmt(tot_h)} ש׳'])
    y = table(c, M, p.y, W - 2 * M, ['כיתה', 'יחידות', 'תמונות', 'אודיו', 'טקסט', 'סה"כ', 'זמן worker'], rows,
              [0.13, 0.13, 0.15, 0.13, 0.13, 0.15, 0.18], row_h=16)
    p.y = y - 10
    p.note('"זמן worker" = שעות של slot אחד במסלול הנוכחי (420 ש׳ ליחידה). concurrency 12 מחלק ב-12; TTS+תמונות במקביל מחלק בעוד ~3.')

    p.h2('אותה הקרנה אחרי האופטימיזציות')
    scen = [
        ('היום: 20 תמונות, TTS בטור', UNIT_COST, UNIT_SECONDS),
        ('8 תמונות ליחידה', 8 * 0.0336 + UNIT_AUDIO_COST + UNIT_TEXT_COST, UNIT_SECONDS - 12 * 4.9),
        ('8 תמונות + TTS/תמונות במקביל', 8 * 0.0336 + UNIT_AUDIO_COST + UNIT_TEXT_COST, 81 + 100),
        ('לפי שימוש: 20% מהיחידות נפתחות', (8 * 0.0336 + UNIT_AUDIO_COST + UNIT_TEXT_COST) * 0.2, 0),
    ]
    rows = []
    for name, uc, secs in scen:
        rows.append([(name, INK), f'${uc:.2f}', f'${fmt(tot_u * uc)}', f'{fmt(tot_u * secs / 3600 / 12)} ש׳ ב-12 slots' if secs else 'לפי ביקוש'])
    y = table(c, M, p.y, W - 2 * M, ['תרחיש', 'ליחידה', 'כל הקוריקולום', 'זמן ייצור'], rows, [0.4, 0.14, 0.22, 0.24], row_h=16)
    p.y = y - 8
    p.note('20% נפתחות = הנחה, לא מדידה. ai_costs_per_lesson יגיד אחרי חודש כמה יחידות באמת נפתחות.')
    c.showPage()


# ============================================================================ 4-5
def page_opts_1(c):
    p = Page(c, 'האופטימיזציות, לפי סדר (1)', 'קודם מה שחוסך הכי הרבה כסף וזמן לילד', 4)
    opt(p, 1, 'תיקון גיל/כיתה', '82 מ-133 ילדים מקבלים גישה לשיעורי יחידה. שום אופטימיזציה אחרת לא שווה את זה',
        'מיפוי age→grade (או שדה grade בפרופיל) בבדיקה ב-unit-lesson / hero / audio / visuals', 'פתוח', BAD)
    opt(p, 2, 'פחות תמונות ליחידה: 20 → 8', 'עלות יחידה $0.82 → ~$0.41; זמן תמונות 108 ש׳ → ~45',
        'Visual Director: תמונה לכל 2-3 קטעים במקום לכל קטע; hero משותף לתת-השיעורים של unit', 'פתוח', BAD)
    opt(p, 3, 'TTS במקביל ב-worker', 'אודיו 105-230 ש׳ → ~40; שיעור חדש מוכן ב-~2 דק׳ במקום 7',
        'ThreadPoolExecutor(4) על קטעי חלק; OpenRouter לא מגביל; שמירת סדר ב-lesson_audio_json', 'פתוח', BAD)
    opt(p, 4, 'ייצור לפי שימוש + חימום פופולריות', '$39k → כמה מאות דולר לחודש, לפי מה שנפתח בפועל',
        'להשאיר ייצור בפתיחה ראשונה (קיים); job לילי שמייצר את N היחידות הבאות בכל מסלול פעיל', 'פתוח', WARN)
    opt(p, 5, 'אודיו הדרגתי', 'ילד מתחיל אחרי חלק 1 (~50 ש׳) במקום אחרי הכל (105+)',
        'כתיבת lesson_audio_json לפי חלק + status "partial"; הפרונט מתחיל כשחלק 1 מוכן', 'פתוח', WARN)
    opt(p, 6, 'cache לקטע TTS', 'ריטריי/קריסה לא מייצרים מחדש; חוסך גם כסף וגם דקות',
        'לפני ייצור קטע: לבדוק segment_N.wav ב-Storage לאותה content_version', 'פתוח', WARN)
    opt(p, 7, 'תמונות במקביל: 3 → 6', 'זמן תמונות ליחידה 108 ש׳ → ~55',
        'max_workers=6 ב-generate_all_lesson_visuals (זיכרון: ~15MB לתמונה בזמן העלאה)', 'פתוח', WARN)
    opt(p, 8, 'פולינג backoff בפרונט', '160 בקשות/דקה לילד → ~10; 72% 429 → ~0',
        'iakidsPollSleep בכל 7 הלולאות; מכבד 429; טאב מוסתר לא שואל. לוודא בדפדפן', 'בקוד', WARN)
    c.showPage()


def page_opts_2(c):
    p = Page(c, 'האופטימיזציות, לפי סדר (2)', 'קיבולת, אמינות, ומה שכבר נכנס', 5)
    opt(p, 9, 'worker עם concurrency 2+ ב-Render', 'עבודה ארוכה לא חוסמת שיעור של ילד אחר (נמדד: 162 ש׳ המתנה)',
        'WORKER_CONCURRENCY=3 ב-512MB (110MB + ~90MB לעבודה), 12 ב-2GB', 'פתוח', WARN)
    opt(p, 10, 'Streaming לצ׳אט', 'מילה ראשונה ב-<1 ש׳ במקום 4.5-6 ש׳ לתשובה מלאה',
        'stream=True + StreamingResponse; הסכמה המובנית נבנית בצד הלקוח תוך כדי', 'פתוח', WARN)
    opt(p, 11, 'Prompt caching בין ילדים', 'פחות טוקני קלט ופחות זמן בכל הודעה (OpenAI מטמון אוטומטי מ-1,024 טוקנים)',
        'פרטי הילד בסוף ה-system prompt במקום בתחילתו, כדי שהתחילית תהיה זהה לכולם', 'פתוח', BLUE)
    opt(p, 12, 'unit-lesson: JSON רזה + audio/visuals בתשובה אחת', 'פחות CPU (55% ב-11 req/s) ופחות בקשות פולינג',
        'להחזיר רק מה שחלק 1 צריך; סטטוס אודיו ותמונות באותה תשובה', 'פתוח', BLUE)
    opt(p, 13, 'Realtime במקום פולינג', 'אפס בקשות סטטוס: Supabase דוחף כשהשורה משתנה',
        'ערוץ postgres_changes על lesson_units_content לפי id', 'פתוח', BLUE)
    opt(p, 14, 'מגביל קצב ב-Redis + שני מופעי web', 'מדויק עם כמה מופעים; שרידות',
        'יש קונטיינר redis; INCR עם TTL של דקה', 'פתוח', BLUE)
    opt(p, 15, 'timeout מפורש על OpenAI', 'קריאה תקועה לא תופסת חיבור לנצח',
        'AsyncOpenAI(timeout=..., max_retries=2); ל-Gemini TTS כבר 90 ש׳', 'פתוח', BLUE)
    opt(p, 16, 'תור + worker + reaper + עדיפויות', 'מדיה לא אובדת; hero קודם; אודיו לפני וידאו',
        'media_jobs, worker.py — אומת כולל קריסה יזומה', 'בוצע', GOOD)
    opt(p, 17, 'signed URL cache + batch, HTTP/1.1 pool, DB ב-threadpool', 'unit-lesson 17s → 7.4s, hero 9s → 1.5s',
        'main.py, tools/async_db_helpers.py — נמדד', 'בוצע', GOOD)
    opt(p, 18, 'עלות לכל קריאה + OpenRouter ל-TTS', 'ai_calls: ספק, מודל, מטרה, עלות; אין מכסת TTS',
        'ai_costs.py, TTS_PROVIDER=openrouter — 84 שורות בטבלה, כולן מתומחרות', 'בוצע', GOOD)
    c.showPage()


# ============================================================================ 6
def page_plan(c):
    p = Page(c, 'תוכנית ייצור מראש', 'אם רוצים קטלוג מוכן, ככה עושים את זה בלי לשרוף כסף', 6)
    p.h2('שלב א׳: לפני כל ייצור המוני', gap=4)
    step(p, 1, 'תיקון גיל/כיתה, אחרת הייצור משרת 51 ילדים בלבד.', BAD)
    step(p, 2, 'להוריד תמונות ל-8 ליחידה ולהפעיל TTS/תמונות במקביל. כל יחידה שנוצרת לפני זה עולה כפול.', BAD)
    step(p, 3, 'להחליט על הדגם: 25 יחידות לשיעור-אב (כמו ששת הקיימים) או פחות. זה הכפיל הכי גדול במחיר.', BAD)
    p.y -= 6
    p.h2('שלב ב׳: סדר הייצור')
    step(p, 4, 'כיתות ה׳ ו-ו׳ קודם: שם רוב הילדים (בני 10-11) ושם כבר יש יחידות. ~16,000 יחידות ב-25/שיעור.', WARN)
    step(p, 5, 'לפי מקצוע: מתמטיקה ועברית הן 55% מהשיעורים. להתחיל מהקטגוריות שבתוכנית הלימודים של הרבעון.', WARN)
    step(p, 6, 'job לילי: N יחידות בכל מסלול פעיל, בעדיפות 40 (מתחת לאודיו של ילד שמחכה). worker ייעודי לזה.', WARN)
    p.y -= 6
    p.h2('מה זה עולה, אחרי שלב א׳')
    tot_u = sum(g[1] for g in GRADES) * UNITS_PER_LESSON
    uc = 8 * 0.0336 + UNIT_AUDIO_COST + UNIT_TEXT_COST
    rows = [
        [('כיתות ה׳+ו׳, 25/שיעור', INK), fmt((336 + 358) * 25), f'${fmt((336 + 358) * 25 * uc)}', f'{fmt((336 + 358) * 25 * 181 / 3600 / 12)} ש׳ ב-12 slots'],
        [('כל הקוריקולום, 25/שיעור', INK), fmt(tot_u), f'${fmt(tot_u * uc)}', f'{fmt(tot_u * 181 / 3600 / 12)} ש׳ ב-12 slots'],
        [('כל הקוריקולום, 6/שיעור', INK), fmt(sum(g[1] for g in GRADES) * 6), f'${fmt(sum(g[1] for g in GRADES) * 6 * uc)}', f'{fmt(sum(g[1] for g in GRADES) * 6 * 181 / 3600 / 12)} ש׳ ב-12 slots'],
        [('לפי שימוש, 20% נפתחות', INK), fmt(tot_u * 0.2), f'${fmt(tot_u * 0.2 * uc)}', 'מתפרס על חודשים'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['תרחיש', 'יחידות', 'עלות', 'זמן'], rows, [0.36, 0.16, 0.2, 0.28], row_h=16)
    p.y = y - 10
    p.note(f'עלות ליחידה אחרי שלב א׳: ${uc:.2f} (8 תמונות $0.27 + אודיו $0.08 + טקסט $0.06). זמן: 81 ש׳ ייצור + ~100 ש׳ מדיה.')
    p.y -= 6
    p.h2('מה מודדים תוך כדי')
    bullet(p, 'ai_costs_daily: עלות ליום לפי מודל ומטרה. אם התמונות מעל 60% — עוד לא חתכנו מספיק.')
    bullet(p, 'ai_costs_per_lesson: אילו יחידות נפתחות בפועל. זה מה שמכריע בין "הכל מראש" ל"לפי שימוש".')
    bullet(p, 'media_jobs_hourly: זמן המתנה בתור. אם עולה מעל דקה בשעות פעילות — עוד slot ל-worker.')
    c.showPage()


# ============================================================================ 7
def page_basis(c):
    p = Page(c, 'על מה המספרים נשענים', 'מה נמדד, מה הנחה, ומה יכול להזיז את התמונה', 7)
    rows = [
        [('$0.82 ליחידה', INK), 'נמדד', 'שיעור 11, 44 קריאות ב-ai_calls; אודיו מדויק מהספק, תמונות/טקסט לפי מחירון'],
        [('$0.0336 לתמונה', INK), 'מחירון', 'ai.google.dev: $30/M טוקני פלט תמונה, 1,120 טוקנים ל-1024px'],
        [('1,893 שיעורים, 150 יחידות', INK), 'נמדד', 'ספירה מהפרודקשן, 14/9 17:40'],
        [('25 יחידות לשיעור-אב', INK), 'הנחה', 'ששת השיעורים עם יחידות: 4 units × 6-8. דגם אחר = הכל פרופורציונלי'],
        [('420 ש׳ ליחידה', INK), 'נמדד', '81 ש׳ ייצור + 339 ש׳ מדיה (הערב; בבוקר 169-184; TTS 6-12 ש׳ לקטע)'],
        [('133 ילדים, 82 חסומים', INK), 'נמדד + קריאת קוד', 'kids_profiles.age מול הבדיקה ב-unit-lesson; לא נבדק מהדפדפן'],
        [('20% נפתחות', INK), 'הנחה', 'אין עדיין נתוני שימוש; ai_costs_per_lesson ייתן את המספר האמיתי'],
        [('8 תמונות ליחידה', INK), 'הצעה', 'לא נבדק פדגוגית; המספר לדוגמה בלבד'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['מספר', 'סוג', 'מקור / הערה'], rows, [0.24, 0.14, 0.62], row_h=17)
    p.y = y - 12
    p.h2('מה עוד לא נמדד ויכול לשנות את התמונה')
    bullet(p, 'עלות סרטוני הפתיחה האישיים (3 לילד, gemini-omni): אין מחיר בקוד. עם 1,000 ילדים זה יכול להיות משמעותי.')
    bullet(p, 'התפלגות השימוש האמיתית: איזה כיתות ומקצועות נפתחים. זה קובע כמה מהקטלוג צריך בכלל.')
    bullet(p, 'עלות הצ׳אט לילד ליום: הערכה ~1.5 סנט; ai_costs_per_kid יאשר.')
    bullet(p, 'איכות אחרי חיתוך תמונות: צריך ילד אחד ומורה אחת שיסתכלו, לא רק מספר.')
    c.showPage()


def main():
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle('iakids — Hebrew tutor optimization and curriculum economics')
    for fn in (page_summary, page_curriculum, page_costs, page_opts_1, page_opts_2, page_plan, page_basis):
        fn(c)
    c.save()
    print(OUT, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()
