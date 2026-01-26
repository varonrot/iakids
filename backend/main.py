from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from supabase import create_client
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path

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
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth")

    token = authorization.replace("Bearer ", "")
    try:
        user_res = sb.auth.get_user(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid session")

    if not user_res or not user_res.user:
        raise HTTPException(status_code=401, detail="Invalid session")

    user = user_res.user
    child = get_child_profile(user.id)
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
        kids_memory=""  # נכניס בהמשך
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

    return {"reply": answer}

