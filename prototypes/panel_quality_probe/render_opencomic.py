"""Render upstream component boxes; labels denote component index, not reading order."""
import argparse,json
from PIL import Image,ImageDraw
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('images',type=Path);a=p.parse_args();out=a.run/'review';out.mkdir()
for result in json.loads((a.run/'results.json').read_text()):
 page=result['source_page'];data=json.loads((a.run/f'page-{page:04}'/'detections.json').read_text());im=Image.open(a.images/f'{page:04}.jpg').convert('RGB');overlay=im.copy();d=ImageDraw.Draw(overlay)
 for n,b in enumerate(data['boxes'],1):
  box=[b['box'][0]*im.width/b['width'],b['box'][1]*im.height/b['height'],b['box'][2]*im.width/b['width'],b['box'][3]*im.height/b['height']];d.rectangle(box,outline='red',width=3);d.text(tuple(box[:2]),str(n),fill='red',font_size=24)
 overlay.save(out/f'{page}-overlay.jpg',quality=95)
print('Rendered original OpenComic component boxes without sorting or corrections')
