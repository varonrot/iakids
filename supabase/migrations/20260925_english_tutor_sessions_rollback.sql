-- ROLLBACK of 20260925_english_tutor_sessions.sql  ·  2026-09-25
--
-- The English tutor routes (backend-ai-tutor-he/english_tutor.py) answer 503
-- "English tutor is not set up" without this table, so turn them off first
-- (ENGLISH_TUTOR_ENABLED=0) and nothing else in the service notices.
--
-- Dropping the table deletes every English conversation, its allowance record and the
-- summaries parents may have seen. It is written out but left commented on purpose.
--
-- DATA LOSS: drop table if exists public.english_tutor_sessions;

-- Safe to run: removes only the index (the table keeps working, reads by child get slower).
drop index if exists public.english_tutor_sessions_kid_started_idx;
