"""Cache-only V63 oracle over a page list in ONE run directory (ordinals match a multi-page run).

Usage: v63_replay_run.py LEDGER_COPY OUTPUT PAGES TITLE
"""
import io, socket, sys, urllib.request
from pathlib import Path
SOURCE = Path('/home/tester/comic-reader/evidence/candidate-v63-first-pass-cost-20261014/source')
ledger, out, pages, title = sys.argv[1:5]
sys.path.insert(0, str(SOURCE / 'panel_quality_probe'))
sys.dont_write_bytecode = True
import auto_convert as app


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
sys.argv = ['auto_convert.py', '/home/tester/comic-reader/source.pdf', out, '--ledger', ledger, '--render-cache',
            '/home/tester/comic-reader/replay-local/replay.json', '--pages', pages, '--reading-direction', 'ltr', '--title', title,
            '--execute-approved', '--page-cap-usd', '0.50', '--auto-transient-recovery']
sys.stdin = io.StringIO('sk-cache-only-no-provider-credential-0000000000\n')
app.main()
