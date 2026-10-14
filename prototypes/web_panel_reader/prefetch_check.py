"""Rendered prefetch lifecycle regression checks.

Run in the disposable browser VM:
  python prefetch_check.py CDP_URL EVIDENCE_DIRECTORY SITE_URL
The test controls synthetic asynchronous page loads inside the actual built reader.
"""
import asyncio,json,urllib.request,pathlib,base64,sys
import websockets
r=pathlib.Path(sys.argv[2]);r.mkdir(exist_ok=False)
async def main():
 tab=next(t for t in json.load(urllib.request.urlopen(sys.argv[1]+'/json')) if t['type']=='page');counter=0;errors=[]
 async with websockets.connect(tab['webSocketDebuggerUrl']) as ws:
  async def cmd(method,**params):
   nonlocal counter
   counter+=1;await ws.send(json.dumps({'id':counter,'method':method,'params':params}))
   async with asyncio.timeout(30):
    while True:
     v=json.loads(await ws.recv())
     if v.get('method')=='Runtime.exceptionThrown':errors.append(v['params'])
     if v.get('id')==counter:
      assert 'error' not in v,v
      return v.get('result',{})
  async def ev(s):
   v=await cmd('Runtime.evaluate',expression=s,awaitPromise=True,returnByValue=True);assert 'exceptionDetails' not in v,v
   return v['result'].get('value')
  await cmd('Runtime.enable');await cmd('Page.enable');await cmd('Emulation.setDeviceMetricsOverride',width=390,height=844,deviceScaleFactor=1,mobile=True);await cmd('Page.navigate',url=sys.argv[3].rstrip('/')+'/')
  for _ in range(100):
   if await ev('!!window.__panelview'):break
   await asyncio.sleep(.1)
  result=await ev('''(async()=>{
    localStorage.clear();
    const moduleURL=performance.getEntriesByType('resource').find(x=>x.name.includes('/reader.js?v=')).name;
    const reader=await import(moduleURL);if(reader.state!==__panelview.state)throw Error('Wrong reader module');
    const checks=[],delay=ms=>new Promise(resolve=>setTimeout(resolve,ms)),assert=(ok,s)=>{if(!ok)throw Error(s)};
    const c=document.createElement('canvas');c.width=100;c.height=150;const ctx=c.getContext('2d');ctx.fillStyle='red';ctx.fillRect(0,0,100,70);ctx.fillStyle='blue';ctx.fillRect(0,80,100,70);const blob=await new Promise(resolve=>c.toBlob(resolve));
    const page=(get,panels)=>({path:'test.png',srcW:100,srcH:150,get,panels}),whole=[{x:0,y:0,width:100,height:150}],two=[{x:0,y:0,width:100,height:70},{x:0,y:80,width:100,height:70}];
    const book=(name,pages)=>({title:name,resumeId:name,comicSol:true,pages});
    const defer=()=>{let release,reject;return {promise:new Promise((ok,no)=>{release=ok;reject=no}),resolve:b=>release(b),reject:e=>reject(e)}};
    async function validNext(name){await reader.jumpToPage(1);await delay(1000);const g=reader.state.guided,rect=g.rects[0],im=g.img.getBoundingClientRect();assert(rect.width===100&&rect.height===150&&im.width>300&&g.img.isConnected,name+' wrong replacement geometry');checks.push({name,rect,bounds:[im.x,im.y,im.width,im.height]})}
    let pending=defer(),entered=false;
    const A=book('old-A',[page(()=>Promise.resolve(blob),whole),page(()=>{entered=true;return pending.promise},whole)]);
    const B=book('new-B',[page(()=>Promise.resolve(blob),two),page(()=>Promise.resolve(blob),whole)]);
    await reader.openBook(A);assert(entered,'A prefetch never started');await reader.openBook(B);pending.resolve(blob);await delay(100);assert(!reader.state.panelCache[1],'Stale old-book prefetch poisoned B cache');await validNext('different-book lifecycle');
    let first=defer(),second=defer(),calls=0;
    const same=book('same-object',[page(()=>Promise.resolve(blob),whole),page(()=>++calls===1?first.promise:second.promise,whole)]);
    await reader.openBook(same);await reader.openBook(same);assert(calls===2,'New lifecycle did not own new pending load');first.resolve(blob);await delay(100);assert(!reader.state.panelCache[1],'Old lifecycle poisoned reopened same object');second.resolve(blob);await delay(100);await validNext('same-book-object reopen lifecycle');
    pending=defer();
    const staleReject=book('stale-extraction',[page(()=>Promise.resolve(blob),whole),page(()=>pending.promise,whole)]);
    const afterReject=book('after-rejection',[page(()=>Promise.resolve(blob),two),page(()=>Promise.resolve(blob),whole)]);
    await reader.openBook(staleReject);await reader.openBook(afterReject);pending.reject(Error('controlled old extraction failure'));await delay(100);assert(reader.state.book===afterReject&&!reader.state.panelCache[1],'Stale extraction rejection affected current reader');checks.push({name:'stale extraction rejection is ignored',passed:true});
    const bad=book('bad-prefetch',[page(()=>Promise.resolve(blob),whole),page(()=>Promise.resolve(new Blob(['invalid image'],{type:'image/png'})),whole)]);
    await reader.openBook(bad);await delay(100);assert(!reader.state.panelCache[1],'Failed decode cached zero geometry');assert(reader.state.book===bad,'Failed background decode closed the current book');checks.push({name:'failed decode leaves panel cache empty',passed:true});
    pending=defer();let decodeCalls=0;const original=Image.prototype.decode;
    Image.prototype.decode=function(){++decodeCalls;return original.call(this)};
    try {
      const many=book('coalescing',[page(()=>Promise.resolve(blob),whole),page(()=>pending.promise,whole)]);
      await reader.openBook(many);const before=decodeCalls;for(let i=0;i<8;++i)reader.frameCurrentPanel(false);pending.resolve(blob);await delay(150);assert(decodeCalls-before===1,'Repeated prefetch produced '+(decodeCalls-before)+' decodes');checks.push({name:'repeated framing coalesces next-page decode',decodes:decodeCalls-before});
      await validNext('coalesced prefetch retains valid geometry');
    } finally {Image.prototype.decode=original}
    assert(!document.querySelector('#error').innerText,'Visible unexpected error');
    let getFailures=0;const getBad=book('current-get-failure',[page(()=>Promise.resolve(blob),whole),page(()=>{++getFailures;return Promise.reject(Error('controlled demand extraction failure'))},whole)]);
    await reader.openBook(getBad);await delay(100);assert(reader.state.book===getBad&&!reader.state.panelCache[1]&&reader.state.guided.img.isConnected,'Speculative extraction failure damaged current view');checks.push({name:'current speculative extraction failure preserves current view',calls:getFailures});
    reader.stage.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:350,clientY:400}));await delay(100);assert(getFailures>=2&&!reader.state.book&&document.querySelector('#error').innerText.includes('controlled demand extraction failure'),'Explicit next navigation did not retry/report failure');checks.push({name:'explicit next retries extraction and shows normal error',calls:getFailures,error:document.querySelector('#error').innerText});
    return {moduleURL,checks};
  })()''')
  (r/'results.json').write_text(json.dumps({'result':result,'uncaught_exceptions':errors},indent=2));shot=await cmd('Page.captureScreenshot',format='png');(r/'replacement-page.png').write_bytes(base64.b64decode(shot['data']));assert len(result['checks'])==8 and not errors;print(json.dumps(result,indent=2),flush=True)
asyncio.run(main())
