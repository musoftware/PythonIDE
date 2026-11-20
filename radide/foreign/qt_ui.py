"""Qt Designer .ui files (PySide6 / PyQt / C++ Qt projects) opened IN PLACE.

* ``read_ui(path) -> (Form, UiContext)``: the .ui XML -> the neutral form model for the designer.
  Widgets inside layouts keep their layout (positions shown are the real ones, computed by
  PyQt6.uic when available) and are marked ``NativeLayout`` - their geometry is never written.
* ``write_ui(path, form) -> notes``: writes ONLY what changed (compared with the file on disk)
  as byte-span patches (radide/foreign/_xmlspan.py): unknown widgets, properties, layouts,
  custom widgets, resources, connections, comments and formatting stay untouched; open + save
  without changes leaves the file byte-identical.
* ``QtProjectAdapter``: a .ui file (with its sibling .ui files), a qmake ``.pro`` project or a
  PySide ``.pyproject``. Code generation (pyside6-uic / uic) stays the project's own.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ..model import Control, Form
from ..controls import CONTROL_TYPES
from . import _xmlspan as X
from ._others_base import (ForeignAdapter, ForeignProject, FormBinding, RunTarget, Step, find_gdb, mingw_bin,
                           show_projects, source_files, tool_env)

QT2TYPE = {
    "QPushButton": "Button", "QToolButton": "Button", "QCommandLinkButton": "Button",
    "QLabel": "Label", "QLineEdit": "TextBox", "QTextEdit": "TextBox", "QPlainTextEdit": "TextBox",
    "QTextBrowser": "TextBox", "QCheckBox": "CheckBox", "QRadioButton": "RadioButton",
    "QComboBox": "ComboBox", "QFontComboBox": "ComboBox", "QListWidget": "ListBox", "QListView": "ListBox",
    "QGroupBox": "GroupBox", "QFrame": "Panel", "QWidget": "Panel", "QScrollArea": "Panel",
    "QStackedWidget": "Panel", "QTabWidget": "TabControl", "QProgressBar": "ProgressBar",
    "QSpinBox": "NumericUpDown", "QDoubleSpinBox": "NumericUpDown", "QSlider": "TrackBar", "QDial": "TrackBar",
    "QScrollBar": "TrackBar", "QTreeWidget": "TreeView", "QTreeView": "TreeView",
    "QTableWidget": "DataGridView", "QTableView": "DataGridView", "QDateEdit": "DateTimePicker",
    "QDateTimeEdit": "DateTimePicker", "QTimeEdit": "DateTimePicker", "QCalendarWidget": "DateTimePicker",
    "QStatusBar": "StatusBar", "QMenuBar": "MenuStrip", "QToolBar": "ToolStrip",
}
TYPE2QT = {"Button": "QPushButton", "Label": "QLabel", "TextBox": "QLineEdit", "CheckBox": "QCheckBox",
           "RadioButton": "QRadioButton", "ComboBox": "QComboBox", "ListBox": "QListWidget",
           "GroupBox": "QGroupBox", "Panel": "QFrame", "TabControl": "QTabWidget", "ProgressBar": "QProgressBar",
           "NumericUpDown": "QSpinBox", "TrackBar": "QSlider", "TreeView": "QTreeWidget",
           "DataGridView": "QTableWidget", "DateTimePicker": "QDateEdit", "PictureBox": "QLabel",
           "LinkLabel": "QLabel", "ListView": "QTreeWidget", "StatusBar": "QStatusBar"}
TEXT_PROP = {"QGroupBox": "title", "QPlainTextEdit": "plainText", "QTextEdit": "plainText",
             "QTextBrowser": "plainText"}
NO_TEXT = {"QFrame", "QWidget", "QScrollArea", "QStackedWidget", "QTabWidget", "QProgressBar", "QSpinBox",
           "QDoubleSpinBox", "QSlider", "QDial", "QScrollBar", "QTreeWidget", "QTreeView", "QTableWidget",
           "QTableView", "QListWidget", "QListView", "QComboBox", "QFontComboBox", "QCalendarWidget",
           "QDateEdit", "QDateTimeEdit", "QTimeEdit", "QStatusBar", "QMenuBar", "QToolBar"}
# model props written back as simple .ui properties: model prop -> (ui property, kind)
SIMPLE = {"Enabled": ("enabled", "bool"), "ToolTip": ("toolTip", "string"), "Checked": ("checked", "bool"),
          "Value": ("value", "number"), "Minimum": ("minimum", "number"), "Maximum": ("maximum", "number")}
EVENT2SIGNAL = {"Click": "clicked", "TextChanged": "textChanged", "CheckedChanged": "toggled",
                "SelectedIndexChanged": "currentIndexChanged", "ValueChanged": "valueChanged",
                "DoubleClick": "doubleClicked", "Load": "", "Tick": "timeout"}
TRANSPARENT = ("centralwidget", "scrollAreaWidgetContents")


@dataclass
class UiContext:
    data: bytes
    root: X.XNode
    top: X.XNode
    widgets: dict = field(default_factory=dict)       # native name -> XNode <widget>
    in_layout: dict = field(default_factory=dict)     # native name -> <item> XNode (layout-managed)
    hosts: dict = field(default_factory=dict)         # model parent ("" / name / name#page) -> XNode host widget
    is_main: bool = False
    notes: list = field(default_factory=list)


# ---------------------------------------------------------------- reading

def _prop(w: X.XNode, name: str) -> X.XNode | None:
    return w.find("property", name=name)


def _value(p: X.XNode | None):
    if p is None or not p.children:
        return None
    v = p.children[0]
    t = v.tag
    if t in ("string", "cstring", "enum", "set"):
        return v.text
    if t == "bool":
        return v.text.strip().lower() == "true"
    if t in ("number", "double"):
        try:
            return int(float(v.text)) if t == "number" else float(v.text)
        except ValueError:
            return 0
    if t == "rect":
        return tuple(int(float((v.find(k).text if v.find(k) is not None else "0") or 0))
                     for k in ("x", "y", "width", "height"))
    if t == "font":
        return {c.tag: c.text for c in v.children}
    return v.text


def _items(w: X.XNode) -> list[str]:
    out = []
    for it in w.findall("item"):
        p = _prop(it, "text")
        if p is not None:
            out.append(_value(p) or "")
    return out


def read_ui(path: Path, live: bool = True) -> tuple[Form, UiContext]:
    data = Path(path).read_bytes()
    root = X.parse(data)
    top = root.find("widget")
    if top is None:
        raise ValueError(f"{Path(path).name}: no top-level <widget>")
    ctx = UiContext(data, root, top, is_main=top.get("class") == "QMainWindow")
    form = Form()
    cls_node = root.find("class")
    form.props["Name"] = (cls_node.text.strip() if cls_node is not None else "") or top.get("name") or "Form"
    form.props["Text"] = _value(_prop(top, "windowTitle")) or form.props["Name"]
    geo = _value(_prop(top, "geometry"))
    if geo:
        form.props["Width"], form.props["Height"] = geo[2], geo[3]
    form.props["NativeClass"] = top.get("class")
    geoms = _live_geometry(data, Path(path)) if live else None
    order: list[Control] = []

    def host_walk(host: X.XNode, parent: str, page=None, in_layout_item=None):
        if parent not in ctx.hosts or page is not None:
            ctx.hosts[parent if page is None else f"{parent}#{page}"] = host
        for c in host.children:
            if c.tag == "widget":
                handle(c, parent, page, None)
            elif c.tag == "layout":
                layout_walk(c, parent, page)

    def layout_walk(layout: X.XNode, parent: str, page):
        for item in layout.findall("item"):
            for c in item.children:
                if c.tag == "widget":
                    handle(c, parent, page, item)
                elif c.tag == "layout":
                    layout_walk(c, parent, page)

    def handle(w: X.XNode, parent: str, page, item):
        cls, name = w.get("class", "QWidget"), w.get("name", "")
        if not name:
            return
        ctx.widgets[name] = w
        if item is not None:
            ctx.in_layout[name] = item
        if name in TRANSPARENT and cls == "QWidget" and not parent:
            host_walk(w, "", page)
            return
        mtype = QT2TYPE.get(cls)
        if mtype is None:
            mtype = "Panel"
        if cls in ("QDockWidget",):
            return
        ct = CONTROL_TYPES[mtype]
        props = ct.default_props(name)
        props["Parent"] = parent
        if page is not None:
            props["TabPage"] = page
        props["NativeId"] = name
        props["NativeClass"] = cls
        if item is not None or (ctx.is_main and cls in ("QStatusBar", "QToolBar")):
            props["NativeLayout"] = True          # placed by a layout / by QMainWindow
        if not ct.nonvisual:
            g = _value(_prop(w, "geometry"))
            if geoms and name in geoms:
                g = geoms[name]
            if g:
                props["Left"], props["Top"], props["Width"], props["Height"] = g
            elif item is not None:
                props["Left"], props["Top"] = _estimate(ctx, item, ct)
        if ct.has_text and cls not in NO_TEXT:
            t = _value(_prop(w, TEXT_PROP.get(cls, "text")))
            if t is None and cls in ("QTextEdit", "QTextBrowser"):
                html = _value(_prop(w, "html"))
                t = re.sub(r"<[^>]+>", "", html or "").strip() if html else None
            props["Text"] = t if t is not None else ""
        for mp, (up, _k) in SIMPLE.items():
            if mp in props:
                v = _value(_prop(w, up))
                if v is not None:
                    props[mp] = v
        if cls in ("QTextEdit", "QPlainTextEdit", "QTextBrowser"):
            props["Multiline"] = True
        if mtype in ("ComboBox", "ListBox"):
            props["Items"] = ";".join(_items(w))
        font = _value(_prop(w, "font"))
        if isinstance(font, dict):
            if font.get("pointsize"):
                props["FontSize"] = int(font["pointsize"])
            if font.get("family"):
                props["FontName"] = font["family"]
            if font.get("bold"):
                props["FontBold"] = font["bold"] == "true"
            if font.get("italic"):
                props["FontItalic"] = font["italic"] == "true"
        if mtype == "MenuStrip":
            props["Items"] = _menu_items(ctx, w)
        ctrl = Control(mtype, props)
        order.append(ctrl)
        if cls == "QTabWidget":
            titles = []
            pages = [c for c in w.children if c.tag == "widget"]
            for i, pg in enumerate(pages):
                ctx.widgets[pg.get("name", "")] = pg
                t = pg.find("attribute", name="title")
                titles.append(_value(t) if t is not None else pg.get("name", f"Tab{i + 1}"))
                host_walk(pg, name, i)
            props["TabPages"] = ";".join(titles)
            ctx.hosts.setdefault(name, pages[0] if pages else w)
        elif cls == "QScrollArea":
            inner = next((c for c in w.children if c.tag == "widget"), None)
            if inner is not None:
                ctx.widgets[inner.get("name", "")] = inner
                host_walk(inner, name)
        elif cls == "QStackedWidget":
            inner = next((c for c in w.children if c.tag == "widget"), None)
            if inner is not None:
                ctx.widgets[inner.get("name", "")] = inner
                host_walk(inner, name)
        elif ct.container or mtype == "Panel":
            host_walk(w, name)

    host_walk(top, "")
    if ctx.is_main and "" in ctx.hosts and ctx.hosts[""] is top:
        central = next((c for c in top.children if c.tag == "widget" and c.get("name") in TRANSPARENT), None)
        if central is not None:
            ctx.hosts[""] = central
    form.controls = order
    return form, ctx


def _menu_items(ctx: UiContext, menubar: X.XNode) -> list:
    actions = {}
    for a in ctx.top.iter("action"):
        actions[a.get("name", "")] = _value(_prop(a, "text")) or a.get("name", "")

    def menu(m: X.XNode) -> dict:
        items = []
        for c in m.children:
            if c.tag == "addaction":
                n = c.get("name", "")
                if n == "separator":
                    items.append({"Text": "-", "Name": "", "Items": []})
                elif n in actions:
                    items.append({"Text": actions[n], "Name": n, "Items": []})
                else:
                    sub = next((w for w in m.children if w.tag == "widget" and w.get("name") == n), None)
                    if sub is not None:
                        items.append(menu(sub))
        return {"Text": _value(_prop(m, "title")) or m.get("name", ""), "Name": m.get("name", ""), "Items": items}
    return menu(menubar)["Items"]


def _estimate(ctx: UiContext, item: X.XNode, ct) -> tuple[int, int]:
    """Position of a layout item when the live layout is not available."""
    layout = item.parent
    cls = layout.get("class", "") if layout is not None else ""
    idx = layout.children.index(item) if layout is not None else 0
    row, col = int(item.get("row", idx) or 0), int(item.get("column", 0) or 0)
    if cls == "QHBoxLayout":
        return 9 + idx * 90, 9
    if cls in ("QGridLayout", "QFormLayout"):
        return 9 + col * 110, 9 + row * 30
    return 9, 9 + idx * 30


_LIVE_CACHE: dict = {}

_PYSIDE_LAYOUT = r"""
import json, os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPoint, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QWidget
app = QApplication([])
data = sys.stdin.buffer.read()
buf = QBuffer(); buf.setData(QByteArray(data)); buf.open(QIODevice.ReadOnly)
os.chdir(sys.argv[1])
w = QUiLoader().load(buf)
if w is None:
    sys.exit(2)
w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
if len(sys.argv) > 3:
    w.resize(int(sys.argv[2]), int(sys.argv[3]))
w.show(); app.processEvents()
out = {}
for c in w.findChildren(QWidget):
    n = c.objectName()
    if not n or c.parentWidget() is None:
        continue
    h = c.parentWidget()
    while h is not None and h is not w and not h.objectName():
        h = h.parentWidget()
    h = h or w
    p = c.mapTo(h, QPoint(0, 0))
    out[n] = [p.x(), p.y(), c.width(), c.height()]
print(json.dumps(out))
"""


def _live_geometry(data: bytes, path: Path) -> dict | None:
    """Real positions of every named widget: PyQt6.uic in process, else PySide6's QUiLoader in a
    subprocess (Qt 5 style enums, custom widgets ...). Cached per file content."""
    import hashlib
    key = hashlib.sha1(data).hexdigest()
    if key in _LIVE_CACHE:
        return _LIVE_CACHE[key]
    geo = _live_geometry_pyqt(data, path)
    if geo is None:
        geo = _live_geometry_pyside(data, path)
    if len(_LIVE_CACHE) > 64:
        _LIVE_CACHE.clear()
    _LIVE_CACHE[key] = geo
    return geo


def _live_geometry_pyside(data: bytes, path: Path) -> dict | None:
    import importlib.util
    import subprocess
    if importlib.util.find_spec("PySide6") is None:
        return None
    m = re.search(rb"<widget[^>]*>\s*(?:<property[^>]*>(?:(?!</property>).)*</property>\s*)*?"
                  rb"<property name=\"geometry\">\s*<rect>\s*<x>-?\d+</x>\s*<y>-?\d+</y>"
                  rb"\s*<width>(\d+)</width>\s*<height>(\d+)</height>", data, re.S)
    args = [sys.executable, "-I", "-c", _PYSIDE_LAYOUT, str(path.parent)] +         ([m.group(1).decode(), m.group(2).decode()] if m else [])
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    try:
        r = subprocess.run(args, input=data, capture_output=True, timeout=30, env=env,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0:
            return None
        return {k: tuple(v) for k, v in json.loads(r.stdout.decode("utf-8", "replace").strip().splitlines()[-1]).items()}
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def _live_geometry_pyqt(data: bytes, path: Path) -> dict | None:
    """Real positions of every named widget (laid out by Qt itself), relative to the widget that
    hosts it in the model (the central widget, a group box, a tab page ...). None if unavailable."""
    try:
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import Qt, QPoint
        if QApplication.instance() is None:
            return None
        import io
        from PyQt6 import uic
        cwd = os.getcwd()
        try:
            os.chdir(path.parent)                 # resources / includes relative to the .ui
            w = uic.loadUi(io.BytesIO(data))
        finally:
            os.chdir(cwd)
    except Exception:  # noqa: BLE001 - custom widgets, PyQt6 missing ...
        return None
    try:
        w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        geo = re.search(rb"<widget[^>]*>\s*<property name=\"geometry\">\s*<rect>\s*<x>(-?\d+)</x>\s*<y>(-?\d+)</y>"
                        rb"\s*<width>(\d+)</width>\s*<height>(\d+)</height>", data)
        if geo:
            w.resize(int(geo.group(3)), int(geo.group(4)))
        w.show()
        QApplication.processEvents()
        out = {}
        for child in w.findChildren(QWidget):
            name = child.objectName()
            if not name or child.parentWidget() is None:
                continue
            host = child.parentWidget()
            # the model parent is the nearest named ancestor that is not a layout helper; tab pages and
            # scroll contents are hosts themselves
            hp = host
            while hp is not None and hp is not w and not hp.objectName():
                hp = hp.parentWidget()
            host = hp or w
            p = child.mapTo(host, QPoint(0, 0)) if host is not child else QPoint(0, 0)
            out[name] = (p.x(), p.y(), child.width(), child.height())
        w.close()
        w.deleteLater()
        return out
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- writing

def _rect_lines(x, y, w, h) -> list[str]:
    return ['<property name="geometry">', " <rect>", f"  <x>{x}</x>", f"  <y>{y}</y>",
            f"  <width>{w}</width>", f"  <height>{h}</height>", " </rect>", "</property>"]


def _prop_lines(name: str, kind: str, value) -> list[str]:
    if kind == "bool":
        v = "true" if value else "false"
    elif kind == "number":
        v = str(int(value or 0))
    else:
        v = X.escape_text(str(value))
    return [f'<property name="{name}">', f" <{kind}>{v}</{kind}>", "</property>"]


def _new_widget_lines(c: Control, kids: dict, in_layout: bool) -> list[str]:
    cls = c.props.get("NativeClass") or TYPE2QT.get(c.type, "QWidget")
    name = c.name
    lines = [f'<widget class="{cls}" name="{X.escape_attr(name)}">']
    body = []
    if not in_layout and not c.ctype.nonvisual:
        body += _rect_lines(int(c.props.get("Left", 0)), int(c.props.get("Top", 0)),
                            int(c.props.get("Width", 75)), int(c.props.get("Height", 23)))
    if c.type == "GroupBox":
        body += _prop_lines("title", "string", c.props.get("Text", ""))
    elif c.ctype.has_text and cls not in NO_TEXT and c.props.get("Text", "") != "":
        body += _prop_lines(TEXT_PROP.get(cls, "text"), "string", c.props.get("Text", ""))
    defaults = c.ctype.default_props(name)
    for mp, (up, kind) in SIMPLE.items():
        if mp in c.props and c.props[mp] != defaults.get(mp):
            body += _prop_lines(up, kind, c.props[mp])
    if c.type in ("ComboBox", "ListBox"):
        for it in [s for s in str(c.props.get("Items", "")).split(";") if s]:
            body += ["<item>", ' <property name="text">', f"  <string>{X.escape_text(it)}</string>",
                     " </property>", "</item>"]
    if c.type == "TabControl":
        pages = [s for s in str(c.props.get("TabPages", "")).split(";")] or ["Tab 1"]
        for i, title in enumerate(pages):
            body += [f'<widget class="QWidget" name="{X.escape_attr(name)}_page{i + 1}">',
                     ' <attribute name="title">', f"  <string>{X.escape_text(title)}</string>",
                     " </attribute>"]
            for k in kids.get(name, []):
                if int(k.props.get("TabPage", 0) or 0) == i:
                    body += [" " + ln for ln in _new_widget_lines(k, kids, False)]
            body += ["</widget>"]
    else:
        for k in kids.get(name, []):
            body += _new_widget_lines(k, kids, False)
    return lines + [" " + ln for ln in body] + ["</widget>"]


def write_ui(path: Path, form: Form) -> list[str]:
    """Write the changes of *form* (vs the file on disk) into the .ui file. Returns notes."""
    path = Path(path)
    old, ctx = read_ui(path, live=True)           # same geometry source as when the form was loaded
    notes: list[str] = []
    patch = X.Patch(ctx.data)
    old_by_id = {c.props.get("NativeId"): c for c in old.controls if c.props.get("NativeId")}
    seen_ids: set = set()
    new_ctrls: list[Control] = []
    kept: dict[str, Control] = {}
    for c in form.controls:
        nid = c.props.get("NativeId")
        if nid and nid in old_by_id and nid not in seen_ids and nid in ctx.widgets:
            seen_ids.add(nid)
            kept[nid] = c
        else:
            new_ctrls.append(c)
    removed = [nid for nid in old_by_id if nid not in kept]
    removed_nodes = {id(ctx.widgets[n]) for n in removed if n in ctx.widgets}

    def under_removed(node: X.XNode) -> bool:
        return any(id(a) in removed_nodes for a in node.ancestors())

    # --- form
    top = ctx.top
    if form.props.get("Text") != old.props.get("Text"):
        _set_prop(patch, top, "windowTitle", "string", form.props.get("Text", ""))
    if (form.props.get("Width"), form.props.get("Height")) != (old.props.get("Width"), old.props.get("Height")):
        g = _value(_prop(top, "geometry")) or (0, 0, 0, 0)
        _set_rect(patch, top, (g[0], g[1], int(form.props["Width"]), int(form.props["Height"])))
    # --- removed
    for nid in removed:
        w = ctx.widgets.get(nid)
        if w is None or under_removed(w):
            continue
        item = ctx.in_layout.get(nid)
        patch.remove(item if item is not None else w)
        notes.append(f"{path.name}: removed {nid}")
    renames: dict[str, str] = {}
    # --- changed
    for nid, c in kept.items():
        w = ctx.widgets[nid]
        if under_removed(w):
            continue
        o = old_by_id[nid]
        cls = w.get("class", "")
        if c.name != nid:
            patch.set_attr(w, "name", c.name)
            renames[nid] = c.name
        if c.props.get("Parent", "") != o.props.get("Parent", "") or \
                int(c.props.get("TabPage", 0) or 0) != int(o.props.get("TabPage", 0) or 0):
            notes.append(f"{path.name}: {c.name} was moved to another container - not written "
                         "(move it in Qt Designer, or delete and re-add it)")
        geo_new = tuple(int(c.props.get(k, 0) or 0) for k in ("Left", "Top", "Width", "Height"))
        geo_old = tuple(int(o.props.get(k, 0) or 0) for k in ("Left", "Top", "Width", "Height"))
        if geo_new != geo_old and not c.ctype.nonvisual:
            if c.props.get("NativeLayout"):
                notes.append(f"{path.name}: {c.name} is managed by a layout - its position/size was not written")
            else:
                _set_rect(patch, w, geo_new)
        if c.ctype.has_text and c.props.get("Text") != o.props.get("Text") and cls not in NO_TEXT:
            pname = TEXT_PROP.get(cls, "text")
            if cls in ("QTextEdit", "QTextBrowser") and _prop(w, "html") is not None:
                patch.remove(_prop(w, "html"))
                notes.append(f"{path.name}: {c.name}: rich text (html) replaced by plain text")
            _set_prop(patch, w, pname, "string", c.props.get("Text", ""))
        for mp, (up, kind) in SIMPLE.items():
            if mp in c.props and c.props.get(mp) != o.props.get(mp):
                k = kind
                pn = _prop(w, up)
                if pn is not None and pn.children and pn.children[0].tag == "double":
                    k = "double"
                _set_prop(patch, w, up, k, c.props.get(mp))
        if c.type in ("ComboBox", "ListBox") and c.props.get("Items", "") != o.props.get("Items", ""):
            for it in w.findall("item"):
                patch.remove(it)
            lines = []
            for s in [s for s in str(c.props.get("Items", "")).split(";") if s]:
                lines += ["<item>", ' <property name="text">', f"  <string>{X.escape_text(s)}</string>",
                          " </property>", "</item>"]
            if lines:
                first_widget = next((ch for ch in w.children if ch.tag not in ("property", "attribute", "item")),
                                    None)
                patch.append_child(w, lines, before=first_widget)
        if c.type in ("MenuStrip", "ToolStrip") and c.props.get("Items") != o.props.get("Items"):
            notes.append(f"{path.name}: menu/tool bar edits are not written to .ui files yet - edit them in "
                         "Qt Designer")
        if c.type == "TabControl" and c.props.get("TabPages") != o.props.get("TabPages"):
            pages = [ch for ch in w.children if ch.tag == "widget"]
            titles = str(c.props.get("TabPages", "")).split(";")
            for pg, title in zip(pages, titles):
                t = pg.find("attribute", name="title")
                if t is not None and t.children and t.children[0].text != title:
                    patch.set_text(t.children[0], title)
            if len(titles) != len(pages):
                notes.append(f"{path.name}: {c.name}: adding/removing tab pages is not written - edit in Qt Designer")
    # --- renames in connections / tab stops / buddies
    if renames:
        for tag in ("sender", "receiver", "tabstop", "cstring"):
            for n in ctx.root.iter(tag):
                if n.text in renames and not under_removed(n):
                    if tag == "cstring" and (n.parent is None or n.parent.get("name") != "buddy"):
                        continue
                    patch.set_text(n, renames[n.text])
    # --- new controls
    if new_ctrls:
        new_names = {c.name for c in new_ctrls}
        kids: dict[str, list] = {}
        roots: list[Control] = []
        for c in new_ctrls:
            par = c.props.get("Parent", "")
            if par in new_names:
                kids.setdefault(par, []).append(c)
            else:
                roots.append(c)
        for c in roots:
            if c.ctype.nonvisual:
                notes.append(f"{path.name}: {c.type} {c.name} has no .ui equivalent - not written")
                continue
            par = c.props.get("Parent", "")
            # the native name of the parent (it may have been renamed in the designer)
            par_id = next((nid for nid, k in kept.items() if k.name == par), par)
            key = par_id
            if par_id and old_by_id.get(par_id) is not None and old_by_id[par_id].type == "TabControl":
                key = f"{par_id}#{int(c.props.get('TabPage', 0) or 0)}"
            host = ctx.hosts.get(key) or (ctx.hosts.get(par_id) if par_id else ctx.hosts.get(""))
            if host is None:
                notes.append(f"{path.name}: no place for new control {c.name} (parent {par})")
                continue
            layout = host.find("layout")
            if layout is not None:
                lines = _new_widget_lines(c, kids, True)
                cls = layout.get("class", "")
                attrs = ""
                if cls in ("QGridLayout", "QFormLayout"):
                    rows = [int(i.get("row", 0) or 0) for i in layout.findall("item")]
                    attrs = f' row="{max(rows) + 1 if rows else 0}" column="0"'
                    if cls == "QFormLayout":
                        attrs += ' colspan="2"'
                patch.append_child(layout, [f"<item{attrs}>"] + [" " + ln for ln in lines] + ["</item>"])
                notes.append(f"{path.name}: added {c.name} at the end of layout {layout.get('name', '')}")
            else:
                before = None
                patch.append_child(host, _new_widget_lines(c, kids, False), before=before)
                notes.append(f"{path.name}: added {c.name}")
    if not patch.edits:
        return notes
    out = patch.apply()
    X.parse(out)                                    # never write a broken file
    path.write_bytes(out)
    notes.append(f"{path.name}: saved ({len(patch.edits)} change{'s' if len(patch.edits) != 1 else ''}, "
                 "everything else kept byte for byte)")
    return notes


def _set_prop(patch: X.Patch, w: X.XNode, pname: str, kind: str, value) -> None:
    p = _prop(w, pname)
    if kind == "bool":
        text = "true" if value else "false"
    elif kind == "number":
        text = str(int(value or 0))
    else:
        text = str(value if value is not None else "")
    if p is not None and p.children:
        patch.set_text(p.children[0], text)
        return
    first_non_prop = next((ch for ch in w.children if ch.tag not in ("property",)), None)
    patch.append_child(w, _prop_lines(pname, kind, value), before=first_non_prop)


def _set_rect(patch: X.Patch, w: X.XNode, g) -> None:
    p = _prop(w, "geometry")
    if p is not None and p.children and p.children[0].tag == "rect":
        r = p.children[0]
        for key, v in zip(("x", "y", "width", "height"), g):
            n = r.find(key)
            if n is not None and n.text.strip() != str(v):
                patch.set_text(n, str(v))
        return
    first = next((ch for ch in w.children), None)
    patch.append_child(w, _rect_lines(*g), before=first)


# ---------------------------------------------------------------- binding

class UiBinding(FormBinding):
    kind = "qt-ui"

    def __init__(self, name: str, native: Path, root: Path, code_candidates: list[Path] | None = None):
        super().__init__(name, native)
        self.root = root
        self.code_path = _find_code(native, root, code_candidates)
        self.ui_class = ""

    def load(self) -> Form:
        form, ctx = read_ui(self.native)
        self.ui_class = form.props.get("Name", "")
        self.notes += ctx.notes
        return form

    def write(self, form: Form) -> list[str]:
        return write_ui(self.native, form)

    # events -> Qt auto-connected slots on_<object>_<signal>
    def handler_name(self, form, ctrl, event: str) -> str:
        if ctrl is not None and ctrl.type in ("MenuStrip", "ToolStrip"):
            return f"on_{event}_triggered"
        owner = ctrl.name if ctrl is not None else form.name
        sig = EVENT2SIGNAL.get(event)
        if sig is None:
            sig = event[:1].lower() + event[1:]
        return f"on_{owner}_{sig}" if sig else f"on_{owner}_shown"

    def find_handler(self, code: str, name: str) -> int:
        for i, line in enumerate(code.splitlines()):
            if re.search(rf"(\bdef\s+|::){re.escape(name)}\s*\(", line):
                return i
        return -1

    def add_handler(self, code: str, name: str, form, args=None):
        found = self.find_handler(code, name)
        if found >= 0:
            return code, found
        cp = self.code_path
        lines = code.split("\n")
        if cp is not None and cp.suffix.lower() == ".py":
            idx = next((i for i, ln in enumerate(lines) if re.match(r"\s*class\s+\w+", ln) and
                        any(k in "\n".join(lines[i:i + 80]) for k in ("setupUi", "loadUi", "QUiLoader"))), -1)
            if idx < 0:
                idx = next((i for i, ln in enumerate(lines) if re.match(r"\s*class\s+\w+", ln)), -1)
            if idx < 0:
                return code, 0
            ind = len(lines[idx]) - len(lines[idx].lstrip())
            end = len(lines)
            for j in range(idx + 1, len(lines)):
                if lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) <= ind:
                    end = j
                    break
            while end > idx + 1 and not lines[end - 1].strip():
                end -= 1
            pad = " " * (ind + 4)
            new = ["", f"{pad}def {name}(self, *args):", f"{pad}    # Qt connects this slot automatically "
                   f"(QMetaObject.connectSlotsByName)", f"{pad}    pass"]
            lines[end:end] = new
            return "\n".join(lines), end + 3
        if cp is not None and cp.suffix.lower() in (".cpp", ".cxx", ".cc"):
            cls = self.ui_class or form.name
            lines += ["", f"void {cls}::{name}()", "{", "    ", "}"]
            self._declare_cpp_slot(cp, cls, name)
            return "\n".join(lines), len(lines) - 2
        return code, 0

    def _declare_cpp_slot(self, cpp: Path, cls: str, name: str) -> None:
        for h in (cpp.with_suffix(".h"), cpp.with_suffix(".hpp")):
            if not h.exists():
                continue
            from ._others_base import read_text_keep, write_text_keep
            text, enc, nl = read_text_keep(h)
            if re.search(rf"\b{re.escape(name)}\s*\(", text):
                return
            m = re.search(r"^([ \t]*)private\s+slots\s*:\s*$", text, re.M)
            if m:
                at = m.end()
                text = text[:at] + f"\n{m.group(1)}    void {name}();" + text[at:]
            else:
                m = re.search(rf"class\s+{re.escape(cls)}\b[^{{]*\{{", text)
                end = text.find("\n};", m.end()) if m else -1
                if end < 0:
                    return
                text = text[:end] + f"\n\nprivate slots:\n    void {name}();" + text[end:]
            write_text_keep(h, text, enc, nl)
            return


def _find_code(ui: Path, root: Path, candidates: list[Path] | None) -> Path | None:
    """The code file that uses the .ui: Python (loadUi / Ui_<Class> import) first, then C++."""
    stem = ui.stem
    pats = [f"{stem}.ui", f"ui_{stem}", f"Ui_{stem}"]
    try:
        cls = re.search(rb"<class>([^<]+)</class>", ui.read_bytes())
        if cls:
            pats.append(f"Ui_{cls.group(1).decode().strip()}")
    except OSError:
        pass
    files = candidates if candidates is not None else \
        [root / f for f in source_files(root, (".py", ".cpp", ".cxx", ".cc"), limit=800)]
    best = None
    for f in files:
        if f.name.lower().startswith("ui_"):
            continue                                # generated by uic
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(p in text for p in pats):
            if f.suffix == ".py":
                return f
            best = best or f
    return best


def ui_bindings(adapter: ForeignAdapter, ui_files: list[Path]) -> None:
    """Add a UiBinding for every .ui file (used by the CMake / Python adapters too)."""
    cands = [adapter.root / f for f in source_files(adapter.root, (".py", ".cpp", ".cxx", ".cc"), limit=800)]
    for u in ui_files:
        adapter.add_binding(UiBinding(Path(u).stem, Path(u), adapter.root, cands))


# ---------------------------------------------------------------- the adapter

def _pro_vars(text: str) -> dict[str, list[str]]:
    text = re.sub(r"\\\s*\n", " ", text)
    out: dict[str, list[str]] = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        m = re.match(r"([A-Za-z_][A-Za-z0-9_.]*)\s*(\+=|=|\*=)\s*(.*)$", line)
        if m:
            vals = m.group(3).split()
            if m.group(2) == "=":
                out[m.group(1)] = vals
            else:
                out.setdefault(m.group(1), []).extend(vals)
    return out


def project_python(root: Path) -> str:
    for d in (".venv", "venv", "env"):
        for exe in (Path(root) / d / "Scripts" / "python.exe", Path(root) / d / "bin" / "python"):
            if exe.exists():
                return str(exe)
    return sys.executable


class QtProjectAdapter(ForeignAdapter):
    kind = "qt"
    title = "Qt project"
    base_language = "python-qt"

    def scan(self) -> None:
        n = self.native
        suffix = n.suffix.lower()
        if suffix == ".pro":
            self.title = "qmake project"
            self.base_language = "cpp-bridge"
            v = _pro_vars(n.read_text(encoding="utf-8", errors="replace"))
            self.name = (v.get("TARGET") or [n.stem])[0]
            forms = [self.root / f for f in v.get("FORMS", [])]
            files = [n.name] + v.get("SOURCES", []) + v.get("HEADERS", []) + v.get("RESOURCES", []) + \
                v.get("OTHER_FILES", []) + v.get("DISTFILES", [])
            self.modules = [f.replace("\\", "/") for f in files if (self.root / f).exists()]
            ui_bindings(self, [f for f in forms if f.exists()])
            self.qmake = _which_any("qmake6", "qmake")
            self.targets = [RunTarget(self.name, "exe", {})]
            self.info.append(f"qmake: {self.qmake or 'not found (install Qt for C++ to build; the forms open anyway)'}")
            return
        if suffix == ".pyproject":
            self.title = "PySide project"
            try:
                d = json.loads(n.read_text(encoding="utf-8"))
                files = [str(f) for f in d.get("files", [])]
            except (OSError, ValueError):
                files = []
            self.name = n.stem
            self.modules = [n.name] + [f for f in files if not f.lower().endswith(".ui")]
            ui_bindings(self, [self.root / f for f in files if f.lower().endswith(".ui")])
            pys = [f for f in files if f.endswith(".py")]
            main = next((f for f in pys if Path(f).stem in ("main", "app", "__main__")), pys[0] if pys else "")
            if main:
                self.targets.append(RunTarget(main, "python", {"script": main}))
            self._preview_targets()
            return
        # a single .ui file: it and its sibling .ui files
        self.title = "Qt Designer forms"
        self.name = n.stem if n.is_file() else self.root.name
        uis = sorted(self.root.glob("*.ui"))
        if n.is_file() and n in uis:
            uis.remove(n)
            uis.insert(0, n)
        ui_bindings(self, uis)
        self.modules = [f for f in source_files(self.root, (".py", ".cpp", ".h", ".hpp", ".qrc", ".pro", ".txt",
                                                            ".toml", ".pyproject"), limit=300)
                        if "/" not in f]
        for b in self.bindings.values():
            if b.code_path is not None and b.code_path.suffix == ".py":
                rel = self.rel(b.code_path)
                if not any(t.name == rel for t in self.targets):
                    self.targets.append(RunTarget(rel, "python", {"script": rel}))
        self._preview_targets()

    def _preview_targets(self):
        for name, b in self.bindings.items():
            self.targets.append(RunTarget(f"Preview {b.native.name}", "preview", {"ui": str(b.native)}))

    def tool(self) -> str:
        return project_python(self.root)

    def build_steps(self, target, debug):
        if self.native.suffix.lower() == ".pro" and target is not None and target.kind == "exe":
            if not self.qmake:
                raise RuntimeError("qmake was not found - install Qt (C++) to build this .pro project")
            b = self.state / "build"
            b.mkdir(exist_ok=True)
            env = tool_env([str(Path(self.qmake).parent)])
            return [Step([self.qmake, str(self.native), "-spec", "win32-g++", "CONFIG+=debug" if debug else
                          "CONFIG+=release"], b, env, "qmake"),
                    Step([str(Path(mingw_bin()) / "mingw32-make.exe") if mingw_bin() else "mingw32-make"],
                         b, env, "make")]
        return []

    def run_step(self, target, debug):
        if target is None:
            return None
        if target.kind == "python":
            return Step([project_python(self.root), str(self.root / target.data["script"])], self.root, {},
                        f"python {target.data['script']}")
        if target.kind == "preview":
            code = ("import sys; from PyQt6 import uic, QtWidgets; app = QtWidgets.QApplication(sys.argv); "
                    "w = uic.loadUi(sys.argv[1]); w.show(); sys.exit(app.exec())")
            return Step([sys.executable, "-c", code, target.data["ui"]], self.root, {}, f"preview {target.name}")
        if target.kind == "exe":
            b = self.state / "build"
            exe = next(iter(sorted(b.glob(f"**/{self.name}.exe"))), b / "debug" / f"{self.name}.exe")
            return Step([str(exe)], self.root, tool_env([str(Path(self.qmake).parent)] if self.qmake else []))
        return None

    def debug_session(self, win, target, pre):
        from ._others_base import ChainSession, debugpy_session, gdb_session
        if target.kind == "python":
            py = project_python(self.root)
            return ChainSession(pre, lambda: debugpy_session(win, py, self.root / target.data["script"], [],
                                                             self.root, None), win)
        if target.kind == "exe" and find_gdb():
            run = self.run_step(target, True)
            return ChainSession(pre, lambda: gdb_session(win, Path(run.argv[0]), [], self.root, run.env), win)
        return None

    def commands(self):
        out = []
        for name, b in self.bindings.items():
            gen = b.native.with_name(f"ui_{b.native.stem}.py")
            if gen.exists():
                uic = _which_any("pyside6-uic") or str(Path(sys.executable).parent / "pyside6-uic.exe")
                out.append((f"pyside6-uic {b.native.name} -> {gen.name}",
                            [Step([uic, str(b.native), "-o", str(gen)], self.root, {}, "pyside6-uic")]))
        try:
            from .vscode_folder import vscode_commands
            out += vscode_commands(self.root)
        except Exception:  # noqa: BLE001
            pass
        return out


def _which_any(*names) -> str:
    import shutil
    for n in names:
        w = shutil.which(n)
        if w:
            return w
    return ""


# ---------------------------------------------------------------- registration

def open_qt(win, path: Path) -> bool:
    adapter = QtProjectAdapter(Path(path))
    project = ForeignProject(adapter)
    return show_projects(win, [project], project.name, Path(path))


def probe_folder(folder: Path):
    for pat in ("*.pro", "*.pyproject"):
        hits = sorted(Path(folder).glob(pat))
        if hits:
            return hits[0]
    return None


def register() -> None:
    from ..features.foreign_projects import register_format
    register_format([".ui"], open_qt, "Qt Designer form", name="qt-ui", priority=0)
    register_format([".pro"], open_qt, "qmake project (Qt)", folder_probe=probe_folder, name="qmake", priority=2)
    register_format([".pyproject"], open_qt, "PySide project", name="pyside-project", priority=2)
