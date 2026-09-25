-- IAKIDS: English voice tutor sessions (backend-ai-tutor-he/english_tutor.py).  2026-09-25
--
-- One row per conversation between a child and the English tutor ("Hebrew explanations,
-- English is the subject", decided 2026-09-15). The server keeps the conversation here, so
-- the browser never sends a history that could be forged, and a second web process or
-- server sees the same session (nothing lives in process memory).
--
-- seconds_used feeds the daily allowance: free children get ENGLISH_FREE_SECONDS_PER_DAY
-- (10 minutes by default), paying families ENGLISH_PAID_SECONDS_PER_DAY. The allowance is
-- the sum of today's rows (Israel time) for the child.
--
-- Access: service role only. RLS on with no policies, browser grants revoked.
-- Idempotent: safe to paste more than once. Nothing existing is changed.

create table if not exists public.english_tutor_sessions (
    id                  uuid        primary key default gen_random_uuid(),
    user_id             uuid        not null,
    kid_id              uuid        not null,
    level               text        not null default 'beginner'
                        check (level in ('beginner', 'elementary', 'intermediate')),
    topic               text,
    status              text        not null default 'active'
                        check (status in ('active', 'ended')),
    turns               int         not null default 0,
    seconds_used        int         not null default 0,
    spoken_corrections  int         not null default 0,
    history             jsonb       not null default '[]'::jsonb,
    words               jsonb       not null default '[]'::jsonb,
    summary             jsonb,
    started_at          timestamptz not null default now(),
    last_turn_at        timestamptz,
    ended_at            timestamptz,
    updated_at          timestamptz not null default now()
);

-- today's allowance and "my last sessions" are both read by child, newest first
create index if not exists english_tutor_sessions_kid_started_idx
    on public.english_tutor_sessions (kid_id, started_at desc);

alter table public.english_tutor_sessions enable row level security;
-- No policies on purpose: anon/authenticated get nothing, the service role bypasses RLS.
revoke all on public.english_tutor_sessions from anon, authenticated;
