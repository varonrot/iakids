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
  const stages = [
    {
      title:'See the idea', eyebrow:'SEE THE IDEA', equation:'¾ ÷ ½', lead:aiLesson.headline,
      message:aiLesson.opening || 'Look at the pizza. Two quarters make one half.',
      takeaway:'Two quarters make one half. The last quarter is half of another half.',
      question:'How many halves fit into three quarters?', options:['1','1½','2'], answer:'1½', hint:'Two quarters make one half. The third quarter is half of another half.',
      visual:{type:'pizza'}
    },
    {
      title:'Try together', eyebrow:'TRY TOGETHER', equation:'⅔ ÷ ⅓', lead:'Count equal pieces',
      message:'A third is one of three equal parts. Let’s count the thirds in two thirds.',
      takeaway:'Two thirds contains two one-third pieces.',
      question:'How many one-third pieces fit into two thirds?', options:['1','2','3'], answer:'2', hint:'Count the shaded thirds, one at a time.',
      visual:{type:'bar', parts:3, filled:2, label:'2 of 3 equal parts are shaded'}
    },
    {
      title:'Your turn', eyebrow:'YOUR TURN', equation:'½ ÷ ¼', lead:'One last check',
      message:'You’ve seen how to count equal pieces. Try this one yourself.',
      takeaway:'A half contains two quarters.',
      question:'How many quarters fit into one half?', options:['1','2','4'], answer:'2', hint:'A half is the same size as two quarters.',
      visual:{type:'bar', parts:4, filled:2, label:'2 of 4 equal parts are shaded'}
    }
  ];
  let stageIndex = 0, choice = null, correct = false, hintUsed = false;
  $('learnerName').textContent = name;
  $('headerSubject').textContent = payload.draft?.subject || 'Math';
  $('headerGrade').textContent = `Grade ${payload.draft?.grade || 5}`;
  $('sidebarTitle').textContent = payload.draft?.topics?.[0] || 'Dividing fractions';
  $('sidebarContext').textContent = `${payload.draft?.subject || 'Math'} · Grade ${payload.draft?.grade || 5}`;
  $('lessonApp').hidden = false;

  function renderModel(stage) {
    const scene = document.querySelector('.visual-stage');
    const model = $('fractionModel');
    const isModel = stage.visual.type === 'bar';
    scene.classList.toggle('is-model', isModel);
    model.hidden = !isModel;
    scene.setAttribute('aria-label', isModel ? stage.visual.label : 'A pizza divided into four equal quarters. Three remain. Two quarters make one half, and one quarter is half of another half.');
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
    $('sceneEyebrow').textContent = stage.eyebrow;
    $('sceneCounter').textContent = `Step ${stageIndex + 1} of ${stages.length}`;
    $('sceneTitle').textContent = stage.lead;
    $('sceneLead').textContent = stageIndex === 0 ? 'A short visual idea, then one question.' : stage.message;
    $('sceneTakeaway').textContent = stage.takeaway;
    document.querySelector('.equation').replaceChildren(document.createTextNode(stage.equation + ' '), Object.assign(document.createElement('span'), {textContent:'= ?'}));
    $('guideMessage').textContent = stageIndex === 0 ? `${name}, ${stage.message}` : stage.message;
    $('questionText').textContent = stage.question;
    $('questionLabel').textContent = stage.eyebrow;
    $('hintCopy').textContent = stage.hint;
    $('hintCopy').hidden = !hintUsed;
    $('hintButton').hidden = correct;
    $('answerFeedback').hidden = !correct;
    $('answerFeedback').classList.remove('is-error');
    $('answerFeedback').textContent = correct ? 'Exactly. Nice work!' : '';
    const options = $('answerOptions');
    options.replaceChildren();
    stage.options.forEach(value => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = value;
      button.setAttribute('aria-pressed', String(choice === value));
      button.disabled = correct;
      button.addEventListener('click', () => {
        choice = value;
        options.querySelectorAll('button').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
        $('checkButton').disabled = false;
      });
      options.append(button);
    });
    $('checkButton').disabled = !choice && !correct;
    $('checkButton').textContent = correct ? stageIndex === stages.length - 1 ? 'Finish lesson →' : 'Continue →' : 'Check answer →';
    $('sidebarProgressLabel').textContent = `${stageIndex + 1} of ${stages.length} steps`;
    $('sidebarProgressBar').style.width = `${(stageIndex + 1) / stages.length * 100}%`;
    document.querySelectorAll('.step-list li,.footer-dot').forEach((item, index) => {
      item.classList.toggle('is-current', index === stageIndex);
      item.classList.toggle('is-complete', index < stageIndex);
    });
    renderModel(stage);
  }
  $('hintButton').addEventListener('click', () => { hintUsed = true; $('hintCopy').hidden = false; });
  $('checkButton').addEventListener('click', () => {
    if (correct) {
      if (stageIndex === stages.length - 1) { location.assign('../../#test-prep'); return; }
      stageIndex++; choice = null; correct = false; hintUsed = false; render(); return;
    }
    if (!choice) return;
    const feedback = $('answerFeedback');
    feedback.hidden = false;
    if (choice === stages[stageIndex].answer) {
      correct = true;
      feedback.textContent = 'Exactly. Nice work!';
      feedback.classList.remove('is-error');
      $('hintButton').hidden = true;
      $('answerOptions').querySelectorAll('button').forEach(button => { button.disabled = true; });
      $('checkButton').textContent = stageIndex === stages.length - 1 ? 'Finish lesson →' : 'Continue →';
    } else {
      feedback.textContent = 'Take another look at the visual, then try again.';
      feedback.classList.add('is-error');
      $('hintCopy').hidden = false;
      hintUsed = true;
      choice = null;
      $('answerOptions').querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed','false'));
      $('checkButton').disabled = true;
    }
  });
  render();
})();
