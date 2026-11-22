"""Run a RAD IDE "VB6 / BASIC" project.

    python -m radide.runtimes.vbrun <project-folder> [--debug]

Forms are built with Tkinter from the .form files (via the Python/Tk code
generator); VB event procedures (Command1_Click, Form_Load, Text1_Change,
Timer1_Timer, ...) are run by the BASIC interpreter. With --debug the RAD IDE
debug protocol is spoken on stdin/stdout (breakpoints from RADDBG_BP).
"""
from __future__ import annotations

import datetime as _dt
import os
import sys
import time
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox, simpledialog

from ..controls import CONTROL_TYPES, menu_leaves
from ..languages.python_tk import PythonTkPlugin
from ..model import Form, Project
from .vbinterp import (EMPTY, NOTHING, Cell, EndProgram, Interpreter, ModuleProxy,
                       VBRuntimeError, err, to_bool, to_num, to_str)
from .vbparse import VBSyntaxError, parse_module

TAG = "@@RADDBG@@"

from .vbevents import VB_EVENT, vb_event_name  # noqa: E402 - re-exported (no tkinter there)
_REEXPORTED = (VB_EVENT, vb_event_name)


def color_to_vb(c: str) -> int:
    if not c or not c.startswith("#"):
        return 0x8000000F
    r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    return r + g * 256 + b * 65536


def vb_to_color(v) -> str:
    if isinstance(v, str) and v.strip().startswith("#"):      # "#RRGGBB" (GUI Bridge languages, like radforms)
        s = v.strip()
        return s.upper() if len(s) == 7 else ""
    n = int(to_num(v))
    if n & 0x80000000:          # system colour
        return ""
    return f"#{n & 0xFF:02X}{(n >> 8) & 0xFF:02X}{(n >> 16) & 0xFF:02X}"


# ============================================================================ new controls (CONTRACTS 4)
_NA = object()          # "not handled here" marker of VBControl._ext_get / _ext_set / _ext_call


def _is_comp(type_name: str) -> bool:
    """A control of a (non built-in) component package (radide/components): VBControl reaches its runtime
    object's properties and methods by their manifest names (VB code and GUI Bridge SET/GET/CALL)."""
    try:
        from ..components import is_component_type
        return is_component_type(type_name)
    except Exception:  # noqa: BLE001
        return False


VB_TYPENAME = {"Button": "CommandButton", "RadioButton": "OptionButton", "GroupBox": "Frame",
               "NumericUpDown": "UpDown", "TrackBar": "Slider", "PictureBox": "PictureBox",
               "TabControl": "SSTab", "DataGridView": "MSFlexGrid", "DateTimePicker": "DTPicker",
               "OpenFileDialog": "CommonDialog", "SaveFileDialog": "CommonDialog", "ColorDialog": "CommonDialog",
               "FontDialog": "CommonDialog", "FolderBrowserDialog": "CommonDialog"}
VB_DEFAULT = {"TabControl": "tab", "TreeView": "text", "ListView": "text", "DataGridView": "text",
              "DateTimePicker": "value", "LinkLabel": "caption", "StatusBar": "simpletext",
              "OpenFileDialog": "filename", "SaveFileDialog": "filename", "ColorDialog": "color",
              "FontDialog": "fontname", "FolderBrowserDialog": "selectedpath", "ActiveX": "object"}
DIALOGS = ("OpenFileDialog", "SaveFileDialog", "ColorDialog", "FontDialog", "FolderBrowserDialog")
VB_EXT = {"TabControl", "TreeView", "ListView", "DataGridView", "DateTimePicker", "LinkLabel", "StatusBar",
          "ActiveX", *DIALOGS}


def _int(v, default=0):
    if v is EMPTY or v is None or v == "":
        return default
    return int(to_num(v))


def _given(v):
    return v is not EMPTY and v is not None and v != ""


class _VBNode:
    """TreeView Node: Text, Key, Index, FullPath, Parent, Children, Child, Expanded, Selected."""
    vb_typename = "Node"
    vb_default = "text"

    def __init__(self, ctrl, iid):
        self.ctrl, self.iid = ctrl, iid

    @property
    def _tree(self):
        return self.ctrl.w

    def vb_get(self, name):
        t = self._tree
        if not t.exists(self.iid):
            raise err(35605, "Control has been deleted")
        if name == "text":
            return t.item(self.iid, "text")
        if name == "key":
            return self.ctrl.node_key(self.iid)
        if name == "index":
            return t.Nodes.index(self.iid) + 1
        if name == "fullpath":
            parts, iid = [], self.iid
            while iid:
                parts.insert(0, t.item(iid, "text"))
                iid = t.parent(iid)
            return "\\".join(parts)
        if name == "parent":
            p = t.parent(self.iid)
            return _VBNode(self.ctrl, p) if p else NOTHING
        if name == "children":
            return len(t.get_children(self.iid))
        if name == "child":
            kids = t.get_children(self.iid)
            return _VBNode(self.ctrl, kids[0]) if kids else NOTHING
        if name == "expanded":
            return bool(t.item(self.iid, "open"))
        if name == "selected":
            return self.iid in t.selection()
        if name == "tag":
            return getattr(self, "_tag", "")
        raise err(438, f"Node doesn't support '{name}'")

    def vb_set(self, name, value):
        t = self._tree
        if name == "text":
            t.item(self.iid, text=to_str(value))
        elif name == "expanded":
            t.item(self.iid, open=to_bool(value))
        elif name == "selected":
            if to_bool(value):
                t.see(self.iid)
                t.selection_set(self.iid)
        elif name == "tag":
            self._tag = value
        else:
            raise err(438, f"Node doesn't support '{name}'")

    def vb_call(self, name, args):
        if name == "ensurevisible":
            self._tree.see(self.iid)
            return EMPTY
        return self.vb_get(name)


class _VBNodes:
    """TreeView.Nodes: Add([Relative], [Relationship], [Key], [Text]), Item, Remove, Clear, Count."""
    vb_typename = "Nodes"
    vb_default = "item"

    def __init__(self, ctrl):
        self.ctrl = ctrl

    def vb_items(self):
        return [_VBNode(self.ctrl, i) for i in self.ctrl.w.Nodes]

    def vb_get(self, name):
        if name == "count":
            return len(self.ctrl.w.Nodes)
        raise err(438, f"Nodes doesn't support '{name}'")

    def vb_index(self, args):
        return self.vb_call("item", args)

    def vb_call(self, name, args):
        c, t = self.ctrl, self.ctrl.w
        if name == "add":
            if len(args) == 1:                          # Nodes.Add "Text"
                rel, relation, key, text = EMPTY, EMPTY, EMPTY, args[0]
            else:
                rel, relation, key, text = (list(args) + [EMPTY] * 4)[:4]
            parent, index = "", "end"
            if _given(rel):
                ref = c.find_node(rel)
                rel_kind = _int(relation, 1)            # tvwFirst 0, tvwLast 1, tvwNext 2, tvwPrevious 3, tvwChild 4
                if rel_kind == 4:
                    parent = ref
                else:
                    parent = t.parent(ref)
                    sib = t.index(ref)
                    index = {0: 0, 1: "end", 2: sib + 1, 3: sib}.get(rel_kind, "end")
            if _given(key) and c.key_node(to_str(key)):
                raise err(35602, "Key is not unique in collection")
            label = to_str(text)
            base = f"{parent}/{label}" if parent else label
            iid, n = base, 2
            while t.exists(iid):
                iid, n = f"{base}#{n}", n + 1
            t.insert(parent, index, iid=iid, text=label)
            if parent:
                t.item(parent, open=True)
            if _given(key):
                c.keys[to_str(key).lower()] = iid
            return _VBNode(c, iid)
        if name == "item":
            return _VBNode(c, c.find_node(args[0]))
        if name == "remove":
            iid = c.find_node(args[0])
            t.delete(iid)
            c.keys = {k: v for k, v in c.keys.items() if t.exists(v)}
            return EMPTY
        if name == "clear":
            t.Clear()
            c.keys.clear()
            return EMPTY
        return self.vb_get(name)


class _VBListItem:
    """ListView ListItem: Text, SubItems(i), Key, Index, Selected."""
    vb_typename = "ListItem"
    vb_default = "text"

    def __init__(self, ctrl, iid):
        self.ctrl, self.iid = ctrl, iid

    def _row(self):
        lv = self.ctrl.w
        if not lv.exists(self.iid):
            raise err(35605, "Control has been deleted")
        return lv.index(self.iid)

    def vb_get(self, name):
        lv = self.ctrl.w
        if name == "text":
            return lv.GetCell(self._row(), 0)
        if name == "index":
            return self._row() + 1
        if name == "key":
            return self.ctrl.node_key(self.iid)
        if name == "selected":
            return self.iid in lv.selection()
        if name == "subitems":
            return _IndexedProp(self, "subitems")
        raise err(438, f"ListItem doesn't support '{name}'")

    def vb_set(self, name, value):
        lv = self.ctrl.w
        if name == "text":
            lv.SetCell(self._row(), 0, to_str(value))
        elif name == "selected":
            if to_bool(value):
                lv.selection_set(self.iid)
                lv.see(self.iid)
        else:
            raise err(438, f"ListItem doesn't support '{name}'")

    def vb_call(self, name, args):
        if name == "subitems":
            i = _int(args[0])
            if i < 1 or i >= len(self.ctrl.w.Columns):
                raise err(380, "Invalid property value (SubItems index)")
            return self.ctrl.w.GetCell(self._row(), i)
        if name == "ensurevisible":
            self.ctrl.w.see(self.iid)
            return EMPTY
        return self.vb_get(name)

    def vb_setindexed(self, name, args, value):
        if name != "subitems":
            raise err(438, f"'{name}' cannot be indexed")
        i = _int(args[0])
        if i < 1 or i >= len(self.ctrl.w.Columns):
            raise err(380, "Invalid property value (SubItems index)")
        self.ctrl.w.SetCell(self._row(), i, to_str(value))


class _VBListItems:
    """ListView.ListItems: Add([Index], [Key], [Text]), Item, Remove, Clear, Count (1-based)."""
    vb_typename = "ListItems"
    vb_default = "item"

    def __init__(self, ctrl):
        self.ctrl = ctrl

    def vb_items(self):
        return [_VBListItem(self.ctrl, i) for i in self.ctrl.w.get_children()]

    def vb_get(self, name):
        if name == "count":
            return self.ctrl.w.RowCount
        raise err(438, f"ListItems doesn't support '{name}'")

    def vb_index(self, args):
        return self.vb_call("item", args)

    def _iid(self, k):
        lv = self.ctrl.w
        if isinstance(k, str) and not k.strip().lstrip("-").isdigit():
            iid = self.ctrl.key_node(k)
            if iid is None:
                raise err(35601, f"Element not found: '{k}'")
            return iid
        i = _int(k)
        kids = lv.get_children()
        if not 1 <= i <= len(kids):
            raise err(35600, "Index out of bounds")
        return kids[i - 1]

    def vb_call(self, name, args):
        c, lv = self.ctrl, self.ctrl.w
        if name == "add":
            index, key, text = (list(args) + [EMPTY] * 3)[:3]
            if _given(key) and c.key_node(to_str(key)):
                raise err(35602, "Key is not unique in collection")
            pos = _int(index) - 1 if _given(index) else "end"
            iid = lv.insert("", pos, values=[to_str(text)] + [""] * (len(lv.Columns) - 1))
            if _given(key):
                c.keys[to_str(key).lower()] = iid
            return _VBListItem(c, iid)
        if name == "item":
            return _VBListItem(c, self._iid(args[0]))
        if name == "remove":
            lv.delete(self._iid(args[0]))
            return EMPTY
        if name == "clear":
            lv.Clear()
            c.keys.clear()
            return EMPTY
        return self.vb_get(name)


class _VBColumns:
    """ListView.ColumnHeaders: Add([Index], [Key], [Text], [Width]), Clear, Count, Item(i).Text."""
    vb_typename = "ColumnHeaders"

    def __init__(self, ctrl):
        self.ctrl = ctrl

    def vb_get(self, name):
        if name == "count":
            return len(self.ctrl.w.Columns)
        raise err(438, f"ColumnHeaders doesn't support '{name}'")

    def vb_call(self, name, args):
        lv = self.ctrl.w
        if name == "add":
            index, _key, text, width = (list(args) + [EMPTY] * 4)[:4]
            cols = list(lv.Columns) if getattr(self.ctrl, "_cols_set", True) else []
            self.ctrl._cols_set = True
            pos = _int(index) - 1 if _given(index) else len(cols)
            cols.insert(pos, to_str(text))
            lv.SetColumns(cols)
            if _given(width):
                lv.column(f"c{pos}", width=int(to_num(width) / self.ctrl._unit()))
            return EMPTY
        if name == "clear":
            self.ctrl._cols_set = False
            return EMPTY
        if name == "item":
            i = _int(args[0])
            return lv.Columns[i - 1]
        return self.vb_get(name)


class VBToolButton:
    """A ToolStrip button: Caption / Text, Enabled, ToolTipText, Visible."""
    vb_typename = "Button"
    vb_default = "caption"

    def __init__(self, form, name, button):
        self.form, self.vb_name, self.b = form, name, button

    def vb_get(self, name):
        if name in ("caption", "text"):
            return self.b.cget("text")
        if name == "enabled":
            return str(self.b.cget("state")) != "disabled"
        if name == "visible":
            return bool(self.b.winfo_manager())
        if name == "name":
            return self.vb_name
        raise err(438, f"Button doesn't support '{name}'")

    def vb_set(self, name, value):
        if name in ("caption", "text"):
            self.b.configure(text=to_str(value))
        elif name == "enabled":
            self.b.configure(state="normal" if to_bool(value) else "disabled")
        elif name == "visible":
            if to_bool(value):
                if not self.b.winfo_manager():
                    self.b.pack(side="left", padx=1, pady=1)
            else:
                self.b.pack_forget()
        elif name in ("tooltiptext", "tag", "value"):
            pass
        else:
            raise err(438, f"Button doesn't support '{name}'")

    def vb_call(self, name, args):
        return self.vb_get(name)


def _set_state(w, on):
    try:
        w.configure(state="normal" if on else "disabled")
        return
    except tk.TclError:
        pass
    try:
        w.state(["!disabled"] if on else ["disabled"])
    except (tk.TclError, AttributeError):
        for child in w.winfo_children():
            _set_state(child, on)


def _photo(path: str):
    """LoadPicture: Tk reads PNG/GIF; BMP/JPG/ICO (common in VB6 programs) go through Pillow."""
    try:
        return tk.PhotoImage(file=path)
    except tk.TclError:
        try:
            from PIL import Image, ImageTk
            return ImageTk.PhotoImage(Image.open(path))
        except Exception:  # noqa: BLE001
            raise err(481, f"Invalid picture: {path}") from None


# ============================================================================ controls
# ---------------------------------------------------------------- animations (radide/motion, Blend storyboards)
def _fx_of(vf: "VBForm"):
    """The form's animation runtime (_RadFx), created on demand (radide/motion/runtime_py.py)."""
    from ..motion.runtime_py import ensure_fx
    return ensure_fx(vf.ui, "tk")


def _animate_args(args) -> tuple[str, dict]:
    """VB ``Command1.Animate "slideIn", 600, "from=right"`` / bridge ``CALL Button1 Animate slideIn\t600``:
    the preset, then an optional duration (ms) and "name=value" options."""
    if not args:
        raise err(5, "Animate needs a preset name (e.g. \"shake\")")
    preset = to_str(args[0]).strip()
    opts: dict = {}
    for a in args[1:]:
        if a is EMPTY:
            continue
        text = to_str(a).strip()
        if "=" in text:
            k, _, v = text.partition("=")
            k, v = k.strip(), v.strip()
            try:
                opts[k] = int(v) if v.lstrip("-").isdigit() else float(v)
            except ValueError:
                opts[k] = {"true": True, "false": False}.get(v.lower(), v)
        elif "durationMs" not in opts:
            try:
                opts["durationMs"] = int(to_num(a))
            except (TypeError, ValueError):
                pass
    from ..motion.presets import CATALOG
    match = next((k for k in CATALOG if k.lower() == preset.lower()), None)
    if match is None:
        raise err(5, f"Unknown animation preset '{preset}' (one of: {', '.join(CATALOG)})")
    return match, opts


class VBStoryboard:
    """A storyboard (Objects and Timeline) or an animation of the Animations window as a VB object:
    ``Storyboard1.Begin``, ``fx1.Stop``, ``.Pause``, ``.Resume``, ``.Reverse``, ``.Seek ms``, ``.IsPlaying``."""
    vb_typename = "Storyboard"
    vb_default = "isplaying"

    def __init__(self, form: "VBForm", name: str, fx: bool):
        self.form, self.name, self.vb_name, self.fx = form, name, name, fx

    def _sb(self):
        if self.fx:
            return _fx_of(self.form).Storyboards.get(self.name)
        return getattr(self.form.ui, self.name, None)

    def vb_get(self, name):
        sb = self._sb()
        if sb is None:
            raise err(91, f"Storyboard '{self.name}' is not available")
        if name == "isplaying":
            return bool(sb.IsPlaying)
        if name == "duration":
            return sb.Duration
        if name == "position":
            return int(sb.Position)
        if name == "name":
            return self.name
        raise err(438, f"Storyboard doesn't support '{name}'")

    def vb_set(self, name, value):
        sb = self._sb()
        if sb is not None and name in ("repeatforever", "autoreverse"):
            setattr(sb, "RepeatForever" if name == "repeatforever" else "AutoReverse", to_bool(value))
            return
        raise err(438, f"Storyboard doesn't support property '{name}'")

    def vb_call(self, name, args):
        if self.fx and name in ("begin", "stop"):
            fx = _fx_of(self.form)
            (fx.Begin if name == "begin" else fx.Stop)(self.name)
            return EMPTY
        sb = self._sb()
        if sb is None:
            raise err(91, f"Storyboard '{self.name}' is not available")
        if name in ("begin", "stop", "pause", "resume", "reverse"):
            getattr(sb, name.capitalize())()
            return EMPTY
        if name == "seek":
            sb.Seek(to_num(args[0]) if args else 0)
            return EMPTY
        return self.vb_get(name)


class VBControl:
    vb_default = "text"

    def __init__(self, form: "VBForm", ctrl):
        self.form, self.ctrl = form, ctrl
        self.name = ctrl.name
        self.type = ctrl.type
        self.vb_typename = VB_TYPENAME.get(ctrl.type, ctrl.type)
        self.vb_name = self.name
        self.tag = ""
        self.keys: dict[str, str] = {}          # TreeView / ListView keys -> item ids
        self.cancel_error = False               # CommonDialog.CancelError
        if self.type in ("Label", "Button", "CheckBox", "RadioButton", "GroupBox"):
            self.vb_default = "caption" if self.type != "CheckBox" else "value"
        if self.type in ("ListBox",):
            self.vb_default = "text"
        if self.type in ("NumericUpDown", "TrackBar", "ProgressBar"):
            self.vb_default = "value"
        if self.type == "RadioButton":
            self.vb_default = "value"
        if self.type in VB_DEFAULT:
            self.vb_default = VB_DEFAULT[self.type]

    # -- helpers
    @property
    def w(self):
        return getattr(self.form.ui, self.name)

    def _var(self):
        return getattr(self.form.ui, f"{self.name}_var", None)

    def _unit(self):
        return self.form.unit

    def _relative(self):
        info = self.w.place_info()
        return any(float(info.get(k) or 0) for k in ("relx", "rely", "relwidth", "relheight"))

    def _place(self, **kw):
        """Move/resize (VB Left/Top/Width/Height): the control stops following its Anchor/Dock."""
        w = self.w
        info = w.place_info()
        if self._relative():
            w.update_idletasks()
            geo = {"x": w.winfo_x(), "y": w.winfo_y(), "width": w.winfo_width(), "height": w.winfo_height()}
        else:
            geo = {k: int(float(info.get(k, 0) or 0)) for k in ("x", "y", "width", "height")}
        geo.update(kw)
        w.place(relx=0, rely=0, relwidth="", relheight="", **geo)

    # -- protocol
    def vb_get(self, name):
        w, t = self.w, self.type
        if _is_comp(t):          # a component package control (radide/components)
            v = self._comp_get(name)
            if v is not _NA:
                return v
        if name == "maxlength":
            return getattr(self, "_maxlength", int(self.ctrl.props.get("MaxLength", 0) or 0))
        if name in ("datasource", "datamember", "datafield"):
            return getattr(self, "_" + name, NOTHING if name == "datasource" else "")
        if t in VB_EXT:
            v = self._ext_get(name)
            if v is not _NA:
                return v
        if t == "Timer":
            if name == "interval":
                return w.Interval
            if name == "enabled":
                return w.Enabled
            if name == "name":
                return self.name
            raise err(438, f"Timer doesn't support '{name}'")
        if name == "name":
            return self.name
        if name == "tag":
            return self.tag
        if name in ("caption", "text"):
            if t == "TextBox" and self.ctrl.props.get("Multiline"):
                return w.get("1.0", "end-1c").replace("\n", "\r\n")
            if t in ("TextBox", "ComboBox"):
                return self._var().get()
            if t == "ListBox":
                sel = w.curselection()
                return w.get(sel[0]) if sel else ""
            try:
                return w.cget("text")
            except tk.TclError:
                return ""
        if name == "value":
            if t == "CheckBox":
                return 1 if self._var().get() else 0
            if t == "RadioButton":
                return self.form.ui._radio.get() == self.name
            if t in ("NumericUpDown", "TrackBar"):
                return int(to_num(self._var().get() or 0))
            if t == "ProgressBar":
                return int(float(w.cget("value")))
        if name in ("min", "minimum"):
            return int(float(w.cget("from"))) if t in ("NumericUpDown", "TrackBar") else 0
        if name in ("max", "maximum"):
            if t == "ProgressBar":
                return int(float(w.cget("maximum")))
            return int(float(w.cget("to")))
        if name in ("left", "top", "width", "height"):
            info = w.place_info()
            key = {"left": "x", "top": "y"}.get(name, name)
            if info and not self._relative():
                v = int(float(info.get(key, 0) or 0))
            else:
                w.update_idletasks()
                v = getattr(w, f"winfo_{key}")()
            return v * self._unit()
        if name == "enabled":
            try:
                return str(w.cget("state")) != "disabled"
            except tk.TclError:
                try:
                    return not w.instate(["disabled"])
                except (tk.TclError, AttributeError):
                    return True
        if name == "visible":
            return bool(w.winfo_manager())
        if name in ("x1", "x2", "y1", "y2") and t == "Panel":      # VB6 Line control (drawn as a Panel)
            if name in ("x1", "x2"):
                left = self.vb_get("left")
                return left if name == "x1" else left + self.vb_get("width")
            top = self.vb_get("top")
            return top if name == "y1" else top + self.vb_get("height")
        if name == "backcolor" or (name in ("fillcolor", "bordercolor") and t == "Panel"):
            try:
                return color_to_vb(self._hex(w.cget("bg")))
            except tk.TclError:
                return 0x8000000F
        if name == "forecolor":
            try:
                return color_to_vb(self._hex(w.cget("fg")))
            except tk.TclError:
                return 0
        if name == "listcount":
            return int(w.size()) if t == "ListBox" else len(w.cget("values") or ())
        if name == "listindex":
            if t == "ListBox":
                sel = w.curselection()
                return sel[0] if sel else -1
            return w.current()
        if name == "newindex":
            return getattr(self, "_newindex", self.vb_get("listcount") - 1)
        if name == "itemdata" and t in ("ListBox", "ComboBox"):
            return _IndexedProp(self, "itemdata")
        if name in ("selstart", "sellength", "seltext") and t == "TextBox":
            return self._sel_get(name)
        if name == "selstart":
            return 0
        if name in ("interval",):
            return self._timer().Interval
        if name == "hwnd":
            return w.winfo_id()
        if name == "font":
            return self
        if name in ("fontsize", "size"):
            return self.ctrl.props.get("FontSize", 9)
        if name in ("fontbold", "bold"):
            return bool(self.ctrl.props.get("FontBold"))
        if name in ("fontname",):
            return self.ctrl.props.get("FontName", "Segoe UI")
        if name == "tooltiptext":
            return self.ctrl.props.get("ToolTip", "")
        if name == "list":
            return _IndexedProp(self, "list")
        if name == "multiline":
            return bool(self.ctrl.props.get("Multiline"))
        if name == "locked":
            return bool(self.ctrl.props.get("ReadOnly"))
        raise err(438, f"Object doesn't support property or method '{name}' ({self.name})")

    @staticmethod
    def _hex(c):
        try:
            r, g, b = (x // 257 for x in tk._default_root.winfo_rgb(c))
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:  # noqa: BLE001
            return ""

    def _timer(self):
        return getattr(self.form.ui, self.name)

    # -- TextBox SelStart / SelLength / SelText (VB offsets: a line break of a multi-line box counts 2, CR LF)
    def _sel_range(self):
        """(start, end) of the selection in VB offsets; no selection = (caret, caret)."""
        w = self.w
        if self.ctrl.props.get("Multiline"):
            def off(idx):
                s = w.get("1.0", idx)
                return len(s) + s.count("\n")
            r = w.tag_ranges("sel")
            return (off(r[0]), off(r[1])) if r else (off("insert"),) * 2
        try:
            if w.selection_present():
                return int(w.index("sel.first")), int(w.index("sel.last"))
        except tk.TclError:
            pass
        i = int(w.index("insert"))
        return i, i

    def _tk_index(self, vb_off: int):
        """VB offset -> Tk index of a multi-line box ("1.0 + N chars")."""
        text, chars, pos = self.w.get("1.0", "end-1c"), 0, 0
        for ch in text:
            step = 2 if ch == "\n" else 1
            if pos + step > vb_off:
                break
            pos += step
            chars += 1
        return f"1.0 + {chars} chars"

    def _sel_get(self, name):
        a, b = self._sel_range()
        if name == "selstart":
            return a
        if name == "sellength":
            return b - a
        w = self.w
        if self.ctrl.props.get("Multiline"):
            return w.get(self._tk_index(a), self._tk_index(b)).replace("\n", "\r\n")
        return w.get()[a:b]

    def _sel_set(self, name, value):
        w = self.w
        multi = bool(self.ctrl.props.get("Multiline"))
        a, b = self._sel_range()
        if name == "seltext":
            s = to_str(value)
            state = str(w.cget("state"))
            w.configure(state="normal")
            if multi:
                s = s.replace("\r\n", "\n")
                w.delete(self._tk_index(a), self._tk_index(b))
                w.insert(self._tk_index(a), s)
                w.tag_remove("sel", "1.0", "end")
            else:
                w.delete(a, b)
                w.insert(a, s)
                w.selection_clear()
            w.configure(state=state)
            return
        n = max(0, int(to_num(value)))
        start, end = (n, n) if name == "selstart" else (a, a + n)
        if multi:
            w.tag_remove("sel", "1.0", "end")
            w.mark_set("insert", self._tk_index(end if name == "sellength" else start))
            if end > start:
                w.tag_add("sel", self._tk_index(start), self._tk_index(end))
                w.mark_set("insert", self._tk_index(start))   # SelStart stays the start of the selection
            w.see("insert")
        else:
            w.selection_clear()
            w.icursor(start)
            if end > start:
                w.selection_range(start, end)

    def vb_set(self, name, value):
        w, t = self.w, self.type
        if _is_comp(t) and self._comp_set(name, value):     # component package control
            return
        if name in ("datasource", "datamember", "datafield"):          # bound grids / controls (vbdata.py)
            if name == "datasource" and t == "DataGridView":
                from .vbdata import set_datasource
                set_datasource(self, value)
            else:
                setattr(self, "_" + name, to_str(value) if not hasattr(value, "vb_get") else value)
            return
        if name == "maxlength":
            self._maxlength = int(to_num(value))
            return
        if t in VB_EXT and self._ext_set(name, value) is not _NA:
            return
        if t == "Timer":
            tm = self._timer()
            if name == "interval":
                tm.Interval = int(to_num(value))
                if tm.Enabled:
                    tm.Enabled = True
                return
            if name == "enabled":
                tm.Enabled = to_bool(value)
                return
        if name == "tag":
            self.tag = value
            return
        if name in ("caption", "text"):
            s = to_str(value)
            if t == "TextBox" and self.ctrl.props.get("Multiline"):
                state = w.cget("state")
                w.configure(state="normal")
                w.delete("1.0", "end")
                w.insert("1.0", s.replace("\r\n", "\n"))
                w.configure(state=state)
            elif t in ("TextBox", "ComboBox"):
                self._var().set(s)
            elif t == "ListBox":
                items = w.get(0, "end")
                if s in items:
                    w.selection_clear(0, "end")
                    w.selection_set(items.index(s))
            else:
                w.configure(text=s)
            return
        if name == "value":
            if t == "CheckBox":
                self._var().set(int(to_num(value)) == 1)
                self.form.fire(self.name, "CheckedChanged")
            elif t == "RadioButton":
                if to_bool(value):
                    self.form.ui._radio.set(self.name)
                    self.form.fire(self.name, "CheckedChanged")
                elif self.form.ui._radio.get() == self.name:      # Option1.Value = False clears it
                    self.form.ui._radio.set("")
            elif t in ("NumericUpDown", "TrackBar"):
                self._var().set(int(to_num(value)))
                self.form.fire(self.name, "ValueChanged")
            elif t == "ProgressBar":
                w.configure(value=to_num(value))
            return
        if name in ("min", "minimum"):
            w.configure(**{"from_": to_num(value)}) if t != "ProgressBar" else None
            return
        if name in ("max", "maximum"):
            w.configure(maximum=to_num(value)) if t == "ProgressBar" else w.configure(to=to_num(value))
            return
        if name in ("left", "top", "width", "height"):
            key = {"left": "x", "top": "y"}.get(name, name)
            self._place(**{key: int(to_num(value) / self._unit())})
            return
        if name == "enabled":
            _set_state(w, to_bool(value))
            return
        if name == "visible":
            fx = self.form.ui.__dict__.get("_fx")
            if fx is not None and (fx._show.get(self.name) or fx._hide.get(self.name)):
                fx.SetVisible(self.name, to_bool(value))    # its "On show" / "On hide" animation
                return
            if to_bool(value):
                if w.winfo_manager():
                    return
                p = self.ctrl.props
                info = getattr(self, "_saved_place", None) or getattr(self.form.ui, "_places", {}).get(self.name) \
                    or {"x": p["Left"], "y": p["Top"], "width": p["Width"], "height": p["Height"]}
                w.place(**info)
            else:
                info = w.place_info()
                if info:
                    self._saved_place = {k: info[k] for k in ("x", "y", "width", "height", "relx", "rely",
                                                             "relwidth", "relheight", "bordermode") if k in info}
                w.place_forget()
            return
        if name in ("x1", "x2", "y1", "y2") and t == "Panel":      # VB6 Line: move one end, keep the other
            v = to_num(value)
            if name in ("x1", "x2"):
                a, b = self.vb_get("x1"), self.vb_get("x2")
                a, b = (v, b) if name == "x1" else (a, v)
                self.vb_set("left", min(a, b))
                self.vb_set("width", max(abs(b - a), self._unit()))
            else:
                a, b = self.vb_get("y1"), self.vb_get("y2")
                a, b = (v, b) if name == "y1" else (a, v)
                self.vb_set("top", min(a, b))
                self.vb_set("height", max(abs(b - a), self._unit()))
            return
        if name in ("fillcolor", "bordercolor") and t == "Panel":     # VB6 Shape / Line (drawn as a Panel)
            name = "backcolor"
        if name in ("fillstyle", "backstyle", "shape", "borderwidth", "drawmode") and t == "Panel":
            return
        if name in ("backcolor", "forecolor"):
            c = vb_to_color(value)
            try:
                w.configure(**{"bg" if name == "backcolor" else "fg": c or "SystemButtonFace"})
            except tk.TclError:
                pass
            return
        if name == "listindex":
            i = int(to_num(value))
            if t == "ListBox":
                w.selection_clear(0, "end")
                if i >= 0:
                    w.selection_set(i)
                    w.see(i)
            else:
                if i >= 0:
                    w.current(i)
                else:
                    self._var().set("")
            self.form.fire(self.name, "SelectedIndexChanged")
            return
        if name in ("fontsize", "size", "fontbold", "bold", "fontname", "fontitalic", "italic"):
            key = {"size": "FontSize", "bold": "FontBold", "italic": "FontItalic"}.get(name, None)
            key = key or {"fontsize": "FontSize", "fontbold": "FontBold", "fontname": "FontName",
                          "fontitalic": "FontItalic"}[name]
            self.ctrl.props[key] = to_num(value) if key == "FontSize" else (to_str(value) if key == "FontName"
                                                                           else to_bool(value))
            p = self.ctrl.props
            style = " ".join(s for s, on in (("bold", p.get("FontBold")), ("italic", p.get("FontItalic"))) if on)
            try:
                w.configure(font=(p.get("FontName") or "Segoe UI", int(p.get("FontSize", 9)), style))
            except tk.TclError:
                pass
            return
        if name == "tooltiptext":
            self.ctrl.props["ToolTip"] = to_str(value)
            return
        if name == "locked":
            self.ctrl.props["ReadOnly"] = to_bool(value)          # Locked reads back what was set
            try:
                w.configure(state="readonly" if to_bool(value) else "normal")
            except tk.TclError:
                pass
            return
        if name == "picture" and t == "PictureBox":
            path = to_str(value)
            if path:
                img = _photo(self.form.runtime.resolve(path))
                w.configure(image=img)
                setattr(self.form.ui, f"{self.name}_image", img)
            else:
                w.configure(image="")
            return
        if name in ("selstart", "sellength", "seltext") and t == "TextBox":
            self._sel_set(name, value)
            return
        if name in ("textalign", "alignment") and t in ("Label", "Button", "CheckBox", "RadioButton"):
            s = to_str(value).strip().lower()           # "Left" / "Center" / "Right" (+ "Top..") or VB 0 / 1 / 2
            side = {"0": "left", "1": "right", "2": "center"}.get(s) or \
                ("right" if "right" in s else "center" if "center" in s else "left")
            self.ctrl.props["TextAlign"] = side.capitalize()
            try:
                w.configure(anchor={"left": "w", "right": "e", "center": "center"}[side], justify=side)
            except tk.TclError:
                pass
            return
        if name in ("selstart", "sellength", "seltext", "tabindex", "tabstop", "mousepointer", "default",
                    "cancel", "appearance", "borderstyle", "sorted", "alignment", "autosize", "wordwrap"):
            return                       # accepted but not applicable
        raise err(438, f"Object doesn't support property '{name}' ({self.name})")

    def vb_call(self, name, args):
        w, t = self.w, self.type
        if _is_comp(t):          # a component package control: its methods / properties
            v = self._comp_call(name, args)
            if v is not _NA:
                return v
        if t in VB_EXT:
            v = self._ext_call(name, args)
            if v is not _NA:
                return v
        if name == "animate":                   # Command1.Animate "shake" (radide/motion presets)
            preset, opts = _animate_args(args)
            _fx_of(self.form).Animate(self.name, preset, **opts)
            return EMPTY
        if name == "additem":
            item = to_str(args[0])
            data = self._itemdata()
            if t == "ListBox":
                at = int(w.size()) if len(args) < 2 or not _given(args[1]) else int(to_num(args[1]))
                w.insert(at, item)
            else:
                vals = list(w.cget("values") or ())
                at = len(vals) if len(args) < 2 or not _given(args[1]) else int(to_num(args[1]))
                vals.insert(at, item)
                w.configure(values=vals)
            data.insert(at, 0)
            self._newindex = at
            return EMPTY
        if name == "itemdata" and t in ("ListBox", "ComboBox"):
            i = int(to_num(args[0]))
            data = self._itemdata()
            if not 0 <= i < len(data):
                raise err(381, "Invalid property array index (ItemData)")
            return data[i]
        if name == "removeitem":
            i = int(to_num(args[0]))
            data = self._itemdata()
            if 0 <= i < len(data):
                data.pop(i)
            if t == "ListBox":
                w.delete(i)
            else:
                vals = list(w.cget("values") or ())
                vals.pop(i)
                w.configure(values=vals)
            return EMPTY
        if name == "clear":
            if t in ("ListBox", "ComboBox"):
                self._items_data = []
            if t == "ListBox":
                w.delete(0, "end")
            elif t == "ComboBox":
                w.configure(values=[])
                self._var().set("")
            elif t == "TextBox":
                self.vb_set("text", "")
            return EMPTY
        if name == "list":
            i = int(to_num(args[0]))
            if t == "ListBox":
                return w.get(i)
            return (w.cget("values") or ())[i]
        if name == "setfocus":
            w.focus_set()
            return EMPTY
        if name == "refresh":
            w.update_idletasks()
            return EMPTY
        if name == "move":
            keys = ["left", "top", "width", "height"]
            for k, v in zip(keys, args):
                if v is not EMPTY:
                    self.vb_set(k, v)
            return EMPTY
        if name == "zorder":
            w.lift() if not args or to_num(args[0]) == 0 else w.lower()
            return EMPTY
        if name in ("start", "stop") and t == "Timer":
            self._timer().Enabled = name == "start"
            return EMPTY
        return self.vb_get(name)

    # -- component package controls (radide/components): the runtime object's members by manifest name
    def _comp_member(self, name):
        try:
            from ..components.targets import member
            return member(self.type, name)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _comp_value(v):
        if isinstance(v, bool) or v is None or isinstance(v, (int, float, str)):
            return EMPTY if v is None else v
        return to_str(v)

    def _comp_get(self, name):
        m = self._comp_member(name)
        obj = getattr(self.form.ui, self.name, None)
        if m is None or obj is None:
            return _NA
        kind, real, _ptype = m
        try:
            v = getattr(obj, real)
        except AttributeError:
            return _NA
        if kind == "method" and callable(v):
            return self._comp_value(v())
        return self._comp_value(v() if callable(v) else v)

    def _comp_set(self, name, value) -> bool:
        m = self._comp_member(name)
        obj = getattr(self.form.ui, self.name, None)
        if m is None or obj is None or m[0] != "prop":
            return False
        _kind, real, ptype = m
        if ptype in ("int",):
            value = int(to_num(value))
        elif ptype in ("float",):
            value = float(to_num(value))
        elif ptype in ("bool",):
            value = bool(to_bool(value))
        elif ptype not in ("custom",):
            value = to_str(value)
        elif not isinstance(value, (int, float, bool)):
            value = to_str(value)
        setattr(obj, real, value)
        return True

    def _comp_call(self, name, args):
        m = self._comp_member(name)
        obj = getattr(self.form.ui, self.name, None)
        if m is None or obj is None:
            return _NA
        kind, real, _ptype = m
        attr = getattr(obj, real, None)
        if kind == "method" and callable(attr):
            return self._comp_value(attr(*[a if isinstance(a, (int, float, bool)) else to_str(a) for a in args]))
        return _NA

    # -- new controls (TabControl, TreeView, ListView, DataGridView, DateTimePicker, dialogs, ...)
    def node_key(self, iid):
        for k, v in self.keys.items():
            if v == iid:
                return k
        return ""

    def key_node(self, key):
        iid = self.keys.get(str(key).lower())
        return iid if iid is not None and self.w.exists(iid) else None

    def find_node(self, ref):
        """Node / ListItem object, key, 1-based index or path -> item id."""
        if isinstance(ref, (_VBNode, _VBListItem)):
            return ref.iid
        t = self.w
        if isinstance(ref, str) and not ref.strip().lstrip("-").isdigit():
            iid = self.key_node(ref)
            if iid is None and t.exists(ref):
                iid = ref
            if iid is None:
                raise err(35601, f"Element not found: '{ref}'")
            return iid
        i = _int(ref)
        items = t.Nodes if self.type == "TreeView" else list(t.get_children())
        if not 1 <= i <= len(items):
            raise err(35600, "Index out of bounds")
        return items[i - 1]

    def _grid_cell(self, args):
        r, c = _int(args[0]), _int(args[1])
        g = self.w
        if not (0 <= r <= g.RowCount) or not (0 <= c < g.ColumnCount):
            raise err(381, "Subscript out of range (TextMatrix)")
        return r, c

    def _grid_resize(self, rows=None, cols=None):
        g = self.w
        if cols is not None:
            cols = max(1, cols)
            names = list(g.Columns[:cols]) + [f"Column{i + 1}" for i in range(len(g.Columns), cols)]
            g.SetColumns(names)
        if rows is not None:
            want = max(0, rows - 1)                     # row 0 = the header row (FixedRows = 1)
            while g.RowCount < want:
                g.AddRow()
            while g.RowCount > want:
                g.RemoveRow(g.RowCount - 1)

    def _dialog_result(self, method):
        res = getattr(self.w, method)()
        if res != "OK" and self.cancel_error:
            raise err(32755, "Cancel was selected.")
        return res

    def _ext_get(self, name):
        w, t = self.w, self.type
        if t in DIALOGS:
            if name == "name":
                return self.name
            if name == "tag":
                return self.tag
            if name == "filename":
                return w.FileName
            if name == "filetitle":
                return os.path.basename(w.FileName)
            if name == "filter":
                return w.Filter
            if name in ("title", "dialogtitle"):
                return w.Title
            if name in ("initdir", "initialdirectory"):
                return w.InitialDirectory
            if name == "color":
                return color_to_vb(w.Color)
            if name == "fontname":
                return w.FontName
            if name == "fontsize":
                return w.FontSize
            if name in ("selectedpath", "path"):
                return w.SelectedPath
            if name == "cancelerror":
                return self.cancel_error
            if name in ("flags", "filterindex", "fontbold", "fontitalic", "fontunderline", "fontstrikethru"):
                return 0
            raise err(438, f"CommonDialog doesn't support '{name}'")
        if t == "TabControl":
            if name in ("tab", "selectedindex"):
                return w.index("current") if w.tabs() else -1
            if name in ("tabs", "tabcount"):
                return len(w.tabs())
            if name in ("caption", "text"):
                return w.tab("current", "text") if w.tabs() else ""
            if name in ("tabcaption", "taburl"):
                return _IndexedProp(self, "tabcaption")
        elif t == "TreeView":
            if name == "nodes":
                return _VBNodes(self)
            if name == "selecteditem":
                sel = w.selection()
                return _VBNode(self, sel[0]) if sel else NOTHING
            if name in ("text", "caption"):
                return w.SelectedText
            if name == "pathseparator":
                return "\\"
        elif t == "ListView":
            if name == "listitems":
                return _VBListItems(self)
            if name == "columnheaders":
                return _VBColumns(self)
            if name == "selecteditem":
                sel = w.selection()
                if not sel and w.get_children():          # VB6: the first item is the focused/selected one
                    sel = (w.get_children()[0],)
                return _VBListItem(self, sel[0]) if sel else NOTHING
            if name in ("text", "caption"):
                sel = w.selection()
                return w.GetCell(w.index(sel[0]), 0) if sel else ""
            if name == "listindex":
                return w.SelectedIndex
            if name == "view":
                return 3 if str(w.cget("show")) == "headings" else 2      # lvwReport / lvwList
        elif t == "DataGridView":
            if name == "rows":
                return w.RowCount + 1
            if name == "cols":
                return w.ColumnCount
            if name == "fixedrows":
                return 1
            if name == "fixedcols":
                return 0
            if name == "row":
                return w.CurrentRow + 1 if w.CurrentRow >= 0 else 0
            if name == "col":
                return max(0, w.CurrentColumn)
            if name == "textmatrix":
                return _IndexedProp(self, "textmatrix")
            if name in ("text", "caption"):
                r = self._ext_get("row")
                return self.vb_call("textmatrix", [r, self._ext_get("col")])
            if name in ("readonly", "locked"):
                return bool(w.ReadOnly)
        elif t == "DateTimePicker":
            if name == "value":
                return w.DateTime
            if name in ("text", "caption"):
                return w.get()
            if name in ("year", "month", "day", "hour", "minute", "second"):
                return getattr(w.DateTime, name)
            if name == "format":
                return {"Long": 0, "Short": 1, "Time": 2}.get(w.Format, 1)
        elif t == "StatusBar":
            if name in ("simpletext", "text", "caption"):
                return w.cget("text")
        elif t == "LinkLabel":
            if name == "linkcolor":
                return color_to_vb(self._hex(w.cget("fg")))
        elif t == "ActiveX":
            if name == "progid":
                return self.ctrl.props.get("ProgID", "")
            if name == "object":
                if getattr(self, "_com", None) is None:
                    self._com = self.form.runtime.create_object(self.ctrl.props.get("ProgID", ""))
                return self._com
        return _NA

    def _ext_set(self, name, value):
        w, t = self.w, self.type
        if t in DIALOGS:
            if name == "tag":
                self.tag = value
            elif name == "filename":
                w.FileName = to_str(value)
            elif name == "filter":
                w.Filter = to_str(value)
            elif name in ("title", "dialogtitle"):
                w.Title = to_str(value)
            elif name in ("initdir", "initialdirectory"):
                w.InitialDirectory = to_str(value)
            elif name == "color":
                s = to_str(value).strip()           # "#RRGGBB" (GUI Bridge languages) or a VB colour number
                w.Color = s.upper() if s.startswith("#") and len(s) == 7 else (vb_to_color(value) or "#000000")
            elif name == "fontname":
                w.FontName = to_str(value)
            elif name == "fontsize":
                w.FontSize = int(to_num(value))
            elif name in ("selectedpath", "path"):
                w.SelectedPath = to_str(value)
            elif name == "cancelerror":
                self.cancel_error = to_bool(value)
            elif name in ("flags", "filterindex", "maxfilesize", "defaultext", "helpfile", "min", "max",
                          "fontbold", "fontitalic", "fontunderline", "fontstrikethru"):
                pass
            else:
                raise err(438, f"CommonDialog doesn't support '{name}'")
            return None
        if t == "TabControl":
            if name in ("tab", "selectedindex"):
                i = int(to_num(value))
                if not 0 <= i < len(w.tabs()):
                    raise err(380, "Invalid property value (Tab)")
                w.select(i)
                return None
            if name in ("caption", "text"):
                if w.tabs():
                    w.tab("current", text=to_str(value))
                return None
        elif t == "TreeView":
            if name in ("text", "caption"):
                return None
            if name in ("pathseparator", "linestyle", "style", "indentation", "labeledit", "sorted",
                        "hideselection"):
                return None
        elif t == "ListView":
            if name == "listindex":
                w.SelectedIndex = int(to_num(value))
                return None
            if name == "view":
                v = int(to_num(value))
                w.configure(show="headings" if v == 3 else "")
                w.configure(displaycolumns="#all" if v == 3 else ("c0",))
                return None
            if name in ("labeledit", "fullrowselect", "gridlines", "sorted", "hideselection"):
                return None
        elif t == "DataGridView":
            if name == "rows":
                self._grid_resize(rows=int(to_num(value)))
                return None
            if name == "cols":
                self._grid_resize(cols=int(to_num(value)))
                return None
            if name == "row":
                r = int(to_num(value))
                w.CurrentRow = r - 1
                if r >= 1:
                    w.SelectedIndex = r - 1
                return None
            if name == "col":
                w.CurrentColumn = int(to_num(value))
                return None
            if name in ("text", "caption"):
                self.vb_setindexed("textmatrix", [self._ext_get("row"), self._ext_get("col")], value)
                return None
            if name in ("readonly", "locked"):
                w.ReadOnly = to_bool(value)
                return None
            if name in ("fixedrows", "fixedcols", "colwidth", "gridlines", "allowuserresizing", "selectionmode",
                        "focusrect", "highlight", "scrollbars", "wordwrap", "redraw", "backcolorfixed",
                        "forecolorfixed", "backcolorsel", "forecolorsel", "gridcolor", "fillstyle", "mergecells",
                        "allowbigselection", "colsel", "rowsel", "toprow", "leftcol", "cellalignment",
                        "cellfontbold", "cellbackcolor", "cellforecolor", "allowupdate", "allowaddnew",
                        "allowdelete", "caption", "headlines", "rowheight", "datamember"):
                return None
            if name == "formatstring":
                heads = [h.lstrip("<^>").strip() for h in to_str(value).split(";")[0].split("|")]
                self._grid_resize(cols=len(heads))
                for i, h in enumerate(heads):
                    self._ext_setindexed("textmatrix", [0, i], h)
                return None
        elif t == "DateTimePicker":
            if name == "value":
                try:
                    w.Value = value if isinstance(value, _dt.datetime) else to_str(value)
                except ValueError:
                    raise err(380, f"Invalid property value: {to_str(value)!r}") from None
                return None
            if name in ("format", "customformat", "checkbox", "updown"):
                return None
        elif t == "StatusBar":
            if name in ("simpletext", "text", "caption"):
                w.configure(text=to_str(value))
                return None
            if name in ("style", "simplestyle"):
                return None
        elif t == "LinkLabel":
            if name == "linkcolor":
                w.configure(fg=vb_to_color(value) or "#0066CC")
                return None
        return _NA

    def _ext_call(self, name, args):
        w, t = self.w, self.type
        if t in DIALOGS:
            method = {"showopen": "ShowOpen", "showsave": "ShowSave", "showcolor": "ShowColor",
                      "showfont": "ShowFont", "showfolder": "ShowFolder", "showdialog": "ShowDialog"}.get(name)
            if method:
                return self._dialog_result(method)
            return self._ext_get(name)
        if t == "TabControl" and name == "tabcaption":
            i = _int(args[0])
            return w.tab(i, "text")
        if t == "TreeView" and name == "nodes" and args:
            return _VBNodes(self).vb_call("item", args)
        if t == "ListView" and name == "listitems" and args:
            return _VBListItems(self).vb_call("item", args)
        if t == "DataGridView":
            if name == "textmatrix":
                r, c = self._grid_cell(args)
                return w.Columns[c] if r == 0 else w.GetCell(r - 1, c)
            if name == "textarray":
                cols = max(1, w.ColumnCount)
                return self._ext_call("textmatrix", [_int(args[0]) // cols, _int(args[0]) % cols])
            if name == "colwidth":
                return int(w.column(f"c{_int(args[0])}", "width")) * 15
            if name in ("colalignment", "rowheight", "coldata", "rowdata", "colisvisible"):
                return 0
            if name == "additem":
                cells = to_str(args[0]).split("\t")
                # GUI Bridge clients send one cell per argument (CALL grid AddItem a<TAB>b<TAB>c): VB's
                # AddItem has at most (Item, Index), so 3+ arguments or a non-numeric 2nd one are cells
                if len(args) > 2 or (len(args) == 2 and _given(args[1])
                                     and not str(args[1]).strip().lstrip("-").isdigit()):
                    w.AddRow(*[to_str(a) for a in args])
                    return EMPTY
                if len(args) > 1 and _given(args[1]):
                    w.insert("", max(0, _int(args[1]) - 1), values=cells)
                else:
                    w.AddRow(*cells)
                return EMPTY
            if name == "removeitem":
                w.RemoveRow(_int(args[0]) - 1)
                return EMPTY
            if name == "clear":
                w.Clear()
                return EMPTY
        if t in ("TreeView", "ListView") and name == "clear":
            w.Clear()
            self.keys.clear()
            return EMPTY
        return _NA

    def _ext_setindexed(self, name, args, value):
        w, t = self.w, self.type
        if t == "DataGridView" and name in ("colwidth", "colalignment", "rowheight", "colformat", "coldata",
                                            "rowdata", "mergecol", "mergerow", "colisvisible"):
            if name == "colwidth" and 0 <= _int(args[0]) < w.ColumnCount:          # twips -> pixels
                w.column(f"c{_int(args[0])}", width=max(0, int(to_num(value) / 15)))
            elif name == "colalignment" and 0 <= _int(args[0]) < w.ColumnCount:
                a = _int(value)
                w.column(f"c{_int(args[0])}", anchor="w" if a in (0, 1, 2) else "center" if a in (3, 4, 5)
                         else "e" if a in (6, 7, 8) else "w")
            return True
        if t == "DataGridView" and name == "textarray":
            cols = max(1, w.ColumnCount)
            return self._ext_setindexed("textmatrix", [_int(args[0]) // cols, _int(args[0]) % cols], value)
        if t == "DataGridView" and name == "textmatrix":
            r, c = self._grid_cell(args)
            if r == 0:
                cols = list(w.Columns)
                cols[c] = to_str(value)
                w.Columns = cols
                w.heading(f"c{c}", text=cols[c])
            else:
                w.SetCell(r - 1, c, to_str(value))
            return True
        if t == "TabControl" and name == "tabcaption":
            w.tab(_int(args[0]), text=to_str(value))
            return True
        return False

    def _itemdata(self) -> list:
        """ListBox / ComboBox ItemData(), kept the same length as the list."""
        n = int(self.w.size()) if self.type == "ListBox" else len(self.w.cget("values") or ())
        data = getattr(self, "_items_data", None)
        if data is None:
            data = self._items_data = []
        if len(data) < n:
            data += [0] * (n - len(data))
        return data

    def vb_setindexed(self, name, args, value):
        if self.type in VB_EXT and self._ext_setindexed(name, args, value):
            return
        if name == "itemdata" and self.type in ("ListBox", "ComboBox"):
            i = int(to_num(args[0]))
            data = self._itemdata()
            if not 0 <= i < len(data):
                raise err(381, "Invalid property array index (ItemData)")
            data[i] = int(to_num(value))
            return
        if name == "list":
            i = int(to_num(args[0]))
            if self.type == "ListBox":
                self.w.delete(i)
                self.w.insert(i, to_str(value))
            return
        raise err(438, f"'{name}' cannot be indexed")


class ControlArray:
    """VB6 control array: Command1(0), Command1(1) ..."""
    vb_typename = "Object"

    def __init__(self, name):
        self.vb_name = name
        self.items: dict[int, VBControl] = {}

    def vb_index(self, args):
        i = int(to_num(args[0]))
        if i not in self.items:
            raise err(340, f"Control array element '{i}' doesn't exist ({self.vb_name})")
        return self.items[i]

    def vb_items(self):
        return [self.items[k] for k in sorted(self.items)]

    def vb_get(self, name):
        if name == "count":
            return len(self.items)
        if name == "ubound":
            return max(self.items)
        if name == "lbound":
            return min(self.items)
        raise err(343, f"Object '{self.vb_name}' is a control array - use {self.vb_name}(index).{name}")

    def vb_call(self, name, args):
        if name == "item":
            return self.vb_index(args)
        return self.vb_get(name)


class _IndexedProp:
    def __init__(self, ctrl, name):
        self.ctrl, self.name = ctrl, name
        self.vb_default = "item"

    def vb_call(self, _name, args):
        return self.ctrl.vb_call(self.name, args)

    def vb_get(self, name):
        raise err(438, name)


class VBMenuItem:
    vb_typename = "Menu"

    def __init__(self, form, name, menu, index):
        self.form, self.vb_name, self.menu, self.index = form, name, menu, index

    def vb_get(self, name):
        if name == "caption":
            return self.menu.entrycget(self.index, "label")
        if name == "enabled":
            return self.menu.entrycget(self.index, "state") != "disabled"
        if name == "checked":
            return bool(getattr(self, "_checked", False))
        if name == "visible":
            return True
        raise err(438, f"Menu doesn't support '{name}'")

    def vb_set(self, name, value):
        if name == "caption":
            self.menu.entryconfigure(self.index, label=to_str(value))
        elif name == "enabled":
            self.menu.entryconfigure(self.index, state="normal" if to_bool(value) else "disabled")
        elif name == "checked":
            self._checked = to_bool(value)
            label = self.menu.entrycget(self.index, "label").lstrip("✓ ")
            self.menu.entryconfigure(self.index, label=("✓ " if self._checked else "") + label)
        elif name == "visible":
            pass

    def vb_call(self, name, args):
        return self.vb_get(name)


# ============================================================================ forms
class VBForm:
    vb_typename = "Form"
    vb_default = "caption"

    def __init__(self, runtime: "Runtime", form: Form):
        self.runtime = runtime
        self.model = form
        self.name = form.name
        self.vb_name = form.name
        self.ui = None
        self.controls: dict[str, object] = {}
        self.unit = 15 if form.props.get("ScaleMode", "Pixel") == "Twip" else 1
        self.loaded = False

    # -- life cycle
    def load(self):
        if self.loaded:
            return
        self.loaded = True
        self.runtime.build_form(self)
        for c in self.model.controls:
            if c.type == "ToolStrip":
                for item, b in (getattr(self.ui, f"{c.name}_buttons", None) or {}).items():
                    self.controls[item.lower()] = VBToolButton(self, item, b)
                continue
            if c.type != "MenuStrip":
                vc = VBControl(self, c)
                self.controls[c.name.lower()] = vc
                arr = c.props.get("ArrayName")
                if arr:
                    ca = self.controls.setdefault(arr.lower(), ControlArray(arr))
                    ca.items[int(c.props.get("ArrayIndex", 0))] = vc
        try:                    # data sources (Data Sources window): Customers.MoveNext, Customers.Update ...
            from ..databinding_sql import vb_objects
            for k, v in vb_objects(self.ui).items():
                self.controls.setdefault(k, v)
        except ImportError:
            pass
        datas = []
        try:                    # VB6 Data / ADO Data controls, bound controls and grids (native .frm)
            from .vbdata import install
            datas = install(self)
        except Exception as ex:  # noqa: BLE001
            print(f"[VB6] data controls of {self.name}: {ex}", file=sys.stderr, flush=True)
        for sb in self.model.extra.get("storyboards") or []:      # Storyboard1.Begin
            nm = str(sb.get("name") or "") if isinstance(sb, dict) else ""
            if nm and hasattr(self.ui, nm):
                self.controls.setdefault(nm.lower(), VBStoryboard(self, nm, False))
        fxrt = self.ui.__dict__.get("_fx")                          # fx1.Begin (Animations window)
        for fx_id in (fxrt.Storyboards if fxrt is not None else ()):
            if str(fx_id).isidentifier():
                self.controls.setdefault(str(fx_id).lower(), VBStoryboard(self, fx_id, True))
        menu = self.model.menu()
        if menu is not None and hasattr(self.ui, menu.name):
            self._map_menu(getattr(self.ui, menu.name), menu.props.get("Items", []))
        self.runtime.fire(self, "Form", "Load")
        if datas and self.loaded:
            from .vbdata import after_load
            after_load(datas)

    def _map_menu(self, tkmenu, items):
        idx = 0
        for it in items:
            if it.get("Text") == "-":
                idx += 1
                continue
            if it.get("Items"):
                sub = tkmenu.nametowidget(tkmenu.entrycget(idx, "menu"))
                if it.get("Name"):
                    self.controls[it["Name"].lower()] = VBMenuItem(self, it["Name"], tkmenu, idx)
                self._map_menu(sub, it["Items"])
            elif it.get("Name"):
                self.controls[it["Name"].lower()] = VBMenuItem(self, it["Name"], tkmenu, idx)
            idx += 1

    def fire(self, ctrl_name: str, event: str, *args):
        self.runtime.fire(self, ctrl_name, event, *args)

    # -- protocol
    def vb_has(self, name):
        if name in self.controls:
            return True
        if self.loaded:
            return False
        names = {c.name.lower() for c in self.model.controls}
        names |= {str(c.props.get("ArrayName", "")).lower() for c in self.model.controls}
        return name in names

    def vb_get(self, name):
        if name in self.controls or not self.loaded:
            self.load()
            if name in self.controls:
                return self.controls[name]
        root = self.ui.root
        if name in ("caption", "text"):     # VB6 Caption / WinForms Text (the designer and SET Form1 Text)
            return root.title()
        if name == "name":
            return self.name
        if name in ("width", "height", "scalewidth", "scaleheight"):
            root.update_idletasks()
            return (root.winfo_width() if "width" in name else root.winfo_height()) * self.unit
        if name in ("left", "top"):
            return (root.winfo_x() if name == "left" else root.winfo_y()) * self.unit
        if name == "visible":
            return root.state() != "withdrawn"
        if name == "backcolor":
            return color_to_vb(VBControl._hex(root.cget("bg")))
        if name == "windowstate":
            return {"normal": 0, "iconic": 1, "zoomed": 2}.get(root.state(), 0)
        if name == "hwnd":
            return root.winfo_id()
        if name == "controls":
            return _ControlsColl(list(self.controls.values()))
        if name == "activecontrol":
            fw = root.focus_get()
            for c in self.controls.values():
                if isinstance(c, VBControl) and c.w is fw:
                    return c
            return NOTHING
        found, v = self._member(name, [])
        if found:
            return v
        raise err(438, f"Form doesn't support property or method '{name}'")

    def _member(self, name, args, value=_NA):
        """Public Sub / Function / Property and public variables of the form's own code (frmX.LoadGrid)."""
        it = self.runtime.interp
        st = it.modules.get(self.name.lower())
        if st is None:
            return False, None
        procs = st.mod.procs
        if value is not _NA:
            is_obj = hasattr(value, "vb_get")
            for key in ((f"set:{name}", f"let:{name}") if is_obj else (f"let:{name}", f"set:{name}")):
                if key in procs:
                    it.call_proc(st, procs[key], [*args, value], me=self)
                    return True, None
            if name in st.vars:
                it.assign_cell(st.vars[name], value, is_set=is_obj)
                return True, None
            return False, None
        for key in (name, f"get:{name}"):
            if key in procs:
                return True, it.call_proc(st, procs[key], list(args), me=self)
        if name in st.vars:
            v = st.vars[name].value
            if args and hasattr(v, "get") and type(v).__name__ == "VBArray":
                return True, v.get(list(args))
            return True, v
        return False, None

    def vb_set(self, name, value):
        self.load()
        if name == "text" and not self._member(name, [])[0]:
            name = "caption"                # WinForms Text = VB6 Caption (SET Form1 Text ... from the bridge)
        found, _v = self._member(name, [], value)
        if found and name not in ("caption", "width", "height", "left", "top", "backcolor", "visible",
                                  "windowstate"):
            return
        root = self.ui.root
        if name == "caption":
            root.title(to_str(value))
        elif name in ("width", "height"):
            root.update_idletasks()
            w, h = root.winfo_width(), root.winfo_height()
            v = int(to_num(value) / self.unit)
            root.geometry(f"{v if name == 'width' else w}x{v if name == 'height' else h}")
        elif name in ("left", "top"):
            x, y = root.winfo_x(), root.winfo_y()
            v = int(to_num(value) / self.unit)
            root.geometry(f"+{v if name == 'left' else x}+{v if name == 'top' else y}")
        elif name == "backcolor":
            root.configure(bg=vb_to_color(value) or "SystemButtonFace")
        elif name == "visible":
            self.vb_call("show" if to_bool(value) else "hide", [])
        elif name == "windowstate":
            root.state({0: "normal", 1: "iconic", 2: "zoomed"}.get(int(to_num(value)), "normal"))
        elif name in ("borderstyle", "mousepointer", "keypreview", "scalemode", "enabled", "icon"):
            pass
        else:
            raise err(438, f"Form doesn't support property '{name}'")

    def vb_call(self, name, args):
        if name == "show":
            self.load()
            root = self.ui.root
            root.deiconify()
            root.attributes("-alpha", 1.0)
            root.lift()
            if args and int(to_num(args[0])) == 1:        # vbModal
                if root is not self.runtime.root:
                    root.grab_set()
                    root.wait_window(root)
            return EMPTY
        if name == "hide":
            if self.loaded:
                self.ui.root.withdraw()
            return EMPTY
        if name == "load":
            self.load()
            return EMPTY
        if name == "unload":
            self.runtime.unload(self)
            return EMPTY
        if name == "refresh":
            if self.loaded:
                self.ui.root.update_idletasks()
            return EMPTY
        if name == "setfocus":
            self.ui.root.focus_force()
            return EMPTY
        if name == "animate":           # Form1.Animate "fadeIn"  /  Me.Animate "Command1", "shake"
            self.load()
            target = ""
            if len(args) >= 2 and to_str(args[0]).lower() in self.controls \
                    and isinstance(self.controls[to_str(args[0]).lower()], VBControl):
                target, args = self.controls[to_str(args[0]).lower()].name, list(args[1:])
            preset, opts = _animate_args(args)
            _fx_of(self).Animate(target, preset, **opts)
            return EMPTY
        if name in ("beginanimation", "stopanimation"):
            self.load()
            fx = _fx_of(self)
            ok = (fx.Begin if name == "beginanimation" else fx.Stop)(to_str(args[0]) if args else "")
            return bool(ok)
        if name in ("cls", "print", "move", "zorder", "circle", "line", "pset", "arrange", "printform"):
            return EMPTY
        if args:
            self.load()
            found, v = self._member(name, args)
            if found:
                return v
        return self.vb_get(name)


class _ControlsColl:
    vb_typename = "Controls"
    vb_default = "item"

    def __init__(self, items):
        self.items = items

    def vb_items(self):
        return self.items

    def vb_get(self, name):
        if name == "count":
            return len(self.items)
        raise err(438, name)

    def vb_call(self, name, args):
        if name == "item":
            return self.items[int(to_num(args[0]))]
        return self.vb_get(name)


class _FormsColl(_ControlsColl):
    def __init__(self, runtime):
        self.runtime = runtime

    @property
    def items(self):
        return [f for f in self.runtime.forms.values() if f.loaded]


# ============================================================================ global objects
class App:
    vb_typename = "App"

    def __init__(self, runtime):
        self.runtime = runtime

    def vb_get(self, name):
        p = self.runtime.project
        nat = getattr(self.runtime, "native", None)          # a .vbp run in place: its own values
        if nat is not None:
            v = nat.vbp

            def num(k):
                try:
                    return int(v.get(k, "0") or 0)
                except ValueError:
                    return 0
            return {"title": nat.title, "path": str(nat.folder),
                    "exename": Path(v.get("ExeName32", "") or nat.name).stem, "major": num("MajorVer"),
                    "minor": num("MinorVer"), "revision": num("RevisionVer"), "previnstance": False,
                    "comments": v.get("VersionComments", ""), "companyname": v.get("VersionCompanyName", ""),
                    "productname": v.get("VersionProductName", "") or nat.title,
                    "helpfile": v.get("HelpFile", "")}.get(name, EMPTY)
        return {"title": p.name, "path": str(p.folder), "exename": p.name, "major": 1, "minor": 0,
                "revision": 0, "previnstance": False, "comments": "", "companyname": "",
                "productname": p.name, "helpfile": ""}.get(name, EMPTY)

    def vb_set(self, name, value):
        pass

    def vb_call(self, name, args):
        return self.vb_get(name)


class Screen:
    vb_typename = "Screen"

    def __init__(self, runtime):
        self.runtime = runtime

    def vb_get(self, name):
        r = self.runtime.root
        if name == "width":
            return r.winfo_screenwidth() * 15
        if name == "height":
            return r.winfo_screenheight() * 15
        if name in ("twipsperpixelx", "twipsperpixely"):
            return 15
        if name == "activeform":
            return self.runtime.startup_form or NOTHING
        return EMPTY

    def vb_set(self, name, value):
        if name == "mousepointer":
            self.runtime.root.configure(cursor="watch" if int(to_num(value)) == 11 else "")

    def vb_call(self, name, args):
        return self.vb_get(name)


class Clipboard:
    vb_typename = "Clipboard"

    def __init__(self, runtime):
        self.runtime = runtime

    def vb_get(self, name):
        return self.vb_call(name, [])          # s = Clipboard.GetText / Clipboard.Clear (no parentheses)

    def vb_call(self, name, args):
        r = self.runtime.root
        if name == "settext":
            r.clipboard_clear()
            r.clipboard_append(to_str(args[0]))
        elif name == "gettext":
            try:
                return r.clipboard_get()
            except tk.TclError:
                return ""
        elif name == "clear":
            r.clipboard_clear()
        return EMPTY


class COMObject:
    """CreateObject("Excel.Application") etc. - requires pywin32."""
    vb_typename = "Object"

    def __init__(self, obj):
        self._o = obj

    def vb_get(self, name):
        return _wrap(getattr(self._o, name))

    def vb_set(self, name, value):
        setattr(self._o, name, value._o if isinstance(value, COMObject) else value)

    def vb_call(self, name, args):
        attr = getattr(self._o, name)
        return _wrap(attr(*[a._o if isinstance(a, COMObject) else a for a in args]) if callable(attr) else attr)


def _wrap(v):
    if hasattr(v, "_oleobj_"):
        return COMObject(v)
    return v


# ============================================================================ runtime
class Runtime:
    def __init__(self, folder: Path, debug: bool = False):
        self.native = None             # a VB6 .vbp run in place (radide/foreign/vb6_project.py)
        if folder.suffix.lower() == ".vbp" and folder.is_file():
            from ..foreign.vb6_project import NativeVB6
            import tempfile
            self.native = NativeVB6(folder, Path(tempfile.gettempdir()) / "radide-vb6-frx")
            folder = self.native.folder
            self.project = self.native.project()
        else:
            self.project = Project.load(folder)
        self.folder = folder
        self.interp = Interpreter(host=self)
        self.interp.output = lambda s: (print(s, flush=True))
        from . import vbado                  # ADO / DAO (Access .mdb through a 32-bit ADO helper)
        vbado.SEARCH_ROOTS.append(folder)
        from . import vbinterp as _vbi
        for _k, _v in vbado.CONSTANTS.items():
            _vbi.CONSTANTS.setdefault(_k, _v)
        self._dbengine = None
        self.interp.builtins["opendatabase"] = lambda *a: vbado.open_database(*a[:4], base=self.folder)
        self.forms: dict[str, VBForm] = {}
        self.root: tk.Tk | None = None
        self.startup_form: VBForm | None = None
        self.plugin = PythonTkPlugin()
        self._last_tick = time.time()
        self.debugger = Debugger(self) if debug else None

    def resolve(self, path):
        p = Path(path)
        return str(p if p.is_absolute() else self.folder / p)

    # -- loading code
    def load(self):
        it = self.interp
        # multi-language projects: only the VB forms/modules run here (others via RadCall)
        lang = getattr(self.project, "form_language", lambda _n: "vb-basic")
        self.project.forms = [n for n in self.project.forms if lang(n) == "vb-basic"]
        self.project.modules = [m for m in self.project.modules if m.lower().endswith((".bas", ".cls"))]
        for name in self.project.forms:
            form = self.native.form(name) if self.native else Form.load(self.project.form_path(name))
            vf = VBForm(self, form)
            self.forms[name.lower()] = vf
            it.objects[name.lower()] = vf
        it.objects.update(app=App(self), screen=Screen(self), clipboard=Clipboard(self),
                          forms=_FormsColl(self))
        if self.native is not None:          # DataEnvironment / DataReport designers (.Dsr)
            from .vbdata import load_designers
            load_designers(self)
        # solution references: <Lib>.ref.bas proxy modules first, so the project's own procedures win
        from ..languages._refs import proxy_files
        listed = {m.lower() for m in self.project.modules}
        for path in proxy_files(self.folder, "*.ref.bas"):
            if path.name.lower() not in listed:
                self._load_code(path, path.name[:-len(".ref.bas")], False)
        # Enum type names of every module first: "Dim m As MyEnum" (declared anywhere) is a Long
        import re as _re
        srcs = [self.native.module_text(m) if self.native else (self.folder / m).read_text(
                    encoding="utf-8-sig", errors="replace") if (self.folder / m).is_file() else ""
                for m in self.project.modules]
        srcs += [self.native.form_code(n) if self.native else "" for n in self.project.forms]
        it.enum_types = {m.lower() for src in srcs
                         for m in _re.findall(r"(?im)^\s*(?:public\s+|private\s+)?enum\s+(\w+)", src)}
        # class modules first, so module-level "Dim x As New CFoo" / "As CFoo" know the class
        for mod in sorted(self.project.modules, key=lambda m: not m.lower().endswith(".cls")):
            path = self.native.module_path(mod) if self.native else self.folder / mod
            self._load_code(path, Path(mod).stem, False,
                            src=self.native.module_text(mod) if self.native else None, filename=mod)
        for name in self.project.forms:
            self._load_code(self.folder / f"{name}.bas", name, True, self.forms[name.lower()],
                            src=self.native.form_code(name) if self.native else None)
            st = it.modules.get(name.lower())         # an MDIForm's events are MDIForm_Load, MDIForm_Unload ...
            if st is not None:
                for pname in [p for p in st.mod.procs if p.startswith("mdiform_")]:
                    st.mod.procs.setdefault("form_" + pname[len("mdiform_"):], st.mod.procs[pname])
        for st in it.modules.values():
            if not st.is_form:
                it.objects.setdefault(st.name.lower(), ModuleProxy(it, st))

    def _load_code(self, path: Path, name: str, is_form: bool, me=None, src=None, filename=None):
        if src is None:
            src = path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""
        fname = filename or path.name
        try:
            mod = parse_module(src, name, fname)
        except VBSyntaxError as e:
            self.fatal(f"{fname}({e.line}): Syntax error: {e.msg}", fname, e.line)
            raise SystemExit(1) from None
        st = self.interp.load_module(mod, is_form, me)
        st.filename = fname

    # -- UI
    def build_form(self, vf: VBForm):
        form = vf.model
        st = self.interp.modules.get(form.name.lower())
        fake = []                    # tell the Tk generator which events have handlers
        handlers = {}
        for c in [None, *form.controls]:
            ctype = "Form" if c is None else c.type
            owner = "Form" if c is None else (c.props.get("ArrayName") or c.name)
            index = None if c is None or not c.props.get("ArrayName") else int(c.props.get("ArrayIndex", 0))
            events = CONTROL_TYPES[c.type].all_events() if c is not None else \
                ["Load", "Activated", "Deactivate", "Resize", "FormClosing", "FormClosed", "Click",
                 "DoubleClick", "MouseDown", "MouseUp", "MouseMove", "MouseWheel", "KeyDown", "KeyUp", "KeyPress"]
            if c is not None and c.type in ("MenuStrip", "ToolStrip"):
                for it in menu_leaves(c.props.get("Items", [])):
                    neutral = f"{it['Name']}_Click"
                    if st and it["Name"].lower() + "_click" in st.mod.procs:
                        fake.append(f"    def {neutral}(")
                        handlers[neutral] = (it["Name"] + "_Click", "Click", None)
                continue
            for ev in events:
                if c is None and ev in ("Load", "FormClosing", "FormClosed"):
                    continue          # run synchronously by the runtime (VB semantics)
                vbev = vb_event_name(ctype, ev)
                if not vbev:
                    continue
                vbname = f"{owner}_{vbev}"
                if st and vbname.lower() in st.mod.procs:
                    neutral = f"{form.name if c is None else c.name}_{ev}"
                    fake.append(f"    def {neutral}(")
                    handlers[neutral] = (vbname, ev, index)
        code = self.plugin.generate_designer(form, "\n".join(fake))
        ns = {"__name__": f"vbform_{form.name}", "__file__": str(self.folder / f"{form.name}.py")}
        exec(compile(code, f"<{form.name} designer>", "exec"), ns)
        base = ns[f"{form.name}Designer"]
        runtime = self

        class FormUI(base):
            def __getattr__(self, name):
                if name in handlers:
                    vbname, ev, index = handlers[name]
                    return lambda *a: runtime.run_handler(vf, vbname, ev, *a, index=index)
                return base.__getattr__(self, name)
        is_first = self.root is None
        master = None if is_first else self.root
        ui = FormUI(master)
        vf.ui = ui
        if is_first:
            self.root = ui.root
        if not is_first:
            ui.root.withdraw()
        # Unload event → close
        ui.root.protocol("WM_DELETE_WINDOW", lambda: self.request_close(vf))

    def fire(self, vf: VBForm, owner: str, event: str, *args):
        st = self.interp.modules.get(vf.name.lower())
        vbev = vb_event_name("Form" if owner == "Form" else self._type_of(vf, owner), event)
        if not vbev or st is None:
            return
        index = None
        c = vf.model.find(owner) if owner != "Form" else None
        if c is not None and c.props.get("ArrayName"):         # control array: optKind_Click(Index)
            owner, index = c.props["ArrayName"], int(c.props.get("ArrayIndex", 0))
        name = f"{owner}_{vbev}"
        if name.lower() in st.mod.procs:
            self.run_handler(vf, name, event, *args, index=index)

    @staticmethod
    def _type_of(vf, owner):
        c = vf.model.find(owner)
        return c.type if c else ""

    def run_handler(self, vf: VBForm, vbname: str, event: str, *a, index=None):
        """Translate the toolkit event into VB arguments and run the procedure."""
        e = a[0] if a else None
        args, cells = [], []
        ret = None
        if event == "KeyPress" and e is not None:
            cell = Cell(ord(e.KeyChar) if e.KeyChar else 0)
            args, cells = [cell.value], [cell]
        elif event in ("KeyDown", "KeyUp") and e is not None:
            raw = e.raw
            s = getattr(raw, "state", 0) or 0
            shift = (1 if s & 1 else 0) | (2 if s & 4 else 0) | (4 if s & 0x20000 else 0)
            code = Cell(getattr(raw, "keycode", 0))
            args, cells = [code.value, shift], [code, None]
        elif event in ("MouseDown", "MouseUp", "MouseMove") and e is not None:
            btn = {1: 1, 3: 2, 2: 4}.get(e.Button, 0)
            args = [btn, 0, e.X * vf.unit, e.Y * vf.unit]
        elif event == "FormClosing":
            cell = Cell(0)
            args, cells = [cell.value], [cell]
        if event == "SelectedIndexChanged" and not args and index is None:
            c = vf.controls.get(vbname.rsplit("_", 1)[0].lower())
            if getattr(c, "type", "") == "TabControl":      # SSTab_Click(PreviousTab As Integer)
                cur = c.vb_get("tab")
                args = [getattr(c, "_prev_tab", 0)]
                c._prev_tab = cur
            elif getattr(c, "type", "") in ("ListView", "TreeView"):   # ItemClick(Item) / NodeClick(Node)
                args = [c.vb_get("selecteditem")]
        if index is not None:                     # control array: Index As Integer comes first
            args = [index, *args]
            cells = [None, *cells] if cells else []
        st = self.interp.modules.get(vf.name.lower())
        proc = st.mod.procs.get(vbname.lower()) if st is not None else None
        if proc is not None:                      # VB passes every declared argument (Button, Shift, X, Y ...)
            need = [p for p in proc.params if not p.optional and not getattr(p, "paramarray", False)]
            if len(args) < len(need):
                args = list(args) + [0] * (len(need) - len(args))
                cells = (list(cells) + [None] * (len(args) - len(cells))) if cells else []
        try:
            self.interp.call_by_name(vf.name, vbname, args, me=vf, arg_cells=cells or None)
        except EndProgram:
            self.end()
            return "break"
        except VBRuntimeError as ex:
            self.runtime_error(ex)
            return "break"
        except RecursionError:
            self.runtime_error(err(28, "Out of stack space"))
            return "break"
        if event == "KeyPress" and cells and cells[0].value == 0:
            ret = "break"
        if event == "FormClosing" and cells and int(to_num(cells[0].value)) != 0 and e is not None:
            e.Cancel = True
        return ret

    def runtime_error(self, ex: VBRuntimeError):
        mod = self.interp.modules.get((ex.module or "").lower())
        filename = getattr(mod, "filename", ex.module or "?") if mod else (ex.module or "?")
        msg = f"Run-time error '{ex.number}':\n\n{ex.description}"
        print(f"{filename}({ex.line}): Run-time error {ex.number}: {ex.description}", file=sys.stderr, flush=True)
        if self.debugger is not None:
            self.debugger.stop_on_error(filename, ex.line, ex)
        messagebox.showerror(self.project.name, msg)

    def fatal(self, text, filename="", line=0):
        print(text, file=sys.stderr, flush=True)
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror(self.project.name, text)
            r.destroy()
        except tk.TclError:
            pass

    def request_close(self, vf: VBForm):
        e = type("E", (), {"Cancel": False, "raw": None})()
        st = self.interp.modules.get(vf.name.lower())
        if st and "form_queryunload" in st.mod.procs:
            cell = Cell(0)
            try:
                self.interp.call_by_name(vf.name, "Form_QueryUnload", [0, 0], me=vf, arg_cells=[cell, None])
            except VBRuntimeError as ex:
                self.runtime_error(ex)
            if int(to_num(cell.value)):
                return
        if st and "form_unload" in st.mod.procs:
            self.run_handler(vf, "Form_Unload", "FormClosing", e)
            if e.Cancel:
                return
        self.unload(vf, events=False)

    def unload(self, vf: VBForm, events=True):
        if not vf.loaded:
            return
        if events:
            st = self.interp.modules.get(vf.name.lower())
            if st and "form_unload" in st.mod.procs:
                e = type("E", (), {"Cancel": False, "raw": None})()
                self.run_handler(vf, "Form_Unload", "FormClosing", e)
                if e.Cancel:
                    return
        root = vf.ui.root
        vf.loaded = False
        vf.controls.clear()
        if root is self.root:
            root.withdraw()
        else:
            root.destroy()
        if not any(f.loaded for f in self.forms.values()):
            # VB6 ends the program when no form is loaded AND no code runs: "Unload Me: frmNext.Show" goes on
            try:
                self.root.after_idle(self._end_if_no_forms)
            except (tk.TclError, AttributeError):
                self.end()

    def _end_if_no_forms(self):
        if not any(f.loaded for f in self.forms.values()):
            self.end()

    def end(self):
        try:
            if self.root is not None:
                self.root.destroy()
        except tk.TclError:
            pass
        try:                                    # End: flush and close files opened with Open ... As #n
            self.interp.shutting_down = True
            self.interp.files.close_all()
            sys.stdout.flush()
        except Exception:  # noqa: BLE001
            pass
        try:                                    # database helpers (vbado.py) release the .mdb files
            from .vbado import _close_all
            _close_all()
        except Exception:  # noqa: BLE001
            pass
        os._exit(0)

    # -- host services for the interpreter
    def msgbox(self, prompt, buttons, title):
        title = title or self.project.name
        kind = buttons & 7
        icon = {16: "error", 32: "question", 48: "warning", 64: "info"}.get(buttons & 0x70, "info")
        if kind == 4:
            return 6 if messagebox.askyesno(title, prompt, icon=icon) else 7
        if kind == 3:
            r = messagebox.askyesnocancel(title, prompt, icon=icon)
            return 6 if r else 7 if r is False else 2
        if kind == 1:
            return 1 if messagebox.askokcancel(title, prompt, icon=icon) else 2
        if kind == 5:
            return 4 if messagebox.askretrycancel(title, prompt, icon=icon) else 2
        {"error": messagebox.showerror, "warning": messagebox.showwarning}.get(icon, messagebox.showinfo)(title, prompt)
        return 1

    def inputbox(self, prompt, title, default):
        r = simpledialog.askstring(title or self.project.name, prompt, initialvalue=default)
        return r if r is not None else ""

    def doevents(self):
        if self.root is not None:
            self.root.update()

    def tick(self):
        now = time.time()
        if now - self._last_tick > 0.05 and self.root is not None:
            self._last_tick = now
            try:
                self.root.update()
            except tk.TclError:
                raise EndProgram() from None

    def new_object(self, cls):
        from . import vbado                  # New ADODB.Recordset / New Connection / DAO objects
        return vbado.create(cls, self.folder)

    def create_object(self, progid):
        from .vbfso import create as _builtin_object      # Scripting.FileSystemObject without COM
        obj = _builtin_object(str(progid), self.folder)
        if obj is not None:
            return obj
        from . import vbado                  # ADODB.* / DAO.DBEngine without 64-bit providers
        obj = vbado.create(str(progid), self.folder)
        if obj is not None:
            return obj
        try:
            import win32com.client  # type: ignore
        except ImportError:
            raise err(429, f"CreateObject(\"{progid}\") needs the pywin32 package (pip install pywin32)") from None
        return COMObject(win32com.client.Dispatch(progid))

    def global_object(self, name):
        obj = self.interp.objects.get(name)
        if obj is None and name in ("dbengine", "workspaces"):          # DAO globals
            from . import vbado
            if self._dbengine is None:
                self._dbengine = vbado.DBEngine(self.folder)
            obj = self._dbengine if name == "dbengine" else self._dbengine.Workspaces
        return obj

    def stop_statement(self, frame):
        if self.debugger is not None:
            self.debugger.pause(frame, "stop")

    # -- run
    def run(self):
        self.load()
        if self.debugger is not None:
            self.interp.trace = self.debugger.trace
        start = (os.environ.get("RAD_START_FORM") or self.project.startup or "").lower()
        try:
            if start in ("sub main", "main") or start not in self.forms:
                found = self.interp.find_proc("main", None)
                if found is None:
                    self.fatal("No startup form and no Sub Main found.")
                    return
                self.interp.call_proc(found[0], found[1], [])
            else:
                vf = self.forms[start]
                self.startup_form = vf
                vf.load()
                vf.vb_call("show", [])
        except EndProgram:
            self.end()
        except VBRuntimeError as ex:
            self.runtime_error(ex)
        if self.root is not None and any(f.loaded for f in self.forms.values()):
            self.root.mainloop()


# ============================================================================ debugger
class Debugger:
    def __init__(self, runtime: Runtime):
        self.rt = runtime
        self.mode = "run"
        self.depth = 0
        self.bps: set[tuple[str, int]] = set()
        self.conds: dict[tuple[str, int], str] = {}
        for spec in filter(None, os.environ.get("RADDBG_BP", "").split(";")):
            self._add_bp(spec, True)

    def _add_bp(self, spec, on):
        """spec = file|line[|condition]"""
        parts = spec.split("|")
        if len(parts) < 2 or not parts[1].strip().isdigit():
            return
        key = (parts[0].lower(), int(parts[1]))
        cond = "|".join(parts[2:]).strip()
        from ..debug_extras import parse_bp      # "@@bp {json}": hit count / logpoint
        d = parse_bp(cond)
        cond = d["cond"]
        self.hits = getattr(self, "hits", {})
        self.extra = getattr(self, "extra", {})
        self.hits.pop(key, None)
        self.extra.pop(key, None)
        if on and (d["hit"] or d["log"]):
            self.extra[key] = (d["hit"], d["log"])
        if on:
            self.bps.add(key)
            if cond:
                self.conds[key] = cond
            else:
                self.conds.pop(key, None)
        else:
            self.bps.discard(key)
            self.conds.pop(key, None)

    def _cond_true(self, key, frame):
        cond = self.conds.get(key)
        if not cond:
            return True
        try:
            from .vbinterp import to_bool
            return to_bool(self.rt.interp.evaluate_text(cond, frame))
        except Exception:  # noqa: BLE001 - a broken condition stops (like VB) so the user sees it
            return True

    def send(self, *fields):
        text = "|".join(str(f).replace("\n", "\\n").replace("|", "¦") for f in fields)
        sys.stdout.write(f"{TAG}{text}\n")
        sys.stdout.flush()

    def trace(self, frame, line):
        depth = len(self.rt.interp.stack)
        fname = getattr(frame.module, "filename", frame.module.name + ".bas").lower()
        stop = None
        if self.mode == "step":
            stop = "step"
        elif self.mode == "next" and depth <= self.depth:
            stop = "step"
        elif self.mode == "out" and depth < self.depth:
            stop = "step"
        if stop is None and (fname, line) in self.bps and self._cond_true((fname, line), frame):
            stop = "breakpoint"
            key = (fname, line)
            self.hits = getattr(self, "hits", {})
            self.hits[key] = self.hits.get(key, 0) + 1
            hit, log = getattr(self, "extra", {}).get(key, ("", ""))
            from ..debug_extras import format_log, hit_ok
            if hit and not hit_ok(hit, self.hits[key]):
                stop = None
            elif log:                                # logpoint: print the message, do not stop
                from .vbinterp import to_str
                sys.stdout.write(format_log(log, lambda e: to_str(self.rt.interp.evaluate_text(e, frame))) + "\n")
                sys.stdout.flush()
                stop = None
        if stop:
            self.pause(frame, stop)

    # ---- expandable Locals / Watch (arrays, collections, Types, objects with variables)
    @staticmethod
    def _children(value):
        from .vbinterp import UDT, Collection, VBArray
        if isinstance(value, VBArray):
            if len(value.bounds) == 1:
                lo = value.bounds[0][0]
                return [(f"({lo + i})", v) for i, v in enumerate(value.items()[:500])]
            return [("(" + ", ".join(map(str, k)) + ")", value.data[k]) for k in sorted(value.data)[:500]]
        if isinstance(value, Collection):
            return [(f"({i + 1})", v) for i, v in enumerate(value.items[:500])]
        if isinstance(value, UDT):
            return list(value._fields.items())
        cells = getattr(getattr(value, "st", None), "vars", None) or getattr(value, "vars", None)
        if isinstance(cells, dict):
            return [(n, c.value if isinstance(c, Cell) else c) for n, c in list(cells.items())[:500]]
        return []

    def _handle(self, value):
        if isinstance(value, (str, int, float, bool)) or not self._children(value):
            return 0
        h = len(self.handles) + 1
        self.handles[h] = value
        return h

    def stop_on_error(self, filename, line, ex):
        frame = self.rt.interp.stack[-1] if self.rt.interp.stack else None
        if frame is not None:
            self.pause(frame, "error", filename, line)

    def pause(self, frame, reason, filename=None, line=None):
        it = self.rt.interp
        fname = filename or getattr(frame.module, "filename", frame.module.name + ".bas")
        self.send("stop", str(self.rt.folder / fname), line or frame.line, reason)
        self.send("caps", "children", "bpx")
        self.handles = {}
        raw = dict(frame.locals)
        raw.update({f"{frame.module.name}.{n}": c for n, c in frame.module.vars.items()})
        for name, typ, val in it.frame_variables(frame):
            self.send("var", name, typ, val)
            cell = raw.get(name)
            h = self._handle(cell.value) if cell is not None else 0
            if h:
                self.send("ref", name, h)          # expandable in Locals (radide/debug_extras.py)
        for f in reversed(it.stack):
            self.send("frame", f.proc.display or f.proc.name if f.proc else "(module)",
                      str(self.rt.folder / getattr(f.module, "filename", f.module.name + ".bas")), f.line)
        while True:
            self.send("wait")
            cmd = sys.stdin.readline()
            if not cmd:
                cmd = "c"
            cmd = cmd.strip().lstrip("﻿")
            if cmd.startswith("e "):
                try:
                    from .vbinterp import _repr
                    self.send("eval", _repr(it.evaluate_text(cmd[2:], frame)))
                except (VBRuntimeError, VBSyntaxError) as ex:
                    self.send("eval", f"Error: {ex}")
                except Exception as ex:  # noqa: BLE001
                    self.send("eval", f"Error: {ex}")
                continue
            if cmd.startswith("k "):               # children of an expandable value
                from .vbinterp import _repr, _typename
                value = self.handles.get(int(cmd[2:].strip())) if cmd[2:].strip().isdigit() else None
                for cname, child in self._children(value):
                    self.send("kid", cname, _typename(child), _repr(child), self._handle(child))
                self.send("kend")
                continue
            if cmd.startswith("w "):               # Watch expression with its handle
                from .vbinterp import _repr, _typename
                try:
                    v = it.evaluate_text(cmd[2:], frame)
                    self.send("watch", _typename(v), self._handle(v), _repr(v))
                except Exception as ex:  # noqa: BLE001
                    self.send("watch", "", 0, f"Error: {ex}")
                continue
            if cmd.startswith(("b ", "B ")):
                self._add_bp(cmd[2:], cmd[0] == "b")
                continue
            if cmd in ("c", "s", "n", "o"):
                self.mode = {"c": "run", "s": "step", "n": "next", "o": "out"}[cmd]
                self.depth = len(it.stack)
                return
            if cmd == "q":
                self.send("done")
                os._exit(0)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    folder = Path(argv[0]).resolve()
    rt = Runtime(folder, debug="--debug" in argv)
    try:
        rt.run()
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
