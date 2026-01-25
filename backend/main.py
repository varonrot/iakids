import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

from db import sb

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI()

# ---------- MODELS ----------
class ChatRequest(BaseModel):
    kid_id: str
    message: str


# ---------- HELPERS ----------
def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


CORE_PROMPT = load_prompt("prompts/iakids_core_chat_system_prompt.txt")
MEMORY_PROMPT = load_prompt("prompts/iakids_memory_extractor_prompt.txt")


def get_kid_profile(kid_id: str):
    res = sb.table("kids_profiles").select("*").eq("id", kid_id).single().execute()
    return res.data


def get_recent_messages(kid_id: str, limit=10):
    res = (
        sb.table("kids_chats")
        .select("role, content")
        .eq("kid_id", kid_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(res.data or []))


def get_memory(kid_id: str):
    res = (
        sb.table("kids_memory")
        .select("memory_key, memory_value")
        .eq("kid_id", kid_id)
        .execute()
    )
    return res.data or []


def save_message(kid_id, role, content):
    sb.table("kids_chats").insert({
        "kid_id": kid_id,
        "role": role,
        "content": content
    }).execute()


def extract_and_save_memory(kid_id, messages):
    text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": MEMORY_PROMPT},
            {"role": "user", "content": text}
        ]
    )

    try:
        items = eval(completion.choices[0].message.content)
    except:
        return

    for item in items:
        sb.table("kids_memory").upsert({
            "kid_id": kid_id,
            "memory_key": item["key"],
            "memory_value": item["value"]
        }).execute()


# ---------- ROUTE ----------
@app.post("/chat")
def chat(req: ChatRequest):
    kid = get_kid_profile(req.kid_id)
    memory = get_memory(req.kid_id)
    history = get_recent_messages(req.kid_id)

    system_prompt = CORE_PROMPT.format(
        child_name=kid["child_name"],
        age=kid["age"],
        interests=", ".join(kid["learning_interests"] or []),
        goals=", ".join(kid["usage_goals"] or []),
        memory="\n".join([f"{m['memory_key']}: {m['memory_value']}" for m in memory])
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    messages.append({"role": "user", "content": req.message})

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    reply = completion.choices[0].message.content

    save_message(req.kid_id, "user", req.message)
    save_message(req.kid_id, "assistant", reply)

    # כל 10 הודעות – עדכון זיכרון
    if len(history) % 10 == 0:
        extract_and_save_memory(req.kid_id, history)

    return {"reply": reply}
