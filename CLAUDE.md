# iakids — CLAUDE.md

Safe AI tutor/chat platform for kids, live at **https://iakids.app** (CNAME → GitHub Pages).
Multilingual static site: Spanish is default (root `index.html`, `lang="es"`), plus `/he` (Hebrew, RTL), `/de`, `/pt`.

## Stack

- **Frontend**: plain static HTML/CSS/JS. No framework, no build step. Large single-file pages (e.g. `he/index.html` ~250KB). Deploy = push to GitHub Pages.
- **Backends** (Python FastAPI, deployed separately — NOT served by Pages):
  - `backend/` — core chat API: Supabase + OpenAI, LemonSqueezy payment webhooks (HMAC-verified). Prompts loaded from `backend/prompts/`.
  - `backend-ai-tutor-he/` — Hebrew AI tutor: OpenAI + Google Gemini (`google-genai`, incl. TTS/wave audio), Supabase.
    Providers: `AI_PROVIDER=direct|openrouter` (chat + lesson models) and `TTS_PROVIDER=direct|openrouter` (same Gemini TTS model via OpenRouter's `/audio/speech`, needs `OPENROUTER_API_KEY`); default `direct`. Images stay on the direct Gemini client. `tools/tts_check.py` synthesizes one sentence with the configured provider.
    Models are env vars with defaults in `main.py` (missing from `.env` = default): `CHAT_MODEL` (gpt-4o-mini), `LESSON_MODEL` (gpt-5.6-sol), `HOMEWORK_COACH_MODEL`, `HOMEWORK_PLANNER_MODEL`, `CLEAN_CHAT_MODEL` (gpt-5.6-sol), `HOMEWORK_VISION_MODEL` (google/gemini-3.1-flash-lite on OpenRouter), `GEMINI_TTS_MODEL`, `OPENROUTER_TTS_MODEL`, `LESSON_IMAGE_MODEL`, `NIKUD_MODEL`, `STT_MODEL`, `IMAGE_TEXT_CHECK_MODEL`. The gate fails on a model name written into a call. The `[config]` line at startup prints the resolved ones.
    Every model call is recorded in `public.ai_calls` (provider, model, purpose, tokens, audio seconds, cost) by `ai_costs.py`, which wraps the SDK clients; routes tag calls with `ai_context(...)`, the worker per job. Views: `ai_costs_daily`, `ai_costs_per_kid`, `ai_costs_per_lesson`.
    Media generation (intro videos, visuals, TTS) runs in a separate process: `worker.py` pulls rows from `public.media_jobs` (migration `supabase/migrations/20260914_media_jobs.sql`). Routes only enqueue via `dispatch_media_job`. `MEDIA_JOBS_MODE=inline` restores the old in-process BackgroundTasks behaviour; the queue also falls back to inline if the insert fails.
- **DB**: Supabase (Postgres). Games use client-side IndexedDB (see `games/GAMES.md`).
- **Payments**: LemonSqueezy webhooks in `backend/main.py`.

## Layout

```
index.html            Spanish landing (default)
he/                   Hebrew site: landing, app/, workspace/, onboarding/, parent-panel/, perfil/, preferencias/, iakids-admin-dashboard-he/
de/  pt/              German / Portuguese landings
workspace/            main app workspace (ES)
games/                100 educational mini-games — catalog + interface spec in games/GAMES.md, shared SDK in games/game-sdk.js
admin/dashboard/      admin dashboard
he/admin/lessons-review/  admin-only lesson quality review (Google sign-in; backend enforces ADMIN_EMAILS)
he/diagnostics/       "בדיקות ומעקב" hub (opened in the workspace center, in a frame). Every check runs on check-shell.js/.css:
                      parent gate → spoken child intro → items (no clock, score or right/wrong shown to the child) →
                      effort-only end screen → parent report (strengths, what to strengthen, practice, re-check date,
                      trend only after 3 runs, the "not a diagnosis" line). fluency/ = reading fluency v2 (Ministry
                      format: 80-word vowelled list for 45 s + 1-min passage, parent marks). Results stay on the device until
                      the privacy review; the gate fails on clinical words, network calls or a check not on the shell.
                      Only check-shell.js may fetch, and only /api/tutor/checks/ and /api/tutor/exam-practice.
                      math/ (mental math, adaptive, Ministry strand names), comprehension/ (listening א–ב, reading ג–ו,
                      4 Ministry dimensions), dictation/ (tiles א–ב, typing ג–ו), exam/ (8 practice questions by subject
                      + topic, never in a report), gifted/ (familiarisation, 5 question types, SVG figures, no score).
                      Question banks live on the server: backend-ai-tutor-he/data/checks/*.json. GET
                      /api/tutor/checks/{bank}/set strips answers, explanations and a figure's rule/formula (and the
                      title when a question asks for it); POST /api/tutor/checks/score scores. `check_bank_checks` in
                      the gate validates every bank.
backend-ai-tutor-he/prompts/homework/  homework coach, pedagogy, planner prompts + subjects/ (one module per subject, per grade)
parent-dashboard/     parent dashboard
backend/              core FastAPI (chat, payments)
backend-ai-tutor-he/  Hebrew tutor FastAPI (many main_vN.py versions — main.py is current)
blog/ privacy/ terms/ coppa/ refunds/ support/ ...  content & legal pages
```

## Conventions & gotchas

- **Versioned files, not git branches**: `index2.html`, `main_v6.py`, `workspace_back_up.html` etc. The unnumbered `main.py`/`index.html` is the live one. Don't delete backups without asking. Exception decided 2026-09-15: `prompts/` folders hold ONLY the files `main.py` loads; old prompt versions live in `V<N>_BACKUP/`, never as `_v2`/`_back_up` siblings (the gate fails on an unlisted prompt).
- **Hebrew pages are RTL**: `<html dir="rtl" lang="he">`. Keep RTL when editing `/he/**`.
- **Secrets**: `backend/.env` exists locally (gitignored, 600). Never put a key in a client file — the Supabase key in the browser is the publishable one and RLS does the work.
- **Edit style**: pages are self-contained; match existing inline CSS/JS style, no new deps or build tools.
- **Games**: each game = own folder `/games/<slug>/` with `index.html` + `GAME.md` (spec + build subtasks), own IndexedDB `iakids_game_<slug>`, implements SDK contract from `games/GAMES.md`. Shared coin wallet (`IAKidsCoins`, DB `iakids_wallet`): +10 right / −5 wrong / +25 complete / streak bonus. Completion reported via `postMessage {type:'iakids-game-complete'}`. Hub (`games/index.html`) auto-detects playable games by probing `<slug>/index.html` — paste a game folder and it goes live, no code edits.
- **Before implementing a new game**: read its `games/<slug>/GAME.md` fully, then research the game before coding — how existing versions of this game type look and feel (what makes them fun/beautiful for kids), and the correct content logic (question generation, distractor quality, edge cases like Hebrew final letters, RTL, level balance). Only then build, following the GAME.md subtask checklist. Beautiful + correct beats fast: kids notice jank, parents notice wrong answers.
- **Mandatory interface for EVERY new game**: the full 11-point spec lives in **`games/INTERFACE.md`** — read it before writing code, it's the single source of truth (rounds/level picker, coins, no-repeat questions, adaptive difficulty, feedback FX, question timer, help modal, end screen with share, languages, home button — most of these are automatic once a game links `game-sdk.js`/`game-style.css`, see that doc's "Automatic — no code needed" section). Working reference: `games/demo/index.html`. Game catalog + SDK contract: `games/GAMES.md`. Tournaments and the אלוף האלופים table (`games/champions/`) need zero per-game code. After building: browser-test a full playthrough (zero console errors) and screenshot.

## Build number (mandatory on every fix)

- The user-visible build is stamped in `he/workspace/index.html` in three places: the `#iakidsBuildStamp` div (`IAKIDS • build 0.7.N`), `window.IAKIDS_BUILD_VERSION = "0.7.N"`, and the cache-buster `openai-clean-chat.js?v=07N`.
- **Every fix bumps N by exactly 1** (0.7.101 → 0.7.102 → 0.7.103 …), in the same commit as the fix. Never skip or reuse a number. Check the current value with `grep -n IAKIDS_BUILD_VERSION he/workspace/index.html` before bumping — GitHub Actions workflows in `.github/` also bump it, so pull first.

## Backups

- Back up ONLY before changing a prompt file (or when the user says "גיבוי"): `bash .claude/skills/backup/backup.sh "<note>"` (project skill `backup`). Code-only changes to main.py do not need a backup. It snapshots `backend/main.py`, `backend-ai-tutor-he/main.py` and every prompt file (root `iakids_*_prompt.txt`, `backend/prompts/`, `backend-ai-tutor-he/prompts/`) into the next `V<N>_BACKUP/` folder, verifies with `diff`, writes a README. Never overwrite an existing `V<N>_BACKUP`. Take one before touching `main.py` or a prompt.

## Dictation (speak instead of typing)

- `assets/js/iakids-dictation.js` is loaded by every page with a chat box (`he/workspace`, `he/games/workspace`, `he/add-subject`, `frontend-v2/homework.html`) and auto-attaches on load: existing `.talk-btn`, `[data-dictation-for="#input"]`, or an injected mic next to `#chatInput`. It uses the browser's Web Speech API — **no model, no cost** — and writes interim text into the input while the child speaks.
- The server route `POST /api/tutor/stt` exists for browsers without the API but is **off** unless a page sets `window.IAKIDS_STT_SERVER_FALLBACK = true` (knobs `STT_PROVIDER=openai|gemini`, `STT_MODEL`). A new chat surface only needs the script tag, or `data-dictation-for` on its own mic button.

## Rule: docs/BUGFIXES.md on every commit + push

- Every `git commit` that is pushed adds an entry to `docs/BUGFIXES.md` (newest first): symptom, cause, fix, how it was verified, build number. The user reads this file to know exactly what changed. No entry, no push.

## Rule: gate before every commit and every deploy

- **Commit**: the git pre-commit hook runs `tools/prompt_gate.py --staged` whenever a prompt file or `main.py` is staged. A failing gate blocks the commit. Install once per clone: `bash tools/install_hooks.sh`.
- **Deploy**: the only way to restart the tutor backend is `bash tools/deploy_tutor.sh` (gate → restart web+worker → health check: active, "startup complete", HTTP 200). A Claude Code PreToolUse hook on Bash also blocks any bare `systemctl restart/start iakids-tutor-*` unless the gate passes. Never restart prod while the gate fails (2026-09-15: a failed import smoke was overridden and prod was down 4 minutes).

## Log mode (test prints, production is silent)

- `assets/js/iakids-log-mode.js` replaces the console methods once, and must be the **first** script on every page that prints (`he/workspace`, `he/games/workspace`, `he/parent-panel`, `he/index`, `he/add-subject`, `frontend-v2/homework.html`). Anything loaded before it escapes the switch, so the gate checks the order, not just the presence.
- **test** prints everything, **prod** prints nothing except `console.error`, which is never silenced. Uncaught exceptions are untouched.
- Mode: `window.IAKIDS_LOG_MODE` set before the shim wins; then `?log=1` / `?log=0` in the URL (kept for the tab); then `localStorage.IAKIDS_LOG`; otherwise localhost and private ranges are test and everything else is prod.
- To debug production: open the page with `?log=1`, or run `iakidsLogMode("test")` in the console and reload.
- **Do not** create a second copy of a page for debugging and **do not** add a build step: the pages are static files served by nginx and GitHub Pages, so nothing can strip the prints on the way out, and two copies diverge. Keep writing ordinary `console.log` calls — the switch handles them.

## Lesson closing (what happens when a lesson ends)

- `POST /api/tutor/unit-lesson/closing` returns the teacher's personal wrap-up: `spoken` (read aloud, ~30 s), `learned` / `did_well` / `to_strengthen` (the three lines on the card) and `parent_note` (one sentence for the parent panel). Prompt: `prompts/iakids_lesson_closing_prompt.txt`. It is built from the lesson's own explanations, the child's real answers and the per-part scores — never from the score alone.
- **Generated once per child per lesson.** The result is stored as a `kid_lesson_history` row whose `evaluation.kind = "lesson_closing"`; `find_cached_lesson_closing()` serves it after that, so re-entering a finished lesson costs nothing. The parent panel reads the same row.
- The closing video is cut to a short sting (`window.LESSON_CLOSING_VIDEO_MAX_MS`, 4 s): it is the same file for every lesson and every child, so it must not stand between the child and the summary.
- When the last part finishes, `kid_lesson_progress` is written `status="completed"`, `completed_at`, `progress_percent=100`, `xp_earned`, `stars_earned` — the columns the child's and the parent's dashboards already read. Never leave it `in_progress`.
- The completion card shows **one** primary next-lesson button plus the unit grid, and its score comes from the progress row, not from the on-screen gauge.

## Rule: nothing ships without a word from the user (reaffirmed 2026-09-17)

- **No `git commit`, no `git push`, no `tools/deploy_tutor.sh`** until the user says so, each time. Making the change is not permission to ship it.
- Work locally, run the gate, and then **show what changed and stop**: the file list, what each change does, and what it would do to production. The user decides.
- This covers anything that reaches production or another person: a deploy, a migration run against prod ([[prod-migrations-need-approval]]), an email, a published page.
- A green gate is evidence, not consent. "It passed" is a reason to offer the change, not to ship it.
- The reason is the user's, and it is a good one: too much changed too fast today. Slow is fine.

## Performance and cost

- **`docs/PERFORMANCE.md`** holds the measured picture: where the child's time goes, where the money goes, every model in production with its latency and cost, and a benchmarked provider comparison. Every number there comes from `ai_calls`, `ai_costs_per_lesson` or the `STAGE SUMMARY` log lines. Re-measure with the queries at the bottom of that file instead of trusting the page after a change.
- **Two facts to keep in mind before optimising anything**: media is about 95% of a lesson's cost and images are 82% of it, while the Visual Director is the largest single block of the child's wait.
- **Never compare providers by running one and then the other.** Interleave the runs, same prompt, same machine, and report the sample size. "OpenRouter is slower" turned out to be true for OpenAI models here and not measurable for Gemini ones.

## Architecture rule (decided 2026-09-17): the UI talks to the backend, never to the database

- **No page, script or game opens a connection to Supabase, Firebase or any other data store.** The browser calls our own API and nothing else. All the work happens in the backend.
- **Why**: code that reaches the browser cannot be hidden. Minifying or obfuscating buys hours, not safety, and costs a build step this project deliberately avoids. What *can* be hidden is the data layer: as long as a page calls `sb.from("kids_profiles")`, the table name, the column list and the relationships are in the request URL and the JSON, visible in the network tab whatever the JS looks like. The only way to hide them is to stop the browser talking to the database.
- **Also**: RLS stops being the single line of defence, a table rename stops being a frontend change, and the answer key, the scoring rules and the quotas live where the child cannot reach them.
- **Starting point, measured 2026-09-17**: 178 direct database calls in 53 files. `kids_profiles` alone appears in about 30 of them, most through one helper in `games/game-sdk.js`. Inventory and order in `docs/MIGRATION_TO_BACKEND.md`.
- **Until a table's last browser caller is gone** it keeps its grant; the moment it is gone, revoke it (`supabase/migrations/*_revoke_*`) and the gate keeps it closed.
- **New code**: never add a `.from("...")` call in a browser file. Add an endpoint.

## Rule: chat security, for every route and every prompt (decided 2026-09-24)

- **Models get no tools.** No `tools=`, `functions=` or `tool_choice` in any model call: the model can reach no database, file or system, so a prompt injection can only leak what the prompt itself holds. Adding tools is the user's decision, never a side effect. The gate fails on it.
- **Every request body inherits `LimitedRequest`**, never a plain `BaseModel`. Strings and lists over `REQUEST_FIELD_LIMITS` are rejected before the route runs: 1,500 characters for a message or answer, 20,000 for homework source text, 300 for ids and short fields. Browser chat inputs carry `maxlength="1500"`.
- **Browser history is never trusted**: `clip_chat_history()` keeps the last 12 user/assistant turns of at most 2,000 characters each, and drops any "system" turn.
- **Every prompt that takes a child's or a parent's text carries `PROMPT_SECURITY_RULES`**, through `hebrew_child_prompt_block()`, `HEBREW_WRITING_RULES` users or explicitly. **Every reply goes through `reply_leaks_internal()` or `guard_reply_payload()`**, which replace a reply holding internal markers, table names or key-like tokens.
- The gate scans every function that sends a user's text to a model, including ones written later, and fails on a missing security block or a missing reply check. It also fails on a route body that is not a `LimitedRequest`. `tutor_tts` is the only exemption: it reads text aloud and writes no reply.
- **Red-team checks are extraction-only** and run in dev with a dummy DB key; never a write or delete attempt. 2026-09-24: 12 attacks on the homework coach (ignore rules, reveal the prompt, plan or answer, "debug mode", SQL, other children, forged history, HTML, gematria) got nothing out, and a 5,000-character message was rejected.

### Checklist: a new prompt or a new model route
1. Prompt file under `backend-ai-tutor-he/prompts/` (subfolders allowed), loaded by a literal `"prompts/…"` path in `main.py`; old versions go to `V<N>_BACKUP/`, never as siblings.
2. A `REQUIRED` entry in `tools/prompt_gate.py` that pins at least one placeholder or section. An entry that pins nothing fails.
3. Child-facing: `hebrew_child_prompt_block(child)` (gender, Hebrew correctness, security). Parent-facing: `PROMPT_SECURITY_RULES`.
4. Request body `class XRequest(LimitedRequest)`, with a limit in `REQUEST_FIELD_LIMITS` for any new long text field.
5. The reply goes through `reply_leaks_internal()` (text) or `guard_reply_payload()` (structured).
6. A gate rule for the feature's own behaviour, with a negative test.

## Rule: every migration ships with its rollback

- `supabase/migrations/<name>.sql` must have `supabase/migrations/<name>_rollback.sql` in the same commit. The gate fails otherwise, and an empty rollback counts as missing.
- A rollback that would destroy data writes the statement out but leaves it **commented** with `-- DATA LOSS:`. A `drop table` or `drop column` is never left ready to run.
- A `create or replace function` cannot be undone by dropping it — that removes the function entirely. The rollback says so and names the earlier migration to re-run instead.
- A rollback that reopens a security hole says that at the top, in capitals.
- **Prod SQL needs explicit approval every time** ([[prod-migrations-need-approval]]). This box has no `psql`, no Supabase CLI and no DB password, so migrations are run by the user in the Supabase SQL editor; verify from here afterwards.
- Browser access: `anon` and `authenticated` hold grants on everything by default, and RLS is the only gate. Tables the browser never touches have their grants revoked (`20260917_revoke_browser_table_access.sql`). Before adding a browser read of a new table, check it is granted.

## Rule: every reported bug becomes a gate rule

- **When the user reports a bug in the chat, in a prompt, or in the lesson mechanism, the fix is not done until a rule in `tools/prompt_gate.py` would catch it again.** Same commit as the fix. This is not optional and does not wait to be asked.
- Where the rule goes: a prompt rule → `REQUIRED` (placeholder or section); a rule that lives in `main.py` → `learning_coach_checks` / `media_failure_checks` / `code_rule_checks`; a rule in the lesson screen → `workspace_checks`; a pure function → `pure_function_tests`; an env/secret shape → `env_file_checks` (deploy path only).
- Every new rule gets a **negative test**: break the code in a scratch copy and confirm the gate fails. A rule that never fails is not a rule.
- The rule's message says what the child would experience, not what the code looks like ("a non-science lesson opens with no layout and no images"), plus the date and the incident.
- `bash tools/install_hooks.sh` installs the pre-commit hook **and runs the whole suite**; a fresh clone is verified at install time. The hook covers prompts, `main.py`, `he/workspace/index.html` and the gate itself.

Cases already pinned (2026-09-15 → 17): `{lesson_text}` in the director prompt; gender rule in every child-facing prompt; a loaded prompt that is never used; a hint or example that gives the answer away; the Learning Coach getting the real correct answer and a real last round; a corrupted API key (non-ASCII or a glued variable) refusing to start; a part whose images all failed logging FAILED instead of DONE; the lesson layout applying to every subject; images never blocking the lesson; the build stamp matching `IAKIDS_BUILD_VERSION`.

## Prompt gate (always runs on prompt changes)

- `tools/prompt_gate.py` checks every prompt `main.py` loads: required placeholders (e.g. `{lesson_text}` in the director prompt), required sections (gender rule, shared-lesson neutrality, immutable question), placeholders that no code fills, conflict markers, that the pre-edit version exists in a `V<N>_BACKUP`, and a render smoke (imports `main`, builds every prompt, no `{placeholder}` left). Modes: `--all`, `--staged`, `--hook`, `--pre-edit`, `--check-file X --as name`.
- Wired three ways: `.claude/settings.json` hooks (PreToolUse auto-runs the backup skill before a prompt edit; PostToolUse runs the gate and blocks with the reason), and a git pre-commit hook installed by `bash tools/install_hooks.sh` (re-run after a fresh clone; hooks are not versioned).
- Adding a prompt file or a must-keep section: extend `REQUIRED` in `tools/prompt_gate.py` in the same commit.
- Hook commands in `.claude/settings.json` MUST use absolute paths (`"${CLAUDE_PROJECT_DIR:-/opt/iakids}/tools/..."`): the session cwd moves with `cd`, and a hook that cannot find its script exits 2 and blocks every tool (happened 2026-09-15).

## Lesson quality gate (runs after every media job)

- `backend-ai-tutor-he/lesson_quality.py` + `run_lesson_quality_gate()` in `main.py`: after each `unit_lesson_media/audio/visuals` job the worker checks text rules (no gendered singular, no question in `lesson[]`, no placeholders/emoji, segment length), visual plan (one visual per segment + question, `trigger_text` present), audio (segments/question per part, files exist), storage (no files from another `content_version`) and, via one cheap Gemini vision call per image, that no image carries readable text. Report → `generated_lesson_json["quality"]`, log line `LESSON QUALITY GATE PASS|FAIL`. On demand: `tools/lesson_gate.py --lesson N` (`--all-ready`, `--no-images`).
- Generation-time guards: `ensure_no_text_in_image()` (vision check + one strict retry for every hero/visual), style chain (part N's first image follows part 1's), `content_version` bump on regeneration (route) and on delete (`delete_unit_lesson.py`), TTS text normalisation (`normalize_for_tts`: emoji, arrows, ×÷=%°, fractions, gershayim abbreviations) and long-segment splitting, rhetorical questions allowed in explanations, first name only in greetings for long full names, signed URLs 4 h.
- Knobs: `LESSON_QUALITY_GATE` and `IMAGE_TEXT_CHECK` are **OFF by default** (user decision 2026-09-16: they cost model calls; everything stays wired, set `=1` in the service env to enable). `IMAGE_TEXT_CHECK_MODEL` (gemini-3.1-flash-lite), `TTS_CACHE`, `TTS_PARALLEL`, `TTS_NIKUD`. The admin page's "בדיקה מחדש" button runs the gate on demand regardless.

## Deleting / regenerating a lesson

- On "מחק שיעור N" run the project skill `delete-lesson`: `cd backend-ai-tutor-he && APP_ENV=prod ../backend/.venv/bin/python tools/delete_unit_lesson.py --id N --yes` (without `--yes` = dry run). It wipes Storage `lesson-media` + `lesson-audio` under `unit_lessons/N/`, deletes that lesson's `media_jobs`, and resets the generated fields of `lesson_units_content` (row itself and curriculum fields stay). `--with-progress` also clears kids' progress (ask first). Storage must be wiped because `content_version` stays 1 and new media overwrites the same paths, leaving stale files otherwise.

## Lesson generation pipeline (backend-ai-tutor-he) — known trap

- Route `POST /api/tutor/unit-lesson`: per part, `gpt-5.6-sol` writes `explanation` + `question` (`UniversalLessonResponse`), then the **Lesson Director** (`prompts/lesson_director_prompt.txt`, `build_lesson_director_prompt(lesson_text=…)`) splits the explanation into `lesson[]` segments. The question is owned by the teacher and is overwritten in code after the director.
- **All parts must go through `direct_lesson_part()`** (`main.py`): it injects the explanation via the `{lesson_text}` placeholder AND sends it as the user message, runs on `UNIVERSAL_LESSON_MODEL`, validates with `find_invalid_lesson_segments()` (rejects segments copied from the question, ending with `?`, starting with a directive like הסבירו/כיצד/מדוע, or not drawn from the explanation), retries once, then falls back to a deterministic sentence split. Log lines: `LESSON DIRECTOR OK|REJECTED|FALLBACK`.
- Bug fixed 2026-09-15: on 2026-09-01 the prompt lost `{lesson_text}` and Part 1 sent the director only the *question*, so `lesson[]` of Part 1 became the question chopped into sentences (14/15 prod lessons, ids 1,3–12,29–31). **Never remove `{lesson_text}` from the director prompt** and never pass only the question as the director's user message. Product rule: `lesson[]` is explanation only, exactly one `question` per part, explanation always before question.

## Testing / running

- Frontend: open HTML files directly or `python3 -m http.server` from repo root.
- Backend: `cd backend && uvicorn main:app --reload` (needs `.env` with SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY, LEMON_* keys).
