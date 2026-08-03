# iakids — CLAUDE.md

Safe AI tutor/chat platform for kids, live at **https://iakids.app** (CNAME → GitHub Pages).
Multilingual static site: Spanish is default (root `index.html`, `lang="es"`), plus `/he` (Hebrew, RTL), `/de`, `/pt`.

## Stack

- **Frontend**: plain static HTML/CSS/JS. No framework, no build step. Large single-file pages (e.g. `he/index.html` ~250KB). Deploy = push to GitHub Pages.
- **Backends** (Python FastAPI, deployed separately — NOT served by Pages):
  - `backend/` — core chat API: Supabase + OpenAI, LemonSqueezy payment webhooks (HMAC-verified). Prompts loaded from `backend/prompts/`.
  - `backend-ai-tutor-he/` — Hebrew AI tutor: OpenAI + Google Gemini (`google-genai`, incl. TTS/wave audio), Supabase.
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
- **Secrets**: `backend/.env` exists locally; `backend/db.py` has hardcoded Supabase creds (known issue — do not copy the pattern; use env vars).
- **Edit style**: pages are self-contained; match existing inline CSS/JS style, no new deps or build tools.
- **Games**: each game = own folder `/games/<slug>/` with `index.html` + `GAME.md` (spec + build subtasks), own IndexedDB `iakids_game_<slug>`, implements SDK contract from `games/GAMES.md`. Shared coin wallet (`IAKidsCoins`, DB `iakids_wallet`): +10 right / −5 wrong / +25 complete / streak bonus. Completion reported via `postMessage {type:'iakids-game-complete'}`. Hub (`games/index.html`) auto-detects playable games by probing `<slug>/index.html` — paste a game folder and it goes live, no code edits.
- **Before implementing a new game**: read its `games/<slug>/GAME.md` fully, then research the game before coding — how existing versions of this game type look and feel (what makes them fun/beautiful for kids), and the correct content logic (question generation, distractor quality, edge cases like Hebrew final letters, RTL, level balance). Only then build, following the GAME.md subtask checklist. Beautiful + correct beats fast: kids notice jank, parents notice wrong answers.
- **Mandatory interface for EVERY new game**: the full 11-point spec lives in **`games/INTERFACE.md`** — read it before writing code, it's the single source of truth (rounds/level picker, coins, no-repeat questions, adaptive difficulty, feedback FX, question timer, help modal, end screen with share, languages, home button — most of these are automatic once a game links `game-sdk.js`/`game-style.css`, see that doc's "Automatic — no code needed" section). Working reference: `games/demo/index.html`. Game catalog + SDK contract: `games/GAMES.md`. Tournaments and the אלוף האלופים table (`games/champions/`) need zero per-game code. After building: browser-test a full playthrough (zero console errors) and screenshot.

## Testing / running

- Frontend: open HTML files directly or `python3 -m http.server` from repo root.
- Backend: `cd backend && uvicorn main:app --reload` (needs `.env` with SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY, LEMON_* keys).
