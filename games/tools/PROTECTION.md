# Protecting the games from being copied

## What cannot be prevented, and why

Every game here is a static HTML file served publicly from GitHub Pages. One command
gets the whole thing:

```
curl https://iakids.app/games/dictation/index.html
```

There is no change to the code that stops that. A browser has to receive the game in
order to run it, and whatever a browser receives, a person can save. Disabling
right-click, blocking F12, obfuscating the JavaScript — all of it is removed in
minutes by anyone who wants to, and it costs real things: harder debugging, a worse
experience for a curious child, and broken tooling.

So the goal is not to make copying impossible. It is to make the copy **not work**,
make it **provable**, and make **mass scraping expensive**. Those three are achievable.

---

## 1. A copy does not work — `IAKidsGuard` (in `game-sdk.js`)

`IAKidsGame.init()` checks the hostname against an allowlist before a game starts. On
a host that is not on it, the game never runs: the child sees a notice and a link to
the real site instead.

This defeats the copy that actually happens — someone downloads the folder and points
their own domain at it. It does not defeat someone who edits the JavaScript, and it is
not meant to.

**The allowlist is in `IAKidsGuard.ALLOWED`. Add a new domain there before pointing it
at the site**, or every game will refuse to run on it. The failure is a visible notice
with a link home, never a blank page, so a mistake is obvious rather than silent.

Currently allowed: `iakids.app`, `www.iakids.app`, `smarts-brains.online`,
`www.smarts-brains.online`, `varonrot.github.io`, `localhost`, `127.0.0.1`, and
`file://` for opening a game straight off disk.

## 2. A copy is provable — the canary

`IAKidsGuard.CANARY` and the copyright banner at the top of `game-sdk.js` are stamped
into every copy. A file carrying that string came from here, whatever name is on the
page serving it. That is what a hosting provider wants to see in a takedown notice,
and it is why the banner must not be minified away.

`LICENSE` at the repository root states the terms the takedown rests on.

## 3. Mass scraping is expensive — Cloudflare

**This is the only layer that stops an automated scraper, and it is a settings change,
not code.** The site is already behind Cloudflare, so it is available now.

In the Cloudflare dashboard for `iakids.app`:

| Where | What | Why |
|---|---|---|
| Security → Bots | **Bot Fight Mode** on | Challenges the crawlers that ignore robots.txt |
| Security → WAF → Rate limiting | 60 requests / minute per IP on `/games/*` | A child plays a handful of games an hour; a scraper pulls hundreds of files a minute |
| Scrape Shield | **Hotlink Protection** on | Stops another site embedding the images and audio |
| Security → WAF → Custom rules | Block `User-Agent` containing `HTTrack`, `wget`, `curl`, `python-requests` | The site-copiers, which announce themselves |

A rate limit is the single highest-value item: it is the difference between copying
100 games in a minute and needing two hours and a rotating IP pool.

## 4. Polite crawlers are asked to stay out — `robots.txt`

`robots.txt` blocks the AI training crawlers (GPTBot, ClaudeBot, CCBot,
Google-Extended, Bytespider, PerplexityBot and others) and the site-copiers (HTTrack,
wget, WebCopier). Search engines are still welcome, because the site needs to be found.

This is a request. A crawler that ignores it is Cloudflare's problem, which is why
item 3 matters more than this one.

---

## What is worth doing next, in order

1. **Turn on the Cloudflare rate limit.** Ten minutes, and it is the biggest single
   gain on this page.
2. **Keep the valuable content server-side.** The question bank already lives in
   Supabase behind RLS, and a copied game cannot read another child's rows. The word
   lists and generators, though, are in the JavaScript and therefore public. If a game's
   content is genuinely the asset, serve it from the backend per question rather than
   shipping the whole bank to the browser.
3. **Watch for copies.** A search for a distinctive string from a game — a help text,
   an unusual word list — finds a rehosted copy faster than anything automated.

## What not to do

- **Do not obfuscate or minify the shared files.** It would break the nikud checker,
  the harvester and `bump-sdk.py`, all of which read the source, and it stops nobody.
- **Do not disable right-click or the developer tools.** It does not protect anything,
  it annoys the parent who wanted to check what their child is using, and every browser
  offers "view source" from a menu anyway.
- **Do not put a secret in the client.** Anything the browser holds is public: that is
  why the Supabase key in `game-sdk.js` is the publishable one and RLS does the work.
