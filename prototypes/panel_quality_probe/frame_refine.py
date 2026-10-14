"""Expand near-matching framed panels to their connected ink extents.

Diagnostic candidate: geometry comes only from source pixels. A connected ink
component must already closely match all four proposed crop edges. This avoids
following a protruding object into a different panel or across a whole page.
"""
import cv2
import numpy as np


def expand_frame_boxes(rgb, boxes):
    height, width = rgb.shape[:2]
    dark = rgb.max(axis=2) < 100
    ink = (rgb.min(axis=2) < 220).astype('uint8')
    # Bridge small scan/JPEG gaps, without spanning normal page gutters.
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    _, _, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
    candidates = []
    for x, y, w, h, area in stats[1:]:
        if min(w / width, h / height) < .025 or area < width * height * .001:
            continue
        candidates.append([int(x), int(y), int(x + w), int(y + h)])
    result = [list(box) for box in boxes]
    changes = []
    for index, box in enumerate(boxes):
        l, t, r, b = box
        matches = []
        for candidate in candidates:
            x, y, rr, bb = candidate
            if any(abs(a - v) > .02 * scale for a, v, scale in
                   zip(box, candidate, [width, height, width, height])):
                continue
            intersection = max(0, min(r, rr) - max(l, x)) * max(0, min(b, bb) - max(t, y))
            areas = [(r - l) * (b - t), (rr - x) * (bb - y)]
            if min(areas) <= 0 or min(intersection / area for area in areas) < .90:
                continue
            matches.append(candidate)
        if len(matches) != 1:
            continue
        x, y, rr, bb = matches[0]
        # Ignore deviations within roughly a scanned border's thickness.
        # This is resolution-relative, not a page-specific coordinate.
        if max(l - x, t - y, rr - r, bb - b) <= .004 * min(width, height):
            continue
        # Require a nearly complete dark frame near each proposed edge. Colored
        # shapes and diagonal/borderless scenes can have matching component
        # bounds without being a rectangular panel; don't expand those here.
        dx, dy = max(1, round(width * .02)), max(1, round(height * .02))
        bands = [(dark[max(0,t-dy):min(height,t+dy+1),l:r], 1),
                 (dark[max(0,b-dy):min(height,b+dy+1),l:r], 1),
                 (dark[t:b,max(0,l-dx):min(width,l+dx+1)], 0),
                 (dark[t:b,max(0,r-dx):min(width,r+dx+1)], 0)]
        if any(band.size == 0 or band.mean(axis=axis).max() < .8 for band, axis in bands):
            continue
        expanded = [max(0, min(l, x - 2)), max(0, min(t, y - 2)),
                    min(width, max(r, rr + 2)), min(height, max(b, bb + 2))]
        result[index] = expanded
        changes.append({'index': index, 'before_pixels': list(box),
                        'after_pixels': expanded, 'component_pixels': matches[0],
                        'method': 'near-matching-connected-ink-v1'})
    return result, changes
