# English lesson engine — Grade 5 fraction slice

The English contract is isolated from the Hebrew lesson logic. `backend-ai-tutor-he/eng_lessons_2027.py` composes the subject and topic guide, validates the three steps, sends only the active step to the browser, and grades answers using the server copy. `teacher-plan.js` is an earlier contract sketch and is not loaded by the site. No provider credentials are in the browser.

`buildTeacherRequest` combines the general teaching rules, the Math guide, the Dividing fractions guide, the selected grade and language, and a low-confidence Quick Check snapshot into one OpenAI request. `validateTeacherPlan` rejects unsupported actions or malformed plans before a lesson could be displayed. A step may request `continue` rather than force a multiple-choice question.

The migrations in `sql/` have been applied to Supabase. They add `2027_eng_lesson_plans` (shared, server-only), `2027_eng_lesson_visuals` (shared media paths with review status), `2027_eng_lesson_progress` (per-child progress), `2027_eng_lesson_attempts` (chosen option, correctness, hint usage), and a private `2027-eng-lesson-media` bucket. Parents can read their child's progress and attempts; only the server can write them. A reviewed first Grade 5 dividing-fractions plan is seeded. The existing `2027_test_prep_lessons` record still supplies the opening text before entering the lesson.

`eng_lesson_routes_2027.py` registers authenticated start and answer routes through the English-only `test_prep_2027.py` import. The lesson screen calls them, resumes a child's current step, and asks the server to grade choices. The first step only needs Continue. The next two use buttons. The current CSS diagrams remain visible until reviewed images exist.

`eng_lesson_admin_2027.py` provides admin-only OpenAI draft generation, draft inspection, text approval, Gemini image generation, image inspection, and image approval. Text and image approvals are separate: an unreviewed result is never shown to children. A later approved prompt version is shared with new learners; learners already in a lesson keep their current plan. Gemini generation is explicit and cached by plan and step; it is not performed on every child's visit.

The code is on `feature/eng-lessons-2027` as draft PR #3, not deployed to the live site. Generation and image endpoints still need a live integration check before merging.

Run `node --test eng/lesson-engine/teacher-plan.test.js` from the repository root.
Run `python -m unittest test_eng_lessons_2027.py test_eng_lesson_routes_2027.py` from `backend-ai-tutor-he/`.
