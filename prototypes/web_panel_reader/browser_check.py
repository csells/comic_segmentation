"""Rendered acceptance checks. Run in staging with a task-owned CDP browser.

Usage: python3 browser_check.py CDP_URL EVIDENCE_DIRECTORY [SITE_URL] [FIXTURES_DIRECTORY]
Requires Debian python3-websockets. Evidence directory must not exist.
"""
import asyncio
import base64
import json
from pathlib import Path
import sys
import urllib.request
import websockets

async def main():
    out = Path(sys.argv[2]); out.mkdir(exist_ok=False)
    base = sys.argv[3] if len(sys.argv)>3 else 'http://127.0.0.1:8080'
    fixtures = Path(sys.argv[4]) if len(sys.argv)>4 else Path('/home/tester/comic-reader/fixtures')
    tabs = json.load(urllib.request.urlopen(sys.argv[1] + '/json'))
    tab = next(t for t in tabs if t['type'] == 'page')
    counter = 0
    errors = []
    results = []
    async with websockets.connect(tab['webSocketDebuggerUrl'], max_size=16*1024*1024) as ws:
        async def command(method, **params):
            nonlocal counter
            counter += 1
            await ws.send(json.dumps({'id':counter,'method':method,'params':params}))
            async with asyncio.timeout(30):
                while True:
                    data = json.loads(await ws.recv())
                    if data.get('method') == 'Runtime.exceptionThrown': errors.append(data['params'])
                    if data.get('id') == counter:
                        if 'error' in data: raise RuntimeError(data['error'])
                        return data.get('result', {})
        async def evaluate(expression):
            r = await command('Runtime.evaluate', expression=expression, returnByValue=True, awaitPromise=True)
            if 'exceptionDetails' in r: raise RuntimeError(r['exceptionDetails'])
            return r['result'].get('value')
        async def until(expression):
            async with asyncio.timeout(15):
                while not await evaluate(expression): await asyncio.sleep(.1)
        async def shot(name):
            # The renderer animates its camera for 850 ms. State changes precede
            # the visible framing, so capture and measure the settled result.
            if await evaluate('!!window.__panelview?.state.guided'):
                await until('''(() => {const s=__panelview.state,g=s.guided;
                  return g?.img.isConnected && g.viewport.isConnected
                    && g.img.complete && g.img.naturalWidth>0 && g.img.naturalHeight>0
                    && g.img.getBoundingClientRect().width>0
                    && g.img.src===s.urls[s.page] && g.rects===s.panelCache[s.page];})()''')
            await asyncio.sleep(1)
            framing = await evaluate("""(() => {
              const g = window.__panelview?.state.guided;
              if (!g) return null;
              const r = g.rects[__panelview.state.panel];
              const image = g.img.getBoundingClientRect();
              const viewport = g.viewport.getBoundingClientRect();
              const scale = image.width / g.img.naturalWidth;
              const target = {left:image.left + r.x*scale, top:image.top + r.y*scale,
                right:image.left + (r.x+r.width)*scale,
                bottom:image.top + (r.y+r.height)*scale};
              return {target, rendered:g.img.isConnected && g.viewport.isConnected
                  && g.img.naturalWidth>0 && g.img.naturalHeight>0
                  && g.img.src===__panelview.state.urls[__panelview.state.page]
                  && g.rects===__panelview.state.panelCache[__panelview.state.page]
                  && image.width>0 && image.height>0
                  && viewport.width>0 && viewport.height>0,
                viewport:{left:viewport.left,top:viewport.top,
                right:viewport.right,bottom:viewport.bottom},
                contained:target.left >= viewport.left-1 && target.top >= viewport.top-1
                  && target.right <= viewport.right+1 && target.bottom <= viewport.bottom+1,
                centered:Math.abs((target.left+target.right-viewport.left-viewport.right)/2)<=2
                  && Math.abs((target.top+target.bottom-viewport.top-viewport.bottom)/2)<=2};
            })()""")
            if framing:
                assert framing['rendered'] and framing['contained'] and framing['centered'], {'screenshot':name, **framing}
                results.append({'check':name+' selected frame fits and centers in visible viewport',
                                'passed':True, 'framing':framing})
            r = await command('Page.captureScreenshot', format='png')
            (out / (name+'.png')).write_bytes(base64.b64decode(r['data']))
        async def click(x, y):
            await command('Input.dispatchMouseEvent', type='mousePressed', x=x, y=y, button='left', clickCount=1)
            await command('Input.dispatchMouseEvent', type='mouseReleased', x=x, y=y, button='left', clickCount=1)
        async def check(name, expression):
            await until(expression)
            results.append({'check':name,'passed':True})
        await command('Runtime.enable')
        await command('Page.enable')
        await command('Page.navigate', url=base+'/test-acbf.html')
        await until("document.title === 'PASS' || document.title === 'FAIL'")
        assert await evaluate('document.title') == 'PASS', await evaluate('document.body.innerText')
        results.append({'check':'ACBF browser suite','output':await evaluate('document.body.innerText')})
        await command('Emulation.setDeviceMetricsOverride', width=390, height=844, deviceScaleFactor=1, mobile=True)
        await command('Emulation.setTouchEmulationEnabled', enabled=True)
        await command('Page.navigate', url=base+'/')
        await until('!!window.__panelview')
        await evaluate('localStorage.clear()')
        await shot('01-phone-landing')
        await evaluate("document.querySelector('#btn-demo').click()")
        await check('cover opens guided', "__panelview.state.page===0 && !!__panelview.state.guided")
        await shot('02-cover')
        await click(350,400)
        await check('page overview precedes its panels', '__panelview.state.page===1 && __panelview.state.panel===0 && __panelview.state.guided?.rects[0].width===1000 && __panelview.state.guided.rects[0].height===1500')
        await shot('02b-page-overview')
        await evaluate('document.querySelector("#btn-thumbs").click()')
        await until('!document.querySelector("#thumbs").hidden')
        await shot('02c-overview-with-thumbnails')
        await evaluate('document.querySelector("#btn-thumbs").click()')
        await check('thumbnail close preserves page overview', '__panelview.state.page===1 && __panelview.state.panel===0 && document.querySelector("#thumbs").hidden')
        await shot('02d-overview-after-thumbnails')
        await click(350,400)
        await check('first metadata frame is panel 3', '__panelview.state.page===1 && __panelview.state.panel===1 && __panelview.state.guided?.rects[__panelview.state.panel].x===350')
        await asyncio.sleep(.7)
        await shot('03-panel-3')
        await evaluate('document.querySelector("#btn-thumbs").click()')
        await until('!document.querySelector("#thumbs").hidden')
        await shot('03b-panel-with-thumbnails')
        await evaluate('document.querySelector("#btn-thumbs").click()')
        await check('thumbnail close preserves selected panel', '__panelview.state.page===1 && __panelview.state.panel===1 && document.querySelector("#thumbs").hidden')
        await shot('03c-panel-after-thumbnails')
        await click(350,400)
        await check('next is panel 1', '__panelview.state.panel===2 && __panelview.state.guided.rects[2].y===50')
        await click(30,400)
        await check('previous returns to panel 3', '__panelview.state.page===1 && __panelview.state.panel===1')
        await click(30,400)
        await check('previous first panel returns to overview', '__panelview.state.page===1 && __panelview.state.panel===0')
        await click(350,400)
        await check('overview advances to first panel again', '__panelview.state.panel===1')
        # Actual touch swipe, then a possible synthesized click: must advance only once.
        await command('Input.dispatchTouchEvent', type='touchStart', touchPoints=[{'x':330,'y':400}])
        await command('Input.dispatchTouchEvent', type='touchMove', touchPoints=[{'x':120,'y':402}])
        await command('Input.dispatchTouchEvent', type='touchEnd', touchPoints=[])
        await check('swipe advances one panel', '__panelview.state.panel===2')
        await click(120,402)
        await check('swipe click suppressed', '__panelview.state.panel===2')
        await asyncio.sleep(.75)
        await click(350,400)
        await check('next is panel 4', '__panelview.state.panel===3 && __panelview.state.guided.rects[3].y===950')
        await asyncio.sleep(.7)
        await shot('04-panel-4')
        await click(350,400)
        await check('next is panel 2', '__panelview.state.panel===4 && __panelview.state.guided.rects[4].width===250')
        await command('Emulation.setDeviceMetricsOverride', width=844, height=390, deviceScaleFactor=1, mobile=True)
        await asyncio.sleep(.7)
        await shot('05-landscape-panel-2')
        await command('Emulation.setDeviceMetricsOverride', width=390, height=844, deviceScaleFactor=1, mobile=True)
        await asyncio.sleep(.3)
        await click(350,400)
        await check('adapter fallback is one whole-page step', '__panelview.state.page===2 && __panelview.state.guided?.rects.length===1 && __panelview.state.guided.rects[0].width===1000 && __panelview.state.guided.rects[0].height===1500')
        await shot('06-whole-page-fallback')
        await click(30,400)
        await check('back across page goes to last frame', '__panelview.state.page===1 && __panelview.state.panel===4')
        await evaluate('document.querySelector(\'[data-mode="page"]\').click()')
        await check('page mode preserves full page', "__panelview.state.mode==='page' && !!document.querySelector('#stage img')")
        await asyncio.sleep(.4)  # Wait for the reader's 250 ms page entrance animation.
        await shot('07-page-mode')
        await command('Page.reload')
        await until('!!window.__panelview')
        # A real file input load, independent of hosted demo fetch.
        await evaluate("document.querySelector('#file-input').id='file-input'")
        dom = await command('DOM.getDocument')
        node = await command('DOM.querySelector', nodeId=dom['root']['nodeId'], selector='#file-input')
        await command('DOM.setFileInputFiles', nodeId=node['nodeId'], files=[str(fixtures/'order-control.cbz')])
        await check('local file load and resume', "!!__panelview.state.book && !document.querySelector('#reader').hidden && __panelview.state.page===1 && __panelview.state.mode==='page' && document.querySelector('#stage img')?.naturalWidth===1000")
        await evaluate("document.querySelector('#btn-close').click()")
        await command('DOM.setFileInputFiles', nodeId=node['nodeId'], files=[str(fixtures/'stored-control.cbz')])
        await check('uncompressed adapter CBZ loads', "!!__panelview.state.book && !document.querySelector('#reader').hidden && __panelview.state.page===1 && __panelview.state.mode==='page' && document.querySelector('#stage img')?.naturalWidth===1000")
        await evaluate("document.querySelector('#btn-close').click()")
        await command('DOM.setFileInputFiles', nodeId=node['nodeId'], files=[str(fixtures/'duplicate.cbz')])
        await check('bad CBZ produces visible error', "!document.querySelector('#error').hidden && document.querySelector('#error').textContent.includes('Duplicate') && !__panelview.state.book")
        await shot('08-visible-error')
        await command('DOM.setFileInputFiles', nodeId=node['nodeId'], files=[str(fixtures/'rtl-control.cbz')])
        await check('RTL profile reaches reader state', "!!__panelview.state.book && __panelview.state.readingDirection==='rtl' && __panelview.state.page===0 && !!__panelview.state.guided")
        await click(30,400)
        await check('RTL left tap advances to page overview', '__panelview.state.page===1 && __panelview.state.panel===0')
        await click(30,400)
        await check('RTL preserves first metadata panel', '__panelview.state.page===1 && __panelview.state.panel===1 && __panelview.state.guided.rects[1].x===350')
        await click(350,400)
        await check('RTL right tap returns to overview', '__panelview.state.page===1 && __panelview.state.panel===0')
        await shot('09-rtl-overview')
        await evaluate("document.querySelector('#btn-close').click()")
        await command('DOM.setFileInputFiles', nodeId=node['nodeId'], files=[str(fixtures/'single-control.cbz')])
        await check('single page opens once with overview and all its panels', "__panelview.state.book?.pages.length===1 && __panelview.state.page===0 && __panelview.state.panel===0 && __panelview.state.guided?.rects.length===5")
        for panel in range(1, 5):
            await click(350,400)
            await check(f'single page reaches panel {panel}', f'__panelview.state.page===0 && __panelview.state.panel==={panel}')
        await click(350,400)
        await check('single-page end never invents a second page', '__panelview.state.page===0 && __panelview.state.panel===4 && __panelview.state.book.pages.length===1')
        await shot('10-single-page-last-panel')
        assert not errors, errors
        results.append({'check':'uncaught browser exceptions','count':len(errors)})
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

asyncio.run(main())
