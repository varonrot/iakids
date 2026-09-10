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
