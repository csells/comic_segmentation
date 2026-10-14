"""Image-only hidden-gutter risk and regional detection reconciliation.

Risk flags are not automatic split coordinates. Only an independent detector
provides replacement geometry; all resulting pages must pass normal checks.
"""
import copy
import math
import numpy as np
from PIL import Image

def edge_gutters(path):
    a=np.asarray(Image.open(path).convert('RGB'));mask=np.min(a,axis=2)>240
    findings=[]
    for axis,m in [('vertical',mask),('horizontal',mask.T)]:
        h,w=m.shape
        if min(h,w)<40:continue
        for side,v in [('start',m),('end',m[::-1])]:
            # Ignore outer white padding, but do not search far into the scene.
            row=next((i for i in range(max(1,int(h*.05))) if v[i].mean()<.9),None)
            if row is None:continue
            line=np.all(v[row:row+max(2,round(h*.01))],axis=0)
            padded=np.r_[False,line,False].astype(int);changes=np.diff(padded)
            for left,right in zip(np.where(changes==1)[0],np.where(changes==-1)[0]):
                fraction=(right-left)/w
                if left<w*.1 or right>w*.9 or not .01<=fraction<=.05:continue
                whiteness=float(m[:,left:right].mean())
                if whiteness<.6:continue
                findings.append({'axis':axis,'side':side,'position':round((left+right)/2/w,4),
                    'width_fraction':round(fraction,4),'white_fraction':round(whiteness,4)})
    return findings


def intersection(a,b):
    return [max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]


def area(box):
    return max(0,box[2]-box[0])*max(0,box[3]-box[1])


def iou(a,b):
    overlap=area(intersection(a,b));union=area(a)+area(b)-overlap
    return overlap/union if union else 0.0


def reconcile_regions(value,target_order,regional,pixel_bounds,page_size,confirmed_context=None):
    """Map model boxes from the exact crop back to the original source page.

    Existing neighboring scenes may occur inside an irregular target's bounding
    rectangle. Match them against their visible intersection with that rectangle,
    not against their full off-crop bounds. With fewer than two unmatched scenes,
    retain the original target unchanged, including its precise reviewed bounds.
    """
    if regional['classification']!='panels':return copy.deepcopy(value),{'replaced':False,'context_matches':[]}
    original=next(p for p in value['panels'] if p['order']==target_order)
    left,top,right,bottom=pixel_bounds;width,height=page_size
    crop_box=[top*1000/height,left*1000/width,bottom*1000/height,right*1000/width]
    remaining=[];matches=[]
    for panel in sorted(regional['panels'],key=lambda p:p['order']):
        y,x,b,r=panel['box']
        mapped=[math.floor((top+y*(bottom-top)/1000)*1000/height),
                math.floor((left+x*(right-left)/1000)*1000/width),
                math.ceil((top+b*(bottom-top)/1000)*1000/height),
                math.ceil((left+r*(right-left)/1000)*1000/width)]
        mapped=[max(0,min(1000,n)) for n in mapped]
        context=[p for p in value['panels'] if p['order']!=target_order and
                 iou(mapped,intersection(p['box'],crop_box))>=.5]
        if confirmed_context and panel['order'] in confirmed_context:
            match=next(p for p in value['panels'] if p['order']==confirmed_context[panel['order']])
            if match['order']==target_order or area(intersection(mapped,match['box']))/max(1,area(mapped))<.9:
                raise ValueError('regional context match is not spatially supported')
            context=[match]
        if context:
            matches.append({'regional_order':panel['order'],'existing_orders':[p['order'] for p in context]})
        else:remaining.append({**panel,'box':mapped})
    if len(remaining)<2:return copy.deepcopy(value),{'replaced':False,'context_matches':matches}
    result=copy.deepcopy(value);panels=[]
    for p in result['panels']:
        panels.extend(remaining if p['order']==target_order else [p])
    for number,p in enumerate(panels,1):p['order']=number
    result['panels']=panels
    return result,{'replaced':True,'old_panel':original,'replacement_count':len(remaining),'replacement_boxes':[p['box'] for p in remaining],'context_matches':matches}
