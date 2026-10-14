"""Diagnostic for narrow edge-reaching light gutters obscured by dialogue."""
import argparse
import json
from pathlib import Path
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

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    rows=[]
    for page in sorted(a.run.glob('page-*.json')):
        value=json.loads(page.read_text());candidate=value.get('selected')
        if not candidate or candidate['panels']['classification']!='panels':continue
        bundle=json.loads(Path(candidate['bundle']).read_text())
        for crop in bundle['images'][1:]:
            findings=edge_gutters(crop['path'])
            if findings:
                record={'page':value['page'],'target':int(crop['label'].split()[2]),'findings':findings,'crop':crop['path']}
                rows.append(record);print(json.dumps(record),flush=True)
    a.output.write_text(json.dumps(rows,indent=2));print('flagged regions',len(rows),flush=True)

if __name__=='__main__':main()
