import copy
import base64
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image
from inventory_guard import merged_groups, represented_orders, context_request_body


def panel(n, box):
    return {'order': n, 'box': box}


def layout(*boxes):
    return {'classification': 'panels', 'panels': [panel(n, box) for n, box in enumerate(boxes, 1)]}


class InventoryGuardTests(unittest.TestCase):
    def test_surviving_inset_uses_best_iou_instead_of_enclosing_background(self):
        previous = layout([0,0,400,400], [500,0,1000,500], [500,500,1000,1000])
        current = layout([0,0,400,400], [0,0,1000,1000])
        groups = merged_groups(previous, current)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['current_order'], 2)
        self.assertEqual([p['order'] for p in groups[0]['previous_panels']], [2,3])

    def test_touching_or_partially_intersecting_views_do_not_imply_merge(self):
        previous = layout([0,0,400,400], [500,0,1000,500], [500,500,1000,1000])
        current = layout([0,0,400,400], [500,200,1000,800])
        self.assertEqual(merged_groups(previous,current), [])
        self.assertEqual(merged_groups(previous,previous), [])

    def test_context_is_detector_independent_and_preserves_complete_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.jpg';Image.new('RGB',(100,100)).save(source)
            body=context_request_body(source,source)
            content=body['input'][0]['content']
            self.assertEqual(len([c for c in content if c['type']=='input_image']),2)
            self.assertNotIn('earlier_regions',content[0]['text'])
            self.assertNotIn('all_current_regions',content[0]['text'])

    def test_existing_insets_count_but_incidental_fragments_do_not(self):
        group={'current_order':3,'previous_panels':[panel(4,[500,0,1000,500]),panel(5,[500,500,1000,1000])]}
        current=layout([400,0,700,500],[100,500,510,1000],[500,0,1000,1000])
        self.assertEqual(represented_orders(group,current),[1,3])


class InventoryRoutingTests(unittest.TestCase):
    def test_earliest_inventory_survives_an_intermediate_merge(self):
        from auto_convert import Converter
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.jpg';Image.new('RGB',(100,100)).save(source)
            client=Mock();client.request.return_value=({'output':[{'content':[{'type':'output_text','text':json.dumps(
                {'classification':'distinct','views':['portrait','flashback'],'evidence':'Two separate camera views.'})}]}]}, {})
            converter=Converter(client,root)
            many=layout([0,0,500,1000],[500,0,1000,500],[500,500,1000,1000])
            few=layout([0,0,500,1000],[500,0,1000,1000])
            candidate={'identity':'final','source_sha256':'same-source','tier':'astra','panels':few,'bundle':str(root/'bundle.json')}
            converter.bundles['final']={**few,'images':[{'path':str(source)}]}
            converter.history['same-source']=[{'identity':'first','tier':'sol-low','panels':many},
                {'identity':'middle','tier':'sol-high','panels':few},candidate]
            result=converter.check_inventory(candidate)
            self.assertEqual(result['flags'],[2])
            self.assertEqual(result['checks'][0]['previous_tier'],'sol-low')
            self.assertEqual(client.request.call_count,2)

    def test_equal_inventory_uses_latest_geometry_reference(self):
        from auto_convert import Converter
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.jpg';Image.new('RGB',(100,100)).save(source)
            client=Mock();client.request.return_value=({'output':[{'content':[{'type':'output_text','text':json.dumps(
                {'classification':'continuous','views':['One room view.'],'evidence':'Continuous perspective.'})}]}]}, {})
            converter=Converter(client,root)
            early=layout([0,0,500,1000],[500,0,1000,500],[500,500,1000,1000])
            later=layout([0,0,500,1000],[501,0,1000,500],[501,500,1000,1000])
            few=layout([0,0,500,1000],[500,0,1000,1000])
            candidate={'identity':'final','source_sha256':'source','tier':'astra','panels':few,'bundle':str(root/'bundle.json')}
            converter.bundles['final']={**few,'images':[{'path':str(source)}]}
            converter.history['source']=[{'identity':'first','tier':'sol-low','panels':early},
                {'identity':'middle','tier':'sol-high','panels':later},candidate]
            result=converter.check_inventory(candidate)
            self.assertEqual(result['flags'],[]);self.assertEqual(len(result['checks']),1)
            self.assertEqual(result['checks'][0]['previous_tier'],'sol-high')
            self.assertEqual(client.request.call_count,1)

    def test_uncertain_inventory_cannot_be_cleared_by_other_quality_verifiers(self):
        from auto_convert import Converter
        with tempfile.TemporaryDirectory() as tmp:
            converter=Converter(None,Path(tmp))
            converter.bundles['candidate']=layout([0,0,1000,1000])
            candidate={'identity':'candidate','tier':'sol-high'}
            with patch.object(converter,'check_inventory',return_value={'flags':[1],'checks':[]}),patch.object(converter,'check_splits') as splits:
                self.assertEqual(converter.judge(None,candidate)['route'],'escalate');splits.assert_not_called()
            with patch.object(converter,'verification') as verifier:
                self.assertEqual(converter.verify(None,candidate)['route'],'escalate');verifier.assert_not_called()

    def test_whole_page_replacement_does_not_hide_count_loss(self):
        previous=layout([0,0,500,1000],[500,0,1000,1000])
        current={'classification':'whole_page','panels':[]}
        self.assertEqual(len(merged_groups(previous,current)),1)

class InventoryAdjudicationTests(unittest.TestCase):
    """Actual controller/Client/proof paths; only provider answers are synthetic."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, name, *, failure=None, global_failure=False):
        from types import SimpleNamespace
        from auto_convert import Client
        from gemini_budget import Budget
        from marked_native import MarkedNativeConverter
        root = self.root / name; root.mkdir()
        source = root / 'source.jpg'; Image.new('RGB', (100, 100), 'white').save(source)
        budget = self.enterContext(Budget(root / 'ledger.jsonl', cap=20_000_000))
        client = Client('offline-test-key', budget, root / 'calls')
        converter = MarkedNativeConverter(client, root)
        proposal = {'classification': 'panels', 'orientation': 'upright', 'reading_direction': 'ltr',
                    'panels': [{'order': 1, 'box': [0, 0, 400, 1000], 'description': 'First source view'},
                               {'order': 2, 'box': [600, 0, 1000, 1000], 'description': 'Second source view'}]}
        candidate = converter.refine(source, {'tier': 'astra', 'panels': proposal})
        inventory = {'page_kind': 'narrative', 'rationale': 'Two synthetic test views.', 'views': [
            {'id': 'a', 'visual_cue': 'Upper view', 'locator_y': 200, 'locator_x': 500, 'uncertain': False},
            {'id': 'b', 'visual_cue': 'Lower view', 'locator_y': 800, 'locator_x': 500, 'uncertain': False}]}
        mapping = {'disposition': 'complete', 'inventory_issues': [], 'reason': 'Each view has one step.',
                   'mappings': [{'source_id': 'a', 'proposed_order': 1, 'reason': 'Upper view.'},
                                {'source_id': 'b', 'proposed_order': 2, 'reason': 'Lower view.'}]}
        if failure == 'source_uncertain': inventory['views'][0]['uncertain'] = True
        elif failure == 'missing':
            mapping['disposition'] = 'missing'; mapping['mappings'][1]['proposed_order'] = None
        elif failure == 'duplicate': mapping['mappings'][1]['proposed_order'] = 1
        elif failure == 'mapping_uncertain': mapping['disposition'] = 'uncertain'
        elif failure == 'inventory_issue': mapping['inventory_issues'] = ['An unresolved source view.']
        elif failure == 'invalid': mapping['mappings'][1]['proposed_order'] = 99
        calls = []
        def http(endpoint, body):
            if endpoint == 'responses/input_tokens': return {'input_tokens': 1}
            calls.append((endpoint, copy.deepcopy(body)))
            usage = {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2}
            if endpoint == 'decisions':
                return {'model': body['model'], 'usage': {'input_tokens': 1, 'output_tokens': 0, 'total_tokens': 1}, 'answers': [
                    {'type': 'predicate', 'name': question['name'],
                     'probability': .9 if global_failure and question['name'] == 'art_clipping'
                                    and len(body['questions']) > 2 else 0.0}
                    for question in body['questions']]}
            schema = body['text']['format']['name']
            if schema == 'source_view_inventory_v1': value = inventory
            elif schema == 'source_view_coverage_v1': value = mapping
            elif schema == 'panel_quality_verdict':
                value = {'decision': 'escalate', 'scene_inventory': 'pass', 'reading_order': 'pass',
                         'crop_coverage': 'fail', 'issues': [
                             {'kind': 'clipped_art', 'panels': [1], 'evidence': 'Synthetic crop defect.'}]}
            else: raise AssertionError('Unexpected provider request: ' + schema)
            return {'status': 'completed', 'model': body['model'], 'usage': usage,
                    'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(value)}]}]}
        self.enterContext(patch.object(client, 'http', side_effect=http))
        return SimpleNamespace(root=root, source=source, client=client, converter=converter,
                               candidate=candidate, inventory=inventory, mapping=mapping, calls=calls)

    @staticmethod
    def legacy_warning():
        return {'flags': [2], 'checks': [{'legacy_evidence': 'Unresolved earlier inventory warning.'}]}

    def test_final_inventory_adjudication_resumes_all_checks_and_keeps_normal_final_h(self):
        from auto_convert import Converter, final_acceptance
        from automatic_escalation import run_page
        from source_completeness import SourceCompleteness, inventory_body, mapping_body, validate_proof
        fixture = self.fixture('pass'); converter = fixture.converter
        normal = SourceCompleteness(fixture.client, fixture.root / 'completeness')
        final = Mock(side_effect=lambda page, candidate: final_acceptance(page, candidate, converter, normal))
        legacy = self.legacy_warning(); unchanged = copy.deepcopy(fixture.candidate)
        with patch.object(Converter, 'check_inventory', return_value=legacy), \
                patch.object(converter, 'check_splits', wraps=converter.check_splits) as splits, \
                patch.object(converter, 'check_crossing_art', wraps=converter.check_crossing_art) as crossing:
            result = run_page(fixture.source, lambda *_: fixture.candidate, lambda _p, value: value,
                              converter.judge, converter.verify, tiers=('astra',), final_accept=final)
        self.assertEqual(result['status'], 'accepted')
        splits.assert_called_once(); crossing.assert_called_once(); final.assert_called_once()
        self.assertEqual(fixture.candidate, unchanged)
        self.assertEqual(legacy, self.legacy_warning())
        judge = result['attempts'][0]['judge']
        self.assertEqual(set(judge['target_probabilities']), {1, 2})
        self.assertIn('global_probabilities', judge)
        self.assertEqual(judge['inventory_checks'][0], legacy['checks'][0])
        resolution = judge['inventory_checks'][-1]
        self.assertEqual(resolution['original_flags'], [2])
        strong_proof = resolution['resolution']['proof']
        final_proof = result['attempts'][0]['completeness']['proof']
        self.assertEqual(json.loads(Path(strong_proof['path']).read_text())['mode'], 'inventory-disagreement')
        self.assertEqual(json.loads(Path(final_proof['path']).read_text())['mode'], 'normal')
        self.assertNotEqual(strong_proof, final_proof)
        bundle = converter.bundles[fixture.candidate['identity']]
        source_calls = [body for endpoint, body in fixture.calls if endpoint == 'responses'
                        and body['text']['format']['name'] == 'source_view_inventory_v1']
        mapping_calls = [body for endpoint, body in fixture.calls if endpoint == 'responses'
                         and body['text']['format']['name'] == 'source_view_coverage_v1']
        self.assertEqual(source_calls, [inventory_body(bundle, 'astra'), inventory_body(bundle)])
        self.assertEqual(mapping_calls, [mapping_body(bundle, fixture.inventory, strong=True),
                                        mapping_body(bundle, fixture.inventory)])
        altered = copy.deepcopy(bundle)
        altered['panels'] = [{'order': 999, 'box': [1, 2, 3, 4], 'description': 'DO NOT SEND'}]
        altered['_ownership_hypotheses'] = 'DO NOT SEND'
        self.assertEqual(inventory_body(altered, 'astra'), source_calls[0])
        with patch.object(fixture.client, 'http', side_effect=AssertionError('No replay HTTP')):
            self.assertEqual(validate_proof(fixture.source, fixture.candidate, strong_proof,
                            expected_mode='inventory-disagreement'), resolution['resolution'])
            with self.assertRaisesRegex(ValueError, 'mode differs'):
                validate_proof(fixture.source, fixture.candidate, strong_proof)
            self.assertEqual(final_acceptance(fixture.source, fixture.candidate, converter, normal),
                             result['attempts'][0]['completeness'])
            changed = copy.deepcopy(fixture.candidate); changed['panels']['panels'][0]['box'][0] += 1
            with self.assertRaisesRegex(ValueError, 'geometry differs'):
                validate_proof(fixture.source, changed, strong_proof, expected_mode='inventory-disagreement')

    def test_strong_uncertainty_missing_nonbijection_and_invalid_answers_cannot_clear_warning(self):
        from auto_convert import Converter
        from automatic_escalation import RunBlocked
        for failure in ('source_uncertain', 'missing', 'duplicate', 'mapping_uncertain', 'inventory_issue', 'invalid'):
            with self.subTest(failure=failure):
                fixture = self.fixture(failure, failure=failure); converter = fixture.converter
                with patch.object(Converter, 'check_inventory', return_value=self.legacy_warning()), \
                        patch.object(converter, 'check_splits') as splits:
                    # V53: a nonexistent mapped order is a rejected answer, never a run halt.
                    if True:
                        result = converter.judge(fixture.source, fixture.candidate)
                        self.assertEqual(result['route'], 'escalate')
                        self.assertEqual(result['inventory_flags'], [2])
                        self.assertEqual(result['inventory_checks'][-1]['resolution']['route'], 'escalate')
                        self.assertEqual(converter.verify(fixture.source, fixture.candidate)['route'], 'escalate')
                    splits.assert_not_called()
                self.assertEqual(len(fixture.calls), 2)

    def test_unflagged_and_earlier_tiers_retain_inventory_result_without_adjudication(self):
        from auto_convert import Converter
        fixture = self.fixture('ineligible')
        for tier, flags in (('sol-low', [2]), ('sol-high', [2]), ('astra', [])):
            fixture.candidate['tier'] = tier
            expected = {'flags': flags, 'checks': []}
            with patch.object(Converter, 'check_inventory', return_value=expected):
                self.assertIs(fixture.converter.check_inventory(fixture.candidate), expected)
        self.assertEqual(fixture.calls, [])

    def test_resolved_inventory_cannot_clear_independent_split_or_crop_failure(self):
        from auto_convert import Converter
        from automatic_escalation import run_page
        for failure in ('split', 'crop'):
            with self.subTest(failure=failure):
                fixture = self.fixture(failure, global_failure=failure == 'crop'); converter = fixture.converter
                final = Mock(side_effect=AssertionError('Independent failed quality must precede final H'))
                split_result = {'flags': [[1, 2]] if failure == 'split' else [], 'checks': []}
                with patch.object(Converter, 'check_inventory', return_value=self.legacy_warning()), \
                        patch.object(converter, 'check_splits', return_value=split_result):
                    result = run_page(fixture.source, lambda *_: fixture.candidate, lambda _p, value: value,
                                      converter.judge, converter.verify, tiers=('astra',), final_accept=final)
                self.assertEqual(result['status'], 'whole_page_fallback')
                final.assert_not_called()
                attempt = result['attempts'][0]
                self.assertEqual(attempt['judge']['inventory_checks'][-1]['resolution']['route'], 'keep')
                self.assertEqual(attempt['verifier']['route'], 'escalate')


class WholePageMappingTests(unittest.TestCase):
    """A real sentinel order is valid evidence, not proof of classification."""
    def evaluate(self, *, strong_kind='whole_page', count=1, order=1, strong_order=None):
        from source_completeness import _evaluate
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source.jpg'
            Image.new('RGB', (80, 100)).save(source)
            bundle = {'classification': 'whole_page', 'reading_direction': 'ltr',
                      'panels': [{'order': 1, 'box': [0, 0, 1000, 1000]}],
                      'images': [{'label': 'Original complete page', 'path': str(source),
                                  'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}]}
            calls = []
            def call(body):
                schema = body['text']['format']['name']; model = body['model']
                calls.append((schema, model))
                if schema == 'source_view_inventory_v1':
                    kind = strong_kind if model == 'gpt-6-astra' else 'narrative'
                    value = {'page_kind': kind, 'rationale': 'Independent source finding.',
                             'views': [] if kind == 'whole_page' else [
                                 {'id': f'v{i}', 'visual_cue': f'Source view {i}',
                                  'locator_y': 300 + i * 100, 'locator_x': 500,
                                  'uncertain': kind == 'uncertain'} for i in range(count)]}
                else:
                    text = body['input'][0]['content'][2]['text']
                    inventory = json.loads(text.split('\n', 1)[1])
                    value = {'disposition': 'complete', 'reason': 'Mapped source views.',
                             'inventory_issues': [], 'mappings': [
                                 {'source_id': v['id'],
                                  'proposed_order': strong_order if model == 'gpt-6-astra' and strong_order is not None else order,
                                  'reason': 'Proposed whole-page step.'} for v in inventory['views']]}
                return {'status': 'completed', 'model': model, 'output': [
                    {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(value)}]}]}
            return _evaluate(bundle, call), calls

    def test_narrative_mapping_to_whole_page_requires_source_audit(self):
        result, calls = self.evaluate()
        self.assertEqual(result['route'], 'keep')
        self.assertEqual(result['inventory_stages'], ['low', 'astra'])
        self.assertEqual(calls, [('source_view_inventory_v1', 'gpt-6-sol'),
                                 ('source_view_coverage_v1', 'gpt-6-sol'),
                                 ('source_view_inventory_v1', 'gpt-6-astra'),
                                 ('source_view_coverage_v1', 'gpt-6-sol')])

    def test_persistent_narrative_and_many_to_one_never_certify_whole_page(self):
        for count in (1, 2):
            with self.subTest(count=count):
                result, calls = self.evaluate(strong_kind='narrative', count=count)
                self.assertEqual(result['route'], 'escalate')
                self.assertIn('source_candidate_classification', result['unresolved'])
                self.assertIn(('source_view_coverage_v1', 'gpt-6-astra'), calls)
                if count == 2: self.assertIn('duplicate_proposed_order', result['unresolved'])

    def test_source_uncertainty_still_blocks_whole_page(self):
        result, _ = self.evaluate(strong_kind='uncertain')
        self.assertEqual(result['route'], 'escalate')
        self.assertIn('astra_source_uncertainty', result['unresolved'])

    def test_nonexistent_order_from_both_models_rejects_without_halting(self):
        # A model answer naming a nonexistent order is a rejected mapping, never a run failure.
        result, calls = self.evaluate(order=2)
        self.assertEqual(result['route'], 'escalate')
        self.assertEqual(result['unresolved'], ['invalid_model_mapping'])
        self.assertIn('Unknown proposed order', result['reason'])
        self.assertEqual(calls[-1], ('source_view_coverage_v1', 'gpt-6-astra'))

    def test_invalid_cheap_mapping_gets_one_strong_mapping_and_can_certify(self):
        result, calls = self.evaluate(order=2, strong_order=1)
        self.assertEqual(result['route'], 'keep')
        self.assertEqual(calls, [('source_view_inventory_v1', 'gpt-6-sol'),
                                 ('source_view_coverage_v1', 'gpt-6-sol'),
                                 ('source_view_coverage_v1', 'gpt-6-astra'),
                                 ('source_view_inventory_v1', 'gpt-6-astra'),
                                 ('source_view_coverage_v1', 'gpt-6-sol')])


class SharedContentInventoryPromptTests(unittest.TestCase):
    def test_both_inventory_prompts_exclude_unowned_shared_content(self):
        from source_completeness import SOURCE_PROMPT, AUDIT_PROMPT
        for prompt in (SOURCE_PROMPT, AUDIT_PROMPT):
            text = prompt.read_text()
            self.assertIn('belongs to no single view is not itself a view', text)
            self.assertIn('facing page of a spread', text)
            self.assertIn('never excuses a distinct view', text)


class CompositeRulePromptTests(unittest.TestCase):
    def test_inventory_mapping_and_ownership_share_one_composite_rule(self):
        from source_completeness import SOURCE_PROMPT, MAPPING_PROMPT, AUDIT_PROMPT
        from scene_evidence import PROMPT
        for prompt in (SOURCE_PROMPT, MAPPING_PROMPT, PROMPT):
            text = ' '.join(prompt.read_text().split())
            self.assertIn("composited inside one framed panel's artwork", text)
            self.assertIn('A distinct inset with its own frame or border remains a separate view', text)
        self.assertNotIn('borderless montage views', SOURCE_PROMPT.read_text())
        self.assertIn('composited portraits', AUDIT_PROMPT.read_text())


class DetectorCompositeRuleTests(unittest.TestCase):
    def test_detectors_keep_composites_with_their_framed_panel(self):
        import auto_convert
        source = Path(auto_convert.__file__).read_text()
        self.assertIn("'prompt-v10.txt'", source); self.assertIn("'prompt-v11-direction.txt'", source)
        self.assertNotIn("'prompt-v6.txt'", source); self.assertNotIn("'prompt-v8.txt'", source)
        for name in ('prompt-v10.txt', 'prompt-v11-direction.txt'):
            text = ' '.join((Path(auto_convert.__file__).parent / name).read_text().split())
            self.assertIn("composited inside one framed panel's artwork", text)
            self.assertIn('A distinct inset with its own frame or border remains a separate panel', text)


class ReadingRegionRuleTests(unittest.TestCase):
    """V58: every prompt that judges what counts as a view shares one reading-region definition."""
    def test_all_view_judging_prompts_share_reading_region_rule(self):
        import auto_convert, split_check, continuity_verifier, inventory_guard, narrative_context, scene_evidence, source_completeness
        here = Path(auto_convert.__file__).parent
        rule = 'A view is an independently presented composition'
        for name in ('prompt-v10.txt', 'prompt-v11-direction.txt', 'continuity-prompt-v4.txt', 'continuity-verifier-prompt-v2.txt',
                     'inventory-context-prompt-v2.txt', 'narrative-context-prompt-v3.txt', 'judge-target-prompt-v5.txt'):
            self.assertIn(rule, ' '.join((here / name).read_text().split()), name)
        self.assertIn(rule, split_check.QUESTION['instructions'])
        self.assertIn(rule, ' '.join(scene_evidence.PROMPT.read_text().split()))
        self.assertIn(rule, ' '.join(source_completeness.SOURCE_PROMPT.read_text().split()))
        for module, name in ((continuity_verifier, 'continuity-verifier-prompt-v2.txt'), (inventory_guard, 'inventory-context-prompt-v2.txt'),
                             (narrative_context, 'narrative-context-prompt-v3.txt'), (split_check, 'continuity-prompt-v4.txt')):
            self.assertIn(name, Path(module.__file__).read_text())
        for stale in ('prompt-v8.txt', 'judge-target-prompt-v4.txt', 'scene-evidence-prompt-v3.txt'):
            self.assertNotIn("'" + stale + "'", Path(auto_convert.__file__).read_text())


class SourceDetailInventoryTests(unittest.TestCase):
    """Real Client and completeness proof routing with synthetic provider answers."""
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')))

    def fixture(self,name,*,mode='normal',failure=None,trigger=True):
        from types import SimpleNamespace
        from auto_convert import Client
        from gemini_budget import Budget
        from source_completeness import SourceCompleteness
        root=self.root/name;root.mkdir();source=root/'source.jpg'
        image=Image.new('RGB',(63,47));image.putdata([(x*4,y*5,(x+y)*2) for y in range(47) for x in range(63)])
        image.save(source,quality=95)
        sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        geometry={'classification':'panels','reading_direction':'ltr',
                  'panels':[panel(1,[0,0,400,1000]),panel(2,[600,0,1000,1000])]}
        images=[{'label':'Original complete page','path':str(source),'sha256':sha(source)}]
        for order,bounds in [(1,(0,0,63,19)),(2,(0,28,63,47))]:
            path=root/f'crop-{order}.png'
            with Image.open(source) as original:original.crop(bounds).save(path)
            images.append({'label':f'Candidate crop {order} in reading order','path':str(path),'sha256':sha(path)})
        bundle={**copy.deepcopy(geometry),'images':images};bundle_path=root/'bundle.json'
        bundle_path.write_text(json.dumps(bundle))
        candidate={'identity':hashlib.sha256((sha(source)+json.dumps(geometry,sort_keys=True)).encode()).hexdigest(),
                   'source_sha256':sha(source),'panels':copy.deepcopy(geometry),'bundle':str(bundle_path),'tier':'astra'}
        inventory={'page_kind':'narrative','rationale':'Synthetic source compositions.', 'views':[
            {'id':'a','visual_cue':'Upper source view','locator_y':200,'locator_x':500,'uncertain':False},
            {'id':'b','visual_cue':'Lower source view','locator_y':800,'locator_x':500,'uncertain':False}]}
        mapping={'disposition':'complete','inventory_issues':[],'reason':'Each source view has one step.',
            'mappings':[{'source_id':'a','proposed_order':1,'reason':'Upper source view.'},
                        {'source_id':'b','proposed_order':2,'reason':'Lower source view.'}]}
        budget=self.enterContext(Budget(root/'ledger',cap=20000000))
        client=Client('synthetic-not-credential',budget,root/'calls');calls=[];mapping_calls=0
        def http(endpoint,body):
            nonlocal mapping_calls
            if endpoint=='responses/input_tokens':return {'input_tokens':10}
            self.assertEqual(endpoint,'responses');calls.append(copy.deepcopy(body))
            name=body['text']['format']['name']
            if name=='source_view_inventory_v1':
                value=copy.deepcopy(inventory)
                detail=sum(p['type']=='input_image' for p in body['input'][0]['content'])==5
                if trigger and body['model']=='gpt-6-astra' and not detail:value['views'][0]['uncertain']=True
                if detail and failure=='uncertain':value['views'][0]['uncertain']=True
                if detail and failure=='page_uncertain':value['page_kind']='uncertain'
                if detail and failure=='malformed':value.pop('rationale')
            elif name=='source_view_coverage_v1':
                mapping_calls+=1;value=copy.deepcopy(mapping)
                if trigger and mode=='normal' and mapping_calls==1:value['inventory_issues']=['Unresolved source identity.']
                elif failure=='missing':value['disposition']='missing';value['mappings'][1]['proposed_order']=None
                elif failure=='duplicate':value['mappings'][1]['proposed_order']=1
                elif failure=='invalid':value['mappings'][1]['proposed_order']=99
            else:raise AssertionError('Unexpected request schema')
            return {'status':'completed','model':body['model'],
                'usage':{'input_tokens':10,'output_tokens':30,'total_tokens':40},
                'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(value)}]}]}
        self.enterContext(patch.object(client,'http',side_effect=http))
        return SimpleNamespace(root=root,source=source,bundle=bundle,candidate=candidate,client=client,budget=budget,
            inventory=inventory,mapping=mapping,calls=calls,guard=SourceCompleteness(client,root/'proofs',mode=mode))

    def test_uncertain_astra_inventory_gets_one_source_only_detail_audit_and_bound_proof(self):
        import source_completeness as completeness
        f=self.fixture('normal');unchanged=copy.deepcopy(f.candidate)
        result=f.guard.check(f.source,f.bundle,f.candidate)
        self.assertEqual(result['route'],'keep')
        self.assertEqual(result['inventory_stages'],['low','astra','astra-detail'])
        self.assertTrue(result['retained_uncertainty']);self.assertTrue(result['source_detail_audit']['resolved'])
        uncertain=copy.deepcopy(f.inventory);uncertain['views'][0]['uncertain']=True
        self.assertEqual(result['source_detail_audit']['original_inventory_sha256'],completeness._json_hash(uncertain))
        self.assertEqual(f.candidate,unchanged);self.assertEqual(len(f.calls),5)
        detail=f.calls[3];images=[p for p in detail['input'][0]['content'] if p['type']=='input_image']
        self.assertEqual(len(images),5)
        self.assertEqual(base64.b64decode(images[0]['image_url'].split(',',1)[1]),f.source.read_bytes())
        with Image.open(f.source) as source:
            source=source.convert('RGB');bounds=[(0,0,38,29),(25,0,63,29),(0,18,38,47),(25,18,63,47)]
            for part,box in zip(images[1:],bounds):
                with Image.open(io.BytesIO(base64.b64decode(part['image_url'].split(',',1)[1]))) as tile:
                    self.assertEqual(tile.size,(38,29));self.assertEqual(tile.tobytes(),source.crop(box).tobytes())
        altered=copy.deepcopy(f.bundle);altered['classification']='blank';altered['panels']=[{'do_not_send':'candidate geometry'}]
        altered['_ownership_hypotheses']={'do_not_send':'prior model opinions'}
        self.assertEqual(detail,completeness.detail_inventory_body(altered))
        text=json.dumps(detail['input'][0]['content'])
        for forbidden in ('Upper source view','Lower source view','Unresolved source identity','proposed_order','locator_y'):
            self.assertNotIn(forbidden,text)
        proof=result['proof'];calls_before=len(f.calls);ledger=f.budget.path.read_bytes()
        with patch.object(f.client,'http',side_effect=AssertionError('Proof replay attempted HTTP')):
            self.assertEqual(completeness.validate_proof(f.source,f.candidate,proof),result)
            self.assertEqual(f.guard.check(f.source,f.bundle,f.candidate),result)
        self.assertEqual(len(f.calls),calls_before);self.assertEqual(f.budget.path.read_bytes(),ledger)

    def test_strong_inventory_mode_gets_detail_but_stays_separate_from_normal_proof(self):
        from source_completeness import validate_proof
        f=self.fixture('strong',mode='inventory-disagreement');result=f.guard.check(f.source,f.bundle,f.candidate)
        self.assertEqual(result['route'],'keep');self.assertEqual(len(f.calls),3)
        self.assertEqual(result['inventory_stages'],['astra','astra-detail'])
        self.assertEqual(result['mapping_stages'],['astra']);self.assertTrue(result['retained_uncertainty'])
        self.assertEqual(validate_proof(f.source,f.candidate,result['proof'],expected_mode='inventory-disagreement'),result)
        with self.assertRaisesRegex(ValueError,'mode differs'):validate_proof(f.source,f.candidate,result['proof'])

    def test_detail_uncertainty_invalidity_or_bad_mapping_cannot_accept_or_loop(self):
        from automatic_escalation import RunBlocked
        for failure in ('uncertain','page_uncertain','malformed','missing','duplicate','invalid'):
            with self.subTest(failure=failure):
                f=self.fixture(failure,mode='inventory-disagreement',failure=failure)
                if failure=='malformed':
                    with self.assertRaises(RunBlocked):f.guard.check(f.source,f.bundle,f.candidate)
                elif failure=='invalid':
                    # V53: a nonexistent mapped order rejects without halting or looping.
                    result=f.guard.check(f.source,f.bundle,f.candidate)
                    self.assertEqual(result['route'],'escalate')
                    self.assertEqual(result['unresolved'],['invalid_model_mapping'])
                else:
                    result=f.guard.check(f.source,f.bundle,f.candidate)
                    self.assertEqual(result['route'],'escalate')
                    self.assertTrue(result['retained_uncertainty'])
                detail=[body for body in f.calls if sum(p['type']=='input_image' for p in body['input'][0]['content'])==5]
                self.assertEqual(len(detail),1)
                self.assertEqual(len(f.calls),2 if failure in ('uncertain','page_uncertain','malformed') else 3)

    def test_certain_inventory_paths_keep_existing_request_bodies(self):
        from source_completeness import inventory_body,mapping_body
        for mode in ('normal','inventory-disagreement'):
            with self.subTest(mode=mode):
                f=self.fixture(mode,mode=mode,trigger=False);result=f.guard.check(f.source,f.bundle,f.candidate)
                self.assertEqual(result['route'],'keep');self.assertNotIn('source_detail_audit',result)
                self.assertEqual(f.calls,[inventory_body(f.bundle,'astra' if mode=='inventory-disagreement' else 'low'),
                    mapping_body(f.bundle,f.inventory,strong=mode=='inventory-disagreement')])

    def test_forged_detail_pixels_fail_even_with_updated_request_and_proof_hashes(self):
        from source_completeness import validate_proof
        f=self.fixture('tamper');result=f.guard.check(f.source,f.bundle,f.candidate)
        proof=json.loads(Path(result['proof']['path']).read_text());record=proof['calls'][3]
        copied=f.root/'forged-request';shutil.copytree(record['path'],copied);request_path=copied/'request.json'
        request=json.loads(request_path.read_text())
        images=[p for p in request['body_without_image_bytes']['input'][0]['content'] if p['type']=='input_image']
        images[1]['image_sha256']='0'*64;request_path.write_text(json.dumps(request))
        record['path']=str(copied);record['request_sha256']=hashlib.sha256(request_path.read_bytes()).hexdigest()
        forged=f.root/'forged-proof.json';forged.write_text(json.dumps(proof))
        receipt={'path':str(forged),'sha256':hashlib.sha256(forged.read_bytes()).hexdigest()}
        with self.assertRaisesRegex(ValueError,'Saved request body differs'):
            validate_proof(f.source,f.candidate,receipt)


class SourceRelationInventoryTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')))

    def fixture(self,name,*,relation='same_region',failure=None,pattern=None,mode='normal'):
        f=SourceDetailInventoryTests.fixture(self,name,mode=mode)
        if relation=='same_region':
            f.inventory['views'].append({'id':'c','visual_cue':'Unchanged other source view',
                'locator_y':950,'locator_x':500,'uncertain':False})
        f.inventory['rationale']='PRIVATE prior rationale; not a relation instruction.'
        original_http=f.client.http
        relation_value={'relation':relation,'anchors_resolved':True,
            'region_cues':['One source composition'] if relation=='same_region' else ['First region','Second region'],
            'evidence':'Concrete synthetic authored-boundary evidence.'}
        if failure=='uncertain':relation_value.update(relation='uncertain',anchors_resolved=False,region_cues=[])
        elif failure=='anchors':relation_value['anchors_resolved']=False
        elif failure=='cue_count':relation_value['region_cues']=[]
        elif failure=='malformed':relation_value.pop('evidence')
        def http(endpoint,body):
            if endpoint=='responses/input_tokens':return original_http(endpoint,body)
            schema=body['text']['format']['name']
            if schema=='source_view_relation_v1':
                f.calls.append(copy.deepcopy(body));value=copy.deepcopy(relation_value)
                return {'status':'completed','model':body['model'],
                    'usage':{'input_tokens':10,'output_tokens':30,'total_tokens':40},
                    'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(value)}]}]}
            raw=original_http(endpoint,body)
            if schema=='source_view_inventory_v1':
                value=copy.deepcopy(f.inventory)
                if body['model']=='gpt-6-astra':
                    selected=[0,1] if pattern is None else [0,2] if pattern=='nonadjacent' else [0,1,2]
                    for i in selected:value['views'][i]['uncertain']=True
                    if pattern=='page_uncertain':value['page_kind']='uncertain'
            else:
                content=body['input'][0]['content']
                text=next(p['text'] for p in content if p['type']=='input_text' and p['text'].startswith('Automatic source inventory:\n'))
                inventory=json.loads(text.split('\n',1)[1]);ids=[v['id'] for v in inventory['views']]
                value={'disposition':'complete','reason':'Source views checked against the complete original.',
                    'inventory_issues':['Original source ambiguity.'] if body['model']=='gpt-6-sol' else [],
                    'mappings':[{'source_id':identity,'proposed_order':(1 if i<2 else 2) if len(ids)==3 else i+1,
                                 'reason':'Source-grounded synthetic mapping.'} for i,identity in enumerate(ids)]}
                if body['model']=='gpt-6-astra':
                    if failure=='missing':value['disposition']='missing';value['mappings'][-1]['proposed_order']=None
                    elif failure=='duplicate':value['mappings'][-1]['proposed_order']=1
                    elif failure=='mapping_uncertain':value['disposition']='uncertain'
                    elif failure=='inventory_issue':value['inventory_issues']=['Another unresolved source view.']
            raw['output'][0]['content'][0]['text']=json.dumps(value);return raw
        self.enterContext(patch.object(f.client,'http',side_effect=http))
        return f

    def test_same_region_resolves_only_automatic_pair_then_requires_strong_mapping(self):
        import source_completeness as completeness
        f=self.fixture('same');candidate_before=copy.deepcopy(f.candidate)
        result=f.guard.check(f.source,f.bundle,f.candidate)
        self.assertEqual(result['route'],'keep')
        self.assertEqual(result['inventory_stages'],['low','astra','astra-detail','astra-relation'])
        self.assertEqual(result['mapping_stages'],['low','astra'])
        self.assertTrue(result['retained_uncertainty']);self.assertFalse(result['source_detail_audit']['resolved'])
        resolution=result['source_relation_audit'];self.assertTrue(resolution['resolved'])
        self.assertEqual(resolution['pair_ids'],['a','b'])
        reconstructed=resolution['reconstructed_inventory']
        self.assertEqual([v['id'] for v in reconstructed['views']],['a','c'])
        self.assertEqual(reconstructed['views'][1],f.inventory['views'][2])
        self.assertEqual(reconstructed['views'][0],{**f.inventory['views'][0],'visual_cue':'One source composition'})
        self.assertEqual(resolution['reconstructed_inventory_sha256'],completeness._json_hash(reconstructed))
        self.assertEqual(f.candidate,candidate_before)
        self.assertEqual(len(f.calls),6)
        request=f.calls[4];content=request['input'][0]['content']
        self.assertEqual(request['text']['format']['name'],'source_view_relation_v1')
        images=[p for p in content if p['type']=='input_image'];self.assertEqual(len(images),2)
        self.assertEqual(base64.b64decode(images[0]['image_url'].split(',',1)[1]),f.source.read_bytes())
        with Image.open(f.source) as original,Image.open(io.BytesIO(base64.b64decode(images[1]['image_url'].split(',',1)[1]))) as detail:
            self.assertEqual(detail.tobytes(),original.convert('RGB').crop((18,0,45,47)).tobytes())
        uncertain=copy.deepcopy(f.inventory)
        for i in (0,1):uncertain['views'][i]['uncertain']=True
        altered=copy.deepcopy(f.bundle);altered['panels']=[{'DO_NOT_SEND':'candidate geometry'}]
        uncertain['rationale']='DO_NOT_SEND prior verdict'
        for view in uncertain['views']:view['visual_cue']='DO_NOT_SEND previous cue'
        self.assertEqual(request,completeness.relation_body(altered,uncertain))
        self.assertNotIn('PRIVATE',json.dumps(content));self.assertNotIn('Candidate geometry',json.dumps(content))
        self.assertEqual(f.calls[-1],completeness.mapping_body(f.bundle,reconstructed,strong=True))
        before=f.budget.path.read_bytes()
        with patch.object(f.client,'http',side_effect=AssertionError('Replay attempted HTTP')):
            self.assertEqual(completeness.validate_proof(f.source,f.candidate,result['proof']),result)
            self.assertEqual(f.guard.check(f.source,f.bundle,f.candidate),result)
        self.assertEqual(f.budget.path.read_bytes(),before)

    def test_distinct_clears_only_pair_uncertainty_in_both_modes(self):
        for mode in ('normal','inventory-disagreement'):
            with self.subTest(mode=mode):
                f=self.fixture(mode,relation='distinct_regions',mode=mode)
                result=f.guard.check(f.source,f.bundle,f.candidate)
                self.assertEqual(result['route'],'keep')
                self.assertEqual(result['source_relation_audit']['reconstructed_inventory']['views'],f.inventory['views'])
                self.assertEqual(result['mapping_stages'][-1],'astra')
                self.assertEqual(sum(b['text']['format']['name']=='source_view_relation_v1' for b in f.calls),1)

    def test_unresolved_invalid_relation_and_failed_strong_mapping_remain_blocking(self):
        from automatic_escalation import RunBlocked
        for failure in ('uncertain','anchors','cue_count','malformed','missing','duplicate','mapping_uncertain','inventory_issue'):
            with self.subTest(failure=failure):
                f=self.fixture(failure,failure=failure)
                if failure in ('anchors','cue_count','malformed'):
                    with self.assertRaises(RunBlocked):f.guard.check(f.source,f.bundle,f.candidate)
                else:
                    result=f.guard.check(f.source,f.bundle,f.candidate)
                    self.assertEqual(result['route'],'escalate')
                    if failure=='uncertain':self.assertFalse(result['source_relation_audit']['resolved'])
                self.assertEqual(sum(b['text']['format']['name']=='source_view_relation_v1' for b in f.calls),1)
                strong_maps=[b for b in f.calls if b['text']['format']['name']=='source_view_coverage_v1' and b['model']=='gpt-6-astra']
                self.assertEqual(len(strong_maps),0 if failure in ('uncertain','anchors','cue_count','malformed') else 1)

    def test_other_uncertainty_patterns_do_not_launch_relation(self):
        for pattern in ('nonadjacent','three','page_uncertain'):
            with self.subTest(pattern=pattern):
                f=self.fixture(pattern,pattern=pattern);result=f.guard.check(f.source,f.bundle,f.candidate)
                self.assertEqual(result['route'],'escalate');self.assertNotIn('source_relation_audit',result)
                self.assertFalse(any(b['text']['format']['name']=='source_view_relation_v1' for b in f.calls))

    def test_forged_reconstructed_inventory_or_missing_relation_fails_proof_replay(self):
        from source_completeness import validate_proof
        f=self.fixture('tamper');result=f.guard.check(f.source,f.bundle,f.candidate)
        original=json.loads(Path(result['proof']['path']).read_text())
        for name in ('inventory','missing-call'):
            with self.subTest(name=name):
                proof=copy.deepcopy(original)
                if name=='inventory':proof['decision']['source_relation_audit']['reconstructed_inventory']['views'][1]['visual_cue']='Forged other view'
                else:del proof['calls'][4]
                path=f.root/f'forged-{name}.json';path.write_text(json.dumps(proof))
                receipt={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                with self.assertRaises(ValueError):validate_proof(f.source,f.candidate,receipt)


class SourceCompletenessRedetectionTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')))

    def fixture(self,name,*,failure='missing',mode='normal'):
        from marked_native import MarkedNativeConverter
        f=SourceRelationInventoryTests.fixture(self,name,failure=failure,mode=mode)
        f.rejection=f.guard.check(f.source,f.bundle,f.candidate)
        f.converter=MarkedNativeConverter(f.client,f.root)
        f.converter.bundles[f.candidate['identity']]=copy.deepcopy(f.bundle)
        f.converter.bundles[f.candidate['identity']]['_ownership_hypotheses']={'PRIVATE':'Old automatic ownership hypothesis'}
        f.converter.history[f.candidate['source_sha256']]=[f.candidate]
        f.attempt={'candidate':f.candidate,'judge':{'route':'keep'},'completeness':f.rejection}
        return f

    def detector(self,f,*,malformed=False):
        calls=[];previous=f.client.http
        def http(endpoint,body):
            if endpoint!='responses' or body['text']['format']['name']!='comic_panels':return previous(endpoint,body)
            calls.append(copy.deepcopy(body))
            value={'classification':'panels','orientation':'upright','reading_direction':'ltr','panels':[
                {'order':i+1,'description':f'New automatic source view {i+1}',
                 'bounds':{'left':0,'top':top,'right':1000,'bottom':bottom}}
                for i,(top,bottom) in enumerate(((0,250),(350,600),(700,1000)))]}
            if malformed:value['panels'][0]['bounds']['bottom']=0
            return {'status':'completed','model':body['model'],
                'usage':{'input_tokens':10,'output_tokens':30,'total_tokens':40},
                'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(value)}]}]}
        self.enterContext(patch.object(f.client,'http',side_effect=http))
        return calls

    def test_bound_missing_feedback_drives_fresh_detector_request_and_cache(self):
        from source_completeness import missing_feedback
        f=self.fixture('request');self.assertEqual(f.rejection['disposition'],'missing')
        self.assertTrue(f.rejection['retained_uncertainty'])
        findings=missing_feedback(f.source,f.candidate,f.rejection)
        self.assertFalse(any(v['uncertain'] for v in findings['source_inventory']['views']))
        self.assertEqual(findings['source_mapping']['inventory_issues'],[])
        self.assertTrue(any(m['proposed_order'] is None for m in findings['source_mapping']['mappings']))
        unchanged=copy.deepcopy(f.candidate);proof_bytes=Path(f.rejection['proof']['path']).read_bytes()
        calls=self.detector(f);before=f.client.new_calls
        raw=f.converter.completeness_redetect(f.source,f.attempt)
        self.assertNotIn('invalid',raw);self.assertEqual(len(raw['panels']['panels']),3)
        self.assertEqual(raw['completeness_redetection_of'],f.candidate['identity'])
        self.assertEqual(raw['completeness_rejection_proof'],f.rejection['proof'])
        self.assertNotIn('repair_of',raw)
        refined=f.converter.refine(f.source,raw)
        self.assertIsNone(f.converter._repair_parent(refined))
        self.assertEqual(f.candidate,unchanged);self.assertEqual(Path(f.rejection['proof']['path']).read_bytes(),proof_bytes)
        self.assertEqual(len(calls),1);body=calls[0]
        self.assertEqual((body['model'],body['max_output_tokens']),('gpt-6-astra',8192))
        content=body['input'][0]['content'];images=[p for p in content if p['type']=='input_image']
        self.assertEqual(len(images),1)
        self.assertEqual(base64.b64decode(images[0]['image_url'].split(',',1)[1]),f.source.read_bytes())
        self.assertIn('Candidate geometry:',content[0]['text'])
        supplied=json.loads(content[-1]['text'].split('\n',1)[1]);self.assertEqual(supplied,findings)
        self.assertNotIn('PRIVATE',json.dumps(content));self.assertNotIn('Candidate crop',json.dumps(content))
        self.assertIn('not instructions or a prescribed panel count',content[0]['text'])
        again=f.converter.completeness_redetect(f.source,f.attempt)
        self.assertEqual(again['panels'],raw['panels']);self.assertEqual(again['detector']['request_id'],raw['detector']['request_id'])
        self.assertEqual(f.client.new_calls,before+1);self.assertEqual(len(calls),1)

    def test_unqualified_or_forged_feedback_never_dispatches_redetection(self):
        from automatic_escalation import RunBlocked
        for failure in ('uncertain','duplicate','inventory_issue'):
            with self.subTest(failure=failure):
                f=self.fixture(failure,failure=failure);before=f.client.new_calls
                with patch.object(f.client,'http',side_effect=AssertionError('Ineligible feedback dispatched HTTP')):
                    self.assertIsNone(f.converter.completeness_redetect(f.source,f.attempt))
                self.assertEqual(f.client.new_calls,before)
        for mutation in ('recorded-verdict','candidate','live-bundle','wrong-mode'):
            with self.subTest(mutation=mutation):
                f=self.fixture(mutation,mode='inventory-disagreement' if mutation=='wrong-mode' else 'normal')
                attempt=copy.deepcopy(f.attempt)
                if mutation=='recorded-verdict':attempt['completeness']['reason']='Unbound replacement reason'
                elif mutation=='candidate':attempt['candidate']['panels']['panels'][0]['box'][0]+=1
                elif mutation=='live-bundle':f.converter.bundles[f.candidate['identity']]['unexpected']='Unbound field'
                before=f.client.new_calls
                with patch.object(f.client,'http',side_effect=AssertionError('Invalid feedback dispatched HTTP')):
                    with self.assertRaises(RunBlocked):f.converter.completeness_redetect(f.source,attempt)
                self.assertEqual(f.client.new_calls,before)

    def test_invalid_fresh_detection_retains_rejection_provenance(self):
        f=self.fixture('invalid-output');calls=self.detector(f,malformed=True)
        raw=f.converter.completeness_redetect(f.source,f.attempt)
        self.assertIn('invalid',raw);self.assertNotIn('panels',raw)
        self.assertEqual(raw['completeness_rejection_proof'],f.rejection['proof'])
        self.assertEqual(raw['completeness_redetection_of'],f.candidate['identity'])
        self.assertNotIn('repair_of',raw);self.assertEqual(len(calls),1)


if __name__=='__main__':unittest.main()
