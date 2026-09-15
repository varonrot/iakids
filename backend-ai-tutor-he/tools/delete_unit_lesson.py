#!/usr/bin/env python3
"""Delete a generated unit lesson so it can be regenerated from scratch.

    cd backend-ai-tutor-he
    APP_ENV=prod ../backend/.venv/bin/python tools/delete_unit_lesson.py --id 31            # DRY RUN: only lists
    APP_ENV=prod ../backend/.venv/bin/python tools/delete_unit_lesson.py --id 31 --yes      # really delete
    APP_ENV=prod ../backend/.venv/bin/python tools/delete_unit_lesson.py --id 1 --id 3 --yes
    ... --with-progress   also delete kid_unit_lesson_progress rows of that unit lesson (all kids)

What it deletes (per unit lesson id):
  1. Storage bucket `lesson-media`  : every object under unit_lessons/<id>/   (hero, visuals, transition video)
  2. Storage bucket `lesson-audio`  : every object under unit_lessons/<id>/   (segment_*.wav, question.wav)
  3. public.media_jobs               : rows whose payload.unit_lesson_id == id (pending/done/failed;
                                       a RUNNING job is reported and skipped unless --force)
  4. public.lesson_units_content     : generated fields reset (generated_lesson_json, lesson_audio_json,
                                       statuses, timestamps, errors). Curriculum fields (name, order,
                                       learning_objective, complexity, parts count, duration) are kept.
Nothing else is touched. Without --yes it is a dry run.
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
os.chdir(HERE)

ap = argparse.ArgumentParser()
ap.add_argument("--id", type=int, action="append", required=True, help="lesson_units_content.id (repeatable)")
ap.add_argument("--yes", action="store_true", help="actually delete (default: dry run)")
ap.add_argument("--force", action="store_true", help="also delete media_jobs that are currently running")
ap.add_argument("--with-progress", action="store_true", help="also delete kid_unit_lesson_progress rows")
args = ap.parse_args()

from dotenv import load_dotenv  # noqa: E402
app_env = os.environ.get("APP_ENV", "").strip().lower()
env_file = {"prod": ".env.prod", "dev": ".env.dev"}.get(app_env, ".env")
if not Path(env_file).exists():
    sys.exit(f"env file {env_file} not found (APP_ENV={app_env!r})")
load_dotenv(env_file)
from supabase import create_client  # noqa: E402

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
MEDIA_BUCKET = "lesson-media"
AUDIO_BUCKET = "lesson-audio"
MODE = "DELETE" if args.yes else "DRY RUN"
print(f"[config] APP_ENV={app_env or 'default'} -> {env_file}  project={os.environ['SUPABASE_URL']}  mode={MODE}")


def walk(bucket: str, prefix: str, acc=None):
    """Recursively list object paths under prefix (Supabase list() returns folders with id=None)."""
    acc = [] if acc is None else acc
    offset = 0
    while True:
        page = sb.storage.from_(bucket).list(prefix, {"limit": 1000, "offset": offset})
        if not page:
            break
        for o in page:
            path = f"{prefix}/{o['name']}" if prefix else o["name"]
            if o.get("id") is None and o.get("metadata") is None:
                walk(bucket, path, acc)
            else:
                acc.append(path)
        if len(page) < 1000:
            break
        offset += len(page)
    return acc


def remove_objects(bucket: str, paths: list):
    for i in range(0, len(paths), 100):
        sb.storage.from_(bucket).remove(paths[i:i + 100])


RESET_FIELDS = {
    "generation_status": "empty",
    "status": "empty",
    "generated_lesson_json": None,
    "lesson_audio_json": None,
    "lesson_content_json": None,
    "audio_generation_status": "pending",
    "audio_generation_error": None,
    "audio_generated_at": None,
    "audio_mode": None,
    "generation_error": None,
    "generation_started_at": None,
    "generation_completed_at": None,
    "generated_at": None,
    "tts_generated_at": None,
    "model_name": None,
    "prompt_version": None,
}

exit_code = 0
for lesson_id in args.id:
    print(f"\n===== unit lesson {lesson_id} =====")
    rows = sb.table("lesson_units_content").select(
        "id,unit_name,lesson_name,generation_status,audio_generation_status,content_version"
    ).eq("id", lesson_id).execute().data
    if not rows:
        print("  !! row not found in lesson_units_content — skipping")
        exit_code = 1
        continue
    row = rows[0]
    print(f"  {row['unit_name']} | {row['lesson_name']} | generation={row['generation_status']} "
          f"audio={row['audio_generation_status']} content_version={row['content_version']}")

    prefix = f"unit_lessons/{lesson_id}"
    media = walk(MEDIA_BUCKET, prefix)
    audio = walk(AUDIO_BUCKET, prefix)
    print(f"  storage {MEDIA_BUCKET}: {len(media)} objects under {prefix}/")
    for p in media:
        print(f"     - {p}")
    print(f"  storage {AUDIO_BUCKET}: {len(audio)} objects under {prefix}/")
    for p in audio:
        print(f"     - {p}")

    jobs = sb.table("media_jobs").select("id,job_type,status,dedupe_key") \
        .eq("payload->>unit_lesson_id", str(lesson_id)).execute().data
    running = [j for j in jobs if j["status"] == "running"]
    deletable = [j for j in jobs if j["status"] != "running" or args.force]
    print(f"  media_jobs: {len(jobs)} rows ({len(running)} running) -> "
          f"{[ (j['id'], j['status']) for j in jobs ]}")
    if running and not args.force:
        print("  !! a job is RUNNING for this lesson — it is skipped; stop the worker or use --force")

    progress = []
    if args.with_progress:
        progress = sb.table("kid_unit_lesson_progress").select("id,kid_id") \
            .eq("unit_lesson_id", lesson_id).execute().data
        print(f"  kid_unit_lesson_progress: {len(progress)} rows")

    if not args.yes:
        print("  (dry run — nothing deleted; add --yes)")
        continue

    if media:
        remove_objects(MEDIA_BUCKET, media)
    if audio:
        remove_objects(AUDIO_BUCKET, audio)
    left_media = walk(MEDIA_BUCKET, prefix)
    left_audio = walk(AUDIO_BUCKET, prefix)
    print(f"  storage deleted: media {len(media)-len(left_media)}/{len(media)}, "
          f"audio {len(audio)-len(left_audio)}/{len(audio)}")
    if left_media or left_audio:
        print(f"  !! objects still present: {left_media + left_audio}")
        exit_code = 1

    for j in deletable:
        sb.table("media_jobs").delete().eq("id", j["id"]).execute()
    print(f"  media_jobs deleted: {len(deletable)}")

    if args.with_progress and progress:
        sb.table("kid_unit_lesson_progress").delete().eq("unit_lesson_id", lesson_id).execute()
        print(f"  kid_unit_lesson_progress deleted: {len(progress)}")

    sb.table("lesson_units_content").update(
        {**RESET_FIELDS, "updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", lesson_id).execute()
    after = sb.table("lesson_units_content").select(
        "generation_status,audio_generation_status,generated_lesson_json,lesson_audio_json"
    ).eq("id", lesson_id).single().execute().data
    ok = (after["generation_status"] == "empty" and after["generated_lesson_json"] is None
          and after["lesson_audio_json"] is None)
    print(f"  row reset: {'OK' if ok else 'FAILED'} -> {after['generation_status']}/{after['audio_generation_status']}")
    if not ok:
        exit_code = 1

print(f"\nRESULT: {'OK' if exit_code == 0 else 'WITH WARNINGS'} ({MODE})")
sys.exit(exit_code)
