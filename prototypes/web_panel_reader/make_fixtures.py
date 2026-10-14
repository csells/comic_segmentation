"""New synthetic CBZs; never reproduce private books or call a model."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import warnings
import zipfile
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument('destination', type=Path)
parser.add_argument('--adapter-directory', required=True, type=Path)
args = parser.parse_args()
sys.path.insert(0, str(args.adapter_directory))
from adapter import build_cbz

dest = args.destination
dest.mkdir(parents=True, exist_ok=False)
pages = dest / 'pages'
pages.mkdir()
font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
big = ImageFont.truetype(font_path, 120)
small = ImageFont.truetype(font_path, 35)
for name, title, subtitle in [
    ('cover.png', 'Panel lab', 'SYNTHETIC ORDER TEST'),
    ('fallback.png', 'Whole page', 'PRESERVED WITHOUT PANEL GUIDANCE'),
]:
    im = Image.new('RGB', (1000, 1500), '#f4eee2')
    draw = ImageDraw.Draw(im)
    draw.rectangle((60, 70, 940, 1430), outline='#202334', width=8)
    draw.text((105, 500), title, font=big, fill='#202334')
    draw.text((105, 700), subtitle, font=small, fill='#202334')
    if name == 'cover.png':
        draw.text((105, 800), 'Next: 3 → 1 → 4 → 2', font=small, fill='#202334')
    im.save(pages / name)

im = Image.new('RGB', (1000, 1500), 'white')
draw = ImageDraw.Draw(im)
rects = [(50,50,900,350), (50,450,250,450), (350,450,600,450), (50,950,900,450)]
for n, ((x,y,w,h), color) in enumerate(zip(rects, ['#f4d76d','#8ac2b2','#e4a895','#a4bce3']), 1):
    draw.rectangle((x,y,x+w,y+h), fill=color, outline='#202334', width=10)
    draw.text((x+28,y+28), str(n), font=big, fill='#202334')
im.save(pages / 'story.png')
panels = [{'x':x/1000,'y':y/1500,'w':w/1000,'h':h/1500} for x,y,w,h in rects]
data = {'total_pages':3,'reading_direction':'ltr','pages':[
    {'page':1,'image':'cover.png','panels':[{'x':0,'y':0,'w':1,'h':1}]},
    {'page':2,'image':'story.png','panels':[panels[i-1] for i in [3,1,4,2]]},
    {'page':3,'image':'fallback.png','panels':[]},
]}
manifest = build_cbz(pages, data, dest/'stored-control.cbz', title='Panel lab · 3 → 1 → 4 → 2')
(dest/'stored-control.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(dest/'stored-control.cbz') as src:
    entries = [(n,src.read(n)) for n in src.namelist()]
for name in ['order-control.cbz','bounds.cbz','duplicate.cbz','legacy-control.cbz','profile-mismatch.cbz']:
    candidate = dict(entries)
    if name == 'bounds.cbz':
        candidate['metadata.acbf'] = candidate['metadata.acbf'].replace(b'350,450', b'3500,450', 1)
        profile = json.loads(candidate['panel-reader.json'])
        profile['metadata_sha256'] = hashlib.sha256(candidate['metadata.acbf']).hexdigest()
        candidate['panel-reader.json'] = json.dumps(profile).encode()
    elif name == 'legacy-control.cbz':
        del candidate['panel-reader.json']
    elif name == 'profile-mismatch.cbz':
        profile = json.loads(candidate['panel-reader.json'])
        profile['metadata_sha256'] = '0' * 64
        candidate['panel-reader.json'] = json.dumps(profile).encode()
    with zipfile.ZipFile(dest/name, 'x', compression=zipfile.ZIP_DEFLATED) as out:
        for n,b in candidate.items():
            out.writestr(n,b)
        if name=='duplicate.cbz':
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                out.writestr(entries[0][0],entries[0][1])
                assert any('Duplicate name' in str(w.message) for w in caught)
rtl = build_cbz(pages, {**data, 'reading_direction':'rtl'}, dest/'rtl-control.cbz', title='Panel lab · RTL controls')
(dest/'rtl-control.manifest.json').write_text(json.dumps(rtl,indent=2)+'\n')
single_pages = dest/'single-pages'; single_pages.mkdir()
(single_pages/'story.png').write_bytes((pages/'story.png').read_bytes())
single = build_cbz(single_pages, {'total_pages':1, 'reading_direction':'ltr', 'pages':[
    {**data['pages'][1], 'page':1}]}, dest/'single-control.cbz', title='Panel lab · one source page')
(dest/'single-control.manifest.json').write_text(json.dumps(single,indent=2)+'\n')
print('Created synthetic order, RTL, legacy, profile, bounds and duplicate controls in',dest)
