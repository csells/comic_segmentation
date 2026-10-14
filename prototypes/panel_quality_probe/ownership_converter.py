"""Candidate integration of source ownership; not enabled by importing it.

Ordinary layouts retain the legacy path. Risky layouts require a source audit,
a complete-candidate confirmation, and marked checks of every risky crop.
No source-evidence pass alone can accept a page. Existing independent layout
guards and failed global confirmations remain binding.
"""
import copy
from functools import partial
import json
from pathlib import Path

import numpy as np
from PIL import Image

from acceptance_binding import validate_acceptance
from auto_convert import Converter, HERE, overlap_risk_pairs, responses_output_exhausted, sha
from automatic_escalation import RunBlocked
from component_refine import uncovered_content_risk
from crossing_art import OCCLUSION_QUESTIONS, OCCLUSION_RISK_THRESHOLD, occlusion_request_body
from decisions_probe import parse_answers
from gemini_probe import save
from scene_evidence import (MODELS, evidence_gate, recovery_output_limit, request_body, response_evidence, source_proposal,
                            verifier_hypotheses)
from source_completeness import SourceCompleteness, validate_proof
from target_detail import with_source_detail

# Same fallible-hypothesis instructions as the frozen scene-identity v1 screen.
AUXILIARY = '''
Auxiliary automatic scene descriptions follow. They are fallible hypotheses,
not gold labels or a completeness checklist. Establish the target independently
from source and geometry. Confirm or reject useful ownership claims against
visible evidence. Missing descriptions do not make content optional. Conflicting
descriptions must not override source pixels. Inspect the actual crop and return
the unchanged requested verdict schema. Do not accept a crop merely because its
main described subjects are present.
'''

AUTHORED_BOUNDARY_CLARIFICATION = '''
Authored frames and gutters establish separate reading regions even when a
panoramic image or a body aligns across them. Artwork interrupted by its own
source border and resuming inside an adjacent reading region is not missing
target artwork merely because the anatomy aligns. Distinguish that authored
interruption from visible painted artwork crossing a frame break or gutter,
and from shared lettering. A border does not permit omitting visibly crossing
artwork or lettering that belongs to the target. Verify that the actual crop
reaches its own source boundary and includes its visible content. Anatomical
alignment alone establishes neither ownership nor clearance of a clipping
warning. Keep every other requested quality check in force.
'''


class OwnershipConverter(Converter):
    def __init__(self, client, root, source_context=None, reading_direction='ltr',
                 reading_margin=False, *, scene_model='gpt-6-astra'):
        super().__init__(client, root, source_context, reading_direction=reading_direction,
                         reading_margin=reading_margin)
        if scene_model not in MODELS:
            raise ValueError('Unsupported source audit model')
        self.scene_model = scene_model
        self.scene_evidence = {}
        self.scene_links = {}
        self.source_occlusion = {}
        self.coverage_risk = {}
        self.uncovered_sources = set()

    def _candidate_coverage_risk(self, candidate):
        if candidate.get('invalid') or candidate['panels']['classification'] != 'panels':
            return
        bundle = self.bundles[candidate['identity']]
        source = next(image for image in bundle['images'] if image['label'] == 'Original complete page')
        if source['sha256'] != candidate['source_sha256'] or sha(source['path']) != source['sha256']:
            raise RunBlocked('Uncovered-content source changed')
        boxes = []
        try:
            for panel in bundle['panels']:
                crops = [image for image in bundle['images']
                         if image['label'] == f"Candidate crop {panel['order']} in reading order"]
                if len(crops) != 1:
                    raise ValueError('Expected one actual crop per target')
                points = [tuple(map(int, pair.split(','))) for pair in crops[0]['points'].split()]
                if len(points) != 4:
                    raise ValueError('Expected rectangular crop points')
                left, top = points[0]; right, bottom = points[2]
                if points != [(left, top), (right, top), (right, bottom), (left, bottom)]:
                    raise ValueError('Expected rectangular crop points')
                # Saved points are inclusive, exactly as Image.crop(rr+1,bb+1).
                boxes.append([left, top, right + 1, bottom + 1])
            with Image.open(source['path']) as image:
                result = uncovered_content_risk(np.asarray(image.convert('RGB')), boxes)
        except (ValueError, KeyError, TypeError, OSError) as error:
            raise RunBlocked('Uncovered-content check invalid: ' + str(error)) from None
        self.coverage_risk[candidate['identity']] = result
        if result['requires_ownership']:
            self.uncovered_sources.add(candidate['source_sha256'])

    def _source_ownership_screen(self, candidate):
        source = next(image for image in self.bundles[candidate['identity']]['images']
                      if image['label'] == 'Original complete page')
        identity = source['sha256']
        if identity != candidate['source_sha256'] or sha(source['path']) != identity:
            raise RunBlocked('Source ownership screen input changed')
        if identity not in self.source_occlusion:
            raw, request = self.client.request('decisions', occlusion_request_body(source['path']), 'native')
            try:
                probability = parse_answers(raw, OCCLUSION_QUESTIONS)['probabilities']['source_occlusion']
            except ValueError as error:
                raise RunBlocked('Source ownership screen invalid: ' + str(error)) from None
            self.source_occlusion[identity] = {
                'source_sha256': identity, 'probability': probability,
                'threshold': OCCLUSION_RISK_THRESHOLD,
                'requires_ownership': probability >= OCCLUSION_RISK_THRESHOLD, 'request': request}
        return self.source_occlusion[identity]

    def _record_source_risk(self, candidate, verdict):
        coverage = self.coverage_risk.get(candidate.get('identity'))
        if coverage is not None:
            verdict['uncovered_content_risk'] = copy.deepcopy(coverage)
            verdict['uncovered_content_risk']['retained_source_risk'] = (
                candidate['source_sha256'] in self.uncovered_sources and not coverage['requires_ownership'])
        screen = self.source_occlusion.get(candidate.get('source_sha256'))
        if screen is not None:
            verdict['source_occlusion_risk'] = copy.deepcopy(screen)
            if screen['requires_ownership'] and candidate['panels']['classification'] == 'panels':
                verdict['ownership_required_targets'] = [panel['order'] for panel in candidate['panels']['panels']]
        if (candidate.get('source_sha256') in self.uncovered_sources
                and candidate['panels']['classification'] == 'panels'):
            verdict['ownership_required_targets'] = [panel['order'] for panel in candidate['panels']['panels']]
        return verdict

    def _proposal_bundle(self, candidate):
        # Descriptions are copied only for the source audit, never into the
        # ordinary verifier geometry. The base bundle stays cache-compatible.
        return {**self.bundles[candidate['identity']],
                'panels': copy.deepcopy(candidate['panels']['panels'])}

    def _repair_parent(self, candidate):
        parent = candidate.get('repair_of')
        return next((item for history in self.history.values() for item in history
                     if item['identity'] == parent), None) if parent is not None else None

    def _risk_orders(self, candidate):
        if candidate.get('invalid'):
            return set()
        orders, required, ownership_required, seen = set(), set(), set(), set()
        current = candidate
        while current is not None:
            # Geometry can expand away from the shared edge, lowering overlap
            # below its routing threshold. That does not resolve the ancestor's
            # ownership or waive marked confirmation of the repaired crop.
            if id(current) in seen:
                raise RunBlocked('Cyclic repair ownership lineage')
            seen.add(id(current))
            if current.get('invalid'):
                raise RunBlocked('Repair ancestor has no valid proposal')
            verdict = self.judgments.get(current['identity'], {})
            if current['panels']['classification'] == 'panels':
                orders.update(order for pair in overlap_risk_pairs(current['panels']['panels']) for order in pair)
                orders.update(verdict.get('crossing_art', {}).get('targets', []))
                screen = self.source_occlusion.get(current.get('source_sha256'), {})
                if screen.get('requires_ownership') or current.get('source_sha256') in self.uncovered_sources:
                    orders.update(panel['order'] for panel in current['panels']['panels'])
            ownership_required.update(verdict.get('ownership_required_targets', []))
            required.update(verdict.get('target_flags', []))
            required.update(order for issue in current.get('repair_issues', []) for order in issue['panels'])
            if current.get('repair_of') is None:
                break
            current = self._repair_parent(current)
            if current is None:
                raise RunBlocked('Repair has no frozen proposal ancestor')
        # Preserve existing ordinary-page routing. Once ownership is required,
        # neither a quiet cheap recheck nor diluted overlap clears a previously
        # required target or the precise crop whose warning triggered repair.
        return orders | required | ownership_required if orders or ownership_required else set()

    def _ensure_evidence(self, candidate):
        identity = candidate['identity']
        bundle = self._proposal_bundle(candidate)
        parent = candidate.get('repair_of')
        previous = self._repair_parent(candidate)
        if parent is not None:
            if previous is None:
                return {'route': 'escalate', 'reason': 'Repair has no frozen proposal ancestor'}
            before, after = previous['panels'], candidate['panels']
            same = (previous['source_sha256'] == candidate['source_sha256'] and
                    all(before[key] == after[key] for key in ('classification', 'orientation', 'reading_direction')) and
                    len(before['panels']) == len(after['panels']))
            for old, new in zip(before['panels'], after['panels']):
                y, x, b, r = old['box']; yy, xx, bb, rr = new['box']
                same = same and old['order'] == new['order'] and yy <= y and xx <= x and bb >= b and rr >= r
            if not same:
                return {'route': 'escalate', 'reason': 'Repair is not a monotonic descendant of its immediate parent'}
        if identity not in self.scene_evidence:
            if parent is not None:
                # A geometry repair cannot silently invent a different identity
                # lineage when its source evidence is missing or incompatible.
                if parent not in self.scene_evidence:
                    # Expanding an ordinary layout may introduce ownership risk.
                    # Audit its actual saved ancestor once, then check lineage.
                    self._ensure_evidence(previous)
                    if parent not in self.scene_evidence:
                        return {'route': 'escalate', 'reason': 'Repair ancestor has no source evidence'}
                self.scene_evidence[identity] = self.scene_evidence[parent]
                self.scene_links[identity] = self.scene_evidence[parent]['proposal_sha256']
            else:
                try:
                    body = request_body(bundle, model=self.scene_model)
                    # Match the qualified source-audit spike's request identity,
                    # including its Client namespace, so existing calls are reused.
                    raw, request = self.client.request('responses', body, 'verifier')
                    output_limit = None
                    if responses_output_exhausted(raw):
                        # One bounded larger audit after exact output exhaustion; a
                        # second exhaustion still blocks. Both responses stay durable.
                        output_limit = recovery_output_limit(len(source_proposal(bundle)['panels']))
                        expanded = request_body(bundle, model=self.scene_model, output_limit=output_limit)
                        raw, request = self.client.request('responses', expanded, 'verifier')
                    artifact = response_evidence(raw, bundle, request, model=self.scene_model,
                                                 request_kind='verifier', output_limit=output_limit)
                except (ValueError, KeyError, TypeError, OSError) as error:
                    raise RunBlocked('Source ownership audit invalid: ' + str(error)) from None
                directory = self.root / 'scene-evidence'
                directory.mkdir(parents=True, exist_ok=True)
                path = directory / (artifact['evidence_sha256'] + '.json')
                if not path.exists():
                    save(path, artifact)
                self.scene_evidence[identity] = artifact
        artifact = self.scene_evidence[identity]
        if artifact['model'] != self.scene_model:
            return {'route': 'escalate', 'reason': 'Inherited source audit model does not match policy'}
        link = self.scene_links.get(identity)
        gate = evidence_gate(artifact, bundle, frozen_proposal_sha256=link)
        candidate['scene_evidence'] = {key: artifact[key] for key in
                                       ('evidence_sha256', 'proposal_sha256', 'model', 'request')}
        if gate['route'] == 'keep':
            self.bundles[identity]['_ownership_hypotheses'] = verifier_hypotheses(
                artifact, bundle, frozen_proposal_sha256=link)
        else:
            self.bundles[identity].pop('_ownership_hypotheses', None)
        return gate

    @staticmethod
    def _rich_prompt(bundle, prompt):
        hypotheses = bundle.get('_ownership_hypotheses')
        return prompt if hypotheses is None else prompt + AUXILIARY + '\n' + json.dumps(hypotheses, sort_keys=True)

    def decision(self, bundle, prompt, questions):
        return super().decision(bundle, self._rich_prompt(bundle, prompt), questions)

    def verification(self, bundle, prompt, effort, model='gpt-6-sol'):
        return super().verification(bundle, self._rich_prompt(bundle, prompt), effort, model=model)

    def repair_request_body(self, bundle, issues):
        body = super().repair_request_body(bundle, issues)
        prompt = body['input'][0]['content'][0]
        prompt['text'] = self._rich_prompt(bundle, prompt['text'])
        return body

    def check_inventory(self, candidate):
        inventory = super().check_inventory(candidate)
        if not inventory['flags'] or candidate['tier'] != 'astra':
            return inventory
        source = next(image for image in self.bundles[candidate['identity']]['images']
                      if image['label'] == 'Original complete page')
        guard = SourceCompleteness(self.client, self.root / 'inventory-adjudication',
                                   mode='inventory-disagreement')
        try:
            # Only fallible ownership descriptions may differ from the saved
            # bundle. The independent inventory must receive none of them.
            live = self.bundles[candidate['identity']]
            canonical = {key: value for key, value in live.items() if key != '_ownership_hypotheses'}
            saved = json.loads(Path(candidate['bundle']).read_text())
            if canonical != saved:
                raise ValueError('Live candidate bundle differs from saved bundle')
            resolution = guard.check(Path(source['path']), saved, candidate)
            if resolution['route'] == 'keep':
                validate_acceptance(Path(source['path']), candidate, resolution,
                                    partial(validate_proof, expected_mode='inventory-disagreement'))
        except RunBlocked:
            raise
        except (ValueError, KeyError, TypeError, OSError) as error:
            raise RunBlocked('Invalid inventory adjudication proof: ' + str(error)) from None
        # Resolve only this alarm. The controller still requires ordinary final
        # H after split/native/crop/ownership checks; its normal proof is separate.
        return {'flags': [] if resolution['route'] == 'keep' else inventory['flags'],
                'checks': [*inventory['checks'], {
                    'scope': 'final-tier independent source inventory adjudication',
                    'original_flags': list(inventory['flags']), 'resolution': resolution}]}

    def judge(self, page, candidate):
        self._candidate_coverage_risk(candidate)
        risky = self._risk_orders(candidate)
        # This legacy layout guard cannot accept; defer paid source auditing
        # until a detector tier can actually reach quality confirmation.
        verdict = None
        if not risky or candidate['tier'] == 'sol-low':
            verdict = super().judge(page, candidate)
            risky |= self._risk_orders(candidate) | set(verdict.get('crossing_art', {}).get('targets', []))
            if not risky and verdict['route'] == 'keep' and candidate['panels']['classification'] == 'panels':
                self._source_ownership_screen(candidate)
                risky = self._risk_orders(candidate)
            self._record_source_risk(candidate, verdict)
            if not risky or verdict['route'] != 'keep':
                return verdict
        gate = self._ensure_evidence(candidate)
        if gate['route'] != 'keep':
            verdict = {'route': 'escalate', 'source_evidence_gate': gate,
                       'semantic_flags': [], 'global_crop_flags': [], 'target_flags': []}
            self.judgments[candidate['identity']] = self._record_source_risk(candidate, verdict)
            return verdict
        if verdict is None:
            verdict = super().judge(page, candidate)
        self._record_source_risk(candidate, verdict)
        verdict['source_evidence_gate'] = gate
        verdict['ownership_confirmation_required'] = True
        verdict['ownership_required_targets'] = sorted(risky | set(verdict.get('target_flags', [])))
        # Native keep must never bypass the rich global and marked target checks.
        verdict['route'] = 'escalate'
        self.judgments[candidate['identity']] = verdict
        return verdict

    def _adjudicate_clipping(self, candidate, bundle, prompt, entry, *, target=None):
        answer = entry['verdict']
        if (candidate.get('tier') not in ('sol-high', 'astra')
                or answer.get('route') != 'escalate' or answer.get('decision') != 'escalate'
                or answer.get('scene_inventory') != 'pass' or answer.get('reading_order') != 'pass'
                or answer.get('crop_coverage') != 'fail'
                or not isinstance(answer.get('issues'), list) or not answer['issues']):
            return entry
        known = {panel['order'] for panel in candidate['panels']['panels']}
        targets = set()
        for issue in answer['issues']:
            if (not isinstance(issue, dict) or issue.get('kind') not in ('clipped_art', 'clipped_text')
                    or not isinstance(issue.get('panels'), list) or not issue['panels']
                    or any(type(order) is not int or order not in known for order in issue['panels'])
                    or not isinstance(issue.get('evidence'), str) or not issue['evidence'].strip()):
                return entry
            targets.update(issue['panels'])
        if target is not None and targets != {target}:
            return entry
        details = entry.get('source_details', [])
        if target is None:
            # A target pass cannot clear a global failure. Keep the complete
            # candidate and append source-only context for its flagged targets.
            details = []
            for order in sorted(targets):
                local = with_source_detail(bundle, order,
                    Path(candidate['bundle']).parent / 'ownership-source-detail', mark_boundary=True)
                details.extend(local['images'][2:])
            bundle = {**bundle, 'images': [*bundle['images'], *details]}
        stronger, request = self.verification(bundle, prompt + AUTHORED_BOUNDARY_CLARIFICATION,
                                              'high', model='gpt-6-astra')
        # Each item retains its initial result and exposes only this scope's
        # stronger result to the existing quality and repair-feedback paths.
        return {**entry, 'original_verdict': answer, 'original_request': entry['request'],
                'original_model': entry['model'], 'model': 'gpt-6-astra',
                'verdict': stronger, 'request': request,
                'adjudication': {'scope': entry['scope'], 'target': target,
                                 'model': 'gpt-6-astra', 'effort': 'high', 'source_details': details}}

    def verify(self, page, candidate):
        self._candidate_coverage_risk(candidate)
        risky = self._risk_orders(candidate)
        previous_confirmation = None
        if not risky:
            previous_confirmation = super().verify(page, candidate)
            if (previous_confirmation.get('route') != 'keep'
                    or candidate['panels']['classification'] != 'panels'):
                return previous_confirmation
            self._source_ownership_screen(candidate)
            self._record_source_risk(candidate, self.judgments[candidate['identity']])
            risky = self._risk_orders(candidate)
            if not risky:
                return previous_confirmation
        verdict = self.judgments[candidate['identity']]
        if previous_confirmation is None and (verdict.get('overlap_pairs') or verdict.get('split_flags') or verdict.get('inventory_flags')):
            previous_confirmation = super().verify(page, candidate)
            if previous_confirmation.get('route') != 'keep':
                return previous_confirmation
            # A base verifier's permitted clearance resolves only its own guard.
            # It never substitutes for source ownership or required crop checks.
        gate = self._ensure_evidence(candidate)
        if gate['route'] != 'keep':
            return {'route': 'escalate', 'source_evidence_gate': gate, 'evidence': [],
                    'reason': 'Source ownership is unresolved; crop passes cannot clear it'}
        bundle = self.bundles[candidate['identity']]
        checks = []
        evidence = copy.deepcopy(previous_confirmation.get('evidence', [])) if previous_confirmation else []
        crossing_targets = set(verdict.get('crossing_art', {}).get('targets', []))
        global_model = 'gpt-6-astra' if candidate['tier'] == 'astra' and crossing_targets else 'gpt-6-sol'
        prompt = (HERE / 'judge-prompt-v2.txt').read_text()
        if global_model == 'gpt-6-astra':
            prompt += AUTHORED_BOUNDARY_CLARIFICATION
        answer, request = self.verification(bundle, prompt, 'high', model=global_model)
        item = {'scope': 'complete candidate with source ownership', 'verdict': answer,
                'request': request, 'model': global_model, 'effort': 'high'}
        if global_model == 'gpt-6-sol':
            item = self._adjudicate_clipping(candidate, bundle, prompt, item)
        checks.append(item['verdict']['route'] == 'keep')
        evidence.append(item)
        if candidate['tier'] != 'astra' and not checks[-1]:
            return {'route': 'escalate', 'evidence': evidence, 'source_evidence_gate': gate,
                    'reason': 'Global ownership confirmation failed; require stronger detection'}
        targets = risky | set(verdict.get('target_flags', [])) | crossing_targets
        for target in sorted(targets):
            local = with_source_detail(bundle, target, Path(candidate['bundle']).parent / 'ownership-source-detail',
                                       mark_boundary=True)
            prompt = (HERE / 'judge-target-detail-prompt-v2.txt').read_text()
            model = 'gpt-6-astra' if target in crossing_targets else 'gpt-6-sol'
            if model == 'gpt-6-astra':
                prompt += AUTHORED_BOUNDARY_CLARIFICATION
            answer, request = self.verification(local, prompt, 'high', model=model)
            item = {'scope': 'target with source ownership and exact crop boundary', 'panel': target,
                    'verdict': answer, 'request': request, 'source_details': local['images'][2:],
                    'model': model, 'effort': 'high', 'crossing_art_risk': target in crossing_targets}
            # A directly selected Astra verdict is already the strongest check.
            # Do not clear its rejection with another same-strength adjudication.
            if model == 'gpt-6-sol':
                item = self._adjudicate_clipping(candidate, local, prompt, item, target=target)
            checks.append(item['verdict']['route'] == 'keep')
            evidence.append(item)
            if candidate['tier'] != 'astra' and not checks[-1]:
                return {'route': 'escalate', 'evidence': evidence, 'source_evidence_gate': gate,
                        'reason': 'Marked target failed; require stronger detection'}
        return {'route': 'keep' if checks and all(checks) else 'escalate',
                'evidence': evidence, 'source_evidence_gate': gate}
