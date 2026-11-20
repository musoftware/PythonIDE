// Class library RustLib.
// Every `pub fn` below is public: projects that reference RustLib call it as code of their
// own language (Python: RustLib.add(2, 3), Rust: RustLib::add(2, 3), ...).
// Results may be numbers, bool, String, Json, Vec<..>, Option<..>, () or Result<_, String>.
#[allow(unused_imports)]
use crate::radgui::*;

/// Add two numbers. Public functions (pub fn) with number, bool, String/&str, Json or Vec
/// parameters can be called by every project that references this one.
pub fn add(a: f64, b: f64) -> f64 {
    a + b
}
