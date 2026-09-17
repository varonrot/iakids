-- ROLLBACK of 20260908_game_question_bank.sql  ·  2026-09-17
--
-- Read this before running it.
--
-- game_next_questions and game_record_answer were redefined by the later
-- 20260910_game_bank_* migrations. Re-run the newest of those instead of dropping.
--
-- A `create or replace function` cannot be undone by this file: dropping the
-- function removes it altogether, which breaks the app harder than leaving it.
-- If an earlier migration defined the same function, re-run THAT file instead.
--
-- The statements that would destroy data are written out but COMMENTED OUT on
-- purpose. Uncomment one only after you have a backup and you are certain.
--
-- Idempotent where it is active: safe to run more than once.

drop policy if exists game_questions_read on public.game_questions;
drop policy if exists game_questions_insert on public.game_questions;
drop policy if exists kid_question_answers_select_own on public.kid_question_answers;
drop policy if exists kid_question_answers_insert_own on public.kid_question_answers;

drop index if exists public.game_questions_game_level_idx;
drop index if exists public.kid_question_answers_kid_game_idx;
drop index if exists public.kid_question_answers_question_idx;

drop function if exists public.game_question_mark(text, text, boolean);
drop function if exists public.game_next_questions(uuid, text, smallint, int);

-- DATA LOSS: -- drop table if exists public.game_questions cascade;
-- DATA LOSS: -- drop table if exists public.kid_question_answers cascade;

notify pgrst, 'reload schema';
