from pathlib import Path

backend = Path('backend-ai-tutor-he/main.py')
text = backend.read_text(encoding='utf-8')

marker = '''def get_or_create_lesson_progress(
'''
helper = '''def complete_kid_unit_lesson_progress(
        kid_id: str,
        unit_lesson_id: int,
        mastery_score: int
):
    now_iso = datetime.now(timezone.utc).isoformat()
    final_score = max(0, min(100, int(mastery_score or 0)))

    try:
        current_res = (
            sb.table("kid_unit_lesson_progress")
            .select("id, best_mastery_score")
            .eq("kid_id", kid_id)
            .eq("unit_lesson_id", unit_lesson_id)
            .limit(1)
            .execute()
        )

        if not current_res.data:
            print("UNIT LESSON PROGRESS COMPLETE WARNING: row not found", {
                "kid_id": kid_id,
                "unit_lesson_id": unit_lesson_id
            })
            return None

        current = current_res.data[0]
        best_score = max(
            int(current.get("best_mastery_score") or 0),
            final_score
        )

        updated = (
            sb.table("kid_unit_lesson_progress")
            .update({
                "status": "completed",
                "progress_percent": 100,
                "current_stage": LESSON_STAGE_FINAL_ASSESSMENT,
                "mastery_score": final_score,
                "best_mastery_score": best_score,
                "last_activity_at": now_iso,
                "completed_at": now_iso,
                "updated_at": now_iso
            })
            .eq("id", current["id"])
            .execute()
        )

        return updated.data[0] if updated.data else current

    except Exception as e:
        # Do not break the existing lesson engine if the migration has not
        # reached an environment yet.
        print("UNIT LESSON PROGRESS COMPLETE WARNING:", repr(e))
        return None


'''
if 'def complete_kid_unit_lesson_progress(' not in text:
    if marker not in text:
        raise SystemExit('helper insertion marker not found')
    text = text.replace(marker, helper + marker, 1)

needle = '''        if progress_update.data:
            progress = (
                progress_update.data[0]
            )

    else:
'''
replacement = '''        if progress_update.data:
            progress = (
                progress_update.data[0]
            )

        if not has_next_part:
            complete_kid_unit_lesson_progress(
                kid_id=child["id"],
                unit_lesson_id=unit_lesson["id"],
                mastery_score=overall_mastery_score
            )

    else:
'''
if 'complete_kid_unit_lesson_progress(\n                kid_id=child["id"]' not in text:
    if needle not in text:
        raise SystemExit('completion call insertion marker not found')
    text = text.replace(needle, replacement, 1)

backend.write_text(text, encoding='utf-8')

front = Path('he/workspace/index.html')
f = front.read_text(encoding='utf-8')
f = f.replace('IAKIDS • build 0.5.5', 'IAKIDS • build 0.5.6')
f = f.replace('window.IAKIDS_BUILD_VERSION = "0.5.5";', 'window.IAKIDS_BUILD_VERSION = "0.5.6";')
front.write_text(f, encoding='utf-8')
