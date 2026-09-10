-- IAKIDS: a message quota that knows who is paying, and cannot be raced past.
--
-- What it replaces (backend/main.py): `LIMIT = 20  # זמני לבדיקה`, a read of
-- messages_used followed later by a write of used + 1. Two problems, both live:
--
--   * a paying customer is cut off after twenty messages exactly like a free one —
--     the check never looks at plan, status or expires_at;
--   * read-then-write is not atomic, so two requests that arrive together both read
--     19, both write 20, and the quota is worth whatever the concurrency is.
--
-- This does the whole thing in one statement under a row lock, and returns what the
-- caller needs to answer with. The limits stay in the backend (env-configurable) and
-- are passed in, so changing a price does not need a migration.
--
-- The period is a calendar month. A quota that never resets is not a quota, it is a
-- lifetime cap — which is what the site has today.
--
-- Idempotent: safe to paste more than once.

alter table public.subscriptions
    add column if not exists messages_period_start date;

create or replace function public.chat_consume_message(
    p_user uuid, p_free_limit int, p_paid_limit int)
returns jsonb
language plpgsql security definer set search_path = public as $$
declare
    s public.subscriptions%rowtype;
    period date := date_trunc('month', now())::date;
    paid boolean;
    lim int;
    used int;
begin
    select * into s from public.subscriptions where user_id = p_user for update;
    if not found then
        -- No row yet: onboarding creates one, but a chat can arrive first.
        insert into public.subscriptions (user_id, plan, status, messages_used, messages_period_start)
        values (p_user, 'free', 'active', 0, period)
        returning * into s;
    end if;

    paid := coalesce(s.plan, 'free') <> 'free'
            and coalesce(s.status, '') = 'active'
            and s.canceled_at is null
            and (s.expires_at is null or s.expires_at > now());
    lim := greatest(coalesce(case when paid then p_paid_limit else p_free_limit end, 0), 0);

    -- A new month starts the count again.
    used := case when s.messages_period_start is distinct from period
                 then 0 else coalesce(s.messages_used, 0) end;

    if used >= lim then
        update public.subscriptions
           set messages_used = used, messages_period_start = period
         where user_id = p_user;
        return jsonb_build_object('allowed', false, 'used', used, 'limit', lim,
                                  'plan', s.plan, 'paid', paid, 'period', period);
    end if;

    update public.subscriptions
       set messages_used = used + 1, messages_period_start = period
     where user_id = p_user;

    return jsonb_build_object('allowed', true, 'used', used + 1, 'limit', lim,
                              'plan', s.plan, 'paid', paid, 'period', period);
end;
$$;

-- The backend calls this with the service role. No client has any business spending
-- someone's quota, so nobody else may execute it.
revoke all on function public.chat_consume_message(uuid, int, int) from public, anon, authenticated;

comment on function public.chat_consume_message is
    'Counts one chat message against the account''s monthly quota, atomically under a row lock, with the limit chosen by whether the subscription is actually paid and current. Returns {allowed, used, limit, plan, paid, period}.';
