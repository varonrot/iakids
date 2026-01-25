from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from openai import OpenAI

from db import supabase

load_dotenv()

app = FastAPI()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# ---------- Models ----------
class ChatRequest(BaseModel):
    child_id: str
    message: str

# ---------- Utils ----------
def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

CORE_PROMPT = load_prompt("prompts/core_chat_system.txt")
MEMORY_PROMPT = load_prompt("prompts/memory_extractor.txt")

# ---------- Endpoint ----------
@app.post("/api/chat")
def chat(req: ChatRequest):

    # 1. Save user message
    supabase.table("kids_chats").insert({
        "child_id": req.child_id,
        "role": "user",
        "content": req.message
    }).execute()

    # 2. Load profile
    profile = supabase.table("kids_profiles") \
        .select("*") \
        .eq("id", req.child_id) \
        .single() \
        .execute().data

    if not profile:
        raise HTTPException(404, "Child not found")

    # 3. Load memory
    memory_rows = supabase.table("kids_memory") \
        .select("key,value") \
        .eq("child_id", req.child_id) \
        .execute().data or []

    memory_text = "\n".join(
        f"- {m['key']}: {m['value']}" for m in memory_rows
    )

    # 4. Load last messages
    history = supabase.table("kids_chats") \
        .select("role,content") \
        .eq("child_id", req.child_id) \
        .order("created_at", desc=True) \
        .limit(8) \
        .execute().data or []

    history = list(reversed(history))

    # 5. Build messages
    system_message = CORE_PROMPT.format(
        name=profile["child_name"],
        age=profile["age"],
        interests=", ".join(profile.get("learning_interests", [])),
        memory=memory_text
    )

    messages = [{"role": "system", "content": system_message}]
    messages += history
    messages.append({"role": "user", "content": req.message})

    # 6. OpenAI call
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7
    )

    reply = response.choices[0].message.content

    # 7. Save assistant message
    supabase.table("kids_chats").insert({
        "child_id": req.child_id,
        "role": "assistant",
        "content": reply
    }).execute()

    # 8. Optional: memory extractor trigger
    if len(history) >= 8:
        extract_memory(req.child_id, history + [
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": reply}
        ])

    return {"reply": reply}


# ---------- Memory Extraction ----------
def extract_memory(child_id: str, messages: list):

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": MEMORY_PROMPT},
            {"role": "user", "content": str(messages)}
        ],
        temperature=0
    )

    try:
        data = eval(res.choices[0].message.content)
    except:
        return

    for item in data:
        supabase.table("kids_memory").upsert({
            "child_id": child_id,
            "key": item["key"],
            "value": item["value"],
            "confidence": item.get("confidence", 0.7),
            "source": "chat"
        }).execute()
