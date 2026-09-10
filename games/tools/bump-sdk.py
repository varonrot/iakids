#!/usr/bin/env python3
"""Stamp the shared files' version onto every game's <script>/<link> tag.

    python3 games/tools/bump-sdk.py           # report what would change
    python3 games/tools/bump-sdk.py --apply

Why this exists: game-sdk.js, nikud.js and game-style.css are served with
`cache-control: max-age=14400`, so a browser that opened any game in the last four
hours keeps its copy. A game whose HTML has just changed then loads *today's* markup
against *yesterday's* SDK — and a page calling something the old SDK never had dies
on a ReferenceError, which looks to a child like a button that does nothing.

Stamping the file's own content hash into the URL means the browser fetches a shared
file again exactly when it changed, and reuses it every other time. Run this after
any edit to a shared file, before pushing.
"""
import hashlib, re, sys, glob, os

APPLY = '--apply' in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # games/
SHARED = ['game-sdk.js', 'game-style.css']


def version(name):
    """Eight hex of the file's own content: it changes when, and only when, the file does."""
    with open(os.path.join(ROOT, name), 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def main():
    vers = {n: version(n) for n in SHARED}
    print('shared files:')
    for n, v in vers.items():
        print(f'  {n:16} {v}')

    # every page under games/, at any depth (a guide page links them too)
    pages = sorted(glob.glob(f'{ROOT}/**/*.html', recursive=True))
    changed, total = [], 0
    for p in pages:
        s = open(p, encoding='utf-8').read()
        out = s
        for name, v in vers.items():
            # ../game-sdk.js, ./game-sdk.js, game-sdk.js — with or without an old ?v=
            out = re.sub(
                r'((?:\.\./)*' + re.escape(name) + r')(?:\?v=[0-9a-f]+)?(?=["\'])',
                lambda m: f'{m.group(1)}?v={v}', out)
        # nikud.js is split per page (nikud-build.py): hash the copy beside this page
        own = os.path.join(os.path.dirname(p), 'nikud.js')
        if os.path.isfile(own):
            hv = hashlib.sha256(open(own, 'rb').read()).hexdigest()[:8]
            out = re.sub(r'(src=")nikud\.js(?:\?v=[0-9a-f]+)?"', lambda m: f'{m.group(1)}nikud.js?v={hv}"', out)
        if out != s:
            changed.append(os.path.relpath(p, ROOT))
            total += 1
            if APPLY:
                open(p, 'w', encoding='utf-8').write(out)

    print(f'\n{total} of {len(pages)} pages ' + ('updated' if APPLY else 'would change'))
    for c in changed[:8]:
        print('   ', c)
    if len(changed) > 8:
        print(f'    … and {len(changed)-8} more')
    if not APPLY and changed:
        print('\nrun again with --apply')
    return 0


if __name__ == '__main__':
    sys.exit(main())
