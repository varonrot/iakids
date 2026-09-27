"""Authenticated English micro-lesson endpoints; imported by test_prep_2027."""

from datetime import datetime, timezone

from fastapi import Header, HTTPException
from pydantic import Field
from starlette.concurrency import run_in_threadpool

from main import LimitedRequest, app, authenticate_user, get_child_by_id, sb
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


def _parent_and_child(authorization: str, kid_id: str):
    user = authenticate_user(authorization)
    child = get_child_by_id(str(user.id), kid_id)
    if int(child.get("age") or 0) != 5:
        raise HTTPException(status_code=409, detail="This first lesson is for Grade 5.")
    # Require the saved topic and completed quick check, as in the existing flow.
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


def _approved_plan():
    rows = (sb.table("2027_eng_lesson_plans").select("id,content")
            .eq("language", "en").eq("grade", 5).eq("subject", SUBJECT)
            .eq("topic", TOPIC).eq("skill_id", "division-as-groups")
            .eq("prompt_version", 1).eq("status", "approved")
            .limit(1).execute().data or [])
    if not rows:
        raise HTTPException(status_code=409, detail="This lesson is being prepared.")
    return rows[0]


def _visible_step(plan_id: str, content: dict, index: int):
    visual = (sb.table("2027_eng_lesson_visuals").select("storage_path")
              .eq("plan_id", plan_id).eq("step_index", index)
              .order("generation_version", desc=True).limit(1).execute().data or [])
    image_url = None
    if visual:
        signed = sb.storage.from_(BUCKET).create_signed_url(visual[0]["storage_path"], 600)
        image_url = signed.get("signedURL") or signed.get("signedUrl")
    return public_step(content, index, image_url)


@app.post("/api/eng/lesson-engine/start")
async def start_english_lesson(body: StartRequest, authorization: str = Header(None)):
    user_id = await run_in_threadpool(_parent_and_child, authorization, body.kid_id)
    plan = await run_in_threadpool(_approved_plan)
    progress = await run_in_threadpool(_progress, user_id, body.kid_id, plan["id"])
    index = int(progress["current_step"])
    if index >= 3:
        return {"plan_id": plan["id"], "complete": True}
    step = await run_in_threadpool(_visible_step, plan["id"], plan["content"], index)
    return {"plan_id": plan["id"], "complete": False, **step}


def _submit(user_id: str, kid_id: str, body: AnswerRequest):
    plan = _approved_plan()
    if plan["id"] != body.plan_id:
        raise HTTPException(status_code=409, detail="Restart the lesson to load its current plan.")
    progress = _progress(user_id, kid_id, plan["id"])
    index = int(progress["current_step"])
    if index != body.step_index or index >= 3:
        raise HTTPException(status_code=409, detail="The lesson has moved on. Reload this step.")
    if not check_answer(plan["content"], index, body.option_index):
        action = plan["content"]["steps"][index]["interaction"]
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
