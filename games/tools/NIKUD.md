# Nikud rules

Every task that adds, changes or moves Hebrew text in the games goes through these.
They exist because each one was broken at least once and a child would have seen it.

Run the checker before you call such a task done:

```bash
python3 games/tools/nikud-check.py          # 0 = every rule holds
python3 games/tools/nikud-check.py --words  # list every uncovered word
```

`FAIL` must be empty. A `warn` needs a human to read it and decide.

---

## The invariant everything rests on

**A vocalised word has exactly the letters of the plain word.** Strip the marks and
you get the original back, character for character. Every game keys its comparisons,
its question keys and its answers on the plain word and renders the vocalised one, so
the moment a mark changes a letter, the game's own logic is wrong — a child answers
correctly and is told they are wrong.

This is rule **R1**, it is checked on every entry, and nothing may weaken it.

---

## R1 — letters survive

`strip(nikud) == word`, always. The generator refuses any reading that fails this and
leaves the word plain instead; the checker re-tests the whole dictionary; the database
enforces it again in a `CHECK` constraint. Three layers, because a violation is silent
and looks like a content bug rather than a data bug.

## R2 — an override is a real correction

An entry in `nikud-overrides.json` must obey R1 and must differ from the plain word.
Pinning a word to itself hides it from the generator without saying so.

## R3 — an override actually reaches the dictionary

`nikud.js` is regenerated from the overrides plus Dicta. An override that is not in
the built file is a note to nobody. Regenerate after every override change:

```bash
python3 games/tools/nikud-check.py --emit > /tmp/w.txt
python3 games/tools/nakdan.py --json /tmp/w.txt > /tmp/n.json
# then rebuild games/nikud.js from /tmp/n.json
```

## R4 — every rendered word is covered

A word the games can put on screen but the dictionary lacks appears bare beside
vocalised text, which reads worse than no nikud at all. The checker extracts the words
itself and `--emit` prints that same list for the generator, so the two cannot drift:
whatever the checker demands, the generator was fed.

What is deliberately not a word: abbreviations and transliterations that hold a geresh
or gershayim (`מנכ"ל`, `סה"כ`, `בייג׳ינג`), and the alphabet strip. They are removed
before extraction rather than pointed wrongly.

## R5 — an order is not a report

Dicta reads one word at a time, so it points `גררו` as the past tense `גָּרְרוּ`. The
how-to text is giving an order: `גִּרְרוּ`. The same for `בחרו`, `מצאו`, `הפכו`,
`סדרו`, `צבעו`, `קראו`, `חזרו`, `עשו`, `מלאו`, `עזרו`, `מחאו`, `ענו` — all pinned.
The checker flags an instruction verb ending in shuruk whose first letter carries a
qamats; read each one, because a real past tense inside a story is a legitimate hit.

## R6 — send words a sentence apart

Space-separated, Dicta reads two adjacent nouns as a construct pair and returns
`בֵּית` for `בַּיִת`, `שֻׁלְחַן` for `שֻׁלְחָן`. The generator joins them with a full
stop, which fixed eight readings by itself. Do not change that.

## R7 — ktiv male, refitted

Dicta answers in ktiv haser; the games spell ktiv male. The generator moves the mark
onto the letter the games actually write:

| Dicta | game | rule |
|---|---|---|
| `שֻׁלְחָן` | `שׁוּלְחָן` | qubuts before a dropped vav becomes shuruk |
| `חֹל` | `חוֹל` | holam becomes holam male |
| `אָזְנַיִים` | `אוֹזְנַיִים` | a qamats before a written vav is qamats qatan, an /o/ |
| `שַׁלְוָה` | `שַׁלְוָוה` | but a vav after a vav is only ktiv male doubling a consonant |

Every refit is then re-checked against R1, so a rule that misfires drops the word
rather than corrupting it.

## R8 — a homograph carries the sense the games use

Dicta cannot know that `עז` is a goat and not strength, that `ספר` is a book and not a
barber, that `שמן` is oil and not fat, that `את` marks the object. Those are pinned by
hand with the sense that game text actually means, and the note next to each says why.
A game that needs the other reading passes its own map to `IAKidsNikud.local()`
instead of changing the shared dictionary.

## R9 — never bake nikud into a game

A game may hold its own vocalised text — some do, from before the shared dictionary
existed — but it must ask `IAKidsNikud.enabled` before showing it, or a child who
turned nikud off still sees marks. Twenty-five games used to gate theirs on
`CHILD_AGE === 1 || CHILD_AGE === 2`, which never fired because `kids_profiles.age`
holds years, not grades; they now follow the pill like everything else.

Exempt, and the checker knows it: a game whose subject *is* nikud (`nikud`,
`syllables`) has to show marks whatever the pill says, and `IAKidsNikud.local()` is
the sanctioned way to pin one reading. The test looks only for combining marks — the
maqaf in "מתאימה ל־" is punctuation, not nikud.

## R10 — nikud must never give the answer away

In a game about reading a word, vocalise it as the question appears. In a game about
its letters or its spelling — `first-last-letter`, `missing-letter`, `spelling-error`,
`letter-swap`, `word-scramble` — the marks tell the child the answer, so show the
vocalised word only after they have answered.

## R11 — the child decides

`IAKidsNikud.enabled` answers in one order, most specific first:

1. **the pill** — `iakids_nikud`, set the moment anyone presses it. This always wins.
2. **the child's age** — `iakids_nikud_auto`, 8 and under gets nikud (`AUTO_UNTIL_AGE`).
3. **on**, for Hebrew, when neither is known.

The age lookup needs the network, so it lands after the page has drawn its text. When
it disagrees with what was drawn it redraws once, guarded by a session flag — without
that, the setting appears to change by itself on the *next* visit, which reads as a
bug rather than as a default. The pill's tooltip says which of the three is in force,
so "why is there no nikud" has an answer on the screen itself. Non-Hebrew pages never vocalise. A game that renders through
`IAKidsNikud` gets this for free; one that renders its own marks does not, which is
why R9 exists.

## R12 — no word disappears quietly

The generator returns every word it was asked about. When Dicta rewrites a spelling or
returns nothing that fits, the word comes back plain and is reported on stderr — it is
never dropped from the result, because a caller comparing counts is the only thing that
catches an API that half-answered.
