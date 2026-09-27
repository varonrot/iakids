-- Rollback for 20260927_01_eng_lesson_engine.sql (English lesson engine tables, applied on 2026-09-27).
-- Runs 04, 03 and 02's rollbacks first. The policy drop is safe to run; the tables and the bucket hold
-- lesson plans, children's progress and generated images, so dropping them is left commented.
drop policy if exists "2027_eng_progress_read_own_child" on public."2027_eng_lesson_progress";

-- DATA LOSS: drop table if exists public."2027_eng_lesson_progress";
-- DATA LOSS: drop table if exists public."2027_eng_lesson_visuals";
-- DATA LOSS: drop table if exists public."2027_eng_lesson_plans";
-- DATA LOSS: delete from storage.buckets where id = '2027-eng-lesson-media';  -- empty the bucket first
