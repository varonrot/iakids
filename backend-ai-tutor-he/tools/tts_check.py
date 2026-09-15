#!/usr/bin/env python3
"""Synthesize one Hebrew sentence with the configured TTS provider and save it as WAV.

    cd backend-ai-tutor-he
    APP_ENV=prod TTS_PROVIDER=openrouter OPENROUTER_API_KEY=... ../backend/.venv/bin/python tools/tts_check.py
    APP_ENV=prod ../backend/.venv/bin/python tools/tts_check.py                      # direct Gemini (current default)
    ... tools/tts_check.py --text "טקסט אחר" --n 5                                   # 5 calls in parallel: latency + rate limit

Prints provider, latency, bytes, seconds of audio, and writes /var/log/iakids/tts-<provider>-<time>.wav
so you can listen and compare voice quality between providers. Costs one TTS call per --n.
"""
import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.chdir(Path(__file__).resolve().parent.parent)

ap = argparse.ArgumentParser()
ap.add_argument("--text", default="שלום! איזה כיף שבאת ללמוד היום. בואו נתחיל עם משהו מעניין.")
ap.add_argument("--n", type=int, default=1)
ap.add_argument("--outdir", default="/var/log/iakids")
args = ap.parse_args()

import main as tutor  # noqa: E402

print(f"provider={tutor.TTS_PROVIDER} model={'openrouter:' + tutor.OPENROUTER_TTS_MODEL if tutor.TTS_PROVIDER == 'openrouter' else 'gemini-3.1-flash-tts-preview (direct)'} voice={tutor.TTS_VOICE}")


def one(i):
    t = time.time()
    try:
        wav, dur = tutor.generate_tts_wav_bytes(args.text)
        return i, time.time() - t, wav, dur, None
    except Exception as e:
        return i, time.time() - t, b"", 0, f"{type(e).__name__}: {str(e)[:200]}"


with ThreadPoolExecutor(args.n) as ex:
    results = list(ex.map(one, range(args.n)))

Path(args.outdir).mkdir(parents=True, exist_ok=True)
for i, secs, wav, dur, err in results:
    if err:
        print(f"call {i}: FAILED after {secs:.1f}s -> {err}")
    else:
        print(f"call {i}: {secs:.1f}s latency, {len(wav)} bytes, {dur:.1f}s of audio")
ok = [r for r in results if not r[4]]
if ok:
    out = Path(args.outdir) / f"tts-{tutor.TTS_PROVIDER}-{time.strftime('%H%M%S')}.wav"
    out.write_bytes(ok[0][2])
    print("saved:", out, "| listen to compare providers")

# what the accounting recorded for these calls, and the exact cost when the provider reports one
rows = list(tutor.ai_costs._buf)
if rows:
    if tutor.TTS_PROVIDER == "openrouter":
        time.sleep(2)                      # the generation record is available a moment later
        import httpx
        for r in rows:
            gid = r.get("generation_id")
            if not gid:
                continue
            g = httpx.get(f"{tutor.OPENROUTER_BASE_URL}/generation", params={"id": gid},
                          headers={"Authorization": f"Bearer {tutor.OPENROUTER_API_KEY}"}, timeout=15)
            d = (g.json() or {}).get("data") or {}
            if d.get("total_cost") is not None:
                r["cost_usd"], r["cost_source"] = float(d["total_cost"]), "provider"
                r["extra"] = {k: d.get(k) for k in ("native_tokens_prompt", "native_tokens_completion", "provider_name") if d.get(k) is not None}
    print("\nai_calls rows (what will be written to the DB):")
    total = 0.0
    for r in rows:
        total += float(r.get("cost_usd") or 0)
        print(f"  {r['provider']:<11} {r['model']:<38} {r['purpose']:<8} {r['status']:<5} "
              f"{(r.get('audio_seconds') or 0):>5.1f}s audio  {(r.get('latency_ms') or 0):>6}ms  "
              f"cost ${r.get('cost_usd') if r.get('cost_usd') is not None else '?'} ({r['cost_source']})  {r.get('extra') or ''}")
    print(f"  total for this run: ${total:.6f}")
    try:
        n = tutor.ai_costs.flush()
        print(f"  written to ai_calls: {n} rows")
        pending = [r for r in rows if r.get("cost_source") == "pending"]
        if pending:
            time.sleep(3)
            done = tutor.ai_costs.resolve_pending_costs()
            print(f"  exact cost resolved in the DB for {done} of {len(pending)} pending rows (the worker resolves the rest within a minute)")
    except Exception as e:
        print(f"  NOT written to ai_calls ({type(e).__name__}: {str(e)[:120]}) -> apply supabase/migrations/20260914_ai_calls.sql")
sys.exit(0 if ok else 1)
