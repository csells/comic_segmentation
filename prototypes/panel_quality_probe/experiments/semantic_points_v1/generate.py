"""Bounded research ownership requests; run only in VM153, key on stdin."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from auto_convert import Client
from gemini_budget import Budget
from gemini_probe import save

ROOT = Path('/home/tester/comic-reader')
OUTPUT = ROOT/'evidence/semantic-points-astra-v1-20261009'
LEDGER = ROOT/'evidence/gemini-10usd-20261008.jsonl'
LIMIT = 2_000_000
CASES = [(40, 'full-sequential-v24-20261008', 'c61591c9a41df0ab6ce4275fe2a85108a37f59f00497b7a5d65796f1bc6fdd19'),
         (57, 'component-repair-page57-v28-exact-20261009', 'b5cd08f0b5768683c1a6cd351598b4da2801bbe4504fa5914672fb3060f60a8d'),
         (150, 'crossing-art-regression-v23-20261009', '336c8c32736fda4e69aaa3f5db415680ef9360cdada05395aa288b6d0b838871')]


class SpikeBudget(Budget):
    def reserve(self, identity, path, reservation, input_rate, output_rate):
        spike_used = sum(v['cost'] for v in self.entries.values()
                         if Path(v['path']).is_relative_to(OUTPUT))
        if spike_used + reservation > LIMIT:
            raise ValueError('Ownership spike $2 ceiling reached')
        super().reserve(identity, path, reservation, input_rate, output_rate)


def main():
    key = sys.stdin.readline().strip()
    if not key.startswith('sk-'):
        raise ValueError('Expected credential on stdin')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    prompt = (HERE/'ownership-prompt.txt').read_text()
    point = {'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2}
    scene = {'type': 'object', 'additionalProperties': False,
             'properties': {'order': {'type': 'integer'},
                            'exclusive_points': {'type': 'array', 'items': point, 'maxItems': 3},
                            'uncertain': {'type': 'boolean'}},
             'required': ['order', 'exclusive_points', 'uncertain']}
    schema = {'type': 'object', 'additionalProperties': False,
              'properties': {'scenes': {'type': 'array', 'items': scene}},
              'required': ['scenes']}
    manifest = {'purpose': 'Automatic semantic seeds; no reviewed geometry, no production integration',
                'model': 'gpt-6-astra', 'reasoning': 'high', 'max_new_calls': 3,
                'new_spend_ceiling_micro_usd': LIMIT, 'global_cap_micro_usd': 100000000,
                'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(), 'cases': CASES}
    save(OUTPUT/'run.json', manifest)
    with SpikeBudget(LEDGER, cap=100000000) as budget:
        client = Client(key, budget, OUTPUT/'calls')
        for page, run, identity in CASES:
            dest = OUTPUT/f'page-{page:04}.json'
            if dest.exists():
                print('Preserving completed ownership result', page, flush=True)
                continue
            bundle_path = ROOT/'evidence'/run/'candidates'/identity/'bundle.json'
            bundle = json.loads(bundle_path.read_text())
            source = ROOT/'replay-local/pages'/f'{page:04}.jpg'
            source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
            assert source_sha == bundle['images'][0]['sha256']
            supplied = json.dumps({'scenes': bundle['panels'],
                                   'box_coordinate_convention': '[top,left,bottom,right] normalized 0..1000'})
            body = {'model': 'gpt-6-astra', 'store': False, 'max_output_tokens': 8192,
                    'reasoning': {'effort': 'high'}, 'service_tier': 'default',
                    'text': {'format': {'type': 'json_schema', 'name': 'scene_interior_points',
                                        'strict': True, 'schema': schema}},
                    'input': [{'role': 'user', 'content': [
                        {'type': 'input_text', 'text': prompt+'\n'+supplied},
                        {'type': 'input_image', 'detail': 'original',
                         'image_url': 'data:image/jpeg;base64,'+base64.b64encode(source.read_bytes()).decode()}]}]}
            raw, request = client.request('responses', body, 'detector')
            if raw.get('status') != 'completed':
                raise ValueError('Ownership output incomplete; no blind retry')
            texts = [part['text'] for item in raw.get('output', []) if item.get('type') == 'message'
                     for part in item.get('content', []) if part.get('type') == 'output_text']
            result = json.loads(''.join(texts))
            if [s['order'] for s in result['scenes']] != list(range(1, len(bundle['panels'])+1)):
                raise ValueError('Ownership identities changed; stop')
            for scene in result['scenes']:
                points = scene['exclusive_points']
                if scene['uncertain'] and points:
                    raise ValueError('Uncertain scene must abstain')
                if not scene['uncertain'] and not points:
                    raise ValueError('Certain scene needs interior evidence')
                for point in points:
                    if len(point) != 2 or not all(type(v) in (int, float) and 0 < v < 1000 for v in point):
                        raise ValueError('Invalid normalized interior point')
            save(dest, {'version': 1, 'source_sha256': source_sha, 'scenes': result['scenes'],
                        'request': request, 'proposal_path': str(bundle_path),
                        'proposal_sha256': hashlib.sha256(bundle_path.read_bytes()).hexdigest()})
            print('Ownership complete', page, 'scenes', len(result['scenes']),
                  'used/held', budget.used()/1e6, flush=True)
        save(OUTPUT/'complete.json', {'new_calls': client.new_calls, 'cache_hits': client.cache_hits,
                                     'used_or_held_micro_usd': budget.used(),
                                     'spike_used_micro_usd': sum(v['cost'] for v in budget.entries.values()
                                                               if Path(v['path']).is_relative_to(OUTPUT))})


if __name__ == '__main__':
    main()
