"""Drive the staged real-book gallery; keep private screenshots outside Git.

Usage: python3 check_openai_pilot.py EVIDENCE_DIRECTORY [SITE_BASE_URL] [BOOK_ID] [CATALOG_COUNT] [PANEL_COUNTS_JSON]
Optional counts list excludes the cover; use zero for a whole-page-only composition.
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
    book_id=sys.argv[3] if len(sys.argv)>3 else 'openai-astra-pilot'
    catalog_count=int(sys.argv[4]) if len(sys.argv)>4 else 3
    counts=json.loads(Path(sys.argv[5]).read_text()) if len(sys.argv)>5 else [7,6,4,0]
    assert counts and all(type(n) is int and n >= 0 for n in counts), counts
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
        await check(f'{catalog_count} labeled saved experiments',f"document.querySelectorAll('#book-list button').length==={catalog_count}")
        await ev('localStorage.clear()');await shot('01-gallery')
        await ev(f'document.querySelector({json.dumps("[data-book="+json.dumps(book_id)+"]")}).click()')
        await check(f'book has cover plus {len(counts)} source pages',f"__panelview.state.book?.pages.length==={len(counts)+1} && !!__panelview.state.guided")
        await check('cover retained once','__panelview.state.page===0 && __panelview.state.guided.rects.length===1')
        for page,count in enumerate(counts,1):
            await next_panel()
            await check(f'page {page} overview',f'__panelview.state.page==={page} && __panelview.state.panel===0 && __panelview.state.guided?.rects.length==={count+1}')
            await shot(f'page-{page}-overview')
            for panel in range(1,count+1):
                await next_panel()
                await check(f'page {page} panel {panel}',f'__panelview.state.page==={page} && __panelview.state.panel==={panel}')
                await shot(f'page-{page}-panel-{panel}')
        if counts[-1] == 0:
            await check('final whole page not duplicated','__panelview.state.guided.rects.length===1')
        assert not errors,errors
        results.append({'check':'uncaught browser exceptions','count':len(errors)})
        (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Saved reader acceptance and private screenshots:',out)

asyncio.run(main())
