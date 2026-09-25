# How many children the tutor API holds — before and after (2026-09-25)

Measured on this box (`s-2vcpu-2gb`, nyc1) with `performance/run.py`. Every number below comes
from a run whose raw file is in `performance/results/`; the route-by-route tables are in
`results/REPORT-numbers.md`. Nothing here is shipped: the changes are in the working tree.

**Goal given: more than 100,000 children at once by the end of development.**

---

## 1. The answer in five lines

1. **Today (old code) one tutor process holds about 155 children in a lesson**, and one child
   opening a lesson while seven others do froze the whole server for half a second; the main
   chat blocked every other child for up to 14 s under load.
2. **After the changes: ~177 children per CPU core, 54 % fewer database calls per child**, and the
   routes a lesson screen polls answer **2.5–6x more requests a second** on the real production
   database, at a third of the latency.
3. The server scales with cores: 1 → 2 cores gave +58 % on the same routes (while sharing those
   cores with the load generator and production).
4. **100,000 children is ~560 busy cores of web process, ~21,000 database calls a second, and
   thousands of model calls a second.** That is not one bigger server; it is a different
   architecture (section 5) — and at that size the AI bill, not the servers, is the ceiling.
5. The heavy work should move off the machine children talk to: the media worker first (no code
   change), then the AI routes onto their own pool (a proxy rule, no code change).

---

## 2. What changed in the code (working tree, not committed)

| change | file | effect measured |
|---|---|---|
| Login tokens verified locally against the project's public key (ES256/JWKS), network check only as fallback | `backend-ai-tutor-he/request_cache.py`, `authenticate_user` | −1 database round trip on **every** request |
| Child row cached 60 s per (parent, child), dropped on `/api/kid/update` | `get_child_by_id` | −1 round trip on nearly every request |
| Subscription cached 60 s, curriculum row 5 min | `is_paid_active_subscription`, `get_learning_lesson` | lesson open 10 → 3 calls |
| Same media job not re-sent to the database within 60 s | `enqueue_media_job` | lesson open no longer re-enqueues 3 jobs per poll |
| Three `async` routes no longer wait on the network **on the event loop** | `openai_clean_chat`, `homework_coach_v2`, `get_or_generate_unit_lesson` | lesson open 0.7 → 25.7 req/s; chat no longer freezes the server |
| Cache hit/miss and local/network login counts on the metrics line | `ops.gauges["request_cache"]` | visible in production |

Not cached on purpose: the lesson row itself (`lesson_units_content`) — the worker flips its
audio/visual status while a child polls, and a cached row would hide the new pictures.

Trade-off to know: a login revoked at logout stays usable until the token expires (1 hour by
default). That is what every Supabase client that uses `getClaims()` accepts. `AUTH_LOCAL_JWT=0`
turns it off; `REQUEST_CACHE=0` turns every cache off.

---

## 3. Before → after, in numbers

### 3a. Real production database (6 read-only routes, capped at 32 at once, 2026-09-25 06:37–06:45 UTC)

| route | one user, ms | requests/s at 8 users | p95 at 8 users | CPU ms / request | DB calls / request |
|---|---|---|---|---|---|
| units | 352 → **122** | 19.2 → **52.9** | 798 → **257** | 17.1 → **11.0** | 3 → **1** |
| active-lesson-state | 363 → **120** | 18.0 → **53.3** | 1,463 → **418** | 23.3 → **14.4** | 3 → **1** |
| audio (polled) | 487 → **132** | 15.1 → **38.0** | 722 → **309** | 28.6 → **19.9** | 4 → **1** |
| kid-lessons | 347 → **118** | 21.1 → **53.0** | 514 → **274** | 15.5 → **10.4** | 3 → **1** |
| check-set | 234 → **5** | 30.6 → **142.2** | 363 → **230** | 13.6 → **6.3** | 2 → **0** |
| kid-get | 222 → **5** | 26.8 → **170.0** | 529 → **98** | 14.4 → **5.3** | 2 → **0** |

With the old code the process sat at 30–39 % CPU while throughput stayed flat: it was waiting on
round trips to Supabase Auth and the database. With the new code the same routes run the CPU to
50–95 % — the limit is now this machine, which is the limit you can buy your way past.

The live service's median latency stayed at 11–12 ms during both passes; one step of the new
pass pushed its p95 to 660 ms because the test used a whole core of this 2-core box. Test parents
and children were created and deleted; none is left.

### 3b. Fake database (100 ms per call), production-median model delays — every route type

| route | kind | requests/s where it still kept up | CPU ms / request | DB calls |
|---|---|---|---|---|
| open a lesson (`unit-lesson`) | media | 0.7 → **25.7** (event loop no longer blocked) | 72 → 42 | 10 → 3 |
| `visuals` (polled) | read | 15.7 → **37.5** | 38 → 20 | 4 → 1 |
| `audio` (polled) | media | 14.4 → **39.3** | 34 → 21 | 4 → 1 |
| `hero-image` | media | 16.1 → **40.8** | 36 → 23 | 4 → 1 |
| `tts` | model | 42.3 → **115.8** | 22 → 9 | 2 → 0 |
| `kid-get` | read | 34.7 → **181.3** | 14 → 5 | 2 → 0 |
| `check-set` | read | 35.1 → **160.2** | 14 → 6 | 2 → 0 |
| `structured-lesson` (answers) | model | 1.1 → **4.2** | 109 → 126 | 13 → 10 |
| `tutor-chat` | model | 4.3 → 4.5 | 102 → 93 | 8 → 6 |
| `openai-clean-chat` (main chat) | model | event loop blocked, **lag p95 14 s** → not blocked at 256 at once | 60 → 80 | 2 → 0 |

### 3c. One child in a lesson (per minute, from `routes.CHILD_MIX_PER_MINUTE`)

| | before | after |
|---|---|---|
| CPU of our server | 270 ms | **238 ms** |
| database calls | 27.7 | **12.8** (−54 %) |
| children per CPU core at 70 % busy | 155 | **177** |

CPU per child moved less than the per-route numbers because the child's minute is dominated by
the AI routes (lesson answers, chat), which spend 80–126 ms of **our** CPU per call — about
3–4 ms per outbound HTTP call in Python's HTTP stack, times ~10 database calls + 1 model call.
That is the next lever (section 6, items 5–6).

### 3d. Cores and memory, measured

| | 1 core, 1 worker | 2 cores, 2 workers |
|---|---|---|
| `kid-get` peak | 222 req/s | **349 req/s (+58 %)** |
| `check-set` peak | 194 req/s | **277 req/s (+43 %)** |
| memory (RSS) | 178 MB | 348 MB (≈170 MB per worker) |

The 2-core figure shares its two cores with the load generator, the fakes and production, so on
a machine with spare cores the gain per core is higher.

---

## 4. What each machine would hold (after the changes, CPU-bound)

One web worker per core, one core left for the media worker, nginx and the OS; ~194 MB per worker.
Prices: DigitalOcean price page, 2026-09-25 (billed per second).

| droplet | vCPU / RAM | $/month | web workers | children at once | DB calls/s at that load |
|---|---|---|---|---|---|
| s-2vcpu-2gb (today) | 2 / 2 GB | $18 | 1 | **~176** | 37 |
| s-2vcpu-4gb | 2 / 4 GB | $24 | 1 | ~176 (room for a 2nd worker: ~350) | 37 |
| s-4vcpu-8gb | 4 / 8 GB | $48 | 3 | **~530** | 112 |
| c-4 CPU-optimized | 4 / 8 GB | $84 | 3 | ~530 (steadier: dedicated cores) | 112 |
| s-8vcpu-16gb | 8 / 16 GB | $96 | 7 | **~1,240** | 263 |
| c-8 CPU-optimized | 8 / 16 GB | $168 | 7 | ~1,240 (dedicated) | 263 |
| c-16 CPU-optimized | 16 / 32 GB | $336 | 15 | **~2,650** | 563 |

Shared "Basic" cores are cheaper per core but can be throttled by neighbours; CPU-Optimized cores
are dedicated. For a service whose limit is CPU, dedicated cores give predictable latency.

Today's box also runs MongoDB, Docker (the site mirror), the Cursor server and Claude sessions
(~580 MB together), has ~780 MB free and 1 GB already in swap. Production should not share a
machine with development tools.

**100,000 children at once** at today's per-child cost:
- ~**566 busy cores** of web process → ~80 × c-8 droplets (~$13,000/month) — or 3–5x fewer after
  the items in section 6;
- ~**21,000 database calls a second** — Supabase gave ~600–1,000/s on the tier measured
  2026-09-10: needs a much larger compute, read replicas, and far fewer calls per child (edge
  caching, push instead of poll);
- ~2,500–5,000 **model calls a second** — beyond default provider rate limits (OpenRouter TTS was
  20 per minute on a new account) and, at rough token counts (1,500 in / 300 out; gpt-4o-mini for
  lesson answers, gpt-5.6-sol for the main chat), on the order of **$0.20 per child-hour ≈ $20,000
  an hour at 100k**. Re-measure from `ai_calls` before planning on it.

---

## 5. Architecture: should the heavy APIs move to another server?

The tutor has three very different kinds of work:

| kind | examples | CPU | waits on | volume per child |
|---|---|---|---|---|
| **polls and reads** | visuals, audio, active-lesson-state, kid pages | 5–20 ms | database | high (≈4 per minute) |
| **AI routes** | lesson answers, chat, homework, TTS | 80–126 ms | the model, 2–20 s | medium (≈3 per minute) |
| **media generation** | images, intro videos, lesson audio | heavy bursts, ~200 MB | image/TTS models, 1–5 min | per lesson, not per child |

Mixing them on one machine means a burst of one starves the others — measured today: test load
on the same box pushed the live service's p95 from 12 ms to 660 ms.

### Recommended order

**A. Media worker on its own droplet — yes, now.** It already runs as a separate process that
pulls `media_jobs` from the database; moving it needs no code change: same code, same env,
`worker.py` under systemd on a second droplet (s-2vcpu-4gb, $24). Image and video bursts stop
competing with children's requests. Risk: low. Scale it later by adding worker droplets (the
queue already handles several).

**B. Make the web process stateless — required before a second worker or server.**
- `EXAM_SETS` (exam-practice sets) lives in process memory: with 2 workers, 2 servers, or after
  a deploy, a child mid-set gets "practice set expired". Move to a table or Valkey.
- The rate limiter (`_rate_buckets`) is per process: with N processes the limit becomes N×60/min.
  Move to Valkey, or to the load balancer / Cloudflare rules.
- The in-process caches added today are fine per process (short TTLs); a shared Valkey
  ($15/month) makes them shared.

**C. Several web servers behind one name.** How "many servers, one DNS" works:

```
iakids.app  ── Cloudflare (DNS + proxy, TLS, cache, rate rules)
                 │
                 ▼
        DigitalOcean Load Balancer ($12/month per node; 1 node ≈ 10k req/s, 10k connections)
          │  health check GET /  (removes a dead server within seconds)
          ├── web droplet 1   uvicorn --workers <cores-1>
          ├── web droplet 2
          └── web droplet N   ← an Autoscale Pool adds/removes these on CPU
                 │
                 ▼
        Supabase (Postgres + Auth + Storage)     Valkey (shared cache, rate limit, exam sets)
                 ▲
        worker droplet(s): media_jobs
```

One DNS record points at the load balancer (or Cloudflare proxies to it); the droplets behind it
are found by tag, so an **Autoscale Pool** (dynamic: target CPU e.g. 60 %, min/max size) can add
and remove them. Requirements: a snapshot with the systemd units, SSH keys, the app stateless (B).
Account catch: a new DigitalOcean team is **Tier 1 — 3 droplets, Basic plans ≤ $48** — request a
limit increase before planning a pool.

**D. AI routes on their own pool — yes, when the lesson screen grows past one server.** Same code;
the load balancer (or nginx) routes `/api/tutor/(chat|openai-clean-chat|homework-*|lesson)` to
pool B and everything else to pool A. A spike of chat can no longer slow the polls every child
depends on, and each pool is sized for its own shape (AI routes: many slow connections, little
CPU; polls: short, CPU-bound). Not worth it at one server: the split halves each pool's headroom.

**E. Lesson generation out of the request path — yes.** The first open of a never-generated lesson
still holds a request for 70–90 s of model calls. Queue it like media, and let the page poll: no
server holds a 90 s request, and a deploy cannot cut one in half.

**F. Cache what is the same for every child at the edge.** A lesson's content (text, audio list,
visual list) is identical for every child; only progress is personal. Served as a versioned JSON
through Cloudflare, it costs the servers and the database nothing after the first child.

**G. Push instead of poll.** Audio and visuals polls are ~2 of a child's ~6 requests a minute,
mostly while media is generated. Server-Sent Events (one open connection, one message when ready),
or longer backoff, cut that to ~0.

Is it good? A–C are standard, low-risk and reversible, and each has a measured reason above. D–G
are what 100k needs; each removes a multiple, not a percentage. What is **not** a good idea:
buying one very large server — it caps at ~2,650 children (c-16) and is a single point of failure.

---

## 6. To-do list, ranked by what the measurements say it is worth

| # | item | why (measured) | effort |
|---|---|---|---|
| 1 | Review and ship today's changes (request caches, local token check, event-loop fixes) | 2.5–6x req/s on prod reads, −54 % DB calls per child, chat no longer freezes the server | done, needs your OK |
| 2 | Media worker to its own droplet ($24/month) | test load on the shared box slowed the live service 12 → 660 ms p95 | 1 h, no code |
| 3 | Move dev tools (Cursor, Claude, MongoDB, Docker mirror) off the production box | ~580 MB of 2 GB; 1 GB already swapped | ops |
| 4 | `EXAM_SETS` and the rate limiter to Valkey/DB | blocks a second worker or server | half a day |
| 5 | Fewer DB calls per lesson answer (`structured-lesson` 10 → 2–3: one RPC for progress + session + history) | AI routes are the biggest CPU share of a child's minute (126 ms/answer) | 1 day |
| 6 | Async database client for the hot routes (no thread per call) | ~3–4 ms CPU per outbound call in the sync HTTP stack | 2–3 days |
| 7 | Upgrade the web droplet to s-4vcpu-8gb ($48) with 3 workers (after 4) | ~176 → ~530 children | 1 h + restart |
| 8 | Load balancer + 2 web droplets + Autoscale Pool (after 4); raise the DO tier | no single point of failure; add capacity by CPU | 1 day |
| 9 | Lesson generation to the queue | no 70–90 s request | 1–2 days |
| 10 | Lesson content as versioned JSON at the Cloudflare edge | removes most lesson-screen reads from servers and DB | 2–3 days |
| 11 | SSE/backoff instead of 1–1.5 s polling | ~⅓ of a child's requests | 1–2 days |
| 12 | AI routes on their own pool | isolates chat spikes from polls | proxy rule, once 8 exists |
| 13 | Supabase compute upgrade + read replicas; re-measure its ceiling from several machines | 21k DB calls/s at 100k | plan + $ |
| 14 | AI cost and provider limits plan (caching TTS/answers, per-plan quotas, provider rate increases) | ~$0.20 per child-hour estimated: at 100k the bill is the ceiling | business |
| 15 | Retry once on a dropped keep-alive connection to Supabase | "Server disconnected" seen in Storage (2026-09-14) and in today's run | 1 h |
| 16 | Trim per-request trace logging on hot routes | ~3 % of CPU in the log prefixer | 1 h |

---

## 7. DigitalOcean: API, MCP, autoscaling

- **MCP**: official, `claude mcp add --transport http digitalocean-droplets https://droplets.mcp.digitalocean.com/mcp`
  (OAuth), or local `npx @digitalocean/mcp --services droplets,networking,insights,accounts` with a
  token. It can list/resize droplets, manage load balancers, alert policies, balance and invoices.
  It has **no tool for CPU/memory time series or autoscale pools** — use the API for those.
- **API/doctl**: a read-only token (`droplet:read monitoring:read billing:read`) reads metrics
  (`/v2/monitoring/metrics/droplet/cpu?host_id=…`, needs the do-agent on the droplet). Resizing
  powers the droplet off (downtime); a CPU/RAM-only resize can be undone, a disk resize cannot.
- **Autoscaling**: yes — Droplet Autoscale Pools (target CPU/memory, min/max, cooldown) behind a
  Load Balancer; App Platform (request-based autoscaling, Dockerfile) is the lowest-ops path; DOKS
  only when there are many services.

---

## 8. What shipping would do

- **Files**: `backend-ai-tutor-he/main.py` (+70/−16), new `backend-ai-tutor-he/request_cache.py`,
  `tools/prompt_gate.py` (performance checks + token tests), new `performance/` folder.
- **Production effect after `tools/deploy_tutor.sh`**: logins verified locally (logout no longer
  instant: up to the token's remaining life); child, subscription and curriculum rows up to
  60 s / 5 min stale; three routes stop blocking the server. No database migration, no new
  dependency (PyJWT and cryptography are already installed), no frontend change.
- **Gate**: `tools/prompt_gate.py --all` passes, with the new checks negative-tested (a route
  without a performance test, a blocking call in an async route, a database-call budget, removed
  cache wiring, an expired / forged / wrong-audience / legacy token, a syntax error in `main.py`).
