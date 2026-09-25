-- ROLLBACK of 20260925_qbank.sql  ·  2026-09-25
--
-- Nothing in the service reads these tables yet except the question-bank tools
-- (backend-ai-tutor-he/qbank/), which fall back to local files when the tables are missing.
--
-- Dropping the tables deletes every generated, adapted and reviewed item and the review history.
-- The statements are written out but left commented on purpose.
--
-- DATA LOSS: drop table if exists public.qbank_item;
-- DATA LOSS: drop table if exists public.curriculum_topics;
-- DATA LOSS: drop table if exists public.qbank_source;

-- Safe to run: the trigger and its function (items then accept any source again - re-run the
-- migration to restore the class-A guard), and the lookup indexes.
drop trigger if exists qbank_item_source_is_open on public.qbank_item;
drop function if exists public.qbank_item_source_is_open();
drop index if exists public.qbank_item_lookup_idx;
drop index if exists public.curriculum_topics_subject_grade_idx;
