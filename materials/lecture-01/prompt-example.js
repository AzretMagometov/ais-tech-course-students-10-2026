/* Local, temporary emphasis links each legend button to one prompt fragment. */
(() => {
  'use strict';
  const slide = document.getElementById('prompt-example');
  if (!slide) return;
  const overview = document.getElementById('overview');
  const buttons = [...slide.querySelectorAll('.prompt-legend button')];
  const printMedia = window.matchMedia('print');
  let timer = null;
  let highlighted = null;

  function clear() {
    window.clearTimeout(timer);
    timer = null;
    highlighted?.classList.remove('is-highlighted');
    highlighted = null;
  }

  buttons.forEach(button => {
    const target = document.getElementById(button.dataset.promptTarget);
    if (!target || !slide.contains(target)) return;
    button.disabled = false;
    button.addEventListener('click', () => {
      clear();
      if (slide.hidden || document.hidden || overview.open || printMedia.matches) return;
      // Restart CSS animation even when the same legend entry is pressed again.
      void target.offsetWidth;
      highlighted = target;
      target.classList.add('is-highlighted');
      timer = window.setTimeout(clear, 1050);
    });
  });
  new MutationObserver(() => { if (slide.hidden) clear(); }).observe(slide, { attributes: true, attributeFilter: ['hidden'] });
  new MutationObserver(() => { if (overview.open) clear(); }).observe(overview, { attributes: true, attributeFilter: ['open'] });
  document.addEventListener('visibilitychange', () => { if (document.hidden) clear(); });
  window.addEventListener('beforeprint', clear);
  printMedia.addEventListener('change', () => { if (printMedia.matches) clear(); });
})();
