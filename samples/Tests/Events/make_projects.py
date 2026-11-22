"""Writes the EventsDemo project of every desktop language for the event semantics matrix (test_events.py).

    .venv\\Scripts\\python samples\\Tests\\Events\\make_projects.py

Every project has the same form (Form1: cmdA, lblA, txtA, txtB, chkA, lstA, cmdCode, cmdTmr, tmrA) and handlers
that only LOG the event and its arguments, one line per event, to the file named by the environment variable
RADEVT_LOG (VB6: Debug.Print, which is stdout in the native exe and the Immediate output in vbrun):

    EVT <Owner>_<Event> [args]

args = the raw GUI Bridge argument text ("X Y Button KeyCode KeyChar") for mouse / key events, "text=..." /
"value=..." / "index=..." for change events (read back through the language's own API), VB6: its own
arguments (Button Shift X Y, KeyCode Shift, KeyAscii, UnloadMode ...).
Special handlers (same in every language): cmdCode_Click changes txtA.Text, chkA.Value and lstA.ListIndex from
code between "begin" and "end"; cmdTmr_Click enables tmrA, whose first Tick disables it; the first
FormClosing / QueryUnload cancels the close. VB6 only: txtA_KeyPress swallows "x" (KeyAscii = 0) and turns
"b" into "B"; txtB_Validate keeps the focus while txtB.Text = "stay"; cmdDoEv runs DoEvents for 0.8 s with tmrA
on, cmdMsg shows a MsgBox with tmrA on, cmdUnload runs Unload Me between "begin" and "end", cmdErr divides by zero (an unhandled run-time error:
the message box, the rest of the handler is skipped, the program goes on).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from radide.model import Form  # noqa: E402

PROJECTS = HERE / "projects"

# neutral handlers: (owner, event, payload) - payload: "args" raw event args, "text"/"value"/"index" a property,
# "" nothing; the special ones are written per language
LOGGED = [
    ("Form1", "Load", ""), ("Form1", "Activated", ""), ("Form1", "FormClosed", ""),
    ("cmdA", "MouseDown", "args"), ("cmdA", "MouseUp", "args"), ("cmdA", "Click", ""),
    ("lblA", "MouseDown", "args"), ("lblA", "MouseUp", "args"), ("lblA", "Click", ""),
    ("txtA", "GotFocus", ""), ("txtA", "LostFocus", ""),
    ("txtA", "KeyDown", "args"), ("txtA", "KeyPress", "args"), ("txtA", "KeyUp", "args"),
    ("txtA", "TextChanged", "text"),
    ("txtB", "GotFocus", ""), ("txtB", "LostFocus", ""),
    ("chkA", "CheckedChanged", "value"), ("lstA", "SelectedIndexChanged", "index"),
]
PROP = {"text": ("txtA", "Text"), "value": ("chkA", "Value"), "index": ("lstA", "ListIndex")}


def make_form() -> Form:
    f = Form()
    f.props.update(Name="Form1", Text="Events", Width=420, Height=300)

    def ctl(typ, name, x, y, w, h, **props):
        c = f.add(typ, x, y, "")
        c.props["Name"] = name
        if "Width" in c.props:
            c.props["Width"], c.props["Height"] = w, h
        if "Text" in c.props:
            c.props["Text"] = name
        c.props.update(props)
        return c
    ctl("TextBox", "txtA", 10, 50, 150, 22, Text="", TabIndex=0)
    ctl("TextBox", "txtB", 10, 80, 150, 22, Text="", TabIndex=1)
    ctl("Button", "cmdA", 10, 10, 100, 30, Text="A", TabIndex=2)
    ctl("Label", "lblA", 120, 10, 100, 30, Text="label A", TabIndex=3)
    ctl("CheckBox", "chkA", 10, 110, 150, 22, Text="check A", TabIndex=4)
    ctl("ListBox", "lstA", 200, 50, 150, 80, Items="a;b;c", TabIndex=5)
    ctl("Button", "cmdCode", 10, 140, 150, 28, Text="from code", TabIndex=6)
    ctl("Button", "cmdTmr", 10, 175, 150, 28, Text="timer", TabIndex=7)
    ctl("Button", "cmdDoEv", 200, 140, 100, 28, Text="DoEvents", TabIndex=8)        # VB6 handlers only
    ctl("Button", "cmdMsg", 200, 175, 100, 28, Text="MsgBox", TabIndex=9)
    ctl("Button", "cmdUnload", 310, 140, 90, 28, Text="Unload Me", TabIndex=10)
    ctl("Button", "cmdErr", 310, 175, 90, 28, Text="Error", TabIndex=11)
    t = f.add("Timer", 300, 200, "")
    t.props.update(Name="tmrA", Interval=150, Enabled=False)
    return f


def write_project(lang: str, language: str, files: dict[str, str], extra: dict | None = None,
                  modules: list[str] | None = None):
    d = PROJECTS / lang
    d.mkdir(parents=True, exist_ok=True)
    make_form().save(d / "Form1.form")
    for name, text in files.items():
        (d / name).write_text(text.strip("\n") + "\n", encoding="utf-8")
    if language == "java-bridge":       # the IDE writes Form1_designer.java when the form is saved
        from radide.languages import get_plugin
        (d / "Form1_designer.java").write_text(get_plugin(language).generate_designer(make_form(), files["Form1.java"]),
                                               encoding="utf-8")
    proj = {"name": f"Events{lang}", "language": language, "forms": ["Form1"], "startup": "Form1",
            "modules": modules or []}
    proj.update(extra or {})
    (d / "project.radproj").write_text(json.dumps(proj, indent=2), encoding="utf-8")


# ------------------------------------------------------------------ C (radgui.h: bridge + native radforms)
def c_code() -> str:
    L = ["/* EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py) */",
         "#include <stdio.h>", "#include <stdlib.h>", "#include <string.h>", '#include "radgui.h"', "",
         "static int closing = 0;", "",
         "static void evlog(const char *name, const char *rest)", "{",
         '    const char *p = getenv("RADEVT_LOG");', "    FILE *f;", "    if (!p || !*p) return;",
         '    f = fopen(p, "ab");', "    if (!f) return;",
         '    fprintf(f, "EVT %s%s%s\\n", name, rest && *rest ? " " : "", rest ? rest : "");', "    fclose(f);", "}",
         "", "static void evkv(const char *name, const char *k, const char *v)", "{",
         "    char b[600];", '    snprintf(b, sizeof b, "%s=%s", k, v);', "    evlog(name, b);", "}", ""]
    for owner, ev, pay in LOGGED:
        n = f"{owner}_{ev}"
        if pay == "args":
            body = f'evlog("{n}", rad_args);'
        elif pay in PROP:
            o, p = PROP[pay]
            body = f'evkv("{n}", "{pay}", rad_get("{o}", "{p}"));'
        else:
            body = f'evlog("{n}", "");'
        L += [f"void {n}(void)", "{", f"    {body}", "}", ""]
    L += ["void Form1_FormClosing(void)", "{", "    closing++;", '    evlog("Form1_FormClosing", "");',
          '    if (closing == 1) rad_set("Form1", "Cancel", "True");', "}", "",
          "void cmdCode_Click(void)", "{", '    evlog("cmdCode_Click", "begin");', '    rad_set("txtA", "Text", "code");',
          '    rad_set("chkA", "Value", "1");', '    rad_set("lstA", "ListIndex", "2");', '    evlog("cmdCode_Click", "end");',
          "}", "", "void cmdTmr_Click(void)", "{", '    evlog("cmdTmr_Click", "");', '    rad_set("tmrA", "Enabled", "True");',
          "}", "", "void tmrA_Tick(void)", "{", '    rad_set("tmrA", "Enabled", "False");', '    evlog("tmrA_Tick", "");', "}"]
    return "\n".join(L)


# ------------------------------------------------------------------ Rust
def rust_code() -> str:
    L = ["// EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)",
         "use crate::radgui::*;", "use std::io::Write;", "use std::sync::atomic::{AtomicI32, Ordering};", "",
         "static CLOSING: AtomicI32 = AtomicI32::new(0);", "",
         "fn evlog(name: &str, rest: &str) {",
         '    if let Ok(p) = std::env::var("RADEVT_LOG") {',
         "        if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(p) {",
         '            let _ = writeln!(f, "EVT {}{}{}", name, if rest.is_empty() { "" } else { " " }, rest);',
         "        }", "    }", "}", ""]
    for owner, ev, pay in LOGGED:
        n = f"{owner}_{ev}"
        if pay == "args":
            body = f'evlog("{n}", &event_args());'
        elif pay in PROP:
            o, p = PROP[pay]
            body = f'evlog("{n}", &format!("{pay}={{}}", get("{o}", "{p}")));'
        else:
            body = f'evlog("{n}", "");'
        L += [f"pub fn {n}() {{", f"    {body}", "}", ""]
    L += ["pub fn Form1_FormClosing() {", "    let n = CLOSING.fetch_add(1, Ordering::SeqCst) + 1;",
          '    evlog("Form1_FormClosing", "");', '    if n == 1 { set("Form1", "Cancel", "True"); }', "}", "",
          "pub fn cmdCode_Click() {", '    evlog("cmdCode_Click", "begin");', '    set("txtA", "Text", "code");',
          '    set("chkA", "Value", 1);', '    set("lstA", "ListIndex", 2);', '    evlog("cmdCode_Click", "end");', "}", "",
          "pub fn cmdTmr_Click() {", '    evlog("cmdTmr_Click", "");', '    set("tmrA", "Enabled", "True");', "}", "",
          "pub fn tmrA_Tick() {", '    set("tmrA", "Enabled", "False");', '    evlog("tmrA_Tick", "");', "}"]
    return "\n".join(L)


# ------------------------------------------------------------------ Go
def go_code() -> str:
    L = ["// EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)", "package main", "",
         'import (\n\t"fmt"\n\t"os"\n)', "", "var closing = 0", "",
         "func evlog(name, rest string) {", '\tp := os.Getenv("RADEVT_LOG")', '\tif p == "" {', "\t\treturn", "\t}",
         "\tf, err := os.OpenFile(p, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)", "\tif err != nil {", "\t\treturn", "\t}",
         '\tif rest != "" {', '\t\trest = " " + rest', "\t}", '\tfmt.Fprintf(f, "EVT %s%s\\n", name, rest)', "\tf.Close()", "}", ""]
    for owner, ev, pay in LOGGED:
        n = f"{owner}_{ev}"
        if pay == "args":
            body = f'evlog("{n}", e.Args)'
        elif pay in PROP:
            o, p = PROP[pay]
            body = f'evlog("{n}", "{pay}="+Get("{o}", "{p}"))'
        else:
            body = f'evlog("{n}", "")'
        L += [f"func {n}(e RadEvent) {{", f"\t{body}", "}", ""]
    L += ["func Form1_FormClosing(e RadEvent) {", "\tclosing++", '\tevlog("Form1_FormClosing", "")',
          "\tif closing == 1 {", '\t\tSet("Form1", "Cancel", "True")', "\t}", "}", "",
          "func cmdCode_Click(e RadEvent) {", '\tevlog("cmdCode_Click", "begin")', '\tSet("txtA", "Text", "code")',
          '\tSet("chkA", "Value", 1)', '\tSet("lstA", "ListIndex", 2)', '\tevlog("cmdCode_Click", "end")', "}", "",
          "func cmdTmr_Click(e RadEvent) {", '\tevlog("cmdTmr_Click", "")', '\tSet("tmrA", "Enabled", "True")', "}", "",
          "func tmrA_Tick(e RadEvent) {", '\tSet("tmrA", "Enabled", "False")', '\tevlog("tmrA_Tick", "")', "}"]
    return "\n".join(L)


# ------------------------------------------------------------------ Lua
def lua_code() -> str:
    L = ["-- EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)", "local closing = 0", "",
         "local function evlog(name, rest)", '  local p = os.getenv("RADEVT_LOG")', '  if not p or p == "" then return end',
         '  local f = io.open(p, "ab")', "  if not f then return end",
         '  f:write("EVT " .. name .. ((rest and rest ~= "") and (" " .. rest) or "") .. "\\n")', "  f:close()", "end", ""]
    for owner, ev, pay in LOGGED:
        n = f"{owner}_{ev}"
        if pay == "args":
            body = f'evlog("{n}", e and e.args or "")'
        elif pay in PROP:
            o, p = PROP[pay]
            body = f'evlog("{n}", "{pay}=" .. rad.get("{o}", "{p}"))'
        else:
            body = f'evlog("{n}", "")'
        L += [f"function {n}(e)", f"  {body}", "end", ""]
    L += ["function Form1_FormClosing(e)", "  closing = closing + 1", '  evlog("Form1_FormClosing", "")',
          '  if closing == 1 then rad.set("Form1", "Cancel", "True") end', "end", "",
          "function cmdCode_Click(e)", '  evlog("cmdCode_Click", "begin")', '  rad.set("txtA", "Text", "code")',
          '  rad.set("chkA", "Value", 1)', '  rad.set("lstA", "ListIndex", 2)', '  evlog("cmdCode_Click", "end")', "end", "",
          "function cmdTmr_Click(e)", '  evlog("cmdTmr_Click", "")', '  rad.set("tmrA", "Enabled", "True")', "end", "",
          "function tmrA_Tick(e)", '  rad.set("tmrA", "Enabled", "False")', '  evlog("tmrA_Tick", "")', "end"]
    return "\n".join(L)


# ------------------------------------------------------------------ JavaScript
def js_code() -> str:
    L = ["// EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)", "const fs = require('fs');", "",
         "let closing = 0;", "",
         "function evlog(name, rest) {", "    const p = process.env.RADEVT_LOG;", "    if (!p) return;",
         "    fs.appendFileSync(p, `EVT ${name}${rest ? ' ' + rest : ''}\\n`, 'utf8');", "}", ""]
    for owner, ev, pay in LOGGED:
        n = f"{owner}_{ev}"
        if pay == "args":
            body = f"evlog('{n}', e ? e.args : '');"
        elif pay in PROP:
            o, p = PROP[pay]
            body = f"evlog('{n}', '{pay}=' + get('{o}', '{p}'));"
        else:
            body = f"evlog('{n}', '');"
        L += [f"function {n}(e) {{", f"    {body}", "}", ""]
    L += ["function Form1_FormClosing(e) {", "    closing++;", "    evlog('Form1_FormClosing', '');",
          "    if (closing === 1) set('Form1', 'Cancel', 'True');", "}", "",
          "function cmdCode_Click(e) {", "    evlog('cmdCode_Click', 'begin');", "    set('txtA', 'Text', 'code');",
          "    set('chkA', 'Value', 1);", "    set('lstA', 'ListIndex', 2);", "    evlog('cmdCode_Click', 'end');", "}", "",
          "function cmdTmr_Click(e) {", "    evlog('cmdTmr_Click', '');", "    set('tmrA', 'Enabled', 'True');", "}", "",
          "function tmrA_Tick(e) {", "    set('tmrA', 'Enabled', 'False');", "    evlog('tmrA_Tick', '');", "}"]
    return "\n".join(L)


# ------------------------------------------------------------------ C# (bridge client + native WinForms)
def cs_code() -> str:
    L = ["// EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)", "using System;",
         "using System.IO;", "", "public static partial class Form1", "{", "    static int closing;", "",
         "    static void EvLog(string name, string rest)", "    {",
         '        var p = Environment.GetEnvironmentVariable("RADEVT_LOG");', "        if (string.IsNullOrEmpty(p)) return;",
         '        File.AppendAllText(p, "EVT " + name + (string.IsNullOrEmpty(rest) ? "" : " " + rest) + "\\n");', "    }", "",
         "    static string Raw(RadEvent e)", "    {",
         '        if (e == null) return "";', "        if (!string.IsNullOrEmpty(e.Args)) return e.Args;",
         '        return (e.X + " " + e.Y + " " + e.Button + " " + e.KeyCode + " " + e.KeyChar).Trim();', "    }", ""]
    for owner, ev, pay in LOGGED:
        n = f"{owner}_{ev}"
        if pay == "args":
            body = f'EvLog("{n}", Raw(e));'
        elif pay in PROP:
            o, p = PROP[pay]
            body = f'EvLog("{n}", "{pay}=" + Rad.Get("{o}", "{p}"));'
        else:
            body = f'EvLog("{n}", "");'
        L += [f"    static void {n}(RadEvent e)", "    {", f"        {body}", "    }", ""]
    L += ["    static void Form1_FormClosing(RadEvent e)", "    {", "        closing++;", '        EvLog("Form1_FormClosing", "");',
          "        if (closing == 1) e.Cancel = true;", "    }", "",
          "    static void cmdCode_Click(RadEvent e)", "    {", '        EvLog("cmdCode_Click", "begin");',
          '        Rad.Set("txtA", "Text", "code");', '        Rad.Set("chkA", "Value", 1);', '        Rad.Set("lstA", "ListIndex", 2);',
          '        EvLog("cmdCode_Click", "end");', "    }", "",
          "    static void cmdTmr_Click(RadEvent e)", "    {", '        EvLog("cmdTmr_Click", "");', '        Rad.Set("tmrA", "Enabled", true);', "    }", "",
          "    static void tmrA_Tick(RadEvent e)", "    {", '        Rad.Set("tmrA", "Enabled", false);', '        EvLog("tmrA_Tick", "");', "    }", "}"]
    return "\n".join(L)


# ------------------------------------------------------------------ Java (bridge client + native Swing)
def java_code() -> str:
    L = ["// EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)",
         "public class Form1 extends Form1Designer {", "    static int closing;", "",
         "    static void evlog(String name, String rest) {", '        String p = System.getenv("RADEVT_LOG");',
         "        if (p == null || p.isEmpty()) return;",
         "        try (java.io.Writer w = new java.io.OutputStreamWriter(new java.io.FileOutputStream(p, true), "
         "java.nio.charset.StandardCharsets.UTF_8)) {",
         '            w.write("EVT " + name + (rest == null || rest.isEmpty() ? "" : " " + rest) + "\\n");',
         "        } catch (java.io.IOException ex) {", "        }", "    }", "",
         "    static String raw(RadEvent e) {", '        if (e == null) return "";', "        if (!e.args.isEmpty()) return e.args;",
         '        return (e.x + " " + e.y + " " + e.button + " " + e.keyCode + " " + e.keyChar).trim();', "    }", ""]
    for owner, ev, pay in LOGGED:
        n = f"{owner}_{ev}"
        if pay == "args":
            body = f'evlog("{n}", raw(e));'
        elif pay in PROP:
            o, p = PROP[pay]
            body = f'evlog("{n}", "{pay}=" + Rad.get("{o}", "{p}"));'
        else:
            body = f'evlog("{n}", "");'
        L += [f"    static void {n}(RadEvent e) {{", f"        {body}", "    }", ""]
    L += ["    static void Form1_FormClosing(RadEvent e) {", "        closing++;", '        evlog("Form1_FormClosing", "");',
          "        if (closing == 1) e.cancel = true;", "    }", "",
          "    static void cmdCode_Click(RadEvent e) {", '        evlog("cmdCode_Click", "begin");', '        Rad.set("txtA", "Text", "code");',
          '        Rad.set("chkA", "Value", 1);', '        Rad.set("lstA", "ListIndex", 2);', '        evlog("cmdCode_Click", "end");', "    }", "",
          "    static void cmdTmr_Click(RadEvent e) {", '        evlog("cmdTmr_Click", "");', '        Rad.set("tmrA", "Enabled", true);', "    }", "",
          "    static void tmrA_Tick(RadEvent e) {", '        Rad.set("tmrA", "Enabled", false);', '        evlog("tmrA_Tick", "");', "    }", "}"]
    return "\n".join(L)


# ------------------------------------------------------------------ Python (Tkinter)
def py_code() -> str:
    L = ['"""EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py)."""', "import os", "",
         "from Form1_designer import Form1Designer, EventArgs  # noqa: F401", "", "",
         "def evlog(name, rest=\"\"):", '    p = os.environ.get("RADEVT_LOG")', "    if not p:", "        return",
         '    with open(p, "a", encoding="utf-8", newline="\\n") as f:', '        f.write(f"EVT {name}{\' \' + rest if rest else \'\'}\\n")',
         "", "", "def raw(e):", '    return f"{e.X} {e.Y} {e.Button} {e.KeyCode} {e.KeyChar}".strip()', "", "",
         "class Form1(Form1Designer):", "    closing = 0", ""]
    getter = {"text": "self.txtA_var.get()", "value": "int(self.chkA_var.get())",
              "index": "(self.lstA.curselection() or (-1,))[0]"}
    for owner, ev, pay in LOGGED:
        n = f"{owner}_{ev}"
        if pay == "args":
            L += [f"    def {n}(self, e):", f'        evlog("{n}", raw(e))', ""]
        elif pay in PROP:
            L += [f"    def {n}(self, *_):", f'        evlog("{n}", f"{pay}={{{getter[pay]}}}")', ""]
        else:
            L += [f"    def {n}(self, *_):", f'        evlog("{n}")', ""]
    L += ["    def Form1_FormClosing(self, e):", "        Form1.closing += 1", '        evlog("Form1_FormClosing")',
          "        if Form1.closing == 1:", "            e.Cancel = True", "",
          "    def cmdCode_Click(self):", '        evlog("cmdCode_Click", "begin")', '        self.txtA_var.set("code")',
          "        self.chkA_var.set(True)", "        self.lstA.selection_clear(0, \"end\")", "        self.lstA.selection_set(2)",
          '        evlog("cmdCode_Click", "end")', "",
          "    def cmdTmr_Click(self):", '        evlog("cmdTmr_Click")', "        self.tmrA.Enabled = True", "",
          "    def tmrA_Tick(self):", "        self.tmrA.Enabled = False", '        evlog("tmrA_Tick")', "", "",
          'if __name__ == "__main__":', "    Form1().show()"]
    return "\n".join(L)


# ------------------------------------------------------------------ VB6 (vbrun + FreeBASIC native)
VB6 = r'''
Option Explicit
Private closing As Integer

Private Sub EvLog(ByVal s As String)
    Debug.Print "EVT " & s
End Sub

Private Sub Form_Initialize()
    EvLog "Form_Initialize"
End Sub

Private Sub Form_Load()
    EvLog "Form_Load"
End Sub

Private Sub Form_Activate()
    EvLog "Form_Activate"
End Sub

Private Sub Form_QueryUnload(Cancel As Integer, UnloadMode As Integer)
    closing = closing + 1
    EvLog "Form_QueryUnload mode=" & UnloadMode
    If closing = 1 Then Cancel = 1
End Sub

Private Sub Form_Unload(Cancel As Integer)
    EvLog "Form_Unload"
End Sub

Private Sub Form_Terminate()
    EvLog "Form_Terminate"
End Sub

Private Sub cmdA_MouseDown(Button As Integer, Shift As Integer, X As Single, Y As Single)
    EvLog "cmdA_MouseDown " & Button & " " & Shift & " " & X & " " & Y
End Sub

Private Sub cmdA_MouseUp(Button As Integer, Shift As Integer, X As Single, Y As Single)
    EvLog "cmdA_MouseUp " & Button & " " & Shift & " " & X & " " & Y
End Sub

Private Sub cmdA_Click()
    EvLog "cmdA_Click"
End Sub

Private Sub lblA_MouseDown(Button As Integer, Shift As Integer, X As Single, Y As Single)
    EvLog "lblA_MouseDown " & Button & " " & Shift & " " & X & " " & Y
End Sub

Private Sub lblA_MouseUp(Button As Integer, Shift As Integer, X As Single, Y As Single)
    EvLog "lblA_MouseUp " & Button & " " & Shift & " " & X & " " & Y
End Sub

Private Sub lblA_Click()
    EvLog "lblA_Click"
End Sub

Private Sub txtA_GotFocus()
    EvLog "txtA_GotFocus"
End Sub

Private Sub txtA_LostFocus()
    EvLog "txtA_LostFocus"
End Sub

Private Sub txtA_KeyDown(KeyCode As Integer, Shift As Integer)
    EvLog "txtA_KeyDown " & KeyCode & " " & Shift
End Sub

Private Sub txtA_KeyPress(KeyAscii As Integer)
    EvLog "txtA_KeyPress " & KeyAscii
    If KeyAscii = 120 Then KeyAscii = 0
    If KeyAscii = 98 Then KeyAscii = 66
End Sub

Private Sub txtA_KeyUp(KeyCode As Integer, Shift As Integer)
    EvLog "txtA_KeyUp " & KeyCode & " " & Shift
End Sub

Private Sub txtA_Change()
    EvLog "txtA_Change text=" & txtA.Text
End Sub

Private Sub txtB_GotFocus()
    EvLog "txtB_GotFocus"
End Sub

Private Sub txtB_LostFocus()
    EvLog "txtB_LostFocus"
End Sub

Private Sub txtB_Validate(Cancel As Boolean)
    EvLog "txtB_Validate text=" & txtB.Text
    If txtB.Text = "stay" Then Cancel = True
End Sub

Private Sub chkA_Click()
    EvLog "chkA_Click value=" & chkA.Value
End Sub

Private Sub lstA_Click()
    EvLog "lstA_Click index=" & lstA.ListIndex
End Sub

Private Sub cmdCode_Click()
    EvLog "cmdCode_Click begin"
    txtA.Text = "code"
    chkA.Value = 1
    lstA.ListIndex = 2
    EvLog "cmdCode_Click end"
End Sub

Private Sub cmdTmr_Click()
    EvLog "cmdTmr_Click"
    tmrA.Enabled = True
End Sub

Private Sub tmrA_Timer()
    tmrA.Enabled = False
    EvLog "tmrA_Timer"
End Sub

Private Sub cmdDoEv_Click()
    Dim t As Single
    EvLog "cmdDoEv_Click begin"
    tmrA.Enabled = True
    t = Timer
    Do While Timer - t < 0.8
        DoEvents
    Loop
    EvLog "cmdDoEv_Click end"
End Sub

Private Sub cmdMsg_Click()
    EvLog "cmdMsg_Click begin"
    tmrA.Enabled = True
    MsgBox "modal"
    EvLog "cmdMsg_Click end"
End Sub

Private Sub cmdErr_Click()
    Dim d As Integer
    EvLog "cmdErr_Click begin"
    d = 0
    d = 10 / d
    EvLog "cmdErr_Click end"
End Sub

Private Sub cmdUnload_Click()
    EvLog "cmdUnload_Click begin"
    Unload Me
    EvLog "cmdUnload_Click end"
End Sub
'''


def main():
    write_project("VB6", "vb-basic", {"Form1.bas": VB6})
    write_project("Python", "python-tk", {"Form1.py": py_code()})
    write_project("C", "c-bridge", {"Form1.c": c_code()})
    write_project("CSharp", "csharp-bridge", {"Form1.cs": cs_code()})
    write_project("Java", "java-bridge", {"Form1.java": java_code()})
    write_project("Rust", "rust-bridge", {"Form1.rs": rust_code()})
    write_project("Go", "go-bridge", {"Form1.go": go_code(), "go.mod": "module eventsdemo\n\ngo 1.21\n"})
    write_project("Lua", "lua-bridge", {"Form1.lua": lua_code()})
    write_project("JS", "javascript", {"Form1.js": js_code()})
    print("projects written to", PROJECTS)


if __name__ == "__main__":
    main()
