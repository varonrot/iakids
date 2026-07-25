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
UNIVERSAL_UNIT_LESSON_PROMPT_PATH = Path(
    "prompts/iakids_universal_unit_lesson_prompt.txt"
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
GEMINI_TTS_AUDIO_OUTPUT_COST_PER_1M = 20.00
GEMINI_AUDIO_TOKENS_PER_SECOND = 32
# =====================================================
# STRUCTURED LESSON PEDAGOGICAL ENGINE
# =====================================================

# =====================================================
# STRUCTURED LESSON PEDAGOGICAL ENGINE
# =====================================================

# יעד נחשב נשלט כאשר הילד מגיע לפחות לציון הזה
OBJECTIVE_MASTERY_THRESHOLD = 90

# =====================================================
# DIFFICULTY LEVEL CAPS
#
# ילד לא יכול להגיע לשליטה מלאה
# רק מחזרה על משימות קלות.
#
# רמה 1 = היכרות / זיהוי
# רמה 2 = הבנה בסיסית
# רמה 3 = יישום
# רמה 4 = יישום עצמאי
# רמה 5 = העברה / מצב חדש / אתגר מסכם
# =====================================================

DIFFICULTY_SCORE_CAPS = {

    1: 30,

    2: 50,

    3: 70,

    4: 90,

    5: 100

}

# =====================================================
# BASE EVIDENCE POINTS
#
# אלו נקודות "הוכחת שליטה".
# הן עדיין כפופות לתקרת רמת הקושי.
# =====================================================

RESPONSE_QUALITY_POINTS = {

    "correct":
        8,

    "partial":
        3,

    "incorrect":
        0

}

INDEPENDENCE_POINTS = {

    "independent":
        4,

    "with_hint":
        2,

    "guided":
        0

}

UNDERSTANDING_POINTS = {

    "strong":
        4,

    "partial":
        2,

    "weak":
        0

}

EVIDENCE_STRENGTH_POINTS = {

    "strong":
        4,

    "moderate":
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
if not UNIVERSAL_UNIT_LESSON_PROMPT_PATH.exists():
    raise RuntimeError(
        f"Missing universal unit lesson prompt file: "
        f"{UNIVERSAL_UNIT_LESSON_PROMPT_PATH}"
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
UNIVERSAL_UNIT_LESSON_PROMPT_TEMPLATE = (
    UNIVERSAL_UNIT_LESSON_PROMPT_PATH
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

class LessonIntroRequest(BaseModel):
    kid_id: str
    unit_lesson_id: int

class UnitLessonRequest(BaseModel):
    kid_id: str
    unit_lesson_id: int

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
    # היעד הלימודי שנבדק בתור הזה
    objective_index: int | None = None

    # correct / partial / incorrect
    response_quality: str | None = None

    # independent / with_hint / guided
    independence_level: str | None = None

    # strong / partial / weak
    understanding_level: str | None = None

    # 1-5
    #
    # 1 = היכרות / זיהוי
    # 2 = הבנה בסיסית
    # 3 = יישום
    # 4 = יישום עצמאי
    # 5 = העברה למצב חדש / אתגר
    difficulty_level: int | None = None

    # strong / moderate / weak
    #
    # עד כמה האינטראקציה הזאת באמת
    # מספקת הוכחה לשליטה
    evidence_strength: str | None = None

    # האם מדובר בחזרה על אותו סוג
    # משימה שכבר נבדק מספר פעמים
    is_repetition: bool = False

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

def get_gender_placeholders(
        child: dict
) -> dict:

    gender = str(
        child.get("gender")
        or "male"
    ).strip().lower()

    if gender == "female":
        return {
            "{you}": "את",
            "{ready}": "מוכנה",
            "{try}": "נסי",
            "{think}": "חושבת",
            "{know}": "יודעת",
            "{succeed}": "מצליחה"
        }

    return {
        "{you}": "אתה",
        "{ready}": "מוכן",
        "{try}": "נסה",
        "{think}": "חושב",
        "{know}": "יודע",
        "{succeed}": "מצליח"
    }

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

def get_lesson_units_and_lessons(
        learning_lesson_id: int
):
    res = (
        sb.table(
            "lesson_units_content"
        )
        .select(
            "id, "
            "learning_lesson_id, "
            "unit_order, "
            "unit_name, "
            "lesson_order, "
            "lesson_name, "
            "status, "
            "is_active"
        )
        .eq(
            "learning_lesson_id",
            learning_lesson_id
        )
        .eq(
            "is_active",
            True
        )
        .order(
            "unit_order"
        )
        .order(
            "lesson_order"
        )
        .execute()
    )

    rows = res.data or []

    units_map = {}

    for row in rows:
        unit_order = int(
            row.get("unit_order") or 0
        )

        if unit_order not in units_map:
            units_map[unit_order] = {
                "unit_order": unit_order,
                "unit_name": row.get("unit_name"),
                "lessons": []
            }

        units_map[unit_order]["lessons"].append({
            "id": row.get("id"),
            "lesson_order": row.get("lesson_order"),
            "lesson_name": row.get("lesson_name"),
            "status": row.get("status")
        })

    return list(
        units_map.values()
    )

def get_unit_lesson(
        unit_lesson_id: int
):
    res = (
        sb.table(
            "lesson_units_content"
        )
        .select(
            "id, "
            "learning_lesson_id, "
            "unit_order, "
            "unit_name, "
            "lesson_order, "
            "lesson_name, "
            "intro_template_id, "
            "estimated_duration_seconds, "
            "generation_status, "
            "content_version, "
            "generated_lesson_json, "
            "generation_error, "
            "generated_at, "
            "tts_generated_at, "
            "status, "
            "is_active"
        )
        .eq(
            "id",
            unit_lesson_id
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
            detail="Unit lesson not found"
        )

    return res.data[0]

def get_intro_template(
        template_id: int
):
    res = (
        sb.table(
            "lesson_intro_templates"
        )
        .select(
            "id, "
            "template_name, "
            "lesson_type, "
            "tts_provider, "
            "tts_model, "
            "tts_voice, "
            "intro_json"
        )
        .eq(
            "id",
            template_id
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
            detail="Intro template not found"
        )

    return res.data[0]

def replace_intro_variables(
        value,
        replacements: dict
):
    if isinstance(value, str):

        result = value

        for placeholder, replacement in replacements.items():
            result = result.replace(
                placeholder,
                str(replacement or "")
            )

        return result

    if isinstance(value, list):
        return [
            replace_intro_variables(
                item,
                replacements
            )
            for item in value
        ]

    if isinstance(value, dict):
        return {
            key: replace_intro_variables(
                item,
                replacements
            )
            for key, item in value.items()
        }

    return value



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
                0,

            # רמת הקושי הגבוהה ביותר
            # שבה הילד הראה הצלחה
            "highest_difficulty_reached":
                0,

            # מספר אינטראקציות שהיוו
            # הוכחה אמיתית ללמידה
            "evidence_count":
                0,

            # כמה פעמים נצפתה הצלחה
            # בכל רמת קושי
            "evidence_by_level": {

                "1": 0,

                "2": 0,

                "3": 0,

                "4": 0,

                "5": 0

            }

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


def should_show_answering_hint(
        kid_id: str,
        max_lessons: int = 3
):
    res = (
        sb.table(
            "kid_lesson_progress"
        )
        .select(
            "lesson_id"
        )
        .eq(
            "kid_id",
            kid_id
        )
        .limit(
            max_lessons + 1
        )
        .execute()
    )

    lessons_started = len(
        res.data or []
    )

    return (
            lessons_started <= max_lessons
    )


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


# =====================================================
# CALCULATE PEDAGOGICAL EVIDENCE
# =====================================================

def calculate_objective_evidence(
        evaluation: dict
):
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

    evidence_strength = (
        evaluation.get(
            "evidence_strength"
        )
    )

    difficulty_level = int(

        evaluation.get(
            "difficulty_level"
        )

        or 1

    )

    # מגבילים תמיד לטווח 1-5

    difficulty_level = max(

        1,

        min(
            difficulty_level,
            5
        )

    )

    evidence_points = 0

    evidence_points += (

        RESPONSE_QUALITY_POINTS
        .get(
            response_quality,
            0
        )

    )

    evidence_points += (

        INDEPENDENCE_POINTS
        .get(
            independence_level,
            0
        )

    )

    evidence_points += (

        UNDERSTANDING_POINTS
        .get(
            understanding_level,
            0
        )

    )

    evidence_points += (

        EVIDENCE_STRENGTH_POINTS
        .get(
            evidence_strength,
            0
        )

    )

    # =================================================
    # חזרה על אותו סוג משימה
    #
    # עדיין נותנת מעט חיזוק,
    # אבל לא ניקוד מלא שוב ושוב
    # =================================================

    if evaluation.get(
            "is_repetition"
    ):
        evidence_points = round(

            evidence_points
            * 0.35

        )

    # =================================================
    # טעות חוזרת
    # =================================================

    if evaluation.get(
            "repeated_mistake"
    ):
        evidence_points -= 3

    # =================================================
    # תשובה שגויה לא יכולה
    # לייצר evidence חיובי
    # =================================================

    if response_quality == "incorrect":
        evidence_points = min(

            evidence_points,

            0

        )

    return {

        "evidence_points":
            evidence_points,

        "difficulty_level":
            difficulty_level,

        "difficulty_cap":

            DIFFICULTY_SCORE_CAPS[
                difficulty_level
            ]

    }


# =====================================================
# APPLY LESSON EVALUATION
# =====================================================

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

    evidence_result = (

        calculate_objective_evidence(
            evaluation
        )

    )

    evidence_points = (

        evidence_result[
            "evidence_points"
        ]

    )

    difficulty_level = (

        evidence_result[
            "difficulty_level"
        ]

    )

    difficulty_cap = (

        evidence_result[
            "difficulty_cap"
        ]

    )

    # =================================================
    # UPDATE CURRENT OBJECTIVE
    # =================================================

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

                !=

                int(
                    objective_index
                )

        ):
            continue

        old_score = int(

            objective.get(
                "score"
            )

            or 0

        )

        highest_difficulty_reached = int(

            objective.get(
                "highest_difficulty_reached"
            )

            or 0

        )

        evidence_count = int(

            objective.get(
                "evidence_count"
            )

            or 0

        )

        evidence_by_level = (

                objective.get(
                    "evidence_by_level"
                )

                or {

                    "1": 0,

                    "2": 0,

                    "3": 0,

                    "4": 0,

                    "5": 0

                }

        )

        # =============================================
        # עדכון מספר ראיות ברמת הקושי
        # =============================================

        level_key = str(
            difficulty_level
        )

        if (

                evaluation.get(
                    "response_quality"
                )

                in (
                "correct",
                "partial"
        )

        ):
            evidence_by_level[
                level_key
            ] = (

                    int(
                        evidence_by_level.get(
                            level_key,
                            0
                        )
                    )

                    + 1

            )

        # =============================================
        # רק הצלחה אמיתית נחשבת
        # כהגעה לרמת קושי
        # =============================================

        if (

                evaluation.get(
                    "response_quality"
                )

                == "correct"

        ):
            highest_difficulty_reached = max(

                highest_difficulty_reached,

                difficulty_level

            )

        # =============================================
        # SCORE UPDATE
        #
        # קודם מחשבים שינוי רגיל
        # =============================================

        proposed_score = (

                old_score
                + evidence_points

        )

        # =============================================
        # CAP
        #
        # לא מאפשרים לעבור את התקרה
        # של רמת הקושי הגבוהה ביותר
        # שהילד באמת הצליח בה.
        # =============================================

        highest_cap = (

            DIFFICULTY_SCORE_CAPS.get(

                highest_difficulty_reached,

                0

            )

        )

        # אם עדיין אין הצלחה מלאה,
        # משתמשים לפחות בתקרת השאלה
        # הנוכחית אבל לא מאפשרים
        # לפרוץ אותה

        effective_cap = max(

            highest_cap,

            difficulty_cap
            if (
                    evaluation.get(
                        "response_quality"
                    )
                    == "correct"
            )
            else old_score

        )

        new_score = max(

            0,

            min(

                100,

                proposed_score,

                effective_cap

            )

        )

        # =============================================
        # ראיה חדשה
        # =============================================

        if (

                evidence_points > 0

                and

                not evaluation.get(
                    "is_repetition"
                )

        ):
            evidence_count += 1

        objective[
            "score"
        ] = new_score

        objective[
            "highest_difficulty_reached"
        ] = highest_difficulty_reached

        objective[
            "evidence_count"
        ] = evidence_count

        objective[
            "evidence_by_level"
        ] = evidence_by_level

        break

    # =================================================
    # ALL OBJECTIVE SCORES
    # =================================================

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

    # =================================================
    # LESSON PROGRESS
    #
    # ממוצע ציוני כל היעדים
    # =================================================

    if scores:

        progress_percent = round(

            sum(scores)
            /
            len(scores)

        )

    else:

        progress_percent = 0

    # =================================================
    # MASTERY
    #
    # ממוצע של יעדים שכבר התחילו
    # =================================================

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

    # =================================================
    # NEXT OBJECTIVE
    # =================================================

    next_objective_index = None

    for objective in (
            objectives_progress
    ):

        objective_score = int(

            objective.get(
                "score"
            )

            or 0

        )

        highest_difficulty = int(

            objective.get(
                "highest_difficulty_reached"
            )

            or 0

        )

        if (

                objective_score
                < OBJECTIVE_MASTERY_THRESHOLD

                or

                highest_difficulty
                < 5

        ):
            next_objective_index = (

                objective[
                    "objective_index"
                ]

            )

            break

    # =================================================
    # LESSON COMPLETION
    # =================================================

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

                and

                int(
                    objective.get(
                        "highest_difficulty_reached"
                    )

                    or 0
                )

                >= 5

                for objective
                in objectives_progress

            )

    )

    if lesson_completed:

        status = "completed"

        progress_percent = 100

        next_objective_index = None


    else:

        status = "in_progress"

    # =================================================
    # SUCCESS / FAILURE STREAKS
    # =================================================

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

    # =================================================
    # HINTS
    # =================================================

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

    # =================================================
    # DATABASE UPDATE
    # =================================================

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

    # =================================================
    # COMPLETED
    # =================================================

    if lesson_completed:
        update_data[
            "completed_at"
        ] = now.isoformat()

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
        turn_type: str,
        review_mode: bool = False,
        show_answering_hint: bool = False
):
    runtime_context = {

        "lesson_mode":
            (
                "review"
                if review_mode
                else "learning"
            ),

        "review_mode":
            review_mode,

        "turn_type":
            turn_type,

        "show_answering_hint":
            show_answering_hint,

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

def build_universal_unit_lesson_prompt(
        unit_lesson: dict,
        parent_lesson: dict
) -> str:

    prompt = (
        UNIVERSAL_UNIT_LESSON_PROMPT_TEMPLATE
    )

    replacements = {

        "{grade}":
            str(
                parent_lesson.get(
                    "grade"
                )
                or ""
            ),

        "{subject}":
            str(
                parent_lesson.get(
                    "subject"
                )
                or ""
            ),

        "{parent_lesson}":
            str(
                parent_lesson.get(
                    "lesson_name"
                )
                or ""
            ),

        "{unit_name}":
            str(
                unit_lesson.get(
                    "unit_name"
                )
                or ""
            ),

        "{lesson_name}":
            str(
                unit_lesson.get(
                    "lesson_name"
                )
                or ""
            ),

        "{estimated_duration_seconds}":
            str(
                unit_lesson.get(
                    "estimated_duration_seconds"
                )
                or 60
            )

    }

    for placeholder, value in replacements.items():

        prompt = prompt.replace(
            placeholder,
            value
        )

    return prompt

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

                temperature=2.0,

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

        error_message = repr(e)

        print(
            "GEMINI TTS ERROR:",
            error_message
        )

        raise HTTPException(
            status_code=500,
            detail=f"Gemini TTS failed: {error_message}"
        )

@app.get(
    "/api/learning-lessons/{learning_lesson_id}/units"
)
def get_learning_lesson_units(
        learning_lesson_id: int,
        authorization: str = Header(None)
):
    try:
        authenticate_user(
            authorization
        )

        # מוודאים שהרשומה הראשית קיימת
        parent_lesson = get_learning_lesson(
            learning_lesson_id
        )

        units = get_lesson_units_and_lessons(
            learning_lesson_id
        )

        return {
            "learning_lesson_id":
                parent_lesson["id"],

            "subject":
                parent_lesson.get("subject"),

            "category":
                parent_lesson.get("category"),

            "parent_lesson_name":
                parent_lesson.get("lesson_name"),

            "units":
                units
        }

    except HTTPException:
        raise

    except Exception as e:
        print(
            "GET LESSON UNITS ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to load lesson units"
        )

@app.post(
    "/api/tutor/lesson-intro"
)
def lesson_intro(
        body: LessonIntroRequest,
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
        # SELECTED UNIT LESSON
        # =============================================

        unit_lesson = get_unit_lesson(
            body.unit_lesson_id
        )

        # =============================================
        # PARENT LESSON
        # =============================================

        parent_lesson = get_learning_lesson(
            unit_lesson[
                "learning_lesson_id"
            ]
        )

        # =============================================
        # INTRO TEMPLATE
        # =============================================

        intro_template_id = (
            unit_lesson.get(
                "intro_template_id"
            )
        )

        if not intro_template_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No intro template assigned "
                    "to this lesson"
                )
            )

        intro_template = get_intro_template(
            intro_template_id
        )

        intro_json = (
            intro_template.get(
                "intro_json"
            )
            or {}
        )

        # =============================================
        # REPLACE VARIABLES
        # =============================================

        replacements = {
            "{child_name}":
                child.get(
                    "child_name"
                )
                or "",

            "{parent_lesson}":
                parent_lesson.get(
                    "lesson_name"
                )
                or "",

            "{unit_name}":
                unit_lesson.get(
                    "unit_name"
                )
                or "",

            "{lesson_name}":
                unit_lesson.get(
                    "lesson_name"
                )
                or "",

            "{subject}":
                parent_lesson.get(
                    "subject"
                )
                or "",

            "{grade}":
                child.get(
                    "age"
                )
                or ""
        }

        replacements.update(
            get_gender_placeholders(
                child
            )
        )

        rendered_intro = (
            replace_intro_variables(
                intro_json,
                replacements
            )
        )

        raw_steps = (
            rendered_intro.get(
                "steps"
            )
            or []
        )

        sequence = []

        for step in raw_steps:

            sequence.append(
                TutorAction(
                    type=step.get(
                        "type",
                        "write"
                    ),

                    text=step.get(
                        "text"
                    ),

                    target=step.get(
                        "target"
                    ),

                    style=step.get(
                        "style"
                    ),

                    speed=step.get(
                        "speed"
                    ),

                    duration=(
                        step.get(
                            "duration"
                        )
                        or step.get(
                            "duration_ms"
                        )
                    ),

                    speech_tts=step.get(
                        "speech_tts"
                    )
                )
            )

        return {
            "success": True,

            "unit_lesson_id":
                unit_lesson["id"],

            "learning_lesson_id":
                parent_lesson["id"],

            "intro_template_id":
                intro_template["id"],

            "intro_template_name":
                intro_template.get(
                    "template_name"
                ),

            "tts": {
                "provider":
                    intro_template.get(
                        "tts_provider"
                    ),

                "model":
                    intro_template.get(
                        "tts_model"
                    ),

                "voice":
                    intro_template.get(
                        "tts_voice"
                    )
            },

            "sequence": [
                action.model_dump()
                for action in sequence
            ],

            "wait_for_answer": False
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "LESSON INTRO ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Lesson intro failed"
        )

@app.post(
    "/api/tutor/unit-lesson"
)
def get_or_generate_unit_lesson(
        body: UnitLessonRequest,
        authorization: str = Header(None)
):
    unit_lesson = None

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

        # מוודאים שהילד שייך למשתמש
        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )

        # =============================================
        # UNIT LESSON
        # =============================================

        unit_lesson = get_unit_lesson(
            body.unit_lesson_id
        )

        parent_lesson = get_learning_lesson(
            unit_lesson[
                "learning_lesson_id"
            ]
        )

        # =============================================
        # GRADE SECURITY
        # =============================================

        child_grade = int(
            child.get(
                "age"
            )
            or 0
        )

        lesson_grade = int(
            parent_lesson.get(
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

        generation_status = (
            unit_lesson.get(
                "generation_status"
            )
            or "empty"
        )

        cached_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
        )

        # =============================================
        # CACHE HIT
        # =============================================

        if (
                generation_status == "ready"
                and isinstance(
                    cached_json,
                    dict
                )
                and cached_json.get(
                    "sequence"
                )
        ):
            return {
                "success": True,

                "source": "cache",

                "unit_lesson_id":
                    unit_lesson["id"],

                "learning_lesson_id":
                    parent_lesson["id"],

                "generation_status":
                    "ready",

                "content_version":
                    unit_lesson.get(
                        "content_version"
                    )
                    or 1,

                "speech":
                    cached_json.get(
                        "speech"
                    ),

                "sequence":
                    cached_json.get(
                        "sequence"
                    )
                    or [],

                "wait_for_answer":
                    bool(
                        cached_json.get(
                            "wait_for_answer",
                            True
                        )
                    )
            }

        # =============================================
        # ALREADY GENERATING
        # =============================================

        if generation_status == "generating":
            return {
                "success": False,

                "source": "generating",

                "unit_lesson_id":
                    unit_lesson["id"],

                "learning_lesson_id":
                    parent_lesson["id"],

                "generation_status":
                    "generating",

                "sequence": [],

                "wait_for_answer": False
            }

        # =============================================
        # MARK AS GENERATING
        # =============================================

        now = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        sb.table(
            "lesson_units_content"
        ).update({

            "generation_status":
                "generating",

            "generation_error":
                None,

            "updated_at":
                now

        }).eq(
            "id",
            unit_lesson["id"]
        ).execute()

        # =============================================
        # BUILD UNIVERSAL PROMPT
        # =============================================

        system_prompt = (
            build_universal_unit_lesson_prompt(
                unit_lesson=
                    unit_lesson,

                parent_lesson=
                    parent_lesson
            )
        )

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

                    {
                        "role":
                            "user",

                        "content":
                            (
                                "צרו עכשיו את השיעור "
                                "המובנה והאוניברסלי. "
                                "החזירו את רצף הפעולות בלבד "
                                "לפי מבנה התגובה."
                            )
                    }

                ],

                response_format=
                    TutorLessonResponse

            )
        )

        lesson_data = (
            completion
            .choices[0]
            .message
            .parsed
        )

        if not lesson_data:
            raise RuntimeError(
                "Universal unit lesson "
                "returned no response"
            )

        sequence = (
            lesson_data.sequence
            or []
        )

        # =============================================
        # VALIDATION
        # =============================================

        has_write = any(
            action.type == "write"
            and bool(
                (
                    action.text
                    or ""
                ).strip()
            )
            for action in sequence
        )

        final_action = (
            sequence[-1]
            if sequence
            else None
        )

        has_final_ask = (
            final_action is not None
            and final_action.type == "ask"
            and bool(
                (
                    final_action.text
                    or ""
                ).strip()
            )
        )

        if not has_write:
            raise RuntimeError(
                "Generated lesson has no write action"
            )

        if not has_final_ask:
            sequence.append(

                TutorAction(

                    type="ask",

                    text="אפשר להסביר במילים שלכם מה למדתם עכשיו?"

                )

            )

            # =============================================
            # GUARANTEE AUDIO FOR THE LESSON
            #
            # אם המודל החזיר כתיבה ללא speak,
            # מוסיפים הקראה אחרי כל קטע כתוב.
            # כך כל ההסבר יישמע ולא רק שאלת הסיום.
            # =============================================

            has_explanation_speak = any(

                action.type == "speak"

                and bool(
                    (
                            action.text
                            or action.speech_tts
                            or ""
                    ).strip()
                )

                for action in sequence

            )

            if not has_explanation_speak:

                sequence_with_audio = []

                for action in sequence:

                    sequence_with_audio.append(
                        action
                    )

                    # מוסיפים הקראה רק אחרי פעולת כתיבה
                    # שיש בה טקסט אמיתי
                    if (
                            action.type == "write"

                            and bool(
                        (
                                action.text
                                or ""
                        ).strip()
                    )
                    ):
                        sequence_with_audio.append(

                            TutorAction(
                                type="speak",
                                text=action.text
                            )

                        )

                sequence = sequence_with_audio
                
            lesson_data.sequence = sequence
            lesson_data.wait_for_answer = True

        # ה-Backend קובע זאת בעצמו
        lesson_data.wait_for_answer = True

        lesson_json = {
            "speech":
                lesson_data.speech,

            "sequence": [
                action.model_dump()
                for action in sequence
            ],

            "wait_for_answer":
                True
        }

        # =============================================
        # SAVE CACHE
        # =============================================

        content_version = int(
            unit_lesson.get(
                "content_version"
            )
            or 1
        )

        generated_at = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        sb.table(
            "lesson_units_content"
        ).update({

            "generated_lesson_json":
                lesson_json,

            "generation_status":
                "ready",

            "generation_error":
                None,

            "content_version":
                content_version,

            "generated_at":
                generated_at,

            "updated_at":
                generated_at

        }).eq(
            "id",
            unit_lesson["id"]
        ).execute()

        # =============================================
        # USAGE
        # =============================================

        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        if completion.usage:

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

            total_tokens = (
                completion
                .usage
                .total_tokens
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

        increment_usage_summary(

            user_id=
                user.id,

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
        # RESPONSE
        # =============================================

        return {
            "success": True,

            "source": "generated",

            "unit_lesson_id":
                unit_lesson["id"],

            "learning_lesson_id":
                parent_lesson["id"],

            "generation_status":
                "ready",

            "content_version":
                content_version,

            "speech":
                lesson_json.get(
                    "speech"
                ),

            "sequence":
                lesson_json.get(
                    "sequence"
                )
                or [],

            "wait_for_answer":
                True
        }

    except HTTPException:
        raise

    except Exception as e:

        error_message = repr(e)

        print(
            "UNIT LESSON GENERATION ERROR:",
            error_message
        )

        # =============================================
        # MARK AS FAILED
        # =============================================

        if unit_lesson:

            try:

                sb.table(
                    "lesson_units_content"
                ).update({

                    "generation_status":
                        "failed",

                    "generation_error":
                        str(e)[:1500],

                    "updated_at":
                        datetime
                        .now(timezone.utc)
                        .isoformat()

                }).eq(
                    "id",
                    unit_lesson["id"]
                ).execute()

            except Exception as update_error:

                print(
                    "UNIT LESSON FAILURE UPDATE ERROR:",
                    repr(update_error)
                )

        raise HTTPException(
            status_code=500,
            detail="Unit lesson generation failed"
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

        # =============================================
        # SPECIAL LESSON EVENTS
        #
        # __NO_RESPONSE__ נשלח מה-Frontend
        # כאשר הילד לא ענה במשך זמן מסוים.
        #
        # זה אינו נחשב תשובת תלמיד ולכן:
        # - לא מבצעים Evaluation
        # - לא מעדכנים Progress
        # - לא שומרים אותו כתשובת ילד
        # =============================================

        is_no_response = (

                message
                == "__NO_RESPONSE__"

        )

        is_lesson_start = (

            not bool(
                message
            )

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
        # LESSON MODE
        #
        # אם השיעור כבר הושלם,
        # כניסה חוזרת אליו היא Review Mode.
        #
        # במצב Review:
        # - לא מאפסים התקדמות
        # - לא משנים ציוני יעדים
        # - לא נותנים שוב XP / Stars
        # =============================================

        review_mode = (

                progress.get(
                    "status"
                )

                == "completed"

        )

        # =============================================
        # TURN TYPE
        # =============================================

        if review_mode:

            if is_lesson_start:

                turn_type = (
                    "review_start"
                )

            elif is_no_response:

                turn_type = (
                    "review_no_response"
                )

            else:

                turn_type = (
                    "review_response"
                )


        else:

            if is_lesson_start:

                turn_type = (
                    "start"
                )

            elif is_no_response:

                turn_type = (
                    "no_response"
                )

            else:

                turn_type = (
                    "student_response"
                )

        # =============================================
        # PROMPT
        # =============================================

        show_answering_hint = False

        if (
                is_lesson_start
                and
                not review_mode
                and
                child_grade in (1, 2)
        ):
            show_answering_hint = (
                should_show_answering_hint(
                    kid_id=child["id"],
                    max_lessons=3
                )
            )

        system_prompt = (

            build_structured_lesson_prompt(

                child=child,

                lesson=lesson,

                progress=progress,

                turn_type=turn_type,

                review_mode=review_mode,

                show_answering_hint=
                show_answering_hint

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

            if review_mode:

                current_message = (

                    "התחל חזרה על שיעור שכבר הושלם. "
                    "אל תלמד את השיעור מחדש מההתחלה. "
                    "בצע חזרה קצרה ובדיקת שימור ידע "
                    "על יעדי הלמידה, תוך העדפה למשימות "
                    "ברמות בינוניות עד גבוהות. "
                    "זהו תור פתיחת Review ולכן "
                    "אין להעריך עדיין תשובת תלמיד."

                )

            else:

                current_message = (

                    "התחל את השיעור המובנה. "
                    "זהו תור פתיחת שיעור ולכן "
                    "אין להעריך עדיין תשובת תלמיד."

                )


        elif is_no_response:

            current_message = (

                "התלמיד עדיין לא ענה לשאלה האחרונה. "
                "אל תתייחס לכך כתשובת תלמיד ואל תבצע הערכה. "
                "דובב את הילד בצורה קצרה, חמה וטבעית. "
                "אפשר לעודד אותו לחשוב, להציע רמז קטן "
                "או לנסח את השאלה בצורה פשוטה יותר. "
                "אל תיתן מיד את התשובה. "
                "המשך להמתין לתשובת הילד."

            )


        else:

            current_message = (
                message
            )

        # =============================================
        # ADD CURRENT TURN TO LLM MESSAGES
        #
        # מתבצע תמיד:
        # - פתיחת שיעור רגיל
        # - פתיחת Review
        # - תשובת תלמיד
        # =============================================

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
        # VALIDATE LESSON START SEQUENCE
        #
        # בפתיחת שיעור רגילה:
        # - חייב להיות לפחות write אחד
        # - חייב להיות ask בסוף
        #
        # אם GPT החזיר פתיח חלקי,
        # מבצעים Retry אחד עם הוראה מפורשת.
        # =============================================

        if is_lesson_start and not review_mode:

            sequence = (
                    lesson_data.sequence
                    or []
            )

            has_write = any(
                action.type == "write"
                for action in sequence
            )

            has_ask = any(
                action.type == "ask"
                and bool(
                    (
                            action.text
                            or ""
                    ).strip()
                )
                for action in sequence
            )

            final_action_is_ask = (
                    bool(sequence)
                    and sequence[-1].type == "ask"
                    and bool(
                (
                        sequence[-1].text
                        or ""
                ).strip()
            )
            )

            if (
                    not has_write
                    or
                    not has_ask
                    or
                    not final_action_is_ask
            ):

                retry_message = (

                        current_message

                        +

                        "\n\n"
                        "IMPORTANT RETRY: "
                        "The previous lesson-start response was incomplete. "
                        "Return a COMPLETE lesson-start sequence. "
                        "Do not return only speak actions. "
                        "The sequence must include actual teaching, "
                        "at least one write action, "
                        "and must end with one real ask action "
                        "that requires the child's response. "
                        "Begin teaching the current objective now, "
                        "not only introducing the lesson."
                )

                retry_messages = [

                    {
                        "role":
                            "system",

                        "content":
                            system_prompt

                    },

                    *recent_messages[:-1],

                    {
                        "role":
                            "user",

                        "content":
                            retry_message

                    }

                ]

                retry_completion = (

                    client
                    .beta
                    .chat
                    .completions
                    .parse(

                        model=
                        "gpt-4o-mini",

                        messages=
                        retry_messages,

                        response_format=
                        StructuredLessonResponse

                    )

                )

                retry_lesson_data = (

                    retry_completion
                    .choices[0]
                    .message
                    .parsed

                )

                if retry_lesson_data:
                    lesson_data = (
                        retry_lesson_data
                    )

                    completion = (
                        retry_completion
                    )

        # =============================================
        # NORMALIZE WAIT FOR ANSWER
        #
        # מחכים לילד אך ורק כאשר הפעולה האחרונה
        # ב-sequence היא ASK אמיתית עם טקסט.
        #
        # אם המודל כתב wait_for_answer=true
        # אבל לא שאל שאלה בפועל,
        # ה-Backend מתקן זאת אוטומטית.
        # =============================================

        sequence = (

                lesson_data.sequence
                or []

        )

        # =============================================
        # GUARANTEE LESSON OPENING GREETING
        # =============================================

        if is_lesson_start and not review_mode:
            child_name = (
                    child.get("child_name")
                    or ""
            ).strip()

            subject = (
                    lesson.get("subject")
                    or ""
            ).strip()

            greeting_text = (
                f"שלום {child_name}! "
                f"כיף שבחרת ללמוד איתי היום {subject}."
            )

            # מוסיפים פתיח קולי קבוע בתחילת השיעור
            sequence.insert(
                0,
                TutorAction(
                    type="speak",
                    text=greeting_text
                )
            )

            lesson_data.sequence = sequence

        last_action = (

            sequence[-1]

            if sequence

            else None

        )

        has_real_final_ask = (

                last_action is not None

                and

                last_action.type == "ask"

                and

                bool(

                    (
                            last_action.text
                            or ""
                    ).strip()

                )

        )

        lesson_data.wait_for_answer = (

            has_real_final_ask

        )

        # =============================================
        # EVALUATION
        #
        # רק אחרי תשובה אמיתית של הילד
        # =============================================

        evaluation_dict = None

        evaluated_objective_index = (
            progress.get(
                "current_objective_index"
            )
        )

        if (

                not is_lesson_start

                and

                not is_no_response

                and

                lesson_data.evaluation

        ):

            evaluation_dict = (

                lesson_data
                .evaluation
                .model_dump()

            )

            evaluated_objective_index = (

                    evaluation_dict.get(
                        "objective_index"
                    )

                    or progress.get(
                "current_objective_index"
            )

            )

            # =========================================
            # NORMAL LEARNING MODE
            #
            # רק במהלך לימוד רגיל
            # ההערכה משנה את ההתקדמות הרשמית.
            # =========================================

            if not review_mode:
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
            evaluated_objective_index,

            user_content=(

                None

                if (
                        is_lesson_start
                        or
                        is_no_response
                )

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

        response_data[
            "review_mode"
        ] = review_mode

        response_data[
            "lesson_mode"
        ] = (

            "review"

            if review_mode

            else "learning"

        )

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
