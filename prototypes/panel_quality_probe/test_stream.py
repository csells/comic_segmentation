import json
import unittest
from gemini_probe import merge_chunks, parse


class StreamTests(unittest.TestCase):
    def test_fragmented_json_uses_final_usage_and_requires_stop(self):
        value={'classification':'whole_page','orientation':'upright','reading_direction':'ltr',
               'panels':[{'order':1,'description':'single scene',
                          'bounds':{'left':0,'top':0,'right':1000,'bottom':1000}}]}
        text=json.dumps(value)
        chunks=[{'candidates':[{'content':{'parts':[{'text':text[:40]}]}}]},
                {'candidates':[{'content':{'parts':[{'text':text[40:]}]},'finishReason':'STOP'}]},
                {'usageMetadata':{'promptTokenCount':100,'totalTokenCount':220}}]
        result=merge_chunks(chunks)
        self.assertEqual(parse(result)['panels'][0]['box'],[0,0,1000,1000])
        self.assertEqual(result['usageMetadata']['totalTokenCount'],220)
        del chunks[1]['candidates'][0]['finishReason']
        with self.assertRaises(ValueError):
            parse(merge_chunks(chunks))

    def test_multiple_candidates_and_error_do_not_become_success(self):
        with self.assertRaises(ValueError):
            merge_chunks([{'candidates':[{},{}]}])
        with self.assertRaises(ValueError):
            merge_chunks([{'error':{'message':'unavailable'}}])


if __name__=='__main__':
    unittest.main()
