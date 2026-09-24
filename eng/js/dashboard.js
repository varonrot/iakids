const menuButton = document.getElementById('mobileMenu');
const nav = document.querySelector('.main-nav');

menuButton?.addEventListener('click', () => {
  nav?.classList.toggle('mobile-open');
  menuButton.setAttribute('aria-expanded', nav?.classList.contains('mobile-open') ? 'true' : 'false');
});

document.addEventListener('click', (event) => {
  if (!nav?.classList.contains('mobile-open')) return;
  const insideNav = nav.contains(event.target);
  const onButton = menuButton?.contains(event.target);
  if (!insideNav && !onButton) {
    nav.classList.remove('mobile-open');
    menuButton?.setAttribute('aria-expanded', 'false');
  }
});

document.querySelectorAll('.feature-card').forEach((card) => {
  const arrow = card.querySelector('.feature-arrow');
  const link = card.querySelector('.feature-cta');
  arrow?.addEventListener('click', () => {
    if (link?.href) window.location.href = link.href;
  });
});
