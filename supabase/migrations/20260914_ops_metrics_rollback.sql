-- ROLLBACK of 20260914_ops_metrics.sql  ·  2026-09-17
--
-- Read this before running it.
--
-- media_jobs_claim and media_jobs_finish are also defined by 20260914_media_jobs.sql.
-- Dropping them here removes the queue's claim/finish path entirely. If you only want
-- the pre-metrics behaviour back, re-run 20260914_media_jobs.sql instead of this file.
--
-- A `create or replace function` cannot be undone by this file: dropping the
-- function removes it altogether, which breaks the app harder than leaving it.
-- If an earlier migration defined the same function, re-run THAT file instead.
--
-- The statements that would destroy data are written out but COMMENTED OUT on
-- purpose. Uncomment one only after you have a backup and you are certain.
--
-- Idempotent where it is active: safe to run more than once.

drop index if exists public.media_jobs_created_at_idx;
drop index if exists public.request_log_ts_idx;
drop index if exists public.request_log_route_idx;
drop index if exists public.service_metrics_ts_idx;

drop view if exists public.media_jobs_hourly;
drop view if exists public.request_log_hourly;
drop view if exists public.service_metrics_5min;

drop function if exists public.media_jobs_claim(text, int);
drop function if exists public.media_jobs_finish(bigint, text, boolean, text, int, jsonb);
drop function if exists public.request_log_insert(jsonb);
drop function if exists public.ops_metrics_prune(int);

-- DATA LOSS: -- alter table public.media_jobs drop column if exists started_at;
-- DATA LOSS: -- alter table public.media_jobs drop column if exists duration_ms;
-- DATA LOSS: -- alter table public.media_jobs drop column if exists metrics;

-- DATA LOSS: -- drop table if exists public.request_log cascade;
-- DATA LOSS: -- drop table if exists public.service_metrics cascade;

notify pgrst, 'reload schema';
