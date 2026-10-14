"""Research end-to-end converter: input -> live/cached analysis -> automatic CBZ.

Run only in disposable staging. Key arrives on stdin. One shared durable ledger;
Unknown requests stop by default; explicitly named eligible transport failures get
at most one separately reserved recovery. No curated cases or evaluation labels.
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

from automatic_escalation import run_page, RunBlocked, PageBudgetExhausted
from decisions_probe import decision_cost, experiment_questions, parse_answers
from escalation_probe import judge_payload, parse_verdict, verdict_schema
from gemini_budget import Budget
from gemini_probe import save, validate_page
from crossing_art import partial_overlap_pairs, request_body as crossing_art_request_body, QUESTIONS as CROSSING_ART_QUESTIONS, RISK_THRESHOLD as CROSSING_ART_THRESHOLD
from geometry_repair import clipping_feedback, request_body as repair_request_body, apply_expansions
from gutter_refine import expand_dark_gutter_boxes
from balloon_refine import expand_balloon_boxes
from frame_refine import expand_frame_boxes
from fringe_refine import expand_dark_fringe_boxes
from continuity_verifier import request_body as continuity_request_body, response_verdict as continuity_response_verdict
from narrative_context import request_body as narrative_context_request_body
from inventory_guard import merged_groups, represented_orders, context_request_body as inventory_context_request_body
from openai_probe import PRICES, strict_schema, response_panels, response_usage
from split_check import QUESTION as SPLIT_QUESTION, source_region, request_body as split_request_body
from target_detail import with_source_detail, needs_source_detail
from component_refine import expand_component_boxes
from import_format import prepare_publication_image
from viewport_refine import reading_viewports

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'comic_panel_e2e'))
from adapter import build_cbz, _rectangle, IMAGE_EXTS

HERE=Path(__file__).resolve().parent
from source_completeness import SourceCompleteness, validate_proof, configuration_hashes, missing_feedback, extra_feedback
from acceptance_binding import (POLICY, validate_acceptance, validate_page_record,
                                publication_inputs, bind_manifest, validate_archive_reuse)
TRANSPORT_POLICY='explicit-connection-recovery-v6'
# An unreferenced step merges into the referenced step holding at least half of its area (a composite
# drawn within one view); the union may not grow its overlap with any other kept step by more than 5%.
MERGE_OVERLAP=0.5
MERGE_GROWTH=0.05
# Page-limit policy: final completeness of a candidate that already passed every quality check may use this much
# beyond the page limit; an Astra detector tier never starts with less than this much page budget left.
PAGE_GRACE=400_000
ASTRA_TIER_MIN=300_000


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text())


def credit_balance_rejection(error):
    """Only an explicit provider error code identifies a known quota rejection."""
    if not isinstance(error,str) or not error.startswith('HTTP 429:'):return False
    try:value=json.loads(error[len('HTTP 429:'):])
    except (ValueError,TypeError):return False
    details=value.get('error') if isinstance(value,dict) else None
    return isinstance(details,dict) and details.get('code')=='credit_balance_exhausted'


def transient_network_failure(error):
    """Recorded connection errors only; timeouts and TLS failures stay separate.

    RemoteDisconnected means the connection dropped before any response; the provider
    outcome is unknown, so recovery keeps the original hold like every other kind."""
    if not isinstance(error,str):return False
    return error=='Remote end closed connection without response' or error in {
        f'<urlopen error [Errno {code}] {message}>' for code,message in (
        (101,'Network is unreachable'),(113,'No route to host'),
        (111,'Connection refused'),(100,'Network is down'))}


def transient_server_rejection(error):
    """A narrow transport classification, never evidence of zero provider cost.

    Besides the structured JSON body, accepts only the exact recorded edge-proxy reset text."""
    if error=='HTTP 503: upstream connect error or disconnect/reset before headers. reset reason: connection termination':return True
    if not isinstance(error,str) or not error.startswith('HTTP 503:'):return False
    try:value=json.loads(error[len('HTTP 503:'):])
    except (ValueError,TypeError):return False
    details=value.get('error') if isinstance(value,dict) else None
    return (isinstance(details,dict) and details.get('type')=='server_error'
            and isinstance(details.get('message'),str) and bool(details['message'].strip())
            and 'param' in details and details['param'] is None
            and 'code' in details and details['code'] is None)


def gateway_failure(error):
    """An HTTP 500/502/503/504 whose body is an edge or proxy gateway page, not a provider JSON verdict."""
    if not isinstance(error,str) or not re.match(r'HTTP 50[0234]: ',error):return False
    body=error[9:].lower()
    return body.lstrip().startswith('<') and any(word in body for word in ('bad gateway','gateway time-out','gateway timeout','service unavailable','internal server error'))


def transient_failure(error):
    return transient_server_rejection(error) or transient_network_failure(error) or gateway_failure(error)


def responses_output_exhausted(raw):
    """Known output exhaustion only; never retry refusal or malformed output."""
    if not isinstance(raw,dict) or raw.get('status')!='incomplete':return False
    details=raw.get('incomplete_details');output=raw.get('output')
    if not isinstance(details,dict) or details.get('reason')!='max_output_tokens' or not isinstance(output,list):return False
    for item in output:
        if not isinstance(item,dict) or item.get('type') not in ('reasoning','message'):return False
        reasoning=item['type']=='reasoning'
        content=item.get('content',[] if reasoning else None)
        if not isinstance(content,list):return False
        part_type='reasoning_text' if reasoning else 'output_text'
        if any(not isinstance(part,dict) or part.get('type')!=part_type or not isinstance(part.get('text'),str) for part in content):return False
        if reasoning:
            summary=item.get('summary',[])
            if not isinstance(summary,list) or any(not isinstance(part,dict) or part.get('type')!='summary_text' or not isinstance(part.get('text'),str) for part in summary):return False
    return True


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
                source_map.append(prepare_publication_image(path,pages/f'{len(source_map)+1:04d}',
                    pages/'source-auxiliary/original-images',source_locator=path.relative_to(extracted).as_posix()))
            else:
                dest=pages/'source-auxiliary'/path.relative_to(extracted)
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    if not source_map:raise ValueError('input contains no comic page images')
    for record in source_map:
        with Image.open(pages/record['image']) as im:
            im.load();record['width'],record['height']=im.size
    result={'source':str(source),'source_sha256':source_id,'pages':source_map,'render_cache':str(render_cache) if render_cache else None}
    save(manifest,result);return result


class Client:
    def __init__(self,key,budget,root,retry_unknown=(),retry_rejected=(),retry_transient=(),retry_interrupted=(),retry_second=(),page_cap=None,auto_transient=False):
        self.key=key;self.budget=budget;self.root=root;root.mkdir(parents=True,exist_ok=True)
        # Optional per-page spend limit (micro-USD); cached responses never count against it.
        if page_cap is not None and (type(page_cap) is not int or page_cap<=0):raise ValueError('Invalid page spend limit')
        # Counts settled costs of this page's new calls (full reservation only when a call fails unsettled);
        # reservations held by in-flight calls never count, so parallel checks cannot trip the limit early.
        self.page_cap=page_cap;self.page_spent=0;self.page_grace=False
        self.auto_transient=auto_transient
        self.lock=threading.RLock();self.new_calls=0;self.cache_hits=0
        self.retry_unknown=set(retry_unknown)
        self.retry_rejected=set(retry_rejected)
        self.retry_transient=set(retry_transient)
        self.retry_interrupted=set(retry_interrupted)
        self.retry_second=set(retry_second)
        groups=(self.retry_unknown,self.retry_rejected,self.retry_transient,self.retry_interrupted,self.retry_second)
        if sum(map(len,groups))!=len(set().union(*groups)):raise ValueError('Ambiguous recovery type')

    def start_page(self):
        self.page_spent=0;self.page_grace=False

    def charge_cached(self,*identities):
        """A cached answer costs nothing now, but a cold first pass would have paid for it: charge its recorded
        cost to the page so cached and cold runs make identical page-limit decisions."""
        if self.page_cap is None:return
        if self.page_spent>=self.page_cap+(PAGE_GRACE if self.page_grace else 0):
            raise PageBudgetExhausted(f'page spend limit reached: {self.page_spent} of {self.page_cap} micro-USD')
        for identity in identities:
            entry=self.budget.entries[identity];self.page_spent+=entry.get('cost',entry.get('reserve',0))

    def page_remaining(self):
        return None if self.page_cap is None else self.page_cap-self.page_spent

    def http(self,endpoint,body):
        req=urllib.request.Request('https://api.openai.com/v1/'+endpoint,data=json.dumps(body).encode(),
            headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=600 if endpoint=='responses' else 180) as response:return json.load(response)
        except urllib.error.HTTPError as e:
            raise RunBlocked(f'HTTP {e.code}: '+e.read().decode(errors='replace').replace(self.key,'[REDACTED]')) from None

    def second_recovery(self,identity,first,endpoint,kind):
        """One more explicit recovery, only after the first recovery itself failed transiently."""
        path=Path(self.budget.entries[first]['path'])
        error=read(path/'error.json').get('error','') if (path/'error.json').is_file() else ''
        if not transient_failure(error):
            raise RunBlocked('second recovery requires a recorded transient failure of the first recovery: '+first)
        saved=read(path/'request.json') if (path/'request.json').is_file() else {}
        if (saved.get('request_id')!=first or saved.get('request_fingerprint')!=identity
                or saved.get('retry_of')!=identity or saved.get('endpoint')!=endpoint or saved.get('kind')!=kind):
            raise RunBlocked('second recovery requires the first recovery provenance: '+first)
        return hashlib.sha256(('explicit-second-transient-recovery-1:'+identity).encode()).hexdigest()

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
                    self.charge_cached(identity);self.cache_hits+=1
                    return read(response),{'request_id':identity,'path':str(old),'cached':True}
                recoveries={kind:hashlib.sha256((f'explicit-{kind}-recovery-1:'+identity).encode()).hexdigest()
                            for kind in ('timeout','quota','transient-server','interruption')}
                second=hashlib.sha256(('explicit-second-transient-recovery-1:'+identity).encode()).hexdigest()
                if second in self.budget.entries:
                    recovered=Path(self.budget.entries[second]['path']);response=recovered/'response.json'
                    if not response.is_file():raise RunBlocked('second recovery also unknown; no further replay: '+second)
                    self.charge_cached(identity,second);self.cache_hits+=1
                    return read(response),{'request_id':second,'retry_of':identity,'path':str(recovered),'cached':True}
                failed_recovery=None
                for recovery in recoveries.values():
                    if recovery in self.budget.entries:
                        recovered=Path(self.budget.entries[recovery]['path']);response=recovered/'response.json'
                        if not response.is_file():
                            if identity not in self.retry_second:raise RunBlocked('recovery also unknown; no further replay: '+recovery)
                            failed_recovery=recovery;break
                        self.charge_cached(identity,recovery);self.cache_hits+=1
                        return read(response),{'request_id':recovery,'retry_of':identity,'path':str(recovered),'cached':True}
                recorded=read(old/'error.json').get('error','') if (old/'error.json').is_file() else ''
                if (self.auto_transient and failed_recovery is None and transient_failure(recorded)
                        and identity not in self.retry_unknown | self.retry_rejected | self.retry_interrupted):
                    # One automatic recovery of a recorded transient transport/gateway failure; hold kept.
                    self.retry_transient.add(identity)
                if failed_recovery is None and identity not in self.retry_unknown | self.retry_rejected | self.retry_transient | self.retry_interrupted:
                    raise RunBlocked('previous unknown request; no automatic replay: '+identity)
                error=read(old/'error.json').get('error','') if (old/'error.json').is_file() else ''
                if failed_recovery is not None:
                    # Original and failed first-recovery holds both remain; this is the last attempt.
                    recovery=self.second_recovery(identity,failed_recovery,endpoint,kind)
                elif identity in self.retry_interrupted:
                    original=read(old/'request.json') if (old/'request.json').is_file() else {}
                    proof=read(old/'interruption.json') if (old/'interruption.json').is_file() else {}
                    if (original.get('request_id')!=identity or original.get('request_fingerprint')!=identity
                            or original.get('retry_of') is not None or original.get('endpoint')!=endpoint
                            or original.get('kind')!=kind or (old/'error.json').exists()
                            or proof.get('kind')!='confirmed_process_loss' or proof.get('request_id')!=identity
                            or proof.get('request_sha256')!=sha(old/'request.json')
                            or proof.get('process_not_running') is not True
                            or not isinstance(proof.get('observed_at'),str) or not proof['observed_at'].strip()
                            or not isinstance(proof.get('evidence'),str) or not proof['evidence'].strip()):
                        raise RunBlocked('interruption recovery requires confirmed process-loss evidence: '+identity)
                    recovery=recoveries['interruption']
                elif identity in self.retry_unknown:
                    if not any(word in error.lower() for word in ('timed out','timeout')):
                        raise RunBlocked('explicit recovery requires a recorded timeout: '+identity)
                    recovery=recoveries['timeout']
                elif identity in self.retry_rejected:
                    if not credit_balance_rejection(error):
                        raise RunBlocked('quota recovery requires a recorded credit-balance rejection: '+identity)
                    recovery=recoveries['quota']
                else:
                    if not transient_failure(error):
                        raise RunBlocked('transient recovery requires a recorded structured HTTP 503 or connection error: '+identity)
                    original=read(old/'request.json') if (old/'request.json').is_file() else {}
                    if (original.get('request_id')!=identity or original.get('request_fingerprint')!=identity
                            or original.get('retry_of') is not None or original.get('endpoint')!=endpoint
                            or original.get('kind')!=kind):
                        raise RunBlocked('transient recovery requires the original request provenance: '+identity)
                    # Keep the original hold; reserve a distinct one-shot identity below.
                    recovery=recoveries['transient-server']
                retry_of=identity;identity=recovery
            if self.page_cap is not None and self.page_spent>=self.page_cap+(PAGE_GRACE if self.page_grace else 0):
                raise PageBudgetExhausted(f'page spend limit reached: {self.page_spent} of {self.page_cap} micro-USD')
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
            elif kind=='detector':
                output_limit=body.get('max_output_tokens',8192)
                if type(output_limit) is not int or not 1<=output_limit<=16384:
                    raise RunBlocked('unsupported detector output allowance')
                reserve,inp,out_rate=PRICES[body['model']]
                reserve=max(reserve,math.ceil(20000*inp+output_limit*out_rate))
            else:
                output_limit=body.get('max_output_tokens',8192)
                if type(output_limit) is not int or not 1<=output_limit<=32768:
                    raise RunBlocked('unsupported verifier output allowance')
                _,inp,out_rate=PRICES[body['model']];reserve=math.ceil(60000*inp+output_limit*out_rate)
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
        settled=False
        try:
            raw=self.http(endpoint,body);save(out/'response.json',raw)
            with self.lock:
                if kind=='native':
                    cost=decision_cost(raw.get('usage',{}))
                    if cost is None or cost>reserve:raise RunBlocked('native usage missing/excessive')
                    self.budget.append({'kind':'settle','id':identity,'cost':cost,'usage':raw['usage'],'endpoint':'decisions'})
                    self.budget.entries[identity]['cost']=cost
                else:self.budget.settle(identity,response_usage(raw))
                self.page_spent+=self.budget.entries[identity]['cost'];settled=True
            save(out/'timing.json',{'seconds':time.monotonic()-started})
            if kind!='native':print(f'  {kind} completed in {time.monotonic()-started:.1f}s',flush=True)
            return raw,{'request_id':identity,'retry_of':retry_of,'path':str(out),'cached':False}
        except Exception as e:
            if not settled:
                with self.lock:self.page_spent+=reserve
            message=str(e).replace(self.key,'[REDACTED]')
            if not (out/'error.json').exists():save(out/'error.json',{'error':message})
            if self.auto_transient and retry_of is None and transient_failure(message):
                return self.request(endpoint,body,kind)
            raise RunBlocked('request failed; durable reservation retained when unsettled: '+message) from None


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


def source_page_context(records, pages_root):
    """Up to two actual predecessors, before any bounded validation selection."""
    return {str((pages_root/record['image']).resolve()):
            [str((pages_root/previous['image']).resolve()) for previous in records[max(0,i-2):i]]
            for i,record in enumerate(records)}


def prepare_analysis_image(image, output, number):
    """Preserve publication bytes; create a resumable upright JPEG analysis copy."""
    if image.suffix.lower() in ('.jpg','.jpeg'):return image
    analysis=output/f'analysis-{number:04d}.jpg'
    provenance=output/f'analysis-{number:04d}.json'
    source_hash=sha(image)
    if provenance.exists():
        record=read(provenance)
        if record['publication_sha256']!=source_hash or sha(analysis)!=record['analysis_sha256']:
            raise ValueError('analysis source or cached pixels changed')
        return analysis
    if analysis.exists():raise ValueError('unfinalized analysis image; preserve and inspect before resuming')
    with Image.open(image) as im:
        rgba=im.convert('RGBA');matte=Image.new('RGBA',rgba.size,'white')
        matte.alpha_composite(rgba);matte.convert('RGB').save(analysis,quality=95)
    save(provenance,{'publication_sha256':source_hash,'analysis_sha256':sha(analysis),
        'transform':'upright source composited on white, JPEG quality95'})
    return analysis


class Converter:
    def __init__(self,client,root,source_context=None,reading_direction='ltr',reading_margin=False):
        self.client=client;self.root=root;self.bundles={};self.judgments={};self.history={}
        self.source_context=source_context or {}
        if reading_direction not in ('ltr','rtl','auto'):raise ValueError('Invalid reading direction')
        self.reading_direction=reading_direction;self.reading_margin=reading_margin

    def responses_with_output_recovery(self,request,kind):
        """Opt-in recovery for detector and source-continuity output exhaustion."""
        raw,provenance=self.client.request('responses',request,kind)
        limit=request.get('max_output_tokens')
        if limit in (4096,8192) and responses_output_exhausted(raw):
            recovery={'original_request':provenance,'original_status':raw['status'],
                      'incomplete_details':copy.deepcopy(raw['incomplete_details']),
                      'original_output_limit':limit,'expanded_output_limit':limit*2}
            # A different bounded request, not transport retry_of. Both raw
            # responses remain durable; either result is reused on resumption.
            expanded={**request,'max_output_tokens':limit*2}
            raw,provenance=self.client.request('responses',expanded,kind)
            provenance={**provenance,'output_limit_recovery':recovery}
        return raw,provenance

    def detect(self,page,tier):
        remaining=self.client.page_remaining() if hasattr(self.client,'page_remaining') else None
        if tier=='astra' and remaining is not None and remaining<ASTRA_TIER_MIN:
            raise PageBudgetExhausted(f'page budget too low to start the Astra tier: {remaining} micro-USD left')
        model,effort,promptfile={'sol-low':('gpt-6-sol','low','prompt-v10.txt'),
            'sol-high':('gpt-6-sol','high','prompt-v10.txt'),'astra':('gpt-6-astra','high','prompt-v10.txt')}[tier]
        if self.reading_direction!='ltr':promptfile='prompt-v11-direction.txt'
        prompt=(HERE/promptfile).read_text();data=page.read_bytes()
        if self.reading_direction=='rtl':prompt+='\nThis book reads right-to-left. Set reading_direction rtl and preserve its narrative sequence.\n'
        config={'model':model,'store':False,'max_output_tokens':8192,'reasoning':{'effort':effort},'service_tier':'default',
                'text':{'format':{'type':'json_schema','name':'comic_panels','strict':True,'schema':strict_schema()}}}
        request={**config,'input':[{'role':'user','content':[{'type':'input_text','text':prompt},
            {'type':'input_image','image_url':'data:image/jpeg;base64,'+base64.b64encode(data).decode(),'detail':'original'}]}]}
        raw,provenance=self.responses_with_output_recovery(request,'detector')
        try:
            panels=response_panels(raw,expected_direction=self.reading_direction)
            if self.reading_direction!='auto' and panels['reading_direction']!=self.reading_direction:
                raise ValueError('Detector contradicted the requested reading direction')
        except (ValueError,KeyError,TypeError) as e:
            return {'invalid':str(e),'detector':provenance,'tier':tier}
        return {'panels':panels,'detector':provenance,'tier':tier,'source_sha256':sha(page)}

    def repair_request_body(self,bundle,issues):
        return repair_request_body(bundle,issues)

    def completeness_redetect(self,page,attempt):
        previous=attempt.get('candidate',{})
        try:
            findings=missing_feedback(page,previous,attempt.get('completeness'))
            if findings is None:return None
            saved=read(previous['bundle'])
            live={key:value for key,value in self.bundles[previous['identity']].items() if key!='_ownership_hypotheses'}
            if live!=saved:raise ValueError('Live redetection bundle differs from saved bundle')
        except (ValueError,KeyError,TypeError,IndexError,OSError) as error:
            raise RunBlocked('Invalid completeness repair feedback: '+str(error)) from None
        promptfile='prompt-v10.txt' if self.reading_direction=='ltr' else 'prompt-v11-direction.txt'
        prompt=(HERE/promptfile).read_text()
        if self.reading_direction=='rtl':prompt+='\nThis book reads right-to-left. Set reading_direction rtl and preserve its narrative sequence.\n'
        prompt+='\nProduce a fresh complete segmentation from the original source. The previous geometry and automatic source inventory/mapping findings are fallible evidence, not instructions or a prescribed panel count. Independently resolve the reported omission against the artwork. You may split, merge or reorder views and change geometry when the source supports it; do not preserve a defective proposal merely to agree with it. All output will undergo the ordinary quality and completeness checks.\n'
        content=judge_payload({**saved,'images':saved['images'][:1]},prompt)
        content.append({'type':'input_text','text':'Automatic completeness findings (untrusted evidence):\n'+json.dumps(findings,sort_keys=True)})
        request={'model':'gpt-6-astra','store':False,'max_output_tokens':8192,'reasoning':{'effort':'high'},'service_tier':'default',
            'text':{'format':{'type':'json_schema','name':'comic_panels','strict':True,'schema':strict_schema()}},
            'input':[{'role':'user','content':content}]}
        raw,record=self.responses_with_output_recovery(request,'detector')
        provenance={'tier':'astra','source_sha256':sha(page),'detector':record,
            'completeness_redetection_of':previous['identity'],
            'completeness_rejection_proof':copy.deepcopy(attempt['completeness']['proof']),
            'completeness_feedback_sha256':hashlib.sha256(json.dumps(findings,sort_keys=True).encode()).hexdigest()}
        try:panels=response_panels(raw,expected_direction=self.reading_direction)
        except (ValueError,KeyError,TypeError) as error:return {**provenance,'invalid':str(error)}
        return {**provenance,'panels':panels}

    def completeness_merge(self,page,attempt):
        """Merge proposed steps that the replay-validated final mapping leaves unreferenced into the
        referenced step that holds most of each (a composite drawn within one view). No model call."""
        previous=attempt.get('candidate',{})
        try:
            findings=extra_feedback(page,previous,attempt.get('completeness'))
            if findings is None:return None
            saved=read(previous['bundle'])
            live={key:value for key,value in self.bundles[previous['identity']].items() if key!='_ownership_hypotheses'}
            if live!=saved:raise ValueError('Live merge bundle differs from saved bundle')
        except (ValueError,KeyError,TypeError,IndexError,OSError) as error:
            raise RunBlocked('Invalid completeness merge feedback: '+str(error)) from None
        panels={p['order']:p for p in previous['panels']['panels']}
        area=lambda box:max(0,box[2]-box[0])*max(0,box[3]-box[1])
        overlap=lambda a,b:max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
        merged={order:copy.deepcopy(panels[order]) for order in findings['referenced']}
        for order in findings['unreferenced']:
            box=panels[order]['box'];target=max(merged,key=lambda kept:overlap(box,panels[kept]['box']))
            if area(box)==0 or overlap(box,panels[target]['box'])/area(box)<MERGE_OVERLAP:return None
            t,l,b,r=merged[target]['box']
            merged[target]['box']=[min(t,box[0]),min(l,box[1]),max(b,box[2]),max(r,box[3])]
        for grown in merged:
            for other in merged:
                if other!=grown and (overlap(merged[grown]['box'],merged[other]['box'])-overlap(panels[grown]['box'],panels[other]['box'])
                        >MERGE_GROWTH*area(panels[other]['box'])):return None
        kept=[merged[order] for order in findings['referenced']]
        for index,panel in enumerate(kept,1):panel['order']=index
        value={**copy.deepcopy(previous['panels']),'panels':kept}
        return {'tier':'astra','source_sha256':sha(page),'completeness_merge_of':previous['identity'],
                'completeness_rejection_proof':copy.deepcopy(attempt['completeness']['proof']),
                'merged_orders':list(findings['unreferenced']),
                'viewport_padding_applied':previous.get('viewport_padding_applied',False),'panels':value}

    def repair(self,page,attempt):
        issues=clipping_feedback(attempt)
        if not issues:return None
        previous=attempt['candidate'];bundle=self.bundles[previous['identity']]
        raw,request=self.client.request('responses',self.repair_request_body(bundle,issues),'detector')
        provenance={'tier':'astra','source_sha256':sha(page),'detector':request,
                    'repair_of':previous['identity'],'repair_issues':issues,
                    'viewport_padding_applied':previous.get('viewport_padding_applied',False)}
        try:panels=apply_expansions(previous['panels'],response_panels(raw,expected_direction=previous['panels']['reading_direction']),issues)
        except (ValueError,KeyError,TypeError) as e:return {**provenance,'invalid':str(e)}
        return {**provenance,'panels':panels or previous['panels'],'repair_changed':panels is not None}

    def pixel_repair(self,page,attempt):
        issues=clipping_feedback(attempt)
        if not issues:return None
        previous=attempt['candidate'];bundle=self.bundles[previous['identity']]
        targets={target for issue in issues for target in issue['panels']}
        with Image.open(page) as im:rgb=np.asarray(im.convert('RGB'))
        height,width=rgb.shape[:2];boxes=[]
        for image in bundle['images'][1:]:
            points=[tuple(map(int,p.split(','))) for p in image['points'].split()]
            boxes.append([*points[0],points[2][0]+1,points[2][1]+1])
        updated,changes=expand_component_boxes(rgb,boxes)
        changes=[change for change in changes if previous['panels']['panels'][change['index']]['order'] in targets]
        if {previous['panels']['panels'][c['index']]['order'] for c in changes}!=targets:return None
        proposed=copy.deepcopy(previous['panels'])
        for change in changes:
            index=change['index'];left,top,right,bottom=updated[index];old=proposed['panels'][index]['box']
            before=boxes[index]
            proposed['panels'][index]['box']=[min(old[0],math.floor(top*1000/height)) if top<before[1] else old[0],
                min(old[1],math.floor(left*1000/width)) if left<before[0] else old[1],
                max(old[2],math.ceil(bottom*1000/height)) if bottom>before[3] else old[2],
                max(old[3],math.ceil(right*1000/width)) if right>before[2] else old[3]]
        panels=apply_expansions(previous['panels'],proposed,issues)
        if panels is None:return None
        return {'tier':'astra','source_sha256':sha(page),'detector':previous['detector'],
                'panels':panels,'repair_of':previous['identity'],'repair_issues':issues,
                'repair_changed':True,'component_changes':changes,
                'viewport_padding_applied':previous.get('viewport_padding_applied',False)}

    def refine(self,page,candidate):
        if candidate.get('invalid'):return candidate
        value=copy.deepcopy(candidate['panels'])
        with Image.open(page) as im:rgb=np.asarray(im.convert('RGB'))
        h,w=rgb.shape[:2];boxes=[[round(p['box'][1]*w/1000),round(p['box'][0]*h/1000),
            round(p['box'][3]*w/1000),round(p['box'][2]*h/1000)] for p in value['panels']]
        refined,changes=expand_dark_gutter_boxes(rgb,boxes) if value['classification']=='panels' else (boxes,[])
        if value['classification']=='panels':
            refined,balloon_changes=expand_balloon_boxes(rgb,refined);changes.extend(balloon_changes)
            refined,frame_changes=expand_frame_boxes(rgb,refined);changes.extend(frame_changes)
            refined,fringe_changes=expand_dark_fringe_boxes(rgb,refined);changes.extend(fringe_changes)
        for change in changes:
            i=change['index'];l,t,r,b=refined[i];old=value['panels'][i]['box']
            n=[math.floor(t*1000/h),math.floor(l*1000/w),math.ceil(b*1000/h),math.ceil(r*1000/w)]
            value['panels'][i]['box']=[min(old[0],n[0]),min(old[1],n[1]),max(old[2],n[2]),max(old[3],n[3])]
        margin_changes=[]
        if self.reading_margin and not candidate.get('viewport_padding_applied'):
            value,margin_changes=reading_viewports(value,w,h)
        validate_page(value,expected_direction=self.reading_direction)
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
        result={**candidate,'source_sha256':sha(page),'panels':value,'identity':identity,
                'refinement_changes':candidate.get('component_changes',[])+changes+
                    [{**change,'kind':'reading-viewport-margin'} for change in margin_changes],
                'viewport_padding_applied':bool(margin_changes) or candidate.get('viewport_padding_applied',False),
                'bundle':str(directory/'bundle.json')}
        self.history.setdefault(result['source_sha256'],[]).append(result)
        return result

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
            check={'pair':pair,'probability':probability,'request':request}
            flagged=probability>=.5
            if flagged and candidate['tier']=='astra':
                # Only after exhausting detector tiers, independently adjudicate
                # the source region with a stronger model. Uncertainty keeps the
                # warning; a distinct-view verdict still runs all other checks.
                raw,secondary_request=self.responses_with_output_recovery(continuity_request_body(region),'verifier')
                try:secondary=continuity_response_verdict(raw)
                except (ValueError,KeyError,TypeError) as e:raise RunBlocked(str(e)) from None
                check['final_tier_disambiguation']={'verdict':secondary,'request':secondary_request}
                flagged=secondary['classification']!='distinct'
                source=bundle['images'][0]['path']
                predecessors=self.source_context.get(str(Path(source).resolve()),[])
                if flagged and predecessors:
                    raw,context_request=self.responses_with_output_recovery(
                        narrative_context_request_body(predecessors,source,region),'verifier')
                    try:context=continuity_response_verdict(raw)
                    except (ValueError,KeyError,TypeError) as e:raise RunBlocked(str(e)) from None
                    check['preceding_page_disambiguation']={'verdict':context,'request':context_request,
                        'source_pages':[{'path':p,'sha256':sha(p)} for p in predecessors]}
                    flagged=context['classification']!='distinct'
            checks.append(check)
            if flagged:flags.append(pair)
        return {'flags':flags,'checks':checks}

    def check_inventory(self,candidate):
        checks=[];flags=[];seen=set()
        current=candidate['panels'] if 'panels' in candidate else self.bundles[candidate['identity']]
        earlier=[p for p in self.history.get(candidate.get('source_sha256'),[])
                 if p['identity']!=candidate['identity']]
        # Preserve the largest observed inventory across intermediate reductions.
        # At equal counts prefer the later tier's more refined geometry, rather
        # than adjudicating several nearly identical crops of the same views.
        reference=max(enumerate(earlier),key=lambda item:(len(item[1]['panels']['panels']),item[0]))[1] if earlier else None
        for previous in [reference] if reference else []:
            for group in merged_groups(previous['panels'],current):
                signature=json.dumps(group,sort_keys=True)
                if signature in seen:continue
                seen.add(signature)
                directory=Path(candidate['bundle']).parent
                region=source_region(self.bundles[candidate['identity']]['images'][0]['path'],
                    group['previous_panels'],directory/('inventory-'+hashlib.sha256(signature.encode()).hexdigest()+'.jpg'))
                raw,request=self.responses_with_output_recovery(continuity_request_body(region),'verifier')
                try:verdict=continuity_response_verdict(raw)
                except (ValueError,KeyError,TypeError) as e:raise RunBlocked(str(e)) from None
                check={'previous_tier':previous['tier'],'group':group,'source_verdict':verdict,'source_request':request}
                represented=represented_orders(group,current)
                check['represented_current_orders']=represented
                if verdict['classification']!='continuous':
                    # Detector-independent full-page context resolves architectural
                    # boundaries. Do not give the model proposed detector splits.
                    body=inventory_context_request_body(self.bundles[candidate['identity']]['images'][0]['path'],region)
                    raw,context_request=self.responses_with_output_recovery(body,'verifier')
                    try:verdict=continuity_response_verdict(raw)
                    except (ValueError,KeyError,TypeError) as e:raise RunBlocked(str(e)) from None
                    check['context_verdict']=verdict;check['context_request']=context_request
                checks.append(check)
                if verdict['classification']=='uncertain' or len(verdict['views'])>len(represented):
                    flags.append(group['current_order'])
        return {'flags':sorted(set(flags)),'checks':checks}

    def judge(self,page,candidate):
        if candidate.get('invalid'):return {'route':'escalate','structural_error':candidate['invalid']}
        identity=candidate['identity'];bundle=self.bundles[identity];prompt=(HERE/'decisions-prompt-v2.txt').read_text()
        overlap_pairs=overlap_risk_pairs(bundle['panels']) if candidate['tier']=='sol-low' and bundle['classification']=='panels' else []
        if overlap_pairs:
            verdict={'route':'escalate','overlap_pairs':overlap_pairs,
                     'reason':'overlapping or contained scenes require stronger boundary and scene detection',
                     'semantic_flags':[],'global_crop_flags':[],'target_flags':[]}
            self.judgments[identity]=verdict;return verdict
        inventory=self.check_inventory(candidate)
        if inventory['flags']:
            verdict={'route':'escalate','inventory_flags':inventory['flags'],'inventory_checks':inventory['checks'],
                     'reason':'a stronger candidate lost a previously proposed narrative view',
                     'semantic_flags':[],'global_crop_flags':[],'target_flags':[]}
            self.judgments[identity]=verdict;return verdict
        splits=self.check_splits(candidate)
        if splits['flags']:
            verdict={'route':'escalate','split_flags':splits['flags'],'split_checks':splits['checks'],'inventory_checks':inventory['checks'],
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
        crossing=self.check_crossing_art(bundle)
        verdict={**quality_route(global_answer['probabilities'],targets),'split_checks':splits['checks'],'inventory_checks':inventory['checks'],
            'crossing_art':crossing,
            'global_probabilities':global_answer['probabilities'],
            'target_probabilities':targets,'global_request':global_request,'target_requests':requests}
        if crossing['targets']:verdict['route']='escalate'
        self.judgments[identity]=verdict;return verdict

    def check_crossing_art(self,bundle):
        pairs=partial_overlap_pairs(bundle['panels']) if bundle['classification']=='panels' else []
        if not pairs:return {'pairs':[],'targets':[]}
        raw,request=self.client.request('decisions',crossing_art_request_body(bundle['images'][0]['path']),'native')
        try:probability=parse_answers(raw,CROSSING_ART_QUESTIONS)['probabilities']['crossing_art']
        except ValueError as e:raise RunBlocked(str(e)) from None
        targets=sorted({target for pair in pairs for target in pair}) if probability>=CROSSING_ART_THRESHOLD else []
        return {'pairs':pairs,'targets':targets,'probability':probability,
                'threshold':CROSSING_ART_THRESHOLD,'request':request}

    def verification(self,bundle,prompt,effort,model='gpt-6-sol'):
        config={'model':model,'store':False,'max_output_tokens':8192,'reasoning':{'effort':effort},'service_tier':'default',
            'text':{'format':{'type':'json_schema','name':'panel_quality_verdict','strict':True,'schema':verdict_schema()}}}
        raw,request=self.client.request('responses',{**config,'input':[{'role':'user','content':judge_payload(bundle,prompt)}]},'verifier')
        try:return parse_verdict(raw,len(bundle['panels'])),request
        except ValueError as e:raise RunBlocked(str(e)) from None

    def verify(self,page,candidate):
        if candidate.get('invalid'):return {'route':'escalate','structural_error':candidate['invalid']}
        bundle=self.bundles[candidate['identity']];verdict=self.judgments[candidate['identity']];checks=[];evidence=[]
        if verdict.get('overlap_pairs') or verdict.get('split_flags') or verdict.get('inventory_flags'):
            return {'route':'escalate','evidence':[],
                    'reason':'layout risk requires stronger detection, not verifier clearance'}
        crossing_targets=set(verdict.get('crossing_art',{}).get('targets',[]))
        global_model='gpt-6-astra' if candidate['tier']=='astra' and crossing_targets else 'gpt-6-sol'
        if verdict['global_crop_flags']:
            # Target checks and the global Responses verifier have demonstrated
            # false negatives. Their passes cannot erase an independent warning.
            if candidate['tier']=='sol-low':
                return {'route':'escalate','evidence':[],
                        'reason':'independent page-level clipping warning requires stronger detection'}
            answer,request=self.verification(bundle,(HERE/'judge-prompt-v2.txt').read_text(),'high',model=global_model)
            checks.append(answer['route']=='keep')
            evidence.append({'scope':'complete stronger candidate','verdict':answer,'request':request})
        elif verdict['semantic_flags']:
            answer,request=self.verification(bundle,(HERE/'judge-prompt-v2.txt').read_text(),
                                             'high' if global_model=='gpt-6-astra' else 'low',model=global_model)
            # It sees the whole candidate and can discover defects beyond the
            # original trigger. Preserve those findings even if a target passes.
            checks.append(answer['route']=='keep')
            evidence.append({'scope':'complete candidate after semantic warning','verdict':answer,'request':request})
        if candidate['tier']!='astra' and False in checks:
            return {'route':'escalate','evidence':evidence,
                    'reason':'intermediate candidate already rejected; proceed to stronger detection'}
        for target in sorted(set(verdict['target_flags']) | crossing_targets):
            local={**bundle,'images':[im for im in bundle['images'] if im['label'] in ('Original complete page',f'Candidate crop {target} in reading order')]}
            model='gpt-6-astra' if target in crossing_targets else 'gpt-6-sol'
            answer,request=self.verification(local,(HERE/'judge-target-prompt-v3.txt').read_text(),'high',model=model)
            evidence.append({'scope':'target','panel':target,'verdict':answer,'request':request,
                             'crossing_art_risk':target in crossing_targets})
            resolved_context=any(target in check['pair'] and
                check.get('preceding_page_disambiguation',{}).get('verdict',{}).get('classification')=='distinct'
                for check in verdict.get('split_checks',[]))
            if answer['route']!='keep' and candidate['tier']=='astra' and resolved_context:
                predecessors=self.source_context.get(str(Path(bundle['images'][0]['path']).resolve()),[])
                if predecessors:
                    contextual={**local,'images':local['images']+[
                        {'label':f'Preceding source page {i} of {len(predecessors)} (context only)',
                         'path':p,'sha256':sha(p)} for i,p in enumerate(predecessors,1)]}
                    answer,request=self.verification(contextual,(HERE/'judge-target-prompt-v5.txt').read_text(),
                                                     'high',model='gpt-6-astra')
                    evidence.append({'scope':'target after narrative disambiguation','panel':target,
                                     'verdict':answer,'request':request})
            if answer['route']!='keep' and needs_source_detail(candidate,answer,target):
                # A final repaired crop can be confused with incidental neighbor
                # fragments. Add source context and the exact actual crop extent;
                # retain the original warning and all independent page checks.
                detailed=with_source_detail(bundle,target,Path(candidate['bundle']).parent/'source-detail',
                                            mark_boundary=True)
                answer,request=self.verification(detailed,(HERE/'judge-target-detail-prompt-v2.txt').read_text(),
                                                 'high',model='gpt-6-astra')
                evidence.append({'scope':'repaired target with source boundary context','panel':target,
                                 'verdict':answer,'request':request,'source_details':detailed['images'][2:]})
            checks.append(answer['route']=='keep')
            if candidate['tier']!='astra' and answer['route']!='keep':
                return {'route':'escalate','evidence':evidence,
                        'reason':'intermediate target failed; proceed to stronger detection'}
        return {'route':'keep' if checks and all(checks) else 'escalate','evidence':evidence}


def final_acceptance(page, candidate, converter, guard):
    try:
        # Ownership descriptions are transient verifier hypotheses. Completeness
        # sees the exact saved geometry/images and never these descriptions.
        live=converter.bundles[candidate['identity']]
        canonical={key:value for key,value in live.items() if key!='_ownership_hypotheses'}
        saved=read(candidate['bundle'])
        if canonical!=saved:
            raise ValueError('Live candidate bundle differs from saved bundle')
        # The candidate passed every quality check: let its final completeness proof finish within the grace.
        client=getattr(converter,'client',None)
        if client is not None and hasattr(client,'page_grace'):client.page_grace=True
        try:verdict=guard.check(page,saved,candidate)
        finally:
            if client is not None and hasattr(client,'page_grace'):client.page_grace=False
        if isinstance(verdict,dict) and verdict.get('route')=='keep':
            validate_acceptance(page,candidate,verdict,validate_proof)
        return verdict
    except RunBlocked:raise
    except (ValueError,KeyError,TypeError,OSError) as error:
        raise RunBlocked('Invalid final acceptance proof: '+str(error)) from None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--ledger',type=Path,required=True);p.add_argument('--render-cache',type=Path)
    p.add_argument('--pages',help='Optional bounded source page numbers; preserve original order')
    p.add_argument('--max-new-pages',type=int,help='Checkpoint after this many new pages; resume with the same output directory')
    p.add_argument('--auto-transient-recovery',action='store_true',help='One automatic recovery of a recorded transient transport or gateway failure (original hold kept)')
    p.add_argument('--page-cap-usd',type=float,help='Per-page spend limit; a page that reaches it stops escalating and falls back to a whole-page view')
    p.add_argument('--retry-unknown',action='append',default=[],help='Explicit request fingerprint: one separately budgeted recovery of a recorded timeout; never repeats success')
    p.add_argument('--retry-rejected',action='append',default=[],help='Explicit request fingerprint after funding: one separately reserved recovery of a recorded credit-balance rejection')
    p.add_argument('--retry-interrupted',action='append',default=[],help='Explicit fingerprint after confirmed process loss; requires bound interruption evidence; one separately reserved recovery')
    p.add_argument('--retry-second-transient',action='append',default=[],help='Explicit original fingerprint: one final separately reserved recovery after the first recovery failed with a recorded transient error')
    p.add_argument('--retry-transient',action='append',default=[],help='Explicit request fingerprint: one separately reserved recovery of a recorded structured HTTP 503 or connection error')
    p.add_argument('--title',default='Automatic panel edition');p.add_argument('--execute-approved',action='store_true')
    p.add_argument('--reading-direction',choices=('auto','ltr','rtl'),default='auto',
                   help='Infer from the page by default; explicit direction overrides ambiguity without reversing pixels')
    a=p.parse_args()
    if a.max_new_pages is not None and a.max_new_pages<1:p.error('--max-new-pages must be positive')
    if a.page_cap_usd is not None and not 0<a.page_cap_usd<=100:p.error('--page-cap-usd must be in (0,100]')
    page_cap=None if a.page_cap_usd is None else round(a.page_cap_usd*1e6)
    if any(not re.fullmatch(r'[0-9a-f]{64}',v) for v in a.retry_unknown+a.retry_rejected+a.retry_transient+a.retry_interrupted+a.retry_second_transient):p.error('retry fingerprint must be SHA256')
    if not a.execute_approved:p.error('live operation requires --execute-approved')
    if datetime.now(timezone.utc).date().isoformat()>'2026-12-31':p.error('refresh pricing policy')
    key=sys.stdin.readline().strip()
    if not re.fullmatch(r'sk-[\w-]{30,}',key):p.error('valid stdin credential required')
    a.output.mkdir(parents=True,exist_ok=True)
    input_=prepare_input(a.source,a.output/'input',a.render_cache)
    analysis_paths={}
    for number,record in enumerate(input_['pages'],1):
        record['source_page']=number
        analysis_paths[number]=prepare_analysis_image(a.output/'input/pages'/record['image'],a.output,number)
    # Context keys must name the same analysis pixels the detector actually sees,
    # including PNG and normalized EXIF sources, and retain unselected predecessors.
    context=source_page_context([{'image':str(path.resolve())} for path in analysis_paths.values()],a.output)
    if a.pages:
        selected=[int(v) for v in a.pages.split(',')]
        if not selected or len(set(selected))!=len(selected) or any(v<1 or v>len(input_['pages']) for v in selected):
            p.error('invalid selected source pages')
        input_={**input_,'pages':[r for r in input_['pages'] if r['source_page'] in selected]}
    config={'policy':POLICY,'transport_policy':TRANSPORT_POLICY,'source_sha256':input_['source_sha256'],'title':a.title,
        'reading_direction':a.reading_direction,'page_cap_micro_usd':page_cap,
        'completeness_configuration_sha256s':configuration_hashes(),
        'source_pages':[r['source_page'] for r in input_['pages']],
        'source_sha256s':{str(p.relative_to(HERE.parent)):sha(p) for p in [
          *[HERE/n for n in ('auto_convert.py','automatic_escalation.py','gutter_refine.py','balloon_refine.py','frame_refine.py','fringe_refine.py','continuity-prompt-v4.txt','continuity_verifier.py','continuity-verifier-prompt-v2.txt','inventory_guard.py','inventory-context-prompt-v2.txt','narrative_context.py','narrative-context-prompt-v3.txt',
             'decisions_probe.py','escalation_probe.py','openai_probe.py','gemini_probe.py','gemini_budget.py','split_check.py','crossing_art.py','geometry_repair.py','geometry-repair-prompt-v1.txt','target_detail.py','judge-target-detail-prompt-v2.txt','component_refine.py',
             'prompt-v10.txt','prompt-v11-direction.txt','decisions-prompt-v2.txt','judge-prompt-v2.txt','judge-target-prompt-v3.txt','judge-target-prompt-v5.txt',
             'import_format.py','viewport_refine.py','scene_evidence.py','scene-evidence-prompt-v4.txt','ownership_converter.py','acceptance_binding.py','marked_native.py','base-prompt.txt','questions.json','context-guidance.txt')],
          HERE.parent/'comic_panel_e2e/adapter.py',HERE.parent/'gemini_panel_probe/contract.py']}}
    if (a.output/'run.json').exists():
        if read(a.output/'run.json')!=config:raise ValueError('run identity changed; use a new output directory')
    else:save(a.output/'run.json',config)
    outcomes=[];count=len(input_['pages']);started=time.monotonic();new_pages=0
    with Budget(a.ledger,cap=100000000) as budget:
        from marked_native import MarkedNativeConverter
        client=Client(key,budget,a.output/'calls',retry_unknown=a.retry_unknown,retry_rejected=a.retry_rejected,retry_transient=a.retry_transient,retry_interrupted=a.retry_interrupted,retry_second=a.retry_second_transient,page_cap=page_cap,auto_transient=a.auto_transient_recovery)
        converter=MarkedNativeConverter(client,a.output,context,reading_direction=a.reading_direction,reading_margin=True)
        guard=SourceCompleteness(client,a.output/'completeness')
        for i,record in enumerate(input_['pages'],1):
            analysis=analysis_paths[record['source_page']]
            publication_source=a.output/'input/pages'/record['image']
            final=a.output/f'page-{i:04d}.json'
            if final.exists():
                previous=read(final)
                validate_page_record(publication_source,analysis,record,previous,i,validate_proof)
                outcomes.append(previous);continue
            if a.max_new_pages is not None and new_pages>=a.max_new_pages:
                print(json.dumps({'status':'checkpoint','completed_pages':len(outcomes),'total_pages':count,
                    'new_calls':client.new_calls,'cache_hits':client.cache_hits,'used_held_micro_usd':budget.used()}),flush=True)
                return
            print(f'[{i}/{count}] automatic analysis; used/held ${budget.used()/1e6:.6f}',flush=True)
            client.start_page()
            result=run_page(analysis,converter.detect,converter.refine,converter.judge,converter.verify,
                            repair=converter.repair,pixel_repair=converter.pixel_repair,
                            completeness_redetect=converter.completeness_redetect,
                            completeness_merge=converter.completeness_merge,
                            final_accept=lambda page,candidate:final_acceptance(page,candidate,converter,guard))
            result={**result,'policy':POLICY,'page':i,'source_page':record['source_page'],
                    'source_sha256':record['sha256'],'analysis_source_sha256':sha(analysis)}
            if result['status']=='blocked':
                save(a.output/f'blocked-{time.time_ns()}.json',result)
                print(f'[{i}/{count}] BLOCKED: {result["reason"]}',flush=True);raise SystemExit(2)
            validate_page_record(publication_source,analysis,record,result,i,validate_proof)
            save(final,result);outcomes.append(result)
            new_pages+=1
            first_pass='' if client.page_cap is None else f'; first-pass page cost ${client.page_spent/1e6:.4f}'
            print(f'[{i}/{count}] {result["status"]}; tiers={len(result["attempts"])}; new calls={client.new_calls}; cache hits={client.cache_hits}{first_pass}; used/held ${budget.used()/1e6:.6f}',flush=True)
        stats={'new_calls':client.new_calls,'cache_hits':client.cache_hits,'used_held_micro_usd':budget.used(),'elapsed_seconds':time.monotonic()-started}
    directions={r['selected']['panels']['reading_direction'] for r in outcomes
                if r['status']=='accepted'}
    if len(directions)>1:raise ValueError('Conflicting page reading directions; provide explicit book direction before publication')
    direction=a.reading_direction if a.reading_direction!='auto' else next(iter(directions),'ltr')
    entries=[];bindings=[];expected_frames=[];fallbacks={};counts=[];publication=a.output/'publication-pages';publication.mkdir(exist_ok=True)
    if len(input_['pages'])!=len(outcomes):raise ValueError('Incomplete publication outcomes')
    for i,(record,result) in enumerate(zip(input_['pages'],outcomes),1):
        bindings.append(validate_page_record(a.output/'input/pages'/record['image'],
            analysis_paths[record['source_page']],record,result,i,validate_proof))
        if result['status']=='accepted':
            selected=result['selected']['panels'];validate_page(selected,expected_direction=direction)
            panels=selected['panels'];classification=selected['classification']
        else:
            panels=[{'box':[0,0,1000,1000]}];classification='whole_page';fallbacks[i]=result['reason']
        boxes=[]
        for panel in panels:
            y,x,b,r=panel['box'];boxes.append({'x':x/1000,'y':y/1000,'w':(r-x)/1000,'h':(b-y)/1000})
        entries.append({'page':i,'image':record['image'],'panels':boxes});counts.append(len(panels) if classification=='panels' else 0)
        target=publication/record['image']
        if not target.exists():os.link(a.output/'input/pages'/record['image'],target)
        if sha(target)!=record['sha256']:raise ValueError('publication page changed')
        with Image.open(target) as image:width,height=image.size
        # Fail before the adapter can turn malformed accepted geometry into fallback.
        expected_frames.append([_rectangle(box,width,height) for box in boxes])
    auxiliary=a.output/'input/pages/source-auxiliary'
    if auxiliary.exists() and not (publication/'source-auxiliary').exists():shutil.copytree(auxiliary,publication/'source-auxiliary')
    auxiliary_hashes=[{'source':p.relative_to(publication).as_posix(),'sha256':sha(p)}
        for p in sorted((publication/'source-auxiliary').rglob('*')) if p.is_file()]
    bound_inputs=publication_inputs(entries,bindings,expected_frames,title=a.title,
                                   direction=direction,auxiliary=auxiliary_hashes)
    output=a.output/'automatic-panels.cbz'
    manifest_path=a.output/'book.manifest.json'
    if output.exists()!=manifest_path.exists():raise ValueError('unpaired archive/manifest; inspect before resuming')
    if not output.exists():
        manifest=build_cbz(publication,{'pages':entries,'total_pages':count,'reading_direction':direction},output,title=a.title,
            source_map={i:r['source_page'] for i,r in enumerate(input_['pages'],1)},fallback_reasons=fallbacks)
        manifest=bind_manifest(manifest,bound_inputs)
        save(manifest_path,manifest)
    else:
        manifest=read(manifest_path)
        validate_archive_reuse(output,manifest,bound_inputs)
    if not (a.output/'counts.json').exists():save(a.output/'counts.json',counts[1:])
    # Keep the historical body-only file for the older reader harness. The first
    # source image may itself be a comic page with panels, including single-page
    # books; its panels remain in ACBF coverpage and count in the complete result.
    if not (a.output/'all-page-counts.json').exists():save(a.output/'all-page-counts.json',counts)
    summary={**stats,'source_sha256':input_['source_sha256'],'output_sha256':manifest['output_sha256'],
        'pages':count,'source_pages':[r['source_page'] for r in input_['pages']],
        'accepted_pages':sum(r['status']=='accepted' for r in outcomes),'fallback_pages':list(fallbacks),
        'escalated_pages':[r['page'] for r in outcomes if len(r['attempts'])>1],
        'refined_pages':[r['page'] for r in outcomes if r['selected'] and r['selected'].get('refinement_changes')],
        'panel_steps':sum(counts),'panel_counts':counts,'body_panel_steps':sum(counts[1:]),
        'human_routing_decisions':0,'evaluation_labels_read':False}
    save(a.output/f'completed-{time.time_ns()}.json',summary);print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
