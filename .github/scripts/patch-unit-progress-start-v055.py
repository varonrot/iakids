from pathlib import Path

backend = Path('backend-ai-tutor-he/main.py')
s = backend.read_text(encoding='utf-8')
marker = 'IAKIDS_UNIT_LESSON_PROGRESS_V055'

if marker not in s:
    anchor = '\ndef get_or_create_lesson_progress(\n'
    if anchor not in s:
        raise SystemExit('backend helper anchor not found')

    helper = r'''

# =====================================================
# IAKIDS_UNIT_LESSON_PROGRESS_V055
# Persistent progress for each internal unit lesson.
# =====================================================

def start_kid_unit_lesson_progress(
        kid_id: str,
        learning_lesson_id: int,
        unit_lesson_id: int
):
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        # Any other lesson that was started but never completed becomes partial.
        active_res = (
            sb.table("kid_unit_lesson_progress")
            .select("id, unit_lesson_id, status")
            .eq("kid_id", kid_id)
            .eq("status", "in_progress")
            .execute()
        )

        for row in (active_res.data or []):
            if int(row.get("unit_lesson_id") or 0) == int(unit_lesson_id):
                continue

            sb.table("kid_unit_lesson_progress").update({
                "status": "partial",
                "last_activity_at": now_iso,
                "updated_at": now_iso
            }).eq("id", row["id"]).execute()

        current_res = (
            sb.table("kid_unit_lesson_progress")
            .select("*")
            .eq("kid_id", kid_id)
            .eq("unit_lesson_id", unit_lesson_id)
            .limit(1)
            .execute()
        )

        if current_res.data:
            current = current_res.data[0]

            # Re-opening a completed lesson is review; never erase completion.
            if current.get("status") == "completed":
                sb.table("kid_unit_lesson_progress").update({
                    "last_activity_at": now_iso,
                    "updated_at": now_iso
                }).eq("id", current["id"]).execute()
                return current

            updated = (
                sb.table("kid_unit_lesson_progress")
                .update({
                    "status": "in_progress",
                    "attempts_count": int(current.get("attempts_count") or 0) + 1,
                    "last_activity_at": now_iso,
                    "updated_at": now_iso
                })
                .eq("id", current["id"])
                .execute()
            )
            return updated.data[0] if updated.data else current

        inserted = (
            sb.table("kid_unit_lesson_progress")
            .insert({
                "kid_id": kid_id,
                "unit_lesson_id": unit_lesson_id,
                "learning_lesson_id": learning_lesson_id,
                "status": "in_progress",
                "progress_percent": 0,
                "current_stage": LESSON_STAGE_INTRO,
                "last_part_number": 1,
                "mastery_score": 0,
                "best_mastery_score": 0,
                "attempts_count": 1,
                "started_at": now_iso,
                "last_activity_at": now_iso,
                "updated_at": now_iso
            })
            .execute()
        )
        return inserted.data[0] if inserted.data else None

    except Exception as e:
        # Keep the existing lesson engine available until the DB migration
        # has been applied in every environment.
        print("UNIT LESSON PROGRESS START WARNING:", repr(e))
        return None
'''
    s = s.replace(anchor, helper + anchor, 1)

call_anchor = '''        is_new_unit_lesson = (
            requested_unit_lesson_id is not None
            and requested_unit_lesson_id
            != stored_unit_lesson_id
        )

        if is_new_unit_lesson:
'''
if 'start_kid_unit_lesson_progress(' not in s[s.find('requested_unit_lesson_id = ('):s.find('if is_new_unit_lesson:', s.find('requested_unit_lesson_id = ('))]:
    if call_anchor not in s:
        raise SystemExit('unit switch call anchor not found')
    replacement = '''        is_new_unit_lesson = (
            requested_unit_lesson_id is not None
            and requested_unit_lesson_id
            != stored_unit_lesson_id
        )

        if is_lesson_start and requested_unit_lesson_id is not None:
            start_kid_unit_lesson_progress(
                kid_id=child["id"],
                learning_lesson_id=lesson["id"],
                unit_lesson_id=requested_unit_lesson_id
            )

        if is_new_unit_lesson:
'''
    s = s.replace(call_anchor, replacement, 1)

backend.write_text(s, encoding='utf-8')

index = Path('he/workspace/index.html')
h = index.read_text(encoding='utf-8')
h = h.replace('IAKIDS • build 0.5.4', 'IAKIDS • build 0.5.5')
h = h.replace('window.IAKIDS_BUILD_VERSION = "0.5.4"', 'window.IAKIDS_BUILD_VERSION = "0.5.5"')
index.write_text(h, encoding='utf-8')

print('patched unit lesson start/partial tracking; build 0.5.5')
