"""Capture the GUI built by an existing Tkinter program (run in a subprocess).

Usage: python tk_capture.py <script.py> <output.json>

The script is executed with mainloop() replaced: when the program would start
its event loop, every window and widget is inspected (type, geometry, text,
colours, fonts, items, variables, command/bind callbacks, menus) and written
as JSON. Only the standard library is used.
"""
import gc
import json
import os
import re
import runpy
import sys
import tkinter as tk
import traceback
from tkinter import font as tkfont

RX_CMD = re.compile(r"\d+([A-Za-z_]\w*|<lambda>)")


class _Done(BaseException):
    pass


def _callback_name(tcl_name: str) -> str:
    """tkinter registers callbacks as '<id><function name>'."""
    m = RX_CMD.search(str(tcl_name or ""))
    return m.group(1) if m else ""


def _user_cb(tcl_name) -> str:
    name = _callback_name(tcl_name)
    return "" if name in ("destroy", "quit") else name


def _opt(w, name):
    try:
        return w.cget(name)
    except Exception:  # noqa: BLE001
        return None


def _color(w, name):
    v = _opt(w, name)
    if not v:
        return ""
    try:
        r, g, b = (c // 257 for c in w.winfo_rgb(v))
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:  # noqa: BLE001
        return ""


def _font(w):
    f = _opt(w, "font")
    if not f:
        return {}
    try:
        a = tkfont.Font(root=w, font=f).actual()
        return {"family": a.get("family"), "size": abs(int(a.get("size") or 9)),
                "bold": a.get("weight") == "bold", "italic": a.get("slant") == "italic"}
    except Exception:  # noqa: BLE001
        return {}


def _names_map(script_path):
    """Map id(widget or variable) -> Python name (attribute or global)."""
    names = {}
    main = sys.modules.get("__main__")
    spaces = []
    # globals of the running script frames
    f = sys._getframe()
    while f is not None:
        if os.path.abspath(f.f_code.co_filename) == script_path:
            spaces.append(("", f.f_globals))
            spaces.append(("", f.f_locals))
            if "self" in f.f_locals and hasattr(f.f_locals["self"], "__dict__"):
                spaces.append(("self.", vars(f.f_locals["self"])))
        f = f.f_back
    if main is not None:
        spaces.append(("", vars(main)))
    # attributes of instances of classes defined in the script
    for obj in gc.get_objects():
        try:
            cls = type(obj)
            if getattr(cls, "__module__", "") in ("__main__", "<run_path>") and hasattr(obj, "__dict__"):
                spaces.append(("self.", vars(obj)))
        except Exception:  # noqa: BLE001
            continue
    for prefix, space in spaces:
        for k, v in list(space.items()):
            if k.startswith("__"):
                continue
            if isinstance(v, (tk.Misc, tk.Variable)) and id(v) not in names:
                names[id(v)] = prefix + k
    return names


def _variables():
    out = {}
    for obj in gc.get_objects():
        try:
            if isinstance(obj, tk.Variable):
                out[str(obj)] = obj
        except Exception:  # noqa: BLE001
            continue
    return out


def _binds(w):
    out = []
    try:
        for seq in w.bind():
            script = w.bind(seq)
            for name in RX_CMD.findall(script or ""):
                out.append({"sequence": seq, "handler": name})
    except Exception:  # noqa: BLE001
        pass
    return out


def _menu(m):
    items = []
    try:
        last = m.index("end")
    except Exception:  # noqa: BLE001
        last = None
    if last is None:
        return items
    for i in range(last + 1):
        try:
            kind = m.type(i)
            if kind == "separator":
                items.append({"Text": "-"})
            elif kind == "cascade":
                sub = m.nametowidget(m.entrycget(i, "menu"))
                items.append({"Text": m.entrycget(i, "label"), "Items": _menu(sub)})
            elif kind in ("command", "checkbutton", "radiobutton"):
                items.append({"Text": m.entrycget(i, "label"),
                              "handler": _callback_name(m.entrycget(i, "command"))})
        except Exception:  # noqa: BLE001
            continue
    return items


def _widget(w, names, variables):
    cls = w.winfo_class()
    d = {"class": cls, "tkpath": str(w), "name": names.get(id(w), ""),
         "x": w.winfo_x(), "y": w.winfo_y(), "width": w.winfo_width(), "height": w.winfo_height(),
         "mapped": bool(w.winfo_ismapped()) or bool(w.winfo_manager()),
         "manager": w.winfo_manager()}
    if d["width"] <= 1:
        d["width"], d["height"] = w.winfo_reqwidth(), w.winfo_reqheight()
    for key in ("text", "state", "show", "orient", "from", "to", "values", "relief", "wrap",
                "justify", "anchor", "value", "maximum", "image"):
        v = _opt(w, key)
        if v not in (None, ""):
            d[key] = str(v) if not isinstance(v, (int, float)) else v
    d["bg"] = _color(w, "background") if cls not in ("TButton", "TLabel", "TEntry", "TCombobox",
                                                       "TCheckbutton", "TRadiobutton", "TFrame") else ""
    d["fg"] = _color(w, "foreground") if cls not in ("Frame", "TFrame", "Canvas") else ""
    d["font"] = _font(w)
    d["command"] = _callback_name(_opt(w, "command"))
    d["binds"] = _binds(w)
    for key in ("textvariable", "variable"):
        v = _opt(w, key)
        if v:
            var = variables.get(str(v))
            d[key] = {"tcl": str(v), "name": names.get(id(var), "") if var is not None else "",
                      "value": str(var.get()) if var is not None else ""}
    if cls == "Listbox":
        try:
            d["items"] = list(w.get(0, "end"))
        except Exception:  # noqa: BLE001
            pass
    if cls == "Text":
        try:
            d["text"] = w.get("1.0", "end-1c")
        except Exception:  # noqa: BLE001
            pass
    if cls in ("Entry", "TEntry", "Spinbox", "TSpinbox", "TCombobox"):
        try:
            d["current_text"] = w.get()
        except Exception:  # noqa: BLE001
            pass
    if cls in ("Checkbutton", "TCheckbutton") and d.get("variable"):
        on = _opt(w, "onvalue")
        d["checked"] = str(d["variable"]["value"]) == str(on if on is not None else 1)
    if cls == "TNotebook":
        try:
            d["tabs"] = [{"text": w.tab(t, "text"), "tkpath": str(t)} for t in w.tabs()]
        except Exception:  # noqa: BLE001
            pass
    d["children"] = [_widget(c, names, variables) for c in w.winfo_children()
                     if c.winfo_class() not in ("Menu", "Toplevel", "Tk")]
    return d


def capture(script_path):
    root = tk._default_root
    windows = []
    if root is None:
        return {"windows": [], "error": "the program created no Tk window"}
    names = _names_map(script_path)
    variables = _variables()
    tops = [root] + [w for w in _all_children(root) if isinstance(w, tk.Toplevel)]
    for top in tops:
        try:
            top.attributes("-alpha", 0.0)
        except Exception:  # noqa: BLE001
            pass
        try:
            top.deiconify()
        except Exception:  # noqa: BLE001
            pass
    root.update_idletasks()
    root.update()
    for top in tops:
        menu = None
        mname = _opt(top, "menu")
        if mname:
            try:
                menu = _menu(top.nametowidget(mname))
            except Exception:  # noqa: BLE001
                menu = None
        windows.append({
            "title": top.title(), "name": names.get(id(top), ""),
            "class_name": type(top).__name__, "is_root": top is root,
            "width": top.winfo_width() if top.winfo_width() > 1 else top.winfo_reqwidth(),
            "height": top.winfo_height() if top.winfo_height() > 1 else top.winfo_reqheight(),
            "bg": _color(top, "background"), "resizable": list(top.resizable()),
            "protocol_close": _user_cb(top.protocol("WM_DELETE_WINDOW")),
            "binds": _binds(top), "menu": menu,
            "children": [_widget(c, names, variables) for c in top.winfo_children()
                         if c.winfo_class() not in ("Menu", "Toplevel")],
        })
    return {"windows": windows}


def _all_children(w):
    out = []
    for c in w.winfo_children():
        out.append(c)
        out += _all_children(c)
    return out


def main():
    script = os.path.abspath(sys.argv[1])
    out_path = sys.argv[2]
    result = {"windows": [], "error": ""}

    def fake_mainloop(*_a, **_k):
        # capture while the program's frames (and so its variable names) are alive
        try:
            result.update(capture(script))
        except Exception:  # noqa: BLE001
            result["error"] = "capture failed:\n" + traceback.format_exc()
        result["captured"] = True
        raise _Done()
    tk.Misc.mainloop = fake_mainloop
    tk.mainloop = fake_mainloop
    sys.argv = [script]
    os.chdir(os.path.dirname(script))
    sys.path.insert(0, os.path.dirname(script))
    try:
        runpy.run_path(script, run_name="__main__")
        if not result.get("captured"):
            result.update(capture(script))     # script ended without mainloop
    except _Done:
        pass
    except SystemExit:
        if not result.get("captured"):
            result.update(capture(script))
    except BaseException:  # noqa: BLE001
        result["error"] = "the program raised an error:\n" + traceback.format_exc()
        try:
            result.update(capture(script))
        except Exception:  # noqa: BLE001
            pass
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1, default=str)
    os._exit(0)


if __name__ == "__main__":
    main()
