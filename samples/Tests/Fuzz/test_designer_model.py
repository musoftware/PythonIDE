"""Model-based fuzzing of the classic form designer (FormDocument + DesignerView + Properties window).

Seeded, reproducible random sequences of user operations, in episodes (default 60 operations) on fresh
documents (an empty form, a rich generated form with containers / TabControl pages / Rm* package controls /
menu / timer, and sample .form files of the repo):

  add (drop at a point, also into containers / TabControl pages) and Toolbox double-click, select (1..4,
  primary = last), Delete key, copy / cut / paste / duplicate, arrow keys (move, Ctrl = grid / edge,
  Shift = resize), mouse drags (move, reparent into / out of containers), Format > Align / Make Same Size /
  Spacing / Center (every mode), Bring to Front / Send to Back, Lock Controls, Properties window edits with
  random valid AND invalid text / combo choices (rename too: invalid / duplicate names), TabControl pages
  and SelectedIndex, layout sizes ("this size only" edits through VariantPreview), animations,
  undo / redo interleaved, save + reload.

After EVERY step: no exception; unique (case-insensitive) valid names; every Parent an existing container,
no cycles, containers before their children, non-visual controls on the form; integer geometry (W/H > 0);
TabPage inside the page list; selection made of live controls; the snapshot round-trips unchanged.
At the end of each episode: undo of everything gives back the exact original form dict, redo of everything
the final one; save -> load equals the in-memory model; designer code of Python/Tk + Python/Qt compiles
(compile()), the VB6 .frm description parses with the IDE's .frm reader and lists every control, and the
JavaScript designer code passes `node --check` (when node is installed).

A failing episode is shrunk automatically (ddmin over its operations; every operation carries its own
random numbers, so any subsequence still replays) and, with --save, stored as corpus/designer/<sig>.json;
those regression cases are replayed first on every run.

Run:  .venv\\Scripts\\python samples\\Tests\\Fuzz\\test_designer_model.py [--seed S] [--steps N]
      [--episode N] [--save] [--replay FILE]
Default: 1200 steps (~2-3 min unloaded; --steps 5000+ for deep runs). Exit code = failures.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing")
for _s in (sys.stdout, sys.stderr):         # Arabic / emoji test values on a cp1252 console
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import PyQt6.QtWebEngineWidgets  # noqa: F401  (before the QApplication)
from PyQt6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, QSettings, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QComboBox, QMessageBox, QPushButton

QCoreApplication.setOrganizationName("RADIDE-TEST-FUZZ")
QCoreApplication.setApplicationName("RADIDE-TEST-FUZZ")
app = QApplication(sys.argv[:1])
QSettings().clear()
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
for _n in ("warning", "critical", "information"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
# a combo choice may open a modal dialog ("(Browse...)", a colour / font picker ...): offscreen nobody can
# close it, so every modal loop is cancelled at once (the dialog's Cancel path is exercised instead)
from PyQt6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFileDialog,
    QFontDialog,
    QInputDialog,
    QMenu,
)

QDialog.exec = lambda self, *a, **k: 0
QMenu.exec = lambda self, *a, **k: None
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: "")
QColorDialog.getColor = staticmethod(lambda *a, **k: __import__("PyQt6.QtGui", fromlist=["QColor"]).QColor())
QFontDialog.getFont = staticmethod(lambda *a, **k: (None, False))
QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", False))

import fuzzlib as FL

from radide import motion  # noqa: F401
from radide.controls import CONTROL_TYPES, PAGED_TYPES, split_items
from radide.designer import DesignerView
from radide.document import FORMAT_MIN, UNDO_LIMIT, FormDocument
from radide.features.variants import VariantPreview
from radide.languages import get_plugin
from radide.model import Form
from radide.motion import model as mm
from radide.motion import presets as mp
from radide.properties import PropertiesPanel, valid_identifier
from radide.variants import model as vm

OUT = Path(tempfile.mkdtemp(prefix="radide-designer-fuzz-"))
VERBOSE = False
# exceptions raised inside Qt virtuals / slots (paintEvent, signal handlers ...): PyQt6 would abort the
# process; they are collected here and reported as a failure of the step that caused them
QT_ERRORS: list[BaseException] = []
sys.excepthook = lambda t, v, tb: QT_ERRORS.append(v.with_traceback(tb))
CORPUS = FL.CORPUS / "designer"
Mod = Qt.KeyboardModifier

COMMON = ["Button", "Label", "TextBox", "CheckBox", "RadioButton", "ListBox", "ComboBox", "PictureBox",
          "ProgressBar", "NumericUpDown", "TrackBar", "TreeView", "ListView", "DataGridView", "DateTimePicker",
          "LinkLabel", "StatusBar"]
CONTAINERS = ["Panel", "GroupBox", "TabControl"]
RM = sorted(t for t in CONTROL_TYPES if t.startswith("Rm"))
NONVISUAL = ["Timer", "OpenFileDialog", "ColorDialog", "MenuStrip", "ToolStrip"]
ALIGN_MODES = sorted(FORMAT_MIN)
PRESET_SIZES = sorted(vm.PRESETS)
FX = sorted(mp.CATALOG)
INT_TEXT = ["0", "1", "8", "16", "100", "250", "-5", "-1", "65535", "2147483647", "99999999999", "abc", "", " 12 ", "1.5",
            "1e3", "0x10", "+7", "٣"]
STR_TEXT = ["Hello", "", "with \"quotes\"", "back\\slash", "new\nline", "tab\there", "'single'", "{0}", "%s",
            "\u0627\u0644\u0639\u0631\u0628\u064a\u0629", "\U0001F600 emoji", "x" * 300, "End Sub", "\"\"\"", "*/",
            "</script>", "${x}", "a\r\nb", "\x00nul", "\u202eRTL"]
BAD_NAMES = ["1abc", "", "my name", "class", "def", "If", "a-b", "Form1", "x" * 3, "Button1", "label1", "ÄÖ"]


class Invariant(AssertionError):
    def __init__(self, name: str, detail: str = ""):
        super().__init__(f"{name}: {detail}")
        self.name = name


# ============================================================================================ base forms
def base_rich() -> Form:
    f = Form()
    f.props["Width"], f.props["Height"] = 640, 480

    def add(t, x, y, parent="", name=None, **props):
        c = f.add(t, x, y, parent)
        if name:
            c.props["Name"] = name
        c.props.update(props)
        return c
    add("Panel", 16, 16, name="pnlTop", Width=300, Height=160)
    add("Button", 8, 8, "pnlTop", name="btnInPanel")
    add("GroupBox", 8, 48, "pnlTop", name="grpInner", Width=200, Height=90)
    add("CheckBox", 8, 20, "grpInner", name="chkDeep")
    tc = add("TabControl", 330, 16, name="tabs", Width=280, Height=200)
    tc.props["TabPages"] = "General;Advanced;About"
    add("TextBox", 8, 8, "tabs", name="txtPage0", TabPage=0)
    add("Label", 8, 8, "tabs", name="lblPage1", TabPage=1)
    add("Button", 16, 200, name="btnOk", Text="OK")
    add("Button", 120, 200, name="btnCancel", Text="Cancel", Anchor="Bottom, Right")
    add("ListBox", 16, 240, name="lstItems", Dock="None")
    if "RmPanel" in CONTROL_TYPES:
        add("RmPanel", 330, 240, name="rmCard", Width=200, Height=120)
        if "RmButton" in CONTROL_TYPES:
            add("RmButton", 8, 8, "rmCard", name="rmAction")
    add("StatusBar", 0, 0, name="sbMain", Dock="Bottom")
    add("Timer", 0, 0, name="tmrTick")
    m = add("MenuStrip", 0, 0, name="menuMain")
    m.props["Items"] = [{"Name": "mnuFile", "Text": "&File", "Items": [{"Name": "mnuExit", "Text": "E&xit"}]}]
    return f


def _sample_forms() -> list[str]:
    out = []
    for pat in ("Examples/Python/*/Form1.form", "Tests/Designer/**/*.form", "Examples/VBNet/*/*.form"):
        for p in sorted((ROOT / "samples").glob(pat)):
            if "HelloSolution" not in p.parts and p.stat().st_size < 60000:
                out.append(str(p.relative_to(ROOT)).replace("\\", "/"))
            if len(out) >= 6:
                return out
    return out


def make_base(name: str) -> Form:
    if name == "empty":
        return Form()
    if name == "rich":
        return base_rich()
    if name.startswith("sample:"):
        return Form.load(ROOT / name[7:])
    raise KeyError(name)


# ============================================================================================ helpers
def pump(n=2):
    for _ in range(n):
        app.processEvents()


def pick(r: float, seq):
    seq = list(seq)
    return seq[min(len(seq) - 1, int(r * len(seq)))] if seq else None


def mouse(w, kind, pos, mods=Mod.NoModifier):
    t = {"press": QEvent.Type.MouseButtonPress, "move": QEvent.Type.MouseMove,
         "release": QEvent.Type.MouseButtonRelease}[kind]
    L = Qt.MouseButton.LeftButton
    btn = Qt.MouseButton.NoButton if kind == "move" else L
    btns = L if kind in ("press", "move") else Qt.MouseButton.NoButton
    p = QPointF(QPoint(*pos))
    QApplication.sendEvent(w, QMouseEvent(t, p, w.mapToGlobal(p), btn, btns, mods))


def deepest_frame(e: BaseException) -> str:
    frames = traceback.extract_tb(e.__traceback__)
    mine = [f for f in frames if os.sep + "radide" + os.sep in f.filename] or frames
    f = mine[-1] if mine else None
    if f is None:
        return type(e).__name__
    try:
        rel = Path(f.filename).resolve().relative_to(ROOT)
    except ValueError:
        rel = Path(f.filename).name
    return f"{type(e).__name__}@{str(rel).replace(os.sep, '/')}:{f.lineno}"


# ============================================================================================ operations
def gen_op(rng: random.Random) -> dict:
    ops = [("add", 10), ("add_default", 4), ("select", 12), ("delete", 4), ("copy_paste", 5), ("cut_paste", 2),
           ("duplicate", 3), ("key", 10), ("drag", 6), ("align", 6), ("order", 3), ("lock", 1), ("prop", 16),
           ("rename", 4), ("pages", 3), ("variant", 4), ("anim", 3), ("undo", 9), ("redo", 5), ("save", 2),
           ("form_prop", 3), ("select_form", 2)]
    name = rng.choices([o for o, _ in ops], [w for _, w in ops])[0]
    op = {"op": name, "r": [round(rng.random(), 6) for _ in range(6)]}
    if name in ("add", "add_default"):
        op["type"] = rng.choice(COMMON * 3 + CONTAINERS * 3 + RM + NONVISUAL)
    elif name == "key":
        op["key"] = rng.choice(["Left", "Right", "Up", "Down"])
        op["mods"] = rng.choice(["", "", "shift", "ctrl", "ctrl+shift"])
    elif name == "align":
        op["mode"] = rng.choice(ALIGN_MODES)
    elif name in ("prop", "form_prop"):
        op["int"] = rng.choice(INT_TEXT)
        op["str"] = rng.choice(STR_TEXT)
    elif name == "rename":
        op["valid"] = rng.random() < 0.6
        op["bad"] = rng.choice(BAD_NAMES)
    elif name == "variant":
        op["action"] = rng.choice(["add", "add", "mode_this", "mode_all", "switch", "remove", "edit", "edit"])
        op["preset"] = rng.choice(PRESET_SIZES)
        op["int"] = rng.choice(INT_TEXT[:9])
    elif name == "anim":
        op["action"] = rng.choice(["add", "add", "remove"])
        op["preset"] = rng.choice(FX)
    return op


class Runner:
    """One episode: a fresh document + DesignerView + Properties window."""

    def __init__(self, base: str):
        self.base = base
        f = make_base(base)
        folder = OUT / f"ep{random.randrange(10 ** 9)}"
        folder.mkdir(parents=True)
        self.path = folder / "Form1.form"
        self.doc = FormDocument(f, self.path)
        self.doc._normalize()
        self.view = DesignerView(self.doc)
        self.view.resize(1000, 760)
        self.view.show()
        self.panel = PropertiesPanel()
        self.panel.set_document(self.doc, get_plugin("python-tk"))
        self.vp = VariantPreview.of(self.view)
        self.doc.renamed.connect(lambda old, new: (mm.rename_references(self.doc.form, old, new),
                                                   vm.rename_references(self.doc.form, old, new)))
        pump()
        self.start = model_state(self.doc.form)
        self.log: list[str] = []

    def close(self):
        try:
            self.vp.set_size(None)
        except Exception:  # noqa: BLE001
            pass
        self.panel.set_document(None, None)
        self.view.close()
        self.view.deleteLater()
        self.panel.deleteLater()
        pump(1)

    # ------------------------------------------------------------------ queries
    @property
    def form(self) -> Form:
        return self.doc.form

    def visual(self):
        return [c for c in self.form.controls if not c.ctype.nonvisual]

    def containers(self):
        return [c for c in self.visual() if c.ctype.container]

    def overlay_point(self, x: int, y: int) -> tuple[int, int]:
        """Form coordinates -> overlay coordinates (zoom / form offset of the view)."""
        ov = self.view.overlay
        origin = ov.abs_rect(self.visual()[0]).topLeft() - QPoint(*self.form.abs_pos(self.visual()[0])) \
            if self.visual() else QPoint(0, 0)
        return origin.x() + x, origin.y() + y

    # ------------------------------------------------------------------ apply one operation
    def apply(self, op: dict) -> None:
        getattr(self, "op_" + op["op"])(op, op["r"])
        pump(1)

    def op_add(self, op, r):
        t = op["type"]
        if t not in CONTROL_TYPES:
            return
        ctype = CONTROL_TYPES[t]
        target = pick(r[0], [None, None] + self.containers())
        if target is not None and not ctype.nonvisual:
            ox, oy = self.form.client_origin(target)
            w, h = int(target.props["Width"]), int(target.props["Height"])
            x, y = ox + int(r[1] * max(1, w - 8)), oy + int(r[2] * max(1, h - 30))
        else:
            x, y = int(r[1] * 560), int(r[2] * 400)
        self.view.create_control(t, QPoint(x, y))

    def op_add_default(self, op, r):
        if op["type"] in CONTROL_TYPES:
            self.view.add_default(op["type"])

    def op_select(self, op, r):
        vis = self.form.controls
        if not vis:
            return
        k = 1 + int(r[0] * 4)
        chosen = []
        for i in range(k):
            c = pick(r[1 + i], vis)
            if c is not None and c not in chosen:
                chosen.append(c)
        self.doc.select_many(chosen)

    def op_select_form(self, op, r):
        self.doc.select(None)

    def op_delete(self, op, r):
        if self.doc.selection:
            self.view.overlay.setFocus()
            QTest.keyClick(self.view.overlay, Qt.Key.Key_Delete)

    def op_copy_paste(self, op, r):
        if self.doc.copy():
            if r[0] < 0.3:
                self.doc.select(pick(r[1], self.containers()))
            self.doc.paste()

    def op_cut_paste(self, op, r):
        if self.doc.selection:
            self.doc.cut()
            if r[0] < 0.7:
                self.doc.select(pick(r[1], [None] + self.containers()))
                self.doc.paste()

    def op_duplicate(self, op, r):
        if self.doc.copy():
            self.doc.paste()

    def op_key(self, op, r):
        if not self.doc.selection:
            return
        key = getattr(Qt.Key, "Key_" + op["key"])
        mods = Mod.NoModifier
        if "shift" in op["mods"]:
            mods |= Mod.ShiftModifier
        if "ctrl" in op["mods"]:
            mods |= Mod.ControlModifier
        self.view.overlay.setFocus()
        QTest.keyClick(self.view.overlay, key, mods)

    def op_drag(self, op, r):
        vis = [c for c in self.visual() if self.view.overlay.abs_rect(c).width() > 4]
        c = pick(r[0], vis)
        if c is None:
            return
        ov = self.view.overlay
        a = ov.abs_rect(c).center()
        dest = pick(r[1], [None, None] + self.containers())
        if dest is not None and dest is not c:
            rr = ov.abs_rect(dest)
            b = QPoint(rr.left() + int(r[2] * max(1, rr.width())), rr.top() + int(r[3] * max(1, rr.height())))
        else:
            b = QPoint(a.x() + int((r[2] - 0.5) * 300), a.y() + int((r[3] - 0.5) * 240))
        mods = Mod.AltModifier if r[4] < 0.2 else Mod.NoModifier
        mouse(ov, "press", (a.x(), a.y()), mods)
        for i in range(1, 4):
            mouse(ov, "move", (a.x() + (b.x() - a.x()) * i // 3, a.y() + (b.y() - a.y()) * i // 3), mods)
        if r[5] < 0.05:                           # Esc during the drag: everything goes back
            QTest.keyClick(ov, Qt.Key.Key_Escape)
        mouse(ov, "release", (b.x(), b.y()), mods)

    def op_align(self, op, r):
        self.doc.align(op["mode"])

    def op_order(self, op, r):
        if self.doc.selection:
            self.doc.reorder(list(self.doc.selection), r[0] < 0.5)

    def op_lock(self, op, r):
        self.doc.set_locked(not self.doc.locked)

    # -- Properties window
    def _rows(self):
        p = self.panel
        out = []
        for row in range(p.props.rowCount()):
            d = p._row_def(row)
            if d is not None and not isinstance(d, str):
                out.append((row, d))
        return out

    def _edit_row(self, row, d, op, r):
        p = self.panel
        w = p.props.cellWidget(row, 1)
        if VERBOSE:
            print(f"         row {d.name} ({d.kind}) widget {type(w).__name__}", flush=True)
        if isinstance(w, QComboBox):
            if w.count():
                i = int(r[3] * w.count()) % w.count()
                w.setCurrentIndex(i)
                w.activated.emit(i)
            return
        if isinstance(w, QPushButton) or w is not None:
            # dialogs (colour, font, file, menu, anchor ...): the value they would commit
            v = None
            if d.kind == "color":
                v = pick(r[3], ["#FF0000", "#00FF00", "", "#123ABC", "Red"])
            elif d.kind == "anchor":
                v = pick(r[3], ["Top, Left", "Bottom, Right", "Top, Bottom, Left, Right", "None", "Left"])
            elif d.kind == "font":
                v = pick(r[3], ["Segoe UI", "Arial", "Courier New"])
            elif d.kind == "list":
                v = ";".join(f"Item{i}" for i in range(int(r[3] * 5)))
            if v is not None:
                p._set(d.name, v)
            return
        item = p.props.item(row, 1)
        if item is None or not (item.flags() & Qt.ItemFlag.ItemIsEditable):
            return
        if d.name == "Name":
            return
        text = op["int"] if d.kind in ("int", "float") else op["str"]
        if d.kind == "list":
            text = pick(r[3], ["A;B;C", "", "Page1", "x;;y"])
        item.setText(text)

    def op_prop(self, op, r):
        if self.doc.selected is None:
            self.op_select({"op": "select"}, r)
        rows = [(row, d) for row, d in self._rows() if d.name != "Name"]
        if rows:
            row, d = pick(r[2], rows)
            self._edit_row(row, d, op, r)

    def op_form_prop(self, op, r):
        self.doc.select(None)
        pump(1)
        rows = [(row, d) for row, d in self._rows() if d.name in ("Width", "Height", "Text", "BackColor",
                                                                     "StartPosition", "LockControls")]
        if rows:
            row, d = pick(r[2], rows)
            self._edit_row(row, d, op, r)

    def op_rename(self, op, r):
        c = pick(r[0], self.form.controls)
        if c is None:
            return
        self.doc.select(c)
        pump(1)
        row = next((row for row, d in self._rows() if d.name == "Name"), None)
        if row is None:
            return
        if op["valid"]:
            base = pick(r[1], ["renamed", "ctl", "alpha", "Zeta"])
            new = self.form.unique_name(base)
        else:
            new = op["bad"]
        item = self.panel.props.item(row, 1)
        if item is not None:
            item.setText(new)

    def op_pages(self, op, r):
        paged = [c for c in self.visual() if c.type in PAGED_TYPES]
        c = pick(r[0], paged)
        if c is None:
            return
        key = "Pages" if "Pages" in c.props and "TabPages" not in c.props else "TabPages"
        pages = split_items(c.props.get(key, ""))
        if r[1] < 0.4:
            new = pages + [f"Page{len(pages) + 1}"]
        elif r[1] < 0.7 and pages:
            k = int(r[2] * len(pages))
            new = pages[:k] + pages[k + 1:]
        else:
            new = None
        if new is not None:              # what the Properties window commits: "Page1;Page2"
            self.doc.set_prop(c, key, ";".join(new))
        else:
            n = max(1, len(pages))
            self.doc.set_prop(c, "SelectedIndex", int(r[3] * (n + 1)) - (1 if r[4] < 0.1 else 0))

    def op_variant(self, op, r):
        a, vp = op["action"], self.vp
        sizes = vm.sizes(self.form)
        if a == "add":
            if len(sizes) < 4:
                vp.add_size(vm.preset(op["preset"]), select=r[0] < 0.7, edit_only=r[1] < 0.6)
        elif a == "switch":
            vp.set_size(pick(r[0], [None] + [s["id"] for s in sizes]))
        elif a == "mode_this":
            vp.set_mode("this")
        elif a == "mode_all":
            vp.set_mode("all")
        elif a == "remove" and sizes:
            vid = pick(r[0], sizes)["id"]
            self.doc.checkpoint()
            vm.remove_size(self.form, vid)
            self.doc.set_modified()
            if vp.vid == vid:
                vp.set_size(None)
            vp.invalidate()
        elif a == "edit":                 # a geometry edit while a size is shown (either mode)
            c = pick(r[0], self.visual())
            if c is not None:
                try:
                    v = int(op["int"])
                except ValueError:
                    return
                self.doc.set_prop(c, pick(r[1], ["Left", "Top", "Width", "Height"]), max(1, v))

    def op_anim(self, op, r):
        lst = mm.animations(self.form) if self.form.extra.get("animations") else []
        if op["action"] == "add":
            target = pick(r[0], [""] + [c.name for c in self.visual()])
            self.doc.checkpoint()
            try:
                mm.add(self.form, target, op["preset"])
            except (KeyError, ValueError):
                self.doc.drop_noop()
                return
            self.doc.set_modified()
        elif lst:
            fx = pick(r[0], lst)
            self.doc.checkpoint()
            mm.remove(self.form, fx.get("id"))
            self.doc.set_modified()

    def op_undo(self, op, r):
        self.doc.undo()

    def op_redo(self, op, r):
        self.doc.redo()

    def op_save(self, op, r):
        self.check_save_load()

    # ------------------------------------------------------------------ invariants
    def check_model(self) -> None:
        f = self.form
        names = {}
        for c in f.controls:
            n = c.props.get("Name")
            if not isinstance(n, str) or not valid_identifier(n):
                raise Invariant("valid names", f"{n!r} ({c.type})")
            if n.lower() in names or n.lower() == str(f.name).lower():
                raise Invariant("unique names", f"{n!r} twice")
            names[n.lower()] = c
            if c.type not in CONTROL_TYPES:
                raise Invariant("known types", c.type)
        byname = {c.name: c for c in f.controls}
        index = {id(c): i for i, c in enumerate(f.controls)}
        for c in f.controls:
            par = c.props.get("Parent", "")
            if c.ctype.nonvisual:
                if par:
                    raise Invariant("non-visual controls on the form", f"{c.name} in {par!r}")
                continue
            for k in ("Left", "Top", "Width", "Height"):
                v = c.props.get(k)
                if not isinstance(v, int) or isinstance(v, bool):
                    raise Invariant("integer geometry", f"{c.name}.{k} = {v!r}")
            if c.props["Width"] < 0 or c.props["Height"] < 0:        # (0 is allowed, like WinForms)
                raise Invariant("non-negative size", f"{c.name} {c.props['Width']}x{c.props['Height']}")
            if par:
                p = byname.get(par)
                if p is None or not p.ctype.container or p.ctype.nonvisual:
                    raise Invariant("valid parents", f"{c.name} -> {par!r}")
                if index[id(p)] > index[id(c)]:
                    raise Invariant("containers before children", f"{par} after {c.name}")
                seen, q = {c.name}, p
                while q is not None and q.props.get("Parent"):
                    if q.name in seen:
                        raise Invariant("no parent cycles", c.name)
                    seen.add(q.name)
                    q = byname.get(q.props.get("Parent"))
                if p.type in PAGED_TYPES and "TabPage" in c.props:
                    n = len(split_items(p.props.get("TabPages", p.props.get("Pages", ""))))
                    tp = c.props.get("TabPage")
                    if not isinstance(tp, int) or not (0 <= tp < max(1, n)):
                        raise Invariant("TabPage inside the page list", f"{c.name}.TabPage = {tp!r}, {n} pages")
        alive = {id(c) for c in f.controls}
        if any(id(c) not in alive for c in self.doc.selection):
            raise Invariant("selection made of live controls")
        snap = f.snapshot()
        again = Form.from_dict(json.loads(snap)).snapshot()
        if again != snap:
            raise Invariant("snapshot round-trips", _diff(json.loads(snap), json.loads(again)))
        if len(self.doc._undo) > UNDO_LIMIT:
            raise Invariant("undo limit", str(len(self.doc._undo)))

    def check_save_load(self) -> None:
        self.doc.save()
        loaded = Form.load(self.path).to_dict()
        mine = json.loads(json.dumps(self.form.to_dict()))
        if loaded != mine:
            raise Invariant("save -> load equals the model", _diff(mine, loaded))

    def check_codegen(self, with_node: bool = True) -> None:
        f = self.form
        for pid in ("python-tk", "python-qt"):
            code = get_plugin(pid).generate_designer(f, "")
            try:
                compile(code, f"{pid}_designer.py", "exec")
            except SyntaxError as e:
                raise Invariant(f"{pid} designer code compiles", f"{e}: {code.splitlines()[e.lineno - 1] if e.lineno else ''}") from None
        frm = get_plugin("vb-basic").generate_designer(f, "")
        from radide.foreign.frm_writer import load_form, parse_frm
        doc = parse_frm(frm)
        if doc.root is None:
            raise Invariant("VB6 .frm description parses", frm[:300])
        got = {b.name.lower() for b in doc.root.walk()}
        want = {c.name.lower() for c in self.visual()}
        if not want <= got:
            raise Invariant("VB6 .frm lists every control", f"missing {sorted(want - got)[:5]}")
        p = self.path.with_suffix(".frm")
        p.write_text(frm, encoding="cp1252", errors="replace")
        load_form(frm, p, p.parent / "frmcache")
        node = shutil.which("node") if with_node else None
        if node:
            js = get_plugin("javascript").generate_designer(f, "")
            jp = self.path.with_name("designer_check.js")
            jp.write_text(js, encoding="utf-8")
            res = subprocess.run([node, "--check", str(jp)], capture_output=True, text=True, timeout=60)
            if res.returncode != 0:
                raise Invariant("JavaScript designer code passes node --check", res.stderr[-400:])

    def check_undo_redo_all(self) -> None:
        if len(self.doc._undo) >= UNDO_LIMIT:
            return                                  # the oldest steps were dropped: not comparable
        self.vp.set_size(None)
        final = model_state(self.form)
        n = 0
        while self.doc.can_undo():
            self.doc.undo()
            n += 1
            self.check_model()
        now = model_state(self.form)
        if now != self.start:
            raise Invariant("undo of everything gives the original form", _diff(self.start, now))
        for _ in range(n):            # exactly the steps undone (redo steps pending at the end stay pending)
            if not self.doc.can_redo():
                raise Invariant("redo of everything gives the final form", f"only some of {n} redo steps")
            self.doc.redo()
            self.check_model()
        now = model_state(self.form)
        if now != final:
            raise Invariant("redo of everything gives the final form", _diff(final, now))


def model_state(form: Form) -> dict:
    """The form dict compared by the undo / redo checks. SelectedIndex of a TabControl is view state: the
    designer shows the page of the selected control by changing it, and like in Visual Studio switching
    tabs is no undo step - it is left out."""
    d = json.loads(form.snapshot())
    for c in d.get("controls", []):
        if c.get("type") in PAGED_TYPES:
            c.get("props", {}).pop("SelectedIndex", None)
    return d


def _diff(a, b, path="$") -> str:
    if type(a) is not type(b):
        return f"{path}: {a!r:.120} != {b!r:.120}"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                return f"{path}.{k}: only in {'first' if k in a else 'second'} ({(a.get(k) if k in a else b.get(k))!r:.120})"
            if a[k] != b[k]:
                return _diff(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: {len(a)} items != {len(b)} items"
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return _diff(x, y, f"{path}[{i}]")
    elif a != b:
        return f"{path}: {a!r:.120} != {b!r:.120}"
    return f"{path}: equal?"


# ============================================================================================ episodes
def run_episode(base: str, ops: list[dict], final_checks: bool = True, node: bool = True) -> tuple[str | None, str, int]:
    """(failure signature | None, detail, steps done)."""
    try:
        r = Runner(base)
    except Exception as e:  # noqa: BLE001
        return f"setup:{deepest_frame(e)}", traceback.format_exc()[-2000:], 0
    done = 0
    try:
        r.check_model()
        for i, op in enumerate(ops):
            if VERBOSE:
                print(f"       [{base}] step {i}: {op}", flush=True)
            try:
                r.apply(op)
                if QT_ERRORS:
                    raise QT_ERRORS.pop(0)
            except Invariant:
                raise
            except Exception as e:  # noqa: BLE001
                del QT_ERRORS[:]
                tb = "".join(traceback.format_exception(e))[-2500:]
                return f"exc:{op['op']}:{deepest_frame(e)}", f"step {i} {op}\n{tb}", done
            done += 1
            try:
                r.check_model()
            except Invariant as e:
                return f"inv:{e.name}:{op['op']}", f"after step {i} {op}: {e}", done
            except Exception as e:  # noqa: BLE001
                return f"check:{deepest_frame(e)}", f"after step {i} {op}\n{traceback.format_exc()[-2500:]}", done
        if final_checks:
            for name, fn in (("save/load", r.check_save_load), ("codegen", lambda: r.check_codegen(node)),
                             ("undo/redo all", r.check_undo_redo_all), ("save/load", r.check_save_load)):
                try:
                    fn()
                except Invariant as e:
                    return f"inv:{e.name}", f"end of episode ({name}): {e}", done
                except Exception as e:  # noqa: BLE001
                    return f"end:{name}:{deepest_frame(e)}", traceback.format_exc()[-2500:], done
        return None, "", done
    finally:
        r.close()


def shrink(base: str, ops: list[dict], sig: str, budget: float) -> list[dict]:
    end = time.monotonic() + budget

    def still(cand):
        if time.monotonic() > end:
            return False
        s, _d, _n = run_episode(base, cand)
        return s == sig
    return FL.ddmin(list(ops), still, max_probes=400)


def save_case(base: str, ops: list[dict], sig: str, detail: str) -> Path:
    CORPUS.mkdir(parents=True, exist_ok=True)
    import hashlib
    import re
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", sig)[:60] + "_" + hashlib.sha1(sig.encode()).hexdigest()[:8]
    p = CORPUS / f"{name}.json"
    p.write_text(json.dumps({"base": base, "sig": sig, "detail": detail[:1500], "ops": ops}, indent=1,
                            ensure_ascii=False), encoding="utf-8")
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", default=os.environ.get("RADFUZZ_SEED", "radide"))
    ap.add_argument("--steps", type=int, default=1200, help="total random operations (default 1200)")
    ap.add_argument("--episode", type=int, default=60, help="operations per episode (default 60)")
    ap.add_argument("--save", action="store_true", help="store shrunk failures in corpus/designer/")
    ap.add_argument("--no-shrink", action="store_true")
    ap.add_argument("--shrink-secs", type=float, default=120.0)
    ap.add_argument("--replay", help="run one saved case (corpus/designer/*.json) and print the result")
    ap.add_argument("--max-failures", type=int, default=8, help="stop the random part after this many")
    ap.add_argument("--verbose", action="store_true", help="print every operation before it runs")
    args = ap.parse_args()
    global VERBOSE
    VERBOSE = args.verbose
    rep = FL.Report()
    t0 = time.monotonic()
    try:
        if args.replay:
            case = json.loads(Path(args.replay).read_text(encoding="utf-8"))
            sig, detail, n = run_episode(case["base"], case["ops"])
            rep.check(f"replay {Path(args.replay).name} ({len(case['ops'])} ops)", sig is None, f"{sig}\n{detail}")
            return rep.summary()
        # 1. regression cases
        cases = sorted(CORPUS.glob("*.json")) if CORPUS.is_dir() else []
        bad = []
        for p in cases:
            case = json.loads(p.read_text(encoding="utf-8"))
            sig, detail, _n = run_episode(case["base"], case["ops"])
            if sig is not None:
                bad.append(f"{p.name}: {sig} {detail[-600:]}")
        rep.check(f"designer regression corpus ({len(cases)} minimized sequences) passes", not bad, "\n".join(bad))
        # 2. random episodes
        bases = ["empty", "rich", "rich"] + [f"sample:{s}" for s in _sample_forms()]
        rng = random.Random(f"{args.seed}:designer")
        steps = episodes = 0
        failures: dict[str, str] = {}
        while steps < args.steps and len(failures) < args.max_failures:
            base = bases[episodes % len(bases)]
            ops = [gen_op(rng) for _ in range(args.episode)]
            sig, detail, n = run_episode(base, ops, node=episodes % 4 == 0)
            steps += n
            episodes += 1
            if sig is None or sig in failures:
                continue
            print(f"     failure in episode {episodes} ({base}): {sig}", flush=True)
            small = ops if args.no_shrink else shrink(base, ops, sig, args.shrink_secs)
            s2, d2, _ = run_episode(base, small)
            where = ""
            if args.save:
                where = f" -> {save_case(base, small, sig, d2 or detail).relative_to(HERE)}"
            else:
                tmp = OUT.parent / "radide-designer-fuzz-findings"
                tmp.mkdir(exist_ok=True)
                fp = tmp / f"case_{len(failures)}.json"
                fp.write_text(json.dumps({"base": base, "sig": sig, "ops": small}, indent=1), encoding="utf-8")
                where = f" -> {fp}"
            failures[sig] = f"{sig} ({len(ops)} -> {len(small)} ops){where}\n{(d2 or detail)[-1500:]}"
        rep.check(f"{steps} random designer operations in {episodes} episodes keep the model consistent "
                  f"(undo/redo all, save/load, codegen after each episode)", not failures,
                  "\n\n".join(failures.values()))
        print(f"     {steps} steps, {episodes} episodes, {time.monotonic() - t0:.0f} s", flush=True)
    finally:
        QSettings().clear()
        shutil.rmtree(OUT, ignore_errors=True)
    return rep.summary()


if __name__ == "__main__":
    sys.exit(main())
