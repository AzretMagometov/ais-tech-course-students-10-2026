/* Deterministic teaching example: tokens and probabilities are illustrative. */
(() => {
  'use strict';
  const slide = document.getElementById('prediction');
  if (!slide) return;
  const output = document.getElementById('generated-text');
  const candidates = document.getElementById('candidate-list');
  const overview = document.getElementById('overview');
  const printMedia = window.matchMedia('print');
  const selectionDelay = 160;
  const nextDelay = 140;
  const repeatDelay = 600;
  const choices = [
    [' открой', ' проверь', ' найди'], ['те', ' файл', ' документ'],
    [' файл', ' документ', ' папку'], [' отч', ' данных', ' проекта'],
    ['ёта', 'ёт', 'ётов'], [',', '.', ' и'],
    [' срав', ' проверь', ' уточ'], ['ните', 'ни', 'нение'],
    [' каждое', ' одно', ' последнее'], [' знач', ' число', ' услов'],
    ['ение', 'ения', 'ений'], [' с', ' и', ' по'],
    [' исход', ' новым', ' другим'], ['ным', 'ного', 'ные'],
    [' документ', ' файл', ' текст'], ['ом', 'а', 'ами'],
    [' и', ',', '.'], [' отдельно', ' затем', ' сразу'],
    [' отмет', ' запиш', ' проверь'], ['ьте', 'ить', 'ка'],
    [' условия', ' ошибки', ' выводы'], [',', '.', ' и'],
    [' для', ' при', ' если'], [' которых', ' каждого', ' них'],
    [' не', ' уже', ' пока'], [' найден', ' указан', ' получен'],
    ['о', 'ы', 'ного'], [' подтверж', ' объяс', ' уточ'],
    ['дение', 'дения', 'дений'], ['.', ',', ' и']
  ];
  const frames = choices.map(([token, alternative, third], i) => ({
    token,
    options: i === 3
      ? [[alternative, 42], [token, 35], [third, 15], ['Остальные', 8]]
      : [[token, 52 + i % 5 * 4], [alternative, 26 - i % 5 * 2], [third, 14 - i % 5], ['Остальные', 8 - i % 5]]
  }));
  let index = 0;
  let selected = false;
  let timer = null;
  let printing = false;

  const available = () => !slide.hidden && !document.hidden && !overview.open && !printing && !printMedia.matches;
  const visibleToken = token => token.replaceAll(' ', '·');

  function stop() {
    window.clearTimeout(timer);
    timer = null;
  }

  function schedule(callback, delay) {
    stop();
    timer = window.setTimeout(() => {
      timer = null;
      if (available()) callback();
    }, delay);
  }

  function renderCandidates() {
    const frame = frames[Math.min(index, frames.length - 1)];
    candidates.replaceChildren();
    frame.options.forEach(([token, probability], rowIndex) => {
      const row = document.createElement('div');
      row.className = 'candidate-row';
      if (rowIndex === 3) row.classList.add('other');
      if (selected && token === frame.token) row.classList.add('selected');
      const label = document.createElement('b');
      label.textContent = rowIndex === 3 ? token : visibleToken(token);
      const track = document.createElement('div');
      track.className = 'candidate-track';
      const bar = document.createElement('i');
      bar.style.width = `${probability}%`;
      track.append(bar);
      const value = document.createElement('span');
      value.textContent = `${probability}%`;
      row.append(label, track, value);
      candidates.append(row);
    });
  }

  function restart() {
    index = 0;
    selected = false;
    output.replaceChildren();
    select();
  }

  function commit() {
    const previous = output.querySelector('.latest-token');
    if (previous) previous.replaceWith(document.createTextNode(previous.textContent));
    const latest = document.createElement('span');
    latest.className = 'latest-token';
    latest.textContent = frames[index].token;
    output.append(latest);
    index += 1;
    selected = false;
    if (index === frames.length) schedule(restart, repeatDelay);
    else {
      renderCandidates();
      schedule(select, nextDelay);
    }
  }

  function select() {
    selected = true;
    renderCandidates();
    schedule(commit, selectionDelay);
  }

  function synchronize() {
    if (!available()) { stop(); return; }
    if (timer !== null) return;
    if (index === frames.length) schedule(restart, repeatDelay);
    else if (selected) schedule(commit, selectionDelay);
    else select();
  }

  // Deck state remains owned by deck.js; this component watches visibility only.
  new MutationObserver(synchronize).observe(slide, { attributes: true, attributeFilter: ['hidden'] });
  new MutationObserver(synchronize).observe(overview, { attributes: true, attributeFilter: ['open'] });
  document.addEventListener('visibilitychange', synchronize);
  printMedia.addEventListener('change', synchronize);
  window.addEventListener('beforeprint', () => { printing = true; stop(); });
  window.addEventListener('afterprint', () => { printing = false; synchronize(); });
  slide.classList.add('generation-ready');
  slide.querySelector('.generation-interactive').hidden = false;
  renderCandidates();
  synchronize();
})();
