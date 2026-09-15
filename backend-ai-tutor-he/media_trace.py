"""Timeline logging for everything the child waits on (text, images, audio, video).

Two things, both zero-touch for existing code:

1. install_print_prefix()  -- every print() in this process gets a prefix
       12:34:56.789 [T+12.3s job=734 lesson=31 part=1] <original message>
   T+ is the time since the current job / request started (see trace_begin),
   so a journal or a worker log reads as a timeline without re-editing 196 prints.

2. stage(name, **fields)  -- context manager that logs
       STAGE START name {...}
       STAGE DONE  name {"took_s": 4.2, ...}      (or STAGE FAILED name {...})
   and keeps a per-job breakdown; summary(...) prints it at the end of a job:
       STAGE SUMMARY {"total_s": 176.1, "hero": 4.4, "visuals": 121.0, "audio": 155.2, "transition": 20.5}

Context (job id, lesson id, part, kid) lives in a contextvar, so it follows
run_in_context() into thread pools exactly like ai_costs' call context.
"""
import builtins
import contextvars
import threading
import time
from contextlib import contextmanager
from datetime import datetime

_TRACE: contextvars.ContextVar = contextvars.ContextVar("iakids_media_trace", default=None)
_ORIGINAL_PRINT = builtins.print
_LOCK = threading.Lock()


def trace_begin(**ctx):
    """Start a timeline: T+0 is now. Call at the start of a job or a request."""
    cur = {"t0": time.monotonic(), "stages": {}}
    cur.update({k: v for k, v in ctx.items() if v is not None})
    _TRACE.set(cur)
    return cur


def trace_set(**ctx):
    """Add / change context fields (e.g. part=2) without resetting T+0."""
    cur = dict(_TRACE.get() or trace_begin())
    cur.update({k: v for k, v in ctx.items() if v is not None})
    _TRACE.set(cur)
    return cur


def elapsed() -> float | None:
    cur = _TRACE.get()
    return round(time.monotonic() - cur["t0"], 1) if cur else None


def _prefix() -> str:
    now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    cur = _TRACE.get()
    if not cur:
        return f"{now} [--]"
    bits = [f"T+{time.monotonic() - cur['t0']:.1f}s"]
    for k in ("job", "req", "lesson", "part", "kid"):
        v = cur.get(k)
        if v not in (None, ""):
            bits.append(f"{k}={str(v)[:8] if k in ('kid', 'req') else v}")
    return f"{now} [{' '.join(bits)}]"


def _print_with_prefix(*args, **kwargs):
    kwargs.setdefault("flush", True)
    return _ORIGINAL_PRINT(_prefix(), *args, **kwargs)


def install_print_prefix():
    """Prefix every print() in this process (idempotent)."""
    if builtins.print is not _print_with_prefix:
        builtins.print = _print_with_prefix


@contextmanager
def stage(name: str, **fields):
    """Log START/DONE(+took_s)/FAILED for one step and record it in the job breakdown."""
    t = time.perf_counter()
    print(f"STAGE START {name}", fields if fields else "")
    try:
        yield
    except BaseException as e:
        took = round(time.perf_counter() - t, 1)
        _record(name, took)
        print(f"STAGE FAILED {name}", {**fields, "took_s": took, "error": f"{type(e).__name__}: {str(e)[:160]}"})
        raise
    took = round(time.perf_counter() - t, 1)
    _record(name, took)
    print(f"STAGE DONE {name}", {**fields, "took_s": took})


def _record(name: str, took: float):
    cur = _TRACE.get()
    if cur is None:
        return
    with _LOCK:
        stages = cur.setdefault("stages", {})
        stages[name] = round(stages.get(name, 0.0) + took, 1)


def summary(label: str = "STAGE SUMMARY", **extra):
    """Print the per-stage breakdown of the current job/request."""
    cur = _TRACE.get()
    if cur is None:
        return
    out = {"total_s": round(time.monotonic() - cur["t0"], 1)}
    out.update(cur.get("stages") or {})
    out.update(extra)
    print(label, out)
    return out


def waiting(what: str, **fields):
    """One line for 'the browser asked for X and this is what it got' — the user-side view."""
    print(f"USER WAIT {what}", fields)


# ---- small helpers for one-line START/DONE markers around existing statements ----
def mark_start(name: str, **fields) -> float:
    print(f"STAGE START {name}", fields if fields else "")
    return time.perf_counter()


def mark_done(name: str, t0: float, **fields):
    took = round(time.perf_counter() - t0, 1)
    _record(name, took)
    print(f"STAGE DONE {name}", {**fields, "took_s": took})


def staged(name: str, fn, *args, **kwargs):
    """Run fn inside stage(name) — for executor.submit(run_in_context(staged, 'audio', fn, id))."""
    with stage(name):
        return fn(*args, **kwargs)


def lesson_age_s(unit_lesson: dict | None) -> float | None:
    """Seconds since the lesson text was generated — how long the child may have been waiting for media."""
    try:
        ts = (unit_lesson or {}).get("generated_at")
        if not ts:
            return None
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        from datetime import timezone as _tz
        return round((datetime.now(_tz.utc) - dt).total_seconds(), 1)
    except Exception:
        return None
