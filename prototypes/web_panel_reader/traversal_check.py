"""All-page guided playback, with streamed evidence and selected screenshots.

Run only in the disposable browser VM. Product bytes and metadata are unchanged.
Usage: traversal_check.py CDP_URL OUTPUT SITE_URL CBZ [EXPECTED_BUILD] [EXPECTED_DIRECTION]
The existing panelized_check remains the immutable small-book test harness.
"""
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request
import zipfile

import websockets

from panelized_check import inspect_archive


async def main():
    output = Path(sys.argv[2]); output.mkdir(exist_ok=False)
    book = Path(sys.argv[4])
    archive_sha = hashlib.file_digest(book.open('rb'), 'sha256').hexdigest()
    pages = inspect_archive(book)
    expected_steps = sum(len(page['steps']) for page in pages)
    expected_build = sys.argv[5] if len(sys.argv) > 5 else 'e5a769ca768d395e'
    with zipfile.ZipFile(book) as archive:
        direction = 'ltr'
        if 'panel-reader.json' in archive.namelist():
            profile = json.loads(archive.read('panel-reader.json'))
            assert profile['format'] == 'comic-panel-reader-profile' and profile['version'] == 1
            assert profile['metadata_sha256'] == hashlib.sha256(archive.read('metadata.acbf')).hexdigest()
            direction = profile['reading_direction']
        assert direction in ('ltr', 'rtl')
    if len(sys.argv) > 6:
        assert direction == sys.argv[6], 'Published profile differs from expected source direction'
    result = {'scope': 'Every actual metadata step; reader transport/rendering, not semantic segmentation judgment',
              'archive_sha256': archive_sha, 'archive_bytes': book.stat().st_size,
              'pages': len(pages), 'expected_steps': expected_steps, 'checked_steps': 0,
              'expected_reading_direction': direction,
              'source_direction_asserted': len(sys.argv) > 6,
              'screenshots': [], 'page_metrics': [], 'complete': False,
              'memory_scope': 'JS heap excludes native image memory; runner records aggregate process RSS separately'}
    (output/'expected.json').write_text(json.dumps(pages, indent=2)+'\n')
    tab = next(t for t in json.load(urllib.request.urlopen(sys.argv[1]+'/json')) if t['type'] == 'page')
    errors = []; counter = 0
    selected_pages = {0, len(pages)//2, len(pages)-1}
    with (output/'steps.jsonl').open('x') as stream:
        async with websockets.connect(tab['webSocketDebuggerUrl'], max_size=32*1024*1024) as ws:
            async def command(method, **params):
                nonlocal counter
                counter += 1
                await ws.send(json.dumps({'id': counter, 'method': method, 'params': params}))
                async with asyncio.timeout(40):
                    while True:
                        data = json.loads(await ws.recv())
                        if data.get('method') == 'Runtime.exceptionThrown': errors.append(data['params'])
                        if data.get('id') == counter:
                            assert 'error' not in data, data
                            return data.get('result', {})

            async def evaluate(code):
                value = await command('Runtime.evaluate', expression=code, awaitPromise=True, returnByValue=True)
                assert 'exceptionDetails' not in value, value
                return value['result'].get('value')

            async def until(code):
                async with asyncio.timeout(40):
                    while not await evaluate(code): await asyncio.sleep(.05)

            async def screenshot(label):
                shot = await command('Page.captureScreenshot', format='png')
                path = output/(label+'.png'); path.write_bytes(base64.b64decode(shot['data']))
                result['screenshots'].append({'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

            async def click(x, y):
                for kind in ('mousePressed', 'mouseReleased'):
                    await command('Input.dispatchMouseEvent', type=kind, x=x, y=y,
                                  button='left', clickCount=1)

            async def load_file():
                dom = await command('DOM.getDocument')
                node = await command('DOM.querySelector', nodeId=dom['root']['nodeId'], selector='#file-input')
                await command('DOM.setFileInputFiles', nodeId=node['nodeId'], files=[str(book)])

            async def settled(page_index, step_index):
                page = pages[page_index]
                await until(f'''(() => {{const s=__panelview.state,g=s.guided;
                  return s.page==={page_index} && s.panel==={step_index}
                    && g?.img.isConnected && g.viewport.isConnected && g.img.complete
                    && g.img.naturalWidth==={page['width']} && g.img.naturalHeight==={page['height']}
                    && g.img.src===s.urls[s.page] && g.rects===s.panelCache[s.page]
                    && g.img.getBoundingClientRect().width>0;}})()''')
                # Observe normal CSS animations; never finish, disable or accelerate them.
                # Two RAFs let the browser commit a newly scheduled camera transition.
                observed_animations = await evaluate('''(async()=>{const g=__panelview.state.guided;
                  await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
                  const animations=g.canvas.getAnimations({subtree:true});
                  const observed=animations.map(a=>({target:a.effect.target.className,
                    property:a.transitionProperty,duration:a.effect.getTiming().duration}));
                  await Promise.all(animations.map(a=>a.finished));
                  await new Promise(requestAnimationFrame);return observed;})()''')
                snapshot = await evaluate('''(()=>{const s=__panelview.state,g=s.guided,r=g.rects[s.panel];
                  const im=g.img.getBoundingClientRect(),v=g.viewport.getBoundingClientRect(),z=im.width/g.img.naturalWidth;
                  const t={left:im.left+r.x*z,top:im.top+r.y*z,right:im.left+(r.x+r.width)*z,bottom:im.top+(r.y+r.height)*z};
                  const style=getComputedStyle(g.img);
                  return {page:s.page,step:s.panel,stepCount:g.rects.length,rect:r,
                    connected:g.img.isConnected&&g.viewport.isConnected,
                    sourceBound:g.img.src===s.urls[s.page]&&g.rects===s.panelCache[s.page],
                    visible:!document.querySelector('#reader').hidden&&style.visibility==='visible'&&+style.opacity>0,
                    image:[g.img.naturalWidth,g.img.naturalHeight],target:t,
                    animations:g.canvas.getAnimations({subtree:true}).filter(a=>a.playState==='running'||a.pending).length,
                    camera_transform:getComputedStyle(g.canvas).transform,
                    mask_clip_path:getComputedStyle(g.dim).clipPath,
                    urls:s.urls.filter(u=>typeof u==='string').length,
                    pendingURLs:s.urls.filter(u=>u&&typeof u!=='string').length,
                    panelCaches:s.panelCache.filter(Boolean).length,
                    contained:t.left>=v.left-1&&t.top>=v.top-1&&t.right<=v.right+1&&t.bottom<=v.bottom+1,
                    centered:Math.abs((t.left+t.right-v.left-v.right)/2)<=2&&Math.abs((t.top+t.bottom-v.top-v.bottom)/2)<=2};})()''')
                expected = page['steps'][step_index]
                snapshot['observed_animations'] = observed_animations
                assert snapshot['page'] == page_index and snapshot['step'] == step_index, snapshot
                assert snapshot['stepCount'] == len(page['steps']), snapshot
                assert snapshot['image'] == [page['width'], page['height']], snapshot
                assert all(abs(snapshot['rect'][key]-value) < .001 for key,value in expected.items()), (expected,snapshot)
                assert bool(snapshot['rect'].get('overview')) == (step_index == 0), snapshot
                assert all(snapshot[key] for key in ('connected','sourceBound','visible','contained','centered')), snapshot
                assert snapshot['animations'] == 0, snapshot
                assert snapshot['target']['right'] > snapshot['target']['left'] and snapshot['target']['bottom'] > snapshot['target']['top']
                return snapshot

            async def close_and_check(label):
                await evaluate('window.__traversalURLs=__panelview.state.urls.filter(u=>typeof u==="string")')
                box = await evaluate('''(()=>{const b=document.querySelector('#btn-close'),r=b.getBoundingClientRect();
                  return {x:r.x+r.width/2,y:r.y+r.height/2};})()''')
                await click(**box)
                await until('__panelview.state.book===null && __panelview.state.urls.length===0 && __panelview.state.guided===null')
                cleanup = await evaluate('''(async()=>{const urls=window.__traversalURLs;
                  const retained=await Promise.all(urls.map(u=>fetch(u).then(()=>true,()=>false)));
                  delete window.__traversalURLs;
                  return {urls_checked:urls.length,still_fetchable:retained.filter(Boolean).length,
                    state_urls:__panelview.state.urls.length,thumb_nodes:document.querySelector('#thumbs').children.length};})()''')
                assert cleanup['still_fetchable'] == cleanup['state_urls'] == cleanup['thumb_nodes'] == 0, cleanup
                cleanup['heap'] = await command('Runtime.getHeapUsage')
                result[label] = cleanup

            try:
                await command('Runtime.enable'); await command('Page.enable')
                await command('Emulation.setDeviceMetricsOverride', width=390, height=844, deviceScaleFactor=1, mobile=True)
                await command('Page.navigate', url=sys.argv[3].rstrip('/')+'/')
                await until('!!window.__panelview'); await evaluate('localStorage.clear()')
                build = json.load(urllib.request.urlopen(sys.argv[3].rstrip('/')+'/build.json'))
                assert build['assets'] == expected_build, build
                result['reader_build'] = build
                started = time.monotonic(); await load_file()
                await until(f'__panelview.state.book?.pages.length==={len(pages)} && !!__panelview.state.guided')
                actual_direction = await evaluate('__panelview.state.readingDirection')
                assert actual_direction == direction, (direction, actual_direction)
                result['reading_direction'] = actual_direction
                x = 30 if direction == 'rtl' else 350
                for page_index,page in enumerate(pages):
                    for step_index in range(len(page['steps'])):
                        step_started = time.monotonic()
                        if result['checked_steps']: await click(x, 400)
                        snapshot = await settled(page_index, step_index)
                        snapshot['elapsed_seconds'] = time.monotonic()-started
                        snapshot['navigation_settled_seconds'] = time.monotonic()-step_started
                        if not result['checked_steps']:
                            result['cold_open_settled_seconds'] = time.monotonic()-started
                        if step_index == 0:
                            image_hash = await evaluate('''(async()=>{const u=__panelview.state.guided.img.src;
                              const bytes=await (await fetch(u)).arrayBuffer();
                              return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(v=>v.toString(16).padStart(2,'0')).join('');})()''')
                            assert image_hash == page['image_bytes_sha256'], (page_index,image_hash)
                            snapshot['image_bytes_sha256'] = image_hash
                        stream.write(json.dumps(snapshot)+'\n'); stream.flush()
                        result['checked_steps'] += 1
                        if page_index in selected_pages and step_index in {0,len(page['steps'])-1}:
                            await screenshot(f'page-{page_index+1:03}-step-{step_index:03}')
                    result['page_metrics'].append({'page':page_index,'urls':snapshot['urls'],
                        'pending_urls':snapshot['pendingURLs'],'panel_caches':snapshot['panelCaches'],
                        'elapsed_seconds':time.monotonic()-started,'heap':await command('Runtime.getHeapUsage')})
                    print('PAGE',page_index+1,'/',len(pages),'steps',result['checked_steps'],'/',expected_steps,
                          'URLs',snapshot['urls'],'seconds',round(time.monotonic()-started,2),flush=True)
                await click(x,400); await asyncio.sleep(.1)
                await settled(len(pages)-1,len(pages[-1]['steps'])-1)
                result['end_boundary_passed'] = True
                result['traversal_seconds'] = time.monotonic()-started
                await close_and_check('close_cleanup')
                await load_file(); await settled(len(pages)-1,len(pages[-1]['steps'])-1)
                result['resume_last_step_passed'] = True
                await screenshot('resumed-final-step')
                await close_and_check('reopened_close_cleanup')
                result['archive_unchanged'] = hashlib.file_digest(book.open('rb'),'sha256').hexdigest() == archive_sha
                assert result['archive_unchanged'] and not errors, errors
                assert result['checked_steps'] == expected_steps
                result['complete'] = True
                print('PASS all pages/steps, end, all cached URL revocations, and persisted resume',flush=True)
            except BaseException as error:
                result['failure'] = {'type':type(error).__name__,'message':str(error)}
                try: await screenshot('failure')
                except BaseException as capture_error: result['failure_screenshot_error'] = str(capture_error)
                raise
            finally:
                result['uncaught_exceptions'] = errors
                (output/'results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__ == '__main__':
    asyncio.run(main())
