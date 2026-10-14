"""Offline diagnostic over saved automatic candidates; no API or publication."""
import argparse,json,math
from pathlib import Path
import numpy as np
from PIL import Image
from frame_refine import expand_frame_boxes

def main():
 p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False,parents=True)
 allchanges=[]
 for file in sorted(a.run.glob('page-*.json')):
  d=json.loads(file.read_text());c=d['selected']
  if not c or c['panels']['classification']!='panels':continue
  bundle=json.loads(Path(c['bundle']).read_text());im=Image.open(bundle['images'][0]['path']).convert('RGB');rgb=np.asarray(im);w,h=im.size
  boxes=[[round(v['box'][1]*w/1000),round(v['box'][0]*h/1000),round(v['box'][3]*w/1000),round(v['box'][2]*h/1000)] for v in c['panels']['panels']]
  result,changes=expand_frame_boxes(rgb,boxes)
  if changes:
   folder=a.output/file.stem;folder.mkdir();records=[]
   for change in changes:
    i=change['index'];im.crop(tuple(result[i])).save(folder/f'crop-{i+1:02d}.jpg',quality=95)
    records.append(change)
   allchanges.append({'page':int(file.stem.split('-')[1]),'changes':records});print(file.stem,[(c['index']+1,c['after_pixels']) for c in changes],flush=True)
 (a.output/'scan.json').write_text(json.dumps(allchanges,indent=2)+'\n')
 print('Changed pages',len(allchanges),'crops',sum(len(v['changes']) for v in allchanges),flush=True)
if __name__=='__main__':main()
