from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from supabase import create_client
from openai import OpenAI
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

# ---------
# MODELS
# ---------

class ChatRequest(BaseModel):
    message: str

# ---------
# HELPERS
# ---------

def get_user_from_token(access_token: str):
    user = sb.auth.get_user(access_token)
    if not user or not user.user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user.user

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

@app.post("/api/chat")
def chat(
    body: ChatRequest,
    authorization: str = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth")

    token = authorization.replace("Bearer ", "")
    user = get_user_from_token(token)

    child = get_child_profile(user.id)
    memory = get_memory(child["id"])

    system_prompt = f"""
You are iakids, a friendly AI companion for children.

Child name: {child['child_name']}
Age: {child['age']}
Interests: {', '.join(child.get('learning_interests', []))}
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

    # Save chat
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
