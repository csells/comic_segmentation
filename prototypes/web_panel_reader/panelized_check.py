"""Inspect every guided step in an actual generated CBZ using isolated Chrome.

Usage: python panelized_check.py CDP_URL OUTPUT_DIRECTORY SITE_URL CBZ [PANEL_COUNT] [CATALOG_ID]
Run only in the disposable browser VM. Does not infer or alter panel metadata.
"""
import asyncio
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

from lxml import etree
from PIL import Image
import websockets


def inspect_archive(path):
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith('.acbf')]
        assert len(names) == 1, names
        root = etree.fromstring(archive.read(names[0]), etree.XMLParser(resolve_entities=False, no_network=True))
        ns = {'a': 'http://www.acbf.info/xml/acbf/1.1'}
        nodes = root.xpath('./a:meta-data/a:book-info/a:coverpage | ./a:body/a:page', namespaces=ns)
        pages = []
        for node in nodes:
            image_path = node.find('a:image', ns).attrib['href']
            image_bytes = archive.read(image_path)
            with Image.open(io.BytesIO(image_bytes)) as image:
                width, height = image.size
                pixel_hash = hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()
            rects = []
            for frame in node.findall('a:frame', ns):
                points = [tuple(map(int, point.split(','))) for point in frame.attrib['points'].split()]
                xs, ys = zip(*points)
                rects.append({'x': min(xs), 'y': min(ys), 'width': max(xs)-min(xs), 'height': max(ys)-min(ys)})
            whole = len(rects) == 1 and rects[0]['x'] <= 1 and rects[0]['y'] <= 1 and abs(rects[0]['x']+rects[0]['width']-width) <= 1 and abs(rects[0]['y']+rects[0]['height']-height) <= 1
            overview = {'x': 0, 'y': 0, 'width': width, 'height': height}
            pages.append({'image_path': image_path, 'width': width, 'height': height,
                          'image_bytes_sha256': hashlib.sha256(image_bytes).hexdigest(),
                          'image_rgb_sha256': pixel_hash, 'metadata_frames': rects,
                          'steps': [overview] if whole or not rects else [overview, *rects]})
        return pages


async def main():
    output = Path(sys.argv[2]); output.mkdir(exist_ok=False)
    book = Path(sys.argv[4]); original_hash = hashlib.file_digest(book.open('rb'), 'sha256').hexdigest()
    pages = inspect_archive(book)
    panel_count = sum(len(page['steps'])-1 for page in pages)
    if len(sys.argv) > 5:
        assert panel_count == int(sys.argv[5]), panel_count
    result = {'scope': 'Actual generated CBZ playback; preserves converter metadata without correction',
              'archive': str(book), 'archive_sha256': original_hash,
              'expected_pages': pages, 'panel_count': panel_count, 'steps': []}
    (output/'expected.json').write_text(json.dumps(result, indent=2))
    tab = next(t for t in json.load(urllib.request.urlopen(sys.argv[1]+'/json')) if t['type'] == 'page')
    counter = 0; errors = []
    async with websockets.connect(tab['webSocketDebuggerUrl'], max_size=32*1024*1024) as ws:
        async def command(method, **params):
            nonlocal counter
            counter += 1
            await ws.send(json.dumps({'id': counter, 'method': method, 'params': params}))
            async with asyncio.timeout(30):
                while True:
                    data = json.loads(await ws.recv())
                    if data.get('method') == 'Runtime.exceptionThrown': errors.append(data['params'])
                    if data.get('id') == counter:
                        assert 'error' not in data, data
                        return data.get('result', {})

        async def evaluate(expression):
            value = await command('Runtime.evaluate', expression=expression, awaitPromise=True, returnByValue=True)
            assert 'exceptionDetails' not in value, value
            return value['result'].get('value')

        async def until(expression):
            async with asyncio.timeout(30):
                while not await evaluate(expression): await asyncio.sleep(.05)

        async def advance(direction):
            x = 30 if direction == 'rtl' else 350
            for kind in ['mousePressed', 'mouseReleased']:
                await command('Input.dispatchMouseEvent', type=kind, x=x, y=400, button='left', clickCount=1)

        await command('Runtime.enable'); await command('Page.enable')
        await command('Emulation.setDeviceMetricsOverride', width=390, height=844, deviceScaleFactor=1, mobile=True)
        await command('Page.navigate', url=sys.argv[3].rstrip('/')+'/')
        await until('!!window.__panelview')
        await evaluate('localStorage.clear()')
        if len(sys.argv) > 6:
            catalog_id = sys.argv[6]
            catalog = json.load(urllib.request.urlopen(sys.argv[3].rstrip('/')+'/catalog.json'))
            entry = next(item for item in catalog if item['id'] == catalog_id)
            served = urllib.request.urlopen(sys.argv[3].rstrip('/')+'/'+entry['file']).read()
            assert hashlib.sha256(served).hexdigest() == original_hash
            selector = '#book-list button[data-book='+json.dumps(catalog_id)+']'
            await until('!!document.querySelector('+json.dumps(selector)+')')
            await evaluate('document.querySelector('+json.dumps(selector)+').scrollIntoView({block:"center",behavior:"instant"})')
            await asyncio.sleep(.2)
            shot = await command('Page.captureScreenshot', format='png')
            (output/'catalog-card.png').write_bytes(base64.b64decode(shot['data']))
            button = await evaluate('''(() => {
              const b=document.querySelector('''+json.dumps(selector)+'''),r=b.getBoundingClientRect();
              const x=r.x+r.width/2,y=r.y+r.height/2;
              return {x,y,hit:b.contains(document.elementFromPoint(x,y)),text:b.closest('article').innerText};})()''')
            assert button.pop('hit'), button
            result['catalog_entry'] = entry
            result['catalog_card_text'] = button.pop('text')
            for kind in ['mousePressed', 'mouseReleased']:
                await command('Input.dispatchMouseEvent', type=kind, **button, button='left', clickCount=1)
        else:
            dom = await command('DOM.getDocument')
            node = await command('DOM.querySelector', nodeId=dom['root']['nodeId'], selector='#file-input')
            await command('DOM.setFileInputFiles', nodeId=node['nodeId'], files=[str(book)])
        await until(f'__panelview.state.book?.pages.length==={len(pages)} && !!__panelview.state.guided')
        direction = await evaluate('__panelview.state.readingDirection')
        result['reading_direction'] = direction
        result['reader_build'] = json.load(urllib.request.urlopen(sys.argv[3].rstrip('/')+'/build.json'))
        ordinal = 0
        for page_index, page in enumerate(pages):
            for step_index, expected in enumerate(page['steps']):
                if ordinal: await advance(direction)
                await until(f'''(() => {{const s=__panelview.state,g=s.guided;
                  return s.page==={page_index} && s.panel==={step_index}
                    && g?.img.isConnected && g.viewport.isConnected && g.img.complete
                    && g.img.naturalWidth==={page['width']} && g.img.naturalHeight==={page['height']}
                    && g.img.src===s.urls[s.page] && g.rects===s.panelCache[s.page]
                    && g.img.getBoundingClientRect().width>0;}})()''')
                await asyncio.sleep(1)  # Camera transition is 850 ms.
                snapshot = await evaluate('''(() => {
                  const s=__panelview.state,g=s.guided,r=g.rects[s.panel];
                  const im=g.img.getBoundingClientRect(),v=g.viewport.getBoundingClientRect(),z=im.width/g.img.naturalWidth;
                  const t={left:im.left+r.x*z,top:im.top+r.y*z,right:im.left+(r.x+r.width)*z,bottom:im.top+(r.y+r.height)*z};
                  return {page:s.page,step:s.panel,stepCount:g.rects.length,rect:r,
                    connected:g.img.isConnected&&g.viewport.isConnected,
                    sourceBound:g.img.src===s.urls[s.page]&&g.rects===s.panelCache[s.page],
                    image:[g.img.naturalWidth,g.img.naturalHeight],target:t,
                    viewport:{left:v.left,top:v.top,right:v.right,bottom:v.bottom},
                    contained:t.left>=v.left-1&&t.top>=v.top-1&&t.right<=v.right+1&&t.bottom<=v.bottom+1,
                    centered:Math.abs((t.left+t.right-v.left-v.right)/2)<=2&&Math.abs((t.top+t.bottom-v.top-v.bottom)/2)<=2};})()''')
                assert snapshot['page'] == page_index and snapshot['step'] == step_index, snapshot
                assert snapshot['stepCount'] == len(page['steps']), snapshot
                assert all(abs(snapshot['rect'][key]-value) < .001 for key, value in expected.items()), (expected, snapshot)
                assert snapshot['connected'] and snapshot['sourceBound'] and snapshot['contained'] and snapshot['centered'], snapshot
                assert snapshot['target']['right'] > snapshot['target']['left'] and snapshot['target']['bottom'] > snapshot['target']['top'], snapshot
                assert bool(snapshot['rect'].get('overview')) == (step_index == 0), snapshot
                label = f'page-{page_index+1:03}-'+('overview' if step_index == 0 else f'panel-{step_index:03}')
                shot = await command('Page.captureScreenshot', format='png')
                (output/(label+'.png')).write_bytes(base64.b64decode(shot['data']))
                result['steps'].append({'label': label, **snapshot})
                (output/'partial-results.json').write_text(json.dumps(result, indent=2))
                print('PASS', label, 'rect', expected, flush=True)
                ordinal += 1
        await advance(direction); await asyncio.sleep(.2)
        assert await evaluate(f'__panelview.state.page==={len(pages)-1} && __panelview.state.panel==={len(pages[-1]["steps"])-1}'), 'End invented a guided step'
        result['end_boundary_passed'] = True
        result['uncaught_exceptions'] = errors
        result['archive_unchanged'] = hashlib.file_digest(book.open('rb'), 'sha256').hexdigest() == original_hash
        assert not errors and result['archive_unchanged']
        (output/'results.json').write_text(json.dumps(result, indent=2))
        print('PASS complete archive:', len(pages), 'pages,', panel_count, 'panels,', ordinal, 'guided steps; no corrections', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
