#[allow(unused_imports)]
use crate::radgui::*;
use crate::PyLib;
pub fn test() -> String {
    format!("{}|{}", PyLib::Add(2, 3).as_f64(), PyLib::Greet("Rust").as_str())
}
