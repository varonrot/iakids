-- IAKIDS: tables the browser never touches stop being reachable from a browser.  2026-09-17
--
-- Why
-- ---
-- Supabase grants anon and authenticated full privileges on every table in `public` by
-- default, and row level security is the only thing standing in front of them. That is
-- one policy mistake away from an open table, and it already happened once: the
-- 2026-09-10 audit found anonymous reads of exam answer keys, exam questions and the
-- whole lesson catalogue, and an anonymous INSERT into subscriptions that only a NOT
-- NULL constraint stopped.
--
-- A grant the browser never uses is pure risk. Every table below was checked against
-- every .html and .js file the site serves (excluding backup copies): not one is read
-- or written from a browser. The backend runs as service_role, which grants do not
-- restrict, so it keeps full access to all of them.
--
-- What was deliberately NOT touched
-- ---------------------------------
-- 23 tables that live browser code really does use stay exactly as they are:
--   game_questions, games_catalog, homework_capture_sessions, homework_sessions,
--   kid_custom_curriculums, kid_custom_lessons, kid_custom_subjects, kid_custom_units,
--   kid_game_sessions, kid_lesson_history, kid_lesson_progress, kid_question_answers,
--   kid_tasks, kid_unit_lesson_progress, kids_profiles, learning_coach_sessions,
--   learning_lessons, lesson_units_content, subscriptions, support_messages,
--   support_tickets, tutor_sessions, usage_summary.
-- Closing those means moving their reads behind the backend first. Separate job.
--
-- Functions the browser calls were checked one by one:
--   record_user_location, game_record_answer, game_record_answers, game_question_mark
--     are SECURITY DEFINER, so they keep working without the caller holding table rights.
--   game_next_questions is SECURITY INVOKER, but it only reads game_questions and
--     kid_question_answers, both of which stay granted.
--
-- Reversible: 20260917_revoke_browser_table_access_rollback.sql puts every grant back.
-- Idempotent: safe to run more than once.

revoke all on public.ai_calls from anon, authenticated;
revoke all on public.ai_costs_daily from anon, authenticated;
revoke all on public.ai_costs_per_kid from anon, authenticated;
revoke all on public.ai_costs_per_lesson from anon, authenticated;
revoke all on public.app_admins from anon, authenticated;
revoke all on public.exam_answer_keys from anon, authenticated;
revoke all on public.exam_pages from anon, authenticated;
revoke all on public.exam_questions from anon, authenticated;
revoke all on public.exams from anon, authenticated;
revoke all on public.game_lesson_links from anon, authenticated;
revoke all on public.hebrew_nikud from anon, authenticated;
revoke all on public.homework_uploads from anon, authenticated;
revoke all on public.kid_custom_curriculum_versions from anon, authenticated;
revoke all on public.kid_learning_plan_nodes from anon, authenticated;
revoke all on public.kid_learning_plans from anon, authenticated;
revoke all on public.kid_part_reward_claims from anon, authenticated;
revoke all on public.kid_personal_media from anon, authenticated;
revoke all on public.kids_chats from anon, authenticated;
revoke all on public.kids_memory from anon, authenticated;
revoke all on public.lesson_intro_templates from anon, authenticated;
revoke all on public.lesson_plans from anon, authenticated;
revoke all on public.media_jobs from anon, authenticated;
revoke all on public.media_jobs_hourly from anon, authenticated;
revoke all on public.request_log from anon, authenticated;
revoke all on public.request_log_hourly from anon, authenticated;
revoke all on public.service_metrics from anon, authenticated;
revoke all on public.service_metrics_5min from anon, authenticated;
revoke all on public.user_locations from anon, authenticated;

notify pgrst, 'reload schema';

-- Check afterwards, signed in as an ordinary account (not the service role):
--
--   select * from public.exam_answer_keys limit 1;
--   -- expected: ERROR: permission denied for table exam_answer_keys
--
--   select * from public.kids_profiles limit 1;
--   -- expected: the account's own rows, exactly as before
