"""Pinned Magi/Western-YOLO pilot; execute only in a disposable research guest."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageDraw
import torch


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--kind', choices=['magi', 'yolo'], required=True)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--magi-iou-nms', action='store_true')
    p.add_argument('--image-size', type=int, default=640)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    started = time.monotonic()
    print('Loading', a.kind, 'on CPU', flush=True)
    if a.kind == 'magi':
        from transformers import AutoConfig, AutoModel
        path = a.root / 'models/magi'
        config = AutoConfig.from_pretrained(path, trust_remote_code=True)
        config.disable_ocr = True  # OCR is unrelated to panel detection.
        # Full checkpoint supplies the backbone; avoid a redundant pretrained download.
        config.detection_model_config.use_pretrained_backbone = False
        model, loading = AutoModel.from_pretrained(
            path, config=config, trust_remote_code=True, use_safetensors=True,
            output_loading_info=True)
        save(a.output / 'loading.json', loading)
        if loading['missing_keys'] or loading.get('mismatched_keys') or loading.get('error_msgs'):
            raise RuntimeError('Incomplete checkpoint loading; see loading.json')
        if any(not k.startswith('ocr_model.') for k in loading['unexpected_keys']):
            raise RuntimeError('Unexpected non-OCR weights')
        model.eval()
        utils = importlib.import_module(model.__class__.__module__.rsplit('.', 1)[0] + '.utils')
        sort_panels = utils.sort_panels
        model_path = path / 'model.safetensors'
    else:
        from ultralytics import YOLO
        model_path = a.root / 'models/yolo/best.pt'
        model = YOLO(model_path)
        # Same published geometric ordering algorithm, adapted to LTR by mirroring
        # box coordinates only. Actual detections and images are never mirrored.
        sys.path.insert(0, str(a.root / 'models/magi'))
        from utils import sort_panels
    run = {'kind': a.kind, 'device': 'cpu', 'threads': 2,
           'model_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest(),
           'load_seconds': time.monotonic() - started, 'manual_geometry': False,
           'ordering': 'Magi sort_panels on horizontally mirrored box coordinates for LTR',
           'input': 'grayscale RGB per Magi usage' if a.kind == 'magi' else 'original RGB',
           'threshold': .2 if a.kind == 'magi' else .25}
    run['magi_postprocessing'] = 'IoU NMS 0.7' if a.magi_iou_nms else 'upstream coverage suppression'
    run['yolo_image_size'] = a.image_size
    save(a.output / 'run.json', run)
    results = []
    for index, page in enumerate([5, 25, 254, 256], 1):
        source = a.root / 'pages' / f'{page:04}.jpg'
        im = Image.open(source).convert('RGB')
        out = a.output / f'page-{page:04}'
        out.mkdir()
        if a.kind == 'magi' and a.magi_iou_nms:
            def keep_panels(scores, labels, boxes, threshold):
                from torchvision.ops import nms
                selected = []
                proposals = []
                for score, label, box in zip(scores, labels, boxes):
                    indices = torch.where((label == 2) & (score >= threshold))[0]
                    proposals.append({'boxes': box[indices].tolist(), 'scores': score[indices].tolist()})
                    selected.append(indices[nms(box[indices], score[indices], .7)].tolist())
                save(out / 'before-panel-nms.json', proposals)
                return selected
            model.processor._get_indices_of_panels_to_keep = keep_panels
        save(out / 'request.json', {'source_page': page,
             'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), **run})
        print(f'[{index}/4] PDF {page}: {a.kind} inference', flush=True)
        started = time.monotonic()
        with torch.inference_mode():
            if a.kind == 'magi':
                raw = model.predict_detections_and_associations(
                    [np.asarray(im.convert('L').convert('RGB'))])[0]
                raw = {k: v.tolist() if hasattr(v, 'tolist') else v for k, v in raw.items()}
                boxes = raw['panels']
            else:
                pred = model.predict(im, device='cpu', imgsz=a.image_size, conf=.25,
                                     iou=.7, verbose=False, save=False)[0]
                raw = {'boxes': pred.boxes.xyxy.tolist(), 'scores': pred.boxes.conf.tolist(),
                       'classes': pred.boxes.cls.tolist(), 'names': pred.names}
                boxes = raw['boxes']
        elapsed = time.monotonic() - started
        save(out / 'raw.json', raw)
        mirrored = [[im.width-x2, y1, im.width-x1, y2] for x1, y1, x2, y2 in boxes]
        order = sort_panels(mirrored) if boxes else []
        ordered = [boxes[i] for i in order]
        save(out / 'ordered.json', {'boxes': ordered, 'raw_indices': order,
             'order_status': 'unreviewed', 'bounds_unchanged': True})
        overlay = im.copy()
        d = ImageDraw.Draw(overlay)
        for n, box in enumerate(ordered, 1):
            d.rectangle(box, outline='#ff2255', width=3)
            x, y = box[:2]
            d.rectangle([x, y, x+32, y+28], fill='black')
            d.text((x+3, y+2), str(n), fill='#ff2255', font_size=22)
            im.crop(tuple(round(v) for v in box)).save(out / f'crop-{n:02}.jpg', quality=95)
        overlay.save(out / 'overlay.jpg', quality=95)
        results.append({'source_page': page, 'panels': len(boxes),
                        'seconds': elapsed, 'quality': 'unreviewed'})
        save(a.output / 'results.json', results)
        print(f'[{index}/4] PDF {page}: {len(boxes)} panels in {elapsed:.3f}s', flush=True)


if __name__ == '__main__':
    main()
