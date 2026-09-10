-- IAKIDS: one round trip per question, not two.
--
-- Until now a generated question cost the browser an upsert into the bank the moment
-- it was shown, and then a call to record the answer. game_record_answer now takes
-- the question itself (payload + answer) and files it into the bank in the same
-- statement, under the same terms the old insert policy enforced: source='generated',
-- unverified, pending — a client still cannot promote a row into the served set.
-- A question shown but never answered is simply not filed, which is fine: the bank
-- should hold questions a child actually met.
--
-- The old signature is dropped rather than overloaded: with default parameters both
-- would match a call and PostgREST would refuse it as ambiguous.
-- Idempotent: safe to paste more than once. Requires 20260910_game_bank_lockdown.sql first.

drop function if exists public.game_record_answer(uuid, text, text, boolean, int, smallint, uuid);

create or replace function public.game_record_answer(
    p_kid uuid, p_game text, p_key text, p_correct boolean,
    p_ms int default null, p_level smallint default null, p_session uuid default null,
    p_payload jsonb default null, p_answer text default null)
returns void
language plpgsql security definer set search_path = public as $$
begin
    if not exists (select 1 from public.kids_profiles k
                    where k.id = p_kid and k.user_id = auth.uid()) then
        raise exception 'not your child' using errcode = '42501';
    end if;

    -- The question, if this child's browser generated it (a bank-served one is
    -- already here). Same terms as the old insert policy: never served until the
    -- verifier has looked at it. No markup: the verifier rejects it anyway, and a
    -- row is read by every child. Payloads over 8 KB are not questions.
    if p_payload is not null
       and octet_length(p_payload::text) <= 8192
       and p_payload::text !~ '[<>]' then
        insert into public.game_questions
            (game_code, level, qkey, payload, answer, source, verified, verify_state)
        values
            (p_game, coalesce(p_level, 0), p_key, p_payload, p_answer,
             'generated', false, 'pending')
        on conflict (game_code, qkey) do nothing;
    end if;

    insert into public.kid_question_answers
        (kid_id, game_code, qkey, correct, response_ms, level, session_id)
    values
        (p_kid, p_game, p_key, coalesce(p_correct, false),
         least(coalesce(p_ms, 0), 3600000), p_level, p_session);

    update public.game_questions
       set times_asked   = times_asked + 1,
           times_correct = times_correct + (case when p_correct then 1 else 0 end),
           updated_at    = now()
     where game_code = p_game and qkey = p_key;
end;
$$;

revoke all on function public.game_record_answer(uuid, text, text, boolean, int, smallint, uuid, jsonb, text) from public, anon;
grant execute on function public.game_record_answer(uuid, text, text, boolean, int, smallint, uuid, jsonb, text) to authenticated;
