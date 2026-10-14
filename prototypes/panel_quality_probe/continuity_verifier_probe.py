"""Independent stronger source-only continuity diagnosis on frozen regions."""
import argparse,base64,json,sys
from pathlib import Path
from auto_convert import Client
from gemini_budget import Budget

SCHEMA={'type':'object','properties':{
 'classification':{'type':'string','enum':['continuous','distinct','uncertain']},
 'views':{'type':'array','items':{'type':'string'}},
 'evidence':{'type':'string'}},'required':['classification','views','evidence'],'additionalProperties':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--ledger',type=Path,required=True);p.add_argument('--regions',type=Path,nargs='+',required=True);a=p.parse_args();key=sys.stdin.readline().strip();a.output.mkdir(exist_ok=False,parents=True)
 prompt=(Path(__file__).parent/'continuity-verifier-prompt-v1.txt').read_text();results=[]
 with Budget(a.ledger,cap=20000000) as budget:
  client=Client(key,budget,a.output/'calls')
  for i,region in enumerate(a.regions,1):
   body={'model':'gpt-6-sol','store':False,'max_output_tokens':4096,'reasoning':{'effort':'high'},'service_tier':'default','text':{'format':{'type':'json_schema','name':'source_continuity','strict':True,'schema':SCHEMA}},'input':[{'role':'user','content':[
    {'type':'input_text','text':prompt},{'type':'input_image','image_url':'data:image/jpeg;base64,'+base64.b64encode(region.read_bytes()).decode(),'detail':'original'}]}]}
   raw,request=client.request('responses',body,'verifier')
   value=json.loads(''.join(c.get('text','') for v in raw.get('output',[]) for c in v.get('content',[]) if c.get('type')=='output_text'))
   result={'region':str(region),'verdict':value,'request':request};results.append(result);(a.output/f'result-{i:03}.json').write_text(json.dumps(result,indent=2)+'\n');print(f'[{i}/{len(a.regions)}]',region.name,value,flush=True)
  (a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n');print('Used/held',budget.used(),flush=True)
if __name__=='__main__':main()
