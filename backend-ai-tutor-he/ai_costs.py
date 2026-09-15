"""One row per AI call, with provider, model, purpose, tokens, seconds and cost.

    tracker = AICostTracker(sb, service="tutor-web", prices=MODEL_PRICING_USD, ...)
    tracker.install(openai_clients=[client, aclient], gemini_client=gemini_client)
    tracker.start()

After install() every call through those clients is recorded automatically:
    OpenAI   chat.completions.create / beta.chat.completions.parse   (sync + async)
    Gemini   models.generate_content, aio.models.generate_content, interactions.create
Direct OpenRouter TTS calls (main.openrouter_tts_pcm*) call tracker.record() themselves.

Who / what the call was for comes from a contextvar set by the route or the worker:
    set_call_context(purpose="chat", user_id=..., kid_id=..., unit_lesson_id=...)
contextvars travel through `await run_in_threadpool` (anyio copies the context) but not
through a bare ThreadPoolExecutor.submit — wrap those with run_in_context().

Cost:
    provider   exact cost from the provider. OpenRouter chat responses carry usage.cost;
               OpenRouter TTS gives a generation id that is looked up later (/generation?id=)
    estimated  tokens × price table (AI_PRICES_JSON env overrides, per 1M tokens), or
               audio seconds × audio tokens/s × price, or images × price per image
    unknown    no price known -> cost_usd null; the daily view counts these so you notice

Rows are buffered and inserted in batches (ai_calls_insert RPC) by a daemon thread; a
failure is printed once a minute and never reaches the caller. AI_COSTS_ENABLED=0 turns it off.
"""
import contextvars
import functools
import inspect
import json
import os
import socket
import threading
import time
from collections import deque

ENABLED = os.getenv("AI_COSTS_ENABLED", "1") not in ("0", "false", "no")
FLUSH_SECONDS = float(os.getenv("AI_COSTS_FLUSH_SECONDS", "5"))
BUFFER_MAX = 5000

CALL_CONTEXT: contextvars.ContextVar = contextvars.ContextVar("iakids_ai_call_context", default=None)


def set_call_context(**fields):
    """Merge fields into the current context (purpose, user_id, kid_id, unit_lesson_id)."""
    cur = dict(CALL_CONTEXT.get() or {})
    cur.update({k: v for k, v in fields.items() if v is not None})
    CALL_CONTEXT.set(cur)
    return cur


def run_in_context(fn, *args, **kwargs):
    """Capture the caller's context NOW and return a no-arg callable that runs fn in it:
        executor.submit(run_in_context(fn, arg))
    (copying inside the pool thread would copy the pool thread's empty context)."""
    ctx = contextvars.copy_context()
    return lambda: ctx.run(fn, *args, **kwargs)


def _purpose_from_model(model: str) -> str:
    m = (model or "").lower()
    if "tts" in m:
        return "tts"
    if "image" in m or "imagen" in m:
        return "image"
    if "omni" in m or "veo" in m or "video" in m:
        return "video"
    return "llm"


class AICostTracker:
    def __init__(self, sb, service: str, instance: str | None = None, prices: dict | None = None,
                 audio_tokens_per_second: float = 25.0, audio_output_price_per_1m: float | None = None,
                 image_prices: dict | None = None, openrouter_api_key: str = "",
                 openrouter_base_url: str = "https://openrouter.ai/api/v1"):
        self.sb = sb
        self.service = service
        self.instance = instance or f"{socket.gethostname()}:{os.getpid()}"
        self.prices = dict(prices or {})                     # model -> {"input": $/1M, "output": $/1M}
        try:
            self.prices.update(json.loads(os.getenv("AI_PRICES_JSON", "{}")))
        except Exception as e:
            print("[ai_costs] AI_PRICES_JSON ignored:", repr(e)[:120])
        self.audio_tokens_per_second = audio_tokens_per_second
        self.audio_output_price_per_1m = audio_output_price_per_1m
        self.image_prices = dict(image_prices or {})         # model -> $ per image
        self.openrouter_api_key = openrouter_api_key
        self.openrouter_base_url = openrouter_base_url.rstrip("/")
        self._buf = deque()
        self._pending_generation_ids = deque()
        self._lock = threading.Lock()
        self._started = False
        self._last_err = 0.0
        self.dropped = 0
        self.recorded = 0

    # ------------------------------------------------------------------ recording
    def estimate(self, provider, model, input_tokens=None, output_tokens=None, audio_seconds=None, images=None):
        """(cost_usd, cost_source) from the price tables, or (None, 'unknown')."""
        base = model.split("/", 1)[1] if "/" in model else model
        price = self.prices.get(model) or self.prices.get(base)
        if price and (input_tokens or output_tokens):
            cost = (int(input_tokens or 0) / 1e6) * float(price.get("input", 0)) + \
                   (int(output_tokens or 0) / 1e6) * float(price.get("output", 0))
            return round(cost, 6), "estimated"
        if audio_seconds and self.audio_output_price_per_1m is not None and "tts" in base:
            tokens = float(audio_seconds) * self.audio_tokens_per_second
            return round(tokens / 1e6 * self.audio_output_price_per_1m, 6), "estimated"
        if images and (self.image_prices.get(model) or self.image_prices.get(base)):
            per = float(self.image_prices.get(model) or self.image_prices.get(base))
            return round(int(images) * per, 6), "estimated"
        return None, "unknown"

    def record(self, provider, model, purpose=None, input_tokens=None, output_tokens=None, cached_tokens=None,
               audio_seconds=None, images=None, latency_ms=None, status="ok", error=None,
               cost_usd=None, cost_source=None, generation_id=None, extra=None):
        if not ENABLED:
            return None
        ctx = CALL_CONTEXT.get() or {}
        if cost_usd is None and cost_source is None:
            cost_usd, cost_source = self.estimate(provider, model, input_tokens, output_tokens, audio_seconds, images)
        row = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
            "service": self.service, "instance": self.instance,
            "provider": provider, "model": model,
            "purpose": purpose or ctx.get("purpose") or _purpose_from_model(model),
            "user_id": ctx.get("user_id"), "kid_id": ctx.get("kid_id"), "unit_lesson_id": ctx.get("unit_lesson_id"),
            "input_tokens": input_tokens, "output_tokens": output_tokens, "cached_tokens": cached_tokens,
            "audio_seconds": round(float(audio_seconds), 2) if audio_seconds is not None else None,
            "images": images, "latency_ms": int(latency_ms) if latency_ms is not None else None,
            "status": status, "error": (error or None) and str(error)[:500],
            "cost_usd": cost_usd, "cost_source": cost_source or ("provider" if cost_usd is not None else "unknown"),
            "generation_id": generation_id, "extra": extra,
        }
        with self._lock:
            if len(self._buf) >= BUFFER_MAX:
                self.dropped += 1
                return row
            self._buf.append(row)
            self.recorded += 1
            if generation_id and cost_source == "pending":
                self._pending_generation_ids.append(generation_id)
        return row

    # ------------------------------------------------------------------ client wrappers
    def install(self, openai_clients=(), gemini_client=None):
        for c in openai_clients:
            provider = "openrouter" if "openrouter" in str(getattr(c, "base_url", "")) else "openai"
            for path in (("chat", "completions", "create"), ("beta", "chat", "completions", "parse")):
                self._wrap(c, path, provider, self._openai_usage)
        if gemini_client is not None:
            self._wrap(gemini_client, ("models", "generate_content"), "gemini", self._gemini_usage)
            self._wrap(gemini_client, ("aio", "models", "generate_content"), "gemini", self._gemini_usage)
            self._wrap(gemini_client, ("interactions", "create"), "gemini", self._gemini_interaction_usage)
        return self

    def _wrap(self, root, path, provider, usage_fn):
        obj = root
        for attr in path[:-1]:
            obj = getattr(obj, attr, None)
            if obj is None:
                return
        name = path[-1]
        orig = getattr(obj, name, None)
        if orig is None or getattr(orig, "_iakids_tracked", False):
            return
        tracker = self

        def _done(kw, result, err, t0):
            model = kw.get("model") or getattr(result, "model", None) or "?"
            fields = {}
            try:
                if result is not None:
                    fields = usage_fn(result) or {}
            except Exception as e:                   # never let accounting break a call
                fields = {"extra": {"usage_parse_error": repr(e)[:120]}}
            tracker.record(provider, str(model), latency_ms=(time.time() - t0) * 1000,
                           status="ok" if err is None else "error", error=err, **fields)

        if inspect.iscoroutinefunction(orig):
            @functools.wraps(orig)
            async def tracked(*a, **kw):
                t0 = time.time()
                try:
                    r = await orig(*a, **kw)
                except Exception as e:
                    _done(kw, None, f"{type(e).__name__}: {str(e)[:200]}", t0); raise
                _done(kw, r, None, t0); return r
        else:
            @functools.wraps(orig)
            def tracked(*a, **kw):
                t0 = time.time()
                try:
                    r = orig(*a, **kw)
                except Exception as e:
                    _done(kw, None, f"{type(e).__name__}: {str(e)[:200]}", t0); raise
                _done(kw, r, None, t0); return r
        tracked._iakids_tracked = True
        setattr(obj, name, tracked)

    @staticmethod
    def _openai_usage(resp):
        u = getattr(resp, "usage", None)
        if u is None:
            return {}
        details = getattr(u, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", None) if details is not None else None
        extra_fields = getattr(u, "model_extra", None) or {}
        cost = extra_fields.get("cost") if isinstance(extra_fields, dict) else None
        if cost is None:
            cost = getattr(u, "cost", None)
        out = {"input_tokens": getattr(u, "prompt_tokens", None), "output_tokens": getattr(u, "completion_tokens", None),
               "cached_tokens": cached}
        if cost is not None:                          # OpenRouter reports the exact charge
            out["cost_usd"] = round(float(cost), 6); out["cost_source"] = "provider"
        return out

    @staticmethod
    def _gemini_usage(resp):
        out = {}
        um = getattr(resp, "usage_metadata", None)
        if um is not None:
            out["input_tokens"] = getattr(um, "prompt_token_count", None)
            out["output_tokens"] = getattr(um, "candidates_token_count", None)
            out["cached_tokens"] = getattr(um, "cached_content_token_count", None)
        audio_bytes = 0; images = 0
        try:
            for cand in (getattr(resp, "candidates", None) or []):
                for part in (getattr(getattr(cand, "content", None), "parts", None) or []):
                    blob = getattr(part, "inline_data", None)
                    if blob is None or not getattr(blob, "data", None):
                        continue
                    mime = str(getattr(blob, "mime_type", "") or "")
                    if mime.startswith("image/"):
                        images += 1
                    else:
                        audio_bytes += len(blob.data)
        except Exception:
            pass
        if audio_bytes:
            out["audio_seconds"] = audio_bytes / (24000 * 2)      # PCM 16-bit mono 24 kHz
        if images:
            out["images"] = images
        return out

    @staticmethod
    def _gemini_interaction_usage(resp):
        um = getattr(resp, "usage", None) or getattr(resp, "usage_metadata", None)
        out = {"extra": {"kind": "interaction"}}
        if um is not None:
            out["input_tokens"] = getattr(um, "prompt_token_count", None) or getattr(um, "input_tokens", None)
            out["output_tokens"] = getattr(um, "candidates_token_count", None) or getattr(um, "output_tokens", None)
        return out

    # ------------------------------------------------------------------ lifecycle
    def start(self):
        if not ENABLED or self._started:
            return self
        self._started = True
        threading.Thread(target=self._loop, name="ai-costs", daemon=True).start()
        return self

    def flush(self):
        with self._lock:
            rows = list(self._buf); self._buf.clear()
        if rows:
            self.sb.rpc("ai_calls_insert", {"p_rows": rows}).execute()
        return len(rows)

    def resolve_pending_costs(self, limit=20):
        """OpenRouter TTS: the exact charge is available a moment later by generation id."""
        if not self.openrouter_api_key:
            return 0
        import httpx
        done = 0
        with self._lock:
            queue_empty = not self._pending_generation_ids
        if queue_empty and time.time() - getattr(self, "_last_db_scan", 0.0) > 60:
            self._last_db_scan = time.time()
            # nothing of our own to resolve: pick up rows any process left pending
            # (a script that exited, a worker that was killed) — the DB is the queue
            try:
                rows = (self.sb.table("ai_calls").select("generation_id")
                        .eq("cost_source", "pending").not_.is_("generation_id", "null")
                        .order("id", desc=True).limit(limit).execute().data or [])
                with self._lock:
                    for r in rows:
                        if r.get("generation_id"):
                            self._pending_generation_ids.append(r["generation_id"])
            except Exception as e:
                self._err("pending rows lookup failed", e)
        for _ in range(limit):
            with self._lock:
                if not self._pending_generation_ids:
                    break
                gid = self._pending_generation_ids.popleft()
            try:
                r = httpx.get(f"{self.openrouter_base_url}/generation", params={"id": gid},
                              headers={"Authorization": f"Bearer {self.openrouter_api_key}"}, timeout=15)
                data = (r.json() or {}).get("data") or {}
                cost = data.get("total_cost")
                if r.status_code == 200 and cost is not None:
                    extra = {k: data.get(k) for k in ("native_tokens_prompt", "native_tokens_completion", "provider_name", "model") if data.get(k) is not None}
                    self.sb.rpc("ai_calls_set_cost", {"p_generation_id": gid, "p_cost_usd": float(cost), "p_extra": extra}).execute()
                    done += 1
                else:                                   # not ready yet: try again next round
                    with self._lock:
                        self._pending_generation_ids.append(gid)
                    break
            except Exception as e:
                with self._lock:
                    self._pending_generation_ids.append(gid)
                self._err("openrouter cost lookup failed", e)
                break
        return done

    def _loop(self):
        while True:
            time.sleep(FLUSH_SECONDS)
            try:
                self.flush()
            except Exception as e:
                self._err("ai_calls flush failed", e)
            try:
                self.resolve_pending_costs()
            except Exception as e:
                self._err("cost resolve failed", e)

    def _err(self, msg, e):
        if time.time() - self._last_err > 60:
            self._last_err = time.time()
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [ai_costs {self.service}] {msg}: {repr(e)[:200]}", flush=True)
