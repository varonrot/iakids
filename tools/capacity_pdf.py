#!/usr/bin/env python3
"""Draw the capacity report as a PDF.

    backend/.venv/bin/python tools/capacity_pdf.py [out.pdf]

The numbers come from tools/loadtest.py (see tools/CAPACITY.md). Hebrew is laid out
right-to-left through python-bidi, because reportlab draws glyphs in the order it is
given them and would otherwise print every Hebrew line backwards.
"""
import sys, os
from bidi.algorithm import get_display
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

W, H = A4
M = 42                      # page margin

FONT_DIR = '/usr/share/fonts/truetype/dejavu'
pdfmetrics.registerFont(TTFont('S', f'{FONT_DIR}/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('SB', f'{FONT_DIR}/DejaVuSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('M', f'{FONT_DIR}/DejaVuSansMono.ttf'))

# Validated categorical palette (scripts/validate_palette.js, light surface)
BLUE, ORANGE, AQUA = HexColor('#2a78d6'), HexColor('#eb6834'), HexColor('#1baf7a')
INK, INK2, MUTED = HexColor('#12161c'), HexColor('#454b54'), HexColor('#7a828d')
LINE, PANEL, SURFACE = HexColor('#dfe3e8'), HexColor('#f4f6f8'), HexColor('#fcfcfb')
GOOD, WARN, BAD = HexColor('#1e7a48'), HexColor('#b06a00'), HexColor('#b3261e')


def he(s):
    """Hebrew laid out for a renderer that has no bidi of its own."""
    return get_display(s)


class Page:
    def __init__(self, c, title, sub=None, n=1):
        self.c, self.y = c, H - M
        c.setFillColor(SURFACE); c.rect(0, 0, W, H, fill=1, stroke=0)
        # header rule
        c.setFillColor(INK); c.setFont('SB', 21)
        c.drawRightString(W - M, self.y - 16, he(title))
        if sub:
            c.setFillColor(MUTED); c.setFont('S', 9.5)
            c.drawRightString(W - M, self.y - 32, he(sub))
        c.setFillColor(MUTED); c.setFont('S', 8)
        c.drawString(M, self.y - 16, f'iakids  ·  {n}')
        c.setStrokeColor(LINE); c.setLineWidth(1)
        c.line(M, self.y - 42, W - M, self.y - 42)
        self.y -= 62

    def h2(self, t, gap=16):
        self.y -= gap
        self.c.setFillColor(INK); self.c.setFont('SB', 13)
        self.c.drawRightString(W - M, self.y, he(t))
        self.y -= 16

    def p(self, t, size=9.5, color=None, lead=13):
        self.c.setFillColor(color or INK2); self.c.setFont('S', size)
        self.c.drawRightString(W - M, self.y, he(t))
        self.y -= lead

    def note(self, t, size=8.5):
        self.p(t, size, MUTED, 11)


def hero(c, x, y, w, big, label, sub, color):
    """One headline number in a panel."""
    c.setFillColor(PANEL); c.setStrokeColor(LINE); c.setLineWidth(1)
    c.roundRect(x, y, w, 70, 10, fill=1, stroke=1)
    c.setFillColor(color); c.setFont('SB', 26)
    c.drawRightString(x + w - 14, y + 40, big)
    c.setFillColor(INK); c.setFont('SB', 9.5)
    c.drawRightString(x + w - 14, y + 25, he(label))
    c.setFillColor(MUTED); c.setFont('S', 8)
    c.drawRightString(x + w - 14, y + 11, he(sub))


def axes(c, x, y, w, h, xs, ymax, ylab, xlab, yfmt='{:.0f}'):
    """A plain frame: recessive grid, ticks on the left, categories along the bottom."""
    c.setFillColor(HexColor('#ffffff')); c.setStrokeColor(LINE); c.setLineWidth(1)
    c.rect(x, y, w, h, fill=1, stroke=1)
    c.setFont('S', 7.5)
    for i in range(5):
        gy = y + h * i / 4
        c.setStrokeColor(HexColor('#eef1f4')); c.setLineWidth(0.8)
        if i: c.line(x + 1, gy, x + w - 1, gy)
        c.setFillColor(MUTED)
        c.drawRightString(x - 5, gy - 2.5, yfmt.format(ymax * i / 4))
    n = len(xs)
    for i, v in enumerate(xs):
        px = x + w * (i + .5) / n
        c.setFillColor(MUTED)
        c.drawCentredString(px, y - 11, str(v))
    c.setFillColor(MUTED); c.setFont('S', 7.5)
    c.drawCentredString(x + w / 2, y - 23, he(xlab))
    # flat, above the axis: rotated Hebrew is unreadable
    c.drawString(x, y + h + 6, he(ylab))
    return lambda i: x + w * (i + .5) / n, lambda v: y + h * min(v / ymax, 1.02)


def line_series(c, px, py, values, color, label, dot=True, dash=None, nudge=0):
    c.setStrokeColor(color); c.setLineWidth(2)
    c.setDash(dash or [])
    pts = [(px(i), py(v)) for i, v in enumerate(values)]
    for a, b in zip(pts, pts[1:]):
        c.line(a[0], a[1], b[0], b[1])
    c.setDash([])
    if dot:
        for X, Y in pts:
            c.setFillColor(HexColor('#ffffff')); c.circle(X, Y, 3.6, fill=1, stroke=0)
            c.setFillColor(color); c.circle(X, Y, 2.6, fill=1, stroke=0)
    # direct label at the last point, which is what the legend would otherwise carry.
    # It goes in the gutter the caller reserved, so it cannot run off the plot.
    c.setFillColor(color); c.setFont('SB', 8)
    c.drawString(pts[-1][0] + 8, pts[-1][1] - 3 + nudge, label)


def bars(c, x, y, w, h, rows, ymax, xlab, ylab):
    px, py = axes(c, x, y, w, h, [r[0] for r in rows], ymax, ylab, xlab,
                  yfmt='{:,.0f}')
    n = len(rows)
    bw = w / n * 0.52
    for i, (_, v, col) in enumerate(rows):
        cx = px(i)
        top = py(v)
        c.setFillColor(col)
        c.roundRect(cx - bw / 2, y + 1, bw, max(top - y - 1, 2), 4, fill=1, stroke=0)
        c.setFillColor(INK); c.setFont('SB', 8)
        c.drawCentredString(cx, top + 5, f'{v:,}')


def table(c, x, y, w, head, rows, widths, row_h=17):
    """A right-to-left table: first column on the right."""
    cols = [w * f for f in widths]
    edges, acc = [], x + w
    for cw in cols:
        edges.append(acc); acc -= cw
    c.setFillColor(PANEL); c.rect(x, y - row_h, w, row_h, fill=1, stroke=0)
    c.setFillColor(INK); c.setFont('SB', 8.5)
    for e, t in zip(edges, head):
        c.drawRightString(e - 7, y - row_h + 5.5, he(t))
    yy = y - row_h
    for r in rows:
        yy -= row_h
        c.setStrokeColor(LINE); c.setLineWidth(0.6); c.line(x, yy + row_h, x + w, yy + row_h)
        for j, (e, t) in enumerate(zip(edges, r)):
            bold = isinstance(t, tuple)
            txt, col = (t if bold else (t, INK2))
            c.setFillColor(col)
            c.setFont('SB' if bold else 'S', 8.5)
            c.drawRightString(e - 7, yy + 5.5, he(str(txt)))
    c.setStrokeColor(LINE); c.line(x, yy, x + w, yy)
    return yy


def box(c, x, y, w, h, fill, stroke, r=9):
    c.setFillColor(fill); c.setStrokeColor(stroke); c.setLineWidth(1.2)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1)


def node(c, x, y, w, h, title, sub, color, fill=None):
    box(c, x, y, w, h, fill or HexColor('#ffffff'), color)
    c.setFillColor(INK); c.setFont('SB', 9)
    c.drawCentredString(x + w / 2, y + h - 16, he(title))
    c.setFillColor(MUTED); c.setFont('S', 7.5)
    for i, s in enumerate(sub):
        c.drawCentredString(x + w / 2, y + h - 29 - i * 10, he(s))


def arrow(c, x1, y1, x2, y2, color, label=None, dash=None):
    c.setStrokeColor(color); c.setLineWidth(1.4); c.setDash(dash or [])
    c.line(x1, y1, x2, y2)
    c.setDash([])
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    for s in (2.6, -2.6):
        c.line(x2, y2, x2 - 7 * math.cos(a - s * .12) * 1.0, y2 - 7 * math.sin(a - s * .12))
    c.setFillColor(color)
    p = c.beginPath(); p.moveTo(x2, y2)
    p.lineTo(x2 - 8 * math.cos(a - .35), y2 - 8 * math.sin(a - .35))
    p.lineTo(x2 - 8 * math.cos(a + .35), y2 - 8 * math.sin(a + .35))
    p.close(); c.drawPath(p, fill=1, stroke=0)
    if label:
        c.setFillColor(MUTED); c.setFont('S', 7)
        c.drawCentredString((x1 + x2) / 2, (y1 + y2) / 2 + 5, he(label))


# ----------------------------------------------------------------- measured data
CONC = [2, 4, 8, 16, 32, 64]
STATIC = [37, 80, 127, 117, 80, None]          # page loads/s, Cloudflare
SUPA = [6.3, 17.6, 25.5, 44.8, 40.2, 25.5]     # game-loads/s, Supabase reads
REND = [11.6, 21.0, 39.4, 58.4, 64.1, None]    # requests/s, FastAPI, no model
P95_SUPA = [0.72, 0.26, 0.39, 0.49, 0.76, 3.00]
P95_STATIC = [0.15, 0.09, 0.12, 0.19, 0.39, None]
P95_REND = [0.32, 0.30, 0.27, 0.40, 0.45, None]


def page1(c):
    p = Page(c, 'כמה ילדים יכולים לשחק בו זמנית', 'נמדד ב-10 בספטמבר 2026 · הנתונים מ-tools/loadtest.py', 1)
    gap = 12
    bw = (W - 2 * M - 2 * gap) / 3
    hero(c, W - M - bw, p.y - 70, bw, '~600', 'ילדים משחקים בו זמנית', 'מוגבל על ידי Supabase', BLUE)
    hero(c, W - M - 2 * bw - gap, p.y - 70, bw, '~10/s', 'בקשות לטיוטור', 'מוגבל על ידי קריאת המודל', ORANGE)
    hero(c, M, p.y - 70, bw, '0.14/s', 'בקשות לכל ילד', '34 קריאות במשחק של 4 דקות', AQUA)
    p.y -= 92

    p.h2('מה שנמדד: כמה נטענים בשנייה, לפי כמה בו זמנית', 4)
    GUT = 62                      # room for the direct labels, inside the page
    cw = W - 2 * M - 46 - GUT
    px, py = axes(c, M + 40, p.y - 150, cw, 140, CONC, 140,
                  'בקשות בשנייה', 'כמה בקשות במקביל')
    line_series(c, px, py, [v for v in STATIC if v is not None], BLUE, 'Cloudflare')
    line_series(c, px, py, SUPA, AQUA, 'Supabase')
    line_series(c, px, py, [v for v in REND if v is not None], ORANGE, 'Render')
    p.y -= 194
    p.note('שלושת הקווים מגיעים לרמה ואז יורדים. הירידה של Cloudflare ו-Render היא של מכונת המדידה,')
    p.note('שהיא בעלת שני מעבדים בלבד וה-CPU שלה ירד ל-27% פנוי. Supabase הוא היחיד שנצפתה בו האטה אמיתית.')

    p.h2('אותו ניסוי, אבל כמה זמן ילד מחכה', 10)
    px, py = axes(c, M + 40, p.y - 130, cw, 120, CONC, 3.2,
                  'זמן המתנה בשניות, p95', 'כמה בקשות במקביל', yfmt='{:.1f}')
    line_series(c, px, py, P95_STATIC[:5], BLUE, 'Cloudflare', nudge=-7)
    line_series(c, px, py, P95_SUPA, AQUA, 'Supabase')
    line_series(c, px, py, P95_REND[:5], ORANGE, 'Render', nudge=6)
    c.setStrokeColor(BAD); c.setLineWidth(1); c.setDash([3, 3])
    c.line(M + 40, py(2.0), M + 40 + cw, py(2.0)); c.setDash([])
    c.setFillColor(BAD); c.setFont('S', 7.5)
    c.drawString(M + 44, py(2.0) + 4, he('הגבול שקבענו: 2 שניות'))
    p.y -= 174
    p.note('ב-64 בקשות במקביל, Supabase חוצה שתי שניות. שם עובר הגבול, ובלי שגיאה אחת —')
    p.note('הבקשות פשוט ממתינות בתור. ילד רואה מסך שנעצר, לא הודעת שגיאה.')

    p.h2('איך מגיעים מזה ל-600', 6)
    p.p('משחק של עשר שאלות עושה 34 קריאות ל-Supabase לאורך כארבע דקות, כלומר 0.14 בשנייה לילד.')
    p.p('Supabase עמד ב-90 בקשות בשנייה בלי שגיאות, ו-90 חלקי 0.14 הוא כ-600 ילדים במקביל.')
    p.note('וזו רצפה, לא תקרה: המדידה נחסמה על ידי מכונת המדידה. הכלי מוכן להרצה ממכונה גדולה יותר.')


def page2(c):
    p = Page(c, 'לפי גודל השרת', 'מה גודל השרת באמת קונה, ומה לא', 2)
    p.p('הנקודה החשובה קודם: **גודל השרת לא משפיע על המשחקים בכלל.**'.replace('**', ''))
    p.p('המשחקים אינם נוגעים ב-Render. הם קבצים סטטיים מ-Cloudflare, ובסיס נתונים ב-Supabase.')
    p.p('שרת גדול יותר לא יוסיף אפילו שחקן אחד. רק שדרוג של Supabase יוסיף.')
    p.y -= 6

    p.h2('הטיוטור: מה כל שדרוג קונה', 8)
    p.p('כל 19 הנתיבים בטיוטור העברי מוגדרים כ-def רגיל ולא async. FastAPI מריץ כזה בבריכה')
    p.p('של 40 חוטים, וכל בקשה תופסת חוט לכל אורך קריאת המודל — שניות, לא אלפיות.')
    p.y -= 4

    rows = [
        [('Starter', INK), '512MB · 0.5 CPU', '1', ('~40', INK), ('~10', INK)],
        [('Standard', INK), '2GB · 1 CPU', '4', ('~160', INK), ('~40', INK)],
        [('Pro', INK), '4GB · 2 CPU', '8', ('~320', INK), ('~80', INK)],
        [('Pro Plus', INK), '8GB · 4 CPU', '16', ('~640', INK), ('~160', INK)],
    ]
    y2 = table(c, M, p.y, W - 2 * M,
               ['תוכנית Render', 'משאבים', 'עובדים', 'בקשות במקביל', 'בקשות/שנייה'],
               rows, [0.20, 0.26, 0.14, 0.20, 0.20])
    p.y = y2 - 14
    p.note('ההנחות: כ-400MB לעובד עם הספריות של OpenAI, Gemini ו-Supabase טעונות; 40 חוטים לעובד;')
    p.note('כארבע שניות לקריאת מודל. המספרים מתקבלים מ-40 חוטים חלקי 4 שניות לכל עובד.')
    p.y -= 8

    p.h2('אבל אם מתקנים את הקוד', 8)
    p.p('נתיב שמוגדר async ומחכה למודל במקום לחסום, מחזיר את החוט בזמן שהמודל חושב.')
    p.p('אז מספר החוטים מפסיק להיות התקרה, והתקרה עוברת למגבלת הקצב של ספק המודל.')
    p.y -= 6

    cw = (W - 2 * M - 18) / 2
    bh = 112
    bars(c, M + 40 + cw + 18, p.y - bh, cw - 40, bh,
         [('Starter', 10, ORANGE), ('Standard', 40, ORANGE), ('Pro', 80, ORANGE), ('Pro Plus', 160, ORANGE)],
         180, 'היום · def רגיל', 'בקשות/שנייה')
    bars(c, M + 40, p.y - bh, cw - 40, bh,
         [('Starter', 250, GOOD), ('Standard', 250, GOOD), ('Pro', 250, GOOD), ('Pro Plus', 250, GOOD)],
         300, 'אחרי async · מוגבל בספק', 'בקשות/שנייה')
    p.y -= bh + 34
    p.note('אחרי async, כל ארבע התוכניות מגיעות לאותו מספר, כי הגבול כבר אינו השרת אלא ספק המודל.')
    p.note('שינוי קוד של יום עבודה שווה יותר מכל שדרוג חומרה שאפשר לקנות.')

    p.h2('מה נשבר ראשון, לפי הסדר', 10)
    for i, t in enumerate([
        'הטיוטור, בכ-40 משתמשים במקביל — בקשות נכנסות לתור וילד רואה מסך שנעצר.',
        'כתיבות ל-Supabase, בכמה מאות שחקנים — כל תשובה כותבת שלוש שורות.',
        'קריאות מ-Supabase, סביב 600 שחקנים — כפי שנמדד.',
        'Cloudflare — לא צפוי להישבר בשום סדר גודל שרלוונטי כאן.',
    ]):
        p.p(f'{i + 1}.  {t}')


def page3(c):
    p = Page(c, 'הארכיטקטורה שתסיר את התקרה', 'מה יש היום, ומה צריך כדי לא להיות מוגבל', 3)

    # ---- today
    p.h2('היום: שני מסלולים נפרדים', 4)
    y0 = p.y - 118
    cw = (W - 2 * M - 24) / 2
    node(c, W - M - cw, y0, cw, 108, 'מסלול המשחקים  ✓',
         ['הדפדפן ← Cloudflare (קבצים סטטיים)', 'הדפדפן ← Supabase (התקדמות)',
          'לא נוגע בשרת כלל', 'תקרה: כ-600 במקביל'], AQUA, HexColor('#f2fbf7'))
    node(c, M, y0, cw, 108, 'מסלול הטיוטור  ✗',
         ['הדפדפן ← Render (FastAPI)', 'Render ← OpenAI / Gemini',
          'def רגיל: 40 חוטים חוסמים', 'תקרה: כ-40 במקביל'], ORANGE, HexColor('#fff6f1'))
    p.y = y0 - 18
    p.note('אותו אתר, שתי תקרות שרחוקות זו מזו פי חמישה עשר. כל עוד זה כך, "כמה משתמשים"')
    p.note('היא שאלה בלי תשובה אחת — היא תלויה במה הילד עושה באותו רגע.')

    # ---- target
    p.h2('היעד: מה משנים, ומה זה נותן', 12)
    yy = p.y - 150
    bwd = (W - 2 * M - 30) / 3
    node(c, W - M - bwd, yy + 76, bwd, 62, '1 · נתיבים async',
         ['await במקום חסימה', 'החוט חוזר בזמן ההמתנה'], AQUA, HexColor('#f2fbf7'))
    node(c, W - M - 2 * bwd - 15, yy + 76, bwd, 62, '2 · תור לעבודה ארוכה',
         ['יצירת שיעור ← תור', 'התשובה נאספת בהמשך'], AQUA, HexColor('#f2fbf7'))
    node(c, M, yy + 76, bwd, 62, '3 · הגבלת קצב לכל משתמש',
         ['לשונית בלולאה לא', 'תיקח את כל השרת'], AQUA, HexColor('#f2fbf7'))
    node(c, W - M - bwd, yy, bwd, 62, '4 · מטמון לתשובות חוזרות',
         ['שיעור שכבר נוצר', 'הקראה שכבר יוצרה'], BLUE, HexColor('#f3f8fe'))
    node(c, W - M - 2 * bwd - 15, yy, bwd, 62, '5 · יותר עובדים',
         ['רק אחרי async —', 'אחרת רק מכפילים זיכרון'], BLUE, HexColor('#f3f8fe'))
    node(c, M, yy, bwd, 62, '6 · Supabase גדול יותר',
         ['הדבר היחיד שמזיז', 'את תקרת המשחקים'], BLUE, HexColor('#f3f8fe'))
    p.y = yy - 18

    p.h2('לא מוגבל, באמת', 10)
    p.p('"בלי הגבלה" אינו קיים, אבל אפשר להעביר את הגבול למקום שקונים בכסף ולא בעבודה:')
    p.y -= 4
    rows = [
        [('קבצים סטטיים', INK), 'Cloudflare — כבר שם', ('אינסופי למעשה', GOOD)],
        [('התקדמות ילדים', INK), 'Supabase, שדרוג תוכנית', ('אלפים', GOOD)],
        [('קריאות מודל', INK), 'async + תור + מטמון', ('מגבלת הספק', WARN)],
        [('עומס פתאומי', INK), 'תור מפריד בין קליטה לעיבוד', ('לא נופל, רק מאט', GOOD)],
    ]
    y2 = table(c, M, p.y, W - 2 * M, ['מה', 'איך', 'התקרה החדשה'], rows, [0.26, 0.44, 0.30])
    p.y = y2 - 16
    p.p('הסדר הנכון: הגבלת קצב היום, async אחריה, ותור רק כשבאמת צריך.')
    p.note('שלושת הראשונים הם קוד ואינם עולים כלום בחומרה. שלושת האחרונים הם כסף.')
    p.note('אין טעם לשלם על אף אחד מהאחרונים לפני שהראשונים נעשו.')


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else '/opt/iakids/tools/iakids-capacity.pdf'
    c = canvas.Canvas(out, pagesize=A4)
    c.setTitle('iakids — capacity and architecture')
    c.setAuthor('iakids.app')
    for fn in (page1, page2, page3):
        fn(c); c.showPage()
    c.save()
    print(f'{out}  ({os.path.getsize(out) / 1024:.0f} KB, 3 pages)')


if __name__ == '__main__':
    main()
