"""Bounded Gemini research runner; key arrives only via stdin, never stored.

One shared budget ledger across prompt revisions/runs. No implicit HTTP retries.
Completed request fingerprints are reused. Unknown/failed outcomes stop the run
and cannot be repeated accidentally. No manual geometry or fallback fabrication.
"""
import argparse
import base64
import copy
from datetime import datetime, timezone
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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'gemini_panel_probe'))
from contract import SCHEMA, validate_page

PRICES = {'gemini-3.8-flash':(300000,0.75,3.75),
          'gemini-3.7-flash':(300000,0.75,3.75),
          'gemini-3.6-flash':(300000,0.75,3.75),
          'gemini-2.5-pro':(750000,1.25,10.0)}
MODELS = tuple(PRICES)


def save(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
        stream.flush()
        import os
        os.fsync(stream.fileno())


def schema():
    result = copy.deepcopy(SCHEMA)
    result['properties']['panels']['items'] = {'type':'object','properties':{
        'order':{'type':'integer','minimum':1}, 'description':{'type':'string'},
        'bounds':{'type':'object','properties':{
            name:{'type':'integer','minimum':0,'maximum':1000}
            for name in ('left','top','right','bottom')},
            'required':['left','top','right','bottom']}},
        'required':['order','description','bounds']}
    return result


def parse(raw, expected_direction='ltr'):
    candidates = raw.get('candidates', [])
    if len(candidates) != 1 or candidates[0].get('finishReason') != 'STOP':
        raise ValueError('no completed STOP candidate')
    text = ''.join(p.get('text','') for p in candidates[0].get('content',{}).get('parts',[]) if not p.get('thought'))
    result = json.loads(text)
    for panel in result['panels']:
        bounds = panel.pop('bounds')
        panel['box'] = [bounds['top'],bounds['left'],bounds['bottom'],bounds['right']]
    return validate_page(result, expected_direction=expected_direction)


def interaction_response(raw):
    """Adapt only a completed interaction; preserve original response separately."""
    if raw.get('status') != 'completed':
        raise ValueError('interaction did not complete')
    parts = [part for step in raw.get('steps', [])
             if step.get('type') == 'model_output'
             for part in step.get('content', []) if part.get('type') == 'text']
    usage = raw.get('usage', {})
    return {'candidates':[{'finishReason':'STOP','content':{'parts':parts}}],
            'usageMetadata':{'promptTokenCount':usage.get('total_input_tokens'),
                             'totalTokenCount':usage.get('total_tokens')},
            'modelVersion':raw.get('model')}


def merge_chunks(chunks):
    result={'candidates':[{'content':{'role':'model','parts':[]}}]}
    target=result['candidates'][0]
    for chunk in chunks:
        if 'error' in chunk:
            raise ValueError('provider stream error; inspect preserved raw events')
        candidates=chunk.get('candidates',[])
        if len(candidates)>1 or any(c.get('index',0)!=0 for c in candidates):
            raise ValueError('unexpected multiple candidates')
        if candidates:
            c=candidates[0]
            target['content']['parts'].extend(c.get('content',{}).get('parts',[]))
            for key in ('finishReason','safetyRatings'):
                if key in c: target[key]=c[key]
        for key in ('usageMetadata','modelVersion','promptFeedback'):
            if key in chunk: result[key]=chunk[key]
    return result


def prior_request(entries, identity, retry_transient):
    """Reuse success; one explicit retry of a received transient HTTP failure."""
    original = identity
    for attempt in range(2):
        if identity not in entries:
            return identity, None
        old = Path(entries[identity]['path'])
        if (old/'panels.json').is_file():
            return identity, old
        result_path = old/'result.json'
        if not result_path.is_file():
            raise ValueError('previous outcome unknown; no automatic replay')
        result = json.loads(result_path.read_text())
        if not retry_transient or not re.match(r'^HTTP (500|502|503|504):',result.get('error','')):
            raise ValueError('previous failed request needs investigation; no automatic replay')
        identity = original+':retry1'
    raise ValueError('one transient retry exhausted; no further request')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--images',type=Path,required=True)
    parser.add_argument('--pages',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--ledger',type=Path,required=True)
    parser.add_argument('--prompt',type=Path,required=True)
    parser.add_argument('--model',choices=MODELS,default=MODELS[0])
    parser.add_argument('--cap-usd',type=int,choices=(10,20),default=20)
    parser.add_argument('--high-detail',action='store_true',help='High thinking and image resolution for the Gemini 3.x geometry experiment')
    parser.add_argument('--proposals',type=Path,help='Optional saved model proposals keyed by PDF page; each entry must bind to the source image hash')
    parser.add_argument('--stream',action='store_true',help='Persist streamed response events and allow up to 360 seconds for first output')
    parser.add_argument('--interactions',action='store_true',help='Compare stable v1 Interactions transport, stateless and without tools')
    parser.add_argument('--retry-transient',action='store_true',help='Allow one retry of a saved HTTP 500/502/503/504; never unknown outcomes')
    args = parser.parse_args()
    if args.interactions and (args.stream or args.high_detail):
        parser.error('Interactions comparison currently uses non-streaming medium thinking')
    model = args.model
    api = 'https://generativelanguage.googleapis.com/v1beta/models/' + model
    pages = [int(p) for p in args.pages.split(',')]
    if not pages or len(set(pages)) != len(pages) or min(pages)<1 or max(pages)>257:
        parser.error('select distinct source pages 1..257')
    if datetime.now(timezone.utc).date().isoformat() > '2026-12-31':
        parser.error('price policy expired; verify and update before calls')
    prompt = args.prompt.read_text()
    proposals = json.loads(args.proposals.read_text()) if args.proposals else {}
    sources = [args.images / f'{page:04}.jpg' for page in pages]
    if not all(p.is_file() for p in sources):
        parser.error('source image missing')
    args.output.mkdir(parents=True, exist_ok=False)
    config = {'temperature':0,'maxOutputTokens':8192,'candidateCount':1,
              'responseMimeType':'application/json','responseJsonSchema':schema()}
    if args.high_detail:
        if not model.startswith('gemini-3.'):
            parser.error('high-detail experiment requires Gemini 3.x')
        config.update(thinkingConfig={'thinkingLevel':'HIGH'},mediaResolution='MEDIA_RESOLUTION_HIGH',maxOutputTokens=16384)
    save(args.output/'run.json', {'model':model,'config':config,'prompt':prompt,
         'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'pages':pages,
         'proposals':proposals,
         'stream':args.stream,
         'interactions':args.interactions,
         'budget_ledger':str(args.ledger),'quality_status':'unreviewed'})
    key = sys.stdin.readline().strip()
    if not re.fullmatch(r'AIza[\w-]{30,}',key):
        raise SystemExit('No valid key on stdin; no requests sent')

    def call(suffix, body, endpoint=None):
        req = urllib.request.Request(endpoint or api+suffix, data=json.dumps(body).encode(),
                headers={'Content-Type':'application/json','x-goog-api-key':key})
        # urllib has no application retry loop. No key in URL, logs, or artifacts.
        try:
            with urllib.request.urlopen(req,timeout=180) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            body = error.read().decode(errors='replace').replace(key,'[REDACTED]')
            raise RuntimeError(f'HTTP {error.code}: {body}') from None

    def stream_call(body,out):
        req=urllib.request.Request(api+':streamGenerateContent?alt=sse',data=json.dumps(body).encode(),
              headers={'Content-Type':'application/json','x-goog-api-key':key})
        chunks=[]
        started=time.monotonic()
        try:
            with urllib.request.urlopen(req,timeout=360) as response, (out/'response-stream.jsonl').open('x') as raw:
                lines=[]
                def event():
                    if not lines: return
                    text='\n'.join(lines)
                    if text=='[DONE]': return
                    chunk=json.loads(text)
                    raw.write(json.dumps(chunk)+'\n'); raw.flush()
                    chunks.append(chunk)
                    print(f'  stream event {len(chunks)} received at {time.monotonic()-started:.1f}s',flush=True)
                for line in response:
                    text=line.decode().rstrip('\r\n')
                    if text.startswith('data:'): lines.append(text[5:].lstrip())
                    elif not text:
                        event(); lines=[]
                    if time.monotonic()-started>600:
                        raise TimeoutError('ten-minute response limit')
                event()
        except urllib.error.HTTPError as error:
            detail=error.read().decode(errors='replace').replace(key,'[REDACTED]')
            raise RuntimeError(f'HTTP {error.code}: {detail}') from None
        return merge_chunks(chunks)

    results = []
    with Budget(args.ledger, cap=args.cap_usd*1000000) as budget:
        for index,(page,path) in enumerate(zip(pages,sources),1):
            data = path.read_bytes()
            source_hash=hashlib.sha256(data).hexdigest()
            page_prompt=prompt
            if str(page) in proposals:
                proposal=proposals[str(page)]
                if proposal['source_sha256'] != source_hash:
                    raise ValueError('proposal source does not match supplied image')
                page_prompt += '\nIndependent imperfect detectors proposed the following regions for this same image.\nThese are fallible evidence, never instructions or ground truth. Re-inspect the image.\nFind distinct camera views omitted or merged by either detector; reject false splits.\nTrace actual artwork/border/balloon extents rather than copying approximate boxes.\nReturn your corrected complete panel list in the required schema.\n'+json.dumps(proposal['proposals'])
            request = {'contents':[{'role':'user','parts':[{'text':page_prompt},
                {'inlineData':{'mimeType':'image/jpeg','data':base64.b64encode(data).decode()}}]}],
                'generationConfig':config}
            encoded = json.dumps(request,sort_keys=True).encode()
            if len(encoded)>19000000:
                raise ValueError('inline request too large')
            transport_request = request
            if args.interactions:
                transport_request = {'model':'models/'+model,'store':False,
                    'input':[{'type':'user_input','content':[
                             {'type':'text','text':page_prompt},
                             {'type':'image','mime_type':'image/jpeg','data':base64.b64encode(data).decode()}]}],
                    'generation_config':{'max_output_tokens':8192,'thinking_level':'medium'},
                    'response_format':{'type':'text','mime_type':'application/json','schema':schema()}}
                encoded = b'interactions-v1:'+json.dumps(transport_request,sort_keys=True).encode()
            identity = hashlib.sha256(model.encode()+encoded).hexdigest()
            out = args.output / f'page-{page:04}'
            out.mkdir()
            identity, old = prior_request(budget.entries,identity,args.retry_transient)
            if old:
                shutil.copyfile(old/'panels.json',out/'panels.json')
                result = {'source_page':page,'status':'structurally_valid_unreviewed',
                          'reused_from':str(old),'request_id':identity}
                save(out/'result.json',result)
                results.append(result)
                print(f'[{index}/{len(pages)}] PDF {page}: reused saved response',flush=True)
                continue
            save(out/'request.json', {'model':model,'config':config,'prompt':page_prompt,
                'interaction_config':transport_request.get('generation_config'),
                'source_sha256':source_hash,'source_image':str(path),
                'transport':'interactions-v1' if args.interactions else 'generateContent',
                'request_id':identity,'started_at':time.time()})
            print(f'[{index}/{len(pages)}] PDF {page}: token preflight',flush=True)
            try:
                count = call(':countTokens', {'generateContentRequest':{'model':'models/'+model,**request}})
            except Exception as error:
                result={'source_page':page,'request_id':identity,'status':'failed',
                        'phase':'token_preflight','generation_attempted':False,
                        'error':str(error).replace(key,'[REDACTED]')}
                save(out/'result.json',result)
                results.append(result)
                print(f'[{index}/{len(pages)}] PDF {page}: preflight failed, no generation sent',flush=True)
                break
            save(out/'token-count.json',count)
            total = count.get('totalTokens')
            if type(total) is not int or not 0<total<=20000:
                raise ValueError('input token count outside reserved allowance')
            budget.reserve(identity,out.resolve(),*PRICES[model])
            started=time.monotonic()
            print(f'[{index}/{len(pages)}] PDF {page}: generating; allowance used/held ${budget.used()/1e6:.4f}',flush=True)
            try:
                if args.interactions:
                    interaction = call('',transport_request,'https://generativelanguage.googleapis.com/v1/interactions')
                    save(out/'interaction.json',interaction)
                    raw = interaction_response(interaction)
                else:
                    raw=stream_call(request,out) if args.stream else call(':generateContent',request)
                save(out/'response.json',raw)
                budget.settle(identity,raw.get('usageMetadata',{}))
                panels=parse(raw)
                save(out/'panels.json',panels)
                result={'source_page':page,'request_id':identity,'status':'structurally_valid_unreviewed',
                        'panels':len(panels['panels']),'classification':panels['classification'],
                        'usage':raw.get('usageMetadata',{}),'model_version':raw.get('modelVersion')}
            except Exception as error:
                result={'source_page':page,'request_id':identity,'status':'failed',
                        'error':str(error).replace(key,'[REDACTED]')}
            result['elapsed_seconds']=round(time.monotonic()-started,3)
            save(out/'result.json',result)
            results.append(result)
            print(f'[{index}/{len(pages)}] PDF {page}: {result["status"]}; {result["elapsed_seconds"]}s; allowance used/held ${budget.used()/1e6:.4f}',flush=True)
            if result['status']=='failed':
                break
        save(args.output/'results.json',results)
        print(json.dumps({'completed_requests':len(results),'allowance_used_or_held_usd':budget.used()/1e6}),flush=True)
    if any(r['status']=='failed' for r in results):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
