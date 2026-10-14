"""Bound a full traversal inside the disposable browser VM; no host runtime.

Usage: traversal_run.py LABEL OUTPUT SITE_URL CBZ [--max-seconds 3600]
Chrome RSS is the sum over owned processes, not physical memory footprint.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import urllib.request

import websockets


ROOT = Path('/Users/admin/comic-browser')
CHROME = ROOT/'Google Chrome.app/Contents/MacOS/Google Chrome'


def process_sample():
    rows = []
    for line in subprocess.check_output(['ps','-axo','pid=,ppid=,rss=,command='],text=True).splitlines():
        fields = line.strip().split(None,3)
        if len(fields) == 4 and str(ROOT/'Google Chrome.app')+'/' in fields[3]:
            rows.append({'pid':int(fields[0]),'ppid':int(fields[1]),'rss_kib':int(fields[2])})
    return rows


async def close_browser():
    version = json.load(urllib.request.urlopen('http://127.0.0.1:9222/json/version',timeout=3))
    async with websockets.connect(version['webSocketDebuggerUrl']) as ws:
        await ws.send(json.dumps({'id':1,'method':'Browser.close'}))
        try:
            async with asyncio.timeout(5):
                while json.loads(await ws.recv()).get('id') != 1: pass
        except websockets.exceptions.ConnectionClosed: pass


def finish_owned_processes():
    evidence = {'samples': [], 'signals': []}
    for kind in (None, signal.SIGTERM, signal.SIGKILL):
        remaining = process_sample()
        if kind is not None:
            for row in remaining:
                # Recheck ownership immediately before signalling a potentially reused PID.
                if row['pid'] in {item['pid'] for item in process_sample()}:
                    try: os.kill(row['pid'], kind)
                    except ProcessLookupError: continue
                    evidence['signals'].append({'pid': row['pid'], 'signal': kind.name})
        for _ in range(15):
            remaining = process_sample(); evidence['samples'].append(remaining)
            if not remaining:
                evidence['remaining'] = []; return evidence
            time.sleep(.2)
    evidence['remaining'] = remaining
    return evidence


def main():
    assert Path.home() == Path('/Users/admin') and CHROME.is_file(), 'Disposable browser guest only'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('label'); parser.add_argument('output'); parser.add_argument('site'); parser.add_argument('cbz')
    parser.add_argument('--max-seconds',type=int,default=3600)
    parser.add_argument('--expected-direction',choices=('ltr','rtl'),required=True)
    args = parser.parse_args()
    assert re.fullmatch('[a-z0-9-]+',args.label) and 10 <= args.max_seconds <= 7200
    assert not process_sample(), 'Owned browser runtime must be idle'
    logs = ROOT/args.label; logs.mkdir(exist_ok=False)
    command = [str(CHROME),'--headless=new','--remote-debugging-address=127.0.0.1',
        '--remote-debugging-port=9222','--user-data-dir='+str(logs/'profile'),
        '--no-first-run','--no-default-browser-check','--disable-background-networking',
        '--disable-component-update','--disable-sync','--disable-default-apps','about:blank']
    with (logs/'chrome.log').open('xb') as log:
        browser = subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    (logs/'process.json').write_text(json.dumps({'pid':browser.pid,'command':command},indent=2)+'\n')
    samples = []; stop = None; harness = None; code = None; start = time.monotonic()
    try:
        for _ in range(30):
            assert browser.poll() is None, 'Chrome exited before readiness'
            try:
                version = json.load(urllib.request.urlopen('http://127.0.0.1:9222/json/version',timeout=1)); break
            except OSError: time.sleep(1)
        else: raise RuntimeError('CDP not ready')
        (logs/'version.json').write_text(json.dumps(version,indent=2)+'\n')
        print('Browser',version['Browser'],flush=True)
        start = time.monotonic(); offset = 0
        with (logs/'check.log').open('xb') as log:
            harness = subprocess.Popen([str(ROOT/'venv/bin/python'),'-u',str(Path(__file__).with_name('traversal_check.py')),
                'http://127.0.0.1:9222',args.output,args.site,args.cbz,'e5a769ca768d395e',args.expected_direction],stdout=log,stderr=subprocess.STDOUT)
            with (logs/'rss.jsonl').open('x') as memory:
                while True:
                    processes = process_sample(); total = sum(row['rss_kib'] for row in processes)*1024
                    sample = {'seconds':time.monotonic()-start,'aggregate_chrome_rss_bytes':total,'processes':processes}
                    memory.write(json.dumps(sample)+'\n'); memory.flush(); samples.append(total)
                    text = (logs/'check.log').read_text(); fresh = text[offset:]; offset = len(text)
                    if fresh: print(fresh,end='',flush=True)
                    if len(samples)%5 == 1:
                        print('Progress',round(sample['seconds'],1),'s; aggregate Chrome RSS',round(total/1024**2,1),'MiB',flush=True)
                    if total > 4*1024**3: stop = 'Aggregate Chrome RSS exceeded4GiB'
                    if sample['seconds'] > args.max_seconds: stop = 'Traversal exceeded time bound'
                    if stop:
                        harness.terminate(); break
                    if harness.poll() is not None: break
                    time.sleep(1)
            code = harness.wait(timeout=10)
        text = (logs/'check.log').read_text()[offset:]
        if text: print(text,end='',flush=True)
    finally:
        if harness is not None and harness.poll() is None:
            harness.terminate()
            try: harness.wait(timeout=10)
            except subprocess.TimeoutExpired: harness.kill(); harness.wait(timeout=5)
        closed = {'pid':browser.pid}
        try: asyncio.run(close_browser()); closed['method'] = 'CDP Browser.close'
        except BaseException as error:
            closed['close_error'] = str(error); browser.terminate(); closed['method'] = 'Owned process terminate'
        try: browser.wait(timeout=10)
        except subprocess.TimeoutExpired: browser.kill(); browser.wait(timeout=5); closed['method'] = 'Owned process kill'
        closed['exit_code'] = browser.returncode
        closed['owned_process_cleanup'] = finish_owned_processes()
        closed['all_owned_processes_exited'] = not closed['owned_process_cleanup']['remaining']
        if not closed['all_owned_processes_exited']:
            stop = (stop+'; ' if stop else '')+'Owned Chrome processes remained after bounded cleanup'
        (logs/'closed.json').write_text(json.dumps(closed,indent=2)+'\n')
        (logs/'run.json').write_text(json.dumps({'exit_code':code,'stop_reason':stop,
            'seconds':time.monotonic()-start,'time_bound_seconds':args.max_seconds,
            'rss_bound_bytes':4*1024**3,'max_aggregate_chrome_rss_bytes':max(samples,default=0),
            'sample_interval_seconds':1,'memory_scope':'Sum of process RSS; shared mappings may double-count; not physical phone footprint'},indent=2)+'\n')
        print('Owned browser closed;',code,stop,flush=True)
    if stop: raise RuntimeError(stop)
    assert code == 0, f'Traversal harness exited {code}'


if __name__ == '__main__': main()
