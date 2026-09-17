# BUGFIXES — what each commit fixed

Rule (2026-09-16): every `commit` + `push` adds an entry here that says exactly what was fixed, how it showed up, and how it was verified. Newest first. Build numbers refer to the workspace stamp (`IAKIDS • build 0.7.N`).

## 2026-09-17

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
