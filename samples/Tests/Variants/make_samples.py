"""(Re)build the layout-variant sample projects: one responsive form for python-qt, python-tk and vb-basic.

    python samples/Tests/Variants/make_samples.py

The form is designed once (760 x 460: a docked header and side menu, a search box and a list anchored to
stretch, Save / status anchored to the bottom) and has three sizes made with "This size only":

* Phone  (width <= 599, previewed 400 x 700): side menu hidden, the search box / list / Save button use the
  whole width, the title says "Customers (phone)", the status label is hidden;
* Tablet (width 600-1023, previewed 800 x 600): green header, Save reads "Save changes" and is wider;
* Tabletop (posture half-opened, a foldable on a table): the list only uses the top half.

Writes Form1.form (+ the generated Form1_designer.py for the Python ones) into Variants_Qt_Responsive,
Variants_Tk_Responsive and Variants_VB6. User code files (Form1.py / Form1.bas) are kept when they exist."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from radide.languages import get_plugin  # noqa: E402
from radide.layout import relayout  # noqa: E402
from radide.model import Form  # noqa: E402
from radide.variants import model as vm  # noqa: E402


def build_form(vb: bool = False) -> Form:
    f = Form()
    f.props.update(Name="Form1", Text="Customers", Width=760, Height=460, BackColor="#f4f6fb")
    save = "cmdSave" if vb else "btnSave"

    def add(kind, name, x, y, w, h, parent="", **props):
        c = f.add(kind, x, y, parent)
        c.props.update(Name=name, Left=x, Top=y, Width=w, Height=h, **props)
        return c
    header = add("Panel", "pnlHeader", 0, 0, 760, 56, Dock="Top", BackColor="#1f6feb")
    title = add("Label", "lblTitle", 16, 14, 320, 28, "pnlHeader", Text="Customers", FontSize=14, FontBold=True,
                ForeColor="#ffffff", BackColor="#1f6feb")
    side = add("Panel", "pnlSide", 0, 56, 180, 404, Dock="Left", BackColor="#e8eefc")
    add("Button", "btnHome", 12, 12, 156, 30, "pnlSide", Text="Home")
    add("Button", "btnOrders", 12, 50, 156, 30, "pnlSide", Text="Orders")
    search = add("TextBox", "txtSearch", 200, 72, 540, 24, Anchor="Top, Left, Right", Text="")
    items = add("ListBox", "lstItems", 200, 108, 540, 296, Anchor="Top, Bottom, Left, Right",
                Items="Ada Lovelace;Alan Turing;Grace Hopper;Linus Torvalds")
    btn = add("Button", save, 640, 418, 100, 30, Anchor="Bottom, Right", Text="Save")
    status = add("Label", "lblStatus", 200, 422, 300, 22, Anchor="Bottom, Left", Text="4 customers")
    relayout(f)                     # docked header / side menu snap to the edges
    vm.add_size(f, vm.preset("phone") | {"id": "phone", "preview": {"width": 400, "height": 700}})
    vm.add_size(f, vm.preset("tablet") | {"id": "tablet", "preview": {"width": 800, "height": 600}})
    vm.add_size(f, {"id": "tabletop", "label": "Tabletop", "when": {"posture": "half-opened"},
                    "preview": {"width": 882, "height": 520}})
    # Phone: one column, no side menu (absolute values at the 400 x 700 preview; anchors keep stretching)
    vm.set_override(f, side, "phone", "Visible", False)
    vm.set_override(f, title, "phone", "Text", "Customers (phone)")
    for c, top, h in ((search, 72, 24), (items, 108, 520)):
        for k, v in (("Left", 16), ("Top", top), ("Width", 368), ("Height", h)):
            vm.set_override(f, c, "phone", k, v)
    for k, v in (("Left", 16), ("Top", 650), ("Width", 368), ("Height", 34)):
        vm.set_override(f, btn, "phone", k, v)
    vm.set_override(f, btn, "phone", "Anchor", "Bottom, Left, Right")
    vm.set_override(f, status, "phone", "Visible", False)
    # Tablet: green header, a wider Save button
    vm.set_override(f, header, "tablet", "BackColor", "#0b8a5f")
    vm.set_override(f, title, "tablet", "BackColor", "#0b8a5f")
    vm.set_override(f, btn, "tablet", "Text", "Save changes")
    for k, v in (("Left", 640), ("Top", 558), ("Width", 140), ("Height", 30)):
        vm.set_override(f, btn, "tablet", k, v)
    # Tabletop (half-opened foldable): the list stays above the fold
    vm.set_override(f, items, "tabletop", "Height", 140)
    vm.set_override(f, items, "tabletop", "Anchor", "Top, Left, Right")
    return f


QT_USER = '''import sys

from PySide6.QtWidgets import QApplication

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """One design, three sizes (Phone / Tablet / Tabletop) made with Edit: This size only in the designer.
    Resize the window: the layout switches at 600 and 1024 pixels."""

    def Form1_Load(self):
        self.changes = 0
        self.lblStatus.setText(f"Sizes: {self.CurrentSizes or ['(designed size)']}")

    def Form1_SizeVariantChanged(self):
        self.changes = getattr(self, "changes", 0) + 1
        self.lblStatus.setText(f"Sizes: {self.CurrentSizes or ['(designed size)']}")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
'''

TK_USER = '''from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Same sizes as Variants_Qt_Responsive (python-tk). Resize the window to see the layouts switch."""

    def Form1_Load(self):
        self.changes = 0

    def Form1_SizeVariantChanged(self):
        self.changes = getattr(self, "changes", 0) + 1
        self.lblStatus.configure(text=f"Sizes: {self.CurrentSizes or ['(designed size)']}")


if __name__ == "__main__":
    Form1().show()
'''

VB_USER = '''Option Explicit

Private Sub cmdSave_Click()
    lblStatus.Caption = "Saved"
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
    write("Variants_Qt_Responsive", "python-qt", "Form1.py", QT_USER)
    write("Variants_Tk_Responsive", "python-tk", "Form1.py", TK_USER)
    write("Variants_VB6", "vb-basic", "Form1.bas", VB_USER, vb=True)
    print("ok")


if __name__ == "__main__":
    main()
