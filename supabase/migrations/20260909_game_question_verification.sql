-- IAKIDS: verification bookkeeping for the game question bank.
--
-- 20260908 added the bank and made game_next_questions serve only trusted
-- rows (verified, or seeded/authored server-side). Nothing ever set
-- `verified`, so the bank harvested questions but never served any. This adds
-- the state the verifier (backend/verify_questions.py) needs to do that job
-- once, idempotently, and to record why a row was turned down.
--
--   verify_state  pending -> ok | rejected. `verified` stays the flag that
--                 game_next_questions reads; the verifier keeps the two in
--                 step (verified = (verify_state = 'ok')).
--   verify_note   why a row was rejected, so a bad generator is debuggable.

alter table public.game_questions
    add column if not exists verify_state text not null default 'pending'
        check (verify_state in ('pending', 'ok', 'rejected')),
    add column if not exists verify_note  text,
    add column if not exists verified_at  timestamptz;

-- Rows written server-side with the service role are trusted on arrival;
-- only client-generated rows need checking.
update public.game_questions
   set verify_state = 'ok',
       verified     = true,
       verified_at  = coalesce(verified_at, now())
 where source in ('seed', 'authored')
   and verify_state = 'pending';

-- The verifier's work queue: partial index, so it stays small as the bank grows.
create index if not exists game_questions_pending_idx
    on public.game_questions (game_code, id)
    where verify_state = 'pending';

-- Close a gap in 20260908: that policy pinned `verified = false` but said
-- nothing about verify_state, so a client could have inserted a row already
-- marked 'ok' and skipped verification entirely. Pin both.
drop policy if exists game_questions_insert on public.game_questions;

create policy game_questions_insert
    on public.game_questions for insert
    to authenticated
    with check (source = 'generated'
                and verified = false
                and verify_state = 'pending');

comment on column public.game_questions.verify_state is
    'pending -> ok | rejected, set by backend/verify_questions.py. Only ok rows are ever served to a child.';
