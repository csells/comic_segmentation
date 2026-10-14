"""Native Decisions API diagnostic; frozen image bundles, no geometry mutations."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request

from escalation_probe import cached_verdict, judge_payload
from gemini_budget import Budget
from gemini_probe import save

MODEL = 'gpt-6-luna'
ENDPOINT = 'https://api.openai.com/v1/decisions'
THRESHOLD = 0.5
# Conservative hold: four questions * model maximum 922k input * $0.20/M
# long-context rate * 1.2 regional allowance < $1. No output billing.
# Reported input usage is settled at the documented global endpoint rate.
RESERVATION = 1000000
QUESTIONS = [
    {'type':'predicate','name':'scene_defect','instructions':
     'Does the proposed segmentation omit a distinct scene, merge distinct scenes, falsely split one continuous scene, duplicate a scene, or incorrectly classify a multi-scene page as whole_page? Use the original page to inventory scenes independently. Covers, credits and single continuous splash compositions may correctly be whole_page. Overlapping inset rectangles and neighboring fragments alone are not defects.'},
    {'type':'predicate','name':'order_defect','instructions':
     'Are the proposed scene steps in the wrong narrative reading order for the stated reading direction? Judge scene order, including insets, rather than strict geometric sorting. A whole_page composition has no panel-order defect.'},
    {'type':'predicate','name':'text_clipping','instructions':
     'Does any proposed crop cut off associated lettering or part of a speech/thought balloon visible in the original? A shared balloon with tails or thought dots into two scenes must be complete in both crops. Compare all crop edges with the original; the full-page overview does not excuse clipped panel text. Ignore lettering in incidental fragments of neighboring scenes.'},
    {'type':'predicate','name':'art_clipping','instructions':
     'Does any proposed crop trim visible artwork belonging to that scene, including subjects or objects breaking its frame? Inspect all edges, including bottom and right, against the original. Extra gutter and neighboring fragments from rectangular crops of angled/overlapping panels are acceptable. Distinguish a source-drawn panel boundary from an erroneous crop through artwork.'},
]

OPTIMIZED_QUESTIONS = [
    {'type':'predicate','name':'scene_defect','instructions':
     'The candidate has a genuine scene-inventory error: a narrative scene is missing, two distinct narrative panels are merged, or one continuous scene is falsely split. Evaluate the proposed TARGET scenes, not decorative boundaries. Covers, introductions, title/credits/biography pages with illustrative strips are intentionally whole_page, even if the decoration contains multiple pictures. A splash is also whole_page. Nested inset scenes may overlap the background rectangle. These permitted cases are NOT scene errors. Is a genuine inventory error present?'},
    {'type':'predicate','name':'order_defect','instructions':
     'The ordered TARGET scenes violate the narrative reading sequence for the stated direction. Insets may be read before or after their background; geometric overlap alone is not wrong order. Whole-page introductory/credits/splash layouts have no panel ordering defect. Is there a genuine wrong-order error?'},
    {'type':'predicate','name':'text_clipping','instructions':
     'At least one TARGET scene crop removes lettering or an associated speech/thought balloon that is visible in that scene in the unmodified original page. The same shared balloon must be complete for each of its speakers. Do NOT count lettering belonging to another inset or neighboring scene incidentally visible in the rectangle. Do NOT count anything covered by diagnostic overlay labels/lines; only the original and actual crop determine clipping. A balloon meeting the original drawn border is not crop damage. Does genuine target-scene text clipping occur?'},
    {'type':'predicate','name':'art_clipping','instructions':
     'At least one TARGET scene crop excludes artwork visibly belonging to that scene in the original, such as a border-breaking ear, limb, clothing or object. Compare candidate crop edge with the ORIGINAL SCENE edge. A subject cut by the original frame was drawn that way and is not erroneous. Incidental fragments of OTHER inset/neighboring scenes, source page edges, overlay labels and the source artist\'s black frame are not clipping defects. Does genuine target-scene artwork clipping occur?'},
]


def experiment_questions(variant):
    if variant == 'target-v3':
        return OPTIMIZED_QUESTIONS[2:]
    return QUESTIONS if variant == 'v1' else OPTIMIZED_QUESTIONS


def experiment_bundle(bundle, variant):
    if variant == 'target-v3':
        target = bundle['target_order']
        if type(target) is not int or target < 1:
            raise ValueError('invalid target order')
        images = [im for im in bundle['images'] if im['label'] in (
            'Original complete page',f'Candidate crop {target} in reading order')]
        if len(images) != 2:
            raise ValueError('missing target image')
        return {**bundle,'images':images}
    if variant != 'clean-v2':
        return bundle
    return {**bundle, 'images':[im for im in bundle['images']
            if im['label'] != 'Proposed rectangles numbered in reading order']}


def parse_answers(raw, questions=None):
    questions = QUESTIONS if questions is None else questions
    if not isinstance(raw, dict) or not str(raw.get('model','')).startswith(MODEL):
        raise ValueError('unexpected Decisions model')
    answers = raw.get('answers')
    if not isinstance(answers, list) or len(answers) != len(questions):
        raise ValueError('missing Decisions answers; never keep')
    probabilities = {}
    for question, answer in zip(questions, answers):
        if (not isinstance(answer, dict) or answer.get('type') != 'predicate'
                or answer.get('name') != question['name']):
            raise ValueError('refused/mismatched Decisions answer; never keep')
        probability = answer.get('probability')
        if type(probability) not in (int, float) or not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError('invalid Decisions probability; never keep')
        probabilities[question['name']] = probability
    return {'route':'escalate' if max(probabilities.values()) >= THRESHOLD else 'keep',
            'threshold':THRESHOLD,'probabilities':probabilities}


def decision_cost(usage):
    if 'input_tokens' not in usage:
        return None
    tokens = usage['input_tokens']
    if (type(tokens) is not int or tokens < 0 or usage.get('output_tokens') != 0
            or usage.get('total_tokens') != tokens):
        raise ValueError('unexpected native Decisions usage; retain hold')
    # Gross-input estimate, without assuming any cache discount.
    rate = Decimal('0.2') if tokens > 272000 else Decimal('0.1')
    return math.ceil(tokens * rate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','output','ledger','prompt'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--execute-approved-comparison', action='store_true')
    parser.add_argument('--variant', choices=('v1','prompt-v2','clean-v2','target-v3'), default='v1')
    a = parser.parse_args()
    if datetime.now(timezone.utc).date().isoformat() > '2026-12-31':
        parser.error('verify expired pricing policy')
    cases = json.loads(a.manifest.read_text())
    if (not 1 <= len(cases) <= 100 or len({c['id'] for c in cases}) != len(cases)
            or any(not re.fullmatch(r'case-\d{2}(?:-panel-\d{2})?',c['id']) for c in cases)):
        parser.error('expected 1..100 unique prepared case/target identifiers')
    a.output.mkdir(parents=True, exist_ok=False)
    prompt = a.prompt.read_text()
    config = {'model':MODEL,'questions':experiment_questions(a.variant)}
    save(a.output/'run.json', {'endpoint':ENDPOINT,'config':config,'prompt':prompt,
         'cases':cases,'threshold':THRESHOLD,'rule':'escalate if any predicate >= threshold; invalid/refused stops',
         'reservation_micro_usd':RESERVATION,'ledger':str(a.ledger),
         'execution_approved':a.execute_approved_comparison,'variant':a.variant,
         'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'pricing_source':'https://developers.openai.com/api/docs/guides/decisions',
         'pricing':'$0.10/M input; 2x above 272k; zero output; gross-input estimate'})
    key = None
    if a.execute_approved_comparison:
        key = sys.stdin.readline().strip()
        if not re.fullmatch(r'sk-[\w-]{30,}',key):
            raise SystemExit('No valid API key; no request sent')
    results = []
    with Budget(a.ledger, cap=20000000) as budget:
        for i, case in enumerate(cases, 1):
            bundle_path = Path(case['bundle'])
            bundle = experiment_bundle(json.loads(bundle_path.read_text()),a.variant)
            case_prompt = prompt
            if a.variant == 'target-v3':
                case_prompt += f'\nONLY judge TARGET scene {bundle["target_order"]}. The second image is its actual crop. The other geometries provide context only; do not evaluate their crops.\n'
            request = {**config,'input':[{'role':'user','content':judge_payload(bundle,case_prompt)}]}
            encoded = json.dumps(request, sort_keys=True).encode()
            if len(encoded) > 19000000 or len(bundle['images']) > 128:
                raise ValueError('request exceeds local size limit; not sent')
            identity = hashlib.sha256(ENDPOINT.encode()+b'\n'+encoded).hexdigest()
            out = a.output/case['id']; out.mkdir()
            save(out/'request.json', {'request_id':identity,'endpoint':ENDPOINT,'config':config,
                 'prompt':case_prompt,'bundle':bundle,'request_bytes':len(encoded),
                 'expected_labels_sent':False,'bundle_sha256':hashlib.sha256(bundle_path.read_bytes()).hexdigest()})
            if not a.execute_approved_comparison:
                print(f'[{i}/{len(cases)}] {case["id"]}: prepared offline',flush=True)
                continue
            old = cached_verdict(budget.entries,identity)
            if old:
                raw = json.loads((old/'response.json').read_text())
                verdict = parse_answers(raw,config['questions'])
                save(out/'verdict.json',verdict)
                result = {'id':case['id'],'request_id':identity,'reused_from':str(old),
                          'status':'completed_unscored','verdict':verdict,'cost_micro_usd':0,
                          'elapsed_seconds':0,'model':raw['model'],'cached_usage':raw['usage']}
                save(out/'result.json',result); results.append(result)
                print(f'[{i}/{len(cases)}] {case["id"]}: saved decision reused; {verdict["route"]}',flush=True)
                continue
            started = time.monotonic(); attempted = False
            try:
                budget.reserve(identity,out.resolve(),RESERVATION,0.1,0.5)
                attempted = True
                print(f'[{i}/{len(cases)}] {case["id"]}: Decisions request; used/held ${budget.used()/1e6:.6f}',flush=True)
                req = urllib.request.Request(ENDPOINT,data=encoded,
                    headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=120) as response:
                    raw = json.load(response)
                    save(out/'response-headers.json',{'request_id':response.headers.get('x-request-id')})
                save(out/'response.json',raw)
                cost = decision_cost(raw.get('usage',{}))
                if cost is None or cost > RESERVATION:
                    raise ValueError('missing/excessive usage; retain hold and stop')
                budget.append({'kind':'settle','id':identity,'cost':cost,'usage':raw['usage'],
                               'endpoint':'decisions','pricing':'gross-input-only estimate'})
                budget.entries[identity]['cost'] = cost
                verdict = parse_answers(raw,config['questions']); save(out/'verdict.json',verdict)
                result = {'id':case['id'],'request_id':identity,'status':'completed_unscored',
                          'verdict':verdict,'usage':raw['usage'],'cost_micro_usd':cost,'model':raw['model']}
            except Exception as error:
                if isinstance(error,urllib.error.HTTPError):
                    message = f'HTTP {error.code}: '+error.read().decode(errors='replace')
                else:
                    message = str(error)
                result = {'id':case['id'],'request_id':identity,'status':'failed','route':'stop',
                          'attempted':attempted,'error':message.replace(key,'[REDACTED]')}
            result['elapsed_seconds'] = round(time.monotonic()-started,3)
            save(out/'result.json',result); results.append(result)
            print(f'[{i}/{len(cases)}] {case["id"]}: {result["status"]}; {result.get("verdict",{}).get("route", "stop")}; used/held ${budget.used()/1e6:.6f}',flush=True)
            if result['status'] == 'failed': break
        save(a.output/'results.json',results)
    if any(r.get('status') == 'failed' for r in results): raise SystemExit(2)


if __name__ == '__main__': main()
