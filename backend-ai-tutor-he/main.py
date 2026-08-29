from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Response,
    BackgroundTasks
)
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
import traceback
import time
from concurrent.futures import ThreadPoolExecutor
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
LESSON_DIRECTOR_PROMPT_PATH = Path(
    "prompts/lesson_director_prompt.txt"
)
VISUAL_DIRECTOR_PROMPT_PATH = Path(
    "prompts/iakids_visual_director_prompt.txt"
)
LESSON_TRANSITION_PROMPT_PATH = Path(
    "prompts/iakids_lesson_transition_prompt.txt"
)
LEARNING_COACH_PROMPT_PATH = Path(
    "prompts/learning_coach_system_prompt.txt"
)
CURRICULUM_BUILDER_PROMPT_PATH = Path(
    "prompts/iakids_curriculum_builder_system_prompt.txt"
)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# =====================================================
# OPENAI MODELS
# =====================================================

# מודל זול לפעולות שוטפות:
# צ'אט, המשך שיעור, הערכה וניתוח שיעורי בית
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

# המודל החזק ביותר משמש אך ורק ליצירת
# תוכן שיעור אוניברסלי חדש שנשמר במטמון
UNIVERSAL_LESSON_MODEL = "gpt-5.6-sol"


# =====================================================
# MODEL PRICING - USD PER 1M TOKENS
# =====================================================

MODEL_PRICING_USD = {

    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60
    },

    "gpt-5.6-sol": {
        "input": 5.00,
        "output": 30.00
    }

}

# =====================================================
# GEMINI TTS PRICING
# =====================================================

# כמות משוערת של Audio Tokens לשנייה
GEMINI_AUDIO_TOKENS_PER_SECOND = 25

# מחיר פלט אודיו (USD לכל מיליון Audio Tokens)
GEMINI_TTS_AUDIO_OUTPUT_COST_PER_1M = 10.0


def calculate_openai_cost(
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0
) -> float:

    pricing = MODEL_PRICING_USD.get(
        model
    )

    if not pricing:
        print(
            "WARNING: Missing pricing for model:",
            model
        )
        return 0.0

    input_cost = (
        int(input_tokens or 0)
        / 1_000_000
        * pricing["input"]
    )

    output_cost = (
        int(output_tokens or 0)
        / 1_000_000
        * pricing["output"]
    )

    return input_cost + output_cost

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
if not LESSON_DIRECTOR_PROMPT_PATH.exists():
    raise RuntimeError(
        f"Missing lesson director prompt file: "
        f"{LESSON_DIRECTOR_PROMPT_PATH}"
    )
if not VISUAL_DIRECTOR_PROMPT_PATH.exists():
    raise RuntimeError(
        f"Missing visual director prompt file: "
        f"{VISUAL_DIRECTOR_PROMPT_PATH}"
    )
if not LESSON_TRANSITION_PROMPT_PATH.exists():
    raise RuntimeError(
        f"Missing Lesson Transition prompt file: "
        f"{LESSON_TRANSITION_PROMPT_PATH}"
    )
if not LEARNING_COACH_PROMPT_PATH.exists():
    raise RuntimeError(
        f"Missing Learning Coach prompt file: "
        f"{LEARNING_COACH_PROMPT_PATH}"
    )
if not CURRICULUM_BUILDER_PROMPT_PATH.exists():
    raise RuntimeError(
        f"Missing Curriculum Builder prompt file: "
        f"{CURRICULUM_BUILDER_PROMPT_PATH}"
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
LESSON_DIRECTOR_PROMPT_TEMPLATE = (
    LESSON_DIRECTOR_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
VISUAL_DIRECTOR_PROMPT_TEMPLATE = (
    VISUAL_DIRECTOR_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
LESSON_TRANSITION_PROMPT_TEMPLATE = (
    LESSON_TRANSITION_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
LEARNING_COACH_PROMPT_TEMPLATE = (
    LEARNING_COACH_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
CURRICULUM_BUILDER_PROMPT_TEMPLATE = (
    CURRICULUM_BUILDER_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
print("=== LEARNING COACH PROMPT LOADED ===")
print(LEARNING_COACH_PROMPT_TEMPLATE[:300])
print("====================================")

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

# =====================================================
# SUPABASE TEMPORARY ERROR RETRY
# =====================================================

def supabase_with_retry(
        operation,
        label: str = "SUPABASE",
        max_attempts: int = 3,
        base_delay_seconds: float = 0.5
):

    last_error = None

    for attempt in range(
        1,
        max_attempts + 1
    ):

        try:

            return operation()

        except Exception as e:

            last_error = e

            print(
                f"{label} RETRY:",
                {
                    "attempt":
                        attempt,

                    "max_attempts":
                        max_attempts,

                    "error":
                        repr(e)
                }
            )

            if attempt >= max_attempts:
                raise

            time.sleep(
                base_delay_seconds
                * attempt
            )

    raise last_error

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

class CurriculumLesson(BaseModel):
    name: str


class CurriculumUnit(BaseModel):
    name: str
    lessons: list[CurriculumLesson]


class CurriculumTopic(BaseModel):
    name: str
    units: list[CurriculumUnit]


class CurriculumHierarchy(BaseModel):
    subject: str
    topics: list[CurriculumTopic]


class CurriculumBuilderChatRequest(BaseModel):
    kid_id: str
    message: str

    custom_subject_id: str | None = None

    history: list[dict] | None = None

class CurriculumApproveRequest(BaseModel):
    kid_id: str
    custom_subject_id: str
    curriculum_id: str

class CurriculumBuilderAIResponse(BaseModel):
    reply: str

    subject: str | None = None

    focus_topic: str | None = None

    hierarchy: CurriculumHierarchy | None = None

    ready_to_create: bool = False

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

    # =============================================
    # VISUAL CARD
    # =============================================

    title: str | None = None

    items: list[str] | None = None

    icon: str | None = None


class TutorLessonResponse(BaseModel):
    speech: str | None = None
    sequence: list[TutorAction]
    wait_for_answer: bool = False

class UniversalLessonResponse(BaseModel):
    lesson: str
class DirectedLessonSegment(BaseModel):
    text: str


class DirectedLessonQuestion(BaseModel):
    text: str


class DirectedLessonPart(BaseModel):
    lesson: list[DirectedLessonSegment]
    question: DirectedLessonQuestion


class DirectedLessonSummary(BaseModel):
    text: str


class DirectedLessonResponse(BaseModel):

    part_1: DirectedLessonPart

    part_2: DirectedLessonPart

    summary: DirectedLessonSummary

class VisualDirectorItem(BaseModel):
    order: int
    trigger_text: str
    type: str
    visual_goal: str
    source_text: str
    generation_prompt: str


class VisualDirectorResponse(BaseModel):
    version: int = 1
    visuals: list[VisualDirectorItem]

class LessonTransitionResponse(BaseModel):

    speech: str

    video_scene: str

    next_part_hook: str

    duration_seconds: int = 10

# =====================================================
# STRUCTURED LESSON MODELS
# =====================================================

class LessonIntroRequest(BaseModel):
    kid_id: str
    unit_lesson_id: int

class UnitLessonRequest(BaseModel):
    kid_id: str
    unit_lesson_id: int

class ActiveLessonStateRequest(BaseModel):
    kid_id: str
class ResetUnitLessonRequest(BaseModel):
    kid_id: str
    lesson_id: int
    unit_lesson_id: int
class StructuredLessonRequest(
    BaseModel
):
    kid_id: str

    lesson_id: int

    # תת־השיעור שהילד ראה בפועל
    unit_lesson_id: int | None = None

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
# LEARNING COACH MODELS
# =====================================================

class LearningCoachAIResponse(
    BaseModel
):
    understanding_score: int

    lesson_goal_achieved: bool

    teacher_response: str

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

def get_child_by_id(
        user_id: str,
        kid_id: str
):

    def operation():

        return (
            sb.table(
                "kids_profiles"
            )
            .select("*")
            .eq(
                "id",
                kid_id
            )
            .eq(
                "user_id",
                user_id
            )
            .single()
            .execute()
        )

    res = supabase_with_retry(
        operation,
        label="GET CHILD"
    )

    if not res.data:
        raise HTTPException(
            status_code=404,
            detail="Child not found"
        )

    return res.data

# =====================================================
# CUSTOM CURRICULUM HELPERS
# =====================================================

def get_custom_subject(
        user_id: str,
        kid_id: str,
        custom_subject_id: str
):
    res = (
        sb.table(
            "kid_custom_subjects"
        )
        .select("*")
        .eq(
            "id",
            custom_subject_id
        )
        .eq(
            "user_id",
            user_id
        )
        .eq(
            "kid_id",
            kid_id
        )
        .limit(1)
        .execute()
    )

    if not res.data:
        raise HTTPException(
            status_code=404,
            detail="Custom subject not found"
        )

    return res.data[0]

def create_custom_subject(
        user_id: str,
        kid_id: str,
        subject_name: str
):
    now_iso = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    clean_subject_name = str(
        subject_name or ""
    ).strip()

    if not clean_subject_name:
        raise ValueError(
            "subject_name is required"
        )

    # =============================================
    # CHECK IF SUBJECT ALREADY EXISTS FOR THIS KID
    # =============================================

    existing_res = (
        sb.table(
            "kid_custom_subjects"
        )
        .select("*")
        .eq(
            "user_id",
            user_id
        )
        .eq(
            "kid_id",
            kid_id
        )
        .eq(
            "subject_name",
            clean_subject_name
        )
        .in_(
            "status",
            ["draft", "active"]
        )
        .order(
            "created_at",
            desc=True
        )
        .limit(1)
        .execute()
    )

    if existing_res.data:

        existing_subject = (
            existing_res.data[0]
        )

        print(
            "REUSING CUSTOM SUBJECT:",
            existing_subject["id"],
            clean_subject_name
        )

        return existing_subject

    # =============================================
    # CREATE ONLY IF IT DOES NOT EXIST
    # =============================================

    res = (
        sb.table(
            "kid_custom_subjects"
        )
        .insert({
            "user_id":
                user_id,

            "kid_id":
                kid_id,

            "subject_name":
                clean_subject_name,

            "status":
                "draft",

            "created_by":
                "parent_ai_builder",

            "created_at":
                now_iso,

            "updated_at":
                now_iso
        })
        .execute()
    )

    if not res.data:
        raise RuntimeError(
            "Failed to create custom subject"
        )

    return res.data[0]


def get_current_custom_curriculum(
        custom_subject_id: str
):
    res = (
        sb.table(
            "kid_custom_curriculums"
        )
        .select("*")
        .eq(
            "custom_subject_id",
            custom_subject_id
        )
        .limit(1)
        .execute()
    )

    if not res.data:
        return None

    return res.data[0]


def create_custom_curriculum(
        user_id: str,
        kid_id: str,
        custom_subject_id: str,
        curriculum_json: dict,
        ready_to_create: bool,
        parent_message: str
):
    now_iso = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    curriculum_status = (
        "ready_for_approval"
        if ready_to_create
        else "building"
    )

    # =============================================
    # CURRENT VERSION
    # =============================================

    curriculum_res = (
        sb.table(
            "kid_custom_curriculums"
        )
        .insert({
            "user_id":
                user_id,

            "kid_id":
                kid_id,

            "custom_subject_id":
                custom_subject_id,

            "curriculum_json":
                curriculum_json,

            "version":
                1,

            "status":
                curriculum_status,

            "last_change_type":
                "created",

            "last_change_summary":
                "Initial curriculum created by AI",

            "updated_by":
                "ai",

            "created_at":
                now_iso,

            "updated_at":
                now_iso
        })
        .execute()
    )

    if not curriculum_res.data:
        raise RuntimeError(
            "Failed to create custom curriculum"
        )

    curriculum = (
        curriculum_res.data[0]
    )

    # =============================================
    # VERSION 1 SNAPSHOT
    # =============================================

    sb.table(
        "kid_custom_curriculum_versions"
    ).insert({
        "user_id":
            user_id,

        "kid_id":
            kid_id,

        "custom_subject_id":
            custom_subject_id,

        "curriculum_id":
            curriculum["id"],

        "version":
            1,

        "curriculum_json":
            curriculum_json,

        "change_type":
            "created",

        "change_summary":
            "Initial curriculum created by AI",

        "changed_by":
            "ai",

        "parent_message":
            parent_message,

        "created_at":
            now_iso
    }).execute()

    return curriculum


def update_custom_curriculum(
        user_id: str,
        kid_id: str,
        custom_subject: dict,
        curriculum: dict,
        curriculum_json: dict,
        subject_name: str | None,
        ready_to_create: bool,
        parent_message: str
):
    now_iso = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    current_version = int(
        curriculum.get(
            "version"
        )
        or 1
    )

    new_version = (
        current_version + 1
    )

    curriculum_status = (
        "ready_for_approval"
        if ready_to_create
        else "building"
    )

    # =============================================
    # UPDATE SUBJECT NAME IF AI REFINED IT
    # =============================================

    clean_subject_name = str(
        subject_name or ""
    ).strip()

    if (
            clean_subject_name
            and
            clean_subject_name
            != custom_subject.get(
                "subject_name"
            )
    ):
        sb.table(
            "kid_custom_subjects"
        ).update({
            "subject_name":
                clean_subject_name,

            "updated_at":
                now_iso
        }).eq(
            "id",
            custom_subject["id"]
        ).eq(
            "user_id",
            user_id
        ).execute()

    # =============================================
    # UPDATE CURRENT CURRICULUM
    # =============================================

    updated_res = (
        sb.table(
            "kid_custom_curriculums"
        )
        .update({
            "curriculum_json":
                curriculum_json,

            "version":
                new_version,

            "status":
                curriculum_status,

            "last_change_type":
                "ai_update",

            "last_change_summary":
                "Curriculum updated from parent conversation",

            "updated_by":
                "ai",

            "updated_at":
                now_iso
        })
        .eq(
            "id",
            curriculum["id"]
        )
        .eq(
            "user_id",
            user_id
        )
        .eq(
            "kid_id",
            kid_id
        )
        .execute()
    )

    if not updated_res.data:
        raise RuntimeError(
            "Failed to update custom curriculum"
        )

    updated_curriculum = (
        updated_res.data[0]
    )

    # =============================================
    # SAVE NEW VERSION SNAPSHOT
    # =============================================

    sb.table(
        "kid_custom_curriculum_versions"
    ).insert({
        "user_id":
            user_id,

        "kid_id":
            kid_id,

        "custom_subject_id":
            custom_subject["id"],

        "curriculum_id":
            curriculum["id"],

        "version":
            new_version,

        "curriculum_json":
            curriculum_json,

        "change_type":
            "ai_update",

        "change_summary":
            "Curriculum updated from parent conversation",

        "changed_by":
            "ai",

        "parent_message":
            parent_message,

        "created_at":
            now_iso
    }).execute()

    return updated_curriculum

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
# LEARNING COACH SESSION HELPERS
# =====================================================

LEARNING_COACH_MAX_ROUNDS = 5

# =====================================================
# UNIVERSAL LESSON STAGES
# =====================================================

LESSON_STAGE_INTRO = "lesson_intro"
LESSON_STAGE_FIRST_EXPLANATION = "first_explanation"
LESSON_STAGE_FIRST_QUESTION = "first_question"
LESSON_STAGE_LEARNING_COACH_1 = "learning_coach_1"
LESSON_STAGE_CLARIFICATION = "clarification"
LESSON_STAGE_SECOND_QUESTION = "second_question"
LESSON_STAGE_LEARNING_COACH_2 = "learning_coach_2"
LESSON_STAGE_FINAL_ASSESSMENT = "final_assessment"
LESSON_STAGE_COMPLETED = "lesson_completed"
LESSON_STAGE_NEXT_LESSON = "next_lesson"

VALID_LESSON_STAGES = {
    LESSON_STAGE_INTRO,
    LESSON_STAGE_FIRST_EXPLANATION,
    LESSON_STAGE_FIRST_QUESTION,
    LESSON_STAGE_LEARNING_COACH_1,
    LESSON_STAGE_CLARIFICATION,
    LESSON_STAGE_SECOND_QUESTION,
    LESSON_STAGE_LEARNING_COACH_2,
    LESSON_STAGE_FINAL_ASSESSMENT,
    LESSON_STAGE_COMPLETED,
    LESSON_STAGE_NEXT_LESSON,
}

def update_lesson_stage(
        progress: dict,
        current_stage: str
):
    if current_stage not in VALID_LESSON_STAGES:
        raise ValueError(
            f"Invalid lesson stage: {current_stage}"
        )

    now = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    res = (
        sb.table(
            "kid_lesson_progress"
        )
        .update({
            "current_stage":
                current_stage,

            "last_activity_at":
                now,

            "updated_at":
                now
        })
        .eq(
            "id",
            progress["id"]
        )
        .execute()
    )

    if not res.data:
        raise RuntimeError(
            "Failed to update lesson stage"
        )

    return res.data[0]

def get_active_learning_coach_session(
        kid_id: str,
        lesson_id: int,
        unit_lesson_id: int,
        coach_index: int
):
    res = (
        sb.table(
            "learning_coach_sessions"
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
        .eq(
            "unit_lesson_id",
            unit_lesson_id
        )
        .eq(
            "coach_index",
            coach_index
        )
        .eq(
            "status",
            "active"
        )
        .order(
            "created_at",
            desc=True
        )
        .limit(1)
        .execute()
    )

    if not res.data:
        return None

    return res.data[0]

def create_learning_coach_session(
        kid_id: str,
        lesson_id: int,
        unit_lesson_id: int,
        coach_index: int,
        lesson_history_id: int | None = None
):
    if coach_index not in (1, 2):
        raise ValueError(
            f"Invalid coach_index: {coach_index}"
        )

    now = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    insert_data = {
        "kid_id":
            kid_id,

        "lesson_id":
            lesson_id,

        "unit_lesson_id":
            unit_lesson_id,

        "coach_index":
            coach_index,

        "started_at":
            now,

        "initial_understanding_score":
            0,

        "final_understanding_score":
            0,

        "total_rounds":
            0,

        "status":
            "active",

        "created_at":
            now
    }

    if lesson_history_id is not None:
        insert_data[
            "lesson_history_id"
        ] = lesson_history_id

    res = (
        sb.table(
            "learning_coach_sessions"
        )
        .insert(
            insert_data
        )
        .execute()
    )

    if not res.data:
        raise RuntimeError(
            "Failed to create "
            "Learning Coach session"
        )

    return res.data[0]

def get_or_create_learning_coach_session(
        kid_id: str,
        lesson_id: int,
        unit_lesson_id: int,
        coach_index: int
):
    existing_session = (
        get_active_learning_coach_session(
            kid_id=kid_id,
            lesson_id=lesson_id,
            unit_lesson_id=unit_lesson_id,
            coach_index=coach_index
        )
    )

    if existing_session:

        print(
            "LEARNING COACH SESSION FOUND:",
            json.dumps(
                {
                    "id":
                        existing_session.get("id"),

                    "coach_index":
                        existing_session.get(
                            "coach_index"
                        ),

                    "status":
                        existing_session.get("status"),

                    "total_rounds":
                        existing_session.get(
                            "total_rounds"
                        ),

                    "final_understanding_score":
                        existing_session.get(
                            "final_understanding_score"
                        )
                },
                ensure_ascii=False,
                indent=2
            )
        )

        return existing_session

    new_session = (
        create_learning_coach_session(
            kid_id=kid_id,
            lesson_id=lesson_id,
            unit_lesson_id=unit_lesson_id,
            coach_index=coach_index
        )
    )

    print(
        "LEARNING COACH SESSION CREATED:",
        json.dumps(
            {
                "id":
                    new_session.get("id"),

                "kid_id":
                    kid_id,

                "lesson_id":
                    lesson_id,

                "unit_lesson_id":
                    unit_lesson_id,

                "coach_index":
                    coach_index
            },
            ensure_ascii=False,
            indent=2
        )
    )

    return new_session

def extract_unit_lesson_coach_content(
        unit_lesson: dict
):
    generated_json = (
        unit_lesson.get(
            "generated_lesson_json"
        )
        or {}
    )

    structured_lesson = (
        generated_json.get(
            "structured_lesson"
        )
        or {}
    )

    lesson_segments = (
        structured_lesson.get(
            "lesson"
        )
        or []
    )

    explanation_parts = []

    for segment in lesson_segments:

        if not isinstance(
                segment,
                dict
        ):
            continue

        text = str(
            segment.get(
                "text"
            )
            or ""
        ).strip()

        if text:
            explanation_parts.append(
                text
            )

    lesson_explanation = "\n\n".join(
        explanation_parts
    )

    first_question = str(
        (
            structured_lesson.get(
                "question"
            )
            or {}
        ).get(
            "text"
        )
        or ""
    ).strip()

    return {
        "lesson_explanation":
            lesson_explanation,

        "first_question":
            first_question
    }

def build_learning_coach_prompt(
        child: dict,
        parent_lesson: dict,
        unit_lesson: dict,
        coach_session: dict,
        conversation_history: list[dict],
        child_answer: str
):
    coach_content = (
        extract_unit_lesson_coach_content(
            unit_lesson
        )
    )

    current_round = (
        int(
            coach_session.get(
                "total_rounds"
            )
            or 0
        )
        + 1
    )

    previous_score = int(
        coach_session.get(
            "final_understanding_score"
        )
        or coach_session.get(
            "initial_understanding_score"
        )
        or 0
    )

    conversation_text_parts = []

    for item in conversation_history:

        role = item.get("role")

        content = str(
            item.get("content")
            or ""
        ).strip()

        if not content:
            continue

        role_name = (
            "Child"
            if role == "user"
            else "Teacher"
        )

        conversation_text_parts.append(
            f"{role_name}: {content}"
        )

    conversation_text_parts.append(
        f"Child: {child_answer}"
    )

    conversation_text = "\n".join(
        conversation_text_parts
    )

    runtime_data = {
        "child": {
            "child_name":
                child.get("child_name"),

            "grade":
                child.get("age"),

            "gender":
                child.get("gender")
                or "male"
        },

        "lesson": {
            "subject":
                parent_lesson.get("subject"),

            "lesson_name":
                unit_lesson.get("lesson_name"),

            "lesson_goal":
                (
                    unit_lesson.get(
                        "learning_objective"
                    )
                    or parent_lesson.get(
                        "lesson_goal"
                    )
                ),

            "lesson_explanation":
                coach_content[
                    "lesson_explanation"
                ],

            "first_question":
                coach_content[
                    "first_question"
                ],

            # כרגע אין עמודה נפרדת של תשובה נכונה.
            # ההסבר ומטרת השיעור משמשים כמקור האמת.
            "correct_answer":
                "Derive from the lesson explanation and lesson goal."
        },

        "conversation": {
            "conversation_history":
                conversation_text
        },

        "coach_state": {
            "coach_index":
                int(
                    coach_session.get(
                        "coach_index"
                    )
                    or 1
                ),

            "current_round":
                current_round,

            "maximum_rounds":
                LEARNING_COACH_MAX_ROUNDS,

            "previous_understanding_score":
                previous_score
        }
    }

    final_prompt = (
        LEARNING_COACH_PROMPT_TEMPLATE
        + "\n\n"
        + "RUNTIME_DATA:\n"
        + json.dumps(
            runtime_data,
            ensure_ascii=False,
            indent=2
        )
    )

    return (
        final_prompt,
        runtime_data,
        current_round
    )

def update_learning_coach_session(
        coach_session: dict,
        understanding_score: int,
        goal_achieved: bool,
        current_round: int
):
    now = datetime.now(
        timezone.utc
    )

    max_rounds_reached = (
        current_round
        >= LEARNING_COACH_MAX_ROUNDS
    )

    if goal_achieved:
        status = "completed"

    elif max_rounds_reached:
        status = "max_rounds"

    else:
        status = "active"

    update_data = {
        "final_understanding_score":
            understanding_score,

        "total_rounds":
            current_round,

        "status":
            status
    }

    if status != "active":
        update_data[
            "ended_at"
        ] = now.isoformat()

    res = (
        sb.table(
            "learning_coach_sessions"
        )
        .update(
            update_data
        )
        .eq(
            "id",
            coach_session["id"]
        )
        .execute()
    )

    if res.data:
        return res.data[0]

    return {
        **coach_session,
        **update_data
    }


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

    def operation():

        return (
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
                "learning_objective, "
                "lesson_complexity, "
                "max_duration_seconds, "
                "generation_status, "
                "content_version, "
                "generated_lesson_json, "
                "generation_error, "
                "generated_at, "
                "tts_generated_at, "
                "lesson_audio_json, "
                "audio_generation_status, "
                "audio_generation_error, "
                "audio_generated_at, "
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

    res = supabase_with_retry(
        operation,
        label="GET UNIT LESSON"
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

    def operation():

        return (
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

    res = supabase_with_retry(
        operation,
        label="GET INTRO TEMPLATE"
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

    def operation():

        return (
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

    res = supabase_with_retry(
        operation,
        label="GET LEARNING LESSON"
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
        is_lesson_start: bool = False,
        unit_lesson_id: int | None = None
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

            "current_unit_lesson_id":
                unit_lesson_id,

            "status":
                "in_progress",

            "current_stage":
                LESSON_STAGE_INTRO,

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
        unit_lesson_id: int | None = None,
        limit: int = 8
):
    query = (
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
    )

    if unit_lesson_id is not None:
        query = query.eq(
            "unit_lesson_id",
            unit_lesson_id
        )

    res = (
        query
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

        for message in messages

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
        unit_lesson_id: int | None,
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

            "unit_lesson_id":
                unit_lesson_id,

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

        "unit_lesson_id":
            unit_lesson_id,

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

    now = datetime.now(
        timezone.utc
    )

    # =============================================
    # FIND ACTIVE SESSION
    # =============================================

    def load_session():

        return (
            sb.table(
                "tutor_sessions"
            )
            .select(
                "id, started_at, last_activity_at, status, "
                "message_count, user_message_count, "
                "assistant_message_count, ai_call_count, "
                "input_tokens, output_tokens, total_tokens, "
                "estimated_cost_usd"
            )
            .eq(
                "user_id",
                user_id
            )
            .eq(
                "kid_id",
                kid_id
            )
            .eq(
                "status",
                "active"
            )
            .order(
                "last_activity_at",
                desc=True
            )
            .limit(1)
            .execute()
        )

    res = supabase_with_retry(
        load_session,
        label="GET TUTOR SESSION"
    )

    # =============================================
    # EXISTING SESSION
    # =============================================

    if res.data:

        session = res.data[0]

        last_activity = (
            parse_supabase_datetime(
                session.get(
                    "last_activity_at"
                )
            )
        )

        if last_activity:

            inactive_time = (
                now - last_activity
            )

            if inactive_time < timedelta(
                    minutes=
                        SESSION_TIMEOUT_MINUTES
            ):

                session["_is_new"] = False

                return session

        # =========================================
        # CLOSE OLD SESSION
        # =========================================

        started_at = (
            parse_supabase_datetime(
                session.get(
                    "started_at"
                )
            )
        )

        duration_seconds = 0

        if started_at and last_activity:

            duration_seconds = max(
                0,
                int(
                    (
                        last_activity
                        - started_at
                    ).total_seconds()
                )
            )

        def close_old_session():

            return (
                sb.table(
                    "tutor_sessions"
                )
                .update({
                    "status":
                        "completed",

                    "ended_at":
                        (
                            last_activity
                            or now
                        ).isoformat(),

                    "duration_seconds":
                        duration_seconds,

                    "updated_at":
                        now.isoformat()
                })
                .eq(
                    "id",
                    session["id"]
                )
                .execute()
            )

        supabase_with_retry(
            close_old_session,
            label="CLOSE TUTOR SESSION"
        )

        try:

            increment_usage_summary(
                user_id=user_id,
                usage_seconds=
                    duration_seconds
            )

        except Exception as usage_error:

            print(
                "SESSION USAGE UPDATE ERROR:",
                repr(usage_error)
            )

    # =============================================
    # CREATE SESSION
    # =============================================

    def create_session():

        return (
            sb.table(
                "tutor_sessions"
            )
            .insert({
                "user_id":
                    user_id,

                "kid_id":
                    kid_id,

                "started_at":
                    now.isoformat(),

                "last_activity_at":
                    now.isoformat(),

                "status":
                    "active",

                "ai_model":
                    "gpt-4o-mini",

                "tts_model":
                    "gemini-3.1-flash-tts-preview"
            })
            .execute()
        )

    new_session_res = (
        supabase_with_retry(
            create_session,
            label="CREATE TUTOR SESSION"
        )
    )

    if not new_session_res.data:

        raise RuntimeError(
            "Failed to create tutor session"
        )

    new_session = (
        new_session_res.data[0]
    )

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

    def operation():
        return (
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
            )
            .execute()
        )

    return supabase_with_retry(
        operation,
        label="INCREMENT USAGE SUMMARY",
        max_attempts=3
    )


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

    lesson_complexity = int(
        unit_lesson.get(
            "lesson_complexity"
        )
        or 2
    )

    max_duration_seconds = int(
        unit_lesson.get(
            "max_duration_seconds"
        )
        or 120
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

        "{learning_objective}":
            str(
                unit_lesson.get(
                    "learning_objective"
                )
                or ""
            ),

        "{lesson_complexity}":
            str(
                lesson_complexity
            ),

        "{max_duration_seconds}":
            str(
                max_duration_seconds
            )

    }

    for placeholder, value in replacements.items():

        prompt = prompt.replace(
            placeholder,
            value
        )

    return prompt

def build_lesson_director_prompt(
        lesson_text: str
) -> str:

    return (
        LESSON_DIRECTOR_PROMPT_TEMPLATE
        .replace(
            "{lesson_text}",
            lesson_text
        )
    )


def build_visual_director_prompt(
        unit_lesson: dict,
        parent_lesson: dict,
        lesson_text: str,
        structured_lesson: dict
) -> str:

    runtime_context = {

        "grade":
            parent_lesson.get(
                "grade"
            ),

        "subject":
            parent_lesson.get(
                "subject"
            ),

        "main_topic":
            parent_lesson.get(
                "lesson_name"
            ),

        "unit_name":
            unit_lesson.get(
                "unit_name"
            ),

        "lesson_name":
            unit_lesson.get(
                "lesson_name"
            ),

        "learning_objective":
            unit_lesson.get(
                "learning_objective"
            ),

        "lesson_text":
            lesson_text,

        "structured_lesson":
            structured_lesson
    }

    return (
        VISUAL_DIRECTOR_PROMPT_TEMPLATE
        + "\n\n"
        + "RUNTIME_CONTEXT:\n"
        + json.dumps(
            runtime_context,
            ensure_ascii=False,
            indent=2
        )
    )

def build_lesson_transition_prompt(
        unit_lesson: dict,
        parent_lesson: dict,
        part_1: dict,
        part_2: dict
) -> str:

    runtime_context = {

        "grade":
            parent_lesson.get(
                "grade"
            ),

        "subject":
            parent_lesson.get(
                "subject"
            ),

        "lesson_name":
            unit_lesson.get(
                "lesson_name"
            ),

        "learning_objective":
            unit_lesson.get(
                "learning_objective"
            ),

        "part_1":
            part_1,

        "part_2":
            part_2
    }

    return (
        LESSON_TRANSITION_PROMPT_TEMPLATE
        + "\n\n"
        + "RUNTIME_CONTEXT:\n"
        + json.dumps(
            runtime_context,
            ensure_ascii=False,
            indent=2
        )
    )

def build_segment_visual_fallback_prompt(
        unit_lesson: dict,
        parent_lesson: dict,
        segment_text: str,
        segment_index: int
) -> str:

    grade = str(
        parent_lesson.get("grade")
        or ""
    )

    subject = str(
        parent_lesson.get("subject")
        or ""
    )

    main_topic = str(
        parent_lesson.get("lesson_name")
        or ""
    )

    unit_name = str(
        unit_lesson.get("unit_name")
        or ""
    )

    lesson_name = str(
        unit_lesson.get("lesson_name")
        or ""
    )

    learning_objective = str(
        unit_lesson.get("learning_objective")
        or ""
    )

    return f"""
Create one premium educational 16:9 illustration
for segment {segment_index} of a school lesson.

CURRICULUM CONTEXT:

Grade: {grade}
Subject: {subject}
Main topic: {main_topic}
Unit: {unit_name}
Lesson: {lesson_name}
Learning objective: {learning_objective}

EXACT LESSON SEGMENT:

{segment_text}

VISUAL GOAL:

Translate the educational meaning of this exact segment
into one clear visual scene.

The image must help the student understand this segment
while listening to its corresponding audio.

Use the full curriculum context.
Do not interpret isolated keywords.

REQUIREMENTS:

- educationally accurate
- appropriate for grade {grade}
- premium modern educational illustration
- 16:9 landscape composition
- one clear educational focus
- visually rich but easy to understand
- maintain continuity with the lesson context
- no written text
- no labels
- no captions
- no logos
- no watermark
- no UI elements
- no title cards
""".strip()


def normalize_visual_plan_to_segments(
        visual_plan: dict,
        structured_lesson: dict,
        unit_lesson: dict,
        parent_lesson: dict
) -> dict:

    segments = (
        structured_lesson.get("lesson")
        or []
    )

    raw_visuals = (
        visual_plan.get("visuals")
        or []
    )

    normalized_visuals = []

    print(
        "VISUAL PLAN NORMALIZATION START:",
        {
            "segments_count":
                len(segments),

            "director_visuals_count":
                len(raw_visuals)
        }
    )

    for index, segment in enumerate(
            segments,
            start=1
    ):

        if not isinstance(
                segment,
                dict
        ):
            continue

        segment_text = str(
            segment.get("text")
            or ""
        ).strip()

        if not segment_text:
            continue

        # =========================================
        # FIND VISUAL RETURNED BY DIRECTOR
        # =========================================

        director_visual = None

        # קודם מחפשים לפי order
        for item in raw_visuals:

            if not isinstance(
                    item,
                    dict
            ):
                continue

            try:
                item_order = int(
                    item.get("order")
                    or 0
                )
            except Exception:
                item_order = 0

            if item_order == index:
                director_visual = item
                break

        # =========================================
        # GENERATION PROMPT
        # =========================================

        generation_prompt = ""

        visual_goal = (
            f"Help the student understand "
            f"lesson segment {index}."
        )

        if director_visual:

            generation_prompt = str(
                director_visual.get(
                    "generation_prompt"
                )
                or ""
            ).strip()

            visual_goal = str(
                director_visual.get(
                    "visual_goal"
                )
                or visual_goal
            ).strip()

        # אם ה-Director דילג על הסגמנט,
        # ה-Backend מייצר Prompt בעצמו.
        if not generation_prompt:

            print(
                "VISUAL DIRECTOR MISSING SEGMENT:",
                {
                    "segment_index":
                        index,

                    "segment_text":
                        segment_text
                }
            )

            generation_prompt = (
                build_segment_visual_fallback_prompt(
                    unit_lesson=
                        unit_lesson,

                    parent_lesson=
                        parent_lesson,

                    segment_text=
                        segment_text,

                    segment_index=
                        index
                )
            )

        # =========================================
        # TRIGGER
        #
        # היום הפרונט כבר מתקדם לפי order,
        # אבל עדיין נשמור trigger_text תקין.
        # =========================================

        words = (
            segment_text
            .replace("\n", " ")
            .split()
        )

        trigger_text = " ".join(
            words[:6]
        )

        # =========================================
        # HARD 1:1 VISUAL
        # =========================================

        normalized_visuals.append({

            "order":
                index,

            "trigger_text":
                trigger_text,

            # חשוב:
            # כל Segment הוא תמונה.
            # גם אם ה-Director החזיר video.
            "type":
                "image",

            "visual_goal":
                visual_goal,

            "source_text":
                segment_text,

            "generation_prompt":
                generation_prompt
        })

    result = {
        "version":
            int(
                visual_plan.get("version")
                or 1
            ),

        "visuals":
            normalized_visuals
    }

    print(
        "VISUAL PLAN NORMALIZATION DONE:",
        {
            "segments_count":
                len(segments),

            "visuals_count":
                len(normalized_visuals),

            "orders":
                [
                    item["order"]
                    for item
                    in normalized_visuals
                ]
        }
    )

    return result

def normalize_universal_lesson_visuals(
        sequence: list[TutorAction]
) -> list[TutorAction]:

    normalized_sequence = []

    visual_count = 0

    max_visual_cards = 2

    for action in sequence:

        # כל פעולה רגילה נשמרת
        if action.type != "visual_card":

            normalized_sequence.append(
                action
            )

            continue


        # מגבילים לשתי המחשות בשיעור
        if visual_count >= max_visual_cards:
            continue


        title = (
            action.title
            or ""
        ).strip()


        raw_items = (
            action.items
            or []
        )


        clean_items = []

        for item in raw_items:

            clean_item = str(
                item
                or ""
            ).strip()

            if not clean_item:
                continue

            if clean_item in clean_items:
                continue

            clean_items.append(
                clean_item
            )


        # כרטיס לא תקין לא נכנס לרצף
        if not title:
            continue

        if len(clean_items) < 2:
            continue


        # לא יותר מחמישה פריטים
        clean_items = clean_items[:5]


        normalized_sequence.append(

            TutorAction(
                type="visual_card",
                title=title,
                items=clean_items,
                icon=action.icon
            )

        )

        visual_count += 1


    return normalized_sequence

# =====================================================
# UNIVERSAL LESSON MEDIA
# Shared images / videos for all children
# =====================================================

LESSON_MEDIA_BUCKET = "lesson-media"

LESSON_MEDIA_URL_EXPIRY_SECONDS = 3600

# בשלב הראשון נייצר רק Hero Image אחת לכל תת-שיעור
LESSON_MEDIA_HERO_VERSION = 1


def get_lesson_media_storage_path(
        unit_lesson_id: int,
        media_type: str = "hero"
) -> str:
    """
    נתיב קבוע למדיה של תת-שיעור.

    אותו unit_lesson_id תמיד יוביל
    לאותו קובץ, ולכן ילדים אחרים
    יוכלו להשתמש באותה מדיה.
    """

    if media_type == "hero":
        return (
            f"unit_lessons/"
            f"{unit_lesson_id}/"
            f"hero_v{LESSON_MEDIA_HERO_VERSION}.png"
        )

    raise ValueError(
        f"Unsupported lesson media type: "
        f"{media_type}"
    )


def create_lesson_media_signed_url(
        storage_path: str
) -> str:
    """
    יוצר URL זמני לקובץ שכבר נמצא
    ב-Supabase Storage.
    """

    signed_response = (
        sb.storage
        .from_(
            LESSON_MEDIA_BUCKET
        )
        .create_signed_url(
            storage_path,
            LESSON_MEDIA_URL_EXPIRY_SECONDS
        )
    )

    signed_url = None

    if isinstance(
            signed_response,
            dict
    ):
        signed_url = (
            signed_response.get(
                "signedURL"
            )
            or signed_response.get(
                "signedUrl"
            )
            or signed_response.get(
                "signed_url"
            )
        )

    if not signed_url:
        raise RuntimeError(
            "Failed to create signed URL "
            f"for lesson media: {storage_path}"
        )

    return signed_url


def build_lesson_hero_image_prompt(
        unit_lesson: dict,
        parent_lesson: dict
) -> str:
    """
    Prompt אוניברסלי לתמונה הראשונה של השיעור.

    אין כאן מידע אישי על הילד.
    לכן התמונה יכולה להישמר ולהיות
    משותפת לכל הילדים שלומדים את אותו שיעור.
    """

    grade = str(
        parent_lesson.get(
            "grade"
        )
        or ""
    ).strip()

    subject = str(
        parent_lesson.get(
            "subject"
        )
        or ""
    ).strip()

    parent_lesson_name = str(
        parent_lesson.get(
            "lesson_name"
        )
        or ""
    ).strip()

    unit_name = str(
        unit_lesson.get(
            "unit_name"
        )
        or ""
    ).strip()

    lesson_name = str(
        unit_lesson.get(
            "lesson_name"
        )
        or ""
    ).strip()

    learning_objective = str(
        unit_lesson.get(
            "learning_objective"
        )
        or ""
    ).strip()

    return f"""
Create one premium educational HERO illustration for a school lesson.

CURRICULUM CONTEXT:
Grade: {grade}
Subject: {subject}
Main topic: {parent_lesson_name}
Unit: {unit_name}
Lesson: {lesson_name}
Learning objective: {learning_objective}

IMPORTANT CONTEXT RULE:
The lesson title must NEVER be interpreted in isolation.

First understand the lesson through its complete curriculum context:
Subject -> Main topic -> Unit -> Lesson -> Learning objective.

The illustration must clearly belong to the MAIN TOPIC and UNIT,
while visually introducing the specific LESSON.

If the lesson title is broad or ambiguous, use the Main topic,
Unit and Learning objective to determine its correct meaning.

For example:
If a lesson is called "What is a system?" and it belongs to a unit
about ecosystems, the image should explain the idea of a system
through an ecological context: living and non-living elements
interacting, influencing and depending on one another.

Do NOT interpret such a lesson as a mechanical system,
computer system, gears, machinery or another unrelated type
of system unless the curriculum context specifically requires it.

VISUAL GOAL:
Create one immediately understandable visual scene that helps
the student intuitively understand the central concept of the lesson
before the full lesson explanation begins.

The image must TEACH the concept visually,
not simply decorate or illustrate the lesson title.

The visual should prioritize the actual educational concept
described by the curriculum context and learning objective.

REQUIREMENTS:
- appropriate for a student in grade {grade}
- educational and scientifically accurate
- one clear central educational concept
- premium modern 3D educational illustration
- visually rich and engaging but not childish
- realistic enough to support learning
- clear visual relationships between important elements
- cinematic soft lighting
- clean professional composition
- suitable for a large lesson presentation area
- landscape composition
- no written text
- no labels
- no captions
- no logos
- no watermark
""".strip()

# =====================================================
# GEMINI LESSON HERO IMAGE
# =====================================================

LESSON_IMAGE_MODEL = (
    "gemini-3.1-flash-image"
)


def generate_lesson_hero_image_bytes(
        prompt: str
) -> tuple[bytes, str]:
    """
    יוצר תמונת Hero אחת דרך Gemini.

    מחזיר:
    - bytes של התמונה
    - MIME type
    """

    clean_prompt = str(
        prompt or ""
    ).strip()

    if not clean_prompt:
        raise RuntimeError(
            "Lesson hero image prompt is empty"
        )

    print(
        "========== LESSON IMAGE GENERATION START ==========",
        {
            "model":
                LESSON_IMAGE_MODEL,

            "prompt_length":
                len(clean_prompt)
        }
    )

    started_at = (
        time.perf_counter()
    )

    response = (
        gemini_client
        .models
        .generate_content(

            model=
                LESSON_IMAGE_MODEL,

            contents=
                clean_prompt,

            config=
            types.GenerateContentConfig(

                response_modalities=[
                    "IMAGE"
                ],

                image_config=
                types.ImageConfig(
                    aspect_ratio="16:9",
                    image_size="1K"
                )
            )
        )
    )

    elapsed_ms = round(
        (
            time.perf_counter()
            - started_at
        )
        * 1000
    )

    print(
        "========== LESSON IMAGE GEMINI RESPONSE ==========",
        {
            "elapsed_ms":
                elapsed_ms
        }
    )

    # =================================================
    # FIND IMAGE PART
    # =================================================

    response_parts = (
        getattr(
            response,
            "parts",
            None
        )
        or []
    )

    for part in response_parts:

        inline_data = getattr(
            part,
            "inline_data",
            None
        )

        if inline_data is None:
            continue

        image_data = getattr(
            inline_data,
            "data",
            None
        )

        if not image_data:
            continue

        mime_type = (
            getattr(
                inline_data,
                "mime_type",
                None
            )
            or
            "image/png"
        )

        # בחלק מגרסאות SDK
        # data מגיע כ-bytes.
        #
        # באחרות הוא יכול להגיע
        # כ-base64 string.
        if isinstance(
                image_data,
                str
        ):

            image_bytes = (
                base64.b64decode(
                    image_data
                )
            )

        else:

            image_bytes = bytes(
                image_data
            )

        if not image_bytes:
            continue

        print(
            "========== LESSON IMAGE GENERATED ==========",
            {
                "elapsed_ms":
                    elapsed_ms,

                "mime_type":
                    mime_type,

                "bytes":
                    len(image_bytes)
            }
        )

        return (
            image_bytes,
            mime_type
        )

    raise RuntimeError(
        "Gemini returned no image data"
    )

def generate_lesson_visual_image_bytes(
        prompt: str,
        reference_image_bytes: bytes | None = None,
        reference_mime_type: str = "image/png"
) -> tuple[bytes, str]:

    clean_prompt = str(
        prompt or ""
    ).strip()

    if not clean_prompt:
        raise RuntimeError(
            "Lesson visual image prompt is empty"
        )

    # =============================================
    # NORMAL FIRST IMAGE
    # =============================================

    if not reference_image_bytes:

        return generate_lesson_hero_image_bytes(
            clean_prompt
        )

    # =============================================
    # REFERENCE-BASED IMAGE GENERATION
    # =============================================

    reference_part = types.Part.from_bytes(
        data=reference_image_bytes,
        mime_type=reference_mime_type
    )

    reference_prompt = f"""
    The attached image is the MASTER STYLE REFERENCE
    for an educational lesson image series.

    You must create a NEW SCENE, but it MUST look like it was
    created by the EXACT SAME illustrator, using the EXACT SAME
    visual medium and rendering technique as the reference image.

    CRITICAL STYLE LOCK:

    The reference image controls HOW the new image looks.
    The CURRENT SCENE controls ONLY WHAT the new image shows.

    DO NOT change the visual medium because of the scene description.

    MATCH THE REFERENCE IMAGE:

    - same premium semi-realistic digital illustration style
    - same illustrated rendering technique
    - same character design language
    - same level of illustrated realism
    - same cinematic lighting style
    - same color palette and color treatment
    - same texture and material treatment
    - same depth and atmosphere
    - same visual detail density
    - same cinematic quality
    - same overall educational production style

    The result must visually belong to the SAME IMAGE SERIES
    as the reference.

    If the reference looks semi-realistic,
    the new image MUST remain semi-realistic.

    If the reference uses realistic materials and lighting,
    preserve those characteristics.

    NEVER convert the scene into:

    - an infographic
    - a diagram
    - a labeled educational chart
    - a technical illustration
    - a poster
    - a textbook page
    - a cartoon
    - flat vector artwork
    - comic-book artwork
    - watercolor
    - a different illustration style

    VERY IMPORTANT:

    Do NOT copy any text, labels or annotations
    that may appear in the scene description.

    ABSOLUTELY NO WRITTEN TEXT IN THE IMAGE.

    No:
    - words
    - labels
    - titles
    - captions
    - letters
    - numbers
    - arrows with text
    - annotations
    - logos
    - watermarks
    - readable signs

    When the same bicycle, child, object or environment
    appears again, preserve its established visual identity
    from the reference whenever applicable.

    The composition and action may change completely.
    The STYLE MUST NOT.

    Think of this as another frame from the exact same
    animated educational film.

    CURRENT SCENE CONTENT:

    {clean_prompt}

    Again:
    Use the CURRENT SCENE only to determine WHAT is shown.
    Use the REFERENCE IMAGE to determine HOW everything looks.
    """.strip()

    print(
        "LESSON VISUAL WITH REFERENCE:",
        {
            "prompt_length":
                len(reference_prompt),

            "reference_bytes":
                len(reference_image_bytes)
        }
    )

    started_at = (
        time.perf_counter()
    )

    response = (
        gemini_client
        .models
        .generate_content(

            model=
                LESSON_IMAGE_MODEL,

            contents=[
                reference_part,
                reference_prompt
            ],

            config=
            types.GenerateContentConfig(

                response_modalities=[
                    "IMAGE"
                ],

                image_config=
                types.ImageConfig(
                    aspect_ratio="16:9",
                    image_size="1K"
                )
            )
        )
    )

    elapsed_ms = round(
        (
            time.perf_counter()
            - started_at
        )
        * 1000
    )

    response_parts = (
        getattr(
            response,
            "parts",
            None
        )
        or []
    )

    for part in response_parts:

        inline_data = getattr(
            part,
            "inline_data",
            None
        )

        if inline_data is None:
            continue

        image_data = getattr(
            inline_data,
            "data",
            None
        )

        if not image_data:
            continue

        mime_type = (
            getattr(
                inline_data,
                "mime_type",
                None
            )
            or "image/png"
        )

        if isinstance(
                image_data,
                str
        ):

            image_bytes = (
                base64.b64decode(
                    image_data
                )
            )

        else:

            image_bytes = bytes(
                image_data
            )

        print(
            "LESSON VISUAL REFERENCE IMAGE GENERATED:",
            {
                "elapsed_ms":
                    elapsed_ms,

                "bytes":
                    len(image_bytes),

                "mime_type":
                    mime_type
            }
        )

        return (
            image_bytes,
            mime_type
        )

    raise RuntimeError(
        "Gemini returned no reference-based image data"
    )

# =====================================================
# GENERATE + STORE HERO IMAGE
# =====================================================

def generate_and_store_lesson_hero_image(
        unit_lesson_id: int
) -> dict:
    """
    יוצר Hero Image אוניברסלית
    עבור unit lesson אחד.

    התמונה:
    1. נוצרת דרך Gemini
    2. עולה ל-Supabase Storage
    3. מקבלת Signed URL
    4. מוחזרת כ-metadata

    אין כאן kid_id.
    המדיה שייכת לשיעור עצמו.
    """

    print(
        "LESSON HERO IMAGE START:",
        unit_lesson_id
    )

    # =================================================
    # LOAD UNIT LESSON
    # =================================================

    unit_lesson = get_unit_lesson(
        unit_lesson_id
    )

    # =================================================
    # LOAD PARENT LESSON
    # =================================================

    parent_lesson = (
        get_learning_lesson(
            unit_lesson[
                "learning_lesson_id"
            ]
        )
    )

    # =================================================
    # BUILD EDUCATIONAL PROMPT
    # =================================================

    image_prompt = (
        build_lesson_hero_image_prompt(

            unit_lesson=
                unit_lesson,

            parent_lesson=
                parent_lesson
        )
    )

    print(
        "LESSON HERO IMAGE PROMPT:",
        {
            "unit_lesson_id":
                unit_lesson_id,

            "lesson_name":
                unit_lesson.get(
                    "lesson_name"
                ),

            "prompt":
                image_prompt
        }
    )

    # =================================================
    # GEMINI
    # =================================================

    image_bytes, mime_type = (
        generate_lesson_hero_image_bytes(
            image_prompt
        )
    )

    # =================================================
    # STORAGE PATH
    # =================================================

    storage_path = (
        get_lesson_media_storage_path(
            unit_lesson_id=
                unit_lesson_id,

            media_type=
                "hero"
        )
    )

    # =================================================
    # UPLOAD TO SUPABASE STORAGE
    # =================================================

    print(
        "LESSON HERO IMAGE UPLOAD:",
        {
            "bucket":
                LESSON_MEDIA_BUCKET,

            "path":
                storage_path,

            "bytes":
                len(image_bytes)
        }
    )

    sb.storage.from_(
        LESSON_MEDIA_BUCKET
    ).upload(

        path=
            storage_path,

        file=
            image_bytes,

        file_options={
            "content-type":
                mime_type,

            # אם אנחנו מייצרים גרסה מחדש,
            # הקובץ הקודם יוחלף.
            "upsert":
                "true"
        }
    )

    # =================================================
    # SIGNED URL
    # =================================================

    signed_url = (
        create_lesson_media_signed_url(
            storage_path
        )
    )

    generated_at = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    result = {

        "type":
            "image",

        "role":
            "hero",

        "version":
            LESSON_MEDIA_HERO_VERSION,

        "provider":
            "gemini",

        "model":
            LESSON_IMAGE_MODEL,

        "bucket":
            LESSON_MEDIA_BUCKET,

        "storage_path":
            storage_path,

        "mime_type":
            mime_type,

        "aspect_ratio":
            "16:9",

        "image_size":
            "1K",

        "generated_at":
            generated_at,

        # זה זמני בלבד.
        # את ה-URL עצמו לא נשמור ב-DB.
        "url":
            signed_url,

        "url_expires_in_seconds":
            LESSON_MEDIA_URL_EXPIRY_SECONDS
    }

    print(
        "LESSON HERO IMAGE READY:",
        {
            "unit_lesson_id":
                unit_lesson_id,

            "storage_path":
                storage_path,

            "generated_at":
                generated_at
        }
    )

    return result

# =====================================================
# AI TUTOR NATURAL VOICE - GEMINI TTS
# =====================================================
LESSON_AUDIO_BUCKET = "lesson-audio"
LESSON_AUDIO_URL_EXPIRY_SECONDS = 3600

def generate_and_store_lesson_visual_image(
        unit_lesson_id: int,
        content_version: int,
        visual: dict,
        reference_image_bytes: bytes | None = None,
        reference_mime_type: str = "image/png"
) -> dict:

    visual_order = int(
        visual.get("order")
        or 0
    )

    generation_prompt = str(
        visual.get("generation_prompt")
        or ""
    ).strip()

    # =============================================
    # GLOBAL LESSON VISUAL STYLE LOCK
    #
    # חל על visual_1 וגם על כל התמונות שאחריה.
    # visual_1 תקבע את ה-DNA החזותי של השיעור.
    # =============================================

    LESSON_VISUAL_STYLE_LOCK = """
    Create a premium semi-realistic digital educational illustration.

    This image belongs to a high-end educational animated visual series
    for children.

    MANDATORY VISUAL STYLE:

    - premium semi-realistic digital illustration
    - high-end animated educational film quality
    - realistic human and object proportions
    - clearly illustrated, NOT photographic
    - detailed digital painting with polished rendering
    - soft cinematic natural lighting
    - warm, rich but controlled colors
    - subtle depth and atmospheric perspective
    - clean professional composition
    - realistic materials interpreted through illustration
    - expressive but natural characters
    - modern premium educational media aesthetic
    - visually engaging for children without looking childish

    The final result must clearly look like
    a professionally illustrated scene,
    NOT a photograph.

    CHARACTER STYLE:

    When children appear:

    - use relatable school-age children around 10-12 years old
    - natural facial features
    - realistic proportions
    - expressive but believable poses
    - modern everyday clothing
    - friendly and intelligent appearance
    - never exaggerated cartoon proportions

    When the same child appears in later images,
    preserve the child's:

    - approximate face and appearance
    - age
    - hairstyle
    - clothing colors and design
    - body proportions

    OBJECT CONTINUITY:

    When an important object appears again,
    preserve its established visual identity.

    For example, the same bicycle should maintain:

    - frame design
    - frame color
    - wheel style
    - proportions
    - important recognizable details

    VISUAL WORLD:

    All lesson images should feel like consecutive scenes
    from the SAME premium educational animated film.

    They may show different actions, locations, camera angles
    and compositions, but the artistic rendering must remain consistent.

    DO NOT create:

    - photography
    - photorealistic photography
    - stock photography
    - live-action imagery
    - flat cartoons
    - childish cartoons
    - flat vector art
    - infographic
    - diagram
    - technical drawing
    - textbook page
    - educational poster
    - comic-book art
    - watercolor
    - anime
    - 3D infographic
    - labeled educational chart

    ABSOLUTELY NO WRITTEN TEXT INSIDE THE IMAGE.

    Do not include:

    - words
    - labels
    - captions
    - titles
    - letters
    - numbers
    - annotations
    - readable signs
    - logos
    - watermarks
    - arrows containing text

    Educational concepts must be communicated
    through the visual scene itself.

    IMPORTANT:

    ILLUSTRATION STYLE is mandatory.

    Even when the scene describes a realistic situation,
    render it as a premium semi-realistic digital illustration,
    never as a photograph.
    """.strip()

    final_generation_prompt = f"""
    {LESSON_VISUAL_STYLE_LOCK}

    CURRENT EDUCATIONAL SCENE:

    {generation_prompt}
    """.strip()

    trigger_text = str(
        visual.get("trigger_text")
        or ""
    ).strip()

    if not visual_order:
        raise RuntimeError(
            "Visual order is missing"
        )

    if not generation_prompt:
        raise RuntimeError(
            "Visual generation prompt is missing"
        )

    print(
        "LESSON VISUAL IMAGE START:",
        {
            "unit_lesson_id":
                unit_lesson_id,

            "content_version":
                content_version,

            "order":
                visual_order,

            "trigger_text":
                trigger_text
        }
    )

    image_bytes, mime_type = (
        generate_lesson_visual_image_bytes(
            final_generation_prompt,
            reference_image_bytes=
            reference_image_bytes,
            reference_mime_type=
            reference_mime_type
        )
    )

    storage_path = (
        f"unit_lessons/"
        f"{unit_lesson_id}/"
        f"v{content_version}/"
        f"visual_{visual_order}.png"
    )

    sb.storage.from_(
        LESSON_MEDIA_BUCKET
    ).upload(

        path=
            storage_path,

        file=
            image_bytes,

        file_options={
            "content-type":
                mime_type,

            "upsert":
                "true"
        }
    )

    print(
        "LESSON VISUAL IMAGE STORED:",
        {
            "unit_lesson_id":
                unit_lesson_id,

            "order":
                visual_order,

            "storage_path":
                storage_path
        }
    )

    return {
        "order":
            visual_order,

        "type":
            "image",

        "trigger_text":
            trigger_text,

        "storage_path":
            storage_path,

        "mime_type":
            mime_type
    }

def generate_all_lesson_visuals_background(
        unit_lesson_id: int
):
    import time
    import traceback

    MAX_VISUAL_RETRIES = 3
    RETRY_DELAY_SECONDS = 3

    try:

        unit_lesson = get_unit_lesson(
            unit_lesson_id
        )

        generated_lesson_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
            or {}
        )

        visual_plan = (
            generated_lesson_json.get(
                "visual_plan"
            )
            or {}
        )

        visuals = (
            visual_plan.get(
                "visuals"
            )
            or []
        )

        content_version = int(
            unit_lesson.get(
                "content_version"
            )
            or 1
        )

        if not visuals:

            print(
                "NO VISUALS FOUND IN VISUAL PLAN:",
                unit_lesson_id
            )

            return

        generated_visuals = []
        master_reference_bytes = None
        master_reference_mime_type = "image/png"
        image_visuals = [
            visual
            for visual in visuals
            if isinstance(visual, dict)
            and str(
                visual.get("type") or ""
            ).strip().lower() == "image"
        ]

        structured_lesson = (
            generated_lesson_json.get(
                "structured_lesson"
            )
            or {}
        )

        segments = (
            structured_lesson.get(
                "lesson"
            )
            or []
        )

        print(
            "VISUAL/AUDIO SEGMENT CHECK:",
            {
                "unit_lesson_id":
                    unit_lesson_id,

                "segments_count":
                    len(segments),

                "visuals_count":
                    len(image_visuals)
            }
        )

        if (
            len(image_visuals)
            !=
            len(segments)
        ):

            print(
                "CRITICAL VISUAL COUNT MISMATCH:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "segments_count":
                        len(segments),

                    "visuals_count":
                        len(image_visuals)
                }
            )

        print(
            "LESSON VISUAL GENERATION START:",
            {
                "unit_lesson_id":
                    unit_lesson_id,

                "content_version":
                    content_version,

                "planned_images":
                    len(image_visuals)
            }
        )

        for visual in image_visuals:

            visual_order = (
                visual.get("order")
            )
            # =========================================
            # MASTER VISUAL REFERENCE
            #
            # visual_1 היא התמונה שמגדירה את העולם
            # החזותי של כל השיעור.
            # =========================================

            if (
                    int(visual_order or 0) > 1
                    and master_reference_bytes is None
            ):

                reference_storage_path = (
                    f"unit_lessons/"
                    f"{unit_lesson_id}/"
                    f"v{content_version}/"
                    f"visual_1.png"
                )

                try:

                    master_reference_bytes = (
                        sb.storage
                        .from_(
                            LESSON_MEDIA_BUCKET
                        )
                        .download(
                            reference_storage_path
                        )
                    )

                    master_reference_mime_type = (
                        "image/png"
                    )

                    print(
                        "LESSON MASTER VISUAL REFERENCE LOADED:",
                        {
                            "unit_lesson_id":
                                unit_lesson_id,

                            "storage_path":
                                reference_storage_path,

                            "bytes":
                                len(
                                    master_reference_bytes
                                    or b""
                                )
                        }
                    )

                except Exception as reference_error:

                    print(
                        "LESSON MASTER VISUAL REFERENCE NOT READY:",
                        {
                            "unit_lesson_id":
                                unit_lesson_id,

                            "error":
                                repr(reference_error)
                        }
                    )

                    master_reference_bytes = None
            # =========================================
            # VISUAL CACHE CHECK
            #
            # אם התמונה כבר קיימת ב-Storage,
            # לא מייצרים אותה שוב.
            # =========================================

            storage_path = (
                f"unit_lessons/"
                f"{unit_lesson_id}/"
                f"v{content_version}/"
                f"visual_{visual_order}.png"
            )

            try:

                create_lesson_media_signed_url(
                    storage_path
                )

                print(
                    "LESSON VISUAL CACHE HIT:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "order":
                            visual_order,

                        "storage_path":
                            storage_path
                    }
                )

                generated_visuals.append({
                    "order":
                        visual_order,

                    "type":
                        "image",

                    "storage_path":
                        storage_path,

                    "source":
                        "cache"
                })

                continue

            except Exception:

                print(
                    "LESSON VISUAL CACHE MISS:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "order":
                            visual_order,

                        "storage_path":
                            storage_path
                    }
                )

            success = False

            for attempt in range(
                1,
                MAX_VISUAL_RETRIES + 1
            ):

                try:

                    print(
                        "LESSON VISUAL ATTEMPT:",
                        {
                            "unit_lesson_id":
                                unit_lesson_id,

                            "order":
                                visual_order,

                            "attempt":
                                attempt,

                            "max_attempts":
                                MAX_VISUAL_RETRIES
                        }
                    )

                    result = (
                        generate_and_store_lesson_visual_image(
                            unit_lesson_id=
                            unit_lesson_id,

                            content_version=
                            content_version,

                            visual=
                            visual,

                            reference_image_bytes=(
                                master_reference_bytes
                                if int(visual_order or 0) > 1
                                else None
                            ),

                            reference_mime_type=
                            master_reference_mime_type
                        )
                    )

                    generated_visuals.append(
                        result
                    )

                    success = True

                    print(
                        "LESSON VISUAL SUCCESS:",
                        {
                            "unit_lesson_id":
                                unit_lesson_id,

                            "order":
                                visual_order,

                            "attempt":
                                attempt
                        }
                    )

                    break

                except Exception as visual_error:

                    print(
                        "LESSON VISUAL ATTEMPT FAILED:",
                        {
                            "unit_lesson_id":
                                unit_lesson_id,

                            "order":
                                visual_order,

                            "attempt":
                                attempt,

                            "max_attempts":
                                MAX_VISUAL_RETRIES,

                            "error":
                                repr(
                                    visual_error
                                )
                        }
                    )

                    traceback.print_exc()

                    if (
                        attempt
                        <
                        MAX_VISUAL_RETRIES
                    ):

                        delay = (
                            RETRY_DELAY_SECONDS
                            * attempt
                        )

                        print(
                            "LESSON VISUAL RETRYING:",
                            {
                                "unit_lesson_id":
                                    unit_lesson_id,

                                "order":
                                    visual_order,

                                "retry_in_seconds":
                                    delay
                            }
                        )

                        time.sleep(
                            delay
                        )

            if not success:

                print(
                    "LESSON VISUAL PRIMARY PROMPT FAILED:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "order":
                            visual_order,

                        "attempts":
                            MAX_VISUAL_RETRIES
                    }
                )

                # =====================================
                # FALLBACK PROMPT
                #
                # אסור להשאיר Segment בלי תמונה.
                # אם ה-Prompt של Visual Director נכשל,
                # מייצרים Prompt פשוט ובטוח יותר
                # מתוך ה-source_text עצמו.
                # =====================================

                source_text = str(
                    visual.get(
                        "source_text"
                    )
                    or ""
                ).strip()

                parent_lesson = (
                    get_learning_lesson(
                        unit_lesson[
                            "learning_lesson_id"
                        ]
                    )
                )

                fallback_prompt = (
                    build_segment_visual_fallback_prompt(
                        unit_lesson=
                            unit_lesson,

                        parent_lesson=
                            parent_lesson,

                        segment_text=
                            source_text,

                        segment_index=
                            int(
                                visual_order
                            )
                    )
                )

                fallback_visual = {
                    **visual,

                    "type":
                        "image",

                    "generation_prompt":
                        fallback_prompt
                }

                try:

                    print(
                        "LESSON VISUAL FALLBACK START:",
                        {
                            "unit_lesson_id":
                                unit_lesson_id,

                            "order":
                                visual_order
                        }
                    )

                    result = (
                        generate_and_store_lesson_visual_image(
                            unit_lesson_id=
                                unit_lesson_id,

                            content_version=
                                content_version,

                            visual=
                                fallback_visual
                        )
                    )

                    generated_visuals.append(
                        result
                    )

                    success = True

                    print(
                        "LESSON VISUAL FALLBACK SUCCESS:",
                        {
                            "unit_lesson_id":
                                unit_lesson_id,

                            "order":
                                visual_order
                        }
                    )

                except Exception as fallback_error:

                    print(
                        "LESSON VISUAL FALLBACK FAILED:",
                        {
                            "unit_lesson_id":
                                unit_lesson_id,

                            "order":
                                visual_order,

                            "error":
                                repr(
                                    fallback_error
                                )
                        }
                    )

                    traceback.print_exc()

        print(
            "ALL LESSON VISUALS READY:",
            {
                "unit_lesson_id":
                    unit_lesson_id,

                "planned_count":
                    len(image_visuals),

                "generated_count":
                    len(generated_visuals),

                "visuals":
                    generated_visuals
            }
        )

    except Exception as e:

        print(
            "ALL LESSON VISUALS ERROR:",
            {
                "unit_lesson_id":
                    unit_lesson_id,

                "error":
                    repr(e)
            }
        )

        traceback.print_exc()

def generate_unit_lesson_media_background(
        unit_lesson_id: int
):
    print(
        "========== LESSON MEDIA BACKGROUND START ==========",
        {
            "unit_lesson_id":
                unit_lesson_id
        }
    )

    with ThreadPoolExecutor(
            max_workers=2
    ) as executor:

        audio_future = executor.submit(
            generate_unit_lesson_audio_background,
            unit_lesson_id
        )

        visuals_future = executor.submit(
            generate_all_lesson_visuals_background,
            unit_lesson_id
        )

        try:
            visuals_future.result()

        except Exception as e:
            print(
                "LESSON VISUALS BACKGROUND FAILED:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "error":
                        repr(e)
                }
            )

            traceback.print_exc()

        try:
            audio_future.result()

        except Exception as e:
            print(
                "LESSON AUDIO BACKGROUND FAILED:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "error":
                        repr(e)
                }
            )

            traceback.print_exc()

    print(
        "========== LESSON MEDIA BACKGROUND DONE ==========",
        {
            "unit_lesson_id":
                unit_lesson_id
        }
    )

def generate_first_lesson_visual_background(
        unit_lesson_id: int
):
    try:

        unit_lesson = get_unit_lesson(
            unit_lesson_id
        )

        generated_lesson_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
            or {}
        )

        visual_plan = (
            generated_lesson_json.get(
                "visual_plan"
            )
            or {}
        )

        visuals = (
            visual_plan.get(
                "visuals"
            )
            or []
        )

        content_version = int(
            unit_lesson.get(
                "content_version"
            )
            or 1
        )

        first_image = None

        for visual in visuals:

            if not isinstance(
                    visual,
                    dict
            ):
                continue

            if (
                visual.get("type")
                == "image"
            ):
                first_image = visual
                break

        if not first_image:

            print(
                "NO IMAGE FOUND IN VISUAL PLAN:",
                unit_lesson_id
            )

            return

        result = (
            generate_and_store_lesson_visual_image(
                unit_lesson_id=
                    unit_lesson_id,

                content_version=
                    content_version,

                visual=
                    first_image
            )
        )

        print(
            "FIRST LESSON VISUAL READY:",
            result
        )

    except Exception as e:

        print(
            "FIRST LESSON VISUAL ERROR:",
            {
                "unit_lesson_id":
                    unit_lesson_id,

                "error":
                    repr(e)
            }
        )

        traceback.print_exc()

def add_signed_urls_to_lesson_audio(
        lesson_audio_json: dict | None
) -> dict | None:

    if not isinstance(
            lesson_audio_json,
            dict
    ):
        return None

    bucket = (
        lesson_audio_json.get(
            "bucket"
        )
        or LESSON_AUDIO_BUCKET
    )

    raw_segments = (
        lesson_audio_json.get(
            "segments"
        )
        or []
    )

    signed_segments = []

    for segment in raw_segments:

        if not isinstance(
                segment,
                dict
        ):
            continue

        path = str(
            segment.get(
                "path"
            )
            or ""
        ).strip()

        if not path:
            continue

        signed_response = (
            sb.storage
            .from_(
                bucket
            )
            .create_signed_url(
                path,
                LESSON_AUDIO_URL_EXPIRY_SECONDS
            )
        )

        signed_url = None

        if isinstance(
                signed_response,
                dict
        ):
            signed_url = (
                signed_response.get(
                    "signedURL"
                )
                or signed_response.get(
                    "signedUrl"
                )
                or signed_response.get(
                    "signed_url"
                )
            )

        if not signed_url:
            raise RuntimeError(
                f"Failed to create signed URL for {path}"
            )

        signed_segments.append({
            **segment,
            "url": signed_url
        })

    raw_question = (
        lesson_audio_json.get(
            "question"
        )
    )

    signed_question = None

    if isinstance(
            raw_question,
            dict
    ):

        question_path = str(
            raw_question.get(
                "path"
            )
            or ""
        ).strip()

        if question_path:

            signed_response = (
                sb.storage
                .from_(
                    bucket
                )
                .create_signed_url(
                    question_path,
                    LESSON_AUDIO_URL_EXPIRY_SECONDS
                )
            )

            signed_url = None

            if isinstance(
                    signed_response,
                    dict
            ):
                signed_url = (
                    signed_response.get(
                        "signedURL"
                    )
                    or signed_response.get(
                        "signedUrl"
                    )
                    or signed_response.get(
                        "signed_url"
                    )
                )

            if not signed_url:
                raise RuntimeError(
                    "Failed to create signed URL "
                    "for lesson question"
                )

            signed_question = {
                **raw_question,
                "url": signed_url
            }

    return {
        **lesson_audio_json,
        "segments":
            signed_segments,
        "question":
            signed_question,
        "url_expires_in_seconds":
            LESSON_AUDIO_URL_EXPIRY_SECONDS
    }

def generate_tts_wav_bytes(
        text: str
) -> tuple[bytes, float]:

    clean_text = str(
        text or ""
    ).strip()

    if not clean_text:
        raise RuntimeError(
            "Cannot generate audio for empty text"
        )

    response = gemini_client.models.generate_content(
        model="gemini-3.1-flash-tts-preview",

        contents=(
            "Speak in natural, fluent Hebrew. "
            "Sound like a warm, friendly and patient teacher "
            "speaking naturally to a school-age child. "
            "Use clear pronunciation and natural pauses. "
            "Read exactly the following Hebrew text:\n\n"
            + clean_text
        ),

        config=types.GenerateContentConfig(
            temperature=2.0,

            response_modalities=[
                "AUDIO"
            ],

            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=
                    types.PrebuiltVoiceConfig(
                        voice_name="Aoede"
                    )
                )
            )
        )
    )

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

    duration_seconds = (
        len(audio_data)
        / (24000 * 2)
    )

    wav_buffer = io.BytesIO()

    with wave.open(
            wav_buffer,
            "wb"
    ) as wav_file:

        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(audio_data)

    return (
        wav_buffer.getvalue(),
        duration_seconds
    )


def generate_and_store_lesson_audio(
        unit_lesson_id: int,
        structured_lesson: dict,
        content_version: int
) -> dict:

    lesson_segments = (
        structured_lesson.get("lesson")
        or []
    )

    question_data = (
        structured_lesson.get("question")
        or {}
    )

    stored_segments = []

    total_duration_seconds = 0.0

    # =============================================
    # LESSON SEGMENTS
    # =============================================

    for index, segment in enumerate(
            lesson_segments,
            start=1
    ):

        segment_text = str(
            segment.get("text")
            or ""
        ).strip()

        if not segment_text:
            continue

        print(
            "BACKGROUND TTS SEGMENT START:",
            {
                "unit_lesson_id": unit_lesson_id,
                "segment_index": index,
                "text_length": len(segment_text),
                "text": repr(segment_text)
            }
        )

        try:
            wav_bytes, duration_seconds = (
                generate_tts_wav_bytes(
                    segment_text
                )
            )

            print(
                "BACKGROUND TTS SEGMENT SUCCESS:",
                {
                    "unit_lesson_id": unit_lesson_id,
                    "segment_index": index,
                    "duration_seconds": duration_seconds
                }
            )

        except Exception as e:
            print(
                "BACKGROUND TTS SEGMENT FAILED:",
                {
                    "unit_lesson_id": unit_lesson_id,
                    "segment_index": index,
                    "text_length": len(segment_text),
                    "text": repr(segment_text),
                    "error": repr(e)
                }
            )
            raise

        storage_path = (
            f"unit_lessons/"
            f"{unit_lesson_id}/"
            f"v{content_version}/"
            f"segment_{index}.wav"
        )

        sb.storage.from_(
            LESSON_AUDIO_BUCKET
        ).upload(
            path=storage_path,
            file=wav_bytes,
            file_options={
                "content-type": "audio/wav",
                "upsert": "true"
            }
        )

        stored_segments.append({
            "index":
                index,

            "path":
                storage_path,

            "duration_seconds":
                round(
                    duration_seconds,
                    2
                )
        })

        total_duration_seconds += (
            duration_seconds
        )

    # =============================================
    # FINAL QUESTION
    # =============================================

    stored_question = None

    question_text = str(
        question_data.get("text")
        or ""
    ).strip()

    if question_text:

        print(
            "BACKGROUND TTS QUESTION START:",
            {
                "unit_lesson_id": unit_lesson_id,
                "text_length": len(question_text),
                "text": repr(question_text)
            }
        )

        try:
            wav_bytes, duration_seconds = (
                generate_tts_wav_bytes(
                    question_text
                )
            )

            print(
                "BACKGROUND TTS QUESTION SUCCESS:",
                {
                    "unit_lesson_id": unit_lesson_id,
                    "duration_seconds": duration_seconds
                }
            )

        except Exception as e:
            print(
                "BACKGROUND TTS QUESTION FAILED:",
                {
                    "unit_lesson_id": unit_lesson_id,
                    "text_length": len(question_text),
                    "text": repr(question_text),
                    "error": repr(e)
                }
            )
            raise

        question_path = (
            f"unit_lessons/"
            f"{unit_lesson_id}/"
            f"v{content_version}/"
            f"question.wav"
        )

        sb.storage.from_(
            LESSON_AUDIO_BUCKET
        ).upload(
            path=question_path,
            file=wav_bytes,
            file_options={
                "content-type": "audio/wav",
                "upsert": "true"
            }
        )

        stored_question = {
            "path":
                question_path,

            "duration_seconds":
                round(
                    duration_seconds,
                    2
                )
        }

        total_duration_seconds += (
            duration_seconds
        )

    if not stored_segments:
        raise RuntimeError(
            "No lesson audio segments were generated"
        )

    return {
        "version":
            content_version,

        "bucket":
            LESSON_AUDIO_BUCKET,

        "segments":
            stored_segments,

        "question":
            stored_question,

        "total_duration_seconds":
            round(
                total_duration_seconds,
                2
            )
    }
def generate_unit_lesson_audio_background(
        unit_lesson_id: int
):
    """
    יצירת אודיו לשיעור ברקע.

    הפונקציה אינה תלויה ב-request של המשתמש.
    היא שולפת את השיעור מהמסד,
    יוצרת קבצי WAV,
    מעלה אותם ל-Storage
    ומעדכנת את סטטוס האודיו.
    """

    try:

        # =============================================
        # LOAD LESSON
        # =============================================

        unit_lesson = get_unit_lesson(
            unit_lesson_id
        )

        generation_status = (
            unit_lesson.get(
                "generation_status"
            )
            or "empty"
        )

        audio_generation_status = (
            unit_lesson.get(
                "audio_generation_status"
            )
            or "pending"
        )

        cached_audio = (
            unit_lesson.get(
                "lesson_audio_json"
            )
        )

        generated_lesson_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
        )

        # =============================================
        # CONTENT MUST BE READY
        # =============================================

        if generation_status != "ready":
            print(
                "BACKGROUND AUDIO SKIPPED: "
                "lesson content is not ready:",
                unit_lesson_id
            )
            return

        if not isinstance(
                generated_lesson_json,
                dict
        ):
            print(
                "BACKGROUND AUDIO SKIPPED: "
                "generated lesson JSON is missing:",
                unit_lesson_id
            )
            return

        structured_lesson = (
            generated_lesson_json.get(
                "structured_lesson"
            )
        )

        if not isinstance(
                structured_lesson,
                dict
        ):
            print(
                "BACKGROUND AUDIO SKIPPED: "
                "structured lesson is missing:",
                unit_lesson_id
            )
            return

        # =============================================
        # ALREADY READY
        # =============================================

        if (
                audio_generation_status == "ready"
                and isinstance(
                    cached_audio,
                    dict
                )
                and cached_audio.get(
                    "segments"
                )
        ):
            print(
                "BACKGROUND AUDIO ALREADY READY:",
                unit_lesson_id
            )
            return

        # =============================================
        # ALREADY GENERATING
        # =============================================

        if audio_generation_status == "generating":
            print(
                "BACKGROUND AUDIO ALREADY GENERATING:",
                unit_lesson_id
            )
            return

        # =============================================
        # MARK AS GENERATING
        # =============================================

        audio_started_at = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        sb.table(
            "lesson_units_content"
        ).update({

            "audio_generation_status":
                "generating",

            "audio_generation_error":
                None,

            "updated_at":
                audio_started_at

        }).eq(
            "id",
            unit_lesson_id
        ).execute()

        print(
            "BACKGROUND AUDIO STARTED:",
            unit_lesson_id
        )

        # =============================================
        # GENERATE AUDIO
        # =============================================

        content_version = int(
            unit_lesson.get(
                "content_version"
            )
            or 1
        )

        lesson_audio_json = (
            generate_and_store_lesson_audio(

                unit_lesson_id=
                    unit_lesson_id,

                structured_lesson=
                    structured_lesson,

                content_version=
                    content_version
            )
        )

        audio_generated_at = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        # =============================================
        # SAVE RESULT
        # =============================================

        sb.table(
            "lesson_units_content"
        ).update({

            "lesson_audio_json":
                lesson_audio_json,

            "audio_generation_status":
                "ready",

            "audio_generation_error":
                None,

            "audio_generated_at":
                audio_generated_at,

            "tts_generated_at":
                audio_generated_at,

            "updated_at":
                audio_generated_at

        }).eq(
            "id",
            unit_lesson_id
        ).execute()

        print(
            "BACKGROUND AUDIO READY:",
            unit_lesson_id
        )

    except Exception as e:

        error_message = repr(e)

        print(
            "BACKGROUND AUDIO ERROR:",
            unit_lesson_id,
            error_message
        )

        try:

            sb.table(
                "lesson_units_content"
            ).update({

                "audio_generation_status":
                    "failed",

                "audio_generation_error":
                    str(e)[:1500],

                "updated_at":
                    datetime
                    .now(timezone.utc)
                    .isoformat()

            }).eq(
                "id",
                unit_lesson_id
            ).execute()

        except Exception as update_error:

            print(
                "BACKGROUND AUDIO FAILURE "
                "UPDATE ERROR:",
                repr(update_error)
            )
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
        print(
            "LIVE TTS REQUEST:",
            {
                "session_id": body.session_id,
                "text_length": len(text),
                "text": repr(text)
            }
        )
        # =============================================
        # GEMINI TTS DEBUG
        # =============================================

        tts_started_at = time.perf_counter()

        print(
            "========== LIVE TTS GEMINI START ==========",
            {
                "session_id": body.session_id,
                "text_length": len(text),
                "text": repr(text)
            }
        )

        try:

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
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=
                            types.PrebuiltVoiceConfig(
                                voice_name="Aoede"
                            )
                        )
                    )
                )
            )

            print(
                "========== LIVE TTS GEMINI SUCCESS ==========",
                {
                    "session_id": body.session_id,
                    "elapsed_ms": round(
                        (
                            time.perf_counter()
                            - tts_started_at
                        )
                        * 1000
                    )
                }
            )

        except Exception as gemini_error:

            print(
                "========== LIVE TTS GEMINI FAILED ==========",
                {
                    "session_id": body.session_id,
                    "text_length": len(text),
                    "text": repr(text),
                    "elapsed_ms": round(
                        (
                            time.perf_counter()
                            - tts_started_at
                        )
                        * 1000
                    ),
                    "error_type":
                        type(gemini_error).__name__,
                    "error":
                        repr(gemini_error)
                }
            )

            traceback.print_exc()

            raise

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

            try:

                update_tutor_session_after_tts(
                    session_id=
                    body.session_id,

                    audio_duration_seconds=
                    audio_duration_seconds,

                    cost_usd=
                    gemini_audio_cost_usd
                )

                increment_usage_summary(
                    user_id=
                    user.id,

                    tts_calls=
                    1,

                    tts_seconds=
                    audio_duration_seconds,

                    voice_output_seconds=
                    audio_duration_seconds,

                    gemini_cost_usd=
                    gemini_audio_cost_usd
                )

            except Exception as usage_error:

                # =========================================
                # IMPORTANT:
                # האודיו כבר נוצר בהצלחה.
                # תקלה זמנית ב-Supabase/Usage
                # לא מפילה את ה-TTS לילד.
                # =========================================

                print(
                    "TTS USAGE UPDATE FAILED - AUDIO STILL RETURNED:",
                    {
                        "session_id":
                            body.session_id,

                        "error":
                            repr(
                                usage_error
                            )
                    }
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
            "GEMINI TTS ENDPOINT ERROR:",
            {
                "error_type":
                    type(e).__name__,

                "error":
                    error_message,

                "session_id":
                    body.session_id,

                "text_length":
                    len(
                        (
                            body.text
                            or ""
                        ).strip()
                    )
            }
        )
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=(
                "Gemini TTS failed: "
                f"{error_message}"
            )
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
    "/api/tutor/active-lesson-state"
)
def get_active_lesson_state(
        body: ActiveLessonStateRequest,
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
        # ACTIVE LEARNING COACH SESSION
        #
        # קודם מחפשים Coach פעיל.
        # כך לא משחזרים בטעות שיעור ישן אחר.
        # =============================================

        coach_res = (
            sb.table(
                "learning_coach_sessions"
            )
            .select(
                "id, "
                "kid_id, "
                "lesson_id, "
                "unit_lesson_id, "
                "coach_index, "
                "status, "
                "total_rounds, "
                "final_understanding_score, "
                "started_at"
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "status",
                "active"
            )
            .order(
                "started_at",
                desc=True
            )
            .limit(1)
            .execute()
        )

        if not coach_res.data:
            return {
                "has_active_lesson": False
            }

        coach_session = (
            coach_res.data[0]
        )

        # =============================================
        # LESSON PROGRESS
        # =============================================

        progress_res = (
            sb.table(
                "kid_lesson_progress"
            )
            .select(
                "id, "
                "kid_id, "
                "lesson_id, "
                "current_stage, "
                "status, "
                "progress_percent, "
                "mastery_score, "
                "last_activity_at"
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "lesson_id",
                coach_session["lesson_id"]
            )
            .limit(1)
            .execute()
        )

        if not progress_res.data:
            return {
                "has_active_lesson": False
            }

        progress = (
            progress_res.data[0]
        )

        # =============================================
        # LAST ASSISTANT MESSAGE
        # =============================================

        last_message_res = (
            sb.table(
                "kid_lesson_history"
            )
            .select(
                "id, "
                "content, "
                "sequence_json, "
                "created_at"
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "lesson_id",
                coach_session["lesson_id"]
            )
            .eq(
                "role",
                "assistant"
            )
            .order(
                "created_at",
                desc=True
            )
            .limit(1)
            .execute()
        )

        last_assistant_message = (
            last_message_res.data[0]
            if last_message_res.data
            else None
        )

        # =============================================
        # UNIT LESSON DETAILS
        # =============================================

        unit_lesson = get_unit_lesson(
            coach_session[
                "unit_lesson_id"
            ]
        )

        # =============================================
        # PARENT LESSON DETAILS
        # =============================================

        parent_lesson = get_learning_lesson(
            coach_session[
                "lesson_id"
            ]
        )

        return {
            "has_active_lesson": True,

            "progress_id":
                progress["id"],

            "lesson_id":
                progress["lesson_id"],

            "unit_lesson_id":
                coach_session[
                    "unit_lesson_id"
                ],

            "current_stage":
                progress.get(
                    "current_stage"
                ),

            "lesson_status":
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

            "parent_lesson": {
                "id":
                    parent_lesson.get(
                        "id"
                    ),

                "lesson_name":
                    parent_lesson.get(
                        "lesson_name"
                    ),

                "subject":
                    parent_lesson.get(
                        "subject"
                    ),

                "category":
                    parent_lesson.get(
                        "category"
                    )
            },

            "unit_lesson": {
                "id":
                    unit_lesson.get(
                        "id"
                    ),

                "unit_order":
                    unit_lesson.get(
                        "unit_order"
                    ),

                "unit_name":
                    unit_lesson.get(
                        "unit_name"
                    ),

                "lesson_order":
                    unit_lesson.get(
                        "lesson_order"
                    ),

                "lesson_name":
                    unit_lesson.get(
                        "lesson_name"
                    )
            },

            "learning_coach": {
                "session_id":
                    coach_session.get(
                        "id"
                    ),

                "coach_index":
                    coach_session.get(
                        "coach_index"
                    ),

                "status":
                    coach_session.get(
                        "status"
                    ),

                "total_rounds":
                    coach_session.get(
                        "total_rounds"
                    ),

                "understanding_score":
                    coach_session.get(
                        "final_understanding_score"
                    )
            },

            "last_assistant_message": {
                "content":
                    (
                        last_assistant_message.get(
                            "content"
                        )
                        if last_assistant_message
                        else None
                    ),

                "sequence":
                    (
                        last_assistant_message.get(
                            "sequence_json"
                        )
                        if last_assistant_message
                        else None
                    )
            }
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "ACTIVE LESSON STATE ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load "
                "active lesson state"
            )
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
        # TUTOR SESSION
        # =============================================

        tutor_session = get_or_create_tutor_session(
            user_id=user.id,
            kid_id=child["id"]
        )

        session_id = tutor_session["id"]
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
                    ),

                    title=step.get(
                        "title"
                    ),

                    items=step.get(
                        "items"
                    ),

                    icon=step.get(
                        "icon"
                    )
                )
            )

        # =============================================
        # GUARANTEE PERSONAL GREETING FIRST
        # =============================================

        child_name = str(
            child.get("child_name")
            or ""
        ).strip()

        if child_name:
            greeting_text = (
                f"היי {child_name}! "
                f"כיף שבאת ללמוד איתי."
            )

            sequence.insert(
                0,
                TutorAction(
                    type="speak",
                    text=greeting_text,
                    speech_tts=greeting_text
                )
            )

        return {
            "success": True,

            "session_id":
                session_id,

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
        background_tasks: BackgroundTasks,
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
        audio_generation_status = (
                unit_lesson.get(
                    "audio_generation_status"
                )
                or "pending"
        )

        cached_audio = (
            unit_lesson.get(
                "lesson_audio_json"
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
                and isinstance(
                    cached_json.get(
                        "structured_lesson"
                    ),
                    dict
                )
                and cached_json.get(
                    "structured_lesson",
                    {}
                ).get(
                    "lesson"
                )
        ):

            # =========================================
            # REPAIR OLD CACHED LESSON WITHOUT VISUAL PLAN
            # =========================================

            cached_visual_plan = (
                    cached_json.get("visual_plan")
                    or {}
            )

            cached_visuals = (
                    cached_visual_plan.get("visuals")
                    or []
            )

            if not cached_visuals:

                print(
                    "CACHED LESSON MISSING VISUAL PLAN:",
                    {
                        "unit_lesson_id":
                            unit_lesson["id"]
                    }
                )

                structured_lesson = (
                        cached_json.get(
                            "structured_lesson"
                        )
                        or {}
                )

                lesson_text = str(
                    cached_json.get("lesson")
                    or ""
                ).strip()

                visual_director_prompt = (
                    build_visual_director_prompt(
                        unit_lesson=
                        unit_lesson,

                        parent_lesson=
                        parent_lesson,

                        lesson_text=
                        lesson_text,

                        structured_lesson=
                        structured_lesson
                    )
                )

                visual_director_completion = (
                    client
                    .beta
                    .chat
                    .completions
                    .parse(

                        model=
                        DEFAULT_OPENAI_MODEL,

                        messages=[
                            {
                                "role":
                                    "system",

                                "content":
                                    visual_director_prompt
                            },
                            {
                                "role":
                                    "user",

                                "content":
                                    (
                                        "Analyze the lesson and create "
                                        "the visual media plan. "
                                        "Return only the required structure."
                                    )
                            }
                        ],

                        response_format=
                        VisualDirectorResponse
                    )
                )

                visual_director_data = (
                    visual_director_completion
                    .choices[0]
                    .message
                    .parsed
                )

                if visual_director_data:
                    repaired_visual_plan = (
                        normalize_visual_plan_to_segments(
                            visual_plan=
                            visual_director_data.model_dump(),

                            structured_lesson=
                            structured_lesson,

                            unit_lesson=
                            unit_lesson,

                            parent_lesson=
                            parent_lesson
                        )
                    )

                    cached_json[
                        "visual_plan"
                    ] = repaired_visual_plan

                    sb.table(
                        "lesson_units_content"
                    ).update({

                        "generated_lesson_json":
                            cached_json,

                        "updated_at":
                            datetime
                            .now(timezone.utc)
                            .isoformat()

                    }).eq(
                        "id",
                        unit_lesson["id"]
                    ).execute()

                    print(
                        "CACHED VISUAL PLAN REPAIRED:",
                        {
                            "unit_lesson_id":
                                unit_lesson["id"],

                            "visuals_count":
                                len(
                                    repaired_visual_plan
                                    .get("visuals")
                                    or []
                                )
                        }
                    )

            response_audio = None

            # =========================================
            # TRY STORED AUDIO
            #
            # חשוב:
            # ייתכן שב-DB האודיו מסומן ready,
            # אבל הקבצים עצמם נמחקו מה-Storage.
            #
            # מצב כזה הוא CACHE MISS של המדיה בלבד.
            # אסור להפיל בגללו את כל השיעור.
            # =========================================

            if (
                    audio_generation_status == "ready"
                    and isinstance(
                        cached_audio,
                        dict
                    )
                    and cached_audio.get(
                        "segments"
                    )
            ):

                try:

                    response_audio = (
                        add_signed_urls_to_lesson_audio(
                            cached_audio
                        )
                    )

                    print(
                        "UNIT LESSON AUDIO CACHE HIT:",
                        {
                            "unit_lesson_id":
                                unit_lesson["id"]
                        }
                    )

                except Exception as audio_cache_error:

                    print(
                        "UNIT LESSON AUDIO CACHE MISS:",
                        {
                            "unit_lesson_id":
                                unit_lesson["id"],

                            "error":
                                repr(
                                    audio_cache_error
                                )
                        }
                    )

                    # ---------------------------------
                    # ה-DB מצביע על קבצים שכבר אינם
                    # קיימים ב-Storage.
                    #
                    # מאפסים רק את האודיו,
                    # לא את תוכן השיעור.
                    # ---------------------------------

                    audio_generation_status = (
                        "pending"
                    )

                    cached_audio = None

                    sb.table(
                        "lesson_units_content"
                    ).update({

                        "audio_generation_status":
                            "pending",

                        "lesson_audio_json":
                            None,

                        "audio_generation_error":
                            None,

                        "audio_generated_at":
                            None,

                        "tts_generated_at":
                            None,

                        "updated_at":
                            datetime
                            .now(timezone.utc)
                            .isoformat()

                    }).eq(
                        "id",
                        unit_lesson["id"]
                    ).execute()

            # =========================================
            # BACKGROUND AUDIO REPAIR ONLY
            #
            # אם האודיו כבר קיים ותקין,
            # אין שום סיבה להפעיל מחדש את כל
            # מנגנון המדיה בכל Refresh.
            #
            # זה מונע עשרות קריאות מיותרות
            # ל-Supabase בכל טעינת עמוד.
            # =========================================

            if response_audio is None:

                print(
                    "QUEUE BACKGROUND AUDIO REPAIR:",
                    {
                        "unit_lesson_id":
                            unit_lesson["id"],

                        "audio_generation_status":
                            audio_generation_status
                    }
                )

                background_tasks.add_task(
                    generate_unit_lesson_audio_background,
                    unit_lesson["id"]
                )

            else:

                print(
                    "SKIP BACKGROUND MEDIA - CACHE COMPLETE:",
                    {
                        "unit_lesson_id":
                            unit_lesson["id"]
                    }
                )

            # =========================================
            # BACKGROUND VISUAL REPAIR
            #
            # גם אם תוכן השיעור נמצא ב-cache,
            # ייתכן שקבצי התמונות נמחקו מה-Storage.
            #
            # הפונקציה עצמה בודקת כל visual:
            # קיים -> CACHE HIT ולא מייצרת מחדש
            # חסר  -> מייצרת מחדש
            # =========================================

            print(
                "QUEUE BACKGROUND VISUAL CHECK:",
                {
                    "unit_lesson_id":
                        unit_lesson["id"]
                }
            )

            background_tasks.add_task(
                generate_all_lesson_visuals_background,
                unit_lesson["id"]
            )

            # =========================================
            # RESPONSE
            # =========================================

            return {

                "success":
                    True,

                "source":
                    "cache",

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

                "lesson":
                    cached_json.get(
                        "lesson"
                    ),

                "structured_lesson":
                    cached_json.get(
                        "structured_lesson"
                    ),

                "audio_generation_status":
                    (
                        "ready"
                        if response_audio
                        else "pending"
                    ),

                "audio_mode":
                    (
                        "stored"
                        if response_audio
                        else "background_generating"
                    ),

                "lesson_audio":
                    response_audio
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

                model=UNIVERSAL_LESSON_MODEL,

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
                                "השיגו במדויק את מטרת הלמידה. "
                                "התאימו את עומק ההסבר "
                                "לרמת המורכבות שהוגדרה. "
                                "אין חובה להשתמש בכל הזמן המקסימלי. "
                                "סיימו כאשר ההסבר ברור ושלם. "
                                "החזירו את רצף הפעולות בלבד "
                                "לפי מבנה התגובה."
                            )
                    }

                ],

                response_format=
                UniversalLessonResponse

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

        lesson_text = lesson_data.lesson.strip()

        # =============================================
        # LESSON DIRECTOR
        # חלוקת השיעור לקטעים והפרדת שאלת הסיום
        # =============================================

        director_prompt = (
            build_lesson_director_prompt(
                lesson_text=lesson_text
            )
        )

        director_completion = (
            client
            .beta
            .chat
            .completions
            .parse(

                model=DEFAULT_OPENAI_MODEL,

                messages=[
                    {
                        "role": "system",
                        "content": director_prompt
                    },
                    {
                        "role": "user",
                        "content": (
                            "ארגן את השיעור לפי ההנחיות "
                            "והחזר JSON בלבד."
                        )
                    }
                ],

                response_format=
                DirectedLessonResponse
            )
        )

        directed_lesson_data = (
            director_completion
            .choices[0]
            .message
            .parsed
        )

        if not directed_lesson_data:
            raise RuntimeError(
                "Lesson director returned no response"
            )

        structured_lesson = (
            directed_lesson_data.model_dump()
        )

        # =============================================
        # BACKWARD COMPATIBILITY
        #
        # הקוד הישן עדיין משתמש ב:
        # structured_lesson["lesson"]
        # structured_lesson["question"]
        #
        # כרגע הם מייצגים את Part 1.
        # =============================================

        structured_lesson[
            "lesson"
        ] = (
                structured_lesson
                .get(
                    "part_1",
                    {}
                )
                .get(
                    "lesson"
                )
                or []
        )

        structured_lesson[
            "question"
        ] = (
                structured_lesson
                .get(
                    "part_1",
                    {}
                )
                .get(
                    "question"
                )
                or {}
        )

        # =============================================
        # LESSON TRANSITION DIRECTOR
        #
        # מעבר אוניברסלי בין Part 1 ל-Part 2.
        # אינו תלוי בדיאלוג של הילד.
        # =============================================

        transition_prompt = (
            build_lesson_transition_prompt(

                unit_lesson=
                unit_lesson,

                parent_lesson=
                parent_lesson,

                part_1=
                structured_lesson[
                    "part_1"
                ],

                part_2=
                structured_lesson[
                    "part_2"
                ]
            )
        )

        print(
            "========== LESSON TRANSITION DIRECTOR START ==========",
            {
                "unit_lesson_id":
                    unit_lesson["id"]
            }
        )

        transition_completion = (
            client
            .beta
            .chat
            .completions
            .parse(

                model=
                DEFAULT_OPENAI_MODEL,

                messages=[
                    {
                        "role":
                            "system",

                        "content":
                            transition_prompt
                    },

                    {
                        "role":
                            "user",

                        "content":
                            (
                                "Create the universal transition "
                                "between Part 1 and Part 2. "
                                "Return only the required structure."
                            )
                    }
                ],

                response_format=
                LessonTransitionResponse
            )
        )

        transition_data = (
            transition_completion
            .choices[0]
            .message
            .parsed
        )

        if not transition_data:
            raise RuntimeError(
                "Lesson Transition Director "
                "returned no response"
            )

        lesson_transition = (
            transition_data
            .model_dump()
        )

        print(
            "========== LESSON TRANSITION DIRECTOR RESULT =========="
        )

        print(
            json.dumps(
                lesson_transition,
                ensure_ascii=False,
                indent=2
            )
        )

        # =============================================
        # VISUAL DIRECTOR
        # מחליט אילו המחשות דרושות לשיעור
        # ומתי להציג תמונה או וידאו
        # =============================================

        visual_director_prompt = (
            build_visual_director_prompt(
                unit_lesson=
                unit_lesson,

                parent_lesson=
                parent_lesson,

                lesson_text=
                lesson_text,

                structured_lesson=
                structured_lesson
            )
        )

        print(
            "========== VISUAL DIRECTOR START ==========",
            {
                "unit_lesson_id":
                    unit_lesson["id"],

                "lesson_name":
                    unit_lesson.get(
                        "lesson_name"
                    ),

                "lesson_text_length":
                    len(
                        lesson_text
                        or ""
                    )
            }
        )

        visual_director_completion = (
            client
            .beta
            .chat
            .completions
            .parse(

                model=
                DEFAULT_OPENAI_MODEL,

                messages=[
                    {
                        "role":
                            "system",

                        "content":
                            visual_director_prompt
                    },

                    {
                        "role":
                            "user",

                        "content":
                            (
                                "Analyze the lesson and create "
                                "the visual media plan. "
                                "Return only the required structure."
                            )
                    }
                ],

                response_format=
                VisualDirectorResponse
            )
        )

        visual_director_data = (
            visual_director_completion
            .choices[0]
            .message
            .parsed
        )

        if not visual_director_data:
            raise RuntimeError(
                "Visual Director returned no response"
            )

        visual_plan = (
            visual_director_data
            .model_dump()
        )

        visual_plan = (
            normalize_visual_plan_to_segments(
                visual_plan=
                visual_plan,

                structured_lesson=
                structured_lesson,

                unit_lesson=
                unit_lesson,

                parent_lesson=
                parent_lesson
            )
        )

        print(
            "========== VISUAL DIRECTOR RESULT =========="
        )

        print(
            json.dumps(
                visual_plan,
                ensure_ascii=False,
                indent=2
            )
        )

        lesson_json = {

            "generation_model":
                UNIVERSAL_LESSON_MODEL,

            "director_model":
                DEFAULT_OPENAI_MODEL,

            "learning_objective":
                unit_lesson.get(
                    "learning_objective"
                ),

            "lesson_complexity":
                unit_lesson.get(
                    "lesson_complexity"
                ),

            "max_duration_seconds":
                unit_lesson.get(
                    "max_duration_seconds"
                ),

            # נשאר זמנית כדי לא לשבור את הפרונט
            "lesson":
                lesson_text,

            # המבנה החדש
            "structured_lesson":
                structured_lesson,

            "transition":
                lesson_transition,

            # תוכנית ההמחשות של Visual Director
            "visual_director_model":
                DEFAULT_OPENAI_MODEL,

            "visual_plan":
                visual_plan
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

            # האודיו החדש עדיין לא מוכן
            "audio_generation_status":
                "pending",

            "lesson_audio_json":
                None,

            "audio_generation_error":
                None,

            "audio_generated_at":
                None,

            "tts_generated_at":
                None,

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

        director_input_tokens = 0
        director_output_tokens = 0
        director_total_tokens = 0

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

        if director_completion.usage:

            director_input_tokens = (
                director_completion
                .usage
                .prompt_tokens
                or 0
            )

            director_output_tokens = (
                director_completion
                .usage
                .completion_tokens
                or 0
            )

            director_total_tokens = (
                director_completion
                .usage
                .total_tokens
                or 0
            )

        openai_cost_usd = calculate_openai_cost(
            model=UNIVERSAL_LESSON_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        director_cost_usd = calculate_openai_cost(
            model=DEFAULT_OPENAI_MODEL,
            input_tokens=director_input_tokens,
            output_tokens=director_output_tokens
        )

        increment_usage_summary(

            user_id=
                user.id,

            ai_calls=
                2,

            input_tokens=(
                input_tokens
                + director_input_tokens
            ),

            output_tokens=(
                output_tokens
                + director_output_tokens
            ),

            total_tokens=(
                total_tokens
                + director_total_tokens
            ),

            openai_cost_usd=(
                openai_cost_usd
                + director_cost_usd
            )

        )
        # =============================================
        # START AUDIO GENERATION IN BACKGROUND
        # =============================================
        print(
            "QUEUE BACKGROUND AUDIO AFTER LESSON GENERATION:",
            {
                "unit_lesson_id": unit_lesson["id"],
                "content_version": content_version,
                "segments_count": len(
                    structured_lesson.get("lesson")
                    or []
                ),
                "has_question": bool(
                    (
                            structured_lesson.get("question")
                            or {}
                    ).get("text")
                )
            }
        )
        background_tasks.add_task(
            generate_unit_lesson_media_background,
            unit_lesson["id"]
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

            "lesson":
                lesson_json.get(
                    "lesson"
                ),

            "structured_lesson":
                lesson_json.get(
                    "structured_lesson"
                ),

            "audio_generation_status":
                "pending",

            "lesson_audio":
                None
        }

    except HTTPException:
        raise

    except Exception as e:

        error_message = repr(e)

        print(
            "UNIT LESSON GENERATION ERROR:",
            error_message
        )
        traceback.print_exc()
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
# UNIT LESSON HERO IMAGE
# =====================================================

@app.post(
    "/api/tutor/unit-lesson/hero-image"
)
def get_or_generate_unit_lesson_hero_image(
        body: UnitLessonRequest,
        authorization: str = Header(None)
):
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 0.7

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

        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )

        # =============================================
        # LOAD LESSON
        # WITH RETRY
        # =============================================

        unit_lesson = None

        for attempt in range(
            1,
            MAX_RETRIES + 1
        ):

            try:

                unit_lesson = get_unit_lesson(
                    body.unit_lesson_id
                )

                break

            except HTTPException:
                raise

            except Exception as e:

                print(
                    "HERO GET UNIT LESSON RETRY:",
                    {
                        "attempt":
                            attempt,
                        "max_attempts":
                            MAX_RETRIES,
                        "error":
                            repr(e)
                    }
                )

                if attempt >= MAX_RETRIES:
                    raise

                time.sleep(
                    RETRY_DELAY_SECONDS
                    * attempt
                )

        # =============================================
        # PARENT LESSON
        # WITH RETRY
        # =============================================

        parent_lesson = None

        for attempt in range(
            1,
            MAX_RETRIES + 1
        ):

            try:

                parent_lesson = get_learning_lesson(
                    unit_lesson[
                        "learning_lesson_id"
                    ]
                )

                break

            except HTTPException:
                raise

            except Exception as e:

                print(
                    "HERO GET PARENT LESSON RETRY:",
                    {
                        "attempt":
                            attempt,
                        "max_attempts":
                            MAX_RETRIES,
                        "error":
                            repr(e)
                    }
                )

                if attempt >= MAX_RETRIES:
                    raise

                time.sleep(
                    RETRY_DELAY_SECONDS
                    * attempt
                )

        # =============================================
        # GRADE SECURITY
        # =============================================

        child_grade = int(
            child.get("age")
            or 0
        )

        lesson_grade = int(
            parent_lesson.get("grade")
            or 0
        )

        if (
            child_grade
            and lesson_grade
            and child_grade != lesson_grade
        ):
            raise HTTPException(
                status_code=403,
                detail="Lesson does not match child grade"
            )

        # =============================================
        # STORAGE PATH
        # =============================================

        storage_path = (
            get_lesson_media_storage_path(
                unit_lesson_id=
                    unit_lesson["id"],
                media_type="hero"
            )
        )

        # =============================================
        # CACHE CHECK
        # WITH RETRY
        # =============================================

        signed_url = None
        last_cache_error = None

        for attempt in range(
            1,
            MAX_RETRIES + 1
        ):

            try:

                signed_url = (
                    create_lesson_media_signed_url(
                        storage_path
                    )
                )

                break

            except Exception as cache_error:

                last_cache_error = cache_error

                print(
                    "LESSON HERO CACHE CHECK RETRY:",
                    {
                        "unit_lesson_id":
                            unit_lesson["id"],
                        "attempt":
                            attempt,
                        "max_attempts":
                            MAX_RETRIES,
                        "error":
                            repr(cache_error)
                    }
                )

                if attempt < MAX_RETRIES:

                    time.sleep(
                        RETRY_DELAY_SECONDS
                        * attempt
                    )

        # =============================================
        # CACHE HIT
        # =============================================

        if signed_url:

            print(
                "LESSON HERO CACHE HIT:",
                {
                    "unit_lesson_id":
                        unit_lesson["id"],
                    "storage_path":
                        storage_path
                }
            )

            return {
                "success": True,
                "source": "cache",
                "unit_lesson_id":
                    unit_lesson["id"],
                "hero_image": {
                    "type": "image",
                    "role": "hero",
                    "storage_path":
                        storage_path,
                    "url":
                        signed_url
                }
            }

        # =============================================
        # CACHE MISS
        # =============================================

        print(
            "LESSON HERO CACHE MISS:",
            {
                "unit_lesson_id":
                    unit_lesson["id"],
                "error":
                    repr(last_cache_error)
            }
        )

        # =============================================
        # GENERATE HERO
        # =============================================

        hero_image = (
            generate_and_store_lesson_hero_image(
                unit_lesson["id"]
            )
        )

        return {
            "success": True,
            "source": "generated",
            "unit_lesson_id":
                unit_lesson["id"],
            "hero_image":
                hero_image
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "UNIT LESSON HERO IMAGE ERROR:",
            repr(e)
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Lesson hero image generation failed"
        )

# =====================================================
# UNIT LESSON VISUALS
# =====================================================

@app.post(
    "/api/tutor/unit-lesson/visuals"
)
def get_unit_lesson_visuals(
        body: UnitLessonRequest,
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

        # מוודאים שהילד שייך למשתמש
        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )

        # =============================================
        # LOAD UNIT LESSON
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
            child.get("age")
            or 0
        )

        lesson_grade = int(
            parent_lesson.get("grade")
            or 0
        )

        if (
                child_grade
                and lesson_grade
                and child_grade != lesson_grade
        ):
            raise HTTPException(
                status_code=403,
                detail="Lesson does not match child grade"
            )

        # =============================================
        # LOAD VISUAL PLAN
        # =============================================

        generated_lesson_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
            or {}
        )

        visual_plan = (
            generated_lesson_json.get(
                "visual_plan"
            )
            or {}
        )

        planned_visuals = (
            visual_plan.get(
                "visuals"
            )
            or []
        )

        content_version = int(
            unit_lesson.get(
                "content_version"
            )
            or 1
        )

        response_visuals = []

        # =============================================
        # BUILD RESPONSE
        # =============================================

        for visual in planned_visuals:

            if not isinstance(
                    visual,
                    dict
            ):
                continue

            visual_type = str(
                visual.get("type")
                or ""
            ).strip().lower()

            # כרגע הפרונט מקבל רק תמונות.
            # וידאו נחבר בשלב הבא.
            if visual_type != "image":
                continue

            visual_order = int(
                visual.get("order")
                or 0
            )

            if not visual_order:
                continue

            storage_path = (
                f"unit_lessons/"
                f"{unit_lesson['id']}/"
                f"v{content_version}/"
                f"visual_{visual_order}.png"
            )

            # -----------------------------------------
            # התמונה יכולה עדיין להיות בתהליך יצירה.
            # במקרה כזה פשוט לא מחזירים אותה עדיין.
            # -----------------------------------------

            try:

                signed_url = (
                    create_lesson_media_signed_url(
                        storage_path
                    )
                )

            except Exception as image_error:

                print(
                    "LESSON VISUAL NOT READY:",
                    {
                        "unit_lesson_id":
                            unit_lesson["id"],

                        "order":
                            visual_order,

                        "storage_path":
                            storage_path,

                        "error":
                            repr(image_error)
                    }
                )

                continue

            response_visuals.append({

                "order":
                    visual_order,

                "type":
                    "image",

                "trigger_text":
                    visual.get(
                        "trigger_text"
                    ),

                "visual_goal":
                    visual.get(
                        "visual_goal"
                    ),

                "source_text":
                    visual.get(
                        "source_text"
                    ),

                "storage_path":
                    storage_path,

                "url":
                    signed_url
            })

        # =============================================
        # RESPONSE
        # =============================================

        print(
            "LESSON VISUALS RESPONSE:",
            {
                "unit_lesson_id":
                    unit_lesson["id"],

                "content_version":
                    content_version,

                "planned_count":
                    len(planned_visuals),

                "ready_count":
                    len(response_visuals)
            }
        )

        return {

            "success":
                True,

            "unit_lesson_id":
                unit_lesson["id"],

            "content_version":
                content_version,

            "visuals":
                response_visuals,

            "visuals_ready":
                len(response_visuals),

            "visuals_planned":
                len([
                    item
                    for item in planned_visuals
                    if isinstance(item, dict)
                    and item.get("type") == "image"
                ])
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "UNIT LESSON VISUALS ERROR:",
            {
                "unit_lesson_id":
                    body.unit_lesson_id,

                "error":
                    repr(e)
            }
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Failed to load lesson visuals"
        )

@app.post(
    "/api/tutor/unit-lesson/audio"
)
def generate_unit_lesson_audio(
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
        # LOAD UNIT LESSON
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
            child.get("age")
            or 0
        )

        lesson_grade = int(
            parent_lesson.get("grade")
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

        generated_lesson_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
        )

        audio_generation_status = (
            unit_lesson.get(
                "audio_generation_status"
            )
            or "pending"
        )

        cached_audio = (
            unit_lesson.get(
                "lesson_audio_json"
            )
        )

        # =============================================
        # LESSON CONTENT MUST EXIST
        # =============================================

        if (
                generation_status != "ready"
                or not isinstance(
                    generated_lesson_json,
                    dict
                )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Lesson content is not ready"
                )
            )

        structured_lesson = (
            generated_lesson_json.get(
                "structured_lesson"
            )
        )

        if not isinstance(
                structured_lesson,
                dict
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Structured lesson is missing"
                )
            )

        # =============================================
        # AUDIO ALREADY READY
        # =============================================

        if (
                audio_generation_status == "ready"
                and isinstance(
                    cached_audio,
                    dict
                )
                and cached_audio.get(
                    "segments"
                )
        ):
            return {
                "success": True,

                "source":
                    "cache",

                "unit_lesson_id":
                    unit_lesson["id"],

                "audio_generation_status":
                    "ready",

                "lesson_audio":
                    add_signed_urls_to_lesson_audio(
                        cached_audio
                    )
            }

        # =============================================
        # AUDIO ALREADY GENERATING
        # =============================================

        if (
                audio_generation_status
                == "generating"
        ):
            return {
                "success": False,

                "source":
                    "generating",

                "unit_lesson_id":
                    unit_lesson["id"],

                "audio_generation_status":
                    "generating",

                "lesson_audio":
                    None
            }

        # =============================================
        # MARK AUDIO AS GENERATING
        # =============================================

        audio_started_at = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        sb.table(
            "lesson_units_content"
        ).update({

            "audio_generation_status":
                "generating",

            "audio_generation_error":
                None,

            "updated_at":
                audio_started_at

        }).eq(
            "id",
            unit_lesson["id"]
        ).execute()

        # =============================================
        # GENERATE AND STORE AUDIO
        # =============================================

        content_version = int(
            unit_lesson.get(
                "content_version"
            )
            or 1
        )

        lesson_audio_json = (
            generate_and_store_lesson_audio(

                unit_lesson_id=
                    unit_lesson["id"],

                structured_lesson=
                    structured_lesson,

                content_version=
                    content_version
            )
        )

        audio_generated_at = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        # =============================================
        # SAVE AUDIO CACHE
        # =============================================

        sb.table(
            "lesson_units_content"
        ).update({

            "lesson_audio_json":
                lesson_audio_json,

            "audio_generation_status":
                "ready",

            "audio_generation_error":
                None,

            "audio_generated_at":
                audio_generated_at,

            "tts_generated_at":
                audio_generated_at,

            "updated_at":
                audio_generated_at

        }).eq(
            "id",
            unit_lesson["id"]
        ).execute()

        return {
            "success": True,

            "source":
                "generated",

            "unit_lesson_id":
                unit_lesson["id"],

            "audio_generation_status":
                "ready",

            "lesson_audio":
                add_signed_urls_to_lesson_audio(
                    lesson_audio_json
                )
        }

    except HTTPException:
        raise

    except Exception as e:

        error_message = repr(e)

        print(
            "UNIT LESSON AUDIO ERROR:",
            error_message
        )

        if unit_lesson:

            try:

                sb.table(
                    "lesson_units_content"
                ).update({

                    "audio_generation_status":
                        "failed",

                    "audio_generation_error":
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
                    "UNIT LESSON AUDIO "
                    "FAILURE UPDATE ERROR:",
                    repr(update_error)
                )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unit lesson audio "
                "generation failed"
            )
        )

# =====================================================
# LEARNING COACH EXECUTION
# =====================================================

def run_learning_coach(
        user,
        child: dict,
        lesson: dict,
        unit_lesson: dict,
        message: str,
        tutor_session: dict,
        session_id: str,
        progress: dict,
        coach_index: int
):
    # =============================================
    # SESSION
    # =============================================

    coach_session = (
        get_or_create_learning_coach_session(
            kid_id=child["id"],
            lesson_id=lesson["id"],
            unit_lesson_id=unit_lesson["id"],
            coach_index=coach_index
        )
    )

    # =============================================
    # HISTORY
    # =============================================

    conversation_history = (
        get_recent_lesson_history_for_llm(
            kid_id=child["id"],
            lesson_id=lesson["id"],
            unit_lesson_id=unit_lesson["id"],
            limit=12
        )
    )

    # =============================================
    # BUILD PROMPT
    # =============================================

    (
        system_prompt,
        runtime_data,
        current_round
    ) = build_learning_coach_prompt(
        child=child,
        parent_lesson=lesson,
        unit_lesson=unit_lesson,
        coach_session=coach_session,
        conversation_history=conversation_history,
        child_answer=message
    )

    # =============================================
    # CONSOLE DEBUG
    # =============================================

    print("\n")
    print("=" * 70)
    print("LEARNING COACH TRIGGERED")
    print("=" * 70)

    print(
        "ROUTING DATA:",
        json.dumps(
            {
                "kid_id":
                    child.get("id"),

                "child_name":
                    child.get("child_name"),

                "grade":
                    child.get("age"),

                "lesson_id":
                    lesson.get("id"),

                "unit_lesson_id":
                    unit_lesson.get("id"),

                "coach_session_id":
                    coach_session.get("id"),

                "coach_index":
                    coach_index,

                "current_round":
                    current_round,

                "maximum_rounds":
                    LEARNING_COACH_MAX_ROUNDS,

                "previous_score":
                    coach_session.get(
                        "final_understanding_score"
                    ),

                "child_answer":
                    message
            },
            ensure_ascii=False,
            indent=2
        )
    )

    print("-" * 70)
    print("LEARNING COACH RUNTIME DATA:")
    print(
        json.dumps(
            runtime_data,
            ensure_ascii=False,
            indent=2
        )
    )

    print("-" * 70)
    print("FINAL LEARNING COACH PROMPT:")
    print(system_prompt)
    print("=" * 70)

    # =============================================
    # OPENAI
    # =============================================

    completion = (
        client
        .beta
        .chat
        .completions
        .parse(
            model=DEFAULT_OPENAI_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": message
                }
            ],

            response_format=
                LearningCoachAIResponse
        )
    )

    coach_data = (
        completion
        .choices[0]
        .message
        .parsed
    )

    if not coach_data:
        raise RuntimeError(
            "Learning Coach returned no response"
        )

    understanding_score = max(
        0,
        min(
            100,
            int(
                coach_data
                .understanding_score
            )
        )
    )

    goal_achieved = bool(
        coach_data
        .lesson_goal_achieved
    )

    teacher_response = str(
        coach_data
        .teacher_response
        or ""
    ).strip()

    max_rounds_reached = (
        current_round
        >= LEARNING_COACH_MAX_ROUNDS
    )

    coach_finished = (
        goal_achieved
        or max_rounds_reached
    )

    # =============================================
    # UPDATE COACH SESSION
    # =============================================

    updated_coach_session = (
        update_learning_coach_session(
            coach_session=coach_session,
            understanding_score=
                understanding_score,
            goal_achieved=
                goal_achieved,
            current_round=
                current_round
        )
    )

    # =============================================
    # FINISH LEARNING COACH AND LESSON
    # =============================================

    if coach_finished:

        now_iso = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        next_stage = (
            LESSON_STAGE_COMPLETED
        )

        progress_update = (
            sb.table(
                "kid_lesson_progress"
            )
            .update({
                "current_stage":
                    next_stage,

                "status":
                    "completed",

                "progress_percent":
                    100,

                "mastery_score":
                    understanding_score,

                "completed_at":
                    now_iso,

                "last_activity_at":
                    now_iso,

                "updated_at":
                    now_iso
            })
            .eq(
                "id",
                progress["id"]
            )
            .execute()
        )

        if progress_update.data:
            progress = (
                progress_update.data[0]
            )

    else:

        next_stage = (
            progress.get(
                "current_stage"
            )
        )

    print("-" * 70)
    print(
        "LEARNING COACH RESPONSE:",
        json.dumps(
            {
                "understanding_score":
                    understanding_score,

                "lesson_goal_achieved":
                    goal_achieved,

                "teacher_response":
                    teacher_response,

                "coach_finished":
                    coach_finished,

                "status":
                    updated_coach_session.get(
                        "status"
                    )
            },
            ensure_ascii=False,
            indent=2
        )
    )
    print("=" * 70)
    print("\n")

    # =============================================
    # FRONTEND SEQUENCE
    #
    # teacher_response כבר כולל את תגובת המורה
    # ואת השאלה הבאה.
    #
    # לכן אסור לשלוח אותו גם כ-write וגם כ-ask.
    # =============================================

    if coach_finished:

        sequence = [
            TutorAction(
                type="ask",
                text=teacher_response,
                style="normal",
                speed=45
            )
        ]

    else:

        sequence = [
            TutorAction(
                type="ask",
                text=teacher_response,
                style="question",
                speed=45
            )
        ]

    # =============================================
    # SAVE HISTORY
    # =============================================

    save_lesson_history(
        kid_id=child["id"],
        lesson_id=lesson["id"],
        unit_lesson_id=unit_lesson["id"],
        session_id=session_id,
        objective_index=None,
        user_content=message,
        assistant_content=teacher_response,
        evaluation=None,
        sequence_json=[
            action.model_dump()
            for action in sequence
        ]
    )

    # =============================================
    # TOKENS AND COST
    # =============================================

    input_tokens = 0
    output_tokens = 0
    total_tokens = 0

    if completion.usage:
        input_tokens = (
            completion.usage.prompt_tokens
            or 0
        )

        output_tokens = (
            completion.usage.completion_tokens
            or 0
        )

        total_tokens = (
            completion.usage.total_tokens
            or 0
        )

    openai_cost_usd = (
        calculate_openai_cost(
            model=DEFAULT_OPENAI_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
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

        sessions=(
            1
            if tutor_session.get("_is_new")
            else 0
        ),

        ai_calls=1,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        openai_cost_usd=openai_cost_usd
    )

    return {
        "speech":
            teacher_response,

        "sequence": [
            action.model_dump()
            for action in sequence
        ],

        "wait_for_answer":
            not coach_finished,
        "coach_finished":
            coach_finished,

        "lesson_completed":
            coach_finished,
        "session_id":
            session_id,

        "lesson_id":
            lesson["id"],

        "unit_lesson_id":
            unit_lesson["id"],

        "lesson_mode":
            "learning_coach",

        "current_stage":
            progress.get(
                "current_stage"
            ),

        "coach_index":
            coach_index,

        "review_mode":
            False,

        "learning_coach": {
            "session_id":
                updated_coach_session.get(
                    "id"
                ),

            "coach_index":
                coach_index,

            "current_round":
                current_round,

            "maximum_rounds":
                LEARNING_COACH_MAX_ROUNDS,

            "understanding_score":
                understanding_score,

            "lesson_goal_achieved":
                goal_achieved,

            "status":
                updated_coach_session.get(
                    "status"
                ),

            "finished":
                coach_finished
        }
    }
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
                is_lesson_start,

                unit_lesson_id=
                body.unit_lesson_id

            )

        )
        # =============================================
        # UNIT LESSON SWITCH
        #
        # kid_lesson_progress הוא ברמת הנושא הראשי,
        # ולכן חייבים לזהות מעבר לשיעור פנימי חדש.
        # =============================================

        requested_unit_lesson_id = (
            int(body.unit_lesson_id)
            if body.unit_lesson_id
            else None
        )

        stored_unit_lesson_id = (
            int(
                progress.get(
                    "current_unit_lesson_id"
                )
                or 0
            )
            or None
        )

        is_new_unit_lesson = (
            requested_unit_lesson_id is not None
            and requested_unit_lesson_id
            != stored_unit_lesson_id
        )

        if is_new_unit_lesson:

            now_iso = (
                datetime
                .now(timezone.utc)
                .isoformat()
            )

            progress_update = (
                sb.table(
                    "kid_lesson_progress"
                )
                .update({
                    # תת־השיעור החדש
                    "current_unit_lesson_id":
                        requested_unit_lesson_id,

                    # מתחילים זרימה חדשה
                    "current_stage":
                        LESSON_STAGE_INTRO,

                    "current_flow_step":
                        0,

                    "flow_state":
                        {},

                    "status":
                        "in_progress",

                    # מאפסים את תוצאת תת־השיעור הקודם
                    "progress_percent":
                        0,

                    "mastery_score":
                        0,

                    "current_objective_index":
                        1,

                    "total_interactions":
                        0,

                    "hints_used":
                        0,

                    "consecutive_successes":
                        0,

                    "consecutive_failures":
                        0,

                    "last_evaluation":
                        None,

                    "last_error_type":
                        None,

                    "completed_at":
                        None,

                    "last_activity_at":
                        now_iso,

                    "updated_at":
                        now_iso
                })
                .eq(
                    "id",
                    progress["id"]
                )
                .execute()
            )

            if not progress_update.data:
                raise RuntimeError(
                    "Failed to switch unit lesson"
                )

            progress = progress_update.data[0]

            print(
                "UNIT LESSON PROGRESS SWITCHED:",
                {
                    "kid_id":
                        child["id"],

                    "lesson_id":
                        lesson["id"],

                    "previous_unit_lesson_id":
                        stored_unit_lesson_id,

                    "current_unit_lesson_id":
                        requested_unit_lesson_id,

                    "current_stage":
                        progress.get(
                            "current_stage"
                        ),

                    "status":
                        progress.get(
                            "status"
                        )
                }
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

            and

            not is_new_unit_lesson
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
        # UNIVERSAL LESSON STAGE ROUTER
        # =============================================

        is_real_student_answer = (
                not is_lesson_start
                and not is_no_response
                and not review_mode
        )

        current_stage = (
                progress.get(
                    "current_stage"
                )
                or LESSON_STAGE_INTRO
        )

        if is_real_student_answer:
            if (
                    current_stage
                    == LESSON_STAGE_COMPLETED
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Lesson is already completed"
                )

            if not body.unit_lesson_id:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "unit_lesson_id is required "
                        "for Universal Lesson"
                    )
                )

            unit_lesson = get_unit_lesson(
                body.unit_lesson_id
            )

            if (
                    int(
                        unit_lesson.get(
                            "learning_lesson_id"
                        )
                        or 0
                    )
                    !=
                    int(
                        lesson.get("id")
                        or 0
                    )
            ):
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Unit lesson does not belong "
                        "to the selected lesson"
                    )
                )

            # =========================================
            # FIRST QUESTION -> LEARNING COACH 1
            # =========================================

            if current_stage in (
                    LESSON_STAGE_INTRO,
                    LESSON_STAGE_FIRST_EXPLANATION,
                    LESSON_STAGE_FIRST_QUESTION
            ):
                progress = update_lesson_stage(
                    progress=progress,
                    current_stage=
                    LESSON_STAGE_LEARNING_COACH_1
                )

                return run_learning_coach(
                    user=user,
                    child=child,
                    lesson=lesson,
                    unit_lesson=unit_lesson,
                    message=message,
                    tutor_session=tutor_session,
                    session_id=session_id,
                    progress=progress,
                    coach_index=1
                )

            # =========================================
            # CONTINUE LEARNING COACH 1
            # =========================================

            if (
                    current_stage
                    == LESSON_STAGE_LEARNING_COACH_1
            ):
                return run_learning_coach(
                    user=user,
                    child=child,
                    lesson=lesson,
                    unit_lesson=unit_lesson,
                    message=message,
                    tutor_session=tutor_session,
                    session_id=session_id,
                    progress=progress,
                    coach_index=1
                )

            # =========================================
            # SECOND QUESTION -> LEARNING COACH 2
            # =========================================

            if (
                    current_stage
                    == LESSON_STAGE_SECOND_QUESTION
            ):
                progress = update_lesson_stage(
                    progress=progress,
                    current_stage=
                    LESSON_STAGE_LEARNING_COACH_2
                )

                return run_learning_coach(
                    user=user,
                    child=child,
                    lesson=lesson,
                    unit_lesson=unit_lesson,
                    message=message,
                    tutor_session=tutor_session,
                    session_id=session_id,
                    progress=progress,
                    coach_index=2
                )

            # =========================================
            # CONTINUE LEARNING COACH 2
            # =========================================

            if (
                    current_stage
                    == LESSON_STAGE_LEARNING_COACH_2
            ):
                return run_learning_coach(
                    user=user,
                    child=child,
                    lesson=lesson,
                    unit_lesson=unit_lesson,
                    message=message,
                    tutor_session=tutor_session,
                    session_id=session_id,
                    progress=progress,
                    coach_index=2
                )

            # בשלבי clarification ו-final_assessment
            # עדיין אין מנוע ייעודי בקוד הנוכחי.
            raise HTTPException(
                status_code=409,
                detail=(
                    "Student answer is not expected "
                    f"during stage: {current_stage}"
                )
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

                unit_lesson_id=
                body.unit_lesson_id,

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
                DEFAULT_OPENAI_MODEL,

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
                        DEFAULT_OPENAI_MODEL,

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

            unit_lesson_id=
            body.unit_lesson_id,

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

        openai_cost_usd = calculate_openai_cost(
            model=DEFAULT_OPENAI_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens
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

            "current_stage":
                progress.get(
                    "current_stage"
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
# RESET UNIT LESSON PROGRESS
# =====================================================

@app.post(
    "/api/tutor/reset-unit-lesson"
)
def reset_unit_lesson(
        body: ResetUnitLessonRequest,
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
        # CHILD OWNERSHIP
        # =============================================

        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )

        # =============================================
        # LESSON VALIDATION
        # =============================================

        lesson = get_learning_lesson(
            body.lesson_id
        )

        unit_lesson = get_unit_lesson(
            body.unit_lesson_id
        )

        if (
                int(
                    unit_lesson.get(
                        "learning_lesson_id"
                    )
                    or 0
                )
                !=
                int(
                    lesson.get(
                        "id"
                    )
                    or 0
                )
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Unit lesson does not belong "
                    "to the selected lesson"
                )
            )

        # =============================================
        # GRADE SECURITY
        # =============================================

        child_grade = int(
            child.get("age")
            or 0
        )

        lesson_grade = int(
            lesson.get("grade")
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

        now_iso = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        # =============================================
        # DELETE LEARNING COACH SESSIONS
        #
        # רק עבור הילד ותת־השיעור הנוכחי
        # =============================================

        coach_delete = (
            sb.table(
                "learning_coach_sessions"
            )
            .delete()
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "lesson_id",
                lesson["id"]
            )
            .eq(
                "unit_lesson_id",
                unit_lesson["id"]
            )
            .execute()
        )

        # =============================================
        # DELETE UNIT LESSON HISTORY
        # =============================================

        history_delete = (
            sb.table(
                "kid_lesson_history"
            )
            .delete()
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "lesson_id",
                lesson["id"]
            )
            .eq(
                "unit_lesson_id",
                unit_lesson["id"]
            )
            .execute()
        )

        # =============================================
        # RESET MAIN PROGRESS ROW
        #
        # kid_lesson_progress היא רשומה אחת לנושא,
        # לכן לא מוחקים אותה אלא מאפסים אותה
        # ומכוונים לתת־השיעור שנבחר.
        # =============================================

        progress_res = (
            sb.table(
                "kid_lesson_progress"
            )
            .select("*")
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "lesson_id",
                lesson["id"]
            )
            .limit(1)
            .execute()
        )

        progress = None

        if progress_res.data:

            progress_id = (
                progress_res.data[0]["id"]
            )
            objectives = (
                    lesson.get(
                        "learning_objectives"
                    )
                    or []
            )

            reset_objectives_progress = []

            for index, _ in enumerate(
                    objectives,
                    start=1
            ):
                reset_objectives_progress.append({
                    "objective_index":
                        index,

                    "score":
                        0,

                    "highest_difficulty_reached":
                        0,

                    "evidence_count":
                        0,

                    "evidence_by_level": {
                        "1": 0,
                        "2": 0,
                        "3": 0,
                        "4": 0,
                        "5": 0
                    }
                })

            progress_update = (
                sb.table(
                    "kid_lesson_progress"
                )
                .update({
                    "current_unit_lesson_id":
                        unit_lesson["id"],

                    "current_stage":
                        LESSON_STAGE_INTRO,

                    "current_flow_step":
                        0,

                    "flow_state":
                        {},

                    "status":
                        "in_progress",

                    "progress_percent":
                        0,

                    "mastery_score":
                        0,

                    "current_objective_index":
                        1,

                    "objectives_progress":
                        reset_objectives_progress,

                    "total_interactions":
                        0,

                    "attempts_count":
                        0,

                    "hints_used":
                        0,

                    "consecutive_successes":
                        0,

                    "consecutive_failures":
                        0,

                    "last_evaluation":
                        None,

                    "last_error_type":
                        None,

                    "completed_at":
                        None,

                    "xp_earned":
                        0,

                    "stars_earned":
                        0,

                    "last_session_id":
                        None,

                    "started_at":
                        now_iso,

                    "last_activity_at":
                        now_iso,

                    "updated_at":
                        now_iso
                })
                .eq(
                    "id",
                    progress_id
                )
                .execute()
            )

            if progress_update.data:
                progress = (
                    progress_update.data[0]
                )

        # =============================================
        # DEBUG
        # =============================================

        print(
            "UNIT LESSON RESET COMPLETED:",
            json.dumps(
                {
                    "user_id":
                        user.id,

                    "kid_id":
                        child["id"],

                    "lesson_id":
                        lesson["id"],

                    "unit_lesson_id":
                        unit_lesson["id"],

                    "coach_rows_deleted":
                        len(
                            coach_delete.data
                            or []
                        ),

                    "history_rows_deleted":
                        len(
                            history_delete.data
                            or []
                        ),

                    "progress_reset":
                        progress is not None,

                    "lesson_content_deleted":
                        False,

                    "lesson_audio_deleted":
                        False
                },
                ensure_ascii=False,
                indent=2
            )
        )

        return {
            "success": True,

            "kid_id":
                child["id"],

            "lesson_id":
                lesson["id"],

            "unit_lesson_id":
                unit_lesson["id"],

            "reset": {
                "learning_coach_sessions":
                    True,

                "lesson_history":
                    True,

                "lesson_progress":
                    True
            },

            "preserved": {
                "lesson_content":
                    True,

                "lesson_audio":
                    True
            },

            "progress": {
                "current_stage":
                    (
                        progress.get(
                            "current_stage"
                        )
                        if progress
                        else LESSON_STAGE_INTRO
                    ),

                "progress_percent":
                    0,

                "mastery_score":
                    0,

                "status":
                    "in_progress"
            }
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "RESET UNIT LESSON ERROR:",
            {
                "kid_id":
                    body.kid_id,

                "lesson_id":
                    body.lesson_id,

                "unit_lesson_id":
                    body.unit_lesson_id,

                "error_type":
                    type(e).__name__,

                "error":
                    repr(e)
            }
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Failed to reset unit lesson"
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
                    DEFAULT_OPENAI_MODEL,

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

            model=
            DEFAULT_OPENAI_MODEL,

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
                DEFAULT_OPENAI_MODEL,

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

# =====================================================
# CURRICULUM BUILDER CHAT
# =====================================================

@app.post("/api/curriculum/chat")
def curriculum_builder_chat(
        body: CurriculumBuilderChatRequest,
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

        message = str(
            body.message or ""
        ).strip()

        if not message:
            raise HTTPException(
                status_code=400,
                detail="message is required"
            )

        # =============================================
        # CHILD OWNERSHIP
        # =============================================

        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )

        custom_subject = None
        current_curriculum = None

        # =============================================
        # LOAD EXISTING SUBJECT + TREE
        # =============================================

        if body.custom_subject_id:

            custom_subject = (
                get_custom_subject(
                    user_id=user.id,
                    kid_id=child["id"],
                    custom_subject_id=
                        body.custom_subject_id
                )
            )

            current_curriculum = (
                get_current_custom_curriculum(
                    custom_subject_id=
                        custom_subject["id"]
                )
            )

        current_tree = {}

        if current_curriculum:
            current_tree = (
                current_curriculum.get(
                    "curriculum_json"
                )
                or {}
            )

        # =============================================
        # RUNTIME CONTEXT
        # =============================================

        runtime_context = {

            "child": {
                "id":
                    child.get("id"),

                "name":
                    child.get("child_name"),

                # אצלנו age משמש כמספר הכיתה
                "grade":
                    child.get("age"),

                "gender":
                    child.get("gender")
                    or "male"
            },

            "current_subject": (
                {
                    "id":
                        custom_subject.get("id"),

                    "subject_name":
                        custom_subject.get(
                            "subject_name"
                        ),

                    "status":
                        custom_subject.get(
                            "status"
                        )
                }
                if custom_subject
                else None
            ),

            "current_curriculum": (
                current_tree
            )
        }

        system_prompt = (
            CURRICULUM_BUILDER_PROMPT_TEMPLATE
            + "\n\n"
            + "RUNTIME_CONTEXT:\n"
            + json.dumps(
                runtime_context,
                ensure_ascii=False,
                indent=2
            )
        )

        # =============================================
        # CONVERSATION HISTORY
        # =============================================

        messages = [
            {
                "role":
                    "system",

                "content":
                    system_prompt
            }
        ]

        history = (
            body.history
            or []
        )

        for item in history[-12:]:

            if not isinstance(
                    item,
                    dict
            ):
                continue

            role = item.get(
                "role"
            )

            content = str(
                item.get(
                    "content"
                )
                or ""
            ).strip()

            if (
                    role not in (
                        "user",
                        "assistant"
                    )
                    or not content
            ):
                continue

            messages.append({
                "role":
                    role,

                "content":
                    content
            })

        messages.append({
            "role":
                "user",

            "content":
                message
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
                    DEFAULT_OPENAI_MODEL,

                messages=
                    messages,

                response_format=
                    CurriculumBuilderAIResponse
            )
        )

        curriculum_data = (
            completion
            .choices[0]
            .message
            .parsed
        )

        if not curriculum_data:
            raise RuntimeError(
                "Curriculum Builder returned no response"
            )

        response_subject = str(
            curriculum_data.subject
            or ""
        ).strip()

        if curriculum_data.hierarchy:

            hierarchy = (
                curriculum_data
                .hierarchy
                .model_dump()
            )

        else:

            hierarchy = (
                    current_tree
                    or {}
            )

        # =============================================
        # CREATE SUBJECT
        #
        # ברגע שה-AI זיהה מקצוע,
        # נוצרת הרשומה הראשית.
        # =============================================

        if (
                not custom_subject
                and response_subject
        ):

            custom_subject = (
                create_custom_subject(
                    user_id=user.id,
                    kid_id=child["id"],
                    subject_name=
                    response_subject
                )
            )

            # אם חזר מקצוע שכבר היה קיים,
            # נטען גם את התוכנית הקיימת שלו.
            current_curriculum = (
                get_current_custom_curriculum(
                    custom_subject_id=
                    custom_subject["id"]
                )
            )

            if current_curriculum:
                current_tree = (
                        current_curriculum.get(
                            "curriculum_json"
                        )
                        or {}
                )

        # =============================================
        # SAVE CURRICULUM
        # =============================================

        if (
                custom_subject
                and hierarchy
        ):

            if not current_curriculum:

                current_curriculum = (
                    create_custom_curriculum(
                        user_id=user.id,

                        kid_id=
                            child["id"],

                        custom_subject_id=
                            custom_subject["id"],

                        curriculum_json=
                            hierarchy,

                        ready_to_create=
                            bool(
                                curriculum_data
                                .ready_to_create
                            ),

                        parent_message=
                            message
                    )
                )

            else:

                current_curriculum = (
                    update_custom_curriculum(
                        user_id=user.id,

                        kid_id=
                            child["id"],

                        custom_subject=
                            custom_subject,

                        curriculum=
                            current_curriculum,

                        curriculum_json=
                            hierarchy,

                        subject_name=
                            response_subject,

                        ready_to_create=
                            bool(
                                curriculum_data
                                .ready_to_create
                            ),

                        parent_message=
                            message
                    )
                )

        # =============================================
        # TOKEN USAGE
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
            calculate_openai_cost(
                model=
                    DEFAULT_OPENAI_MODEL,

                input_tokens=
                    input_tokens,

                output_tokens=
                    output_tokens
            )
        )

        increment_usage_summary(
            user_id=user.id,

            ai_calls=1,

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
            curriculum_data
            .model_dump()
        )

        response_data[
            "kid_id"
        ] = child["id"]

        response_data[
            "custom_subject_id"
        ] = (
            custom_subject.get("id")
            if custom_subject
            else None
        )

        response_data[
            "curriculum_id"
        ] = (
            current_curriculum.get("id")
            if current_curriculum
            else None
        )

        response_data[
            "version"
        ] = (
            current_curriculum.get(
                "version"
            )
            if current_curriculum
            else None
        )

        response_data[
            "curriculum_status"
        ] = (
            current_curriculum.get(
                "status"
            )
            if current_curriculum
            else None
        )

        return response_data

    except HTTPException:
        raise

    except Exception as e:

        print(
            "CURRICULUM BUILDER ERROR:",
            repr(e)
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Curriculum Builder failed"
        )

# =====================================================
# APPROVE CUSTOM CURRICULUM
# =====================================================

@app.post("/api/curriculum/approve")
def approve_custom_curriculum(
        body: CurriculumApproveRequest,
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

        if not body.custom_subject_id:
            raise HTTPException(
                status_code=400,
                detail="custom_subject_id is required"
            )

        if not body.curriculum_id:
            raise HTTPException(
                status_code=400,
                detail="curriculum_id is required"
            )

        # =============================================
        # CHILD
        # =============================================

        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )

        # =============================================
        # SUBJECT
        # =============================================

        custom_subject = get_custom_subject(
            user_id=user.id,
            kid_id=child["id"],
            custom_subject_id=
                body.custom_subject_id
        )

        # =============================================
        # CURRICULUM
        # =============================================

        curriculum_res = (
            sb.table(
                "kid_custom_curriculums"
            )
            .select("*")
            .eq(
                "id",
                body.curriculum_id
            )
            .eq(
                "custom_subject_id",
                custom_subject["id"]
            )
            .eq(
                "user_id",
                user.id
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .limit(1)
            .execute()
        )

        if not curriculum_res.data:
            raise HTTPException(
                status_code=404,
                detail="Curriculum not found"
            )

        curriculum = (
            curriculum_res.data[0]
        )

        curriculum_json = (
            curriculum.get(
                "curriculum_json"
            )
            or {}
        )

        if not curriculum_json:
            raise HTTPException(
                status_code=400,
                detail="Curriculum is empty"
            )

        current_version = int(
            curriculum.get(
                "version"
            )
            or 1
        )

        now_iso = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        # =============================================
        # ACTIVATE SUBJECT
        # =============================================

        subject_update = (
            sb.table(
                "kid_custom_subjects"
            )
            .update({
                "status":
                    "active",

                "updated_at":
                    now_iso
            })
            .eq(
                "id",
                custom_subject["id"]
            )
            .eq(
                "user_id",
                user.id
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .execute()
        )

        if not subject_update.data:
            raise RuntimeError(
                "Failed to activate custom subject"
            )

        # =============================================
        # ACTIVATE CURRICULUM
        # =============================================

        curriculum_update = (
            sb.table(
                "kid_custom_curriculums"
            )
            .update({
                "status":
                    "active",

                "last_change_type":
                    "approved",

                "last_change_summary":
                    "Parent approved curriculum",

                "updated_by":
                    "parent",

                "updated_at":
                    now_iso
            })
            .eq(
                "id",
                curriculum["id"]
            )
            .eq(
                "user_id",
                user.id
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .execute()
        )

        if not curriculum_update.data:
            raise RuntimeError(
                "Failed to activate curriculum"
            )

        approved_curriculum = (
            curriculum_update.data[0]
        )

        # =============================================
        # MARK CURRENT VERSION AS APPROVED
        # =============================================

        version_update = (
            sb.table(
                "kid_custom_curriculum_versions"
            )
            .update({
                "change_type":
                    "approved",

                "change_summary":
                    "Parent approved curriculum",

                "changed_by":
                    "parent"
            })
            .eq(
                "curriculum_id",
                curriculum["id"]
            )
            .eq(
                "version",
                current_version
            )
            .eq(
                "user_id",
                user.id
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .execute()
        )

        # =============================================
        # BUILD RUNTIME UNITS + LESSONS
        # =============================================

        topics = (
            curriculum_json.get("topics")
            or []
        )

        if not isinstance(topics, list):
            raise RuntimeError(
                "Invalid curriculum topics"
            )

        units_created = 0
        lessons_created = 0

        for topic_index, topic in enumerate(
                topics,
                start=1
        ):

            if not isinstance(topic, dict):
                continue

            topic_name = str(
                topic.get("name")
                or ""
            ).strip()

            if not topic_name:
                continue

            units = (
                topic.get("units")
                or []
            )

            if not isinstance(units, list):
                continue

            for unit_index, unit in enumerate(
                    units,
                    start=1
            ):

                if not isinstance(unit, dict):
                    continue

                unit_name = str(
                    unit.get("name")
                    or ""
                ).strip()

                if not unit_name:
                    continue

                # =====================================
                # FIND EXISTING UNIT
                # =====================================

                existing_unit_res = (
                    sb.table(
                        "kid_custom_units"
                    )
                    .select("*")
                    .eq(
                        "curriculum_id",
                        curriculum["id"]
                    )
                    .eq(
                        "topic_order",
                        topic_index
                    )
                    .eq(
                        "unit_order",
                        unit_index
                    )
                    .limit(1)
                    .execute()
                )

                if existing_unit_res.data:

                    custom_unit = (
                        existing_unit_res.data[0]
                    )

                    # אם השם השתנה בגרסה חדשה
                    # מעדכנים את היחידה הקיימת
                    update_unit_res = (
                        sb.table(
                            "kid_custom_units"
                        )
                        .update({
                            "topic_name":
                                topic_name,

                            "unit_name":
                                unit_name,

                            "status":
                                "active",

                            "source_curriculum_version":
                                current_version,

                            "updated_at":
                                now_iso
                        })
                        .eq(
                            "id",
                            custom_unit["id"]
                        )
                        .execute()
                    )

                    if update_unit_res.data:
                        custom_unit = (
                            update_unit_res.data[0]
                        )

                else:

                    # =================================
                    # CREATE UNIT
                    # =================================

                    unit_insert_res = (
                        sb.table(
                            "kid_custom_units"
                        )
                        .insert({
                            "user_id":
                                user.id,

                            "kid_id":
                                child["id"],

                            "custom_subject_id":
                                custom_subject["id"],

                            "curriculum_id":
                                curriculum["id"],

                            "topic_name":
                                topic_name,

                            "topic_order":
                                topic_index,

                            "unit_name":
                                unit_name,

                            "unit_order":
                                unit_index,

                            "status":
                                "active",

                            "source_curriculum_version":
                                current_version,

                            "created_at":
                                now_iso,

                            "updated_at":
                                now_iso
                        })
                        .execute()
                    )

                    if not unit_insert_res.data:
                        raise RuntimeError(
                            "Failed to create custom unit"
                        )

                    custom_unit = (
                        unit_insert_res.data[0]
                    )

                    units_created += 1


                # =====================================
                # LESSONS
                # =====================================

                lessons = (
                    unit.get("lessons")
                    or []
                )

                if not isinstance(
                        lessons,
                        list
                ):
                    continue

                for lesson_index, lesson in enumerate(
                        lessons,
                        start=1
                ):

                    if not isinstance(
                            lesson,
                            dict
                    ):
                        continue

                    lesson_name = str(
                        lesson.get("name")
                        or ""
                    ).strip()

                    if not lesson_name:
                        continue

                    # =================================
                    # FIND EXISTING LESSON
                    # =================================

                    existing_lesson_res = (
                        sb.table(
                            "kid_custom_lessons"
                        )
                        .select("*")
                        .eq(
                            "custom_unit_id",
                            custom_unit["id"]
                        )
                        .eq(
                            "lesson_order",
                            lesson_index
                        )
                        .limit(1)
                        .execute()
                    )

                    if existing_lesson_res.data:

                        existing_lesson = (
                            existing_lesson_res.data[0]
                        )

                        sb.table(
                            "kid_custom_lessons"
                        ).update({
                            "lesson_name":
                                lesson_name,

                            "source_curriculum_version":
                                current_version,

                            "updated_at":
                                now_iso
                        }).eq(
                            "id",
                            existing_lesson["id"]
                        ).execute()

                    else:

                        # =============================
                        # CREATE LESSON
                        # =============================

                        lesson_insert_res = (
                            sb.table(
                                "kid_custom_lessons"
                            )
                            .insert({
                                "user_id":
                                    user.id,

                                "kid_id":
                                    child["id"],

                                "custom_subject_id":
                                    custom_subject["id"],

                                "curriculum_id":
                                    curriculum["id"],

                                "custom_unit_id":
                                    custom_unit["id"],

                                "lesson_name":
                                    lesson_name,

                                "lesson_order":
                                    lesson_index,

                                "status":
                                    "pending",

                                "source_curriculum_version":
                                    current_version,

                                "created_at":
                                    now_iso,

                                "updated_at":
                                    now_iso
                            })
                            .execute()
                        )

                        if not lesson_insert_res.data:
                            raise RuntimeError(
                                "Failed to create custom lesson"
                            )

                        lessons_created += 1

        print(
            "CUSTOM CURRICULUM APPROVED:",
            json.dumps(
                {
                    "user_id":
                        user.id,

                    "kid_id":
                        child["id"],

                    "custom_subject_id":
                        custom_subject["id"],

                    "curriculum_id":
                        curriculum["id"],

                    "version":
                        current_version,

                    "version_rows_updated":
                        len(
                            version_update.data
                            or []
                        ),
                    "units_created":
                        units_created,

                    "lessons_created":
                        lessons_created
                },
                ensure_ascii=False,
                indent=2
            )
        )

        return {
            "success": True,

            "kid_id":
                child["id"],

            "custom_subject_id":
                custom_subject["id"],

            "curriculum_id":
                approved_curriculum["id"],

            "subject":
                custom_subject.get(
                    "subject_name"
                ),

            "version":
                approved_curriculum.get(
                    "version"
                ),

            "subject_status":
                "active",

            "curriculum_status":
                "active",

            "units_created":
                units_created,

            "lessons_created":
                lessons_created
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "CURRICULUM APPROVE ERROR:",
            repr(e)
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Curriculum approval failed"
        )

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

            model=DEFAULT_OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                *recent_messages
            ],
            response_format=
            TutorLessonResponse
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

        openai_cost_usd = calculate_openai_cost(

            model=
            DEFAULT_OPENAI_MODEL,

            input_tokens=
            input_tokens,

            output_tokens=
            output_tokens

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

            sessions=(
                1
                if tutor_session.get("_is_new")
                else 0
            ),

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
