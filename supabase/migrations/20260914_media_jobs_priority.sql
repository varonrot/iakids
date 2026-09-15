-- IAKIDS: priority for media jobs — first-screen media before nice-to-have media.  2026-09-14
--
-- The worker used to take jobs strictly in arrival order, so a child's lesson audio
-- could wait behind another child's three intro videos (seen: 2 min 20 s). Now every
-- job carries a priority (lower runs first) and the worker takes the most urgent
-- pending job. The web process sets it per job type (main.py MEDIA_JOB_PRIORITY):
--   10  unit_lesson_media / unit_lesson_audio   the child is waiting for these
--   30  unit_lesson_visuals (repair on open)     usually all cache hits
--   60  kid_intro_videos                          the standard intro plays meanwhile
--   90  unit_lesson_transition                    disabled feature, cheap no-op
--
-- Additive and idempotent. The 4-argument enqueue is replaced by a 5-argument one
-- whose new argument has a default, so callers that do not send it still work.

alter table public.media_jobs add column if not exists priority integer not null default 50;

drop index if exists public.media_jobs_pending_idx;
create index if not exists media_jobs_pending_idx
    on public.media_jobs (priority, run_after, id)
    where status = 'pending';

create or replace function public.media_jobs_enqueue(
    p_job_type text, p_payload jsonb, p_dedupe_key text default null,
    p_max_attempts int default 3, p_priority int default 50)
returns bigint
language plpgsql security definer set search_path = public as $$
declare
    v_id bigint;
begin
    insert into public.media_jobs (job_type, payload, dedupe_key, max_attempts, priority)
    values (p_job_type, coalesce(p_payload, '{}'::jsonb), p_dedupe_key,
            greatest(1, coalesce(p_max_attempts, 3)), coalesce(p_priority, 50))
    on conflict (job_type, dedupe_key)
        where status in ('pending', 'running') and dedupe_key is not null
        do nothing
    returning id into v_id;

    if v_id is null then
        select id into v_id from public.media_jobs
         where job_type = p_job_type and dedupe_key = p_dedupe_key
           and status in ('pending', 'running')
         order by id desc limit 1;
        -- a more urgent request for the same live job pulls it forward
        update public.media_jobs set priority = least(priority, coalesce(p_priority, 50))
         where id = v_id and status = 'pending';
    end if;

    return v_id;
end $$;

drop function if exists public.media_jobs_enqueue(text, jsonb, text, int);

create or replace function public.media_jobs_claim(p_worker text, p_limit int default 1)
returns setof public.media_jobs
language sql security definer set search_path = public as $$
    with picked as (
        select id from public.media_jobs
         where status = 'pending' and run_after <= now()
         order by priority, run_after, id
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

revoke all on function public.media_jobs_enqueue(text, jsonb, text, int, int) from public, anon, authenticated;
revoke all on function public.media_jobs_claim(text, int) from public, anon, authenticated;
