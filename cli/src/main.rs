//! `comic-panel`: convert a comic (PDF, CBZ/ZIP, CBR/RAR or image folder)
//! into a CBZ whose ACBF metadata guides a reader panel by panel.

use clap::Parser;
use comic_panel::acceptance::{self, POLICY};
use comic_panel::budget::{self, Budget};
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
use comic_panel::util::{self, read_json, save, sha_file, sha256_hex};
use std::collections::HashMap;
use std::io::IsTerminal;
use std::path::{Path, PathBuf};
use std::time::Instant;

const TRANSPORT_POLICY: &str = "explicit-connection-recovery-v6";
/// Model prices were verified on this date; reservations use them as holds.
const PRICES_VERIFIED_THROUGH: &str = "2026-12-31";

/// Exit status when the book was published and every page has panel guidance
/// or a legitimate whole-page classification.
const EXIT_PUBLISHED: i32 = 0;
/// Exit status when the run stopped without publishing (resumable).
const EXIT_STOPPED: i32 = 1;
/// Exit status when the book was published with reported whole-page fallbacks.
const EXIT_FALLBACKS: i32 = 2;

#[derive(Parser)]
#[command(
    name = "comic-panel",
    version,
    about = "Convert a comic into a CBZ that readers can navigate panel by panel.",
    long_about = "Convert a comic (PDF, CBZ/ZIP, CBR/RAR or a folder of page images) into a new CBZ \
containing every original page plus ACBF 1.1 panel frames in reading order.\n\n\
The OpenAI API key is read from OPENAI_API_KEY (or the first line of piped stdin). \
Runs are resumable: rerun the same command to continue. Paid answers are cached in a \
shared ledger and reused by later runs.\n\n\
Exit status: 0 published; 2 published with whole-page fallbacks (listed); 1 stopped without \
publishing (resume by rerunning)."
)]
struct Args {
    /// Comic PDF, CBZ/ZIP, CBR/RAR or folder of page images.
    source: PathBuf,
    /// CBZ to create [default: <source name>.panels.cbz beside the source]. Never overwritten.
    output: Option<PathBuf>,
    /// Resumable run state [default: <output>.work beside the output].
    #[arg(long)]
    work_dir: Option<PathBuf>,
    /// New API spending allowed for this run, in USD.
    #[arg(long, default_value_t = 20.0)]
    max_spend_usd: f64,
    /// First-pass spending limit per page, in USD; a page reaching it is published whole.
    #[arg(long, default_value_t = 0.50)]
    page_cap_usd: f64,
    /// Disable the per-page spending limit.
    #[arg(long)]
    no_page_cap: bool,
    /// Reading direction; `auto` infers it from the pages.
    #[arg(long, default_value = "auto", value_parser = ["auto", "ltr", "rtl"])]
    reading_direction: String,
    /// Book title [default: source file name].
    #[arg(long)]
    title: Option<String>,
    /// Convert only these source pages (comma separated), keeping their order.
    #[arg(long)]
    pages: Option<String>,
    /// Stop after this many newly analysed pages; rerun to continue.
    #[arg(long)]
    max_new_pages: Option<usize>,
    /// Shared spending ledger and answer cache [default: platform data directory].
    #[arg(long)]
    ledger: Option<PathBuf>,
    /// Lifetime ledger cap in USD: asserted for an existing ledger, recorded for a new one [new default: 100].
    #[arg(long)]
    ledger_cap_usd: Option<f64>,
    /// Cache-only replay: no API key, no network, no spending.
    #[arg(long)]
    offline: bool,
    /// Print the machine-readable summary JSON.
    #[arg(long)]
    json: bool,
    /// Do not automatically recover a recorded transient transport or gateway failure.
    #[arg(long)]
    no_auto_transient_recovery: bool,
    /// Pre-rendered PDF page cache (render.json beside a pages/ directory).
    #[arg(long, hide = true)]
    render_cache: Option<PathBuf>,
    /// Explicit request fingerprint: one recovery of a recorded timeout.
    #[arg(long = "retry-unknown", hide = true)]
    retry_unknown: Vec<String>,
    /// Explicit request fingerprint after funding: one recovery of a credit-balance rejection.
    #[arg(long = "retry-rejected", hide = true)]
    retry_rejected: Vec<String>,
    /// Explicit fingerprint after confirmed process loss (requires interruption evidence).
    #[arg(long = "retry-interrupted", hide = true)]
    retry_interrupted: Vec<String>,
    /// Explicit original fingerprint: final recovery after a failed transient recovery.
    #[arg(long = "retry-second-transient", hide = true)]
    retry_second_transient: Vec<String>,
    /// Explicit request fingerprint: one recovery of a recorded HTTP 503 or connection error.
    #[arg(long = "retry-transient", hide = true)]
    retry_transient: Vec<String>,
    /// Accepted for compatibility with earlier scripts; has no effect.
    #[arg(long, hide = true)]
    execute_approved: bool,
    /// Compatibility alias for --ledger-cap-usd.
    #[arg(long, hide = true)]
    budget_cap_usd: Option<f64>,
    /// Compatibility: disable automatic transient recovery unless given (defaults on).
    #[arg(long, hide = true)]
    auto_transient_recovery: bool,
}

fn usage_error(msg: &str) -> Error {
    Error::Value(format!("usage: {msg}"))
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

fn micro(usd: f64) -> i64 {
    comic_panel::cv::py_round(usd * 1e6)
}

fn read_key() -> R<String> {
    let key = match std::env::var("OPENAI_API_KEY") {
        Ok(k) if !k.trim().is_empty() => k.trim().to_string(),
        _ => {
            if std::io::stdin().is_terminal() {
                return Err(usage_error("set OPENAI_API_KEY (or pipe the key on stdin), or use --offline"));
            }
            let mut line = String::new();
            std::io::stdin().read_line(&mut line)?;
            line.trim().to_string()
        }
    };
    let valid = key.starts_with("sk-") && key.len() >= 33 && key[3..].bytes().all(|c| c.is_ascii_alphanumeric() || c == b'_' || c == b'-');
    if !valid {
        return Err(usage_error("the OpenAI API key is not in the expected sk-... form"));
    }
    Ok(key)
}

fn main() {
    let a = Args::parse();
    let code = match run(a) {
        Ok(code) => code,
        Err(e) => {
            eprintln!("comic-panel: {e}");
            EXIT_STOPPED
        }
    };
    std::process::exit(code);
}

struct Paths {
    output: PathBuf,
    work: PathBuf,
}

fn resolve_paths(a: &Args) -> Paths {
    let source = util::resolve(&a.source);
    let output = match &a.output {
        Some(o) => util::resolve(o),
        None => {
            let stem = source.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_else(|| "comic".into());
            source.parent().unwrap_or(Path::new(".")).join(format!("{stem}.panels.cbz"))
        }
    };
    let work = match &a.work_dir {
        Some(w) => util::resolve(w),
        None => output.with_file_name(format!("{}.work", output.file_name().unwrap().to_string_lossy())),
    };
    Paths { output, work }
}

fn run(a: Args) -> R<i32> {
    if a.max_new_pages == Some(0) {
        return Err(usage_error("--max-new-pages must be positive"));
    }
    if a.page_cap_usd.is_nan() || a.page_cap_usd <= 0.0 || a.page_cap_usd > 100.0 {
        return Err(usage_error("--page-cap-usd must be in (0, 100]"));
    }
    if a.max_spend_usd.is_nan() || a.max_spend_usd <= 0.0 {
        return Err(usage_error("--max-spend-usd must be positive"));
    }
    let page_cap = if a.no_page_cap { None } else { Some(micro(a.page_cap_usd)) };
    let all_retries = [&a.retry_unknown, &a.retry_rejected, &a.retry_transient, &a.retry_interrupted, &a.retry_second_transient];
    if all_retries.iter().flat_map(|v| v.iter()).any(|v| !is_sha(v)) {
        return Err(usage_error("retry fingerprints must be SHA-256 hex"));
    }
    if utc_date().as_str() > PRICES_VERIFIED_THROUGH {
        eprintln!("comic-panel: warning: model prices were last verified for {PRICES_VERIFIED_THROUGH}; ledger costs are estimates");
    }
    let source = util::resolve(&a.source);
    if !source.exists() {
        return Err(Error::Value(format!("source not found: {}", source.display())));
    }
    let paths = resolve_paths(&a);
    let key = if a.offline { None } else { Some(read_key()?) };
    let title =
        a.title.clone().unwrap_or_else(|| source.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_else(|| "Comic".into()));
    std::fs::create_dir_all(&paths.work)?;
    let output = util::resolve(&paths.work);
    if paths.output.exists() {
        let manifest = output.join("book.manifest.json");
        let finished = manifest.exists() && read_json(&manifest)?.opt("output_sha256").as_str() == Some(&sha_file(&paths.output)?);
        if !finished {
            return Err(Error::Value(format!("output already exists; choose another path: {}", paths.output.display())));
        }
    }
    let mut input = input::prepare_input(&source, &output.join("input"), a.render_cache.as_deref())?;
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
            return Err(usage_error(&format!("--pages must list distinct pages between 1 and {count}")));
        }
        let kept: Vec<Value> = input
            .opt("pages")
            .as_array()
            .unwrap()
            .iter()
            .filter(|r| selected.contains(&r.opt("source_page").as_int().unwrap()))
            .cloned()
            .collect();
        input.set("pages", Value::Array(kept));
    }
    let records: Vec<Value> = input.opt("pages").as_array().unwrap().clone();
    let mut prompt_hashes = obj! {};
    for (n, t) in prompts::FILES {
        prompt_hashes.set(n, sha256_hex(t.as_bytes()));
    }
    let implementation = obj! {"name" => "comic-panel", "version" => env!("CARGO_PKG_VERSION"), "prompt_sha256s" => prompt_hashes};
    let config = obj! {"policy" => POLICY, "transport_policy" => TRANSPORT_POLICY, "source_sha256" => input.opt("source_sha256").clone(),
    "title" => title.as_str(), "reading_direction" => a.reading_direction.as_str(), "page_cap_micro_usd" => page_cap,
    "completeness_configuration_sha256s" => completeness::configuration_hashes(),
    "source_pages" => Value::Array(records.iter().map(|r| r.opt("source_page").clone()).collect()),
    "implementation" => implementation};
    let run_json = output.join("run.json");
    if run_json.exists() {
        if read_json(&run_json)? != config {
            return Err(Error::Value(format!(
                "this work directory belongs to a different conversion (source, pages, title, direction or page cap changed): {}",
                output.display()
            )));
        }
    } else {
        save(&run_json, &config)?;
    }
    let count = records.len();
    let started = Instant::now();
    let mut outcomes: Vec<Value> = Vec::new();
    let mut new_pages = 0usize;
    let ledger = a.ledger.clone().unwrap_or_else(budget::default_ledger);
    let expected_cap = a.ledger_cap_usd.or(a.budget_cap_usd).map(micro);
    let mut ledger_budget = Budget::open(&ledger, expected_cap, expected_cap.unwrap_or(100_000_000), a.offline).map_err(Error::Value)?;
    ledger_budget.set_run_limit(micro(a.max_spend_usd));
    let used_at_start = ledger_budget.used();
    let retries = Recoveries {
        unknown: a.retry_unknown.clone(),
        rejected: a.retry_rejected.clone(),
        transient: a.retry_transient.clone(),
        interrupted: a.retry_interrupted.clone(),
        second: a.retry_second_transient.clone(),
    };
    let client = Client::new(key, ledger_budget, &output.join("calls"), retries, page_cap, !a.no_auto_transient_recovery)?;
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
            println!(
                "Checkpoint: {}/{count} pages done; rerun the same command to continue ({calls} new requests, {hits} reused, ${:.2} spent this run).",
                outcomes.len(),
                (client.budget_used() - used_at_start) as f64 / 1e6
            );
            return Ok(EXIT_STOPPED);
        }
        println!("[{ordinal}/{count}] page {source_page}: analysing");
        client.start_page();
        let mut result = escalation::run_page(&mut converter, &analysis, &guard)?;
        result.set("policy", POLICY);
        result.set("page", ordinal);
        result.set("source_page", source_page);
        result.set("source_sha256", record.opt("sha256").clone());
        result.set("analysis_source_sha256", sha_file(&analysis)?);
        if result.opt("status").as_str() == Some("blocked") {
            let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
            save(&output.join(format!("blocked-{nanos}.json")), &result)?;
            eprintln!("comic-panel: stopped at page {source_page}: {}", result.opt("reason").as_str().unwrap_or(""));
            eprintln!("comic-panel: completed pages are kept in {}; rerun the same command to resume.", output.display());
            return Ok(EXIT_STOPPED);
        }
        acceptance::validate_page_record(&publication_source, &analysis, record, &result, ordinal)?;
        save(&final_path, &result)?;
        let status = result.opt("status").as_str().unwrap_or("").to_string();
        let panels = result.opt("selected").opt("panels").opt("panels").as_array().map(Vec::len).unwrap_or(0);
        outcomes.push(result);
        new_pages += 1;
        let cost =
            if client.page_cap().is_some() { format!(", page cost ${:.3}", client.page_spent() as f64 / 1e6) } else { String::new() };
        let what = if status == "accepted" { format!("{panels} panel(s)") } else { "whole-page fallback".to_string() };
        println!("[{ordinal}/{count}] page {source_page}: {what}{cost}");
    }
    let (new_calls, cache_hits) = client.counters();
    let spent = client.budget_used() - used_at_start;
    let stats = obj! {"new_calls" => new_calls as i64, "cache_hits" => cache_hits as i64, "run_spend_micro_usd" => spent,
    "used_held_micro_usd" => client.budget_used(), "elapsed_seconds" => started.elapsed().as_secs_f64()};
    publish_book(&a, &title, &paths, &output, &input, &records, &analysis_paths, &outcomes, stats)
}

#[allow(clippy::too_many_arguments)]
fn publish_book(
    a: &Args,
    title: &str,
    paths: &Paths,
    output: &Path,
    input: &Value,
    records: &[Value],
    analysis: &HashMap<i64, PathBuf>,
    outcomes: &[Value],
    stats: Value,
) -> R<i32> {
    let mut directions: Vec<String> = outcomes
        .iter()
        .filter(|r| r.opt("status").as_str() == Some("accepted"))
        .map(|r| r.opt("selected").opt("panels").opt("reading_direction").as_str().unwrap_or("").to_string())
        .collect();
    directions.sort();
    directions.dedup();
    if directions.len() > 1 {
        return Err("pages disagree on reading direction; rerun with --reading-direction ltr or rtl".into());
    }
    let direction = if a.reading_direction != "auto" {
        a.reading_direction.clone()
    } else {
        directions.first().cloned().unwrap_or_else(|| "ltr".into())
    };
    let count = records.len();
    if count != outcomes.len() {
        return Err("Incomplete publication outcomes".into());
    }
    let pages_dir = output.join("input/pages");
    let publication = output.join("publication-pages");
    std::fs::create_dir_all(&publication)?;
    let (mut entries, mut bindings, mut expected_frames, mut counts) = (vec![], vec![], vec![], vec![]);
    let mut fallbacks: HashMap<i64, String> = HashMap::new();
    let mut report_pages = Vec::new();
    for (i, (record, result)) in records.iter().zip(outcomes).enumerate() {
        let ordinal = i as i64 + 1;
        let image = record.opt("image").as_str().unwrap();
        let source_page = record.opt("source_page").as_int().unwrap();
        bindings.push(acceptance::validate_page_record(&pages_dir.join(image), &analysis[&source_page], record, result, ordinal)?);
        let accepted = result.opt("status").as_str() == Some("accepted");
        let (panels, classification) = if accepted {
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
            boxes.push(
                obj! {"x" => x as f64 / 1000.0, "y" => y as f64 / 1000.0, "w" => (r - x) as f64 / 1000.0, "h" => (b - y) as f64 / 1000.0},
            );
        }
        let target = publication.join(image);
        if !target.exists() {
            std::fs::hard_link(pages_dir.join(image), &target).or_else(|_| std::fs::copy(pages_dir.join(image), &target).map(|_| ()))?;
        }
        if Some(sha_file(&target)?.as_str()) != record.opt("sha256").as_str() {
            return Err("publication page changed".into());
        }
        let (width, height) = comic_panel::image::image_size(&target)?;
        let frames: Vec<String> = boxes
            .iter()
            .map(|b| {
                geometry::rectangle(
                    b.opt("x").as_f64().unwrap(),
                    b.opt("y").as_f64().unwrap(),
                    b.opt("w").as_f64().unwrap(),
                    b.opt("h").as_f64().unwrap(),
                    width as i64,
                    height as i64,
                )
            })
            .collect::<Result<_, _>>()?;
        expected_frames.push(frames);
        counts.push(if classification == "panels" { panels.len() as i64 } else { 0 });
        let status = if !accepted {
            "whole_page_fallback"
        } else if classification == "panels" {
            "panels"
        } else {
            "whole_page"
        };
        report_pages.push(obj! {"page" => ordinal, "source_page" => source_page, "status" => status,
        "panels" => if classification == "panels" { panels.len() } else { 0 }, "fallback_reason" => fallbacks.get(&ordinal).cloned()});
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
            aux_hashes.push(
                obj! {"source" => f.strip_prefix(&publication).unwrap().to_string_lossy().replace('\\', "/"), "sha256" => sha_file(&f)?},
            );
        }
    }
    let inputs = acceptance::publication_inputs(&entries, &bindings, &expected_frames, title, &direction, &Value::Array(aux_hashes))?;
    let cbz = output.join("automatic-panels.cbz");
    let manifest_path = output.join("book.manifest.json");
    if cbz.exists() != manifest_path.exists() {
        return Err("unpaired archive/manifest; inspect before resuming".into());
    }
    let mut fallback_pages: Vec<i64> = fallbacks.keys().copied().collect();
    fallback_pages.sort();
    let report = obj! {"format" => "comic-panel-report", "version" => 1, "generator" => format!("comic-panel {}", env!("CARGO_PKG_VERSION")),
    "policy" => POLICY, "title" => title, "reading_direction" => direction.as_str(), "pages" => Value::Array(report_pages)};
    let manifest = if !cbz.exists() {
        let source_map: Vec<i64> = records.iter().map(|r| r.opt("source_page").as_int().unwrap()).collect();
        let data = obj! {"pages" => Value::Array(entries), "total_pages" => count, "reading_direction" => direction.as_str()};
        let manifest = publish::build_cbz(&publication, &data, &cbz, title, &source_map, &fallbacks, Some(&report))?;
        publish::validate_cbz(&cbz, &manifest)?;
        let manifest = acceptance::bind_manifest(&manifest, &inputs)?;
        save(&manifest_path, &manifest)?;
        manifest
    } else {
        let manifest = read_json(&manifest_path)?;
        acceptance::validate_archive_reuse(&cbz, &manifest, &inputs)?;
        manifest
    };
    if !paths.output.exists() {
        publish::validate_cbz(&cbz, &manifest)?;
        publish::publish_no_replace(&cbz, &paths.output)?;
    }
    if !output.join("counts.json").exists() {
        save(&output.join("counts.json"), &Value::from(counts[1..].to_vec()))?;
    }
    if !output.join("all-page-counts.json").exists() {
        save(&output.join("all-page-counts.json"), &Value::from(counts.clone()))?;
    }
    let accepted = outcomes.iter().filter(|r| r.opt("status").as_str() == Some("accepted")).count();
    let whole = counts.iter().zip(outcomes).filter(|(c, r)| **c == 0 && r.opt("status").as_str() == Some("accepted")).count();
    let summary = stats
        .with("output", util::path_str(&paths.output))
        .with("source_sha256", input.opt("source_sha256").clone())
        .with("output_sha256", manifest.opt("output_sha256").clone())
        .with("pages", count)
        .with("source_pages", Value::Array(records.iter().map(|r| r.opt("source_page").clone()).collect()))
        .with("accepted_pages", accepted)
        .with("fallback_pages", fallback_pages.clone())
        .with(
            "escalated_pages",
            Value::Array(
                outcomes
                    .iter()
                    .filter(|r| r.opt("attempts").as_array().map(Vec::len).unwrap_or(0) > 1)
                    .map(|r| r.opt("page").clone())
                    .collect(),
            ),
        )
        .with(
            "refined_pages",
            Value::Array(
                outcomes.iter().filter(|r| r.opt("selected").opt("refinement_changes").truthy()).map(|r| r.opt("page").clone()).collect(),
            ),
        )
        .with("panel_steps", counts.iter().sum::<i64>())
        .with("panel_counts", counts.clone())
        .with("body_panel_steps", counts[1..].iter().sum::<i64>())
        .with("human_routing_decisions", 0)
        .with("evaluation_labels_read", false);
    let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
    save(&output.join(format!("completed-{nanos}.json")), &summary)?;
    if a.json {
        println!("{}", json::dumps(&summary));
    } else {
        println!(
            "Published {}: {count} pages, {} with panel guidance ({} panels), {whole} whole-page, {} fallback.",
            paths.output.display(),
            accepted - whole,
            counts.iter().sum::<i64>(),
            fallback_pages.len()
        );
        for p in &fallback_pages {
            let source_page = records[(*p - 1) as usize].opt("source_page").as_int().unwrap_or(*p);
            println!("  page {source_page} shown whole: {}", fallbacks[p]);
        }
        let s = summary.opt("run_spend_micro_usd").as_int().unwrap_or(0);
        println!(
            "Spent ${:.2} this run ({} new requests, {} reused from the cache).",
            s as f64 / 1e6,
            summary.opt("new_calls").as_int().unwrap_or(0),
            summary.opt("cache_hits").as_int().unwrap_or(0)
        );
    }
    Ok(if fallback_pages.is_empty() { EXIT_PUBLISHED } else { EXIT_FALLBACKS })
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
