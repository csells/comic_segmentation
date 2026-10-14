"""Conditional V31 provenance boundary; no provider or application execution."""
import copy
import hashlib
import json
from pathlib import Path
import re

POLICY = 'automatic-marked-target-completeness-v63'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def validate_acceptance(page, candidate, verdict, validate_proof):
    require(isinstance(verdict, dict) and verdict.get('route') == 'keep',
            'Missing passing completeness verdict')
    proof = verdict.get('proof')
    require(isinstance(proof, dict) and set(proof) == {'path', 'sha256'},
            'Missing bound completeness proof')
    require(isinstance(proof['sha256'], str) and
            re.fullmatch(r'[0-9a-f]{64}', proof['sha256']) is not None,
            'Invalid completeness proof hash')
    require(sha(proof['path']) == proof['sha256'], 'Completeness proof changed')
    checked = validate_proof(page, candidate, proof, require_keep=True)
    require(checked == verdict and checked.get('route') == 'keep',
            'Stored completeness verdict differs from validated proof')
    return proof['sha256']


def validate_page_record(publication, analysis, record, result, ordinal, validate_proof):
    """Both new and resumed records must identify the actual two source byte sets."""
    require(type(ordinal) is int and ordinal > 0 and
            type(record.get('source_page')) is int and record['source_page'] > 0,
            'Invalid output/source page order')
    require(result.get('policy') == POLICY, 'Old or unbound page policy')
    require(type(result.get('page')) is int and result['page'] == ordinal and
            type(result.get('source_page')) is int and
            result['source_page'] == record['source_page'], 'Page source/order changed')
    publication_hash, analysis_hash = sha(publication), sha(analysis)
    require(record.get('sha256') == publication_hash == result.get('source_sha256'),
            'Publication source changed')
    require(result.get('analysis_source_sha256') == analysis_hash, 'Analysis source changed')
    status = result.get('status')
    require(status in ('accepted', 'whole_page_fallback'), 'Page is not publishable')
    proof_hash, candidate_identity, direction = None, None, None
    reason = None
    if status == 'accepted':
        selected, attempts = result.get('selected'), result.get('attempts')
        require(isinstance(selected, dict) and isinstance(attempts, list) and attempts,
                'Missing selected acceptance attempt')
        last = attempts[-1]
        require(isinstance(last, dict) and last.get('candidate') == selected,
                'Selected candidate is not the final accepted attempt')
        judge, verifier = last.get('judge'), last.get('verifier')
        # Reconstruct the controller's actual quality route. A persisted verifier
        # cannot override an invalid judge or contradict an earlier direct keep.
        quality_passed = isinstance(judge, dict) and (
            (judge.get('route') == 'keep' and 'verifier' not in last) or
            (judge.get('route') == 'escalate' and isinstance(verifier, dict) and
             verifier.get('route') == 'keep'))
        require(quality_passed, 'Invalid quality trace: existing quality did not pass')
        require(selected.get('source_sha256') == analysis_hash, 'Candidate analysis source changed')
        proposal = selected.get('panels', {})
        require(proposal.get('classification') in ('panels', 'whole_page'),
                'Blank or malformed acceptance is not qualified')
        direction = proposal.get('reading_direction')
        require(direction in ('ltr', 'rtl'), 'Invalid accepted reading direction')
        proof_hash = validate_acceptance(analysis, selected, last.get('completeness'), validate_proof)
        candidate_identity = selected.get('identity')
    else:
        require(result.get('selected') is None, 'Fallback must not retain accepted geometry')
        reason = result.get('reason')
        require(isinstance(reason, str) and reason.strip(), 'Fallback reason missing')
    return {'page': ordinal, 'source_page': record['source_page'],
            'source_sha256': publication_hash, 'analysis_source_sha256': analysis_hash,
            'status': status, 'reading_direction': direction,
            'candidate_identity': candidate_identity, 'completeness_proof_sha256': proof_hash,
            'fallback_reason': reason}


def publication_inputs(entries, bindings, expected_frames, *, title, direction, auxiliary):
    """Canonical ordered inputs, including source bytes and every accepted proof."""
    require(direction in ('ltr', 'rtl'), 'Invalid publication reading direction')
    require(len(entries) == len(bindings) == len(expected_frames) and entries,
            'Publication binding count differs')
    pages = []
    for ordinal, (entry, binding, frames) in enumerate(zip(entries, bindings, expected_frames), 1):
        require(entry.get('page') == binding.get('page') == ordinal,
                'Publication order changed')
        require(binding['reading_direction'] in (None, direction),
                'Publication direction contradicts accepted source')
        pages.append({**copy.deepcopy(binding), 'entry': copy.deepcopy(entry),
                      'expected_frames': list(frames)})
    return {'schema': 'comic-publication-input-v1', 'policy': POLICY, 'title': title,
            'reading_direction': direction, 'pages': pages,
            'auxiliary': copy.deepcopy(auxiliary)}


def bind_manifest(manifest, inputs):
    """Refuse adapter fallback or mapping changes beneath an accepted claim."""
    require(manifest.get('page_count') == len(inputs['pages']) and
            manifest.get('reading_direction') == inputs['reading_direction'],
            'Adapter publication identity differs')
    actual = manifest.get('pages')
    require(isinstance(actual, list) and len(actual) == len(inputs['pages']),
            'Adapter page inventory differs')
    for published, expected in zip(actual, inputs['pages']):
        require(published.get('page') == expected['page'] and
                published.get('source_page') == expected['source_page'] and
                published.get('source_image') == expected['entry']['image'] and
                published.get('sha256') == expected['source_sha256'] and
                published.get('frames') == expected['expected_frames'] and
                published.get('frame_count') == len(expected['expected_frames']) and
                published.get('fallback_reason') == expected['fallback_reason'],
                'Adapter changed source, geometry or acceptance status')
    preserved = manifest.get('preserved_auxiliary')
    require(isinstance(preserved, list) and
            [{'source': item.get('source'), 'sha256': item.get('sha256')}
             for item in preserved] == inputs['auxiliary'], 'Adapter auxiliary bytes differ')
    result = copy.deepcopy(manifest)
    result['publication_inputs'] = copy.deepcopy(inputs)
    result['publication_input_sha256'] = digest(inputs)
    return result


def validate_archive_reuse(output, manifest, inputs):
    require(manifest.get('publication_inputs') == inputs and
            manifest.get('publication_input_sha256') == digest(inputs),
            'Published input/proof binding changed; use a new output')
    require(sha(output) == manifest.get('output_sha256'), 'Published archive changed')
    # Also check the adapter result that was bound, not just a saved digest.
    require(bind_manifest(manifest, inputs) == manifest, 'Published manifest changed')
