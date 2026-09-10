# What is left to do

Everything known and not yet done, in one place, newest work at 2026-09-10. Security
findings have their own file — **`SECURITY.md`** — because they are checked as a set;
this file points at them rather than repeating them.

Order within each section is the order worth doing them in.

The same picture as a PDF — architecture, capacity, gaps, bugs and the plan — is
`tools/iakids-report.pdf`, redrawn with `backend/.venv/bin/python tools/report_pdf.py`
after this file or `SECURITY.md` changes. It supersedes the earlier readiness report.

---

## Waiting on you, not on code

These are done in the repo and inert until someone presses a button somewhere.

| what | where | why it matters |
|---|---|---|
| ~~Paste the four pending migrations~~ | Supabase SQL editor | **done 2026-09-10** — `APPLY_NOW.sql` applied and verified end to end |
| **Redeploy `iakids-backend` on Render, with `APP_ENV=prod`** | Render | the capacity block (96 threads, 30/min rate limit), the `/` health route, the closed `/docs`, CORS without localhost and the new chat quota have all never gone out. Without `APP_ENV=prod` the docs stay open even after the deploy |
| **Redeploy `iakids-ai-tutor-he` on Render, with `APP_ENV=prod`** | Render | the async conversion, the closed `/docs`, the stop on printing children's words into the logs, and the new `/` health route. Point Render's health check at `/` on **both** services — `/openapi.json` was the tutor's only unauthenticated 200 and prod closes it |
| **Cloudflare: security headers** | Rules → Transform Rules → Modify Response Header | CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy. See `SECURITY.md` §6 — this is the single highest-value thing on this page |
| **Cloudflare: rate limit `/games/*`** | Security → WAF → Rate limiting | `games/tools/PROTECTION.md` §3. The mirror already has one in nginx; iakids.app does not |
| **Supabase compute step, then measure again** | Supabase → Settings → Compute | the ceiling is DB CPU (`tools/CAPACITY.md`). Re-run the wrk numbers after, to see what the step bought |
| **A LemonSqueezy read API key** | `backend/.env` → `LEMON_API_KEY` | it is empty, and so is `LEMON_WEBHOOK_SECRET`. Without them the country, city and real revenue of the two paying customers cannot be read back, and the webhook cannot be verified |

---

## Bugs

### Open

**`lemon_order_id` is null on both paid subscriptions.** Both rows have a
`lemon_customer_id` and a `lemon_subscription_id` but no order. Either
`order_created` never ran, or the rows were made by hand. If money actually moved,
the database disagrees with LemonSqueezy about it. Needs the API key above to settle.

**`admin/dashboard/` cannot connect.** The anon key in the file is literally truncated
to `"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...."`. The page has never worked. It also
reads `subscriptions` directly, which is the table anyone can write to
(`SECURITY.md` §1).

**`tutor_sessions.mode` and `.device_type` are null in all 113 rows.** The columns
exist and nothing fills them, so "which device, which mode" cannot be answered.

**`game_wins` and `game_achievements` do not exist.** `IAKidsCloud.recordWin` and
`recordAchievement` swallow the error, so the cloud leaderboard silently does nothing.
Either create the tables (`games/games-tables.sql`) or remove the code.

**`get_or_generate_unit_lesson` makes six sequential Supabase round trips.** Each one
waits for the last. They are independent and could go together.

### Fixed on 2026-09-10, listed so they are not re-reported

- Games asked a parent to sign in again — the games ran a second identity (Firebase)
  next to the site's Supabase one. Supabase is the identity now.
- The workspace dock kept six columns after two buttons were hidden, so four buttons
  sat off-centre.
- The signed-in name pill and the champions tables were white-on-white on the dark
  theme.
- `smarts-brains.online` served every JS and CSS file uncompressed (96 KB for
  `game-sdk.js`) with `no-cache` on everything.
- `game_record_answers` was created but failed on every call: the loop variable and a
  subquery alias were both named `a`.

---

## Worth building

**Batch what the tutor writes, the way the games now do.** `IAKidsOutbox` turned a
game session from 14 database calls into 4. The tutor writes one row per message.

**A queue for the tutor's heavy work.** Lesson audio, visuals and hero images run in
`BackgroundTasks` and a `ThreadPoolExecutor` inside the request process today, so a
deploy loses whatever was in flight and the work competes with requests for CPU.
A Redis worker (`arq`/RQ) or Supabase's own `pgmq` moves it off the web process and
makes it survive a restart. There is already a `redis:7-alpine` container on the
server. Not the chat itself: a child is waiting for that answer, and a queue cannot
return one.

**One admin dashboard instead of two.** `he/iakids-admin-dashboard-he/` is the good
one (sessions, usage minutes, model calls, tokens, cost, charts). `admin/dashboard/`
has the business numbers (customers, free/paying/cancelled, MRR) and does not work.
Fold the second into the first and add: countries (once the migration is pasted),
sign-ins over time, and time spent per area. Guard it with `app_admins` in the
policies, not with an email list in JavaScript.

**Time spent per area.** `tutor_sessions.duration_seconds` and
`kid_game_sessions.duration_seconds` cover the tutor and the games. Everywhere else —
the workspace, the parent panel, the hub — is unmeasured.

**Load from more than one machine.** The current ceiling numbers were found with
`wrk` from a two-core box; they are real, but the next measurement needs several
machines to push past them.

**A verifier for the question bank.** Questions generated in a browser land as
`source='generated', verified=false` and are never served. Nothing promotes them.
Until something does, the bank only grows with what was seeded.

---

## Housekeeping

- `CLAUDE.md` still says `backend/db.py` has hardcoded credentials. That file is gone.
- `parent-dashboard/index.com` — an `.htm`-shaped typo; nothing serves it.
- `ops/nginx-smarts-brains.conf` is a copy of the live nginx config and is kept in step
  by hand. If you edit the server, copy it back.
- The nikud pipeline (`games/tools/`) is the one thing here with real tests; the games
  themselves have none. A smoke test that opens each game and asserts zero console
  errors would catch what the SDK version bump keeps breaking.
