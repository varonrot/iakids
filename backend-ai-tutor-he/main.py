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

# =====================================================
# CONFIG
# =====================================================

APP_NAME = "iakids AI Tutor Hebrew"
PROMPT_PATH = Path("prompts/iakids_ai_tutor_system_prompt.txt")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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

TUTOR_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")

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
    audio_duration_seconds: float = 0
):
    """
    עדכון Session לאחר קריאת TTS אחת.

    צובר:
    - מספר קריאות TTS
    - משך האודיו שנוצר
    """

    if not session_id:
        return

    now = datetime.now(timezone.utc)

    res = (
        sb.table("tutor_sessions")
        .select(
            "id, tts_call_count, voice_output_seconds"
        )
        .eq("id", session_id)
        .single()
        .execute()
    )

    if not res.data:
        return

    current_tts_calls = int(
        res.data.get("tts_call_count") or 0
    )

    current_voice_output_seconds = float(
        res.data.get("voice_output_seconds") or 0
    )

    new_voice_output_seconds = (
        current_voice_output_seconds
        + float(audio_duration_seconds or 0)
    )

    sb.table("tutor_sessions").update({

        "tts_call_count":
            current_tts_calls + 1,

        "voice_output_seconds":
            round(
                new_voice_output_seconds,
                3
            ),

        "last_activity_at":
            now.isoformat(),

        "updated_at":
            now.isoformat()

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
            "input_tokens, output_tokens, total_tokens"
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

    return new_session_res.data[0]

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

def update_tutor_session_after_chat(
    session: dict,
    total_tokens: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None
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
        authenticate_user(authorization)

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
                audio_duration_seconds=audio_duration_seconds
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

        # שומרים את הודעת הילד ותשובת ה-AI יחד
        # בקריאת Supabase אחת
        save_tutor_chat_messages(
            user_id=user.id,
            kid_id=child["id"],
            user_content=message,
            assistant_content=lesson_data.model_dump_json(),
            assistant_tokens=total_tokens,
            session_id=session_id
        )

        update_tutor_session_after_chat(
            session=tutor_session,
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens
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
