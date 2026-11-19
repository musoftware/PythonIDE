"""Run a RAD IDE "VB6 / BASIC" project.

    python -m radide.runtimes.vbrun <project-folder> [--debug]

Forms are built with Tkinter from the .form files (via the Python/Tk code
generator); VB event procedures (Command1_Click, Form_Load, Text1_Change,
Timer1_Timer, ...) are run by the BASIC interpreter. With --debug the RAD IDE
debug protocol is spoken on stdin/stdout (breakpoints from RADDBG_BP).
"""
from __future__ import annotations

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

# neutral event -> VB6 event name, by control type (None = not exposed)
VB_EVENT = {
    "*": {"Click": "Click", "DoubleClick": "DblClick", "MouseDown": "MouseDown", "MouseUp": "MouseUp",
          "MouseMove": "MouseMove", "MouseEnter": "MouseEnter", "MouseLeave": "MouseLeave",
          "MouseWheel": "MouseWheel", "KeyDown": "KeyDown", "KeyUp": "KeyUp", "KeyPress": "KeyPress",
          "GotFocus": "GotFocus", "LostFocus": "LostFocus"},
    "TextBox": {"TextChanged": "Change"},
    "CheckBox": {"CheckedChanged": "Click", "Click": None},
    "RadioButton": {"CheckedChanged": "Click", "Click": None},
    "ListBox": {"SelectedIndexChanged": "Click", "Click": None},
    "ComboBox": {"SelectedIndexChanged": "Click", "TextChanged": "Change", "Click": None},
    "NumericUpDown": {"ValueChanged": "Change"},
    "TrackBar": {"ValueChanged": "Change"},
    "Timer": {"Tick": "Timer"},
    "Form": {"Load": "Load", "Activated": "Activate", "Deactivate": "Deactivate", "Resize": "Resize",
             "FormClosing": "Unload", "FormClosed": "Terminate"},
}


def vb_event_name(ctype: str, event: str) -> str | None:
    table = VB_EVENT.get(ctype, {})
    if event in table:
        return table[event]
    if ctype in ("Timer", "MenuStrip"):
        return None
    return VB_EVENT["*"].get(event, event)


def color_to_vb(c: str) -> int:
    if not c or not c.startswith("#"):
        return 0x8000000F
    r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    return r + g * 256 + b * 65536


def vb_to_color(v) -> str:
    n = int(to_num(v))
    if n & 0x80000000:          # system colour
        return ""
    return f"#{n & 0xFF:02X}{(n >> 8) & 0xFF:02X}{(n >> 16) & 0xFF:02X}"


# ============================================================================ controls
class VBControl:
    vb_default = "text"

    def __init__(self, form: "VBForm", ctrl):
        self.form, self.ctrl = form, ctrl
        self.name = ctrl.name
        self.type = ctrl.type
        self.vb_typename = {"Button": "CommandButton", "RadioButton": "OptionButton",
                            "GroupBox": "Frame", "NumericUpDown": "UpDown", "TrackBar": "Slider",
                            "PictureBox": "PictureBox"}.get(ctrl.type, ctrl.type)
        self.vb_name = self.name
        self.tag = ""
        if self.type in ("Label", "Button", "CheckBox", "RadioButton", "GroupBox"):
            self.vb_default = "caption" if self.type != "CheckBox" else "value"
        if self.type in ("ListBox",):
            self.vb_default = "text"
        if self.type in ("NumericUpDown", "TrackBar", "ProgressBar"):
            self.vb_default = "value"
        if self.type == "RadioButton":
            self.vb_default = "value"

    # -- helpers
    @property
    def w(self):
        return getattr(self.form.ui, self.name)

    def _var(self):
        return getattr(self.form.ui, f"{self.name}_var", None)

    def _unit(self):
        return self.form.unit

    def _place(self, **kw):
        info = self.w.place_info()
        geo = {k: int(float(info.get(k, 0) or 0)) for k in ("x", "y", "width", "height")}
        geo.update(kw)
        self.w.place(**geo)

    # -- protocol
    def vb_get(self, name):
        w, t = self.w, self.type
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
            v = int(float(info.get(key, 0) or 0)) if info else getattr(w, f"winfo_{key if key in ('x', 'y') else name}")()
            return v * self._unit()
        if name == "enabled":
            try:
                return str(w.cget("state")) != "disabled"
            except tk.TclError:
                return True
        if name == "visible":
            return bool(w.winfo_manager())
        if name == "backcolor":
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
            return self.vb_get("listcount") - 1
        if name == "selstart":
            return w.index("insert") if t == "TextBox" and not self.ctrl.props.get("Multiline") else 0
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

    def vb_set(self, name, value):
        w, t = self.w, self.type
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
            try:
                w.configure(state="normal" if to_bool(value) else "disabled")
            except tk.TclError:
                pass
            return
        if name == "visible":
            if to_bool(value):
                p = self.ctrl.props
                info = getattr(self, "_saved_place", None) or {"x": p["Left"], "y": p["Top"],
                                                                "width": p["Width"], "height": p["Height"]}
                w.place(**info)
            else:
                info = w.place_info()
                if info:
                    self._saved_place = {k: info[k] for k in ("x", "y", "width", "height")}
                w.place_forget()
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
            try:
                w.configure(state="readonly" if to_bool(value) else "normal")
            except tk.TclError:
                pass
            return
        if name == "picture" and t == "PictureBox":
            path = to_str(value)
            if path:
                img = tk.PhotoImage(file=self.form.runtime.resolve(path))
                w.configure(image=img)
                setattr(self.form.ui, f"{self.name}_image", img)
            else:
                w.configure(image="")
            return
        if name in ("selstart", "sellength", "seltext", "tabindex", "tabstop", "mousepointer", "default",
                    "cancel", "appearance", "borderstyle", "sorted", "alignment", "autosize", "wordwrap"):
            return                       # accepted but not applicable
        raise err(438, f"Object doesn't support property '{name}' ({self.name})")

    def vb_call(self, name, args):
        w, t = self.w, self.type
        if name == "additem":
            item = to_str(args[0])
            if t == "ListBox":
                w.insert("end" if len(args) < 2 else int(to_num(args[1])), item)
            else:
                vals = list(w.cget("values") or ())
                vals.insert(len(vals) if len(args) < 2 else int(to_num(args[1])), item)
                w.configure(values=vals)
            return EMPTY
        if name == "removeitem":
            i = int(to_num(args[0]))
            if t == "ListBox":
                w.delete(i)
            else:
                vals = list(w.cget("values") or ())
                vals.pop(i)
                w.configure(values=vals)
            return EMPTY
        if name == "clear":
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

    def vb_setindexed(self, name, args, value):
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
            if c.type != "MenuStrip":
                vc = VBControl(self, c)
                self.controls[c.name.lower()] = vc
                arr = c.props.get("ArrayName")
                if arr:
                    ca = self.controls.setdefault(arr.lower(), ControlArray(arr))
                    ca.items[int(c.props.get("ArrayIndex", 0))] = vc
        menu = self.model.menu()
        if menu is not None and hasattr(self.ui, menu.name):
            self._map_menu(getattr(self.ui, menu.name), menu.props.get("Items", []))
        self.runtime.fire(self, "Form", "Load")

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
        if name == "caption":
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
        raise err(438, f"Form doesn't support property or method '{name}'")

    def vb_set(self, name, value):
        self.load()
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
        if name in ("cls", "print", "move", "zorder", "circle", "line", "pset"):
            return EMPTY
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
        return EMPTY

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
        self.project = Project.load(folder)
        self.folder = folder
        self.interp = Interpreter(host=self)
        self.interp.output = lambda s: (print(s, flush=True))
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
        for name in self.project.forms:
            form = Form.load(self.project.form_path(name))
            vf = VBForm(self, form)
            self.forms[name.lower()] = vf
            it.objects[name.lower()] = vf
        it.objects.update(app=App(self), screen=Screen(self), clipboard=Clipboard(self),
                          forms=_FormsColl(self))
        for mod in self.project.modules:
            path = self.folder / mod
            self._load_code(path, Path(mod).stem, False)
        for name in self.project.forms:
            self._load_code(self.folder / f"{name}.bas", name, True, self.forms[name.lower()])
        for st in it.modules.values():
            if not st.is_form:
                it.objects.setdefault(st.name.lower(), ModuleProxy(it, st))

    def _load_code(self, path: Path, name: str, is_form: bool, me=None):
        src = path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""
        try:
            mod = parse_module(src, name, path.name)
        except VBSyntaxError as e:
            self.fatal(f"{path.name}({e.line}): Syntax error: {e.msg}", path.name, e.line)
            raise SystemExit(1) from None
        st = self.interp.load_module(mod, is_form, me)
        st.filename = path.name

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
            if c is not None and c.type == "MenuStrip":
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
        name = f"{owner}_{vbev}"
        if name.lower() in st.mod.procs:
            self.run_handler(vf, name, event, *args)

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
        if index is not None:                     # control array: Index As Integer comes first
            args = [index, *args]
            cells = [None, *cells] if cells else []
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
            others = [f for f in self.forms.values() if f.loaded and f is not vf]
            if not others:
                self.end()
                return
            root.withdraw()
        else:
            root.destroy()
        if not any(f.loaded for f in self.forms.values()):
            self.end()

    def end(self):
        try:
            if self.root is not None:
                self.root.destroy()
        except tk.TclError:
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
        return None

    def create_object(self, progid):
        try:
            import win32com.client  # type: ignore
        except ImportError:
            raise err(429, f"CreateObject(\"{progid}\") needs the pywin32 package (pip install pywin32)") from None
        return COMObject(win32com.client.Dispatch(progid))

    def global_object(self, name):
        return self.interp.objects.get(name)

    def stop_statement(self, frame):
        if self.debugger is not None:
            self.debugger.pause(frame, "stop")

    # -- run
    def run(self):
        self.load()
        if self.debugger is not None:
            self.interp.trace = self.debugger.trace
        start = (self.project.startup or "").lower()
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
        for spec in filter(None, os.environ.get("RADDBG_BP", "").split(";")):
            f, _, ln = spec.rpartition("|")
            if ln.isdigit():
                self.bps.add((f.lower(), int(ln)))

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
        if stop is None and (fname, line) in self.bps:
            stop = "breakpoint"
        if stop:
            self.pause(frame, stop)

    def stop_on_error(self, filename, line, ex):
        frame = self.rt.interp.stack[-1] if self.rt.interp.stack else None
        if frame is not None:
            self.pause(frame, "error", filename, line)

    def pause(self, frame, reason, filename=None, line=None):
        it = self.rt.interp
        fname = filename or getattr(frame.module, "filename", frame.module.name + ".bas")
        self.send("stop", str(self.rt.folder / fname), line or frame.line, reason)
        for name, typ, val in it.frame_variables(frame):
            self.send("var", name, typ, val)
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
            if cmd.startswith(("b ", "B ")):
                f, _, ln = cmd[2:].rpartition("|")
                if ln.isdigit():
                    (self.bps.add if cmd[0] == "b" else self.bps.discard)((f.lower(), int(ln)))
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
