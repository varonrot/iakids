#!/usr/bin/env python3
"""End-to-end check of the media_jobs queue, with CPU / memory per phase.

    cd backend-ai-tutor-he
    APP_ENV=prod ../backend/.venv/bin/python tools/e2e_media_jobs.py --kid-id <id>                    # cached lesson
    APP_ENV=prod ../backend/.venv/bin/python tools/e2e_media_jobs.py --kid-id <id> --fresh            # generate a new lesson + media
    APP_ENV=prod ../backend/.venv/bin/python tools/e2e_media_jobs.py --kid-id <id> --fresh --kill-worker-once
    APP_ENV=prod ../backend/.venv/bin/python tools/e2e_media_jobs.py --kid-id <id> --load 20          # 20 concurrent cached opens

What it does, in order (every step prints what it saw):
  1. connects with the env's Supabase project and checks public.media_jobs exists
  2. finds the kid (by --kid name or --kid-id) and mints a login token for the parent
     (admin generate_link + verify_otp; no email is sent) so the call goes through
     the real route with real auth, exactly like the browser
  3. starts uvicorn and worker.py as child processes; a sampler thread records
     RSS + CPU% of both, system free memory and load, every 2s -> <logdir>/resources.csv
  4. picks a unit lesson: --unit-lesson, else --fresh = not generated yet,
     else one generated without audio, else any cached lesson (visual-repair job only)
  5. POSTs /api/tutor/unit-lesson like the workspace does (or --load N of them at once)
  6. watches media_jobs for that lesson (and the kid's intro-video job): pending -> running -> done
     --kill-worker-once: SIGKILLs the worker mid-job, restarts it; the reaper must hand the job back
  7. re-reads the lesson row and prints a per-phase table: seconds, peak RSS, avg/peak CPU
  8. stops both processes. Logs: server.log, worker.log, resources.csv, phases.log

Nothing here writes to the database except what the route and worker write anyway.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent          # backend-ai-tutor-he/
os.chdir(HERE)
sys.path.insert(0, str(HERE))

ap = argparse.ArgumentParser()
ap.add_argument("--kid", default=None, help="child_name substring; reversed order tried too (terminals flip Hebrew)")
ap.add_argument("--kid-id", default=None, help="kids_profiles.id")
ap.add_argument("--unit-lesson", type=int, default=None)
ap.add_argument("--fresh", action="store_true", help="pick a unit lesson that was never generated (lesson gen + full media)")
ap.add_argument("--load", type=int, default=0, help="fire N concurrent POSTs of the chosen lesson and report latencies")
ap.add_argument("--port", type=int, default=8765)
ap.add_argument("--logdir", default=os.environ.get("E2E_LOGDIR", "/var/log/iakids/e2e"))
ap.add_argument("--timeout", type=int, default=1500, help="seconds to wait for the jobs")
ap.add_argument("--concurrency", type=int, default=2, help="WORKER_CONCURRENCY for the worker")
ap.add_argument("--kill-worker-once", action="store_true")
args = ap.parse_args()

PY = sys.executable
RUN_ID = time.strftime("%Y%m%d-%H%M%S")
LOGDIR = Path(args.logdir) / RUN_ID
LOGDIR.mkdir(parents=True, exist_ok=True)
server_log = open(LOGDIR / "server.log", "ab")
worker_log = open(LOGDIR / "worker.log", "ab")
phases_log = open(LOGDIR / "phases.log", "a")
env = dict(os.environ, MEDIA_JOBS_MODE="queue", WORKER_CONCURRENCY=str(args.concurrency), WORKER_POLL_SECONDS="2",
           WORKER_HEARTBEAT_SECONDS="10", MEDIA_JOBS_STALE_SECONDS="60")

T0 = time.time()


def now():
    return time.strftime("%H:%M:%S")


def step(n, msg, **kv):
    line = f"\n[{n}] {now()} {msg} " + (json.dumps(kv, ensure_ascii=False, default=str) if kv else "")
    print(line, flush=True)
    phases_log.write(line + "\n"); phases_log.flush()


def note(msg):
    print("    " + msg, flush=True)
    phases_log.write(f"    {now()} {msg}\n"); phases_log.flush()


def tail(path, n=15):
    try:
        lines = Path(path).read_text(errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except FileNotFoundError:
        return "(no log yet)"


# ---------------------------------------------------------------- 1. connect
import main as tutor  # noqa: E402
from supabase import create_client  # noqa: E402

step(1, "connected", project=tutor.SUPABASE_URL, app_env=os.getenv("APP_ENV", "dev"), mode=tutor.MEDIA_JOBS_MODE, logdir=str(LOGDIR))
try:
    tutor.sb.table("media_jobs").select("id").limit(1).execute()
    note("media_jobs table: OK")
except Exception as e:
    note(f"media_jobs table MISSING on this project: {str(e)[:160]}")
    note("-> run supabase/migrations/20260914_media_jobs.sql in this project's SQL editor first")
    sys.exit(2)

# ---------------------------------------------------------------- 2. kid + token
if not args.kid and not args.kid_id:
    note("pass --kid <name> or --kid-id <id>"); sys.exit(2)
if args.kid_id:
    kids = tutor.sb.table("kids_profiles").select("id,user_id,child_name,age").eq("id", args.kid_id).execute().data
else:
    kids = []
    for name in (args.kid, args.kid[::-1]):
        kids = tutor.sb.table("kids_profiles").select("id,user_id,child_name,age").ilike("child_name", f"%{name}%").execute().data
        if kids:
            break
if not kids:
    sample = tutor.sb.table("kids_profiles").select("id,child_name").order("created_at", desc=True).limit(8).execute().data
    note(f"no kid matching {args.kid or args.kid_id!r} | some kids: {[(k['id'][:8], k['child_name']) for k in sample]}")
    sys.exit(2)

allp = tutor.sb.table("learning_lessons").select("id,grade,is_active").limit(5000).execute().data
grades_present = {int(p["grade"]) for p in allp if p.get("grade")}
usable = [k for k in kids if int(k.get("age") or 0) in grades_present]
note(f"matches: {[(k['id'][:8], k['child_name'], 'age', k.get('age')) for k in kids]} | lesson grades: {sorted(grades_present)}")
kid = (usable or kids)[0]
step(2, "kid chosen", kid=kid, can_open_lessons=bool(usable))

parent = tutor.sb.auth.admin.get_user_by_id(kid["user_id"]).user
link = tutor.sb.auth.admin.generate_link({"type": "magiclink", "email": parent.email})
tmp = create_client(tutor.SUPABASE_URL, tutor.SUPABASE_SERVICE_KEY)   # throw-away client keeps sb on service role
TOKEN = tmp.auth.verify_otp({"token_hash": link.properties.hashed_token, "type": "magiclink"}).session.access_token
note(f"parent: {parent.email} | token minted")

# ---------------------------------------------------------------- 3. processes + sampler
procs = {}


def start_server():
    procs["server"] = subprocess.Popen(
        [PY, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(args.port)],
        stdout=server_log, stderr=subprocess.STDOUT, env=env)


def start_worker():
    procs["worker"] = subprocess.Popen([PY, "worker.py"], stdout=worker_log, stderr=subprocess.STDOUT, env=env)


def stop_all():
    for p in procs.values():
        if p.poll() is None:
            p.send_signal(signal.SIGTERM)
    for p in procs.values():
        try:
            p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            p.kill()


CLK = os.sysconf("SC_CLK_TCK")
NCPU = os.cpu_count() or 1
samples = []          # (t, phase, server_rss, server_cpu, worker_rss, worker_cpu, free_mb, load1)
phase = ["startup"]
_last = {}


def _proc_stat(pid):
    """(rss_mb, cpu_seconds) from /proc, or None if the process is gone."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            parts = f.read().rsplit(")", 1)[1].split()
        cpu_s = (int(parts[11]) + int(parts[12])) / CLK
        with open(f"/proc/{pid}/statm") as f:
            rss_mb = int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") // (1024 * 1024)
        return rss_mb, cpu_s
    except (FileNotFoundError, ProcessLookupError, IndexError):
        return None


def _free_mb():
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    return -1


def _sampler():
    csv = open(LOGDIR / "resources.csv", "w")
    csv.write("t,phase,server_rss_mb,server_cpu_pct,worker_rss_mb,worker_cpu_pct,mem_available_mb,load1\n")
    while True:
        t = time.time()
        row = [round(t - T0, 1), phase[0]]
        for name in ("server", "worker"):
            p = procs.get(name)
            st = _proc_stat(p.pid) if p and p.poll() is None else None
            if st is None:
                row += [0, 0.0]; _last.pop(name, None); continue
            rss, cpu_s = st
            prev = _last.get(name)
            pct = 0.0 if not prev else round(100.0 * (cpu_s - prev[1]) / max(0.001, t - prev[0]), 1)
            _last[name] = (t, cpu_s)
            row += [rss, pct]
        row += [_free_mb(), round(os.getloadavg()[0], 2)]
        samples.append(tuple(row))
        csv.write(",".join(map(str, row)) + "\n"); csv.flush()
        time.sleep(2)


start_server(); start_worker()
threading.Thread(target=_sampler, daemon=True).start()
step(3, "started", server_pid=procs["server"].pid, worker_pid=procs["worker"].pid, worker_concurrency=args.concurrency, cpus=NCPU)
for _ in range(60):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{args.port}/", timeout=2).read()
        break
    except Exception:
        if procs["server"].poll() is not None:
            note("server died:\n" + tail(LOGDIR / "server.log", 30)); stop_all(); sys.exit(1)
        time.sleep(1)
else:
    note("server never answered:\n" + tail(LOGDIR / "server.log", 30)); stop_all(); sys.exit(1)
time.sleep(2.5)
note(f"health OK | RSS MB at start server/worker: {[(_proc_stat(procs[n].pid) or (0, 0))[0] for n in ('server', 'worker')]} | mem available {_free_mb()} MB")


def set_phase(name):
    phase[0] = name
    note(f"--- phase: {name}")


def phase_table():
    """Per phase: seconds, server/worker peak RSS and avg/peak CPU, min free memory."""
    by = {}
    for t, ph, srss, scpu, wrss, wcpu, free, load in samples:
        d = by.setdefault(ph, {"t0": t, "t1": t, "srss": 0, "scpu": [], "wrss": 0, "wcpu": [], "free": 10**9, "load": 0})
        d["t1"] = t; d["srss"] = max(d["srss"], srss); d["wrss"] = max(d["wrss"], wrss)
        d["scpu"].append(scpu); d["wcpu"].append(wcpu); d["free"] = min(d["free"], free); d["load"] = max(d["load"], load)
    print(f"\n    {'phase':<28}{'sec':>6} | {'srv RSS':>8}{'srv CPU avg/pk':>16} | {'wrk RSS':>8}{'wrk CPU avg/pk':>16} | {'min free':>9}{'load':>6}")
    for ph, d in by.items():
        sa = sum(d["scpu"]) / max(1, len(d["scpu"])); wa = sum(d["wcpu"]) / max(1, len(d["wcpu"]))
        line = (f"    {ph:<28}{d['t1'] - d['t0']:>6.0f} | {d['srss']:>6}MB {sa:>6.0f}%/{max(d['scpu']):>4.0f}% | "
                f"{d['wrss']:>6}MB {wa:>6.0f}%/{max(d['wcpu']):>4.0f}% | {d['free']:>7}MB {d['load']:>6}")
        print(line); phases_log.write(line + "\n")
    phases_log.flush()


# ---------------------------------------------------------------- 4. lesson
try:
    grade = int(kid.get("age") or 0)
    parent_ids = [p["id"] for p in allp if p.get("is_active") is not False and (not p.get("grade") or int(p["grade"]) == grade)]
    SEL = "id,unit_name,lesson_name,generation_status,audio_generation_status,lesson_audio_json,tts_generated_at,learning_lesson_id"

    def pick(q, label):
        rows = q.limit(1).execute().data
        if rows:
            note(f"lesson pick: {label}")
        return rows

    rows = []
    if args.unit_lesson:
        rows = [tutor.get_unit_lesson(args.unit_lesson)]
    elif parent_ids:
        base = lambda: tutor.sb.table("lesson_units_content").select(SEL).in_("learning_lesson_id", parent_ids)  # noqa: E731
        if args.fresh:
            rows = pick(base().or_("generation_status.is.null,generation_status.neq.ready").order("id"),
                        "NOT-YET-GENERATED lesson (full pipeline: lesson generation + audio + visuals)")
        if not rows:
            rows = pick(base().eq("generation_status", "ready").is_("lesson_audio_json", "null").order("id", desc=True),
                        "generated lesson without audio (audio job)")
        if not rows:
            rows = pick(base().eq("generation_status", "ready").order("id", desc=True),
                        "cached lesson (visual-repair job only; use --fresh for the full pipeline)")
    if not rows:
        grade_of = {p["id"]: p.get("grade") for p in allp}
        units = tutor.sb.table("lesson_units_content").select("id,learning_lesson_id,generation_status").limit(5000).execute().data
        note(f"lesson_units_content rows by grade: {dict(Counter(str(grade_of.get(u['learning_lesson_id'])) for u in units))}")
        siblings = tutor.sb.table("kids_profiles").select("id,child_name,age").eq("user_id", kid["user_id"]).execute().data
        note(f"kids on this parent account: {[(k['id'], k['child_name'], 'age', k.get('age')) for k in siblings]}")
        note("-> re-run with --kid-id of a kid whose age is a grade that has unit content")
        stop_all(); sys.exit(2)
    ul = rows[0]
    step(4, "unit lesson", id=ul["id"], unit=ul.get("unit_name"), lesson=ul.get("lesson_name"),
         generation_status=ul.get("generation_status"), audio_status=ul.get("audio_generation_status"),
         has_audio=bool(ul.get("lesson_audio_json")))
    keys = [f"unit_lesson:{ul['id']}", f"kid:{kid['id']}"]
    before_ids = {r["id"] for r in tutor.sb.table("media_jobs").select("id").in_("dedupe_key", keys).execute().data}

    # ------------------------------------------------------------ 5. the request(s)
    def post_lesson():
        body = json.dumps({"kid_id": kid["id"], "unit_lesson_id": int(ul["id"])}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{args.port}/api/tutor/unit-lesson", data=body, method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"})
        t = time.time()
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                return r.status, json.loads(r.read()), time.time() - t
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(errors="replace")[:300], time.time() - t
        except Exception as e:
            return 0, repr(e)[:300], time.time() - t

    set_phase("request:lesson-generation" if (args.fresh and ul.get("generation_status") != "ready") else "request:cached-open")
    t0 = time.time()
    if args.load > 1:
        with ThreadPoolExecutor(max_workers=args.load) as ex:
            results = list(ex.map(lambda _: post_lesson(), range(args.load)))
        lat = sorted(r[2] for r in results)
        codes = Counter(r[0] for r in results)
        step(5, f"{args.load} concurrent POST /api/tutor/unit-lesson", codes=dict(codes), wall_s=round(time.time() - t0, 1),
             p50_s=round(lat[len(lat) // 2], 2), p90_s=round(lat[int(len(lat) * .9)], 2), max_s=round(lat[-1], 2),
             req_per_s=round(args.load / (time.time() - t0), 1))
        code, resp, dt = results[0]
    else:
        code, resp, dt = post_lesson()
        step(5, "POST /api/tutor/unit-lesson", http=code, seconds=round(dt, 1),
             source=resp.get("source") if isinstance(resp, dict) else resp,
             generation_status=resp.get("generation_status") if isinstance(resp, dict) else None,
             audio_status=resp.get("audio_generation_status") if isinstance(resp, dict) else None)
    for line in tail(LOGDIR / "server.log", 400).splitlines():
        if any(k in line for k in ("MEDIA JOB", "SKIP BACKGROUND", "QUEUE KID", "LESSON GENERATION", "OPENAI", "gpt-")):
            note("server: " + line[:180])

    # ------------------------------------------------------------ 6. watch the queue
    set_phase("queue:waiting")
    step(6, "watching media_jobs", keys=keys, timeout_s=args.timeout)
    seen = {}
    killed = False
    deadline = time.time() + args.timeout
    final = None
    while time.time() < deadline:
        rows = (tutor.sb.table("media_jobs").select("id,job_type,status,attempts,locked_by,error,updated_at")
                .in_("dedupe_key", keys).order("id").execute().data)
        rows = [r for r in rows if r["id"] not in before_ids]
        running = [r for r in rows if r["status"] == "running"]
        if running:
            phase[0] = "worker:" + "+".join(sorted({r["job_type"] for r in running}))
        elif rows and all(r["status"] in ("done", "failed") for r in rows):
            phase[0] = "idle:after-jobs"
        for r in rows:
            sig = (r["status"], r["attempts"], r["locked_by"])
            if seen.get(r["id"]) != sig:
                seen[r["id"]] = sig
                note(f"job {r['id']} {r['job_type']:<22} {r['status']:<8} attempt {r['attempts']}  by {r['locked_by']}"
                     + (f"  error: {r['error'][:100]}" if r.get("error") else ""))
                if r["status"] == "running":
                    st = _proc_stat(procs["worker"].pid)
                    note(f"      worker RSS now {st[0] if st else '?'} MB | mem available {_free_mb()} MB | load {os.getloadavg()[0]:.2f}")
            if args.kill_worker_once and not killed and r["status"] == "running" and r["job_type"] != "kid_intro_videos":
                time.sleep(20)
                procs["worker"].kill(); procs["worker"].wait()
                note(f">>> worker SIGKILLed 20s into job {r['id']} ({r['job_type']}); restarting. Reaper should re-queue within ~60-120s")
                killed = True
                start_worker()
        if not rows and time.time() - t0 > 30:
            note("no job row appeared in 30s. Either the route skipped media (cache complete) or enqueue fell back to inline.")
            note("server log tail:\n" + tail(LOGDIR / "server.log", 25))
            break
        if rows and all(r["status"] in ("done", "failed") for r in rows):
            final = rows; break
        time.sleep(3)
    else:
        note("timed out waiting; worker log tail:\n" + tail(LOGDIR / "worker.log", 25))

    # ------------------------------------------------------------ 7. the lesson afterwards
    after = tutor.get_unit_lesson(ul["id"])
    step(7, "lesson after", generation_status=after.get("generation_status"), audio_status=after.get("audio_generation_status"),
         tts_generated_at=after.get("tts_generated_at"), has_audio=bool(after.get("lesson_audio_json")),
         audio_error=after.get("audio_generation_error"), generation_error=after.get("generation_error"))
    note("worker timeline:")
    for line in tail(LOGDIR / "worker.log", 500).splitlines():
        if "[worker" in line and any(k in line for k in ("start", "done", "failed", "reaper", "signal", "up ")):
            note("  " + line[:170])
    phase_table()
    if final:
        ok = all(r["status"] == "done" for r in final) and bool(after.get("lesson_audio_json"))
        print("\nRESULT:", "PASS" if ok else "FAIL", "| jobs:", [(r["id"], r["job_type"], r["status"], r["attempts"]) for r in final])
    else:
        print("\nRESULT: INCOMPLETE")
finally:
    stop_all()
    step(8, "stopped", logs=str(LOGDIR))
