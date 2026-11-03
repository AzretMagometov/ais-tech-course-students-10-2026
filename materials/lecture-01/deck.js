/* Plain local HTML: no build step, modules, network requests or third-party runtime. */
(() => {
  'use strict';
  const slides = [...document.querySelectorAll('.slide')];
  const byId = id => document.getElementById(id);
  const overview = byId('overview');
  let current = 0;
  let touchStart = null;

  function resize() {
    const scale = Math.min(window.innerWidth / 1600, Math.max(1, window.innerHeight - 64) / 900);
    document.documentElement.style.setProperty('--scale', scale);
  }

  function show(index, updateHash = true) {
    current = Math.max(0, Math.min(slides.length - 1, index));
    slides.forEach((slide, i) => { slide.hidden = i !== current; });
    const slide = slides[current];
    byId('counter').textContent = `${String(current + 1).padStart(2, '0')} / ${slides.length}`;
    byId('progress').style.width = `${(current + 1) / slides.length * 100}%`;
    byId('previous').disabled = current === 0;
    byId('next').disabled = current === slides.length - 1;
    byId('announcement').textContent = `Слайд ${current + 1} из ${slides.length}: ${slide.dataset.title}`;
    document.title = `${current + 1}. ${slide.dataset.title} — AI Sprint × НПП АС`;
    document.querySelectorAll('#slide-list button').forEach((button, i) => {
      button.setAttribute('aria-current', String(i === current));
    });
    if (updateHash) {
      // Location hashes also work from file:// and provide copyable links to a slide.
      try { history.replaceState(null, '', `#${slide.id}`); }
      catch { if (location.hash !== `#${slide.id}`) location.hash = slide.id; }
    }
  }

  function fromHash() {
    const index = slides.findIndex(slide => `#${slide.id}` === location.hash);
    show(index < 0 ? 0 : index, false);
  }

  async function toggleFullscreen() {
    if (!document.fullscreenEnabled) return;
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch { /* Browsers may deny fullscreen without a user gesture. */ }
  }

  slides.forEach((slide, i) => {
    const item = document.createElement('li');
    const button = document.createElement('button');
    const number = document.createElement('span');
    const title = document.createElement('span');
    number.textContent = String(i + 1).padStart(2, '0');
    title.textContent = slide.dataset.title;
    button.append(number, title);
    button.addEventListener('click', () => { show(i); overview.close(); byId('overview-open').focus(); });
    item.append(button);
    byId('slide-list').append(item);
  });
  byId('previous').addEventListener('click', () => show(current - 1));
  byId('next').addEventListener('click', () => show(current + 1));
  byId('overview-open').addEventListener('click', () => {
    overview.showModal();
    const selected = overview.querySelector('[aria-current="true"]');
    selected?.focus();
    selected?.scrollIntoView({ block: 'nearest' });
  });
  byId('overview-close').addEventListener('click', () => overview.close());
  byId('fullscreen').addEventListener('click', toggleFullscreen);
  if (!document.fullscreenEnabled) byId('fullscreen').hidden = true;
  document.addEventListener('keydown', event => {
    if (overview.open || event.altKey || event.ctrlKey || event.metaKey || /INPUT|TEXTAREA|SELECT/.test(event.target.tagName) || event.target.isContentEditable) return;
    const key = event.key.toLowerCase();
    const onButton = event.target.closest('button, a');
    if ((key === ' ' || key === 'enter') && onButton) return;
    if (['arrowright', 'arrowdown', 'pagedown', ' '].includes(key)) { event.preventDefault(); show(current + 1); }
    else if (['arrowleft', 'arrowup', 'pageup', 'backspace'].includes(key)) { event.preventDefault(); show(current - 1); }
    else if (key === 'home') { event.preventDefault(); show(0); }
    else if (key === 'end') { event.preventDefault(); show(slides.length - 1); }
    else if (key === 'o' || key === 'щ') byId('overview-open').click();
    else if (key === 'f' || key === 'а') toggleFullscreen();
  });
  byId('deck').addEventListener('touchstart', event => {
    if (event.touches.length === 1) touchStart = { x: event.touches[0].clientX, y: event.touches[0].clientY };
    else touchStart = null;
  }, { passive: true });
  byId('deck').addEventListener('touchend', event => {
    if (!touchStart || !event.changedTouches.length) return;
    const dx = event.changedTouches[0].clientX - touchStart.x;
    const dy = event.changedTouches[0].clientY - touchStart.y;
    if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.5) show(current + (dx < 0 ? 1 : -1));
    touchStart = null;
  }, { passive: true });
  window.addEventListener('resize', resize);
  window.addEventListener('hashchange', fromHash);
  resize();
  fromHash();
})();
