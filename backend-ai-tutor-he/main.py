from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Response,
    BackgroundTasks
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client
from openai import OpenAI
import asyncio
import hashlib
from starlette.concurrency import run_in_threadpool
from openai import AsyncOpenAI
from google import genai
from google.genai import types
from pathlib import Path
from datetime import datetime, timezone, timedelta
import io
import wave
import os
import json
import base64
import traceback
import time
import math
import re
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Must run before the os.getenv calls below. APP_ENV picks the file:
#   APP_ENV=prod -> .env.prod   (live iakids.app data)
#   APP_ENV=dev  -> .env.dev    (default; safe to experiment)
# Falls back to plain .env if the per-env file is absent. No-op on Render,
# which injects the vars directly and is never overridden by load_dotenv.
_env = os.getenv("APP_ENV", "dev")
_here = Path(__file__).resolve().parent
_envfile = _here / f".env.{_env}"
load_dotenv(_envfile if _envfile.exists() else _here / ".env")
print(f"[config] APP_ENV={_env} -> {_envfile.name if _envfile.exists() else '.env'}")
# =====================================================
# CONFIG
# =====================================================

APP_NAME = "iakids AI Tutor Hebrew"
PROMPT_PATH = Path("prompts/iakids_ai_tutor_system_prompt.txt")
HOMEWORK_VISION_PROMPT_PATH = Path(
    "prompts/iakids_homework_vision_prompt.txt"
)
LESSON_PROMPT_PATH = Path(
    "prompts/iakids_structured_lesson_prompt.txt"
)

LESSON_INITIAL_PROMPT_PATH = Path(
    "prompts/iakids_lesson_initial_prompt.txt"
)

LESSON_EXPANSION_PROMPT_PATH = Path(
    "prompts/iakids_lesson_expansion_prompt.txt"
)

LESSON_DIRECTOR_PROMPT_PATH = Path(
    "prompts/lesson_director_prompt.txt"
)
VISUAL_DIRECTOR_PROMPT_PATH = Path(
    "prompts/iakids_visual_director_prompt.txt"
)
LESSON_TRANSITION_PROMPT_PATH = Path(
    "prompts/iakids_lesson_transition_prompt.txt"
)
LEARNING_COACH_PROMPT_PATH = Path(
    "prompts/learning_coach_system_prompt.txt"
)
CURRICULUM_BUILDER_PROMPT_PATH = Path(
    "prompts/iakids_curriculum_builder_system_prompt.txt"
)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# =====================================================
# OPENAI MODELS
# =====================================================

# מודל זול לפעולות שוטפות:
# צ'אט, המשך שיעור, הערכה וניתוח שיעורי בית
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

# המודל החזק ביותר משמש אך ורק ליצירת
# תוכן שיעור אוניברסלי חדש שנשמר במטמון
UNIVERSAL_LESSON_MODEL = "gpt-5.6-sol"


# =====================================================
# MODEL PRICING - USD PER 1M TOKENS
# =====================================================

MODEL_PRICING_USD = {

    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60
    },

    "gpt-5.6-sol": {
        "input": 5.00,
        "output": 30.00
    }

}

# =====================================================
# GEMINI TTS PRICING
# =====================================================

# כמות משוערת של Audio Tokens לשנייה
GEMINI_AUDIO_TOKENS_PER_SECOND = 25

# מחיר פלט אודיו (USD לכל מיליון Audio Tokens)
GEMINI_TTS_AUDIO_OUTPUT_COST_PER_1M = 10.0


def calculate_openai_cost(
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0
) -> float:

    pricing = MODEL_PRICING_USD.get(
        model
    )

    if not pricing:
        print(
            "WARNING: Missing pricing for model:",
            model
        )
        return 0.0

    input_cost = (
        int(input_tokens or 0)
        / 1_000_000
        * pricing["input"]
    )

    output_cost = (
        int(output_tokens or 0)
        / 1_000_000
        * pricing["output"]
    )

    return input_cost + output_cost

# =====================================================
# STRUCTURED LESSON PEDAGOGICAL ENGINE
# =====================================================

# יעד נחשב נשלט כאשר הילד מגיע לפחות לציון הזה
OBJECTIVE_MASTERY_THRESHOLD = 90

# =====================================================
# DIFFICULTY LEVEL CAPS
#
# ילד לא יכול להגיע לשליטה מלאה
# רק מחזרה על משימות קלות.
#
# רמה 1 = היכרות / זיהוי
# רמה 2 = הבנה בסיסית
# רמה 3 = יישום
# רמה 4 = יישום עצמאי
# רמה 5 = העברה / מצב חדש / אתגר מסכם
# =====================================================

DIFFICULTY_SCORE_CAPS = {

    1: 30,

    2: 50,

    3: 70,

    4: 90,

    5: 100

}

# =====================================================
# BASE EVIDENCE POINTS
#
# אלו נקודות "הוכחת שליטה".
# הן עדיין כפופות לתקרת רמת הקושי.
# =====================================================

RESPONSE_QUALITY_POINTS = {

    "correct":
        8,

    "partial":
        3,

    "incorrect":
        0

}

INDEPENDENCE_POINTS = {

    "independent":
        4,

    "with_hint":
        2,

    "guided":
        0

}

UNDERSTANDING_POINTS = {

    "strong":
        4,

    "partial":
        2,

    "weak":
        0

}

EVIDENCE_STRENGTH_POINTS = {

    "strong":
        4,

    "moderate":
        2,

    "weak":
        0

}

if not SUPABASE_URL:
    raise RuntimeError("Missing SUPABASE_URL")

if not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")

def require_api_key(
        name: str,
        value: str
) -> str:
    """
    A key must be present AND usable. 2026-09-17: an edit to .env.prod left the
    file without a closing newline, so the next appended line was glued onto the
    end of GEMINI_API_KEY. The service started normally, every text and voice
    call worked, and EVERY image of the lesson failed deep inside the SDK with
    'ascii codec can't encode character' — a whole lesson was generated with no
    pictures and the media job still reported success. A key that is not clean
    ASCII, or that carries a second VAR= inside it, is a broken file, not a
    key: refuse to start and say which variable it is.
    """
    v = (value or "").strip()

    if not v:
        raise RuntimeError(f"Missing {name}")

    if not v.isascii():
        raise RuntimeError(
            f"{name} contains non-ASCII characters (length {len(v)}). "
            f"The value in the env file is corrupted — most likely a line was "
            f"appended to a file with no trailing newline. Fix the env file."
        )

    if "_KEY=" in v or "_URL=" in v:
        raise RuntimeError(
            f"{name} has another variable glued into its value "
            f"(length {len(v)}). The env file is missing a newline. Fix it."
        )

    return v


OPENAI_API_KEY = require_api_key("OPENAI_API_KEY", OPENAI_API_KEY)
GEMINI_API_KEY = require_api_key("GEMINI_API_KEY", GEMINI_API_KEY)
SUPABASE_SERVICE_KEY = require_api_key("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_KEY)

if not PROMPT_PATH.exists():
    raise RuntimeError(f"Missing prompt file: {PROMPT_PATH}")
if not LESSON_PROMPT_PATH.exists():
    raise RuntimeError(
        f"Missing lesson prompt file: "
        f"{LESSON_PROMPT_PATH}"
    )
TUTOR_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")
LESSON_PROMPT_TEMPLATE = (
    LESSON_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
LESSON_INITIAL_PROMPT_TEMPLATE = (
    LESSON_INITIAL_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
LESSON_EXPANSION_PROMPT_TEMPLATE = (
    LESSON_EXPANSION_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
LESSON_DIRECTOR_PROMPT_TEMPLATE = (
    LESSON_DIRECTOR_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
VISUAL_DIRECTOR_PROMPT_TEMPLATE = (
    VISUAL_DIRECTOR_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
LESSON_TRANSITION_PROMPT_TEMPLATE = (
    LESSON_TRANSITION_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
LEARNING_COACH_PROMPT_TEMPLATE = (
    LEARNING_COACH_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
CURRICULUM_BUILDER_PROMPT_TEMPLATE = (
    CURRICULUM_BUILDER_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
print("=== LEARNING COACH PROMPT LOADED ===")
print(LEARNING_COACH_PROMPT_TEMPLATE[:300])
print("====================================")

HOMEWORK_VISION_PROMPT = (
    HOMEWORK_VISION_PROMPT_PATH
    .read_text(
        encoding="utf-8"
    )
)
print("=== AI TUTOR PROMPT LOADED ===")
print(TUTOR_PROMPT_TEMPLATE[:300])
print("==============================")

# =====================================================
# CLIENTS
# =====================================================

# One pooled HTTP/1.1 client for PostgREST, Auth and Storage. The library default is
# a single HTTP/2 connection per sub-client, and the *sync* HTTP/2 client under many
# threads is where the capacity went: measured 2026-09-14 on this service, 30
# concurrent cached lesson opens took 18 s (every request finished together) and a
# 30-thread benchmark on the same client died with "RECV_DATA in state CLOSED" —
# also the likely source of the "Server disconnected" seen in Storage. Pooled
# HTTP/1.1 measured ~16x parallel for 30 threads on the same endpoint.
import httpx as _httpx
from supabase.lib.client_options import SyncClientOptions as _SyncClientOptions

SUPABASE_HTTP_POOL = int(os.getenv("SUPABASE_HTTP_POOL", "100"))
_supabase_http = _httpx.Client(
    http2=False,
    timeout=_httpx.Timeout(float(os.getenv("SUPABASE_HTTP_TIMEOUT", "30")), connect=10.0),
    limits=_httpx.Limits(max_connections=SUPABASE_HTTP_POOL, max_keepalive_connections=SUPABASE_HTTP_POOL),
    follow_redirects=True,
)
sb = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    options=_SyncClientOptions(httpx_client=_supabase_http),
)

# =====================================================
# SUPABASE TEMPORARY ERROR RETRY
# =====================================================

def supabase_with_retry(
        operation,
        label: str = "SUPABASE",
        max_attempts: int = 3,
        base_delay_seconds: float = 0.5
):

    last_error = None

    for attempt in range(
        1,
        max_attempts + 1
    ):

        try:

            return operation()

        except Exception as e:

            last_error = e

            print(
                f"{label} RETRY:",
                {
                    "attempt":
                        attempt,

                    "max_attempts":
                        max_attempts,

                    "error":
                        repr(e)
                }
            )

            if attempt >= max_attempts:
                raise

            time.sleep(
                base_delay_seconds
                * attempt
            )

    raise last_error


_TRANSPORT_ERROR_MARKERS = (
    "RemoteProtocolError", "ConnectError", "ReadError", "WriteError",
    "ReadTimeout", "ConnectTimeout", "PoolTimeout", "Server disconnected",
    "ConnectionReset", "RemoteDisconnected",
)


def storage_with_retry(
        operation,
        label: str = "STORAGE",
        max_attempts: int = 3,
        base_delay_seconds: float = 0.3
):
    """Like supabase_with_retry, but only for dropped connections. A Storage
    answer such as 'Object not found' is a real answer (the media pipeline uses
    it as 'not generated yet') and must come back immediately, not after three
    tries and 1.5 s of sleeping."""

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except Exception as e:
            text = f"{type(e).__name__}: {e}"
            transient = any(marker in text for marker in _TRANSPORT_ERROR_MARKERS)
            if not transient or attempt >= max_attempts:
                raise
            print(
                f"{label} RETRY:",
                {"attempt": attempt, "max_attempts": max_attempts, "error": text[:200]}
            )
            time.sleep(base_delay_seconds * attempt)

client = OpenAI(
    api_key=OPENAI_API_KEY
)

# The async twin of `client`, for the routes that await the model instead of
# holding a worker thread through the call (tools/async_routes.py).
aclient = AsyncOpenAI(
    api_key=OPENAI_API_KEY
)

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)

# =====================================================
# AI PROVIDER SWITCH — direct (OpenAI + Google keys) or OpenRouter
# =====================================================
# AI_PROVIDER=openrouter routes the chat / lesson models through OpenRouter's
# OpenAI-compatible endpoint (same OpenAI SDK, model ids prefixed "openai/").
# TTS_PROVIDER (defaults to AI_PROVIDER) routes text-to-speech through
# OpenRouter's /audio/speech with the SAME Gemini TTS model, billed to the
# OpenRouter account instead of our Google AI Studio quota — the quota that ran
# out on 2026-09-14 with a single worker. Images stay on the direct Gemini
# client for now (OpenRouter has image output, but with a different model id
# and response shape; not wired yet).
AI_PROVIDER = os.getenv("AI_PROVIDER", "direct").strip().lower()
TTS_PROVIDER = os.getenv("TTS_PROVIDER", AI_PROVIDER).strip().lower()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_TTS_MODEL = os.getenv("OPENROUTER_TTS_MODEL", "google/gemini-3.1-flash-tts-preview")
TTS_VOICE = os.getenv("TTS_VOICE", "Aoede")
# --- speech to text (dictation): the child speaks, the text appears in the chat box ---
STT_PROVIDER = os.getenv("STT_PROVIDER", "openai")            # openai (direct key) | gemini
STT_MODEL = os.getenv("STT_MODEL", "gpt-4o-mini-transcribe")  # fallback: whisper-1
STT_GEMINI_MODEL = os.getenv("STT_GEMINI_MODEL", "gemini-3.1-flash-lite")
STT_MAX_SECONDS = int(os.getenv("STT_MAX_SECONDS", "60"))
STT_MAX_BYTES = int(os.getenv("STT_MAX_BYTES", "4000000"))    # ~4 MB of compressed audio
TTS_PARALLEL = max(1, int(os.getenv("TTS_PARALLEL", "3")))   # TTS calls in flight per lesson part (OpenRouter: 20 rpm)
TTS_STYLE_PREFIX = os.getenv(
    "TTS_STYLE_PREFIX",
    "Speak in natural, fluent Hebrew. Sound like a warm, friendly and patient teacher "
    "speaking naturally to a school-age child. Use clear pronunciation and natural pauses. "
    "Some words carry nikud (Hebrew vowel points) to remove ambiguity: pronounce those words "
    "exactly as vocalized (for example \u05de\u05b4\u05d3\u05b0\u05d1\u05b8\u05bc\u05e8 is midbar, desert, not medaber). "
    "Words written in Latin letters are English: pronounce them in English. "
    "Read exactly the following Hebrew text:\n\n"
)
_OPENROUTER_HEADERS = {"HTTP-Referer": "https://iakids.app", "X-Title": "iakids tutor"}

if AI_PROVIDER == "openrouter" or TTS_PROVIDER == "openrouter":
    if not OPENROUTER_API_KEY:
        raise RuntimeError("AI_PROVIDER/TTS_PROVIDER=openrouter but OPENROUTER_API_KEY is missing")

if AI_PROVIDER == "openrouter":
    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL, default_headers=_OPENROUTER_HEADERS)
    aclient = AsyncOpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL, default_headers=_OPENROUTER_HEADERS)


def llm_model(name: str) -> str:
    """OpenRouter wants 'openai/gpt-4o-mini'; the direct API wants 'gpt-4o-mini'."""
    if AI_PROVIDER == "openrouter" and "/" not in name:
        return f"openai/{name}"
    return name


DEFAULT_OPENAI_MODEL = llm_model(DEFAULT_OPENAI_MODEL)
UNIVERSAL_LESSON_MODEL = llm_model(UNIVERSAL_LESSON_MODEL)
print(f"[config] AI_PROVIDER={AI_PROVIDER} TTS_PROVIDER={TTS_PROVIDER} chat={DEFAULT_OPENAI_MODEL} lesson={UNIVERSAL_LESSON_MODEL}")

_openrouter_async_http = None


# ---------------------------------------------------------------------------
# TTS homographs (2026-09-15): unvocalized Hebrew is ambiguous — "מדבר" was read as
# medaber (speaks) instead of midbar (desert). Vocalizing every segment would cost
# a model call per segment, so only segments that contain a known homograph get
# ONE small gpt-4o-mini call that adds nikud to THOSE words only. The answer is
# accepted only if, with the nikud stripped, it is the original text word for word.
# ---------------------------------------------------------------------------
TTS_NIKUD = os.getenv("TTS_NIKUD", "1") == "1"
NIKUD_MODEL = os.getenv("NIKUD_MODEL", "gpt-4o-mini")
_TTS_HOMOGRAPHS = {
    "מדבר", "ספר", "חלב", "שמן", "דבר", "עלה", "כתב", "גזר", "זרע", "מלח", "בקר", "ערב",
    "פרח", "שבר", "פרה", "ילד", "לבן", "מטר", "סופר", "עצם", "מלך", "חבר", "אכל", "בשר",
    "צמח", "גדל", "עבר", "עוף", "שוק", "קרן", "זכר", "חמה", "רעב", "שער", "פנה", "מנה",
    "אמה", "עמד", "נשר", "כבש", "רצה", "בנה", "ראה", "שמר", "חלה", "עשה", "מסך", "קצר",
    "חצי", "אבל",
}
_TTS_HOMOGRAPHS |= {w.strip() for w in os.getenv("TTS_HOMOGRAPHS", "").split(",") if w.strip()}
_HEB_PREFIXES = ("וכש", "וש", "וב", "ול", "ומ", "וה", "וכ", "כש", "ש", "ה", "ב", "ל", "מ", "כ", "ו")
_NIKUD_CHARS = re.compile(r"[֑-ׇ]")
_HEB_WORD = re.compile(r"[א-ת]+")
_NIKUD_CACHE: dict = {}


def strip_nikud(text: str) -> str:
    return _NIKUD_CHARS.sub("", str(text or ""))


def tts_homographs_in(text: str) -> list:
    """Words of `text` (with their prefix) whose base form is in the homograph list."""
    found = []
    for w in _HEB_WORD.findall(strip_nikud(text)):
        if w in _TTS_HOMOGRAPHS:
            found.append(w); continue
        for pre in _HEB_PREFIXES:
            if w.startswith(pre) and len(w) > len(pre) + 1 and w[len(pre):] in _TTS_HOMOGRAPHS:
                found.append(w); break
    return found


# ---------------------------------------------------------------------------
# CHILD NAME PRONUNCIATION (2026-09-17)
# "ארבל" read without vowels comes out wrong; a name is the first word the child
# hears. Curated table for the names we have, one small model call for a new name,
# and the answer is kept in Storage so every process and restart reuses it.
# ---------------------------------------------------------------------------
NAME_NIKUD_CURATED = {
    "ארבל": "\u05d0\u05b7\u05e8\u05b0\u05d1\u05bc\u05b5\u05dc",          # Arbel
    "איתן": "\u05d0\u05b5\u05d9\u05ea\u05b8\u05df",                        # Eitan
    "אלונה": "\u05d0\u05b7\u05dc\u05bc\u05d5\u05b9\u05e0\u05b8\u05d4",  # Alona
    "אבישג": "\u05d0\u05b2\u05d1\u05b4\u05d9\u05e9\u05c1\u05b7\u05d2",  # Avishag
    "אביתר": "\u05d0\u05b6\u05d1\u05b0\u05d9\u05b8\u05ea\u05b8\u05e8",  # Evyatar
    "רותם": "\u05e8\u05d5\u05b9\u05ea\u05b6\u05dd",                        # Rotem
    "נועה": "\u05e0\u05d5\u05b9\u05e2\u05b8\u05d4",
    "יהלי": "\u05d9\u05b7\u05d4\u05b2\u05dc\u05b4\u05d9",
    "תמר": "\u05ea\u05bc\u05b8\u05de\u05b8\u05e8",
    "שירה": "\u05e9\u05c1\u05b4\u05d9\u05e8\u05b8\u05d4",
    "אורי": "\u05d0\u05d5\u05bc\u05e8\u05b4\u05d9",
    "רוני": "\u05e8\u05d5\u05b9\u05e0\u05b4\u05d9",
    "עידו": "\u05e2\u05b4\u05d9\u05d3\u05d5\u05b9",
}
NAME_NIKUD_CURATED.update(json.loads(os.getenv("TTS_NAME_NIKUD_JSON", "{}")))
_NAME_NIKUD_PATH = os.getenv("TTS_NAME_NIKUD_PATH", "tts-cache/v1/name_nikud.json")
_name_nikud: dict | None = None


def _load_name_nikud() -> dict:
    global _name_nikud
    if _name_nikud is None:
        learned = {}
        try:
            raw = sb.storage.from_(LESSON_AUDIO_BUCKET).download(_NAME_NIKUD_PATH)
            learned = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            learned = {}
        _name_nikud = {**learned, **NAME_NIKUD_CURATED}      # curated always wins
    return _name_nikud


def _save_name_nikud(name: str, vocalized: str):
    try:
        try:
            raw = sb.storage.from_(LESSON_AUDIO_BUCKET).download(_NAME_NIKUD_PATH)
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            data = {}
        data[name] = vocalized
        sb.storage.from_(LESSON_AUDIO_BUCKET).upload(
            path=_NAME_NIKUD_PATH, file=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            file_options={"content-type": "application/json", "upsert": "true"})
    except Exception as e:
        print("NAME NIKUD SAVE FAILED (kept in memory):", repr(e)[:120])


def vocalize_name(name: str) -> str:
    """The child's first name with nikud, so the voice says it correctly."""
    clean = str(name or "").strip()
    if not clean or _NIKUD_CHARS.search(clean) or not _HEB_WORD.fullmatch(clean):
        return clean                                   # empty, already vocalized, or not one Hebrew word
    table = _load_name_nikud()
    if clean in table:
        return table[clean]
    if not TTS_NIKUD:
        return clean
    try:
        r = client.chat.completions.create(
            model=llm_model(NIKUD_MODEL), temperature=0,
            messages=[
                {"role": "system", "content": "נקד שם פרטי בעברית כפי שהוגים אותו בישראל. "
                                              "החזר אך ורק את השם המנוקד, בלי ניקוד חלקי ובלי מילים נוספות."},
                {"role": "user", "content": clean},
            ])
        out = str(r.choices[0].message.content or "").strip().split()[0]
        if strip_nikud(out) != clean or not _NIKUD_CHARS.search(out):
            print("NAME NIKUD REJECTED:", {"name": clean, "got": out[:40]})
            out = clean
        else:
            print("NAME NIKUD LEARNED:", {"name": clean, "vocalized": out})
            table[clean] = out
            _threading.Thread(target=_save_name_nikud, args=(clean, out), daemon=True).start()
        return out
    except Exception as e:
        print("NAME NIKUD FAILED:", {"name": clean, "error": repr(e)[:120]})
        return clean


def vocalize_for_tts(text: str, gender: str | None = None, child_name: str | None = None) -> str:
    """Return `text` with nikud where Hebrew is ambiguous when read aloud:
    1) second-person forms that are spelled identically for a boy and a girl
       (בשבילך, שלך, הצלחת, ראית) — deterministic table, needs the child's gender;
    2) semantic homographs (מדבר) — one small model call, only when one is present."""
    clean = str(text or "").strip()
    if child_name:
        spoken_name = vocalize_name(child_name)
        if spoken_name and spoken_name != child_name:
            clean = re.sub(r"(?<![\w\u0590-\u05FF])" + re.escape(str(child_name).strip()) + r"(?![\w\u0590-\u05FF])",
                           spoken_name, clean)
    if gender in ("male", "female"):
        clean = lq.second_person_nikud(clean, gender)
    if not TTS_NIKUD or not clean or _NIKUD_CHARS.search(clean):
        return clean                                   # already vocalized (or disabled)
    words = tts_homographs_in(clean)
    if not words:
        return clean                                   # nothing ambiguous: no model call, no cost
    if clean in _NIKUD_CACHE:
        return _NIKUD_CACHE[clean]
    t0 = time.perf_counter()
    try:
        r = client.chat.completions.create(
            model=llm_model(NIKUD_MODEL),
            temperature=0,
            messages=[
                {"role": "system", "content": (
                    "You add Hebrew nikud (vowel points) to specific words so a text-to-speech engine "
                    "pronounces them correctly. Rules: return the ENTIRE input text unchanged, except that "
                    "the listed words get full, correct nikud according to their meaning in context "
                    "(e.g. מדבר = מִדְבָּר desert, or מְדַבֵּר speaks). Do not add nikud to other words. "
                    "Do not change, add, remove or reorder any word or punctuation. Output the text only."
                )},
                {"role": "user", "content": "Words to vocalize: " + ", ".join(dict.fromkeys(words)) + "\n\nText:\n" + clean},
            ],
        )
        out = str(r.choices[0].message.content or "").strip()
        same = re.sub(r"\s+", " ", strip_nikud(out)) == re.sub(r"\s+", " ", clean)
        if not same:
            print("TTS NIKUD REJECTED (text changed):", {"words": words, "got": out[:120]})
            out = clean
        else:
            print("TTS NIKUD:", {"words": words, "ms": round((time.perf_counter() - t0) * 1000), "text": out[:120]})
    except Exception as e:
        print("TTS NIKUD FAILED (reading unvocalized):", {"words": words, "error": repr(e)[:160]})
        out = clean
    if len(_NIKUD_CACHE) > 5000:
        _NIKUD_CACHE.clear()
    _NIKUD_CACHE[clean] = out
    return out


# ---------------------------------------------------------------------------
# LIVE TTS CACHE (2026-09-15): the same sentence is spoken to the same child many
# times ("היי אלונה! כיף שבאת ללמוד איתי.", "אז קדימה, בואו נתחיל!"). Each
# rendering used to be a new model call (~2.5 s, ~$0.004). Now a WAV is stored
# once in Storage under a hash of (provider, model, voice, exact text) and served
# from there; identical requests in flight share one synthesis. Long, one-off
# texts (chat replies) are not cached. TTS_CACHE=0 disables it.
# ---------------------------------------------------------------------------
TTS_CACHE_ENABLED = os.getenv("TTS_CACHE", "1") == "1"
TTS_CACHE_MAX_CHARS = int(os.getenv("TTS_CACHE_MAX_CHARS", "400"))
TTS_CACHE_PREFIX = "tts-cache/v1"
_TTS_INFLIGHT: dict = {}          # cache key -> asyncio.Future (same text requested twice at once)


def tts_cache_key(text: str, gender: str | None = None) -> str:
    model = OPENROUTER_TTS_MODEL if TTS_PROVIDER == "openrouter" else "gemini-3.1-flash-tts-preview"
    raw = f"{TTS_PROVIDER}|{model}|{TTS_VOICE}|{gender or ''}|{TTS_STYLE_PREFIX}|{text.strip()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def tts_cacheable(text: str) -> bool:
    return TTS_CACHE_ENABLED and 0 < len(text.strip()) <= TTS_CACHE_MAX_CHARS


def tts_cache_path(key: str) -> str:
    return f"{TTS_CACHE_PREFIX}/{key}.wav"


_TTS_MEM_CACHE: dict = {}         # key -> wav bytes, hot items (a Storage download is ~0.5-1 s)
_TTS_MEM_CACHE_MAX = int(os.getenv("TTS_MEM_CACHE_ITEMS", "300"))   # ~300 × 150 KB ≈ 45 MB


def _tts_mem_put(key: str, wav_bytes: bytes):
    if len(_TTS_MEM_CACHE) >= _TTS_MEM_CACHE_MAX:
        _TTS_MEM_CACHE.pop(next(iter(_TTS_MEM_CACHE)), None)   # oldest inserted
    _TTS_MEM_CACHE[key] = wav_bytes


def tts_cache_get(key: str) -> bytes | None:
    """WAV bytes from memory or Storage, or None. A miss is a real answer, so no retries."""
    hit = _TTS_MEM_CACHE.get(key)
    if hit:
        return hit
    try:
        data = sb.storage.from_(LESSON_AUDIO_BUCKET).download(tts_cache_path(key))
        if data and len(data) > 44:
            _tts_mem_put(key, data)
            return data
        return None
    except Exception:
        return None


def tts_cache_put(key: str, wav_bytes: bytes):
    _tts_mem_put(key, wav_bytes)
    try:
        storage_with_retry(lambda: sb.storage.from_(LESSON_AUDIO_BUCKET).upload(
            path=tts_cache_path(key), file=wav_bytes,
            file_options={"content-type": "audio/wav", "upsert": "true"}
        ), label="TTS CACHE PUT")
        print("LIVE TTS CACHE STORED:", {"key": key[:12], "bytes": len(wav_bytes)})
    except Exception as e:
        print("LIVE TTS CACHE PUT FAILED (audio still served):", {"key": key[:12], "error": repr(e)[:160]})


def warm_tts_cache(texts: list, gender: str | None = None, child_name: str | None = None) -> dict:
    """Synthesize + store every text that is not cached yet. Runs on a thread
    (_threading.Thread(target=run_in_context(warm_tts_cache, texts))) so an intro's
    sentences are ready before the browser asks for them. Returns counts."""
    out = {"hit": 0, "warmed": 0, "failed": 0, "skipped": 0}
    for raw in texts:
        text = str(raw or "").strip()
        if not tts_cacheable(text):
            out["skipped"] += 1
            continue
        spoken = vocalize_for_tts(text, gender, child_name)
        key = tts_cache_key(spoken, gender)
        if tts_cache_get(key) is not None:
            out["hit"] += 1
            continue
        try:
            wav, dur = generate_tts_wav_bytes(spoken, gender)
            tts_cache_put(key, wav)
            out["warmed"] += 1
            print("LIVE TTS CACHE WARMED:", {"key": key[:12], "seconds": round(dur, 1), "text_length": len(text)})
        except Exception as e:
            out["failed"] += 1
            print("LIVE TTS CACHE WARM FAILED:", {"key": key[:12], "error": repr(e)[:160]})
    return out


def _openrouter_tts_payload(text: str) -> dict:
    return {
        "model": OPENROUTER_TTS_MODEL,
        "input": TTS_STYLE_PREFIX + text,
        "voice": TTS_VOICE,
        "response_format": "pcm",          # 24 kHz 16-bit mono, same bytes Gemini returns directly
    }


def openrouter_tts_pcm(text: str, timeout_s: float = 90.0) -> bytes:
    """One synchronous TTS call through OpenRouter. Returns raw PCM bytes."""
    t0 = time.time()
    r = _httpx.post(
        f"{OPENROUTER_BASE_URL}/audio/speech",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", **_OPENROUTER_HEADERS},
        json=_openrouter_tts_payload(text),
        timeout=timeout_s,
    )
    _record_openrouter_tts(r, t0)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} OPENROUTER_TTS {r.text[:300]}")
    if not r.content:
        raise RuntimeError("OpenRouter TTS returned no audio data")
    return r.content


def _record_openrouter_tts(r, t0: float):
    """ai_calls row for one OpenRouter TTS answer; exact cost is filled in later by
    generation id (ai_costs.resolve_pending_costs)."""
    try:
        ok = r.status_code == 200 and bool(r.content)
        gen_id = r.headers.get("X-Generation-Id") if ok else None
        ai_costs.record(
            "openrouter", OPENROUTER_TTS_MODEL,
            audio_seconds=(len(r.content) / (24000 * 2)) if ok else None,
            latency_ms=(time.time() - t0) * 1000,
            status="ok" if ok else "error",
            error=None if ok else f"{r.status_code} {r.text[:200]}",
            cost_source="pending" if gen_id else "unknown",
            generation_id=gen_id,
        )
    except Exception as e:
        print("AI COSTS RECORD FAILED (tts):", repr(e)[:120])


async def openrouter_tts_pcm_async(text: str, timeout_s: float = 90.0) -> bytes:
    global _openrouter_async_http
    if _openrouter_async_http is None:
        _openrouter_async_http = _httpx.AsyncClient(timeout=timeout_s)
    t0 = time.time()
    r = await _openrouter_async_http.post(
        f"{OPENROUTER_BASE_URL}/audio/speech",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", **_OPENROUTER_HEADERS},
        json=_openrouter_tts_payload(text),
    )
    _record_openrouter_tts(r, t0)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} OPENROUTER_TTS {r.text[:300]}")
    if not r.content:
        raise RuntimeError("OpenRouter TTS returned no audio data")
    return r.content
# ===== end AI provider switch =====

# =====================================================
# AI CALL ACCOUNTING — one ai_calls row per model call (ai_costs.py)
# =====================================================
from ai_costs import AICostTracker, set_call_context, run_in_context  # noqa: E402

ai_costs = AICostTracker(
    sb, service="tutor-web",
    prices=MODEL_PRICING_USD,
    audio_tokens_per_second=GEMINI_AUDIO_TOKENS_PER_SECOND,
    audio_output_price_per_1m=GEMINI_TTS_AUDIO_OUTPUT_COST_PER_1M,
    # $30 per 1M image-output tokens, 1120 tokens per 1024px image (ai.google.dev pricing, 2026-09)
    image_prices={"gemini-3.1-flash-lite-image": 0.0336, **json.loads(os.getenv("AI_IMAGE_PRICES_JSON", "{}"))},
    openrouter_api_key=OPENROUTER_API_KEY,
    openrouter_base_url=OPENROUTER_BASE_URL,
)
ai_costs.install(openai_clients=[client, aclient], gemini_client=gemini_client)
import uuid
import media_trace
media_trace.install_print_prefix()
import lesson_quality as lq
IMAGE_TEXT_CHECK = os.getenv("IMAGE_TEXT_CHECK", "0") == "1"          # vision call per image (~$0.0003): OFF by default (2026-09-16), set 1 to enable
IMAGE_TEXT_CHECK_MODEL = os.getenv("IMAGE_TEXT_CHECK_MODEL", "gemini-3.1-flash-lite")
VISUAL_REUSE = False  # disabled: generate a distinct image for every visual segment
VISUAL_NEW_RATIO = float(os.getenv("VISUAL_NEW_RATIO", "0.5"))     # share of segments that get a NEW image per part
VISUAL_MIN_NEW = int(os.getenv("VISUAL_MIN_NEW", "3"))              # never fewer new images than this per part (unless fewer segments)
LESSON_QUALITY_GATE = os.getenv("LESSON_QUALITY_GATE", "0") == "1"    # per-lesson report after every media job: OFF by default (2026-09-16), set 1 to enable
NO_TEXT_RETRY_SUFFIX = (
    "\n\nSTRICT RETRY: the previous image contained readable text. Produce the SAME scene with "
    "ABSOLUTELY NO letters, words, numbers, labels, captions, signs or symbols that look like writing."
)   # every print() -> "HH:MM:SS.mmm [T+.. req/job lesson part]" prefix


def ai_context(purpose: str, user=None, payload=None, **more):
    """Tag every model call made while handling this request/job."""
    return set_call_context(
        purpose=purpose,
        user_id=getattr(user, "id", None),
        kid_id=getattr(payload, "kid_id", None),
        unit_lesson_id=getattr(payload, "unit_lesson_id", None),
        **more
    )
# ===== end AI call accounting =====

# In production the interactive docs are off: /docs, /redoc and /openapi.json handed
# all 19 routes and 14 schemas to anyone who asked.
IS_PROD = os.getenv("APP_ENV", "dev") == "prod"
app = FastAPI(
    title=APP_NAME,
    version="0.1.0",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)

@app.middleware("http")
async def _media_trace_request(request, call_next):
    """T+0 for every request so every print in it reads as a timeline; lesson/kid are added by the routes."""
    media_trace.trace_begin(req=uuid.uuid4().hex[:8], path=request.url.path)
    t = time.perf_counter()
    response = await call_next(request)
    if request.url.path.startswith("/api/tutor/unit-lesson") or request.url.path.startswith("/api/tutor/tts"):
        print("REQUEST DONE", {"path": request.url.path, "status": response.status_code, "took_s": round(time.perf_counter() - t, 1)})
    return response

# =====================================================
# CORS
# =====================================================

# localhost is a development origin. Left on in production it lets a page running on
# the visitor's own machine call this API with their credentials.
ALLOWED_ORIGINS = [
    "https://iakids.app",
    "https://www.iakids.app",
    # mirror of the site served from smarts-brains.online
    "https://smarts-brains.online",
    "https://www.smarts-brains.online",
]
if not IS_PROD:
    ALLOWED_ORIGINS += ["http://localhost:3000", "http://localhost:5500", "http://127.0.0.1:5500"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== capacity: widen the worker pool, and keep one client from taking all of it =====
# Every route here is a plain `def`, so FastAPI runs it in anyio's worker threadpool
# and each request holds a thread for the whole model call. The pool defaults to 40,
# which is the whole service's concurrency; while the routes stay blocking, a wider
# pool is the cheapest capacity there is (a waiting thread costs memory, not CPU).
# Making the routes `async def` is the real fix and would make this moot.
import anyio as _anyio
import time as _time
from collections import deque as _deque
from fastapi import Request as _Request
from starlette.responses import JSONResponse as _JSONResponse

WORKER_THREADS = int(os.getenv("WORKER_THREADS", "128"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
_RATE_EXEMPT = set()
_rate_buckets: dict = {}


@app.on_event("startup")
async def _widen_threadpool():
    _anyio.to_thread.current_default_thread_limiter().total_tokens = WORKER_THREADS


@app.get("/")
async def health():
    """Something that answers 200 without a token.

    Render polls a path to decide whether the service is alive. Until now the only
    unauthenticated 200 on this service was /openapi.json — and in production that is
    now closed, which would have left the health check with nothing to hit and Render
    restarting a service that was working perfectly. It sits outside /api/, so the
    rate limiter does not count it.
    """
    return {"status": "ok", "service": "iakids-ai-tutor-he"}


@app.middleware("http")
async def _rate_limit(request: _Request, call_next):
    """A sliding one-minute window per caller on /api/*.

    Without it, one browser tab in a loop takes every worker thread and every other
    child sees a page that has stopped. Keyed by the bearer token when there is one
    (a user), else by address (a guest). Webhooks are exempt: Lemon retries them.
    """
    path = request.url.path
    if path.startswith("/api/") and path not in _RATE_EXEMPT:
        key = request.headers.get("authorization") or (request.client.host if request.client else "?")
        now = _time.time()
        q = _rate_buckets.setdefault(key, _deque())
        while q and q[0] < now - 60:
            q.popleft()
        if len(q) >= RATE_LIMIT_PER_MINUTE:
            return _JSONResponse(status_code=429, headers={"Retry-After": "60"},
                                 content={"detail": "rate_limited", "limit_per_minute": RATE_LIMIT_PER_MINUTE})
        q.append(now)
        if len(_rate_buckets) > 5000:                       # forget callers not seen this minute
            for k in [k for k, v in _rate_buckets.items() if not v or v[-1] < now - 60]:
                _rate_buckets.pop(k, None)
    return await call_next(request)


# ---- operational metrics: request_log + service_metrics in Supabase (ops_metrics.py)
from ops_metrics import OpsReporter as _OpsReporter

ops = _OpsReporter(sb, service="tutor-web")
_inflight = {"n": 0}
ops.gauges["threads_busy"] = lambda: _inflight["n"]          # /api requests in flight right now
ops.gauges["rate_buckets"] = lambda: len(_rate_buckets)
ops.gauges["media_jobs_mode"] = lambda: MEDIA_JOBS_MODE


@app.on_event("startup")
async def _start_ops_reporter():
    ops.start()
    ai_costs.start()


@app.middleware("http")
async def _request_log(request: _Request, call_next):
    """One request_log row per /api/* call: route template, status, milliseconds.
    Buffered in memory and flushed in batches; never adds a DB call to the request."""
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    _inflight["n"] += 1
    t0 = _time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        _inflight["n"] -= 1
        route = request.scope.get("route")
        ops.log_request(getattr(route, "path", None) or request.url.path, request.method, status,
                        (_time.perf_counter() - t0) * 1000)
# ===== end capacity =====


# =====================================================
# MEDIA JOBS — the queue that replaced BackgroundTasks
# =====================================================
# The media pipeline (intro videos, lesson visuals, TTS audio) used to run inside
# this web process after the response was sent. A deploy or crash in the middle
# lost the work silently, and every five-minute video poll held one of the
# server's threads. Now a route inserts one row into public.media_jobs and a
# separate process (worker.py) does the work. Same functions, different process.
#
# MEDIA_JOBS_MODE=queue   (default) rows go to the table; worker.py must be running
# MEDIA_JOBS_MODE=inline  the old behaviour, BackgroundTasks in this process
#
# If the queue is on but the insert fails (table missing, Supabase down), the job
# runs inline as before, so a broken queue degrades to today's behaviour, never to
# a lesson with no audio.

MEDIA_JOBS_MODE = os.getenv("MEDIA_JOBS_MODE", "queue").strip().lower()


# Lower runs first. What the child is waiting for on the first screen comes before
# what plays later or has a fallback (the standard intro replaces a missing personal one).
MEDIA_JOB_PRIORITY = {
    "unit_lesson_media": 10,
    "unit_lesson_audio": 10,
    "unit_lesson_visuals": 30,
    "kid_intro_videos": 60,
    "unit_lesson_transition": 90,
}
_enqueue_supports_priority = {"value": True}


def enqueue_media_job(
        job_type: str,
        payload: dict,
        dedupe_key: str | None = None,
        max_attempts: int = 3,
        priority: int | None = None
) -> int:
    """Insert a job row. Returns its id, or the id of the live duplicate."""

    if priority is None:
        priority = MEDIA_JOB_PRIORITY.get(job_type, 50)

    def operation():
        params = {
            "p_job_type": job_type,
            "p_payload": payload or {},
            "p_dedupe_key": dedupe_key,
            "p_max_attempts": max_attempts
        }
        if _enqueue_supports_priority["value"]:
            params["p_priority"] = int(priority)
        try:
            return sb.rpc("media_jobs_enqueue", params).execute()
        except Exception as e:
            # database still on the 4-argument enqueue (priority migration not applied):
            # fall back once, remember, keep working
            if _enqueue_supports_priority["value"] and "p_priority" in params and (
                    "PGRST202" in repr(e) or "Could not find the function" in repr(e)):
                _enqueue_supports_priority["value"] = False
                print("MEDIA JOB ENQUEUE: media_jobs_priority migration not applied, enqueuing without priority")
                params.pop("p_priority", None)
                return sb.rpc("media_jobs_enqueue", params).execute()
            raise

    res = supabase_with_retry(
        operation,
        label="MEDIA JOB ENQUEUE"
    )

    return int(res.data)


def dispatch_media_job(
        background_tasks: BackgroundTasks,
        job_type: str,
        payload: dict,
        dedupe_key: str | None,
        inline_fn,
        inline_args: tuple = ()
):
    """Queue the job, or fall back to running it in-process the old way.

    Synchronous (one Supabase RPC). From an `async def` route wrap it:
        await run_in_threadpool(lambda: dispatch_media_job(...))
    """

    if MEDIA_JOBS_MODE != "inline":

        try:

            job_id = enqueue_media_job(
                job_type=job_type,
                payload=payload,
                dedupe_key=dedupe_key,
                # a TTS quota hit costs a whole attempt; 5 tries × growing backoff
                # (60s × attempt) covers a few minutes of provider trouble
                max_attempts=int(os.getenv("MEDIA_JOB_MAX_ATTEMPTS", "5"))
            )

            print(
                "MEDIA JOB QUEUED:",
                {
                    "job_id": job_id,
                    "job_type": job_type,
                    "dedupe_key": dedupe_key
                }
            )

            return job_id

        except Exception as enqueue_error:

            print(
                "MEDIA JOB ENQUEUE FAILED - RUNNING INLINE:",
                {
                    "job_type": job_type,
                    "dedupe_key": dedupe_key,
                    "error": repr(enqueue_error)
                }
            )

    background_tasks.add_task(
        inline_fn,
        *inline_args
    )

    return None


def _list_storage_prefix(bucket: str, prefix: str) -> list:
    acc = []
    def walk(pfx):
        for o in sb.storage.from_(bucket).list(pfx, {"limit": 1000}):
            path = f"{pfx}/{o['name']}"
            if o.get("id") is None and o.get("metadata") is None:
                walk(path)
            else:
                acc.append(path)
    try:
        walk(prefix)
    except Exception as e:
        print("STORAGE LIST FAILED:", {"bucket": bucket, "prefix": prefix, "error": repr(e)[:120]})
    return acc


def run_lesson_quality_gate(unit_lesson_id: int, check_images: bool = True) -> dict:
    """Per-lesson QUALITY GATE: text rules, visual plan vs segments, audio vs segments,
    storage consistency (no stale versions, every referenced file exists) and, optionally,
    a vision check that no stored image carries readable text. The report is written to
    generated_lesson_json["quality"] and printed; it never raises."""
    row = get_unit_lesson(unit_lesson_id)
    g = row.get("generated_lesson_json") or {}
    cv = int(row.get("content_version") or 1)
    media = _list_storage_prefix(LESSON_MEDIA_BUCKET, f"unit_lessons/{unit_lesson_id}")
    audio = _list_storage_prefix(LESSON_AUDIO_BUCKET, f"unit_lessons/{unit_lesson_id}")
    image_results = None
    if check_images and IMAGE_TEXT_CHECK:
        image_results = {}
        reused = 0
        for path in sorted(p for p in media if (f"/v{cv}/" in p or "/hero_v" in p) and p.endswith(".png")):
            key = path.split(f"unit_lessons/{unit_lesson_id}/", 1)[-1]
            gen = _IMAGE_TEXT_RESULTS.get((int(unit_lesson_id), key))
            if gen is not None:
                image_results[key] = dict(gen, source="generation")   # already verified when it was made
                reused += 1
                continue
            try:
                data = sb.storage.from_(LESSON_MEDIA_BUCKET).download(path)
                image_results[key] = dict(lq.image_text_check(gemini_client, types, IMAGE_TEXT_CHECK_MODEL, data, "image/png"),
                                          source="gate")
            except Exception as e:
                image_results[key] = {"has_text": False, "text": "", "error": repr(e)[:100], "source": "gate"}
        print("LESSON QUALITY GATE IMAGES:", {"unit_lesson_id": unit_lesson_id, "checked": len(image_results), "reused_generation_results": reused})
    prev_q = g.get("quality") or {}
    report = lq.build_quality_report(
        g.get("structured_lesson") or {}, g.get("visual_plan"), row.get("lesson_audio_json"), cv,
        media, audio, image_results, image_overrides=prev_q.get("image_overrides") or {})
    report["image_overrides"] = prev_q.get("image_overrides") or {}
    print("LESSON QUALITY GATE " + ("PASS" if report["ok"] else "FAIL") + ":",
          {"unit_lesson_id": unit_lesson_id, "errors": report["errors"][:8], "warnings": len(report["warnings"]),
           "stats": report["stats"]})
    try:
        g = dict(g); g["quality"] = report
        update = {"generated_lesson_json": g}
        # generation_status has a CHECK constraint without a 'needs_review' value, so the
        # verdict lives in generated_lesson_json.quality: ok=false (and no human approval)
        # makes the unit-lesson route answer "needs_review" instead of serving the lesson.
        if not report["ok"]:
            print("LESSON QUALITY GATE -> flagged for human review (served anyway):", {"unit_lesson_id": unit_lesson_id, "errors": len(report["errors"])})
        supabase_with_retry(lambda: sb.table("lesson_units_content").update(update)
                            .eq("id", unit_lesson_id).execute(), label="SAVE QUALITY REPORT")
    except Exception as e:
        print("LESSON QUALITY GATE SAVE FAILED:", {"unit_lesson_id": unit_lesson_id, "error": repr(e)[:160]})
    return report


def run_media_job(
        job_type: str,
        payload: dict
):
    """Execute one job. Called by worker.py; the functions are the ones
    BackgroundTasks used to call, unchanged."""

    payload = payload or {}

    if job_type == "kid_intro_videos":
        child = get_child_by_id(
            user_id=str(payload["user_id"]),
            kid_id=str(payload["kid_id"])
        )
        return generate_kid_lesson_intro_videos_background(child)

    unit_lesson_runners = {
        "unit_lesson_audio": generate_unit_lesson_audio_background,
        "unit_lesson_visuals": generate_all_lesson_visuals_background,
        "unit_lesson_transition": generate_transition_video_background,
        "unit_lesson_media": generate_unit_lesson_media_background,
    }

    runner = unit_lesson_runners.get(job_type)

    if runner is None:
        raise ValueError(
            f"unknown media job type: {job_type}"
        )

    unit_lesson_id = int(payload["unit_lesson_id"])
    result = runner(unit_lesson_id)
    if LESSON_QUALITY_GATE and job_type in ("unit_lesson_media", "unit_lesson_audio", "unit_lesson_visuals"):
        try:
            with media_trace.stage("quality_gate"):
                run_lesson_quality_gate(unit_lesson_id, check_images=(job_type != "unit_lesson_audio"))
        except Exception as gate_error:
            print("LESSON QUALITY GATE CRASHED (job still done):", {"unit_lesson_id": unit_lesson_id, "error": repr(gate_error)[:200]})

    # generate_unit_lesson_media_background swallows an audio failure (it only
    # prints it), so without this check the job row would say "done" while the
    # lesson row says audio "failed". Raising here makes the queue retry the job
    # with backoff; visuals already stored are cache hits on the second attempt.
    if job_type in ("unit_lesson_media", "unit_lesson_audio"):
        after = get_unit_lesson(unit_lesson_id)
        status = after.get("audio_generation_status")
        if status == "failed":
            raise RuntimeError(
                f"audio generation failed for unit lesson {unit_lesson_id}: "
                f"{str(after.get('audio_generation_error') or '')[:300]}"
            )
        # The audio function returns silently when it decides there is nothing to do
        # (content not ready yet, JSON missing, ...). A job that ends without audio
        # is not done: fail it so the queue retries with backoff instead of leaving
        # the lesson mute forever.
        if status != "ready" or not after.get("lesson_audio_json"):
            raise RuntimeError(
                f"audio not ready after {job_type} for unit lesson {unit_lesson_id}: "
                f"audio_generation_status={status!r}, generation_status={after.get('generation_status')!r}"
            )

    return result
# ===== end media jobs =====


# =====================================================
# MODELS
# =====================================================

class TutorChatRequest(BaseModel):
    message: str
    kid_id: str

class CurriculumLesson(BaseModel):
    name: str


class CurriculumUnit(BaseModel):
    name: str
    lessons: list[CurriculumLesson]


class CurriculumTopic(BaseModel):
    name: str
    units: list[CurriculumUnit]


class CurriculumHierarchy(BaseModel):
    subject: str
    topics: list[CurriculumTopic]


class CurriculumBuilderChatRequest(BaseModel):
    kid_id: str
    message: str

    custom_subject_id: str | None = None

    history: list[dict] | None = None

class CurriculumApproveRequest(BaseModel):
    kid_id: str
    custom_subject_id: str
    curriculum_id: str

class CurriculumBuilderAIResponse(BaseModel):
    reply: str

    subject: str | None = None

    focus_topic: str | None = None

    hierarchy: CurriculumHierarchy | None = None

    ready_to_create: bool = False

class TutorTTSRequest(BaseModel):
    text: str
    session_id: str | None = None
    kid_id: str | None = None          # the voice must read second-person forms in the child's gender


class OpenAICleanChatRequest(BaseModel):
    message: str = ""
    image_url: str = ""
    history: list = []
    kid_id: str | None = None          # so the teacher speaks in the child's gender


class HomeworkCoachRequest(BaseModel):
    image_url: str = ""
    kid_id: str
    source_text: str = ""
    current_question: str = ""
    message: str = ""
    history: list[dict] | None = None


class HomeworkAnalyzeRequest(BaseModel):
    kid_id: str

    storage_path: str

    session_id: str | None = None

    file_name: str | None = None

    file_type: str | None = None

    file_size_bytes: int | None = None

    original_width: int | None = None

    original_height: int | None = None

    processed_width: int | None = None

    processed_height: int | None = None

    compression_quality: float | None = None


class TutorAction(BaseModel):

    type: str

    text: str | None = None

    target: str | None = None

    style: str | None = None

    speed: int | None = None

    duration: int | None = None

    speech_tts: str | None = None

    # =============================================
    # VISUAL CARD
    # =============================================

    title: str | None = None

    items: list[str] | None = None

    icon: str | None = None


class TutorLessonResponse(BaseModel):
    speech: str | None = None
    sequence: list[TutorAction]
    wait_for_answer: bool = False

class UniversalLessonResponse(BaseModel):
    explanation: str
    question: str
class DirectedLessonSegment(BaseModel):
    text: str


class DirectedLessonQuestion(BaseModel):
    text: str

class DirectedLessonUnitResponse(BaseModel):
    lesson: list[DirectedLessonSegment]
    question: DirectedLessonQuestion

class DirectedLessonPart(BaseModel):
    lesson: list[DirectedLessonSegment]
    question: DirectedLessonQuestion


class DirectedLessonSummary(BaseModel):
    text: str


class DirectedLessonResponse(BaseModel):

    part_1: DirectedLessonPart

    part_2: DirectedLessonPart

    summary: DirectedLessonSummary

class VisualDirectorItem(BaseModel):
    part_number: int
    order: int
    trigger_text: str
    type: str
    visual_goal: str
    source_text: str
    generation_prompt: str
    reuse_previous: bool          # True = this segment adds no new visual idea: show the previous image, generate nothing


class VisualDirectorResponse(BaseModel):
    version: int = 1
    visuals: list[VisualDirectorItem]

class LessonTransitionResponse(BaseModel):

    speech: str

    video_scene: str

    next_part_hook: str

    duration_seconds: int = 10

# =====================================================
# STRUCTURED LESSON MODELS
# =====================================================

class LessonIntroRequest(BaseModel):
    kid_id: str
    unit_lesson_id: int

class UnitLessonRequest(BaseModel):
    kid_id: str
    unit_lesson_id: int

class ActiveLessonStateRequest(BaseModel):
    kid_id: str
class ResetUnitLessonRequest(BaseModel):
    kid_id: str
    lesson_id: int
    unit_lesson_id: int
class StructuredLessonRequest(
    BaseModel
):
    kid_id: str

    lesson_id: int

    # תת־השיעור שהילד ראה בפועל
    unit_lesson_id: int | None = None

    # ריק = פתיחת שיעור
    # עם טקסט = תשובת הילד
    message: str | None = None


class LessonEvaluation(
    BaseModel
):
    # היעד הלימודי שנבדק בתור הזה
    objective_index: int | None = None

    # correct / partial / incorrect
    response_quality: str | None = None

    # independent / with_hint / guided
    independence_level: str | None = None

    # strong / partial / weak
    understanding_level: str | None = None

    # 1-5
    #
    # 1 = היכרות / זיהוי
    # 2 = הבנה בסיסית
    # 3 = יישום
    # 4 = יישום עצמאי
    # 5 = העברה למצב חדש / אתגר
    difficulty_level: int | None = None

    # strong / moderate / weak
    #
    # עד כמה האינטראקציה הזאת באמת
    # מספקת הוכחה לשליטה
    evidence_strength: str | None = None

    # האם מדובר בחזרה על אותו סוג
    # משימה שכבר נבדק מספר פעמים
    is_repetition: bool = False

    hint_used: bool = False

    repeated_mistake: bool = False

    identified_difficulty: str | None = None

    evaluation_summary: str | None = None

    lesson_summary: str | None = None


class StructuredLessonResponse(
    BaseModel
):
    speech: str | None = None

    sequence: list[TutorAction]

    wait_for_answer: bool = False

    # בפתיחת שיעור אין עדיין מה להעריך
    evaluation: (
            LessonEvaluation |
            None
    ) = None

# =====================================================
# LEARNING COACH MODELS
# =====================================================

class LearningCoachAIResponse(
    BaseModel
):
    understanding_score: int

    lesson_goal_achieved: bool

    teacher_response: str

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
        audio_duration_seconds: float = 0,
        cost_usd: float = 0
):
    """
    עדכון אטומי של Session לאחר קריאת TTS אחת.
    """

    if not session_id:
        return

    sb.rpc(
        "increment_tutor_session_tts",
        {
            "p_session_id": session_id,
            "p_audio_duration_seconds": audio_duration_seconds,
            "p_cost_usd": cost_usd
        }
    ).execute()


def update_tutor_session_after_vision(
        session_id: str,
        image_uploads: int = 1,
        vision_calls: int = 1
):
    if not session_id:
        return

    res = (
        sb.table("tutor_sessions")
        .select(
            "image_upload_count, "
            "vision_call_count"
        )
        .eq(
            "id",
            session_id
        )
        .single()
        .execute()
    )

    if not res.data:
        return

    current_image_uploads = int(
        res.data.get(
            "image_upload_count"
        ) or 0
    )

    current_vision_calls = int(
        res.data.get(
            "vision_call_count"
        ) or 0
    )

    sb.table(
        "tutor_sessions"
    ).update({

        "image_upload_count":
            current_image_uploads
            + image_uploads,

        "vision_call_count":
            current_vision_calls
            + vision_calls,

        "last_activity_at":
            datetime
            .now(timezone.utc)
            .isoformat(),

        "updated_at":
            datetime
            .now(timezone.utc)
            .isoformat()

    }).eq(
        "id",
        session_id
    ).execute()


# =====================================================
# DATA HELPERS
# =====================================================

def get_child_by_id(
        user_id: str,
        kid_id: str
):

    def operation():

        return (
            sb.table(
                "kids_profiles"
            )
            .select("*")
            .eq(
                "id",
                kid_id
            )
            .eq(
                "user_id",
                user_id
            )
            .single()
            .execute()
        )

    res = supabase_with_retry(
        operation,
        label="GET CHILD"
    )

    if not res.data:
        raise HTTPException(
            status_code=404,
            detail="Child not found"
        )

    return res.data

# =====================================================
# CUSTOM CURRICULUM HELPERS
# =====================================================

def get_custom_subject(
        user_id: str,
        kid_id: str,
        custom_subject_id: str
):
    res = (
        sb.table(
            "kid_custom_subjects"
        )
        .select("*")
        .eq(
            "id",
            custom_subject_id
        )
        .eq(
            "user_id",
            user_id
        )
        .eq(
            "kid_id",
            kid_id
        )
        .limit(1)
        .execute()
    )

    if not res.data:
        raise HTTPException(
            status_code=404,
            detail="Custom subject not found"
        )

    return res.data[0]

def create_custom_subject(
        user_id: str,
        kid_id: str,
        subject_name: str
):
    now_iso = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    clean_subject_name = str(
        subject_name or ""
    ).strip()

    if not clean_subject_name:
        raise ValueError(
            "subject_name is required"
        )

    # =============================================
    # CHECK IF SUBJECT ALREADY EXISTS FOR THIS KID
    # =============================================

    existing_res = (
        sb.table(
            "kid_custom_subjects"
        )
        .select("*")
        .eq(
            "user_id",
            user_id
        )
        .eq(
            "kid_id",
            kid_id
        )
        .eq(
            "subject_name",
            clean_subject_name
        )
        .in_(
            "status",
            ["draft", "active"]
        )
        .order(
            "created_at",
            desc=True
        )
        .limit(1)
        .execute()
    )

    if existing_res.data:

        existing_subject = (
            existing_res.data[0]
        )

        print(
            "REUSING CUSTOM SUBJECT:",
            existing_subject["id"],
            clean_subject_name
        )

        return existing_subject

    # =============================================
    # CREATE ONLY IF IT DOES NOT EXIST
    # =============================================

    res = (
        sb.table(
            "kid_custom_subjects"
        )
        .insert({
            "user_id":
                user_id,

            "kid_id":
                kid_id,

            "subject_name":
                clean_subject_name,

            "status":
                "draft",

            "created_by":
                "parent_ai_builder",

            "created_at":
                now_iso,

            "updated_at":
                now_iso
        })
        .execute()
    )

    if not res.data:
        raise RuntimeError(
            "Failed to create custom subject"
        )

    return res.data[0]


def get_current_custom_curriculum(
        custom_subject_id: str
):
    res = (
        sb.table(
            "kid_custom_curriculums"
        )
        .select("*")
        .eq(
            "custom_subject_id",
            custom_subject_id
        )
        .limit(1)
        .execute()
    )

    if not res.data:
        return None

    return res.data[0]


def create_custom_curriculum(
        user_id: str,
        kid_id: str,
        custom_subject_id: str,
        curriculum_json: dict,
        ready_to_create: bool,
        parent_message: str
):
    now_iso = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    curriculum_status = (
        "ready_for_approval"
        if ready_to_create
        else "building"
    )

    # =============================================
    # CURRENT VERSION
    # =============================================

    curriculum_res = (
        sb.table(
            "kid_custom_curriculums"
        )
        .insert({
            "user_id":
                user_id,

            "kid_id":
                kid_id,

            "custom_subject_id":
                custom_subject_id,

            "curriculum_json":
                curriculum_json,

            "version":
                1,

            "status":
                curriculum_status,

            "last_change_type":
                "created",

            "last_change_summary":
                "Initial curriculum created by AI",

            "updated_by":
                "ai",

            "created_at":
                now_iso,

            "updated_at":
                now_iso
        })
        .execute()
    )

    if not curriculum_res.data:
        raise RuntimeError(
            "Failed to create custom curriculum"
        )

    curriculum = (
        curriculum_res.data[0]
    )

    # =============================================
    # VERSION 1 SNAPSHOT
    # =============================================

    sb.table(
        "kid_custom_curriculum_versions"
    ).insert({
        "user_id":
            user_id,

        "kid_id":
            kid_id,

        "custom_subject_id":
            custom_subject_id,

        "curriculum_id":
            curriculum["id"],

        "version":
            1,

        "curriculum_json":
            curriculum_json,

        "change_type":
            "created",

        "change_summary":
            "Initial curriculum created by AI",

        "changed_by":
            "ai",

        "parent_message":
            parent_message,

        "created_at":
            now_iso
    }).execute()

    return curriculum


def update_custom_curriculum(
        user_id: str,
        kid_id: str,
        custom_subject: dict,
        curriculum: dict,
        curriculum_json: dict,
        subject_name: str | None,
        ready_to_create: bool,
        parent_message: str
):
    now_iso = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    current_version = int(
        curriculum.get(
            "version"
        )
        or 1
    )

    new_version = (
        current_version + 1
    )

    curriculum_status = (
        "ready_for_approval"
        if ready_to_create
        else "building"
    )

    # =============================================
    # UPDATE SUBJECT NAME IF AI REFINED IT
    # =============================================

    clean_subject_name = str(
        subject_name or ""
    ).strip()

    if (
            clean_subject_name
            and
            clean_subject_name
            != custom_subject.get(
                "subject_name"
            )
    ):
        sb.table(
            "kid_custom_subjects"
        ).update({
            "subject_name":
                clean_subject_name,

            "updated_at":
                now_iso
        }).eq(
            "id",
            custom_subject["id"]
        ).eq(
            "user_id",
            user_id
        ).execute()

    # =============================================
    # UPDATE CURRENT CURRICULUM
    # =============================================

    updated_res = (
        sb.table(
            "kid_custom_curriculums"
        )
        .update({
            "curriculum_json":
                curriculum_json,

            "version":
                new_version,

            "status":
                curriculum_status,

            "last_change_type":
                "ai_update",

            "last_change_summary":
                "Curriculum updated from parent conversation",

            "updated_by":
                "ai",

            "updated_at":
                now_iso
        })
        .eq(
            "id",
            curriculum["id"]
        )
        .eq(
            "user_id",
            user_id
        )
        .eq(
            "kid_id",
            kid_id
        )
        .execute()
    )

    if not updated_res.data:
        raise RuntimeError(
            "Failed to update custom curriculum"
        )

    updated_curriculum = (
        updated_res.data[0]
    )

    # =============================================
    # SAVE NEW VERSION SNAPSHOT
    # =============================================

    sb.table(
        "kid_custom_curriculum_versions"
    ).insert({
        "user_id":
            user_id,

        "kid_id":
            kid_id,

        "custom_subject_id":
            custom_subject["id"],

        "curriculum_id":
            curriculum["id"],

        "version":
            new_version,

        "curriculum_json":
            curriculum_json,

        "change_type":
            "ai_update",

        "change_summary":
            "Curriculum updated from parent conversation",

        "changed_by":
            "ai",

        "parent_message":
            parent_message,

        "created_at":
            now_iso
    }).execute()

    return updated_curriculum

HEBREW_WRITING_RULES = (
    "HEBREW CORRECTNESS (every answer is shown on screen AND read aloud by TTS):\n"
    "- Apply the gender rule above to EVERY verb, adjective, pronoun and suffix that refers to the child "
    "(שלך/שלך, בשבילך, הצלחת, ראית are written the same for a boy and a girl but are READ differently, "
    "so the rest of the sentence must make the gender unambiguous).\n"
    "- Hebrew numerals agree with the noun's gender: שלושה עצים / שלוש מילים, שני חלקים / שתי שאלות.\n"
    "- Never write slash or parenthesis forms (נסה/י, מוכן/ה): they are read aloud as gibberish.\n"
    "- No gershayim abbreviations (ק\"מ, ד\"ר, בי\"ס, וכו'): write the full words.\n"
    "- No emoji or symbols inside a spoken sentence; describe arrows and diagrams in words.\n"
    "- English words only when the English word itself is what is being taught.\n"
    "- One space after a comma or a period, no double spaces, no words in capitals.\n"
)


def hebrew_child_prompt_block(child: dict) -> str:
    """The block every child-facing prompt must carry: how to address THIS child plus the
    Hebrew rules that keep the answer correct both on screen and in the voice."""
    gender, rule = hebrew_gender_rule(child)
    return f"CHILD GENDER: {gender}. {rule}\n{HEBREW_WRITING_RULES}"


def hebrew_gender_rule(child: dict) -> tuple[str, str]:
    """('female'|'male'|'unknown', instruction for the model) — the ONE place that decides
    how the child is addressed in Hebrew. Every child-facing prompt uses it (2026-09-15)."""
    raw = str((child or {}).get("gender") or "").strip().lower()
    if raw in ("female", "f", "girl", "נקבה", "בת"):
        gender = "female"
    elif raw in ("male", "m", "boy", "זכר", "בן"):
        gender = "male"
    else:
        gender = "unknown"
    if gender == "female":
        rule = (
            "The child is a GIRL. Every Hebrew verb, adjective and pronoun that refers to her "
            "must be FEMININE SINGULAR (את, תרצי, נסי, חשבי, כתבי, תסתכלי, הצלחת, מוכנה, יודעת, "
            "בטוחה). Never use masculine forms."
        )
    elif gender == "male":
        rule = (
            "The child is a BOY. Every Hebrew verb, adjective and pronoun that refers to him "
            "must be MASCULINE SINGULAR (אתה, תרצה, נסה, חשוב, כתוב, תסתכל, הצלחת, מוכן, יודע, "
            "בטוח). Never use feminine forms."
        )
    else:
        rule = (
            "The child's gender is UNKNOWN. Do NOT guess it from the name. Write Hebrew that is "
            "correct for both: plural imperatives (בואו ננסה, תסתכלו, נבדוק יחד), 'אפשר ל...' "
            "constructions (אפשר לנסות?), questions without a second-person verb (מה דעתך? מה "
            "מצאת?), and shared past-tense forms (הצלחת, מצאת, ראית). Never write slash forms "
            "like נסה/י or מוכן/ה: the text is read aloud."
        )
        print("CHILD GENDER UNKNOWN (neutral Hebrew):", {"kid_id": (child or {}).get("id"), "child_name": (child or {}).get("child_name")})
    return gender, rule


def get_gender_placeholders(
        child: dict
) -> dict:
    gender = str(
        child.get("gender")
        or "unknown"
    ).strip().lower()

    if gender == "female":
        return {
            "{you}": "את",
            "{ready}": "מוכנה",
            "{try}": "נסי",
            "{think}": "חושבת",
            "{know}": "יודעת",
            "{succeed}": "מצליחה"
        }

    return {
        "{you}": "אתה",
        "{ready}": "מוכן",
        "{try}": "נסה",
        "{think}": "חושב",
        "{know}": "יודע",
        "{succeed}": "מצליח"
    }

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
# LEARNING COACH SESSION HELPERS
# =====================================================

LEARNING_COACH_MAX_ROUNDS = 5


def get_learning_coach_round_limit(understanding_score: int) -> int:
    """Adaptive diagnostic limit: do not trap a child until mastery.

    High scores need very little extra probing; lower scores get a few more
    focused turns so we can identify the weakness, then the lesson continues.
    The score is still preserved as diagnostic evidence.
    """
    score = max(0, min(100, int(understanding_score or 0)))

    if score >= 90:
        return 1
    if score >= 70:
        return 2
    if score >= 40:
        return 3
    return 4

# =====================================================
# UNIVERSAL LESSON STAGES
# =====================================================

LESSON_STAGE_INTRO = "lesson_intro"
LESSON_STAGE_FIRST_EXPLANATION = "first_explanation"
LESSON_STAGE_FIRST_QUESTION = "first_question"
LESSON_STAGE_LEARNING_COACH_1 = "learning_coach_1"
LESSON_STAGE_LEARNING_COACH = "learning_coach"
LESSON_STAGE_CLARIFICATION = "clarification"
LESSON_STAGE_SECOND_QUESTION = "second_question"
LESSON_STAGE_LEARNING_COACH_2 = "learning_coach_2"
LESSON_STAGE_FINAL_ASSESSMENT = "final_assessment"
LESSON_STAGE_COMPLETED = "lesson_completed"
LESSON_STAGE_NEXT_LESSON = "next_lesson"

VALID_LESSON_STAGES = {
    LESSON_STAGE_INTRO,
    LESSON_STAGE_FIRST_EXPLANATION,
    LESSON_STAGE_FIRST_QUESTION,
    LESSON_STAGE_LEARNING_COACH_1,
    LESSON_STAGE_LEARNING_COACH,
    LESSON_STAGE_CLARIFICATION,
    LESSON_STAGE_SECOND_QUESTION,
    LESSON_STAGE_LEARNING_COACH_2,
    LESSON_STAGE_FINAL_ASSESSMENT,
    LESSON_STAGE_COMPLETED,
    LESSON_STAGE_NEXT_LESSON,
}

def update_lesson_stage(
        progress: dict,
        current_stage: str
):
    if current_stage not in VALID_LESSON_STAGES:
        raise ValueError(
            f"Invalid lesson stage: {current_stage}"
        )

    now = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    res = (
        sb.table(
            "kid_lesson_progress"
        )
        .update({
            "current_stage":
                current_stage,

            "last_activity_at":
                now,

            "updated_at":
                now
        })
        .eq(
            "id",
            progress["id"]
        )
        .execute()
    )

    if not res.data:
        raise RuntimeError(
            "Failed to update lesson stage"
        )

    return res.data[0]

def update_learning_coach_flow_state(
        progress: dict,
        part_number: int
):
    now = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    existing_flow_state = (
        progress.get(
            "flow_state"
        )
        or {}
    )

    if not isinstance(
            existing_flow_state,
            dict
    ):
        existing_flow_state = {}

    new_flow_state = {
        **existing_flow_state,
        "phase": "learning_coach",
        "part_number": int(
            part_number
        )
    }

    res = (
        sb.table(
            "kid_lesson_progress"
        )
        .update({
            "current_stage":
                LESSON_STAGE_LEARNING_COACH,

            "flow_state":
                new_flow_state,

            "last_activity_at":
                now,

            "updated_at":
                now
        })
        .eq(
            "id",
            progress["id"]
        )
        .execute()
    )

    if not res.data:
        raise RuntimeError(
            "Failed to update Learning Coach flow state"
        )

    return res.data[0]

def get_active_learning_coach_session(
        kid_id: str,
        lesson_id: int,
        unit_lesson_id: int,
        coach_index: int
):
    res = (
        sb.table(
            "learning_coach_sessions"
        )
        .select("*")
        .eq(
            "kid_id",
            kid_id
        )
        .eq(
            "lesson_id",
            lesson_id
        )
        .eq(
            "unit_lesson_id",
            unit_lesson_id
        )
        .eq(
            "coach_index",
            coach_index
        )
        .eq(
            "status",
            "active"
        )
        .order(
            "created_at",
            desc=True
        )
        .limit(1)
        .execute()
    )

    if not res.data:
        return None

    return res.data[0]

def create_learning_coach_session(
        kid_id: str,
        lesson_id: int,
        unit_lesson_id: int,
        coach_index: int,
        lesson_history_id: int | None = None
):
    if coach_index < 1 or coach_index > 6:
        raise ValueError(
            f"Invalid coach_index: {coach_index}"
        )

    now = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    insert_data = {
        "kid_id":
            kid_id,

        "lesson_id":
            lesson_id,

        "unit_lesson_id":
            unit_lesson_id,

        "coach_index":
            coach_index,

        "started_at":
            now,

        "initial_understanding_score":
            0,

        "final_understanding_score":
            0,

        "total_rounds":
            0,

        "status":
            "active",

        "created_at":
            now
    }

    if lesson_history_id is not None:
        insert_data[
            "lesson_history_id"
        ] = lesson_history_id

    res = (
        sb.table(
            "learning_coach_sessions"
        )
        .insert(
            insert_data
        )
        .execute()
    )

    if not res.data:
        raise RuntimeError(
            "Failed to create "
            "Learning Coach session"
        )

    return res.data[0]

def get_or_create_learning_coach_session(
        kid_id: str,
        lesson_id: int,
        unit_lesson_id: int,
        coach_index: int
):
    existing_session = (
        get_active_learning_coach_session(
            kid_id=kid_id,
            lesson_id=lesson_id,
            unit_lesson_id=unit_lesson_id,
            coach_index=coach_index
        )
    )

    if existing_session:

        print(
            "LEARNING COACH SESSION FOUND:",
            json.dumps(
                {
                    "id":
                        existing_session.get("id"),

                    "coach_index":
                        existing_session.get(
                            "coach_index"
                        ),

                    "status":
                        existing_session.get("status"),

                    "total_rounds":
                        existing_session.get(
                            "total_rounds"
                        ),

                    "final_understanding_score":
                        existing_session.get(
                            "final_understanding_score"
                        )
                },
                ensure_ascii=False,
                indent=2
            )
        )

        return existing_session

    new_session = (
        create_learning_coach_session(
            kid_id=kid_id,
            lesson_id=lesson_id,
            unit_lesson_id=unit_lesson_id,
            coach_index=coach_index
        )
    )

    print(
        "LEARNING COACH SESSION CREATED:",
        json.dumps(
            {
                "id":
                    new_session.get("id"),

                "kid_id":
                    kid_id,

                "lesson_id":
                    lesson_id,

                "unit_lesson_id":
                    unit_lesson_id,

                "coach_index":
                    coach_index
            },
            ensure_ascii=False,
            indent=2
        )
    )

    return new_session

def extract_unit_lesson_coach_content(
        unit_lesson: dict,
        coach_index: int
):
    generated_json = (
        unit_lesson.get(
            "generated_lesson_json"
        )
        or {}
    )

    structured_lesson = (
        generated_json.get(
            "structured_lesson"
        )
        or {}
    )

    lesson_parts = (
        structured_lesson.get(
            "parts"
        )
        or []
    )

    lesson_part = None

    # Canonical dynamic parts structure.
    for fallback_part_number, candidate_part in enumerate(
            lesson_parts,
            start=1
    ):
        if not isinstance(
                candidate_part,
                dict
        ):
            continue

        candidate_part_number = int(
            candidate_part.get(
                "part_number"
            )
            or fallback_part_number
        )

        if candidate_part_number == coach_index:
            lesson_part = candidate_part
            break

    # Legacy fallback for older cached lessons.
    if lesson_part is None:
        legacy_part_key = (
            f"part_{coach_index}"
        )

        legacy_part = (
            structured_lesson.get(
                legacy_part_key
            )
            or {}
        )

        if isinstance(
                legacy_part,
                dict
        ) and legacy_part:
            lesson_part = legacy_part

    if not lesson_part:
        raise ValueError(
            f"Lesson part {coach_index} not found"
        )

    lesson_segments = (
        lesson_part.get(
            "lesson"
        )
        or []
    )

    explanation_parts = []

    for segment in lesson_segments:

        if not isinstance(
                segment,
                dict
        ):
            continue

        text = str(
            segment.get(
                "text"
            )
            or ""
        ).strip()

        if text:
            explanation_parts.append(
                text
            )

    lesson_explanation = "\n\n".join(
        explanation_parts
    )

    lesson_question = str(
        (
            lesson_part.get(
                "question"
            )
            or {}
        ).get(
            "text"
        )
        or ""
    ).strip()

    if not lesson_explanation:
        raise ValueError(
            f"Lesson part {coach_index} has no explanation"
        )

    if not lesson_question:
        raise ValueError(
            f"Lesson part {coach_index} has no question"
        )

    return {
        "part_number":
            coach_index,

        "lesson_explanation":
            lesson_explanation,

        "lesson_question":
            lesson_question
    }

def build_learning_coach_prompt(
        child: dict,
        parent_lesson: dict,
        unit_lesson: dict,
        coach_session: dict,
        conversation_history: list[dict],
        child_answer: str,
        coach_index: int
):
    coach_content = (
        extract_unit_lesson_coach_content(
            unit_lesson,
            coach_index
        )
    )

    current_round = (
        int(
            coach_session.get(
                "total_rounds"
            )
            or 0
        )
        + 1
    )

    previous_score = int(
        coach_session.get(
            "final_understanding_score"
        )
        or coach_session.get(
            "initial_understanding_score"
        )
        or 0
    )

    conversation_text_parts = []

    for item in conversation_history:

        role = item.get("role")

        content = str(
            item.get("content")
            or ""
        ).strip()

        if not content:
            continue

        role_name = (
            "Child"
            if role == "user"
            else "Teacher"
        )

        conversation_text_parts.append(
            f"{role_name}: {content}"
        )

    conversation_text_parts.append(
        f"Child: {child_answer}"
    )

    conversation_text = "\n".join(
        conversation_text_parts
    )

    runtime_data = {
        "child": {
            "child_name":
                child.get("child_name"),

            "grade":
                child.get("age"),

            "gender":
                child.get("gender")
                or "unknown"
        },

        "lesson": {
            "subject":
                parent_lesson.get("subject"),

            "lesson_name":
                unit_lesson.get("lesson_name"),

            "lesson_goal":
                (
                    unit_lesson.get(
                        "learning_objective"
                    )
                    or parent_lesson.get(
                        "lesson_goal"
                    )
                ),

            "lesson_explanation":
                coach_content[
                    "lesson_explanation"
                ],

            "current_question":
                coach_content[
                    "lesson_question"
                ],

            # כרגע אין עמודה נפרדת של תשובה נכונה.
            # ההסבר ומטרת השיעור משמשים כמקור האמת.
            "correct_answer":
                "Derive from the lesson explanation and lesson goal."
        },

        "conversation": {
            "conversation_history":
                conversation_text
        },

        "coach_state": {
            "part_number":
                int(
                    coach_content[
                        "part_number"
                    ]
                ),

            "current_round":
                current_round,

            "maximum_rounds":
                LEARNING_COACH_MAX_ROUNDS,

            "previous_understanding_score":
                previous_score
        }
    }

    final_prompt = (
        LEARNING_COACH_PROMPT_TEMPLATE
        + "\n\n"
        + "RUNTIME_DATA:\n"
        + json.dumps(
            runtime_data,
            ensure_ascii=False,
            indent=2
        )
    )

    return (
        final_prompt,
        runtime_data,
        current_round
    )

def update_learning_coach_session(
        coach_session: dict,
        understanding_score: int,
        goal_achieved: bool,
        current_round: int
):
    now = datetime.now(
        timezone.utc
    )

    recommended_round_limit = min(
        LEARNING_COACH_MAX_ROUNDS,
        get_learning_coach_round_limit(understanding_score)
    )

    max_rounds_reached = (
        current_round
        >= recommended_round_limit
    )

    if goal_achieved:
        status = "completed"

    elif max_rounds_reached:
        # Diagnostic completion: the child can continue even below mastery.
        # We intentionally keep the existing DB-safe status value.
        status = "max_rounds"

    else:
        status = "active"

    update_data = {
        "final_understanding_score":
            understanding_score,

        "total_rounds":
            current_round,

        "status":
            status
    }

    if status != "active":
        update_data[
            "ended_at"
        ] = now.isoformat()

    res = (
        sb.table(
            "learning_coach_sessions"
        )
        .update(
            update_data
        )
        .eq(
            "id",
            coach_session["id"]
        )
        .execute()
    )

    if res.data:
        return res.data[0]

    return {
        **coach_session,
        **update_data
    }

def calculate_lesson_coach_mastery(
        kid_id: str,
        lesson_id: int,
        unit_lesson_id: int,
        lesson_parts_count: int
) -> int:

    lesson_parts_count = max(
        1,
        min(
            6,
            int(
                lesson_parts_count
                or 1
            )
        )
    )

    res = (
        sb.table(
            "learning_coach_sessions"
        )
        .select(
            "coach_index, "
            "final_understanding_score, "
            "created_at"
        )
        .eq(
            "kid_id",
            kid_id
        )
        .eq(
            "lesson_id",
            lesson_id
        )
        .eq(
            "unit_lesson_id",
            unit_lesson_id
        )
        .order(
            "created_at",
            desc=True
        )
        .execute()
    )

    latest_scores = {}

    for coach_session in (
            res.data
            or []
    ):
        part_number = int(
            coach_session.get(
                "coach_index"
            )
            or 0
        )

        if (
                part_number < 1
                or
                part_number > lesson_parts_count
        ):
            continue

        if part_number in latest_scores:
            continue

        latest_scores[
            part_number
        ] = max(
            0,
            min(
                100,
                int(
                    coach_session.get(
                        "final_understanding_score"
                    )
                    or 0
                )
            )
        )

    total_score = 0

    for part_number in range(
            1,
            lesson_parts_count + 1
    ):
        total_score += (
            latest_scores.get(
                part_number,
                0
            )
        )

    return round(
        total_score
        /
        lesson_parts_count
    )

# =====================================================
# STRUCTURED LESSON DATA HELPERS
# =====================================================

def get_lesson_units_and_lessons(
        learning_lesson_id: int
):
    res = (
        sb.table(
            "lesson_units_content"
        )
        .select(
            "id, "
            "learning_lesson_id, "
            "unit_order, "
            "unit_name, "
            "lesson_order, "
            "lesson_name, "
            "status, "
            "is_active"
        )
        .eq(
            "learning_lesson_id",
            learning_lesson_id
        )
        .eq(
            "is_active",
            True
        )
        .order(
            "unit_order"
        )
        .order(
            "lesson_order"
        )
        .execute()
    )

    rows = res.data or []

    units_map = {}

    for row in rows:
        unit_order = int(
            row.get("unit_order") or 0
        )

        if unit_order not in units_map:
            units_map[unit_order] = {
                "unit_order": unit_order,
                "unit_name": row.get("unit_name"),
                "lessons": []
            }

        units_map[unit_order]["lessons"].append({
            "id": row.get("id"),
            "lesson_order": row.get("lesson_order"),
            "lesson_name": row.get("lesson_name"),
            "status": row.get("status")
        })

    return list(
        units_map.values()
    )

def get_unit_lesson(
        unit_lesson_id: int
):

    def operation():

        return (
            sb.table(
                "lesson_units_content"
            )
            .select(
                "id, "
                "learning_lesson_id, "
                "unit_order, "
                "unit_name, "
                "lesson_order, "
                "lesson_name, "
                "intro_template_id, "
                "learning_objective, "
                "lesson_complexity, "
                "max_duration_seconds, "
                "lesson_parts_count, "
                "generation_status, "
                "content_version, "
                "generated_lesson_json, "
                "generation_error, "
                "generated_at, "
                "tts_generated_at, "
                "lesson_audio_json, "
                "audio_generation_status, "
                "audio_generation_error, "
                "audio_generated_at, "
                "updated_at, "
                "status, "
                "is_active"
            )
            .eq(
                "id",
                unit_lesson_id
            )
            .eq(
                "is_active",
                True
            )
            .limit(1)
            .execute()
        )

    res = supabase_with_retry(
        operation,
        label="GET UNIT LESSON"
    )

    if not res.data:
        raise HTTPException(
            status_code=404,
            detail="Unit lesson not found"
        )

    return res.data[0]

def get_intro_template(
        template_id: int
):

    def operation():

        return (
            sb.table(
                "lesson_intro_templates"
            )
            .select(
                "id, "
                "template_name, "
                "lesson_type, "
                "tts_provider, "
                "tts_model, "
                "tts_voice, "
                "intro_json"
            )
            .eq(
                "id",
                template_id
            )
            .eq(
                "is_active",
                True
            )
            .limit(1)
            .execute()
        )

    res = supabase_with_retry(
        operation,
        label="GET INTRO TEMPLATE"
    )

    if not res.data:
        raise HTTPException(
            status_code=404,
            detail="Intro template not found"
        )

    return res.data[0]

def replace_intro_variables(
        value,
        replacements: dict
):
    if isinstance(value, str):

        result = value

        for placeholder, replacement in replacements.items():
            result = result.replace(
                placeholder,
                str(replacement or "")
            )

        return result

    if isinstance(value, list):
        return [
            replace_intro_variables(
                item,
                replacements
            )
            for item in value
        ]

    if isinstance(value, dict):
        return {
            key: replace_intro_variables(
                item,
                replacements
            )
            for key, item in value.items()
        }

    return value


def get_learning_lesson(
        lesson_id: int
):

    def operation():

        return (
            sb.table(
                "learning_lessons"
            )
            .select(
                "id, "
                "grade, "
                "subject, "
                "category, "
                "lesson_order, "
                "lesson_name, "
                "lesson_goal, "
                "lesson_content, "
                "teaching_method, "
                "learning_objectives, "
                "xp_reward, "
                "stars_reward, "
                "is_checkpoint, "
                "is_active"
            )
            .eq(
                "id",
                lesson_id
            )
            .eq(
                "is_active",
                True
            )
            .limit(1)
            .execute()
        )

    res = supabase_with_retry(
        operation,
        label="GET LEARNING LESSON"
    )

    if not res.data:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found"
        )

    return res.data[0]



# =====================================================
# IAKIDS_UNIT_LESSON_PROGRESS_V055
# Persistent progress for each internal unit lesson.
# =====================================================

def start_kid_unit_lesson_progress(
        kid_id: str,
        learning_lesson_id: int,
        unit_lesson_id: int
):
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        # Any other lesson that was started but never completed becomes partial.
        active_res = (
            sb.table("kid_unit_lesson_progress")
            .select("id, unit_lesson_id, status")
            .eq("kid_id", kid_id)
            .eq("status", "in_progress")
            .execute()
        )

        for row in (active_res.data or []):
            if int(row.get("unit_lesson_id") or 0) == int(unit_lesson_id):
                continue

            sb.table("kid_unit_lesson_progress").update({
                "status": "partial",
                "last_activity_at": now_iso,
                "updated_at": now_iso
            }).eq("id", row["id"]).execute()

        current_res = (
            sb.table("kid_unit_lesson_progress")
            .select("*")
            .eq("kid_id", kid_id)
            .eq("unit_lesson_id", unit_lesson_id)
            .limit(1)
            .execute()
        )

        if current_res.data:
            current = current_res.data[0]

            # Re-opening a completed lesson is review; never erase completion.
            if current.get("status") == "completed":
                sb.table("kid_unit_lesson_progress").update({
                    "last_activity_at": now_iso,
                    "updated_at": now_iso
                }).eq("id", current["id"]).execute()
                return current

            updated = (
                sb.table("kid_unit_lesson_progress")
                .update({
                    "status": "in_progress",
                    "attempts_count": int(current.get("attempts_count") or 0) + 1,
                    "last_activity_at": now_iso,
                    "updated_at": now_iso
                })
                .eq("id", current["id"])
                .execute()
            )
            return updated.data[0] if updated.data else current

        inserted = (
            sb.table("kid_unit_lesson_progress")
            .insert({
                "kid_id": kid_id,
                "unit_lesson_id": unit_lesson_id,
                "learning_lesson_id": learning_lesson_id,
                "status": "in_progress",
                "progress_percent": 0,
                "current_stage": LESSON_STAGE_INTRO,
                "last_part_number": 1,
                "mastery_score": 0,
                "best_mastery_score": 0,
                "attempts_count": 1,
                "started_at": now_iso,
                "last_activity_at": now_iso,
                "updated_at": now_iso
            })
            .execute()
        )
        return inserted.data[0] if inserted.data else None

    except Exception as e:
        # Keep the existing lesson engine available until the DB migration
        # has been applied in every environment.
        print("UNIT LESSON PROGRESS START WARNING:", repr(e))
        return None

def complete_kid_unit_lesson_progress(
        kid_id: str,
        unit_lesson_id: int,
        mastery_score: int
):
    now_iso = datetime.now(timezone.utc).isoformat()
    final_score = max(0, min(100, int(mastery_score or 0)))

    try:
        current_res = (
            sb.table("kid_unit_lesson_progress")
            .select("id, best_mastery_score")
            .eq("kid_id", kid_id)
            .eq("unit_lesson_id", unit_lesson_id)
            .limit(1)
            .execute()
        )

        if not current_res.data:
            print("UNIT LESSON PROGRESS COMPLETE WARNING: row not found", {
                "kid_id": kid_id,
                "unit_lesson_id": unit_lesson_id
            })
            return None

        current = current_res.data[0]
        best_score = max(
            int(current.get("best_mastery_score") or 0),
            final_score
        )

        updated = (
            sb.table("kid_unit_lesson_progress")
            .update({
                "status": "completed",
                "progress_percent": 100,
                "current_stage": LESSON_STAGE_FINAL_ASSESSMENT,
                "mastery_score": final_score,
                "best_mastery_score": best_score,
                "last_activity_at": now_iso,
                "completed_at": now_iso,
                "updated_at": now_iso
            })
            .eq("id", current["id"])
            .execute()
        )

        return updated.data[0] if updated.data else current

    except Exception as e:
        # Do not break the existing lesson engine if the migration has not
        # reached an environment yet.
        print("UNIT LESSON PROGRESS COMPLETE WARNING:", repr(e))
        return None


def get_or_create_lesson_progress(
        kid_id: str,
        lesson: dict,
        session_id: str | None = None,
        is_lesson_start: bool = False,
        unit_lesson_id: int | None = None
):
    lesson_id = lesson["id"]

    res = (

        sb.table(
            "kid_lesson_progress"
        )

        .select("*")

        .eq(
            "kid_id",
            kid_id
        )

        .eq(
            "lesson_id",
            lesson_id
        )

        .limit(1)

        .execute()

    )

    now = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    # =============================================
    # כבר קיימת התקדמות
    # =============================================

    if res.data:

        progress = res.data[0]

        update_data = {

            "last_session_id":
                session_id,

            "last_activity_at":
                now,

            "updated_at":
                now

        }

        # כל כניסה חדשה לשיעור
        # נחשבת ניסיון/חזרה לשיעור

        if is_lesson_start:
            update_data[
                "attempts_count"
            ] = (

                    int(
                        progress.get(
                            "attempts_count"
                        ) or 0
                    )

                    + 1

            )

        updated = (

            sb.table(
                "kid_lesson_progress"
            )

            .update(
                update_data
            )

            .eq(
                "id",
                progress["id"]
            )

            .execute()

        )

        if updated.data:
            return updated.data[0]

        return progress

    # =============================================
    # שיעור חדש לילד
    # =============================================

    objectives = (

            lesson.get(
                "learning_objectives"
            )

            or []

    )

    objectives_progress = []

    for index, _ in enumerate(
            objectives,
            start=1
    ):
        objectives_progress.append({

            "objective_index":
                index,

            "score":
                0,

            # רמת הקושי הגבוהה ביותר
            # שבה הילד הראה הצלחה
            "highest_difficulty_reached":
                0,

            # מספר אינטראקציות שהיוו
            # הוכחה אמיתית ללמידה
            "evidence_count":
                0,

            # כמה פעמים נצפתה הצלחה
            # בכל רמת קושי
            "evidence_by_level": {

                "1": 0,

                "2": 0,

                "3": 0,

                "4": 0,

                "5": 0

            }

        })

    insert_res = (

        sb.table(
            "kid_lesson_progress"
        )

        .insert({

            "kid_id":
                kid_id,

            "lesson_id":
                lesson_id,

            "current_unit_lesson_id":
                unit_lesson_id,

            "status":
                "in_progress",

            "current_stage":
                LESSON_STAGE_INTRO,

            "progress_percent":
                0,

            "mastery_score":
                0,

            "current_objective_index":
                1,

            "objectives_progress":
                objectives_progress,

            "attempts_count":
                1,

            "total_interactions":
                0,

            "hints_used":
                0,

            "consecutive_successes":
                0,

            "consecutive_failures":
                0,

            "last_session_id":
                session_id,

            "started_at":
                now,

            "last_activity_at":
                now,

            "created_at":
                now,

            "updated_at":
                now

        })

        .execute()

    )

    if not insert_res.data:
        raise RuntimeError(
            "Failed to create "
            "lesson progress"
        )

    return insert_res.data[0]


def get_recent_lesson_history_for_llm(
        kid_id: str,
        lesson_id: int,
        unit_lesson_id: int | None = None,
        part_number: int | None = None,
        limit: int = 8
):
    query = (
        sb.table(
            "kid_lesson_history"
        )
        .select(
            "role, content"
        )
        .eq(
            "kid_id",
            kid_id
        )
        .eq(
            "lesson_id",
            lesson_id
        )
    )

    if unit_lesson_id is not None:
        query = query.eq(
            "unit_lesson_id",
            unit_lesson_id
        )
    if part_number is not None:
        query = query.eq(
            "part_number",
            part_number
        )
    res = (
        query
        .order(
            "created_at",
            desc=True
        )
        .limit(
            limit
        )
        .execute()
    )

    messages = list(
        reversed(
            res.data or []
        )
    )

    return [
        {
            "role":
                message["role"],

            "content":
                message["content"]
        }

        for message in messages

        if message.get(
            "role"
        ) in (
            "user",
            "assistant"
        )
    ]


def should_show_answering_hint(
        kid_id: str,
        max_lessons: int = 3
):
    res = (
        sb.table(
            "kid_lesson_progress"
        )
        .select(
            "lesson_id"
        )
        .eq(
            "kid_id",
            kid_id
        )
        .limit(
            max_lessons + 1
        )
        .execute()
    )

    lessons_started = len(
        res.data or []
    )

    return (
            lessons_started <= max_lessons
    )

def save_lesson_history(
        kid_id: str,
        lesson_id: int,
        unit_lesson_id: int | None,
        session_id: str,
        objective_index: int | None,
        user_content: str | None,
        assistant_content: str,
        evaluation: dict | None,
        sequence_json: list | None,
        part_number: int | None = None
):
    rows = []

    # =============================================
    # תשובת הילד
    # =============================================

    if (
            user_content
            and user_content.strip()
    ):
        rows.append({

            "kid_id":
                kid_id,

            "lesson_id":
                lesson_id,

            "unit_lesson_id":
                unit_lesson_id,

            "session_id":
                session_id,

            "objective_index":
                objective_index,

            "part_number":
                part_number,

            "role":
                "user",

            "content":
                user_content.strip(),

            "evaluation":
                None,

            "sequence_json":
                None

        })

    # =============================================
    # תשובת המורה
    # =============================================

    rows.append({

        "kid_id":
            kid_id,

        "lesson_id":
            lesson_id,

        "unit_lesson_id":
            unit_lesson_id,

        "session_id":
            session_id,

        "objective_index":
            objective_index,

        "part_number":
            part_number,

        "role":
            "assistant",

        "content":
            assistant_content,

        "evaluation":
            evaluation,

        "sequence_json":
            sequence_json

    })

    sb.table(
        "kid_lesson_history"
    ).insert(
        rows
    ).execute()


# =====================================================
# CALCULATE PEDAGOGICAL EVIDENCE
# =====================================================

def calculate_objective_evidence(
        evaluation: dict
):
    response_quality = (
        evaluation.get(
            "response_quality"
        )
    )

    independence_level = (
        evaluation.get(
            "independence_level"
        )
    )

    understanding_level = (
        evaluation.get(
            "understanding_level"
        )
    )

    evidence_strength = (
        evaluation.get(
            "evidence_strength"
        )
    )

    difficulty_level = int(

        evaluation.get(
            "difficulty_level"
        )

        or 1

    )

    # מגבילים תמיד לטווח 1-5

    difficulty_level = max(

        1,

        min(
            difficulty_level,
            5
        )

    )

    evidence_points = 0

    evidence_points += (

        RESPONSE_QUALITY_POINTS
        .get(
            response_quality,
            0
        )

    )

    evidence_points += (

        INDEPENDENCE_POINTS
        .get(
            independence_level,
            0
        )

    )

    evidence_points += (

        UNDERSTANDING_POINTS
        .get(
            understanding_level,
            0
        )

    )

    evidence_points += (

        EVIDENCE_STRENGTH_POINTS
        .get(
            evidence_strength,
            0
        )

    )

    # =================================================
    # חזרה על אותו סוג משימה
    #
    # עדיין נותנת מעט חיזוק,
    # אבל לא ניקוד מלא שוב ושוב
    # =================================================

    if evaluation.get(
            "is_repetition"
    ):
        evidence_points = round(

            evidence_points
            * 0.35

        )

    # =================================================
    # טעות חוזרת
    # =================================================

    if evaluation.get(
            "repeated_mistake"
    ):
        evidence_points -= 3

    # =================================================
    # תשובה שגויה לא יכולה
    # לייצר evidence חיובי
    # =================================================

    if response_quality == "incorrect":
        evidence_points = min(

            evidence_points,

            0

        )

    return {

        "evidence_points":
            evidence_points,

        "difficulty_level":
            difficulty_level,

        "difficulty_cap":

            DIFFICULTY_SCORE_CAPS[
                difficulty_level
            ]

    }


# =====================================================
# APPLY LESSON EVALUATION
# =====================================================

def apply_lesson_evaluation(
        progress: dict,
        lesson: dict,
        evaluation: dict,
        session_id: str
):
    now = datetime.now(
        timezone.utc
    )

    objectives_progress = (

            progress.get(
                "objectives_progress"
            )

            or []

    )

    objective_index = (

            evaluation.get(
                "objective_index"
            )

            or progress.get(
        "current_objective_index"
    )

            or 1

    )

    evidence_result = (

        calculate_objective_evidence(
            evaluation
        )

    )

    evidence_points = (

        evidence_result[
            "evidence_points"
        ]

    )

    difficulty_level = (

        evidence_result[
            "difficulty_level"
        ]

    )

    difficulty_cap = (

        evidence_result[
            "difficulty_cap"
        ]

    )

    # =================================================
    # UPDATE CURRENT OBJECTIVE
    # =================================================

    for objective in (
            objectives_progress
    ):

        if (

                int(
                    objective.get(
                        "objective_index",
                        0
                    )
                )

                !=

                int(
                    objective_index
                )

        ):
            continue

        old_score = int(

            objective.get(
                "score"
            )

            or 0

        )

        highest_difficulty_reached = int(

            objective.get(
                "highest_difficulty_reached"
            )

            or 0

        )

        evidence_count = int(

            objective.get(
                "evidence_count"
            )

            or 0

        )

        evidence_by_level = (

                objective.get(
                    "evidence_by_level"
                )

                or {

                    "1": 0,

                    "2": 0,

                    "3": 0,

                    "4": 0,

                    "5": 0

                }

        )

        # =============================================
        # עדכון מספר ראיות ברמת הקושי
        # =============================================

        level_key = str(
            difficulty_level
        )

        if (

                evaluation.get(
                    "response_quality"
                )

                in (
                "correct",
                "partial"
        )

        ):
            evidence_by_level[
                level_key
            ] = (

                    int(
                        evidence_by_level.get(
                            level_key,
                            0
                        )
                    )

                    + 1

            )

        # =============================================
        # רק הצלחה אמיתית נחשבת
        # כהגעה לרמת קושי
        # =============================================

        if (

                evaluation.get(
                    "response_quality"
                )

                == "correct"

        ):
            highest_difficulty_reached = max(

                highest_difficulty_reached,

                difficulty_level

            )

        # =============================================
        # SCORE UPDATE
        #
        # קודם מחשבים שינוי רגיל
        # =============================================

        proposed_score = (

                old_score
                + evidence_points

        )

        # =============================================
        # CAP
        #
        # לא מאפשרים לעבור את התקרה
        # של רמת הקושי הגבוהה ביותר
        # שהילד באמת הצליח בה.
        # =============================================

        highest_cap = (

            DIFFICULTY_SCORE_CAPS.get(

                highest_difficulty_reached,

                0

            )

        )

        # אם עדיין אין הצלחה מלאה,
        # משתמשים לפחות בתקרת השאלה
        # הנוכחית אבל לא מאפשרים
        # לפרוץ אותה

        effective_cap = max(

            highest_cap,

            difficulty_cap
            if (
                    evaluation.get(
                        "response_quality"
                    )
                    == "correct"
            )
            else old_score

        )

        new_score = max(

            0,

            min(

                100,

                proposed_score,

                effective_cap

            )

        )

        # =============================================
        # ראיה חדשה
        # =============================================

        if (

                evidence_points > 0

                and

                not evaluation.get(
                    "is_repetition"
                )

        ):
            evidence_count += 1

        objective[
            "score"
        ] = new_score

        objective[
            "highest_difficulty_reached"
        ] = highest_difficulty_reached

        objective[
            "evidence_count"
        ] = evidence_count

        objective[
            "evidence_by_level"
        ] = evidence_by_level

        break

    # =================================================
    # ALL OBJECTIVE SCORES
    # =================================================

    scores = [

        int(
            objective.get(
                "score"
            )

            or 0
        )

        for objective
        in objectives_progress

    ]

    # =================================================
    # LESSON PROGRESS
    #
    # ממוצע ציוני כל היעדים
    # =================================================

    if scores:

        progress_percent = round(

            sum(scores)
            /
            len(scores)

        )

    else:

        progress_percent = 0

    # =================================================
    # MASTERY
    #
    # ממוצע של יעדים שכבר התחילו
    # =================================================

    started_scores = [

        score

        for score
        in scores

        if score > 0

    ]

    if started_scores:

        mastery_score = round(

            sum(
                started_scores
            )

            /

            len(
                started_scores
            )

        )

    else:

        mastery_score = 0

    # =================================================
    # NEXT OBJECTIVE
    # =================================================

    next_objective_index = None

    for objective in (
            objectives_progress
    ):

        objective_score = int(

            objective.get(
                "score"
            )

            or 0

        )

        highest_difficulty = int(

            objective.get(
                "highest_difficulty_reached"
            )

            or 0

        )

        if (

                objective_score
                < OBJECTIVE_MASTERY_THRESHOLD

                or

                highest_difficulty
                < 5

        ):
            next_objective_index = (

                objective[
                    "objective_index"
                ]

            )

            break

    # =================================================
    # LESSON COMPLETION
    # =================================================

    lesson_completed = (

            bool(
                objectives_progress
            )

            and

            all(

                int(
                    objective.get(
                        "score"
                    )

                    or 0
                )

                >=

                OBJECTIVE_MASTERY_THRESHOLD

                and

                int(
                    objective.get(
                        "highest_difficulty_reached"
                    )

                    or 0
                )

                >= 5

                for objective
                in objectives_progress

            )

    )

    if lesson_completed:

        status = "completed"

        progress_percent = 100

        next_objective_index = None


    else:

        status = "in_progress"

    # =================================================
    # SUCCESS / FAILURE STREAKS
    # =================================================

    response_quality = (

        evaluation.get(
            "response_quality"
        )

    )

    current_successes = int(

        progress.get(
            "consecutive_successes"
        )

        or 0

    )

    current_failures = int(

        progress.get(
            "consecutive_failures"
        )

        or 0

    )

    if response_quality == "correct":

        consecutive_successes = (

                current_successes
                + 1

        )

        consecutive_failures = 0


    elif response_quality == "incorrect":

        consecutive_successes = 0

        consecutive_failures = (

                current_failures
                + 1

        )


    else:

        consecutive_successes = 0

        consecutive_failures = 0

    # =================================================
    # HINTS
    # =================================================

    hints_used = int(

        progress.get(
            "hints_used"
        )

        or 0

    )

    if evaluation.get(
            "hint_used"
    ):
        hints_used += 1

    # =================================================
    # DATABASE UPDATE
    # =================================================

    update_data = {

        "status":
            status,

        "progress_percent":
            progress_percent,

        "mastery_score":
            mastery_score,

        "current_objective_index":
            next_objective_index,

        "objectives_progress":
            objectives_progress,

        "total_interactions":

            int(
                progress.get(
                    "total_interactions"
                )

                or 0
            )

            + 1,

        "hints_used":
            hints_used,

        "consecutive_successes":
            consecutive_successes,

        "consecutive_failures":
            consecutive_failures,

        "last_evaluation":
            evaluation,

        "last_error_type":
            evaluation.get(
                "identified_difficulty"
            ),

        "last_session_id":
            session_id,

        "last_activity_at":
            now.isoformat(),

        "updated_at":
            now.isoformat()

    }

    # =================================================
    # COMPLETED
    # =================================================

    if lesson_completed:
        update_data[
            "completed_at"
        ] = now.isoformat()

        update_data[
            "xp_earned"
        ] = int(

            lesson.get(
                "xp_reward"
            )

            or 0

        )

        update_data[
            "stars_earned"
        ] = int(

            lesson.get(
                "stars_reward"
            )

            or 0

        )

    updated = (

        sb.table(
            "kid_lesson_progress"
        )

        .update(
            update_data
        )

        .eq(
            "id",
            progress["id"]
        )

        .execute()

    )

    if updated.data:
        return updated.data[0]

    return {

        **progress,

        **update_data

    }


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

    now = datetime.now(
        timezone.utc
    )

    # =============================================
    # FIND ACTIVE SESSION
    # =============================================

    def load_session():

        return (
            sb.table(
                "tutor_sessions"
            )
            .select(
                "id, started_at, last_activity_at, status, "
                "message_count, user_message_count, "
                "assistant_message_count, ai_call_count, "
                "input_tokens, output_tokens, total_tokens, "
                "estimated_cost_usd"
            )
            .eq(
                "user_id",
                user_id
            )
            .eq(
                "kid_id",
                kid_id
            )
            .eq(
                "status",
                "active"
            )
            .order(
                "last_activity_at",
                desc=True
            )
            .limit(1)
            .execute()
        )

    res = supabase_with_retry(
        load_session,
        label="GET TUTOR SESSION"
    )

    # =============================================
    # EXISTING SESSION
    # =============================================

    if res.data:

        session = res.data[0]

        last_activity = (
            parse_supabase_datetime(
                session.get(
                    "last_activity_at"
                )
            )
        )

        if last_activity:

            inactive_time = (
                now - last_activity
            )

            if inactive_time < timedelta(
                    minutes=
                        SESSION_TIMEOUT_MINUTES
            ):

                session["_is_new"] = False

                return session

        # =========================================
        # CLOSE OLD SESSION
        # =========================================

        started_at = (
            parse_supabase_datetime(
                session.get(
                    "started_at"
                )
            )
        )

        duration_seconds = 0

        if started_at and last_activity:

            duration_seconds = max(
                0,
                int(
                    (
                        last_activity
                        - started_at
                    ).total_seconds()
                )
            )

        def close_old_session():

            return (
                sb.table(
                    "tutor_sessions"
                )
                .update({
                    "status":
                        "completed",

                    "ended_at":
                        (
                            last_activity
                            or now
                        ).isoformat(),

                    "duration_seconds":
                        duration_seconds,

                    "updated_at":
                        now.isoformat()
                })
                .eq(
                    "id",
                    session["id"]
                )
                .execute()
            )

        supabase_with_retry(
            close_old_session,
            label="CLOSE TUTOR SESSION"
        )

        try:

            increment_usage_summary(
                user_id=user_id,
                usage_seconds=
                    duration_seconds
            )

        except Exception as usage_error:

            print(
                "SESSION USAGE UPDATE ERROR:",
                repr(usage_error)
            )

    # =============================================
    # CREATE SESSION
    # =============================================

    def create_session():

        return (
            sb.table(
                "tutor_sessions"
            )
            .insert({
                "user_id":
                    user_id,

                "kid_id":
                    kid_id,

                "started_at":
                    now.isoformat(),

                "last_activity_at":
                    now.isoformat(),

                "status":
                    "active",

                "ai_model":
                    "gpt-4o-mini",

                "tts_model":
                    "gemini-3.1-flash-tts-preview"
            })
            .execute()
        )

    new_session_res = (
        supabase_with_retry(
            create_session,
            label="CREATE TUTOR SESSION"
        )
    )

    if not new_session_res.data:

        raise RuntimeError(
            "Failed to create tutor session"
        )

    new_session = (
        new_session_res.data[0]
    )

    new_session["_is_new"] = True

    return new_session


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


def increment_usage_summary(
        user_id: str,
        sessions: int = 0,
        usage_seconds: int = 0,
        ai_calls: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        tts_calls: int = 0,
        tts_seconds: float = 0,
        voice_output_seconds: float = 0,
        image_uploads: int = 0,
        vision_calls: int = 0,
        file_uploads: int = 0,
        file_analysis_calls: int = 0,
        errors: int = 0,
        openai_cost_usd: float = 0,
        gemini_cost_usd: float = 0,
        vision_cost_usd: float = 0,
        realtime_cost_usd: float = 0,
        other_cost_usd: float = 0
):
    """
    עדכון מצטבר של usage_summary.
    מתבצע באמצעות RPC אחד בלבד.
    """

    def operation():
        return (
            sb.rpc(
                "increment_usage_summary",
                {
                    "p_user_id": user_id,

                    "p_sessions": sessions,
                    "p_usage_seconds": usage_seconds,

                    "p_ai_calls": ai_calls,
                    "p_input_tokens": input_tokens,
                    "p_output_tokens": output_tokens,
                    "p_total_tokens": total_tokens,

                    "p_tts_calls": tts_calls,
                    "p_tts_seconds": tts_seconds,
                    "p_voice_output_seconds": voice_output_seconds,

                    "p_image_uploads": image_uploads,
                    "p_vision_calls": vision_calls,

                    "p_file_uploads": file_uploads,
                    "p_file_analysis_calls": file_analysis_calls,

                    "p_errors": errors,

                    "p_openai_cost_usd": openai_cost_usd,
                    "p_gemini_cost_usd": gemini_cost_usd,
                    "p_vision_cost_usd": vision_cost_usd,
                    "p_realtime_cost_usd": realtime_cost_usd,
                    "p_other_cost_usd": other_cost_usd
                }
            )
            .execute()
        )

    return supabase_with_retry(
        operation,
        label="INCREMENT USAGE SUMMARY",
        max_attempts=3
    )


def update_tutor_session_after_chat(
        session: dict,
        total_tokens: int | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float = 0
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
    new_estimated_cost_usd = (
            float(session.get("estimated_cost_usd") or 0)
            + float(cost_usd or 0)
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

        "estimated_cost_usd": new_estimated_cost_usd,

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

    child_gender, gender_instruction = hebrew_gender_rule(child)
    gender_instruction = gender_instruction + "\n" + HEBREW_WRITING_RULES
    child_name = str(child.get("child_name") or "").strip()

    prompt += (
        "\n\nAUTHORITATIVE_CHILD_PROFILE:\n"
        f"child_name: {child_name}\n"
        f"gender: {child_gender}\n"
        f"{gender_instruction}"
    )

    return prompt


def build_structured_lesson_prompt(
        child: dict,
        lesson: dict,
        progress: dict,
        turn_type: str,
        review_mode: bool = False,
        show_answering_hint: bool = False
):
    runtime_context = {

        "lesson_mode":
            (
                "review"
                if review_mode
                else "learning"
            ),

        "review_mode":
            review_mode,

        "turn_type":
            turn_type,

        "show_answering_hint":
            show_answering_hint,

        "child": {

            "name":
                child.get(
                    "child_name"
                ),

            # אצלך age מכיל כרגע
            # את מספר הכיתה 1-6

            "grade":
                child.get(
                    "age"
                ),

            "avatar_key":
                child.get(
                    "avatar_key"
                ),
            "gender":
                hebrew_gender_rule(child)[0],

            "learning_interests":
                child.get(
                    "learning_interests"
                )

                or [],

            "usage_goals":
                child.get(
                    "usage_goals"
                )

                or []

        },

        "lesson": {

            "lesson_id":
                lesson.get(
                    "id"
                ),

            "subject":
                lesson.get(
                    "subject"
                ),

            "category":
                lesson.get(
                    "category"
                ),

            "lesson_name":
                lesson.get(
                    "lesson_name"
                ),

            "lesson_goal":
                lesson.get(
                    "lesson_goal"
                ),

            "lesson_content":
                lesson.get(
                    "lesson_content"
                ),

            "teaching_method":
                lesson.get(
                    "teaching_method"
                ),

            "learning_objectives":
                lesson.get(
                    "learning_objectives"
                )

                or []

        },

        "progress": {

            "status":
                progress.get(
                    "status"
                ),

            "progress_percent":
                progress.get(
                    "progress_percent"
                ),

            "mastery_score":
                progress.get(
                    "mastery_score"
                ),

            "current_objective_index":
                progress.get(
                    "current_objective_index"
                ),

            "objectives_progress":
                progress.get(
                    "objectives_progress"
                )

                or [],

            "hints_used":
                progress.get(
                    "hints_used"
                ),

            "consecutive_successes":
                progress.get(
                    "consecutive_successes"
                ),

            "consecutive_failures":
                progress.get(
                    "consecutive_failures"
                ),

            "last_error_type":
                progress.get(
                    "last_error_type"
                )

        }

    }

    return (

            LESSON_PROMPT_TEMPLATE

            +

            "\n\n"
            "RUNTIME_CONTEXT:\n"

            +

            json.dumps(
                runtime_context,
                ensure_ascii=False
            )
            + "\n\nADDRESSING THE CHILD (Hebrew grammar, mandatory):\n"
            + hebrew_child_prompt_block(child)
    )

def build_universal_unit_lesson_prompt(
        unit_lesson: dict,
        parent_lesson: dict
) -> str:
    prompt = (
        LESSON_INITIAL_PROMPT_TEMPLATE
    )

    lesson_complexity = int(
        unit_lesson.get(
            "lesson_complexity"
        )
        or 2
    )

    max_duration_seconds = int(
        unit_lesson.get(
            "max_duration_seconds"
        )
        or 120
    )

    replacements = {

        "{grade}":
            str(
                parent_lesson.get(
                    "grade"
                )
                or ""
            ),

        "{subject}":
            str(
                parent_lesson.get(
                    "subject"
                )
                or ""
            ),

        "{parent_lesson}":
            str(
                parent_lesson.get(
                    "lesson_name"
                )
                or ""
            ),

        "{unit_name}":
            str(
                unit_lesson.get(
                    "unit_name"
                )
                or ""
            ),

        "{lesson_name}":
            str(
                unit_lesson.get(
                    "lesson_name"
                )
                or ""
            ),

        "{learning_objective}":
            str(
                unit_lesson.get(
                    "learning_objective"
                )
                or ""
            ),

        "{lesson_complexity}":
            str(
                lesson_complexity
            ),

        "{max_duration_seconds}":
            str(
                max_duration_seconds
            )

    }

    for placeholder, value in replacements.items():

        prompt = prompt.replace(
            placeholder,
            value
        )

    return prompt
def build_lesson_expansion_prompt(
        unit_lesson: dict,
        parent_lesson: dict,
        part_number: int,
        previous_parts: list[dict]
) -> str:

    prompt = (
        LESSON_EXPANSION_PROMPT_TEMPLATE
    )

    lesson_complexity = int(
        unit_lesson.get(
            "lesson_complexity"
        )
        or 2
    )

    max_duration_seconds = int(
        unit_lesson.get(
            "max_duration_seconds"
        )
        or 120
    )

    previous_parts_text = "\n\n".join(
        [
            (
                f"Part {item['part_number']}:\n"
                f"Explanation:\n"
                f"{item['explanation']}\n\n"
                f"Question:\n"
                f"{item['question']}"
            )
            for item in previous_parts
        ]
    )

    replacements = {

        "{grade}":
            str(
                parent_lesson.get(
                    "grade"
                )
                or ""
            ),

        "{subject}":
            str(
                parent_lesson.get(
                    "subject"
                )
                or ""
            ),

        "{parent_lesson}":
            str(
                parent_lesson.get(
                    "lesson_name"
                )
                or ""
            ),

        "{lesson_name}":
            str(
                unit_lesson.get(
                    "lesson_name"
                )
                or ""
            ),

        "{learning_objective}":
            str(
                unit_lesson.get(
                    "learning_objective"
                )
                or ""
            ),

        "{lesson_complexity}":
            str(
                lesson_complexity
            ),

        "{max_duration_seconds}":
            str(
                max_duration_seconds
            ),

        "{part_number}":
            str(
                part_number
            ),

        "{previous_parts}":
            previous_parts_text
    }

    for placeholder, value in replacements.items():
        prompt = prompt.replace(
            placeholder,
            value
        )

    return prompt

def build_lesson_director_prompt(
        lesson_text: str
) -> str:

    return (
        LESSON_DIRECTOR_PROMPT_TEMPLATE
        .replace(
            "{lesson_text}",
            lesson_text
        )
    )


# =====================================================
# LESSON DIRECTOR — validation + single entry point
#
# Bug history (2026-09-01 → 2026-09-15): the prompt lost
# its {lesson_text} placeholder and Part 1 sent the
# director only the QUESTION as user message, so the
# director segmented the question into "explanation"
# segments (14/15 prod lessons). Every part now goes
# through direct_lesson_part(), which always hands the
# explanation to the model and refuses question-like or
# foreign segments (retry once, then deterministic
# sentence split of the teacher's explanation).
# =====================================================

_LESSON_DIRECTIVE_PREFIXES = (
    "הסבירו", "הסבר", "הסבירי", "תארו", "תאר", "תארי",
    "כיצד", "איך", "מדוע", "למה", "חשבו", "חשוב", "חשבי",
    "ענו", "ענה", "עני", "נסו", "נסה", "נסי", "כתבו", "כתוב", "כתבי",
    "סדרו", "מצאו", "ציינו", "הציעו", "בדקו", "מה ", "מי ", "איזה", "אילו", "האם"
)


def _normalize_lesson_text(text: str) -> str:
    return re.sub(r"[^\w]", "", str(text or ""))


def _content_words(text: str) -> set:
    return {
        w for w in re.findall(r"[\w']+", str(text or ""))
        if len(w) > 2
    }


def find_invalid_lesson_segments(
        segments: list,
        question_text: str,
        explanation_text: str
) -> list:
    """Return [(index, reason, text)] for segments that must not be read to the child."""
    problems = []
    q_norm = _normalize_lesson_text(question_text)
    expl_words = _content_words(explanation_text)
    for i, seg in enumerate(segments):
        text = str(seg or "").strip()
        if not text:
            problems.append((i, "empty", text))
            continue
        norm = _normalize_lesson_text(text)
        if len(norm) > 6 and norm in q_norm:
            problems.append((i, "copied_from_question", text))
            continue
        why = lq.question_segment_problem(text)      # directive / short question; rhetorical ok
        if why and why != "empty":
            problems.append((i, why, text))
            continue
        words = _content_words(text)
        if expl_words and len(words) >= 3:
            overlap = len(words & expl_words) / len(words)
            if overlap < 0.4:
                problems.append((i, "not_from_explanation", text))
    return problems


def fallback_lesson_segments(explanation_text: str) -> list:
    """Deterministic split of the teacher's explanation into sentences."""
    text = re.sub(r"\s+", " ", str(explanation_text or "")).strip()
    parts = re.split(r"(?<=[.!:])\s+(?=\S)", text)
    out = []
    for s in parts:
        s = s.strip()
        if not s:
            continue
        if out and len(s) < 25:
            out[-1] = (out[-1] + " " + s).strip()
        else:
            out.append(s)
    return [{"text": s} for s in out] or [{"text": text}]


_GENDERED_2ND_PERSON = re.compile(
    r"(?<![\w\u0590-\u05FF])(אתה|שלך|שלךְ|תוכל|תוכלי|נסי|חשבי|כתבי|תארי|הסבירי|תנסה|תנסי|תחשוב|תחשבי|"
    r"תסתכל|תסתכלי|תזכור|תזכרי|תוכלו?\s+לבד|בעצמך|מוכנה|מוכן\?)(?![\w\u0590-\u05FF])"
)


def warn_if_gendered_lesson_text(text: str, label: str, unit_lesson_id=None):
    """A shared lesson must not address one child in masculine/feminine singular.
    Conservative word list (no 'את' — it is also the object marker); logs only."""
    hits = _GENDERED_2ND_PERSON.findall(str(text or ""))
    if hits:
        print("LESSON TEXT GENDERED 2ND PERSON (shared lesson should be neutral):",
              {"unit_lesson_id": unit_lesson_id, "where": label, "hits": hits[:6]})
    return hits


async def direct_lesson_part(
        explanation: str,
        question: str,
        part_number: int,
        unit_lesson_id=None
):
    """Segment ONE lesson part. Returns (part_dict, first_completion).

    part_dict = {"lesson": [{"text": ...}], "question": {"text": question}}.
    The question is owned by the teacher and is never taken from the director.
    """
    explanation = str(explanation or "").strip()
    question = str(question or "").strip()
    warn_if_gendered_lesson_text(explanation, f"part{part_number}.explanation", unit_lesson_id)
    warn_if_gendered_lesson_text(question, f"part{part_number}.question", unit_lesson_id)
    system_prompt = build_lesson_director_prompt(
        lesson_text=explanation
    )
    user_content = explanation
    first_completion = None
    for attempt in (1, 2):
        completion = await aclient.beta.chat.completions.parse(
            model=UNIVERSAL_LESSON_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format=DirectedLessonUnitResponse
        )
        if first_completion is None:
            first_completion = completion
        data = completion.choices[0].message.parsed
        segments = (
            [s.text for s in data.lesson]
            if data and data.lesson else []
        )
        problems = find_invalid_lesson_segments(
            segments, question, explanation
        )
        if segments and not problems:
            print(
                "LESSON DIRECTOR OK",
                {
                    "unit_lesson_id": unit_lesson_id,
                    "part_number": part_number,
                    "attempt": attempt,
                    "segments": len(segments)
                }
            )
            return (
                {
                    "lesson": [{"text": s.strip()} for s in segments],
                    "question": {"text": question}
                },
                first_completion
            )
        print(
            "LESSON DIRECTOR REJECTED",
            {
                "unit_lesson_id": unit_lesson_id,
                "part_number": part_number,
                "attempt": attempt,
                "segments": len(segments),
                "problems": [(i, r, t[:80]) for i, r, t in problems][:8]
            }
        )
        bad_lines = "\n".join(
            f"- {t}" for _, _, t in problems if t
        )
        user_content = (
            explanation
            + "\n\n---\n"
            "הניסיון הקודם נדחה. המקטעים הבאים אסורים "
            "(שאלה, הוראה לתלמיד, או טקסט שאינו מתוך ההסבר):\n"
            + bad_lines
            + "\nחלקו מחדש אך ורק את טקסט ההסבר שלמעלה. "
            "אל תכללו את השאלה או חלק ממנה בתוך lesson."
        )
    print(
        "LESSON DIRECTOR FALLBACK (sentence split)",
        {"unit_lesson_id": unit_lesson_id, "part_number": part_number}
    )
    return (
        {
            "lesson": fallback_lesson_segments(explanation),
            "question": {"text": question}
        },
        first_completion
    )


def build_visual_director_prompt(
        unit_lesson: dict,
        parent_lesson: dict,
        lesson_text: str,
        structured_lesson: dict
) -> str:

    runtime_context = {

        "grade":
            parent_lesson.get(
                "grade"
            ),

        "subject":
            parent_lesson.get(
                "subject"
            ),

        "main_topic":
            parent_lesson.get(
                "lesson_name"
            ),

        "unit_name":
            unit_lesson.get(
                "unit_name"
            ),

        "lesson_name":
            unit_lesson.get(
                "lesson_name"
            ),

        "learning_objective":
            unit_lesson.get(
                "learning_objective"
            ),

        "lesson_text":
            lesson_text,

        "structured_lesson":
            structured_lesson
    }

    return (
        VISUAL_DIRECTOR_PROMPT_TEMPLATE
        + "\n\n"
        + "RUNTIME_CONTEXT:\n"
        + json.dumps(
            runtime_context,
            ensure_ascii=False,
            indent=2
        )
    )

def build_lesson_transition_prompt(
        unit_lesson: dict,
        parent_lesson: dict,
        part_1: dict,
        part_2: dict
) -> str:

    runtime_context = {

        "grade":
            parent_lesson.get(
                "grade"
            ),

        "subject":
            parent_lesson.get(
                "subject"
            ),

        "lesson_name":
            unit_lesson.get(
                "lesson_name"
            ),

        "learning_objective":
            unit_lesson.get(
                "learning_objective"
            ),

        "part_1":
            part_1,

        "part_2":
            part_2
    }

    return (
        LESSON_TRANSITION_PROMPT_TEMPLATE
        + "\n\n"
        + "RUNTIME_CONTEXT:\n"
        + json.dumps(
            runtime_context,
            ensure_ascii=False,
            indent=2
        )
    )

async def regenerate_lesson_transition_only(
        unit_lesson: dict,
        parent_lesson: dict
) -> dict:

    generated_json = (
        unit_lesson.get(
            "generated_lesson_json"
        )
        or {}
    )

    structured_lesson = (
        generated_json.get(
            "structured_lesson"
        )
        or {}
    )

    part_1 = (
        structured_lesson.get(
            "part_1"
        )
        or {}
    )

    part_2 = (
        structured_lesson.get(
            "part_2"
        )
        or {}
    )

    if not part_1 or not part_2:
        raise RuntimeError(
            "Cannot regenerate transition: "
            "Part 1 or Part 2 is missing"
        )

    transition_prompt = (
        build_lesson_transition_prompt(
            unit_lesson=
                unit_lesson,

            parent_lesson=
                parent_lesson,

            part_1=
                part_1,

            part_2=
                part_2
        )
    )

    print(
        "========== TRANSITION ONLY REGENERATION START ==========",
        {
            "unit_lesson_id":
                unit_lesson["id"]
        }
    )

    # =============================================
    # HARD SPEECH WORD COUNT
    #
    # לא סומכים רק על ה-Prompt.
    # ה-Backend עצמו בודק שה-speech
    # באמת מכיל 36-40 מילים.
    # =============================================

    MIN_TRANSITION_WORDS = 36
    MAX_TRANSITION_WORDS = 40
    MAX_TRANSITION_ATTEMPTS = 4

    lesson_transition = None

    for attempt in range(
        1,
        MAX_TRANSITION_ATTEMPTS + 1
    ):

        print(
            "TRANSITION GENERATION ATTEMPT:",
            {
                "unit_lesson_id":
                    unit_lesson["id"],

                "attempt":
                    attempt,

                "max_attempts":
                    MAX_TRANSITION_ATTEMPTS
            }
        )

        transition_completion = (await (
            aclient.beta.chat.completions.parse(

                model=
                    DEFAULT_OPENAI_MODEL,

                messages=[
                    {
                        "role":
                            "system",

                        "content":
                            transition_prompt
                    },

                    {
                        "role":
                            "user",

                        "content":
                            (
                                "Create the universal transition "
                                "between Part 1 and Part 2. "

                                "IMPORTANT HARD REQUIREMENT: "
                                "The Hebrew speech field MUST contain "
                                "between 36 and 40 Hebrew words. "

                                "Count the words before returning. "

                                "If the speech has fewer than 36 words, "
                                "expand it naturally. "

                                "If the speech has more than 40 words, "
                                "rewrite it naturally. "

                                "Do not return the response until "
                                "the speech contains 36-40 words. "

                                "Return only the required structure."
                            )
                    }
                ],

                response_format=
                    LessonTransitionResponse
            )
        ))

        transition_data = (
            transition_completion
            .choices[0]
            .message
            .parsed
        )

        if not transition_data:

            print(
                "TRANSITION ATTEMPT RETURNED NO DATA:",
                {
                    "unit_lesson_id":
                        unit_lesson["id"],

                    "attempt":
                        attempt
                }
            )

            continue

        candidate_transition = (
            transition_data
            .model_dump()
        )

        candidate_speech = str(
            candidate_transition.get(
                "speech"
            )
            or ""
        ).strip()

        word_count = len(
            candidate_speech.split()
        )

        print(
            "TRANSITION WORD COUNT CHECK:",
            {
                "unit_lesson_id":
                    unit_lesson["id"],

                "attempt":
                    attempt,

                "word_count":
                    word_count,

                "min_words":
                    MIN_TRANSITION_WORDS,

                "max_words":
                    MAX_TRANSITION_WORDS,

                "speech":
                    candidate_speech
            }
        )

        # =========================================
        # VALID RESULT
        # =========================================

        if (
            MIN_TRANSITION_WORDS
            <= word_count
            <= MAX_TRANSITION_WORDS
        ):

            lesson_transition = (
                candidate_transition
            )

            print(
                "TRANSITION WORD COUNT VALID:",
                {
                    "unit_lesson_id":
                        unit_lesson["id"],

                    "attempt":
                        attempt,

                    "word_count":
                        word_count
                }
            )

            break

        # =========================================
        # INVALID RESULT -> RETRY
        # =========================================

        print(
            "TRANSITION WORD COUNT INVALID — RETRY:",
            {
                "unit_lesson_id":
                    unit_lesson["id"],

                "attempt":
                    attempt,

                "word_count":
                    word_count
            }
        )

    # =============================================
    # NO VALID RESULT AFTER RETRIES
    # =============================================

    if lesson_transition is None:

        print(
            "TRANSITION WORD COUNT FALLBACK:",
            {
                "unit_lesson_id":
                    unit_lesson["id"],

                "message":
                    (
                        "No 36-40 word result found. "
                        "Using last generated transition."
                    )
            }
        )

        if not candidate_transition:
            raise RuntimeError(
                "Transition Director returned "
                "no usable transition"
            )

        lesson_transition = (
            candidate_transition
        )

    # =============================================
    # FINAL RESULT
    # =============================================

    final_speech = str(
        lesson_transition.get(
            "speech"
        )
        or ""
    ).strip()

    final_word_count = len(
        final_speech.split()
    )

    print(
        "========== TRANSITION ONLY REGENERATION RESULT =========="
    )

    print(
        json.dumps(
            lesson_transition,
            ensure_ascii=False,
            indent=2
        )
    )

    print(
        "========== TRANSITION FINAL WORD COUNT ==========",
        {
            "unit_lesson_id":
                unit_lesson["id"],

            "word_count":
                final_word_count,

            "speech":
                final_speech
        }
    )

    return lesson_transition

def build_segment_visual_fallback_prompt(
        unit_lesson: dict,
        parent_lesson: dict,
        segment_text: str,
        segment_index: int
) -> str:

    grade = str(
        parent_lesson.get("grade")
        or ""
    )

    subject = str(
        parent_lesson.get("subject")
        or ""
    )

    main_topic = str(
        parent_lesson.get("lesson_name")
        or ""
    )

    unit_name = str(
        unit_lesson.get("unit_name")
        or ""
    )

    lesson_name = str(
        unit_lesson.get("lesson_name")
        or ""
    )

    learning_objective = str(
        unit_lesson.get("learning_objective")
        or ""
    )

    return f"""
Create one premium educational 16:9 illustration
for segment {segment_index} of a school lesson.

CURRICULUM CONTEXT:

Grade: {grade}
Subject: {subject}
Main topic: {main_topic}
Unit: {unit_name}
Lesson: {lesson_name}
Learning objective: {learning_objective}

EXACT LESSON SEGMENT:

{segment_text}

VISUAL GOAL:

Translate the educational meaning of this exact segment
into one clear visual scene.

The image must help the student understand this segment
while listening to its corresponding audio.

Use the full curriculum context.
Do not interpret isolated keywords.

REQUIREMENTS:

- educationally accurate
- appropriate for grade {grade}
- premium modern educational illustration
- 16:9 landscape composition
- one clear educational focus
- visually rich but easy to understand
- maintain continuity with the lesson context
- no written text
- no labels
- no captions
- no logos
- no watermark
- no UI elements
- no title cards
""".strip()

def normalize_visual_plan_to_segments(
        visual_plan: dict,
        structured_lesson: dict,
        unit_lesson: dict,
        parent_lesson: dict
) -> dict:

    lesson_parts = (
        structured_lesson.get(
            "parts"
        )
        or []
    )

    # Legacy fallback for old cached lessons.
    if not lesson_parts:

        lesson_parts = [
            {
                "part_number": 1,

                "lesson":
                    structured_lesson.get(
                        "lesson"
                    )
                    or [],

                "question":
                    structured_lesson.get(
                        "question"
                    )
                    or {}
            }
        ]

    raw_visuals = (
        visual_plan.get(
            "visuals"
        )
        or []
    )

    normalized_visuals = []

    total_segments = 0

    for lesson_part in lesson_parts:

        if not isinstance(
                lesson_part,
                dict
        ):
            continue

        total_segments += len(
            lesson_part.get(
                "lesson"
            )
            or []
        )

    print(
        "VISUAL PLAN NORMALIZATION START:",
        {
            "parts_count":
                len(
                    lesson_parts
                ),

            "segments_count":
                total_segments,

            "director_visuals_count":
                len(
                    raw_visuals
                )
        }
    )

    # =============================================
    # NORMALIZE EACH LESSON PART
    # =============================================

    for fallback_part_number, lesson_part in enumerate(
            lesson_parts,
            start=1
    ):

        if not isinstance(
                lesson_part,
                dict
        ):
            continue

        part_number = int(
            lesson_part.get(
                "part_number"
            )
            or fallback_part_number
        )

        segments = (
            lesson_part.get(
                "lesson"
            )
            or []
        )

        print(
            "VISUAL PLAN PART START:",
            {
                "part_number":
                    part_number,

                "segments_count":
                    len(
                        segments
                    )
            }
        )

        for segment_index, segment in enumerate(
                segments,
                start=1
        ):

            if not isinstance(
                    segment,
                    dict
            ):
                continue

            segment_text = str(
                segment.get(
                    "text"
                )
                or ""
            ).strip()

            if not segment_text:
                continue

            # =========================================
            # FIND DIRECTOR VISUAL BY PART + ORDER
            # =========================================

            director_visual = None

            for item in raw_visuals:

                if not isinstance(
                        item,
                        dict
                ):
                    continue

                try:
                    item_part_number = int(
                        item.get(
                            "part_number"
                        )
                        or 1
                    )
                except Exception:
                    item_part_number = 1

                try:
                    item_order = int(
                        item.get(
                            "order"
                        )
                        or 0
                    )
                except Exception:
                    item_order = 0

                if (
                    item_part_number == part_number
                    and
                    item_order == segment_index
                ):
                    director_visual = item
                    break

            # =========================================
            # GENERATION PROMPT
            # =========================================

            generation_prompt = ""

            visual_goal = (
                f"Help the student understand "
                f"part {part_number}, "
                f"lesson segment {segment_index}."
            )

            if director_visual:

                generation_prompt = str(
                    director_visual.get(
                        "generation_prompt"
                    )
                    or ""
                ).strip()

                visual_goal = str(
                    director_visual.get(
                        "visual_goal"
                    )
                    or visual_goal
                ).strip()

            # =========================================
            # FALLBACK PROMPT
            # =========================================

            if not generation_prompt:

                print(
                    "VISUAL DIRECTOR MISSING SEGMENT:",
                    {
                        "part_number":
                            part_number,

                        "segment_index":
                            segment_index,

                        "segment_text":
                            segment_text
                    }
                )

                generation_prompt = (
                    build_segment_visual_fallback_prompt(
                        unit_lesson=
                            unit_lesson,

                        parent_lesson=
                            parent_lesson,

                        segment_text=
                            segment_text,

                        segment_index=
                            segment_index
                    )
                )

            # =========================================
            # TRIGGER
            # =========================================

            words = (
                segment_text
                .replace(
                    "\n",
                    " "
                )
                .split()
            )

            trigger_text = " ".join(
                words[:6]
            )

            # =========================================
            # ONE ENTRY PER SEGMENT, BUT NOT ONE IMAGE PER SEGMENT (2026-09-16)
            # The director marks segments that continue the same idea with
            # reuse_previous; they point at the previous image (reuse_of) and
            # no image is generated for them. The player still maps
            # segment N -> entry N, so nothing changes on the frontend.
            # =========================================
            reuse_of = None
            if VISUAL_REUSE and director_visual and director_visual.get("reuse_previous") and segment_index > 1:
                prev = next((v for v in reversed(normalized_visuals) if v.get("part_number") == part_number), None)
                if prev:
                    reuse_of = int(prev.get("reuse_of") or prev.get("order"))
                    generation_prompt = prev.get("generation_prompt") or generation_prompt
            normalized_visuals.append(
                {
                    "part_number":
                        part_number,
                    "order":
                        segment_index,
                    "reuse_of":
                        reuse_of,

                    "trigger_text":
                        trigger_text,

                    "type":
                        "image",

                    "role":
                        "lesson_segment",

                    "visual_goal":
                        visual_goal,

                    "source_text":
                        segment_text,

                    "generation_prompt":
                        generation_prompt
                }
            )

        # =============================================
        # IMAGE BUDGET (deterministic, 2026-09-16)
        # The director's reuse_previous flag swings between 0% and 90%, so the
        # budget decides: ceil(S * VISUAL_NEW_RATIO) new images per part (min
        # VISUAL_MIN_NEW), given to the segments whose prompts differ most from
        # the previous one; the rest reuse the previous image.
        # =============================================
        if VISUAL_REUSE:
            part_entries = [v for v in normalized_visuals if v.get("part_number") == part_number]
            flags = []
            for v in part_entries:
                dv = next((it for it in raw_visuals if isinstance(it, dict) and int(it.get("part_number") or 1) == part_number and int(it.get("order") or 0) == int(v.get("order") or 0)), None)
                flags.append(bool(dv.get("reuse_previous")) if dv else False)
            lq.enforce_image_budget(part_entries, VISUAL_NEW_RATIO, VISUAL_MIN_NEW, flags)
            print("VISUAL IMAGE BUDGET:", {"part_number": part_number, "segments": len(part_entries),
                  "new_images": sum(1 for v in part_entries if not v.get("reuse_of")),
                  "reused": sum(1 for v in part_entries if v.get("reuse_of")),
                  "model_said_reuse": sum(flags)})

        # =============================================
        # PART QUESTION VISUAL
        # =============================================

        question = (
            lesson_part.get(
                "question"
            )
            or {}
        )

        question_text = str(
            question.get(
                "text"
            )
            or ""
        ).strip()

        if question_text:

            question_visual_order = (
                len(
                    segments
                )
                + 1
            )

            question_generation_prompt = (
                build_segment_visual_fallback_prompt(
                    unit_lesson=
                        unit_lesson,

                    parent_lesson=
                        parent_lesson,

                    segment_text=
                        question_text,

                    segment_index=
                        question_visual_order
                )
            )

            question_words = (
                question_text
                .replace(
                    "\n",
                    " "
                )
                .split()
            )

            question_trigger_text = " ".join(
                question_words[:6]
            )

            normalized_visuals.append(
                {
                    "part_number":
                        part_number,

                    "order":
                        question_visual_order,

                    "trigger_text":
                        question_trigger_text,

                    "type":
                        "image",

                    "role":
                        "question",

                    "visual_goal":
                        (
                            f"Visually support the "
                            f"comprehension question "
                            f"for part {part_number}."
                        ),

                    "source_text":
                        question_text,

                    "generation_prompt":
                        question_generation_prompt
                }
            )

            print(
                "PART QUESTION VISUAL ADDED:",
                {
                    "part_number":
                        part_number,

                    "order":
                        question_visual_order,

                    "question":
                        question_text
                }
            )

    # =============================================
    # FINAL SORT
    # =============================================

    normalized_visuals.sort(
        key=lambda item: (
            int(
                item.get(
                    "part_number"
                )
                or 1
            ),
            int(
                item.get(
                    "order"
                )
                or 0
            )
        )
    )

    result = {
        "version":
            int(
                visual_plan.get(
                    "version"
                )
                or 1
            ),

        "visuals":
            normalized_visuals
    }

    print(
        "VISUAL PLAN NORMALIZATION DONE:",
        {
            "parts_count":
                len(
                    lesson_parts
                ),

            "segments_count":
                total_segments,

            "visuals_count":
                len(
                    normalized_visuals
                ),

            "visual_keys":
                [
                    {
                        "part_number":
                            item[
                                "part_number"
                            ],

                        "order":
                            item[
                                "order"
                            ],

                        "role":
                            item.get(
                                "role"
                            )
                    }
                    for item
                    in normalized_visuals
                ]
        }
    )

    return result

def normalize_universal_lesson_visuals(
        sequence: list[TutorAction]
) -> list[TutorAction]:

    normalized_sequence = []

    visual_count = 0

    max_visual_cards = 2

    for action in sequence:

        # כל פעולה רגילה נשמרת
        if action.type != "visual_card":

            normalized_sequence.append(
                action
            )

            continue


        # מגבילים לשתי המחשות בשיעור
        if visual_count >= max_visual_cards:
            continue


        title = (
            action.title
            or ""
        ).strip()


        raw_items = (
            action.items
            or []
        )


        clean_items = []

        for item in raw_items:

            clean_item = str(
                item
                or ""
            ).strip()

            if not clean_item:
                continue

            if clean_item in clean_items:
                continue

            clean_items.append(
                clean_item
            )


        # כרטיס לא תקין לא נכנס לרצף
        if not title:
            continue

        if len(clean_items) < 2:
            continue


        # לא יותר מחמישה פריטים
        clean_items = clean_items[:5]


        normalized_sequence.append(

            TutorAction(
                type="visual_card",
                title=title,
                items=clean_items,
                icon=action.icon
            )

        )

        visual_count += 1


    return normalized_sequence

# =====================================================
# KID PERSONAL MEDIA
# Personal reusable media for paid subscribers
# =====================================================

KID_PERSONAL_MEDIA_BUCKET = (
    "kid-personal-media"
)

KID_PERSONAL_MEDIA_URL_EXPIRY_SECONDS = (
    3600
)

KID_LESSON_INTRO_MEDIA_TYPE = (
    "lesson_intro"
)

KID_LESSON_INTRO_VARIANTS = (
    1,
    2,
    3
)


def is_paid_active_subscription(
        user_id: str
) -> bool:
    """
    מחזיר True רק למשתמש בתשלום
    עם מנוי פעיל ולא מבוטל.
    """

    now_iso = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    res = (
        sb.table(
            "subscriptions"
        )
        .select(
            "plan, "
            "status, "
            "expires_at, "
            "canceled_at"
        )
        .eq(
            "user_id",
            user_id
        )
        .eq(
            "status",
            "active"
        )
        .neq(
            "plan",
            "free"
        )
        .is_(
            "canceled_at",
            "null"
        )
        .limit(1)
        .execute()
    )

    if not res.data:
        return False

    subscription = (
        res.data[0]
    )

    expires_at = (
        subscription.get(
            "expires_at"
        )
    )

    if expires_at:

        expires_dt = (
            parse_supabase_datetime(
                expires_at
            )
        )

        if (
            expires_dt
            and
            expires_dt
            <= datetime.now(
                timezone.utc
            )
        ):
            return False

    return True


def get_kid_lesson_intro_media(
        kid_id: str
) -> list[dict]:

    res = (
        sb.table(
            "kid_personal_media"
        )
        .select(
            "id, "
            "kid_id, "
            "media_type, "
            "variant, "
            "storage_path, "
            "status"
        )
        .eq(
            "kid_id",
            kid_id
        )
        .eq(
            "media_type",
            KID_LESSON_INTRO_MEDIA_TYPE
        )
        .order(
            "variant"
        )
        .execute()
    )

    return (
        res.data
        or []
    )


# =====================================================
# SIGNED URL CACHE
# =====================================================
# Every lesson open used to ask Storage for a fresh signed URL per file: ~17 audio
# segments + ~21 visuals + 3 intro videos, one HTTP call each, per request. Under
# load that was the whole cost of /unit-lesson, /audio, /visuals and /hero-image
# (30 concurrent opens: 17 s, every request finishing together). A signed URL is
# valid for an hour, so it is cached here until five minutes before it expires,
# and the audio segments of a lesson are signed in ONE Storage call (batch API).
import threading as _threading

_SIGNED_URL_CACHE: dict = {}                 # (bucket, path) -> (url, expires_at_monotonic)
_SIGNED_URL_LOCK = _threading.Lock()
SIGNED_URL_CACHE_MARGIN_SECONDS = int(os.getenv("SIGNED_URL_CACHE_MARGIN_SECONDS", "300"))
_SIGNED_URL_CACHE_MAX = 50_000


def _signed_url_from_response(signed_response) -> str | None:
    if isinstance(signed_response, dict):
        return (
            signed_response.get("signedURL")
            or signed_response.get("signedUrl")
            or signed_response.get("signed_url")
        )
    return None


def _signed_cache_get(bucket: str, path: str) -> str | None:
    with _SIGNED_URL_LOCK:
        hit = _SIGNED_URL_CACHE.get((bucket, path))
    if hit and hit[1] > time.monotonic():
        return hit[0]
    return None


def _signed_cache_put(bucket: str, path: str, url: str, expires_in: int):
    ttl = max(30, int(expires_in) - SIGNED_URL_CACHE_MARGIN_SECONDS)
    with _SIGNED_URL_LOCK:
        if len(_SIGNED_URL_CACHE) >= _SIGNED_URL_CACHE_MAX:
            now = time.monotonic()
            for k in [k for k, v in _SIGNED_URL_CACHE.items() if v[1] <= now]:
                _SIGNED_URL_CACHE.pop(k, None)
            if len(_SIGNED_URL_CACHE) >= _SIGNED_URL_CACHE_MAX:
                _SIGNED_URL_CACHE.clear()
        _SIGNED_URL_CACHE[(bucket, path)] = (url, time.monotonic() + ttl)


def signed_url_cached(bucket: str, path: str, expires_in: int) -> str:
    """One signed URL, from cache or from one Storage call. Raises if the file is
    not there (callers use that as the 'not generated yet' signal)."""
    hit = _signed_cache_get(bucket, path)
    if hit:
        return hit
    signed_response = storage_with_retry(
        lambda: sb.storage.from_(bucket).create_signed_url(path, expires_in),
        label="STORAGE SIGN"
    )
    url = _signed_url_from_response(signed_response)
    if not url:
        raise RuntimeError(f"Failed to create signed URL for {bucket}/{path}")
    _signed_cache_put(bucket, path, url, expires_in)
    return url


def signed_urls_cached_batch(bucket: str, paths: list, expires_in: int) -> dict:
    """path -> signed url for every path that exists, misses fetched in ONE call."""
    out = {}
    missing = []
    for p in dict.fromkeys(p for p in paths if p):
        hit = _signed_cache_get(bucket, p)
        if hit:
            out[p] = hit
        else:
            missing.append(p)
    if missing:
        items = storage_with_retry(
            lambda: sb.storage.from_(bucket).create_signed_urls(missing, expires_in),
            label="STORAGE SIGN BATCH"
        ) or []
        for item in items:
            if not isinstance(item, dict) or item.get("error"):
                continue
            url = _signed_url_from_response(item)
            p = str(item.get("path") or "").lstrip("/")
            if url and p:
                _signed_cache_put(bucket, p, url, expires_in)
                out[p] = url
    return out


_GENERATION_LOCKS: dict = {}
_GENERATION_LOCKS_GUARD = _threading.Lock()


def generation_lock(key: str) -> "_threading.Lock":
    """One lock per media key, so 30 children opening the same new lesson trigger
    one generation in this process, not 30 (seen in the 2026-09-14 load test:
    30 parallel hero-image requests -> 30 image generations, 493 MB, 121% CPU)."""
    with _GENERATION_LOCKS_GUARD:
        lock = _GENERATION_LOCKS.get(key)
        if lock is None:
            lock = _GENERATION_LOCKS[key] = _threading.Lock()
        return lock


def create_kid_personal_media_signed_url(
        storage_path: str
) -> str:

    return signed_url_cached(
        KID_PERSONAL_MEDIA_BUCKET,
        storage_path,
        KID_PERSONAL_MEDIA_URL_EXPIRY_SECONDS
    )


def get_ready_kid_lesson_intro_videos(
        kid_id: str
) -> list[dict]:

    media_rows = (
        get_kid_lesson_intro_media(
            kid_id
        )
    )

    ready_videos = []

    for row in media_rows:

        if (
            row.get("status")
            != "ready"
        ):
            continue

        storage_path = str(
            row.get(
                "storage_path"
            )
            or ""
        ).strip()

        if not storage_path:
            continue

        try:

            signed_url = (
                create_kid_personal_media_signed_url(
                    storage_path
                )
            )

        except Exception as e:

            print(
                "KID INTRO SIGNED URL FAILED:",
                {
                    "kid_id":
                        kid_id,

                    "variant":
                        row.get(
                            "variant"
                        ),

                    "storage_path":
                        storage_path,

                    "error":
                        repr(e)
                }
            )

            continue

        ready_videos.append({
            "variant":
                row.get(
                    "variant"
                ),

            "storage_path":
                storage_path,

            "url":
                signed_url
        })

    return ready_videos

def ensure_kid_lesson_intro_rows(
        kid_id: str
) -> list[dict]:

    existing_rows = (
        get_kid_lesson_intro_media(
            kid_id
        )
    )

    existing_variants = {
        int(
            row.get("variant")
            or 0
        )
        for row in existing_rows
    }

    missing_variants = [
        variant
        for variant
        in KID_LESSON_INTRO_VARIANTS
        if variant not in existing_variants
    ]

    if not missing_variants:

        print(
            "KID INTRO ROWS ALREADY EXIST:",
            {
                "kid_id":
                    kid_id,

                "variants":
                    sorted(
                        existing_variants
                    )
            }
        )

        return existing_rows

    now_iso = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    rows_to_insert = []

    for variant in missing_variants:

        rows_to_insert.append({
            "kid_id":
                kid_id,

            "media_type":
                KID_LESSON_INTRO_MEDIA_TYPE,

            "variant":
                variant,

            "storage_path":
                None,

            "status":
                "pending",

            "error_message":
                None,

            "created_at":
                now_iso,

            "updated_at":
                now_iso
        })

    try:

        sb.table(
            "kid_personal_media"
        ).insert(
            rows_to_insert
        ).execute()

        print(
            "KID INTRO PENDING ROWS CREATED:",
            {
                "kid_id":
                    kid_id,

                "variants":
                    missing_variants
            }
        )

    except Exception as e:

        print(
            "KID INTRO ROW INSERT WARNING:",
            {
                "kid_id":
                    kid_id,

                "error":
                    repr(e)
            }
        )

    return (
        get_kid_lesson_intro_media(
            kid_id
        )
    )


# =====================================================
# KID PERSONAL LESSON INTRO VIDEO GENERATION
# =====================================================

def get_kid_lesson_intro_script(
        child: dict,
        variant: int
) -> str:

    child_name = str(
        child.get(
            "child_name"
        )
        or ""
    ).strip()

    gender = str(
        child.get(
            "gender"
        )
        or "male"
    ).strip().lower()

    ready_word = (
        "מוכנה"
        if gender == "female"
        else "מוכן"
    )

    scripts = {

        1:
            (
                f"היי {child_name}! "
                f"איזה כיף שבאת ללמוד איתי."
            ),

        2:
            (
                f"{child_name}, כיף לראות אותך שוב! "
                f"{ready_word} להתחיל?"
            ),

        3:
            (
                f"היי {child_name}! "
                f"בואי נראה מה נלמד היום."
                if gender == "female"
                else
                f"היי {child_name}! "
                f"בוא נראה מה נלמד היום."
            )
    }

    script = str(
        scripts.get(
            variant
        )
        or ""
    ).strip()

    if not script:
        raise RuntimeError(
            f"Missing intro script "
            f"for variant {variant}"
        )

    return script


def download_gemini_video_bytes(
        output_video
) -> bytes:

    if output_video is None:
        raise RuntimeError(
            "Gemini returned no video"
        )

    video_uri = getattr(
        output_video,
        "uri",
        None
    )

    if video_uri:

        file_name = (
            str(video_uri)
            .split("/")[-1]
        )

        file_name = (
            file_name
            .split(":")[0]
            .split("?")[0]
        )

        print(
            "KID INTRO VIDEO WAITING:",
            {
                "file_name":
                    file_name
            }
        )

        video_ready = False

        for _ in range(60):

            file_info = (
                gemini_client
                .files
                .get(
                    name=
                        f"files/{file_name}"
                )
            )

            state = str(
                getattr(
                    getattr(
                        file_info,
                        "state",
                        None
                    ),
                    "name",
                    ""
                )
                or ""
            ).upper()

            if state == "ACTIVE":
                video_ready = True
                break

            if state == "FAILED":
                raise RuntimeError(
                    "Gemini kid intro video "
                    "processing failed"
                )

            time.sleep(5)

        if not video_ready:
            raise RuntimeError(
                "Gemini kid intro video "
                "processing timed out"
            )

        video_bytes = (
            gemini_client
            .files
            .download(
                file=video_uri
            )
        )

    else:

        inline_data = getattr(
            output_video,
            "data",
            None
        )

        if not inline_data:
            raise RuntimeError(
                "Gemini kid intro video "
                "contains no data"
            )

        if isinstance(
                inline_data,
                str
        ):

            video_bytes = (
                base64.b64decode(
                    inline_data
                )
            )

        else:

            video_bytes = bytes(
                inline_data
            )

    if not video_bytes:
        raise RuntimeError(
            "Downloaded kid intro video "
            "is empty"
        )

    return video_bytes


def generate_single_kid_lesson_intro_video(
        child: dict,
        variant: int
):

    kid_id = str(
        child.get("id")
        or ""
    ).strip()

    if not kid_id:
        raise RuntimeError(
            "kid_id is missing"
        )

    media_res = (
        sb.table(
            "kid_personal_media"
        )
        .select("*")
        .eq(
            "kid_id",
            kid_id
        )
        .eq(
            "media_type",
            KID_LESSON_INTRO_MEDIA_TYPE
        )
        .eq(
            "variant",
            variant
        )
        .limit(1)
        .execute()
    )

    if not media_res.data:
        return

    media_row = (
        media_res.data[0]
    )

    current_status = str(
        media_row.get(
            "status"
        )
        or ""
    ).strip()

    if current_status == "ready":
        return

    if current_status == "generating":
        return

    now_iso = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    claim_res = (
        sb.table(
            "kid_personal_media"
        )
        .update({
            "status":
                "generating",

            "error_message":
                None,

            "updated_at":
                now_iso
        })
        .eq(
            "id",
            media_row["id"]
        )
        .eq(
            "status",
            current_status
        )
        .execute()
    )

    if not claim_res.data:
        return

    try:

        script = (
            get_kid_lesson_intro_script(
                child=child,
                variant=variant
            )
        )

        print(
            "========== KID INTRO VIDEO START ==========",
            {
                "kid_id":
                    kid_id,

                "variant":
                    variant,

                "script":
                    script
            }
        )

        teacher_bytes = storage_with_retry(lambda: (
            sb.storage
            .from_(
                LESSON_MEDIA_BUCKET
            )
            .download(
                LESSON_TRANSITION_TEACHER_PATH
            )
        ), label="STORAGE DOWNLOAD")

        if not teacher_bytes:
            raise RuntimeError(
                "Kid intro teacher reference "
                "is missing"
            )

        teacher_b64 = (
            base64.b64encode(
                teacher_bytes
            )
            .decode("utf-8")
        )

        video_prompt = f"""
[# References
<IMAGE_REF_0>@Image1]

Create a short premium personalized educational
welcome video with synchronized spoken audio.

IMAGE_REF_0 shows the fictional,
AI-generated IAKIDS virtual teacher.

Maintain the same fictional teacher design.

The teacher looks directly toward the learner,
smiles naturally and gives a small welcoming gesture.

THE TEACHER MUST SAY EXACTLY THIS HEBREW TEXT:

"{script}"

Speak ONLY this text.

Do not paraphrase.
Do not add words.
Do not remove words.
Do not repeat words.
Do not repeat the child's name.

The spoken language must be Hebrew.

Use natural fluent Hebrew pronunciation.

- premium semi-realistic educational animation
- teacher face clearly visible
- mouth clearly visible while speaking
- natural eye contact
- subtle body movement
- subtle hand gesture
- medium composition
- cinematic soft lighting
- one continuous shot
- synchronized Hebrew spoken audio
- no written text
- no subtitles
- no captions
- no labels
- no logos
- no UI
- no watermark

After the final word the teacher becomes silent.

No additional speech.
No repeated ending.
No invented dialogue.

The final video must contain spoken audio.
""".strip()

        interaction = (
            gemini_client
            .interactions
            .create(

                model=
                    LESSON_TRANSITION_VIDEO_MODEL,

                input=[
                    {
                        "type":
                            "image",

                        "data":
                            teacher_b64,

                        "mime_type":
                            "image/png"
                    },

                    {
                        "type":
                            "text",

                        "text":
                            video_prompt
                    }
                ],

                response_format={
                    "type":
                        "video",

                    "aspect_ratio":
                        "16:9",

                    "resolution":
                        "720p",

                    "delivery":
                        "uri"
                }
            )
        )

        if not getattr(
                interaction,
                "id",
                None
        ):
            raise RuntimeError(
                "Gemini returned no kid intro "
                "interaction id"
            )

        output_video = getattr(
            interaction,
            "output_video",
            None
        )

        video_bytes = (
            download_gemini_video_bytes(
                output_video
            )
        )

        storage_path = (
            f"{kid_id}/"
            f"lesson-intro/"
            f"intro-{variant}.mp4"
        )

        storage_with_retry(lambda: sb.storage.from_(
            KID_PERSONAL_MEDIA_BUCKET
        ).upload(

            path=
                storage_path,

            file=
                video_bytes,

            file_options={
                "content-type":
                    "video/mp4",

                "upsert":
                    "true"
            }
        ), label="STORAGE UPLOAD")

        ready_at = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        sb.table(
            "kid_personal_media"
        ).update({

            "storage_path":
                storage_path,

            "status":
                "ready",

            "error_message":
                None,

            "updated_at":
                ready_at

        }).eq(
            "id",
            media_row["id"]
        ).execute()

        print(
            "========== KID INTRO VIDEO READY ==========",
            {
                "kid_id":
                    kid_id,

                "variant":
                    variant,

                "storage_path":
                    storage_path,

                "bytes":
                    len(video_bytes)
            }
        )

    except Exception as e:

        print(
            "========== KID INTRO VIDEO ERROR ==========",
            {
                "kid_id":
                    kid_id,

                "variant":
                    variant,

                "error":
                    repr(e)
            }
        )

        traceback.print_exc()

        try:

            sb.table(
                "kid_personal_media"
            ).update({

                "status":
                    "failed",

                "error_message":
                    str(e)[:1500],

                "updated_at":
                    datetime
                    .now(timezone.utc)
                    .isoformat()

            }).eq(
                "id",
                media_row["id"]
            ).execute()

        except Exception as update_error:

            print(
                "KID INTRO FAILURE UPDATE ERROR:",
                repr(
                    update_error
                )
            )


def generate_kid_lesson_intro_videos_background(
        child: dict
):

    kid_id = str(
        child.get("id")
        or ""
    ).strip()

    print(
        "========== KID INTRO VIDEOS BACKGROUND START ==========",
        {
            "kid_id":
                kid_id,

            "child_name":
                child.get(
                    "child_name"
                )
        }
    )

    for variant in KID_LESSON_INTRO_VARIANTS:

        generate_single_kid_lesson_intro_video(
            child=child,
            variant=variant
        )

    print(
        "========== KID INTRO VIDEOS BACKGROUND DONE ==========",
        {
            "kid_id":
                kid_id
        }
    )
# =====================================================
# UNIVERSAL LESSON MEDIA
# Shared images / videos for all children
# =====================================================

LESSON_MEDIA_BUCKET = "lesson-media"

LESSON_MEDIA_URL_EXPIRY_SECONDS = int(os.getenv('LESSON_MEDIA_URL_EXPIRY_SECONDS', '14400'))   # 4 h: a lesson tab left open must not 403

# =====================================================
# UNIVERSAL LESSON TRANSITION VIDEO
# =====================================================

LESSON_TRANSITION_VIDEO_GENERATION_ENABLED = False

LESSON_TRANSITION_VIDEO_MODEL = (
    "gemini-omni-1.1-flash"
)

LESSON_TRANSITION_TEACHER_PATH = (
    "shared/teacher/"
    "lesson-teacher-full-body.png"
)

LESSON_TRANSITION_VIDEO_TARGET_SECONDS = 20

# בשלב הראשון נייצר רק Hero Image אחת לכל תת-שיעור
LESSON_MEDIA_HERO_VERSION = 1


def get_lesson_media_storage_path(
        unit_lesson_id: int,
        media_type: str = "hero"
) -> str:
    """
    נתיב קבוע למדיה של תת-שיעור.

    אותו unit_lesson_id תמיד יוביל
    לאותו קובץ, ולכן ילדים אחרים
    יוכלו להשתמש באותה מדיה.
    """

    if media_type == "hero":
        return (
            f"unit_lessons/"
            f"{unit_lesson_id}/"
            f"hero_v{LESSON_MEDIA_HERO_VERSION}.png"
        )

    raise ValueError(
        f"Unsupported lesson media type: "
        f"{media_type}"
    )


def create_lesson_media_signed_url(
        storage_path: str
) -> str:
    """
    יוצר URL זמני לקובץ שכבר נמצא
    ב-Supabase Storage.
    """

    return signed_url_cached(
        LESSON_MEDIA_BUCKET,
        storage_path,
        LESSON_MEDIA_URL_EXPIRY_SECONDS
    )

def get_shared_lesson_transition(
        transition_type: str
) -> dict:

    allowed_transitions = {
        "opening":
            "shared/lesson-transitions/lesson-opening.mp4",

        "middle":
            "shared/lesson-transitions/lesson-middle.mp4",

        "closing":
            "shared/lesson-transitions/lesson-closing.mp4"
    }

    storage_path = (
        allowed_transitions.get(
            transition_type
        )
    )

    if not storage_path:
        raise ValueError(
            f"Unsupported transition type: "
            f"{transition_type}"
        )

    signed_url = (
        create_lesson_media_signed_url(
            storage_path
        )
    )

    return {
        "type":
            transition_type,

        "video": {
            "storage_path":
                storage_path,

            "url":
                signed_url,

            "status":
                "ready"
        },

        "duration_seconds":
            20
    }

def add_transition_video_signed_url(
        transition: dict | None
) -> dict | None:

    if not isinstance(
        transition,
        dict
    ):
        return transition

    video = (
        transition.get(
            "video"
        )
        or {}
    )

    if not isinstance(
        video,
        dict
    ):
        return transition

    storage_path = str(
        video.get(
            "storage_path"
        )
        or ""
    ).strip()

    if not storage_path:

        return transition

    try:

        signed_url = (
            create_lesson_media_signed_url(
                storage_path
            )
        )

    except Exception as e:

        print(
            "TRANSITION VIDEO SIGNED URL FAILED:",
            {
                "storage_path":
                    storage_path,

                "error":
                    repr(e)
            }
        )

        return transition

    return {
        **transition,

        "video": {
            **video,

            "url":
                signed_url,

            "url_expires_in_seconds":
                LESSON_MEDIA_URL_EXPIRY_SECONDS
        }
    }

def build_lesson_hero_image_prompt(
        unit_lesson: dict,
        parent_lesson: dict
) -> str:
    """
    Prompt אוניברסלי לתמונה הראשונה של השיעור.

    אין כאן מידע אישי על הילד.
    לכן התמונה יכולה להישמר ולהיות
    משותפת לכל הילדים שלומדים את אותו שיעור.
    """

    grade = str(
        parent_lesson.get(
            "grade"
        )
        or ""
    ).strip()

    subject = str(
        parent_lesson.get(
            "subject"
        )
        or ""
    ).strip()

    parent_lesson_name = str(
        parent_lesson.get(
            "lesson_name"
        )
        or ""
    ).strip()

    unit_name = str(
        unit_lesson.get(
            "unit_name"
        )
        or ""
    ).strip()

    lesson_name = str(
        unit_lesson.get(
            "lesson_name"
        )
        or ""
    ).strip()

    learning_objective = str(
        unit_lesson.get(
            "learning_objective"
        )
        or ""
    ).strip()

    return f"""
Create one premium educational HERO illustration for a school lesson.

CURRICULUM CONTEXT:
Grade: {grade}
Subject: {subject}
Main topic: {parent_lesson_name}
Unit: {unit_name}
Lesson: {lesson_name}
Learning objective: {learning_objective}

IMPORTANT CONTEXT RULE:
The lesson title must NEVER be interpreted in isolation.

First understand the lesson through its complete curriculum context:
Subject -> Main topic -> Unit -> Lesson -> Learning objective.

The illustration must clearly belong to the MAIN TOPIC and UNIT,
while visually introducing the specific LESSON.

If the lesson title is broad or ambiguous, use the Main topic,
Unit and Learning objective to determine its correct meaning.

For example:
If a lesson is called "What is a system?" and it belongs to a unit
about ecosystems, the image should explain the idea of a system
through an ecological context: living and non-living elements
interacting, influencing and depending on one another.

Do NOT interpret such a lesson as a mechanical system,
computer system, gears, machinery or another unrelated type
of system unless the curriculum context specifically requires it.

VISUAL GOAL:
Create one immediately understandable visual scene that helps
the student intuitively understand the central concept of the lesson
before the full lesson explanation begins.

The image must TEACH the concept visually,
not simply decorate or illustrate the lesson title.

The visual should prioritize the actual educational concept
described by the curriculum context and learning objective.

REQUIREMENTS:
- appropriate for a student in grade {grade}
- educational and scientifically accurate
- one clear central educational concept
- premium modern 3D educational illustration
- visually rich and engaging but not childish
- realistic enough to support learning
- clear visual relationships between important elements
- cinematic soft lighting
- clean professional composition
- suitable for a large lesson presentation area
- landscape composition
- no written text
- no labels
- no captions
- no logos
- no watermark

ABSOLUTELY NO WRITTEN TEXT IN THE IMAGE: do not render the lesson title, the
question, names of animals or any word or letter, in any language. The concept
must be understood from the picture alone. Only universally readable scientific
notation used by the lesson (CO2, H2O, O2, sin, cos, π, √, plain numbers, units) may appear. A poster, a title card, a
labeled chart or a diagram with words is WRONG. Hebrew readers scan right to
left: sequences start on the right. Calm, child-safe, no killing moment.
""".strip()

# =====================================================
# GEMINI LESSON HERO IMAGE
# =====================================================

LESSON_IMAGE_MODEL = (
    "gemini-3.1-flash-lite-image"
)


def generate_lesson_hero_image_bytes(
        prompt: str
) -> tuple[bytes, str]:
    """
    יוצר תמונת Hero אחת דרך Gemini.

    מחזיר:
    - bytes של התמונה
    - MIME type
    """

    clean_prompt = str(
        prompt or ""
    ).strip()

    if not clean_prompt:
        raise RuntimeError(
            "Lesson hero image prompt is empty"
        )

    print(
        "========== LESSON IMAGE GENERATION START ==========",
        {
            "model":
                LESSON_IMAGE_MODEL,

            "prompt_length":
                len(clean_prompt)
        }
    )

    started_at = (
        time.perf_counter()
    )

    response = (
        gemini_client
        .models
        .generate_content(

            model=
                LESSON_IMAGE_MODEL,

            contents=
                clean_prompt,

            config=
            types.GenerateContentConfig(

                response_modalities=[
                    "IMAGE"
                ],

                image_config=
                types.ImageConfig(
                    aspect_ratio="16:9",
                    image_size="1K"
                )
            )
        )
    )

    elapsed_ms = round(
        (
            time.perf_counter()
            - started_at
        )
        * 1000
    )

    print(
        "========== LESSON IMAGE GEMINI RESPONSE ==========",
        {
            "elapsed_ms":
                elapsed_ms
        }
    )

    # =================================================
    # FIND IMAGE PART
    # =================================================

    response_parts = (
        getattr(
            response,
            "parts",
            None
        )
        or []
    )

    for part in response_parts:

        inline_data = getattr(
            part,
            "inline_data",
            None
        )

        if inline_data is None:
            continue

        image_data = getattr(
            inline_data,
            "data",
            None
        )

        if not image_data:
            continue

        mime_type = (
            getattr(
                inline_data,
                "mime_type",
                None
            )
            or
            "image/png"
        )

        # בחלק מגרסאות SDK
        # data מגיע כ-bytes.
        #
        # באחרות הוא יכול להגיע
        # כ-base64 string.
        if isinstance(
                image_data,
                str
        ):

            image_bytes = (
                base64.b64decode(
                    image_data
                )
            )

        else:

            image_bytes = bytes(
                image_data
            )

        if not image_bytes:
            continue

        print(
            "========== LESSON IMAGE GENERATED ==========",
            {
                "elapsed_ms":
                    elapsed_ms,

                "mime_type":
                    mime_type,

                "bytes":
                    len(image_bytes)
            }
        )

        return (
            image_bytes,
            mime_type
        )

    raise RuntimeError(
        "Gemini returned no image data"
    )

def generate_lesson_visual_image_bytes(
        prompt: str,
        reference_image_bytes: bytes | None = None,
        reference_mime_type: str = "image/png"
) -> tuple[bytes, str]:

    clean_prompt = str(
        prompt or ""
    ).strip()

    if not clean_prompt:
        raise RuntimeError(
            "Lesson visual image prompt is empty"
        )

    # =============================================
    # NORMAL FIRST IMAGE
    # =============================================

    if not reference_image_bytes:

        return generate_lesson_hero_image_bytes(
            clean_prompt
        )

    # =============================================
    # REFERENCE-BASED IMAGE GENERATION
    # =============================================

    reference_part = types.Part.from_bytes(
        data=reference_image_bytes,
        mime_type=reference_mime_type
    )

    reference_prompt = f"""
    The attached image is the MASTER STYLE REFERENCE
    for an educational lesson image series.

    You must create a NEW SCENE, but it MUST look like it was
    created by the EXACT SAME illustrator, using the EXACT SAME
    visual medium and rendering technique as the reference image.

    CRITICAL STYLE LOCK:

    The reference image controls HOW the new image looks.
    The CURRENT SCENE controls ONLY WHAT the new image shows.

    DO NOT change the visual medium because of the scene description.

    MATCH THE REFERENCE IMAGE:

    - same premium semi-realistic digital illustration style
    - same illustrated rendering technique
    - same character design language
    - same level of illustrated realism
    - same cinematic lighting style
    - same color palette and color treatment
    - same texture and material treatment
    - same depth and atmosphere
    - same visual detail density
    - same cinematic quality
    - same overall educational production style

    The result must visually belong to the SAME IMAGE SERIES
    as the reference.

    If the reference looks semi-realistic,
    the new image MUST remain semi-realistic.

    If the reference uses realistic materials and lighting,
    preserve those characteristics.

    NEVER convert the scene into:

    - an infographic
    - a diagram
    - a labeled educational chart
    - a technical illustration
    - a poster
    - a textbook page
    - a cartoon
    - flat vector artwork
    - comic-book artwork
    - watercolor
    - a different illustration style

    VERY IMPORTANT:

    Do NOT copy any text, labels or annotations
    that may appear in the scene description.

    ABSOLUTELY NO WRITTEN TEXT IN THE IMAGE. No words, letters, labels, captions or titles
in any language. The ONLY allowed exception: universally readable scientific notation
that the lesson itself uses (chemical formulas such as CO2, H2O, O2; math notation such as
sin, cos, π, √, +, =, x²; plain numbers; units).

READING DIRECTION: Hebrew readers scan right-to-left. If the scene shows a sequence,
chain or process, place the first step on the RIGHT and the last on the LEFT; arrows,
if any, point right-to-left. CHILD SAFETY: calm, no blood, no killing moment, nothing
frightening. Do not depict a single child who could be read as the viewer.

    No:
    - words
    - labels
    - titles
    - captions
    - letters
    - numbers
    - arrows with text
    - annotations
    - logos
    - watermarks
    - readable signs

    When the same bicycle, child, object or environment
    appears again, preserve its established visual identity
    from the reference whenever applicable.

    The composition and action may change completely.
    The STYLE MUST NOT.

    Think of this as another frame from the exact same
    animated educational film.

    CURRENT SCENE CONTENT:

    {clean_prompt}

    Again:
    Use the CURRENT SCENE only to determine WHAT is shown.
    Use the REFERENCE IMAGE to determine HOW everything looks.
    """.strip()

    print(
        "LESSON VISUAL WITH REFERENCE:",
        {
            "prompt_length":
                len(reference_prompt),

            "reference_bytes":
                len(reference_image_bytes)
        }
    )

    started_at = (
        time.perf_counter()
    )

    response = (
        gemini_client
        .models
        .generate_content(

            model=
                LESSON_IMAGE_MODEL,

            contents=[
                reference_part,
                reference_prompt
            ],

            config=
            types.GenerateContentConfig(

                response_modalities=[
                    "IMAGE"
                ],

                image_config=
                types.ImageConfig(
                    aspect_ratio="16:9",
                    image_size="1K"
                )
            )
        )
    )

    elapsed_ms = round(
        (
            time.perf_counter()
            - started_at
        )
        * 1000
    )

    response_parts = (
        getattr(
            response,
            "parts",
            None
        )
        or []
    )

    for part in response_parts:

        inline_data = getattr(
            part,
            "inline_data",
            None
        )

        if inline_data is None:
            continue

        image_data = getattr(
            inline_data,
            "data",
            None
        )

        if not image_data:
            continue

        mime_type = (
            getattr(
                inline_data,
                "mime_type",
                None
            )
            or "image/png"
        )

        if isinstance(
                image_data,
                str
        ):

            image_bytes = (
                base64.b64decode(
                    image_data
                )
            )

        else:

            image_bytes = bytes(
                image_data
            )

        print(
            "LESSON VISUAL REFERENCE IMAGE GENERATED:",
            {
                "elapsed_ms":
                    elapsed_ms,

                "bytes":
                    len(image_bytes),

                "mime_type":
                    mime_type
            }
        )

        return (
            image_bytes,
            mime_type
        )

    raise RuntimeError(
        "Gemini returned no reference-based image data"
    )

# =====================================================
# GENERATE + STORE HERO IMAGE
# =====================================================

_IMAGE_TEXT_RESULTS: dict = {}     # (unit_lesson_id, "v1/part_2/visual_9.png") -> last generation-time check


def _image_text_key(ctx: dict, kind: str) -> str | None:
    if kind == "hero":
        return f"hero_v{LESSON_MEDIA_HERO_VERSION}.png"
    if ctx.get("content_version") and ctx.get("part_number") and ctx.get("order"):
        return f"v{ctx['content_version']}/part_{ctx['part_number']}/visual_{ctx['order']}.png"
    return None


def ensure_no_text_in_image(image_bytes, mime_type, kind, regenerate, **ctx):
    """The prompts forbid text, the model sometimes ignores it. One cheap vision call; on
    readable text, one strict regeneration; the second result is kept either way (logged)."""
    if not IMAGE_TEXT_CHECK:
        return image_bytes, mime_type
    try:
        chk = lq.image_text_check(gemini_client, types, IMAGE_TEXT_CHECK_MODEL, image_bytes, mime_type)
    except Exception as e:
        print("LESSON IMAGE TEXT CHECK FAILED (kept image):", {**ctx, "kind": kind, "error": repr(e)[:160]})
        return image_bytes, mime_type
    if chk.get("has_text") and (chk.get("kind") == "formula" or lq.is_allowed_scientific_text(chk.get("text", ""))):
        chk = dict(chk, has_text=False, allowed=True)      # CO2, H2O, numbers: fine in a shared image
    print("LESSON IMAGE TEXT CHECK:", {**ctx, "kind": kind, **chk})
    key = _image_text_key(ctx, kind)
    if key and ctx.get("unit_lesson_id") is not None:
        _IMAGE_TEXT_RESULTS[(int(ctx["unit_lesson_id"]), key)] = dict(chk)
    if not chk["has_text"]:
        return image_bytes, mime_type
    try:
        image_bytes2, mime2 = regenerate(NO_TEXT_RETRY_SUFFIX)
        chk2 = lq.image_text_check(gemini_client, types, IMAGE_TEXT_CHECK_MODEL, image_bytes2, mime2)
        print("LESSON IMAGE TEXT CHECK (after retry):", {**ctx, "kind": kind, **chk2})
        if key and ctx.get("unit_lesson_id") is not None:
            _IMAGE_TEXT_RESULTS[(int(ctx["unit_lesson_id"]), key)] = dict(chk2, retried=True)
        if not chk2["has_text"] or len(chk2.get("text", "")) <= len(chk.get("text", "")):
            return image_bytes2, mime2
    except Exception as e:
        print("LESSON IMAGE TEXT RETRY FAILED (kept first image):", {**ctx, "kind": kind, "error": repr(e)[:160]})
    return image_bytes, mime_type


def generate_and_store_lesson_hero_image(
        unit_lesson_id: int
) -> dict:
    """
    יוצר Hero Image אוניברסלית
    עבור unit lesson אחד.

    התמונה:
    1. נוצרת דרך Gemini
    2. עולה ל-Supabase Storage
    3. מקבלת Signed URL
    4. מוחזרת כ-metadata

    אין כאן kid_id.
    המדיה שייכת לשיעור עצמו.
    """

    print(
        "LESSON HERO IMAGE START:",
        unit_lesson_id
    )

    # =================================================
    # LOAD UNIT LESSON
    # =================================================

    unit_lesson = get_unit_lesson(
        unit_lesson_id
    )

    # =================================================
    # LOAD PARENT LESSON
    # =================================================

    parent_lesson = (
        get_learning_lesson(
            unit_lesson[
                "learning_lesson_id"
            ]
        )
    )

    # =================================================
    # BUILD EDUCATIONAL PROMPT
    # =================================================

    image_prompt = (
        build_lesson_hero_image_prompt(

            unit_lesson=
                unit_lesson,

            parent_lesson=
                parent_lesson
        )
    )

    print(
        "LESSON HERO IMAGE PROMPT:",
        {
            "unit_lesson_id":
                unit_lesson_id,

            "lesson_name":
                unit_lesson.get(
                    "lesson_name"
                ),

            "prompt":
                image_prompt
        }
    )

    # =================================================
    # GEMINI
    # =================================================

    image_bytes, mime_type = (
        generate_lesson_hero_image_bytes(
            image_prompt
        )
    )
    image_bytes, mime_type = ensure_no_text_in_image(
        image_bytes, mime_type, "hero",
        lambda extra: generate_lesson_hero_image_bytes(image_prompt + extra),
        unit_lesson_id=unit_lesson_id
    )

    # =================================================
    # STORAGE PATH
    # =================================================

    storage_path = (
        get_lesson_media_storage_path(
            unit_lesson_id=
                unit_lesson_id,

            media_type=
                "hero"
        )
    )

    # =================================================
    # UPLOAD TO SUPABASE STORAGE
    # =================================================

    print(
        "LESSON HERO IMAGE UPLOAD:",
        {
            "bucket":
                LESSON_MEDIA_BUCKET,

            "path":
                storage_path,

            "bytes":
                len(image_bytes)
        }
    )

    storage_with_retry(lambda: sb.storage.from_(
        LESSON_MEDIA_BUCKET
    ).upload(

        path=
            storage_path,

        file=
            image_bytes,

        file_options={
            "content-type":
                mime_type,

            # אם אנחנו מייצרים גרסה מחדש,
            # הקובץ הקודם יוחלף.
            "upsert":
                "true"
        }
    ), label="STORAGE UPLOAD")

    # =================================================
    # SIGNED URL
    # =================================================

    signed_url = (
        create_lesson_media_signed_url(
            storage_path
        )
    )

    generated_at = (
        datetime
        .now(timezone.utc)
        .isoformat()
    )

    result = {

        "type":
            "image",

        "role":
            "hero",

        "version":
            LESSON_MEDIA_HERO_VERSION,

        "provider":
            "gemini",

        "model":
            LESSON_IMAGE_MODEL,

        "bucket":
            LESSON_MEDIA_BUCKET,

        "storage_path":
            storage_path,

        "mime_type":
            mime_type,

        "aspect_ratio":
            "16:9",

        "image_size":
            "1K",

        "generated_at":
            generated_at,

        # זה זמני בלבד.
        # את ה-URL עצמו לא נשמור ב-DB.
        "url":
            signed_url,

        "url_expires_in_seconds":
            LESSON_MEDIA_URL_EXPIRY_SECONDS
    }

    print(
        "LESSON HERO IMAGE READY:",
        {
            "unit_lesson_id":
                unit_lesson_id,

            "storage_path":
                storage_path,

            "generated_at":
                generated_at
        }
    )

    return result

# =====================================================
# AI TUTOR NATURAL VOICE - GEMINI TTS
# =====================================================
LESSON_AUDIO_BUCKET = "lesson-audio"
LESSON_AUDIO_URL_EXPIRY_SECONDS = int(os.getenv('LESSON_AUDIO_URL_EXPIRY_SECONDS', '14400'))   # 4 h: a lesson tab left open must not 403

def generate_and_store_lesson_visual_image(
        unit_lesson_id: int,
        content_version: int,
        visual: dict,
        reference_image_bytes: bytes | None = None,
        reference_mime_type: str = "image/png"
) -> dict:

    visual_order = int(
        visual.get("order")
        or 0
    )
    part_number = int(
        visual.get("part_number")
        or 0
    )
    generation_prompt = str(
        visual.get("generation_prompt")
        or ""
    ).strip()

    # =============================================
    # GLOBAL LESSON VISUAL STYLE LOCK
    #
    # חל על visual_1 וגם על כל התמונות שאחריה.
    # visual_1 תקבע את ה-DNA החזותי של השיעור.
    # =============================================

    LESSON_VISUAL_STYLE_LOCK = """
    Create a premium semi-realistic digital educational illustration.

    This image belongs to a high-end educational animated visual series
    for children.

    MANDATORY VISUAL STYLE:

    - premium semi-realistic digital illustration
    - high-end animated educational film quality
    - realistic human and object proportions
    - clearly illustrated, NOT photographic
    - detailed digital painting with polished rendering
    - soft cinematic natural lighting
    - warm, rich but controlled colors
    - subtle depth and atmospheric perspective
    - clean professional composition
    - realistic materials interpreted through illustration
    - expressive but natural characters
    - modern premium educational media aesthetic
    - visually engaging for children without looking childish

    The final result must clearly look like
    a professionally illustrated scene,
    NOT a photograph.

    CHARACTER STYLE:

    When children appear:

    - use relatable school-age children around 10-12 years old
    - natural facial features
    - realistic proportions
    - expressive but believable poses
    - modern everyday clothing
    - friendly and intelligent appearance
    - never exaggerated cartoon proportions

    When the same child appears in later images,
    preserve the child's:

    - approximate face and appearance
    - age
    - hairstyle
    - clothing colors and design
    - body proportions

    OBJECT CONTINUITY:

    When an important object appears again,
    preserve its established visual identity.

    For example, the same bicycle should maintain:

    - frame design
    - frame color
    - wheel style
    - proportions
    - important recognizable details

    VISUAL WORLD:

    All lesson images should feel like consecutive scenes
    from the SAME premium educational animated film.

    They may show different actions, locations, camera angles
    and compositions, but the artistic rendering must remain consistent.

    DO NOT create:

    - photography
    - photorealistic photography
    - stock photography
    - live-action imagery
    - flat cartoons
    - childish cartoons
    - flat vector art
    - infographic
    - diagram
    - technical drawing
    - textbook page
    - educational poster
    - comic-book art
    - watercolor
    - anime
    - 3D infographic
    - labeled educational chart

    ABSOLUTELY NO WRITTEN TEXT INSIDE THE IMAGE.

    Do not include:

    - words
    - labels
    - captions
    - titles
    - letters
    - numbers
    - annotations
    - readable signs
    - logos
    - watermarks
    - arrows containing text

    Educational concepts must be communicated
    through the visual scene itself.

    IMPORTANT:

    ILLUSTRATION STYLE is mandatory.

    Even when the scene describes a realistic situation,
    render it as a premium semi-realistic digital illustration,
    never as a photograph.
    """.strip()

    final_generation_prompt = f"""
    final_generation_prompt = lq.sanitize_generation_prompt(final_generation_prompt)   # never ask the image model for labels/text
    {LESSON_VISUAL_STYLE_LOCK}

    CURRENT EDUCATIONAL SCENE:

    {generation_prompt}
    """.strip()

    trigger_text = str(
        visual.get("trigger_text")
        or ""
    ).strip()
    if not part_number:
        raise RuntimeError(
            "Visual part number is missing"
        )
    if not visual_order:
        raise RuntimeError(
            "Visual order is missing"
        )

    if not generation_prompt:
        raise RuntimeError(
            "Visual generation prompt is missing"
        )

    print(
        "LESSON VISUAL IMAGE START:",
        {
            "unit_lesson_id":
                unit_lesson_id,

            "content_version":
                content_version,

            "part_number":
                part_number,

            "order":
                visual_order,

            "trigger_text":
                trigger_text
        }
    )

    image_bytes, mime_type = (
        generate_lesson_visual_image_bytes(
            final_generation_prompt,
            reference_image_bytes=
            reference_image_bytes,
            reference_mime_type=
            reference_mime_type
        )
    )
    image_bytes, mime_type = ensure_no_text_in_image(
        image_bytes, mime_type, "visual",
        lambda extra: generate_lesson_visual_image_bytes(
            final_generation_prompt + extra,
            reference_image_bytes=reference_image_bytes,
            reference_mime_type=reference_mime_type
        ),
        unit_lesson_id=unit_lesson_id, part_number=part_number, order=visual_order, content_version=content_version
    )

    storage_path = (
        f"unit_lessons/"
        f"{unit_lesson_id}/"
        f"v{content_version}/"
        f"part_{part_number}/"
        f"visual_{visual_order}.png"
    )

    storage_with_retry(lambda: sb.storage.from_(
        LESSON_MEDIA_BUCKET
    ).upload(

        path=
            storage_path,

        file=
            image_bytes,

        file_options={
            "content-type":
                mime_type,

            "upsert":
                "true"
        }
    ), label="STORAGE UPLOAD")

    print(
        "LESSON VISUAL IMAGE STORED:",
        {
            "unit_lesson_id":
                unit_lesson_id,

            "order":
                visual_order,

            "storage_path":
                storage_path
        }
    )

    return {
        "part_number":
            part_number,

        "order":
            visual_order,

        "type":
            "image",

        "trigger_text":
            trigger_text,

        "storage_path":
            storage_path,

        "mime_type":
            mime_type
    }

def generate_all_lesson_visuals_background(
        unit_lesson_id: int
):
    import time
    import traceback

    MAX_VISUAL_RETRIES = 3
    RETRY_DELAY_SECONDS = 3

    try:

        unit_lesson = get_unit_lesson(
            unit_lesson_id
        )

        generated_lesson_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
            or {}
        )

        visual_plan = (
            generated_lesson_json.get(
                "visual_plan"
            )
            or {}
        )

        visuals = (
            visual_plan.get(
                "visuals"
            )
            or []
        )
        visuals = sorted(
            visuals,
            key=lambda item: (
                int(
                    item.get(
                        "part_number"
                    )
                    or 0
                ),
                int(
                    item.get(
                        "order"
                    )
                    or 0
                )
            )
        )
        content_version = int(
            unit_lesson.get(
                "content_version"
            )
            or 1
        )

        if not visuals:

            print(
                "NO VISUALS FOUND IN VISUAL PLAN:",
                unit_lesson_id
            )

            return

        generated_visuals = []
        master_reference_bytes = None
        master_reference_mime_type = "image/png"
        image_visuals = [
            visual
            for visual in visuals
            if isinstance(visual, dict)
            and str(
                visual.get("type") or ""
            ).strip().lower() == "image"
        ]

        structured_lesson = (
            generated_lesson_json.get(
                "structured_lesson"
            )
            or {}
        )

        segments = (
            structured_lesson.get(
                "lesson"
            )
            or []
        )

        print(
            "VISUAL/AUDIO SEGMENT CHECK:",
            {
                "unit_lesson_id":
                    unit_lesson_id,

                "segments_count":
                    len(segments),

                "visuals_count":
                    len(image_visuals)
            }
        )

        if (
            len(image_visuals)
            !=
            len(segments)
        ):

            print(
                "CRITICAL VISUAL COUNT MISMATCH:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "segments_count":
                        len(segments),

                    "visuals_count":
                        len(image_visuals)
                }
            )

        print(
            "LESSON VISUAL GENERATION START:",
            {
                "unit_lesson_id":
                    unit_lesson_id,

                "content_version":
                    content_version,

                "planned_images":
                    len(image_visuals)
            }
        )

        # =====================================================
        # PARALLEL VISUAL GENERATION BY LESSON PART
        #
        # Each lesson part owns its own visual world.
        # The first visual of every part is generated first
        # and becomes the reference for the remaining visuals
        # in that same part.
        # =====================================================

        if not image_visuals:
            return


        def generate_single_visual(
                visual: dict,
                reference_bytes=None,
                reference_mime_type="image/png"
        ):
            if visual.get("reuse_of"):
                print("LESSON VISUAL REUSED (no image generated):", {"unit_lesson_id": unit_lesson_id,
                      "part_number": visual.get("part_number"), "order": visual.get("order"), "reuse_of": visual.get("reuse_of")})
                return {"part_number": visual.get("part_number"), "order": visual.get("order"), "reuse_of": visual.get("reuse_of"),
                        "type": "image", "trigger_text": visual.get("trigger_text"), "storage_path": None, "reused": True}
            part_number = int(
                visual.get(
                    "part_number"
                )
                or 0
            )

            if not part_number:
                raise RuntimeError(
                    "Visual part number is missing"
                )

            visual_order = int(
                visual.get(
                    "order"
                )
                or 0
            )

            if not visual_order:
                raise RuntimeError(
                    "Visual order is missing"
                )

            storage_path = (
                f"unit_lessons/"
                f"{unit_lesson_id}/"
                f"v{content_version}/"
                f"part_{part_number}/"
                f"visual_{visual_order}.png"
            )

            try:

                create_lesson_media_signed_url(
                    storage_path
                )

                print(
                    "LESSON VISUAL CACHE HIT:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "order":
                            visual_order,

                        "storage_path":
                            storage_path
                    }
                )

                return {
                    "part_number":
                        part_number,

                    "order":
                        visual_order,

                    "type":
                        "image",

                    "storage_path":
                        storage_path,

                    "source":
                        "cache"
                }

            except Exception:

                print(
                    "LESSON VISUAL CACHE MISS:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "order":
                            visual_order
                    }
                )

            for attempt in range(
                1,
                MAX_VISUAL_RETRIES + 1
            ):

                try:

                    print(
                        "LESSON VISUAL ATTEMPT:",
                        {
                            "unit_lesson_id":
                                unit_lesson_id,

                            "part_number":
                                part_number,

                            "order":
                                visual_order,

                            "attempt":
                                attempt
                        }
                    )

                    result = (
                        generate_and_store_lesson_visual_image(
                            unit_lesson_id=
                                unit_lesson_id,

                            content_version=
                                content_version,

                            visual=
                                visual,

                            reference_image_bytes=(
                                reference_bytes
                                if visual_order > 1
                                else None
                            ),

                            reference_mime_type=
                                reference_mime_type
                        )
                    )

                    print(
                        "LESSON VISUAL SUCCESS:",
                        {
                            "unit_lesson_id":
                                unit_lesson_id,

                            "part_number":
                                part_number,

                            "order":
                                visual_order,

                            "attempt":
                                attempt
                        }
                    )

                    return result

                except Exception as visual_error:

                    print(
                        "LESSON VISUAL ATTEMPT FAILED:",
                        {
                            "unit_lesson_id":
                                unit_lesson_id,

                            "part_number":
                                part_number,

                            "order":
                                visual_order,

                            "attempt":
                                attempt,

                            "error":
                                repr(
                                    visual_error
                                )
                        }
                    )

                    traceback.print_exc()

                    if (
                        attempt
                        <
                        MAX_VISUAL_RETRIES
                    ):

                        time.sleep(
                            RETRY_DELAY_SECONDS
                            * attempt
                        )

            print(
                "LESSON VISUAL PRIMARY PROMPT FAILED:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "part_number":
                        part_number,

                    "order":
                        visual_order
                }
            )

            source_text = str(
                visual.get(
                    "source_text"
                )
                or ""
            ).strip()

            parent_lesson = (
                get_learning_lesson(
                    unit_lesson[
                        "learning_lesson_id"
                    ]
                )
            )

            fallback_prompt = (
                build_segment_visual_fallback_prompt(
                    unit_lesson=
                        unit_lesson,

                    parent_lesson=
                        parent_lesson,

                    segment_text=
                        source_text,

                    segment_index=
                        visual_order
                )
            )

            fallback_visual = {
                **visual,

                "type":
                    "image",

                "generation_prompt":
                    fallback_prompt
            }

            try:

                print(
                    "LESSON VISUAL FALLBACK START:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "order":
                            visual_order
                    }
                )

                result = (
                    generate_and_store_lesson_visual_image(
                        unit_lesson_id=
                            unit_lesson_id,

                        content_version=
                            content_version,

                        visual=
                            fallback_visual,

                        reference_image_bytes=(
                            reference_bytes
                            if visual_order > 1
                            else None
                        ),

                        reference_mime_type=
                            reference_mime_type
                    )
                )

                print(
                    "LESSON VISUAL FALLBACK SUCCESS:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "order":
                            visual_order
                    }
                )

                return result

            except Exception as fallback_error:

                print(
                    "LESSON VISUAL FALLBACK FAILED:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "order":
                            visual_order,

                        "error":
                            repr(
                                fallback_error
                            )
                    }
                )

                traceback.print_exc()

                return None


        part_numbers = sorted(
            {
                int(
                    visual.get(
                        "part_number"
                    )
                    or 0
                )
                for visual in image_visuals
                if isinstance(
                    visual,
                    dict
                )
                and int(
                    visual.get(
                        "part_number"
                    )
                    or 0
                ) > 0
            }
        )


        for part_number in part_numbers:

            # generated_visuals accumulates across parts; remember where this part started
            # so the DONE line below counts this part's images and not the whole lesson.
            generated_before_part = len(generated_visuals)

            part_visuals = [
                visual
                for visual in image_visuals
                if int(
                    visual.get(
                        "part_number"
                    )
                    or 0
                )
                ==
                part_number
            ]

            part_visuals = sorted(
                part_visuals,
                key=lambda visual:
                    int(
                        visual.get(
                            "order"
                        )
                        or 0
                    )
            )

            if not part_visuals:
                continue

            media_trace.trace_set(part=part_number)
            print(
                "LESSON PART VISUAL GENERATION START:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "part_number":
                        part_number,

                    "visual_count":
                        len(
                            part_visuals
                        )
                }
            )

            first_visual = (
                part_visuals[0]
            )

            first_visual_order = int(
                first_visual.get(
                    "order"
                )
                or 0
            )

            chain_reference = None
            if int(part_number) > 1:
                # keep ONE illustrator across parts: part N's first image follows part 1's first image
                try:
                    chain_reference = storage_with_retry(lambda: sb.storage.from_(LESSON_MEDIA_BUCKET).download(
                        f"unit_lessons/{unit_lesson_id}/v{content_version}/part_1/visual_1.png"), label="STORAGE DOWNLOAD")
                    print("LESSON PART STYLE CHAIN:", {"unit_lesson_id": unit_lesson_id, "part_number": part_number, "bytes": len(chain_reference or b"")})
                except Exception as chain_error:
                    print("LESSON PART STYLE CHAIN NOT AVAILABLE:", {"unit_lesson_id": unit_lesson_id, "part_number": part_number, "error": repr(chain_error)[:120]})
                    chain_reference = None
            first_result = (
                generate_single_visual(first_visual, reference_bytes=chain_reference)
                if chain_reference else generate_single_visual(first_visual)
            )

            if first_result:

                generated_visuals.append(
                    first_result
                )

            part_reference_bytes = None
            part_reference_mime_type = (
                "image/png"
            )

            reference_storage_path = (
                f"unit_lessons/"
                f"{unit_lesson_id}/"
                f"v{content_version}/"
                f"part_{part_number}/"
                f"visual_{first_visual_order}.png"
            )

            try:

                part_reference_bytes = storage_with_retry(lambda: (
                    sb.storage
                    .from_(
                        LESSON_MEDIA_BUCKET
                    )
                    .download(
                        reference_storage_path
                    )
                ), label="STORAGE DOWNLOAD")

                print(
                    "LESSON PART MASTER REFERENCE LOADED:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "order":
                            first_visual_order,

                        "bytes":
                            len(
                                part_reference_bytes
                                or b""
                            )
                    }
                )

            except Exception as reference_error:

                print(
                    "LESSON PART MASTER REFERENCE NOT READY:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "order":
                            first_visual_order,

                        "error":
                            repr(
                                reference_error
                            )
                    }
                )

                part_reference_bytes = None

            remaining_part_visuals = (
                part_visuals[1:]
            )

            if remaining_part_visuals:

                print(
                    "LESSON PART VISUAL PARALLEL START:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "visual_count":
                            len(
                                remaining_part_visuals
                            ),

                        "max_workers":
                            3
                    }
                )

                with ThreadPoolExecutor(
                    max_workers=3
                ) as executor:

                    futures = [
                        executor.submit(run_in_context(
                            generate_single_visual,
                            visual,
                            part_reference_bytes,
                            part_reference_mime_type
                        ))
                        for visual
                        in remaining_part_visuals
                    ]

                    for future in futures:

                        try:

                            result = (
                                future.result()
                            )

                            if result:

                                generated_visuals.append(
                                    result
                                )

                        except Exception as future_error:

                            print(
                                "LESSON PART VISUAL WORKER FAILED:",
                                {
                                    "unit_lesson_id":
                                        unit_lesson_id,

                                    "part_number":
                                        part_number,

                                    "error":
                                        repr(
                                            future_error
                                        )
                                }
                            )

                            traceback.print_exc()

            # 2026-09-17: a part whose images ALL failed used to log "DONE" and the
            # media job reported success, so a lesson with zero pictures looked
            # healthy in the logs. Say it loudly instead.
            print(
                "LESSON PART VISUAL GENERATION DONE:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "part_number":
                        part_number,

                    "images_ok":
                        len(generated_visuals)
                        - generated_before_part,

                    "images_planned":
                        len(part_visuals)
                }
            )

            if part_visuals and len(generated_visuals) == generated_before_part:
                print(
                    "LESSON PART VISUAL GENERATION FAILED (no image produced):",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "images_planned":
                            len(part_visuals)
                    }
                )


        generated_visuals.sort(
            key=lambda visual: (
                int(
                    visual.get(
                        "part_number"
                    )
                    or 0
                ),
                int(
                    visual.get(
                        "order"
                    )
                    or 0
                )
            )
        )

        print(
            "ALL LESSON VISUALS READY:",
            {
                "unit_lesson_id":
                    unit_lesson_id,

                "planned_count":
                    len(
                        image_visuals
                    ),

                "generated_count":
                    len(
                        generated_visuals
                    ),

                "visuals":
                    generated_visuals
            }
        )

    except Exception as e:

        print(
            "ALL LESSON VISUALS ERROR:",
            {
                "unit_lesson_id":
                    unit_lesson_id,

                "error":
                    repr(e)
            }
        )

        traceback.print_exc()

# =====================================================
# TRANSITION VIDEO
# Teacher + lesson visual -> Gemini Omni
# =====================================================

def generate_transition_video_background(
        unit_lesson_id: int
):

    print(
        "TRANSITION VIDEO GENERATION DISABLED:",
        {
            "unit_lesson_id":
                unit_lesson_id
        }
    )

    return


def generate_unit_lesson_media_background(
        unit_lesson_id: int
):
    print(
        "========== LESSON MEDIA BACKGROUND START ==========",
        {
            "unit_lesson_id":
                unit_lesson_id
        }
    )

    # =============================================
    # FIRST SCREEN FIRST: the hero image
    # =============================================
    # The child sees the hero before any audio or part visual. It used to be
    # generated only when the browser asked for it, inside that request (~5 s).
    # Now it is the first thing the media job does; a request that arrives
    # meanwhile waits on the same lock and gets the stored file.
    try:
        hero_path = get_lesson_media_storage_path(
            unit_lesson_id=unit_lesson_id,
            media_type="hero"
        )
        with generation_lock(f"hero:{unit_lesson_id}"):
            try:
                create_lesson_media_signed_url(hero_path)
                print("LESSON HERO ALREADY STORED:", {"unit_lesson_id": unit_lesson_id})
            except Exception:
                with media_trace.stage("hero"):
                    generate_and_store_lesson_hero_image(unit_lesson_id)
    except Exception as hero_error:
        print(
            "LESSON HERO FIRST FAILED (continuing with audio/visuals):",
            {"unit_lesson_id": unit_lesson_id, "error": repr(hero_error)[:200]}
        )

    with ThreadPoolExecutor(
            max_workers=2
    ) as executor:

        # =============================================
        # AUDIO + VISUALS RUN IN PARALLEL
        # =============================================

        audio_future = executor.submit(run_in_context(
            media_trace.staged, "audio",
            generate_unit_lesson_audio_background,
            unit_lesson_id
        ))

        visuals_future = executor.submit(run_in_context(
            media_trace.staged, "visuals",
            generate_all_lesson_visuals_background,
            unit_lesson_id
        ))

        # =============================================
        # WAIT FOR VISUALS
        # =============================================

        try:

            visuals_future.result()

        except Exception as e:

            print(
                "LESSON VISUALS BACKGROUND FAILED:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "error":
                        repr(e)
                }
            )

            traceback.print_exc()

        # =============================================
        # TRANSITION VIDEO
        #
        # מתחיל רק אחרי שהתמונות מוכנות,
        # כי visual_1 משמש כ-reference.
        # =============================================

        try:

            with media_trace.stage("transition_video"):
                generate_transition_video_background(
                    unit_lesson_id
                )

        except Exception as e:

            print(
                "LESSON TRANSITION VIDEO BACKGROUND FAILED:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "error":
                        repr(e)
                }
            )

            traceback.print_exc()

        # =============================================
        # WAIT FOR AUDIO
        # =============================================

        try:

            audio_future.result()

        except Exception as e:

            print(
                "LESSON AUDIO BACKGROUND FAILED:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "error":
                        repr(e)
                }
            )

            traceback.print_exc()

    print(
        "========== LESSON MEDIA BACKGROUND DONE ==========",
        {
            "unit_lesson_id":
                unit_lesson_id
        }
    )

def generate_first_lesson_visual_background(
        unit_lesson_id: int
):
    try:

        unit_lesson = get_unit_lesson(
            unit_lesson_id
        )

        generated_lesson_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
            or {}
        )

        visual_plan = (
            generated_lesson_json.get(
                "visual_plan"
            )
            or {}
        )

        visuals = (
            visual_plan.get(
                "visuals"
            )
            or []
        )

        content_version = int(
            unit_lesson.get(
                "content_version"
            )
            or 1
        )

        first_image = None

        for visual in visuals:

            if not isinstance(
                    visual,
                    dict
            ):
                continue

            if (
                visual.get("type")
                == "image"
            ):
                first_image = visual
                break

        if not first_image:

            print(
                "NO IMAGE FOUND IN VISUAL PLAN:",
                unit_lesson_id
            )

            return

        result = (
            generate_and_store_lesson_visual_image(
                unit_lesson_id=
                    unit_lesson_id,

                content_version=
                    content_version,

                visual=
                    first_image
            )
        )

        print(
            "FIRST LESSON VISUAL READY:",
            result
        )

    except Exception as e:

        print(
            "FIRST LESSON VISUAL ERROR:",
            {
                "unit_lesson_id":
                    unit_lesson_id,

                "error":
                    repr(e)
            }
        )

        traceback.print_exc()

def add_signed_urls_to_lesson_audio(
        lesson_audio_json: dict | None
) -> dict | None:

    if not isinstance(
            lesson_audio_json,
            dict
    ):
        return None

    bucket = (
        lesson_audio_json.get(
            "bucket"
        )
        or LESSON_AUDIO_BUCKET
    )

    def create_audio_signed_item(
            audio_item: dict | None
    ) -> dict | None:

        if not isinstance(
                audio_item,
                dict
        ):
            return None

        path = str(
            audio_item.get(
                "path"
            )
            or ""
        ).strip()

        if not path:
            return None

        # cache hit after the batch prefetch below; one Storage call only if the
        # path was not part of the batch (legacy shapes)
        signed_url = signed_url_cached(
            bucket,
            path,
            LESSON_AUDIO_URL_EXPIRY_SECONDS
        )

        return {
            **audio_item,
            "url":
                signed_url
        }

    # =============================================
    # SIGN LESSON PARTS
    # =============================================

    raw_parts = (
        lesson_audio_json.get(
            "parts"
        )
        or []
    )

    # =============================================
    # PREFETCH: sign every path of the lesson in ONE Storage call
    # =============================================
    all_paths = []
    for raw_part in raw_parts:
        if isinstance(raw_part, dict):
            for seg in (raw_part.get("segments") or []):
                if isinstance(seg, dict) and seg.get("path"):
                    all_paths.append(str(seg["path"]).strip())
            q = raw_part.get("question")
            if isinstance(q, dict) and q.get("path"):
                all_paths.append(str(q["path"]).strip())
    for seg in (lesson_audio_json.get("segments") or []):
        if isinstance(seg, dict) and seg.get("path"):
            all_paths.append(str(seg["path"]).strip())
    q = lesson_audio_json.get("question")
    if isinstance(q, dict) and q.get("path"):
        all_paths.append(str(q["path"]).strip())
    if all_paths:
        try:
            signed_urls_cached_batch(
                bucket,
                all_paths,
                LESSON_AUDIO_URL_EXPIRY_SECONDS
            )
        except Exception as batch_error:
            # fall through: per-item signing below still works, just slower
            print(
                "AUDIO SIGNED URL BATCH FAILED:",
                {"paths": len(all_paths), "error": repr(batch_error)[:200]}
            )

    signed_parts = []

    for fallback_part_number, raw_part in enumerate(
            raw_parts,
            start=1
    ):

        if not isinstance(
                raw_part,
                dict
        ):
            continue

        part_number = int(
            raw_part.get(
                "part_number"
            )
            or fallback_part_number
        )

        raw_part_segments = (
            raw_part.get(
                "segments"
            )
            or []
        )

        signed_part_segments = []

        for segment in raw_part_segments:

            signed_segment = (
                create_audio_signed_item(
                    segment
                )
            )

            if signed_segment:

                signed_part_segments.append(
                    signed_segment
                )

        signed_part_question = (
            create_audio_signed_item(
                raw_part.get(
                    "question"
                )
            )
        )

        signed_parts.append(
            {
                **raw_part,

                "part_number":
                    part_number,

                "segments":
                    signed_part_segments,

                "question":
                    signed_part_question
            }
        )

    # =============================================
    # LEGACY TOP-LEVEL AUDIO
    # =============================================

    raw_segments = (
        lesson_audio_json.get(
            "segments"
        )
        or []
    )

    signed_segments = []

    for segment in raw_segments:

        signed_segment = (
            create_audio_signed_item(
                segment
            )
        )

        if signed_segment:

            signed_segments.append(
                signed_segment
            )

    signed_question = (
        create_audio_signed_item(
            lesson_audio_json.get(
                "question"
            )
        )
    )

    # =============================================
    # USE PART 1 AS LEGACY FALLBACK
    # =============================================

    if (
        not signed_segments
        and signed_parts
    ):

        signed_segments = (
            signed_parts[0].get(
                "segments"
            )
            or []
        )

    if (
        signed_question is None
        and signed_parts
    ):

        signed_question = (
            signed_parts[0].get(
                "question"
            )
        )

    return {
        **lesson_audio_json,

        "parts":
            signed_parts,

        "segments":
            signed_segments,

        "question":
            signed_question,

        "url_expires_in_seconds":
            LESSON_AUDIO_URL_EXPIRY_SECONDS
    }

def _concat_wavs(wavs: list) -> tuple[bytes, float]:
    """Join 24 kHz/16-bit/mono WAVs (as generate_tts_wav_bytes returns) into one."""
    pcm = b""
    for wav_bytes, _dur in wavs:
        with wave.open(io.BytesIO(wav_bytes), "rb") as w:
            pcm += w.readframes(w.getnframes())
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    return buf.getvalue(), len(pcm) / (24000 * 2)


def generate_tts_wav_bytes(
        text: str,
        gender: str | None = None
) -> tuple[bytes, float]:

    clean_text = str(
        text or ""
    ).strip()

    if not clean_text:
        raise RuntimeError(
            "Cannot generate audio for empty text"
        )

    # The TTS preview model answers 400 INVALID_ARGUMENT now and then for text that
    # succeeds on the next call (seen on segment 6 of lesson 5 and on lesson 1).
    # One such answer used to fail the whole lesson's audio, 17 calls in. Three tries
    # with a short pause; a real 400 still comes back after the third.
    # 429 RESOURCE_EXHAUSTED is the TTS model's per-minute quota (seen on lesson 5):
    # a short pause is useless there, so those wait 20/40/60 seconds instead.
    TTS_ATTEMPTS = int(os.getenv("TTS_ATTEMPTS", "4"))
    clean_text = lq.normalize_for_tts(clean_text)    # emoji out, arrows/units/math spelled out
    chunks = lq.split_for_tts(clean_text)
    if len(chunks) > 1:
        # long segment: several short calls (the TTS model rejects long/odd input), one WAV
        print("TTS LONG TEXT SPLIT:", {"chars": len(clean_text), "chunks": len(chunks)})
        wavs = [generate_tts_wav_bytes(c) for c in chunks]
        return _concat_wavs(wavs)
    spoken_text = vocalize_for_tts(clean_text, gender)      # nikud on ambiguous words only
    response = None
    audio_data = None
    for attempt in range(1, TTS_ATTEMPTS + 1):
        try:
            if TTS_PROVIDER == "openrouter":
                audio_data = openrouter_tts_pcm(spoken_text)
                break
            response = gemini_client.models.generate_content(
                model="gemini-3.1-flash-tts-preview",
                contents=(
                    TTS_STYLE_PREFIX
                    + spoken_text
                ),

                config=types.GenerateContentConfig(
                    temperature=2.0,

                    response_modalities=[
                        "AUDIO"
                    ],

                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=
                            types.PrebuiltVoiceConfig(
                                voice_name="Aoede"
                            )
                        )
                    ),

                    http_options=types.HttpOptions(
                        timeout=90_000          # ms; a hung call must not hold a thread forever
                    )
                )
            )
            break
        except Exception as tts_error:
            print(
                "TTS RETRY:",
                {
                    "attempt": attempt,
                    "max_attempts": TTS_ATTEMPTS,
                    "text_length": len(clean_text),
                    "error": repr(tts_error)[:200]
                }
            )
            err_text = repr(tts_error)
            if attempt >= TTS_ATTEMPTS or "401" in err_text or "403" in err_text:
                raise                         # a bad key does not get better on retry
            quota_hit = "429" in err_text or "RESOURCE_EXHAUSTED" in err_text
            time.sleep(20 * attempt if quota_hit else 2 * attempt)

    if audio_data is None:                 # direct Gemini path
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

    duration_seconds = (
        len(audio_data)
        / (24000 * 2)
    )

    wav_buffer = io.BytesIO()

    with wave.open(
            wav_buffer,
            "wb"
    ) as wav_file:

        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(audio_data)

    return (
        wav_buffer.getvalue(),
        duration_seconds
    )


def generate_and_store_lesson_audio(
        unit_lesson_id: int,
        structured_lesson: dict,
        content_version: int,
        on_progress=None
) -> dict:
    """Synthesise every segment of every part and store the WAVs.

    on_progress(partial_lesson_audio_json) is called after every stored segment
    and after every finished part, with the same shape as the final result plus
    "partial": True and per-part "complete" flags. The caller persists it so the
    browser can start playing part 1 while the rest is still being synthesised
    (progressive audio, 2026-09-15). A failure inside on_progress is logged and
    ignored: progress is a convenience, the final write is what counts.
    """

    lesson_parts = (
        structured_lesson.get(
            "parts"
        )
        or []
    )

    # Legacy fallback for previously generated lessons.
    if not lesson_parts:

        legacy_lesson = (
            structured_lesson.get(
                "lesson"
            )
            or []
        )

        legacy_question = (
            structured_lesson.get(
                "question"
            )
            or {}
        )

        if legacy_lesson:

            lesson_parts = [
                {
                    "part_number": 1,
                    "lesson": legacy_lesson,
                    "question": legacy_question
                }
            ]

    if not lesson_parts:
        raise RuntimeError(
            "No lesson parts found for audio generation"
        )

    stored_parts = []

    total_duration_seconds = 0.0

    def emit_progress(current_part):
        if on_progress is None:
            return
        parts = list(stored_parts)
        if current_part is not None:
            parts.append(current_part)
        try:
            on_progress({
                "version": content_version,
                "bucket": LESSON_AUDIO_BUCKET,
                "partial": True,
                "parts": parts,
            })
        except Exception as progress_error:
            print(
                "BACKGROUND AUDIO PROGRESS SAVE FAILED:",
                {"unit_lesson_id": unit_lesson_id, "error": repr(progress_error)[:200]}
            )

    # =============================================
    # LESSON PARTS
    # =============================================

    for fallback_part_number, lesson_part in enumerate(
            lesson_parts,
            start=1
    ):

        if not isinstance(
                lesson_part,
                dict
        ):
            continue

        part_number = int(
            lesson_part.get(
                "part_number"
            )
            or fallback_part_number
        )

        lesson_segments = (
            lesson_part.get(
                "lesson"
            )
            or []
        )

        question_data = (
            lesson_part.get(
                "question"
            )
            or {}
        )

        stored_segments = []

        part_duration_seconds = 0.0

        expected_segment_count = sum(
            1 for s in lesson_segments
            if isinstance(s, dict) and str(s.get("text") or "").strip()
        )

        print(
            "BACKGROUND TTS PART START:",
            {
                "unit_lesson_id":
                    unit_lesson_id,

                "part_number":
                    part_number,

                "segments_count":
                    len(
                        lesson_segments
                    )
            }
        )

        # =============================================
        # PART SEGMENTS
        # =============================================

        # Parallel TTS (2026-09-15): every segment of this part (and its question)
        # is synthesised by TTS_PARALLEL threads at once; the loop below consumes
        # the results IN ORDER, so uploads, progress saves and the progressive
        # player still see segment 1, 2, 3... Measured serial: ~8.5 s/segment,
        # 147 s per lesson; with 3 in parallel ~55 s.
        tts_pool = ThreadPoolExecutor(max_workers=TTS_PARALLEL)
        tts_futures = {}
        for _i, _seg in enumerate(lesson_segments, start=1):
            _txt = str(_seg.get("text") or "").strip() if isinstance(_seg, dict) else ""
            if _txt:
                tts_futures[_i] = tts_pool.submit(run_in_context(generate_tts_wav_bytes, _txt))
        _qtxt = str((question_data or {}).get("text") or "").strip()
        tts_question_future = (
            tts_pool.submit(run_in_context(generate_tts_wav_bytes, _qtxt)) if _qtxt else None
        )
        print("BACKGROUND TTS PART SUBMITTED:", {"unit_lesson_id": unit_lesson_id, "part_number": part_number,
                                               "segments": len(tts_futures), "question": bool(_qtxt), "parallel": TTS_PARALLEL})

        for index, segment in enumerate(
                lesson_segments,
                start=1
        ):

            if not isinstance(
                    segment,
                    dict
            ):
                continue

            segment_text = str(
                segment.get(
                    "text"
                )
                or ""
            ).strip()

            if not segment_text:
                continue

            print(
                "BACKGROUND TTS SEGMENT START:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "part_number":
                        part_number,

                    "segment_index":
                        index,

                    "text_length":
                        len(
                            segment_text
                        ),

                    "text":
                        repr(
                            segment_text
                        )
                }
            )

            try:

                wav_bytes, duration_seconds = tts_futures[index].result()

                print(
                    "BACKGROUND TTS SEGMENT SUCCESS:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "segment_index":
                            index,

                        "duration_seconds":
                            duration_seconds
                    }
                )

            except Exception as e:

                print(
                    "BACKGROUND TTS SEGMENT FAILED:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "segment_index":
                            index,

                        "text_length":
                            len(
                                segment_text
                            ),

                        "text":
                            repr(
                                segment_text
                            ),

                        "error":
                            repr(
                                e
                            )
                    }
                )

                raise

            storage_path = (
                f"unit_lessons/"
                f"{unit_lesson_id}/"
                f"v{content_version}/"
                f"part_{part_number}/"
                f"segment_{index}.wav"
            )

            storage_with_retry(lambda: sb.storage.from_(
                LESSON_AUDIO_BUCKET
            ).upload(
                path=storage_path,
                file=wav_bytes,
                file_options={
                    "content-type":
                        "audio/wav",

                    "upsert":
                        "true"
                }
            ), label="STORAGE UPLOAD")

            stored_segments.append(
                {
                    "index":
                        index,

                    "path":
                        storage_path,

                    "duration_seconds":
                        round(
                            duration_seconds,
                            2
                        )
                }
            )

            part_duration_seconds += (
                duration_seconds
            )

            total_duration_seconds += (
                duration_seconds
            )

            # progressive audio: what exists so far, this part still open
            emit_progress({
                "part_number": part_number,
                "segments": list(stored_segments),
                "question": None,
                "expected_segments": expected_segment_count,
                "complete": False,
            })

        # =============================================
        # PART QUESTION
        # =============================================

        stored_question = None

        question_text = str(
            question_data.get(
                "text"
            )
            or ""
        ).strip()

        if question_text:

            print(
                "BACKGROUND TTS QUESTION START:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "part_number":
                        part_number,

                    "text_length":
                        len(
                            question_text
                        ),

                    "text":
                        repr(
                            question_text
                        )
                }
            )

            try:

                wav_bytes, duration_seconds = tts_question_future.result()

                print(
                    "BACKGROUND TTS QUESTION SUCCESS:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "duration_seconds":
                            duration_seconds
                    }
                )

            except Exception as e:

                print(
                    "BACKGROUND TTS QUESTION FAILED:",
                    {
                        "unit_lesson_id":
                            unit_lesson_id,

                        "part_number":
                            part_number,

                        "text_length":
                            len(
                                question_text
                            ),

                        "text":
                            repr(
                                question_text
                            ),

                        "error":
                            repr(
                                e
                            )
                    }
                )

                raise

            question_path = (
                f"unit_lessons/"
                f"{unit_lesson_id}/"
                f"v{content_version}/"
                f"part_{part_number}/"
                f"question.wav"
            )

            storage_with_retry(lambda: sb.storage.from_(
                LESSON_AUDIO_BUCKET
            ).upload(
                path=question_path,
                file=wav_bytes,
                file_options={
                    "content-type":
                        "audio/wav",

                    "upsert":
                        "true"
                }
            ), label="STORAGE UPLOAD")

            stored_question = {
                "path":
                    question_path,

                "duration_seconds":
                    round(
                        duration_seconds,
                        2
                    )
            }

            part_duration_seconds += (
                duration_seconds
            )

            total_duration_seconds += (
                duration_seconds
            )

        if not stored_segments:

            raise RuntimeError(
                f"No lesson audio segments were generated "
                f"for part {part_number}"
            )

        stored_parts.append(
            {
                "part_number":
                    part_number,

                "segments":
                    stored_segments,

                "question":
                    stored_question,

                "expected_segments":
                    expected_segment_count,

                "complete":
                    True,

                "total_duration_seconds":
                    round(
                        part_duration_seconds,
                        2
                    )
            }
        )

        tts_pool.shutdown(wait=False)
        # progressive audio: this part is complete, later parts still to come
        emit_progress(None)

        print(
            "BACKGROUND TTS PART READY:",
            {
                "unit_lesson_id":
                    unit_lesson_id,

                "part_number":
                    part_number,

                "segments_count":
                    len(
                        stored_segments
                    ),

                "duration_seconds":
                    round(
                        part_duration_seconds,
                        2
                    )
            }
        )

    if not stored_parts:
        raise RuntimeError(
            "No lesson audio parts were generated"
        )

    first_part = (
        stored_parts[0]
    )

    return {
        "version":
            content_version,

        "bucket":
            LESSON_AUDIO_BUCKET,

        "parts":
            stored_parts,

        # Temporary compatibility fields.
        "segments":
            first_part.get(
                "segments"
            )
            or [],

        "question":
            first_part.get(
                "question"
            ),

        "total_duration_seconds":
            round(
                total_duration_seconds,
                2
            )
    }
def generate_unit_lesson_audio_background(
        unit_lesson_id: int
):
    """
    יצירת אודיו לשיעור ברקע.

    הפונקציה אינה תלויה ב-request של המשתמש.
    היא שולפת את השיעור מהמסד,
    יוצרת קבצי WAV,
    מעלה אותם ל-Storage
    ומעדכנת את סטטוס האודיו.
    """

    try:

        # =============================================
        # LOAD LESSON
        # =============================================

        unit_lesson = get_unit_lesson(
            unit_lesson_id
        )

        generation_status = (
            unit_lesson.get(
                "generation_status"
            )
            or "empty"
        )

        audio_generation_status = (
            unit_lesson.get(
                "audio_generation_status"
            )
            or "pending"
        )

        cached_audio = (
            unit_lesson.get(
                "lesson_audio_json"
            )
        )

        generated_lesson_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
        )

        # =============================================
        # CONTENT MUST BE READY
        # =============================================

        if generation_status != "ready":
            print(
                "BACKGROUND AUDIO SKIPPED: "
                "lesson content is not ready:",
                unit_lesson_id
            )
            return

        if not isinstance(
                generated_lesson_json,
                dict
        ):
            print(
                "BACKGROUND AUDIO SKIPPED: "
                "generated lesson JSON is missing:",
                unit_lesson_id
            )
            return

        structured_lesson = (
            generated_lesson_json.get(
                "structured_lesson"
            )
        )

        if not isinstance(
                structured_lesson,
                dict
        ):
            print(
                "BACKGROUND AUDIO SKIPPED: "
                "structured lesson is missing:",
                unit_lesson_id
            )
            return

        # =============================================
        # ALREADY READY
        # =============================================

        cached_audio_has_parts = (
            isinstance(
                cached_audio,
                dict
            )
            and bool(
                cached_audio.get(
                    "parts"
                )
            )
        )

        cached_audio_has_legacy_segments = (
            isinstance(
                cached_audio,
                dict
            )
            and bool(
                cached_audio.get(
                    "segments"
                )
            )
        )

        if (
                audio_generation_status == "ready"
                and (
                    cached_audio_has_parts
                    or
                    cached_audio_has_legacy_segments
                )
        ):
            print(
                "BACKGROUND AUDIO ALREADY READY:",
                {
                    "unit_lesson_id":
                        unit_lesson_id,

                    "has_parts":
                        cached_audio_has_parts,

                    "has_legacy_segments":
                        cached_audio_has_legacy_segments
                }
            )

            return

        # =============================================
        # ALREADY GENERATING
        # =============================================

        if audio_generation_status == "generating":
            # "generating" with no progress for a long time means the process that
            # was generating died (deploy, crash, SIGKILL). Without this the lesson
            # stayed "generating" forever: the re-queued job saw the status and quit.
            stale_after = int(os.getenv("AUDIO_GENERATING_STALE_SECONDS", "600"))
            updated_raw = str(unit_lesson.get("updated_at") or "")
            try:
                updated_dt = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
                age_s = (datetime.now(timezone.utc) - updated_dt).total_seconds()
            except Exception:
                age_s = stale_after + 1
            if age_s < stale_after:
                print(
                    "BACKGROUND AUDIO ALREADY GENERATING:",
                    {"unit_lesson_id": unit_lesson_id, "age_seconds": round(age_s)}
                )
                return
            print(
                "BACKGROUND AUDIO STALE GENERATING - TAKING OVER:",
                {"unit_lesson_id": unit_lesson_id, "age_seconds": round(age_s)}
            )

        # =============================================
        # MARK AS GENERATING
        # =============================================

        audio_started_at = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        sb.table(
            "lesson_units_content"
        ).update({

            "audio_generation_status":
                "generating",

            "audio_generation_error":
                None,

            "updated_at":
                audio_started_at

        }).eq(
            "id",
            unit_lesson_id
        ).execute()

        print(
            "BACKGROUND AUDIO STARTED:",
            unit_lesson_id
        )

        # =============================================
        # GENERATE AUDIO
        # =============================================

        content_version = int(
            unit_lesson.get(
                "content_version"
            )
            or 1
        )

        def persist_audio_progress(partial_audio_json: dict):
            # One small update per synthesised segment. The browser polls
            # /unit-lesson/audio and starts playing what exists while the rest
            # is still being generated. Status stays "generating"; updated_at
            # moves so the stale-takeover check above stays honest.
            sb.table(
                "lesson_units_content"
            ).update({
                "lesson_audio_json": partial_audio_json,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq(
                "id", unit_lesson_id
            ).execute()

        lesson_audio_json = (
            generate_and_store_lesson_audio(

                unit_lesson_id=
                    unit_lesson_id,

                structured_lesson=
                    structured_lesson,

                content_version=
                    content_version,

                on_progress=
                    persist_audio_progress
            )
        )

        audio_generated_at = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        # =============================================
        # SAVE RESULT
        # =============================================

        sb.table(
            "lesson_units_content"
        ).update({

            "lesson_audio_json":
                lesson_audio_json,

            "audio_generation_status":
                "ready",

            "audio_generation_error":
                None,

            "audio_generated_at":
                audio_generated_at,

            "tts_generated_at":
                audio_generated_at,

            "updated_at":
                audio_generated_at

        }).eq(
            "id",
            unit_lesson_id
        ).execute()

        print(
            "BACKGROUND AUDIO READY:",
            unit_lesson_id
        )

    except Exception as e:

        error_message = repr(e)

        print(
            "BACKGROUND AUDIO ERROR:",
            unit_lesson_id,
            error_message
        )

        try:

            sb.table(
                "lesson_units_content"
            ).update({

                "audio_generation_status":
                    "failed",

                "audio_generation_error":
                    str(e)[:1500],

                "updated_at":
                    datetime
                    .now(timezone.utc)
                    .isoformat()

            }).eq(
                "id",
                unit_lesson_id
            ).execute()

        except Exception as update_error:

            print(
                "BACKGROUND AUDIO FAILURE "
                "UPDATE ERROR:",
                repr(update_error)
            )
@app.post("/api/tutor/tts")
async def tutor_tts(
        body: TutorTTSRequest,
        authorization: str = Header(None)
):
    try:

        # אימות משתמש
        user = (await run_in_threadpool(lambda: authenticate_user(authorization)))
        ai_context("tts_live", user, body)

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
        # Identifiers and a length, never the text. This is a child's own words and
        # Render keeps logs; COPPA/GDPR-K treat that as personal data about a minor.
        print(
            "LIVE TTS REQUEST:",
            {
                "session_id": body.session_id,
                "text_length": len(text),
                **({"text": repr(text)} if not IS_PROD else {}),
            }
        )
        # =============================================
        # GEMINI TTS DEBUG
        # =============================================

        tts_started_at = time.perf_counter()

        print(
            "========== LIVE TTS GEMINI START ==========",
            {
                "session_id": body.session_id,
                "text_length": len(text),
                **({"text": repr(text)} if not IS_PROD else {}),
            }
        )

        try:

            audio_data_override = None
            text = lq.normalize_for_tts(text)
            # "אני כאן בשבילך" is written the same for a boy and a girl and read differently:
            # resolve the child (kid_id, else the tutor session) before vocalizing.
            _gender = None
            _child_name = None
            try:
                _child = None
                if body.kid_id:
                    _child = await run_in_threadpool(lambda: get_child_by_id(user.id, body.kid_id))
                elif body.session_id:
                    _sess = await run_in_threadpool(lambda: sb.table("tutor_sessions").select("kid_id")
                                                    .eq("id", body.session_id).limit(1).execute().data)
                    if _sess and _sess[0].get("kid_id"):
                        _child = await run_in_threadpool(lambda: get_child_by_id(user.id, _sess[0]["kid_id"]))
                if _child:
                    _gender = hebrew_gender_rule(_child)[0]
                    if _gender not in ("male", "female"):
                        _gender = None
                    _child_name = lq.display_first_name(_child.get("child_name") or "")
            except Exception as _gender_error:
                print("LIVE TTS GENDER LOOKUP FAILED (neutral reading):", repr(_gender_error)[:140])
            text = await run_in_threadpool(vocalize_for_tts, text, _gender, _child_name)   # name + gender-aware nikud
            _tts_key = tts_cache_key(text, _gender) if tts_cacheable(text) else None
            _tts_future = None
            if _tts_key:
                _cached = await run_in_threadpool(tts_cache_get, _tts_key)
                if _cached:
                    print("LIVE TTS CACHE HIT:", {"session_id": body.session_id, "key": _tts_key[:12],
                                                  "bytes": len(_cached), "text_length": len(text)})
                    return Response(content=_cached, media_type="audio/wav",
                                    headers={"Cache-Control": "no-store", "X-TTS-Cache": "hit"})
                _inflight = _TTS_INFLIGHT.get(_tts_key)
                if _inflight is not None:
                    print("LIVE TTS CACHE WAIT (same text in flight):", {"key": _tts_key[:12]})
                    _wav = await asyncio.shield(_inflight)
                    return Response(content=_wav, media_type="audio/wav",
                                    headers={"Cache-Control": "no-store", "X-TTS-Cache": "inflight"})
                _tts_future = asyncio.get_running_loop().create_future()
                _TTS_INFLIGHT[_tts_key] = _tts_future
            if TTS_PROVIDER == "openrouter":
                audio_data_override = await openrouter_tts_pcm_async(text)
                response = None
            else:
              response = (await gemini_client.aio.models.generate_content(
                model="gemini-3.1-flash-tts-preview",
                contents=(
                    TTS_STYLE_PREFIX
                    + text
                ),

                config=types.GenerateContentConfig(
                    temperature=2.0,

                    response_modalities=[
                        "AUDIO"
                    ],

                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=
                            types.PrebuiltVoiceConfig(
                                voice_name="Aoede"
                            )
                        )
                    )
                )
            ))

            print(
                "========== LIVE TTS GEMINI SUCCESS ==========",
                {
                    "session_id": body.session_id,
                    "elapsed_ms": round(
                        (
                            time.perf_counter()
                            - tts_started_at
                        )
                        * 1000
                    )
                }
            )

        except Exception as gemini_error:

            print(
                "========== LIVE TTS GEMINI FAILED ==========",
                {
                    "session_id": body.session_id,
                    "text_length": len(text),
                    "text": repr(text),
                    "elapsed_ms": round(
                        (
                            time.perf_counter()
                            - tts_started_at
                        )
                        * 1000
                    ),
                    "error_type":
                        type(gemini_error).__name__,
                    "error":
                        repr(gemini_error)
                }
            )

            traceback.print_exc()
            if _tts_future is not None and not _tts_future.done():
                _tts_future.set_exception(gemini_error)
                _TTS_INFLIGHT.pop(_tts_key, None)
            raise

        # קבלת PCM audio
        audio_data = audio_data_override if audio_data_override is not None else (
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
        audio_output_tokens = (
                audio_duration_seconds
                * GEMINI_AUDIO_TOKENS_PER_SECOND
        )

        gemini_audio_cost_usd = (
                audio_output_tokens
                / 1_000_000
                * GEMINI_TTS_AUDIO_OUTPUT_COST_PER_1M
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
        if _tts_key:
            if _tts_future is not None and not _tts_future.done():
                _tts_future.set_result(wav_bytes)
            _TTS_INFLIGHT.pop(_tts_key, None)
            _threading.Thread(target=tts_cache_put, args=(_tts_key, wav_bytes), daemon=True).start()

        # עדכון Session - קריאת TTS אחת
        if body.session_id:

            try:

                (await run_in_threadpool(lambda: update_tutor_session_after_tts(
                    session_id=
                    body.session_id,

                    audio_duration_seconds=
                    audio_duration_seconds,

                    cost_usd=
                    gemini_audio_cost_usd
                )))

                (await run_in_threadpool(lambda: increment_usage_summary(
                    user_id=
                    user.id,

                    tts_calls=
                    1,

                    tts_seconds=
                    audio_duration_seconds,

                    voice_output_seconds=
                    audio_duration_seconds,

                    gemini_cost_usd=
                    gemini_audio_cost_usd
                )))

            except Exception as usage_error:

                # =========================================
                # IMPORTANT:
                # האודיו כבר נוצר בהצלחה.
                # תקלה זמנית ב-Supabase/Usage
                # לא מפילה את ה-TTS לילד.
                # =========================================

                print(
                    "TTS USAGE UPDATE FAILED - AUDIO STILL RETURNED:",
                    {
                        "session_id":
                            body.session_id,

                        "error":
                            repr(
                                usage_error
                            )
                    }
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

        error_message = repr(e)

        print(
            "GEMINI TTS ENDPOINT ERROR:",
            {
                "error_type":
                    type(e).__name__,

                "error":
                    error_message,

                "session_id":
                    body.session_id,

                "text_length":
                    len(
                        (
                            body.text
                            or ""
                        ).strip()
                    )
            }
        )
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=(
                "Gemini TTS failed: "
                f"{error_message}"
            )
        )
@app.get(
    "/api/learning-lessons/{learning_lesson_id}/units"
)
def get_learning_lesson_units(
        learning_lesson_id: int,
        authorization: str = Header(None)
):
    try:
        authenticate_user(
            authorization
        )

        # מוודאים שהרשומה הראשית קיימת
        parent_lesson = get_learning_lesson(
            learning_lesson_id
        )

        units = get_lesson_units_and_lessons(
            learning_lesson_id
        )

        return {
            "learning_lesson_id":
                parent_lesson["id"],

            "subject":
                parent_lesson.get("subject"),

            "category":
                parent_lesson.get("category"),

            "parent_lesson_name":
                parent_lesson.get("lesson_name"),

            "units":
                units
        }

    except HTTPException:
        raise

    except Exception as e:
        print(
            "GET LESSON UNITS ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to load lesson units"
        )

def build_resume_context(unit_lesson: dict, chat_history: list) -> dict:
    """What was on screen before the coach dialogue: the explanation segments and the
    question of the part the child reached (from the shared lesson content)."""
    try:
        parts = (((unit_lesson or {}).get("generated_lesson_json") or {}).get("structured_lesson") or {}).get("parts") or []
        part_number = 1
        for row in chat_history:
            if row.get("part_number"):
                part_number = int(row["part_number"])
        part = next((p for p in parts if int(p.get("part_number") or 0) == part_number), parts[0] if parts else None)
        if not part:
            return {"part_number": part_number, "explanation_segments": [], "question": None}
        return {
            "part_number": part_number,
            "explanation_segments": [str(s.get("text") or "") for s in (part.get("lesson") or []) if isinstance(s, dict) and s.get("text")],
            "question": str(((part.get("question") or {}).get("text")) or "") or None,
        }
    except Exception as e:
        print("RESUME CONTEXT FAILED:", repr(e)[:120])
        return {"part_number": 1, "explanation_segments": [], "question": None}


@app.post(
    "/api/tutor/active-lesson-state"
)
def get_active_lesson_state(
        body: ActiveLessonStateRequest,
        authorization: str = Header(None)
):
    try:

        # =============================================
        # AUTH
        # =============================================

        user = authenticate_user(
            authorization
        )

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        # =============================================
        # CHILD
        # =============================================

        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )

        # =============================================
        # ACTIVE LEARNING COACH SESSION
        #
        # קודם מחפשים Coach פעיל.
        # כך לא משחזרים בטעות שיעור ישן אחר.
        # =============================================

        coach_res = (
            sb.table(
                "learning_coach_sessions"
            )
            .select(
                "id, "
                "kid_id, "
                "lesson_id, "
                "unit_lesson_id, "
                "coach_index, "
                "status, "
                "total_rounds, "
                "final_understanding_score, "
                "started_at"
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "status",
                "active"
            )
            .order(
                "started_at",
                desc=True
            )
            .limit(1)
            .execute()
        )

        if not coach_res.data:
            return {
                "has_active_lesson": False
            }

        coach_session = (
            coach_res.data[0]
        )

        # =============================================
        # LESSON PROGRESS
        # =============================================

        progress_res = (
            sb.table(
                "kid_lesson_progress"
            )
            .select(
                "id, "
                "kid_id, "
                "lesson_id, "
                "current_stage, "
                "status, "
                "progress_percent, "
                "mastery_score, "
                "last_activity_at"
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "lesson_id",
                coach_session["lesson_id"]
            )
            .limit(1)
            .execute()
        )

        if not progress_res.data:
            return {
                "has_active_lesson": False
            }

        progress = (
            progress_res.data[0]
        )

        # =============================================
        # LAST ASSISTANT MESSAGE
        # =============================================

        last_message_res = (
            sb.table(
                "kid_lesson_history"
            )
            .select(
                "id, "
                "content, "
                "sequence_json, "
                "created_at"
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "lesson_id",
                coach_session["lesson_id"]
            )
            .eq(
                "role",
                "assistant"
            )
            .order(
                "created_at",
                desc=True
            )
            .limit(1)
            .execute()
        )

        last_assistant_message = (
            last_message_res.data[0]
            if last_message_res.data
            else None
        )

        # =============================================
        # FULL CHAT HISTORY OF THIS UNIT LESSON (2026-09-16)
        #
        # Re-entering a lesson used to show only the last teacher
        # message. The child must see the whole conversation:
        # the explanation segments of the current part, the
        # question, and every exchange with the coach.
        # =============================================
        history_res = (
            sb.table("kid_lesson_history")
            .select("role, content, part_number, created_at")
            .eq("kid_id", child["id"])
            .eq("lesson_id", coach_session["lesson_id"])
            .eq("unit_lesson_id", coach_session["unit_lesson_id"])
            .order("created_at", desc=False)
            .order("id", desc=False)          # a child answer + coach reply share created_at: keep insert order
            .limit(80)
            .execute()
        )
        chat_history = [
            {"role": r.get("role"), "content": r.get("content"), "part_number": r.get("part_number"),
             "created_at": r.get("created_at")}
            for r in (history_res.data or []) if r.get("content")
        ]

        # =============================================
        # UNIT LESSON DETAILS
        # =============================================

        unit_lesson = get_unit_lesson(
            coach_session[
                "unit_lesson_id"
            ]
        )

        # =============================================
        # PARENT LESSON DETAILS
        # =============================================

        parent_lesson = get_learning_lesson(
            coach_session[
                "lesson_id"
            ]
        )

        return {
            "has_active_lesson": True,

            "progress_id":
                progress["id"],

            "lesson_id":
                progress["lesson_id"],

            "unit_lesson_id":
                coach_session[
                    "unit_lesson_id"
                ],

            "current_stage":
                progress.get(
                    "current_stage"
                ),

            "lesson_status":
                progress.get(
                    "status"
                ),

            "progress_percent":
                progress.get(
                    "progress_percent"
                ),

            "mastery_score":
                progress.get(
                    "mastery_score"
                ),

            "parent_lesson": {
                "id":
                    parent_lesson.get(
                        "id"
                    ),

                "lesson_name":
                    parent_lesson.get(
                        "lesson_name"
                    ),

                "subject":
                    parent_lesson.get(
                        "subject"
                    ),

                "category":
                    parent_lesson.get(
                        "category"
                    )
            },

            "unit_lesson": {
                "id":
                    unit_lesson.get(
                        "id"
                    ),

                "unit_order":
                    unit_lesson.get(
                        "unit_order"
                    ),

                "unit_name":
                    unit_lesson.get(
                        "unit_name"
                    ),

                "lesson_order":
                    unit_lesson.get(
                        "lesson_order"
                    ),

                "lesson_name":
                    unit_lesson.get(
                        "lesson_name"
                    )
            },

            "learning_coach": {
                "session_id":
                    coach_session.get(
                        "id"
                    ),

                "coach_index":
                    coach_session.get(
                        "coach_index"
                    ),

                "status":
                    coach_session.get(
                        "status"
                    ),

                "total_rounds":
                    coach_session.get(
                        "total_rounds"
                    ),

                "understanding_score":
                    coach_session.get(
                        "final_understanding_score"
                    )
            },

            "chat_history": chat_history,
            "resume_context": build_resume_context(unit_lesson, chat_history),
            "last_assistant_message": {
                "content":
                    (
                        last_assistant_message.get(
                            "content"
                        )
                        if last_assistant_message
                        else None
                    ),

                "sequence":
                    (
                        last_assistant_message.get(
                            "sequence_json"
                        )
                        if last_assistant_message
                        else None
                    )
            }
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "ACTIVE LESSON STATE ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load "
                "active lesson state"
            )
        )

@app.post(
    "/api/tutor/lesson-intro"
)
def lesson_intro(
        body: LessonIntroRequest,
        background_tasks: BackgroundTasks,
        authorization: str = Header(None)
):
    try:

        # =============================================
        # AUTH
        # =============================================

        user = authenticate_user(
            authorization
        )
        ai_context("intro", user, body)

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        # =============================================
        # CHILD
        # =============================================

        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )
        # =============================================
        # PERSONAL INTRO VIDEO ELIGIBILITY
        # =============================================

        personal_intro_eligible = False

        personal_intro_rows = []

        personal_intro_videos = []

        try:

            personal_intro_eligible = (
                is_paid_active_subscription(
                    user.id
                )
            )

            print(
                "KID PERSONAL INTRO ELIGIBILITY:",
                {
                    "user_id":
                        user.id,

                    "kid_id":
                        child["id"],

                    "eligible":
                        personal_intro_eligible
                }
            )

            if personal_intro_eligible:

                personal_intro_rows = (
                    ensure_kid_lesson_intro_rows(
                        child["id"]
                    )
                )

                personal_intro_videos = (
                    get_ready_kid_lesson_intro_videos(
                        child["id"]
                    )
                )
                # =====================================
                # GENERATE MISSING PERSONAL INTROS
                # IN BACKGROUND
                # =====================================

                ready_variants = {
                    int(
                        video.get(
                            "variant"
                        )
                        or 0
                    )
                    for video
                    in personal_intro_videos
                }

                missing_ready_variants = [
                    variant
                    for variant
                    in KID_LESSON_INTRO_VARIANTS
                    if variant
                    not in ready_variants
                ]

                if missing_ready_variants:

                    print(
                        "QUEUE KID PERSONAL INTRO GENERATION:",
                        {
                            "kid_id":
                                child["id"],

                            "missing_variants":
                                missing_ready_variants
                        }
                    )

                    dispatch_media_job(
                        background_tasks,
                        job_type="kid_intro_videos",
                        payload={
                            "kid_id": str(child["id"]),
                            "user_id": str(child["user_id"])
                        },
                        dedupe_key=f"kid:{child['id']}",
                        inline_fn=generate_kid_lesson_intro_videos_background,
                        inline_args=(child,)
                    )
        except Exception as personal_media_error:

            # תקלה במנגנון האישי לעולם לא
            # תפיל את פתיחת השיעור.
            #
            # במקרה כזה הפתיח הקולי הרגיל ממשיך.
            print(
                "KID PERSONAL INTRO CHECK FAILED:",
                {
                    "user_id":
                        user.id,

                    "kid_id":
                        child["id"],

                    "error":
                        repr(
                            personal_media_error
                        )
                }
            )

            personal_intro_eligible = False

            personal_intro_rows = []

            personal_intro_videos = []
        # =============================================
        # SELECTED UNIT LESSON
        # =============================================

        unit_lesson = get_unit_lesson(
            body.unit_lesson_id
        )

        # =============================================
        # PARENT LESSON
        # =============================================

        parent_lesson = get_learning_lesson(
            unit_lesson[
                "learning_lesson_id"
            ]
        )

        # =============================================
        # UNIT LESSON PROGRESS START
        #
        # lesson-intro is the real entry point used by
        # the current workspace when a child opens an
        # internal lesson. Persist that start here.
        # =============================================

        start_kid_unit_lesson_progress(
            kid_id=child["id"],
            learning_lesson_id=parent_lesson["id"],
            unit_lesson_id=unit_lesson["id"]
        )

        # =============================================
        # TUTOR SESSION
        # =============================================

        tutor_session = get_or_create_tutor_session(
            user_id=user.id,
            kid_id=child["id"]
        )

        session_id = tutor_session["id"]
        # =============================================
        # INTRO TEMPLATE
        # =============================================

        intro_template_id = (
            unit_lesson.get(
                "intro_template_id"
            )
        )

        if not intro_template_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No intro template assigned "
                    "to this lesson"
                )
            )

        intro_template = get_intro_template(
            intro_template_id
        )

        intro_json = (
            intro_template.get(
                "intro_json"
            )
            or {}
        )

        # =============================================
        # REPLACE VARIABLES
        # =============================================

        replacements = {
            "{child_name}":
                child.get(
                    "child_name"
                )
                or "",

            "{parent_lesson}":
                parent_lesson.get(
                    "lesson_name"
                )
                or "",

            "{unit_name}":
                unit_lesson.get(
                    "unit_name"
                )
                or "",

            "{lesson_name}":
                unit_lesson.get(
                    "lesson_name"
                )
                or "",

            "{subject}":
                parent_lesson.get(
                    "subject"
                )
                or "",

            "{grade}":
                child.get(
                    "age"
                )
                or ""
        }

        replacements.update(
            get_gender_placeholders(
                child
            )
        )

        rendered_intro = (
            replace_intro_variables(
                intro_json,
                replacements
            )
        )

        raw_steps = (
            rendered_intro.get(
                "steps"
            )
            or []
        )

        sequence = []

        for step in raw_steps:

            sequence.append(
                TutorAction(
                    type=step.get(
                        "type",
                        "write"
                    ),

                    text=step.get(
                        "text"
                    ),

                    target=step.get(
                        "target"
                    ),

                    style=step.get(
                        "style"
                    ),

                    speed=step.get(
                        "speed"
                    ),

                    duration=(
                        step.get(
                            "duration"
                        )
                        or step.get(
                            "duration_ms"
                        )
                    ),

                    speech_tts=step.get(
                        "speech_tts"
                    ),

                    title=step.get(
                        "title"
                    ),

                    items=step.get(
                        "items"
                    ),

                    icon=step.get(
                        "icon"
                    )
                )
            )

        # =============================================
        # GUARANTEE PERSONAL GREETING FIRST
        # =============================================

        child_name = str(
            child.get("child_name")
            or ""
        ).strip()

        child_name = lq.display_first_name(child_name)

        if child_name:
            greeting_text = (
                f"היי {child_name}! "
                f"כיף שבאת ללמוד איתי."
            )

            sequence.insert(
                0,
                TutorAction(
                    type="speak",
                    text=greeting_text,
                    speech_tts=greeting_text
                )
            )
        # Warm the TTS cache for this intro's sentences (greeting with the child's
        # name, shared closing line) so the browser's requests a second later are hits.
        try:
            _warm_texts = [a.speech_tts for a in sequence if getattr(a, "speech_tts", None)]
            if _warm_texts and TTS_CACHE_ENABLED:
                _threading.Thread(target=run_in_context(
                    warm_tts_cache, _warm_texts, hebrew_gender_rule(child)[0],
                    lq.display_first_name(child.get("child_name") or "")), daemon=True).start()
        except Exception as _warm_error:
            print("LIVE TTS CACHE WARM SCHEDULE FAILED:", repr(_warm_error)[:160])
        return {
            "success": True,

            "session_id":
                session_id,

            "unit_lesson_id":
                unit_lesson["id"],

            "learning_lesson_id":
                parent_lesson["id"],

            "intro_template_id":
                intro_template["id"],

            "intro_template_name":
                intro_template.get(
                    "template_name"
                ),

            "tts": {
                "provider":
                    intro_template.get(
                        "tts_provider"
                    ),

                "model":
                    intro_template.get(
                        "tts_model"
                    ),

                "voice":
                    intro_template.get(
                        "tts_voice"
                    )
            },

            "sequence": [
                action.model_dump()
                for action in sequence
            ],

            "wait_for_answer":
                False,

            "personal_intro": {

                "eligible":
                    personal_intro_eligible,

                "media_type":
                    KID_LESSON_INTRO_MEDIA_TYPE,

                "required_variants":
                    len(
                        KID_LESSON_INTRO_VARIANTS
                    ),

                "records_count":
                    len(
                        personal_intro_rows
                    ),

                "ready_count":
                    len(
                        personal_intro_videos
                    ),

                "videos":
                    personal_intro_videos
            }
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "LESSON INTRO ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Lesson intro failed"
        )

@app.post(
    "/api/tutor/unit-lesson"
)
async def get_or_generate_unit_lesson(
        body: UnitLessonRequest,
        background_tasks: BackgroundTasks,
        authorization: str = Header(None)
):
    unit_lesson = None

    try:

        # =============================================
        # AUTH
        # =============================================

        user = (await run_in_threadpool(lambda: authenticate_user(
            authorization
        )))
        ai_context("lesson", user, body)
        media_trace.trace_set(lesson=body.unit_lesson_id, kid=body.kid_id)

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        # מוודאים שהילד שייך למשתמש
        child = (await run_in_threadpool(lambda: get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )))
        # =============================================
        # ENSURE PERSONAL INTRO VIDEOS
        # PAID SUBSCRIBERS ONLY
        # =============================================

        try:

            personal_intro_eligible = (await run_in_threadpool(lambda: (
                is_paid_active_subscription(
                    user.id
                )
            )))

            print(
                "UNIT LESSON PERSONAL INTRO CHECK:",
                {
                    "user_id":
                        user.id,

                    "kid_id":
                        child["id"],

                    "eligible":
                        personal_intro_eligible
                }
            )

            if personal_intro_eligible:

                (await run_in_threadpool(lambda: ensure_kid_lesson_intro_rows(
                    child["id"]
                )))

                ready_intro_videos = (
                    get_ready_kid_lesson_intro_videos(
                        child["id"]
                    )
                )

                ready_variants = {
                    int(
                        video.get(
                            "variant"
                        )
                        or 0
                    )
                    for video
                    in ready_intro_videos
                }

                missing_variants = [
                    variant
                    for variant
                    in KID_LESSON_INTRO_VARIANTS
                    if variant
                    not in ready_variants
                ]

                if missing_variants:

                    print(
                        "QUEUE KID PERSONAL INTRO GENERATION:",
                        {
                            "kid_id":
                                child["id"],

                            "missing_variants":
                                missing_variants
                        }
                    )

                    await run_in_threadpool(lambda: dispatch_media_job(
                        background_tasks,
                        job_type="kid_intro_videos",
                        payload={
                            "kid_id": str(child["id"]),
                            "user_id": str(child["user_id"])
                        },
                        dedupe_key=f"kid:{child['id']}",
                        inline_fn=generate_kid_lesson_intro_videos_background,
                        inline_args=(child,)
                    ))

                else:

                    print(
                        "KID PERSONAL INTROS ALREADY READY:",
                        {
                            "kid_id":
                                child["id"]
                        }
                    )

        except Exception as personal_intro_error:

            print(
                "UNIT LESSON PERSONAL INTRO ERROR:",
                {
                    "kid_id":
                        child["id"],

                    "error":
                        repr(
                            personal_intro_error
                        )
                }
            )

            traceback.print_exc()
        # =============================================
        # UNIT LESSON
        # =============================================

        unit_lesson = (await run_in_threadpool(lambda: get_unit_lesson(
            body.unit_lesson_id
        )))

        parent_lesson = (await run_in_threadpool(lambda: get_learning_lesson(
            unit_lesson[
                "learning_lesson_id"
            ]
        )))

        # =============================================
        # GRADE SECURITY
        # =============================================

        child_grade = int(
            child.get(
                "age"
            )
            or 0
        )

        lesson_grade = int(
            parent_lesson.get(
                "grade"
            )
            or 0
        )

        if (
                child_grade
                and lesson_grade
                and child_grade != lesson_grade
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Lesson does not match "
                    "child grade"
                )
            )

        generation_status = (
            unit_lesson.get(
                "generation_status"
            )
            or "empty"
        )

        cached_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
        )
        audio_generation_status = (
                unit_lesson.get(
                    "audio_generation_status"
                )
                or "pending"
        )

        cached_audio = (
            unit_lesson.get(
                "lesson_audio_json"
            )
        )
        # =============================================
        # CACHE HIT
        # =============================================

        cached_structured_lesson = (
            cached_json.get(
                "structured_lesson"
            )
            if isinstance(
                cached_json,
                dict
            )
            else None
        )

        cached_lesson_has_parts = (
            isinstance(
                cached_structured_lesson,
                dict
            )
            and bool(
                cached_structured_lesson.get(
                    "parts"
                )
            )
        )

        cached_lesson_has_legacy_lesson = (
            isinstance(
                cached_structured_lesson,
                dict
            )
            and bool(
                cached_structured_lesson.get(
                    "lesson"
                )
            )
        )

        _quality = (cached_json or {}).get("quality") if isinstance(cached_json, dict) else None
        # Product decision 2026-09-16: a failed quality gate never blocks a lesson. The verdict
        # stays in generated_lesson_json.quality (ok=false) for the future admin review screen;
        # only an explicit generation_status="needs_review" (set by a human) withholds a lesson.
        if isinstance(_quality, dict) and _quality.get("ok") is False and not _quality.get("approved_by_human"):
            print("UNIT LESSON FLAGGED FOR REVIEW (served anyway):", {"unit_lesson_id": unit_lesson["id"], "errors": (_quality.get("errors") or [])[:2]})
        _needs_review = generation_status == "needs_review"
        if _needs_review:

            # the quality gate failed for this lesson: do NOT regenerate on every open (cost loop);

            # it is released by a fix + re-run of the gate, or by tools/lesson_gate.py --approve

            print("UNIT LESSON NEEDS REVIEW (served as unavailable):", {"unit_lesson_id": unit_lesson["id"]})

            return {

                "success": False,

                "source": "needs_review",

                "unit_lesson_id": unit_lesson["id"],

                "generation_status": "needs_review",

                "quality": (cached_json or {}).get("quality") if isinstance(cached_json, dict) else None,

                "message": "השיעור הזה בבדיקת איכות ויחזור בקרוב. אפשר לבחור שיעור אחר בינתיים."

            }

        if (
                generation_status == "ready"
                and isinstance(
                    cached_json,
                    dict
                )
                and isinstance(
                    cached_structured_lesson,
                    dict
                )
                and (
                    cached_lesson_has_parts
                    or
                    cached_lesson_has_legacy_lesson
                )
        ):

            # =========================================
            # REPAIR OLD CACHED LESSON WITHOUT VISUAL PLAN
            # =========================================

            cached_visual_plan = (
                    cached_json.get("visual_plan")
                    or {}
            )

            cached_visuals = (
                    cached_visual_plan.get("visuals")
                    or []
            )

            structured_lesson = (
                    cached_json.get(
                        "structured_lesson"
                    )
                    or {}
            )

            lesson_parts = (
                structured_lesson.get(
                    "parts"
                )
                or []
            )

            expected_segments = []

            if lesson_parts:

                for lesson_part in lesson_parts:

                    if not isinstance(
                            lesson_part,
                            dict
                    ):
                        continue

                    part_segments = (
                        lesson_part.get(
                            "lesson"
                        )
                        or []
                    )

                    expected_segments.extend(
                        part_segments
                    )

            else:

                # Legacy fallback for old cached lessons.
                expected_segments = (
                    structured_lesson.get(
                        "lesson"
                    )
                    or []
                )

            expected_questions_count = 0

            if lesson_parts:

                for lesson_part in lesson_parts:

                    if not isinstance(
                            lesson_part,
                            dict
                    ):
                        continue

                    question = (
                        lesson_part.get(
                            "question"
                        )
                        or {}
                    )

                    question_text = str(
                        question.get(
                            "text"
                        )
                        or ""
                    ).strip()

                    if question_text:
                        expected_questions_count += 1

            else:

                legacy_question = (
                    structured_lesson.get(
                        "question"
                    )
                    or {}
                )

                legacy_question_text = str(
                    legacy_question.get(
                        "text"
                    )
                    or ""
                ).strip()

                if legacy_question_text:
                    expected_questions_count = 1

            expected_visuals_count = (
                len(
                    expected_segments
                )
                +
                expected_questions_count
            )

            visual_plan_needs_repair = (
                not cached_visuals
                or
                len(
                    cached_visuals
                )
                !=
                expected_visuals_count
            )

            if visual_plan_needs_repair:

                print(
                    "CACHED LESSON VISUAL PLAN NEEDS REPAIR:",
                    {
                        "unit_lesson_id":
                            unit_lesson["id"],

                        "segments_count":
                            len(expected_segments),

                        "questions_count":
                            expected_questions_count,

                        "expected_visuals_count":
                            expected_visuals_count,

                        "visuals_count":
                            len(cached_visuals)
                    }
                )

                lesson_text_parts = []

                cached_lesson_parts = (
                    structured_lesson.get(
                        "parts"
                    )
                    or []
                )

                if cached_lesson_parts:

                    for lesson_part in cached_lesson_parts:

                        if not isinstance(
                                lesson_part,
                                dict
                        ):
                            continue

                        part_number = int(
                            lesson_part.get(
                                "part_number"
                            )
                            or 0
                        )

                        part_segments = (
                            lesson_part.get(
                                "lesson"
                            )
                            or []
                        )

                        part_text = "\n".join(
                            [
                                str(
                                    segment.get(
                                        "text"
                                    )
                                    or ""
                                ).strip()
                                for segment in part_segments
                                if isinstance(
                                    segment,
                                    dict
                                )
                                and str(
                                    segment.get(
                                        "text"
                                    )
                                    or ""
                                ).strip()
                            ]
                        )

                        if part_text:

                            lesson_text_parts.append(
                                (
                                    f"Part {part_number}:\n"
                                    f"{part_text}"
                                )
                            )

                    lesson_text = "\n\n".join(
                        lesson_text_parts
                    ).strip()

                else:

                    # Legacy fallback for old cached lessons.
                    lesson_text = str(
                        cached_json.get(
                            "lesson"
                        )
                        or ""
                    ).strip()

                visual_director_prompt = (
                    build_visual_director_prompt(
                        unit_lesson=
                        unit_lesson,

                        parent_lesson=
                        parent_lesson,

                        lesson_text=
                        lesson_text,

                        structured_lesson=
                        structured_lesson
                    )
                )

                visual_director_completion = (await (
                    aclient.beta.chat.completions.parse(

                        model=
                        DEFAULT_OPENAI_MODEL,

                        messages=[
                            {
                                "role":
                                    "system",

                                "content":
                                    visual_director_prompt
                            },
                            {
                                "role":
                                    "user",

                                "content":
                                    (
                                        "Analyze the lesson and create "
                                        "the visual media plan. "
                                        "Return only the required structure."
                                    )
                            }
                        ],

                        response_format=
                        VisualDirectorResponse
                    )
                ))

                visual_director_data = (
                    visual_director_completion
                    .choices[0]
                    .message
                    .parsed
                )

                if visual_director_data:
                    repaired_visual_plan = (
                        normalize_visual_plan_to_segments(
                            visual_plan=
                            visual_director_data.model_dump(),

                            structured_lesson=
                            structured_lesson,

                            unit_lesson=
                            unit_lesson,

                            parent_lesson=
                            parent_lesson
                        )
                    )

                    cached_json[
                        "visual_plan"
                    ] = repaired_visual_plan

                    (await run_in_threadpool(lambda: sb.table(
                        "lesson_units_content"
                    ).update({

                        "generated_lesson_json":
                            cached_json,

                        "updated_at":
                            datetime
                            .now(timezone.utc)
                            .isoformat()

                    }).eq(
                        "id",
                        unit_lesson["id"]
                    ).execute()))

                    print(
                        "CACHED VISUAL PLAN REPAIRED:",
                        {
                            "unit_lesson_id":
                                unit_lesson["id"],

                            "visuals_count":
                                len(
                                    repaired_visual_plan
                                    .get("visuals")
                                    or []
                                )
                        }
                    )

            response_audio = None

            # =========================================
            # TRY STORED AUDIO
            #
            # חשוב:
            # ייתכן שב-DB האודיו מסומן ready,
            # אבל הקבצים עצמם נמחקו מה-Storage.
            #
            # מצב כזה הוא CACHE MISS של המדיה בלבד.
            # אסור להפיל בגללו את כל השיעור.
            # =========================================

            cached_audio_has_parts = (
                isinstance(
                    cached_audio,
                    dict
                )
                and bool(
                    cached_audio.get(
                        "parts"
                    )
                )
            )

            cached_audio_has_legacy_segments = (
                isinstance(
                    cached_audio,
                    dict
                )
                and bool(
                    cached_audio.get(
                        "segments"
                    )
                )
            )

            if (
                    audio_generation_status == "ready"
                    and (
                        cached_audio_has_parts
                        or
                        cached_audio_has_legacy_segments
                    )
            ):

                try:

                    response_audio = (await run_in_threadpool(lambda: (
                        add_signed_urls_to_lesson_audio(
                            cached_audio
                        )
                    )))

                    media_trace.waiting("audio HIT", lesson=unit_lesson["id"], lesson_age_s=media_trace.lesson_age_s(unit_lesson))
                    print(
                        "UNIT LESSON AUDIO CACHE HIT:",
                        {
                            "unit_lesson_id":
                                unit_lesson["id"]
                        }
                    )

                except Exception as audio_cache_error:

                    media_trace.waiting("audio MISS -> repair queued", lesson=unit_lesson["id"], lesson_age_s=media_trace.lesson_age_s(unit_lesson))
                    print(
                        "UNIT LESSON AUDIO CACHE MISS:",
                        {
                            "unit_lesson_id":
                                unit_lesson["id"],

                            "error":
                                repr(
                                    audio_cache_error
                                )
                        }
                    )

                    # ---------------------------------
                    # ה-DB מצביע על קבצים שכבר אינם
                    # קיימים ב-Storage.
                    #
                    # מאפסים רק את האודיו,
                    # לא את תוכן השיעור.
                    # ---------------------------------

                    audio_generation_status = (
                        "pending"
                    )

                    cached_audio = None

                    (await run_in_threadpool(lambda: sb.table(
                        "lesson_units_content"
                    ).update({

                        "audio_generation_status":
                            "pending",

                        "lesson_audio_json":
                            None,

                        "audio_generation_error":
                            None,

                        "audio_generated_at":
                            None,

                        "tts_generated_at":
                            None,

                        "updated_at":
                            datetime
                            .now(timezone.utc)
                            .isoformat()

                    }).eq(
                        "id",
                        unit_lesson["id"]
                    ).execute()))

            # =========================================
            # BACKGROUND AUDIO REPAIR ONLY
            #
            # אם האודיו כבר קיים ותקין,
            # אין שום סיבה להפעיל מחדש את כל
            # מנגנון המדיה בכל Refresh.
            #
            # זה מונע עשרות קריאות מיותרות
            # ל-Supabase בכל טעינת עמוד.
            # =========================================

            # Progressive audio: while the worker is still synthesising, hand
            # the browser whatever segments are already stored.
            response_audio_partial = None
            if (
                    response_audio is None
                    and audio_generation_status == "generating"
                    and cached_audio_has_parts
            ):
                try:
                    response_audio_partial = (await run_in_threadpool(lambda: (
                        add_signed_urls_to_lesson_audio(cached_audio)
                    )))
                except Exception as partial_error:
                    print(
                        "PARTIAL LESSON AUDIO SIGN FAILED:",
                        {"unit_lesson_id": unit_lesson["id"], "error": repr(partial_error)[:200]}
                    )

            if response_audio is None:

                print(
                    "QUEUE BACKGROUND AUDIO REPAIR:",
                    {
                        "unit_lesson_id":
                            unit_lesson["id"],

                        "audio_generation_status":
                            audio_generation_status
                    }
                )

                await run_in_threadpool(lambda: dispatch_media_job(
                    background_tasks,
                    job_type="unit_lesson_audio",
                    payload={"unit_lesson_id": int(unit_lesson["id"])},
                    dedupe_key=f"unit_lesson:{unit_lesson['id']}",
                    inline_fn=generate_unit_lesson_audio_background,
                    inline_args=(unit_lesson["id"],)
                ))

            else:

                print(
                    "SKIP BACKGROUND MEDIA - CACHE COMPLETE:",
                    {
                        "unit_lesson_id":
                            unit_lesson["id"]
                    }
                )

            # =========================================
            # BACKGROUND VISUAL REPAIR
            #
            # גם אם תוכן השיעור נמצא ב-cache,
            # ייתכן שקבצי התמונות נמחקו מה-Storage.
            #
            # הפונקציה עצמה בודקת כל visual:
            # קיים -> CACHE HIT ולא מייצרת מחדש
            # חסר  -> מייצרת מחדש
            # =========================================

            print(
                "QUEUE BACKGROUND VISUAL CHECK:",
                {
                    "unit_lesson_id":
                        unit_lesson["id"]
                }
            )

            await run_in_threadpool(lambda: dispatch_media_job(
                background_tasks,
                job_type="unit_lesson_visuals",
                payload={"unit_lesson_id": int(unit_lesson["id"])},
                dedupe_key=f"unit_lesson:{unit_lesson['id']}",
                inline_fn=generate_all_lesson_visuals_background,
                inline_args=(unit_lesson["id"],)
            ))

            # =========================================
            # SHARED TRANSITION JSON REPAIR
            # =========================================

            expected_transition = {
                "type": "shared",
                "transition_key": "middle"
            }

            cached_transition = (
                cached_json.get(
                    "transition"
                )
            )

            if (
                    not isinstance(
                        cached_transition,
                        dict
                    )
                    or
                    cached_transition.get(
                        "type"
                    ) != "shared"
                    or
                    cached_transition.get(
                        "transition_key"
                    ) != "middle"
            ):

                print(
                    "SHARED TRANSITION JSON REPAIR:",
                    {
                        "unit_lesson_id":
                            unit_lesson["id"]
                    }
                )

                cached_json[
                    "transition"
                ] = expected_transition

                (await run_in_threadpool(lambda: supabase_with_retry(
                    lambda:
                        sb.table(
                            "lesson_units_content"
                        ).update({

                            "generated_lesson_json":
                                cached_json,

                            "updated_at":
                                datetime
                                .now(timezone.utc)
                                .isoformat()

                        }).eq(
                            "id",
                            unit_lesson["id"]
                        ).execute(),

                    label=
                        "SAVE SHARED TRANSITION"
                )))
            print(
                "QUEUE BACKGROUND TRANSITION VIDEO CHECK:",
                {
                    "unit_lesson_id":
                        unit_lesson["id"]
                }
            )

            await run_in_threadpool(lambda: dispatch_media_job(
                background_tasks,
                job_type="unit_lesson_transition",
                payload={"unit_lesson_id": int(unit_lesson["id"])},
                dedupe_key=f"unit_lesson:{unit_lesson['id']}",
                inline_fn=generate_transition_video_background,
                inline_args=(unit_lesson["id"],)
            ))

            # =========================================
            # RESPONSE
            # =========================================

            return {

                "success":
                    True,

                "source":
                    "cache",

                "unit_lesson_id":
                    unit_lesson["id"],

                "learning_lesson_id":
                    parent_lesson["id"],

                "generation_status":
                    "ready",

                "content_version":
                    unit_lesson.get(
                        "content_version"
                    )
                    or 1,

                "lesson":
                    cached_json.get(
                        "lesson"
                    ),

                "structured_lesson":
                    cached_json.get(
                        "structured_lesson"
                    ),

                "transition":
                    add_transition_video_signed_url(
                        cached_json.get(
                            "transition"
                        )
                    ),

                "audio_generation_status":
                    (
                        "ready"
                        if response_audio
                        else (
                            "generating"
                            if response_audio_partial
                            else "pending"
                        )
                    ),

                "audio_mode":
                    (
                        "stored"
                        if response_audio
                        else (
                            "stored_progressive"
                            if response_audio_partial
                            else "background_generating"
                        )
                    ),

                "lesson_audio":
                    response_audio or response_audio_partial
            }

        # =============================================
        # ALREADY GENERATING
        # =============================================

        if generation_status == "generating":
            return {
                "success": False,

                "source": "generating",

                "unit_lesson_id":
                    unit_lesson["id"],

                "learning_lesson_id":
                    parent_lesson["id"],

                "generation_status":
                    "generating",

                "sequence": [],

                "wait_for_answer": False
            }

        # =============================================
        # MARK AS GENERATING
        # =============================================

        now = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        (await run_in_threadpool(lambda: sb.table(
            "lesson_units_content"
        ).update({

            "generation_status":
                "generating",

            "generation_error":
                None,

            "updated_at":
                now

        }).eq(
            "id",
            unit_lesson["id"]
        ).execute()))
        lesson_parts_count = int(
            unit_lesson.get(
                "lesson_parts_count"
            )
            or 2
        )

        lesson_parts_count = max(
            1,
            min(
                lesson_parts_count,
                6
            )
        )

        print(
            "========== LESSON PARTS COUNT ==========",
            {
                "unit_lesson_id":
                    unit_lesson["id"],

                "lesson_parts_count":
                    lesson_parts_count
            }
        )
        # =============================================
        # BUILD UNIVERSAL PROMPT
        # =============================================

        system_prompt = (
            build_universal_unit_lesson_prompt(
                unit_lesson=
                    unit_lesson,

                parent_lesson=
                    parent_lesson
            )
        )

        # =============================================
        # OPENAI
        # =============================================

        _t_p1 = media_trace.mark_start("text_part1_teacher", model=UNIVERSAL_LESSON_MODEL)
        completion = (await (
            aclient.beta.chat.completions.parse(

                model=UNIVERSAL_LESSON_MODEL,

                messages=[

                    {
                        "role":
                            "system",

                        "content":
                            system_prompt
                    },

                    {
                        "role":
                            "user",

                        "content":
                            (
                                "צרו עכשיו את השיעור "
                                "המובנה והאוניברסלי. "
                                "השיגו במדויק את מטרת הלמידה. "
                                "התאימו את עומק ההסבר "
                                "לרמת המורכבות שהוגדרה. "
                                "אין חובה להשתמש בכל הזמן המקסימלי. "
                                "סיימו כאשר ההסבר ברור ושלם. "
                                "החזירו את רצף הפעולות בלבד "
                                "לפי מבנה התגובה."
                            )
                    }

                ],

                response_format=
                UniversalLessonResponse

            )
        ))

        media_trace.mark_done("text_part1_teacher", _t_p1)
        lesson_data = (
            completion
            .choices[0]
            .message
            .parsed
        )


        if not lesson_data:
            raise RuntimeError(
                "Universal unit lesson "
                "returned no response"
            )

        part_1_explanation = (
            lesson_data.explanation.strip()
        )

        part_1_question = (
            lesson_data.question.strip()
        )

        if not part_1_explanation:
            raise RuntimeError(
                "Initial lesson returned empty explanation"
            )

        if not part_1_question:
            raise RuntimeError(
                "Initial lesson returned empty question"
            )

        # =============================================
        # PART 1 DIRECTOR
        # Structures one complete learning unit.
        # It must not create or split lesson parts.
        # Same model + same input as every other part:
        # the explanation is the user message and is
        # also injected into the prompt ({lesson_text}).
        # =============================================
        # Director of part 1 only needs part 1's explanation, and the teacher of
        # part 2 only needs part 1's explanation + question: run them side by side
        # (saves ~16 s per new lesson, measured 2026-09-15 on lesson 29).
        _t_dir1 = media_trace.mark_start("text_part1_director", parallel_with="text_part2_teacher")

        async def _direct_part_1():
            result = await direct_lesson_part(
                explanation=part_1_explanation,
                question=part_1_question,
                part_number=1,
                unit_lesson_id=unit_lesson["id"]
            )
            media_trace.mark_done("text_part1_director", _t_dir1)
            return result

        director_1_task = asyncio.create_task(_direct_part_1())
        generated_parts_context = [
            {
                "part_number": 1,
                "explanation":
                    part_1_explanation,
                "question":
                    part_1_question
            }
        ]

        generated_parts = []      # part 1 is inserted once its director finishes (below)

        expansion_completions = []
        expansion_director_completions = []

        for part_number in range(
                2,
                lesson_parts_count + 1
        ):

            expansion_prompt = (
                build_lesson_expansion_prompt(
                    unit_lesson=
                        unit_lesson,

                    parent_lesson=
                        parent_lesson,

                    part_number=
                        part_number,

                    previous_parts=
                        generated_parts_context
                )
            )

            _t_exp = media_trace.mark_start(f"text_part{part_number}_teacher", model=UNIVERSAL_LESSON_MODEL)
            expansion_completion = (await (
                aclient.beta.chat.completions.parse(

                    model=
                        UNIVERSAL_LESSON_MODEL,

                    messages=[
                        {
                            "role":
                                "system",

                            "content":
                                expansion_prompt
                        },

                        {
                            "role":
                                "user",

                            "content":
                                (
                                    "Create the next "
                                    "lesson part now."
                                )
                        }
                    ],

                    response_format=
                        UniversalLessonResponse
                )
            ))

            media_trace.mark_done(f"text_part{part_number}_teacher", _t_exp)
            expansion_data = (
                expansion_completion
                .choices[0]
                .message
                .parsed
            )

            if not expansion_data:
                raise RuntimeError(
                    (
                        "Expansion returned no "
                        f"Part {part_number}"
                    )
                )

            expansion_explanation = (
                expansion_data
                .explanation
                .strip()
            )

            expansion_question = (
                expansion_data
                .question
                .strip()
            )

            if not expansion_explanation:
                raise RuntimeError(
                    (
                        "Expansion returned empty "
                        f"explanation for Part "
                        f"{part_number}"
                    )
                )

            if not expansion_question:
                raise RuntimeError(
                    (
                        "Expansion returned empty "
                        f"question for Part "
                        f"{part_number}"
                    )
                )

            _t_dir = media_trace.mark_start(f"text_part{part_number}_director")
            directed_part, expansion_director_completion = (
                await direct_lesson_part(
                    explanation=expansion_explanation,
                    question=expansion_question,
                    part_number=part_number,
                    unit_lesson_id=unit_lesson["id"]
                )
            )

            media_trace.mark_done(f"text_part{part_number}_director", _t_dir)
            generated_parts.append(
                {
                    "part_number":
                        part_number,

                    **directed_part
                }
            )

            generated_parts_context.append(
                {
                    "part_number":
                        part_number,

                    "explanation":
                        expansion_explanation,

                    "question":
                        expansion_question
                }
            )

            expansion_completions.append(
                expansion_completion
            )

            expansion_director_completions.append(
                expansion_director_completion
            )
        part_1, director_completion = await director_1_task
        generated_parts.insert(0, {"part_number": 1, **part_1})
        structured_lesson = {
            "parts":
                generated_parts,

            # Temporary compatibility fields.
            "lesson":
                part_1["lesson"],

            "question":
                part_1["question"]
        }

        # Add temporary part aliases for existing code.
        for generated_part in generated_parts:
            generated_part_number = int(
                generated_part[
                    "part_number"
                ]
            )

            structured_lesson[
                f"part_{generated_part_number}"
            ] = generated_part

        # =============================================
        # SHARED LESSON TRANSITION
        #
        # Transitions between lesson parts are handled
        # by the shared frontend transition asset.
        # =============================================

        lesson_transition = {
            "type": "shared",
            "transition_key": "middle"
        }
        lesson_text = "\n\n".join(
            [
                "\n".join(
                    [
                        str(
                            segment.get(
                                "text"
                            )
                            or ""
                        ).strip()
                        for segment in (
                            part.get(
                                "lesson"
                            )
                            or []
                        )
                        if isinstance(
                            segment,
                            dict
                        )
                    ]
                )
                for part in generated_parts
                if isinstance(
                    part,
                    dict
                )
            ]
        ).strip()
        # =============================================
        # VISUAL DIRECTOR
        # מחליט אילו המחשות דרושות לשיעור
        # ומתי להציג תמונה או וידאו
        # =============================================

        visual_director_prompt = (
            build_visual_director_prompt(
                unit_lesson=
                unit_lesson,

                parent_lesson=
                parent_lesson,

                lesson_text=
                lesson_text,

                structured_lesson=
                structured_lesson
            )
        )

        print(
            "========== VISUAL DIRECTOR START ==========",
            {
                "unit_lesson_id":
                    unit_lesson["id"],

                "lesson_name":
                    unit_lesson.get(
                        "lesson_name"
                    ),

                "lesson_text_length":
                    len(
                        lesson_text
                        or ""
                    )
            }
        )

        _t_vd = media_trace.mark_start("visual_director", model=DEFAULT_OPENAI_MODEL)
        visual_director_completion = (await (
            aclient.beta.chat.completions.parse(

                model=
                DEFAULT_OPENAI_MODEL,

                messages=[
                    {
                        "role":
                            "system",

                        "content":
                            visual_director_prompt
                    },

                    {
                        "role":
                            "user",

                        "content":
                            (
                                "Analyze the lesson and create "
                                "the visual media plan. "
                                "Return only the required structure."
                            )
                    }
                ],

                response_format=
                VisualDirectorResponse
            )
        ))

        media_trace.mark_done("visual_director", _t_vd)
        visual_director_data = (
            visual_director_completion
            .choices[0]
            .message
            .parsed
        )

        if not visual_director_data:
            raise RuntimeError(
                "Visual Director returned no response"
            )

        visual_plan = (
            visual_director_data
            .model_dump()
        )

        visual_plan = (
            normalize_visual_plan_to_segments(
                visual_plan=
                visual_plan,

                structured_lesson=
                structured_lesson,

                unit_lesson=
                unit_lesson,

                parent_lesson=
                parent_lesson
            )
        )

        print(
            "========== VISUAL DIRECTOR RESULT =========="
        )

        print(
            json.dumps(
                visual_plan,
                ensure_ascii=False,
                indent=2
            )
        )

        lesson_json = {

            "generation_model":
                UNIVERSAL_LESSON_MODEL,

            "director_model":
                UNIVERSAL_LESSON_MODEL,

            "learning_objective":
                unit_lesson.get(
                    "learning_objective"
                ),

            "lesson_complexity":
                unit_lesson.get(
                    "lesson_complexity"
                ),

            "max_duration_seconds":
                unit_lesson.get(
                    "max_duration_seconds"
                ),

            # נשאר זמנית כדי לא לשבור את הפרונט
            "lesson":
                lesson_text,

            # המבנה החדש
            "structured_lesson":
                structured_lesson,

            "transition":
                lesson_transition,

            # תוכנית ההמחשות של Visual Director
            "visual_director_model":
                DEFAULT_OPENAI_MODEL,

            "visual_plan":
                visual_plan
        }

        # =============================================
        # SAVE CACHE
        # =============================================

        content_version = int(
            unit_lesson.get(
                "content_version"
            )
            or 1
        )
        if unit_lesson.get("generated_lesson_json"):
            # regenerating over existing content: new version so old audio/images can never be served
            content_version += 1
            print("LESSON CONTENT VERSION BUMPED (regeneration):", {"unit_lesson_id": unit_lesson["id"], "content_version": content_version})

        generated_at = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        (await run_in_threadpool(lambda: sb.table(
            "lesson_units_content"
        ).update({

            "generated_lesson_json":
                lesson_json,

            "generation_status":
                "ready",

            "generation_error":
                None,

            "content_version":
                content_version,

            "generated_at":
                generated_at,

            # האודיו החדש עדיין לא מוכן
            "audio_generation_status":
                "pending",

            "lesson_audio_json":
                None,

            "audio_generation_error":
                None,

            "audio_generated_at":
                None,

            "tts_generated_at":
                None,

            "updated_at":
                generated_at

        }).eq(
            "id",
            unit_lesson["id"]
        ).execute()))

        # =============================================
        # USAGE
        # =============================================

        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        director_input_tokens = 0
        director_output_tokens = 0
        director_total_tokens = 0

        if completion.usage:

            input_tokens = (
                completion
                .usage
                .prompt_tokens
                or 0
            )

            output_tokens = (
                completion
                .usage
                .completion_tokens
                or 0
            )

            total_tokens = (
                completion
                .usage
                .total_tokens
                or 0
            )

        if director_completion.usage:

            director_input_tokens = (
                director_completion
                .usage
                .prompt_tokens
                or 0
            )

            director_output_tokens = (
                director_completion
                .usage
                .completion_tokens
                or 0
            )

            director_total_tokens = (
                director_completion
                .usage
                .total_tokens
                or 0
            )

        openai_cost_usd = calculate_openai_cost(
            model=UNIVERSAL_LESSON_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        director_cost_usd = calculate_openai_cost(
            model=UNIVERSAL_LESSON_MODEL,
            input_tokens=director_input_tokens,
            output_tokens=director_output_tokens
        )

        (await run_in_threadpool(lambda: increment_usage_summary(

            user_id=
                user.id,

            ai_calls=
                2,

            input_tokens=(
                input_tokens
                + director_input_tokens
            ),

            output_tokens=(
                output_tokens
                + director_output_tokens
            ),

            total_tokens=(
                total_tokens
                + director_total_tokens
            ),

            openai_cost_usd=(
                openai_cost_usd
                + director_cost_usd
            )

        )))
        # =============================================
        # START AUDIO GENERATION IN BACKGROUND
        # =============================================
        print(
            "QUEUE BACKGROUND AUDIO AFTER LESSON GENERATION:",
            {
                "unit_lesson_id": unit_lesson["id"],
                "content_version": content_version,
                "segments_count": len(
                    structured_lesson.get("lesson")
                    or []
                ),
                "has_question": bool(
                    (
                            structured_lesson.get("question")
                            or {}
                    ).get("text")
                )
            }
        )
        _t_enq = media_trace.mark_start("enqueue_media_job", lesson=unit_lesson["id"])
        await run_in_threadpool(lambda: dispatch_media_job(
            background_tasks,
            job_type="unit_lesson_media",
            payload={"unit_lesson_id": int(unit_lesson["id"])},
            dedupe_key=f"unit_lesson:{unit_lesson['id']}",
            inline_fn=generate_unit_lesson_media_background,
            inline_args=(unit_lesson["id"],)
        ))
        media_trace.mark_done("enqueue_media_job", _t_enq)
        media_trace.summary("STAGE SUMMARY (unit-lesson text generated; media queued)", lesson=unit_lesson["id"], parts=len(generated_parts))

        # =============================================
        # RESPONSE
        # =============================================

        return {
            "success": True,

            "source": "generated",

            "unit_lesson_id":
                unit_lesson["id"],

            "learning_lesson_id":
                parent_lesson["id"],

            "generation_status":
                "ready",

            "content_version":
                content_version,

            "lesson":
                lesson_json.get(
                    "lesson"
                ),

            "structured_lesson":
                lesson_json.get(
                    "structured_lesson"
                ),

            "transition":
                add_transition_video_signed_url(
                    lesson_json.get(
                        "transition"
                    )
                ),

            "audio_generation_status":
                "pending",

            "lesson_audio":
                None
        }

    except HTTPException:
        raise

    except Exception as e:

        error_message = repr(e)

        print(
            "UNIT LESSON GENERATION ERROR:",
            error_message
        )
        traceback.print_exc()
        # =============================================
        # MARK AS FAILED
        # =============================================

        if unit_lesson:

            try:

                (await run_in_threadpool(lambda: sb.table(
                    "lesson_units_content"
                ).update({

                    "generation_status":
                        "failed",

                    "generation_error":
                        str(e)[:1500],

                    "updated_at":
                        datetime
                        .now(timezone.utc)
                        .isoformat()

                }).eq(
                    "id",
                    unit_lesson["id"]
                ).execute()))

            except Exception as update_error:

                print(
                    "UNIT LESSON FAILURE UPDATE ERROR:",
                    repr(update_error)
                )

        raise HTTPException(
            status_code=500,
            detail="Unit lesson generation failed"
        )

# =====================================================
# REGENERATE UNIT LESSON TRANSITION ONLY
# =====================================================

@app.post(
    "/api/tutor/unit-lesson/regenerate-transition"
)
async def regenerate_unit_lesson_transition(
        body: UnitLessonRequest,
        background_tasks: BackgroundTasks,
        authorization: str = Header(None)
):
    try:

        # =============================================
        # AUTH
        # =============================================

        user = (await run_in_threadpool(lambda: authenticate_user(
            authorization
        )))
        ai_context("transition", user, body)

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        child = (await run_in_threadpool(lambda: get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )))

        # =============================================
        # LOAD EXISTING LESSON
        # =============================================

        unit_lesson = (await run_in_threadpool(lambda: get_unit_lesson(
            body.unit_lesson_id
        )))

        parent_lesson = (await run_in_threadpool(lambda: get_learning_lesson(
            unit_lesson[
                "learning_lesson_id"
            ]
        )))

        # =============================================
        # GRADE SECURITY
        # =============================================

        child_grade = int(
            child.get("age")
            or 0
        )

        lesson_grade = int(
            parent_lesson.get("grade")
            or 0
        )

        if (
            child_grade
            and lesson_grade
            and child_grade != lesson_grade
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Lesson does not match "
                    "child grade"
                )
            )

        # =============================================
        # EXISTING LESSON JSON
        # =============================================

        generated_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
            or {}
        )

        structured_lesson = (
            generated_json.get(
                "structured_lesson"
            )
            or {}
        )

        if not structured_lesson:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Structured lesson is missing"
                )
            )

        if (
            not structured_lesson.get(
                "part_1"
            )
            or
            not structured_lesson.get(
                "part_2"
            )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Part 1 or Part 2 is missing"
                )
            )

        # =============================================
        # GENERATE ONLY NEW TRANSITION
        # =============================================

        new_transition = (await (
            regenerate_lesson_transition_only(
                unit_lesson=
                    unit_lesson,

                parent_lesson=
                    parent_lesson
            )
        ))

        # =============================================
        # REPLACE ONLY TRANSITION IN JSON
        # =============================================

        generated_json[
            "transition"
        ] = new_transition

        now_iso = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        (await run_in_threadpool(lambda: sb.table(
            "lesson_units_content"
        ).update({

            "generated_lesson_json":
                generated_json,

            "updated_at":
                now_iso

        }).eq(
            "id",
            unit_lesson["id"]
        ).execute()))

        # =============================================
        # DELETE OLD TRANSITION VIDEO ONLY
        #
        # התמונות, האודיו והשיעור עצמו נשארים.
        # =============================================

        content_version = int(
            unit_lesson.get(
                "content_version"
            )
            or 1
        )

        video_storage_path = (
            f"unit_lessons/"
            f"{unit_lesson['id']}/"
            f"v{content_version}/"
            f"transition/"
            f"transition_part_1_to_2.mp4"
        )

        try:

            (await run_in_threadpool(lambda: sb.storage.from_(
                LESSON_MEDIA_BUCKET
            ).remove([
                video_storage_path
            ])))

            print(
                "OLD TRANSITION VIDEO REMOVED:",
                {
                    "unit_lesson_id":
                        unit_lesson["id"],

                    "storage_path":
                        video_storage_path
                }
            )

        except Exception as delete_error:

            print(
                "OLD TRANSITION VIDEO REMOVE SKIPPED:",
                {
                    "unit_lesson_id":
                        unit_lesson["id"],

                    "error":
                        repr(delete_error)
                }
            )

        # =============================================
        # GENERATE NEW VIDEO IN BACKGROUND
        # =============================================

        print(
            "QUEUE NEW TRANSITION VIDEO:",
            {
                "unit_lesson_id":
                    unit_lesson["id"]
            }
        )

        await run_in_threadpool(lambda: dispatch_media_job(
            background_tasks,
            job_type="unit_lesson_transition",
            payload={"unit_lesson_id": int(unit_lesson["id"])},
            dedupe_key=f"unit_lesson:{unit_lesson['id']}",
            inline_fn=generate_transition_video_background,
            inline_args=(unit_lesson["id"],)
        ))

        # =============================================
        # RESPONSE
        # =============================================

        return {
            "success":
                True,

            "unit_lesson_id":
                unit_lesson["id"],

            "transition":
                new_transition,

            "video_status":
                "generating"
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "REGENERATE TRANSITION ERROR:",
            {
                "unit_lesson_id":
                    body.unit_lesson_id,

                "error":
                    repr(e)
            }
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to regenerate "
                "lesson transition"
            )
        )

# =====================================================
# UNIT LESSON HERO IMAGE
# =====================================================

@app.post(
    "/api/tutor/unit-lesson/hero-image"
)
async def get_or_generate_unit_lesson_hero_image(
        body: UnitLessonRequest,
        authorization: str = Header(None)
):
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 0.7

    try:

        # =============================================
        # AUTH
        # =============================================

        user = (await run_in_threadpool(lambda: authenticate_user(
            authorization
        )))
        ai_context("image", user, body)

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        child = (await run_in_threadpool(lambda: get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )))

        # =============================================
        # LOAD LESSON
        # WITH RETRY
        # =============================================

        unit_lesson = None

        for attempt in range(
            1,
            MAX_RETRIES + 1
        ):

            try:

                unit_lesson = (await run_in_threadpool(lambda: get_unit_lesson(
                    body.unit_lesson_id
                )))

                break

            except HTTPException:
                raise

            except Exception as e:

                print(
                    "HERO GET UNIT LESSON RETRY:",
                    {
                        "attempt":
                            attempt,
                        "max_attempts":
                            MAX_RETRIES,
                        "error":
                            repr(e)
                    }
                )

                if attempt >= MAX_RETRIES:
                    raise

                await asyncio.sleep(
                    RETRY_DELAY_SECONDS
                    * attempt
                )

        # =============================================
        # PARENT LESSON
        # WITH RETRY
        # =============================================

        parent_lesson = None

        for attempt in range(
            1,
            MAX_RETRIES + 1
        ):

            try:

                parent_lesson = (await run_in_threadpool(lambda: get_learning_lesson(
                    unit_lesson[
                        "learning_lesson_id"
                    ]
                )))

                break

            except HTTPException:
                raise

            except Exception as e:

                print(
                    "HERO GET PARENT LESSON RETRY:",
                    {
                        "attempt":
                            attempt,
                        "max_attempts":
                            MAX_RETRIES,
                        "error":
                            repr(e)
                    }
                )

                if attempt >= MAX_RETRIES:
                    raise

                await asyncio.sleep(
                    RETRY_DELAY_SECONDS
                    * attempt
                )

        # =============================================
        # GRADE SECURITY
        # =============================================

        child_grade = int(
            child.get("age")
            or 0
        )

        lesson_grade = int(
            parent_lesson.get("grade")
            or 0
        )

        if (
            child_grade
            and lesson_grade
            and child_grade != lesson_grade
        ):
            raise HTTPException(
                status_code=403,
                detail="Lesson does not match child grade"
            )

        # =============================================
        # STORAGE PATH
        # =============================================

        storage_path = (
            get_lesson_media_storage_path(
                unit_lesson_id=
                    unit_lesson["id"],
                media_type="hero"
            )
        )

        # =============================================
        # CACHE CHECK
        # WITH RETRY
        # =============================================

        signed_url = None
        last_cache_error = None

        for attempt in range(
            1,
            MAX_RETRIES + 1
        ):

            try:

                signed_url = (await run_in_threadpool(lambda: (
                    create_lesson_media_signed_url(
                        storage_path
                    )
                )))

                break

            except Exception as cache_error:

                last_cache_error = cache_error

                print(
                    "LESSON HERO CACHE CHECK RETRY:",
                    {
                        "unit_lesson_id":
                            unit_lesson["id"],
                        "attempt":
                            attempt,
                        "max_attempts":
                            MAX_RETRIES,
                        "error":
                            repr(cache_error)
                    }
                )

                if attempt < MAX_RETRIES:

                    await asyncio.sleep(
                        RETRY_DELAY_SECONDS
                        * attempt
                    )

        # =============================================
        # CACHE HIT
        # =============================================

        if signed_url:

            media_trace.waiting("hero HIT", lesson=unit_lesson["id"], lesson_age_s=media_trace.lesson_age_s(unit_lesson))
            print(
                "LESSON HERO CACHE HIT:",
                {
                    "unit_lesson_id":
                        unit_lesson["id"],
                    "storage_path":
                        storage_path
                }
            )

            return {
                "success": True,
                "source": "cache",
                "unit_lesson_id":
                    unit_lesson["id"],
                "hero_image": {
                    "type": "image",
                    "role": "hero",
                    "storage_path":
                        storage_path,
                    "url":
                        signed_url
                }
            }

        # =============================================
        # CACHE MISS
        # =============================================

        media_trace.waiting("hero MISS -> generating now", lesson=unit_lesson["id"], lesson_age_s=media_trace.lesson_age_s(unit_lesson))
        print(
            "LESSON HERO CACHE MISS:",
            {
                "unit_lesson_id":
                    unit_lesson["id"],
                "error":
                    repr(last_cache_error)
            }
        )

        # =============================================
        # GENERATE HERO
        # =============================================

        # One generation per lesson per process: concurrent requests wait on the
        # lock, then find the file the first one stored and return that instead.
        def _generate_hero_once():
            with generation_lock(f"hero:{unit_lesson['id']}"):
                try:
                    return {
                        "type": "image",
                        "role": "hero",
                        "storage_path": storage_path,
                        "url": create_lesson_media_signed_url(storage_path)
                    }
                except Exception:
                    return generate_and_store_lesson_hero_image(
                        unit_lesson["id"]
                    )

        hero_image = (await run_in_threadpool(_generate_hero_once))

        return {
            "success": True,
            "source": "generated",
            "unit_lesson_id":
                unit_lesson["id"],
            "hero_image":
                hero_image
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "UNIT LESSON HERO IMAGE ERROR:",
            repr(e)
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Lesson hero image generation failed"
        )

# =====================================================
# UNIT LESSON VISUALS
# =====================================================

@app.post(
    "/api/tutor/unit-lesson/visuals"
)
def get_unit_lesson_visuals(
        body: UnitLessonRequest,
        authorization: str = Header(None)
):
    try:

        # =============================================
        # AUTH
        # =============================================

        user = authenticate_user(
            authorization
        )

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        # מוודאים שהילד שייך למשתמש
        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )

        # =============================================
        # LOAD UNIT LESSON
        # =============================================

        unit_lesson = get_unit_lesson(
            body.unit_lesson_id
        )

        parent_lesson = get_learning_lesson(
            unit_lesson[
                "learning_lesson_id"
            ]
        )

        # =============================================
        # GRADE SECURITY
        # =============================================

        child_grade = int(
            child.get("age")
            or 0
        )

        lesson_grade = int(
            parent_lesson.get("grade")
            or 0
        )

        if (
                child_grade
                and lesson_grade
                and child_grade != lesson_grade
        ):
            raise HTTPException(
                status_code=403,
                detail="Lesson does not match child grade"
            )

        # =============================================
        # LOAD VISUAL PLAN
        # =============================================

        generated_lesson_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
            or {}
        )

        visual_plan = (
            generated_lesson_json.get(
                "visual_plan"
            )
            or {}
        )

        planned_visuals = (
            visual_plan.get(
                "visuals"
            )
            or []
        )

        content_version = int(
            unit_lesson.get(
                "content_version"
            )
            or 1
        )

        response_visuals = []

        # =============================================
        # BUILD RESPONSE
        # =============================================

        for visual in planned_visuals:

            if not isinstance(
                    visual,
                    dict
            ):
                continue

            visual_type = str(
                visual.get("type")
                or ""
            ).strip().lower()

            # כרגע הפרונט מקבל רק תמונות.
            # וידאו נחבר בשלב הבא.
            if visual_type != "image":
                continue

            part_number = int(
                visual.get(
                    "part_number"
                )
                or 1
            )

            visual_order = int(
                visual.get(
                    "order"
                )
                or 0
            )

            if not visual_order:
                continue
            image_order = int(visual.get("reuse_of") or visual_order)   # reused entries show the previous image
            storage_path = (
                f"unit_lessons/"
                f"{unit_lesson['id']}/"
                f"v{content_version}/"
                f"part_{part_number}/"
                f"visual_{image_order}.png"
            )
            # The image may still be generating.
            # If it is not ready yet, skip it for now.
            try:

                signed_url = (
                    create_lesson_media_signed_url(
                        storage_path
                    )
                )

            except Exception as image_error:

                print(
                    "LESSON VISUAL NOT READY:",
                    {
                        "unit_lesson_id":
                            unit_lesson["id"],

                        "part_number":
                            part_number,

                        "order":
                            visual_order,

                        "storage_path":
                            storage_path,

                        "error":
                            repr(
                                image_error
                            )
                    }
                )

                continue

            response_visuals.append(
                {
                    "part_number":
                        part_number,

                    "order":
                        visual_order,

                    "type":
                        "image",

                    "role":
                        visual.get(
                            "role"
                        ),

                    "trigger_text":
                        visual.get(
                            "trigger_text"
                        ),

                    "visual_goal":
                        visual.get(
                            "visual_goal"
                        ),

                    "source_text":
                        visual.get(
                            "source_text"
                        ),

                    "storage_path":
                        storage_path,

                    "url":
                        signed_url
                }
            )

        # =============================================
        # RESPONSE
        # =============================================

        media_trace.waiting("visuals", lesson=unit_lesson["id"], planned=len(planned_visuals), lesson_age_s=media_trace.lesson_age_s(unit_lesson))
        print(
            "LESSON VISUALS RESPONSE:",
            {
                "unit_lesson_id":
                    unit_lesson["id"],

                "content_version":
                    content_version,

                "planned_count":
                    len(planned_visuals),

                "ready_count":
                    len(response_visuals)
            }
        )

        return {

            "success":
                True,

            "unit_lesson_id":
                unit_lesson["id"],

            "content_version":
                content_version,

            "visuals":
                response_visuals,

            "visuals_ready":
                len(response_visuals),

            "visuals_planned":
                len([
                    item
                    for item in planned_visuals
                    if isinstance(item, dict)
                    and item.get("type") == "image"
                ])
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "UNIT LESSON VISUALS ERROR:",
            {
                "unit_lesson_id":
                    body.unit_lesson_id,

                "error":
                    repr(e)
            }
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Failed to load lesson visuals"
        )

@app.get(
    "/api/tutor/shared-transition/{transition_type}"
)
def get_shared_transition_endpoint(
        transition_type: str
):

    try:

        return get_shared_lesson_transition(
            transition_type
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        print(
            "SHARED TRANSITION ERROR:",
            {
                "transition_type":
                    transition_type,

                "error":
                    repr(e)
            }
        )

        raise HTTPException(
            status_code=500,
            detail="Shared transition unavailable"
        )

@app.post(
    "/api/tutor/unit-lesson/audio"
)
def generate_unit_lesson_audio(
        body: UnitLessonRequest,
        background_tasks: BackgroundTasks,
        authorization: str = Header(None)
):
    unit_lesson = None

    try:

        # =============================================
        # AUTH
        # =============================================

        user = authenticate_user(
            authorization
        )
        ai_context("tts", user, body)

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        # מוודאים שהילד שייך למשתמש
        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )

        # =============================================
        # LOAD UNIT LESSON
        # =============================================

        unit_lesson = get_unit_lesson(
            body.unit_lesson_id
        )

        parent_lesson = get_learning_lesson(
            unit_lesson[
                "learning_lesson_id"
            ]
        )

        # =============================================
        # GRADE SECURITY
        # =============================================

        child_grade = int(
            child.get("age")
            or 0
        )

        lesson_grade = int(
            parent_lesson.get("grade")
            or 0
        )

        if (
                child_grade
                and lesson_grade
                and child_grade != lesson_grade
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Lesson does not match "
                    "child grade"
                )
            )

        generation_status = (
            unit_lesson.get(
                "generation_status"
            )
            or "empty"
        )

        generated_lesson_json = (
            unit_lesson.get(
                "generated_lesson_json"
            )
        )

        audio_generation_status = (
            unit_lesson.get(
                "audio_generation_status"
            )
            or "pending"
        )

        cached_audio = (
            unit_lesson.get(
                "lesson_audio_json"
            )
        )

        # =============================================
        # LESSON CONTENT MUST EXIST
        # =============================================

        if (
                generation_status != "ready"
                or not isinstance(
                    generated_lesson_json,
                    dict
                )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Lesson content is not ready"
                )
            )

        structured_lesson = (
            generated_lesson_json.get(
                "structured_lesson"
            )
        )

        if not isinstance(
                structured_lesson,
                dict
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Structured lesson is missing"
                )
            )

        # =============================================
        # AUDIO ALREADY READY
        # =============================================

        cached_audio_has_parts = (
            isinstance(
                cached_audio,
                dict
            )
            and bool(
                cached_audio.get(
                    "parts"
                )
            )
        )

        cached_audio_has_legacy_segments = (
            isinstance(
                cached_audio,
                dict
            )
            and bool(
                cached_audio.get(
                    "segments"
                )
            )
        )

        if (
                audio_generation_status == "ready"
                and (
                    cached_audio_has_parts
                    or
                    cached_audio_has_legacy_segments
                )
        ):
            return {
                "success": True,

                "source":
                    "cache",

                "unit_lesson_id":
                    unit_lesson["id"],

                "audio_generation_status":
                    "ready",

                "lesson_audio":
                    add_signed_urls_to_lesson_audio(
                        cached_audio
                    )
            }

        # =============================================
        # AUDIO ALREADY GENERATING
        # =============================================

        if (
                audio_generation_status
                == "generating"
        ):
            # Progressive audio: the worker persists every stored segment while
            # it works, so the browser can play part 1 before part 2 exists.
            if cached_audio_has_parts:
                return {
                    "success": True,

                    "source":
                        "partial",

                    "unit_lesson_id":
                        unit_lesson["id"],

                    "audio_generation_status":
                        "generating",

                    "lesson_audio":
                        add_signed_urls_to_lesson_audio(
                            cached_audio
                        )
                }

            return {
                "success": False,

                "source":
                    "generating",

                "unit_lesson_id":
                    unit_lesson["id"],

                "audio_generation_status":
                    "generating",

                "lesson_audio":
                    None
            }

        # =============================================
        # QUEUE THE AUDIO, ANSWER "generating" NOW
        # =============================================
        # This route used to synthesise all ~17 segments inside the request
        # (100+ s in a worker thread) and every concurrent request for the same
        # lesson did it again: 30 children opening a lesson with pending audio
        # = 30 parallel TTS runs and the Gemini quota gone (load test 2026-09-14).
        # Now it enqueues one job (deduped per lesson, priority 10); the browser
        # already polls this route until the status turns "ready".
        dispatch_media_job(
            background_tasks,
            job_type="unit_lesson_audio",
            payload={"unit_lesson_id": int(unit_lesson["id"])},
            dedupe_key=f"unit_lesson:{unit_lesson['id']}",
            inline_fn=generate_unit_lesson_audio_background,
            inline_args=(unit_lesson["id"],)
        )

        return {
            "success": True,
            "source": "queued",
            "unit_lesson_id": unit_lesson["id"],
            "audio_generation_status": "generating",
            "lesson_audio": None
        }

    except HTTPException:
        raise

    except Exception as e:

        error_message = repr(e)

        print(
            "UNIT LESSON AUDIO ERROR:",
            error_message
        )

        if unit_lesson:

            try:

                sb.table(
                    "lesson_units_content"
                ).update({

                    "audio_generation_status":
                        "failed",

                    "audio_generation_error":
                        str(e)[:1500],

                    "updated_at":
                        datetime
                        .now(timezone.utc)
                        .isoformat()

                }).eq(
                    "id",
                    unit_lesson["id"]
                ).execute()

            except Exception as update_error:

                print(
                    "UNIT LESSON AUDIO "
                    "FAILURE UPDATE ERROR:",
                    repr(update_error)
                )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unit lesson audio "
                "generation failed"
            )
        )

# =====================================================
# LEARNING COACH EXECUTION
# =====================================================

async def run_learning_coach(
        user,
        child: dict,
        lesson: dict,
        unit_lesson: dict,
        message: str,
        tutor_session: dict,
        session_id: str,
        progress: dict,
        coach_index: int
):
    # =============================================
    # SESSION
    # =============================================

    coach_session = (
        get_or_create_learning_coach_session(
            kid_id=child["id"],
            lesson_id=lesson["id"],
            unit_lesson_id=unit_lesson["id"],
            coach_index=coach_index
        )
    )

    # =============================================
    # HISTORY
    # =============================================

    conversation_history = (await run_in_threadpool(lambda: (
        get_recent_lesson_history_for_llm(
            kid_id=child["id"],
            lesson_id=lesson["id"],
            unit_lesson_id=unit_lesson["id"],
            part_number=coach_index,
            limit=12
        )
    )))

    # =============================================
    # BUILD PROMPT
    # =============================================

    (
        system_prompt,
        runtime_data,
        current_round
    ) = build_learning_coach_prompt(
        child=child,
        parent_lesson=lesson,
        unit_lesson=unit_lesson,
        coach_session=coach_session,
        conversation_history=conversation_history,
        child_answer=message,
        coach_index=coach_index
    )

    # =============================================
    # CONSOLE DEBUG
    # =============================================

    print("\n")
    print("=" * 70)
    print("LEARNING COACH TRIGGERED")
    print("=" * 70)

    print(
        "ROUTING DATA:",
        json.dumps(
            {
                "kid_id":
                    child.get("id"),

                "child_name":
                    child.get("child_name"),

                "grade":
                    child.get("age"),

                "lesson_id":
                    lesson.get("id"),

                "unit_lesson_id":
                    unit_lesson.get("id"),

                "coach_session_id":
                    coach_session.get("id"),

                "coach_index":
                    coach_index,

                "current_round":
                    current_round,

                "maximum_rounds":
                    LEARNING_COACH_MAX_ROUNDS,

                "previous_score":
                    coach_session.get(
                        "final_understanding_score"
                    ),

                "child_answer":
                    message
            },
            ensure_ascii=False,
            indent=2
        )
    )

    print("-" * 70)
    print("LEARNING COACH RUNTIME DATA:")
    print(
        json.dumps(
            runtime_data,
            ensure_ascii=False,
            indent=2
        )
    )

    print("-" * 70)
    print("FINAL LEARNING COACH PROMPT:")
    print(system_prompt)
    print("=" * 70)

    # =============================================
    # OPENAI
    # =============================================

    completion = (await (
        aclient.beta.chat.completions.parse(
            model=DEFAULT_OPENAI_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": message
                }
            ],

            response_format=
                LearningCoachAIResponse
        )
    ))

    coach_data = (
        completion
        .choices[0]
        .message
        .parsed
    )

    if not coach_data:
        raise RuntimeError(
            "Learning Coach returned no response"
        )

    understanding_score = max(
        0,
        min(
            100,
            int(
                coach_data
                .understanding_score
            )
        )
    )

    # The backend is the authority for mastery.
    goal_achieved = (
            understanding_score
            >= OBJECTIVE_MASTERY_THRESHOLD
    )

    teacher_response = str(
        coach_data
        .teacher_response
        or ""
    ).strip()

    recommended_round_limit = min(
        LEARNING_COACH_MAX_ROUNDS,
        get_learning_coach_round_limit(understanding_score)
    )

    max_rounds_reached = (
        current_round
        >= recommended_round_limit
    )

    # Separate mastery from flow completion. A child does NOT need 90+ to move on.
    # Low/medium scores are retained as diagnostic evidence and the lesson continues
    # after a small adaptive number of focused turns.
    coach_finished = (
        goal_achieved
        or max_rounds_reached
    )

    # =============================================
    # UPDATE COACH SESSION
    # =============================================

    updated_coach_session = (await run_in_threadpool(lambda: (
        update_learning_coach_session(
            coach_session=coach_session,
            understanding_score=
                understanding_score,
            goal_achieved=
                goal_achieved,
            current_round=
                current_round
        )
    )))

    # =============================================
    # FINISH CURRENT LEARNING COACH
    # =============================================

    if coach_finished:

        now_iso = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        lesson_parts_count = max(
            1,
            min(
                6,
                int(
                    unit_lesson.get(
                        "lesson_parts_count"
                    )
                    or 2
                )
            )
        )

        has_next_part = (
                coach_index
                < lesson_parts_count
        )

        overall_mastery_score = (await run_in_threadpool(lambda: (
            calculate_lesson_coach_mastery(
                kid_id=child["id"],
                lesson_id=lesson["id"],
                unit_lesson_id=unit_lesson["id"],
                lesson_parts_count=
                lesson_parts_count
            )
        )))

        if has_next_part:
            next_part_number = (
                    coach_index + 1
            )

            next_stage = (
                LESSON_STAGE_FIRST_EXPLANATION
            )

        else:
            next_part_number = None

            next_stage = (
                LESSON_STAGE_FINAL_ASSESSMENT
            )

        progress_update = (await run_in_threadpool(lambda: (
            sb.table(
                "kid_lesson_progress"
            )
            .update({
                "current_stage":
                    next_stage,

                "flow_state": {
                    "phase": (
                        "explanation"
                        if has_next_part
                        else "final_assessment"
                    ),
                    "part_number": (
                        next_part_number
                        if has_next_part
                        else coach_index
                    ),
                    "segment_index": 0
                },

                "status":
                    "in_progress",

                "mastery_score":
                    overall_mastery_score,

                "last_activity_at":
                    now_iso,

                "updated_at":
                    now_iso
            })
            .eq(
                "id",
                progress["id"]
            )
            .execute()
        )))

        if progress_update.data:
            progress = (
                progress_update.data[0]
            )

        if not has_next_part:
            (await run_in_threadpool(lambda: complete_kid_unit_lesson_progress(
                kid_id=child["id"],
                unit_lesson_id=unit_lesson["id"],
                mastery_score=overall_mastery_score
            )))

    else:

        lesson_parts_count = max(
            1,
            min(
                6,
                int(
                    unit_lesson.get(
                        "lesson_parts_count"
                    )
                    or 2
                )
            )
        )

        has_next_part = False
        next_part_number = None

        next_stage = (
            progress.get(
                "current_stage"
            )
        )

    print("-" * 70)
    print(
        "LEARNING COACH RESPONSE:",
        json.dumps(
            {
                "understanding_score":
                    understanding_score,

                "lesson_goal_achieved":
                    goal_achieved,

                "teacher_response":
                    teacher_response,

                "coach_finished":
                    coach_finished,

                "status":
                    updated_coach_session.get(
                        "status"
                    )
            },
            ensure_ascii=False,
            indent=2
        )
    )
    print("=" * 70)
    print("\n")

    # =============================================
    # FRONTEND SEQUENCE
    #
    # teacher_response כבר כולל את תגובת המורה
    # ואת השאלה הבאה.
    #
    # לכן אסור לשלוח אותו גם כ-write וגם כ-ask.
    # =============================================

    if coach_finished:

        # =========================================
        # כשה-Coach הסתיים אסור לשאול עוד שאלה.
        #
        # speak = הודעת סיום בלבד.
        # wait_for_answer יהיה False.
        # =========================================

        sequence = [
            TutorAction(
                type="speak",
                text=teacher_response,
                style="normal",
                speed=45
            )
        ]

    else:

        sequence = [
            TutorAction(
                type="ask",
                text=teacher_response,
                style="question",
                speed=45
            )
        ]

    # =============================================
    # SAVE HISTORY
    # =============================================

    (await run_in_threadpool(lambda: save_lesson_history(
        kid_id=child["id"],
        lesson_id=lesson["id"],
        unit_lesson_id=unit_lesson["id"],
        session_id=session_id,
        objective_index=None,
        user_content=message,
        assistant_content=teacher_response,
        evaluation=None,
        sequence_json=[
            action.model_dump()
            for action in sequence
        ],
        part_number=coach_index
    )))

    # =============================================
    # TOKENS AND COST
    # =============================================

    input_tokens = 0
    output_tokens = 0
    total_tokens = 0

    if completion.usage:
        input_tokens = (
            completion.usage.prompt_tokens
            or 0
        )

        output_tokens = (
            completion.usage.completion_tokens
            or 0
        )

        total_tokens = (
            completion.usage.total_tokens
            or 0
        )

    openai_cost_usd = (
        calculate_openai_cost(
            model=DEFAULT_OPENAI_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
    )

    (await run_in_threadpool(lambda: update_tutor_session_after_chat(
        session=tutor_session,
        total_tokens=total_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=openai_cost_usd
    )))

    (await run_in_threadpool(lambda: increment_usage_summary(
        user_id=user.id,

        sessions=(
            1
            if tutor_session.get("_is_new")
            else 0
        ),

        ai_calls=1,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        openai_cost_usd=openai_cost_usd
    )))

    return {
        "speech":
            teacher_response,

        "sequence": [
            action.model_dump()
            for action in sequence
        ],

        "wait_for_answer":
            not coach_finished,
        "coach_finished":
            coach_finished,

        "lesson_completed":
            False,
        "session_id":
            session_id,

        "lesson_id":
            lesson["id"],

        "unit_lesson_id":
            unit_lesson["id"],

        "lesson_mode":
            "learning_coach",

        "current_stage":
            progress.get(
                "current_stage"
            ),

        "coach_index":
            coach_index,

        "lesson_parts_count":
            lesson_parts_count,

        "next_part_number":
            next_part_number,

        "has_next_part":
            has_next_part,

        "review_mode":
            False,

        "learning_coach": {
            "session_id":
                updated_coach_session.get(
                    "id"
                ),

            "coach_index":
                coach_index,

            "current_round":
                current_round,

            "maximum_rounds":
                recommended_round_limit,

            "understanding_score":
                understanding_score,

            "lesson_goal_achieved":
                goal_achieved,

            "status":
                updated_coach_session.get(
                    "status"
                ),

            "finished":
                coach_finished
        }
    }
# =====================================================
# STRUCTURED AI LESSON
# =====================================================

@app.post(
    "/api/tutor/lesson"
)
async def structured_lesson(
        body: StructuredLessonRequest,
        authorization: str = Header(None)
):
    try:

        # =============================================
        # AUTH
        # =============================================

        user = (await run_in_threadpool(lambda: authenticate_user(
            authorization
        )))
        ai_context("lesson_chat", user, body)

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        # =============================================
        # CHILD
        # =============================================

        child = (await run_in_threadpool(lambda: get_child_by_id(

            user_id=user.id,

            kid_id=body.kid_id

        )))

        # =============================================
        # LESSON
        # =============================================

        lesson = (await run_in_threadpool(lambda: get_learning_lesson(
            body.lesson_id
        )))

        # =============================================
        # SECURITY
        #
        # מוודאים שהשיעור מתאים לכיתה
        # של הילד
        # =============================================

        child_grade = int(

            child.get(
                "age"
            )

            or 0

        )

        lesson_grade = int(

            lesson.get(
                "grade"
            )

            or 0

        )

        if (

                child_grade
                and lesson_grade
                and child_grade != lesson_grade

        ):
            raise HTTPException(

                status_code=403,

                detail=(
                    "Lesson does not match "
                    "child grade"
                )

            )

        # =============================================
        # SESSION
        # =============================================

        tutor_session = (await run_in_threadpool(lambda: (

            get_or_create_tutor_session(

                user_id=user.id,

                kid_id=child["id"]

            )

        )))

        session_id = (
            tutor_session["id"]
        )

        # =============================================
        # האם זו פתיחת שיעור
        # =============================================

        message = (

                body.message
                or ""

        ).strip()

        # =============================================
        # SPECIAL LESSON EVENTS
        #
        # __NO_RESPONSE__ נשלח מה-Frontend
        # כאשר הילד לא ענה במשך זמן מסוים.
        #
        # זה אינו נחשב תשובת תלמיד ולכן:
        # - לא מבצעים Evaluation
        # - לא מעדכנים Progress
        # - לא שומרים אותו כתשובת ילד
        # =============================================

        is_no_response = (

                message
                == "__NO_RESPONSE__"

        )

        is_lesson_start = (

            not bool(
                message
            )

        )

        # =============================================
        # PROGRESS
        # =============================================

        progress = (await run_in_threadpool(lambda: (

            get_or_create_lesson_progress(

                kid_id=child["id"],

                lesson=lesson,

                session_id=session_id,

                is_lesson_start=
                is_lesson_start,

                unit_lesson_id=
                body.unit_lesson_id

            )

        )))
        # =============================================
        # UNIT LESSON SWITCH
        #
        # kid_lesson_progress הוא ברמת הנושא הראשי,
        # ולכן חייבים לזהות מעבר לשיעור פנימי חדש.
        # =============================================

        requested_unit_lesson_id = (
            int(body.unit_lesson_id)
            if body.unit_lesson_id
            else None
        )

        stored_unit_lesson_id = (
            int(
                progress.get(
                    "current_unit_lesson_id"
                )
                or 0
            )
            or None
        )

        is_new_unit_lesson = (
            requested_unit_lesson_id is not None
            and requested_unit_lesson_id
            != stored_unit_lesson_id
        )

        if is_lesson_start and requested_unit_lesson_id is not None:
            (await run_in_threadpool(lambda: start_kid_unit_lesson_progress(
                kid_id=child["id"],
                learning_lesson_id=lesson["id"],
                unit_lesson_id=requested_unit_lesson_id
            )))

        if is_new_unit_lesson:

            now_iso = (
                datetime
                .now(timezone.utc)
                .isoformat()
            )

            progress_update = (await run_in_threadpool(lambda: (
                sb.table(
                    "kid_lesson_progress"
                )
                .update({
                    # תת־השיעור החדש
                    "current_unit_lesson_id":
                        requested_unit_lesson_id,

                    # מתחילים זרימה חדשה
                    "current_stage":
                        LESSON_STAGE_INTRO,

                    "current_flow_step":
                        0,

                    "flow_state":
                        {},

                    "status":
                        "in_progress",

                    # מאפסים את תוצאת תת־השיעור הקודם
                    "progress_percent":
                        0,

                    "mastery_score":
                        0,

                    "current_objective_index":
                        1,

                    "total_interactions":
                        0,

                    "hints_used":
                        0,

                    "consecutive_successes":
                        0,

                    "consecutive_failures":
                        0,

                    "last_evaluation":
                        None,

                    "last_error_type":
                        None,

                    "completed_at":
                        None,

                    "last_activity_at":
                        now_iso,

                    "updated_at":
                        now_iso
                })
                .eq(
                    "id",
                    progress["id"]
                )
                .execute()
            )))

            if not progress_update.data:
                raise RuntimeError(
                    "Failed to switch unit lesson"
                )

            progress = progress_update.data[0]

            print(
                "UNIT LESSON PROGRESS SWITCHED:",
                {
                    "kid_id":
                        child["id"],

                    "lesson_id":
                        lesson["id"],

                    "previous_unit_lesson_id":
                        stored_unit_lesson_id,

                    "current_unit_lesson_id":
                        requested_unit_lesson_id,

                    "current_stage":
                        progress.get(
                            "current_stage"
                        ),

                    "status":
                        progress.get(
                            "status"
                        )
                }
            )
        # =============================================
        # LESSON MODE
        #
        # אם השיעור כבר הושלם,
        # כניסה חוזרת אליו היא Review Mode.
        #
        # במצב Review:
        # - לא מאפסים התקדמות
        # - לא משנים ציוני יעדים
        # - לא נותנים שוב XP / Stars
        # =============================================

        review_mode = (
            progress.get(
                "status"
            )
            == "completed"

            and

            not is_new_unit_lesson
        )

        # =============================================
        # TURN TYPE
        # =============================================

        if review_mode:

            if is_lesson_start:

                turn_type = (
                    "review_start"
                )

            elif is_no_response:

                turn_type = (
                    "review_no_response"
                )

            else:

                turn_type = (
                    "review_response"
                )


        else:

            if is_lesson_start:

                turn_type = (
                    "start"
                )

            elif is_no_response:

                turn_type = (
                    "no_response"
                )

            else:

                turn_type = (
                    "student_response"
                )
        # =============================================
        # UNIVERSAL LESSON STAGE ROUTER
        # =============================================

        is_real_student_answer = (
                not is_lesson_start
                and not is_no_response
                and not review_mode
        )

        current_stage = (
                progress.get(
                    "current_stage"
                )
                or LESSON_STAGE_INTRO
        )

        if is_real_student_answer:
            if (
                    current_stage
                    == LESSON_STAGE_COMPLETED
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Lesson is already completed"
                )

            if not body.unit_lesson_id:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "unit_lesson_id is required "
                        "for Universal Lesson"
                    )
                )

            unit_lesson = (await run_in_threadpool(lambda: get_unit_lesson(
                body.unit_lesson_id
            )))

            if (
                    int(
                        unit_lesson.get(
                            "learning_lesson_id"
                        )
                        or 0
                    )
                    !=
                    int(
                        lesson.get("id")
                        or 0
                    )
            ):
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Unit lesson does not belong "
                        "to the selected lesson"
                    )
                )

            # =========================================
            # DYNAMIC LEARNING COACH ROUTER
            # =========================================

            flow_state = (
                    progress.get(
                        "flow_state"
                    )
                    or {}
            )

            if not isinstance(
                    flow_state,
                    dict
            ):
                flow_state = {}

            # Resolve the Part that owns the current fixed question.
            if current_stage in (
                    LESSON_STAGE_INTRO,
                    LESSON_STAGE_FIRST_EXPLANATION,
                    LESSON_STAGE_FIRST_QUESTION
            ):
                coach_part_number = int(
                    flow_state.get(
                        "part_number"
                    )
                    or 1
                )

                progress = (await run_in_threadpool(lambda: (
                    update_learning_coach_flow_state(
                        progress=progress,
                        part_number=
                        coach_part_number
                    )
                )))

                return (await run_learning_coach(
                    user=user,
                    child=child,
                    lesson=lesson,
                    unit_lesson=unit_lesson,
                    message=message,
                    tutor_session=tutor_session,
                    session_id=session_id,
                    progress=progress,
                    coach_index=
                    coach_part_number
                ))

            # Continue the currently active Coach.
            if (
                    current_stage
                    == LESSON_STAGE_LEARNING_COACH
            ):
                coach_part_number = int(
                    flow_state.get(
                        "part_number"
                    )
                    or 1
                )

                return (await run_learning_coach(
                    user=user,
                    child=child,
                    lesson=lesson,
                    unit_lesson=unit_lesson,
                    message=message,
                    tutor_session=tutor_session,
                    session_id=session_id,
                    progress=progress,
                    coach_index=
                    coach_part_number
                ))

            # Compatibility with old progress rows.
            if (
                    current_stage
                    == LESSON_STAGE_LEARNING_COACH_1
            ):
                progress = (await run_in_threadpool(lambda: (
                    update_learning_coach_flow_state(
                        progress=progress,
                        part_number=1
                    )
                )))

                return (await run_learning_coach(
                    user=user,
                    child=child,
                    lesson=lesson,
                    unit_lesson=unit_lesson,
                    message=message,
                    tutor_session=tutor_session,
                    session_id=session_id,
                    progress=progress,
                    coach_index=1
                ))

            if (
                    current_stage
                    == LESSON_STAGE_LEARNING_COACH_2
            ):
                progress = (await run_in_threadpool(lambda: (
                    update_learning_coach_flow_state(
                        progress=progress,
                        part_number=2
                    )
                )))

                return (await run_learning_coach(
                    user=user,
                    child=child,
                    lesson=lesson,
                    unit_lesson=unit_lesson,
                    message=message,
                    tutor_session=tutor_session,
                    session_id=session_id,
                    progress=progress,
                    coach_index=2
                ))
            # בשלבי clarification ו-final_assessment
            # עדיין אין מנוע ייעודי בקוד הנוכחי.
            raise HTTPException(
                status_code=409,
                detail=(
                    "Student answer is not expected "
                    f"during stage: {current_stage}"
                )
            )
        # =============================================
        # PROMPT
        # =============================================

        show_answering_hint = False

        if (
                is_lesson_start
                and
                not review_mode
                and
                child_grade in (1, 2)
        ):
            show_answering_hint = (await run_in_threadpool(lambda: (
                should_show_answering_hint(
                    kid_id=child["id"],
                    max_lessons=3
                )
            )))

        system_prompt = (

            build_structured_lesson_prompt(

                child=child,

                lesson=lesson,

                progress=progress,

                turn_type=turn_type,

                review_mode=review_mode,

                show_answering_hint=
                show_answering_hint

            )

        )

        # =============================================
        # HISTORY
        # =============================================

        recent_messages = (await run_in_threadpool(lambda: (

            get_recent_lesson_history_for_llm(

                kid_id=
                child["id"],

                lesson_id=
                lesson["id"],

                unit_lesson_id=
                body.unit_lesson_id,

                limit=8

            )

        )))

        # =============================================
        # CURRENT TURN
        # =============================================

        if is_lesson_start:

            if review_mode:

                current_message = (

                    "התחל חזרה על שיעור שכבר הושלם. "
                    "אל תלמד את השיעור מחדש מההתחלה. "
                    "בצע חזרה קצרה ובדיקת שימור ידע "
                    "על יעדי הלמידה, תוך העדפה למשימות "
                    "ברמות בינוניות עד גבוהות. "
                    "זהו תור פתיחת Review ולכן "
                    "אין להעריך עדיין תשובת תלמיד."

                )

            else:

                current_message = (

                    "התחל את השיעור המובנה. "
                    "זהו תור פתיחת שיעור ולכן "
                    "אין להעריך עדיין תשובת תלמיד."

                )


        elif is_no_response:

            current_message = (

                "התלמיד עדיין לא ענה לשאלה האחרונה. "
                "אל תתייחס לכך כתשובת תלמיד ואל תבצע הערכה. "
                "דובב את הילד בצורה קצרה, חמה וטבעית. "
                "אפשר לעודד אותו לחשוב, להציע רמז קטן "
                "או לנסח את השאלה בצורה פשוטה יותר. "
                "אל תיתן מיד את התשובה. "
                "המשך להמתין לתשובת הילד."

            )


        else:

            current_message = (
                message
            )

        # =============================================
        # ADD CURRENT TURN TO LLM MESSAGES
        #
        # מתבצע תמיד:
        # - פתיחת שיעור רגיל
        # - פתיחת Review
        # - תשובת תלמיד
        # =============================================

        recent_messages.append({

            "role":
                "user",

            "content":
                current_message

        })

        # =============================================
        # OPENAI
        # =============================================

        completion = (await (

            aclient.beta.chat.completions.parse(

                model=
                DEFAULT_OPENAI_MODEL,

                messages=[

                    {

                        "role":
                            "system",

                        "content":
                            system_prompt

                    },

                    *recent_messages

                ],

                response_format=
                StructuredLessonResponse

            )

        ))

        lesson_data = (

            completion
            .choices[0]
            .message
            .parsed

        )

        if not lesson_data:
            raise HTTPException(

                status_code=500,

                detail=(
                    "Structured lesson "
                    "returned no response"
                )

            )

        # =============================================
        # VALIDATE LESSON START SEQUENCE
        #
        # בפתיחת שיעור רגילה:
        # - חייב להיות לפחות write אחד
        # - חייב להיות ask בסוף
        #
        # אם GPT החזיר פתיח חלקי,
        # מבצעים Retry אחד עם הוראה מפורשת.
        # =============================================

        if is_lesson_start and not review_mode:

            sequence = (
                    lesson_data.sequence
                    or []
            )

            has_write = any(
                action.type == "write"
                for action in sequence
            )

            has_ask = any(
                action.type == "ask"
                and bool(
                    (
                            action.text
                            or ""
                    ).strip()
                )
                for action in sequence
            )

            final_action_is_ask = (
                    bool(sequence)
                    and sequence[-1].type == "ask"
                    and bool(
                (
                        sequence[-1].text
                        or ""
                ).strip()
            )
            )

            if (
                    not has_write
                    or
                    not has_ask
                    or
                    not final_action_is_ask
            ):

                retry_message = (

                        current_message

                        +

                        "\n\n"
                        "IMPORTANT RETRY: "
                        "The previous lesson-start response was incomplete. "
                        "Return a COMPLETE lesson-start sequence. "
                        "Do not return only speak actions. "
                        "The sequence must include actual teaching, "
                        "at least one write action, "
                        "and must end with one real ask action "
                        "that requires the child's response. "
                        "Begin teaching the current objective now, "
                        "not only introducing the lesson."
                )

                retry_messages = [

                    {
                        "role":
                            "system",

                        "content":
                            system_prompt

                    },

                    *recent_messages[:-1],

                    {
                        "role":
                            "user",

                        "content":
                            retry_message

                    }

                ]

                retry_completion = (await (

                    aclient.beta.chat.completions.parse(

                        model=
                        DEFAULT_OPENAI_MODEL,

                        messages=
                        retry_messages,

                        response_format=
                        StructuredLessonResponse

                    )

                ))

                retry_lesson_data = (

                    retry_completion
                    .choices[0]
                    .message
                    .parsed

                )

                if retry_lesson_data:
                    lesson_data = (
                        retry_lesson_data
                    )

                    completion = (
                        retry_completion
                    )

        # =============================================
        # NORMALIZE WAIT FOR ANSWER
        #
        # מחכים לילד אך ורק כאשר הפעולה האחרונה
        # ב-sequence היא ASK אמיתית עם טקסט.
        #
        # אם המודל כתב wait_for_answer=true
        # אבל לא שאל שאלה בפועל,
        # ה-Backend מתקן זאת אוטומטית.
        # =============================================

        sequence = (

                lesson_data.sequence
                or []

        )

        # =============================================
        # GUARANTEE LESSON OPENING GREETING
        # =============================================

        if is_lesson_start and not review_mode:
            child_name = (
                    child.get("child_name")
                    or ""
            ).strip()

            subject = (
                    lesson.get("subject")
                    or ""
            ).strip()

            greeting_text = (
                f"שלום {child_name}! "
                f"כיף שבחרת ללמוד איתי היום {subject}."
            )

            # מוסיפים פתיח קולי קבוע בתחילת השיעור
            sequence.insert(
                0,
                TutorAction(
                    type="speak",
                    text=greeting_text
                )
            )


            lesson_data.sequence = sequence

        last_action = (

            sequence[-1]

            if sequence

            else None

        )

        has_real_final_ask = (

                last_action is not None

                and

                last_action.type == "ask"

                and

                bool(

                    (
                            last_action.text
                            or ""
                    ).strip()

                )

        )

        lesson_data.wait_for_answer = (

            has_real_final_ask

        )

        # =============================================
        # EVALUATION
        #
        # רק אחרי תשובה אמיתית של הילד
        # =============================================

        evaluation_dict = None

        evaluated_objective_index = (
            progress.get(
                "current_objective_index"
            )
        )

        if (

                not is_lesson_start

                and

                not is_no_response

                and

                lesson_data.evaluation

        ):

            evaluation_dict = (

                lesson_data
                .evaluation
                .model_dump()

            )

            evaluated_objective_index = (

                    evaluation_dict.get(
                        "objective_index"
                    )

                    or progress.get(
                "current_objective_index"
            )

            )

            # =========================================
            # NORMAL LEARNING MODE
            #
            # רק במהלך לימוד רגיל
            # ההערכה משנה את ההתקדמות הרשמית.
            # =========================================

            if not review_mode:
                progress = (await run_in_threadpool(lambda: (

                    apply_lesson_evaluation(

                        progress=progress,

                        lesson=lesson,

                        evaluation=
                        evaluation_dict,

                        session_id=
                        session_id

                    )

                )))

        # =============================================
        # CLEAN ASSISTANT HISTORY
        # =============================================

        assistant_history_parts = []

        if lesson_data.speech:
            assistant_history_parts.append(

                lesson_data
                .speech
                .strip()

            )

        for action in (

                lesson_data.sequence
                or []

        ):

            if (

                    action.type
                    in (
                    "write",
                    "ask"
            )

                    and action.text

                    and action.text.strip()

            ):

                clean_text = (

                    action.text
                    .strip()

                )

                if (

                        clean_text

                        not in
                        assistant_history_parts

                ):
                    assistant_history_parts.append(

                        clean_text

                    )

        assistant_history_text = (

            "\n".join(

                assistant_history_parts

            )

        )

        # =============================================
        # SAVE LESSON HISTORY
        # =============================================

        (await run_in_threadpool(lambda: save_lesson_history(

            kid_id=
            child["id"],

            lesson_id=
            lesson["id"],

            unit_lesson_id=
            body.unit_lesson_id,

            session_id=
            session_id,

            objective_index=
            evaluated_objective_index,

            user_content=(

                None

                if (
                        is_lesson_start
                        or
                        is_no_response
                )

                else message

            ),

            assistant_content=
            assistant_history_text,

            evaluation=
            evaluation_dict,

            sequence_json=[

                action.model_dump()

                for action
                in lesson_data.sequence

            ]

        )))

        # =============================================
        # TOKEN USAGE
        # =============================================

        total_tokens = 0

        input_tokens = 0

        output_tokens = 0

        if completion.usage:
            total_tokens = (

                    completion
                    .usage
                    .total_tokens

                    or 0

            )

            input_tokens = (

                    completion
                    .usage
                    .prompt_tokens

                    or 0

            )

            output_tokens = (

                    completion
                    .usage
                    .completion_tokens

                    or 0

            )

        openai_cost_usd = calculate_openai_cost(
            model=DEFAULT_OPENAI_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        # =============================================
        # SESSION USAGE
        # =============================================

        (await run_in_threadpool(lambda: update_tutor_session_after_chat(

            session=
            tutor_session,

            total_tokens=
            total_tokens,

            input_tokens=
            input_tokens,

            output_tokens=
            output_tokens,

            cost_usd=
            openai_cost_usd

        )))

        (await run_in_threadpool(lambda: increment_usage_summary(

            user_id=
            user.id,

            sessions=(

                1

                if tutor_session.get(
                    "_is_new"
                )

                else 0

            ),

            ai_calls=
            1,

            input_tokens=
            input_tokens,

            output_tokens=
            output_tokens,

            total_tokens=
            total_tokens,

            openai_cost_usd=
            openai_cost_usd

        )))

        # =============================================
        # RESPONSE TO FRONTEND
        # =============================================

        response_data = (

            lesson_data
            .model_dump()

        )

        response_data[
            "session_id"
        ] = session_id

        response_data[
            "lesson_id"
        ] = lesson["id"]

        response_data[
            "progress"
        ] = {

            "status":
                progress.get(
                    "status"
                ),

            "current_stage":
                progress.get(
                    "current_stage"
                ),

            "progress_percent":
                progress.get(
                    "progress_percent"
                ),

            "mastery_score":
                progress.get(
                    "mastery_score"
                ),

            "current_objective_index":
                progress.get(
                    "current_objective_index"
                ),

            "objectives_progress":
                progress.get(
                    "objectives_progress"
                )

        }

        response_data[
            "review_mode"
        ] = review_mode

        response_data[
            "lesson_mode"
        ] = (

            "review"

            if review_mode

            else "learning"

        )

        return response_data


    except HTTPException:

        raise


    except Exception as e:

        print(

            "STRUCTURED LESSON ERROR:",

            repr(e)

        )

        raise HTTPException(

            status_code=500,

            detail=(
                "Structured lesson failed"
            )

        )

# =====================================================
# RESET UNIT LESSON PROGRESS
# =====================================================

@app.post(
    "/api/tutor/reset-unit-lesson"
)
def reset_unit_lesson(
        body: ResetUnitLessonRequest,
        authorization: str = Header(None)
):
    try:

        # =============================================
        # AUTH
        # =============================================

        user = authenticate_user(
            authorization
        )

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        # =============================================
        # CHILD OWNERSHIP
        # =============================================

        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )

        # =============================================
        # LESSON VALIDATION
        # =============================================

        lesson = get_learning_lesson(
            body.lesson_id
        )

        unit_lesson = get_unit_lesson(
            body.unit_lesson_id
        )

        if (
                int(
                    unit_lesson.get(
                        "learning_lesson_id"
                    )
                    or 0
                )
                !=
                int(
                    lesson.get(
                        "id"
                    )
                    or 0
                )
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Unit lesson does not belong "
                    "to the selected lesson"
                )
            )

        # =============================================
        # GRADE SECURITY
        # =============================================

        child_grade = int(
            child.get("age")
            or 0
        )

        lesson_grade = int(
            lesson.get("grade")
            or 0
        )

        if (
                child_grade
                and lesson_grade
                and child_grade != lesson_grade
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Lesson does not match "
                    "child grade"
                )
            )

        now_iso = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        # =============================================
        # DELETE LEARNING COACH SESSIONS
        #
        # רק עבור הילד ותת־השיעור הנוכחי
        # =============================================

        coach_delete = (
            sb.table(
                "learning_coach_sessions"
            )
            .delete()
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "lesson_id",
                lesson["id"]
            )
            .eq(
                "unit_lesson_id",
                unit_lesson["id"]
            )
            .execute()
        )

        # =============================================
        # DELETE UNIT LESSON HISTORY
        # =============================================

        history_delete = (
            sb.table(
                "kid_lesson_history"
            )
            .delete()
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "lesson_id",
                lesson["id"]
            )
            .eq(
                "unit_lesson_id",
                unit_lesson["id"]
            )
            .execute()
        )

        # =============================================
        # RESET UNIT LESSON PROGRESS ROW
        #
        # kid_unit_lesson_progress היא טבלת ההתקדמות
        # החדשה ברמת תת־השיעור. כפתור "להתחיל מחדש"
        # חייב לאפס גם אותה, אחרת השיעור נשאר completed
        # למרות שהטבלה הראשית הישנה כבר אופסה.
        # =============================================

        unit_progress_reset = (
            sb.table(
                "kid_unit_lesson_progress"
            )
            .update({
                "status":
                    "in_progress",

                "progress_percent":
                    0,

                "current_stage":
                    LESSON_STAGE_INTRO,

                "last_part_number":
                    1,

                "mastery_score":
                    0,

                "best_mastery_score":
                    0,

                "attempts_count":
                    0,

                "started_at":
                    now_iso,

                "last_activity_at":
                    now_iso,

                "completed_at":
                    None,

                "updated_at":
                    now_iso
            })
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "learning_lesson_id",
                lesson["id"]
            )
            .eq(
                "unit_lesson_id",
                unit_lesson["id"]
            )
            .execute()
        )

        # =============================================
        # RESET MAIN PROGRESS ROW
        #
        # kid_lesson_progress היא רשומה אחת לנושא,
        # לכן לא מוחקים אותה אלא מאפסים אותה
        # ומכוונים לתת־השיעור שנבחר.
        # =============================================

        progress_res = (
            sb.table(
                "kid_lesson_progress"
            )
            .select("*")
            .eq(
                "kid_id",
                child["id"]
            )
            .eq(
                "lesson_id",
                lesson["id"]
            )
            .limit(1)
            .execute()
        )

        progress = None

        if progress_res.data:

            progress_id = (
                progress_res.data[0]["id"]
            )
            objectives = (
                    lesson.get(
                        "learning_objectives"
                    )
                    or []
            )

            reset_objectives_progress = []

            for index, _ in enumerate(
                    objectives,
                    start=1
            ):
                reset_objectives_progress.append({
                    "objective_index":
                        index,

                    "score":
                        0,

                    "highest_difficulty_reached":
                        0,

                    "evidence_count":
                        0,

                    "evidence_by_level": {
                        "1": 0,
                        "2": 0,
                        "3": 0,
                        "4": 0,
                        "5": 0
                    }
                })

            progress_update = (
                sb.table(
                    "kid_lesson_progress"
                )
                .update({
                    "current_unit_lesson_id":
                        unit_lesson["id"],

                    "current_stage":
                        LESSON_STAGE_INTRO,

                    "current_flow_step":
                        0,

                    "flow_state":
                        {},

                    "status":
                        "in_progress",

                    "progress_percent":
                        0,

                    "mastery_score":
                        0,

                    "current_objective_index":
                        1,

                    "objectives_progress":
                        reset_objectives_progress,

                    "total_interactions":
                        0,

                    "attempts_count":
                        0,

                    "hints_used":
                        0,

                    "consecutive_successes":
                        0,

                    "consecutive_failures":
                        0,

                    "last_evaluation":
                        None,

                    "last_error_type":
                        None,

                    "completed_at":
                        None,

                    "xp_earned":
                        0,

                    "stars_earned":
                        0,

                    "last_session_id":
                        None,

                    "started_at":
                        now_iso,

                    "last_activity_at":
                        now_iso,

                    "updated_at":
                        now_iso
                })
                .eq(
                    "id",
                    progress_id
                )
                .execute()
            )

            if progress_update.data:
                progress = (
                    progress_update.data[0]
                )

        # =============================================
        # DEBUG
        # =============================================

        print(
            "UNIT LESSON RESET COMPLETED:",
            json.dumps(
                {
                    "user_id":
                        user.id,

                    "kid_id":
                        child["id"],

                    "lesson_id":
                        lesson["id"],

                    "unit_lesson_id":
                        unit_lesson["id"],

                    "coach_rows_deleted":
                        len(
                            coach_delete.data
                            or []
                        ),

                    "history_rows_deleted":
                        len(
                            history_delete.data
                            or []
                        ),

                    "progress_reset":
                        progress is not None,

                    "unit_progress_reset":
                        bool(
                            unit_progress_reset.data
                            or []
                        ),

                    "lesson_content_deleted":
                        False,

                    "lesson_audio_deleted":
                        False
                },
                ensure_ascii=False,
                indent=2
            )
        )

        return {
            "success": True,

            "kid_id":
                child["id"],

            "lesson_id":
                lesson["id"],

            "unit_lesson_id":
                unit_lesson["id"],

            "reset": {
                "learning_coach_sessions":
                    True,

                "lesson_history":
                    True,

                "lesson_progress":
                    True,

                "unit_lesson_progress":
                    True
            },

            "preserved": {
                "lesson_content":
                    True,

                "lesson_audio":
                    True
            },

            "progress": {
                "current_stage":
                    (
                        progress.get(
                            "current_stage"
                        )
                        if progress
                        else LESSON_STAGE_INTRO
                    ),

                "progress_percent":
                    0,

                "mastery_score":
                    0,

                "status":
                    "in_progress"
            }
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "RESET UNIT LESSON ERROR:",
            {
                "kid_id":
                    body.kid_id,

                "lesson_id":
                    body.lesson_id,

                "unit_lesson_id":
                    body.unit_lesson_id,

                "error_type":
                    type(e).__name__,

                "error":
                    repr(e)
            }
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Failed to reset unit lesson"
        )
# =====================================================
# HOMEWORK IMAGE / PDF ANALYSIS
# =====================================================

@app.post(
    "/api/tutor/homework-analyze"
)
async def homework_analyze(
        body: HomeworkAnalyzeRequest,
        authorization: str = Header(None)
):
    upload_row_id = None

    try:

        # =============================================
        # AUTH
        # =============================================

        user = (await run_in_threadpool(lambda: authenticate_user(
            authorization
        )))
        ai_context("homework", user, body)

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        if not body.storage_path:
            raise HTTPException(
                status_code=400,
                detail="storage_path is required"
            )

        # =============================================
        # מוודאים שהילד שייך למשתמש
        # =============================================

        child = (await run_in_threadpool(lambda: get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )))

        # =============================================
        # SECURITY
        #
        # הנתיב חייב להתחיל ב-user_id
        #
        # user_id/kid_id/file.jpg
        # =============================================

        expected_prefix = (
            f"{user.id}/"
        )

        if not body.storage_path.startswith(
                expected_prefix
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Invalid storage path"
                )
            )

        # =============================================
        # SESSION
        # =============================================

        if body.session_id:

            session_id = (
                body.session_id
            )

        else:

            tutor_session = (await run_in_threadpool(lambda: (
                get_or_create_tutor_session(
                    user_id=user.id,
                    kid_id=child["id"]
                )
            )))

            session_id = (
                tutor_session["id"]
            )

        # =============================================
        # CREATE homework_uploads ROW
        # =============================================

        upload_res = (await run_in_threadpool(lambda: (

            sb.table(
                "homework_uploads"
            )

            .insert({

                "user_id":
                    user.id,

                "kid_id":
                    child["id"],

                "session_id":
                    session_id,

                "file_name":
                    body.file_name,

                "file_type":
                    body.file_type,

                "storage_path":
                    body.storage_path,

                "file_size_bytes":
                    body.file_size_bytes,

                "original_width":
                    body.original_width,

                "original_height":
                    body.original_height,

                "processed_width":
                    body.processed_width,

                "processed_height":
                    body.processed_height,

                "compression_quality":
                    body.compression_quality,

                "vision_status":
                    "processing",

                "vision_model":
                    DEFAULT_OPENAI_MODEL,

                "vision_call_count":
                    0

            })

            .execute()

        )))

        if not upload_res.data:
            raise RuntimeError(
                "Failed to create "
                "homework_uploads row"
            )

        upload_row_id = (
            upload_res.data[0]["id"]
        )

        # =============================================
        # DOWNLOAD FILE FROM PRIVATE STORAGE
        # =============================================

        file_bytes = (await run_in_threadpool(lambda: (

            sb.storage

            .from_(
                "homework-uploads"
            )

            .download(
                body.storage_path
            )

        )))

        if not file_bytes:
            raise RuntimeError(
                "Failed to download "
                "homework file"
            )

        # =============================================
        # MIME TYPE
        # =============================================

        mime_type = (
                body.file_type
                or "image/jpeg"
        )

        allowed_mime_types = {

            "image/jpeg",

            "image/png",

            "image/webp",

            "application/pdf"

        }

        if mime_type not in (
                allowed_mime_types
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported file type"
                )
            )

        # =============================================
        # SEND TO OPENAI GPT-4o MINI VISION
        # =============================================

        base64_file = base64.b64encode(
            file_bytes
        ).decode("utf-8")

        if mime_type == "application/pdf":
            raise HTTPException(
                status_code=400,
                detail=(
                    "PDF analysis is not supported "
                    "yet in GPT-4o-mini image mode"
                )
            )

        data_url = (
            f"data:{mime_type};base64,"
            f"{base64_file}"
        )

        response = (await aclient.chat.completions.create(

            model=
            DEFAULT_OPENAI_MODEL,

            messages=[

                {
                    "role": "system",
                    "content":
                        HOMEWORK_VISION_PROMPT
                },

                {
                    "role": "user",
                    "content": [

                        {
                            "type": "text",
                            "text":
                                "Analyze this homework image "
                                "and return only the requested JSON."
                        },

                        {
                            "type": "image_url",
                            "image_url": {
                                "url":
                                    data_url,

                                "detail":
                                    "high"
                            }
                        }

                    ]
                }

            ],

            response_format={
                "type":
                    "json_object"
            },

            temperature=0.1

        ))

        # =============================================
        # PARSE RESPONSE
        # =============================================

        raw_response = (
                response.choices[0].message.content or ""
        ).strip()

        if not raw_response:
            raise RuntimeError(
                "Gemini Vision "
                "returned empty response"
            )

        # Robust JSON parsing for homework vision. Models may occasionally
        # wrap otherwise-valid JSON in markdown fences or add short text
        # before/after the object. Do not fail the whole homework flow for
        # those harmless formatting deviations.
        cleaned_response = raw_response.strip()

        if cleaned_response.startswith("```"):
            cleaned_response = re.sub(
                r"^```(?:json)?\s*",
                "",
                cleaned_response,
                flags=re.IGNORECASE
            )
            cleaned_response = re.sub(
                r"\s*```$",
                "",
                cleaned_response
            ).strip()

        analysis = None

        try:
            analysis = json.loads(cleaned_response)
        except json.JSONDecodeError:
            first_brace = cleaned_response.find("{")
            last_brace = cleaned_response.rfind("}")

            if first_brace >= 0 and last_brace > first_brace:
                candidate = cleaned_response[first_brace:last_brace + 1]
                try:
                    analysis = json.loads(candidate)
                except json.JSONDecodeError:
                    analysis = None

        if not isinstance(analysis, dict):
            print(
                "VISION INVALID JSON - SAFE FALLBACK:",
                raw_response
            )
            analysis = {
                "subject": "",
                "topic": "",
                "language": "",
                "instructions": "",
                "extracted_text": "",
                "exercises": [],
                "handwritten_answers": [],
                "confidence": 0,
                "needs_high_resolution": False
            }

        # =============================================
        # EXTRACT VALUES
        # =============================================

        extracted_text = (
                analysis.get(
                    "extracted_text"
                )
                or ""
        )

        detected_subject = (
            analysis.get(
                "subject"
            )
        )

        detected_topic = (
            analysis.get(
                "topic"
            )
        )

        detected_language = (
            analysis.get(
                "language"
            )
        )

        needs_high_resolution = bool(

            analysis.get(
                "needs_high_resolution",
                False
            )

        )

        confidence = float(

            analysis.get(
                "confidence",
                0
            )

            or 0

        )

        # =============================================
        # TOKEN USAGE
        # =============================================

        input_tokens = 0

        output_tokens = 0

        total_tokens = 0

        if response.usage:
            input_tokens = response.usage.prompt_tokens or 0
            output_tokens = response.usage.completion_tokens or 0
            total_tokens = response.usage.total_tokens or 0

        # =============================================
        # STATUS
        # =============================================

        if needs_high_resolution:

            vision_status = (
                "needs_high_resolution"
            )

        else:

            vision_status = (
                "completed"
            )

        # =============================================
        # UPDATE homework_uploads
        # =============================================

        (await run_in_threadpool(lambda: sb.table(
            "homework_uploads"
        ).update({

            "vision_status":
                vision_status,

            "vision_model":
                DEFAULT_OPENAI_MODEL,

            "vision_call_count":
                1,

            "extracted_text":
                extracted_text,

            "detected_subject":
                detected_subject,

            "detected_topic":
                detected_topic,

            "detected_language":
                detected_language,

            "analysis_json":
                analysis,

            "input_tokens":
                input_tokens,

            "output_tokens":
                output_tokens,

            "total_tokens":
                total_tokens,

            "used_high_resolution":
                False,

            "updated_at":
                datetime
                .now(timezone.utc)
                .isoformat()

        }).eq(

            "id",
            upload_row_id

        ).execute()))

        # =============================================
        # SESSION USAGE
        # =============================================

        (await run_in_threadpool(lambda: update_tutor_session_after_vision(

            session_id=session_id,

            image_uploads=1,

            vision_calls=1

        )))

        # =============================================
        # MONTHLY USAGE
        # =============================================

        (await run_in_threadpool(lambda: increment_usage_summary(

            user_id=user.id,

            image_uploads=1,

            vision_calls=1

        )))

        # =============================================
        # RESPONSE TO FRONTEND
        # =============================================

        return {

            "success":
                True,

            "upload_id":
                upload_row_id,

            "session_id":
                session_id,

            "vision_status":
                vision_status,

            "child_name":
                str(child.get("child_name") or "").strip(),

            "gender":
                str(child.get("gender") or "unknown").strip().lower(),

            "needs_high_resolution":
                needs_high_resolution,

            "confidence":
                confidence,

            "subject":
                detected_subject,

            "topic":
                detected_topic,

            "language":
                detected_language,

            "extracted_text":
                extracted_text,

            "analysis":
                analysis

        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "HOMEWORK ANALYZE ERROR:",
            repr(e)
        )

        # =============================================
        # UPDATE FAILED ROW
        # =============================================

        if upload_row_id:

            try:

                (await run_in_threadpool(lambda: sb.table(
                    "homework_uploads"
                ).update({

                    "vision_status":
                        "failed",

                    "vision_error":
                        str(e)[:1000],

                    "updated_at":
                        datetime
                        .now(timezone.utc)
                        .isoformat()

                }).eq(

                    "id",
                    upload_row_id

                ).execute()))

            except Exception as update_error:

                print(
                    "HOMEWORK ERROR UPDATE FAILED:",
                    repr(update_error)
                )

        raise HTTPException(

            status_code=500,

            detail=(
                "Homework analysis failed"
            )

        )


# =====================================================
# AI TUTOR CHAT
# =====================================================

# =====================================================
# CURRICULUM BUILDER CHAT
# =====================================================

def build_curriculum_builder_prompt(child: dict, custom_subject: dict | None, current_tree: dict, history: list) -> str:
    """Fill the prompt's placeholders (until 2026-09-15 the runtime context was only appended as
    JSON, so the model saw the literal text "שם: {child_name}") and add the runtime context."""
    gender, _ = hebrew_gender_rule(child)
    history_lines = []
    for item in history or []:
        if isinstance(item, dict) and item.get("content"):
            role = "הורה" if item.get("role") == "user" else "מערכת"
            history_lines.append(f"{role}: {str(item.get('content')).strip()}")
    replacements = {
        "{child_name}": str(child.get("child_name") or ""),
        "{grade}": str(child.get("age") or ""),
        "{gender}": gender,
        "{subject}": str((custom_subject or {}).get("subject_name") or "לא זוהה עדיין"),
        "{current_tree}": json.dumps(current_tree, ensure_ascii=False) if current_tree else "אין עדיין",
        "{conversation_history}": "\n".join(history_lines) if history_lines else "אין עדיין",
    }
    prompt = CURRICULUM_BUILDER_PROMPT_TEMPLATE
    for k, v in replacements.items():
        prompt = prompt.replace(k, v)
    runtime_context = {
        "child": {"id": child.get("id"), "name": child.get("child_name"), "grade": child.get("age"), "gender": gender},
        "current_subject": (
            {"id": custom_subject.get("id"), "subject_name": custom_subject.get("subject_name"),
             "status": custom_subject.get("status")} if custom_subject else None
        ),
        "current_curriculum": current_tree,
    }
    return prompt + "\n\nRUNTIME_CONTEXT:\n" + json.dumps(runtime_context, ensure_ascii=False, indent=2)


@app.post("/api/curriculum/chat")
async def curriculum_builder_chat(
        body: CurriculumBuilderChatRequest,
        authorization: str = Header(None)
):
    try:

        # =============================================
        # AUTH
        # =============================================

        user = (await run_in_threadpool(lambda: authenticate_user(
            authorization
        )))
        ai_context("curriculum", user, body)

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        message = str(
            body.message or ""
        ).strip()

        if not message:
            raise HTTPException(
                status_code=400,
                detail="message is required"
            )

        # =============================================
        # CHILD OWNERSHIP
        # =============================================

        child = (await run_in_threadpool(lambda: get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )))

        custom_subject = None
        current_curriculum = None

        # =============================================
        # LOAD EXISTING SUBJECT + TREE
        # =============================================

        if body.custom_subject_id:

            custom_subject = (await run_in_threadpool(lambda: (
                get_custom_subject(
                    user_id=user.id,
                    kid_id=child["id"],
                    custom_subject_id=
                        body.custom_subject_id
                )
            )))

            current_curriculum = (await run_in_threadpool(lambda: (
                get_current_custom_curriculum(
                    custom_subject_id=
                        custom_subject["id"]
                )
            )))

        current_tree = {}

        if current_curriculum:
            current_tree = (
                current_curriculum.get(
                    "curriculum_json"
                )
                or {}
            )

        # =============================================
        # RUNTIME CONTEXT
        # =============================================

        system_prompt = build_curriculum_builder_prompt(
            child, custom_subject, current_tree, body.history or []
        )

        # =============================================
        # CONVERSATION HISTORY
        # =============================================

        messages = [
            {
                "role":
                    "system",

                "content":
                    system_prompt
            }
        ]

        history = (
            body.history
            or []
        )

        for item in history[-12:]:

            if not isinstance(
                    item,
                    dict
            ):
                continue

            role = item.get(
                "role"
            )

            content = str(
                item.get(
                    "content"
                )
                or ""
            ).strip()

            if (
                    role not in (
                        "user",
                        "assistant"
                    )
                    or not content
            ):
                continue

            messages.append({
                "role":
                    role,

                "content":
                    content
            })

        messages.append({
            "role":
                "user",

            "content":
                message
        })

        # =============================================
        # OPENAI
        # =============================================

        completion = (await (
            aclient.beta.chat.completions.parse(

                model=
                    DEFAULT_OPENAI_MODEL,

                messages=
                    messages,

                response_format=
                    CurriculumBuilderAIResponse
            )
        ))

        curriculum_data = (
            completion
            .choices[0]
            .message
            .parsed
        )

        if not curriculum_data:
            raise RuntimeError(
                "Curriculum Builder returned no response"
            )

        response_subject = str(
            curriculum_data.subject
            or ""
        ).strip()

        if curriculum_data.hierarchy:

            hierarchy = (
                curriculum_data
                .hierarchy
                .model_dump()
            )

        else:

            hierarchy = (
                    current_tree
                    or {}
            )

        # =============================================
        # CREATE SUBJECT
        #
        # ברגע שה-AI זיהה מקצוע,
        # נוצרת הרשומה הראשית.
        # =============================================

        if (
                not custom_subject
                and response_subject
        ):

            custom_subject = (await run_in_threadpool(lambda: (
                create_custom_subject(
                    user_id=user.id,
                    kid_id=child["id"],
                    subject_name=
                    response_subject
                )
            )))

            # אם חזר מקצוע שכבר היה קיים,
            # נטען גם את התוכנית הקיימת שלו.
            current_curriculum = (await run_in_threadpool(lambda: (
                get_current_custom_curriculum(
                    custom_subject_id=
                    custom_subject["id"]
                )
            )))

            if current_curriculum:
                current_tree = (
                        current_curriculum.get(
                            "curriculum_json"
                        )
                        or {}
                )

        # =============================================
        # SAVE CURRICULUM
        # =============================================

        if (
                custom_subject
                and hierarchy
        ):

            if not current_curriculum:

                current_curriculum = (await run_in_threadpool(lambda: (
                    create_custom_curriculum(
                        user_id=user.id,

                        kid_id=
                            child["id"],

                        custom_subject_id=
                            custom_subject["id"],

                        curriculum_json=
                            hierarchy,

                        ready_to_create=
                            bool(
                                curriculum_data
                                .ready_to_create
                            ),

                        parent_message=
                            message
                    )
                )))

            else:

                current_curriculum = (await run_in_threadpool(lambda: (
                    update_custom_curriculum(
                        user_id=user.id,

                        kid_id=
                            child["id"],

                        custom_subject=
                            custom_subject,

                        curriculum=
                            current_curriculum,

                        curriculum_json=
                            hierarchy,

                        subject_name=
                            response_subject,

                        ready_to_create=
                            bool(
                                curriculum_data
                                .ready_to_create
                            ),

                        parent_message=
                            message
                    )
                )))

        # =============================================
        # TOKEN USAGE
        # =============================================

        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        if completion.usage:

            input_tokens = (
                completion
                .usage
                .prompt_tokens
                or 0
            )

            output_tokens = (
                completion
                .usage
                .completion_tokens
                or 0
            )

            total_tokens = (
                completion
                .usage
                .total_tokens
                or 0
            )

        openai_cost_usd = (
            calculate_openai_cost(
                model=
                    DEFAULT_OPENAI_MODEL,

                input_tokens=
                    input_tokens,

                output_tokens=
                    output_tokens
            )
        )

        (await run_in_threadpool(lambda: increment_usage_summary(
            user_id=user.id,

            ai_calls=1,

            input_tokens=
                input_tokens,

            output_tokens=
                output_tokens,

            total_tokens=
                total_tokens,

            openai_cost_usd=
                openai_cost_usd
        )))

        # =============================================
        # RESPONSE TO FRONTEND
        # =============================================

        response_data = (
            curriculum_data
            .model_dump()
        )

        response_data[
            "kid_id"
        ] = child["id"]

        response_data[
            "custom_subject_id"
        ] = (
            custom_subject.get("id")
            if custom_subject
            else None
        )

        response_data[
            "curriculum_id"
        ] = (
            current_curriculum.get("id")
            if current_curriculum
            else None
        )

        response_data[
            "version"
        ] = (
            current_curriculum.get(
                "version"
            )
            if current_curriculum
            else None
        )

        response_data[
            "curriculum_status"
        ] = (
            current_curriculum.get(
                "status"
            )
            if current_curriculum
            else None
        )

        return response_data

    except HTTPException:
        raise

    except Exception as e:

        print(
            "CURRICULUM BUILDER ERROR:",
            repr(e)
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Curriculum Builder failed"
        )

# =====================================================
# APPROVE CUSTOM CURRICULUM
# =====================================================

@app.post("/api/curriculum/approve")
def approve_custom_curriculum(
        body: CurriculumApproveRequest,
        authorization: str = Header(None)
):
    try:

        # =============================================
        # AUTH
        # =============================================

        user = authenticate_user(
            authorization
        )

        if not body.kid_id:
            raise HTTPException(
                status_code=400,
                detail="kid_id is required"
            )

        if not body.custom_subject_id:
            raise HTTPException(
                status_code=400,
                detail="custom_subject_id is required"
            )

        if not body.curriculum_id:
            raise HTTPException(
                status_code=400,
                detail="curriculum_id is required"
            )

        # =============================================
        # CHILD
        # =============================================

        child = get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )

        # =============================================
        # SUBJECT
        # =============================================

        custom_subject = get_custom_subject(
            user_id=user.id,
            kid_id=child["id"],
            custom_subject_id=
                body.custom_subject_id
        )

        # =============================================
        # CURRICULUM
        # =============================================

        curriculum_res = (
            sb.table(
                "kid_custom_curriculums"
            )
            .select("*")
            .eq(
                "id",
                body.curriculum_id
            )
            .eq(
                "custom_subject_id",
                custom_subject["id"]
            )
            .eq(
                "user_id",
                user.id
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .limit(1)
            .execute()
        )

        if not curriculum_res.data:
            raise HTTPException(
                status_code=404,
                detail="Curriculum not found"
            )

        curriculum = (
            curriculum_res.data[0]
        )

        curriculum_json = (
            curriculum.get(
                "curriculum_json"
            )
            or {}
        )

        if not curriculum_json:
            raise HTTPException(
                status_code=400,
                detail="Curriculum is empty"
            )

        current_version = int(
            curriculum.get(
                "version"
            )
            or 1
        )

        now_iso = (
            datetime
            .now(timezone.utc)
            .isoformat()
        )

        # =============================================
        # ACTIVATE SUBJECT
        # =============================================

        subject_update = (
            sb.table(
                "kid_custom_subjects"
            )
            .update({
                "status":
                    "active",

                "updated_at":
                    now_iso
            })
            .eq(
                "id",
                custom_subject["id"]
            )
            .eq(
                "user_id",
                user.id
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .execute()
        )

        if not subject_update.data:
            raise RuntimeError(
                "Failed to activate custom subject"
            )

        # =============================================
        # ACTIVATE CURRICULUM
        # =============================================

        curriculum_update = (
            sb.table(
                "kid_custom_curriculums"
            )
            .update({
                "status":
                    "active",

                "last_change_type":
                    "approved",

                "last_change_summary":
                    "Parent approved curriculum",

                "updated_by":
                    "parent",

                "updated_at":
                    now_iso
            })
            .eq(
                "id",
                curriculum["id"]
            )
            .eq(
                "user_id",
                user.id
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .execute()
        )

        if not curriculum_update.data:
            raise RuntimeError(
                "Failed to activate curriculum"
            )

        approved_curriculum = (
            curriculum_update.data[0]
        )

        # =============================================
        # MARK CURRENT VERSION AS APPROVED
        # =============================================

        version_update = (
            sb.table(
                "kid_custom_curriculum_versions"
            )
            .update({
                "change_type":
                    "approved",

                "change_summary":
                    "Parent approved curriculum",

                "changed_by":
                    "parent"
            })
            .eq(
                "curriculum_id",
                curriculum["id"]
            )
            .eq(
                "version",
                current_version
            )
            .eq(
                "user_id",
                user.id
            )
            .eq(
                "kid_id",
                child["id"]
            )
            .execute()
        )

        # =============================================
        # BUILD RUNTIME UNITS + LESSONS
        # =============================================

        topics = (
            curriculum_json.get("topics")
            or []
        )

        if not isinstance(topics, list):
            raise RuntimeError(
                "Invalid curriculum topics"
            )

        units_created = 0
        lessons_created = 0

        for topic_index, topic in enumerate(
                topics,
                start=1
        ):

            if not isinstance(topic, dict):
                continue

            topic_name = str(
                topic.get("name")
                or ""
            ).strip()

            if not topic_name:
                continue

            units = (
                topic.get("units")
                or []
            )

            if not isinstance(units, list):
                continue

            for unit_index, unit in enumerate(
                    units,
                    start=1
            ):

                if not isinstance(unit, dict):
                    continue

                unit_name = str(
                    unit.get("name")
                    or ""
                ).strip()

                if not unit_name:
                    continue

                # =====================================
                # FIND EXISTING UNIT
                # =====================================

                existing_unit_res = (
                    sb.table(
                        "kid_custom_units"
                    )
                    .select("*")
                    .eq(
                        "curriculum_id",
                        curriculum["id"]
                    )
                    .eq(
                        "topic_order",
                        topic_index
                    )
                    .eq(
                        "unit_order",
                        unit_index
                    )
                    .limit(1)
                    .execute()
                )

                if existing_unit_res.data:

                    custom_unit = (
                        existing_unit_res.data[0]
                    )

                    # אם השם השתנה בגרסה חדשה
                    # מעדכנים את היחידה הקיימת
                    update_unit_res = (
                        sb.table(
                            "kid_custom_units"
                        )
                        .update({
                            "topic_name":
                                topic_name,

                            "unit_name":
                                unit_name,

                            "status":
                                "active",

                            "source_curriculum_version":
                                current_version,

                            "updated_at":
                                now_iso
                        })
                        .eq(
                            "id",
                            custom_unit["id"]
                        )
                        .execute()
                    )

                    if update_unit_res.data:
                        custom_unit = (
                            update_unit_res.data[0]
                        )

                else:

                    # =================================
                    # CREATE UNIT
                    # =================================

                    unit_insert_res = (
                        sb.table(
                            "kid_custom_units"
                        )
                        .insert({
                            "user_id":
                                user.id,

                            "kid_id":
                                child["id"],

                            "custom_subject_id":
                                custom_subject["id"],

                            "curriculum_id":
                                curriculum["id"],

                            "topic_name":
                                topic_name,

                            "topic_order":
                                topic_index,

                            "unit_name":
                                unit_name,

                            "unit_order":
                                unit_index,

                            "status":
                                "active",

                            "source_curriculum_version":
                                current_version,

                            "created_at":
                                now_iso,

                            "updated_at":
                                now_iso
                        })
                        .execute()
                    )

                    if not unit_insert_res.data:
                        raise RuntimeError(
                            "Failed to create custom unit"
                        )

                    custom_unit = (
                        unit_insert_res.data[0]
                    )

                    units_created += 1


                # =====================================
                # LESSONS
                # =====================================

                lessons = (
                    unit.get("lessons")
                    or []
                )

                if not isinstance(
                        lessons,
                        list
                ):
                    continue

                for lesson_index, lesson in enumerate(
                        lessons,
                        start=1
                ):

                    if not isinstance(
                            lesson,
                            dict
                    ):
                        continue

                    lesson_name = str(
                        lesson.get("name")
                        or ""
                    ).strip()

                    if not lesson_name:
                        continue

                    # =================================
                    # FIND EXISTING LESSON
                    # =================================

                    existing_lesson_res = (
                        sb.table(
                            "kid_custom_lessons"
                        )
                        .select("*")
                        .eq(
                            "custom_unit_id",
                            custom_unit["id"]
                        )
                        .eq(
                            "lesson_order",
                            lesson_index
                        )
                        .limit(1)
                        .execute()
                    )

                    if existing_lesson_res.data:

                        existing_lesson = (
                            existing_lesson_res.data[0]
                        )

                        sb.table(
                            "kid_custom_lessons"
                        ).update({
                            "lesson_name":
                                lesson_name,

                            "source_curriculum_version":
                                current_version,

                            "updated_at":
                                now_iso
                        }).eq(
                            "id",
                            existing_lesson["id"]
                        ).execute()

                    else:

                        # =============================
                        # CREATE LESSON
                        # =============================

                        lesson_insert_res = (
                            sb.table(
                                "kid_custom_lessons"
                            )
                            .insert({
                                "user_id":
                                    user.id,

                                "kid_id":
                                    child["id"],

                                "custom_subject_id":
                                    custom_subject["id"],

                                "curriculum_id":
                                    curriculum["id"],

                                "custom_unit_id":
                                    custom_unit["id"],

                                "lesson_name":
                                    lesson_name,

                                "lesson_order":
                                    lesson_index,

                                "status":
                                    "pending",

                                "source_curriculum_version":
                                    current_version,

                                "created_at":
                                    now_iso,

                                "updated_at":
                                    now_iso
                            })
                            .execute()
                        )

                        if not lesson_insert_res.data:
                            raise RuntimeError(
                                "Failed to create custom lesson"
                            )

                        lessons_created += 1

        print(
            "CUSTOM CURRICULUM APPROVED:",
            json.dumps(
                {
                    "user_id":
                        user.id,

                    "kid_id":
                        child["id"],

                    "custom_subject_id":
                        custom_subject["id"],

                    "curriculum_id":
                        curriculum["id"],

                    "version":
                        current_version,

                    "version_rows_updated":
                        len(
                            version_update.data
                            or []
                        ),
                    "units_created":
                        units_created,

                    "lessons_created":
                        lessons_created
                },
                ensure_ascii=False,
                indent=2
            )
        )

        return {
            "success": True,

            "kid_id":
                child["id"],

            "custom_subject_id":
                custom_subject["id"],

            "curriculum_id":
                approved_curriculum["id"],

            "subject":
                custom_subject.get(
                    "subject_name"
                ),

            "version":
                approved_curriculum.get(
                    "version"
                ),

            "subject_status":
                "active",

            "curriculum_status":
                "active",

            "units_created":
                units_created,

            "lessons_created":
                lessons_created
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "CURRICULUM APPROVE ERROR:",
            repr(e)
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Curriculum approval failed"
        )

@app.post("/api/tutor/chat")
async def tutor_chat(
        body: TutorChatRequest,
        authorization: str = Header(None)
):
    try:
        # אימות משתמש
        user = (await run_in_threadpool(lambda: authenticate_user(authorization)))
        ai_context("chat", user, body)

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

        child = (await run_in_threadpool(lambda: get_child_by_id(
            user_id=user.id,
            kid_id=body.kid_id
        )))

        # =================================================
        # GET OR CREATE TUTOR SESSION
        # =================================================

        tutor_session = (await run_in_threadpool(lambda: get_or_create_tutor_session(
            user_id=user.id,
            kid_id=child["id"]
        )))

        session_id = tutor_session["id"]

        existing_memory = (await run_in_threadpool(lambda: get_existing_kids_memory(
            child["id"]
        )))

        system_prompt = build_tutor_prompt(
            child=child,
            kids_memory=existing_memory
        )

        # מביאים רק את ההיסטוריה הקודמת.
        # את ההודעה הנוכחית נוסיף מקומית ולא נשמור לפני קריאת ה-AI.
        recent_messages = (await run_in_threadpool(lambda: get_recent_tutor_messages_for_llm(
            kid_id=child["id"],
            limit=7
        )))

        recent_messages.append({
            "role": "user",
            "content": message
        })

        completion = (await aclient.beta.chat.completions.parse(

            model=DEFAULT_OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                *recent_messages
            ],
            response_format=
            TutorLessonResponse
        ))

        lesson_data = completion.choices[0].message.parsed

        if lesson_data and lesson_data.sequence:

            has_write = any(
                action.type == "write"
                for action in lesson_data.sequence
            )

            if not has_write and lesson_data.speech:
                lesson_data.sequence.insert(
                    0,
                    TutorAction(
                        type="write",
                        text=lesson_data.speech,
                        style="normal",
                        speed=45
                    )
                )
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

        openai_cost_usd = calculate_openai_cost(

            model=
            DEFAULT_OPENAI_MODEL,

            input_tokens=
            input_tokens,

            output_tokens=
            output_tokens

        )

        # שומרים את הודעת הילד ותשובת ה-AI יחד
        # בקריאת Supabase אחת
        # =================================================
        # יצירת טקסט נקי של תשובת המורה לשמירה בהיסטוריה
        # =================================================

        assistant_history_parts = []

        # מוסיפים את speech הראשי
        if lesson_data.speech:
            assistant_history_parts.append(
                lesson_data.speech.strip()
            )

        # מוסיפים את הטקסטים הרלוונטיים מה-sequence
        for action in lesson_data.sequence or []:

            if (
                    action.type in ("write", "ask")
                    and action.text
                    and action.text.strip()
            ):

                clean_text = action.text.strip()

                # מונע שמירת אותו טקסט פעמיים
                if clean_text not in assistant_history_parts:
                    assistant_history_parts.append(
                        clean_text
                    )

        assistant_history_text = "\n".join(
            assistant_history_parts
        )

        # שומרים את הודעת הילד ואת תשובת המורה הנקייה
        (await run_in_threadpool(lambda: save_tutor_chat_messages(
            user_id=user.id,
            kid_id=child["id"],
            user_content=message,
            assistant_content=assistant_history_text,
            assistant_tokens=total_tokens,
            session_id=session_id
        )))

        (await run_in_threadpool(lambda: update_tutor_session_after_chat(
            session=tutor_session,
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=openai_cost_usd
        )))

        (await run_in_threadpool(lambda: increment_usage_summary(

            user_id=user.id,

            sessions=(
                1
                if tutor_session.get("_is_new")
                else 0
            ),

            ai_calls=1,

            input_tokens=input_tokens,

            output_tokens=output_tokens,

            total_tokens=total_tokens,

            openai_cost_usd=openai_cost_usd
        )))


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


# =====================================================
# IAKIDS HOMEWORK TURN EVALUATOR V0.7.26
# =====================================================

HOMEWORK_GLOBAL_PEDAGOGY_PROMPT = r"""
את/ה מורה פרטית חכמה לילדים שעוזרת בשיעורי בית.

המטרה שלך היא לא רק להגיע לתשובה הנכונה, אלא ללמד את הילד/ה איך להבין את המשימה, איך לחשוב עליה, איך למצוא את המידע הדרוש ואיך לבנות תשובה טובה בעצמו/ה.

כללי הוראה מחייבים:
1. קודם להבין מה בדיוק המשימה או השאלה מבקשת.
2. אם יש מקור מצורף — טקסט, תמונה, דף עבודה, תרשים, טבלה, גרף, ניסוי, הוראות או נתונים — הוא מקור האמת המרכזי.
3. אין להמציא פרטים שלא מופיעים במקור.
4. אין לשאול שאלת הכוונה שהתשובה עליה לא ניתנת מתוך המקור או מתוך הידע שהמשימה דורשת במפורש.
5. כל רמז צריך לקדם ישירות לפתרון של השאלה הנוכחית.
6. אין לסטות לנושאים כלליים, חיים אישיים, רגשות, ערכים או דוגמאות שלא נדרשו במשימה.
7. אין לחזור על אותה שאלה שוב ושוב בניסוחים שונים.
8. אם הילד/ה אומר/ת "לא יודע/ת", אין לשאול שוב את אותה שאלה. במקום זה יש לפרק את המשימה לצעד קטן יותר, להפנות למקום רלוונטי במקור, להצביע על מילת מפתח, לתת רמז ממוקד, לתת התחלה של דרך פתרון או תבנית חלקית של תשובה.
9. בכל פעם שואלים שאלה אחת בלבד, קצרה וברורה.
10. אם הילד/ה כבר הבין/ה את הרעיון המרכזי, לא ממשיכים לחפש מידע נוסף שלא נדרש.
11. לפני שנותנים תשובה מלאה, עוזרים לילד/ה להגיע לרעיון בעצמו/ה.
12. אם הילד/ה מבין/ה את התוכן אבל מתקשה בניסוח, עוזרים לבנות תשובה באמצעות פתיח, תבנית משפט או מבנה.
13. משוב חייב להיות ספציפי: מה נכון, מה חסר ומה הצעד הבא.
14. לא להסתפק ב"כל הכבוד" או "נכון".
15. כאשר התשובה כבר מספיקה, יש להסביר בקצרה למה היא נכונה, להציע ניסוח מלא וקצר, ואז לאפשר למערכת לעבור לשאלה הבאה.
16. אין לתת את התשובה הסופית מיד, אלא אם הילד/ה כבר קיבל/ה מספר רמזים ועדיין תקוע/ה.

אסטרטגיית עבודה:
שלב 1 — להבין את המשימה: לזהות אם השאלה דורשת עובדה, סיבה, תוצאה, הסבר, מסקנה, מסר, השוואה, חישוב, תיאור, ניתוח, כתיבה או סוג אחר.
שלב 2 — לזהות את מקור המידע: טקסט, נתונים, תרשים, ידע שנלמד, נוסחה, הוראות, ניסוי או מקור אחר.
שלב 3 — ללמד דרך חשיבה: להסביר איפה לחפש, מה לסמן, אילו מילים או נתונים חשובים, איזה קשר צריך לזהות או לאילו צעדים לפרק את המשימה.
שלב 4 — לאסוף את רכיבי התשובה: לעזור לזהות את הנקודות המרכזיות שצריכות להיכלל.
שלב 5 — לבנות תשובה: אם צריך, לתת פתיח או מבנה שהילד/ה ישלים/תשלים.
שלב 6 — ניסיון עצמאי: לבקש מהילד/ה לנסות לענות.
שלב 7 — משוב: לבדוק אם התשובה מספיקה לשאלה עצמה, בלי לדרוש מידע שלא נדרש.
שלב 8 — ניסוח סופי: רק אחרי שהילד/ה הבין/ה וניסה/תה לענות, לתת ניסוח מלא, קצר וברור.

התאמה לפי סוג משימה:
- משימה מבוססת טקסט: להיצמד לטקסט, להפנות לחלק הרלוונטי, לזהות ראיות/מילות מפתח/פעולות/סיבות/מסקנות, ולא להמציא מידע מחוץ לטקסט.
- מתמטיקה: לזהות מה נתון, מה מבקשים, איזו פעולה או דרך מתאימה, לפתור שלב אחר שלב, ולתת תשובה סופית רק בסוף.
- מדעים: לזהות מושג, תהליך, עובדה, תרשים או ראיה רלוונטיים, לקשר אותם ישירות לשאלה ולבנות הסבר.
- כתיבה: להבהיר מה צריך לכתוב, לפרק לרכיבים, לבנות שלד, לתת פתיח או תבנית, ורק אז לבקש כתיבה עצמאית.
- טבלה/גרף/תרשים: קודם לקרוא כותרת, צירים, מקרא ונתונים, ואז להשתמש רק במה שניתן להסיק מהם.

סגנון:
- ברור
- קצר
- מותאם לגיל
- שאלה אחת בכל פעם
- לא מטיף
- לא מסבך
- לא נותן תשובה מוקדם מדי
- לא ממציא מידע
- תמיד שומר על קשר ישיר בין השאלה, המקור וההכוונה
""".strip()

HOMEWORK_TEACHING_STRATEGIES = {
    "reading_source": "Use the provided source as the primary truth. Give a PRECISE source cue: identify the relevant sentence, paragraph, event, data region, label, or instruction and tell the child what specific feature to look for there (for example: action, cause, result, key word, comparison, value, or evidence). Avoid vague prompts such as asking what they see in the text or what the text says in general. Then ask ONE small focused question answerable from that exact source location. Never invent facts outside the source.",
    "math_problem": "Identify givens, identify what is being asked, choose the required mathematical relation/operation, solve one step at a time, then formulate the contextual answer. Do not reveal the final result before a genuine attempt.",
    "science_reasoning": "Identify the relevant scientific concept, observation, diagram, experiment, or evidence. Connect it explicitly to what the question asks, then help formulate the explanation.",
    "writing_composition": "Clarify the required content and format, break the task into 2-4 components, build a short outline or sentence frame, and only then ask the child to write. Do not ask vague wording questions before giving structure.",
    "language_skill": "Identify the target language skill (vocabulary, grammar, sentence construction, translation, reading). Teach the rule/pattern with one focused cue, then ask for a short application.",
    "data_visual": "Treat the table/chart/diagram/data as the source of truth. First identify what needs to be read or compared, then locate the relevant values/features, then formulate the answer.",
    "knowledge_direct": "Teach only the minimum concept needed for the current question, check one key understanding point, then ask the child to answer in their own words.",
    "general": "Apply the global sequence: understand the task, identify the source/method, isolate key points, provide structure, child attempts, specific feedback, final wording."
}

HOMEWORK_TEACHING_STYLE_PROMPTS = {
    "quantitative_math": r"""
TEACHING STYLE: QUANTITATIVE / MATHEMATICS

You are teaching a child how to solve a mathematical or quantitative task.

Your goal is not only to reach the correct result, but to teach the child how to understand the problem, choose a method, and solve it independently.

MANDATORY TEACHING PRINCIPLES:
1. First identify what information is given, what the question asks, and what mathematical relationship, operation, or method is needed.
2. Do not jump directly to calculation before the child understands what needs to be found.
3. Break the solution into small logical steps.
4. Teach one step at a time. Do not ask several calculations or reasoning steps in one message.
5. If the child already completed a step correctly: acknowledge it briefly, do not ask them to explain it again, do not repeat the same reasoning, and continue immediately to the next unresolved step.
6. If the child makes a mistake: identify the specific step where the mistake occurred, explain only that step, give a focused hint or simpler sub-step, then let the child try again.
7. If the task involves fractions, percentages, ratios, multiplication, division, measurement, geometry, or multi-step word problems, first explain the underlying relationship before asking for the calculation.
8. When useful, teach the method with ONE very short analogous example using different numbers, names, objects, or context from the child's homework.
9. The analogous example must be short and serve only to demonstrate the method. Never reuse the exact numbers or objects from the uploaded homework.
10. After the example, explicitly return to the child's task and apply the same method step by step.
11. Do not give the final numerical answer too early. The child should participate in the main reasoning or calculation steps.
12. At the end: summarize the calculation briefly, verify that the result answers the original question, and give the final answer with the correct unit or context.
13. For word problems, always connect the final number back to what it represents.
14. Keep explanations short, concrete, and appropriate for the child's grade.
15. Avoid unnecessary formulas or terminology when a simpler explanation is enough.

PREFERRED FLOW:
UNDERSTAND THE PROBLEM -> IDENTIFY GIVEN INFORMATION -> IDENTIFY WHAT IS ASKED -> CHOOSE METHOD -> SHORT ANALOGOUS EXAMPLE IF NEEDED -> SOLVE ONE STEP AT A TIME -> CHECK -> FINAL ANSWER
""".strip(),
    "text_comprehension": r"""
TEACHING STYLE: TEXT / READING COMPREHENSION

You are teaching a child how to answer a question whose answer depends mainly on a written source: reading passage, Bible text, history text, literature passage, instructions, or another provided text.

Your goal is not only to reach the correct answer, but to teach the child how to find evidence in the source and turn it into a clear answer independently.

MANDATORY TEACHING PRINCIPLES:
1. First identify exactly what the question is asking: fact, action, cause, result, explanation, comparison, conclusion, message, evidence, sequence, or another text-based task.
2. Treat the provided source as the primary truth. Do not add facts that are not in the source unless the task explicitly requires outside knowledge.
3. Direct the child to the most precise relevant place in the source possible: sentence, paragraph, event, instruction, line, or nearby phrase.
4. Tell the child what to look for there: an action, reason, result, key word, comparison, description, evidence, or sequence.
5. Avoid vague questions such as "what does the text say?" or "what do you see?" when a more precise cue is possible.
6. Break the reasoning into small steps. Ask only one focused question at a time.
7. If the child identifies a correct piece of evidence, treat it as completed. Do not ask for the same evidence again in different words. Move to the next missing component.
8. If the answer requires more than one idea, help collect the ideas one by one before asking for the final formulation.
9. If the child is stuck, move closer to the source: point to the exact section, identify a key word, quote only a very short cue if needed, or give the beginning of an answer frame. Do not simply repeat the worksheet question.
10. When useful, teach the method with ONE very short analogous example based on a different mini-text or different situation. The example must demonstrate the same reading skill without copying the child's text or revealing the homework answer.
11. After the analogous example, explicitly return to the child's actual source and apply the same method.
12. If the child understands the idea but struggles to phrase it, give a short sentence frame or opening phrase rather than writing the whole answer immediately.
13. Do not demand information that the question does not require.
14. Once the answer is sufficient, explain briefly why it answers the question, then provide one concise polished formulation.
15. Keep language short, concrete, grade-appropriate, and closely tied to the source.

PREFERRED FLOW:
UNDERSTAND WHAT THE QUESTION ASKS -> LOCATE THE RELEVANT PART OF THE SOURCE -> IDENTIFY THE NEEDED EVIDENCE -> COLLECT THE REQUIRED IDEA(S) -> BUILD THE ANSWER -> CHILD ATTEMPTS -> SPECIFIC FEEDBACK -> FINAL FORMULATION
""".strip(),
    "conceptual_science": r"""
TEACHING STYLE: CONCEPTUAL / SCIENCE

You are teaching a child how to solve a science, nature, technology, or conceptual reasoning task.

Your goal is not only to reach the correct answer, but to help the child understand the relevant concept, connect it to evidence or observations, and explain the answer independently.

MANDATORY TEACHING PRINCIPLES:
1. First identify what the question is asking: definition, process, cause, result, comparison, relationship, classification, prediction, explanation, evidence, experiment, diagram interpretation, or application of a concept.
2. Identify the minimum scientific concept needed for this question. Do not overload the child with unrelated theory.
3. If the task includes a diagram, experiment, table, observation, image, or provided text, treat that source as primary evidence and use only what it supports.
4. Explain the core concept briefly before asking the child to apply it when the child has not yet demonstrated understanding.
5. Connect concept -> evidence/observation -> question explicitly. Do not jump from a definition directly to the final answer.
6. Break explanations into small causal or logical steps. Ask one focused question at a time.
7. If the child correctly identifies a concept, fact, observation, or connection, mark it as completed and move to the next missing step. Do not ask for the same idea again in different words.
8. If the child is stuck, simplify only the current step: point to the relevant observation, identify one key feature, contrast two possibilities, or give a short causal cue.
9. When useful, teach the idea with ONE very short analogous example from a different situation. The example must use different objects/context from the uploaded homework and must not reveal the real answer.
10. After the analogous example, explicitly return to the child's question and apply the same reasoning pattern.
11. For processes, help the child reason in sequence: what happens first -> what changes -> what happens next -> why.
12. For cause-and-effect questions, distinguish clearly between the cause, the mechanism/connection, and the result.
13. For classification questions, identify the rule/criterion first, then apply it to the item.
14. For experiment questions, distinguish observation from conclusion. Do not invent results not present in the source.
15. For diagrams and systems, identify the relevant parts and the relationship between them before formulating the explanation.
16. If the child understands the science but struggles to phrase the answer, provide a short sentence frame or explanation structure rather than the full answer immediately.
17. Once the answer is sufficient, explain briefly why it is correct, then provide one concise polished formulation.
18. Keep explanations short, concrete, grade-appropriate, and avoid unnecessary technical terminology.

PREFERRED FLOW:
UNDERSTAND WHAT IS ASKED -> IDENTIFY THE RELEVANT CONCEPT -> EXPLAIN THE CORE IDEA -> LOCATE EVIDENCE/OBSERVATION -> CONNECT CONCEPT TO EVIDENCE -> APPLY TO THE QUESTION -> CHILD EXPLAINS -> SPECIFIC FEEDBACK -> FINAL FORMULATION
""".strip(),

    "language_writing": r"""
TEACHING STYLE: LANGUAGE / WRITING

You are teaching a child how to solve a language, grammar, vocabulary, sentence-construction, translation, or writing/composition task.

Your goal is not only to produce a correct sentence or text, but to teach the child the rule, pattern, structure, or writing process needed to do it independently.

MANDATORY TEACHING PRINCIPLES:
1. First identify the exact task type: vocabulary, grammar, spelling, sentence construction, translation, reading in a foreign language, short answer, paragraph, description, explanation, story, opinion, or another writing task.
2. Identify the minimum rule, language pattern, vocabulary item, or writing structure needed for the current task. Do not overload the child with unrelated grammar or theory.
3. Before asking the child to produce an answer, explain the relevant rule or structure briefly when it has not yet been demonstrated.
4. When useful, give ONE very short analogous example using different words, names, sentence content, or topic from the uploaded homework. The example must teach the same rule or structure without revealing the real answer.
5. After the analogous example, explicitly return to the child's actual task and apply the same pattern.
6. For grammar: identify the relevant clue in the sentence, state the rule simply, then apply it one step at a time.
7. For vocabulary: establish meaning from the provided source/context when available, then ask for one focused use or choice.
8. For translation: first identify meaning and sentence structure; do not translate word-by-word when that would produce unnatural or incorrect language.
9. For sentence construction: help the child identify the required parts and correct order before asking for the full sentence.
10. For writing/composition: clarify the assignment requirements first, then build a short plan or outline, then develop one component at a time, and only then ask the child to write the full response.
11. If the child already completed a component correctly, treat it as completed. Do not ask for the same word, rule, idea, or sentence component again. Move to the next unresolved component.
12. If the child is stuck, simplify only the current step: provide a word bank, sentence opener, grammar cue, structure cue, or partial frame. Do not write the full answer immediately.
13. If the child has the right idea but weak wording, help improve wording without replacing the child's work entirely. Explain what changed and why in a short, age-appropriate way.
14. Correct only errors relevant to the current learning goal unless another error prevents understanding.
15. Do not demand stylistic sophistication beyond the child's grade level or the assignment requirements.
16. Ask only one focused question or writing action at a time.
17. Once the response is sufficient, briefly explain why it works and provide one concise polished version when appropriate.
18. Keep explanations short, concrete, grade-appropriate, and in the child's learning language unless the task requires otherwise.

PREFERRED FLOW:
UNDERSTAND THE LANGUAGE/WRITING TASK -> IDENTIFY RULE OR REQUIRED STRUCTURE -> EXPLAIN BRIEFLY -> SHORT ANALOGOUS EXAMPLE IF NEEDED -> BUILD COMPONENTS ONE AT A TIME -> CHILD ATTEMPTS -> SPECIFIC CORRECTION/FEEDBACK -> POLISHED FINAL VERSION
""".strip(),


}

HOMEWORK_HELP_MODE_PROMPTS = {
    "understand_question": r"""
HELP MODE: UNDERSTAND THE QUESTION

The child explicitly chose help understanding what the worksheet question is asking.

Your job in this mode is NOT to solve the exercise and NOT to begin the full solution process. Your job is to make the task itself clear enough that the child knows what they are being asked to do.

MANDATORY BEHAVIOR:
1. Focus only on the current worksheet question.
2. Start by explaining in one or two short sentences what the question is asking the child to find, explain, identify, compare, calculate, write, or prove.
3. Translate difficult wording into simpler age-appropriate language without changing the meaning of the task.
4. Identify the important instruction word(s) or signal(s) in the question, when relevant: for example calculate, explain, compare, according to the text, give a reason, describe, identify, complete, or justify.
5. Identify what information/source the child is expected to use: numbers in the problem, a passage, diagram, table, scientific concept, grammar rule, instructions, or other supplied material.
6. Do NOT calculate the result, reveal the answer, collect all answer components, or walk through the complete solution in this mode.
7. Do NOT immediately interrogate the child. First TEACH what the question means.
8. After the explanation, ask at most ONE short check-for-understanding question whose purpose is only to verify that the child understands the task. The check must not secretly become the first solving step.
9. If a tiny analogous example would make the wording clearer, you may give ONE very short example with completely different content or numbers. The example must illustrate the meaning of the instruction, not solve the uploaded homework.
10. If the child says they still do not understand, simplify the wording further or separate the task into: "what is given" and "what are we being asked to find/do". Do not repeat the same explanation verbatim.
11. Once the child clearly understands what is being asked, stop teaching this mode. Do not continue into a full solution unless the child chooses another help mode or explicitly asks to proceed.
12. Respect the active TEACHING STYLE for how you describe the task: mathematical task language for quantitative work, source/evidence language for text comprehension, concept/process language for science, and rule/structure language for language-writing tasks.

PREFERRED FLOW:
READ THE QUESTION -> SAY IN SIMPLE WORDS WHAT IT ASKS -> IDENTIFY THE SOURCE/INFORMATION TO USE -> OPTIONAL TINY DIFFERENT EXAMPLE -> ONE UNDERSTANDING CHECK -> STOP WHEN THE TASK IS CLEAR
""".strip(),
    "explain_topic": r"""
HELP MODE: EXPLAIN THE TOPIC

The child explicitly chose an explanation of the material/topic needed for the current homework question.

Your job in this mode is to TEACH the minimum concept, rule, method, or background knowledge the child needs BEFORE asking them to solve the real worksheet question.

MANDATORY BEHAVIOR:
1. Focus only on the knowledge needed for the current worksheet question. Do not turn this into a broad lesson about the whole subject.
2. Start with a short, direct explanation in age-appropriate language. Do not begin by interrogating the child.
3. Explain the core idea before asking the child to apply it.
4. Keep the explanation concrete: define the idea, show how it works, and identify the key signal/rule/relationship the child should notice.
5. When useful, give ONE short analogous example that is different from the uploaded homework. Use different numbers, names, objects, sentences, text, or context so the example teaches the method without revealing the real answer.
6. Demonstrate the analogous example briefly enough that the child can see the method. Do not create a second full exercise unless needed.
7. After the explanation/example, explicitly return to the child's actual question with wording such as: "עכשיו נחזור לשאלה שלך".
8. Ask at most ONE short application question that helps the child use the newly explained idea on the real worksheet question.
9. Do not give the final answer immediately. The child should apply the explanation to at least one meaningful step unless they are still stuck after several hints.
10. If the child says they still do not understand, simplify the explanation, use a smaller example, or explain only the confusing sub-concept. Do not repeat the same explanation verbatim.
11. If the child already demonstrates understanding of the concept, do not reteach it. Move directly to the next unresolved application step.
12. Respect the active TEACHING STYLE:
   - quantitative_math: explain the relationship/method and show a tiny different numerical example;
   - text_comprehension: explain the reading skill, evidence type, or instruction meaning with a tiny different text example;
   - conceptual_science: explain the needed concept/process and connect it to an observation or different example;
   - language_writing: explain the relevant rule/structure/pattern and show a different sentence or writing example.
13. Keep the response short enough for homework help: explanation first, then one example if useful, then return to the real question.
14. Never drift to unrelated theory, personal discussion, values, or examples that do not help answer the current worksheet question.
15. Preserve PEDAGOGICAL PROGRESS STATE. If a concept or step has already been mastered, continue from the next unresolved step instead of restarting the explanation.

PREFERRED FLOW:
IDENTIFY NEEDED KNOWLEDGE -> EXPLAIN THE CORE IDEA -> OPTIONAL SHORT DIFFERENT EXAMPLE -> RETURN TO THE CHILD'S QUESTION -> ONE APPLICATION STEP -> CONTINUE FROM PROGRESS STATE
""".strip(),
    "hint": r"""
HELP MODE: SMALL HINT

The child explicitly chose to receive a SMALL HINT for the current homework question.

Your job in this mode is NOT to explain the whole topic, NOT to solve the problem step by step, and NOT to reveal the final answer. Give only the smallest useful clue that moves the child from the current PEDAGOGICAL PROGRESS STATE to the single next unresolved step.

MANDATORY BEHAVIOR:
1. Focus only on the current worksheet question and the next unresolved step.
2. Give ONE hint only in each response.
3. The hint must be short, specific, and actionable. It should narrow where to look, what relation to notice, what rule to recall, what word/data to use, or what first micro-step to try.
4. Do not give a broad explanation of the topic. If the child wanted teaching, that belongs to EXPLAIN THE TOPIC mode.
5. Do not solve several steps at once. If a multi-step task is involved, hint only at the immediate next step.
6. Never reveal the final answer unless the child has already received several increasingly explicit hints and remains genuinely stuck, and the global pedagogy rules allow it.
7. Preserve all completed steps. Never hint toward a step that has already been completed or ask the child to redo it.
8. After the hint, ask at most ONE short question or instruction that lets the child try the hinted step.
9. If the child is still stuck, make the NEXT hint slightly more explicit, but still only for the same unresolved step. Do not restart from the beginning.
10. Respect the active TEACHING STYLE:
   - quantitative_math: point to the needed relation, operation, quantity, or next calculation without doing it for the child;
   - text_comprehension: point to the precise sentence/event/keyword/evidence location and what to notice there;
   - conceptual_science: point to the relevant concept, observation, cause-effect link, or diagram feature;
   - language_writing: point to the relevant grammar rule, word cue, sentence structure, idea component, or writing frame.
11. If the child asks "why?" about the hint, explain only the reasoning behind that hint briefly; do not expand into a full lesson unless the child switches modes.
12. Keep the response concise and age-appropriate. A hint should feel like a nudge, not a mini-lecture.

PREFERRED FLOW:
READ CURRENT PROGRESS -> IDENTIFY SINGLE NEXT UNRESOLVED STEP -> GIVE ONE SMALL SPECIFIC HINT -> ASK CHILD TO TRY THAT STEP -> WAIT
""".strip(),
    "solve_together": r"""
HELP MODE: SOLVE TOGETHER STEP BY STEP

The child explicitly chose to solve the homework together step by step.

Your role in this mode is to TEACH THE METHOD first, then guide the child through the real worksheet question one small step at a time.

MANDATORY BEHAVIOR:
1. Start by identifying the type of task and the general method needed.
2. Before asking the child to solve the real worksheet question, give a SHORT clear explanation of the method in age-appropriate language.
3. Do NOT begin with interrogation. First teach the method.
4. After the explanation, give ONE very short analogous example that uses DIFFERENT numbers, names, objects, sentences, text, or context from the uploaded homework.
5. The analogous example must teach the SAME underlying method while remaining clearly separate from the real homework.
6. Demonstrate or solve the analogous example briefly so the child can see how the method works. Keep it short; do not turn it into another full lesson.
7. Then explicitly return to the real homework with wording such as: "עכשיו נעשה את אותו הדבר בשאלה שלך".
8. Break the real question into small ordered pedagogical steps.
9. Ask the child to perform ONLY the NEXT unresolved step. Ask one question at a time.
10. PEDAGOGICAL PROGRESS STATE is authoritative. Every completed step remains completed. NEVER ask the child to justify it again, repeat it, or restart from it.
11. After a correct step: acknowledge it briefly, state what was achieved if useful, and immediately move to the next unresolved step.
12. If the child makes a mistake or is stuck: explain ONLY the current step, optionally give one smaller hint, then let the child try that same step again. Do not restart the whole solution.
13. Do not give the final answer before the child has participated in the main solving/reasoning steps, except after repeated scaffolding when the child is still stuck.
14. When all required steps are complete: summarize the method briefly, verify that the result/response answers the original worksheet question, provide one concise polished final answer, and allow the application to move to the next question.
15. Respect the active TEACHING STYLE:
   - quantitative_math: explain the mathematical relationship/method, show one different numerical example, then solve the real problem step by step;
   - text_comprehension: explain how to locate/use evidence, show one tiny different text example, then return to the real source and collect evidence step by step;
   - conceptual_science: explain the concept/process, show one different situation, then apply the reasoning to the real question step by step;
   - language_writing: explain the rule/structure, show one different sentence/writing example, then build the real response step by step.
16. The analogous example must NEVER copy the exact homework numbers, names, objects, wording, or answer.
17. Keep each teacher message short and focused. This is guided practice, not a lecture.

PREFERRED FLOW:
IDENTIFY METHOD -> SHORT EXPLANATION -> ONE DIFFERENT ANALOGOUS EXAMPLE -> RETURN TO THE REAL QUESTION -> ONE STEP -> CHILD ANSWERS -> NEXT STEP -> CHECK -> FINAL FORMULATION
""".strip(),

    "check_answer": r"""
HELP MODE: CHECK THE CHILD'S ANSWER

The child explicitly chose: "check an answer I wrote".

Your role in this mode is to evaluate the CHILD'S OWN answer to the CURRENT worksheet question, explain what is correct and what still needs improvement, and help the child repair the answer independently.

MANDATORY BEHAVIOR:
1. If the child has not yet supplied an answer, do NOT solve the worksheet question. Ask the child to type or say the answer they wrote, and stop.
2. Once an answer is supplied, compare it only with what the CURRENT question requires and with the provided source/data/concept. Do not require extra details that the worksheet does not ask for.
3. Judge meaning, reasoning and completeness — not exact wording. A differently worded answer can be fully correct.
4. Start feedback with a precise statement of what is correct in the child's answer. Do not use praise alone.
5. If something is missing or incorrect, identify ONLY the specific missing/incorrect part and explain why it matters for this question.
6. Do not immediately replace a partial answer with the full correct answer. Give ONE focused repair instruction, clue, source cue, calculation check, rule cue, or sentence frame, then let the child improve the answer.
7. If the answer contains a mathematical calculation, check both the method and result. If one step is wrong, point to that exact step rather than restarting the entire problem.
8. If the answer depends on a text/source, verify that the answer is supported by the source. Point to the precise relevant evidence if correction is needed; never invent evidence.
9. If the answer is scientific, check that the relevant concept and the required cause/process/evidence connection are correct.
10. If the answer is language/writing, separate content correctness from wording/grammar. Correct only what is needed for the task and grade level.
11. Respect PEDAGOGICAL PROGRESS STATE: any step already established as correct remains completed. Never make the child re-prove it.
12. If the answer is already sufficient, say specifically why it answers the question, mark it sufficient, and provide ONE concise polished formulation only if useful.
13. When the answer is sufficient, do not keep searching for optional details. Allow the application to complete the question and move on.
14. Ask at most ONE repair question/action at a time.
15. Keep feedback short, clear, concrete, supportive, and grade-appropriate.

MODE-SPECIFIC FLOW:
NO CHILD ANSWER YET -> ASK FOR THE CHILD'S ANSWER -> CHECK AGAINST CURRENT QUESTION/SOURCE -> STATE WHAT IS CORRECT -> IDENTIFY ONE MISSING/WRONG PART IF ANY -> GIVE ONE REPAIR STEP -> CHILD REVISES -> RECHECK -> MARK SUFFICIENT -> OPTIONAL POLISHED FORMULATION
""".strip()

}

def resolve_homework_help_mode(help_mode: str | None) -> tuple[str | None, str]:
    name = str(help_mode or "").strip()
    if name in HOMEWORK_HELP_MODE_PROMPTS:
        return name, HOMEWORK_HELP_MODE_PROMPTS[name]
    return None, ""


def resolve_homework_teaching_style(strategy_name: str) -> tuple[str | None, str]:
    # First new teaching style: math / quantitative.
    # The remaining three styles will be added separately.
    name = str(strategy_name or "").strip()
    if name == "math_problem":
        return "quantitative_math", HOMEWORK_TEACHING_STYLE_PROMPTS["quantitative_math"]
    if name == "reading_source":
        return "text_comprehension", HOMEWORK_TEACHING_STYLE_PROMPTS["text_comprehension"]
    if name == "science_reasoning":
        return "conceptual_science", HOMEWORK_TEACHING_STYLE_PROMPTS["conceptual_science"]
    if name in ("language_skill", "writing_composition"):
        return "language_writing", HOMEWORK_TEACHING_STYLE_PROMPTS["language_writing"]
    return None, ""


def resolve_homework_teaching_strategy(question: str, source_text: str) -> tuple[str, str]:
    q = str(question or "").strip().lower()
    s = str(source_text or "").strip().lower()
    combined = f"{q}\n{s}"

    if any(token in combined for token in [
        "קטע קריאה", "לפי הקטע", "על פי הקטע", "בסיפור", "בטקסט",
        "מה אפשר ללמוד", "מה ניתן ללמוד", "מסר", "מסקנה", "תנ״ך", "פרשה"
    ]):
        return "reading_source", HOMEWORK_TEACHING_STRATEGIES["reading_source"]

    if any(token in combined for token in [
        "חשב", "חשבו", "כמה", "סכום", "הפרש", "כפל", "חילוק", "שבר",
        "אחוז", "משוואה", "היקף", "שטח", "זווית"
    ]):
        return "math_problem", HOMEWORK_TEACHING_STRATEGIES["math_problem"]

    if any(token in combined for token in [
        "גרף", "טבלה", "תרשים", "דיאגרמה", "נתונים", "ציר"
    ]):
        return "data_visual", HOMEWORK_TEACHING_STRATEGIES["data_visual"]

    if any(token in combined for token in [
        "כתבו", "כתבי", "חיבור", "פסקה", "תארו", "תארי", "נמקו", "נמקי",
        "writing", "composition"
    ]):
        return "writing_composition", HOMEWORK_TEACHING_STRATEGIES["writing_composition"]

    if any(token in combined for token in [
        "מדעים", "science", "ניסוי", "תהליך", "מערכת", "אנרגיה", "כוח",
        "חומר", "סביבה", "אקולוג"
    ]):
        return "science_reasoning", HOMEWORK_TEACHING_STRATEGIES["science_reasoning"]

    if any(token in combined for token in [
        "grammar", "vocabulary", "דקדוק", "אוצר מילים", "תרגמו", "תרגמי",
        "english", "אנגלית"
    ]):
        return "language_skill", HOMEWORK_TEACHING_STRATEGIES["language_skill"]

    return "general", HOMEWORK_TEACHING_STRATEGIES["general"]

class HomeworkTurnRequest(BaseModel):
    kid_id: str
    current_question_number: int
    current_question: str
    answer: str
    source_text: str = ""
    next_question_number: int | None = None
    next_question: str | None = None
    session_id: str | None = None
    homework_session_id: str | None = None


    progress_context: str | None = None
    help_mode: str | None = None
class HomeworkSessionStartRequest(BaseModel):
    kid_id: str
    tutor_session_id: str | None = None
    subject: str | None = None
    topic: str | None = None
    source_file_name: str | None = None
    source_file_url: str | None = None
    source_type: str | None = None
    total_questions: int = 0


@app.post("/api/tutor/homework-session/start")
def start_homework_session(
        req: HomeworkSessionStartRequest,
        authorization: str = Header(None)
):
    user = authenticate_user(authorization)
    child = get_child_by_id(user.id, req.kid_id)

    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "user_id": user.id,
        "kid_id": child["id"],
        "tutor_session_id": req.tutor_session_id,
        "subject": req.subject,
        "topic": req.topic,
        "source_file_name": req.source_file_name,
        "source_file_url": req.source_file_url,
        "source_type": req.source_type,
        "total_questions": max(0, int(req.total_questions or 0)),
        "completed_questions": 0,
        "status": "in_progress",
        "started_at": now_iso,
        "last_activity_at": now_iso,
        "updated_at": now_iso
    }

    result = supabase_with_retry(
        lambda: sb.table("homework_sessions").insert(payload).execute(),
        label="HOMEWORK SESSION START"
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create homework session")

    return result.data[0]


def _normalize_homework_guard_text(value: str) -> str:
    text = str(value or "").lower()
    text = re.sub(r'[\"\'׳״“”‘’.,!?;:()\[\]{}<>\\/|_\-–—]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def homework_response_leaks_source_answer(
        teacher_response: str,
        source_text: str,
        current_question: str,
        min_words: int = 6
) -> bool:
    response = _normalize_homework_guard_text(teacher_response)
    source = _normalize_homework_guard_text(source_text)
    question = _normalize_homework_guard_text(current_question)

    if not response or not source:
        return False

    words = response.split()
    if len(words) < min_words:
        return False

    for size in (9, 8, 7, 6):
        if size < min_words or len(words) < size:
            continue
        for i in range(0, len(words) - size + 1):
            phrase = ' '.join(words[i:i + size]).strip()
            if not phrase:
                continue
            if question and phrase in question:
                continue
            if phrase in source:
                return True

    return False


def build_safe_homework_first_guidance(
        current_question: str,
        source_text: str,
        child_gender: str | None = None,
        force_step_by_step: bool = False
) -> str:
    q = str(current_question or '').strip()
    female = str(child_gender or '').strip().lower() in ('female', 'f', 'נקבה')

    if force_step_by_step:
        if female:
            return (
                "אני אסביר לך שלב־שלב איך עונים על השאלה הזאת.\n\n"
                f"שלב 1 — קוראות את השאלה: {q}\n"
                "אנחנו בודקות על מי מדברים ומה בדיוק מבקשים לדעת.\n\n"
                "שלב 2 — חוזרות לטקסט: מחפשות את המקום שבו מופיעה הדמות מהשאלה.\n\n"
                "שלב 3 — מוצאות את המידע: מחפשות באותו חלק את הפעולה או העובדה שעונה לשאלה.\n\n"
                "שלב 4 — בונות תשובה: מחברות את מה שמצאנו למשפט קצר וברור.\n\n"
                "עכשיו מתחילות בשלב 1 בלבד: על מי מדברת השאלה ומה אנחנו צריכות לגלות עליו?"
            )
        return (
            "אני אסביר לך שלב־שלב איך עונים על השאלה הזאת.\n\n"
            f"שלב 1 — קוראים את השאלה: {q}\n"
            "אנחנו בודקים על מי מדברים ומה בדיוק מבקשים לדעת.\n\n"
            "שלב 2 — חוזרים לטקסט: מחפשים את המקום שבו מופיעה הדמות מהשאלה.\n\n"
            "שלב 3 — מוצאים את המידע: מחפשים באותו חלק את הפעולה או העובדה שעונה לשאלה.\n\n"
            "שלב 4 — בונים תשובה: מחברים את מה שמצאנו למשפט קצר וברור.\n\n"
            "עכשיו מתחילים בשלב 1 בלבד: על מי מדברת השאלה ומה אנחנו צריכים לגלות עליו?"
        )

    if source_text:
        if female:
            return (
                f"בואי נפתור את זה בלי לגלות את התשובה. "
                f"כששואלים: {q} אנחנו מחפשות בטקסט את הפעולות או העובדות שעונות בדיוק על השאלה. "
                f"חפשי במשפט שבו מתחיל התיאור של מה שקרה. מה הדבר הראשון שאת מוצאת שם?"
            )
        return (
            f"בוא נפתור את זה בלי לגלות את התשובה. "
            f"כששואלים: {q} אנחנו מחפשים בטקסט את הפעולות או העובדות שעונות בדיוק על השאלה. "
            f"חפש במשפט שבו מתחיל התיאור של מה שקרה. מה הדבר הראשון שאתה מוצא שם?"
        )

    if female:
        return (
            f"בואי נפתור את זה שלב־שלב בלי לגלות את התשובה. "
            f"השאלה היא: {q} מה הצעד הראשון שצריך לעשות כדי לענות עליה?"
        )
    return (
        f"בוא נפתור את זה שלב־שלב בלי לגלות את התשובה. "
        f"השאלה היא: {q} מה הצעד הראשון שצריך לעשות כדי לענות עליה?"
    )


class HomeworkTurnEvaluation(BaseModel):
    completed_step: str | None = None
    next_step: str | None = None
    answer_sufficient: bool
    feedback: str
    teacher_response: str


@app.post("/api/tutor/openai-clean-chat")
async def openai_clean_chat(
        req: OpenAICleanChatRequest,
        authorization: str = Header(None)
):
    user = authenticate_user(authorization)
    child = {}
    if req.kid_id:
        try:
            child = get_child_by_id(user.id, req.kid_id) or {}
        except Exception as e:
            print("CLEAN CHAT: child lookup failed, neutral Hebrew:", repr(e)[:120])
    system_prompt = (
        hebrew_child_prompt_block(child) + "\n"
        "את מורה פרטית מצוינת לילדים. "
        "עזרי לילד להבין ולפתור את המשימה בעצמו. "
        "לפני השאלה הסבירי במשפט קצר מה מבקשים ואיך ניגשים אליה. "
        "בכל תגובה הציגי רק צעד אחד ברור, הסבירי אותו בקצרה, ואז שאלי שאלה קצרה אחת בלבד. "
        "אחרי השאלה עצרי וחכי לתשובת הילד; אל תציגי את הצעדים הבאים ואל תפתרי את יתר הדף. "
        "אל תעתיקי את כל דף העבודה ואל תתני רשימה של כל השאלות או התשובות. "
        "אם יש בתמונה כמה משימות, התחילי רק מהמשימה הראשונה שעדיין לא נפתרה. "
        "בתגובה הראשונה לתמונה צייני בקצרה מה הנושא שזיהית, הסבירי את הצעד הראשון ושאלי שאלה אחת. "
        "שמרי כל תגובה קצרה, ברורה ומתאימה לילד. אל תתני את התשובה הסופית לפני שהילד ניסה. "
        "אם הילד העלה תמונה, קראי אותה בעצמך והשתמשי בה כמקור הראשי. "
        "התנהגי כמו מורה פרטית טבעית וחכמה, לא כמו שאלון."
    )

    messages=[{"role":"system","content":system_prompt}]
    for item in (req.history or [])[-16:]:
        role=str(item.get("role") or "")
        content=str(item.get("content") or "").strip()
        if role in ("user","assistant") and content:
            messages.append({"role":role,"content":content})

    user_parts=[]
    if str(req.message or "").strip():
        user_parts.append({"type":"text","text":str(req.message).strip()})
    elif req.image_url:
        user_parts.append({"type":"text","text":"תסתכלי על דף העבודה ותעזרי לי להבין איך לפתור אותו שלב אחרי שלב."})
    if str(req.image_url or "").strip():
        user_parts.append({"type":"image_url","image_url":{"url":str(req.image_url).strip(),"detail":"high"}})
    if not user_parts:
        user_parts.append({"type":"text","text":"היי"})
    messages.append({"role":"user","content":user_parts})

    response=await aclient.chat.completions.create(
        model="gpt-5.6-sol",
        messages=messages
    )
    text=str(response.choices[0].message.content or "").strip()
    return {"reply":text,"model":"gpt-5.6-sol","openai_only":True}


@app.post("/api/tutor/homework-coach-v2")
async def homework_coach_v2(
        req: HomeworkCoachRequest,
        authorization: str = Header(None)
):
    user = authenticate_user(authorization)
    child = get_child_by_id(user.id, req.kid_id)
    grade = child.get("grade") if isinstance(child, dict) else None
    system_prompt = (
        hebrew_child_prompt_block(child) + "\n"
        "את מורה פרטית מצוינת לילדים. "
        "המטרה שלך היא לעזור לילד להבין ולפתור את שיעורי הבית בעצמו. "
        "קודם הסתכלי על המשימה והביני מה השאלה מבקשת. "
        "הסבירי לילד בקצרה ובמילים פשוטות מה צריך לעשות ואיך ניגשים לשאלה. "
        "אחר כך למדי אותו שלב אחרי שלב. "
        "בכל הודעה הסבירי רק צעד אחד ברור, הסבירי למה עושים את הצעד הזה, שאלי שאלה קצרה אחת וחכי לתשובת הילד. "
        "אל תתני את התשובה הסופית לפני שהילד ניסה להגיע אליה בעצמו. "
        "אם הילד מתקשה, הסבירי שוב בדרך פשוטה יותר או תני רמז קטן. "
        "אם הילד כבר אמר משהו נכון, זכרי אותו ואל תשאלי עליו שוב. "
        "כשהילד כבר אסף מספיק מידע או ביצע את כל השלבים, בקשי ממנו לנסח או לפתור את התשובה בעצמו. "
        "רק אחרי שהוא ענה, בדקי את התשובה ועזרי לתקן אם צריך. "
        "התאימי את ההסבר לגיל הילד ולסוג המשימה. "
        "התנהגי כמו מורה פרטית אמיתית, לא כמו שאלון."
    )

    # V2 deliberately mirrors a clean ChatGPT conversation:
    # short tutor prompt + original worksheet image + clean per-session history.
    # Do NOT inject OCR, extracted question state, legacy strategies or guards here.
    worksheet_content = [{
        "type": "text",
        "text": (
            f"כיתה: {grade or 'לא ידוע'}\n"
            "זה דף העבודה של הילד. למדי אותו לפתור את שיעורי הבית בעצמו לפי ההוראות שלך. "
            "התחילי מהמשימה הראשונה שעדיין לא נפתרה בתמונה, והתקדמי איתו באופן טבעי שלב אחרי שלב."
        )
    }]
    image_url = str(req.image_url or "").strip()
    if image_url:
        worksheet_content.append({
            "type": "image_url",
            "image_url": {"url": image_url, "detail": "high"}
        })

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": worksheet_content},
    ]
    for item in (req.history or [])[-12:]:
        role = str(item.get("role") or "")
        content = str(item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    if req.message.strip():
        messages.append({"role": "user", "content": req.message.strip()})
    else:
        messages.append({"role": "user", "content": "תתחילי ללמד אותי ולעזור לי לפתור את השאלה הזאת."})

    response = await aclient.chat.completions.create(
        model="gpt-5.6-sol",
        messages=messages,
    )
    text = str(response.choices[0].message.content or "").strip()
    return {"reply": text, "model": "gpt-5.6-sol", "v2": True}


@app.post("/api/tutor/homework-coach")
async def homework_coach(
        req: HomeworkCoachRequest,
        authorization: str = Header(None)
):
    user = (await run_in_threadpool(lambda: authenticate_user(authorization)))
    ai_context("homework", user, req)
    child = (await run_in_threadpool(lambda: get_child_by_id(user.id, req.kid_id)))
    grade = child.get("grade") if isinstance(child, dict) else None

    system_prompt = (
        hebrew_child_prompt_block(child) + "\n"
        "את מורה פרטית מצוינת לילדים. המטרה שלך היא ללמד את הילד להבין ולפתור את שיעורי הבית בעצמו, בכל מקצוע ובכל סוג משימה. "
        "קודם הביני בשקט מה סוג המשימה: מתמטיקה, הבנת הנקרא, כתיבה, שפה, אנגלית, מדעים, גאוגרפיה, היסטוריה או תחום אחר; ומה בדיוק השאלה מבקשת. אל תציגי לילד ניתוח פנימי או סיווגים. "
        "יש בכל רגע שאלה פעילה אחת בלבד: השאלה שנשלחה בשדה השאלה הפעילה. אסור לעבור לשאלה אחרת, גם אם חומר המקור כולל שאלות נוספות. "
        "בכל תגובה שלך עשי בדיוק את הרצף הבא: 1) הסבירי בקצרה מה עושים עכשיו ולמה; 2) התייחסי למה שהילד כבר עשה או מצא; 3) תני רק צעד אחד הבא; 4) שאלי שאלה קצרה אחת בלבד וחכי לתשובה. "
        "את מורה שמסבירה, לא חוקרת. אל תסתפקי במחמאה או בשאלה. לפני כל שאלה לילד חייב להיות הסבר קצר שמלמד אותו איך להתקדם. "
        "אם הילד נתן תשובת ביניים נכונה, הסבירי מה בדיוק הוא מצא ולמה זה עוזר לשאלה הפעילה, ואז הסבירי מה עדיין חסר ושאלי רק על הצעד הבא. "
        "אל תשאלי שאלות כלליות, פילוסופיות, רגשיות או שאלות 'מה לדעתך' אלא אם השאלה הפעילה עצמה דורשת דעה, הסבר, נימוק או פרשנות. "
        "אל תמציאי משמעות שלא כתובה בחומר. בשאלות עובדתיות היצמדי לעובדות, לנתונים, לטקסט או לכלל הרלוונטי. "
        "במתמטיקה: הסבירי מה נתון ומה מחפשים, בחרי עם הילד את הפעולה או הכלל המתאים, פתרי איתו צעד אחד בכל פעם, ואל תגלי את התוצאה הסופית לפני שניסה. "
        "בהבנת הנקרא: הסבירי מה השאלה מבקשת, עזרי למצוא ראיות או פרטים בטקסט, חברי עם הילד את הפרטים, ורק אז בקשי ממנו לנסח תשובה בעצמו. אל תעברי לפרשנות אם לא התבקש. "
        "באנגלית או בשפה: הסבירי בקצרה את המילה, הכלל או המבנה, תני דוגמה דומה שאינה פותרת את המשימה, ואז בקשי מהילד לנסות בעצמו. "
        "במדעים, גאוגרפיה, היסטוריה ומקצועות ידע: הסבירי את המושג או הקשר הדרוש במילים פשוטות, קשרי אותו לחומר הנתון, ואז הובילי את הילד ליישם אותו על השאלה. "
        "בכתיבה: הסבירי מה צריך לכתוב, עזרי לבנות מבנה או רעיונות, ואז תני לילד לנסח. אל תכתבי במקומו תשובה מלאה מראש. "
        "אם הילד טועה, אל תגידי מיד את התשובה. הסבירי מה לא מסתדר, תני רמז קטן יותר או פרקי את הצעד, ואז בקשי ניסיון נוסף. "
        "אם הילד אומר שאינו יודע, אל תחזרי על אותה שאלה. הסבירי מחדש בפשטות, תני רמז או דוגמה מקבילה, ואז שאלי שאלה קלה יותר שמקדמת אותו. "
        "שמרי כל דבר נכון שהילד כבר מצא ואל תחזרי אחורה. אל תגרמי לו לענות שוב על מידע שכבר נתן. "
        "כאשר כבר יש לילד מספיק ידע או פרטים כדי לענות, אמרי זאת במפורש ובקשי ממנו לפתור, לחשב או לנסח את התשובה בעצמו. "
        "רק אחרי שהילד עצמו נתן תשובה מלאה ומספקת לשאלה הפעילה, אשרי בקצרה וסיימי את השאלה. "
        "התאימי את אורך ההסבר, המילים וקושי הצעדים לגיל ולכיתה. העדיפי עברית פשוטה, טבעית וקצרה. "
        "כל תגובה חייבת להתחיל בסמן פנימי אחד בלבד: [[CONTINUE]] אם עדיין חסר מידע, תרגול או ניסוח של הילד; [[COMPLETE]] רק אם הילד עצמו כבר נתן תשובה מלאה ומספקת לשאלה הפעילה. "
        "תשובת ביניים נכונה, פרט בודד, חישוב חלקי או מילה אחת לעולם אינם COMPLETE אם עדיין צריך לבנות תשובה מלאה. "
        "במצב CONTINUE חובה להמשיך ללמד: הסבר קצר ואז שאלה אחת שמקדמת לצעד הבא. במצב COMPLETE אשרי בקצרה בלבד ואל תשאלי שאלה נוספת."
    )

    context = (
        f"כיתה: {grade or 'לא ידוע'}\n"
        f"השאלה הפעילה היחידה: {req.current_question}\n"
        f"חומר מקור בלבד — אין להתייחס לשאלות אחרות שמופיעות בו:\n<<<SOURCE>>>\n{req.source_text}\n<<<END SOURCE>>>"
    )

    messages = [{"role":"system","content":system_prompt}, {"role":"user","content":context}]
    for item in (req.history or [])[-8:]:
        role = str(item.get("role") or "")
        content = str(item.get("content") or "").strip()
        if role in ("user","assistant") and content:
            messages.append({"role":role,"content":content})
    if req.message.strip():
        messages.append({"role":"user","content":req.message.strip()})
    else:
        messages.append({"role":"user","content":"תלמדי אותי לפתור את השאלה הזאת כמו מורה פרטית. קודם תסבירי לי בקצרה מה השאלה מבקשת ואיך ניגשים אליה. אחר כך תני לי רק את הצעד הראשון, הסבירי מה עושים בו ולמה, ושאלי אותי שאלה קצרה אחת. בכל המשך תשמרי את מה שכבר עשיתי ותעזרי לי להתקדם צעד אחד בכל פעם עד שאוכל לענות בעצמי."})

    response = (await aclient.chat.completions.create(
        model="gpt-5.6-sol",
        messages=messages
    ))
    raw_text = str(response.choices[0].message.content or "").strip()
    state = "complete" if raw_text.startswith("[[COMPLETE]]") else "continue"
    text = re.sub(r"^\s*\[\[(?:CONTINUE|COMPLETE)\]\]\s*", "", raw_text, count=1).strip()
    if state == "continue" and "?" not in text:
        text = (text + "\n\nעכשיו נמשיך לצעד הבא: חפש/י בטקסט את הפעולה הבאה שעוזרת לענות על השאלה. מה מצאת?").strip()
    return {"reply": text, "state": state, "model": "gpt-5.6-sol", "production_mode": True}


@app.post("/api/tutor/homework-turn")
async def homework_turn(
        req: HomeworkTurnRequest,
        authorization: str = Header(None)
):
    user = (await run_in_threadpool(lambda: authenticate_user(authorization)))
    ai_context("homework", user, req)
    child = (await run_in_threadpool(lambda: get_child_by_id(user.id, req.kid_id)))

    child_name = str(child.get("child_name") or "").strip()
    gender, gender_rule = hebrew_gender_rule(child)
    gender_rule = gender_rule + "\n" + HEBREW_WRITING_RULES

    normalized_answer = " ".join(str(req.answer or "").strip().lower().split())
    uncertainty_phrases = {
        "לא יודע", "לא יודעת", "לא יודע/ת", "אין לי מושג", "לא בטוח", "לא בטוחה",
        "לא זוכר", "לא זוכרת", "לא הבנתי", "לא מבין", "לא מבינה"
    }
    is_uncertainty = normalized_answer in uncertainty_phrases or any(
        phrase in normalized_answer for phrase in ["לא יודע", "לא יודעת", "אין לי מושג", "לא זוכר", "לא זוכרת"]
    )

    strategy_name, strategy_instruction = resolve_homework_teaching_strategy(
        req.current_question,
        req.source_text
    )
    style_name, style_instruction = resolve_homework_teaching_style(strategy_name)
    mode_name, mode_instruction = resolve_homework_help_mode(req.help_mode)

    system_prompt = f"""
You are the homework-answer evaluator for IAKIDS.
The child is answering ONE specific worksheet question.

Child name: {child_name}
Gender: {gender}
{gender_rule}

CURRENT WORKSHEET QUESTION:
{req.current_question}

SOURCE MATERIAL / OCR:
{req.source_text}

CHILD ANSWER IS EXPLICIT UNCERTAINTY: {is_uncertainty}

{HOMEWORK_GLOBAL_PEDAGOGY_PROMPT}

ACTIVE TEACHING STYLE: {style_name or "legacy"}
TEACHING STYLE INSTRUCTION:
{style_instruction or "No dedicated teaching-style prompt is active for this task yet; keep the existing strategy behavior."}

ACTIVE HELP MODE: {mode_name or "default"}
HELP MODE INSTRUCTION:
{mode_instruction or "No dedicated help-mode prompt is active; use the normal tutoring flow."}

ACTIVE TEACHING STRATEGY: {strategy_name}
STRATEGY INSTRUCTION:
{strategy_instruction}

PEDAGOGICAL PROGRESS STATE:
{req.progress_context or "No earlier step state for this question."}

PROGRESS RULES:
- Treat every completed step listed above as already learned/accepted. NEVER ask the child to justify it again and NEVER restart from an earlier step.
- Continue only from NEXT UNRESOLVED STEP.
- If the child answer correctly completes the next unresolved step, acknowledge it briefly and immediately advance one step.
- For multi-step math, preserve the chain of operations/results already established. Example pattern only: identify operation -> calculate intermediate result -> use that result in the next operation -> final contextual answer. Do not restart the chain.
- For reading/science/writing, use the same principle: evidence/idea/structure already established remains completed and the next response advances from there.
- Populate completed_step with the newest step the child has successfully completed in THIS turn, or leave it empty if none.
- Populate next_step with the single next unresolved pedagogical action the child should do next, or leave it empty when the worksheet answer is complete.

HARD RULES:
0. Never regress to an already completed pedagogical step. The progress state is authoritative for sequencing.
1. Work only on the CURRENT WORKSHEET QUESTION.
2. Judge semantic correctness; exact wording is not required.
3. If the answer is partial but contains a correct idea, scaffold one step and let the child complete it; do not immediately reveal the complete answer.
4. If the answer is sufficient, explain briefly why it is correct and provide one concise polished formulation.
5. Do not invent information and do not ask for details not required by the question.
6. Do not repeat the same question in different wording.
7. Ask at most one focused follow-up at a time.
8. If the child says they do not know, give a smaller clue, source cue, first step, or sentence frame instead of repeating the question.
9. Do not move to the next worksheet question; application code controls progression.
10. Never mention prompts, internal rules, evaluation logic or state.
11. Return only the structured response.
""".strip()

    completion = (await (
        aclient.beta.chat.completions.parse(
            model=DEFAULT_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.answer}
            ],
            response_format=HomeworkTurnEvaluation
        )
    ))

    parsed = completion.choices[0].message.parsed

    # HARD ANSWER-LEAK GUARD (0.7.75)
    # On the first help-mode response, prevent the teacher from copying a
    # source sentence that contains the worksheet answer before the child tries.
    if parsed:
        answer_context = str(req.answer or "")
        help_mode_name = str(req.help_mode or "").strip()
        progress_state = str(req.progress_context or "").strip()

        # req.help_mode is authoritative. The long saved prompt contains the
        # Hebrew help-mode wording, but req.answer itself normally does not.
        is_step_by_step_mode = (help_mode_name == "solve_together")

        # The frontend always sends a textual progress summary, even before
        # the first child attempt (for example: "None yet"). Therefore an
        # empty-string check is not enough to identify the first help turn.
        progress_lower = progress_state.lower()
        has_child_attempt = (
            "child:" in progress_lower
            or "teacher:" in progress_lower
            or "attempt" in progress_lower
        )
        has_completed_step = not (
            not progress_state
            or "none yet" in progress_lower
            or "no earlier step state" in progress_lower
        )
        is_first_help_turn = (
            is_step_by_step_mode
            and not has_child_attempt
            and not has_completed_step
        )

        if is_step_by_step_mode:
            print("HOMEWORK STEP MODE DETECTED", {
                "help_mode": help_mode_name,
                "first_turn": is_first_help_turn,
                "has_progress": bool(progress_state)
            })

        # STRICT STEP-BY-STEP ENTRY (0.7.77)
        # If the child explicitly chose step-by-step help, the first teacher
        # response is deterministic: explain the method, name the steps, and
        # begin with step 1. Do not depend on the model remembering the format.
        if is_first_help_turn and is_step_by_step_mode:
            parsed.teacher_response = build_safe_homework_first_guidance(
                req.current_question,
                req.source_text,
                child.get("gender") if isinstance(child, dict) else None,
                force_step_by_step=True
            )
            parsed.feedback = ""
            parsed.answer_sufficient = False
            parsed.completed_step = None
            parsed.next_step = "שלב 1 — להבין מה השאלה מבקשת"

        elif is_first_help_turn and homework_response_leaks_source_answer(
                parsed.teacher_response,
                req.source_text,
                req.current_question
        ):
            print("HOMEWORK ANSWER LEAK GUARD TRIGGERED", {
                "question": req.current_question,
                "teacher_response": parsed.teacher_response
            })
            parsed.teacher_response = build_safe_homework_first_guidance(
                req.current_question,
                req.source_text,
                child.get("gender") if isinstance(child, dict) else None
            )
            parsed.feedback = ""
            parsed.answer_sufficient = False
            parsed.completed_step = None
    if not parsed:
        raise HTTPException(status_code=502, detail="Invalid homework evaluation")

    result = parsed.model_dump()

    # =====================================================
    # HOMEWORK SESSION PROGRESS
    # =====================================================
    if req.homework_session_id:
        try:
            existing_hw = (await run_in_threadpool(lambda: (
                sb.table("homework_sessions")
                .select("id,user_id,kid_id,total_questions,completed_questions,status")
                .eq("id", req.homework_session_id)
                .eq("user_id", user.id)
                .eq("kid_id", req.kid_id)
                .limit(1)
                .execute()
            )))

            if existing_hw.data:
                hw = existing_hw.data[0]
                now_iso = datetime.now(timezone.utc).isoformat()
                update_payload = {
                    "last_activity_at": now_iso,
                    "updated_at": now_iso
                }

                if result.get("answer_sufficient"):
                    previous_completed = int(hw.get("completed_questions") or 0)
                    completed_now = max(previous_completed, int(req.current_question_number or 0))
                    total_questions = int(hw.get("total_questions") or 0)

                    # If the client knows there is no next question, the worksheet is complete.
                    is_complete = not bool(req.next_question)
                    if total_questions > 0:
                        completed_now = min(total_questions, completed_now)
                        is_complete = is_complete or completed_now >= total_questions

                    update_payload["completed_questions"] = completed_now
                    if is_complete:
                        update_payload["status"] = "completed"
                        update_payload["completed_at"] = now_iso

                if req.session_id:
                    update_payload["tutor_session_id"] = req.session_id

                (await run_in_threadpool(lambda: supabase_with_retry(
                    lambda: (
                        sb.table("homework_sessions")
                        .update(update_payload)
                        .eq("id", req.homework_session_id)
                        .eq("user_id", user.id)
                        .eq("kid_id", req.kid_id)
                        .execute()
                    ),
                    label="HOMEWORK SESSION UPDATE"
                )))
        except Exception as hw_error:
            print("HOMEWORK SESSION PROGRESS WARNING:", repr(hw_error))

    session = (await run_in_threadpool(lambda: get_or_create_tutor_session(user.id, req.kid_id)))
    session_id = session.get("id")

    # Save the actual child/teacher exchange. If answer is sufficient, include
    # the deterministic next worksheet question in the saved transcript too.
    assistant_content = str(result.get("teacher_response") or result.get("feedback") or "").strip()
    if result.get("answer_sufficient"):
        if req.next_question:
            assistant_content += (
                f"\n\nנעבור לשאלה {req.next_question_number or ''}: {req.next_question}"
            ).strip()
        else:
            assistant_content += "\n\nסיימנו את כל השאלות בדף. כל הכבוד!"

    usage = getattr(completion, "usage", None)
    input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
    cost_usd = calculate_openai_cost(
        DEFAULT_OPENAI_MODEL,
        input_tokens=input_tokens,
        output_tokens=output_tokens
    )

    (await run_in_threadpool(lambda: save_tutor_chat_messages(
        user_id=user.id,
        kid_id=req.kid_id,
        user_content=req.answer,
        assistant_content=assistant_content,
        assistant_tokens=output_tokens,
        session_id=session_id
    )))

    (await run_in_threadpool(lambda: update_tutor_session_after_chat(
        session=session,
        total_tokens=total_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd
    )))

    return {
        **result,
        "session_id": session_id,
        "current_question_number": req.current_question_number,
        "next_question_number": req.next_question_number
    }


# =====================================================
# ADMIN — LESSON REVIEW (2026-09-16)
#
# Server-side allowlist (ADMIN_EMAILS env, comma separated). The page at
# /he/admin/lessons-review/ only calls these routes with the parent's Supabase
# token; nothing here is reachable without an allowlisted email.
# =====================================================
ADMIN_EMAILS = {
    e.strip().lower() for e in os.getenv(
        "ADMIN_EMAILS",
        "varonrot@gmail.com,office@calzo-app.com,yossi.heine@gmail.com,yossi.hina@gmail.com,yossiheine.biz@gmail.com"
    ).split(",") if e.strip()
}


def require_admin(authorization: str | None):
    user = authenticate_user(authorization)
    email = str(getattr(user, "email", "") or "").lower()
    if email not in ADMIN_EMAILS:
        print("ADMIN DENIED:", {"email": email})
        raise HTTPException(status_code=403, detail="admin only")
    return user


def _lesson_review_row(r: dict, parents: dict) -> dict:
    g = r.get("generated_lesson_json") or {}
    q = g.get("quality") or {}
    parent = parents.get(r.get("learning_lesson_id")) or {}
    return {
        "id": r["id"], "unit_name": r.get("unit_name"), "lesson_name": r.get("lesson_name"),
        "grade": parent.get("grade"), "subject": parent.get("subject"), "topic": parent.get("lesson_name"),
        "generation_status": r.get("generation_status"), "audio_generation_status": r.get("audio_generation_status"),
        "content_version": r.get("content_version"), "generated_at": r.get("generated_at"),
        "quality": {
            "checked": bool(q), "ok": q.get("ok"), "errors": q.get("errors") or [], "warnings": q.get("warnings") or [],
            "stats": q.get("stats") or {}, "checked_at": q.get("checked_at"),
            "approved_by_human": bool(q.get("approved_by_human")), "approved_by": q.get("approved_by"), "approved_at": q.get("approved_at"),
            "note": q.get("review_note"),
        },
    }


@app.get("/api/admin/lessons/quality")
async def admin_lessons_quality(authorization: str = Header(None)):
    await run_in_threadpool(lambda: require_admin(authorization))
    rows = await run_in_threadpool(lambda: sb.table("lesson_units_content").select(
        "id,unit_name,lesson_name,learning_lesson_id,generation_status,audio_generation_status,content_version,generated_at,generated_lesson_json"
    ).order("id").execute().data)
    parent_ids = sorted({r.get("learning_lesson_id") for r in rows if r.get("learning_lesson_id")})
    parents = {}
    if parent_ids:
        pl = await run_in_threadpool(lambda: sb.table("learning_lessons").select("id,grade,subject,lesson_name").in_("id", parent_ids).execute().data)
        parents = {p["id"]: p for p in pl}
    out = [_lesson_review_row(r, parents) for r in rows]
    flagged = [x for x in out if x["quality"]["checked"] and x["quality"]["ok"] is False and not x["quality"]["approved_by_human"]]
    return {"success": True, "count": len(out), "flagged": len(flagged),
            "generated": sum(1 for x in out if x["generation_status"] == "ready"), "lessons": out}


class AdminLessonNote(BaseModel):
    note: str | None = None


@app.post("/api/admin/lessons/{unit_lesson_id}/approve")
async def admin_lesson_approve(unit_lesson_id: int, body: AdminLessonNote = None, authorization: str = Header(None)):
    user = await run_in_threadpool(lambda: require_admin(authorization))
    row = await run_in_threadpool(lambda: get_unit_lesson(unit_lesson_id))
    g = dict(row.get("generated_lesson_json") or {})
    q = dict(g.get("quality") or {})
    q.update({"approved_by_human": True, "approved_by": user.email, "approved_at": datetime.now(timezone.utc).isoformat(),
              "review_note": (body.note if body else None) or q.get("review_note")})
    g["quality"] = q
    await run_in_threadpool(lambda: sb.table("lesson_units_content").update({"generated_lesson_json": g}).eq("id", unit_lesson_id).execute())
    print("ADMIN LESSON APPROVED:", {"unit_lesson_id": unit_lesson_id, "by": user.email})
    return {"success": True, "quality": q}


@app.post("/api/admin/lessons/{unit_lesson_id}/recheck")
async def admin_lesson_recheck(unit_lesson_id: int, authorization: str = Header(None)):
    await run_in_threadpool(lambda: require_admin(authorization))
    report = await run_in_threadpool(lambda: run_lesson_quality_gate(unit_lesson_id, check_images=True))
    return {"success": True, "quality": report}


@app.post("/api/admin/lessons/{unit_lesson_id}/regenerate")
async def admin_lesson_regenerate(unit_lesson_id: int, authorization: str = Header(None)):
    """Wipe media + generated content (same as tools/delete_unit_lesson.py) so the next open
    rebuilds the lesson with the current prompts. content_version is bumped."""
    user = await run_in_threadpool(lambda: require_admin(authorization))
    def wipe():
        row = get_unit_lesson(unit_lesson_id)
        removed = {}
        for bucket in (LESSON_MEDIA_BUCKET, LESSON_AUDIO_BUCKET):
            paths = _list_storage_prefix(bucket, f"unit_lessons/{unit_lesson_id}")
            for i in range(0, len(paths), 100):
                sb.storage.from_(bucket).remove(paths[i:i + 100])
            removed[bucket] = len(paths)
        jobs = sb.table("media_jobs").select("id,status").eq("payload->>unit_lesson_id", str(unit_lesson_id)).execute().data
        for j in jobs:
            if j["status"] != "running":
                sb.table("media_jobs").delete().eq("id", j["id"]).execute()
        new_cv = int(row.get("content_version") or 1) + 1
        sb.table("lesson_units_content").update({
            "generation_status": "empty", "status": "empty", "generated_lesson_json": None, "lesson_audio_json": None,
            "lesson_content_json": None, "audio_generation_status": "pending", "audio_generation_error": None,
            "audio_generated_at": None, "audio_mode": None, "generation_error": None, "generation_started_at": None,
            "generation_completed_at": None, "generated_at": None, "tts_generated_at": None, "model_name": None,
            "prompt_version": None, "content_version": new_cv, "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", unit_lesson_id).execute()
        return {"removed": removed, "jobs_deleted": len([j for j in jobs if j["status"] != "running"]), "content_version": new_cv}
    result = await run_in_threadpool(wipe)
    print("ADMIN LESSON REGENERATE (wiped):", {"unit_lesson_id": unit_lesson_id, "by": user.email, **result})
    return {"success": True, **result}


class AdminImageAction(BaseModel):
    path: str          # e.g. "v1/part_2/visual_9.png" or "hero_v1.png"


def _recompute_quality_after_override(q: dict, path: str) -> dict:
    q = dict(q)
    q["errors"] = [e for e in (q.get("errors") or []) if f"image {path}:" not in e]
    imgs = dict(q.get("images") or {})
    if path in imgs:
        imgs[path] = dict(imgs[path], verdict="approved_by_human")
    q["images"] = imgs
    q["ok"] = not q["errors"]
    return q


@app.post("/api/admin/lessons/{unit_lesson_id}/images/approve")
async def admin_image_approve(unit_lesson_id: int, body: AdminImageAction, authorization: str = Header(None)):
    """A human looked at the image and it is fine: the vision verdict is overridden for this file."""
    user = await run_in_threadpool(lambda: require_admin(authorization))
    row = await run_in_threadpool(lambda: get_unit_lesson(unit_lesson_id))
    g = dict(row.get("generated_lesson_json") or {}); q = dict(g.get("quality") or {})
    ov = dict(q.get("image_overrides") or {}); ov[body.path] = {"by": user.email, "at": datetime.now(timezone.utc).isoformat()}
    q["image_overrides"] = ov
    q = _recompute_quality_after_override(q, body.path)
    g["quality"] = q
    await run_in_threadpool(lambda: sb.table("lesson_units_content").update({"generated_lesson_json": g}).eq("id", unit_lesson_id).execute())
    print("ADMIN IMAGE APPROVED:", {"unit_lesson_id": unit_lesson_id, "path": body.path, "by": user.email})
    return {"success": True, "quality": q}


@app.post("/api/admin/lessons/{unit_lesson_id}/images/regenerate")
async def admin_image_regenerate(unit_lesson_id: int, body: AdminImageAction, authorization: str = Header(None)):
    """Delete ONE image; a visuals job (or the hero route on next open) recreates just the missing file."""
    user = await run_in_threadpool(lambda: require_admin(authorization))
    row = await run_in_threadpool(lambda: get_unit_lesson(unit_lesson_id))
    full = f"unit_lessons/{unit_lesson_id}/{body.path}"
    def do():
        sb.storage.from_(LESSON_MEDIA_BUCKET).remove([full])
        job_id = None
        if not body.path.startswith("hero_"):
            job_id = enqueue_media_job("unit_lesson_visuals", {"unit_lesson_id": unit_lesson_id},
                                       dedupe_key=f"unit_lesson_visuals:{unit_lesson_id}", priority=5)
        g = dict(row.get("generated_lesson_json") or {}); q = dict(g.get("quality") or {})
        imgs = dict(q.get("images") or {})
        if body.path in imgs:
            imgs[body.path] = dict(imgs[body.path], verdict="regenerating")
        q["images"] = imgs; g["quality"] = q
        sb.table("lesson_units_content").update({"generated_lesson_json": g}).eq("id", unit_lesson_id).execute()
        return job_id
    job_id = await run_in_threadpool(do)
    print("ADMIN IMAGE REGENERATE:", {"unit_lesson_id": unit_lesson_id, "path": body.path, "job_id": job_id, "by": user.email})
    return {"success": True, "job_id": job_id, "note": "hero is recreated on the next lesson open" if body.path.startswith("hero_") else "visuals job queued"}


@app.get("/api/admin/lessons/{unit_lesson_id}/media")
async def admin_lesson_media(unit_lesson_id: int, authorization: str = Header(None)):
    """Signed URLs of the hero and every visual of the current content_version, with the
    text-check verdicts from the last quality report, so a human can look at them."""
    await run_in_threadpool(lambda: require_admin(authorization))
    row = await run_in_threadpool(lambda: get_unit_lesson(unit_lesson_id))
    cv = int(row.get("content_version") or 1)
    q = ((row.get("generated_lesson_json") or {}).get("quality") or {})
    flagged = {}
    for e in q.get("errors") or []:
        m = re.search(r"readable text in image (\S+): '(.*)'", e)
        if m:
            flagged[m.group(1)] = m.group(2)
    paths = await run_in_threadpool(lambda: _list_storage_prefix(LESSON_MEDIA_BUCKET, f"unit_lessons/{unit_lesson_id}"))
    paths = sorted(p for p in paths if p.endswith(".png") and (f"/v{cv}/" in p or "/hero_v" in p))
    urls = await run_in_threadpool(lambda: signed_urls_cached_batch(LESSON_MEDIA_BUCKET, paths, LESSON_MEDIA_URL_EXPIRY_SECONDS))
    verdicts = q.get("images") or {}
    items = []
    for p in paths:
        key = p.split(f"unit_lessons/{unit_lesson_id}/", 1)[-1]
        v = verdicts.get(key) or {}
        items.append({"path": key, "url": urls.get(p), "text_found": flagged.get(key) or (v.get("text") if v.get("verdict") in ("text", "possible_text") else None),
                      "verdict": v.get("verdict") or ("text" if key in flagged else ("unchecked" if not verdicts else "clean")),
                      "kind": v.get("kind"), "confidence": v.get("confidence"), "source": v.get("source")})
    parts = (((row.get("generated_lesson_json") or {}).get("structured_lesson") or {}).get("parts") or [])
    text = [{"part_number": p.get("part_number"), "segments": [s.get("text") for s in (p.get("lesson") or []) if isinstance(s, dict)],
             "question": (p.get("question") or {}).get("text")} for p in parts]
    return {"success": True, "content_version": cv, "images": items, "text": text, "quality": q}


# =====================================================
# SPEECH TO TEXT (2026-09-17)
#
# Every chat box in the product has a microphone: the child speaks and the words
# appear in the input instead of typing. The browser's own recognition is used when
# it exists; this route is the fallback (Firefox, old WebViews) and the accurate
# path for children's Hebrew. Audio arrives as base64 in JSON, like the rest of the
# API. Nothing is stored: the clip is transcribed and dropped.
# =====================================================
_stt_openai_client = None


def _get_stt_openai_client():
    """A DIRECT OpenAI client: transcription does not exist on OpenRouter, so the
    shared `client` (which may point at OpenRouter) cannot be used here."""
    global _stt_openai_client
    if _stt_openai_client is None:
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required for speech to text")
        _stt_openai_client = OpenAI(api_key=key)
    return _stt_openai_client


def transcribe_audio_bytes(audio: bytes, mime_type: str = "audio/webm", language: str = "he") -> dict:
    """{'text': str, 'provider': str, 'model': str, 'ms': int}. Raises on failure."""
    t0 = time.perf_counter()
    suffix = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mp4": ".m4a",
              "audio/mpeg": ".mp3", "audio/wav": ".wav", "audio/x-wav": ".wav"}.get(
        (mime_type or "").split(";")[0].strip(), ".webm")
    provider, model, text = STT_PROVIDER, STT_MODEL, ""
    if STT_PROVIDER == "openai":
        buf = io.BytesIO(audio)
        buf.name = f"speech{suffix}"
        try:
            r = _get_stt_openai_client().audio.transcriptions.create(
                model=STT_MODEL, file=buf, language=language,
                prompt="תמלול דיבור של ילד בעברית, בשיעור. כתוב רק את מה שנאמר.")
        except Exception as first_error:
            print("STT MODEL FAILED, TRYING whisper-1:", {"model": STT_MODEL, "error": repr(first_error)[:160]})
            buf.seek(0)
            model = "whisper-1"
            r = _get_stt_openai_client().audio.transcriptions.create(model=model, file=buf, language=language)
        text = str(getattr(r, "text", "") or "").strip()
    else:
        provider, model = "gemini", STT_GEMINI_MODEL
        resp = gemini_client.models.generate_content(
            model=STT_GEMINI_MODEL,
            contents=[types.Part.from_bytes(data=audio, mime_type=(mime_type or "audio/webm").split(";")[0]),
                      "Transcribe this speech verbatim. It is a child speaking Hebrew during a lesson. "
                      "Return ONLY the transcription, no punctuation guesses beyond the obvious, no commentary."],
            config=types.GenerateContentConfig(temperature=0))
        text = str(getattr(resp, "text", "") or "").strip()
    ms = round((time.perf_counter() - t0) * 1000)
    try:
        ai_costs.record(provider, model, purpose="stt", audio_seconds=None, latency_ms=ms,
                        status="ok" if text else "error", error=None if text else "empty transcription",
                        extra={"bytes": len(audio), "mime": mime_type})
    except Exception as e:
        print("AI COSTS RECORD FAILED (stt):", repr(e)[:120])
    return {"text": text, "provider": provider, "model": model, "ms": ms}


class TutorSTTRequest(BaseModel):
    audio_base64: str
    mime_type: str = "audio/webm"
    kid_id: str | None = None
    language: str = "he"


@app.post("/api/tutor/stt")
async def tutor_stt(body: TutorSTTRequest, authorization: str = Header(None)):
    try:
        user = (await run_in_threadpool(lambda: authenticate_user(authorization)))
        ai_context("stt", user, body)
        raw = (body.audio_base64 or "").strip()
        if "," in raw[:120] and raw.lstrip().startswith("data:"):
            raw = raw.split(",", 1)[1]                       # data:audio/webm;base64,....
        try:
            audio = base64.b64decode(raw, validate=False)
        except Exception:
            raise HTTPException(status_code=400, detail="audio_base64 is not valid base64")
        if not audio:
            raise HTTPException(status_code=400, detail="audio is empty")
        if len(audio) > STT_MAX_BYTES:
            raise HTTPException(status_code=413, detail="audio is too long")
        # Identifiers and sizes only: this is a child's own voice.
        print("STT REQUEST:", {"bytes": len(audio), "mime": body.mime_type, "kid_id": (body.kid_id or "")[:8]})
        result = await run_in_threadpool(lambda: transcribe_audio_bytes(audio, body.mime_type, body.language or "he"))
        print("STT DONE:", {"chars": len(result["text"]), "ms": result["ms"], "model": result["model"],
                            **({"text": repr(result["text"])} if not IS_PROD else {})})
        return {"success": bool(result["text"]), "text": result["text"], "model": result["model"], "ms": result["ms"]}
    except HTTPException:
        raise
    except Exception as e:
        print("STT ERROR:", repr(e)[:300])
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"speech to text failed: {e}")
