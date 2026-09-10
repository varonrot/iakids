-- IAKIDS: make the question bank cheap at scale.
--
-- Two things, both measured on the live table (106k rows, 2026-09-10):
--
--   1. game_next_questions ended in `order by times_asked, random()`. random() in an
--      ORDER BY cannot use an index, so Postgres read and sorted every matching row
--      to hand back twenty — 1,237 rows for true-false-math level 1, and growing with
--      the bank. It now takes the least-asked window through an index that covers
--      exactly the served set, and shuffles only inside that window.
--
--   2. Every answer cost three round trips from the browser: an insert into
--      kid_question_answers, an rpc to bump the question's counters, and (at question
--      time) an upsert into the bank. game_record_answer does the first two in one
--      call, and checks that the child belongs to the caller before writing anything,
--      which is what lets it run as security definer.
--
-- Idempotent: safe to paste more than once. Paste in the SQL editor.

-- ---------------------------------------------------------------- 1. the served set
-- The function only ever serves verified / seeded / authored rows, so index just those,
-- ordered the way the function wants them. A partial index is small and stays hot.
create index if not exists game_questions_served_idx
    on public.game_questions (game_code, level, times_asked)
    where verified or source in ('seed', 'authored');

create or replace function public.game_next_questions(
    p_kid uuid, p_game text, p_level smallint, p_limit int default 20)
returns setof public.game_questions
language sql stable security invoker set search_path = public as $$
    -- Step 1 walks the partial index in times_asked order and stops early: the
    -- least-asked unanswered rows, a few times more than requested.
    -- Step 2 shuffles only that window, so the child does not always get the same
    -- twenty. Nothing sorts the whole bank any more.
    with window_rows as (
        select q.*
          from public.game_questions q
         where q.game_code = p_game
           and (p_level = 0 or q.level = p_level)
           and (q.verified or q.source in ('seed', 'authored'))
           and not exists (select 1 from public.kid_question_answers a
                            where a.kid_id = p_kid and a.qkey = q.qkey and a.game_code = q.game_code)
         order by q.times_asked asc
         limit greatest(p_limit * 8, 100)
    )
    select * from window_rows
     order by random()
     limit p_limit;
$$;

grant execute on function public.game_next_questions(uuid, text, smallint, int) to authenticated;

-- ---------------------------------------------------------------- 2. one call per answer
-- Replaces: insert into kid_question_answers + rpc game_question_mark.
-- security definer so it can bump game_questions (clients have no update policy
-- there), and therefore it verifies the child itself instead of relying on RLS.
create or replace function public.game_record_answer(
    p_kid uuid, p_game text, p_key text, p_correct boolean,
    p_ms int default null, p_level smallint default null, p_session uuid default null)
returns void
language plpgsql security definer set search_path = public as $$
begin
    -- The one check RLS would have made on the insert: this child is the caller's.
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

grant execute on function public.game_record_answer(uuid, text, text, boolean, int, smallint, uuid) to authenticated;

comment on function public.game_record_answer is
    'One round trip per answer: records it and bumps the question counters. Verifies the child belongs to auth.uid() itself, since it runs as definer.';
