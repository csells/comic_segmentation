"""Assemble pinned PanelView with a narrow experimental ACBF entry point.

Run only in the disposable candidate VM. Every build has a new output directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

parser=argparse.ArgumentParser()
parser.add_argument('upstream',type=Path)
parser.add_argument('fixtures',type=Path)
parser.add_argument('output',type=Path)
parser.add_argument('--saved-books',type=Path,help='Directory containing gemini/local replay output directories')
a=parser.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
for name in ['reader.js','comicsol.js','detect.js','zip.js','style.css','LICENSE']:
    shutil.copyfile(a.upstream/name,a.output/name)
for name in ['acbf.js','main.js','guided_sequence.js','visible_thumbnails.js','test-acbf.html','test-thumbnails.html']:
    shutil.copyfile(Path(__file__).parent/name,a.output/name)
# Keep the pinned renderer patch explicit and fail if its integration points drift.
reader=(a.output/'reader.js').read_text()
patches={
    'import { IMG_RE, detectPanels }': 'import { guidedSteps } from "./guided_sequence.js";\nimport { createThumbnailStrip } from "./visible_thumbnails.js";\nimport { IMG_RE, detectPanels }',
    'const thumbsEl = $("#thumbs");': 'const thumbsEl = $("#thumbs");\nconst thumbnailStrip = createThumbnailStrip(thumbsEl, index => jumpToPage(index));',
    'function closeBook() {\n  ++renderGen;': 'function closeBook() {\n  thumbnailStrip.clear();\n  ++renderGen;',
    '  if (thumbs.open) renderThumbs();\n}': '''  if (thumbs.open) renderThumbs();
  else thumbnailStrip.hide();
  requestAnimationFrame(() => {
    if (state.book && state.mode === "guided") frameCurrentPanel(false, false);
  });
}''',
    'function frameCurrentPanel(animate = true) {':
        'function frameCurrentPanel(animate = true, prefetch = true) {',
    '  if (shouldPrefetchNextPanel(state.panel, g.rects.length)) prefetchGuidedNext(state.page);':
        '  if (prefetch && shouldPrefetchNextPanel(state.panel, g.rects.length)) prefetchGuidedNext(state.page);',
    '  state.panelCache[i] = rects;': '  rects = guidedSteps(rects, img.naturalWidth, img.naturalHeight);\n  state.panelCache[i] = rects;',
    '  updatePos(`p${state.page + 1} · panel ${state.panel + 1}/${g.rects.length}`);':
        '  updatePos(r.overview ? `p${state.page + 1} · page` : `p${state.page + 1} · panel ${state.panel}/${g.rects.length - 1}`);',
    '  state.mode = mode;\n  await render();': '  state.mode = mode;\n  if (mode === "guided") state.panel = 0;\n  await render();',
}
# Match the entire pinned eager-loader body: an upstream change must be reviewed.
patches['''async function renderThumbs() {
  if (!thumbsEl || !thumbs.open || !state.book) return;
  thumbsEl.innerHTML = "";
  updateThumbActive();
  state.book.pages.forEach((_, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.page = String(index);
    button.setAttribute("aria-label", `Jump to page ${index + 1}`);
    const canvas = document.createElement("canvas");
    canvas.width = 120; canvas.height = 160;
    canvas.setAttribute("aria-hidden", "true");
    button.appendChild(canvas);
    button.addEventListener("click", () => { jumpToPage(index); });
    thumbsEl.appendChild(button);
    pageURL(index).then((url) => {
      const image = new Image();
      image.onload = () => {
        const scale = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
        const width = Math.max(1, Math.round(image.naturalWidth * scale));
        const height = Math.max(1, Math.round(image.naturalHeight * scale));
        canvas.getContext("2d").drawImage(image, (canvas.width - width) / 2, (canvas.height - height) / 2, width, height);
      };
      image.src = url;
    }).catch(() => {});
  });
  updateThumbActive();
}'''] = '''async function renderThumbs() {
  if (!thumbsEl || !thumbs.open || !state.book) return;
  thumbnailStrip.show(state.book);
  updateThumbActive();
}'''
# A late prefetch must not use the new book's metadata with the old image. The
# cache array identifies one open-book lifecycle, including reopening an object.
patches['''async function prefetchGuidedNext(currentPage) {
  if (!state.book) return;
  const next = currentPage + 1;
  if (next >= state.book.pages.length) return;
  const url = await pageURL(next);
  const img = new Image();
  img.src = url;
  try { await img.decode(); } catch {}
  if (state.book && state.page === currentPage && state.panelCache[next]) return;
  if (!state.panelCache[next]) {
    await panelsFor(next, img);
  }
}'''] = '''const guidedPrefetches = new WeakMap();
async function prefetchGuidedNext(currentPage) {
  const book = state.book, cache = state.panelCache;
  const next = currentPage + 1;
  if (!book || next >= book.pages.length || cache[next]) return;
  let pending = guidedPrefetches.get(cache);
  if (!pending) { pending = new Map(); guidedPrefetches.set(cache, pending); }
  if (pending.has(next)) return pending.get(next);
  const current = () => state.book === book && state.panelCache === cache;
  const work = (async () => {
    let img = null;
    try {
      // Speculative failure must not close a readable current page. pageURL
      // clears failed requests, so demand navigation retries and reports errors.
      let url;
      try { url = await pageURL(next); } catch { return; }
      if (!current()) return;
      img = new Image();
      img.src = url;
      try { await img.decode(); } catch { return; }
      if (!current() || cache[next]) return;
      await panelsFor(next, img);
    } catch (error) {
      if (current()) throw error;
    } finally {
      if (img) img.removeAttribute("src");
      pending.delete(next);
    }
  })();
  pending.set(next, work);
  return work;
}'''
for before,after in patches.items():
    assert reader.count(before)==1, 'Upstream reader changed: '+before
    reader=reader.replace(before,after)
(a.output/'reader.js').write_text(reader)
for name in ['order-control.cbz','bounds.cbz','duplicate.cbz','rtl-control.cbz','legacy-control.cbz','profile-mismatch.cbz','single-control.cbz']:
    shutil.copyfile(a.fixtures/name,a.output/name)
catalog=[]
if a.saved_books:
    for kind, title, description in [
        ('gemini','Gemini sample','4 PDF pages: 1, 3, 5 and 25. Page 5 falls back to a whole page; page 25 has a known merged panel.'),
        ('local','Full book · local detector','257 PDF pages with saved local-detector results. Includes known panel errors and 48 reported whole-page fallbacks.'),
    ]:
        folder=a.saved_books/('replay-'+kind)
        report=json.loads((folder/'replay.json').read_text())
        name=report['output_file']
        assert Path(name).name==name and name.endswith('.cbz')
        source=folder/name
        with source.open('rb') as stream:
            assert hashlib.file_digest(stream,'sha256').hexdigest()==report['output_sha256']
        shutil.copyfile(source,a.output/name)
        catalog.append({'id':kind,'title':title,'description':description,'file':name,
                        'bytes':source.stat().st_size,'sha256':report['output_sha256']})
(a.output/'catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
html=(a.upstream/'index.html').read_text()
changes={
    '<title>PanelView — cinematic comic reader</title>':'<title>Panel lab · comic reader experiment</title>',
    '<link rel="manifest" href="manifest.webmanifest">':'',
    '<h1><span class="logo-mark"></span>PanelView</h1>':'<h1><span class="logo-mark"></span>Panel lab</h1>',
    'A cinematic comic reader that runs entirely in your browser.':'Read the panels. Keep the whole page.',
    'CBZ &middot; image folders &middot; <a href="https://github.com/wenn-id/comic-sol" target="_blank" rel="noopener">Comic Sol</a> projects — nothing is uploaded, ever.':'A phone-browser experiment. Open the sample below or choose a CBZ with ACBF metadata. Your chosen file stays in your browser.',
    'Drop a .cbz / .zip, an image folder, or a Comic Sol project':'Open a CBZ with panel metadata',
    '▶ Try the demo comic':'▶ Open the order experiment',
    'The camera glides panel-to-panel. Comic Sol projects get pixel-exact framing from their manifest; other comics use automatic panel detection.':'Follow the panel order stored in the book. The numbered sample deliberately reads 3 → 1 → 4 → 2.',
    'MIT · No tracking, no server.':'PanelView (MIT) + experimental ACBF adapter. Saved experiments; no new AI calls.',
    '<input type="file" id="file-input" multiple hidden>':'<input type="file" id="file-input" accept=".cbz,.zip" hidden>',
}
for before,after in changes.items():
    assert before in html, 'Upstream template changed: '+before
    html=html.replace(before,after)
html=html.replace('>📖</button>', '>Page</button>').replace('>📜</button>', '>Scroll</button>').replace('>🎬</button>', '>Panels</button>')
html=html.replace('📖 Page','Page').replace('📜 Webtoon','Scroll').replace('🎬 Guided','Panels')
html=html.replace('Read CBZ, image folders, and Comic Sol projects in your browser. Page, webtoon, and cinematic guided panel-by-panel modes. 100% client-side.', 'Experimental CBZ reader with embedded ACBF panel order. Files stay in your browser.')
html=html.replace('</head>','''<style>
#error {color:#ffb4a9;max-width:44rem;margin:1rem auto;padding:1rem}
#modes button {font-size:12px;min-height:40px}
#toolbar button {min-height:40px}
#hint {max-width:95vw;white-space:normal;text-align:center}
#saved-books {width:min(680px,100%);margin:0 0 28px}
#saved-books h2 {font-size:1.2rem;margin-bottom:8px}
.saved-book {padding:18px;margin:12px 0;background:var(--bg2);border:1px solid #333a55;border-radius:14px}
.saved-book p {color:var(--dim);font-size:14px;margin:8px 0 12px}
.saved-book button {padding:10px 18px}
#loading {max-width:42rem;padding:12px;color:var(--accent);text-align:center}
@media(max-width:560px){
 #btn-fs{display:none} #toolbar{gap:4px;padding-inline:6px}
 #toolbar > #book-meta{max-width:none;flex-basis:calc(100% - 56px)}
 #pos{font-size:10px} #toolbar button{padding-inline:6px}
}
</style></head>''')
html=html.replace('<section class="features">','<p id="error" role="alert" hidden></p><section class="features">')
html=html.replace('<div id="dropzone"','<section id="saved-books" hidden><h2>Read the saved experiments</h2><p>Rendered from the original PDF using the recorded panel results.</p><div id="book-list"></div></section><p id="loading" role="status" hidden></p><div id="dropzone"')
(a.output/'index.html').write_text(html)
# A returning phone browser must not combine a new shell with cached modules.
modules=sorted(a.output.glob('*.js'))
revision=hashlib.sha256(b''.join(p.read_bytes() for p in modules)).hexdigest()[:16]
for path in [*modules,*a.output.glob('*.html')]:
    source=path.read_text()
    source=re.sub(r'([\'"])(\./)?([a-z_-]+\.js)\1',
                  lambda m: m[1]+(m[2] or '')+m[3]+'?v='+revision+m[1],source)
    path.write_text(source)
(a.output/'build.json').write_text(json.dumps({'assets':revision})+'\n')
(a.output/'healthz').write_text('comic-reader-stage\n')
print('Built experimental reader:',a.output)
