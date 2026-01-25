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
": answer}
