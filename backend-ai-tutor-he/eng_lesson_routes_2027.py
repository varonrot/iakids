"""Authenticated English micro-lesson endpoints; imported by test_prep_2027."""

from datetime import datetime, timezone

from fastapi import Header, HTTPException
from pydantic import Field
from starlette.concurrency import run_in_threadpool

from main import LimitedRequest, app, authenticate_user, get_child_by_id, sb, signed_url_cached
from eng_lessons_2027 import check_answer, public_step
from test_prep_2027 import SUBJECT, TOPIC, _diagnostic

BUCKET = "2027-eng-lesson-media"


class StartRequest(LimitedRequest):
    kid_id: str


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
        return {"correct": False, "hint": action.get("hint", "Look at the visual and try again.")}
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


@app.post("/api/eng/lesson-engine/answer")
async def answer_english_lesson(body: AnswerRequest, authorization: str = Header(None)):
    user_id = await run_in_threadpool(_parent_and_child, authorization, body.kid_id)
    return await run_in_threadpool(_submit, user_id, body.kid_id, body)
