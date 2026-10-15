// Differential probe: crop -> LANCZOS resize -> red outline -> JPEG q95.
use comic_panel::image::*;
fn main() {
    let a: Vec<String> = std::env::args().collect();
    let n = |i: usize| a[i].parse::<i64>().unwrap();
    let src = decode_jpeg(&std::fs::read(&a[1]).unwrap()).unwrap();
    let c = src.crop(n(2), n(3), n(4), n(5));
    let r = resize_lanczos(&c, n(6) as usize, n(7) as usize);
    let mut m = r.clone();
    draw_rectangle_outline(&mut m, n(8), n(9), n(10), n(11), [255, 0, 0], 2);
    std::fs::write(&a[12], encode_jpeg(&r, 95).unwrap()).unwrap();
    std::fs::write(&a[13], encode_jpeg(&m, 95).unwrap()).unwrap();
}
