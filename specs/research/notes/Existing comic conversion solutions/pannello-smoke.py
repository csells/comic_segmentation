from PIL import Image, ImageDraw
from pathlib import Path
from zipfile import ZipFile
import hashlib, json, subprocess, sys, platform
root=Path(__file__).parent
inputs=root/'fixtures'
inputs.mkdir()
images=[]
layouts=[[],[(40,40,370,540),(430,40,760,540),(40,620,370,1120),(430,620,760,1120)],[(40,40,760,540),(40,620,760,1120)]]
for name,boxes in zip(['page1.png','page2.png','page10.png'],layouts):
 im=Image.new('RGB',(800,1160),'white')
 draw=ImageDraw.Draw(im)
 for i,b in enumerate(boxes):
  draw.rectangle(b,fill=['lightblue','lightgreen','pink','khaki'][i],outline='black',width=8)
  draw.line((b[0]+30,b[1]+30,b[2]-30,b[3]-30),fill='black',width=4)
 im.save(inputs/name)
 images.append(im)
images[0].save(root/'synthetic.pdf',save_all=True,append_images=images[1:],resolution=150)
with ZipFile(root/'synthetic.cbz','x') as z:
 for name in ['page10.png','page1.png','page2.png']: z.write(inputs/name,name)
 z.writestr('ComicInfo.xml','<ComicInfo><Title>SMOKE TEST</Title><Manga>YesAndRightToLeft</Manga></ComicInfo>')
 z.writestr('notes.txt','Synthetic auxiliary file for retention test.')
original={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs.iterdir()}
book_hash=hashlib.sha256((root/'synthetic.cbz').read_bytes()).hexdigest()
exe=root/'venv/bin/pannello'
runs=[('cbz_direct',[str(root/'synthetic.cbz')]),('cbz_repack',['--repack',str(root/'synthetic.cbz')]),('pdf_repack',['--repack',str(root/'synthetic.pdf')]),('folder_repack',['--repack',str(inputs)])]
report={'platform':platform.platform(),'python':sys.version,'runs':[]}
for name,args in runs:
 dest=root/name
 cmd=[str(exe),*args,'--fallback','none','-j','1','-o',str(dest)]
 p=subprocess.run(cmd,capture_output=True,text=True)
 entry={'name':name,'command':cmd,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 data=list(dest.glob('*.json'))
 if data:
  entry['metadata']=json.loads(data[0].read_text())
 for archive in dest.glob('*.cbz'):
  with ZipFile(archive) as z:
   entry['archive_entries']=z.namelist()
   entry['image_hashes']={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
 report['runs'].append(entry)
assert hashlib.sha256((root/'synthetic.cbz').read_bytes()).hexdigest()==book_hash
assert original=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs.iterdir()}
report['input_preserved']=True
report['original_image_hashes']=original
(root/'smoke-report.json').write_text(json.dumps(report,indent=2))
for r in report['runs']:
 print(r['name'],'exit',r['exit'],'direction',r.get('metadata',{}).get('reading_direction'),'panel_counts',[len(p['panels']) for p in r.get('metadata',{}).get('pages',[])])
 print('entries',r.get('archive_entries'))
 print(r['stderr'])
print('Inputs preserved; report:',root/'smoke-report.json')
