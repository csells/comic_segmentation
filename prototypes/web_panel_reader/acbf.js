/* Experimental ACBF 1.1 -> PanelView boundary. No detection or order inference. */
import { readZip } from './zip.js';

const NS = 'http://www.acbf.info/xml/acbf/1.1';
const MB = 1024 * 1024;
const children = (node, name) => [...(node?.children || [])].filter(e => e.namespaceURI === NS && e.localName === name);
function one(node, name) {
  const found = children(node, name);
  if (found.length !== 1) throw Error(`ACBF needs exactly one ${name}`);
  return found[0];
}
function safePath(path) {
  if (!path || /[\\:#?%\x00-\x1f]/.test(path) || path.split('/').some(p => !p || p === '.' || p === '..'))
    throw Error('Unsupported archive path: ' + path);
  return path;
}
function frameRect(frame) {
  const raw = (frame.getAttribute('points') || '').trim().split(/\s+/);
  if (raw.length < 3 || raw.length > 100 || raw.some(p => !/^\d+,\d+$/.test(p)))
    throw Error('Invalid frame points');
  const points = raw.map(p => p.split(',').map(Number));
  if (points.flat().some(n => !Number.isSafeInteger(n))) throw Error('Invalid frame coordinates');
  const xs = points.map(p => p[0]), ys = points.map(p => p[1]);
  const area = points.reduce((sum, p, i) => {
    const q = points[(i + 1) % points.length];
    return sum + p[0] * q[1] - q[0] * p[1];
  }, 0);
  const x = Math.min(...xs), y = Math.min(...ys);
  const width = Math.max(...xs) - x, height = Math.max(...ys) - y;
  if (!width || !height || !area) throw Error('Degenerate frame');
  return { x, y, width, height };
}

export function parseAcbf(text, paths) {
  if (/<!DOCTYPE|<!ENTITY/i.test(text)) throw Error('DTD and entities are unsupported');
  const doc = new DOMParser().parseFromString(text, 'application/xml');
  if (doc.querySelector('parsererror')) throw Error('Invalid XML');
  const root = doc.documentElement;
  if (root.localName !== 'ACBF' || root.namespaceURI !== NS) throw Error('Expected ACBF 1.1');
  const info = one(one(root, 'meta-data'), 'book-info');
  const bodies = children(root, 'body');
  if (bodies.length > 1) throw Error('ACBF supports at most one body');
  const bodyPages = children(bodies[0], 'page');
  if (bodies.length && !bodyPages.length) throw Error('ACBF body needs at least one page');
  const nodes = [one(info, 'coverpage'), ...bodyPages];
  if (nodes.length > 600) throw Error('This experiment supports at most 600 pages');
  const seen = new Set();
  const pages = nodes.map(node => {
    const path = safePath(one(node, 'image').getAttribute('href'));
    if (!/\.(png|jpe?g)$/i.test(path)) throw Error('Only PNG and JPEG pages are supported');
    if (!paths.has(path)) throw Error('Missing image: ' + path);
    if (seen.has(path)) throw Error('Duplicate image reference: ' + path);
    seen.add(path);
    const frames = children(node, 'frame');
    if (frames.length > 200) throw Error('Too many frames on a page');
    // Even [] is intentional: PanelView must use a whole-page frame, never detect.
    return { path, panels: frames.map(frameRect) };
  });
  return {
    title: children(info, 'book-title')[0]?.textContent.trim() || 'Untitled comic',
    pages,
    // The standard ACBF 1.1 schema does not define reading direction.
    // A verified optional companion profile supplies this reader preference.
    readingDirection: 'ltr',
    comicSol: true, // PanelView's supplied-panel flag; enables Guided by default.
    subtitle: 'Embedded panel order · full page, then panels',
  };
}

export function parseReaderProfile(text, metadataSha256) {
  const profile = JSON.parse(text);
  const keys = ['format', 'metadata_sha256', 'reading_direction', 'version'];
  if (!profile || typeof profile !== 'object' || Array.isArray(profile) ||
      Object.keys(profile).sort().join(',') !== keys.join(',') ||
      profile.format !== 'comic-panel-reader-profile' || profile.version !== 1 ||
      !['ltr', 'rtl'].includes(profile.reading_direction) ||
      !/^[a-f0-9]{64}$/.test(profile.metadata_sha256) || profile.metadata_sha256 !== metadataSha256)
    throw Error('Invalid or mismatched panel reader profile');
  return profile;
}

async function sha256(blob) {
  const bytes = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
  return [...new Uint8Array(bytes)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

export async function openAcbf(blob) {
  if (blob.size > 128 * MB) throw Error('This experiment supports CBZ files up to 128 MiB');
  const zip = await readZip(blob, 32 * MB);
  if (zip.entries.length > 2000) throw Error('Too many archive entries');
  const entries = new Map();
  let declaredBytes = 0;
  for (const entry of zip.entries) {
    safePath(entry.name);
    if (entries.has(entry.name)) throw Error('Duplicate ZIP name: ' + entry.name);
    if (![0, 8].includes(entry.method)) throw Error('Only stored and deflated ZIP entries are supported');
    declaredBytes += entry.uncompSize;
    if (entry.uncompSize > 32 * MB || entry.compSize > 32 * MB || declaredBytes > 512 * MB)
      throw Error('Archive exceeds experiment size limits');
    entries.set(entry.name, entry);
  }
  const metadata = entries.get('metadata.acbf');
  if (!metadata) throw Error('This experiment requires root metadata.acbf');
  if (metadata.uncompSize > 2 * MB) throw Error('Metadata exceeds 2 MiB');
  const xml = await zip.extract(metadata);
  if (xml.size > 2 * MB) throw Error('Metadata exceeds 2 MiB');
  const book = parseAcbf(await xml.text(), new Set(entries.keys()));
  const profileEntry = entries.get('panel-reader.json');
  if (profileEntry) {
    if (profileEntry.uncompSize > 4096) throw Error('Panel reader profile exceeds 4 KiB');
    const profileBlob = await zip.extract(profileEntry);
    if (profileBlob.size !== profileEntry.uncompSize || profileBlob.size > 4096)
      throw Error('Panel reader profile size mismatch');
    const profile = parseReaderProfile(await profileBlob.text(), await sha256(xml));
    book.readingDirection = profile.reading_direction;
    // A revised profile must not restore a stale direction from an older book.
    book.resumeId = book.title + ':profile-v1:' + await sha256(profileBlob);
  }
  for (const page of book.pages) {
    const entry = entries.get(page.path);
    page.resumeSource = [page.path, entry.crc, entry.uncompSize, metadata.crc];
    page.get = async () => {
      const extracted = await zip.extract(entry);
      if (extracted.size !== entry.uncompSize) throw Error('ZIP size mismatch: ' + page.path);
      const result = new Blob([extracted], {type: /\.png$/i.test(page.path) ? 'image/png' : 'image/jpeg'});
      const url = URL.createObjectURL(result);
      try {
        const image = new Image(); image.src = url;
        await image.decode();
        if (image.naturalWidth * image.naturalHeight > 40_000_000) throw Error('Image exceeds 40 megapixels');
        for (const p of page.panels) {
          if (p.x + p.width > image.naturalWidth || p.y + p.height > image.naturalHeight)
            throw Error('Frame outside image bounds: ' + page.path);
        }
      } finally { URL.revokeObjectURL(url); }
      return result;
    };
  }
  return book;
}
