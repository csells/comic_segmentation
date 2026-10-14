"""Diagnostic YOLO26 end-to-end ONNX panel boxes; no reading-order claim."""
import argparse,hashlib,json,time
from pathlib import Path
import cv2,numpy as np,onnxruntime as ort
from PIL import Image,ImageDraw
p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('images',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir()
options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
s=ort.InferenceSession(str(a.model),sess_options=options,providers=['CPUExecutionProvider'])
assert s.get_inputs()[0].shape==[1,3,640,640] and s.get_outputs()[0].shape==[1,300,6]
(a.output/'run.json').write_text(json.dumps({'model_sha256':hashlib.sha256(a.model.read_bytes()).hexdigest(),'metadata':s.get_modelmeta().custom_metadata_map,'preprocess':'RGB float32 /255, centered 640 square letterbox gray114, cv2 linear resize','confidence':0.25,'class':0,'ordering':'confidence, not reading order'},indent=2))
results=[]
for i,page in enumerate([5,25,254,256],1):
 print(f'[{i}/4] PDF {page}: YOLO26 inference',flush=True);src=a.images/f'{page:04}.jpg';im=Image.open(src).convert('RGB');w,h=im.size;ratio=min(640/w,640/h);nw,nh=round(w*ratio),round(h*ratio);left,top=round((640-nw)/2-.1),round((640-nh)/2-.1)
 resized=cv2.resize(np.array(im),(nw,nh),interpolation=cv2.INTER_LINEAR);tensor=np.full((640,640,3),114,dtype=np.uint8);tensor[top:top+nh,left:left+nw]=resized;inp=np.ascontiguousarray(tensor.transpose(2,0,1)[None],dtype=np.float32)/255
 start=time.monotonic();raw=s.run(None,{'images':inp})[0];elapsed=time.monotonic()-start;np.save(a.output/f'{page}-raw.npy',raw)
 boxes=[]
 for x1,y1,x2,y2,conf,cls in raw[0]:
  if conf<.25 or int(cls)!=0:continue
  box=[max(0,min(w,float((x1-left)/ratio))),max(0,min(h,float((y1-top)/ratio))),max(0,min(w,float((x2-left)/ratio))),max(0,min(h,float((y2-top)/ratio)))];boxes.append({'box':box,'confidence':float(conf)})
 overlay=im.copy();draw=ImageDraw.Draw(overlay)
 for n,b in enumerate(boxes,1):
  draw.rectangle(b['box'],outline='red',width=3);draw.text(tuple(b['box'][:2]),str(n),fill='red',font_size=22)
 overlay.save(a.output/f'{page}-overlay.jpg',quality=95)
 result={'source_page':page,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'boxes':boxes,'elapsed_seconds':elapsed,'status':'unreviewed'};results.append(result);(a.output/'results.json').write_text(json.dumps(results,indent=2));print(f'[{i}/4] PDF {page}: {len(boxes)} panels, {elapsed:.3f}s',flush=True)
