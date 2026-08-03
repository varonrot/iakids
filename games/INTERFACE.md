# iakids Game Interface Spec

Every game under `/games/<slug>/index.html` implements this interface. It's how 100 independently-built games behave as one consistent product. Reference implementation: `games/demo/index.html` — copy it as a starting point.

## Setup

```html
<link rel="stylesheet" href="../game-style.css">
<script src="../game-sdk.js"></script>
```

Both files are shared and loaded read-only by every game — never edit them from within a game's own build task; changes there affect all 100 games.

```js
const game = await IAKidsGame.init('<slug>'); // slug = folder name, own IndexedDB: iakids_game_<slug>
```

---

## The 11 required pieces

### 1. Rounds picker
Start screen offers **5 / 10 / 15** rounds (or the game's natural unit — boards, pyramids, mazes). Persist the choice:
```js
await game.saveProgress({ rounds: TOTAL, lastLevel: level });
```

### 2. Level select
Buttons: **קל / בינוני / קשה / 🎲 אקראי**. Highlight/restore the last-played level from `loadProgress()`. 🎲 mixes levels question-to-question.

### 3. Coins
```js
IAKidsCoins.mount();          // once, on load — shows the wallet badge
IAKidsCoins.right(btnEl);     // +10, +streak bonus every 3 in a row, coin-fly animation
IAKidsCoins.wrong();          // -5, floors at 0
```
`game.complete(score)` auto-awards **+25** on finish — don't award it yourself.

### 4. No-repeat questions
```js
const q = await game.newQuestion(() => makeQuestion(level), q => q.text); // keyFn = identity
```
Skips the player's last ~300 answered questions; auto-resets when the pool is exhausted so the game never dead-ends.

### 5. Adaptive difficulty
```js
const diff = game.difficulty(startLevel, maxLevel); // e.g. game.difficulty(level || 1, 3)
diff.right();   // nudges level up (+0.25)
diff.wrong();   // nudges level down (-0.5)
diff.level;     // current integer level — feed into your question generator
```

### 6. Feedback FX
```js
IAKidsFX.correct(btnEl);   // green pop + chime + floating "+10" — class auto-clears
IAKidsFX.wrong(btnEl);     // red shake + buzz + vibration — class auto-clears
```

### 7. Question timer (where the mechanic is fast-paced — see each game's GAME.md)
```js
const timer = game.timer({ style: 'bomb', onTimeout: () => answer(null) }); // once
timer.start(IAKidsTimer.secondsFor(diff.level));  // each question — shrinks as level rises
timer.stop();                                     // on answer
```
Timeout counts as wrong. Optional for slow/manipulation mechanics (drag boards, widgets) — document the choice.

### 8. Help modal
```js
IAKidsHelp.mount({
  slug: '<slug>',
  how: 'קצר, ידידותי לילדים, מסביר איך משחקים',
  example: '<span dir="ltr"><b>7 + ◻ = 10</b></span> ← 3',  // HTML allowed
});
```
❓ button, auto-opens on the player's first visit only (localStorage-gated).

### 9. End screen
Stars (1–3, by accuracy), score, **player name + date/time** (automatic via `saveScore`), personal best, share button, play-again:
```js
await game.saveScore(score, { level });         // auto-attaches player + timestamp
const top = (await game.getHighScores(1))[0];
game.shareButton(score, containerEl);            // 📤 challenge-a-friend link
```

### 10. Finish the round
```js
game.complete(score);   // LAST call — awards +25 coins, confetti, challenge win-check, tournament chaining
```

### 11. Languages
```js
IAKidsLang.t({ he: 'טקסט', en: 'text', es: '...', de: '...', pt: '...' });
IAKidsLang.ui('play_again');  // pre-translated shared strings
```
Sets `<html lang/dir>` from `?lang=` or saved pref (he = RTL). Language-bound content (Hebrew letters, English vocab) stays in its own language regardless of UI language.

---

## Automatic — no code needed

These come free from `game-sdk.js` / `game-style.css` the moment a game links them:

| Feature | How |
|---|---|
| 🏠 Home button | Injected by `IAKidsGame.init()` — links back to the hub (`../`) |
| 🏆 Champion table | `games/champions/index.html` scans every `iakids_game_*` DB — nothing per-game |
| ⚔️ Tournaments | Chained via `?tournament=<id>` — SDK shows the "next game" button automatically after `complete()` |
| 📤 Challenge links | `shareButton()` embeds score in a URL; opening it shows a "beat X!" banner and auto win/lose check on `complete()` |
| Button style reset | `.correct` / `.wrong` classes auto-clear after their animation |

---

## Content rules

- **RTL correctness**: wrap math/English/numeric expressions in `<span dir="ltr">` so they don't flip inside the RTL page.
- **Touch-friendly**: tap targets ≥60px; drag uses **Pointer Events** (`pointerdown`/`pointermove`/`pointerup` + `setPointerCapture`), never HTML5 drag&drop — it doesn't work reliably on touch. Hit-test the drop target *before* clearing the dragged element's `pointer-events:none` (via the `.dragging` CSS class), not after — clearing it first makes `elementFromPoint` hit the dragged element itself instead of the zone underneath.
- **MCQ**: exactly one correct option, distractors plausible (common mistakes, ±1–3 off), shuffle position every question.
- **Hebrew**: final letters (ם ן ץ ף ך) only at word end; verify roots/nikud/gender/syllable counts — this is real content kids learn from.
- **Facts**: science/geography/flags/capitals must be independently verified, not guessed.

## "Tool" games (category ⏱️ שיעורי בית ומוטיבציה)

Different shape — no rounds/level/timer/difficulty/newQuestion. They persist state via `saveProgress`/`loadProgress` and award coins directly per completed action (`IAKidsCoins.add(n)`), no `game.complete()` call. Still get: `IAKidsCoins.mount()`, `IAKidsHelp.mount()`, home button (automatic).

## Definition of done

Full playthrough in a real browser, zero console errors, screenshot. Add the game's folder under `/games/<slug>/` — the hub (`games/index.html`) auto-detects it by probing `<slug>/index.html`; no registration step needed.
