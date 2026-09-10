#!/usr/bin/env python3
"""Check the nikud rules. Run this after any change that touches nikud.

    python3 games/tools/nikud-check.py            # report
    python3 games/tools/nikud-check.py --words    # also list every uncovered word
    python3 games/tools/nikud-check.py --emit     # print every Hebrew word the games render

`--emit` is what feeds the generator, so the dictionary is built from exactly the
words this checker then demands coverage of — the two can never drift apart:

    python3 games/tools/nikud-check.py --emit > /tmp/w.txt
    python3 games/tools/nakdan.py --json /tmp/w.txt > /tmp/n.json

Exit code 0 = every rule holds, 1 = something needs fixing. The rules themselves,
and why each one exists, are in games/tools/NIKUD.md.
"""
import json, re, sys, glob, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # games/
MARKS = re.compile('[֑-ׇ]')
HEB = re.compile(r'[א-ת]{2,}')
# A Hebrew token holding a geresh or gershayim is either an abbreviation (מנכ"ל,
# סה"כ) or a transliteration whose geresh carries a foreign sound (בייג׳ינג).
# Neither is a word to vocalise, and splitting one leaves nonsense fragments
# behind, so take the whole token out before looking for words.
ABBREV = re.compile(r'[א-ת]+(?:["\u05f4\u05f3\'][א-ת]*)+')
LIST_WORDS = '--words' in sys.argv
EMIT = '--emit' in sys.argv

# Pages under games/ that are not games and render no game text.
SKIP_DIRS = {'tools'}
# Deliberately never vocalised. The acronyms game prints the letters of an
# abbreviation, which are not words, and Dicta rewrites some transliterations
# rather than pointing them — those stay plain instead of getting a wrong reading.
NEVER = {'אבגדהוזחטיכלמנסעפצקרשת', 'פלאשקארדס'}
FRAGMENT = re.compile(r'^[א-ת]{2,4}$')      # only when it never appears as a real word

def is_fragment(w, counts):
    """An abbreviation the acronyms game spells out, not a word of Hebrew."""
    return w in NEVER or (FRAGMENT.match(w) and counts.get(w, 0) and w in ACRONYM_BITS)

ACRONYM_BITS = set()

fails, warns = [], []
def fail(rule, msg): fails.append(f'{rule}: {msg}')
def warn(rule, msg): warns.append(f'{rule}: {msg}')


def load_dictionary():
    src = open(f'{ROOT}/nikud.js', encoding='utf-8').read()
    return dict(re.findall(r"'([א-ת]+)': '([^']+)'", src)), src


def load_overrides():
    d = json.load(open(f'{ROOT}/tools/nikud-overrides.json', encoding='utf-8'))
    return {k: v for k, v in d.items() if not k.startswith('_')}


def hebrew_words_in_games():
    """Every Hebrew word the games can put on screen, by game."""
    per_game = collections.defaultdict(collections.Counter)
    # the acronyms game's own letter lists: those strings are abbreviations, not words
    try:
        acr = open(f'{ROOT}/acronyms/index.html', encoding='utf-8').read()
        for m in re.findall(r"short\s*:\s*'([א-ת]+)'|'([א-ת]{2,4})'\s*,\s*full", acr):
            ACRONYM_BITS.add(m[0] or m[1])
        for m in re.findall(r"'([א-ת]{2,4})'", acr):
            if len(m) <= 4: ACRONYM_BITS.add(m)
    except OSError:
        pass
    files = sorted(glob.glob(f'{ROOT}/*/index.html')) + [f'{ROOT}/index.html', f'{ROOT}/game-sdk.js']
    for f in files:
        slug = os.path.basename(os.path.dirname(f)) if f.endswith('index.html') else 'game-sdk'
        if slug in SKIP_DIRS:
            continue
        s = open(f, encoding='utf-8').read()
        blocks = re.findall(r'<script>(.*?)</script>', s, re.S) if f.endswith('.html') else [s]
        for blk in blocks:
            for m in re.findall(r"'([^'\\\n]{1,400})'|\"([^\"\\\n]{1,400})\"|`([^`\\]{1,400})`", blk):
                t = m[0] or m[1] or m[2]
                if not re.search(r'[א-ת]', t):
                    continue
                # A Latin sentinel, not a space: `כ${n}ו` must not become the word
                # "כו", and <b>מתאדים</b> must still yield מתאדים. Strip the marks
                # too: a game that hard-codes vocalised text would otherwise yield
                # the unmarked letter pairs inside it (הַכּוֹכָבִים -> "ים") as words.
                t = MARKS.sub('', re.sub(r'<[^>]*>|\$\{[^}]*\}', 'Z', t))
                t = ABBREV.sub('Z', t)
                for w in HEB.findall(t):
                    per_game[slug][w] += 1
    return per_game


def instruction_words():
    """Words from how-to / intro / subtitle text — where a verb is an order, not a report."""
    pat = re.compile(
        r"(?:how|howto|hint|intro|desc|tagline|instr|play|subtitle|note)\w*\s*:\s*"
        r"(?:\{[^{}]*?he\s*:\s*)?(['\"`])(.*?)\1", re.S)
    out = collections.Counter()
    for f in sorted(glob.glob(f'{ROOT}/*/index.html')):
        s = open(f, encoding='utf-8').read()
        for blk in re.findall(r'<script>(.*?)</script>', s, re.S):
            for _, t in pat.findall(blk):
                t = ABBREV.sub('Z', MARKS.sub('', re.sub(r'<[^>]*>|\$\{[^}]*\}', 'Z', t)))
                for w in HEB.findall(t):
                    out[w] += 1
    return out


def main():
    if EMIT:
        words = collections.Counter()
        for c in hebrew_words_in_games().values():
            words.update(c)
        print('\n'.join(sorted(w for w in words if w not in NEVER)))
        return 0
    dictionary, src = load_dictionary()
    overrides = load_overrides()
    per_game = hebrew_words_in_games()
    instr = instruction_words()
    all_words = collections.Counter()
    for c in per_game.values():
        all_words.update(c)

    print(f'dictionary {len(dictionary)} words · {len(overrides)} pinned by hand · '
          f'{len(all_words)} Hebrew words across {len(per_game)} games\n')

    # R1 — the letters must survive vocalisation, or a game's own logic breaks.
    broken = {w: v for w, v in dictionary.items() if MARKS.sub('', v) != w}
    if broken:
        fail('R1 letters', f'{len(broken)} entries change the letters, e.g. ' +
             ', '.join(f'{w}->{v}' for w, v in list(broken.items())[:3]))

    # R2 — an override must obey R1 too, and must actually differ from the plain word.
    for w, v in overrides.items():
        if MARKS.sub('', v) != w:
            fail('R2 override', f'{w} -> {v} changes the letters')
        if v == w:
            fail('R2 override', f'{w} pins the plain word — delete it instead')

    # R3 — every override has to reach the dictionary, or it is a note to nobody.
    missing_ov = [w for w in overrides if dictionary.get(w) != overrides[w]]
    if missing_ov:
        fail('R3 applied', f'{len(missing_ov)} overrides are not in nikud.js — regenerate it: ' +
             ' '.join(missing_ov[:6]))

    # R4 — coverage: a word a game renders but the dictionary lacks shows up bare
    # next to vocalised text, which reads worse than no nikud at all.
    uncovered = {w: n for w, n in all_words.items()
                 if w not in dictionary and not is_fragment(w, all_words)}
    if uncovered:
        by_game = {g: sorted(w for w in c if w in uncovered) for g, c in per_game.items()}
        by_game = {g: ws for g, ws in by_game.items() if ws}
        fail('R4 coverage', f'{len(uncovered)} words are rendered but not in the dictionary, '
                            f'in {len(by_game)} games')
        for g, ws in sorted(by_game.items(), key=lambda x: -len(x[1]))[:8]:
            print(f'    {g:24} {len(ws):3}  {" ".join(ws[:6])}')
        if LIST_WORDS:
            print('\n    all uncovered:', ' '.join(sorted(uncovered)))

    # R5 — an imperative in the instructions must not be pointed as past tense.
    # Past ...וּ of a plain verb takes qamats on the first letter (גָּרְרוּ); the
    # order takes hiriq or patach (גִּרְרוּ). Flag those for a human to read.
    QAMATS, SHURUK = 'ָ', 'וּ'
    suspects = []
    for w in instr:
        if not w.endswith('ו') or len(w) < 3 or w in overrides:
            continue
        v = dictionary.get(w)
        # Only a verb: the plural ends in shuruk (גָּרְרוּ). A possessive or a place
        # name ends in holam (יָדוֹ, יָפוֹ) and is not an order anyone can give.
        if not v or not v.endswith(SHURUK):
            continue
        if QAMATS in v[:2]:
            suspects.append(f'{w}={v}')
    if suspects:
        warn('R5 imperative', f'{len(suspects)} instruction verbs look like past tense — '
                              f'read them and pin the order form: ' + ', '.join(suspects[:10]))

    # R6 — nikud.js is generated; a hand edit is lost on the next run.
    if 'Generated by' not in src.split('const IAKIDS_NIKUD')[0]:
        fail('R6 generated', 'nikud.js lost its "generated" header — is it being edited by hand?')

    # R7 — no game may carry its own copy of the vocalisation.
    baked = []
    for f in sorted(glob.glob(f'{ROOT}/*/index.html')):
        s = open(f, encoding='utf-8').read()
        for blk in re.findall(r'<script>(.*?)</script>', s, re.S):
            if re.search(r"[א-ת]" + MARKS.pattern, blk) and 'IAKIDS_NIKUD' not in blk:
                # a vocalised literal inside game code
                sample = re.search(r"['\"]([^'\"\n]{0,20}[א-ת][֑-ׇ][^'\"\n]{0,20})['\"]", blk)
                baked.append(f'{os.path.basename(os.path.dirname(f))}' +
                             (f' ({sample.group(1)})' if sample else ''))
                break
    if baked:
        warn('R7 no baking', f'{len(baked)} games hold vocalised text of their own — it ignores '
                             f'the on/off pill: ' + ', '.join(baked[:8]))

    # R8 — a game that renders a word must load the dictionary.
    for f in sorted(glob.glob(f'{ROOT}/*/index.html')):
        s = open(f, encoding='utf-8').read()
        if 'IAKidsNikud' in s and '../nikud.js' not in s:
            fail('R8 script tag', f'{os.path.basename(os.path.dirname(f))} calls IAKidsNikud '
                                  f'but never loads ../nikud.js')

    for line in fails:
        print('  FAIL  ' + line)
    for line in warns:
        print('  warn  ' + line)
    if not fails and not warns:
        print('  all rules hold')
    print()
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
