"""Detector-independent continuity diagnosis with preceding source-page context."""
import base64
from pathlib import Path
from continuity_verifier import SCHEMA


def request_body(previous_pages, source, region):
    previous_pages=list(previous_pages)
    if not 1 <= len(previous_pages) <= 2:raise ValueError('one or two preceding pages required')
    prompt=(Path(__file__).parent/'narrative-context-prompt-v3.txt').read_text()
    content=[{'type':'input_text','text':prompt+'\nPreceding context pages supplied: '+str(len(previous_pages))}]
    for path in (*previous_pages,source,region):
        content.append({'type':'input_image','image_url':'data:image/jpeg;base64,'+
                        base64.b64encode(Path(path).read_bytes()).decode(),'detail':'original'})
    return {'model':'gpt-6-astra','store':False,'max_output_tokens':4096,
            'reasoning':{'effort':'high'},'service_tier':'default',
            'text':{'format':{'type':'json_schema','name':'source_continuity','strict':True,'schema':SCHEMA}},
            'input':[{'role':'user','content':content}]}
