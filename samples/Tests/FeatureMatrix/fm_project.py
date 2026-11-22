"""The FeatureMatrix test form: animations (load / click / after / timer / manual triggers, slide, shake, move,
bounce, colour, typewriter), visual states (MouseOver automatic state, a custom form state "Alert" switched
from code) and layout variants (a "compact" size < 400 px and a "wide" size >= 700 px).

    write_project(lang_key, dest)    -> dest / project.radproj + Form1.form + Form1.<ext> (user code)

The same form is published for every output target by check_feature_matrix.py and driven on the running
program's own window (Win32 messages, PrintWindow pixels) - see docs/features/FEATURE_MATRIX.md."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if not __import__("os").environ.get("RADIDE_FM_NO_REPO"):        # (the frozen IDE check uses its own radide)
    sys.path.insert(0, str(REPO))

from radide import motion  # noqa: E402
from radide.model import Form  # noqa: E402

# FeatureMatrix expectations (logical 96-DPI pixels)
TITLE_LEFT, MOVE_LEFT, MOVE_DX, SHAKE_LEFT, MANUAL_LEFT, MANUAL_DX = 20, 150, 60, 20, 150, 80
BOX = "#3399ff"
BOX_TO = "#ff7a59"
TIMER_FROM, TIMER_TO = "#00aa00", "#aa0000"
TYPED = "typewriter text"
WIDE_SHAKE_LEFT = 400


def build_form(vb: bool = False) -> Form:
    f = Form()
    f.props.update(Name="Form1", Text="Feature matrix", Width=480, Height=320, BackColor="#f4f6fb",
                   StartPosition="CenterScreen", FormBorderStyle="Sizable")
    p = "cmd" if vb else "btn"

    def add(kind, name, x, y, w, h, **props):
        c = f.add(kind, x, y)
        c.props.update(Name=name, Left=x, Top=y, Width=w, Height=h, **props)
        return c
    title = add("Label", "lblTitle", TITLE_LEFT, 14, 300, 28, Text="Feature matrix", FontSize=12,
                BackColor="#ffffff")
    add("Button", p + "Shake", SHAKE_LEFT, 60, 110, 30, Text="Shake")
    add("Button", p + "Move", MOVE_LEFT, 60, 110, 30, Text="Move")
    add("Panel", "pnlBox", 300, 60, 120, 80, BackColor=BOX)
    add("Button", p + "Color", 20, 110, 110, 30, Text="Color")
    add("Label", "lblType", 150, 110, 140, 24, Text=TYPED)
    add("Panel", "pnlTimer", 300, 160, 60, 40, BackColor=TIMER_FROM)
    hover = add("Button", p + "Hover", 20, 160, 110, 30, Text="Hover me")
    add("Button", p + "Alert", 150, 160, 110, 30, Text="Alert")
    add("Button", p + "Manual", 20, 210, 110, 30, Text="Manual")
    add("Label", "lblManual", MANUAL_LEFT, 214, 120, 24, Text="manual", BackColor="#ddeeff")
    # animations (motion presets; expand() makes the keyframes)
    motion.add(f, "lblTitle", "slideIn", id="fx1", durationMs=600, params={"from": "left", "distance": 120})
    motion.add(f, p + "Shake", "shake", id="fx2", durationMs=500, trigger={"on": "click"})
    motion.add(f, p + "Move", "move", id="fx3", durationMs=400, params={"dx": MOVE_DX, "dy": 0},
               trigger={"on": "click"})
    motion.add(f, p + "Move", "bounce", id="fx4", durationMs=500, trigger={"on": "after", "after": "fx3"})
    motion.add(f, "pnlBox", "colorTo", id="fx5", durationMs=600, params={"prop": "BackColor", "color": BOX_TO},
               trigger={"on": "click", "source": p + "Color"})
    motion.add(f, "lblType", "typewriter", id="fx6", durationMs=900, trigger={"on": "after", "after": "fx1"})
    motion.add(f, "pnlTimer", "colorTo", id="fx7", durationMs=400, autoreverse=True,
               params={"prop": "BackColor", "color": TIMER_TO}, trigger={"on": "timer", "intervalMs": 1500})
    motion.add(f, "lblManual", "move", id="fx8", durationMs=400, params={"dx": MANUAL_DX, "dy": 0},
               trigger={"on": "manual"})
    f.extra["motion"] = {"respectReducedMotion": True}
    # visual states: automatic MouseOver + a custom state switched from code
    hover.states = {"MouseOver": {"Text": "Hovered", "BackColor": "#ffcc00"}}
    title.states = {"Alert": {"Text": "ALERT!"}}
    f.extra["states"] = {"Alert": {"Text": "ALERT", "BackColor": "#ffdddd"}}
    # layout variants
    f.extra["variants"] = {"sizes": [
        {"id": "compact", "label": "Small", "when": {"maxWidth": 399}, "preview": {"width": 380, "height": 320}},
        {"id": "wide", "label": "Wide", "when": {"minWidth": 700}, "preview": {"width": 760, "height": 320}}]}
    f.find("pnlBox").variants = {"compact": {"Visible": False}}
    title.variants = {"compact": {"Text": "Small"}}
    f.find(p + "Shake").variants = {"wide": {"Left": WIDE_SHAKE_LEFT}}
    return f


# user code per language: Alert -> GoToState("Alert"), Manual -> BeginAnimation("fx8")
USER = {
    "c": ("c-bridge", "Form1.c", '''/* FeatureMatrix: visual state + manual animation from code (radgui.h API). */
#include "radgui.h"

void btnAlert_Click(void) { rad_call("Form1", "GoToState", "Alert"); }
void btnManual_Click(void) { rad_call("Form1", "BeginAnimation", "fx8"); }
'''),
    "cpp": ("cpp-bridge", "Form1.cpp", '''// FeatureMatrix: visual state + manual animation from code (radgui.hpp API).
#include "radgui.hpp"

void btnAlert_Click() { rad::call("Form1", "GoToState", "Alert"); }
void btnManual_Click() { rad::call("Form1", "BeginAnimation", "fx8"); }
'''),
    "fortran": ("fortran-bridge", "Form1.f90", '''! FeatureMatrix: visual state + manual animation from code (radgui module).
module form1_code
  use radgui
  implicit none
contains
  subroutine btnAlert_Click()
    call rad_call('Form1', 'GoToState', 'Alert')
  end subroutine btnAlert_Click

  subroutine btnManual_Click()
    call rad_call('Form1', 'BeginAnimation', 'fx8')
  end subroutine btnManual_Click
end module form1_code
'''),
    "rust": ("rust-bridge", "Form1.rs", '''// FeatureMatrix: visual state + manual animation from code (radgui.rs API).
use crate::radgui::*;

pub fn btnAlert_Click() {
    call("Form1", "GoToState", &["Alert"]);
}

pub fn btnManual_Click() {
    call("Form1", "BeginAnimation", &["fx8"]);
}
'''),
    "go": ("go-bridge", "Form1.go", '''// FeatureMatrix: visual state + manual animation from code (radlib.go API).
package main

func btnAlert_Click() {
	Call("Form1", "GoToState", "Alert")
}

func btnManual_Click() {
	Call("Form1", "BeginAnimation", "fx8")
}
'''),
    "lua": ("lua-bridge", "Form1.lua", '''-- FeatureMatrix: visual state + manual animation from code (rad.lua API).
function btnAlert_Click(e)
  rad.call("Form1", "GoToState", "Alert")
end

function btnManual_Click(e)
  rad.call("Form1", "BeginAnimation", "fx8")
end
'''),
    "js": ("javascript", "Form1.js", '''// FeatureMatrix: visual state + manual animation from code (radgui.js API).
function btnAlert_Click(e) {
    call('Form1', 'GoToState', 'Alert');
}

function btnManual_Click(e) {
    call('Form1', 'BeginAnimation', 'fx8');
}
'''),
}
# files a language's project needs besides the form and the user code (copied from samples/Tests/Native/*)
SCAFFOLD = {"go": ("Native/Go/FormsDemo", ("go.mod",)),
            "lua": ("Native/Lua/FormsDemo", ("rad.lua", "radworker.lua", "_radmain.lua")),
            }


def write_project(key: str, dest: Path) -> Path:
    lang, fname, code = USER[key]
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    build_form().save(dest / "Form1.form")
    (dest / fname).write_text(code, encoding="utf-8")
    (dest / "project.radproj").write_text(json.dumps({"name": "FeatureMatrix", "language": lang, "forms": ["Form1"],
                                                      "startup": "Form1"}, indent=2), encoding="utf-8")
    src, files = SCAFFOLD.get(key, ("", ()))
    for n in files:
        p = HERE.parent / src / n
        if p.is_file():
            shutil.copy2(p, dest / n)
    return dest


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "projects"
    for k in USER:
        print(write_project(k, out / k))
