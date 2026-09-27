"""Admin-only OpenAI drafts for the English lesson engine."""

from typing import Literal

from fastapi import Header, HTTPException
from pydantic import BaseModel, Field

from main import aclient, app, guard_reply_payload, llm_model, require_admin, sb, spend_daily_budget
from eng_lessons_2027 import teacher_messages, validate_plan

TABLE = "2027_eng_lesson_plans"
PROMPT_VERSION = 2
MODEL = llm_model("gpt-4o-mini")


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
