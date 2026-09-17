-- IAKIDS: a parent sees only their own children's coach sessions.  2026-09-17
--
-- Found by signing in as a brand new account with no data of its own and reading every
-- table the browser still touches. Twenty-two of them came back empty, correctly
-- isolated. `learning_coach_sessions` came back with other accounts' rows.
--
-- What was readable: kid_id, lesson_id, unit_lesson_id, the understanding score the
-- teacher gave at the start and at the end, how many rounds the dialogue took, and the
-- timestamps. That is another child's performance, lesson by lesson. Not their words —
-- kid_lesson_history is properly isolated — but enough to follow a child's difficulty
-- with a subject.
--
-- The table had row level security with no policy restricting rows, which in practice
-- meant "any signed-in account". It now matches kid_unit_lesson_progress, written in
-- the 2026-09-10 audit: a row is visible when the child belongs to the caller.
--
-- Reads: he/workspace and he/games/workspace, both already filtering by kid_id.
-- Writes: the tutor backend under the service role, which policies do not restrict, so
-- there is deliberately no write policy.
--
-- Idempotent: safe to run more than once.

alter table public.learning_coach_sessions enable row level security;

drop policy if exists lcs_select_own on public.learning_coach_sessions;
create policy lcs_select_own on public.learning_coach_sessions
    for select to authenticated
    using (kid_id in (select id from public.kids_profiles where user_id = auth.uid()));

notify pgrst, 'reload schema';

-- Check afterwards, signed in as an ordinary account:
--   select count(*) from public.learning_coach_sessions;
--   -- expected: only the rows of that account's own children
