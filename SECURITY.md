# Security — what was found, what was fixed, what is still open

The first audit was 2026-09-09 (read-only; the report is the artifact linked from that
session). This file re-checks every finding against the live system on **2026-09-10**
and is the place to keep score from now on.

How the re-check was done: anonymous reads with the publishable key that every
visitor's browser holds, HEAD/GET against both Render services, header checks on the
site, and — new this time — **a throwaway account** created and deleted inside one
script, to answer the question the first audit could not: what can a signed-in
stranger reach? Every row that test wrote was removed with it; `kid_unit_lesson_progress`
still holds the same four rows it held before.

---

## Fixed

| finding | what changed |
|---|---|
| **The whole question bank was readable anonymously** — 106,096 rows with their answers | `20260910_game_bank_lockdown.sql`: no SELECT policy on `game_questions`; the only way in is `game_next_questions`, which serves at most 25 unanswered rows to a child of the caller and refuses a child who has pulled more than 900 in an hour. Verified: anon gets `[]`, the RPC refuses without a session, a stranger's child is refused |
| **No rate limiting on the backends** | A per-caller sliding window on `/api/*`: 60/min on the tutor, 30/min on the core API, webhook exempt. **Live on the tutor** (it answers 429 with `limit_per_minute: 60`). The core API has not been redeployed — 40 requests pass without a 429 and `/` still 404s |
| Mass scraping of the games | `robots.txt`, `IAKidsGuard` hostname allowlist, the canary in `game-sdk.js`, `LICENSE`. On the mirror, per-IP `limit_req` in nginx (Cloudflare's rate limit does not reach that domain) |

---

## Still open, in the order worth fixing

### 1. Any signed-in user can give themselves a paid subscription — CONFIRMED

The first audit called this "cannot verify from the repo". It is now verified. A
brand-new free account, one call:

```
insert into subscriptions (user_id, plan, status, expires_at)
values (auth.uid(), 'annual', 'active', '2099-01-01')      -> ACCEPTED
```

`is_paid_active_subscription` (`backend-ai-tutor-he/main.py`) reads exactly those
fields, so that row is a lifetime paid account. Anyone with a Google account can do
it from the browser console in ten seconds.

**Fix:** the INSERT policy must pin the values a client is allowed to write, and there
must be no UPDATE policy at all:

```sql
drop policy if exists subscriptions_insert_own on public.subscriptions;
create policy subscriptions_insert_free on public.subscriptions
    for insert to authenticated
    with check (user_id = auth.uid() and plan = 'free'
                and status = 'active' and expires_at is null
                and lemon_subscription_id is null);
drop policy if exists subscriptions_update_own on public.subscriptions;
-- paid rows are written by the LemonSqueezy webhook with the service role only
```

Then check whether anyone has already done it: any row with `plan <> 'free'` and no
`lemon_subscription_id` was not paid for.

### 2. `kid_unit_lesson_progress` has no RLS — CONFIRMED, unchanged

Anonymous SELECT still returns all four rows (`kid_id`, `status`, `progress_percent`,
`mastery_score`, …). An anonymous INSERT was refused only by a NOT NULL constraint,
which means no policy stood in its way — the table is writable too.

```sql
alter table public.kid_unit_lesson_progress enable row level security;
create policy kulp_select_own on public.kid_unit_lesson_progress
    for select to authenticated
    using (kid_id in (select id from public.kids_profiles where user_id = auth.uid()));
-- writing stays with the backend's service role, so no write policy
```

### 3. Exam answer keys are public — NEW

`exam_answer_keys` (14 rows), `exam_questions` (14) and `exams` return rows to an
anonymous caller. The answer key to an exam is the one thing in an exam that must not
be readable.

```sql
alter table public.exam_answer_keys enable row level security;
alter table public.exam_questions   enable row level security;
alter table public.exams            enable row level security;
-- then a SELECT policy for authenticated only, and serve keys from the backend
```

### 4. Generated lesson content is readable by anyone — unchanged

`lesson_units_content`: 150 rows to an anonymous caller. This is what the model was
paid to write and what a subscription is supposed to buy. Either it is deliberately
public — a business decision, not a bug — or it needs a policy.

### 5. `/docs`, `/redoc` and `/openapi.json` are public on both backends — unchanged

Every route and every request schema, to anyone. `FastAPI(docs_url=None,
redoc_url=None, openapi_url=None)` when `APP_ENV == "prod"`.

### 6. No security headers on the site — unchanged

No `Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`,
`X-Content-Type-Options`, `Referrer-Policy` or `Permissions-Policy`. GitHub Pages
cannot set headers, but **Cloudflare can**, through Transform Rules → Modify Response
Header. With the Supabase session living in `localStorage` on 63 pages, any XSS is a
full account takeover, and a CSP is the difference between a bug and a breach.

### 7. `LIMIT = 20` — unchanged

`backend/main.py:311`, still commented `# זמני לבדיקה`. Paying customers are cut off
after twenty messages exactly like free ones, and the read-then-update around it is
not atomic, so parallel requests walk past the limit.

### 8. No usage quota before a model call — unchanged

`/api/tutor/tts` still takes free text from any signed-in account. The per-caller rate
limit added on 2026-09-10 caps the *rate* (60/min) but not the *bill*: a daily quota
per `user_id`, checked before the call, is still missing.

### 9. Smaller, unchanged

| | |
|---|---|
| CORS allows `http://localhost:3000` (and `:5500`, `127.0.0.1:5500` on the tutor) with credentials, in production | gate on `APP_ENV` |
| `games/index.html` listens for `iakids-game-complete` without checking `e.origin` | check it before it ever grants coins |
| Google Tag Manager on kid-facing pages (`he/games/index.html`, `workspace/index.html`) | COPPA: behavioural tracking on pages meant for children needs verified parental consent |
| 180 `print()` calls in the tutor, some printing a child's text | a logger with levels; identifiers and lengths in production, not content |
| Supabase auth uses the implicit flow; no `flowType: 'pkce'` | tokens land in the URL fragment |
| LemonSqueezy webhook: no idempotency, missing `payment_failed` / `paused` / `updated` / `resumed`, `plan` taken from client-supplied `custom_data` | derive the plan from `variant_id`; store the event id |
| No parent/child separation — `he/parent-panel/` needs only a session | a PIN |

---

## Checked and sound

The cross-family isolation is right, and that is the part that matters most. A
signed-in stranger asking for everything got **nothing**:

| table | rows returned to a stranger |
|---|---|
| `kids_profiles`, `kids_chats`, `tutor_sessions`, `usage_summary`, `support_tickets`, `app_admins`, `kid_question_answers`, `kid_game_sessions`, `learning_lessons`, `lesson_plans` | 0 |
| `subscriptions` | 1 — its own |

Also still sound: child-ownership checks on all 17 identified tutor routes,
`sb.auth.get_user(token)` verified against Supabase on every request rather than
decoded locally, homework uploads confined to `{user.id}/` in a non-public bucket
served through signed URLs, the webhook's HMAC on the raw body with
`compare_digest`, chat rendered through `textContent`, and no `eval`, `new Function`,
`document.write` or raw SQL anywhere.

New since the first audit and worth stating: the games now use the site's own
Supabase identity instead of a second Firebase login, so there is one account, one
session, and one thing to secure.

---

## Re-running this

```bash
# anonymous reads, backends, headers
backend/.venv/bin/python tools/security_check.py
```

The account test is deliberately not committed as a script that runs itself: it
creates a real user. It lives in the session transcript, and the shape is: create a
user with the service role, sign in with the publishable key, try the writes and reads
above, delete the user.
