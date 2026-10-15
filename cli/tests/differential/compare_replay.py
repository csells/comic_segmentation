"""Compare prototype and Rust page records from per-page replay directories.

Usage: compare_replay.py PYTHON_ROOT RUST_ROOT [PAGES]
Paths are normalized to their run roots; completeness proof file references are
compared structurally (their names hash implementation-specific configuration).
"""
import json, re, sys
from pathlib import Path
py_root, rs_root = Path(sys.argv[1]), Path(sys.argv[2])
pages = [int(v) for v in sys.argv[3].split(',')] if len(sys.argv) > 3 else sorted(int(p.name[1:]) for p in py_root.glob('p[0-9]*'))
HEX = re.compile(r'^[0-9a-f]{64}$')


def normalize(value, root):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k == 'proof' and isinstance(v, dict) and set(v) == {'path', 'sha256'}:
                out[k] = {'path': '<proof>', 'sha256': '<proof>'}
            elif k in ('completeness_rejection_proof',) and isinstance(v, dict):
                out[k] = '<proof>'
            elif k == 'analysis_source_sha256' or k == 'source_sha256':
                out[k] = v
            else:
                out[k] = normalize(v, root)
        return out
    if isinstance(value, list):
        return [normalize(v, root) for v in value]
    if isinstance(value, str):
        return value.replace(str(root), '<run>')
    return value


def first_diff(a, b, path='$'):
    if type(a) is not type(b):
        return path, a, b
    if isinstance(a, dict):
        for k in list(a) + [k for k in b if k not in a]:
            if k not in a or k not in b:
                return f'{path}.{k}', a.get(k, '<missing>'), b.get(k, '<missing>')
            d = first_diff(a[k], b[k], f'{path}.{k}')
            if d: return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f'{path}[len]', len(a), len(b)
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_diff(x, y, f'{path}[{i}]')
            if d: return d
        return None
    return None if a == b else (path, a, b)


summary = {'identical': [], 'different': [], 'python_blocked': [], 'rust_blocked': [], 'missing': []}
for page in pages:
    py, rs = py_root / f'p{page:03d}', rs_root / f'p{page:03d}'
    pb, rb = sorted(py.glob('blocked-*.json')), sorted(rs.glob('blocked-*.json'))
    pp, rp = py / 'page-0001.json', rs / 'page-0001.json'
    if pb or rb:
        if pb: summary['python_blocked'].append(page)
        if rb: summary['rust_blocked'].append(page)
        if pb and rb:
            a = json.loads(pb[-1].read_text()); b = json.loads(rb[-1].read_text())
            if normalize(a, py) != normalize(b, rs):
                print(f'p{page}: both blocked, records differ: {first_diff(normalize(a, py), normalize(b, rs))}')
        continue
    if not pp.exists() or not rp.exists():
        summary['missing'].append(page); continue
    a, b = normalize(json.loads(pp.read_text()), py), normalize(json.loads(rp.read_text()), rs)
    if a == b:
        summary['identical'].append(page)
    else:
        summary['different'].append(page)
        print(f'p{page}: {first_diff(a, b)}')
print(json.dumps({k: (v if k != 'identical' else len(v)) for k, v in summary.items()}))
