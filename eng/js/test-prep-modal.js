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
    <section class="prep-step prep-plan-step" data-prep-view="plan" hidden><button class="prep-back prep-edit-topics" type="button">← Edit topics</button><h2 id="prepPlanTitle">Let’s get ready!</h2><p class="prep-plan-subtitle"></p><div class="prep-plan-layout"><div class="prep-plan-roadmap"><p class="prep-plan-kicker">YOUR PATH</p><ol class="prep-plan-steps"><li class="prep-plan-active"><span class="prep-plan-number">1</span><div><strong>Quick check</strong><small>See what you already know.</small></div></li><li><span class="prep-plan-number">2</span><div><strong>Learn the idea</strong><small>Build understanding step by step.</small></div></li><li><span class="prep-plan-number">3</span><div><strong>Practice together</strong><small>Work through guided examples.</small></div></li><li><span class="prep-plan-number">4</span><div><strong>Try it yourself</strong><small>Check your readiness.</small></div></li></ol></div><aside class="prep-plan-focus"><p class="prep-plan-kicker">YOUR TOPICS</p><h3 class="prep-plan-subject"></h3><p class="prep-plan-intro">We’ll start with your first topic and adapt the next steps as you learn.</p><div class="prep-plan-chips" aria-label="Saved topics"></div><p class="prep-plan-date" hidden></p></aside></div><footer class="prep-plan-footer"><span>✓ Your topic list is saved for this child.</span><div><p>Learning activities are coming next.</p><button class="prep-primary" type="button" disabled>Start quick check →</button></div></footer></section>
    <input type="file" data-prep-input="photo" accept="image/jpeg,image/png,image/webp,image/heic,image/heif" hidden>
    <input type="file" data-prep-input="file" accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.webp,.heic,.heif" hidden>`;
  dialog.querySelector('.prep-hero img').src = new URL('assets/hero/test-prep-hero.webp', base).href;
  document.body.append(dialog);
  let opener, previousOverflow, previewURL, fileKind = 'file';
  let topicChildId = null, topicChildGrade = null, remoteDraftChild = null, topicRevision = 0;
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
  function renderPlan(draft) {
    const child = window.IAKidsAuth?.child;
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
