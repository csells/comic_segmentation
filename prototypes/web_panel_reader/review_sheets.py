"""Produce numbered review overlays from saved manifests, without model calls.

Run in the disposable VM. Images and per-page review evidence stay outside Git.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

p=argparse.ArgumentParser()
p.add_argument('manifest', type=Path)
p.add_argument('images', type=Path)
p.add_argument('output', type=Path)
a=p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
pages=json.loads(a.manifest.read_text())['pages']
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
colors=['#ff2040','#00dfff','#ffff00','#ff40ff','#00ff60','#ff9000']
tiles=[]
for page in pages:
    n=page['source_page']
    im=Image.open(a.images/page['source_image']).convert('RGB')
    im.thumbnail((600,876))
    sx=im.width/page['width']; sy=im.height/page['height']
    tile=Image.new('RGB',(620,916),'#202020')
    tile.paste(im,(10,30)); d=ImageDraw.Draw(tile)
    d.text((10,5),f"PDF {n} | saved regions {page['frame_count']}",font=font,fill='white')
    for i,frame in enumerate(page['frames']):
        pts=[tuple(map(int,pair.split(','))) for pair in frame.split()]
        xy=[(round(x*sx)+10,round(y*sy)+30) for x,y in pts]
        c=colors[i%len(colors)]
        d.line(xy+[xy[0]],fill=c,width=2)
        x,y=xy[0]; d.rectangle((x,y,x+24,y+23),fill='#000000')
        d.text((x+3,y),str(i+1),font=font,fill=c)
    tile.save(a.output/f'page-{n:04d}.jpg',quality=94)
    tiles.append(tile)
    if len(tiles)==4 or n==pages[-1]['source_page']:
        sheet=Image.new('RGB',(1240,1832),'#202020')
        for j,t in enumerate(tiles):sheet.paste(t,((j%2)*620,(j//2)*916))
        sheet.save(a.output/f'sheet-{n-len(tiles)+1:04d}-{n:04d}.jpg',quality=94)
        tiles=[]
print('Saved',len(pages),'page overlays to',a.output)
