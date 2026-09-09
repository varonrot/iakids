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

def strip(s): return MARKS.sub('', s)

def dicta(words):
    body = json.dumps({'task': 'nakdan', 'data': ' '.join(words), 'genre': 'modern',
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
            elif QAMATS in prev and i < len(cl) and cl[i][0] != 'ו': out.append('ו')               # rare; leave bare
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

def vocalise(words):
    res, bad = {}, []
    ov = overrides()
    words = [w for w in words if w not in ov]
    res.update({w: ov[w] for w in ov})
    for chunk in (words[i:i + 60] for i in range(0, len(words), 60)):
        for w, d in zip(chunk, dicta(chunk)):
            if strip(d['word']) != w: bad.append((w, 'misaligned reply')); continue
            v = None
            for opt in d.get('options') or []:
                v = refit(w, opt)
                if v: break
            if v: res[w] = v
            else: bad.append((w, (d.get('options') or ['?'])[0]))
    return res, bad

if __name__ == '__main__':
    args = sys.argv[1:]
    as_json = '--json' in args; args = [a for a in args if a != '--json']
    words = []
    for a in args:
        try: words += [x for x in open(a, encoding='utf-8').read().split() if x]
        except OSError: words.append(a)
    res, bad = vocalise(words)
    if as_json: print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        for w in words: print(f'{w}\t{res.get(w, "")}')
    for w, why in bad: print(f'[unvocalised] {w}: {why}', file=sys.stderr)
