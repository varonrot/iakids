-- English lesson progress: anonymous callers could still query 2027_eng_lesson_progress (select was never
-- revoked from anon; RLS returned 0 rows, so nothing leaked). Only signed-in parents read their own child's
-- progress, through the existing policy. Found in the 2026-09-27 review. Safe to run more than once.
revoke select on public."2027_eng_lesson_progress" from anon;
