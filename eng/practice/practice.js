(() => {
  'use strict';
  const API = 'https://iakids-ai-tutor-he.onrender.com';
  const childKey = 'iakids.eng.child';
  const $ = id => document.getElementById(id);
  const views = ['loading', 'signin', 'chooseChild', 'choosePack', 'quiz', 'complete'];
  const auth = window.supabase?.createClient(
    'https://bxnfzuglfwytiyaguwjj.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4bmZ6dWdsZnd5dGl5YWd1d2pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyMjk0NjUsImV4cCI6MjA4NDgwNTQ2NX0.IcmVvbboKLkJLkE31_udEtvhPl66-kmZAvmPCT_lk5o',
    {auth: {flowType: 'pkce', storageKey: 'iakids-eng-auth', persistSession: true, autoRefreshToken: true, detectSessionInUrl: false}}
  );
  let user, children = [], child, catalog = [], pack, index = 0, selected = null, checked = false, score = 0, busy = false, sessionId;

  function view(name) {
    views.forEach(id => { $(id).hidden = id !== name; });
    $('error').hidden = true;
  }
  function fail(error) {
    $('error').textContent = error?.message || 'Something went wrong. Please try again.';
    $('error').hidden = false;
  }
  async function api(path, body) {
    const {data: {session}, error} = await auth.auth.getSession();
    if (error || !session?.access_token) throw new Error('Your session expired. Return to the dashboard to sign in.');
    const response = await fetch(API + path, {
      method: body ? 'POST' : 'GET',
      headers: {Authorization: `Bearer ${session.access_token}`, ...(body ? {'Content-Type': 'application/json'} : {})},
      ...(body ? {body: JSON.stringify(body)} : {}),
      signal: AbortSignal.timeout(30000)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Practice could not load. Please try again.');
    return result;
  }
  function remember(kid) {
    try { sessionStorage.setItem(childKey, JSON.stringify({userId: user.id, id: kid.id})); } catch {}
  }
  function chooseChild() {
    child = null;
    $('learnerChip').hidden = true;
    const list = $('childChoices'); list.replaceChildren();
    for (const kid of children) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = `${kid.child_name} · Grade ${kid.age}`;
      button.addEventListener('click', () => selectChild(kid));
      list.append(button);
    }
    view('chooseChild');
  }
  async function selectChild(kid) {
    child = kid; remember(kid);
    $('learnerChip').textContent = `${kid.child_name} · Grade ${kid.age}`;
    $('learnerChip').hidden = false;
    view('loading');
    try {
      const result = await api('/api/eng/practice/start', {kid_id: kid.id});
      catalog = result.packs;
      showPacks();
    } catch (error) { chooseChild(); fail(error); }
  }
  function showPacks() {
    view('choosePack');
    $('packTitle').textContent = `${child.child_name}’s practice`;
    $('packDescription').textContent = `Math · Grade ${child.age}. Choose a short set to begin.`;
    const list = $('packChoices'); list.replaceChildren();
    for (const item of catalog) {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'pack';
      const icon = document.createElement('span'); icon.className = 'pack-icon'; icon.textContent = '✎'; icon.setAttribute('aria-hidden', 'true');
      const title = document.createElement('strong'); title.textContent = item.title;
      const detail = document.createElement('small'); detail.textContent = 'Math · 3 questions →';
      button.append(icon, title, detail);
      button.addEventListener('click', () => startPack(item.id));
      list.append(button);
    }
    if (!catalog.length) {
      const message = document.createElement('p');
      message.textContent = 'Practice for this grade is coming soon.';
      list.append(message);
    }
  }
  async function startPack(id) {
    if (busy) return;
    busy = true; view('loading');
    try {
      const result = await api('/api/eng/practice/start', {kid_id: child.id, pack_id: id});
      pack = result.pack; index = 0; score = 0; sessionId = crypto.randomUUID();
      renderQuestion();
    } catch (error) { showPacks(); fail(error); }
    finally { busy = false; }
  }
  function renderQuestion() {
    selected = null; checked = false;
    const item = pack.questions[index];
    $('quizSubject').textContent = `${pack.subject.toUpperCase()} · ${pack.title.toUpperCase()}`;
    $('progressLabel').textContent = `Question ${index + 1} of ${pack.questions.length}`;
    $('progressFill').style.width = `${index / pack.questions.length * 100}%`;
    $('question').textContent = item.prompt;
    $('feedback').hidden = true;
    $('feedback').classList.remove('is-wrong');
    const list = $('answerChoices'); list.replaceChildren();
    item.options.forEach((answer, option) => {
      const button = document.createElement('button');
      button.type = 'button'; button.textContent = answer;
      button.setAttribute('aria-pressed', 'false');
      button.addEventListener('click', () => {
        if (checked || busy) return;
        selected = option;
        list.querySelectorAll('button').forEach((node, n) => node.setAttribute('aria-pressed', String(n === option)));
        $('nextButton').disabled = false;
      });
      list.append(button);
    });
    $('nextButton').textContent = 'Check answer →';
    $('nextButton').disabled = true;
    view('quiz');
  }
  async function next() {
    if (busy) return;
    if (checked) {
      if (++index < pack.questions.length) renderQuestion();
      else finish();
      return;
    }
    if (selected === null) return;
    busy = true; $('nextButton').disabled = true;
    try {
      const result = await api('/api/eng/practice/answer', {
        kid_id: child.id, pack_id: pack.id, session_id: sessionId,
        question_key: pack.questions[index].key, option_index: selected
      });
      checked = true; if (result.correct) score++;
      $('answerChoices').querySelectorAll('button').forEach((button, option) => {
        button.disabled = true;
        if (option === result.correct_index) button.classList.add('is-correct');
        if (option === selected && !result.correct) button.classList.add('is-wrong');
      });
      $('feedback').textContent = `${result.correct ? 'That’s right! ' : 'Good try. '}${result.explanation}`;
      $('feedback').classList.toggle('is-wrong', !result.correct);
      $('feedback').hidden = false;
      $('progressFill').style.width = `${(index + 1) / pack.questions.length * 100}%`;
      $('nextButton').textContent = index + 1 === pack.questions.length ? 'See results →' : 'Next question →';
    } catch (error) { fail(error); }
    finally { busy = false; $('nextButton').disabled = false; }
  }
  function finish() {
    $('completedName').textContent = child.child_name;
    $('resultSummary').textContent = `You answered ${score} of ${pack.questions.length} questions correctly in ${pack.title}. You can practice again any time.`;
    view('complete');
  }
  $('changeChild').addEventListener('click', chooseChild);
  $('leaveQuiz').addEventListener('click', showPacks);
  $('nextButton').addEventListener('click', next);
  $('againButton').addEventListener('click', () => startPack(pack.id));
  $('anotherButton').addEventListener('click', showPacks);
  async function initialize() {
    if (!auth) { view('signin'); return; }
    try {
      const {data: {user: currentUser}} = await auth.auth.getUser();
      if (!currentUser) { view('signin'); return; }
      user = currentUser;
      children = (await api('/api/kid/list')).kids || [];
      if (!children.length) { view('signin'); return; }
      let saved;
      try { saved = JSON.parse(sessionStorage.getItem(childKey)); } catch {}
      const last = children.find(kid => saved?.userId === user.id && saved?.id === kid.id);
      if (last || children.length === 1) await selectChild(last || children[0]);
      else chooseChild();
    } catch (error) { view('signin'); fail(error); }
  }
  initialize();
})();
