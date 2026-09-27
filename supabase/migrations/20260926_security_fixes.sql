-- IAKIDS: database side of the 2026-09-26 security fixes.
--
-- Rollback: 20260926_security_fixes_rollback.sql (REOPENS every hole closed here).
-- Verify afterwards from the server: backend/.venv/bin/python tools/verify_security_sql.py --run
--
-- Idempotent: every block is drop-if-exists / if-not-exists / revoke, so pasting it
-- twice changes nothing. Nothing here deletes or rewrites a row.
--
-- The service role (tutor backend, core backend, LemonSqueezy webhook, worker) has
-- BYPASSRLS, so none of the policies below apply to it. SECURITY DEFINER functions
-- owned by postgres (chat_consume_message, game_record_answer(s), ...) run as the
-- owner and are not affected either.
--
-- ORDER: run this only AFTER the frontend change that removes the
-- rpc('game_question_mark') call from games/game-sdk.js is live. (An old cached SDK
-- would only get a silent permission error: the call is fire-and-forget.)

-- =====================================================================
-- 1. RPC functions a browser must not call
-- =====================================================================
-- game_question_mark is SECURITY DEFINER and bumps times_asked/times_correct on ANY
-- question for ANY caller: no auth.uid() check, no child. Its only browser caller
-- (games/game-sdk.js) is gone; game_record_answer(s) do the same work with an
-- ownership check.
revoke all on function public.game_question_mark(text,text,boolean) from public, anon, authenticated;

-- Functions that exist live but are not in supabase/migrations/ (created in the
-- dashboard), so their bodies and SECURITY mode are not in the repo. None of them has
-- a browser caller (grep of every .html/.js for .rpc( and /rest/v1/rpc/, 2026-09-26).
--   * increment_usage_summary(p_user_id, ...costs...) and increment_tutor_session_tts
--     take the target user/session as an argument and are called only by
--     backend-ai-tutor-he/main.py with the service role -> closed to every client role.
--   * claim_part_coin_reward, close_inactive_tutor_sessions,
--     reconcile_custom_curriculum_rows have no caller anywhere in the repo -> closed to
--     anon/public; `authenticated` keeps its explicit grant until someone reads the
--     bodies (query at the end of this file).
-- Done by name over pg_proc so every overload is covered and a missing one is skipped.
do $$
declare f record; auth_had boolean;
begin
    for f in select p.oid, p.oid::regprocedure as sig, p.proname
               from pg_proc p join pg_namespace n on n.oid = p.pronamespace
              where n.nspname = 'public'
                and p.proname in ('increment_usage_summary', 'increment_tutor_session_tts',
                                  'claim_part_coin_reward', 'close_inactive_tutor_sessions',
                                  'reconcile_custom_curriculum_rows') loop
        auth_had := has_function_privilege('authenticated', f.oid, 'execute');
        if f.proname in ('increment_usage_summary', 'increment_tutor_session_tts') then
            execute format('revoke all on function %s from public, anon, authenticated', f.sig);
        else
            execute format('revoke all on function %s from public, anon', f.sig);
            -- if authenticated only had it through PUBLIC, keep it explicitly
            if auth_had then
                execute format('grant execute on function %s to authenticated', f.sig);
            end if;
        end if;
        -- the backends call these with the service role: never lose it via PUBLIC
        execute format('grant execute on function %s to service_role', f.sig);
    end loop;
end $$;

-- =====================================================================
-- 2. Support: tickets and messages
-- =====================================================================
-- The browser writes these directly (support/, contact/, support-dashboard/).
-- Values found live 2026-09-26 (4 tickets, 0 messages):
--   category {question:3, bug:1}  status {open:3, closed:1}  priority {medium:4}
-- The allowed sets are the ones the pages offer.
do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'support_tickets_category_chk') then
        alter table public.support_tickets add constraint support_tickets_category_chk
            check (category in ('bug', 'billing', 'question', 'feature')) not valid;
    end if;
    if not exists (select 1 from pg_constraint where conname = 'support_tickets_status_chk') then
        alter table public.support_tickets add constraint support_tickets_status_chk
            check (status in ('open', 'in_progress', 'closed')) not valid;
    end if;
    if not exists (select 1 from pg_constraint where conname = 'support_tickets_priority_chk') then
        alter table public.support_tickets add constraint support_tickets_priority_chk
            check (priority in ('low', 'medium', 'high')) not valid;
    end if;
    if not exists (select 1 from pg_constraint where conname = 'support_messages_sender_type_chk') then
        alter table public.support_messages add constraint support_messages_sender_type_chk
            check (sender_type in ('user', 'admin')) not valid;
    end if;
    if not exists (select 1 from pg_constraint where conname = 'support_messages_message_len_chk') then
        alter table public.support_messages add constraint support_messages_message_len_chk
            check (char_length(message) <= 5000) not valid;
    end if;
end $$;

-- VALIDATE only when every existing row passes; otherwise the constraint stays
-- NOT VALID (still enforced on every new write) and a NOTICE says which one.
do $$
declare c record; bad bigint;
begin
    for c in select * from (values
            ('support_tickets',  'support_tickets_category_chk',     'category not in (''bug'',''billing'',''question'',''feature'')'),
            ('support_tickets',  'support_tickets_status_chk',       'status not in (''open'',''in_progress'',''closed'')'),
            ('support_tickets',  'support_tickets_priority_chk',     'priority not in (''low'',''medium'',''high'')'),
            ('support_messages', 'support_messages_sender_type_chk', 'sender_type not in (''user'',''admin'')'),
            ('support_messages', 'support_messages_message_len_chk', 'char_length(message) > 5000')
        ) as v(tbl, con, violation) loop
        execute format('select count(*) from public.%I where %s', c.tbl, c.violation) into bad;
        if bad = 0 then
            execute format('alter table public.%I validate constraint %I', c.tbl, c.con);
        else
            raise notice '% left NOT VALID: % existing rows violate it', c.con, bad;
        end if;
    end loop;
end $$;

-- Who is trusted: any caller that is not a browser role (service_role, or a direct
-- database session such as the SQL editor, where there is no JWT), or an admin.
-- Admins are identified the way the support RLS already does it: is_admin(auth.uid())
-- over public.app_admins (RUN_NOW.sql, 2026-09-17). The function below reads
-- app_admins itself (SECURITY DEFINER), so it keeps working if app_admins is later
-- closed to the browser. NOTE: app_admins had 0 rows on 2026-09-26.
create or replace function public.support_caller_is_trusted()
returns boolean
language sql stable security definer set search_path = public as $$
    select coalesce(auth.role(), '') not in ('anon', 'authenticated')
        or exists (select 1 from public.app_admins a where a.user_id = auth.uid());
$$;
-- Only the two triggers below call it, and they run as the owner.
revoke all on function public.support_caller_is_trusted() from public, anon, authenticated;

create or replace function public.support_tickets_guard()
returns trigger
language plpgsql security definer set search_path = public as $$
begin
    if public.support_caller_is_trusted() then
        return new;
    end if;
    if tg_op = 'INSERT' then
        new.status    := 'open';
        new.priority  := 'medium';          -- the column default
        new.user_id   := auth.uid();
        new.closed_at := null;
    else
        -- A user may edit their own ticket's text, never its state or its owner.
        new.status    := old.status;
        new.priority  := old.priority;
        new.user_id   := old.user_id;
        new.closed_at := old.closed_at;
    end if;
    return new;
end $$;
revoke all on function public.support_tickets_guard() from public, anon, authenticated;

create or replace function public.support_messages_guard()
returns trigger
language plpgsql security definer set search_path = public as $$
begin
    if public.support_caller_is_trusted() then
        return new;
    end if;
    new.sender_type := 'user';
    new.sender_id   := auth.uid();
    new.is_internal := false;
    if tg_op = 'UPDATE' then
        new.ticket_id := old.ticket_id;
    end if;
    if auth.uid() is null or not exists (
            select 1 from public.support_tickets t
             where t.id = new.ticket_id and t.user_id = auth.uid()) then
        raise exception 'support message: ticket does not belong to the caller'
            using errcode = '42501';
    end if;
    return new;
end $$;
revoke all on function public.support_messages_guard() from public, anon, authenticated;

-- "zz_" so they fire after any other BEFORE trigger on these tables (alphabetical
-- order) and have the last word.
drop trigger if exists zz_support_tickets_guard on public.support_tickets;
create trigger zz_support_tickets_guard
    before insert or update on public.support_tickets
    for each row execute function public.support_tickets_guard();

drop trigger if exists zz_support_messages_guard on public.support_messages;
create trigger zz_support_messages_guard
    before insert or update on public.support_messages
    for each row execute function public.support_messages_guard();

-- =====================================================================
-- 3. Game results: only for your own child
-- =====================================================================
-- RESTRICTIVE policies are ANDed with whatever permissive policies exist, so they can
-- only narrow access. Columns checked live: both tables have kid_id (uuid, no nulls).
drop policy if exists sec_own_kid_insert on public.kid_game_sessions;
create policy sec_own_kid_insert on public.kid_game_sessions
    as restrictive for insert to anon, authenticated
    with check (kid_id in (select id from public.kids_profiles where user_id = auth.uid()));

drop policy if exists sec_own_kid_update on public.kid_game_sessions;
create policy sec_own_kid_update on public.kid_game_sessions
    as restrictive for update to anon, authenticated
    using      (kid_id in (select id from public.kids_profiles where user_id = auth.uid()))
    with check (kid_id in (select id from public.kids_profiles where user_id = auth.uid()));

drop policy if exists sec_own_kid_insert on public.kid_question_answers;
create policy sec_own_kid_insert on public.kid_question_answers
    as restrictive for insert to anon, authenticated
    with check (kid_id in (select id from public.kids_profiles where user_id = auth.uid()));

drop policy if exists sec_own_kid_update on public.kid_question_answers;
create policy sec_own_kid_update on public.kid_question_answers
    as restrictive for update to anon, authenticated
    using      (kid_id in (select id from public.kids_profiles where user_id = auth.uid()))
    with check (kid_id in (select id from public.kids_profiles where user_id = auth.uid()));

-- =====================================================================
-- 4. Parent-owned tables: belt and braces
-- =====================================================================
-- Every table below has user_id (checked live, no null rows). The ones with kid_id
-- also require the child to be the caller's own (no mismatched rows exist today).
-- Live probes already showed cross-user writes refused; these make that independent
-- of whatever permissive policies are there.
do $$
declare
    t text;
    own text;
    own_kid constant text :=
        'user_id = auth.uid() and (kid_id is null or kid_id in '
        '(select id from public.kids_profiles where user_id = auth.uid()))';
begin
    foreach t in array array['kids_profiles', 'kid_tasks', 'kid_custom_subjects',
                             'kid_custom_units', 'kid_custom_lessons',
                             'homework_capture_sessions', 'homework_sessions',
                             'tutor_sessions'] loop
        own := case when t = 'kids_profiles' then 'user_id = auth.uid()' else own_kid end;

        execute format('drop policy if exists sec_owner_insert on public.%I', t);
        execute format('create policy sec_owner_insert on public.%I as restrictive '
                       'for insert to anon, authenticated with check (%s)', t, own);

        execute format('drop policy if exists sec_owner_update on public.%I', t);
        execute format('create policy sec_owner_update on public.%I as restrictive '
                       'for update to anon, authenticated using (%s) with check (%s)', t, own, own);

        execute format('drop policy if exists sec_owner_delete on public.%I', t);
        execute format('create policy sec_owner_delete on public.%I as restrictive '
                       'for delete to anon, authenticated using (%s)', t, own);
    end loop;
end $$;

-- =====================================================================
-- 5. Billing and usage: the browser never changes them
-- =====================================================================
-- Browser writes found (grep 2026-09-26): only subscriptions.insert of the free row in
-- */onboarding/prepare-user and he/games-onboarding/prepare-user. No browser writes
-- usage_summary. Both are written by the backends with the service role, and
-- chat_consume_message (SECURITY DEFINER) bumps messages_used as the owner.
-- The free-row insert (subscriptions_insert_free) is untouched.
drop policy if exists sec_no_client_update on public.subscriptions;
create policy sec_no_client_update on public.subscriptions
    as restrictive for update to anon, authenticated using (false) with check (false);

drop policy if exists sec_no_client_delete on public.subscriptions;
create policy sec_no_client_delete on public.subscriptions
    as restrictive for delete to anon, authenticated using (false);

drop policy if exists sec_no_client_insert on public.usage_summary;
create policy sec_no_client_insert on public.usage_summary
    as restrictive for insert to anon, authenticated with check (false);

drop policy if exists sec_no_client_update on public.usage_summary;
create policy sec_no_client_update on public.usage_summary
    as restrictive for update to anon, authenticated using (false) with check (false);

drop policy if exists sec_no_client_delete on public.usage_summary;
create policy sec_no_client_delete on public.usage_summary
    as restrictive for delete to anon, authenticated using (false);

-- =====================================================================
-- 6. games_catalog: read-only to the browser
-- =====================================================================
-- The only browser use is a select in games/game-sdk.js (id, game_code, is_active).
revoke insert, update, delete, truncate on public.games_catalog from anon, authenticated;

notify pgrst, 'reload schema';

-- =====================================================================
-- After running: read the functions that are not in the repo (step 1).
-- Any row with prosecdef = true and uses_auth_uid = false that `authenticated` can
-- still execute is worth a look before revoking it from authenticated as well.
-- =====================================================================
-- select p.proname, p.oid::regprocedure as signature, p.prosecdef,
--        pg_get_functiondef(p.oid) ilike '%auth.uid()%' as uses_auth_uid,
--        has_function_privilege('anon', p.oid, 'execute')          as anon_exec,
--        has_function_privilege('authenticated', p.oid, 'execute') as auth_exec
--   from pg_proc p join pg_namespace n on n.oid = p.pronamespace
--  where n.nspname = 'public' and p.prosecdef
--  order by 1;
