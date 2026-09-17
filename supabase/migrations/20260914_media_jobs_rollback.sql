-- ROLLBACK of 20260914_media_jobs.sql  ·  2026-09-17
--
-- Read this before running it.
--
-- media_jobs is the queue the worker lives on. Dropping these functions stops all
-- media generation: no images, no audio, no intro videos. Stop the worker first.
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
drop index if exists public.media_jobs_live_dedupe_idx;
drop index if exists public.media_jobs_dedupe_key_idx;

drop function if exists public.media_jobs_enqueue(text, jsonb, text, int);
drop function if exists public.media_jobs_claim(text, int);
drop function if exists public.media_jobs_heartbeat(bigint, text);
drop function if exists public.media_jobs_finish(bigint, text, boolean, text, int);
drop function if exists public.media_jobs_requeue_stale(int);

-- DATA LOSS: -- drop table if exists public.media_jobs cascade;

notify pgrst, 'reload schema';
