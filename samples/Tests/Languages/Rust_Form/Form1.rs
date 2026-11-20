// Event handlers for Form1 (debugger test)
use crate::radgui::*;

pub fn Form1_Load() {
}

pub fn cmdAdd_Click() {
    let a = get_num("txtA", "Text");
    let b = get_num("txtB", "Text");
    let total = (a + b) as i32;
    set("lblOut", "Caption", total);
}
