-- ROLLBACK of 20260910_rls_findings.sql  ·  2026-09-17
--
-- Read this before running it.
--
-- THIS ROLLBACK REOPENS THE HOLES THE 2026-09-10 AUDIT CLOSED.
-- Those policies are what stops anonymous reads of exam answer keys, exam questions,
-- the whole lesson catalogue and kid progress, and an anonymous INSERT into
-- subscriptions. Dropping them without putting something else in front of those
-- tables leaves them open to anyone with the publishable key. Do not run this to
-- 'fix' a page that stopped working: grant that one page what it needs instead.
--
-- Idempotent where it is active: safe to run more than once.

drop policy if exists subscriptions_select_own on public.subscriptions;
drop policy if exists subscriptions_insert_free on public.subscriptions;
drop policy if exists kulp_select_own on public.kid_unit_lesson_progress;
drop policy if exists exams_read on public.exams;
drop policy if exists exam_pages_read on public.exam_pages;
drop policy if exists exam_questions_read on public.exam_questions;
drop policy if exists lesson_units_content_read on public.lesson_units_content;

notify pgrst, 'reload schema';
