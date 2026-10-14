"""Diagnostic package: marked target evidence, generic cut clarification,
and no automatic ownership hypotheses in native target inputs.

All other native calls and all strong verifiers retain their existing behavior.
No evaluation cases, labels, targets, probabilities or thresholds live here.
"""
from pathlib import Path
import copy
import hashlib
import json
import re

from auto_convert import Converter
from automatic_escalation import RunBlocked
from decisions_probe import experiment_questions
from ownership_converter import OwnershipConverter
from target_detail import with_source_detail

HERE = Path(__file__).resolve().parent


class MarkedNativeConverter(OwnershipConverter):
    def decision(self, bundle, prompt, questions):
        if questions != experiment_questions('target-v3'):
            return super().decision(bundle, prompt, questions)
        images = bundle.get('images', [])
        if len(images) != 2 or images[0]['label'] != 'Original complete page':
            raise RunBlocked('Marked target decision requires source and exactly one actual crop')
        match = re.fullmatch(r'Candidate crop ([1-9][0-9]*) in reading order', images[1]['label'])
        if not match:
            raise RunBlocked('Marked target decision has no unambiguous target label')
        target = int(match.group(1))
        if sum(p['order'] == target for p in bundle['panels']) != 1:
            raise RunBlocked('Marked target decision target does not uniquely match geometry')
        base = (HERE/'base-prompt.txt').read_text()
        expected_prompt = base+f'\nONLY judge TARGET scene {target}. The second image is its actual crop. The other geometries provide context only; do not evaluate their crops.\n'
        if prompt != expected_prompt:
            raise RunBlocked('Unexpected target-decision prompt; no silent rewrite')
        # Strip descriptions and transient hypotheses from this native target
        # payload only. Source audit/global calls/strong verifier stay rich.
        clean = {key:bundle[key] for key in ('classification','reading_direction')}
        clean['panels'] = [{key:p[key] for key in ('order','box')} for p in bundle['panels']]
        clean['images'] = copy.deepcopy(images)
        identity = hashlib.sha256(json.dumps({'geometry':clean['panels'], 'source':images[0]['sha256'],
                                             'crop':images[1]['sha256'], 'target':target}, sort_keys=True).encode()).hexdigest()
        detailed = with_source_detail(clean, target, self.root/'marked-native'/identity, mark_boundary=True)
        instructions = expected_prompt+(HERE/'context-guidance.txt').read_text()
        marked_questions = json.loads((HERE/'questions.json').read_text())
        # Bypass only OwnershipConverter.decision's native hypothesis enrichment.
        # Converter.decision still uses the real Client and strict native parser.
        return Converter.decision(self, detailed, instructions, marked_questions)
