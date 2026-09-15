-- IAKIDS: a job queue for the Hebrew tutor's media pipeline.  2026-09-14
--
-- What it replaces (backend-ai-tutor-he/main.py): seven `background_tasks.add_task(...)`
-- calls that generate intro videos, lesson visuals and TTS audio *inside the web
-- process* after the response is sent. Any restart of that process (deploy, crash,
-- Render scaling) kills the work silently, and every long video poll holds one of
-- the web server's threads for up to five minutes.
--
-- With this table the routes only insert a row. A separate worker
-- (backend-ai-tutor-he/worker.py) claims rows, runs the same functions, and marks
-- them done or failed. A job whose worker died is re-queued automatically.
--
-- Access: service role only. The browser never touches this table; the frontend
-- keeps polling the lesson rows it already polls (hero-image / visuals / audio).
--
-- Idempotent: safe to paste more than once.

create table if not exists public.media_jobs (
    id            bigint generated always as identity primary key,
    job_type      text        not null,
    payload       jsonb       not null default '{}'::jsonb,
    dedupe_key    text,
    status        text        not null default 'pending'
                  check (status in ('pending', 'running', 'done', 'failed')),
    attempts      int         not null default 0,
    max_attempts  int         not null default 3,
    run_after     timestamptz not null default now(),
    locked_by     text,
    locked_at     timestamptz,
    error         text,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now(),
    finished_at   timestamptz
);

-- What the worker scans: only pending rows, ordered by when they may run.
create index if not exists media_jobs_pending_idx
    on public.media_jobs (run_after, id)
    where status = 'pending';

-- One live job per (type, key). A lesson opened twice while its audio is still
-- generating gets one audio job, not two. Finished jobs do not block a re-run.
create unique index if not exists media_jobs_live_dedupe_idx
    on public.media_jobs (job_type, dedupe_key)
    where status in ('pending', 'running') and dedupe_key is not null;

-- Handy for "show me every job of this lesson".
create index if not exists media_jobs_dedupe_key_idx
    on public.media_jobs (dedupe_key);

alter table public.media_jobs enable row level security;
-- No policies on purpose: anon/authenticated get nothing, service role bypasses RLS.

-- ---------------------------------------------------------------------------
-- enqueue: insert, or return the id of the live duplicate.
-- ---------------------------------------------------------------------------
create or replace function public.media_jobs_enqueue(
    p_job_type text, p_payload jsonb, p_dedupe_key text default null,
    p_max_attempts int default 3)
returns bigint
language plpgsql security definer set search_path = public as $$
declare
    v_id bigint;
begin
    insert into public.media_jobs (job_type, payload, dedupe_key, max_attempts)
    values (p_job_type, coalesce(p_payload, '{}'::jsonb), p_dedupe_key,
            greatest(1, coalesce(p_max_attempts, 3)))
    on conflict (job_type, dedupe_key)
        where status in ('pending', 'running') and dedupe_key is not null
        do nothing
    returning id into v_id;

    if v_id is null then
        select id into v_id from public.media_jobs
         where job_type = p_job_type and dedupe_key = p_dedupe_key
           and status in ('pending', 'running')
         order by id desc limit 1;
    end if;

    return v_id;
end $$;

-- ---------------------------------------------------------------------------
-- claim: hand a batch of pending jobs to one worker, atomically.
-- SKIP LOCKED means two workers never take the same row and never wait on each other.
-- ---------------------------------------------------------------------------
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
       set status = 'running', locked_by = p_worker, locked_at = now(),
           attempts = j.attempts + 1, updated_at = now()
      from picked
     where j.id = picked.id
    returning j.*;
$$;

-- ---------------------------------------------------------------------------
-- heartbeat: a running worker touches its job so the reaper knows it is alive.
-- ---------------------------------------------------------------------------
create or replace function public.media_jobs_heartbeat(p_id bigint, p_worker text)
returns void
language sql security definer set search_path = public as $$
    update public.media_jobs
       set locked_at = now(), updated_at = now()
     where id = p_id and status = 'running' and locked_by = p_worker;
$$;

-- ---------------------------------------------------------------------------
-- finish: done, or failed-with-retry, or failed-for-good.
-- ---------------------------------------------------------------------------
create or replace function public.media_jobs_finish(
    p_id bigint, p_worker text, p_ok boolean, p_error text default null,
    p_retry_delay_seconds int default 60)
returns void
language plpgsql security definer set search_path = public as $$
declare
    j public.media_jobs%rowtype;
begin
    select * into j from public.media_jobs where id = p_id for update;
    if not found or j.locked_by is distinct from p_worker then
        return;   -- someone else owns it now (reaper re-queued it); leave it alone
    end if;

    if p_ok then
        update public.media_jobs
           set status = 'done', error = null, finished_at = now(), updated_at = now(),
               locked_by = null, locked_at = null
         where id = p_id;
    elsif j.attempts < j.max_attempts then
        update public.media_jobs
           set status = 'pending', error = left(p_error, 4000),
               run_after = now() + make_interval(secs => greatest(1, p_retry_delay_seconds) * j.attempts),
               updated_at = now(), locked_by = null, locked_at = null
         where id = p_id;
    else
        update public.media_jobs
           set status = 'failed', error = left(p_error, 4000), finished_at = now(),
               updated_at = now(), locked_by = null, locked_at = null
         where id = p_id;
    end if;
end $$;

-- ---------------------------------------------------------------------------
-- reaper: a job whose worker stopped heart-beating goes back to pending
-- (or to failed if it already used its attempts). Returns how many it touched.
-- ---------------------------------------------------------------------------
create or replace function public.media_jobs_requeue_stale(p_stale_seconds int default 300)
returns int
language plpgsql security definer set search_path = public as $$
declare
    n int;
begin
    with stale as (
        select id, attempts, max_attempts from public.media_jobs
         where status = 'running'
           and locked_at < now() - make_interval(secs => greatest(30, p_stale_seconds))
         for update skip locked
    )
    update public.media_jobs j
       set status     = case when s.attempts < s.max_attempts then 'pending' else 'failed' end,
           error      = coalesce(j.error, '') || ' [worker lost heartbeat]',
           finished_at = case when s.attempts < s.max_attempts then null else now() end,
           locked_by  = null, locked_at = null, updated_at = now()
      from stale s
     where j.id = s.id;
    get diagnostics n = row_count;
    return n;
end $$;

revoke all on function public.media_jobs_enqueue(text, jsonb, text, int)  from public, anon, authenticated;
revoke all on function public.media_jobs_claim(text, int)                 from public, anon, authenticated;
revoke all on function public.media_jobs_heartbeat(bigint, text)          from public, anon, authenticated;
revoke all on function public.media_jobs_finish(bigint, text, boolean, text, int) from public, anon, authenticated;
revoke all on function public.media_jobs_requeue_stale(int)               from public, anon, authenticated;
