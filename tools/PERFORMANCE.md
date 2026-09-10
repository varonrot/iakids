# Where the performance actually goes

Measured 2026-09-10. Every number here came from a measurement or from counting rows,
not from reading the code and guessing.

Ordered by what it would buy, not by where it is in the stack.

---

## 1. Every child downloads a dictionary they do not use

`games/nikud.js` is **155 KB raw, 37 KB over the wire, on every game page**. The
median game renders **44** of its 4,237 words — **one percent**.

| game | words it renders | its own file would be | saving |
|---|---|---|---|
| story-fill | 606 | 19.8 KB | 87% |
| idioms | 476 | 15.5 KB | 90% |
| roots | 233 | 7.2 KB | 95% |
| *the median game* | 44 | ~1.5 KB | 99% |

**Fix:** split it. `nikud-check.py` already knows exactly which words each game
renders — that is how R4 works — so the generator can emit one small file per game
plus a shared core for the SDK's own labels. A game would load 1–20 KB instead of
155 KB, and the split costs nothing to maintain because the word list is derived,
not written.

This is the single biggest thing on the page, and it is self-inflicted: the
dictionary was added whole because that was the simplest thing that worked.

## 2. JavaScript is served gzip, not brotli

| file | raw | wire | encoding |
|---|---|---|---|
| `game-sdk.js` | 92 KB | 30 KB | **gzip** |
| `nikud.js` | 155 KB | 37 KB | **gzip** |
| `dictation/index.html` | 30 KB | 11 KB | brotli |

The HTML gets brotli; the JavaScript does not. Brotli is typically 15–20% better than
gzip on text this size, so this is roughly **10 KB per cold game load** for a
Cloudflare setting, not a code change. Worth checking Speed → Optimization.

## 3. The hot query sorts the whole bank to return twenty rows

`game_next_questions` ends with:

```sql
order by q.times_asked asc, random()
limit p_limit;
```

`random()` in an `ORDER BY` cannot use an index, so Postgres reads and sorts **every
matching row** before taking twenty:

| game | rows in the bank | rows sorted for one call at level 1 |
|---|---|---|
| true-false-math | 3,295 | **1,237** |
| compare-numbers | 2,952 | 216 |
| capitals | 2,341 | 56 |

It grows with the bank, and the bank grows with play — it is 106,096 rows today.

The index is `(game_code, level)`. The query also filters on
`verified or source in ('seed','authored')`, which the index does not cover, so those
rows are fetched and then discarded.

**Fix, in order:**

```sql
-- 1. index the set that is actually served
create index if not exists game_questions_served_idx
    on public.game_questions (game_code, level, times_asked)
    where verified or source in ('seed', 'authored');

-- 2. stop sorting the whole partition: take the least-asked window, shuffle inside it
--    (the caller only needs twenty unseen questions, not the globally rarest twenty)
```

A window of a few hundred by `times_asked`, shuffled in the SDK rather than in
Postgres, gives the same behaviour without the sort.

## 4. The read-aloud button watches every DOM change

`IAKidsSpeech.mountReader()` observes the whole card with `subtree` **and**
`characterData`, and each mutation runs `currentQuestion()`, which is a
`querySelectorAll` over ten selectors. In a drag game the DOM changes on every
pointer move, so that runs hundreds of times a second to answer a question that
changes once a round.

**Fix:** coalesce with `requestAnimationFrame`, and drop `characterData` — a new
question always replaces a node.

## 5. The tutor holds a thread for the whole model call

All 19 routes in `backend-ai-tutor-he/main.py` are a plain `def`. FastAPI runs those
in a 40-thread pool, and each request keeps a thread for the entire model call.
About **10 requests a second, then queueing**. This is covered in `CAPACITY.md`;
it is repeated here because it is the largest single ceiling in the product.

`get_or_generate_unit_lesson` also makes **six sequential Supabase round trips** in
one request. From Render each is tens of milliseconds; they do not depend on each
other and could be issued together.

## 6. What is already fine

Worth writing down so nobody "optimises" it:

- **Prompts are read once at import**, not per request.
- **`IAKidsNikud.text()` costs 18 µs** on an eleven-word sentence, `of()` 0.9 µs.
  The dictionary's runtime cost is nothing; only its download size matters.
- **The N+1 loop** at `main.py:2481` updates one row per in-progress lesson, of which
  a child has none or one.
- **Static delivery**: Cloudflare answered 127 page-loads a second and did not
  strain; the limit measured there was the load generator.

---

## Supabase: what an upgrade buys, and what it does not

**The database is small.** One table has 106,096 rows; everything else is in the
hundreds or thousands. Storage is not the constraint and a bigger plan does not buy
anything for it.

What actually decides how many children play at once is **how many requests
PostgREST can answer in parallel**, which follows the compute add-on rather than the
plan tier. That is the knob to turn — *after* the two free things below.

**Do these first, because they cost nothing and buy more than a compute step:**

1. **Fix `game_next_questions`** (§3). The current query gets slower as the bank
   grows, so an upgrade buys time rather than a fix.
2. **Send fewer requests.** A game makes 34 calls per session, of which **30 are one
   per question** — a bank upsert, an answer insert, and a counter RPC per answer.
   Batching each answer's three writes into one RPC turns 30 calls into 10 and cuts
   the write load by two thirds. At 600 concurrent players that is the difference
   between ~250 and ~85 writes a second.

**Then, if it is still tight:** move the compute size up one step and re-run
`tools/loadtest.py supabase --max 256 --yes` to see what it bought. Measure before
and after — the point of the tool is that the answer is a number.

**What no Supabase plan fixes:** the tutor. It never touches Supabase for the slow
part; it waits on OpenAI and Gemini.

---

## If only three things get done

1. **Split `nikud.js` per game.** 37 KB → 1–5 KB for most games, on every load.
2. **Index and de-sort `game_next_questions`.** It is the only query that gets worse
   as the product succeeds.
3. **Make the tutor routes `async`.** It is the difference between 40 concurrent
   users and as many as the model provider allows.

The first two are hours. The third is a day and is worth more than any hardware.
