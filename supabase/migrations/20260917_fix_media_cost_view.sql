-- IAKIDS: ai_costs_per_lesson.media_cost_usd counted almost nothing.  2026-09-17
--
-- The column was defined as
--     sum(cost_usd) filter (where purpose in ('tts', 'image', 'video', 'lesson'))
-- but the worker, which generates every image, every voice line and every intro video,
-- tags its calls with purpose 'media'. In the last 5000 recorded calls that is 634 rows,
-- the single largest group, and none of them counted. 'tts_live' and 'intro' were missed
-- too, while 'lesson' — the text generation — was counted as media although it is text.
--
-- So the per-lesson media figure has been wrong since the view was created, in the
-- direction that matters: it under-reported the expensive half of a lesson.
--
-- media  = anything that produced a picture, a voice line or a video
-- text   = lesson, llm, lesson_chat, homework, stt
--
-- Adds text_cost_usd alongside, so the two halves add up to cost_usd and a gap is
-- visible instead of silent.
--
-- Idempotent: create or replace.

create or replace view public.ai_costs_per_lesson as
select unit_lesson_id,
       count(*) as calls,
       round(sum(cost_usd) filter (
           where purpose in ('media', 'image', 'tts', 'tts_live', 'video', 'intro')
       ), 4) as media_cost_usd,
       round(sum(cost_usd) filter (
           where purpose in ('lesson', 'llm', 'lesson_chat', 'homework', 'stt')
       ), 4) as text_cost_usd,
       round(sum(cost_usd), 4) as cost_usd,
       min(ts) as first_call,
       max(ts) as last_call
  from public.ai_calls
 where unit_lesson_id is not null
 group by 1
 order by 5 desc nulls last;

alter view public.ai_costs_per_lesson set (security_invoker = true);
revoke all on public.ai_costs_per_lesson from anon, authenticated;

notify pgrst, 'reload schema';
