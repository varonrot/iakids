-- ROLLBACK of 20260917_revoke_browser_table_access.sql  ·  2026-09-17
--
-- Puts back the Supabase default: anon and authenticated hold every privilege on these
-- tables and row level security is the only gate. Run this only if revoking broke
-- something, and say what broke — the right fix is usually to move that one read behind
-- the backend, not to reopen 28 tables.
--
-- Idempotent: safe to run more than once.

grant all on public.ai_calls to anon, authenticated;
grant all on public.ai_costs_daily to anon, authenticated;
grant all on public.ai_costs_per_kid to anon, authenticated;
grant all on public.ai_costs_per_lesson to anon, authenticated;
grant all on public.app_admins to anon, authenticated;
grant all on public.exam_answer_keys to anon, authenticated;
grant all on public.exam_pages to anon, authenticated;
grant all on public.exam_questions to anon, authenticated;
grant all on public.exams to anon, authenticated;
grant all on public.game_lesson_links to anon, authenticated;
grant all on public.hebrew_nikud to anon, authenticated;
grant all on public.homework_uploads to anon, authenticated;
grant all on public.kid_custom_curriculum_versions to anon, authenticated;
grant all on public.kid_learning_plan_nodes to anon, authenticated;
grant all on public.kid_learning_plans to anon, authenticated;
grant all on public.kid_part_reward_claims to anon, authenticated;
grant all on public.kid_personal_media to anon, authenticated;
grant all on public.kids_chats to anon, authenticated;
grant all on public.kids_memory to anon, authenticated;
grant all on public.lesson_intro_templates to anon, authenticated;
grant all on public.lesson_plans to anon, authenticated;
grant all on public.media_jobs to anon, authenticated;
grant all on public.media_jobs_hourly to anon, authenticated;
grant all on public.request_log to anon, authenticated;
grant all on public.request_log_hourly to anon, authenticated;
grant all on public.service_metrics to anon, authenticated;
grant all on public.service_metrics_5min to anon, authenticated;
grant all on public.user_locations to anon, authenticated;

notify pgrst, 'reload schema';
