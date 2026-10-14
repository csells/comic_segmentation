"""Exercise the actual candidate importer on equivalent RAR/ZIP/folder pixels.

Run in the disposable VM only. No inference or budget ledger is used.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('candidate_source', type=Path)
    args = parser.parse_args()
    root, candidate = args.root.resolve(), args.candidate_source.resolve()
    if (root / 'import-validation.json').exists():
        raise FileExistsError('import validation already complete')
    sys.path.insert(0, str(candidate / 'panel_quality_probe'))
    from auto_convert import Client, prepare_input
    fixture = json.loads((root / 'fixture-manifest.json').read_text())
    expected = [(row['name'], row['sha256'], *row['size']) for row in fixture['source_pages']]
    sources = {'cbr': Path(fixture['rar']['path']),
               'cbz': Path(fixture['equivalent_cbz']['path']),
               'folder': Path(fixture['source_folder'])}
    before = {str(path): sha(path) for path in root.joinpath('source-pages').iterdir()}
    before.update({str(path): sha(path) for path in sources.values() if path.is_file()})
    cases = []
    with patch.object(Client, 'http', side_effect=AssertionError('HTTP dispatch forbidden in import parity')) as http:
        for label, source in sources.items():
            work = root / ('candidate-import-' + label)
            result = prepare_input(source, work, None)
            actual = [(row['locator'], row['sha256'], row['width'], row['height']) for row in result['pages']]
            if actual != expected: raise AssertionError(f'{label} page order/hash/dimensions changed')
            for row in result['pages']:
                if sha(work / 'pages' / row['image']) != row['sha256']:
                    raise AssertionError('prepared image differs from manifest')
            if sha(work / 'pages/source-auxiliary/notes.txt') != before[str(sources['folder'] / 'notes.txt')]:
                raise AssertionError('auxiliary content changed')
            # Resume must return the same completed import without rewriting bytes.
            if prepare_input(source, work, None) != result:
                raise AssertionError('resumed import changed')
            cases.append({'input_kind': label, 'source': str(source), 'work': str(work),
                          'pages': actual, 'auxiliary_preserved': True, 'resume_identical': True})
            print(f'PASS {label}: three page hashes/order/dimensions, auxiliary and resume', flush=True)
        negative_work = root / 'candidate-import-symlink-rejection'
        try:
            prepare_input(Path(fixture['negative_fixture']['path']), negative_work, None)
        except ValueError as error:
            if 'nonregular RAR member' not in str(error): raise
            rejection = str(error)
        else:
            raise AssertionError('RAR symlink accepted')
        if any(p.is_symlink() for p in negative_work.rglob('*')):
            raise AssertionError('negative input created a symlink')
        if (negative_work / 'input.json').exists():
            raise AssertionError('rejected archive was marked prepared')
        if http.call_count: raise AssertionError('import attempted provider HTTP')
    if any(sha(path) != expected_hash for path, expected_hash in before.items()):
        raise AssertionError('original inputs changed')
    result = {'completed_at': datetime.now(timezone.utc).isoformat(), 'cases': cases,
              'source_code_sha256': {str(p.relative_to(candidate)): sha(p) for p in (
                  candidate / 'panel_quality_probe/auto_convert.py',
                  candidate / 'panel_quality_probe/import_format.py',
                  candidate / 'comic_panel_e2e/adapter.py')},
              'negative_case': {'reason': rejection, 'no_symlink_created': True,
                                'no_prepared_manifest': True},
              'original_inputs_unchanged': True, 'http_dispatches': 0,
              'scope': 'Actual import parity only. Automatic detector/quality and reader not exercised.'}
    (root / 'import-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
