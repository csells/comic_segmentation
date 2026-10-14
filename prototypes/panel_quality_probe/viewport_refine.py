"""Small source-pixel reading margin; does not infer scene ownership or boundaries."""
import copy
import math


def reading_viewports(value, width, height):
    """Expand once: <=1% short page side and <=5% of each crop dimension per edge.

    Returned geometry is the reading viewport, not a segmentation mask. Callers
    must preserve lineage to avoid applying the margin again to a repaired view.
    Whole-page/blank classifications and scene order/identity remain unchanged.
    """
    if type(width) is not int or type(height) is not int or min(width, height) < 1:
        raise ValueError('Invalid source dimensions')
    result = copy.deepcopy(value)
    if value['classification'] != 'panels':
        return result, []
    changes = []
    page_margin = math.ceil(min(width, height) * .01)
    for index, panel in enumerate(result['panels']):
        top, left, bottom, right = panel['box']
        if not 0 <= left < right <= 1000 or not 0 <= top < bottom <= 1000:
            raise ValueError('Invalid panel geometry')
        # Evaluate spans in unrounded source space; round outward after padding.
        px_width, px_height = (right-left)*width/1000, (bottom-top)*height/1000
        dx = min(page_margin, max(1, math.ceil(px_width*.05)))
        dy = min(page_margin, max(1, math.ceil(px_height*.05)))
        box = [max(0, math.floor(top-dy*1000/height)),
               max(0, math.floor(left-dx*1000/width)),
               min(1000, math.ceil(bottom+dy*1000/height)),
               min(1000, math.ceil(right+dx*1000/width))]
        panel['box'] = box
        changes.append({'index': index, 'order': panel['order'], 'before': [top,left,bottom,right],
                        'after': box, 'margin_source_pixels': [dx,dy]})
    return result, changes
