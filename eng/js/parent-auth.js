(() => {
  'use strict';
  const base = new URL('../', document.currentScript.src);
  const API = 'https://iakids-ai-tutor-he.onrender.com';
  const pendingKey = 'iakids.eng.pending';
  const childKey = 'iakids.eng.child';
  const storage = {
    get(key) { try { return sessionStorage.getItem(key); } catch { return null; } },
    set(key, value) { sessionStorage.setItem(key, value); },
    remove(key) { try { sessionStorage.removeItem(key); } catch {} }
  };
  const sb = window.supabase?.createClient('https://bxnfzuglfwytiyaguwjj.supabase.co', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4bmZ6dWdsZnd5dGl5YWd1d2pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyMjk0NjUsImV4cCI6MjA4NDgwNTQ2NX0.IcmVvbboKLkJLkE31_udEtvhPl66-kmZAvmPCT_lk5o', {
    auth: { flowType: 'pkce', storageKey: 'iakids-eng-auth', persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
  });
  const dialog = document.createElement('dialog');
  dialog.id = 'parentAuthDialog';
  dialog.className = 'parent-auth';
  dialog.setAttribute('aria-labelledby', 'parentAuthTitle');
  dialog.innerHTML = `<button class="auth-close" type="button" aria-label="Close parent sign in">×</button>
    <div class="auth-art"><img src="${new URL('assets/hero/test-prep-hero.webp', base).href}" alt=""><span>Learning starts<br>with your support.</span></div>
    <div class="auth-body"><div class="auth-brand">IA KIDS <span>ENG</span></div>
      <section data-auth-view="login"><p class="auth-eyebrow">FOR PARENTS</p><h2 id="parentAuthTitle">A little support.<br>A world of learning.</h2><p>Sign in to set up your child’s learning space and help them get ready for their next test.</p>
      <button class="google-signin" type="button"><svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#4285F4" d="M43.6 24.5c0-1.4-.1-2.8-.4-4.2H24v8h11a9.4 9.4 0 0 1-4.1 6.2v5.2h6.7c3.9-3.6 6-8.9 6-15.2Z"/><path fill="#34A853" d="M24 44c5.5 0 10.2-1.8 13.6-4.9l-6.7-5.2c-1.8 1.2-4.1 1.9-6.9 1.9-5.3 0-9.9-3.6-11.5-8.4H5.6v5.3A20 20 0 0 0 24 44Z"/><path fill="#FBBC05" d="M12.5 27.4a12 12 0 0 1 0-7.6v-5.3H5.6a20 20 0 0 0 0 18.2l6.9-5.3Z"/><path fill="#EA4335" d="M24 11.4c3 0 5.6 1 7.7 3l5.8-5.8A19.3 19.3 0 0 0 24 4 20 20 0 0 0 5.6 14.5l6.9 5.3c1.6-4.8 6.2-8.4 11.5-8.4Z"/></svg><span>Continue with Google</span></button>
      <p class="auth-parent-note">A parent or guardian should complete this step.<br>Kids don’t need their own account.</p>
      <p class="auth-legal">By continuing, you agree to our <a href="/terms/" target="_blank" rel="noopener">Terms</a> and <a href="/privacy/" target="_blank" rel="noopener">Privacy Policy</a>.</p></section>
      <section data-auth-view="children" hidden><h2 id="authChildrenTitle">Who’s learning today?</h2><p>Choose a child to continue.</p><div class="auth-children"></div><button type="button" class="auth-add">+ Add a child</button><button type="button" class="auth-signout">Sign out</button></section>
      <section data-auth-view="create" hidden><h2 id="authCreateTitle">Meet your learner</h2><p>Parent or guardian: add your child’s details once, so we can adapt their learning.</p><form id="authChildForm"><label for="authChildName">Child’s first name</label><input id="authChildName" required maxlength="60" autocomplete="off"><label for="authChildGrade">Grade</label><select id="authChildGrade" required><option value="">Choose a grade</option>${[1,2,3,4,5,6].map(n => `<option value="${n}">Grade ${n}</option>`).join('')}</select><button class="auth-primary" type="submit">Save and continue</button><button class="auth-back" type="button">Back</button></form></section>
      <section data-auth-view="loading" hidden><h2 id="authLoadingTitle">Getting things ready…</h2><p>Checking your account and loading your child profiles.</p></section>
      <p class="auth-error" role="alert" hidden></p><button type="button" class="auth-retry" hidden>Try again</button>
    </div>`;
  document.body.append(dialog);
  let opener, overflow, continuation, userId, activeChild, busy = false, generation = 0, resumeOnClose;
  const show = name => {
    dialog.querySelectorAll('[data-auth-view]').forEach(el => { el.hidden = el.dataset.authView !== name; });
    dialog.setAttribute('aria-labelledby', {login:'parentAuthTitle', children:'authChildrenTitle', create:'authCreateTitle', loading:'authLoadingTitle'}[name]);
    dialog.querySelector('.auth-error').hidden = true;
    dialog.querySelector('.auth-retry').hidden = true;
  };
  function error(message, retry = false) {
    const el = dialog.querySelector('.auth-error');
    el.textContent = message; el.hidden = false;
    dialog.querySelector('.auth-retry').hidden = !retry;
  }
  function open(trigger) {
    if (dialog.open) return;
    opener = trigger || document.activeElement;
    overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog.showModal();
  }
  function paintProfile(kid) {
    activeChild = kid || null;
    document.querySelector('.profile-copy strong').textContent = kid ? kid.child_name : 'Parent sign in';
    document.querySelector('.profile-copy small').textContent = kid ? 'Change learner' : 'Continue with Google';
    document.querySelector('.avatar').textContent = kid ? Array.from(kid.child_name)[0].toUpperCase() : 'P';
    document.querySelector('.eyebrow').textContent = kid ? `Welcome back, ${kid.child_name}!` : 'Welcome to IA KIDS!';
    document.querySelector('.mobile-intro > p').textContent = kid ? `Hello ${kid.child_name}!` : 'Hello!';
  }
  function finish(kid) {
    storage.set(childKey, JSON.stringify({ userId, id: kid.id }));
    storage.remove(pendingKey);
    paintProfile(kid);
    if (dialog.open) {
      resumeOnClose = continuation;
      continuation = null;
      dialog.close();
    } else {
      const next = continuation;
      continuation = null;
      next?.();
    }
  }
  async function api(path, body) {
    if (!sb) throw new Error('Sign in could not load. Please refresh and try again.');
    const { data, error: sessionError } = await sb.auth.getSession();
    if (sessionError || !data.session) throw new Error('Your session expired. Please sign in again.');
    const response = await fetch(API + path, {
      method: body ? 'POST' : 'GET',
      headers: { Authorization: `Bearer ${data.session.access_token}`, ...(body ? {'Content-Type':'application/json'} : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}), signal: AbortSignal.timeout(25000)
    });
    if (!response.ok) {
      if (response.status === 403) throw new Error('Your account cannot add another child. Choose an existing profile or contact support.');
      if (response.status === 401) throw new Error('Your session expired. Please sign in again.');
      throw new Error('We couldn’t load or save your child profile. Please try again.');
    }
    return response.json();
  }
  async function check(forceSelection = false, silent = false) {
    const turn = ++generation;
    if (!silent) show('loading');
    try {
      if (!sb) throw new Error('Sign in could not load. Please refresh and try again.');
      const {data: {user}, error: authError} = await sb.auth.getUser();
      if (turn !== generation || (!silent && !dialog.open)) return;
      if (!user) {
        if (silent) open(opener);
        userId = null; paintProfile(null); show('login');
        if (authError && authError.name !== 'AuthSessionMissingError') error('We couldn’t verify your session. Please try signing in again.');
        return;
      }
      userId = user.id;
      const {kids} = await api('/api/kid/list');
      if (turn !== generation || (!silent && !dialog.open)) return;
      let remembered;
      try { remembered = JSON.parse(storage.get(childKey)); } catch {}
      const selected = kids.find(k => remembered?.userId === user.id && k.id === remembered.id);
      if (!forceSelection && selected) return finish(selected);
      if (!forceSelection && kids.length === 1) return finish(kids[0]);
      if (silent) open(opener);
      if (!kids.length) { show('create'); dialog.querySelector('#authChildName').focus(); return; }
      show('children');
      const list = dialog.querySelector('.auth-children'); list.replaceChildren();
      kids.forEach(kid => {
        const button = document.createElement('button'); button.type = 'button'; button.textContent = kid.child_name;
        button.addEventListener('click', () => finish(kid)); list.append(button);
      });
      list.querySelector('button')?.focus();
    } catch (e) {
      if (turn === generation && (dialog.open || silent)) {
        if (silent) open(opener);
        show('children'); dialog.querySelector('.auth-children').replaceChildren(); error(e.message || 'Please try again.', true);
      }
    }
  }
  function requireChild(next, trigger, force = false) {
    if (dialog.open) return;
    continuation = next;
    opener = trigger || document.activeElement;
    if (force) { open(opener); check(true); }
    else check(false, true);
  }
  async function topicDraftUser(childId) {
    if (!sb || !activeChild || activeChild.id !== childId) throw new Error('Choose a child and sign in again.');
    const {data: {user}, error: authError} = await sb.auth.getUser();
    if (authError || !user) throw new Error('Your session expired. Please sign in again.');
    return user;
  }
  async function loadTopicDraft(childId) {
    await topicDraftUser(childId);
    const {data, error: draftError} = await sb.from('2027_test_prep_topics')
      .select('grade,subject,topics,custom_topics,test_date')
      .eq('child_id', childId).eq('language', 'en').maybeSingle();
    if (draftError) throw new Error('We couldn’t load your saved topics. Please try again.');
    return data;
  }
  async function saveTopicDraft(childId, draft) {
    const user = await topicDraftUser(childId);
    const {error: draftError} = await sb.from('2027_test_prep_topics').upsert({
      user_id: user.id, child_id: childId, language: 'en', grade: draft.grade,
      subject: draft.subject, topics: draft.topics, custom_topics: draft.custom,
      test_date: draft.date || null, updated_at: new Date().toISOString()
    }, {onConflict: 'child_id,language'});
    if (draftError) throw new Error('We couldn’t save your topics to your account. Please try again.');
  }
  async function loadQuickCheck(childId, topic) {
    await topicDraftUser(childId);
    const {data, error} = await sb.from('2027_test_prep_quick_checks')
      .select('question_key,answer,is_correct,hint_used')
      .eq('child_id', childId).eq('language', 'en').eq('subject', 'Math').eq('topic', topic);
    if (error) throw new Error('We couldn’t load your quick check. Please try again.');
    return data || [];
  }
  async function saveQuickCheck(childId, topic, grade, answer) {
    const user = await topicDraftUser(childId);
    const {error} = await sb.from('2027_test_prep_quick_checks').upsert({
      user_id: user.id, child_id: childId, language: 'en', grade,
      subject: 'Math', topic, question_key: answer.key,
      answer: answer.choice, is_correct: answer.correct, hint_used: answer.hintUsed,
      answered_at: new Date().toISOString()
    }, {onConflict: 'child_id,language,subject,topic,question_key'});
    if (error) throw new Error('We couldn’t save your answer. Please try again.');
  }
  window.IAKidsAuth = { requireChild, loadTopicDraft, saveTopicDraft, loadQuickCheck, saveQuickCheck, get child() { return activeChild; } };
  dialog.querySelector('.google-signin').addEventListener('click', async () => {
    if (busy) return;
    const button = dialog.querySelector('.google-signin');
    busy = true; button.disabled = true; button.querySelector('span').textContent = 'Connecting to Google…';
    try {
      if (!sb) throw new Error('Sign in could not load. Please refresh and try again.');
      storage.set(pendingKey, JSON.stringify({ action: continuation ? 'test-prep' : 'profile', at: Date.now() }));
      const {error: authError} = await sb.auth.signInWithOAuth({provider:'google', options:{redirectTo:base.href, queryParams:{prompt:'select_account'}}});
      if (authError) throw authError;
    } catch {
      error('We couldn’t connect to Google. Please try again.');
      storage.remove(pendingKey); busy = false; button.disabled = false; button.querySelector('span').textContent = 'Continue with Google';
    }
  });
  dialog.querySelector('#authChildForm').addEventListener('submit', async event => {
    event.preventDefault(); if (busy) return;
    const name = dialog.querySelector('#authChildName').value.trim();
    const grade = Number(dialog.querySelector('#authChildGrade').value);
    if (!name || !Number.isInteger(grade) || grade < 1 || grade > 6) return error('Enter your child’s name and grade.');
    busy = true; const button = dialog.querySelector('.auth-primary'); button.disabled = true; button.textContent = 'Saving…';
    const turn = generation;
    try {
      // The current tutor API stores the school grade (1–6) in its legacy age field.
      const {kid} = await api('/api/kid/create', {child_name:name, age:grade, avatar_key:'cat'});
      if (turn === generation && dialog.open) { dialog.querySelector('#authChildForm').reset(); finish(kid); }
    } catch (e) { if (turn === generation && dialog.open) error(e.message); }
    finally { busy = false; button.disabled = false; button.textContent = 'Save and continue'; }
  });
  dialog.querySelector('.auth-add').addEventListener('click', () => { show('create'); dialog.querySelector('#authChildName').focus(); });
  dialog.querySelector('.auth-back').addEventListener('click', () => check(true));
  dialog.querySelector('.auth-retry').addEventListener('click', () => check(true));
  dialog.querySelector('.auth-close').addEventListener('click', () => { if (!busy) dialog.close(); });
  dialog.addEventListener('cancel', event => { if (busy) event.preventDefault(); });
  dialog.addEventListener('close', () => {
    generation++; continuation = null; storage.remove(pendingKey);
    document.body.style.overflow = overflow || ''; opener?.focus();
    const next = resumeOnClose; resumeOnClose = null; if (next) next();
  });
  dialog.querySelector('.auth-signout').addEventListener('click', async () => {
    const {error: signoutError} = await sb.auth.signOut({scope:'local'});
    if (signoutError) return error('Sign out failed. Please try again.');
    storage.remove(childKey); userId = null; paintProfile(null); show('login');
  });
  const profile = document.querySelector('.profile');
  profile.setAttribute('role','button'); profile.setAttribute('tabindex','0'); profile.setAttribute('aria-label','Parent sign in or change learner');
  profile.addEventListener('click', () => requireChild(null, profile, true));
  profile.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); requireChild(null, profile, true); } });
  paintProfile(null);
  window.addEventListener('pageshow', () => { busy = false; const b = dialog.querySelector('.google-signin'); b.disabled = false; b.querySelector('span').textContent = 'Continue with Google'; });
  sb?.auth.onAuthStateChange(event => {
    if (event === 'SIGNED_OUT') { generation++; storage.remove(childKey); paintProfile(null); if (dialog.open) show('login'); }
  });
  window.addEventListener('iakids:prep-ready', () => {
    let pending;
    try { pending = JSON.parse(storage.get(pendingKey)); } catch {}
    const url = new URL(location.href);
    const hash = new URLSearchParams(url.hash.slice(1));
    const failed = url.searchParams.has('error') || hash.has('error');
    const callback = url.searchParams.has('code') || failed;
    if (pending && Date.now() - pending.at < 30 * 60 * 1000) {
      if (failed) { open(); show('login'); error('Google sign in was cancelled or couldn’t be completed. Please try again.'); storage.remove(pendingKey); }
      else requireChild(pending.action === 'test-prep' ? () => window.IAKidsTestPrep.open() : null);
    } else if (callback) { open(); show('login'); error('Please start sign in again from this page.'); }
    else if (sb) {
      sb.auth.getUser().then(async ({data:{user}}) => {
        if (!user || dialog.open) return;
        try {
          const saved = JSON.parse(storage.get(childKey));
          if (saved?.userId !== user.id) return;
          const {kids} = await api('/api/kid/list');
          const kid = kids.find(k => k.id === saved.id);
          if (kid && !dialog.open) paintProfile(kid);
        } catch {}
      });
    }
    if (callback) {
      // The SDK reads the callback on initialization; remove it after session processing.
      sb?.auth.getSession().finally(() => {
        const clean = new URL(location.href);
        ['code','error','error_code','error_description'].forEach(key => clean.searchParams.delete(key));
        if (failed) clean.hash = '';
        history.replaceState(null,'',clean.pathname + clean.search + clean.hash);
      });
    }
  }, {once:true});
})();
