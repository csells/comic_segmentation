"""Bounded offline segmentation spike. Never modifies converter output.

Seeds come solely from source pixels and saved automatic box proposals. Ambiguous
component ownership is recorded and skipped; it is not resolved by human labels.
Run in disposable staging with OpenCV, numpy, and Pillow already available.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bbox(mask):
    ys, xs = np.nonzero(mask)
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1,
            int(ys.max()) + 1] if len(xs) else None


def select_seeds(rgb, boxes, radius, score):
    foreground = (rgb.min(axis=2) < 245).astype('uint8')
    if radius:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                          (radius * 2 + 1, radius * 2 + 1))
        foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    significant = set(np.flatnonzero(stats[:, 4] >= rgb.shape[0] * rgb.shape[1] * .005)) - {0}
    rows = []
    for order, (l, t, r, b) in enumerate(boxes, 1):
        inside = np.bincount(labels[t:b, l:r].ravel(), minlength=count)
        choices = []
        for label in significant:
            area = int(stats[label, 4])
            x,y,cw,ch = map(int,stats[label,:4])
            intersection = max(0,min(r,x+cw)-max(l,x))*max(0,min(b,y+ch)-max(t,y))
            iou = intersection / ((r-l)*(b-t)+cw*ch-intersection)
            if inside[label] / area >= .85 and inside[label] >= .03 * (r-l) * (b-t):
                if score == 'bbox_iou' and iou < .5:
                    continue
                choices.append({'label': int(label), 'inside_pixels': int(inside[label]),
                                'component_pixels': area, 'containment': float(inside[label]/area),
                                'bbox_iou':iou})
        key = 'inside_pixels' if score == 'pixel_support' else 'bbox_iou'
        ratio = .7 if score == 'pixel_support' else .9
        choices.sort(key=lambda x: x[key], reverse=True)
        reason = None
        if not choices:
            reason = 'no sufficiently contained significant component'
        elif len(choices) > 1 and choices[1][key] >= ratio * choices[0][key]:
            reason = 'multiple comparable components'
        rows.append({'order': order, 'proposal': [l,t,r,b], 'choices': choices[:3],
                     'seed_label': choices[0]['label'] if choices and reason is None else None,
                     'skip_reason': reason})
    selected = [row['seed_label'] for row in rows if row['seed_label'] is not None]
    for row in rows:
        if row['seed_label'] is not None and selected.count(row['seed_label']) > 1:
            row['skip_reason'] = 'component selected by competing proposals'
            row['seed_label'] = None
    seeds = {}
    for row in rows:
        if row['seed_label'] is not None:
            component = (labels == row['seed_label']).astype('uint8')
            core = cv2.erode(component, np.ones((5,5), 'uint8'))
            if not core.any():
                row['skip_reason'] = 'component has no eroded core'
                row['seed_label'] = None
            else:
                seeds[row['order']] = (component.astype(bool), core.astype(bool))
                row['component_bounds'] = bbox(component)
    return foreground, labels, rows, seeds


def watershed(rgb, foreground, rows, seeds):
    markers = np.zeros(rgb.shape[:2], dtype='int32')
    white = (rgb.min(axis=2) >= 252).astype('uint8')
    markers[cv2.erode(white, np.ones((7,7), 'uint8')).astype(bool)] = 1
    for order, (_, core) in seeds.items():
        markers[core] = order + 1
    markers[0,:] = markers[-1,:] = markers[:,0] = markers[:,-1] = 1
    cv2.watershed(cv2.cvtColor(cv2.GaussianBlur(rgb, (3,3), 0), cv2.COLOR_RGB2BGR), markers)
    masks = {}
    h,w = rgb.shape[:2]
    pad = max(16, round(min(h,w)*.04))
    for row in rows:
        order = row['order']
        if order not in seeds:
            continue
        l,t,r,b = row['proposal']
        roi = np.zeros((h,w), bool)
        roi[max(0,t-pad):min(h,b+pad), max(0,l-pad):min(w,r+pad)] = True
        masks[order] = (markers == order+1) & roi
    return masks


def grabcut(rgb, foreground, rows, seeds):
    h,w = rgb.shape[:2]
    pad = max(16, round(min(h,w)*.04))
    masks = {}
    for row in rows:
        order = row['order']
        if order not in seeds:
            continue
        l,t,r,b = row['proposal']
        l,t,r,b = max(0,l-pad),max(0,t-pad),min(w,r+pad),min(h,b+pad)
        source = np.ascontiguousarray(rgb[t:b,l:r,::-1])
        component, core = [x[t:b,l:r] for x in seeds[order]]
        init = np.full(source.shape[:2], cv2.GC_PR_BGD, dtype='uint8')
        init[component] = cv2.GC_PR_FGD
        init[core] = cv2.GC_FGD
        white = (source.min(axis=2) >= 252).astype('uint8')
        init[cv2.erode(white, np.ones((7,7), 'uint8')).astype(bool)] = cv2.GC_BGD
        for other, (_, othercore) in seeds.items():
            if other != order:
                init[othercore[t:b,l:r]] = cv2.GC_BGD
        init[0,:] = init[-1,:] = init[:,0] = init[:,-1] = cv2.GC_BGD
        cv2.grabCut(source, init, None, np.zeros((1,65)), np.zeros((1,65)), 3,
                    cv2.GC_INIT_WITH_MASK)
        mask = np.zeros((h,w), bool)
        mask[t:b,l:r] = (init == cv2.GC_FGD) | (init == cv2.GC_PR_FGD)
        masks[order] = mask
        print(json.dumps({'event':'grabcut_target_complete', 'order':order,
                          'mask_pixels':int(mask.sum())}), flush=True)
    return masks


def render(rgb, rows, seeds, masks, output, method):
    overlay = Image.fromarray(rgb).convert('RGBA')
    color = np.zeros((*rgb.shape[:2],4), dtype='uint8')
    results = []
    for row in rows:
        order = row['order']
        result = dict(row)
        mask = masks.get(order)
        if mask is None:
            results.append(result)
            continue
        component, core = seeds[order]
        color[mask] = [(order * 67)%220+30, (order*113)%220+30, (order*151)%220+30, 105]
        l,t,r,b = row['proposal']
        inside = np.zeros(mask.shape, bool);inside[t:b,l:r] = True
        competing = np.zeros(mask.shape, bool)
        for other,(_,othercore) in seeds.items():
            if other != order:
                competing |= othercore
        result.update({'mask_bounds':bbox(mask), 'mask_pixels':int(mask.sum()),
                       'pixels_outside_proposal':int((mask & ~inside).sum()),
                       'retained_seed_component_fraction':float((mask & component).sum()/component.sum()),
                       'retained_core_fraction':float((mask & core).sum()/core.sum()),
                       'competing_core_pixels':int((mask & competing).sum())})
        Image.fromarray(mask.astype('uint8')*255).save(output/f'{method}-{order:02d}-mask.png')
        bounds = result['mask_bounds']
        if bounds:
            x,y,x2,y2 = bounds
            isolated = rgb.copy();isolated[~mask] = 255
            Image.fromarray(isolated[y:y2,x:x2]).save(output/f'{method}-{order:02d}-isolated.jpg', quality=94)
        results.append(result)
    overlay = Image.alpha_composite(overlay,Image.fromarray(color)).convert('RGB')
    draw = ImageDraw.Draw(overlay)
    for row in results:
        box = row['proposal'];draw.rectangle(box, outline='red', width=2)
        draw.text((box[0]+3,box[1]+3), str(row['order']) + (' SKIP' if row['seed_label'] is None else ''),
                  fill='black', stroke_width=2, stroke_fill='white')
    overlay.save(output/f'{method}-overlay.jpg', quality=94)
    return results


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--bundle',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--radii',type=int,nargs='+',default=[0,3,7])
    ap.add_argument('--score',choices=['pixel_support','bbox_iou'],default='pixel_support')
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    cv2.setNumThreads(1);cv2.setRNGSeed(0)
    rgb=np.asarray(Image.open(a.source).convert('RGB'))
    h,w=rgb.shape[:2]
    panels=json.loads(a.bundle.read_text())['panels']
    boxes=[]
    for panel in panels:
        t,l,b,r=panel['box']
        boxes.append([int(np.floor(l*w/1000)),int(np.floor(t*h/1000)),
                      int(np.ceil(r*w/1000)),int(np.ceil(b*h/1000))])
    manifest={'source':str(a.source),'source_sha256':digest(a.source),
              'bundle':str(a.bundle),'bundle_sha256':digest(a.bundle),
              'code_sha256':digest(__file__), 'cv2_version':cv2.__version__,
              'dimensions':[w,h], 'score':a.score,
              'purpose':'Offline hypothesis screen; not runtime output or quality acceptance',
              'variants':[]}
    Image.fromarray(rgb).save(a.output/'source.png')
    for radius in a.radii:
        output=a.output/f'opening-{radius}';output.mkdir()
        start=time.monotonic()
        foreground,labels,rows,seeds=select_seeds(rgb,boxes,radius,a.score)
        seedseconds=time.monotonic()-start
        print(json.dumps({'event':'seeds','opening_radius':radius,'selected':len(seeds),
                          'proposals':len(boxes),'seconds':seedseconds}),flush=True)
        for method,func in [('watershed',watershed),('grabcut',grabcut)]:
            start=time.monotonic();masks=func(rgb,foreground,rows,seeds)
            seconds=time.monotonic()-start
            result={'opening_radius':radius,'method':method,'seed_seconds':seedseconds,
                    'method_seconds':seconds,'rows':render(rgb,rows,seeds,masks,output,method)}
            manifest['variants'].append(result)
            (a.output/'result.json').write_text(json.dumps(manifest,indent=2)+'\n')
            print(json.dumps({'event':'variant_complete','opening_radius':radius,'method':method,
                              'seconds':seconds,'selected':len(seeds)}),flush=True)
    print(json.dumps({'event':'complete','variants':len(manifest['variants'])}),flush=True)


if __name__ == '__main__':
    main()
