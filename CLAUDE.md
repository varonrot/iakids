# iakids — CLAUDE.md

Safe AI tutor/chat platform for kids, live at **https://iakids.app** (CNAME → GitHub Pages).
Multilingual static site: Spanish is default (root `index.html`, `lang="es"`), plus `/he` (Hebrew, RTL), `/de`, `/pt`.

## Stack

- **Frontend**: plain static HTML/CSS/JS. No framework, no build step. Large single-file pages (e.g. `he/index.html` ~250KB). Deploy = push to GitHub Pages.
- **Backends** (Python FastAPI, deployed separately — NOT served by Pages):
  - `backend/` — core chat API: Supabase + OpenAI, LemonSqueezy payment webhooks (HMAC-verified). Prompts loaded from `backend/prompts/`.
  - `backend-ai-tutor-he/` — Hebrew AI tutor: OpenAI + Google Gemini (`google-genai`, incl. TTS/wave audio), Supabase.
    Providers: `AI_PROVIDER=direct|openrouter` (chat + lesson models) and `TTS_PROVIDER=direct|openrouter` (same Gemini TTS model via OpenRouter's `/audio/speech`, needs `OPENROUTER_API_KEY`); default `direct`. Images stay on the direct Gemini client. `tools/tts_check.py` synthesizes one sentence with the configured provider.
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
parent-dashboard/     parent dashboard
backend/              core FastAPI (chat, payments)
backend-ai-tutor-he/  Hebrew tutor FastAPI (many main_vN.py versions — main.py is current)
iakids_*_prompt.txt   system prompts (root copies; backend loads from backend/prompts/)
blog/ privacy/ terms/ coppa/ refunds/ support/ ...  content & legal pages
```

## Conventions & gotchas

- **Versioned files, not git branches**: `index2.html`, `main_v6.py`, `workspace_back_up.html` etc. The unnumbered `main.py`/`index.html` is the live one. Don't delete backups without asking.
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

- On "גיבוי"/"backup": run `bash .claude/skills/backup/backup.sh "<note>"` (project skill `backup`). It snapshots `backend/main.py`, `backend-ai-tutor-he/main.py` and every prompt file (root `iakids_*_prompt.txt`, `backend/prompts/`, `backend-ai-tutor-he/prompts/`) into the next `V<N>_BACKUP/` folder, verifies with `diff`, writes a README. Never overwrite an existing `V<N>_BACKUP`. Take one before touching `main.py` or a prompt.

## Lesson generation pipeline (backend-ai-tutor-he) — known trap

- Route `POST /api/tutor/unit-lesson`: per part, `gpt-5.6-sol` writes `explanation` + `question` (`UniversalLessonResponse`), then the **Lesson Director** (`prompts/lesson_director_prompt.txt`, `build_lesson_director_prompt(lesson_text=…)`) splits the explanation into `lesson[]` segments. The question is owned by the teacher and is overwritten in code after the director.
- **All parts must go through `direct_lesson_part()`** (`main.py`): it injects the explanation via the `{lesson_text}` placeholder AND sends it as the user message, runs on `UNIVERSAL_LESSON_MODEL`, validates with `find_invalid_lesson_segments()` (rejects segments copied from the question, ending with `?`, starting with a directive like הסבירו/כיצד/מדוע, or not drawn from the explanation), retries once, then falls back to a deterministic sentence split. Log lines: `LESSON DIRECTOR OK|REJECTED|FALLBACK`.
- Bug fixed 2026-09-15: on 2026-09-01 the prompt lost `{lesson_text}` and Part 1 sent the director only the *question*, so `lesson[]` of Part 1 became the question chopped into sentences (14/15 prod lessons, ids 1,3–12,29–31). **Never remove `{lesson_text}` from the director prompt** and never pass only the question as the director's user message. Product rule: `lesson[]` is explanation only, exactly one `question` per part, explanation always before question.

## Testing / running

- Frontend: open HTML files directly or `python3 -m http.server` from repo root.
- Backend: `cd backend && uvicorn main:app --reload` (needs `.env` with SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY, LEMON_* keys).
