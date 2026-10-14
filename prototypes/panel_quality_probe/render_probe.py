"""Render model output for human inspection, preserving original source images."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("images", type=Path)
    args = parser.parse_args()
    output = args.run / "review"
    output.mkdir(exist_ok=False)
    for result in json.loads((args.run / "results.json").read_text()):
        if result["status"] != "structurally_valid_unreviewed":
            continue
        page = result["source_page"]
        source = Image.open(args.images / f"{page:04}.jpg").convert("RGB")
        overlay = source.copy()
        draw = ImageDraw.Draw(overlay)
        panels = json.loads((args.run / f"page-{page:04}" / "panels.json").read_text())["panels"]
        crops = output / f"page-{page:04}-panels"
        crops.mkdir()
        for panel in panels:
            y1, x1, y2, x2 = panel["box"]
            box = (round(x1*source.width/1000), round(y1*source.height/1000),
                   round(x2*source.width/1000), round(y2*source.height/1000))
            color = ["#ff2255", "#00bbdd", "#ccbb00", "#ee33ee", "#11cc44"][(panel["order"]-1)%5]
            draw.rectangle(box, outline=color, width=3)
            x, y = box[:2]
            draw.rectangle((x,y,x+30,y+28), fill="black")
            draw.text((x+4,y+3), str(panel["order"]), fill=color, font_size=20)
            source.crop(box).save(crops / f"{panel['order']:02}.jpg", quality=95)
        overlay.save(output / f"page-{page:04}.jpg", quality=95)
        print(f"PDF {page}: {len(panels)} overlays/crops rendered")


if __name__ == "__main__":
    main()
