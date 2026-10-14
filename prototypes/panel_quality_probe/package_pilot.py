"""Package saved model results into a new private ACBF pilot; never call inference."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'comic_panel_e2e'))
from adapter import build_cbz
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('images',type=Path);p.add_argument('output',type=Path)
p.add_argument('--filename',default='openai-astra-pilot.cbz');p.add_argument('--title',default='OpenAI Astra · four difficult pages');a=p.parse_args()
if Path(a.filename).name!=a.filename or not a.filename.endswith('.cbz'):p.error('filename must be a CBZ basename')
a.output.mkdir(parents=True,exist_ok=False);pages=a.output/'pages';pages.mkdir()
results=json.loads((a.run/'results.json').read_text());assert all(x['status']=='structurally_valid_unreviewed' for x in results)
entries=[];mapping={};provenance=[]
for index,record in enumerate([{'source_page':1}]+results,1):
 page=record['source_page'];source=a.images/f'{page:04}.jpg';dest=pages/f'{index:04}.jpg';shutil.copyfile(source,dest)
 if index==1:panels=[{'box':[0,0,1000,1000]}]
 else:
  req=json.loads((a.run/f'page-{page:04}'/'request.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==req['source_sha256']
  panels=json.loads((a.run/f'page-{page:04}'/'panels.json').read_text())['panels'];provenance.append({'source_page':page,'request_id':req['request_id']})
 boxes=[]
 for panel in panels:
  y,x,b,r=panel['box'];boxes.append({'x':x/1000,'y':y/1000,'w':(r-x)/1000,'h':(b-y)/1000})
 entries.append({'page':index,'image':dest.name,'panels':boxes});mapping[index]=page
manifest=build_cbz(pages,{'pages':entries,'total_pages':len(entries),'reading_direction':'ltr'},a.output/a.filename,title=a.title,source_map=mapping)
(a.output/'source-provenance.json').write_text(json.dumps({'source_run':str(a.run),'manual_geometry':False,'source_pages':mapping,'requests':provenance},indent=2)+'\n')
print(json.dumps(manifest,indent=2))
