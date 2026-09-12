const state = {
  step: 1,
  file: null,
  child: null,
};

const els = {
  fileInput: document.getElementById('fileInput'),
  cameraInput: document.getElementById('cameraInput'),
  dropZone: document.getElementById('dropZone'),
  uploadState: document.getElementById('uploadState'),
  documentState: document.getElementById('documentState'),
  imagePreview: document.getElementById('imagePreview'),
  pdfPreview: document.getElementById('pdfPreview'),
  genericPreview: document.getElementById('genericPreview'),
  fileName: document.getElementById('fileName'),
  analyzeBtn: document.getElementById('analyzeBtn'),
  replaceFileBtn: document.getElementById('replaceFileBtn'),
  identifiedCard: document.getElementById('identifiedCard'),
  identifiedText: document.getElementById('identifiedText'),
  startHelpBtn: document.getElementById('startHelpBtn'),
  steps: [...document.querySelectorAll('#steps li')],
  mobileStepNumber: document.getElementById('mobileStepNumber'),
  mobileProgressBar: document.getElementById('mobileProgressBar'),
  chat: document.getElementById('chat'),
  chatForm: document.getElementById('chatForm'),
  chatInput: document.getElementById('chatInput'),
  quickActions: document.getElementById('quickActions'),
  tutorPanel: document.getElementById('tutorPanel'),
  floatingChat: document.getElementById('floatingChat'),
  closeChat: document.getElementById('closeChat'),
  chatOverlay: document.getElementById('chatOverlay'),
  childName: document.getElementById('childName'),
  childGrade: document.getElementById('childGrade'),
  childAvatar: document.getElementById('childAvatar'),
};

function setStep(step) {
  state.step = Math.max(1, Math.min(5, step));
  els.steps.forEach((item) => {
    const itemStep = Number(item.dataset.step);
    item.classList.toggle('active', itemStep === state.step);
    item.classList.toggle('done', itemStep < state.step);
  });
  els.mobileStepNumber.textContent = String(state.step);
  els.mobileProgressBar.style.width = `${state.step * 20}%`;
}

function addMessage(role, text) {
  const box = document.createElement('div');
  box.className = `message ${role}`;
  box.innerHTML = `<p>${escapeHtml(text)}</p>`;
  els.chat.appendChild(box);
  els.chat.scrollTop = els.chat.scrollHeight;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  })[char]);
}

function clearPreviews() {
  [els.imagePreview, els.pdfPreview, els.genericPreview].forEach((el) => el.classList.add('hidden'));
  els.imagePreview.removeAttribute('src');
  els.pdfPreview.removeAttribute('src');
}

function showFile(file) {
  if (!file) return;
  state.file = file;
  clearPreviews();
  els.fileName.textContent = file.name || 'שיעורי בית';

  const url = URL.createObjectURL(file);
  if (file.type.startsWith('image/')) {
    els.imagePreview.src = url;
    els.imagePreview.classList.remove('hidden');
  } else if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
    els.pdfPreview.src = url;
    els.pdfPreview.classList.remove('hidden');
  } else {
    els.genericPreview.classList.remove('hidden');
  }

  els.uploadState.classList.add('hidden');
  els.documentState.classList.remove('hidden');
  els.identifiedCard.classList.add('hidden');
  setStep(2);
  addMessage('teacher', 'קיבלתי את הקובץ. עכשיו אזהה את המקצוע והנושא, ואז נבין יחד מה מבקשים.');
}

function openFilePicker() {
  els.fileInput.click();
}

[els.fileInput, els.cameraInput].forEach((input) => {
  input?.addEventListener('change', () => showFile(input.files?.[0]));
});

['dragenter', 'dragover'].forEach((eventName) => {
  els.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    els.dropZone.classList.add('dragover');
  });
});
['dragleave', 'drop'].forEach((eventName) => {
  els.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    els.dropZone.classList.remove('dragover');
  });
});
els.dropZone.addEventListener('drop', (event) => showFile(event.dataTransfer.files?.[0]));

els.replaceFileBtn.addEventListener('click', openFilePicker);

els.analyzeBtn.addEventListener('click', async () => {
  if (!state.file) return;
  els.analyzeBtn.disabled = true;
  els.analyzeBtn.textContent = 'מזהה...';

  // TODO(PRODUCTION): Replace this visual/demo fallback with the existing homework-analysis API.
  // The frontend intentionally does not guess a child id or expose privileged Supabase credentials.
  await new Promise((resolve) => setTimeout(resolve, 650));

  els.identifiedText.textContent = 'הקובץ מוכן לזיהוי דרך מנוע שיעורי הבית הקיים';
  els.identifiedCard.classList.remove('hidden');
  els.analyzeBtn.textContent = 'זוהה ✓';
  setStep(3);
  addMessage('teacher', 'הקובץ מוכן. בחיבור למנוע הקיים כאן יופיעו המקצוע, הנושא והשאלה שזוהתה בפועל.');
});

els.startHelpBtn.addEventListener('click', () => {
  setStep(4);
  addMessage('teacher', 'נתחיל מהבנה: קודם אסביר בקצרה מה השאלה מבקשת, ואז אשאל אותך שאלה אחת קצרה.');
  openChat();
});

els.chatForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const text = els.chatInput.value.trim();
  if (!text) return;
  addMessage('user', text);
  els.chatInput.value = '';
  setTimeout(() => addMessage('teacher', 'כאן תתחבר תשובת המורה מהמנוע הקיים. כרגע זהו שלד ה־UI החדש.'), 250);
});

els.quickActions.addEventListener('click', (event) => {
  const button = event.target.closest('button[data-message]');
  if (!button) return;
  els.chatInput.value = button.dataset.message;
  els.chatForm.requestSubmit();
});

function openChat() {
  els.tutorPanel.classList.add('open');
  els.chatOverlay.classList.add('show');
}
function closeChat() {
  els.tutorPanel.classList.remove('open');
  els.chatOverlay.classList.remove('show');
}
els.floatingChat?.addEventListener('click', openChat);
els.closeChat?.addEventListener('click', closeChat);
els.chatOverlay?.addEventListener('click', closeChat);

/**
 * Production bridge contract.
 * Call this from the auth/current-child adapter once the new frontend is connected.
 * Example: window.IAKidsHomework.setChild({ id, name, grade })
 */
window.IAKidsHomework = {
  setChild(child) {
    if (!child) return;
    state.child = child;
    if (child.name) {
      els.childName.textContent = child.name;
      els.childAvatar.textContent = child.name.trim().charAt(0) || 'י';
    }
    if (child.grade) els.childGrade.textContent = `כיתה ${child.grade}`;
  },
  getState() {
    return { ...state, file: state.file ? { name: state.file.name, type: state.file.type, size: state.file.size } : null };
  },
  setStep,
  addTeacherMessage(text) { addMessage('teacher', text); },
};

setStep(1);
