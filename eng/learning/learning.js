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
  let user, children = [], child, catalog = [], library = [], plans = [], subject, unit, recent, current, count = 0, busy = false, generation = 0, activeOptions = [];
  let plannerStage = 'subjects';
  let activePlan = null, introVoice = null, planAudioSerial = 0;
  const planAudioUrls = new Map();
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
    child = kid; ++generation; stopPlanVoice(); if (recognition) recognition.stop();
    try { sessionStorage.setItem(childKey, JSON.stringify({userId: user.id, id: kid.id})); } catch {}
    $('learnerChip').textContent = `${kid.child_name} · Grade ${kid.age} ▾`;
    $('learnerChip').hidden = false;
    show('loading');
    try {
      const result = await api(`library?kid_id=${encodeURIComponent(kid.id)}`);
      library = result.subjects; plans = result.plans;
      subject = null; unit = null; plannerStage = 'subjects'; renderPath();
    } catch (err) { childPicker(); error(err.message); }
  }
  function choice(iconText, titleText, detailText, action) {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'choice';
    const icon = document.createElement('span'); icon.className = 'choice-icon'; icon.textContent = iconText;
    const title = document.createElement('strong'); title.textContent = titleText;
    const detail = document.createElement('small'); detail.textContent = detailText;
    button.append(icon, title, detail); button.addEventListener('click', action); return button;
  }
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  function plannerBubble(role, message, index = -1, intro = null, animate = false) {
    const bubble = document.createElement('div'); bubble.className = `planner-bubble ${role}`;
    const words = document.createElement('span');
    if (animate && role === 'guide' && !reducedMotion.matches) {
      // Keep the full message available to assistive technology while it appears visually.
      bubble.setAttribute('aria-label', message); words.setAttribute('aria-hidden', 'true');
      const characters = Array.from(message);
      const step = Math.max(1, Math.ceil(characters.length / 75));
      let position = 0;
      const typeNext = () => {
        if (!bubble.isConnected) return;
        position = Math.min(position + step, characters.length);
        words.textContent = characters.slice(0, position).join('');
        $('plannerMessages').scrollTop = $('plannerMessages').scrollHeight;
        if (position < characters.length) setTimeout(typeNext, 28);
      };
      requestAnimationFrame(typeNext);
    } else words.textContent = message;
    bubble.append(words);
    if (role === 'guide' && (index >= 0 || intro)) {
      const listen = document.createElement('button'); listen.type = 'button'; listen.className = 'plan-listen';
      listen.textContent = '▶ Listen';
      listen.addEventListener('click', () => intro ? playPlanIntro(intro) : playPlanVoice(index)); bubble.append(listen);
    }
    $('plannerMessages').append(bubble);
    $('plannerMessages').scrollTop = $('plannerMessages').scrollHeight;
    return bubble;
  }
  function plannerPending(message) {
    const bubble = document.createElement('div'); bubble.className = 'planner-bubble guide planner-pending';
    bubble.setAttribute('role', 'status'); bubble.setAttribute('aria-label', `${message}…`);
    const words = document.createElement('span'); words.textContent = message; words.setAttribute('aria-hidden', 'true');
    const dots = document.createElement('span'); dots.className = 'planner-dots'; dots.textContent = '...'; dots.setAttribute('aria-hidden', 'true');
    bubble.append(words, dots); $('plannerMessages').append(bubble);
    $('plannerMessages').scrollTop = $('plannerMessages').scrollHeight;
    return bubble;
  }
  function stopPlanVoice() {
    ++planAudioSerial; $('plannerAudio').pause(); $('plannerAudio').removeAttribute('src');
    $('plannerAudio').load(); $('plannerVoiceStatus').hidden = true;
  }
  function updatePlannerVoice() {
    $('plannerVoiceToggle').textContent = voiceEnabled ? '🔊 Voice on' : '🔇 Voice off';
    $('plannerVoiceToggle').setAttribute('aria-pressed', String(voiceEnabled));
  }
  async function playPlanVoice(index, automatic = false) {
    if (!activePlan || (automatic && !voiceEnabled)) return;
    if (!voiceEnabled) {
      voiceEnabled = true; try { localStorage.setItem(voiceKey, 'on'); } catch {}
      updatePlannerVoice(); updateVoiceToggle();
    }
    const token = ++planAudioSerial, planId = activePlan.id;
    $('plannerAudio').pause(); $('plannerVoiceStatus').textContent = 'Preparing the guide’s voice…';
    $('plannerVoiceStatus').hidden = false;
    try {
      const key = `${planId}:${index}`;
      let cached = planAudioUrls.get(key);
      if (!cached || cached.expiresAt < Date.now()) {
        const result = await api('plan/audio', {kid_id: child.id, plan_id: planId, turn_index: index}, 120000);
        cached = {url: result.url, expiresAt: Date.now() + 9 * 60 * 1000}; planAudioUrls.set(key, cached);
      }
      if (token !== planAudioSerial || activePlan?.id !== planId || !voiceEnabled) return;
      $('plannerAudio').src = cached.url; await $('plannerAudio').play();
      if (token === planAudioSerial) $('plannerVoiceStatus').hidden = true;
    } catch (err) {
      if (token !== planAudioSerial) return;
      $('plannerVoiceStatus').textContent = err.name === 'NotAllowedError'
        ? 'Tap ▶ Listen to hear the guide.' : 'Voice is unavailable. You can continue reading.';
    }
  }
  async function playPlanIntro(context, automatic = false) {
    if (automatic && !voiceEnabled) return;
    if (!voiceEnabled) {
      voiceEnabled = true; try { localStorage.setItem(voiceKey, 'on'); } catch {}
      updatePlannerVoice(); updateVoiceToggle();
    }
    const token = ++planAudioSerial, kidId = child.id;
    $('plannerAudio').pause(); $('plannerVoiceStatus').textContent = 'Preparing the guide’s voice…';
    $('plannerVoiceStatus').hidden = false;
    try {
      const key = `${kidId}:${context.stage}:${context.subject || ''}`;
      let cached = planAudioUrls.get(key);
      if (!cached || cached.expiresAt < Date.now()) {
        const result = await api('plan/intro-audio', {kid_id: kidId, ...context}, 120000);
        cached = {url: result.url, expiresAt: Date.now() + 9 * 60 * 1000}; planAudioUrls.set(key, cached);
      }
      if (token !== planAudioSerial || child.id !== kidId || activePlan || !voiceEnabled) return;
      $('plannerAudio').src = cached.url; await $('plannerAudio').play();
      if (token === planAudioSerial) $('plannerVoiceStatus').hidden = true;
    } catch (err) {
      if (token !== planAudioSerial) return;
      $('plannerVoiceStatus').textContent = err.name === 'NotAllowedError'
        ? 'Tap ▶ Listen to hear the guide.' : 'Voice is unavailable. You can continue reading.';
    }
  }
  $('plannerVoiceToggle').addEventListener('click', () => {
    voiceEnabled = !voiceEnabled; try { localStorage.setItem(voiceKey, voiceEnabled ? 'on' : 'off'); } catch {}
    updatePlannerVoice(); updateVoiceToggle();
    if (!voiceEnabled) stopPlanVoice();
    else if (activePlan) {
      const turns = activePlan.dialogue || [];
      const index = turns.findLastIndex(turn => turn.role === 'assistant');
      if (index >= 0) playPlanVoice(index);
    } else if (introVoice) playPlanIntro(introVoice);
  });
  $('plannerAudio').addEventListener('error', () => {
    $('plannerVoiceStatus').textContent = 'Voice could not load. Tap ▶ Listen to try again.';
    $('plannerVoiceStatus').hidden = false;
  });
  updatePlannerVoice();
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  if (!Recognition) $('plannerMic').hidden = true;
  else $('plannerMic').addEventListener('click', () => {
    if (recognition) { recognition.stop(); return; }
    stopPlanVoice();
    const instance = new Recognition(), original = $('plannerInput').value.trim();
    recognition = instance; instance.lang = 'en-US'; instance.interimResults = true;
    $('plannerMic').classList.add('listening'); $('plannerMic').setAttribute('aria-pressed', 'true');
    $('plannerMic').title = 'Listening… tap to stop';
    instance.onresult = event => {
      const transcript = Array.from(event.results, result => result[0].transcript).join(' ');
      $('plannerInput').value = `${original}${original ? ' ' : ''}${transcript}`.slice(0, 500);
    };
    instance.onerror = event => {
      if (event.error !== 'aborted') error(event.error === 'not-allowed'
        ? 'Allow microphone access to speak, or type your message.'
        : 'Could not hear you. You can type your message.');
    };
    instance.onend = () => {
      recognition = null; $('plannerMic').classList.remove('listening');
      $('plannerMic').setAttribute('aria-pressed', 'false'); $('plannerMic').title = 'Speak your message';
      $('plannerInput').focus();
    };
    try { instance.start(); } catch { instance.onend(); error('Microphone is unavailable. You can type your message.'); }
  });
  function plannerButton(label, icon, action) {
    const button = document.createElement('button'); button.type = 'button';
    const mark = document.createElement('span'); mark.className = 'planner-icon'; mark.textContent = icon;
    const words = document.createElement('span'); words.textContent = label;
    button.append(mark, words); button.addEventListener('click', action); return button;
  }
  function plannerOptions(items) { $('plannerChoices').replaceChildren(...items); }
  function renderSavedPlans() {
    const target = $('savedPlans'); target.replaceChildren();
    if (!plans.length) return;
    const heading = document.createElement('h2'); heading.textContent = 'Your saved plans'; target.append(heading);
    for (const plan of plans) {
      const row = document.createElement('div'); row.className = 'saved-plan-row';
      const open = document.createElement('button'); open.type = 'button'; open.className = 'saved-plan-open';
      open.textContent = `${plan.subject} · ${plan.topic}${plan.ready_at ? ' · Ready ✓' : ''} →`;
      open.addEventListener('click', () => showPlan(plan, true));
      const edit = document.createElement('button'); edit.type = 'button'; edit.className = 'saved-plan-edit';
      edit.textContent = 'Edit'; edit.setAttribute('aria-label', `Edit ${plan.subject} · ${plan.topic} plan`);
      edit.addEventListener('click', () => {
        showPlan(plan, true, true); $('plannerInput').focus();
      });
      row.append(open, edit); target.append(row);
    }
  }
  async function deletePlan(plan) {
    if (busy || !child || !plans.some(item => item.id === plan.id)) return;
    if (!window.confirm(`Delete your ${plan.subject} · ${plan.topic} plan? This also removes its conversation and cannot be undone.`)) return;
    busy = true;
    try {
      await api('plan/delete', {kid_id: child.id, plan_id: plan.id, expected_revision: plan.revision});
      plans = plans.filter(item => item.id !== plan.id);
      if (activePlan?.id === plan.id) renderPath();
      else renderSavedPlans();
    } catch (err) {
      error(err.message);
    } finally { busy = false; }
  }
  function renderPath() {
    stopPlanVoice(); if (recognition) recognition.stop(); activePlan = null;
    introVoice = {stage: 'welcome'};
    show('path'); $('plannerGrade').textContent = `${child.child_name} · Grade ${child.age}`;
    $('plannerMessages').replaceChildren(); $('plannerTree').replaceChildren();
    $('plannerSubtitle').textContent = 'Choose a subject to begin. Your plan will appear here.';
    renderSavedPlans(); plannerStage = 'subjects'; subject = null;
    $('plannerInput').placeholder = 'For example: I want to understand dividing fractions';
    plannerBubble('guide', `Hi ${child.child_name}! What would you like to learn today? Choose a Grade ${child.age} subject, or write your own idea below.`, -1, introVoice, true);
    plannerOptions(library.map(item => plannerButton(item.title, item.icon, () => chooseSubject(item))));
    playPlanIntro(introVoice, true);
  }
  function chooseSubject(item, fresh = false) {
    if (busy) return;
    stopPlanVoice(); introVoice = {stage: 'subject', subject: item.title};
    subject = item; plannerStage = 'topics';
    if (!fresh) plannerBubble('learner', item.title);
    plannerBubble('guide', `Great. Which ${item.title} topic would you like to explore? You can also describe one in your own words.`, -1, introVoice, true);
    const buttons = item.topics.map(topic => {
      const saved = plans.find(plan => plan.subject === item.title && plan.topic.toLowerCase() === topic.toLowerCase());
      return plannerButton(saved ? `${topic} · Open saved plan` : topic, saved ? '↗' : '✦',
        saved ? () => showPlan(saved, true) : () => createPlan(item.title, topic, ''));
    });
    buttons.push(plannerButton('← Change subject', '↩', renderPath)); plannerOptions(buttons);
    $('plannerInput').placeholder = `Or write a ${item.title} topic…`;
    playPlanIntro(introVoice, true);
  }
  function startAnotherPlan() {
    if (busy || !activePlan) return;
    const previous = activePlan;
    const currentSubject = library.find(item => item.title.toLowerCase() === previous.subject.toLowerCase());
    if (!currentSubject) { renderPath(); return; }
    stopPlanVoice(); if (recognition) recognition.stop(); activePlan = null;
    $('plannerMessages').replaceChildren(); $('plannerTree').replaceChildren();
    $('plannerSubtitle').textContent = `Your ${previous.topic} plan is saved. Choose another ${currentSubject.title} topic, or change subject.`;
    renderSavedPlans();
    chooseSubject(currentSubject, true);
  }
  function planActions(options = []) {
    const suggestions = options.length ? options : ['I know some of this already', 'Add more practice questions', 'Change the plan'];
    const actions = [];
    if (activePlan && !activePlan.ready_at) {
      const ready = plannerButton('I’m ready — approve this plan', '✓', approvePlan);
      ready.classList.add('planner-ready'); actions.push(ready);
    }
    return [...actions, ...suggestions.map(label => plannerButton(label, '✦', () => replyToPlan(label))),
      plannerButton('Create another plan', '＋', startAnotherPlan)];
  }
  function showPlan(plan, autoVoice = false, editMode = false, animateLatest = false) {
    const content = plan.content; if (!content?.units) return;
    stopPlanVoice(); if (recognition) recognition.stop(); activePlan = plan; introVoice = null; plannerStage = 'plan'; subject = null;
    const tree = $('plannerTree'); tree.replaceChildren();
    const title = document.createElement('h2'); title.textContent = content.title; tree.append(title);
    const lessonCount = content.units.reduce((total, part) => total + part.lessons.length, 0);
    const meta = document.createElement('p'); meta.textContent = `${content.subject} · ${content.topic} · Grade ${child.age} · ${content.units.length} units · ${lessonCount} lessons`; tree.append(meta);
    if (editMode) {
      const tools = document.createElement('div'); tools.className = 'planner-edit-tools';
      const hint = document.createElement('p'); hint.textContent = 'Tell the guide what you would like to change in this plan.';
      const remove = document.createElement('button'); remove.type = 'button';
      remove.textContent = 'Delete this plan';
      remove.addEventListener('click', () => deletePlan(activePlan));
      tools.append(hint, remove); tree.append(tools);
    }
    const cleanTitle = (title, kind) => title.replace(new RegExp(`^(?:\\d+[.)]\\s*)?(?:${kind}\\s+\\d+\\s*[:.)\\-]\\s*)+`, 'i'), '').trim();
    let lessonNumber = 0;
    content.units.forEach((part, index) => {
      const details = document.createElement('details'); details.open = index === 0;
      const summary = document.createElement('summary'); summary.textContent = `Unit ${index + 1}: ${cleanTitle(part.title, 'Unit')}`;
      if (part.overview) {
        const overview = document.createElement('p'); overview.className = 'unit-overview';
        overview.style.cssText = 'margin:0;padding:0 15px 12px;color:#537488;font-size:13px;line-height:1.5';
        overview.textContent = `In this unit: ${part.overview}`; details.append(summary, overview);
      } else details.append(summary);
      const list = document.createElement('ol');
      for (const lesson of part.lessons) {
        const row = document.createElement('li'), name = document.createElement('strong'), goal = document.createElement('small');
        name.textContent = `Lesson ${++lessonNumber}: ${cleanTitle(lesson.title, 'Lesson')}`; goal.textContent = lesson.goal; row.append(name, goal);
        if (lesson.practice_questions?.length) {
          const questions = document.createElement('ul'); questions.className = 'plan-questions';
          lesson.practice_questions.forEach(question => {
            const item = document.createElement('li'); item.textContent = question; questions.append(item);
          });
          row.append(questions);
        }
        list.append(row);
      }
      list.style.listStyle = 'none'; list.style.paddingLeft = '18px';
      details.append(list); tree.append(details);
    });
    $('plannerSubtitle').textContent = plan.ready_at
      ? 'Plan approved ✓ · Your lessons will be built from this plan next. You can still ask for changes.'
      : 'Your plan is saved. Open each part to see its lessons, or ask the guide to adjust it.';
    $('plannerMessages').replaceChildren();
    const dialogue = plan.dialogue?.length ? plan.dialogue : [{role: 'assistant',
      text: 'Your plan is ready. Tell me what you already know, ask for more practice questions, or tell me what you would like to change.'}];
    dialogue.forEach((turn, index) => plannerBubble(turn.role === 'user' ? 'learner' : 'guide', turn.text,
      turn.role === 'assistant' && plan.dialogue?.length ? index : -1, null,
      animateLatest && index === dialogue.length - 1));
    plannerOptions(planActions(dialogue.at(-1)?.options || []));
    $('plannerInput').placeholder = editMode
      ? 'Tell the guide what to change in this plan…'
      : 'I already know the basics. Can we spend more time on…?';
    if (autoVoice && dialogue.at(-1)?.role === 'assistant') playPlanVoice(dialogue.length - 1, true);
  }
  async function createPlan(chosenSubject, topic, requestText) {
    if (busy) return;
    busy = true; $('plannerSend').disabled = true;
    plannerBubble('learner', topic || requestText);
    plannerOptions([]); const pending = plannerPending('I’m building your learning plan');
    try {
      const result = await api('plan', {kid_id: child.id, subject: chosenSubject, topic, request_text: requestText}, 90000);
      plans = [result.plan, ...plans.filter(item => item.id !== result.plan.id)].slice(0, 12);
      renderSavedPlans(); showPlan(result.plan, true, false, true); $('plannerInput').value = '';
    } catch (err) {
      pending.textContent = 'The plan could not be created. Please try again.';
      error(err.message); plannerOptions([plannerButton('Try again', '↻', () => createPlan(chosenSubject, topic, requestText)),
        plannerButton('Change subject', '↩', renderPath)]);
    } finally { busy = false; $('plannerSend').disabled = false; }
  }
  async function replyToPlan(message) {
    if (busy || !activePlan) return;
    const planId = activePlan.id, expectedRevision = activePlan.revision;
    busy = true; $('plannerSend').disabled = true; plannerOptions([]);
    plannerBubble('learner', message);
    const pending = plannerPending('Thinking about your plan');
    try {
      const result = await api('plan/reply', {kid_id: child.id, plan_id: planId,
        message, expected_revision: expectedRevision}, 90000);
      if (activePlan?.id !== planId) return;
      plans = [result.plan, ...plans.filter(item => item.id !== planId)].slice(0, 12);
      const editing = !!document.querySelector('#plannerTree .planner-edit-tools');
      renderSavedPlans(); showPlan(result.plan, true, editing, true); $('plannerInput').value = '';
    } catch (err) {
      pending.remove(); $('plannerMessages').lastElementChild?.remove();
      error(err.message); plannerOptions(planActions(activePlan?.dialogue?.at(-1)?.options || []));
    } finally { busy = false; $('plannerSend').disabled = false; }
  }
  async function approvePlan() {
    if (busy || !activePlan || activePlan.ready_at) return;
    const planId = activePlan.id, expectedRevision = activePlan.revision;
    busy = true; $('plannerSend').disabled = true; plannerOptions([]);
    try {
      const result = await api('plan/ready', {kid_id: child.id, plan_id: planId,
        expected_revision: expectedRevision});
      if (activePlan?.id !== planId) return;
      plans = [result.plan, ...plans.filter(item => item.id !== planId)].slice(0, 12);
      const editing = !!document.querySelector('#plannerTree .planner-edit-tools');
      renderSavedPlans(); showPlan(result.plan, true, editing);
    } catch (err) {
      error(err.message); plannerOptions(planActions(activePlan?.dialogue?.at(-1)?.options || []));
    } finally { busy = false; $('plannerSend').disabled = false; }
  }
  $('plannerForm').addEventListener('submit', event => {
    event.preventDefault(); const value = $('plannerInput').value.trim();
    if (!value) return;
    if (plannerStage === 'plan') replyToPlan(value);
    else createPlan(subject?.title || '', '', value);
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
    voiceEnabled = !voiceEnabled; updateVoiceToggle(); updatePlannerVoice();
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
    activeOptions = Array.isArray(options) ? [...options] : [];
    const fractionChoices = activeOptions.map(option => /^\s*(\d+)\s*\/\s*(\d+)\s*$/.exec(option));
    if (fractionChoices.length === 2 && fractionChoices.every(Boolean) &&
        Number(fractionChoices[0][2]) > 0 && Number(fractionChoices[1][2]) > 0 &&
        Number(fractionChoices[0][1]) * Number(fractionChoices[1][2]) ===
        Number(fractionChoices[1][1]) * Number(fractionChoices[0][2])) {
      activeOptions.push('They are equal');
    }
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
      // A turn can first discuss the previous answer, then ask a new question.
      // The final pair belongs to the question the child is answering now.
      return unique.length >= 2 ? unique.slice(-2) : null;
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
  $('learnerChip').addEventListener('click', () => { stopVoice(); stopPlanVoice(); if (recognition) recognition.stop(); ++generation; childPicker(); });
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
