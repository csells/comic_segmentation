//! Deterministic source-pixel geometry refinement (no model calls).
//!
//! Each function expands proposed pixel boxes `[left, top, right, bottom]`
//! conservatively and returns change records with the prototype's fields.
//! None can invent, split, merge or reorder panels.

use crate::cv::{self, Components};
use crate::image::Rgb;
use crate::json::Value;
use crate::{arr, obj};

pub type PxBox = [i64; 4];

fn corner_blocks_dark(rgb: &Rgb) -> (bool, i64, Vec<f64>) {
    let (h, w) = (rgb.height, rgb.width);
    let corner = (cv::py_round(h.min(w) as f64 * 0.01)).max(2) as usize;
    let maxes = rgb.channel_max();
    let block = |x0: usize, y0: usize| -> f64 {
        let mut v = Vec::with_capacity(corner * corner);
        for y in y0..y0 + corner.min(h) {
            for x in x0..x0 + corner.min(w) {
                v.push(maxes[y * w + x]);
            }
        }
        cv::quantile_linear(&mut v, 0.95)
    };
    let cw = corner.min(w);
    let ch = corner.min(h);
    let levels = vec![block(0, 0), block(w - cw, 0), block(0, h - ch), block(w - cw, h - ch)];
    (levels.iter().all(|l| *l <= 25.0), corner as i64, levels)
}

fn threshold_mask(values: &[u8], pred: impl Fn(u8) -> bool) -> Vec<u8> {
    values.iter().map(|&v| pred(v) as u8).collect()
}

fn pxbox(b: PxBox) -> Value {
    Value::from(b.to_vec())
}

/// `gutter_refine.expand_dark_gutter_boxes`.
pub fn expand_dark_gutter_boxes(rgb: &Rgb, boxes: &[PxBox]) -> (Vec<PxBox>, Vec<Value>) {
    let (height, width) = (rgb.height as i64, rgb.width as i64);
    let mut result: Vec<PxBox> = boxes.to_vec();
    let (dark, _, _) = corner_blocks_dark(rgb);
    if !dark {
        return (result, vec![]);
    }
    let mask = threshold_mask(&rgb.channel_max(), |v| v > 25);
    let mask = cv::close3(&mask, rgb.width, rgb.height);
    let cc = cv::connected_components(&mask, rgb.width, rgb.height);
    let mut candidates: Vec<PxBox> = Vec::new();
    for s in &cc.stats[1..] {
        if (s.area as f64) < (width * height) as f64 * 0.01 || (s.area as f64) / ((s.width * s.height) as f64) < 0.75 {
            continue;
        }
        candidates.push([s.left, s.top, s.left + s.width, s.top + s.height]);
    }
    let mut changes = Vec::new();
    for (index, b) in boxes.iter().enumerate() {
        let [x1, y1, x2, y2] = *b;
        let mut matches = Vec::new();
        for c in &candidates {
            let [l, t, r, bb] = *c;
            let scales = [width, height, width, height];
            if (0..4).any(|i| (b[i] - c[i]).abs() as f64 > 0.02 * scales[i] as f64) {
                continue;
            }
            let inter = (x2.min(r) - x1.max(l)).max(0) * (y2.min(bb) - y1.max(t)).max(0);
            let box_area = (x2 - x1) * (y2 - y1);
            let comp_area = (r - l) * (bb - t);
            if box_area.min(comp_area) > 0 && (inter as f64 / box_area as f64).min(inter as f64 / comp_area as f64) >= 0.90 {
                matches.push(*c);
            }
        }
        if matches.len() != 1 {
            continue;
        }
        let [l, t, r, bb] = matches[0];
        let expanded = [(x1.min(l - 2)).max(0), (y1.min(t - 2)).max(0), (x2.max(r + 2)).min(width), (y2.max(bb + 2)).min(height)];
        if expanded != *b {
            result[index] = expanded;
            changes.push(obj! {"index" => index, "before_pixels" => pxbox(*b),
            "component_pixels" => pxbox(matches[0]), "after_pixels" => pxbox(expanded)});
        }
    }
    (result, changes)
}

struct Balloon {
    bbox: PxBox,
    label: i32,
    area: i64,
    ink_holes: usize,
}

fn balloon_components(rgb: &Rgb) -> (Components, Vec<Balloon>) {
    let (h, w) = (rgb.height as i64, rgb.width as i64);
    let mask = threshold_mask(&rgb.channel_min(), |v| v >= 230);
    let cc = cv::connected_components(&mask, rgb.width, rgb.height);
    let mut out = Vec::new();
    for label in 1..cc.count {
        let s = cc.stats[label];
        let (x, y, bw, bh, area) = (s.left, s.top, s.width, s.height, s.area);
        if x == 0 || y == 0 || x + bw == w || y + bh == h {
            continue;
        }
        if bw.min(bh) < 12
            || (area as f64) < (w * h) as f64 * 0.00015
            || (area as f64) > (w * h) as f64 * 0.06
            || (area as f64) / ((bw * bh) as f64) < 0.35
        {
            continue;
        }
        let mut comp = vec![0u8; (bw * bh) as usize];
        for yy in 0..bh {
            for xx in 0..bw {
                let li = ((y + yy) * w + x + xx) as usize;
                comp[(yy * bw + xx) as usize] = (cc.labels[li] == label as i32) as u8;
            }
        }
        let mut holes = 0;
        for contour in cv::hole_contours(&comp, bw as usize, bh as usize) {
            let (_, _, hw, hh) = cv::bounding_rect(&contour);
            if 2 <= hw && hw as f64 <= bw as f64 * 0.3 && 3 <= hh && hh as f64 <= bh as f64 * 0.5 && cv::contour_area(&contour) >= 3.0 {
                holes += 1;
            }
        }
        if holes < 3 {
            continue;
        }
        out.push(Balloon { bbox: [x, y, x + bw, y + bh], label: label as i32, area, ink_holes: holes });
    }
    (cc, out)
}

/// Python `round(x, 4)`: correctly rounded, ties to even on the exact binary value.
pub fn py_round4(x: f64) -> f64 {
    py_round_digits(x, 4)
}

pub fn py_round_digits(x: f64, digits: u32) -> f64 {
    if !x.is_finite() || x == 0.0 {
        return x;
    }
    let bits = x.abs().to_bits();
    let exp = ((bits >> 52) & 0x7ff) as i64;
    let frac = bits & ((1u64 << 52) - 1);
    let (m, e) = if exp == 0 { (frac, -1074) } else { (frac | (1u64 << 52), exp - 1075) };
    if e >= 0 {
        return x;
    }
    let k = (-e) as u32;
    let scaled = m as u128 * 10u128.pow(digits);
    let q = if k >= 128 {
        0
    } else {
        let q = scaled >> k;
        let r = scaled & ((1u128 << k) - 1);
        let half = 1u128 << (k - 1);
        if r > half || (r == half && q & 1 == 1) { q + 1 } else { q }
    };
    let v: f64 = format!("{q}e-{digits}").parse().unwrap();
    if x < 0.0 { -v } else { v }
}

/// `balloon_refine.expand_balloon_boxes`.
pub fn expand_balloon_boxes(rgb: &Rgb, boxes: &[PxBox]) -> (Vec<PxBox>, Vec<Value>) {
    let (height, width) = (rgb.height as i64, rgb.width as i64);
    let (cc, components) = balloon_components(rgb);
    let mut result: Vec<PxBox> = boxes.to_vec();
    let mut changes = Vec::new();
    for (index, b) in boxes.iter().enumerate() {
        let [l, t, r, bb] = *b;
        let mut matches: Vec<(&Balloon, f64)> = Vec::new();
        for c in &components {
            let [x, y, rr, cb] = c.bbox;
            if x >= l && y >= t && rr <= r && cb <= bb {
                continue;
            }
            let (il, it, ir, ib) = (l.max(x), t.max(y), r.min(rr), bb.min(cb));
            if ir <= il || ib <= it {
                continue;
            }
            let mut count = 0i64;
            for yy in it..ib {
                for xx in il..ir {
                    if cc.labels[(yy * width + xx) as usize] == c.label {
                        count += 1;
                    }
                }
            }
            let coverage = count as f64 / c.area as f64;
            if coverage < 0.5 {
                continue;
            }
            if ((l - x).max(rr - r)) as f64 > width as f64 * 0.05 || ((t - y).max(cb - bb)) as f64 > height as f64 * 0.05 {
                continue;
            }
            matches.push((c, coverage));
        }
        if matches.is_empty() {
            continue;
        }
        let expanded = [
            l.min(matches.iter().map(|m| m.0.bbox[0] - 3).min().unwrap()).max(0),
            t.min(matches.iter().map(|m| m.0.bbox[1] - 3).min().unwrap()).max(0),
            r.max(matches.iter().map(|m| m.0.bbox[2] + 3).max().unwrap()).min(width),
            bb.max(matches.iter().map(|m| m.0.bbox[3] + 3).max().unwrap()).min(height),
        ];
        if expanded != *b {
            result[index] = expanded;
            let comps: Vec<Value> = matches
                .iter()
                .map(|(c, cov)| {
                    obj! {"box" => pxbox(c.bbox), "label" => c.label as i64, "area" => c.area,
                    "ink_holes" => c.ink_holes, "coverage" => py_round4(*cov)}
                })
                .collect();
            changes.push(obj! {"index" => index, "before_pixels" => pxbox(*b), "after_pixels" => pxbox(expanded),
            "components" => Value::Array(comps), "method" => "enclosed-lettered-light-component-v1"});
        }
    }
    (result, changes)
}

/// Fraction of `true` along `axis` maxed over the other axis (`band.mean(axis).max()`).
fn band_mean_max(dark: &[bool], w: usize, x0: usize, x1: usize, y0: usize, y1: usize, axis: usize) -> Option<f64> {
    if x1 <= x0 || y1 <= y0 {
        return None;
    }
    let (bw, bh) = (x1 - x0, y1 - y0);
    let mut best = f64::NEG_INFINITY;
    if axis == 1 {
        // mean over columns for each row
        for y in y0..y1 {
            let n = (x0..x1).filter(|&x| dark[y * w + x]).count();
            best = best.max(n as f64 / bw as f64);
        }
    } else {
        for x in x0..x1 {
            let n = (y0..y1).filter(|&y| dark[y * w + x]).count();
            best = best.max(n as f64 / bh as f64);
        }
    }
    Some(best)
}

/// `frame_refine.expand_frame_boxes`.
pub fn expand_frame_boxes(rgb: &Rgb, boxes: &[PxBox]) -> (Vec<PxBox>, Vec<Value>) {
    let (height, width) = (rgb.height as i64, rgb.width as i64);
    let (w, h) = (rgb.width, rgb.height);
    let dark: Vec<bool> = rgb.channel_max().iter().map(|&v| v < 100).collect();
    let ink = threshold_mask(&rgb.channel_min(), |v| v < 220);
    let ink = cv::close3(&ink, w, h);
    let cc = cv::connected_components(&ink, w, h);
    let mut candidates: Vec<PxBox> = Vec::new();
    for s in &cc.stats[1..] {
        if (s.width as f64 / width as f64).min(s.height as f64 / height as f64) < 0.025 || (s.area as f64) < (width * height) as f64 * 0.001
        {
            continue;
        }
        candidates.push([s.left, s.top, s.left + s.width, s.top + s.height]);
    }
    let mut result: Vec<PxBox> = boxes.to_vec();
    let mut changes = Vec::new();
    for (index, b) in boxes.iter().enumerate() {
        let [l, t, r, bb] = *b;
        let mut matches = Vec::new();
        for c in &candidates {
            let [x, y, rr, cb] = *c;
            let scales = [width, height, width, height];
            if (0..4).any(|i| (b[i] - c[i]).abs() as f64 > 0.02 * scales[i] as f64) {
                continue;
            }
            let inter = (r.min(rr) - l.max(x)).max(0) * (bb.min(cb) - t.max(y)).max(0);
            let areas = [(r - l) * (bb - t), (rr - x) * (cb - y)];
            if areas.iter().min().copied().unwrap() <= 0
                || areas.iter().map(|&a| inter as f64 / a as f64).fold(f64::INFINITY, f64::min) < 0.90
            {
                continue;
            }
            matches.push(*c);
        }
        if matches.len() != 1 {
            continue;
        }
        let [x, y, rr, cb] = matches[0];
        if ((l - x).max(t - y).max(rr - r).max(cb - bb)) as f64 <= 0.004 * width.min(height) as f64 {
            continue;
        }
        let dx = (cv::py_round(width as f64 * 0.02)).max(1);
        let dy = (cv::py_round(height as f64 * 0.02)).max(1);
        // Python slices clamp to [0, len]; a negative stop counts from the end.
        let sl = |a: i64, b: i64, n: i64| -> (usize, usize) {
            let norm = |v: i64| if v < 0 { (v + n).max(0) } else { v.min(n) };
            let (a, b) = (norm(a), norm(b));
            (a as usize, b.max(a) as usize)
        };
        let bands = [
            (sl(l, r, width), sl((t - dy).max(0), (t + dy + 1).min(height), height), 1),
            (sl(l, r, width), sl((bb - dy).max(0), (bb + dy + 1).min(height), height), 1),
            (sl((l - dx).max(0), (l + dx + 1).min(width), width), sl(t, bb, height), 0),
            (sl((r - dx).max(0), (r + dx + 1).min(width), width), sl(t, bb, height), 0),
        ];
        let failed = bands.iter().any(|((x0, x1), (y0, y1), axis)| match band_mean_max(&dark, w, *x0, *x1, *y0, *y1, *axis) {
            None => true,
            Some(m) => m < 0.8,
        });
        if failed {
            continue;
        }
        let expanded = [(l.min(x - 2)).max(0), (t.min(y - 2)).max(0), (r.max(rr + 2)).min(width), (bb.max(cb + 2)).min(height)];
        result[index] = expanded;
        changes.push(obj! {"index" => index, "before_pixels" => pxbox(*b), "after_pixels" => pxbox(expanded),
        "component_pixels" => pxbox(matches[0]), "method" => "near-matching-connected-ink-v1"});
    }
    (result, changes)
}

/// `fringe_refine.expand_dark_fringe_boxes`.
pub fn expand_dark_fringe_boxes(rgb: &Rgb, boxes: &[PxBox]) -> (Vec<PxBox>, Vec<Value>) {
    let (height, width) = (rgb.height as i64, rgb.width as i64);
    let mut result: Vec<PxBox> = boxes.to_vec();
    let (dark, _, _) = corner_blocks_dark(rgb);
    if !dark {
        return (result, vec![]);
    }
    let mask = threshold_mask(&rgb.channel_max(), |v| v > 25);
    let mask = cv::close3(&mask, rgb.width, rgb.height);
    let cc = cv::connected_components(&mask, rgb.width, rgb.height);
    let short = height.min(width) as f64;
    let (near, limit) = (0.005 * short, 0.04 * short);
    let mut attached: Vec<Vec<PxBox>> = vec![vec![]; boxes.len()];
    for label in 1..cc.count {
        let s = cc.stats[label];
        let (x, y, w, h, area) = (s.left, s.top, s.width, s.height, s.area);
        if (area as f64) < (8f64).max((width * height) as f64 * 0.00001) || area as f64 > (width * height) as f64 * 0.01 {
            continue;
        }
        let component = [x, y, x + w, y + h];
        let mut owners = Vec::new();
        for (index, b) in boxes.iter().enumerate() {
            let [l, t, r, bb] = *b;
            let edge = (l as f64 / width as f64)
                .min(t as f64 / height as f64)
                .min((width - r) as f64 / width as f64)
                .min((height - bb) as f64 / height as f64);
            if edge < 0.02 {
                continue;
            }
            let ddx = (l - (x + w)).max(x - r).max(0);
            let ddy = (t - (y + h)).max(y - bb).max(0);
            if ddx.max(ddy) as f64 > near {
                continue;
            }
            let overflow = (l - x).max(t - y).max(x + w - r).max(y + h - bb);
            if overflow as f64 > limit || overflow as f64 <= 0.004 * short {
                continue;
            }
            owners.push(index);
        }
        if owners.len() != 1 {
            continue;
        }
        let index = owners[0];
        let shared = boxes.iter().enumerate().any(|(j, ob)| {
            if j == index {
                return false;
            }
            let [l, t, r, bb] = *ob;
            let (y0, y1) = (t.max(0), bb.min(height));
            let (x0, x1) = (l.max(0), r.min(width));
            (y0..y1).any(|yy| (x0..x1).any(|xx| cc.labels[(yy * width + xx) as usize] == label as i32))
        });
        if shared {
            continue;
        }
        let [l, t, r, bb] = boxes[index];
        if x >= l && y >= t && x + w <= r && y + h <= bb {
            continue;
        }
        attached[index].push(component);
        let old = result[index];
        result[index] = [
            (old[0].min(x - 2)).max(0),
            (old[1].min(y - 2)).max(0),
            (old[2].max(x + w + 2)).min(width),
            (old[3].max(y + h + 2)).min(height),
        ];
    }
    let changes = attached
        .iter()
        .enumerate()
        .filter(|(_, c)| !c.is_empty())
        .map(|(i, comps)| {
            obj! {"index" => i, "before_pixels" => pxbox(boxes[i]), "after_pixels" => pxbox(result[i]),
            "component_pixels" => Value::Array(comps.iter().map(|c| pxbox(*c)).collect()),
            "method" => "nearby-black-gutter-fringe-v1"}
        })
        .collect();
    (result, changes)
}

/// `component_refine.uncovered_content_risk`.
pub fn uncovered_content_risk(rgb: &Rgb, boxes: &[PxBox]) -> Result<Value, String> {
    let (height, width) = (rgb.height as i64, rgb.width as i64);
    if height < 1 || width < 1 {
        return Err("Expected nonempty RGB source".into());
    }
    let mut covered = vec![false; (width * height) as usize];
    for b in boxes {
        let [left, top, right, bottom] = *b;
        if !(0 <= left && left < right && right <= width && 0 <= top && top < bottom && bottom <= height) {
            return Err("Crop bounds outside source".into());
        }
        for y in top..bottom {
            for x in left..right {
                covered[(y * width + x) as usize] = true;
            }
        }
    }
    let (black, corner, levels) = corner_blocks_dark(rgb);
    let fg: Vec<bool> =
        if black { rgb.channel_max().iter().map(|&v| v > 25).collect() } else { rgb.channel_min().iter().map(|&v| v < 245).collect() };
    let residual: Vec<u8> = fg.iter().zip(&covered).map(|(f, c)| (*f && !*c) as u8).collect();
    let cc = cv::connected_components(&residual, rgb.width, rgb.height);
    let minimum = 16i64.max(((width * height) as f64 * 0.0005).ceil() as i64);
    let components: Vec<Value> = cc.stats[1..]
        .iter()
        .filter(|s| s.area >= minimum)
        .map(|s| obj! {"bounds" => vec![s.left, s.top, s.left + s.width, s.top + s.height], "pixels" => s.area})
        .collect();
    let uncovered: i64 = residual.iter().map(|&v| v as i64).sum();
    let requires = !components.is_empty();
    Ok(obj! {
        "algorithm" => "uncovered-nonpaper-components-v2", "source_dimensions" => vec![width, height],
        "paper_polarity" => if black { "black" } else { "light_or_mixed" },
        "corner_size" => corner, "corner_max_rgb_95th_percentiles" => levels,
        "foreground_below" => if black { Value::Null } else { Value::Int(245) },
        "foreground_above" => if black { Value::Int(25) } else { Value::Null },
        "minimum_component_pixels" => minimum,
        "uncovered_nonpaper_pixels" => uncovered, "components" => Value::Array(components),
        "requires_ownership" => requires
    })
}

/// `component_refine.expand_component_boxes`.
pub fn expand_component_boxes(rgb: &Rgb, boxes: &[PxBox]) -> (Vec<PxBox>, Vec<Value>) {
    let (height, width) = (rgb.height as i64, rgb.width as i64);
    let fg = threshold_mask(&rgb.channel_min(), |v| v < 245);
    let cc = cv::connected_components(&fg, rgb.width, rgb.height);
    let mut colored_counts = vec![0i64; cc.count];
    for (i, p) in rgb.data.as_chunks::<3>().0.iter().enumerate() {
        let (mx, mn) = (p[0].max(p[1]).max(p[2]), p[0].min(p[1]).min(p[2]));
        if mx as i32 - mn as i32 >= 20 {
            colored_counts[cc.labels[i] as usize] += 1;
        }
    }
    let mut result: Vec<PxBox> = boxes.to_vec();
    let mut changes = Vec::new();
    for (index, b) in boxes.iter().enumerate() {
        let [left, top, right, bottom] = *b;
        let area = (right - left) * (bottom - top);
        if area <= 0 {
            continue;
        }
        let mut inside = vec![0i64; cc.count];
        // numpy slicing clamps out-of-range bounds.
        let (y0, y1) = (top.clamp(0, height), bottom.clamp(0, height));
        let (x0, x1) = (left.clamp(0, width), right.clamp(0, width));
        for y in y0..y1 {
            for x in x0..x1 {
                inside[cc.labels[(y * width + x) as usize] as usize] += 1;
            }
        }
        let mut candidates = Vec::new();
        for label in 0..cc.count {
            if (inside[label] as f64) < 0.20 * area as f64 || label == 0 {
                continue;
            }
            let s = cc.stats[label];
            let comp_area = s.area;
            if (inside[label] as f64 / comp_area as f64) < 0.98 || (colored_counts[label] as f64 / comp_area as f64) < 0.35 {
                continue;
            }
            let bounds = [s.left, s.top, s.left + s.width, s.top + s.height];
            let expansion =
                [(left - s.left).max(0), (top - s.top).max(0), (s.left + s.width - right).max(0), (s.top + s.height - bottom).max(0)];
            let scales = [width, height, width, height];
            if expansion.iter().all(|&e| e == 0) || (0..4).any(|i| expansion[i] as f64 > 0.02 * scales[i] as f64) {
                continue;
            }
            candidates.push((label, bounds, inside[label] as f64 / comp_area as f64, expansion));
        }
        if candidates.len() != 1 {
            continue;
        }
        let (_, bounds, contained, expansion) = candidates[0];
        let [x, y, rr, bb] = bounds;
        let updated = [
            if expansion[0] != 0 { (x - 3).max(0) } else { left },
            if expansion[1] != 0 { (y - 3).max(0) } else { top },
            if expansion[2] != 0 { (rr + 3).min(width) } else { right },
            if expansion[3] != 0 { (bb + 3).min(height) } else { bottom },
        ];
        result[index] = updated;
        changes.push(obj! {"index" => index, "before" => pxbox(*b), "after" => pxbox(updated),
        "component_bounds" => pxbox(bounds), "component_fraction_inside" => contained,
        "algorithm" => "mostly-enclosed-color-component-v1"});
    }
    (result, changes)
}

/// `viewport_refine.reading_viewports`: returns the padded value and change records.
pub fn reading_viewports(value: &Value, width: i64, height: i64) -> Result<(Value, Vec<Value>), String> {
    if width.min(height) < 1 {
        return Err("Invalid source dimensions".into());
    }
    let mut result = value.clone();
    if value.opt("classification").as_str() != Some("panels") {
        return Ok((result, vec![]));
    }
    let mut changes = Vec::new();
    let page_margin = (width.min(height) as f64 * 0.01).ceil() as i64;
    let panels = result.get_mut("panels").and_then(Value::as_array_mut).ok_or("Invalid panel geometry")?;
    for (index, panel) in panels.iter_mut().enumerate() {
        let b = crate::geometry::box4(panel.opt("box")).ok_or("Invalid panel geometry")?;
        let [top, left, bottom, right] = b;
        if !(0 <= left && left < right && right <= 1000) || !(0 <= top && top < bottom && bottom <= 1000) {
            return Err("Invalid panel geometry".into());
        }
        let px_w = (right - left) as f64 * width as f64 / 1000.0;
        let px_h = (bottom - top) as f64 * height as f64 / 1000.0;
        let dx = page_margin.min(1i64.max((px_w * 0.05).ceil() as i64));
        let dy = page_margin.min(1i64.max((px_h * 0.05).ceil() as i64));
        let nb = [
            0i64.max((top as f64 - dy as f64 * 1000.0 / height as f64).floor() as i64),
            0i64.max((left as f64 - dx as f64 * 1000.0 / width as f64).floor() as i64),
            1000i64.min((bottom as f64 + dy as f64 * 1000.0 / height as f64).ceil() as i64),
            1000i64.min((right as f64 + dx as f64 * 1000.0 / width as f64).ceil() as i64),
        ];
        panel.set("box", nb.to_vec());
        changes.push(obj! {"index" => index, "order" => panel.opt("order").clone(), "before" => vec![top, left, bottom, right],
        "after" => nb.to_vec(), "margin_source_pixels" => arr![dx, dy]});
    }
    Ok((result, changes))
}
