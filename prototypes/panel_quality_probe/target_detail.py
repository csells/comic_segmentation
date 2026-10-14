"""Source-only local context for an independent target-coverage diagnostic."""
import hashlib
import io
import math
from pathlib import Path

from PIL import Image, ImageDraw


def needs_source_detail(candidate, verdict, target):
    """Only adjudicate localized clipping on the final bounded repair."""
    return bool(candidate.get('repair_of') and candidate.get('tier') == 'astra'
                and verdict.get('decision') == 'escalate'
                and verdict.get('scene_inventory') == 'pass'
                and verdict.get('reading_order') == 'pass'
                and verdict.get('issues')
                and all(issue.get('kind') in ('clipped_art', 'clipped_text')
                        and set(issue.get('panels', [])) == {target}
                        for issue in verdict['issues']))


def with_source_detail(bundle, target, directory, *, mark_boundary=False):
    source = next(im for im in bundle['images'] if im['label'] == 'Original complete page')
    path = Path(source['path'])
    if hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
        raise ValueError('source detail input changed')
    panel = next(p for p in bundle['panels'] if p['order'] == target)
    y, x, bottom, right = panel['box']
    with Image.open(path) as im:
        width, height = im.size
        # Include real neighboring artwork outside every candidate edge. The
        # extraction depends only on source dimensions and generated geometry.
        margin_x, margin_y = max(64, math.ceil(width * .06)), max(64, math.ceil(height * .06))
        bounds = (max(0, math.floor(x * width / 1000) - margin_x),
                  max(0, math.floor(y * height / 1000) - margin_y),
                  min(width, math.ceil(right * width / 1000) + margin_x),
                  min(height, math.ceil(bottom * height / 1000) + margin_y))
        detail = im.convert('RGB').crop(bounds)
        scale = min(2, 1600 / max(detail.size))
        if scale != 1:
            detail = detail.resize(tuple(max(1, round(n * scale)) for n in detail.size), Image.Resampling.LANCZOS)
        directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f'target-{target}-source-detail-v1.jpg'
        encoded = io.BytesIO(); detail.save(encoded, format='JPEG', quality=95)
        data = encoded.getvalue()
        if destination.exists():
            if destination.read_bytes() != data:
                raise ValueError('existing source detail differs; use a new evidence directory')
        else:
            with destination.open('xb') as output:
                output.write(data)
    images = [im for im in bundle['images'] if im['label'] in
              ('Original complete page', f'Candidate crop {target} in reading order')]
    if len(images) != 2:
        raise ValueError('expected original source and one actual target crop')
    images.append({'label': f'Unannotated source detail around target {target}; includes neighboring scenes. '
                           f'Original pixel bounds left/top/right/bottom={list(bounds)}; '
                           f'full source size={width}x{height}. This is source context, not another candidate crop.',
                   'path': str(destination), 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})
    if mark_boundary:
        crop = images[1]
        points = [tuple(map(int, pair.split(','))) for pair in crop['points'].split()]
        left, top = points[0]; right, bottom = points[2]
        if points != [(left, top), (right, top), (right, bottom), (left, bottom)]:
            raise ValueError('expected actual rectangular crop points')
        with Image.open(crop['path']) as actual:
            if actual.size != (right - left + 1, bottom - top + 1):
                raise ValueError('crop points and actual image dimensions differ')
        sx = detail.width / (bounds[2] - bounds[0]); sy = detail.height / (bounds[3] - bounds[1])
        rect = [round((left - bounds[0]) * sx), round((top - bounds[1]) * sy),
                round((right + 1 - bounds[0]) * sx), round((bottom + 1 - bounds[1]) * sy)]
        marked = detail.copy()
        ImageDraw.Draw(marked).rectangle(rect, outline='#ff0000', width=2)
        encoded = io.BytesIO(); marked.save(encoded, format='JPEG', quality=95)
        marked_path = directory / f'target-{target}-crop-boundary-v2.jpg'
        data = encoded.getvalue()
        if marked_path.exists():
            if marked_path.read_bytes() != data:
                raise ValueError('existing boundary detail differs')
        else:
            with marked_path.open('xb') as output: output.write(data)
        images.append({'label': f'Same source detail with a generated RED rectangle marking the exact '
                                f'actual crop extent for target {target}. Outside the rectangle is excluded '
                                f'from the crop. The red line is NOT an artist-drawn panel border. '
                                f'Actual crop pixel bounds left/top/right-exclusive/bottom-exclusive='
                                f'{[left, top, right + 1, bottom + 1]}. Refer to the preceding unmarked '
                                f'detail wherever the line obscures artwork.',
                       'path': str(marked_path), 'sha256': hashlib.sha256(data).hexdigest()})
    return {**bundle, 'images': images}
