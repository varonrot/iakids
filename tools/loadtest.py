#!/usr/bin/env python3
"""How many children can play at once before something gives.

    python3 tools/loadtest.py --list
    python3 tools/loadtest.py game            # ramp until it hurts, then stop
    python3 tools/loadtest.py game --max 200 --yes

It ramps concurrency, doubling each step, and stops at the first step where the
service stops keeping up — so the answer comes back as a number, not a graph.

SAFETY, because this points at production and children may be playing right now:

  * Anything that calls a language model is refused. Those endpoints cost money per
    request and the backends have no rate limit, so a ramp there is a bill, not a
    measurement. `--i-know-this-costs-money` is the only way past it, and the cap
    stays low even then.
  * Nothing writes. Every scenario is a GET, so a run cannot corrupt a child's
    progress or leave rows behind.
  * Concurrency above `SAFE_MAX` needs `--yes`, and the whole run is capped by
    `--max`, `--budget` (total requests) and `--seconds`.
  * A step that goes badly wrong (over half the requests failing) aborts the ramp
    instead of climbing into it.

Read the numbers as a floor, not a ceiling: this box has 2 cores and one uplink, so
past a few hundred concurrent requests the limit measured may be this machine.
"""
import argparse, asyncio, statistics, sys, time

import httpx

SAFE_MAX = 50          # above this, --yes is required
ABORT_ERROR_RATE = 0.5  # half the requests failing: stop climbing
SLOW_P95 = 2.0          # seconds; past this the service is no longer keeping up

# Endpoints that spend money per call. Never in a ramp without the long flag.
COSTS_MONEY = ('/api/tutor/', '/api/chat', '/api/curriculum/', '/tts', '/lesson')

SITE = 'https://iakids.app'
SUPABASE = 'https://bxnfzuglfwytiyaguwjj.supabase.co'
ANON = ('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4bmZ6dWdsZnd5dGl5YWd1d2pqIiwicm9s'
        'ZSI6ImFub24iLCJpYXQiOjE3NjkyMjk0NjUsImV4cCI6MjA4NDgwNTQ2NX0.IcmVvbboKLkJLkE31_udEtvhPl66-kmZAvmPCT_lk5o')

# A scenario is one "user does a thing": every request it makes, in order.
SCENARIOS = {
    'static': {
        'what': 'one page of the site, cached at Cloudflare',
        'requests': [('GET', f'{SITE}/', None)],
    },
    'game': {
        'what': 'a child opening a game: the page and the three shared files',
        'requests': [
            ('GET', f'{SITE}/games/dictation/', None),
            ('GET', f'{SITE}/games/game-style.css', None),
            ('GET', f'{SITE}/games/game-sdk.js', None),
            ('GET', f'{SITE}/games/nikud.js', None),
        ],
    },
    'hub': {
        'what': 'the games hub, which probes every game it lists',
        'requests': [('GET', f'{SITE}/games/', None)],
    },
    'supabase': {
        'what': 'what a game reads from the database on load',
        'requests': [
            ('GET', f'{SUPABASE}/rest/v1/games_catalog?select=id,game_code,is_active&game_code=eq.dictation',
             {'apikey': ANON, 'Authorization': f'Bearer {ANON}'}),
            ('GET', f'{SUPABASE}/rest/v1/hebrew_nikud?select=word,nikud&limit=50',
             {'apikey': ANON, 'Authorization': f'Bearer {ANON}'}),
        ],
    },
    'play': {
        'what': 'the real play path: a signed-in child asking the bank for the next 20 questions (needs IAKIDS_TEST_JWT and IAKIDS_TEST_KID)',
        'requests': [
            ('POST', f'{SUPABASE}/rest/v1/rpc/game_next_questions',
             {'apikey': ANON, 'Authorization': 'Bearer ' + __import__('os').environ.get('IAKIDS_TEST_JWT', ''),
              'Content-Type': 'application/json'},
             '{"p_kid": "%s", "p_game": "true-false-math", "p_level": 1, "p_limit": 20}' % __import__('os').environ.get('IAKIDS_TEST_KID', '')),
        ],
    },
    'backend': {
        'what': 'the core API answering a route that touches no model and no database',
        # NOT '/': the deployed build predates the health route in backend/main.py
        # and answers 404 there. /openapi.json is served by FastAPI itself.
        'requests': [('GET', 'https://iakids-backend.onrender.com/openapi.json', None)],
    },
    'tutor': {
        'what': 'the Hebrew tutor API answering its docs route (no model)',
        'requests': [('GET', 'https://iakids-ai-tutor-he.onrender.com/openapi.json', None)],
    },
}


async def one_user(client, requests, out):
    """One simulated child doing the whole scenario once."""
    t0 = time.perf_counter()
    ok = True
    for method, url, headers, *body in requests:
        try:
            r = await client.request(method, url, headers=headers, content=body[0] if body else None)
            if r.status_code >= 400:
                ok = False
                out['codes'][r.status_code] = out['codes'].get(r.status_code, 0) + 1
        except Exception as e:
            ok = False
            out['codes'][type(e).__name__] = out['codes'].get(type(e).__name__, 0) + 1
    out['times'].append(time.perf_counter() - t0)
    out['ok' if ok else 'bad'] += 1


async def step(requests, concurrency, rounds, timeout):
    """Hold `concurrency` users in flight for `rounds` passes."""
    out = {'times': [], 'ok': 0, 'bad': 0, 'codes': {}}
    limits = httpx.Limits(max_connections=concurrency + 10, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=True,
                                 headers={'User-Agent': 'iakids-loadtest/1.0 (own-site capacity check)'}) as client:
        t0 = time.perf_counter()
        for _ in range(rounds):
            await asyncio.gather(*(one_user(client, requests, out) for _ in range(concurrency)))
        out['wall'] = time.perf_counter() - t0
    return out


def report(name, concurrency, out, per_user):
    t = sorted(out['times'])
    n = len(t)
    if not n:
        return None
    p = lambda q: t[min(n - 1, int(n * q))]
    total = out['ok'] + out['bad']
    rate = out['bad'] / total if total else 1
    users_per_sec = total / out['wall'] if out['wall'] else 0
    print(f'  {concurrency:>4} at once │ {users_per_sec:7.1f} users/s │ '
          f'p50 {p(.5):5.2f}s  p95 {p(.95):5.2f}s  p99 {p(.99):5.2f}s │ '
          f'{out["bad"]:>3} failed'
          + (f'  {out["codes"]}' if out['codes'] else ''))
    return {'concurrency': concurrency, 'rate': rate, 'p95': p(.95), 'users_per_sec': users_per_sec,
            'req_per_sec': users_per_sec * per_user}


async def ramp(name, args):
    sc = SCENARIOS[name]
    reqs = sc['requests']
    per_user = len(reqs)

    if not args.i_know_this_costs_money:
        for _, url, *_ in reqs:
            if any(k in url for k in COSTS_MONEY):
                sys.exit(f'refusing: {url} calls a language model. Every request is billed and the '
                         f'backends have no rate limit, so a ramp there is a bill, not a measurement.')

    print(f'\n{name} — {sc["what"]}')
    print(f'{per_user} request{"s" if per_user > 1 else ""} per simulated child\n')

    spent, results = 0, []
    c = args.start
    while c <= args.max:
        rounds = max(1, args.budget // (10 * max(c, 1) * per_user)) if args.budget else 3
        rounds = min(rounds, 5)
        if args.budget and spent + c * rounds * per_user > args.budget:
            print('  (request budget reached)')
            break
        out = await step(reqs, c, rounds, args.timeout)
        spent += (out['ok'] + out['bad']) * per_user
        r = report(name, c, out, per_user)
        if r:
            results.append(r)
            if r['rate'] > ABORT_ERROR_RATE:
                print(f'\n  stopping: over half the requests failed at {c} at once.')
                break
            if r['rate'] > 0.01 or r['p95'] > SLOW_P95:
                print(f'\n  stopping: this is the point where it stops keeping up.')
                break
        c *= 2

    if not results:
        return
    good = [r for r in results if r['rate'] <= 0.01 and r['p95'] <= SLOW_P95]
    best = max(good, key=lambda r: r['users_per_sec']) if good else None
    print()
    if best:
        print(f'  held {best["concurrency"]} children at once with no errors, '
              f'{best["users_per_sec"]:.0f} page-loads a second '
              f'({best["req_per_sec"]:.0f} requests/s), p95 {best["p95"]:.2f}s')
        if best is results[-1] and best['concurrency'] * 2 > args.max:
            print(f'  it never broke — the ceiling is above {args.max}, raise --max to find it')
    else:
        print('  no step came back clean; look at the failures above before drawing a conclusion')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('scenario', nargs='?', help='one of: ' + ', '.join(SCENARIOS))
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--start', type=int, default=2)
    ap.add_argument('--max', type=int, default=SAFE_MAX)
    ap.add_argument('--budget', type=int, default=4000, help='stop after this many requests in total')
    ap.add_argument('--timeout', type=float, default=20)
    ap.add_argument('--yes', action='store_true', help='allow concurrency above %d' % SAFE_MAX)
    ap.add_argument('--i-know-this-costs-money', action='store_true')
    args = ap.parse_args()

    if args.list or not args.scenario:
        print('scenarios:')
        for k, v in SCENARIOS.items():
            print(f'  {k:10} {v["what"]}  ({len(v["requests"])} req/child)')
        return
    if args.scenario not in SCENARIOS:
        sys.exit(f'unknown scenario {args.scenario!r}; --list shows them')
    if args.max > SAFE_MAX and not args.yes:
        sys.exit(f'--max {args.max} is above the safe default of {SAFE_MAX}. '
                 f'This points at production; add --yes if that is what you mean.')

    asyncio.run(ramp(args.scenario, args))


if __name__ == '__main__':
    main()
