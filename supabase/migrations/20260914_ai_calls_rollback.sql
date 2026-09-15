-- ROLLBACK of 20260914_ai_calls.sql — removes everything that migration added and
-- restores ops_metrics_prune() to the 20260914_ops_metrics.sql version.
--
-- Safe to run whether or not the migration was applied (every drop is IF EXISTS).
-- It touches ONLY the objects that migration created: ai_calls, its two RPCs, its
-- three views. No application table is read or changed. The rows in ai_calls are
-- deleted with the table — export first if you want to keep them:
--   copy (select * from public.ai_calls) to stdout with csv header;
--
-- The Python side keeps working without the table: ai_costs.py prints one line a
-- minute ("ai_calls flush failed") and drops the rows; nothing else is affected.

drop view if exists public.ai_costs_per_lesson;
drop view if exists public.ai_costs_per_kid;
drop view if exists public.ai_costs_daily;
drop function if exists public.ai_calls_set_cost(text, numeric, jsonb);
drop function if exists public.ai_calls_insert(jsonb);
drop table if exists public.ai_calls;

-- ops_metrics_prune as it was before (20260914_ops_metrics.sql), without the ai_calls line
create or replace function public.ops_metrics_prune(p_days int default 30)
returns int
language plpgsql security definer set search_path = public as $$
declare n int; total int := 0;
begin
    delete from public.request_log     where ts < now() - make_interval(days => greatest(1, p_days));
    get diagnostics n = row_count; total := total + n;
    delete from public.service_metrics where ts < now() - make_interval(days => greatest(1, p_days));
    get diagnostics n = row_count; total := total + n;
    delete from public.media_jobs where status in ('done', 'failed')
       and finished_at < now() - make_interval(days => greatest(1, p_days));
    get diagnostics n = row_count; total := total + n;
    return total;
end $$;
revoke all on function public.ops_metrics_prune(int) from public, anon, authenticated;
