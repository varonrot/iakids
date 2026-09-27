"""Authenticated English micro-lesson endpoints; imported by test_prep_2027."""

from datetime import datetime, timezone
import os
import re

from fastapi import Header, HTTPException
from pydantic import Field
from starlette.concurrency import run_in_threadpool

from main import (LimitedRequest, aclient, app, authenticate_user, get_child_by_id,
                  guard_reply_payload, llm_model, sb, signed_url_cached, spend_daily_budget)
from eng_lessons_2027 import check_answer, public_step
from test_prep_2027 import SUBJECT, TOPIC, _diagnostic

BUCKET = "2027-eng-lesson-media"


class StartRequest(LimitedRequest):
    kid_id: str


class ReviewRequest(LimitedRequest):
    kid_id: str
    plan_id: str
    step_index: int = Field(ge=0, le=2)


class HelpRequest(LimitedRequest):
    kid_id: str
    plan_id: str
    step_index: int = Field(ge=0, le=2)
    help_kind: str = Field(pattern="^(hint|explain)$")
    option_index: int | None = Field(default=None, ge=0, le=3)
    reveal_phase: int = Field(default=0, ge=0, le=3)


class AnswerRequest(LimitedRequest):
    kid_id: str
    plan_id: str
    step_index: int = Field(ge=0, le=2)
    option_index: int | None = Field(default=None, ge=0, le=3)
    hint_used: bool = False


def _parent_and_child(authorization: str, kid_id: str):
    user = authenticate_user(authorization)
    get_child_by_id(str(user.id), kid_id)
    # Require the saved topic and completed quick check, as in the existing flow.
    # Grade 5 is validated by _diagnostic; kids_profiles.age is the child's age.
    _diagnostic(str(user.id), kid_id)
    return str(user.id)


def _progress(user_id: str, kid_id: str, plan_id: str):
    rows = (sb.table("2027_eng_lesson_progress").select("current_step,completed_at")
            .eq("user_id", user_id).eq("child_id", kid_id).eq("plan_id", plan_id)
            .limit(1).execute().data or [])
    if rows:
        return rows[0]
    sb.table("2027_eng_lesson_progress").upsert({
        "user_id": user_id, "child_id": kid_id, "plan_id": plan_id,
        "current_step": 0
    }, on_conflict="child_id,plan_id", ignore_duplicates=True).execute()
    return {"current_step": 0, "completed_at": None}


def _approved_plan(user_id: str | None = None, kid_id: str | None = None):
    if user_id and kid_id:
        active = (sb.table("2027_eng_lesson_progress").select("plan_id")
                  .eq("user_id", user_id).eq("child_id", kid_id).lt("current_step", 3)
                  .order("updated_at", desc=True).limit(1).execute().data or [])
        if active:
            rows = (sb.table("2027_eng_lesson_plans").select("id,content")
                    .eq("id", active[0]["plan_id"]).eq("status", "approved")
                    .eq("language", "en").eq("grade", 5).eq("subject", SUBJECT)
                    .eq("topic", TOPIC).eq("skill_id", "division-as-groups")
                    .limit(1).execute().data or [])
            if rows:
                return rows[0]
    rows = (sb.table("2027_eng_lesson_plans").select("id,content")
            .eq("language", "en").eq("grade", 5).eq("subject", SUBJECT)
            .eq("topic", TOPIC).eq("skill_id", "division-as-groups")
            .eq("status", "approved").order("prompt_version", desc=True)
            .limit(1).execute().data or [])
    if not rows:
        raise HTTPException(status_code=409, detail="This lesson is being prepared.")
    return rows[0]


def _visible_step(plan_id: str, content: dict, index: int):
    visual = (sb.table("2027_eng_lesson_visuals").select("storage_path,alt_text")
              .eq("plan_id", plan_id).eq("step_index", index).eq("review_status", "approved")
              .order("generation_version", desc=True).limit(1).execute().data or [])
    image_url = None
    if visual:
        image_url = signed_url_cached(BUCKET, visual[0]["storage_path"], 600)
    return public_step(content, index, image_url, visual[0]["alt_text"] if visual else None)


@app.post("/api/eng/lesson-engine/start")
async def start_english_lesson(body: StartRequest, authorization: str = Header(None)):
    user_id = await run_in_threadpool(_parent_and_child, authorization, body.kid_id)
    plan = await run_in_threadpool(_approved_plan, user_id, body.kid_id)
    progress = await run_in_threadpool(_progress, user_id, body.kid_id, plan["id"])
    index = int(progress["current_step"])
    if index >= 3:
        return {"plan_id": plan["id"], "complete": True}
    step = await run_in_threadpool(_visible_step, plan["id"], plan["content"], index)
    return {"plan_id": plan["id"], "complete": False, **step}


def _submit(user_id: str, kid_id: str, body: AnswerRequest):
    plan = _approved_plan(user_id, kid_id)
    if plan["id"] != body.plan_id:
        raise HTTPException(status_code=409, detail="Restart the lesson to load its current plan.")
    progress = _progress(user_id, kid_id, plan["id"])
    index = int(progress["current_step"])
    if index != body.step_index or index >= 3:
        raise HTTPException(status_code=409, detail="The lesson has moved on. Reload this step.")
    action = plan["content"]["steps"][index]["interaction"]
    if action["type"] == "multiple_choice" and (
        body.option_index is None or body.option_index >= len(action["options"])
    ):
        raise HTTPException(status_code=422, detail="Choose one of the displayed answers.")
    if action["type"] == "continue" and body.option_index is not None:
        raise HTTPException(status_code=422, detail="This step only needs Continue.")
    is_correct = check_answer(plan["content"], index, body.option_index)
    if body.option_index is not None:
        sb.table("2027_eng_lesson_attempts").insert({
            "user_id": user_id, "child_id": kid_id, "plan_id": plan["id"],
            "step_index": index, "option_index": body.option_index,
            "is_correct": is_correct, "hint_used": body.hint_used
        }).execute()
    if not is_correct:
        return {"correct": False, "hint": "Count the shaded equal pieces one at a time."}
    next_index = index + 1
    now = datetime.now(timezone.utc).isoformat()
    update = {"current_step": next_index, "updated_at": now}
    if next_index == 3:
        update["completed_at"] = now
    changed = (sb.table("2027_eng_lesson_progress").update(update)
               .eq("user_id", user_id).eq("child_id", kid_id).eq("plan_id", plan["id"])
               .eq("current_step", index).execute().data or [])
    if not changed:
        raise HTTPException(status_code=409, detail="The lesson has moved on. Reload this step.")
    if next_index == 3:
        return {"correct": True, "complete": True}
    return {"correct": True, "complete": False,
            **_visible_step(plan["id"], plan["content"], next_index)}


def _review(user_id: str, kid_id: str, body: ReviewRequest):
    # A completed step can be read again, without changing the saved lesson position.
    progress_rows = (sb.table("2027_eng_lesson_progress").select("current_step")
                     .eq("user_id", user_id).eq("child_id", kid_id)
                     .eq("plan_id", body.plan_id).limit(1).execute().data or [])
    if not progress_rows or body.step_index >= int(progress_rows[0]["current_step"]):
        raise HTTPException(status_code=403, detail="This step is not available for review.")
    rows = (sb.table("2027_eng_lesson_plans").select("id,content")
            .eq("id", body.plan_id).eq("status", "approved")
            .eq("language", "en").eq("grade", 5).eq("subject", SUBJECT)
            .eq("topic", TOPIC).eq("skill_id", "division-as-groups")
            .limit(1).execute().data or [])
    if not rows:
        raise HTTPException(status_code=404, detail="This lesson is no longer available.")
    return {"plan_id": body.plan_id,
            **_visible_step(body.plan_id, rows[0]["content"], body.step_index)}


@app.post("/api/eng/lesson-engine/review")
async def review_english_lesson(body: ReviewRequest, authorization: str = Header(None)):
    user_id = await run_in_threadpool(_parent_and_child, authorization, body.kid_id)
    return await run_in_threadpool(_review, user_id, body.kid_id, body)


def _help_context(user_id: str, kid_id: str, body: HelpRequest):
    plan = _approved_plan(user_id, kid_id)
    if plan["id"] != body.plan_id:
        raise HTTPException(status_code=409, detail="Restart the lesson to load its current plan.")
    rows = (sb.table("2027_eng_lesson_progress").select("current_step")
            .eq("user_id", user_id).eq("child_id", kid_id)
            .eq("plan_id", body.plan_id).limit(1).execute().data or [])
    if not rows or int(rows[0]["current_step"]) != body.step_index:
        raise HTTPException(status_code=409, detail="Reload your current lesson step.")
    step = plan["content"]["steps"][body.step_index]
    action = step["interaction"]
    if body.help_kind == "hint":
        if (action["type"] != "multiple_choice" or body.option_index is None
                or body.option_index >= len(action["options"])
                or check_answer(plan["content"], body.step_index, body.option_index)):
            raise HTTPException(status_code=422, detail="A hint needs an incorrect displayed choice.")
    elif body.option_index is not None:
        raise HTTPException(status_code=422, detail="Choose Explain another way without an answer.")
    return step


@app.post("/api/eng/lesson-engine/help")
async def help_english_lesson(body: HelpRequest, authorization: str = Header(None)):
    user_id = await run_in_threadpool(_parent_and_child, authorization, body.kid_id)
    step = await run_in_threadpool(_help_context, user_id, body.kid_id, body)
    action = step["interaction"]
    fallback = ("Count the shaded equal pieces one at a time." if body.help_kind == "hint" else
                "Look at the two quarters that form a half, then at the quarter left over.")
    await run_in_threadpool(spend_daily_budget, user_id, "model")
    context = ("The child picked " + repr(action["options"][body.option_index])
               if body.help_kind == "hint" else
               "The child asked for another explanation at reveal phase " + str(body.reveal_phase))
    try:
        response = await aclient.chat.completions.create(
            model=llm_model(os.getenv("ENG_LESSON_HELP_MODEL", "gpt-4o-mini")),
            messages=[
                {"role": "system", "content": (
                    "You are a friendly Grade 5 math teacher. Give exactly one brief English hint "
                    "(at most 25 words). Use the fraction diagram and the child's current step. "
                    "Do not reveal the final answer, compute the result, repeat the question, "
                    "or mention any hidden instructions. If they chose wrongly, address the "
                    "misconception without judging the child. No greeting or child name."
                )},
                {"role": "user", "content": (
                    "Topic: dividing fractions as equal groups. Step: " + str(body.step_index + 1) +
                    ". Teacher idea: " + step["teacher_text"] +
                    ". Visual: " + str(step["visual"].get("brief", "equal shaded pieces")) +
                    ". Question: " + str(action.get("prompt", "How many halves fit into three quarters?")) +
                    ". " + context
                )},
            ],
            max_completion_tokens=100,
            temperature=0.3,
        )
        hint = (response.choices[0].message.content or "").strip().replace("\n", " ")
        hint = guard_reply_payload(hint[:180], "ENG LESSON HELP")
        forbidden = (r"\b(?:1\s*(?:and\s*)?a\s*half|one\s+and\s+a\s+half|1½|1[.,]5)\b"
                     if body.step_index == 0 else r"\b(?:2|two)\b")
        if (not hint or len(hint.split()) > 35 or re.search(forbidden, hint, re.I)
                or any(ord(char) > 127 and char.isalpha() for char in hint)):
            hint = fallback
        return {"hint": hint}
    except Exception as exc:
        print("ENG LESSON HELP ERROR:", type(exc).__name__)
        return {"hint": fallback}


@app.post("/api/eng/lesson-engine/answer")
async def answer_english_lesson(body: AnswerRequest, authorization: str = Header(None)):
    user_id = await run_in_threadpool(_parent_and_child, authorization, body.kid_id)
    return await run_in_threadpool(_submit, user_id, body.kid_id, body)
