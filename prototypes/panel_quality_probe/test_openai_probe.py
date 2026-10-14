import unittest
from openai_probe import response_panels, strict_schema, response_usage
from gemini_budget import usage_cost

class OpenAIProbeTests(unittest.TestCase):
    def test_only_completed_output_is_accepted(self):
        for status in ('incomplete','failed','in_progress'):
            with self.assertRaises(ValueError): response_panels({'status':status})
        with self.assertRaises(ValueError):
            response_panels({'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'no'}]}]})

    def test_schema_closes_all_objects(self):
        s=strict_schema()
        def visit(x):
            if isinstance(x,dict):
                if x.get('type')=='object':
                    self.assertIs(x['additionalProperties'],False)
                    self.assertEqual(set(x['required']),set(x['properties']))
                for v in x.values():visit(v)
            elif isinstance(x,list):
                for v in x:visit(v)
        visit(s)

    def test_reasoning_tokens_count_once(self):
        u=response_usage({'usage':{'input_tokens':1000,'output_tokens':2000,
             'total_tokens':3000,'output_tokens_details':{'reasoning_tokens':1500}}})
        self.assertEqual(usage_cost(u,12.5,50),112500)

if __name__=='__main__': unittest.main()
