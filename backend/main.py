from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from supabase import create_client
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware

import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
client = OpenAI()

app = FastAPI()

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://iakids.app",
        "https://www.iakids.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
    ],
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

def get_user_from_token(access_token: str):
    res = sb.auth.get_user(access_token)

    if res is None or res.user is None:
        raise HTTPException(status_code=401, detail="Invalid session")

    return res.user

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

def get_memory(child_id: str):
    res = (
        sb.table("kids_memory")
        .select("*")
        .eq("child_id", child_id)
        .execute()
    )
    return res.data or []

# ---------
# API
# ---------
@app.post("/api/create-kid-profile")
def create_kid_profile(body: CreateChildProfileRequest):
    # check if profile already exists
    existing = (
        sb.table("kids_profiles")
        .select("id")
        .eq("user_id", body.user_id)
        .limit(1)
        .execute()
    )

    if existing.data:
        return {"ok": True, "already_exists": True}

    res = (
        sb.table("kids_profiles")
        .insert({
            "user_id": body.user_id,
            "child_name": body.child_name,
            "age": body.age,
            "avatar_key": body.avatar_key,
            "usage_goals": body.usage_goals,
            "learning_interests": body.learning_interests
        })
        .execute()
    )

    if res.data is None:
        raise HTTPException(status_code=500, detail="Failed to create profile")

    return {"ok": True}

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
        if user_res is None or user_res.user is None:
            raise HTTPException(status_code=401, detail="Invalid session")
        user = user_res.user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid session")

    child = get_child_profile(user.id)
    memory = get_memory(child["id"])

    system_prompt = f"""
You are iakids, a friendly AI companion for children.

Child name: {child['child_name']}
Age: {child['age']}
Goals: {', '.join(child.get('usage_goals', []))}

Known memory:
{memory}
"""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": body.message}
        ]
    )

    answer = completion.choices[0].message.content

    sb.table("kids_chats").insert({
        "child_id": child["id"],
        "role": "user",
        "content": body.message
    }).execute()

    sb.table("kids_chats").insert({
        "child_id": child["id"],
        "role": "assistant",
        "content": answer
    }).execute()

    return {"reply": answer}
