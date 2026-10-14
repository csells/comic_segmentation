"""Canonical publication images for the disposable converter.

Preserve compatible upright JPEG/PNG bytes. Other supported still images and
EXIF-oriented images become upright PNGs, with original bytes retained separately.
No model calls, frame selection or destructive source updates occur here.
"""
import hashlib
from pathlib import Path
import shutil

from PIL import Image, ImageOps


SUPPORTED_FORMATS = {'JPEG', 'PNG', 'BMP', 'GIF', 'WEBP'}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare_publication_image(source, destination_stem, originals_root, *, source_locator):
    """Return a page record for a fresh destination stem; never overwrite files.

    ``destination_stem`` is e.g. ``pages / '0001'`` with no extension.
    ``originals_root`` should be ``pages / 'source-auxiliary' / 'original-images'``.
    Its preserved files use an ``.original`` suffix so the publication adapter
    cannot mistake those auxiliary bytes for additional page images.
    """
    source, destination_stem, originals_root = map(Path, (source, destination_stem, originals_root))
    if source.is_symlink() or not source.is_file():
        raise ValueError('publication source must be a regular, nonsymlink file')
    if destination_stem.suffix:
        raise ValueError('publication destination stem must not have an extension')
    source_hash = digest(source)
    with Image.open(source) as image:
        source_format = image.format
        if source_format not in SUPPORTED_FORMATS:
            raise ValueError(f'unsupported publication image format: {source_format}')
        if getattr(image, 'n_frames', 1) != 1:
            raise ValueError('animated or multipage image unsupported; no frames were discarded')
        image.load()
        original_size = list(image.size)
        orientation = image.getexif().get(274, 1)
        if orientation not in range(1, 9):
            raise ValueError('invalid EXIF orientation')
        transformed = source_format not in ('JPEG', 'PNG') or orientation != 1
        extension = '.png' if transformed or source_format == 'PNG' else '.jpg'
        # Keep the supported original extension for byte-identical cache replay.
        compatible_extensions = ('.jpg', '.jpeg') if source_format == 'JPEG' else ('.png',)
        if not transformed and source.suffix.lower() in compatible_extensions:
            extension = source.suffix.lower()
        destination = destination_stem.with_suffix(extension)
        original = originals_root / (destination_stem.name + source.suffix.lower() + '.original')
        if not original.resolve().is_relative_to(destination.parent.resolve()):
            raise ValueError('preserved originals must remain beneath the publication page directory')
        if destination.exists() or (transformed and original.exists()):
            raise FileExistsError('publication image or preserved original already exists')
        if destination.resolve() == source.resolve() or original.resolve() == source.resolve():
            raise ValueError('publication must not overwrite source')
        destination.parent.mkdir(parents=True, exist_ok=True)
        operations = []
        if transformed:
            originals_root.mkdir(parents=True, exist_ok=True)
            with source.open('rb') as src, original.open('xb') as dst:
                shutil.copyfileobj(src, dst)
            upright = ImageOps.exif_transpose(image)
            if orientation != 1:
                operations.append('exif-transpose')
            # RGBA retains transparency; RGB avoids palette-dependent PNG output.
            mode = 'RGBA' if 'A' in upright.getbands() or 'transparency' in upright.info else 'RGB'
            upright = upright.convert(mode)
            with destination.open('xb') as stream:
                upright.save(stream, format='PNG')
            size = list(upright.size)
            operations.append('encode-png')
            if digest(original) != source_hash:
                raise RuntimeError('preserved original changed')
        else:
            with source.open('rb') as src, destination.open('xb') as dst:
                shutil.copyfileobj(src, dst)
            size = original_size
        if digest(source) != source_hash:
            raise RuntimeError('source changed during publication preparation')
    return {
        'locator': source_locator,
        'image': destination.name,
        'sha256': digest(destination),
        'width': size[0], 'height': size[1],
        'original_sha256': source_hash,
        'original_format': source_format,
        'original_dimensions': original_size,
        'original_exif_orientation': orientation,
        'publication_transforms': operations,
        'preserved_original': str(original.relative_to(destination.parent)) if transformed else None,
    }
