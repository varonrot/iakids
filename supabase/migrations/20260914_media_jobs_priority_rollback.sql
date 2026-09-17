-- ROLLBACK of 20260914_media_jobs_priority.sql  ·  2026-09-17
--
-- Read this before running it.
--
-- media_jobs_enqueue and media_jobs_claim also exist in 20260914_media_jobs.sql.
-- To go back to the pre-priority behaviour, re-run that file rather than dropping them.
--
-- A `create or replace function` cannot be undone by this file: dropping the
-- function removes it altogether, which breaks the app harder than leaving it.
-- If an earlier migration defined the same function, re-run THAT file instead.
--
-- The statements that would destroy data are written out but COMMENTED OUT on
-- purpose. Uncomment one only after you have a backup and you are certain.
--
-- Idempotent where it is active: safe to run more than once.

drop index if exists public.media_jobs_pending_idx;

drop function if exists public.media_jobs_enqueue(text, jsonb, text, int, int);
drop function if exists public.media_jobs_claim(text, int);

-- DATA LOSS: -- alter table public.media_jobs drop column if exists priority;

notify pgrst, 'reload schema';
