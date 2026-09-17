-- ROLLBACK of 20260909_hebrew_nikud.sql  ·  2026-09-17
--
-- Read this before running it.
--
-- The statements that would destroy data are written out but COMMENTED OUT on
-- purpose. Uncomment one only after you have a backup and you are certain.
--
-- Idempotent where it is active: safe to run more than once.

drop policy if exists hebrew_nikud_read on public.hebrew_nikud;

drop index if exists public.hebrew_nikud_reviewed_idx;

-- DATA LOSS: -- drop table if exists public.hebrew_nikud cascade;

notify pgrst, 'reload schema';
