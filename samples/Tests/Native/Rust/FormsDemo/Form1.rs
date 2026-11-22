// Event handlers for Form1 - written for the GUI Bridge (radgui.rs); the native build compiles the same
// code against radforms (FFI). Handlers: pub fn <Control>_<Event>().
use crate::radgui::*;
use std::cell::Cell;

thread_local! {
    static TICKS: Cell<u32> = Cell::new(0);
}

pub fn Form1_Load() {
    set("lblOut", "Caption", "ready");
    call("lstLog", "AddItem", &["Form1 loaded"]);
}

pub fn cmdAdd_Click() {
    let a = get_num("txtA", "Text");
    let b = get_num("txtB", "Text");
    set("lblOut", "Caption", a + b);
    // Helpers.rs is a module of this project: a plain Rust call
    let line = format!("{} x {} = {}", a, b, crate::helpers::multiply(a, b));
    call("lstLog", "AddItem", &[&line]);
}

pub fn txtA_TextChanged() {
    set("lblEcho", "Caption", get("txtA", "Text"));
}

pub fn chkBig_CheckedChanged() {
    let on = get_num("chkBig", "Value") == 1.0;
    set("lblOut", "FontSize", if on { 14 } else { 9 });
    set("lblOut", "Caption", if on { "big" } else { "small" });
}

pub fn optTwo_CheckedChanged() {
    set("lblEcho", "Caption", get("optTwo", "Value"));
}

pub fn cboColor_SelectedIndexChanged() {
    set("lblOut", "Caption", get("cboColor", "Text"));
}

pub fn tmrTick_Tick() {
    let t = TICKS.with(|c| { c.set(c.get() + 1); c.get() });
    set("lblTicks", "Caption", t);
    set("prgTicks", "Value", t % 51);
}

pub fn cmdShow2_Click() {
    show("Form2");
}

pub fn mnuForm2_Click() {
    show("Form2");
}

pub fn mnuAbout_Click() {
    msgbox("RAD IDE native Rust demo");
}

pub fn mnuExit_Click() {
    end();
}

pub fn cmdMsg_Click() {
    msgbox("Hello from radforms");
    set("lblOut", "Caption", "msg done");
}

pub fn cmdArabic_Click() {
    set("lblOut", "Caption", "مرحبا بالعالم");
}
