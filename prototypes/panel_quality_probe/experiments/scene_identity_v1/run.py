"""Frozen research runner. Execute only inside disposable VM153."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from protocol import (HERE, LIMIT, SpikeBudget, experiment_used, identity_body,
                      parse_identities, verifier_body, fingerprint, auxiliary)
from auto_convert import Client
from escalation_probe import parse_verdict
from gemini_probe import save
from target_detail import with_source_detail

ROOT = Path('/home/tester/comic-reader')
OUTPUT = ROOT/'evidence/scene-identity-controls-v1-20261009'
LEDGER = ROOT/'evidence/gemini-10usd-20261008.jsonl'
EVIDENCE = ROOT/'evidence'
ORIGINAL = EVIDENCE/'full-sequential-v21-20261008/candidates/9a4e20b4791052df33a3c1065e6049124182d8dc42b3e08991f83e9c1ccb6ec1/bundle.json'
CORRECTED = EVIDENCE/'crossing-art-regression-v23-20261009/candidates/336c8c32736fda4e69aaa3f5db415680ef9360cdada05395aa288b6d0b838871/bundle.json'
OLD = EVIDENCE/'target-detail-controls-sol-v2-20261009/original150.json'
SOURCE_SHA = 'ce13e97dcf81deb016a7b3201c59d2ff1e07c0e1638cd8690fe8a1341d397e92'
BASELINE_ID = '4efdac1289b76037e683147f7ac131fa2c68ac028d5b150afd388f862ca4e043'
# Evaluation-only. Never passed to a request builder or model.
EVALUATION = {
    'a': {'target': 3, 'expected': 'defect', 'evidence': 'Upper bouquet and ribbon of the lower carrying scene are absent.'},
    'b': {'target': 3, 'expected': 'intact', 'evidence': 'The same lower carrying scene includes the whole bouquet, ribbon, figures and lettering.'},
    'c': {'target': 2, 'expected': 'intact', 'evidence': 'Middle doorway/carriage scene is intact; the clipped bouquet belongs to scene 3.'},
}
SEQUENCE = [('baseline', c) for c in ('a', 'b', 'c')] + [('identity', c) for c in ('a', 'b', 'c')] + [(condition, c) for condition in ('rotated', 'omitted') for c in ('a', 'b')]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def structural_score(verdict, expected, target):
    """Evidence still needs independent visual review; these are routing gates."""
    if expected == 'defect':
        return {'harmful_accept': verdict['route'] == 'keep',
                'routing_pass': verdict['decision'] == 'escalate' and
                verdict['scene_inventory'] == 'pass' and verdict['reading_order'] == 'pass' and
                verdict['crop_coverage'] == 'fail' and
                any(target in i['panels'] and i['kind'] in ('clipped_art', 'clipped_text')
                    for i in verdict['issues'])}
    return {'harmful_accept': False, 'routing_pass': verdict['route'] == 'keep'}


def prepare():
    if OUTPUT.exists():
        raise ValueError('Run exists; inspect it, never overwrite preparation')
    OUTPUT.mkdir(parents=True)
    original, corrected = read(ORIGINAL), read(CORRECTED)
    assert original['images'][0]['sha256'] == corrected['images'][0]['sha256'] == SOURCE_SHA
    assert [p['order'] for p in original['panels']] == [p['order'] for p in corrected['panels']] == [1, 2, 3]
    old = read(OLD)
    bundles = {'a': old['bundle'],
               'b': with_source_detail(corrected, 3, OUTPUT/'details-b', mark_boundary=True),
               'c': with_source_detail(corrected, 2, OUTPUT/'details-c', mark_boundary=True)}
    assert fingerprint(verifier_body(bundles['a'])) == BASELINE_ID == old['request']['request_id']
    for code, bundle in bundles.items():
        # Hash-verify every image and build exact baseline body before paid work.
        verifier_body(bundle)
        save(OUTPUT/f'input-{code}.json', bundle)
    save(OUTPUT/'generator-input.json', original)
    save(OUTPUT/'evaluation-only.json', EVALUATION)
    run = {'purpose': 'Frozen three-control scene-assistance development screen; no runtime integration',
           'frozen_at': datetime.now(timezone.utc).isoformat(), 'ceiling_micro_usd': LIMIT,
           'max_new_calls': 10, 'sequence': SEQUENCE,
           'generator': {'model': 'gpt-6-astra', 'reasoning': 'high', 'proposal_path': str(ORIGINAL), 'proposal_sha256': sha(ORIGINAL)},
           'verifier': {'model': 'gpt-6-sol', 'reasoning': 'high'},
           'source_sha256': SOURCE_SHA, 'existing_baseline_request': BASELINE_ID,
           'rotated_mapping': {'1': 2, '2': 3, '3': 1},
           'same_scene_correspondence': {'a': 3, 'b': 3, 'c': 2},
           'stop': 'First treatment/robustness harmful acceptance, invalid output, unknown request, or budget block; no retries or tuning.',
           'quality_gate': 'All scored controls pass routing AND negative evidence is visually correct; uncertainty is not a pass.',
           'scope': 'One source, one defect. No independence/generalization or E2E claim.',
           'frozen_files': {str(p): sha(p) for p in [*HERE.glob('*.py'), *HERE.glob('*.txt'),
                              *[HERE.parents[1]/n for n in ('judge-target-detail-prompt-v2.txt',
                                'auto_convert.py', 'escalation_probe.py', 'gemini_budget.py',
                                'openai_probe.py', 'gemini_probe.py', 'target_detail.py')],
                              *OUTPUT.glob('input-*.json'), OUTPUT/'generator-input.json', OUTPUT/'evaluation-only.json']}}
    save(OUTPUT/'run.json', run)
    print('Prepared frozen controls; baseline fingerprint matches saved request; no calls dispatched', flush=True)


def execute():
    if (OUTPUT/'complete.json').exists() or (OUTPUT/'stopped.json').exists():
        raise ValueError('Experiment already terminal; do not replay')
    manifest = read(OUTPUT/'run.json')
    for name, digest in manifest['frozen_files'].items():
        if sha(Path(name)) != digest:
            raise ValueError('Frozen file changed: '+name)
    if fingerprint(verifier_body(read(OUTPUT/'input-a.json'))) != BASELINE_ID:
        raise ValueError('Known baseline body changed; no paid dispatch')
    if datetime.now(timezone.utc).date().isoformat() > '2026-12-31':
        raise ValueError('Verify expired pricing before paid work')
    key = sys.stdin.readline().strip()
    if not key.startswith('sk-'):
        raise ValueError('Missing credential on stdin')
    results = []
    with SpikeBudget(LEDGER, OUTPUT) as budget:
        client = Client(key, budget, OUTPUT/'calls')
        try:
            # Known baseline must be reused; two missing baselines measured once.
            if BASELINE_ID not in budget.entries or not (Path(budget.entries[BASELINE_ID]['path'])/'response.json').exists():
                raise ValueError('Known baseline cache missing; no redispatch')
            identities = None
            for index, (condition, code) in enumerate(SEQUENCE, 1):
                if condition != 'baseline' and identities is None:
                    print('[generator 1/1] source-only identity generation', flush=True)
                    generator_bundle = read(OUTPUT/'generator-input.json')
                    raw, request = client.request('responses', identity_body(generator_bundle), 'detector')
                    identities = parse_identities(raw, [p['order'] for p in generator_bundle['panels']])
                    save(OUTPUT/'identities.json', {'result': identities, 'request': request})
                    for variant in ('identity', 'rotated', 'omitted'):
                        (OUTPUT/f'auxiliary-{variant}.txt').write_text(auxiliary(identities, variant))
                print(f'[verifier {index}/{len(SEQUENCE)}] {condition} case {code}', flush=True)
                bundle = read(OUTPUT/f'input-{code}.json')
                raw, request = client.request('responses', verifier_body(bundle, identities, condition), 'verifier')
                verdict = parse_verdict(raw, len(bundle['panels']))
                score = structural_score(verdict, EVALUATION[code]['expected'], EVALUATION[code]['target'])
                result = {'condition': condition, 'case': code, 'request': request, 'verdict': verdict, **score}
                results.append(result)
                save(OUTPUT/f'{condition}-{code}.json', result)
                print(json.dumps({'condition': condition, 'case': code, 'verdict': verdict,
                                  'used_or_held_micro_usd': budget.used(), **score}), flush=True)
                if condition != 'baseline' and score['harmful_accept']:
                    raise ValueError('Known defective crop accepted; remaining calls stopped')
            save(OUTPUT/'complete.json', {'results': results, 'routing_gate_pass': all(r['routing_pass'] for r in results if r['condition'] != 'baseline'),
                                         'visual_evidence_review': 'pending; routing alone is insufficient'})
        except Exception as error:
            save(OUTPUT/'stopped.json', {'reason': str(error).replace(key, '[REDACTED]'), 'results': results,
                                        'not_completed': SEQUENCE[len(results):]})
            raise
        finally:
            save(OUTPUT/'spend.json', {'new_calls_this_process': client.new_calls, 'cache_hits_this_process': client.cache_hits,
                                      'experiment_used_or_held_micro_usd': experiment_used(budget.entries, OUTPUT),
                                      'total_used_or_held_micro_usd': budget.used(), 'ceiling_micro_usd': LIMIT})


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['prepare', 'execute'])
    action = p.parse_args().action
    prepare() if action == 'prepare' else execute()
