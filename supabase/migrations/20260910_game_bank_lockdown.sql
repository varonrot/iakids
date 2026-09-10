-- IAKIDS: close the question bank to direct reads. The only way in is the function,
-- and it hands out a few unanswered questions at a time, to a child of the caller.
--
-- What was wrong: game_questions_read let `anon` and `authenticated` SELECT the whole
-- table — 106,096 rows on 2026-09-10, each with its payload and its answer — with the
-- publishable key that every visitor's browser holds. One paginated loop copied the
-- entire bank. The game's "nobody knows what comes next" was only true for the child.
--
-- What this does:
--   * no SELECT policy at all on game_questions: clients cannot read it directly;
--   * game_next_questions becomes SECURITY DEFINER so it can still read the table,
--     and therefore checks the child belongs to auth.uid() itself, clamps the batch
--     to 25, and refuses a child who has pulled more than a play session's worth in
--     an hour — so the bank can be enumerated no faster than it can be played;
--   * writing (the SDK's upsert of new questions, the answer log) is unchanged.
--
-- This file also carries everything from 20260910_game_bank_performance.sql, so it
-- is enough to paste this one. Idempotent: safe to paste more than once.

-- ---------------------------------------------------------------- reads: closed
drop policy if exists game_questions_read on public.game_questions;
-- (RLS is already enabled; with no SELECT policy a client sees no rows.)

-- ---------------------------------------------------------------- the served set
create index if not exists game_questions_served_idx
    on public.game_questions (game_code, level, times_asked)
    where verified or source in ('seed', 'authored');

-- How many questions a child may be handed per hour before we assume it is not a
-- child playing. A fast player answers perhaps 300 in an hour; a scraper wants all
-- of them. Pulls are counted through the answer log, which is what any real play
-- writes to and a scraper would have to fake, one row per question, to keep going.
create or replace function public.game_next_questions(
    p_kid uuid, p_game text, p_level smallint, p_limit int default 20)
returns setof public.game_questions
language plpgsql stable security definer set search_path = public as $$
declare
    lim int := least(greatest(coalesce(p_limit, 20), 1), 25);
    recent int;
begin
    -- This child is the caller's. Without this, definer would let any account read
    -- questions on behalf of any child id it could guess.
    if not exists (select 1 from public.kids_profiles k
                    where k.id = p_kid and k.user_id = auth.uid()) then
        raise exception 'not your child' using errcode = '42501';
    end if;

    select count(*) into recent
      from public.kid_question_answers a
     where a.kid_id = p_kid and a.answered_at > now() - interval '1 hour';
    if recent > 900 then
        raise exception 'too many questions this hour' using errcode = '54000';
    end if;

    return query
    with window_rows as (
        select q.*
          from public.game_questions q
         where q.game_code = p_game
           and (p_level = 0 or q.level = p_level)
           and (q.verified or q.source in ('seed', 'authored'))
           and not exists (select 1 from public.kid_question_answers a
                            where a.kid_id = p_kid and a.qkey = q.qkey and a.game_code = q.game_code)
         order by q.times_asked asc
         limit greatest(lim * 8, 100)
    )
    select * from window_rows
     order by random()
     limit lim;
end;
$$;

revoke all on function public.game_next_questions(uuid, text, smallint, int) from public, anon;
grant execute on function public.game_next_questions(uuid, text, smallint, int) to authenticated;

-- ---------------------------------------------------------------- one call per answer
create or replace function public.game_record_answer(
    p_kid uuid, p_game text, p_key text, p_correct boolean,
    p_ms int default null, p_level smallint default null, p_session uuid default null)
returns void
language plpgsql security definer set search_path = public as $$
begin
    if not exists (select 1 from public.kids_profiles k
                    where k.id = p_kid and k.user_id = auth.uid()) then
        raise exception 'not your child' using errcode = '42501';
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

revoke all on function public.game_record_answer(uuid, text, text, boolean, int, smallint, uuid) from public, anon;
grant execute on function public.game_record_answer(uuid, text, text, boolean, int, smallint, uuid) to authenticated;

comment on table public.game_questions is
    'The shared question bank. Not readable by clients: served only through game_next_questions, a few unanswered rows at a time to a child of the caller. Clients may insert (source=generated, unverified) and nothing else.';
