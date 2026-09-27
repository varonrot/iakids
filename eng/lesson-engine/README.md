# English lesson engine — isolated foundation

The English contract is isolated from the Hebrew lesson logic. `teacher-plan.js` describes the requested AI lesson and validates supported interactions. `backend-ai-tutor-he/eng_lessons_2027.py` is the Python server contract: it composes the subject and topic guide, validates the three steps, sends only the active step to the browser, and grades answers using the server copy. It is **not wired to the live site yet** and contains no provider credentials.

`buildTeacherRequest` combines the general teaching rules, the Math guide, the Dividing fractions guide, the selected grade and language, and a low-confidence Quick Check snapshot into one OpenAI request. `validateTeacherPlan` rejects unsupported actions or malformed plans before a lesson could be displayed. A step may request `continue` rather than force a multiple-choice question.

The migration in `sql/2027_eng_lesson_engine.sql` has been applied to the Supabase project. It adds `2027_eng_lesson_plans` (shared, server-only), `2027_eng_lesson_visuals` (shared media paths), `2027_eng_lesson_progress` (per-child, parent-readable, server-written), and a private `2027-eng-lesson-media` bucket. It does not modify the existing `2027_test_prep_lessons` record used by the current opening text.

`backend-ai-tutor-he/eng_lesson_routes_2027.py` stages the authenticated start and answer routes. It checks the parent and child, requires the selected topic and quick check, loads an approved shared plan, sends only the active step, and advances progress after a server-side answer check. It is not imported by the current application yet, and there is no approved plan to serve. The next slice is OpenAI draft generation and math/content review, Gemini visual generation when the shared asset is missing, route registration, and the browser connection. Until those are complete, the live page still uses its current fixed three questions.

Run `node --test eng/lesson-engine/teacher-plan.test.js` from the repository root.
Run `python -m unittest test_eng_lessons_2027.py` from `backend-ai-tutor-he/`.
