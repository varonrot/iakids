#!/usr/bin/env python3
"""Build the fake database's seed data from production, read-only.

    cd backend-ai-tutor-he && APP_ENV=prod ../backend/.venv/bin/python ../performance/make_fixtures.py

What it copies:
  * one generated lesson (lesson_units_content, status ready, with audio) and its parent learning_lessons row;
    lesson content is curriculum, not a child's data.
  * the COLUMN NAMES of every other table the tutor reads. Rows of tables that hold a child's or a parent's
    data (kids_profiles, progress, history, chats, homework...) are never copied: the fake database fills
    them with a synthetic test child.
Nothing is written to production.
"""
import json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend-ai-tutor-he"))
os.chdir(HERE.parent / "backend-ai-tutor-he")
from dotenv import load_dotenv  # noqa: E402

load_dotenv(f".env.{os.getenv('APP_ENV', 'dev')}")
from supabase import create_client  # noqa: E402

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
SHAPE_ONLY = ["kids_profiles", "kid_unit_lesson_progress", "kid_lesson_history", "homework_sessions", "tutor_sessions",
              "homework_uploads", "media_jobs", "kids_chats", "subscriptions", "learning_coach_sessions", "kids_memory",
              "kid_game_sessions", "games_catalog", "kid_lesson_progress"]

lesson = (sb.table("lesson_units_content").select("*").eq("generation_status", "ready")
          .not_.is_("lesson_audio_json", "null").order("id", desc=True).limit(1).execute().data)
if not lesson:
    sys.exit("no ready lesson with audio in this project")
lesson = lesson[0]
parent = sb.table("learning_lessons").select("*").eq("id", lesson["learning_lesson_id"]).execute().data
# the intro template the lesson points at (shared media metadata, no child data)
intro = []
if lesson.get("intro_template_id"):
    intro = sb.table("lesson_intro_templates").select("*").eq("id", lesson["intro_template_id"]).execute().data
shapes = {}
for t in SHAPE_ONLY:
    try:
        rows = sb.table(t).select("*").limit(1).execute().data
        shapes[t] = sorted(rows[0].keys()) if rows else []
    except Exception as e:  # table missing in this project
        shapes[t] = {"error": str(e)[:120]}
out = {"lesson_units_content": [lesson], "learning_lessons": parent, "lesson_intro_templates": intro, "shapes": shapes}
(HERE / "fixtures" / "seed.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
print(f"lesson {lesson['id']} ({lesson.get('lesson_name')}), parent {lesson['learning_lesson_id']}, "
      f"{sum(1 for v in shapes.values() if isinstance(v, list) and v)} table shapes -> fixtures/seed.json")
