# BUGFIXES — what each commit fixed

Rule (2026-09-16): every `commit` + `push` adds an entry here that says exactly what was fixed, how it showed up, and how it was verified. Newest first. Build numbers refer to the workspace stamp (`IAKIDS • build 0.7.N`).

## 2026-09-17

### 2026-09-17 — evening sweep: payments, Render, the closing summary
- **The lesson closing has never run in production yet** — no lesson has been completed since it was deployed — so the store path was exercised directly: an insert with `session_id = null` succeeds and the cache lookup finds it. Not a bug; simply untested by a real child so far.
- **Render is on today's code.** Every route added today answers there, admin and kid routes included.
- **The payment webhook is healthy in production.** A request with a bogus signature gets 403, which proves the secret is set on Render. The empty `LEMON_*` keys in the local `backend/.env` are a local artefact, and the note about them in `docs/SECURITY.md` is stale on that point.
- **The plan label is chosen by the browser.** `index.html` builds the checkout URL with `checkout[custom][plan]=…`, and the webhook records whatever arrives in `custom_data.plan`. A user can open the monthly variant with `plan=annual`. **Not exploitable today**: nothing treats annual differently from monthly — both are just "paid" — and `expires_at` comes from LemonSqueezy's real `renews_at`. It becomes exploitable the day annual grants anything extra. The plan should derive from `variant_id` on the server. *Recommended, not changed*: the core backend deploys through Render and cannot be verified from here.
- **A replayed webhook refills the month.** `subscription_created` upserts `messages_used: 0` with no check that the `lemon_subscription_id` was already seen, so a re-delivered event resets the quota. Small, code-only, in the core backend. *Recommended, not changed*, same reason.
- **Two read-then-act checks added today** — the child limit and the monthly lesson quota — could be beaten by two simultaneous requests. At two accounts generating lessons this is theoretical; the chat quota was moved into a locked SQL function for exactly this, and these can follow it if volume ever warrants.

### 2026-09-17 — the coach session hole is closed, and the rest of the schema was audited
- **Closed and verified from the server, both directions**: a stranger's account now reads **0** coach sessions where it read 10, and an account with a child reads **exactly 1** — its own. A policy that also locks out the owner is not a fix, so both halves were tested.
- **My sweep query was wrong and I corrected it.** For an INSERT policy the condition lives in `with_check`, not `qual`, so the first version flagged every INSERT policy in the schema for nothing and sent a long list of false positives to be read. Sorry for the noise.
- **Six tables are readable by any signed-in account, and all six are meant to be**: exam pages, exam questions, the games catalogue, the nikud dictionary, the lesson catalogue and lesson content. Shared content, decided in the 2026-09-10 audit. The dangerous columns of `lesson_units_content` were closed separately this morning with column grants. So the `debug_` policy was the only unintended open read.
- **Every write policy checks ownership — tested live, not read.** An anonymous client and a signed-in account writing under another account's id were both refused on `kids_profiles`, `homework_sessions`, `homework_uploads`, `support_tickets`, `kids_memory` and `subscriptions`. That last one includes an account trying to **give itself a paid plan**, which was the 2026-09-10 finding: it is genuinely closed.
- **The `public` role on several policies looks alarming and is not**: the check is `auth.uid() = user_id`, and for an anonymous caller `auth.uid()` is null, so the comparison is never true.
- **Found a way to close `app_admins` after all.** It had to stay open this morning because a policy on `support_tickets` reads it. The sweep shows that policy calls `is_admin(auth.uid())`, so the function exists and runs as the caller. Making it `SECURITY DEFINER` lets the table close while the support pages keep working. Written into `RUN_NOW.sql` as optional, commented out, with the order to run it in.
- **Housekeeping, no rush**: `learning_lessons` carries two identical read policies and `kids_profiles` four overlapping INSERT policies. Harmless in themselves, but four policies on one action is exactly how the `debug_` one stayed invisible.

### 2026-09-17 — a policy left over from debugging was keeping the table open
- **The correct policy was added and changed nothing.** A fresh account still read every coach session. `pg_policies` showed why:

| policy | permissive | roles | cmd | condition |
|---|---|---|---|---|
| `debug_select_learning_coach_sessions` | PERMISSIVE | authenticated | SELECT | `true` |
| `lcs_select_own` | PERMISSIVE | authenticated | SELECT | `kid_id in (...)` |

- **Postgres combines permissive policies with OR.** One policy saying "any signed-in account, all rows" makes every restrictive policy beside it pointless. The new one was never going to help while that one existed — it has to be dropped.
- **My mistake in the first attempt**: I wrote a policy without listing what was already on the table. Adding a rule to a table is not the same as knowing what the table allows.
- **Worth more than this one table**: a `debug_` policy sat in production, invisible until someone looked. `RUN_NOW.sql` now ends with a sweep that lists every permissive SELECT policy in the schema whose condition is just `true` — every table any signed-in account can read in full. There is no reason to assume this was the only one.

### 2026-09-17 — `supabase/migrations/RUN_NOW.sql`: what is actually left to run
- Every migration in the folder was checked against the live project by looking for the object it creates. **Sixteen are applied. One is not**: the policy that stops every signed-in account reading other children's coach sessions.
- The file holds that one block between paste markers, the reason it matters, what keeps working after it, and how to verify — plus the two things still open that are not database changes: `APP_ENV=prod` on Render, which is why 37 routes and 21 schemas are public there while the box answers 404, and the six security headers on iakids.app that the mirror already sends.
- Not reachable from the web: the whole `supabase/` folder is blocked, as is every `.sql`.

### 2026-09-17 — three things in the question mechanism that worked against the child
Reviewed end to end and checked against a real transcript. ארבל answered "המורה, ארנב, תלמידה" — the complete correct answer — and was told **"איבדת את המילה שהכי חשובה במשפט"**. She repeated the same answer. She was told she had missed an animal. She repeated it a third time. She was told a word "with a trace of an animal" was missing. The round limit then ended the dialogue at 60 and the lesson moved on **without ever telling her she had been right**. The root cause, a coach with no answer key, was fixed this morning; the transcript exposed three more.

**1. The score the child sees was arithmetically unfair.** `calculate_lesson_coach_mastery` divided by the *total* number of parts and counted a part not yet reached as zero. The gauge is refreshed after every coach turn and is labelled "הבנה כללית", so:

| parts | score on part 1 | what the child saw |
|---|---|---|
| 2 | 90 | 45% |
| 3 | 90 | 30% |
| 4 | 100 | 25% |

A child doing well was shown a number that reads as failure. The average is now over the parts actually attempted. Verified on real data: a child with 40 on part 1 sees 40, and a finished lesson still reports 76 exactly as before, because at the end every part has a score.

**2. Nobody noticed a child repeating themselves.** An identical answer is the clearest signal a child can send that the hint is not working. `repeated_answer` is now computed from the dialogue and forces the closing behaviour: no fourth hint, say the answer, explain it in a sentence, confirm what the child did get right, move on. A fourth hint to a stuck child is not teaching, it is attrition.

**3. The wording opened with what was missing.** The prompt banned judgemental phrasing only in the final round. It now bans it everywhere and requires the first sentence to be what the child *did* say, with the verbs of loss and failure — איבדת, פספסת, טעית, שכחת, לא ענית — forbidden outright. "מצאת שניים. יש עוד אחד שמחכה" instead of "לא ענית על כל שמות העצם".

**Gates**: the mastery divisor, the repeat detection and all three new prompt sections are pinned. Backup taken in `V14_BACKUP` before the prompt changed.

**Deliberately left alone**: the mastery threshold of 90 does not block a child from continuing, the round limit gives a struggling child *more* turns rather than fewer, and the no-response timer is off during the dialogue. Those three are sound.

### build 0.7.136 — a line that threw on every kid load, on both workspaces
- **`document.getElementById("heroAvatar").src = avatarUrl;`** — that element is not in the page. `getElementById` returned null, the assignment threw, and **everything after it in the function stopped**, including `window.ACTIVE_KID_ID = kid.id`, which other code reads. The same block was written out twice, so the second copy never ran either. Both the Hebrew workspace and the games workspace carried it, identically.
- **Why it hid**: the dashboard fields a few lines above are all null-checked, so the page looked fine. Only the tail of the function was missing, silently.
- **Fix**: the four writes go through a helper that checks the element first, so a missing one is skipped instead of stopping the function. **New gate rule**: writing to an element that is not in the page fails the build, verified by restoring the exact line.

### 2026-09-17 — a child's understanding scores were readable by any signed-in account
- **How it was found**: signing in as a brand new account with no data of its own and reading every table the browser still touches. Twenty-two came back empty, correctly isolated. `learning_coach_sessions` came back with other accounts' rows.
- **What was exposed**: `kid_id`, the lesson, the understanding score the teacher gave at the start and the end, how many rounds the dialogue took, and the timestamps — another child's performance, lesson by lesson. Their actual words were not exposed; `kid_lesson_history` is properly isolated.
- **Cause**: the table had row level security enabled with no policy restricting rows, which in practice means every signed-in account.
- **Migration written, not yet applied**: a policy matching `kid_unit_lesson_progress` — a row is visible when the child belongs to the caller. The two screens that read it already filter by `kid_id`, so the policy should be invisible to them.
- **Checked and sound in the same sweep**: the games question bank is not directly readable while the RPC still serves questions, media jobs have no stuck or failed rows, and no table has an orphan row pointing at a deleted child or lesson.

### 2026-09-17 — nothing was capped; now two things are
- **There was no limit on the number of children.** Not in the browser, not in the server, nowhere. One account already holds nine. The endpoint written this morning had no check either.
- **The Hebrew tutor had no quota of any kind.** The only quota in the whole product is the monthly chat message count, and it is enforced in the *core* backend, the Spanish chat. Lesson generation, images and voice — the expensive half, about $0.87 a lesson — were open to any signed-in account. 178 of 180 accounts are on the free plan.
- **Two limits now exist, both server-side.** Children per account, checked when one is created. New lessons per month, checked **before** the first model call of a fresh generation, so a child is told before anything starts rather than half way through a lesson. A lesson served from cache costs nothing and is never counted.
- **The numbers are deliberately far above real use**: three children free and ten paid, thirty new lessons a month free and two hundred paid. Measured the same day: only two accounts have ever generated a lesson, ten and six in a month. These are a ceiling against a runaway loop or an abusive account, not a paywall — that is a product decision, and all four are environment variables (`FREE_MAX_KIDS`, `PAID_MAX_KIDS`, `FREE_MONTHLY_LESSONS`, `PAID_MONTHLY_LESSONS`). `LESSON_QUOTA_ENFORCE=0` measures without blocking.
- **A subscription lookup that fails never blocks a child**: it falls back to treating the account as free rather than refusing.
- **Verified end to end** on a real account: three children created, the fourth refused with 403 and a Hebrew explanation. The paid account resolves as paid, the free one as free, and the lesson counts match what the cost table shows.
- **The parent sees the reason**: the API module was turning a structured error into "[object Object]". It now surfaces the server's own message.

### 2026-09-17 — "הישגים" and "הקבצים שלי" exist now, and the sidebar is whole
- Two more buttons that had pointed at nothing since the workspace was written.
- **`GET /api/kid/achievements`** counts what the child actually did: lessons opened and finished, the best and average understanding score, the subjects, games played and finished, and the number of distinct days they studied. **A number that cannot be computed is left out rather than shown as a zero**, because a zero reads as failure to a child. Six badges, earned or locked, drawn from those same numbers.
- **`GET /api/kid/files`** lists the homework pages the child photographed, with how many questions were answered. An account with nothing uploaded gets a sentence and a button to the workspace, not an empty screen.
- Both pages share the design of `/he/my-lessons/` and neither touches the database.
- **Verified against real data**: nine lessons opened and one finished, best understanding 76%, two subjects, ten games with one finished, three active days.

### 2026-09-17 — the queries asking for columns that do not exist are fixed, and gated
- **`/games/progress/` is repaired.** It asked `kids_profiles` for `avatar_url` and `grade`, which are `avatar_key` and `age`, and embedded `games_catalog` with `icon_path` and `game_url`, which are `icon` and `route_path`. PostgREST answered 42703 to both and the call sites swallowed it, so the page drew an empty report and looked merely unused. The avatar now goes through the same known-avatar helper as the rest of the site.
- **All 65 distinct browser queries now run clean** against the real schema.
- **New gate rule** with the column list recorded in `tools/browser_query_columns.json`: a query asking for a column the table does not have fails the build. It compares shapes and never touches the database, so the gate stays offline. Verified by restoring the exact bug that was live.

- The same class as the `parent_lesson` bug. Every distinct database query in the browser, 65 of them, was run against the real schema. Two fail, both on `/games/progress/`: `kids_profiles` is asked for `avatar_url` and `grade` (the columns are `avatar_key` and `age`), and `kid_game_sessions` embeds `games_catalog` with column names it does not have. Both sit behind `if(!error)`, so the page silently shows nothing. **Found, not yet fixed.**
- The pattern that hides them is everywhere: eight sites assign query results only `if(!r.error)`, and 33 empty `catch` blocks in the workspace alone. Most disappear with the move to the backend; the rest need to say something when they fail.

### 2026-09-17 — "השיעורים שלי" exists now
- **The page behind the sidebar button was never built.** It has been there since the workspace was written, and every child who pressed it got a server error. The data was always there: the progress row joined to the lesson and its subject.
- **`GET /api/kid/lessons`** returns every lesson the child has opened, newest activity first, with the subject, the unit, the progress, the understanding score and the dates. The kid is resolved against the caller's account first, so one parent cannot read another's child. It is registered before `/api/kid/{kid_id}` so "lessons" is not swallowed as an id.
- **The page reads nothing from the database**, in keeping with the rule taken today. It groups by subject, because a child thinks in subjects and not in dates, shows a progress bar per lesson, filters by in-progress or completed, and opens a lesson back in the workspace. An account with no child, and a child with no lessons, each get a sentence rather than an empty screen.
- **Verified against the real data**: ארבל has nine lessons opened across two subjects with one completed, and every row resolves to its subject, unit and lesson name.

### 2026-09-17 — internal documents were readable on the web; every menu link audited
- **The documents are now closed.** The site root is the repo, so every `.md` in it was public. `SECURITY.md` — "what was found, what was fixed, what is still open" — was the worst of them: a list of open security findings, served to anyone. `BUGFIXES.md`, `MIGRATION_TO_BACKEND.md`, `PERFORMANCE.md`, `HANDOFF.md`, `TODO.md` and the deploy script were all readable too. They now live in `docs/`, which nginx refuses, and a rule blocks `.md`, `.sql`, `.sh` and similar anywhere on the site, so the game specs are covered in place. Verified: the documents answer 404 and the site, its assets and the games still answer 200.
- **Every internal link on the site was checked**, 38 of them across all pages. Seven were broken. Three were simply pointing at the wrong path and are fixed:
  - `/chat/` — **the Spanish onboarding sent every new account there when it finished**, and the page does not exist. It goes to `/workspace/` now. This one was breaking sign-up.
  - `/pt/support/` — the Portuguese workspace's support button; support is one page for all languages.
  - `/workspace/u1` — a placeholder path left in a marketing page, in two places, with a comment saying to change it.
- **Four pages in the Hebrew sidebar were never built**: "השיעורים שלי", "הכנה למבחן", "הישגים", "הקבצים שלי". Until they exist the buttons say so instead of dropping the child on a server error.

### 2026-09-17 — bug sweep from the real logs
- **Every documentation file in the repo is readable on the web.** The site root is the repo itself, and nginx blocks `.git`, the backend folders, `supabase` and `CLAUDE.md` — but not markdown. `/BUGFIXES.md`, `/MIGRATION_TO_BACKEND.md`, `/PERFORMANCE.md`, `/handoff_perfromance.md` and `/tools/deploy_tutor.sh` all answer 200 right now. This file alone describes every bug and every security hole we have closed, with table names, column names and route names, and the migration document is a table-by-table map of the database. Three of those files were written today, so the exposure was made worse by the work itself. **A tested nginx fix is ready and waiting for approval**; it is a production config change.
- **The missing video poster**: `/assets/backgrounds/video-poster.webp`, asked for on every load of the Hebrew landing page, 58 times in the log and never there. The hero video showed nothing until it buffered. A real frame was pulled from the demo video itself and saved at 1280px, 57 KB.
- **The avatar bug was in three more screens**, untouched: the Spanish workspace, the Portuguese workspace and the games workspace all built the image path straight from `avatar_key`. Fixed with the same known-avatar helper, eight call sites in all.
- **The gate was only scanning part of the site.** That is why the avatar bug survived in those three. It now covers every folder that serves a page, and the first thing that showed is that the count of direct database calls in the browser is **230**, not the 178 first measured. The ratchet holds the true figure.
- **Not a bug: the "144 empty lessons".** Of 206 lesson rows, 15 have been generated and the rest are `empty` because lessons are generated when a child opens them. The row's own `status` column is not read by any live screen.
- **The backend itself is clean**: one transient metrics timeout in the last three hours, nothing else. The errors filling the earlier log were the corrupted key and the missing images, both fixed today.

### 2026-09-17 — the longest call in the lesson pipeline was taking the slow way round
- **Where the child's wait goes**: the Visual Director is one call of 2000 to 3300 output tokens, measured between 14 and 46 seconds, while the whole rest of the lesson text takes 6 to 22 seconds a part. The child waits through all of it before a single word appears.
- **Measured properly, not guessed**: the same prompt sent three times to each provider, interleaved, same SDK (openai 3.10.0) and same server. Direct won every single run.

| run | direct | openrouter |
|---|---|---|
| 1 | 17.9 s | 28.0 s |
| 2 | 22.5 s | 31.3 s |
| 3 | 15.5 s | 27.7 s |

- **Fix**: this one call goes straight to OpenAI. Everything else stays on OpenRouter, because the reason the service runs through it is the voice quota, which this call never touches. `VISUAL_DIRECTOR_PROVIDER=openrouter` puts it back without a deploy.
- **Caveat worth keeping**: this is true for this model, this request shape and this server. Another project measured the opposite, which is entirely possible — for models OpenRouter routes to a faster provider, or from a different region, the extra hop can pay for itself. The knob exists so the answer can be re-measured rather than argued.
- **Bug caught while testing**: `DEFAULT_OPENAI_MODEL` is rebound to the prefixed `openai/gpt-4o-mini` at import time when the service runs on OpenRouter, so the first version of this change handed a prefixed id to the direct API, which does not know it. The selector strips the prefix.

### 2026-09-17 — cost reporting: a missing price and a view that counted almost nothing
- **The missing price**: `gemini-3.1-flash-lite` was not in `MODEL_PRICING_USD`, and it is the model behind the image text checks and the nikud pass. Of the last thousand recorded calls, 134 had no price at all and landed in the reports as "unknown". Added at the published rate. Verified that all five pricing paths now resolve: text for both providers, images per image, and voice by audio seconds.
- **Applied and verified**: media and text now add up to the total exactly (lesson 12: 2.8977 + 0.166 = 3.0637), and the picture it finally shows is that **media is about 95% of what a lesson costs**. The first attempt was rejected with `42P16: cannot change name of view column`, because `create or replace view` may only append columns — putting the new one in the middle reads as renaming `cost_usd`. The new column sits last.
- **The view**: `ai_costs_per_lesson.media_cost_usd` counted `purpose in ('tts','image','video','lesson')`, but the worker — which generates every image, every voice line and every intro video — tags its calls `media`. In the last five thousand calls that is 634 rows, the largest group, and none of them counted. `tts_live` and `intro` were missed too, while `lesson`, which is text, was counted as media. The per-lesson media figure has been wrong since the view was written, and wrong in the direction that matters: it under-reported the expensive half. Migration written, **not yet applied**, adding `text_cost_usd` alongside so the two halves add up to the total and any gap is visible.
- **Closed on its own**: the OpenRouter voice rows that were stuck at `cost_source='pending'` are all resolved — zero pending rows remain, so the generation-id lookup is working.
- **Cannot be fixed by a price table**: a few `gpt-5.6-sol` rows carry no token counts at all, because the response reported no usage. They stay unpriced and visible as "unknown", which is the honest outcome.

### 2026-09-17 — the parent's picture was a 404 on five pages
- **Symptom**: `/assets/default-parent.png` was requested on every load of the workspace (Hebrew, Spanish, Portuguese and games) and the add-subject page, and the file did not exist. A parent whose account has no picture from Google got a broken image in the top bar, and the site log filled with 404s.
- **Fix**: the file now exists — a deliberately generic illustrated figure, not a recognisable person, in the calm palette the app uses, 256 pixels and under 50 KB because it loads on every page. No code changed: the five references were already correct.

### 2026-09-17 — the games leaderboard was writing to tables that do not exist
- **Symptom in the code**: every completed game called `IAKidsCloud.recordWin()`, which inserted into `game_wins`. That table is not in the database, and neither is `game_achievements`. Each write failed inside its own try/catch, so nothing ever surfaced and nothing was ever recorded. The SQL file the comment pointed at, `games/games-tables.sql`, does not exist either.
- **Nothing read them**: `recordAchievement` and `topWins` have no callers anywhere on the site, and no leaderboard is drawn from them.
- **Not fixed by creating the tables**, for two reasons. The design keyed rows on an email the browser supplied, and its own comment admitted that could not be verified — anyone could post a score under any name. And the UI no longer talks to the database at all. A leaderboard, if it is wanted, is a backend endpoint scoring against the signed-in account.
- **Fix**: the object is an honest no-op stub with the whole story written above it, so existing call sites keep working and nobody believes scores are being saved. Four more direct database calls gone from the browser.

### build 0.7.135 — a gender chosen by mistake could not be corrected from the workspace
- **Symptom**: the parent panel could always change a child's gender, and its field even preloads the current value. The workspace could not. Gender was set once by the popup that appears on entry, and after that, right or wrong, it was locked.
- **Why it matters here**: the teacher addresses the child by that value in writing *and* in speech, so a wrong choice is heard in every sentence.
- **Fix**: the child-details dialog has a "בן או בת" field right after the name, in the same style as the grade picker. It marks what is set now, so the parent can see it and change it with one click; leaving it alone keeps what is stored.
- **Note**: audio already generated stays in the old wording. The voice cache key includes gender, so every new line is correct, but a line generated earlier sounds as it was generated.

### 2026-09-17 — he/parent-panel is off the database
- The three direct `kids_profiles` calls — list, update and create — became `iakidsApi` calls. This is the first screen that exercises all three operations.

### 2026-09-17 — the two converted screens were broken, twice, for two different reasons
- **Symptom**: on `/he/add-subject/` typing in the chat did nothing at all. No error, no message, nothing.
- **Cause one, mine**: the pages create their client as `const sb = supabase.createClient(...)`, and **a `const` at the top level of a classic script never becomes a property of `window`**. The API module looked for `window.sb`, found nothing, and `activeKid()` returned null quietly. The chat's first line is `if (!text || !CURRENT_KID) return;`, so it simply returned. The same applied to the key, also a `const`.
- **Fix**: the module now walks a chain — a client the page registered with `useClient()`, a global one if there is one, the games SDK's client, and failing all of those it creates its own. The session lives in `localStorage` and is shared, so it is the same session either way. It also warns out loud instead of failing silently. Verified in a real JS engine for four cases including "page uses const for both the client and the key".
- **Cause two, the browser**: after the fix the page still did not work. The site's own log showed the browser had loaded the module at 5128 bytes, and the fixed file is 7435; on the next visit the page came back 304 and the module was never re-requested. The browser was running the broken copy from cache. **Every shared JS file gets a version in its script tag from the first day** — the project already does this for the dictation and completion scripts. Without it a fix reaches the server and never reaches the user, and both sides think it shipped.
- **Verified end to end from the production log**: `GET /api/kid/...` answered 200 for the real parent, three `curriculum/chat` calls answered 200, `CUSTOM CURRICULUM APPROVED` followed, and the subject "משחק טאקי" is in the database, active, with its curriculum. Zero errors in the whole window.
- **Noticed, not fixed**: `/assets/default-parent.png` is requested on the add-subject page and does not exist, 404 on every load. It is the parent picture shown when the account has none from Google.

### 2026-09-17 — he/add-subject is off the database
- Two direct `kids_profiles` queries became one `iakidsApi.activeKid()` call. The page no longer knows the table exists.
- Second screen of stage 1. The gate's ceiling on direct database calls drops with each screen that ships, so the number can only go down.

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
