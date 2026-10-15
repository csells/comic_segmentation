//! 8-bit RGB raster operations reproducing Pillow 12 byte for byte.
//!
//! Model requests embed generated JPEG/PNG bytes, so request identities depend
//! on exact pixels and encoder settings. JPEG uses libjpeg-turbo with Pillow's
//! defaults (accurate DCT, fancy upsampling, 4:2:0, quality 95). Resampling and
//! drawing are ports of Pillow's `Resample.c` and `Draw.c`.

use std::ffi::c_int;
use std::path::Path;
use turbojpeg_sys as tj;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Rgb {
    pub width: usize,
    pub height: usize,
    /// Row-major RGB triples.
    pub data: Vec<u8>,
}

impl Rgb {
    pub fn new(width: usize, height: usize) -> Rgb {
        Rgb { width, height, data: vec![0; width * height * 3] }
    }

    #[inline]
    pub fn px(&self, x: usize, y: usize) -> [u8; 3] {
        let i = (y * self.width + x) * 3;
        [self.data[i], self.data[i + 1], self.data[i + 2]]
    }

    /// Pillow `Image.crop((l, t, r, b))`; areas outside the image are black.
    pub fn crop(&self, l: i64, t: i64, r: i64, b: i64) -> Rgb {
        let w = (r - l).max(0) as usize;
        let h = (b - t).max(0) as usize;
        let mut out = Rgb::new(w, h);
        for y in 0..h {
            let sy = t + y as i64;
            if sy < 0 || sy >= self.height as i64 {
                continue;
            }
            let x0 = l.max(0);
            let x1 = r.min(self.width as i64);
            if x1 <= x0 {
                continue;
            }
            let src = ((sy as usize) * self.width + x0 as usize) * 3;
            let dst = (y * w + (x0 - l) as usize) * 3;
            let n = (x1 - x0) as usize * 3;
            out.data[dst..dst + n].copy_from_slice(&self.data[src..src + n]);
        }
        out
    }

    /// Per-pixel max over channels (`rgb.max(axis=2)`).
    pub fn channel_max(&self) -> Vec<u8> {
        self.data.chunks_exact(3).map(|p| p[0].max(p[1]).max(p[2])).collect()
    }

    /// Per-pixel min over channels (`rgb.min(axis=2)`).
    pub fn channel_min(&self) -> Vec<u8> {
        self.data.chunks_exact(3).map(|p| p[0].min(p[1]).min(p[2])).collect()
    }
}

// ---------------------------------------------------------------- JPEG

struct Handle(tj::tjhandle);

impl Drop for Handle {
    fn drop(&mut self) {
        unsafe { tj::tj3Destroy(self.0) };
    }
}

fn tj_error(h: &Handle) -> String {
    unsafe {
        let msg = tj::tj3GetErrorStr(h.0);
        if msg.is_null() {
            "libjpeg-turbo error".into()
        } else {
            std::ffi::CStr::from_ptr(msg).to_string_lossy().into_owned()
        }
    }
}

/// Decode a JPEG the way `Image.open(p).convert('RGB')` does.
pub fn decode_jpeg(bytes: &[u8]) -> Result<Rgb, String> {
    unsafe {
        let h = Handle(tj::tj3Init(tj::TJINIT_TJINIT_DECOMPRESS as c_int));
        if h.0.is_null() {
            return Err("libjpeg-turbo init failed".into());
        }
        if tj::tj3DecompressHeader(h.0, bytes.as_ptr(), bytes.len() as _) != 0 {
            return Err(tj_error(&h));
        }
        let w = tj::tj3Get(h.0, tj::TJPARAM_TJPARAM_JPEGWIDTH as c_int);
        let ht = tj::tj3Get(h.0, tj::TJPARAM_TJPARAM_JPEGHEIGHT as c_int);
        let colorspace = tj::tj3Get(h.0, tj::TJPARAM_TJPARAM_COLORSPACE as c_int);
        if w <= 0 || ht <= 0 {
            return Err("invalid JPEG dimensions".into());
        }
        tj::tj3Set(h.0, tj::TJPARAM_TJPARAM_FASTUPSAMPLE as c_int, 0);
        tj::tj3Set(h.0, tj::TJPARAM_TJPARAM_FASTDCT as c_int, 0);
        let (w, ht) = (w as usize, ht as usize);
        if colorspace == tj::TJCS_TJCS_CMYK as c_int || colorspace == tj::TJCS_TJCS_YCCK as c_int {
            // Pillow decodes Adobe CMYK as inverted CMYK, then converts to RGB.
            let mut cmyk = vec![0u8; w * ht * 4];
            if tj::tj3Decompress8(h.0, bytes.as_ptr(), bytes.len() as _, cmyk.as_mut_ptr(), 0, tj::TJPF_TJPF_CMYK as c_int) != 0 {
                return Err(tj_error(&h));
            }
            let mut out = Rgb::new(w, ht);
            for (o, p) in out.data.chunks_exact_mut(3).zip(cmyk.chunks_exact(4)) {
                // Pillow stores Adobe JPEG CMYK inverted ("CMYK;I"), then `cmyk2rgb`.
                let inv = |v: u8| 255 - v as i32;
                let nk = 255 - inv(p[3]);
                let muldiv255 = |a: i32, b: i32| {
                    let t = a * b + 128;
                    ((t >> 8) + t) >> 8
                };
                o[0] = (nk - muldiv255(inv(p[0]), nk)).clamp(0, 255) as u8;
                o[1] = (nk - muldiv255(inv(p[1]), nk)).clamp(0, 255) as u8;
                o[2] = (nk - muldiv255(inv(p[2]), nk)).clamp(0, 255) as u8;
            }
            return Ok(out);
        }
        let mut out = Rgb::new(w, ht);
        if tj::tj3Decompress8(h.0, bytes.as_ptr(), bytes.len() as _, out.data.as_mut_ptr(), 0, tj::TJPF_TJPF_RGB as c_int) != 0 {
            return Err(tj_error(&h));
        }
        Ok(out)
    }
}

/// Header-only JPEG dimensions.
pub fn jpeg_size(bytes: &[u8]) -> Result<(usize, usize), String> {
    unsafe {
        let h = Handle(tj::tj3Init(tj::TJINIT_TJINIT_DECOMPRESS as c_int));
        if tj::tj3DecompressHeader(h.0, bytes.as_ptr(), bytes.len() as _) != 0 {
            return Err(tj_error(&h));
        }
        Ok((
            tj::tj3Get(h.0, tj::TJPARAM_TJPARAM_JPEGWIDTH as c_int) as usize,
            tj::tj3Get(h.0, tj::TJPARAM_TJPARAM_JPEGHEIGHT as c_int) as usize,
        ))
    }
}

/// Encode like Pillow `save(..., format='JPEG', quality=q)` for an RGB image.
pub fn encode_jpeg(img: &Rgb, quality: i32) -> Result<Vec<u8>, String> {
    if img.width == 0 || img.height == 0 {
        return Err("tile cannot extend outside image".into());
    }
    unsafe {
        let h = Handle(tj::tj3Init(tj::TJINIT_TJINIT_COMPRESS as c_int));
        tj::tj3Set(h.0, tj::TJPARAM_TJPARAM_QUALITY as c_int, quality);
        tj::tj3Set(h.0, tj::TJPARAM_TJPARAM_SUBSAMP as c_int, tj::TJSAMP_TJSAMP_420 as c_int);
        tj::tj3Set(h.0, tj::TJPARAM_TJPARAM_FASTDCT as c_int, 0);
        tj::tj3Set(h.0, tj::TJPARAM_TJPARAM_OPTIMIZE as c_int, 0);
        tj::tj3Set(h.0, tj::TJPARAM_TJPARAM_PROGRESSIVE as c_int, 0);
        let mut out: *mut u8 = std::ptr::null_mut();
        let mut size = 0;
        let rc = tj::tj3Compress8(
            h.0,
            img.data.as_ptr(),
            img.width as c_int,
            0,
            img.height as c_int,
            tj::TJPF_TJPF_RGB as c_int,
            &mut out,
            &mut size,
        );
        if rc != 0 {
            return Err(tj_error(&h));
        }
        let bytes = std::slice::from_raw_parts(out, size as usize).to_vec();
        tj::tj3Free(out as *mut _);
        Ok(bytes)
    }
}

// ---------------------------------------------------------------- decoding any page image

/// Decoded still image with Pillow's `convert('RGBA')` semantics where needed.
pub struct Decoded {
    pub format: &'static str,
    pub width: usize,
    pub height: usize,
    /// RGBA pixels (alpha 255 for opaque sources).
    pub rgba: Vec<u8>,
    pub has_alpha: bool,
}

pub fn sniff_format(bytes: &[u8]) -> Option<&'static str> {
    if bytes.starts_with(&[0xff, 0xd8, 0xff]) {
        Some("JPEG")
    } else if bytes.starts_with(b"\x89PNG\r\n\x1a\n") {
        Some("PNG")
    } else if bytes.starts_with(b"BM") {
        Some("BMP")
    } else if bytes.starts_with(b"GIF87a") || bytes.starts_with(b"GIF89a") {
        Some("GIF")
    } else if bytes.len() >= 12 && &bytes[..4] == b"RIFF" && &bytes[8..12] == b"WEBP" {
        Some("WEBP")
    } else {
        None
    }
}

/// `Image.open(path).convert('RGB')` for supported page formats.
pub fn load_rgb(path: &Path) -> Result<Rgb, String> {
    let bytes = std::fs::read(path).map_err(|e| e.to_string())?;
    match sniff_format(&bytes) {
        Some("JPEG") => decode_jpeg(&bytes),
        Some("PNG") => {
            let d = crate::png::decode(&bytes)?;
            let mut out = Rgb::new(d.width, d.height);
            for (o, p) in out.data.chunks_exact_mut(3).zip(d.rgba.chunks_exact(4)) {
                o.copy_from_slice(&p[..3]);
            }
            Ok(out)
        }
        other => Err(format!("unsupported image format: {other:?}")),
    }
}

/// Image dimensions without full decoding where possible.
pub fn image_size(path: &Path) -> Result<(usize, usize), String> {
    let bytes = std::fs::read(path).map_err(|e| e.to_string())?;
    match sniff_format(&bytes) {
        Some("JPEG") => jpeg_size(&bytes),
        Some("PNG") => crate::png::size(&bytes),
        other => Err(format!("unsupported image format: {other:?}")),
    }
}

/// Pillow `ImagingAlphaComposite(white opaque, src)` then `convert('RGB')`.
pub fn composite_on_white(width: usize, height: usize, rgba: &[u8]) -> Rgb {
    const PB: u32 = 7;
    let mut out = Rgb::new(width, height);
    let div255 = |a: u32| ((a >> 8) + a) >> 8;
    for (o, s) in out.data.chunks_exact_mut(3).zip(rgba.chunks_exact(4)) {
        let sa = s[3] as u32;
        if sa == 0 {
            o.copy_from_slice(&[255, 255, 255]);
            continue;
        }
        let blend = 255 * (255 - sa);
        let outa255 = sa * 255 + blend;
        let coef1 = sa * 255 * 255 * (1 << PB) / outa255;
        let coef2 = 255 * (1 << PB) - coef1;
        for c in 0..3 {
            let tmp = s[c] as u32 * coef1 + 255 * coef2;
            o[c] = (div255(tmp + (0x80 << PB)) >> PB) as u8;
        }
    }
    out
}

// ---------------------------------------------------------------- Pillow resampling

const PRECISION_BITS: i32 = 32 - 8 - 2;

fn sinc(x: f64) -> f64 {
    if x == 0.0 {
        return 1.0;
    }
    let x = x * std::f64::consts::PI;
    x.sin() / x
}

fn lanczos(x: f64) -> f64 {
    if (-3.0..3.0).contains(&x) { sinc(x) * sinc(x / 3.0) } else { 0.0 }
}

struct Coeffs {
    ksize: usize,
    bounds: Vec<(usize, usize)>,
    kk: Vec<i32>,
}

/// `precompute_coeffs` + `normalize_coeffs_8bpc` from Pillow `Resample.c`.
fn coeffs(in_size: usize, in0: f32, in1: f32, out_size: usize) -> Coeffs {
    let support_base = 3.0;
    let scale = (in1 - in0) as f64 / out_size as f64;
    let filterscale = if scale < 1.0 { 1.0 } else { scale };
    let support = support_base * filterscale;
    let ksize = (support.ceil() as usize) * 2 + 1;
    let mut pre = vec![0f64; out_size * ksize];
    let mut bounds = Vec::with_capacity(out_size);
    for xx in 0..out_size {
        let center = in0 as f64 + (xx as f64 + 0.5) * scale;
        let mut ww = 0.0;
        let ss = 1.0 / filterscale;
        let mut xmin = (center - support + 0.5) as i64;
        if xmin < 0 {
            xmin = 0;
        }
        let mut xmax = (center + support + 0.5) as i64;
        if xmax > in_size as i64 {
            xmax = in_size as i64;
        }
        xmax -= xmin;
        let k = &mut pre[xx * ksize..(xx + 1) * ksize];
        for x in 0..xmax.max(0) as usize {
            let w = lanczos((x as f64 + xmin as f64 - center + 0.5) * ss);
            k[x] = w;
            ww += w;
        }
        for x in 0..xmax.max(0) as usize {
            if ww != 0.0 {
                k[x] /= ww;
            }
        }
        bounds.push((xmin as usize, xmax.max(0) as usize));
    }
    let one = (1i64 << PRECISION_BITS) as f64;
    let kk = pre
        .iter()
        .map(|&v| if v < 0.0 { (-0.5 + v * one) as i32 } else { (0.5 + v * one) as i32 })
        .collect();
    Coeffs { ksize, bounds, kk }
}

#[inline]
fn clip8(v: i32) -> u8 {
    (v >> PRECISION_BITS).clamp(0, 255) as u8
}

/// Pillow `Image.resize((w, h), Image.Resampling.LANCZOS)` on an RGB image.
pub fn resize_lanczos(img: &Rgb, out_w: usize, out_h: usize) -> Rgb {
    let (in_w, in_h) = (img.width, img.height);
    let need_h = out_w != in_w;
    let need_v = out_h != in_h;
    let horiz = coeffs(in_w, 0.0, in_w as f32, out_w);
    let mut vert = coeffs(in_h, 0.0, in_h as f32, out_h);
    let ybox_first = vert.bounds[0].0;
    let last = vert.bounds[out_h - 1];
    let ybox_last = last.0 + last.1;
    let mut current = img.clone();
    if need_h {
        for b in vert.bounds.iter_mut() {
            b.0 -= ybox_first;
        }
        let rows = ybox_last - ybox_first;
        let mut tmp = Rgb::new(out_w, rows);
        let half = 1i32 << (PRECISION_BITS - 1);
        for yy in 0..rows {
            let sy = yy + ybox_first;
            let row = &img.data[sy * in_w * 3..(sy + 1) * in_w * 3];
            for xx in 0..out_w {
                let (xmin, xmax) = horiz.bounds[xx];
                let k = &horiz.kk[xx * horiz.ksize..];
                let (mut s0, mut s1, mut s2) = (half, half, half);
                for x in 0..xmax {
                    let p = (x + xmin) * 3;
                    s0 = s0.wrapping_add(row[p] as i32 * k[x]);
                    s1 = s1.wrapping_add(row[p + 1] as i32 * k[x]);
                    s2 = s2.wrapping_add(row[p + 2] as i32 * k[x]);
                }
                let o = (yy * out_w + xx) * 3;
                tmp.data[o] = clip8(s0);
                tmp.data[o + 1] = clip8(s1);
                tmp.data[o + 2] = clip8(s2);
            }
        }
        current = tmp;
    }
    if need_v {
        let w = current.width;
        let mut out = Rgb::new(w, out_h);
        let half = 1i32 << (PRECISION_BITS - 1);
        for yy in 0..out_h {
            let (ymin, ymax) = vert.bounds[yy];
            let k = &vert.kk[yy * vert.ksize..];
            for xx in 0..w {
                let (mut s0, mut s1, mut s2) = (half, half, half);
                for y in 0..ymax {
                    let p = ((y + ymin) * w + xx) * 3;
                    s0 = s0.wrapping_add(current.data[p] as i32 * k[y]);
                    s1 = s1.wrapping_add(current.data[p + 1] as i32 * k[y]);
                    s2 = s2.wrapping_add(current.data[p + 2] as i32 * k[y]);
                }
                let o = (yy * w + xx) * 3;
                out.data[o] = clip8(s0);
                out.data[o + 1] = clip8(s1);
                out.data[o + 2] = clip8(s2);
            }
        }
        current = out;
    }
    current
}

// ---------------------------------------------------------------- Pillow drawing

fn hline(img: &mut Rgb, x0: i64, y: i64, x1: i64, ink: [u8; 3]) {
    // Pillow `hline32`: clip, then fill x0..=x1 (nothing when x0 > x1).
    if y < 0 || y >= img.height as i64 {
        return;
    }
    let mut x0 = x0;
    let mut x1 = x1;
    if x0 < 0 {
        x0 = 0;
    } else if x0 >= img.width as i64 {
        return;
    }
    if x1 < 0 {
        return;
    } else if x1 >= img.width as i64 {
        x1 = img.width as i64 - 1;
    }
    for x in x0..=x1 {
        let i = (y as usize * img.width + x as usize) * 3;
        img.data[i..i + 3].copy_from_slice(&ink);
    }
}

fn point(img: &mut Rgb, x: i64, y: i64, ink: [u8; 3]) {
    if x >= 0 && x < img.width as i64 && y >= 0 && y < img.height as i64 {
        let i = (y as usize * img.width + x as usize) * 3;
        img.data[i..i + 3].copy_from_slice(&ink);
    }
}

/// Pillow `line32` for a vertical segment: |dy| points from y0 toward y1, excluding y1.
fn vline(img: &mut Rgb, x: i64, y0: i64, y1: i64, ink: [u8; 3]) {
    let step = if y1 < y0 { -1 } else { 1 };
    let mut y = y0;
    for _ in 0..(y1 - y0).abs() {
        point(img, x, y, ink);
        y += step;
    }
}

/// Pillow `ImageDraw.rectangle([x0, y0, x1, y1], outline=ink, width=w)` (inclusive corners).
pub fn draw_rectangle_outline(img: &mut Rgb, x0: i64, y0: i64, x1: i64, y1: i64, ink: [u8; 3], width: i64) {
    let width = if width == 0 { 1 } else { width };
    for i in 0..width {
        hline(img, x0, y0 + i, x1, ink);
        hline(img, x0, y1 - i, x1, ink);
        vline(img, x1 - i, y0 + width, y1 - width + 1, ink);
        vline(img, x0 + i, y0 + width, y1 - width + 1, ink);
    }
}
