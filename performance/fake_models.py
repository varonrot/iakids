#!/usr/bin/env python3
"""A stand-in for OpenRouter / OpenAI: answers every model call the tutor makes, at a
measured delay, for free.

    python performance/fake_models.py --port 8792                 # production-like delays
    python performance/fake_models.py --port 8792 --scale 0.1     # 10x faster (to find the server's own limit)

Load-testing the real providers would be a bill, not a measurement, and it would measure
their rate limit rather than this server. The fake:
  * /chat/completions   plain text, or a JSON object built from the request's json_schema
                        (structured outputs), so the tutor's Pydantic parsing succeeds;
                        streaming (stream=true) is answered as SSE chunks
  * /responses          the Responses API, same idea
  * /audio/speech       a short silent PCM/WAV body
  * /audio/transcriptions  a short Hebrew sentence
  * /generation         OpenRouter's cost lookup (so ai_costs does not retry forever)
Delays default to the production medians in docs/PERFORMANCE.md: chat 4.5 s, lesson
model 20 s, TTS 3 s. --scale multiplies them all.
"""
import argparse
import asyncio
import json
import random
import time

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8792)
ap.add_argument("--scale", type=float, default=1.0)
args = ap.parse_args()

# seconds, median; jittered +-30%
DELAY = {"chat": 4.5, "lesson": 20.0, "tts": 3.0, "stt": 1.5, "other": 2.0}
HEBREW = "זה הסבר קצר ופשוט. נסו לחשוב על הדוגמה ולענות במילים שלכם."
CALLS = {"n": 0}


def _delay(kind):
    d = DELAY[kind] * args.scale
    return max(0.0, random.uniform(0.7 * d, 1.3 * d))


def _kind(model: str, body: dict):
    m = (model or "").lower()
    if "5.6" in m or "sol" in m:     # the lesson / planner model: long structured answers
        return "lesson"
    return "chat"


def _from_schema(s, defs, depth=0):
    """A small valid instance of a JSON schema."""
    if depth > 40:
        return None
    if "$ref" in s:
        return _from_schema(defs.get(s["$ref"].split("/")[-1], {}), defs, depth + 1)
    for comb in ("anyOf", "oneOf", "allOf"):
        if comb in s:
            opts = [o for o in s[comb] if o.get("type") != "null"] or s[comb]
            return _from_schema(opts[0], defs, depth + 1)
    if "enum" in s:
        return s["enum"][0]
    if "const" in s:
        return s["const"]
    t = s.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "string")
    if t == "object" or "properties" in s:
        return {k: _from_schema(v, defs, depth + 1) for k, v in (s.get("properties") or {}).items()}
    if t == "array":
        n = max(int(s.get("minItems") or 0), 4)
        items = [_from_schema(s.get("items") or {"type": "string"}, defs, depth + 1) for _ in range(n)]
        # distinct strings: a multiple-choice question needs 4 different options
        return [f"{x} {i + 1}" if isinstance(x, str) else x for i, x in enumerate(items)]
    if t == "integer":
        return int(s.get("minimum") or 1)
    if t == "number":
        return float(s.get("minimum") or 1)
    if t == "boolean":
        return True
    return HEBREW


def _content(body):
    rf = body.get("response_format") or {}
    if rf.get("type") == "json_schema":
        js = rf.get("json_schema") or {}
        schema = js.get("schema") or {}
        return json.dumps(_from_schema(schema, schema.get("$defs") or schema.get("definitions") or {}), ensure_ascii=False)
    if rf.get("type") == "json_object":
        return json.dumps({"reply": HEBREW, "text": HEBREW}, ensure_ascii=False)
    return HEBREW


def _usage():
    return {"prompt_tokens": 1500, "completion_tokens": 300, "total_tokens": 1800}


async def chat(request: Request):
    body = await request.json()
    CALLS["n"] += 1
    await asyncio.sleep(_delay(_kind(body.get("model"), body)))
    content = _content(body)
    cid = f"gen-perf-{CALLS['n']}"
    if body.get("stream"):
        async def gen():
            for i in range(0, len(content), 40):
                chunk = {"id": cid, "object": "chat.completion.chunk", "created": int(time.time()), "model": body.get("model"),
                         "choices": [{"index": 0, "delta": {"content": content[i:i + 40]}, "finish_reason": None}]}
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            done = {"id": cid, "object": "chat.completion.chunk", "created": int(time.time()), "model": body.get("model"),
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}], "usage": _usage()}
            yield f"data: {json.dumps(done)}\n\ndata: [DONE]\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")
    return JSONResponse({
        "id": cid, "object": "chat.completion", "created": int(time.time()), "model": body.get("model"),
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content, "refusal": None}, "finish_reason": "stop"}],
        "usage": _usage(),
    })


async def responses(request: Request):
    body = await request.json()
    CALLS["n"] += 1
    await asyncio.sleep(_delay("chat"))
    fmt = ((body.get("text") or {}).get("format") or {})
    text = _content({"response_format": {"type": "json_schema", "json_schema": {"schema": fmt.get("schema") or {}}}}) \
        if fmt.get("type") == "json_schema" else HEBREW
    return JSONResponse({"id": f"resp-perf-{CALLS['n']}", "object": "response", "created_at": int(time.time()),
                         "model": body.get("model"), "status": "completed",
                         "output": [{"type": "message", "id": "msg1", "role": "assistant", "status": "completed",
                                     "content": [{"type": "output_text", "text": text, "annotations": []}]}],
                         "usage": {"input_tokens": 1500, "output_tokens": 300, "total_tokens": 1800}})


def _wav(seconds=1.0, rate=24000):
    n = int(seconds * rate)
    data = b"\x00\x00" * n
    import struct
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(data)) + data)


async def speech(request: Request):
    body = await request.json()
    CALLS["n"] += 1
    await asyncio.sleep(_delay("tts"))
    fmt = body.get("response_format") or "mp3"
    return Response(_wav(), media_type="audio/wav" if fmt in ("wav", "pcm") else "audio/mpeg")


async def transcribe(request: Request):
    await request.body()
    CALLS["n"] += 1
    await asyncio.sleep(_delay("stt"))
    return JSONResponse({"text": "שלום, אני רוצה לשאול שאלה"})


async def generation(request: Request):
    return JSONResponse({"data": {"id": request.query_params.get("id"), "total_cost": 0.0, "native_tokens_prompt": 1500,
                                  "native_tokens_completion": 300, "model": "fake"}})


async def calls(request: Request):
    return JSONResponse(CALLS)


METHODS = ["POST"]
routes = []
for prefix in ("", "/v1", "/api/v1"):
    routes += [Route(prefix + "/chat/completions", chat, methods=METHODS),
               Route(prefix + "/responses", responses, methods=METHODS),
               Route(prefix + "/audio/speech", speech, methods=METHODS),
               Route(prefix + "/audio/transcriptions", transcribe, methods=METHODS),
               Route(prefix + "/generation", generation, methods=["GET"])]
routes.append(Route("/__calls", calls))
app = Starlette(routes=routes)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning", access_log=False, timeout_keep_alive=120)
