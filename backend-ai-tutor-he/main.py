from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client
from openai import OpenAI
from pathlib import Path
import os
import json

# =====================================================
# CONFIG
# =====================================================

APP_NAME = "iakids AI Tutor Hebrew"
PROMPT_PATH = Path("prompts/iakids_ai_tutor_system_prompt.txt")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SUPABASE_URL:
    raise RuntimeError("Missing SUPABASE_URL")

if not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY")

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
client = OpenAI(api_key=OPENAI_API_KEY)

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


def save_tutor_chat_message(
    user_id: str,
    kid_id: str,
    role: str,
    content: str,
    tokens: int | None = None
):
    payload = {
        "user_id": user_id,
        "kid_id": kid_id,
        "role": role,
        "content": content,
    }

    if tokens is not None:
        payload["tokens"] = tokens

    sb.table("kids_chats").insert(payload).execute()


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
# AI TUTOR CHAT
# =====================================================

@app.post("/api/tutor/chat")
def tutor_chat(
    body: TutorChatRequest,
    authorization: str = Header(None)
):
    try:
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

        existing_memory = get_existing_kids_memory(
            child["id"]
        )

        # Save the child's current message first,
        # so it is included in the conversation history sent to the model.
        save_tutor_chat_message(
            user_id=user.id,
            kid_id=child["id"],
            role="user",
            content=message
        )

        system_prompt = build_tutor_prompt(
            child=child,
            kids_memory=existing_memory
        )

        recent_messages = get_recent_tutor_messages_for_llm(
            kid_id=child["id"],
            limit=8
        )

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                *recent_messages
            ]
        )
        raw_answer = (
            completion.choices[0].message.content or ""
        ).strip()

        print("=== RAW AI TUTOR RESPONSE ===")
        print(raw_answer)
        print("=============================")

        # Parse the structured JSON returned by the tutor
        try:
            tutor_response = json.loads(raw_answer)
        except json.JSONDecodeError as e:
            print("JSON PARSE ERROR:", repr(e))
            print("RAW RESPONSE:", raw_answer)

            raise HTTPException(
                status_code=500,
                detail="Invalid tutor response format"
            )

        # Validate required fields
        speech = tutor_response.get("speech", "")
        actions = tutor_response.get("actions", [])
        wait_for_answer = tutor_response.get(
            "wait_for_answer",
            False
        )

        if not isinstance(speech, str):
            speech = str(speech)

        if not isinstance(actions, list):
            actions = []

        if not isinstance(wait_for_answer, bool):
            wait_for_answer = bool(wait_for_answer)

        total_tokens = None

        if completion.usage:
            total_tokens = completion.usage.total_tokens

        # Save only the natural conversation text in kids_chats
        save_tutor_chat_message(
            user_id=user.id,
            kid_id=child["id"],
            role="assistant",
            content=speech,
            tokens=total_tokens
        )

        # Return structured lesson response to frontend
        return {
            "speech": speech,
            "actions": actions,
            "wait_for_answer": wait_for_answer
        }

    except HTTPException:
        raise

    except Exception as e:
        print("TUTOR CHAT ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail="Tutor chat failed"
        )
