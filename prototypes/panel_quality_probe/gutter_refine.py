"""Conservative offline expansion to near-matching artwork on dark gutters."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def expand_dark_gutter_boxes(rgb, boxes):
    height, width = rgb.shape[:2]
    result = [list(box) for box in boxes]
    corner = max(2, round(min(height, width) * .01))
    corners = [rgb[:corner, :corner], rgb[:corner, -corner:],
               rgb[-corner:, :corner], rgb[-corner:, -corner:]]
    if any(np.quantile(block.max(axis=2), .95) > 25 for block in corners):
        return result, []
    mask = (rgb.max(axis=2) > 25).astype('uint8')
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    _, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    candidates = []
    for x, y, w, h, area in stats[1:]:
        if area < width * height * .01 or area / (w * h) < .75:
            continue
        candidates.append([int(x), int(y), int(x + w), int(y + h)])
    changes = []
    for index, box in enumerate(boxes):
        x1, y1, x2, y2 = box
        matches = []
        for candidate in candidates:
            l, t, r, b = candidate
            if any(abs(a - v) > .02 * scale for a, v, scale in
                   zip(box, candidate, [width, height, width, height])):
                continue
            intersection = max(0, min(x2, r) - max(x1, l)) * max(0, min(y2, b) - max(y1, t))
            box_area = (x2 - x1) * (y2 - y1)
            component_area = (r - l) * (b - t)
            # Reciprocal coverage tolerates small offsets on thin panels while
            # the per-edge distance limit still rejects a different scene.
            if min(box_area, component_area) > 0 and min(intersection / box_area,
                                                       intersection / component_area) >= .90:
                matches.append(candidate)
        if len(matches) != 1:
            continue
        l, t, r, b = matches[0]
        expanded = [max(0, min(x1, l - 2)), max(0, min(y1, t - 2)),
                    min(width, max(x2, r + 2)), min(height, max(y2, b + 2))]
        if expanded != list(box):
            result[index] = expanded
            changes.append({'index': index, 'before_pixels': list(box),
                            'component_pixels': matches[0], 'after_pixels': expanded})
    return result, changes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('images', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    results = json.loads((a.run / 'results.json').read_text())
    output_results = []
    for record in results:
        assert record['status'] == 'structurally_valid_unreviewed', record
        page = record['source_page']
        source_dir = a.run / f'page-{page:04}'
        request = json.loads((source_dir / 'request.json').read_text())
        image_path = a.images / f'{page:04}.jpg'
        assert hashlib.sha256(image_path.read_bytes()).hexdigest() == request['source_sha256']
        with Image.open(image_path) as image:
            rgb = np.asarray(image.convert('RGB'))
        height, width = rgb.shape[:2]
        original = json.loads((source_dir / 'panels.json').read_text())
        panels = copy.deepcopy(original)
        boxes = [[round(v[1] * width / 1000), round(v[0] * height / 1000),
                  round(v[3] * width / 1000), round(v[2] * height / 1000)]
                 for v in [panel['box'] for panel in panels['panels']]]
        refined, changes = expand_dark_gutter_boxes(rgb, boxes) if panels['classification'] == 'panels' else (boxes, [])
        for change in changes:
            index = change['index']; l, t, r, b = refined[index]
            normalized = [math.floor(t * 1000 / height), math.floor(l * 1000 / width),
                          math.ceil(b * 1000 / height), math.ceil(r * 1000 / width)]
            old = panels['panels'][index]['box']
            panels['panels'][index]['box'] = [min(old[0], normalized[0]), min(old[1], normalized[1]),
                                             max(old[2], normalized[2]), max(old[3], normalized[3])]
        out = a.output / source_dir.name; out.mkdir()
        for name, value in [('request.json', request), ('panels.json', panels),
                            ('refinement.json', {'source_run': str(a.run), 'method': 'dark-gutter-expansion-v2',
                             'source_panels_sha256': hashlib.sha256((source_dir / 'panels.json').read_bytes()).hexdigest(),
                             'changes': changes, 'manual_geometry': False, 'inference_calls': 0})]:
            (out / name).write_text(json.dumps(value, indent=2) + '\n')
        output_results.append({**record, 'refined_panels': len(changes), 'reused_from': str(source_dir)})
        print(f'PDF {page}: {len(changes)} of {len(boxes)} boxes expanded; no model call', flush=True)
    (a.output / 'results.json').write_text(json.dumps(output_results, indent=2) + '\n')


if __name__ == '__main__':
    main()
