"""Locate potential scene merges when a stronger detector reduces the inventory.

Geometry only selects unannotated regions for independent diagnosis. It does not
establish whether the earlier split or the later merge is correct.
"""


def area(box):
    top, left, bottom, right = box
    return (bottom - top) * (right - left)


def intersection(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def current_regions(value):
    if value['classification'] == 'panels':
        return value['panels']
    return [{'order': 1, 'box': [0, 0, 1000, 1000]}]


def merged_groups(previous, current):
    """Group earlier views best explained by the same larger current region.

    Use maximum IoU so a surviving inset takes precedence over its enclosing
    background. Require 90% coverage of each old region to avoid comparing
    unrelated regions merely because their boxes touch.
    """
    if previous['classification'] != 'panels':
        return []
    old, new = previous['panels'], current_regions(current)
    if len(new) >= len(old):
        return []
    groups = {p['order']: [] for p in new}
    for prior in old:
        def iou(candidate):
            overlap = intersection(prior['box'], candidate['box'])
            return overlap / (area(prior['box']) + area(candidate['box']) - overlap)
        best = max(new, key=iou)
        if intersection(prior['box'], best['box']) / area(prior['box']) >= .90:
            groups[best['order']].append(prior)
    return [{'current_order': order, 'previous_panels': panels}
            for order, panels in groups.items() if len(panels) > 1]


SCHEMA = {'type': 'object', 'properties': {
    'classification': {'type': 'string', 'enum': ['preserved', 'lost', 'uncertain']},
    'views': {'type': 'array', 'items': {'type': 'string'}},
    'evidence': {'type': 'string'}},
    'required': ['classification', 'views', 'evidence'], 'additionalProperties': False}


def request_body(source, region, group, current):
    import base64
    import json
    from pathlib import Path
    prompt = (Path(__file__).parent / 'inventory-verifier-prompt-v1.txt').read_text()
    geometry = {'earlier_regions_under_review':
                [{'order': p['order'], 'box': p['box']} for p in group['previous_panels']],
                'current_merged_order': group['current_order'],
                'all_current_regions': [{'order': p['order'], 'box': p['box']} for p in current_regions(current)]}
    content = [{'type': 'input_text', 'text': prompt + '\n' + json.dumps(geometry, sort_keys=True)}]
    for path in (source, region):
        content.append({'type': 'input_image', 'image_url': 'data:image/jpeg;base64,' +
                        base64.b64encode(Path(path).read_bytes()).decode(), 'detail': 'original'})
    return {'model': 'gpt-6-sol', 'store': False, 'max_output_tokens': 4096,
            'reasoning': {'effort': 'high'}, 'service_tier': 'default',
            'text': {'format': {'type': 'json_schema', 'name': 'inventory_preservation', 'strict': True, 'schema': SCHEMA}},
            'input': [{'role': 'user', 'content': content}]}


def response_verdict(raw):
    import json
    if raw.get('status', 'completed') != 'completed':
        raise ValueError('incomplete inventory adjudication')
    value = json.loads(''.join(c.get('text', '') for v in raw.get('output', [])
                              for c in v.get('content', []) if c.get('type') == 'output_text'))
    if not isinstance(value, dict) or set(value) != {'classification', 'views', 'evidence'}:
        raise ValueError('invalid inventory fields')
    if value['classification'] not in ('preserved', 'lost', 'uncertain'):
        raise ValueError('invalid inventory classification')
    if not isinstance(value['views'], list) or not value['views'] or any(
            not isinstance(v, str) or not v.strip() for v in value['views']):
        raise ValueError('inventory view descriptions required')
    if not isinstance(value['evidence'], str) or not value['evidence'].strip():
        raise ValueError('inventory evidence required')
    return value
