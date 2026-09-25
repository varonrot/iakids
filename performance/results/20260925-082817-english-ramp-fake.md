# Performance run 20260925-082817-english-ramp-fake

db=fake, fake model delay x1.0, fake DB latency 100.0 ms, box 2 CPUs / 1967 MB, tutor copy idle RSS 138 MB

| route | kind | status | 1 req ms | CPU ms/req | DB calls warm (cold) | DB writes | model calls | prod-safe | max OK conc | req/s there | what broke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| english-allowance | read | 200 | 114 | 12.39 | 1 (4) | 0 | 0 | yes | 32 | 72.23 | p95 2019 > 800 ms (3x one-user p50 112) |
| english-start | model | 200 | 4173 | 83.8 | 4 (4) | 2 | 1 | no | 32 | 4.71 | event loop blocked (lag p95 632 ms) |
| english-turn | model | 200 | 4665 | 19.07 | 3 (3) | 1 | 1 | no | 0 | 0 | errors 100% |
| english-end | write | 200 | 120 | 20.0 | 1 (2) | 0 | 0 | no | - | - | - |
| english-sessions | read | 200 | 121 | 16.28 | 1 (1) | 0 | 0 | yes | 8 | 45.16 | p95 1063 > 1000 ms (3x one-user p50 121) |

## Children at once (this box)

- **per_child_cpu_ms_per_min**: 0.0
- **per_child_db_calls_per_min**: 0.0
- **children_per_process_cpu_bound**: None
- **children_per_box_if_one_process_per_core**: None
- **db_calls_per_sec_at_1000_children**: 0.0
- **mix_routes_not_measured**: ['active-lesson-state', 'unit-lesson', 'lesson-intro', 'visuals', 'audio', 'hero-image', 'structured-lesson', 'openai-clean-chat', 'tts', 'kid-get']
