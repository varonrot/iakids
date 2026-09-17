-- ROLLBACK of 20260910_game_bank_batch.sql  ·  2026-09-17
--
-- Read this before running it.
--
-- A `create or replace function` cannot be undone by this file: dropping the
-- function removes it altogether, which breaks the app harder than leaving it.
-- If an earlier migration defined the same function, re-run THAT file instead.
--
-- Idempotent where it is active: safe to run more than once.

drop function if exists public.game_record_answers(uuid, jsonb);

notify pgrst, 'reload schema';
