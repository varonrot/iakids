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
window.addEventListener('resize', () => { if (window.innerWidth > 900) setSidebar(false); });

// Core learning modes are rendered from JS while the dashboard shell is still static.
const css = document.createElement('style');
css.textContent = `
.learning-modes{margin:18px 0 16px;padding:20px;background:linear-gradient(135deg,#fff,#f6fdff 58%,#eefafb);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}
.learning-modes-head{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;margin-bottom:15px}.learning-modes-head h2{margin:0;font-size:22px}.learning-modes-head p{margin:5px 0 0;color:var(--muted);font-size:13px}.learning-modes-badge{padding:7px 10px;border-radius:999px;background:#e8fafc;color:#078fa1;font-size:11px;font-weight:800;white-space:nowrap}
.learning-mode-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.learning-mode-card{position:relative;min-height:132px;border:1px solid var(--line);border-radius:18px;padding:16px;display:flex;flex-direction:column;align-items:flex-start;text-align:right;background:#fff;color:var(--text);transition:.18s}.learning-mode-card:hover{transform:translateY(-2px);box-shadow:0 13px 28px rgba(35,91,110,.10);border-color:#bfe6ec}.learning-mode-card.learn{background:linear-gradient(145deg,#f5fdff,#e7f8ff)}.learning-mode-card.practice{background:linear-gradient(145deg,#fffcf8,#fff1e7)}.learning-mode-card.games{background:linear-gradient(145deg,#fbf9ff,#f0ecff)}.learning-mode-card.homework{background:linear-gradient(145deg,#f8fffc,#e8faf4)}.learning-mode-icon{width:46px;height:46px;display:grid;place-items:center;border-radius:14px;background:rgba(255,255,255,.86);font-size:23px;margin-bottom:11px}.learning-mode-card strong{font-size:16px;margin-bottom:3px}.learning-mode-card small{font-size:11px;color:#6d8998;line-height:1.45}.learning-mode-arrow{position:absolute;left:14px;top:14px;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:#fff;color:#128fa2;font-weight:800}
.learning-paths{margin-top:13px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.learning-path{display:flex;align-items:center;justify-content:space-between;gap:12px;border:1px solid var(--line);border-radius:14px;padding:12px 14px;background:rgba(255,255,255,.8)}.learning-path-main{display:flex;align-items:center;gap:10px}.learning-path-icon{width:38px;height:38px;display:grid;place-items:center;border-radius:11px;background:#edf9fb}.learning-path strong{display:block;font-size:13px}.learning-path small{display:block;color:var(--muted);font-size:10px}.learning-path button{border:0;background:transparent;color:#0b93a5;font-weight:800}
.mode-toast{position:fixed;left:24px;bottom:24px;z-index:60;padding:12px 15px;border-radius:13px;background:#16384a;color:white;box-shadow:0 15px 40px rgba(22,56,74,.22);opacity:0;transform:translateY(12px);pointer-events:none;transition:.2s;font-size:13px}.mode-toast.show{opacity:1;transform:translateY(0)}
@media(max-width:1180px){.learning-mode-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:700px){.learning-modes{padding:15px}.learning-modes-head{align-items:flex-start;flex-direction:column;gap:7px}.learning-mode-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.learning-mode-card{min-height:122px;padding:13px}.learning-paths{grid-template-columns:1fr}}@media(max-width:390px){.learning-mode-grid{grid-template-columns:1fr}}
`;
document.head.appendChild(css);

const statsGrid = document.querySelector('.stats-grid');
if (statsGrid && !document.querySelector('.learning-modes')) {
  const section = document.createElement('section');
  section.className = 'learning-modes';
  section.innerHTML = `
    <div class="learning-modes-head"><div><p class="eyebrow">המורה AI שלך</p><h2>איך בא לך ללמוד עכשיו?</h2><p>בחר דרך ללמוד — המורה תתאים את השיחה והפעילות למה שבחרת.</p></div><span class="learning-modes-badge">✨ הכל מתחבר לאותו AI</span></div>
    <div class="learning-mode-grid">
      <button class="learning-mode-card learn" data-mode="learn"><span class="learning-mode-arrow">←</span><span class="learning-mode-icon">👩🏻‍🏫</span><strong>למד אותי משהו</strong><small>שאל על כל נושא והמורה תלמד אותך שלב אחרי שלב.</small></button>
      <button class="learning-mode-card practice" data-mode="practice"><span class="learning-mode-arrow">←</span><span class="learning-mode-icon">✏️</span><strong>תרגול</strong><small>תרגול חכם לפי המקצוע, הנושא והרמה שלך.</small></button>
      <button class="learning-mode-card games" data-mode="games"><span class="learning-mode-arrow">←</span><span class="learning-mode-icon">🎮</span><strong>משחקי למידה</strong><small>משחקים קצרים שעוזרים לחזור על החומר בדרך אחרת.</small></button>
      <button class="learning-mode-card homework" data-mode="homework"><span class="learning-mode-arrow">←</span><span class="learning-mode-icon">📸</span><strong>שיעורי בית</strong><small>מעלים צילום או קובץ והמורה עוזרת להבין ולפתור.</small></button>
    </div>
    <div class="learning-paths">
      <div class="learning-path"><div class="learning-path-main"><span class="learning-path-icon">📚</span><div><strong>תכנית הלימודים שלי</strong><small>המקצועות והשיעורים המובנים של IAKIDS</small></div></div><button data-mode="curriculum">לצפייה ←</button></div>
      <div class="learning-path"><div class="learning-path-main"><span class="learning-path-icon">✨</span><div><strong>מה שבחרתי ללמוד</strong><small>מקצועות ונושאים שהוספת בעצמך</small></div></div><button data-mode="personal">לצפייה ←</button></div>
    </div>`;
  statsGrid.insertAdjacentElement('afterend', section);
}

// Make existing sidebar Homework route real without changing the legacy dashboard markup.
const allNavItems = [...document.querySelectorAll('.nav-item')];
const homeworkNav = allNavItems.find((item) => item.textContent.includes('שיעורי בית'));
if (homeworkNav) homeworkNav.href = './homework.html';

const nav = document.querySelector('.nav');
if (nav) {
  const practiceNav = [...nav.querySelectorAll('.nav-item')].find((item) => item.textContent.includes('תרגול'));
  if (practiceNav && !nav.querySelector('[data-v2-nav="games"]')) practiceNav.insertAdjacentHTML('afterend','<a class="nav-item" data-v2-nav="games" href="#"><span>🎮</span><span>משחקי למידה</span></a>');
  const filesNav = [...nav.querySelectorAll('.nav-item')].find((item) => item.textContent.includes('הקבצים שלי'));
  if (filesNav && !nav.querySelector('[data-v2-nav="personal"]')) filesNav.insertAdjacentHTML('afterend','<a class="nav-item" data-v2-nav="personal" href="#"><span>✨</span><span>מה שבחרתי ללמוד</span></a>');
}

const toast = document.createElement('div'); toast.className='mode-toast'; document.body.appendChild(toast); let toastTimer;
function showToast(text){toast.textContent=text;toast.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.classList.remove('show'),2400)}

document.addEventListener('click',(event)=>{
  const mode = event.target.closest('[data-mode]')?.dataset.mode;
  if(mode === 'homework') { window.location.href = './homework.html'; return; }
  if(mode){ showToast('המסך הזה יתחבר בהמשך למנוע הקיים. שיעורי הבית כבר קיבלו Workspace חדש.'); return; }
  const navItem = event.target.closest('.nav-item, .mobile-nav a');
  if(navItem){ if(navItem.getAttribute('href') === '#') event.preventDefault(); setSidebar(false); }
});
