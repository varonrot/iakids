(() => {
  'use strict';
  let payload;
  try { payload = JSON.parse(sessionStorage.getItem('iakids.eng.lesson-workspace.v1') || 'null'); } catch {}
  if (payload?.mode !== 'topic') return;
  const $ = id => document.getElementById(id);
  const valid = payload.version === 1 && payload.child?.id && payload.draft?.topics?.includes(payload.topic)
    && Date.now() >= payload.at && Date.now() - payload.at < 24 * 60 * 60 * 1000;
  if (!valid) { $('lessonEmpty').hidden = false; return; }
  const API = 'https://iakids-ai-tutor-he.onrender.com';
  const auth = window.supabase?.createClient(
    'https://bxnfzuglfwytiyaguwjj.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4bmZ6dWdsZnd5dGl5YWd1d2pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyMjk0NjUsImV4cCI6MjA4NDgwNTQ2NX0.IcmVvbboKLkJLkE31_udEtvhPl66-kmZAvmPCT_lk5o',
    {auth:{flowType:'pkce', storageKey:'iakids-eng-auth', persistSession:true, autoRefreshToken:true, detectSessionInUrl:false}}
  );
  document.body.classList.add('is-topic-lesson');
  $('lessonApp').hidden = false;
  $('learnerName').textContent = (payload.child.child_name || 'learner').slice(0, 40);
  $('headerSubject').textContent = payload.draft.subject;
  $('headerGrade').textContent = `Grade ${payload.draft.grade}`;
  $('sidebarTitle').textContent = payload.topic;
  $('sidebarContext').textContent = `${payload.draft.subject} · Grade ${payload.draft.grade}`;
  document.querySelectorAll('.step-jump').forEach(button => { button.disabled = true; });
  const stageNames = ['See the idea', 'Try together', 'Your turn'];
  const visual = document.createElement('div');
  visual.className = 'topic-visual';
  visual.innerHTML = '<div class="topic-visual-symbol" aria-hidden="true">✦</div><p class="topic-visual-label"></p>';
  document.querySelector('.visual-stage').append(visual);
  let planId = null, stepIndex = 0, step = null, pendingStep = null, slides = [], slideIndex = 0;
  let busy = false, choice = null, correct = false, complete = false;
  let voiceOn = true, voiceNeedsGesture = false, voiceKey = '', ticket = 0, slideTimer;
  const audio = new Audio();
  const urls = new Map();
  const illustrations = new Map();
  function status(message) { $('voiceStatus').textContent = message; $('voiceStatus').hidden = !message; }
  function stopVoice() { ++ticket; clearTimeout(slideTimer); audio.pause(); audio.removeAttribute('src'); audio.load(); }
  async function request(path, data) {
    if (!auth) throw new Error('Sign in again from Test Prep.');
    const {data:{session}, error} = await auth.auth.getSession();
    if (error || !session?.access_token) throw new Error('Your session expired. Sign in again from Test Prep.');
    const response = await fetch(`${API}/api/eng/topic-lesson/${path}`, {
      method:'POST', headers:{'Content-Type':'application/json', Authorization:`Bearer ${session.access_token}`},
      body:JSON.stringify({kid_id:payload.child.id, ...data})
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'The teacher could not load this lesson. Try again.');
    return result;
  }
  function error(message) {
    $('answerFeedback').textContent = message;
    $('answerFeedback').classList.add('is-error');
    $('answerFeedback').hidden = false;
  }
  function currentKey() { return `${planId}:${stepIndex}:${stepIndex === 0 ? slideIndex : 'step'}`; }
  async function playVoice(replay = false) {
    if (!voiceOn || !planId) return;
    const key = currentKey(), currentTicket = ++ticket;
    if (replay && voiceKey === key && audio.src) {
      audio.currentTime = 0;
      try { await audio.play(); status('Playing your teacher’s explanation.'); }
      catch { status('Tap Replay to hear your teacher.'); }
      return;
    }
    audio.pause(); audio.removeAttribute('src'); audio.load();
    voiceKey = key;
    $('replayButton').hidden = true;
    status('Preparing your teacher’s voice…');
    try {
      const cached = urls.get(key);
      const url = cached && cached.expires > Date.now() ? cached.url :
        (await request('narration', {plan_id:planId, step_index:stepIndex,
          ...(stepIndex === 0 ? {slide_index:slideIndex} : {})})).url;
      if (currentTicket !== ticket || !voiceOn) return;
      urls.set(key, {url, expires:Date.now() + 8 * 60 * 1000});
      audio.src = url;
      $('replayButton').hidden = false;
      await audio.play();
      status('Playing your teacher’s explanation.');
    } catch (e) {
      if (currentTicket !== ticket) return;
      if (e?.name === 'NotAllowedError') {
        voiceOn = false; voiceNeedsGesture = true; voiceKey = '';
        status('Tap the button to allow sound and hear your teacher.');
        render();
        scheduleSlide();
      } else {
        status('Audio is unavailable. Read the explanation to continue.');
        if (stepIndex === 0) scheduleSlide();
      }
    }
  }
  function scheduleSlide() {
    clearTimeout(slideTimer);
    if (stepIndex === 0 && slideIndex < slides.length - 1) slideTimer = setTimeout(nextSlide, 9000);
  }
  function nextSlide() {
    clearTimeout(slideTimer);
    if (stepIndex === 0 && slideIndex < slides.length - 1) {
      slideIndex++;
      render();
      if (!voiceOn) scheduleSlide();
    }
  }
  audio.addEventListener('ended', () => {
    if (stepIndex === 0) nextSlide();
    else status('Finished. Tap Replay to listen again.');
  });
  $('voiceButton').addEventListener('click', () => {
    voiceOn = !voiceOn; voiceNeedsGesture = false;
    if (!voiceOn) { stopVoice(); $('replayButton').hidden = true; status('Reading without audio.'); scheduleSlide(); }
    else { voiceKey = ''; status(''); clearTimeout(slideTimer); playVoice(); }
    render();
  });
  $('replayButton').addEventListener('click', () => playVoice(true));
  function setStep(result) {
    planId = result.plan_id;
    stepIndex = result.step_index;
    step = result.step;
    if (result.slides) slides = result.slides;
    slideIndex = 0; choice = null; correct = false; complete = false;
    stopVoice(); voiceKey = '';
    render();
  }
  function render() {
    if (!step) return;
    const first = stepIndex === 0;
    const slide = first ? slides[slideIndex] : null;
    const interaction = step.interaction;
    document.querySelector('.scene').classList.toggle('is-explaining', first);
    $('sceneEyebrow').textContent = stageNames[stepIndex].toUpperCase();
    $('sceneCounter').textContent = first ? `Slide ${slideIndex + 1} of ${slides.length}` : `Step ${stepIndex + 1} of 3`;
    $('sceneTitle').textContent = first ? slide.title : stageNames[stepIndex];
    $('sceneLead').textContent = first ? 'Listen and watch your teacher explain.' : step.teacher_text;
    visual.querySelector('.topic-visual-label').textContent = first ? slide.visual_label : payload.topic;
    const scene = document.querySelector('.visual-stage');
    const image = $('generatedVisual');
    const imageKey = `${planId}:${slideIndex}`;
    image.hidden = true;
    scene.classList.remove('has-generated-image');
    if (first) {
      const saved = illustrations.get(imageKey);
      if (typeof saved === 'object' && saved.url) {
        image.src = saved.url; image.alt = saved.alt_text || slide.visual_label;
        image.hidden = false; scene.classList.add('has-generated-image');
      } else if (!saved) {
        illustrations.set(imageKey, true);
        request('illustration', {plan_id:planId, slide_index:slideIndex}).then(result => {
          illustrations.set(imageKey, result);
          if (stepIndex === 0 && `${planId}:${slideIndex}` === imageKey) render();
        }).catch(() => illustrations.delete(imageKey));
      }
    }
    image.onerror = () => { image.hidden = true; scene.classList.remove('has-generated-image'); };
    $('lessonExplanation').hidden = !first;
    $('lessonExplanation').textContent = first ? slide.narration : '';
    $('guideMessage').textContent = first ? slide.narration : step.teacher_text;
    $('sceneTakeaway').hidden = true;
    $('questionText').textContent = first ? (slideIndex === slides.length - 1 ? 'Ready to try it together?' : 'Listen to the idea unfold.') : interaction.prompt;
    $('questionLabel').textContent = stageNames[stepIndex].toUpperCase();
    $('hintCopy').textContent = interaction.hint || 'Think back to the example.';
    $('hintCopy').hidden = true;
    $('hintButton').hidden = first || correct;
    $('answerFeedback').hidden = true;
    $('answerFeedback').classList.remove('is-error');
    $('answerOptions').replaceChildren();
    if (!first) (interaction.options || []).forEach((answer, index) => {
      const button = document.createElement('button');
      button.type = 'button'; button.textContent = answer;
      button.setAttribute('aria-pressed', String(choice === index));
      button.addEventListener('click', () => {
        choice = index;
        $('answerOptions').querySelectorAll('button').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
        $('checkButton').disabled = false;
      });
      $('answerOptions').append(button);
    });
    $('checkButton').textContent = first ? 'Try together →' : 'Check answer →';
    $('checkButton').disabled = busy || (first ? slideIndex < slides.length - 1 : choice === null);
    $('voiceButton').classList.toggle('requires-gesture', voiceNeedsGesture);
    $('voiceButton').setAttribute('aria-pressed', String(voiceOn));
    $('voiceButton').innerHTML = voiceNeedsGesture ? '<span aria-hidden="true">▶</span> Tap to hear the lesson' : voiceOn ? '<span aria-hidden="true">◼</span> Voice on' : '<span aria-hidden="true">▶</span> Listen to your teacher';
    $('sidebarProgressLabel').textContent = `${stepIndex + 1} of 3 steps`;
    $('sidebarProgressBar').style.width = `${(stepIndex + 1) / 3 * 100}%`;
    document.querySelectorAll('.step-list li,.footer-dot').forEach((item, index) => {
      item.classList.toggle('is-current', index === stepIndex);
      item.classList.toggle('is-complete', index < stepIndex);
    });
    $('slideProgress').hidden = !first;
    if (first) $('slideProgress').replaceChildren(...slides.map((_, index) => {
      const dot = document.createElement('span');
      dot.className = index === slideIndex ? 'is-current' : index < slideIndex ? 'is-complete' : '';
      return dot;
    }));
    if (voiceOn && voiceKey !== currentKey()) playVoice();
  }
  $('hintButton').addEventListener('click', () => {
    $('hintCopy').hidden = false;
    $('hintButton').hidden = true;
  });
  $('checkButton').addEventListener('click', async () => {
    if (!step || busy) return;
    if (correct) {
      if (complete) { location.assign('../../#test-prep'); return; }
      setStep(pendingStep); pendingStep = null; return;
    }
    if (stepIndex === 0 && slideIndex < slides.length - 1) return;
    if (stepIndex > 0 && choice === null) return;
    busy = true; $('checkButton').disabled = true;
    try {
      const result = await request('answer', {plan_id:planId, step_index:stepIndex,
        option_index:stepIndex === 0 ? null : choice, hint_used:!$('hintCopy').hidden});
      if (!result.correct) {
        error('Let’s try that again.');
        $('hintCopy').textContent = result.hint || step.interaction.hint || 'Look at the example again.';
        $('hintCopy').hidden = false; choice = null;
        $('answerOptions').querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed','false'));
        return;
      }
      correct = true; complete = result.complete;
      pendingStep = result.complete ? null : result;
      $('answerFeedback').textContent = stepIndex === 0 ? 'Now let’s practice together.' : 'Yes! You’re ready for the next step.';
      $('answerFeedback').hidden = false;
      $('checkButton').textContent = complete ? 'Finish lesson →' : 'Continue →';
      $('answerOptions').querySelectorAll('button').forEach(button => { button.disabled = true; });
    } catch (e) { error(e.message); }
    finally { busy = false; $('checkButton').disabled = !correct && stepIndex > 0 && choice === null; }
  });
  async function start() {
    $('sceneTitle').textContent = `Preparing ${payload.topic}`;
    $('sceneLead').textContent = 'Your teacher is building a short lesson for this topic.';
    $('guideMessage').textContent = 'This can take a moment the first time. The lesson will be saved for next time.';
    $('checkButton').disabled = true;
    status('Preparing your lesson…');
    try {
      const result = await request('start', {topic:payload.topic});
      if (result.complete) {
        $('sceneTitle').textContent = 'Lesson complete!';
        $('guideMessage').textContent = 'Your progress is saved. Choose another topic from Test Prep.';
        $('checkButton').disabled = false;
        $('checkButton').textContent = 'Choose another topic →';
        $('checkButton').onclick = () => location.assign('../../#test-prep');
        status('');
        return;
      }
      status(''); setStep(result);
    } catch (e) {
      status(''); error(e.message);
      $('checkButton').textContent = 'Try loading again →';
      $('checkButton').disabled = false;
      $('checkButton').onclick = () => location.reload();
    }
  }
  start();
})();
