"""English voice tutor: a short spoken conversation in which Hebrew explains and English is the subject.

New routes only (2026-09-25). Nothing existing changes: main.py imports this module on its last line and
the routes register on the same `app`, so every gate rule (security, prompts, models, performance) reads
them together with main.py (tools/prompt_gate.py, ROUTE_MODULES).

    GET  /api/english/allowance?kid_id=      today's spoken minutes: used, limit, left
    POST /api/english/session/start          new conversation; the teacher opens it
    POST /api/english/turn                   the child's words (typed or dictated) -> the teacher's reply
    POST /api/english/session/end            close it; a summary for the child and one line for the parent
    GET  /api/english/sessions?kid_id=       the last conversations, for the parent panel

Voice uses what already exists: the child speaks through the dictation script (browser speech
recognition, no model, no cost) and the page reads `say_he` aloud through /api/tutor/tts (cached).

What was taken from the competitors (2026-09-25, Lexi and Loora):
  * a daily free allowance (Lexi: 10 minutes a day) - it brings families in AND caps the AI bill;
  * one correction at a time, at most MAX_SPOKEN_CORRECTIONS spoken per session, the rest shown (Loora);
  * the first conversation sets the level and it adjusts itself, no placement test (Loora);
  * one "remember this" line at the end (Loora's key takeaway); "no shame" as a rule of the prompt.
What we add: Hebrew explanations for young beginners, a parent line per session, school topics.

Knobs: ENGLISH_TUTOR_ENABLED (1), ENGLISH_TUTOR_MODEL (gpt-4o-mini), ENGLISH_FREE_SECONDS_PER_DAY (600),
ENGLISH_PAID_SECONDS_PER_DAY (3600), ENGLISH_MAX_SPOKEN_CORRECTIONS (3).
Storage: public.english_tutor_sessions (supabase/migrations/20260925_english_tutor_sessions.sql).
"""
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import Header, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from main import (CHAT_TEXT_MAX, HISTORY_ITEM_MAX, HISTORY_ITEMS_MAX, LimitedRequest, ai_context, aclient, app,
                  authenticate_user, get_child_by_id, guard_reply_payload, hebrew_child_prompt_block,
                  is_paid_active_subscription, llm_model, lq, sb, supabase_with_retry)

ENGLISH_TUTOR_ENABLED = os.getenv("ENGLISH_TUTOR_ENABLED", "1") not in ("0", "false", "no")
ENGLISH_TUTOR_MODEL = llm_model(os.getenv("ENGLISH_TUTOR_MODEL", "gpt-4o-mini"))
ENGLISH_FREE_SECONDS_PER_DAY = int(os.getenv("ENGLISH_FREE_SECONDS_PER_DAY", "600"))
ENGLISH_PAID_SECONDS_PER_DAY = int(os.getenv("ENGLISH_PAID_SECONDS_PER_DAY", "3600"))
ENGLISH_MAX_SPOKEN_CORRECTIONS = int(os.getenv("ENGLISH_MAX_SPOKEN_CORRECTIONS", "3"))
TURN_SECONDS_MIN, TURN_SECONDS_MAX = 10, 90     # a turn counts the time since the last one, within these bounds
LEVELS = ("beginner", "elementary", "intermediate")
TOPICS = ("colors", "animals", "family", "food", "school", "my day", "games and hobbies", "weather", "feelings")
TABLE = "english_tutor_sessions"
IL = ZoneInfo("Asia/Jerusalem")

ENGLISH_TUTOR_PROMPT = (Path(__file__).resolve().parent / "prompts/english/iakids_english_tutor_prompt.txt").read_text(encoding="utf-8")
print(f"[config] english tutor: {'on' if ENGLISH_TUTOR_ENABLED else 'off'} model={ENGLISH_TUTOR_MODEL} "
      f"free={ENGLISH_FREE_SECONDS_PER_DAY}s paid={ENGLISH_PAID_SECONDS_PER_DAY}s")


# ------------------------------------------------------------------ request / reply shapes
class EnglishStartRequest(LimitedRequest):
    kid_id: str
    topic: Optional[str] = None
    level: Optional[Literal["beginner", "elementary", "intermediate"]] = None


class EnglishTurnRequest(LimitedRequest):
    kid_id: str
    session_id: str
    message: str = Field(..., min_length=1, max_length=CHAT_TEXT_MAX)


class EnglishEndRequest(LimitedRequest):
    kid_id: str
    session_id: str


class EnglishCorrection(BaseModel):
    said: str
    better: str
    why_he: str


class EnglishWord(BaseModel):
    en: str
    he: str


class EnglishTeacherReply(BaseModel):
    say_he: str
    target_en: str
    task: Literal["repeat", "answer", "choose", "complete", "free"]
    options: list[str]
    correction: Optional[EnglishCorrection]
    new_words: list[EnglishWord]
    level_signal: Literal["up", "same", "down"]


# ------------------------------------------------------------------ helpers (sync: called through the threadpool)
def _require_enabled():
    if not ENGLISH_TUTOR_ENABLED:
        raise HTTPException(status_code=404, detail="not found")


def _db(operation, label):
    try:
        return supabase_with_retry(operation, label=label)
    except Exception as e:
        if "english_tutor_sessions" in repr(e) and ("does not exist" in repr(e) or "PGRST205" in repr(e)):
            raise HTTPException(status_code=503, detail="English tutor is not set up")
        raise


def _day_start_utc_iso() -> str:
    now = datetime.now(IL)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()


def english_allowance(user_id: str, kid_id: str) -> dict:
    """Today's spoken seconds for this child (Israel day), against the family's daily limit."""
    rows = _db(lambda: sb.table(TABLE).select("seconds_used").eq("kid_id", kid_id)
               .gte("started_at", _day_start_utc_iso()).execute(), "ENGLISH ALLOWANCE").data or []
    used = sum(int(r.get("seconds_used") or 0) for r in rows)
    paid = bool(is_paid_active_subscription(user_id))
    limit = ENGLISH_PAID_SECONDS_PER_DAY if paid else ENGLISH_FREE_SECONDS_PER_DAY
    return {"used_seconds": used, "limit_seconds": limit, "remaining_seconds": max(0, limit - used), "paid": paid}


def _load_session(user_id: str, kid_id: str, session_id: str) -> dict:
    rows = _db(lambda: sb.table(TABLE).select("*").eq("id", session_id).eq("kid_id", kid_id)
               .eq("user_id", user_id).limit(1).execute(), "ENGLISH SESSION").data or []
    if not rows:
        raise HTTPException(status_code=404, detail="session not found")
    return rows[0]


def _save_session(session_id: str, patch: dict) -> None:
    patch = {**patch, "updated_at": datetime.now(timezone.utc).isoformat()}
    _db(lambda: sb.table(TABLE).update(patch).eq("id", session_id).execute(), "ENGLISH SESSION SAVE")


def _turn_seconds(last_turn_at: str | None) -> int:
    if not last_turn_at:
        return TURN_SECONDS_MIN
    try:
        last = datetime.fromisoformat(str(last_turn_at).replace("Z", "+00:00"))
    except ValueError:
        return TURN_SECONDS_MIN
    gap = (datetime.now(timezone.utc) - last).total_seconds()
    return int(min(TURN_SECONDS_MAX, max(TURN_SECONDS_MIN, gap)))


def _next_level(level: str, signal: str) -> str:
    i = LEVELS.index(level) if level in LEVELS else 0
    if signal == "up":
        i = min(len(LEVELS) - 1, i + 1)
    elif signal == "down":
        i = max(0, i - 1)
    return LEVELS[i]


def _clip(history: list) -> list:
    out = [{"role": h["role"], "content": str(h.get("content") or "")[:HISTORY_ITEM_MAX]}
           for h in (history or []) if isinstance(h, dict) and h.get("role") in ("user", "assistant")]
    return out[-HISTORY_ITEMS_MAX:]


def english_teacher_rules(level: str, topic: str, words: list, first_name: str = "") -> str:
    """The English teacher's rules for this session. Placeholders are replaced, not str.format()-ed:
    the prompt shows JSON with braces."""
    so_far = ", ".join(w.get("en", "") for w in (words or [])[-40:]) or "none yet"
    return (ENGLISH_TUTOR_PROMPT.replace("{level}", level).replace("{topic}", topic or "free choice")
            .replace("{words_so_far}", so_far).replace("{child_first_name}", first_name or "unknown"))


async def english_teacher_reply(body, user, child: dict, session: dict) -> dict:
    """One teacher turn. `body.message` is the child's words; None on the opening turn."""
    user_text = body.message if isinstance(body, EnglishTurnRequest) else None
    # the child block carries gender, Hebrew correctness and PROMPT_SECURITY_RULES (the gate checks it is HERE)
    first_name = lq.display_first_name(str((child or {}).get("child_name") or "").strip()) if (child or {}).get("child_name") else ""
    system = hebrew_child_prompt_block(child) + "\n\n" + english_teacher_rules(session["level"], session.get("topic"),
                                                                              session.get("words") or [], first_name)
    messages = [{"role": "system", "content": system}]
    messages += _clip(session.get("history"))
    messages.append({"role": "user", "content": user_text if user_text else
                     "(the conversation starts now: greet the child by first name in Hebrew and give the first small English task)"})
    ai_context("english_tutor", user, body)
    completion = await aclient.beta.chat.completions.parse(
        model=ENGLISH_TUTOR_MODEL,
        messages=messages,
        response_format=EnglishTeacherReply,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise HTTPException(status_code=502, detail="the teacher did not answer, try again")
    reply = guard_reply_payload(parsed.model_dump(), "ENGLISH TUTOR")
    reply["options"] = [str(o)[:80] for o in (reply.get("options") or [])[:2]] if reply.get("task") == "choose" else []
    reply["new_words"] = [w for w in (reply.get("new_words") or [])[:2] if isinstance(w, dict) and w.get("en")]
    reply["target_en"] = str(reply.get("target_en") or "")[:200]
    return reply


def _apply_turn(session: dict, user_text: str | None, reply: dict) -> tuple[dict, dict]:
    """New session fields after a turn, and what the child's screen needs to know about it."""
    history = list(session.get("history") or [])
    if user_text:
        history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": f"{reply['say_he']}\n[{reply['target_en']}]"})
    known = {w.get("en", "").lower() for w in (session.get("words") or [])}
    words = list(session.get("words") or []) + [w for w in reply["new_words"] if w["en"].lower() not in known]
    spoken = int(session.get("spoken_corrections") or 0)
    speak_correction = bool(reply.get("correction")) and spoken < ENGLISH_MAX_SPOKEN_CORRECTIONS
    seconds = _turn_seconds(session.get("last_turn_at"))
    patch = {
        "history": history[-HISTORY_ITEMS_MAX * 2:],          # stored: last 24; sent to the model: last 12 (_clip)
        "words": words[-200:],
        "turns": int(session.get("turns") or 0) + 1,
        "seconds_used": int(session.get("seconds_used") or 0) + seconds,
        "spoken_corrections": spoken + (1 if speak_correction else 0),
        "level": _next_level(session.get("level") or "beginner", reply.get("level_signal") or "same"),
        "last_turn_at": datetime.now(timezone.utc).isoformat(),
    }
    return patch, {"speak_correction": speak_correction, "seconds": seconds}


def english_summary(child: dict, session: dict) -> dict:
    """Built from the session itself, no model call: minutes, the words, one thing to remember, one line for the parent."""
    words = session.get("words") or []
    minutes = max(1, round(int(session.get("seconds_used") or 0) / 60))
    remember = None
    for h in reversed(session.get("history") or []):
        if h.get("role") == "assistant" and "[" in str(h.get("content")):
            remember = str(h["content"]).rsplit("[", 1)[1].rstrip("]").strip() or None
            break
    shown = ", ".join(f"{w['en']} ({w['he']})" for w in words[:8])
    first = str((child or {}).get("child_name") or "").split(" ")[0]
    talk = "דקת שיחה אחת" if minutes == 1 else f"{minutes} דקות שיחה"
    new_words = "מילה חדשה אחת" if len(words) == 1 else f"{len(words)} מילים חדשות"
    parent = (f"היום באנגלית{' עם ' + first if first else ''}: {talk}, {new_words}"
              + (f": {shown}." if shown else "."))
    return {"minutes": minutes, "turns": int(session.get("turns") or 0), "words": words, "level": session.get("level"),
            "remember_en": remember, "parent_note": parent}


# ------------------------------------------------------------------ routes
@app.get("/api/english/allowance")
async def english_allowance_route(kid_id: str, authorization: str = Header(None)):
    _require_enabled()
    if len(kid_id) > 64:
        raise HTTPException(status_code=400, detail="bad kid_id")
    user = await run_in_threadpool(lambda: authenticate_user(authorization))
    await run_in_threadpool(lambda: get_child_by_id(user.id, kid_id))
    return await run_in_threadpool(lambda: english_allowance(user.id, kid_id))


@app.post("/api/english/session/start")
async def english_session_start(body: EnglishStartRequest, authorization: str = Header(None)):
    _require_enabled()
    user = await run_in_threadpool(lambda: authenticate_user(authorization))
    child = await run_in_threadpool(lambda: get_child_by_id(user.id, body.kid_id))
    allowance = await run_in_threadpool(lambda: english_allowance(user.id, body.kid_id))
    if allowance["remaining_seconds"] <= 0:
        raise HTTPException(status_code=429, detail={"reason": "daily_english_limit", **allowance})
    last = await run_in_threadpool(lambda: _db(lambda: sb.table(TABLE).select("level").eq("kid_id", body.kid_id)
                                                .order("started_at", desc=True).limit(1).execute(), "ENGLISH LAST LEVEL").data)
    level = body.level or (last[0]["level"] if last else "beginner")
    topic = (body.topic or TOPICS[int(time.time() // 86400) % len(TOPICS)]).strip()[:60]
    session = (await run_in_threadpool(lambda: _db(lambda: sb.table(TABLE).insert({
        "user_id": user.id, "kid_id": body.kid_id, "level": level, "topic": topic}).execute(), "ENGLISH START"))).data[0]
    reply = await english_teacher_reply(body, user, child, session)
    patch, extra = _apply_turn(session, None, reply)
    await run_in_threadpool(lambda: _save_session(session["id"], patch))
    return {"session_id": session["id"], "level": patch["level"], "topic": topic, "reply": reply, **extra,
            "remaining_seconds": max(0, allowance["remaining_seconds"] - extra["seconds"])}


@app.post("/api/english/turn")
async def english_turn(body: EnglishTurnRequest, authorization: str = Header(None)):
    _require_enabled()
    user = await run_in_threadpool(lambda: authenticate_user(authorization))
    child = await run_in_threadpool(lambda: get_child_by_id(user.id, body.kid_id))
    session = await run_in_threadpool(lambda: _load_session(user.id, body.kid_id, body.session_id))
    if session.get("status") != "active":
        raise HTTPException(status_code=409, detail="session ended")
    allowance = await run_in_threadpool(lambda: english_allowance(user.id, body.kid_id))
    if allowance["remaining_seconds"] <= 0:
        raise HTTPException(status_code=429, detail={"reason": "daily_english_limit", **allowance})
    reply = await english_teacher_reply(body, user, child, session)
    patch, extra = _apply_turn(session, body.message.strip(), reply)
    await run_in_threadpool(lambda: _save_session(session["id"], patch))
    return {"session_id": session["id"], "level": patch["level"], "reply": reply, **extra,
            "remaining_seconds": max(0, allowance["remaining_seconds"] - extra["seconds"])}


@app.post("/api/english/session/end")
async def english_session_end(body: EnglishEndRequest, authorization: str = Header(None)):
    _require_enabled()
    user = await run_in_threadpool(lambda: authenticate_user(authorization))
    child = await run_in_threadpool(lambda: get_child_by_id(user.id, body.kid_id))
    session = await run_in_threadpool(lambda: _load_session(user.id, body.kid_id, body.session_id))
    if session.get("status") == "ended" and session.get("summary"):
        return {"session_id": session["id"], "summary": session["summary"]}
    summary = guard_reply_payload(english_summary(child, session), "ENGLISH SUMMARY")
    await run_in_threadpool(lambda: _save_session(session["id"], {
        "status": "ended", "summary": summary, "ended_at": datetime.now(timezone.utc).isoformat()}))
    return {"session_id": session["id"], "summary": summary}


@app.get("/api/english/sessions")
async def english_sessions(kid_id: str, authorization: str = Header(None)):
    _require_enabled()
    if len(kid_id) > 64:
        raise HTTPException(status_code=400, detail="bad kid_id")
    user = await run_in_threadpool(lambda: authenticate_user(authorization))
    await run_in_threadpool(lambda: get_child_by_id(user.id, kid_id))
    since = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    rows = await run_in_threadpool(lambda: _db(lambda: sb.table(TABLE)
                                               .select("id,level,topic,status,turns,seconds_used,summary,started_at,ended_at")
                                               .eq("kid_id", kid_id).eq("user_id", user.id).gte("started_at", since)
                                               .order("started_at", desc=True).limit(10).execute(), "ENGLISH SESSIONS").data or [])
    return {"sessions": rows}
