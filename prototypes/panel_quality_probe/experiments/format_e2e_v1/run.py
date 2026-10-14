"""VM-only actual converter/cache parity; no provider dispatch or invented verdicts."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path('/home/tester/comic-reader')
SOURCE = ROOT / 'candidate-v29/source'
EVIDENCE = ROOT / 'evidence/format-converter-e2e-20261009'
PAGE_COUNTS = (1, 3)
LEDGER = ROOT / 'evidence/gemini-10usd-20261008.jsonl'
RENDER = ROOT / 'replay-local/replay.json'
PDF = ROOT / 'source.pdf'
RAR = ROOT / 'evidence/cbr-validation-20261009/portable/rar/rar'


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def source_hashes():
    return {str(p.relative_to(SOURCE)): sha(p) for p in sorted(SOURCE.rglob('*'))
            if p.is_file() and p.suffix in ('.py', '.txt', '.js', '.json')
            and '__pycache__' not in p.parts}


def inputs(count, root, render):
    folder = root / 'original-images'
    folder.mkdir()
    for item in render['pages'][:count]:
        source = RENDER.parent / 'pages' / item['archive_image']
        assert sha(source) == item['sha256']
        shutil.copyfile(source, folder / item['archive_image'])
    cbz = root / 'same-pages.cbz'
    with zipfile.ZipFile(cbz, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.iterdir()):
            archive.write(path, path.name)
    cbr = root / 'same-pages.cbr'
    command = [str(RAR), 'a', '-ma5', '-m3', '-md1m', '-mt1', '-s-', '-ep1',
               str(cbr), *[p.name for p in sorted(folder.iterdir())]]
    result = subprocess.run(command, cwd=folder, check=True, capture_output=True, text=True)
    (root / 'rar-create.log').write_text(result.stdout + result.stderr)
    save(root / 'rar-command.json', {'argv': command, 'cwd': str(folder), 'archiver_sha256': sha(RAR)})
    assert cbr.read_bytes().startswith(bytes.fromhex('526172211a070100'))
    listing = subprocess.run([str(RAR), 'lt', str(cbr)], check=True, capture_output=True, text=True)
    (root / 'rar-listing.log').write_text(listing.stdout + listing.stderr)
    assert '-m3' in listing.stdout
    return {'pdf': PDF, 'cbz': cbz, 'cbr': cbr, 'folder': folder}


def hashes(path):
    if path.is_file():
        return sha(path)
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def semantics(output):
    complete = sorted(output.glob('completed-*.json'))
    assert len(complete) == 1
    summary = json.loads(complete[0].read_text())
    manifest = json.loads((output / 'book.manifest.json').read_text())
    outcomes = [json.loads((output / f'page-{i:04d}.json').read_text()) for i in range(1, summary['pages'] + 1)]
    archive_path = output / 'automatic-panels.cbz'
    assert sha(archive_path) == summary['output_sha256'] == manifest['output_sha256']
    with zipfile.ZipFile(archive_path) as archive:
        acbf_name, = [n for n in archive.namelist() if n.endswith('.acbf')]
        xml = archive.read(acbf_name)
        profile = json.loads(archive.read('panel-reader.json'))
        assert profile['metadata_sha256'] == hashlib.sha256(xml).hexdigest()
        tree = ET.fromstring(xml)
        ns = {'a': 'http://www.acbf.info/xml/acbf/1.1'}
        identifier = tree.find('a:meta-data/a:document-info/a:id', ns)
        assert identifier is not None
        identifier.text = '<generated-document-id>'
        image_hashes = {name: hashlib.sha256(archive.read(name)).hexdigest()
                        for name in archive.namelist() if name.lower().endswith(('.jpg', '.jpeg', '.png'))}
    assert summary['new_calls'] == 0
    return {'pages': summary['pages'], 'panel_counts': summary['panel_counts'],
            'panel_steps': summary['panel_steps'], 'body_panel_steps': summary['body_panel_steps'],
            'source_pages': summary['source_pages'], 'accepted_pages': summary['accepted_pages'],
            'fallback_pages': summary['fallback_pages'], 'escalated_pages': summary['escalated_pages'],
            'refined_pages': summary['refined_pages'], 'image_hashes': image_hashes,
            'profile': {k: v for k, v in profile.items() if k != 'metadata_sha256'},
            'xml_without_document_id': ET.tostring(tree, encoding='unicode'),
            'outcomes': [{'status': o['status'], 'reason': o.get('reason'),
                          'selected_panels': o['selected']['panels'] if o['selected'] else None,
                          'attempt_models': [a.get('model') for a in o['attempts']]}
                         for o in outcomes]}


def main():
    EVIDENCE.mkdir(exist_ok=False)
    snapshot = source_hashes()
    save(EVIDENCE / 'source-hashes.json', snapshot)
    shutil.copyfile(__file__, EVIDENCE / 'executed-harness.py')
    initial_ledger = sha(LEDGER)
    initial_pdf = sha(PDF)
    render = json.loads(RENDER.read_text())
    assert initial_pdf == render['source_pdf_sha256']
    save(EVIDENCE / 'provenance.json', {'source_root': str(SOURCE), 'source_pdf': str(PDF),
        'source_pdf_sha256': initial_pdf, 'render_cache': str(RENDER), 'render_cache_sha256': sha(RENDER),
        'shared_ledger': str(LEDGER), 'shared_ledger_sha256_before': initial_ledger,
        'render_records_used_for_bytes_only': True, 'geometry_imported': False,
        'api_credentials_used': False, 'reading_direction': 'ltr'})
    sys.path[:0] = [str(SOURCE / 'panel_quality_probe'), str(SOURCE / 'gemini_panel_probe')]
    import auto_convert as ac
    from automatic_escalation import RunBlocked
    events = []

    class OfflineBudget(ac.Budget):
        def reserve(self, *args, **kwargs):
            events.append({'kind': 'reservation_denied', 'request_id': args[0] if args else None})
            raise ValueError('offline cache miss; no reservation or dispatch')

    class OfflineClient(ac.Client):
        def http(self, endpoint, body):
            events.append({'kind': 'http_denied', 'endpoint': endpoint})
            raise RunBlocked('offline HTTP disabled; no request sent')

        def request(self, endpoint, body, kind):
            response, metadata = super().request(endpoint, body, kind)
            assert metadata['cached']
            events.append({'kind': kind, 'endpoint': endpoint, **metadata})
            return response, metadata

    ac.Budget = OfflineBudget
    ac.Client = OfflineClient
    # Network access is impossible even if a future code path bypasses Client.http.
    def deny_urlopen(*args, **kwargs):
        events.append({'kind': 'urlopen_denied'})
        raise RunBlocked('offline urlopen disabled; no request sent')
    ac.urllib.request.urlopen = deny_urlopen
    report = {'source_sha256s': snapshot, 'trials': [], 'http_dispatches': 0, 'paid_calls': 0}
    try:
        for count in PAGE_COUNTS:
            trial = EVIDENCE / f'pages-{count}'
            trial.mkdir()
            sources = inputs(count, trial, render)
            before = {k: hashes(v) for k, v in sources.items()}
            trial_report = {'page_count': count, 'formats': {}, 'all_formats_passed': False}
            report['trials'].append(trial_report)
            reference = None
            for fmt, source in sources.items():
                assert source_hashes() == snapshot, 'candidate source changed during experiment'
                output = trial / fmt
                ledger = trial / f'{fmt}-ledger.jsonl'
                shutil.copyfile(LEDGER, ledger)
                ledger_before = sha(ledger)
                argv = [str(ac.__file__), str(source), str(output), '--ledger', str(ledger),
                        '--title', f'Format parity {count} pages', '--reading-direction', 'ltr',
                        '--execute-approved']
                if fmt == 'pdf':
                    argv += ['--render-cache', str(RENDER), '--pages', ','.join(map(str, range(1, count + 1)))]
                save(trial / f'{fmt}-argv.json', argv)
                events.clear()
                old_argv, old_stdin = sys.argv, sys.stdin
                sys.argv, sys.stdin = argv, io.StringIO('sk-' + 'OFFLINE_NO_CREDENTIAL_1234567890' * 2 + '\n')
                status, failure = 'completed', None
                started = time.monotonic()
                with (trial / f'{fmt}.log').open('w') as log:
                    try:
                        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                            ac.main()
                    except (Exception, SystemExit) as exc:
                        status, failure = 'blocked', f'{type(exc).__name__}: {exc}'
                        traceback.print_exc(file=log)
                    finally:
                        sys.argv, sys.stdin = old_argv, old_stdin
                assert sha(ledger) == ledger_before, 'copied ledger changed'
                assert sha(LEDGER) == initial_ledger, 'shared ledger changed'
                record = {'status': status, 'failure': failure, 'elapsed_seconds': time.monotonic() - started,
                          'output': str(output), 'cache_hits': sum(e.get('cached') is True for e in events),
                          'new_calls': 0, 'events': list(events), 'copied_ledger_unchanged': True}
                trial_report['formats'][fmt] = record
                save(EVIDENCE / 'report.json', report)
                if status != 'completed':
                    print(json.dumps({'trial': count, 'format': fmt, 'status': status, 'failure': failure,
                                      'events': events[-2:]}, indent=2), flush=True)
                    return
                normalized = semantics(output)
                save(trial / f'{fmt}-semantics.json', normalized)
                if reference is None:
                    reference = normalized
                else:
                    assert normalized == reference, f'{fmt} differs from PDF semantics'
                record['semantic_parity'] = True
                record['summary'] = json.loads(next(output.glob('completed-*.json')).read_text())
                print(json.dumps({'trial': count, 'format': fmt, 'status': status,
                                  'cache_hits': record['cache_hits'], 'panel_counts': normalized['panel_counts']}), flush=True)
            assert {k: hashes(v) for k, v in sources.items()} == before
            trial_report['all_formats_passed'] = True
            trial_report['original_input_bytes_unchanged'] = True
    finally:
        report['shared_ledger_unchanged'] = sha(LEDGER) == initial_ledger
        report['original_pdf_unchanged'] = sha(PDF) == initial_pdf
        report['candidate_source_unchanged'] = source_hashes() == snapshot
        save(EVIDENCE / 'report.json', report)
        print(json.dumps({'report': str(EVIDENCE / 'report.json'),
                          'completed_trials': [t['page_count'] for t in report['trials'] if t['all_formats_passed']]}), flush=True)


if __name__ == '__main__':
    main()
