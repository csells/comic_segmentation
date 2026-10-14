"""Diagnostic image-derived expansion for enclosed light balloons with ink holes.

This never supplies panel inventory/order and never shrinks a proposed crop.
White page/gutter components touching the image edge are excluded. Enclosed
light regions need several small dark holes (letter-like ink), and a majority
of their actual light pixels inside the proposed panel before expansion.
"""
import cv2
import numpy as np


def balloon_components(rgb):
    height,width=rgb.shape[:2]
    mask=(rgb.min(axis=2)>=230).astype('uint8')
    count,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
    candidates=[]
    for label,(x,y,w,h,area) in enumerate(stats[1:],1):
        if x==0 or y==0 or x+w==width or y+h==height:continue
        if min(w,h)<12 or area<width*height*.00015 or area>width*height*.06 or area/(w*h)<.35:continue
        component=(labels[y:y+h,x:x+w]==label).astype('uint8')
        contours,hierarchy=cv2.findContours(component,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None:continue
        holes=[]
        for contour,entry in zip(contours,hierarchy[0]):
            if entry[3]<0:continue
            bx,by,bw,bh=cv2.boundingRect(contour)
            # Closed dark holes substantially smaller than the balloon are
            # evidence of lettering, rather than an empty white object.
            if 2<=bw<=w*.3 and 3<=bh<=h*.5 and cv2.contourArea(contour)>=3:holes.append([bx,by,bw,bh])
        if len(holes)<3:continue
        candidates.append({'box':[int(x),int(y),int(x+w),int(y+h)],'label':label,'area':int(area),'ink_holes':len(holes)})
    return labels,candidates


def expand_balloon_boxes(rgb,boxes):
    height,width=rgb.shape[:2];labels,components=balloon_components(rgb)
    result=[list(b) for b in boxes];changes=[]
    for index,box in enumerate(boxes):
        l,t,r,b=box;matches=[]
        for c in components:
            x,y,rr,bb=c['box']
            if x>=l and y>=t and rr<=r and bb<=b:continue
            il,it,ir,ib=max(l,x),max(t,y),min(r,rr),min(b,bb)
            if ir<=il or ib<=it:continue
            coverage=float(np.count_nonzero(labels[it:ib,il:ir]==c['label']))/c['area']
            if coverage<.5:continue
            # Do not turn a local correction into a large layout change.
            if max(l-x,rr-r)>width*.05 or max(t-y,bb-b)>height*.05:continue
            matches.append({**c,'coverage':round(coverage,4)})
        if not matches:continue
        expanded=[max(0,min(l,*[c['box'][0]-3 for c in matches])),
                  max(0,min(t,*[c['box'][1]-3 for c in matches])),
                  min(width,max(r,*[c['box'][2]+3 for c in matches])),
                  min(height,max(b,*[c['box'][3]+3 for c in matches]))]
        if expanded!=list(box):
            result[index]=expanded;changes.append({'index':index,'before_pixels':list(box),'after_pixels':expanded,'components':matches,'method':'enclosed-lettered-light-component-v1'})
    return result,changes
