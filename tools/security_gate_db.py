#!/usr/bin/env python3
"""Static gate for the database side of the 2026-09-26 security fixes.

    python3 tools/security_gate_db.py              # run the checks
    python3 tools/security_gate_db.py --self-test  # negative tests on scratch copies

`checks()` returns a list of failure messages (empty = pass). It reads
supabase/migrations/20260926_security_fixes.sql and its rollback and fails when a
statement that closes a hole is missing, so a later edit cannot quietly drop one.
Comments are stripped before matching: a statement that is only commented out counts
as missing.
"""
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "supabase" / "migrations" / "20260926_security_fixes.sql"
ROLLBACK = ROOT / "supabase" / "migrations" / "20260926_security_fixes_rollback.sql"
SCRATCH = Path("/tmp/claude-0/-opt-iakids/8abfa422-981e-41ae-9fc8-134796ea412a/scratchpad")

OWNER_TABLES = ["kids_profiles", "kid_tasks", "kid_custom_subjects", "kid_custom_units",
                "kid_custom_lessons", "homework_capture_sessions", "homework_sessions",
                "tutor_sessions"]

# (regex over the normalised SQL, what the child/parent would experience without it)
REQUIRED = [
    (r"revoke all on function public\.game_question_mark\(text, ?text, ?boolean\) from public, anon, authenticated;",
     "any account can call game_question_mark and skew every question's counters for every child (2026-09-26)"),
    (r"revoke all on function %s from public, anon, authenticated', f\.sig\)",
     "increment_usage_summary stays callable from a browser: anyone can inflate another parent's usage and cost (2026-09-26)"),
    (r"create trigger zz_support_tickets_guard before insert or update on public\.support_tickets",
     "a parent can open a ticket as 'closed'/'high' or reassign it to another account (2026-09-26)"),
    (r"create trigger zz_support_messages_guard before insert or update on public\.support_messages",
     "a parent can post a support message as 'admin' or into someone else's ticket (2026-09-26)"),
    (r"new\.sender_type := 'user';",
     "the messages trigger no longer forces sender_type='user': a parent can impersonate support (2026-09-26)"),
    (r"new\.user_id := auth\.uid\(\);",
     "the tickets trigger no longer pins user_id to the caller (2026-09-26)"),
    (r"check \(category in \('bug', 'billing', 'question', 'feature'\)\) not valid",
     "support_tickets.category accepts anything the browser sends (2026-09-26)"),
]
for table in ("kid_game_sessions", "kid_question_answers"):
    for cmd in ("insert", "update"):
        REQUIRED.append((
            rf"create policy sec_own_kid_{cmd} on public\.{table} as restrictive for {cmd} to anon, authenticated",
            f"a parent can {cmd} {table} rows for another family's child (2026-09-26)"))
for cmd in ("insert", "update", "delete"):
    REQUIRED.append((
        rf"create policy sec_owner_{cmd} on public\.%I as restrictive for {cmd} to anon, authenticated",
        f"the parent-owned tables lose their restrictive {cmd} ownership policy (2026-09-26)"))
for table in ("subscriptions", "usage_summary"):
    for cmd in ("update", "delete"):
        REQUIRED.append((
            rf"create policy sec_no_client_{cmd} on public\.{table} as restrictive for {cmd} to anon, authenticated using \(false\)",
            f"a browser can {cmd} {table} (a free account could give itself a paid plan or erase its usage) (2026-09-26)"))
REQUIRED.append((r"revoke insert, update, delete, truncate on public\.games_catalog from anon, authenticated;",
                 "any account can add, change or delete games in the catalogue every child sees (2026-09-26)"))

ROLLBACK_REQUIRED = [
    (r"drop trigger if exists zz_support_tickets_guard", "the rollback does not undo the support tickets trigger"),
    (r"drop policy if exists sec_own_kid_insert on public\.kid_game_sessions", "the rollback does not undo the game-result policies"),
    (r"drop policy if exists sec_no_client_update on public\.subscriptions", "the rollback does not undo the subscriptions policy"),
    (r"grant insert, update, delete, truncate on public\.games_catalog", "the rollback does not restore the games_catalog grants"),
]


def normalise(sql):
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    sql = re.sub(r"'\s*'", "", sql)            # join adjacent literals: 'a ' 'b' -> 'a b'
    return re.sub(r"\s+", " ", sql).strip().lower()


def checks(migration=MIGRATION, rollback=ROLLBACK):
    fails = []
    migration, rollback = Path(migration), Path(rollback)
    if not migration.is_file():
        return [f"security migration missing: {migration}"]
    sql = normalise(migration.read_text())
    for pattern, message in REQUIRED:
        if not re.search(pattern, sql, re.I):
            fails.append(f"{migration.name}: {message}")
    raw = migration.read_text()
    for table in OWNER_TABLES:
        if f"'{table}'" not in raw:
            fails.append(f"{migration.name}: {table} is no longer in the ownership-policy loop (2026-09-26)")

    if not rollback.is_file() or not normalise(rollback.read_text()):
        fails.append(f"{migration.name}: rollback missing or empty ({rollback.name})")
    else:
        if "REOPENS THE SECURITY HOLES" not in rollback.read_text()[:1500]:
            fails.append(f"{rollback.name}: the rollback does not say IN CAPITALS at the top that it reopens the security holes")
        rb = normalise(rollback.read_text())
        for pattern, message in ROLLBACK_REQUIRED:
            if not re.search(pattern, rb, re.I):
                fails.append(f"{rollback.name}: {message}")
        if re.search(r"^\s*drop\s+(table|column)\b", re.sub(r"--[^\n]*", "", rollback.read_text()), re.I | re.M):
            fails.append(f"{rollback.name}: a drop table/column is left ready to run (must be commented with -- DATA LOSS:)")
    return fails


def self_test():
    """Break a scratch copy in several ways; each must fail the gate."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="security_gate_db_", dir=SCRATCH))
    mig, rb = work / MIGRATION.name, work / ROLLBACK.name
    good_mig, good_rb = MIGRATION.read_text(), ROLLBACK.read_text()
    breaks = [
        ("revoke removed", "mig", "revoke all on function public.game_question_mark(text,text,boolean) from public, anon, authenticated;", ""),
        ("revoke commented out", "mig", "revoke all on function public.game_question_mark(text,text,boolean)", "-- revoke all on function public.game_question_mark(text,text,boolean)"),
        ("restrictive -> permissive", "mig", "create policy sec_own_kid_insert on public.kid_game_sessions\n    as restrictive", "create policy sec_own_kid_insert on public.kid_game_sessions\n    as permissive"),
        ("usage_summary update policy gone", "mig", "create policy sec_no_client_update on public.usage_summary", "create policy sec_x on public.usage_summary"),
        ("table dropped from owner loop", "mig", "'homework_sessions',", ""),
        ("sender_type not forced", "mig", "new.sender_type := 'user';", ""),
        ("rollback warning lowercased", "rb", "REOPENS THE SECURITY HOLES", "reopens some things"),
        ("rollback emptied", "rb", None, ""),
        ("rollback drops a table", "rb", "-- 6. games_catalog", "drop table public.support_messages;\n-- 6. games_catalog"),
    ]
    ok = True
    try:
        mig.write_text(good_mig); rb.write_text(good_rb)
        base = checks(mig, rb)
        if base:
            print("self-test: the unbroken copy already fails:", *base, sep="\n  "); return False
        for name, which, old, new in breaks:
            mig.write_text(good_mig); rb.write_text(good_rb)
            target, text = (mig, good_mig) if which == "mig" else (rb, good_rb)
            if old is None:
                target.write_text(new)
            else:
                assert old in text, f"self-test anchor not found: {old!r}"
                target.write_text(text.replace(old, new, 1))
            got = checks(mig, rb)
            print(f"  {'OK  ' if got else 'MISS'} {name}: {got[0] if got else 'gate did not fail'}")
            ok &= bool(got)
        rb.unlink()
        mig.write_text(good_mig)
        got = checks(mig, rb)
        print(f"  {'OK  ' if got else 'MISS'} rollback deleted: {got[0] if got else 'gate did not fail'}")
        ok &= bool(got)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return ok


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(0 if self_test() else 1)
    problems = checks()
    for p in problems:
        print("FAIL", p)
    print("security_gate_db: " + ("PASS" if not problems else f"{len(problems)} failure(s)"))
    sys.exit(1 if problems else 0)
