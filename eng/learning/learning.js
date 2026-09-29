(() => {
  'use strict';
  const API = 'https://iakids-ai-tutor-he.onrender.com';
  const childKey = 'iakids.eng.child';
  const $ = id => document.getElementById(id);
  const auth = window.supabase?.createClient(
    'https://bxnfzuglfwytiyaguwjj.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4bmZ6dWdsZnd5dGl5YWd1d2pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyMjk0NjUsImV4cCI6MjA4NDgwNTQ2NX0.IcmVvbboKLkJLkE31_udEtvhPl66-kmZAvmPCT_lk5o',
    {auth: {flowType: 'pkce', storageKey: 'iakids-eng-auth', persistSession: true, autoRefreshToken: true, detectSessionInUrl: false}}
  );
  const views = ['loading', 'signin', 'chooseChild', 'path', 'lesson'];
  let user, children = [], child, catalog, subject, unit, recent, current, count = 0, busy = false, generation = 0;
  // The key is public. Keep the exact same anon key as the English dashboard.

  function show(name) { views.forEach(id => { $(id).hidden = id !== name; }); $('error').hidden = true; }
  function error(message) { $('error').textContent = message; $('error').hidden = false; }
  async function api(path, body) {
    const {data: {session}, error: authError} = await auth.auth.getSession();
    if (authError || !session?.access_token) throw new Error('Your session expired. Return to the dashboard to sign in.');
    const response = await fetch(`${API}/api/eng/learning/${path}`, {
      method: body ? 'POST' : 'GET',
      headers: {Authorization: `Bearer ${session.access_token}`, ...(body ? {'Content-Type': 'application/json'} : {})},
      ...(body ? {body: JSON.stringify(body)} : {}), signal: AbortSignal.timeout(30000)
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
    item.textContent = text; $('messages').append(item); $('messages').scrollTop = $('messages').scrollHeight;
    return item;
  }
  function bar(label, denominator, shaded) {
    const row = document.createElement('div'); row.className = 'bar-row';
    const title = document.createElement('b'); title.textContent = label;
    const track = document.createElement('div'); track.className = 'bar';
    for (let i = 0; i < denominator; i++) { const cell = document.createElement('i'); if (i < shaded) cell.className = 'filled'; track.append(cell); }
    row.append(title, track); return row;
  }
  function diagram(kind) {
    const target = $('diagram'); target.replaceChildren();
    let caption = '';
    if (kind === 'equivalent') { target.append(bar('1/3', 3, 1), bar('3/9', 9, 3)); caption = 'The shaded amount stays the same when each third is divided into three equal parts.'; }
    else if (kind === 'compare') { target.append(bar('5/8', 8, 5), bar('3/4', 8, 6)); caption = 'Both bars show the same whole. Count the shaded parts and explain what you notice.'; }
    else if (kind === 'percent' || kind === 'percent-convert') {
      const grid = document.createElement('div'); grid.className = 'hundred'; const count = kind === 'percent' ? 25 : 75;
      for (let i = 0; i < 100; i++) { const cell = document.createElement('i'); if (i < count) cell.className = 'filled'; grid.append(cell); }
      target.append(grid); caption = `${count} of 100 equal squares are shaded: ${count}%.`;
    } else if (kind === 'line') {
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('viewBox', '0 0 470 100'); svg.setAttribute('class', 'number-line'); svg.setAttribute('aria-hidden', 'true');
      svg.innerHTML = '<path d="M25 48H445" stroke="#126c83" stroke-width="3"/>' +
        Array.from({length:13}, (_,i) => `<path d="M${25+i*35} 40v16" stroke="#126c83" stroke-width="2"/>`).join('') +
        '<circle cx="270" cy="48" r="7" fill="#0bb8ad"/><text x="20" y="83">0</text><text x="160" y="83">1</text><text x="300" y="83">2</text><text x="440" y="83">3</text>';
      target.append(svg); caption = 'The point is at 1 3/4 on a line divided into fourths.';
    } else if (kind === 'add') { target.append(bar('2/3', 3, 2), bar('1/3', 3, 1)); caption = 'Equal-sized thirds can be combined: 2/3 + 1/3 = 1.'; }
    else if (kind === 'unlike') { target.append(bar('5/12', 12, 5), bar('1/6', 12, 2)); caption = 'One sixth can be shown as two twelfths before adding.'; }
    else if (kind === 'percent-quantity') { target.append(bar('25%', 4, 1)); caption = 'One quarter of 80 is 20, so 25% of 80 is 20.'; }
    $('diagramCaption').textContent = caption; target.setAttribute('aria-label', caption);
  }
  function openLesson(result) {
    current = result.session_id; count = result.turn_count; ++generation;
    $('gradeLabel').textContent = child.age; $('skillTitle').textContent = result.skill.title;
    diagram(result.skill.diagram); $('messages').replaceChildren();
    result.turns.forEach(turn => bubble(turn.role, turn.text));
    $('generatedImage').hidden = true; $('imageStatus').hidden = false; $('imageStatus').textContent = 'Preparing an illustration…';
    $('messageInput').value = ''; show('lesson');
    recent = {id: current, unit_id: unit.id};
    const version = generation;
    api('illustration', {kid_id: child.id, session_id: current}).then(image => {
      if (version !== generation) return;
      $('generatedImage').src = image.url; $('generatedImage').alt = image.alt_text;
      $('generatedImage').hidden = false; $('imageStatus').hidden = true;
    }).catch(() => { if (version === generation) $('imageStatus').textContent = 'Explore the exact diagram below.'; });
  }
  $('messageForm').addEventListener('submit', async event => {
    event.preventDefault(); if (busy || !current) return;
    const text = $('messageInput').value.trim(); if (!text) return;
    busy = true; $('sendButton').disabled = true; $('messageInput').disabled = true;
    const mine = bubble('user', text); const waiting = bubble('assistant', 'Your teacher is thinking…', true);
    try {
      const result = await api('reply', {kid_id: child.id, session_id: current, message: text, expected_turn_count: count});
      count = result.turn_count; waiting.textContent = result.text; waiting.classList.remove('pending'); $('messageInput').value = '';
    } catch (err) { mine.remove(); waiting.remove(); error(err.message); }
    finally { busy = false; $('sendButton').disabled = false; $('messageInput').disabled = false; $('messageInput').focus(); }
  });
  $('messageInput').addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('messageForm').requestSubmit(); }
  });
  $('backToPath').addEventListener('click', () => { ++generation; renderPath(); });
  $('learnerChip').addEventListener('click', () => { ++generation; childPicker(); });
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
