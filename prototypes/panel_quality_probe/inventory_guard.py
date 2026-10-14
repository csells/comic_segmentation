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


def represented_orders(group, current):
    """Count current regions materially visible inside the source union.

    The merged region is one view. Other regions must have at least half their
    own area in the union to count; incidental edge fragments are not views.
    This is a conservation guard, not a proof that view identities are correct.
    """
    boxes=[p['box'] for p in group['previous_panels']]
    union=[min(b[0] for b in boxes),min(b[1] for b in boxes),
           max(b[2] for b in boxes),max(b[3] for b in boxes)]
    return sorted({group['current_order']} | {p['order'] for p in current_regions(current)
                   if intersection(union,p['box'])/area(p['box'])>=.5})


def context_request_body(source, region):
    import base64
    from pathlib import Path
    from continuity_verifier import SCHEMA
    prompt=(Path(__file__).parent/'inventory-context-prompt-v2.txt').read_text()
    content=[{'type':'input_text','text':prompt}]
    for path in (source,region):
        content.append({'type':'input_image','image_url':'data:image/jpeg;base64,'+
                        base64.b64encode(Path(path).read_bytes()).decode(),'detail':'original'})
    return {'model':'gpt-6-sol','store':False,'max_output_tokens':4096,
            'reasoning':{'effort':'high'},'service_tier':'default',
            'text':{'format':{'type':'json_schema','name':'source_continuity','strict':True,'schema':SCHEMA}},
            'input':[{'role':'user','content':content}]}
