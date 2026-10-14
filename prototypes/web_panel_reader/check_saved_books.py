"""Drive the staged real-book gallery; keep private screenshots outside Git.

Usage: python3 check_saved_books.py EVIDENCE_DIRECTORY [SITE_BASE_URL]
Requires a task-owned VM Chromium CDP endpoint on loopback 9222.
"""
import asyncio
import base64
import json
from pathlib import Path
import sys
import urllib.request
import websockets

async def main():
    out=Path(sys.argv[1]);out.mkdir(exist_ok=False)
    base=sys.argv[2] if len(sys.argv)>2 else 'http://127.0.0.1:8081'
    tabs=json.load(urllib.request.urlopen('http://127.0.0.1:9222/json'))
    tab=next(t for t in tabs if t['type']=='page')
    results=[]; errors=[];seq=0; loaded=set()
    async with websockets.connect(tab['webSocketDebuggerUrl'],max_size=16*1024*1024) as ws:
        async def cmd(method,**params):
            nonlocal seq
            seq+=1;await ws.send(json.dumps({'id':seq,'method':method,'params':params}))
            async with asyncio.timeout(45):
                while True:
                    r=json.loads(await ws.recv())
                    if r.get('method')=='Runtime.exceptionThrown':errors.append(r['params'])
                    if r.get('method')=='Page.lifecycleEvent' and r['params']['name']=='load':
                        loaded.add(r['params']['loaderId'])
                    if r.get('id')==seq:
                        if 'error' in r:raise RuntimeError(r['error'])
                        return r.get('result',{})
        async def ev(code):
            r=await cmd('Runtime.evaluate',expression=code,returnByValue=True,awaitPromise=True)
            if 'exceptionDetails' in r:raise RuntimeError(r['exceptionDetails'])
            return r['result'].get('value')
        async def check(name,code):
            async with asyncio.timeout(60):
                while not await ev(code):await asyncio.sleep(.15)
            results.append({'check':name,'passed':True});print('PASS',name,flush=True)
        async def shot(name):
            await asyncio.sleep(.9)
            r=await cmd('Page.captureScreenshot',format='png')
            (out/(name+'.png')).write_bytes(base64.b64decode(r['data']))
        async def next_panel():
            await cmd('Input.dispatchMouseEvent',type='mousePressed',x=350,y=400,button='left',clickCount=1)
            await cmd('Input.dispatchMouseEvent',type='mouseReleased',x=350,y=400,button='left',clickCount=1)
        await cmd('Runtime.enable');await cmd('Page.enable')
        await cmd('Page.setLifecycleEventsEnabled',enabled=True)
        await cmd('Emulation.setDeviceMetricsOverride',width=390,height=844,deviceScaleFactor=1,mobile=True)
        navigation=await cmd('Page.navigate',url=base+'/')
        async with asyncio.timeout(30):
            while navigation.get('loaderId') not in loaded:
                await ev('document.readyState');await asyncio.sleep(.1)
        # A navigation to the current URL may reuse the prior document itself.
        # Exercise the user's normal refresh after a staging update (cache on).
        await cmd('Page.reload',ignoreCache=False)
        await check('two labeled saved experiments',"document.querySelectorAll('#book-list button').length===2")
        await ev('localStorage.clear()');await shot('01-gallery')
        await ev('document.querySelector(\'[data-book="gemini"]\').click()')
        await check('Gemini CBZ opens four pages and eight saved frames',"__panelview.state.book?.pages.length===4 && __panelview.state.book.pages.reduce((n,p)=>n+p.panels.length,0)===8 && !!__panelview.state.guided")
        await shot('02-gemini-cover')
        await next_panel();await check('source page 3 retained', '__panelview.state.page===1 && !!__panelview.state.guided')
        await next_panel();await check('source page 5 whole-page fallback retained','__panelview.state.page===2 && __panelview.state.guided?.rects.length===1 && __panelview.state.guided.rects[0].width===1027')
        await shot('03-gemini-fallback')
        await next_panel();await check('source page 25 overview before five recorded regions','__panelview.state.page===3 && __panelview.state.guided?.rects.length===6 && __panelview.state.panel===0 && __panelview.state.guided.rects[0].overview===true')
        await shot('04-gemini-page25-first')
        for i in range(1,6):
            await next_panel();await check(f'page25 metadata region {i}',f'__panelview.state.page===3 && __panelview.state.panel==={i}')
        await check('known merged bottom region unchanged','__panelview.state.guided.rects[5].y===972 && __panelview.state.guided.rects[5].width===1026')
        await shot('05-gemini-merged-bottom')
        await ev('document.querySelector(\'[data-mode="page"]\').click()')
        await check('whole page 25 remains available',"__panelview.state.mode==='page' && document.querySelector('#stage img')?.naturalWidth===1027")
        await shot('06-gemini-page25-whole')
        await ev('document.querySelector(\'[data-mode="guided"]\').click()')
        await check('entering Panels starts at page overview',"__panelview.state.mode==='guided' && __panelview.state.panel===0 && __panelview.state.guided?.rects[0].overview===true")
        await ev("document.querySelector('#btn-close').click()")
        await ev('document.querySelector(\'[data-book="local"]\').click()')
        await check('full CBZ opens 257 pages and 1094 saved frames',"__panelview.state.book?.pages.length===257 && __panelview.state.book.pages.reduce((n,p)=>n+p.panels.length,0)===1094 && !!__panelview.state.guided")
        await shot('07-full-book-cover')
        await next_panel();await check('full book navigates first body page overview','__panelview.state.page===1 && __panelview.state.guided?.rects.length===4 && __panelview.state.panel===0')
        await shot('08-full-book-body')
        await ev('document.querySelector(\'[data-mode="page"]\').click()')
        await check('full book page mode',"__panelview.state.mode==='page' && document.querySelector('#stage img')?.naturalWidth===1128")
        await shot('09-full-book-page')
        assert not errors,errors
        results.append({'check':'uncaught browser exceptions','count':len(errors)})
        (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Saved reader acceptance and private screenshots:',out)

asyncio.run(main())
