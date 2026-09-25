"""Lock-out for the admin API: an address that keeps failing the admin check is locked for a while.

(2026-09-25, user: lock and release.) Admin sign-in is Google + the server's admin list, and forged tokens are
refused (tools/admin_security_check.py), so nobody can guess their way in; this is defence in depth and an alarm:

  * every /api/admin/* answer 401 or 403 counts as a failure for the caller's address;
  * ADMIN_LOCK_FAILS failures within ADMIN_LOCK_WINDOW_MIN minutes lock that address for ADMIN_LOCK_MINUTES:
    every /api/admin/* request from it gets 429, even with a valid admin token (a stolen token used from the
    attacker's address stays locked out too);
  * a success resets the address's count; a lock ends by itself, or an admin releases it from the hub
    (GET /api/admin/security/locks, POST /api/admin/security/locks/release) from another address;
  * every lock and release is printed to the service log.
State is per process (one uvicorn worker today); a restart clears it. The address is the client address after
uvicorn's --proxy-headers (nginx sets X-Forwarded-For; only 127.0.0.1 is trusted to set it).
"""
import os
import threading
import time
from typing import Optional

from fastapi import Header, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request

from main import LimitedRequest, app, require_admin

LOCK_FAILS = int(os.getenv("ADMIN_LOCK_FAILS", "5"))
LOCK_WINDOW = 60 * float(os.getenv("ADMIN_LOCK_WINDOW_MIN", "15"))
LOCK_SECONDS = 60 * float(os.getenv("ADMIN_LOCK_MINUTES", "30"))
_FAILS: dict = {}      # address -> [failure times]
_LOCKS: dict = {}      # address -> {"until": t, "since": t, "fails": n}
_GUARD = threading.Lock()
now = time.time          # a function, so tests can move the clock


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "?"


def is_locked(ip: str) -> Optional[dict]:
    with _GUARD:
        lk = _LOCKS.get(ip)
        if lk and lk["until"] <= now():
            _LOCKS.pop(ip, None)
            print("ADMIN LOCK EXPIRED:", {"ip": ip})
            return None
        return lk


def record(ip: str, status: int):
    t = now()
    with _GUARD:
        if status in (401, 403):
            times = [x for x in _FAILS.get(ip, []) if x > t - LOCK_WINDOW] + [t]
            _FAILS[ip] = times
            if len(times) >= LOCK_FAILS and ip not in _LOCKS:
                _LOCKS[ip] = {"until": t + LOCK_SECONDS, "since": t, "fails": len(times)}
                _FAILS.pop(ip, None)
                print("ADMIN LOCK:", {"ip": ip, "fails": len(times), "minutes": LOCK_SECONDS / 60})
        elif 200 <= status < 300:
            _FAILS.pop(ip, None)
        if len(_FAILS) > 10000:                           # forget quiet addresses
            for k in [k for k, v in _FAILS.items() if not v or v[-1] < t - LOCK_WINDOW]:
                _FAILS.pop(k, None)


@app.middleware("http")
async def _admin_lockout(request: Request, call_next):
    if not request.url.path.startswith("/api/admin/"):
        return await call_next(request)
    ip = client_ip(request)
    lk = is_locked(ip)
    if lk:
        retry = max(1, int(lk["until"] - now()))
        return JSONResponse(status_code=429, headers={"Retry-After": str(retry)},
                            content={"detail": "too many failed admin attempts from this address; try again later", "retry_after": retry})
    response = await call_next(request)
    record(ip, response.status_code)
    return response


class AdminReleaseRequest(LimitedRequest):
    ip: str


@app.get("/api/admin/security/locks")
def admin_locks(authorization: str = Header(None)):
    require_admin(authorization)
    t = now()
    with _GUARD:
        locks = [{"ip": ip, "minutes_left": round((lk["until"] - t) / 60, 1), "fails": lk["fails"],
                  "since": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(lk["since"]))} for ip, lk in _LOCKS.items() if lk["until"] > t]
        watching = {ip: len(v) for ip, v in _FAILS.items() if v and v[-1] > t - LOCK_WINDOW}
    return {"locks": locks, "failing": watching, "policy": {"fails": LOCK_FAILS, "window_min": LOCK_WINDOW / 60, "lock_min": LOCK_SECONDS / 60}}


@app.post("/api/admin/security/locks/release")
def admin_release(body: AdminReleaseRequest, authorization: str = Header(None)):
    admin = require_admin(authorization)
    with _GUARD:
        gone = _LOCKS.pop(body.ip, None)
        _FAILS.pop(body.ip, None)
    if not gone:
        raise HTTPException(status_code=404, detail="that address is not locked")
    print("ADMIN LOCK RELEASED:", {"ip": body.ip, "by": str(getattr(admin, "email", "") or "").lower()})
    return {"ok": True, "released": body.ip}
