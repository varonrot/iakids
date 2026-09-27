#!/usr/bin/env python3
"""Check supabase/migrations/20260926_security_fixes.sql against the live database.

    backend/.venv/bin/python tools/verify_security_sql.py          # dry run: prints the plan
    backend/.venv/bin/python tools/verify_security_sql.py --run    # does it

Run it AFTER the user has applied the migration in the Supabase SQL editor.

With --run it creates two throwaway parents (perf-test-*@iakids.app, each with one
child) through performance/prod_identity.py, then goes through PostgREST exactly as a
browser would, with each parent's own JWT and with the publishable (anon) key:

  * every FORBIDDEN write must be refused (HTTP >= 400) or change nothing (checked
    afterwards with the service role);
  * every LEGIT flow the pages use must still work.

Everything it created is deleted in `finally`, rows first, then the two users. If a run
dies half-way, `python performance/prod_identity.py --cleanup` removes leftover users.

Keys are read from backend-ai-tutor-he/.env.prod (service role) and backend/.env
(publishable key) and never printed. Exit code 1 if any check fails.
"""
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "performance"))

NIL = "00000000-0000-0000-0000-000000000000"

PLAN = [
    # (kind, description)
    ("setup",     "create parents A and B (one child each) with the service role"),
    ("legit",     "A creates a support ticket as support/index.html does {subject, category, user_id}"),
    ("legit",     "A adds a message to that ticket {ticket_id, sender_type:'user', message}"),
    ("legit",     "A inserts a kid_game_sessions row for A's own child (game-sdk.js shape)"),
    ("legit",     "A inserts its free subscription {user_id, plan:'free', status:'active'}"),
    ("forbidden", "A: rpc game_question_mark -> refused"),
    ("forbidden", "anon: rpc game_question_mark -> refused"),
    ("forbidden", "A: rpc increment_usage_summary(p_user_id=A) -> refused"),
    ("forbidden", "A: ticket sent with status=closed, priority=high -> stored open/medium"),
    ("forbidden", "A: ticket sent with user_id=B -> refused or stored as A's"),
    ("forbidden", "A: PATCH own ticket status=closed, priority=high -> unchanged"),
    ("forbidden", "A: message with sender_type=admin, is_internal=true -> stored user/false, sender_id=A"),
    ("forbidden", "A: message into B's ticket -> refused"),
    ("forbidden", "A: ticket with category='spam' -> refused (CHECK)"),
    ("forbidden", "A: kid_game_sessions insert for B's child -> refused"),
    ("forbidden", "A: PATCH B's kid_game_sessions score -> unchanged"),
    ("forbidden", "A: kid_question_answers insert for B's child -> refused"),
    ("forbidden", "A: PATCH B's kids_profiles child_name -> unchanged"),
    ("forbidden", "A: PATCH own kids_profiles user_id=B -> unchanged"),
    ("forbidden", "A: kid_tasks insert with user_id=A, kid_id=B's child -> refused"),
    ("forbidden", "A: PATCH own subscription plan=annual -> unchanged"),
    ("forbidden", "A: DELETE own subscription -> row still there"),
    ("forbidden", "anon: PATCH subscriptions plan=annual (A's row) -> unchanged"),
    ("forbidden", "A: POST usage_summary own row -> refused"),
    ("forbidden", "A: PATCH own usage_summary total_cost_usd -> unchanged (row seeded by service role)"),
    ("forbidden", "A: DELETE own usage_summary -> row still there"),
    ("forbidden", "A / anon: POST games_catalog -> refused"),
    ("forbidden", "A / anon: PATCH / DELETE games_catalog (filter matching no row) -> refused by grant"),
    ("cleanup",   "delete every row created above, then both users (finally)"),
]


def load_env(path):
    env = {}
    for line in Path(path).read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


class Rest:
    def __init__(self, url, service_key, anon_key):
        self.base = url.rstrip("/") + "/rest/v1/"
        self.service_key, self.anon_key = service_key, anon_key
        self.http = httpx.Client(timeout=30)

    def call(self, method, path, token=None, json=None, prefer="return=representation"):
        """token=None -> anon; token='service' -> service role; else a user JWT."""
        if token == "service":
            key = bearer = self.service_key
        else:
            key, bearer = self.anon_key, (token or self.anon_key)
        headers = {"apikey": key, "Authorization": f"Bearer {bearer}", "Prefer": prefer}
        return self.http.request(method, self.base + path, headers=headers, json=json)

    def svc(self, path):
        r = self.call("GET", path, "service")
        r.raise_for_status()
        return r.json()


class Report:
    def __init__(self):
        self.fails = 0

    def check(self, ok, what, detail=""):
        if not ok:
            self.fails += 1
        tag = "PASS" if ok else "FAIL"
        print(f"  {tag}  {what}" + (f"   [{detail}]" if detail and not ok else ""), flush=True)
        return ok


def refused(r):
    return r.status_code >= 400


def brief(r):
    return f"HTTP {r.status_code} {r.text[:160]}"


def run():
    from prod_identity import make_identity, drop_identity

    prod = load_env(ROOT / "backend-ai-tutor-he" / ".env.prod")
    pub = load_env(ROOT / "backend" / ".env")
    if prod["SUPABASE_URL"].rstrip("/") != pub.get("SUPABASE_URL", "").rstrip("/"):
        sys.exit("backend/.env and backend-ai-tutor-he/.env.prod point at different projects")
    api = Rest(prod["SUPABASE_URL"], prod["SUPABASE_SERVICE_ROLE_KEY"], pub["SUPABASE_PUBLISHABLE_KEY"])
    rep = Report()
    idents, sentinel = [], f"sec-test-{time.strftime('%Y%m%d%H%M%S')}"

    try:
        A = make_identity(prod); idents.append(A)
        time.sleep(1.1)  # make_identity names users by the second
        B = make_identity(prod); idents.append(B)
        ta, tb = A["token"], B["token"]
        game = api.svc("games_catalog?select=id&is_active=eq.true&limit=1")[0]["id"]

        print("\nLegit flows — must still work")
        r = api.call("POST", "support_tickets", ta, {"subject": "sec test A", "category": "question", "user_id": A["user_id"]})
        rep.check(r.status_code == 201, "A creates a ticket", brief(r))
        ticket_a = r.json()[0]["id"] if r.status_code == 201 else None
        r = api.call("POST", "support_messages", ta, {"ticket_id": ticket_a, "sender_type": "user", "message": "hello"})
        rep.check(r.status_code == 201, "A adds a message to own ticket", brief(r))
        r = api.call("POST", "kid_game_sessions", ta, {"kid_id": A["kid_id"], "game_id": game, "difficulty": 1,
                                                      "questions_count": 10, "completed": False, "ended_reason": "interrupted"})
        rep.check(r.status_code == 201, "A inserts kid_game_sessions for own child", brief(r))
        # A free row may already exist for a new account (trigger / unique index): then the
        # insert must at least not be refused by RLS, and the row must stay free.
        existing = api.svc(f"subscriptions?select=id&user_id=eq.{A['user_id']}")
        r = api.call("POST", "subscriptions", ta, {"user_id": A["user_id"], "plan": "free", "status": "active"})
        ok = r.status_code == 201 or (existing and r.status_code == 409)
        rep.check(ok, "A inserts its free subscription", brief(r))
        # B's side, for the cross-user checks
        r = api.call("POST", "support_tickets", tb, {"subject": "sec test B", "category": "bug", "user_id": B["user_id"]})
        rep.check(r.status_code == 201, "B creates a ticket", brief(r))
        ticket_b = r.json()[0]["id"] if r.status_code == 201 else NIL
        sess_b = api.call("POST", "kid_game_sessions", "service", {"kid_id": B["kid_id"], "game_id": game, "score": 7}).json()[0]["id"]
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        r = api.call("POST", "usage_summary", "service", {"user_id": A["user_id"], "total_cost_usd": 1,
                                                          "period_start": now, "period_end": now})
        rep.check(r.status_code == 201, "setup: service role seeds A's usage_summary row", brief(r))

        print("\nForbidden — must be refused or change nothing")
        body = {"p_game": "sec-test", "p_key": "sec-test", "was_correct": True}
        rep.check(refused(api.call("POST", "rpc/game_question_mark", ta, body)), "A: rpc game_question_mark")
        rep.check(refused(api.call("POST", "rpc/game_question_mark", None, body)), "anon: rpc game_question_mark")

        spec = api.call("GET", "", "service", prefer="").json()
        params = next((p.get("schema", {}).get("properties", {})
                       for p in spec["paths"].get("/rpc/increment_usage_summary", {}).get("post", {}).get("parameters", [])
                       if p.get("in") == "body"), {})
        inc = {k: 0 for k in params}
        inc["p_user_id"] = A["user_id"]
        r = api.call("POST", "rpc/increment_usage_summary", ta, inc)
        rep.check(refused(r), "A: rpc increment_usage_summary", brief(r))

        r = api.call("POST", "support_tickets", ta, {"subject": "forged", "category": "question", "status": "closed",
                                                    "priority": "high", "user_id": A["user_id"]})
        row = api.svc(f"support_tickets?select=status,priority&id=eq.{r.json()[0]['id']}")[0] if r.status_code == 201 else None
        rep.check(row == {"status": "open", "priority": "medium"},
                  "A: ticket sent as closed/high is stored open/medium", str(row) if row else brief(r))
        r = api.call("POST", "support_tickets", ta, {"subject": "forged", "category": "question", "user_id": B["user_id"]})
        if r.status_code == 201:
            row = api.svc(f"support_tickets?select=user_id&id=eq.{r.json()[0]['id']}")[0]
            rep.check(row["user_id"] == A["user_id"], "A: ticket sent as B's is stored as A's", str(row))
        else:
            rep.check(True, "A: ticket sent as B's refused outright")

        api.call("PATCH", f"support_tickets?id=eq.{ticket_a}", ta, {"status": "closed", "priority": "high"})
        row = api.svc(f"support_tickets?select=status,priority&id=eq.{ticket_a}")[0]
        rep.check(row == {"status": "open", "priority": "medium"}, "A: PATCH own ticket state -> unchanged", str(row))

        r = api.call("POST", "support_messages", ta, {"ticket_id": ticket_a, "sender_type": "admin",
                                                     "is_internal": True, "message": "forged admin"})
        if r.status_code == 201:
            row = api.svc(f"support_messages?select=sender_type,is_internal,sender_id&id=eq.{r.json()[0]['id']}")[0]
            rep.check(row == {"sender_type": "user", "is_internal": False, "sender_id": A["user_id"]},
                      "A: forged admin message stored as user", str(row))
        else:
            rep.check(True, "A: forged admin message refused outright")

        r = api.call("POST", "support_messages", ta, {"ticket_id": ticket_b, "sender_type": "user", "message": "x"})
        rep.check(refused(r), "A: message into B's ticket", brief(r))
        r = api.call("POST", "support_tickets", ta, {"subject": "x", "category": "spam", "user_id": A["user_id"]})
        rep.check(refused(r), "A: ticket with category=spam", brief(r))

        r = api.call("POST", "kid_game_sessions", ta, {"kid_id": B["kid_id"], "game_id": game})
        rep.check(refused(r), "A: kid_game_sessions for B's child", brief(r))
        api.call("PATCH", f"kid_game_sessions?id=eq.{sess_b}", ta, {"score": 999})
        row = api.svc(f"kid_game_sessions?select=score&id=eq.{sess_b}")[0]
        rep.check(row["score"] == 7, "A: PATCH B's game session -> unchanged", str(row))
        r = api.call("POST", "kid_question_answers", ta, {"kid_id": B["kid_id"], "game_code": "sec-test",
                                                         "qkey": "sec-test", "correct": True})
        rep.check(refused(r), "A: kid_question_answers for B's child", brief(r))

        api.call("PATCH", f"kids_profiles?id=eq.{B['kid_id']}", ta, {"child_name": "hacked"})
        row = api.svc(f"kids_profiles?select=child_name&id=eq.{B['kid_id']}")[0]
        rep.check(row["child_name"] != "hacked", "A: PATCH B's child -> unchanged", str(row))
        api.call("PATCH", f"kids_profiles?id=eq.{A['kid_id']}", ta, {"user_id": B["user_id"]})
        row = api.svc(f"kids_profiles?select=user_id&id=eq.{A['kid_id']}")[0]
        rep.check(row["user_id"] == A["user_id"], "A: hand own child to B -> unchanged", str(row))
        r = api.call("POST", "kid_tasks", ta, {"user_id": A["user_id"], "kid_id": B["kid_id"], "task_type": "homework",
                                              "title": "sec test", "status": "pending", "source": "manual"})
        rep.check(refused(r), "A: kid_tasks on B's child", brief(r))

        api.call("PATCH", f"subscriptions?user_id=eq.{A['user_id']}", ta, {"plan": "annual"})
        api.call("PATCH", f"subscriptions?user_id=eq.{A['user_id']}", None, {"plan": "annual"})
        plans = {s["plan"] for s in api.svc(f"subscriptions?select=plan&user_id=eq.{A['user_id']}")}
        rep.check(plans <= {"free"}, "A / anon: PATCH subscription plan=annual -> unchanged", str(plans))
        before = len(api.svc(f"subscriptions?select=id&user_id=eq.{A['user_id']}"))
        api.call("DELETE", f"subscriptions?user_id=eq.{A['user_id']}", ta)
        after = len(api.svc(f"subscriptions?select=id&user_id=eq.{A['user_id']}"))
        rep.check(after == before, "A: DELETE own subscription -> still there", f"{before} -> {after}")

        r = api.call("POST", "usage_summary", ta, {"user_id": A["user_id"]})
        rep.check(refused(r), "A: POST usage_summary", brief(r))
        api.call("PATCH", f"usage_summary?user_id=eq.{A['user_id']}", ta, {"total_cost_usd": 0})
        costs = [float(u["total_cost_usd"]) for u in api.svc(f"usage_summary?select=total_cost_usd&user_id=eq.{A['user_id']}")]
        rep.check(costs == [1.0], "A: PATCH usage_summary -> unchanged", str(costs))
        api.call("DELETE", f"usage_summary?user_id=eq.{A['user_id']}", ta)
        n = len(api.svc(f"usage_summary?select=id&user_id=eq.{A['user_id']}"))
        rep.check(n == 1, "A: DELETE usage_summary -> still there", str(n))

        for who, tok in (("A", ta), ("anon", None)):
            r = api.call("POST", "games_catalog", tok, {"game_code": sentinel, "game_name": sentinel})
            rep.check(refused(r), f"{who}: POST games_catalog", brief(r))
            r = api.call("PATCH", f"games_catalog?id=eq.{NIL}", tok, {"is_active": False})
            rep.check(refused(r), f"{who}: PATCH games_catalog (no-match filter) refused by grant", brief(r))
            r = api.call("DELETE", f"games_catalog?id=eq.{NIL}", tok)
            rep.check(refused(r), f"{who}: DELETE games_catalog (no-match filter) refused by grant", brief(r))
    finally:
        print("\nCleanup")
        for ident in idents:
            uid, kid = ident["user_id"], ident["kid_id"]
            tickets = [t["id"] for t in api.svc(f"support_tickets?select=id&user_id=eq.{uid}")]
            for t in tickets:
                api.call("DELETE", f"support_messages?ticket_id=eq.{t}", "service")
            api.call("DELETE", f"support_tickets?user_id=eq.{uid}", "service")
            for table in ("kid_question_answers", "kid_game_sessions"):
                api.call("DELETE", f"{table}?kid_id=eq.{kid}", "service")
            for table in ("kid_tasks", "usage_summary", "subscriptions"):
                api.call("DELETE", f"{table}?user_id=eq.{uid}", "service")
            try:
                drop_identity(prod, ident)
            except Exception as e:  # keep cleaning the other one
                print(f"  could not drop {ident.get('email')}: {e} — run performance/prod_identity.py --cleanup")
        api.call("DELETE", f"games_catalog?game_code=eq.{sentinel}", "service")

    print(f"\n{'ALL PASS' if not rep.fails else f'{rep.fails} FAILED'}")
    return 1 if rep.fails else 0


def main():
    if "--run" not in sys.argv:
        print(__doc__)
        print("Plan (dry run — nothing was sent):")
        for kind, what in PLAN:
            print(f"  [{kind:9}] {what}")
        print("\nRe-run with --run to execute.")
        return 0
    return run()


if __name__ == "__main__":
    sys.exit(main())
