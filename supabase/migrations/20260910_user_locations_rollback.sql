-- ROLLBACK of 20260910_user_locations.sql  ·  2026-09-17
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

drop policy if exists user_locations_read_own on public.user_locations;

drop function if exists public.record_user_location(text, text, text, text);

-- DATA LOSS: -- drop table if exists public.user_locations cascade;

notify pgrst, 'reload schema';
