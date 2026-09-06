from pathlib import Path

path = Path('he/index.html')
text = path.read_text(encoding='utf-8')
marker = 'IAKIDS_HOME_FEATURE_POPUPS_V1'

if marker in text:
    print('Patch already applied')
    raise SystemExit(0)

css = r'''

/* =====================================================
   IAKIDS_HOME_FEATURE_POPUPS_V1
===================================================== */
@media (min-width:769px){
  .home-hero{
    background-position:center top !important;
  }
}

.home-feature-card{
  cursor:pointer;
  outline:none;
}

.home-feature-card::after{
  content:"פרטים +";
  position:absolute;
  left:15px;
  bottom:11px;
  padding:4px 9px;
  border:1px solid rgba(38,102,173,.10);
  border-radius:999px;
  background:rgba(255,255,255,.72);
  color:#2b6fae;
  font-size:10px;
  font-weight:900;
  opacity:.78;
  transition:opacity .2s ease, transform .2s ease, background .2s ease;
}

.home-feature-card:hover::after,
.home-feature-card:focus-visible::after{
  opacity:1;
  transform:translateY(-1px);
  background:#fff;
}

.home-feature-card:focus-visible{
  box-shadow:0 0 0 4px rgba(57,145,231,.20),0 22px 50px rgba(36,81,130,.16) !important;
}

.hero-feature-modal[hidden]{display:none !important;}
.hero-feature-modal{
  position:fixed;
  inset:0;
  z-index:10000;
  display:grid;
  place-items:center;
  padding:22px;
  direction:rtl;
}
.hero-feature-modal__backdrop{
  position:absolute;
  inset:0;
  background:rgba(13,36,65,.50);
  backdrop-filter:blur(8px);
  -webkit-backdrop-filter:blur(8px);
}
.hero-feature-modal__dialog{
  position:relative;
  width:min(700px,100%);
  max-height:min(720px,calc(100vh - 44px));
  overflow:auto;
  padding:34px;
  border:1px solid rgba(255,255,255,.88);
  border-radius:32px;
  background:radial-gradient(circle at 90% 0%,rgba(93,190,255,.16),transparent 32%),radial-gradient(circle at 0% 100%,rgba(255,207,71,.15),transparent 30%),#fff;
  box-shadow:0 35px 100px rgba(17,51,89,.30);
  color:#173965;
}
.hero-feature-modal__close{
  position:absolute;
  top:16px;
  left:16px;
  width:42px;
  height:42px;
  display:grid;
  place-items:center;
  border:1px solid rgba(23,57,101,.10);
  border-radius:14px;
  background:#f6faff;
  color:#274d79;
  font-size:24px;
  line-height:1;
  cursor:pointer;
}
.hero-feature-modal__top{
  display:grid;
  grid-template-columns:120px 1fr;
  align-items:center;
  gap:24px;
  padding-left:38px;
}
.hero-feature-modal__image{
  width:120px;
  height:120px;
  display:grid;
  place-items:center;
  overflow:hidden;
  border-radius:27px;
  background:linear-gradient(145deg,#eef8ff,#fff8e7);
  box-shadow:inset 0 0 0 1px rgba(38,87,140,.06),0 14px 34px rgba(33,81,132,.10);
}
.hero-feature-modal__image img{width:112px;height:112px;object-fit:contain;display:block;}
.hero-feature-modal__eyebrow{
  display:inline-flex;
  align-items:center;
  gap:6px;
  width:max-content;
  margin-bottom:8px;
  padding:6px 11px;
  border-radius:999px;
  background:#edf7ff;
  color:#2d79bd;
  font-size:11px;
  font-weight:900;
}
.hero-feature-modal h2{margin:0 0 8px;color:#173965;font-size:30px;font-weight:950;line-height:1.15;}
.hero-feature-modal__lead{margin:0;color:#5b708b;font-size:16px;line-height:1.7;}
.hero-feature-modal__points{display:grid;grid-template-columns:1fr;gap:10px;margin:25px 0 0;}
.hero-feature-modal__point{
  display:grid;
  grid-template-columns:42px 1fr;
  align-items:center;
  gap:12px;
  padding:13px 14px;
  border:1px solid rgba(31,78,126,.07);
  border-radius:18px;
  background:rgba(248,251,255,.86);
}
.hero-feature-modal__point-icon{
  width:42px;
  height:42px;
  display:grid;
  place-items:center;
  border-radius:13px;
  background:#fff;
  font-size:20px;
  box-shadow:0 7px 20px rgba(35,79,126,.08);
}
.hero-feature-modal__point strong{display:block;color:#284c76;font-size:14px;font-weight:900;}
.hero-feature-modal__footer{
  margin-top:23px;
  padding-top:18px;
  border-top:1px solid rgba(31,77,124,.08);
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:14px;
}
.hero-feature-modal__footer span{color:#718197;font-size:12px;font-weight:700;}
.hero-feature-modal__cta{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  gap:7px;
  padding:12px 18px;
  border:1px solid #e3aa16;
  border-radius:999px;
  background:linear-gradient(135deg,#ffdc63,#ffc32a);
  color:#173965;
  text-decoration:none;
  font-size:13px;
  font-weight:950;
  box-shadow:0 12px 28px rgba(235,174,22,.23);
}
body.hero-feature-modal-open{overflow:hidden;}

@media(max-width:650px){
  .home-feature-card::after{left:11px;bottom:8px;}
  .hero-feature-modal{padding:12px;}
  .hero-feature-modal__dialog{padding:25px 20px 22px;border-radius:25px;}
  .hero-feature-modal__top{grid-template-columns:80px 1fr;gap:15px;padding-left:28px;}
  .hero-feature-modal__image{width:80px;height:80px;border-radius:20px;}
  .hero-feature-modal__image img{width:76px;height:76px;}
  .hero-feature-modal h2{font-size:23px;}
  .hero-feature-modal__lead{font-size:14px;}
  .hero-feature-modal__footer{align-items:stretch;flex-direction:column;}
  .hero-feature-modal__cta{width:100%;}
}
'''

if '</style>' not in text:
    raise RuntimeError('Missing </style>')
text = text.replace('</style>', css + '\n</style>', 1)

js = r'''
<script>
/* IAKIDS_HOME_FEATURE_POPUPS_V1 */
document.addEventListener('DOMContentLoaded', () => {
  const cards = Array.from(document.querySelectorAll('.home-hero-features .home-feature-card'));
  if (!cards.length) return;

  const details = [
    {
      title:'לימוד מותאם לכיתות א׳–ו׳',
      image:'/assets/home/feature-kids.png',
      lead:'ההסברים והתרגול מותאמים לגיל, לרמת הלימוד ולקצב של הילד — כדי שהלמידה תהיה ברורה ולא מתסכלת.',
      points:[['🎓','הסברים בשפה שמתאימה לגיל'],['🎯','תרגול בקצב אישי ובהדרגה'],['📚','למידה שמותאמת לרמת הילד']]
    },
    {
      title:'רובוט אישי שמלווה את הילד',
      image:'/assets/home/feature-robot.png',
      lead:'מלווה לימודי אישי שעוזר להבין את החומר, שואל שאלות ומכוון את הילד להתקדם בעצמו — לא רק נותן תשובה.',
      points:[['💡','מסביר שלב אחר שלב בצורה ברורה'],['🧠','נותן רמזים ומעודד חשיבה עצמאית'],['💬','זמין ללמידה, תרגול ושאלות בכל זמן']]
    },
    {
      title:'רואים את ההתקדמות לאורך הדרך',
      image:'/assets/home/feature-progress.png',
      lead:'הילד וההורים יכולים לקבל תמונה ברורה יותר של ההתקדמות, ההישגים והנושאים שכדאי להמשיך לחזק.',
      points:[['🏆','רואים הישגים והתקדמות'],['📈','מזהים נושאים שמתחזקים לאורך הדרך'],['👨‍👩‍👧','להורים יש תמונה ברורה יותר של הלמידה']]
    },
    {
      title:'למידה פעילה ומהנה',
      image:'/assets/home/feature-fun.png',
      lead:'הלמידה משלבת תרגול אינטראקטיבי ופעילויות שמחזיקות את הילד מעורב ועוזרות להפוך את התרגול לחוויה חיובית.',
      points:[['🎮','תרגול אינטראקטיבי ומשחקי למידה'],['✨','חוויית למידה נעימה ומעודדת'],['⭐','הצלחות קטנות שבונות ביטחון ומוטיבציה']]
    }
  ];

  const modal = document.createElement('div');
  modal.className = 'hero-feature-modal';
  modal.hidden = true;
  modal.innerHTML = `
    <div class="hero-feature-modal__backdrop" data-close-feature-modal></div>
    <section class="hero-feature-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="heroFeatureModalTitle">
      <button class="hero-feature-modal__close" type="button" aria-label="סגירה" data-close-feature-modal>×</button>
      <div class="hero-feature-modal__top">
        <div class="hero-feature-modal__image"><img src="" alt=""></div>
        <div>
          <span class="hero-feature-modal__eyebrow">✨ קצת יותר על זה</span>
          <h2 id="heroFeatureModalTitle"></h2>
          <p class="hero-feature-modal__lead"></p>
        </div>
      </div>
      <div class="hero-feature-modal__points"></div>
      <div class="hero-feature-modal__footer">
        <span>רוצים לראות איך זה עובד בפועל?</span>
        <a class="hero-feature-modal__cta" href="/he/onboarding/">מתחילים ללמוד בחינם 🚀</a>
      </div>
    </section>`;
  document.body.appendChild(modal);

  const title = modal.querySelector('#heroFeatureModalTitle');
  const lead = modal.querySelector('.hero-feature-modal__lead');
  const image = modal.querySelector('.hero-feature-modal__image img');
  const points = modal.querySelector('.hero-feature-modal__points');
  const closeButton = modal.querySelector('.hero-feature-modal__close');
  let lastFocused = null;

  const openModal = (index, card) => {
    const item = details[index];
    if (!item) return;
    lastFocused = card;
    title.textContent = item.title;
    lead.textContent = item.lead;
    image.src = item.image;
    image.alt = item.title;
    points.innerHTML = item.points.map(([icon,label]) => `
      <div class="hero-feature-modal__point">
        <span class="hero-feature-modal__point-icon">${icon}</span>
        <strong>${label}</strong>
      </div>`).join('');
    modal.hidden = false;
    document.body.classList.add('hero-feature-modal-open');
    requestAnimationFrame(() => closeButton.focus());
  };

  const closeModal = () => {
    if (modal.hidden) return;
    modal.hidden = true;
    document.body.classList.remove('hero-feature-modal-open');
    if (lastFocused) lastFocused.focus();
  };

  cards.forEach((card,index) => {
    card.setAttribute('role','button');
    card.setAttribute('tabindex','0');
    card.setAttribute('aria-haspopup','dialog');
    card.setAttribute('aria-label',`${card.querySelector('strong')?.textContent?.trim() || 'מידע נוסף'} – לחצו להסבר`);
    card.addEventListener('click',() => openModal(index,card));
    card.addEventListener('keydown',event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openModal(index,card);
      }
    });
  });

  modal.querySelectorAll('[data-close-feature-modal]').forEach(el => el.addEventListener('click',closeModal));
  document.addEventListener('keydown',event => {
    if (event.key === 'Escape' && !modal.hidden) closeModal();
  });
});
</script>
'''

if '</body>' not in text:
    raise RuntimeError('Missing </body>')
text = text.replace('</body>', js + '\n</body>', 1)
path.write_text(text, encoding='utf-8')
print('Hebrew homepage patched successfully')
