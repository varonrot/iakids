# iakids Game Interface Spec

Every game under `/games/<slug>/index.html` implements this interface. It's how 100 independently-built games behave as one consistent product. Reference implementation: `games/demo/index.html` — copy it as a starting point.

## Setup

```html
<link rel="stylesheet" href="../game-style.css">
<script src="../game-sdk.js"></script>
```

Both files are shared and loaded read-only by every game — never edit them from within a game's own build task; changes there affect all 100 games.

**After editing a shared file, run `python3 games/tools/bump-sdk.py --apply` before pushing.** The shared files are served with a four-hour cache, so a browser that opened any game today keeps its copy: a page whose HTML has just changed then runs against yesterday's SDK, and a call to something the old SDK never had dies on a ReferenceError — which, from the outside, looks like a button that does nothing. The tool stamps each shared file's own content hash into every `<script>`/`<link>` that loads it, so a browser refetches exactly when the file changed and reuses it every other time.

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
Skips everything this player already answered — locally (IndexedDB, last 2000) and, for a
signed-in child (`localStorage.active_kid_id`), in Supabase (`kid_question_answers`). When the
generator can't find a fresh question it pulls unanswered ones from the shared bank
(`game_questions`); only when that is empty too does the local history reset, so the game
never dead-ends. If a round has context the payload cannot carry (roots: which three roots are on screen), pass `{ accept: q => … }` as the third argument so a bank row from another round is never served into this one — and put the absolute fact (the root itself) in the payload, never an index into the current round. Every generated question is upserted into the bank (unique per game + key),
so the bank grows with play.

A client-written row is untrusted content — anyone signed in can post one, and the bank is
read by every child — so the bank only ever *serves* rows marked `verified`, or seeded /
authored server-side. Until the verifier has passed over a game, `newQuestion` therefore
behaves exactly as it always did: generator first, local reset on exhaustion. Growing the
bank and serving from it are deliberately two separate steps. The answer outcome is recorded automatically the moment the game
calls `IAKidsCoins.right()` / `.wrong()` (or `IAKidsActivity.correct()` / `.wrong()`).

**Pick a keyFn that identifies the *question*, not the rendering.** `x => x.word` is right;
`x => x.word + x.options.join('')` is wrong — a reshuffled option order would count as a new
question and the child sees the same word again. Pass `{ level }` as the third argument if
your generator's level differs from `game.difficulty().level`.

Schema: `supabase/migrations/20260908_game_question_bank.sql`. Guests (no active child) stay
local-only, exactly as before.

**Seeding.** Waiting for children to play a game into the bank is slow, so
`games/tools/harvest.mjs` runs a game's own generator offline and
`backend/seed_questions.py` loads the result as `source='seed'`. It works without
per-game code because your generator reaches the SDK as a zero-argument closure — the
harvester just calls it a few hundred times:

```bash
node games/tools/harvest.mjs --all --out /tmp/seed.json
python3 backend/seed_questions.py /tmp/seed.json --dry-run
```

Two things stop a game being harvestable, both worth knowing when you write one:

- **Questions must survive `JSON.stringify`.** A payload holding a function or a DOM node
  cannot be stored, so it cannot be shared. Keep questions plain data and let the render
  step turn them into elements.
- **Questions must not contain HTML.** A bank row is written with the anon key and read by
  every child, so the verifier rejects any payload containing markup — it cannot tell your
  `<span dir="ltr">` from an attacker's. Put the markup in your render code and keep the
  raw value in the payload (`{v: 29}`, not `{html: '<span dir="ltr">29</span>'}`).

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

### 9b. Practising a fixed list until it is learnt (optional)

When the words are a parent's or a teacher's, "answer ten questions" is the wrong
goal — the goal is to know *these* words. `IAKidsMastery` runs that loop:

```js
const drill = IAKidsMastery.over(words, { repeats: 2, passing: 0.8 });
const item = drill.next();          // null when there is nothing left to practise
drill.mark(item, wasCorrect);       // a miss returns a few items later, not next
drill.mastered / drill.total / drill.passed / drill.struggling
```

A missed item goes to the back of the queue rather than straight back, so the child
recalls it instead of copying what is still on screen. `maxAsks` stops a word that a
child simply cannot get today, and `struggling` reports those — which is what the end
screen offers as a second, shorter round. Stars follow `mastered / total`, not the raw
answer count: a child who missed a word four times and then learnt it has done well.

Where the list comes from is the game's business. `dictation` takes it three ways: a
textarea on the start screen (kept in the game's own IndexedDB, so it survives), the
`?words=…` query string (how a teacher hands out the week's words), and its built-in
graded lists when neither is present.

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
| 🔊 Read aloud | `IAKidsSpeech.mountReader()` floats a button that speaks the question on screen. A game that wants its own control builds one with `IAKidsSpeech.button(text)` and the floating one stands aside |
| 🌌 Space theme | `<body class="theme-space">` switches the whole game to the shared dark space look (`body.theme-space` block at the end of `game-style.css`). Override only what differs (e.g. `.game-card{width:min(560px,calc(100vw - 28px))!important}`) — never paste the theme into the game |

---

## Content rules

- **Reading aloud**: `IAKidsSpeech.say(text)` speaks a word or a sentence. It tries this browser's cache, then the browser's own voice — free, offline, no model — and only on a device with no voice for the language does it ask the tutor backend's model voice, whose answer it then keeps, so the model is never asked for the same text twice. `IAKidsSpeech.prime(list)` warms a list ahead of a round. Marks and markup are stripped before anything is spoken.

- **Nikud (vowel points) on Hebrew words**: never bake them into a game. Each game loads its **own** `nikud.js` — a few KB holding only the words it renders, cut from the master by `games/tools/nikud-build.py` — before `../game-sdk.js`, and renders through `IAKidsNikud`:

  ```html
  <script src="nikud.js"></script>        <!-- this game's own words, built by nikud-build.py -->
  <script src="../game-sdk.js"></script>
  ```
  ```js
  IAKidsNikud.of('שולחן')             // 'שׁוּלְחָן', '' when unknown
  IAKidsNikud.text('הילד רץ')          // a whole phrase, word by word
  IAKidsNikud.render(el, word, { mark: 0 })   // sets el's text; mark = index of a letter to bold
  IAKidsNikud.local({ 'שמן': 'שָׁמֵן' })      // this game means the other homograph
  ```
  The dictionary's letters always equal the plain word, so **every comparison, key
  and answer stays on the plain word** — only the rendered text is vocalised. A word
  the dictionary doesn't hold falls back to the plain word, so a missing `<script>`
  tag can never break a game.

  To add words: `python3 games/tools/nikud-check.py --emit > /tmp/w.txt`, then
  `python3 games/tools/nakdan.py --json /tmp/w.txt > /tmp/n.json`, review what it
  prints, then `python3 games/tools/nikud-build.py /tmp/n.json`, which rewrites the
  master and every page's own file. **Then run `python3 games/tools/nikud-check.py` — it must
  print no FAIL.** The twelve rules it enforces, and why each exists, are in
  `games/tools/NIKUD.md`; read that before any task that touches Hebrew text. Dicta reads each word on its own, so
  for a homograph it can only guess the sense — correct those in
  `games/tools/nikud-overrides.json`, never in `nikud.js` (it is regenerated) and never
  in the game. `backend/seed_nikud.py` mirrors the same file into Supabase
  (`public.hebrew_nikud`) for the backends.

  Where to show it: in a game that only *reads* the word (rhymes, syllables, roots,
  the sorting games) vocalise it immediately. In a game about letters or spelling
  (first-last-letter, missing-letter, spelling-error) nikud would give the answer
  away — show it after the child answers, as `first-last-letter` does.

  **Titles, how-to text, labels and buttons need no code at all.** Every translated
  string in every game goes through `IAKidsLang.t()`, which vocalises the Hebrew
  when nikud is on — emoji and inline `<b>` are left alone. Add a new string to a
  `T` object as usual; if a word of it is missing from the dictionary it simply
  stays plain, so run `nakdan.py` over the new words and regenerate.

  **On or off is the child's choice.** `IAKidsNikud.enabled` is a per-device flag
  and the pill in the start screen flips it (the page reloads, since every label
  was already rendered). The default is seeded from the active child's age —
  `AUTO_UNTIL_AGE` (8) and under gets nikud — and a child who presses the pill
  keeps their choice from then on. Non-Hebrew pages never show the pill and never
  vocalise.

- **RTL correctness**: wrap math/English/numeric expressions in `<span dir="ltr">` so they don't flip inside the RTL page.
- **Touch-friendly**: tap targets ≥60px; drag uses **Pointer Events** (`pointerdown`/`pointermove`/`pointerup` + `setPointerCapture`), never HTML5 drag&drop — it doesn't work reliably on touch. Hit-test the drop target *before* clearing the dragged element's `pointer-events:none` (via the `.dragging` CSS class), not after — clearing it first makes `elementFromPoint` hit the dragged element itself instead of the zone underneath.
- **MCQ**: exactly one correct option, distractors plausible (common mistakes, ±1–3 off), shuffle position every question.
- **Hebrew**: final letters (ם ן ץ ף ך) only at word end; verify roots/nikud/gender/syllable counts — this is real content kids learn from.
- **Facts**: science/geography/flags/capitals must be independently verified, not guessed.

## "Tool" games (category ⏱️ שיעורי בית ומוטיבציה)

Different shape — no rounds/level/timer/difficulty/newQuestion. They persist state via `saveProgress`/`loadProgress` and award coins directly per completed action (`IAKidsCoins.add(n)`), no `game.complete()` call. Still get: `IAKidsCoins.mount()`, `IAKidsHelp.mount()`, home button (automatic).

## Definition of done

Full playthrough in a real browser, zero console errors, screenshot. Add the game's folder under `/games/<slug>/` — the hub (`games/index.html`) auto-detects it by probing `<slug>/index.html`; no registration step needed.
