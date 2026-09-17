-- ============================================================================
-- IAKIDS — what still has to be run against the database
-- Checked against the live project on 2026-09-17 at 16:03 UTC.
--
-- Everything else in this folder is already applied. Verified one by one, by
-- looking for the object each migration creates:
--
--   applied  20260904_create_kid_unit_lesson_progress
--   applied  20260908_game_question_bank
--   applied  20260909_game_question_verification
--   applied  20260909_hebrew_nikud
--   applied  20260910_chat_quota
--   applied  20260910_game_bank_batch / lockdown / one_call / performance
--   applied  20260910_rls_findings
--   applied  20260910_user_locations
--   applied  20260914_ai_calls
--   applied  20260914_media_jobs
--   applied  20260914_media_jobs_priority
--   applied  20260914_ops_metrics
--   applied  20260917_hide_lesson_answer_key
--   applied  20260917_revoke_browser_table_access
--   applied  20260917_restore_app_admins_grant
--   applied  20260917_fix_media_cost_view
--
--   PENDING  20260917_coach_sessions_own_children   <-- the one below
--
-- How to run: paste the block between the markers into the Supabase SQL editor.
-- There is no psql, no Supabase CLI and no database password on the application
-- server, so migrations are run by hand and verified from the server afterwards.
--
-- Everything here is idempotent. Running it twice changes nothing.
-- ============================================================================


-- ---------------------------------------------------------------------------
-- 1 of 1 · learning_coach_sessions is readable by every signed-in account
--
-- WHY THIS MATTERS
-- Signing in as a brand new account with no data of its own and reading every
-- table the browser still touches: twenty-two came back empty, correctly
-- isolated. This one came back with other accounts' rows — five of them at the
-- last check, and it grows with every lesson dialogue.
--
-- What is exposed: kid_id, the lesson, the understanding score the teacher gave
-- at the start and at the end of the dialogue, how many rounds it took, and the
-- timestamps. That is another child's performance, lesson by lesson. Their
-- actual words are not exposed — kid_lesson_history is properly isolated.
--
-- The table has row level security enabled but no policy restricting rows,
-- which in practice means "anyone with an account". The policy below is the
-- same one kid_unit_lesson_progress has had since the 2026-09-10 audit.
--
-- WHAT KEEPS WORKING
-- he/workspace and he/games/workspace read this table and both already filter
-- by kid_id, so the policy should be invisible to them. The tutor backend
-- writes it under the service role, which policies do not restrict, so there is
-- deliberately no write policy.
--
-- Undo: supabase/migrations/20260917_coach_sessions_own_children_rollback.sql
--       (it reopens the hole — read the warning at the top of that file)
-- ---------------------------------------------------------------------------

-- 2026-09-17, after the first attempt: the policy above was created and changed
-- nothing. pg_policies showed why —
--
--   debug_select_learning_coach_sessions | PERMISSIVE | {authenticated} | SELECT | true
--   lcs_select_own                       | PERMISSIVE | {authenticated} | SELECT | kid_id in (...)
--
-- A policy left behind from debugging says "any signed-in account, all rows", and
-- **Postgres combines PERMISSIVE policies with OR**, so one open policy makes every
-- restrictive one beside it pointless. Adding a correct policy was never going to
-- help; the open one has to go.
--
-- The lesson for the next time: after writing a policy, always list what is already
-- on the table. The sweep at the bottom of this file does that for the whole schema.

-- >>> PASTE FROM HERE >>>

alter table public.learning_coach_sessions enable row level security;

-- the one that was letting everything through
drop policy if exists debug_select_learning_coach_sessions on public.learning_coach_sessions;

drop policy if exists lcs_select_own on public.learning_coach_sessions;
create policy lcs_select_own on public.learning_coach_sessions
    for select to authenticated
    using (kid_id in (select id from public.kids_profiles where user_id = auth.uid()));

notify pgrst, 'reload schema';

-- <<< PASTE TO HERE <<<


-- ---------------------------------------------------------------------------
-- Then run this sweep, and send back what it returns.
--
-- It lists every permissive SELECT policy in the schema whose condition is just
-- `true` — that is, every table currently readable by any signed-in account. The
-- debug policy above was invisible until it was looked for, and there is no reason
-- to believe it is the only one.
-- ---------------------------------------------------------------------------

select tablename, policyname, roles, cmd, qual
  from pg_policies
 where schemaname = 'public'
   and permissive = 'PERMISSIVE'
   and coalesce(qual, 'true') = 'true'
 order by tablename, policyname;


-- ---------------------------------------------------------------------------
-- How to check it worked
--
-- From the SQL editor you are the owner and bypass the policy, so the editor
-- cannot prove this. Ask on the server instead:
--
--     cd /opt/iakids/backend-ai-tutor-he
--     APP_ENV=prod ../backend/.venv/bin/python -c "..."   (the RLS sweep)
--
-- Expected: a fresh account reads 0 rows instead of 5. Say the word and it will
-- be checked from there.
-- ---------------------------------------------------------------------------


-- ============================================================================
-- NOT a database change, but still open and worth doing in the same sitting
--
-- 1. Render: set APP_ENV=prod on the tutor service.
--    https://iakids-ai-tutor-he.onrender.com/openapi.json is public and lists
--    37 routes and 21 schemas, every admin route among them. The code already
--    closes /docs, /redoc and /openapi.json when APP_ENV=prod; the box does
--    exactly that and answers 404. Render is missing the variable.
--
-- 2. Cloudflare: add the security headers to iakids.app.
--    The mirror at smarts-brains.online sends all six — CSP, HSTS,
--    X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
--    Permissions-Policy. iakids.app sends none, because GitHub Pages cannot set
--    headers. With the Supabase session living in localStorage, a CSP is the
--    difference between an XSS bug and an account takeover.
-- ============================================================================
