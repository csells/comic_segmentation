"""Offline preparation in VM153; only source-derived viewport margins."""
import copy,hashlib,json,sys
from pathlib import Path
from PIL import Image
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
from viewport_refine import reading_viewports
from auto_convert import _rectangle
from gemini_probe import save

ROOT=Path('/home/tester/comic-reader')
OUTPUT=ROOT/'evidence/ownership-viewport-v2-20261009'
E=ROOT/'evidence'
CASES={
 'original150':(E/'full-sequential-v21-20261008/page-0150.json',None),
 'corrected150':(E/'crossing-art-regression-v23-20261009/page-0002.json',None),
 'final57':(E/'component-repair-regression-v28-20261009/page-0002.json',-1),
}


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def padded_bundle(bundle,out):
    out.mkdir(parents=True,exist_ok=False)
    source=Path(bundle['images'][0]['path'])
    assert sha(source)==bundle['images'][0]['sha256']
    with Image.open(source) as im:
        width,height=im.size
        value,changes=reading_viewports(bundle,width,height)
        images=[copy.deepcopy(bundle['images'][0])]
        for panel in value['panels']:
            y,x,b,r=panel['box']
            points=_rectangle({'x':x/1000,'y':y/1000,'w':(r-x)/1000,'h':(b-y)/1000},width,height)
            coords=[tuple(map(int,p.split(','))) for p in points.split()]
            left,top=coords[0];right,bottom=coords[2]
            crop=out/f'crop-{panel["order"]:02}.jpg'
            im.convert('RGB').crop((left,top,right+1,bottom+1)).save(crop,quality=95)
            images.append({'label':f'Candidate crop {panel["order"]} in reading order','path':str(crop),'sha256':sha(crop),'points':points})
    value['images']=images
    save(out/'changes.json',changes);save(out/'bundle.json',value)
    return value


def main():
    OUTPUT.mkdir(parents=True,exist_ok=False)
    records={}
    for name,(path,index) in CASES.items():
        d=json.loads(path.read_text())
        selected=d['selected'] if index is None else d['attempts'][index]['candidate']
        bundle=json.loads(Path(selected['bundle']).read_text())
        panels=selected['panels']['panels']
        assert [p['box'] for p in panels]==[p['box'] for p in bundle['panels']]
        bundle['panels']=[{k:p[k] for k in ('order','box','description')} for p in panels]
        save(OUTPUT/(name+'-bundle.json'),bundle)
        padded=padded_bundle(bundle,OUTPUT/(name+'-padded'))
        records[name]={'saved_outcome':str(path),'saved_outcome_sha256':sha(path),'detector_request':selected['detector'],
                       'source_sha256':bundle['images'][0]['sha256'],'bundle_sha256':sha(OUTPUT/(name+'-bundle.json')),
                       'padded_bundle_sha256':sha(OUTPUT/(name+'-padded')/'bundle.json')}
        print(name,len(bundle['panels']),'source-backed viewports prepared',flush=True)
    save(OUTPUT/'preparation.json',{'purpose':'Source-only scene audit and bounded reading margins; no inference yet','records':records})


if __name__=='__main__':main()
