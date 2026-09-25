#!/usr/bin/env python3
"""Try to get into the admin API without being an admin. Read-only except one approve attempt that must fail.

    backend/.venv/bin/python tools/admin_security_check.py --base https://smarts-brains.online/tutor-api \\
        --user-token <a signed-in NON-admin's access token> [--admin-token <an admin's token>] \\
        [--jwks https://<project>.supabase.co/auth/v1/.well-known/jwks.json] [--item-id <qbank id>]

Every attack must end in 401/403/404/405 with no admin data in the body. With --admin-token, the same routes must
answer 200 (so a "pass" is not just a broken route). Exit code 1 if anything got through.
"""
import argparse
import base64
import json
import sys
import time

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

ROUTES = [("GET", "/api/admin/links"), ("GET", "/api/admin/qbank/summary"), ("GET", "/api/admin/qbank/items?status=pending&limit=5"),
          ("GET", "/api/admin/whoami"), ("GET", "/api/admin/lessons/quality")]
LEAK_MARKERS = ('"links"', '"items"', '"by_status"', '"lessons"', '"email"', '"stem"', '"answer"')


def b64(d: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()


def forged_tokens(admin_email: str, kid: str | None, jwks: dict | None) -> dict:
    now = int(time.time())
    claims = {"sub": "00000000-0000-4000-8000-0000000000ad", "email": admin_email, "aud": "authenticated", "role": "authenticated",
              "iat": now, "exp": now + 3600}
    attacker = ec.generate_private_key(ec.SECP256R1())
    out = {"attacker's own ES256 key, admin email": jwt.encode(claims, attacker, algorithm="ES256", headers={"kid": kid or "x"}),
           "alg=none, admin email": b64({"alg": "none", "typ": "JWT"}) + "." + b64(claims) + ".",
           "HS256 with a guessed secret": jwt.encode(claims, "super-secret-jwt-token-with-at-least-32-characters-long", algorithm="HS256")}
    if jwks and jwks.get("keys"):
        pub = jwt.algorithms.ECAlgorithm.from_jwk(jwks["keys"][0])
        pem = pub.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        # key confusion: HMAC-sign with the PUBLIC key as the secret (hand-built: PyJWT refuses to do it)
        import hmac, hashlib
        head = b64({"alg": "HS256", "typ": "JWT", "kid": kid})
        body = b64(claims)
        sig = base64.urlsafe_b64encode(hmac.new(pem, f"{head}.{body}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
        out["HS256 signed with the public key (key confusion)"] = f"{head}.{body}.{sig}"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--user-token", required=True, help="a real signed-in user who is NOT an admin")
    ap.add_argument("--admin-token", default="")
    ap.add_argument("--expired-token", default="")
    ap.add_argument("--jwks", default="")
    ap.add_argument("--admin-email", default="admin@example.com", help="the email a forged token claims")
    ap.add_argument("--item-id", default="", help="a pending qbank item: a non-admin approve must not change it")
    a = ap.parse_args()
    c = httpx.Client(timeout=60, follow_redirects=False)
    jwks = c.get(a.jwks).json() if a.jwks else None
    kid = (jwks or {}).get("keys", [{}])[0].get("kid") if jwks else None
    fails, rows = [], []

    def attempt(name, method, path, headers=None, expect_denied=True, body=None, params=None):
        r = c.request(method, a.base + path, headers=headers or {}, json=body, params=params)
        leaked = r.status_code == 200 and any(m in r.text for m in LEAK_MARKERS)
        # 429 = the address is locked after repeated failures (admin_guard.py): also a denial
        ok = (r.status_code in (401, 403, 404, 405, 422, 429, 307, 308) and not leaked) if expect_denied else r.status_code == 200
        rows.append((ok, name, method, path, r.status_code))
        if not ok:
            fails.append(f"{name}: {method} {path} -> {r.status_code} {r.text[:120]}")

    # the control first: the attacks below lock this address (admin_guard.py), after which even the admin gets 429
    if a.admin_token:
        for m, p in ROUTES:
            attempt("the real admin (control: must work)", m, p, {"Authorization": f"Bearer {a.admin_token}"}, expect_denied=False)
    tokens = {"no token": None, "empty bearer": "", "garbage": "abc.def.ghi", "a real NON-admin user": a.user_token}
    if a.expired_token:
        tokens["expired token"] = a.expired_token
    tokens.update(forged_tokens(a.admin_email, kid, jwks))
    for tname, tok in tokens.items():
        for m, p in ROUTES:
            h = {} if tok is None else {"Authorization": f"Bearer {tok}".strip()}
            attempt(tname, m, p, h)
    u = {"Authorization": f"Bearer {a.user_token}"}
    for m, p in [("GET", "/api/admin/links/"), ("GET", "//api/admin/links"), ("GET", "/api/%61dmin/links"), ("GET", "/api/admin/./links"),
                 ("GET", "/api/ADMIN/links"), ("HEAD", "/api/admin/links"), ("OPTIONS", "/api/admin/links")]:
        attempt("path/method trick as a non-admin", m, p, u)
    attempt("token in the URL instead of the header", "GET", "/api/admin/links", {}, params={"access_token": a.user_token})
    attempt("lower-case 'bearer'", "GET", "/api/admin/links", {"Authorization": f"bearer {a.user_token}"})
    attempt("method override header", "GET", "/api/admin/qbank/items/x/review", {**u, "X-HTTP-Method-Override": "POST"})
    if a.item_id:
        attempt("non-admin approves an item", "POST", f"/api/admin/qbank/items/{a.item_id}/review", u, body={"status": "approved"})
        if a.admin_token:
            r = c.get(a.base + "/api/admin/qbank/items", params={"status": "approved", "limit": 100}, headers={"Authorization": f"Bearer {a.admin_token}"})
            if a.item_id in r.text:
                fails.append(f"the item {a.item_id} became approved after a non-admin request")
    if a.admin_token:
        r = c.get(a.base + "/api/admin/links", headers={"Authorization": f"Bearer {a.admin_token}"})
        rows.append((r.status_code == 429, "after the attacks this address is LOCKED, even for the admin", "GET", "/api/admin/links", r.status_code))
        if r.status_code != 429:
            fails.append(f"after {len(rows)} failed attempts the address was not locked ({r.status_code})")
    width = max(len(r[1]) for r in rows)
    for ok, name, m, p, st in rows:
        print(f"{'ok  ' if ok else 'FAIL'} {name:<{width}}  {m:<7} {p:<52} {st}")
    print(f"\n{len(rows)} attempts, {len(fails)} got through")
    for f in fails:
        print("  GOT THROUGH:", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
