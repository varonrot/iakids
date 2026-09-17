# Performance and cost — measured, not estimated

Everything here comes from production: the `ai_calls` table, the `ai_costs_per_lesson`
view and the `STAGE SUMMARY` lines in the service log. Where a number comes from a
benchmark instead, it says so and gives the sample size. Last measured **2026-09-17**.

Re-measure with the queries at the bottom rather than trusting this page after a change.

---

## 1. Where the child's time goes

A new lesson, from the click to the first word on screen. Three real generations:

| stage | lesson 153 | lesson 152 | lesson 3 |
|---|---|---|---|
| part 1 teacher | 9.4 s | 9.2 s | 14.2 s |
| part 2 teacher | 6.4 s | 9.9 s | 22.6 s |
| part 1 director | 9.9 s | 11.2 s | 11.4 s |
| part 2 director | 6.5 s | 6.6 s | 15.3 s |
| **visual director** | **13.8 s** | **36.0 s** | **45.8 s** |
| queue the media job | 0.1 s | 0.1 s | 0.1 s |
| **total before the child sees text** | **37.3 s** | **62.8 s** | **99.1 s** |

The teacher and director calls for the two parts already run in parallel. **The Visual
Director is the single largest block and the most variable**, and the child waits
through all of it. It is one call with 2000–3300 output tokens.

After the text appears, the media job runs in the background: images at about 4.5 s
each, voice lines at about 6.4 s each.

## 2. Where the money goes

Fifteen lessons that completed a full generation:

| | median | min | max |
|---|---|---|---|
| media | $0.799 | $0.480 | $2.898 |
| text | $0.060 | $0.025 | $0.166 |
| **total per lesson** | **$0.874** | $0.572 | $3.064 |

**Media is about 95% of a lesson**, and inside media it is almost entirely images:

- images per lesson: median **21** (range 11 to 148)
- cost per image: **$0.0336**
- images at the median: **$0.72** of the $0.87

Text generation, the part that takes the longest, costs about seven cents.

> The $3.06 outlier is lesson 12, which was regenerated several times during the
> debugging of 2026-09-16. A lesson generated once costs around $0.87.

## 3. Every model in production

From the last 1000 recorded calls. `med out` is median output tokens.

| purpose | provider | model | calls | med latency | med out | cost |
|---|---|---|---|---|---|---|
| media | gemini | gemini-3.1-flash-lite-image | 277 | 4.8 s | 1512 | $8.77 |
| media | openrouter | gemini-3.1-flash-tts-preview | 262 | 6.4 s | — | $1.29 |
| image check | gemini | gemini-3.1-flash-lite | 160 | 1.7 s | 11 | ~$0 |
| media | gemini | gemini-3.1-flash-lite-image | 50 | 4.7 s | 1507 | $1.68 |
| tts | openrouter | gemini-3.1-flash-tts-preview | 43 | 7.1 s | — | $0.23 |
| lesson text | openai | gpt-5.6-sol | 32 | 15.7 s | 465 | $0.66 |
| lesson text | openrouter | gpt-5.6-sol | 25 | 17.0 s | 542 | $0.21 |
| visual director | openai | gpt-4o-mini | 11 | 17.7 s | 2601 | $0.02 |
| visual director | openrouter | gpt-4o-mini | 7 | **37.2 s** | 3266 | $0.02 |
| live voice | openrouter | gemini-3.1-flash-tts-preview | 36 | 3.0 s | — | $0.12 |

Two things stand out. The image model is where the money is. And the same Visual
Director call is twice as slow through OpenRouter as direct.

## 4. Provider comparison, benchmarked

Same prompt, same server, same SDK (`openai` 3.10.0), runs interleaved, three each.
The workload is the real Visual Director prompt producing the real 14-item plan.

| route | run 1 | run 2 | run 3 | median |
|---|---|---|---|---|
| gpt-4o-mini direct | 17.9 s | 22.5 s | 15.5 s | **17.9 s** |
| gpt-4o-mini via OpenRouter | 28.0 s | 31.3 s | 27.7 s | **28.0 s** |
| gemini-3.1-flash-lite direct | 7.7 s | 6.6 s | 7.5 s | **7.5 s** |
| gemini-3.1-flash-lite via OpenRouter | 8.2 s | 7.2 s | 7.3 s | **7.3 s** |

All four produced the same 14 visuals for the same lesson.

Read it carefully, because the two halves say different things:

- **For an OpenAI model, OpenRouter costs about ten seconds.** It is proxying to the
  same provider, so the extra hop buys nothing here.
- **For a Gemini model, OpenRouter costs nothing measurable** — 7.3 s against 7.5 s.

So "OpenRouter is slower" is not a rule, it is a property of this model and this
request shape. Another project measuring the opposite is entirely consistent with
this table. Always re-measure per model.

**And the largest single finding: Gemini flash-lite does the Visual Director's job in
7.5 s instead of 17.9 s direct or 28 s as production runs it today** — a third of the
time, for the same output.

## 5. What is worth changing, in order

1. **Move the Visual Director to `gemini-3.1-flash-lite`.** Saves about 20 s of the
   child's wait on every new lesson, roughly a third of the total. Needs a check that
   the plan quality holds across a few lessons, because the prompt was written against
   gpt-4o-mini. *Not done — this is a recommendation, not a change.*
2. **Direct instead of OpenRouter for the Visual Director** — done on 2026-09-17,
   saves about 10 s. Reversible with `VISUAL_DIRECTOR_PROVIDER=openrouter`. Step 1
   makes this one irrelevant, since Gemini shows no penalty either way.
3. **Fewer images per lesson.** At $0.0336 each and a median of 21, images are 82% of
   a lesson's cost. `VISUAL_REUSE` and the image budget (`VISUAL_NEW_RATIO`,
   `VISUAL_MIN_NEW`) exist for exactly this; `VISUAL_REUSE` is currently off.
   Dropping from 21 to 14 saves about $0.24 a lesson with no change to the text.
4. **Take the Visual Director off the request path entirely.** It only feeds the media
   worker; the child does not need it to start reading. The catch is that the frontend
   gives up on images after 45 s, so the plan arriving later could mean lessons that
   start without pictures. Needs the budget rethought at the same time.

## 6. How to re-measure

Per-lesson cost, media against text:

```sql
select * from public.ai_costs_per_lesson order by cost_usd desc limit 20;
```

Latency and cost by model, from the service:

```python
rows = sb.table('ai_calls').select(
    'provider,model,purpose,output_tokens,latency_ms,cost_usd').limit(1000).execute().data
```

Where the child's time went on a real generation:

```bash
journalctl -u iakids-tutor-web --no-pager | grep 'STAGE SUMMARY' | tail -5
```

Provider A/B for one call — always interleave the runs, never run one provider then the
other, or you are measuring the time of day as much as the provider.
