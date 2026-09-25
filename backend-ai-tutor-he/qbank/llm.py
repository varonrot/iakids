"""The model client for the question-bank tools (OpenRouter, the same account as the service).

QBANK_GEN_MODEL    writes items            (default openai/gpt-5.6-sol: Hebrew quality matters more than price)
QBANK_SOLVER_MODEL solves them blind       (default google/gemini-3.1-flash-lite: a different model family, so the
                                             writer's own mistakes are not simply repeated)
The key comes from OPENROUTER_API_KEY in the environment or backend-ai-tutor-he/.env.<APP_ENV>. The account is
shared with production: check /api/v1/credits before a large batch (tools print the spend of every run).
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / f".env.{os.getenv('APP_ENV', 'dev')}")
GEN_MODEL = os.getenv("QBANK_GEN_MODEL", "openai/gpt-5.6-sol")
SOLVER_MODEL = os.getenv("QBANK_SOLVER_MODEL", "google/gemini-3.1-flash-lite")
# $ per million tokens (input, output), for the spend line only; OpenRouter's invoice is the truth
PRICES = {"openai/gpt-5.6-sol": (2.0, 10.0), "google/gemini-3.1-flash-lite": (0.10, 0.40), "openai/gpt-4o-mini": (0.15, 0.60)}

_client = None
SPEND = {"in": 0, "out": 0, "usd": 0.0, "calls": 0}


def client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise SystemExit("OPENROUTER_API_KEY is not set (backend-ai-tutor-he/.env.<APP_ENV>)")
        _client = OpenAI(api_key=key, base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                         default_headers={"HTTP-Referer": "https://iakids.app", "X-Title": "iakids qbank"})
    return _client


def parse(model: str, system: str, user: str, schema):
    """One structured call; returns the parsed pydantic object (or None) and records the spend."""
    r = client().beta.chat.completions.parse(model=model, response_format=schema,
                                             messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    u = r.usage
    if u:
        pin, pout = PRICES.get(model, (2.0, 10.0))
        SPEND["in"] += u.prompt_tokens; SPEND["out"] += u.completion_tokens
        SPEND["usd"] += (u.prompt_tokens * pin + u.completion_tokens * pout) / 1e6
    SPEND["calls"] += 1
    return r.choices[0].message.parsed


def credits_left() -> float | None:
    try:
        import httpx
        d = httpx.get("https://openrouter.ai/api/v1/credits", headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, timeout=10).json()["data"]
        return d["total_credits"] - d["total_usage"]
    except Exception:
        return None
