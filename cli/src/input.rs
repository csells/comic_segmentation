//! Input preparation: PDF (Poppler), CBZ/ZIP, CBR/RAR and image folders.
//!
//! Every page and auxiliary file is accounted for before any model call;
//! source files are never modified.

use crate::error::{Error, R};
use crate::image;
use crate::json::Value;
use crate::obj;
use crate::util::{self, read_json, save, sha_file, sha256_hex};
use std::collections::{HashMap, HashSet};
use std::io::{Read, Write};
use std::path::{Component, Path, PathBuf};

pub const IMAGE_EXTS: [&str; 6] = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"];

fn ext_lower(path: &Path) -> String {
    path.extension().map(|e| format!(".{}", e.to_string_lossy().to_lowercase())).unwrap_or_default()
}

/// Python `natural` sort key over the relative path string.
fn natural_key(path: &str) -> Vec<(u8, String, u128)> {
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut digits = false;
    let flush = |cur: &mut String, digits: bool, out: &mut Vec<(u8, String, u128)>| {
        if digits {
            out.push((0, String::new(), cur.parse().unwrap_or(u128::MAX)));
        } else {
            out.push((1, cur.to_lowercase(), 0));
        }
        cur.clear();
    };
    for c in path.chars() {
        let d = c.is_ascii_digit();
        if d != digits && !cur.is_empty() {
            flush(&mut cur, digits, &mut out);
        }
        if cur.is_empty() {
            digits = d;
        }
        cur.push(c);
    }
    if !cur.is_empty() || out.is_empty() {
        flush(&mut cur, digits, &mut out);
    }
    // re.split(r'(\d+)') always starts with a (possibly empty) text segment.
    if out.first().map(|t| t.0) == Some(0) {
        out.insert(0, (1, String::new(), 0));
    }
    out
}

fn safe_member(name: &str) -> R<PathBuf> {
    let path = Path::new(name);
    if name.is_empty()
        || name.contains('\\')
        || path.is_absolute()
        || name.contains(':')
        || path.components().any(|c| matches!(c, Component::ParentDir))
    {
        return Err("unsafe archive member".into());
    }
    Ok(path.to_path_buf())
}

/// Archive limits: entry count and actual expanded bytes (declared sizes can lie).
pub const MAX_ENTRIES: usize = 10_000;
pub const MAX_EXPANDED_BYTES: u64 = 2_000_000_000;
/// Pillow's decompression-bomb error threshold (2 x `Image.MAX_IMAGE_PIXELS`).
pub const MAX_PIXELS: u64 = 178_956_970;

/// Copy at most `budget` bytes; more input than that is an archive bomb.
fn bounded_copy(src: &mut impl Read, dst: &mut impl Write, budget: &mut u64) -> R<()> {
    let mut buf = vec![0u8; 1 << 16];
    loop {
        let n = src.read(&mut buf).map_err(|e| Error::Value(format!("archive read failed: {e}")))?;
        if n == 0 {
            return Ok(());
        }
        if n as u64 > *budget {
            return Err("archive expands beyond the 2 GB limit".into());
        }
        *budget -= n as u64;
        dst.write_all(&buf[..n])?;
    }
}

fn extract_zip(source: &Path, dest: &Path) -> R<()> {
    let file = std::fs::File::open(source)?;
    let mut archive = zip::ZipArchive::new(file).map_err(|e| format!("cannot read ZIP archive: {e}"))?;
    let mut declared: u64 = 0;
    for i in 0..archive.len() {
        declared += archive.by_index_raw(i).map_err(|e| e.to_string())?.size();
    }
    if archive.len() > MAX_ENTRIES || declared > MAX_EXPANDED_BYTES {
        return Err("archive exceeds the 10,000-entry / 2 GB limits".into());
    }
    let mut names = HashSet::new();
    for i in 0..archive.len() {
        let entry = archive.by_index_raw(i).map_err(|e| e.to_string())?;
        if entry.encrypted() {
            return Err("encrypted archive members are not supported".into());
        }
        let name = safe_member(&entry.name().map_err(|e| format!("invalid archive member name: {e}"))?)?;
        if !names.insert(name.to_string_lossy().to_lowercase()) {
            return Err("duplicate archive member".into());
        }
        if entry.unix_mode().is_some_and(|m| m & 0o170000 == 0o120000) {
            return Err("archive symlink".into());
        }
    }
    let mut budget = MAX_EXPANDED_BYTES;
    for i in 0..archive.len() {
        let mut entry = archive.by_index(i).map_err(|e| e.to_string())?;
        let target = dest.join(safe_member(&entry.name().map_err(|e| format!("invalid archive member name: {e}"))?)?);
        if entry.is_dir() {
            std::fs::create_dir_all(&target)?;
            continue;
        }
        std::fs::create_dir_all(target.parent().unwrap())?;
        let mut out = std::fs::File::create(&target)?;
        // Reading to the end verifies the entry CRC.
        bounded_copy(&mut entry, &mut out, &mut budget)?;
    }
    Ok(())
}

/// CBR/RAR through `bsdtar` (libarchive; built into macOS, `libarchive-tools` on Debian).
fn extract_rar(source: &Path, dest: &Path) -> R<()> {
    let list = std::process::Command::new("bsdtar")
        .arg("-tvf")
        .arg(source)
        .output()
        .map_err(|e| format!("CBR/RAR input needs bsdtar (libarchive): {e}"))?;
    if !list.status.success() {
        return Err(format!("cannot read RAR archive: {}", String::from_utf8_lossy(&list.stderr).trim()).into());
    }
    let names_out = std::process::Command::new("bsdtar").arg("-tf").arg(source).output()?;
    let mut names = HashSet::new();
    for (line, verbose) in String::from_utf8_lossy(&names_out.stdout).lines().zip(String::from_utf8_lossy(&list.stdout).lines()) {
        if verbose.starts_with('l') || verbose.starts_with('h') {
            return Err("nonregular RAR member".into());
        }
        let name = safe_member(line.trim_end_matches('/'))?;
        if !names.insert(name.to_string_lossy().to_lowercase()) {
            return Err("duplicate RAR member".into());
        }
        if names.len() > MAX_ENTRIES {
            return Err("archive exceeds the 10,000-entry / 2 GB limits".into());
        }
    }
    let status = std::process::Command::new("bsdtar")
        .arg("-xf")
        .arg(source)
        .arg("-C")
        .arg(dest)
        .arg("--no-same-owner")
        .arg("--no-same-permissions")
        .status()?;
    if !status.success() {
        return Err("RAR extraction failed (encrypted, multipart or unsupported archive)".into());
    }
    let mut total = 0u64;
    for entry in walk(dest)? {
        let meta = std::fs::symlink_metadata(&entry)?;
        if meta.file_type().is_symlink() {
            return Err("nonregular RAR member".into());
        }
        total += meta.len();
    }
    if total > MAX_EXPANDED_BYTES {
        return Err("archive expands beyond the 2 GB limit".into());
    }
    Ok(())
}

fn walk(root: &Path) -> R<Vec<PathBuf>> {
    let mut out = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        for entry in std::fs::read_dir(&dir)? {
            let entry = entry?;
            let path = entry.path();
            let ft = entry.file_type()?;
            out.push(path.clone());
            if ft.is_dir() && !ft.is_symlink() {
                stack.push(path);
            }
        }
    }
    Ok(out)
}

fn rel(path: &Path, root: &Path) -> String {
    path.strip_prefix(root).unwrap_or(path).to_string_lossy().replace('\\', "/")
}

/// Source identity: file hash, or a hash of the sorted (relative path, hash) list.
fn source_identity(source: &Path) -> R<String> {
    if source.is_file() {
        return sha_file(source);
    }
    let mut files: Vec<PathBuf> = walk(source)?.into_iter().filter(|p| p.is_file()).collect();
    files.sort_by(|a, b| a.components().cmp(b.components()));
    let list: Vec<Value> =
        files.iter().map(|p| Ok(Value::from(vec![Value::from(rel(p, source)), Value::from(sha_file(p)?)]))).collect::<R<_>>()?;
    Ok(util::json_hash(&Value::Array(list)))
}

/// Decode any supported still image to RGBA, rejecting animation and bombs.
fn decode_still(bytes: &[u8], format: &str) -> R<(usize, usize, Vec<u8>, bool)> {
    use ::image::AnimationDecoder;
    let frames = match format {
        "GIF" => {
            ::image::codecs::gif::GifDecoder::new(std::io::Cursor::new(bytes)).map_err(|e| e.to_string())?.into_frames().take(2).count()
        }
        "WEBP" => {
            let d = ::image::codecs::webp::WebPDecoder::new(std::io::Cursor::new(bytes)).map_err(|e| e.to_string())?;
            if d.has_animation() { 2 } else { 1 }
        }
        "PNG" => {
            let reader = png::Decoder::new(std::io::Cursor::new(bytes)).read_info().map_err(|e| e.to_string())?;
            reader.info().animation_control().map(|a| a.num_frames as usize).unwrap_or(1)
        }
        _ => 1,
    };
    if frames != 1 {
        return Err("animated or multipage image unsupported; no frames were discarded".into());
    }
    let reader = ::image::ImageReader::new(std::io::Cursor::new(bytes)).with_guessed_format().map_err(|e| e.to_string())?;
    let (w, h) = reader.into_dimensions().map_err(|e| format!("unreadable page image: {e}"))?;
    if w as u64 * h as u64 > MAX_PIXELS {
        return Err(format!("page image of {w}x{h} pixels exceeds the decompression-bomb limit").into());
    }
    let img = ::image::load_from_memory(bytes).map_err(|e| format!("unreadable page image: {e}"))?;
    let alpha = img.color().has_alpha();
    let rgba = img.to_rgba8();
    Ok((rgba.width() as usize, rgba.height() as usize, rgba.into_raw(), alpha))
}

/// `import_format.prepare_publication_image`: preserve compatible upright
/// JPEG/PNG bytes; otherwise write an upright PNG and keep the original bytes.
fn prepare_publication_image(source: &Path, stem: &Path, originals: &Path, locator: &str) -> R<Value> {
    let bytes = std::fs::read(source)?;
    let source_hash = sha256_hex(&bytes);
    let format =
        image::sniff_format(&bytes).ok_or_else(|| Error::Value(format!("unsupported publication image format: {}", ext_lower(source))))?;
    let orientation = exif_orientation(&bytes);
    if !(1..=8).contains(&orientation) {
        return Err("invalid EXIF orientation".into());
    }
    // Decode every page now so unreadable content stops the run before any paid call.
    let (ow, oh, rgba, alpha) = match format {
        "JPEG" => {
            let rgb = image::decode_jpeg(&bytes).map_err(|e| format!("unreadable page image {locator}: {e}"))?;
            let mut rgba = Vec::with_capacity(rgb.width * rgb.height * 4);
            for p in rgb.data.as_chunks::<3>().0 {
                rgba.extend_from_slice(&[p[0], p[1], p[2], 255]);
            }
            (rgb.width, rgb.height, rgba, false)
        }
        _ => decode_still(&bytes, format).map_err(|e| Error::Value(format!("{locator}: {}", e.message())))?,
    };
    let transformed = !matches!(format, "JPEG" | "PNG") || orientation != 1;
    let compatible: &[&str] = if format == "JPEG" { &[".jpg", ".jpeg"] } else { &[".png"] };
    let mut extension = if transformed || format == "PNG" { ".png".to_string() } else { ".jpg".to_string() };
    if !transformed && compatible.contains(&ext_lower(source).as_str()) {
        extension = ext_lower(source);
    }
    let name = stem.file_name().unwrap().to_string_lossy().into_owned();
    let destination = stem.with_file_name(format!("{name}{extension}"));
    let original = originals.join(format!("{name}{}.original", ext_lower(source)));
    if destination.exists() || (transformed && original.exists()) {
        return Err("publication image or preserved original already exists".into());
    }
    std::fs::create_dir_all(destination.parent().unwrap())?;
    let mut operations = Vec::new();
    let (w, h) = if transformed {
        std::fs::create_dir_all(originals)?;
        util::write_new(&original, &bytes)?;
        let (tw, th, upright) = image::exif_transpose(&rgba, ow, oh, orientation);
        if orientation != 1 {
            operations.push("exif-transpose");
        }
        let png = if alpha {
            crate::png::encode_rgba(tw, th, &upright)?
        } else {
            let mut rgb = image::Rgb::new(tw, th);
            for (o, p) in rgb.data.as_chunks_mut::<3>().0.iter_mut().zip(upright.chunks_exact(4)) {
                o.copy_from_slice(&p[..3]);
            }
            crate::png::encode_rgb(&rgb)?
        };
        util::write_new(&destination, &png)?;
        operations.push("encode-png");
        (tw, th)
    } else {
        util::write_new(&destination, &bytes)?;
        (ow, oh)
    };
    Ok(
        obj! {"locator" => locator, "image" => destination.file_name().unwrap().to_string_lossy().as_ref(), "sha256" => sha_file(&destination)?,
        "width" => w, "height" => h, "original_sha256" => source_hash, "original_format" => format,
        "original_dimensions" => vec![ow as i64, oh as i64], "original_exif_orientation" => orientation,
        "publication_transforms" => operations,
        "preserved_original" => if transformed { Value::from(rel(&original, destination.parent().unwrap())) } else { Value::Null }},
    )
}

fn exif_orientation(bytes: &[u8]) -> i64 {
    let mut cursor = std::io::Cursor::new(bytes);
    match exif::Reader::new().read_from_container(&mut cursor) {
        Ok(data) => {
            data.get_field(exif::Tag::Orientation, exif::In::PRIMARY).and_then(|f| f.value.get_uint(0)).map(|v| v as i64).unwrap_or(1)
        }
        Err(_) => 1,
    }
}

/// `prepare_input`: canonical page images plus `input.json`.
pub fn prepare_input(source: &Path, work: &Path, render_cache: Option<&Path>) -> R<Value> {
    let source = util::resolve(source);
    std::fs::create_dir_all(work)?;
    let manifest = work.join("input.json");
    let pages = work.join("pages");
    let source_id = source_identity(&source)?;
    if manifest.exists() {
        let previous = read_json(&manifest)?;
        if previous.opt("source_sha256").as_str() != Some(&source_id) {
            return Err("input changed; use a new run".into());
        }
        for p in previous.opt("pages").as_array().unwrap() {
            if Some(sha_file(&pages.join(p.opt("image").as_str().unwrap()))?.as_str()) != p.opt("sha256").as_str() {
                return Err("prepared page changed".into());
            }
        }
        return Ok(previous);
    }
    if pages.exists() && std::fs::read_dir(&pages)?.next().is_some() {
        return Err("incomplete input preparation; preserve it and use a new output directory".into());
    }
    std::fs::create_dir_all(&pages)?;
    let mut source_map: Vec<Value> = Vec::new();
    if ext_lower(&source) == ".pdf" {
        let info = std::process::Command::new("pdfinfo").arg(&source).output().map_err(|e| format!("pdfinfo: {e}"))?;
        let text = String::from_utf8_lossy(&info.stdout);
        let count: usize = text
            .lines()
            .find_map(|l| l.strip_prefix("Pages:").map(|v| v.trim().parse().unwrap_or(0)))
            .filter(|c| *c > 0)
            .ok_or("PDF page count unavailable")?;
        let cache = match render_cache {
            Some(p) => Some(read_json(p)?),
            None => None,
        };
        if let Some(c) = &cache
            && (c.opt("source_pdf_sha256").as_str() != Some(&source_id) || c.opt("page_count").as_int() != Some(count as i64))
        {
            return Err("render cache does not match PDF".into());
        }
        for i in 1..=count {
            let dest = pages.join(format!("{i:04}.jpg"));
            if let Some(c) = &cache {
                let record = &c.opt("pages").as_array().unwrap()[i - 1];
                let old = render_cache.unwrap().parent().unwrap().join("pages").join(record.opt("archive_image").as_str().unwrap_or(""));
                if record.opt("source_page").as_int() != Some(i as i64) || Some(sha_file(&old)?.as_str()) != record.opt("sha256").as_str() {
                    return Err("invalid render cache".into());
                }
                if !dest.exists() {
                    std::fs::hard_link(&old, &dest)?;
                } else if Some(sha_file(&dest)?.as_str()) != record.opt("sha256").as_str() {
                    return Err("partial render cache differs".into());
                }
            } else {
                let status = std::process::Command::new("pdftoppm")
                    .args(["-f", &i.to_string(), "-l", &i.to_string(), "-singlefile", "-jpeg", "-r", "150"])
                    .arg(&source)
                    .arg(dest.with_extension(""))
                    .status()
                    .map_err(|e| format!("pdftoppm: {e}"))?;
                if !status.success() {
                    return Err(format!("pdftoppm failed on page {i}").into());
                }
            }
            source_map.push(obj! {"locator" => format!("PDF page {i}"), "image" => dest.file_name().unwrap().to_string_lossy().as_ref(), "sha256" => sha_file(&dest)?});
            if i == 1 || i % 25 == 0 || i == count {
                println!("prepare [{i}/{count}] PDF pages");
            }
        }
    } else {
        let extracted = if source.is_file() {
            let dir = work.join("extracted");
            std::fs::create_dir_all(&dir)?;
            let head = std::fs::read(&source)?.into_iter().take(4).collect::<Vec<u8>>();
            if head.starts_with(b"PK") {
                extract_zip(&source, &dir)?;
            } else if matches!(ext_lower(&source).as_str(), ".cbr" | ".rar") {
                extract_rar(&source, &dir)?;
            } else {
                return Err("expected PDF, CBZ/ZIP, CBR/RAR or image folder".into());
            }
            dir
        } else {
            source.clone()
        };
        let mut files = walk(&extracted)?;
        files.sort_by_key(|a| natural_key(&rel(a, &extracted)));
        for p in &files {
            if std::fs::symlink_metadata(p)?.file_type().is_symlink() {
                return Err("source symlinks unsupported".into());
            }
        }
        for path in &files {
            let r = rel(path, &extracted);
            let name = path.file_name().unwrap().to_string_lossy();
            if !path.is_file() || r.split('/').any(|c| c == "__MACOSX") || name.starts_with("._") {
                continue;
            }
            if IMAGE_EXTS.contains(&ext_lower(path).as_str()) {
                let stem = pages.join(format!("{:04}", source_map.len() + 1));
                source_map.push(prepare_publication_image(path, &stem, &pages.join("source-auxiliary/original-images"), &r)?);
            } else {
                let dest = pages.join("source-auxiliary").join(&r);
                std::fs::create_dir_all(dest.parent().unwrap())?;
                std::fs::copy(path, &dest)?;
            }
        }
    }
    if source_map.is_empty() {
        return Err("input contains no comic page images".into());
    }
    for record in source_map.iter_mut() {
        let (w, h) = image::image_size(&pages.join(record.opt("image").as_str().unwrap()))?;
        record.set("width", w);
        record.set("height", h);
    }
    let result = obj! {"source" => util::path_str(&source), "source_sha256" => source_id, "pages" => Value::Array(source_map),
    "render_cache" => render_cache.map(util::path_str)};
    save(&manifest, &result)?;
    Ok(result)
}

/// `prepare_analysis_image`: JPEG pages are analysed as-is; others get an upright JPEG copy.
pub fn prepare_analysis_image(image_path: &Path, output: &Path, number: usize) -> R<PathBuf> {
    if matches!(ext_lower(image_path).as_str(), ".jpg" | ".jpeg") {
        return Ok(image_path.to_path_buf());
    }
    let analysis = output.join(format!("analysis-{number:04}.jpg"));
    let provenance = output.join(format!("analysis-{number:04}.json"));
    let source_hash = sha_file(image_path)?;
    if provenance.exists() {
        let record = read_json(&provenance)?;
        if record.opt("publication_sha256").as_str() != Some(&source_hash)
            || Some(sha_file(&analysis)?.as_str()) != record.opt("analysis_sha256").as_str()
        {
            return Err("analysis source or cached pixels changed".into());
        }
        return Ok(analysis);
    }
    if analysis.exists() {
        return Err("unfinalized analysis image; preserve and inspect before resuming".into());
    }
    let bytes = std::fs::read(image_path)?;
    let rgb = match image::sniff_format(&bytes) {
        Some("PNG") => {
            let d = crate::png::decode(&bytes)?;
            image::composite_on_white(d.width, d.height, &d.rgba)
        }
        Some("JPEG") => image::decode_jpeg(&bytes)?,
        _ => return Err("unsupported analysis image".into()),
    };
    std::fs::write(&analysis, image::encode_jpeg(&rgb, 95)?)?;
    save(
        &provenance,
        &obj! {"publication_sha256" => source_hash, "analysis_sha256" => sha_file(&analysis)?,
        "transform" => "upright source composited on white, JPEG quality95"},
    )?;
    Ok(analysis)
}

/// `source_page_context`: up to two actual predecessors per analysis image.
pub fn source_page_context(paths: &[PathBuf]) -> HashMap<String, Vec<String>> {
    let resolved: Vec<String> = paths.iter().map(|p| util::path_str(&util::resolve(p))).collect();
    resolved.iter().enumerate().map(|(i, p)| (p.clone(), resolved[i.saturating_sub(2)..i].to_vec())).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn natural_order_matches_python() {
        let mut names = vec!["page10.jpg", "page2.jpg", "Page1.jpg", "a/b3.png", "a/b20.png"];
        names.sort_by_key(|a| natural_key(a));
        // CPython: sorted(..., key=natural) puts "a/..." before "page..." (case-folded).
        assert_eq!(names, vec!["a/b3.png", "a/b20.png", "Page1.jpg", "page2.jpg", "page10.jpg"]);
    }
}
