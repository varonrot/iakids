const sidebar = document.getElementById('sidebar');
const menuBtn = document.getElementById('menuBtn');
const overlay = document.getElementById('overlay');

function setSidebar(open) {
  sidebar?.classList.toggle('open', open);
  overlay?.classList.toggle('show', open);
  document.body.style.overflow = open ? 'hidden' : '';
}

menuBtn?.addEventListener('click', () => setSidebar(true));
overlay?.addEventListener('click', () => setSidebar(false));

window.addEventListener('resize', () => {
  if (window.innerWidth > 900) setSidebar(false);
});

document.querySelectorAll('.nav-item, .mobile-nav a').forEach((item) => {
  item.addEventListener('click', (event) => {
    if (item.getAttribute('href') === '#') event.preventDefault();
    setSidebar(false);
  });
});

/* --------------------------------------------------------------------------
   Learning modes hub
   Keeps the dashboard focused on the core IAKIDS experience: the child talks
   with AI, chooses how to learn, and can switch between built-in and personal
   learning paths. This is UI-only for now; backend routes will be connected
   later.
---------------------------------------------------------------------------- */

const learningModesStyles = document.createElement('style');
learningModesStyles.textContent = `
  .learning-modes{
    margin:18px 0 16px;
    padding:20px;
    background:linear-gradient(135deg,#ffffff 0%,#f6fdff 58%,#eefafb 100%);
    border:1px solid var(--line);
    border-radius:var(--radius);
    box-shadow:var(--shadow);
  }
  .learning-modes-head{
    display:flex;
    align-items:flex-end;
    justify-content:space-between;
    gap:18px;
    margin-bottom:15px;
  }
  .learning-modes-head h2{margin:0;font-size:22px;line-height:1.15}
  .learning-modes-head p{margin:5px 0 0;color:var(--muted);font-size:13px}
  .learning-modes-badge{
    display:inline-flex;
    align-items:center;
    gap:6px;
    padding:7px 10px;
    border-radius:999px;
    background:#e8fafc;
    color:#078fa1;
    font-size:11px;
    font-weight:800;
    white-space:nowrap;
  }
  .learning-mode-grid{
    display:grid;
    grid-template-columns:repeat(4,minmax(0,1fr));
    gap:12px;
  }
  .learning-mode-card{
    position:relative;
    min-height:132px;
    border:1px solid var(--line);
    border-radius:18px;
    padding:16px;
    display:flex;
    flex-direction:column;
    align-items:flex-start;
    text-align:right;
    background:#fff;
    color:var(--text);
    overflow:hidden;
    transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease;
  }
  .learning-mode-card:hover{
    transform:translateY(-2px);
    box-shadow:0 13px 28px rgba(35,91,110,.10);
    border-color:#bfe6ec;
  }
  .learning-mode-card::after{
    content:"";
    position:absolute;
    width:110px;
    height:110px;
    left:-38px;
    bottom:-52px;
    border-radius:50%;
    background:rgba(255,255,255,.52);
  }
  .learning-mode-card.learn{background:linear-gradient(145deg,#f5fdff,#e7f8ff)}
  .learning-mode-card.practice{background:linear-gradient(145deg,#fffcf8,#fff1e7)}
  .learning-mode-card.games{background:linear-gradient(145deg,#fbf9ff,#f0ecff)}
  .learning-mode-card.homework{background:linear-gradient(145deg,#f8fffc,#e8faf4)}
  .learning-mode-icon{
    width:46px;
    height:46px;
    display:grid;
    place-items:center;
    border-radius:14px;
    background:rgba(255,255,255,.82);
    box-shadow:0 5px 14px rgba(43,91,108,.06);
    font-size:23px;
    margin-bottom:11px;
  }
  .learning-mode-card strong{font-size:16px;margin-bottom:3px;z-index:1}
  .learning-mode-card small{font-size:11px;color:#6d8998;line-height:1.45;z-index:1}
  .learning-mode-arrow{
    position:absolute;
    left:14px;
    top:14px;
    width:28px;
    height:28px;
    border-radius:50%;
    display:grid;
    place-items:center;
    background:rgba(255,255,255,.88);
    color:#128fa2;
    font-weight:800;
  }
  .learning-paths{
    margin-top:13px;
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:10px;
  }
  .learning-path{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    border:1px solid var(--line);
    border-radius:14px;
    padding:12px 14px;
    background:rgba(255,255,255,.80);
  }
  .learning-path-main{display:flex;align-items:center;gap:10px;min-width:0}
  .learning-path-icon{
    width:38px;
    height:38px;
    flex:0 0 38px;
    display:grid;
    place-items:center;
    border-radius:11px;
    background:#edf9fb;
    font-size:18px;
  }
  .learning-path strong{display:block;font-size:13px}
  .learning-path small{display:block;color:var(--muted);font-size:10px;margin-top:1px}
  .learning-path button{
    border:0;
    background:transparent;
    color:#0b93a5;
    font-weight:800;
    white-space:nowrap;
  }
  .mode-toast{
    position:fixed;
    left:24px;
    bottom:24px;
    z-index:60;
    max-width:330px;
    padding:12px 15px;
    border-radius:13px;
    background:#16384a;
    color:white;
    box-shadow:0 15px 40px rgba(22,56,74,.22);
    opacity:0;
    transform:translateY(12px);
    pointer-events:none;
    transition:.2s ease;
    font-size:13px;
  }
  .mode-toast.show{opacity:1;transform:translateY(0)}

  @media(max-width:1180px){
    .learning-mode-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  }
  @media(max-width:700px){
    .learning-modes{padding:15px;margin-top:12px}
    .learning-modes-head{align-items:flex-start;flex-direction:column;gap:7px}
    .learning-mode-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
    .learning-mode-card{min-height:125px;padding:13px}
    .learning-mode-icon{width:40px;height:40px;font-size:20px}
    .learning-mode-card strong{font-size:14px}
    .learning-mode-card small{font-size:10px}
    .learning-paths{grid-template-columns:1fr}
    .mode-toast{left:12px;right:12px;bottom:82px;max-width:none}
  }
  @media(max-width:390px){
    .learning-mode-grid{grid-template-columns:1fr}
    .learning-mode-card{min-height:104px}
  }
`;
document.head.appendChild(learningModesStyles);

const statsGrid = document.querySelector('.stats-grid');
if (statsGrid && !document.querySelector('.learning-modes')) {
  const modesSection = document.createElement('section');
  modesSection.className = 'learning-modes';
  modesSection.setAttribute('aria-labelledby', 'learningModesTitle');
  modesSection.innerHTML = `
    <div class="learning-modes-head">
      <div>
        <p class="eyebrow">המורה AI שלך</p>
        <h2 id="learningModesTitle">איך בא לך ללמוד עכשיו?</h2>
        <p>בחר דרך ללמוד — המורה תתאים את השיחה והפעילות למה שבחרת.</p>
      </div>
      <span class="learning-modes-badge">✨ הכל מתחבר לאותו AI</span>
    </div>

    <div class="learning-mode-grid">
      <button class="learning-mode-card learn" type="button" data-mode="למד אותי משהו">
        <span class="learning-mode-arrow">←</span>
        <span class="learning-mode-icon">👩🏻‍🏫</span>
        <strong>למד אותי משהו</strong>
        <small>שאל על כל נושא והמורה תלמד אותך שלב אחרי שלב.</small>
      </button>

      <button class="learning-mode-card practice" type="button" data-mode="תרגול">
        <span class="learning-mode-arrow">←</span>
        <span class="learning-mode-icon">✏️</span>
        <strong>תרגול</strong>
        <small>תרגול חכם לפי המקצוע, הנושא והרמה שלך.</small>
      </button>

      <button class="learning-mode-card games" type="button" data-mode="משחקי למידה">
        <span class="learning-mode-arrow">←</span>
        <span class="learning-mode-icon">🎮</span>
        <strong>משחקי למידה</strong>
        <small>משחקים קצרים שעוזרים לחזור על החומר בדרך אחרת.</small>
      </button>

      <button class="learning-mode-card homework" type="button" data-mode="שיעורי בית">
        <span class="learning-mode-arrow">←</span>
        <span class="learning-mode-icon">📸</span>
        <strong>שיעורי בית</strong>
        <small>מעלים צילום או קובץ והמורה עוזרת להבין ולפתור.</small>
      </button>
    </div>

    <div class="learning-paths">
      <div class="learning-path">
        <div class="learning-path-main">
          <span class="learning-path-icon">📚</span>
          <div><strong>תכנית הלימודים שלי</strong><small>המקצועות והשיעורים המובנים של IAKIDS</small></div>
        </div>
        <button type="button" data-mode="תכנית הלימודים">לצפייה ←</button>
      </div>

      <div class="learning-path">
        <div class="learning-path-main">
          <span class="learning-path-icon">✨</span>
          <div><strong>מה שבחרתי ללמוד</strong><small>מקצועות ונושאים שהוספת בעצמך</small></div>
        </div>
        <button type="button" data-mode="המקצועות האישיים">לצפייה ←</button>
      </div>
    </div>
  `;
  statsGrid.insertAdjacentElement('afterend', modesSection);
}

// Add the two missing core destinations to the desktop sidebar without changing
// the legacy markup yet.
const nav = document.querySelector('.nav');
if (nav) {
  const practiceNav = [...nav.querySelectorAll('.nav-item')].find((item) => item.textContent.includes('תרגול'));
  if (practiceNav && !nav.querySelector('[data-v2-nav="games"]')) {
    practiceNav.insertAdjacentHTML('afterend', '<a class="nav-item" data-v2-nav="games" href="#"><span>🎮</span><span>משחקי למידה</span></a>');
  }
  const filesNav = [...nav.querySelectorAll('.nav-item')].find((item) => item.textContent.includes('הקבצים שלי'));
  if (filesNav && !nav.querySelector('[data-v2-nav="personal"]')) {
    filesNav.insertAdjacentHTML('afterend', '<a class="nav-item" data-v2-nav="personal" href="#"><span>✨</span><span>מה שבחרתי ללמוד</span></a>');
  }
}

const toast = document.createElement('div');
toast.className = 'mode-toast';
toast.setAttribute('role', 'status');
document.body.appendChild(toast);
let toastTimer;

function showModeToast(label) {
  toast.textContent = `${label} — הכניסה מוכנה בשלד החדש. בשלב הבא נחבר אותה למסך העבודה ולנתונים האמיתיים.`;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
}

document.addEventListener('click', (event) => {
  const modeTarget = event.target.closest('[data-mode]');
  if (modeTarget) {
    showModeToast(modeTarget.dataset.mode);
    return;
  }

  const newNavItem = event.target.closest('[data-v2-nav]');
  if (newNavItem) {
    event.preventDefault();
    showModeToast(newNavItem.textContent.trim());
    setSidebar(false);
  }
});
