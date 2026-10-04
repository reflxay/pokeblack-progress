'use strict';
const $ = id => document.getElementById(id);
const number = new Intl.NumberFormat('en-US');
const pct = (matched, total) => total ? matched / total * 100 : 0;
const percent = (matched, total) => `${pct(matched, total).toFixed(2)}%`;
const moduleLabel = name => name === 'main' ? 'ARM9 main' : name.startsWith('OVY_') ? `Overlay ${name.slice(4).padStart(3, '0')}` : name;
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
let data, selectedModule = 'main', page = 0, filtered = [];
const pageSize = 40;

const autoHideHeader = document.querySelector('.auto-hide-header');
if (autoHideHeader) {
  let lastScrollY = Math.max(0, window.scrollY);
  let pointerNearHeader = false;
  window.addEventListener('scroll', () => {
    const currentY = Math.max(0, window.scrollY);
    const nearTop = currentY <= autoHideHeader.offsetHeight;
    if (!nearTop && Math.abs(currentY - lastScrollY) < 6) return;
    autoHideHeader.classList.toggle('is-hidden', !nearTop && currentY > lastScrollY && !pointerNearHeader && !autoHideHeader.querySelector(':focus-visible'));
    lastScrollY = currentY;
  }, {passive: true});
  window.addEventListener('pointermove', event => {
    pointerNearHeader = event.pointerType === 'mouse' && event.clientY <= autoHideHeader.offsetHeight;
    if (pointerNearHeader) autoHideHeader.classList.remove('is-hidden');
  }, {passive: true});
  autoHideHeader.addEventListener('focusin', () => autoHideHeader.classList.remove('is-hidden'));
}

function selectModule(name) {
  selectedModule = name;
  const module = data.modules.find(m => m.name === name);
  $('module-title').textContent = moduleLabel(name);
  $('module-percent').textContent = module.code ? percent(module.matched, module.code) : 'Data only';
  $('module-bar').value = pct(module.matched, module.code);
  $('module-bytes').textContent = `${number.format(module.matched)} B`;
  $('module-total').textContent = `${number.format(module.code)} B`;
  $('module-functions').textContent = `${number.format(module.matched_functions)} / ${number.format(module.functions)}`;
  document.querySelectorAll('[data-module]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.module === name)));
}

function renderMaps() {
  const progressColor = getComputedStyle(document.documentElement).getPropertyValue('--progress-color').trim();
  for (const module of data.modules) {
    const overlay = module.name.startsWith('OVY_');
    const button = element('button', overlay ? '' : 'core-tile');
    button.type = 'button';
    button.dataset.module = module.name;
    button.setAttribute('aria-pressed', 'false');
    const completion = module.code ? percent(module.matched, module.code) : 'no tracked code';
    button.title = `${moduleLabel(module.name)} · ${completion} · ${number.format(module.functions)} functions`;
    button.setAttribute('aria-label', button.title);
    if (!module.code) button.classList.add('empty-tile');
    if (overlay) {
      button.textContent = module.name.slice(4);
      if (module.code && module.matched) {
        const lightness = 26 + pct(module.matched, module.code) * .42;
        button.style.backgroundColor = progressColor
          ? `color-mix(in srgb, ${progressColor} ${pct(module.matched, module.code)}%, #2b2d32)`
          : `hsl(var(--progress-hue, 190) 60% ${lightness}%)`;
        button.style.color = lightness > 50 ? '#08171e' : '#ecf5fa';
      }
    } else {
      button.append(element('span', '', module.name === 'main' ? 'ARM9' : module.name), element('strong', '', module.code ? completion : '—'));
    }
    button.addEventListener('click', () => selectModule(module.name));
    $(overlay ? 'overlay-map' : 'core-map').append(button);
    const option = element('option', '', moduleLabel(module.name));
    option.value = module.name;
    $('module-select').append(option);
  }
  selectModule('main');
}

function showFunction(fn) {
  const file = data.files[fn.file];
  const info = $('function-info');
  info.replaceChildren();
  for (const [label, value] of Object.entries({Function: fn.name, File: file.path, Module: moduleLabel(file.module), Address: fn.address, Size: fn.size === null ? 'Not measured for assembly labels' : `${number.format(fn.size)} bytes`, Status: fn.status === 'matched' ? 'Matching C' : 'Assembly'})) {
    info.append(element('dt', '', label), element('dd', '', value));
  }
  $('function-detail').open = true;
  $('function-detail').scrollIntoView({block: 'nearest'});
}

function renderRows() {
  const rows = document.createDocumentFragment();
  const start = page * pageSize;
  for (const fn of filtered.slice(start, start + pageSize)) {
    const file = data.files[fn.file];
    const row = element('tr');
    const name = element('td');
    const button = element('button', 'function-button', fn.name);
    button.type = 'button';
    button.addEventListener('click', () => showFunction(fn));
    name.append(button, element('span', 'file-name', file.path));
    const status = element('td');
    status.append(element('span', `status-badge ${fn.status}`, fn.status === 'matched' ? 'Matching C' : 'Assembly'));
    row.append(name, element('td', '', moduleLabel(file.module)), element('td', '', fn.address), element('td', 'size-cell', fn.size === null ? '—' : `${number.format(fn.size)} B`), status);
    rows.append(row);
  }
  $('function-rows').replaceChildren(rows);
  $('empty').hidden = filtered.length !== 0;
  $('result-count').textContent = `${number.format(filtered.length)} functions`;
  $('page-caption').textContent = filtered.length ? `${number.format(start + 1)}–${number.format(Math.min(start + pageSize, filtered.length))} of ${number.format(filtered.length)}` : '0 results';
  $('previous').disabled = page === 0;
  $('next').disabled = start + pageSize >= filtered.length;
}

function applyFilters() {
  if (!data) return;
  const query = $('search').value.trim().toLowerCase();
  const module = $('module-select').value;
  const status = $('status-select').value;
  filtered = data.functions.filter(fn => {
    const file = data.files[fn.file];
    return (!module || file.module === module) && (!status || fn.status === status) &&
      (!query || `${fn.name} ${file.path} ${fn.address}`.toLowerCase().includes(query));
  });
  const sort = $('sort-select').value;
  filtered.sort((a, b) => sort === 'size' ? (b.size ?? -1) - (a.size ?? -1) || a.name.localeCompare(b.name) : sort === 'module' ? data.files[a.file].module.localeCompare(data.files[b.file].module, undefined, {numeric: true}) || a.name.localeCompare(b.name) : a.name.localeCompare(b.name));
  page = 0;
  renderRows();
}

$('filters').addEventListener('submit', event => event.preventDefault());
$('search').addEventListener('input', applyFilters);
for (const id of ['module-select', 'status-select', 'sort-select']) $(id).addEventListener('change', applyFilters);
$('previous').addEventListener('click', () => { if (page) { page--; renderRows(); } });
$('next').addEventListener('click', () => { if ((page + 1) * pageSize < filtered.length) { page++; renderRows(); } });
$('explore-module').addEventListener('click', () => {
  if (!data) return;
  $('module-select').value = selectedModule;
  $('status-select').value = '';
  $('search').value = '';
  applyFilters();
  $('explorer').scrollIntoView();
  $('search').focus({preventScroll: true});
});

fetch('data/progress.json', {cache: 'no-cache'}).then(response => {
  if (!response.ok) throw new Error('Progress snapshot could not be loaded.');
  return response.json();
}).then(snapshot => {
  if (!snapshot.files?.length || !snapshot.modules?.length || !snapshot.functions?.length || !Number.isFinite(snapshot.code) || snapshot.code <= 0) throw new Error('The progress snapshot is incomplete.');
  data = snapshot;
  const matchedFunctions = data.functions.filter(fn => fn.status === 'matched').length;
  $('overall').textContent = pct(data.matched, data.code).toFixed(2);
  $('overall-bar').value = pct(data.matched, data.code);
  $('byte-caption').textContent = `${number.format(data.matched)} / ${number.format(data.code)} bytes`;
  $('matched-functions').textContent = number.format(matchedFunctions);
  $('function-caption').textContent = `of ${number.format(data.functions.length)} tracked functions · ${percent(matchedFunctions, data.functions.length)}`;
  const main = data.modules.find(module => module.name === 'main');
  $('arm9-percent').textContent = percent(main.matched, main.code);
  const overlays = data.modules.filter(module => module.name.startsWith('OVY_'));
  $('overlay-percent').textContent = percent(overlays.reduce((n, m) => n + m.matched, 0), overlays.reduce((n, m) => n + m.code, 0));
  $('overlay-caption').textContent = `${overlays.length} loadable modules`;
  const verified = ['arm9', 'arm7', 'rom'].every(key => data.verified?.[key] === true);
  if ($('rom-status')) {
    $('rom-status').textContent = verified ? 'BYTE-FOR-BYTE' : 'UNVERIFIED';
    $('rom-caption').textContent = verified ? 'ARM9, ARM7 & full ROM match' : 'Verification unavailable';
  }
  $('verification').textContent = `${verified ? 'Verified' : 'Unverified'} main · ${data.revision.slice(0, 8)}`;
  $('snapshot-date').textContent = `SNAPSHOT ${new Date(data.updated).toLocaleDateString('en-US', {month: 'short', day: '2-digit', year: 'numeric', timeZone: 'America/Toronto'}).toUpperCase()}`;
  renderMaps();
  applyFilters();
}).catch(error => {
  $('error').hidden = false;
  $('error').textContent = `${error.message} Please refresh the page to try again.`;
  $('verification').textContent = 'Snapshot unavailable';
  $('result-count').textContent = 'Unavailable';
});
