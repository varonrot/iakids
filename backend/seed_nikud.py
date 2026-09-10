#!/usr/bin/env python3
"""Upload the nikud dictionary to Supabase (table public.hebrew_nikud).

    APP_ENV=prod python3 backend/seed_nikud.py --dry-run
    APP_ENV=prod python3 backend/seed_nikud.py

Reads games/tools/nikud.full.js, the master every per-page nikud.js is cut from,
so the table and the shipped files can never drift. Words listed in games/tools/nikud-overrides.json
are marked reviewed=true, source='override': a person chose those readings.

Rows already present are updated only when the vocalisation changed; the letters
are re-checked here as well as by the table's own constraint.
"""
import argparse, json, os, re, sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
MARKS = re.compile('[֑-ׇ]')

_env = os.getenv("APP_ENV", "dev")
_here = Path(__file__).resolve().parent
_envfile = _here / f".env.{_env}"
load_dotenv(_envfile if _envfile.exists() else _here / ".env")


def read_dictionary():
    """Parse the `'word': 'vocalised',` lines out of games/nikud.js."""
    src = (ROOT / "games" / "tools" / "nikud.full.js").read_text(encoding="utf-8")
    pairs = re.findall(r"'([א-ת]+)':\s*'([^']+)'", src)
    if not pairs:
        sys.exit("games/tools/nikud.full.js: no entries found — run games/tools/nikud-build.py")
    return dict(pairs)


def read_overrides():
    p = ROOT / "games" / "tools" / "nikud-overrides.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except OSError:
        return set()
    return {k for k in d if not k.startswith("_")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, help="upload at most this many rows (a smoke test)")
    args = ap.parse_args()

    words = read_dictionary()
    reviewed = read_overrides()

    rows, bad = [], []
    for w, v in sorted(words.items()):
        if MARKS.sub("", v) != w:
            bad.append(w)
            continue
        rows.append({
            "word": w,
            "nikud": v,
            "source": "override" if w in reviewed else "nakdan",
            "reviewed": w in reviewed,
        })
    if args.limit:
        rows = rows[: args.limit]

    print(f"[nikud] {len(rows)} rows ready ({sum(r['reviewed'] for r in rows)} hand-reviewed)"
          f"{f', {len(bad)} rejected: letters changed' if bad else ''}")
    for w in bad:
        print(f"  rejected: {w} -> {words[w]}")
    if args.dry_run:
        print("[nikud] dry run — nothing written")
        return

    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (APP_ENV=%s)" % _env)
    sb = create_client(url, key)

    done = 0
    for i in range(0, len(rows), 200):
        chunk = rows[i : i + 200]
        sb.table("hebrew_nikud").upsert(chunk, on_conflict="word").execute()
        done += len(chunk)
        print(f"  uploaded {done}/{len(rows)}")
    print("[nikud] done")


if __name__ == "__main__":
    main()
