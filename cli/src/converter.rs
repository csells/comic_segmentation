//! Automatic page converter: detection, refinement, quality judgement,
//! verification, repair and completeness hooks.
//!
//! Combines the prototype's `Converter`, `OwnershipConverter` and
//! `MarkedNativeConverter` classes. Methods named `base_*` are the base-class
//! implementations; the unprefixed ones are the most-derived overrides, so
//! call sites resolve exactly as Python's method resolution order does.
//!
//! Candidates and judge verdicts are shared, mutable records (`Shared`):
//! the prototype mutates them after storing them in attempts and history,
//! and page records must show those later mutations.

use crate::acceptance::{self, POLICY};
use crate::bodies;
use crate::client::{ASTRA_TIER_MIN, Client, Kind};
use crate::completeness::{self, Completeness};
use crate::contract;
use crate::error::{Error, R};
use crate::geometry;
use crate::image::{self, Rgb};
use crate::json::{self, Value};
use crate::prompts;
use crate::refine;
use crate::scene_evidence;
use crate::util::{self, read_json, save, sha_file, sha256_hex};
use crate::{arr, obj};
use indexmap::IndexMap;
use std::cell::RefCell;
use std::collections::{BTreeSet, HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::rc::Rc;

pub type Shared = Rc<RefCell<Value>>;

pub fn shared(v: Value) -> Shared {
    Rc::new(RefCell::new(v))
}

const MERGE_OVERLAP: f64 = 0.5;
const MERGE_GROWTH: f64 = 0.05;

pub struct Converter<'a> {
    pub client: &'a Client,
    pub root: PathBuf,
    bundles: HashMap<String, Value>,
    judgments: HashMap<String, Shared>,
    history: IndexMap<String, Vec<Shared>>,
    source_context: HashMap<String, Vec<String>>,
    reading_direction: String,
    reading_margin: bool,
    scene_model: String,
    scene_evidence: HashMap<String, Value>,
    scene_links: HashMap<String, String>,
    source_occlusion: HashMap<String, Value>,
    coverage_risk: HashMap<String, Value>,
    uncovered_sources: HashSet<String>,
    rgb_cache: RefCell<Option<(PathBuf, Rc<Rgb>)>>,
}

fn str_of(v: &Value) -> String {
    v.as_str().unwrap_or("").to_string()
}

fn int_set(v: &Value) -> BTreeSet<i64> {
    v.as_array().map(|a| a.iter().filter_map(Value::as_int).collect()).unwrap_or_default()
}

fn ints(set: &BTreeSet<i64>) -> Value {
    Value::from(set.iter().copied().collect::<Vec<i64>>())
}

/// Python `sorted(set)` of panel orders as a JSON list.
fn panel_orders(value: &Value) -> Vec<i64> {
    value.opt("panels").as_array().map(|a| a.iter().filter_map(|p| p.opt("order").as_int()).collect()).unwrap_or_default()
}

fn images_for_target(bundle: &Value, target: i64) -> Value {
    let label = format!("Candidate crop {target} in reading order");
    let images: Vec<Value> = bundle
        .opt("images")
        .as_array()
        .unwrap()
        .iter()
        .filter(|im| matches!(im.opt("label").as_str(), Some(l) if l == "Original complete page" || l == label))
        .cloned()
        .collect();
    bundle.with("images", Value::Array(images))
}

/// `split_check.source_region`: bounding union of source pixels.
pub fn source_region(source: &Path, panels: &[Value], destination: &Path) -> R<PathBuf> {
    let rgb = image::load_rgb(source)?;
    let (w, h) = (rgb.width as f64, rgb.height as f64);
    let boxes: Vec<[i64; 4]> = panels.iter().map(|p| geometry::box4(p.opt("box")).unwrap_or([0; 4])).collect();
    let bounds = [
        (boxes.iter().map(|b| b[1]).min().unwrap() as f64 * w / 1000.0).floor() as i64,
        (boxes.iter().map(|b| b[0]).min().unwrap() as f64 * h / 1000.0).floor() as i64,
        (boxes.iter().map(|b| b[3]).max().unwrap() as f64 * w / 1000.0).ceil() as i64,
        (boxes.iter().map(|b| b[2]).max().unwrap() as f64 * h / 1000.0).ceil() as i64,
    ];
    if !destination.exists() {
        let data = image::encode_jpeg(&rgb.crop(bounds[0], bounds[1], bounds[2], bounds[3]), 95)?;
        std::fs::write(destination, data)?;
    }
    Ok(destination.to_path_buf())
}

fn write_or_match(path: &Path, data: &[u8], message: &str) -> R<()> {
    if path.exists() {
        if std::fs::read(path)? != data {
            return Err(message.into());
        }
        Ok(())
    } else {
        util::write_new(path, data)
    }
}

/// `target_detail.with_source_detail`.
pub fn with_source_detail(bundle: &Value, target: i64, directory: &Path, mark_boundary: bool) -> R<Value> {
    let images = bundle.opt("images").as_array().ok_or("'images'")?;
    let source = images.iter().find(|im| im.opt("label").as_str() == Some("Original complete page")).ok_or("StopIteration")?;
    let path = PathBuf::from(str_of(source.opt("path")));
    let data = std::fs::read(&path)?;
    if Some(sha256_hex(&data).as_str()) != source.opt("sha256").as_str() {
        return Err("source detail input changed".into());
    }
    let panel = bundle.opt("panels").as_array().unwrap().iter().find(|p| p.opt("order").as_int() == Some(target)).ok_or("StopIteration")?;
    let [y, x, bottom, right] = geometry::box4(panel.opt("box")).ok_or("invalid box")?;
    let rgb = match image::sniff_format(&data) {
        Some("JPEG") => image::decode_jpeg(&data)?,
        _ => image::load_rgb(&path)?,
    };
    let (width, height) = (rgb.width as i64, rgb.height as i64);
    let margin_x = 64i64.max((width as f64 * 0.06).ceil() as i64);
    let margin_y = 64i64.max((height as f64 * 0.06).ceil() as i64);
    let bounds = [
        0i64.max((x as f64 * width as f64 / 1000.0).floor() as i64 - margin_x),
        0i64.max((y as f64 * height as f64 / 1000.0).floor() as i64 - margin_y),
        width.min((right as f64 * width as f64 / 1000.0).ceil() as i64 + margin_x),
        height.min((bottom as f64 * height as f64 / 1000.0).ceil() as i64 + margin_y),
    ];
    let mut detail = rgb.crop(bounds[0], bounds[1], bounds[2], bounds[3]);
    let scale = 2f64.min(1600.0 / detail.width.max(detail.height) as f64);
    if scale != 1.0 {
        let nw = 1i64.max(crate::cv::py_round(detail.width as f64 * scale)) as usize;
        let nh = 1i64.max(crate::cv::py_round(detail.height as f64 * scale)) as usize;
        if (nw, nh) != (detail.width, detail.height) {
            detail = image::resize_lanczos(&detail, nw, nh);
        }
    }
    std::fs::create_dir_all(directory)?;
    let destination = directory.join(format!("target-{target}-source-detail-v1.jpg"));
    let encoded = image::encode_jpeg(&detail, 95)?;
    write_or_match(&destination, &encoded, "existing source detail differs; use a new evidence directory")?;
    let label = format!("Candidate crop {target} in reading order");
    let mut out_images: Vec<Value> = images
        .iter()
        .filter(|im| matches!(im.opt("label").as_str(), Some(l) if l == "Original complete page" || l == label))
        .cloned()
        .collect();
    if out_images.len() != 2 {
        return Err("expected original source and one actual target crop".into());
    }
    out_images.push(obj! {"label" => format!("Unannotated source detail around target {target}; includes neighboring scenes. Original pixel bounds left/top/right/bottom={}; full source size={width}x{height}. This is source context, not another candidate crop.", json::py_int_list(&bounds)),
        "path" => util::path_str(&destination), "sha256" => sha_file(&destination)?});
    if mark_boundary {
        let crop = out_images[1].clone();
        let points = geometry::parse_points(crop.opt("points").as_str().ok_or("'points'")?)?;
        let (left, top) = points[0];
        let (r, b) = points[2];
        if points != vec![(left, top), (r, top), (r, b), (left, b)] {
            return Err("expected actual rectangular crop points".into());
        }
        let actual = image::image_size(Path::new(&str_of(crop.opt("path"))))?;
        if actual != ((r - left + 1) as usize, (b - top + 1) as usize) {
            return Err("crop points and actual image dimensions differ".into());
        }
        let sx = detail.width as f64 / (bounds[2] - bounds[0]) as f64;
        let sy = detail.height as f64 / (bounds[3] - bounds[1]) as f64;
        let rect = [
            crate::cv::py_round((left - bounds[0]) as f64 * sx),
            crate::cv::py_round((top - bounds[1]) as f64 * sy),
            crate::cv::py_round((r + 1 - bounds[0]) as f64 * sx),
            crate::cv::py_round((b + 1 - bounds[1]) as f64 * sy),
        ];
        let mut marked = detail.clone();
        image::draw_rectangle_outline(&mut marked, rect[0], rect[1], rect[2], rect[3], [255, 0, 0], 2);
        let data = image::encode_jpeg(&marked, 95)?;
        let marked_path = directory.join(format!("target-{target}-crop-boundary-v2.jpg"));
        write_or_match(&marked_path, &data, "existing boundary detail differs")?;
        out_images.push(obj! {"label" => format!("Same source detail with a generated RED rectangle marking the exact actual crop extent for target {target}. Outside the rectangle is excluded from the crop. The red line is NOT an artist-drawn panel border. Actual crop pixel bounds left/top/right-exclusive/bottom-exclusive={}. Refer to the preceding unmarked detail wherever the line obscures artwork.", json::py_int_list(&[left, top, r + 1, b + 1])),
            "path" => util::path_str(&marked_path), "sha256" => sha256_hex(&data)});
    }
    Ok(bundle.with("images", Value::Array(out_images)))
}

impl<'a> Converter<'a> {
    pub fn new(
        client: &'a Client,
        root: &Path,
        source_context: HashMap<String, Vec<String>>,
        reading_direction: &str,
        reading_margin: bool,
    ) -> R<Converter<'a>> {
        if !matches!(reading_direction, "ltr" | "rtl" | "auto") {
            return Err("Invalid reading direction".into());
        }
        Ok(Converter {
            client,
            root: root.to_path_buf(),
            bundles: HashMap::new(),
            judgments: HashMap::new(),
            history: IndexMap::new(),
            source_context,
            reading_direction: reading_direction.to_string(),
            reading_margin,
            scene_model: "gpt-6-astra".into(),
            scene_evidence: HashMap::new(),
            scene_links: HashMap::new(),
            source_occlusion: HashMap::new(),
            coverage_risk: HashMap::new(),
            uncovered_sources: HashSet::new(),
            rgb_cache: RefCell::new(None),
        })
    }

    fn page_rgb(&self, page: &Path) -> R<Rc<Rgb>> {
        if let Some((p, rgb)) = self.rgb_cache.borrow().as_ref()
            && p == page
        {
            return Ok(rgb.clone());
        }
        let rgb = Rc::new(image::load_rgb(page)?);
        *self.rgb_cache.borrow_mut() = Some((page.to_path_buf(), rgb.clone()));
        Ok(rgb)
    }

    pub fn bundle(&self, identity: &str) -> R<&Value> {
        self.bundles.get(identity).ok_or_else(|| Error::Value(format!("'{identity}'")))
    }

    /// Canonical bundle without transient ownership hypotheses.
    fn canonical_bundle(&self, identity: &str) -> R<Value> {
        let mut b = self.bundle(identity)?.clone();
        b.remove("_ownership_hypotheses");
        Ok(b)
    }

    fn responses_with_output_recovery(&self, request: &Value, kind: Kind) -> R<(Value, Value)> {
        let (raw, provenance) = self.client.request("responses", request, kind)?;
        let limit = request.opt("max_output_tokens").as_int();
        if matches!(limit, Some(4096 | 8192)) && contract::responses_output_exhausted(&raw) {
            let limit = limit.unwrap();
            let recovery = obj! {"original_request" => provenance.clone(), "original_status" => raw.opt("status").clone(),
            "incomplete_details" => raw.opt("incomplete_details").clone(), "original_output_limit" => limit, "expanded_output_limit" => limit * 2};
            let expanded = request.with("max_output_tokens", limit * 2);
            let (raw, provenance) = self.client.request("responses", &expanded, kind)?;
            return Ok((raw, provenance.with("output_limit_recovery", recovery)));
        }
        Ok((raw, provenance))
    }

    // ------------------------------------------------------------ detection

    pub fn detect(&self, page: &Path, tier: &str) -> R<Value> {
        if tier == "astra"
            && let Some(remaining) = self.client.page_remaining()
            && remaining < ASTRA_TIER_MIN
        {
            return Err(Error::PageBudget(format!("page budget too low to start the Astra tier: {remaining} micro-USD left")));
        }
        let data = std::fs::read(page)?;
        let request = bodies::detector(&data, tier, &self.reading_direction);
        let (raw, provenance) = self.responses_with_output_recovery(&request, Kind::Detector)?;
        let parsed = contract::response_panels(&raw, &self.reading_direction).and_then(|p| {
            if self.reading_direction != "auto" && p.opt("reading_direction").as_str() != Some(self.reading_direction.as_str()) {
                Err("Detector contradicted the requested reading direction".to_string())
            } else {
                Ok(p)
            }
        });
        Ok(match parsed {
            Ok(panels) => obj! {"panels" => panels, "detector" => provenance, "tier" => tier, "source_sha256" => sha_file(page)?},
            Err(e) => obj! {"invalid" => e, "detector" => provenance, "tier" => tier},
        })
    }

    fn repair_request_body(&self, bundle: &Value, issues: &[Value]) -> R<Value> {
        let mut body = bodies::repair(bundle, issues)?;
        let prompt = &mut body.get_mut("input").unwrap().as_array_mut().unwrap()[0].get_mut("content").unwrap().as_array_mut().unwrap()[0];
        let rich = rich_prompt(bundle, prompt.opt("text").as_str().unwrap_or(""));
        prompt.set("text", rich);
        Ok(body)
    }

    pub fn completeness_redetect(&self, page: &Path, attempt: &Value) -> R<Option<Value>> {
        let previous = attempt.opt("candidate").clone();
        let prepared = (|| -> R<Option<(Value, Value)>> {
            let findings = completeness::missing_feedback(page, &previous, attempt.opt("completeness"))?;
            let Some(findings) = findings else { return Ok(None) };
            let saved = read_json(Path::new(&str_of(previous.opt("bundle"))))?;
            let live = self.canonical_bundle(&str_of(previous.opt("identity")))?;
            if live != saved {
                return Err("Live redetection bundle differs from saved bundle".into());
            }
            Ok(Some((findings, saved)))
        })()
        .map_err(|e| e.block("Invalid completeness repair feedback: "))?;
        let Some((findings, saved)) = prepared else { return Ok(None) };
        let request = bodies::redetection(&saved, &self.reading_direction, &findings)?;
        let (raw, record) = self.responses_with_output_recovery(&request, Kind::Detector)?;
        let provenance = obj! {"tier" => "astra", "source_sha256" => sha_file(page)?, "detector" => record,
        "completeness_redetection_of" => previous.opt("identity").clone(),
        "completeness_rejection_proof" => attempt.opt("completeness").opt("proof").clone(),
        "completeness_feedback_sha256" => util::json_hash(&findings)};
        Ok(Some(match contract::response_panels(&raw, &self.reading_direction) {
            Ok(panels) => provenance.with("panels", panels),
            Err(e) => provenance.with("invalid", e),
        }))
    }

    pub fn completeness_merge(&self, page: &Path, attempt: &Value) -> R<Option<Value>> {
        let previous = attempt.opt("candidate").clone();
        let findings = (|| -> R<Option<Value>> {
            let findings = completeness::extra_feedback(page, &previous, attempt.opt("completeness"))?;
            let Some(findings) = findings else { return Ok(None) };
            let saved = read_json(Path::new(&str_of(previous.opt("bundle"))))?;
            let live = self.canonical_bundle(&str_of(previous.opt("identity")))?;
            if live != saved {
                return Err("Live merge bundle differs from saved bundle".into());
            }
            Ok(Some(findings))
        })()
        .map_err(|e| e.block("Invalid completeness merge feedback: "))?;
        let Some(findings) = findings else { return Ok(None) };
        let panels_list = previous.opt("panels").opt("panels").as_array().cloned().unwrap_or_default();
        let by_order: IndexMap<i64, Value> = panels_list.iter().map(|p| (p.opt("order").as_int().unwrap(), p.clone())).collect();
        let bx = |o: i64| geometry::box4(by_order[&o].opt("box")).unwrap();
        let area = |b: [i64; 4]| (b[2] - b[0]).max(0) * (b[3] - b[1]).max(0);
        let overlap = |a: [i64; 4], b: [i64; 4]| (a[2].min(b[2]) - a[0].max(b[0])).max(0) * (a[3].min(b[3]) - a[1].max(b[1])).max(0);
        let referenced: Vec<i64> = findings.opt("referenced").as_array().unwrap().iter().filter_map(Value::as_int).collect();
        let unreferenced: Vec<i64> = findings.opt("unreferenced").as_array().unwrap().iter().filter_map(Value::as_int).collect();
        let mut merged: IndexMap<i64, Value> = referenced.iter().map(|o| (*o, by_order[o].clone())).collect();
        for order in &unreferenced {
            let b = bx(*order);
            // Python max(): first maximal key in insertion order.
            let mut target = *merged.keys().next().unwrap();
            let mut best = overlap(b, bx(target));
            for k in merged.keys().skip(1) {
                let v = overlap(b, bx(*k));
                if v > best {
                    best = v;
                    target = *k;
                }
            }
            if area(b) == 0 || overlap(b, bx(target)) as f64 / area(b) as f64 * 1.0 < MERGE_OVERLAP {
                return Ok(None);
            }
            let t = geometry::box4(merged[&target].opt("box")).unwrap();
            merged[&target].set("box", vec![t[0].min(b[0]), t[1].min(b[1]), t[2].max(b[2]), t[3].max(b[3])]);
        }
        let keys: Vec<i64> = merged.keys().copied().collect();
        for grown in &keys {
            for other in &keys {
                if other != grown {
                    let g = geometry::box4(merged[grown].opt("box")).unwrap();
                    let o = geometry::box4(merged[other].opt("box")).unwrap();
                    if (overlap(g, o) - overlap(bx(*grown), bx(*other))) as f64 > MERGE_GROWTH * area(bx(*other)) as f64 {
                        return Ok(None);
                    }
                }
            }
        }
        let mut kept: Vec<Value> = referenced.iter().map(|o| merged[o].clone()).collect();
        for (i, p) in kept.iter_mut().enumerate() {
            p.set("order", i as i64 + 1);
        }
        let value = previous.opt("panels").with("panels", Value::Array(kept));
        Ok(Some(obj! {"tier" => "astra", "source_sha256" => sha_file(page)?, "completeness_merge_of" => previous.opt("identity").clone(),
        "completeness_rejection_proof" => attempt.opt("completeness").opt("proof").clone(),
        "merged_orders" => unreferenced, "viewport_padding_applied" => previous.get("viewport_padding_applied").cloned().unwrap_or(Value::Bool(false)),
        "panels" => value}))
    }

    pub fn repair(&self, page: &Path, attempt: &Value) -> R<Option<Value>> {
        let issues = geometry::clipping_feedback(attempt);
        if issues.is_empty() {
            return Ok(None);
        }
        let previous = attempt.opt("candidate");
        let bundle = self.bundle(&str_of(previous.opt("identity")))?;
        let body = self.repair_request_body(bundle, &issues)?;
        let (raw, request) = self.client.request("responses", &body, Kind::Detector)?;
        let provenance = obj! {"tier" => "astra", "source_sha256" => sha_file(page)?, "detector" => request,
        "repair_of" => previous.opt("identity").clone(), "repair_issues" => Value::Array(issues.clone()),
        "viewport_padding_applied" => previous.get("viewport_padding_applied").cloned().unwrap_or(Value::Bool(false))};
        let direction = str_of(previous.opt("panels").opt("reading_direction"));
        let applied =
            contract::response_panels(&raw, &direction).and_then(|p| geometry::apply_expansions(previous.opt("panels"), &p, &issues));
        Ok(Some(match applied {
            Ok(panels) => {
                let changed = panels.is_some();
                provenance.with("panels", panels.unwrap_or_else(|| previous.opt("panels").clone())).with("repair_changed", changed)
            }
            Err(e) => provenance.with("invalid", e),
        }))
    }

    pub fn pixel_repair(&self, page: &Path, attempt: &Value) -> R<Option<Value>> {
        let issues = geometry::clipping_feedback(attempt);
        if issues.is_empty() {
            return Ok(None);
        }
        let previous = attempt.opt("candidate");
        let bundle = self.bundle(&str_of(previous.opt("identity")))?;
        let targets: BTreeSet<i64> = issues.iter().flat_map(|i| int_set(i.opt("panels"))).collect();
        let rgb = self.page_rgb(page)?;
        let (height, width) = (rgb.height as i64, rgb.width as i64);
        let mut boxes = Vec::new();
        for im in &bundle.opt("images").as_array().unwrap()[1..] {
            let points = geometry::parse_points(im.opt("points").as_str().ok_or("'points'")?)?;
            boxes.push([points[0].0, points[0].1, points[2].0 + 1, points[2].1 + 1]);
        }
        let (updated, changes) = refine::expand_component_boxes(&rgb, &boxes);
        let panels = previous.opt("panels").opt("panels").as_array().unwrap();
        let order_of = |c: &Value| panels[c.opt("index").as_int().unwrap() as usize].opt("order").as_int().unwrap();
        let changes: Vec<Value> = changes.into_iter().filter(|c| targets.contains(&order_of(c))).collect();
        let changed: BTreeSet<i64> = changes.iter().map(order_of).collect();
        if changed != targets {
            return Ok(None);
        }
        let mut proposed = previous.opt("panels").clone();
        for change in &changes {
            let index = change.opt("index").as_int().unwrap() as usize;
            let [left, top, right, bottom] = updated[index];
            let p = &mut proposed.get_mut("panels").unwrap().as_array_mut().unwrap()[index];
            let old = geometry::box4(p.opt("box")).unwrap();
            let before = boxes[index];
            let nb = [
                if top < before[1] { old[0].min((top as f64 * 1000.0 / height as f64).floor() as i64) } else { old[0] },
                if left < before[0] { old[1].min((left as f64 * 1000.0 / width as f64).floor() as i64) } else { old[1] },
                if bottom > before[3] { old[2].max((bottom as f64 * 1000.0 / height as f64).ceil() as i64) } else { old[2] },
                if right > before[2] { old[3].max((right as f64 * 1000.0 / width as f64).ceil() as i64) } else { old[3] },
            ];
            p.set("box", nb.to_vec());
        }
        let Some(applied) = geometry::apply_expansions(previous.opt("panels"), &proposed, &issues)? else { return Ok(None) };
        Ok(Some(obj! {"tier" => "astra", "source_sha256" => sha_file(page)?, "detector" => previous.opt("detector").clone(),
        "panels" => applied, "repair_of" => previous.opt("identity").clone(), "repair_issues" => Value::Array(issues),
        "repair_changed" => true, "component_changes" => Value::Array(changes),
        "viewport_padding_applied" => previous.get("viewport_padding_applied").cloned().unwrap_or(Value::Bool(false))}))
    }

    // ------------------------------------------------------------ refinement

    /// `Converter.refine`: returns a shared candidate (or the invalid raw value).
    pub fn refine(&mut self, page: &Path, candidate: &Value) -> R<Shared> {
        if candidate.opt("invalid").truthy() {
            return Ok(shared(candidate.clone()));
        }
        let mut value = candidate.opt("panels").clone();
        let rgb = self.page_rgb(page)?;
        let (h, w) = (rgb.height as i64, rgb.width as i64);
        let panels = value.opt("panels").as_array().cloned().unwrap_or_default();
        let boxes: Vec<[i64; 4]> = panels
            .iter()
            .map(|p| {
                let b = geometry::box4(p.opt("box")).unwrap();
                [
                    crate::cv::py_round(b[1] as f64 * w as f64 / 1000.0),
                    crate::cv::py_round(b[0] as f64 * h as f64 / 1000.0),
                    crate::cv::py_round(b[3] as f64 * w as f64 / 1000.0),
                    crate::cv::py_round(b[2] as f64 * h as f64 / 1000.0),
                ]
            })
            .collect();
        let is_panels = value.opt("classification").as_str() == Some("panels");
        let (mut refined, mut changes) = if is_panels { refine::expand_dark_gutter_boxes(&rgb, &boxes) } else { (boxes.clone(), vec![]) };
        if is_panels {
            for f in [refine::expand_balloon_boxes, refine::expand_frame_boxes, refine::expand_dark_fringe_boxes] {
                let (r, c) = f(&rgb, &refined);
                refined = r;
                changes.extend(c);
            }
        }
        for change in &changes {
            let i = change.opt("index").as_int().unwrap() as usize;
            let [l, t, r, b] = refined[i];
            let p = &mut value.get_mut("panels").unwrap().as_array_mut().unwrap()[i];
            let old = geometry::box4(p.opt("box")).unwrap();
            let n = [
                (t as f64 * 1000.0 / h as f64).floor() as i64,
                (l as f64 * 1000.0 / w as f64).floor() as i64,
                (b as f64 * 1000.0 / h as f64).ceil() as i64,
                (r as f64 * 1000.0 / w as f64).ceil() as i64,
            ];
            p.set("box", vec![old[0].min(n[0]), old[1].min(n[1]), old[2].max(n[2]), old[3].max(n[3])]);
        }
        let mut margin_changes = vec![];
        if self.reading_margin && !candidate.opt("viewport_padding_applied").truthy() {
            let (v, m) = refine::reading_viewports(&value, w, h)?;
            value = v;
            margin_changes = m;
        }
        contract::validate_page(&value, &self.reading_direction)?;
        let page_sha = sha_file(page)?;
        let identity = sha256_hex(format!("{page_sha}{}{POLICY}", json::dumps_sorted(&value)).as_bytes());
        let directory = self.root.join("candidates").join(&identity);
        std::fs::create_dir_all(&directory)?;
        let mut bundle = value.pick(&["classification", "reading_direction"])?;
        bundle.set(
            "panels",
            Value::Array(
                value
                    .opt("panels")
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|p| obj! {"order" => p.opt("order").clone(), "box" => p.opt("box").clone()})
                    .collect(),
            ),
        );
        let mut images =
            vec![obj! {"label" => "Original complete page", "path" => util::path_str(&util::resolve(page)), "sha256" => page_sha.as_str()}];
        if value.opt("classification").as_str() == Some("panels") {
            for p in value.opt("panels").as_array().unwrap() {
                let points = geometry::box_points(geometry::box4(p.opt("box")).unwrap(), w, h)?;
                let coords = geometry::parse_points(&points)?;
                let (l, t) = coords[0];
                let (rr, bb) = coords[2];
                let order = p.opt("order").as_int().unwrap();
                let crop = directory.join(format!("crop-{order:02}.jpg"));
                if !crop.exists() {
                    std::fs::write(&crop, image::encode_jpeg(&rgb.crop(l, t, rr + 1, bb + 1), 95)?)?;
                }
                images.push(obj! {"label" => format!("Candidate crop {order} in reading order"), "path" => util::path_str(&crop), "sha256" => sha_file(&crop)?, "points" => points});
            }
        }
        bundle.set("images", Value::Array(images));
        self.bundles.insert(identity.clone(), bundle.clone());
        if !directory.join("bundle.json").exists() {
            save(&directory.join("bundle.json"), &bundle)?;
        }
        let mut all_changes: Vec<Value> = candidate.opt("component_changes").as_array().cloned().unwrap_or_default();
        all_changes.extend(changes);
        all_changes.extend(margin_changes.iter().map(|c| c.with("kind", "reading-viewport-margin")));
        let padding = !margin_changes.is_empty() || candidate.get("viewport_padding_applied").map(Value::truthy).unwrap_or(false);
        let padding_value = if !margin_changes.is_empty() {
            Value::Bool(true)
        } else {
            candidate.get("viewport_padding_applied").cloned().unwrap_or(Value::Bool(false))
        };
        let _ = padding;
        let result = candidate
            .with("source_sha256", page_sha.as_str())
            .with("panels", value)
            .with("identity", identity.as_str())
            .with("refinement_changes", Value::Array(all_changes))
            .with("viewport_padding_applied", padding_value)
            .with("bundle", util::path_str(&directory.join("bundle.json")));
        let result = shared(result);
        self.history.entry(page_sha).or_default().push(result.clone());
        Ok(result)
    }

    // ------------------------------------------------------------ native decisions

    fn decision(&self, bundle: &Value, prompt: &str, questions: &Value) -> R<(Value, Value)> {
        decision(self.client, &self.root, bundle, prompt, questions)
    }

    // ------------------------------------------------------------ judge

    fn check_splits(&self, candidate: &Value) -> R<Value> {
        let bundle = self.bundle(&str_of(candidate.opt("identity")))?.clone();
        if bundle.opt("classification").as_str() != Some("panels") {
            return Ok(obj! {"flags" => arr![], "checks" => arr![]});
        }
        let mut panels = bundle.opt("panels").as_array().cloned().unwrap();
        panels.sort_by_key(|p| p.opt("order").as_int().unwrap_or(0));
        let directory = PathBuf::from(str_of(candidate.opt("bundle"))).parent().unwrap().to_path_buf();
        let source = str_of(bundle.opt("images").as_array().unwrap()[0].opt("path"));
        let (mut checks, mut flags) = (vec![], vec![]);
        for pair in panels.windows(2) {
            let orders = [pair[0].opt("order").as_int().unwrap(), pair[1].opt("order").as_int().unwrap()];
            let region = source_region(Path::new(&source), pair, &directory.join(format!("split-region-{}-{}.jpg", orders[0], orders[1])))?;
            let (raw, request) = self.client.request("decisions", &bodies::split(&region)?, Kind::Native)?;
            let answer = contract::parse_answers(&raw, &arr![prompts::false_split_question()]).map_err(Error::Blocked)?;
            let probability = answer.opt("probabilities").opt("false_split").clone();
            let mut check = obj! {"pair" => orders.to_vec(), "probability" => probability.clone(), "request" => request};
            let mut flagged = probability.as_f64().unwrap_or(0.0) >= 0.5;
            if flagged && candidate.opt("tier").as_str() == Some("astra") {
                let (raw, secondary_request) = self.responses_with_output_recovery(&bodies::continuity(&region)?, Kind::Verifier)?;
                let secondary = contract::continuity_verdict(&raw).map_err(Error::Blocked)?;
                flagged = secondary.opt("classification").as_str() != Some("distinct");
                check.set("final_tier_disambiguation", obj! {"verdict" => secondary, "request" => secondary_request});
                let predecessors =
                    self.source_context.get(&util::path_str(&util::resolve(Path::new(&source)))).cloned().unwrap_or_default();
                if flagged && !predecessors.is_empty() {
                    let (raw, context_request) =
                        self.responses_with_output_recovery(&bodies::narrative_context(&predecessors, &source, &region)?, Kind::Verifier)?;
                    let context = contract::continuity_verdict(&raw).map_err(Error::Blocked)?;
                    flagged = context.opt("classification").as_str() != Some("distinct");
                    let pages: Vec<Value> = predecessors
                        .iter()
                        .map(|p| Ok(obj! {"path" => p.as_str(), "sha256" => sha_file(Path::new(p))?}))
                        .collect::<R<_>>()?;
                    check.set(
                        "preceding_page_disambiguation",
                        obj! {"verdict" => context, "request" => context_request, "source_pages" => Value::Array(pages)},
                    );
                }
            }
            checks.push(check);
            if flagged {
                flags.push(Value::from(orders.to_vec()));
            }
        }
        Ok(obj! {"flags" => Value::Array(flags), "checks" => Value::Array(checks)})
    }

    fn base_check_inventory(&self, candidate: &Value) -> R<Value> {
        let (mut checks, mut flags): (Vec<Value>, BTreeSet<i64>) = (vec![], BTreeSet::new());
        let mut seen = HashSet::new();
        let identity = str_of(candidate.opt("identity"));
        let current = if candidate.contains("panels") { candidate.opt("panels").clone() } else { self.bundle(&identity)?.clone() };
        let earlier: Vec<Value> = self
            .history
            .get(&str_of(candidate.opt("source_sha256")))
            .map(|h| h.iter().map(|c| c.borrow().clone()).filter(|p| str_of(p.opt("identity")) != identity).collect())
            .unwrap_or_default();
        // Largest earlier inventory; ties prefer the later tier.
        let reference = earlier
            .iter()
            .enumerate()
            .max_by_key(|(i, p)| (p.opt("panels").opt("panels").as_array().map(Vec::len).unwrap_or(0), *i))
            .map(|(_, p)| p.clone());
        let bundle = self.bundle(&identity)?.clone();
        let source = str_of(bundle.opt("images").as_array().unwrap()[0].opt("path"));
        if let Some(previous) = reference {
            for group in geometry::merged_groups(previous.opt("panels"), &current) {
                let signature = json::dumps_sorted(&group);
                if !seen.insert(signature.clone()) {
                    continue;
                }
                let directory = PathBuf::from(str_of(candidate.opt("bundle"))).parent().unwrap().to_path_buf();
                let region = source_region(
                    Path::new(&source),
                    group.opt("previous_panels").as_array().unwrap(),
                    &directory.join(format!("inventory-{}.jpg", sha256_hex(signature.as_bytes()))),
                )?;
                let (raw, request) = self.responses_with_output_recovery(&bodies::continuity(&region)?, Kind::Verifier)?;
                let mut verdict = contract::continuity_verdict(&raw).map_err(Error::Blocked)?;
                let mut check = obj! {"previous_tier" => previous.opt("tier").clone(), "group" => group.clone(), "source_verdict" => verdict.clone(), "source_request" => request};
                let represented = geometry::represented_orders(&group, &current);
                check.set("represented_current_orders", represented.clone());
                if verdict.opt("classification").as_str() != Some("continuous") {
                    let body = bodies::inventory_context(&source, &region)?;
                    let (raw, context_request) = self.responses_with_output_recovery(&body, Kind::Verifier)?;
                    verdict = contract::continuity_verdict(&raw).map_err(Error::Blocked)?;
                    check.set("context_verdict", verdict.clone());
                    check.set("context_request", context_request);
                }
                checks.push(check);
                if verdict.opt("classification").as_str() == Some("uncertain")
                    || verdict.opt("views").as_array().map(Vec::len).unwrap_or(0) > represented.len()
                {
                    flags.insert(group.opt("current_order").as_int().unwrap());
                }
            }
        }
        Ok(obj! {"flags" => ints(&flags), "checks" => Value::Array(checks)})
    }

    /// `OwnershipConverter.check_inventory`.
    fn check_inventory(&self, candidate: &Value) -> R<Value> {
        let inventory = self.base_check_inventory(candidate)?;
        if !inventory.opt("flags").truthy() || candidate.opt("tier").as_str() != Some("astra") {
            return Ok(inventory);
        }
        let identity = str_of(candidate.opt("identity"));
        let source = PathBuf::from(str_of(self.bundle(&identity)?.opt("images").as_array().unwrap()[0].opt("path")));
        let guard = Completeness::new(self.client, &self.root.join("inventory-adjudication"), "inventory-disagreement")?;
        let resolution = (|| -> R<Value> {
            let canonical = self.canonical_bundle(&identity)?;
            let saved = read_json(Path::new(&str_of(candidate.opt("bundle"))))?;
            if canonical != saved {
                return Err("Live candidate bundle differs from saved bundle".into());
            }
            let resolution = guard.check(&source, &saved, candidate)?;
            if resolution.opt("route").as_str() == Some("keep") {
                acceptance::validate_acceptance(&source, candidate, &resolution, "inventory-disagreement")?;
            }
            Ok(resolution)
        })()
        .map_err(|e| e.block("Invalid inventory adjudication proof: "))?;
        let keep = resolution.opt("route").as_str() == Some("keep");
        let mut checks = inventory.opt("checks").as_array().cloned().unwrap_or_default();
        checks.push(obj! {"scope" => "final-tier independent source inventory adjudication", "original_flags" => inventory.opt("flags").clone(), "resolution" => resolution});
        Ok(obj! {"flags" => if keep { arr![] } else { inventory.opt("flags").clone() }, "checks" => Value::Array(checks)})
    }

    fn check_crossing_art(&self, bundle: &Value) -> R<Value> {
        let pairs = if bundle.opt("classification").as_str() == Some("panels") {
            geometry::partial_overlap_pairs(bundle.opt("panels").as_array().unwrap())
        } else {
            vec![]
        };
        if pairs.is_empty() {
            return Ok(obj! {"pairs" => arr![], "targets" => arr![]});
        }
        let source = str_of(bundle.opt("images").as_array().unwrap()[0].opt("path"));
        let (raw, request) = self.client.request("decisions", &bodies::crossing_art(&source)?, Kind::Native)?;
        let probability = contract::parse_answers(&raw, &prompts::crossing_art_questions())
            .map_err(Error::Blocked)?
            .opt("probabilities")
            .opt("crossing_art")
            .clone();
        let targets: BTreeSet<i64> = if probability.as_f64().unwrap_or(0.0) >= prompts::CROSSING_ART_THRESHOLD {
            pairs.iter().flatten().copied().collect()
        } else {
            BTreeSet::new()
        };
        Ok(obj! {"pairs" => Value::Array(pairs.iter().map(|p| Value::from(p.to_vec())).collect()), "targets" => ints(&targets),
        "probability" => probability, "threshold" => prompts::CROSSING_ART_THRESHOLD, "request" => request})
    }

    fn workers(&self) -> usize {
        let available = (self.client.budget_cap() - self.client.budget_used()) as f64 / 1e6;
        1i64.max(3i64.min((available - 0.3) as i64)) as usize
    }

    fn quality_route(global: &Value, targets: &IndexMap<i64, Value>) -> Value {
        let semantic: Vec<&str> =
            ["scene_defect", "order_defect"].into_iter().filter(|n| global.opt(n).as_f64().unwrap_or(0.0) >= 0.5).collect();
        let crops: Vec<&str> =
            ["text_clipping", "art_clipping"].into_iter().filter(|n| global.get(n).and_then(Value::as_f64).unwrap_or(0.0) >= 0.5).collect();
        let flagged: Vec<i64> = targets
            .iter()
            .filter(|(_, p)| p.as_object().unwrap().values().filter_map(Value::as_f64).fold(f64::NEG_INFINITY, f64::max) >= 0.5)
            .map(|(n, _)| *n)
            .collect();
        let escalate = !semantic.is_empty() || !crops.is_empty() || !flagged.is_empty();
        obj! {"route" => if escalate { "escalate" } else { "keep" }, "semantic_flags" => semantic, "global_crop_flags" => crops, "target_flags" => flagged}
    }

    /// Base `Converter.judge`.
    fn base_judge(&mut self, candidate: &Value) -> R<Shared> {
        if candidate.opt("invalid").truthy() {
            return Ok(shared(obj! {"route" => "escalate", "structural_error" => candidate.opt("invalid").clone()}));
        }
        let identity = str_of(candidate.opt("identity"));
        let bundle = self.bundle(&identity)?.clone();
        let prompt = prompts::DECISIONS;
        let overlap_pairs = if candidate.opt("tier").as_str() == Some("sol-low") && bundle.opt("classification").as_str() == Some("panels")
        {
            geometry::overlap_risk_pairs(bundle.opt("panels").as_array().unwrap())
        } else {
            vec![]
        };
        let store = |this: &mut Self, v: Value| -> Shared {
            let s = shared(v);
            this.judgments.insert(identity.clone(), s.clone());
            s
        };
        if !overlap_pairs.is_empty() {
            let v = obj! {"route" => "escalate", "overlap_pairs" => Value::Array(overlap_pairs.iter().map(|p| Value::from(p.to_vec())).collect()),
            "reason" => "overlapping or contained scenes require stronger boundary and scene detection",
            "semantic_flags" => arr![], "global_crop_flags" => arr![], "target_flags" => arr![]};
            return Ok(store(self, v));
        }
        let inventory = self.check_inventory(candidate)?;
        if inventory.opt("flags").truthy() {
            let v = obj! {"route" => "escalate", "inventory_flags" => inventory.opt("flags").clone(), "inventory_checks" => inventory.opt("checks").clone(),
            "reason" => "a stronger candidate lost a previously proposed narrative view",
            "semantic_flags" => arr![], "global_crop_flags" => arr![], "target_flags" => arr![]};
            return Ok(store(self, v));
        }
        let splits = self.check_splits(candidate)?;
        if splits.opt("flags").truthy() {
            let v = obj! {"route" => "escalate", "split_flags" => splits.opt("flags").clone(), "split_checks" => splits.opt("checks").clone(),
            "inventory_checks" => inventory.opt("checks").clone(),
            "reason" => "source continuity indicates a false split; require fresh detection",
            "semantic_flags" => arr![], "global_crop_flags" => arr![], "target_flags" => arr![]};
            return Ok(store(self, v));
        }
        let (global_answer, global_request) = self.decision(&bundle, prompt, &prompts::global_questions())?;
        let mut targets: IndexMap<i64, Value> = IndexMap::new();
        let mut requests = obj! {};
        if bundle.opt("classification").as_str() == Some("panels") {
            let panels = bundle.opt("panels").as_array().cloned().unwrap();
            let workers = self.workers();
            let (client, root) = (self.client, self.root.clone());
            let results = run_ordered(&panels, workers, |panel| {
                let target = panel.opt("order").as_int().unwrap();
                let local = images_for_target(&bundle, target);
                let instructions = format!("{prompt}{}", prompts::target_suffix(target));
                let (answer, request) = decision(client, &root, &local, &instructions, &prompts::target_questions())?;
                Ok((target, answer.opt("probabilities").clone(), request))
            });
            for r in results {
                let (target, probabilities, request) = r?;
                targets.insert(target, probabilities);
                requests.set(&target.to_string(), request);
            }
        }
        let crossing = self.check_crossing_art(&bundle)?;
        let mut verdict = Self::quality_route(global_answer.opt("probabilities"), &targets);
        verdict.set("split_checks", splits.opt("checks").clone());
        verdict.set("inventory_checks", inventory.opt("checks").clone());
        verdict.set("crossing_art", crossing.clone());
        verdict.set("global_probabilities", global_answer.opt("probabilities").clone());
        let mut tp = obj! {};
        for (k, v) in &targets {
            tp.set(&k.to_string(), v.clone());
        }
        verdict.set("target_probabilities", tp);
        verdict.set("global_request", global_request);
        verdict.set("target_requests", requests);
        if crossing.opt("targets").truthy() {
            verdict.set("route", "escalate");
        }
        Ok(store(self, verdict))
    }

    // ------------------------------------------------------------ ownership

    fn candidate_coverage_risk(&mut self, candidate: &Value) -> R<()> {
        if candidate.opt("invalid").truthy() || candidate.opt("panels").opt("classification").as_str() != Some("panels") {
            return Ok(());
        }
        let identity = str_of(candidate.opt("identity"));
        let bundle = self.bundle(&identity)?.clone();
        let source = bundle
            .opt("images")
            .as_array()
            .unwrap()
            .iter()
            .find(|i| i.opt("label").as_str() == Some("Original complete page"))
            .cloned()
            .ok_or("StopIteration")?;
        if source.opt("sha256") != candidate.opt("source_sha256")
            || Some(sha_file(Path::new(&str_of(source.opt("path"))))?.as_str()) != source.opt("sha256").as_str()
        {
            return Err(Error::Blocked("Uncovered-content source changed".into()));
        }
        let result = (|| -> R<Value> {
            let mut boxes = Vec::new();
            for panel in bundle.opt("panels").as_array().unwrap() {
                let label = format!("Candidate crop {} in reading order", json::dumps(panel.opt("order")));
                let crops: Vec<&Value> =
                    bundle.opt("images").as_array().unwrap().iter().filter(|i| i.opt("label").as_str() == Some(&label)).collect();
                if crops.len() != 1 {
                    return Err("Expected one actual crop per target".into());
                }
                let points = geometry::parse_points(crops[0].opt("points").as_str().ok_or("'points'")?)?;
                if points.len() != 4 {
                    return Err("Expected rectangular crop points".into());
                }
                let (l, t) = points[0];
                let (r, b) = points[2];
                if points != vec![(l, t), (r, t), (r, b), (l, b)] {
                    return Err("Expected rectangular crop points".into());
                }
                boxes.push([l, t, r + 1, b + 1]);
            }
            let rgb = image::load_rgb(Path::new(&str_of(source.opt("path"))))?;
            Ok(refine::uncovered_content_risk(&rgb, &boxes)?)
        })()
        .map_err(|e| e.block("Uncovered-content check invalid: "))?;
        if result.opt("requires_ownership").as_bool() == Some(true) {
            self.uncovered_sources.insert(str_of(candidate.opt("source_sha256")));
        }
        self.coverage_risk.insert(identity, result);
        Ok(())
    }

    fn source_ownership_screen(&mut self, candidate: &Value) -> R<Value> {
        let bundle = self.bundle(&str_of(candidate.opt("identity")))?;
        let source = bundle
            .opt("images")
            .as_array()
            .unwrap()
            .iter()
            .find(|i| i.opt("label").as_str() == Some("Original complete page"))
            .cloned()
            .ok_or("StopIteration")?;
        let identity = str_of(source.opt("sha256"));
        if Some(identity.as_str()) != candidate.opt("source_sha256").as_str()
            || sha_file(Path::new(&str_of(source.opt("path"))))? != identity
        {
            return Err(Error::Blocked("Source ownership screen input changed".into()));
        }
        if !self.source_occlusion.contains_key(&identity) {
            let (raw, request) = self.client.request("decisions", &bodies::occlusion(&str_of(source.opt("path")))?, Kind::Native)?;
            let probability = contract::parse_answers(&raw, &prompts::occlusion_questions())
                .map_err(|e| Error::Blocked(format!("Source ownership screen invalid: {e}")))?
                .opt("probabilities")
                .opt("source_occlusion")
                .clone();
            let requires = probability.as_f64().unwrap_or(0.0) >= prompts::OCCLUSION_THRESHOLD;
            self.source_occlusion.insert(
                identity.clone(),
                obj! {"source_sha256" => identity.as_str(), "probability" => probability,
                "threshold" => prompts::OCCLUSION_THRESHOLD, "requires_ownership" => requires, "request" => request},
            );
        }
        Ok(self.source_occlusion[&identity].clone())
    }

    fn record_source_risk(&self, candidate: &Value, verdict: &mut Value) {
        if let Some(coverage) = self.coverage_risk.get(&str_of(candidate.opt("identity"))) {
            let retained = self.uncovered_sources.contains(&str_of(candidate.opt("source_sha256")))
                && coverage.opt("requires_ownership").as_bool() != Some(true);
            verdict.set("uncovered_content_risk", coverage.with("retained_source_risk", retained));
        }
        if let Some(screen) = self.source_occlusion.get(&str_of(candidate.opt("source_sha256"))) {
            verdict.set("source_occlusion_risk", screen.clone());
            if screen.opt("requires_ownership").as_bool() == Some(true)
                && candidate.opt("panels").opt("classification").as_str() == Some("panels")
            {
                verdict.set("ownership_required_targets", panel_orders(candidate.opt("panels")));
            }
        }
        if candidate.contains("source_sha256")
            && self.uncovered_sources.contains(&str_of(candidate.opt("source_sha256")))
            && candidate.opt("panels").opt("classification").as_str() == Some("panels")
        {
            verdict.set("ownership_required_targets", panel_orders(candidate.opt("panels")));
        }
    }

    fn proposal_bundle(&self, candidate: &Value) -> R<Value> {
        Ok(self.bundle(&str_of(candidate.opt("identity")))?.with("panels", candidate.opt("panels").opt("panels").clone()))
    }

    fn repair_parent(&self, candidate: &Value) -> Option<Shared> {
        let parent = candidate.get("repair_of").filter(|v| !v.is_null())?;
        self.history.values().flatten().find(|item| item.borrow().opt("identity") == parent).cloned()
    }

    fn risk_orders(&self, candidate: &Value) -> R<BTreeSet<i64>> {
        if candidate.opt("invalid").truthy() {
            return Ok(BTreeSet::new());
        }
        let (mut orders, mut required, mut ownership) = (BTreeSet::new(), BTreeSet::new(), BTreeSet::new());
        let mut seen: HashSet<String> = HashSet::new();
        let mut current = candidate.clone();
        loop {
            let key = format!("{}#{}", str_of(current.opt("identity")), seen.len());
            let id = str_of(current.opt("identity"));
            if !seen.insert(id.clone()) {
                let _ = key;
                return Err(Error::Blocked("Cyclic repair ownership lineage".into()));
            }
            if current.opt("invalid").truthy() {
                return Err(Error::Blocked("Repair ancestor has no valid proposal".into()));
            }
            let verdict = self.judgments.get(&id).map(|v| v.borrow().clone()).unwrap_or_else(|| obj! {});
            if current.opt("panels").opt("classification").as_str() == Some("panels") {
                for pair in geometry::overlap_risk_pairs(current.opt("panels").opt("panels").as_array().unwrap()) {
                    orders.extend(pair);
                }
                orders.extend(int_set(verdict.opt("crossing_art").opt("targets")));
                let screen = self.source_occlusion.get(&str_of(current.opt("source_sha256")));
                if screen.is_some_and(|s| s.opt("requires_ownership").as_bool() == Some(true))
                    || self.uncovered_sources.contains(&str_of(current.opt("source_sha256")))
                {
                    orders.extend(panel_orders(current.opt("panels")));
                }
            }
            ownership.extend(int_set(verdict.opt("ownership_required_targets")));
            required.extend(int_set(verdict.opt("target_flags")));
            for issue in current.opt("repair_issues").as_array().cloned().unwrap_or_default() {
                required.extend(int_set(issue.opt("panels")));
            }
            if current.get("repair_of").is_none_or(Value::is_null) {
                break;
            }
            match self.repair_parent(&current) {
                Some(p) => current = p.borrow().clone(),
                None => return Err(Error::Blocked("Repair has no frozen proposal ancestor".into())),
            }
        }
        Ok(if !orders.is_empty() || !ownership.is_empty() {
            orders.union(&required).copied().collect::<BTreeSet<_>>().union(&ownership).copied().collect()
        } else {
            BTreeSet::new()
        })
    }

    fn ensure_evidence(&mut self, cand: &Shared) -> R<Value> {
        let candidate = cand.borrow().clone();
        let identity = str_of(candidate.opt("identity"));
        let bundle = self.proposal_bundle(&candidate)?;
        let parent = candidate.get("repair_of").filter(|v| !v.is_null()).map(str_of);
        let previous = self.repair_parent(&candidate);
        if parent.is_some() {
            let Some(prev) = &previous else {
                return Ok(obj! {"route" => "escalate", "reason" => "Repair has no frozen proposal ancestor"});
            };
            let prev = prev.borrow().clone();
            let (before, after) = (prev.opt("panels"), candidate.opt("panels"));
            let mut same = prev.opt("source_sha256") == candidate.opt("source_sha256")
                && ["classification", "orientation", "reading_direction"].iter().all(|k| before.opt(k) == after.opt(k))
                && before.opt("panels").as_array().map(Vec::len) == after.opt("panels").as_array().map(Vec::len);
            for (old, new) in before.opt("panels").as_array().unwrap().iter().zip(after.opt("panels").as_array().unwrap()) {
                let o = geometry::box4(old.opt("box")).unwrap();
                let n = geometry::box4(new.opt("box")).unwrap();
                same = same && old.opt("order") == new.opt("order") && n[0] <= o[0] && n[1] <= o[1] && n[2] >= o[2] && n[3] >= o[3];
            }
            if !same {
                return Ok(obj! {"route" => "escalate", "reason" => "Repair is not a monotonic descendant of its immediate parent"});
            }
        }
        if !self.scene_evidence.contains_key(&identity) {
            if let Some(parent) = &parent {
                if !self.scene_evidence.contains_key(parent) {
                    let prev = previous.clone().unwrap();
                    self.ensure_evidence(&prev)?;
                    if !self.scene_evidence.contains_key(parent) {
                        return Ok(obj! {"route" => "escalate", "reason" => "Repair ancestor has no source evidence"});
                    }
                }
                let artifact = self.scene_evidence[parent].clone();
                self.scene_links.insert(identity.clone(), str_of(artifact.opt("proposal_sha256")));
                self.scene_evidence.insert(identity.clone(), artifact);
            } else {
                let artifact = (|| -> R<Value> {
                    let body = scene_evidence::request_body(&bundle, &self.scene_model, None)?;
                    let (mut raw, mut request) = self.client.request("responses", &body, Kind::Verifier)?;
                    let mut limit = None;
                    if contract::responses_output_exhausted(&raw) {
                        let n = scene_evidence::source_proposal(&bundle)?.opt("panels").as_array().unwrap().len();
                        limit = Some(scene_evidence::recovery_output_limit(n));
                        let expanded = scene_evidence::request_body(&bundle, &self.scene_model, limit)?;
                        (raw, request) = self.client.request("responses", &expanded, Kind::Verifier)?;
                    }
                    scene_evidence::response_evidence(&raw, &bundle, Some(&request), &self.scene_model, "verifier", limit)
                })()
                .map_err(|e| e.block("Source ownership audit invalid: "))?;
                let directory = self.root.join("scene-evidence");
                std::fs::create_dir_all(&directory)?;
                let path = directory.join(format!("{}.json", str_of(artifact.opt("evidence_sha256"))));
                if !path.exists() {
                    save(&path, &artifact)?;
                }
                self.scene_evidence.insert(identity.clone(), artifact);
            }
        }
        let artifact = self.scene_evidence[&identity].clone();
        if artifact.opt("model").as_str() != Some(self.scene_model.as_str()) {
            return Ok(obj! {"route" => "escalate", "reason" => "Inherited source audit model does not match policy"});
        }
        let link = self.scene_links.get(&identity).cloned();
        let gate = scene_evidence::evidence_gate(&artifact, &bundle, link.as_deref());
        cand.borrow_mut().set("scene_evidence", artifact.pick(&["evidence_sha256", "proposal_sha256", "model", "request"])?);
        let live = self.bundles.get_mut(&identity).unwrap();
        if gate.opt("route").as_str() == Some("keep") {
            let hypotheses = scene_evidence::verifier_hypotheses(&artifact, &bundle, link.as_deref())?;
            live.set("_ownership_hypotheses", hypotheses);
        } else {
            live.remove("_ownership_hypotheses");
        }
        Ok(gate)
    }

    /// `OwnershipConverter.judge` (most derived).
    pub fn judge(&mut self, _page: &Path, cand: &Shared) -> R<Shared> {
        let candidate = cand.borrow().clone();
        self.candidate_coverage_risk(&candidate)?;
        let mut risky = self.risk_orders(&candidate)?;
        let mut verdict: Option<Shared> = None;
        if risky.is_empty() || candidate.opt("tier").as_str() == Some("sol-low") {
            let v = self.base_judge(&candidate)?;
            risky.extend(self.risk_orders(&candidate)?);
            risky.extend(int_set(v.borrow().opt("crossing_art").opt("targets")));
            let keep = v.borrow().opt("route").as_str() == Some("keep");
            if risky.is_empty() && keep && candidate.opt("panels").opt("classification").as_str() == Some("panels") {
                self.source_ownership_screen(&candidate)?;
                risky = self.risk_orders(&candidate)?;
            }
            self.record_source_risk(&candidate, &mut v.borrow_mut());
            if risky.is_empty() || v.borrow().opt("route").as_str() != Some("keep") {
                return Ok(v);
            }
            verdict = Some(v);
        }
        let gate = self.ensure_evidence(cand)?;
        let candidate = cand.borrow().clone();
        let identity = str_of(candidate.opt("identity"));
        if gate.opt("route").as_str() != Some("keep") {
            let mut v = obj! {"route" => "escalate", "source_evidence_gate" => gate, "semantic_flags" => arr![], "global_crop_flags" => arr![], "target_flags" => arr![]};
            self.record_source_risk(&candidate, &mut v);
            let s = shared(v);
            self.judgments.insert(identity, s.clone());
            return Ok(s);
        }
        let v = match verdict {
            Some(v) => v,
            None => self.base_judge(&candidate)?,
        };
        {
            let mut vm = v.borrow_mut();
            self.record_source_risk(&candidate, &mut vm);
            vm.set("source_evidence_gate", gate);
            vm.set("ownership_confirmation_required", true);
            let mut targets = risky.clone();
            targets.extend(int_set(vm.opt("target_flags")));
            vm.set("ownership_required_targets", ints(&targets));
            vm.set("route", "escalate");
        }
        self.judgments.insert(identity, v.clone());
        Ok(v)
    }

    // ------------------------------------------------------------ verification

    /// Base `Converter.verification`.
    fn base_verification(&self, bundle: &Value, prompt: &str, effort: &str, model: &str) -> R<(Value, Value)> {
        let body = bodies::verification(bundle, prompt, effort, model)?;
        let (raw, request) = self.client.request("responses", &body, Kind::Verifier)?;
        let count = bundle.opt("panels").as_array().map(Vec::len).unwrap_or(0);
        let verdict = contract::parse_verdict(&raw, count).map_err(Error::Blocked)?;
        Ok((verdict, request))
    }

    /// `OwnershipConverter.verification` (rich prompt).
    fn verification(&self, bundle: &Value, prompt: &str, effort: &str, model: &str) -> R<(Value, Value)> {
        self.base_verification(bundle, &rich_prompt(bundle, prompt), effort, model)
    }

    /// Base `Converter.verify`.
    fn base_verify(&self, candidate: &Value) -> R<Value> {
        if candidate.opt("invalid").truthy() {
            return Ok(obj! {"route" => "escalate", "structural_error" => candidate.opt("invalid").clone()});
        }
        let identity = str_of(candidate.opt("identity"));
        let bundle = self.bundle(&identity)?.clone();
        let verdict = self.judgments.get(&identity).ok_or_else(|| Error::Value(format!("'{identity}'")))?.borrow().clone();
        let (mut checks, mut evidence): (Vec<bool>, Vec<Value>) = (vec![], vec![]);
        if verdict.opt("overlap_pairs").truthy() || verdict.opt("split_flags").truthy() || verdict.opt("inventory_flags").truthy() {
            return Ok(
                obj! {"route" => "escalate", "evidence" => arr![], "reason" => "layout risk requires stronger detection, not verifier clearance"},
            );
        }
        let crossing_targets = int_set(verdict.opt("crossing_art").opt("targets"));
        let tier = candidate.opt("tier").as_str().unwrap_or("");
        let global_model = if tier == "astra" && !crossing_targets.is_empty() { "gpt-6-astra" } else { "gpt-6-sol" };
        if verdict.opt("global_crop_flags").truthy() {
            if tier == "sol-low" {
                return Ok(
                    obj! {"route" => "escalate", "evidence" => arr![], "reason" => "independent page-level clipping warning requires stronger detection"},
                );
            }
            let (answer, request) = self.verification(&bundle, prompts::JUDGE, "high", global_model)?;
            checks.push(answer.opt("route").as_str() == Some("keep"));
            evidence.push(obj! {"scope" => "complete stronger candidate", "verdict" => answer, "request" => request});
        } else if verdict.opt("semantic_flags").truthy() {
            let effort = if global_model == "gpt-6-astra" { "high" } else { "low" };
            let (answer, request) = self.verification(&bundle, prompts::JUDGE, effort, global_model)?;
            checks.push(answer.opt("route").as_str() == Some("keep"));
            evidence.push(obj! {"scope" => "complete candidate after semantic warning", "verdict" => answer, "request" => request});
        }
        if tier != "astra" && checks.contains(&false) {
            return Ok(
                obj! {"route" => "escalate", "evidence" => Value::Array(evidence), "reason" => "intermediate candidate already rejected; proceed to stronger detection"},
            );
        }
        let mut targets = int_set(verdict.opt("target_flags"));
        targets.extend(crossing_targets.iter().copied());
        for target in targets {
            let local = images_for_target(&bundle, target);
            let model = if crossing_targets.contains(&target) { "gpt-6-astra" } else { "gpt-6-sol" };
            let (mut answer, request) = self.verification(&local, prompts::JUDGE_TARGET, "high", model)?;
            evidence.push(obj! {"scope" => "target", "panel" => target, "verdict" => answer.clone(), "request" => request, "crossing_art_risk" => crossing_targets.contains(&target)});
            let resolved_context = verdict.opt("split_checks").as_array().cloned().unwrap_or_default().iter().any(|check| {
                int_set(check.opt("pair")).contains(&target)
                    && check.opt("preceding_page_disambiguation").opt("verdict").opt("classification").as_str() == Some("distinct")
            });
            if answer.opt("route").as_str() != Some("keep") && tier == "astra" && resolved_context {
                let source = str_of(bundle.opt("images").as_array().unwrap()[0].opt("path"));
                let predecessors =
                    self.source_context.get(&util::path_str(&util::resolve(Path::new(&source)))).cloned().unwrap_or_default();
                if !predecessors.is_empty() {
                    let mut images = local.opt("images").as_array().cloned().unwrap();
                    for (i, p) in predecessors.iter().enumerate() {
                        images.push(obj! {"label" => format!("Preceding source page {} of {} (context only)", i + 1, predecessors.len()), "path" => p.as_str(), "sha256" => sha_file(Path::new(p))?});
                    }
                    let contextual = local.with("images", Value::Array(images));
                    let (a, request) = self.verification(&contextual, prompts::JUDGE_TARGET_CONTEXT, "high", "gpt-6-astra")?;
                    answer = a;
                    evidence.push(obj! {"scope" => "target after narrative disambiguation", "panel" => target, "verdict" => answer.clone(), "request" => request});
                }
            }
            if answer.opt("route").as_str() != Some("keep") && geometry::needs_source_detail(candidate, &answer, target) {
                let directory = PathBuf::from(str_of(candidate.opt("bundle"))).parent().unwrap().join("source-detail");
                let detailed = with_source_detail(&bundle, target, &directory, true)?;
                let (a, request) = self.verification(&detailed, prompts::JUDGE_TARGET_DETAIL, "high", "gpt-6-astra")?;
                answer = a;
                let details = Value::Array(detailed.opt("images").as_array().unwrap()[2..].to_vec());
                evidence.push(obj! {"scope" => "repaired target with source boundary context", "panel" => target, "verdict" => answer.clone(), "request" => request, "source_details" => details});
            }
            checks.push(answer.opt("route").as_str() == Some("keep"));
            if tier != "astra" && answer.opt("route").as_str() != Some("keep") {
                return Ok(
                    obj! {"route" => "escalate", "evidence" => Value::Array(evidence), "reason" => "intermediate target failed; proceed to stronger detection"},
                );
            }
        }
        let keep = !checks.is_empty() && checks.iter().all(|c| *c);
        Ok(obj! {"route" => if keep { "keep" } else { "escalate" }, "evidence" => Value::Array(evidence)})
    }

    fn adjudicate_clipping(&self, candidate: &Value, bundle: &Value, prompt: &str, entry: Value, target: Option<i64>) -> R<Value> {
        let answer = entry.opt("verdict").clone();
        let tier_ok = matches!(candidate.opt("tier").as_str(), Some("sol-high" | "astra"));
        if !tier_ok
            || answer.opt("route").as_str() != Some("escalate")
            || answer.opt("decision").as_str() != Some("escalate")
            || answer.opt("scene_inventory").as_str() != Some("pass")
            || answer.opt("reading_order").as_str() != Some("pass")
            || answer.opt("crop_coverage").as_str() != Some("fail")
            || !answer.opt("issues").as_array().is_some_and(|i| !i.is_empty())
        {
            return Ok(entry);
        }
        let known: BTreeSet<i64> = panel_orders(candidate.opt("panels")).into_iter().collect();
        let mut targets = BTreeSet::new();
        for issue in answer.opt("issues").as_array().unwrap() {
            let ok = issue.is_object()
                && matches!(issue.opt("kind").as_str(), Some("clipped_art" | "clipped_text"))
                && issue
                    .opt("panels")
                    .as_array()
                    .is_some_and(|p| !p.is_empty() && p.iter().all(|o| o.as_int().is_some_and(|v| known.contains(&v))))
                && issue.opt("evidence").as_str().is_some_and(|e| !e.trim().is_empty());
            if !ok {
                return Ok(entry);
            }
            targets.extend(int_set(issue.opt("panels")));
        }
        if let Some(t) = target
            && targets != BTreeSet::from([t])
        {
            return Ok(entry);
        }
        let mut bundle = bundle.clone();
        let mut details = entry.opt("source_details").clone();
        if details.is_null() {
            details = arr![];
        }
        if target.is_none() {
            let mut list = vec![];
            for order in &targets {
                let directory = PathBuf::from(str_of(candidate.opt("bundle"))).parent().unwrap().join("ownership-source-detail");
                let local = with_source_detail(&bundle, *order, &directory, true)?;
                list.extend(local.opt("images").as_array().unwrap()[2..].iter().cloned());
            }
            details = Value::Array(list.clone());
            let mut images = bundle.opt("images").as_array().cloned().unwrap();
            images.extend(list);
            bundle = bundle.with("images", Value::Array(images));
        }
        let (stronger, request) =
            self.verification(&bundle, &format!("{prompt}{}", prompts::AUTHORED_BOUNDARY_CLARIFICATION), "high", "gpt-6-astra")?;
        Ok(entry
            .with("original_verdict", answer)
            .with("original_request", entry.opt("request").clone())
            .with("original_model", entry.opt("model").clone())
            .with("model", "gpt-6-astra")
            .with("verdict", stronger)
            .with("request", request)
            .with("adjudication", obj! {"scope" => entry.opt("scope").clone(), "target" => target, "model" => "gpt-6-astra", "effort" => "high", "source_details" => details}))
    }

    /// `OwnershipConverter.verify` (most derived).
    pub fn verify(&mut self, _page: &Path, cand: &Shared) -> R<Value> {
        let candidate = cand.borrow().clone();
        self.candidate_coverage_risk(&candidate)?;
        let mut risky = self.risk_orders(&candidate)?;
        let mut previous_confirmation: Option<Value> = None;
        let identity = str_of(candidate.opt("identity"));
        if risky.is_empty() {
            let confirmation = self.base_verify(&candidate)?;
            if confirmation.opt("route").as_str() != Some("keep")
                || candidate.opt("panels").opt("classification").as_str() != Some("panels")
            {
                return Ok(confirmation);
            }
            self.source_ownership_screen(&candidate)?;
            let judgment = self.judgments.get(&identity).ok_or_else(|| Error::Value(format!("'{identity}'")))?.clone();
            self.record_source_risk(&candidate, &mut judgment.borrow_mut());
            risky = self.risk_orders(&candidate)?;
            if risky.is_empty() {
                return Ok(confirmation);
            }
            previous_confirmation = Some(confirmation);
        }
        let verdict = self.judgments.get(&identity).ok_or_else(|| Error::Value(format!("'{identity}'")))?.borrow().clone();
        if previous_confirmation.is_none()
            && (verdict.opt("overlap_pairs").truthy() || verdict.opt("split_flags").truthy() || verdict.opt("inventory_flags").truthy())
        {
            let confirmation = self.base_verify(&candidate)?;
            if confirmation.opt("route").as_str() != Some("keep") {
                return Ok(confirmation);
            }
            previous_confirmation = Some(confirmation);
        }
        let gate = self.ensure_evidence(cand)?;
        let candidate = cand.borrow().clone();
        if gate.opt("route").as_str() != Some("keep") {
            return Ok(
                obj! {"route" => "escalate", "source_evidence_gate" => gate, "evidence" => arr![], "reason" => "Source ownership is unresolved; crop passes cannot clear it"},
            );
        }
        let bundle = self.bundle(&identity)?.clone();
        let mut checks = vec![];
        let mut evidence: Vec<Value> =
            previous_confirmation.as_ref().and_then(|c| c.opt("evidence").as_array().cloned()).unwrap_or_default();
        let crossing_targets = int_set(verdict.opt("crossing_art").opt("targets"));
        let tier = candidate.opt("tier").as_str().unwrap_or("").to_string();
        let global_model = if tier == "astra" && !crossing_targets.is_empty() { "gpt-6-astra" } else { "gpt-6-sol" };
        let mut prompt = prompts::JUDGE.to_string();
        if global_model == "gpt-6-astra" {
            prompt.push_str(prompts::AUTHORED_BOUNDARY_CLARIFICATION);
        }
        let (answer, request) = self.verification(&bundle, &prompt, "high", global_model)?;
        let mut item = obj! {"scope" => "complete candidate with source ownership", "verdict" => answer, "request" => request, "model" => global_model, "effort" => "high"};
        if global_model == "gpt-6-sol" {
            item = self.adjudicate_clipping(&candidate, &bundle, &prompt, item, None)?;
        }
        checks.push(item.opt("verdict").opt("route").as_str() == Some("keep"));
        evidence.push(item);
        if tier != "astra" && !checks[checks.len() - 1] {
            return Ok(
                obj! {"route" => "escalate", "evidence" => Value::Array(evidence), "source_evidence_gate" => gate, "reason" => "Global ownership confirmation failed; require stronger detection"},
            );
        }
        let mut targets = risky.clone();
        targets.extend(int_set(verdict.opt("target_flags")));
        targets.extend(crossing_targets.iter().copied());
        for target in targets {
            let directory = PathBuf::from(str_of(candidate.opt("bundle"))).parent().unwrap().join("ownership-source-detail");
            let local = with_source_detail(&bundle, target, &directory, true)?;
            let model = if crossing_targets.contains(&target) { "gpt-6-astra" } else { "gpt-6-sol" };
            let mut prompt = prompts::JUDGE_TARGET_DETAIL.to_string();
            if model == "gpt-6-astra" {
                prompt.push_str(prompts::AUTHORED_BOUNDARY_CLARIFICATION);
            }
            let (answer, request) = self.verification(&local, &prompt, "high", model)?;
            let mut item = obj! {"scope" => "target with source ownership and exact crop boundary", "panel" => target,
            "verdict" => answer, "request" => request, "source_details" => Value::Array(local.opt("images").as_array().unwrap()[2..].to_vec()),
            "model" => model, "effort" => "high", "crossing_art_risk" => crossing_targets.contains(&target)};
            if model == "gpt-6-sol" {
                item = self.adjudicate_clipping(&candidate, &local, &prompt, item, Some(target))?;
            }
            checks.push(item.opt("verdict").opt("route").as_str() == Some("keep"));
            evidence.push(item);
            if tier != "astra" && !checks[checks.len() - 1] {
                return Ok(
                    obj! {"route" => "escalate", "evidence" => Value::Array(evidence), "source_evidence_gate" => gate, "reason" => "Marked target failed; require stronger detection"},
                );
            }
        }
        let keep = !checks.is_empty() && checks.iter().all(|c| *c);
        Ok(obj! {"route" => if keep { "keep" } else { "escalate" }, "evidence" => Value::Array(evidence), "source_evidence_gate" => gate})
    }

    // ------------------------------------------------------------ final acceptance

    /// `final_acceptance`: the bound completeness proof for a passing candidate.
    pub fn final_accept(&self, page: &Path, cand: &Shared, guard: &Completeness) -> R<Value> {
        let candidate = cand.borrow().clone();
        (|| -> R<Value> {
            let canonical = self.canonical_bundle(&str_of(candidate.opt("identity")))?;
            let saved = read_json(Path::new(&str_of(candidate.opt("bundle"))))?;
            if canonical != saved {
                return Err("Live candidate bundle differs from saved bundle".into());
            }
            self.client.set_grace(true);
            let verdict = guard.check(page, &saved, &candidate);
            self.client.set_grace(false);
            let verdict = verdict?;
            if verdict.opt("route").as_str() == Some("keep") {
                acceptance::validate_acceptance(page, &candidate, &verdict, "normal")?;
            }
            Ok(verdict)
        })()
        .map_err(|e| e.block("Invalid final acceptance proof: "))
    }
}

/// Base `Converter.decision`.
fn base_decision(client: &Client, bundle: &Value, prompt: &str, questions: &Value) -> R<(Value, Value)> {
    let body = bodies::decision(bundle, prompt, questions)?;
    let (raw, provenance) = client.request("decisions", &body, Kind::Native)?;
    let answer = contract::parse_answers(&raw, questions).map_err(Error::Blocked)?;
    Ok((answer, provenance))
}

/// `OwnershipConverter._rich_prompt`.
fn rich_prompt(bundle: &Value, prompt: &str) -> String {
    match bundle.get("_ownership_hypotheses") {
        None => prompt.to_string(),
        Some(h) => format!("{prompt}{}\n{}", prompts::AUXILIARY, json::dumps_sorted(h)),
    }
}

/// `MarkedNativeConverter.decision` (most derived), resolving to the
/// ownership-enriched base decision for every non-target question set.
fn decision(client: &Client, root: &Path, bundle: &Value, prompt: &str, questions: &Value) -> R<(Value, Value)> {
    if questions != &prompts::target_questions() {
        return base_decision(client, bundle, &rich_prompt(bundle, prompt), questions);
    }
    let images = bundle.opt("images").as_array().cloned().unwrap_or_default();
    if images.len() != 2 || images[0].opt("label").as_str() != Some("Original complete page") {
        return Err(Error::Blocked("Marked target decision requires source and exactly one actual crop".into()));
    }
    let label = str_of(images[1].opt("label"));
    let target = label
        .strip_prefix("Candidate crop ")
        .and_then(|r| r.strip_suffix(" in reading order"))
        .filter(|n| !n.is_empty() && !n.starts_with('0') && n.bytes().all(|c| c.is_ascii_digit()))
        .and_then(|n| n.parse::<i64>().ok())
        .ok_or_else(|| Error::Blocked("Marked target decision has no unambiguous target label".into()))?;
    let panels = bundle.opt("panels").as_array().cloned().unwrap_or_default();
    if panels.iter().filter(|p| p.opt("order").as_int() == Some(target)).count() != 1 {
        return Err(Error::Blocked("Marked target decision target does not uniquely match geometry".into()));
    }
    let expected = format!("{}{}", prompts::BASE, prompts::target_suffix(target));
    if prompt != expected {
        return Err(Error::Blocked("Unexpected target-decision prompt; no silent rewrite".into()));
    }
    let mut clean = bundle.pick(&["classification", "reading_direction"])?;
    let clean_panels: Vec<Value> = panels.iter().map(|p| obj! {"order" => p.opt("order").clone(), "box" => p.opt("box").clone()}).collect();
    clean.set("panels", Value::Array(clean_panels.clone()));
    clean.set("images", Value::Array(images.clone()));
    let identity = util::json_hash(&obj! {"geometry" => Value::Array(clean_panels), "source" => images[0].opt("sha256").clone(),
    "crop" => images[1].opt("sha256").clone(), "target" => target});
    let detailed = with_source_detail(&clean, target, &root.join("marked-native").join(&identity), true)?;
    let instructions = format!("{expected}{}", prompts::CONTEXT_GUIDANCE);
    base_decision(client, &detailed, &instructions, &prompts::marked_questions())
}

/// `ThreadPoolExecutor.map`: run every task (up to `workers` at once), then
/// return results in input order; callers surface the first error in order.
fn run_ordered<T: Sync, O: Send>(items: &[T], workers: usize, f: impl Fn(&T) -> R<O> + Sync) -> Vec<R<O>>
where
    R<O>: Send,
{
    if workers <= 1 || items.len() <= 1 {
        return items.iter().map(&f).collect();
    }
    let next = std::sync::atomic::AtomicUsize::new(0);
    let slots: Vec<std::sync::Mutex<Option<R<O>>>> = items.iter().map(|_| std::sync::Mutex::new(None)).collect();
    std::thread::scope(|scope| {
        for _ in 0..workers.min(items.len()) {
            scope.spawn(|| {
                loop {
                    let i = next.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    if i >= items.len() {
                        break;
                    }
                    let r = f(&items[i]);
                    *slots[i].lock().unwrap() = Some(r);
                }
            });
        }
    });
    slots.into_iter().map(|s| s.into_inner().unwrap().unwrap()).collect()
}
