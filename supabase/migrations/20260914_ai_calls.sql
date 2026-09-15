-- IAKIDS: one row per AI model call — provider, model, purpose, tokens, seconds, cost.  2026-09-14
--
-- Before this the tutor kept only running totals (usage_summary per user,
-- tutor_sessions.estimated_cost_usd per session), fed by the chat route and the live
-- TTS route only. Lesson generation, background audio, images and intro videos were
-- never counted, and nothing recorded which model or provider answered.
--
-- ai_calls is written by backend-ai-tutor-he/ai_costs.py: every OpenAI / Gemini /
-- OpenRouter call, from the web process and from the worker, in batches.
--   cost_source:  'provider'  exact cost reported by the provider (OpenRouter)
--                 'estimated' tokens × price table (OpenAI direct, Gemini direct)
--                 'unknown'   no price known for the model (cost_usd is null)
-- Sum cost_usd for money; group by provider/model/purpose for where it goes.
--
-- Service role only. Retention: ops_metrics_prune() also prunes this table.
-- Additive and idempotent.

create table if not exists public.ai_calls (
    id              bigint generated always as identity primary key,
    ts              timestamptz not null default now(),
    service         text not null,                 -- 'tutor-web' | 'tutor-worker'
    instance        text not null,
    provider        text not null,                 -- 'openai' | 'gemini' | 'openrouter'
    model           text not null,                 -- 'gpt-4o-mini', 'google/gemini-3.1-flash-tts-preview', ...
    purpose         text,                          -- 'chat' | 'lesson' | 'tts' | 'tts_live' | 'image' | 'video' | 'coach' | 'homework' | ...
    user_id         uuid,
    kid_id          uuid,
    unit_lesson_id  integer,
    input_tokens    integer,
    output_tokens   integer,
    cached_tokens   integer,
    audio_seconds   real,
    images          integer,
    latency_ms      integer,
    status          text not null default 'ok',    -- 'ok' | 'error'
    error           text,
    cost_usd        numeric(12, 6),
    cost_source     text not null default 'unknown',
    generation_id   text,                          -- OpenRouter id, for exact-cost reconciliation
    extra           jsonb
);
create index if not exists ai_calls_ts_idx       on public.ai_calls (ts);
create index if not exists ai_calls_model_idx    on public.ai_calls (provider, model, ts);
create index if not exists ai_calls_purpose_idx  on public.ai_calls (purpose, ts);
create index if not exists ai_calls_kid_idx      on public.ai_calls (kid_id, ts);
create index if not exists ai_calls_unresolved_idx on public.ai_calls (generation_id)
    where cost_source = 'pending';
alter table public.ai_calls enable row level security;

create or replace function public.ai_calls_insert(p_rows jsonb)
returns int
language plpgsql security definer set search_path = public as $$
declare n int;
begin
    insert into public.ai_calls (ts, service, instance, provider, model, purpose, user_id, kid_id, unit_lesson_id,
                                 input_tokens, output_tokens, cached_tokens, audio_seconds, images, latency_ms,
                                 status, error, cost_usd, cost_source, generation_id, extra)
    select coalesce((r->>'ts')::timestamptz, now()), r->>'service', r->>'instance', r->>'provider', r->>'model',
           r->>'purpose', nullif(r->>'user_id', '')::uuid, nullif(r->>'kid_id', '')::uuid,
           nullif(r->>'unit_lesson_id', '')::int,
           nullif(r->>'input_tokens', '')::int, nullif(r->>'output_tokens', '')::int, nullif(r->>'cached_tokens', '')::int,
           nullif(r->>'audio_seconds', '')::real, nullif(r->>'images', '')::int, nullif(r->>'latency_ms', '')::int,
           coalesce(r->>'status', 'ok'), r->>'error', nullif(r->>'cost_usd', '')::numeric,
           coalesce(r->>'cost_source', 'unknown'), r->>'generation_id', r->'extra'
      from jsonb_array_elements(coalesce(p_rows, '[]'::jsonb)) r;
    get diagnostics n = row_count;
    return n;
end $$;

-- exact cost arrives later for OpenRouter TTS (looked up by generation id)
create or replace function public.ai_calls_set_cost(p_generation_id text, p_cost_usd numeric, p_extra jsonb default null)
returns int
language plpgsql security definer set search_path = public as $$
declare n int;
begin
    update public.ai_calls
       set cost_usd = p_cost_usd, cost_source = 'provider',
           extra = coalesce(extra, '{}'::jsonb) || coalesce(p_extra, '{}'::jsonb)
     where generation_id = p_generation_id and cost_source = 'pending';
    get diagnostics n = row_count;
    return n;
end $$;

-- prune ai_calls with the other metrics
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
    -- money is kept a year: 12× the metrics retention
    delete from public.ai_calls where ts < now() - make_interval(days => greatest(1, p_days) * 12);
    get diagnostics n = row_count; total := total + n;
    return total;
end $$;

-- ready-made views
create or replace view public.ai_costs_daily as
select date_trunc('day', ts) as day, provider, model, purpose,
       count(*)                                        as calls,
       count(*) filter (where status <> 'ok')          as errors,
       sum(input_tokens)                               as input_tokens,
       sum(output_tokens)                              as output_tokens,
       round(sum(audio_seconds)::numeric, 1)           as audio_seconds,
       sum(images)                                     as images,
       round(avg(latency_ms))::int                     as avg_latency_ms,
       round(sum(cost_usd), 4)                         as cost_usd,
       count(*) filter (where cost_source = 'unknown') as calls_without_price
  from public.ai_calls
 group by 1, 2, 3, 4 order by 1 desc, 11 desc nulls last;

create or replace view public.ai_costs_per_kid as
select kid_id, date_trunc('day', ts) as day, count(*) as calls, round(sum(cost_usd), 4) as cost_usd
  from public.ai_calls where kid_id is not null
 group by 1, 2 order by 2 desc, 4 desc nulls last;

create or replace view public.ai_costs_per_lesson as
select unit_lesson_id, count(*) as calls,
       round(sum(cost_usd) filter (where purpose in ('tts', 'image', 'video', 'lesson')), 4) as media_cost_usd,
       round(sum(cost_usd), 4) as cost_usd, min(ts) as first_call, max(ts) as last_call
  from public.ai_calls where unit_lesson_id is not null
 group by 1 order by 4 desc nulls last;

alter view public.ai_costs_daily      set (security_invoker = true);
alter view public.ai_costs_per_kid    set (security_invoker = true);
alter view public.ai_costs_per_lesson set (security_invoker = true);
revoke all on public.ai_calls, public.ai_costs_daily, public.ai_costs_per_kid, public.ai_costs_per_lesson
  from anon, authenticated;
revoke all on function public.ai_calls_insert(jsonb)                       from public, anon, authenticated;
revoke all on function public.ai_calls_set_cost(text, numeric, jsonb)      from public, anon, authenticated;
revoke all on function public.ops_metrics_prune(int)                       from public, anon, authenticated;
