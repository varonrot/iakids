-- ROLLBACK of 20260917_coach_sessions_own_children.sql  ·  2026-09-17
--
-- THIS REOPENS THE HOLE. Dropping the policy makes every coach session readable by any
-- signed-in account again — another child's understanding scores, lesson by lesson.
-- Only run it if the policy broke a screen, and fix that screen instead of leaving
-- this in place. The two screens that read the table already filter by kid_id, so the
-- policy should be invisible to them.
--
-- Idempotent: safe to run more than once.

drop policy if exists lcs_select_own on public.learning_coach_sessions;

notify pgrst, 'reload schema';
