"""Differential oracle for cli/src/refine.rs: run the prototype refiners on real pages.

Usage: refine_cases.py PAGES_DIR ACBF PROTOTYPE_DIR OUT_CASES OUT_EXPECTED
Boxes come from the best-available ACBF frames plus seeded perturbations, converted
to pixels exactly as Converter.refine does.
"""
import json, random, sys, re
from pathlib import Path
import numpy as np
from PIL import Image
pages, acbf, proto, out_cases, out_expected = map(Path, sys.argv[1:6])
sys.path.insert(0, str(proto / 'panel_quality_probe'))
from gutter_refine import expand_dark_gutter_boxes
from balloon_refine import expand_balloon_boxes
from frame_refine import expand_frame_boxes
from fringe_refine import expand_dark_fringe_boxes
from component_refine import expand_component_boxes, uncovered_content_risk

text = acbf.read_text()
frames = {}
for m in re.finditer(r'<(?:\w+:)?image href="(\d+)\.jpg"\s*/>(.*?)(?=<(?:\w+:)?image href|\Z)', text, re.S):
    frames[int(m.group(1))] = re.findall(r'points="([^"]+)"', m.group(2))
rng = random.Random(20261014)
cases, expected = [], []
for page in sorted(frames):
    path = pages / f'{page:04d}.jpg'
    with Image.open(path) as im:
        rgb = np.asarray(im.convert('RGB'))
    h, w = rgb.shape[:2]
    norm = []
    for pts in frames[page]:
        xy = [tuple(map(int, p.split(','))) for p in pts.split()]
        l, t = xy[0]; r, b = xy[2]
        norm.append([round(t * 1000 / h), round(l * 1000 / w), round((b + 1) * 1000 / h), round((r + 1) * 1000 / w)])
    variants = [norm]
    for _ in range(2):
        v = []
        for y, x, bb, rr in norm:
            d = [rng.randint(-12, 12) for _ in range(4)]
            box = [min(999, max(0, y + d[0])), min(999, max(0, x + d[1])), max(1, min(1000, bb + d[2])), max(1, min(1000, rr + d[3]))]
            if box[0] >= box[2] or box[1] >= box[3]: box = [y, x, bb, rr]
            v.append(box)
        variants.append(v)
    for vi, boxes in enumerate(variants):
        px = [[round(b[1] * w / 1000), round(b[0] * h / 1000), round(b[3] * w / 1000), round(b[2] * h / 1000)] for b in boxes]
        case = {'page': page, 'variant': vi, 'boxes': px}
        cases.append(case)
        out = {'page': page, 'variant': vi}
        for name, fn in (('gutter', expand_dark_gutter_boxes), ('balloon', expand_balloon_boxes), ('frame', expand_frame_boxes),
                         ('fringe', expand_dark_fringe_boxes), ('component', expand_component_boxes)):
            result, changes = fn(rgb, px)
            out[name] = {'boxes': result, 'changes': changes}
        valid = [b for b in px if 0 <= b[0] < b[2] <= w and 0 <= b[1] < b[3] <= h]
        out['uncovered'] = uncovered_content_risk(rgb, valid)
        expected.append(json.dumps(out))
    print(page, flush=True) if page % 50 == 0 else None
out_cases.write_text(json.dumps(cases))
out_expected.write_text('\n'.join(expected) + '\n')
