# הכתבות — dictation

A child hears a word and writes it. The point is spelling, so everything the game
does is arranged around one question: can they produce the letters themselves.

## Modes

The start screen offers two, as cards rather than buttons, because the choice changes
what the game is:

| mode | what happens |
|---|---|
| 👀 **הצצה** | the word appears, a bar drains, the word fades out, and the child writes it from memory — with the voice available alongside |
| 🎧 **הקשבה** | the word is never shown. Only the voice. |

A device with no speech voice at all falls back to peek mode on its own, so the game
is never unplayable — it just becomes a copying exercise, which is still the right
exercise for the youngest children.

## Levels

The level sets the words *and* how much help the mode gives:

| level | words | peek | listens |
|---|---|---|---|
| קל | short, written the way they sound | 4s | unlimited |
| בינוני | longer, the everyday traps: ו/י as vowels, ה at the end | 2.5s | unlimited |
| קשה | the ones children really get wrong: א/ע, כ/ח, ט/ת, ס/ש | 1.5s | **one** |
| 🎲 | mixes them question to question | | |

Adaptive difficulty moves between the three as usual.

## The teacher's own list

A parent or teacher opens **✏️ רשימת המילים שלי** on the start screen and types words,
one per line or comma separated. The list replaces the built-in words at every level
and is kept in the game's own IndexedDB, so it survives between sessions on that
device. `IAKidsSpeech.prime()` runs once on save, so a device that needs the model
voice pays for each new word exactly once.

A list also travels in a link — `?words=חתול,מטרייה,עיפרון` — which is how a teacher
hands the week's words to a class.

## Repeating until it is learnt

The round is not a fixed number of questions. `IAKidsMastery` holds the round's words
and hands them out until each has been written correctly — once on easy, twice on the
harder levels, where a word spelled right one time may still have been a guess. A
missed word returns a couple of words later, far enough that the child has to recall
it rather than copy what is still on screen.

The counter in the HUD shows **words known / words in the list**, so a word coming
back reads as progress and not as a setback.

A word asked five times and still wrong stops being asked. Holding a child in a loop
they cannot leave is worse than stopping, and that word is more useful to the grown-up
than to the child right now — so it appears on the end screen instead, under
"נשארו לתרגול", with a button that starts a short new round over just those words.
That is the loop that gets to a pass: play, see what is missing, practise only that.

Passing is 80% of the list known. Stars follow the same number rather than the raw
answer count.

## Marking

An answer is compared on its letters: marks, spaces, apostrophes and maqaf are
stripped from both sides, because none of them is a spelling mistake a child made.
Everything else must match exactly.

A wrong answer is worth more than a right one here, so it gets more screen: the child
sees their own letters against the word, right to left, green where they match, red
where they do not and dashed where a letter is missing — then the word itself, with
nikud, under the heading "כך כותבים אותה". Two and a half seconds, against one and a
bit for a correct answer.

## Interface notes

- **No question timer.** The mechanic is writing, and a countdown while a child forms
  letters measures handwriting speed rather than spelling. `INTERFACE.md` §7 allows
  this for slow mechanics; the pressure lives in the peek duration instead.
- **Nikud is withheld until the answer is in** (NIKUD.md R10). Showing marks on the
  target word would spell it out. They appear in the reveal, where they teach.
- **`newQuestion` passes `{ accept }`** so the shared question bank can never serve a
  word from another round — with a teacher's list loaded, a bank row would ask the
  child to spell a word their list never contained.
- Own IndexedDB: `iakids_game_dictation`. Words for the built-in levels are covered by
  `games/nikud.js`, so the reveal is vocalised.

## Build checklist

- [x] rounds picker, persisted
- [x] level select with 🎲, last level restored
- [x] coins on right/wrong, +25 through `game.complete`
- [x] the round is a mastery loop over the list, not a fixed question count
- [x] adaptive difficulty
- [x] feedback FX on the slate
- [ ] question timer — deliberately omitted, see above
- [x] help modal
- [x] end screen: stars, score, player, best, share
- [x] five languages for every label
- [x] home button (automatic)
