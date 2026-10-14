"""Blinded decision-model research on saved segmentation; never edits geometry."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request

from gemini_budget import Budget, usage_cost
from gemini_probe import save
from openai_probe import PRICES, response_usage

CHECKS = ('scene_inventory', 'reading_order', 'crop_coverage')
KINDS = ('missing_scene', 'merged_scenes', 'false_split', 'clipped_text',
         'clipped_art', 'wrong_order', 'wrong_classification', 'uncertain')
MAX_INPUT = 60000
MAX_OUTPUT = 8192


def verdict_schema():
    properties = {'decision': {'type':'string','enum':['accept','escalate','uncertain']}}
    properties.update({k:{'type':'string','enum':['pass','fail','uncertain']} for k in CHECKS})
    issue = {'kind':{'type':'string','enum':list(KINDS)},
             'panels':{'type':'array','items':{'type':'integer','minimum':1}},
             'evidence':{'type':'string'}}
    properties['issues'] = {'type':'array','items':{'type':'object','properties':issue,
        'required':list(issue),'additionalProperties':False}}
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


def parse_verdict(raw, panel_count):
    if raw.get('status') != 'completed':
        raise ValueError('judge response incomplete; never accept')
    texts = []
    for item in raw.get('output', []):
        if item.get('type') != 'message':
            continue
        if item.get('status') not in ('completed', None):
            raise ValueError('judge message incomplete')
        for part in item.get('content', []):
            if part.get('type') == 'refusal':
                raise ValueError('judge refusal; never accept')
            if part.get('type') == 'output_text':
                texts.append(part['text'])
    try:
        value = json.loads(''.join(texts))
    except (ValueError, TypeError) as error:
        raise ValueError('judge JSON missing or invalid') from error
    if not isinstance(value, dict) or set(value) != {'decision', *CHECKS, 'issues'}:
        raise ValueError('judge verdict fields invalid')
    if value['decision'] not in ('accept','escalate','uncertain') or any(
            value[k] not in ('pass','fail','uncertain') for k in CHECKS):
        raise ValueError('judge verdict enum invalid')
    if not isinstance(value['issues'], list):
        raise ValueError('judge issues invalid')
    for issue in value['issues']:
        if (not isinstance(issue, dict) or set(issue) != {'kind','panels','evidence'}
                or issue['kind'] not in KINDS or not isinstance(issue['panels'], list)
                or any(type(n) is not int or not 1 <= n <= panel_count for n in issue['panels'])
                or not isinstance(issue['evidence'], str) or not issue['evidence'].strip()):
            raise ValueError('judge issue invalid')
    keep = value['decision'] == 'accept' and not value['issues'] and all(value[k] == 'pass' for k in CHECKS)
    return {**value, 'route':'keep' if keep else 'escalate'}


def cached_verdict(entries, identity):
    if identity not in entries:
        return None
    old = Path(entries[identity]['path'])
    if not (old/'verdict.json').is_file():
        raise ValueError('previous judge outcome failed/unknown; no automatic replay')
    return old


def judge_payload(bundle, prompt):
    # Explicit whitelist: evaluation labels, source run/provider and page IDs
    # are intentionally absent from the request, including image filenames.
    candidate = {k:bundle[k] for k in ('classification','reading_direction','panels')}
    content = [{'type':'input_text','text':prompt + '\nCandidate geometry:\n' + json.dumps(candidate)}]
    for image in bundle['images']:
        data = Path(image['path']).read_bytes()
        if 'sha256' in image and hashlib.sha256(data).hexdigest() != image['sha256']:
            raise ValueError('judge input image changed')
        content.append({'type':'input_text','text':image['label']})
        content.append({'type':'input_image','image_url':'data:image/jpeg;base64,' + base64.b64encode(data).decode(),
                        'detail':'original'})
    return content


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','output','ledger','prompt'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--model', choices=tuple(PRICES), required=True)
    p.add_argument('--reasoning', choices=('low','medium','high'), default='high')
    p.add_argument('--execute-approved-comparison', action='store_true')
    a = p.parse_args()
    if datetime.now(timezone.utc).date().isoformat() > '2026-12-31':
        p.error('verify expired pricing policy')
    cases = json.loads(a.manifest.read_text())
    if not 1 <= len(cases) <= 20 or len({c['id'] for c in cases}) != len(cases):
        p.error('expected 1..20 unique cases')
    if any(not re.fullmatch(r'[a-z0-9-]+', c['id']) for c in cases):
        p.error('invalid case identity')
    a.output.mkdir(parents=True, exist_ok=False)
    prompt = a.prompt.read_text()
    config = {'model':a.model,'store':False,'max_output_tokens':MAX_OUTPUT,
              'reasoning':{'effort':a.reasoning},'service_tier':'default',
              'text':{'format':{'type':'json_schema','name':'panel_quality_verdict',
                               'strict':True,'schema':verdict_schema()}}}
    _, input_rate, output_rate = PRICES[a.model]
    reservation = usage_cost({'promptTokenCount':MAX_INPUT,'totalTokenCount':MAX_INPUT+MAX_OUTPUT},
                             input_rate, output_rate)
    save(a.output/'run.json', {'config':config,'prompt':prompt,'cases':cases,
         'max_input_tokens':MAX_INPUT,'reservation_micro_usd':reservation,
         'ledger':str(a.ledger),'execution_approved':a.execute_approved_comparison})
    key = None
    if a.execute_approved_comparison:
        key = sys.stdin.readline().strip()
        if not re.fullmatch(r'sk-[\w-]{30,}', key):
            raise SystemExit('No valid API key; no call sent')

    def call(endpoint, body):
        request = urllib.request.Request('https://api.openai.com/v1/'+endpoint,
            data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=360) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f'HTTP {error.code}: '+error.read().decode(errors='replace').replace(key,'[REDACTED]')) from None

    results = []
    with Budget(a.ledger, cap=20000000) as budget:
        for i, case in enumerate(cases, 1):
            bundle_path = Path(case['bundle'])
            bundle = json.loads(bundle_path.read_text())
            request = {**config,'input':[{'role':'user','content':judge_payload(bundle, prompt)}]}
            encoded = json.dumps(request, sort_keys=True).encode()
            if len(encoded) > 19000000:
                raise ValueError('judge request too large')
            identity = hashlib.sha256(b'comic-escalation-judge-v1:'+encoded).hexdigest()
            out = a.output/case['id']; out.mkdir()
            save(out/'request.json', {'request_id':identity,'config':config,'prompt':prompt,
                 'bundle':bundle,'bundle_sha256':hashlib.sha256(bundle_path.read_bytes()).hexdigest(),
                 'request_bytes':len(encoded),'expected_labels_sent':False})
            if not a.execute_approved_comparison:
                print(f'[{i}/{len(cases)}] {case["id"]}: prepared offline', flush=True)
                continue
            old = cached_verdict(budget.entries, identity)
            if old:
                verdict = json.loads((old/'verdict.json').read_text());save(out/'verdict.json',verdict)
                results.append({'id':case['id'],'request_id':identity,'reused_from':str(old),'verdict':verdict})
                print(f'[{i}/{len(cases)}] {case["id"]}: saved verdict reused',flush=True)
                continue
            start = time.monotonic(); reserved = False
            try:
                print(f'[{i}/{len(cases)}] {case["id"]}: token preflight', flush=True)
                count = call('responses/input_tokens', {k:request[k] for k in ('model','input','text','reasoning')})
                save(out/'token-count.json', count)
                if type(count.get('input_tokens')) is not int or not 0 < count['input_tokens'] <= MAX_INPUT:
                    raise ValueError('judge tokens outside reservation; no generation sent')
                budget.reserve(identity, out.resolve(), reservation, input_rate, output_rate); reserved = True
                print(f'[{i}/{len(cases)}] {case["id"]}: judging; used/held ${budget.used()/1e6:.6f}',flush=True)
                raw = call('responses', request);save(out/'response.json', raw)
                budget.settle(identity, response_usage(raw))
                verdict = parse_verdict(raw, len(bundle['panels']));save(out/'verdict.json', verdict)
                result = {'id':case['id'],'request_id':identity,'verdict':verdict,'usage':raw.get('usage'),
                          'model_version':raw.get('model'),'status':'completed_unscored'}
            except Exception as error:
                result = {'id':case['id'],'request_id':identity,'status':'failed','route':'stop',
                          'generation_attempted':reserved,'error':str(error).replace(key,'[REDACTED]')}
            result['elapsed_seconds'] = round(time.monotonic()-start, 3)
            save(out/'result.json', result);results.append(result)
            print(f'[{i}/{len(cases)}] {case["id"]}: {result["status"]}; used/held ${budget.used()/1e6:.6f}',flush=True)
            if result['status'] == 'failed':
                break
        save(a.output/'results.json', results)
    if any(r.get('status') == 'failed' for r in results):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
