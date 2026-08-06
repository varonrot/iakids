/**
 * iakids game SDK — shared interface for all games under /games/<slug>/.
 * Each game gets its OWN IndexedDB database: iakids_game_<slug>.
 * Stores: 'scores' (append-only score history), 'kv' (progress slot).
 *
 * Usage:
 *   const game = await IAKidsGame.init('true-false-math');
 *   await game.saveScore(850, {level: 3});
 *   const top = await game.getHighScores(10);
 *   await game.saveProgress({level: 3});
 *   const p = await game.loadProgress();
 *   game.complete(850); // notify hub/workspace
 */

// Cloud config lives here (not a separate <script> per page) so every one of
// the 100 games has it, not just the hub/champions — IAKidsAuth/IAKidsCloud
// need it wherever game.complete() can actually fire. apiKey/publishable key
// are not secrets by design (Firebase/Supabase docs) — real protection is
// Firebase's Authorized Domains list and Supabase's RLS policies.
const FIREBASE_CONFIG = {
  apiKey: 'AIzaSyDkG_TyCebc-MDvWZWYyVkvDg8owErIWCA',
  authDomain: 'smarts-brains.firebaseapp.com',
  projectId: 'smarts-brains',
  storageBucket: 'smarts-brains.firebasestorage.app',
  messagingSenderId: '48287114684',
  appId: '1:48287114684:web:495b67e4b3ce03d3bf37b9',
};
const SUPABASE_CONFIG = {
  url: 'https://bxnfzuglfwytiyaguwjj.supabase.co',
  publishableKey: 'sb_publishable_L3yZe3EAiTA5lEpDky1eXA_j6ERXAdc',
};
/**
 * IAKidsActivity
 * שומר הפעלה אחת של משחק בטבלת kid_game_sessions.
 *
 * ההפעלה נוצרת כאשר המשחק מתחיל בפועל באמצעות IAKidsGame.init().
 * במהלך המשחק מעדכנים את המדדים בזיכרון.
 * בסיום נשלחת פעולת UPDATE אחת ל-Supabase.
 */
const IAKidsActivity = {
  _client: null,
  _sessionId: null,
  _gameId: null,
  _kidId: null,
  _slug: null,

  _startedAt: null,
  _questionStartedAt: null,

  _questionsCount: 0,
  _correctAnswers: 0,
  _wrongAnswers: 0,
  _skippedAnswers: 0,
  _hintsUsed: 0,

  _currentStreak: 0,
  _bestCorrectStreak: 0,

  _responseTimes: [],
  _difficulty: 1,
  _metadata: {},
  _finished: false,

  async _getClient() {
    if (this._client) return this._client;

    const { createClient } =
      await import('https://esm.sh/@supabase/supabase-js@2');

    this._client = createClient(
      SUPABASE_CONFIG.url,
      SUPABASE_CONFIG.publishableKey
    );

    return this._client;
  },

  _readLessonContext() {
    const params = new URLSearchParams(location.search);

    const learningLessonId =
      params.get('learning_lesson_id');

    const unitLessonId =
      params.get('unit_lesson_id');

    return {
      learning_lesson_id:
        learningLessonId
          ? Number(learningLessonId)
          : null,

      unit_lesson_id:
        unitLessonId
          ? Number(unitLessonId)
          : null,
    };
  },

  async start(slug, options = {}) {
    try {
      this._reset();

      this._slug = slug;
      this._startedAt = Date.now();
      this._questionStartedAt = Date.now();

      this._difficulty =
        Number(options.difficulty ?? 1);

      this._questionsCount =
        Number(options.questionsCount ?? 0);

      this._metadata =
        options.metadata || {};

      this._kidId =
        localStorage.getItem('active_kid_id');

      if (!this._kidId) {
        console.warn(
          '[IAKidsActivity] active_kid_id not found'
        );

        return null;
      }

      const client =
        await this._getClient();

      const {
        data: { session },
        error: sessionError
      } =
        await client.auth.getSession();

      if (
        sessionError ||
        !session?.user
      ) {
        console.warn(
          '[IAKidsActivity] Supabase session not found',
          sessionError
        );

        return null;
      }

const {
  data: gameRow,
  error: gameError
} =
  await client
    .from('games_catalog')
    .select('id, game_code, is_active')
    .eq('game_code', slug)
    .maybeSingle();

      if (
        gameError ||
        !gameRow
      ) {
        console.warn(
          '[IAKidsActivity] Game not found in games_catalog:',
          slug,
          gameError
        );

        return null;
      }

      this._gameId =
        gameRow.id;

      const lessonContext =
        this._readLessonContext();

      const {
        data: insertedSession,
        error: insertError
      } =
        await client
          .from('kid_game_sessions')
          .insert({
            kid_id:
              this._kidId,

            game_id:
              this._gameId,

            learning_lesson_id:
              lessonContext.learning_lesson_id,

            unit_lesson_id:
              lessonContext.unit_lesson_id,

            difficulty:
              this._difficulty,

            questions_count:
              this._questionsCount,

            completed:
              false,

            ended_reason:
              'interrupted',

            metadata:
              this._metadata
          })
          .select('id')
          .single();

      if (
        insertError ||
        !insertedSession
      ) {
        console.error(
          '[IAKidsActivity] Failed to create session:',
          insertError
        );

        return null;
      }

      this._sessionId =
        insertedSession.id;

      console.log(
        '[IAKidsActivity] Session started:',
        {
          sessionId:
            this._sessionId,

          kidId:
            this._kidId,

          gameId:
            this._gameId,

          slug:
            this._slug
        }
      );

      return this._sessionId;

    } catch (error) {
      console.error(
        '[IAKidsActivity] start error:',
        error
      );

      return null;
    }
  },

  configure(options = {}) {
    if (
      options.difficulty !== undefined
    ) {
      this._difficulty =
        Number(options.difficulty);
    }

    if (
      options.questionsCount !== undefined
    ) {
      this._questionsCount =
        Number(options.questionsCount);
    }

    if (
      options.metadata
    ) {
      this._metadata = {
        ...this._metadata,
        ...options.metadata
      };
    }
  },

  questionStarted() {
    this._questionStartedAt =
      Date.now();
  },

  _recordResponseTime() {
    if (!this._questionStartedAt) return;

    const responseTime =
      Date.now() -
      this._questionStartedAt;

    if (
      Number.isFinite(responseTime) &&
      responseTime >= 0
    ) {
      this._responseTimes.push(
        responseTime
      );
    }

    this._questionStartedAt =
      Date.now();
  },

  correct() {
    this._recordResponseTime();

    this._correctAnswers += 1;
    this._currentStreak += 1;

    this._bestCorrectStreak =
      Math.max(
        this._bestCorrectStreak,
        this._currentStreak
      );
  },

  wrong() {
    this._recordResponseTime();

    this._wrongAnswers += 1;
    this._currentStreak = 0;
  },

  skipped() {
    this._recordResponseTime();

    this._skippedAnswers += 1;
    this._currentStreak = 0;
  },

  hint() {
    this._hintsUsed += 1;
  },

  async finish({
    score = 0,
    maxScore = 0,
    completed = true,
    endedReason = 'completed',
    performanceScore = null,
    metadata = {}
  } = {}) {
    if (
      this._finished ||
      !this._sessionId
    ) {
      return;
    }

    this._finished = true;

    try {
      const client =
        await this._getClient();

const attemptsCount =
  this._correctAnswers +
  this._wrongAnswers +
  this._skippedAnswers;

const completedQuestions =
  this._correctAnswers +
  this._skippedAnswers;

const denominator =
  attemptsCount > 0
    ? attemptsCount
    : this._questionsCount;

      const accuracyPercent =
        denominator > 0
          ? (
              this._correctAnswers /
              denominator
            ) * 100
          : 0;

      const durationSeconds =
        this._startedAt
          ? Math.max(
              0,
              Math.round(
                (
                  Date.now() -
                  this._startedAt
                ) / 1000
              )
            )
          : 0;

      const averageResponseMs =
        this._responseTimes.length
          ? Math.round(
              this._responseTimes.reduce(
                (sum, value) =>
                  sum + value,
                0
              ) /
              this._responseTimes.length
            )
          : null;

      const finalPerformance =
        performanceScore !== null
          ? Number(performanceScore)
          : Math.round(
              Math.max(
                0,
                Math.min(
                  100,
                  accuracyPercent -
                  (
                    this._hintsUsed * 2
                  )
                )
              )
            );

      const finalMetadata = {
        ...this._metadata,
        ...metadata,
        language:
          typeof IAKidsLang !== 'undefined'
            ? IAKidsLang.code
            : document.documentElement.lang,

        timer_enabled:
          typeof IAKidsTimer !== 'undefined'
            ? IAKidsTimer.enabled
            : null,

        game_slug:
          this._slug
      };

      const {
        error
      } =
        await client
          .from('kid_game_sessions')
          .update({
            difficulty:
              this._difficulty,

questions_count:
  this._questionsCount,

            correct_answers:
              this._correctAnswers,

            wrong_answers:
              this._wrongAnswers,

            skipped_answers:
              this._skippedAnswers,

            hints_used:
              this._hintsUsed,

            score:
              Number(score) || 0,

            max_score:
              Number(maxScore) || 0,

            accuracy_percent:
              Number(
                accuracyPercent.toFixed(2)
              ),

            duration_seconds:
              durationSeconds,

            average_response_ms:
              averageResponseMs,

            best_correct_streak:
              this._bestCorrectStreak,

            completed:
              Boolean(completed),

            ended_reason:
              endedReason,

            performance_score:
              finalPerformance,

            metadata:
              finalMetadata,

            completed_at:
              completed
                ? new Date().toISOString()
                : null
          })
          .eq(
            'id',
            this._sessionId
          );

      if (error) {
        console.error(
          '[IAKidsActivity] Failed to finish session:',
          error
        );

        this._finished = false;
        return;
      }

      console.log(
        '[IAKidsActivity] Session completed:',
        {
          sessionId:
            this._sessionId,

          score,

          accuracyPercent,

          durationSeconds,

          correctAnswers:
            this._correctAnswers,

          wrongAnswers:
            this._wrongAnswers
        }
      );

    } catch (error) {
      this._finished = false;

      console.error(
        '[IAKidsActivity] finish error:',
        error
      );
    }
  },

  _reset() {
    this._sessionId = null;
    this._gameId = null;
    this._kidId = null;
    this._slug = null;

    this._startedAt = null;
    this._questionStartedAt = null;

    this._questionsCount = 0;
    this._correctAnswers = 0;
    this._wrongAnswers = 0;
    this._skippedAnswers = 0;
    this._hintsUsed = 0;

    this._currentStreak = 0;
    this._bestCorrectStreak = 0;

    this._responseTimes = [];
    this._difficulty = 1;
    this._metadata = {};
    this._finished = false;
  }
};
const IAKidsGame = {
  async init(slug) {
    if (!/^[a-z0-9-]+$/.test(slug)) throw new Error('bad slug: ' + slug);
    IAKidsActivity.start(slug).catch(error => {
  console.warn(
    '[IAKidsGame] Activity session was not started:',
    error
  );
});
    if (!document.getElementById('iakids-home-btn')) {
      const home = document.createElement('a');
      home.id = 'iakids-home-btn';
      home.href = '../';
      home.title = IAKidsLang.t({ he: 'לכל המשחקים', en: 'All games', es: 'Todos los juegos', de: 'Alle Spiele', pt: 'Todos os jogos' });
      home.textContent = '🏠';
      document.body.appendChild(home);
    }
    const db = await new Promise((resolve, reject) => {
      const req = indexedDB.open('iakids_game_' + slug, 1);
      req.onupgradeneeded = () => {
        req.result.createObjectStore('scores', { keyPath: 'id', autoIncrement: true });
        req.result.createObjectStore('kv');
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });

    const tx = (store, mode, fn) => new Promise((resolve, reject) => {
      const t = db.transaction(store, mode);
      const r = fn(t.objectStore(store));
      t.oncomplete = () => resolve(r.result);
      t.onerror = () => reject(t.error);
    });

    return {
      slug,
      saveScore: async (score, meta) => {
        const player = (await IAKidsCoins._kvGet('player')) || 'אורח';
        return tx('scores', 'readwrite', s =>
          s.add({ score, meta: meta || null, player, ts: Date.now() }));
      },
      getHighScores: async (n = 10) => {
        const all = await tx('scores', 'readonly', s => s.getAll());
        return all.sort((a, b) => b.score - a.score).slice(0, n);
      },
      saveProgress: obj => tx('kv', 'readwrite', s => s.put(obj, 'progress')),
      loadProgress: async () => (await tx('kv', 'readonly', s => s.get('progress'))) ?? null,
      clearProgress: () => tx('kv', 'readwrite', s => s.delete('progress')),
complete(score, options = {}) {
  const msg = {
    type:
      'iakids-game-complete',

    slug,

    score,

    ts:
      Date.now()
  };

  if (window.parent !== window) {
    window.parent.postMessage(
      msg,
      '*'
    );
  }

  window.dispatchEvent(
    new CustomEvent(
      'iakids-game-complete',
      {
        detail:
          msg
      }
    )
  );

  IAKidsCoins.add(
    IAKidsCoins.COMPLETE
  );

  IAKidsFX.celebrate();

  IAKidsShare.onComplete(
    slug,
    score
  );

  IAKidsTournament.onComplete(
    slug,
    score
  );

  IAKidsCloud.recordWin(
    slug,
    score
  );

  IAKidsActivity.finish({
    score,

    maxScore:
      options.maxScore ?? 0,

    completed:
      true,

    endedReason:
      'completed',

    performanceScore:
      options.performanceScore ?? null,

    metadata:
      options.metadata || {}
  }).catch(error => {
    console.warn(
      '[IAKidsGame] Activity finish failed:',
      error
    );
  });
},
      shareButton(score, el) { return IAKidsShare.button(slug, score, el); },
      timer: opts => IAKidsTimer.create(opts),

      /**
       * No-repeat question generator. gen() returns a question object; keyFn
       * derives its identity (default: JSON of the object). Questions the
       * player already got (persisted, last 300) are skipped. When the pool
       * is exhausted, history resets so the game never dead-ends.
       */
      async newQuestion(gen, keyFn = JSON.stringify) {
        if (!this._asked) this._asked = (await tx('kv', 'readonly', s => s.get('asked'))) || [];
        const seen = new Set(this._asked);
        let q = gen();
        for (let i = 0; i < 30 && seen.has(keyFn(q)); i++) q = gen();
        if (seen.has(keyFn(q))) { this._asked = []; } // pool exhausted — reset history
        this._asked.push(keyFn(q));
        if (this._asked.length > 300) this._asked = this._asked.slice(-300);
        tx('kv', 'readwrite', s => s.put(this._asked, 'asked'));
        return q;
      },

      /**
       * Adaptive difficulty: starts at the chosen level, every right answer
       * pushes harder (+0.25), a wrong answer eases off (-0.5).
       *   const diff = game.difficulty(startLevel, maxLevel);
       *   diff.level      // current integer level for the question generator
       *   diff.right() / diff.wrong()
       */
      difficulty(start = 1, max = 3) {
        let raw = start;
        return {
          get level() { return Math.max(1, Math.min(max, Math.round(raw))); },
          right() { raw = Math.min(max + 0.4, raw + 0.25); },
          wrong() { raw = Math.max(1, raw - 0.5); },
        };
      },
    };
  },
};

/**
 * IAKidsCoins — shared coin wallet across ALL games (own DB: iakids_wallet).
 * Standard economy: +10 right, -5 wrong (never below 0), +25 game complete,
 * +5 streak bonus every 3 correct in a row.
 *
 *   IAKidsCoins.mount();               // show coin badge (auto-updates)
 *   await IAKidsCoins.right(btnEl);    // +10 (+streak bonus), coin fly FX
 *   await IAKidsCoins.wrong();         // -5
 *   await IAKidsCoins.get();           // balance
 */
const IAKidsCoins = {
  RIGHT: 10, WRONG: -5, COMPLETE: 25, STREAK_EVERY: 3, STREAK_BONUS: 5,
  _streak: 0,

  _db() {
    return (this._dbp ||= new Promise((resolve, reject) => {
      const req = indexedDB.open('iakids_wallet', 1);
      req.onupgradeneeded = () => req.result.createObjectStore('kv');
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    }));
  },

  async get() {
    const db = await this._db();
    return new Promise(res => {
      const r = db.transaction('kv').objectStore('kv').get('coins');
      r.onsuccess = () => res(r.result || 0);
      r.onerror = () => res(0);
    });
  },

  async add(n) {
    const db = await this._db();
    const total = Math.max(0, (await this.get()) + n);
    await new Promise(res => {
      const t = db.transaction('kv', 'readwrite');
      t.objectStore('kv').put(total, 'coins');
      t.oncomplete = res;
    });
    const el = document.getElementById('iakids-coin-badge');
    if (el) {
      el.querySelector('span').textContent = total;
      el.classList.remove('bump'); void el.offsetWidth;
      el.classList.add('bump');
    }
    return total;
  },

  async right(fromEl) {
    this._streak++;
    let n = this.RIGHT;
    if (this._streak % this.STREAK_EVERY === 0) n += this.STREAK_BONUS;
    if (fromEl) IAKidsFX.coinFly(fromEl);
    return this.add(n);
  },

  async wrong() {
    this._streak = 0;
    return this.add(this.WRONG);
  },

  async mount() {
    if (document.getElementById('iakids-coin-badge')) return;
    const el = document.createElement('div');
    el.id = 'iakids-coin-badge';
    el.innerHTML = '🪙 <span>0</span>';
    document.body.appendChild(el);
    el.querySelector('span').textContent = await this.get();
  },
};

/**
 * IAKidsFX — celebration/feedback helpers. Pairs with game-style.css classes.
 *
 *   IAKidsFX.correct(btnEl);        // green pop + happy sound + "+10" popup
 *   IAKidsFX.wrong(btnEl);          // red shake + sad sound
 *   IAKidsFX.scorePop('+10', el);   // floating score text near element
 *   IAKidsFX.celebrate();           // confetti burst + fanfare (auto on complete)
 *   IAKidsFX.muted = true;          // kill sounds
 */
const IAKidsFX = {
  muted: false,
  _ctx: null,

  // ponytail: WebAudio beeps instead of howler + sound files — zero deps, works offline
  _beep(notes) {
    if (this.muted) return;
    try {
      const ctx = (this._ctx ||= new (window.AudioContext || window.webkitAudioContext)());
      notes.forEach(([freq, start, dur]) => {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.type = 'triangle';
        o.frequency.value = freq;
        g.gain.setValueAtTime(0.15, ctx.currentTime + start);
        g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + dur);
        o.connect(g).connect(ctx.destination);
        o.start(ctx.currentTime + start);
        o.stop(ctx.currentTime + start + dur);
      });
    } catch (e) { /* no audio — fine */ }
  },

  correct(el, points = '+10') {
    this._beep([[523, 0, 0.15], [659, 0.1, 0.15], [784, 0.2, 0.25]]); // C-E-G
    if (el) {
      el.classList.remove('correct'); void el.offsetWidth; // restart animation
      el.classList.add('correct');
      setTimeout(() => el.classList.remove('correct'), 500);
      this.scorePop(points, el);
    }
  },

  wrong(el) {
    this._beep([[220, 0, 0.2], [180, 0.15, 0.3]]);
    if (el) {
      el.classList.remove('wrong'); void el.offsetWidth;
      el.classList.add('wrong');
      setTimeout(() => el.classList.remove('wrong'), 500);
    }
    if (navigator.vibrate) navigator.vibrate(150);
  },

  coinFly(fromEl) {
    const badge = document.getElementById('iakids-coin-badge');
    const r = fromEl.getBoundingClientRect();
    const to = badge ? badge.getBoundingClientRect() : { left: 16, top: 16 };
    const c = document.createElement('div');
    c.textContent = '🪙';
    c.style.cssText = `position:fixed;z-index:100;font-size:1.6rem;pointer-events:none;
      left:${r.left + r.width / 2}px;top:${r.top}px;transition:all .6s cubic-bezier(.5,-0.3,.7,1)`;
    document.body.appendChild(c);
    requestAnimationFrame(() => requestAnimationFrame(() => {
      c.style.left = to.left + 'px';
      c.style.top = to.top + 'px';
      c.style.transform = 'scale(0.5)';
      c.style.opacity = '0.3';
    }));
    setTimeout(() => c.remove(), 650);
    this._beep([[988, 0, 0.08], [1319, 0.08, 0.15]]); // coin ding
  },

  scorePop(text, nearEl) {
    const pop = document.createElement('div');
    pop.className = 'score-pop';
    pop.textContent = text;
    const r = nearEl ? nearEl.getBoundingClientRect()
                     : { left: innerWidth / 2, top: innerHeight / 2, width: 0 };
    pop.style.left = r.left + r.width / 2 + 'px';
    pop.style.top = r.top + 'px';
    document.body.appendChild(pop);
    setTimeout(() => pop.remove(), 900);
  },

  async celebrate() {
    this._beep([[523, 0, 0.12], [659, 0.12, 0.12], [784, 0.24, 0.12], [1047, 0.36, 0.4]]);
    if (!window.confetti) {
      await new Promise(res => {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.3/dist/confetti.browser.min.js';
        s.onload = res; s.onerror = res;
        document.head.appendChild(s);
      });
    }
    if (window.confetti) {
      confetti({ particleCount: 120, spread: 80, origin: { y: 0.6 } });
      setTimeout(() => confetti({ particleCount: 60, angle: 60, spread: 55, origin: { x: 0 } }), 250);
      setTimeout(() => confetti({ particleCount: 60, angle: 120, spread: 55, origin: { x: 1 } }), 400);
    }
  },
};

/**
 * IAKidsShare — challenge-a-friend links. No backend: the challenge rides in the URL.
 *   game.shareButton(score, containerEl)  // adds "send to friend" button on end screen
 * SDK auto-shows a "beat X!" banner when a game opens via a challenge link,
 * and a victory banner in complete() if the score beats it.
 */
const IAKidsShare = {
  parse() {
    try {
      const c = new URLSearchParams(location.search).get('challenge');
      return c ? JSON.parse(decodeURIComponent(escape(atob(c)))) : null;
    } catch (e) { return null; }
  },

  url(slug, score, name) {
    const c = btoa(unescape(encodeURIComponent(JSON.stringify({ score, name }))));
    return location.origin + location.pathname.replace(/[^/]*$/, '') + '?challenge=' + c;
  },

  async playerName() {
    // Guests never get a forced name prompt — default label, changeable later
    // (optionally) via the name field on the champions page or Google sign-in.
    return (await IAKidsCoins._kvGet('player')) || IAKidsLang.ui('guest');
  },

  button(slug, score, el) {
    const btn = document.createElement('button');
    btn.className = 'game-btn secondary';
    btn.textContent = IAKidsLang.ui('send_challenge');
    btn.onclick = async () => {
      const url = this.url(slug, score, await this.playerName());
      const text = `🎮 אני עשיתי ${score} נקודות! נראה אותך עובר אותי:`;
      if (navigator.share) { navigator.share({ text, url }).catch(() => {}); return; }
      window.open('https://wa.me/?text=' + encodeURIComponent(text + '\n' + url));
    };
    (el || document.body).appendChild(btn);
    return btn;
  },

  banner(text) {
    const b = document.createElement('div');
    b.className = 'challenge-banner bounce-in';
    b.textContent = text;
    document.body.prepend(b);
    return b;
  },

  init() {
    const c = this.parse();
    if (c) this._target = c, this.banner(`🏆 ${c.name} קבע ${c.score} נקודות — נצח אותו!`);
  },

  onComplete(slug, score) {
    if (!this._target) return;
    this.banner(score > this._target.score
      ? `🥇 ניצחת את ${this._target.name}! ${score} מול ${this._target.score}`
      : `כמעט! ${this._target.name} עדיין מוביל עם ${this._target.score} — נסה שוב 💪`);
  },
};

/**
 * IAKidsTournament — 3-round tournament across playable games. Stored in DB
 * iakids_tournaments. Games need ZERO code: SDK chains them via ?tournament=<id>
 * and complete() records the round + shows a "next game" button.
 * Champion-of-champions table + tournament UI live in games/champions/index.html.
 */
const IAKidsTournament = {
  _db() {
    return (this._dbp ||= new Promise((resolve, reject) => {
      const req = indexedDB.open('iakids_tournaments', 1);
      req.onupgradeneeded = () => req.result.createObjectStore('t', { keyPath: 'id' });
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    }));
  },
  async _get(id) {
    const db = await this._db();
    return new Promise(res => {
      const r = db.transaction('t').objectStore('t').get(id);
      r.onsuccess = () => res(r.result); r.onerror = () => res(null);
    });
  },
  async _put(t) {
    const db = await this._db();
    return new Promise(res => {
      const tx = db.transaction('t', 'readwrite');
      tx.objectStore('t').put(t); tx.oncomplete = res;
    });
  },
  async all() {
    const db = await this._db();
    return new Promise(res => {
      const r = db.transaction('t').objectStore('t').getAll();
      r.onsuccess = () => res(r.result || []); r.onerror = () => res([]);
    });
  },
  async create(slugs) {
    const t = { id: 't' + Date.now(), slugs, scores: {}, done: false, ts: Date.now() };
    await this._put(t);
    return t;
  },
  gameUrl: (t, i) => '../' + t.slugs[i] + '/?tournament=' + t.id,

  currentId: () => new URLSearchParams(location.search).get('tournament'),

  async onComplete(slug, score) {
    const id = this.currentId();
    if (!id) return;
    const t = await this._get(id);
    if (!t) return;
    t.scores[Object.keys(t.scores).length] = { slug, score }; // rounds keyed by order (same game can repeat)
    const round = Object.keys(t.scores).length;
    t.done = round >= t.slugs.length;
    await this._put(t);
    const btn = document.createElement('button');
    btn.className = 'game-btn tournament-next';
    btn.textContent = t.done ? '🏆' : `${IAKidsLang.ui('next_game')} (${round + 1}/${t.slugs.length})`;
    btn.onclick = () => location.href = t.done ? '../champions/?t=' + id : this.gameUrl(t, round);
    document.body.appendChild(btn);
  },
};

if (typeof window !== 'undefined') IAKidsShare.init();

// small kv helpers on the wallet DB (player name etc.)
IAKidsCoins._kvGet = async function (k) {
  const db = await this._db();
  return new Promise(res => {
    const r = db.transaction('kv').objectStore('kv').get(k);
    r.onsuccess = () => res(r.result); r.onerror = () => res(null);
  });
};
IAKidsCoins._kvPut = async function (k, v) {
  const db = await this._db();
  return new Promise(res => {
    const t = db.transaction('kv', 'readwrite');
    t.objectStore('kv').put(v, k); t.oncomplete = res;
  });
};

/**
 * IAKidsLang — language support for games. Order: ?lang= param > saved pref > he.
 *   IAKidsLang.code                  // 'he' | 'en' | 'es' | 'de' | 'pt'
 *   IAKidsLang.t({he:'שלום', en:'Hello'})   // pick per current lang (he fallback)
 *   IAKidsLang.ui('play_again')      // shared UI strings, pre-translated
 *   IAKidsLang.set('es')             // persist + reload
 * Sets <html lang/dir> automatically (he = RTL, rest LTR).
 * Language-bound games (Hebrew letters, English vocab) keep their content
 * language and only translate UI chrome.
 */
const IAKidsLang = {
  code: new URLSearchParams(location.search).get('lang')
    || localStorage.getItem('iakids_lang') || 'he',

  set(c) { localStorage.setItem('iakids_lang', c); location.reload(); },

  t(d) { return d[this.code] ?? d.he ?? Object.values(d)[0]; },

  UI: {
    start:          { he: 'התחל!', en: 'Start!', es: '¡Empezar!', de: 'Los!', pt: 'Começar!' },
    play_again:     { he: 'שחק שוב 🔁', en: 'Play again 🔁', es: 'Jugar otra vez 🔁', de: 'Nochmal 🔁', pt: 'Jogar de novo 🔁' },
    score:          { he: 'ניקוד', en: 'Score', es: 'Puntos', de: 'Punkte', pt: 'Pontos' },
    question:       { he: 'שאלה', en: 'Question', es: 'Pregunta', de: 'Frage', pt: 'Pergunta' },
    your_best:      { he: 'השיא שלך', en: 'Your best', es: 'Tu récord', de: 'Dein Rekord', pt: 'Seu recorde' },
    level_easy:     { he: '🙂 קל', en: '🙂 Easy', es: '🙂 Fácil', de: '🙂 Leicht', pt: '🙂 Fácil' },
    level_medium:   { he: '😎 בינוני', en: '😎 Medium', es: '😎 Medio', de: '😎 Mittel', pt: '😎 Médio' },
    level_hard:     { he: '🤓 קשה', en: '🤓 Hard', es: '🤓 Difícil', de: '🤓 Schwer', pt: '🤓 Difícil' },
    level_random:   { he: '🎲 אקראי', en: '🎲 Random', es: '🎲 Aleatorio', de: '🎲 Zufall', pt: '🎲 Aleatório' },
    send_challenge: { he: '📤 שלח אתגר לחבר', en: '📤 Challenge a friend', es: '📤 Reta a un amigo', de: '📤 Freund herausfordern', pt: '📤 Desafiar um amigo' },
    beat_them:      { he: 'נצח אותו!', en: 'Beat it!', es: '¡Supéralo!', de: 'Schlag das!', pt: 'Supere isso!' },
    next_game:      { he: '⏭ למשחק הבא', en: '⏭ Next game', es: '⏭ Siguiente juego', de: '⏭ Nächstes Spiel', pt: '⏭ Próximo jogo' },
    guest:          { he: 'אורח', en: 'Guest', es: 'Invitado', de: 'Gast', pt: 'Convidado' },
    timer_toggle:   { he: 'הפעל/כבה טיימר', en: 'Toggle timer', es: 'Activar/desactivar temporizador', de: 'Timer ein/aus', pt: 'Ativar/desativar cronômetro' },
    timer_on:       { he: '⏱️ עם טיימר', en: '⏱️ With timer', es: '⏱️ Con temporizador', de: '⏱️ Mit Timer', pt: '⏱️ Com cronômetro' },
    timer_off:      { he: '🚫 בלי טיימר', en: '🚫 No timer', es: '🚫 Sin temporizador', de: '🚫 Ohne Timer', pt: '🚫 Sem cronômetro' },
  },
  ui(k) { return this.t(this.UI[k] || { he: k }); },

  init() {
    document.documentElement.lang = this.code;
    document.documentElement.dir = this.code === 'he' ? 'rtl' : 'ltr';
  },

  // opt-in language-picker pill row — call on pages that want it visible
  // (not auto-mounted on every game, to avoid crowding the coin/help/home corners)
  LANGS: [['he', '🇮🇱'], ['en', '🇬🇧'], ['es', '🇪🇸'], ['de', '🇩🇪'], ['pt', '🇵🇹']],
  mountSwitcher(container) {
    const el = document.createElement('div');
    el.id = 'iakids-lang-switcher';
    el.innerHTML = this.LANGS.map(([code, flag]) =>
      `<button data-code="${code}" class="${code === this.code ? 'active' : ''}">${flag}</button>`).join('');
    el.querySelectorAll('button').forEach(b => b.onclick = () => this.set(b.dataset.code));
    (container || document.body).appendChild(el);
  },
};
if (typeof window !== 'undefined') IAKidsLang.init();

/**
 * IAKidsTimer — optional per-question countdown. Timeout = wrong answer.
 *
 *   const timer = game.timer({ style: 'bomb', onTimeout: () => answer(null) });
 *   timer.start(IAKidsTimer.secondsFor(diff.level));  // each question
 *   timer.stop();                                     // when answered
 *
 * Time follows difficulty: secondsFor(level, base=10, min=3) = base - 2*(level-1),
 * so harder level ⇒ less time. Pass a bigger/smaller base per game.
 * style 'bomb': 💣 with countdown, red pulse + ticking in the last 3s, 💥 on timeout.
 * style 'bar': shrinking top bar only.
 */
const IAKidsTimer = {
  secondsFor: (level, base = 10, min = 3) => Math.max(min, base - 2 * (level - 1)),

  // per-device on/off (some kids/parents don't want a countdown) — one flag, every game respects it.
  // Default OFF: time pressure is opt-in, not something a kid meets unannounced.
  get enabled() { return localStorage.getItem('iakids_timer_enabled') === '1'; },
  set enabled(v) {
    localStorage.setItem('iakids_timer_enabled', v ? '1' : '0');
    if (!v) this._active?.stop();
  },

  // Labeled on/off pill, mounted on every game page at load so the choice is made
  // before picking a level. Sits inside the start screen when one exists (that's
  // where the level/rounds choices are), else floats bottom-right.
  // Only games that actually run a countdown get the control — a "with/without
  // timer" choice on a game that never times you is a dead button.
  // ponytail: sniffs the page's own inline scripts for a game.timer() call; games
  // are single-file with inline JS. If a game ever moves its JS to an external
  // file, call IAKidsTimer.mountToggle() from it explicitly.
  _usesTimer() {
    return [...document.querySelectorAll('script')].some(s => s.textContent.includes('game.timer('));
  },

  mountToggle() {
    if (document.getElementById('iakids-timer-toggle')) return;
    if (!this._usesTimer()) return;
    const btn = document.createElement('button');
    btn.id = 'iakids-timer-toggle';
    btn.className = 'game-btn outline';
    btn.title = IAKidsLang.ui('timer_toggle');
    const paint = () => {
      btn.textContent = IAKidsLang.ui(IAKidsTimer.enabled ? 'timer_on' : 'timer_off');
      btn.classList.toggle('success', IAKidsTimer.enabled);
    };
    paint();
    btn.onclick = () => { IAKidsTimer.enabled = !IAKidsTimer.enabled; paint(); };
    const host = document.getElementById('start-screen');
    if (host) host.appendChild(btn);
    else { btn.classList.add('floating'); document.body.appendChild(btn); }
  },

  create({ style = 'bomb', onTimeout } = {}) {
    let el = document.getElementById('iakids-timer');
    if (!el) {
      el = document.createElement('div');
      el.id = 'iakids-timer';
      el.innerHTML = '<div class="fuse"></div><div class="bomb">💣<span></span></div>';
      document.body.appendChild(el);
    }
    IAKidsTimer.mountToggle();
    el.querySelector('.bomb').style.display = style === 'bomb' ? '' : 'none';
    const fuse = el.querySelector('.fuse');
    const label = el.querySelector('.bomb span');
    let iv = null, left = 0, lastTick = -1;

    const stop = () => { clearInterval(iv); iv = null; el.classList.remove('danger'); el.style.display = 'none'; };

    const start = seconds => {
      stop();
      if (!IAKidsTimer.enabled) return; // timer turned off in settings — never shows, never times out
      el.style.display = '';
      left = seconds;
      const t0 = Date.now();
      iv = setInterval(() => {
        left = seconds - (Date.now() - t0) / 1000;
        const whole = Math.ceil(left);
        fuse.style.width = Math.max(0, (left / seconds) * 100) + '%';
        label.textContent = Math.max(0, whole);
        el.classList.toggle('danger', left <= 3);
        if (left <= 3 && whole !== lastTick && left > 0) { lastTick = whole; IAKidsFX._beep([[1200, 0, 0.05]]); }
        if (left <= 0) {
          stop();
          if (style === 'bomb') {
            label.textContent = '';
            IAKidsFX.scorePop('💥', el);
          }
          IAKidsFX._beep([[80, 0, 0.4], [60, 0.1, 0.5]]); // boom
          if (navigator.vibrate) navigator.vibrate([100, 50, 200]);
          onTimeout && onTimeout();
        }
      }, 100);
    };
    const api = { start, stop, get running() { return !!iv; } };
    IAKidsTimer._active = api;
    return api;
  },
};
// after DOM parse: the game's own <script> and #start-screen exist only by then
if (typeof window !== 'undefined') {
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', () => IAKidsTimer.mountToggle());
  else IAKidsTimer.mountToggle();
}

/**
 * IAKidsHelp — per-game help. Floating ❓ opens a modal that explains the game
 * with an example. Auto-opens on the player's first visit to the game.
 *
 *   IAKidsHelp.mount({
 *     slug: 'missing-number',
 *     how: 'טקסט הסבר קצר איך משחקים',
 *     example: '<b>7 + ◻ = 10</b> ← התשובה היא 3',   // HTML allowed
 *   });
 */
const IAKidsHelp = {
  mount({ slug, how, example }) {
    if (document.getElementById('iakids-help-btn')) return;
    const btn = document.createElement('button');
    btn.id = 'iakids-help-btn';
    btn.textContent = '❓';
    btn.onclick = () => this.open();
    document.body.appendChild(btn);

    const modal = document.createElement('div');
    modal.id = 'iakids-help-modal';
    modal.innerHTML = `
      <div class="help-card game-card">
        <h2>${IAKidsLang.t({ he: 'איך משחקים?', en: 'How to play?', es: '¿Cómo se juega?', de: 'Wie spielt man?', pt: 'Como jogar?' })}</h2>
        <p class="help-how">${how}</p>
        <div class="help-example">${example || ''}</div>
        <button class="game-btn">${IAKidsLang.t({ he: '👍 הבנתי!', en: '👍 Got it!', es: '👍 ¡Entendido!', de: '👍 Verstanden!', pt: '👍 Entendi!' })}</button>
      </div>`;
    modal.style.display = 'none';
    modal.querySelector('.game-btn').onclick = () => modal.style.display = 'none';
    modal.onclick = e => { if (e.target === modal) modal.style.display = 'none'; };
    document.body.appendChild(modal);
    this._modal = modal;

    const key = 'iakids_help_seen_' + slug;
    if (!localStorage.getItem(key)) { localStorage.setItem(key, '1'); this.open(); }
  },
  open() { if (this._modal) this._modal.style.display = ''; },
};

/**
 * IAKidsSkills — single source of truth for the 100-game catalog's cognitive-
 * skill mapping (shared by games/skills/ and games/brain-test/). Pure data +
 * pure functions, no DOM. Educational estimate, not clinical/neuroscience data.
 */
const IAKidsSkills = {
  // label/brain/name are {he,en,es,de,pt} — resolve with IAKidsLang.t() when rendering.
  SKILLS: [
    { key: 'mem',  label: { he: 'זיכרון', en: 'Memory', es: 'Memoria', de: 'Gedächtnis', pt: 'Memória' },
      brain: { he: 'היפוקמפוס', en: 'Hippocampus', es: 'Hipocampo', de: 'Hippocampus', pt: 'Hipocampo' } },
    { key: 'att',  label: { he: 'קשב וריכוז', en: 'Attention & Focus', es: 'Atención y concentración', de: 'Aufmerksamkeit', pt: 'Atenção e foco' },
      brain: { he: 'קליפה קדם-מצחית', en: 'Prefrontal cortex', es: 'Corteza prefrontal', de: 'Präfrontaler Kortex', pt: 'Córtex pré-frontal' } },
    { key: 'log',  label: { he: 'חשיבה לוגית', en: 'Logical Reasoning', es: 'Razonamiento lógico', de: 'Logisches Denken', pt: 'Raciocínio lógico' },
      brain: { he: 'קליפה קדם-מצחית', en: 'Prefrontal cortex', es: 'Corteza prefrontal', de: 'Präfrontaler Kortex', pt: 'Córtex pré-frontal' } },
    { key: 'lang', label: { he: 'שפה ואוצר מילים', en: 'Language & Vocabulary', es: 'Lenguaje y vocabulario', de: 'Sprache & Wortschatz', pt: 'Idioma e vocabulário' },
      brain: { he: 'אזור ברוקה/וורניקה', en: 'Broca\'s/Wernicke\'s area', es: 'Área de Broca/Wernicke', de: 'Broca-/Wernicke-Areal', pt: 'Área de Broca/Wernicke' } },
    { key: 'num',  label: { he: 'חשיבה מספרית', en: 'Numeracy', es: 'Numeración', de: 'Numerisches Denken', pt: 'Raciocínio numérico' },
      brain: { he: 'אונה קודקודית', en: 'Parietal lobe', es: 'Lóbulo parietal', de: 'Parietallappen', pt: 'Lobo parietal' } },
    { key: 'spd',  label: { he: 'מהירות עיבוד', en: 'Processing Speed', es: 'Velocidad de procesamiento', de: 'Verarbeitungsgeschwindigkeit', pt: 'Velocidade de processamento' },
      brain: { he: 'מסלולים עצביים', en: 'Neural pathways', es: 'Vías neuronales', de: 'Neuronale Bahnen', pt: 'Vias neurais' } },
    { key: 'spa',  label: { he: 'תפיסה חזותית-מרחבית', en: 'Visual-Spatial', es: 'Visoespacial', de: 'Visuell-räumlich', pt: 'Visuoespacial' },
      brain: { he: 'אונה קודקודית-עורפית', en: 'Parieto-occipital lobe', es: 'Lóbulo parieto-occipital', de: 'Parieto-okzipitallappen', pt: 'Lobo parieto-occipital' } },
    { key: 'flex', label: { he: 'גמישות וסקרנות', en: 'Cognitive Flexibility', es: 'Flexibilidad cognitiva', de: 'Kognitive Flexibilität', pt: 'Flexibilidade cognitiva' },
      brain: { he: 'קליפה קדם-מצחית', en: 'Prefrontal cortex', es: 'Corteza prefrontal', de: 'Präfrontaler Kortex', pt: 'Córtex pré-frontal' } },
  ],

  CAT_META: {
    math: { name: { he: 'חשבון ומתמטיקה', en: 'Math', es: 'Matemáticas', de: 'Mathematik', pt: 'Matemática' }, emoji: '🔢', scores: { mem: 3, att: 4, log: 5, lang: 1, num: 5, spd: 4, spa: 3, flex: 2 } },
    heb:  { name: { he: 'עברית ושפה', en: 'Hebrew & Language', es: 'Hebreo e idioma', de: 'Hebräisch & Sprache', pt: 'Hebraico e idioma' }, emoji: '📜', scores: { mem: 4, att: 3, log: 2, lang: 5, num: 0, spd: 2, spa: 1, flex: 3 } },
    eng:  { name: { he: 'אנגלית', en: 'English', es: 'Inglés', de: 'Englisch', pt: 'Inglês' }, emoji: '🇬🇧', scores: { mem: 4, att: 3, log: 2, lang: 5, num: 0, spd: 2, spa: 1, flex: 2 } },
    sci:  { name: { he: 'מדעים וגיאוגרפיה', en: 'Science & Geography', es: 'Ciencias y geografía', de: 'Wissenschaft & Geografie', pt: 'Ciências e geografia' }, emoji: '🌍', scores: { mem: 5, att: 3, log: 3, lang: 3, num: 1, spd: 1, spa: 4, flex: 2 } },
    log:  { name: { he: 'לוגיקה וקוד', en: 'Logic & Code', es: 'Lógica y código', de: 'Logik & Code', pt: 'Lógica e código' }, emoji: '🧩', scores: { mem: 3, att: 4, log: 5, lang: 0, num: 1, spd: 3, spa: 5, flex: 4 } },
    hw:   { name: { he: 'שיעורי בית ומוטיבציה', en: 'Homework & Motivation', es: 'Deberes y motivación', de: 'Hausaufgaben & Motivation', pt: 'Lição de casa e motivação' }, emoji: '⏱️', scores: { mem: 1, att: 5, log: 1, lang: 1, num: 0, spd: 1, spa: 0, flex: 5 } },
  },

  MECH_DELTA: {
    mcq:    { spd: +1 },
    drag:   { spa: +1 },
    pairs:  { mem: +2, spd: -1 },
    input:  { lang: +1, flex: +1, spd: -1 },
    tap:    { spd: +2, att: +1 },
    widget: { spa: +2, flex: +1 },
    tf:     { spd: +1, att: +1 },
    tool:   { att: +1, flex: +1, mem: -1 },
  },

  GAMES: [
    { slug:'abc-order-en', name:'ABC Order', emoji:'🔤', cat:'eng', mech:'drag' },
    { slug:'abc-order-he', name:'סדר אלפביתי', emoji:'📚', cat:'heb', mech:'drag' },
    { slug:'acronyms', name:'ראשי תיבות', emoji:'🔡', cat:'heb', mech:'mcq' },
    { slug:'action-verbs', name:'Action Verbs', emoji:'🏃', cat:'eng', mech:'mcq' },
    { slug:'addition-pyramid', name:'פירמידת חיבור', emoji:'🔺', cat:'math', mech:'input' },
    { slug:'animal-sounds', name:'קולות חיות', emoji:'🔊', cat:'sci', mech:'mcq' },
    { slug:'animals-en', name:'Animals', emoji:'🦁', cat:'eng', mech:'mcq' },
    { slug:'balance-scale', name:'מאזניים', emoji:'⚖️', cat:'math', mech:'widget' },
    { slug:'body-parts', name:'Body Parts', emoji:'🦵', cat:'eng', mech:'tap' },
    { slug:'break-wheel', name:'גלגל הפסקות', emoji:'🎡', cat:'hw', mech:'tool' },
    { slug:'capital-small', name:'Aa Letters', emoji:'🅰️', cat:'eng', mech:'pairs' },
    { slug:'capitals', name:'ערי בירה', emoji:'🏛️', cat:'sci', mech:'pairs' },
    { slug:'carnivore-herbivore', name:'טורף או צמחוני', emoji:'🥩', cat:'sci', mech:'drag' },
    { slug:'change-calculator', name:'עודף מקנייה', emoji:'💰', cat:'math', mech:'mcq' },
    { slug:'clock-match', name:'שעון מחוגים', emoji:'🕒', cat:'math', mech:'mcq' },
    { slug:'colors-shapes', name:'Colors & Shapes', emoji:'🎨', cat:'eng', mech:'tap' },
    { slug:'compare-numbers', name:'גדול קטן שווה', emoji:'⚖️', cat:'math', mech:'mcq' },
    { slug:'compound-words', name:'מילים מורכבות', emoji:'🚡', cat:'heb', mech:'pairs' },
    { slug:'continents', name:'זהה יבשת', emoji:'🗺️', cat:'sci', mech:'tap' },
    { slug:'count-shapes', name:'ספירת צורות', emoji:'🔷', cat:'math', mech:'mcq' },
    { slug:'daily-goals', name:'מטרות יומיות', emoji:'🎯', cat:'hw', mech:'tool' },
    { slug:'days-of-week', name:'Days of Week', emoji:'📅', cat:'eng', mech:'drag' },
    { slug:'english-word-match', name:'Word Match', emoji:'🖇️', cat:'eng', mech:'mcq' },
    { slug:'fill-the-gap', name:'Fill the Gap', emoji:'⬜', cat:'eng', mech:'mcq' },
    { slug:'first-last-letter', name:'אות פותחת', emoji:'🔠', cat:'heb', mech:'mcq' },
    { slug:'flags', name:'דגלי מדינות', emoji:'🚩', cat:'sci', mech:'mcq' },
    { slug:'flashcards', name:'פלאשקארדס', emoji:'🗂️', cat:'hw', mech:'tool' },
    { slug:'food-chain', name:'שרשרת המזון', emoji:'🦊', cat:'sci', mech:'tap' },
    { slug:'fraction-pizza', name:'שברים בפיצה', emoji:'🍕', cat:'math', mech:'widget' },
    { slug:'fruit-veggie-sort', name:'Fruit & Veggies', emoji:'🍎', cat:'eng', mech:'drag' },
    { slug:'gender-sort', name:'זכר או נקבה', emoji:'🚻', cat:'heb', mech:'drag' },
    { slug:'half-or-double', name:'חצי או כפול', emoji:'✂️', cat:'math', mech:'mcq' },
    { slug:'hangman-house', name:'בניית בית', emoji:'🏠', cat:'heb', mech:'input' },
    { slug:'idioms', name:'פתגמים', emoji:'💬', cat:'heb', mech:'mcq' },
    { slug:'israel-map', name:'מפת ישראל', emoji:'🇮🇱', cat:'sci', mech:'drag' },
    { slug:'keys-locks', name:'מפתחות ומנעולים', emoji:'🔑', cat:'log', mech:'pairs' },
    { slug:'leaderboard', name:'טבלת שיאים', emoji:'🏆', cat:'hw', mech:'tool' },
    { slug:'letter-swap', name:'החלף אות', emoji:'🔁', cat:'heb', mech:'mcq' },
    { slug:'living-things-sort', name:'חי צומח דומם', emoji:'🌱', cat:'sci', mech:'drag' },
    { slug:'logic-scale', name:'מאזני לוגיקה', emoji:'🤔', cat:'log', mech:'mcq' },
    { slug:'longest-word', name:'המילה הארוכה', emoji:'📏', cat:'heb', mech:'tap' },
    { slug:'make-ten', name:'משלימים ל-10', emoji:'🔗', cat:'math', mech:'tap' },
    { slug:'maze', name:'מבוך', emoji:'🌀', cat:'log', mech:'widget' },
    { slug:'memory-classic', name:'משחק הזיכרון', emoji:'🧠', cat:'log', mech:'pairs' },
    { slug:'memory-equations', name:'זיכרון תרגילים', emoji:'🃏', cat:'math', mech:'pairs' },
    { slug:'missing-letter', name:'האות החסרה', emoji:'🅰️', cat:'heb', mech:'mcq' },
    { slug:'missing-number', name:'השלם את הנעלם', emoji:'❓', cat:'math', mech:'mcq' },
    { slug:'mood-journal', name:'יומן מצב רוח', emoji:'😊', cat:'hw', mech:'tool' },
    { slug:'multiplication-bingo', name:'בינגו כפל', emoji:'🎱', cat:'math', mech:'tap' },
    { slug:'nikud', name:'זהה את הניקוד', emoji:'🎯', cat:'heb', mech:'mcq' },
    { slug:'number-line-jumps', name:'ציר המספרים', emoji:'🐸', cat:'math', mech:'widget' },
    { slug:'number-sequence', name:'סדרה חסרה', emoji:'📈', cat:'math', mech:'mcq' },
    { slug:'numbers-to-words', name:'Numbers to Words', emoji:'5️⃣', cat:'eng', mech:'pairs' },
    { slug:'odd-even-sort', name:'זוגי או אי-זוגי', emoji:'2️⃣', cat:'math', mech:'drag' },
    { slug:'odd-one-out-math', name:'יוצא דופן', emoji:'🕵️', cat:'math', mech:'mcq' },
    { slug:'opposites-en', name:'Opposites', emoji:'↔️', cat:'eng', mech:'pairs' },
    { slug:'opposites-he', name:'הפכים', emoji:'↔️', cat:'heb', mech:'pairs' },
    { slug:'pattern-match', name:'זהה תבנית', emoji:'🔶', cat:'log', mech:'mcq' },
    { slug:'perimeter', name:'היקפים', emoji:'📐', cat:'math', mech:'mcq' },
    { slug:'picture-story', name:'סיפור בתמונות', emoji:'🖼️', cat:'heb', mech:'drag' },
    { slug:'pixel-art-code', name:'פיקסל ארט', emoji:'🎨', cat:'log', mech:'widget' },
    { slug:'plant-parts', name:'חלקי הצמח', emoji:'🌷', cat:'sci', mech:'tap' },
    { slug:'plural-en', name:'Singular-Plural', emoji:'🐱', cat:'eng', mech:'mcq' },
    { slug:'pomodoro-rocket', name:'טיימר חללית', emoji:'🚀', cat:'hw', mech:'tool' },
    { slug:'pronouns', name:'He She It', emoji:'🗣️', cat:'eng', mech:'mcq' },
    { slug:'puzzle-piece', name:'החלק החסר', emoji:'🧩', cat:'log', mech:'mcq' },
    { slug:'quiz-maker', name:'בוחן עצמי', emoji:'📝', cat:'hw', mech:'tool' },
    { slug:'reading-comprehension', name:'הבנת הנקרא', emoji:'🧐', cat:'heb', mech:'mcq' },
    { slug:'recycling-sort', name:'מיון מחזור', emoji:'♻️', cat:'sci', mech:'drag' },
    { slug:'rhymes', name:'חרוזים', emoji:'🎵', cat:'heb', mech:'mcq' },
    { slug:'robot-grid', name:'כוון את הרובוט', emoji:'🤖', cat:'log', mech:'widget' },
    { slug:'roots', name:'שורשים', emoji:'🌳', cat:'heb', mech:'drag' },
    { slug:'rounding', name:'עיגול מספרים', emoji:'🔵', cat:'math', mech:'mcq' },
    { slug:'seasons', name:'עונות השנה', emoji:'🍂', cat:'sci', mech:'drag' },
    { slug:'sentence-scramble', name:'משפט מבולבל', emoji:'🧩', cat:'heb', mech:'drag' },
    { slug:'simon-says', name:'סיימון', emoji:'🚦', cat:'log', mech:'tap' },
    { slug:'singular-plural', name:'יחיד ורבים', emoji:'👥', cat:'heb', mech:'pairs' },
    { slug:'solar-system', name:'מערכת השמש', emoji:'🪐', cat:'sci', mech:'drag' },
    { slug:'sort-ascending', name:'מהקטן לגדול', emoji:'↗️', cat:'math', mech:'drag' },
    { slug:'spelling-bee', name:'Spelling Bee', emoji:'🐝', cat:'eng', mech:'input' },
    { slug:'spelling-error', name:'שגיאת כתיב', emoji:'✏️', cat:'heb', mech:'mcq' },
    { slug:'states-of-matter', name:'מצבי צבירה', emoji:'🧊', cat:'sci', mech:'drag' },
    { slug:'sticker-book', name:'אוסף מדבקות', emoji:'⭐', cat:'hw', mech:'tool' },
    { slug:'story-fill', name:'השלם את הסיפור', emoji:'📖', cat:'heb', mech:'mcq' },
    { slug:'sudoku-4x4', name:'סודוקו 4×4', emoji:'🔢', cat:'log', mech:'input' },
    { slug:'syllables', name:'הברות', emoji:'👏', cat:'heb', mech:'mcq' },
    { slug:'synonyms', name:'מילים נרדפות', emoji:'🤝', cat:'heb', mech:'pairs' },
    { slug:'target-bubbles', name:'קליעה למטרה', emoji:'🎯', cat:'math', mech:'tap' },
    { slug:'task-checklist', name:'רשימת משימות', emoji:'✅', cat:'hw', mech:'tool' },
    { slug:'tens-units', name:'עשרות ויחידות', emoji:'🔟', cat:'math', mech:'mcq' },
    { slug:'thermometer', name:'מד חום', emoji:'🌡️', cat:'math', mech:'widget' },
    { slug:'times-table-race', name:'אליפות הכפל', emoji:'🏁', cat:'math', mech:'mcq' },
    { slug:'toy-shop', name:'חנות צעצועים', emoji:'🧸', cat:'math', mech:'widget' },
    { slug:'true-false-math', name:'אמת או שקר', emoji:'✅', cat:'math', mech:'tf' },
    { slug:'typing-race', name:'הקלדה מהירה', emoji:'⌨️', cat:'hw', mech:'input' },
    { slug:'water-cycle', name:'מחזור המים', emoji:'💧', cat:'sci', mech:'drag' },
    { slug:'weather-clothes', name:'מזג אוויר ולבוש', emoji:'🧥', cat:'sci', mech:'drag' },
    { slug:'word-scramble', name:'סדר את המילה', emoji:'🔤', cat:'heb', mech:'drag' },
    { slug:'word-search', name:'תפזורת', emoji:'🔍', cat:'heb', mech:'tap' },
    { slug:'word-types', name:'שם עצם או פועל', emoji:'🏷️', cat:'heb', mech:'drag' },
  ],

  gameScores(g) {
    const base = this.CAT_META[g.cat].scores;
    const delta = this.MECH_DELTA[g.mech] || {};
    const out = {};
    for (const s of this.SKILLS) out[s.key] = Math.max(0, Math.min(5, (base[s.key] || 0) + (delta[s.key] || 0)));
    return out;
  },

  // top N games ranked by how strongly they train a given skill key
  topGamesFor(skillKey, n = 3, exclude = []) {
    return this.GAMES
      .filter(g => !exclude.includes(g.slug))
      .map(g => ({ game: g, score: this.gameScores(g)[skillKey] }))
      .sort((a, b) => b.score - a.score)
      .slice(0, n)
      .map(x => x.game);
  },

  // reusable radar-chart SVG renderer: scores = {key: 0..5}, color = CSS color string
  radarSVG(scores, color, { size = 220, max = 5 } = {}) {
    const cx = size / 2, cy = size / 2, r = size * 0.37;
    const pt = (i, value) => {
      const angle = (Math.PI * 2 * i) / this.SKILLS.length - Math.PI / 2;
      const rad = (value / max) * r;
      return [cx + rad * Math.cos(angle), cy + rad * Math.sin(angle)];
    };
    const rings = [1, 2, 3, 4, 5].map(lvl => {
      const pts = this.SKILLS.map((_, i) => pt(i, lvl).join(',')).join(' ');
      return `<polygon points="${pts}" fill="none" stroke="var(--line, #ddd)" stroke-width="${lvl === 5 ? 1.4 : 1}" opacity="${lvl === 5 ? 0.9 : 0.5}"/>`;
    }).join('');
    const spokes = this.SKILLS.map((_, i) => {
      const [x, y] = pt(i, max);
      return `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="var(--line, #ddd)" stroke-width="1" opacity="0.6"/>`;
    }).join('');
    const dataPts = this.SKILLS.map((s, i) => pt(i, scores[s.key] || 0));
    const dots = dataPts.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3" fill="${color}"/>`).join('');
    const labels = this.SKILLS.map((s, i) => {
      const angle = (Math.PI * 2 * i) / this.SKILLS.length - Math.PI / 2;
      const lx = cx + (r + 20) * Math.cos(angle);
      const ly = cy + (r + 20) * Math.sin(angle);
      const anchor = Math.cos(angle) > 0.3 ? 'start' : Math.cos(angle) < -0.3 ? 'end' : 'middle';
      return `<text x="${lx}" y="${ly}" font-size="8.2" fill="var(--text-3, #999)" text-anchor="${anchor}" dominant-baseline="middle">${IAKidsLang.t(s.label)}</text>`;
    }).join('');
    return `<svg viewBox="0 0 ${size} ${size}" width="100%" role="img">
      ${rings}${spokes}
      <polygon points="${dataPts.map(p => p.join(',')).join(' ')}" fill="${color}" fill-opacity="0.22" stroke="${color}" stroke-width="2"/>
      ${dots}${labels}
    </svg>`;
  },
};

/**
 * IAKidsAuth — Google sign-in via Firebase (config in ../firebase-config.js).
 * Optional layer on top of the existing name-based wallet: signing in with
 * Google replaces the "type your name" flow — the Google display name becomes
 * the wallet player name automatically, so leaderboards/champions/challenge
 * links all pick it up for free, no per-game changes needed.
 *
 *   IAKidsAuth.mount();               // renders the sign-in/avatar widget
 *   await IAKidsAuth.currentUser();   // null or {name, email, photo}
 */
const IAKidsAuth = {
  _app: null, _auth: null, _user: null, _ready: null,

  async _init() {
    if (this._ready) return this._ready;
    this._ready = (async () => {
      if (typeof FIREBASE_CONFIG === 'undefined' || FIREBASE_CONFIG.apiKey.startsWith('PASTE_ME')) {
        return false; // not configured yet — auth silently unavailable
      }
      const [{ initializeApp }, authMod] = await Promise.all([
        import('https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js'),
        import('https://www.gstatic.com/firebasejs/10.13.2/firebase-auth.js'),
      ]);
      this._app = initializeApp(FIREBASE_CONFIG);
      this._auth = authMod.getAuth(this._app);
      this._authMod = authMod;
      await new Promise(resolve => {
        authMod.onAuthStateChanged(this._auth, user => {
          this._user = user ? { name: user.displayName, email: user.email, photo: user.photoURL } : null;
          if (this._user) IAKidsCoins._kvPut('player', this._user.name);
          this._paint();
          resolve();
        });
      });
      return true;
    })();
    return this._ready;
  },

  async currentUser() {
    await this._init();
    return this._user;
  },

  async signIn() {
    const ok = await this._init();
    if (!ok) return alert(IAKidsLang.t({
      he: 'ההתחברות עם Google עדיין לא הופעלה באתר הזה.',
      en: 'Google sign-in isn\'t set up on this site yet.',
      es: 'El inicio de sesión con Google aún no está configurado.',
      de: 'Google-Anmeldung ist hier noch nicht eingerichtet.',
      pt: 'O login com Google ainda não está configurado.',
    }));
    try {
      await this._authMod.signInWithPopup(this._auth, new this._authMod.GoogleAuthProvider());
    } catch (e) { /* user closed popup — fine */ }
  },

  async signOut() {
    if (this._auth) await this._authMod.signOut(this._auth);
  },

  _paint() {
    const el = document.getElementById('iakids-auth-widget');
    if (!el) return;
    el.innerHTML = this._user
      ? `<img src="${this._user.photo || ''}" alt="" onerror="this.style.display='none'"><span>${this._user.name || this._user.email}</span><button title="${IAKidsLang.t({ he: 'התנתקות', en: 'Sign out', es: 'Salir', de: 'Abmelden', pt: 'Sair' })}">⏻</button>`
      : `<button class="signin-btn">🔐 ${IAKidsLang.t({ he: 'התחברות עם Google', en: 'Sign in with Google', es: 'Iniciar con Google', de: 'Mit Google anmelden', pt: 'Entrar com Google' })}</button>`;
    const btn = el.querySelector('.signin-btn');
    if (btn) btn.onclick = () => this.signIn();
    const out = el.querySelector('button[title]');
    if (out) out.onclick = () => this.signOut();
  },

  async mount() {
    if (!document.getElementById('iakids-auth-widget')) {
      const el = document.createElement('div');
      el.id = 'iakids-auth-widget';
      document.body.appendChild(el);
    }
    await this._init();
    this._paint();
  },
};

/**
 * IAKidsCloud — optional cloud leaderboard, only for signed-in players (never
 * guests — matches the "your data stays on your device unless you sign in"
 * promise on the skills page). Fails silently if supabase-config.js/the
 * game_wins table aren't set up yet (see games/games-tables.sql).
 *
 * Honesty note: identity here is only as strong as "the browser said this
 * email" — Supabase RLS can't verify a Firebase-issued token, so this can't
 * cryptographically stop someone from inserting under a fake email. RLS does
 * guarantee no one can edit or delete a score once written. Fine for a fun
 * kids' leaderboard; not a substitute for real server-side auth if this ever
 * needs to be tamper-proof.
 */
const IAKidsCloud = {
  _client: null, _ready: null,

  async _init() {
    if (this._ready) return this._ready;
    this._ready = (async () => {
      if (typeof SUPABASE_CONFIG === 'undefined') return false;
      const { createClient } = await import('https://esm.sh/@supabase/supabase-js@2');
      this._client = createClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.publishableKey);
      return true;
    })().catch(() => false);
    return this._ready;
  },

  async recordWin(slug, score, meta) {
    const user = await IAKidsAuth.currentUser();
    if (!user) return; // guests: local-only, never sent to the cloud
    if (!(await this._init())) return;
    try {
      await this._client.from('game_wins').insert({
        email: user.email, display_name: user.name, game_slug: slug, score, meta: meta || null,
      });
    } catch (e) { /* table not migrated yet, or offline — silently skip */ }
  },

  async recordAchievement(key) {
    const user = await IAKidsAuth.currentUser();
    if (!user) return;
    if (!(await this._init())) return;
    try {
      await this._client.from('game_achievements')
        .insert({ email: user.email, display_name: user.name, achievement_key: key })
        .select(); // duplicate (email, achievement_key) -> unique-violation, caught below
    } catch (e) { /* already unlocked, table missing, or offline — fine */ }
  },

  async topWins(slug, n = 10) {
    if (!(await this._init())) return [];
    const { data } = await this._client.from('game_wins')
      .select('email,display_name,score,created_at').eq('game_slug', slug)
      .order('score', { ascending: false }).limit(n);
    return data || [];
  },
};
