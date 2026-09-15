---
name: delete-lesson
description: Delete a generated unit lesson (מחק שיעור N) — wipes its Storage media (lesson-media + lesson-audio under unit_lessons/<id>/), its media_jobs rows, and resets the lesson_units_content row so the lesson regenerates from scratch. Use when the user asks to delete / reset / regenerate a lesson by number.
---

# delete-lesson — wipe a unit lesson's generated content + media

The number the user gives is `lesson_units_content.id` (the same "מספר שיעור" shown in the affected-lessons table).

1. **Dry run first** (safe, read-only) and show the user what will go:
   ```bash
   cd backend-ai-tutor-he && APP_ENV=prod ../backend/.venv/bin/python tools/delete_unit_lesson.py --id <N>
   ```
2. If the user already said explicitly to delete that lesson (e.g. "מחק שיעור 31"), run the real deletion right away:
   ```bash
   cd backend-ai-tutor-he && APP_ENV=prod ../backend/.venv/bin/python tools/delete_unit_lesson.py --id <N> --yes
   ```
   Several ids: repeat `--id`. `--with-progress` also clears `kid_unit_lesson_progress` for that lesson (ask first — it erases kids' progress). `--force` also deletes a *running* media job (stop the worker first: `systemctl stop iakids-tutor-worker`).
3. Report per lesson: objects removed from each bucket, media_jobs removed, row reset OK. `RESULT: OK` must appear.
4. To regenerate: open the lesson in the workspace, or run
   `APP_ENV=prod ../backend/.venv/bin/python tools/e2e_media_jobs.py --kid-id <kid> --unit-lesson <N>`.

Why storage must be wiped: `content_version` stays 1 after a reset, so new media is written to the *same* paths; stale files (e.g. an old `segment_8.wav` when the new part has 7 segments) would otherwise survive and could be served.
Never delete the `lesson_units_content` row itself (curriculum data lives there) and never touch other lessons' prefixes.
