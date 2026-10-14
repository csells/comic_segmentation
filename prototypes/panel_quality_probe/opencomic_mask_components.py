"""Offline diagnostic: extract connected dark panel interiors from saved masks.

Unlike the upstream panel component routine, seed and traverse the same polarity.
Uses no comic-specific coordinates, manual corrections or fresh model calls.
"""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('images',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir();results=[]
for r in json.loads((a.run/'results.json').read_text()):
 page=r['source_page'];mask_path=a.run/f'page-{page:04}'/'mask-buffer.png';mask=np.array(Image.open(mask_path).convert('L'));n,labels,stats,_=cv2.connectedComponentsWithStats((mask<127).astype(np.uint8),connectivity=4)
 im=Image.open(a.images/f'{page:04}.jpg').convert('RGB');overlay=im.copy();d=ImageDraw.Draw(overlay);boxes=[]
 for x,y,w,h,area in stats[1:]:
  if area<50:continue
  box=[x*im.width/mask.shape[1],y*im.height/mask.shape[0],(x+w)*im.width/mask.shape[1],(y+h)*im.height/mask.shape[0]];boxes.append(box);d.rectangle(box,outline='red',width=3);d.text(tuple(box[:2]),str(len(boxes)),fill='red',font_size=24)
 overlay.save(a.output/f'{page}-overlay.jpg',quality=95);results.append({'source_page':page,'mask_source':str(mask_path),'boxes':boxes,'status':'unreviewed_components','ordering':'component scan order, not reading order'})
 print(page,len(boxes),flush=True)
(a.output/'results.json').write_text(json.dumps(results,indent=2));(a.output/'provenance.json').write_text(json.dumps({'fresh_inference':False,'manual_geometry':False,'rule':'4-connected mask<127; minimum50 model pixels; scale to source'},indent=2))
