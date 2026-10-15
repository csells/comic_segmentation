//! Hashing and durable-file helpers shared across modules.

use crate::error::R;
use crate::json::{self, Value};
use sha2::{Digest, Sha256};
use std::io::Write;
use std::path::{Path, PathBuf};

pub fn sha256_hex(data: &[u8]) -> String {
    hex::encode(Sha256::digest(data))
}

pub fn sha_file(path: &Path) -> R<String> {
    Ok(sha256_hex(&std::fs::read(path).map_err(|e| format!("{}: {e}", path.display()))?))
}

/// `hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()`.
pub fn json_hash(value: &Value) -> String {
    sha256_hex(json::dumps_sorted(value).as_bytes())
}

pub fn read_json(path: &Path) -> R<Value> {
    let text = std::fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
    Ok(json::loads(&text)?)
}

/// `gemini_probe.save`: exclusive create, indent=2, trailing newline, fsync.
pub fn save(path: &Path, value: &Value) -> R<()> {
    let mut f = std::fs::OpenOptions::new().write(true).create_new(true).open(path).map_err(|e| format!("{}: {e}", path.display()))?;
    f.write_all(json::dumps_indent(value).as_bytes())?;
    f.write_all(b"\n")?;
    f.flush()?;
    f.sync_all()?;
    Ok(())
}

/// Exclusive create of raw bytes.
pub fn write_new(path: &Path, data: &[u8]) -> R<()> {
    let mut f = std::fs::OpenOptions::new().write(true).create_new(true).open(path).map_err(|e| format!("{}: {e}", path.display()))?;
    f.write_all(data)?;
    Ok(())
}

/// `Path.resolve()` that tolerates missing paths (like Python's non-strict resolve).
pub fn resolve(path: &Path) -> PathBuf {
    if let Ok(p) = std::fs::canonicalize(path) {
        return p;
    }
    let abs = if path.is_absolute() { path.to_path_buf() } else { std::env::current_dir().unwrap_or_default().join(path) };
    let mut out = PathBuf::new();
    for c in abs.components() {
        match c {
            std::path::Component::ParentDir => {
                out.pop();
            }
            std::path::Component::CurDir => {}
            other => out.push(other),
        }
    }
    out
}

pub fn path_str(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

pub fn b64(data: &[u8]) -> String {
    use base64::Engine;
    base64::engine::general_purpose::STANDARD.encode(data)
}

pub fn b64_decode(text: &str) -> R<Vec<u8>> {
    use base64::Engine;
    Ok(base64::engine::general_purpose::STANDARD.decode(text).map_err(|e| e.to_string())?)
}

/// A data-URL image part as the prototype sends it.
pub fn image_part(data: &[u8], mime: &str) -> Value {
    crate::obj! {"type" => "input_image", "image_url" => format!("data:{mime};base64,{}", b64(data)), "detail" => "original"}
}

pub fn text_part(text: impl Into<String>) -> Value {
    crate::obj! {"type" => "input_text", "text" => text.into()}
}
