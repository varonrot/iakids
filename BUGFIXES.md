# BUGFIXES — what each commit fixed

Rule (2026-09-16): every `commit` + `push` adds an entry here that says exactly what was fixed, how it showed up, and how it was verified. Newest first. Build numbers refer to the workspace stamp (`IAKIDS • build 0.7.N`).

## 2026-09-17

### 2026-09-17 — stage 1 of moving the UI off the database: the kid profile API
- **Four routes** cover everything the browser did with `kids_profiles`: list my kids, read one, update one partially, create one. About thirty direct call sites across the site collapse into these five operations.
- **Authorisation is server-side only.** A kid id in the request proves nothing: every route resolves the owner from the token and filters on `user_id`. Verified against production with two real test accounts — a parent reading or updating another parent's child gets 404 and the child is unchanged, no token gets 401, an invalid gender or an empty update gets 400, and the response carries only the fields a screen draws, never `user_id`.
- **`assets/js/iakids-api.js`** is the single door: it resolves the API base, takes the token from the existing auth session, and exposes `listKids`, `getKid`, `updateKid`, `createKid` and `activeKid`.
- **Found and fixed on the way**: `get_child_by_id` used `.single()`, which *raises* when nothing matches, so a parent asking for a child that is not theirs got a 500 after the retry wrapper had tried three times, instead of a plain 404.
- **Learned the hard way**: the site container mounts `/opt/iakids` straight as the web root, so every frontend file edit is live the moment it is saved, with no commit and no deploy. A converted page was live for a few minutes while its backend routes were not yet deployed, and was restored immediately. Frontend and backend of the same change now ship together, backend first.

### 2026-09-17 — the tasks page showed a default avatar for every child
- **Symptom**: the child's picture never appeared on `/he/tasks/`.
- **Cause**: the page asked for `avatar_key + ".webp"` (`dog.webp`) while the files are named `dog_blue.png`. Every request answered 404 and an `onerror` handler quietly swapped in the generic default, so nothing ever looked broken and no child ever saw the avatar they chose. Same class as the missing dog avatar fixed earlier today, in a page that had not been touched then.
- **Fix**: the page uses the shared naming convention and the known-avatar list, so an unknown key falls back to a real image instead of a broken one.
- **Also**: `/he/tasks/` is now the first screen that no longer queries the database at all. Its task list is empty because `kid_tasks` holds no rows for any child, not because of the change.

### 2026-09-17 — decision: the UI talks to the backend, never to the database
- **Question asked**: can the code be hidden so a user of the system cannot see it. **Answer: no.** The browser must receive and run it. Minifying or obfuscating buys an attacker hours, not safety, and here it would cost a build step the project deliberately avoids, break the log switch and blind the gates that read those files.
- **What can be hidden is the data layer.** As long as a page calls `sb.from("kids_profiles")`, the table name, the column list and the relationships sit in the request URL and the JSON response, visible in the network tab whatever the JavaScript looks like. The only way to hide them is to stop the browser talking to the database — which is the decision that was taken.
- **Measured**: 178 direct database calls in 53 browser files. `kids_profiles` appears in about 30 of them, most through one shared helper in `games/game-sdk.js`. Full inventory, per-table counts and the staged order are in `MIGRATION_TO_BACKEND.md`.
- **Gate**: the number of direct database calls in browser files may only go down. A new `.from(...)` call in any page fails the build and says to add an endpoint. Verified by adding one on purpose.
- **Checked while mapping**: no real secret is in any page. The Firebase and Supabase publishable keys are public by design and documented as such in `games/game-sdk.js`. The gate now also fails on a secret-looking key or any mention of `service_role` in a page.

### 2026-09-17 — the admin email list was published in two pages
- **Symptom**: `he/admin/lessons-review/` and `he/iakids-admin-dashboard-he/` each carried the admin email addresses in plain source, five in one and two in the other.
- **What it protected**: nothing. Every admin route already checks `ADMIN_EMAILS` server-side and answers 403, which was verified when those routes were built. What the list did do was hand anyone the accounts worth phishing.
- **Fix**: a new `GET /api/admin/whoami` answers 200 for an admin and 403 for anyone else. Both pages ask it instead of holding a list. A gate rule fails the build if an allowlist ever comes back.

### 2026-09-17 — browser grants revoked on every table the browser never touches
- **Applied and verified** with a real signed-in session: all 27 revoked tables answer `permission denied`, all 23 tables live pages use still work, the backend (service_role) still reads everything, and the services are clean.
- **One table had to come back out of the list: `app_admins`.** Revoking it broke reading `support_tickets`, and the error named a table nobody asked for: `permission denied for table app_admins`. A row level policy on support_tickets asks whether the user is in app_admins, and a policy runs with the caller's own rights, so the moment the caller cannot read that table the whole policy fails — for an ordinary user looking at their own tickets. `app_admins` is empty and holds only admin user ids. The proper fix is a `SECURITY DEFINER is_app_admin()` helper and a policy that calls it; until then the table stays granted, and the migration says why.
- **Why**: Supabase grants `anon` and `authenticated` every privilege on every table in `public` by default, and row level security is the only thing in front of them. That is one policy mistake away from an open table, and it already happened: the 2026-09-10 audit found anonymous reads of exam answer keys, exam questions and the whole lesson catalogue, plus an anonymous INSERT into subscriptions that only a NOT NULL constraint stopped.
- **Method**: every `.html` and `.js` file the site serves was scanned for `.from("table")`, excluding backup copies. 28 tables are never read or written from a browser; 23 are. Only the 28 are revoked, so nothing that works today stops working.
- **Functions were checked one by one**, because a `SECURITY INVOKER` function needs the caller's own rights: `record_user_location`, `game_record_answer`, `game_record_answers` and `game_question_mark` are `SECURITY DEFINER`; `game_next_questions` is invoker but reads only `game_questions` and `kid_question_answers`, both of which stay granted.
- **Still open by design**: the 23 tables live pages read directly. Closing those means moving their reads behind the backend first, which is a separate job.
- **Found on the way**: `games/game-sdk.js` calls two tables that do not exist in the database at all, `game_achievements` and `game_wins`, so those calls have always failed.

### 2026-09-17 — every migration now has a rollback file
- **Rule**: `<name>.sql` must ship with `<name>_rollback.sql` in the same commit; the gate fails otherwise, and a rollback with only comments counts as missing.
- **Written for all 17 migrations**, 14 of which had none. Statements that would destroy data are written out but left commented with `-- DATA LOSS:` — a `drop table` or `drop column` is never left ready to run.
- **Honest about what a rollback cannot do**: `create or replace function` cannot be undone by dropping the function, because that removes it entirely. Those files say so and name the earlier migration to re-run instead. The rollback of the 2026-09-10 security audit opens with a capitalised warning that running it reopens the holes it closed.

### build 0.7.135 — a browser query had been asking for a column that does not exist
- **Found while checking that the answer-key migration breaks nothing.** One query in the workspace asked `lesson_units_content` for `parent_lesson`, which is not a column of that table. PostgREST answers `42703 undefined column`, and the call site is `if(!r.error) unitMeta = r.data` — so the error was swallowed and the unit names were silently missing from that view. Confirmed against prod: the old query fails today, the corrected one returns rows.
- **Fix**: it now asks for `learning_lesson_id`, the column it actually needed.
- **Also verified**: every live browser query on that table selects only columns the new grant keeps, so the migration cannot break the product.

### build 0.7.134 — the answer key was on its way to the browser
- **Found while answering "how do I stop someone reading the JS and turning the logs back on"**. The honest answer is that you cannot: anything the page holds can be shown. So the question becomes what the page is allowed to hold — and today's own change had just made that worse.
- **The leak**: `question.answer` was added this morning so the Learning Coach stops inventing the answer it grades the child against. The unit-lesson route returns `structured_lesson` verbatim, so the answer to every question was about to travel to the browser, where any child with the network tab open could read it before answering.
- **Fixed in the response**: `public_structured_lesson()` strips `answer` from every question on the way out, at both return paths (fresh and cached). The coach reads the answer from the database, never from the client, so nothing else changes. The original object is not mutated.
- **Still open, needs approval**: `lesson_units_content` is readable by **any signed-in account** (`for select to authenticated using (true)`, from the 2026-09-10 RLS work), so a child with a session can query the table from the console and read `generated_lesson_json` directly, route or no route. Row level security cannot fix this — the row must stay readable, it is one column that must not be. `supabase/migrations/20260917_hide_lesson_answer_key.sql` revokes column-level select on `generated_lesson_json` and `lesson_audio_json` from `authenticated` and `anon`. **Not applied.** Checked first that no browser code reads either column.
- **`he/lesson/index.html`** was doing `select("*")` on that table, which pulled the whole generated JSON into the page. It now selects the seven columns it actually uses.
- **Three gate rules**: the strip helper must exist and be used on every path that returns a structured lesson, no browser file may read `generated_lesson_json`, and no browser file may `select("*")` from `lesson_units_content`. All verified by breaking them.

### build 0.7.133 — test and production log modes
- **Ask**: a test configuration where the logs are written to the console, and a production one where they are not.
- **Why one switch and not two scripts**: the pages are static files that nginx (and GitHub Pages on iakids.app) serves as they are. The backend never generates them, so the prints cannot be stripped on the way out, and a second copy of a page would diverge within a week. A build step is against the project's structure. So `assets/js/iakids-log-mode.js` replaces the console methods once, before anything else runs.
- **Behaviour**: test prints everything; production prints nothing except `console.error`, which is never silenced, and uncaught exceptions are untouched. The switch hides noise, never failures.
- **Choosing the mode**: `window.IAKIDS_LOG_MODE` before the shim, then `?log=1` / `?log=0` in the URL (kept for the tab), then `localStorage.IAKIDS_LOG`, otherwise localhost and private ranges are test and everything else is production. On production, open with `?log=1` or run `iakidsLogMode("test")` and reload.
- **Covers**: log, debug, info, warn, table, dir, group, time, count, trace and assert, on all six pages that print — the workspace alone had 154 log calls, 70 warns and a table, all of which were reaching every child's console together with kid ids and signed media URLs.
- **Verified** in a real JS engine for six cases: production host, localhost, production with `?log=1` (and that it persists), localhost with `?log=0`, blocked storage in private mode, and switching at runtime in both directions. Loading the file twice does not re-wrap. Four gate rules, each verified by breaking it.

### build 0.7.132 — a lesson now ends with a summary, not with a video and three numbers
- **What it was**: the closing was the coach's one-sentence wrap-up of the **last question only**, then `lesson-closing.mp4` — one file, identical for every lesson and every child, twenty seconds — then a card with three numbers and a grid of eight equal lesson cards. Nothing ever told the child what they had learned. The progress rail even had a "סיכום" step with a checkered flag that rendered nothing.
- **New**: `POST /api/tutor/unit-lesson/closing` returns a personal wrap-up built from the lesson's own explanations, the child's real answers and the per-part scores: a spoken summary of about thirty seconds, three short lines (למדנו / הצלחת / נחזק) shown on the card, and one sentence for the parent. Generated once per child per lesson and cached in the history table, so re-entering a finished lesson costs nothing and needs no migration.
- **Verified on lesson 152 with ארבל's real answers**: "ארבל, היום למדנו איך לזהות שמות עצם שמציינים אנשים ובעלי חיים… הצלחת לזהות כמעט את כל השמות במשפטים… כדאי לחזק את זיהוי השמות במשפטים מורכבים יותר." Correct feminine forms throughout, grounded in what she actually wrote, no numbers and no question.
- **The video** is cut to a four-second sting and plays while the summary is fetched.
- **The lesson is finally marked as finished**: `status="completed"`, `completed_at`, `progress_percent=100`, `xp_earned` and `stars_earned` are written when the last part ends. Those are exactly the columns the child's and the parent's dashboards read, which is why every unit lesson had been showing zero.
- **One next step** instead of a grid of equals: the next lesson was already computed in the code and never shown. It is now a single primary button, with the unit grid kept below it.
- **The score on the card** came from scraping the on-screen gauge, which is refreshed by a call nobody awaits, so it could show the previous part's score. It now comes from the progress row the backend just wrote.
- **The parent** sees the teacher's sentence instead of percentages, with the numbers moved to a small second line.
- **Five gate rules** cover all of it (route, response model, cache, completion write, the fetch/render/sting in the screen, the single next button, the score source), each verified by breaking it on purpose.

### build 0.7.131 — "save" in the child-details dialog left it open (again)
- **Symptom**: editing the child's details and pressing save kept the dialog on screen. The profile was in fact saved.
- **Cause**: after the save, the function refreshes the screen. Four of those updates wrote to elements that do not exist on every screen (`heroGreeting`, `heroAvatar`, `rightbarAvatar`, `rightbarName`) with no check, so the first missing one threw and `closeSettings()` was never reached. The earlier fix in 0.7.122 had only wrapped the subject list.
- **Fix**: once the save has succeeded, the whole screen refresh runs inside `try`, every element is checked before it is written, and `closeSettings()` runs in a `finally`. A failed refresh can never hold the dialog open again. Gate rule added and verified by removing the `finally` on purpose.

### build 0.7.131 — 22 children had a broken avatar
- **Symptom**: `GET /assets/avatars/dog_blue.png 404`.
- **Cause**: the avatar URL was built straight from `avatar_key` with no check that the file exists. Of 137 children, 22 had chosen `dog` and there was no dog image; 2 have no key at all.
- **Fix**: `dog_blue.png` was generated in the same style as the other six avatars (the cat was used as the style reference) and added. A shared `iakidsAvatarUrl()` helper falls back to the cat for any unknown key, in the workspace and in the parent panel. The gate fails if an avatar URL is ever built straight from the key again.

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
