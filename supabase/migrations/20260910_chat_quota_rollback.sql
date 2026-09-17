-- ROLLBACK of 20260910_chat_quota.sql  ·  2026-09-17
--
-- Read this before running it.
--
-- A `create or replace function` cannot be undone by this file: dropping the
-- function removes it altogether, which breaks the app harder than leaving it.
-- If an earlier migration defined the same function, re-run THAT file instead.
--
-- The statements that would destroy data are written out but COMMENTED OUT on
-- purpose. Uncomment one only after you have a backup and you are certain.
--
-- Idempotent where it is active: safe to run more than once.

drop function if exists public.chat_consume_message(uuid, int, int);

-- DATA LOSS: -- alter table public.subscriptions drop column if exists messages_period_start;

notify pgrst, 'reload schema';
