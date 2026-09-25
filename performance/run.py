#!/usr/bin/env python3
"""Performance test of every tutor API route: how many at once before it stops keeping up.

    backend/.venv/bin/python performance/run.py                    # fake DB + fake models, every route
    backend/.venv/bin/python performance/run.py --only tutor-chat,visuals
    backend/.venv/bin/python performance/run.py --scale 0.1        # 10x faster fake models: the server's own ceiling
    backend/.venv/bin/python performance/run.py --db prod --max-conc 32   # real prod DB, prod-safe routes only (asks first)

What happens
  1. Starts, on this box, a fake Supabase (or, with --db prod, a counting proxy to the real one),
     a fake model provider, and ITS OWN copy of the tutor (one uvicorn process, same flags as
     production) on --port. The live service on :8011 is never touched. Every key the copy
     gets is a dummy, so a call that escapes the fakes fails instead of costing money.
  2. Profile: each route once. Status, milliseconds, database calls, database writes, model
     calls. A route with no writes and no model calls is marked prod_safe.
  3. Ramp: each rampable route at 1, 4, 16, 64, 128, 256 connections (wrk), 10-15 s per step.
     Per step: requests/s, p50/p95/p99, errors, the copy's CPU% and RSS, and the event-loop lag
     (the latency of GET / measured alongside — a blocked loop shows up there first).
     The ramp stops at the first step that breaks a limit: errors > 1%, p95 over the route's
     budget, RSS over --rss-limit, or loop lag p95 over 500 ms.
  4. Writes results/<run>.json and results/<run>.md, and copies them to results/latest.*.
     The summary turns CPU ms per request into "children at once" with routes.CHILD_MIX_PER_MINUTE.

Read every number as a floor: the load generator, the fakes and the copy share this box's two
cores with the live service.
"""
import argparse
import json
import os
import re
import shutil
import signal
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TUTOR = ROOT / "backend-ai-tutor-he"
sys.path.insert(0, str(HERE))
from routes import CHILD_MIX_PER_MINUTE, ROUTES  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--db", choices=["fake", "prod"], default="fake")
ap.add_argument("--only", default="")
ap.add_argument("--scale", type=float, default=1.0, help="fake model delay multiplier (1 = production medians)")
ap.add_argument("--db-latency-ms", type=float, default=100.0)
ap.add_argument("--steps", default="1,4,16,64,128,256")
ap.add_argument("--seconds", type=int, default=10)
ap.add_argument("--max-conc", type=int, default=256)
ap.add_argument("--rss-limit", type=int, default=900, help="MB; the box has 2 GB shared with prod")
ap.add_argument("--port", type=int, default=8799)
ap.add_argument("--profile-only", action="store_true")
ap.add_argument("--label", default="")
ap.add_argument("--yes", action="store_true", help="--db prod: skip the confirmation prompt")
ap.add_argument("--workers", type=int, default=1, help="uvicorn worker processes (production runs 1)")
ap.add_argument("--cpus", default="", help="pin the tutor copy to these cores, e.g. 0 or 0-1 (taskset): 1 core vs 2 cores")
ap.add_argument("--tutor-dir", default="", help="run another checkout of backend-ai-tutor-he (e.g. a git worktree of the old code, for before/after)")
args = ap.parse_args()
if args.tutor_dir:
    TUTOR = Path(args.tutor_dir).resolve()

PY = str(ROOT / "backend" / ".venv" / "bin" / "python")
UVICORN = str(ROOT / "backend" / ".venv" / "bin" / "uvicorn")
RUN = time.strftime("%Y%m%d-%H%M%S") + (f"-{args.label}" if args.label else "") + f"-{args.db}"
if args.workers > 1 or args.cpus:
    RUN += f"-w{args.workers}" + (f"-cpu{args.cpus}" if args.cpus else "")
OUT = HERE / "results"
LOG = OUT / "logs" / RUN
LOG.mkdir(parents=True, exist_ok=True)
SB_PORT, MODEL_PORT = args.port - 8, args.port - 7
BASE = f"http://127.0.0.1:{args.port}"
LIVE = "http://127.0.0.1:8011/"
procs = {}


def say(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def http(method, url, body=None, headers=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read()
            return r.status, (time.perf_counter() - t0) * 1000, payload
    except urllib.error.HTTPError as e:
        return e.code, (time.perf_counter() - t0) * 1000, e.read()
    except Exception as e:
        return 0, (time.perf_counter() - t0) * 1000, repr(e).encode()


# ------------------------------------------------------------------ prod credentials (only for --db prod)
def prod_env():
    vals = {}
    for line in (ROOT / "backend-ai-tutor-he" / ".env.prod").read_text().splitlines():   # never from another checkout
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"')
    return vals


# ------------------------------------------------------------------ processes
def start(name, cmd, env=None, cwd=None):
    procs[name] = subprocess.Popen(cmd, stdout=open(LOG / f"{name}.log", "ab"), stderr=subprocess.STDOUT,
                                   env=env, cwd=cwd, start_new_session=True)


def wait_up(url, what, tries=60):
    for _ in range(tries):
        try:
            urllib.request.urlopen(url, timeout=2).read()
            return
        except urllib.error.HTTPError:
            return
        except Exception:
            time.sleep(0.5)
    stop_all()
    sys.exit(f"{what} never answered; see {LOG}")


def stop_all():
    for p in procs.values():
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGTERM)
    for p in procs.values():
        try:
            p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)


PROD = {}
if args.db == "prod":
    PROD = prod_env()
    if not args.yes:
        ans = input(f"--db prod: real load on the production database for a few minutes, prod-safe routes only, "
                    f"max {args.max_conc} at once. Type yes to go: ")
        if ans.strip() != "yes":
            sys.exit("not confirmed")

sb_cmd = [PY, str(HERE / "fake_supabase.py"), "--port", str(SB_PORT), "--latency-ms", str(args.db_latency_ms)]
if args.db == "prod":
    sb_cmd += ["--proxy", PROD["SUPABASE_URL"]]
start("supabase", sb_cmd)
start("models", [PY, str(HERE / "fake_models.py"), "--port", str(MODEL_PORT), "--scale", str(args.scale)])
wait_up(f"http://127.0.0.1:{SB_PORT}/__stats", "fake supabase")
wait_up(f"http://127.0.0.1:{MODEL_PORT}/__calls", "fake models")

env = dict(os.environ)
for k in list(env):
    if k.startswith(("OPENAI", "OPENROUTER", "GEMINI", "GOOGLE", "SUPABASE", "ANTHROPIC")):
        env.pop(k)
env.update({
    "APP_ENV": "perf",                         # there is no .env.perf: every value below wins over .env
    "SUPABASE_URL": f"http://127.0.0.1:{SB_PORT}",
    "SUPABASE_SERVICE_ROLE_KEY": PROD.get("SUPABASE_SERVICE_ROLE_KEY", "perf-service-key"),
    "SUPABASE_PUBLISHABLE_KEY": "perf-publishable",
    "OPENAI_API_KEY": "sk-perf-dummy", "GEMINI_API_KEY": "perf-dummy-gemini", "OPENROUTER_API_KEY": "sk-or-perf-dummy",
    "OPENROUTER_BASE_URL": f"http://127.0.0.1:{MODEL_PORT}/api/v1", "OPENAI_BASE_URL": f"http://127.0.0.1:{MODEL_PORT}/v1",
    "AI_PROVIDER": "openrouter", "TTS_PROVIDER": "openrouter", "STT_PROVIDER": "openai",
    "MEDIA_JOBS_MODE": "queue", "RATE_LIMIT_PER_MINUTE": "1000000",
    "ADMIN_EMAILS": "perf-test-parent@example.invalid",
    "ENGLISH_FREE_SECONDS_PER_DAY": "100000000", "ENGLISH_PAID_SECONDS_PER_DAY": "100000000",   # measure the server, not the allowance
    **({"SUPABASE_JWT_ISSUER": PROD["SUPABASE_URL"].rstrip("/") + "/auth/v1"} if args.db == "prod" else {}),
    "OPS_LOG_DIR": str(LOG), "PYTHONUNBUFFERED": "1",
    # production: never write cost or metrics rows from a test
    "AI_COSTS_ENABLED": "0" if args.db == "prod" else "1",
    "OPS_METRICS_ENABLED": "0" if args.db == "prod" else "1",
})
pin = ["taskset", "-c", args.cpus] if args.cpus else []
start("tutor", pin + [UVICORN, "main:app", "--workers", str(args.workers), "--host", "127.0.0.1", "--port", str(args.port), "--proxy-headers",
                 "--forwarded-allow-ips=127.0.0.1", "--timeout-keep-alive", "75", "--no-access-log"], env=env, cwd=str(TUTOR))
wait_up(BASE + "/", "tutor copy", tries=120)
TUTOR_PID = procs["tutor"].pid
say(f"run {RUN}: db={args.db} scale={args.scale} tutor copy pid {TUTOR_PID} on :{args.port}, logs {LOG}")

# ------------------------------------------------------------------ test identity
if args.db == "fake":
    TOKEN = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{SB_PORT}/__token").read())["access_token"]
    KID = "00000000-0000-4000-8000-00000000c001"
    seed = json.loads((HERE / "fixtures" / "seed.json").read_text())
    UL_ID, LL_ID = seed["lesson_units_content"][0]["id"], seed["lesson_units_content"][0]["learning_lesson_id"]
else:
    from prod_identity import make_identity, drop_identity  # noqa: E402  (performance/prod_identity.py)
    ident = make_identity(PROD)
    TOKEN, KID, UL_ID, LL_ID = ident["token"], ident["kid_id"], ident["unit_lesson_id"], ident["learning_lesson_id"]
AUTH = {"Authorization": f"Bearer {TOKEN}"}


STATE = {"english_session": ""}   # ids a route created in this run, for the routes that need them


def fill(x):
    if isinstance(x, str):
        return (x.replace("{kid}", KID).replace("{ul}", str(UL_ID)).replace("{ll}", str(LL_ID))
                .replace("{english_session}", STATE["english_session"]))
    if isinstance(x, dict):
        out = {k: fill(v) for k, v in x.items()}
        for k in ("unit_lesson_id", "lesson_id"):
            if isinstance(out.get(k), str) and out[k].isdigit():
                out[k] = int(out[k])
        return out
    return x


# ------------------------------------------------------------------ sampling
CLK = os.sysconf("SC_CLK_TCK")


def proc_cpu_rss(pid):
    with open(f"/proc/{pid}/stat") as f:
        parts = f.read().rsplit(")", 1)[1].split()
    cpu = (int(parts[11]) + int(parts[12])) / CLK
    with open(f"/proc/{pid}/status") as f:
        rss = next(int(l.split()[1]) // 1024 for l in f if l.startswith("VmRSS"))
    return cpu, rss


def tutor_pids():
    """uvicorn with one worker is one process; children are counted if there are any."""
    pids = [TUTOR_PID]
    try:
        pids += [int(p) for p in subprocess.check_output(["pgrep", "-P", str(TUTOR_PID)]).split()]
    except subprocess.CalledProcessError:
        pass
    return pids


def cpu_rss():
    c = r = 0
    for p in tutor_pids():
        try:
            a, b = proc_cpu_rss(p); c += a; r += b
        except Exception:
            pass
    return c, r


def sb_stats():
    return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{SB_PORT}/__stats").read())


def model_calls():
    return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{MODEL_PORT}/__calls").read())["n"]


class Sampler(threading.Thread):
    """RSS peak and event-loop lag (GET / every 200 ms) while a step runs."""

    def __init__(self):
        super().__init__(daemon=True)
        self.stop = threading.Event(); self.rss_peak = 0; self.lag = []; self.live = []

    def run(self):
        n = 0
        while not self.stop.is_set():
            self.rss_peak = max(self.rss_peak, cpu_rss()[1])
            st, ms, _ = http("GET", BASE + "/", timeout=30)
            self.lag.append(ms if st == 200 else 30000)
            if args.db == "prod" and n % 5 == 0:   # the live service, once a second
                st, ms, _ = http("GET", LIVE, timeout=10)
                self.live.append(ms if st == 200 else 10000)
            n += 1
            time.sleep(0.2)


def pct(xs, p):
    if not xs:
        return 0.0
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


# ------------------------------------------------------------------ profile
def _cold_writes(stats):
    return sum(v for k, v in stats["by"].items() if k.split()[0] in ("POST", "PATCH", "DELETE", "PUT")
               and "auth/v1" not in k and "object/sign" not in k and "object/list" not in k)


selected = [r for r in ROUTES if not args.only or r in args.only.split(",")]
if args.db == "prod":
    # production only ever sees routes the fake run proved read-only (no writes, no model calls)
    fake = HERE / "results" / "latest-fake.json"
    if not fake.exists():
        stop_all(); sys.exit("run the fake pass first: it decides which routes are safe for production")
    safe = {k for k, v in json.loads(fake.read_text())["routes"].items() if v.get("prod_safe")}
    selected = [r for r in selected if r in safe]
    say(f"prod: {len(selected)} prod-safe routes from the fake run: {', '.join(selected)}")
results = {"run": RUN, "db": args.db, "scale": args.scale, "workers": args.workers, "cpus": args.cpus or "all", "db_latency_ms": args.db_latency_ms, "routes": {},
           "box": {"cpus": os.cpu_count(), "mem_total_mb": int(open("/proc/meminfo").readline().split()[1]) // 1024}}

say(f"profile: {len(selected)} routes, one request each")
cpu0, rss_idle = cpu_rss()
results["box"]["tutor_rss_idle_mb"] = rss_idle
for name in selected:
    spec = ROUTES[name]
    # cold: the first request (caches empty); warm: the second, what a child polling the route costs
    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{SB_PORT}/__reset", method="POST")).read()
    st0, ms0, _ = http(spec["method"], BASE + fill(spec["path"]), fill(spec.get("body")), AUTH, timeout=180)
    cold = sb_stats()
    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{SB_PORT}/__reset", method="POST")).read()
    m0 = model_calls(); c0, _ = cpu_rss()
    st, ms, payload = http(spec["method"], BASE + fill(spec["path"]), fill(spec.get("body")), AUTH, timeout=180)
    s = sb_stats(); c1, _ = cpu_rss()
    if name == "english-start" and st == 200:
        STATE["english_session"] = json.loads(payload).get("session_id", "")
    # background flushes (request_log, ai_calls, service_metrics) are not the route's calls
    for k in [k for k in s["by"] if any(x in k for x in ("request_log", "ai_calls", "service_metrics"))]:
        s["calls"] -= s["by"].pop(k)
    for k in [k for k in cold["by"] if any(x in k for x in ("request_log", "ai_calls", "service_metrics"))]:
        cold["calls"] -= cold["by"].pop(k)
    writes = sum(v for k, v in s["by"].items() if k.split()[0] in ("POST", "PATCH", "DELETE", "PUT") and "rpc:" not in k
                 and "auth/v1" not in k and "object/sign" not in k and "object/list" not in k)
    rpc_writes = sum(v for k, v in s["by"].items() if "rpc:media_jobs_enqueue" in k)
    mc = model_calls() - m0
    results["routes"][name] = {
        "kind": spec["kind"], "status": st, "ms": round(ms, 1), "cpu_ms": round((c1 - c0) * 1000, 1),
        "db_calls": s["calls"], "db_calls_cold": cold["calls"], "db_by_cold": cold["by"], "db_ms": s["ms"], "db_by": s["by"], "db_writes": writes + rpc_writes, "model_calls": mc,
        # prod-safe = no writes and no model calls on the FIRST (cold) request as well as the warm one:
        # a new test child's first lesson open enqueues personal intro videos (real generation, real cost)
        "prod_safe": st < 500 and writes + rpc_writes == 0 and mc == 0 and _cold_writes(cold) == 0
                     and spec["kind"] in ("read", "health", "media"),
        "error": None if st < 400 else payload[:300].decode("utf-8", "replace"),
    }
    r = results["routes"][name]
    say(f"  {name:24} {st} {ms:8.0f} ms  cpu {r['cpu_ms']:6.1f} ms  db {s['calls']:2} warm / {cold['calls']:2} cold ({writes + rpc_writes} writes)  models {mc}"
        + (f"  ERR {r['error'][:90]}" if r["error"] else ""))


# ------------------------------------------------------------------ ramp
def lua_for(name, spec):
    body = fill(spec.get("body"))
    path = fill(spec["path"])
    lua = [f'wrk.method = "{spec["method"]}"', 'wrk.headers["Content-Type"] = "application/json"',
           f'wrk.headers["Authorization"] = "Bearer {TOKEN}"']
    if body is not None:
        lua.append("wrk.body = " + json.dumps(json.dumps(body, ensure_ascii=False), ensure_ascii=False))
    f = LOG / f"{name}.lua"
    f.write_text("\n".join(lua) + "\n", encoding="utf-8")
    return f, path


def parse_wrk(out):
    def ms(v, unit):
        return float(v) * {"us": 0.001, "ms": 1, "s": 1000, "m": 60000}[unit]
    lat = {p: ms(v, u) for p, v, u in re.findall(r"^\s+(50|75|90|99)%\s+([\d.]+)(us|ms|s|m)\s*$", out, re.M)}
    total = int(re.search(r"(\d+) requests in", out).group(1)) if re.search(r"(\d+) requests in", out) else 0
    non2xx = int(re.search(r"Non-2xx or 3xx responses: (\d+)", out).group(1)) if "Non-2xx" in out else 0
    sock = re.search(r"Socket errors: connect (\d+), read (\d+), write (\d+), timeout (\d+)", out)
    sock_err = sum(map(int, sock.groups())) if sock else 0
    rps = float(re.search(r"Requests/sec:\s+([\d.]+)", out).group(1)) if "Requests/sec" in out else 0.0
    p95 = lat.get("90", 0) + (lat.get("99", 0) - lat.get("90", 0)) * 5 / 9 if lat else 0
    return {"requests": total, "rps": rps, "p50": lat.get("50", 0), "p90": lat.get("90", 0), "p95": round(p95, 1),
            "p99": lat.get("99", 0), "errors": non2xx + sock_err, "non2xx": non2xx, "socket_errors": sock_err}


def ramp(name):
    spec = ROUTES[name]
    if "{english_session}" in json.dumps(spec, ensure_ascii=False):
        # the profile pass may have ended the session: every ramp of a session route gets a fresh one
        st, _, payload = http("POST", BASE + "/api/english/session/start", fill(ROUTES["english-start"]["body"]), AUTH, timeout=120)
        if st == 200:
            STATE["english_session"] = json.loads(payload).get("session_id", "")
    lua, path = lua_for(name, spec)
    steps = [int(x) for x in args.steps.split(",") if int(x) <= args.max_conc]
    secs = args.seconds if spec["kind"] not in ("model",) else max(args.seconds, 15)
    out, best, one_user_p50 = [], None, None
    for c in steps:
        smp = Sampler(); smp.start()
        c0, _ = cpu_rss(); t0 = time.time()
        p = subprocess.run(["wrk", f"-t{min(2, c)}", f"-c{c}", f"-d{secs}s", "--latency", "--timeout", "60s", "-s", str(lua), BASE + path],
                           capture_output=True, text=True)
        wall = time.time() - t0; c1, _ = cpu_rss()
        smp.stop.set(); smp.join(timeout=35)
        w = parse_wrk(p.stdout)
        w.update(conc=c, cpu_pct=round(100 * (c1 - c0) / wall, 1),
                 cpu_ms_per_req=round(1000 * (c1 - c0) / max(1, w["requests"]), 2),
                 rss_peak_mb=smp.rss_peak, loop_lag_p95_ms=round(pct(smp.lag, 95), 1), loop_lag_max_ms=round(max(smp.lag or [0]), 1))
        if smp.live:
            w["live_p95_ms"] = round(pct(smp.live, 95), 1)
        err_rate = w["errors"] / max(1, w["requests"])
        why = []
        if err_rate > 0.01: why.append(f"errors {err_rate:.0%}")
        # saturated = latency climbs well above what one user sees (queueing), not "slower than an absolute
        # number": a route with 8 sequential DB calls is slow at one user and that is not a capacity limit
        if one_user_p50 is None:
            one_user_p50 = w["p50"]
        limit_ms = max(spec["p95_ms"], 3 * one_user_p50)
        w["p95_limit_ms"] = round(limit_ms)
        if w["p95"] > limit_ms: why.append(f"p95 {w['p95']:.0f} > {limit_ms:.0f} ms (3x one-user p50 {one_user_p50:.0f})")
        if w["rss_peak_mb"] > args.rss_limit: why.append(f"RSS {w['rss_peak_mb']} MB > {args.rss_limit}")
        if w["loop_lag_p95_ms"] > 500: why.append(f"event loop blocked (lag p95 {w['loop_lag_p95_ms']:.0f} ms)")
        if w.get("live_p95_ms", 0) > 1000: why.append(f"LIVE service slowed ({w['live_p95_ms']:.0f} ms)")
        w["broke"] = why
        out.append(w)
        say(f"  {name:24} c={c:<4} {w['rps']:8.1f} req/s  p50 {w['p50']:7.0f}  p95 {w['p95']:7.0f} ms  err {w['errors']:4}  "
            f"cpu {w['cpu_pct']:5.1f}% ({w['cpu_ms_per_req']} ms/req)  rss {w['rss_peak_mb']} MB  lag p95 {w['loop_lag_p95_ms']:.0f} ms"
            + (f"  <- {', '.join(why)}" if why else ""))
        if why:
            if w.get("live_p95_ms", 0) > 1000:
                say("  live service slowed: stopping the whole run"); return out, best, True
            break
        best = w
        time.sleep(2)
    return out, best, False


abort = False
if not args.profile_only:
    for name in selected:
        spec = ROUTES[name]
        r = results["routes"][name]
        if spec.get("ramp") is False or spec["kind"] in ("admin",) or r["status"] >= 400:
            continue
        if args.db == "prod" and not r["prod_safe"]:
            continue
        say(f"ramp {name}")
        steps, best, abort = ramp(name)
        r["steps"] = steps
        r["max_ok_conc"] = best["conc"] if best else 0
        r["max_ok_rps"] = best["rps"] if best else 0
        r["cpu_ms_per_req"] = statistics.median([s["cpu_ms_per_req"] for s in steps if s["requests"] > 20] or [r["cpu_ms"]])
        r["limit"] = steps[-1]["broke"] if steps and steps[-1]["broke"] else ["not reached"]
        if abort:
            break

# ------------------------------------------------------------------ summary: children at once
cores = os.cpu_count() or 1
per_child_cpu_ms_min = 0.0
per_child_db_calls_min = 0.0
missing = []
for route, per_min in CHILD_MIX_PER_MINUTE.items():
    r = results["routes"].get(route)
    if not r:
        missing.append(route); continue
    per_child_cpu_ms_min += per_min * (r.get("cpu_ms_per_req") or r["cpu_ms"])
    per_child_db_calls_min += per_min * r["db_calls"]
summary = {
    "per_child_cpu_ms_per_min": round(per_child_cpu_ms_min, 1),
    "per_child_db_calls_per_min": round(per_child_db_calls_min, 1),
    # one uvicorn process uses one core; 70% target utilisation
    "children_per_process_cpu_bound": int(0.7 * 60000 / per_child_cpu_ms_min) if per_child_cpu_ms_min else None,
    "children_per_box_if_one_process_per_core": int(cores * 0.7 * 60000 / per_child_cpu_ms_min) if per_child_cpu_ms_min else None,
    "db_calls_per_sec_at_1000_children": round(per_child_db_calls_min * 1000 / 60, 1),
    "mix_routes_not_measured": missing,
}
results["summary"] = summary

stop_all()
if args.db == "prod":
    drop_identity(PROD, ident)

# ------------------------------------------------------------------ write
import hashlib  # noqa: E402
results["main_sha"] = hashlib.sha256((TUTOR / "main.py").read_bytes()).hexdigest()[:16]
results["tutor_dir"] = str(TUTOR)
(OUT / f"{RUN}.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
md = [f"# Performance run {RUN}", "",
      f"db={args.db}, fake model delay x{args.scale}, fake DB latency {args.db_latency_ms} ms, box {cores} CPUs / "
      f"{results['box']['mem_total_mb']} MB, tutor copy idle RSS {results['box']['tutor_rss_idle_mb']} MB", "",
      "| route | kind | status | 1 req ms | CPU ms/req | DB calls warm (cold) | DB writes | model calls | prod-safe | max OK conc | req/s there | what broke |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for name, r in results["routes"].items():
    md.append(f"| {name} | {r['kind']} | {r['status']} | {r['ms']:.0f} | {r.get('cpu_ms_per_req', r['cpu_ms'])} | {r['db_calls']} ({r['db_calls_cold']}) | "
              f"{r['db_writes']} | {r['model_calls']} | {'yes' if r['prod_safe'] else 'no'} | {r.get('max_ok_conc', '-')} | "
              f"{r.get('max_ok_rps', '-')} | {', '.join(r.get('limit', [])) or '-'} |")
md += ["", "## Children at once (this box)", ""] + [f"- **{k}**: {v}" for k, v in summary.items()]
(OUT / f"{RUN}.md").write_text("\n".join(md) + "\n")
if args.tutor_dir:
    say(f"wrote results/{RUN}.md (another checkout: latest-{args.db}.* left alone)")
else:
    # latest-<db>.json is the gate's reference: a partial run (--only) updates its routes, keeps the rest
    latest = OUT / f"latest-{args.db}.json"
    merged = json.loads(latest.read_text()) if latest.exists() else {"routes": {}}
    merged_routes = {**merged.get("routes", {}), **results["routes"]}
    merged.update({k: v for k, v in results.items() if k != "routes"})
    merged["routes"] = merged_routes
    latest.write_text(json.dumps(merged, ensure_ascii=False, indent=1))
    shutil.copy(OUT / f"{RUN}.md", OUT / f"latest-{args.db}.md")
    say(f"wrote results/{RUN}.md and updated results/latest-{args.db}.json ({len(merged_routes)} routes)")
print(json.dumps(summary, indent=1))
