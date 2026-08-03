# iakids Games — Catalog & Integration Spec

100 educational mini-games for iakids. Static site — each game is a self-contained folder under `/games/<slug>/` with its own `index.html` and its own database (IndexedDB, namespaced per game).

---

## Architecture

```
/games/
  GAMES.md            ← this file
  game-sdk.js         ← shared interface, loaded by every game
  index.html          ← games hub (grid of all games)  [to build]
  <slug>/
    index.html        ← the game itself (self-contained: HTML+CSS+JS)
```

- **No build step, no framework.** Plain HTML/CSS/JS, RTL Hebrew, mobile-first, matches site look (see `/he/index.html` styling).
- **Each game has its own DB**: an IndexedDB database named `iakids_game_<slug>`, created and managed by `game-sdk.js`. Games never touch another game's DB.
- **Launched from the hub or from the workspace via iframe or direct link.** Game reports completion to parent window via `postMessage`.

## Interface contract — every game MUST implement

Each game's `index.html` loads the SDK and follows this lifecycle:

```html
<link rel="stylesheet" href="../game-style.css">
<script src="../game-sdk.js"></script>
<script>
  const game = await IAKidsGame.init('true-false-math');  // slug = folder name

  // during play
  await game.saveProgress({level: 3, streak: 5});         // any JSON, overwrites
  const p = await game.loadProgress();                    // null if none

  // on game over
  await game.saveScore(850, {level: 3, mistakes: 2});     // appends to score history
  const top = await game.getHighScores(10);               // sorted desc
  game.complete(850);                                     // notifies parent window
</script>
```

| Method | Purpose |
|---|---|
| `IAKidsGame.init(slug)` | Opens/creates DB `iakids_game_<slug>`. Returns game handle. |
| `saveScore(score, meta?)` | Append score record `{score, meta, ts}`. |
| `getHighScores(n=10)` | Top n scores, descending. |
| `saveProgress(obj)` / `loadProgress()` | Single saved-state slot (resume). |
| `complete(score)` | `postMessage({type:'iakids-game-complete', slug, score})` to parent — hub/workspace listens for stickers/leaderboard. Also fires confetti + fanfare. |

**Look & feel — shared, free for every game:**

- `game-style.css` — brand palette (orange #ff6a2a), `.game-card`, `.game-btn` (big kid-friendly buttons), `.answer-grid`, `.game-hud`, `.drop-zone`, correct/wrong animations, end screen.
- `IAKidsFX` (in `game-sdk.js`) — feedback helpers:
  - `IAKidsFX.correct(el)` — green pop + happy chime + floating "+10"
  - `IAKidsFX.wrong(el)` — red shake + buzz + vibration
  - `IAKidsFX.celebrate()` — confetti burst + fanfare (auto-called by `complete()`)
  - `IAKidsFX.muted = true` — sound toggle
- Sounds are WebAudio-generated (no audio files). Confetti = canvas-confetti, lazy-loaded from CDN only when celebrating.

**Reference implementation:** `games/demo/index.html` — copy it as the starting point for any new game.

**Extended interface — every game gets these via the SDK (most are automatic):**

| Feature | How | Game's work |
|---|---|---|
| Player name + date on every score | `saveScore` auto-attaches `player` (from wallet) + `ts` | Show `player · date` on end screen |
| No repeated questions | `game.newQuestion(genFn, keyFn)` — persists last 300 asked, resets when pool exhausted | Generate questions through it |
| Adaptive difficulty (always gets harder) | `game.difficulty(start, max)` → `.level`, `.right()`, `.wrong()` | Call right/wrong, read `.level` |
| 📤 Send-to-friend challenge link | `game.shareButton(score, el)` — WhatsApp/native share, score rides in the URL; opening the link auto-shows "beat X!" banner and win/lose check on complete | One line on end screen |
| ⚔️ Tournaments (3 rounds) | Created in `games/champions/`; SDK chains games via `?tournament=<id>`, records rounds, injects next-game button | Nothing |
| 🏆 אלוף האלופים table | `games/champions/index.html` scans all `iakids_game_*` DBs: best score, player, date per game + totals | Nothing |
| Languages (he/en/es/de/pt) | `IAKidsLang.code`, `t({he,en,...})`, `ui('play_again')` — sets `<html lang/dir>` (he=RTL) from `?lang=` or saved pref | Wrap UI strings in `t()`/`ui()`; language-bound content (Hebrew letters, English vocab) stays in its language |
| ⏱️ Question timer (💣 bomb) | `game.timer({style:'bomb'\|'bar', onTimeout})` + `timer.start(IAKidsTimer.secondsFor(diff.level, base))` — time shrinks as level rises (base−2·(level−1), min 3s); last-3s red pulse + ticking, 💥 + boom on timeout | Optional per GAME.md. `start()` each question, `stop()` on answer; timeout counts as a wrong answer |
| 🔢 Rounds picker | Start screen offers 5/10/15 rounds (per-game default in GAME.md); choice persisted via `saveProgress` | Rounds row on start screen; HUD shows `qnum/total` |
| ❓ Help with example | `IAKidsHelp.mount({slug, how, example})` — ❓ button + modal, auto-opens on first visit (localStorage flag) | Provide kid-friendly `how` text + one concrete `example` (HTML) |

**UI requirements per game:** RTL (`<html dir="rtl" lang="he">`), big touch targets (kids), start screen → play → end screen with score + "שחק שוב" button, sounds optional but muted by default toggle.

---

## Catalog

### 🔢 חשבון ומתמטיקה (1–25)

| # | Slug | שם | מכניקה |
|---|---|---|---|
| 1 | true-false-math | אמת/שקר בחשבון | משפט חשבוני (5×4=22), בחירת אמת/שקר נגד השעון |
| 2 | missing-number | השלם את הנעלם | 7+◻=15, בחירה מ-4 אפשרויות |
| 3 | target-bubbles | קליעה למטרה | מספר מטרה, לחיצה על בועה עם התרגיל שיוצר אותו |
| 4 | compare-numbers | גדול, קטן או שווה | השוואת תרגילים/מספרים עם > < = |
| 5 | odd-even-sort | זוגי או אי-זוגי | גרירת מספרים לסל זוגי/אי-זוגי |
| 6 | memory-equations | זיכרון תרגיל-תוצאה | קלפים: תרגיל (3×3) מול תוצאה (9) |
| 7 | number-sequence | סדרה חשבונית חסרה | המספר הבא בסדרה (2,4,6,◻) |
| 8 | multiplication-bingo | בינגו לוח הכפל | המערכת מגרילה תרגיל, סימון תוצאה בלוח |
| 9 | tens-units | עשרות ויחידות | פירוק 45 ל-4 עשרות ו-5 יחידות |
| 10 | rounding | עיגול מספרים | עיגול לעשרת/מאה הקרובה |
| 11 | odd-one-out-math | איזה מספר יוצא דופן | 4 מספרים, רק 3 מתחלקים ב-5/זוגיים |
| 12 | fraction-pizza | מחשבון שברים ויזואלי | צביעת חלקי פיצה לפי שבר |
| 13 | sort-ascending | סדר מהקטן לגדול | גרירת 4–5 מספרים/תרגילים לסדר |
| 14 | make-ten | משלימים ל-10/100 | מרוץ לחיצה על זוגות שסכומם 10/100 |
| 15 | addition-pyramid | פירמידת חיבור | כל לבנה = סכום שתי הלבנים מתחתיה |
| 16 | toy-shop | חנות צעצועים | בחירת מטבעות מדויקים לתשלום |
| 17 | change-calculator | עודף מהקנייה | חישוב עודף מקנייה |
| 18 | thermometer | מד חום ומספרים שליליים | הזזת מד חום לחישוב טמפרטורה |
| 19 | clock-match | שעון מחוגים ← דיגיטלי | התאמת שעון אנלוגי לשעה דיגיטלית |
| 20 | number-line-jumps | ציר המספרים | קפיצות קדימה/אחורה להגעה לתוצאה |
| 21 | balance-scale | משקל ומאזניים | איזון מאזניים עם משקולות |
| 22 | perimeter | חישוב היקפים | סכום צלעות של צורות |
| 23 | times-table-race | אליפות לוח הכפל | 10 שאלות כפל ברצף בזמן |
| 24 | count-shapes | ספירת צורות | כמה משולשים/מרובעים באיור |
| 25 | half-or-double | חצי או כפול | לחיצה מהירה: פי 2 או מחצית |

### 📜 עברית ושפה (26–50)

| # | Slug | שם | מכניקה |
|---|---|---|---|
| 26 | word-scramble | סדר את המילה | גרירת אותיות מבולבלות לסדר נכון |
| 27 | gender-sort | זכר או נקבה | גרירת מילים לתיבת זכר/נקבה |
| 28 | hangman-house | איש תלוי (בניית בית) | ניחוש אותיות, כל טעות מורידה לבנה |
| 29 | spelling-error | מצא את שגיאת הכתיב | ספינה מול ספינע — בחירת הנכונה |
| 30 | singular-plural | יחיד או רבים | כסא ← כסאות |
| 31 | rhymes | חרוזים לפי צליל | מציאת מילים מתחרזות |
| 32 | opposites-he | הפכים | חם-קר, גבוה-נמוך |
| 33 | synonyms | מילים נרדפות | מתיחת קו בין מילים דומות |
| 34 | missing-letter | השלם את האות החסרה | אות חסרה בהתחלה/אמצע/סוף |
| 35 | word-types | מיון לפי תפקיד | שם עצם / פועל / תואר |
| 36 | word-search | תפזורת אותיות | תפזורת 5×5 |
| 37 | story-fill | השלמת מילים בסיפור | Mad Libs — קטע עם מילים חסרות |
| 38 | sentence-scramble | סידור משפט מבולבל | הרכבת משפט תקני ממילים |
| 39 | first-last-letter | אות פותחת/סוגרת | זיהוי אות פותחת/סוגרת לפי תמונה |
| 40 | roots | שורשים פשוטים | א-כ-ל ← אוכל, אכילה |
| 41 | abc-order-he | סדר אלפביתי | גרירת 4 מילים לפי א'-ב' |
| 42 | compound-words | מילים מורכבות | רכבל, מגדלור ← שני חלקים |
| 43 | nikud | זהה את הניקוד | בחירת ניקוד נכון למילה |
| 44 | idioms | ביטויים ופתגמים | התאמת פתגם למשמעות |
| 45 | reading-comprehension | הבנת הנקרא | 3 משפטים + שאלת הבנה |
| 46 | syllables | חלוקה להברות | לחיצה על מספר ההברות |
| 47 | longest-word | טריוויית מילים | איזו מילה מכילה יותר אותיות |
| 48 | acronyms | ראשי תיבות | פענוח ראשי תיבות מוכרים |
| 49 | letter-swap | החלף אות | שיר ← גיר |
| 50 | picture-story | סיפור בתמונות | סידור 4 תמונות בסדר כרונולוגי |

### 🇬🇧 אנגלית (51–65)

| # | Slug | שם | מכניקה |
|---|---|---|---|
| 51 | english-word-match | English Word Match | מילה באנגלית ← תמונה |
| 52 | spelling-bee | Spelling Bee | שמיעת מילה + הקלדת אותיות |
| 53 | abc-order-en | ABC Order | סידור אותיות אנגליות |
| 54 | colors-shapes | Colors & Shapes | שמות צבעים וצורות |
| 55 | pronouns | Subject Pronouns | He/She/It/They למשפט/תמונה |
| 56 | numbers-to-words | Numbers to Words | 5 ← Five |
| 57 | opposites-en | Opposites | Big-Small, Fast-Slow |
| 58 | animals-en | Animals Vocabulary | שמות חיות באנגלית |
| 59 | fruit-veggie-sort | Fruit & Veggie Sorting | מיון פירות/ירקות |
| 60 | days-of-week | Days of the Week | סידור ימות השבוע |
| 61 | body-parts | Body Parts Quiz | לחיצה על חלק הגוף לפי המילה |
| 62 | action-verbs | Action Verbs Match | Run, Jump, Swim ← תמונות |
| 63 | plural-en | Singular vs Plural | Cat←Cats, Child←Children |
| 64 | fill-the-gap | Fill the Gap | השלמת מילה במשפט אנגלי |
| 65 | capital-small | Capital vs Small | A ← a |

### 🌍 מדעים וגיאוגרפיה (66–80)

| # | Slug | שם | מכניקה |
|---|---|---|---|
| 66 | living-things-sort | חי, צומח, דומם | גרירה ל-3 קטגוריות |
| 67 | water-cycle | מחזור המים | סידור: אידוי, עיבוי, משקעים |
| 68 | solar-system | מערכת השמש | סידור כוכבי לכת לפי מרחק מהשמש |
| 69 | weather-clothes | מזג אוויר ולבוש | התאמת לבוש לתנאי מזג אוויר |
| 70 | recycling-sort | מיון מחזור | אשפה ← פח נכון (נייר/פלסטיק/אורגני) |
| 71 | food-chain | שרשרת המזון | צמח ← ארנב ← שועל |
| 72 | continents | זהה את היבשת | לחיצה על יבשת במפת עולם |
| 73 | flags | דגלי מדינות | דגל ← שם מדינה |
| 74 | capitals | עיר בירה ומדינה | בירה ← מדינה |
| 75 | plant-parts | חלקי הצמח | שורש, גבעול, עלה, פרח |
| 76 | states-of-matter | מצבי צבירה | גז / נוזל / מוצק |
| 77 | carnivore-herbivore | טורף או צמחוני | סיווג חיות לפי תזונה |
| 78 | animal-sounds | זהה את צליל החיה | השמעת קול ← זיהוי חיה |
| 79 | israel-map | מפת ישראל | מיקום ערים על ציר צפון-דרום |
| 80 | seasons | עונות השנה | שיוך תופעות לעונה |

### 🧩 לוגיקה וקוד (81–90)

| # | Slug | שם | מכניקה |
|---|---|---|---|
| 81 | robot-grid | כוון את הרובוט | תכנון מסלול בצעדים למטרה |
| 82 | pattern-match | זהה את התבנית | השלמת רצף צורות/צבעים |
| 83 | memory-classic | משחק הזיכרון | זוגות תמונות זהות |
| 84 | sudoku-4x4 | סודוקו 4×4 | מספרים 1–4 או צורות |
| 85 | maze | מבוך | ניווט בחצי מקלדת/מגע |
| 86 | simon-says | סיימון | רצף אורות וצלילים מתארך |
| 87 | pixel-art-code | מילוי לפי קוד | צביעה לפי קואורדינטות (Pixel Art) |
| 88 | puzzle-piece | החלק החסר בפאזל | בחירת חתיכה להשלמת תמונה |
| 89 | keys-locks | מפתחות ומנעולים | התאמת צורות למנעולים |
| 90 | logic-scale | מאזני לוגיקה | A>B, B>C — מי הכי גדול |

### ⏱️ שיעורי בית ומוטיבציה (91–100)

| # | Slug | שם | מכניקה |
|---|---|---|---|
| 91 | pomodoro-rocket | טיימר חללית | Pomodoro שמקדם חללית בזמן למידה |
| 92 | task-checklist | רשימת V | צ'ק-ליסט עם צלילי ניצחון |
| 93 | break-wheel | גלגל המזל להפסקות | הגרלת פעילות הפסקה |
| 94 | sticker-book | אוסף מדבקות | לוח שמתמלא עם סיום משימות — **מאזין ל-`iakids-game-complete` מכל המשחקים** |
| 95 | flashcards | פלאשקארדס | כרטיסיות זיכרון לשינון |
| 96 | daily-goals | בונה מטרות יומי | 3 יעדים ליום + סימון |
| 97 | mood-journal | יומן מצב רוח | דירוג קל/בינוני/קשה ליום |
| 98 | typing-race | הקלדה מהירה | הקלדת מילים לפני שנעלמות |
| 99 | quiz-maker | בוחן עצמי | הורה/ילד מזין 3 שאלות + מענה |
| 100 | leaderboard | מדרג הישגים | טבלת שיאים אישית — **קורא high scores מכל משחקי ה-DB** |

---

## Build order suggestion

Start with one game per category as template (1, 26, 51, 66, 81, 91), verify SDK + hub flow, then batch-produce the rest — most games in a category share a mechanic (drag-sort, match-pairs, multiple-choice, timed-quiz) and can reuse each other's code.
