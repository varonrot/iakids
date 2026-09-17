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

## Fixed on 2026-09-10, verified live after the migrations landed

| finding | verified how |
|---|---|
| **A user could write themselves a paid subscription** | a fresh account's `insert plan='annual', expires_at='2099-01-01'` is now refused by the policy; the free row onboarding writes still goes in; an update to `annual` changes 0 rows and the row still reads `free` |
| `kid_unit_lesson_progress` had no RLS | anonymous read now returns nothing; a parent sees their own child and 0 rows of anyone else's |
| `exam_answer_keys` readable by anyone | empty for an anonymous caller *and* for a signed-in one — RLS on with no policy, so only the backend sees it |
| `exam_questions`, `exams` readable by anyone | closed to anonymous, still readable signed in |
| `lesson_units_content` — 150 rows to the open internet | closed to anonymous; the workspace still reads it signed in |
| Chat quota was a flat 20 for everyone, and racy | `chat_consume_message` is refused to a browser and answers the backend `{"allowed": true, "used": 1, "limit": 20, "plan": "free"}` |

**Nobody had exploited the subscription hole.** Every paid row in the table has a
LemonSqueezy subscription id behind it.

`tools/security_check.py` went from 17 findings to 12. The twelve that remain are
`/docs`, `/redoc` and `/openapi.json` on the two backends — fixed in code, waiting on a
Render deploy — and the six response headers, which are a Cloudflare setting.

---

## Still open, in the order worth fixing

### 1. `/docs`, `/redoc` and `/openapi.json` are public on both backends

Every route and every request schema, to anyone. **Fixed in code** — `FastAPI(docs_url=None,
redoc_url=None, openapi_url=None)` when `APP_ENV == "prod"` — and waiting on a Render
deploy. Set `APP_ENV=prod` in both services' environment: without it the code thinks it
is in development and leaves them on.

### 2. No security headers on the site

No `Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`,
`X-Content-Type-Options`, `Referrer-Policy` or `Permissions-Policy` on `iakids.app`.
GitHub Pages cannot set headers; **Cloudflare can**, through Rules → Transform Rules →
Modify Response Header. The exact CSP is `$iakids_csp` in
`ops/nginx-smarts-brains.conf`, where it is already live and working on the mirror —
test there first.

With the Supabase session living in `localStorage` on 63 pages, any XSS is a full
account takeover, and a CSP is the difference between a bug and a breach.

### 3. No usage quota before a model call

`/api/tutor/tts` takes free text from any signed-in account. The per-caller rate limit
caps the *rate* (60/min) but not the *bill*. The chat now has a real monthly quota
(`chat_consume_message`); TTS, images and lesson generation do not.

### 4. Supabase auth still uses the implicit flow

No `flowType: 'pkce'`, so tokens arrive in the URL fragment and can reach history,
extensions and analytics. Deliberately not changed here: 63 pages construct a client,
and a half-migration breaks sign-in for everyone. It needs one pass, all pages at once,
with the OAuth round trip actually tested in a browser.

### 5. The LemonSqueezy webhook

No idempotency (a re-sent `subscription_created` resets `messages_used`), no handling
for `payment_failed`, `paused`, `updated` or `resumed`, and `plan` is taken from
client-supplied `custom_data` rather than derived from `variant_id`. The HMAC on the
raw body is correct.

Both keys are also empty in `backend/.env`, so the signature cannot be verified at all
right now and neither customer's country or real revenue can be read back.

### 6. Smaller

| | |
|---|---|
| No parent/child separation — `he/parent-panel/` needs only a session | a PIN |
| 180 `print()` calls in the tutor; the two that printed a child's own words are fixed, the rest still print identifiers | a logger with levels |
| Firebase rules for the `smarts-brains` project are not visible from the repo | the games no longer use Firebase for identity, so this shrank to "check the old project is locked down" |

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
