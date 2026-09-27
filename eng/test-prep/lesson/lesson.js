(() => {
  'use strict';
  const handoffKey = 'iakids.eng.lesson-workspace.v1';
  let payload;
  try { payload = JSON.parse(sessionStorage.getItem(handoffKey) || 'null'); } catch {}
  if (!payload && new URLSearchParams(location.search).get('demo') === '1') {
    payload = {
      version:1, at:Date.now(), child:{id:'preview', child_name:'Alona'},
      draft:{subject:'Math', grade:5, topics:['Dividing fractions']},
      lesson:{headline:'Understanding Dividing Fractions', opening:'Look at the pizza. How many half-pizza portions fit into three quarters?'}
    };
    document.body.classList.add('is-preview');
  }
  if (!payload || payload.version !== 1 || !payload.child?.id || !payload.lesson?.headline || Date.now() - payload.at > 24 * 60 * 60 * 1000 || Date.now() < payload.at) {
    document.getElementById('lessonEmpty').hidden = false;
    return;
  }
  const $ = id => document.getElementById(id);
  const child = payload.child;
  const aiLesson = payload.lesson;
  const name = (child.child_name || 'learner').trim().slice(0, 40);
  const API = 'https://iakids-ai-tutor-he.onrender.com';
  const auth = !document.body.classList.contains('is-preview') && window.supabase?.createClient(
    'https://bxnfzuglfwytiyaguwjj.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4bmZ6dWdsZnd5dGl5YWd1d2pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyMjk0NjUsImV4cCI6MjA4NDgwNTQ2NX0.IcmVvbboKLkJLkE31_udEtvhPl66-kmZAvmPCT_lk5o',
    {auth:{flowType:'pkce', storageKey:'iakids-eng-auth', persistSession:true, autoRefreshToken:true, detectSessionInUrl:false}}
  );
  const stages = [
    {
      title:'See the idea', eyebrow:'SEE THE IDEA', equation:'¾ ÷ ½', lead:aiLesson.headline,
      message:aiLesson.opening || 'Look at the pizza. Two quarters make one half.',
      takeaway:'Two quarters make one half. The last quarter is half of another half.',
      question:'How many halves fit into three quarters?', options:['1','1½','2'], hint:'Two quarters make one half. The third quarter is half of another half.',
      visual:{type:'pizza'}
    },
    {
      title:'Try together', eyebrow:'TRY TOGETHER', equation:'⅔ ÷ ⅓', lead:'Count equal pieces',
      message:'A third is one of three equal parts. Let’s count the thirds in two thirds.',
      takeaway:'Two thirds contains two one-third pieces.',
      question:'How many one-third pieces fit into two thirds?', options:['1','2','3'], hint:'Count the shaded thirds, one at a time.',
      visual:{type:'bar', parts:3, filled:2, label:'2 of 3 equal parts are shaded'}
    },
    {
      title:'Your turn', eyebrow:'YOUR TURN', equation:'½ ÷ ¼', lead:'One last check',
      message:'You’ve seen how to count equal pieces. Try this one yourself.',
      takeaway:'A half contains two quarters.',
      question:'How many quarters fit into one half?', options:['1','2','4'], hint:'A half is the same size as two quarters.',
      visual:{type:'bar', parts:4, filled:2, label:'Half the bar is shaded. The whole bar has four equal parts.'}
    }
  ];
  let stageIndex = 0, choice = null, correct = false, hintUsed = false;
  let planId = null, activeStep = null, pendingStep = null, complete = false, busy = false;
  let resumeIndex = 0, resumeStep = null, reviewMode = false, revealIndex = 0;
  const ideaBeats = [
    {message:'Three of the four equal pizza pieces are shaded. How many half-pizza portions fit?', button:'Show one half →'},
    {message:'Look at the top two quarters. Together they make one whole half.', button:'Look at the last quarter →'},
    {message:'One quarter remains. It is half of another half. What does that make altogether?', button:'Show the answer →'},
    {message:'One whole half plus half of another half makes one and a half halves.', button:'Try together →'}
  ];
  $('learnerName').textContent = name;
  $('headerSubject').textContent = payload.draft?.subject || 'Math';
  $('headerGrade').textContent = `Grade ${payload.draft?.grade || 5}`;
  $('sidebarTitle').textContent = payload.draft?.topics?.[0] || 'Dividing fractions';
  $('sidebarContext').textContent = `${payload.draft?.subject || 'Math'} · Grade ${payload.draft?.grade || 5}`;
  $('lessonApp').hidden = false;

  function renderModel(stage) {
    const scene = document.querySelector('.visual-stage');
    const model = $('fractionModel');
    const image = $('generatedVisual');
    const imageUrl = activeStep?.visual?.url;
    const guidedIdea = stageIndex === 0 && (activeStep?.interaction?.type === 'continue' || document.body.classList.contains('is-preview'));
    image.hidden = !imageUrl || (guidedIdea && revealIndex < 3);
    scene.classList.toggle('has-generated-image', !!imageUrl && !image.hidden);
    scene.dataset.reveal = stageIndex === 0 ? String(revealIndex) : '0';
    if (imageUrl) { image.src = imageUrl; image.alt = activeStep.visual.alt_text || 'Lesson illustration'; }
    image.onerror = () => { image.hidden = true; scene.classList.remove('has-generated-image'); };
    const isModel = stage.visual.type === 'bar';
    scene.classList.toggle('is-model', isModel);
    model.hidden = !isModel;
    scene.setAttribute('aria-label', !image.hidden ? image.alt : isModel ? stage.visual.label : 'A pizza divided into four equal quarters, with three quarters shaded.');
    if (!isModel) return;
    model.replaceChildren();
    const bar = document.createElement('div');
    bar.className = 'model-bar';
    for (let i = 0; i < stage.visual.parts; i++) {
      const cell = document.createElement('span');
      cell.className = 'model-cell' + (i < stage.visual.filled ? ' filled' : '');
      bar.append(cell);
    }
    const label = document.createElement('span');
    label.className = 'model-caption';
    label.textContent = stage.visual.label;
    model.append(bar, label);
  }

  function render() {
    const stage = stages[stageIndex];
    const interaction = activeStep?.interaction;
    const isContinue = interaction?.type === 'continue' || (stageIndex === 0 && document.body.classList.contains('is-preview'));
    const guidedIdea = stageIndex === 0 && isContinue;
    const beat = ideaBeats[revealIndex];
    const optionsList = interaction?.options || stage.options;
    $('sceneEyebrow').textContent = stage.eyebrow;
    $('sceneCounter').textContent = `Step ${stageIndex + 1} of ${stages.length}`;
    $('sceneTitle').textContent = stage.lead;
    $('sceneLead').textContent = stageIndex === 0 ? (guidedIdea ? 'Look at the three shaded quarters. We will build the answer together.' : 'A short visual idea, then one question.') : (activeStep?.teacher_text || stage.message);
    $('sceneTakeaway').textContent = stage.takeaway;
    $('sceneTakeaway').hidden = stageIndex === 0 ? guidedIdea && revealIndex < 3 : !correct && !reviewMode;
    const showIdeaAnswer = stageIndex === 0 && guidedIdea && revealIndex === 3;
    document.querySelector('.equation').replaceChildren(document.createTextNode(stage.equation + ' '), Object.assign(document.createElement('span'), {textContent:showIdeaAnswer ? '= 1½' : '= ?'}));
    $('guideMessage').textContent = guidedIdea ? `${name}, ${beat.message}` : stageIndex === 0 ? `${name}, ${activeStep?.teacher_text || stage.message}` : (activeStep?.teacher_text || stage.message);
    $('questionText').textContent = reviewMode ? 'Take another look at this step.' : guidedIdea ? (revealIndex === 3 ? 'Ready to try together?' : 'Follow the shaded pieces.') : isContinue ? 'Ready to try together?' : (interaction?.prompt || stage.question);
    $('questionLabel').textContent = reviewMode ? 'REVIEW' : stage.eyebrow;
    $('hintCopy').textContent = stage.hint;
    $('hintCopy').hidden = reviewMode || !hintUsed;
    $('hintButton').hidden = reviewMode || correct;
    $('answerFeedback').hidden = !reviewMode && !correct;
    $('answerFeedback').classList.remove('is-error');
    $('answerFeedback').textContent = reviewMode ? `Your progress is saved at Step ${resumeIndex + 1}.` : correct ? 'Exactly. Nice work!' : '';
    const options = $('answerOptions');
    options.replaceChildren();
    optionsList.forEach((value, optionIndex) => {
      if (isContinue || reviewMode) return;
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = value;
      button.setAttribute('aria-pressed', String(choice === optionIndex));
      button.disabled = correct;
      button.addEventListener('click', () => {
        choice = optionIndex;
        options.querySelectorAll('button').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
        $('checkButton').disabled = false;
      });
      options.append(button);
    });
    $('checkButton').disabled = busy || (!reviewMode && !guidedIdea && !isContinue && choice === null && !correct);
    $('checkButton').textContent = guidedIdea && revealIndex < 3 ? beat.button : reviewMode ? `Back to Step ${resumeIndex + 1} →` : correct ? complete ? 'Finish lesson →' : 'Continue →' : guidedIdea ? beat.button : isContinue ? 'Continue →' : 'Check answer →';
    $('sidebarProgressLabel').textContent = `${resumeIndex + 1} of ${stages.length} steps`;
    $('sidebarProgressBar').style.width = `${(resumeIndex + 1) / stages.length * 100}%`;
    document.querySelectorAll('.step-list li,.footer-dot').forEach((item, index) => {
      item.classList.toggle('is-current', index === stageIndex);
      item.classList.toggle('is-complete', index < resumeIndex);
    });
    document.querySelectorAll('.step-jump').forEach((button, index) => {
      button.disabled = busy || correct || index > resumeIndex;
      button.setAttribute('aria-current', index === stageIndex ? 'step' : 'false');
      button.title = index < resumeIndex ? `Review Step ${index + 1}` : '';
    });
    renderModel(stage);
  }
  async function lessonRequest(path, data) {
    if (!auth) throw new Error('Your sign-in could not be loaded. Open Test Prep and try again.');
    const {data:{session}, error} = await auth.auth.getSession();
    if (error || !session?.access_token) throw new Error('Your session expired. Open Test Prep and sign in again.');
    const response = await fetch(`${API}/api/eng/lesson-engine/${path}`, {
      method:'POST', headers:{'Content-Type':'application/json', Authorization:`Bearer ${session.access_token}`},
      body:JSON.stringify(data)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'The lesson could not be loaded. Please try again.');
    return result;
  }
  function showError(message) {
    const feedback = $('answerFeedback');
    feedback.textContent = message;
    feedback.classList.add('is-error');
    feedback.hidden = false;
  }
  async function start() {
    if (document.body.classList.contains('is-preview')) { render(); return; }
    try {
      const result = await lessonRequest('start', {kid_id:child.id});
      if (result.complete) { location.assign('../../#test-prep'); return; }
      planId = result.plan_id; stageIndex = result.step_index; activeStep = result.step;
      resumeIndex = stageIndex; resumeStep = activeStep; revealIndex = 0;
      render();
    } catch (error) {
      showError(error.message);
      $('checkButton').textContent = 'Try loading again →';
      $('checkButton').disabled = false;
    }
  }
  async function openStep(index) {
    if (busy || correct || index > resumeIndex) return;
    if (index === resumeIndex) {
      if (reviewMode) { reviewMode = false; stageIndex = resumeIndex; activeStep = resumeStep; revealIndex = 0; choice = null; hintUsed = false; render(); }
      return;
    }
    busy = true;
    document.querySelectorAll('.step-jump').forEach(button => { button.disabled = true; });
    try {
      const step = document.body.classList.contains('is-preview') ? null :
        await lessonRequest('review', {kid_id:child.id, plan_id:planId, step_index:index});
      stageIndex = index;
      activeStep = step?.step || null;
      reviewMode = true;
      revealIndex = 0;
      choice = null; hintUsed = false;
      render();
    } catch (error) { showError(error.message); }
    finally {
      busy = false;
      document.querySelectorAll('.step-jump').forEach((button, stepIndex) => { button.disabled = correct || stepIndex > resumeIndex; });
      $('checkButton').disabled = !reviewMode && !correct && activeStep?.interaction?.type !== 'continue' && choice === null;
    }
  }
  document.querySelectorAll('.step-jump').forEach((button, index) => button.addEventListener('click', () => openStep(index)));
  $('hintButton').addEventListener('click', async () => {
    if (busy || reviewMode) return;
    busy = true;
    hintUsed = true;
    const fallback = stageIndex === 0 ? 'Look at the two quarters on top, then the quarter left over.' : stages[stageIndex].hint;
    const button = $('hintButton');
    button.disabled = true; button.textContent = 'Thinking of a hint…';
    $('checkButton').disabled = true;
    $('hintCopy').textContent = 'Thinking of a hint…'; $('hintCopy').hidden = false;
    try {
      const result = document.body.classList.contains('is-preview') ? {hint:fallback} :
        await lessonRequest('help', {kid_id:child.id, plan_id:planId, step_index:stageIndex,
          help_kind:'explain', reveal_phase:stageIndex === 0 ? revealIndex : 0});
      $('hintCopy').textContent = result.hint || fallback;
    } catch { $('hintCopy').textContent = fallback; }
    finally {
      busy = false;
      button.disabled = false; button.textContent = '✦ Explain another way';
      $('checkButton').disabled = stageIndex !== 0 && choice === null && !correct && activeStep?.interaction?.type !== 'continue';
    }
  });
  $('checkButton').addEventListener('click', async () => {
    if (stageIndex === 0 && (activeStep?.interaction?.type === 'continue' || document.body.classList.contains('is-preview')) && revealIndex < 3) {
      revealIndex++; hintUsed = false; render(); return;
    }
    if (reviewMode) { reviewMode = false; stageIndex = resumeIndex; activeStep = resumeStep; revealIndex = 0; choice = null; hintUsed = false; render(); return; }
    if (document.body.classList.contains('is-preview')) {
      if (stageIndex === 0) { stageIndex = 1; resumeIndex = 1; revealIndex = 0; choice = null; render(); return; }
      if (correct) {
        if (stageIndex === stages.length - 1) { location.assign('../../#test-prep'); return; }
        stageIndex++; resumeIndex = stageIndex; resumeStep = activeStep; revealIndex = 0;
        choice = null; correct = false; hintUsed = false; render(); return;
      }
      if (choice === null) return;
      // The design preview has no account or server-side answer check.
      correct = true; complete = stageIndex === stages.length - 1;
      $('answerFeedback').hidden = false; $('answerFeedback').textContent = 'Exactly. Nice work!';
      $('answerFeedback').classList.remove('is-error');
      $('sceneTakeaway').hidden = false;
      $('checkButton').textContent = complete ? 'Finish lesson →' : 'Continue →';
      return;
    }
    if (!planId) { await start(); return; }
    if (correct) {
      if (complete) { location.assign('../../#test-prep'); return; }
      stageIndex = pendingStep.step_index; activeStep = pendingStep.step; pendingStep = null;
      resumeIndex = stageIndex; resumeStep = activeStep; revealIndex = 0;
      choice = null; correct = false; hintUsed = false; render(); return;
    }
    if (choice === null && activeStep?.interaction.type !== 'continue') return;
    if (!planId) return;
    const feedback = $('answerFeedback');
    busy = true; $('checkButton').disabled = true;
    try {
      const result = await lessonRequest('answer', {kid_id:child.id, plan_id:planId,
        step_index:stageIndex, option_index:activeStep.interaction.type === 'continue' ? null : choice,
        hint_used:hintUsed});
      feedback.hidden = false;
      if (!result.correct) {
        feedback.textContent = 'Let’s look at the pieces again.';
        feedback.classList.add('is-error');
        const selectedOption = choice;
        const fallback = result.hint || 'Look at the visual and try again.';
        $('hintCopy').textContent = 'Thinking of a hint…'; $('hintCopy').hidden = false;
        hintUsed = true; choice = null;
        $('answerOptions').querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed','false'));
        try {
          const help = await lessonRequest('help', {kid_id:child.id, plan_id:planId,
            step_index:stageIndex, help_kind:'hint', option_index:selectedOption});
          $('hintCopy').textContent = help.hint || fallback;
        } catch { $('hintCopy').textContent = fallback; }
        return;
      }
      correct = true;
      complete = result.complete;
      pendingStep = result.complete ? null : result;
      feedback.textContent = 'Exactly. Nice work!';
      feedback.classList.remove('is-error');
      $('sceneTakeaway').hidden = false;
      $('hintButton').hidden = true;
      $('answerOptions').querySelectorAll('button').forEach(button => { button.disabled = true; });
      $('checkButton').textContent = complete ? 'Finish lesson →' : 'Continue →';
    } catch (error) {
      showError(error.message);
    } finally {
      busy = false;
      $('checkButton').disabled = !correct && activeStep?.interaction.type !== 'continue' && choice === null;
    }
  });
  start();
})();
