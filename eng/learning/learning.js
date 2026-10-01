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
  const views = ['loading', 'signin', 'chooseChild', 'path', 'lesson', 'curriculumLesson'];
  let user, children = [], child, catalog = [], library = [], plans = [], subject, unit, recent, current, count = 0, busy = false, generation = 0, activeOptions = [];
  let plannerStage = 'subjects';
  let activePlan = null, introVoice = null, planAudioSerial = 0;
  const curriculumProgress = new Map();
  let curriculumProgressSerial = 0;
  let curriculumOpenSerial = 0;
  const planAudioUrls = new Map();
  let voiceEnabled = true, audioSerial = 0, playingKey = '';
  let lessonDiagram, teacherTurns = [];
  const audioUrls = new Map();
  try { voiceEnabled = localStorage.getItem(voiceKey) !== 'off'; } catch {}
  // The key is public. Keep the exact same anon key as the English dashboard.

  function show(name) { if (name !== 'curriculumLesson') stopCurriculumVoice(); views.forEach(id => { $(id).hidden = id !== name; }); $('error').hidden = true; }
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
      row.append(open); if (!plan.ready_at) row.append(edit); target.append(row);
    }
  }
  async function deletePlan(plan) {
    if (plan.ready_at || busy || !child || !plans.some(item => item.id === plan.id)) return;
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
    $('plannerForm').hidden = false;
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
    $('plannerForm').hidden = false;
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
    if (activePlan) {
      const ready = plannerButton(activePlan.ready_at ? 'Continue learning' : 'Approve plan & start learning', '▶', () => approvePlan());
      ready.classList.add('planner-ready'); actions.push(ready);
    }
    if (activePlan?.ready_at) return [...actions, plannerButton('Create another plan', '＋', startAnotherPlan)];
    return [...actions, ...suggestions.map(label => plannerButton(label, '✦', /^(begin|start|let.s start)/i.test(label) ? () => approvePlan() : () => replyToPlan(label))),
      plannerButton('Create another plan', '＋', startAnotherPlan)];
  }
  function showPlan(plan, autoVoice = false, editMode = false, animateLatest = false) {
    const content = plan.content; if (!content?.units) return;
    editMode = editMode && !plan.ready_at;
    $('plannerForm').hidden = !!plan.ready_at;
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
      for (const [lessonIndex, lesson] of part.lessons.entries()) {
        const row = document.createElement('li'), name = document.createElement('strong'), goal = document.createElement('small');
        name.textContent = `Lesson ${++lessonNumber}: ${cleanTitle(lesson.title, 'Lesson')}`; goal.textContent = lesson.goal; row.append(name, goal);
        const open = document.createElement('button'); open.type = 'button'; open.className = 'plan-lesson-open';
        open.dataset.unit = index; open.dataset.lesson = lessonIndex;
        open.textContent = 'Open lesson →';
        open.onclick = () => approvePlan({unit_index:index,lesson_index:lessonIndex}); row.append(open);
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
      ? 'Your approved plan is locked. Continue learning or review a completed lesson.'
      : 'Review your plan before approving. Once approved, it cannot be edited. You can always create a separate plan.';
    $('plannerMessages').replaceChildren();
    const dialogue = plan.dialogue?.length ? plan.dialogue : [{role: 'assistant',
      text: 'Your plan is ready. Tell me what you already know, ask for more practice questions, or tell me what you would like to change.'}];
    dialogue.forEach((turn, index) => plannerBubble(turn.role === 'user' ? 'learner' : 'guide', turn.text,
      turn.role === 'assistant' && plan.dialogue?.length ? index : -1, null,
      animateLatest && index === dialogue.length - 1));
    // Saved approval messages are history, not a fresh instruction to begin again.
    if(plan.ready_at && !animateLatest) {
      const messages=$('plannerMessages'),history=document.createElement('details');
      history.className='planner-history';
      const label=document.createElement('summary');label.textContent='Previous planning conversation';
      history.append(label,...messages.childNodes);messages.append(history);
      const status=document.createElement('p');status.id='plannerResumeStatus';
      status.className='planner-resume-status';status.setAttribute('role','status');
      status.textContent='Your learning plan is saved. Checking your progress…';messages.append(status);
    }
    plannerOptions(planActions(dialogue.at(-1)?.options || []));
    $('plannerInput').placeholder = editMode
      ? 'Tell the guide what to change in this plan…'
      : 'I already know the basics. Can we spend more time on…?';
    if (autoVoice && (!plan.ready_at || animateLatest) && dialogue.at(-1)?.role === 'assistant') playPlanVoice(dialogue.length - 1, true);
    refreshCurriculumProgress(plan);
  }
  function curriculumLessons() {
    return (activePlan?.content.units || []).flatMap((part,unit_index) =>
      part.lessons.map((lesson,lesson_index) => ({...lesson,unit_index,lesson_index})));
  }
  function progressFor(plan) {
    const saved = curriculumProgress.get(plan.id);
    return saved?.revision === plan.revision ? saved.lessons : [];
  }
  function updateCurriculumNavigation() {
    if(!teachingLesson || !activePlan)return;
    const lessons=curriculumLessons(), position=lessons.findIndex(item =>
      item.unit_index===teachingLesson.unit_index && item.lesson_index===teachingLesson.lesson_index);
    const select=$('curriculumLessonSelect'); select.replaceChildren();
    activePlan.content.units.forEach((unit,unit_index)=>{
      const group=document.createElement('optgroup');group.label=`Unit ${unit_index+1}: ${unit.title}`;
      lessons.forEach((item,index)=>{
        if(item.unit_index!==unit_index)return;
        const option=document.createElement('option'),status=progressFor(activePlan).find(p=>p.unit_index===item.unit_index&&p.lesson_index===item.lesson_index);
        option.value=String(index);option.textContent=`${status?.completed?'✓ ':''}Lesson ${index+1}: ${item.title}`;
        option.selected=index===position;group.append(option);
      });select.append(group);
    });
    $('curriculumPreviousLesson').disabled=busy||position<=0;
    $('curriculumNextLesson').disabled=busy||position<0||position===lessons.length-1;
    select.disabled=busy;
    const completed=progressFor(activePlan).filter(item=>item.completed).length;
    $('curriculumCourseProgress').textContent=`Lesson ${position+1} of ${lessons.length} · ${completed} completed`;
    $('curriculumContinueLesson').hidden=!teachingLesson.completed;
    $('curriculumContinueLesson').textContent=position===lessons.length-1?'Back to learning plan ✓':'Continue to next lesson →';
  }
  async function refreshCurriculumProgress(plan) {
    const token=++curriculumProgressSerial,learnerId=child.id;
    try {
      const result=await api('plan/progress',{kid_id:learnerId,plan_id:plan.id,expected_revision:plan.revision});
      if(token!==curriculumProgressSerial||child.id!==learnerId||activePlan?.id!==plan.id||activePlan.revision!==plan.revision)return;
      curriculumProgress.set(plan.id,{revision:plan.revision,lessons:result.lessons});
      document.querySelectorAll('.plan-lesson-open').forEach(button=>{
        const item=result.lessons.find(p=>p.unit_index===Number(button.dataset.unit)&&p.lesson_index===Number(button.dataset.lesson));
        button.textContent=item?.completed?'✓ Review lesson':item?.available?'Continue lesson →':'Open lesson →';
      });
      const resumeStatus=$('plannerResumeStatus');
      if(resumeStatus) {
        const completed=result.lessons.filter(item=>item.completed).length;
        const next=result.lessons.find(item=>!item.completed);
        resumeStatus.textContent=next
          ? `${completed} of ${result.lessons.length} lessons completed. ${next.available ? 'Continue' : 'Up next'}: Lesson ${next.number} — ${next.title}. Choose Continue learning when you’re ready.`
          : `You’ve completed all ${result.lessons.length} lessons in this plan. Choose any lesson to review.`;
      }
      updateCurriculumNavigation();
    } catch(err) { if(!document || token!==curriculumProgressSerial || child.id!==learnerId || activePlan?.id!==plan.id)return;const status=$('plannerResumeStatus');if(status)status.textContent='Your learning plan is saved. Choose Continue learning or open a lesson.'; /* Lessons remain accessible if the status request fails. */ }
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
    if (busy || !activePlan || activePlan.ready_at) return;
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
  async function approvePlan(position = null) {
    if (busy || !activePlan) return;
    if (!activePlan.ready_at && !window.confirm('Approve this learning plan? Once approved, it cannot be edited. Your lessons and progress will stay linked to this plan. You can always create a separate plan.')) return;
    const planId = activePlan.id, learnerId = child.id, serial = generation;
    const openSerial=++curriculumOpenSerial;
    busy = true; $('plannerSend').disabled = true; plannerOptions([]); stopPlanVoice();
    const inLesson=!$('curriculumLesson').hidden;
    if(inLesson) {stopCurriculumVoice();++teachingVisualSerial;$('curriculumVoiceStatus').textContent='Preparing your lesson';$('curriculumVoiceStatus').classList.add('lesson-preparing');$('curriculumLesson').setAttribute('aria-busy','true');updateCurriculumNavigation();}
    const pending = inLesson ? null : plannerPending('Preparing your lesson');
    try {
      if (!activePlan.ready_at) {
        const result = await api('plan/ready', {kid_id: learnerId, plan_id: planId,
          expected_revision: activePlan.revision});
        if (activePlan?.id !== planId || generation !== serial) return;
        activePlan = result.plan;
        plans = [result.plan, ...plans.filter(item => item.id !== planId)].slice(0, 12);
        renderSavedPlans();
      }
      const result = await api('plan/lesson', {kid_id: learnerId, plan_id: planId,
        expected_revision: activePlan.revision,...(position || {})}, 180000);
      if (generation !== serial || activePlan?.id !== planId || openSerial!==curriculumOpenSerial) return;
      openCurriculumLesson(result.lesson);
      refreshCurriculumProgress(activePlan);
    } catch (err) {
      if (generation === serial) {
        pending?.remove(); if(!inLesson)showPlan(activePlan); error(err.message);
      }
    } finally { busy = false; $('plannerSend').disabled = false;$('curriculumVoiceStatus').classList.remove('lesson-preparing');$('curriculumLesson').setAttribute('aria-busy','false');updateCurriculumNavigation(); }
  }
  let teachingLesson = null, teachingAudioSerial = 0, teachingSection = -1, teachingVisualSerial = 0;
  let teachingSeen = new Set();
  const teachingAudioUrls = new Map(), teachingVisuals = new Map(), teachingPending = new Map();
  let teachingTypingTimer = null;
  function lessonWaiting(waiting) {
    $('curriculumLoading').hidden = !waiting;
    $('curriculumLesson').classList.toggle('waiting-for-voice', waiting);
    $('curriculumNarration').setAttribute('aria-busy', String(waiting));
  }
  function revealTeachingText() {
    document.querySelectorAll('#curriculumNarration [data-spoken]').forEach(node => { node.textContent=node.dataset.spoken; });
  }
  function prepareTeachingTyping(index) {
    const content=teachingLesson.content, box=$('curriculumNarration');
    box.replaceChildren();
    let blocks=[];
    if(index===-1) blocks=[content.unit_intro, 'In this lesson: '+content.objectives.join('; ')];
    else if(index===content.sections.length) blocks=[content.checkpoint.question, ...content.checkpoint.options.map((option,i)=>`Option ${i+1}: ${option}`)];
    else {
      const section=content.sections[index];
      blocks=[(section.paragraph_index===0 || section.paragraph_index==null ? section.title+'. ' : '')+section.explanation, section.worked_example];
      if(index===content.sections.length-1)blocks.push(content.summary);
    }
    blocks.filter(Boolean).forEach(text=>{
      const node=document.createElement('p');node.dataset.spoken=text;box.append(node);
    });
    box.scrollTop=0;
  }
  function syncTeachingTyping(audio) {
    if(!Number.isFinite(audio.duration) || audio.duration<=0)return;
    const nodes=[...document.querySelectorAll('#curriculumNarration [data-spoken]')];
    const total=nodes.reduce((sum,node)=>sum+node.dataset.spoken.length,0);
    // The TTS service returns no word timestamps. Follow the real media clock,
    // distributing the text over its duration; pauses and buffering cannot run ahead.
    let remaining=Math.floor(total*Math.min(1,audio.currentTime/audio.duration));
    nodes.forEach(node=>{
      const text=node.dataset.spoken, count=Math.min(text.length,Math.max(0,remaining));
      node.textContent=text.slice(0,count);remaining-=text.length;
    });
  }
  function stopCurriculumVoice() {
    ++teachingAudioSerial;
    clearInterval(teachingTypingTimer); teachingTypingTimer=null;
    lessonWaiting(false);
    const audio = $('curriculumAudio');
    if (audio) { audio.pause(); audio.onended = null; audio.ontimeupdate=null; audio.onplaying=null; audio.onwaiting=null; audio.removeAttribute('src'); }
  }
  function openCurriculumLesson(lesson) {
    stopVoice(); stopPlanVoice(); stopCurriculumVoice(); teachingLesson = lesson; teachingSection = -1;
    teachingSeen = new Set();
    $('curriculumLesson').classList.toggle('paragraph-mode',!!lesson.content.paragraph_version);
    $('curriculumTitle').textContent = lesson.content.title;
    lesson.unit_index ??= 0; lesson.lesson_index ??= 0;
    const number=curriculumLessons().findIndex(item=>item.unit_index===lesson.unit_index&&item.lesson_index===lesson.lesson_index)+1;
    $('curriculumMeta').textContent = `${activePlan.subject} · Grade ${child.age} · Unit ${lesson.unit_index+1} · Lesson ${number}`;
    updateCurriculumNavigation();
    $('curriculumFeedback').textContent = lesson.completed ? 'You have completed this lesson. Review it whenever you like.' : '';
    $('curriculumQuestion').textContent = lesson.content.checkpoint.question;
    $('curriculumAnswers').replaceChildren(...lesson.content.checkpoint.options.map((text, optionIndex) => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'choice';
      button.textContent = text;
      button.onclick = async () => {
        if (busy) return;
        stopCurriculumVoice(); busy = true;
        const lessonId = teachingLesson.id, learnerId = child.id;
        const buttons = [...$('curriculumAnswers').children]; buttons.forEach(b => b.disabled = true);
        try {
          const result = await api('plan/lesson/answer', {kid_id: learnerId, lesson_id: lessonId, option_index: optionIndex, expected_content_version: teachingLesson.content.paragraph_version || 0, expected_content_token: teachingLesson.content_token || ""});
          if (teachingLesson?.id !== lessonId || $('curriculumLesson').hidden) return;
          $('curriculumFeedback').textContent = result.correct
            ? `Well done — lesson complete. ${result.feedback}` : `Try again. ${result.feedback}`;
          if (result.correct) {
            teachingLesson.completed = true;
            const entries=progressFor(activePlan);
            const item=entries.find(p=>p.unit_index===teachingLesson.unit_index&&p.lesson_index===teachingLesson.lesson_index);
            if(item)item.completed=true;
            refreshCurriculumProgress(activePlan);updateCurriculumNavigation();
          }
        } catch (err) { error(err.message); }
        finally { busy = false; buttons.forEach(b => b.disabled = false);updateCurriculumNavigation(); }
      };
      return button;
    }));
    show('curriculumLesson');
    $('curriculumVoiceToggle').textContent = voiceEnabled ? '🔊 Voice on' : '🔇 Voice off';
    $('curriculumVoiceToggle').setAttribute('aria-pressed', String(voiceEnabled));
    // Warm the first visual while the unit introduction is playing.
    warmTeachingParagraphs(0);
    selectTeachingSlide(-1, voiceEnabled);
  }
  function loadTeachingMedia(kind, index) {
    const lessonId = teachingLesson.id, learnerId = child.id, key = `${lessonId}:${teachingLesson.content_token || "legacy"}:${index}`;
    const cache = kind === 'audio' ? teachingAudioUrls : teachingVisuals;
    const cached = cache.get(key);
    if (cached && cached.expires > Date.now()) return Promise.resolve(cached.result);
    const pendingKey = `${kind}:${key}`;
    if (teachingPending.has(pendingKey)) return teachingPending.get(pendingKey);
    const pending = api(`plan/lesson/${kind}`, {kid_id: learnerId, lesson_id: lessonId, section_index: index, expected_content_version: teachingLesson.content.paragraph_version || 0, expected_content_token: teachingLesson.content_token || ""}, 120000)
      .then(result => { cache.set(key, {result, expires: Date.now() + 480000}); return result; })
      .finally(() => teachingPending.delete(pendingKey));
    teachingPending.set(pendingKey, pending); return pending;
  }
  function warmTeachingParagraphs(start) {
    // At most two upcoming paragraphs (four independent media requests) are prepared ahead.
    const total = teachingLesson.content.sections.length;
    for (let index = start; index < Math.min(start + 2, total); index++) {
      loadTeachingMedia('visual', index).catch(() => {});
      if (voiceEnabled) loadTeachingMedia('audio', index).catch(() => {});
    }
  }
  function svgNode(tag, attributes = {}, text = '') {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attributes).forEach(([name, value]) => node.setAttribute(name, String(value)));
    if (text) node.textContent = text;
    return node;
  }
  function drawTeachingVisual(spec) {
    const svg = svgNode('svg', {viewBox:'0 0 800 450', role:'img', 'aria-label':spec.caption});
    svg.append(svgNode('rect', {x:0,y:0,width:800,height:450,rx:24,fill:'#f3fbf5'}));
    const text = (x,y,value,size=24,color='#153b54') => svgNode('text', {x,y,'text-anchor':'middle','font-family':'Inter, Arial, sans-serif','font-size':size,fill:color}, String(value));
    if (spec.kind === 'grid') {
      const grid=spec.grid, size=Math.min(54,320/grid.rows,580/grid.columns);
      const x=(800-size*grid.columns)/2, y=(380-size*grid.rows)/2;
      for (let i=0;i<grid.rows*grid.columns;i++) svg.append(svgNode('rect', {x:x+(i%grid.columns)*size,y:y+Math.floor(i/grid.columns)*size,width:size,height:size,fill:i<grid.shaded?'#0cb2ae':'#dceee8',stroke:'#267478','stroke-width':2}));
      svg.append(text(400,420,`${grid.shaded} out of ${grid.rows*grid.columns}${grid.label ? ` · ${grid.label}` : ''}`,23));
    } else if (spec.kind === 'number_line') {
      const line=spec.number_line, plot=value=>80+(value-line.start)/(line.end-line.start)*640;
      svg.append(svgNode('line',{x1:80,y1:275,x2:720,y2:275,stroke:'#153b54','stroke-width':5}));
      for(let i=0;i<=line.divisions;i++) {
        const value=line.start+(line.end-line.start)*i/line.divisions, x=plot(value);
        svg.append(svgNode('line',{x1:x,y1:265,x2:x,y2:285,stroke:'#153b54','stroke-width':2}));
        if(line.divisions<=10 || i%2===0 || i===line.divisions) svg.append(text(x,320,Number(value.toFixed(6)),18));
      }
      line.points.forEach((point,i)=> {
        const x=plot(point.value), y=85+(i%4)*38;
        svg.append(svgNode('line',{x1:x,y1:y+10,x2:x,y2:258,stroke:'#09a6a6','stroke-width':2,'stroke-dasharray':'6 5'}),svgNode('circle',{cx:x,cy:275,r:12,fill:'#0cb2ae',stroke:'#fff','stroke-width':3}),text(x,y,point.label||point.value,23));
      });
    } else if(spec.kind === 'place_value') {
      const number=spec.place_value.number, digits=Array.from(number.replace('-','')), point=digits.indexOf('.');
      const units=point<0?digits.length:point, width=Math.min(100,700/digits.length), start=(800-width*digits.length)/2;
      const whole=['Units','Tens','Hundreds','Thousands','Ten thousands'], fractions=['Tenths','Hundredths','Thousandths','Ten-thousandths'];
      digits.forEach((digit,i)=> {
        const x=start+i*width, label=digit==='.'?'Decimal point':i<units?whole[units-i-1]:fractions[i-units-1];
        const focus=spec.place_value.highlight||'all', focused=focus!=='all'&&label?.toLowerCase()===focus;
        svg.append(svgNode('rect',{x:x+2,y:165,width:width-4,height:140,rx:12,fill:focused?'#0ba9a8':digit==='.'?'#fff':'#e8f2ed',stroke:focused?'#087d87':'#81c5ba','stroke-width':focused?4:2}),text(x+width/2,125,label,Math.min(18,width/6),focused?'#007b87':'#537488'),text(x+width/2,252,digit,48,focused?'#fff':'#153b54'));
      });
      svg.append(text(400,380,number,36));
    } else if(spec.kind === 'fraction_bars') {
      spec.fraction_bars.forEach((bar,row)=> {
        const y=60+row*(300/spec.fraction_bars.length), width=520/bar.parts;
        svg.append(text(100,y+35,bar.label||`${bar.filled}/${bar.parts}`,22));
        for(let i=0;i<bar.parts;i++) svg.append(svgNode('rect',{x:220+i*width,y,width,height:58,fill:i<bar.filled?'#0cb2ae':'#dceee8',stroke:'#267478','stroke-width':2}));
      });
    }
    return svg;
  }
  async function displayTeachingVisual(index) {
    const serial=++teachingVisualSerial, lessonId=teachingLesson.id;
    const art=$('curriculumArt'); art.replaceChildren(); art.setAttribute('aria-busy','true');
    const waiting=document.createElement('div'); waiting.className='teaching-art-pending';
    const spinner=document.createElement('span'); spinner.className='spinner'; spinner.setAttribute('aria-hidden','true');
    const message=document.createElement('p'); message.textContent='Preparing this illustration…';
    waiting.append(spinner,message); art.append(waiting); $('curriculumCaption').textContent='';
    try {
      const result=await loadTeachingMedia('visual',index);
      if(serial!==teachingVisualSerial || teachingLesson?.id!==lessonId || $('curriculumLesson').hidden || teachingSection!==index) return;
      if(result.visual.kind==='illustration') {
        const picture=document.createElement('img'); picture.src=result.url; picture.alt=result.visual.caption;
        picture.onerror=()=> { if(serial===teachingVisualSerial) visualError('This picture could not load. Retry illustration.'); };
        art.replaceChildren(picture);
      } else art.replaceChildren(drawTeachingVisual(result.visual));
      $('curriculumCaption').textContent=result.visual.caption;
    } catch(err) {
      if(serial===teachingVisualSerial && teachingLesson?.id===lessonId && teachingSection===index && !$('curriculumLesson').hidden) visualError(err.message);
    } finally { if(serial===teachingVisualSerial) art.setAttribute('aria-busy','false'); }
    function visualError(message) {
      art.replaceChildren(); const label=document.createElement('p'); label.textContent=message;
      const retry=document.createElement('button'); retry.type='button';retry.className='primary';retry.textContent='Retry illustration';
      retry.onclick=()=> { teachingVisuals.delete(`${lessonId}:${index}`);displayTeachingVisual(index); };
      const wrapper=document.createElement('div'); wrapper.className='teaching-art-pending'; wrapper.append(label,retry);art.append(wrapper);
    }
  }
  function selectTeachingSlide(index, narrate = false) {
    if(!teachingLesson) return;
    stopCurriculumVoice(); ++teachingVisualSerial; teachingSection=index;
    const content=teachingLesson.content, total=content.sections.length, intro=index===-1, check=index===total;
    if(!intro && !check) teachingSeen.add(index);
    $('curriculumCheck').hidden=!check; $('curriculumArt').hidden=check;
    $('curriculumCaption').hidden=intro||check;
    $('curriculumArt').setAttribute('aria-busy','false');
    $('curriculumCounter').textContent=intro?'Before we begin':check?'Your turn':content.paragraph_version ? `Part ${content.sections[index].source_index+1} · Paragraph ${content.sections[index].paragraph_index+1} of ${content.sections[index].paragraph_count}` : `Slide ${index+1} of ${total}`;
    $('curriculumEyebrow').textContent=intro?'WHAT WE WILL LEARN':check?'CHECK YOUR UNDERSTANDING':'SEE THE IDEA';
    $('curriculumSceneTitle').textContent=intro?'Let’s see where we’re going':check?'Try what you’ve learned':content.sections[index].title;
    $('curriculumNarration').replaceChildren();
    const paragraph=document.createElement('p');
    if(intro) {
      $('curriculumArt').replaceChildren();const goals=document.createElement('div');goals.className='teaching-goals';
      content.objectives.forEach((goal,i)=> {
        const card=document.createElement('div'),icon=document.createElement('span'),words=document.createElement('strong');
        icon.textContent=['◎','▥','✦','✓'][i];words.textContent=goal;card.append(icon,words);goals.append(card);
      }); $('curriculumArt').append(goals);paragraph.textContent=content.unit_intro;
    } else if(check) { paragraph.textContent=`${content.summary}\n\nTake your time and choose an answer.`;
    } else { paragraph.textContent=content.sections[index].explanation; }
    if(paragraph.textContent) $('curriculumNarration').append(paragraph);
    if(!intro && !check && content.sections[index].worked_example) {
      const example=document.createElement('div');example.className='teaching-example';
      const label=document.createElement('strong');label.textContent='Worked example';
      const words=document.createElement('p');words.textContent=content.sections[index].worked_example;example.append(label,words);$('curriculumNarration').append(example);
    }
    if(index===total-1) {
      const summary=document.createElement('p');summary.className='teaching-summary';summary.textContent=content.summary;$('curriculumNarration').append(summary);
    }
    $('curriculumNarration').scrollTop=0;
    [$('curriculumOverview'),$('curriculumExplain'),$('curriculumCheckJump')].forEach((button,i)=> {
      const current=(i===0&&intro)||(i===1&&!intro&&!check)||(i===2&&check);
      button.classList.toggle('is-current',current);if(current)button.setAttribute('aria-current','step');else button.removeAttribute('aria-current');
    });
    $('curriculumCheckJump').disabled=!teachingLesson.completed&&teachingSeen.size<total;
    $('curriculumProgressLabel').textContent=`${teachingSeen.size} of ${total} ${content.paragraph_version ? 'paragraphs' : 'explanation slides'} visited`;
    $('curriculumProgress').replaceChildren(...content.sections.map((section,i)=> {
      const button=document.createElement('button');button.type='button';button.setAttribute('aria-label',`${content.paragraph_version ? 'Paragraph' : 'Slide'} ${i+1}: ${section.title}`);
      button.className=i===index?'is-current':teachingSeen.has(i)?'is-seen':'';button.onclick=()=>selectTeachingSlide(i,voiceEnabled);return button;
    }));
    $('curriculumPrevious').disabled=intro; $('curriculumNext').hidden=check;
    $('curriculumNext').textContent=intro?'Start explanation →':index===total-1?'Check understanding →':'Next →';
    $('curriculumVoiceStatus').textContent=voiceEnabled?'Preparing your teacher’s voice…':'Voice off. Use Next to move through the explanation.';
    $('curriculumGuideNote').textContent=check?'Choose an answer when you’re ready.':'The explanation moves forward automatically with the voice. You can pause or replay.';
    if(!intro&&!check)displayTeachingVisual(index);
    if(narrate)playCurriculumSection(index);
  }
  async function playCurriculumSection(index) {
    if(!teachingLesson || $('curriculumLesson').hidden) return;
    stopCurriculumVoice(); const serial=teachingAudioSerial, lessonId=teachingLesson.id;
    prepareTeachingTyping(index);lessonWaiting(true);
    const audio=$('curriculumAudio'); $('curriculumVoiceStatus').textContent='Preparing your teacher’s voice…';
    try {
      $('curriculumVoiceStatus').textContent='Preparing this paragraph’s picture and voice…';
      const [result]=await Promise.all([loadTeachingMedia('audio',index),
        index>=0 && index<teachingLesson.content.sections.length ? loadTeachingMedia('visual',index) : Promise.resolve(null)]);
      if(serial!==teachingAudioSerial || teachingLesson?.id!==lessonId || $('curriculumLesson').hidden) return;
      audio.src=result.url;
      audio.ontimeupdate=()=>{if(serial===teachingAudioSerial)syncTeachingTyping(audio);};
      audio.onwaiting=()=>{if(serial===teachingAudioSerial)lessonWaiting(true);};
      audio.onplaying=()=>{if(serial===teachingAudioSerial)lessonWaiting(false);};
      audio.onended=()=> {
        if(serial!==teachingAudioSerial) return;
        revealTeachingText();
        clearInterval(teachingTypingTimer);teachingTypingTimer=null;
        if(index<teachingLesson.content.sections.length)selectTeachingSlide(index+1,voiceEnabled);
        else $('curriculumVoiceStatus').textContent='Choose an answer when you’re ready.';
      };
      await audio.play();
      if(serial!==teachingAudioSerial) return;
      lessonWaiting(false);
      teachingTypingTimer=setInterval(()=>{if(serial===teachingAudioSerial)syncTeachingTyping(audio);},60);
      $('curriculumVoiceStatus').textContent='Playing your teacher’s explanation.';
      const next=index+1;
      // Preparing the next segment while this one plays avoids a generation gap between slides.
      warmTeachingParagraphs(Math.max(0,next));
      if(next===teachingLesson.content.sections.length)loadTeachingMedia('audio',next).catch(()=>{});
    } catch(err) {
      if(serial!==teachingAudioSerial)return;
      lessonWaiting(false);revealTeachingText();
      $('curriculumVoiceStatus').textContent=err.name==='NotAllowedError'
        ? 'Your browser paused automatic audio. Press Replay to hear your teacher.' : err.message;
    }
  }
  $('curriculumBack').onclick=()=> { ++curriculumOpenSerial;stopCurriculumVoice();++teachingVisualSerial;show('path');showPlan(activePlan); };
  function moveCurriculumLesson(offset) {
    const lessons=curriculumLessons(),index=lessons.findIndex(item=>item.unit_index===teachingLesson.unit_index&&item.lesson_index===teachingLesson.lesson_index);
    const target=lessons[index+offset];
    if(target)approvePlan({unit_index:target.unit_index,lesson_index:target.lesson_index});
  }
  $('curriculumPreviousLesson').onclick=()=>moveCurriculumLesson(-1);
  $('curriculumNextLesson').onclick=()=>moveCurriculumLesson(1);
  $('curriculumLessonSelect').onchange=()=>{
    const target=curriculumLessons()[Number($('curriculumLessonSelect').value)];
    if(target)approvePlan({unit_index:target.unit_index,lesson_index:target.lesson_index});
  };
  $('curriculumContinueLesson').onclick=()=>{
    const lessons=curriculumLessons(),last=lessons.at(-1);
    if(teachingLesson.unit_index===last.unit_index&&teachingLesson.lesson_index===last.lesson_index)$('curriculumBack').click();
    else moveCurriculumLesson(1);
  };
  $('curriculumListen').onclick=()=>playCurriculumSection(teachingSection);
  $('curriculumPause').onclick=()=> { stopCurriculumVoice();revealTeachingText();$('curriculumVoiceStatus').textContent='Voice paused. Press Replay to hear this part again.'; };
  $('curriculumVoiceToggle').onclick=()=> {
    voiceEnabled=!voiceEnabled;try{localStorage.setItem(voiceKey,voiceEnabled?'on':'off');}catch{}
    $('curriculumVoiceToggle').textContent=voiceEnabled?'🔊 Voice on':'🔇 Voice off';
    $('curriculumVoiceToggle').setAttribute('aria-pressed',String(voiceEnabled));
    if(voiceEnabled)playCurriculumSection(teachingSection);else {stopCurriculumVoice();revealTeachingText();$('curriculumVoiceStatus').textContent='Voice off. Use Next to continue.';}
  };
  $('curriculumOverview').onclick=()=>selectTeachingSlide(-1,voiceEnabled);
  $('curriculumExplain').onclick=()=>selectTeachingSlide(0,voiceEnabled);
  $('curriculumCheckJump').onclick=()=>selectTeachingSlide(teachingLesson.content.sections.length,voiceEnabled);
  $('curriculumPrevious').onclick=()=>selectTeachingSlide(teachingSection-1,voiceEnabled);
  $('curriculumNext').onclick=()=>selectTeachingSlide(teachingSection+1,voiceEnabled);
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
