//! Model-facing schemas and strict parsers for every structured response.
//!
//! Error messages mirror the prototype because they become durable reasons in
//! page records (invalid candidates, blocked runs).

use crate::json::{self, Value};
use crate::{arr, obj};

/// `(reservation, input $/M, output $/M)` from `openai_probe.PRICES`.
pub fn prices(model: &str) -> Option<(i64, Value, Value)> {
    match model {
        "gpt-6-astra" => Some((700000, Value::Float(12.5), Value::Int(50))),
        "gpt-6-sol" => Some((140000, Value::Float(2.5), Value::Int(10))),
        "gpt-6-luna" => Some((7000, Value::Float(0.125), Value::Float(0.5))),
        "gpt-5.6-luna" => Some((15000, Value::Float(0.25), Value::Float(1.2))),
        _ => None,
    }
}

fn int_field(minimum: i64, maximum: Option<i64>) -> Value {
    let mut v = obj! {"type" => "integer", "minimum" => minimum};
    if let Some(m) = maximum {
        v.set("maximum", m);
    }
    v
}

/// `contract.SCHEMA` (the Gemini-era panel contract).
pub fn base_schema() -> Value {
    obj! {
        "type" => "object",
        "properties" => obj! {
            "classification" => obj! {"type" => "string", "enum" => arr!["panels", "whole_page", "blank"]},
            "orientation" => obj! {"type" => "string", "enum" => arr!["upright", "rotate_90", "rotate_180", "rotate_270"]},
            "reading_direction" => obj! {"type" => "string", "enum" => arr!["ltr", "rtl"]},
            "panels" => obj! {"type" => "array", "minItems" => 1, "items" => obj! {
                "type" => "object", "properties" => obj! {
                    "order" => int_field(1, None),
                    "box" => obj! {"type" => "array", "minItems" => 4, "maxItems" => 4, "items" => int_field(0, Some(1000))},
                }, "required" => arr!["order", "box"],
            }},
        },
        "required" => arr!["classification", "orientation", "reading_direction", "panels"],
    }
}

/// `gemini_probe.schema()`: panels carry order, description and bounds.
pub fn schema() -> Value {
    let mut s = base_schema();
    let bounds_props = obj! {
        "left" => int_field(0, Some(1000)), "top" => int_field(0, Some(1000)),
        "right" => int_field(0, Some(1000)), "bottom" => int_field(0, Some(1000)),
    };
    let items = obj! {"type" => "object", "properties" => obj! {
        "order" => int_field(1, None), "description" => obj! {"type" => "string"},
        "bounds" => obj! {"type" => "object", "properties" => bounds_props, "required" => arr!["left", "top", "right", "bottom"]},
    }, "required" => arr!["order", "description", "bounds"]};
    s.get_mut("properties").unwrap().get_mut("panels").unwrap().set("items", items);
    s
}

fn close(x: &mut Value) {
    match x {
        Value::Object(m) => {
            if m.get("type").and_then(Value::as_str) == Some("object") {
                m.insert("additionalProperties".into(), Value::Bool(false));
                let keys: Vec<Value> = m.get("properties").and_then(Value::as_object).map(|p| p.keys().map(|k| Value::from(k.as_str())).collect()).unwrap_or_default();
                m.insert("required".into(), Value::Array(keys));
            }
            for v in m.values_mut() {
                close(v);
            }
        }
        Value::Array(a) => a.iter_mut().for_each(close),
        _ => {}
    }
}

/// `openai_probe.strict_schema()`.
pub fn strict_schema() -> Value {
    let mut s = schema();
    close(&mut s);
    s
}

/// `contract.validate_page`.
pub fn validate_page(value: &Value, expected_direction: &str) -> Result<(), String> {
    if !value.is_object() {
        return Err("page must be an object".into());
    }
    if !matches!(value.opt("classification").as_str(), Some("panels" | "whole_page" | "blank")) {
        return Err("invalid page classification".into());
    }
    if value.opt("orientation").as_str() != Some("upright") {
        return Err("analysis image is not upright; refusing geometry remapping".into());
    }
    if !matches!(expected_direction, "ltr" | "rtl" | "auto") {
        return Err("invalid expected reading direction".into());
    }
    let direction = value.opt("reading_direction").as_str();
    if !matches!(direction, Some("ltr" | "rtl")) {
        return Err("invalid response reading direction".into());
    }
    if expected_direction != "auto" && direction != Some(expected_direction) {
        return Err("response disagrees with requested reading direction".into());
    }
    let panels = match value.opt("panels").as_array() {
        Some(p) if !p.is_empty() => p,
        _ => return Err("panels must be a nonempty array".into()),
    };
    for (i, panel) in panels.iter().enumerate() {
        let order = i as i64 + 1;
        if !panel.is_object() || panel.opt("order").as_int() != Some(order) {
            return Err("panel order must agree with 1-based array position".into());
        }
        let b = match panel.opt("box").as_array() {
            Some(b) if b.len() == 4 => b,
            _ => return Err(format!("panel {order}: expected four y/x bounds")),
        };
        if b.iter().any(|n| !matches!(n.as_int(), Some(v) if (0..=1000).contains(&v))) {
            return Err(format!("panel {order}: bounds must be integers in 0..1000"));
        }
        let v: Vec<i64> = b.iter().map(|n| n.as_int().unwrap()).collect();
        if !(v[0] < v[2] && v[1] < v[3]) {
            return Err(format!("panel {order}: bounds must have positive area"));
        }
    }
    if matches!(value.opt("classification").as_str(), Some("whole_page" | "blank"))
        && (panels.len() != 1 || panels[0].opt("box") != &arr![0, 0, 1000, 1000])
    {
        return Err("whole-page classifications require one full-page box".into());
    }
    Ok(())
}

fn key_error(k: &str) -> String {
    format!("'{k}'")
}

/// `gemini_probe.parse` applied to the concatenated output text.
fn parse_panels_text(text: &str, expected_direction: &str) -> Result<Value, String> {
    let mut result = json::loads(text).map_err(|e| e.0)?;
    let panels = match result.get_mut("panels") {
        Some(Value::Array(p)) => p,
        Some(_) => return Err("'list' object expected".into()),
        None => return Err(key_error("panels")),
    };
    for panel in panels.iter_mut() {
        let bounds = panel.remove("bounds").ok_or_else(|| key_error("bounds"))?;
        let get = |k: &str| bounds.get(k).cloned().ok_or_else(|| key_error(k));
        let b = arr![get("top")?, get("left")?, get("bottom")?, get("right")?];
        panel.set("box", b);
    }
    validate_page(&result, expected_direction)?;
    Ok(result)
}

/// `openai_probe.response_panels`.
pub fn response_panels(raw: &Value, expected_direction: &str) -> Result<Value, String> {
    if raw.opt("status").as_str() != Some("completed") {
        return Err("response did not complete".into());
    }
    let mut text = String::new();
    for item in raw.opt("output").as_array().cloned().unwrap_or_default() {
        if item.opt("type").as_str() != Some("message") {
            continue;
        }
        if !matches!(item.opt("status"), Value::Null) && item.opt("status").as_str() != Some("completed") {
            return Err("message incomplete".into());
        }
        for part in item.opt("content").as_array().cloned().unwrap_or_default() {
            if part.opt("type").as_str() == Some("refusal") {
                return Err("provider refusal".into());
            }
            if part.opt("type").as_str() == Some("output_text") {
                text.push_str(part.get("text").and_then(Value::as_str).ok_or_else(|| key_error("text"))?);
            }
        }
    }
    parse_panels_text(&text, expected_direction)
}

/// `{'promptTokenCount': input_tokens, 'totalTokenCount': total_tokens}`.
pub fn response_usage(raw: &Value) -> Value {
    let u = raw.opt("usage");
    obj! {"promptTokenCount" => u.opt("input_tokens").clone(), "totalTokenCount" => u.opt("total_tokens").clone()}
}

/// `auto_convert.responses_output_exhausted`.
pub fn responses_output_exhausted(raw: &Value) -> bool {
    if !raw.is_object() || raw.opt("status").as_str() != Some("incomplete") {
        return false;
    }
    let details = raw.opt("incomplete_details");
    let Some(output) = raw.opt("output").as_array() else { return false };
    if !details.is_object() || details.opt("reason").as_str() != Some("max_output_tokens") {
        return false;
    }
    for item in output {
        let kind = item.opt("type").as_str();
        if !item.is_object() || !matches!(kind, Some("reasoning" | "message")) {
            return false;
        }
        let reasoning = kind == Some("reasoning");
        let content = match item.get("content") {
            Some(c) => c.clone(),
            None if reasoning => Value::Array(vec![]),
            None => Value::Null,
        };
        let Some(content) = content.as_array() else { return false };
        let part_type = if reasoning { "reasoning_text" } else { "output_text" };
        if content.iter().any(|p| !p.is_object() || p.opt("type").as_str() != Some(part_type) || !p.opt("text").is_str()) {
            return false;
        }
        if reasoning {
            let summary = item.get("summary").cloned().unwrap_or(Value::Array(vec![]));
            let Some(summary) = summary.as_array() else { return false };
            if summary.iter().any(|p| !p.is_object() || p.opt("type").as_str() != Some("summary_text") || !p.opt("text").is_str()) {
                return false;
            }
        }
    }
    true
}

// ---------------------------------------------------------------- verifier verdicts

pub const CHECKS: [&str; 3] = ["scene_inventory", "reading_order", "crop_coverage"];
pub const KINDS: [&str; 8] = ["missing_scene", "merged_scenes", "false_split", "clipped_text", "clipped_art", "wrong_order", "wrong_classification", "uncertain"];

/// `escalation_probe.verdict_schema()`.
pub fn verdict_schema() -> Value {
    let mut properties = obj! {"decision" => obj! {"type" => "string", "enum" => arr!["accept", "escalate", "uncertain"]}};
    for k in CHECKS {
        properties.set(k, obj! {"type" => "string", "enum" => arr!["pass", "fail", "uncertain"]});
    }
    let issue = obj! {"kind" => obj! {"type" => "string", "enum" => Value::from(KINDS.to_vec())},
        "panels" => obj! {"type" => "array", "items" => obj! {"type" => "integer", "minimum" => 1}},
        "evidence" => obj! {"type" => "string"}};
    properties.set("issues", obj! {"type" => "array", "items" => obj! {"type" => "object", "properties" => issue,
        "required" => arr!["kind", "panels", "evidence"], "additionalProperties" => false}});
    let required: Vec<Value> = properties.as_object().unwrap().keys().map(|k| Value::from(k.as_str())).collect();
    obj! {"type" => "object", "properties" => properties, "required" => Value::Array(required), "additionalProperties" => false}
}

fn output_texts(raw: &Value, incomplete: &str, refusal: &str) -> Result<Vec<String>, String> {
    let mut texts = Vec::new();
    for item in raw.opt("output").as_array().cloned().unwrap_or_default() {
        if item.opt("type").as_str() != Some("message") {
            continue;
        }
        if !item.opt("status").is_null() && item.opt("status").as_str() != Some("completed") {
            return Err(incomplete.into());
        }
        for part in item.opt("content").as_array().cloned().unwrap_or_default() {
            if part.opt("type").as_str() == Some("refusal") {
                return Err(refusal.into());
            }
            if part.opt("type").as_str() == Some("output_text") {
                texts.push(part.opt("text").as_str().unwrap_or("").to_string());
            }
        }
    }
    Ok(texts)
}

/// `escalation_probe.parse_verdict`.
pub fn parse_verdict(raw: &Value, panel_count: usize) -> Result<Value, String> {
    if raw.opt("status").as_str() != Some("completed") {
        return Err("judge response incomplete; never accept".into());
    }
    let texts = output_texts(raw, "judge message incomplete", "judge refusal; never accept")?;
    let value = json::loads(&texts.concat()).map_err(|_| "judge JSON missing or invalid".to_string())?;
    let Some(m) = value.as_object() else { return Err("judge verdict fields invalid".into()) };
    let mut want: Vec<&str> = vec!["decision", "issues"];
    want.extend(CHECKS);
    if m.len() != want.len() || !want.iter().all(|k| m.contains_key(*k)) {
        return Err("judge verdict fields invalid".into());
    }
    if !matches!(value.opt("decision").as_str(), Some("accept" | "escalate" | "uncertain"))
        || CHECKS.iter().any(|k| !matches!(value.opt(k).as_str(), Some("pass" | "fail" | "uncertain")))
    {
        return Err("judge verdict enum invalid".into());
    }
    let Some(issues) = value.opt("issues").as_array() else { return Err("judge issues invalid".into()) };
    for issue in issues {
        let ok = issue.as_object().is_some_and(|o| o.len() == 3 && o.contains_key("kind") && o.contains_key("panels") && o.contains_key("evidence"))
            && issue.opt("kind").as_str().is_some_and(|k| KINDS.contains(&k))
            && issue.opt("panels").as_array().is_some_and(|p| p.iter().all(|n| matches!(n.as_int(), Some(v) if v >= 1 && v <= panel_count as i64)))
            && issue.opt("evidence").as_str().is_some_and(|e| !e.trim().is_empty());
        if !ok {
            return Err("judge issue invalid".into());
        }
    }
    let keep = value.opt("decision").as_str() == Some("accept") && issues.is_empty() && CHECKS.iter().all(|k| value.opt(k).as_str() == Some("pass"));
    Ok(value.with("route", if keep { "keep" } else { "escalate" }))
}

/// `continuity_verifier.SCHEMA`.
pub fn continuity_schema() -> Value {
    obj! {"type" => "object", "properties" => obj! {
        "classification" => obj! {"type" => "string", "enum" => arr!["continuous", "distinct", "uncertain"]},
        "views" => obj! {"type" => "array", "items" => obj! {"type" => "string"}},
        "evidence" => obj! {"type" => "string"}},
        "required" => arr!["classification", "views", "evidence"], "additionalProperties" => false}
}

/// `continuity_verifier.response_verdict`.
pub fn continuity_verdict(raw: &Value) -> Result<Value, String> {
    let status = raw.get("status").cloned().unwrap_or(Value::from("completed"));
    if status.as_str() != Some("completed") {
        return Err("incomplete source-continuity adjudication".into());
    }
    let mut text = String::new();
    for v in raw.opt("output").as_array().cloned().unwrap_or_default() {
        for c in v.opt("content").as_array().cloned().unwrap_or_default() {
            if c.opt("type").as_str() == Some("output_text") {
                text.push_str(c.opt("text").as_str().unwrap_or(""));
            }
        }
    }
    let value = json::loads(&text).map_err(|e| e.0)?;
    let ok_fields = value.as_object().is_some_and(|m| m.len() == 3 && ["classification", "views", "evidence"].iter().all(|k| m.contains_key(*k)));
    if !ok_fields {
        return Err("invalid source-continuity fields".into());
    }
    let classification = value.opt("classification").as_str();
    if !matches!(classification, Some("continuous" | "distinct" | "uncertain")) {
        return Err("invalid source-continuity classification".into());
    }
    let views = value.opt("views").as_array();
    if views.is_none() || views.unwrap().iter().any(|v| !v.as_str().is_some_and(|s| !s.trim().is_empty())) {
        return Err("invalid source-continuity view descriptions".into());
    }
    if !value.opt("evidence").as_str().is_some_and(|s| !s.trim().is_empty()) {
        return Err("source-continuity evidence required".into());
    }
    let n = views.unwrap().len();
    if classification == Some("distinct") && n < 2 {
        return Err("distinct verdict requires multiple described views".into());
    }
    if classification == Some("continuous") && n != 1 {
        return Err("continuous verdict requires one described view".into());
    }
    Ok(value)
}

// ---------------------------------------------------------------- native decisions

pub const DECISION_MODEL: &str = "gpt-6-luna";
pub const DECISION_THRESHOLD: f64 = 0.5;

/// `decisions_probe.parse_answers`.
pub fn parse_answers(raw: &Value, questions: &Value) -> Result<Value, String> {
    let model_ok = raw.is_object() && raw.opt("model").as_str().map(|m| m.to_string()).unwrap_or_else(|| json::dumps(raw.opt("model"))).starts_with(DECISION_MODEL);
    if !model_ok {
        return Err("unexpected Decisions model".into());
    }
    let questions = questions.as_array().unwrap();
    let answers = match raw.opt("answers").as_array() {
        Some(a) if a.len() == questions.len() => a,
        _ => return Err("missing Decisions answers; never keep".into()),
    };
    let mut probabilities = crate::json::Map::new();
    for (q, a) in questions.iter().zip(answers) {
        if !a.is_object() || a.opt("type").as_str() != Some("predicate") || a.opt("name") != q.opt("name") {
            return Err("refused/mismatched Decisions answer; never keep".into());
        }
        let p = a.opt("probability");
        let ok = matches!(p, Value::Int(_) | Value::Float(_)) && p.as_f64().is_some_and(|v| v.is_finite() && (0.0..=1.0).contains(&v));
        if !ok {
            return Err("invalid Decisions probability; never keep".into());
        }
        probabilities.insert(q.opt("name").as_str().unwrap().to_string(), p.clone());
    }
    let max = probabilities.values().filter_map(Value::as_f64).fold(f64::NEG_INFINITY, f64::max);
    Ok(obj! {"route" => if max >= DECISION_THRESHOLD { "escalate" } else { "keep" },
        "threshold" => DECISION_THRESHOLD, "probabilities" => Value::Object(probabilities)})
}

/// `decisions_probe.decision_cost`: `Ok(None)` when usage lacks input tokens.
pub fn decision_cost(usage: &Value) -> Result<Option<i64>, String> {
    let Some(tokens) = usage.get("input_tokens") else { return Ok(None) };
    let t = match tokens.as_int() {
        Some(t) if t >= 0 => t,
        _ => return Err("unexpected native Decisions usage; retain hold".into()),
    };
    if usage.opt("output_tokens") != &Value::Int(0) || usage.opt("total_tokens") != tokens {
        return Err("unexpected native Decisions usage; retain hold".into());
    }
    let rate = if t > 272000 { 2 } else { 1 };
    Ok(Some((t * rate + 9) / 10))
}

/// Exact decimal of `str(rate)` as numerator / 10^scale.
fn decimal(rate: &Value) -> (i128, u32) {
    let text = match rate {
        Value::Int(i) => i.to_string(),
        Value::Float(f) => json::float_repr(*f),
        _ => "0".into(),
    };
    match text.split_once('.') {
        Some((a, b)) => (format!("{a}{b}").parse().unwrap(), b.len() as u32),
        None => (text.parse().unwrap(), 0),
    }
}

/// `gemini_budget.usage_cost`: `Ok(None)` when token counts are absent.
pub fn usage_cost(usage: &Value, input_rate: &Value, output_rate: &Value) -> Result<Option<i64>, String> {
    if !usage.contains("promptTokenCount") || !usage.contains("totalTokenCount") {
        return Ok(None);
    }
    let (inp, total) = match (usage.opt("promptTokenCount").as_int(), usage.opt("totalTokenCount").as_int()) {
        (Some(i), Some(t)) if 0 <= i && i <= t => (i, t),
        _ => return Err("invalid usage; keep reservation".into()),
    };
    let (a, sa) = decimal(input_rate);
    let (b, sb) = decimal(output_rate);
    let scale = sa.max(sb);
    let num = a * 10i128.pow(scale - sa) * inp as i128 + b * 10i128.pow(scale - sb) * (total - inp) as i128;
    let den = 10i128.pow(scale);
    Ok(Some(((num + den - 1).div_euclid(den)) as i64))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn costs_match_decimal_ceil() {
        let usage = obj! {"promptTokenCount" => 12345, "totalTokenCount" => 20000};
        // ceil(2.5*12345 + 10*7655) = ceil(30862.5 + 76550) = 107413
        assert_eq!(usage_cost(&usage, &Value::Float(2.5), &Value::Int(10)).unwrap(), Some(107413));
        let usage = obj! {"input_tokens" => 999, "output_tokens" => 0, "total_tokens" => 999};
        assert_eq!(decision_cost(&usage).unwrap(), Some(100));
    }

    #[test]
    fn strict_schema_closes_objects() {
        let s = strict_schema();
        assert_eq!(s.opt("additionalProperties"), &Value::Bool(false));
        let bounds = s.opt("properties").opt("panels").opt("items").opt("properties").opt("bounds");
        assert_eq!(bounds.opt("required"), &arr!["left", "top", "right", "bottom"]);
    }
}
