from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from supabase import create_client
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
import json
import hmac
import hashlib

from pathlib import Path
import os

# ===== LOAD PROMPTS =====

CORE_PROMPT_TEMPLATE = Path(
    "prompts/iakids_core_chat_system_prompt.txt"
).read_text()

print("=== CORE PROMPT LOADED ===")
print(CORE_PROMPT_TEMPLATE[:300])
print("=========================")

MODE_PROMPT_TEMPLATE = Path(
    "prompts/iakids_mode_guidance_prompt.txt"
).read_text()

print("=== MODE PROMPT LOADED ===")
print(MODE_PROMPT_TEMPLATE[:300])
print("==========================")

# ===== ENV =====

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LEMON_WEBHOOK_SECRET = os.getenv("LEMON_WEBHOOK_SECRET")

# ===== CLIENTS =====

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
    kid_id: str
    mode: str | None = None

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

def get_recent_chat_messages_for_llm(kid_id: str, limit: int = 7):
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
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m["role"] in ("user", "assistant")
    ]

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

        kid_id = body.kid_id
        if not kid_id:
            raise HTTPException(status_code=400, detail="kid_id is required")

        child = get_child_by_id(user.id, kid_id)
        existing_memory = get_existing_kids_memory(child["id"])
        sub = (
            sb.table("subscriptions")
            .select("messages_used")
            .eq("user_id", user.id)
            .single()
            .execute()
        )

        used = sub.data["messages_used"] if sub.data else 0
        LIMIT = 150  # זמני לבדיקה

        print("SUBSCRIPTION MESSAGES USED:", used)

        if used >= LIMIT:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "quota_exceeded",
                    "used": used,
                    "limit": LIMIT
                }
            )

        save_chat_message(
            user_id=user.id,
            kid_id=child["id"],
            role="user",
            content=body.message
        )
        sb.table("subscriptions").update({
            "messages_used": used + 1
        }).eq("user_id", user.id).execute()

        mode_value = body.mode or "unknown"

        system_prompt = (
                CORE_PROMPT_TEMPLATE
                + "\n\n"
                + MODE_PROMPT_TEMPLATE.format(
            child_name=child["child_name"],
            age=child["age"],
            avatar_key=child.get("avatar_key", ""),
            learning_interests=", ".join(child.get("learning_interests", [])),
            usage_goals=", ".join(child.get("usage_goals", [])),
            kids_memory=existing_memory,
            mode=mode_value
        )
        )

        recent_messages = get_recent_chat_messages_for_llm(child["id"], limit=5)

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                *recent_messages
            ]
        )

        answer = completion.choices[0].message.content

        save_chat_message(
            user_id=user.id,
            kid_id=child["id"],
            role="assistant",
            content=answer
        )

        if False:
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

                if (
                        isinstance(data, dict)
                        and data.get("update") is True
                        and isinstance(data.get("memory"), list)
                        and len(data["memory"]) > 0
                ):
                    save_kids_memory(
                        user_id=user.id,
                        kid_id=child["id"],
                        memory_list=data["memory"]
                    )


            except Exception as e:
                print("Memory extractor error:", e)

            return {"reply": answer}

        return {"reply": answer}

    except HTTPException:
        raise

    except Exception as e:
        print("CHAT ERROR:", e)
        raise HTTPException(status_code=500, detail="Chat failed")


# =====================================================
# LEMON SQUEEZY WEBHOOK
# =====================================================

from fastapi import Request
from datetime import datetime, timezone

@app.post("/api/lemonsqueezy-webhook")
async def lemonsqueezy_webhook(request: Request):

    # ===== READ RAW BODY =====
    raw_body = await request.body()

    # ===== GET SIGNATURE HEADER =====
    signature = request.headers.get("X-Signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    # ===== VERIFY SIGNATURE =====
    expected_signature = hmac.new(
        LEMON_WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # ===== PARSE JSON AFTER VERIFY =====
    payload = await request.json()

    event = payload.get("meta", {}).get("event_name")
    data = payload.get("data", {})
    attributes = data.get("attributes", {})

    print("LEMON EVENT:", event)

    # -------------------------
    # SUBSCRIPTION CREATED
    # -------------------------
    # -------------------------
    # SUBSCRIPTION CREATED
    # -------------------------
    if event == "subscription_created":

        email = attributes.get("user_email")
        lemon_subscription_id = data.get("id")
        lemon_customer_id = attributes.get("customer_id")
        renews_at = attributes.get("renews_at")

        user_res = sb.auth.admin.list_users()
        user = next((u for u in user_res.users if u.email == email), None)

        if not user:
            print("User not found:", email)
            return {"status": "user_not_found"}

        product_name = attributes.get("product_name", "").lower()

        if "anual" in product_name or "annual" in product_name:
            plan = "annual"
        else:
            plan = "monthly"

        sb.table("subscriptions").upsert({
            "user_id": user.id,
            "plan": plan,
            "status": "active",
            "lemon_subscription_id": lemon_subscription_id,
            "lemon_customer_id": lemon_customer_id,
            "expires_at": renews_at,
            "messages_used": 0
        }, on_conflict=["user_id"]).execute()

        print("Subscription created:", user.id)

    # -------------------------
    # PAYMENT SUCCESS (RENEWAL)
    # -------------------------
    if event == "subscription_payment_success":
        # 🔥 subscription id מגיע מה relationships
        lemon_subscription_id = (
            data.get("relationships", {})
            .get("subscription", {})
            .get("data", {})
            .get("id")
        )

        renews_at = attributes.get("renews_at")

        print("Updating subscription:", lemon_subscription_id)

        sb.table("subscriptions").update({
            "status": "active",
            "expires_at": renews_at
        }).eq("lemon_subscription_id", lemon_subscription_id).execute()


