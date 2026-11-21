"""(Re)build the animation samples of the non-Python targets (plan MOTION_VARIANTS_FOLDABLES slice D).

    python samples/Tests/Motion/Targets/make_targets.py

Motion_Ring      ring-qt desktop form: all kinds of triggers (load, click, hover, timer, after, show / hide)
Motion_Flutter   classic Flutter mobile form (lib/radmotion.dart + F's radfx.dart RadKey)
Motion_Kivy      Kivy mobile form (kivy.animation.Animation, canvas Translate / Rotate / Scale)
Motion_Expo      React Native (Expo) mobile form (Animated, useNativeDriver)
Each form uses the 15 presets of radide/motion/presets.py; user code files are kept when they exist."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from proj import ROOT, add, mobile_form, write_project  # noqa: E402

sys.path.insert(0, str(ROOT))
from radide import motion  # noqa: E402
from radide.model import Form  # noqa: E402


def desktop_form() -> Form:
    f = Form()
    f.props.update(Name="Form1", Text="Motion presets (Ring)", Width=460, Height=300, BackColor="#f4f6fb")
    add(f, "Label", "lblTitle", 20, 14, 300, 28, Text="Hello, motion!", FontSize=14, FontBold=True)
    add(f, "Button", "btnShake", 20, 60, 110, 30, Text="Shake me")
    add(f, "Button", "btnPulse", 150, 60, 110, 30, Text="Hover me")
    add(f, "Button", "btnMove", 20, 110, 110, 30, Text="Move + bounce")
    add(f, "Button", "btnSpin", 150, 110, 110, 30, Text="Rotate")
    add(f, "Button", "btnHide", 20, 160, 110, 30, Text="Hide / show")
    add(f, "Label", "lblInfo", 150, 164, 260, 24, Text="I fade out and in", BackColor="#ffe08a")
    add(f, "Panel", "pnlBox", 300, 60, 120, 80, BackColor="#3399ff")
    add(f, "Button", "btnFlip", 300, 160, 120, 30, Text="Flip / zoom")
    _animations(f, "btnShake", "btnPulse", "btnMove", "btnSpin", "lblInfo", "pnlBox", "btnFlip")
    return f


def phone_form(name: str = "Form1") -> Form:
    f = mobile_form(name)
    add(f, "Label", "lblTitle", 16, 16, 300, 36, Text="Hello, motion!", FontSize=20, FontBold=True)
    add(f, "Button", "btnShake", 16, 72, 150, 44, Text="Shake me")
    add(f, "Button", "btnPulse", 182, 72, 150, 44, Text="Hover me")
    add(f, "Button", "btnMove", 16, 132, 150, 44, Text="Move + bounce")
    add(f, "Button", "btnSpin", 182, 132, 150, 44, Text="Rotate")
    add(f, "Button", "btnHide", 16, 192, 150, 44, Text="Hide / show")
    add(f, "Label", "lblInfo", 182, 196, 180, 36, Text="I fade out and in", BackColor="#ffe08a")
    add(f, "Card", "pnlBox", 16, 260, 150, 100, BackColor="#3399ff")
    add(f, "Button", "btnFlip", 182, 260, 150, 44, Text="Flip / zoom")
    _animations(f, "btnShake", "btnPulse", "btnMove", "btnSpin", "lblInfo", "pnlBox", "btnFlip")
    return f


def _animations(f, shake, pulse, move, spin, info, box, flip):
    motion.add(f, "lblTitle", "slideIn", id="fx1", durationMs=600, params={"from": "left", "distance": 120})
    motion.add(f, "lblTitle", "typewriter", id="fx2", durationMs=900)
    motion.add(f, shake, "shake", id="fx3", trigger={"on": "click"})
    motion.add(f, pulse, "zoom", id="fx4", durationMs=250, params={"scale": 1.15},
               trigger={"on": "hover", "leave": "reverse"})
    motion.add(f, move, "move", id="fx5", durationMs=400, params={"dx": 60, "dy": 0}, trigger={"on": "click"})
    motion.add(f, move, "bounce", id="fx6", durationMs=500, trigger={"on": "after", "after": "fx5"})
    motion.add(f, spin, "rotate", id="fx7", trigger={"on": "click"})
    motion.add(f, info, "fadeOut", id="fx8", trigger={"on": "hide"})
    motion.add(f, info, "fadeIn", id="fx9", trigger={"on": "show"})
    motion.add(f, box, "colorTo", id="fx10", durationMs=700, autoreverse=True,
               params={"prop": "BackColor", "color": "#ff7a59"}, trigger={"on": "timer", "intervalMs": 2500})
    motion.add(f, flip, "flip", id="fx11", trigger={"on": "click"})
    motion.add(f, flip, "pulse", id="fx12", trigger={"on": "after", "after": "fx11"})
    motion.add(f, "btnHide", "scaleIn", id="fx13", delayMs=300)
    motion.add(f, "btnHide", "slideOut", id="fx14", trigger={"on": "manual"})
    motion.add(f, box, "scaleOut", id="fx15", trigger={"on": "manual"})
    motion.add(f, box, "fadeIn", id="fx16", trigger={"on": "manual"})
    f.extra["motion"] = {"respectReducedMotion": True}


RING_USER = '''load "Form1_designer.ring"

# Animations are designed in the Animations window (form.extra["animations"]); the runtime is _radfx.ring.
# Form1_BeginAnimation("fx1") / Form1_StopAnimation("fx1") / Form1_SetVisible("lblInfo", false)

lHidden = false

func Form1_Load
    # runs after the form is created

func btnHide_Click
    lHidden = not lHidden
    Form1_SetVisible("lblInfo", not lHidden)
'''

FLUTTER_USER = """// Form1 screen - animations come from the Animations window (lib/radmotion.dart plays them).
// BeginAnimation('fx1') / StopAnimation('fx1') / SetVisible('lblInfo', false)
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'form1_designer.dart';

class Form1Code extends Form1Designer {
  bool _hidden = false;

  void btnHide_Click() {
    _hidden = !_hidden;
    SetVisible('lblInfo', !_hidden);
  }
}
"""

KIVY_USER = '''# Form1 screen - animations come from the Animations window (radkivyfx.py plays them).
# self.BeginAnimation("fx1") / self.StopAnimation("fx1") / self.SetVisible("lblInfo", False)
from Form1_designer import Form1Designer, RadEvent, run_app  # noqa: F401


class Form1(Form1Designer):
    _hidden = False

    def btnHide_Click(self):
        self._hidden = not self._hidden
        self.SetVisible("lblInfo", not self._hidden)


if __name__ == "__main__":
    run_app("Form1")
'''

EXPO_USER = """// Form1 - animations come from the Animations window (radapp.js RadFx plays them).
// this.BeginAnimation('fx1') / this.StopAnimation('fx1') / this.SetVisible('lblInfo', false)
import { Form1Designer } from './Form1_designer';
import { RadApp } from './radapp';

export default class Form1 extends Form1Designer {
  btnHide_Click(e) {
    this._hidden = !this._hidden;
    this.SetVisible('lblInfo', !this._hidden);
  }
}
"""


def build(overwrite_user: bool = False) -> dict:
    out = {}
    out["ring"] = write_project(HERE / "Motion_Ring", "ring-qt", [desktop_form()], {"Form1": RING_USER},
                                overwrite_user)
    out["flutter"] = write_project(HERE / "Motion_Flutter", "flutter", [phone_form()], {"Form1": FLUTTER_USER},
                                   overwrite_user)
    out["kivy"] = write_project(HERE / "Motion_Kivy", "kivy", [phone_form()], {"Form1": KIVY_USER}, overwrite_user)
    out["expo"] = write_project(HERE / "Motion_Expo", "expo", [phone_form()], {"Form1": EXPO_USER}, overwrite_user)
    return out


if __name__ == "__main__":
    build("--overwrite" in sys.argv)
    print("Motion target samples written in", HERE)
