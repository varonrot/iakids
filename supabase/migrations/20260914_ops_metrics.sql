-- IAKIDS: operational metrics for the Hebrew tutor, so capacity can be analysed
-- from the database instead of from a terminal on one machine.  2026-09-14
--
-- Three things:
--   1. media_jobs gets started_at / duration_ms / metrics, and the claim/finish
--      RPCs fill them. Wait time = started_at - created_at; run time = duration_ms.
--   2. request_log: one row per /api/* request (route, status, duration). Written
--      in batches by the web process (backend-ai-tutor-he/ops_metrics.py).
--   3. service_metrics: every 30s each process (web / worker, per instance) writes
--      its RSS, CPU%, free memory, load, busy threads, running jobs, queue depth.
--
-- Access: service role only. Retention: ops_metrics_prune(days) — the worker
-- calls it once a day with OPS_METRICS_RETENTION_DAYS (default 30).
--
-- Additive and idempotent: safe to paste more than once; nothing existing changes.

alter table public.media_jobs add column if not exists started_at  timestamptz;
alter table public.media_jobs add column if not exists duration_ms integer;
alter table public.media_jobs add column if not exists metrics     jsonb;

create index if not exists media_jobs_created_at_idx on public.media_jobs (created_at);

-- claim: also stamp started_at (locked_at is refreshed by heartbeats, so it cannot
-- serve as the start time).
create or replace function public.media_jobs_claim(p_worker text, p_limit int default 1)
returns setof public.media_jobs
language sql security definer set search_path = public as $$
    with picked as (
        select id from public.media_jobs
         where status = 'pending' and run_after <= now()
         order by run_after, id
         limit greatest(1, coalesce(p_limit, 1))
         for update skip locked
    )
    update public.media_jobs j
       set status = 'running', locked_by = p_worker, locked_at = now(), started_at = now(),
           attempts = j.attempts + 1, updated_at = now()
      from picked
     where j.id = picked.id
    returning j.*;
$$;

-- finish: same as before plus duration_ms and a metrics blob from the worker.
-- The old 5-argument signature stays callable (p_metrics defaults to null).
create or replace function public.media_jobs_finish(
    p_id bigint, p_worker text, p_ok boolean, p_error text default null,
    p_retry_delay_seconds int default 60, p_metrics jsonb default null)
returns void
language plpgsql security definer set search_path = public as $$
declare
    j public.media_jobs%rowtype;
    v_ms integer;
begin
    select * into j from public.media_jobs where id = p_id for update;
    if not found or j.locked_by is distinct from p_worker then
        return;
    end if;
    v_ms := case when j.started_at is null then null
                 else (extract(epoch from (now() - j.started_at)) * 1000)::integer end;

    if p_ok then
        update public.media_jobs
           set status = 'done', error = null, finished_at = now(), updated_at = now(),
               locked_by = null, locked_at = null, duration_ms = v_ms,
               metrics = coalesce(p_metrics, metrics)
         where id = p_id;
    elsif j.attempts < j.max_attempts then
        update public.media_jobs
           set status = 'pending', error = left(p_error, 4000),
               run_after = now() + make_interval(secs => greatest(1, p_retry_delay_seconds) * j.attempts),
               updated_at = now(), locked_by = null, locked_at = null, duration_ms = v_ms,
               metrics = coalesce(p_metrics, metrics)
         where id = p_id;
    else
        update public.media_jobs
           set status = 'failed', error = left(p_error, 4000), finished_at = now(),
               updated_at = now(), locked_by = null, locked_at = null, duration_ms = v_ms,
               metrics = coalesce(p_metrics, metrics)
         where id = p_id;
    end if;
end $$;

drop function if exists public.media_jobs_finish(bigint, text, boolean, text, int);
revoke all on function public.media_jobs_finish(bigint, text, boolean, text, int, jsonb) from public, anon, authenticated;
revoke all on function public.media_jobs_claim(text, int) from public, anon, authenticated;

-- ---------------------------------------------------------------------------
create table if not exists public.request_log (
    id          bigint generated always as identity primary key,
    ts          timestamptz not null default now(),
    service     text not null,            -- 'tutor-web'
    instance    text not null,            -- host:pid
    route       text not null,            -- '/api/tutor/unit-lesson' (template, not the raw path)
    method      text not null,
    status      integer not null,
    duration_ms integer not null,
    user_id     uuid,
    kid_id      uuid,
    extra       jsonb
);
create index if not exists request_log_ts_idx    on public.request_log (ts);
create index if not exists request_log_route_idx on public.request_log (route, ts);
alter table public.request_log enable row level security;

create table if not exists public.service_metrics (
    id                bigint generated always as identity primary key,
    ts                timestamptz not null default now(),
    service           text not null,      -- 'tutor-web' | 'tutor-worker'
    instance          text not null,
    rss_mb            integer,
    cpu_pct           real,
    mem_available_mb  integer,
    load1             real,
    threads_busy      integer,            -- web: worker threads in use; worker: jobs running
    jobs_running      integer,
    queue_pending     integer,
    extra             jsonb
);
create index if not exists service_metrics_ts_idx on public.service_metrics (service, ts);
alter table public.service_metrics enable row level security;

-- Batch insert for request_log rows (one round trip per flush).
create or replace function public.request_log_insert(p_rows jsonb)
returns int
language plpgsql security definer set search_path = public as $$
declare n int;
begin
    insert into public.request_log (ts, service, instance, route, method, status, duration_ms, user_id, kid_id, extra)
    select coalesce((r->>'ts')::timestamptz, now()), r->>'service', r->>'instance', r->>'route', r->>'method',
           (r->>'status')::int, (r->>'duration_ms')::int,
           nullif(r->>'user_id', '')::uuid, nullif(r->>'kid_id', '')::uuid, r->'extra'
      from jsonb_array_elements(coalesce(p_rows, '[]'::jsonb)) r;
    get diagnostics n = row_count;
    return n;
end $$;

create or replace function public.ops_metrics_prune(p_days int default 30)
returns int
language plpgsql security definer set search_path = public as $$
declare n int; total int := 0;
begin
    delete from public.request_log     where ts < now() - make_interval(days => greatest(1, p_days));
    get diagnostics n = row_count; total := total + n;
    delete from public.service_metrics where ts < now() - make_interval(days => greatest(1, p_days));
    get diagnostics n = row_count; total := total + n;
    delete from public.media_jobs where status in ('done', 'failed')
       and finished_at < now() - make_interval(days => greatest(1, p_days));
    get diagnostics n = row_count; total := total + n;
    return total;
end $$;

revoke all on function public.request_log_insert(jsonb) from public, anon, authenticated;
revoke all on function public.ops_metrics_prune(int)    from public, anon, authenticated;

-- ---------------------------------------------------------------------------
-- Ready-made views for the analysis.
-- ---------------------------------------------------------------------------
-- Jobs: wait, run, attempts, per type per hour.
create or replace view public.media_jobs_hourly as
select date_trunc('hour', created_at) as hour, job_type, status,
       count(*)                                                        as jobs,
       round(avg(extract(epoch from (started_at - created_at))))::int  as avg_wait_s,
       round(max(extract(epoch from (started_at - created_at))))::int  as max_wait_s,
       round(avg(duration_ms) / 1000.0)::int                           as avg_run_s,
       round(max(duration_ms) / 1000.0)::int                           as max_run_s,
       max(attempts)                                                   as max_attempts
  from public.media_jobs
 group by 1, 2, 3 order by 1 desc, 2;

-- Requests: latency percentiles per route per hour.
create or replace view public.request_log_hourly as
select date_trunc('hour', ts) as hour, route,
       count(*)                                                               as requests,
       count(*) filter (where status >= 500)                                  as errors_5xx,
       count(*) filter (where status = 429)                                   as rate_limited,
       percentile_cont(0.5) within group (order by duration_ms)::int          as p50_ms,
       percentile_cont(0.9) within group (order by duration_ms)::int          as p90_ms,
       max(duration_ms)                                                       as max_ms
  from public.request_log
 group by 1, 2 order by 1 desc, 3 desc;

-- Resources: per service/instance per 5 minutes.
create or replace view public.service_metrics_5min as
select to_timestamp(floor(extract(epoch from ts) / 300) * 300) as bucket, service, instance,
       max(rss_mb) as peak_rss_mb, round(avg(cpu_pct))::int as avg_cpu_pct, max(cpu_pct) as peak_cpu_pct,
       min(mem_available_mb) as min_mem_available_mb, max(load1) as peak_load1,
       max(threads_busy) as peak_threads_busy, max(jobs_running) as peak_jobs_running, max(queue_pending) as peak_queue
  from public.service_metrics
 group by 1, 2, 3 order by 1 desc, 2, 3;

-- Supabase grants new public tables/views to anon+authenticated by default, and a
-- view runs as its owner, which would bypass the RLS on the tables under it.
-- Both closed here: the views check the caller's rights, and the caller has none.
alter view public.media_jobs_hourly      set (security_invoker = true);
alter view public.request_log_hourly     set (security_invoker = true);
alter view public.service_metrics_5min   set (security_invoker = true);
revoke all on public.request_log, public.service_metrics, public.media_jobs,
              public.media_jobs_hourly, public.request_log_hourly, public.service_metrics_5min
  from anon, authenticated;
