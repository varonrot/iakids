# Moving the UI off the database

Decision, 2026-09-17: **the UI talks to the backend and nothing else.** No page, script or
game opens a connection to Supabase, Firebase or any other data store.

Why, in one paragraph. Code that reaches the browser cannot be hidden; minifying buys hours,
not safety. What can be hidden is the data layer. As long as a page calls `sb.from("kids_profiles")`,
the table name, the column list and the relationships sit in the request URL and the JSON
response, visible in the network tab whatever the JavaScript looks like. Stop the browser
talking to the database and all of that disappears, row level security stops being the only
line of defence, and renaming a table stops being a frontend change.

## Where it stands

Measured 178 direct database calls in 53 files on 2026-09-17. That first count only
looked at part of the site; scanning every folder that serves a page put the real
figure at **230**. Four screens have shipped since (`he/tasks`, `he/add-subject`,
`he/parent-panel`, and the games SDK), and the gate holds the number as a ratchet that
can only go down.

| table | calls | files | operations | notes |
|---|---|---|---|---|
| `kids_profiles` | 69 | 46 | select×54, insert×9, update×6 | the crown jewel: names, ages, gender, interests. Most calls come from one helper in games/game-sdk.js, so they collapse into a single endpoint. |
| `learning_lessons` | 13 | 3 | select×13 |  |
| `kid_custom_subjects` | 11 | 3 | select×10, update×1 |  |
| `kid_unit_lesson_progress` | 8 | 4 | select×8 |  |
| `lesson_units_content` | 8 | 4 | select×8 | answer key already stripped from responses and the column revoked. |
| `kid_lesson_progress` | 8 | 2 | select×8 |  |
| `kid_custom_lessons` | 8 | 1 | select×7, update×1 |  |
| `support_messages` | 7 | 3 | insert×5, select×2 |  |
| `support_tickets` | 6 | 3 | insert×3, select×2, update×1 |  |
| `homework_sessions` | 6 | 1 | select×6 |  |
| `kid_tasks` | 5 | 2 | select×2, update×1, delete×1, insert×1 |  |
| `subscriptions` | 5 | 5 | insert×4, select×1 | an anonymous INSERT here was possible until the 2026-09-10 audit. |
| `kid_game_sessions` | 4 | 3 | select×2, insert×1, update×1 |  |
| `homework_capture_sessions` | 3 | 1 | insert×1, select×1, update×1 |  |
| `kid_question_answers` | 2 | 1 | select×1, insert×1 |  |
| `game_wins` | 2 | 1 | insert×1, select×1 | does not exist in the database — this call has always failed. |
| `tutor_sessions` | 2 | 2 | select×2 |  |
| `kid_lesson_history` | 2 | 2 | select×2 | every message a child has written. |
| `learning_coach_sessions` | 2 | 2 | select×2 |  |
| `kid_custom_units` | 2 | 1 | select×2 |  |
| `games_catalog` | 1 | 1 | select×1 |  |
| `game_questions` | 1 | 1 | upsert×1 |  |
| `game_achievements` | 1 | 1 | insert×1 | does not exist in the database — this call has always failed. |
| `usage_summary` | 1 | 1 | select×1 |  |
| `kid_custom_curriculums` | 1 | 1 | select×1 |  |

## Order of work

Each stage ends the same way: the last browser caller of those tables is gone, a migration
revokes their grants, and a gate rule keeps them closed. Nothing is revoked while a page
still needs it.

1. **Kid profile.** One endpoint for read and update behind a shared `assets/js/iakids-api.js`,
   and one call site inside `games/game-sdk.js` that the ~24 game pages already share.
   Removes the widest exposure for the least code.
2. **Progress and lessons.** The workspace, the parent panel and `frontend-v2`:
   `kid_unit_lesson_progress`, `kid_lesson_progress`, `kid_lesson_history`, `learning_lessons`,
   `lesson_units_content`. Largest stage; the tutor backend already owns most of this data.
3. **Games.** `games_catalog`, `game_questions`, `kid_game_sessions`, `kid_question_answers`,
   plus deleting the two calls to tables that do not exist.
4. **Custom subjects.** `kid_custom_*`, the add-subject flow.
5. **Support, subscriptions, admin, homework.** Lowest traffic, and the admin pages already
   have a backend to ask (`/api/admin/whoami`, added 2026-09-17).

## Removed rather than moved

- **`IAKidsCloud`** (leaderboard and achievements) wrote to `game_wins` and
  `game_achievements`, neither of which exists in the database, so every write had
  always failed silently. Nothing read them: `recordAchievement` and `topWins` have no
  callers anywhere and no leaderboard is drawn. The tables were not created, because the
  design keyed rows on an email the browser supplied — its own comment admitted that
  could not be verified — and because the UI no longer talks to the database at all. If
  a leaderboard is ever wanted it is a backend endpoint scoring against the signed-in
  account. The methods remain as no-ops so call sites keep working.

## Rules while this is in progress

- Never add a new `.from(...)` call to a browser file. Add an endpoint.
- A table keeps its grant until its last browser caller is gone, then loses it in the same commit.
- Every endpoint authorises server-side; the browser being 'ours' proves nothing.
- Responses carry only the fields the screen draws, never a row as the table stores it.
