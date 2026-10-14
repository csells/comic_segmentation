"""Freeze blinded judge inputs and separate evaluation labels from saved runs."""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from gemini_probe import save

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'comic_panel_e2e'))
from adapter import _rectangle as normalized_box_to_points


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence', type=Path)
    p.add_argument('images', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args();a.output.mkdir(parents=True, exist_ok=False)
    samples = []
    for run in ('openai-sol-low-v4-pilot-20261008','openai-sol-low-v4-confirmation-20261008'):
        for result in json.loads((a.evidence/run/'results.json').read_text()):
            page = result['source_page']
            samples.append({'page':page,'run':run,'expected':'escalate' if page in (100,205) else 'keep',
                            'known_defect':{100:'Artwork edges trimmed on five panels.',
                                            205:'Shared thought balloon clipped in panel2; collar clipped in panel9.'}.get(page,'')})
    samples.extend([
        {'page':100,'run':'openai-sol-low-v4-gutter-v2-confirmation-20261008','expected':'keep','known_defect':''},
        {'page':205,'run':'openai-sol-high-v5-boundaries-20261008','expected':'keep','known_defect':''}])
    random.Random(20261008).shuffle(samples)
    manifest = [];labels = []
    for index, sample in enumerate(samples, 1):
        case_id = f'case-{index:02}'; out = a.output/case_id;out.mkdir()
        page = sample['page'];source = a.images/f'{page:04}.jpg'
        directory = a.evidence/sample['run']/f'page-{page:04}'
        request = json.loads((directory/'request.json').read_text())
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        assert source_hash == request['source_sha256']
        panel_path = directory/'panels.json';panels = json.loads(panel_path.read_text())
        candidate = {k:panels[k] for k in ('classification','reading_direction')}
        candidate['panels'] = [{'order':v['order'],'box':v['box']} for v in panels['panels']]
        images = [{'label':'Original complete page','path':str(source.resolve()),'sha256':source_hash}]
        with Image.open(source) as im:
            original = im.convert('RGB')
        overlay = original.copy();draw = ImageDraw.Draw(overlay)
        crops = []
        if panels['classification'] == 'panels':
            for v in panels['panels']:
                y,x,b,r = v['box']
                points = normalized_box_to_points({'x':x/1000,'y':y/1000,'w':(r-x)/1000,'h':(b-y)/1000},original.width,original.height)
                coordinates = [tuple(map(int, point.split(','))) for point in points.split()]
                left,top = coordinates[0];right,bottom = coordinates[2]
                color = ['#ff2255','#00bbdd','#ccbb00','#ee33ee','#11cc44'][(v['order']-1)%5]
                draw.rectangle((left,top,right,bottom),outline=color,width=2)
                draw.rectangle((left,top,left+28,top+26),fill='black')
                draw.text((left+3,top+2),str(v['order']),fill=color,font_size=20)
                crop = out/f'crop-{v["order"]:02}.jpg'
                # Match adapter ACBF endpoints. Include the endpoint pixel in
                # diagnostic crops; record exact points for reproducibility.
                original.crop((left,top,right+1,bottom+1)).save(crop,quality=95)
                crops.append({'label':f'Candidate crop {v["order"]} in reading order',
                              'path':str(crop.resolve()),'points':points})
            overlay_path = out/'overlay.jpg';overlay.save(overlay_path,quality=95)
            images.append({'label':'Proposed rectangles numbered in reading order', 'path':str(overlay_path.resolve())})
            images.extend(crops)
        for entry in images:
            entry['sha256'] = hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest()
        save(out/'bundle.json',{**candidate,'images':images})
        manifest.append({'id':case_id,'bundle':str((out/'bundle.json').resolve())})
        labels.append({'id':case_id,**sample,'source_sha256':source_hash,
                       'panels_sha256':hashlib.sha256(panel_path.read_bytes()).hexdigest()})
        print(f'[{index}/{len(samples)}] {case_id}: frozen inputs; evaluation label excluded from bundle',flush=True)
    save(a.output/'manifest.json',manifest)
    save(a.output/'evaluation-labels.json',{'cases':labels,'declared_before_judging':True,
         'rubric':'Keep all12 usable candidates; escalate both known failures. This is a diagnostic gate, not independent held-out validation.',
         'model_input_excludes_labels':True,'random_seed':20261008})


if __name__=='__main__':main()
