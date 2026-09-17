#!/usr/bin/env python
"""Write the correct answer into the questions of lessons generated before 2026-09-17.

Why this exists
---------------
Until 2026-09-17 the teacher wrote only `explanation` and `question`, and the Learning
Coach was handed the sentence "Derive from the lesson explanation and lesson goal"
instead of a real answer. It therefore graded the child against an answer it invented:
a child who answered "המורה, ארנב, תלמידה" - every noun the question asked for - was
told she had missed an animal she had just named.

New lessons carry `question.answer`. Existing lessons do not, and regenerating them
would throw away their text, their images and their audio for a single missing field.
This tool fills that one field with one cheap text call per part and touches nothing
else: the explanation, the question, the visuals and the audio stay exactly as they are.

Usage
-----
    cd backend-ai-tutor-he
    APP_ENV=prod ../backend/.venv/bin/python tools/backfill_lesson_answers.py --id 152
    ... --all-missing            every ready lesson whose questions have no answer
    ... --id 152 --dry-run       show what would be written, write nothing
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APP_ENV", "prod")

import main  # noqa: E402


ANSWER_PROMPT = (
    "אתה המורה שכתב את השיעור הזה. כתוב את התשובה הנכונה והמלאה לשאלה, למורה בלבד.\n"
    "- התשובה נגזרת אך ורק מההסבר שלמטה וממטרת השיעור.\n"
    "- אם השאלה מבקשת לזהות מילים במשפט, מנה את כולן במפורש ולא במילים כלליות.\n"
    "- אם השאלה מסננת לפי קטגוריה, כתוב רק את מה שנכנס לקטגוריה, וציין מילה שנראית\n"
    "  מתאימה אך אינה נכנסת, כדי שהמורה לא תטעה.\n"
    "- שני משפטים לכל היותר. בלי פנייה לילד ובלי שאלה.\n"
)


async def answer_for(question: str, explanation: str, goal: str) -> str:
    completion = await main.aclient.chat.completions.create(
        model=main.llm_model(main.DEFAULT_OPENAI_MODEL),
        messages=[
            {"role": "system", "content": ANSWER_PROMPT},
            {"role": "user", "content": (
                f"מטרת השיעור: {goal}\n\n"
                f"ההסבר:\n{explanation}\n\n"
                f"השאלה:\n{question}"
            )},
        ],
    )
    return (completion.choices[0].message.content or "").strip()


def lesson_rows(lesson_id, all_missing):
    q = main.sb.table("lesson_units_content").select(
        "id, lesson_name, learning_objective, generated_lesson_json")
    if lesson_id:
        q = q.eq("id", lesson_id)
    rows = (q.execute().data or [])
    out = []
    for row in rows:
        parts = (((row.get("generated_lesson_json") or {}).get("structured_lesson") or {}).get("parts") or [])
        if not parts:
            continue
        missing = [p for p in parts
                   if isinstance(p, dict)
                   and (p.get("question") or {}).get("text")
                   and not str((p.get("question") or {}).get("answer") or "").strip()]
        if missing or not all_missing:
            out.append((row, parts, missing))
    return out


async def run(lesson_id, all_missing, dry_run):
    rows = lesson_rows(lesson_id, all_missing)
    if not rows:
        print("nothing to do: no lesson with a question missing its answer")
        return 0
    written = 0
    for row, parts, missing in rows:
        if not missing:
            print(f"lesson {row['id']}: every question already has an answer")
            continue
        print(f"\nlesson {row['id']} - {row.get('lesson_name')}  ({len(missing)} of {len(parts)} parts missing)")
        for part in missing:
            question = (part.get("question") or {}).get("text") or ""
            explanation = "\n\n".join(
                str(seg.get("text") or "").strip()
                for seg in (part.get("lesson") or [])
                if isinstance(seg, dict) and str(seg.get("text") or "").strip()
            )
            answer = await answer_for(question, explanation, row.get("learning_objective") or "")
            if not answer:
                print(f"  part {part.get('part_number')}: model returned nothing - left as is")
                continue
            print(f"  part {part.get('part_number')} Q: {question[:90]}")
            print(f"  part {part.get('part_number')} A: {answer[:160]}")
            if not dry_run:
                part["question"]["answer"] = answer
                written += 1
        if not dry_run and written:
            main.sb.table("lesson_units_content").update(
                {"generated_lesson_json": row["generated_lesson_json"]}
            ).eq("id", row["id"]).execute()
            print(f"  saved lesson {row['id']}")
    print(f"\n{'would write' if dry_run else 'wrote'} {written} answers")
    return 0


def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, help="one unit lesson id")
    ap.add_argument("--all-missing", action="store_true", help="every lesson whose questions have no answer")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.id and not a.all_missing:
        ap.error("pass --id N or --all-missing")
    return asyncio.run(run(a.id, a.all_missing, a.dry_run))


if __name__ == "__main__":
    sys.exit(cli())
