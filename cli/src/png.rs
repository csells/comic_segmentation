//! PNG decoding (via the `png` crate) and a Pillow-structured RGB encoder:
//! IHDR, IDAT chunks of `max(65536, 4*width)` bytes, IEND; adaptive per-row
//! filter choice exactly as Pillow's `ZipEncode.c`; zlib-ng deflate at level 6
//! with `Z_FILTERED`, window 15 and memLevel 9.

use crate::image::Rgb;
use libz_ng_sys as z;
use std::ffi::c_int;

pub struct Decoded {
    pub width: usize,
    pub height: usize,
    /// RGBA pixels.
    pub rgba: Vec<u8>,
}

pub fn size(bytes: &[u8]) -> Result<(usize, usize), String> {
    let decoder = png::Decoder::new(std::io::Cursor::new(bytes));
    let reader = decoder.read_info().map_err(|e| e.to_string())?;
    let info = reader.info();
    Ok((info.width as usize, info.height as usize))
}

/// Decode to 8-bit RGBA (`convert('RGBA')` semantics for common PNG modes).
pub fn decode(bytes: &[u8]) -> Result<Decoded, String> {
    let mut decoder = png::Decoder::new(std::io::Cursor::new(bytes));
    decoder.set_transformations(png::Transformations::EXPAND | png::Transformations::STRIP_16);
    let mut reader = decoder.read_info().map_err(|e| e.to_string())?;
    let mut buf = vec![0; reader.output_buffer_size()];
    let frame = reader.next_frame(&mut buf).map_err(|e| e.to_string())?;
    let (w, h) = (frame.width as usize, frame.height as usize);
    let data = &buf[..frame.buffer_size()];
    let mut rgba = vec![0u8; w * h * 4];
    match frame.color_type {
        png::ColorType::Rgba => rgba.copy_from_slice(&data[..w * h * 4]),
        png::ColorType::Rgb => {
            for (o, p) in rgba.chunks_exact_mut(4).zip(data.chunks_exact(3)) {
                o[..3].copy_from_slice(p);
                o[3] = 255;
            }
        }
        png::ColorType::Grayscale => {
            for (o, &g) in rgba.chunks_exact_mut(4).zip(data.iter()) {
                o.copy_from_slice(&[g, g, g, 255]);
            }
        }
        png::ColorType::GrayscaleAlpha => {
            for (o, p) in rgba.chunks_exact_mut(4).zip(data.chunks_exact(2)) {
                o.copy_from_slice(&[p[0], p[0], p[0], p[1]]);
            }
        }
        png::ColorType::Indexed => return Err("unexpanded palette PNG".into()),
    }
    Ok(Decoded { width: w, height: h, rgba })
}

fn crc32(data: &[&[u8]]) -> u32 {
    let mut crc: u32 = 0xffff_ffff;
    for part in data {
        for &b in *part {
            crc ^= b as u32;
            for _ in 0..8 {
                crc = if crc & 1 != 0 { (crc >> 1) ^ 0xedb8_8320 } else { crc >> 1 };
            }
        }
    }
    !crc
}

fn chunk(out: &mut Vec<u8>, kind: &[u8; 4], data: &[u8]) {
    out.extend_from_slice(&(data.len() as u32).to_be_bytes());
    out.extend_from_slice(kind);
    out.extend_from_slice(data);
    out.extend_from_slice(&crc32(&[kind, data]).to_be_bytes());
}

#[inline]
fn cost(v: u8) -> i64 {
    if v < 128 { v as i64 } else { 256 - v as i64 }
}

/// Filtered scanlines (filter byte + row) using Pillow's selection order.
fn filtered_rows(img: &Rgb) -> Vec<u8> {
    let bytes = img.width * 3;
    let bpp = 3;
    let mut previous = vec![0u8; bytes + 1];
    let mut out = Vec::with_capacity((bytes + 1) * img.height);
    let mut buffer = vec![0u8; bytes + 1];
    let mut up = vec![2u8; bytes + 1];
    let mut prior = vec![1u8; bytes + 1];
    let mut average = vec![3u8; bytes + 1];
    let mut paeth = vec![4u8; bytes + 1];
    for y in 0..img.height {
        buffer[0] = 0;
        buffer[1..].copy_from_slice(&img.data[y * bytes..(y + 1) * bytes]);
        let mut choice = 0;
        let mut sum: i64 = buffer[1..].iter().map(|&v| cost(v)).sum();
        if sum > 0 {
            let mut s = 0;
            for i in 1..=bytes {
                let v = buffer[i].wrapping_sub(previous[i]);
                up[i] = v;
                s += cost(v);
            }
            if s < sum {
                choice = 2;
                sum = s;
            }
        }
        if sum > 0 {
            let mut s = 0;
            for i in 1..=bytes {
                let v = if i <= bpp { buffer[i] } else { buffer[i].wrapping_sub(buffer[i - bpp]) };
                prior[i] = v;
                s += cost(v);
            }
            if s < sum {
                choice = 1;
                sum = s;
            }
        }
        if sum > 0 {
            let mut s = 0;
            for i in 1..=bytes {
                let v = if i <= bpp {
                    buffer[i].wrapping_sub(previous[i] / 2)
                } else {
                    buffer[i].wrapping_sub(((buffer[i - bpp] as u32 + previous[i] as u32) / 2) as u8)
                };
                average[i] = v;
                s += cost(v);
            }
            if s < sum {
                choice = 3;
                sum = s;
            }
        }
        if sum > 0 {
            let mut s = 0;
            for i in 1..=bytes {
                let v = if i <= bpp {
                    buffer[i].wrapping_sub(previous[i])
                } else {
                    let (a, b, c) = (buffer[i - bpp] as i32, previous[i] as i32, previous[i - bpp] as i32);
                    let (pa, pb, pc) = ((b - c).abs(), (a - c).abs(), (a + b - 2 * c).abs());
                    let pred = if pa <= pb && pa <= pc { a } else if pb <= pc { b } else { c };
                    buffer[i].wrapping_sub(pred as u8)
                };
                paeth[i] = v;
                s += cost(v);
            }
            if s < sum {
                choice = 4;
            }
        }
        match choice {
            0 => out.extend_from_slice(&buffer),
            1 => out.extend_from_slice(&prior),
            2 => out.extend_from_slice(&up),
            3 => out.extend_from_slice(&average),
            _ => out.extend_from_slice(&paeth),
        }
        std::mem::swap(&mut previous, &mut buffer);
    }
    out
}

extern "C" fn zalloc(_opaque: z::voidpf, items: z::uInt, size: z::uInt) -> z::voidpf {
    unsafe { libc::calloc(items as libc::size_t, size as libc::size_t) as z::voidpf }
}

extern "C" fn zfree(_opaque: z::voidpf, address: z::voidpf) {
    unsafe { libc::free(address as *mut libc::c_void) }
}

fn deflate(data: &[u8], row: usize) -> Result<Vec<u8>, String> {
    unsafe {
        let mut uninit = std::mem::MaybeUninit::<z::z_stream>::zeroed();
        let raw = uninit.as_mut_ptr();
        std::ptr::addr_of_mut!((*raw).zalloc).write(zalloc);
        std::ptr::addr_of_mut!((*raw).zfree).write(zfree);
        let mut stream = uninit.assume_init();
        let rc = z::deflateInit2_(
            &mut stream,
            z::Z_DEFAULT_COMPRESSION,
            z::Z_DEFLATED,
            15,
            9,
            z::Z_FILTERED,
            z::zlibVersion(),
            std::mem::size_of::<z::z_stream>() as c_int,
        );
        if rc != z::Z_OK {
            return Err("deflateInit2 failed".into());
        }
        let mut out = Vec::new();
        let mut buf = vec![0u8; 65536];
        // Feed one filtered scanline at a time, like Pillow.
        for line in data.chunks(row) {
            stream.next_in = line.as_ptr() as *mut _;
            stream.avail_in = line.len() as _;
            while stream.avail_in > 0 {
                stream.next_out = buf.as_mut_ptr();
                stream.avail_out = buf.len() as _;
                if z::deflate(&mut stream, z::Z_NO_FLUSH) < 0 {
                    z::deflateEnd(&mut stream);
                    return Err("deflate failed".into());
                }
                out.extend_from_slice(&buf[..buf.len() - stream.avail_out as usize]);
            }
        }
        loop {
            stream.next_out = buf.as_mut_ptr();
            stream.avail_out = buf.len() as _;
            let rc = z::deflate(&mut stream, z::Z_FINISH);
            out.extend_from_slice(&buf[..buf.len() - stream.avail_out as usize]);
            if rc == z::Z_STREAM_END {
                break;
            }
            if rc < 0 {
                z::deflateEnd(&mut stream);
                return Err("deflate failed".into());
            }
        }
        z::deflateEnd(&mut stream);
        Ok(out)
    }
}

/// `image.save(buf, format='PNG')` for an RGB image without ICC/pnginfo.
pub fn encode_rgb(img: &Rgb) -> Result<Vec<u8>, String> {
    if img.width == 0 || img.height == 0 {
        return Err("cannot write empty image as PNG".into());
    }
    let mut out = b"\x89PNG\r\n\x1a\n".to_vec();
    let mut ihdr = Vec::new();
    ihdr.extend_from_slice(&(img.width as u32).to_be_bytes());
    ihdr.extend_from_slice(&(img.height as u32).to_be_bytes());
    ihdr.extend_from_slice(&[8, 2, 0, 0, 0]);
    chunk(&mut out, b"IHDR", &ihdr);
    let stream = deflate(&filtered_rows(img), img.width * 3 + 1)?;
    let block = 65536usize.max(img.width * 4);
    for part in stream.chunks(block) {
        chunk(&mut out, b"IDAT", part);
    }
    chunk(&mut out, b"IEND", b"");
    Ok(out)
}
