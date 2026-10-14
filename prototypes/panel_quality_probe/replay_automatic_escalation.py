"""Historical cache replay for its matching archived controller version.

This script predates the mandatory final completeness callback and is not a
current CLI/acceptance path. Reproduce it only with its frozen historical source;
do not add a passing callback to the current controller. Use auto_convert.py for
the current prototype. The implementation below is retained as historical code.

Exercise automatic routing on real saved outputs; no labels or network calls.

Runs the real gutter refiner. Cached detector/judge providers fail closed when
an exact source/geometry or required result is absent. This is an offline policy
replay, not proof of a new live detector integration or held-out quality.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

from automatic_escalation import run_page, RunBlocked
from gutter_refine import expand_dark_gutter_boxes
from gemini_probe import save


def read(path):
    if not path.is_file(): raise RunBlocked('required cache artifact missing: '+str(path))
    return json.loads(path.read_text())


def geometry(value):
    return {k:value[k] if k!='panels' else [{'order':p['order'],'box':p['box']} for p in value[k]]
            for k in ('classification','reading_direction','panels')}


def key(source_hash,value):
    return hashlib.sha256((source_hash+json.dumps(geometry(value),sort_keys=True)).encode()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence',type=Path); p.add_argument('output',type=Path)
    a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
    bundles={}; by_geometry={}
    for entry in read(a.evidence/'judge-cases-v1-20261008/manifest.json'):
        bundle=read(Path(entry['bundle'])); bundles[entry['id']]=bundle
        by_geometry[key(bundle['images'][0]['sha256'],bundle)]=entry['id']
    detectors={}; pages=[]
    for tier,dirname in [('sol-low','openai-sol-low-v4-pilot-20261008'),
                         ('sol-low','openai-sol-low-v4-confirmation-20261008'),
                         ('sol-high','openai-sol-high-v5-boundaries-20261008')]:
        for record in read(a.evidence/dirname/'results.json'):
            directory=a.evidence/dirname/f'page-{record["source_page"]:04d}'
            source_hash=read(directory/'request.json')['source_sha256']
            value=read(directory/'panels.json'); case=by_geometry.get(key(source_hash,value))
            if case is None: raise RunBlocked('saved detector geometry has no exact case')
            detectors[(source_hash,tier)]={'case_id':case,'source_sha256':source_hash,
                'geometry':geometry(value),'source_run':dirname}
            if tier=='sol-low': pages.append(source_hash)
    if len(pages)!=len(set(pages)): raise ValueError('duplicate source in replay catalog')
    globals_={r['id']:r['verdict'] for r in read(a.evidence/'luna-decisions-clean-v2-20261008/results.json')}
    targets={r['id']:r['verdict'] for r in read(a.evidence/'luna-decisions-target-v3-20261008/results.json')}
    verifiers={r['id']:r['verdict'] for r in read(a.evidence/'sol-verifier-target-v3-20261008/results.json')}
    global_verifiers={r['id']:r['verdict'] for r in read(a.evidence/'sol-verifier-v2-20261008/results.json')}

    def detect(page,tier):
        if (page,tier) not in detectors: raise RunBlocked('requested detector tier absent from cache')
        return copy.deepcopy(detectors[(page,tier)])

    def refine(page,candidate):
        bundle=bundles[candidate['case_id']]; source=Path(bundle['images'][0]['path'])
        if hashlib.sha256(source.read_bytes()).hexdigest()!=page: raise RunBlocked('source hash mismatch')
        with Image.open(source) as im: rgb=np.asarray(im.convert('RGB'))
        height,width=rgb.shape[:2]; value=copy.deepcopy(candidate['geometry'])
        boxes=[[round(p['box'][1]*width/1000),round(p['box'][0]*height/1000),
                round(p['box'][3]*width/1000),round(p['box'][2]*height/1000)] for p in value['panels']]
        refined,changes=expand_dark_gutter_boxes(rgb,boxes) if value['classification']=='panels' else (boxes,[])
        for change in changes:
            i=change['index']; l,t,r,b=refined[i]; old=value['panels'][i]['box']
            norm=[math.floor(t*1000/height),math.floor(l*1000/width),
                  math.ceil(b*1000/height),math.ceil(r*1000/width)]
            value['panels'][i]['box']=[min(old[0],norm[0]),min(old[1],norm[1]),max(old[2],norm[2]),max(old[3],norm[3])]
        case=by_geometry.get(key(page,value))
        if case is None: raise RunBlocked('refined geometry has no exact cached judge input')
        return {**candidate,'case_id':case,'geometry':value,'refinement_changes':changes}

    def judge(page,candidate):
        case=candidate['case_id']; g=globals_[case]['probabilities']
        semantic=[name for name in ('scene_defect','order_defect') if g[name]>=0.5]
        flagged=[]
        if candidate['geometry']['classification']=='panels':
            for panel in candidate['geometry']['panels']:
                target=f'{case}-panel-{panel["order"]:02d}'
                if target not in targets: raise RunBlocked('missing target decision')
                if targets[target]['route']=='escalate': flagged.append(target)
        return {'route':'escalate' if semantic or flagged else 'keep',
                'semantic_flags':semantic,'target_flags':flagged,'case_id':case}

    def verify(page,candidate):
        verdict=judge(page,candidate); case=candidate['case_id']; checks=[]
        if verdict['semantic_flags']:
            if case not in global_verifiers: raise RunBlocked('missing semantic verifier')
            g=global_verifiers[case]
            # Whole-page verifier coverage proved unreliable. It cannot veto
            # target clipping flags; only its corresponding semantic fields count.
            mapping={'scene_defect':'scene_inventory','order_defect':'reading_order'}
            checks.extend(g[mapping[name]]=='pass' for name in verdict['semantic_flags'])
        for target in verdict['target_flags']:
            if target not in verifiers: raise RunBlocked('missing target verifier')
            checks.append(verifiers[target]['route']=='keep')
        return {'route':'keep' if checks and all(checks) else 'escalate',
                'semantic_flags':verdict['semantic_flags'],'target_flags':verdict['target_flags']}

    results=[]
    for i,page in enumerate(pages,1):
        result={'source_sha256':page,**run_page(page,detect,refine,judge,verify,tiers=('sol-low','sol-high'))}
        save(a.output/f'page-{i:02d}.json',result); results.append(result)
        print(f'[{i}/{len(pages)}] {result["status"]}; detector attempts={len(result["attempts"])}',flush=True)
    save(a.output/'results.json',{'mode':'offline exact-cache replay with actual gutter refinement',
        'network_calls':0,'runtime_reads_evaluation_labels':False,'human_decisions':0,'pages':results})


if __name__=='__main__': main()
