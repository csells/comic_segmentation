import unittest
from gemini_probe import interaction_response
from gemini_budget import usage_cost


class InteractionTests(unittest.TestCase):
    def test_completed_usage_includes_thoughts(self):
        result = interaction_response({'status':'completed',
            'steps':[{'type':'thought','content':[{'type':'text','text':'ignore'}]},
                     {'type':'model_output','content':[{'type':'text','text':'{}'}]}],
            'usage':{'total_input_tokens':100,'total_output_tokens':20,
                     'total_thought_tokens':80,'total_tokens':200}})
        self.assertEqual(result['candidates'][0]['content']['parts'],[{'type':'text','text':'{}'}])
        self.assertEqual(usage_cost(result['usageMetadata']),450)

    def test_incomplete_is_never_accepted(self):
        for status in ('in_progress','incomplete','failed','requires_action'):
            with self.assertRaises(ValueError):
                interaction_response({'status':status})


if __name__ == '__main__':
    unittest.main()
