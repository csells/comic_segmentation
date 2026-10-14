"""Research-only request builders. No evaluation labels enter these functions."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from escalation_probe import judge_payload, verdict_schema
from gemini_budget import Budget

LIMIT = 5_000_000


def experiment_used(entries, root):
    return sum(v['cost'] for v in entries.values()
               if Path(v['path']).is_relative_to(root.resolve()))


class SpikeBudget(Budget):
    def __init__(self, ledger, output):
        super().__init__(ledger, cap=100_000_000)
        self.output = output.resolve()

    def reserve(self, identity, path, reservation, input_rate, output_rate):
        if not Path(path).is_relative_to(self.output):
            raise ValueError('Experiment reservation outside scoped output')
        if experiment_used(self.entries, self.output) + reservation > LIMIT:
            raise ValueError('Scene identity experiment $5 ceiling reached')
        super().reserve(identity, path, reservation, input_rate, output_rate)


def identity_schema():
    text = {'type': 'string', 'minLength': 1, 'maxLength': 1200}
    fields = {'order': {'type': 'integer'}, 'identity': text,
              **{key: {'type': 'array', 'items': text, 'maxItems': 6}
                 for key in ('owned_content', 'ownership_cues', 'distinguish_from_neighbors')},
              'uncertain': {'type': 'boolean'}}
    return {'type': 'object', 'additionalProperties': False,
            'properties': {'scenes': {'type': 'array', 'items': {
                'type': 'object', 'additionalProperties': False,
                'properties': fields, 'required': list(fields)}}}, 'required': ['scenes']}


def identity_body(bundle):
    source = bundle['images'][0]
    data = Path(source['path']).read_bytes()
    if hashlib.sha256(data).hexdigest() != source['sha256']:
        raise ValueError('Source changed')
    supplied = {'scenes': [{'order': p['order'], 'box': p['box']} for p in bundle['panels']],
                'box_coordinate_convention': '[top,left,bottom,right] normalized 0..1000'}
    return {'model': 'gpt-6-astra', 'store': False, 'max_output_tokens': 8192,
            'reasoning': {'effort': 'high'}, 'service_tier': 'default',
            'text': {'format': {'type': 'json_schema', 'name': 'scene_identities',
                                'strict': True, 'schema': identity_schema()}},
            'input': [{'role': 'user', 'content': [
                {'type': 'input_text', 'text': (HERE/'identity-prompt.txt').read_text()+'\n'+json.dumps(supplied)},
                {'type': 'input_image', 'detail': 'original',
                 'image_url': 'data:image/jpeg;base64,'+base64.b64encode(data).decode()}]}]}


def parse_identities(raw, orders):
    if raw.get('status') != 'completed':
        raise ValueError('Incomplete identity response; no retry')
    texts = []
    for item in raw.get('output', []):
        if item.get('type') != 'message':
            continue
        if item.get('status') not in ('completed', None):
            raise ValueError('Incomplete identity message')
        for part in item.get('content', []):
            if part.get('type') == 'refusal':
                raise ValueError('Identity refusal')
            if part.get('type') == 'output_text':
                texts.append(part['text'])
    value = json.loads(''.join(texts))
    fields = {'order', 'identity', 'owned_content', 'ownership_cues',
              'distinguish_from_neighbors', 'uncertain'}
    if not isinstance(value, dict) or set(value) != {'scenes'} or not isinstance(value['scenes'], list):
        raise ValueError('Invalid identity envelope')
    if any(not isinstance(s, dict) or set(s) != fields for s in value['scenes']):
        raise ValueError('Invalid identity fields')
    if [s['order'] for s in value['scenes']] != orders:
        raise ValueError('Identity inventory changed')
    for s in value['scenes']:
        if type(s['order']) is not int or type(s['uncertain']) is not bool:
            raise ValueError('Invalid identity types')
        if not isinstance(s['identity'], str) or not 1 <= len(s['identity']) <= 1200:
            raise ValueError('Invalid identity text')
        for field in fields - {'order', 'identity', 'uncertain'}:
            if not isinstance(s[field], list) or len(s[field]) > 6 or any(
                not isinstance(v, str) or not 1 <= len(v) <= 1200 for v in s[field]):
                raise ValueError('Invalid identity evidence')
    return value


def auxiliary(value, condition):
    value = copy.deepcopy(value)
    if condition == 'rotated':
        scenes = value['scenes']
        value['scenes'] = [{**scenes[(i+1) % len(scenes)], 'order': s['order']}
                           for i, s in enumerate(scenes)]
    elif condition == 'omitted':
        value = {'scenes': []}
    elif condition != 'identity':
        raise ValueError('Unknown identity condition')
    return (HERE/'auxiliary-prompt.txt').read_text()+'\n'+json.dumps(value, sort_keys=True)


def verifier_body(bundle, identities=None, condition='baseline'):
    prompt = (HERE.parents[1]/'judge-target-detail-prompt-v2.txt').read_text()
    if condition != 'baseline':
        prompt += auxiliary(identities, condition)
    return {'model': 'gpt-6-sol', 'store': False, 'max_output_tokens': 8192,
            'reasoning': {'effort': 'high'}, 'service_tier': 'default',
            'text': {'format': {'type': 'json_schema', 'name': 'panel_quality_verdict',
                                'strict': True, 'schema': verdict_schema()}},
            'input': [{'role': 'user', 'content': judge_payload(bundle, prompt)}]}


def fingerprint(body):
    return hashlib.sha256(b'comic-escalation-judge-v1:'+json.dumps(body, sort_keys=True).encode()).hexdigest()
