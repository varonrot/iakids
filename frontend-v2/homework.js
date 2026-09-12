const SUPABASE_URL = 'https://bxnfzuglfwytiyaguwjj.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4bmZ6dWdsZnd5dGl5YWd1d2pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyMjk0NjUsImV4cCI6MjA4NDgwNTQ2NX0.IcmVvbboKLkJLkE31_udEtvhPl66-kmZAvmPCT_lk5o';
const TUTOR_API_BASE = 'https://iakids-ai-tutor-he.onrender.com';
const sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const state = {
  step: 1,
  file: null,
  fileUrl: null,
  child: null,
  session: null,
  analysis: null,
  storagePath: null,
  tutorSessionId: null,
  homeworkSessionId: null,
  questions: [],
  questionIndex: 0,
  answered: [],
  lastTeacherText: '',
  audio: null,
  audioUrl: null,
  history: []
};

const $ = id => document.getElementById(id);
const els = {
  fileInput: $('fileInput'), cameraInput: $('cameraInput'), dropZone: $('dropZone'),
  uploadState: $('uploadState'), imagePreview: $('imagePreview'), pdfPreview: $('pdfPreview'),
  genericPreview: $('genericPreview'), fileName: $('fileName'), replaceFileBtn: $('replaceFileBtn'),
  analyzeBtn: $('analyzeBtn'), sourceStatus: $('sourceStatus'), notebook: $('homeworkNotebook'),
  notebookStatus: $('notebookStatus'), notebookCount: $('notebookCount'),
  steps: [...document.querySelectorAll('#steps li')], mobileStepNumber: $('mobileStepNumber'),
  mobileProgressBar: $('mobileProgressBar'), flowFill: $('flowFill'),
  flowSteps: [...document.querySelectorAll('#flowSteps > div')], chat: $('chat'),
  chatForm: $('chatForm'), chatInput: $('chatInput'), quickActions: $('quickActions'),
  tutorPanel: $('tutorPanel'), floatingChat: $('floatingChat'), closeChat: $('closeChat'),
  chatOverlay: $('chatOverlay'), audioPlay: $('audioPlay'), audioStatus: $('audioStatus'),
  understandingText: $('understandingText'), childName: $('childName'), childGrade: $('childGrade'),
  childAvatar: $('childAvatar'), questionHint: $('questionHint'), overallScore: $('overallScore'),
  overallLabel: $('overallLabel'), questionProgress: $('questionProgress'),
  questionProgressLabel: $('questionProgressLabel'), currentQuestionLabel: $('currentQuestionLabel'),
  currentQuestionScore: $('currentQuestionScore'), liveStatus: $('liveStatus')
};

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
}

function setStep(step) {
  state.step = Math.max(1, Math.min(5, Number(step) || 1));
  els.steps.forEach(item => {
    const n = Number(item.dataset.step);
    item.classList.toggle('active', n === state.step);
    item.classList.toggle('done', n < state.step);
  });
  if (els.mobileStepNumber) els.mobileStepNumber.textContent = state.step;
  if (els.mobileProgressBar) els.mobileProgressBar.style.width = `${state.step * 20}%`;
  if (els.flowFill) els.flowFill.style.width = `${(state.step - 1) * 25}%`;
  els.flowSteps.forEach((item, i) => item.classList.toggle('active', i <= state.step - 1));
}

function addMessage(role, text) {
  const clean = String(text || '').trim();
  if (!clean) return;
  const box = document.createElement('div');
  box.className = `message ${role}`;
  box.innerHTML = `<p>${escapeHtml(clean)}</p>`;
  els.chat.appendChild(box);
  els.chat.scrollTop = els.chat.scrollHeight;
  state.history.push({ role: role === 'teacher' ? 'assistant' : 'user', content: clean });
  if (state.history.length > 16) state.history = state.history.slice(-16);
  if (role === 'teacher') state.lastTeacherText = clean;
}

function setLive(text) { if (els.liveStatus) els.liveStatus.textContent = text; }
function setBusy(button, busy, busyText, normalText) {
  if (!button) return;
  button.disabled = busy;
  if (busy) button.textContent = busyText;
  else button.textContent = normalText;
}

async function getAccessToken() {
  const { data, error } = await sb.auth.getSession();
  if (error) throw error;
  state.session = data?.session || null;
  return state.session?.access_token || null;
}

async function requireSession() {
  const token = await getAccessToken();
  if (token) return token;
  els.sourceStatus.textContent = 'אין חיבור פעיל. פתחו את V2 מתוך iakids.app לאחר התחברות.';
  setLive('ממתין להתחברות');
  return null;
}

async function loadCurrentChild() {
  const token = await requireSession();
  if (!token) {
    addMessage('teacher', 'כדי לעבוד עם שיעורי הבית האמיתיים צריך לפתוח את המסך מתוך החשבון המחובר ב־iakids.app.');
    return null;
  }

  const userId = state.session.user.id;
  let kidId = localStorage.getItem('active_kid_id');

  if (!kidId) {
    const { data: kids, error } = await sb
      .from('kids_profiles').select('id').eq('user_id', userId)
      .order('created_at', { ascending: true }).limit(1);
    if (error) throw error;
    kidId = kids?.[0]?.id || null;
    if (kidId) localStorage.setItem('active_kid_id', kidId);
  }
  if (!kidId) throw new Error('לא נמצא פרופיל ילד');

  const { data: kid, error } = await sb
    .from('kids_profiles')
    .select('id,user_id,child_name,age,avatar_key,gender')
    .eq('id', kidId).eq('user_id', userId).single();
  if (error) throw error;

  const name = kid.child_name || 'הילד/ה שלי';
  state.child = { ...kid, name, grade: Number(kid.age || 0) };
  els.childName.textContent = name;
  els.childAvatar.textContent = name.trim().charAt(0) || 'י';
  els.childGrade.textContent = state.child.grade ? `כיתה ${state.child.grade}` : 'כיתה';
  els.sourceStatus.textContent = 'מחובר. אפשר להעלות שיעורי בית.';
  setLive(`מחובר ל${name}`);
  addMessage('teacher', `שלום ${name} 👋 העלו את שיעורי הבית ואני אזהה את המקצוע, הנושא והשאלה ואעבוד איתכם צעד־צעד.`);
  return state.child;
}

function clearPreview() {
  [els.imagePreview, els.pdfPreview, els.genericPreview].forEach(el => el?.classList.add('hidden'));
  if (state.fileUrl) URL.revokeObjectURL(state.fileUrl);
  state.fileUrl = null;
  els.imagePreview?.removeAttribute('src');
  els.pdfPreview?.removeAttribute('src');
}

function showFile(file) {
  if (!file) return;
  state.file = file;
  state.analysis = null;
  state.questions = [];
  state.questionIndex = 0;
  state.answered = [];
  clearPreview();
  state.fileUrl = URL.createObjectURL(file);
  els.uploadState.classList.add('hidden');
  els.fileName.textContent = file.name || 'שיעורי בית';
  els.replaceFileBtn.classList.remove('hidden');
  els.analyzeBtn.disabled = !state.child;

  if (file.type?.startsWith('image/')) {
    els.imagePreview.src = state.fileUrl;
    els.imagePreview.classList.remove('hidden');
  } else if (file.type === 'application/pdf' || file.name?.toLowerCase().endsWith('.pdf')) {
    els.pdfPreview.src = state.fileUrl;
    els.pdfPreview.classList.remove('hidden');
  } else {
    els.genericPreview.classList.remove('hidden');
  }
  els.sourceStatus.textContent = state.child ? 'הקובץ מוכן לזיהוי.' : 'הקובץ מוכן; ממתין לחיבור משתמש.';
  setStep(2);
  updateQuestionUI();
}

[els.fileInput, els.cameraInput].forEach(input => input?.addEventListener('change', () => showFile(input.files?.[0])));
['dragenter', 'dragover'].forEach(name => els.dropZone?.addEventListener(name, e => {
  e.preventDefault(); els.dropZone.classList.add('dragover');
}));
['dragleave', 'drop'].forEach(name => els.dropZone?.addEventListener(name, e => {
  e.preventDefault(); els.dropZone.classList.remove('dragover');
}));
els.dropZone?.addEventListener('drop', e => showFile(e.dataTransfer.files?.[0]));
els.replaceFileBtn?.addEventListener('click', () => els.fileInput.click());

function safeFileName(name) {
  const ext = (name.match(/\.[a-zA-Z0-9]+$/) || [''])[0];
  const base = name.slice(0, name.length - ext.length)
    .replace(/[^a-zA-Z0-9_-]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '') || 'homework';
  return `${Date.now()}-${base}${ext.toLowerCase()}`;
}

async function uploadHomeworkFile(file) {
  const path = `${state.session.user.id}/${state.child.id}/${safeFileName(file.name || 'homework')}`;
  const { error } = await sb.storage.from('homework-uploads').upload(path, file, {
    cacheControl: '3600', upsert: false, contentType: file.type || undefined
  });
  if (error) throw error;
  state.storagePath = path;
  return path;
}

function normalizeAnalysis(raw) { return raw?.analysis || raw?.result || raw || {}; }

function parseQuestions(text) {
  const clean = String(text || '').replace(/\r/g, '\n').replace(/\n{3,}/g, '\n\n');
  const out = [];
  const re = /(?:^|\n)\s*(\d{1,2})[.)]\s*([^\n]+(?:\n(?!\s*\d{1,2}[.)]\s)[^\n]+){0,3})/g;
  let m;
  while ((m = re.exec(clean))) {
    const q = String(m[2] || '').replace(/\s+/g, ' ').trim();
    if (q.length > 4) out.push({ number: Number(m[1]), text: q });
  }
  if (!out.length) {
    clean.split('\n').map(s => s.trim()).filter(s => s.length > 8 && /[?？]$/.test(s))
      .slice(0, 20).forEach((q, i) => out.push({ number: i + 1, text: q }));
  }
  return out.sort((a, b) => a.number - b.number);
}

function currentQuestion() {
  return state.questions[state.questionIndex] || null;
}

function updateQuestionUI() {
  const total = state.questions.length;
  const q = currentQuestion();
  const done = state.answered.length;
  const pct = total ? Math.round(done / total * 100) : 0;
  if (els.questionProgress) els.questionProgress.textContent = `${pct}%`;
  if (els.questionProgressLabel) els.questionProgressLabel.textContent = `${done} מתוך ${total} שאלות`;
  if (els.currentQuestionLabel) els.currentQuestionLabel.textContent = q ? `שאלה ${q.number}` : 'שאלה 1';
  if (els.currentQuestionScore) els.currentQuestionScore.textContent = q && state.answered.includes(q.number) ? '100%' : '0%';
  if (els.questionHint) els.questionHint.textContent = q ? q.text : 'כתבו כאן את דרך הפתרון שלכם';
  if (els.overallScore) els.overallScore.textContent = `${pct}%`;
  if (els.overallLabel) els.overallLabel.textContent = total ? 'התקדמות לפי השאלות שנענו' : 'ממתין להתחלת עבודה';
}

async function createHomeworkSession() {
  const token = await requireSession();
  if (!token || !state.analysis || !state.child) return null;
  const a = normalizeAnalysis(state.analysis);
  const res = await fetch(`${TUTOR_API_BASE}/api/tutor/homework-session/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      kid_id: state.child.id,
      tutor_session_id: state.tutorSessionId,
      subject: a.subject || a.detected_subject || null,
      topic: a.topic || a.detected_topic || null,
      source_file_name: state.file?.name || null,
      source_file_url: null,
      source_type: state.file?.type || null,
      total_questions: state.questions.length
    })
  });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  state.homeworkSessionId = data?.id || null;
  return data;
}

async function analyzeHomework() {
  if (!state.file || !state.child) return;
  const token = await requireSession();
  if (!token) return;

  setBusy(els.analyzeBtn, true, 'מעלה ומזהה...', 'זהה שוב ✨');
  els.sourceStatus.textContent = 'מעלה את הקובץ למערכת...';
  setLive('מנתח את שיעורי הבית...');
  try {
    const path = await uploadHomeworkFile(state.file);
    els.sourceStatus.textContent = 'מזהה מקצוע, נושא ושאלות...';
    const res = await fetch(`${TUTOR_API_BASE}/api/tutor/homework-analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        kid_id: state.child.id,
        storage_path: path,
        session_id: state.tutorSessionId,
        file_name: state.file.name,
        file_type: state.file.type,
        file_size_bytes: state.file.size
      })
    });
    if (!res.ok) throw new Error(await res.text());

    const data = await res.json();
    state.analysis = data;
    state.tutorSessionId = data?.session_id || state.tutorSessionId;
    const a = normalizeAnalysis(data);
    const extracted = a.extracted_text || data?.extracted_text || '';
    state.questions = parseQuestions(extracted);
    state.questionIndex = 0;
    state.answered = [];
    await createHomeworkSession().catch(err => console.warn('homework session start', err));

    const subject = a.subject || a.detected_subject || data?.subject || data?.detected_subject || 'מקצוע';
    const topic = a.topic || a.detected_topic || data?.topic || data?.detected_topic || 'נושא';
    els.sourceStatus.textContent = `זוהה: ${subject} · ${topic}`;
    els.understandingText.textContent = 'זיהינו את החומר';
    setLive(`זוהה ${subject} · ${topic}`);
    setStep(3);
    updateQuestionUI();

    addMessage('teacher', `זיהיתי שזה שיעורי בית ב${subject}${topic && topic !== 'נושא' ? ` בנושא ${topic}` : ''}. קודם נבין מה השאלה מבקשת, ואז נעבוד עליה יחד.`);
    const q = currentQuestion();
    if (q) addMessage('teacher', `נתחיל בשאלה ${q.number}: ${q.text}`);
  } catch (err) {
    console.error(err);
    els.sourceStatus.textContent = 'לא הצלחתי לנתח את הקובץ. נסו שוב.';
    setLive('שגיאה בניתוח');
    addMessage('teacher', 'לא הצלחתי לנתח את הקובץ כרגע. אפשר לנסות שוב או להחליף קובץ.');
  } finally {
    setBusy(els.analyzeBtn, false, '', 'זהה שוב ✨');
  }
}
els.analyzeBtn?.addEventListener('click', analyzeHomework);

const NOTE_KEY = () => `iakids-v2-homework-notebook-${state.child?.id || 'guest'}`;
function loadNotebook() {
  try {
    const saved = localStorage.getItem(NOTE_KEY());
    if (saved) els.notebook.innerHTML = saved;
  } catch {}
  saveNotebook();
}
function saveNotebook() {
  const text = els.notebook.innerText.trim();
  try { localStorage.setItem(NOTE_KEY(), els.notebook.innerHTML); } catch {}
  els.notebookStatus.textContent = 'נשמר אוטומטית';
  els.notebookCount.textContent = `${text.length} תווים`;
  if (text.length > 0 && state.step < 4) setStep(4);
}
els.notebook?.addEventListener('input', () => {
  els.notebookStatus.textContent = 'שומר...';
  clearTimeout(saveNotebook.timer);
  saveNotebook.timer = setTimeout(saveNotebook, 250);
});

function openChat() { els.tutorPanel.classList.add('open'); els.chatOverlay.classList.add('show'); }
function closeChat() { els.tutorPanel.classList.remove('open'); els.chatOverlay.classList.remove('show'); }
els.floatingChat?.addEventListener('click', openChat);
els.closeChat?.addEventListener('click', closeChat);
els.chatOverlay?.addEventListener('click', closeChat);

async function sendHomeworkTurn(answer) {
  const clean = String(answer || '').trim();
  if (!clean) return;
  addMessage('user', clean);
  if (!state.analysis) { addMessage('teacher', 'קודם צריך להעלות ולזהות את שיעורי הבית.'); return; }

  const token = await requireSession();
  if (!token) return;
  const q = currentQuestion() || { number: state.questionIndex + 1, text: 'השאלה הנוכחית' };
  const next = state.questions[state.questionIndex + 1] || null;
  setLive('המורה חושבת...');
  els.chatInput.disabled = true;
  try {
    const a = normalizeAnalysis(state.analysis);
    const res = await fetch(`${TUTOR_API_BASE}/api/tutor/homework-turn`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        kid_id: state.child.id,
        current_question_number: q.number || state.questionIndex + 1,
        current_question: q.text || '',
        answer: clean,
        source_text: a.extracted_text || state.analysis?.extracted_text || '',
        next_question_number: next?.number || null,
        next_question: next?.text || null,
        session_id: state.tutorSessionId,
        homework_session_id: state.homeworkSessionId,
        progress_context: `answered ${state.answered.length} of ${state.questions.length}`
      })
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    const reply = data?.reply || data?.teacher_response || data?.message || data?.feedback || 'בואו נמשיך יחד.';
    addMessage('teacher', reply);

    const sufficient = Boolean(data?.answer_sufficient || data?.sufficient || data?.is_correct);
    if (sufficient) {
      if (!state.answered.includes(q.number)) state.answered.push(q.number);
      if (next) {
        state.questionIndex += 1;
        setStep(4);
        addMessage('teacher', `יפה. עכשיו נעבור לשאלה ${next.number}: ${next.text}`);
      } else {
        setStep(5);
        els.understandingText.textContent = 'סיימנו את הדף';
        addMessage('teacher', 'סיימנו את השאלות. עכשיו אפשר לבדוק יחד את הניסוח הסופי.');
      }
    } else {
      setStep(4);
      els.understandingText.textContent = 'עובדים על השאלה';
    }
    updateQuestionUI();
    setLive('המורה מחוברת בזמן אמת');
  } catch (err) {
    console.error(err);
    addMessage('teacher', 'הייתה תקלה בחיבור למורה. נסו שוב בעוד רגע.');
    setLive('שגיאת חיבור');
  } finally {
    els.chatInput.disabled = false;
    els.chatInput.focus();
  }
}

async function askHomeworkCoach(message) {
  const clean = String(message || '').trim();
  if (!clean) return;
  addMessage('user', clean);
  if (!state.analysis) { addMessage('teacher', 'קודם צריך להעלות ולזהות את שיעורי הבית.'); return; }
  const token = await requireSession();
  if (!token) return;
  const q = currentQuestion();
  const a = normalizeAnalysis(state.analysis);
  setLive('המורה מכינה עזרה...');
  try {
    const res = await fetch(`${TUTOR_API_BASE}/api/tutor/homework-coach`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        kid_id: state.child.id,
        source_text: a.extracted_text || state.analysis?.extracted_text || '',
        current_question: q?.text || '',
        message: clean,
        history: state.history.slice(-10)
      })
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    addMessage('teacher', data?.reply || data?.teacher_response || data?.message || 'בואו נעבוד על זה יחד.');
    setStep(Math.max(state.step, 3));
    setLive('המורה מחוברת בזמן אמת');
  } catch (err) {
    console.error(err);
    addMessage('teacher', 'לא הצלחתי להכין את העזרה כרגע. נסו שוב בעוד רגע.');
    setLive('שגיאת חיבור');
  }
}

els.chatForm?.addEventListener('submit', e => {
  e.preventDefault();
  const text = els.chatInput.value;
  els.chatInput.value = '';
  sendHomeworkTurn(text);
});
els.quickActions?.addEventListener('click', e => {
  const button = e.target.closest('button[data-message]');
  if (!button) return;
  askHomeworkCoach(button.dataset.message);
  if (window.innerWidth <= 1000) openChat();
});

async function playTeacherTTS() {
  const text = state.lastTeacherText.trim();
  if (!text) { els.audioStatus.textContent = 'אין עדיין טקסט להקראה'; return; }
  const token = await requireSession();
  if (!token) return;
  try {
    if (state.audio && !state.audio.paused) {
      state.audio.pause();
      els.audioPlay.textContent = '▶';
      return;
    }
    els.audioStatus.textContent = 'מכין הקראה...';
    els.audioPlay.disabled = true;
    const res = await fetch(`${TUTOR_API_BASE}/api/tutor/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text, session_id: state.tutorSessionId })
    });
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    if (state.audioUrl) URL.revokeObjectURL(state.audioUrl);
    state.audioUrl = URL.createObjectURL(blob);
    state.audio = new Audio(state.audioUrl);
    state.audio.onplay = () => { els.audioPlay.textContent = '⏸'; els.audioStatus.textContent = 'מקריא...'; };
    state.audio.onended = () => { els.audioPlay.textContent = '▶'; els.audioStatus.textContent = 'ההקראה הסתיימה'; };
    state.audio.onerror = () => { els.audioPlay.textContent = '▶'; els.audioStatus.textContent = 'שגיאה בהקראה'; };
    await state.audio.play();
  } catch (err) {
    console.error(err);
    els.audioStatus.textContent = 'לא הצלחתי להפעיל הקראה';
  } finally {
    els.audioPlay.disabled = false;
  }
}
els.audioPlay?.addEventListener('click', playTeacherTTS);

window.IAKidsHomework = {
  getState() {
    return {
      step: state.step,
      child: state.child,
      analysis: state.analysis,
      homeworkSessionId: state.homeworkSessionId,
      questionIndex: state.questionIndex,
      questions: state.questions,
      answered: state.answered,
      file: state.file ? { name: state.file.name, type: state.file.type, size: state.file.size } : null
    };
  },
  setStep, analyzeHomework, sendHomeworkTurn, askHomeworkCoach, playTeacherTTS
};

(async function init() {
  setStep(1);
  updateQuestionUI();
  try {
    await loadCurrentChild();
    loadNotebook();
  } catch (err) {
    console.error(err);
    els.sourceStatus.textContent = 'לא הצלחתי לטעון את פרופיל הילד.';
    setLive('שגיאה בטעינת משתמש');
    addMessage('teacher', 'לא הצלחתי לטעון את פרופיל הילד. ודאו שאתם מחוברים לחשבון.');
  }
})();