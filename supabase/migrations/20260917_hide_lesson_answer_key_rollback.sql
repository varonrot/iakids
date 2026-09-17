-- ROLLBACK of 20260917_hide_lesson_answer_key.sql  ·  2026-09-17
--
-- Gives the browser back a blanket SELECT on lesson_units_content, including
-- generated_lesson_json — which carries the correct answer of every question, so a
-- signed-in child could read the answers before answering. Only run this if hiding the
-- column broke a page, and fix that page instead of leaving this in place.
--
-- Idempotent: safe to run more than once.

grant select on public.lesson_units_content to authenticated;

notify pgrst, 'reload schema';

-- anon was never meant to read this table (the 2026-09-10 policy limits it to
-- authenticated), so it is deliberately not granted back here.
