# Before / after, route by route

before: `20260925-060414-before-fake`  |  after: `20260925-061442-after-fake`  |  fake DB 100.0 ms per call, fake models at x1.0 of production median delays

| route | kind | max children at once (before → after) | req/s there | p50 / p95 ms there | CPU ms per request | RSS peak MB | DB calls per request (warm) | what stopped it (after) |
|---|---|---|---|---|---|---|---|---|
| health | health | 8 → **8** | 340.8 → **398.8** | 20/150 → 18/126 | 2.8 → **2.6** | 147 → 148 | 0 → **0** | p95 280 > 200 ms (3x one-user p50 3) |
| active-lesson-state | read | 32 → **8** | 16.2 → **12.7** | 1,680/2,526 → 596/771 | 49.3 → **34.4** | 179 → 169 | 3 → **1** | p95 1846 > 1619 ms (3x one-user p50 540) |
| unit-lesson | media | 1 → **32** | 0.7 → **25.7** | 1,090/2,580 → 1,190/1,497 | 72.5 → **41.9** | 181 → 179 | 10 → **3** | p95 4250 > 1500 ms (3x one-user p50 342) |
| hero-image | media | 8 → **32** | 16.1 → **40.8** | 474/570 → 714/1,010 | 36.0 → **22.5** | 180 → 179 | 4 → **1** | p95 2187 > 1500 ms (3x one-user p50 122), event loop blocked (lag p95 631 ms) |
| visuals | read | 8 → **8** | 15.7 → **37.5** | 492/638 → 205/434 | 37.7 → **20.4** | 180 → 179 | 4 → **1** | p95 1004 > 800 ms (3x one-user p50 121) |
| audio | media | 8 → **8** | 14.4 → **39.3** | 508/738 → 204/290 | 33.6 → **20.5** | 180 → 177 | 4 → **1** | p95 965 > 800 ms (3x one-user p50 119), event loop blocked (lag p95 516 ms) |
| structured-lesson | model | 8 → **32** | 1.1 → **4.2** | 6,700/8,330 → 5,960/7,777 | 108.7 → **125.9** | 184 → 194 | 13 → **10** | event loop blocked (lag p95 731 ms) |
| tutor-chat | model | 32 → **32** | 4.3 → **4.5** | 5,820/7,599 → 5,980/7,911 | 101.6 → **92.5** | 192 → 192 | 8 → **6** | event loop blocked (lag p95 571 ms) |
| openai-clean-chat | model | 32 → **256** | 0.0 → **0.0** | 0/0 → 0/0 | 60.0 → **80.0** | 191 → 194 | 2 → **0** | not reached |
| tts | model | 64 → **32** | 42.3 → **115.8** | 1,380/2,253 → 246/538 | 21.9 → **9.2** | 193 → 190 | 2 → **0** | p95 9620 > 8000 ms (3x one-user p50 9) |
| check-set | read | 8 → **32** | 35.1 → **160.2** | 222/265 → 189/354 | 14.3 → **6.3** | 193 → 190 | 2 → **0** | p95 899 > 800 ms (3x one-user p50 7) |
| kid-get | read | 8 → **32** | 34.7 → **181.3** | 225/266 → 163/388 | 13.8 → **5.2** | 191 → 189 | 2 → **0** | event loop blocked (lag p95 576 ms) |

# One child in a lesson

| | before | after |
|---|---|---|
| CPU per child per minute | 270 ms | **238 ms** |
| database calls per child per minute | 27.7 | **12.8** |
| children per CPU core (70 % busy) | 155 | **177** |

# What each machine would hold (after the changes)

One uvicorn worker per core, one core kept for the media worker, nginx and the OS. Memory per worker ≈ 194 MB peak (measured) + the media worker's ~200 MB (2026-09-14). CPU-bound figure; the database limit is separate (below).

| droplet | vCPU / RAM | $/month | web workers | RAM needed | children at once (CPU) | DB calls/s at that load |
|---|---|---|---|---|---|---|
| s-2vcpu-2gb (today) | 2 / 2 GB | $18 | 1 | 0.7 GB | **176** | 37 |
| s-2vcpu-4gb | 2 / 4 GB | $24 | 1 | 0.7 GB | **176** | 37 |
| s-4vcpu-8gb | 4 / 8 GB | $48 | 3 | 1.1 GB | **529** | 112 |
| c-4 (CPU-optimized) | 4 / 8 GB | $84 | 3 | 1.1 GB | **529** | 112 |
| s-8vcpu-16gb | 8 / 16 GB | $96 | 7 | 1.8 GB | **1,236** | 263 |
| c-8 (CPU-optimized) | 8 / 16 GB | $168 | 7 | 1.8 GB | **1,236** | 263 |
| c-16 (CPU-optimized) | 16 / 32 GB | $336 | 15 | 3.3 GB | **2,649** | 563 |

100,000 children at once would need about **566 busy cores** of web process and **21,250 database calls a second** at today's per-child call count.


# Production database, before → after (same 6 read-only routes, same box, 2026-09-25)

| route | 1 user p50 ms | req/s at 8 users | p95 ms at 8 users | req/s at 32 users | CPU ms/request | DB calls/request |
|---|---|---|---|---|---|---|
| units | 352 → **122** | 19.2 → **52.9** | 798 → **257** | 20.5 → **60.0** | 17.1 → **11.0** | 3 → **1** |
| active-lesson-state | 363 → **120** | 18.0 → **53.3** | 1,463 → **418** | - → **43.5** | 23.3 → **14.4** | 3 → **1** |
| audio | 487 → **132** | 15.1 → **38.0** | 722 → **309** | 12.3 → **43.0** | 28.6 → **19.9** | 4 → **1** |
| check-set | 234 → **5** | 30.6 → **142.2** | 363 → **230** | 29.0 → **140.8** | 13.6 → **6.3** | 2 → **0** |
| kid-lessons | 347 → **118** | 21.1 → **53.0** | 514 → **274** | 19.4 → **51.2** | 15.5 → **10.4** | 3 → **1** |
| kid-get | 222 → **5** | 26.8 → **170.0** | 529 → **98** | 27.4 → **182.9** | 14.4 → **5.3** | 2 → **0** |
