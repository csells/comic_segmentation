import unittest
from decisions_probe import QUESTIONS, parse_answers, decision_cost, experiment_bundle, experiment_questions


def response(probability=0.01):
    return {'model':'gpt-6-luna', 'answers':[
        {'type':'predicate','name':q['name'],'probability':probability} for q in QUESTIONS]}


class DecisionsTests(unittest.TestCase):
    def test_target_variant_keeps_source_and_exact_target_only(self):
        bundle = {'target_order':2,'images':[{'label':'Original complete page'},
            {'label':'Proposed rectangles numbered in reading order'},
            {'label':'Candidate crop 1 in reading order'},
            {'label':'Candidate crop 2 in reading order'}]}
        self.assertEqual([x['label'] for x in experiment_bundle(bundle,'target-v3')['images']],
                         ['Original complete page','Candidate crop 2 in reading order'])
        questions = experiment_questions('target-v3')
        self.assertEqual([q['name'] for q in questions], ['text_clipping','art_clipping'])
        raw = response(); raw['answers'] = raw['answers'][2:]
        self.assertEqual(parse_answers(raw,questions)['route'], 'keep')

    def test_clean_variant_removes_only_overlay_without_mutating_source(self):
        bundle = {'classification':'panels','panels':[], 'images':[
            {'label':'Original complete page'},
            {'label':'Proposed rectangles numbered in reading order'},
            {'label':'Candidate crop 1 in reading order'}]}
        clean = experiment_bundle(bundle, 'clean-v2')
        self.assertEqual(len(clean['images']), 2)
        self.assertEqual(len(bundle['images']), 3)
        self.assertEqual(experiment_bundle(bundle, 'prompt-v2'), bundle)
        self.assertEqual([q['name'] for q in experiment_questions('clean-v2')],
                         [q['name'] for q in QUESTIONS])
        self.assertNotEqual(experiment_questions('prompt-v2'), QUESTIONS)

    def test_any_defect_at_threshold_escalates(self):
        raw = response()
        self.assertEqual(parse_answers(raw)['route'], 'keep')
        raw['answers'][2]['probability'] = 0.5
        self.assertEqual(parse_answers(raw)['route'], 'escalate')

    def test_refusal_missing_duplicate_and_reordered_fail_closed(self):
        for mutate in (lambda a:a.pop(), lambda a:a.reverse(),
                       lambda a:a[0].update(type='refusal'),
                       lambda a:a[1].update(name=a[0]['name'])):
            raw = response(); mutate(raw['answers'])
            with self.assertRaises(ValueError): parse_answers(raw)

    def test_invalid_probabilities_fail_closed(self):
        for bad in (float('nan'), float('inf'), -0.1, 1.1, True, '0.1', None):
            raw = response(); raw['answers'][0]['probability'] = bad
            with self.assertRaises(ValueError): parse_answers(raw)

    def test_native_billing_and_long_context(self):
        self.assertEqual(decision_cost({'input_tokens':101,'output_tokens':0,'total_tokens':101}), 11)
        self.assertEqual(decision_cost({'input_tokens':272001,'output_tokens':0,'total_tokens':272001}), 54401)
        self.assertIsNone(decision_cost({}))
        for usage in ({'input_tokens':True}, {'input_tokens':-1},
                      {'input_tokens':1,'output_tokens':1,'total_tokens':2}):
            with self.assertRaises(ValueError): decision_cost(usage)


if __name__ == '__main__': unittest.main()
