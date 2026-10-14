"""Research end-to-end converter: input -> live/cached analysis -> automatic CBZ.

Run only in disposable staging. Key arrives on stdin. One shared durable ledger;
Unknown requests stop by default; an explicitly named timeout gets at most one
separately reserved recovery attempt. No curated case catalog or evaluation labels.
"""
import argparse
import base64
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile

import numpy as np
from PIL import Image

from automatic_escalation import run_page, RunBlocked
from decisions_probe import decision_cost, experiment_questions, parse_answers
from escalation_probe import judge_payload, parse_verdict, verdict_schema
from gemini_budget import Budget
from gemini_probe import save, validate_page
from gutter_refine import expand_dark_gutter_boxes
from openai_probe import PRICES, strict_schema, response_panels, response_usage
from split_check import QUESTION as SPLIT_QUESTION, source_region, request_body as split_request_body
from gutter_audit import edge_gutters, reconcile_regions

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'comic_panel_e2e'))
from adapter import build_cbz, _rectangle, IMAGE_EXTS

HERE=Path(__file__).resolve().parent
POLICY='automatic-target-quality-v11'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text())


def natural(path):
    return [int(v) if v.isdigit() else v.lower() for v in re.split(r'(\d+)',str(path))]


def safe_member(name):
    path=PurePosixPath(name)
    if not name or '\\' in name or path.is_absolute() or '..' in path.parts or ':' in name:
        raise ValueError('unsafe archive member')
    return path


def prepare_input(source, work, render_cache):
    source=source.resolve();work.mkdir(parents=True,exist_ok=True)
    manifest=work/'input.json';pages=work/'pages'
    source_id=sha(source) if source.is_file() else hashlib.sha256(json.dumps(
        [(p.relative_to(source).as_posix(),sha(p)) for p in sorted(source.rglob('*')) if p.is_file()],sort_keys=True).encode()).hexdigest()
    if manifest.exists():
        previous=read(manifest)
        if previous['source_sha256']!=source_id:raise ValueError('input changed; use a new run')
        for p in previous['pages']:
            if sha(pages/p['image'])!=p['sha256']:raise ValueError('prepared page changed')
        return previous
    if pages.exists() and any(pages.iterdir()):
        raise ValueError('incomplete input preparation; preserve it and use a new output directory')
    pages.mkdir(exist_ok=True)
    source_map=[]
    if source.suffix.lower()=='.pdf':
        info=subprocess.run(['pdfinfo',str(source)],capture_output=True,text=True,check=True).stdout
        match=re.search(r'^Pages:\s+(\d+)',info,re.M)
        if not match:raise ValueError('PDF page count unavailable')
        count=int(match[1]);cache=read(render_cache) if render_cache else None
        if cache and (cache['source_pdf_sha256']!=source_id or cache['page_count']!=count):
            raise ValueError('render cache does not match PDF')
        for i in range(1,count+1):
            dest=pages/f'{i:04d}.jpg'
            if cache:
                record=cache['pages'][i-1];old=render_cache.parent/'pages'/record['archive_image']
                if record['source_page']!=i or sha(old)!=record['sha256']:raise ValueError('invalid render cache')
                if not dest.exists():os.link(old,dest)
                elif sha(dest)!=record['sha256']:raise ValueError('partial render cache differs')
            else:
                subprocess.run(['pdftoppm','-f',str(i),'-l',str(i),'-singlefile','-jpeg','-r','150',str(source),str(dest.with_suffix(''))],check=True,timeout=180)
            source_map.append({'locator':f'PDF page {i}','image':dest.name,'sha256':sha(dest)})
            if i==1 or i%25==0 or i==count:print(f'prepare [{i}/{count}] PDF pages',flush=True)
    else:
        extracted=source
        if source.is_file():
            extracted=work/'extracted';extracted.mkdir(exist_ok=True)
            if zipfile.is_zipfile(source):
                with zipfile.ZipFile(source) as archive:
                    entries=archive.infolist()
                    if len(entries)>10000 or sum(x.file_size for x in entries)>2_000_000_000:
                        raise ValueError('archive exceeds research limits')
                    names=set()
                    for item in entries:
                        name=safe_member(item.filename)
                        if str(name).casefold() in names:raise ValueError('duplicate archive member')
                        names.add(str(name).casefold())
                        if stat.S_ISLNK(item.external_attr>>16):raise ValueError('archive symlink')
                    for item in entries:
                        target=extracted/str(safe_member(item.filename))
                        if item.is_dir():target.mkdir(parents=True,exist_ok=True);continue
                        target.parent.mkdir(parents=True,exist_ok=True)
                        with archive.open(item) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
            elif source.suffix.lower() in ('.cbr','.rar'):
                import libarchive
                total=0;names=set()
                with libarchive.file_reader(str(source)) as archive:
                    for entry in archive:
                        name=safe_member(entry.pathname)
                        if str(name).casefold() in names:raise ValueError('duplicate RAR member')
                        names.add(str(name).casefold());total+=entry.size
                        if len(names)>10000 or total>2_000_000_000:raise ValueError('RAR exceeds research limits')
                        if entry.isdir:continue
                        if not entry.isfile:raise ValueError('nonregular RAR member')
                        target=extracted/str(name);target.parent.mkdir(parents=True,exist_ok=True)
                        with target.open('wb') as f:
                            for block in entry.get_blocks():f.write(block)
            else:raise ValueError('expected PDF, CBZ/ZIP, CBR/RAR or image folder')
        files=sorted(extracted.rglob('*'),key=lambda p:natural(p.relative_to(extracted)))
        if any(p.is_symlink() for p in files):raise ValueError('source symlinks unsupported')
        for path in files:
            if not path.is_file() or '__MACOSX' in path.parts or path.name.startswith('._'):continue
            if path.suffix.lower() in IMAGE_EXTS:
                dest=pages/f'{len(source_map)+1:04d}{path.suffix.lower()}'
                shutil.copyfile(path,dest)
                source_map.append({'locator':path.relative_to(extracted).as_posix(),'image':dest.name,'sha256':sha(dest)})
            else:
                dest=pages/'source-auxiliary'/path.relative_to(extracted)
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    if len(source_map)<2:raise ValueError('prototype requires cover and at least one body page')
    for record in source_map:
        with Image.open(pages/record['image']) as im:
            im.load();record['width'],record['height']=im.size
    result={'source':str(source),'source_sha256':source_id,'pages':source_map,'render_cache':str(render_cache) if render_cache else None}
    save(manifest,result);return result


class Client:
    def __init__(self,key,budget,root,retry_unknown=()):
        self.key=key;self.budget=budget;self.root=root;root.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.new_calls=0;self.cache_hits=0
        self.retry_unknown=set(retry_unknown)

    def http(self,endpoint,body):
        req=urllib.request.Request('https://api.openai.com/v1/'+endpoint,data=json.dumps(body).encode(),
            headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=600 if endpoint=='responses' else 180) as response:return json.load(response)
        except urllib.error.HTTPError as e:
            raise RunBlocked(f'HTTP {e.code}: '+e.read().decode(errors='replace').replace(self.key,'[REDACTED]')) from None

    def request(self,endpoint,body,kind):
        encoded=json.dumps(body,sort_keys=True).encode()
        if len(encoded)>19000000:raise RunBlocked('request too large')
        prefix={'native':b'https://api.openai.com/v1/decisions\n',
                'detector':b'openai-responses:','verifier':b'comic-escalation-judge-v1:'}[kind]
        identity=hashlib.sha256(prefix+encoded).hexdigest()
        original_identity=identity
        retry_of=None
        with self.lock:
            if identity in self.budget.entries:
                old=Path(self.budget.entries[identity]['path']);response=old/'response.json'
                if response.is_file():
                    # Missing usage settlement remains held, never silently free.
                    self.cache_hits+=1
                    return read(response),{'request_id':identity,'path':str(old),'cached':True}
                recovery=hashlib.sha256(('explicit-timeout-recovery-1:'+identity).encode()).hexdigest()
                if recovery in self.budget.entries:
                    old=Path(self.budget.entries[recovery]['path']);response=old/'response.json'
                    if not response.is_file():raise RunBlocked('recovery also unknown; no further replay: '+recovery)
                    self.cache_hits+=1
                    return read(response),{'request_id':recovery,'retry_of':identity,'path':str(old),'cached':True}
                if identity not in self.retry_unknown:
                    raise RunBlocked('previous unknown request; no automatic replay: '+identity)
                error=read(old/'error.json').get('error','') if (old/'error.json').is_file() else ''
                if not any(word in error.lower() for word in ('timed out','timeout')):
                    raise RunBlocked('explicit recovery requires a recorded timeout: '+identity)
                retry_of=identity;identity=recovery
            out=self.root/identity;out.mkdir(exist_ok=True)
            if (out/'response.json').exists():raise RunBlocked('untracked existing response')
            sanitized=copy.deepcopy(body)
            for item in sanitized.get('input',[]) if isinstance(sanitized.get('input'),list) else []:
                for part in item.get('content',[]):
                    if part.get('type')=='input_image':
                        data=base64.b64decode(part.pop('image_url').split(',',1)[1])
                        part['image_sha256']=hashlib.sha256(data).hexdigest()
            if not (out/'request.json').exists():save(out/'request.json',{'endpoint':endpoint,'kind':kind,'request_id':identity,'request_fingerprint':original_identity,'retry_of':retry_of,'body_without_image_bytes':sanitized})
            if kind=='native':reserve,inp,out_rate=1000000,.1,.5
            elif kind=='detector':reserve,inp,out_rate=PRICES[body['model']]
            else:
                _,inp,out_rate=PRICES[body['model']];reserve=math.ceil(60000*inp+8192*out_rate)
            # Preflight is non-generative. All paid dispatches reserve durably first.
            if kind!='native':
                count=self.http('responses/input_tokens',{k:body[k] for k in ('model','input','text','reasoning')})
                n=count.get('input_tokens');limit=20000 if kind=='detector' else 60000
                if type(n) is not int or not 0<n<=limit:raise RunBlocked('input exceeds reservation')
            try:self.budget.reserve(identity,out.resolve(),reserve,inp,out_rate)
            except ValueError as e:raise RunBlocked(str(e)) from None
            self.new_calls+=1
        started=time.monotonic()
        if kind!='native':print(f'  {kind} {body["model"]} started; recovery={retry_of is not None}; request={identity[:12]}',flush=True)
        try:
            raw=self.http(endpoint,body);save(out/'response.json',raw)
            with self.lock:
                if kind=='native':
                    cost=decision_cost(raw.get('usage',{}))
                    if cost is None or cost>reserve:raise RunBlocked('native usage missing/excessive')
                    self.budget.append({'kind':'settle','id':identity,'cost':cost,'usage':raw['usage'],'endpoint':'decisions'})
                    self.budget.entries[identity]['cost']=cost
                else:self.budget.settle(identity,response_usage(raw))
            save(out/'timing.json',{'seconds':time.monotonic()-started})
            if kind!='native':print(f'  {kind} completed in {time.monotonic()-started:.1f}s',flush=True)
            return raw,{'request_id':identity,'retry_of':retry_of,'path':str(out),'cached':False}
        except Exception as e:
            if not (out/'error.json').exists():save(out/'error.json',{'error':str(e).replace(self.key,'[REDACTED]')})
            raise RunBlocked('request failed; durable reservation retained when unsettled: '+str(e).replace(self.key,'[REDACTED]')) from None


def quality_route(global_probabilities,targets):
    semantic=[name for name in ('scene_defect','order_defect') if global_probabilities[name]>=.5]
    global_crops=[name for name in ('text_clipping','art_clipping') if global_probabilities.get(name,0)>=.5]
    flagged=[n for n,p in targets.items() if max(p.values())>=.5]
    return {'route':'escalate' if semantic or global_crops or flagged else 'keep',
            'semantic_flags':semantic,'global_crop_flags':global_crops,'target_flags':flagged}


def overlap_risk_pairs(panels):
    """A routing risk, not an assertion that overlapping comic panels are wrong.

    Ignore small gutter/border overlap. Both partial overlap and containment can
    hide scene boundaries or visible artwork beside an occluding foreground
    subject. Require stronger detection before accepting either layout.
    """
    pairs=[]
    for i,a in enumerate(panels):
        ay,ax,ab,ar=a['box'];area_a=(ab-ay)*(ar-ax)
        for b in panels[i+1:]:
            by,bx,bb,br=b['box'];area_b=(bb-by)*(br-bx)
            overlap=max(0,min(ab,bb)-max(ay,by))*max(0,min(ar,br)-max(ax,bx))
            fraction=overlap/min(area_a,area_b)
            if fraction>=.10:pairs.append([a['order'],b['order']])
    return pairs


class Converter:
    def __init__(self,client,root):
        self.client=client;self.root=root;self.bundles={};self.judgments={}

    def detect(self,page,tier):
        model,effort,promptfile={'sol-low':('gpt-6-sol','low','prompt-v6.txt'),
            'sol-high':('gpt-6-sol','high','prompt-v6.txt'),'astra':('gpt-6-astra','high','prompt-v6.txt')}[tier]
        prompt=(HERE/promptfile).read_text();data=page.read_bytes()
        config={'model':model,'store':False,'max_output_tokens':8192,'reasoning':{'effort':effort},'service_tier':'default',
                'text':{'format':{'type':'json_schema','name':'comic_panels','strict':True,'schema':strict_schema()}}}
        request={**config,'input':[{'role':'user','content':[{'type':'input_text','text':prompt},
            {'type':'input_image','image_url':'data:image/jpeg;base64,'+base64.b64encode(data).decode(),'detail':'original'}]}]}
        raw,provenance=self.client.request('responses',request,'detector')
        try:panels=response_panels(raw)
        except (ValueError,KeyError,TypeError) as e:
            return {'invalid':str(e),'detector':provenance,'tier':tier}
        return {'panels':panels,'detector':provenance,'tier':tier,'source_sha256':sha(page)}

    def refine(self,page,candidate):
        if candidate.get('invalid'):return candidate
        value=copy.deepcopy(candidate['panels'])
        with Image.open(page) as im:rgb=np.asarray(im.convert('RGB'))
        h,w=rgb.shape[:2];boxes=[[round(p['box'][1]*w/1000),round(p['box'][0]*h/1000),
            round(p['box'][3]*w/1000),round(p['box'][2]*h/1000)] for p in value['panels']]
        refined,changes=expand_dark_gutter_boxes(rgb,boxes) if value['classification']=='panels' else (boxes,[])
        for change in changes:
            i=change['index'];l,t,r,b=refined[i];old=value['panels'][i]['box']
            n=[math.floor(t*1000/h),math.floor(l*1000/w),math.ceil(b*1000/h),math.ceil(r*1000/w)]
            value['panels'][i]['box']=[min(old[0],n[0]),min(old[1],n[1]),max(old[2],n[2]),max(old[3],n[3])]
        validate_page(value)
        base=self.bundle_candidate(page,candidate,value,changes)
        bundle=self.bundles[base['identity']];risks=[];audits=[]
        if value['classification']=='panels':
            for panel,crop in zip(value['panels'],bundle['images'][1:]):
                findings=edge_gutters(crop['path'])
                if findings:risks.append({'target':panel['order'],'findings':findings,'crop':crop})
        if candidate['tier']=='sol-low':return {**base,'gutter_risks':risks}
        # Descending replacement keeps earlier target indices stable. Regional
        # model geometry is mapped to the source; pixel flags never set a split.
        for risk in sorted(risks,key=lambda r:r['target'],reverse=True):
            target=risk['target'];crop=risk['crop'];regional=self.detect(Path(crop['path']),'astra')
            if regional.get('invalid'):raise RunBlocked('invalid regional gutter audit: '+regional['invalid'])
            coords=[tuple(map(int,v.split(','))) for v in crop['points'].split()]
            l,t=coords[0];rr,bb=coords[2]
            proposed,audit=reconcile_regions(value,target,regional['panels'],(l,t,rr+1,bb+1),(w,h))
            if audit['replaced']:
                review=self.review_region(page,value,target,Path(crop['path']),regional)
                confirmed={m['regional_order']:m['existing_order'] for m in review['answer']['context_matches']}
                proposed,audit=reconcile_regions(value,target,regional['panels'],(l,t,rr+1,bb+1),(w,h),confirmed)
                audit['review']=review
                if audit['replaced'] and not review['answer']['distinct_scenes']:
                    audit['replaced']=False;audit['unresolved']=True
                else:value=proposed
            else:value=proposed
            record={'target':target,'risk':risk['findings'],'regional':regional,**audit}
            save(Path(base['bundle']).parent/f'regional-audit-{target:02d}.json',record);audits.append(record)
        if any(a['replaced'] for a in audits):
            validate_page(value);base=self.bundle_candidate(page,candidate,value,changes)
        return {**base,'gutter_risks':risks,'regional_audits':audits}

    def review_region(self,page,value,target,crop,regional):
        # A separate high-reasoning reviewer checks new regional proposals,
        # including neighbor fragments. No evaluation labels enter the request.
        local=self.bundle_candidate(crop,regional,regional['panels'],[])
        bundle=copy.deepcopy(self.bundles[local['identity']])
        bundle['images'].insert(0,{'label':'Original complete source page','path':str(page)})
        prompt=(HERE/'regional-review-prompt-v1.txt').read_text()+'\nFull-page candidate geometry (0..1000): '+json.dumps(value)+'\nAudited original target: '+str(target)+'\nFollowing candidate geometry uses LOCAL coordinates of the audited region.'
        match={'type':'object','properties':{'regional_order':{'type':'integer'},'existing_order':{'type':'integer'}},'required':['regional_order','existing_order'],'additionalProperties':False}
        props={'distinct_scenes':{'type':'boolean'},'context_matches':{'type':'array','items':match},'evidence':{'type':'string'}}
        body={'model':'gpt-6-sol','store':False,'max_output_tokens':8192,'reasoning':{'effort':'high'},'service_tier':'default',
              'text':{'format':{'type':'json_schema','name':'regional_review','strict':True,'schema':{'type':'object','properties':props,'required':list(props),'additionalProperties':False}}},
              'input':[{'role':'user','content':judge_payload(bundle,prompt)}]}
        raw,request=self.client.request('responses',body,'verifier')
        try:
            if raw.get('status')!='completed':raise ValueError('incomplete regional review')
            answer=json.loads(''.join(p['text'] for m in raw.get('output',[]) if m.get('type')=='message' for p in m.get('content',[]) if p.get('type')=='output_text'))
            if set(answer)!=set(props) or type(answer['distinct_scenes']) is not bool or not isinstance(answer['evidence'],str) or not answer['evidence'].strip():raise ValueError('invalid regional review')
            seen=set()
            for m in answer['context_matches']:
                if set(m)!={'regional_order','existing_order'} or type(m['regional_order']) is not int or type(m['existing_order']) is not int or not 1<=m['regional_order']<=len(regional['panels']['panels']) or m['existing_order']==target or not 1<=m['existing_order']<=len(value['panels']) or m['regional_order'] in seen:raise ValueError('invalid regional context match')
                seen.add(m['regional_order'])
        except (ValueError,KeyError,TypeError) as error:raise RunBlocked(str(error)) from None
        return {'answer':answer,'request':request}

    def bundle_candidate(self,page,candidate,value,changes):
        with Image.open(page) as im:w,h=im.size
        identity=hashlib.sha256((sha(page)+json.dumps(value,sort_keys=True)+POLICY).encode()).hexdigest()
        directory=self.root/'candidates'/identity;directory.mkdir(parents=True,exist_ok=True)
        bundle={k:value[k] for k in ('classification','reading_direction')}
        bundle['panels']=[{'order':p['order'],'box':p['box']} for p in value['panels']]
        images=[{'label':'Original complete page','path':str(page.resolve()),'sha256':sha(page)}]
        if value['classification']=='panels':
            with Image.open(page) as im:
                for p in value['panels']:
                    y,x,b,r=p['box'];points=_rectangle({'x':x/1000,'y':y/1000,'w':(r-x)/1000,'h':(b-y)/1000},w,h)
                    coords=[tuple(map(int,v.split(','))) for v in points.split()];l,t=coords[0];rr,bb=coords[2]
                    crop=directory/f'crop-{p["order"]:02}.jpg'
                    if not crop.exists():im.convert('RGB').crop((l,t,rr+1,bb+1)).save(crop,quality=95)
                    images.append({'label':f'Candidate crop {p["order"]} in reading order','path':str(crop),'sha256':sha(crop),'points':points})
        bundle['images']=images;self.bundles[identity]=bundle
        if not (directory/'bundle.json').exists():save(directory/'bundle.json',bundle)
        return {**candidate,'panels':value,'identity':identity,'refinement_changes':changes,'bundle':str(directory/'bundle.json')}

    def decision(self,bundle,prompt,questions):
        raw,provenance=self.client.request('decisions',{'model':'gpt-6-luna','questions':questions,
            'input':[{'role':'user','content':judge_payload(bundle,prompt)}]},'native')
        try:return parse_answers(raw,questions),provenance
        except ValueError as e:raise RunBlocked(str(e)) from None

    def check_splits(self,candidate):
        bundle=self.bundles[candidate['identity']]
        if bundle['classification']!='panels':return {'flags':[],'checks':[]}
        panels=sorted(bundle['panels'],key=lambda p:p['order']);checks=[];flags=[]
        directory=Path(candidate['bundle']).parent
        for first,second in zip(panels,panels[1:]):
            pair=[first['order'],second['order']]
            region=source_region(bundle['images'][0]['path'],[first,second],
                                 directory/f'split-region-{pair[0]}-{pair[1]}.jpg')
            raw,request=self.client.request('decisions',split_request_body(region),'native')
            try:answer=parse_answers(raw,[SPLIT_QUESTION])
            except ValueError as e:raise RunBlocked(str(e)) from None
            probability=answer['probabilities']['false_split']
            checks.append({'pair':pair,'probability':probability,'request':request})
            certified=any(a.get('replaced') and a.get('review',{}).get('answer',{}).get('distinct_scenes') and
                any(first['box']==x and second['box']==y for x,y in zip(a.get('replacement_boxes',[]),a.get('replacement_boxes',[])[1:]))
                for a in candidate.get('regional_audits',[]))
            checks[-1]['regional_split_certified']=certified
            if probability>=.5 and not certified:flags.append(pair)
        return {'flags':flags,'checks':checks}

    def judge(self,page,candidate):
        if candidate.get('invalid'):return {'route':'escalate','structural_error':candidate['invalid']}
        identity=candidate['identity'];bundle=self.bundles[identity];prompt=(HERE/'decisions-prompt-v2.txt').read_text()
        overlap_pairs=overlap_risk_pairs(bundle['panels']) if candidate['tier']=='sol-low' and bundle['classification']=='panels' else []
        if overlap_pairs or (candidate['tier']=='sol-low' and candidate.get('gutter_risks')):
            verdict={'route':'escalate','overlap_pairs':overlap_pairs,
                     'gutter_risks':candidate.get('gutter_risks',[]),
                     'reason':'overlap or hidden-gutter risk requires stronger boundary and scene detection',
                     'semantic_flags':[],'global_crop_flags':[],'target_flags':[]}
            self.judgments[identity]=verdict;return verdict
        if any(a.get('unresolved') for a in candidate.get('regional_audits',[])):
            verdict={'route':'escalate','gutter_risks':candidate['gutter_risks'],'reason':'regional proposal not independently confirmed','semantic_flags':[],'global_crop_flags':[],'target_flags':[]}
            self.judgments[identity]=verdict;return verdict
        splits=self.check_splits(candidate)
        if splits['flags']:
            verdict={'route':'escalate','split_flags':splits['flags'],'split_checks':splits['checks'],
                     'reason':'source continuity indicates a false split; require fresh detection',
                     'semantic_flags':[],'global_crop_flags':[],'target_flags':[]}
            self.judgments[identity]=verdict;return verdict
        global_answer,global_request=self.decision(bundle,prompt,experiment_questions('clean-v2'))
        targets={};requests={}
        def inspect(panel):
            target=panel['order'];local={**bundle,'images':[im for im in bundle['images'] if im['label'] in ('Original complete page',f'Candidate crop {target} in reading order')]}
            instructions=prompt+f'\nONLY judge TARGET scene {target}. The second image is its actual crop. The other geometries provide context only; do not evaluate their crops.\n'
            answer,request=self.decision(local,instructions,experiment_questions('target-v3'))
            return target,answer['probabilities'],request
        if bundle['classification']=='panels':
            available=(self.client.budget.cap-self.client.budget.used())/1e6
            workers=max(1,min(3,int(available-.3)))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for target,probabilities,request in pool.map(inspect,bundle['panels']):targets[target]=probabilities;requests[target]=request
        verdict={**quality_route(global_answer['probabilities'],targets),'split_checks':splits['checks'],
            'global_probabilities':global_answer['probabilities'],
            'target_probabilities':targets,'global_request':global_request,'target_requests':requests}
        self.judgments[identity]=verdict;return verdict

    def verification(self,bundle,prompt,effort):
        config={'model':'gpt-6-sol','store':False,'max_output_tokens':8192,'reasoning':{'effort':effort},'service_tier':'default',
            'text':{'format':{'type':'json_schema','name':'panel_quality_verdict','strict':True,'schema':verdict_schema()}}}
        raw,request=self.client.request('responses',{**config,'input':[{'role':'user','content':judge_payload(bundle,prompt)}]},'verifier')
        try:return parse_verdict(raw,len(bundle['panels'])),request
        except ValueError as e:raise RunBlocked(str(e)) from None

    def verify(self,page,candidate):
        if candidate.get('invalid'):return {'route':'escalate','structural_error':candidate['invalid']}
        bundle=self.bundles[candidate['identity']];verdict=self.judgments[candidate['identity']];checks=[];evidence=[]
        if verdict.get('overlap_pairs') or verdict.get('split_flags') or verdict.get('gutter_risks'):
            return {'route':'escalate','evidence':[],
                    'reason':'layout risk requires stronger detection, not verifier clearance'}
        if verdict['global_crop_flags']:
            # Target checks and the global Responses verifier have demonstrated
            # false negatives. Their passes cannot erase an independent warning.
            if candidate['tier']=='sol-low':
                return {'route':'escalate','evidence':[],
                        'reason':'independent page-level clipping warning requires stronger detection'}
            answer,request=self.verification(bundle,(HERE/'judge-prompt-v2.txt').read_text(),'high')
            checks.append(answer['route']=='keep')
            evidence.append({'scope':'complete stronger candidate','verdict':answer,'request':request})
        elif verdict['semantic_flags']:
            answer,request=self.verification(bundle,(HERE/'judge-prompt-v2.txt').read_text(),'low')
            # It sees the whole candidate and can discover defects beyond the
            # original trigger. Preserve those findings even if a target passes.
            checks.append(answer['route']=='keep')
            evidence.append({'scope':'complete candidate after semantic warning','verdict':answer,'request':request})
        for target in verdict['target_flags']:
            local={**bundle,'images':[im for im in bundle['images'] if im['label'] in ('Original complete page',f'Candidate crop {target} in reading order')]}
            answer,request=self.verification(local,(HERE/'judge-target-prompt-v3.txt').read_text(),'high')
            checks.append(answer['route']=='keep');evidence.append({'scope':'target','panel':target,'verdict':answer,'request':request})
        return {'route':'keep' if checks and all(checks) else 'escalate','evidence':evidence}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--ledger',type=Path,required=True);p.add_argument('--render-cache',type=Path)
    p.add_argument('--pages',help='Optional bounded source page numbers; preserve original order')
    p.add_argument('--max-new-pages',type=int,help='Checkpoint after this many new pages; resume with the same output directory')
    p.add_argument('--retry-unknown',action='append',default=[],help='Explicit request fingerprint: one separately budgeted recovery of a recorded timeout; never repeats success')
    p.add_argument('--title',default='Automatic panel edition');p.add_argument('--execute-approved',action='store_true')
    a=p.parse_args()
    if a.max_new_pages is not None and a.max_new_pages<1:p.error('--max-new-pages must be positive')
    if any(not re.fullmatch(r'[0-9a-f]{64}',v) for v in a.retry_unknown):p.error('retry fingerprint must be SHA256')
    if not a.execute_approved:p.error('live operation requires --execute-approved')
    if datetime.now(timezone.utc).date().isoformat()>'2026-12-31':p.error('refresh pricing policy')
    key=sys.stdin.readline().strip()
    if not re.fullmatch(r'sk-[\w-]{30,}',key):p.error('valid stdin credential required')
    a.output.mkdir(parents=True,exist_ok=True)
    input_=prepare_input(a.source,a.output/'input',a.render_cache)
    for number,record in enumerate(input_['pages'],1):record['source_page']=number
    if a.pages:
        selected=[int(v) for v in a.pages.split(',')]
        if len(selected)<2 or len(set(selected))!=len(selected) or any(v<1 or v>len(input_['pages']) for v in selected):
            p.error('invalid selected source pages')
        input_={**input_,'pages':[r for r in input_['pages'] if r['source_page'] in selected]}
    config={'policy':POLICY,'source_sha256':input_['source_sha256'],'title':a.title,
        'source_pages':[r['source_page'] for r in input_['pages']],
        'source_sha256s':{str(p.relative_to(HERE.parent)):sha(p) for p in [
          *[HERE/n for n in ('auto_convert.py','automatic_escalation.py','gutter_refine.py',
             'decisions_probe.py','escalation_probe.py','openai_probe.py','gemini_probe.py','gemini_budget.py','split_check.py','gutter_audit.py','regional-review-prompt-v1.txt',
             'prompt-v6.txt','decisions-prompt-v2.txt','judge-prompt-v2.txt','judge-target-prompt-v3.txt')],
          HERE.parent/'comic_panel_e2e/adapter.py',HERE.parent/'gemini_panel_probe/contract.py']}}
    if (a.output/'run.json').exists():
        if read(a.output/'run.json')!=config:raise ValueError('run identity changed; use a new output directory')
    else:save(a.output/'run.json',config)
    outcomes=[];count=len(input_['pages']);started=time.monotonic();new_pages=0
    with Budget(a.ledger,cap=20000000) as budget:
        client=Client(key,budget,a.output/'calls',retry_unknown=a.retry_unknown);converter=Converter(client,a.output)
        for i,record in enumerate(input_['pages'],1):
            final=a.output/f'page-{i:04d}.json'
            if final.exists():
                previous=read(final)
                if previous['source_sha256']!=record['sha256']:raise ValueError('completed page changed')
                outcomes.append(previous);continue
            if a.max_new_pages is not None and new_pages>=a.max_new_pages:
                print(json.dumps({'status':'checkpoint','completed_pages':len(outcomes),'total_pages':count,
                    'new_calls':client.new_calls,'cache_hits':client.cache_hits,'used_held_micro_usd':budget.used()}),flush=True)
                return
            image=a.output/'input/pages'/record['image'];analysis=image
            if image.suffix.lower() not in ('.jpg','.jpeg'):
                analysis=a.output/f'analysis-{i:04d}.jpg'
                if not analysis.exists():
                    with Image.open(image) as im:im.convert('RGB').save(analysis,quality=95)
            print(f'[{i}/{count}] automatic analysis; used/held ${budget.used()/1e6:.6f}',flush=True)
            result=run_page(analysis,converter.detect,converter.refine,converter.judge,converter.verify)
            result={'page':i,'source_sha256':record['sha256'],**result}
            if result['status']=='blocked':
                save(a.output/f'blocked-{time.time_ns()}.json',result)
                print(f'[{i}/{count}] BLOCKED: {result["reason"]}',flush=True);raise SystemExit(2)
            save(final,result);outcomes.append(result)
            new_pages+=1
            print(f'[{i}/{count}] {result["status"]}; tiers={len(result["attempts"])}; new calls={client.new_calls}; cache hits={client.cache_hits}; used/held ${budget.used()/1e6:.6f}',flush=True)
        stats={'new_calls':client.new_calls,'cache_hits':client.cache_hits,'used_held_micro_usd':budget.used(),'elapsed_seconds':time.monotonic()-started}
    entries=[];fallbacks={};counts=[];publication=a.output/'publication-pages';publication.mkdir(exist_ok=True)
    for i,(record,result) in enumerate(zip(input_['pages'],outcomes),1):
        if result['status']=='accepted':
            selected=result['selected']['panels'];panels=selected['panels'];classification=selected['classification']
        else:
            panels=[{'box':[0,0,1000,1000]}];classification='whole_page';fallbacks[i]=result['reason']
        boxes=[]
        for panel in panels:
            y,x,b,r=panel['box'];boxes.append({'x':x/1000,'y':y/1000,'w':(r-x)/1000,'h':(b-y)/1000})
        entries.append({'page':i,'image':record['image'],'panels':boxes});counts.append(len(panels) if classification=='panels' else 0)
        target=publication/record['image']
        if not target.exists():os.link(a.output/'input/pages'/record['image'],target)
        if sha(target)!=record['sha256']:raise ValueError('publication page changed')
    auxiliary=a.output/'input/pages/source-auxiliary'
    if auxiliary.exists() and not (publication/'source-auxiliary').exists():shutil.copytree(auxiliary,publication/'source-auxiliary')
    output=a.output/'automatic-panels.cbz'
    manifest_path=a.output/'book.manifest.json'
    if output.exists() and not manifest_path.exists():raise ValueError('unfinalized archive exists; inspect before resuming')
    if not output.exists():
        manifest=build_cbz(publication,{'pages':entries,'total_pages':count,'reading_direction':'ltr'},output,title=a.title,
            source_map={i:r['source_page'] for i,r in enumerate(input_['pages'],1)},fallback_reasons=fallbacks)
        save(manifest_path,manifest)
    else:
        manifest=read(manifest_path)
        if sha(output)!=manifest['output_sha256']:raise ValueError('published archive changed')
    if not (a.output/'counts.json').exists():save(a.output/'counts.json',counts[1:])
    summary={**stats,'source_sha256':input_['source_sha256'],'output_sha256':manifest['output_sha256'],
        'pages':count,'source_pages':[r['source_page'] for r in input_['pages']],
        'accepted_pages':sum(r['status']=='accepted' for r in outcomes),'fallback_pages':list(fallbacks),
        'escalated_pages':[r['page'] for r in outcomes if len(r['attempts'])>1],
        'refined_pages':[r['page'] for r in outcomes if r['selected'] and r['selected'].get('refinement_changes')],
        'panel_steps':sum(counts[1:]),'human_routing_decisions':0,'evaluation_labels_read':False}
    save(a.output/f'completed-{time.time_ns()}.json',summary);print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
