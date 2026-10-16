//! Hermetic end-to-end tests: the real binary against a fake OpenAI server.
//!
//! Synthetic pages with drawn panels go into a CBZ; the fake server answers
//! every request type the pipeline makes (detector, decisions, verifiers,
//! source evidence, completeness inventory and mapping) with consistent,
//! passing answers, so the full HTTP, ledger, quality and publish paths run.

use comic_panel::image::{self, Rgb};
use comic_panel::json::{self, Value};
use comic_panel::{arr, obj};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};

const W: usize = 800;
const H: usize = 1200;

/// Panel rectangles in pixels: (left, top, right, bottom). Empty = whole page.
fn layouts() -> Vec<Vec<(usize, usize, usize, usize)>> {
    vec![vec![], vec![(40, 40, 760, 580), (40, 620, 760, 1160)], vec![(40, 40, 380, 580), (420, 40, 760, 580), (40, 620, 760, 1160)]]
}

fn draw_page(index: usize, panels: &[(usize, usize, usize, usize)]) -> Vec<u8> {
    let mut img = Rgb::new(W, H);
    img.data.fill(255);
    let fill = |img: &mut Rgb, l: usize, t: usize, r: usize, b: usize, c: [u8; 3]| {
        for y in t..b {
            for x in l..r {
                let i = (y * W + x) * 3;
                img.data[i..i + 3].copy_from_slice(&c);
            }
        }
    };
    if panels.is_empty() {
        fill(&mut img, 100, 150, 700, 1050, [200, 60, 40]);
        fill(&mut img, 250, 400, 550, 800, [30, 30, 120]);
    }
    for (n, &(l, t, r, b)) in panels.iter().enumerate() {
        for k in 0..6 {
            image::draw_rectangle_outline(&mut img, (l + k) as i64, (t + k) as i64, (r - 1 - k) as i64, (b - 1 - k) as i64, [0, 0, 0], 1);
        }
        let shade = (60 + 50 * ((n + index) % 4)) as u8;
        fill(&mut img, l + 60, t + 60, r - 60, b - 60, [shade, 120, 255 - shade]);
    }
    image::encode_jpeg(&img, 92).unwrap()
}

struct Fixture {
    pages: Vec<Vec<u8>>,
    b64: Vec<String>,
}

fn fixture() -> Fixture {
    let pages: Vec<Vec<u8>> = layouts().iter().enumerate().map(|(i, p)| draw_page(i, p)).collect();
    let b64 = pages.iter().map(|p| comic_panel::util::b64(p)).collect();
    Fixture { pages, b64 }
}

fn norm(v: usize, size: usize) -> i64 {
    (v as f64 * 1000.0 / size as f64).round() as i64
}

#[derive(Default)]
struct Behavior {
    /// Remaining structured 503 failures to inject on generation calls.
    fail_503: AtomicUsize,
}

struct Server {
    port: u16,
    requests: Arc<Mutex<Vec<String>>>,
}

fn page_of(body: &str, fx: &Fixture) -> Option<usize> {
    fx.b64.iter().position(|b| body.contains(b.as_str()))
}

fn responses_reply(model: &str, value: &Value) -> Value {
    obj! {"id" => "resp_test", "model" => format!("{model}-2026-10-01"), "status" => "completed",
    "output" => arr![obj! {"type" => "message", "status" => "completed", "content" => arr![obj! {"type" => "output_text", "text" => json::dumps(value)}]}],
    "usage" => obj! {"input_tokens" => 1000, "output_tokens" => 200, "total_tokens" => 1200}}
}

fn answer(path: &str, body: &Value, raw: &str, fx: &Fixture, behavior: &Behavior) -> (u16, Value) {
    let layouts = layouts();
    let page = page_of(raw, fx);
    if path.ends_with("/responses/input_tokens") {
        return (200, obj! {"input_tokens" => 1500});
    }
    if path.ends_with("/decisions") {
        let answers: Vec<Value> = body
            .opt("questions")
            .as_array()
            .unwrap()
            .iter()
            .map(|q| obj! {"type" => "predicate", "name" => q.opt("name").clone(), "probability" => 0.02})
            .collect();
        return (
            200,
            obj! {"model" => "gpt-6-luna-2026-10-01", "answers" => Value::Array(answers),
            "usage" => obj! {"input_tokens" => 800, "output_tokens" => 0, "total_tokens" => 800}},
        );
    }
    if behavior.fail_503.load(Ordering::SeqCst) > 0 {
        behavior.fail_503.fetch_sub(1, Ordering::SeqCst);
        return (
            503,
            obj! {"error" => obj! {"message" => "The server is overloaded.", "type" => "server_error", "param" => Value::Null, "code" => Value::Null}},
        );
    }
    let model = body.opt("model").as_str().unwrap_or("gpt-6-sol").to_string();
    let schema = body.opt("text").opt("format").opt("name").as_str().unwrap_or("").to_string();
    let panels = page.map(|p| layouts[p].clone()).unwrap_or_default();
    let value = match schema.as_str() {
        "comic_panels" => {
            if panels.is_empty() {
                obj! {"classification" => "whole_page", "orientation" => "upright", "reading_direction" => "ltr",
                "panels" => arr![obj! {"order" => 1, "description" => "Cover artwork", "bounds" => obj! {"left" => 0, "top" => 0, "right" => 1000, "bottom" => 1000}}]}
            } else {
                let ps: Vec<Value> = panels
                    .iter()
                    .enumerate()
                    .map(|(i, &(l, t, r, b))| {
                        obj! {"order" => i + 1, "description" => format!("Scene {}", i + 1),
                        "bounds" => obj! {"left" => norm(l, W), "top" => norm(t, H), "right" => norm(r, W), "bottom" => norm(b, H)}}
                    })
                    .collect();
                obj! {"classification" => "panels", "orientation" => "upright", "reading_direction" => "ltr", "panels" => Value::Array(ps)}
            }
        }
        "panel_quality_verdict" => {
            obj! {"decision" => "accept", "scene_inventory" => "pass", "reading_order" => "pass", "crop_coverage" => "pass", "issues" => arr![]}
        }
        "source_continuity" => {
            obj! {"classification" => "continuous", "views" => arr!["one composition"], "evidence" => "Single continuous composition."}
        }
        "source_scene_evidence" => {
            let scenes: Vec<Value> = (1..=panels.len().max(1)).map(|o| obj! {"order" => o, "identity" => format!("Scene {o}"), "owned_content" => arr!["figures"],
                "ownership_cues" => arr!["inside its frame"], "distinguish_from_neighbors" => arr!["separate frame"], "uncertain" => false}).collect();
            obj! {"inventory_status" => "complete", "scenes" => Value::Array(scenes), "issues" => arr![]}
        }
        "source_view_inventory_v1" => {
            if panels.is_empty() {
                obj! {"page_kind" => "whole_page", "rationale" => "A single cover composition.", "views" => arr![]}
            } else {
                let views: Vec<Value> = panels
                    .iter()
                    .enumerate()
                    .map(|(i, &(l, t, r, b))| {
                        obj! {"id" => format!("v{}", i + 1), "visual_cue" => format!("framed scene {}", i + 1),
                        "locator_y" => norm((t + b) / 2, H), "locator_x" => norm((l + r) / 2, W), "uncertain" => false}
                    })
                    .collect();
                obj! {"page_kind" => "narrative", "rationale" => "Framed narrative panels.", "views" => Value::Array(views)}
            }
        }
        "source_view_coverage_v1" => {
            let mappings: Vec<Value> = (1..=panels.len())
                .map(|o| obj! {"source_id" => format!("v{o}"), "proposed_order" => o, "reason" => "same frame"})
                .collect();
            obj! {"disposition" => "complete", "mappings" => Value::Array(mappings), "inventory_issues" => arr![], "reason" => "Every source view maps to one step."}
        }
        other => panic!("unexpected request schema {other}"),
    };
    (200, responses_reply(&model, &value))
}

fn handle(mut stream: TcpStream, fx: Arc<Fixture>, behavior: Arc<Behavior>, log: Arc<Mutex<Vec<String>>>) {
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    loop {
        let mut line = String::new();
        if reader.read_line(&mut line).unwrap_or(0) == 0 {
            return;
        }
        let path = line.split_whitespace().nth(1).unwrap_or("").to_string();
        let mut length = 0;
        loop {
            let mut h = String::new();
            if reader.read_line(&mut h).unwrap_or(0) == 0 {
                return;
            }
            if h == "\r\n" {
                break;
            }
            if let Some(v) = h.to_ascii_lowercase().strip_prefix("content-length:") {
                length = v.trim().parse().unwrap_or(0);
            }
        }
        let mut body = vec![0; length];
        reader.read_exact(&mut body).unwrap();
        let raw = String::from_utf8(body).unwrap();
        let value = json::loads(&raw).unwrap();
        log.lock().unwrap().push(path.clone());
        let (status, reply) = answer(&path, &value, &raw, &fx, &behavior);
        let text = json::dumps(&reply);
        let reason = if status == 200 { "OK" } else { "Service Unavailable" };
        let _ =
            write!(stream, "HTTP/1.1 {status} {reason}\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n{text}", text.len());
    }
}

fn start(fx: Arc<Fixture>, behavior: Arc<Behavior>) -> Server {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let requests = Arc::new(Mutex::new(Vec::new()));
    let log = requests.clone();
    std::thread::spawn(move || {
        for stream in listener.incoming().flatten() {
            let (fx, behavior, log) = (fx.clone(), behavior.clone(), log.clone());
            std::thread::spawn(move || handle(stream, fx, behavior, log));
        }
    });
    Server { port, requests }
}

fn temp_dir(name: &str) -> PathBuf {
    let d = std::env::temp_dir().join(format!("comic-panel-e2e-{}-{name}", std::process::id()));
    let _ = std::fs::remove_dir_all(&d);
    std::fs::create_dir_all(&d).unwrap();
    d
}

fn write_cbz(path: &Path, pages: &[Vec<u8>], extra: &[(&str, &[u8])]) {
    let mut zw = zip::ZipWriter::new(std::fs::File::create(path).unwrap());
    let opts = zip::write::SimpleFileOptions::default();
    for (i, p) in pages.iter().enumerate() {
        zw.start_file(format!("pages/{:03}.jpg", i + 1), opts).unwrap();
        zw.write_all(p).unwrap();
    }
    for (name, data) in extra {
        zw.start_file(*name, opts).unwrap();
        zw.write_all(data).unwrap();
    }
    zw.finish().unwrap();
}

struct Run {
    code: i32,
    stdout: String,
    stderr: String,
}

fn run(port: u16, args: &[&str]) -> Run {
    let out = Command::new(env!("CARGO_BIN_EXE_comic-panel"))
        .args(args)
        .env("COMIC_PANEL_OPENAI_BASE", format!("http://127.0.0.1:{port}/v1/"))
        .env("OPENAI_API_KEY", "sk-test-0123456789abcdefghijklmnopqrstuv")
        .env_remove("HTTPS_PROXY")
        .env_remove("https_proxy")
        .env_remove("HTTP_PROXY")
        .env_remove("http_proxy")
        .env_remove("ALL_PROXY")
        .env_remove("all_proxy")
        .output()
        .unwrap();
    Run {
        code: out.status.code().unwrap_or(-1),
        stdout: String::from_utf8_lossy(&out.stdout).into(),
        stderr: String::from_utf8_lossy(&out.stderr).into(),
    }
}

fn acbf(cbz: &Path) -> String {
    let mut archive = zip::ZipArchive::new(std::fs::File::open(cbz).unwrap()).unwrap();
    let mut s = String::new();
    archive.by_name("metadata.acbf").unwrap().read_to_string(&mut s).unwrap();
    s
}

/// Validate published metadata against the pinned ACBF 1.1 XSD when
/// `COMIC_PANEL_ACBF_XSD` names it (see tests/fetch-acbf-xsd.sh); requires xmllint.
fn validate_schema(cbz: &Path) {
    let Ok(xsd) = std::env::var("COMIC_PANEL_ACBF_XSD") else { return };
    let path = cbz.with_extension("metadata.acbf");
    std::fs::write(&path, acbf(cbz)).unwrap();
    let out = Command::new("xmllint").args(["--noout", "--schema", &xsd]).arg(&path).output().expect("xmllint");
    assert!(out.status.success(), "ACBF schema validation failed: {}", String::from_utf8_lossy(&out.stderr));
}

fn frame_counts(xml: &str) -> Vec<usize> {
    xml.split("<image href=")
        .skip(1)
        .map(|s| s.split("</page>").next().unwrap().split("</coverpage>").next().unwrap().matches("<frame points=").count())
        .collect()
}

fn s(p: &Path) -> String {
    p.to_string_lossy().into_owned()
}

#[test]
fn converts_resumes_and_replays() {
    let fx = Arc::new(fixture());
    let server = start(fx.clone(), Arc::new(Behavior::default()));
    let dir = temp_dir("convert");
    let cbz = dir.join("book.cbz");
    write_cbz(&cbz, &fx.pages, &[("ComicInfo.xml", b"<ComicInfo/>")]);
    let out = dir.join("book.panels.cbz");
    let ledger = dir.join("ledger.jsonl");
    let args = [s(&cbz), s(&out), "--ledger".into(), s(&ledger), "--reading-direction".into(), "ltr".into()];
    let args: Vec<&str> = args.iter().map(String::as_str).collect();
    let first = run(server.port, &args);
    assert_eq!(first.code, 0, "stdout:\n{}\nstderr:\n{}", first.stdout, first.stderr);
    assert!(first.stdout.contains("3 pages, 2 with panel guidance (5 panels), 1 whole-page, 0 fallback"), "{}", first.stdout);
    let xml = acbf(&out);
    assert_eq!(frame_counts(&xml), vec![1, 2, 3]);
    validate_schema(&out);
    let mut archive = zip::ZipArchive::new(std::fs::File::open(&out).unwrap()).unwrap();
    for (i, page) in fx.pages.iter().enumerate() {
        let mut data = Vec::new();
        archive.by_name(&format!("{:04}.jpg", i + 1)).unwrap().read_to_end(&mut data).unwrap();
        assert_eq!(&data, page, "page bytes must be preserved");
    }
    // Non-page source files are preserved byte for byte under source-auxiliary/.
    let mut info = Vec::new();
    archive.by_name("source-auxiliary/ComicInfo.xml").unwrap().read_to_end(&mut info).unwrap();
    assert_eq!(info, b"<ComicInfo/>");
    assert!(archive.by_name("comic-panel-report.json").is_ok());
    let calls_first = server.requests.lock().unwrap().len();
    assert!(calls_first > 0);

    // Rerunning a finished conversion makes no requests and leaves the book alone.
    let before = std::fs::read(&out).unwrap();
    let again = run(server.port, &args);
    assert_eq!(again.code, 0, "{}", again.stderr);
    assert_eq!(server.requests.lock().unwrap().len(), calls_first);
    assert_eq!(std::fs::read(&out).unwrap(), before);

    // A fresh work directory replays every answer offline from the shared ledger.
    let replay_out = dir.join("replay.cbz");
    let replay =
        run(server.port, &[&s(&cbz), &s(&replay_out), "--ledger", &s(&ledger), "--reading-direction", "ltr", "--offline", "--json"]);
    assert_eq!(replay.code, 0, "{}\n{}", replay.stdout, replay.stderr);
    let summary = json::loads(replay.stdout.lines().last().unwrap()).unwrap();
    assert_eq!(summary.opt("new_calls"), &Value::Int(0));
    assert_eq!(summary.opt("run_spend_micro_usd"), &Value::Int(0));
    assert_eq!(frame_counts(&acbf(&replay_out)), vec![1, 2, 3]);
    assert_eq!(server.requests.lock().unwrap().len(), calls_first, "offline replay must not touch the network");
}

#[test]
fn refuses_to_overwrite_existing_output() {
    let fx = Arc::new(fixture());
    let server = start(fx.clone(), Arc::new(Behavior::default()));
    let dir = temp_dir("overwrite");
    let cbz = dir.join("book.cbz");
    write_cbz(&cbz, &fx.pages, &[]);
    let out = dir.join("existing.cbz");
    std::fs::write(&out, b"keep me").unwrap();
    let r = run(server.port, &[&s(&cbz), &s(&out), "--ledger", &s(&dir.join("ledger.jsonl"))]);
    assert_eq!(r.code, 1);
    assert!(r.stderr.contains("output already exists"), "{}", r.stderr);
    assert_eq!(std::fs::read(&out).unwrap(), b"keep me");
    assert!(server.requests.lock().unwrap().is_empty());
}

#[test]
fn run_spending_limit_stops_resumably() {
    let fx = Arc::new(fixture());
    let server = start(fx.clone(), Arc::new(Behavior::default()));
    let dir = temp_dir("limit");
    let cbz = dir.join("book.cbz");
    write_cbz(&cbz, &fx.pages, &[]);
    let out = dir.join("out.cbz");
    let ledger = dir.join("ledger.jsonl");
    let low = run(server.port, &[&s(&cbz), &s(&out), "--ledger", &s(&ledger), "--reading-direction", "ltr", "--max-spend-usd", "0.10"]);
    assert_eq!(low.code, 1, "{}", low.stdout);
    assert!(low.stderr.contains("run spending limit reached"), "{}", low.stderr);
    assert!(!out.exists());
    let resumed = run(server.port, &[&s(&cbz), &s(&out), "--ledger", &s(&ledger), "--reading-direction", "ltr", "--max-spend-usd", "20"]);
    assert_eq!(resumed.code, 0, "{}\n{}", resumed.stdout, resumed.stderr);
    assert_eq!(frame_counts(&acbf(&out)), vec![1, 2, 3]);
}

#[test]
fn recovers_one_transient_server_error() {
    let fx = Arc::new(fixture());
    let behavior = Arc::new(Behavior::default());
    behavior.fail_503.store(1, Ordering::SeqCst);
    let server = start(fx.clone(), behavior.clone());
    let dir = temp_dir("transient");
    let cbz = dir.join("book.cbz");
    write_cbz(&cbz, &fx.pages, &[]);
    let out = dir.join("out.cbz");
    let r = run(server.port, &[&s(&cbz), &s(&out), "--ledger", &s(&dir.join("ledger.jsonl")), "--reading-direction", "ltr"]);
    assert_eq!(r.code, 0, "{}\n{}", r.stdout, r.stderr);
    assert_eq!(behavior.fail_503.load(Ordering::SeqCst), 0);
    let ledger = std::fs::read_to_string(dir.join("ledger.jsonl")).unwrap();
    assert!(ledger.lines().filter(|l| l.contains("\"kind\": \"reserve\"")).count() > 1);
}

#[test]
fn rejects_corrupt_or_unsafe_input_before_any_request() {
    let fx = Arc::new(fixture());
    let server = start(fx.clone(), Arc::new(Behavior::default()));
    let dir = temp_dir("bad-input");
    // A truncated JPEG page.
    let mut pages = fx.pages.clone();
    pages[1].truncate(400);
    let bad = dir.join("bad.cbz");
    write_cbz(&bad, &pages, &[]);
    let r = run(server.port, &[&s(&bad), &s(&dir.join("bad.panels.cbz")), "--ledger", &s(&dir.join("ledger.jsonl"))]);
    assert_eq!(r.code, 1);
    assert!(r.stderr.contains("unreadable page image"), "{}", r.stderr);
    // A path-traversal member.
    let evil = dir.join("evil.cbz");
    write_cbz(&evil, &fx.pages, &[("../escape.txt", b"x")]);
    let r = run(server.port, &[&s(&evil), &s(&dir.join("evil.panels.cbz")), "--ledger", &s(&dir.join("ledger.jsonl"))]);
    assert_eq!(r.code, 1);
    assert!(r.stderr.contains("unsafe archive member"), "{}", r.stderr);
    assert!(!dir.join("escape.txt").exists());
    assert!(server.requests.lock().unwrap().is_empty(), "no request may be sent for unreadable input");
}

#[test]
fn converts_an_image_folder() {
    let fx = Arc::new(fixture());
    let server = start(fx.clone(), Arc::new(Behavior::default()));
    let dir = temp_dir("folder");
    let book = dir.join("Book Folder");
    std::fs::create_dir_all(&book).unwrap();
    // Natural order: page2 before page10.
    let names = ["page1.jpg", "page2.jpg", "page10.jpg"];
    for (name, data) in names.iter().zip(&fx.pages) {
        std::fs::write(book.join(name), data).unwrap();
    }
    std::fs::write(book.join("notes.txt"), b"auxiliary").unwrap();
    let r = run(server.port, &[&s(&book), "--ledger", &s(&dir.join("ledger.jsonl")), "--reading-direction", "ltr"]);
    assert_eq!(r.code, 0, "{}\n{}", r.stdout, r.stderr);
    let out = dir.join("Book Folder.panels.cbz");
    assert_eq!(frame_counts(&acbf(&out)), vec![1, 2, 3]);
    validate_schema(&out);
    let mut archive = zip::ZipArchive::new(std::fs::File::open(&out).unwrap()).unwrap();
    assert!(archive.by_name("source-auxiliary/notes.txt").is_ok());
}

#[test]
fn single_page_book_is_cover_only() {
    let fx = Arc::new(fixture());
    let server = start(fx.clone(), Arc::new(Behavior::default()));
    let dir = temp_dir("single");
    let cbz = dir.join("one.cbz");
    write_cbz(&cbz, &fx.pages[2..3], &[]);
    let out = dir.join("one.panels.cbz");
    let r = run(server.port, &[&s(&cbz), &s(&out), "--ledger", &s(&dir.join("ledger.jsonl")), "--reading-direction", "ltr"]);
    assert_eq!(r.code, 0, "{}\n{}", r.stdout, r.stderr);
    let xml = acbf(&out);
    assert!(!xml.contains("<body>"), "a one-page book is cover-only");
    assert_eq!(frame_counts(&xml), vec![3]);
    validate_schema(&out);
}
