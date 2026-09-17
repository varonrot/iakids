-- ROLLBACK of 20260904_create_kid_unit_lesson_progress.sql  ·  2026-09-17
--
-- Read this before running it.
--
-- The statements that would destroy data are written out but COMMENTED OUT on
-- purpose. Uncomment one only after you have a backup and you are certain.
--
-- Idempotent where it is active: safe to run more than once.

drop index if exists public.kid_unit_lesson_progress_kid_idx;
drop index if exists public.kid_unit_lesson_progress_learning_lesson_idx;
drop index if exists public.kid_unit_lesson_progress_status_idx;

-- DATA LOSS: -- drop table if exists public.kid_unit_lesson_progress cascade;

notify pgrst, 'reload schema';
