#!/usr/bin/env python3
"""Talk to the English voice tutor in the terminal, before anything is deployed.

    backend/.venv/bin/python performance/english_try.py                 # the real teacher (OpenRouter, ~$0.0005 a turn)
    backend/.venv/bin/python performance/english_try.py --fake-model    # free: checks the flow only
    backend/.venv/bin/python performance/english_try.py --gender female --level elementary --topic food

What it starts, all on this box and all stopped at the end:
  * the fake database (performance/fake_supabase.py) - no table to create, no production data touched;
  * with --fake-model, the fake model server; otherwise the real model through OPENROUTER_API_KEY from
    backend-ai-tutor-he/.env.dev (the key is shared with production: every turn is a real, small charge);
  * its own copy of the tutor on --port with every other key a dummy.
Commands while talking: /end (summary + parent line), /allowance, /quit.
The daily allowance is the real one (ENGLISH_FREE_SECONDS_PER_DAY, 10 minutes), so you can see it run out
(--free-seconds 60 to see it quickly).
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TUTOR = ROOT / "backend-ai-tutor-he"
PY = str(ROOT / "backend" / ".venv" / "bin" / "python")
KID = "00000000-0000-4000-8000-00000000c001"

ap = argparse.ArgumentParser()
ap.add_argument("--fake-model", action="store_true")
ap.add_argument("--gender", choices=["male", "female"], default="male")
ap.add_argument("--level", choices=["beginner", "elementary", "intermediate"], default=None)
ap.add_argument("--topic", default="animals")
ap.add_argument("--name", default="", help="the test child's first name (default: נועה / איתי by gender)")
ap.add_argument("--free-seconds", type=int, default=600)
ap.add_argument("--port", type=int, default=8789)
ap.add_argument("--script", default="", help="file with one child message per line (non-interactive run)")
args = ap.parse_args()
SB, MODELS = args.port - 8, args.port - 7
LOG = Path(os.environ.get("TMPDIR", "/tmp")) / f"english_try_{args.port}"
LOG.mkdir(parents=True, exist_ok=True)
procs = []


def start(cmd, name, env=None, cwd=None):
    procs.append(subprocess.Popen(cmd, stdout=open(LOG / f"{name}.log", "wb"), stderr=subprocess.STDOUT,
                                  env=env, cwd=cwd, start_new_session=True))


def stop():
    for p in procs:
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGTERM)


def call(method, path, body=None, token=None):
    req = urllib.request.Request(f"http://127.0.0.1:{args.port}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def wait(url):
    for _ in range(120):
        try:
            urllib.request.urlopen(url, timeout=2).read(); return True
        except urllib.error.HTTPError:
            return True
        except Exception:
            time.sleep(0.5)
    return False


def dotenv(path):
    out = {}
    for line in Path(path).read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1); out[k.strip()] = v.strip().strip('"')
    return out


def show(reply, extra):
    print(f"\n  המורה: {reply['say_he']}")
    print(f"  ► להגיד באנגלית: {reply['target_en']}   ({reply['task']}" + (f": {' / '.join(reply['options'])}" if reply.get("options") else "") + ")")
    c = reply.get("correction")
    if c:
        print(f"  ✎ תיקון{' (נאמר בקול)' if extra.get('speak_correction') else ' (רק על המסך)'}: {c['said']} → {c['better']} — {c['why_he']}")
    if reply.get("new_words"):
        print("  + מילים חדשות: " + ", ".join(f"{w['en']} ({w['he']})" for w in reply["new_words"]))
    print(f"  [רמה: {extra.get('level')} · נותרו היום: {extra.get('remaining_seconds')} שנ׳]")


try:
    start([PY, str(HERE / "fake_supabase.py"), "--port", str(SB), "--latency-ms", "0"], "db")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENAI", "OPENROUTER", "GEMINI", "SUPABASE"))}
    env.update({"APP_ENV": "perf", "SUPABASE_URL": f"http://127.0.0.1:{SB}", "SUPABASE_SERVICE_ROLE_KEY": "try-key",
                "SUPABASE_PUBLISHABLE_KEY": "x", "GEMINI_API_KEY": "try-dummy", "OPENAI_API_KEY": "sk-try-dummy",
                "AI_PROVIDER": "openrouter", "TTS_PROVIDER": "openrouter", "AI_COSTS_ENABLED": "0", "OPS_METRICS_ENABLED": "0",
                "OPS_LOG_DIR": str(LOG), "ENGLISH_FREE_SECONDS_PER_DAY": str(args.free_seconds),
                "ENGLISH_PAID_SECONDS_PER_DAY": str(args.free_seconds), "PYTHONUNBUFFERED": "1"})
    if args.fake_model:
        start([PY, str(HERE / "fake_models.py"), "--port", str(MODELS), "--scale", "0.1"], "models")
        env.update({"OPENROUTER_API_KEY": "sk-or-try-dummy", "OPENROUTER_BASE_URL": f"http://127.0.0.1:{MODELS}/api/v1"})
        wait(f"http://127.0.0.1:{MODELS}/__calls")
    else:
        key = dotenv(TUTOR / ".env.dev").get("OPENROUTER_API_KEY", "")
        if not key:
            sys.exit("no OPENROUTER_API_KEY in backend-ai-tutor-he/.env.dev; use --fake-model")
        env["OPENROUTER_API_KEY"] = key
    wait(f"http://127.0.0.1:{SB}/__stats")
    start([str(ROOT / "backend" / ".venv" / "bin" / "uvicorn"), "main:app", "--host", "127.0.0.1", "--port", str(args.port),
           "--no-access-log"], "tutor", env=env, cwd=str(TUTOR))
    print("starting the tutor copy (fake database, " + ("fake model" if args.fake_model else "REAL model via OpenRouter") + ") ...")
    if not wait(f"http://127.0.0.1:{args.port}/"):
        sys.exit(f"the tutor copy did not start; see {LOG}/tutor.log")
    token = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{SB}/__token").read())["access_token"]
    # the test child's gender decides how the teacher addresses them
    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{SB}/rest/v1/kids_profiles?id=eq.{KID}", method="PATCH",
                           data=json.dumps({"gender": args.gender, "child_name": args.name or ("נועה" if args.gender == "female" else "איתי")}).encode(), headers={"Content-Type": "application/json"})).read()

    st, r = call("POST", "/api/english/session/start", {"kid_id": KID, "topic": args.topic, **({"level": args.level} if args.level else {})}, token)
    if st != 200:
        sys.exit(f"start failed: {st} {r}")
    sid = r["session_id"]
    print(f"\nשיחה חדשה · נושא: {r['topic']} · ילד{'ה' if args.gender == 'female' else ''} בדיקה")
    show(r["reply"], r)
    lines = Path(args.script).read_text().splitlines() if args.script else None
    while True:
        if lines is not None:
            if not lines:
                msg = "/end"
            else:
                msg = lines.pop(0); print(f"\n  את/ה: {msg}")
        else:
            try:
                msg = input("\n  את/ה: ").strip()
            except EOFError:
                msg = "/end"
        if not msg:
            continue
        if msg == "/quit":
            break
        if msg == "/allowance":
            print(" ", call("GET", f"/api/english/allowance?kid_id={KID}", token=token)[1]); continue
        if msg == "/end":
            st, r = call("POST", "/api/english/session/end", {"kid_id": KID, "session_id": sid}, token)
            s = r.get("summary", {})
            print(f"\n  סיכום: {s.get('minutes')} דק׳ · {s.get('turns')} תורות · רמה {s.get('level')}")
            print(f"  לזכור: {s.get('remember_en')}")
            print(f"  להורה: {s.get('parent_note')}")
            break
        st, r = call("POST", "/api/english/turn", {"kid_id": KID, "session_id": sid, "message": msg}, token)
        if st == 429:
            print("  ⏱ נגמרו הדקות להיום (429) — המורה לא נקרא, לא שולם כלום."); continue
        if st != 200:
            print(f"  שגיאה {st}: {r}"); continue
        show(r["reply"], r)
finally:
    stop()
