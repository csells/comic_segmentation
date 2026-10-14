"""Preserve nearby disconnected artwork on uniform black page backgrounds.

Only small foreground components intersecting or immediately adjacent to a crop
qualify. Components owned by another crop, ambiguous between crops, or extending
far beyond the crop are excluded. This cannot invent, split, or reorder panels.
"""
import cv2
import numpy as np


def expand_dark_fringe_boxes(rgb, boxes):
    height, width = rgb.shape[:2]
    result = [list(box) for box in boxes]
    corner = max(2, round(min(height, width) * .01))
    corners = [rgb[:corner, :corner], rgb[:corner, -corner:],
               rgb[-corner:, :corner], rgb[-corner:, -corner:]]
    if any(np.quantile(block.max(axis=2), .95) > 25 for block in corners):
        return result, []
    mask = (rgb.max(axis=2) > 25).astype('uint8')
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    _, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    short = min(height, width)
    near, limit = .005 * short, .04 * short
    attached = [[] for _ in boxes]
    for label, (x, y, w, h, area) in enumerate(stats[1:], 1):
        if area < max(8, width * height * .00001) or area > width * height * .01:
            continue
        component = [int(x), int(y), int(x+w), int(y+h)]
        owners = []
        for index, (l, t, r, b) in enumerate(boxes):
            # Restrict this heuristic to inset panels. Full-bleed views and
            # components in page-edge furniture need semantic interpretation.
            if min(l / width, t / height, (width-r) / width, (height-b) / height) < .02:
                continue
            dx = max(l - (x+w), x-r, 0)
            dy = max(t - (y+h), y-b, 0)
            if max(dx, dy) > near:
                continue
            overflow = max(l-x, t-y, x+w-r, y+h-b)
            if overflow > limit or overflow <= .004 * short:
                continue
            owners.append(index)
        if len(owners) != 1:
            continue
        index = owners[0]
        # A bounding box can straddle a neighboring view: use actual foreground
        # ownership rather than assuming that its empty bounding-box area is art.
        if any(np.any(labels[max(0,t):min(height,b), max(0,l):min(width,r)] == label)
               for j, (l,t,r,b) in enumerate(boxes) if j != index):
            continue
        l,t,r,b = boxes[index]
        if x >= l and y >= t and x+w <= r and y+h <= b:
            continue
        attached[index].append(component)
        old = result[index]
        result[index] = [max(0,min(old[0],int(x)-2)), max(0,min(old[1],int(y)-2)),
                         min(width,max(old[2],int(x+w)+2)), min(height,max(old[3],int(y+h)+2))]
    changes = [{'index':i, 'before_pixels':list(boxes[i]), 'after_pixels':result[i],
                'component_pixels':components, 'method':'nearby-black-gutter-fringe-v1'}
               for i,components in enumerate(attached) if components]
    return result, changes
