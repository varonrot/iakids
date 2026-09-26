(() => {
  'use strict';
  const script = document.currentScript;
  const base = new URL('../', script.src);
  const dialog = document.createElement('dialog');
  dialog.className = 'prep-modal';
  dialog.id = 'testPrepDialog';
  dialog.setAttribute('aria-labelledby', 'prepTitle');
  const icons = {
    photo: '<path d="M4 7h4l2-3h4l2 3h4v14H4Z"/><circle cx="12" cy="13" r="4"/>',
    file: '<path d="M6 2h8l5 5v15H6Z"/><path d="M14 2v6h5M9 12h7M9 16h7"/>',
    topics: '<path d="m3 5 2 2 3-4m-5 9 2 2 3-4m-5 9 2 2 3-4M12 5h9M12 12h9M12 19h9"/>'
  };
  const topicCatalog = {
    Math: {
      1: ['Counting to 100', 'Place value to 100', 'Addition within 20', 'Subtraction within 20', 'Number patterns', 'Comparing numbers', 'Shapes and solids', 'Measuring length', 'Time to the hour', 'Money basics', 'Word problems'],
      2: ['Place value to 1,000', 'Addition with regrouping', 'Subtraction with regrouping', 'Multiplication basics', 'Division basics', 'Fractions: halves and quarters', 'Measurement', 'Time and calendars', 'Money problems', 'Shapes and symmetry', 'Word problems'],
      3: ['Multiplication facts', 'Division facts', 'Multi-digit addition', 'Multi-digit subtraction', 'Fractions on a number line', 'Equivalent fractions', 'Area and perimeter', 'Time intervals', 'Data and graphs', 'Word problems'],
      4: ['Place value and large numbers', 'Multi-digit multiplication', 'Long division', 'Understanding fractions', 'Equivalent fractions', 'Adding and subtracting fractions', 'Decimals', 'Factors and multiples', 'Angles and shapes', 'Area and perimeter', 'Word problems'],
      5: ['Operations with whole numbers', 'Multiplying fractions', 'Dividing fractions', 'Adding and subtracting decimals', 'Multiplying decimals', 'Percentages', 'Volume', 'Coordinate grids', 'Data and graphs', 'Multi-step word problems'],
      6: ['Ratios and rates', 'Percentages', 'Fractions and decimals', 'Negative numbers', 'Order of operations', 'Expressions and equations', 'Geometry and area', 'Volume and surface area', 'Statistics and probability', 'Multi-step word problems']
    },
    English: {
      1: ['Letters and sounds', 'Phonics', 'Sight words', 'Everyday vocabulary', 'Simple sentences', 'Listening comprehension', 'Short stories'],
      2: ['Phonics and spelling', 'Vocabulary', 'Reading short texts', 'Finding details', 'Nouns and verbs', 'Sentence writing', 'Listening comprehension'],
      3: ['Reading comprehension', 'Main idea', 'Vocabulary in context', 'Parts of speech', 'Present simple', 'Questions and answers', 'Paragraph writing'],
      4: ['Reading comprehension', 'Main idea and details', 'Making inferences', 'Present simple', 'Past simple', 'Questions and negatives', 'Paragraph writing'],
      5: ['Reading comprehension', 'Inference and evidence', 'Vocabulary in context', 'Past and future tenses', 'Comparatives', 'Writing a summary', 'Opinion writing'],
      6: ['Reading longer texts', 'Main idea and evidence', 'Inference', 'Vocabulary and idioms', 'Verb tenses', 'Writing an argument', 'Research and presentations']
    },
    Science: {
      1: ['The five senses', 'Living and nonliving things', 'Animals', 'Plants', 'Seasons', 'Materials', 'Caring for the environment'],
      2: ['Living things', 'The human body', 'Plants and animals', 'Materials and their properties', 'Weather and seasons', 'Habitats', 'Healthy habits'],
      3: ['Life cycles', 'Plants and their parts', 'Food chains', 'States of matter', 'Forces and motion', 'Light and sound', 'Earth and space'],
      4: ['Ecosystems', 'Adaptations', 'The human body', 'Matter and materials', 'Electricity', 'Energy', 'The water cycle', 'Earth and space'],
      5: ['Cells and living things', 'Ecosystems and food webs', 'The human body', 'Matter and changes', 'Forces and motion', 'Energy and electricity', 'Weather and climate'],
      6: ['Ecosystems and interdependence', 'The human body', 'Matter and mixtures', 'Energy transfer', 'Electric circuits', 'Earth systems', 'The solar system', 'Scientific investigations']
    },
    Hebrew: {
      1: ['Letters and vowel marks', 'Reading words', 'Reading sentences', 'Vocabulary', 'Handwriting', 'Listening to stories'],
      2: ['Reading fluency', 'Reading comprehension', 'Vocabulary', 'Sentence structure', 'Spelling', 'Short writing'],
      3: ['Reading comprehension', 'Main idea', 'Vocabulary in context', 'Parts of speech', 'Spelling', 'Paragraph writing'],
      4: ['Main idea and details', 'Reading comprehension', 'Inference', 'Vocabulary', 'Grammar', 'Writing a summary'],
      5: ['Reading comprehension', 'Inference and evidence', 'Text structure', 'Grammar', 'Writing a summary', 'Opinion writing'],
      6: ['Reading longer texts', 'Main idea and evidence', 'Inference', 'Language and grammar', 'Comparing texts', 'Argumentative writing']
    },
    History: {
      1: ['Past and present', 'Family stories', 'How people lived long ago', 'Timelines'],
      2: ['Past and present', 'Family and community history', 'Important events', 'Timelines'],
      3: ['Timelines and sources', 'Ancient civilizations', 'People and communities', 'Changes over time'],
      4: ['Timelines and sources', 'Ancient civilizations', 'Everyday life in the past', 'Important people and events'],
      5: ['Historical sources', 'Ancient civilizations', 'Empires and societies', 'Causes and consequences', 'Historical timelines'],
      6: ['Historical sources and evidence', 'Civilizations and empires', 'Migration and trade', 'Cause and effect', 'Comparing historical periods']
    },
    Geography: {
      1: ['My home and neighborhood', 'Maps and symbols', 'Land and water', 'Weather'],
      2: ['Maps and directions', 'My community', 'Landforms', 'Weather and seasons'],
      3: ['Reading maps', 'Continents and oceans', 'Landforms', 'Climate', 'People and places'],
      4: ['Maps and scale', 'Continents and countries', 'Landforms', 'Climate zones', 'Natural resources'],
      5: ['Maps and coordinates', 'Regions of the world', 'Climate and environment', 'Population', 'Natural resources'],
      6: ['Maps and coordinates', 'Physical geography', 'Climate and ecosystems', 'Population and migration', 'Human impact on the environment']
    }
  };
  const option = (kind, title, text) => `<button type="button" class="prep-option" data-prep-action="${kind}"><span class="prep-icon"><svg viewBox="0 0 24 24" aria-hidden="true">${icons[kind]}</svg></span><strong>${title}</strong><small>${text}</small><span class="prep-chevron" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></span></button>`;
  dialog.innerHTML = `<button type="button" class="prep-close" aria-label="Close Test Prep">×</button>
    <section data-prep-view="start"><div class="prep-hero"><img alt="" width="1500" height="500"><div class="prep-hero-copy"><h2 id="prepTitle">Test Prep</h2><p>Let’s get ready for your test!</p></div></div>
    <div class="prep-content"><h3>How would you like to start?</h3><div class="prep-options">
    ${option('photo', 'Upload a photo', 'Take or upload a photo of your worksheet.')}
    ${option('file', 'Upload a file', 'Add a PDF, document or image.')}
    ${option('topics', 'Choose topics', 'Pick the topics you want to practice.')}
    </div><p class="prep-error" role="alert" hidden></p><footer class="prep-footer"><button class="prep-secondary" type="button" data-prep-close>Cancel</button><p>We’ll help you build a study plan from your material.</p></footer></div></section>
    <section class="prep-step" data-prep-view="file" hidden><button class="prep-back" type="button">← Back</button><h2 id="prepFileTitle">Your material</h2><p class="prep-filename"></p><img class="prep-preview" alt="Selected worksheet preview" hidden><p class="prep-notice">Your file is selected for preview only. Study-plan creation from uploaded material is coming next. Nothing has been uploaded.</p><button type="button" class="prep-secondary" data-prep-action="replace">Choose another file</button></section>
    <section class="prep-step prep-topics-step" data-prep-view="topics" hidden><button class="prep-back" type="button">← Back</button><h2 id="prepTopicsTitle">Choose topics</h2><p class="prep-learner" aria-live="polite"></p><form id="prepTopicsForm"><label for="prepSubject">Subject</label><select id="prepSubject" required><option>Math</option><option>English</option><option>Science</option><option>Hebrew</option><option>History</option><option>Geography</option><option>Other</option></select><label for="prepTopicSearch">Search topics</label><input id="prepTopicSearch" type="search" placeholder="Search topics for this grade" autocomplete="off"><div class="prep-topic-heading"><strong>Select topics to prepare</strong><span class="prep-topic-count" aria-live="polite">0 selected</span></div><div class="prep-topic-list" role="group" aria-label="Topics for this grade"></div><p class="prep-topic-empty" hidden>No matching topics. Add your own below.</p><div class="prep-add-topic"><label for="prepCustomTopic">Another topic</label><div><input id="prepCustomTopic" maxlength="100" placeholder="Add a topic from your test" autocomplete="off"><button type="button" class="prep-secondary" id="prepAddTopic">Add</button></div></div><label for="prepTestDate">Test date (optional)</label><input id="prepTestDate" type="date"><p class="prep-status" role="status"></p><footer class="prep-topic-footer"><span class="prep-topic-summary">0 topics selected</span><button class="prep-primary" type="submit" disabled>Keep topic list →</button></footer></form></section>
    <section class="prep-step prep-plan-step" data-prep-view="plan" hidden><button class="prep-back prep-edit-topics" type="button">← Edit topics</button><h2 id="prepPlanTitle">Let’s get ready!</h2><p class="prep-plan-subtitle"></p><div class="prep-plan-layout"><div class="prep-plan-roadmap"><p class="prep-plan-kicker">YOUR PATH</p><ol class="prep-plan-steps"><li class="prep-plan-active"><span class="prep-plan-number">1</span><span class="prep-plan-icon prep-plan-icon-1"><svg viewBox="0 0 36 36" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="8" y="7" width="21" height="26" rx="3"/><path d="M14 7.5h2.2a2.3 2.3 0 0 1 4.6 0H23v4H14zM13 18l2 2 3-3m3 2h4M13 26l2 2 3-3m3 2h4"/></svg></span><div><strong>Quick check</strong><small>See what you already know.</small></div></li><li><span class="prep-plan-number">2</span><span class="prep-plan-icon prep-plan-icon-2"><svg viewBox="0 0 36 36" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 23c-.5-2-4-4.2-4-9a10 10 0 1 1 20 0c0 4.8-3.5 7-4 9M13 25h10m-9 4h8m-6 3h4M18 23v-7m-3-2c0 3 6 3 6 0"/></svg></span><div><strong>Learn the idea</strong><small>Build understanding step by step.</small></div></li><li><span class="prep-plan-number">3</span><span class="prep-plan-icon prep-plan-icon-3"><svg viewBox="0 0 36 36" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="9" r="4"/><circle cx="7" cy="18" r="3"/><circle cx="29" cy="18" r="3"/><path d="M10 31v-4a8 8 0 0 1 16 0v4H10Zm-7 0v-4a5 5 0 0 1 5-5m25 9v-4a5 5 0 0 0-5-5"/></svg></span><div><strong>Practice together</strong><small>Work through guided examples.</small></div></li><li><span class="prep-plan-number">4</span><span class="prep-plan-icon prep-plan-icon-4"><svg viewBox="0 0 36 36" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="22" width="5" height="10" rx="1"/><rect x="15" y="16" width="5" height="16" rx="1"/><rect x="25" y="6" width="5" height="26" rx="1"/></svg></span><div><strong>Try it yourself</strong><small>Check your readiness.</small></div></li></ol></div><aside class="prep-plan-focus"><p class="prep-plan-kicker">YOUR TOPICS</p><h3 class="prep-plan-subject"></h3><p class="prep-plan-intro">We’ll start with your first topic and adapt the next steps as you learn.</p><div class="prep-plan-chips" aria-label="Saved topics"></div><p class="prep-plan-date" hidden></p></aside><div class="prep-quiz" hidden>
      <div class="prep-quiz-head"><strong>QUICK CHECK</strong><span class="prep-quiz-count"></span></div>
      <h3 class="prep-quiz-question"></h3>
      <div class="prep-quiz-equation" aria-label="Fraction division"></div>
      <div class="prep-quiz-bars" aria-label="Fraction bar model"></div>
      <div class="prep-quiz-choices" role="group" aria-label="Choose an answer"></div>
      <p class="prep-quiz-hint" hidden></p>
      <p class="prep-quiz-feedback" role="status" hidden></p>
      <div class="prep-quiz-actions"><button class="prep-quiz-hint-button" type="button">♧ Need a hint?</button><button class="prep-primary prep-quiz-submit" type="button" disabled>Check answer →</button></div>
    </div><section class="prep-lesson" hidden>
      <div class="prep-quiz-head"><strong>LEARN THE IDEA</strong><span>Step 2 of 4</span></div>
      <h3 class="prep-lesson-headline"></h3><p class="prep-lesson-opening"></p>
      <div class="prep-lesson-visual"><strong>See the groups</strong><p>3/4 ÷ 1/2 = 1½</p><div class="prep-quiz-bars"></div></div>
      <ol class="prep-lesson-steps"></ol><p class="prep-lesson-takeaway"></p>
      <button class="prep-secondary prep-lesson-back" type="button">← Review quick check</button>
    </section></div><footer class="prep-plan-footer"><span>✓ Your topic list is saved for this child.</span><div><p>Learning activities are coming next.</p><button class="prep-primary prep-start-quiz" type="button">Start quick check →</button></div></footer></section>
    <input type="file" data-prep-input="photo" accept="image/jpeg,image/png,image/webp,image/heic,image/heif" hidden>
    <input type="file" data-prep-input="file" accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.webp,.heic,.heif" hidden>`;
  dialog.querySelector('.prep-hero img').src = new URL('assets/hero/test-prep-hero.webp', base).href;
  document.body.append(dialog);
  let opener, previousOverflow, previewURL, fileKind = 'file';
  let topicChildId = null, topicChildGrade = null, remoteDraftChild = null, topicRevision = 0;
  const fractionQuestions = [
    {key:'fractions-q1', top:[3,4], divisor:[1,2], choices:['1','1½','2'], correct:'1½', hint:'A half covers two quarters. One half fits, with one quarter left over: another half of a half.', explanation:'Three quarters contains one whole half and half of another half: 1½.'},
    {key:'fractions-q2', top:[2,3], divisor:[1,3], choices:['1','2','3'], correct:'2', hint:'Both fractions are divided into thirds. Count how many one-third pieces are shaded.', explanation:'Two thirds contains two groups of one third.'},
    {key:'fractions-q3', top:[1,2], divisor:[1,4], choices:['1','2','4'], correct:'2', hint:'Split a half into two equal pieces. What fraction of the whole is each piece?', explanation:'A half contains two quarters, so the answer is 2.'}
  ];
  let quizDraft = null, quizRows = new Map(), quizIndex = 0, quizChoice = null, quizHintUsed = false, quizBusy = false;
  let selectedTopics = new Set();
  let customTopics = [];
  const topicsForm = dialog.querySelector('#prepTopicsForm');
  const subjectField = dialog.querySelector('#prepSubject');
  const searchField = dialog.querySelector('#prepTopicSearch');
  const topicList = dialog.querySelector('.prep-topic-list');
  const gradeFor = child => Number(child?.age);
  const draftKey = id => `iakids.eng.prep.topics.${id}`;
  function saveTopicDraft() {
    const grade = gradeFor(window.IAKidsAuth?.child);
    if (!topicChildId || !Number.isInteger(grade) || grade < 1 || grade > 6) return;
    try {
      sessionStorage.setItem(draftKey(topicChildId), JSON.stringify({grade, subject:subjectField.value, topics:[...selectedTopics], custom:customTopics, date:dialog.querySelector('#prepTestDate').value}));
    } catch {}
  }
  function updateTopicCount() {
    const count = selectedTopics.size;
    dialog.querySelector('.prep-topic-count').textContent = `${count} selected`;
    dialog.querySelector('.prep-topic-summary').textContent = `${count} ${count === 1 ? 'topic' : 'topics'} selected`;
    topicsForm.querySelector('[type="submit"]').disabled = count === 0;
  }
  function renderTopics() {
    const grade = gradeFor(window.IAKidsAuth?.child);
    const available = topicCatalog[subjectField.value]?.[grade] || [];
    const search = searchField.value.trim().toLocaleLowerCase();
    topicList.replaceChildren();
    const visible = [...new Set([...available, ...customTopics])].filter(name => name.toLocaleLowerCase().includes(search));
    visible.forEach(name => {
      const label = document.createElement('label');
      label.className = 'prep-topic-choice';
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.value = name;
      checkbox.checked = selectedTopics.has(name);
      const text = document.createElement('span');
      text.textContent = name;
      label.append(checkbox, text);
      topicList.append(label);
    });
    dialog.querySelector('.prep-topic-empty').hidden = visible.length > 0;
    updateTopicCount();
  }
  function setupTopics() {
    const child = window.IAKidsAuth?.child;
    const grade = gradeFor(child);
    const valid = !!child?.id && Number.isInteger(grade) && grade >= 1 && grade <= 6;
    dialog.querySelector('.prep-learner').textContent = valid ? `For ${child.child_name} · Grade ${grade}` : 'Choose a learner with a grade to see suggested topics.';
    subjectField.disabled = !valid;
    searchField.disabled = !valid;
    dialog.querySelector('#prepCustomTopic').disabled = !valid;
    dialog.querySelector('#prepAddTopic').disabled = !valid;
    if (topicChildId !== child?.id || topicChildGrade !== grade) {
      topicChildId = child?.id || null;
      topicChildGrade = grade;
      remoteDraftChild = null;
      topicRevision++;
      selectedTopics = new Set();
      customTopics = [];
      subjectField.value = 'Math';
      dialog.querySelector('#prepTestDate').value = '';
      if (valid) {
        try {
          const draft = JSON.parse(sessionStorage.getItem(draftKey(child.id)));
          if (draft?.grade === grade && [...Object.keys(topicCatalog), 'Other'].includes(draft.subject)) {
            subjectField.value = draft.subject;
            selectedTopics = new Set(Array.isArray(draft.topics) ? draft.topics.filter(name => typeof name === 'string' && name.length <= 100) : []);
            customTopics = Array.isArray(draft.custom) ? draft.custom.filter(name => typeof name === 'string' && name.length <= 100) : [];
            dialog.querySelector('#prepTestDate').value = draft.date || '';
          }
        } catch {}
      }
    }
    searchField.value = '';
    dialog.querySelector('.prep-status').textContent = '';
    renderTopics();
    if (valid && remoteDraftChild !== child.id) {
      remoteDraftChild = child.id;
      const revision = topicRevision;
      window.IAKidsAuth.loadTopicDraft(child.id).then(draft => {
        if (!draft || topicChildId !== child.id || topicRevision !== revision || draft.grade !== grade) return;
        if (![...Object.keys(topicCatalog), 'Other'].includes(draft.subject) || !Array.isArray(draft.topics)) return;
        subjectField.value = draft.subject;
        selectedTopics = new Set(draft.topics.filter(name => typeof name === 'string' && name.length <= 100));
        customTopics = Array.isArray(draft.custom_topics) ? draft.custom_topics.filter(name => typeof name === 'string' && name.length <= 100) : [];
        dialog.querySelector('#prepTestDate').value = draft.test_date || '';
        renderTopics();
        saveTopicDraft();
      }).catch(() => {
        if (topicChildId === child.id && topicRevision === revision)
          dialog.querySelector('.prep-status').textContent = 'Saved topics could not be loaded. You can still choose topics and try saving again.';
      });
    }
  }
  function supportsQuickCheck(draft) {
    return draft.subject === 'Math' && draft.grade === 5 && draft.topics.includes('Dividing fractions');
  }
  function renderFractionBar([numerator, denominator], className) {
    const cells = Array.from({length:denominator}, (_, index) => '<span class="' + (index < numerator ? 'filled' : '') + '"></span>').join('');
    return '<div class="prep-quiz-bar-row"><span class="prep-quiz-fraction">' + numerator + '/' + denominator + '</span><div class="prep-quiz-bar ' + className + '" style="--parts:' + denominator + '">' + cells + '</div></div>';
  }
  function renderQuickCheck() {
    const panel = dialog.querySelector('.prep-quiz');
    const question = fractionQuestions[quizIndex];
    const done = quizIndex >= fractionQuestions.length;
    const count = dialog.querySelector('.prep-quiz-count');
    const choices = dialog.querySelector('.prep-quiz-choices');
    const equation = dialog.querySelector('.prep-quiz-equation');
    const bars = dialog.querySelector('.prep-quiz-bars');
    const feedback = dialog.querySelector('.prep-quiz-feedback');
    const hint = dialog.querySelector('.prep-quiz-hint');
    const hintButton = dialog.querySelector('.prep-quiz-hint-button');
    const submit = dialog.querySelector('.prep-quiz-submit');
    panel.hidden = false;
    bars.hidden = false;
    choices.replaceChildren();
    hint.hidden = true;
    feedback.hidden = true;
    if (done) {
      const score = fractionQuestions.filter(item => quizRows.get(item.key)?.is_correct).length;
      count.textContent = '3 of 3 answered';
      dialog.querySelector('.prep-quiz-question').textContent = 'Quick check complete!';
      equation.textContent = score + ' of 3 correct';
      bars.replaceChildren();
      bars.hidden = true;
      feedback.textContent = score === 3 ? 'Great work! You’re ready to build on this idea.' : 'Nice effort. The next step will help you understand the tricky parts.';
      feedback.hidden = false;
      hintButton.textContent = 'Review answers';
      hintButton.hidden = false;
      submit.textContent = 'Learn the idea →';
      submit.disabled = false;
      return;
    }
    const answer = quizRows.get(question.key);
    count.textContent = 'Question ' + (quizIndex + 1) + ' of ' + fractionQuestions.length;
    dialog.querySelector('.prep-quiz-question').textContent = 'How many ' + (question.divisor[0] === 1 ? ({2:'halves',3:'thirds',4:'quarters'}[question.divisor[1]]) : 'groups') + ' fit into ' + ({2:'a half',3:'two thirds',4:'three quarters'}[question.top[1]]) + '?';
    equation.textContent = question.top[0] + '/' + question.top[1] + ' ÷ ' + question.divisor[0] + '/' + question.divisor[1];
    bars.innerHTML = renderFractionBar(question.top, 'prep-quiz-bar-top') + renderFractionBar(question.divisor, 'prep-quiz-bar-bottom');
    question.choices.forEach(choice => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'prep-quiz-choice';
      button.textContent = choice;
      button.dataset.choice = choice;
      button.setAttribute('aria-pressed', String(choice === (answer?.answer || quizChoice)));
      button.disabled = !!answer;
      choices.append(button);
    });
    hint.textContent = question.hint;
    quizHintUsed = answer?.hint_used || false;
    hint.hidden = !quizHintUsed;
    hintButton.textContent = '♧ Need a hint?';
    hintButton.hidden = !!answer;
    if (answer) {
      feedback.textContent = (answer.is_correct ? 'Correct! ' : 'The answer is ' + question.correct + '. ') + question.explanation;
      feedback.classList.toggle('prep-quiz-incorrect', !answer.is_correct);
      feedback.hidden = false;
      submit.textContent = quizIndex === fractionQuestions.length - 1 ? 'See results →' : 'Next question →';
      submit.disabled = false;
    } else {
      feedback.classList.remove('prep-quiz-incorrect');
      submit.textContent = 'Check answer →';
      submit.disabled = !quizChoice;
    }
  }
  function syncQuickCheckRows(rows) {
    quizRows = new Map(rows.filter(row => fractionQuestions.some(item => item.key === row.question_key)).map(row => [row.question_key, row]));
    quizIndex = fractionQuestions.findIndex(item => !quizRows.has(item.key));
    if (quizIndex < 0) quizIndex = fractionQuestions.length;
    quizChoice = null;
    const complete = quizIndex === fractionQuestions.length;
    dialog.querySelector('.prep-start-quiz').textContent = complete ? 'Continue learning →' : quizIndex > 0 ? 'Continue quick check →' : 'Start quick check →';
    dialog.querySelector('.prep-plan-footer p').textContent = complete ? 'Your quick check is saved. Your next step is ready.' : quizIndex > 0 ? 'Your answers are saved. Pick up where you left off.' : 'A short visual check is ready.';
  }
  async function refreshQuickCheckProgress(draft) {
    if (!supportsQuickCheck(draft)) return;
    const childId = topicChildId;
    const button = dialog.querySelector('.prep-start-quiz');
    button.disabled = true;
    button.textContent = 'Checking progress…';
    try {
      const rows = await window.IAKidsAuth.loadQuickCheck(childId, 'Dividing fractions');
      if (dialog.open && topicChildId === childId && quizDraft === draft) syncQuickCheckRows(rows);
    } catch (error) {
      if (dialog.open && topicChildId === childId && quizDraft === draft) {
        dialog.querySelector('.prep-plan-footer p').textContent = error.message;
        button.textContent = 'Try to continue →';
      }
    } finally {
      if (dialog.open && topicChildId === childId && quizDraft === draft) button.disabled = false;
    }
  }
  async function startQuickCheck() {
    if (!quizDraft || !supportsQuickCheck(quizDraft) || quizBusy) return;
    quizBusy = true;
    const button = dialog.querySelector('.prep-start-quiz');
    button.disabled = true;
    button.textContent = 'Loading…';
    try {
      const rows = await window.IAKidsAuth.loadQuickCheck(topicChildId, 'Dividing fractions');
      if (!dialog.open || topicChildId !== window.IAKidsAuth?.child?.id) return;
      syncQuickCheckRows(rows);
      dialog.classList.add('prep-quiz-active');
      renderQuickCheck();
      if (quizIndex === fractionQuestions.length) {
        quizBusy = false;
        await startLesson();
      }
    } catch (error) {
      dialog.querySelector('.prep-plan-footer p').textContent = error.message;
    } finally {
      quizBusy = false;
      button.disabled = false;
    }
  }
  function renderLesson(content) {
    const child = window.IAKidsAuth?.child;
    if (child?.id && quizDraft?.grade === 5 && quizDraft?.subject === 'Math') {
      try {
        sessionStorage.setItem('iakids.eng.lesson-workspace.v1', JSON.stringify({
          version: 1, at: Date.now(),
          child: {id: child.id, child_name: child.child_name},
          draft: quizDraft, lesson: content
        }));
        dialog.close();
        location.assign(new URL('test-prep/lesson/', base).href);
        return;
      } catch (error) {
        console.warn('Lesson workspace handoff failed; showing the lesson here.', error);
      }
    }
    dialog.querySelector('.prep-lesson-headline').textContent = content.headline;
    dialog.querySelector('.prep-lesson-opening').textContent = content.opening;
    dialog.querySelector('.prep-lesson-takeaway').textContent = content.takeaway;
    dialog.querySelector('.prep-lesson-visual .prep-quiz-bars').innerHTML =
      renderFractionBar([3,4], 'prep-quiz-bar-top') + renderFractionBar([1,2], 'prep-quiz-bar-bottom');
    const steps = dialog.querySelector('.prep-lesson-steps');
    steps.replaceChildren();
    content.steps.forEach((step, index) => {
      const item = document.createElement('li');
      const heading = document.createElement('strong');
      const body = document.createElement('p');
      heading.textContent = (index + 1) + '. ' + step.title;
      body.textContent = step.body;
      item.append(heading, body);
      steps.append(item);
    });
    dialog.querySelector('.prep-quiz').hidden = true;
    dialog.querySelector('.prep-lesson').hidden = false;
    dialog.classList.remove('prep-quiz-active');
    dialog.classList.add('prep-lesson-active');
    const cards = dialog.querySelectorAll('.prep-plan-steps li');
    cards.forEach((card, i) => card.classList.toggle('prep-plan-active', i === 1));
  }
  async function startLesson() {
    if (quizBusy || quizIndex < fractionQuestions.length) return;
    quizBusy = true;
    const button = dialog.querySelector('.prep-quiz-submit');
    const childId = topicChildId;
    button.disabled = true;
    button.textContent = 'Preparing your lesson…';
    try {
      const lesson = await window.IAKidsAuth.loadTestPrepLesson(childId);
      if (!dialog.open || childId !== topicChildId) return;
      renderLesson(lesson);
    } catch (error) {
      const feedback = dialog.querySelector('.prep-quiz-feedback');
      feedback.textContent = error.message;
      feedback.classList.add('prep-quiz-incorrect');
      feedback.hidden = false;
      button.textContent = 'Try lesson again →';
      button.disabled = false;
    } finally {
      quizBusy = false;
    }
  }
  async function submitQuickCheck() {
    if (quizBusy || !quizDraft) return;
    if (quizIndex >= fractionQuestions.length) {
      await startLesson();
      return;
    }
    const question = fractionQuestions[quizIndex];
    if (quizRows.has(question.key)) {
      quizIndex++;
      quizChoice = null;
      renderQuickCheck();
      return;
    }
    if (!quizChoice) return;
    const childId = topicChildId, choice = quizChoice;
    const submit = dialog.querySelector('.prep-quiz-submit');
    quizBusy = true;
    submit.disabled = true;
    submit.textContent = 'Saving…';
    try {
      const row = {key:question.key, choice, correct:choice === question.correct, hintUsed:quizHintUsed};
      await window.IAKidsAuth.saveQuickCheck(childId, 'Dividing fractions', 5, row);
      if (!dialog.open || childId !== topicChildId || quizDraft?.grade !== 5) return;
      quizRows.set(question.key, {question_key:question.key, answer:choice, is_correct:row.correct, hint_used:row.hintUsed});
      renderQuickCheck();
    } catch (error) {
      const feedback = dialog.querySelector('.prep-quiz-feedback');
      feedback.textContent = error.message;
      feedback.hidden = false;
      submit.textContent = 'Try again →';
      submit.disabled = false;
    } finally {
      quizBusy = false;
    }
  }
  function renderPlan(draft) {
    const child = window.IAKidsAuth?.child;
    quizDraft = draft;
    dialog.classList.remove('prep-quiz-active', 'prep-lesson-active');
    dialog.querySelector('.prep-quiz').hidden = true;
    dialog.querySelector('.prep-lesson').hidden = true;
    dialog.querySelectorAll('.prep-plan-steps li').forEach((card, i) => card.classList.toggle('prep-plan-active', i === 0));
    const supported = supportsQuickCheck(draft);
    dialog.querySelector('.prep-start-quiz').disabled = !supported;
    dialog.querySelector('.prep-start-quiz').textContent = 'Start quick check →';
    dialog.querySelector('.prep-plan-footer p').textContent = supported ? 'Checking your saved progress…' : 'Interactive questions for these topics are coming next.';
    const name = child?.child_name?.trim() || 'learner';
    dialog.querySelector('#prepPlanTitle').textContent = `Let’s get ready, ${name}!`;
    dialog.querySelector('.prep-plan-subtitle').textContent = `Your plan for ${draft.subject} · Grade ${draft.grade}`;
    dialog.querySelector('.prep-plan-subject').textContent = draft.subject;
    const chips = dialog.querySelector('.prep-plan-chips');
    chips.replaceChildren();
    draft.topics.forEach(topic => {
      const chip = document.createElement('span');
      chip.textContent = topic;
      chips.append(chip);
    });
    const date = dialog.querySelector('.prep-plan-date');
    date.hidden = !draft.date;
    if (draft.date) date.textContent = `Test date: ${new Date(`${draft.date}T12:00:00`).toLocaleDateString('en', {year:'numeric', month:'long', day:'numeric'})}`;
    if (supported) refreshQuickCheckProgress(draft);
  }
  function view(name) {
    dialog.querySelectorAll('[data-prep-view]').forEach(el => { el.hidden = el.dataset.prepView !== name; });
    dialog.setAttribute('aria-labelledby', name === 'start' ? 'prepTitle' : name === 'file' ? 'prepFileTitle' : name === 'plan' ? 'prepPlanTitle' : 'prepTopicsTitle');
    dialog.classList.toggle('prep-plan-open', name === 'plan');
    dialog.scrollTop = 0;
    if (name === 'topics') setupTopics();
    dialog.querySelector(`[data-prep-view="${name}"] button`)?.focus();
  }
  function open(trigger) {
    if (dialog.open) return;
    opener = trigger;
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog.showModal();
    view('start');
  }
  function releasePreview() {
    const img = dialog.querySelector('.prep-preview');
    img.hidden = true;
    img.removeAttribute('src');
    if (previewURL) URL.revokeObjectURL(previewURL);
    previewURL = null;
  }
  dialog.addEventListener('close', () => {
    document.body.style.overflow = previousOverflow || '';
    releasePreview();
    dialog.querySelectorAll('input[type=file]').forEach(input => { input.value = ''; });
    dialog.querySelector('.prep-error').hidden = true;
    opener?.focus();
  });
  dialog.addEventListener('click', event => {
    if (event.target.closest('.prep-close,[data-prep-close]')) dialog.close();
    if (event.target.closest('.prep-edit-topics')) view('topics');
    if (event.target.closest('.prep-start-quiz')) startQuickCheck();
    if (event.target.closest('.prep-quiz-submit')) submitQuickCheck();
    if (event.target.closest('.prep-quiz-hint-button')) {
      if (quizIndex >= fractionQuestions.length) { quizIndex = 0; quizChoice = null; renderQuickCheck(); }
      else { quizHintUsed = true; const hint = dialog.querySelector('.prep-quiz-hint'); hint.textContent = fractionQuestions[quizIndex].hint; hint.hidden = false; }
    }
    if (event.target.closest('.prep-lesson-back')) { dialog.querySelector('.prep-lesson').hidden = true; dialog.classList.remove('prep-lesson-active'); dialog.classList.add('prep-quiz-active'); dialog.querySelectorAll('.prep-plan-steps li').forEach((card, i) => card.classList.toggle('prep-plan-active', i === 0)); quizIndex = fractionQuestions.length; renderQuickCheck(); }
    const choice = event.target.closest('.prep-quiz-choice');
    if (choice && !quizBusy && !quizRows.has(fractionQuestions[quizIndex]?.key)) { quizChoice = choice.dataset.choice; dialog.querySelectorAll('.prep-quiz-choice').forEach(button => button.setAttribute('aria-pressed', String(button === choice))); dialog.querySelector('.prep-quiz-submit').disabled = false; }
    else if (event.target.closest('.prep-back')) view('start');
    const action = event.target.closest('[data-prep-action]')?.dataset.prepAction;
    if (action === 'topics') view('topics');
    if (['photo', 'file', 'replace'].includes(action)) {
      if (action !== 'replace') fileKind = action;
      dialog.querySelector(`[data-prep-input="${fileKind}"]`).click();
    }
    if (event.target === dialog) {
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    }
  });
  dialog.querySelectorAll('input[type=file]').forEach(input => input.addEventListener('change', () => {
    const file = input.files[0];
    if (!file) return;
    const error = dialog.querySelector('.prep-error');
    const ext = file.name.split('.').pop().toLowerCase();
    const valid = input.dataset.prepInput === 'photo' ? ['jpg','jpeg','png','webp','heic','heif'] : ['pdf','doc','docx','txt','jpg','jpeg','png','webp','heic','heif'];
    if (!valid.includes(ext) || file.size > 20 * 1024 * 1024 || !file.size) {
      error.textContent = 'Choose a supported, non-empty file up to 20 MB.';
      error.hidden = false;
      input.value = '';
      view('start');
      return;
    }
    error.hidden = true;
    releasePreview();
    dialog.querySelector('.prep-filename').textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB`;
    if (['jpg','jpeg','png','webp'].includes(ext)) {
      const img = dialog.querySelector('.prep-preview');
      previewURL = URL.createObjectURL(file);
      img.onerror = () => { img.hidden = true; };
      img.src = previewURL;
      img.hidden = false;
    }
    view('file');
  }));
  subjectField.addEventListener('change', () => {
    topicRevision++;
    selectedTopics.clear();
    customTopics = [];
    searchField.value = '';
    dialog.querySelector('.prep-status').textContent = '';
    renderTopics();
    saveTopicDraft();
  });
  searchField.addEventListener('input', () => { topicRevision++; renderTopics(); });
  topicList.addEventListener('change', event => {
    if (!event.target.matches('input[type="checkbox"]')) return;
    if (event.target.checked) selectedTopics.add(event.target.value);
    else selectedTopics.delete(event.target.value);
    topicRevision++;
    updateTopicCount();
    dialog.querySelector('.prep-status').textContent = '';
    saveTopicDraft();
  });
  function addCustomTopic() {
    const input = dialog.querySelector('#prepCustomTopic');
    const name = input.value.trim().replace(/\s+/g, ' ');
    if (!name || !topicChildId) return;
    if (selectedTopics.size >= 30 && !selectedTopics.has(name)) {
      dialog.querySelector('.prep-status').textContent = 'Choose up to 30 topics for one test.';
      return;
    }
    topicRevision++;
    if (!(topicCatalog[subjectField.value]?.[gradeFor(window.IAKidsAuth?.child)] || []).includes(name) && !customTopics.includes(name)) customTopics.push(name);
    selectedTopics.add(name);
    input.value = '';
    searchField.value = '';
    renderTopics();
    saveTopicDraft();
  }
  dialog.querySelector('#prepAddTopic').addEventListener('click', addCustomTopic);
  dialog.querySelector('#prepCustomTopic').addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); addCustomTopic(); }
  });
  dialog.querySelector('#prepTestDate').addEventListener('change', () => { topicRevision++; saveTopicDraft(); });
  topicsForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (!selectedTopics.size || selectedTopics.size > 30 || !topicChildId) return;
    const childId = topicChildId;
    const revision = topicRevision;
    const draft = {
      grade: topicChildGrade, subject: subjectField.value, topics: [...selectedTopics],
      custom: [...customTopics], date: dialog.querySelector('#prepTestDate').value
    };
    const button = topicsForm.querySelector('[type="submit"]');
    button.disabled = true;
    button.textContent = 'Saving…';
    saveTopicDraft();
    dialog.querySelector('.prep-status').textContent = '';
    try {
      await window.IAKidsAuth.saveTopicDraft(childId, draft);
      if (dialog.open && topicChildId === childId && topicRevision === revision) {
        renderPlan(draft);
        view('plan');
      } else if (topicChildId === childId) {
        dialog.querySelector('.prep-status').textContent = 'Your selections changed while saving. Save again to continue.';
      }
    } catch (error) {
      if (topicChildId === childId) dialog.querySelector('.prep-status').textContent = error.message;
    } finally {
      button.textContent = 'Keep topic list →';
      updateTopicCount();
    }
  });
  document.addEventListener('click', event => {
    const trigger = event.target.closest('a[href],button[aria-label="Open Test Prep"]');
    if (!trigger || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const path = trigger.href ? new URL(trigger.href).pathname : '';
    if (path === new URL('test-prep/', base).pathname || trigger.matches('button[aria-label="Open Test Prep"]')) {
      event.preventDefault();
      event.stopImmediatePropagation();
      document.querySelector('.main-nav')?.classList.remove('mobile-open');
      document.getElementById('mobileMenu')?.setAttribute('aria-expanded','false');
      if (window.IAKidsAuth) window.IAKidsAuth.requireChild(() => open(trigger), trigger);
      else location.assign(new URL('#test-prep', base).href);
    }
  }, true);
  window.IAKidsTestPrep = { open };
  window.dispatchEvent(new Event('iakids:prep-ready'));
  if (location.hash === '#test-prep') {
    window.IAKidsAuth?.requireChild(() => open(document.querySelector('a[href="./test-prep/"]')));
    history.replaceState(null, '', location.pathname + location.search);
  }
})();
