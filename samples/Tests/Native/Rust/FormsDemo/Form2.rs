// Event handlers for Form2.
use crate::radgui::*;

pub fn Form2_Load() {
    set("txt2", "Text", "from Form2 Load");
}

pub fn cmdClose2_Click() {
    set("Form1.lblOut", "Caption", get("txt2", "Text"));
    hide("Form2");
}
