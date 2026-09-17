-- IAKIDS: the answer key stops being readable from a browser.  2026-09-17
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
-- Order matters
-- -------------
-- A column-level REVOKE does nothing while the role still holds a table-level SELECT
-- grant, and it fails silently. So the table grant is removed first and the safe
-- columns are granted back explicitly. This is deterministic whatever the current
-- state is, and it is safe to run more than once.
--
-- service_role is untouched: the backend keeps full access and is what actually serves
-- lesson content to the child.
--
-- What still works
-- ----------------
-- Nothing in the browser reads generated_lesson_json, lesson_audio_json or
-- lesson_content_json. Checked on 2026-09-17: the workspace, the lesson sidebar and the
-- parent panel each select an explicit short list of columns, and he/lesson/index.html
-- was changed from select("*") to the columns it actually uses. A gate rule now fails
-- the build if any browser file reads those columns or selects * from this table.
--
-- What stops working
-- ------------------
-- Any browser query asking for the three JSON columns, and any new select("*") on this
-- table from a browser. That is the point.

-- 1. take away the blanket table grant from the two browser roles
revoke select on public.lesson_units_content from authenticated;
revoke select on public.lesson_units_content from anon;

-- 2. give back every column except the three that carry generated content
--    (generated_lesson_json, lesson_audio_json, lesson_content_json)
grant select (
    id,
    learning_lesson_id,
    unit_order,
    unit_name,
    lesson_order,
    lesson_name,
    intro_template_id,
    learning_objective,
    lesson_complexity,
    max_duration_seconds,
    lesson_parts_count,
    generation_status,
    generation_error,
    generation_started_at,
    generation_completed_at,
    generated_at,
    tts_generated_at,
    audio_mode,
    audio_generation_status,
    audio_generation_error,
    audio_generated_at,
    content_version,
    model_name,
    prompt_version,
    status,
    is_active,
    created_at,
    updated_at
) on public.lesson_units_content to authenticated;

-- 3. let PostgREST notice the change immediately
notify pgrst, 'reload schema';

-- Check afterwards, signed in as an ordinary account (not the service role):
--
--   select generated_lesson_json from public.lesson_units_content limit 1;
--   -- expected: ERROR: permission denied for column generated_lesson_json
--
--   select id, lesson_name, status from public.lesson_units_content limit 1;
--   -- expected: the row, exactly as before
--
-- Rollback, if it ever breaks something:
--
--   grant select on public.lesson_units_content to authenticated;
--   notify pgrst, 'reload schema';
