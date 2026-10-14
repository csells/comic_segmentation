"""Recover tiny clipped edges of mostly enclosed color regions.

Only eligible machine-flagged targets may use this final bounded correction.
Full semantic checks remain necessary.
"""
import math
import cv2
import numpy as np


def uncovered_content_risk(rgb, boxes):
    """Find substantive non-paper pixels outside all half-open crop boxes.

    This only routes ownership checks. It cannot identify a scene, repair a
    rectangle, or certify quality. Mixed/tinted paper may conservatively flag.
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3 or min(rgb.shape[:2]) < 1:
        raise ValueError('Expected nonempty RGB source')
    height, width = rgb.shape[:2]
    covered = np.zeros((height, width), dtype=bool)
    for box in boxes:
        if len(box) != 4 or any(type(n) is not int for n in box):
            raise ValueError('Expected integer pixel crop bounds')
        left, top, right, bottom = box
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise ValueError('Crop bounds outside source')
        covered[top:bottom, left:right] = True
    # Reuse the existing gutter/fringe black-paper rule, without changing boxes.
    corner = max(2, round(min(height, width) * .01))
    corners = [rgb[:corner, :corner], rgb[:corner, -corner:],
               rgb[-corner:, :corner], rgb[-corner:, -corner:]]
    corner_levels = [float(np.quantile(block.max(axis=2), .95)) for block in corners]
    black_paper = all(level <= 25 for level in corner_levels)
    foreground = rgb.max(axis=2) > 25 if black_paper else rgb.min(axis=2) < 245
    residual = (foreground & ~covered).astype('uint8')
    _, _, stats, _ = cv2.connectedComponentsWithStats(residual, 8)
    minimum = max(16, math.ceil(width * height * .0005))
    components = [{'bounds': [int(x), int(y), int(x+w), int(y+h)], 'pixels': int(area)}
                  for x, y, w, h, area in stats[1:] if area >= minimum]
    return {'algorithm': 'uncovered-nonpaper-components-v2', 'source_dimensions': [width, height],
            'paper_polarity': 'black' if black_paper else 'light_or_mixed',
            'corner_size': corner, 'corner_max_rgb_95th_percentiles': corner_levels,
            'foreground_below': None if black_paper else 245,
            'foreground_above': 25 if black_paper else None, 'minimum_component_pixels': minimum,
            'uncovered_nonpaper_pixels': int(residual.sum()), 'components': components,
            'requires_ownership': bool(components)}


def expand_component_boxes(rgb, boxes):
    height, width = rgb.shape[:2]
    foreground = (rgb.min(axis=2) < 245).astype('uint8')
    count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    colored = rgb.max(axis=2) - rgb.min(axis=2) >= 20
    colored_counts = np.bincount(labels[colored], minlength=count)
    result = [list(box) for box in boxes]; changes = []
    for index, (left, top, right, bottom) in enumerate(boxes):
        area = (right - left) * (bottom - top)
        if area <= 0: continue
        inside = np.bincount(labels[top:bottom, left:right].reshape(-1), minlength=count)
        candidates = []
        for label in np.flatnonzero(inside >= .20 * area):
            if label == 0: continue
            x, y, w, h, component_area = map(int, stats[label])
            if inside[label] / component_area < .98 or colored_counts[label] / component_area < .35:
                continue
            bounds = [x, y, x + w, y + h]
            expansion = [max(0, left - x), max(0, top - y),
                         max(0, x + w - right), max(0, y + h - bottom)]
            if not any(expansion) or any(n > .02 * scale for n, scale in
                                        zip(expansion, [width, height, width, height])):
                continue
            candidates.append((label, bounds, float(inside[label] / component_area), expansion))
        # Ambiguous ownership stays unchanged for model-based handling.
        if len(candidates) != 1: continue
        label, bounds, contained, expansion = candidates[0]
        x, y, rr, bb = bounds
        updated = [max(0, x - 3) if expansion[0] else left,
                   max(0, y - 3) if expansion[1] else top,
                   min(width, rr + 3) if expansion[2] else right,
                   min(height, bb + 3) if expansion[3] else bottom]
        result[index] = updated
        changes.append({'index': index, 'before': list(boxes[index]), 'after': updated,
                        'component_bounds': bounds, 'component_fraction_inside': contained,
                        'algorithm': 'mostly-enclosed-color-component-v1'})
    return result, changes
