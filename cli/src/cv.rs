//! Binary-image primitives reproducing the OpenCV 5.0 / NumPy 2.5 calls the
//! deterministic refiners rely on: 3x3 closing, 8-connected component labels
//! and statistics in OpenCV order, CCOMP hole contours, and linear quantiles.

/// `cv2.morphologyEx(mask, MORPH_CLOSE, ones((3,3)))` for a 0/1 mask.
///
/// OpenCV's default constant border is 0 for dilation and 255 for erosion.
pub fn close3(mask: &[u8], w: usize, h: usize) -> Vec<u8> {
    let mut dil = vec![0u8; w * h];
    for y in 0..h {
        for x in 0..w {
            let mut v = 0u8;
            'n: for dy in -1i64..=1 {
                let yy = y as i64 + dy;
                if yy < 0 || yy >= h as i64 {
                    continue;
                }
                for dx in -1i64..=1 {
                    let xx = x as i64 + dx;
                    if xx < 0 || xx >= w as i64 {
                        continue;
                    }
                    if mask[yy as usize * w + xx as usize] != 0 {
                        v = 1;
                        break 'n;
                    }
                }
            }
            dil[y * w + x] = v;
        }
    }
    let mut out = vec![0u8; w * h];
    for y in 0..h {
        for x in 0..w {
            let mut v = 1u8;
            'e: for dy in -1i64..=1 {
                let yy = y as i64 + dy;
                if yy < 0 || yy >= h as i64 {
                    continue; // border counts as foreground
                }
                for dx in -1i64..=1 {
                    let xx = x as i64 + dx;
                    if xx < 0 || xx >= w as i64 {
                        continue;
                    }
                    if dil[yy as usize * w + xx as usize] == 0 {
                        v = 0;
                        break 'e;
                    }
                }
            }
            out[y * w + x] = v;
        }
    }
    out
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Stat {
    pub left: i64,
    pub top: i64,
    pub width: i64,
    pub height: i64,
    pub area: i64,
}

pub struct Components {
    /// Label per pixel; 0 is background.
    pub labels: Vec<i32>,
    /// `stats[label]`; index 0 describes the background.
    pub stats: Vec<Stat>,
    pub count: usize,
}

fn find(parent: &mut [u32], mut i: u32) -> u32 {
    while parent[i as usize] != i {
        let p = parent[i as usize];
        parent[i as usize] = parent[p as usize];
        i = p;
    }
    i
}

fn union(parent: &mut [u32], a: u32, b: u32) {
    let ra = find(parent, a);
    let rb = find(parent, b);
    if ra != rb {
        let (lo, hi) = if ra < rb { (ra, rb) } else { (rb, ra) };
        parent[hi as usize] = lo;
    }
}

/// `cv2.connectedComponentsWithStats(mask, 8)`.
///
/// OpenCV's Spaghetti labelling scans 2x2 blocks and keeps the minimum
/// provisional label as root, so final labels follow the block-raster order
/// of each component's first block. That order is reproduced here.
pub fn connected_components(mask: &[u8], w: usize, h: usize) -> Components {
    let mut prov = vec![0u32; w * h];
    let mut parent: Vec<u32> = vec![0];
    for y in 0..h {
        for x in 0..w {
            let i = y * w + x;
            if mask[i] == 0 {
                continue;
            }
            let mut neighbors = [0u32; 4];
            let mut n = 0;
            if x > 0 && prov[i - 1] != 0 {
                neighbors[n] = prov[i - 1];
                n += 1;
            }
            if y > 0 {
                let up = i - w;
                if x > 0 && prov[up - 1] != 0 {
                    neighbors[n] = prov[up - 1];
                    n += 1;
                }
                if prov[up] != 0 {
                    neighbors[n] = prov[up];
                    n += 1;
                }
                if x + 1 < w && prov[up + 1] != 0 {
                    neighbors[n] = prov[up + 1];
                    n += 1;
                }
            }
            if n == 0 {
                let l = parent.len() as u32;
                parent.push(l);
                prov[i] = l;
            } else {
                let l = neighbors[..n].iter().copied().min().unwrap();
                prov[i] = l;
                for &m in &neighbors[..n] {
                    union(&mut parent, l, m);
                }
            }
        }
    }
    // Root of every provisional label, and each root's first 2x2 block.
    let roots: Vec<u32> = (0..parent.len() as u32).map(|l| find(&mut parent, l)).collect();
    let bw = w.div_ceil(2);
    let mut first_block = vec![usize::MAX; parent.len()];
    for y in 0..h {
        for x in 0..w {
            let p = prov[y * w + x];
            if p != 0 {
                let r = roots[p as usize] as usize;
                let b = (y / 2) * bw + x / 2;
                if b < first_block[r] {
                    first_block[r] = b;
                }
            }
        }
    }
    let mut ordered: Vec<usize> = (1..parent.len()).filter(|&l| roots[l] as usize == l).collect();
    ordered.sort_by_key(|&r| first_block[r]);
    let mut final_label = vec![0i32; parent.len()];
    for (k, &r) in ordered.iter().enumerate() {
        final_label[r] = k as i32 + 1;
    }
    let count = ordered.len() + 1;
    let mut labels = vec![0i32; w * h];
    let mut minx = vec![i64::MAX; count];
    let mut miny = vec![i64::MAX; count];
    let mut maxx = vec![i64::MIN; count];
    let mut maxy = vec![i64::MIN; count];
    let mut area = vec![0i64; count];
    for y in 0..h {
        for x in 0..w {
            let i = y * w + x;
            let l = if prov[i] == 0 { 0 } else { final_label[roots[prov[i] as usize] as usize] } as usize;
            labels[i] = l as i32;
            area[l] += 1;
            minx[l] = minx[l].min(x as i64);
            miny[l] = miny[l].min(y as i64);
            maxx[l] = maxx[l].max(x as i64);
            maxy[l] = maxy[l].max(y as i64);
        }
    }
    let stats = (0..count)
        .map(|l| {
            if area[l] == 0 {
                Stat { left: 0, top: 0, width: 0, height: 0, area: 0 }
            } else {
                Stat { left: minx[l], top: miny[l], width: maxx[l] - minx[l] + 1, height: maxy[l] - miny[l] + 1, area: area[l] }
            }
        })
        .collect();
    Components { labels, stats, count }
}

const DELTAS: [(i64, i64); 8] = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)];

/// Hole borders of `cv2.findContours(mask, RETR_CCOMP, CHAIN_APPROX_SIMPLE)`.
///
/// A port of OpenCV 5's Suzuki border follower (`contours_new.cpp`). Image
/// marks written while tracing affect later scans, so outer borders are traced
/// too; only the hole contours' compressed points are returned.
pub fn hole_contours(mask: &[u8], w: usize, h: usize) -> Vec<Vec<(i64, i64)>> {
    let pw = w + 2;
    let ph = h + 2;
    let mut img = vec![0i8; pw * ph];
    for y in 0..h {
        for x in 0..w {
            if mask[y * w + x] != 0 {
                img[(y + 1) * pw + x + 1] = 1;
            }
        }
    }
    let at = |x: i64, y: i64| y as usize * pw + x as usize;
    let mut holes = Vec::new();
    let (mut ptx, mut pty) = (1i64, 1i64);
    let mut nbd: i8 = 2;
    let width = pw as i64 - 1;
    let height = ph as i64 - 1;
    loop {
        let mut x = ptx;
        let mut y = pty;
        let mut prev = img[at(x - 1, y)] as i32;
        let mut found = None;
        'rows: while y < height {
            let mut p: i32 = 0;
            while x < width {
                while x < width {
                    p = img[at(x, y)] as i32;
                    if p != prev {
                        break;
                    }
                    x += 1;
                }
                if x >= width {
                    break;
                }
                let is_hole = if prev == 0 && p == 1 {
                    Some(false)
                } else if p != 0 || prev < 1 {
                    None
                } else {
                    Some(true)
                };
                if let Some(is_hole) = is_hole {
                    found = Some((x, y, is_hole));
                    break 'rows;
                }
                prev = p;
                x += 1;
            }
            x = 1;
            prev = 0;
            y += 1;
        }
        let Some((x, y, is_hole)) = found else { break };
        let start = (x - if is_hole { 1 } else { 0 }, y);
        let lval = nbd;
        nbd = ((nbd as i32 + 1) & 0x7f) as i8;
        if nbd == 0 {
            nbd = 3;
        }
        let points = fetch_contour(&mut img, pw, start, lval, is_hole);
        if is_hole {
            holes.push(points);
        }
        ptx = x + 1;
        pty = y;
    }
    holes
}

fn fetch_contour(img: &mut [i8], pw: usize, start: (i64, i64), nbd: i8, is_hole: bool) -> Vec<(i64, i64)> {
    let idx = |x: i64, y: i64| y as usize * pw + x as usize;
    let right_flag = (nbd as u8 | 0x80) as i8;
    let mut points = Vec::new();
    // Contour points are reported in unpadded coordinates (offset -1, -1).
    let (mut ptx, mut pty) = (start.0 - 1, start.1 - 1);
    let i0 = start;
    let s_end0: i64 = if is_hole { 0 } else { 4 };
    let mut s = s_end0;
    let mut i1;
    loop {
        s = (s - 1) & 7;
        i1 = (i0.0 + DELTAS[s as usize].0, i0.1 + DELTAS[s as usize].1);
        if img[idx(i1.0, i1.1)] != 0 || s == s_end0 {
            break;
        }
    }
    if s == s_end0 {
        img[idx(i0.0, i0.1)] = right_flag;
        points.push((ptx, pty));
        return points;
    }
    let mut i3 = i0;
    let mut prev_s = s ^ 4;
    loop {
        let s_end = s;
        s = s.min(15);
        let mut i4 = i3;
        while s < 15 {
            s += 1;
            let d = DELTAS[(s % 8) as usize];
            i4 = (i3.0 + d.0, i3.1 + d.1);
            if img[idx(i4.0, i4.1)] != 0 {
                break;
            }
        }
        s &= 7;
        if s >= 1 && s - 1 < s_end {
            img[idx(i3.0, i3.1)] = right_flag;
        } else if img[idx(i3.0, i3.1)] == 1 {
            img[idx(i3.0, i3.1)] = nbd;
        }
        if s != prev_s {
            points.push((ptx, pty));
        }
        prev_s = s;
        ptx += DELTAS[s as usize].0;
        pty += DELTAS[s as usize].1;
        if i4 == i0 && i3 == i1 {
            break;
        }
        i3 = i4;
        s = (s + 4) & 7;
    }
    points
}

/// `cv2.boundingRect(points)` as (x, y, w, h).
pub fn bounding_rect(points: &[(i64, i64)]) -> (i64, i64, i64, i64) {
    let minx = points.iter().map(|p| p.0).min().unwrap_or(0);
    let maxx = points.iter().map(|p| p.0).max().unwrap_or(-1);
    let miny = points.iter().map(|p| p.1).min().unwrap_or(0);
    let maxy = points.iter().map(|p| p.1).max().unwrap_or(-1);
    (minx, miny, maxx - minx + 1, maxy - miny + 1)
}

/// `cv2.contourArea(points)` (unoriented shoelace area).
pub fn contour_area(points: &[(i64, i64)]) -> f64 {
    if points.is_empty() {
        return 0.0;
    }
    let mut a = 0.0f64;
    let mut prev = points[points.len() - 1];
    for &p in points {
        a += prev.0 as f32 as f64 * p.1 as f32 as f64 - prev.1 as f32 as f64 * p.0 as f32 as f64;
        prev = p;
    }
    (a * 0.5).abs()
}

/// `np.quantile(values, q)` with the default linear method.
pub fn quantile_linear(values: &mut [u8], q: f64) -> f64 {
    values.sort_unstable();
    let n = values.len();
    let virtual_index = (n as f64 - 1.0) * q;
    let (prev, next) = if virtual_index >= n as f64 - 1.0 {
        (n - 1, n - 1)
    } else if virtual_index < 0.0 {
        (0, 0)
    } else {
        let p = virtual_index.floor() as usize;
        (p, p + 1)
    };
    let gamma = virtual_index - virtual_index.floor().max(0.0).min(n as f64 - 1.0);
    let gamma = if virtual_index >= n as f64 - 1.0 { virtual_index - (n as f64 - 1.0) } else { gamma };
    let a = values[prev] as f64;
    let b = values[next] as f64;
    let diff = b - a;
    if gamma >= 0.5 { b - diff * (1.0 - gamma) } else { a + diff * gamma }
}

/// Python `round()` (round half to even) for a float.
pub fn py_round(v: f64) -> i64 {
    v.round_ties_even() as i64
}
