"""Offline hypothesis: recover tiny clipped edges of mostly enclosed color regions.

Not integrated into automatic conversion. Full semantic checks remain necessary.
"""
import cv2
import numpy as np


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
