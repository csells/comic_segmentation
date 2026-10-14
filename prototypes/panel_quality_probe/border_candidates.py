"""Offline border evidence for model proposals, never semantic panel acceptance."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np


def candidates(image):
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    h,w=gray.shape
    edges=cv2.Canny(gray,50,150)
    lines=cv2.HoughLinesP(edges,1,np.pi/180,60,
        minLineLength=min(w,h)*.07,maxLineGap=20)
    hs,vs=[],[]
    if lines is not None:
        for x1,y1,x2,y2 in lines.reshape(-1,4):
            if abs(y2-y1)<=max(3,abs(x2-x1)*.012):
                hs.append([int((y1+y2)/2),int(min(x1,x2)),int(max(x1,x2))])
            elif abs(x2-x1)<=max(3,abs(y2-y1)*.012):
                vs.append([int((x1+x2)/2),int(min(y1,y2)),int(max(y1,y2))])
    def merge(lines):
        result=[]
        for v,lo,hi in sorted(lines,key=lambda x:x[2]-x[1],reverse=True):
            for old in result:
                if abs(v-old[0])<=5 and min(hi,old[2])-max(lo,old[1])>=-20:
                    old[1]=min(lo,old[1]);old[2]=max(hi,old[2]);break
            else: result.append([v,lo,hi])
        return result
    hs,vs=merge(hs),merge(vs)
    mask=np.zeros_like(gray)
    for y,x1,x2 in hs:cv2.line(mask,(x1,y),(x2,y),255,2)
    for x,y1,y2 in vs:cv2.line(mask,(x,y1),(x,y2),255,2)
    rectangles=[]
    near=cv2.dilate(edges,np.ones((7,7),np.uint8))>0
    def add(box):
        x,y,r,b=box
        if r-x<w*.12 or b-y<h*.08 or (r-x)*(b-y)<w*h*.015:return
        def coverage(values):return float(np.mean(values)) if values.size else 0.
        scores=[1. if y<3 else coverage(near[y,x:r]),
                1. if b>=h-3 else coverage(near[b,x:r]),
                1. if x<3 else coverage(near[y:b,x]),
                1. if r>=w-3 else coverage(near[y:b,r])]
        if sum(v>.85 for v in scores)<3:return
        if any(max(abs(a-z) for a,z in zip(box,old))<12 for old in rectangles):return
        rectangles.append(box)
    # Parallel edge evidence tolerates an occluded endpoint; candidates still need
    # semantic verification because doors/windows also have parallel borders.
    for i,(y1,a1,b1) in enumerate(hs):
        for y2,a2,b2 in hs[i+1:]:
            if abs(a1-a2)<w*.06 and abs(b1-b2)<w*.06:
                add([min(a1,a2),min(y1,y2),max(b1,b2),max(y1,y2)])
    for i,(x1,a1,b1) in enumerate(vs):
        for x2,a2,b2 in vs[i+1:]:
            if abs(a1-a2)<h*.04 and abs(b1-b2)<h*.04:
                add([min(x1,x2),min(a1,a2),max(x1,x2),max(b1,b2)])
    # Image edge can complete a frame clipped by the scan.
    for x,y1,y2 in vs:
        if y1<h*.02 and .12*w<x<.9*w:
            for y,a,b in hs:
                if abs(y-y2)<h*.025 and abs(b-x)<w*.025 and a<w*.02:add([0,0,x,max(y,y2)])
    return rectangles,mask


def main():
    p=argparse.ArgumentParser();p.add_argument('--images',type=Path,required=True);p.add_argument('--pages',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    for page in map(int,a.pages.split(',')):
        im=cv2.imread(str(a.images/f'{page:04}.jpg')); boxes,mask=candidates(im)
        out=im.copy()
        for i,b in enumerate(boxes):
            x,y,r,bottom=b
            cv2.rectangle(out,(x,y),(r,bottom),(0,0,255),2)
            cv2.putText(out,str(i+1),(x+5,y+25),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,0,255),2)
        cv2.imwrite(str(a.output/f'{page:04}-candidates.jpg'),out)
        cv2.imwrite(str(a.output/f'{page:04}-lines.png'),mask)
        (a.output/f'{page:04}.json').write_text(json.dumps(boxes,indent=2)+'\n')
        print(f'PDF {page}: {len(boxes)} border candidates',flush=True)


if __name__=='__main__':main()
