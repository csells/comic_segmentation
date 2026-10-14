"""Create ordered crop contact sheets for inspection; never change detector output."""
import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review', type=Path)
    args = parser.parse_args()
    output = args.review / 'contacts'
    output.mkdir(exist_ok=False)
    for folder in sorted(args.review.glob('page-*-panels')):
        crops = sorted(folder.glob('*.jpg'))
        for start in range(0, len(crops), 4):
            group = crops[start:start + 4]
            sheet = Image.new('RGB', (1128, 820 * math.ceil(len(group) / 2)), '#dddddd')
            draw = ImageDraw.Draw(sheet)
            for index, crop in enumerate(group):
                with Image.open(crop) as original:
                    im = original.convert('RGB')
                im.thumbnail((552, 780))
                x, y = (index % 2) * 564, (index // 2) * 820
                sheet.paste(im, (x + 6, y + 32))
                draw.text((x + 6, y + 4), f'{folder.name[:9]} panel {start + index + 1}',
                          fill='black', font_size=22)
            sheet.save(output / f'{folder.name[:9]}-{start + 1:02}.jpg', quality=95)
        print(f'{folder.name}: {len(crops)} ordered crops', flush=True)


if __name__ == '__main__':
    main()
