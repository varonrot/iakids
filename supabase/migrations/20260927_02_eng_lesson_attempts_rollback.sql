-- Rollback for 20260927_02_eng_lesson_attempts.sql (the children's answers in the English lesson engine).
-- Parents lose the read of their child's attempts; the table and its rows stay.
drop policy if exists "2027_eng_attempts_read_own_child" on public."2027_eng_lesson_attempts";
revoke select on public."2027_eng_lesson_attempts" from authenticated;

-- DATA LOSS: drop table if exists public."2027_eng_lesson_attempts";
