"""RAD Modern (Rm*) controls for Tkinter - the python-tk runtime of the Rm* component packages.

It draws the controls when a form runs inside the IDE with Tk: python-tk projects, VB6 forms (vb-basic) and
every GUI Bridge language (C, C++, C#, Java, ...). The native exe of a C / C++ / Fortran project uses the
radforms modules (radide/runtimes/native/radforms/controls/rm_*.c) instead; both follow
docs/plans/MODERN_CONTROLS.md (same property, event and method names).

Properties are attributes with the manifest names (``RmToggle1.Checked = True``), methods are methods
(``RmToast1.Show("Saved", "Done", "Success", 3000)``), events go through ``rad_bind(name, callback)``. Item
events (ItemClick, NodeClick, CellClick ...) also store the item in ``EventItem`` / ``EventIndex`` (grids:
``EventRow`` / ``EventColumn``) so every language can read it.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import tkinter as tk
import tkinter.font as tkfont

THEMES = {
    "Light": dict(dark=False, window="#F0F0F0", text="#000000", face="#E1E1E1", face_text="#000000", border="#ADADAD",
                  hot="#E5F1FB", accent="#0078D7", disabled="#A0A0A0", input="#FFFFFF", input_text="#000000"),
    "Dark": dict(dark=True, window="#202020", text="#F0F0F0", face="#333333", face_text="#F0F0F0", border="#555555",
                 hot="#454545", accent="#0078D7", disabled="#787878", input="#191919", input_text="#F0F0F0"),
    "Office": dict(dark=False, window="#F3F3F3", text="#262626", face="#FFFFFF", face_text="#262626", border="#ABABAB",
                   hot="#D5E1F2", accent="#2B579A", disabled="#A5A5A5", input="#FFFFFF", input_text="#262626"),
    "Metro": dict(dark=False, window="#FFFFFF", text="#1E1E1E", face="#E6E6E6", face_text="#1E1E1E", border="#CCCCCC",
                  hot="#DADADA", accent="#0078D7", disabled="#AAAAAA", input="#FFFFFF", input_text="#1E1E1E"),
}
APP_THEME = ["Light"]           # the application theme (set_theme)


def set_theme(name):
    if name in THEMES:
        APP_THEME[0] = name


def _rgb(c):
    c = str(c or "#000000").lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    try:
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    except ValueError:
        return 0, 0, 0


def blend(a, b, t):
    ra, ga, ba = _rgb(a)
    rb, gb, bb = _rgb(b)
    t = max(0.0, min(1.0, t))
    return "#%02X%02X%02X" % (round(ra + (rb - ra) * t), round(ga + (gb - ga) * t), round(ba + (bb - ba) * t))


def on(back):
    r, g, b = _rgb(back)
    return "#202020" if (r * 299 + g * 587 + b * 114) / 1000 > 150 else "#FFFFFF"


def _items(value):
    if isinstance(value, list):
        out = value
    else:
        s = str(value or "").strip()
        if s.startswith("["):
            try:
                out = json.loads(s)
            except ValueError:
                out = []
        else:
            out = [x for x in s.split(";") if x != ""] if s else []
    return [it if isinstance(it, dict) else {"Text": str(it)} for it in out]


def _kids(it):
    for k in ("Items", "Nodes", "Groups", "Pages", "Children", "Panels", "Tabs"):
        if isinstance(it.get(k), list) and it[k]:
            return [x if isinstance(x, dict) else {"Text": str(x)} for x in it[k]]
    return []


def _name(it):
    return str(it.get("Name") or str(it.get("Text", "")).replace(" ", "").replace("&", ""))


def _num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _bool(v):
    return v is True or str(v).lower() in ("true", "1", "-1", "yes", "on")


GLYPH_CHARS = {"home": "⌂", "settings": "⚙", "user": "☺", "users": "☺", "mail": "✉",
               "search": "⚲", "save": "▣", "open": "▱", "folder": "▱", "new": "▯", "file": "▯",
               "cut": "✂", "copy": "⧉", "paste": "▤", "undo": "↶", "redo": "↷", "bold": "B",
               "italic": "I", "underline": "U", "print": "⎙", "chart": "▁▃▅", "bell": "♪",
               "calendar": "▦", "clock": "◷", "info": "ℹ", "warning": "⚠", "error": "✖",
               "success": "✔", "help": "?", "close": "✕", "plus": "+", "minus": "−", "menu": "☰",
               "star": "★", "heart": "♥", "grid": "▦", "list": "☰", "table": "▦",
               "filter": "▽", "refresh": "⟳", "play": "▶", "pause": "‖", "stop": "■",
               "lock": "▣", "cloud": "☁", "download": "↓", "upload": "↑", "edit": "✎",
               "trash": "✖", "tag": "◆", "link": "∞", "phone": "☎", "globe": "◎",
               "camera": "◉", "image": "▧", "music": "♫", "video": "▶", "database": "▤",
               "code": "</>", "terminal": ">_", "bug": "⌘", "light": "☀", "dark": "☾", "send": "➤",
               "attach": "✂", "flag": "⚑", "pin": "●", "eye": "◉"}


def glyph(name):
    n = str(name or "")
    if not n:
        return ""
    return GLYPH_CHARS.get(n.lower(), "□" if "." in n else n[:1])


class Args:
    """Event data of an item event (also usable where EventArgs is expected)."""

    def __init__(self, item="", index=-1, row=-1, col=-1):
        self.ItemName = self.Name = item
        self.Index = index
        self.Row, self.Column = row, col
        self.X, self.Y = item, index           # the GUI Bridge sends "X Y": item name and index
        self.Button, self.KeyCode, self.KeyChar, self.Delta, self.Cancel = 0, "", "", 0, False


class _Base(tk.Canvas):
    PROPS: dict = {}
    COMMON = {"Text": "", "Enabled": True, "BackColor": "", "ForeColor": "", "FontName": "Segoe UI", "FontSize": 9,
              "FontBold": False, "FontItalic": False, "Style": "Inherit", "AccentColor": "", "ToolTip": "", "Visible": True}

    def __init__(self, master, **kw):
        object.__setattr__(self, "_p", {**self.COMMON, **self.PROPS})
        object.__setattr__(self, "_h", {})
        object.__setattr__(self, "_hover", -1)
        object.__setattr__(self, "_inside", False)
        try:
            bg = master.cget("bg")
        except (tk.TclError, AttributeError):
            bg = THEMES["Light"]["window"]
        super().__init__(master, highlightthickness=0, bd=0, bg=bg, takefocus=1)
        for k, v in kw.items():
            self._p[k] = v
        self.EventItem, self.EventIndex, self.EventRow, self.EventColumn = "", -1, -1, -1
        self.init()
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Enter>", lambda _e: self._enter(True))
        self.bind("<Leave>", lambda _e: self._enter(False))
        self.bind("<Motion>", self._motion)
        self.bind("<Button-1>", self._down)
        self.bind("<ButtonRelease-1>", self._up)
        self.bind("<Double-Button-1>", self._double)
        self.bind("<MouseWheel>", self._wheel)
        self.bind("<Key>", self._key)
        self.bind("<FocusIn>", lambda _e: self.redraw())
        self.bind("<FocusOut>", lambda _e: self.redraw())

    # ---- properties: attributes with an upper-case first letter
    def __getattr__(self, name):
        p = self.__dict__.get("_p")
        if p is not None and name in p:
            return p[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name[:1].isupper() and name not in ("EventItem", "EventIndex", "EventRow", "EventColumn"):
            old = self._p.get(name)
            self._p[name] = value
            self.changed(name, old, value)
            self.redraw()
        else:
            object.__setattr__(self, name, value)

    def changed(self, name, old, value):
        if name == "Enabled":
            self.configure(state="normal" if _bool(value) else "disabled")

    def init(self):
        pass

    # ---- events
    def rad_bind(self, event, callback):
        self._h[event] = callback

    def _raise(self, event, item=None, index=-1, row=-1, col=-1):
        if item is not None:
            self.EventItem, self.EventIndex = item, index
        if row >= 0:
            self.EventRow, self.EventColumn = row, col
        fn = self._h.get(event)
        if fn is not None:
            try:
                fn(Args(item or "", index, row, col))
            except TypeError:
                fn()

    # ---- look
    @property
    def T(self):
        name = str(self._p.get("Style") or "Inherit")
        return THEMES.get(name, THEMES.get(APP_THEME[0], THEMES["Light"]))

    @property
    def accent(self):
        return self._p.get("AccentColor") or self.T["accent"]

    def font(self, scale=1.0, bold=False):
        size = max(6, int(round(_num(self._p.get("FontSize"), 9) * scale)))
        return (self._p.get("FontName") or "Segoe UI", size, "bold" if bold or _bool(self._p.get("FontBold")) else "normal")

    def text_w(self, s, f=None):
        return tkfont.Font(font=f or self.font()).measure(str(s))

    def W(self):
        return max(1, self.winfo_width())

    def H(self):
        return max(1, self.winfo_height())

    def rrect(self, x0, y0, x1, y1, r=0, fill="", outline="", width=1):
        if r <= 0 or x1 - x0 < 2 * r or y1 - y0 < 2 * r:
            return self.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=width)
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r,
               x0, y0 + r, x0, y0]
        return self.create_polygon(pts, smooth=True, fill=fill, outline=outline, width=width)

    def label(self, x, y, s, color, anchor="w", f=None, width=0):
        return self.create_text(x, y, text=str(s), fill=color, anchor=anchor, font=f or self.font(), width=width or 0)

    def background(self):
        bg = self._p.get("BackColor") or self.T["window"]
        try:
            self.configure(bg=bg)
        except tk.TclError:
            pass
        return bg

    def redraw(self):
        try:
            self.delete("all")
            self.draw()
        except tk.TclError:
            pass

    def draw(self):
        pass

    # ---- mouse / keys (overridden)
    def _enter(self, inside):
        self._inside = inside
        if not inside:
            self._hover = -1
        self.redraw()

    def _motion(self, e):
        h = self.hit(e.x, e.y)
        if h != self._hover:
            self._hover = h
            self.redraw()

    def hit(self, x, y):
        return 0

    def _down(self, e):
        if not _bool(self._p.get("Enabled", True)):
            return
        self.focus_set()
        self.press(e.x, e.y)

    def _up(self, e):
        if not _bool(self._p.get("Enabled", True)):
            return
        if 0 <= e.x < self.W() and 0 <= e.y < self.H():
            self.click(e.x, e.y)

    def _double(self, e):
        self.double(e.x, e.y)

    def _wheel(self, e):
        self.wheel(1 if e.delta > 0 else -1)

    def _key(self, e):
        self.key(e.keysym)

    def press(self, x, y):
        pass

    def click(self, x, y):
        pass

    def double(self, x, y):
        pass

    def wheel(self, d):
        pass

    def key(self, k):
        if k in ("space", "Return"):
            self.click(1, 1)

    # a Canvas' lift / lower raise canvas items: without arguments raise the widget itself (z-order code)
    def lift(self, *args):
        return tk.Canvas.tag_raise(self, *args) if args else tk.Misc.tkraise(self)

    def lower(self, *args):
        return tk.Canvas.tag_lower(self, *args) if args else tk.Misc.lower(self)

    def PerformClick(self):
        self.click(1, 1)

    def Refresh(self):
        self.redraw()


# ====================================================================== buttons
class RmButton(_Base):
    PROPS = {"Image": "", "ImagePosition": "Left", "Kind": "Default", "CornerRadius": -1, "DropDownItems": ""}

    def draw(self):
        t, w, h = self.T, self.W(), self.H()
        bg = self.background()
        kind = self._p.get("Kind", "Default")
        hot = self._inside
        rad = int(_num(self._p.get("CornerRadius"), -1))
        rad = 5 if rad < 0 else rad
        fg = self._p.get("ForeColor") or t["face_text"]
        if kind == "Accent":
            fill, outline, fg = blend(self.accent, "#FFFFFF", .18 if hot else 0), "", on(self.accent)
        elif kind == "Outline":
            fill, outline, fg = blend(bg, self.accent, .08) if hot else "", self.accent, self.accent
        elif kind == "Flat":
            fill, outline = t["hot"] if hot else "", ""
        elif kind == "Link":
            fill, outline, fg = "", "", self.accent
        else:
            fill, outline = (t["hot"] if hot else (self._p.get("BackColor") or t["face"])), t["border"]
        if not _bool(self._p.get("Enabled", True)):
            fg = t["disabled"]
        if fill or outline:
            self.rrect(1, 1, w - 2, h - 2, rad, fill=fill, outline=outline)
        drop = bool(_items(self._p.get("DropDownItems")))
        aw = 22 if drop else 0
        g, s = glyph(self._p.get("Image")), str(self._p.get("Text", ""))
        label = (g + "  " + s).strip() if g and self._p.get("ImagePosition") != "Top" else s
        if g and self._p.get("ImagePosition") == "Top":
            self.label((w - aw) / 2, h / 2 - 9, g, fg, "center", self.font(1.6))
            self.label((w - aw) / 2, h / 2 + 12, s, fg, "center")
        else:
            f = (self._p.get("FontName") or "Segoe UI", int(_num(self._p.get("FontSize"), 9)), "underline") if kind == "Link" and hot else None
            if kind == "Link":
                self.label(6, h / 2, label, fg, "w", f)
            else:
                self.label((w - aw) / 2, h / 2, label, fg, "center")
        if drop:
            self.create_line(w - aw, 6, w - aw, h - 6, fill=blend(t["face"], fg, .35))
            self.label(w - aw / 2, h / 2, "⌄", fg, "center")
        if self.focus_get() is self and kind != "Link":
            self.rrect(4, 4, w - 5, h - 5, max(0, rad - 3), outline=blend(fill or bg, fg, .5))

    def click(self, x, y):
        if _items(self._p.get("DropDownItems")) and x >= self.W() - 22:
            return self.ShowDropDown()
        self._raise("Click")

    def ShowDropDown(self):
        menu = tk.Menu(self, tearoff=0)
        for i, it in enumerate(_items(self._p.get("DropDownItems"))):
            if it.get("Text") == "-":
                menu.add_separator()
            else:
                menu.add_command(label=it.get("Text", ""), command=lambda n=_name(it), k=i: self._raise("DropDownItemClicked", n, k))
        menu.tk_popup(self.winfo_rootx(), self.winfo_rooty() + self.H())


class _CheckBase(_Base):
    PROPS = {"Checked": False, "CheckAlign": "Left"}
    RADIO = False
    SWITCH = False

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "Checked" and _bool(old) != _bool(value):
            if self.RADIO and _bool(value):
                self._others_off()
            self._raise("CheckedChanged")

    def _others_off(self):
        for w in self.master.winfo_children():
            if w is not self and isinstance(w, RmRadioButton) and _bool(w._p.get("Checked")):
                w.Checked = False

    def toggle(self):
        if self.RADIO:
            if not _bool(self.Checked):
                self.Checked = True
        else:
            if _bool(self._p.get("Indeterminate")):
                self._p["Indeterminate"] = False
                self.Checked = True
            else:
                self.Checked = not _bool(self.Checked)

    def click(self, x, y):
        self.toggle()
        self._raise("Click")

    def Toggle(self):
        self.toggle()

    def draw(self):
        t, h = self.T, self.H()
        self.background()
        ac = self.accent if _bool(self._p.get("Enabled", True)) else t["disabled"]
        fg = (self._p.get("ForeColor") or t["text"]) if _bool(self._p.get("Enabled", True)) else t["disabled"]
        on_ = _bool(self._p.get("Checked"))
        if self.SWITCH:
            y = h / 2 - 10
            if on_:
                self.rrect(1, y, 41, y + 20, 10, fill=ac)
                self.create_oval(24, y + 3, 38, y + 17, fill=on(ac), outline="")
            else:
                self.rrect(1, y, 41, y + 20, 10, fill="", outline=blend(t["border"], t["text"], .3), width=1.2)
                self.create_oval(4, y + 3, 18, y + 17, fill=blend(t["text"], t["window"], .35), outline="")
            s = self._p.get("OnText") if on_ and self._p.get("OnText") else self._p.get("OffText") if not on_ and self._p.get("OffText") else self._p.get("Text", "")
            self.label(49, h / 2, s, fg)
            return
        y = h / 2 - 8
        if self.RADIO:
            self.create_oval(1, y, 17, y + 16, fill=t["input"], outline=ac if on_ else blend(t["border"], t["text"], .3), width=1.4)
            if on_:
                self.create_oval(5, y + 4, 13, y + 12, fill=ac, outline="")
        else:
            ind = _bool(self._p.get("Indeterminate"))
            if on_ or ind:
                self.rrect(1, y, 17, y + 16, 3, fill=ac)
                if ind:
                    self.create_rectangle(5, y + 7, 13, y + 9, fill=on(ac), outline="")
                else:
                    self.create_line(4, y + 8, 7.5, y + 12, 14, y + 4.5, fill=on(ac), width=2, capstyle="round", joinstyle="round")
            else:
                self.rrect(1, y, 17, y + 16, 3, fill=t["input"], outline=blend(t["border"], t["text"], .3))
        self.label(25, h / 2, self._p.get("Text", ""), fg)


class RmToggle(_CheckBase):
    PROPS = {"Checked": False, "OnText": "", "OffText": "", "CheckAlign": "Left"}
    SWITCH = True


class RmCheckBox(_CheckBase):
    PROPS = {"Checked": False, "Indeterminate": False, "CheckAlign": "Left"}

    @property
    def CheckState(self):
        return "Indeterminate" if _bool(self._p.get("Indeterminate")) else "Checked" if _bool(self._p.get("Checked")) else "Unchecked"


class RmRadioButton(_CheckBase):
    RADIO = True


class RmTile(_Base):
    PROPS = {"Title": "", "Count": "", "Image": "", "TileColor": "", "Size": "Medium"}

    def draw(self):
        w, h = self.W(), self.H()
        self.background()
        base = self._p.get("TileColor") or self.accent
        fill = blend(base, "#FFFFFF", .14) if self._inside else base
        fg = on(base)
        self.rrect(1, 1, w - 1, h - 1, 4, fill=fill)
        title = self._p.get("Title") or self._p.get("Text", "")
        g = glyph(self._p.get("Image"))
        if h < 90:
            self.label(w / 2, h / 2, g or title, fg, "center", self.font(1.6 if g else 1.0))
        else:
            if g:
                self.label(w / 2, h / 2 - 8, g, fg, "center", self.font(3.2))
            if str(self._p.get("Count", "")):
                self.label(w - 10, 8, self._p.get("Count"), fg, "ne", self.font(2.4, True))
            self.label(10, h - 10, title, fg, "sw", self.font(1.05, True))
        if str(self._p.get("Count", "")) and h < 90:
            self.label(w - 5, 3, self._p.get("Count"), fg, "ne", self.font(.9, True))

    def click(self, x, y):
        self._raise("Click")


# ====================================================================== input
class _Inner:
    """Mix-in: a real tk.Entry / tk.Text inside the canvas frame."""


class RmTextBox(_Base):
    PROPS = {"Watermark": "", "Icon": "", "ShowClear": False, "PasswordChar": "", "MultiLine": False, "ReadOnly": False,
             "ErrorText": "", "MaxLength": 0}

    def init(self):
        object.__setattr__(self, "_entry", None)
        self._make()

    def _make(self):
        old = ""
        if self._entry is not None:
            old = self._get()
            self._entry.destroy()
        t = self.T
        if _bool(self._p.get("MultiLine")):
            e = tk.Text(self, bd=0, highlightthickness=0, wrap="word", bg=t["input"], fg=t["input_text"],
                        insertbackground=t["input_text"], font=self.font())
            e.insert("1.0", old or str(self._p.get("Text", "")))
            e.bind("<<Modified>>", self._modified)
        else:
            e = tk.Entry(self, bd=0, highlightthickness=0, bg=t["input"], fg=t["input_text"], insertbackground=t["input_text"],
                         font=self.font(), show=str(self._p.get("PasswordChar") or "")[:1])
            e.insert(0, old or str(self._p.get("Text", "")))
            e.bind("<KeyRelease>", lambda _e: self._typed())
        e.bind("<Key>", lambda ev: self._raise_key(ev))
        e.bind("<FocusIn>", lambda _e: (self.redraw(), self._raise("GotFocus")))
        e.bind("<FocusOut>", lambda _e: (self.redraw(), self._raise("LostFocus")))
        object.__setattr__(self, "_entry", e)
        object.__setattr__(self, "_last", self._get())
        if _bool(self._p.get("ReadOnly")):
            e.configure(state="disabled" if isinstance(e, tk.Text) else "readonly")
        self._place()

    def _raise_key(self, ev):
        fn = self._h.get("KeyPress")
        if fn is not None and ev.char:
            a = Args()
            a.KeyChar, a.KeyCode = ev.char, ev.keysym
            a.X, a.Y = 0, 0
            try:
                fn(a)
            except TypeError:
                fn()

    def _modified(self, _e=None):
        try:
            self._entry.edit_modified(False)
        except tk.TclError:
            return
        self._typed()

    def _typed(self):
        now = self._get()
        if now != getattr(self, "_last", None):
            object.__setattr__(self, "_last", now)
            self._p["Text"] = now
            self.redraw()
            self._raise("TextChanged")

    def _get(self):
        e = self._entry
        if e is None:
            return str(self._p.get("Text", ""))
        return e.get("1.0", "end-1c") if isinstance(e, tk.Text) else e.get()

    def _place(self):
        if self._entry is None:
            return
        w, h = self.W(), self.H()
        left = 8 + (22 if self._p.get("Icon") else 0)
        right = 8 + (22 if _bool(self._p.get("ShowClear")) else 0) + (22 if self._p.get("ErrorText") else 0)
        if _bool(self._p.get("MultiLine")):
            self._entry.place(x=left, y=5, width=max(4, w - left - right), height=max(4, h - 10))
        else:
            eh = tkfont.Font(font=self.font()).metrics("linespace") + 2
            self._entry.place(x=left, y=(h - eh) / 2, width=max(4, w - left - right), height=eh)

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "Text" and self._entry is not None and str(value) != self._get():
            e = self._entry
            st = e.cget("state")
            e.configure(state="normal")
            if isinstance(e, tk.Text):
                e.delete("1.0", "end")
                e.insert("1.0", str(value))
            else:
                e.delete(0, "end")
                e.insert(0, str(value))
            e.configure(state=st)
            self._typed()
        elif name in ("MultiLine", "PasswordChar", "ReadOnly", "Style", "FontName", "FontSize"):
            self._make()

    def draw(self):
        t, w, h = self.T, self.W(), self.H()
        self.background()
        self._place()
        focused = self.focus_get() is self._entry
        err = bool(self._p.get("ErrorText"))
        border = "#C62828" if err else self.accent if focused else t["border"]
        self.rrect(1, 1, w - 2, h - 2, 4, fill=self._p.get("BackColor") or t["input"], outline=border)
        if self._p.get("Icon"):
            self.label(10, h / 2 if not _bool(self._p.get("MultiLine")) else 14, glyph(self._p.get("Icon")),
                       blend(t["input_text"], t["input"], .35))
        if not self._get() and self._p.get("Watermark") and not focused and not _bool(self._p.get("MultiLine")):
            self.label(8 + (22 if self._p.get("Icon") else 0), h / 2, self._p.get("Watermark"), blend(t["input_text"], t["input"], .5))
            if self._entry is not None:
                self._entry.lower()
        elif self._entry is not None:
            self._entry.lift()
        x = w - 16
        if _bool(self._p.get("ShowClear")) and self._get():
            self.label(x, h / 2, "✕", blend(t["input_text"], t["input"], .3), "center")
            x -= 22
        if err:
            self.label(x, h / 2, "✖", "#C62828", "center")

    def press(self, x, y):
        if _bool(self._p.get("ShowClear")) and x > self.W() - 26:
            self.Text = ""
        elif self._p.get("Icon") and x < 30:
            self._raise("IconClick")
        if self._entry is not None:
            self._entry.focus_set()

    def Clear(self):
        self.Text = ""

    def SelectAll(self):
        if isinstance(self._entry, tk.Entry):
            self._entry.select_range(0, "end")

    def AppendText(self, s):
        self.Text = self._get() + str(s)

    def Focus(self):
        if self._entry is not None:
            self._entry.focus_set()


class RmComboBox(_Base):
    PROPS = {"Items": "", "SelectedIndex": -1, "Watermark": "", "DropDownStyle": "DropDownList"}

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "SelectedIndex" and int(_num(old, -1)) != int(_num(value, -1)):
            its = _items(self._p.get("Items"))
            i = int(_num(value, -1))
            self._p["Text"] = its[i].get("Text", "") if 0 <= i < len(its) else ""
            self._raise("SelectedIndexChanged")
            self._raise("TextChanged")
        if name == "Text":
            its = _items(self._p.get("Items"))
            for i, it in enumerate(its):
                if it.get("Text") == value and int(_num(self._p.get("SelectedIndex"), -1)) != i:
                    self._p["SelectedIndex"] = i
                    self._raise("SelectedIndexChanged")

    @property
    def SelectedItem(self):
        its = _items(self._p.get("Items"))
        i = int(_num(self._p.get("SelectedIndex"), -1))
        return its[i].get("Text", "") if 0 <= i < len(its) else ""

    @property
    def ListCount(self):
        return len(_items(self._p.get("Items")))

    def draw(self):
        t, w, h = self.T, self.W(), self.H()
        self.background()
        self.rrect(1, 1, w - 2, h - 2, 4, fill=blend(t["input"], t["hot"], .5 if self._inside else 0),
                   outline=self.accent if self.focus_get() is self else t["border"])
        its = _items(self._p.get("Items"))
        i = int(_num(self._p.get("SelectedIndex"), -1))
        if 0 <= i < len(its):
            it = its[i]
            g = glyph(it.get("Image"))
            self.label(8, h / 2, ((g + "  ") if g else "") + it.get("Text", ""), t["input_text"])
        elif self._p.get("Watermark"):
            self.label(8, h / 2, self._p.get("Watermark"), blend(t["input_text"], t["input"], .5))
        self.label(w - 13, h / 2, "⌄", t["input_text"], "center")

    def click(self, x, y):
        self.ShowDropDown()

    def ShowDropDown(self):
        menu = tk.Menu(self, tearoff=0)
        for i, it in enumerate(_items(self._p.get("Items"))):
            menu.add_command(label=(glyph(it.get("Image")) + "  " if it.get("Image") else "") + it.get("Text", ""),
                             command=lambda k=i: setattr(self, "SelectedIndex", k))
        menu.tk_popup(self.winfo_rootx(), self.winfo_rooty() + self.H())

    def _set_items(self, its):
        self._p["Items"] = ";".join(it.get("Text", "") for it in its)
        self.redraw()

    def AddItem(self, text):
        its = _items(self._p.get("Items"))
        its.append({"Text": str(text)})
        self._set_items(its)
        return len(its) - 1

    def RemoveItem(self, index):
        its = _items(self._p.get("Items"))
        i = int(_num(index, -1))
        if 0 <= i < len(its):
            del its[i]
            self._set_items(its)
            if int(_num(self._p.get("SelectedIndex"), -1)) >= len(its):
                self.SelectedIndex = -1

    def Clear(self):
        self._set_items([])
        self.SelectedIndex = -1

    def List(self, index):
        its = _items(self._p.get("Items"))
        i = int(_num(index, -1))
        return its[i].get("Text", "") if 0 <= i < len(its) else ""

    def IndexOf(self, text):
        for i, it in enumerate(_items(self._p.get("Items"))):
            if str(it.get("Text", "")).lower() == str(text).lower():
                return i
        return -1

    def key(self, k):
        n = len(_items(self._p.get("Items")))
        i = int(_num(self._p.get("SelectedIndex"), -1))
        if k == "Down" and i < n - 1:
            self.SelectedIndex = i + 1
        elif k == "Up" and i > 0:
            self.SelectedIndex = i - 1
        elif k in ("space", "Return", "F4"):
            self.ShowDropDown()


class RmSlider(_Base):
    PROPS = {"Value": 0, "Minimum": 0, "Maximum": 100, "TickFrequency": 0, "SmallChange": 1, "LargeChange": 10, "ShowValue": False}

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "Value":
            v = max(_num(self._p.get("Minimum")), min(_num(self._p.get("Maximum"), 100), _num(value)))
            self._p["Value"] = int(v) if float(v).is_integer() else v
            if _num(old) != _num(self._p["Value"]):
                self._raise("ValueChanged")

    def _geo(self):
        w, h = self.W(), self.H()
        return 10, w - 10, h - 14 if h > 30 else h / 2

    def draw(self):
        t = self.T
        self.background()
        x0, x1, ty = self._geo()
        lo, hi, v = _num(self._p.get("Minimum")), _num(self._p.get("Maximum"), 100), _num(self._p.get("Value"))
        f = 0 if hi <= lo else (v - lo) / (hi - lo)
        self.rrect(x0, ty - 2, x1, ty + 2, 2, fill=blend(t["border"], t["window"], .25))
        self.rrect(x0, ty - 2, x0 + (x1 - x0) * f, ty + 2, 2, fill=self.accent)
        tick = int(_num(self._p.get("TickFrequency")))
        if tick > 0 and hi > lo:
            val = lo
            while val <= hi:
                tx = x0 + (x1 - x0) * (val - lo) / (hi - lo)
                self.create_line(tx, ty + 9, tx, ty + 12, fill=blend(t["border"], t["window"], .2))
                val += tick
        cx = x0 + (x1 - x0) * f
        self.create_oval(cx - 9, ty - 9, cx + 9, ty + 9, fill=t["input"], outline=blend(t["border"], self.accent, .4))
        self.create_oval(cx - 4, ty - 4, cx + 4, ty + 4, fill=self.accent, outline="")
        if (_bool(self._p.get("ShowValue")) or self._inside) and self.H() > 30:
            self.label(cx, ty - 20, int(v) if float(v).is_integer() else v, t["text"], "center")

    def _set_from(self, x):
        x0, x1, _ty = self._geo()
        lo, hi = _num(self._p.get("Minimum")), _num(self._p.get("Maximum"), 100)
        self.Value = round(lo + (hi - lo) * max(0, min(1, (x - x0) / max(1, x1 - x0))))

    def press(self, x, y):
        self._set_from(x)
        self.bind("<B1-Motion>", lambda e: self._set_from(e.x))

    def wheel(self, d):
        self.Value = _num(self._p.get("Value")) + d * _num(self._p.get("SmallChange"), 1)

    def key(self, k):
        s, big = _num(self._p.get("SmallChange"), 1), _num(self._p.get("LargeChange"), 10)
        d = {"Right": s, "Up": s, "Left": -s, "Down": -s, "Prior": big, "Next": -big}.get(k)
        if d:
            self.Value = _num(self._p.get("Value")) + d
        elif k == "Home":
            self.Value = self._p.get("Minimum")
        elif k == "End":
            self.Value = self._p.get("Maximum")


# ====================================================================== indicators
class RmProgress(_Base):
    PROPS = {"Value": 0, "Minimum": 0, "Maximum": 100, "Kind": "Bar", "ShowText": False, "TextFormat": ""}

    def init(self):
        object.__setattr__(self, "_phase", 0)
        self.after(40, self._tick)

    def _tick(self):
        try:
            if self._p.get("Kind") == "Marquee":
                object.__setattr__(self, "_phase", (self._phase + 3) % 200)
                self.redraw()
            self.after(40, self._tick)
        except tk.TclError:
            pass

    def _f(self):
        lo, hi, v = _num(self._p.get("Minimum")), _num(self._p.get("Maximum"), 100), _num(self._p.get("Value"))
        return 0 if hi <= lo else max(0.0, min(1.0, (v - lo) / (hi - lo)))

    def _text(self):
        pct = str(round(self._f() * 100))
        fmt = str(self._p.get("TextFormat") or "")
        return fmt.replace("{0}", pct) if fmt else pct + "%"

    def draw(self):
        t, w, h = self.T, self.W(), self.H()
        self.background()
        track = blend(t["window"], t["text"], .18 if t["dark"] else .12)
        f = self._f()
        if self._p.get("Kind") == "Circle":
            s = min(w, h)
            lw = max(3, s / 10)
            x0, y0 = (w - s) / 2 + lw / 2, (h - s) / 2 + lw / 2
            self.create_oval(x0, y0, x0 + s - lw, y0 + s - lw, outline=track, width=lw)
            if f > 0:
                self.create_arc(x0, y0, x0 + s - lw, y0 + s - lw, start=90, extent=-359.9 * f, style="arc", outline=self.accent, width=lw)
            if s >= 40 or _bool(self._p.get("ShowText")):
                self.label(w / 2, h / 2, self._text(), t["text"], "center", self.font(1.6 if s >= 80 else 1.0, True))
            return
        show = _bool(self._p.get("ShowText")) and h >= 14
        bh = h if show or h < 14 else 6
        by = (h - bh) / 2
        self.rrect(0, by, w - 1, by + bh, bh / 2 if not show else 3, fill=track)
        if self._p.get("Kind") == "Marquee":
            seg = w / 3
            x = (w + seg) * self._phase / 200 - seg
            self.rrect(max(0, x), by, min(w - 1, x + seg), by + bh, bh / 2 if not show else 3, fill=self.accent)
        elif f > 0:
            self.rrect(0, by, max(bh, (w - 1) * f), by + bh, bh / 2 if not show else 3, fill=self.accent)
        if show and self._p.get("Kind") != "Marquee":
            self.label(w / 2, h / 2, self._text(), t["text"], "center")

    def Increment(self, d=1):
        self.Value = min(_num(self._p.get("Maximum"), 100), _num(self._p.get("Value")) + _num(d, 1))
        return self.Value

    PerformStep = Increment


class RmGauge(_Base):
    PROPS = {"Value": 0, "Minimum": 0, "Maximum": 100, "Ranges": "", "Unit": "", "Title": "", "Kind": "Circular", "Decimals": 0,
             "ShowTicks": True}

    def _ranges(self):
        out = []
        for part in str(self._p.get("Ranges") or "").split(";"):
            try:
                rng, col = part.split(":")
                a, b = rng.split("-")
                out.append((float(a), float(b), col.strip()))
            except ValueError:
                pass
        return out

    def draw(self):
        t, w, h = self.T, self.W(), self.H()
        self.background()
        lo, hi, v = _num(self._p.get("Minimum")), _num(self._p.get("Maximum"), 100), _num(self._p.get("Value"))
        span = (hi - lo) or 1
        f = max(0.0, min(1.0, (v - lo) / span))
        rngs = self._ranges()
        col = next((c for a, b, c in rngs if a <= v <= b), self.accent)
        fg = self._p.get("ForeColor") or t["text"]
        track = blend(t["window"], t["text"], .18 if t["dark"] else .1)
        unit = str(self._p.get("Unit", ""))
        val = f"{v:.{int(_num(self._p.get('Decimals')))}f}" + (f" {unit}" if unit else "")
        title = str(self._p.get("Title") or self._p.get("Text", ""))
        if self._p.get("Kind") == "Linear":
            y = h - 34
            self.rrect(8, y, w - 8, y + 10, 5, fill=track)
            for a, b, c in rngs:
                self.create_rectangle(8 + (w - 16) * max(0, (a - lo) / span), y + 7, 8 + (w - 16) * min(1, (b - lo) / span), y + 10,
                                      fill=c, outline="")
            self.rrect(8, y, 8 + (w - 16) * f, y + 7, 3, fill=col)
            x = 8 + (w - 16) * f
            self.create_polygon(x - 6, y - 9, x + 6, y - 9, x, y - 1, fill=fg)
            self.label(8, y + 20, title, fg, "w", self.font(1.0, True))
            self.label(w - 8, y + 20, val, fg, "e", self.font(1.0, True))
            return
        s = min(w, h * 0.98)
        lw = max(4, s / 12)
        d = s - lw - 4
        x, y = (w - d) / 2, (h - d * .88) / 2 + 2
        self.create_arc(x, y, x + d, y + d, start=-135 + 360, extent=-270, style="arc", outline=track, width=lw)
        for a, b, c in rngs:
            fa, fb = max(0, (a - lo) / span), min(1, (b - lo) / span)
            if fb > fa:
                k = lw * .85
                self.create_arc(x + k, y + k, x + d - k, y + d - k, start=225 - 270 * fa, extent=-270 * (fb - fa), style="arc",
                                outline=c, width=max(1, lw * .3))
        if f > 0:
            self.create_arc(x, y, x + d, y + d, start=225, extent=-270 * f, style="arc", outline=col, width=lw)
        cx, cy = x + d / 2, y + d / 2
        a = math.radians(135 + 270 * f)
        nr, nw = d / 2 - lw * 1.2, max(2, lw * .45)
        self.create_polygon(cx + math.cos(a) * nr, cy + math.sin(a) * nr, cx + math.cos(a + math.pi / 2) * nw,
                            cy + math.sin(a + math.pi / 2) * nw, cx + math.cos(a - math.pi / 2) * nw,
                            cy + math.sin(a - math.pi / 2) * nw, fill=fg)
        self.create_oval(cx - nw * 1.6, cy - nw * 1.6, cx + nw * 1.6, cy + nw * 1.6, fill=fg, outline="")
        vy = cy + d * .16 + nw * 1.6
        self.label(cx, vy, val, fg, "n", self.font(1.7 if d >= 120 else 1.15, True))
        if title:
            self.label(cx, vy + (26 if d >= 120 else 18), title, blend(fg, t["window"], .3), "n")


# ====================================================================== containers
class RmPanel(_Base):
    PROPS = {"Title": "", "CornerRadius": -1, "Shadow": False, "GradientTo": "", "BorderColor": ""}

    def draw(self):
        t, w, h = self.T, self.W(), self.H()
        try:
            self.configure(bg=self.master.cget("bg"))
        except tk.TclError:
            pass
        back = self._p.get("BackColor") or (blend(t["window"], "#FFFFFF", .06) if t["dark"] else t["input"])
        sh = 6 if _bool(self._p.get("Shadow")) else 0
        for i in range(sh, 0, -1):
            self.rrect(sh - i + 1, sh / 2 - i + 1 + sh / 2, w - sh + i - 1, h - sh + i - 1, 8 + i,
                       fill=blend(t["window"], "#000000", .035 * (sh - i + 1)))
        self.rrect(sh, sh / 2, w - sh, h - sh, int(_num(self._p.get("CornerRadius"), 8)) if _num(self._p.get("CornerRadius"), -1) >= 0 else 8,
                   fill=back, outline=self._p.get("BorderColor") or blend(t["border"], back, .35))
        for c in self.winfo_children():
            if isinstance(c, (tk.Label, tk.Checkbutton, tk.Radiobutton)):
                try:
                    c.configure(bg=back)
                except tk.TclError:
                    pass
        if self._p.get("Title"):
            self.label(sh + 12, sh / 2 + 15, self._p["Title"], self._p.get("ForeColor") or t["face_text"], "w", self.font(1.05, True))
            self.create_line(sh + 1, sh / 2 + 30, w - sh - 1, sh / 2 + 30, fill=blend(t["border"], back, .5))

    def click(self, x, y):
        self._raise("Click")


class RmGroupPanel(_Base):
    PROPS = {"Title": "", "Collapsed": False}

    def init(self):
        object.__setattr__(self, "_full", 0)

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "Collapsed" and _bool(old) != _bool(value):
            self._apply()
            self._raise("CollapsedChanged")

    def _apply(self):
        try:
            info = self.place_info()
        except tk.TclError:
            info = {}
        if _bool(self._p.get("Collapsed")):
            object.__setattr__(self, "_full", self.H())
            for c in self.winfo_children():
                tk.Misc.lower(c)
            if info:
                self.place_configure(height=30)
        else:
            for c in self.winfo_children():
                tk.Misc.tkraise(c)
            if info and self._full:
                self.place_configure(height=self._full)

    def draw(self):
        t, w, h = self.T, self.W(), self.H()
        back = self._p.get("BackColor") or (blend(t["window"], "#FFFFFF", .06) if t["dark"] else t["input"])
        self.rrect(1, 1, w - 2, h - 2, 5, fill=back, outline=blend(t["border"], back, .35))
        self.rrect(2, 2, w - 3, 30, 4, fill=blend(back, t["text"], .08 if self._inside else .04))
        fg = self._p.get("ForeColor") or t["face_text"]
        self.label(16, 16, "›" if _bool(self._p.get("Collapsed")) else "⌄", fg, "center", self.font(1.2, True))
        self.label(30, 16, self._p.get("Title") or self._p.get("Text", ""), fg, "w", self.font(1.0, True))

    def press(self, x, y):
        if y < 30:
            self.Collapsed = not _bool(self._p.get("Collapsed"))

    def Toggle(self):
        self.Collapsed = not _bool(self._p.get("Collapsed"))

    def Expand(self):
        self.Collapsed = False

    def Collapse(self):
        self.Collapsed = True


class _PageCanvas(tk.Canvas):
    """One page of an RmTabStrip / RmNavigationPane: full size, draws the owner's header itself."""

    def __init__(self, owner, index):
        super().__init__(owner, highlightthickness=0, bd=0)
        self.owner, self.index = owner, index
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Button-1>", lambda e: owner._header_click(e.x, e.y))

    def redraw(self):
        self.delete("all")
        self.owner.paint_on(self)


class _Paged(_Base):
    """Base of the paged containers: page(i) returns the canvas the children of page i are placed on."""

    def init(self):
        object.__setattr__(self, "_pages", {})

    def page(self, i):
        i = int(i)
        if i not in self._pages:
            pc = _PageCanvas(self, i)
            self._pages[i] = pc
            pc.place(x=0, y=0, relwidth=1, relheight=1)
            self.after_idle(self._show)
        return self._pages[i]

    def _show(self):
        sel = int(_num(self._p.get("SelectedIndex"), 0))
        for i, pc in self._pages.items():
            if i == sel:
                pc.place(x=0, y=0, relwidth=1, relheight=1)
                tk.Misc.tkraise(pc)
                pc.redraw()
            else:
                pc.place_forget()

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "SelectedIndex" and int(_num(old, 0)) != int(_num(value, 0)):
            self._show()
            self._raise("SelectedIndexChanged")

    def draw(self):
        self.paint_on(self)
        for pc in getattr(self, "_pages", {}).values():
            if pc.winfo_ismapped():
                pc.redraw()

    def paint_on(self, cv):
        pass

    def _header_click(self, x, y):
        self.focus_set()
        self.click(x, y)


class RmTabStrip(_Paged):
    PROPS = {"TabPages": "TabPage1;TabPage2", "SelectedIndex": 0, "TabPosition": "Top", "Closable": False, "AutoClose": True}

    def _rects(self):
        tabs = _items(self._p.get("TabPages"))
        pos = self._p.get("TabPosition", "Top")
        if pos == "Left":
            return [(0, i * 34, 140, (i + 1) * 34) for i in range(len(tabs))]
        out, x = [], 0
        y0 = self.H() - 34 if pos == "Bottom" else 0
        for it in tabs:
            tw = self.text_w(it.get("Text", ""), self.font(1.0, True)) + 28 + (20 if _bool(self._p.get("Closable")) else 0) + (22 if it.get("Image") else 0)
            out.append((x, y0, x + tw, y0 + 34))
            x += tw
        return out

    def paint_on(self, cv):
        t, w, h = self.T, self.W(), self.H()
        back = self._p.get("BackColor") or t["window"]
        page = blend(t["window"], "#FFFFFF", .06) if t["dark"] else t["input"]
        bar = blend(back, t["text"], .04 if t["dark"] else .03)
        cv.configure(bg=page)
        pos = self._p.get("TabPosition", "Top")
        if pos == "Left":
            cv.create_rectangle(0, 0, 140, h, fill=bar, outline="")
        elif pos == "Bottom":
            cv.create_rectangle(0, h - 34, w, h, fill=bar, outline="")
        else:
            cv.create_rectangle(0, 0, w, 34, fill=bar, outline="")
        sel = int(_num(self._p.get("SelectedIndex"), 0))
        fg = self._p.get("ForeColor") or t["text"]
        for i, (it, (x0, y0, x1, y1)) in enumerate(zip(_items(self._p.get("TabPages")), self._rects())):
            if i == sel:
                cv.create_rectangle(x0, y0, x1, y1, fill=page, outline="")
                if pos == "Left":
                    cv.create_rectangle(x0, y0 + 6, x0 + 3, y1 - 6, fill=self.accent, outline="")
                else:
                    cv.create_rectangle(x0 + 8, y1 - 3, x1 - 8, y1, fill=self.accent, outline="")
            c = (fg if t["dark"] else self.accent) if i == sel else blend(fg, back, .35)
            g = glyph(it.get("Image"))
            cv.create_text(x0 + 14, (y0 + y1) / 2, text=((g + "  ") if g else "") + it.get("Text", ""), fill=c, anchor="w",
                           font=self.font(1.0, i == sel))
            if _bool(self._p.get("Closable")) and i == sel:
                cv.create_text(x1 - 14, (y0 + y1) / 2, text="✕", fill=c, font=self.font(.9))
        cv.create_rectangle(0, 0, w - 1, h - 1, outline=blend(t["border"], back, .4))

    def click(self, x, y):
        for i, (x0, y0, x1, y1) in enumerate(self._rects()):
            if x0 <= x < x1 and y0 <= y < y1:
                if _bool(self._p.get("Closable")) and x >= x1 - 24 and i == int(_num(self._p.get("SelectedIndex"), 0)):
                    tabs = _items(self._p.get("TabPages"))
                    self._raise("TabClosing", _name(tabs[i]), i)
                    if _bool(self._p.get("AutoClose", True)):
                        self.RemoveTab(i)
                    return
                self.SelectedIndex = i
                return

    def key(self, k):
        n = len(_items(self._p.get("TabPages")))
        i = int(_num(self._p.get("SelectedIndex"), 0))
        if k in ("Right", "Down") and n:
            self.SelectedIndex = (i + 1) % n
        elif k in ("Left", "Up") and n:
            self.SelectedIndex = (i - 1) % n

    @property
    def TabCount(self):
        return len(_items(self._p.get("TabPages")))

    @property
    def SelectedTab(self):
        tabs = _items(self._p.get("TabPages"))
        i = int(_num(self._p.get("SelectedIndex"), 0))
        return tabs[i].get("Text", "") if 0 <= i < len(tabs) else ""

    def AddTab(self, text):
        tabs = _items(self._p.get("TabPages")) + [{"Text": str(text)}]
        self._p["TabPages"] = json.dumps(tabs)
        self.redraw()
        return len(tabs) - 1

    def RemoveTab(self, index):
        tabs = _items(self._p.get("TabPages"))
        i = int(_num(index, -1))
        if 0 <= i < len(tabs):
            del tabs[i]
            self._p["TabPages"] = json.dumps(tabs)
            if int(_num(self._p.get("SelectedIndex"), 0)) >= len(tabs):
                self.SelectedIndex = max(0, len(tabs) - 1)
            self.redraw()

    def TabCaption(self, index, text=None):
        tabs = _items(self._p.get("TabPages"))
        i = int(_num(index, -1))
        if 0 <= i < len(tabs):
            if text is not None:
                tabs[i]["Text"] = str(text)
                self._p["TabPages"] = json.dumps(tabs)
                self.redraw()
            return tabs[i].get("Text", "")
        return ""

    def SelectTab(self, name):
        for i, it in enumerate(_items(self._p.get("TabPages"))):
            if str(name).lower() in (_name(it).lower(), str(it.get("Text", "")).lower()):
                self.SelectedIndex = i


class RmNavigationPane(_Paged):
    PROPS = {"Pages": "", "SelectedIndex": 0}

    def paint_on(self, cv):
        t, w, h = self.T, self.W(), self.H()
        back = self._p.get("BackColor") or (blend(t["window"], "#FFFFFF", .06) if t["dark"] else t["input"])
        cv.configure(bg=back)
        fg = self._p.get("ForeColor") or t["face_text"]
        btn = blend(back, t["text"], .05 if t["dark"] else .035)
        pages = _items(self._p.get("Pages"))
        sel = int(_num(self._p.get("SelectedIndex"), 0))
        cv.create_rectangle(0, 0, w, 34, fill=blend(back, self.accent, .1), outline="")
        if 0 <= sel < len(pages):
            cv.create_text(12, 17, text=pages[sel].get("Text", ""), anchor="w", fill=fg, font=self.font(1.15, True))
        top = h - len(pages) * 34
        for i, it in enumerate(pages):
            y = top + i * 34
            cv.create_rectangle(0, y, w, y + 34, fill=blend(btn, self.accent, .22) if i == sel else btn, outline=blend(t["border"], back, .4))
            if i == sel:
                cv.create_rectangle(1, y + 1, 4, y + 34, fill=self.accent, outline="")
            g = glyph(it.get("Image"))
            cv.create_text(12, y + 17, text=((g + "   ") if g else "") + it.get("Text", ""), anchor="w", fill=fg, font=self.font(1.0, i == sel))
        cv.create_rectangle(0, 0, w - 1, h - 1, outline=blend(t["border"], back, .4))

    def click(self, x, y):
        pages = _items(self._p.get("Pages"))
        top = self.H() - len(pages) * 34
        if y >= top and pages:
            self.SelectedIndex = min(len(pages) - 1, int((y - top) // 34))

    @property
    def SelectedPage(self):
        pages = _items(self._p.get("Pages"))
        i = int(_num(self._p.get("SelectedIndex"), 0))
        return pages[i].get("Text", "") if 0 <= i < len(pages) else ""

    @property
    def PageCount(self):
        return len(_items(self._p.get("Pages")))


class RmDockWindow(_Base):
    PROPS = {"Title": "", "DockSide": "Left", "AutoHide": False, "DockSize": 0}

    def draw(self):
        t, w, h = self.T, self.W(), self.H()
        back = self._p.get("BackColor") or t["window"]
        self.configure(bg=back)
        self.create_rectangle(0, 0, w - 1, h - 1, outline=blend(t["border"], back, .3))
        self.create_rectangle(1, 1, w - 1, 26, fill=blend(back, t["text"], .07), outline="")
        self.label(8, 13, self._p.get("Title") or self._p.get("Text", ""), t["text"], "w", self.font(1.0, True))
        self.label(w - 11, 13, "✕", t["text"], "center")

    def press(self, x, y):
        if y < 26 and x > self.W() - 22:
            self.place_forget()
            dock = self.master
            if isinstance(dock, RmDockPanel):
                dock._raise("WindowClosed", getattr(self, "_rad_name", ""), -1)
        elif isinstance(self.master, RmDockPanel):
            self.master._activate(self)


class RmDockPanel(_Base):
    PROPS = {"Layout": ""}

    def init(self):
        object.__setattr__(self, "_active", None)
        self.after(50, self._layout)
        self.bind("<Configure>", lambda _e: (self.redraw(), self._layout()), add="+")

    def _wins(self):
        return [c for c in self.winfo_children() if isinstance(c, RmDockWindow)]

    def _layout(self):
        try:
            w, h = self.W(), self.H()
        except tk.TclError:
            return
        left, top, right, bottom = 0, 0, w, h
        for side in ("Left", "Right", "Top", "Bottom"):
            ws = [c for c in self._wins() if c._p.get("DockSide") == side and c.winfo_manager()]
            if not ws:
                continue
            size = max(40, int(_num(ws[0]._p.get("DockSize"), 0)) or (ws[0].winfo_reqwidth() if side in ("Left", "Right") else ws[0].winfo_reqheight()) or 200)
            for c in ws:
                if side == "Left":
                    c.place(x=left, y=top, width=size, height=bottom - top)
                elif side == "Right":
                    c.place(x=right - size, y=top, width=size, height=bottom - top)
                elif side == "Top":
                    c.place(x=left, y=top, width=right - left, height=size)
                else:
                    c.place(x=left, y=bottom - size, width=right - left, height=size)
            if side == "Left":
                left += size + 4
            elif side == "Right":
                right -= size + 4
            elif side == "Top":
                top += size + 4
            else:
                bottom -= size + 4
        for c in self._wins():
            if c._p.get("DockSide") in ("Fill", "Float") and c.winfo_manager():
                c.place(x=left, y=top, width=max(4, right - left), height=max(4, bottom - top))

    def _activate(self, win):
        if win is not self._active:
            object.__setattr__(self, "_active", win)
            self._raise("ActiveWindowChanged", getattr(win, "_rad_name", ""), -1)

    def draw(self):
        self.configure(bg=blend(self.T["window"], self.T["text"], .06))

    def SaveLayout(self):
        return json.dumps([{"DockSide": c._p.get("DockSide"), "AutoHide": _bool(c._p.get("AutoHide"))} for c in self._wins()])

    def LoadLayout(self, s):
        self._layout()

    def Refresh(self):
        self._layout()


# ====================================================================== bars
class RmSideBar(_Base):
    PROPS = {"Items": "", "SelectedItem": "", "Collapsed": False, "ShowToggle": True}

    def init(self):
        object.__setattr__(self, "_rows", [])
        object.__setattr__(self, "_full", 0)

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "Collapsed" and _bool(old) != _bool(value):
            try:
                if _bool(value):
                    object.__setattr__(self, "_full", self.W())
                    self.place_configure(width=48)
                elif self._full:
                    self.place_configure(width=self._full)
            except tk.TclError:
                pass
            self._raise("CollapsedChanged")

    def _layout(self):
        rows, y = [], 40 if _bool(self._p.get("ShowToggle", True)) else 4
        for gi, it in enumerate(_items(self._p.get("Items"))):
            ks = _kids(it)
            if ks:
                rows.append(("group", it, y, 9 if _bool(self._p.get("Collapsed")) else 28, gi))
                y += rows[-1][3]
                for k, c in enumerate(ks):
                    rows.append(("item", c, y, 34, k))
                    y += 34
            else:
                rows.append(("item", it, y, 34, gi))
                y += 34
        object.__setattr__(self, "_rows", rows)
        return rows

    def draw(self):
        t, w = self.T, self.W()
        back = self._p.get("BackColor") or (blend(t["window"], "#000000", .25) if t["dark"] else blend(t["window"], t["text"], .035))
        self.configure(bg=back)
        fg = self._p.get("ForeColor") or t["text"]
        col = _bool(self._p.get("Collapsed"))
        if _bool(self._p.get("ShowToggle", True)):
            self.label(w / 2 if col else 22, 20, "☰", fg, "center", self.font(1.3))
            if not col and self._p.get("Text"):
                self.label(44, 20, self._p["Text"], fg, "w", self.font(1.05, True))
        sel = str(self._p.get("SelectedItem", "")).lower()
        for i, (kind, it, y, hh, _k) in enumerate(self._layout()):
            if kind == "group":
                if col:
                    self.create_line(10, y + 4, w - 10, y + 4, fill=blend(t["border"], back, .3))
                else:
                    self.label(14, y + 14, "⌄  " + it.get("Text", ""), blend(fg, back, .4), "w", self.font(.85, True))
                continue
            is_sel = sel and _name(it).lower() == sel
            if is_sel:
                self.rrect(4, y + 2, w - 5, y + hh - 2, 4, fill=blend(back, self.accent, .35 if t["dark"] else .16))
                self.create_rectangle(4, y + 8, 7, y + hh - 8, fill=self.accent, outline="")
            elif i == self._hover:
                self.rrect(4, y + 2, w - 5, y + hh - 2, 4, fill=blend(back, t["text"], .07))
            g = glyph(it.get("Image")) or (str(it.get("Text", " "))[:1] if col else "")
            if col:
                self.label(w / 2, y + hh / 2, g, self.accent if is_sel else fg, "center", self.font(1.2))
            else:
                self.label(16, y + hh / 2, ((g + "   ") if g else "") + it.get("Text", ""), fg, "w", self.font(1.0, bool(is_sel)))
            if it.get("Count"):
                x = w - 18 if not col else w - 10
                self.create_oval(x - 9, y + hh / 2 - 8 - (6 if col else 0), x + 9, y + hh / 2 + 8 - (6 if col else 0), fill=self.accent, outline="")
                self.label(x, y + hh / 2 - (6 if col else 0), it["Count"], on(self.accent), "center", self.font(.8, True))

    def hit(self, x, y):
        for i, (_k, _it, ry, hh, _x) in enumerate(self._rows):
            if ry <= y < ry + hh:
                return i
        return -1

    def press(self, x, y):
        if _bool(self._p.get("ShowToggle", True)) and y < 40:
            self.Collapsed = not _bool(self._p.get("Collapsed"))
            return
        i = self.hit(x, y)
        if i >= 0 and self._rows[i][0] == "item":
            _kind, it, _y, _h, k = self._rows[i]
            self._p["SelectedItem"] = _name(it)
            self.redraw()
            self._raise("ItemClick", _name(it), k)

    def SelectItem(self, name):
        self.SelectedItem = name

    def SetBadge(self, name, count):
        its = _items(self._p.get("Items"))

        def walk(lst):
            for it in lst:
                if _name(it).lower() == str(name).lower():
                    it["Count"] = int(_num(count))
                walk(_kids(it))
        walk(its)
        self._p["Items"] = json.dumps(its)
        self.redraw()

    def SetItemText(self, name, text):
        its = _items(self._p.get("Items"))

        def walk(lst):
            for it in lst:
                if _name(it).lower() == str(name).lower():
                    it["Text"] = str(text)
                walk(_kids(it))
        walk(its)
        self._p["Items"] = json.dumps(its)
        self.redraw()

    def Toggle(self):
        self.Collapsed = not _bool(self._p.get("Collapsed"))


class RmStatusBar(_Base):
    PROPS = {"Panels": "", "AccentBar": False}

    def init(self):
        object.__setattr__(self, "_vals", {})

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "Text" and _items(self._p.get("Panels")):
            self.SetPanelText(0, value)

    def _geo(self):
        panels = _items(self._p.get("Panels"))
        widths = []
        for it in panels:
            w = int(_num(it.get("Width")))
            if w <= 0 and it.get("Kind") == "Zoom":
                w = 160
            if w <= 0 and it.get("Kind") == "Progress":
                w = 120
            widths.append(w)
        springs = sum(1 for w in widths if w <= 0) or 1
        rest = max(0, self.W() - sum(w for w in widths if w > 0) - 4)
        out, x = [], 0
        for it, w in zip(panels, widths):
            w = w if w > 0 else rest / springs
            out.append((it, x, w))
            x += w
        return out

    def draw(self):
        t, h = self.T, self.H()
        acc = _bool(self._p.get("AccentBar"))
        back = self._p.get("BackColor") or (self.accent if acc else blend(t["window"], t["text"], .05 if t["dark"] else .04))
        fg = self._p.get("ForeColor") or (on(self.accent) if acc else t["text"])
        self.configure(bg=back)
        geo = self._geo()
        if not geo:
            self.label(8, h / 2, self._p.get("Text", ""), fg)
        for i, (it, x, w) in enumerate(geo):
            if i:
                self.create_line(x, 5, x, h - 5, fill=blend(back, fg, .25))
            kind = it.get("Kind", "Text")
            v = self._vals.get(i, _num(it.get("Value"), 100 if kind == "Zoom" else 0))
            if kind == "Progress":
                self.rrect(x + 8, h / 2 - 3, x + w - 8, h / 2 + 3, 3, fill=blend(back, fg, .18))
                self.rrect(x + 8, h / 2 - 3, x + 8 + max(6, (w - 16) * max(0, min(1, v / 100))), h / 2 + 3, 3, fill=fg if acc else self.accent)
            elif kind == "Zoom":
                self.label(x + 10, h / 2, "−", fg, "center")
                self.label(x + w - 54, h / 2, "+", fg, "center")
                self.create_line(x + 20, h / 2, x + w - 64, h / 2, fill=blend(back, fg, .4))
                tx = x + 20 + (w - 84) * max(0, min(1, (v - 10) / 390))
                self.create_rectangle(tx - 3, h / 2 - 6, tx + 3, h / 2 + 6, fill=fg, outline="")
                self.label(x + w - 4, h / 2, f"{int(v)}%", fg, "e")
            else:
                g = glyph(it.get("Image"))
                self.label(x + 8, h / 2, ((g + "  ") if g else "") + str(it.get("Text", "")), fg)

    def press(self, x, y):
        for i, (it, px, w) in enumerate(self._geo()):
            if px <= x < px + w:
                if it.get("Kind") == "Zoom":
                    v = self._vals.get(i, _num(it.get("Value"), 100))
                    v = v - 10 if x < px + 18 else v + 10 if x >= px + w - 62 else v
                    self._vals[i] = max(10, min(400, v))
                    self.redraw()
                    self._raise("ValueChanged")
                self._raise("PanelClick", _name(it), i)

    def _index(self, which):
        for i, (it, _x, _w) in enumerate(self._geo()):
            if _name(it).lower() == str(which).lower():
                return i
        return int(_num(which, -1))

    def SetPanelText(self, which, text):
        panels = _items(self._p.get("Panels"))
        i = self._index(which)
        if 0 <= i < len(panels):
            panels[i]["Text"] = str(text)
            self._p["Panels"] = json.dumps(panels)
            self.redraw()

    def GetPanelText(self, which):
        panels = _items(self._p.get("Panels"))
        i = self._index(which)
        return str(panels[i].get("Text", "")) if 0 <= i < len(panels) else ""

    def SetPanelValue(self, which, value):
        self._vals[self._index(which)] = _num(value)
        self.redraw()

    def GetPanelValue(self, which):
        panels = _items(self._p.get("Panels"))
        i = self._index(which)
        return self._vals.get(i, _num(panels[i].get("Value")) if 0 <= i < len(panels) else 0)

    @property
    def PanelCount(self):
        return len(_items(self._p.get("Panels")))


class RmRibbon(_Base):
    PROPS = {"Tabs": "", "QuickAccess": "", "AppMenu": "", "AppButtonText": "File", "SelectedTab": 0, "Collapsed": False}

    def init(self):
        object.__setattr__(self, "_hits", [])
        object.__setattr__(self, "_checked", {})
        object.__setattr__(self, "_values", {})
        object.__setattr__(self, "_disabled", set())

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "SelectedTab" and str(old) != str(value):
            tabs = _items(self._p.get("Tabs"))
            i = self._tab_index(value)
            self._p["SelectedTab"] = i
            if 0 <= i < len(tabs):
                self._raise("TabChanged", _name(tabs[i]), i)
        if name == "Collapsed" and _bool(old) != _bool(value):
            try:
                self.place_configure(height=(26 if _items(self._p.get("QuickAccess")) else 0) + 31 if _bool(value) else
                                     getattr(self, "_full_h", 154))
            except tk.TclError:
                pass
            self._raise("CollapsedChanged")

    def _tab_index(self, v):
        tabs = _items(self._p.get("Tabs"))
        for i, it in enumerate(tabs):
            if str(v).lower() in (_name(it).lower(), str(it.get("Text", "")).lower()):
                return i
        return int(_num(v, 0))

    def _find(self, name):
        def walk(lst):
            for it in lst:
                if _name(it).lower() == str(name).lower():
                    return it
                r = walk(_kids(it))
                if r is not None:
                    return r
            return None
        return walk(_items(self._p.get("Tabs")))

    def draw(self):
        t, w, h = self.T, self.W(), self.H()
        if not _bool(self._p.get("Collapsed")):
            object.__setattr__(self, "_full_h", h)
        back = self._p.get("BackColor") or (blend(t["window"], "#000000", .2) if t["dark"] else blend(t["window"], t["text"], .03))
        body = blend(t["window"], "#FFFFFF", .05) if t["dark"] else t["input"]
        fg = self._p.get("ForeColor") or t["text"]
        self.configure(bg=back)
        hits = []
        qat = _items(self._p.get("QuickAccess"))
        top = 26 if qat else 0
        for i, q in enumerate(qat):
            x = 6 + i * 26
            self.label(x + 12, 13, glyph(q.get("Image") or q.get("Text")), fg, "center")
            hits.append(("item", x, 0, x + 24, 24, q, i))
        x = 0
        app = str(self._p.get("AppButtonText", ""))
        if app:
            aw = self.text_w(app) + 28
            self.rrect(0, top + 2, aw, top + 30, 3, fill=self.accent)
            self.label(aw / 2, top + 16, app, on(self.accent), "center")
            hits.append(("app", 0, top, aw, top + 30, None, -1))
            x = aw + 4
        tabs = _items(self._p.get("Tabs"))
        sel = self._tab_index(self._p.get("SelectedTab", 0))
        col = _bool(self._p.get("Collapsed"))
        if not col:
            self.create_rectangle(0, top + 30, w, h, fill=body, outline="")
        for i, tab in enumerate(tabs):
            tw = self.text_w(tab.get("Text", "")) + 28
            if i == sel and not col:
                self.create_rectangle(x, top + 3, x + tw, top + 31, fill=body, outline=blend(t["border"], back, .45))
                self.create_line(x + 1, top + 30, x + tw, top + 30, fill=body)
            if i == sel:
                self.create_rectangle(x + 10, top + 27, x + tw - 10, top + 29, fill=tab.get("Color") or self.accent, outline="")
            self.label(x + tw / 2, top + 16, tab.get("Text", ""), tab.get("Color") or ((fg if t["dark"] else self.accent) if i == sel else fg), "center")
            hits.append(("tab", x, top, x + tw, top + 30, tab, i))
            x += tw
        self.label(w - 15, top + 15, "⌄" if col else "⌃", fg, "center")
        hits.append(("collapse", w - 26, top, w, top + 30, None, -1))
        if not col and 0 <= sel < len(tabs):
            gx, gy = 4, top + 33
            for grp in _kids(tabs[sel]):
                colx, row, colw = gx + 6, 0, 0
                for k, it in enumerate(_kids(grp)):
                    if it.get("Text") == "-":
                        if row:
                            colx, row, colw = colx + colw + 6, 0, 0
                        self.create_line(colx + 3, gy + 4, colx + 3, gy + 68, fill=blend(t["border"], body, .4))
                        colx += 6
                        continue
                    name = _name(it)
                    checked = self._checked.get(name.lower(), _bool(it.get("Checked")))
                    large = _bool(it.get("Large")) or it.get("Size") == "Large"
                    if large:
                        if row:
                            colx, row, colw = colx + colw + 6, 0, 0
                        bw = max(48, self.text_w(it.get("Text", "")) + 12)
                        if checked:
                            self.rrect(colx, gy + 2, colx + bw, gy + 70, 3, fill=blend(body, self.accent, .2))
                        self.label(colx + bw / 2, gy + 22, glyph(it.get("Image")) or "★", self.accent, "center", self.font(2.2))
                        self.label(colx + bw / 2, gy + 50, it.get("Text", ""), fg, "n", width=bw)
                        hits.append(("item", colx, gy + 2, colx + bw, gy + 70, it, k))
                        colx += bw + 2
                    else:
                        combo = it.get("Kind") == "Combo"
                        bw = 130 if combo else 34 + self.text_w(it.get("Text", "")) + (12 if _kids(it) else 0)
                        y = gy + 3 + row * 24
                        if checked:
                            self.rrect(colx, y, colx + bw, y + 22, 3, fill=blend(body, self.accent, .2), outline=blend(body, self.accent, .5))
                        if combo:
                            lw = self.text_w(it.get("Text", "")) + 6
                            self.label(colx, y + 11, it.get("Text", ""), fg)
                            self.rrect(colx + lw, y + 1, colx + bw, y + 21, 2, fill=t["input"], outline=t["border"])
                            self.label(colx + lw + 5, y + 11, self._values.get(name.lower(), it.get("Value", "")), t["input_text"])
                        else:
                            g = glyph(it.get("Image"))
                            self.label(colx + 12, y + 11, g, self.accent, "center")
                            self.label(colx + 26, y + 11, it.get("Text", ""), fg)
                        hits.append(("item", colx, y, colx + bw, y + 22, it, k))
                        colw = max(colw, bw)
                        row += 1
                        if row == 3:
                            colx, row, colw = colx + colw + 2, 0, 0
                if row:
                    colx += colw + 2
                gw = max(colx - gx + 4, self.text_w(grp.get("Text", "")) + 16)
                self.label(gx + gw / 2, gy + 81, grp.get("Text", ""), blend(fg, body, .4), "center")
                self.create_line(gx + gw + 1, gy + 4, gx + gw + 1, gy + 86, fill=blend(t["border"], back, .45))
                gx += gw + 3
        object.__setattr__(self, "_hits", hits)

    def click(self, x, y):
        for kind, x0, y0, x1, y1, it, k in self._hits:
            if x0 <= x < x1 and y0 <= y < y1:
                if kind == "tab":
                    self.SelectedTab = k
                    if _bool(self._p.get("Collapsed")):
                        self.Collapsed = False
                elif kind == "collapse":
                    self.Collapsed = not _bool(self._p.get("Collapsed"))
                elif kind == "app":
                    app = _items(self._p.get("AppMenu"))
                    if app:
                        self._menu(app, 0, self.H(), None)
                    else:
                        self._raise("ItemClick", "AppButton", -1)
                elif it is not None:
                    name = _name(it)
                    target = self._find(name) or it
                    if name.lower() in self._disabled:
                        return
                    if _kids(it) or it.get("Kind") in ("Combo", "DropDown"):
                        self._menu(_kids(it), x0, y1, it)
                        return
                    if target.get("Kind") in ("Check", "Toggle"):
                        self._checked[name.lower()] = not self._checked.get(name.lower(), _bool(target.get("Checked")))
                        self.redraw()
                    self._raise("ItemClick", name, k)
                return

    def _menu(self, its, x, y, owner):
        menu = tk.Menu(self, tearoff=0)
        for i, it in enumerate(its):
            if it.get("Text") == "-":
                menu.add_separator()
                continue

            def pick(it=it, i=i):
                if owner is not None and owner.get("Kind") == "Combo":
                    self._values[_name(owner).lower()] = it.get("Text", "")
                    self.redraw()
                    self._raise("ItemClick", _name(owner), i)
                else:
                    self._raise("ItemClick", _name(it), i)
            menu.add_command(label=it.get("Text", ""), command=pick)
        menu.tk_popup(self.winfo_rootx() + int(x), self.winfo_rooty() + int(y))

    def SetChecked(self, name, value):
        self._checked[str(name).lower()] = _bool(value)
        self.redraw()

    def GetChecked(self, name):
        it = self._find(name)
        return self._checked.get(str(name).lower(), _bool(it.get("Checked")) if it else False)

    def SetEnabled(self, name, value):
        (self._disabled.discard if _bool(value) else self._disabled.add)(str(name).lower())

    def SetItemText(self, name, text):
        tabs = _items(self._p.get("Tabs"))

        def walk(lst):
            for it in lst:
                if _name(it).lower() == str(name).lower():
                    it["Text"] = str(text)
                walk(_kids(it))
        walk(tabs)
        self._p["Tabs"] = json.dumps(tabs)
        self.redraw()

    def SetValue(self, name, value):
        self._values[str(name).lower()] = str(value)
        self.redraw()

    def GetValue(self, name):
        it = self._find(name)
        return self._values.get(str(name).lower(), it.get("Value", "") if it else "")

    def SelectTab(self, name):
        self.SelectedTab = name

    def Toggle(self):
        self.Collapsed = not _bool(self._p.get("Collapsed"))


# ====================================================================== data views
def _columns(v):
    s = v if isinstance(v, str) else json.dumps(v or [])
    if s.strip().startswith("["):
        try:
            return [c if isinstance(c, dict) else {"Text": str(c)} for c in json.loads(s)]
        except ValueError:
            return []
    out = []
    for part in [x for x in s.split(";") if x]:
        bits = part.split(":")
        out.append({"Text": bits[0], "Type": bits[1] if len(bits) > 1 else "Text", "Width": int(_num(bits[2])) if len(bits) > 2 else 0})
    return out


def _rows(v):
    if isinstance(v, list):
        return [[str(c) for c in (r if isinstance(r, list) else [r])] for r in v]
    s = str(v or "").strip()
    if s.startswith("["):
        try:
            data = json.loads(s)
        except ValueError:
            return []
        out = []
        for r in data:
            if isinstance(r, dict):
                out.append([str(r.get("Text", ""))] + [str(x) for x in (r.get("SubItems") or [])])
            elif isinstance(r, list):
                out.append([str(x) for x in r])
            else:
                out.append([str(r)])
        return out
    return [row.split("|") for row in s.split(";")] if s else []


class RmGrid(_Base):
    PROPS = {"Columns": "Column1;Column2", "Rows": "", "ReadOnly": False, "AllowSort": True, "AllowFilter": False, "GroupBy": "",
             "SelectionMode": "FullRowSelect", "AlternatingRows": True, "RowHeight": 28}

    def init(self):
        object.__setattr__(self, "_data", _rows(self._p.get("Rows")))
        object.__setattr__(self, "_sort", (-1, False))
        object.__setattr__(self, "_sel", -1)
        object.__setattr__(self, "_col", -1)
        object.__setattr__(self, "_top", 0)
        object.__setattr__(self, "_filters", {})

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "Rows":
            object.__setattr__(self, "_data", _rows(value))

    def _cols(self):
        return _columns(self._p.get("Columns"))

    def _view(self):
        idx = [i for i, r in enumerate(self._data)
               if all(str(f).lower() in (r[k] if k < len(r) else "").lower() for k, f in self._filters.items() if f)]
        col, desc = self._sort
        cols = self._cols()
        if 0 <= col < len(cols):
            num = cols[col].get("Type") in ("Number", "Progress")
            idx.sort(key=lambda i: (_num(self._cell(i, col)) if num else self._cell(i, col).lower()), reverse=desc)
        return idx

    def _cell(self, r, c):
        row = self._data[r] if 0 <= r < len(self._data) else []
        return row[c] if 0 <= c < len(row) else ""

    def draw(self):
        t, w, h = self.T, self.W(), self.H()
        back = self._p.get("BackColor") or t["input"]
        fg = self._p.get("ForeColor") or t["input_text"]
        self.configure(bg=back)
        cols = self._cols()
        hh, fh, rh = 30, 26 if _bool(self._p.get("AllowFilter")) else 0, int(_num(self._p.get("RowHeight"), 28)) or 28
        self.create_rectangle(0, 0, w, hh, fill=blend(back, t["text"], .08 if t["dark"] else .045), outline="")
        x = 0
        xs = []
        for k, c in enumerate(cols):
            cw = int(_num(c.get("Width"))) or 110
            xs.append((x, cw))
            arrow = (" ▴" if not self._sort[1] else " ▾") if self._sort[0] == k else ""
            self.label(x + 8, hh / 2, c.get("Text", "") + arrow, fg, "w", self.font(1.0, True))
            self.create_line(x + cw - 1, 6, x + cw - 1, hh - 6, fill=blend(t["border"], back, .55))
            x += cw
        if fh:
            for k, (x, cw) in enumerate(xs):
                self.label(x + 8, hh + fh / 2, "▽ " + str(self._filters.get(k, "")), blend(fg, back, .4), "w")
        y = hh + fh
        for vi, r in enumerate(self._view()[self._top:]):
            if y > h:
                break
            if r == self._sel:
                self.create_rectangle(0, y, w, y + rh, fill=blend(back, self.accent, .35 if t["dark"] else .16), outline="")
                self.create_rectangle(0, y, 3, y + rh, fill=self.accent, outline="")
            elif _bool(self._p.get("AlternatingRows", True)) and (vi + self._top) % 2:
                self.create_rectangle(0, y, w, y + rh, fill=blend(back, t["text"], .035 if t["dark"] else .022), outline="")
            for k, (x, cw) in enumerate(xs):
                v = self._cell(r, k)
                typ = cols[k].get("Type", "Text")
                if typ == "Check":
                    on_ = _bool(v)
                    self.rrect(x + cw / 2 - 8, y + rh / 2 - 8, x + cw / 2 + 8, y + rh / 2 + 8, 3, fill=self.accent if on_ else t["input"],
                               outline="" if on_ else blend(t["border"], fg, .2))
                    if on_:
                        self.create_line(x + cw / 2 - 5, y + rh / 2, x + cw / 2 - 1.5, y + rh / 2 + 4, x + cw / 2 + 6, y + rh / 2 - 4,
                                         fill=on(self.accent), width=2)
                elif typ == "Progress":
                    f = max(0, min(1, _num(v) / 100))
                    bw = cw - 50
                    self.rrect(x + 8, y + rh / 2 - 4, x + 8 + bw, y + rh / 2 + 4, 4, fill=blend(back, fg, .15))
                    self.rrect(x + 8, y + rh / 2 - 4, x + 8 + max(8, bw * f), y + rh / 2 + 4, 4, fill=self.accent)
                    self.label(x + cw - 6, y + rh / 2, v, fg, "e")
                elif typ == "Button":
                    self.rrect(x + 5, y + 4, x + cw - 5, y + rh - 4, 4, fill=t["face"], outline=t["border"])
                    self.label(x + cw / 2, y + rh / 2, v or cols[k].get("Text", ""), t["face_text"], "center")
                elif typ == "Image":
                    self.label(x + cw / 2, y + rh / 2, glyph(v), self.accent, "center")
                else:
                    self.label(x + cw - 8 if typ == "Number" else x + 8, y + rh / 2, v, fg, "e" if typ == "Number" else "w")
            self.create_line(0, y + rh - 1, w, y + rh - 1, fill=blend(t["border"], back, .55))
            y += rh
        self.create_rectangle(0, 0, w - 1, h - 1, outline=blend(t["border"], back, .3))

    def _hit(self, x, y):
        cols = self._cols()
        hh, fh, rh = 30, 26 if _bool(self._p.get("AllowFilter")) else 0, int(_num(self._p.get("RowHeight"), 28)) or 28
        cx, col = 0, -1
        for k, c in enumerate(cols):
            cw = int(_num(c.get("Width"))) or 110
            if cx <= x < cx + cw:
                col = k
            cx += cw
        if y < hh:
            return "head", -1, col
        if y < hh + fh:
            return "filter", -1, col
        view = self._view()
        vi = self._top + int((y - hh - fh) // rh)
        return ("cell", view[vi], col) if 0 <= vi < len(view) else ("none", -1, col)

    def press(self, x, y):
        area, r, c = self._hit(x, y)
        cols = self._cols()
        if area == "head" and c >= 0 and _bool(self._p.get("AllowSort", True)):
            col, desc = self._sort
            object.__setattr__(self, "_sort", (c, not desc if col == c else False))
            self.redraw()
            self._raise("ColumnHeaderClick", cols[c].get("Text", ""), c)
        elif area == "filter" and c >= 0:
            from tkinter import simpledialog
            v = simpledialog.askstring("Filter", cols[c].get("Text", ""), initialvalue=self._filters.get(c, ""), parent=self)
            if v is not None:
                self._filters[c] = v
                self.redraw()
        elif area == "cell":
            changed = r != self._sel
            object.__setattr__(self, "_sel", r)
            object.__setattr__(self, "_col", c)
            self.redraw()
            if changed:
                self._raise("SelectionChanged")
            self._raise("CellClick", None, -1, r, c)
            typ = cols[c].get("Type", "Text") if 0 <= c < len(cols) else ""
            if typ == "Check" and not _bool(self._p.get("ReadOnly")):
                self.SetCell(r, c, "False" if _bool(self._cell(r, c)) else "True")
                self._raise("CellValueChanged", None, -1, r, c)
            elif typ == "Button":
                self._raise("ButtonCellClick", None, -1, r, c)

    def double(self, x, y):
        area, r, c = self._hit(x, y)
        cols = self._cols()
        if area != "cell" or c < 0:
            return
        self._raise("CellDoubleClick", None, -1, r, c)
        if _bool(self._p.get("ReadOnly")) or cols[c].get("ReadOnly") or cols[c].get("Type", "Text") not in ("Text", "Number", "Date", "Combo"):
            return
        from tkinter import simpledialog
        v = simpledialog.askstring(cols[c].get("Text", ""), "", initialvalue=self._cell(r, c), parent=self)
        if v is not None and v != self._cell(r, c):
            self.SetCell(r, c, v)
            self._raise("CellValueChanged", None, -1, r, c)

    def wheel(self, d):
        object.__setattr__(self, "_top", max(0, min(len(self._data) - 1, self._top - d * 3)))
        self.redraw()

    def key(self, k):
        view = self._view()
        if not view:
            return
        i = view.index(self._sel) if self._sel in view else -1
        if k in ("Down", "Up"):
            i = max(0, min(len(view) - 1, i + (1 if k == "Down" else -1)))
            object.__setattr__(self, "_sel", view[i])
            self.redraw()
            self._raise("SelectionChanged")

    @property
    def RowCount(self):
        return len(self._data)

    @property
    def ColumnCount(self):
        return len(self._cols())

    @property
    def SelectedRow(self):
        return self._sel

    @SelectedRow.setter
    def SelectedRow(self, v):
        object.__setattr__(self, "_sel", int(_num(v, -1)))
        self.redraw()

    @property
    def CurrentColumn(self):
        return self._col

    def _cells(self, args):
        if len(args) > 1:
            return [str(a) for a in args]
        s = str(args[0]) if args else ""
        return s.split("|") if "|" in s else s.split(";")

    def AddRow(self, *args):
        self._data.append(self._cells(args))
        self.redraw()
        return len(self._data) - 1

    def InsertRow(self, index, cells):
        self._data.insert(int(_num(index)), self._cells([cells]))
        self.redraw()

    def RemoveRow(self, index):
        i = int(_num(index, -1))
        if 0 <= i < len(self._data):
            del self._data[i]
            self.redraw()

    def Clear(self):
        self._data.clear()
        object.__setattr__(self, "_sel", -1)
        self.redraw()

    def _col_index(self, c):
        for k, col in enumerate(self._cols()):
            if str(c).lower() in (str(col.get("Text", "")).lower(), str(col.get("Name", "")).lower()):
                return k
        return int(_num(c, -1))

    def GetCell(self, row, col):
        return self._cell(int(_num(row, -1)), self._col_index(col))

    def SetCell(self, row, col, value):
        r, c = int(_num(row, -1)), self._col_index(col)
        if 0 <= r < len(self._data) and c >= 0:
            while len(self._data[r]) <= c:
                self._data[r].append("")
            self._data[r][c] = str(value)
            self.redraw()

    def GetRow(self, row):
        r = int(_num(row, -1))
        return "|".join(self._data[r]) if 0 <= r < len(self._data) else ""

    def SortBy(self, col, desc=False):
        object.__setattr__(self, "_sort", (self._col_index(col), _bool(desc) or str(desc) == "Descending"))
        self.redraw()

    def SetFilter(self, col, text):
        self._filters[self._col_index(col)] = str(text)
        self.redraw()

    def ClearFilter(self):
        self._filters.clear()
        self.redraw()

    def SetColumnWidth(self, col, width):
        cols = self._cols()
        k = self._col_index(col)
        if 0 <= k < len(cols):
            cols[k]["Width"] = int(_num(width))
            self._p["Columns"] = json.dumps(cols)
            self.redraw()

    def BeginEdit(self, row, col):
        pass

    def EnsureVisible(self, row):
        pass


class RmListView(RmGrid):
    PROPS = {"Columns": "Name", "Items": "", "View": "Details", "RowHeight": 0}

    def init(self):
        super().init()
        object.__setattr__(self, "_data", _rows(self._p.get("Items")))
        object.__setattr__(self, "_imgs", [str(r.get("Image", "")) if isinstance(r, dict) else "" for r in _items(self._p.get("Items"))]
                           if str(self._p.get("Items", "")).strip().startswith("[") else [])

    def changed(self, name, old, value):
        _Base.changed(self, name, old, value)
        if name == "Items":
            object.__setattr__(self, "_data", _rows(value))

    def draw(self):
        if str(self._p.get("View", "Details")) in ("Details", "List", ""):
            object.__setattr__(self, "_p", {**self._p, "AllowFilter": False, "AllowSort": False})
            return RmGrid.draw(self)
        t, w, h = self.T, self.W(), self.H()
        back = self._p.get("BackColor") or t["input"]
        fg = self._p.get("ForeColor") or t["input_text"]
        self.configure(bg=back)
        cards = str(self._p.get("View")).startswith("Card")
        cw, ch = (236, 120) if cards else (220, 64)
        per = max(1, int(w // cw))
        cols = self._cols()
        for i, row in enumerate(self._data):
            x, y = (i % per) * cw + 4, (i // per) * (ch + 8) + 4
            if y > h:
                break
            card = blend(t["window"], "#FFFFFF", .07) if t["dark"] else t["input"]
            self.rrect(x, y, x + cw - 8, y + ch, 6, fill=blend(card, self.accent, .12) if i == self._sel else card,
                       outline=self.accent if i == self._sel else blend(t["border"], card, .4))
            img = glyph(self._imgs[i]) if i < len(self._imgs) else ""
            if cards:
                self.label(x + 12, y + 20, row[0] if row else "", fg, "w", self.font(1.12, True))
                self.label(x + cw - 24, y + 22, img, self.accent, "center", self.font(1.5))
                for k in range(1, min(len(cols), 4)):
                    self.label(x + 12, y + 50 + (k - 1) * 19, cols[k].get("Text", ""), blend(fg, back, .45))
                    self.label(x + 96, y + 50 + (k - 1) * 19, row[k] if k < len(row) else "", fg)
            else:
                self.label(x + 28, y + ch / 2, img, self.accent, "center", self.font(2.2))
                self.label(x + 54, y + 20, row[0] if row else "", fg, "w", self.font(1.0, True))
                self.label(x + 54, y + 42, row[1] if len(row) > 1 else "", blend(fg, back, .35))

    def _lv_hit(self, x, y):
        if str(self._p.get("View", "Details")) in ("Details", "List", ""):
            area, r, _c = self._hit(x, y)
            return r if area == "cell" else -1
        cards = str(self._p.get("View")).startswith("Card")
        cw, ch = (236, 120) if cards else (220, 64)
        per = max(1, int(self.W() // cw))
        i = int(y // (ch + 8)) * per + int(x // cw)
        return i if 0 <= i < len(self._data) else -1

    def press(self, x, y):
        i = self._lv_hit(x, y)
        if i >= 0:
            changed = i != self._sel
            object.__setattr__(self, "_sel", i)
            self.redraw()
            if changed:
                self._raise("SelectedIndexChanged")
            self._raise("ItemClick", self._data[i][0] if self._data[i] else "", i)

    def double(self, x, y):
        i = self._lv_hit(x, y)
        if i >= 0:
            self._raise("ItemActivate", self._data[i][0] if self._data[i] else "", i)

    @property
    def SelectedIndex(self):
        return self._sel

    @SelectedIndex.setter
    def SelectedIndex(self, v):
        object.__setattr__(self, "_sel", int(_num(v, -1)))
        self.redraw()

    @property
    def SelectedItem(self):
        return self._cell(self._sel, 0)

    @property
    def Count(self):
        return len(self._data)

    def AddItem(self, *args):
        return self.AddRow(*args)

    def RemoveItem(self, index):
        self.RemoveRow(index)

    def List(self, index):
        return self._cell(int(_num(index, -1)), 0)

    def SetItemImage(self, index, image):
        i = int(_num(index, -1))
        while len(self._imgs) <= i:
            self._imgs.append("")
        if i >= 0:
            self._imgs[i] = str(image)
            self.redraw()


class RmTreeView(_Base):
    PROPS = {"Nodes": "", "CheckBoxes": False, "ShowLines": True, "SelectedNode": ""}

    def init(self):
        object.__setattr__(self, "_nodes", _items(self._p.get("Nodes")))
        object.__setattr__(self, "_rows", [])
        object.__setattr__(self, "_auto", 0)
        self._name_all(self._nodes)

    def _name_all(self, nodes):
        for n in nodes:
            if not n.get("Name"):
                object.__setattr__(self, "_auto", self._auto + 1)
                n["Name"] = f"node{self._auto}"
            for k in ("Nodes", "Items", "Children"):
                if isinstance(n.get(k), list):
                    n[k] = [x if isinstance(x, dict) else {"Text": str(x)} for x in n[k]]
            self._name_all(_kids(n))

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "Nodes":
            object.__setattr__(self, "_nodes", _items(value))
            self._name_all(self._nodes)

    def _walk(self):
        rows = []

        def visit(nodes, depth):
            for n in nodes:
                rows.append((n, depth))
                if n.get("Expanded") and _kids(n):
                    visit(_kids(n), depth + 1)
        visit(self._nodes, 0)
        object.__setattr__(self, "_rows", rows)
        return rows

    def _find(self, name, nodes=None, parent=None):
        for n in self._nodes if nodes is None else nodes:
            if str(n.get("Name", "")).lower() == str(name).lower():
                return n, parent
            r = self._find(name, _kids(n), n)
            if r[0] is not None:
                return r
        return None, None

    def draw(self):
        t, w, h = self.T, self.W(), self.H()
        back = self._p.get("BackColor") or t["input"]
        fg = self._p.get("ForeColor") or t["input_text"]
        self.configure(bg=back)
        sel = str(self._p.get("SelectedNode", "")).lower()
        for i, (n, depth) in enumerate(self._walk()):
            y = i * 26
            if y > h:
                break
            if str(n.get("Name", "")).lower() == sel:
                self.rrect(2, y + 1, w - 3, y + 25, 4, fill=blend(back, self.accent, .35 if t["dark"] else .16))
            x = 6 + depth * 18
            if _kids(n) or n.get("Lazy"):
                self.label(x + 9, y + 13, "⌄" if n.get("Expanded") else "›", blend(fg, back, .3), "center", self.font(1.1, True))
            x += 18
            if _bool(self._p.get("CheckBoxes")):
                on_ = _bool(n.get("Checked"))
                self.rrect(x, y + 5, x + 15, y + 20, 3, fill=self.accent if on_ else t["input"], outline="" if on_ else blend(t["border"], fg, .2))
                if on_:
                    self.create_line(x + 3, y + 12.5, x + 6.5, y + 16, x + 12, y + 9, fill=on(self.accent), width=2)
                x += 22
            g = glyph(n.get("Image"))
            if g:
                self.label(x + 8, y + 13, g, blend(self.accent, fg, .3), "center")
                x += 22
            self.label(x, y + 13, n.get("Text", ""), fg, "w", self.font(1.0, str(n.get("Name", "")).lower() == sel))
        self.create_rectangle(0, 0, w - 1, h - 1, outline=blend(t["border"], back, .3))

    def press(self, x, y):
        i = int(y // 26)
        if not 0 <= i < len(self._rows):
            return
        n, depth = self._rows[i]
        ex = 6 + depth * 18
        if ex <= x < ex + 18 and (_kids(n) or n.get("Lazy")):
            self._expand(n, not n.get("Expanded"))
            return
        if _bool(self._p.get("CheckBoxes")) and ex + 18 <= x < ex + 38:
            self._check(n, not _bool(n.get("Checked")))
            self.redraw()
            self._raise("NodeChecked", n["Name"], i)
            return
        self._p["SelectedNode"] = n["Name"]
        self.redraw()
        self._raise("NodeClick", n["Name"], i)
        self._raise("SelectedIndexChanged")

    def double(self, x, y):
        i = int(y // 26)
        if 0 <= i < len(self._rows):
            n = self._rows[i][0]
            self._raise("NodeDoubleClick", n["Name"], i)
            if _kids(n) or n.get("Lazy"):
                self._expand(n, not n.get("Expanded"))

    def _expand(self, n, on_):
        n["Expanded"] = bool(on_)
        if on_:
            if n.get("Lazy"):
                n["Lazy"] = False
            self._raise("NodeExpanding", n["Name"], -1)
        else:
            self._raise("NodeCollapsed", n["Name"], -1)
        self.redraw()

    def _check(self, n, on_):
        n["Checked"] = bool(on_)
        for k in _kids(n):
            self._check(k, on_)

    @property
    def SelectedText(self):
        n, _p = self._find(self._p.get("SelectedNode", ""))
        return n.get("Text", "") if n else ""

    @property
    def CheckedNodes(self):
        out = []

        def visit(nodes):
            for n in nodes:
                if _bool(n.get("Checked")):
                    out.append(n["Name"])
                visit(_kids(n))
        visit(self._nodes)
        return ";".join(out)

    @property
    def NodeCount(self):
        return len(self._walk())

    def AddNode(self, parent, text, name="", image=""):
        if not name:
            object.__setattr__(self, "_auto", self._auto + 1)
            name = f"node{self._auto}"
        node = {"Text": str(text), "Name": str(name), "Image": str(image)}
        p, _x = self._find(parent) if parent else (None, None)
        if p is not None:
            p.setdefault("Nodes", []).append(node)
            p["Lazy"] = False
        else:
            self._nodes.append(node)
        self.redraw()
        return name

    def RemoveNode(self, name):
        n, parent = self._find(name)
        if n is not None:
            lst = _kids(parent) if parent is not None else self._nodes
            for k in ("Nodes", "Items", "Children"):
                if parent is not None and isinstance(parent.get(k), list) and n in parent[k]:
                    parent[k].remove(n)
            if parent is None and n in lst:
                lst.remove(n)
            self.redraw()

    def Clear(self):
        self._nodes.clear()
        self.redraw()

    def ExpandNode(self, name):
        n, _p = self._find(name)
        if n is not None:
            self._expand(n, True)

    def CollapseNode(self, name):
        n, _p = self._find(name)
        if n is not None:
            self._expand(n, False)

    def ExpandAll(self):
        def visit(nodes):
            for n in nodes:
                if _kids(n):
                    n["Expanded"] = True
                visit(_kids(n))
        visit(self._nodes)
        self.redraw()

    def CollapseAll(self):
        def visit(nodes):
            for n in nodes:
                n["Expanded"] = False
                visit(_kids(n))
        visit(self._nodes)
        self.redraw()

    def SetChecked(self, name, value):
        n, _p = self._find(name)
        if n is not None:
            self._check(n, _bool(value))
            self.redraw()

    def GetChecked(self, name):
        n, _p = self._find(name)
        return bool(n and _bool(n.get("Checked")))

    def SelectNode(self, name):
        self.SelectedNode = name

    def GetNodeText(self, name):
        n, _p = self._find(name)
        return n.get("Text", "") if n else ""

    def SetNodeText(self, name, text):
        n, _p = self._find(name)
        if n is not None:
            n["Text"] = str(text)
            self.redraw()

    def SetNodeImage(self, name, image):
        n, _p = self._find(name)
        if n is not None:
            n["Image"] = str(image)
            self.redraw()


# ====================================================================== dates
def _date(v):
    try:
        return _dt.date.fromisoformat(str(v))
    except ValueError:
        return _dt.date.today()


class RmCalendar(_Base):
    PROPS = {"Value": "", "MinDate": "", "MaxDate": "", "Format": "Short"}

    def init(self):
        object.__setattr__(self, "_shown", _date(self._p.get("Value")).replace(day=1))

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "Value":
            d = _date(value) if str(value) not in ("", "Today") else _dt.date.today()
            self._p["Value"] = d.isoformat()
            object.__setattr__(self, "_shown", d.replace(day=1))
            if str(old) != d.isoformat():
                self._raise("ValueChanged")

    def _geo(self):
        w, h = self.W() - 8, self.H() - 8
        return 4, 4, w / 7, h / 8

    def draw(self):
        t = self.T
        back = self._p.get("BackColor") or t["input"]
        self.configure(bg=self.master.cget("bg") if hasattr(self.master, "cget") else back)
        self.rrect(1, 1, self.W() - 2, self.H() - 2, 5, fill=back, outline=blend(t["border"], back, .3))
        x, y, cw, ch = self._geo()
        d = _date(self._p.get("Value"))
        fg = t["text"]
        self.label(x + 3.5 * cw, y + ch / 2, self._shown.strftime("%B %Y"), fg, "center", self.font(1.1, True))
        self.label(x + cw / 2, y + ch / 2, "‹", fg, "center", self.font(1.4, True))
        self.label(x + 6.5 * cw, y + ch / 2, "›", fg, "center", self.font(1.4, True))
        for i, n in enumerate(["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]):
            self.label(x + (i + .5) * cw, y + 1.5 * ch, n, blend(fg, back, .55), "center")
        start = self._shown - _dt.timedelta(days=(self._shown.weekday() + 1) % 7)
        for i in range(42):
            day = start + _dt.timedelta(days=i)
            cx, cy = x + (i % 7 + .5) * cw, y + (i // 7 + 2.5) * ch
            s = min(cw, ch) * .43
            if day == d:
                self.create_oval(cx - s, cy - s, cx + s, cy + s, fill=self.accent, outline="")
            elif day == _dt.date.today():
                self.create_oval(cx - s, cy - s, cx + s, cy + s, outline=self.accent, width=1.5)
            self.label(cx, cy, day.day, on(self.accent) if day == d else (fg if day.month == self._shown.month else blend(fg, back, .55)), "center")

    def press(self, x, y):
        x0, y0, cw, ch = self._geo()
        if y < y0 + ch:
            m = self._shown.month + (-1 if x < x0 + cw else 1 if x > x0 + 6 * cw else 0)
            if m != self._shown.month:
                yr = self._shown.year + (m - 1) // 12
                object.__setattr__(self, "_shown", _dt.date(yr, (m - 1) % 12 + 1, 1))
                self.redraw()
            return
        r, c = int((y - y0) // ch) - 2, int((x - x0) // cw)
        if 0 <= r < 6 and 0 <= c < 7:
            start = self._shown - _dt.timedelta(days=(self._shown.weekday() + 1) % 7)
            self.Value = (start + _dt.timedelta(days=r * 7 + c)).isoformat()

    @property
    def Year(self):
        return _date(self._p.get("Value")).year

    @property
    def Month(self):
        return _date(self._p.get("Value")).month

    @property
    def Day(self):
        return _date(self._p.get("Value")).day

    @property
    def DayOfWeek(self):
        return (_date(self._p.get("Value")).weekday() + 1) % 7

    def AddDays(self, n):
        self.Value = (_date(self._p.get("Value")) + _dt.timedelta(days=int(_num(n)))).isoformat()
        return self.Value

    def AddMonths(self, n):
        d = _date(self._p.get("Value"))
        m = d.month - 1 + int(_num(n))
        yr, m = d.year + m // 12, m % 12 + 1
        import calendar
        self.Value = d.replace(year=yr, month=m, day=min(d.day, calendar.monthrange(yr, m)[1])).isoformat()
        return self.Value

    def Today(self):
        self.Value = _dt.date.today().isoformat()
        return self.Value

    def FormatDate(self, value="", fmt=""):
        d = _date(value or self._p.get("Value"))
        f = str(fmt or self._p.get("Format") or "Short")
        return d.strftime("%A, %B %d, %Y") if f == "Long" else d.isoformat() if f in ("ISO", "yyyy-MM-dd") else d.strftime("%d/%m/%Y")


class RmDatePicker(RmCalendar):
    def draw(self):
        t = self.T
        self.background()
        self.rrect(1, 1, self.W() - 2, self.H() - 2, 4, fill=t["input"], outline=self.accent if self.focus_get() is self else t["border"])
        self.label(8, self.H() / 2, self.FormatDate(), t["input_text"])
        self.label(self.W() - 16, self.H() / 2, "▦", blend(t["input_text"], t["input"], .3), "center")

    def press(self, x, y):
        self.ShowDropDown()

    def ShowDropDown(self):
        top = tk.Toplevel(self)
        top.overrideredirect(True)
        top.geometry(f"252x236+{self.winfo_rootx()}+{self.winfo_rooty() + self.H() + 1}")
        cal = RmCalendar(top, Value=self._p.get("Value"), Style=self._p.get("Style"), AccentColor=self._p.get("AccentColor"))
        cal.place(x=0, y=0, relwidth=1, relheight=1)

        def picked(_a=None):
            self.Value = cal.Value
            top.destroy()
        cal.rad_bind("ValueChanged", picked)
        top.bind("<FocusOut>", lambda _e: top.destroy())
        top.focus_set()

    def key(self, k):
        if k in ("Up", "Down"):
            self.AddDays(1 if k == "Up" else -1)
        elif k in ("space", "Return", "F4"):
            self.ShowDropDown()


class RmTimePicker(_Base):
    PROPS = {"Value": "12:00:00", "Format": "HH:mm", "ShowSeconds": False}

    def init(self):
        object.__setattr__(self, "_seg", 0)

    def _parts(self):
        bits = (str(self._p.get("Value") or "00:00:00").split(":") + ["0", "0"])[:3]
        return [int(_num(b)) for b in bits]

    def changed(self, name, old, value):
        super().changed(name, old, value)
        if name == "Value":
            if str(value) in ("", "Now"):
                n = _dt.datetime.now()
                self._p["Value"] = f"{n.hour:02d}:{n.minute:02d}:{n.second:02d}"
            else:
                h, m, s = self._parts()
                self._p["Value"] = f"{h % 24:02d}:{m % 60:02d}:{s % 60:02d}"
            if str(old) != self._p["Value"]:
                self._raise("ValueChanged")

    def draw(self):
        t = self.T
        self.background()
        self.rrect(1, 1, self.W() - 2, self.H() - 2, 4, fill=t["input"], outline=self.accent if self.focus_get() is self else t["border"])
        secs = "ss" in str(self._p.get("Format")) or _bool(self._p.get("ShowSeconds"))
        h, m, s = self._parts()
        parts = [h, m, s] if secs else [h, m]
        x = 10
        for i, v in enumerate(parts):
            if self.focus_get() is self and i == self._seg:
                self.rrect(x - 2, 5, x + 20, self.H() - 5, 3, fill=self.accent)
            self.label(x + 9, self.H() / 2, f"{v:02d}", on(self.accent) if self.focus_get() is self and i == self._seg else t["input_text"], "center")
            if i < len(parts) - 1:
                self.label(x + 23, self.H() / 2, ":", t["input_text"], "center")
            x += 26
        self.label(self.W() - 12, self.H() * .3, "˄", blend(t["input_text"], t["input"], .3), "center")
        self.label(self.W() - 12, self.H() * .72, "˅", blend(t["input_text"], t["input"], .3), "center")

    def _step(self, d):
        h, m, s = self._parts()
        if self._seg == 0:
            h += d
        elif self._seg == 1:
            m += d
        else:
            s += d
        self.Value = f"{h % 24:02d}:{m % 60:02d}:{s % 60:02d}"

    def press(self, x, y):
        if x > self.W() - 22:
            self._step(1 if y < self.H() / 2 else -1)
        else:
            object.__setattr__(self, "_seg", max(0, min(2, int((x - 8) // 26))))
            self.redraw()

    def wheel(self, d):
        self._step(d)

    def key(self, k):
        if k in ("Up", "Down"):
            self._step(1 if k == "Up" else -1)
        elif k in ("Left", "Right"):
            object.__setattr__(self, "_seg", max(0, min(2, self._seg + (1 if k == "Right" else -1))))
            self.redraw()

    @property
    def Hour(self):
        return self._parts()[0]

    @property
    def Minute(self):
        return self._parts()[1]

    @property
    def Second(self):
        return self._parts()[2]


# ====================================================================== non-visual components
class _Component:
    """A non-visual component: place() / lift() do nothing (the form generator calls them)."""
    PROPS: dict = {}

    def __init__(self, master, **kw):
        self.master = master
        self._h = {}
        self._p = {"Style": "Inherit", "AccentColor": "", **self.PROPS, **kw}
        self.EventItem, self.EventIndex = "", -1

    def __getattr__(self, name):
        p = self.__dict__.get("_p")
        if p is not None and name in p:
            return p[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name[:1].isupper() and name not in ("EventItem", "EventIndex"):
            self._p[name] = value
        else:
            object.__setattr__(self, name, value)

    def place(self, *a, **k):
        pass

    def place_forget(self):
        pass

    def lift(self, *a):
        pass

    lower = lift

    def bind(self, *a, **k):
        pass

    def configure(self, **k):
        pass

    def rad_bind(self, event, callback):
        self._h[event] = callback

    def _raise(self, event, item=None, index=-1):
        if item is not None:
            self.EventItem, self.EventIndex = item, index
        fn = self._h.get(event)
        if fn is not None:
            try:
                fn(Args(item or "", index))
            except TypeError:
                fn()

    @property
    def T(self):
        return THEMES.get(str(self._p.get("Style")), THEMES.get(APP_THEME[0], THEMES["Light"]))

    def _root(self):
        try:
            return self.master.winfo_toplevel()
        except AttributeError:
            return tk._default_root


class RmToast(_Component):
    PROPS = {"Position": "BottomRight", "Duration": 3000, "ToastWidth": 340}

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        object.__setattr__(self, "_open", [])

    @property
    def Count(self):
        return len(self._open)

    def Show(self, title="", text="", kind="Info", ms=None):
        root = self._root()
        t = self.T
        colors = {"Success": "#2E7D32", "Warning": "#ED6C02", "Error": "#C62828"}
        kc = colors.get(str(kind), self._p.get("AccentColor") or t["accent"])
        back = blend(t["window"], "#FFFFFF", .08) if t["dark"] else t["input"]
        top = tk.Toplevel(root)
        top.overrideredirect(True)
        try:
            top.attributes("-topmost", True)
        except tk.TclError:
            pass
        w = int(_num(self._p.get("ToastWidth"), 340))
        frame = tk.Frame(top, bg=back, highlightthickness=1, highlightbackground=blend(t["border"], back, .2))
        frame.pack(fill="both", expand=True)
        tk.Frame(frame, bg=kc, width=5).pack(side="left", fill="y")
        sym = {"Success": "✔", "Warning": "⚠", "Error": "✖"}.get(str(kind), "ℹ")
        tk.Label(frame, text=sym, fg=kc, bg=back, font=("Segoe UI", 16)).pack(side="left", padx=10, anchor="n", pady=10)
        body = tk.Frame(frame, bg=back)
        body.pack(side="left", fill="both", expand=True, pady=10, padx=(0, 12))
        tk.Label(body, text=str(title), fg=t["text"], bg=back, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(body, text=str(text), fg=blend(t["text"], back, .2), bg=back, font=("Segoe UI", 9), anchor="w", justify="left",
                 wraplength=w - 80).pack(fill="x")
        top.update_idletasks()
        h = max(76, top.winfo_reqheight())
        sw, sh = top.winfo_screenwidth(), top.winfo_screenheight()
        pos = str(self._p.get("Position") or "BottomRight")
        offset = sum(o.winfo_height() + 10 for o in self._open if o.winfo_exists())
        x = 10 if "Left" in pos else (sw - w) // 2 if "Center" in pos else sw - w - 10
        y = 10 + offset if "Top" in pos else sh - h - 50 - offset
        top.geometry(f"{w}x{h}+{x}+{y}")
        self._open.append(top)

        def close(_e=None, clicked=False):
            if top in self._open:
                self._open.remove(top)
            if clicked:
                self._raise("Click", str(title), -1)
            try:
                top.destroy()
            except tk.TclError:
                pass
        for wdg in (top, frame, body):
            wdg.bind("<Button-1>", lambda e: close(e, True))
        top.after(int(_num(ms if ms not in (None, "") else self._p.get("Duration"), 3000)), close)

    def CloseAll(self):
        for o in list(self._open):
            try:
                o.destroy()
            except tk.TclError:
                pass
        self._open.clear()


class RmSuperTooltip(_Component):
    PROPS = {"Delay": 500, "MaxWidth": 320, "Duration": 8000}
    BALLOON = False

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        object.__setattr__(self, "_tips", {})
        object.__setattr__(self, "_win", None)

    @property
    def IsShown(self):
        return self._win is not None

    def _target(self, name):
        form = self.master
        while form is not None and not hasattr(form, "winfo_toplevel"):
            form = getattr(form, "master", None)
        ui = None
        try:
            import gc
            for obj in gc.get_referrers(self):
                if isinstance(obj, dict) and obj.get(str(name)) is not None and hasattr(obj.get(str(name)), "winfo_rootx"):
                    ui = obj[str(name)]
                    break
        except Exception:  # noqa: BLE001
            ui = None
        return ui

    def SetToolTip(self, control, title="", text="", footer="", image=""):
        w = self._target(control) if isinstance(control, str) else control
        if w is None:
            return
        self._tips[w] = (str(title), str(text), str(footer), str(image))
        w.bind("<Enter>", lambda _e, w=w: w.after(int(_num(self._p.get("Delay"), 500)), lambda: self._show(w)), add="+")
        w.bind("<Leave>", lambda _e: self.Hide(), add="+")

    def _show(self, w, ms=None):
        if w not in self._tips:
            return
        self.Hide()
        title, text, footer, image = self._tips[w]
        t = self.T
        back = blend(t["window"], "#FFFFFF", .1) if t["dark"] else t["input"]
        top = tk.Toplevel(w)
        top.overrideredirect(True)
        f = tk.Frame(top, bg=back, highlightthickness=1, highlightbackground=blend(t["border"], back, .1))
        f.pack(fill="both", expand=True)
        if title:
            tk.Label(f, text=title, bg=back, fg=t["text"], font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", padx=10, pady=(8, 2))
        row = tk.Frame(f, bg=back)
        row.pack(fill="x", padx=10, pady=4)
        if image:
            tk.Label(row, text=glyph(image), bg=back, fg=t["accent"], font=("Segoe UI", 18)).pack(side="left", padx=(0, 8))
        tk.Label(row, text=text, bg=back, fg=t["text"], justify="left", wraplength=int(_num(self._p.get("MaxWidth"), 320)) - 60).pack(side="left")
        if footer:
            tk.Frame(f, bg=blend(t["border"], back, .3), height=1).pack(fill="x", padx=10)
            tk.Label(f, text="? " + footer, bg=back, fg=blend(t["text"], back, .3), anchor="w").pack(fill="x", padx=10, pady=(2, 8))
        top.geometry(f"+{w.winfo_rootx()}+{w.winfo_rooty() + w.winfo_height() + 2}")
        object.__setattr__(self, "_win", top)
        dur = int(_num(ms if ms is not None else self._p.get("Duration"), 0))
        if dur > 0:
            top.after(dur, self.Hide)

    def Show(self, control, title=None, text=None, ms=None):
        w = self._target(control) if isinstance(control, str) else control
        if w is None:
            return
        if title is not None or text is not None or w not in self._tips:
            self._tips[w] = (str(title or ""), str(text or ""), "", "")
        self._show(w, int(_num(ms, 5000)) if ms is not None else None)

    def Hide(self):
        if self._win is not None:
            try:
                self._win.destroy()
            except tk.TclError:
                pass
            object.__setattr__(self, "_win", None)

    def RemoveToolTip(self, control):
        w = self._target(control) if isinstance(control, str) else control
        self._tips.pop(w, None)


class RmBalloonTip(RmSuperTooltip):
    PROPS = {"Delay": 500, "MaxWidth": 320, "Duration": 0}
    BALLOON = True


class RmMessageBox(_Component):
    PROPS = {"Result": ""}

    def Show(self, text="", title="", buttons="OK", icon="", heading=""):
        from tkinter import messagebox
        b = str(buttons or "OK")
        msg = (str(heading) + "\n\n" if heading else "") + str(text)
        kw = {"icon": {"Error": "error", "Warning": "warning", "Question": "question"}.get(str(icon), "info"), "parent": self._root()}
        if b == "OKCancel":
            r = "OK" if messagebox.askokcancel(title, msg, **kw) else "Cancel"
        elif b == "YesNo":
            r = "Yes" if messagebox.askyesno(title, msg, **kw) else "No"
        elif b == "YesNoCancel":
            v = messagebox.askyesnocancel(title, msg, **kw)
            r = "Cancel" if v is None else "Yes" if v else "No"
        elif b == "RetryCancel":
            r = "Retry" if messagebox.askretrycancel(title, msg, **kw) else "Cancel"
        elif ";" in b:
            choices = b.split(";")
            v = messagebox.askyesnocancel(title, msg + "\n\n" + " / ".join(choices), **kw) if len(choices) >= 3 else \
                messagebox.askyesno(title, msg, **kw)
            r = choices[0] if v else choices[1] if v is False or len(choices) < 3 else choices[2]
        else:
            messagebox.showinfo(title, msg, **kw)
            r = "OK"
        self._p["Result"] = r
        return r


__all__ = [n for n in dir() if n.startswith("Rm")] + ["set_theme", "THEMES"]
