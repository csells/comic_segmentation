//! Source-only scene ownership evidence (`scene_evidence.py`, version 6).

use crate::error::{Error, R};
use crate::json::{self, Value};
use crate::prompts;
use crate::util::{json_hash, sha256_hex};
use crate::{arr, obj};

pub const VERSION: i64 = 6;
pub const MODELS: [&str; 2] = ["gpt-6-sol", "gpt-6-astra"];
const SCENE_FIELDS: [&str; 6] = ["order", "identity", "owned_content", "ownership_cues", "distinguish_from_neighbors", "uncertain"];
const ISSUE_KINDS: [&str; 5] = ["missing_scene", "ambiguous_mapping", "contradictory_ownership", "uncertain", "shared_unowned"];

fn source(bundle: &Value) -> R<(String, Vec<u8>)> {
    let images = bundle.opt("images").as_array().ok_or("Invalid source image inventory")?;
    if images.iter().any(|i| !i.is_object()) {
        return Err("Invalid source image inventory".into());
    }
    let sources: Vec<&Value> = images.iter().filter(|i| i.opt("label").as_str() == Some("Original complete page")).collect();
    if sources.len() != 1 {
        return Err("Expected one original complete source".into());
    }
    let s = sources[0];
    let data = std::fs::read(s.opt("path").as_str().ok_or("'path'")?)?;
    if Some(sha256_hex(&data).as_str()) != s.opt("sha256").as_str() {
        return Err("Source image changed".into());
    }
    Ok((s.opt("sha256").as_str().unwrap().to_string(), data))
}

fn panels(bundle: &Value, descriptions: bool) -> R<Vec<Value>> {
    let ps = match bundle.opt("panels").as_array() {
        Some(p) if !p.is_empty() => p,
        _ => return Err("Missing proposal inventory".into()),
    };
    let mut out = Vec::new();
    for (i, p) in ps.iter().enumerate() {
        let order = i as i64 + 1;
        if !p.is_object() || p.opt("order").as_int() != Some(order) {
            return Err("Proposal orders must be contiguous and unchanged".into());
        }
        let b = crate::geometry::box4(p.opt("box"));
        let valid = b.is_some_and(|b| b.iter().all(|n| (0..=1000).contains(n)) && b[0] < b[2] && b[1] < b[3]);
        if !valid {
            return Err("Invalid proposal rectangle".into());
        }
        let mut v = obj! {"order" => order, "box" => p.opt("box").clone()};
        if descriptions {
            match p.opt("description").as_str() {
                Some(d) if !d.trim().is_empty() && d.chars().count() <= 1200 => v.set("description", d),
                _ => return Err("Missing or invalid detector description".into()),
            }
        }
        out.push(v);
    }
    Ok(out)
}

pub fn source_proposal(bundle: &Value) -> R<Value> {
    let (sha, _) = source(bundle)?;
    if !matches!(bundle.opt("classification").as_str(), Some("panels" | "whole_page" | "blank")) {
        return Err("Invalid proposal classification".into());
    }
    if !matches!(bundle.opt("reading_direction").as_str(), Some("ltr" | "rtl")) {
        return Err("Invalid proposal reading direction".into());
    }
    Ok(obj! {"source_sha256" => sha, "classification" => bundle.opt("classification").clone(),
    "reading_direction" => bundle.opt("reading_direction").clone(), "panels" => Value::Array(panels(bundle, true)?)})
}

pub fn evidence_schema() -> Value {
    let text = || obj! {"type" => "string", "minLength" => 1, "maxLength" => 1200};
    let list = || obj! {"type" => "array", "items" => text(), "maxItems" => 8};
    let scene = obj! {"order" => obj! {"type" => "integer", "minimum" => 1}, "identity" => text(),
    "owned_content" => list(), "ownership_cues" => list(), "distinguish_from_neighbors" => list(),
    "uncertain" => obj! {"type" => "boolean"}};
    let issue = obj! {"kind" => obj! {"type" => "string", "enum" => Value::from(ISSUE_KINDS.to_vec())},
    "orders" => obj! {"type" => "array", "items" => obj! {"type" => "integer", "minimum" => 1}}, "evidence" => text()};
    let keys = |v: &Value| Value::Array(v.as_object().unwrap().keys().map(|k| Value::from(k.as_str())).collect());
    let fields = obj! {
        "inventory_status" => obj! {"type" => "string", "enum" => arr!["complete", "incomplete", "uncertain"]},
        "scenes" => obj! {"type" => "array", "items" => obj! {"type" => "object", "additionalProperties" => false, "properties" => scene.clone(), "required" => keys(&scene)}},
        "issues" => obj! {"type" => "array", "items" => obj! {"type" => "object", "additionalProperties" => false, "properties" => issue.clone(), "required" => keys(&issue)}},
    };
    let required = keys(&fields);
    obj! {"type" => "object", "additionalProperties" => false, "properties" => fields, "required" => required}
}

pub fn source_output_limit(scene_count: usize) -> i64 {
    let n = scene_count as i64;
    if n <= 4 { 8192 } else { 8192i64.max(24576i64.min(4096 + 1024 * n)) }
}

pub fn recovery_output_limit(scene_count: usize) -> i64 {
    32768i64.min(2 * source_output_limit(scene_count))
}

fn output_limit(snapshot: &Value, limit: Option<i64>) -> R<i64> {
    let n = snapshot.opt("panels").as_array().map(Vec::len).unwrap_or(0);
    let default = source_output_limit(n);
    match limit {
        None => Ok(default),
        Some(l) if l == default || l == recovery_output_limit(n) => Ok(l),
        Some(_) => Err("Unsupported source audit output allowance".into()),
    }
}

pub fn request_body(bundle: &Value, model: &str, limit: Option<i64>) -> R<Value> {
    if !MODELS.contains(&model) {
        return Err("Unsupported source audit model".into());
    }
    let snapshot = source_proposal(bundle)?;
    let (_, data) = source(bundle)?;
    let mut supplied = snapshot.pick(&["classification", "reading_direction", "panels"])?;
    supplied.set("box_coordinate_convention", "[top,left,bottom,right] normalized 0..1000");
    let max = output_limit(&snapshot, limit)?;
    Ok(obj! {"model" => model, "store" => false, "max_output_tokens" => max,
    "reasoning" => obj! {"effort" => "high"}, "service_tier" => "default",
    "text" => obj! {"format" => obj! {"type" => "json_schema", "name" => "source_scene_evidence", "strict" => true, "schema" => evidence_schema()}},
    "input" => arr![obj! {"role" => "user", "content" => arr![
        obj! {"type" => "input_text", "text" => format!("{}\n{}", prompts::SCENE_EVIDENCE, json::dumps(&supplied))},
        obj! {"type" => "input_image", "detail" => "original", "image_url" => format!("data:image/jpeg;base64,{}", crate::util::b64(&data))}]}]})
}

fn validate_result(value: &Value, orders: &[i64]) -> R<()> {
    let ok = value.as_object().is_some_and(|m| m.len() == 3 && ["inventory_status", "scenes", "issues"].iter().all(|k| m.contains_key(*k)));
    if !ok {
        return Err("Invalid source evidence envelope".into());
    }
    if !matches!(value.opt("inventory_status").as_str(), Some("complete" | "incomplete" | "uncertain")) {
        return Err("Invalid inventory status".into());
    }
    let scenes = value.opt("scenes").as_array();
    let fields_ok = scenes.is_some_and(|s| {
        s.iter().all(|sc| sc.as_object().is_some_and(|m| m.len() == SCENE_FIELDS.len() && SCENE_FIELDS.iter().all(|k| m.contains_key(*k))))
    });
    let scene_orders: Vec<Value> = scenes.map(|s| s.iter().map(|sc| sc.opt("order").clone()).collect()).unwrap_or_default();
    let want: Vec<Value> = orders.iter().map(|o| Value::Int(*o)).collect();
    if !fields_ok || scene_orders != want {
        return Err("Unmapped or changed scene inventory".into());
    }
    for scene in scenes.unwrap() {
        if scene.opt("order").as_int().is_none() || scene.opt("uncertain").as_bool().is_none() {
            return Err("Invalid source evidence types".into());
        }
        for key in ["identity", "owned_content", "ownership_cues", "distinguish_from_neighbors"] {
            let values: Vec<Value> = if key == "identity" {
                vec![scene.opt(key).clone()]
            } else {
                scene.opt(key).as_array().cloned().unwrap_or_else(|| vec![Value::Null; 9])
            };
            if values.len() > 8 || values.iter().any(|v| !v.as_str().is_some_and(|s| !s.trim().is_empty() && s.chars().count() <= 1200)) {
                return Err("Invalid source evidence text".into());
            }
            if key != "identity" && !scene.opt(key).is_array() {
                return Err("Invalid source evidence text".into());
            }
        }
        if !scene.opt("uncertain").as_bool().unwrap() && (!scene.opt("owned_content").truthy() || !scene.opt("ownership_cues").truthy()) {
            return Err("Established scene lacks content or source support".into());
        }
    }
    let Some(issues) = value.opt("issues").as_array() else { return Err("Invalid source issues".into()) };
    for issue in issues {
        let ok = issue.as_object().is_some_and(|m| m.len() == 3 && ["kind", "orders", "evidence"].iter().all(|k| m.contains_key(*k)))
            && issue.opt("kind").as_str().is_some_and(|k| ISSUE_KINDS.contains(&k))
            && issue.opt("orders").as_array().is_some_and(|o| o.iter().all(|n| n.as_int().is_some_and(|v| orders.contains(&v))))
            && issue.opt("evidence").as_str().is_some_and(|e| !e.trim().is_empty() && e.chars().count() <= 1200);
        if !ok {
            return Err("Invalid source issue".into());
        }
    }
    Ok(())
}

fn prefix(kind: &str) -> R<&'static [u8]> {
    match kind {
        "detector" => Ok(b"openai-responses:"),
        "verifier" => Ok(b"comic-escalation-judge-v1:"),
        _ => Err("Unsupported source audit request kind".into()),
    }
}

pub fn request_fingerprint(bundle: &Value, model: &str, kind: &str, limit: Option<i64>) -> R<String> {
    let mut data = prefix(kind)?.to_vec();
    data.extend_from_slice(json::dumps_sorted(&request_body(bundle, model, limit)?).as_bytes());
    Ok(sha256_hex(&data))
}

/// `scene_evidence.response_evidence`.
pub fn response_evidence(raw: &Value, bundle: &Value, request: Option<&Value>, model: &str, kind: &str, limit: Option<i64>) -> R<Value> {
    if raw.opt("status").as_str() != Some("completed") {
        return Err("Source audit incomplete; never certify or retry automatically".into());
    }
    let mut texts = String::new();
    for item in raw.opt("output").as_array().cloned().unwrap_or_default() {
        if item.opt("type").as_str() != Some("message") {
            continue;
        }
        if !item.opt("status").is_null() && item.opt("status").as_str() != Some("completed") {
            return Err("Source audit message incomplete".into());
        }
        for part in item.opt("content").as_array().cloned().unwrap_or_default() {
            if part.opt("type").as_str() == Some("refusal") {
                return Err("Source audit refused".into());
            }
            if part.opt("type").as_str() == Some("output_text") {
                texts.push_str(part.opt("text").as_str().unwrap_or(""));
            }
        }
    }
    let snapshot = source_proposal(bundle)?;
    let orders: Vec<i64> = snapshot.opt("panels").as_array().unwrap().iter().map(|p| p.opt("order").as_int().unwrap()).collect();
    let result = json::loads(&texts)?;
    validate_result(&result, &orders)?;
    let limit = output_limit(&snapshot, limit)?;
    let fingerprint = request_fingerprint(bundle, model, kind, Some(limit))?;
    if let Some(req) = request {
        let rid = if req.opt("retry_of").truthy() { req.opt("retry_of") } else { req.opt("request_id") };
        if rid.as_str() != Some(&fingerprint) {
            return Err("Source audit request does not match requested model and inputs".into());
        }
    }
    let response_model = raw.opt("model").clone();
    if !response_model.is_null() {
        let ok = response_model.as_str().is_some_and(|m| m == model || m.starts_with(&format!("{model}-")));
        if !ok {
            return Err("Source audit returned another model".into());
        }
    }
    let mut req_subset = obj! {};
    if let Some(req) = request {
        for k in ["request_id", "path", "cached", "retry_of"] {
            if req.contains(k) {
                req_subset.set(k, req.opt(k).clone());
            }
        }
    }
    let mut artifact = obj! {"version" => VERSION, "model" => model, "response_model" => response_model,
    "request_kind" => kind, "request_fingerprint" => fingerprint, "output_limit" => limit,
    "prompt_sha256" => sha256_hex(prompts::SCENE_EVIDENCE.as_bytes()),
    "proposal" => snapshot.clone(), "proposal_sha256" => json_hash(&snapshot), "result" => result,
    "response_sha256" => json_hash(raw), "request" => req_subset};
    let digest = json_hash(&artifact);
    artifact.set("evidence_sha256", digest);
    Ok(artifact)
}

fn gate_inner(evidence: &Value, bundle: &Value, frozen: Option<&str>) -> R<Value> {
    if !evidence.is_object() {
        return Err("Source evidence missing".into());
    }
    let mut content = evidence.clone();
    content.remove("evidence_sha256");
    if Some(json_hash(&content).as_str()) != evidence.opt("evidence_sha256").as_str() {
        return Err("Source evidence changed".into());
    }
    let key = |k: &str| evidence.get(k).cloned().ok_or_else(|| Error::Value(format!("'{k}'")));
    if key("version")? != Value::Int(VERSION)
        || !key("model")?.as_str().is_some_and(|m| MODELS.contains(&m))
        || key("prompt_sha256")?.as_str() != Some(&sha256_hex(prompts::SCENE_EVIDENCE.as_bytes()))
    {
        return Err("Source evidence policy changed".into());
    }
    let snapshot = key("proposal")?;
    if Some(json_hash(&snapshot).as_str()) != key("proposal_sha256")?.as_str() {
        return Err("Frozen proposal changed".into());
    }
    let (sha, _) = source(bundle)?;
    if Some(sha.as_str()) != snapshot.opt("source_sha256").as_str() {
        return Err("Source evidence belongs to another page".into());
    }
    for k in ["classification", "reading_direction"] {
        if bundle.opt(k) != snapshot.opt(k) {
            return Err("Source classification or direction changed".into());
        }
    }
    let mut frozen_bundle = bundle.clone();
    for k in ["classification", "reading_direction", "panels"] {
        frozen_bundle.set(k, snapshot.opt(k).clone());
    }
    let limit = key("output_limit")?.as_int();
    if request_fingerprint(&frozen_bundle, key("model")?.as_str().unwrap(), key("request_kind")?.as_str().unwrap_or(""), limit)?
        != key("request_fingerprint")?.as_str().unwrap_or("")
    {
        return Err("Source audit request fingerprint changed".into());
    }
    match frozen {
        None => {
            if source_proposal(bundle)? != snapshot {
                return Err("Proposal changed without explicit frozen lineage".into());
            }
        }
        Some(link) => {
            let hex64 = link.len() == 64 && link.bytes().all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c));
            if !hex64 || Some(link) != key("proposal_sha256")?.as_str() {
                return Err("Frozen proposal link does not match".into());
            }
            let current = panels(bundle, false)?;
            let before = snapshot.opt("panels").as_array().unwrap();
            if current.len() != before.len() {
                return Err("Proposal inventory changed".into());
            }
            for (b, a) in before.iter().zip(&current) {
                let bb = crate::geometry::box4(b.opt("box")).unwrap();
                let ab = crate::geometry::box4(a.opt("box")).unwrap();
                if b.opt("order") != a.opt("order") || ab[0] > bb[0] || ab[1] > bb[1] || ab[2] < bb[2] || ab[3] < bb[3] {
                    return Err("Geometry is not a monotonic expansion of the frozen proposal".into());
                }
            }
        }
    }
    let orders: Vec<i64> = snapshot.opt("panels").as_array().unwrap().iter().map(|p| p.opt("order").as_int().unwrap()).collect();
    let value = key("result")?;
    validate_result(&value, &orders)?;
    let issues = value.opt("issues").as_array().unwrap();
    let blocking = issues.iter().any(|i| i.opt("kind").as_str() != Some("shared_unowned"));
    let status = value.opt("inventory_status").as_str();
    let status_ok = status == Some("complete") || (status == Some("uncertain") && !issues.is_empty() && !blocking);
    if !status_ok || blocking || value.opt("scenes").as_array().unwrap().iter().any(|s| s.opt("uncertain").as_bool() == Some(true)) {
        return Err("Source inventory or ownership remains unresolved".into());
    }
    Ok(obj! {"route" => "keep", "reason" => "Source evidence is linked and resolved; crop quality still requires checking",
    "evidence_sha256" => evidence.opt("evidence_sha256").clone(), "proposal_sha256" => evidence.opt("proposal_sha256").clone()})
}

/// `scene_evidence.evidence_gate` (never raises; failures escalate).
pub fn evidence_gate(evidence: &Value, bundle: &Value, frozen: Option<&str>) -> Value {
    match gate_inner(evidence, bundle, frozen) {
        Ok(v) => v,
        Err(e) => obj! {"route" => "escalate", "reason" => e.message()},
    }
}

/// `scene_evidence.verifier_hypotheses`.
pub fn verifier_hypotheses(evidence: &Value, bundle: &Value, frozen: Option<&str>) -> R<Value> {
    let gate = evidence_gate(evidence, bundle, frozen);
    if gate.opt("route").as_str() != Some("keep") {
        return Err(Error::Value(gate.opt("reason").as_str().unwrap_or("").to_string()));
    }
    let scenes: Vec<Value> = evidence
        .opt("result")
        .opt("scenes")
        .as_array()
        .unwrap()
        .iter()
        .map(|s| {
            // SCENE_FIELDS is a Python set: iteration order is hash order, but the
            // result only reaches requests through json.dumps(..., sort_keys=True).
            let mut m = obj! {};
            for k in SCENE_FIELDS {
                m.set(k, s.opt(k).clone());
            }
            m
        })
        .collect();
    Ok(obj! {"scenes" => Value::Array(scenes)})
}
