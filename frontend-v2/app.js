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
