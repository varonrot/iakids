-- ============================================================================
-- WARNING: THIS ROLLBACK REOPENS THE SECURITY HOLES CLOSED BY
-- 20260926_security_fixes.sql:
--   * ANY SIGNED-IN ACCOUNT CAN AGAIN CALL game_question_mark AND SKEW THE COUNTERS
--     OF EVERY QUESTION IN THE BANK; increment_usage_summary /
--     increment_tutor_session_tts BECOME CALLABLE FROM THE BROWSER AGAIN;
--   * A BROWSER CAN AGAIN SET ITS OWN TICKET STATUS/PRIORITY, POST AS "admin",
--     AND WRITE MESSAGES INTO TICKETS IT DOES NOT OWN (IF THE OLD POLICIES ALLOW IT);
--   * THE OWNERSHIP BELT-AND-BRACES ON GAME RESULTS AND PARENT TABLES IS GONE;
--   * games_catalog IS WRITABLE BY anon/authenticated AGAIN (IF RLS ALLOWS).
-- Run it only to get a broken flow working again, and re-apply the fix after.
-- ============================================================================
--
-- No data is touched: this drops policies, triggers, functions and constraints
-- that 20260926_security_fixes.sql added, and puts the grants back.

-- 6. games_catalog
grant insert, update, delete, truncate on public.games_catalog to anon, authenticated;

-- 5. billing / usage
drop policy if exists sec_no_client_update on public.subscriptions;
drop policy if exists sec_no_client_delete on public.subscriptions;
drop policy if exists sec_no_client_insert on public.usage_summary;
drop policy if exists sec_no_client_update on public.usage_summary;
drop policy if exists sec_no_client_delete on public.usage_summary;

-- 4. parent-owned tables
do $$
declare t text;
begin
    foreach t in array array['kids_profiles', 'kid_tasks', 'kid_custom_subjects',
                             'kid_custom_units', 'kid_custom_lessons',
                             'homework_capture_sessions', 'homework_sessions',
                             'tutor_sessions'] loop
        execute format('drop policy if exists sec_owner_insert on public.%I', t);
        execute format('drop policy if exists sec_owner_update on public.%I', t);
        execute format('drop policy if exists sec_owner_delete on public.%I', t);
    end loop;
end $$;

-- 3. game results
drop policy if exists sec_own_kid_insert on public.kid_game_sessions;
drop policy if exists sec_own_kid_update on public.kid_game_sessions;
drop policy if exists sec_own_kid_insert on public.kid_question_answers;
drop policy if exists sec_own_kid_update on public.kid_question_answers;

-- 2. support: triggers, their functions, constraints
drop trigger if exists zz_support_tickets_guard on public.support_tickets;
drop trigger if exists zz_support_messages_guard on public.support_messages;
drop function if exists public.support_tickets_guard();
drop function if exists public.support_messages_guard();
drop function if exists public.support_caller_is_trusted();

alter table public.support_tickets  drop constraint if exists support_tickets_category_chk;
alter table public.support_tickets  drop constraint if exists support_tickets_status_chk;
alter table public.support_tickets  drop constraint if exists support_tickets_priority_chk;
alter table public.support_messages drop constraint if exists support_messages_sender_type_chk;
alter table public.support_messages drop constraint if exists support_messages_message_len_chk;

-- 1. function grants, back to the Supabase defaults (public + anon + authenticated)
grant execute on function public.game_question_mark(text,text,boolean) to public, anon, authenticated;

do $$
declare f record;
begin
    for f in select p.oid::regprocedure as sig
               from pg_proc p join pg_namespace n on n.oid = p.pronamespace
              where n.nspname = 'public'
                and p.proname in ('increment_usage_summary', 'increment_tutor_session_tts',
                                  'claim_part_coin_reward', 'close_inactive_tutor_sessions',
                                  'reconcile_custom_curriculum_rows') loop
        execute format('grant execute on function %s to public, anon, authenticated', f.sig);
    end loop;
end $$;

notify pgrst, 'reload schema';
