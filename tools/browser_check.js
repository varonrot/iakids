/**
 * Load the site in a real browser and report what breaks.
 *
 *   node tools/browser_check.js                          # the mirror
 *   node tools/browser_check.js https://iakids.app       # after Cloudflare
 *
 * What the static CSP check cannot see: a URL a script builds at runtime, a module
 * that imports another module, a font a stylesheet pulls in. A browser sees all of
 * it, so this opens each page, waits for the network to settle, gives the page a
 * moment to do its own work, and collects:
 *
 *   - every CSP refusal ("Refused to load…"), which is the thing we are testing
 *   - every console error and every uncaught exception
 *   - every request that failed outright
 *
 * A page that a signed-out visitor sees is all this can reach; the workspace behind
 * a login shows its sign-in screen, which still loads the same scripts, styles and
 * fonts — which is what a CSP governs.
 *
 * Needs playwright's chromium, installed once:
 *   npx playwright@1.49.1 install --with-deps chromium
 */
// playwright is not a dependency of this repo — it is installed wherever the person
// running this put it. NODE_PATH, or a sibling node_modules, both work.
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');

const BASE = (process.argv[2] || 'https://smarts-brains.online').replace(/\/$/, '');
const PAGES = [
  ['/he/games/workspace/', 'the workspace'],
  ['/games/', 'the games hub'],
  ['/games/dictation/', 'a game'],
  ['/games/quiz-maker/', 'the quiz maker'],
  ['/games/champions/', 'the champions page'],
  ['/he/parent-panel/', 'the parent panel'],
  ['/he/', 'the Hebrew landing page'],
  ['/', 'the Spanish landing page'],
];

// Noise that is not ours and not a CSP problem: a favicon that is not there, an
// analytics beacon a blocker ate, the Supabase 401 a signed-out page expects.
const IGNORE = [
  /favicon\.ico/i,
  /Failed to load resource: the server responded with a status of 40[13]/i,
  /net::ERR_ABORTED/i,
];
const isCsp = t => /Refused to (load|connect|execute|apply|frame)/i.test(t)
                || /Content Security Policy/i.test(t);

(async () => {
  const browser = await chromium.launch();
  let cspTotal = 0, errTotal = 0;

  for (const [path, label] of PAGES) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    const csp = [], errors = [], failed = [];

    page.on('console', m => {
      if (m.type() !== 'error') return;
      const t = m.text();
      if (IGNORE.some(re => re.test(t))) return;
      (isCsp(t) ? csp : errors).push(t);
    });
    page.on('pageerror', e => errors.push('uncaught: ' + e.message));
    page.on('requestfailed', r => {
      const why = (r.failure() && r.failure().errorText) || '';
      const line = `${r.url()} — ${why}`;
      if (IGNORE.some(re => re.test(line))) return;
      (/blockedbycsp|blockedbyclient/i.test(why) ? csp : failed).push(line);
    });

    try {
      await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 45000 });
      await page.waitForTimeout(3500);          // let the page's own scripts run
    } catch (e) {
      errors.push('navigation: ' + e.message.split('\n')[0]);
    }

    const title = (await page.title().catch(() => '')) || '—';
    const bodyLen = await page.evaluate(() => document.body ? document.body.innerText.length : 0).catch(() => 0);
    cspTotal += csp.length; errTotal += errors.length;

    const mark = csp.length ? '\x1b[31mCSP\x1b[0m' : (errors.length ? '\x1b[33m err\x1b[0m' : '\x1b[32m  ok\x1b[0m');
    console.log(`${mark}  ${path.padEnd(24)} ${String(bodyLen).padStart(6)} chars of text   \x1b[2m${title.slice(0, 40)}\x1b[0m`);
    for (const t of csp)    console.log(`       \x1b[31mCSP\x1b[0m ${t.slice(0, 150)}`);
    for (const t of errors) console.log(`       \x1b[33merr\x1b[0m ${t.slice(0, 150)}`);
    for (const t of failed) console.log(`       \x1b[2mnet ${t.slice(0, 150)}\x1b[0m`);

    await ctx.close();
  }

  await browser.close();
  console.log(`\n${cspTotal} CSP refusals, ${errTotal} console errors across ${PAGES.length} pages.`);
  process.exit(cspTotal ? 1 : 0);
})();
