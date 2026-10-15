//! Durable, cached OpenAI client: one request identity per exact request body.
//!
//! Identities are `sha256(prefix + json.dumps(body, sort_keys=True))`, so any
//! byte-identical request made by the prototype or by this binary reuses the
//! same recorded response. Unknown outcomes never replay automatically; the
//! named one-shot recoveries follow the prototype's rules exactly.

use crate::budget::Budget;
use crate::contract;
use crate::error::{Error, R};
use crate::json::{self, Value};
use crate::obj;
use crate::util::{self, read_json, save, sha256_hex};
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::Instant;

pub const PAGE_GRACE: i64 = 400_000;
pub const ASTRA_TIER_MIN: i64 = 300_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Kind {
    Native,
    Detector,
    Verifier,
}

impl Kind {
    fn prefix(self) -> &'static [u8] {
        match self {
            Kind::Native => b"https://api.openai.com/v1/decisions\n",
            Kind::Detector => b"openai-responses:",
            Kind::Verifier => b"comic-escalation-judge-v1:",
        }
    }
    pub fn name(self) -> &'static str {
        match self {
            Kind::Native => "native",
            Kind::Detector => "detector",
            Kind::Verifier => "verifier",
        }
    }
}

pub fn identity(kind: Kind, body: &Value) -> String {
    let mut data = kind.prefix().to_vec();
    data.extend_from_slice(json::dumps_sorted(body).as_bytes());
    sha256_hex(&data)
}

/// `credit_balance_rejection`.
pub fn credit_balance_rejection(error: &str) -> bool {
    let Some(rest) = error.strip_prefix("HTTP 429:") else { return false };
    let Ok(value) = json::loads(rest.trim_start_matches(' ').trim_end()) else { return false };
    value.opt("error").opt("code").as_str() == Some("credit_balance_exhausted")
}

/// `transient_network_failure`.
pub fn transient_network_failure(error: &str) -> bool {
    error == "Remote end closed connection without response"
        || [(101, "Network is unreachable"), (113, "No route to host"), (111, "Connection refused"), (100, "Network is down")]
            .iter()
            .any(|(c, m)| error == format!("<urlopen error [Errno {c}] {m}>"))
}

/// `transient_server_rejection`.
pub fn transient_server_rejection(error: &str) -> bool {
    if error == "HTTP 503: upstream connect error or disconnect/reset before headers. reset reason: connection termination" {
        return true;
    }
    let Some(rest) = error.strip_prefix("HTTP 503:") else { return false };
    let Ok(value) = json::loads(rest) else { return false };
    let d = value.opt("error");
    d.is_object()
        && d.opt("type").as_str() == Some("server_error")
        && d.opt("message").as_str().is_some_and(|m| !m.trim().is_empty())
        && d.contains("param")
        && d.opt("param").is_null()
        && d.contains("code")
        && d.opt("code").is_null()
}

/// `gateway_failure`: an HTTP 500/502/503/504 HTML gateway page.
pub fn gateway_failure(error: &str) -> bool {
    let b = error.as_bytes();
    if b.len() < 9 || !error.starts_with("HTTP 50") || !matches!(b[7], b'0' | b'2' | b'3' | b'4') || &error[8..10.min(error.len())] != ": " {
        return false;
    }
    let body = error[9..].to_lowercase();
    body.trim_start().starts_with('<')
        && ["bad gateway", "gateway time-out", "gateway timeout", "service unavailable", "internal server error"].iter().any(|w| body.contains(w))
}

pub fn transient_failure(error: &str) -> bool {
    transient_server_rejection(error) || transient_network_failure(error) || gateway_failure(error)
}

struct State {
    budget: Budget,
    page_spent: i64,
    page_grace: bool,
    new_calls: u64,
    cache_hits: u64,
    retry_unknown: HashSet<String>,
    retry_rejected: HashSet<String>,
    retry_transient: HashSet<String>,
    retry_interrupted: HashSet<String>,
    retry_second: HashSet<String>,
}

pub struct Client {
    key: Option<String>,
    root: PathBuf,
    page_cap: Option<i64>,
    auto_transient: bool,
    state: Mutex<State>,
    http: Option<reqwest::blocking::Client>,
    base_url: String,
}

#[derive(Default)]
pub struct Recoveries {
    pub unknown: Vec<String>,
    pub rejected: Vec<String>,
    pub transient: Vec<String>,
    pub interrupted: Vec<String>,
    pub second: Vec<String>,
}

pub fn recovery_identity(kind: &str, identity: &str) -> String {
    sha256_hex(format!("explicit-{kind}-recovery-1:{identity}").as_bytes())
}

pub fn second_identity(identity: &str) -> String {
    sha256_hex(format!("explicit-second-transient-recovery-1:{identity}").as_bytes())
}

fn sanitized(body: &Value) -> R<Value> {
    let mut out = body.clone();
    if let Some(items) = out.get_mut("input").and_then(Value::as_array_mut) {
        for item in items {
            if let Some(parts) = item.get_mut("content").and_then(Value::as_array_mut) {
                for part in parts {
                    if part.opt("type").as_str() == Some("input_image") {
                        let url = part.remove("image_url").and_then(|v| v.as_str().map(String::from)).ok_or("'image_url'")?;
                        let (_, data) = url.split_once(',').ok_or("invalid data URL")?;
                        part.set("image_sha256", sha256_hex(&util::b64_decode(data)?));
                    }
                }
            }
        }
    }
    Ok(out)
}

impl Client {
    pub fn new(key: Option<String>, budget: Budget, root: &Path, retries: Recoveries, page_cap: Option<i64>, auto_transient: bool) -> R<Client> {
        std::fs::create_dir_all(root)?;
        if let Some(c) = page_cap {
            if c <= 0 {
                return Err("Invalid page spend limit".into());
            }
        }
        let groups = [&retries.unknown, &retries.rejected, &retries.transient, &retries.interrupted, &retries.second];
        let total: usize = groups.iter().map(|g| g.len()).sum();
        let union: HashSet<&String> = groups.iter().flat_map(|g| g.iter()).collect();
        if total != union.len() {
            return Err("Ambiguous recovery type".into());
        }
        let http = if key.is_some() {
            Some(reqwest::blocking::Client::builder().build().map_err(|e| e.to_string())?)
        } else {
            None
        };
        let set = |v: &Vec<String>| v.iter().cloned().collect::<HashSet<_>>();
        Ok(Client {
            key,
            root: root.to_path_buf(),
            page_cap,
            auto_transient,
            http,
            base_url: std::env::var("COMIC_PANEL_OPENAI_BASE").unwrap_or_else(|_| "https://api.openai.com/v1/".into()),
            state: Mutex::new(State {
                budget,
                page_spent: 0,
                page_grace: false,
                new_calls: 0,
                cache_hits: 0,
                retry_unknown: set(&retries.unknown),
                retry_rejected: set(&retries.rejected),
                retry_transient: set(&retries.transient),
                retry_interrupted: set(&retries.interrupted),
                retry_second: set(&retries.second),
            }),
        })
    }

    pub fn start_page(&self) {
        let mut s = self.state.lock().unwrap();
        s.page_spent = 0;
        s.page_grace = false;
    }

    pub fn set_grace(&self, grace: bool) {
        self.state.lock().unwrap().page_grace = grace;
    }

    pub fn page_remaining(&self) -> Option<i64> {
        self.page_cap.map(|c| c - self.state.lock().unwrap().page_spent)
    }

    pub fn page_spent(&self) -> i64 {
        self.state.lock().unwrap().page_spent
    }

    pub fn page_cap(&self) -> Option<i64> {
        self.page_cap
    }

    pub fn counters(&self) -> (u64, u64) {
        let s = self.state.lock().unwrap();
        (s.new_calls, s.cache_hits)
    }

    pub fn budget_used(&self) -> i64 {
        self.state.lock().unwrap().budget.used()
    }

    pub fn budget_cap(&self) -> i64 {
        self.state.lock().unwrap().budget.cap
    }

    fn limit_reached(&self, s: &State) -> Option<Error> {
        let cap = self.page_cap?;
        let limit = cap + if s.page_grace { PAGE_GRACE } else { 0 };
        (s.page_spent >= limit).then(|| Error::PageBudget(format!("page spend limit reached: {} of {} micro-USD", s.page_spent, cap)))
    }

    /// `Client.charge_cached`: cached answers count at their recorded cost.
    fn charge_cached(&self, s: &mut State, identities: &[&str]) -> R<()> {
        if self.page_cap.is_none() {
            return Ok(());
        }
        if let Some(e) = self.limit_reached(s) {
            return Err(e);
        }
        for id in identities {
            let entry = &s.budget.entries[*id];
            let cost = entry.get("cost").or_else(|| entry.get("reserve")).and_then(Value::as_int).unwrap_or(0);
            s.page_spent += cost;
        }
        Ok(())
    }

    fn http_call(&self, endpoint: &str, body: &Value) -> R<Value> {
        let (Some(client), Some(key)) = (&self.http, &self.key) else {
            return Err(Error::Blocked("CACHE_ONLY_MISS: HTTP disabled".into()));
        };
        let timeout = if endpoint == "responses" { 600 } else { 180 };
        let response = client
            .post(format!("{}{}", self.base_url, endpoint))
            .bearer_auth(key)
            .header("Content-Type", "application/json")
            .timeout(std::time::Duration::from_secs(timeout))
            .body(json::dumps(body))
            .send()
            .map_err(|e| Error::Value(transport_message(&e)))?;
        let status = response.status();
        let text = response.text().map_err(|e| Error::Value(transport_message(&e)))?;
        if !status.is_success() {
            return Err(Error::Blocked(format!("HTTP {}: {}", status.as_u16(), text.replace(key.as_str(), "[REDACTED]"))));
        }
        Ok(json::loads(&text)?)
    }

    fn second_recovery(&self, identity: &str, first: &str, endpoint: &str, kind: Kind, s: &State) -> R<String> {
        let path = PathBuf::from(s.budget.entries[first].opt("path").as_str().unwrap_or(""));
        let error = if path.join("error.json").is_file() { read_json(&path.join("error.json"))?.opt("error").as_str().unwrap_or("").to_string() } else { String::new() };
        if !transient_failure(&error) {
            return Err(Error::Blocked(format!("second recovery requires a recorded transient failure of the first recovery: {first}")));
        }
        let saved = if path.join("request.json").is_file() { read_json(&path.join("request.json"))? } else { obj! {} };
        if saved.opt("request_id").as_str() != Some(first)
            || saved.opt("request_fingerprint").as_str() != Some(identity)
            || saved.opt("retry_of").as_str() != Some(identity)
            || saved.opt("endpoint").as_str() != Some(endpoint)
            || saved.opt("kind").as_str() != Some(kind.name())
        {
            return Err(Error::Blocked(format!("second recovery requires the first recovery provenance: {first}")));
        }
        Ok(second_identity(identity))
    }

    fn cached(&self, s: &mut State, charge: &[&str], id: &str, retry_of: Option<&str>, dir: &Path) -> R<(Value, Value)> {
        self.charge_cached(s, charge)?;
        s.cache_hits += 1;
        let mut meta = obj! {"request_id" => id};
        if let Some(r) = retry_of {
            meta.set("retry_of", r);
        }
        meta.set("path", util::path_str(dir));
        meta.set("cached", true);
        Ok((read_json(&dir.join("response.json"))?, meta))
    }

    /// `Client.request`: returns `(raw_response, provenance)`.
    pub fn request(&self, endpoint: &str, body: &Value, kind: Kind) -> R<(Value, Value)> {
        let encoded = json::dumps_sorted(body);
        if encoded.len() > 19_000_000 {
            return Err(Error::Blocked("request too large".into()));
        }
        let mut identity = identity(kind, body);
        let original_identity = identity.clone();
        let mut retry_of: Option<String> = None;
        let out;
        let reserve;
        {
            let mut guard = self.state.lock().unwrap();
            let s = &mut *guard;
            if let Some(entry) = s.budget.entries.get(&identity).cloned() {
                let old = PathBuf::from(entry.opt("path").as_str().unwrap_or(""));
                if old.join("response.json").is_file() {
                    let id = identity.clone();
                    return self.cached(s, &[&id], &id, None, &old);
                }
                let recoveries: Vec<(&str, String)> = ["timeout", "quota", "transient-server", "interruption"].iter().map(|k| (*k, recovery_identity(k, &identity))).collect();
                let second = second_identity(&identity);
                if let Some(e) = s.budget.entries.get(&second).cloned() {
                    let recovered = PathBuf::from(e.opt("path").as_str().unwrap_or(""));
                    if !recovered.join("response.json").is_file() {
                        return Err(Error::Blocked(format!("second recovery also unknown; no further replay: {second}")));
                    }
                    let id = identity.clone();
                    return self.cached(s, &[&id, &second], &second, Some(&id), &recovered);
                }
                let mut failed_recovery: Option<String> = None;
                for (_, recovery) in &recoveries {
                    if let Some(e) = s.budget.entries.get(recovery).cloned() {
                        let recovered = PathBuf::from(e.opt("path").as_str().unwrap_or(""));
                        if !recovered.join("response.json").is_file() {
                            if !s.retry_second.contains(&identity) {
                                return Err(Error::Blocked(format!("recovery also unknown; no further replay: {recovery}")));
                            }
                            failed_recovery = Some(recovery.clone());
                            break;
                        }
                        let id = identity.clone();
                        return self.cached(s, &[&id, recovery], recovery, Some(&id), &recovered);
                    }
                }
                let error = if old.join("error.json").is_file() { read_json(&old.join("error.json"))?.opt("error").as_str().unwrap_or("").to_string() } else { String::new() };
                let in_other = |s: &State| s.retry_unknown.contains(&identity) || s.retry_rejected.contains(&identity) || s.retry_interrupted.contains(&identity);
                if self.auto_transient && failed_recovery.is_none() && transient_failure(&error) && !in_other(s) {
                    s.retry_transient.insert(identity.clone());
                }
                if failed_recovery.is_none() && !in_other(s) && !s.retry_transient.contains(&identity) {
                    return Err(Error::Blocked(format!("previous unknown request; no automatic replay: {identity}")));
                }
                let recovery = if let Some(first) = &failed_recovery {
                    self.second_recovery(&identity, first, endpoint, kind, s)?
                } else if s.retry_interrupted.contains(&identity) {
                    let original = if old.join("request.json").is_file() { read_json(&old.join("request.json"))? } else { obj! {} };
                    let proof = if old.join("interruption.json").is_file() { read_json(&old.join("interruption.json"))? } else { obj! {} };
                    let request_sha = if old.join("request.json").is_file() { util::sha_file(&old.join("request.json"))? } else { String::new() };
                    let ok = original.opt("request_id").as_str() == Some(&identity)
                        && original.opt("request_fingerprint").as_str() == Some(&identity)
                        && original.opt("retry_of").is_null()
                        && original.opt("endpoint").as_str() == Some(endpoint)
                        && original.opt("kind").as_str() == Some(kind.name())
                        && !old.join("error.json").exists()
                        && proof.opt("kind").as_str() == Some("confirmed_process_loss")
                        && proof.opt("request_id").as_str() == Some(&identity)
                        && proof.opt("request_sha256").as_str() == Some(&request_sha)
                        && proof.opt("process_not_running") == &Value::Bool(true)
                        && proof.opt("observed_at").as_str().is_some_and(|v| !v.trim().is_empty())
                        && proof.opt("evidence").as_str().is_some_and(|v| !v.trim().is_empty());
                    if !ok {
                        return Err(Error::Blocked(format!("interruption recovery requires confirmed process-loss evidence: {identity}")));
                    }
                    recoveries[3].1.clone()
                } else if s.retry_unknown.contains(&identity) {
                    let lower = error.to_lowercase();
                    if !(lower.contains("timed out") || lower.contains("timeout")) {
                        return Err(Error::Blocked(format!("explicit recovery requires a recorded timeout: {identity}")));
                    }
                    recoveries[0].1.clone()
                } else if s.retry_rejected.contains(&identity) {
                    if !credit_balance_rejection(&error) {
                        return Err(Error::Blocked(format!("quota recovery requires a recorded credit-balance rejection: {identity}")));
                    }
                    recoveries[1].1.clone()
                } else {
                    if !transient_failure(&error) {
                        return Err(Error::Blocked(format!("transient recovery requires a recorded structured HTTP 503 or connection error: {identity}")));
                    }
                    let original = if old.join("request.json").is_file() { read_json(&old.join("request.json"))? } else { obj! {} };
                    if original.opt("request_id").as_str() != Some(&identity)
                        || original.opt("request_fingerprint").as_str() != Some(&identity)
                        || !original.opt("retry_of").is_null()
                        || original.opt("endpoint").as_str() != Some(endpoint)
                        || original.opt("kind").as_str() != Some(kind.name())
                    {
                        return Err(Error::Blocked(format!("transient recovery requires the original request provenance: {identity}")));
                    }
                    recoveries[2].1.clone()
                };
                retry_of = Some(identity.clone());
                identity = recovery;
            }
            if let Some(e) = self.limit_reached(s) {
                return Err(e);
            }
            out = self.root.join(&identity);
            std::fs::create_dir_all(&out)?;
            if out.join("response.json").exists() {
                return Err(Error::Blocked("untracked existing response".into()));
            }
            if !out.join("request.json").exists() {
                save(&out.join("request.json"), &obj! {"endpoint" => endpoint, "kind" => kind.name(), "request_id" => identity.as_str(),
                    "request_fingerprint" => original_identity.as_str(), "retry_of" => retry_of.clone(), "body_without_image_bytes" => sanitized(body)?})?;
            }
            let model = body.opt("model").as_str().unwrap_or("");
            let (res, inp, out_rate) = match kind {
                Kind::Native => (1_000_000, Value::Float(0.1), Value::Float(0.5)),
                Kind::Detector => {
                    let limit = body.get("max_output_tokens").cloned().unwrap_or(Value::Int(8192));
                    let limit = match limit.as_int() {
                        Some(l) if (1..=16384).contains(&l) => l,
                        _ => return Err(Error::Blocked("unsupported detector output allowance".into())),
                    };
                    let (base, inp, o) = contract::prices(model).ok_or_else(|| format!("'{model}'"))?;
                    let est = (20000.0 * inp.as_f64().unwrap() + limit as f64 * o.as_f64().unwrap()).ceil() as i64;
                    (base.max(est), inp, o)
                }
                Kind::Verifier => {
                    let limit = body.get("max_output_tokens").cloned().unwrap_or(Value::Int(8192));
                    let limit = match limit.as_int() {
                        Some(l) if (1..=32768).contains(&l) => l,
                        _ => return Err(Error::Blocked("unsupported verifier output allowance".into())),
                    };
                    let (_, inp, o) = contract::prices(model).ok_or_else(|| format!("'{model}'"))?;
                    ((60000.0 * inp.as_f64().unwrap() + limit as f64 * o.as_f64().unwrap()).ceil() as i64, inp, o)
                }
            };
            reserve = res;
            if kind != Kind::Native {
                let count = self.http_call("responses/input_tokens", &body.pick(&["model", "input", "text", "reasoning"])?)?;
                let limit = if kind == Kind::Detector { 20000 } else { 60000 };
                if !matches!(count.opt("input_tokens").as_int(), Some(n) if 0 < n && n <= limit) {
                    return Err(Error::Blocked("input exceeds reservation".into()));
                }
            }
            if s.budget.offline {
                return Err(Error::Blocked("CACHE_ONLY_MISS: reservations disabled".into()));
            }
            s.budget.reserve(&identity, &util::path_str(&util::resolve(&out)), reserve, inp, out_rate).map_err(Error::Blocked)?;
            s.new_calls += 1;
        }
        let started = Instant::now();
        if kind != Kind::Native {
            println!("  {} {} started; recovery={}; request={}", kind.name(), body.opt("model").as_str().unwrap_or(""), if retry_of.is_some() { "True" } else { "False" }, &identity[..12]);
        }
        let mut settled = false;
        let result: R<Value> = (|| {
            let raw = self.http_call(endpoint, body)?;
            save(&out.join("response.json"), &raw)?;
            let mut s = self.state.lock().unwrap();
            if kind == Kind::Native {
                let cost = contract::decision_cost(raw.opt("usage"))?;
                let cost = match cost {
                    Some(c) if c <= reserve => c,
                    _ => return Err(Error::Blocked("native usage missing/excessive".into())),
                };
                s.budget.append(&obj! {"kind" => "settle", "id" => identity.as_str(), "cost" => cost, "usage" => raw.opt("usage").clone(), "endpoint" => "decisions"})?;
                s.budget.entries.get_mut(&identity).unwrap().set("cost", cost);
            } else {
                s.budget.settle(&identity, &contract::response_usage(&raw))?;
            }
            let cost = s.budget.entries[&identity].opt("cost").as_int().unwrap_or(0);
            s.page_spent += cost;
            settled = true;
            drop(s);
            save(&out.join("timing.json"), &obj! {"seconds" => started.elapsed().as_secs_f64()})?;
            if kind != Kind::Native {
                println!("  {} completed in {:.1}s", kind.name(), started.elapsed().as_secs_f64());
            }
            Ok(raw)
        })();
        match result {
            Ok(raw) => {
                let meta = obj! {"request_id" => identity.as_str(), "retry_of" => retry_of.clone(), "path" => util::path_str(&out), "cached" => false};
                Ok((raw, meta))
            }
            Err(e) => {
                if !settled {
                    self.state.lock().unwrap().page_spent += reserve;
                }
                let mut message = e.message().to_string();
                if let Some(k) = &self.key {
                    message = message.replace(k.as_str(), "[REDACTED]");
                }
                if !out.join("error.json").exists() {
                    let _ = save(&out.join("error.json"), &obj! {"error" => message.as_str()});
                }
                if self.auto_transient && retry_of.is_none() && transient_failure(&message) {
                    return self.request(endpoint, body, kind);
                }
                Err(Error::Blocked(format!("request failed; durable reservation retained when unsettled: {message}")))
            }
        }
    }
}

/// Render a transport failure the way CPython's urllib reports it, because
/// recovery eligibility is decided from these recorded strings.
fn transport_message(e: &reqwest::Error) -> String {
    if e.is_timeout() {
        return "timed out".into();
    }
    let mut source: Option<&dyn std::error::Error> = Some(e);
    while let Some(err) = source {
        if let Some(io) = err.downcast_ref::<std::io::Error>() {
            use std::io::ErrorKind::*;
            return match io.kind() {
                ConnectionRefused => "<urlopen error [Errno 111] Connection refused>".into(),
                NetworkUnreachable => "<urlopen error [Errno 101] Network is unreachable>".into(),
                HostUnreachable => "<urlopen error [Errno 113] No route to host>".into(),
                NetworkDown => "<urlopen error [Errno 100] Network is down>".into(),
                UnexpectedEof | ConnectionReset | ConnectionAborted => "Remote end closed connection without response".into(),
                TimedOut => "timed out".into(),
                _ => format!("<urlopen error {io}>"),
            };
        }
        source = err.source();
    }
    if e.is_connect() {
        return format!("<urlopen error {e}>");
    }
    e.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn transient_classification() {
        assert!(transient_failure("Remote end closed connection without response"));
        assert!(transient_failure("<urlopen error [Errno 111] Connection refused>"));
        assert!(transient_failure(r#"HTTP 503: {"error": {"message": "busy", "type": "server_error", "param": null, "code": null}}"#));
        assert!(transient_failure("HTTP 502: <html><title>502 Bad Gateway</title></html>"));
        assert!(!transient_failure("HTTP 500: {\"error\": {}}"));
        assert!(!transient_failure("timed out"));
        assert!(credit_balance_rejection(r#"HTTP 429: {"error": {"code": "credit_balance_exhausted"}}"#));
    }
}
