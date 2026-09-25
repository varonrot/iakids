#!/usr/bin/env python3
"""Hebrew PDF summary of the performance work: API, children at once, handling times, machines, architecture.

    backend/.venv/bin/python performance/report_pdf.py      # -> performance/results/iakids-performance-he.pdf

Tables are read from the result files (before/after on the fake and on the production database);
the prose is the summary of performance/REPORT.md. Hebrew is wrapped into lines FIRST and each line
is then reordered with python-bidi: reportlab draws glyphs in the order it gets them, and reordering
a whole paragraph before wrapping would put its lines in the wrong order.
"""
import json
from pathlib import Path

from bidi.algorithm import get_display
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
OUT = RES / "iakids-performance-he.pdf"
FONTS = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("S", f"{FONTS}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("SB", f"{FONTS}/DejaVuSans-Bold.ttf"))

INK, INK2, MUTED = HexColor("#14213d"), HexColor("#33415c"), HexColor("#6b7a90")
LINE, SOFT = HexColor("#d9e1ec"), HexColor("#f3f6fa")
GOOD, BAD, ACCENT, WARN = HexColor("#1b8a5a"), HexColor("#c0392b"), HexColor("#1f6feb"), HexColor("#b7791f")
W, H = A4
M = 40                      # page margin
RIGHT = W - M


def load(name):
    return json.loads((RES / name).read_text())


PROD_B = load("20260925-064153-before-prod.json")["routes"]
PROD_A = load("20260925-063742-after-prod.json")["routes"]
FAKE_B = load("20260925-060414-before-fake.json")["routes"]
FAKE_A = load("20260925-061442-after-fake.json")["routes"]


def vis(s):
    return get_display(str(s))


def wrap(text, font, size, width):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(t, font, size) <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


class Doc:
    def __init__(self, path):
        self.c = canvas.Canvas(str(path), pagesize=A4)
        self.c.setTitle("iakids — ביצועים וקיבולת ה-API")
        self.page = 0
        self.new_page()

    def new_page(self):
        if self.page:
            self.c.showPage()
        self.page += 1
        self.y = H - M
        c = self.c
        c.setFillColor(MUTED); c.setFont("S", 7.5)
        c.drawRightString(RIGHT, 22, vis(f"iakids · ביצועים וקיבולת ה-API של המורה · 25.09.2026 · עמוד {self.page}"))
        c.drawString(M, 22, "performance/REPORT.md")

    def need(self, h):
        if self.y - h < 45:
            self.new_page()

    def title(self, t, sub):
        c = self.c
        c.setFillColor(INK); c.setFont("SB", 18)
        for ln in wrap(t, "SB", 18, W - 2 * M):
            c.drawRightString(RIGHT, self.y - 18, vis(ln)); self.y -= 24
        self.y -= 4
        c.setFillColor(MUTED); c.setFont("S", 9.5)
        for ln in wrap(sub, "S", 9.5, W - 2 * M):
            c.drawRightString(RIGHT, self.y - 10, vis(ln)); self.y -= 13
        self.y -= 6
        c.setStrokeColor(LINE); c.setLineWidth(1); c.line(M, self.y, RIGHT, self.y); self.y -= 10

    def h2(self, t, gap=10):
        self.need(40)
        self.y -= gap
        c = self.c
        c.setFillColor(ACCENT); c.rect(RIGHT - 3, self.y - 15, 3, 14, stroke=0, fill=1)
        c.setFillColor(INK); c.setFont("SB", 12.5)
        c.drawRightString(RIGHT - 9, self.y - 13, vis(t)); self.y -= 22

    def p(self, t, size=9.2, color=None, font="S", lead=None, indent=0):
        lead = lead or size * 1.45
        lines = wrap(t, font, size, W - 2 * M - indent)
        self.need(len(lines) * lead + 2)
        c = self.c
        c.setFillColor(color or INK2); c.setFont(font, size)
        for ln in lines:
            c.drawRightString(RIGHT - indent, self.y - size, vis(ln)); self.y -= lead
        self.y -= 3

    def bullets(self, items, size=9.0):
        for it in items:
            lines = wrap(it, "S", size, W - 2 * M - 14)
            lead = size * 1.45
            self.need(len(lines) * lead + 2)
            c = self.c
            c.setFillColor(ACCENT); c.circle(RIGHT - 3, self.y - size * 0.62, 1.8, stroke=0, fill=1)
            c.setFillColor(INK2); c.setFont("S", size)
            for ln in lines:
                c.drawRightString(RIGHT - 12, self.y - size, vis(ln)); self.y -= lead
            self.y -= 2

    def cards(self, items):
        """big-number cards, right to left"""
        n = len(items)
        gap = 8
        w = (W - 2 * M - gap * (n - 1)) / n
        h = 74
        self.need(h + 8)
        c = self.c
        for i, (big, label, sub, color) in enumerate(items):
            x = RIGHT - (i + 1) * w - i * gap
            c.setFillColor(SOFT); c.setStrokeColor(LINE); c.roundRect(x, self.y - h, w, h, 6, stroke=1, fill=1)
            size = 17
            while size > 10 and pdfmetrics.stringWidth(big, "SB", size) > w - 12:
                size -= 0.5
            c.setFillColor(color); c.setFont("SB", size)
            c.drawCentredString(x + w / 2, self.y - 26, vis(big))
            c.setFillColor(INK); c.setFont("SB", 8.4)
            for k, ln in enumerate(wrap(label, "SB", 8.4, w - 10)[:2]):
                c.drawCentredString(x + w / 2, self.y - 41 - k * 10.5, vis(ln))
            c.setFillColor(MUTED); c.setFont("S", 7.2)
            for k, ln in enumerate(wrap(sub, "S", 7.2, w - 10)[:1]):
                c.drawCentredString(x + w / 2, self.y - h + 9, vis(ln))
        self.y -= h + 12

    def table(self, header, rows, widths, size=8.2, bold_col=None, shade_first=True):
        """columns listed right to left; widths are fractions of the text width"""
        total = W - 2 * M
        ws = [f * total for f in widths]
        c = self.c
        rh = size * 2.05

        def row(cells, font, fill=None, color=INK2):
            fonts = ["SB" if (bold_col is not None and j == bold_col and font == "S") else font for j in range(len(cells))]
            lines_per = [wrap(str(x), f, size, w - 8) for x, w, f in zip(cells, ws, fonts)]
            h = max(len(l) for l in lines_per) * size * 1.3 + 7
            self.need(h + 2)
            if fill:
                c.setFillColor(fill); c.rect(M, self.y - h, total, h, stroke=0, fill=1)
            x = RIGHT
            for j, (lines, w) in enumerate(zip(lines_per, ws)):
                f = "SB" if (bold_col is not None and j == bold_col and font == "S") else font
                c.setFillColor(color); c.setFont(f, size)
                for k, ln in enumerate(lines):
                    c.drawRightString(x - 4, self.y - 4 - size - k * size * 1.3, vis(ln))
                x -= w
            self.y -= h
            c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(M, self.y, RIGHT, self.y)

        row(header, "SB", fill=HexColor("#e8eef7"), color=INK)
        for i, r in enumerate(rows):
            row(r, "S", fill=SOFT if (shade_first and i % 2) else None)
        self.y -= 8

    def boxes(self, rows):
        """a simple top-to-bottom diagram: each row is a list of (label, color)"""
        c = self.c
        bh, gap = 26, 14
        self.need(len(rows) * (bh + gap) + 4)
        for r, items in enumerate(rows):
            n = len(items)
            w = min(320 if n == 1 else 160, (W - 2 * M - 10 * (n - 1)) / n)
            span = n * w + (n - 1) * 10
            x0 = W / 2 + span / 2
            for i, (label, color) in enumerate(items):
                x = x0 - (i + 1) * w - i * 10
                c.setFillColor(color); c.roundRect(x, self.y - bh, w, bh, 5, stroke=0, fill=1)
                c.setFillColor(HexColor("#ffffff")); c.setFont("SB", 7.6)
                lines = wrap(label, "SB", 7.6, w - 8)[:2]
                for k, ln in enumerate(lines):
                    c.drawCentredString(x + w / 2, self.y - bh / 2 + 3 - k * 9 + (len(lines) - 1) * 4.5, vis(ln))
            self.y -= bh
            if r < len(rows) - 1:
                c.setStrokeColor(MUTED); c.setLineWidth(1)
                c.line(W / 2, self.y - 1, W / 2, self.y - gap + 3)
                c.setFillColor(MUTED)
                p = c.beginPath(); p.moveTo(W / 2 - 3, self.y - gap + 5); p.lineTo(W / 2 + 3, self.y - gap + 5); p.lineTo(W / 2, self.y - gap + 1); p.close()
                c.drawPath(p, stroke=0, fill=1)
            self.y -= gap
        self.y -= 2

    def save(self):
        self.c.save()


def step(r, conc):
    s = [x for x in r.get("steps", []) if x["conc"] == conc]
    return s[0] if s else None


def best(r):
    ok = [s for s in r.get("steps", []) if not s.get("broke")]
    return ok[-1] if ok else None


def n(x, nd=0):
    return "-" if x is None else f"{x:,.{nd}f}"


d = Doc(OUT)

# ------------------------------------------------------------------ page 1: the answer
d.title("כמה ילדים ה-API של המורה מחזיק — לפני ואחרי השינויים",
        "סיכום בדיקות העומס של backend-ai-tutor-he, 25.09.2026. נמדד על השרת הנוכחי (2 ליבות, 2GB, ניו יורק) עם עותק נפרד "
        "של השרת, בסיס נתונים מדומה וגם בסיס הנתונים האמיתי (קריאה בלבד, עם הגבלה). המטרה שהוגדרה: יותר מ-100,000 ילדים בו-זמנית.")
d.cards([
    ("177", "ילדים בשיעור לכל ליבת מעבד", "היה 155", GOOD),
    ("-54%", "קריאות לבסיס הנתונים לכל ילד", "27.7 ← 12.8 בדקה", GOOD),
    ("x2.5–6", "בקשות בשנייה על בסיס הנתונים האמיתי", "6 נתיבי קריאה", GOOD),
    ("14,000 → 25", "השהיית כל השרת בזמן צ'אט, מ״ש", "הצ'אט הראשי", GOOD),
    ("+58%", "מליבה שנייה", "השרת גדל עם הליבות", ACCENT),
])
d.h2("השורה התחתונה")
d.bullets([
    "לפני: תהליך אחד של השרת החזיק כ-155 ילדים בשיעור. פתיחת שיעור ע\"י 8 ילדים יחד הקפיאה את כל השרת לחצי שנייה, והצ'אט הראשי הקפיא את כל שאר הילדים עד 14 שניות תחת עומס.",
    "אחרי: כ-177 ילדים לליבה, 54% פחות קריאות לבסיס הנתונים לכל ילד, והנתיבים שמסך השיעור שואל שוב ושוב עונים פי 2.5 עד 6 יותר בקשות בשנייה, בשליש מהזמן.",
    "השרת גדל עם הליבות: מעבר מליבה אחת לשתיים נתן +58% באותם נתיבים. כל תהליך נוסף עולה כ-170MB זיכרון.",
    "100,000 ילדים בו-זמנית זה כ-560 ליבות עסוקות, כ-21,000 קריאות לבסיס הנתונים בשנייה ואלפי קריאות למודלים בשנייה. זה לא שרת אחד גדול יותר — זו ארכיטקטורה אחרת (עמוד 4). בגודל כזה החשבון על המודלים, לא השרתים, הוא התקרה.",
    "העבודה הכבדה צריכה לצאת מהמכונה שהילדים מדברים איתה: קודם ה-worker של המדיה (בלי שינוי קוד), אחר כך נתיבי ה-AI לקבוצת שרתים משלהם.",
])
d.h2("מה שונה בקוד (עדיין לא הועלה — מחכה לאישור)")
d.table(["שינוי", "איפה", "מה זה נתן"], [
    ["בדיקת הכניסה (token) מקומית מול המפתח הציבורי של הפרויקט במקום פנייה ל-Supabase", "request_cache.py, authenticate_user", "קריאה אחת פחות לבסיס הנתונים בכל בקשה"],
    ["שורת הילד נשמרת 60 שנ׳ (נמחקת בעדכון פרטי ילד)", "get_child_by_id", "עוד קריאה אחת פחות כמעט בכל בקשה"],
    ["מנוי 60 שנ׳, שורת תוכנית לימודים 5 דק׳", "is_paid_active_subscription, get_learning_lesson", "פתיחת שיעור: 10 ← 3 קריאות"],
    ["אותה משימת מדיה לא נשלחת שוב תוך 60 שנ׳", "enqueue_media_job", "פתיחת שיעור לא שולחת 3 משימות בכל בדיקה"],
    ["3 נתיבים כבר לא מחכים לרשת בתוך לולאת השרת", "openai_clean_chat, homework_coach_v2, unit-lesson", "פתיחת שיעור 0.7 ← 25.7 בקשות/שנ׳; הצ'אט לא מקפיא"],
], [0.46, 0.27, 0.27], size=7.9)
d.p("המחיר היחיד: אחרי התנתקות, כניסה נשארת בתוקף עד שה-token פג (עד שעה) — כמו בכל לקוח Supabase שבודק מקומית. "
    "AUTH_LOCAL_JWT=0 מבטל את זה, REQUEST_CACHE=0 מבטל את כל המטמונים.", size=8.3, color=MUTED)

# ------------------------------------------------------------------ page 2: before/after numbers
d.new_page()
d.title("לפני ← אחרי, במספרים", "זמן טיפול (latency) ותפוקה לכל נתיב. p50 = הזמן שחצי מהבקשות עומדות בו, p95 = 95% מהבקשות.")
d.h2("בסיס הנתונים האמיתי (אותם 6 נתיבי קריאה, אותו שרת, 06:37–06:45 UTC)")
d.p("בכל תא מספרי: לפני → אחרי.", size=8.2, color=MUTED)
rows = []
for k in PROD_A:
    b, a = PROD_B[k], PROD_A[k]
    b1, a1, b8, a8 = step(b, 1), step(a, 1), step(b, 8), step(a, 8)
    rows.append([k, f"{n(b1 and b1['p50'])} → {n(a1 and a1['p50'])}", f"{n(b8 and b8['rps'], 1)} → {n(a8 and a8['rps'], 1)}",
                 f"{n(b8 and b8['p95'])} → {n(a8 and a8['p95'])}", f"{b.get('cpu_ms_per_req', 0):.1f} → {a.get('cpu_ms_per_req', 0):.1f}",
                 f"{b['db_calls']} → {a['db_calls']}"])
d.table(["נתיב", "משתמש אחד, מ״ש", "בקשות/שנ׳ ב-8 משתמשים", "p95 ב-8 משתמשים, מ״ש", "CPU לבקשה, מ״ש", "קריאות DB לבקשה"],
        rows, [0.2, 0.16, 0.18, 0.17, 0.14, 0.15], size=8, bold_col=0)
d.p("בקוד הישן התהליך עמד על 30–39% CPU בזמן שהתפוקה נשארה שטוחה: הוא חיכה לנסיעות הלוך-חזור ל-Supabase. "
    "בקוד החדש אותם נתיבים מביאים את המעבד ל-50–95% — המגבלה היא עכשיו המכונה, ואת זה אפשר לקנות. "
    "השירות החי נשאר בחציון 11–12 מ״ש בשתי הבדיקות; משתמשי הבדיקה נמחקו.", size=8.5)

d.h2("כל סוגי הנתיבים (בסיס נתונים מדומה, 100 מ״ש לקריאה, זמני מודלים כמו בפרודקשן)")
d.p("בכל תא מספרי: לפני → אחרי.", size=8.2, color=MUTED)
rows = []
for k in ["unit-lesson", "visuals", "audio", "hero-image", "tts", "kid-get", "check-set", "structured-lesson", "tutor-chat", "openai-clean-chat"]:
    b, a = FAKE_B[k], FAKE_A[k]
    bb, ab = best(b), best(a)
    lag_b = max([s["loop_lag_p95_ms"] for s in b.get("steps", [])] or [0])
    lag_a = max([s["loop_lag_p95_ms"] for s in a.get("steps", [])] or [0])
    rps = f"{n(bb and bb['rps'], 1)} → {n(ab and ab['rps'], 1)}"
    if (bb and bb["rps"]) == 0 and (ab and ab["rps"]) == 0:
        rps = "-"          # the fake model takes 20 s, longer than the step: throughput not measured
    rows.append([k, a["kind"], rps,
                 f"{n(b.get('cpu_ms_per_req'), 0)} → {n(a.get('cpu_ms_per_req'), 0)}",
                 f"{b['db_calls']} → {a['db_calls']}", f"{n(lag_b)} → {n(lag_a)}"])
d.table(["נתיב", "סוג", "בקשות/שנ׳ בשיא תקין", "CPU לבקשה, מ״ש", "קריאות DB", "השהיית כל השרת (מקס׳), מ״ש"],
        rows, [0.22, 0.1, 0.19, 0.16, 0.13, 0.2], size=7.9, bold_col=0)
d.p("\"השהיית כל השרת\" = כמה זמן בקשה פשוטה של ילד אחר חיכתה בזמן העומס. בצ'אט הראשי זה ירד מ-14 שניות ל-25 מ״ש ב-256 משתמשים בו-זמנית "
    "(התפוקה שלו לא נמדדה: המודל המדומה עונה אחרי 20 שנ׳, יותר משלב הבדיקה).",
    size=8.3, color=MUTED)

d.h2("זמני טיפול בפרודקשן (מדידות קודמות, 14–16.09, מתוך ai_calls ויומני השרת)")
d.table(["פעולה", "זמן", "הערה"], [
    ["תשובת צ'אט של המורה", "4.5–6 שניות (חציון)", "רובו המודל"],
    ["יצירת שיעור חדש (טקסט)", "70–92 שניות", "Visual Director לבד 14–46 שנ׳"],
    ["קול ראשון בשיעור חדש", "כ-107 שניות", "הקול מוגש רק כשכל החלקים מוכנים"],
    ["משימת מדיה (תמונות + קול)", "68–339 שניות", "ב-worker, לא בבקשה של הילד"],
    ["קריאה פשוטה ל-DB (אחרי השינוי)", "120–130 מ״ש", "רובו נסיעה הלוך-חזור לאזור של Supabase"],
    ["נתיב שכבר במטמון (אחרי השינוי)", "5 מ״ש", "check-set, kid-get"],
], [0.36, 0.26, 0.38], size=8.2, bold_col=0)

# ------------------------------------------------------------------ page 3: users, machines, cost
d.new_page()
d.title("כמה משתמשים, על איזו מכונה, ובכמה", "ילד אחד בשיעור בדקה (לפי תמהיל הבקשות של מסך השיעור): 4 בדיקות סטטוס, תשובה אחת, חצי הודעת צ'אט, קריאת טקסט בקול ועוד.")
d.table(["", "לפני", "אחרי"], [
    ["זמן מעבד של השרת לילד בדקה", "270 מ״ש", "238 מ״ש"],
    ["קריאות לבסיס הנתונים לילד בדקה", "27.7", "12.8 (-54%)"],
    ["ילדים לכל ליבה (70% ניצול)", "155", "177"],
], [0.5, 0.25, 0.25], size=8.6, bold_col=0)
d.p("זמן המעבד לילד ירד פחות מהנתיבים עצמם, כי דקה של ילד נשלטת ע\"י נתיבי ה-AI (תשובות בשיעור, צ'אט) — 80–126 מ״ש של המעבד שלנו לכל קריאה, "
    "בערך 3–4 מ״ש לכל קריאת רשת יוצאת כפול כ-10 קריאות DB וקריאת מודל. זה המנוף הבא.", size=8.4)

d.h2("ליבות וזיכרון — נמדד")
d.table(["", "ליבה אחת, תהליך אחד", "2 ליבות, 2 תהליכים"], [
    ["kid-get בשיא", "222 בקשות/שנ׳", "349 בקשות/שנ׳ (+58%)"],
    ["check-set בשיא", "194 בקשות/שנ׳", "277 בקשות/שנ׳ (+43%)"],
    ["זיכרון (RSS)", "178MB", "348MB (כ-170MB לתהליך)"],
], [0.34, 0.33, 0.33], size=8.6, bold_col=0)
d.p("במדידה עם 2 ליבות, מחולל העומס, השרתים המדומים והפרודקשן חלקו את אותן ליבות — במכונה עם ליבות פנויות הרווח לליבה גבוה יותר.", size=8.2, color=MUTED)

d.h2("מה כל מכונה תחזיק (אחרי השינויים, לפי מעבד)")
sizes = [("s-2vcpu-2gb (היום)", "2 / 2GB", "$18", "1", "כ-176"), ("s-2vcpu-4gb", "2 / 4GB", "$24", "1–2", "כ-176–350"),
         ("s-4vcpu-8gb", "4 / 8GB", "$48", "3", "כ-530"), ("c-4 (ליבות ייעודיות)", "4 / 8GB", "$84", "3", "כ-530, יציב יותר"),
         ("s-8vcpu-16gb", "8 / 16GB", "$96", "7", "כ-1,240"), ("c-8 (ליבות ייעודיות)", "8 / 16GB", "$168", "7", "כ-1,240, יציב"),
         ("c-16 (ליבות ייעודיות)", "16 / 32GB", "$336", "15", "כ-2,650")]
d.table(["מכונה ב-DigitalOcean", "ליבות / זיכרון", "לחודש", "תהליכי שרת", "ילדים בשיעור בו-זמנית"], [list(s) for s in sizes],
        [0.3, 0.17, 0.12, 0.14, 0.27], size=8.3, bold_col=0)
d.p("תהליך אחד לכל ליבה, ליבה אחת נשמרת ל-worker של המדיה, nginx ומערכת ההפעלה. מחירים מדף המחירים של DigitalOcean, 25.09.2026 (חיוב לפי שנייה). "
    "ליבות Basic זולות יותר אבל משותפות עם שכנים; CPU-Optimized ייעודיות — לשירות שהמגבלה שלו מעבד, זה זמן תגובה צפוי.", size=8.2, color=MUTED)
d.p("השרת של היום מריץ גם MongoDB, Docker, Cursor ו-Claude (כ-580MB), עם כ-780MB פנויים ו-1GB כבר ב-swap. פרודקשן לא צריך לחלוק מכונה עם כלי פיתוח.", size=8.4)

d.h2("100,000 ילדים בו-זמנית — מה זה אומר")
d.bullets([
    "כ-566 ליבות עסוקות של שרת (כ-80 מכונות c-8, כ-$13,000 לחודש) — או פי 3–5 פחות אחרי המשימות ברשימה.",
    "כ-21,000 קריאות לבסיס הנתונים בשנייה. Supabase נתן כ-600–1,000 בשנייה במדידה של 10.09 — צריך מחשוב גדול בהרבה, העתקי קריאה, והרבה פחות קריאות לילד.",
    "2,500–5,000 קריאות למודלים בשנייה — מעבר למגבלות ברירת המחדל של הספקים. הערכה גסה (1,500 טוקנים פנימה / 300 החוצה): כ-$0.20 לילד לשעה, כלומר כ-$20,000 לשעה ב-100k. צריך למדוד מ-ai_calls לפני שמתכננים.",
], size=8.8)

# ------------------------------------------------------------------ page 4: architecture
d.new_page()
d.title("ארכיטקטורה: להעביר את ה-API הכבד לשרת אחר?", "יש בשרת שלושה סוגי עבודה שונים מאוד, והם מפריעים אחד לשני כשהם על אותה מכונה.")
d.table(["סוג", "דוגמאות", "מעבד לבקשה", "מחכה ל-", "כמה לילד"], [
    ["בדיקות סטטוס וקריאות", "visuals, audio, active-lesson-state, דפי ילד", "5–20 מ״ש", "בסיס הנתונים", "גבוה (כ-4 בדקה)"],
    ["נתיבי AI", "תשובות בשיעור, צ'אט, שיעורי בית, הקראה", "80–126 מ״ש", "המודל, 2–20 שנ׳", "בינוני (כ-3 בדקה)"],
    ["יצירת מדיה", "תמונות, סרטוני פתיחה, קול השיעור", "פרצים כבדים, כ-200MB", "מודלי תמונה/קול, 1–5 דק׳", "לשיעור, לא לילד"],
], [0.2, 0.3, 0.15, 0.18, 0.17], size=8, bold_col=0)
d.p("היום זה נראה: עומס הבדיקה על אותה מכונה העלה את ה-p95 של השירות החי מ-12 ל-660 מ״ש.", size=8.4, color=BAD)

d.h2("איך מחברים הרבה שרתים לאותו שם (DNS)")
d.boxes([
    [("iakids.app ב-Cloudflare: DNS, TLS, מטמון וחוקי קצב", HexColor("#f38020"))],
    [("Load Balancer של DigitalOcean: $12 לחודש, בדיקת בריאות", ACCENT)],
    [("שרת web 1", INK2), ("שרת web 2", INK2), ("עוד שרתים לפי עומס: Autoscale", INK2)],
    [("Supabase: DB + Auth + Storage", GOOD), ("Valkey: מטמון משותף, $15", WARN), ("שרת worker למדיה", HexColor("#6f42c1"))],
])
d.p("רשומת DNS אחת מצביעה על ה-Load Balancer (או Cloudflare מעביר אליו). השרתים מאחוריו נמצאים לפי תגית, כך ש-Autoscale Pool יכול להוסיף ולהוריד "
    "שרתים לפי מעבד (למשל יעד 60%). דרוש: snapshot עם שירותי systemd, מפתחות SSH, ושרת בלי מצב פנימי. שים לב: חשבון DigitalOcean חדש מוגבל ל-3 מכונות — צריך לבקש הגדלה מראש.",
    size=8.4)

d.h2("ההמלצה, לפי הסדר — והאם זה טוב")
d.table(["", "מה", "האם כדאי", "איך"], [
    ["א", "worker המדיה לשרת משלו", "כן, עכשיו. סיכון נמוך", "אותו קוד, systemd על מכונה שנייה ($24). בלי שינוי קוד"],
    ["ב", "שרת בלי מצב פנימי", "חובה לפני תהליך/שרת שני", "EXAM_SETS ומגביל הקצב ל-Valkey או לטבלה"],
    ["ג", "כמה שרתי web מאחורי שם אחד", "כן, אחרי ב", "Load Balancer + Autoscale Pool"],
    ["ד", "נתיבי AI לקבוצת שרתים משלהם", "כן, כששרת אחד לא מספיק", "חוק ניתוב לפי נתיב, בלי שינוי קוד"],
    ["ה", "יצירת שיעור חדש לתור", "כן", "אף בקשה לא מחזיקה 90 שנ׳ של מודל"],
    ["ו", "תוכן השיעור ב-Cloudflare", "כן, פי כמה", "התוכן זהה לכל הילדים: JSON עם גרסה"],
    ["ז", "דחיפה במקום בדיקות חוזרות", "כן", "SSE או המתנה ארוכה יותר: כ-שליש מהבקשות"],
    ["✗", "שרת אחד ענק", "לא", "תקרה כ-2,650 ילדים ונקודת כשל יחידה"],
], [0.05, 0.3, 0.27, 0.38], size=8.1, bold_col=1)

# ------------------------------------------------------------------ page 5: to-do
d.new_page()
d.title("רשימת משימות — מדורגת לפי מה שהמדידות אומרות", "כל שורה עם הסיבה הנמדדת שלה.")
todo = [
    ("1", "לבדוק ולהעלות את השינויים של היום", "פי 2.5–6 בקריאות, -54% קריאות DB, הצ'אט לא מקפיא", "מוכן, מחכה לאישור"),
    ("2", "worker המדיה לשרת משלו ($24)", "עומס על המכונה המשותפת: 12 ← 660 מ״ש לשירות החי", "שעה, בלי קוד"),
    ("3", "כלי פיתוח (Cursor, Claude, Mongo, Docker) מחוץ לשרת הפרודקשן", "כ-580MB מתוך 2GB, 1GB ב-swap", "תפעול"),
    ("4", "EXAM_SETS ומגביל הקצב ל-Valkey/DB", "חוסם תהליך או שרת שני", "חצי יום"),
    ("5", "פחות קריאות DB לתשובה בשיעור (10 ← 2–3)", "נתיבי AI הם רוב המעבד לילד (126 מ״ש)", "יום"),
    ("6", "לקוח DB אסינכרוני בנתיבים החמים", "כ-3–4 מ״ש מעבד לכל קריאת רשת", "2–3 ימים"),
    ("7", "שדרוג ל-s-4vcpu-8gb ($48) עם 3 תהליכים (אחרי 4)", "כ-176 ← כ-530 ילדים", "שעה + הפעלה מחדש"),
    ("8", "Load Balancer + 2 שרתים + Autoscale; הגדלת מגבלת החשבון", "בלי נקודת כשל יחידה", "יום"),
    ("9", "יצירת שיעור לתור", "אין בקשה של 70–90 שנ׳", "1–2 ימים"),
    ("10", "תוכן שיעור כ-JSON בקצה של Cloudflare", "מוריד את רוב הקריאות של מסך השיעור", "2–3 ימים"),
    ("11", "SSE / המתנה ארוכה במקום בדיקה כל 1–1.5 שנ׳", "כ-שליש מהבקשות של ילד", "1–2 ימים"),
    ("12", "נתיבי AI לקבוצת שרתים משלהם", "צ'אט עמוס לא מאט את הבדיקות", "חוק ניתוב, אחרי 8"),
    ("13", "Supabase: מחשוב גדול יותר + העתקי קריאה; מדידה מכמה מכונות", "21,000 קריאות/שנ׳ ב-100k", "תכנון + תקציב"),
    ("14", "תוכנית עלות וספקי AI (מטמון, מכסות, הגדלת מגבלות)", "כ-$0.20 לילד לשעה בהערכה", "עסקי"),
    ("15", "ניסיון חוזר אחד על חיבור שנפל ל-Supabase", "\"Server disconnected\" נראה ב-14.09 ובבדיקה היום", "שעה"),
    ("16", "פחות לוגים לכל בקשה בנתיבים החמים", "כ-3% מהמעבד", "שעה"),
]
d.table(["#", "משימה", "למה (נמדד)", "מאמץ"], [list(t) for t in todo], [0.05, 0.42, 0.35, 0.18], size=7.9, bold_col=1)

d.h2("DigitalOcean: API, MCP, Autoscale")
d.bullets([
    "MCP רשמי קיים (droplets.mcp.digitalocean.com, התחברות OAuth): רשימת מכונות, שינוי גודל, Load Balancers, התראות, יתרה וחשבוניות. אין בו גרף מעבד/זיכרון ואין Autoscale Pools — לאלה ה-API.",
    "API: token לקריאה בלבד (droplet:read, monitoring:read, billing:read) קורא מדדי מעבד וזיכרון (דורש do-agent). שינוי גודל מכבה את המכונה — השבתה קצרה.",
    "Autoscale: כן — Droplet Autoscale Pools (יעד מעבד/זיכרון, מינימום/מקסימום) מאחורי Load Balancer. App Platform הוא הדרך עם הכי פחות תפעול.",
], size=8.6)

d.h2("מה יקרה בהעלאה, ומה נבדק")
d.bullets([
    "קבצים: backend-ai-tutor-he/main.py (+70/−16), request_cache.py חדש, tools/prompt_gate.py, תיקיית performance/ חדשה, שורה ב-CLAUDE.md. בלי מיגרציה, בלי תלות חדשה, בלי שינוי ב-frontend.",
    "אחרי deploy: כניסה נבדקת מקומית; שורות ילד/מנוי/תוכנית עד דקה (או 5 דק׳) ישנות; שלושת הנתיבים מפסיקים להקפיא את השרת.",
    "ה-gate עובר, וכל חוק חדש נבדק שהוא נכשל כשמקלקלים: נתיב בלי בדיקת ביצועים, המתנה לרשת בתוך לולאת השרת, חריגה מתקציב קריאות DB, מטמון שהוסר, token פג / מזויף / לקהל אחר / מהסוג הישן, שגיאת תחביר ב-main.py.",
    "לא הועלה כלום: אין commit, push או deploy עד שתאשר.",
], size=8.6)

d.save()
print(f"wrote {OUT} ({d.page} pages)")
