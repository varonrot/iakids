# English lesson engine — first slice

This is the first, server-side contract for one micro-lesson in IA KIDS ENG. It is deliberately isolated under `eng/`; no Hebrew lesson file or API route is modified. It is **not wired to the live site yet** and contains no provider credentials.

`buildTeacherRequest` combines the general teaching rules, the Math guide, the Dividing fractions guide, the selected grade and language, and a low-confidence Quick Check snapshot into one OpenAI request. `validateTeacherPlan` rejects unsupported actions or malformed plans before a lesson could be displayed. A step may request `continue` rather than force a multiple-choice question.

The server should keep answer keys private. A subsequent endpoint will store an approved plan in new `2027` English lesson tables, send a visual brief to the Gemini image director, store the generated asset in a dedicated English bucket, and send the browser a public projection without `answer_index`. Each child's answers and progress will live separately from the reusable plan. Until those pieces are implemented, this module is a tested contract, not a live AI lesson.

Run `node --test eng/lesson-engine/teacher-plan.test.js` from the repository root.
