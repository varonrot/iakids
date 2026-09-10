#!/usr/bin/env python3
"""Check a page's Content-Security-Policy against what the page actually loads.

    backend/.venv/bin/python tools/csp_check.py                    # the mirror
    backend/.venv/bin/python tools/csp_check.py https://iakids.app # after Cloudflare

A CSP breaks a site quietly: the browser refuses a script and the page just stops
doing something, with a line in a console nobody has open. This reads the policy off
the response, then reads the page for every external thing it asks for — script src,
stylesheet href, fonts, images, `fetch(...)`, `import(...)`, iframes — and says which
of them the policy would refuse.

It is static, so it sees what the HTML says and what the inline JavaScript spells out
literally. It cannot see a URL a script builds at runtime; for that, load the page in
a browser and watch the console. Use both.
"""
import re, sys, urllib.parse
import httpx

BASE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'https://smarts-brains.online'

# One of each kind of page, so a gap anywhere shows up somewhere.
PAGES = [
    ('/he/games/workspace/', 'the workspace'),
    ('/games/', 'the games hub'),
    ('/games/dictation/', 'a game'),
    ('/games/champions/', 'the champions page'),
    ('/he/parent-panel/', 'the parent panel'),
    ('/he/', 'the Hebrew landing page'),
    ('/', 'the Spanish landing page'),
]
# Which directive governs which kind of reference, with the fallback the spec uses.
KIND_DIRECTIVE = {
    'script': 'script-src', 'style': 'style-src', 'font': 'font-src',
    'img': 'img-src', 'connect': 'connect-src', 'frame': 'frame-src', 'media': 'media-src',
}
RED, GREEN, DIM, OFF = '\033[31m', '\033[32m', '\033[2m', '\033[0m'


def parse_csp(header):
    out = {}
    for part in (header or '').split(';'):
        part = part.strip()
        if not part:
            continue
        name, *values = part.split()
        out[name.lower()] = values
    return out


def allowed(csp, kind, url, origin):
    """Would this policy let `url` load, for this kind of reference?"""
    directive = KIND_DIRECTIVE[kind]
    sources = csp.get(directive) or csp.get('default-src')
    if sources is None:
        return True, 'no directive and no default-src'
    if "'none'" in sources:
        return False, f"{directive} 'none'"
    p = urllib.parse.urlparse(url)
    if p.scheme in ('data', 'blob'):
        return (f'{p.scheme}:' in sources), f'{directive}: {p.scheme}:'
    if not p.netloc:                                   # same-origin path
        return ("'self'" in sources), f"{directive} 'self'"
    o = f'{p.scheme}://{p.netloc}'
    if o == origin:
        return ("'self'" in sources), f"{directive} 'self'"
    for s in sources:
        if s in (o, p.netloc, f'{p.scheme}:'):
            return True, s
        if s == 'https:' and p.scheme == 'https':
            return True, s
        if s.startswith('https://') and s.endswith('/') and url.startswith(s):
            return True, s
    return False, directive


def refs(html, page_url):
    """Every external thing the page asks for, as (kind, url)."""
    found = set()
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)', html, re.I):
        found.add(('script', m.group(1)))
    for m in re.finditer(r'<link[^>]+href=["\']([^"\']+)[^>]*>', html, re.I):
        tag = m.group(0).lower()
        if 'stylesheet' in tag:
            found.add(('style', m.group(1)))
        elif 'preconnect' in tag or 'dns-prefetch' in tag:
            pass                                        # a hint, not a load
    for m in re.finditer(r'<(?:img|source)[^>]+src=["\']([^"\']+)', html, re.I):
        found.add(('img', m.group(1)))
    for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)', html, re.I):
        found.add(('frame', m.group(1)))
    # inline JavaScript, spelled out literally
    for m in re.finditer(r'''\bimport\s*\(\s*["']([^"']+)["']''', html):
        found.add(('script', m.group(1)))
    for m in re.finditer(r'''\bfetch\s*\(\s*["']([^"']+)["']''', html):
        found.add(('connect', m.group(1)))
    # Anything already named by a <link> is a stylesheet or a hint, not a fetch —
    # counting it as connect-src reports font CSS as a refused XHR, which it is not.
    linked = {m.group(1) for m in re.finditer(r'<link[^>]+href=["\']([^"\']+)', html, re.I)}
    linked |= {m.group(1) for m in re.finditer(r'<(?:link|meta)[^>]+(?:href|content)=["\'](https?://[^"\']+)', html, re.I)}
    hosts_linked = {urllib.parse.urlparse(u).netloc for u in linked if u.startswith('http')}
    for m in re.finditer(r'''["'](https?://[^"'\s]+)["']''', html):
        u = m.group(1)
        if u in linked or urllib.parse.urlparse(u).netloc in hosts_linked:
            continue
        if any(k in u for k in ('supabase.co', 'onrender.com', 'googleapis.com', 'gstatic.com')):
            found.add(('connect', u))
    return {(k, urllib.parse.urljoin(page_url, u)) for k, u in found}


def main():
    origin = BASE
    print(f'\nCSP as served by {BASE}')
    r = httpx.get(BASE + '/he/games/workspace/', timeout=40, follow_redirects=True)
    csp = parse_csp(r.headers.get('content-security-policy'))
    if not csp:
        print(f'  {RED}no Content-Security-Policy header — nothing to check{OFF}\n')
        return 1
    for k in sorted(csp):
        print(f'  {DIM}{k:14}{OFF} {" ".join(csp[k])[:100]}')

    problems, checked = [], 0
    print('\nWhat each page asks for')
    for path, label in PAGES:
        try:
            page = httpx.get(BASE + path, timeout=60, follow_redirects=True)
        except Exception as e:
            print(f'  {path:26} {DIM}{type(e).__name__}{OFF}')
            continue
        if page.status_code >= 400:
            print(f'  {path:26} {DIM}{page.status_code}{OFF}')
            continue
        bad = []
        for kind, url in sorted(refs(page.text, BASE + path)):
            checked += 1
            ok, why = allowed(csp, kind, url, origin)
            if not ok:
                bad.append((kind, url, why))
        if bad:
            print(f'  {path:26} {RED}{len(bad)} refused{OFF}   ({label})')
            for kind, url, why in bad:
                print(f'      {RED}{kind:8}{OFF} {url[:88]}   {DIM}{why}{OFF}')
            problems += bad
        else:
            print(f'  {path:26} {GREEN}all allowed{OFF}   {DIM}({label}){OFF}')

    print(f'\n{checked} references checked, {len(problems)} would be refused.')
    if problems:
        need = sorted({urllib.parse.urlparse(u).scheme + '://' + urllib.parse.urlparse(u).netloc
                       for _, u, _ in problems})
        print('Add to the policy: ' + ' '.join(need))
    print('Static only — a URL built at runtime is invisible here. Load the pages in a'
          '\nbrowser too and watch the console for "Refused to".\n')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
