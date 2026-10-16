"""Differential check of page-image preparation against the prototype (Pillow).

Usage: formats.py PROTOTYPE_DIR COMIC_PANEL_BIN WORK
Builds a folder book of EXIF-rotated JPEGs and other still formats, prepares it
with the Rust binary (--offline stops before any request) and with
import_format.prepare_publication_image, then compares records and pixels.
"""
import json, subprocess, sys, shutil
from pathlib import Path
import numpy as np
from PIL import Image
proto, binary, work = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
sys.path.insert(0, str(proto / 'panel_quality_probe'))
from import_format import prepare_publication_image
shutil.rmtree(work, ignore_errors=True); book = work / 'book'; book.mkdir(parents=True)
base = Image.new('RGB', (64, 40))
for x in range(64):
    for y in range(40):
        base.putpixel((x, y), (x * 4, y * 6, (x * y) % 256))
n = 0
def add(name, save):
    global n; n += 1; save(book / f'{n:02d}-{name}')
for o in range(1, 9):
    exif = Image.Exif(); exif[274] = o
    add(f'exif{o}.jpg', lambda p, e=exif: base.save(p, quality=95, exif=e))
rgba = base.convert('RGBA'); rgba.putalpha(Image.linear_gradient('L').resize((64, 40)))
add('rgba.png', lambda p: rgba.save(p))
pal = base.convert('P', palette=Image.Palette.ADAPTIVE, colors=16); pal.info['transparency'] = 0
add('palette.png', lambda p: pal.save(p, transparency=0))
add('plain.bmp', lambda p: base.save(p))
add('static.gif', lambda p: base.save(p))
add('still.webp', lambda p: base.save(p, lossless=True))
ok_count = n
# Rust: --offline prepares every page, then stops at the first (uncached) request.
ledger = work / 'ledger.jsonl'
ledger.write_text(json.dumps({'kind': 'policy', 'cap': 1, 'reserve': 300000, 'input_per_million_usd': 0.75, 'output_per_million_usd': 3.75}) + '\n')
subprocess.run([binary, str(book), str(work / 'out.cbz'), '--work-dir', str(work / 'rust'), '--ledger', str(ledger), '--offline'], capture_output=True)
rust = json.loads((work / 'rust/input/input.json').read_text())['pages']
pages = work / 'py'; pages.mkdir()
bad = 0
for i, (src, rec) in enumerate(zip(sorted(book.iterdir()), rust), 1):
    py = prepare_publication_image(src, pages / f'{i:04d}', pages / 'source-auxiliary/original-images', source_locator=src.name)
    keys = ('image', 'width', 'height', 'original_format', 'original_dimensions', 'original_exif_orientation', 'publication_transforms', 'preserved_original')
    diffs = {k: (py[k], rec[k]) for k in keys if py[k] != rec[k]}
    a = np.asarray(Image.open(pages / py['image']).convert('RGBA')); b = np.asarray(Image.open(work / 'rust/input/pages' / rec['image']).convert('RGBA'))
    same = a.shape == b.shape and (a == b).all()
    if diffs or not same:
        bad += 1; print('MISMATCH', src.name, diffs, 'pixels equal' if same else f'pixels differ {a.shape} {b.shape}')
print(f'{len(rust) - bad}/{ok_count} formats identical to the prototype' if len(rust) == ok_count else f'page count differs: {len(rust)} vs {ok_count}')
# Animated GIF must be refused before any request.
anim = work / 'anim'; anim.mkdir()
base.save(anim / '01.gif', save_all=True, append_images=[base.rotate(90, expand=False)], duration=100)
r = subprocess.run([binary, str(anim), str(work / 'anim.cbz'), '--work-dir', str(work / 'anim-run'), '--ledger', str(ledger), '--offline'], capture_output=True, text=True)
print('animated GIF refused:', r.returncode == 1 and 'animated' in r.stderr, r.stderr.strip()[-120:])
