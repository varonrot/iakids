#!/usr/bin/env python3
"""Before/after table from two run.py result files, plus the children-at-once model per machine size.

    python3 performance/compare.py results/<before>.json results/<after>.json [--prod results/<prod>.json] > results/REPORT-numbers.md

Children at once, from the measurements:
  per child a minute  = sum over routes.CHILD_MIX_PER_MINUTE of (requests/min x CPU ms per request)
  children per core   = 0.7 x 60,000 ms / per-child CPU ms a minute      (70 % target utilisation)
  children per box    = cores used by the web process(es) x children per core
  database calls/s    = children x per-child database calls a minute / 60
The CPU figure per request is the median over ramp steps with more than 20 requests (the
fixed cost of a request under load, including the HTTP server and logging).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from routes import CHILD_MIX_PER_MINUTE  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
before, after = (json.loads(Path(a).read_text()) for a in args[:2])
prod = json.loads(Path(sys.argv[sys.argv.index("--prod") + 1]).read_text()) if "--prod" in sys.argv else None


def best(r):
    """the last step that kept up"""
    ok = [s for s in r.get("steps", []) if not s.get("broke")]
    return ok[-1] if ok else None


def cpu_ms(r):
    return r.get("cpu_ms_per_req") or r.get("cpu_ms") or 0


def fmt(x, nd=0):
    if x is None or x == "-":
        return "-"
    return f"{x:,.{nd}f}"


def child_model(res):
    cpu = db = 0.0
    for route, per_min in CHILD_MIX_PER_MINUTE.items():
        r = res["routes"].get(route)
        if r:
            cpu += per_min * cpu_ms(r)
            db += per_min * r.get("db_calls", 0)
    return cpu, db


out = ["# Before / after, route by route", "",
       f"before: `{before['run']}`  |  after: `{after['run']}`  |  fake DB {after.get('db_latency_ms')} ms per call, "
       f"fake models at x{after.get('scale')} of production median delays", "",
       "| route | kind | max children at once (before → after) | req/s there | p50 / p95 ms there | CPU ms per request | RSS peak MB | DB calls per request (warm) | what stopped it (after) |",
       "|---|---|---|---|---|---|---|---|---|"]
for name, a in after["routes"].items():
    b = before["routes"].get(name)
    if not b or ("steps" not in a and "steps" not in b):
        continue
    bb, ab = best(b), best(a)
    stop = ", ".join(a.get("limit", [])) or "-"
    out.append(
        f"| {name} | {a['kind']} | {bb['conc'] if bb else 0} → **{ab['conc'] if ab else 0}** | "
        f"{fmt(bb and bb['rps'], 1)} → **{fmt(ab and ab['rps'], 1)}** | "
        f"{fmt(bb and bb['p50'])}/{fmt(bb and bb['p95'])} → {fmt(ab and ab['p50'])}/{fmt(ab and ab['p95'])} | "
        f"{fmt(cpu_ms(b), 1)} → **{fmt(cpu_ms(a), 1)}** | "
        f"{max([s['rss_peak_mb'] for s in b.get('steps', [])] or [0])} → {max([s['rss_peak_mb'] for s in a.get('steps', [])] or [0])} | "
        f"{b.get('db_calls')} → **{a.get('db_calls')}** | {stop} |")

cb, db_b = child_model(before)
ca, db_a = child_model(after)
out += ["", "# One child in a lesson", "",
        "| | before | after |", "|---|---|---|",
        f"| CPU per child per minute | {cb:,.0f} ms | **{ca:,.0f} ms** |",
        f"| database calls per child per minute | {db_b:,.1f} | **{db_a:,.1f}** |",
        f"| children per CPU core (70 % busy) | {0.7 * 60000 / cb:,.0f} | **{0.7 * 60000 / ca:,.0f}** |", ""]

# machine sizes: web processes = vCPUs - 1 (one core left for the media worker, nginx, the OS) with a floor of 1
SIZES = [  # slug, vCPU, RAM GB, $/month (DigitalOcean price page, 2026-09-25)
    ("s-2vcpu-2gb (today)", 2, 2, 18), ("s-2vcpu-4gb", 2, 4, 24), ("s-4vcpu-8gb", 4, 8, 48),
    ("c-4 (CPU-optimized)", 4, 8, 84), ("s-8vcpu-16gb", 8, 16, 96), ("c-8 (CPU-optimized)", 8, 16, 168),
    ("c-16 (CPU-optimized)", 16, 32, 336)]
rss = max([s["rss_peak_mb"] for r in after["routes"].values() for s in r.get("steps", [])] or [200])
out += ["# What each machine would hold (after the changes)", "",
        f"One uvicorn worker per core, one core kept for the media worker, nginx and the OS. Memory per worker "
        f"≈ {rss} MB peak (measured) + the media worker's ~200 MB (2026-09-14). CPU-bound figure; the database "
        f"limit is separate (below).", "",
        "| droplet | vCPU / RAM | $/month | web workers | RAM needed | children at once (CPU) | DB calls/s at that load |",
        "|---|---|---|---|---|---|---|"]
for slug, cpu, ram, usd in SIZES:
    workers = max(1, cpu - 1)
    need = workers * rss + 200 + 300
    kids = int(workers * 0.7 * 60000 / ca)
    fits = "" if need <= ram * 1024 * 0.8 else " ⚠ tight"
    out.append(f"| {slug} | {cpu} / {ram} GB | ${usd} | {workers} | {need / 1024:.1f} GB{fits} | **{kids:,}** | {kids * db_a / 60:,.0f} |")
out += ["", f"100,000 children at once would need about **{100000 / (0.7 * 60000 / ca):,.0f} busy cores** of web process "
        f"and **{100000 * db_a / 60:,.0f} database calls a second** at today's per-child call count.", ""]

if prod:
    out += ["# Production database (read-only routes, capped)", "",
            "| route | max at once | req/s | p50 / p95 ms | DB calls | live service p95 during step |", "|---|---|---|---|---|---|"]
    for name, r in prod["routes"].items():
        b = best(r)
        live = max([s.get("live_p95_ms", 0) for s in r.get("steps", [])] or [0])
        out.append(f"| {name} | {b['conc'] if b else 0} | {fmt(b and b['rps'], 1)} | {fmt(b and b['p50'])}/{fmt(b and b['p95'])} | "
                   f"{r.get('db_calls')} | {fmt(live)} |")
print("\n".join(out))
