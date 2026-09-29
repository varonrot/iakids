(() => {
  'use strict';
  const API = 'https://iakids-ai-tutor-he.onrender.com';
  const childKey = 'iakids.eng.child';
  const voiceKey = 'iakids.eng.learning.voice';
  const $ = id => document.getElementById(id);
  const auth = window.supabase?.createClient(
    'https://bxnfzuglfwytiyaguwjj.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4bmZ6dWdsZnd5dGl5YWd1d2pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyMjk0NjUsImV4cCI6MjA4NDgwNTQ2NX0.IcmVvbboKLkJLkE31_udEtvhPl66-kmZAvmPCT_lk5o',
    {auth: {flowType: 'pkce', storageKey: 'iakids-eng-auth', persistSession: true, autoRefreshToken: true, detectSessionInUrl: false}}
  );
  const views = ['loading', 'signin', 'chooseChild', 'path', 'lesson'];
  let user, children = [], child, catalog, subject, unit, recent, current, count = 0, busy = false, generation = 0, activeOptions = [];
  let voiceEnabled = true, audioSerial = 0, playingKey = '';
  let lessonDiagram, teacherTurns = [];
  const audioUrls = new Map();
  try { voiceEnabled = localStorage.getItem(voiceKey) !== 'off'; } catch {}
  // The key is public. Keep the exact same anon key as the English dashboard.

  function show(name) { views.forEach(id => { $(id).hidden = id !== name; }); $('error').hidden = true; }
  function error(message) { $('error').textContent = message; $('error').hidden = false; }
  async function api(path, body, timeoutMs = 30000) {
    const {data: {session}, error: authError} = await auth.auth.getSession();
    if (authError || !session?.access_token) throw new Error('Your session expired. Return to the dashboard to sign in.');
    const response = await fetch(`${API}/api/eng/learning/${path}`, {
      method: body ? 'POST' : 'GET',
      headers: {Authorization: `Bearer ${session.access_token}`, ...(body ? {'Content-Type': 'application/json'} : {})},
      ...(body ? {body: JSON.stringify(body)} : {}), signal: AbortSignal.timeout(timeoutMs)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Your lesson could not load. Please try again.');
    return result;
  }
  function childPicker() {
    const list = $('childChoices'); list.replaceChildren();
    for (const kid of children) {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'choice';
      const icon = document.createElement('span'); icon.className = 'choice-icon'; icon.textContent = kid.child_name[0]?.toUpperCase() || '✦';
      const title = document.createElement('strong'); title.textContent = kid.child_name;
      const grade = document.createElement('small'); grade.textContent = `Grade ${kid.age}`;
      button.append(icon, title, grade); button.addEventListener('click', () => selectChild(kid)); list.append(button);
    }
    show('chooseChild');
  }
  async function selectChild(kid) {
    child = kid; ++generation;
    try { sessionStorage.setItem(childKey, JSON.stringify({userId: user.id, id: kid.id})); } catch {}
    $('learnerChip').textContent = `${kid.child_name} · Grade ${kid.age} ▾`;
    $('learnerChip').hidden = false;
    show('loading');
    try {
      const result = await api(`catalog?kid_id=${encodeURIComponent(kid.id)}`);
      catalog = result.subjects; recent = result.recent;
      subject = null; unit = null; renderPath();
    } catch (err) { childPicker(); error(err.message); }
  }
  function choice(iconText, titleText, detailText, action) {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'choice';
    const icon = document.createElement('span'); icon.className = 'choice-icon'; icon.textContent = iconText;
    const title = document.createElement('strong'); title.textContent = titleText;
    const detail = document.createElement('small'); detail.textContent = detailText;
    button.append(icon, title, detail); button.addEventListener('click', action); return button;
  }
  function renderPath() {
    show('path');
    const title = $('pathTitle'), description = $('pathDescription'), list = $('pathChoices'), crumbs = $('crumbs');
    list.replaceChildren(); crumbs.replaceChildren();
    const addCrumb = (label, action) => { const button = document.createElement('button'); button.type = 'button'; button.textContent = label; button.addEventListener('click', action); crumbs.append(button); };
    addCrumb(`Grade ${child.age}`, () => { subject = null; unit = null; renderPath(); });
    if (subject) addCrumb(subject.title, () => { unit = null; renderPath(); });
    if (unit) addCrumb(unit.title, () => renderPath());
    if (!subject) {
      title.textContent = `What will you learn, ${child.child_name}?`;
      description.textContent = 'Choose a subject to explore your learning path.';
      catalog.forEach(item => list.append(choice('∑', item.title, `${item.units.length} learning areas`, () => { subject = item; renderPath(); })));
    } else if (!unit) {
      title.textContent = `Explore ${subject.title}`;
      description.textContent = 'Pick an area to see the ideas in learning order.';
      subject.units.forEach(item => list.append(choice(item.id === 'fractions' ? '⅓' : '%', item.title, `${item.skills.length} learning steps`, () => { unit = item; renderPath(); })));
    } else {
      title.textContent = `${unit.title}, step by step`;
      description.textContent = 'Choose a skill, or let us guide you from the beginning.';
      unit.skills.forEach((item, index) => list.append(choice(item.icon, item.title, `Step ${index + 1} · Learn with your teacher`, () => start(item))));
    }
    if (!catalog.length) { description.textContent = `Learning paths for Grade ${child.age} are being prepared.`; $('notSure').hidden = true; }
    else $('notSure').hidden = false;
    $('recent').hidden = !recent;
    if (recent) $('recentButton').textContent = 'Resume lesson →';
  }
  $('notSure').addEventListener('click', () => {
    if (!subject) subject = catalog[0];
    if (!unit) unit = subject.units[0];
    start(unit.skills[0]);
  });
  $('recentButton').addEventListener('click', async () => {
    if (!recent || busy) return;
    const chosen = catalog.flatMap(s => s.units).find(u => u.id === recent.unit_id);
    subject = catalog.find(s => s.units.includes(chosen)); unit = chosen;
    if (!unit) { error('That lesson is no longer available. Choose a new step.'); return; }
    busy = true; show('loading');
    try { openLesson(await api('resume', {kid_id: child.id, session_id: recent.id})); }
    catch (err) { renderPath(); error(err.message); }
    finally { busy = false; }
  });
  async function start(skill) {
    if (busy) return;
    busy = true; show('loading');
    try { openLesson(await api('start', {kid_id: child.id, unit_id: unit.id, skill_id: skill.id})); }
    catch (err) { renderPath(); error(err.message); }
    finally { busy = false; }
  }
  function bubble(role, text, pending = false) {
    const item = document.createElement('div'); item.className = `bubble ${role}${pending ? ' pending' : ''}`;
    const words = document.createElement('span'); words.className = 'bubble-text'; words.textContent = text;
    item.append(words); $('messages').append(item); $('messages').scrollTop = $('messages').scrollHeight;
    return item;
  }
  function replayButton(item, index) {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'replay-voice';
    button.textContent = '▶ Listen'; button.setAttribute('aria-label', `Play teacher message ${index + 1}`);
    button.addEventListener('click', () => playTeacher(index)); item.append(button);
  }
  function voiceStatus(message) {
    $('voiceStatus').textContent = message;
    $('voiceStatus').hidden = !message;
  }
  function stopVoice() {
    ++audioSerial;
    $('teacherAudio').pause(); $('teacherAudio').removeAttribute('src'); $('teacherAudio').load();
    playingKey = ''; voiceStatus('');
  }
  function updateVoiceToggle() {
    $('voiceToggle').textContent = voiceEnabled ? '🔊 Voice on' : '🔇 Voice off';
    $('voiceToggle').setAttribute('aria-pressed', String(voiceEnabled));
  }
  async function playTeacher(index, automatic = false) {
    if (!current || (automatic && !voiceEnabled)) return;
    if (!voiceEnabled) {
      voiceEnabled = true; updateVoiceToggle();
      try { localStorage.setItem(voiceKey, 'on'); } catch {}
    }
    const request = ++audioSerial, version = generation, sessionId = current;
    const key = `${sessionId}:${index}`;
    $('teacherAudio').pause(); voiceStatus('Preparing the teacher’s voice…');
    try {
      let cached = audioUrls.get(key);
      if (!cached || cached.expiresAt < Date.now()) {
        const result = await api('audio', {kid_id: child.id, session_id: sessionId, turn_index: index}, 120000);
        cached = {url: result.url, expiresAt: Date.now() + 9 * 60 * 1000};
        audioUrls.set(key, cached);
      }
      if (request !== audioSerial || version !== generation || sessionId !== current || !voiceEnabled) return;
      playingKey = key; $('teacherAudio').src = cached.url;
      await $('teacherAudio').play();
      if (request === audioSerial) voiceStatus('');
    } catch (err) {
      if (request !== audioSerial) return;
      voiceStatus(err.name === 'NotAllowedError'
        ? 'Tap ▶ Listen to hear the teacher.' : 'Voice is unavailable. You can continue reading.');
    }
  }
  $('voiceToggle').addEventListener('click', () => {
    voiceEnabled = !voiceEnabled; updateVoiceToggle();
    try { localStorage.setItem(voiceKey, voiceEnabled ? 'on' : 'off'); } catch {}
    if (!voiceEnabled) stopVoice();
    else if (current) playTeacher(count - 1);
  });
  $('teacherAudio').addEventListener('error', () => {
    if (!playingKey) return;
    audioUrls.delete(playingKey);
    voiceStatus('Voice could not load. Tap ▶ Listen to try again.');
  });
  updateVoiceToggle();
  function renderChoices(options) {
    activeOptions = Array.isArray(options) ? options : [];
    const target = $('answerChoices'); target.replaceChildren();
    for (const option of activeOptions) {
      const button = document.createElement('button'); button.type = 'button';
      button.textContent = option; button.addEventListener('click', () => sendMessage(option));
      target.append(button);
    }
    target.hidden = !activeOptions.length;
  }
  function bar(label, denominator, shaded) {
    const row = document.createElement('div'); row.className = 'bar-row';
    const title = document.createElement('b'); title.textContent = label;
    const track = document.createElement('div'); track.className = 'bar';
    for (let i = 0; i < denominator; i++) { const cell = document.createElement('i'); if (i < shaded) cell.className = 'filled'; track.append(cell); }
    row.append(title, track); return row;
  }
  function examples(kind, text) {
    const fractions = [...text.matchAll(/\b(\d{1,2})\s*\/\s*(\d{1,2})\b/g)]
      .map(([, numerator, denominator]) => ({numerator: Number(numerator), denominator: Number(denominator)}))
      .filter(({numerator, denominator}) => denominator >= 2 && denominator <= 16 && numerator <= denominator);
    if (['equivalent', 'compare', 'add', 'unlike'].includes(kind)) {
      const unique = fractions.filter((fraction, index) => fractions.findIndex(other =>
        other.numerator === fraction.numerator && other.denominator === fraction.denominator) === index);
      return unique.length >= 2 ? unique.slice(0, 2) : null;
    }
    if (kind === 'line') {
      const mixed = text.match(/\b(\d)\s+(\d{1,2})\s*\/\s*(\d{1,2})\b/);
      if (mixed && Number(mixed[3]) >= 2 && Number(mixed[3]) <= 16 && Number(mixed[2]) < Number(mixed[3]))
        return {whole: Number(mixed[1]), numerator: Number(mixed[2]), denominator: Number(mixed[3])};
      return null;
    }
    const percent = text.match(/\b(\d{1,3})\s*%/);
    return percent && Number(percent[1]) <= 100 ? Number(percent[1]) : null;
  }
  function diagram(kind, turns) {
    const target = $('diagram'); target.replaceChildren();
    // Use the latest complete example. A follow-up that says only "that fraction"
    // keeps the preceding diagram rather than introducing unrelated numbers.
    const example = [...turns].reverse().filter(turn => turn.role === 'assistant')
      .map(turn => examples(kind, turn.text)).find(value => value !== null);
    let caption = 'The teacher’s next numerical example will appear here.';
    if (Array.isArray(example)) {
      target.append(...example.map(({numerator, denominator}) =>
        bar(`${numerator}/${denominator}`, denominator, numerator)));
      caption = 'Each bar represents the same whole. Compare the shaded areas.';
    } else if (typeof example === 'number') {
      const grid = document.createElement('div'); grid.className = 'hundred';
      for (let i = 0; i < 100; i++) { const cell = document.createElement('i'); if (i < example) cell.className = 'filled'; grid.append(cell); }
      target.append(grid); caption = `${example} of 100 equal squares are shaded.`;
    } else if (kind === 'line' && example) {
      const {whole, numerator, denominator} = example;
      const max = Math.max(3, whole + 1), steps = max * denominator;
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('viewBox', '0 0 470 100'); svg.setAttribute('class', 'number-line'); svg.setAttribute('aria-hidden', 'true');
      const x = step => 25 + 420 * step / steps;
      svg.innerHTML = '<path d="M25 48H445" stroke="#126c83" stroke-width="3"/>' +
        Array.from({length: steps + 1}, (_, i) => `<path d="M${x(i)} 40v16" stroke="#126c83" stroke-width="2"/>`).join('') +
        `<circle cx="${x(whole * denominator + numerator)}" cy="48" r="7" fill="#0bb8ad"/>` +
        Array.from({length: max + 1}, (_, i) => `<text x="${x(i * denominator) - 5}" y="83">${i}</text>`).join('');
      target.append(svg); caption = `The point is at ${whole} ${numerator}/${denominator} on a line divided into ${denominator} equal parts per whole.`;
    }
    $('diagramCaption').textContent = caption; target.setAttribute('aria-label', caption);
  }
  function openLesson(result) {
    stopVoice();
    current = result.session_id; count = result.turn_count; ++generation;
    $('gradeLabel').textContent = child.age; $('skillTitle').textContent = result.skill.title;
    lessonDiagram = result.skill.diagram; teacherTurns = result.turns.filter(turn => turn.role === 'assistant');
    diagram(lessonDiagram, teacherTurns); $('messages').replaceChildren();
    result.turns.forEach((turn, index) => {
      const item = bubble(turn.role, turn.text);
      if (turn.role === 'assistant') replayButton(item, index);
    });
    const latest = result.turns.at(-1);
    renderChoices(latest?.role === 'assistant' ? latest.options : []);
    $('generatedImage').hidden = true; $('imageStatus').hidden = false; $('imageStatus').textContent = 'Preparing an illustration…';
    $('messageInput').value = ''; show('lesson');
    if (result.turns.at(-1)?.role === 'assistant') playTeacher(result.turns.length - 1, true);
    recent = {id: current, unit_id: unit.id};
    const version = generation;
    api('illustration', {kid_id: child.id, session_id: current}).then(image => {
      if (version !== generation) return;
      $('generatedImage').src = image.url; $('generatedImage').alt = image.alt_text;
      $('generatedImage').hidden = false; $('imageStatus').hidden = true;
    }).catch(() => { if (version === generation) $('imageStatus').textContent = 'Explore the exact diagram below.'; });
  }
  async function sendMessage(value) {
    if (busy || !current) return;
    const text = value.trim(); if (!text) return;
    stopVoice();
    busy = true; $('sendButton').disabled = true; $('messageInput').disabled = true;
    const previousOptions = activeOptions;
    renderChoices([]);
    const mine = bubble('user', text); const waiting = bubble('assistant', 'Your teacher is thinking…', true);
    try {
      const result = await api('reply', {kid_id: child.id, session_id: current, message: text, expected_turn_count: count});
      count = result.turn_count; waiting.querySelector('.bubble-text').textContent = result.text;
      waiting.classList.remove('pending'); replayButton(waiting, count - 1); $('messageInput').value = '';
      teacherTurns.push({role: 'assistant', text: result.text}); diagram(lessonDiagram, teacherTurns);
      renderChoices(result.options);
      playTeacher(count - 1, true);
    } catch (err) { mine.remove(); waiting.remove(); renderChoices(previousOptions); error(err.message); }
    finally { busy = false; $('sendButton').disabled = false; $('messageInput').disabled = false; $('messageInput').focus(); }
  }
  $('messageForm').addEventListener('submit', event => {
    event.preventDefault(); sendMessage($('messageInput').value);
  });
  $('messageInput').addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('messageForm').requestSubmit(); }
  });
  $('backToPath').addEventListener('click', () => { stopVoice(); ++generation; renderPath(); });
  $('learnerChip').addEventListener('click', () => { stopVoice(); ++generation; childPicker(); });
  async function initialize() {
    if (!auth) { show('signin'); return; }
    try {
      const {data: {user: currentUser}} = await auth.auth.getUser();
      if (!currentUser) { show('signin'); return; }
      user = currentUser;
    } catch {}
    try {
      if (!user) { show('signin'); return; }
      const {data: {session}} = await auth.auth.getSession();
      const response = await fetch(`${API}/api/kid/list`, {headers: {Authorization: `Bearer ${session.access_token}`}, signal: AbortSignal.timeout(30000)});
      if (!response.ok) throw new Error('Could not load learner profiles.');
      children = (await response.json()).kids || [];
      if (!children.length) { show('signin'); return; }
      let saved; try { saved = JSON.parse(sessionStorage.getItem(childKey)); } catch {}
      const selected = children.find(k => saved?.userId === user.id && saved?.id === k.id);
      if (selected || children.length === 1) await selectChild(selected || children[0]);
      else childPicker();
    } catch (err) { show('signin'); error(err.message || 'Your learning space could not load.'); }
  }
  initialize();
})();
