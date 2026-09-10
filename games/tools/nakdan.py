#!/usr/bin/env python3
"""Vocalise (add nikud to) Hebrew words for the games, offline, once.

    python3 games/tools/nakdan.py כלב חתול שולחן            # prints word<TAB>vocalised
    python3 games/tools/nakdan.py --json words.txt > out.json

Uses Dicta's Nakdan (https://nakdan.dicta.org.il) and takes its most likely
reading. Dicta answers in ktiv haser (שֻׁלְחָן), but every game keys its logic
on the plain ktiv male spelling the child sees (שולחן), so the marks are
re-fitted onto the game's own letters (שׁוּלְחָן): a dropped ו becomes shuruk /
holam male, a dropped י becomes hiriq male. The result is accepted only if
stripping the marks gives back exactly the original word; otherwise the word
is left unvocalised and listed on stderr, so nothing wrong ever reaches a child.
"""
import json, sys, re, urllib.request

API = 'https://nakdan-5-3.loadbalancer.dicta.org.il/api'
MARKS = re.compile('[֑-ׇ]')
SHEVA, HIRIQ, TSERE, SEGOL, PATACH, QAMATS, HOLAM, QUBUTS, DAGESH = 'ְ', 'ִ', 'ֵ', 'ֶ', 'ַ', 'ָ', 'ֹ', 'ֻ', 'ּ'
HATAF_QAMATS = 'ֳ'  # אֳנִיָּה -> אוֹנִיָּיה: also an /o/ that ktiv male writes with a vav

def strip(s): return MARKS.sub('', s)

def dicta(words):
    # A full stop between the words matters: sent space-separated, Dicta reads two
    # adjacent nouns as smichut and returns construct forms (בֵּית for בַּיִת).
    body = json.dumps({'task': 'nakdan', 'data': '. '.join(words) + '.', 'genre': 'modern',
                       'addmorph': False, 'keepqq': False, 'nodageshdefmem': False, 'patachma': False, 'keepmetagim': False})
    req = urllib.request.Request(API, data=body.encode('utf-8'), headers={'Content-Type': 'text/plain;charset=UTF-8'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return [w for w in json.load(r) if not w.get('sep')]

def clusters(voc):
    """Split a vocalised string into [letter + its marks] clusters."""
    out = []
    for ch in voc:
        if MARKS.match(ch) and out: out[-1] += ch
        else: out.append(ch)
    return out

def refit(plain, option):
    """Re-fit Dicta's (possibly haser) vocalisation onto the plain male spelling."""
    if strip(option) == plain:
        return option
    cl = clusters(option.replace('|', ''))
    out, i = [], 0
    for ch in plain:
        if i < len(cl) and cl[i][0] == ch:
            out.append(cl[i]); i += 1; continue
        # plain has a letter Dicta dropped: a mater lectionis
        prev = out[-1] if out else ''
        if ch == 'ו':
            if QUBUTS in prev:   out[-1] = prev.replace(QUBUTS, ''); out.append('ו' + DAGESH)      # שֻׁלְחָן -> שׁוּלְחָן
            elif HOLAM in prev:  out[-1] = prev.replace(HOLAM, '');  out.append('ו' + HOLAM)       # חֹל -> חוֹל
            # A qamats before a vav that ktiv male writes is qamats qatan, i.e. an
            # /o/: אָזְנַיִים is spelled אוֹזְנַיִים, not אָוזְנַיִים. But when the
            # previous letter is itself a vav this second vav is only ktiv male
            # doubling a consonantal one (שַׁלְוָה -> שלווה), so it stays bare.
            elif prev[:1] == 'ו': out.append('ו')
            elif QAMATS in prev: out[-1] = prev.replace(QAMATS, ''); out.append('ו' + HOLAM)
            elif HATAF_QAMATS in prev: out[-1] = prev.replace(HATAF_QAMATS, ''); out.append('ו' + HOLAM)
            else: out.append('ו')
        elif ch == 'י':
            if HIRIQ in prev or TSERE in prev or SEGOL in prev: out.append('י')                   # hiriq/tsere male
            else: out.append('י')
        else:
            return None   # a real consonant differs: not the same word
    if i != len(cl):
        return None
    voc = ''.join(out)
    return voc if strip(voc) == plain else None

OVERRIDES_FILE = __file__.rsplit('/', 1)[0] + '/nikud-overrides.json'
def overrides():
    try:
        d = json.load(open(OVERRIDES_FILE, encoding='utf-8'))
        return {k: v for k, v in d.items() if not k.startswith('_') and strip(v) == k}
    except OSError:
        return {}

def vocalise(words, want_alts=False):
    """Returns (word -> vocalised, unvocalised list, word -> other valid readings).
    A word with more than one valid reading is a homograph: the top reading may be
    the wrong sense (עֹז strength vs עֵז goat), so those are worth eyeballing."""
    res, bad, alts = {}, [], {}
    ov = overrides()
    todo = [w for w in dict.fromkeys(words) if w not in ov]
    res.update({w: ov[w] for w in ov if w in set(words)})
    for chunk in (todo[i:i + 50] for i in range(0, len(todo), 50)):
        try:
            reply = dicta(chunk)
        except Exception as e:
            bad += [(w, f'api: {e}') for w in chunk]; continue
        if len(reply) != len(chunk):
            bad += [(w, 'misaligned reply') for w in chunk]; continue
        for w, d in zip(chunk, reply):
            if strip(d['word']) != w: bad.append((w, 'misaligned reply')); continue
            fitted = []
            for opt in d.get('options') or []:
                v = refit(w, opt)
                if v and v not in fitted: fitted.append(v)
            if fitted:
                res[w] = fitted[0]
                if len(fitted) > 1: alts[w] = fitted[1:4]
            else:
                bad.append((w, (d.get('options') or ['?'])[0]))
    return (res, bad, alts) if want_alts else (res, bad)

if __name__ == '__main__':
    args = sys.argv[1:]
    as_json = '--json' in args; args = [a for a in args if a != '--json']
    words = []
    for a in args:
        try: words += [x for x in open(a, encoding='utf-8').read().split() if x]
        except OSError: words.append(a)
    res, bad, alts = vocalise(words, want_alts=True)
    if as_json: print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        for w in words: print(f'{w}\t{res.get(w, "")}')
    for w, why in bad: print(f'[unvocalised] {w}: {why}', file=sys.stderr)
    for w, a in alts.items(): print(f'[homograph] {w}: {res[w]}  (also {" ".join(a)})', file=sys.stderr)
