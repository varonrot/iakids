-- ROLLBACK of 20260917_fix_media_cost_view.sql  ·  2026-09-17
--
-- Restores the original definition, in which media_cost_usd misses the worker's own
-- calls (purpose 'media') and therefore under-reports the expensive half of a lesson.
-- Only run this if something depended on the old column order or on text_cost_usd not
-- existing.
--
-- Idempotent: create or replace.

create or replace view public.ai_costs_per_lesson as
select unit_lesson_id, count(*) as calls,
       round(sum(cost_usd) filter (where purpose in ('tts', 'image', 'video', 'lesson')), 4) as media_cost_usd,
       round(sum(cost_usd), 4) as cost_usd, min(ts) as first_call, max(ts) as last_call
  from public.ai_calls where unit_lesson_id is not null
 group by 1 order by 4 desc nulls last;

alter view public.ai_costs_per_lesson set (security_invoker = true);
revoke all on public.ai_costs_per_lesson from anon, authenticated;

notify pgrst, 'reload schema';
