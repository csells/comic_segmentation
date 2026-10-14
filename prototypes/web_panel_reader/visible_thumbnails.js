/* Small previews are independent of the reader's full-page object URL cache. */
export function createThumbnailStrip(root, jumpToPage) {
  let book = null, shown = false, generation = 0, observer = null;
  let buttons = [], queue = [];
  const near = new Set(), queued = new Set(), active = new Set();

  const current = task => shown && task.generation === generation && task.book === book;

  function enqueue(index) {
    if (!shown || queued.has(index) || buttons[index].dataset.thumbnailState) return;
    if ([...active].some(task => current(task) && task.index === index)) return;
    queued.add(index);
    queue.push(index);
  }

  function pump() {
    while (shown && active.size < 2 && queue.length) {
      const index = queue.shift();
      queued.delete(index);
      if (!near.has(index) || buttons[index].dataset.thumbnailState) continue;
      const task = {book, generation, index, button: buttons[index], cancel: null};
      active.add(task);
      load(task);
    }
  }

  async function load(task) {
    let image = null, url = null;
    try {
      // Do not call pageURL: a preview must not retain a full-size page URL.
      const blob = await task.book.pages[task.index].get();
      if (!current(task) || !near.has(task.index)) return;
      url = URL.createObjectURL(blob);
      image = new Image();
      const canceled = new Promise(resolve => {
        task.cancel = () => { image.removeAttribute('src'); resolve(false); };
      });
      image.src = url;
      const decoded = await Promise.race([image.decode().then(() => true), canceled]);
      if (!decoded || !current(task) || !near.has(task.index)) return;
      const canvas = task.button.firstElementChild;
      const scale = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
      const width = Math.max(1, Math.round(image.naturalWidth * scale));
      const height = Math.max(1, Math.round(image.naturalHeight * scale));
      canvas.getContext('2d').drawImage(image, (canvas.width - width) / 2,
        (canvas.height - height) / 2, width, height);
      task.button.dataset.thumbnailState = 'ready';
      observer?.unobserve(task.button);
    } catch {
      if (current(task) && near.has(task.index)) {
        task.button.dataset.thumbnailState = 'error';
        task.button.title = 'Thumbnail unavailable; open this page to try reading it';
        observer?.unobserve(task.button);
      }
    } finally {
      task.cancel = null;
      if (image) image.removeAttribute('src');
      if (url) URL.revokeObjectURL(url);
      active.delete(task);
      pump();
    }
  }

  function hide() {
    shown = false;
    ++generation;
    observer?.disconnect();
    observer = null;
    queue = [];
    queued.clear();
    near.clear();
    // Extraction cannot be aborted. It retains its slot until it settles, then
    // the generation check discards it before creating a URL or decoding again.
    for (const task of active) task.cancel?.();
  }

  function clear() {
    hide();
    book = null;
    for (const button of buttons) {
      button.firstElementChild.width = 0;
      button.firstElementChild.height = 0;
    }
    buttons = [];
    root?.replaceChildren();
  }

  function show(nextBook) {
    if (!root || !nextBook) return;
    if (book !== nextBook) {
      clear();
      book = nextBook;
      const fragment = document.createDocumentFragment();
      buttons = book.pages.map((_, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.dataset.page = String(index);
        button.setAttribute('aria-label', `Jump to page ${index + 1}`);
        const canvas = document.createElement('canvas');
        canvas.width = 120; canvas.height = 160;
        canvas.setAttribute('aria-hidden', 'true');
        button.appendChild(canvas);
        button.addEventListener('click', () => jumpToPage(index));
        fragment.appendChild(button);
        return button;
      });
      root.replaceChildren(fragment);
      root.scrollLeft = 0;
    }
    // A page jump calls this again. Keep both DOM and scroll position intact.
    if (shown) return;
    shown = true;
    const observedGeneration = generation;
    observer = new IntersectionObserver(entries => {
      if (!shown || generation !== observedGeneration) return;
      for (const entry of entries) {
        const index = Number(entry.target.dataset.page);
        if (entry.isIntersecting) { near.add(index); enqueue(index); }
        else near.delete(index);
      }
      pump();
    }, {root, rootMargin: '0px 240px', threshold: 0});
    for (const button of buttons) {
      if (!button.dataset.thumbnailState) observer.observe(button);
    }
  }

  return {show, hide, clear};
}
