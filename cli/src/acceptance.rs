//! Acceptance provenance binding (`acceptance_binding.py`).

use crate::completeness;
use crate::error::{require, R};
use crate::json::{self, Value};
use crate::obj;
use crate::util::{sha256_hex, sha_file};
use std::path::Path;

pub const POLICY: &str = "automatic-marked-target-completeness-v63";

/// `digest`: compact sorted JSON.
pub fn digest(value: &Value) -> String {
    sha256_hex(json::dumps_with(value, json::SORTED_COMPACT).as_bytes())
}

fn is_hex64(s: &str) -> bool {
    s.len() == 64 && s.bytes().all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
}

/// `validate_acceptance` with the proof mode of the gate that produced it.
pub fn validate_acceptance(page: &Path, candidate: &Value, verdict: &Value, mode: &str) -> R<String> {
    require(verdict.is_object() && verdict.opt("route").as_str() == Some("keep"), "Missing passing completeness verdict")?;
    let proof = verdict.opt("proof");
    require(proof.as_object().is_some_and(|m| m.len() == 2 && m.contains_key("path") && m.contains_key("sha256")), "Missing bound completeness proof")?;
    require(proof.opt("sha256").as_str().is_some_and(is_hex64), "Invalid completeness proof hash")?;
    require(Some(sha_file(Path::new(proof.opt("path").as_str().unwrap_or("")))?.as_str()) == proof.opt("sha256").as_str(), "Completeness proof changed")?;
    let checked = completeness::validate_proof(page, candidate, proof, true, mode)?;
    require(&checked == verdict && checked.opt("route").as_str() == Some("keep"), "Stored completeness verdict differs from validated proof")?;
    Ok(proof.opt("sha256").as_str().unwrap().to_string())
}

/// `validate_page_record`: both new and resumed records bind the two source byte sets.
pub fn validate_page_record(publication: &Path, analysis: &Path, record: &Value, result: &Value, ordinal: i64) -> R<Value> {
    require(ordinal > 0 && record.opt("source_page").as_int().is_some_and(|v| v > 0), "Invalid output/source page order")?;
    require(result.opt("policy").as_str() == Some(POLICY), "Old or unbound page policy")?;
    require(result.opt("page").as_int() == Some(ordinal) && result.opt("source_page").as_int().is_some() && result.opt("source_page") == record.opt("source_page"), "Page source/order changed")?;
    let (publication_hash, analysis_hash) = (sha_file(publication)?, sha_file(analysis)?);
    require(record.opt("sha256").as_str() == Some(&publication_hash) && result.opt("source_sha256").as_str() == Some(&publication_hash), "Publication source changed")?;
    require(result.opt("analysis_source_sha256").as_str() == Some(&analysis_hash), "Analysis source changed")?;
    let status = result.opt("status").as_str();
    require(matches!(status, Some("accepted" | "whole_page_fallback")), "Page is not publishable")?;
    let (mut proof_hash, mut identity, mut direction, mut reason) = (Value::Null, Value::Null, Value::Null, Value::Null);
    if status == Some("accepted") {
        let selected = result.opt("selected");
        let attempts = result.opt("attempts").as_array();
        require(selected.is_object() && attempts.is_some_and(|a| !a.is_empty()), "Missing selected acceptance attempt")?;
        let last = attempts.unwrap().last().unwrap();
        require(last.is_object() && last.opt("candidate") == selected, "Selected candidate is not the final accepted attempt")?;
        let (judge, verifier) = (last.opt("judge"), last.opt("verifier"));
        let quality = judge.is_object()
            && ((judge.opt("route").as_str() == Some("keep") && !last.contains("verifier"))
                || (judge.opt("route").as_str() == Some("escalate") && verifier.is_object() && verifier.opt("route").as_str() == Some("keep")));
        require(quality, "Invalid quality trace: existing quality did not pass")?;
        require(selected.opt("source_sha256").as_str() == Some(&analysis_hash), "Candidate analysis source changed")?;
        let proposal = selected.opt("panels");
        require(matches!(proposal.opt("classification").as_str(), Some("panels" | "whole_page")), "Blank or malformed acceptance is not qualified")?;
        direction = proposal.opt("reading_direction").clone();
        require(matches!(direction.as_str(), Some("ltr" | "rtl")), "Invalid accepted reading direction")?;
        proof_hash = Value::from(validate_acceptance(analysis, selected, last.opt("completeness"), "normal")?);
        identity = selected.opt("identity").clone();
    } else {
        require(result.opt("selected").is_null(), "Fallback must not retain accepted geometry")?;
        reason = result.opt("reason").clone();
        require(reason.as_str().is_some_and(|r| !r.trim().is_empty()), "Fallback reason missing")?;
    }
    Ok(obj! {"page" => ordinal, "source_page" => record.opt("source_page").clone(),
        "source_sha256" => publication_hash, "analysis_source_sha256" => analysis_hash,
        "status" => status, "reading_direction" => direction,
        "candidate_identity" => identity, "completeness_proof_sha256" => proof_hash, "fallback_reason" => reason})
}

/// `publication_inputs`.
pub fn publication_inputs(entries: &[Value], bindings: &[Value], frames: &[Vec<String>], title: &str, direction: &str, auxiliary: &Value) -> R<Value> {
    require(matches!(direction, "ltr" | "rtl"), "Invalid publication reading direction")?;
    require(entries.len() == bindings.len() && bindings.len() == frames.len() && !entries.is_empty(), "Publication binding count differs")?;
    let mut pages = Vec::new();
    for (i, ((entry, binding), f)) in entries.iter().zip(bindings).zip(frames).enumerate() {
        let ordinal = i as i64 + 1;
        require(entry.opt("page").as_int() == Some(ordinal) && binding.opt("page").as_int() == Some(ordinal), "Publication order changed")?;
        require(binding.opt("reading_direction").is_null() || binding.opt("reading_direction").as_str() == Some(direction), "Publication direction contradicts accepted source")?;
        pages.push(binding.with("entry", entry.clone()).with("expected_frames", Value::from(f.clone())));
    }
    Ok(obj! {"schema" => "comic-publication-input-v1", "policy" => POLICY, "title" => title,
        "reading_direction" => direction, "pages" => Value::Array(pages), "auxiliary" => auxiliary.clone()})
}

/// `bind_manifest`: refuse adapter fallback or mapping changes beneath an accepted claim.
pub fn bind_manifest(manifest: &Value, inputs: &Value) -> R<Value> {
    let expected = inputs.opt("pages").as_array().unwrap();
    require(manifest.opt("page_count").as_int() == Some(expected.len() as i64) && manifest.opt("reading_direction") == inputs.opt("reading_direction"), "Adapter publication identity differs")?;
    let actual = manifest.opt("pages").as_array();
    require(actual.is_some_and(|a| a.len() == expected.len()), "Adapter page inventory differs")?;
    for (p, e) in actual.unwrap().iter().zip(expected) {
        let frames = e.opt("expected_frames");
        require(p.opt("page") == e.opt("page") && p.opt("source_page") == e.opt("source_page")
            && p.opt("source_image") == e.opt("entry").opt("image") && p.opt("sha256") == e.opt("source_sha256")
            && p.opt("frames") == frames && p.opt("frame_count").as_int() == Some(frames.as_array().map(Vec::len).unwrap_or(0) as i64)
            && p.opt("fallback_reason") == e.opt("fallback_reason"), "Adapter changed source, geometry or acceptance status")?;
    }
    let preserved = manifest.opt("preserved_auxiliary").as_array();
    let pairs: Option<Vec<Value>> = preserved.map(|items| items.iter().map(|i| obj! {"source" => i.opt("source").clone(), "sha256" => i.opt("sha256").clone()}).collect());
    require(pairs.is_some_and(|p| Value::Array(p) == *inputs.opt("auxiliary")), "Adapter auxiliary bytes differ")?;
    Ok(manifest.with("publication_inputs", inputs.clone()).with("publication_input_sha256", digest(inputs)))
}

/// `validate_archive_reuse`.
pub fn validate_archive_reuse(output: &Path, manifest: &Value, inputs: &Value) -> R<()> {
    require(manifest.opt("publication_inputs") == inputs && manifest.opt("publication_input_sha256").as_str() == Some(&digest(inputs)), "Published input/proof binding changed; use a new output")?;
    require(Some(sha_file(output)?.as_str()) == manifest.opt("output_sha256").as_str(), "Published archive changed")?;
    require(&bind_manifest(manifest, inputs)? == manifest, "Published manifest changed")
}
