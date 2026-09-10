# How many children can play at once

Measured 2026-09-10 with `tools/loadtest.py`, from this box.

**Read every number here as a floor.** The load generator is a 2-core DigitalOcean
droplet on one uplink, and its CPU idle dropped to 27% during a run — so several of
these ceilings are the generator's, not the service's. Where that is the case it is
said below. To find the real ceiling, run the same tool from a bigger machine, or
from several at once.

---

## The shape of the system decides the answer

There are two completely different capacity questions here, because there are two
completely different paths through the product:

| what a child is doing | what it touches | what limits it |
|---|---|---|
| **playing a game** | Cloudflare (static files) + Supabase | Supabase, and it is a long way off |
| **using the tutor / workspace** | Render → OpenAI / Gemini | the model call, and it is close |

The games never call the Render backends at all. The only line in `game-sdk.js` that
does is the TTS fallback, and that fires only on a device with no Hebrew voice.

---

## Playing a game

**One child costs about 0.14 Supabase requests a second.** A ten-question game over
roughly four minutes makes 34 calls in total:

| calls | what |
|---|---|
| 1 | look the game up in `games_catalog` |
| 1 | open a row in `kid_game_sessions` |
| 1 | read the keys this child has already answered |
| 10 | add each generated question to the shared bank |
| 10 | record each answer |
| 10 | bump the question's counters |
| 1 | close the session row |

The four files the page itself needs — the HTML and the three shared files — are
served by Cloudflare from cache. They cost the origin nothing.

**Measured:** Supabase reads ran clean to 32 concurrent (90 requests/s, p95 0.49s)
and started queueing at 64 (p95 3.0s, still no errors).

At 90 requests a second and 0.14 per child, that is **roughly 600 children playing at
the same time** — and the measurement was generator-bound, so the true figure is
higher. Static page loads measured 127 a second, also generator-bound; Cloudflare
serves those and is not a meaningful constraint at this scale.

**What would actually break first:** not throughput but the write pattern. Every
answer writes three rows. At 600 concurrent players that is ~250 writes a second into
`kid_question_answers` and `game_questions`, which is where a Supabase plan's limits
and the connection pool start to matter well before the HTTP layer does.

---

## The tutor and the workspace

This is the side with a real ceiling, and it was **not** load-tested: every one of
those endpoints calls a language model, each call is billed, and the backends have no
rate limit (`tools/loadtest.py` refuses them for that reason). What can be said comes
from reading the code rather than from hammering it.

**Every route in `backend-ai-tutor-he/main.py` is a plain `def`, not `async def`** —
all 19 of them, and 2 of the 4 in `backend/main.py`. FastAPI runs a plain `def` in a
worker threadpool, 40 threads by default. Each request holds one of those threads for
the entire model call — seconds, not milliseconds.

So the ceiling is roughly:

```
40 threads ÷ ~4 seconds per model call ≈ 10 requests a second
```

and past 40 in flight, requests queue rather than fail. A child waiting on a lesson
that queues behind 40 others sees a page that has simply stopped.

Both services answered a route with no model and no database at 32 concurrent without
strain (~62 requests/s each), so FastAPI and Render are not the problem. The model
call is.

**What to do about it, in order of value:**

1. **Rate limit per user**, which the security review already called for. Without it
   one browser tab in a loop can take the whole threadpool.
2. **Make the model calls `async def`** and await the client's async methods. A route
   that awaits instead of blocking gives the thread back while the model thinks, and
   the ceiling stops being the threadpool.
3. **Raise Render's worker count** once the routes no longer block, or the extra
   workers just multiply the memory.
4. **Cache what repeats.** A generated lesson is stored already; the TTS cache added
   in `IAKidsSpeech` is the same idea client-side.

---

## Running it yourself

```bash
python3 tools/loadtest.py --list
python3 tools/loadtest.py game               # a child opening a game
python3 tools/loadtest.py supabase --max 128 --yes
```

It doubles the concurrency each step and stops at the first step that stops keeping
up, so the answer is a number rather than a graph. Every scenario is read-only, so a
run cannot damage a child's data, and anything that would call a model is refused.

## One thing found while measuring

`https://iakids-backend.onrender.com/` answers **404**, but `backend/main.py` has had
a health route at `/` since commit `320fa583`. **The deployed build is older than the
repository.** Worth checking what else that service is missing before trusting it.

---

## The one-page version

`tools/capacity_pdf.py` draws all of this as a three-page PDF — the measured curves,
what each Render tier buys, and the architecture that removes the ceiling:

```bash
backend/.venv/bin/python tools/capacity_pdf.py            # -> tools/iakids-capacity.pdf
```

It needs `reportlab` and `python-bidi` (both in `backend/.venv`). The bidi part is
not optional: reportlab draws glyphs in the order it is handed them, so Hebrew has to
be reordered before it is drawn or every line comes out backwards.

---

## After the bank migration (2026-09-10, evening)

Measured on the real play path — a signed-in child calling `game_next_questions`
against the 106k-row bank through the new partial index, with the table itself closed
to direct reads:

| at once | calls/s | p95 |
|---|---|---|
| 32 | 68.5 | 0.48 s |
| 64 | 40.4 | 1.73 s |
| 128 | 69.2 | 1.73 s |

**128 concurrent, no errors, still under the 2-second line** — the earlier read
scenario had crossed it at 64. The dip at 64 and the flat line after it are this
2-core generator again; the ceiling is above what this box can produce.

A session now makes 24 calls instead of 34 (one `game_record_answer` per question
instead of an insert plus an rpc), 0.10 requests/s per child. Reads measured at
~70 calls/s put that at **roughly 700 children playing at once**, as a floor. Writes
were not hammered — this is production — so the write ceiling remains an estimate.
