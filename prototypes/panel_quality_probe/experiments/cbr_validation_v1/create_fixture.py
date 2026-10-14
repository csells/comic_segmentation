"""Bounded synthetic CBR fixture; execute only in the disposable validation VM.

Requires an already downloaded official portable RAR package beneath ROOT/portable
and the VM's libarchive Python binding. No API key, inference or system install.
"""
import argparse
import binascii
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import urllib.request
import zipfile

import libarchive
from PIL import Image, ImageDraw


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if (root / 'fixture-manifest.json').exists():
        raise FileExistsError('fixture already complete; do not replace evidence')
    rar = root / 'portable/rar/rar'
    pages = root / 'source-pages'; pages.mkdir()
    records = []
    for ordinal in range(1, 4):
        image = Image.new('RGB', (320, 480), 'white')
        draw = ImageDraw.Draw(image)
        draw.text((15, 10), f'SYNTHETIC CONTAINER TEST / PAGE {ordinal}', fill='black')
        bounds = [(15, 40, 305, 460)] if ordinal == 1 else [
            (15, 40, 150, 230), (170, 40, 305, 230),
            (15, 250, 150, 460), (170, 250, 305, 460)]
        for number, box in enumerate(bounds, 1):
            draw.rectangle(box, fill=['#eacb5a', '#7dc7aa', '#dc9a89', '#a4b8dd'][number - 1],
                           outline='black', width=3)
            x0, y0, x1, y1 = box
            draw.ellipse((x0 + 20, y0 + 35, x0 + 60, y0 + 75), fill='white', outline='black', width=2)
            draw.line((x0 + 40, y0 + 75, x0 + 40, y1 - 20), fill='black', width=3)
            draw.text((x0 + 10, y0 + 10), f'Scene {number}', fill='black')
        path = pages / f'{ordinal:04d}.png'
        # Valid, lossless PNG with uncompressed DEFLATE blocks makes the archive's
        # own nonzero compression measurable, independent of image codec savings.
        image.save(path, compress_level=0)
        records.append({'name': path.name, 'bytes': path.stat().st_size,
                        'sha256': digest(path.read_bytes()), 'size': list(image.size),
                        'pixel_sha256': digest(image.tobytes())})
    (pages / 'notes.txt').write_text('Owned synthetic images for container parity only. No segmentation-quality claim.\n')
    commands = []

    def run(command, name, *, allowed=(0,)):
        result = subprocess.run(command, cwd=pages, capture_output=True, text=True, timeout=30)
        (root / name).write_text(result.stdout + result.stderr)
        commands.append({'argv': [str(v) for v in command], 'cwd': str(pages),
                         'exit_code': result.returncode, 'log': name})
        if result.returncode not in allowed:
            raise RuntimeError(f'archiver command failed; see {name}')
        return result.stdout

    version = run([str(rar)], 'rar-version.txt', allowed=(0, 7))
    archive = root / 'synthetic-rar5-compressed.cbr'
    run([str(rar), 'a', '-ma5', '-m3', '-md1m', '-mt1', '-s-', '-ep1',
         str(archive), *[r['name'] for r in records], 'notes.txt'], 'rar-create.txt')
    run([str(rar), 't', str(archive)], 'rar-test.txt')
    listing = run([str(rar), 'lt', str(archive)], 'rar-list.txt')
    raw = archive.read_bytes()
    if raw[:8] != b'Rar!\x1a\x07\x01\x00':
        raise ValueError('expected genuine RAR5 signature')
    if not len(raw) < sum(row['bytes'] for row in records):
        raise ValueError('archive did not measurably compress original page bytes')
    extracted = root / 'libarchive-extracted'; extracted.mkdir()
    actual = []
    with libarchive.file_reader(str(archive)) as reader:
        for entry in reader:
            name = PurePosixPath(entry.pathname)
            if not entry.isfile or name.is_absolute() or '..' in name.parts or len(name.parts) != 1:
                raise ValueError('unexpected archive entry')
            data = b''.join(entry.get_blocks())
            (extracted / str(name)).write_bytes(data)
            if data != (pages / str(name)).read_bytes():
                raise ValueError('libarchive did not preserve original bytes')
            actual.append({'name': str(name), 'bytes': len(data), 'sha256': digest(data)})
            if name.suffix == '.png':
                with Image.open(io.BytesIO(data)) as image:
                    expected = next(row for row in records if row['name'] == str(name))
                    if digest(image.convert('RGB').tobytes()) != expected['pixel_sha256']:
                        raise ValueError('decoded pixel parity failed')
    cbz = root / 'synthetic-equivalent.cbz'
    with zipfile.ZipFile(cbz, 'x', compression=zipfile.ZIP_DEFLATED) as writer:
        for path in sorted(pages.iterdir()): writer.write(path, path.name)

    # Upstream's small RAR4 fixture contains ordinary text plus a symlink.
    # Preserve it for the converter's rejection test; never extract that link.
    upstream = 'https://raw.githubusercontent.com/libarchive/libarchive/v3.7.4/libarchive/test/'
    downloads = []
    for name in ('test_read_format_rar.rar.uu', 'test_read_format_rar.c'):
        with urllib.request.urlopen(upstream + name, timeout=30) as response:
            data = response.read(200_001)
            if len(data) > 200_000: raise ValueError('upstream fixture download exceeded bound')
        (root / name).write_bytes(data)
        downloads.append({'url': upstream + name, 'bytes': len(data), 'sha256': digest(data)})
    lines = (root / 'test_read_format_rar.rar.uu').read_bytes().splitlines()
    if not lines[0].startswith(b'begin '): raise ValueError('not upstream uuencoded fixture')
    negative = root / 'upstream-rar4-symlink.cbr'
    negative.write_bytes(b''.join(binascii.a2b_uu(line) for line in lines[1:] if line != b'end'))
    negative_entries = []
    with libarchive.file_reader(str(negative)) as reader:
        for entry in reader:
            negative_entries.append({'name': entry.pathname, 'is_file': bool(entry.isfile),
                                     'is_symlink': bool(entry.issym), 'is_directory': bool(entry.isdir)})
    if not any(item['is_symlink'] for item in negative_entries):
        raise ValueError('negative fixture does not contain expected symlink')
    result = {'completed_at': datetime.now(timezone.utc).isoformat(), 'api_calls': 0,
              'archiver_version_header': version.strip().splitlines()[0],
              'archiver_binary_sha256': digest(rar.read_bytes()), 'commands': commands,
              'source_pages': records, 'source_folder': str(pages),
              'rar': {'path': str(archive), 'bytes': len(raw), 'sha256': digest(raw),
                      'signature_hex': raw[:8].hex(), 'format': 'RAR5',
                      'compression': 'normal (-m3), non-solid, unencrypted, single volume',
                      'requested_dictionary': '1 MiB (-md1m); inspect rar-list.txt for actual per-file dictionary'},
              'equivalent_cbz': {'path': str(cbz), 'sha256': digest(cbz.read_bytes())},
              'extracted': actual, 'byte_and_decoded_pixel_parity': True,
              'negative_fixture': {'path': str(negative), 'sha256': digest(negative.read_bytes()),
                                   'entries': negative_entries, 'downloads': downloads},
              'scope': 'Container creation and independent libarchive extraction only; converter and reader qualification pending.'}
    (root / 'fixture-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
