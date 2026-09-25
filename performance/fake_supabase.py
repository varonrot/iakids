#!/usr/bin/env python3
"""A stand-in for Supabase (PostgREST + Auth + Storage), or a counting proxy in front of the real one.

    python performance/fake_supabase.py --port 8791                     # fake, 100 ms per call
    python performance/fake_supabase.py --port 8791 --latency-ms 60
    python performance/fake_supabase.py --port 8791 --proxy https://<ref>.supabase.co   # real DB, counted

Why: the tutor's capacity is decided by what it does around the database, and the only
database with data is production. The fake answers every call the tutor makes with the
measured round-trip delay, so every route (writes included) can be driven to its limit
without touching a child's data. In --proxy mode nothing is faked: calls are forwarded
and only counted and timed.

GET /__stats   calls, per table, and total time, since the last reset
POST /__reset  zero the counters

The fake is deliberately generic: tables are lists of dicts, filters are the PostgREST
operators the SDK emits (eq, neq, gt, gte, lt, lte, in, is, not.is, like, ilike), and an
unknown table is an empty table, not an error. Seed data: fixtures/seed.json
(make_fixtures.py) plus a synthetic test parent and child.
"""
import argparse
import asyncio
import json
import re
import time
import uuid
from collections import Counter
from pathlib import Path

import httpx
import jwt
import uvicorn
from cryptography.hazmat.primitives.asymmetric import ec
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

HERE = Path(__file__).resolve().parent
TEST_PARENT_ID = "00000000-0000-4000-8000-00000000a001"
TEST_KID_ID = "00000000-0000-4000-8000-00000000c001"
TEST_EMAIL = "perf-test-parent@example.invalid"

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8791)
ap.add_argument("--latency-ms", type=float, default=100.0, help="added to every fake call (measured prod round trip)")
ap.add_argument("--proxy", default="", help="forward to this Supabase URL instead of faking")
args = ap.parse_args()

# Login tokens: signed ES256 like production (Supabase's asymmetric JWT keys), with the public key
# at /auth/v1/.well-known/jwks.json, so a tutor that verifies tokens locally does so here too.
_KEY = ec.generate_private_key(ec.SECP256R1())
_KID = "perf-key-1"
_JWK = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(_KEY.public_key()))
_JWK.update({"kid": _KID, "alg": "ES256", "use": "sig"})


def mint(base_url, seconds=3600):
    now = int(time.time())
    return jwt.encode({"sub": TEST_PARENT_ID, "email": TEST_EMAIL, "aud": "authenticated", "role": "authenticated",
                       "iss": f"{base_url}/auth/v1", "iat": now, "exp": now + seconds, "session_id": "perf",
                       "app_metadata": {"provider": "email"}, "user_metadata": {}},
                      _KEY, algorithm="ES256", headers={"kid": _KID})


def _valid(tok):
    try:
        jwt.decode(tok, _KEY.public_key(), algorithms=["ES256"], audience="authenticated")
        return True
    except Exception:
        return False


STATS = {"calls": 0, "ms": 0.0, "by": Counter(), "ms_by": Counter()}


# ------------------------------------------------------------------ data
def _seed():
    seed = json.loads((HERE / "fixtures" / "seed.json").read_text()) if (HERE / "fixtures" / "seed.json").exists() else {}
    db = {k: v for k, v in seed.items() if isinstance(v, list)}
    lesson = (db.get("lesson_units_content") or [{}])[0]
    parent = (db.get("learning_lessons") or [{}])[0]
    grade = parent.get("grade") or 5
    db["kids_profiles"] = [{
        "id": TEST_KID_ID, "user_id": TEST_PARENT_ID, "child_name": "ילד בדיקה", "age": grade, "grade": grade,
        "gender": "male", "created_at": "2026-01-01T00:00:00+00:00", "avatar": None, "interests": [],
    }]
    db["subscriptions"] = [{"id": 1, "user_id": TEST_PARENT_ID, "status": "active", "plan": "family"}]
    db["kid_unit_lesson_progress"] = [{
        "id": 1, "kid_id": TEST_KID_ID, "unit_lesson_id": lesson.get("id"), "learning_lesson_id": lesson.get("learning_lesson_id"),
        "status": "in_progress", "current_part": 1, "progress_percent": 20, "updated_at": "2026-09-01T00:00:00+00:00",
    }]
    return db


DB = _seed()
_ids = Counter()
# column defaults of tables whose real schema gives them (supabase/migrations), so a fresh row looks like prod's
DEFAULTS = {
    "english_tutor_sessions": lambda: {"id": str(uuid.uuid4()), "level": "beginner", "status": "active", "turns": 0,
                                       "seconds_used": 0, "spoken_corrections": 0, "history": [], "words": [],
                                       "summary": None, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
                                       "last_turn_at": None, "ended_at": None},
}

OPS = {
    "eq": lambda a, b: str(a) == b or (isinstance(a, bool) and str(a).lower() == b),
    "neq": lambda a, b: str(a) != b,
    "gt": lambda a, b: _num(a) > _num(b), "gte": lambda a, b: _num(a) >= _num(b),
    "lt": lambda a, b: _num(a) < _num(b), "lte": lambda a, b: _num(a) <= _num(b),
    "in": lambda a, b: str(a) in [x.strip().strip('"') for x in b.strip("()").split(",")],
    "is": lambda a, b: (a is None) if b == "null" else (str(a).lower() == b),
    "like": lambda a, b: re.fullmatch(b.replace("*", ".*").replace("%", ".*"), str(a or "")) is not None,
    "ilike": lambda a, b: re.fullmatch(b.replace("*", ".*").replace("%", ".*"), str(a or ""), re.I) is not None,
    "cs": lambda a, b: True, "ov": lambda a, b: True, "fts": lambda a, b: True,
}
SKIP = {"select", "order", "limit", "offset", "on_conflict", "columns"}


def _num(x):
    try:
        return float(x)
    except Exception:
        return str(x)


def _match(row, params):
    for k, v in params.multi_items():
        if k in SKIP or k in ("or", "and"):
            continue
        neg = v.startswith("not.")
        if neg:
            v = v[4:]
        op, _, val = v.partition(".")
        fn = OPS.get(op)
        if fn is None:
            continue
        col = k.split("->")[0]
        ok = fn(row.get(col), val)
        if ok == neg:
            return False
    return True


def _order_limit(rows, params):
    order = params.get("order")
    if order:
        for part in reversed(order.split(",")):
            col, *mods = part.split(".")
            rows = sorted(rows, key=lambda r: (r.get(col) is None, str(r.get(col))), reverse="desc" in mods)
    off = int(params.get("offset") or 0)
    lim = params.get("limit")
    return rows[off: off + int(lim)] if lim else rows[off:]


def _project(rows, select):
    """Only the selected columns, like PostgREST (embedded resources like x(*) and casts are ignored)."""
    if not select or select.strip() == "*":
        return rows
    cols = [c.strip().split("::")[0].split(":")[-1] for c in select.split(",") if c.strip() and "(" not in c]
    if not cols or "*" in cols:
        return rows
    return [{c: r.get(c) for c in cols} for r in rows]


def _content_range(n):
    return {"Content-Range": f"0-{max(0, n - 1)}/{n}"}


def _respond(rows, request, total=None, status=200):
    accept = request.headers.get("accept", "")
    headers = _content_range(total if total is not None else len(rows))
    if "vnd.pgrst.object" in accept:
        if len(rows) != 1:
            if request.headers.get("prefer", "").find("missing=null") >= 0 or request.method == "GET" and "maybe" in accept:
                return Response(status_code=204, headers=headers)
            return JSONResponse({"code": "PGRST116", "message": "JSON object requested, multiple (or no) rows returned",
                                 "details": f"The result contains {len(rows)} rows", "hint": None},
                                status_code=406, headers=headers)
        return JSONResponse(rows[0], status_code=status, headers=headers)
    return JSONResponse(rows, status_code=status, headers=headers)


# ------------------------------------------------------------------ handlers
async def rest(request: Request):
    table = request.path_params["table"]
    params = request.query_params
    rows = DB.setdefault(table, [])
    if request.method == "GET" or request.method == "HEAD":
        hit = [r for r in rows if _match(r, params)]
        return _respond(_project(_order_limit(hit, params), params.get("select")), request, total=len(hit))
    body = await request.body()
    payload = json.loads(body) if body else {}
    if request.method == "POST":
        items = payload if isinstance(payload, list) else [payload]
        out = []
        conflict = [c for c in (params.get("on_conflict") or "").split(",") if c]
        for it in items:
            it = {**DEFAULTS[table](), **it} if table in DEFAULTS else dict(it)
            existing = None
            if conflict:
                existing = next((r for r in rows if all(str(r.get(c)) == str(it.get(c)) for c in conflict)), None)
            if existing is not None:
                existing.update(it); out.append(existing); continue
            if "id" not in it:
                _ids[table] += 1
                it["id"] = 10_000_000 + _ids[table]
            it.setdefault("created_at", time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()))
            rows.append(it); out.append(it)
        if len(rows) > 5000:  # a long run must not grow the fake without bound
            del rows[: len(rows) - 5000]
        return _respond(out, request, status=201)
    if request.method == "PATCH":
        hit = [r for r in rows if _match(r, params)]
        for r in hit:
            r.update(payload)
        return _respond(hit, request)
    if request.method == "DELETE":
        hit = [r for r in rows if _match(r, params)]
        DB[table] = [r for r in rows if r not in hit]
        return _respond(hit, request)
    return JSONResponse({"message": "method"}, status_code=405)


async def rpc(request: Request):
    fn = request.path_params["fn"]
    if fn == "media_jobs_enqueue":
        _ids["media_jobs"] += 1
        return JSONResponse(10_000_000 + _ids["media_jobs"])
    return JSONResponse([])


USER = {"id": TEST_PARENT_ID, "aud": "authenticated", "role": "authenticated", "email": TEST_EMAIL,
        "app_metadata": {"provider": "email"}, "user_metadata": {}, "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z", "email_confirmed_at": "2026-01-01T00:00:00Z"}


async def auth(request: Request):
    path = request.path_params["path"]
    if path == "user" or path.startswith("admin/users"):
        tok = request.headers.get("authorization", "")
        if path == "user" and not (tok.startswith("Bearer perf-") or _valid(tok[7:])):
            return JSONResponse({"code": 401, "msg": "invalid JWT"}, status_code=401)
        return JSONResponse(USER if path == "user" else {"user": USER, **USER})
    return JSONResponse({})


async def jwks(request: Request):
    return JSONResponse({"keys": [_JWK]})


async def token(request: Request):
    return JSONResponse({"access_token": mint(f"http://127.0.0.1:{args.port}")})


async def storage(request: Request):
    path = request.path_params["path"]
    if path.startswith("object/sign/"):
        body = await request.body()
        data = json.loads(body) if body else {}
        if isinstance(data, dict) and "paths" in data:
            return JSONResponse([{"path": p, "signedURL": f"/object/sign/fake/{p}?token=perf", "error": None} for p in data["paths"]])
        return JSONResponse({"signedURL": f"/object/sign/{path[12:]}?token=perf"})
    if path.startswith("object/list/"):
        return JSONResponse([])
    if request.method in ("POST", "PUT"):
        await request.body()
        return JSONResponse({"Key": path, "Id": str(uuid.uuid4())})
    if request.method == "GET":
        return Response(b"\x00" * 1024, media_type="application/octet-stream")
    return JSONResponse({})


async def stats(request: Request):
    return JSONResponse({"calls": STATS["calls"], "ms": round(STATS["ms"], 1),
                         "by": dict(STATS["by"]), "ms_by": {k: round(v, 1) for k, v in STATS["ms_by"].items()}})


async def reset(request: Request):
    STATS.update(calls=0, ms=0.0, by=Counter(), ms_by=Counter())
    return JSONResponse({"ok": True})


# ------------------------------------------------------------------ proxy mode
_upstream = httpx.AsyncClient(base_url=args.proxy, timeout=60,
                              limits=httpx.Limits(max_connections=400, max_keepalive_connections=400)) if args.proxy else None


async def proxy(request: Request):
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length", "accept-encoding")}
    r = await _upstream.request(request.method, request.url.path, params=request.query_params,
                                content=await request.body(), headers=headers)
    out = {k: v for k, v in r.headers.items() if k.lower() not in ("content-length", "content-encoding", "transfer-encoding", "connection")}
    return Response(r.content, status_code=r.status_code, headers=out)


# ------------------------------------------------------------------ counting wrapper
def _key(path):
    parts = path.strip("/").split("/")
    if parts[:2] == ["rest", "v1"] and len(parts) > 2:
        return "rpc:" + parts[3] if parts[2] == "rpc" and len(parts) > 3 else "table:" + parts[2]
    if parts[:2] == ["storage", "v1"]:          # object/sign/... vs object/<bucket> (upload) vs object/list
        return "/".join(parts[:4]) if len(parts) > 3 and parts[3] in ("sign", "list", "info") else "/".join(parts[:3])
    return "/".join(parts[:3])


def counted(handler):
    async def wrap(request: Request):
        t0 = time.perf_counter()
        if not args.proxy and args.latency_ms:
            await asyncio.sleep(args.latency_ms / 1000)
        resp = await (proxy(request) if args.proxy else handler(request))
        ms = (time.perf_counter() - t0) * 1000
        k = f"{request.method} {_key(request.url.path)}"
        STATS["calls"] += 1; STATS["ms"] += ms; STATS["by"][k] += 1; STATS["ms_by"][k] += ms
        return resp
    return wrap


METHODS = ["GET", "POST", "PATCH", "DELETE", "PUT", "HEAD"]
app = Starlette(routes=[
    Route("/__stats", stats), Route("/__reset", reset, methods=["POST"]), Route("/__token", token),
    Route("/auth/v1/.well-known/jwks.json", counted(jwks)),
    Route("/rest/v1/rpc/{fn}", counted(rpc), methods=METHODS),
    Route("/rest/v1/{table}", counted(rest), methods=METHODS),
    Route("/auth/v1/{path:path}", counted(auth), methods=METHODS),
    Route("/storage/v1/{path:path}", counted(storage), methods=METHODS),
])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning", access_log=False, timeout_keep_alive=120)
