#!/usr/bin/env python3
"""iakids Hebrew tutor — media job worker.

    cd backend-ai-tutor-he
    APP_ENV=dev  ../backend/.venv/bin/python worker.py      # local, against the dev project
    APP_ENV=prod python worker.py                            # Render "Background Worker" start command

Pulls rows from public.media_jobs (see supabase/migrations/20260914_media_jobs.sql)
and runs the same functions the web process used to run through BackgroundTasks:
intro videos, lesson visuals, TTS audio. The web process only inserts rows now.

Why a separate process: a deploy or crash of the web server no longer loses media
that was half-generated, a five-minute video poll no longer holds a web thread,
and adding capacity means starting another copy of this file — several workers
never take the same job (SKIP LOCKED in media_jobs_claim).

Lifecycle of a row
    pending  --claim-->  running  --finish ok-->  done
                            |--finish error, attempts left-->  pending (run_after = now + backoff)
                            |--finish error, no attempts-->    failed
                            '--no heartbeat for MEDIA_JOBS_STALE_SECONDS-->  pending / failed (reaper)

Environment (all optional)
    WORKER_CONCURRENCY          jobs run at once in this process        default 2
    WORKER_POLL_SECONDS         sleep when the queue is empty           default 3
    WORKER_HEARTBEAT_SECONDS    how often a running job says "alive"    default 30
    MEDIA_JOBS_STALE_SECONDS    reaper threshold; must exceed heartbeat default 300
    WORKER_ID                   name in locked_by; default host:pid

SIGTERM / Ctrl-C: stop claiming, let running jobs finish, then exit. Render sends
SIGTERM on deploy and waits; a job that does not finish in time is re-queued by the
reaper once its heartbeat goes stale, so nothing is lost either way.
"""
import os
import signal
import socket
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

# Importing main builds the FastAPI app and the Supabase/OpenAI/Gemini clients, and
# reads the prompts from ./prompts — so run from backend-ai-tutor-he/. It starts no
# server: uvicorn is what serves `app`, and uvicorn is not involved here.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Logs go to a file on Render and in the test tools; block buffering would lose the
# last minutes of output when the process is killed. Line-buffer them.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(line_buffering=True)
    except Exception:
        pass
import main as tutor  # noqa: E402
import media_trace
media_trace.install_print_prefix()   # every print() -> timestamp + T+elapsed + job/lesson context

# 2026-09-17: production runs one job at a time (WORKER_CONCURRENCY=1 in the unit file)
# because the box has 2 vCPU and 2 GB, and a second image job in parallel pushed it into
# swap. The default now says what we actually run.
CONCURRENCY = max(1, int(os.getenv("WORKER_CONCURRENCY", "1")))
POLL_SECONDS = max(1.0, float(os.getenv("WORKER_POLL_SECONDS", "3")))
HEARTBEAT_SECONDS = max(5.0, float(os.getenv("WORKER_HEARTBEAT_SECONDS", "30")))
STALE_SECONDS = max(60, int(os.getenv("MEDIA_JOBS_STALE_SECONDS", "300")))
WORKER_ID = os.getenv("WORKER_ID") or f"{socket.gethostname()}:{os.getpid()}"
REAPER_EVERY_SECONDS = 60

_stop = threading.Event()
_state = {"running": 0}

# service_metrics rows every 30s: RSS, CPU, jobs running, queue depth (ops_metrics.py)
from ops_metrics import OpsReporter, _self_stat, _mem_available_mb as _mem_available  # noqa: E402

ops = OpsReporter(tutor.sb, service="tutor-worker", instance=WORKER_ID)
ops.gauges["jobs_running"] = lambda: _state["running"]
ops.gauges["queue_pending"] = lambda: (
    tutor.sb.table("media_jobs").select("id", count="exact", head=True).eq("status", "pending").execute().count)
ops.gauges["concurrency"] = lambda: CONCURRENCY
tutor.ai_costs.service = "tutor-worker"          # ai_calls rows from here are the worker's
tutor.ai_costs.instance = WORKER_ID

# ai_calls.purpose for each job type
JOB_PURPOSE = {
    "kid_intro_videos": "video",
    "unit_lesson_audio": "tts",
    "unit_lesson_visuals": "image",
    "unit_lesson_media": "media",
    "unit_lesson_transition": "transition",
}


def _log(event: str, **fields):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{ts} [worker {WORKER_ID}] {event}", fields if fields else "", flush=True)


def _rpc(name: str, params: dict, label: str):
    return tutor.supabase_with_retry(
        lambda: tutor.sb.rpc(name, params).execute(),
        label=label
    )


def claim(limit: int) -> list:
    res = _rpc("media_jobs_claim", {"p_worker": WORKER_ID, "p_limit": limit}, "MEDIA JOB CLAIM")
    return list(res.data or [])


def heartbeat(job_id: int):
    _rpc("media_jobs_heartbeat", {"p_id": job_id, "p_worker": WORKER_ID}, "MEDIA JOB HEARTBEAT")


def finish(job_id: int, ok: bool, error: str | None = None, metrics: dict | None = None):
    _rpc("media_jobs_finish", {
        "p_id": job_id, "p_worker": WORKER_ID, "p_ok": ok,
        "p_error": error, "p_retry_delay_seconds": 60, "p_metrics": metrics,
    }, "MEDIA JOB FINISH")


def requeue_stale() -> int:
    res = _rpc("media_jobs_requeue_stale", {"p_stale_seconds": STALE_SECONDS}, "MEDIA JOB REAPER")
    return int(res.data or 0)


def run_job(job: dict):
    """One job, start to finish, on a pool thread. Heartbeats from a side thread."""
    job_id = int(job["id"])
    job_type = job["job_type"]
    payload = job.get("payload") or {}
    done = threading.Event()
    rss_start = _self_stat()[0] or 0
    peak = {"rss": rss_start}

    def beat():
        # heartbeat every HEARTBEAT_SECONDS; RSS sampled every 2s so the job's peak is known
        n = 0
        while not done.wait(2):
            peak["rss"] = max(peak["rss"], _self_stat()[0] or 0)
            n += 2
            if n >= HEARTBEAT_SECONDS:
                n = 0
                try:
                    heartbeat(job_id)
                except Exception as e:                   # a missed beat is not fatal
                    _log("heartbeat failed", job_id=job_id, error=repr(e))

    threading.Thread(target=beat, name=f"hb-{job_id}", daemon=True).start()
    started = time.time()
    _state["running"] += 1
    # every model call made by this job carries the job's purpose / kid / lesson
    tutor.set_call_context(
        purpose=JOB_PURPOSE.get(job_type, job_type),
        kid_id=payload.get("kid_id"), user_id=payload.get("user_id"),
        unit_lesson_id=payload.get("unit_lesson_id"), job_id=job_id,
    )
    media_trace.trace_begin(job=job_id, lesson=payload.get("unit_lesson_id"), kid=payload.get("kid_id"))
    _log("start", job_id=job_id, job_type=job_type, attempt=job.get("attempts"), payload=payload,
         rss_mb=rss_start, mem_available_mb=_mem_available())

    def metrics():
        return {"seconds": round(time.time() - started, 1), "rss_start_mb": rss_start,
                "rss_peak_mb": max(peak["rss"], _self_stat()[0] or 0), "attempt": job.get("attempts"),
                "concurrency": CONCURRENCY, "jobs_running": _state["running"], "worker": WORKER_ID}

    try:
        tutor.run_media_job(job_type, payload)
        done.set()
        m = metrics()
        _state["running"] -= 1
        stages = media_trace.summary("STAGE SUMMARY (job ok)") or {}
        m["stages"] = stages
        finish(job_id, ok=True, metrics=m)
        _log("done", job_id=job_id, job_type=job_type, **m)
    except Exception as e:
        done.set()
        m = metrics()
        _state["running"] -= 1
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-3000:]}"
        media_trace.summary("STAGE SUMMARY (job failed)")
        _log("failed", job_id=job_id, job_type=job_type, error=f"{type(e).__name__}: {e}", **m)
        try:
            finish(job_id, ok=False, error=err, metrics=m)
        except Exception as fe:
            # Can't report the failure: the reaper will re-queue it once the
            # heartbeat goes stale, which is the right outcome anyway.
            _log("finish() failed after job error", job_id=job_id, error=repr(fe))


def main_loop():
    _log("up", concurrency=CONCURRENCY, poll=POLL_SECONDS, stale=STALE_SECONDS,
         mode=tutor.MEDIA_JOBS_MODE, app_env=os.getenv("APP_ENV", "dev"))
    if tutor.MEDIA_JOBS_MODE == "inline":
        _log("note: web process has MEDIA_JOBS_MODE=inline; this worker will only see rows enqueued elsewhere")
    ops.start()
    tutor.ai_costs.start()

    last_reap = 0.0
    with ThreadPoolExecutor(max_workers=CONCURRENCY, thread_name_prefix="job") as pool:
        running = set()
        while not _stop.is_set():
            # finished futures leave the set; exceptions were handled inside run_job
            running = {f for f in running if not f.done()}

            if time.time() - last_reap > REAPER_EVERY_SECONDS:
                last_reap = time.time()
                try:
                    n = requeue_stale()
                    if n:
                        _log("reaper re-queued stale jobs", count=n)
                except Exception as e:
                    _log("reaper failed", error=repr(e))

            free = CONCURRENCY - len(running)
            jobs = []
            if free > 0:
                try:
                    jobs = claim(free)
                except Exception as e:
                    _log("claim failed", error=repr(e))
                    _stop.wait(POLL_SECONDS)
                    continue

            for job in jobs:
                running.add(pool.submit(run_job, job))

            if not jobs:
                if running:
                    wait(running, timeout=POLL_SECONDS, return_when=FIRST_COMPLETED)
                else:
                    _stop.wait(POLL_SECONDS)

        if running:
            _log("stopping: waiting for running jobs", count=len(running))
            wait(running)
    _log("down")


def _on_signal(signum, _frame):
    _log("signal received, finishing current jobs", signal=signum)
    _stop.set()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    main_loop()
