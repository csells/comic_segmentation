//! CBZ + ACBF 1.1 publication (`comic_panel_e2e/adapter.build_cbz`).
//!
//! Complete pages are stored unchanged; panel frames are ACBF polygons.
//! Malformed per-page geometry becomes an explicit whole-page fallback.

use crate::error::{require, Error, R};
use crate::geometry;
use crate::image;
use crate::json::{self, Value};
use crate::obj;
use crate::util::{self, sha256_hex, sha_file};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

pub const NS: &str = "http://www.acbf.info/xml/acbf/1.1";
pub const READER_PROFILE: &str = "panel-reader.json";

fn esc_text(s: &str) -> String {
    s.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;")
}

fn esc_attr(s: &str) -> String {
    esc_text(s).replace('"', "&quot;").replace('\n', "&#10;").replace('\r', "&#13;").replace('\t', "&#09;")
}

struct Xml(String);

impl Xml {
    fn open(&mut self, tag: &str, attrs: &[(&str, &str)]) {
        self.0.push('<');
        self.0.push_str(tag);
        for (k, v) in attrs {
            self.0.push_str(&format!(" {k}=\"{}\"", esc_attr(v)));
        }
        self.0.push('>');
    }
    fn empty(&mut self, tag: &str, attrs: &[(&str, &str)]) {
        self.0.push('<');
        self.0.push_str(tag);
        for (k, v) in attrs {
            self.0.push_str(&format!(" {k}=\"{}\"", esc_attr(v)));
        }
        self.0.push_str(" />");
    }
    fn close(&mut self, tag: &str) {
        self.0.push_str(&format!("</{tag}>"));
    }
    fn text(&mut self, tag: &str, text: &str, attrs: &[(&str, &str)]) {
        self.open(tag, attrs);
        self.0.push_str(&esc_text(text));
        self.close(tag);
    }
}

fn uuid4() -> String {
    let mut b = [0u8; 16];
    getrandom::fill(&mut b).expect("random");
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    let h = hex::encode(b);
    format!("{}-{}-{}-{}-{}", &h[..8], &h[8..12], &h[12..16], &h[16..20], &h[20..])
}

fn today() -> String {
    // Civil date (UTC) without a time-zone database.
    let days = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs() / 86400) as i64;
    let z = days + 719468;
    let era = z.div_euclid(146097);
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    format!("{:04}-{:02}-{:02}", if m <= 2 { y + 1 } else { y }, m, d)
}

fn walk_files(root: &Path) -> R<Vec<PathBuf>> {
    let mut out = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        for entry in std::fs::read_dir(&dir)? {
            let entry = entry?;
            let ft = entry.file_type()?;
            if ft.is_symlink() {
                return Err("symlinks in source tree are unsupported".into());
            }
            if ft.is_dir() {
                stack.push(entry.path());
            } else {
                out.push(entry.path());
            }
        }
    }
    out.sort();
    Ok(out)
}

/// Build the CBZ; refuses collisions, mapping mistakes and lost source bytes.
pub fn build_cbz(page_root: &Path, panel_data: &Value, output: &Path, title: &str, source_map: &[i64], fallback_reasons: &std::collections::HashMap<i64, String>) -> R<Value> {
    let root = util::resolve(page_root);
    let output = util::resolve(output);
    if output.exists() {
        return Err(format!("output already exists: {}", output.display()).into());
    }
    if output.starts_with(&root) {
        return Err("output must be outside the source page tree".into());
    }
    let files = walk_files(&root)?;
    let rel = |p: &Path| p.strip_prefix(&root).unwrap().to_string_lossy().replace('\\', "/");
    let page_files: Vec<&PathBuf> = files
        .iter()
        .filter(|p| {
            let r = rel(p);
            let name = p.file_name().unwrap().to_string_lossy();
            crate::input::IMAGE_EXTS.contains(&format!(".{}", p.extension().map(|e| e.to_string_lossy().to_lowercase()).unwrap_or_default()).as_str())
                && !r.split('/').any(|c| c == "__MACOSX")
                && !name.starts_with("._")
        })
        .collect();
    let entries = panel_data.opt("pages").as_array().cloned().unwrap_or_default();
    require(!entries.is_empty() && panel_data.opt("total_pages").as_int() == Some(entries.len() as i64), "empty pages or inconsistent total_pages")?;
    let direction = panel_data.opt("reading_direction").as_str().unwrap_or("").to_string();
    require(matches!(direction.as_str(), "ltr" | "rtl"), "reading_direction must be ltr or rtl")?;
    let mut mapped: Vec<(PathBuf, String, Vec<String>)> = Vec::new();
    let mut records = Vec::new();
    let mut seen: Vec<PathBuf> = Vec::new();
    for (i, entry) in entries.iter().enumerate() {
        let index = i as i64 + 1;
        require(entry.opt("page").as_int() == Some(index), "page numbers must be consecutive and in reading order")?;
        let image_name = entry.opt("image").as_str().unwrap_or("").to_string();
        let mut candidates: Vec<&PathBuf> = page_files.iter().copied().filter(|p| rel(p) == image_name).collect();
        if candidates.is_empty() && !image_name.contains('/') {
            candidates = page_files.iter().copied().filter(|p| p.file_name().unwrap().to_string_lossy() == image_name).collect();
        }
        if candidates.len() != 1 {
            return Err(format!("missing or ambiguous page image: {image_name}").into());
        }
        let path = candidates[0].clone();
        if seen.contains(&path) {
            return Err(format!("duplicate page mapping: {image_name}").into());
        }
        seen.push(path.clone());
        let (width, height) = image::image_size(&path)?;
        require(width >= 2 && height >= 2, &format!("page image too small: {image_name}"))?;
        let mut fallback = fallback_reasons.get(&index).cloned();
        let frames: Result<Vec<String>, String> = (|| {
            let panels = entry.opt("panels").as_array().filter(|p| !p.is_empty()).ok_or("empty_panels")?;
            panels
                .iter()
                .map(|p| {
                    let f = |k: &str| p.get(k).and_then(Value::as_f64).ok_or_else(|| format!("'{k}'"));
                    geometry::rectangle(f("x")?, f("y")?, f("w")?, f("h")?, width as i64, height as i64)
                })
                .collect()
        })();
        let frames = match frames {
            Ok(f) => f,
            Err(e) => {
                fallback = Some(match fallback {
                    Some(prev) => format!("{prev}; invalid_geometry: {e}"),
                    None => e,
                });
                vec![geometry::rectangle(0.0, 0.0, 1.0, 1.0, width as i64, height as i64)?]
            }
        };
        let ext = path.extension().map(|e| e.to_string_lossy().to_lowercase()).unwrap_or_default();
        let archive_name = format!("{index:04}.{ext}");
        records.push(obj! {"page" => index, "source_image" => rel(&path), "source_page" => source_map.get(i).copied().unwrap_or(index),
            "archive_image" => archive_name.as_str(), "width" => width, "height" => height, "sha256" => sha_file(&path)?,
            "frame_count" => frames.len(), "frames" => frames.clone(), "fallback_reason" => fallback});
        mapped.push((path, archive_name, frames));
    }
    let mut page_set: Vec<&PathBuf> = page_files.clone();
    page_set.sort();
    let mut seen_sorted: Vec<&PathBuf> = seen.iter().collect();
    seen_sorted.sort();
    if page_set != seen_sorted {
        return Err("unmapped source images would be lost".into());
    }
    let mut x = Xml(String::new());
    x.0.push_str("<?xml version='1.0' encoding='utf-8'?>\n");
    x.open("ACBF", &[("xmlns", NS)]);
    x.open("meta-data", &[]);
    x.open("book-info", &[]);
    x.open("author", &[]);
    x.text("nickname", "Unknown", &[]);
    x.close("author");
    x.text("book-title", title, &[]);
    x.open("coverpage", &[]);
    let (_, cover_name, cover_frames) = &mapped[0];
    x.empty("image", &[("href", cover_name)]);
    for f in cover_frames {
        x.empty("frame", &[("points", f)]);
    }
    x.close("coverpage");
    x.close("book-info");
    x.empty("publish-info", &[]);
    x.open("document-info", &[]);
    x.open("author", &[]);
    x.text("nickname", "comic-panel", &[]);
    x.close("author");
    let date = today();
    x.text("creation-date", &date, &[("value", &date)]);
    x.text("id", &uuid4(), &[]);
    x.close("document-info");
    x.close("meta-data");
    if mapped.len() > 1 {
        x.open("body", &[]);
        for (_, name, frames) in &mapped[1..] {
            x.open("page", &[]);
            x.empty("image", &[("href", name)]);
            for f in frames {
                x.empty("frame", &[("points", f)]);
            }
            x.close("page");
        }
        x.close("body");
    }
    x.close("ACBF");
    let xml = x.0.into_bytes();
    let reader_profile = obj! {"format" => "comic-panel-reader-profile", "version" => 1, "reading_direction" => direction.as_str(), "metadata_sha256" => sha256_hex(&xml)};
    let mut occupied: Vec<String> = mapped.iter().map(|m| m.1.to_lowercase()).collect();
    occupied.push("metadata.acbf".into());
    occupied.push(READER_PROFILE.into());
    let mut auxiliary = Vec::new();
    for path in &files {
        if seen.contains(path) {
            continue;
        }
        let mut name = rel(path);
        if name.to_lowercase().ends_with(".acbf") || occupied.contains(&name.to_lowercase()) {
            name = format!("source-metadata/{name}.original");
        }
        if occupied.contains(&name.to_lowercase()) {
            return Err(format!("preserved auxiliary path collision: {name}").into());
        }
        occupied.push(name.to_lowercase());
        auxiliary.push((path.clone(), name));
    }
    {
        let file = std::fs::OpenOptions::new().write(true).create_new(true).open(&output)?;
        let mut zw = zip::ZipWriter::new(file);
        let opts = zip::write::SimpleFileOptions::default().compression_method(zip::CompressionMethod::Stored);
        let add = |zw: &mut zip::ZipWriter<std::fs::File>, name: &str, data: &[u8]| -> R<()> {
            zw.start_file(name, opts).map_err(|e| e.to_string())?;
            zw.write_all(data)?;
            Ok(())
        };
        for (path, name, _) in &mapped {
            add(&mut zw, name, &std::fs::read(path)?)?;
        }
        add(&mut zw, "metadata.acbf", &xml)?;
        add(&mut zw, READER_PROFILE, format!("{}\n", json::dumps_sorted(&reader_profile)).as_bytes())?;
        for (path, name) in &auxiliary {
            add(&mut zw, name, &std::fs::read(path)?)?;
        }
        let file = zw.finish().map_err(|e| e.to_string())?;
        file.sync_all()?;
    }
    let mut archive = zip::ZipArchive::new(std::fs::File::open(&output)?).map_err(|e| e.to_string())?;
    for record in &records {
        let mut data = Vec::new();
        archive.by_name(record.opt("archive_image").as_str().unwrap()).map_err(|e| e.to_string())?.read_to_end(&mut data)?;
        if Some(sha256_hex(&data).as_str()) != record.opt("sha256").as_str() {
            return Err(Error::Value("archive image preservation check failed".into()));
        }
    }
    let preserved: Vec<Value> = auxiliary.iter().map(|(p, n)| Ok(obj! {"source" => rel(p), "archive" => n.as_str(), "sha256" => sha_file(p)?})).collect::<R<_>>()?;
    Ok(obj! {"output" => util::path_str(&output), "output_sha256" => sha_file(&output)?,
        "page_count" => records.len(), "body_page_count" => records.len() - 1, "reading_direction" => direction.as_str(),
        "pages" => Value::Array(records), "reader_profile" => reader_profile, "preserved_auxiliary" => Value::Array(preserved)})
}
