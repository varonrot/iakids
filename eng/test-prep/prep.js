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
  let pendingSpeech = null, typingFrame = 0, mediaWait = null;
  try { voice = localStorage.getItem('iakids.eng.prep.voice') !== 'off'; } catch {}
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  function stopMic() { const instance = recognition; recognition = null; if (instance) instance.abort(); $('mic').classList.remove('listening'); $('mic').setAttribute('aria-pressed', 'false'); $('mic').setAttribute('aria-label', 'Dictate your message'); }
  const subjects = ['Math', 'English', 'Science', 'History', 'Geography'];
  function node(tag, text, className) { const el = document.createElement(tag); if (text != null) el.textContent = text; if (className) el.className = className; return el; }
  function button(text, fn, className = 'secondary') { const el = node('button', text, className); el.type = 'button'; el.addEventListener('click', fn); return el; }
  function show(id) { ['loading', 'signin', 'chooseChild', 'workspace'].forEach(name => { $(name).hidden = name !== id; }); }
  function error(text) { $('error').textContent = text; $('error').hidden = !text; }
  function stopVoice() {
    voiceSerial++; mediaWait?.abort(); mediaWait = null;
    cancelAnimationFrame(typingFrame); document.querySelectorAll('[data-full-text]').forEach(el => { el.textContent = el.dataset.fullText; delete el.dataset.fullText; }); audio.pause(); audio.removeAttribute('src');
  }
  function typeText(el, text, withAudio = false) {
    cancelAnimationFrame(typingFrame);
    const characters = Array.from(text), started = performance.now();
    let shown = 0;
    const tick = () => {
      if (!el.isConnected) return;
      const duration = Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : characters.length / 24;
      const progress = withAudio ? (audio.ended ? 1 : audio.currentTime / duration) : (performance.now() - started) / (characters.length * 24);
      // Reveal progressively, using playback time so buffering also pauses the text.
      shown = Math.max(shown, Math.min(characters.length, Math.floor(progress * characters.length)));
      el.textContent = characters.slice(0, shown).join('');
      $('conversation').scrollTop = $('conversation').scrollHeight;
      if (shown < characters.length) typingFrame = requestAnimationFrame(tick);
    };
    typingFrame = requestAnimationFrame(tick);
  }
  function revealPending(withAudio) {
    const item = pendingSpeech;
    if (!item || !item.el.isConnected || current?.id !== item.id) return;
    pendingSpeech = null; item.el.removeAttribute('aria-busy'); item.el.replaceChildren();
    const words = node('span', ''); words.dataset.fullText = item.text; item.el.append(words);
    item.el.append(button('▶ Listen', () => { voice = true; setVoice(); speak(item.text); }));
    $('suggestions').hidden = false; $('composer').hidden = false;
    typeText(words, item.text, withAudio);
  }
  function waitForAudio() {
    mediaWait = new AbortController();
    const signal = mediaWait.signal;
    return new Promise((resolve, reject) => {
      let timeout;
      const finish = err => { clearTimeout(timeout); audio.removeEventListener('canplay', ready); audio.removeEventListener('error', failed); signal.removeEventListener('abort', cancelled); err ? reject(err) : resolve(); };
      const ready = () => finish();
      const failed = () => finish(new Error('Voice could not load.'));
      const cancelled = () => finish(new DOMException('Cancelled', 'AbortError'));
      audio.addEventListener('canplay', ready, {once:true}); audio.addEventListener('error', failed, {once:true}); signal.addEventListener('abort', cancelled, {once:true});
      timeout = setTimeout(failed, 30000); audio.load();
      if (audio.readyState >= 3) ready();
    });
  }
  async function speak(text) {
    if (!voice || !current || current.approved_at) return;
    const turn = current.dialogue.findLastIndex(t => t.role === 'assistant' && t.text === text);
    if (turn < 0) return;
    const target = pendingSpeech?.text === text ? pendingSpeech.el : [...$('conversation').querySelectorAll('[data-speech-text]')].findLast(el => el.dataset.speechText === text);
    stopVoice(); const serial = voiceSerial, id = current.id;
    // Replays and restored conversations use the same reveal path as a fresh reply.
    if (target?.isConnected) pendingSpeech = {el: target, text, id};
    const item = pendingSpeech;
    if (item?.id === id && item.text === text) { item.el.replaceChildren(node('span', 'Preparing your guide’s voice…', 'voice-wait')); item.el.setAttribute('aria-busy', 'true'); }
    try {
      const result = await api('audio', {kid_id: child.id, session_id: id, turn_index: turn});
      if (serial !== voiceSerial || current?.id !== id || !voice) return;
      audio.src = result.url; await waitForAudio();
      audio.currentTime = 0;
      if (serial !== voiceSerial || current?.id !== id || !voice) return;
      await audio.play();
      if (serial !== voiceSerial || current?.id !== id || !voice) return;
      setVoice(); revealPending(true);
    } catch (err) {
      if (serial !== voiceSerial || err.name === 'AbortError') return;
      $('voice').textContent = err.name === 'NotAllowedError' ? '▶ Tap to listen' : '↻ Retry voice';
      if (pendingSpeech === item && item?.el.isConnected) {
        item.el.removeAttribute('aria-busy');
        item.el.replaceChildren(node('span', err.name === 'NotAllowedError' ? 'Your guide is ready. Tap to listen.' : 'The voice could not load yet.'));
        item.el.append(button('▶ Listen / retry', () => speak(text)), button('Read without sound', () => { voice = false; stopVoice(); setVoice(); revealPending(false); }));
      }
    }
  }
  function setVoice() { $('voice').textContent = voice ? '🔊 Listen on' : '🔈 Listen off'; $('voice').setAttribute('aria-pressed', String(voice)); }
  function bubble(role, text, fresh = false) {
    const el = node('div', null, `planner-bubble ${role === 'user' ? 'learner' : 'guide'}`);
    if (role === 'assistant') el.dataset.speechText = text;
    $('conversation').append(el);
    if (fresh && role === 'assistant' && current) {
      pendingSpeech = {el, text, id:current.id};
      if (voice) { el.append(node('span', 'Preparing your guide’s voice…', 'voice-wait')); el.setAttribute('aria-busy', 'true'); }
      else revealPending(false);
    } else {
      el.append(node('span', text));
      if (role !== 'user' && current) el.append(button('▶ Listen', () => { voice = true; setVoice(); speak(text); }));
    }
  }
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
    busy = true; stopMic(); error(''); stopVoice(); $('status').textContent = label; $('status').hidden = false; lock();
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
    url(current.id); questionIndex = Object.keys(current.answers).length; choice = null; clearFile(); render(true);
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
  function render(fresh = false) {
    pendingSpeech = null; $('suggestions').hidden = false;
    show('workspace'); renderDraft(); $('uploadPanel').hidden = true; $('conversation').replaceChildren(); $('suggestions').replaceChildren();
    $('composer').hidden = !current || !!current.approved_at; $('exercise').hidden = !current?.approved_at;
    if (!current) return;
    if (current.approved_at) { renderExercise(); return; }
    current.dialogue.forEach((turn, index) => bubble(turn.role, turn.text, fresh && index === current.dialogue.length - 1));
    const last = current.dialogue.at(-1);
    for (const text of last?.options || []) $('suggestions').append(button(text, () => send(text), 'choice'));
    if (current.mode === 'topics' && current.dialogue.length === 1) for (const text of subjects) $('suggestions').append(button(text, () => text === 'Math' ? chooseMath() : send(text), 'choice'));
    if (current.source_name && !current.pack) $('suggestions').append(button('Build exercises from my material', () => send('Build exercises from my uploaded material.'), 'choice'));
    if (pendingSpeech) { $('suggestions').hidden = true; $('composer').hidden = true; speak(pendingSpeech.text); }
    $('conversation').scrollTop = $('conversation').scrollHeight;
  }
  function home(mode) {
    stopMic(); stopVoice(); error(''); current = null; clearFile(); url(null); render(); $('composer').hidden = true;
    bubble('assistant', `Hi ${child.child_name}! How would you like to prepare for your test? We’ll create exercises, then you can review and approve them.`);
    for (const [key, title] of [['topics', 'Choose one topic'], ['photo', 'Take or upload a photo'], ['file', 'Upload a file']]) $('suggestions').append(button(title, () => begin(key), 'choice'));
    if (mode) begin(mode);
  }
  function begin(mode) {
    if (busy) return;
    if (mode === 'topics') run('Starting your preparation', async () => { current = await api('start', {kid_id: child.id, mode}); url(current.id); render(true); await saved(); });
    else {
      $('conversation').replaceChildren(); $('suggestions').replaceChildren(); $('uploadPanel').hidden = false;
      $('uploadTitle').textContent = mode === 'photo' ? 'Take or upload a photo' : 'Upload your test material';
      $('material').accept = mode === 'photo' ? 'image/jpeg,image/png,image/webp' : '.pdf,.docx,.txt,.jpg,.jpeg,.png,.webp';
      // No capture restriction: mobile learners may use their camera or photo library.
      bubble('assistant', 'Send the material you want to prepare from. I’ll read it and build exercises for you to review.'); lock();
    }
  }
  async function chooseMath() {
    await run('Loading Math topics', async () => {
      const {domains} = await api(`curriculum-map?kid_id=${encodeURIComponent(child.id)}`);
      const showDomains = () => {
        $('suggestions').replaceChildren(...domains.map(domain => button(domain.title, () => {
          $('suggestions').replaceChildren(...domain.children.map(topic => {
            const b = button(topic.title, () => send(topic.title, topic.id), 'choice');
            b.title = topic.children.map(skill => skill.title).join(' · '); return b;
          }), button('← All Math areas', showDomains, 'choice'));
        }, 'choice')), button('← Subjects', () => render(), 'choice'));
      };
      showDomains();
    });
  }
  async function send(text, curriculumTopicId = '') {
    if (!text.trim() || !current || current.approved_at) return;
    await run('Preparing and checking your exercises', async () => {
      const next = await api('reply', body({message: text.trim(), curriculum_topic_id: curriculumTopicId})); current = next; $('message').value = ''; render(true); await saved();
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
  function picker() { if (busy) return; stopMic(); stopVoice(); generation++; $('childChoices').replaceChildren(); for (const kid of children) $('childChoices').append(button(`${kid.child_name} · Grade ${kid.age}`, () => selectChild(kid), 'choice')); show('chooseChild'); }
  async function selectChild(kid, initial = false) {
    child = kid; generation++; current = null; $('learnerChip').hidden = false; $('learnerChip').textContent = `${kid.child_name} · Grade ${kid.age} ▾`; $('gradeLabel').textContent = `${kid.child_name} · Grade ${kid.age}`;
    try { sessionStorage.setItem('iakids.eng.child', JSON.stringify({userId: user.id, id: kid.id})); } catch {}
    const params = new URLSearchParams(location.search); show('workspace'); home();
    await run('Loading your saved preparations', async () => { await saved(); if (initial && params.get('prep')) await open(params.get('prep')); });
    if (initial && !params.get('prep') && ['topics','file','photo'].includes(params.get('mode'))) begin(params.get('mode'));
  }
  $('mic').addEventListener('click', () => {
    if (recognition) { recognition.stop(); return; }
    if (!Recognition) { error('Voice typing is not available in this browser. You can type your message or use Chrome.'); return; }
    if (busy || !current || current.approved_at || $('composer').hidden) return;
    stopVoice(); error('');
    const instance = new Recognition(), id = current.id, kid = child.id;
    const prefix = $('message').value.trim();
    recognition = instance; instance.lang = 'en-US'; instance.interimResults = true; instance.continuous = false;
    instance.onresult = event => {
      if (recognition !== instance || current?.id !== id || child.id !== kid) return;
      const transcript = Array.from(event.results).map(result => result[0].transcript).join(' ');
      $('message').value = [prefix, transcript].filter(Boolean).join(' ').slice(0, 1000);
    };
    instance.onerror = event => {
      if (recognition !== instance || event.error === 'aborted') return;
      error(event.error === 'not-allowed' ? 'Allow microphone access in your browser to dictate a message.' : event.error === 'no-speech' ? 'I didn’t hear anything. Tap the microphone and try again.' : 'Voice typing could not start. Please try again or type your message.');
    };
    instance.onend = () => {
      if (recognition !== instance) return;
      recognition = null; $('mic').classList.remove('listening'); $('mic').setAttribute('aria-pressed', 'false'); $('mic').setAttribute('aria-label', 'Dictate your message'); $('message').focus();
    };
    try {
      instance.start(); $('mic').classList.add('listening'); $('mic').setAttribute('aria-pressed', 'true'); $('mic').setAttribute('aria-label', 'Stop dictation');
    } catch { stopMic(); error('The microphone could not start. Please try again.'); }
  });
  $('composer').addEventListener('submit', event => { event.preventDefault(); send($('message').value); });
  $('newPrep').addEventListener('click', () => home()); $('learnerChip').addEventListener('click', picker);
  $('voice').addEventListener('click', () => { voice = !voice; setVoice(); try { localStorage.setItem('iakids.eng.prep.voice', voice ? 'on' : 'off'); } catch {} if (voice && current?.dialogue.length) speak(current.dialogue.at(-1).text); else { stopVoice(); revealPending(false); } }); setVoice();
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
    await run('Reading your material', async () => { const form = new FormData(); form.append('kid_id', child.id); form.append('file', selectedFile); current = await api('material', form); url(current.id); clearFile(); render(); $('conversation').replaceChildren(node('p', 'Your material is ready. Preparing exercises…', 'voice-wait')); await saved(); });
    if (current && !current.pack && current.source_name) await send('Build exercises from my uploaded material.');
  });
  $('approve').addEventListener('click', () => { $('approval').returnValue = ''; $('approval').showModal(); });
  $('approval').addEventListener('close', () => { if ($('approval').returnValue !== 'approve') return; run('Saving your approved exercises', async () => { current = await api('approve', body()); questionIndex = Object.keys(current.answers).length; choice = null; render(); await saved(); }); });
  window.addEventListener('pagehide', () => { stopMic(); stopVoice(); });
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
