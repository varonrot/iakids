#!/usr/bin/env node
/**
 * harvest.mjs — run a game's own question generator and collect its output.
 *
 * The bank (supabase/migrations/20260908_game_question_bank.sql) otherwise
 * only fills as children play, which is slow and leaves quiet games empty.
 * This runs each game's generator here instead and writes the questions to
 * JSON for backend/seed_questions.py to upload as source='seed'.
 *
 * How it works, and why it generalises across ~90 games without per-game code:
 * a game hands its generator to the SDK as a zero-argument closure —
 *
 *     await game.newQuestion(() => makeQuestion(lvl), x => x.word)
 *
 * — with the level already captured. So a stub SDK whose newQuestion() calls
 * that closure a few hundred times and keeps the distinct results harvests the
 * game without knowing anything about its internals. The page runs against
 * shimmed browser globals; nothing is rendered and nothing is stored.
 *
 *     node harvest.mjs --game rhymes --per-level 200
 *     node harvest.mjs --all --out /tmp/seed.json
 *     node harvest.mjs --all --quiet --out /tmp/seed.json
 *
 * Games that fail are reported and skipped — they simply stay generator-only,
 * which is the behaviour they have today.
 */

import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const GAMES_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const LEVELS = [1, 2, 3];
const DEFAULT_PER_LEVEL = 200;
const TRIES_FACTOR = 40;      // generator attempts per wanted question
const MAX_MS_PER_LEVEL = 5000;

// Same key order as IAKidsBank.answerOf in game-sdk.js, so a seeded row's
// `answer` column matches what a played row would have carried.
const ANSWER_KEYS = ['ans', 'answer', 'correct', 'result', 'truth', 'sign', 'target'];

const HARVEST_DONE = Symbol('harvest-done');

const OPTION_KEYS = ['options', 'choices', 'answers', 'opts', 'alternatives'];
const INDEX_KEYS = ['correctIdx', 'correctIndex', 'answerIdx', 'correct'];

function answerOf(q) {
  if (!q || typeof q !== 'object') return null;
  for (const k of ANSWER_KEYS) {
    if (q[k] !== undefined && q[k] !== null && typeof q[k] !== 'object') return String(q[k]);
  }
  // Many games record the answer as an index into their options list; resolve
  // it, so the verifier has a concrete answer to check rather than a number.
  const options = OPTION_KEYS.map((k) => q[k]).find((v) => Array.isArray(v) && v.length);
  if (options) {
    for (const k of INDEX_KEYS) {
      const i = q[k];
      if (Number.isInteger(i) && i >= 0 && i < options.length && typeof options[i] !== 'object') {
        return String(options[i]);
      }
    }
  }
  return null;
}

/** A question must survive a JSON round trip unchanged — no functions, no DOM. */
function jsonSafe(q) {
  if (!q || typeof q !== 'object' || Array.isArray(q)) return null;
  let clone;
  try { clone = JSON.parse(JSON.stringify(q)); } catch { return null; }
  const before = Object.keys(q).sort().join();
  const after = Object.keys(clone).sort().join();
  return before === after ? clone : null;   // a dropped key means a function or DOM node
}

/** A forgiving stand-in for a DOM element: absorbs any property or method. */
function fakeEl() {
  const target = function () {};
  return new Proxy(target, {
    get(_t, key) {
      if (key === 'classList' || key === 'style' || key === 'dataset') return fakeEl();
      if (key === 'children' || key === 'childNodes') return fakeList();
      if (key === 'querySelectorAll') return () => fakeList();
      if (key === 'textContent' || key === 'innerHTML' || key === 'value' || key === 'id') return '';
      if (key === 'hidden' || key === 'disabled') return false;
      if (key === Symbol.toPrimitive || key === 'toString') return () => '';
      if (key === 'length') return 0;
      if (key === Symbol.iterator) return [][Symbol.iterator].bind([]);
      return fakeEl();
    },
    set() { return true; },
    apply() { return fakeEl(); },
    has() { return true; },
  });
}

/**
 * A stand-in for an SDK object: `real` entries behave, every other property
 * answers with a function that absorbs the call. The SDK gains methods over
 * time and games call them at load; without this the harvester breaks every
 * time one is added.
 */
function stub(real = {}) {
  return new Proxy(real, {
    get(target, key) {
      if (key in target) return target[key];
      if (key === 'then') return undefined;          // must not look thenable
      return () => fakeEl();
    },
    has() { return true; },
  });
}

/**
 * A stand-in for a NodeList. Length is 0 so loops over it do nothing, but an
 * indexed read still yields an element — games routinely write
 * `qsa('.tile')[0].textContent`, which on a plain [] throws.
 */
function fakeList() {
  return new Proxy([], {
    get(target, key) {
      if (key === 'length') return 0;
      if (typeof key === 'string' && /^\d+$/.test(key)) return fakeEl();
      if (key in target) return target[key];
      return () => fakeEl();
    },
  });
}

function makeContext(slug, collector) {
  const noop = () => {};
  const asyncNoop = async () => {};

  const game = {
    _diff: null,
    difficulty(start = 1, max = 3) {
      let raw = start;
      return (this._diff = {
        get level() { return Math.max(1, Math.min(max, Math.round(raw))); },
        right() { raw = Math.min(max + 0.4, raw + 0.25); },
        wrong() { raw = Math.max(1, raw - 0.5); },
      });
    },
    async loadProgress() { return null; },
    async saveProgress() {},
    async clearProgress() {},
    async saveScore() { return true; },
    async getHighScores() { return []; },
    shareButton: () => fakeEl(),
    timer: () => ({ start: noop, stop: noop, pause: noop, resume: noop }),

    // The interception point. `gen` already has this game's level captured.
    newQuestion(gen, keyFn = JSON.stringify, opts = {}) {
      const level = opts.level ?? collector.level;
      const tries = collector.perLevel * TRIES_FACTOR;
      const deadline = Date.now() + MAX_MS_PER_LEVEL;
      for (let i = 0; i < tries && collector.rows.length < collector.perLevel; i++) {
        if ((i & 63) === 0 && Date.now() > deadline) break;
        let q;
        try { q = gen(); } catch { continue; }
        const payload = jsonSafe(q);
        if (!payload) { collector.unserialisable++; continue; }
        let key;
        try { key = String(keyFn(q)); } catch { continue; }
        if (!key || key.length > 500 || collector.seen.has(key)) continue;
        collector.seen.add(key);
        collector.rows.push({ game_code: slug, level, qkey: key, payload, answer: answerOf(payload) });
      }
      throw HARVEST_DONE;   // stop the game; we have what we came for
    },
  };

  const ctx = {
    console: { log: noop, warn: noop, error: noop, info: noop },
    setTimeout: (fn) => { void fn; return 0; },   // never actually fire: no game loop here
    clearTimeout: noop, setInterval: () => 0, clearInterval: noop,
    requestAnimationFrame: () => 0, cancelAnimationFrame: noop,
    Promise, Date, Math, JSON, Set, Map, Array, Object, String, Number, Boolean,
    Error, RegExp, Symbol, parseInt, parseFloat, isNaN, isFinite, encodeURIComponent,
    decodeURIComponent, URLSearchParams, Intl, structuredClone,
    localStorage: { getItem: () => null, setItem: noop, removeItem: noop },
    sessionStorage: { getItem: () => null, setItem: noop, removeItem: noop },
    indexedDB: { open: () => fakeEl() },
    location: { search: '', href: `https://iakids.app/games/${slug}/`, hostname: 'iakids.app' },
    navigator: { language: 'he', clipboard: { writeText: asyncNoop }, share: asyncNoop },
    alert: noop, confirm: () => true, prompt: () => null, fetch: () => Promise.reject(new Error('offline')),
    speechSynthesis: { speak: noop, cancel: noop, getVoices: () => [] },
    MutationObserver: function () { return { observe: noop, disconnect: noop, takeRecords: () => [] }; },
    IntersectionObserver: function () { return { observe: noop, disconnect: noop, unobserve: noop }; },
    ResizeObserver: function () { return { observe: noop, disconnect: noop, unobserve: noop }; },
    matchMedia: () => ({ matches: false, addEventListener: noop, removeEventListener: noop, addListener: noop }),
    getComputedStyle: () => fakeEl(),
    CustomEvent: function () { return fakeEl(); },
    Event: function () { return fakeEl(); },
    DOMParser: function () { return { parseFromString: () => fakeEl() }; },
    performance: { now: () => Date.now() },
    crypto: { randomUUID: () => '00000000-0000-4000-8000-000000000000', getRandomValues: (a) => a },
    btoa: (x) => Buffer.from(String(x), 'binary').toString('base64'),
    atob: (x) => Buffer.from(String(x), 'base64').toString('binary'),
    TextEncoder, TextDecoder, Buffer,
    addEventListener: noop, removeEventListener: noop, dispatchEvent: noop,
    scrollTo: noop, postMessage: noop, open: () => null, close: noop, focus: noop, blur: noop,
    innerWidth: 1024, innerHeight: 768, devicePixelRatio: 1,
    SpeechSynthesisUtterance: function () { return fakeEl(); },
    AudioContext: function () { return fakeEl(); },
    Audio: function () { return fakeEl(); },
    Image: function () { return fakeEl(); },

    document: new Proxy({}, {
      get(_t, key) {
        if (key === 'querySelectorAll' || key === 'getElementsByClassName'
            || key === 'getElementsByTagName') return () => fakeList();
        if (key === 'addEventListener' || key === 'removeEventListener') return noop;
        if (key === 'documentElement' || key === 'body' || key === 'head') return fakeEl();
        if (key === 'readyState') return 'complete';
        return () => fakeEl();
      },
      has() { return true; },
    }),

    // SDK surface. Only newQuestion does real work; the rest must merely not
    // throw, and must return something a game can use where it inspects it.
    IAKidsGame: stub({ async init() { return game; }, async getActiveKidContext() { return null; } }),
    IAKidsCoins: stub({
      RIGHT: 10, WRONG: -5, COMPLETE: 25, STREAK_EVERY: 3, STREAK_BONUS: 5,
      mount: noop, add: asyncNoop, get: async () => 0, right: asyncNoop, wrong: asyncNoop,
    }),
    IAKidsFX: stub(),
    IAKidsHelp: stub({ mount: noop, open: noop, close: noop }),
    IAKidsShare: stub({ button: () => fakeEl(), share: asyncNoop }),
    IAKidsTimer: stub({ create: () => ({ start: noop, stop: noop, pause: noop, resume: noop }),
                        secondsFor: () => 30 }),
    IAKidsLang: stub({
      t: (o) => (o && typeof o === 'object' ? (o.he ?? o.en ?? Object.values(o)[0] ?? '') : (o ?? '')),
      current: () => 'he', dir: () => 'rtl', ui: () => ({}),
    }),
    IAKidsActivity: stub({ start: async () => null, correct: noop, wrong: noop,
                           skipped: noop, hint: noop, finish: asyncNoop }),
    IAKidsBank: stub(),
    IAKidsTournament: stub({ active: () => null, isActive: () => false }),
    IAKidsSkills: stub(),
    IAKidsAuth: stub({ user: async () => null, signedIn: () => false }),
    IAKidsCloud: stub({ enabled: () => false }),
  };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx; ctx.top = ctx; ctx.parent = ctx;
  return ctx;
}

/** Inline <script> blocks, in order. External src= tags are the SDK, which we stub. */
function inlineScripts(html) {
  const out = [];
  const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html))) {
    if (/\bsrc\s*=/i.test(m[1])) continue;
    if (/\btype\s*=\s*["']?(?!text\/javascript|module)/i.test(m[1])) continue;
    out.push(m[2]);
  }
  return out;
}

async function harvestGame(slug, perLevel, verbose) {
  const file = path.join(GAMES_DIR, slug, 'index.html');
  if (!fs.existsSync(file)) return { slug, error: 'no index.html' };
  const html = fs.readFileSync(file, 'utf8');
  if (!/newQuestion/.test(html)) return { slug, skipped: 'does not use newQuestion' };

  const rows = [];
  const seen = new Set();
  let unserialisable = 0;

  for (const level of LEVELS) {
    const collector = { rows: [], seen, level, perLevel, unserialisable: 0 };
    const ctx = makeContext(slug, collector);
    vm.createContext(ctx);
    try {
      for (const src of inlineScripts(html)) {
        vm.runInContext(src, ctx, { timeout: 10000 });
      }
    } catch (err) {
      if (level === LEVELS[0]) return { slug, error: `script failed: ${err.message}` };
      continue;
    }

    let start;
    try { start = vm.runInContext('typeof start === "function" ? start : null', ctx); } catch { start = null; }
    if (!start) return { slug, error: 'no start() entry point' };

    try {
      const result = start(level);
      if (result && typeof result.catch === 'function') {
        await result.catch((e) => { if (e !== HARVEST_DONE) throw e; });
      }
    } catch (err) {
      if (err !== HARVEST_DONE) {
        if (level === LEVELS[0]) return { slug, error: `start(${level}) failed: ${String(err.message || err)}` };
        continue;
      }
    }
    unserialisable += collector.unserialisable;
    rows.push(...collector.rows);
    if (verbose) process.stderr.write(`    level ${level}: ${collector.rows.length}\n`);
  }

  if (!rows.length) {
    return { slug, error: unserialisable ? 'questions are not JSON-serialisable' : 'generator produced nothing' };
  }
  return { slug, rows };
}

// A game's start() typically fires next() without awaiting it, so our sentinel
// escapes as an unhandled rejection on a promise we never see. Swallow exactly
// that one; anything else still crashes the run, as it should.
let strayRejections = 0;
process.on('unhandledRejection', (reason) => {
  if (reason === HARVEST_DONE) return;
  // A game firing an un-awaited async call that fails against the shims is
  // noise, not a harvest failure — the questions are collected synchronously.
  strayRejections++;
});

async function main() {
  const argv = process.argv.slice(2);
  const flag = (name, fallback) => {
    const i = argv.indexOf(name);
    return i === -1 ? fallback : argv[i + 1];
  };
  const perLevel = parseInt(flag('--per-level', String(DEFAULT_PER_LEVEL)), 10);
  const out = flag('--out', null);
  const quiet = argv.includes('--quiet');
  const verbose = argv.includes('--verbose');

  let slugs;
  if (argv.includes('--all')) {
    slugs = fs.readdirSync(GAMES_DIR, { withFileTypes: true })
      .filter((d) => d.isDirectory() && fs.existsSync(path.join(GAMES_DIR, d.name, 'index.html')))
      .map((d) => d.name).sort();
  } else if (flag('--game', null)) {
    slugs = [flag('--game', null)];
  } else {
    console.error('usage: harvest.mjs (--game <slug> | --all) [--per-level N] [--out file.json] [--quiet]');
    process.exit(2);
  }

  const all = [];
  const failed = [];
  let skipped = 0;
  for (const slug of slugs) {
    if (verbose) process.stderr.write(`  ${slug}\n`);
    let result;
    try {
      result = await harvestGame(slug, perLevel, verbose);
    } catch (err) {
      result = { slug, error: `harvester crashed: ${err.message}` };
    }
    if (result.skipped) { skipped++; continue; }
    if (result.error) { failed.push(result); if (!quiet) process.stderr.write(`  FAIL ${slug}: ${result.error}\n`); continue; }
    all.push(...result.rows);
    if (!quiet) process.stderr.write(`  ok   ${slug}: ${result.rows.length}\n`);
  }

  const games = new Set(all.map((r) => r.game_code));
  process.stderr.write(`\nharvested ${all.length} questions from ${games.size} game(s); `
    + `${failed.length} failed, ${skipped} do not use newQuestion\n`);

  if (out) {
    fs.writeFileSync(out, JSON.stringify(all, null, 1));
    process.stderr.write(`wrote ${out}\n`);
  } else {
    process.stdout.write(JSON.stringify(all, null, 1));
  }
}

main();
