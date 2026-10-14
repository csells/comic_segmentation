"""Disposable-VM SAM 2.1 tiny box-refinement spike; no production integration.

Consumes only immutable saved automatic proposals. No manual points, model calls,
training labels, crop-based image embeddings, or mask clipping to prompt boxes.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import re
import resource
import shutil
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

CODE_REVISION = "2b90b9f5ceec907a1c18123530e92e794ad901a4"
MODEL_REPO = "facebook/sam2.1-hiera-tiny"
MODEL_REVISION = "de431c4043854a71d8101e17995dfe596bf101a5"
WEIGHT_NAME = "sam2.1_hiera_tiny.pt"
WEIGHT_SHA = "7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69"
CONFIG = "configs/sam2.1/sam2.1_hiera_t.yaml"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save_json(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def checked_file(root, name, expected):
    path = (root / name).resolve()
    if sha(path) != expected:
        raise ValueError(f"Input digest mismatch: {path}")
    return path


def proposal_boxes(proposal, width, height):
    """Use saved crop extents when available; otherwise explicit outward mapping."""
    panels = proposal["panels"]
    if not panels or [p["order"] for p in panels] != list(range(1, len(panels) + 1)):
        raise ValueError("Expected nonempty automatic panels in contiguous reading order")
    images = proposal.get("images")
    exact = images is not None
    if exact and len(images) != len(panels) + 1:
        raise ValueError("Bundle does not map one saved crop to every panel")
    result = []
    for index, panel in enumerate(panels, 1):
        if exact:
            points = [[int(n) for n in pair.split(",")]
                      for pair in images[index]["points"].split()]
            xs, ys = zip(*points)
            x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
            if len(points) != 4 or set(map(tuple, points)) != {
                    (x0, y0), (x1, y0), (x1, y1), (x0, y1)}:
                raise ValueError("Expected saved rectangular integer crop points")
            # ACBF-style bundle points name included corner pixels. The converter
            # crops (left, top, right + 1, bottom + 1), so convert before using
            # NumPy/Pillow half-open extents for prompts, metrics and overlays.
            x1 += 1
            y1 += 1
            rule = "saved_inclusive_corner_points_to_half_open_xyxy_plus_one"
        else:
            y0n, x0n, y1n, x1n = panel["box"]
            if not (0 <= x0n < x1n <= 1000 and 0 <= y0n < y1n <= 1000):
                raise ValueError("Expected normalized yxyx coordinates in 0..1000")
            x0, y0 = math.floor(x0n * width / 1000), math.floor(y0n * height / 1000)
            x1, y1 = math.ceil(x1n * width / 1000), math.ceil(y1n * height / 1000)
            rule = "estimated_normalized_yxyx_1000_to_outward_integer_xyxy_half_open"
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise ValueError("Prompt bounds outside source")
        result.append({"order": index, "box_xyxy": [x0, y0, x1, y1],
                       "mapping_rule": rule, "crop_extent_exact": exact,
                       "original_box": panel["box"]})
    return result


def weights_at(root):
    root.mkdir(parents=True, exist_ok=True)
    path = root / WEIGHT_NAME
    if not path.exists():
        partial = path.with_suffix(path.suffix + ".partial")
        url = f"https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REVISION}/{WEIGHT_NAME}"
        print("Downloading pinned Meta SAM 2.1 tiny checkpoint", flush=True)
        with urllib.request.urlopen(url, timeout=120) as response, partial.open("xb") as dest:
            shutil.copyfileobj(response, dest)
        if sha(partial) != WEIGHT_SHA:
            raise ValueError("Downloaded checkpoint digest mismatch")
        partial.rename(path)
    if sha(path) != WEIGHT_SHA:
        raise ValueError("Checkpoint digest mismatch")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--weights-dir", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--multimask", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.threads <= 8:
        raise ValueError("Expected 1..8 CPU threads")
    envelope = json.loads(args.cases.read_text())
    if envelope.get("version") != 1 or not envelope.get("cases"):
        raise ValueError("Expected nonempty version-1 case manifest")
    groups = defaultdict(list)
    identities = set()
    for case in envelope["cases"]:
        identity = case["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", identity) or identity in identities:
            raise ValueError("Case IDs must be unique safe directory names")
        identities.add(identity)
        source = checked_file(args.cases.parent, case["source"], case["source_sha256"])
        proposals = checked_file(args.cases.parent, case["proposals"], case["proposals_sha256"])
        proposal = json.loads(proposals.read_text())
        embedded_sha = (proposal.get("source_sha256") or
                        (proposal.get("images") or [{}])[0].get("sha256"))
        if embedded_sha and embedded_sha != case["source_sha256"]:
            raise ValueError("Proposal was generated for a different source image")
        groups[case["source_sha256"]].append((case, source, proposal))

    args.output.mkdir(parents=True, exist_ok=False)
    weights = weights_at(args.weights_dir)
    started = time.monotonic()
    import numpy as np
    import torch
    import sam2
    from PIL import Image, ImageDraw
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    torch.set_num_threads(args.threads)
    provenance = importlib.metadata.distribution("SAM-2").read_text("direct_url.json")
    provenance = json.loads(provenance) if provenance else None
    installed_commit = (provenance or {}).get("vcs_info", {}).get("commit_id")
    if installed_commit != CODE_REVISION:
        raise ValueError("Install SAM-2 from the exact pinned git URL; package commit is unverified")
    import_seconds = time.monotonic() - started
    started = time.monotonic()
    model = build_sam2(CONFIG, str(weights), device="cpu", mode="eval", apply_postprocessing=True)
    predictor = SAM2ImagePredictor(model, mask_threshold=0.0, max_hole_area=0.0,
                                  max_sprinkle_area=0.0)
    run = {"purpose": "Unqualified SAM box-refinement diagnostic",
           "cases_manifest_sha256": sha(args.cases), "cases": envelope["cases"],
           "code_revision": CODE_REVISION, "model_repo": MODEL_REPO,
           "model_revision": MODEL_REVISION, "weights_sha256": WEIGHT_SHA,
           "config": CONFIG, "platform": platform.platform(), "device": "cpu",
           "threads": args.threads, "multimask_output": args.multimask,
           "mask_threshold": 0.0, "max_hole_area": 0.0, "max_sprinkle_area": 0.0,
           "apply_model_postprocessing": True, "mask_clipped_to_prompt": False,
           "point_prompts": False, "new_paid_calls": 0,
           "reading_order_evaluated": False, "package_provenance": provenance,
           "packages": {name: importlib.metadata.version(name) for name in
                        ["SAM-2", "torch", "torchvision", "numpy", "Pillow", "hydra-core"]},
           "import_seconds": import_seconds, "model_load_seconds": time.monotonic() - started,
           "predictor_source_sha256": sha(Path(sam2.__file__).parent / "sam2_image_predictor.py")}
    save_json(args.output / "run.json", run)
    completed = []
    for source_sha, cases in groups.items():
        with Image.open(cases[0][1]) as opened:
            if opened.getexif().get(274, 1) != 1:
                raise ValueError("Nontrivial EXIF orientation needs an explicit source transform")
            image = opened.convert("RGB")
        width, height = image.size
        started = time.monotonic()
        with torch.inference_mode():
            predictor.set_image(np.array(image, copy=True))
        embedding_seconds = time.monotonic() - started
        print(f"Embedded {source_sha[:12]} once for {len(cases)} proposal sets", flush=True)
        for case, _, proposal in cases:
            folder = args.output / case["id"]
            folder.mkdir()
            boxes = proposal_boxes(proposal, width, height)
            records = []
            for row in boxes:
                index = row["order"]
                prompt = np.asarray(row["box_xyxy"], dtype=np.float32)
                started = time.monotonic()
                with torch.inference_mode():
                    logits, scores, low_logits = predictor.predict(
                        box=prompt, multimask_output=args.multimask,
                        return_logits=True, normalize_coords=True)
                prediction_seconds = time.monotonic() - started
                if logits.ndim != 3 or logits.shape[1:] != (height, width):
                    raise ValueError("SAM returned unexpected source-coordinate mask dimensions")
                if len(scores) != len(logits) or not all(np.isfinite(a).all()
                                                        for a in [logits, scores, low_logits]):
                    raise ValueError("Invalid SAM output alignment/numerics")
                native_name = f"target-{index:02}-native.npz"
                np.savez_compressed(folder / native_name, source_logits=logits,
                                    low_resolution_logits=low_logits, predicted_iou=scores,
                                    prompt_xyxy=prompt)
                candidates = []
                x0, y0, x1, y1 = row["box_xyxy"]
                for candidate, (logit, score) in enumerate(zip(logits, scores)):
                    mask = logit > 0.0
                    mask_image = Image.fromarray(mask.astype("uint8") * 255)
                    bounds = mask_image.getbbox()
                    prefix = f"target-{index:02}-mask-{candidate}"
                    mask_image.save(folder / (prefix + ".png"))
                    alpha = mask_image.point(lambda x: 80 if x else 0)
                    overlay = image.convert("RGBA")
                    ink = Image.new("RGBA", image.size, (0, 180, 255, 0))
                    ink.putalpha(alpha)
                    overlay = Image.alpha_composite(overlay, ink).convert("RGB")
                    draw = ImageDraw.Draw(overlay)
                    draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline="red", width=2)
                    overlay.save(folder / (prefix + "-overlay.jpg"), quality=95)
                    area = int(mask.sum())
                    inside = int(mask[y0:y1, x0:x1].sum())
                    item = {"candidate": candidate, "predicted_iou": float(score),
                            "mask_bounds_xyxy_half_open": bounds, "mask_pixels": area,
                            "inside_original_box_pixels": inside, "outside_original_box_pixels": area - inside,
                            "outside_fraction": (area - inside) / area if area else None,
                            "box_mask_coverage": inside / ((x1 - x0) * (y1 - y0)),
                            "empty_mask": not area}
                    if bounds:
                        bx0, by0, bx1, by1 = bounds
                        union = [min(x0, bx0), min(y0, by0), max(x1, bx1), max(y1, by1)]
                        item["outward_extension_ltrb_pixels"] = [max(0, x0 - bx0), max(0, y0 - by0),
                                                                max(0, bx1 - x1), max(0, by1 - y1)]
                        item["diagnostic_union_window_xyxy"] = union
                        image.crop(union).save(folder / (prefix + "-union-window.png"))
                    candidates.append(item)
                records.append({**row, "prediction_seconds": prediction_seconds,
                                "native_file": native_name, "native_sha256": sha(folder / native_name),
                                "candidates": candidates})
                print(f'{case["id"]} target {index}/{len(boxes)}: {prediction_seconds:.3f}s', flush=True)
            record = {"case": case, "source_dimensions": [width, height],
                      "source_sha256": source_sha, "embedding_seconds_shared": embedding_seconds,
                      "embedding_reused_across_cases": len(cases), "regions": records,
                      "process_lifetime_maxrss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      "maxrss_units": "bytes" if platform.system() == "Darwin" else "KiB"}
            save_json(folder / "result.json", record)
            completed.append(case["id"])
    save_json(args.output / "complete.json", {"completed_cases": completed,
                                              "unique_source_embeddings": len(groups),
                                              "new_paid_calls": 0})


if __name__ == "__main__":
    main()
