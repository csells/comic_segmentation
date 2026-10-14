/* Narrow ACBF experiment using the pinned MIT PanelView renderer. */
import { openAcbf } from './acbf.js';
import * as reader from './reader.js';
const { $, stage, state, openBook, closeBook, next, prev, setMode, toggleDirection,
  toggleThumbs, keyboardIntent, frameCurrentPanel } = reader;
const error = $('#error');
function fail(reason) {
  closeBook();
  error.textContent = 'Could not read this book: ' + (reason?.message || String(reason));
  error.hidden = false;
}
const run = action => Promise.resolve().then(action).catch(fail);
let opening = false;
async function open(blob) {
  if (opening) return;
  opening = true; error.hidden = true;
  try {
    const book = await openAcbf(blob);
    // Older saved indices did not include the page overview. Keep those records
    // intact, but start a separate resume history for this navigation sequence.
    book.resumeId = (book.resumeId || book.title) + ':page-first-v1';
    await openBook(book);
  }
  catch (e) { fail(e); }
  finally { opening = false; }
}
const file = $('#file-input'), drop = $('#dropzone');
drop.addEventListener('click', () => file.click());
drop.addEventListener('keydown', e => {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); file.click(); }
});
file.addEventListener('change', () => { if (file.files.length) open(file.files[0]); file.value = ''; });
document.addEventListener('dragover', e => e.preventDefault());
document.addEventListener('drop', e => {
  e.preventDefault(); if (e.dataTransfer.files.length) open(e.dataTransfer.files[0]);
});
$('#btn-demo').addEventListener('click', () => run(async () => {
  const response = await fetch('./order-control.cbz');
  if (!response.ok) throw Error('Sample download failed');
  await open(await response.blob());
}));
let downloading = false;
async function openSaved(entry) {
  if (downloading || opening) return;
  downloading = true;
  const status = $('#loading'); status.hidden = false;
  error.hidden = true;
  const buttons = [...document.querySelectorAll('#book-list button, #btn-demo')];
  buttons.forEach(b => { b.disabled = true; });
  try {
    status.textContent = 'Loading ' + entry.title + '…';
    const response = await fetch('./' + entry.file);
    if (!response.ok) throw Error('Book download failed: HTTP ' + response.status);
    const chunks = [], stream = response.body.getReader();
    let received = 0;
    for (;;) {
      const {done, value} = await stream.read();
      if (done) break;
      chunks.push(value); received += value.byteLength;
      status.textContent = `Loading ${entry.title} · ${Math.min(100, Math.round(received / entry.bytes * 100))}%`;
    }
    if (received !== entry.bytes) throw Error('Incomplete book download');
    await open(new Blob(chunks, {type:'application/zip'}));
  } catch (e) { fail(e); }
  finally {
    downloading = false; status.hidden = true;
    buttons.forEach(b => { b.disabled = false; });
  }
}
run(async () => {
  const response = await fetch('./catalog.json');
  if (!response.ok) throw Error('Saved-book list could not load');
  const catalog = await response.json();
  for (const entry of catalog) {
    if (!/^[a-z-]+\.cbz$/.test(entry.file) || !Number.isSafeInteger(entry.bytes) || entry.bytes <= 0)
      throw Error('Invalid saved-book entry');
    const card = document.createElement('article'); card.className = 'saved-book';
    const title = document.createElement('h3'); title.textContent = entry.title;
    const description = document.createElement('p'); description.textContent = entry.description;
    const button = document.createElement('button'); button.className = 'btn-primary';
    button.dataset.book = entry.id; button.textContent = `Read · ${(entry.bytes/1024/1024).toFixed(1)} MB`;
    button.setAttribute('aria-label', 'Read ' + entry.title);
    button.addEventListener('click', () => openSaved(entry));
    card.append(title, description, button); $('#book-list').append(card);
  }
  $('#saved-books').hidden = catalog.length === 0;
});
$('#btn-close').addEventListener('click', closeBook);
$('#btn-fs').addEventListener('click', () => run(() => document.fullscreenElement
  ? document.exitFullscreen() : $('#reader').requestFullscreen?.()));
document.querySelectorAll('#modes button').forEach(b => b.addEventListener('click', () => run(() => setMode(b.dataset.mode))));
$('#btn-direction').addEventListener('click', toggleDirection);
$('#btn-thumbs').addEventListener('click', toggleThumbs);
let suppressClickUntil = 0;
stage.addEventListener('click', e => {
  if (Date.now() < suppressClickUntil || state.mode === 'webtoon') return;
  const intent = reader.navigationIntent(e.clientX < innerWidth * .3 ? 'click-left' : 'click-right', state.readingDirection);
  run(intent === 'prev' ? prev : next);
});
let touch = null;
stage.addEventListener('touchstart', e => {
  touch = e.touches.length === 1 ? [e.touches[0].clientX, e.touches[0].clientY] : null;
}, {passive:true});
stage.addEventListener('touchend', e => {
  if (!touch) return;
  const dx = e.changedTouches[0].clientX - touch[0], dy = e.changedTouches[0].clientY - touch[1];
  touch = null;
  if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) {
    suppressClickUntil = Date.now() + 700;
    const intent = reader.swipeIntent(state.mode, dx, state.readingDirection);
    if (intent) run(intent === 'prev' ? prev : next);
  }
}, {passive:true});
stage.addEventListener('touchcancel', () => { touch = null; });
document.addEventListener('keydown', e => {
  if (!state.book) return;
  const intent = keyboardIntent(e, state.readingDirection);
  if (intent === 'next' || intent === 'prev') { e.preventDefault(); run(intent === 'prev' ? prev : next); }
  else if (['1','2','3'].includes(intent)) run(() => setMode({'1':'page','2':'webtoon','3':'guided'}[intent]));
  else if (intent === 'Escape') closeBook();
});
window.addEventListener('resize', () => { if (state.mode === 'guided') frameCurrentPanel(false); });
// Upstream background prefetch can reject outside a navigation promise.
window.addEventListener('unhandledrejection', e => { e.preventDefault(); fail(e.reason); });
window.__panelview = { state }; // Read-only use by acceptance checks.
