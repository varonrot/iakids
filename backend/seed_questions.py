#!/usr/bin/env python3
"""
seed_questions.py — upload harvested questions into the bank as source='seed'.

Second half of the seeding path. games/tools/harvest.mjs runs each game's own
generator and writes the questions to JSON; this loads that file into
public.game_questions with the service role.

Why seeded rows are trusted on arrival: they are the output of the very
generators that already run in every child's browser, produced from the
repository on a machine you control, and they pass the same structural gate
verify_questions.py applies to client-written rows (imported from there, so the
two can never drift). That is a different provenance from an anon-key insert,
which is what the gate exists to catch. Pass --needs-review to load them as
'pending' anyway and put them through the semantic check as well:

    node ../games/tools/harvest.mjs --all --out /tmp/seed.json
    python3 seed_questions.py /tmp/seed.json --dry-run
    python3 seed_questions.py /tmp/seed.json
    python3 seed_questions.py /tmp/seed.json --needs-review   # then verify_questions.py

Existing rows are never overwritten: a question a child has already been asked
keeps its row, its counters and its verification state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

_env = os.getenv("APP_ENV", "dev")
_here = Path(__file__).resolve().parent
_envfile = _here / f".env.{_env}"
load_dotenv(_envfile if _envfile.exists() else _here / ".env")

from supabase import create_client  # noqa: E402

# One definition of "structurally acceptable", shared with the verifier.
sys.path.insert(0, str(_here))
from verify_questions import shape_of, structural_reject  # noqa: E402

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

BATCH = 200
HEBREW = re.compile(r"[֐-׿]")

MIN_SHAPE_SAMPLE = 20
SHAPE_MAJORITY = 0.6


def detect_lang(payload):
    """'he' if the question contains Hebrew, else 'en'. The column defaults to
    'he', which would mislabel every English game in the catalog."""
    return "he" if HEBREW.search(json.dumps(payload, ensure_ascii=False)) else "en"


def dominant_shapes(rows):
    """The shape each game's generator agrees on, learned from the harvest
    itself — the same rule verify_questions applies to the live corpus."""
    by_game = {}
    for row in rows:
        by_game.setdefault(row["game_code"], Counter())[shape_of(row["payload"])] += 1
    shapes = {}
    for game, counts in by_game.items():
        total = sum(counts.values())
        shape, n = counts.most_common(1)[0]
        shapes[game] = shape if total >= MIN_SHAPE_SAMPLE and n / total >= SHAPE_MAJORITY else None
    return shapes


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="JSON written by games/tools/harvest.mjs")
    ap.add_argument("--game", help="only this game_code")
    ap.add_argument("--limit", type=int, help="stop after this many rows")
    ap.add_argument("--needs-review", action="store_true",
                    help="load as pending so verify_questions.py must approve them")
    ap.add_argument("--dry-run", action="store_true", help="report, upload nothing")
    args = ap.parse_args()

    rows = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if args.game:
        rows = [r for r in rows if r["game_code"] == args.game]
    if not rows:
        sys.exit("nothing to upload")

    shapes = dominant_shapes(rows)

    accepted, rejected = [], Counter()
    for row in rows:
        why = structural_reject(row, shapes.get(row["game_code"]))
        if why:
            rejected[f"{row['game_code']}: {why.split(':')[0]}"] += 1
            continue
        accepted.append({
            "game_code": row["game_code"],
            "level": row.get("level") or 1,
            "lang": detect_lang(row["payload"]),
            "qkey": row["qkey"][:500],
            "payload": row["payload"],
            "answer": row.get("answer"),
            "source": "seed",
            "verify_state": "pending" if args.needs_review else "ok",
            "verified": not args.needs_review,
        })
        if args.limit and len(accepted) >= args.limit:
            break

    games = {r["game_code"] for r in accepted}
    state = "pending (needs review)" if args.needs_review else "ok (trusted)"
    print(f"[APP_ENV={_env}] {len(accepted)} row(s) from {len(games)} game(s) -> {state}")
    if rejected:
        print(f"  {sum(rejected.values())} rejected by the structural gate:")
        for reason, n in rejected.most_common(10):
            print(f"    {n:6}  {reason}")
        if len(rejected) > 10:
            print(f"    ... and {len(rejected) - 10} more kinds")

    if args.dry_run:
        print("dry run — nothing uploaded")
        return
    if not accepted:
        return

    # Checked here, not at startup: a dry run never opens a connection, so it
    # should work on a machine that has no credentials at all.
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        sys.exit(f"SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing — check .env.{_env} in {_here}")

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    done = 0
    for start in range(0, len(accepted), BATCH):
        batch = accepted[start:start + BATCH]
        try:
            # ignore_duplicates: a question a child has already met keeps its
            # row, its counters and whatever the verifier decided about it.
            (sb.table("game_questions")
               .upsert(batch, on_conflict="game_code,qkey", ignore_duplicates=True)
               .execute())
            done += len(batch)
            print(f"  uploaded {done}/{len(accepted)}", end="\r", flush=True)
        except Exception as exc:                        # noqa: BLE001
            print(f"\n  batch at {start} failed: {exc}")
    print(f"\n[APP_ENV={_env}] uploaded {done} row(s)")


if __name__ == "__main__":
    main()
