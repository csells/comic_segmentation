//! `comic-panel`: convert a comic (PDF, CBZ/ZIP, CBR/RAR or image folder)
//! into a CBZ whose ACBF metadata guides a reader panel by panel.

use clap::Parser;
use comic_panel::acceptance::{self, POLICY};
use comic_panel::budget::Budget;
use comic_panel::client::{Client, Recoveries};
use comic_panel::completeness::{self, Completeness};
use comic_panel::contract;
use comic_panel::converter::Converter;
use comic_panel::error::{Error, R};
use comic_panel::escalation;
use comic_panel::geometry;
use comic_panel::input;
use comic_panel::json::{self, Value};
use comic_panel::obj;
use comic_panel::prompts;
use comic_panel::publish;
use comic_panel::util::{self, read_json, save, sha256_hex, sha_file};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::time::Instant;

const TRANSPORT_POLICY: &str = "explicit-connection-recovery-v6";

#[derive(Parser)]
#[command(name = "comic-panel", version, about = "Automatic comic panel segmentation into a panel-guided CBZ.\n\nThe OpenAI API key is read from the first line of stdin (not needed with --offline).")]
struct Args {
    /// Comic PDF, CBZ/ZIP, CBR/RAR or folder of page images.
    source: PathBuf,
    /// Run directory (resumable; created if missing).
    output: PathBuf,
    /// Durable spending ledger shared by every run.
    #[arg(long)]
    ledger: PathBuf,
    /// Spending cap recorded in the ledger, in USD; must equal its effective cap.
    #[arg(long, default_value_t = 100.0)]
    budget_cap_usd: f64,
    /// Existing rendered-PDF cache (render.json beside a pages/ directory).
    #[arg(long)]
    render_cache: Option<PathBuf>,
    /// Bounded source page numbers (comma separated); original order is preserved.
    #[arg(long)]
    pages: Option<String>,
    /// Checkpoint after this many new pages; resume with the same output directory.
    #[arg(long)]
    max_new_pages: Option<usize>,
    /// One automatic recovery of a recorded transient transport or gateway failure.
    #[arg(long)]
    auto_transient_recovery: bool,
    /// Per-page spend limit in USD; a page reaching it falls back to a whole-page view.
    #[arg(long)]
    page_cap_usd: Option<f64>,
    /// Explicit request fingerprint: one recovery of a recorded timeout.
    #[arg(long = "retry-unknown")]
    retry_unknown: Vec<String>,
    /// Explicit request fingerprint after funding: one recovery of a credit-balance rejection.
    #[arg(long = "retry-rejected")]
    retry_rejected: Vec<String>,
    /// Explicit fingerprint after confirmed process loss (requires interruption evidence).
    #[arg(long = "retry-interrupted")]
    retry_interrupted: Vec<String>,
    /// Explicit original fingerprint: final recovery after a failed transient recovery.
    #[arg(long = "retry-second-transient")]
    retry_second_transient: Vec<String>,
    /// Explicit request fingerprint: one recovery of a recorded HTTP 503 or connection error.
    #[arg(long = "retry-transient")]
    retry_transient: Vec<String>,
    #[arg(long, default_value = "Automatic panel edition")]
    title: String,
    /// Required for live operation (paid API calls).
    #[arg(long)]
    execute_approved: bool,
    /// Cache-only replay: deny every reservation and network call.
    #[arg(long)]
    offline: bool,
    #[arg(long, default_value = "auto", value_parser = ["auto", "ltr", "rtl"])]
    reading_direction: String,
}

fn fail(msg: &str) -> ! {
    eprintln!("comic-panel: error: {msg}");
    std::process::exit(2);
}

fn is_sha(v: &str) -> bool {
    v.len() == 64 && v.bytes().all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
}

fn utc_date() -> String {
    let days = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs() / 86400) as i64;
    let z = days + 719468;
    let era = z.div_euclid(146097);
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    format!("{:04}-{:02}-{:02}", yoe + era * 400 + if m <= 2 { 1 } else { 0 }, m, d)
}

fn main() {
    let a = Args::parse();
    match run(a) {
        Ok(code) => std::process::exit(code),
        Err(e) => {
            eprintln!("comic-panel: {e}");
            std::process::exit(1);
        }
    }
}

fn run(a: Args) -> R<i32> {
    if a.max_new_pages == Some(0) {
        fail("--max-new-pages must be positive");
    }
    if let Some(c) = a.page_cap_usd {
        if !(c > 0.0 && c <= 100.0) {
            fail("--page-cap-usd must be in (0,100]");
        }
    }
    let page_cap = a.page_cap_usd.map(|c| comic_panel::cv::py_round(c * 1e6));
    let all_retries = [&a.retry_unknown, &a.retry_rejected, &a.retry_transient, &a.retry_interrupted, &a.retry_second_transient];
    if all_retries.iter().flat_map(|v| v.iter()).any(|v| !is_sha(v)) {
        fail("retry fingerprint must be SHA256");
    }
    if !a.execute_approved && !a.offline {
        fail("live operation requires --execute-approved (or use --offline for cache-only replay)");
    }
    if utc_date().as_str() > "2026-12-31" {
        fail("refresh pricing policy");
    }
    let key = if a.offline {
        None
    } else {
        let mut line = String::new();
        std::io::stdin().read_line(&mut line)?;
        let key = line.trim().to_string();
        let valid = key.starts_with("sk-") && key.len() >= 33 && key[3..].bytes().all(|c| c.is_ascii_alphanumeric() || c == b'_' || c == b'-');
        if !valid {
            fail("valid stdin credential required");
        }
        Some(key)
    };
    std::fs::create_dir_all(&a.output)?;
    let output = util::resolve(&a.output);
    let mut input = input::prepare_input(&a.source, &output.join("input"), a.render_cache.as_deref())?;
    let mut analysis_paths: HashMap<i64, PathBuf> = HashMap::new();
    let mut ordered_analysis = Vec::new();
    let pages_dir = output.join("input/pages");
    for (i, record) in input.get_mut("pages").unwrap().as_array_mut().unwrap().iter_mut().enumerate() {
        let number = i as i64 + 1;
        record.set("source_page", number);
        let path = input::prepare_analysis_image(&pages_dir.join(record.opt("image").as_str().unwrap()), &output, number as usize)?;
        ordered_analysis.push(path.clone());
        analysis_paths.insert(number, path);
    }
    let context = input::source_page_context(&ordered_analysis);
    if let Some(sel) = &a.pages {
        let selected: Vec<i64> = sel.split(',').map(|v| v.trim().parse().unwrap_or(0)).collect();
        let count = input.opt("pages").as_array().unwrap().len() as i64;
        let mut unique = selected.clone();
        unique.sort();
        unique.dedup();
        if selected.is_empty() || unique.len() != selected.len() || selected.iter().any(|v| *v < 1 || *v > count) {
            fail("invalid selected source pages");
        }
        let kept: Vec<Value> = input.opt("pages").as_array().unwrap().iter().filter(|r| selected.contains(&r.opt("source_page").as_int().unwrap())).cloned().collect();
        input.set("pages", Value::Array(kept));
    }
    let records: Vec<Value> = input.opt("pages").as_array().unwrap().clone();
    let prompt_hashes: Vec<(String, Value)> = prompts::FILES.iter().map(|(n, t)| (n.to_string(), Value::from(sha256_hex(t.as_bytes())))).collect();
    let mut implementation = obj! {"name" => "comic-panel", "version" => env!("CARGO_PKG_VERSION")};
    let mut ph = obj! {};
    for (n, h) in prompt_hashes {
        ph.set(&n, h);
    }
    implementation.set("prompt_sha256s", ph);
    let config = obj! {"policy" => POLICY, "transport_policy" => TRANSPORT_POLICY, "source_sha256" => input.opt("source_sha256").clone(),
        "title" => a.title.as_str(), "reading_direction" => a.reading_direction.as_str(), "page_cap_micro_usd" => page_cap,
        "completeness_configuration_sha256s" => completeness::configuration_hashes(),
        "source_pages" => Value::Array(records.iter().map(|r| r.opt("source_page").clone()).collect()),
        "implementation" => implementation};
    let run_json = output.join("run.json");
    if run_json.exists() {
        if read_json(&run_json)? != config {
            return Err("run identity changed; use a new output directory".into());
        }
    } else {
        save(&run_json, &config)?;
    }
    let count = records.len();
    let started = Instant::now();
    let mut outcomes: Vec<Value> = Vec::new();
    let mut new_pages = 0usize;
    let budget = Budget::open(&a.ledger, comic_panel::cv::py_round(a.budget_cap_usd * 1e6), a.offline).map_err(Error::Value)?;
    let retries = Recoveries {
        unknown: a.retry_unknown.clone(),
        rejected: a.retry_rejected.clone(),
        transient: a.retry_transient.clone(),
        interrupted: a.retry_interrupted.clone(),
        second: a.retry_second_transient.clone(),
    };
    let client = Client::new(key, budget, &output.join("calls"), retries, page_cap, a.auto_transient_recovery)?;
    let mut converter = Converter::new(&client, &output, context, &a.reading_direction, true)?;
    let guard = Completeness::new(&client, &output.join("completeness"), "normal")?;
    for (i, record) in records.iter().enumerate() {
        let ordinal = i as i64 + 1;
        let source_page = record.opt("source_page").as_int().unwrap();
        let analysis = analysis_paths[&source_page].clone();
        let publication_source = pages_dir.join(record.opt("image").as_str().unwrap());
        let final_path = output.join(format!("page-{ordinal:04}.json"));
        if final_path.exists() {
            let previous = read_json(&final_path)?;
            acceptance::validate_page_record(&publication_source, &analysis, record, &previous, ordinal)?;
            outcomes.push(previous);
            continue;
        }
        if a.max_new_pages.is_some_and(|m| new_pages >= m) {
            let (calls, hits) = client.counters();
            println!("{}", json::dumps(&obj! {"status" => "checkpoint", "completed_pages" => outcomes.len(), "total_pages" => count,
                "new_calls" => calls as i64, "cache_hits" => hits as i64, "used_held_micro_usd" => client.budget_used()}));
            return Ok(0);
        }
        println!("[{ordinal}/{count}] automatic analysis; used/held ${:.6}", client.budget_used() as f64 / 1e6);
        client.start_page();
        let result = escalation::run_page(&mut converter, &analysis, &guard)?;
        let mut result = result;
        result.set("policy", POLICY);
        result.set("page", ordinal);
        result.set("source_page", source_page);
        result.set("source_sha256", record.opt("sha256").clone());
        result.set("analysis_source_sha256", sha_file(&analysis)?);
        if result.opt("status").as_str() == Some("blocked") {
            let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
            save(&output.join(format!("blocked-{nanos}.json")), &result)?;
            println!("[{ordinal}/{count}] BLOCKED: {}", result.opt("reason").as_str().unwrap_or(""));
            return Ok(2);
        }
        acceptance::validate_page_record(&publication_source, &analysis, record, &result, ordinal)?;
        save(&final_path, &result)?;
        let tiers = result.opt("attempts").as_array().map(Vec::len).unwrap_or(0);
        let status = result.opt("status").as_str().unwrap_or("").to_string();
        outcomes.push(result);
        new_pages += 1;
        let (calls, hits) = client.counters();
        let first_pass = if client.page_cap().is_some() { format!("; first-pass page cost ${:.4}", client.page_spent() as f64 / 1e6) } else { String::new() };
        println!("[{ordinal}/{count}] {status}; tiers={tiers}; new calls={calls}; cache hits={hits}{first_pass}; used/held ${:.6}", client.budget_used() as f64 / 1e6);
    }
    let (new_calls, cache_hits) = client.counters();
    let stats = obj! {"new_calls" => new_calls as i64, "cache_hits" => cache_hits as i64, "used_held_micro_usd" => client.budget_used(), "elapsed_seconds" => started.elapsed().as_secs_f64()};
    publish_book(&a, &output, &input, &records, &analysis_paths, &outcomes, stats)
}

fn publish_book(a: &Args, output: &Path, input: &Value, records: &[Value], analysis: &HashMap<i64, PathBuf>, outcomes: &[Value], stats: Value) -> R<i32> {
    let mut directions: Vec<String> = outcomes.iter().filter(|r| r.opt("status").as_str() == Some("accepted")).map(|r| r.opt("selected").opt("panels").opt("reading_direction").as_str().unwrap_or("").to_string()).collect();
    directions.sort();
    directions.dedup();
    if directions.len() > 1 {
        return Err("Conflicting page reading directions; provide explicit book direction before publication".into());
    }
    let direction = if a.reading_direction != "auto" { a.reading_direction.clone() } else { directions.first().cloned().unwrap_or_else(|| "ltr".into()) };
    let count = records.len();
    if count != outcomes.len() {
        return Err("Incomplete publication outcomes".into());
    }
    let pages_dir = output.join("input/pages");
    let publication = output.join("publication-pages");
    std::fs::create_dir_all(&publication)?;
    let (mut entries, mut bindings, mut expected_frames, mut counts) = (vec![], vec![], vec![], vec![]);
    let mut fallbacks: HashMap<i64, String> = HashMap::new();
    for (i, (record, result)) in records.iter().zip(outcomes).enumerate() {
        let ordinal = i as i64 + 1;
        let image = record.opt("image").as_str().unwrap();
        let source_page = record.opt("source_page").as_int().unwrap();
        bindings.push(acceptance::validate_page_record(&pages_dir.join(image), &analysis[&source_page], record, result, ordinal)?);
        let (panels, classification) = if result.opt("status").as_str() == Some("accepted") {
            let selected = result.opt("selected").opt("panels");
            contract::validate_page(selected, &direction).map_err(Error::Value)?;
            (selected.opt("panels").as_array().cloned().unwrap(), selected.opt("classification").as_str().unwrap_or("").to_string())
        } else {
            fallbacks.insert(ordinal, result.opt("reason").as_str().unwrap_or("").to_string());
            (vec![obj! {"box" => vec![0, 0, 1000, 1000]}], "whole_page".to_string())
        };
        let mut boxes = Vec::new();
        for p in &panels {
            let [y, x, b, r] = geometry::box4(p.opt("box")).ok_or("invalid box")?;
            boxes.push(obj! {"x" => x as f64 / 1000.0, "y" => y as f64 / 1000.0, "w" => (r - x) as f64 / 1000.0, "h" => (b - y) as f64 / 1000.0});
        }
        let target = publication.join(image);
        if !target.exists() {
            std::fs::hard_link(pages_dir.join(image), &target)?;
        }
        if Some(sha_file(&target)?.as_str()) != record.opt("sha256").as_str() {
            return Err("publication page changed".into());
        }
        let (width, height) = comic_panel::image::image_size(&target)?;
        let frames: Vec<String> = boxes
            .iter()
            .map(|b| geometry::rectangle(b.opt("x").as_f64().unwrap(), b.opt("y").as_f64().unwrap(), b.opt("w").as_f64().unwrap(), b.opt("h").as_f64().unwrap(), width as i64, height as i64))
            .collect::<Result<_, _>>()?;
        expected_frames.push(frames);
        counts.push(if classification == "panels" { panels.len() as i64 } else { 0 });
        entries.push(obj! {"page" => ordinal, "image" => image, "panels" => Value::Array(boxes)});
    }
    let auxiliary = pages_dir.join("source-auxiliary");
    if auxiliary.exists() && !publication.join("source-auxiliary").exists() {
        copy_tree(&auxiliary, &publication.join("source-auxiliary"))?;
    }
    let mut aux_hashes = Vec::new();
    if publication.join("source-auxiliary").exists() {
        let mut files = Vec::new();
        collect(&publication.join("source-auxiliary"), &mut files)?;
        files.sort();
        for f in files {
            aux_hashes.push(obj! {"source" => f.strip_prefix(&publication).unwrap().to_string_lossy().replace('\\', "/"), "sha256" => sha_file(&f)?});
        }
    }
    let inputs = acceptance::publication_inputs(&entries, &bindings, &expected_frames, &a.title, &direction, &Value::Array(aux_hashes))?;
    let cbz = output.join("automatic-panels.cbz");
    let manifest_path = output.join("book.manifest.json");
    if cbz.exists() != manifest_path.exists() {
        return Err("unpaired archive/manifest; inspect before resuming".into());
    }
    let manifest = if !cbz.exists() {
        let source_map: Vec<i64> = records.iter().map(|r| r.opt("source_page").as_int().unwrap()).collect();
        let data = obj! {"pages" => Value::Array(entries), "total_pages" => count, "reading_direction" => direction.as_str()};
        let manifest = publish::build_cbz(&publication, &data, &cbz, &a.title, &source_map, &fallbacks)?;
        let manifest = acceptance::bind_manifest(&manifest, &inputs)?;
        save(&manifest_path, &manifest)?;
        manifest
    } else {
        let manifest = read_json(&manifest_path)?;
        acceptance::validate_archive_reuse(&cbz, &manifest, &inputs)?;
        manifest
    };
    if !output.join("counts.json").exists() {
        save(&output.join("counts.json"), &Value::from(counts[1..].to_vec()))?;
    }
    if !output.join("all-page-counts.json").exists() {
        save(&output.join("all-page-counts.json"), &Value::from(counts.clone()))?;
    }
    let mut fallback_pages: Vec<i64> = fallbacks.keys().copied().collect();
    fallback_pages.sort();
    let summary = stats
        .with("source_sha256", input.opt("source_sha256").clone())
        .with("output_sha256", manifest.opt("output_sha256").clone())
        .with("pages", count)
        .with("source_pages", Value::Array(records.iter().map(|r| r.opt("source_page").clone()).collect()))
        .with("accepted_pages", outcomes.iter().filter(|r| r.opt("status").as_str() == Some("accepted")).count())
        .with("fallback_pages", fallback_pages)
        .with("escalated_pages", Value::Array(outcomes.iter().filter(|r| r.opt("attempts").as_array().map(Vec::len).unwrap_or(0) > 1).map(|r| r.opt("page").clone()).collect()))
        .with("refined_pages", Value::Array(outcomes.iter().filter(|r| r.opt("selected").opt("refinement_changes").truthy()).map(|r| r.opt("page").clone()).collect()))
        .with("panel_steps", counts.iter().sum::<i64>())
        .with("panel_counts", counts.clone())
        .with("body_panel_steps", counts[1..].iter().sum::<i64>())
        .with("human_routing_decisions", 0)
        .with("evaluation_labels_read", false);
    let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
    save(&output.join(format!("completed-{nanos}.json")), &summary)?;
    println!("{}", json::dumps(&summary));
    Ok(0)
}

fn collect(dir: &Path, out: &mut Vec<PathBuf>) -> R<()> {
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        if entry.file_type()?.is_dir() {
            collect(&entry.path(), out)?;
        } else {
            out.push(entry.path());
        }
    }
    Ok(())
}

fn copy_tree(from: &Path, to: &Path) -> R<()> {
    std::fs::create_dir_all(to)?;
    for entry in std::fs::read_dir(from)? {
        let entry = entry?;
        let target = to.join(entry.file_name());
        if entry.file_type()?.is_dir() {
            copy_tree(&entry.path(), &target)?;
        } else {
            std::fs::copy(entry.path(), &target)?;
        }
    }
    Ok(())
}
