"""Offline source/threshold sensitivity probe; never edits converter output.

Input boxes are saved automatic proposals. Matching diagnostics are not semantic
ownership labels or an acceptance decision. Run only in disposable staging.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--bundle', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(exist_ok=False, parents=True)
    rgb = np.asarray(Image.open(a.source).convert('RGB'))
    height, width = rgb.shape[:2]
    panels = json.loads(a.bundle.read_text())['panels']
    boxes = []
    for p in panels:
        top, left, bottom, right = p['box']
        boxes.append([int(np.floor(left * width / 1000)),
                      int(np.floor(top * height / 1000)),
                      int(np.ceil(right * width / 1000)),
                      int(np.ceil(bottom * height / 1000))])
    rows = []
    for threshold in [220, 235, 245, 250, 253, 254]:
        start = time.monotonic()
        count, labels, stats, _ = cv2.connectedComponentsWithStats(
            (rgb.min(axis=2) < threshold).astype('uint8'), 8)
        minimum = max(16, int(width * height * .0005))
        significant = set(np.flatnonzero(stats[:, 4] >= minimum)) - {0}
        matches = []
        vis = Image.fromarray(rgb).copy()
        draw = ImageDraw.Draw(vis)
        for order, (left, top, right, bottom) in enumerate(boxes, 1):
            inside = np.bincount(labels[top:bottom, left:right].ravel(), minlength=count)
            choices = []
            for label in significant:
                x, y, w, h, area = map(int, stats[label])
                contained = int(inside[label]) / area
                if contained < .85:
                    continue
                # Rank by supported pixels, not bbox area; record ambiguity.
                choices.append((int(inside[label]), label, contained, [x, y, x+w, y+h]))
            choices.sort(reverse=True)
            match = {'order': order, 'proposal': [left, top, right, bottom],
                     'candidates': [{'inside_pixels': n, 'label': int(label),
                                     'contained_fraction': fraction, 'bounds': bounds}
                                    for n, label, fraction, bounds in choices[:3]]}
            matches.append(match)
            if choices:
                bounds = choices[0][3]
                draw.rectangle(bounds, outline='red', width=max(1, width//550))
                draw.text((bounds[0]+3, bounds[1]+3), str(order), fill='blue',
                          stroke_width=1, stroke_fill='white')
        selected = [m['candidates'][0]['label'] for m in matches if m['candidates']]
        row = {'threshold': threshold, 'significant_components': len(significant),
               'matched_panels': len(selected), 'unique_selected_components': len(set(selected)),
               'seconds': time.monotonic()-start, 'matches': matches}
        rows.append(row)
        vis.thumbnail((1128, 1648))
        vis.save(a.output/f'threshold-{threshold}.png')
        print(json.dumps({k:v for k,v in row.items() if k != 'matches'}), flush=True)
    manifest = {'purpose': 'Diagnostic threshold sensitivity; no runtime corrections or acceptances',
                'source': str(a.source), 'source_sha256': hashlib.sha256(a.source.read_bytes()).hexdigest(),
                'bundle_sha256': hashlib.sha256(a.bundle.read_bytes()).hexdigest(),
                'source_dimensions': [width, height], 'rows': rows}
    (a.output/'result.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
