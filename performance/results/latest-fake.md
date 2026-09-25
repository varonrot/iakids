# Performance run 20260925-083842-english-turn-fake

db=fake, fake model delay x1.0, fake DB latency 100.0 ms, box 2 CPUs / 1967 MB, tutor copy idle RSS 137 MB

| route | kind | status | 1 req ms | CPU ms/req | DB calls warm (cold) | DB writes | model calls | prod-safe | max OK conc | req/s there | what broke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| english-allowance | read | 200 | 112 | 12.879999999999999 | 1 (4) | 0 | 0 | yes | 32 | 82.61 | p95 1979 > 800 ms (3x one-user p50 113) |
| english-start | model | 200 | 5066 | 83.08 | 4 (4) | 2 | 1 | no | 64 | 7.98 | event loop blocked (lag p95 1282 ms) |
| english-turn | model | 200 | 3782 | 82.56 | 3 (3) | 1 | 1 | no | 64 | 8.06 | event loop blocked (lag p95 1880 ms) |

## Children at once (this box)

- **per_child_cpu_ms_per_min**: 0.0
- **per_child_db_calls_per_min**: 0.0
- **children_per_process_cpu_bound**: None
- **children_per_box_if_one_process_per_core**: None
- **db_calls_per_sec_at_1000_children**: 0.0
- **mix_routes_not_measured**: ['active-lesson-state', 'unit-lesson', 'lesson-intro', 'visuals', 'audio', 'hero-image', 'structured-lesson', 'openai-clean-chat', 'tts', 'kid-get']
