from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client
from openai import OpenAI
from google import genai
from google.genai import types
from pathlib import Path
from datetime import datetime, timezone, timedelta
import io
import wave
import os
import json
import base64

# =====================================================
# CONFIG
# =====================================================

APP_NAME = "iakids AI Tutor Hebrew"
PROMPT_PATH = Path("prompts/iakids_ai_tutor_system_prompt.txt")
HOMEWORK_VISION_PROMPT_PATH = Path(
    "prompts/iakids_homework_vision_prompt.txt"
)
LESSON_PROMPT_PATH = Path(
    "prompts/iakids_structured_lesson_prompt.txt"
)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# =====================================================
# MODEL PRICING - USD
# =====================================================

# GPT-4o mini
OPENAI_INPUT_COST_PER_1M = 0.15
OPENAI_OUTPUT_COST_PER_1M = 0.60

# Gemini TTS
GEMINI_TTS_AUDIO_OUTPUT_COST_PER_1M = 10.00
GEMINI_AUDIO_TOKENS_PER_SECOND = 32
# =====================================================
# STRUCTURED LESSON PEDAGOGICAL ENGINE
# =====================================================

OBJECTIVE_MASTERY_THRESHOLD = 90


RESPONSE_QUALITY_POINTS = {

    "correct":
        10,

    "partial":
        5,

    "incorrect":
        0

}


INDEPENDENCE_POINTS = {

    "independent":
        5,

    "with_hint":
        2,

    "guided":
        0

}


UNDERSTANDING_POINTS = {

    "strong":
        5,

    "partial":
        2,

    "weak":
        0

}

if not SUPABASE_URL:
    raise RuntimeError("Missing SUPABASE_URL")

if not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY")

if not PROMPT_PATH.exists():
    raise RuntimeError(f"Missing prompt file: {PROMPT_PATH}")
if not LESSON_PROMPT_PATH.exists():
    raise RuntimeError(
        f"Missing lesson prompt file: "
        f"{LESSON_PROMPT_PATH}"
    )
if not HOMEWORK_VISION_PROMPT_PATH.exists():
    raise RuntimeError(
        f"Missing homework vision prompt file: "
        f"{HOMEWORK_VISION_PROMPT_PATH}"
    )

TUTOR_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")
LESSON_PROMPT_TEMPLATE = (
    LESSON_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
HOMEWORK_VISION_PROMPT = (
    HOMEWORK_VISION_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)

print("=== AI TUTOR PROMPT LOADED ===")
print(TUTOR_PROMPT_TEMPLATE[:300])
print("==============================")

# =====================================================
# CLIENTS
# =====================================================

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

client = OpenAI(
    api_key=OPENAI_API_KEY
)

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)

app = FastAPI(
    title=APP_NAME,
    version="0.1.0"
)

# =====================================================
# CORS
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://iakids.app",
        "https://www.iakids.app",
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# MODELS
# =====================================================

class TutorChatRequest(BaseModel):
    message: str
    kid_id: str


class TutorTTSRequest(BaseModel):
    text: str
    session_id: str | None = None

class HomeworkAnalyzeRequest(BaseModel):

    kid_id: str

    storage_path: str

    session_id: str | None = None

    file_name: str | None = None

    file_type: str | None = None

    file_size_bytes: int | None = None

    original_width: int | None = None

    original_height: int | None = None

    processed_width: int | None = None

    processed_height: int | None = None

    compression_quality: float | None = None


class TutorAction(BaseModel):
    type: str
    text: str | None = None
    target: str | None = None
    style: str | None = None
    speed: int | None = None
    duration: int | None = None
    speech_tts: str | None = None


class TutorLessonResponse(BaseModel):
    speech: str | None = None
    sequence: list[TutorAction]
    wait_for_answer: bool = False

# =====================================================
# STRUCTURED LESSON MODELS
# =====================================================


class StructuredLessonRequest(
    BaseModel
):

    kid_id: str

    lesson_id: int

    # ריק = פתיחת שיעור
    # עם טקסט = תשובת הילד
    message: str | None = None


class LessonEvaluation(
    BaseModel
):

    objective_index: int | None = None

    response_quality: str | None = None

    independence_level: str | None = None

    understanding_level: str | None = None

    hint_used: bool = False

    repeated_mistake: bool = False

    identified_difficulty: str | None = None

    evaluation_summary: str | None = None

    lesson_summary: str | None = None


class StructuredLessonResponse(
    BaseModel
):

    speech: str | None = None

    sequence: list[TutorAction]

    wait_for_answer: bool = False

    # בפתיחת שיעור אין עדיין מה להעריך
    evaluation: (
        LessonEvaluation |
        None
    ) = None
# =====================================================
# AUTH
# =====================================================

def authenticate_user(authorization: str):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth")

    token = authorization.replace("Bearer ", "").strip()

    try:
        user_res = sb.auth.get_user(token)
    except Exception as e:
        print("AUTH ERROR:", repr(e))
        raise HTTPException(status_code=401, detail="Invalid session")

    if not user_res or not user_res.user:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user_res.user


def update_tutor_session_after_tts(
        session_id: str,
        audio_duration_seconds: float = 0,
        cost_usd: float = 0
):
    """
    עדכון אטומי של Session לאחר קריאת TTS אחת.
    """

    if not session_id:
        return

    sb.rpc(
        "increment_tutor_session_tts",
        {
            "p_session_id": session_id,
            "p_audio_duration_seconds": audio_duration_seconds,
            "p_cost_usd": cost_usd
        }
    ).execute()

def update_tutor_session_after_vision(
        session_id: str,
        image_uploads: int = 1,
        vision_calls: int = 1
):

    if not session_id:
        return

    res = (
        sb.table("tutor_sessions")
        .select(
            "image_upload_count, "
            "vision_call_count"
        )
        .eq(
            "id",
            session_id
        )
        .single()
        .execute()
    )

    if not res.data:
        return

    current_image_uploads = int(
        res.data.get(
            "image_upload_count"
        ) or 0
    )

    current_vision_calls = int(
        res.data.get(
            "vision_call_count"
        ) or 0
    )

    sb.table(
        "tutor_sessions"
    ).update({

        "image_upload_count":
            current_image_uploads
            + image_uploads,

        "vision_call_count":
            current_vision_calls
            + vision_calls,

        "last_activity_at":
            datetime
            .now(timezone.utc)
            .isoformat(),

        "updated_at":
            datetime
            .now(timezone.utc)
            .isoformat()

    }).eq(
        "id",
        session_id
    ).execute()

# =====================================================
# DATA HELPERS
# =====================================================

def get_child_by_id(user_id: str, kid_id: str):
    res = (
        sb.table("kids_profiles")
        .select("*")
        .eq("id", kid_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Child not found")

    return res.data


def get_existing_kids_memory(kid_id: str) -> str:
    res = (
        sb.table("kids_memory")
        .select("memory")
        .eq("kid_id", kid_id)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )

    if not res.data:
        return ""

    memory = res.data[0].get("memory")

    if isinstance(memory, list):
        return "\n".join(f"- {item}" for item in memory)

    return str(memory or "")

# =====================================================
# STRUCTURED LESSON DATA HELPERS
# =====================================================


def get_learning_lesson(
        lesson_id: int
):

    res = (

        sb.table(
            "learning_lessons"
        )

        .select(
            "id, "
            "grade, "
            "subject, "
            "category, "
            "lesson_order, "
            "lesson_name, "
            "lesson_goal, "
            "lesson_content, "
            "teaching_method, "
            "learning_objectives, "
            "xp_reward, "
            "stars_reward, "
            "is_checkpoint, "
            "is_active"
        )

        .eq(
            "id",
            lesson_id
        )

        .eq(
            "is_active",
            True
        )

        .limit(1)

        .execute()

    )


    if not res.data:

        raise HTTPException(
            status_code=404,
            detail="Lesson not found"
        )


    return res.data[0]

def get_or_create_lesson_progress(
        kid_id: str,
        lesson: dict,
        session_id: str | None = None,
        is_lesson_start: bool = False
):

    lesson_id = lesson["id"]


    res = (

        sb.table(
            "kid_lesson_progress"
        )

        .select("*")

        .eq(
            "kid_id",
            kid_id
        )

        .eq(
            "lesson_id",
            lesson_id
        )

        .limit(1)

        .execute()

    )


    now = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )


    # =============================================
    # כבר קיימת התקדמות
    # =============================================

    if res.data:

        progress = res.data[0]


        update_data = {

            "last_session_id":
                session_id,

            "last_activity_at":
                now,

            "updated_at":
                now

        }


        # כל כניסה חדשה לשיעור
        # נחשבת ניסיון/חזרה לשיעור

        if is_lesson_start:

            update_data[
                "attempts_count"
            ] = (

                int(
                    progress.get(
                        "attempts_count"
                    ) or 0
                )

                + 1

            )


        updated = (

            sb.table(
                "kid_lesson_progress"
            )

            .update(
                update_data
            )

            .eq(
                "id",
                progress["id"]
            )

            .execute()

        )


        if updated.data:

            return updated.data[0]


        return progress


    # =============================================
    # שיעור חדש לילד
    # =============================================

    objectives = (

        lesson.get(
            "learning_objectives"
        )

        or []

    )


    objectives_progress = []


    for index, _ in enumerate(
        objectives,
        start=1
    ):

        objectives_progress.append({

            "objective_index":
                index,

            "score":
                0

        })


    insert_res = (

        sb.table(
            "kid_lesson_progress"
        )

        .insert({

            "kid_id":
                kid_id,

            "lesson_id":
                lesson_id,

            "status":
                "in_progress",

            "progress_percent":
                0,

            "mastery_score":
                0,

            "current_objective_index":
                1,

            "objectives_progress":
                objectives_progress,

            "attempts_count":
                1,

            "total_interactions":
                0,

            "hints_used":
                0,

            "consecutive_successes":
                0,

            "consecutive_failures":
                0,

            "last_session_id":
                session_id,

            "started_at":
                now,

            "last_activity_at":
                now,

            "created_at":
                now,

            "updated_at":
                now

        })

        .execute()

    )


    if not insert_res.data:

        raise RuntimeError(
            "Failed to create "
            "lesson progress"
        )


    return insert_res.data[0]

def get_recent_lesson_history_for_llm(
        kid_id: str,
        lesson_id: int,
        limit: int = 8
):

    res = (

        sb.table(
            "kid_lesson_history"
        )

        .select(
            "role, content"
        )

        .eq(
            "kid_id",
            kid_id
        )

        .eq(
            "lesson_id",
            lesson_id
        )

        .order(
            "created_at",
            desc=True
        )

        .limit(
            limit
        )

        .execute()

    )


    messages = list(
        reversed(
            res.data or []
        )
    )


    return [

        {

            "role":
                message["role"],

            "content":
                message["content"]

        }

        for message
        in messages

        if message.get(
            "role"
        ) in (
            "user",
            "assistant"
        )

    ]

def save_lesson_history(
        kid_id: str,
        lesson_id: int,
        session_id: str,
        objective_index: int | None,
        user_content: str | None,
        assistant_content: str,
        evaluation: dict | None,
        sequence_json: list | None
):

    rows = []


    # =============================================
    # תשובת הילד
    # =============================================

    if (
        user_content
        and user_content.strip()
    ):

        rows.append({

            "kid_id":
                kid_id,

            "lesson_id":
                lesson_id,

            "session_id":
                session_id,

            "objective_index":
                objective_index,

            "role":
                "user",

            "content":
                user_content.strip(),

            "evaluation":
                None,

            "sequence_json":
                None

        })


    # =============================================
    # תשובת המורה
    # =============================================

    rows.append({

        "kid_id":
            kid_id,

        "lesson_id":
            lesson_id,

        "session_id":
            session_id,

        "objective_index":
            objective_index,

        "role":
            "assistant",

        "content":
            assistant_content,

        "evaluation":
            evaluation,

        "sequence_json":
            sequence_json

    })


    sb.table(
        "kid_lesson_history"
    ).insert(
        rows
    ).execute()

    def calculate_objective_delta(
            evaluation: dict
    ):

        delta = 0

        response_quality = (
            evaluation.get(
                "response_quality"
            )
        )

        independence_level = (
            evaluation.get(
                "independence_level"
            )
        )

        understanding_level = (
            evaluation.get(
                "understanding_level"
            )
        )

        delta += (
            RESPONSE_QUALITY_POINTS
            .get(
                response_quality,
                0
            )
        )

        delta += (
            INDEPENDENCE_POINTS
            .get(
                independence_level,
                0
            )
        )

        delta += (
            UNDERSTANDING_POINTS
            .get(
                understanding_level,
                0
            )
        )

        # טעות חוזרת מורידה מעט
        # את רמת השליטה הנוכחית

        if evaluation.get(
                "repeated_mistake"
        ):
            delta -= 2

        return delta

    def apply_lesson_evaluation(
            progress: dict,
            lesson: dict,
            evaluation: dict,
            session_id: str
    ):

        now = datetime.now(
            timezone.utc
        )

        objectives_progress = (

                progress.get(
                    "objectives_progress"
                )

                or []

        )

        objective_index = (

                evaluation.get(
                    "objective_index"
                )

                or progress.get(
            "current_objective_index"
        )

                or 1

        )

        delta = (
            calculate_objective_delta(
                evaluation
            )
        )

        # =============================================
        # עדכון ציון היעד הנוכחי
        # =============================================

        for objective in (
                objectives_progress
        ):

            if (

                    int(
                        objective.get(
                            "objective_index",
                            0
                        )
                    )

                    == int(
                objective_index
            )

            ):
                old_score = int(

                    objective.get(
                        "score"
                    )

                    or 0

                )

                new_score = max(

                    0,

                    min(

                        100,

                        old_score
                        + delta

                    )

                )

                objective[
                    "score"
                ] = new_score

                break

        # =============================================
        # ציוני כל היעדים
        # =============================================

        scores = [

            int(
                objective.get(
                    "score"
                )

                or 0
            )

            for objective
            in objectives_progress

        ]

        # =============================================
        # התקדמות כוללת בשיעור
        #
        # ממוצע של כל היעדים
        # =============================================

        if scores:

            progress_percent = round(

                sum(scores)
                /
                len(scores)

            )

        else:

            progress_percent = 0

        # =============================================
        # Mastery
        #
        # ממוצע היעדים שכבר התחילו
        # =============================================

        started_scores = [

            score

            for score
            in scores

            if score > 0

        ]

        if started_scores:

            mastery_score = round(

                sum(
                    started_scores
                )

                /
                len(
                    started_scores
                )

            )

        else:

            mastery_score = 0

        # =============================================
        # מציאת היעד הבא שעדיין
        # לא הגיע לסף שליטה
        # =============================================

        next_objective_index = None

        for objective in (
                objectives_progress
        ):

            if (

                    int(
                        objective.get(
                            "score"
                        )

                        or 0
                    )

                    <
                    OBJECTIVE_MASTERY_THRESHOLD

            ):
                next_objective_index = (

                    objective[
                        "objective_index"
                    ]

                )

                break

        # =============================================
        # האם השיעור הסתיים
        # =============================================

        lesson_completed = (

                bool(
                    objectives_progress
                )

                and

                all(

                    int(
                        objective.get(
                            "score"
                        )

                        or 0
                    )

                    >=
                    OBJECTIVE_MASTERY_THRESHOLD

                    for objective
                    in objectives_progress

                )

        )

        if lesson_completed:

            status = (
                "completed"
            )

            progress_percent = 100

            next_objective_index = None


        else:

            status = (
                "in_progress"
            )

        # =============================================
        # רצף הצלחות / קשיים
        # =============================================

        response_quality = (

            evaluation.get(
                "response_quality"
            )

        )

        current_successes = int(

            progress.get(
                "consecutive_successes"
            )

            or 0

        )

        current_failures = int(

            progress.get(
                "consecutive_failures"
            )

            or 0

        )

        if response_quality == "correct":

            consecutive_successes = (

                    current_successes
                    + 1

            )

            consecutive_failures = 0


        elif response_quality == "incorrect":

            consecutive_successes = 0

            consecutive_failures = (

                    current_failures
                    + 1

            )


        else:

            consecutive_successes = 0

            consecutive_failures = 0

        hints_used = int(

            progress.get(
                "hints_used"
            )

            or 0

        )

        if evaluation.get(
                "hint_used"
        ):
            hints_used += 1

        update_data = {

            "status":
                status,

            "progress_percent":
                progress_percent,

            "mastery_score":
                mastery_score,

            "current_objective_index":
                next_objective_index,

            "objectives_progress":
                objectives_progress,

            "total_interactions":

                int(
                    progress.get(
                        "total_interactions"
                    )

                    or 0
                )

                + 1,

            "hints_used":
                hints_used,

            "consecutive_successes":
                consecutive_successes,

            "consecutive_failures":
                consecutive_failures,

            "last_evaluation":
                evaluation,

            "last_error_type":
                evaluation.get(
                    "identified_difficulty"
                ),

            "last_session_id":
                session_id,

            "last_activity_at":
                now.isoformat(),

            "updated_at":
                now.isoformat()

        }

        # =============================================
        # השלמת שיעור
        # =============================================

        if lesson_completed:
            update_data[
                "completed_at"
            ] = (
                now.isoformat()
            )

            update_data[
                "xp_earned"
            ] = int(

                lesson.get(
                    "xp_reward"
                )

                or 0

            )

            update_data[
                "stars_earned"
            ] = int(

                lesson.get(
                    "stars_reward"
                )

                or 0

            )

        updated = (

            sb.table(
                "kid_lesson_progress"
            )

            .update(
                update_data
            )

            .eq(
                "id",
                progress["id"]
            )

            .execute()

        )

        if updated.data:
            return updated.data[0]

        return {
            **progress,
            **update_data
        }


# =====================================================
# TUTOR SESSION HELPERS
# =====================================================

SESSION_TIMEOUT_MINUTES = 30


def parse_supabase_datetime(value: str):
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def get_or_create_tutor_session(
        user_id: str,
        kid_id: str
):
    """
    מחפש את ה-Session האחרון של הילד.

    אם ה-Session עדיין פעיל ולא עברו 30 דקות
    מהפעילות האחרונה -> משתמשים בו.

    אחרת -> סוגרים את הקודם ופותחים Session חדש.
    """

    now = datetime.now(timezone.utc)

    res = (
        sb.table("tutor_sessions")
        .select(
            "id, started_at, last_activity_at, status, "
            "message_count, user_message_count, "
            "assistant_message_count, ai_call_count, "
            "input_tokens, output_tokens, total_tokens, "
            "estimated_cost_usd"
        )
        .eq("user_id", user_id)
        .eq("kid_id", kid_id)
        .eq("status", "active")
        .order("last_activity_at", desc=True)
        .limit(1)
        .execute()
    )

    # =================================================
    # אם קיים Session פעיל
    # =================================================

    if res.data:

        session = res.data[0]

        last_activity = parse_supabase_datetime(
            session.get("last_activity_at")
        )

        if last_activity:

            inactive_time = now - last_activity

            # עדיין בתוך חלון 30 הדקות
            if inactive_time < timedelta(
                    minutes=SESSION_TIMEOUT_MINUTES
            ):
                session["_is_new"] = False

                return session

        # =================================================
        # ה-Session ישן יותר מ-30 דקות
        # סוגרים אותו
        # =================================================

        started_at = parse_supabase_datetime(
            session.get("started_at")
        )

        duration_seconds = 0

        if started_at and last_activity:
            duration_seconds = max(
                0,
                int(
                    (
                            last_activity - started_at
                    ).total_seconds()
                )
            )

        sb.table("tutor_sessions").update({
            "status": "completed",
            "ended_at": (
                    last_activity or now
            ).isoformat(),
            "duration_seconds": duration_seconds,
            "updated_at": now.isoformat()
        }).eq(
            "id",
            session["id"]
        ).execute()

        # מוסיפים את זמן השיחה לסיכום החודשי
        increment_usage_summary(
            user_id=user_id,
            usage_seconds=duration_seconds
        )
    # =================================================
    # פתיחת Session חדש
    # =================================================

    new_session_res = (
        sb.table("tutor_sessions")
        .insert({
            "user_id": user_id,
            "kid_id": kid_id,
            "started_at": now.isoformat(),
            "last_activity_at": now.isoformat(),
            "status": "active",
            "ai_model": "gpt-4o-mini",
            "tts_model": "gemini-3.1-flash-tts-preview"
        })
        .execute()
    )

    if not new_session_res.data:
        raise RuntimeError(
            "Failed to create tutor session"
        )

    new_session = new_session_res.data[0]

    new_session["_is_new"] = True

    return new_session


def save_tutor_chat_messages(
        user_id: str,
        kid_id: str,
        user_content: str,
        assistant_content: str,
        assistant_tokens: int | None = None,
        session_id: str | None = None
):
    user_payload = {
        "user_id": user_id,
        "kid_id": kid_id,
        "role": "user",
        "content": user_content,
    }

    assistant_payload = {
        "user_id": user_id,
        "kid_id": kid_id,
        "role": "assistant",
        "content": assistant_content,
    }

    if assistant_tokens is not None:
        assistant_payload["tokens"] = assistant_tokens

    if session_id:
        user_payload["session_id"] = session_id
        assistant_payload["session_id"] = session_id

    # שתי ההודעות נשמרות בקריאת Supabase אחת
    sb.table("kids_chats").insert([
        user_payload,
        assistant_payload
    ]).execute()


def increment_usage_summary(
        user_id: str,
        sessions: int = 0,
        usage_seconds: int = 0,
        ai_calls: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        tts_calls: int = 0,
        tts_seconds: float = 0,
        voice_output_seconds: float = 0,
        image_uploads: int = 0,
        vision_calls: int = 0,
        file_uploads: int = 0,
        file_analysis_calls: int = 0,
        errors: int = 0,
        openai_cost_usd: float = 0,
        gemini_cost_usd: float = 0,
        vision_cost_usd: float = 0,
        realtime_cost_usd: float = 0,
        other_cost_usd: float = 0
):
    """
    עדכון מצטבר של usage_summary.
    מתבצע באמצעות RPC אחד בלבד.
    """

    sb.rpc(
        "increment_usage_summary",
        {
            "p_user_id": user_id,

            "p_sessions": sessions,
            "p_usage_seconds": usage_seconds,

            "p_ai_calls": ai_calls,
            "p_input_tokens": input_tokens,
            "p_output_tokens": output_tokens,
            "p_total_tokens": total_tokens,

            "p_tts_calls": tts_calls,
            "p_tts_seconds": tts_seconds,
            "p_voice_output_seconds": voice_output_seconds,

            "p_image_uploads": image_uploads,
            "p_vision_calls": vision_calls,

            "p_file_uploads": file_uploads,
            "p_file_analysis_calls": file_analysis_calls,

            "p_errors": errors,

            "p_openai_cost_usd": openai_cost_usd,
            "p_gemini_cost_usd": gemini_cost_usd,
            "p_vision_cost_usd": vision_cost_usd,
            "p_realtime_cost_usd": realtime_cost_usd,
            "p_other_cost_usd": other_cost_usd
        }
    ).execute()


def update_tutor_session_after_chat(
        session: dict,
        total_tokens: int | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float = 0
):
    """
    עדכון מצטבר של Session לאחר אינטראקציית צ'אט אחת.
    """

    now = datetime.now(timezone.utc)

    started_at = parse_supabase_datetime(
        session.get("started_at")
    )

    duration_seconds = 0

    if started_at:
        duration_seconds = max(
            0,
            int(
                (
                        now - started_at
                ).total_seconds()
            )
        )

    new_input_tokens = (
            int(session.get("input_tokens") or 0)
            + int(input_tokens or 0)
    )

    new_output_tokens = (
            int(session.get("output_tokens") or 0)
            + int(output_tokens or 0)
    )

    new_total_tokens = (
            int(session.get("total_tokens") or 0)
            + int(total_tokens or 0)
    )
    new_estimated_cost_usd = (
            float(session.get("estimated_cost_usd") or 0)
            + float(cost_usd or 0)
    )

    sb.table("tutor_sessions").update({

        "last_activity_at": now.isoformat(),

        "duration_seconds": duration_seconds,

        # בכל אינטראקציה נשמרות 2 הודעות:
        # ילד + AI
        "message_count":
            int(session.get("message_count") or 0) + 2,

        "user_message_count":
            int(session.get("user_message_count") or 0) + 1,

        "assistant_message_count":
            int(session.get("assistant_message_count") or 0) + 1,

        # קריאת OpenAI אחת
        "ai_call_count":
            int(session.get("ai_call_count") or 0) + 1,

        "input_tokens": new_input_tokens,

        "output_tokens": new_output_tokens,

        "total_tokens": new_total_tokens,

        "estimated_cost_usd": new_estimated_cost_usd,

        "updated_at": now.isoformat()

    }).eq(
        "id",
        session["id"]
    ).execute()


def get_recent_tutor_messages_for_llm(
        kid_id: str,
        limit: int = 8
):
    res = (
        sb.table("kids_chats")
        .select("role, content")
        .eq("kid_id", kid_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    messages = list(reversed(res.data or []))

    return [
        {
            "role": message["role"],
            "content": message["content"]
        }
        for message in messages
        if message.get("role") in ("user", "assistant")
    ]


def build_tutor_prompt(child: dict, kids_memory: str) -> str:
    prompt = TUTOR_PROMPT_TEMPLATE

    replacements = {
        "{child_name}": str(child.get("child_name", "")),
        "{age}": str(child.get("age", "")),
        "{grade}": str(child.get("grade", "")),
        "{avatar_key}": str(child.get("avatar_key", "")),
        "{learning_interests}": ", ".join(
            child.get("learning_interests") or []
        ),
        "{usage_goals}": ", ".join(
            child.get("usage_goals") or []
        ),
        "{kids_memory}": kids_memory or "",
    }

    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)

    return prompt

def build_structured_lesson_prompt(
        child: dict,
        lesson: dict,
        progress: dict,
        turn_type: str
):

    runtime_context = {

        "turn_type":
            turn_type,


        "child": {

            "name":
                child.get(
                    "child_name"
                ),

            # אצלך age מכיל כרגע
            # את מספר הכיתה 1-6

            "grade":
                child.get(
                    "age"
                ),

            "avatar_key":
                child.get(
                    "avatar_key"
                ),

            "learning_interests":
                child.get(
                    "learning_interests"
                )

                or [],

            "usage_goals":
                child.get(
                    "usage_goals"
                )

                or []

        },


        "lesson": {

            "lesson_id":
                lesson.get(
                    "id"
                ),

            "subject":
                lesson.get(
                    "subject"
                ),

            "category":
                lesson.get(
                    "category"
                ),

            "lesson_name":
                lesson.get(
                    "lesson_name"
                ),

            "lesson_goal":
                lesson.get(
                    "lesson_goal"
                ),

            "lesson_content":
                lesson.get(
                    "lesson_content"
                ),

            "teaching_method":
                lesson.get(
                    "teaching_method"
                ),

            "learning_objectives":
                lesson.get(
                    "learning_objectives"
                )

                or []

        },


        "progress": {

            "status":
                progress.get(
                    "status"
                ),

            "progress_percent":
                progress.get(
                    "progress_percent"
                ),

            "mastery_score":
                progress.get(
                    "mastery_score"
                ),

            "current_objective_index":
                progress.get(
                    "current_objective_index"
                ),

            "objectives_progress":
                progress.get(
                    "objectives_progress"
                )

                or [],

            "hints_used":
                progress.get(
                    "hints_used"
                ),

            "consecutive_successes":
                progress.get(
                    "consecutive_successes"
                ),

            "consecutive_failures":
                progress.get(
                    "consecutive_failures"
                ),

            "last_error_type":
                progress.get(
                    "last_error_type"
                )

        }

    }


    return (

        LESSON_PROMPT_TEMPLATE

        +

        "\n\n"
        "RUNTIME_CONTEXT:\n"

        +

        json.dumps(

            runtime_context,

            ensure_ascii=False

        )

    )


# =====================================================
# HEALTH
# =====================================================

@app.get("/")
def root():
    return {
        "service": APP_NAME,
        "status": "ok"
    }


@app.get("/api/tutor/health")
def tutor_health():
    return {
        "status": "ok",
        "service": "ai-tutor-he"
    }


# =====================================================
# AI TUTOR NATURAL VOICE - GEMINI TTS
# =====================================================

@app.post("/api/tutor/tts")
def tutor_tts(
        body: TutorTTSRequest,
        authorization: str = Header(None)
):
    try:

        # אימות משתמש
        user = authenticate_user(authorization)

        text = (body.text or "").strip()

        if not text:
            raise HTTPException(
                status_code=400,
                detail="text is required"
            )

        if len(text) > 1500:
            raise HTTPException(
                status_code=400,
                detail="text is too long"
            )

        # Gemini TTS
        response = gemini_client.models.generate_content(
            model="gemini-3.1-flash-tts-preview",

            contents=(
                    "Speak in natural, fluent Hebrew. "
                    "Sound like a warm, friendly and patient teacher "
                    "speaking naturally to a school-age child. "
                    "Use clear pronunciation, natural pauses, "
                    "and an encouraging tone. "
                    "Read exactly the following Hebrew text:\n\n"
                    + text
            ),

            config=types.GenerateContentConfig(

                response_modalities=[
                    "AUDIO"
                ],

                speech_config=types.SpeechConfig(

                    voice_config=
                    types.VoiceConfig(

                        prebuilt_voice_config=
                        types.PrebuiltVoiceConfig(
                            voice_name="Aoede"
                        )

                    )

                )

            )

        )

        # קבלת PCM audio
        audio_data = (
            response
            .candidates[0]
            .content
            .parts[0]
            .inline_data
            .data
        )

        if not audio_data:
            raise RuntimeError(
                "Gemini returned no audio data"
            )

        # =================================================
        # AUDIO DURATION
        # PCM 16-bit mono at 24kHz
        # 2 bytes per sample
        # =================================================

        audio_duration_seconds = (
                len(audio_data)
                / (24000 * 2)
        )
        audio_output_tokens = (
                audio_duration_seconds
                * GEMINI_AUDIO_TOKENS_PER_SECOND
        )

        gemini_audio_cost_usd = (
                audio_output_tokens
                / 1_000_000
                * GEMINI_TTS_AUDIO_OUTPUT_COST_PER_1M
        )
        # =================================================
        # PCM -> WAV
        # Gemini מחזיר PCM 16-bit, mono, 24kHz
        # =================================================

        wav_buffer = io.BytesIO()

        with wave.open(
                wav_buffer,
                "wb"
        ) as wav_file:

            wav_file.setnchannels(1)

            # 16-bit audio = 2 bytes
            wav_file.setsampwidth(2)

            # 24 kHz
            wav_file.setframerate(24000)

            wav_file.writeframes(
                audio_data
            )

        wav_buffer.seek(0)

        wav_bytes = wav_buffer.read()

        # עדכון Session - קריאת TTS אחת
        if body.session_id:
            update_tutor_session_after_tts(
                session_id=body.session_id,
                audio_duration_seconds=audio_duration_seconds,
                cost_usd=gemini_audio_cost_usd
            )

            increment_usage_summary(
                user_id=user.id,

                tts_calls=1,

                tts_seconds=
                audio_duration_seconds,

                voice_output_seconds=
                audio_duration_seconds,

                gemini_cost_usd=gemini_audio_cost_usd
            )

        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={
                "Cache-Control": "no-store"
            }
        )


    except HTTPException:
        raise


    except Exception as e:

        print(
            "GEMINI TTS ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Gemini TTS failed"
        )


# =====================================================
# STRUCTURED AI LESSON
# =====================================================

@app.post(
    "/api/tutor/lesson"
)
def structured_lesson(
        body: StructuredLessonRequest,
        authorization: str = Header(None)
):

    try:

        # =============================================
        # AUTH
        # =============================================

        user = authenticate_user(
            authorization
        )


        if not body.kid_id:

            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )


        # =============================================
        # CHILD
        # =============================================

        child = get_child_by_id(

            user_id=user.id,

            kid_id=body.kid_id

        )


        # =============================================
        # LESSON
        # =============================================

        lesson = get_learning_lesson(
            body.lesson_id
        )


        # =============================================
        # SECURITY
        #
        # מוודאים שהשיעור מתאים לכיתה
        # של הילד
        # =============================================

        child_grade = int(

            child.get(
                "age"
            )

            or 0

        )


        lesson_grade = int(

            lesson.get(
                "grade"
            )

            or 0

        )


        if (

            child_grade
            and lesson_grade
            and child_grade != lesson_grade

        ):

            raise HTTPException(

                status_code=403,

                detail=(
                    "Lesson does not match "
                    "child grade"
                )

            )


        # =============================================
        # SESSION
        # =============================================

        tutor_session = (

            get_or_create_tutor_session(

                user_id=user.id,

                kid_id=child["id"]

            )

        )


        session_id = (
            tutor_session["id"]
        )


        # =============================================
        # האם זו פתיחת שיעור
        # =============================================

        message = (

            body.message
            or ""

        ).strip()


        is_lesson_start = (

            not bool(
                message
            )

        )


        turn_type = (

            "start"

            if is_lesson_start

            else "student_response"

        )


        # =============================================
        # PROGRESS
        # =============================================

        progress = (

            get_or_create_lesson_progress(

                kid_id=child["id"],

                lesson=lesson,

                session_id=session_id,

                is_lesson_start=
                    is_lesson_start

            )

        )


        # =============================================
        # PROMPT
        # =============================================

        system_prompt = (

            build_structured_lesson_prompt(

                child=child,

                lesson=lesson,

                progress=progress,

                turn_type=turn_type

            )

        )


        # =============================================
        # HISTORY
        # =============================================

        recent_messages = (

            get_recent_lesson_history_for_llm(

                kid_id=
                    child["id"],

                lesson_id=
                    lesson["id"],

                limit=8

            )

        )


        # =============================================
        # CURRENT TURN
        # =============================================

        if is_lesson_start:

            current_message = (

                "התחל את השיעור המובנה "
                "מהיעד הנוכחי. "
                "זהו תור פתיחת שיעור ולכן "
                "אין להעריך עדיין תשובת תלמיד."

            )


        else:

            current_message = (
                message
            )


        recent_messages.append({

            "role":
                "user",

            "content":
                current_message

        })


        # =============================================
        # OPENAI
        # =============================================

        completion = (

            client
            .beta
            .chat
            .completions
            .parse(

                model=
                    "gpt-4o-mini",

                messages=[

                    {

                        "role":
                            "system",

                        "content":
                            system_prompt

                    },

                    *recent_messages

                ],

                response_format=
                    StructuredLessonResponse

            )

        )


        lesson_data = (

            completion
            .choices[0]
            .message
            .parsed

        )


        if not lesson_data:

            raise HTTPException(

                status_code=500,

                detail=(
                    "Structured lesson "
                    "returned no response"
                )

            )


        # =============================================
        # EVALUATION
        #
        # רק אחרי תשובה אמיתית של הילד
        # =============================================

        evaluation_dict = None


        if (

            not is_lesson_start

            and

            lesson_data.evaluation

        ):

            evaluation_dict = (

                lesson_data
                .evaluation
                .model_dump()

            )


            progress = (

                apply_lesson_evaluation(

                    progress=progress,

                    lesson=lesson,

                    evaluation=
                        evaluation_dict,

                    session_id=
                        session_id

                )

            )


        # =============================================
        # CLEAN ASSISTANT HISTORY
        # =============================================

        assistant_history_parts = []


        if lesson_data.speech:

            assistant_history_parts.append(

                lesson_data
                .speech
                .strip()

            )


        for action in (

            lesson_data.sequence
            or []

        ):

            if (

                action.type
                in (
                    "write",
                    "ask"
                )

                and action.text

                and action.text.strip()

            ):

                clean_text = (

                    action.text
                    .strip()

                )


                if (

                    clean_text

                    not in
                    assistant_history_parts

                ):

                    assistant_history_parts.append(

                        clean_text

                    )


        assistant_history_text = (

            "\n".join(

                assistant_history_parts

            )

        )


        # =============================================
        # SAVE LESSON HISTORY
        # =============================================

        save_lesson_history(

            kid_id=
                child["id"],

            lesson_id=
                lesson["id"],

            session_id=
                session_id,

            objective_index=
                progress.get(
                    "current_objective_index"
                ),

            user_content=(

                None

                if is_lesson_start

                else message

            ),

            assistant_content=
                assistant_history_text,

            evaluation=
                evaluation_dict,

            sequence_json=[

                action.model_dump()

                for action
                in lesson_data.sequence

            ]

        )


        # =============================================
        # TOKEN USAGE
        # =============================================

        total_tokens = 0

        input_tokens = 0

        output_tokens = 0


        if completion.usage:

            total_tokens = (

                completion
                .usage
                .total_tokens

                or 0

            )


            input_tokens = (

                completion
                .usage
                .prompt_tokens

                or 0

            )


            output_tokens = (

                completion
                .usage
                .completion_tokens

                or 0

            )


        openai_cost_usd = (

            (
                input_tokens
                / 1_000_000
            )

            *
            OPENAI_INPUT_COST_PER_1M

            +

            (
                output_tokens
                / 1_000_000
            )

            *
            OPENAI_OUTPUT_COST_PER_1M

        )


        # =============================================
        # SESSION USAGE
        # =============================================

        update_tutor_session_after_chat(

            session=
                tutor_session,

            total_tokens=
                total_tokens,

            input_tokens=
                input_tokens,

            output_tokens=
                output_tokens,

            cost_usd=
                openai_cost_usd

        )


        increment_usage_summary(

            user_id=
                user.id,

            sessions=(

                1

                if tutor_session.get(
                    "_is_new"
                )

                else 0

            ),

            ai_calls=
                1,

            input_tokens=
                input_tokens,

            output_tokens=
                output_tokens,

            total_tokens=
                total_tokens,

            openai_cost_usd=
                openai_cost_usd

        )


        # =============================================
        # RESPONSE TO FRONTEND
        # =============================================

        response_data = (

            lesson_data
            .model_dump()

        )


        response_data[
            "session_id"
        ] = session_id


        response_data[
            "lesson_id"
        ] = lesson["id"]


        response_data[
            "progress"
        ] = {

            "status":
                progress.get(
                    "status"
                ),

            "progress_percent":
                progress.get(
                    "progress_percent"
                ),

            "mastery_score":
                progress.get(
                    "mastery_score"
                ),

            "current_objective_index":
                progress.get(
                    "current_objective_index"
                ),

            "objectives_progress":
                progress.get(
                    "objectives_progress"
                )

        }


        return response_data


    except HTTPException:

        raise


    except Exception as e:

        print(

            "STRUCTURED LESSON ERROR:",

            repr(e)

        )


        raise HTTPException(

            status_code=500,

            detail=(
                "Structured lesson failed"
            )

        )
    
    
# =====================================================
# HOMEWORK IMAGE / PDF ANALYSIS
# =====================================================

@app.post(
    "/api/tutor/homework-analyze"
)
def homework_analyze(
        body: HomeworkAnalyzeRequest,
        authorization: str = Header(None)
):

    upload_row_id = None

    try:

        # =============================================
        # AUTH
        # =============================================

        user = authenticate_user(
            authorization
        )

        if not body.kid_id:

            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )


        if not body.storage_path:

            raise HTTPException(
                status_code=400,
                detail="storage_path is required"
            )


        # =============================================
        # מוודאים שהילד שייך למשתמש
        # =============================================

        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )


        # =============================================
        # SECURITY
        #
        # הנתיב חייב להתחיל ב-user_id
        #
        # user_id/kid_id/file.jpg
        # =============================================

        expected_prefix = (
            f"{user.id}/"
        )

        if not body.storage_path.startswith(
            expected_prefix
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "Invalid storage path"
                )
            )


        # =============================================
        # SESSION
        # =============================================

        if body.session_id:

            session_id = (
                body.session_id
            )

        else:

            tutor_session = (
                get_or_create_tutor_session(
                    user_id=user.id,
                    kid_id=child["id"]
                )
            )

            session_id = (
                tutor_session["id"]
            )


        # =============================================
        # CREATE homework_uploads ROW
        # =============================================

        upload_res = (

            sb.table(
                "homework_uploads"
            )

            .insert({

                "user_id":
                    user.id,

                "kid_id":
                    child["id"],

                "session_id":
                    session_id,

                "file_name":
                    body.file_name,

                "file_type":
                    body.file_type,

                "storage_path":
                    body.storage_path,

                "file_size_bytes":
                    body.file_size_bytes,

                "original_width":
                    body.original_width,

                "original_height":
                    body.original_height,

                "processed_width":
                    body.processed_width,

                "processed_height":
                    body.processed_height,

                "compression_quality":
                    body.compression_quality,

                "vision_status":
                    "processing",

                "vision_model":
                    "gpt-4o-mini",

                "vision_call_count":
                    0

            })

            .execute()

        )


        if not upload_res.data:

            raise RuntimeError(
                "Failed to create "
                "homework_uploads row"
            )


        upload_row_id = (
            upload_res.data[0]["id"]
        )


        # =============================================
        # DOWNLOAD FILE FROM PRIVATE STORAGE
        # =============================================

        file_bytes = (

            sb.storage

            .from_(
                "homework-uploads"
            )

            .download(
                body.storage_path
            )

        )


        if not file_bytes:

            raise RuntimeError(
                "Failed to download "
                "homework file"
            )


        # =============================================
        # MIME TYPE
        # =============================================

        mime_type = (
            body.file_type
            or "image/jpeg"
        )


        allowed_mime_types = {

            "image/jpeg",

            "image/png",

            "image/webp",

            "application/pdf"

        }


        if mime_type not in (
            allowed_mime_types
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported file type"
                )
            )

        # =============================================
        # SEND TO OPENAI GPT-4o MINI VISION
        # =============================================

        base64_file = base64.b64encode(
            file_bytes
        ).decode("utf-8")

        if mime_type == "application/pdf":
            raise HTTPException(
                status_code=400,
                detail=(
                    "PDF analysis is not supported "
                    "yet in GPT-4o-mini image mode"
                )
            )

        data_url = (
            f"data:{mime_type};base64,"
            f"{base64_file}"
        )

        response = client.chat.completions.create(

            model="gpt-4o-mini",

            messages=[

                {
                    "role": "system",
                    "content":
                        HOMEWORK_VISION_PROMPT
                },

                {
                    "role": "user",
                    "content": [

                        {
                            "type": "text",
                            "text":
                                "Analyze this homework image "
                                "and return only the requested JSON."
                        },

                        {
                            "type": "image_url",
                            "image_url": {
                                "url":
                                    data_url,

                                "detail":
                                    "high"
                            }
                        }

                    ]
                }

            ],

            response_format={
                "type":
                    "json_object"
            },

            temperature=0.1

        )

        # =============================================
        # PARSE RESPONSE
        # =============================================

        raw_response = (
                response.choices[0].message.content or ""
        ).strip()


        if not raw_response:

            raise RuntimeError(
                "Gemini Vision "
                "returned empty response"
            )


        try:

            analysis = json.loads(
                raw_response
            )

        except json.JSONDecodeError:

            print(
                "VISION INVALID JSON:",
                raw_response
            )

            raise RuntimeError(
                "Gemini Vision "
                "returned invalid JSON"
            )


        # =============================================
        # EXTRACT VALUES
        # =============================================

        extracted_text = (
            analysis.get(
                "extracted_text"
            )
            or ""
        )


        detected_subject = (
            analysis.get(
                "subject"
            )
        )


        detected_topic = (
            analysis.get(
                "topic"
            )
        )


        detected_language = (
            analysis.get(
                "language"
            )
        )


        needs_high_resolution = bool(

            analysis.get(
                "needs_high_resolution",
                False
            )

        )


        confidence = float(

            analysis.get(
                "confidence",
                0
            )

            or 0

        )


        # =============================================
        # TOKEN USAGE
        # =============================================

        input_tokens = 0

        output_tokens = 0

        total_tokens = 0

        if response.usage:
            input_tokens = response.usage.prompt_tokens or 0
            output_tokens = response.usage.completion_tokens or 0
            total_tokens = response.usage.total_tokens or 0

        # =============================================
        # STATUS
        # =============================================

        if needs_high_resolution:

            vision_status = (
                "needs_high_resolution"
            )

        else:

            vision_status = (
                "completed"
            )


        # =============================================
        # UPDATE homework_uploads
        # =============================================

        sb.table(
            "homework_uploads"
        ).update({

            "vision_status":
                vision_status,

            "vision_model":
                "gpt-4o-mini",

            "vision_call_count":
                1,

            "extracted_text":
                extracted_text,

            "detected_subject":
                detected_subject,

            "detected_topic":
                detected_topic,

            "detected_language":
                detected_language,

            "analysis_json":
                analysis,

            "input_tokens":
                input_tokens,

            "output_tokens":
                output_tokens,

            "total_tokens":
                total_tokens,

            "used_high_resolution":
                False,

            "updated_at":
                datetime
                .now(timezone.utc)
                .isoformat()

        }).eq(

            "id",
            upload_row_id

        ).execute()


        # =============================================
        # SESSION USAGE
        # =============================================

        update_tutor_session_after_vision(

            session_id=session_id,

            image_uploads=1,

            vision_calls=1

        )


        # =============================================
        # MONTHLY USAGE
        # =============================================

        increment_usage_summary(

            user_id=user.id,

            image_uploads=1,

            vision_calls=1

        )


        # =============================================
        # RESPONSE TO FRONTEND
        # =============================================

        return {

            "success":
                True,

            "upload_id":
                upload_row_id,

            "session_id":
                session_id,

            "vision_status":
                vision_status,

            "needs_high_resolution":
                needs_high_resolution,

            "confidence":
                confidence,

            "subject":
                detected_subject,

            "topic":
                detected_topic,

            "language":
                detected_language,

            "extracted_text":
                extracted_text,

            "analysis":
                analysis

        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "HOMEWORK ANALYZE ERROR:",
            repr(e)
        )


        # =============================================
        # UPDATE FAILED ROW
        # =============================================

        if upload_row_id:

            try:

                sb.table(
                    "homework_uploads"
                ).update({

                    "vision_status":
                        "failed",

                    "vision_error":
                        str(e)[:1000],

                    "updated_at":
                        datetime
                        .now(timezone.utc)
                        .isoformat()

                }).eq(

                    "id",
                    upload_row_id

                ).execute()

            except Exception as update_error:

                print(
                    "HOMEWORK ERROR UPDATE FAILED:",
                    repr(update_error)
                )


        raise HTTPException(

            status_code=500,

            detail=(
                "Homework analysis failed"
            )

        )

# =====================================================
# AI TUTOR CHAT
# =====================================================

@app.post("/api/tutor/chat")
def tutor_chat(
        body: TutorChatRequest,
        authorization: str = Header(None)
):
    try:
        # אימות משתמש
        user = authenticate_user(authorization)

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        message = (body.message or "").strip()

        if not message:
            raise HTTPException(
                status_code=400,
                detail="message is required"
            )

        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )

        # =================================================
        # GET OR CREATE TUTOR SESSION
        # =================================================

        tutor_session = get_or_create_tutor_session(
            user_id=user.id,
            kid_id=child["id"]
        )

        session_id = tutor_session["id"]

        existing_memory = get_existing_kids_memory(
            child["id"]
        )

        system_prompt = build_tutor_prompt(
            child=child,
            kids_memory=existing_memory
        )

        # מביאים רק את ההיסטוריה הקודמת.
        # את ההודעה הנוכחית נוסיף מקומית ולא נשמור לפני קריאת ה-AI.
        recent_messages = get_recent_tutor_messages_for_llm(
            kid_id=child["id"],
            limit=7
        )

        recent_messages.append({
            "role": "user",
            "content": message
        })

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                *recent_messages
            ],
            response_format=TutorLessonResponse
        )

        lesson_data = completion.choices[0].message.parsed

        if lesson_data and lesson_data.sequence:

            has_write = any(
                action.type == "write"
                for action in lesson_data.sequence
            )

            if not has_write and lesson_data.speech:
                lesson_data.sequence.insert(
                    0,
                    TutorAction(
                        type="write",
                        text=lesson_data.speech,
                        style="normal",
                        speed=45
                    )
                )
        if not lesson_data:
            raise HTTPException(
                status_code=500,
                detail="Tutor returned no structured lesson"
            )

        total_tokens = 0
        input_tokens = 0
        output_tokens = 0

        if completion.usage:
            total_tokens = (
                    completion.usage.total_tokens or 0
            )

            input_tokens = (
                    completion.usage.prompt_tokens or 0
            )

            output_tokens = (
                    completion.usage.completion_tokens or 0
            )

        openai_cost_usd = (
                (input_tokens / 1_000_000)
                * OPENAI_INPUT_COST_PER_1M
                +
                (output_tokens / 1_000_000)
                * OPENAI_OUTPUT_COST_PER_1M
        )

        # שומרים את הודעת הילד ותשובת ה-AI יחד
        # בקריאת Supabase אחת
        # =================================================
        # יצירת טקסט נקי של תשובת המורה לשמירה בהיסטוריה
        # =================================================

        assistant_history_parts = []

        # מוסיפים את speech הראשי
        if lesson_data.speech:
            assistant_history_parts.append(
                lesson_data.speech.strip()
            )

        # מוסיפים את הטקסטים הרלוונטיים מה-sequence
        for action in lesson_data.sequence or []:

            if (
                    action.type in ("write", "ask")
                    and action.text
                    and action.text.strip()
            ):

                clean_text = action.text.strip()

                # מונע שמירת אותו טקסט פעמיים
                if clean_text not in assistant_history_parts:
                    assistant_history_parts.append(
                        clean_text
                    )

        assistant_history_text = "\n".join(
            assistant_history_parts
        )

        # שומרים את הודעת הילד ואת תשובת המורה הנקייה
        save_tutor_chat_messages(
            user_id=user.id,
            kid_id=child["id"],
            user_content=message,
            assistant_content=assistant_history_text,
            assistant_tokens=total_tokens,
            session_id=session_id
        )

        update_tutor_session_after_chat(
            session=tutor_session,
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=openai_cost_usd
        )

        increment_usage_summary(
            user_id=user.id,

            # מוסיפים Session רק אם באמת נפתח חדש
            sessions=(
                1
                if tutor_session.get("_is_new")
                else 0
            ),

            # קריאת AI אחת
            ai_calls=1,

            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,

            openai_cost_usd=openai_cost_usd
        )

        response_data = lesson_data.model_dump()

        response_data["session_id"] = session_id

        return response_data

    except HTTPException:
        raise

    except Exception as e:
        print("TUTOR CHAT ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail="Tutor chat failed"
        )
