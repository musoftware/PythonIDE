"""(Re)build the layout-size (variants) and TwoPane samples of the non-Python targets (plan
MOTION_VARIANTS_FOLDABLES slice D).

    python samples/Tests/Variants/Targets/make_targets.py

Variants_Ring     ring-qt desktop form: "Small" (< 500 wide) moves / renames a button, hides a label, retitles
Variants_Flutter  classic Flutter mobile form: Phone / Tablet / Half-open sizes + a TwoPane (RadTwoPane)
Variants_Kivy     the same mobile form for Kivy (KV positions follow root.radsizes, RadTwoPane)
Variants_Expo     the same mobile form for React Native (placeV / useSizes, TwoPane of radfx.js)
User code files are kept when they exist."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "Motion" / "Targets"))

from proj import ROOT, add, mobile_form, write_project  # noqa: E402

sys.path.insert(0, str(ROOT))
from radide.model import Form  # noqa: E402
from radide.variants import model as vm  # noqa: E402


def desktop_form() -> Form:
    f = Form()
    f.props.update(Name="Form1", Text="Sizes (Ring)", Width=640, Height=400)
    b = add(f, "Button", "btnGo", 400, 20, 200, 30, Text="Go", Anchor="Top, Right")
    lbl = add(f, "Label", "lblSide", 20, 20, 200, 24, Text="Side panel")
    add(f, "Panel", "pnlMain", 20, 80, 600, 300, Anchor="Top, Bottom, Left, Right", BackColor="#e8eefc")
    vm.add_size(f, {"id": "small", "label": "Small", "when": {"maxWidth": 499}, "preview": {"width": 420, "height": 400}})
    for k, v in (("Left", 20), ("Top", 340), ("Width", 380)):
        vm.set_override(f, b, "small", k, v)
    vm.set_override(f, b, "small", "Text", "Go (small)")
    vm.set_override(f, lbl, "small", "Visible", False)
    vm.set_override(f, None, "small", "Text", "Sizes (Ring) - small")
    return f


def phone_form(name: str = "Form1") -> Form:
    f = mobile_form(name)                        # pixel portrait: 412 x 867
    add(f, "Label", "lblTitle", 16, 16, 380, 36, Text="Responsive", FontSize=20, FontBold=True)
    b = add(f, "Button", "btnGo", 16, 64, 380, 44, Text="Go")
    side = add(f, "Label", "lblSide", 16, 120, 380, 30, Text="Only on phones")
    tp = add(f, "TwoPane", "TwoPane1", 16, 160, 380, 400, PaneMode="Auto", Ratio=0.4, SinglePane="Start",
             HingeAware=True)
    add(f, "Column", "colList", 0, 0, 380, 400, parent=tp.name, BackColor="#e3f2fd")
    add(f, "Column", "colDetail", 0, 0, 380, 400, parent=tp.name, BackColor="#fff3e0")
    add(f, "Label", "lblList", 0, 0, 200, 30, parent="colList", Text="List")
    add(f, "Label", "lblDetail", 0, 0, 200, 30, parent="colDetail", Text="Detail")
    for s in ({"id": "phone", "label": "Phone", "when": {"maxWidth": 599}, "preview": {"width": 412, "height": 867}},
              {"id": "tablet", "label": "Tablet", "when": {"minWidth": 600}, "preview": {"width": 900, "height": 700}},
              {"id": "tabletop", "label": "Half-open", "when": {"posture": "half-opened"},
               "preview": {"device": "galaxy_z_fold6", "orientation": "Landscape", "posture": "HalfOpened"}}):
        vm.add_size(f, s)
    for k, v in (("Left", 500), ("Top", 16), ("Width", 380)):
        vm.set_override(f, b, "tablet", k, v)
    vm.set_override(f, b, "tablet", "Text", "Go (tablet)")
    vm.set_override(f, side, "tablet", "Visible", False)
    vm.set_override(f, b, "tabletop", "Text", "Go (half-open)")
    return f


FLUTTER_USER = """// Form1 screen - the layout sizes come from the Sizes bar (RadVariant of lib/radlayout.dart).
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'form1_designer.dart';

class Form1Code extends Form1Designer {
  void Form1_Load() {
    // CurrentSizes = the layout sizes that apply now
  }

  void btnGo_Click() {
    lblTitle.text = 'Sizes: ${CurrentSizes.join(', ')}';
  }
}
"""


def build(overwrite_user: bool = False) -> dict:
    out = {}
    out["ring"] = write_project(HERE / "Variants_Ring", "ring-qt", [desktop_form()], None, overwrite_user)
    out["flutter"] = write_project(HERE / "Variants_Flutter", "flutter", [phone_form()], {"Form1": FLUTTER_USER},
                                   overwrite_user)
    out["kivy"] = write_project(HERE / "Variants_Kivy", "kivy", [phone_form()], None, overwrite_user)
    out["expo"] = write_project(HERE / "Variants_Expo", "expo", [phone_form()], None, overwrite_user)
    return out


if __name__ == "__main__":
    build("--overwrite" in sys.argv)
    print("Variant target samples written in", HERE)
