(() => {
  'use strict';
  const API = 'https://iakids-ai-tutor-he.onrender.com';
  const $ = id => document.getElementById(id);
  const auth = window.supabase?.createClient(
    'https://bxnfzuglfwytiyaguwjj.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4bmZ6dWdsZnd5dGl5YWd1d2pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyMjk0NjUsImV4cCI6MjA4NDgwNTQ2NX0.IcmVvbboKLkJLkE31_udEtvhPl66-kmZAvmPCT_lk5o',
    {auth: {flowType: 'pkce', storageKey: 'iakids-eng-auth', persistSession: true, autoRefreshToken: true, detectSessionInUrl: false}}
  );
  let user, children = [], child, current = null, busy = false, generation = 0;
  let selectedFile = null, previewUrl = null, questionIndex = 0, choice = null;
  let voice = true, voiceSerial = 0;
  const audio = new Audio();
  try { voice = localStorage.getItem('iakids.eng.prep.voice') !== 'off'; } catch {}
  const subjects = ['Math', 'English', 'Science', 'History', 'Geography'];
  function node(tag, text, className) { const el = document.createElement(tag); if (text != null) el.textContent = text; if (className) el.className = className; return el; }
  function button(text, fn, className = 'secondary') { const el = node('button', text, className); el.type = 'button'; el.addEventListener('click', fn); return el; }
  function show(id) { ['loading', 'signin', 'chooseChild', 'workspace'].forEach(name => { $(name).hidden = name !== id; }); }
  function error(text) { $('error').textContent = text; $('error').hidden = !text; }
  function stopVoice() { voiceSerial++; audio.pause(); audio.removeAttribute("src"); }
  async function speak(text) {
    if (!voice || !current || current.approved_at) return;
    const turn = current.dialogue.findLastIndex(t => t.role === 'assistant' && t.text === text);
    if (turn < 0) return;
    stopVoice(); const serial = voiceSerial, id = current.id;
    try {
      const result = await api('audio', {kid_id: child.id, session_id: id, turn_index: turn});
      if (serial !== voiceSerial || current?.id !== id || !voice) return;
      audio.src = result.url; await audio.play();
    } catch (err) {
      if (serial === voiceSerial) { $('voice').textContent = err.name === 'NotAllowedError' ? '▶ Tap to listen' : '↻ Retry voice'; }
    }
  }
  function setVoice() { $('voice').textContent = voice ? '🔊 Listen on' : '🔈 Listen off'; $('voice').setAttribute('aria-pressed', String(voice)); }
  function bubble(role, text) { const el = node('div', text, `planner-bubble ${role === 'user' ? 'learner' : 'guide'}`); if (role !== 'user' && current) el.append(button('▶ Listen', () => { voice = true; setVoice(); speak(text); })); $('conversation').append(el); }
  async function api(path, body) {
    const {data: {session}} = await auth.auth.getSession();
    if (!session) throw new Error('Your session expired. Please sign in from the dashboard.');
    const form = body instanceof FormData;
    const response = await fetch(`${API}/api/eng/test-prep/${path}`, {method: body ? 'POST' : 'GET', headers: {Authorization: `Bearer ${session.access_token}`, ...(body && !form ? {'Content-Type': 'application/json'} : {})}, ...(body ? {body: form ? body : JSON.stringify(body)} : {}), signal: AbortSignal.timeout(180000)});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'This preparation could not be completed. Please try again.');
    return data;
  }
  function body(extra = {}) { return {kid_id: child.id, session_id: current.id, revision: current.revision, ...extra}; }
  async function run(label, fn) {
    if (busy) return;
    busy = true; error(''); stopVoice(); $('status').textContent = label; $('status').hidden = false; lock();
    try { await fn(); } catch (err) { error(err.name === 'TimeoutError' ? 'This took longer than expected. Reopen your saved preparation before retrying.' : err.message); }
    finally { busy = false; $('status').hidden = true; lock(); }
  }
  function lock() {
    document.querySelectorAll('#workspace button, #workspace input, #workspace textarea, #learnerChip').forEach(el => { el.disabled = busy; });
    $('upload').disabled = busy || !selectedFile;
    if ($('checkAnswer')) $('checkAnswer').disabled = busy || choice === null;
    if (current?.answers?.[String(questionIndex)]) document.querySelectorAll('.exercise-options button').forEach(b => { b.disabled = true; });
  }
  async function saved() {
    const id = child.id, token = generation;
    const data = await api(`preparations?kid_id=${encodeURIComponent(id)}`);
    if (token !== generation || child.id !== id) return;
    $('saved').replaceChildren();
    for (const row of data.preparations) $('saved').append(button(`${row.topic || row.source_name || 'Choose a topic'} · ${row.approved_at ? 'Approved' : 'Draft'} →`, () => run('Opening your preparation', () => open(row.id))));
  }
  function url(id) { const u = new URL(location.href); u.search = ''; if (id) u.searchParams.set('prep', id); history.replaceState(null, '', u); }
  async function open(id) {
    stopVoice();
    current = await api(`preparation/${encodeURIComponent(id)}?kid_id=${encodeURIComponent(child.id)}`);
    url(current.id); questionIndex = Object.keys(current.answers).length; choice = null; clearFile(); render();
  }
  function clearFile() { selectedFile = null; $('material').value = ''; if (previewUrl) URL.revokeObjectURL(previewUrl); previewUrl = null; $('preview').removeAttribute('src'); $('preview').hidden = true; $('filename').textContent = ''; }
  function renderDraft() {
    $('draft').replaceChildren(); $('draftTitle').textContent = current?.pack?.title || 'Your test preparation';
    $('draftSubtitle').textContent = current?.pack?.overview || (current?.source_name ? `Based on: ${current.source_name}` : 'Choose one topic. Your exercises will appear here for review.');
    $('approve').hidden = !current?.pack || !!current.approved_at; $('lockNote').hidden = !current?.pack;
    $('lockNote').textContent = current?.approved_at ? 'Approved and locked. Your progress is saved automatically.' : 'Review the exercises. After approval, this set is locked.';
    if (!current?.pack) return;
    $('draft').append(node('p', `${current.pack.questions.length} exercises · Grade ${current.grade}`, 'eyebrow'));
    $('draft').append(node('p', current.pack.skills.join(' · '), 'skills'));
    current.pack.questions.forEach((q, i) => {
      const detail = node('details'); detail.append(node('summary', `${i + 1}. ${q.prompt}`));
      if (q.context) detail.append(node('p', q.context));
      const options = node('ol'); q.options.forEach(value => options.append(node('li', value))); detail.append(options); $('draft').append(detail);
    });
  }
  function render() {
    show('workspace'); renderDraft(); $('uploadPanel').hidden = true; $('conversation').replaceChildren(); $('suggestions').replaceChildren();
    $('composer').hidden = !current || !!current.approved_at; $('exercise').hidden = !current?.approved_at;
    if (!current) return;
    if (current.approved_at) { renderExercise(); return; }
    for (const turn of current.dialogue) bubble(turn.role, turn.text);
    const last = current.dialogue.at(-1);
    for (const text of last?.options || []) $('suggestions').append(button(text, () => send(text), 'choice'));
    if (current.mode === 'topics' && current.dialogue.length === 1) for (const text of subjects) $('suggestions').append(button(text, () => send(text), 'choice'));
    if (current.source_name && !current.pack) $('suggestions').append(button('Build exercises from my material', () => send('Build exercises from my uploaded material.'), 'choice'));
    $('conversation').scrollTop = $('conversation').scrollHeight;
  }
  function home(mode) {
    stopVoice(); error(''); current = null; clearFile(); url(null); render(); $('composer').hidden = true;
    bubble('assistant', `Hi ${child.child_name}! How would you like to prepare for your test? We’ll create exercises, then you can review and approve them.`);
    for (const [key, title] of [['topics', 'Choose one topic'], ['photo', 'Take or upload a photo'], ['file', 'Upload a file']]) $('suggestions').append(button(title, () => begin(key), 'choice'));
    if (mode) begin(mode);
  }
  function begin(mode) {
    if (busy) return;
    if (mode === 'topics') run('Starting your preparation', async () => { current = await api('start', {kid_id: child.id, mode}); url(current.id); render(); await saved(); speak(current.dialogue.at(-1).text); });
    else {
      $('conversation').replaceChildren(); $('suggestions').replaceChildren(); $('uploadPanel').hidden = false;
      $('uploadTitle').textContent = mode === 'photo' ? 'Take or upload a photo' : 'Upload your test material';
      $('material').accept = mode === 'photo' ? 'image/jpeg,image/png,image/webp' : '.pdf,.docx,.txt,.jpg,.jpeg,.png,.webp';
      // No capture restriction: mobile learners may use their camera or photo library.
      bubble('assistant', 'Send the material you want to prepare from. I’ll read it and build exercises for you to review.'); lock();
    }
  }
  async function send(text) {
    if (!text.trim() || !current || current.approved_at) return;
    await run('Preparing and checking your exercises', async () => {
      const next = await api('reply', body({message: text.trim()})); current = next; $('message').value = ''; render(); await saved(); speak(current.dialogue.at(-1).text);
    });
  }
  function renderExercise() {
    const root = $('exercise'); root.replaceChildren();
    const questions = current.pack.questions;
    if (questionIndex >= questions.length) {
      const correct = Object.values(current.answers).filter(a => a.correct).length;
      root.append(node('span', 'PREPARATION COMPLETE', 'eyebrow'), node('h2', 'You finished your practice!'), node('p', `${correct} / ${questions.length}`, 'score'), node('p', 'Review your answers below. You can create another preparation for more practice.'));
      questions.forEach((q, i) => { const a = current.answers[String(i)]; if (!a) return; const card = node('div', null, 'review-answer'); card.append(node('strong', `${i + 1}. ${q.prompt}`), node('p', `${a.correct ? '✓ Correct' : 'Review'} · Your answer: ${q.options[a.option_index]}`), node('p', `Correct answer: ${q.options[a.correct_index]}`), node('p', a.explanation)); root.append(card); });
      root.append(button('Create another preparation', () => home(), 'primary')); return;
    }
    const q = questions[questionIndex], answer = current.answers[String(questionIndex)];
    root.append(node('span', `EXERCISE ${questionIndex + 1} OF ${questions.length}`, 'eyebrow'));
    if (q.context) root.append(node('p', q.context, 'exercise-context'));
    root.append(node('h2', q.prompt));
    const options = node('div', null, 'exercise-options');
    q.options.forEach((text, i) => { const b = button(text, () => { if (busy || answer) return; choice = i; renderExercise(); }, ''); b.setAttribute('aria-pressed', String((answer?.option_index ?? choice) === i)); if (answer) { b.disabled = true; if (i === answer.correct_index) b.classList.add('correct'); else if (i === answer.option_index) b.classList.add('wrong'); } options.append(b); });
    root.append(options);
    if (answer) { root.append(node('p', `${answer.correct ? 'Correct! ' : 'Let’s review. '}${answer.explanation}`, 'feedback')); root.append(button(questionIndex + 1 === questions.length ? 'See my results →' : 'Next exercise →', () => { questionIndex++; choice = null; renderExercise(); }, 'primary')); }
    else { const check = button('Check answer →', () => run('Checking your answer', async () => { current = await api('answer', body({question_index: questionIndex, option_index: choice})); renderExercise(); }), 'primary'); check.id = 'checkAnswer'; check.disabled = choice === null; root.append(check); }
  }
  function picker() { if (busy) return; stopVoice(); generation++; $('childChoices').replaceChildren(); for (const kid of children) $('childChoices').append(button(`${kid.child_name} · Grade ${kid.age}`, () => selectChild(kid), 'choice')); show('chooseChild'); }
  async function selectChild(kid, initial = false) {
    child = kid; generation++; current = null; $('learnerChip').hidden = false; $('learnerChip').textContent = `${kid.child_name} · Grade ${kid.age} ▾`; $('gradeLabel').textContent = `${kid.child_name} · Grade ${kid.age}`;
    try { sessionStorage.setItem('iakids.eng.child', JSON.stringify({userId: user.id, id: kid.id})); } catch {}
    const params = new URLSearchParams(location.search); show('workspace'); home();
    await run('Loading your saved preparations', async () => { await saved(); if (initial && params.get('prep')) await open(params.get('prep')); });
    if (initial && !params.get('prep') && ['topics','file','photo'].includes(params.get('mode'))) begin(params.get('mode'));
  }
  $('composer').addEventListener('submit', event => { event.preventDefault(); send($('message').value); });
  $('newPrep').addEventListener('click', () => home()); $('learnerChip').addEventListener('click', picker);
  $('voice').addEventListener('click', () => { voice = !voice; setVoice(); try { localStorage.setItem('iakids.eng.prep.voice', voice ? 'on' : 'off'); } catch {} if (voice && current?.dialogue.length) speak(current.dialogue.at(-1).text); else stopVoice(); }); setVoice();
  $('material').addEventListener('change', () => {
    selectedFile = $('material').files[0] || null; error('');
    if (previewUrl) URL.revokeObjectURL(previewUrl); previewUrl = null; $('preview').hidden = true;
    if (selectedFile && (!selectedFile.size || selectedFile.size > 10 * 1024 * 1024)) { selectedFile = null; error('Choose a non-empty file up to 10 MB.'); }
    $('filename').textContent = selectedFile?.name || '';
    if (selectedFile?.type.startsWith('image/')) { previewUrl = URL.createObjectURL(selectedFile); $('preview').src = previewUrl; $('preview').hidden = false; }
    lock();
  });
  $('upload').addEventListener('click', async () => {
    if (!selectedFile) return;
    await run('Reading your material', async () => { const form = new FormData(); form.append('kid_id', child.id); form.append('file', selectedFile); current = await api('material', form); url(current.id); clearFile(); render(); await saved(); });
    if (current && !current.pack && current.source_name) await send('Build exercises from my uploaded material.');
  });
  $('approve').addEventListener('click', () => { $('approval').returnValue = ''; $('approval').showModal(); });
  $('approval').addEventListener('close', () => { if ($('approval').returnValue !== 'approve') return; run('Saving your approved exercises', async () => { current = await api('approve', body()); questionIndex = Object.keys(current.answers).length; choice = null; render(); await saved(); }); });
  window.addEventListener('pagehide', stopVoice);
  async function initialize() {
    try {
      const {data} = await auth.auth.getUser(); user = data.user;
      if (!user) { show('signin'); return; }
      const {data: {session}} = await auth.auth.getSession();
      const response = await fetch(`${API}/api/kid/list`, {headers: {Authorization: `Bearer ${session.access_token}`}, signal: AbortSignal.timeout(30000)});
      if (!response.ok) throw new Error('Could not load your learner profiles.');
      children = (await response.json()).kids || [];
      if (!children.length) { show('signin'); return; }
      let stored; try { stored = JSON.parse(sessionStorage.getItem('iakids.eng.child')); } catch {}
      const selected = children.find(k => stored?.userId === user.id && k.id === stored.id);
      if (selected || children.length === 1) await selectChild(selected || children[0], true); else picker();
    } catch (err) { show('signin'); $('signin').append(node('p', err.message)); }
  }
  initialize();
})();
