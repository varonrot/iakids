# Performance run 20260925-063742-after-prod

db=prod, fake model delay x1.0, fake DB latency 100.0 ms, box 2 CPUs / 1967 MB, tutor copy idle RSS 137 MB

| route | kind | status | 1 req ms | CPU ms/req | DB calls warm (cold) | DB writes | model calls | prod-safe | max OK conc | req/s there | what broke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| units | read | 200 | 149 | 11.01 | 1 (3) | 0 | 0 | yes | 8 | 52.9 | p95 1235 > 800 ms (3x one-user p50 122) |
| active-lesson-state | read | 200 | 152 | 14.42 | 1 (2) | 0 | 0 | yes | 8 | 53.32 | p95 1813 > 800 ms (3x one-user p50 120) |
| audio | media | 200 | 227 | 19.86 | 1 (2) | 0 | 0 | yes | 8 | 37.96 | p95 1122 > 800 ms (3x one-user p50 132) |
| check-set | read | 200 | 6 | 6.29 | 0 (0) | 0 | 0 | yes | 32 | 140.81 | not reached |
| kid-lessons | read | 200 | 123 | 10.43 | 1 (1) | 0 | 0 | yes | 8 | 52.99 | p95 1677 > 1000 ms (3x one-user p50 118) |
| kid-get | read | 200 | 7 | 5.32 | 0 (0) | 0 | 0 | yes | 32 | 182.89 | not reached |

## Children at once (this box)

- **per_child_cpu_ms_per_min**: 24.0
- **per_child_db_calls_per_min**: 1.2
- **children_per_process_cpu_bound**: 1750
- **children_per_box_if_one_process_per_core**: 3500
- **db_calls_per_sec_at_1000_children**: 20.8
- **mix_routes_not_measured**: ['unit-lesson', 'lesson-intro', 'visuals', 'hero-image', 'structured-lesson', 'openai-clean-chat', 'tts']
