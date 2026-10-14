"""Render diagnostic evidence from one completed automatic page; never changes it."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont


def source_page(run, ordinal):
    config=run/'run.json'
    config=json.loads(config.read_text()) if config.exists() else {}
    if 'source_pages' not in config:return ordinal,'legacy output ordinal; no source mapping recorded'
    mapping=config['source_pages']
    if (not isinstance(mapping,list) or any(type(n) is not int or n<1 for n in mapping)
            or len(set(mapping))!=len(mapping) or ordinal>len(mapping)):
        raise ValueError('Invalid run source_pages mapping; cannot label review evidence')
    return mapping[ordinal-1],'run.json.source_pages'


def verified_image(entry):
    path=Path(entry['path'])
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=entry['sha256']:raise ValueError('Review image changed: '+str(path))
    return path


def caption(image,lines,font):
    # Keep the diagnostic annotation visibly separate from original page pixels.
    width=max(image.width,1000);height=38*len(lines)+12
    result=Image.new('RGB',(width,image.height+height),'#303030')
    result.paste(image,(0,height));draw=ImageDraw.Draw(result)
    for i,line in enumerate(lines):draw.text((10,8+38*i),line,fill='white',font=font)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path)
    p.add_argument('page',type=int,help='1-based output ordinal, not original source-page number')
    p.add_argument('--output',type=Path,help='New diagnostic directory; use outside frozen run directories')
    a=p.parse_args()
    if a.page<1:p.error('output ordinal must be positive')
    original_page,mapping_basis=source_page(a.run,a.page)
    record=json.loads((a.run/f'page-{a.page:04d}.json').read_text())
    if record.get('page',a.page)!=a.page:raise ValueError('Page record disagrees with output ordinal')
    if record['status']=='accepted' and record.get('selected'):
        candidate=record['selected'];role='selected_candidate'
        published_classification=candidate['panels']['classification']
        published_panels=candidate['panels']['panels']
    elif record['status']=='whole_page_fallback' and record.get('selected') is None:
        candidate=record['attempts'][-1]['candidate'];role='rejected_last_attempt'
        published_classification='whole_page'
        published_panels=[{'order':1,'box':[0,0,1000,1000]}]
    else:raise ValueError('Expected a completed accepted page or explicit whole-page fallback')
    if not candidate.get('bundle') or candidate.get('invalid'):
        raise ValueError('Last candidate has no valid visual bundle; inspect its rejection record')
    bundle=json.loads(Path(candidate['bundle']).read_text())
    out=a.output or a.run/'visual-review'/f'page-{a.page:04d}'
    out.mkdir(parents=True,exist_ok=False)
    source=verified_image(bundle['images'][0]);shutil.copyfile(source,out/'source.jpg')
    original=Image.open(source).convert('RGB');overlay=original.copy();draw=ImageDraw.Draw(overlay)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',24)
    heading=[f'Source page {original_page} | output ordinal {a.page}',
             f'{"SELECTED" if role=="selected_candidate" else "REJECTED DIAGNOSTIC"} | publication: {published_classification}']
    w,h=original.size
    for panel in candidate['panels']['panels']:
        y,x,b,r=panel['box'];l,t,rr,bb=x*w/1000,y*h/1000,r*w/1000,b*h/1000
        draw.rectangle((l,t,rr,bb),outline='#ff00ff',width=3)
        draw.rectangle((l,t,l+42,t+34),fill='#ffff00');draw.text((l+5,t+2),str(panel['order']),font=font,fill='black')
    caption(overlay,heading,font).save(out/'overlay.jpg',quality=95)
    crops=bundle['images'][1:];crop_files=[]
    for start in range(0,len(crops),4):
        group=crops[start:start+4];thumbnails=[]
        for entry in group:
            crop=Image.open(verified_image(entry)).convert('RGB');crop.thumbnail((660,895))
            thumbnails.append(crop)
        row_heights=[max(im.height for im in thumbnails[i:i+2])+55 for i in range(0,len(thumbnails),2)]
        sheet=Image.new('RGB',(1360,sum(row_heights)),'#303030');d=ImageDraw.Draw(sheet)
        for i,(entry,crop) in enumerate(zip(group,thumbnails)):
            x=(i%2)*680;y=sum(row_heights[:i//2])
            d.text((x+10,y+8),entry['label'],fill='white',font=font)
            sheet.paste(crop,(x+10,y+45))
            name=('rejected-' if role=='rejected_last_attempt' else '')+Path(entry['path']).name
            shutil.copyfile(entry['path'],out/name);crop_files.append(name)
        caption(sheet,heading,font).save(out/f'crops-{start//4+1}.jpg',quality=95)
    meta={'output_ordinal':a.page,'source_page':original_page,'source_page_basis':mapping_basis,
          'status':record['status'],'artifact_role':role,'artifact_identity':candidate.get('identity'),
          'artifact_bundle':str(candidate['bundle']),'artifact_classification':candidate['panels']['classification'],
          'artifact_panels':candidate['panels']['panels'],'artifact_crop_files':crop_files,
          'published_classification':published_classification,
          'published_panels':published_panels,'publication_archive_present':(a.run/'automatic-panels.cbz').is_file(),
          'publication_basis':'completed controller outcome; archive contents are not validated by this helper',
          'source_image':'source.jpg','source_image_sha256':bundle['images'][0]['sha256'],
          'publication_source_sha256':record['source_sha256'],'tiers':[v['tier'] for v in record['attempts']],
          'refinement_changes':candidate.get('refinement_changes',[])}
    (out/'result.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta),flush=True)

if __name__=='__main__':main()
