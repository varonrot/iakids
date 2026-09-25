"""A throwaway parent + child in production for `run.py --db prod`, and its removal afterwards.

make_identity(prod_env) -> {"token", "kid_id", "user_id", "unit_lesson_id", "learning_lesson_id"}
drop_identity(prod_env, ident) deletes the child row and the auth user.

The parent is perf-test-<timestamp>@iakids.app (no mail is sent: created by the admin API
with email_confirm=True). Only prod-safe routes run with it - routes the fake run proved
make no writes and no model calls - so nothing else is left behind. If a run dies before
drop_identity, `python performance/prod_identity.py --cleanup` removes every perf-test-*
parent and its children.
"""
import sys
import time

from supabase import create_client


def _sb(env):
    return create_client(env["SUPABASE_URL"], env["SUPABASE_SERVICE_ROLE_KEY"])


def make_identity(env):
    sb = _sb(env)
    email = f"perf-test-{time.strftime('%Y%m%d%H%M%S')}@iakids.app"
    user = sb.auth.admin.create_user({"email": email, "email_confirm": True,
                                      "user_metadata": {"perf_test": True}}).user
    lesson = (sb.table("lesson_units_content").select("id,learning_lesson_id").eq("generation_status", "ready")
              .not_.is_("lesson_audio_json", "null").order("id", desc=True).limit(1).execute().data[0])
    grade = sb.table("learning_lessons").select("grade").eq("id", lesson["learning_lesson_id"]).execute().data[0]["grade"]
    kid = sb.table("kids_profiles").insert({"user_id": user.id, "child_name": "ילד בדיקת עומס", "age": grade,
                                            "gender": "male"}).execute().data[0]
    link = sb.auth.admin.generate_link({"type": "magiclink", "email": email})
    token = _sb(env).auth.verify_otp({"token_hash": link.properties.hashed_token, "type": "magiclink"}).session.access_token
    print(f"prod identity: parent {email}, child {kid['id']}, lesson {lesson['id']}", flush=True)
    return {"token": token, "kid_id": kid["id"], "user_id": user.id, "email": email,
            "unit_lesson_id": lesson["id"], "learning_lesson_id": lesson["learning_lesson_id"]}


def drop_identity(env, ident):
    sb = _sb(env)
    sb.table("kids_profiles").delete().eq("user_id", ident["user_id"]).execute()
    sb.auth.admin.delete_user(ident["user_id"])
    print(f"prod identity removed: {ident['email']}", flush=True)


if __name__ == "__main__" and "--cleanup" in sys.argv:
    from pathlib import Path
    env = {}
    for line in (Path(__file__).resolve().parent.parent / "backend-ai-tutor-he" / ".env.prod").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"')
    sb = _sb(env)
    page, gone = 1, 0
    while True:
        users = sb.auth.admin.list_users(page=page, per_page=200)
        if not users:
            break
        for u in users:
            if (u.email or "").startswith("perf-test-") and (u.email or "").endswith("@iakids.app"):
                drop_identity(env, {"user_id": u.id, "email": u.email}); gone += 1
        page += 1
    print(f"removed {gone} perf-test parents")
