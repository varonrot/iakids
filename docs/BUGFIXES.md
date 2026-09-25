Warning: truncated output (original token count: 12204)
Total output lines: 341

Warning: truncated output (original token count: 27919)
Total output lines: 657

# BUGFIXES — what each commit fixed

Rule (2026-09-16): every `commit` + `push` adds an entry here that says exactly what was fixed, how it showed up, and how it was verified. Newest first. Build numbers refer to the workspace stamp (`IAKIDS • build 0.7.N`).


## 2026-09-25 — Constrain the English dashboard logo at every viewport (eng-dashboard-4)

- Symptom: at tablet widths, the brand mark rendered at its 1280px source size, covering dashboard content and causing horizontal overflow.
- Cause: logo dimensions were only set inside the mobile and wide desktop media queries.
- Fix: define a 38px default logo size with contained scaling; existing breakpoint-specific sizes remain in effect. Bump the dashboard stylesheet cache key.
- Verification: confirmed the base sizing rule applies across the missing 721–1100px range and narrower/wider breakpoint rules override it as intended; `git diff --check`.
- Build: eng-dashboard-4, English dashboard only.


## 2026-09-24 — Complete Recent Progress empty state (eng-dashboard-3)

- Symptom: the Recent Progress panel showed two brief placeholder rows and a large unused gap.
- Fix: replace them with a centered first-use state, a learning-book illustration, a short explanation, and a Test Prep action. No activity is implied.
- Verification: HTML structure and CTA target checked; responsive empty-state styles added; JavaScript and auth flow remain unchanged.
- Build: eng-dashboard-3, English dashboard only.


## 2026-09-24 — Restore English dashboard sections (eng-dashboard-2)

- Symptom: summary cards, Continue Learning, Recent Progress and the mobile goal disappeared after the authentication release.
- Cause: parent-auth.js explicitly hid all four sections to remove demo data.
- Fix: preserve the dashboard layout, replace fabricated scores/activity/lesson progress with honest unavailable and starter states, and route the starter CTA through the existing Test Prep sign-in flow.
- Verification: syntax and DOM checks for section visibility, removal of fabricated metrics, and Test Prep CTA destination.
- Workflow: per user instruction, CLAUDE.md now treats requested fixes as authorization to commit, push and deploy after verification, without a separate shipping confirmation.
- Build: eng-dashboard-2, English frontend only; Hebrew workspace build unchanged.


## 2026-09-24 — Hebrew reading comprehension SEO cluster

- Need: dedicated reading comprehension coverage beyond the existing test-preparation article.
- Change: eight linked pages, 24 original exercises with hints/solutions, original reading passages, generated hero, Heebo and printable worksheets. Added blog discovery cards and contextual link from Hebrew test preparation.
- SEO/analytics: unique metadata, canonical and structured data, GA4 G-DKPPTPCDW8 with reading_comprehension_he event grouping. Existing sitemap workflow picks up eight new index pages.
- Verification: HTML, internal links, IDs, metadata, JSON-LD and inline JS syntax checked. Event harness verifies view, CTA placements, link, hint, solution, practice and print paths. Live rendering and sitemap checked after deployment; Analytics report ingestion not asserted.
- Build: blog content only; workspace build unchanged. Image prompt and implementation details in docs/SEO-READING-COMPREHENSION.md.

## 2026-09-24 — English Google parent sign-in (eng-auth-1)

- Need: Start prep should open parent Google sign-in before selecting or uploading study material.
- Change: responsive parent dialog with Google only, isolated PKCE session, pending-action restoration, existing authenticated kid-list/create APIs, profile selection and first-time name/grade form. The current tutor API uses its legacy age field for grade 1–6. No browser database queries or backend/schema changes.
- UI: parent profile button, real child names rendered as text, sample Emma/statistics/activity hidden. Auth errors and cancellation do not open Test Prep; close restores focus and scrolling.
- Verification: node syntax and diff checks; DOM harness passed unauthenticated gating, OAuth configuration, existing child, cross-account selection isolation, new profile, name escaping, API error, direct-link entry, callback resume/cancellation and scroll restoration. Google provider is enabled and authorize returns 302 to accounts.google.com; kid-list without bearer returns 401. Full Google callback with a real account still requires live user verification.
- Build: English eng-auth-1; shared Hebrew/Spanish screens unchanged. Supabase browser SDK vendored at 2.57.4 from official jsDelivr package distribution.

## 2026-09-24 — Hebrew school test preparation SEO cluster

- Need: expand Hebrew SEO coverage from gifted testing to ordinary elementary school test preparation.
- Change: nine new pages and integration of the existing overview (10-page cluster), 21 original exercises with hints/explanations, planning and review tables, two generated WebP heroes, Heebo, internal links and blog discovery cards. Existing overview canonical preserved; one stale learning-gap link repaired.
- SEO/measurement: unique metadata and structured data; GA4 G-DKPPTPCDW8 and cluster interaction events. Existing sitemap workflow discovers the new index pages.
- Verification: parsed all 11 changed HTML files and structured data, checked inline JavaScript syntax, IDs, canonical URLs and images. Event harness passed view, all three CTA placements, cluster link, practice start, hint, solution and print. Live delivery and sitemap checked after deployment; GA reporting ingestion is not asserted.
- Build: content-only blog addition; workspace build unchanged. Details and image prompts: docs/SEO-TEST-PREPARATION.md.

## 2026-09-24 — English Test Prep mobile layout (prep-mobile-20260924)

- Symptom: the mobile banner shrank into a corner, cards felt compact, and Cancel sat beside the footer note with excess empty space below.
- Cause: the mobile image used contain/auto height and the desktop footer stayed horizontal.
- Fix: use a full-height cover image with a left readability gradient, larger stacked cards, a flexible full-screen content area, centered footer note, and a full-width Cancel button. Narrow-phone and safe-area spacing remain responsive. Only English modal CSS and its cache version changed.
- Verification: CSS parser passed, both English entry points reference the new stylesheet version; desktop declarations preserved. Phone visual verification remains required; no mobile viewport control is exposed in the connected browser.
- Build: English CSS cache version prep-mobile-20260924; Hebrew workspace unchanged.

## 2026-09-24

### 2026-09-24 — English Test Prep entry popup
- **Symptom**: Start prep, its arrow, and navigation/mobile Test Prep links led to a missing page.
- **Cause**: the English Test Prep entry flow had not been implemented.
- **Fix**: shared native dialog with a dedicated optimized photographic banner, three accessible action cards, responsive full-screen mobile layout, Escape/backdrop/Cancel dismissal, focus return and background scroll lock. Connected dashboard and Homework header; added a direct-route fallback. File selection supports local image preview and 20 MB/type validation; topic text is retained only for the current page. AI analysis, suggested topics and plan generation remain explicitly unavailable; no uploads or invented results.
- **Verification**: JavaScript syntax check; checked scoped styles, imports, safe text rendering and object-URL cleanup. Live browser smoke check follows deployment.
- **Build**: English prep-modal-20260924; no Hebrew/Spanish changes.

### 2026-09-24 — Complete Hebrew gifted-tests content cluster
- **Need**: one sample post lacked a complete linked topic cluster.
- **Change**: add 11 pages (hub plus 10 supporting articles), integrate the existing grade-2 article, add the cluster to the Hebrew blog, add two optimised hero assets, and GA4 interaction events on all 12 cluster pages.
- **Verification**: original questions/solutions reviewed; all page titles, H1s, IDs, JSON-LD, local images, cluster links, anchors, single GA config and JS syntax checked; analytics event handlers exercised locally. Live verification follows publication.
- **Build**: SEO gifted-cluster-20260924; Hebrew workspace build unchanged (content addition only).

### 2026-09-24 — Tablet lower panels left an empty column
- **Symptom**: at 1180px, Continue Learning and My Subjects used only two-thirds of the row, with cramped text and a blank third column.
- **Cause**: desktop three-column override combined with the <=1280 full-row Recent Progress placement.
- **Fix**: explicitly use two flexible columns at 1101–1280px; keep Recent Progress across the full next row with a two-column activity list and natural height.
- **Verification**: checked the conflicting media rules and final override; cache key updated on both English pages.
- **Build**: English tablet-panels-20260924; Hebrew workspace unchanged.

### 2026-09-24 — checks: a real teacher and real photos instead of icons; a "working" sign while questions load (build 0.7.146)
- **User request**: a realistic teacher, not an icon ("המורה מכינה שאלות על שברים…" showed 👩‍🏫), and free photos wherever the checks used icons. Before that: "nothing happens, no sign anything is running".
- **Teacher**: every check screen shows our own lesson teacher (`assets/diagnostics/teacher.webp`, a round crop of `assets/lesson/lesson-teacher.webp`, 11 KB) through `C.teacher()`. The child meets the same teacher as in the lessons.
- **Waiting**: `C.busy()` shows the teacher, what she is doing ("זה לוקח כחצי דקה" for exam prep) and moving dots. It is used in comprehension, dictation, exam prep and gifted while the server prepares questions, and respects reduced motion.
- **Photos**: the six hub cards and the end screen use Pexels photos (Pexels License: free for commercial use, no attribution needed): 640×400 WebP, 12–26 KB each. The source, photographer and license for each are in `assets/diagnostics/CREDITS.md`.
- **Kept as symbols**: 🔊 on the play buttons, ✓ on the keypad and ⚙️ inside the "machine" figure are controls or part of the question.
- **Gate**: the teacher image must exist and be the one the shell uses; no page may put an emoji in `.ck-teacher`; every `/assets/diagnostics/…` image a page shows must exist. Negative-tested: an emoji teacher fails, and the missing photos failed before they were copied in.
- **Verified**: headless Chromium, with the hub photos and the exam-prep loading screen (teacher plus dots) screenshotted and checked. There were zero console errors, and `prompt_gate --all` passes.

### 2026-09-24 — Small-laptop dashboard card stretching
- **Symptom**: at 1280px, feature artwork became very tall and summary labels wrapped excessively.
- **Cause**: equal fractional page grid rows inherited the height of a multi-row lower dashboard; feature media flex-grow consumed the excess. Summary icons and bars left too little text space.
- **Fix**: content-sized page flow at 1101–1400px, bounded 150–168px feature media, and compact summary icons without decorative bars at that breakpoint.
- **Verification**: inspected responsive cascade and measured live card layout; post-deploy browser check follows.
- **Build**: English laptop-layout-20260924; Hebrew workspace unchanged.

### 2026-09-24 — English leaf favicon
- **Symptom**: English pages did not declare the requested leaf browser-tab icon.
- **Fix**: declare the existing transparent IA KIDS leaf PNG as the favicon on the dashboard and Homework Help, with relative paths compatible with /eng/.
- **Verification**: visually inspected the existing brand asset and checked both relative paths; no artwork regeneration.
- **Build**: English favicon leaf-20260924; Hebrew workspace unchanged.

### 2026-09-24 — Publish IA KIDS ENG at /eng/
- **Symptom**: the English dashboard was available only on iakids-eng.onrender.com; iakids.app/eng/ returned 404.
- **Cause**: main held only a few English images, without the English pages and styles.
- **Fix**: publish only eng/ from english-app commit 378e6b0083017f671926026bd57a8e8a86abf842. Preserve all other application directories and deployment configuration. Relative asset and Homework Help links support /eng/.
- **Verification**: checked source paths and exact English subtree; production HTTP checks follow deployment. Remaining menu destinations are existing unfinished screens, not part of this migration.
- **Build**: English release 378e6b0; Hebrew workspace build unchanged (English-only publication).

### 2026-09-24 — every check said "צריך להיכנס מתוך סביבת הלמידה" inside the workspace (build 0.7.145)
- **Symptom** (user report): opening any check from "בדיקות ומעקב" in the workspace showed "צריך להיכנס מתוך סביבת הלמידה" instead of starting. The hub's tracking strip also stayed empty.
- **Cause**: the check pages run in a frame and looked for `parent.CURRENT_KID` and `parent.sb`. In the workspace, both are declared as top-level `let` and `const`, which never become `window` properties, so the frame saw no child and no session.
  - A second bug sat behind the first: the profile stores the grade as a number (1–6), while the checks expect a letter, so every child would have started at grade ב.
- **Fix**:
  - The workspace exposes `window.IAKIDS_CHECK_BRIDGE` with `kid()` and `session()`, next to the diagnostics view.
  - `check-shell.js` reads the child and the token through the bridge first, and maps grade 1–6 to א–ו with `gradeLetter()`.
- **Same build, second report** (user: "picked grade ב, the comprehension check doesn't advance"; "exam prep, fractions: nothing happens, no sign anything is running"): nginx caches JS for 4 hours, and the check pages loaded `check-shell.js` without a version. Browsers kept the 0.7.143 shell, which has no `api()` or `signedOut()`, so the start button threw an error and nothing happened. Every check page now loads `check-shell.js?v=07N` and `.css?v=07N` with the build number.
- **Gate**: the workspace must keep the bridge, and a node test checks that the shell finds the child through the bridge and turns grade 3 into ג. Every page that loads the shell must carry `?v=` of the current build. All three were negative-tested.
- **Verified**: headless Chromium with a parent page that declares `let CURRENT_KID` and `const sb`, the way the workspace does:
  - without the bridge, the old "sign in" screen and grade ב;
  - with the bridge, the child is found, grade ה is selected and the question set is requested.

### 2026-09-24 — "בדיקות ומעקב" complete: math, comprehension, dictation, exam practice, gifted familiarisation (build 0.7.144)
- **Why**: the user asked for every check and practice in the hub to be ready, including the gifted familiarisation. All six hub cards are now active.
- **Mental math** (`he/diagnostics/math/`), grades א–ו, adaptive, no bank needed (generators). Built from Israeli sources:
  - the strands use the Ministry's terms, with a percent level for ה–ו (50%, 25%, 10%);
  - missing-number formats appear from grade א, as in the Yesodot check;
  - numbers are read aloud only in א–ב, per the ראמ"ה rule;
  - the report adds "what the school expects now", "when the school checks" and a speed state on basic facts ("נכון, עדיין מחשב"). The speed thresholds (4 s in ב–ג, 3 s from ד; none in א) are labelled research-based, not an official norm.
- **Comprehension** (`comprehension/`): listening in א–ב, reading in ג–ו, 12 original texts (2 forms per grade), 6 questions each across the Ministry's four dimensions. The report is organised by dimension, with a tip for each.
- **Dictation** (`dictation/`): letter tiles in א–ב, typing in ג–ו, 12 forms and 136 words, each word said inside a sentence. The server scores and accepts listed alternative spellings. The report is by spelling feature.
- **Exam practice** (`exam/`, `POST /api/tutor/exam-practice/start|answer`): 8 multiple-choice questions for the child's grade from the subject module; answers stay on the server for 3 hours; the child gets feedback after each answer; nothing reaches a report. New prompt: `prompts/homework/iakids_exam_practice_prompt.txt`.
- **Gifted familiarisation** (`gifted/`): 60 original items in 5 types: word pairs, missing words, word problems, numbers in shapes (pyramid, circles, machine, arrows, tree) and next shape (series and 3×3). The figures are drawn as SVG. Each section opens with a worked example; the child sees the explanation after each answer; there is no score; the next session picks unseen items.
- **Fluency**: forms A, B and C per grade, rotating, so a re-check does not repeat the same text.
- **Server banks** (`backend-ai-tutor-he/data/checks/`): `GET /api/tutor/checks/{bank}/set` sends items without answers or explanations; `POST /api/tutor/checks/score` scores without writing to the DB. Ownership of the kid is checked, and request sizes are limited, now including dict fields.
- **Leaks found and closed while testing**:
  - Grade א comprehension asked "which title fits?" while the story's title was on screen. The server now drops the title when a question asks for it.
  - The gifted figures carried their rule and formula, which is the answer, in the payload. The server strips them.
- **Content checks**:
  - A separate agent solved every gifted and comprehension item without the key. The results were 36/36 and 72/72 matching, and no item was ambiguous.
  - Three "moral" questions had wrong options that were too easy to rule out; they were rewritten.
  - A story where a child uses the oven alone and tastes from every jar was changed: an adult turns on the oven, and "if unsure, ask".
  - Sneaking into a neighbour's home without the parents' knowledge was removed.
- **Gate**, each rule negative-tested:
  - `check_bank_checks`: every bank is valid; 4 different options; `why_wrong` covers exactly the wrong options; tiles can spell the word; comprehension dimensions are the Ministry's four; א–ב comprehension is listening.
  - Code rules for the title strip, the figure strip and the answer-free payloads.
  - The math node test parses the new missing-number and percent formats.
- **Verified**:
  - Headless Chromium walked through math (א, ה), comprehension (ב, ה), dictation (ב, ה), exam practice, the gifted page (all 60 items and 5 intros) and the hub. There were zero console errors, and the screenshots were reviewed.
  - A live exam-practice run for grade ב times tables gave 8 correct questions and no answers in the payload.
  - `prompt_gate --all` passes.
- **Still to do before families use it**: a Hebrew teacher proofreads the nikud (fluency, dictation, comprehension, gifted); 5–10 parents read a report; the privacy review before results move to the server.

### 2026-09-24 — "בדיקות ומעקב": check shell and reading fluency v2 (build 0.7.143)
- **Why**: research on assessing young children, the Ministry's own checks (the literacy profile, the grade-ב fluency check, the grade-ג fluency tool, the תשפ"ז evaluation calendar) and children's assessment products. It came back with 41 sources and recommendations.
- **Renamed** "מבחנים ואבחונים" to "בדיקות ומעקב": to Israeli parents "אבחון" means a formal learning-disability evaluation, and "מבחן" means an exam. The hub order is now a parent strip (only after a first check), then short checks, then "תרגול לקראת…" (exam prep and gifted familiarisation, never in a report), then "איך זה עובד". Every card shows grades, minutes, "עם הורה" and the microphone.
- **Shared check shell** (`he/diagnostics/check-shell.js` and `.css`):
  - a parent screen (what is checked, how long, what it is not);
  - a spoken child intro;
  - a progress path that counts items;
  - a stopping rule (3 misses in a row, or 4 of the last 5);
  - an effort-only end screen with one "בואו נתרגל";
  - a parent report: strengths first, what to strengthen, practice, a re-check date, numbers folded away, a trend only after 3 runs and a change within the day-to-day spread shown as "יציב", the not-a-diagnosis line, and delete.
  - Results stay on the device until the privacy review of storing children's results on the server.
- **Reading fluency v2** (`he/diagnostics/fluency/`), grades ב–ג, in the Ministry's format:
  - a vowelled 80-word graded list read for 45 seconds, then a one-minute passage, with the easier passage when the list is low (ג: below 26, the Ministry's risk band; ב: our own threshold of 20);
  - the parent marks misread words with a small dot, taps the last word read at the chime, and rates prosody;
  - the child sees no clock, score or right/wrong.
  - The report uses דיוק, קצב, הנגנה. The Ministry's grade-ג bands appear only as a labelled rough reference, with the Ministry's own caveat that the norms were not checked. It suggests talking to the class teacher only after two low checks at least 4 weeks apart.
- **Gate**, for these pages and any check added later: no clinical words (דיסלקציה, לקות למידה, ADHD, הפרעת קשב, אבחנה, "חשד ל"), no network calls, every check on the shell, the report keeps the not-a-diagnosis line, the hub keeps checks before practice, and the shell's stop, trend and delete logic runs under node. Each was negative-tested. The negative tests also exposed a gate crash on files outside the repo, now fixed.
- **To do before families use it**: proofread the nikud of the two 80-word lists and the passages; write alternate forms for re-checks; show the parent report to 5–10 parents so nobody reads it as a diagnosis; and a lawyer's review of Amendment 13 before results move to the server.

### 2026-09-24 — the user menu opened behind panels; uploaded files missing from הקבצים שלי (build 0.7.142)
- **User menu behind panels** (user report, homework tab, then also the learning world and other screens): the name menu in the top bar opened behind the homework panel and the center views.
  - *Cause*: the top bar was at z-index 20 inside `.app`, while the center views sit at 240–247 (dashboard, my lessons, my files, achievements, diagnostics) and the worlds at 40–100.
  - *Fix*: an `IAKIDS_TOPBAR_STACKING` block on both workspaces. The top bar is at 400 (still below the modals at 9999+), the menu at 1000, and on mobile the hamburger is at 410 so the bar does not cover it.
  - *Gate*: `topbar_stacking_checks` scans every page with the user menu and fails if any view, world, panel or sidebar declares a z-index at or above the top bar's, including views added later. It was negative-tested.
- **Uploaded files missing from הקבצים שלי** (user report).
  - *Cause*: the files were in storage (checked read-only: 3 of 3). But the page listed `homework_sessions`, whose file name and link are never filled, so it showed "none". Its fallback then listed the storage folder from the browser, which storage rules do not allow, and got nothing. The separate page `he/files/` had the same bug through `/api/kid/files`.
  - *Fix*: `/api/kid/files` now reads `homework_uploads` for this parent and child, signs each file for an hour, and takes status and question counts from the session that started right after the upload. It keeps the fields `he/files/` uses. The workspace view calls this route instead of the database, and the browser storage fallback is off. That removes two browser database and storage calls, per the architecture rule.
  - *Verified*: read-only against production, 3 files returned with working links, subject and topic; another parent's id gets 404.
  - *Gate*: cod…204 tokens truncated… to the cat for any unknown key, in the workspace and in the parent panel. The gate fails if an avatar URL is ever built straight from the key again.

### build 0.7.130 — a server restart ended a child's lesson, in Spanish
- **Symptom**: ארבל sent her answer at the exact moment of a deploy and got "⚠️ Algo salió mal. Intenta más tarde." — a Spanish sentence on a Hebrew page — and the lesson stopped.
- **Cause**: a restart takes about 16 seconds and nginx answers 502 during it. The chat treated that as a fatal error, and the error text had never been translated.
- **Fix**: 502, 503 and 504 are retried twice with a growing pause before anything is shown; the messages are Hebrew and say the server is waking up. Two gate rules pin both, and the gate now fails on any non-Hebrew error string in the workspace.

### build 0.7.130 — the 15 existing lessons got their correct answer without being regenerated
- **Why**: the coach fix only helps lessons generated from today on. Regenerating a lesson to add one field would throw away its text, images and audio.
- **`tools/backfill_lesson_answers.py`**: one cheap text call per part writes `question.answer` into a lesson that has none, and touches nothing else. Run on all 15 ready lessons (30 questions, about 70 seconds). Lesson 152 part 1 now carries "המילים המורה, ארנב, תלמידה", which is exactly what the child had answered.
- **Also**: the lesson quality report now warns when a question has no stored answer and names the tool that fixes it.

### build 0.7.129 — the teacher judged the child against an answer it had invented
- **Symptom, three lessons in a row**: ארבל answered "המורה, ארנב, תלמידה" — the complete correct answer — and the teacher scored 40 and asked her to find "the word that means an animal", which she had just said. On the next lesson she answered "ספריה זה מקום, שולחן זה חפץ, וילדים זה שם עצם" and the teacher sent her back to ילדים instead of naming the one word she actually missed, מחברת.
- **Cause**: the Learning Coach was never given the correct answer. `RUNTIME_DATA.lesson.correct_answer` was the literal sentence "Derive from the lesson explanation and lesson goal", so the model derived an answer itself and graded the child against it.
- **Fix**: the teacher now writes the answer together with the question (`UniversalLessonResponse.answer`), it is stored next to the question in the structured lesson and handed to the coach. The child never sees it and it is never spoken. Lessons cached before today fall back to the old behaviour instead of failing. The coach prompt now requires an explicit item-by-item comparison against that answer and forbids asking for more once every item has been said.

### build 0.7.129 — "after N attempts give the answer and move on" never actually happened
- **Symptom**: a child who could not answer was moved to the next lesson part still holding an open question, with no answer.
- **Cause**: the loop guard existed and worked — the round limit is 1 to 4 by score, with a hard ceiling of 5 — but the model was always told `maximum_rounds: 5`. Its "last round" therefore never arrived before the server cut the session off, so the prompt rule "on the last round explain the correct answer and stop asking" could never fire. The end-of-session decision was also taken after the teacher's text was already written, so the last message usually still ended with a question that was then shipped with `wait_for_answer: false`.
- **Fix**: `learning_coach_round_plan()` is the one source of truth. It derives the limit from the score the session already has, before the model runs, and that same number is what the model is told, what the session status uses and what the flow decision enforces. `coach_state.is_final_round` tells the model outright, and the prompt now requires it to state the full answer, explain it in a sentence, ask nothing, and close with encouragement.

### build 0.7.129 — every case we fell into is now a gate rule, and the installer runs them
- **New rule in CLAUDE.md**: a bug reported in the chat, a prompt or the lesson mechanism is not fixed until `tools/prompt_gate.py` would catch it again, in the same commit, with a negative test proving the rule fails when the code is broken.
- **New checks**: `workspace_checks` (the lesson layout must apply to every subject, the visual wait must have a budget and a give-up flag, the build stamp must match `IAKIDS_BUILD_VERSION`), `media_failure_checks` (a part whose images all failed must log FAILED, `require_api_key` must exist), `learning_coach_checks` (the stored answer, the round plan, `is_final_round`), and `learning_coach_round_tests` (the limit never reaches zero, is monotonic in the score, and the last allowed round reports itself as final).
- **Coverage widened**: the commit gate now also fires on `he/workspace/index.html` and on the gate file itself, and a change to code alone runs the code rules instead of returning early.
- **`bash tools/install_hooks.sh`** installs the hook **and runs the whole suite**, so a fresh clone is verified at install time. All six new rules were verified by breaking them on purpose.
- **Live check corrected**: the 3-provider check failed a deploy on a hero image whose only text was "CO2, H2O, O2" — stricter than the product, which allows universally readable scientific notation. It now applies the same `is_allowed_scientific_text` rule as production, and still fails on words in any language.

### build 0.7.128 — the corrupted Gemini key, found and repaired; lesson 152 has its pictures
- **Where the key broke**: `.env.prod` alone. An append to a file whose last line had no closing newline glued `OPENROUTER_API_KEY=…` onto the end of `GEMINI_API_KEY`, turning a 53-character key into 146 characters with a Hebrew letter in the middle. `.env` and `.env.dev` were never touched and are clean. The broken file is kept as `.env.prod.bak2`.
- **Repaired**: the `GEMINI_API_KEY` line was replaced from `.env`, the file now ends with a newline, and `tools/deploy_tutor.sh` restarted both services with the gate green (the new env-file check passes).
- **Lesson 152**: a `unit_lesson_visuals` job was queued for it — media only, no new text and no extra text cost. All 16 images were generated in 42 s and the visuals route no longer reports a missing file.
- **Fixed in the same pass**: the `images_ok` counter added earlier today counted every image of the lesson instead of the current part, so part 2 reported 16 of 8.

### build 0.7.127 — a lesson was generated with no pictures at all, and the screen waited for them
- **Symptom**: lesson 152 ("שמות של אנשים וחיות", Hebrew) played its text and voice but showed no image; the hero request answered 500 and the visuals poll answered "not ready" for all 16 images.
- **Cause**: not the lesson and not the pipeline. `.env.prod` was appended to without a trailing newline, so the next variable was glued onto the end of `GEMINI_API_KEY` (53 characters became 146, including a Hebrew letter). The server started normally and everything that goes through OpenRouter — text, voice — worked, while **every** image call died deep inside the SDK with `UnicodeEncodeError: 'ascii' codec can't encode character '\u05d1'`. The media job then reported `done` although zero images were produced.
- **Fix, three layers**:
  1. `require_api_key()` at startup: a key must be present, clean ASCII, and must not carry a second `VAR=` inside it. A corrupted env file now refuses to start and names the variable, instead of silently producing lessons with no pictures.
  2. `env_file_checks()` in the prompt gate, on the **deploy** path only (`--all`): the same three rules read straight from the env file, so a broken key is caught before the restart. It is deliberately not part of the commit gate — a commit must not depend on a secrets file that is not in git. The render smoke now runs with dummy keys, so it tests prompts, not secrets.
  3. A part whose images all failed logs `LESSON PART VISUAL GENERATION FAILED (no image produced)` and the DONE line carries `images_ok` / `images_planned`.

### build 0.7.127 — images no longer hold up the lesson
- **Symptom**: with the images failing, the child sat in front of a stuck screen. `waitForLessonVisual` polls up to 40 times with a 2.5–8 s backoff (~300 s), and the opening buffer waits for three images one after another, so a failure could freeze the lesson for many minutes.
- **Fix**: one wait budget of 45 s (`window.LESSON_VISUAL_WAIT_BUDGET_MS`); when it runs out the lesson gives up on images for the rest of the session (`LESSON_VISUALS_GIVE_UP`), every later wait returns immediately, the "generating" box is hidden, and the text and voice continue normally. The flag resets when a lesson opens.

### build 0.7.126 — the lesson screen worked only for מדעים; images were not shown in the middle
- **Symptom**: in a Hebrew lesson ("מהו שם עצם?", lesson 151) the lesson pictures were not displayed in the centre of the screen and the chat sat on the right, while the very same flow in a science lesson looked right. It looked like the generated lesson was broken.
- **Cause**: the lesson was fine — the backend served all 14 visuals plus the hero, all valid images. The whole lesson-screen layout (picture stage in the middle, chat column, heights, dark topbar) lives in 467 CSS rules scoped to `body.lesson-theme-science`, but `setLessonBackgroundForSubject()` added that class **only when the subject was exactly "מדעים"**. Any other subject opened the lesson with no layout at all.
- **Fix**: the class now marks "a lesson screen is open" and is added for every subject; the science-only part, the dusk background image, moved to a new class `lesson-subject-science` that is toggled by subject. Leaving the lesson removes both.
- **Verified**: every inline script passes `node --check`; the background layer stays invisible for non-science subjects (base rule is `opacity:0`), so nothing changes for lessons that already looked right.

### build 0.7.126 — restored two migration files that had been emptied
- `supabase/migrations/20260914_media_jobs.sql` and `..._priority.sql` were sitting in the working tree with 0 lines (one held a single stray `g`), i.e. a stray shell redirect had overwritten them. Restored from `HEAD` before the commit so the queue migrations are not lost.

### build 0.7.125 — the teacher's example gave away the whole answer
- **Symptom**: the question was "find the nouns in: דני שיחק עם כדור בחצר". The child answered partially and the teacher replied with an "example" that named דני, כדור and חצר with their reasons — the complete answer — and then asked "what else?".
- **Fix**: a new rule block in the two prompts that answer a child mid-question (`learning_coach_system_prompt.txt`, `iakids_structured_lesson_prompt.txt`): feedback confirms only what the child actually said; a hint says **how many** items are missing, never which; an example must use different words from the active question; and a final self-check — "if the child copied my reply, would it answer the question? then rewrite it". The gate requires both sections to stay in the files.

### build 0.7.123 — the child's name was mispronounced ("ארבל")
- **Symptom**: the voice said the name wrong; a name is the first word a child hears.
- **Fix**: `vocalize_name()` — a curated nikud table for the names in the product (אַרְבֵּל, אֵיתָן, אֲבִישַׁג, אַלּוֹנָה, רוֹתֶם …), a single small model call for a name that is not in it, and the result is stored in Storage (`tts-cache/v1/name_nikud.json`) so every process and every restart reuses it. Names in Latin letters are left alone (the voice prompt already reads them as English). The name is substituted into the spoken text before the gender nikud, in the live route and in the intro cache warm-up so both produce the same cache key. Override with `TTS_NAME_NIKUD_JSON`.
- **Verified**: "היי ארבל! ... אני כאן בשבילך. כל הכבוד, הצלחת." now speaks as "היי אַרְבֵּל! ... בִּשְׁבִילֵךְ ... הִצְלַחְתְּ" through the real route (audio sent to the user).

### build 0.7.122 — the teacher spoke to a girl in masculine (ארבל)
- **Symptom**: ארבל (gender=female in her profile) wrote to the teacher and the reply was read aloud in masculine: "אני כאן בשבילְךָ" instead of "בשבילֵךְ".
- **Cause**: not the text. "בשבילך", "שלך", "הצלחת", "ראית" are spelled **identically** for a boy and a girl and only the vowels differ, so the written answer was correct and the TTS defaulted to masculine. The prompt did carry `gender: female`.
- **Fix**: `second_person_nikud()` — a deterministic table (no model) for ~35 second-person forms (־ך suffixes and past tense) in both genders; `vocalize_for_tts(text, gender)` applies it; the live TTS route resolves the child from `kid_id` (else the tutor session) and the workspace sends `kid_id`; the TTS cache key now includes gender so a girl never gets the boy's recording.
- **Also found while fixing**: `openai_clean_chat` and `homework_coach_v2` (added on another branch) talked to the child with no gender rule at all, and `iakids_universal_unit_lesson_prompt.txt` was loaded but **never used** — the shared-lesson neutrality rule added on 2026-09-16 sat in a dead file. Both routes now start with `hebrew_child_prompt_block(child)`, the rules moved into the file that is really used (`iakids_lesson_initial_prompt.txt`), and the dead file was deleted.
- **New Hebrew correctness block** (`HEBREW_WRITING_RULES`, one source of truth) in every child-facing prompt: gender agreement on every verb/adjective/suffix, Hebrew numerals agreeing with the noun, no slash forms, no gershayim abbreviations, no emoji in spoken text, English only when it is what is taught.
- **New gates**: `child_prompt_gender_checks` (any route building a Hebrew prompt for the child without a gender rule fails), `prompt_usage_checks` (a loaded prompt whose template is never used fails — this is what caught the dead file), plus unit tests for the nikud tables and a rule that the TTS cache key must include gender.
- **Verified**: live TTS with and without `kid_id` returns different audio; gate + live 3-provider check pass.

### build 0.7.122 — "save" in the child-details screen did not close it
- **Cause**: two of my own changes. In the parent panel the new gender select was **required**, so editing a child that had no gender was blocked. In the workspace, `saveSettings` refreshed the subject list after saving and any error there skipped `closeSettings()`.
- **Fix**: on edit the gender field is optional (empty = leave what is stored); `loadSubjects` is wrapped so the modal always closes; the workspace profile modal can set gender too; the one-time "boy or girl?" prompt got an "אחר כך" dismiss so it can never trap the screen.


### housekeeping — removed backups taken for work that never touched a prompt
- `V3_BACKUP`, `V6_BACKUP`, `V10_BACKUP` deleted: their prompt files were byte-identical to `V4`, `V7` and the current tree, because the work they preceded (TTS nikud in code, the live TTS cache, dictation) changed no prompt file. Kept: V1 (first snapshot), V2, V4, V5, V7, V8, V9 — each holds a distinct pre-change prompt state. The gate still passes.

### build 0.7.121 — dictation: speak instead of typing, in every chat box
- **Ask**: wherever there is a speaker and a chat, let the child speak and have the words appear in the box.
- **How**: `assets/js/iakids-dictation.js` uses the browser's built-in Web Speech API — no model, no cost, and the text appears live while the child speaks. It auto-attaches to the workspace mic button (which was decorative until now), the games workspace, the add-subject chat and the Homework V2 composer (a mic button is injected where none exists). Lesson audio is paused before listening so the teacher's voice is not recorded; 2.5 s of silence ends the recording; permission and no-speech errors show a short Hebrew hint.
- **Fallback (off by default)**: browsers without the API (Firefox, old WebViews) hide the mic. Setting `window.IAKIDS_STT_SERVER_FALLBACK = true` records and posts to the new `POST /api/tutor/stt` (OpenAI transcription, Gemini as an alternative, `STT_PROVIDER`). Verified round-trip: our own Hebrew TTS clip came back transcribed word for word in 1.3 s.

## 2026-09-16

### build 0.7.114 — dynamic image count: no image for a segment that adds nothing new
- **Symptom**: images like visual 1, 2, 4, 5, 10 of a part showed the same idea; every segment got its own picture (one image per sentence, ~70% of lesson cost).
- **Fix**: one plan entry per segment stays (player contract segment N → entry N), but only some entries get a NEW image; the others point at the previous image (`reuse_of`) and the visuals route serves that file. The director's `reuse_previous` flag proved unreliable (0% in one run, 90% in the next), so a deterministic **image budget** decides: `ceil(segments × VISUAL_NEW_RATIO)` new images per part (default 0.5, min `VISUAL_MIN_NEW`=3), given to the segments whose prompts differ most from the previous one. Math notation (sin, cos, π, √, x²) joins the allowed in-image notation.
- **Verified**: offline on lesson 12's plan (26 entries → 15 new images incl. the 2 question images, 11 reused: 16 images with hero instead of 27, ~$0.37 saved per lesson); first regeneration with the flag alone produced 26 images (that is why the budget exists).

### build 0.7.114 — CO2 in an image was treated like a caption
- **Decision**: universally readable scientific notation (chemical formulas, plain numbers, units) is language-neutral and allowed in a shared image; words and labels in any language are not.
- **Fix**: vision check classifies `kind=formula`; `is_allowed_scientific_text()` (formula must contain a digit or be allowlisted, so "Growth Thinking" never passes); generation-time check no longer retries on such images; the three image prompts state the exception explicitly.

### build 0.7.114 — admin page did not explain why an image was flagged
- **Symptom**: the review screen showed a flagged image with a sentence like "The boy is holding a small tablet…" (the vision model's description) instead of the text it read.
- **Fix**: the vision check now returns the text verbatim plus kind and confidence; a description or low confidence is a warning, not a failure. The report stores a verdict per image; the modal explains the rule, shows the quoted text and confidence next to each image, and offers per-image actions: approve (human override) or regenerate that single image (`/api/admin/lessons/{id}/images/approve|regenerate`).

### build 0.7.114 — intro too long for a lesson that already exists
- **Symptom**: opening an existing (cached) lesson still played the full opening video and the whole intro sequence, although the intro only exists to cover generation time.
- **Fix**: the workspace probes the lesson request for 1.5 s; if it comes back from cache, the opening video is cut at 4 s (`LESSON_INTRO_MAX_MS`) and the intro is trimmed to one spoken line. New lessons are unchanged.
- **Verified**: script passes `node --check`; served at build 0.7.114 on smarts-brains.online.

### build 0.7.114 — paid quality checks off by default
- `LESSON_QUALITY_GATE` and `IMAGE_TEXT_CHECK` now default to `0` (each costs model calls per lesson). Everything stays wired; set `=1` in the service environment to turn them on. The admin page's re-check button still runs the gate on demand.

### build 0.7.114 — admin screen: lesson review (admins only)
- New page `/he/admin/lessons-review/` (Google sign-in; allowlist rotem/yossi) backed by `/api/admin/lessons/*` routes that enforce `ADMIN_EMAILS` server-side (a non-admin parent gets 403, verified). Shows every lesson with its quality-gate verdict, the flagged images with the text found, the lesson text, and actions: human approval (with note), re-check, regenerate (wipe + `content_version` bump).


### build 0.7.113 — re-entering a lesson showed only the last question
- **Symptom**: a child who reached "explanation 1 → question" and came back saw only the question in the chat; the explanation and their own answers were gone.
- **Cause**: `/api/tutor/active-lesson-state` returned only `last_assistant_message`; the workspace rendered just that.
- **Fix**: the endpoint now returns `chat_history` (every `kid_lesson_history` row of that unit lesson, teacher and child) and `resume_context` (explanation segments + question of the part the child is on); the workspace renders them, without audio, before playing the last teacher message.
- **Verified**: state endpoint for an active session returns the rows; workspace script passes `node --check`.

### build 0.7.113 — quality-gate failures no longer withhold a lesson
- **Symptom**: after the gate flagged lesson 6 (text on the hero image) the child got "השיעור בבדיקת איכות".
- **Decision**: a failed gate only flags the lesson (`generated_lesson_json.quality.ok=false`) for the admin review screen; lessons are always served. Only an explicit `generation_status="needs_review"` set by a human withholds one.

### commit 702b63c1 — Render build would fail
- `python-multipart` (required by the OpenAI clean chat route) was missing from `backend-ai-tutor-he/requirements.txt`. Found because the same import error took the box's service down for 4 minutes on 2026-09-15.

### commit e320959d — quality gates end to end (build 0.7.112)
- Lesson quality gate after every media job (text rules, visuals vs segments, audio vs segments, storage consistency, no readable text in images) with report in `generated_lesson_json.quality`; `tools/lesson_gate.py`.
- Curriculum-builder prompt placeholders (`{child_name}`, `{gender}`, …) were never filled — the model saw the literal text. Found by the new prompt gate.
- Visual director asked for "labeled diagram / captions" despite the rules → `sanitize_generation_prompt`; hero prompt rendered the lesson title as text → strict no-text block + retry.
- Prompt gate: required placeholders/sections per prompt, orphan prompts, inline-code rules, unit tests, render smoke; git pre-commit + Claude Code hooks; `deploy_tutor.sh` runs the live 3-provider check when prompts changed.
- Route decorator landed on a helper (prod down 4 min on 2026-09-15) → import smoke in the gate, restart only via `deploy_tutor.sh`.
- TTS: normalisation (emoji, arrows, ×÷=%°, fractions, gershayim), long-segment split, live TTS cache in Storage + memory (greeting/shared lines 3.7 s → 0.2 s), nikud on homographs (מִדְבָּר vs מְדַבֵּר).
- Gender: `hebrew_gender_rule` in every child-facing prompt; onboarding / parent panel / workspace collect gender (131 of 133 kids had none).
- Shared lessons stay neutral (rule in generation prompts + log check); RTL / child-safety / shared-audience rules in image prompts; `content_version` bump on regeneration and delete; style chain across parts; signed URLs 4 h.

## 2026-09-15

### build 0.7.104 — parallel director + parallel TTS; nikud
- Part-1 director ran serially before part-2 teacher (77 s → 71 s); TTS segments serial (147 s → 58 s); "מדבר" read as medaber → nikud for ambiguous words.

### build 0.7.102 — Part 1 of every lesson was the question chopped into sentences
- **Cause**: on 2026-09-01 `lesson_director_prompt.txt` lost `{lesson_text}` and the part-1 director received only the question. 14 of 15 lessons affected.
- **Fix**: `direct_lesson_part()` (explanation in prompt + user message, validation, retry, fallback); placeholder restored. Affected lessons wiped and regenerated.
