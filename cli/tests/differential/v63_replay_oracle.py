"""Cache-only V63 oracle on the prototype staging VM: never reserves or connects.

Usage: v63_replay_oracle.py LEDGER_COPY OUT_ROOT PAGES
Runs the frozen V63 prototype once per source page (output OUT_ROOT/pNNN) with
the exact first-pass options of the V63 full run. A cache miss blocks only that page.
"""
import io, socket, sys, urllib.request
from pathlib import Path
SOURCE = Path('/home/tester/comic-reader/evidence/candidate-v63-first-pass-cost-20261014/source')
PDF = Path('/home/tester/comic-reader/source.pdf')
RENDER = Path('/home/tester/comic-reader/replay-local/replay.json')
ledger, out_root, pages = sys.argv[1], Path(sys.argv[2]), [int(v) for v in sys.argv[3].split(',')]
sys.path.insert(0, str(SOURCE / 'panel_quality_probe'))
sys.dont_write_bytecode = True
import auto_convert as app
assert app.POLICY == 'automatic-marked-target-completeness-v63'


class CacheOnlyBudget(app.Budget):
    def __init__(self, path, cap=100000000):
        super().__init__(path, cap=370_000_000)

    def reserve(self, *args, **kwargs):
        raise app.RunBlocked('CACHE_ONLY_MISS: reservations disabled')


def deny_http(_client, _endpoint, _body):
    raise app.RunBlocked('CACHE_ONLY_MISS: HTTP disabled')


def deny_network(*_args, **_kwargs):
    raise AssertionError('Network forbidden')


app.Budget = CacheOnlyBudget
app.Client.http = deny_http
socket.socket.connect = socket.create_connection = urllib.request.urlopen = deny_network
for page in pages:
    out = out_root / f'p{page:03d}'
    if (out / 'page-0001.json').exists() or list(out.glob('blocked-*.json')):
        continue
    sys.argv = ['auto_convert.py', str(PDF), str(out), '--ledger', ledger, '--render-cache', str(RENDER), '--pages', str(page),
                '--reading-direction', 'ltr', '--title', 'V63 replay', '--execute-approved', '--page-cap-usd', '0.50',
                '--auto-transient-recovery']
    sys.stdin = io.StringIO('sk-cache-only-no-provider-credential-0000000000\n')
    try:
        app.main()
        print(f'page {page}: completed', flush=True)
    except SystemExit as exit_:
        print(f'page {page}: exit {exit_.code}', flush=True)
