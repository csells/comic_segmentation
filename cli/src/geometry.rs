//! Pure panel-geometry helpers on 0..1000 `[top, left, bottom, right]` boxes.

use crate::json::Value;
use crate::obj;

/// A 4-integer box from a JSON array (bools rejected), else `None`.
pub fn box4(v: &Value) -> Option<[i64; 4]> {
    let a = v.as_array()?;
    if a.len() != 4 {
        return None;
    }
    let mut out = [0i64; 4];
    for (i, n) in a.iter().enumerate() {
        out[i] = n.as_int()?;
    }
    Some(out)
}

pub fn area(b: [i64; 4]) -> i64 {
    (b[2] - b[0]) * (b[3] - b[1])
}

pub fn intersection(a: [i64; 4], b: [i64; 4]) -> i64 {
    (a[2].min(b[2]) - a[0].max(b[0])).max(0) * (a[3].min(b[3]) - a[1].max(b[1])).max(0)
}

fn panel_box(p: &Value) -> [i64; 4] {
    box4(p.opt("box")).unwrap_or([0, 0, 0, 0])
}

fn order(p: &Value) -> i64 {
    p.opt("order").as_int().unwrap_or(0)
}

/// `auto_convert.overlap_risk_pairs`.
pub fn overlap_risk_pairs(panels: &[Value]) -> Vec<[i64; 2]> {
    let mut pairs = Vec::new();
    for (i, a) in panels.iter().enumerate() {
        let ab = panel_box(a);
        let area_a = area(ab);
        for b in &panels[i + 1..] {
            let bb = panel_box(b);
            let area_b = area(bb);
            let overlap = intersection(ab, bb);
            let fraction = overlap as f64 / area_a.min(area_b) as f64;
            if fraction >= 0.10 {
                pairs.push([order(a), order(b)]);
            }
        }
    }
    pairs
}

/// `crossing_art.partial_overlap_pairs`.
pub fn partial_overlap_pairs(panels: &[Value]) -> Vec<[i64; 2]> {
    let mut pairs = Vec::new();
    for (i, a) in panels.iter().enumerate() {
        let ab = panel_box(a);
        for b in &panels[i + 1..] {
            let bb = panel_box(b);
            let smaller = area(ab).min(area(bb));
            let inter = intersection(ab, bb);
            if smaller > 0 {
                let f = inter as f64 / smaller as f64;
                if (0.1..0.95).contains(&f) {
                    pairs.push([order(a), order(b)]);
                }
            }
        }
    }
    pairs
}

/// `inventory_guard.current_regions`.
pub fn current_regions(value: &Value) -> Vec<Value> {
    if value.opt("classification").as_str() == Some("panels") {
        value.opt("panels").as_array().cloned().unwrap_or_default()
    } else {
        vec![obj! {"order" => 1, "box" => vec![0, 0, 1000, 1000]}]
    }
}

/// `inventory_guard.merged_groups`.
pub fn merged_groups(previous: &Value, current: &Value) -> Vec<Value> {
    if previous.opt("classification").as_str() != Some("panels") {
        return vec![];
    }
    let old = previous.opt("panels").as_array().cloned().unwrap_or_default();
    let new = current_regions(current);
    if new.len() >= old.len() {
        return vec![];
    }
    let mut groups: Vec<(i64, Vec<Value>)> = Vec::new();
    for p in &new {
        let o = order(p);
        if !groups.iter().any(|g| g.0 == o) {
            groups.push((o, vec![]));
        }
    }
    for prior in &old {
        let pb = panel_box(prior);
        let iou = |c: &Value| {
            let cb = panel_box(c);
            let overlap = intersection(pb, cb);
            overlap as f64 / (area(pb) + area(cb) - overlap) as f64
        };
        // Python max(): first maximal element.
        let mut best = &new[0];
        let mut best_v = iou(best);
        for c in &new[1..] {
            let v = iou(c);
            if v > best_v {
                best = c;
                best_v = v;
            }
        }
        if intersection(pb, panel_box(best)) as f64 / area(pb) as f64 >= 0.90 {
            let o = order(best);
            if let Some(g) = groups.iter_mut().find(|g| g.0 == o) {
                g.1.push(prior.clone());
            }
        }
    }
    groups
        .into_iter()
        .filter(|g| g.1.len() > 1)
        .map(|(o, panels)| obj! {"current_order" => o, "previous_panels" => Value::Array(panels)})
        .collect()
}

/// `inventory_guard.represented_orders`.
pub fn represented_orders(group: &Value, current: &Value) -> Vec<i64> {
    let boxes: Vec<[i64; 4]> = group.opt("previous_panels").as_array().map(|a| a.iter().map(panel_box).collect()).unwrap_or_default();
    let union = [
        boxes.iter().map(|b| b[0]).min().unwrap_or(0),
        boxes.iter().map(|b| b[1]).min().unwrap_or(0),
        boxes.iter().map(|b| b[2]).max().unwrap_or(0),
        boxes.iter().map(|b| b[3]).max().unwrap_or(0),
    ];
    let mut set = vec![group.opt("current_order").as_int().unwrap_or(0)];
    for p in current_regions(current) {
        if intersection(union, panel_box(&p)) as f64 / area(panel_box(&p)) as f64 >= 0.5 {
            set.push(order(&p));
        }
    }
    set.sort();
    set.dedup();
    set
}

/// `adapter._rectangle`: integer polygon points for a normalized x/y/w/h box.
pub fn rectangle(x: f64, y: f64, w: f64, h: f64, width: i64, height: i64) -> Result<String, String> {
    if ![x, y, w, h].iter().all(|v| v.is_finite()) {
        return Err("non-finite or non-numeric rectangle".into());
    }
    if x < 0.0 || y < 0.0 || w <= 0.0 || h <= 0.0 || x + w > 1.0002 || y + h > 1.0002 {
        return Err("rectangle outside normalized page bounds or non-positive".into());
    }
    let left = (x * width as f64).floor() as i64;
    let top = (y * height as f64).floor() as i64;
    let right = (width - 1).min(((x + w) * width as f64).ceil() as i64);
    let bottom = (height - 1).min(((y + h) * height as f64).ceil() as i64);
    if right <= left || bottom <= top {
        return Err("rectangle collapses at image resolution".into());
    }
    Ok(format!("{left},{top} {right},{top} {right},{bottom} {left},{bottom}"))
}

/// Points of a 0..1000 `[y, x, b, r]` box as `_rectangle` would produce them.
pub fn box_points(b: [i64; 4], width: i64, height: i64) -> Result<String, String> {
    let [y, x, bb, r] = b;
    rectangle(x as f64 / 1000.0, y as f64 / 1000.0, (r - x) as f64 / 1000.0, (bb - y) as f64 / 1000.0, width, height)
}

/// Parse `"l,t r,t r,b l,b"` into four points.
pub fn parse_points(points: &str) -> Result<Vec<(i64, i64)>, String> {
    points
        .split_whitespace()
        .map(|pair| {
            let (a, b) = pair.split_once(',').ok_or("invalid points")?;
            Ok((a.parse::<i64>().map_err(|e| e.to_string())?, b.parse::<i64>().map_err(|e| e.to_string())?))
        })
        .collect()
}

/// `geometry_repair.apply_expansions`: `Ok(None)` when nothing changed.
pub fn apply_expansions(original: &Value, proposed: &Value, issues: &[Value]) -> Result<Option<Value>, String> {
    for k in ["classification", "orientation", "reading_direction"] {
        if original.opt(k) != proposed.opt(k) {
            return Err("repair changed page classification or direction".into());
        }
    }
    let before = original.opt("panels").as_array().cloned().unwrap_or_default();
    let after = proposed.opt("panels").as_array().cloned().unwrap_or_default();
    if before.len() != after.len() {
        return Err("repair changed panel inventory".into());
    }
    let mut targets = Vec::new();
    for issue in issues {
        for n in issue.opt("panels").as_array().cloned().unwrap_or_default() {
            targets.push(n);
        }
    }
    let mut result = original.clone();
    let mut changed = false;
    for (i, (b, a)) in before.iter().zip(after.iter()).enumerate() {
        if b.opt("order") != a.opt("order") {
            return Err("repair changed panel order".into());
        }
        if !targets.contains(b.opt("order")) {
            if b.opt("box") != a.opt("box") {
                return Err("repair changed unflagged panel".into());
            }
            continue;
        }
        let bb = box4(b.opt("box")).ok_or("invalid box")?;
        let ab = box4(a.opt("box")).ok_or("invalid box")?;
        if ab[0] > bb[0] || ab[1] > bb[1] || ab[2] < bb[2] || ab[3] < bb[3] {
            return Err("repair shrank existing content".into());
        }
        let dest = &mut result.get_mut("panels").unwrap().as_array_mut().unwrap()[i];
        dest.set("box", a.opt("box").clone());
        changed |= dest.opt("box") != b.opt("box");
    }
    Ok(if changed { Some(result) } else { None })
}

/// `geometry_repair.clipping_feedback`.
pub fn clipping_feedback(attempt: &Value) -> Vec<Value> {
    let candidate = attempt.opt("candidate");
    let judge = attempt.opt("judge");
    let verifier = attempt.opt("verifier");
    if candidate.opt("invalid").truthy() || candidate.opt("panels").opt("classification").as_str() != Some("panels") {
        return vec![];
    }
    if ["overlap_pairs", "split_flags", "inventory_flags", "structural_error"].iter().any(|k| judge.opt(k).truthy()) {
        return vec![];
    }
    if verifier.opt("route").as_str() != Some("escalate") {
        return vec![];
    }
    let orders: Vec<Value> =
        candidate.opt("panels").opt("panels").as_array().map(|a| a.iter().map(|p| p.opt("order").clone()).collect()).unwrap_or_default();
    let mut issues = Vec::new();
    // Later contextual adjudication for the same target supersedes earlier ones.
    let mut effective: Vec<(String, Value)> = Vec::new();
    for (index, item) in verifier.opt("evidence").as_array().cloned().unwrap_or_default().into_iter().enumerate() {
        let key =
            if item.contains("panel") { format!("target:{}", crate::json::dumps(item.opt("panel"))) } else { format!("global:{index}") };
        if let Some(e) = effective.iter_mut().find(|e| e.0 == key) {
            e.1 = item;
        } else {
            effective.push((key, item));
        }
    }
    for (_, item) in effective {
        let verdict = item.opt("verdict");
        if verdict.opt("route").as_str() == Some("keep") {
            continue;
        }
        let issues_v = verdict.opt("issues");
        if verdict.opt("scene_inventory").as_str() == Some("pass")
            && verdict.opt("reading_order").as_str() == Some("pass")
            && issues_v.truthy()
            && issues_v.as_array().unwrap().iter().all(|i| i.opt("kind").as_str() == Some("uncertain"))
        {
            continue;
        }
        if verdict.opt("decision").as_str() != Some("escalate")
            || verdict.opt("scene_inventory").as_str() != Some("pass")
            || verdict.opt("reading_order").as_str() != Some("pass")
            || !issues_v.truthy()
        {
            return vec![];
        }
        for issue in issues_v.as_array().unwrap() {
            let kind_ok = matches!(issue.opt("kind").as_str(), Some("clipped_art") | Some("clipped_text"));
            let panels = issue.opt("panels");
            let subset = panels.as_array().map(|a| a.iter().all(|n| orders.contains(n))).unwrap_or(false);
            if !kind_ok || !panels.truthy() || !subset || !issue.opt("evidence").truthy() {
                return vec![];
            }
            issues.push(issue.clone());
        }
    }
    issues
}

/// `target_detail.needs_source_detail`.
pub fn needs_source_detail(candidate: &Value, verdict: &Value, target: i64) -> bool {
    candidate.opt("repair_of").truthy()
        && candidate.opt("tier").as_str() == Some("astra")
        && verdict.opt("decision").as_str() == Some("escalate")
        && verdict.opt("scene_inventory").as_str() == Some("pass")
        && verdict.opt("reading_order").as_str() == Some("pass")
        && verdict.opt("issues").truthy()
        && verdict.opt("issues").as_array().unwrap().iter().all(|issue| {
            matches!(issue.opt("kind").as_str(), Some("clipped_art") | Some("clipped_text")) && {
                let mut set: Vec<i64> =
                    issue.opt("panels").as_array().map(|a| a.iter().filter_map(Value::as_int).collect()).unwrap_or_default();
                set.sort();
                set.dedup();
                set == vec![target]
            }
        })
}
