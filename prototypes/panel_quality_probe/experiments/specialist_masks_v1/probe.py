"""Pinned specialist-mask screen. Run in disposable VM; no paid API calls.

Produces raw masks and source-coordinate boxes, not a reading-order solution.
This is an experimental runner, not part of automatic conversion.
"""
import argparse
import hashlib
import json
import platform
import resource
import shutil
import time
import urllib.request
from pathlib import Path

MODELS = {
    'shadowb': {
        'repo': 'ShadowB/Manga109-panel-balloon-text-yolov26-segmentation',
        'revision': '3a860269ee0beb43ce9f31d82c7851441eb178ae',
        'file': 'best.pt',
        'sha256': '0b4376e426fa96af3976afa6a2602421dacf2dec96ef87b4a44f5e8d4971cb6f',
        'panel_class': 0,
    },
    'koharu': {
        'repo': 'mayocream/koharu-layout-rfdetr-seg-2xl-1152',
        'revision': 'aed55fdb8ca953c6bec33cf6ed6dd52a9b72bfa2',
        'file': 'model.safetensors',
        'sha256': '9bf6d2cbd7793c956d8c857bb1672a396eb7f100eb0682f86830d05e31168efb',
        'panel_class': 3,
    },
}


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('model', choices=MODELS)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--weights-dir', type=Path, required=True)
    a = p.parse_args()
    files = sorted(a.input.glob('*.jpg'))
    if not files:
        raise ValueError('No prepared JPEG inputs')
    a.output.mkdir(parents=True, exist_ok=False)
    cfg = MODELS[a.model]
    a.weights_dir.mkdir(parents=True, exist_ok=True)
    weights = a.weights_dir / (a.model + '-' + cfg['file'])
    if not weights.exists():
        url = f"https://huggingface.co/{cfg['repo']}/resolve/{cfg['revision']}/{cfg['file']}"
        partial = weights.with_suffix(weights.suffix + '.partial')
        print('Downloading pinned weights', cfg['repo'], flush=True)
        with urllib.request.urlopen(url, timeout=120) as response, partial.open('xb') as dest:
            shutil.copyfileobj(response, dest)
        if sha(partial) != cfg['sha256']:
            raise ValueError('Downloaded weight checksum mismatch')
        partial.rename(weights)
    if sha(weights) != cfg['sha256']:
        raise ValueError('Existing weight checksum mismatch')

    import torch
    import numpy as np
    from PIL import Image, ImageDraw
    torch.set_num_threads(4)
    start = time.monotonic()
    if a.model == 'shadowb':
        from ultralytics import YOLO
        model = YOLO(str(weights))
        settings = {'imgsz': 1280, 'conf': .25, 'iou': .7, 'retina_masks': True, 'device': 'cpu'}
    else:
        from rfdetr import RFDETRSeg2XLarge
        from safetensors.torch import load_file
        model = RFDETRSeg2XLarge(pretrain_weights=None, resolution=1152,
                                num_select=160, num_classes=4, device='cpu')
        model.model.model.load_state_dict(load_file(str(weights), device='cpu'), strict=True)
        model.model.class_names = ['text', 'onomatopoeia', 'bubble', 'panel']
        settings = {'threshold': .20, 'shape': (1152, 1152), 'include_source_image': False}
    manifest = {'model': cfg, 'settings': settings, 'model_load_seconds': time.monotonic()-start,
                'torch_version': torch.__version__, 'platform': platform.platform(),
                'new_paid_calls': 0, 'reading_order_evaluated': False,
                'purpose': 'Unqualified raw mask/box comparator; no production integration',
                'inputs': [{'name': f.name, 'sha256': sha(f)} for f in files]}
    (a.output/'run.json').write_text(json.dumps(manifest, indent=2)+'\n')
    for index, file in enumerate(files, 1):
        im = Image.open(file).convert('RGB')
        print(f'[{index}/{len(files)}] start {file.name}', flush=True)
        started = time.monotonic()
        with torch.inference_mode():
            if a.model == 'shadowb':
                result = model.predict(source=im, verbose=True, **settings)[0]
                boxes = result.boxes.xyxy.cpu().numpy()
                classes = result.boxes.cls.cpu().numpy().astype(int)
                scores = result.boxes.conf.cpu().numpy()
                masks = result.masks.data.cpu().numpy() if result.masks is not None else None
            else:
                result = model.predict(im, **settings)
                limits = {0: .25, 1: .20, 2: .50, 3: .50}
                keep = np.array([score >= limits[int(cls)] for cls, score in
                                 zip(result.class_id, result.confidence)], dtype=bool)
                result = result[keep]
                boxes, classes, scores, masks = (result.xyxy, result.class_id,
                                                 result.confidence, result.mask)
        elapsed = time.monotonic()-started
        if len(boxes) and (masks is None or len(masks) != len(boxes)):
            raise ValueError('Missing instance masks; boxes-only output cannot answer this spike')
        folder = a.output/file.stem
        folder.mkdir()
        overlay = im.copy()
        draw = ImageDraw.Draw(overlay)
        regions = []
        for j, (box, cls, score) in enumerate(zip(boxes, classes, scores)):
            raw = np.asarray(masks[j])
            np.savez_compressed(folder/f'raw-mask-{j:03}.npz', mask=raw)
            mask = Image.fromarray((raw > .5).astype('uint8')*255)
            raw_size = list(mask.size)
            if mask.size != im.size:
                raise ValueError(f'Unexpected mask size {mask.size} for source {im.size}; '
                                 'inspect documented transform before any resize')
            mask.save(folder/f'mask-{j:03}.png')
            row = {'index': j, 'class': int(cls), 'score': float(score),
                   'box_xyxy': [float(x) for x in box], 'raw_mask_size': raw_size,
                   'mask_file': f'mask-{j:03}.png', 'mask_bounds': mask.getbbox()}
            regions.append(row)
            if int(cls) == cfg['panel_class']:
                draw.rectangle(list(map(float, box)), outline='red', width=3)
                draw.text((float(box[0])+3, float(box[1])+3), str(j), fill='blue',
                          stroke_width=1, stroke_fill='white')
        overlay.save(folder/'panel-box-overlay.jpg', quality=95)
        record = {'input': file.name, 'source_dimensions': list(im.size),
                  'seconds': elapsed, 'regions': regions,
                  'maxrss': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  'maxrss_units': 'bytes' if platform.system() == 'Darwin' else 'KiB'}
        (folder/'result.json').write_text(json.dumps(record, indent=2)+'\n')
        print(f'[{index}/{len(files)}] done {file.name}: '
              f'{sum(r["class"] == cfg["panel_class"] for r in regions)} panels, {elapsed:.2f}s', flush=True)


if __name__ == '__main__':
    main()
