-- ═══════════════════════════════════════════════════════════════════════════
-- IAKIDS — everything waiting to be applied, in one paste.  2026-09-10
--
-- Supabase dashboard → SQL Editor → New query → paste all of this → Run.
--
-- It is four migrations, in the order they have to run. Every one of them is
-- `create or replace` / `if not exists`, so running this twice changes nothing
-- and running it on a database that already has some of it is fine.
--
-- Each file is also in supabase/migrations/ on its own, with the reasoning in
-- its header. This is only a convenience: one paste instead of four.
--
-- What it changes:

--   1. 20260910_rls_findings.sql          סוגר חמש טבלאות פתוחות, ומונע מנוי בתשלום מהדפדפן
--   2. 20260910_game_bank_batch.sql       סבב תשובות בקריאה אחת (מחליף את הגרסה השבורה)
--   3. 20260910_chat_quota.sql            מכסת הודעות אטומית, לפי התוכנית, מתאפסת כל חודש
--   4. 20260910_user_locations.sql        מדינה ואזור זמן לכל חשבון
--
-- Afterwards, from the repo:  backend/.venv/bin/python tools/security_check.py
-- should report 12 findings instead of 17. The twelve left are /docs, /redoc and
-- /openapi.json on two backends (a Render deploy away) and six missing response
-- headers (a Cloudflare setting away). None of them is SQL.
-- ═══════════════════════════════════════════════════════════════════════════



-- ───────────────────────────────────────────────────────────────────────────
-- 1/4  ·  20260910_rls_findings.sql
-- ───────────────────────────────────────────────────────────────────────────

-- IAKIDS: close the five tables the audit found open, and stop a browser from
-- writing itself a paid subscription.
--
-- Verified on the live database, 2026-09-10, with the publishable key every visitor
-- holds and with a throwaway account:
--
--   subscriptions              a new free account inserted plan='annual',
--                              expires_at='2099-01-01' and was ACCEPTED. The tutor's
--                              is_paid_active_subscription reads exactly those
--                              fields, so that row is a lifetime paid account.
--   kid_unit_lesson_progress   4 rows to an anonymous caller, and an anonymous
--                              INSERT was stopped only by a NOT NULL constraint —
--                              no policy stood in its way.
--   exam_answer_keys           14 answer keys, anonymous.
--   exam_questions / exams     14 questions and the exam list, anonymous.
--   lesson_units_content       150 rows of model-generated lesson content, anonymous.
--
-- What still works afterwards: the workspace reads its own child's progress and the
-- lesson content while signed in; onboarding still creates the free subscription row.
-- What stops working: reading any of it without an account, and writing a paid plan
-- from a browser at all.
--
-- Idempotent: safe to paste more than once.

-- =====================================================================
-- 1. subscriptions — a client may create the free row, and nothing else
-- =====================================================================
-- The existing policies are not in the repo, so drop whatever is there by name and
-- put back exactly the two a browser needs.
do $$
declare p record;
begin
    for p in select policyname from pg_policies
              where schemaname = 'public' and tablename = 'subscriptions' loop
        execute format('drop policy %I on public.subscriptions', p.policyname);
    end loop;
end $$;

alter table public.subscriptions enable row level security;

-- Read your own row: the app checks its own plan.
create policy subscriptions_select_own on public.subscriptions
    for select to authenticated
    using (user_id = auth.uid());

-- Create your own *free* row, which is all onboarding/prepare-user does. Every field
-- that decides whether an account is paid is pinned here, so the row a browser can
-- write is never a paid one.
create policy subscriptions_insert_free on public.subscriptions
    for insert to authenticated
    with check (user_id = auth.uid()
                and plan = 'free'
                and status = 'active'
                and expires_at is null
                and canceled_at is null
                and lemon_subscription_id is null
                and lemon_customer_id is null
                and lemon_order_id is null);

-- No UPDATE and no DELETE policy: paid rows are written by the LemonSqueezy webhook
-- with the service role, which is not subject to RLS. Raising your own plan is now
-- impossible from a browser, whatever it sends.

-- =====================================================================
-- 2. kid_unit_lesson_progress — a parent sees their own children
-- =====================================================================
alter table public.kid_unit_lesson_progress enable row level security;

drop policy if exists kulp_select_own on public.kid_unit_lesson_progress;
create policy kulp_select_own on public.kid_unit_lesson_progress
    for select to authenticated
    using (kid_id in (select id from public.kids_profiles where user_id = auth.uid()));

-- The workspace only reads this table; the tutor backend writes it with the service
-- role. So there is deliberately no write policy.

-- =====================================================================
-- 3. exams — questions to a signed-in account, answer keys to nobody
-- =====================================================================
alter table public.exams            enable row level security;
alter table public.exam_pages       enable row level security;
alter table public.exam_questions   enable row level security;
alter table public.exam_answer_keys enable row level security;

drop policy if exists exams_read on public.exams;
create policy exams_read on public.exams
    for select to authenticated using (coalesce(is_active, true));

drop policy if exists exam_pages_read on public.exam_pages;
create policy exam_pages_read on public.exam_pages
    for select to authenticated using (true);

drop policy if exists exam_questions_read on public.exam_questions;
create policy exam_questions_read on public.exam_questions
    for select to authenticated using (true);

-- exam_answer_keys gets no policy at all. With RLS on and no policy, no client can
-- read a single row; grading happens in the backend under the service role. An answer
-- key that a browser can read is not an answer key.

-- =====================================================================
-- 4. lesson_units_content — for accounts, not for the open internet
-- =====================================================================
-- This is what the model was paid to write. The workspace, the lesson page and the
-- parent panel all read it directly, so it stays readable to a signed-in account;
-- what stops is anyone copying the curriculum without one.
alter table public.lesson_units_content enable row level security;

drop policy if exists lesson_units_content_read on public.lesson_units_content;
create policy lesson_units_content_read on public.lesson_units_content
    for select to authenticated using (true);

-- =====================================================================
-- 5. Did anyone already do it?
-- =====================================================================
-- Run this after pasting. Every row it returns is a paid plan with no payment behind
-- it — either created from a browser, or entered by hand.
--
--   select id, user_id, plan, status, created_at, expires_at
--     from public.subscriptions
--    where plan <> 'free'
--      and lemon_subscription_id is null;

comment on table public.subscriptions is
    'One row per account. A browser may insert only its own free row (subscriptions_insert_free) and may not update anything: paid rows come from the LemonSqueezy webhook under the service role.';
comment on table public.exam_answer_keys is
    'Answer keys. RLS on with no policy: unreadable by any client, served only through the backend.';


-- ───────────────────────────────────────────────────────────────────────────
-- 2/4  ·  20260910_game_bank_batch.sql
-- ───────────────────────────────────────────────────────────────────────────

-- IAKIDS: a whole round of answers in one call.
--
-- Measured on 2026-09-10: the database saturates at ~550 requests/second for
-- game_next_questions and ~700 for game_record_answer, and a ten-question session
-- spends 10 of its 14 calls recording answers one at a time. Sending them together
-- turns those 10 calls into 1 — a session costs 4 calls instead of 14, and the same
-- database serves three to four times as many children.
--
-- The browser keeps the answers in an outbox (IAKidsOutbox in games/game-sdk.js) and
-- flushes every few answers, when the tab is hidden, and when a game ends. Anything
-- still unsent survives in IndexedDB and goes out on the next visit, so a closed tab
-- now loses nothing — today's per-answer call loses whatever was in flight.
--
-- Everything game_record_answer checks, this checks too, and the child-ownership
-- lookup happens once for the whole batch instead of once per answer.
--
-- Idempotent: safe to paste more than once. Requires 20260910_game_bank_one_call.sql.

create or replace function public.game_record_answers(p_kid uuid, p_answers jsonb)
returns int
language plpgsql security definer set search_path = public as $$
declare
    ans jsonb;
    payload jsonb;
    n int := 0;
begin
    if not exists (select 1 from public.kids_profiles k
                    where k.id = p_kid and k.user_id = auth.uid()) then
        raise exception 'not your child' using errcode = '42501';
    end if;

    if p_answers is null or jsonb_typeof(p_answers) <> 'array' then
        return 0;
    end if;
    -- A round is ten questions and the outbox flushes well before fifty. A larger
    -- array is not a child playing.
    if jsonb_array_length(p_answers) > 50 then
        raise exception 'too many answers in one call' using errcode = '54000';
    end if;

    for ans in select * from jsonb_array_elements(p_answers) loop
        if ans->>'game' is null or ans->>'key' is null then
            continue;
        end if;

        -- The question, when this child's browser generated it. Same terms as
        -- game_record_answer: unverified and pending, so a client still cannot put
        -- a row into the served set.
        payload := ans->'payload';
        if payload is not null and jsonb_typeof(payload) <> 'null'
           and octet_length(payload::text) <= 8192
           and payload::text !~ '[<>]' then
            insert into public.game_questions
                (game_code, level, qkey, payload, answer, source, verified, verify_state)
            values
                (ans->>'game', coalesce((ans->>'level')::smallint, 0), ans->>'key',
                 payload, ans->>'answer', 'generated', false, 'pending')
            on conflict (game_code, qkey) do nothing;
        end if;

        insert into public.kid_question_answers
            (kid_id, game_code, qkey, correct, response_ms, level, session_id)
        values
            (p_kid, ans->>'game', ans->>'key', coalesce((ans->>'correct')::boolean, false),
             least(coalesce((ans->>'ms')::int, 0), 3600000),
             (ans->>'level')::smallint, (ans->>'session')::uuid);

        n := n + 1;
    end loop;

    -- The counters for the whole batch in one statement, rather than one update
    -- per answer: this is the part that touches the 106k-row shared table.
    update public.game_questions q
       set times_asked   = q.times_asked + b.asked,
           times_correct = q.times_correct + b.correct,
           updated_at    = now()
      from (
        select e->>'game' as game_code, e->>'key' as qkey,
               count(*)::int as asked,
               count(*) filter (where (e->>'correct')::boolean)::int as correct
          from jsonb_array_elements(p_answers) e
         where e->>'game' is not null and e->>'key' is not null
         group by 1, 2
      ) b
     where q.game_code = b.game_code and q.qkey = b.qkey;

    return n;
end;
$$;

revoke all on function public.game_record_answers(uuid, jsonb) from public, anon;
grant execute on function public.game_record_answers(uuid, jsonb) to authenticated;

comment on function public.game_record_answers is
    'A round of answers in one call: files any generated questions, logs every answer, and bumps the counters in a single statement. Verifies the child belongs to auth.uid() once for the batch.';


-- ───────────────────────────────────────────────────────────────────────────
-- 3/4  ·  20260910_chat_quota.sql
-- ───────────────────────────────────────────────────────────────────────────

-- IAKIDS: a message quota that knows who is paying, and cannot be raced past.
--
-- What it replaces (backend/main.py): `LIMIT = 20  # זמני לבדיקה`, a read of
-- messages_used followed later by a write of used + 1. Two problems, both live:
--
--   * a paying customer is cut off after twenty messages exactly like a free one —
--     the check never looks at plan, status or expires_at;
--   * read-then-write is not atomic, so two requests that arrive together both read
--     19, both write 20, and the quota is worth whatever the concurrency is.
--
-- This does the whole thing in one statement under a row lock, and returns what the
-- caller needs to answer with. The limits stay in the backend (env-configurable) and
-- are passed in, so changing a price does not need a migration.
--
-- The period is a calendar month. A quota that never resets is not a quota, it is a
-- lifetime cap — which is what the site has today.
--
-- Idempotent: safe to paste more than once.

alter table public.subscriptions
    add column if not exists messages_period_start date;

create or replace function public.chat_consume_message(
    p_user uuid, p_free_limit int, p_paid_limit int)
returns jsonb
language plpgsql security definer set search_path = public as $$
declare
    s public.subscriptions%rowtype;
    period date := date_trunc('month', now())::date;
    paid boolean;
    lim int;
    used int;
begin
    select * into s from public.subscriptions where user_id = p_user for update;
    if not found then
        -- No row yet: onboarding creates one, but a chat can arrive first.
        insert into public.subscriptions (user_id, plan, status, messages_used, messages_period_start)
        values (p_user, 'free', 'active', 0, period)
        returning * into s;
    end if;

    paid := coalesce(s.plan, 'free') <> 'free'
            and coalesce(s.status, '') = 'active'
            and s.canceled_at is null
            and (s.expires_at is null or s.expires_at > now());
    lim := greatest(coalesce(case when paid then p_paid_limit else p_free_limit end, 0), 0);

    -- A new month starts the count again.
    used := case when s.messages_period_start is distinct from period
                 then 0 else coalesce(s.messages_used, 0) end;

    if used >= lim then
        update public.subscriptions
           set messages_used = used, messages_period_start = period
         where user_id = p_user;
        return jsonb_build_object('allowed', false, 'used', used, 'limit', lim,
                                  'plan', s.plan, 'paid', paid, 'period', period);
    end if;

    update public.subscriptions
       set messages_used = used + 1, messages_period_start = period
     where user_id = p_user;

    return jsonb_build_object('allowed', true, 'used', used + 1, 'limit', lim,
                              'plan', s.plan, 'paid', paid, 'period', period);
end;
$$;

-- The backend calls this with the service role. No client has any business spending
-- someone's quota, so nobody else may execute it.
revoke all on function public.chat_consume_message(uuid, int, int) from public, anon, authenticated;

comment on function public.chat_consume_message is
    'Counts one chat message against the account''s monthly quota, atomically under a row lock, with the limit chosen by whether the subscription is actually paid and current. Returns {allowed, used, limit, plan, paid, period}.';


-- ───────────────────────────────────────────────────────────────────────────
-- 4/4  ·  20260910_user_locations.sql
-- ───────────────────────────────────────────────────────────────────────────

-- IAKIDS: which country a family is in.
--
-- Nothing in the database says where anyone is: Google hands back a name, an email
-- and a picture, and that is all we ever stored. So "how many customers, and from
-- where" has no answer today, and the one paying customer who is not the owner can
-- only be guessed at from the spelling of a name.
--
-- Cloudflare already knows. Every request through it carries the country, and it
-- publishes the answer to the page itself at /cdn-cgi/trace — so the browser can read
-- its own country without a server, an IP lookup service, or a third party.
--
-- What is stored is the country, the region and the browser's own timezone. **Not the
-- IP address.** An IP is personal data, it identifies a household rather than a
-- country, and it would sit in a database about children; the country is what the
-- question actually needs. The timezone comes from the browser and covers the mirror
-- domain, which does not go through Cloudflare and so has no /cdn-cgi/trace.
--
-- One row per user, overwritten as they travel; first_seen keeps the original.
-- Idempotent: safe to paste more than once.

create table if not exists public.user_locations (
    user_id     uuid primary key references auth.users (id) on delete cascade,
    country     text,                       -- ISO-3166 alpha-2, from Cloudflare
    region      text,
    timezone    text,                       -- IANA, from the browser
    source      text,                       -- 'cloudflare' | 'timezone'
    first_seen  timestamptz not null default now(),
    last_seen   timestamptz not null default now(),
    first_country text                      -- where they were the first time we asked
);

alter table public.user_locations enable row level security;

-- A parent may see their own row and nothing else. Writing goes through the function
-- below, which is the only thing that may set a country, so a client cannot claim to
-- be somewhere it is not by writing the row directly.
drop policy if exists user_locations_read_own on public.user_locations;
create policy user_locations_read_own on public.user_locations
    for select using (user_id = auth.uid());

create or replace function public.record_user_location(
    p_country text default null, p_region text default null,
    p_timezone text default null, p_source text default null)
returns void
language plpgsql security definer set search_path = public as $$
declare
    c text := nullif(upper(substring(coalesce(p_country, '') from 1 for 2)), '');
    r text := nullif(substring(coalesce(p_region, '') from 1 for 80), '');
    z text := nullif(substring(coalesce(p_timezone, '') from 1 for 64), '');
begin
    if auth.uid() is null then
        raise exception 'not signed in' using errcode = '42501';
    end if;
    -- Cloudflare answers XX for an address it cannot place and T1 for Tor. Neither is
    -- a country, and storing one would overwrite a real answer from an earlier visit.
    if c is not null and (c !~ '^[A-Z]{2}$' or c in ('XX', 'T1')) then c := null; end if;

    insert into public.user_locations (user_id, country, region, timezone, source, first_country)
    values (auth.uid(), c, r, z, nullif(p_source, ''), c)
    on conflict (user_id) do update
       set country   = coalesce(excluded.country, user_locations.country),
           region    = coalesce(excluded.region, user_locations.region),
           timezone  = coalesce(excluded.timezone, user_locations.timezone),
           source    = coalesce(excluded.source, user_locations.source),
           last_seen = now(),
           first_country = coalesce(user_locations.first_country, excluded.country);
end;
$$;

revoke all on function public.record_user_location(text, text, text, text) from public, anon;
grant execute on function public.record_user_location(text, text, text, text) to authenticated;

comment on table public.user_locations is
    'Country and timezone per parent account, from Cloudflare''s /cdn-cgi/trace and the browser. No IP address is stored: the country is what the question needs and an IP identifies a household.';


-- ═══════════════════════════════════════════════════════════════════════════
-- Did it work? Run these three afterwards.
-- ═══════════════════════════════════════════════════════════════════════════

-- 1. Nothing open to a visitor without an account. Every row should say `t`.
select 'kid_unit_lesson_progress' as t, relrowsecurity as rls_on from pg_class where relname = 'kid_unit_lesson_progress'
union all select 'exam_answer_keys',      relrowsecurity from pg_class where relname = 'exam_answer_keys'
union all select 'exam_questions',        relrowsecurity from pg_class where relname = 'exam_questions'
union all select 'exams',                 relrowsecurity from pg_class where relname = 'exams'
union all select 'lesson_units_content',  relrowsecurity from pg_class where relname = 'lesson_units_content'
union all select 'subscriptions',         relrowsecurity from pg_class where relname = 'subscriptions';

-- 2. A browser may only insert its own free row. Expect exactly two policies:
--    subscriptions_select_own (SELECT) and subscriptions_insert_free (INSERT).
select policyname, cmd from pg_policies
 where schemaname = 'public' and tablename = 'subscriptions' order by cmd;

-- 3. Has anyone already given themselves a paid plan? Every row here is a paid
--    subscription with no payment behind it.
select id, user_id, plan, status, created_at, expires_at
  from public.subscriptions
 where plan <> 'free' and lemon_subscription_id is null;

