"""Automatic semantic-point SAM spike. CPU VM only; no API or manual prompts."""
import argparse
import importlib.metadata
import importlib.util
import json
import math
import platform
import re
import resource
import time
from collections import defaultdict
from pathlib import Path

CORE_PATH = Path(__file__).resolve().parent.parent / "sam2_refiner_v1" / "probe.py"
spec = importlib.util.spec_from_file_location("sam2_box_spike", CORE_PATH)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def validate_points(manifest, source_sha, width, height, orders):
    """Validate normalized ownership points without dependencies or model calls."""
    if manifest.get("version") != 1 or manifest.get("source_sha256") != source_sha:
        raise ValueError("Point manifest version/source mismatch")
    if width <= 0 or height <= 0:
        raise ValueError("Source dimensions must be positive")
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("Point scenes must be a list")
    parsed, occupied = {}, {}
    for scene in scenes:
        order, uncertain = scene.get("order"), scene.get("uncertain")
        if type(order) is not int or order <= 0 or order in parsed:
            raise ValueError("Duplicate or invalid scene order")
        if type(uncertain) is not bool:
            raise ValueError("Scene uncertainty must be explicit boolean")
        raw_points = scene.get("exclusive_points")
        if not isinstance(raw_points, list) or len(raw_points) > 3:
            raise ValueError("Expected at most three exclusive points per scene")
        if not uncertain and not raw_points:
            raise ValueError("Unambiguous scene must supply at least one point")
        points = []
        for point in raw_points:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError("Expected point [x,y]")
            if any(type(value) not in (int, float) or not math.isfinite(value)
                   or not 0 < value < 1000 for value in point):
                raise ValueError("Point must be finite and strictly inside normalized source boundaries")
            x, y = point[0] * width / 1000, point[1] * height / 1000
            pixel = (math.floor(x), math.floor(y))
            if pixel in occupied:
                raise ValueError("Duplicate pixel or contradictory scene ownership")
            occupied[pixel] = order
            points.append({"normalized_xy": point, "source_xy": [x, y],
                           "lookup_pixel_xy": list(pixel), "owner_order": order})
        parsed[order] = {"order": order, "uncertain": uncertain, "points": points}
    if set(parsed) != set(orders):
        raise ValueError("Point scene inventory differs from cached automatic inventory")
    return parsed


def select_prompts(target, scenes, baseline_contains):
    """Positives belong to target; negatives are owned rival points in its mask."""
    own = scenes[target]
    if own["uncertain"]:
        return {"status": "abstain_uncertain_target", "positives": [], "negatives": []}
    negatives = []
    for order in sorted(scenes):
        scene = scenes[order]
        if order == target or scene["uncertain"]:
            continue
        for point in scene["points"]:
            if baseline_contains(*point["lookup_pixel_xy"]):
                negatives.append(point)
    return {"status": "prompted", "positives": own["points"], "negatives": negatives}


def load_case_inputs(path):
    envelope = json.loads(path.read_text())
    if envelope.get("version") != 1 or not envelope.get("cases"):
        raise ValueError("Expected nonempty version-1 case manifest")
    groups, seen, source_point_hashes = defaultdict(list), set(), {}
    for case in envelope["cases"]:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", case["id"]) or case["id"] in seen:
            raise ValueError("Case IDs must be unique safe directory names")
        seen.add(case["id"])
        paths = {name: core.checked_file(path.parent, case[name], case[name + "_sha256"])
                 for name in ("source", "proposals", "points", "baseline_result")}
        data = {name: json.loads(paths[name].read_text())
                for name in ("proposals", "points", "baseline_result")}
        baseline = data["baseline_result"]
        if (baseline["source_sha256"] != case["source_sha256"] or
                baseline["case"]["proposals_sha256"] != case["proposals_sha256"]):
            raise ValueError("Baseline is not for this exact source/proposal artifact")
        point_hash = source_point_hashes.setdefault(case["source_sha256"], case["points_sha256"])
        if point_hash != case["points_sha256"]:
            raise ValueError("A source must reuse exactly one ownership-point manifest")
        source_image = data["proposals"].get("images", [{}])[0]
        if source_image.get("sha256") != case["source_sha256"]:
            raise ValueError("Exact saved automatic bundle/source binding required")
        groups[case["source_sha256"]].append((case, paths, data))
    return envelope, groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--weights-dir", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--omit-box", action="store_true",
                        help="Separate ablation: retain saved box for diagnostics, prompt with points only")
    args = parser.parse_args()
    if not 1 <= args.threads <= 8:
        raise ValueError("Expected 1..8 CPU threads")
    envelope, groups = load_case_inputs(args.cases)
    args.output.mkdir(parents=True, exist_ok=False)
    weights = core.weights_at(args.weights_dir)
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
    if (provenance or {}).get("vcs_info", {}).get("commit_id") != core.CODE_REVISION:
        raise ValueError("Install SAM-2 from the exact pinned git URL")
    import_seconds = time.monotonic() - started
    started = time.monotonic()
    model = build_sam2(core.CONFIG, str(weights), device="cpu", mode="eval", apply_postprocessing=True)
    predictor = SAM2ImagePredictor(model, mask_threshold=0.0, max_hole_area=0.0, max_sprinkle_area=0.0)
    core.save_json(args.output / "run.json", {
        "purpose": "Unqualified automatic semantic-point ownership spike",
        "cases_manifest_sha256": core.sha(args.cases), "cases": envelope["cases"],
        "runner_sha256": core.sha(Path(__file__)), "box_helper_sha256": core.sha(CORE_PATH),
        "code_revision": core.CODE_REVISION, "model_repo": core.MODEL_REPO,
        "model_revision": core.MODEL_REVISION, "weights_sha256": core.WEIGHT_SHA,
        "config": core.CONFIG, "device": "cpu", "platform": platform.platform(),
        "threads": torch.get_num_threads(), "multimask_output": False,
        "box_prompt_supplied": not args.omit_box,
        "mask_threshold": 0.0, "max_hole_area": 0.0, "max_sprinkle_area": 0.0,
        "apply_model_postprocessing": True, "mask_clipped_to_prompt": False,
        "new_paid_calls_by_runner": 0, "point_generation_cost": "accounted separately",
        "package_provenance": provenance,
        "packages": {name: importlib.metadata.version(name) for name in
                     ["SAM-2", "torch", "torchvision", "numpy", "Pillow", "hydra-core"]},
        "import_seconds": import_seconds, "model_load_seconds": time.monotonic() - started,
        "predictor_source_sha256": core.sha(Path(sam2.__file__).parent / "sam2_image_predictor.py")})
    completed = []
    for source_sha, cases in groups.items():
        with Image.open(cases[0][1]["source"]) as opened:
            if opened.getexif().get(274, 1) != 1:
                raise ValueError("Nontrivial EXIF orientation requires explicit mapping")
            image = opened.convert("RGB")
        width, height = image.size
        # Validate every point/proposal set before embedding this source.
        prepared = []
        for case, paths, data in cases:
            boxes = core.proposal_boxes(data["proposals"], width, height)
            if not all(box["crop_extent_exact"] for box in boxes):
                raise ValueError("Exact saved integer bundle extents required")
            scenes = validate_points(data["points"], source_sha, width, height,
                                     [box["order"] for box in boxes])
            baseline_rows = data["baseline_result"]["regions"]
            if [row["order"] for row in baseline_rows] != [row["order"] for row in boxes]:
                raise ValueError("Baseline target inventory/order mismatch")
            if data["baseline_result"]["source_dimensions"] != [width, height]:
                raise ValueError("Baseline source dimensions mismatch")
            for row, baseline in zip(boxes, baseline_rows):
                if row["box_xyxy"] != baseline["box_xyxy"] or not baseline["crop_extent_exact"]:
                    raise ValueError("Baseline uses different or approximate box extents")
            prepared.append((case, paths, boxes, scenes, baseline_rows))
        started = time.monotonic()
        with torch.inference_mode():
            predictor.set_image(np.array(image, copy=True))
        embedding_seconds = time.monotonic() - started
        print(f"Embedded {source_sha[:12]} once for {len(cases)} cases", flush=True)
        for case, paths, boxes, scenes, baseline_rows in prepared:
            folder = args.output / case["id"]
            folder.mkdir()
            records = []
            for row, baseline in zip(boxes, baseline_rows):
                index = row["order"]
                baseline_native = core.checked_file(paths["baseline_result"].parent,
                                                    baseline["native_file"], baseline["native_sha256"])
                with np.load(baseline_native, allow_pickle=False) as native:
                    source_logits = native["source_logits"]
                    if source_logits.shape != (1, height, width) or not np.isfinite(source_logits).all():
                        raise ValueError("Baseline must contain one finite full-source mask")
                    if native["prompt_xyxy"].tolist() != row["box_xyxy"]:
                        raise ValueError("Baseline native prompt geometry mismatch")
                    baseline_mask = source_logits[0] > 0.0
                prompts = select_prompts(index, scenes, lambda x, y: bool(baseline_mask[y, x]))
                record = {**row, **prompts, "baseline_native_sha256": baseline["native_sha256"],
                          "candidates": []}
                if prompts["status"] != "prompted":
                    records.append(record)
                    print(f'{case["id"]} target {index}: abstained (uncertain ownership)', flush=True)
                    continue
                points = np.asarray([p["source_xy"] for p in prompts["positives"] + prompts["negatives"]],
                                    dtype=np.float32)
                if ((points[:, 0] <= 0) | (points[:, 0] >= width) |
                        (points[:, 1] <= 0) | (points[:, 1] >= height)).any():
                    raise ValueError("Float32 SAM point conversion reached a source boundary")
                labels = np.asarray([1] * len(prompts["positives"]) + [0] * len(prompts["negatives"]),
                                    dtype=np.int32)
                prompt_box = np.asarray(row["box_xyxy"], dtype=np.float32)
                started = time.monotonic()
                with torch.inference_mode():
                    logits, scores, low_logits = predictor.predict(
                        box=None if args.omit_box else prompt_box,
                        point_coords=points, point_labels=labels,
                        multimask_output=False, return_logits=True, normalize_coords=True)
                seconds = time.monotonic() - started
                if logits.shape != (1, height, width) or scores.shape != (1,):
                    raise ValueError("Frozen single-mask output contract failed")
                if not all(np.isfinite(a).all() for a in (logits, scores, low_logits)):
                    raise ValueError("Nonfinite SAM output")
                prefix = f"target-{index:02}"
                native_name = prefix + "-native.npz"
                np.savez_compressed(folder / native_name, source_logits=logits,
                                    low_resolution_logits=low_logits, predicted_iou=scores,
                                    prompt_xyxy=prompt_box, point_coords_xy=points, point_labels=labels)
                mask = logits[0] > 0.0
                mask_image = Image.fromarray(mask.astype("uint8") * 255)
                mask_image.save(folder / (prefix + "-mask.png"))
                bounds = mask_image.getbbox()
                overlay = image.convert("RGBA")
                ink = Image.new("RGBA", image.size, (0, 180, 255, 0))
                ink.putalpha(mask_image.point(lambda x: 80 if x else 0))
                overlay = Image.alpha_composite(overlay, ink).convert("RGB")
                draw = ImageDraw.Draw(overlay)
                x0, y0, x1, y1 = row["box_xyxy"]
                draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline="red", width=2)
                for point, label in zip(points, labels):
                    x, y = map(float, point)
                    draw.ellipse([x - 4, y - 4, x + 4, y + 4], outline="lime" if label else "magenta", width=2)
                overlay.save(folder / (prefix + "-overlay.jpg"), quality=95)
                area, inside = int(mask.sum()), int(mask[y0:y1, x0:x1].sum())
                candidate = {"candidate": 0, "predicted_iou": float(scores[0]),
                             "mask_bounds_xyxy_half_open": bounds, "mask_pixels": area,
                             "outside_original_box_pixels": area - inside,
                             "added_vs_baseline_pixels": int((mask & ~baseline_mask).sum()),
                             "removed_vs_baseline_pixels": int((baseline_mask & ~mask).sum()),
                             "positive_points_retained": [bool(mask[p["lookup_pixel_xy"][1], p["lookup_pixel_xy"][0]])
                                                          for p in prompts["positives"]],
                             "negative_points_excluded": [not bool(mask[p["lookup_pixel_xy"][1], p["lookup_pixel_xy"][0]])
                                                         for p in prompts["negatives"]]}
                if bounds:
                    bx0, by0, bx1, by1 = bounds
                    union = [min(x0, bx0), min(y0, by0), max(x1, bx1), max(y1, by1)]
                    candidate["diagnostic_union_window_xyxy"] = union
                    image.crop(union).save(folder / (prefix + "-union-window.png"))
                record.update(prediction_seconds=seconds, native_file=native_name,
                              native_sha256=core.sha(folder / native_name), candidates=[candidate])
                records.append(record)
                print(f'{case["id"]} target {index}/{len(boxes)}: '
                      f'{len(prompts["positives"])} positive, {len(prompts["negatives"])} negative, {seconds:.3f}s', flush=True)
            core.save_json(folder / "result.json", {
                "case": case, "source_sha256": source_sha, "source_dimensions": [width, height],
                "embedding_seconds_shared": embedding_seconds, "embedding_reused_across_cases": len(cases),
                "regions": records, "prompted_targets": sum(r["status"] == "prompted" for r in records),
                "abstained_targets": sum(r["status"] != "prompted" for r in records),
                "process_lifetime_maxrss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "maxrss_units": "bytes" if platform.system() == "Darwin" else "KiB"})
            completed.append(case["id"])
    core.save_json(args.output / "complete.json", {"completed_cases": completed,
                                                  "unique_source_embeddings": len(groups),
                                                  "new_paid_calls_by_runner": 0})


if __name__ == "__main__":
    main()
