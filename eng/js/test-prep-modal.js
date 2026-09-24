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
  const option = (kind, title, text) => `<button type="button" class="prep-option" data-prep-action="${kind}"><span class="prep-icon"><svg viewBox="0 0 24 24" aria-hidden="true">${icons[kind]}</svg></span><strong>${title}</strong><small>${text}</small><span class="prep-chevron" aria-hidden="true">›</span></button>`;
  dialog.innerHTML = `<button type="button" class="prep-close" aria-label="Close Test Prep">×</button>
    <section data-prep-view="start"><div class="prep-hero"><img alt="" width="1500" height="500"><div class="prep-hero-copy"><h2 id="prepTitle">Test Prep</h2><p>Let’s get ready for your test!</p></div></div>
    <div class="prep-content"><h3>How would you like to start?</h3><div class="prep-options">
    ${option('photo', 'Upload a photo', 'Take or upload a photo of your worksheet.')}
    ${option('file', 'Upload a file', 'Add a PDF, document or image.')}
    ${option('topics', 'Choose topics', 'Pick the topics you want to practice.')}
    </div><p class="prep-error" role="alert" hidden></p><footer class="prep-footer"><button class="prep-secondary" type="button" data-prep-close>Cancel</button><p>We’ll help you build a study plan from your material.</p></footer></div></section>
    <section class="prep-step" data-prep-view="file" hidden><button class="prep-back" type="button">← Back</button><h2 id="prepFileTitle">Your material</h2><p class="prep-filename"></p><img class="prep-preview" alt="Selected worksheet preview" hidden><p class="prep-notice">Your file is selected for preview only. Study-plan creation from uploaded material is coming next. Nothing has been uploaded.</p><button type="button" class="prep-secondary" data-prep-action="replace">Choose another file</button></section>
    <section class="prep-step" data-prep-view="topics" hidden><button class="prep-back" type="button">← Back</button><h2 id="prepTopicsTitle">Choose topics</h2><p>What will be on your test?</p><form id="prepTopicsForm"><label for="prepSubject">Subject</label><select id="prepSubject" required><option value="">Choose a subject</option><option>Math</option><option>English</option><option>Science</option><option>Hebrew</option><option>History</option><option>Geography</option><option>Other</option></select><label for="prepTopics">Topics for your test</label><textarea id="prepTopics" required maxlength="1500" rows="4" placeholder="For example: equivalent fractions, adding fractions…"></textarea><p class="prep-notice">You can prepare your topic list here. Suggested topics and study-plan creation are coming next.</p><button class="prep-primary" type="submit">Keep topic list</button><p class="prep-status" role="status"></p></form></section>
    <input type="file" data-prep-input="photo" accept="image/jpeg,image/png,image/webp,image/heic,image/heif" hidden>
    <input type="file" data-prep-input="file" accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.webp,.heic,.heif" hidden>`;
  dialog.querySelector('.prep-hero img').src = new URL('assets/hero/test-prep-hero.webp', base).href;
  document.body.append(dialog);
  let opener, previousOverflow, previewURL, fileKind = 'file';
  function view(name) {
    dialog.querySelectorAll('[data-prep-view]').forEach(el => { el.hidden = el.dataset.prepView !== name; });
    dialog.setAttribute('aria-labelledby', name === 'start' ? 'prepTitle' : name === 'file' ? 'prepFileTitle' : 'prepTopicsTitle');
    dialog.scrollTop = 0;
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
    if (event.target.closest('.prep-back')) view('start');
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
  dialog.querySelector('#prepTopicsForm').addEventListener('submit', event => {
    event.preventDefault();
    const topics = dialog.querySelector('#prepTopics');
    if (!topics.value.trim()) { topics.setCustomValidity('Enter at least one topic.'); topics.reportValidity(); return; }
    dialog.querySelector('.prep-status').textContent = 'Topic list kept while this page stays open. Your study plan has not been created yet.';
  });
  dialog.querySelector('#prepTopics').addEventListener('input', event => { event.target.setCustomValidity(''); dialog.querySelector('.prep-status').textContent = ''; });
  document.addEventListener('click', event => {
    const trigger = event.target.closest('a[href],button[aria-label="Open Test Prep"]');
    if (!trigger || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const path = trigger.href ? new URL(trigger.href).pathname : '';
    if (path === new URL('test-prep/', base).pathname || trigger.matches('button[aria-label="Open Test Prep"]')) {
      event.preventDefault();
      event.stopImmediatePropagation();
      document.querySelector('.main-nav')?.classList.remove('mobile-open');
      document.getElementById('mobileMenu')?.setAttribute('aria-expanded','false');
      window.IAKidsAuth?.requireChild(() => open(trigger), trigger);
    }
  }, true);
  window.IAKidsTestPrep = { open };
  window.dispatchEvent(new Event('iakids:prep-ready'));
  if (location.hash === '#test-prep') {
    window.IAKidsAuth?.requireChild(() => open(document.querySelector('a[href="./test-prep/"]')));
    history.replaceState(null, '', location.pathname + location.search);
  }
})();
