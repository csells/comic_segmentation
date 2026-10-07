#!/usr/bin/env python3
"""Reproduce the Kumiko synthetic compatibility probe in an empty scratch folder.

This is a research fixture generator, not application implementation. It does not
read user images or invoke cloud services. Run from a fresh temporary directory:

  probe_dir=$(mktemp -d /tmp/kumiko-probe.XXXXXX)
  uv venv "$probe_dir/venv"
  uv pip install --python "$probe_dir/venv/bin/python" \
    opencv-python-headless==4.14.0.94 numpy==2.5.3 requests==2.34.2
  "$probe_dir/venv/bin/python" /absolute/path/kumiko-synthetic-probe.py "$probe_dir"

For the recorded OpenCV 5 failure, use a second fresh directory and substitute
opencv-python-headless==5.0.0.93. Original observations used Python 3.13.12 on
macOS arm64. Source pin: njean42/kumiko at
9d587ae9498bc84dfda06fc19c6ad89f421bec14 (AGPL-3.0-or-later).

The script downloads only the pinned upstream source files and generates three
800x1000 synthetic pages. Existing output paths are rejected, never overwritten.
Results report behavior without asserting overall detector quality.
"""

import json
import platform
import subprocess
import sys
import urllib.request
from pathlib import Path

import cv2 as cv
import numpy as np


PIN = "9d587ae9498bc84dfda06fc19c6ad89f421bec14"
FILES = (
    "LICENSE", "kumiko", "kumikolib.py", "lib/page.py", "lib/panel.py",
    "lib/segment.py", "lib/debug.py", "lib/html.py",
)


def main():
    root = Path(sys.argv[1]).resolve()
    source = root / "kumiko"
    fixtures = root / "fixtures"
    source.mkdir()
    fixtures.mkdir()
    for name in FILES:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://raw.githubusercontent.com/njean42/kumiko/{PIN}/{name}"
        with urllib.request.urlopen(url, timeout=30) as response:
            with target.open("xb") as output:
                output.write(response.read())

    grid = np.full((1000, 800, 3), 255, np.uint8)
    for x, y, right, bottom in (
        (30, 30, 370, 460), (430, 30, 770, 460),
        (30, 540, 370, 970), (430, 540, 770, 970),
    ):
        cv.rectangle(grid, (x, y), (right, bottom), (150, 150, 150), -1)
        cv.rectangle(grid, (x, y), (right, bottom), (0, 0, 0), 5)
    bridged = grid.copy()
    cv.rectangle(bridged, (340, 200), (465, 275), (0, 0, 0), -1)
    inset = np.full((1000, 800, 3), 255, np.uint8)
    cv.rectangle(inset, (30, 30), (770, 970), (120, 120, 120), -1)
    cv.rectangle(inset, (30, 30), (770, 970), (0, 0, 0), 5)
    cv.rectangle(inset, (480, 80), (730, 350), (255, 255, 255), -1)
    cv.rectangle(inset, (490, 90), (720, 340), (20, 20, 20), 5)
    for name, image in {"grid": grid, "broken-gutter": bridged, "inset": inset}.items():
        encoded, data = cv.imencode(".png", image)
        if not encoded:
            raise RuntimeError(f"Could not encode {name}")
        with (fixtures / f"{name}.png").open("xb") as output:
            output.write(data.tobytes())

    results = []
    for name, direction in (
        ("grid", "ltr"), ("grid", "rtl"), ("broken-gutter", "ltr"), ("inset", "ltr"),
    ):
        args = [sys.executable, str(source / "kumiko"), "-i", str(fixtures / f"{name}.png")]
        if direction == "rtl":
            args.append("--rtl")
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=20)
            item = {
                "fixture": name, "direction": direction, "exit": result.returncode,
                "stderr": result.stderr,
                "output": json.loads(result.stdout) if result.returncode == 0 else result.stdout,
            }
        except subprocess.TimeoutExpired:
            item = {"fixture": name, "direction": direction, "timeout_seconds": 20}
        results.append(item)
    evidence = {
        "source_pin": PIN, "python": platform.python_version(),
        "platform": platform.platform(), "cv2": cv.__version__, "results": results,
    }
    with (root / "runtime-results.json").open("x") as output:
        json.dump(evidence, output, indent=2)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
