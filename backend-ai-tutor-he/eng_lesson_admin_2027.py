"""Admin-only OpenAI drafts for the English lesson engine."""

from typing import Literal

from fastapi import Header, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from main import (aclient, app, generate_lesson_hero_image_bytes, guard_reply_payload,
                  llm_model, require_admin, sb, signed_url_cached, spend_daily_budget)
from eng_lessons_2027 import teacher_messages, validate_plan

TABLE = "2027_eng_lesson_plans"
PROMPT_VERSION = 2
MODEL = llm_model("gpt-4o-mini")
BUCKET = "2027-eng-lesson-media"


class VisualDraft(BaseModel):
    kind: Literal["none", "generated_image"]
    brief: str | None = Field(default=None, max_length=500)


class InteractionDraft(BaseModel):
    type: Literal["continue", "multiple_choice"]
    prompt: str | None = Field(default=None, max_length=160)
    options: list[str] | None = None
    answer_index: int | None = None
    hint: str | None = Field(default=None, max_length=180)


class StepDraft(BaseModel):
    phase: Literal["see_the_idea", "try_together", "your_turn"]
    teacher_text: str = Field(max_length=500)
    visual: VisualDraft
    interaction: InteractionDraft


class PlanDraft(BaseModel):
    version: Literal[1]
    skill_id: str = Field(max_length=80)
    steps: list[StepDraft] = Field(min_length=3, max_length=3)


def _draft_record():
    return (sb.table(TABLE).select("id,status,content,prompt_version")
            .eq("language", "en").eq("grade", 5).eq("subject", "Math")
            .eq("topic", "Dividing fractions").eq("skill_id", "division-as-groups")
            .eq("prompt_version", PROMPT_VERSION).limit(1).execute().data or [])


def _plan_by_id(plan_id: str):
    rows = (sb.table(TABLE).select("id,status,content,prompt_version")
            .eq("id", plan_id).limit(1).execute().data or [])
    if not rows:
        raise HTTPException(status_code=404, detail="English lesson plan not found.")
    return rows[0]


@app.get("/api/admin/eng/lesson-engine/draft")
def read_english_draft(authorization: str = Header(None)):
    require_admin(authorization)
    rows = _draft_record()
    return {"draft": rows[0] if rows else None}


@app.post("/api/admin/eng/lesson-engine/generate")
async def generate_english_draft(authorization: str = Header(None)):
    user = require_admin(authorization)
    rows = _draft_record()
    if rows and rows[0]["status"] == "approved":
        raise HTTPException(status_code=409, detail="This version is already approved. Use a new prompt version.")
    spend_daily_budget(user.id, "model")
    try:
        response = await aclient.beta.chat.completions.parse(
            model=MODEL,
            messages=teacher_messages(grade=5, subject="Math", topic="Dividing fractions"),
            response_format=PlanDraft,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("No structured teacher plan")
        content = guard_reply_payload(parsed.model_dump(exclude_none=True), "ENG LESSON DRAFT")
        validate_plan(content)
        if content["skill_id"] != "division-as-groups":
            raise ValueError("Unexpected skill")
        # The model's mathematical choices remain a draft until an admin reviews them.
        saved = (sb.table(TABLE).upsert({
            "language": "en", "grade": 5, "subject": "Math", "topic": "Dividing fractions",
            "skill_id": "division-as-groups", "prompt_version": PROMPT_VERSION,
            "status": "draft", "content": content
        }, on_conflict="language,grade,subject,topic,skill_id,prompt_version")
                 .execute().data or [])
        return {"draft": saved[0] if saved else _draft_record()[0]}
    except HTTPException:
        raise
    except Exception as exc:
        print("ENG LESSON DRAFT ERROR:", type(exc).__name__, repr(exc)[:200])
        raise HTTPException(status_code=502, detail="The teacher draft could not be prepared.")


@app.post("/api/admin/eng/lesson-engine/approve")
def approve_english_draft(authorization: str = Header(None)):
    require_admin(authorization)
    rows = _draft_record()
    if not rows or rows[0]["status"] != "draft":
        raise HTTPException(status_code=409, detail="No draft is awaiting review.")
    validate_plan(rows[0]["content"])
    # A human reviewer must verify the mathematical examples and answer indexes.
    sb.table(TABLE).update({"status": "approved"}).eq("id", rows[0]["id"]).eq("status", "draft").execute()
    return {"approved": True, "id": rows[0]["id"]}


class VisualRequest(BaseModel):
    plan_id: str = Field(max_length=60)
    step_index: int = Field(ge=0, le=2)


def _visual_record(plan_id: str, index: int):
    return (sb.table("2027_eng_lesson_visuals")
            .select("id,storage_path,review_status,alt_text")
            .eq("plan_id", plan_id).eq("step_index", index)
            .eq("generation_version", 1).limit(1).execute().data or [])


def _visual_response(row: dict):
    return {"id": row["id"], "status": row["review_status"],
            "url": signed_url_cached(BUCKET, row["storage_path"], 600),
            "alt_text": row["alt_text"]}


def _generate_visual(plan_id: str, index: int):
    existing = _visual_record(plan_id, index)
    if existing:
        return _visual_response(existing[0])
    plan = _plan_by_id(plan_id)
    if plan["status"] != "approved":
        raise HTTPException(status_code=409, detail="Approve the lesson text before illustrating it.")
    visual = plan["content"]["steps"][index]["visual"]
    if visual["kind"] != "generated_image":
        raise HTTPException(status_code=409, detail="This step does not request an illustration.")
    prompt = (
        "Create one clean, child-friendly mathematics diagram. "
        "Draw exactly the count of equal pieces described below. "
        "The number and size of pieces must be mathematically precise. "
        "Use the teal, mint, navy, and warm cream visual style of IA KIDS ENG. "
        "Leave generous whitespace. No words, labels, digits, letters, or watermark. "
        "Scene: " + visual["brief"]
    )
    image_bytes, mime = generate_lesson_hero_image_bytes(prompt)
    suffix = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime)
    if not suffix or len(image_bytes) > 5 * 1024 * 1024:
        raise ValueError("Gemini image has an unsupported format or size")
    path = f"plans/{plan_id}/v1/step-{index}.{suffix}"
    sb.storage.from_(BUCKET).upload(path, image_bytes, {"content-type": mime, "upsert": "false"})
    saved = (sb.table("2027_eng_lesson_visuals").insert({
        "plan_id": plan_id, "step_index": index, "storage_path": path,
        "alt_text": visual["brief"][:300], "generation_version": 1,
        "review_status": "pending"
    }).execute().data or [])
    return _visual_response(saved[0])


@app.post("/api/admin/eng/lesson-engine/visual/generate")
async def generate_english_visual(body: VisualRequest, authorization: str = Header(None)):
    user = require_admin(authorization)
    if _visual_record(body.plan_id, body.step_index):
        return _visual_response(_visual_record(body.plan_id, body.step_index)[0])
    spend_daily_budget(user.id, "vision")
    try:
        return await run_in_threadpool(_generate_visual, body.plan_id, body.step_index)
    except HTTPException:
        raise
    except Exception as exc:
        print("ENG VISUAL ERROR:", type(exc).__name__, repr(exc)[:200])
        raise HTTPException(status_code=502, detail="The illustration could not be prepared.")


@app.post("/api/admin/eng/lesson-engine/visual/approve")
def approve_english_visual(body: VisualRequest, authorization: str = Header(None)):
    require_admin(authorization)
    row = _visual_record(body.plan_id, body.step_index)
    if not row:
        raise HTTPException(status_code=404, detail="Generate this illustration first.")
    sb.table("2027_eng_lesson_visuals").update({"review_status": "approved"})\
      .eq("id", row[0]["id"]).eq("review_status", "pending").execute()
    return {"approved": True, "id": row[0]["id"]}
