"""Re-render the verified PDF and package saved pixel frames, without inference.

Run inside disposable staging. This creates new review artifacts, never claims
to restore the original CBZ bytes. The historical manifests remain unchanged.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET
import zipfile
from PIL import Image

SOURCE_SHA = '30d075d2bf54cdcd2401ccf905ab50a859779296e7afdbff404efd291f42cd32'
NS = 'http://www.acbf.info/xml/acbf/1.1'
ET.register_namespace('', NS)

def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def replay(source, manifest_path, output, mode):
    if sha(source) != SOURCE_SHA: raise ValueError('Source PDF hash does not match recorded experiment')
    manifest = json.loads(manifest_path.read_text())
    expected = 4 if mode == 'gemini' else 257
    assert manifest['page_count'] == expected == len(manifest['pages'])
    selected = [1,3,5,25] if mode == 'gemini' else list(range(1,258))
    assert [p['source_page'] for p in manifest['pages']] == selected
    output.mkdir(parents=True, exist_ok=False)
    pages = output/'pages'; pages.mkdir()
    root = ET.Element(f'{{{NS}}}ACBF')
    def tag(parent, name, text=None, **attrs):
        e=ET.SubElement(parent, f'{{{NS}}}{name}', attrs); e.text=text; return e
    meta=tag(root,'meta-data'); book=tag(meta,'book-info')
    tag(tag(book,'author'),'nickname','Unknown')
    title = 'Parallel Truths · saved Gemini sample' if mode=='gemini' else 'Parallel Truths · saved local detector'
    tag(book,'book-title',title); cover=tag(book,'coverpage'); tag(meta,'publish-info')
    doc=tag(meta,'document-info'); tag(tag(doc,'author'),'nickname','Offline saved-result replay')
    tag(doc,'creation-date',date.today().isoformat(),value=date.today().isoformat())
    tag(doc,'id','saved-replay-'+mode+'-'+sha(manifest_path)[:20]); body=tag(root,'body')
    records=[]
    for i, old in enumerate(manifest['pages'],1):
        assert old['page']==i
        name=old['archive_image']
        assert Path(name).name==name and Path(name).suffix in ('.png','.jpg')
        print(f'[{i}/{expected}] rendering source PDF page {old["source_page"]}',flush=True)
        args=['pdftoppm','-f',str(old['source_page']),'-l',str(old['source_page']),'-singlefile']
        args += ['-png','-scale-to','1500'] if mode=='gemini' else ['-jpeg','-r','150']
        subprocess.run(args+[str(source),str((pages/name).with_suffix(''))],check=True,timeout=180)
        image=pages/name
        with Image.open(image) as im:
            im.load(); assert im.size==(old['width'],old['height']), (name,im.size)
        page=cover if i==1 else tag(body,'page'); tag(page,'image',href=name)
        assert len(old['frames'])==old['frame_count'] and old['frames']
        for frame in old['frames']:
            pts=[tuple(map(int,p.split(','))) for p in frame.split()]
            assert len(pts)>=3 and all(0<=x<old['width'] and 0<=y<old['height'] for x,y in pts)
            tag(page,'frame',points=frame) # exact recorded coordinates and sequence
        digest=sha(image)
        records.append({**old,'historical_image_sha256':old['sha256'],'sha256':digest,
                        'historical_image_bytes_match':digest==old['sha256']})
    xml=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    path=output/('gemini-saved.cbz' if mode=='gemini' else 'local-saved.cbz')
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_STORED) as z:
        for p in records:z.write(pages/p['archive_image'],p['archive_image'])
        z.writestr('metadata.acbf',xml)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert len(z.namelist())==expected+1
        assert [e.attrib['points'] for e in ET.fromstring(z.read('metadata.acbf')).iter(f'{{{NS}}}frame')] == [f for p in manifest['pages'] for f in p['frames']]
        for p in records:assert hashlib.sha256(z.read(p['archive_image'])).hexdigest()==p['sha256']
    assert sha(source)==SOURCE_SHA
    report={'kind':'offline_saved_geometry_replay','source_pdf_sha256':SOURCE_SHA,
            'historical_manifest_sha256':sha(manifest_path),'historical_cbz_sha256':manifest['output_sha256'],
            'output_file':path.name,'output_sha256':sha(path),'output_bytes':path.stat().st_size,
            'page_count':expected,'frame_count':sum(p['frame_count'] for p in records),
            'fallback_count':sum(bool(p['fallback_reason']) for p in records),
            'new_model_calls':0,'render_version':subprocess.run(['pdftoppm','-v'],capture_output=True,text=True,check=True).stderr.strip(),
            'pages':records}
    (output/'replay.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='pages'},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('manifest',type=Path)
    parser.add_argument('output',type=Path);parser.add_argument('--mode',choices=['gemini','local'],required=True)
    a=parser.parse_args();replay(a.source,a.manifest,a.output,a.mode)
