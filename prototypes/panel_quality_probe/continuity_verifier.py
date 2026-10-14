"""Independent source-only adjudication of exhausted-tier continuity warnings."""
import base64
import json
from pathlib import Path

SCHEMA={'type':'object','properties':{
 'classification':{'type':'string','enum':['continuous','distinct','uncertain']},
 'views':{'type':'array','items':{'type':'string'}},
 'evidence':{'type':'string'}},'required':['classification','views','evidence'],'additionalProperties':False}


def request_body(region):
    prompt=(Path(__file__).parent/'continuity-verifier-prompt-v2.txt').read_text()
    return {'model':'gpt-6-sol','store':False,'max_output_tokens':4096,'reasoning':{'effort':'high'},'service_tier':'default',
            'text':{'format':{'type':'json_schema','name':'source_continuity','strict':True,'schema':SCHEMA}},
            'input':[{'role':'user','content':[
                {'type':'input_text','text':prompt},
                {'type':'input_image','image_url':'data:image/jpeg;base64,'+base64.b64encode(Path(region).read_bytes()).decode(),'detail':'original'}]}]}


def response_verdict(raw):
    if raw.get('status','completed')!='completed':
        raise ValueError('incomplete source-continuity adjudication')
    value=json.loads(''.join(c.get('text','') for v in raw.get('output',[])
                            for c in v.get('content',[]) if c.get('type')=='output_text'))
    if not isinstance(value,dict) or set(value)!={'classification','views','evidence'}:
        raise ValueError('invalid source-continuity fields')
    if value['classification'] not in ('continuous','distinct','uncertain'):
        raise ValueError('invalid source-continuity classification')
    if not isinstance(value['views'],list) or any(not isinstance(v,str) or not v.strip() for v in value['views']):
        raise ValueError('invalid source-continuity view descriptions')
    if not isinstance(value['evidence'],str) or not value['evidence'].strip():
        raise ValueError('source-continuity evidence required')
    if value['classification']=='distinct' and len(value['views'])<2:
        raise ValueError('distinct verdict requires multiple described views')
    if value['classification']=='continuous' and len(value['views'])!=1:
        raise ValueError('continuous verdict requires one described view')
    return value
