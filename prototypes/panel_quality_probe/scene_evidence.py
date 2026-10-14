"""Source-only scene evidence for research; no provider calls or crop approval.

Detector descriptions are fallible locators. An audit must establish ownership
from the source before its result can assist a separate crop check. Evidence can
follow a geometry-only expansion only through an explicit frozen proposal link.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PROMPT = HERE / 'scene-evidence-prompt-v4.txt'
MODEL = 'gpt-6-sol'
MODELS = ('gpt-6-sol', 'gpt-6-astra')
VERSION = 6
SCENE_FIELDS = {'order', 'identity', 'owned_content', 'ownership_cues',
                'distinguish_from_neighbors', 'uncertain'}
ISSUE_KINDS = ('missing_scene', 'ambiguous_mapping', 'contradictory_ownership', 'uncertain', 'shared_unowned')
# Content no single scene visibly owns; recorded, but never by itself an unresolved inventory.
NON_BLOCKING_ISSUES = ('shared_unowned',)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _source(bundle):
    images = bundle['images']
    if not isinstance(images, list) or any(not isinstance(image, dict) for image in images):
        raise ValueError('Invalid source image inventory')
    sources = [image for image in images if image.get('label') == 'Original complete page']
    if len(sources) != 1:
        raise ValueError('Expected one original complete source')
    source = sources[0]
    data = Path(source['path']).read_bytes()
    if hashlib.sha256(data).hexdigest() != source.get('sha256'):
        raise ValueError('Source image changed')
    return source['sha256'], data


def _panels(bundle, *, descriptions):
    panels = bundle['panels']
    if not isinstance(panels, list) or not panels:
        raise ValueError('Missing proposal inventory')
    result = []
    for order, panel in enumerate(panels, 1):
        if not isinstance(panel, dict) or type(panel.get('order')) is not int or panel['order'] != order:
            raise ValueError('Proposal orders must be contiguous and unchanged')
        box = panel.get('box')
        if (not isinstance(box, list) or len(box) != 4 or
                any(type(n) is not int or not 0 <= n <= 1000 for n in box) or
                box[0] >= box[2] or box[1] >= box[3]):
            raise ValueError('Invalid proposal rectangle')
        value = {'order': order, 'box': list(box)}
        if descriptions:
            description = panel.get('description')
            if not isinstance(description, str) or not description.strip() or len(description) > 1200:
                raise ValueError('Missing or invalid detector description')
            value['description'] = description
        result.append(value)
    return result


def source_proposal(bundle):
    """Freeze only source identity and detector-proposed runtime fields."""
    source_sha, _ = _source(bundle)
    if bundle.get('classification') not in ('panels', 'whole_page', 'blank'):
        raise ValueError('Invalid proposal classification')
    if bundle.get('reading_direction') not in ('ltr', 'rtl'):
        raise ValueError('Invalid proposal reading direction')
    return {'source_sha256': source_sha, 'classification': bundle['classification'],
            'reading_direction': bundle['reading_direction'],
            'panels': _panels(bundle, descriptions=True)}


def proposal_sha256(bundle):
    return _digest(source_proposal(bundle))


def evidence_schema():
    text = {'type': 'string', 'minLength': 1, 'maxLength': 1200}
    scene = {'order': {'type': 'integer', 'minimum': 1}, 'identity': text,
             **{name: {'type': 'array', 'items': text, 'maxItems': 8}
                for name in ('owned_content', 'ownership_cues', 'distinguish_from_neighbors')},
             'uncertain': {'type': 'boolean'}}
    issue = {'kind': {'type': 'string', 'enum': list(ISSUE_KINDS)},
             'orders': {'type': 'array', 'items': {'type': 'integer', 'minimum': 1}},
             'evidence': text}
    fields = {'inventory_status': {'type': 'string', 'enum': ['complete', 'incomplete', 'uncertain']},
              'scenes': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                                                  'properties': scene, 'required': list(scene)}},
              'issues': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                                                  'properties': issue, 'required': list(issue)}}}
    return {'type': 'object', 'additionalProperties': False,
            'properties': fields, 'required': list(fields)}


def source_output_limit(scene_count):
    """Bound reasoning plus structured output without changing small-case keys."""
    if type(scene_count) is not int or scene_count < 1:
        raise ValueError('Expected a positive scene count')
    return 8192 if scene_count <= 4 else max(8192, min(24576, 4096 + 1024 * scene_count))


def recovery_output_limit(scene_count):
    """The one bounded expansion allowed after exact output exhaustion."""
    return min(32768, 2 * source_output_limit(scene_count))


def _output_limit(snapshot, output_limit):
    default = source_output_limit(len(snapshot['panels']))
    if output_limit is None:
        return default
    if output_limit not in (default, recovery_output_limit(len(snapshot['panels']))):
        raise ValueError('Unsupported source audit output allowance')
    return output_limit


def request_body(bundle, *, model=MODEL, output_limit=None):
    """Build one generic source audit, excluding crops, paths and reviewer data."""
    if model not in MODELS:
        raise ValueError('Unsupported source audit model')
    snapshot = source_proposal(bundle)
    _, data = _source(bundle)
    supplied = {key: snapshot[key] for key in ('classification', 'reading_direction', 'panels')}
    supplied['box_coordinate_convention'] = '[top,left,bottom,right] normalized 0..1000'
    return {'model': model, 'store': False, 'max_output_tokens': _output_limit(snapshot, output_limit),
            'reasoning': {'effort': 'high'}, 'service_tier': 'default',
            'text': {'format': {'type': 'json_schema', 'name': 'source_scene_evidence',
                                'strict': True, 'schema': evidence_schema()}},
            'input': [{'role': 'user', 'content': [
                {'type': 'input_text', 'text': PROMPT.read_text() + '\n' + json.dumps(supplied)},
                {'type': 'input_image', 'detail': 'original',
                 'image_url': 'data:image/jpeg;base64,' + base64.b64encode(data).decode()}]}]}


def _validate_result(value, orders):
    if not isinstance(value, dict) or set(value) != {'inventory_status', 'scenes', 'issues'}:
        raise ValueError('Invalid source evidence envelope')
    if value['inventory_status'] not in ('complete', 'incomplete', 'uncertain'):
        raise ValueError('Invalid inventory status')
    scenes = value['scenes']
    if (not isinstance(scenes, list) or any(not isinstance(s, dict) or set(s) != SCENE_FIELDS for s in scenes)
            or [s['order'] for s in scenes] != orders):
        raise ValueError('Unmapped or changed scene inventory')
    for scene in scenes:
        if type(scene['order']) is not int or type(scene['uncertain']) is not bool:
            raise ValueError('Invalid source evidence types')
        for key in SCENE_FIELDS - {'order', 'uncertain'}:
            values = [scene[key]] if key == 'identity' else scene[key]
            if (not isinstance(values, list) or len(values) > 8 or
                    any(not isinstance(v, str) or not v.strip() or len(v) > 1200 for v in values)):
                raise ValueError('Invalid source evidence text')
        if not scene['uncertain'] and (not scene['owned_content'] or not scene['ownership_cues']):
            raise ValueError('Established scene lacks content or source support')
    if not isinstance(value['issues'], list):
        raise ValueError('Invalid source issues')
    for issue in value['issues']:
        if (not isinstance(issue, dict) or set(issue) != {'kind', 'orders', 'evidence'} or
                issue['kind'] not in ISSUE_KINDS or not isinstance(issue['orders'], list) or
                any(type(n) is not int or n not in orders for n in issue['orders']) or
                not isinstance(issue['evidence'], str) or not issue['evidence'].strip() or
                len(issue['evidence']) > 1200):
            raise ValueError('Invalid source issue')
    return value


def request_fingerprint(bundle, *, model=MODEL, request_kind='detector', output_limit=None):
    prefixes = {'detector': b'openai-responses:', 'verifier': b'comic-escalation-judge-v1:'}
    if request_kind not in prefixes:
        raise ValueError('Unsupported source audit request kind')
    return hashlib.sha256(prefixes[request_kind] +
                          json.dumps(request_body(bundle, model=model, output_limit=output_limit), sort_keys=True).encode()).hexdigest()


def response_evidence(raw, bundle, request=None, *, model=MODEL, request_kind='detector', output_limit=None):
    """Parse a completed audit and bind it to its unaltered proposal snapshot."""
    if raw.get('status') != 'completed':
        raise ValueError('Source audit incomplete; never certify or retry automatically')
    texts = []
    for item in raw.get('output', []):
        if item.get('type') != 'message':
            continue
        if item.get('status') not in ('completed', None):
            raise ValueError('Source audit message incomplete')
        for part in item.get('content', []):
            if part.get('type') == 'refusal':
                raise ValueError('Source audit refused')
            if part.get('type') == 'output_text':
                texts.append(part['text'])
    snapshot = source_proposal(bundle)
    result = _validate_result(json.loads(''.join(texts)), [p['order'] for p in snapshot['panels']])
    output_limit = _output_limit(snapshot, output_limit)
    fingerprint = request_fingerprint(bundle, model=model, request_kind=request_kind, output_limit=output_limit)
    if request is not None and (request.get('retry_of') or request.get('request_id')) != fingerprint:
        raise ValueError('Source audit request does not match requested model and inputs')
    response_model = raw.get('model')
    if response_model is not None and (not isinstance(response_model, str) or
                                       response_model != model and not response_model.startswith(model + '-')):
        raise ValueError('Source audit returned another model')
    artifact = {'version': VERSION, 'model': model, 'response_model': response_model,
                'request_kind': request_kind, 'request_fingerprint': fingerprint, 'output_limit': output_limit,
                'prompt_sha256': hashlib.sha256(PROMPT.read_bytes()).hexdigest(),
                'proposal': snapshot, 'proposal_sha256': _digest(snapshot), 'result': result,
                'response_sha256': _digest(raw),
                'request': {key: request[key] for key in ('request_id', 'path', 'cached', 'retry_of')
                            if request is not None and key in request}}
    artifact['evidence_sha256'] = _digest(artifact)
    return artifact


def evidence_gate(evidence, bundle, *, frozen_proposal_sha256=None):
    """Reject missing/stale/uncertain evidence; this is NOT a crop-quality pass.

    Supplying a frozen link asserts lineage from that proposal. It authorizes
    only monotonic expansions with the same source, inventory and order. It does
    not infer scene correspondence from overlap or matching ordinal numbers.
    """
    try:
        if not isinstance(evidence, dict):
            raise ValueError('Source evidence missing')
        content = {key: value for key, value in evidence.items() if key != 'evidence_sha256'}
        if _digest(content) != evidence.get('evidence_sha256'):
            raise ValueError('Source evidence changed')
        if (evidence['version'] != VERSION or evidence['model'] not in MODELS or
                evidence['prompt_sha256'] != hashlib.sha256(PROMPT.read_bytes()).hexdigest()):
            raise ValueError('Source evidence policy changed')
        snapshot = evidence['proposal']
        if _digest(snapshot) != evidence['proposal_sha256']:
            raise ValueError('Frozen proposal changed')
        source_sha, _ = _source(bundle)
        if source_sha != snapshot['source_sha256']:
            raise ValueError('Source evidence belongs to another page')
        if any(bundle.get(key) != snapshot[key] for key in ('classification', 'reading_direction')):
            raise ValueError('Source classification or direction changed')
        frozen = {**bundle, **{key: snapshot[key] for key in ('classification', 'reading_direction', 'panels')}}
        if request_fingerprint(frozen, model=evidence['model'], request_kind=evidence['request_kind'],
                               output_limit=evidence['output_limit']) != evidence['request_fingerprint']:
            raise ValueError('Source audit request fingerprint changed')
        if frozen_proposal_sha256 is None:
            if source_proposal(bundle) != snapshot:
                raise ValueError('Proposal changed without explicit frozen lineage')
        else:
            if (not isinstance(frozen_proposal_sha256, str) or
                    not re.fullmatch(r'[0-9a-f]{64}', frozen_proposal_sha256) or
                    frozen_proposal_sha256 != evidence['proposal_sha256']):
                raise ValueError('Frozen proposal link does not match')
            current = _panels(bundle, descriptions=False)
            if len(current) != len(snapshot['panels']):
                raise ValueError('Proposal inventory changed')
            for before, after in zip(snapshot['panels'], current):
                y, x, bottom, right = before['box']
                yy, xx, bb, rr = after['box']
                if before['order'] != after['order'] or yy > y or xx > x or bb < bottom or rr < right:
                    raise ValueError('Geometry is not a monotonic expansion of the frozen proposal')
        value = _validate_result(evidence['result'], [p['order'] for p in snapshot['panels']])
        blocking = [issue for issue in value['issues'] if issue['kind'] not in NON_BLOCKING_ISSUES]
        # Status 'uncertain' caused only by shared_unowned content is resolved; 'incomplete' never is.
        status_ok = value['inventory_status'] == 'complete' or (
            value['inventory_status'] == 'uncertain' and value['issues'] and not blocking)
        if not status_ok or blocking or any(s['uncertain'] for s in value['scenes']):
            raise ValueError('Source inventory or ownership remains unresolved')
    except (KeyError, TypeError, ValueError, OSError) as error:
        return {'route': 'escalate', 'reason': str(error)}
    return {'route': 'keep', 'reason': 'Source evidence is linked and resolved; crop quality still requires checking',
            'evidence_sha256': evidence['evidence_sha256'], 'proposal_sha256': evidence['proposal_sha256']}


def verifier_hypotheses(evidence, bundle, *, frozen_proposal_sha256=None):
    """Return only approved source hypotheses for the existing auxiliary wrapper."""
    gate = evidence_gate(evidence, bundle, frozen_proposal_sha256=frozen_proposal_sha256)
    if gate['route'] != 'keep':
        raise ValueError(gate['reason'])
    return {'scenes': [{key: copy.deepcopy(scene[key]) for key in SCENE_FIELDS}
                       for scene in evidence['result']['scenes']]}
