-- ROLLBACK of 20260909_game_question_verification.sql  ·  2026-09-17
--
-- Read this before running it.
--
-- The statements that would destroy data are written out but COMMENTED OUT on
-- purpose. Uncomment one only after you have a backup and you are certain.
--
-- Idempotent where it is active: safe to run more than once.

drop policy if exists game_questions_insert on public.game_questions;

drop index if exists public.game_questions_pending_idx;

-- DATA LOSS: -- alter table public.game_questions drop column if exists verify_state;

notify pgrst, 'reload schema';
