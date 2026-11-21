"""(Re)build the Motion sample projects: one form with animation presets for python-tk, python-qt and vb-basic.

    python samples/Tests/Motion/make_samples.py

Writes Form1.form (+ the generated Form1_designer.py for the Python ones) into Motion_Tk_Presets,
Motion_Qt_Presets and Motion_VB6. The user code files (Form1.py / Form1.bas) are kept when they exist."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from radide import motion  # noqa: E402
from radide.languages import get_plugin  # noqa: E402
from radide.model import Form  # noqa: E402


def build_form(vb: bool = False) -> Form:
    f = Form()
    f.props.update(Name="Form1", Text="Motion presets", Width=460, Height=300, BackColor="#f4f6fb")

    def add(kind, name, x, y, w, h, **props):
        c = f.add(kind, x, y)
        c.props.update(Name=name, Left=x, Top=y, Width=w, Height=h, **props)
        return c
    add("Label", "lblTitle", 20, 14, 300, 28, Text="Hello, motion!", FontSize=14, FontBold=True)
    shake = "cmdShake" if vb else "btnShake"
    move = "cmdMove" if vb else "btnMove"
    hide = "cmdHide" if vb else "btnHide"
    add("Button", shake, 20, 60, 110, 30, Text="Shake me")
    add("Button", "btnPulse", 150, 60, 110, 30, Text="Hover me")
    add("Button", move, 20, 110, 110, 30, Text="Move + bounce")
    add("Button", "btnSpin", 150, 110, 110, 30, Text="Rotate")
    add("Button", hide, 20, 160, 110, 30, Text="Hide / show")
    add("Label", "lblInfo", 150, 164, 260, 24, Text="I fade out and in", BackColor="#ffe08a")
    add("Panel", "pnlBox", 300, 60, 120, 80, BackColor="#3399ff")
    motion.add(f, "lblTitle", "slideIn", id="fx1", durationMs=600, params={"from": "left", "distance": 120})
    motion.add(f, "lblTitle", "typewriter", id="fx2", durationMs=900)
    motion.add(f, shake, "shake", id="fx3", trigger={"on": "click"})
    motion.add(f, "btnPulse", "zoom", id="fx4", durationMs=250, params={"scale": 1.15},
               trigger={"on": "hover", "leave": "reverse"})
    motion.add(f, move, "move", id="fx5", durationMs=400, params={"dx": 60, "dy": 0}, trigger={"on": "click"})
    motion.add(f, move, "bounce", id="fx6", durationMs=500, trigger={"on": "after", "after": "fx5"})
    motion.add(f, "btnSpin", "rotate", id="fx7", trigger={"on": "click"})
    motion.add(f, "lblInfo", "fadeOut", id="fx8", trigger={"on": "hide"})
    motion.add(f, "lblInfo", "fadeIn", id="fx9", trigger={"on": "show"})
    motion.add(f, "pnlBox", "colorTo", id="fx10", durationMs=700, autoreverse=True,
               params={"prop": "BackColor", "color": "#ff7a59"}, trigger={"on": "timer", "intervalMs": 2500})
    f.extra["motion"] = {"respectReducedMotion": True}
    return f


TK_USER = '''from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Animations are designed in the Animations window (form.extra["animations"]):
    the title slides in and types itself on load, Shake / Rotate / Move react to clicks, Hover me zooms
    while the mouse is over it and the blue panel changes colour every 2.5 s."""

    def btnHide_Click(self):
        # SetVisible plays lblInfo's "On hide" (fade out) / "On show" (fade in) animation
        self._hidden = not getattr(self, "_hidden", False)
        self.SetVisible("lblInfo", not self._hidden)

    def lblTitle_Click(self):
        # any preset from code, with options
        self.Animate("lblTitle", "pulse", durationMs=500)


if __name__ == "__main__":
    Form1().show()
'''

QT_USER = '''import sys

from PySide6.QtWidgets import QApplication

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Same animations as Motion_Tk_Presets; on Qt the fades are real transparency."""

    def btnHide_Click(self):
        self._hidden = not getattr(self, "_hidden", False)
        self.SetVisible("lblInfo", not self._hidden)

    def lblTitle_Click(self):
        self.Animate("lblTitle", "pulse", durationMs=500)


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
'''

VB_USER = '''Option Explicit

Private Sub cmdHide_Click()
    ' lblInfo has "On hide" / "On show" animations: Visible plays them
    lblInfo.Visible = Not lblInfo.Visible
End Sub

Private Sub lblTitle_Click()
    ' any preset from code: preset, duration (ms), "name=value" options
    lblTitle.Animate "slideIn", 500, "from=right"
End Sub

Private Sub pnlBox_Click()
    pnlBox.Animate "pulse"
    fx10.Begin
End Sub
'''


def write(folder: str, language: str, user_name: str, user_text: str, vb: bool = False) -> None:
    d = HERE / folder
    d.mkdir(exist_ok=True)
    form = build_form(vb)
    form.save(d / "Form1.form")
    (d / "project.radproj").write_text(json.dumps({"name": folder, "language": language, "forms": ["Form1"],
                                                   "startup": "Form1", "modules": []}, indent=2), encoding="utf-8")
    user = d / user_name
    if not user.exists():
        user.write_text(user_text, encoding="utf-8")
    if not vb:
        code = get_plugin(language).generate_designer(form, user.read_text(encoding="utf-8"))
        (d / "Form1_designer.py").write_text(code, encoding="utf-8")


def main() -> None:
    write("Motion_Tk_Presets", "python-tk", "Form1.py", TK_USER)
    write("Motion_Qt_Presets", "python-qt", "Form1.py", QT_USER)
    write("Motion_VB6", "vb-basic", "Form1.bas", VB_USER, vb=True)
    print("ok")


if __name__ == "__main__":
    main()
