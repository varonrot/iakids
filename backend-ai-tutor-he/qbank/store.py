"""Where the question bank lives: the Supabase tables (supabase/migrations/20260925_qbank.sql) when they exist and
--db is given, otherwise local JSONL files under data/qbank/local/ (gitignored: items carry their answers, and
the repository is public). Curriculum topics are read from data/curriculum/*.json (reviewed copy in the repo).
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CURRICULUM = ROOT / "data" / "curriculum"
LOCAL = ROOT / "data" / "qbank" / "local"


def load_sources() -> dict:
    return {s["id"]: s for s in json.loads((HERE / "sources.json").read_text(encoding="utf-8"))["sources"]}


def load_topics() -> dict:
    """code -> topic {code, subject, subject_he, grade, strand, title_he, title_en, skills, meta, source_ref, inferred}."""
    out = {}
    for f in sorted(CURRICULUM.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for subj in data.get("subjects") or [data]:
            srcs = {s["id"]: s for s in subj.get("sources") or []}
            for g, topics in (subj.get("grades") or {}).items():
                for t in topics:
                    meta = {k: v for k, v in t.items() if k not in ("code", "strand", "title_he", "title_en", "skills", "source", "source_ref", "inferred")}
                    src = srcs.get(t.get("source")) or {}
                    out[t["code"]] = {"code": t["code"], "subject": subj["subject"], "subject_he": subj.get("subject_he", subj["subject"]),
                                      "grade": int(g), "strand": t.get("strand"), "title_he": t.get("title_he"), "title_en": t.get("title_en"),
                                      # grammar topics (English Grammar Band I) list their structures under "grammar"
                                      "skills": t.get("skills") or t.get("grammar") or [], "meta": meta, "source_url": src.get("url"), "source_title": src.get("title"),
                                      "source_ref": t.get("source_ref"), "inferred": bool(t.get("inferred")), "file": f.name}
    return out


# ------------------------------------------------------------------ local store
def _local_file(subject: str, grade: int) -> Path:
    return LOCAL / f"{subject}-g{grade}.jsonl"


def local_items() -> list:
    items = []
    for f in sorted(LOCAL.glob("*.jsonl")) if LOCAL.exists() else []:
        items += [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    return items


def save_local(items: list) -> int:
    LOCAL.mkdir(parents=True, exist_ok=True)
    have = {i["fingerprint"] for i in local_items()}
    n = 0
    for it in items:
        if it["fingerprint"] in have:
            continue
        with _local_file(it["subject"], it["grade"]).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
        have.add(it["fingerprint"]); n += 1
    return n


# ------------------------------------------------------------------ database
def db_client():
    from dotenv import load_dotenv
    from supabase import create_client
    load_dotenv(ROOT / f".env.{os.getenv('APP_ENV', 'dev')}")
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


ITEM_COLUMNS = ("id", "topic_code", "subject", "grade", "purpose", "format", "difficulty", "language", "stimulus", "stem", "options",
                "answer", "why_wrong", "explain", "origin", "source_id", "source_item_ref", "licence_class", "attribution",
                "generator", "verification", "fingerprint", "review_status")


def save_db(items: list, topics: dict, sources: dict) -> int:
    sb = db_client()
    sb.table("qbank_source").upsert([{k: s.get(k) for k in ("id", "title", "url", "licence", "licence_class", "attribution")}
                                     for s in sources.values()]).execute()
    codes = {i["topic_code"] for i in items}
    sb.table("curriculum_topics").upsert([{"code": t["code"], "subject": t["subject"], "grade": t["grade"], "strand": t["strand"],
                                            "title_he": t["title_he"], "title_en": t["title_en"], "skills": t["skills"],
                                            "meta": {**t["meta"], "source_url": t["source_url"]}, "source_id": "moe-curriculum",
                                            "source_ref": t["source_ref"], "inferred": t["inferred"]}
                                           for c, t in topics.items() if c in codes]).execute()
    rows = [{k: it.get(k) for k in ITEM_COLUMNS} for it in items]
    for r in rows:
        r["source_id"] = r.get("source_id") or "original"
        r["format"] = r.get("format") or "mcq4"
        r["licence_class"] = "A"
    if rows:
        sb.table("qbank_item").upsert(rows, on_conflict="fingerprint", ignore_duplicates=True).execute()
    return len(rows)
