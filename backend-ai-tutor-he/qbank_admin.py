"""Admin review of the question bank (public.qbank_item): see, fix, approve or reject pending items.

New routes only (2026-09-25); main.py imports this module on its last lines and the routes register on the same
`app`, so the gate reads them with main.py (tools/prompt_gate.py ROUTE_MODULES). Every route calls require_admin
(ADMIN_EMAILS on the server; the page holds no list). Page: he/admin/questions-review/.

    GET  /api/admin/qbank/summary                      counts by status, and by subject + grade
    GET  /api/admin/qbank/items?status=&subject=&grade=&topic=&limit=&offset=
                                                       items WITH their answers (admins only) + the topic +
                                                       the validators' findings, computed now
    POST /api/admin/qbank/items/{item_id}/review       {status, note, and optional edits}: edits are validated
                                                       again (qbank/validate.py); an item with problems cannot
                                                       be approved
Nothing here calls a model.
"""
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import Header, HTTPException

from main import REQUEST_FIELD_LIMITS, LimitedRequest, app, require_admin, sb, supabase_with_retry
from qbank import store as qstore
from qbank import validate as qv

# the texts an admin may correct are longer than a child's short fields (LimitedRequest reads this map by key)
REQUEST_FIELD_LIMITS.update({"stem": 1500, "stimulus": 5000, "explain": 2000, "solution_expr": 200})

TABLE = "qbank_item"
STATUSES = ("pending", "approved", "rejected")
_TOPICS: dict = {}
_SOURCES: dict = {}


def _topics() -> dict:
    if not _TOPICS:
        _TOPICS.update(qstore.load_topics())
    return _TOPICS


def _sources() -> dict:
    if not _SOURCES:
        _SOURCES.update(qstore.load_sources())
    return _SOURCES


def _db(operation, label):
    try:
        return supabase_with_retry(operation, label=label)
    except Exception as e:
        if TABLE in repr(e) and ("does not exist" in repr(e) or "PGRST205" in repr(e)):
            raise HTTPException(status_code=503, detail="question bank tables are not set up")
        raise


def _lift(it: dict) -> dict:
    """solution_expr lives in the verification JSON in the table (qbank/store.py); the validators read it at top level."""
    it = dict(it)
    if not it.get("solution_expr"):
        it["solution_expr"] = (it.get("verification") or {}).get("solution_expr")
    return it


def _with_review_info(it: dict) -> dict:
    t = _topics().get(it.get("topic_code")) or {}
    it = _lift(it)
    it["topic"] = {"code": t.get("code"), "title_he": t.get("title_he"), "strand": t.get("strand"), "skills": t.get("skills") or [],
                   "source_url": t.get("source_url"), "inferred": t.get("inferred")}
    it["problems"] = qv.validate_item(it, topic=t or None, sources=_sources())
    return it


class QbankReviewRequest(LimitedRequest):
    status: Literal["pending", "approved", "rejected"]
    note: Optional[str] = None
    stem: Optional[str] = None
    stimulus: Optional[str] = None
    explain: Optional[str] = None
    options: Optional[list[str]] = None
    answer: Optional[int] = None
    why_wrong: Optional[dict[str, str]] = None
    solution_expr: Optional[str] = None
    difficulty: Optional[int] = None


# The admin hub (he/admin/, 2026-09-25): the list of admin pages is served only to admins, so a non-admin sees no
# address at all. "guard" says honestly how each page protects itself today (server = every route checks
# ADMIN_EMAILS; browser = the page itself decides and reads the database directly — to be moved behind the API).
ADMIN_LINKS = [
    {"title": "בדיקת שאלות", "url": "/he/admin/questions-review/", "about": "מאגר השאלות: אישור, דחייה ועריכה של שאלות לפני שהן מגיעות לילדים.", "guard": "server"},
    {"title": "בדיקת שיעורים", "url": "/he/admin/lessons-review/", "about": "איכות השיעורים שנוצרו: תמונות, קול, בדיקה מחדש ואישור.", "guard": "server"},
    {"title": "לוח ניהול", "url": "/he/iakids-admin-dashboard-he/", "about": "שימוש, ילדים ושיחות עם המורה.", "guard": "server check, then direct database reads"},
    {"title": "Admin dashboard (ES)", "url": "/admin/dashboard/", "about": "מנויים (הממשק הספרדי).", "guard": "browser only"},
    {"title": "Support dashboard", "url": "/support-dashboard/", "about": "פניות תמיכה והודעות.", "guard": "browser only"},
]


@app.get("/api/admin/links")
def admin_links(authorization: str = Header(None)):
    user = require_admin(authorization)
    return {"email": str(getattr(user, "email", "") or "").lower(), "links": ADMIN_LINKS}


@app.get("/api/admin/qbank/summary")
def qbank_summary(authorization: str = Header(None)):
    require_admin(authorization)
    rows = _db(lambda: sb.table(TABLE).select("subject,grade,review_status").limit(20000).execute(), "QBANK SUMMARY").data or []
    by_status = {s: 0 for s in STATUSES}
    by_sg: dict = {}
    for r in rows:
        by_status[r["review_status"]] = by_status.get(r["review_status"], 0) + 1
        k = f"{r['subject']}|{r['grade']}"
        by_sg.setdefault(k, {s: 0 for s in STATUSES})[r["review_status"]] += 1
    groups = [{"subject": k.split("|")[0], "grade": int(k.split("|")[1]), **v} for k, v in sorted(by_sg.items())]
    return {"total": len(rows), "by_status": by_status, "groups": groups}


@app.get("/api/admin/qbank/items")
def qbank_items(status: str = "pending", subject: str = "", grade: int = 0, topic: str = "", limit: int = 30, offset: int = 0,
                authorization: str = Header(None)):
    require_admin(authorization)
    if status not in STATUSES or len(subject) > 20 or len(topic) > 20 or not 0 <= grade <= 6 or not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(status_code=400, detail="bad filter")

    def q():
        query = sb.table(TABLE).select("*", count="exact").eq("review_status", status)
        if subject:
            query = query.eq("subject", subject)
        if grade:
            query = query.eq("grade", grade)
        if topic:
            query = query.eq("topic_code", topic)
        return query.order("topic_code").order("difficulty").range(offset, offset + limit - 1).execute()
    res = _db(q, "QBANK ITEMS")
    return {"count": res.count or 0, "items": [_with_review_info(it) for it in (res.data or [])]}


@app.post("/api/admin/qbank/items/{item_id}/review")
def qbank_review(item_id: str, body: QbankReviewRequest, authorization: str = Header(None)):
    admin = require_admin(authorization)
    if len(item_id) > 80:
        raise HTTPException(status_code=400, detail="bad id")
    rows = _db(lambda: sb.table(TABLE).select("*").eq("id", item_id).limit(1).execute(), "QBANK ITEM").data or []
    if not rows:
        raise HTTPException(status_code=404, detail="item not found")
    item = _lift(rows[0])
    edits = {k: getattr(body, k) for k in ("stem", "stimulus", "explain", "options", "answer", "why_wrong", "solution_expr", "difficulty")
             if getattr(body, k) is not None}
    if "stimulus" in edits and not str(edits["stimulus"]).strip():
        edits["stimulus"] = None
    updated = {**item, **edits}
    problems = qv.validate_item(updated, topic=_topics().get(updated["topic_code"]), sources=_sources())
    if body.status == "approved" and problems:
        # never approve an item the validators reject: fix it (edits) first
        raise HTTPException(status_code=422, detail={"reason": "item has problems", "problems": problems})
    db_edits = {k: v for k, v in edits.items() if k != "solution_expr"}
    patch = {**db_edits, "review_status": body.status, "review_note": (body.note or "").strip() or None,
             "reviewer": str(getattr(admin, "email", "") or "").lower(),
             "reviewed_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
    if "solution_expr" in edits:
        patch["verification"] = {**(item.get("verification") or {}), "solution_expr": edits["solution_expr"]}
    if edits:
        patch["fingerprint"] = qv.fingerprint(updated)
        patch["generator"] = {**(item.get("generator") or {}), "edited_by": patch["reviewer"], "edited_at": patch["updated_at"]}
    try:
        _db(lambda: sb.table(TABLE).update(patch).eq("id", item_id).execute(), "QBANK REVIEW")
    except HTTPException:
        raise
    except Exception as e:
        if "fingerprint" in repr(e):
            raise HTTPException(status_code=409, detail="another item already has exactly this text")
        raise
    print("QBANK REVIEW:", {"id": item_id, "status": body.status, "edited": sorted(edits), "by": patch["reviewer"]})
    return {"ok": True, "item": _with_review_info({**updated, **patch})}
