-- ROLLBACK of 20260917_fix_media_cost_view.sql  ·  2026-09-17
--
-- Restores the original definition, in which media_cost_usd misses the worker's own
-- calls (purpose 'media') and therefore under-reports the expensive half of a lesson.
-- Only run this if something depended on the old shape.
--
-- This one has to DROP first: `create or replace view` can add a column at the end but
-- never remove one, so going back from seven columns to six is a drop and recreate.
-- Nothing else in the database reads this view; it is for reporting only.
--
-- Idempotent: safe to run more than once.

drop view if exists public.ai_costs_per_lesson;

create view public.ai_costs_per_lesson as
select unit_lesson_id, count(*) as calls,
       round(sum(cost_usd) filter (where purpose in ('tts', 'image', 'video', 'lesson')), 4) as media_cost_usd,
       round(sum(cost_usd), 4) as cost_usd, min(ts) as first_call, max(ts) as last_call
  from public.ai_calls where unit_lesson_id is not null
 group by 1 order by 4 desc nulls last;

alter view public.ai_costs_per_lesson set (security_invoker = true);
revoke all on public.ai_costs_per_lesson from anon, authenticated;

notify pgrst, 'reload schema';
