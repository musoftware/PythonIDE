
use crate::radgui::*;
use crate::PyLib;

pub fn run(who: String) -> String {
    let h = PyLib::Hello(who.as_str()).as_str();
    let m = PyLib::Mul(6, 7).as_f64();
    let e = match PyLib::try_Mul("a", Json::Arr(vec![])) { Ok(_) => "no error".to_string(), Err(e) => e };
    format!("{} | {} | {}", h, m, e)
}
