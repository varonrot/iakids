# performance/ — how many children the tutor API holds

Everything here tests `backend-ai-tutor-he` (the tutor API) on this box, without touching the
live service on `:8011` and without spending a cent on models.

| file | what it is |
|---|---|
| `routes.py` | every route of `main.py`: how to call it, its kind, its latency budget, its database-call budget (`db_max`), and the per-child request mix |
| `run.py` | starts a fake database, fake models and **its own copy** of the tutor, profiles every route, then ramps each one until it stops keeping up |
| `fake_supabase.py` | stand-in for Supabase (PostgREST, Auth with real ES256 tokens + JWKS, Storage), 100 ms per call; `--proxy URL` counts calls to the real one instead |
| `fake_models.py` | stand-in for OpenRouter/OpenAI (chat, structured outputs, TTS, STT) at production median delays; `--scale` speeds it up |
| `make_fixtures.py` | copies one ready lesson + curriculum rows from production (read-only) into `fixtures/seed.json`; never a child's data |
| `prod_identity.py` | throwaway test parent + child for the production pass, removed at the end (`--cleanup` removes leftovers) |
| `static_checks.py` | what the gate checks (see below) |
| `stop_test_servers.sh` | stops the fake servers and the tutor copy by port (never `:8011`) |
| `results/` | `latest-fake.json` (the gate's reference), one `.json` + `.md` per run; `results/logs/` is not committed |

## Run it

```bash
backend/.venv/bin/python performance/run.py --profile-only          # every route once: DB calls, writes, model calls (~2 min)
backend/.venv/bin/python performance/run.py                         # + ramp every rampable route (~25 min)
backend/.venv/bin/python performance/run.py --only tutor-chat,visuals
backend/.venv/bin/python performance/run.py --scale 0.1             # models 10x faster: the server's own ceiling
backend/.venv/bin/python performance/run.py --tutor-dir <worktree>/backend-ai-tutor-he --label before   # another checkout, for before/after
backend/.venv/bin/python performance/run.py --db prod --max-conc 32 # REAL prod database, prod-safe routes only; asks first
```

`--db prod` only runs routes the fake pass proved make **no writes and no model calls**
(`prod_safe` in `latest-fake.json`), turns off cost and metrics rows, watches the live service's
latency every second and stops the whole run if it passes 1 s. Run it at a quiet hour, and only
with the user's OK: it is real load on the production database.

## What a ramp step reports

requests/s, p50/p95/p99, errors, the copy's CPU% and **CPU ms per request**, its RSS, and the
**event-loop lag** (latency of `GET /` measured alongside: a route that blocks the loop shows up
there before anywhere else). A step "breaks" on errors > 1 %, p95 over 3x the one-user p50 (and
over the route's budget), RSS over `--rss-limit`, or loop lag p95 over 500 ms.

Read every number as a floor: the load generator, the fakes and the copy share this box's two
cores with production.

## The gate (`tools/prompt_gate.py`, `performance_checks`)

Runs on every commit that stages `main.py`, and in `--all`:

1. every `@app` route in `main.py` has an entry in `routes.py`;
2. no `async def` route calls the database, a model client or `sleep` on the event loop
   (one process serves every child: a blocked loop freezes all of them);
3. every entry has a known kind and a latency budget;
4. every entry has a result in `results/latest-fake.json`, it is not a 5xx, and its warm
   database calls are within `db_max`;
5. the request caches stay wired (local token check, child cache, cache drop on kid update,
   media-enqueue memo), plus unit tests of the token check (`request_cache_tests`).

Adding a route: add it to `routes.py`, run `run.py --profile-only --only <name>`, set `db_max`
to what it measured, commit the updated `results/latest-fake.json` with it.
