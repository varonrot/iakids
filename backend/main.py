from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from supabase import create_client
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
import json

CORE_PROMPT_TEMPLATE = Path("prompts/iakids_core_chat_system_prompt.txt").read_text()
print("=== CORE PROMPT LOADED ===")
print(CORE_PROMPT_TEMPLATE[:300])
print("=========================")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

# ✅ ONE CORS ONLY
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://iakids.app",
        "https://www.iakids.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------
# MODELS
# ---------

class ChatRequest(BaseModel):
    message: str

class CreateChildProfileRequest(BaseModel):
    user_id: str
    child_name: str
    age: int
    avatar_key: str | None = None
    usage_goals: list[str] = []
    learning_interests: list[str] = []

# ---------
# HELPERS
# ---------
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

    memory = res.data[0]["memory"]

    if isinstance(memory, list):
        return "\n".join(f"- {m}" for m in memory)

    return str(memory)

def save_kids_memory(
    user_id: str,
    kid_id: str,
    memory_list: list[str],
    updated_by: str = "ai"
):
    sb.table("kids_memory").insert({
        "user_id": user_id,
        "kid_id": kid_id,
        "memory": memory_list,
        "updated_by": updated_by
    }).execute()

def should_run_memory_extraction(kid_id: str, every_n: int = 2) -> bool:
    res = (
        sb.table("kids_chats")
        .select("id")
        .eq("kid_id", kid_id)
        .eq("role", "user")
        .execute()
    )

    user_messages_count = len(res.data or [])
    print("USER MESSAGES COUNT:", user_messages_count)

    return user_messages_count > 0 and user_messages_count % every_n == 0

def get_recent_chat_messages(kid_id: str, limit: int = 8) -> str:
    res = (
        sb.table("kids_chats")
        .select("role, content")
        .eq("kid_id", kid_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    messages = reversed(res.data or [])
    return "\n".join(f"{m['role']}: {m['content']}" for m in messages)

def get_child_profile(user_id: str):
    res = (
        sb.table("kids_profiles")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="No child profile found")
    return res.data[0]

def save_chat_message(
    user_id: str,
    kid_id: str,
    role: str,
    content: str,
    tokens: int | None = None
):
    sb.table("kids_chats").insert({
        "user_id": user_id,
        "kid_id": kid_id,
        "role": role,
        "content": content,
        "tokens": tokens
    }).execute()

# ---------
# CHAT
# ---------

@app.post("/api/chat")
def chat(
    body: ChatRequest,
    authorization: str = Header(None)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing auth")

        token = authorization.replace("Bearer ", "")
        user_res = sb.auth.get_user(token)

        if not user_res or not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid session")

        user = user_res.user
        child = get_child_profile(user.id)
        existing_memory = get_existing_kids_memory(child["id"])

        save_chat_message(
            user_id=user.id,
            kid_id=child["id"],
            role="user",
            content=body.message
        )

        system_prompt = CORE_PROMPT_TEMPLATE.format(
            child_name=child["child_name"],
            age=child["age"],
            avatar_key=child.get("avatar_key", ""),
            learning_interests=", ".join(child.get("learning_interests", [])),
            usage_goals=", ".join(child.get("usage_goals", [])),
            kids_memory=existing_memory
        )

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": body.message}
            ]
        )

        answer = completion.choices[0].message.content

        save_chat_message(
            user_id=user.id,
            kid_id=child["id"],
            role="assistant",
            content=answer
        )

        if should_run_memory_extraction(child["id"]):
            try:
                extractor_prompt = Path(
                    "prompts/iakids_memory_extractor_prompt.txt"
                ).read_text()

                recent_chat = get_recent_chat_messages(child["id"])
                existing_memory_raw = get_existing_kids_memory(child["id"])

                print("===== RECENT CHAT SENT TO MEMORY EXTRACTOR =====")
                print(recent_chat)
                print("================================================")

                extractor_system = extractor_prompt.format(
                    child_name=child["child_name"],
                    age=child["age"],
                    existing_kids_memory=existing_memory_raw,
                    recent_chat_messages=recent_chat
                )

                extraction = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": extractor_system}]
                )

                raw = extraction.choices[0].message.content.strip()

                print("===== MEMORY EXTRACTOR RAW RESULT =====")
                print(raw)
                print("======================================")

                if raw == "NO_UPDATE":
                    return {"reply": answer}

                import re

                match = re.search(r'\{[\s\S]*\}', raw)
                if not match:
                    print("❌ No valid JSON found in memory extractor output")
                    return {"reply": answer}

                json_text = match.group(0)

                try:
                    data = json.loads(json_text)
                except Exception as e:
                    print("❌ JSON parse failed:", e)
                    return {"reply": answer}

                if data.get("update") and data.get("memory"):
                    save_kids_memory(
                        user_id=user.id,
                        kid_id=child["id"],
                        memory_list=data["memory"]
                    )


            except Exception as e:
                print("Memory extractor error:", e)

        return {"reply": answer}

    except Exception as e:
        print("CHAT ERROR:", e)
        raise HTTPException(status_code=500, detail="Chat failed")
