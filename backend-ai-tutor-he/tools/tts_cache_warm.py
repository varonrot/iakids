#!/usr/bin/env python3
"""Warm the live-TTS cache for a few kids (their intro greeting + the shared closing line).

    cd backend-ai-tutor-he
    APP_ENV=prod AI_PROVIDER=openrouter TTS_PROVIDER=openrouter ../backend/.venv/bin/python tools/tts_cache_warm.py --kid-id <id> [--kid-id <id> ...]
    (use the SAME provider vars as the systemd unit — the cache key includes provider+model+voice)
    APP_ENV=prod ../backend/.venv/bin/python tools/tts_cache_warm.py --kid-id <id> --check    # only report hit/miss

Nothing is written except WAV files under lesson-audio/tts-cache/v1/. Costs one TTS call per missing text.
"""
import argparse, os, sys, time
from pathlib import Path
os.chdir(Path(__file__).resolve().parent.parent); sys.path.insert(0, os.getcwd())
ap = argparse.ArgumentParser()
ap.add_argument("--kid-id", action="append", required=True)
ap.add_argument("--check", action="store_true", help="report cache state only, synthesize nothing")
args = ap.parse_args()
import main  # noqa: E402  (loads env, clients, prompts)

def texts_for(kid: dict) -> list:
    name = str(kid.get("child_name") or "").strip()
    return [f"היי {name}! כיף שבאת ללמוד איתי.", "אז קדימה, בואו נתחיל!"]

for kid_id in args.kid_id:
    kid = main.sb.table("kids_profiles").select("id,child_name,gender").eq("id", kid_id).single().execute().data
    print(f"\n== {kid['child_name']} ({kid_id[:8]}) gender={kid.get('gender')}")
    for t in texts_for(kid):
        spoken = main.vocalize_for_tts(t); key = main.tts_cache_key(spoken)
        cached = main.tts_cache_get(key) is not None
        print(f"   {'HIT ' if cached else 'MISS'} {key[:12]}  {t}")
    if not args.check:
        t0 = time.time(); r = main.warm_tts_cache(texts_for(kid)); print(f"   warm -> {r} in {time.time()-t0:.1f}s")
