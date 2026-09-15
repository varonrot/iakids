#!/usr/bin/env python3
"""The full report on the Hebrew tutor backend: every API, what it does, what it waited on,
what was wrong, what was fixed where, before/after numbers, the bottlenecks that remain.

    backend/.venv/bin/python tools/tutor_full_report_pdf.py [out.pdf]

Same drawing helpers as the other reports (tools/capacity_pdf.py). Every number is from
the 2026-09-14 runs on this box (2 vCPU / 2 GB, NYC) against the production Supabase
(eu-central). "Before" = the 10:12 load run, "after" = the 10:39 run and later.
Source: handoff_perfromance.md, /var/log/iakids/{e2e,load}/, public.ai_calls.
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

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'iakids-tutor-full-report.pdf')
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


def h3(p, text):
    p.y -= 6
    p.c.setFillColor(INK); p.c.setFont('SB', 10.5)
    p.c.drawRightString(W - M, p.y, he(text))
    p.y -= 14


def api_block(p, name, what, waits, before, after, fix, bottleneck):
    """One API: a titled panel with six labelled lines."""
    c = p.c
    h = 6 * 12 + 26
    box(c, M, p.y - h, W - 2 * M, h, WHITE, LINE)
    c.setFillColor(BLUE); c.setFont('SB', 9.5)
    c.drawRightString(W - M - 10, p.y - 15, name)
    yy = p.y - 29
    for label, text, col in (('מה', what, INK2), ('מחכה ל', waits, INK2), ('לפני', before, BAD),
                             ('אחרי', after, GOOD), ('תיקון', fix, INK2), ('צוואר בקבוק עכשיו', bottleneck, WARN)):
        c.setFillColor(MUTED); c.setFont('SB', 7.5)
        c.drawRightString(W - M - 10, yy, he(label))
        c.setFillColor(col); c.setFont('S', 8)
        c.drawRightString(W - M - 96, yy, he(text))
        yy -= 12
    p.y -= h + 8


# ============================================================================ 1
def page_summary(c):
    p = Page(c, 'הטיוטור העברי — דוח מלא', f'{DATE} · כל API: מה תוקן, איפה, מה ההשפעה, מה נשאר', 1)
    p.p('יום אחד של מדידה ותיקון מול הפרודקשן. "לפני" = ריצת העומס של 10:12, "אחרי" = 10:39 והלאה. מה שלא נמדד — כתוב.')
    p.y -= 10

    w = (W - 2 * M - 36) / 4
    hero(c, W - M - w, p.y - 70, w, '×2.3', 'unit-lesson ב-30', '17.0s → 7.4s p50', BLUE)
    hero(c, W - M - 2 * w - 12, p.y - 70, w, '×6', 'hero-image', '9.0s → 1.5s · 493 → 136MB', AQUA)
    hero(c, W - M - 3 * w - 24, p.y - 70, w, '0', 'מדיה שאובדת', 'תור + reaper · קריסה: PASS', GOOD)
    hero(c, M, p.y - 70, w, '$0.003', 'לכל קטע TTS', 'מדויק, לכל קריאה', ORANGE)
    p.y -= 92

    p.h2('שלוש התשובות')
    step(p, 1, 'השרת לא הגבול: ראוט DB עולה 12ms CPU; מופע web אחד מחזיק מאות ילדים. הגבול הוא מכסות ספקים ופולינג.')
    step(p, 2, 'הצינור הכבד (אודיו, תמונות, וידאו) יצא מהשרת לתור עם worker. עבודה שנופלת חוזרת לבד, ואומת בהריגה.')
    step(p, 3, 'הכסף נספר מעכשיו לכל קריאה: ספק, מודל, מטרה, שיעור, ילד, עלות. 40 שורות כבר בטבלה, כולן מדויקות.')

    p.h2('מה נמצא, בסדר חומרה')
    rows = [
        [('event loop חסום', INK), '72 קריאות DB סינכרוניות בראוטים async', '~3 בקשות/ש׳ לכל התהליך', ('תוקן', GOOD)],
        [('40 signed URLs לפתיחה', INK), 'קריאה ל-Storage לכל קטע ותמונה', 'unit-lesson 17s, audio 5.5s', ('תוקן', GOOD)],
        [('ייצור בתוך הבקשה', INK), 'hero ו-audio נוצרו בבקשה, ×30 במקביל', '493MB, מכסת TTS נשרפה', ('תוקן', GOOD)],
        [('לקוח Supabase HTTP/2 יחיד', INK), 'sync + threads: פי 3.5 בלבד, קרס ב-30', 'סריאליזציה של DB', ('תוקן', GOOD)],
        [('עבודות רקע בשרת', INK), 'ריסטארט = מדיה אבודה בשקט', 'שיעורים אילמים', ('תוקן', GOOD)],
        [('פולינג 1.5s × 3 לולאות', INK), '160 בקשות/דקה לילד, מגביל 60', '72% מקבלים 429', ('בקוד', WARN)],
        [('מכסת Gemini TTS', INK), '429 עם worker אחד', 'אין אודיו', ('OpenRouter', GOOD)],
        [('TTS בטור', INK), '14-19 קטעים × 6s', 'שיעור 170-185s', ('פתוח', BAD)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['ממצא', 'מה', 'השפעה', 'מצב'], rows, [0.24, 0.38, 0.24, 0.14], row_h=16)
    p.y = y - 12
    p.note('פירוט לכל API בעמודים 3-5, הצינור בעמוד 6, צווארי בקבוק בעמוד 7, מפת השינויים בעמוד 9.')
    c.showPage()


# ============================================================================ 2
def page_architecture(c):
    p = Page(c, 'ארכיטקטורה: לפני ואחרי', 'מה רץ איפה', 2)
    h3(p, 'לפני')
    top = p.y
    nw, nh, gap = 104, 58, 31
    col = [W - M - nw - i * (nw + gap) for i in range(4)]
    node(c, col[0], top - nh, nw, nh, 'דפדפן', ['פולינג כל 1.5 ש׳', 'ללא backoff'], BLUE)
    node(c, col[1], top - nh, nw, nh, 'tutor-web', ['ראוט + BackgroundTasks', 'TTS/וידאו באותו תהליך'], BAD, HexColor('#fdf3f2'))
    node(c, col[2], top - nh, nw, nh, 'Supabase', ['HTTP/2 יחיד', 'signed URL לכל קובץ'], AQUA)
    node(c, col[3], top - nh, nw, nh, 'OpenAI · Gemini', ['DB sync על ה-loop', 'מכסת TTS חינמית'], ORANGE)
    arrow(c, col[0], top - nh / 2, col[1] + nw + 2, top - nh / 2, BLUE)
    arrow(c, col[1], top - nh / 2, col[2] + nw + 2, top - nh / 2, AQUA)
    arrow(c, col[2], top - nh / 2, col[3] + nw + 2, top - nh / 2, ORANGE)
    p.y = top - nh - 18

    h3(p, 'אחרי')
    top = p.y
    node(c, col[0], top - nh, nw, nh, 'דפדפן', ['backoff 2→8 ש׳', 'מכבד 429, טאב מוסתר'], BLUE)
    node(c, col[1], top - nh, nw, nh, 'tutor-web', ['async, DB ב-threadpool', 'רק מכניס לתור'], GOOD, HexColor('#eaf6ef'))
    node(c, col[2], top - nh, nw, nh, 'Supabase', ['HTTP/1.1 pool 100', 'media_jobs · ai_calls'], AQUA)
    node(c, col[3], top - nh, nw, nh, 'OpenAI · OpenRouter', ['צ׳אט/שיעור ישיר', 'TTS: אותו Gemini, בלי מכסה'], ORANGE)
    arrow(c, col[0], top - nh / 2, col[1] + nw + 2, top - nh / 2, BLUE)
    arrow(c, col[1], top - nh / 2, col[2] + nw + 2, top - nh / 2, AQUA, 'enqueue')
    y2 = top - nh - 52
    node(c, col[2], y2 - nh, nw, nh, 'tutor-worker', ['claim לפי עדיפות', 'hero → אודיו ‖ תמונות'], GOOD, HexColor('#eaf6ef'))
    node(c, col[3], y2 - nh, nw, nh, 'Gemini · OpenRouter', ['תמונות ישיר', 'TTS דרך OpenRouter'], ORANGE)
    arrow(c, col[2] + nw / 2, top - nh, col[2] + nw / 2, y2 + 2, AQUA, 'claim / heartbeat')
    arrow(c, col[2], y2 - nh / 2, col[3] + nw + 2, y2 - nh / 2, ORANGE)
    p.y = y2 - nh - 22

    p.h2('מה זה שינה')
    rows = [
        [('בקשה', INK), 'תופסת thread לאורך כל קריאת DB', 'DB ב-threadpool, המודל awaited', '8 בקשות עם auth של 1s: 8s → 1.1s'],
        [('מדיה', INK), 'בתהליך השרת, אובדת בריסטארט', 'תור עם dedupe, heartbeat, reaper, עדיפות', 'SIGKILL באמצע → הושלם'],
        [('Storage', INK), 'signed URL לכל קובץ לכל בקשה', 'cache לשעה + batch', '40 קריאות → 0-1'],
        [('ייצור', INK), 'בתוך הבקשה, בלי dedupe', 'בתור או תחת נעילה', '30 → 1'],
        [('TTS', INK), 'Gemini ישיר, מכסה', 'OpenRouter, אותו מודל', 'אין 429; $0.003/קטע'],
        [('מדדים', INK), 'סיכומים בלבד', 'request_log, service_metrics, ai_calls', 'לכל בקשה, תהליך, קריאה'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['רכיב', 'לפני', 'אחרי', 'ראיה'], rows, [0.1, 0.3, 0.34, 0.26], row_h=16)
    p.y = y - 8
    c.showPage()


# ============================================================================ 3
def page_api_table(c):
    p = Page(c, 'כל ה-API בטבלה אחת', '20 ראוטים · 30 במקביל, 60 בקשות · p50 לפני → אחרי', 3)
    rows = [
        [('GET /learning-lessons/…/units', INK), 'sync', 'DB', '—', '861ms', 'בלי שינוי'],
        [('POST /tutor/active-lesson-state', INK), 'sync', 'DB', '1025ms', '512ms', 'לקוח HTTP'],
        [('GET /tutor/shared-transition/{t}', INK), 'sync', 'DB', '341ms', '517ms', 'רעש'],
        [('POST /tutor/unit-lesson/hero-image', INK), 'async', 'DB, Gemini image', '9035ms', '1513ms', 'cache + נעילה'],
        [('POST /tutor/unit-lesson/visuals', INK), 'sync', 'DB, Storage', '6740ms', '3204ms', 'cache signed URLs'],
        [('POST /tutor/unit-lesson/audio', INK), 'sync', 'DB (היה: TTS)', '5.5s', 'תור', 'לא מייצר בבקשה'],
        [('POST /tutor/unit-lesson', INK), 'async', 'DB, OpenAI, תור', '17040ms', '7434ms', 'loop, cache, batch'],
        [('POST /tutor/lesson-intro', INK), 'sync', 'DB, תור', '—', '2305ms', 'תור'],
        [('POST …/regenerate-transition', INK), 'async', 'DB, תור', '—', '—', 'threadpool'],
        [('POST /tutor/reset-unit-lesson', INK), 'sync', 'DB', '—', '—', '—'],
        [('POST /tutor/lesson', INK), 'async', 'OpenAI', '—', '—', 'threadpool, הקשר'],
        [('POST /tutor/chat', INK), 'async', 'OpenAI gpt-4o-mini', '—', '4.5-6s ×5', 'threadpool, הקשר'],
        [('POST /tutor/tts', INK), 'async', 'Gemini TTS', '500 (מכסה)', 'OpenRouter', 'ספק + הקשר'],
        [('POST /tutor/homework-analyze', INK), 'async', 'OpenAI vision', '—', '—', 'threadpool, הקשר'],
        [('POST /tutor/homework-session', INK), 'sync', 'DB', '—', '—', '—'],
        [('POST /tutor/homework-coach', INK), 'async', 'OpenAI', '—', '—', 'threadpool, הקשר'],
        [('POST /tutor/homework-turn', INK), 'async', 'OpenAI', '—', '—', 'threadpool, הקשר'],
        [('POST /curriculum/chat', INK), 'async', 'OpenAI', '—', '—', 'threadpool, הקשר'],
        [('POST /curriculum/approve', INK), 'sync', 'DB', '—', '—', '—'],
        [('GET /', INK), 'async', '—', '—', '—', 'health'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['ראוט', 'סוג', 'מחכה ל', 'לפני', 'אחרי', 'מה השתנה'], rows,
              [0.36, 0.07, 0.17, 0.1, 0.1, 0.2], row_h=15)
    p.y = y - 12
    p.note('"—" = לא נמדד בעומס (ראוטי מודל עולים כסף בכל קריאה; DB-בלבד לא רלוונטי). "threadpool" = קריאות DB ירדו מה-event loop.')
    p.note('"הקשר" = הראוט מסמן purpose/kid/lesson לכל קריאת מודל שהוא עושה (ai_calls). ')
    p.y -= 4
    p.h2('מה הטבלה אומרת')
    bullet(p, 'ראוטי DB: 27-81 בקשות/שנייה, 12ms CPU כל אחת. הזמן הוא רשת ל-Supabase (~150ms לסיבוב).')
    bullet(p, 'ראוטי המדיה היו האסון: signed URL לכל קובץ, וייצור בתוך הבקשה. שניהם נעלמו.')
    bullet(p, 'ראוטי המודל לא תופסים thread; הזמן שלהם הוא המודל. התקרה שלהם: מכסות OpenAI.')
    bullet(p, 'unit-lesson עדיין 7.4s ב-30 במקביל של אותו ילד: תחרות על שורות progress. עם ילדים שונים — לא נמדד.')
    c.showPage()


# ============================================================================ 4
def page_api_detail_1(c):
    p = Page(c, 'פירוט לפי API (1)', 'הראוטים שהילד מרגיש', 4)
    api_block(p, 'POST /api/tutor/unit-lesson',
              'פתיחת יחידת שיעור: מה-cache, או ייצור עם gpt-5.6-sol (70-92 ש׳) ואז מדיה',
              'auth, ילד, שיעור, progress, OpenAI (בייצור), 3 הכנסות לתור, signed URLs',
              '17.0s ב-30 במקביל, כולן יחד; 40 signed URLs לבקשה; DB על ה-loop; מדיה בתוך השרת',
              '7.4s; 1 batch חתימה; DB ב-threadpool; מדיה בתור עם עדיפות 10',
              'main.py: dispatch_media_job, signed_url_cached, add_signed_urls (batch), async_db_helpers',
              'כתיבות progress של אותו ילד; JSON גדול בתשובה; לא נמדד עם ילדים שונים')
    api_block(p, 'POST /api/tutor/unit-lesson/audio',
              'הפרונט שואל עד שהאודיו מוכן; מחזיר lesson_audio עם URLs חתומים',
              'auth, ילד, שיעור, Storage (חתימה)',
              'אם לא מוכן — ייצר TTS בתוך הבקשה, 100+ ש׳, ×30 במקביל בלי dedupe → 27×500, מכסה נשרפה',
              'מכניס עבודת unit_lesson_audio לתור (dedupe) ומחזיר "generating" מיד; חתימה ב-batch',
              'main.py generate_unit_lesson_audio (ראוט): ייצור הוחלף ב-dispatch_media_job',
              'לא נמדד מול הפרוד אחרי התיקון (אופליין: 10 במקביל, 0.6s)')
    api_block(p, 'POST /api/tutor/unit-lesson/hero-image',
              'תמונת הפתיחה של השיעור; מייצר אם חסרה',
              'auth, ילד, שיעור, Storage, Gemini image (בייצור)',
              '30 בקשות = 30 ייצורים במקביל: p50 9.0s, p90 20s, 493MB, 121% CPU',
              'p50 1.5s, 18 req/s, 136MB; ייצור אחד תחת נעילה; ה-worker מייצר hero ראשון',
              'main.py: generation_lock, signed_url_cached; media job: hero קודם',
              'ייצור ~3.5s ל-Gemini כשחסר')
    api_block(p, 'POST /api/tutor/unit-lesson/visuals',
              'רשימת התמונות המוכנות של השיעור; הפרונט שואל עד שכולן קיימות',
              'auth, ילד, שיעור, Storage ×21',
              '6.7s, 3.5 req/s: signed URL לכל תמונה לכל בקשה',
              '3.2s, 11 req/s: cache לשעה',
              'main.py create_lesson_media_signed_url → signed_url_cached',
              'JSON גדול לכל בקשה (55% CPU ב-11 req/s); ראוט סינכרוני')
    api_block(p, 'POST /api/tutor/chat',
              'הודעת צ׳אט של הילד → תשובה מובנית של gpt-4o-mini',
              'auth, ילד, זיכרון, 7 הודעות היסטוריה, OpenAI, כתיבות סשן/usage',
              'DB על ה-loop (auth, ילד, היסטוריה, סשן): 8 קריאות',
              '5 במקביל: p50 4.5-6s (זמן המודל), 0 שגיאות; DB ב-threadpool; עלות לכל קריאה',
              'tools/async_db_helpers.py, ai_context("chat")',
              'זמן המודל: 4.5-6s לתשובה מלאה. streaming יביא מילה ראשונה ב-<1s')
    c.showPage()


# ============================================================================ 5
def page_api_detail_2(c):
    p = Page(c, 'פירוט לפי API (2)', 'קול, שיעורי בית, תכנית לימודים, ושאר ה-DB', 5)
    api_block(p, 'POST /api/tutor/tts',
              'TTS חי למשפט של המורה (מחוץ לשיעור המוקלט)',
              'auth, Gemini TTS (async), כתיבת סשן',
              '5/5 נכשלו: 429 מכסת Gemini; DB על ה-loop',
              'TTS_PROVIDER=openrouter: אותו מודל וקול, 4-8s, $0.003/משפט; נרשם ב-ai_calls',
              'main.py tutor_tts: ענף OpenRouter (openrouter_tts_pcm_async)',
              'latency של הספק: 4-8s, ולפעמים 27s (1 מ-8)')
    api_block(p, 'POST /api/tutor/lesson · homework-coach · homework-turn · curriculum/chat',
              'שיחות מובנות מול OpenAI (שיעור, שיעורי בית, בניית תכנית)',
              'auth, ילד, DB, OpenAI',
              'DB על ה-loop; בלי מעקב עלות/מודל',
              'DB ב-threadpool; כל קריאה נרשמת עם purpose (lesson_chat / homework / curriculum)',
              'tools/async_db_helpers.py, ai_context(...)',
              'לא נמדד בעומס (כל קריאה עולה כסף). התקרה: מכסות OpenAI')
    api_block(p, 'POST /api/tutor/homework-analyze',
              'ניתוח צילום שיעורי בית (vision)',
              'auth, ילד, Storage (הורדה), OpenAI vision',
              'DB על ה-loop',
              'threadpool + הקשר עלות',
              'tools/async_db_helpers.py',
              'הורדת הקובץ מ-Storage בתוך הבקשה; לא נמדד')
    api_block(p, 'POST /api/tutor/lesson-intro',
              'פתיח לשיעור; למנויים — סרטוני פתיחה אישיים (3, ~139 ש׳)',
              'auth, ילד, מנוי, kid_personal_media, תור',
              'ייצור וידאו ב-BackgroundTasks בשרת',
              '2.3s ב-30 במקביל; וידאו בתור בעדיפות 60 (יש fallback)',
              'main.py: dispatch_media_job("kid_intro_videos")',
              'ראוט סינכרוני (66% CPU); וידאו 46s לסרטון')
    api_block(p, 'units · active-lesson-state · shared-transition · reset · approve · homework-session/start',
              'ראוטי DB בלבד',
              'auth + שאילתה',
              '—',
              '27-81 req/s, 12ms CPU לבקשה, p50 0.3-1.0s (רשת ל-Supabase)',
              'לקוח Supabase pooled HTTP/1.1',
              'סיבובי רשת: 2-4 לבקשה × ~150ms. Realtime/cache יורידו')
    c.showPage()


# ============================================================================ 6
def page_pipeline(c):
    p = Page(c, 'הצינור ברקע: אודיו, תמונות, וידאו', 'לפני: BackgroundTasks בשרת. אחרי: media_jobs + worker', 6)
    p.h2('מחזור חיים של עבודה', gap=4)
    rows = [
        [('enqueue', INK), 'הראוט מכניס שורה; dedupe על (סוג, שיעור) חי; עדיפות לפי סוג; בקשה דחופה מושכת קדימה'],
        [('claim', INK), 'worker לוקח את הדחופה ביותר, אטומי (SKIP LOCKED), attempts+1, started_at'],
        [('heartbeat', INK), 'כל 10-30 ש׳; RSS נדגם כל 2 ש׳ ונשמר ב-metrics של העבודה'],
        [('finish', INK), 'done, או pending עם backoff (60s × ניסיון), או failed אחרי 5; duration_ms'],
        [('reaper', INK), 'running בלי heartbeat 60-300 ש׳ → pending (או failed). זה מה שהציל את בדיקת הקריסה'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['שלב', 'מה קורה'], rows, [0.14, 0.86], row_h=15)
    p.y = y - 12

    p.h2('מה נמדד')
    rows = [
        [('ייצור שיעור', INK), 'gpt-5.6-sol', '70-92 ש׳', 'השרת ב-0-2% CPU: המתנה'],
        [('hero', INK), 'gemini-3.1-flash-lite-image', '3.2-5 ש׳', 'ראשון בעבודה, לפני הכל'],
        [('אודיו לשיעור', INK), 'TTS ×14-19 בטור', '105-236 ש׳', '6 ש׳ לקטע; 27 ש׳ לפעמים'],
        [('תמונות', INK), '14-21 × 3.5-5 ש׳, 3 במקביל', '30-60 ש׳', 'cache hit ב-4.7 ש׳'],
        [('סרטוני פתיחה', INK), '3 × ~46 ש׳', '139 ש׳', 'פעם לילד'],
        [('עבודת מדיה שלמה', INK), 'hero + (אודיו ‖ תמונות)', '169-184 ש׳', 'שיא RSS 200-212MB'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['שלב', 'מודל / מבנה', 'זמן', 'הערה'], rows, [0.2, 0.32, 0.16, 0.32], row_h=15)
    p.y = y - 12

    p.h2('בדיקת הקריסה (13:26)')
    step(p, 1, 'שיעור חדש נוצר (85 ש׳), עבודת מדיה נתפסה. 20 ש׳ אחר כך: SIGKILL ל-worker. הספיק: hero, 6 תמונות, 4 קטעי TTS.')
    step(p, 2, 'worker חדש עלה. אחרי 60 ש׳ ה-reaper החזיר את העבודה (attempt 2).')
    step(p, 3, 'ניסיון 2: hero מה-cache, 6 תמונות cache hit, 8 תמונות + 14 קטעי TTS מחדש. 183 ש׳. אודיו מוכן.')
    step(p, 4, 'מה אבד: 4 קטעי TTS (~$0.013). אין cache לקטע — השיפור הבא. מה נחשף: "generating" תמיד נחשב תקוע (תוקן).')
    p.y -= 6
    p.h2('לפני / אחרי בצינור')
    rows = [
        [('ריסטארט באמצע', INK), 'מדיה אבודה בשקט, שיעור אילם', 'העבודה חוזרת ומושלמת', ('אומת', GOOD)],
        [('כישלון אודיו', INK), 'נבלע; "done" בלי אודיו', 'העבודה נכשלת ורצה שוב; אודיו לא-מוכן = כישלון', ('אומת', GOOD)],
        [('סדר', INK), 'FIFO: אודיו חיכה 2:20 מאחורי וידאו', 'עדיפויות + hero ראשון', ('אומת SQL', GOOD)],
        [('TTS 400/429/ניתוק', INK), 'קריאה אחת מפילה הכל', 'ריטריי; Storage ריטריי על ניתוק בלבד', ('אומת', GOOD)],
        [('מכסה', INK), 'Gemini חינמי, נגמרת', 'OpenRouter pay-as-you-go', ('אומת', GOOD)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['מצב', 'לפני', 'אחרי', 'מצב'], rows, [0.18, 0.32, 0.36, 0.14], row_h=15)
    c.showPage()


# ============================================================================ 7
def page_bottlenecks(c):
    p = Page(c, 'צווארי בקבוק: מה נשאר, לפי סדר', 'מה עוצר אלפי משתמשים היום, עם הראיה והצעד', 7)
    items = [
        ('TTS בטור בתוך עבודת מדיה', 'שיעור חדש = 170-185 ש׳ עד שיש אודיו; worker אחד = ~20 שיעורים/שעה',
         '4 קטעים במקביל: ~40 ש׳ לשיעור, פי 4 תפוקה. OpenRouter לא מגביל', BAD),
        ('פולינג הפרונט (בקוד, לא בדפדפן עדיין)', '72% מבקשות ילד בשיעור חדש נחסמו; 34 req/s ל-50 ילדים',
         'backoff נכנס ל-index.html; לבדוק בדפדפן; אופציה: Supabase Realtime', WARN),
        ('unit-lesson: תחרות שורות + JSON גדול', '7.4s ב-30 של אותו ילד; 55% CPU ב-visuals',
         'למדוד עם ילדים שונים; לצמצם את ה-JSON; audio + visuals בתשובה אחת', WARN),
        ('אודיו כל-או-כלום', 'הפרונט מתחיל רק כשכל האודיו מוכן (~105 ש׳); חלק 1 מוכן ב-~50',
         'כתיבה לפי חלקים + שינוי בפרונט: חצי מזמן ההמתנה', WARN),
        ('latency ספק חריג', 'OpenRouter TTS: 27-29 ש׳ לפעמים (2 מ-~90)', 'timeout 90 ש׳ קיים; ריטריי; במקביל מסתיר', WARN),
        ('מכסות OpenAI', 'לא נבדק בעומס (5 במקביל עברו)', 'לבדוק RPM/TPM בחשבון; backoff על 429', WARN),
        ('worker יחיד', 'עבודה יתומה של 236 ש׳ עיכבה שיעור חדש ב-162 ש׳', 'concurrency 2+ ב-Render; זיכרון: 110MB + 90MB לעבודה', WARN),
        ('מחירים חסרים', 'תמונות ווידאו נרשמים בלי עלות (unknown)', 'AI_IMAGE_PRICES_JSON; ai_costs_daily סופר', BLUE),
        ('מגביל קצב בזיכרון', 'לא מדויק עם 2 מופעים', 'Redis (יש קונטיינר) או טבלה', BLUE),
        ('ללא cache לקטע TTS', 'ריטריי/קריסה = כל הקטעים מחדש', 'לבדוק קיום segment_N.wav לפני ייצור', BLUE),
    ]
    for i, (t, ev, nxt, col) in enumerate(items, 1):
        h = 46
        box(c, M, p.y - h, W - 2 * M, h, WHITE, LINE)
        c.setFillColor(col); c.circle(W - M - 14, p.y - 15, 8, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont('SB', 8); c.drawCentredString(W - M - 14, p.y - 17.5, str(i))
        c.setFillColor(INK); c.setFont('SB', 9); c.drawRightString(W - M - 30, p.y - 17, he(t))
        c.setFillColor(INK2); c.setFont('S', 7.8); c.drawRightString(W - M - 30, p.y - 29, he('ראיה: ' + ev))
        c.setFillColor(MUTED); c.setFont('S', 7.8); c.drawRightString(W - M - 30, p.y - 40, he('צעד: ' + nxt))
        p.y -= h + 6
    c.showPage()


# ============================================================================ 8
def page_costs(c):
    p = Page(c, 'עלויות', 'לכל קריאה, מהיום; מה נמדד ומה עדיין הערכה', 8)
    w = (W - 2 * M - 24) / 3
    hero(c, W - M - w, p.y - 70, w, '$0.003', 'קטע TTS של 6 שניות', 'OpenRouter, מדויק: ~165 טוקני פלט', ORANGE)
    hero(c, W - M - 2 * w - 12, p.y - 70, w, '$0.27', 'OpenRouter היום', '~90 קריאות TTS: 3 שיעורים + בדיקות', BLUE)
    hero(c, W - M - 3 * w - 24, p.y - 70, w, '40', 'שורות ב-ai_calls כבר', 'כולן עם עלות מהספק', AQUA)
    p.y -= 92
    p.h2('שיעור חדש אחד')
    rows = [
        [('אודיו, OpenRouter', INK), '14-19 קריאות', '$0.05-0.06', ('נמדד', GOOD)],
        [('אודיו, Gemini ישיר', INK), 'אותן קריאות', '~$0.03-0.04 לפי $10/M', ('הערכה', WARN)],
        [('ייצור השיעור, gpt-5.6-sol', INK), '2-6 קריאות', '$5/$30 למיליון; מעכשיו ב-ai_calls', ('הערכה', WARN)],
        [('תמונות, flash-lite-image', INK), '14-21 + hero', 'אין מחיר בקוד — AI_IMAGE_PRICES_JSON', ('לא ידוע', BAD)],
        [('סרטוני פתיחה', INK), '3 לילד', 'אין מחיר בקוד', ('לא ידוע', BAD)],
        [('צ׳אט, gpt-4o-mini', INK), 'הודעה', '~$0.0003-0.001 לפי $0.15/$0.60', ('הערכה', WARN)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['מה', 'קריאות', 'עלות', 'מקור'], rows, [0.28, 0.16, 0.42, 0.14], row_h=16)
    p.y = y - 12
    p.h2('איפה רואים')
    rows = [
        [('ai_calls', INK), 'שורה לכל קריאה: provider, model, purpose, kid, lesson, tokens, seconds, latency, cost, source'],
        [('ai_costs_daily', INK), 'יום × ספק × מודל × מטרה: קריאות, שגיאות, טוקנים, latency, עלות, כמה בלי מחיר'],
        [('ai_costs_per_lesson', INK), 'כמה עלה כל שיעור (מדיה לחוד)'],
        [('ai_costs_per_kid', INK), 'כמה עלה כל ילד ליום'],
    ]
    y = table(c, M, p.y, W - 2 * M, ['view', 'מה יש שם'], rows, [0.25, 0.75], row_h=15)
    p.y = y - 12
    p.h2('לאלף ילדים')
    bullet(p, 'המדיה לשיעור, לא לילד: כיתה של 150 יחידות ≈ $9 אודיו + תמונות, פעם אחת.')
    bullet(p, 'העלות המשתנה לילד: צ׳אט, ~30 הודעות ביום ≈ 1.5 סנט ליום, ~$0.45 לחודש. סרטוני פתיחה: פעם אחת, מחיר לא בקוד.')
    bullet(p, 'ai_costs_daily אחרי יום עבודה אמיתי מחליף את כל ההערכות כאן במספרים.')
    c.showPage()


# ============================================================================ 9
def page_changes(c):
    p = Page(c, 'מפת השינויים', 'איפה כל תיקון יושב, ומה נשאר לפני קומיט', 9)
    rows = [
        [('supabase/migrations/20260914_media_jobs.sql', INK), 'טבלת התור + 5 RPC', ('רץ בפרוד', GOOD)],
        [('…/20260914_ops_metrics.sql', INK), 'request_log, service_metrics, views, prune', ('רץ בפרוד', GOOD)],
        [('…/20260914_media_jobs_priority.sql', INK), 'priority, claim לפי עדיפות, pull-forward', ('רץ בפרוד', GOOD)],
        [('…/20260914_ai_calls.sql (+ rollback)', INK), 'ai_calls, 2 RPC, 3 views', ('רץ בפרוד', GOOD)],
        [('backend-ai-tutor-he/main.py', INK), 'תור, cache, נעילות, ריטריי, ספקים, הקשר, loop', ('בקוד', WARN)],
        [('backend-ai-tutor-he/worker.py', INK), 'תהליך ה-worker: claim, heartbeat, reaper, מדדים, הקשר', ('בקוד', WARN)],
        [('backend-ai-tutor-he/ops_metrics.py', INK), 'request_log + service_metrics ברקע', ('בקוד', WARN)],
        [('backend-ai-tutor-he/ai_costs.py', INK), 'עטיפת הלקוחות, ai_calls, פתרון עלות מהספק', ('בקוד', WARN)],
        [('he/workspace/index.html', INK), 'iakidsPollSleep: backoff, 429, טאב מוסתר, 7 לולאות', ('בקוד', WARN)],
        [('tools/ (e2e, load_api, tts_check)', INK), 'בדיקות: מקצה לקצה, עומס, ילדים, TTS', ('בקוד', WARN)],
        [('tools/async_db_helpers.py', INK), 'קריאות DB ב-async → threadpool', ('בקוד', WARN)],
        [('handoff_perfromance.md', INK), 'כל הממצאים, המדידות והצעדים, כרונולוגית', ('בקוד', WARN)],
    ]
    y = table(c, M, p.y, W - 2 * M, ['קובץ', 'מה', 'מצב'], rows, [0.42, 0.46, 0.12], row_h=15)
    p.y = y - 12
    p.h2('מה נשאר לפני קומיט')
    step(p, 1, 'הפולינג החדש מהדפדפן האמיתי: לפתוח שיעור חדש ב-workspace ולראות ב-request_log_hourly שאין 429.', BAD)
    step(p, 2, 'unit-lesson עם ילדים שונים (יש 4 בכיתה ה׳ בחשבון): להפריד תחרות שורות מעלות אמיתית.', BAD)
    step(p, 3, 'ראוט audio מול הפרוד אחרי התיקון (אופליין עבר).', BAD)
    step(p, 4, 'Render: שירות Background Worker + משתני הסביבה החדשים (למטה).', WARN)
    step(p, 5, 'ואז: TTS במקביל, אודיו הדרגתי, cache לקטע, Redis למגביל, מחירים לתמונות/וידאו.', BLUE)
    p.y -= 6
    p.note('משתני סביבה חדשים: MEDIA_JOBS_MODE, WORKER_CONCURRENCY, AI_PROVIDER, TTS_PROVIDER,')
    p.note('OPENROUTER_API_KEY, AI_PRICES_JSON, AI_IMAGE_PRICES_JSON, SUPABASE_HTTP_POOL,')
    p.note('OPS_METRICS_ENABLED, AI_COSTS_ENABLED, MEDIA_JOB_MAX_ATTEMPTS.')
    c.showPage()


def main():
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle('iakids — Hebrew tutor full report')
    for fn in (page_summary, page_architecture, page_api_table, page_api_detail_1, page_api_detail_2,
               page_pipeline, page_bottlenecks, page_costs, page_changes):
        fn(c)
    c.save()
    print(OUT, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()
