// Module L_rust_bridge - use it from forms as crate::l_rust_bridge::...
// Public functions taking (args: &[Json]) can be called from every language through RAD Hub:
//     Python: radcall("L_rust_bridge.add", 2, 3)      Rust: radcall("L_rust_bridge.add", &[2.into(), 3.into()])
// They may return Json, f64, i64, bool, String, () or Result<_, String>.
use crate::radgui::*;

pub fn add(args: &[Json]) -> f64 {
    args.iter().map(Json::as_f64).sum()
}
// Public functions of L_rust_bridge go here - projects that reference L_rust_bridge can call them.
