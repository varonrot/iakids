-- IAKIDS: the answer key stops being readable from a browser.  2026-09-17
--
-- NOT APPLIED. Waiting for approval before anything runs against the prod project.
--
-- Why
-- ---
-- On 2026-09-17 the question objects inside lesson_units_content.generated_lesson_json
-- gained an `answer` field, so the Learning Coach stops inventing the answer it grades
-- the child against. The backend already strips that field from every response
-- (public_structured_lesson in main.py), but the table itself is readable by any
-- signed-in account:
--
--     create policy lesson_units_content_read on public.lesson_units_content
--         for select to authenticated using (true);     -- 20260910_rls_findings.sql
--
-- so a child with a session can query the table from the browser console and read the
-- answer to every question before answering. Row level security cannot help here: the
-- row must stay readable, it is the one column that must not be. Postgres column
-- privileges can, and PostgREST honours them.
--
-- Same reasoning as exam_answer_keys in the 2026-09-10 migration: an answer key that a
-- browser can read is not an answer key.
--
-- What still works
-- ----------------
-- Nothing in the browser reads generated_lesson_json or lesson_audio_json. Checked on
-- 2026-09-17: the workspace, the sidebar and the parent panel each select an explicit
-- short list of columns, and he/lesson/index.html was changed from select("*") to the
-- seven columns it actually uses. The lesson content reaches the child through the
-- backend, which runs under the service role and is unaffected by column grants.
--
-- What stops working
-- ------------------
-- Any browser query that asks for these two columns, and any new select("*") on this
-- table from a browser. That is the point.
--
-- Idempotent: safe to run more than once.

-- The service role bypasses grants; these two are the browser's roles.
revoke select (generated_lesson_json) on public.lesson_units_content from authenticated;
revoke select (generated_lesson_json) on public.lesson_units_content from anon;

revoke select (lesson_audio_json) on public.lesson_units_content from authenticated;
revoke select (lesson_audio_json) on public.lesson_units_content from anon;

-- Everything else on the table stays readable exactly as before.
grant select (
    id, learning_lesson_id, unit_order, unit_name, lesson_order, lesson_name,
    intro_template_id, learning_objective, lesson_complexity, max_duration_seconds,
    lesson_parts_count, generation_status, content_version, generation_error,
    generated_at, tts_generated_at, audio_generation_status, audio_generation_error,
    audio_generated_at, status, created_at, updated_at
) on public.lesson_units_content to authenticated;

-- Check afterwards, signed in as an ordinary account:
--
--   select generated_lesson_json from public.lesson_units_content limit 1;
--   -- expected: permission denied for column generated_lesson_json
--
--   select id, lesson_name from public.lesson_units_content limit 1;
--   -- expected: the row, as before
