"""Per-process caches for the request path, and local verification of login tokens.

Measured 2026-09-25 (performance/run.py): before any work, every route asked Supabase Auth
who the caller is (one network round trip) and read the child's row (another). At one
child in a lesson ~51 database calls a minute, 100,000 children would need ~85,000 calls a
second, against a database that gives out ~600-1,000. Most of those calls return the same
answer as a minute ago. This module keeps those answers for a short time.

What is cached, and for how long (all per process; a second process has its own copy):

  login tokens     verified here against the project's public signing key (JWKS, ES256),
                   exactly what Supabase's own getClaims() does. No network call. A token
                   the key cannot verify (legacy HS256, unknown key, JWKS unreachable) falls
                   back to sb.auth.get_user() as before. Trade-off: a session revoked at
                   logout stays usable until the token expires (at most its lifetime,
                   1 hour by default) - the same as every Supabase client that uses getClaims.
  child rows       60 s, keyed by (parent, child); dropped on /api/kid/update in this process
  subscriptions    60 s
  curriculum rows  5 min (learning_lessons never change during a session)
  media enqueues   a job with a dedupe key is not re-sent for 60 s (the database would
                   return the same live row anyway)

Lesson rows (lesson_units_content) are NOT cached: the worker changes their audio and
visual status while a child polls, and a cached row would hide the new pictures.

Knobs: AUTH_LOCAL_JWT=0 turns local verification off. REQUEST_CACHE=0 turns every cache
off (each lookup goes to the database, like before).
"""
import copy
import os
import threading
import time
from types import SimpleNamespace

import httpx
import jwt

CACHE_ENABLED = os.getenv("REQUEST_CACHE", "1") not in ("0", "false", "no")
AUTH_LOCAL_JWT = os.getenv("AUTH_LOCAL_JWT", "1") not in ("0", "false", "no")
JWKS_TTL_SECONDS = 600
JWKS_MIN_REFRESH_SECONDS = 30      # an unknown key id refetches at most this often


class TTLCache:
    """A small thread-safe dict with a per-entry expiry. get() returns a deep copy, so a caller
    that edits the row cannot change what the next caller sees."""

    def __init__(self, name: str, ttl: float, maxsize: int = 20_000):
        self.name, self.ttl, self.maxsize = name, ttl, maxsize
        self._d: dict = {}
        self._lock = threading.Lock()
        self.hits = self.misses = 0

    def get(self, key):
        if not CACHE_ENABLED:
            return None
        now = time.monotonic()
        with self._lock:
            hit = self._d.get(key)
            if hit is None or hit[1] <= now:
                self.misses += 1
                if hit is not None:
                    self._d.pop(key, None)
                return None
            self.hits += 1
            return copy.deepcopy(hit[0])

    def put(self, key, value, ttl: float | None = None):
        if not CACHE_ENABLED:
            return
        now = time.monotonic()
        with self._lock:
            if len(self._d) >= self.maxsize:
                for k in [k for k, v in self._d.items() if v[1] <= now]:
                    self._d.pop(k, None)
                if len(self._d) >= self.maxsize:
                    self._d.clear()
            self._d[key] = (copy.deepcopy(value), now + (self.ttl if ttl is None else ttl))

    def drop(self, predicate=None):
        with self._lock:
            if predicate is None:
                self._d.clear()
            else:
                for k in [k for k in self._d if predicate(k)]:
                    self._d.pop(k, None)

    def stats(self):
        return {"size": len(self._d), "hits": self.hits, "misses": self.misses}


child_rows = TTLCache("child_rows", 60)
subscriptions = TTLCache("subscriptions", 60)
curriculum_rows = TTLCache("curriculum_rows", 300)
media_enqueues = TTLCache("media_enqueues", 60)
ALL = [child_rows, subscriptions, curriculum_rows, media_enqueues]


class LocalJWTVerifier:
    """Verify a Supabase access token with the project's public keys, without a network call.

    Returns an object with .id / .email / .user_metadata / .app_metadata / .role - the fields
    the routes read from sb.auth.get_user(token).user - or None when this token cannot be
    verified locally (the caller then asks Supabase Auth, as before). A token that IS verified
    locally and is expired or has a wrong audience/issuer is None too: Supabase Auth gets the
    last word on anything this class is not sure about.
    """

    def __init__(self, supabase_url: str):
        self.base = (supabase_url or "").rstrip("/")
        # the tokens' issuer is the project URL; SUPABASE_JWT_ISSUER overrides it only when the service
        # reaches Supabase through a proxy (performance/run.py --db prod). Production never sets it.
        self.issuer = os.getenv("SUPABASE_JWT_ISSUER") or f"{self.base}/auth/v1"
        self._keys: dict = {}
        self._fetched_at = 0.0
        self._lock = threading.Lock()
        self.local_ok = self.fallbacks = 0

    def _refresh(self, force=False):
        now = time.monotonic()
        if not force and self._keys and now - self._fetched_at < JWKS_TTL_SECONDS:
            return
        if force and now - self._fetched_at < JWKS_MIN_REFRESH_SECONDS:
            return
        with self._lock:
            try:
                r = httpx.get(f"{self.base}/auth/v1/.well-known/jwks.json", timeout=5)
                r.raise_for_status()
                keys = {}
                for k in r.json().get("keys", []):
                    if k.get("kty") == "EC" and k.get("kid"):
                        keys[k["kid"]] = jwt.algorithms.ECAlgorithm.from_jwk(k)
                    elif k.get("kty") == "RSA" and k.get("kid"):
                        keys[k["kid"]] = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                self._keys = keys
            except Exception as e:  # keep the old keys; fall back to the network per token
                print("AUTH JWKS: refresh failed, using Supabase Auth per request:", repr(e)[:160])
            self._fetched_at = time.monotonic()

    def verify(self, token: str):
        if not AUTH_LOCAL_JWT or not token or token.count(".") != 2:
            return None
        try:
            header = jwt.get_unverified_header(token)
        except Exception:
            return None
        alg, kid = header.get("alg"), header.get("kid")
        if alg not in ("ES256", "RS256") or not kid:
            self.fallbacks += 1
            return None                      # legacy HS256 tokens: Supabase Auth decides
        self._refresh()
        key = self._keys.get(kid)
        if key is None:
            self._refresh(force=True)        # keys rotated
            key = self._keys.get(kid)
            if key is None:
                self.fallbacks += 1
                return None
        try:
            claims = jwt.decode(token, key, algorithms=[alg], audience="authenticated", issuer=self.issuer,
                                options={"require": ["exp", "sub", "aud"]}, leeway=5)
        except Exception:
            self.fallbacks += 1
            return None
        if claims.get("role") not in (None, "authenticated") or claims.get("is_anonymous"):
            self.fallbacks += 1
            return None
        self.local_ok += 1
        return SimpleNamespace(id=claims["sub"], email=claims.get("email") or "",
                               user_metadata=claims.get("user_metadata") or {},
                               app_metadata=claims.get("app_metadata") or {},
                               role=claims.get("role") or "authenticated", aud=claims.get("aud"))


def stats(verifier: LocalJWTVerifier | None = None) -> dict:
    out = {c.name: c.stats() for c in ALL}
    if verifier is not None:
        out["auth_local"] = verifier.local_ok
        out["auth_fallback"] = verifier.fallbacks
    return out
