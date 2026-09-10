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
