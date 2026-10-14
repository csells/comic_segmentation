import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image
from inventory_guard import merged_groups, response_verdict, request_body


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

    def test_prompt_retains_all_current_regions_and_no_detector_descriptions(self):
        old=layout([0,0,500,500], [500,0,1000,500], [0,500,1000,1000])
        new=layout([0,0,1000,500], [0,500,1000,1000])
        group=merged_groups(old,new)[0]
        group['previous_panels'][0]['description']='DO NOT TRANSMIT DETECTOR NARRATIVE'
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.jpg';Image.new('RGB',(100,100)).save(source)
            body=request_body(source,source,group,new)
            content=body['input'][0]['content'];text=content[0]['text']
            self.assertNotIn('DO NOT TRANSMIT',text)
            geometry=json.loads(text.splitlines()[-1])
            self.assertEqual(geometry['all_current_regions'],new['panels'])
            self.assertEqual(len([c for c in content if c['type']=='input_image']),2)

    def test_malformed_or_incomplete_response_cannot_clear_risk(self):
        valid={'classification':'preserved','views':['One coherent room view.'],'evidence':'A continuous floor.'}
        def raw(value):return {'output':[{'content':[{'type':'output_text','text':json.dumps(value)}]}]}
        self.assertEqual(response_verdict(raw(valid)),valid)
        for value in [dict(valid,classification='accept'),dict(valid,views=[]),dict(valid,evidence=''),dict(valid,extra=True)]:
            with self.subTest(value=value),self.assertRaises(ValueError):response_verdict(raw(value))
        value=raw(valid);value['status']='incomplete'
        with self.assertRaises(ValueError):response_verdict(value)


class InventoryRoutingTests(unittest.TestCase):
    def test_earliest_inventory_survives_an_intermediate_merge(self):
        from auto_convert import Converter
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.jpg';Image.new('RGB',(100,100)).save(source)
            client=Mock();client.request.return_value=({'output':[{'content':[{'type':'output_text','text':json.dumps(
                {'classification':'lost','views':['portrait','flashback'],'evidence':'Two separate camera views.'})}]}]}, {})
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

if __name__=='__main__':unittest.main()
