// EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)
use crate::radgui::*;
use std::io::Write;
use std::sync::atomic::{AtomicI32, Ordering};

static CLOSING: AtomicI32 = AtomicI32::new(0);

fn evlog(name: &str, rest: &str) {
    if let Ok(p) = std::env::var("RADEVT_LOG") {
        if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(p) {
            let _ = writeln!(f, "EVT {}{}{}", name, if rest.is_empty() { "" } else { " " }, rest);
        }
    }
}

pub fn Form1_Load() {
    evlog("Form1_Load", "");
}

pub fn Form1_Activated() {
    evlog("Form1_Activated", "");
}

pub fn Form1_FormClosed() {
    evlog("Form1_FormClosed", "");
}

pub fn cmdA_MouseDown() {
    evlog("cmdA_MouseDown", &event_args());
}

pub fn cmdA_MouseUp() {
    evlog("cmdA_MouseUp", &event_args());
}

pub fn cmdA_Click() {
    evlog("cmdA_Click", "");
}

pub fn lblA_MouseDown() {
    evlog("lblA_MouseDown", &event_args());
}

pub fn lblA_MouseUp() {
    evlog("lblA_MouseUp", &event_args());
}

pub fn lblA_Click() {
    evlog("lblA_Click", "");
}

pub fn txtA_GotFocus() {
    evlog("txtA_GotFocus", "");
}

pub fn txtA_LostFocus() {
    evlog("txtA_LostFocus", "");
}

pub fn txtA_KeyDown() {
    evlog("txtA_KeyDown", &event_args());
}

pub fn txtA_KeyPress() {
    evlog("txtA_KeyPress", &event_args());
}

pub fn txtA_KeyUp() {
    evlog("txtA_KeyUp", &event_args());
}

pub fn txtA_TextChanged() {
    evlog("txtA_TextChanged", &format!("text={}", get("txtA", "Text")));
}

pub fn txtB_GotFocus() {
    evlog("txtB_GotFocus", "");
}

pub fn txtB_LostFocus() {
    evlog("txtB_LostFocus", "");
}

pub fn chkA_CheckedChanged() {
    evlog("chkA_CheckedChanged", &format!("value={}", get("chkA", "Value")));
}

pub fn lstA_SelectedIndexChanged() {
    evlog("lstA_SelectedIndexChanged", &format!("index={}", get("lstA", "ListIndex")));
}

pub fn Form1_FormClosing() {
    let n = CLOSING.fetch_add(1, Ordering::SeqCst) + 1;
    evlog("Form1_FormClosing", "");
    if n == 1 { set("Form1", "Cancel", "True"); }
}

pub fn cmdCode_Click() {
    evlog("cmdCode_Click", "begin");
    set("txtA", "Text", "code");
    set("chkA", "Value", 1);
    set("lstA", "ListIndex", 2);
    evlog("cmdCode_Click", "end");
}

pub fn cmdTmr_Click() {
    evlog("cmdTmr_Click", "");
    set("tmrA", "Enabled", "True");
}

pub fn tmrA_Tick() {
    set("tmrA", "Enabled", "False");
    evlog("tmrA_Tick", "");
}
