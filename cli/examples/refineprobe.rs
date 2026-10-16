// Differential probe for refine.rs; see tests/differential/refine_cases.py.
use comic_panel::json::{self, Value};
use comic_panel::{image, obj, refine};

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let pages = std::path::Path::new(&a[1]);
    let cases = json::loads(&std::fs::read_to_string(&a[2]).unwrap()).unwrap();
    let mut last: Option<(i64, image::Rgb)> = None;
    for case in cases.as_array().unwrap() {
        let page = case.opt("page").as_int().unwrap();
        if last.as_ref().map(|l| l.0) != Some(page) {
            last = Some((page, image::load_rgb(&pages.join(format!("{page:04}.jpg"))).unwrap()));
        }
        let rgb = &last.as_ref().unwrap().1;
        let boxes: Vec<[i64; 4]> = case.opt("boxes").as_array().unwrap().iter().map(|b| comic_panel::geometry::box4(b).unwrap()).collect();
        let mut out = obj! {"page" => page, "variant" => case.opt("variant").clone()};
        type F = fn(&image::Rgb, &[[i64; 4]]) -> (Vec<[i64; 4]>, Vec<Value>);
        let fns: [(&str, F); 5] = [
            ("gutter", refine::expand_dark_gutter_boxes),
            ("balloon", refine::expand_balloon_boxes),
            ("frame", refine::expand_frame_boxes),
            ("fringe", refine::expand_dark_fringe_boxes),
            ("component", refine::expand_component_boxes),
        ];
        for (name, f) in fns {
            let (result, changes) = f(rgb, &boxes);
            out.set(name, obj! {"boxes" => Value::Array(result.iter().map(|b| Value::from(b.to_vec())).collect()), "changes" => Value::Array(changes)});
        }
        let (w, h) = (rgb.width as i64, rgb.height as i64);
        let valid: Vec<[i64; 4]> =
            boxes.iter().copied().filter(|b| 0 <= b[0] && b[0] < b[2] && b[2] <= w && 0 <= b[1] && b[1] < b[3] && b[3] <= h).collect();
        out.set("uncovered", refine::uncovered_content_risk(rgb, &valid).unwrap());
        println!("{}", json::dumps(&out));
    }
}
