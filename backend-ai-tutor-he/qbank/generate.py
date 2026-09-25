#!/usr/bin/env python3
"""Write ORIGINAL questions for a curriculum topic, verify them, and put them in the review queue.

    cd backend-ai-tutor-he
    ../backend/.venv/bin/python -m qbank.generate --topic MATH-3-02 --n 6
    ../backend/.venv/bin/python -m qbank.generate --subject math --grade 3 --n 4          # every topic of the grade
    ../backend/.venv/bin/python -m qbank.generate --topic SCI-4-03 --n 5 --purpose exam_prep --db

Pipeline, per topic:
  1. the writer model (QBANK_GEN_MODEL) writes n items from the topic, its skills and the project's Hebrew rules
     (qbank/prompts/generate_item.txt); never from remembered test items;
  2. qbank.validate: shape, distractor explanations, reading load, Hebrew, key leak, maths solution_expr;
  3. a second model of another family (QBANK_SOLVER_MODEL) solves it WITHOUT the key; a different answer, low
     confidence or a reported problem = the item is dropped (the reason is printed);
  4. copy risk against everything already in the bank and data/qbank/blocked_shingles.json (fingerprints of
     texts we must not reproduce; the texts themselves are never stored);
  5. survivors are saved as review_status 'pending' (local JSONL, or the qbank tables with --db).
Nothing reaches a child until a person approves it. Every run prints its spend (the OpenRouter account is shared
with production).
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from qbank import llm, store
from qbank import validate as v

HERE = Path(__file__).resolve().parent
GEN_PROMPT = (HERE / "prompts" / "generate_item.txt").read_text(encoding="utf-8")
SOLVE_PROMPT = (HERE / "prompts" / "solve_item.txt").read_text(encoding="utf-8")
GRADE_HE = {1: "כיתה א", 2: "כיתה ב", 3: "כיתה ג", 4: "כיתה ד", 5: "כיתה ה", 6: "כיתה ו"}
PURPOSE_HE = {"practice": "תרגול", "exam_prep": "הכנה למבחן בכיתה", "gifted": "היכרות עם מבחן המחוננים"}
BLOCKED = HERE.parent / "data" / "qbank" / "blocked_shingles.json"


class WrongWhy(BaseModel):
    option: Literal["0", "1", "2", "3"]
    why: str


class Draft(BaseModel):
    stimulus: str
    stem: str
    options: list[str]
    answer: int
    why_wrong: list[WrongWhy]
    explain: str
    difficulty: int
    solution_expr: str


class DraftSet(BaseModel):
    items: list[Draft]


class Solved(BaseModel):
    answer: int
    confident: bool
    problem: str


def render_prompt(topic: dict, n: int, purpose: str) -> str:
    extra = []
    for k in ("number_range", "key_terms", "grammar", "vocab_sample", "passages", "band"):
        if topic["meta"].get(k):
            extra.append(f"- {k.replace('_', ' ')}: {topic['meta'][k]}")
    return (GEN_PROMPT.replace("{grade}", str(topic["grade"])).replace("{grade_he}", GRADE_HE[topic["grade"]])
            .replace("{subject_he}", topic["subject_he"]).replace("{purpose_he}", PURPOSE_HE[purpose])
            .replace("{topic_code}", topic["code"]).replace("{topic_title}", topic["title_he"] or "")
            .replace("{strand}", topic.get("strand") or "").replace("{skills}", "; ".join(topic["skills"]))
            .replace("{topic_extra}", "\n".join(extra)).replace("{stem_max}", str(v.STEM_MAX_WORDS[topic["grade"]]))
            .replace("{n}", str(n)))


def to_item(d: Draft, topic: dict, purpose: str) -> dict:
    item = {"topic_code": topic["code"], "subject": topic["subject"], "grade": topic["grade"], "purpose": purpose,
            "format": "mcq4", "difficulty": d.difficulty, "language": "en" if topic["subject"] == "english" and False else "he",
            "stimulus": d.stimulus.strip() or None, "stem": d.stem.strip(), "options": [o.strip() for o in d.options],
            "answer": d.answer, "why_wrong": {w.option: w.why.strip() for w in d.why_wrong}, "explain": d.explain.strip(),
            "origin": "original_llm", "source_id": "original", "solution_expr": d.solution_expr.strip() or None,
            "review_status": "pending"}
    item["fingerprint"] = v.fingerprint(item)
    item["id"] = f"{topic['code']}-{item['fingerprint'][:8]}"
    item["generator"] = {"model": llm.GEN_MODEL, "prompt": "qbank/prompts/generate_item.txt", "at": time.strftime("%Y-%m-%d")}
    return item


def blind_solve(item: dict) -> dict:
    q = ((f"Passage:\n{item['stimulus']}\n\n" if item.get("stimulus") else "") + f"Question:\n{item['stem']}\n\nOptions:\n" +
         "\n".join(f"{i}. {o}" for i, o in enumerate(item["options"])))
    s = llm.parse(llm.SOLVER_MODEL, SOLVE_PROMPT.replace("{grade}", str(item["grade"])), q, Solved)
    return {"model": llm.SOLVER_MODEL, "answer": s.answer if s else None, "confident": bool(s and s.confident),
            "problem": (s.problem if s else "no answer")}


def corpus() -> dict:
    c = {f"bank item {i['id']}": v.item_shingles(i) for i in store.local_items()}
    if BLOCKED.exists():
        for name, sh in json.loads(BLOCKED.read_text(encoding="utf-8")).items():
            c[f"blocked text {name}"] = set(sh)
    return c


def run_topic(topic: dict, n: int, purpose: str, sources: dict, known: dict) -> tuple[list, list]:
    drafts = llm.parse(llm.GEN_MODEL, render_prompt(topic, n, purpose),
                       f"Topic {topic['code']}: write {n} questions.", DraftSet)
    kept, dropped = [], []
    for d in (drafts.items if drafts else []):
        item = to_item(d, topic, purpose)
        problems = v.validate_item(item, topic=topic, sources=sources)
        if not problems:
            sol = blind_solve(item)
            item["verification"] = sol
            if sol["answer"] != item["answer"]:
                problems.append(f"{item['id']}: the blind solver chose option {sol['answer']}, the key is {item['answer']} ({sol['problem'] or 'no reason'})")
            elif not sol["confident"] or sol["problem"].strip():
                problems.append(f"{item['id']}: the blind solver agrees but reports: {sol['problem'] or 'not confident'}")
        if not problems:
            problems += v.copy_risk(item, known)
        if problems:
            dropped.append((item, problems))
        else:
            kept.append(item)
            known[f"bank item {item['id']}"] = v.item_shingles(item)
    return kept, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", action="append", default=[])
    ap.add_argument("--subject")
    ap.add_argument("--grade", type=int)
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--purpose", choices=sorted(v.PURPOSES), default="practice")
    ap.add_argument("--db", action="store_true", help="write to the qbank tables (needs the migration) instead of local files")
    ap.add_argument("--max-usd", type=float, default=2.0, help="stop before a run would pass this spend")
    ap.add_argument("--show", action="store_true", help="print every kept item")
    a = ap.parse_args()
    topics, sources = store.load_topics(), store.load_sources()
    chosen = [topics[c] for c in a.topic if c in topics] or \
        [t for t in topics.values() if t["subject"] == a.subject and t["grade"] == a.grade]
    missing = [c for c in a.topic if c not in topics]
    if missing:
        sys.exit(f"unknown topic codes {missing} (data/curriculum/*.json)")
    if not chosen:
        sys.exit("no topics chosen: --topic CODE, or --subject and --grade")
    if a.purpose == "gifted":
        sys.exit("gifted items are written into data/checks/gifted.json by hand + tools/bank_solver.py, not by this tool yet")
    left = llm.credits_left()
    print(f"{len(chosen)} topic(s), {a.n} items each, writer {llm.GEN_MODEL}, solver {llm.SOLVER_MODEL}; OpenRouter credit left: "
          f"{'unknown' if left is None else f'${left:.2f}'}")
    known = corpus()
    all_kept = []
    for t in chosen:
        if llm.SPEND["usd"] > a.max_usd:
            print(f"stopping: spend ${llm.SPEND['usd']:.3f} passed --max-usd {a.max_usd}"); break
        kept, dropped = run_topic(t, a.n, a.purpose, sources, known)
        all_kept += kept
        print(f"\n{t['code']}  {t['title_he']}  kept {len(kept)}, dropped {len(dropped)}")
        for item, why in dropped:
            print("   DROP", why[0][:170])
        if a.show:
            for it in kept:
                print(f"   + [{it['difficulty']}] {it['stem']}\n     " + " | ".join(("*" if i == it['answer'] else "") + str(o) for i, o in enumerate(it["options"])))
    saved = store.save_db(all_kept, topics, sources) if a.db else store.save_local(all_kept)
    print(f"\nsaved {saved} pending item(s) to {'the qbank tables' if a.db else store.LOCAL}; "
          f"spend ${llm.SPEND['usd']:.3f} ({llm.SPEND['calls']} calls, {llm.SPEND['in']}+{llm.SPEND['out']} tokens)")


if __name__ == "__main__":
    main()
