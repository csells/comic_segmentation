//! PNG support (placeholder until the Pillow-compatible encoder lands).
pub struct Decoded {
    pub width: usize,
    pub height: usize,
    pub rgba: Vec<u8>,
}
pub fn decode(_bytes: &[u8]) -> Result<Decoded, String> {
    Err("PNG decoding not implemented".into())
}
pub fn size(_bytes: &[u8]) -> Result<(usize, usize), String> {
    Err("PNG decoding not implemented".into())
}
