#!/usr/bin/env python3
"""On-demand LESSON QUALITY GATE for one or more unit lessons (same checks the worker runs
after every media job): text rules, visuals vs segments, audio vs segments, storage
consistency, and (unless --no-images) a vision check that no stored image has readable text.

    cd backend-ai-tutor-he
    APP_ENV=prod AI_PROVIDER=openrouter TTS_PROVIDER=openrouter ../backend/.venv/bin/python tools/lesson_gate.py --lesson 29 [--lesson 30]
    ... --no-images      # skip the per-image vision calls (~$0.0003 each)
    ... --all-ready      # every lesson with generation_status=ready

Writes the report into generated_lesson_json["quality"]. Exit 1 if any lesson fails. A failed lesson is NOT withheld from children (product decision 2026-09-16): it is
flagged in generated_lesson_json.quality for the admin review screen; `--approve N` records a human approval.
"""
import argparse, os, sys, json
from pathlib import Path
os.chdir(Path(__file__).resolve().parent.parent); sys.path.insert(0, os.getcwd())
ap = argparse.ArgumentParser()
ap.add_argument("--lesson", type=int, action="append", default=[])
ap.add_argument("--all-ready", action="store_true")
ap.add_argument("--no-images", action="store_true")
ap.add_argument("--approve", type=int, action="append", default=[], help="release a needs_review lesson as ready (after a human looked at it)")
args = ap.parse_args()
import main  # noqa: E402
for lid in args.approve:
    row = main.sb.table("lesson_units_content").select("generation_status,generated_lesson_json").eq("id", lid).single().execute().data
    g = dict(row.get("generated_lesson_json") or {}); q = dict(g.get("quality") or {}); q["approved_by_human"] = True
    q["approved_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(); g["quality"] = q
    main.sb.table("lesson_units_content").update({"generated_lesson_json": g}).eq("id", lid).execute()
    print(f"lesson {lid}: quality.approved_by_human=True -> served again")
ids = list(args.lesson)
if args.all_ready:
    ids += [r["id"] for r in main.sb.table("lesson_units_content").select("id").eq("generation_status", "ready").execute().data]
if not ids:
    sys.exit(0 if args.approve else "give --lesson N, --all-ready or --approve N")
failed = 0
for lid in sorted(set(ids)):
    r = main.run_lesson_quality_gate(lid, check_images=not args.no_images)
    print(f"\n=== lesson {lid}: {'PASS' if r['ok'] else 'FAIL'}  stats={json.dumps(r['stats'], ensure_ascii=False)}")
    for e in r["errors"]: print("   ERROR  ", e)
    for w in r["warnings"][:10]: print("   warn   ", w)
    failed += 0 if r["ok"] else 1
print(f"\nLESSON GATE: {len(set(ids)) - failed} pass, {failed} fail")
sys.exit(1 if failed else 0)
