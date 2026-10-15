//! Bounded automatic escalation for one page (`automatic_escalation.run_page`).
//!
//! Sol-low → Sol-high → Astra detection, at most two verifier-directed
//! geometry repairs, one deterministic component repair, one completeness
//! redetection (plus one repair of it) and one deterministic merge. Exhausted
//! quality falls back to the whole page; budget/account/unknown-request
//! states stop the run resumably.

use crate::completeness::Completeness;
use crate::converter::{Converter, Shared};
use crate::error::{Error, R};
use crate::json::{Map, Value};
use crate::obj;
use std::path::Path;

pub const TIERS: [&str; 3] = ["sol-low", "sol-high", "astra"];
const MAX_REPAIRS: i64 = 2;

enum Slot {
    V(Value),
    S(Shared),
}

/// An attempt record whose candidate and judge stay live until serialization.
#[derive(Default)]
struct Attempt(Vec<(String, Slot)>);

impl Attempt {
    fn set(&mut self, key: &str, slot: Slot) {
        if let Some(entry) = self.0.iter_mut().find(|(k, _)| k == key) {
            entry.1 = slot;
        } else {
            self.0.push((key.to_string(), slot));
        }
    }
    fn value(&self) -> Value {
        let mut m = Map::new();
        for (k, slot) in &self.0 {
            let v = match slot {
                Slot::V(v) => v.clone(),
                Slot::S(s) => s.borrow().clone(),
            };
            m.insert(k.clone(), v);
        }
        Value::Object(m)
    }
}

fn route(verdict: &Value) -> R<bool> {
    match verdict.opt("route").as_str() {
        Some("keep") => Ok(true),
        Some("escalate") => Ok(false),
        _ => Err(Error::Blocked("invalid quality verdict; no acceptance".into())),
    }
}

struct Run<'c, 'a, 'b> {
    conv: &'c mut Converter<'a>,
    guard: &'c Completeness<'b>,
    page: &'c Path,
    attempts: Vec<Attempt>,
}

impl Run<'_, '_, '_> {
    fn passes(&mut self, candidate: &Shared) -> R<bool> {
        let verdict = self.conv.judge(self.page, candidate)?;
        self.attempts.last_mut().unwrap().set("judge", Slot::S(verdict.clone()));
        if !route(&verdict.borrow())? {
            let confirmation = self.conv.verify(self.page, candidate)?;
            self.attempts.last_mut().unwrap().set("verifier", Slot::V(confirmation.clone()));
            if !route(&confirmation)? {
                return Ok(false);
            }
        }
        let completeness = self.conv.final_accept(self.page, candidate, self.guard)?;
        self.attempts.last_mut().unwrap().set("completeness", Slot::V(completeness.clone()));
        route(&completeness)
    }

    /// Append an attempt for `raw`, refine it and check it; `Some` when accepted.
    fn attempt(&mut self, mut fields: Vec<(&str, Value)>, raw: Value) -> R<Option<Shared>> {
        fields.push(("raw", raw.clone()));
        let mut attempt = Attempt::default();
        for (k, v) in fields {
            attempt.set(k, Slot::V(v));
        }
        self.attempts.push(attempt);
        let candidate = self.conv.refine(self.page, &raw)?;
        self.attempts.last_mut().unwrap().set("candidate", Slot::S(candidate.clone()));
        Ok(if self.passes(&candidate)? { Some(candidate) } else { None })
    }

    fn last(&self) -> Value {
        self.attempts.last().map(Attempt::value).unwrap_or_else(|| obj! {})
    }

    fn body(&mut self) -> R<Option<Shared>> {
        for tier in TIERS {
            let raw = self.conv.detect(self.page, tier);
            // The attempt exists before detection, as in the prototype.
            let mut attempt = Attempt::default();
            attempt.set("tier", Slot::V(Value::from(tier)));
            self.attempts.push(attempt);
            let raw = raw?;
            self.attempts.last_mut().unwrap().set("raw", Slot::V(raw.clone()));
            let candidate = self.conv.refine(self.page, &raw)?;
            self.attempts.last_mut().unwrap().set("candidate", Slot::S(candidate.clone()));
            if self.passes(&candidate)? {
                return Ok(Some(candidate));
            }
        }
        for round in 1..=MAX_REPAIRS {
            let Some(raw) = self.conv.repair(self.page, &self.last())? else { break };
            let tier = raw.opt("tier").clone();
            if let Some(c) = self.attempt(vec![("tier", tier), ("stage", Value::from("geometry-repair")), ("repair_round", Value::from(round))], raw.clone())? {
                return Ok(Some(c));
            }
            if raw.get("repair_changed") == Some(&Value::Bool(false)) {
                break;
            }
        }
        if let Some(raw) = self.conv.pixel_repair(self.page, &self.last())? {
            let tier = raw.opt("tier").clone();
            if let Some(c) = self.attempt(vec![("tier", tier), ("stage", Value::from("component-repair"))], raw)? {
                return Ok(Some(c));
            }
        }
        let last = self.last();
        let rejection = last.get("completeness").cloned().unwrap_or_else(|| obj! {});
        if rejection.is_object()
            && rejection.opt("route").as_str() == Some("escalate")
            && rejection.opt("disposition").as_str() == Some("missing")
            && rejection.get("unresolved") == Some(&Value::Array(vec![]))
        {
            if let Some(raw) = self.conv.completeness_redetect(self.page, &last)? {
                let tier = raw.opt("tier").clone();
                if let Some(c) = self.attempt(vec![("tier", tier), ("stage", Value::from("completeness-redetection"))], raw)? {
                    return Ok(Some(c));
                }
                let redetected = self.last();
                if let Some(raw) = self.conv.repair(self.page, &redetected)? {
                    let tier = raw.opt("tier").clone();
                    let identity = redetected.opt("candidate").opt("identity").clone();
                    let fields = vec![("tier", tier), ("stage", Value::from("post-completeness-geometry-repair")), ("repair_round", Value::Int(1)), ("completeness_redetection_candidate", identity)];
                    if let Some(c) = self.attempt(fields, raw)? {
                        return Ok(Some(c));
                    }
                }
            }
        }
        for index in (0..self.attempts.len()).rev() {
            let previous = self.attempts[index].value();
            let rejection = previous.opt("completeness");
            let bijection = rejection.opt("unresolved").as_array().is_some_and(|u| u.iter().any(|x| x.as_str() == Some("incomplete_bijection")));
            if rejection.is_object() && rejection.opt("route").as_str() == Some("escalate") && bijection {
                if let Some(raw) = self.conv.completeness_merge(self.page, &previous)? {
                    let tier = raw.opt("tier").clone();
                    if let Some(c) = self.attempt(vec![("tier", tier), ("stage", Value::from("completeness-merge"))], raw)? {
                        return Ok(Some(c));
                    }
                }
                break;
            }
        }
        Ok(None)
    }
}

/// Run one page; returns `{status, selected, attempts[, reason]}`.
pub fn run_page(conv: &mut Converter, page: &Path, guard: &Completeness) -> R<Value> {
    let mut run = Run { conv, guard, page, attempts: Vec::new() };
    let outcome = run.body();
    let attempts = Value::Array(run.attempts.iter().map(Attempt::value).collect());
    Ok(match outcome {
        Ok(Some(selected)) => obj! {"status" => "accepted", "selected" => selected.borrow().clone(), "attempts" => attempts},
        Ok(None) => obj! {"status" => "whole_page_fallback", "selected" => Value::Null, "attempts" => attempts,
            "reason" => "bounded detector and repair attempts exhausted without a passing quality verdict"},
        Err(Error::PageBudget(m)) => obj! {"status" => "whole_page_fallback", "selected" => Value::Null, "attempts" => attempts, "reason" => m},
        Err(Error::Blocked(m)) => obj! {"status" => "blocked", "selected" => Value::Null, "attempts" => attempts, "reason" => m},
        Err(other) => return Err(other),
    })
}
