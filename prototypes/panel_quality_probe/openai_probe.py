"""Research comparison. Preparation is offline; execution needs upload approval."""
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from gemini_budget import Budget
from gemini_probe import schema,parse,prior_request,save

# Conservative input rates include possible 1.25x cache-write pricing.
# Verified official model documentation 2026-10-08. No tools or premium tier.
PRICES={'gpt-6-astra':(700000,12.5,50),'gpt-6-sol':(140000,2.5,10),
        'gpt-6-luna':(7000,.125,.5),'gpt-5.6-luna':(15000,.25,1.2)}


def strict_schema():
    s=schema()
    def close(x):
        if isinstance(x,dict):
            if x.get('type')=='object':
                x['additionalProperties']=False
                x['required']=list(x['properties'])
            for v in x.values():close(v)
        elif isinstance(x,list):
            for v in x:close(v)
    close(s)
    return s


def response_usage(raw):
    u=raw.get('usage') or {}
    return {'promptTokenCount':u.get('input_tokens'),'totalTokenCount':u.get('total_tokens')}


def response_panels(raw, expected_direction='ltr'):
    if raw.get('status')!='completed': raise ValueError('response did not complete')
    parts=[]
    for item in raw.get('output',[]):
        if item.get('type')!='message': continue
        if item.get('status') not in ('completed',None): raise ValueError('message incomplete')
        for part in item.get('content',[]):
            if part.get('type')=='refusal': raise ValueError('provider refusal')
            if part.get('type')=='output_text': parts.append({'text':part['text']})
    return parse({'candidates':[{'finishReason':'STOP','content':{'parts':parts}}]}, expected_direction=expected_direction)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('images','output','ledger','prompt'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--pages',required=True)
    p.add_argument('--model',choices=tuple(PRICES),default='gpt-6-astra')
    p.add_argument('--reasoning',choices=('none','low','medium','high','xhigh','max'),default='high')
    p.add_argument('--execute-approved-comparison',action='store_true')
    a=p.parse_args()
    pages=[int(s) for s in a.pages.split(',')]
    if not pages or len(set(pages))!=len(pages) or min(pages)<1 or max(pages)>257: p.error('invalid pages')
    if datetime.now(timezone.utc).date().isoformat()>'2026-12-31': p.error('verify expired price policy')
    prompt=a.prompt.read_text()
    a.output.mkdir(parents=True,exist_ok=False)
    config={'model':a.model,'store':False,'max_output_tokens':8192,
            'reasoning':{'effort':a.reasoning},'service_tier':'default',
            'text':{'format':{'type':'json_schema','name':'comic_panels','strict':True,'schema':strict_schema()}}}
    save(a.output/'run.json',{'config':config,'prompt':prompt,'pages':pages,
         'budget_ledger':str(a.ledger),'execution_approved_flag':a.execute_approved_comparison,
         'quality_status':'unreviewed','source':'unchanged JPEG pages','image_detail':'original'})
    key=None
    if a.execute_approved_comparison:
        key=sys.stdin.readline().strip()
        if not re.fullmatch(r'sk-[\w-]{30,}',key): raise SystemExit('No valid API key; no request sent')

    def call(path,body):
        req=urllib.request.Request('https://api.openai.com/v1/'+path,
            data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=360) as r:return json.load(r)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'HTTP {e.code}: '+e.read().decode(errors='replace').replace(key,'[REDACTED]')) from None

    results=[]
    with Budget(a.ledger,cap=20000000) as budget:
        for i,page in enumerate(pages,1):
            source=a.images/f'{page:04}.jpg'; data=source.read_bytes()
            request={**config,'input':[{'role':'user','content':[
                {'type':'input_text','text':prompt},
                {'type':'input_image','image_url':'data:image/jpeg;base64,'+base64.b64encode(data).decode(),'detail':'original'}]}]}
            encoded=json.dumps(request,sort_keys=True).encode()
            if len(encoded)>19000000: raise ValueError('request too large')
            identity=hashlib.sha256(b'openai-responses:'+encoded).hexdigest()
            out=a.output/f'page-{page:04}';out.mkdir()
            save(out/'request.json',{'config':config,'prompt':prompt,'source_image':str(source),
                'source_sha256':hashlib.sha256(data).hexdigest(),'request_id':identity,
                'request_bytes':len(encoded),'image_detail':'original','started_at':time.time()})
            if not a.execute_approved_comparison:
                print(f'[{i}/{len(pages)}] PDF {page}: prepared offline; no upload',flush=True)
                continue
            identity,old=prior_request(budget.entries,identity,False)
            if old:
                shutil.copyfile(old/'panels.json',out/'panels.json')
                result={'source_page':page,'status':'structurally_valid_unreviewed','reused_from':str(old),'request_id':identity}
                save(out/'result.json',result);results.append(result);continue
            started=time.monotonic();reserved=False
            try:
                print(f'[{i}/{len(pages)}] PDF {page}: token preflight',flush=True)
                count=call('responses/input_tokens',{k:request[k] for k in ('model','input','text','reasoning')})
                save(out/'token-count.json',count)
                n=count.get('input_tokens')
                if type(n) is not int or not 0<n<=20000:raise ValueError('input tokens outside reservation')
                budget.reserve(identity,out.resolve(),*PRICES[a.model]);reserved=True
                print(f'[{i}/{len(pages)}] PDF {page}: generating; used/held ${budget.used()/1e6:.4f}',flush=True)
                raw=call('responses',request);save(out/'response.json',raw)
                budget.settle(identity,response_usage(raw))
                panels=response_panels(raw);save(out/'panels.json',panels)
                result={'source_page':page,'request_id':identity,'status':'structurally_valid_unreviewed',
                    'panels':len(panels['panels']),'classification':panels['classification'],
                    'usage':raw.get('usage'),'model_version':raw.get('model')}
            except Exception as error:
                result={'source_page':page,'request_id':identity,'status':'failed',
                    'generation_attempted':reserved,'error':str(error).replace(key,'[REDACTED]')}
            result['elapsed_seconds']=round(time.monotonic()-started,3)
            save(out/'result.json',result);results.append(result)
            print(f'[{i}/{len(pages)}] PDF {page}: {result["status"]}; used/held ${budget.used()/1e6:.4f}',flush=True)
            if result['status']=='failed':break
        save(a.output/'results.json',results)
    if any(r['status']=='failed' for r in results):raise SystemExit(2)

if __name__=='__main__':main()
