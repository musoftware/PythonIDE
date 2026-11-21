"""The model of a DOS text-mode form (.tform, neutral JSON). No Qt in here.

A ``TScreen`` is one screen of the application (like a VB form): its size (80x25 / 80x43 / 80x50), the desktop
background (fill character + colours, or an ANSI / BIN art file) and its controls in z-order (later = on top).
A project holds several .tform files; the code generators put all of them into one program.

File format (``format: "radide-tform"``, ``version: 1``)::

    {"format": "radide-tform", "version": 1,
     "screen": {"name": "Main", "cols": 80, "rows": 25, "back_char": 176, "back_fore": 7, "back_color": 1, ...},
     "controls": [{"type": "Window", "name": "Window1", "x": 10, "y": 3, "w": 40, "h": 12,
                   "fore": 15, "back": 1, "text": "Hello", "border": "double", "shadow": true, ...}, ...]}

Every control has type, name, x, y (0-based cells), w, h, fore, back (colour indexes 0..15 / 0..7), blink,
visible, enabled, tab_index and ``events`` (the names of the events that have a handler: "Click", "Change",
"KeyPress"); the other keys depend on the type (see ``PROPS``).
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .cp437 import BORDER_STYLES, attr

FORMAT = "radide-tform"
VERSION = 1
SIZES = [(80, 25), (80, 43), (80, 50), (40, 25)]

# ------------------------------------------------------------------ control types
STATIC_TYPES = ("Window", "Frame", "Separator", "MenuBar")
DYNAMIC_TYPES = ("Label", "Button", "TextBox", "CheckBox", "Option", "ListBox", "ProgressBar", "StatusBar")
TYPES = ("Window", "Frame", "Label", "Button", "TextBox", "CheckBox", "Option", "ListBox", "MenuBar",
         "StatusBar", "ProgressBar", "Separator")
FOCUSABLE = ("Button", "TextBox", "CheckBox", "Option", "ListBox")
EVENTS: dict[str, tuple[str, ...]] = {
    "Button": ("Click", "KeyPress"), "TextBox": ("Change", "KeyPress"), "CheckBox": ("Click", "KeyPress"),
    "Option": ("Click", "KeyPress"), "ListBox": ("Click", "Change", "KeyPress"), "MenuItem": ("Click",),
    "Screen": ("Load", "KeyPress"),
}
EVENT_CODES = {"Click": 1, "Change": 2, "KeyPress": 3, "Load": 4}
PREFIX = {"Window": "Window", "Frame": "Frame", "Label": "Label", "Button": "Button", "TextBox": "Text",
          "CheckBox": "Check", "Option": "Option", "ListBox": "List", "MenuBar": "MenuBar",
          "StatusBar": "Status", "ProgressBar": "Progress", "Separator": "Line"}
TYPE_DESCRIPTIONS = {
    "Window": "A window: border (single / double), title, shadow. Moving it moves the controls inside.",
    "Frame": "A frame that groups controls (option buttons) under a title.",
    "Label": "Static text (can be changed at run time).",
    "Button": "A push button with a hotkey (Alt+letter) and a Click event.",
    "TextBox": "An input field: typing changes Text and fires Change.",
    "CheckBox": "[X] on / off.",
    "Option": "(*) one choice of a group.",
    "ListBox": "A list of items; arrows / mouse select.",
    "MenuBar": "The menu bar with drop-down menus and hotkeys (F10 / Alt+letter).",
    "StatusBar": "A status line; ~text~ is highlighted.",
    "ProgressBar": "A bar of block characters (Value of Max).",
    "Separator": "A horizontal line; Joined connects it to a window border.",
}

# property metadata for the Properties grid: name -> (kind, default) ; kinds: str int color bgcolor bool
# choice:<a|b|c> items menus
COMMON = [("name", "str"), ("x", "int"), ("y", "int"), ("w", "int"), ("h", "int"), ("fore", "color"),
          ("back", "bgcolor"), ("blink", "bool"), ("visible", "bool")]
PROPS: dict[str, list[tuple[str, str]]] = {
    "Window": [("text", "str"), ("border", "choice:" + "|".join(BORDER_STYLES)), ("shadow", "bool"),
               ("title_align", "choice:left|center|right")],
    "Frame": [("text", "str"), ("border", "choice:" + "|".join(BORDER_STYLES)), ("shadow", "bool"),
              ("title_align", "choice:left|center|right")],
    "Label": [("text", "str"), ("align", "choice:left|center|right"), ("hot", "color")],
    "Button": [("text", "str"), ("hot", "color"), ("focus_fore", "color"), ("focus_back", "bgcolor"),
               ("shadow", "bool"), ("cancel", "bool"), ("enabled", "bool"), ("tab_index", "int")],
    "TextBox": [("text", "str"), ("max_length", "int"), ("password", "bool"), ("focus_fore", "color"),
                ("focus_back", "bgcolor"), ("enabled", "bool"), ("tab_index", "int")],
    "CheckBox": [("text", "str"), ("value", "bool"), ("hot", "color"), ("focus_fore", "color"),
                 ("focus_back", "bgcolor"), ("enabled", "bool"), ("tab_index", "int")],
    "Option": [("text", "str"), ("value", "bool"), ("group", "str"), ("hot", "color"), ("focus_fore", "color"),
               ("focus_back", "bgcolor"), ("enabled", "bool"), ("tab_index", "int")],
    "ListBox": [("items", "items"), ("list_index", "int"), ("border", "choice:" + "|".join(BORDER_STYLES)),
                ("sel_fore", "color"), ("sel_back", "bgcolor"), ("enabled", "bool"), ("tab_index", "int")],
    "MenuBar": [("menus", "menus"), ("hot", "color"), ("sel_fore", "color"), ("sel_back", "bgcolor")],
    "StatusBar": [("text", "str"), ("hot", "color")],
    "ProgressBar": [("value", "int"), ("max", "int")],
    "Separator": [("style", "choice:single|double"), ("joined", "bool")],
}
SCREEN_PROPS = [("name", "str"), ("cols", "int"), ("rows", "int"), ("back_char", "char"), ("back_fore", "color"),
                ("back_color", "bgcolor"), ("background", "file"), ("esc_quits", "bool"), ("splash", "file"),
                ("splash_seconds", "int"), ("ice_colors", "bool")]
PROP_TITLES = {"x": "Left", "y": "Top", "w": "Width", "h": "Height", "fore": "ForeColor", "back": "BackColor",
               "text": "Text", "name": "Name", "blink": "Blink", "visible": "Visible", "enabled": "Enabled",
               "tab_index": "TabIndex", "border": "BorderStyle", "shadow": "Shadow", "title_align": "TitleAlign",
               "align": "Alignment", "hot": "HotColor", "focus_fore": "FocusForeColor",
               "focus_back": "FocusBackColor", "cancel": "Cancel", "max_length": "MaxLength",
               "password": "PasswordChar", "value": "Value", "group": "Group", "items": "Items",
               "list_index": "ListIndex", "sel_fore": "SelForeColor", "sel_back": "SelBackColor",
               "menus": "Menus", "max": "Max", "style": "Style", "joined": "Joined", "cols": "Columns",
               "rows": "Rows", "back_char": "BackChar", "back_fore": "BackForeColor", "back_color": "DesktopColor",
               "background": "BackgroundArt", "esc_quits": "EscQuits", "splash": "SplashArt",
               "splash_seconds": "SplashSeconds", "ice_colors": "IceColors"}

DEFAULTS: dict[str, dict] = {
    "Window": {"w": 40, "h": 12, "fore": 15, "back": 1, "text": "Window", "border": "double", "shadow": True,
               "title_align": "center"},
    "Frame": {"w": 24, "h": 6, "fore": 15, "back": 1, "text": "Frame", "border": "single", "shadow": False,
              "title_align": "left"},
    "Label": {"w": 12, "h": 1, "fore": 15, "back": 1, "text": "Label", "align": "left", "hot": 14},
    "Button": {"w": 10, "h": 1, "fore": 0, "back": 2, "text": "&OK", "hot": 14, "focus_fore": 15,
               "focus_back": 2, "shadow": True, "cancel": False},
    "TextBox": {"w": 20, "h": 1, "fore": 15, "back": 0, "text": "", "max_length": 40, "password": False,
                "focus_fore": 14, "focus_back": 0},
    "CheckBox": {"w": 16, "h": 1, "fore": 15, "back": 1, "text": "&Check", "value": False, "hot": 14,
                 "focus_fore": 15, "focus_back": 3},
    "Option": {"w": 16, "h": 1, "fore": 15, "back": 1, "text": "&Option", "value": False, "group": "1",
               "hot": 14, "focus_fore": 15, "focus_back": 3},
    "ListBox": {"w": 20, "h": 6, "fore": 0, "back": 3, "items": ["Item 1", "Item 2", "Item 3"], "list_index": 0,
                "border": "single", "sel_fore": 15, "sel_back": 1},
    "MenuBar": {"x": 0, "y": 0, "w": 80, "h": 1, "fore": 0, "back": 7, "hot": 4, "sel_fore": 15, "sel_back": 0,
                "menus": [{"text": "&File", "items": [{"text": "E&xit", "name": "mnuExit", "shortcut": "Alt+X"}]}]},
    "StatusBar": {"x": 0, "w": 80, "h": 1, "fore": 0, "back": 7, "text": " ~F1~ Help  ~Esc~ Quit", "hot": 4},
    "ProgressBar": {"w": 20, "h": 1, "fore": 10, "back": 0, "value": 50, "max": 100},
    "Separator": {"w": 20, "h": 1, "fore": 15, "back": 1, "style": "single", "joined": True},
}
COMMON_DEFAULTS = {"blink": False, "visible": True, "enabled": True, "tab_index": 0, "events": []}
SCREEN_DEFAULTS = {"name": "Screen1", "cols": 80, "rows": 25, "back_char": 0xB0, "back_fore": 7, "back_color": 1,
                   "background": "", "esc_quits": True, "splash": "", "splash_seconds": 0, "ice_colors": False}
FIXED_HEIGHT = {"Label": 1, "Button": 1, "TextBox": 1, "CheckBox": 1, "Option": 1, "MenuBar": 1, "StatusBar": 1,
                "ProgressBar": 1, "Separator": 1}
MIN_SIZE = {"Window": (3, 3), "Frame": (3, 3), "ListBox": (3, 1)}

IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
RESERVED = {w.lower() for w in (
    # BASIC
    "print locate color cls input if then else end sub function dim shared const as integer string long single "
    "double for next to step while wend do loop until select case gosub goto return data read restore screen "
    "width key len mid left right chr asc val str inkey time date timer sleep beep sound open close get put line "
    "name kill shell call def seg peek poke out inp random binary output append type let rem stop system on error "
    "resume declare static common erase redim option base and or not xor mod eqv imp is "
    # Pascal / C / asm
    "program unit uses var begin procedure record array of with downto repeat div shl shr nil in label goto "
    "interface implementation char int void unsigned short struct union enum switch default break continue "
    "sizeof typedef extern register volatile auto signed far near huge main "
    "ax bx cx dx si di bp sp cs ds es ss ah al bh bl ch cl dh dl byte word dword ptr offset proc endp db dw dd "
    "equ org").split()}


def hot_split(text: str, marker: str = "&") -> tuple[str, str, int]:
    """("&Save" ->) display text "Save", mask "1000" (1 = hot character) and the hotkey (ASCII upper, 0 = none).
    ``&&`` is a literal &. With marker "~" (status bars) ~text~ toggles a highlighted span."""
    out = []
    mask = []
    key = 0
    i = 0
    hot_span = False
    while i < len(text):
        c = text[i]
        if c == marker:
            if i + 1 < len(text) and text[i + 1] == marker:
                out.append(marker)
                mask.append("1" if hot_span else "0")
                i += 2
                continue
            if marker == "~":
                hot_span = not hot_span
                i += 1
                continue
            if i + 1 < len(text):
                out.append(text[i + 1])
                mask.append("1")
                if not key and text[i + 1].isalnum():
                    key = ord(text[i + 1].upper())
                i += 2
                continue
            i += 1
            continue
        out.append(c)
        mask.append("1" if hot_span else "0")
        i += 1
    return "".join(out), "".join(mask), key


@dataclass
class TControl:
    type: str
    name: str
    x: int = 0
    y: int = 0
    w: int = 10
    h: int = 1
    props: dict = field(default_factory=dict)

    def get(self, key: str, default=None):
        if key in ("x", "y", "w", "h", "name", "type"):
            return getattr(self, key)
        if key in self.props:
            return self.props[key]
        if key in DEFAULTS.get(self.type, {}):
            return DEFAULTS[self.type][key]
        return COMMON_DEFAULTS.get(key, default)

    def set(self, key: str, value) -> None:
        if key in ("x", "y", "w", "h"):
            setattr(self, key, int(value))
        elif key == "name":
            self.name = str(value)
        else:
            self.props[key] = value

    __getitem__ = get

    @property
    def focusable(self) -> bool:
        return self.type in FOCUSABLE and bool(self.get("visible")) and bool(self.get("enabled"))

    @property
    def static(self) -> bool:
        return self.type in STATIC_TYPES

    def attr(self) -> int:
        return attr(int(self.get("fore")), int(self.get("back")), bool(self.get("blink")))

    def events(self) -> list[str]:
        return list(self.get("events") or [])

    def rect(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.w, self.h

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.w and self.y <= y < self.y + self.h

    def to_dict(self) -> dict:
        d = {"type": self.type, "name": self.name, "x": self.x, "y": self.y, "w": self.w, "h": self.h}
        d.update(copy.deepcopy(self.props))
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TControl":
        d = dict(d)
        t = str(d.pop("type", "Label"))
        if t not in TYPES:
            raise ValueError(f"unknown control type {t!r}")
        c = cls(t, str(d.pop("name", t + "1")), int(d.pop("x", 0)), int(d.pop("y", 0)),
                int(d.pop("w", DEFAULTS[t].get("w", 10))), int(d.pop("h", DEFAULTS[t].get("h", 1))))
        c.props = d
        return c

    def menu_items(self) -> list[dict]:
        """All menu items of a MenuBar (flattened, separators included)."""
        out = []
        for m in self.get("menus") or []:
            out.extend(m.get("items") or [])
        return out


@dataclass
class TScreen:
    props: dict = field(default_factory=dict)
    controls: list[TControl] = field(default_factory=list)
    path: Path | None = None

    def get(self, key: str):
        return self.props.get(key, SCREEN_DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        self.props[key] = value

    @property
    def name(self) -> str:
        return str(self.get("name"))

    @property
    def cols(self) -> int:
        return int(self.get("cols"))

    @property
    def rows(self) -> int:
        return int(self.get("rows"))

    def back_attr(self) -> int:
        return attr(int(self.get("back_fore")), int(self.get("back_color")))

    # ------------------------------------------------------------ controls
    def find(self, name: str) -> TControl | None:
        n = name.lower()
        return next((c for c in self.controls if c.name.lower() == n), None)

    def unique_name(self, ctype: str) -> str:
        base = PREFIX.get(ctype, ctype)
        names = {c.name.lower() for c in self.controls} | self.menu_item_names()
        i = 1
        while f"{base}{i}".lower() in names:
            i += 1
        return f"{base}{i}"

    def menu_item_names(self) -> set[str]:
        return {str(it.get("name", "")).lower() for c in self.controls if c.type == "MenuBar"
                for it in c.menu_items() if it.get("name")}

    def add(self, ctype: str, x: int, y: int, w: int | None = None, h: int | None = None, **props) -> TControl:
        d = DEFAULTS[ctype]
        c = TControl(ctype, props.pop("name", None) or self.unique_name(ctype), x, y,
                     w if w is not None else int(d.get("w", 10)), h if h is not None else int(d.get("h", 1)))
        c.props = {k: copy.deepcopy(v) for k, v in d.items() if k not in ("x", "y", "w", "h")}
        if ctype in ("MenuBar", "StatusBar"):
            c.w = w if w is not None else self.cols
            c.x = x
        c.props.update(props)
        if ctype in FOCUSABLE and "tab_index" not in props:
            c.props["tab_index"] = 1 + max([int(o.get("tab_index") or 0) for o in self.controls
                                            if o.type in FOCUSABLE] + [-1])
        if ctype == "Button" and "text" not in props:
            c.props["text"] = "&" + c.name
        if ctype in ("Label", "CheckBox", "Option", "Window", "Frame") and "text" not in props:
            c.props["text"] = ("&" if ctype in ("CheckBox", "Option") else "") + c.name
        self.controls.append(c)
        return c

    def remove(self, c: TControl) -> None:
        self.controls.remove(c)

    def contained(self, box: TControl) -> list[TControl]:
        """Controls drawn on top of *box* and inside its rectangle (moved together with a Window / Frame)."""
        i = self.controls.index(box)
        return [c for c in self.controls[i + 1:] if c.x >= box.x and c.y >= box.y and
                c.x + c.w <= box.x + box.w and c.y + c.h <= box.y + box.h]

    def container_of(self, c: TControl) -> TControl | None:
        """The topmost Window / Frame below *c* that contains it."""
        i = self.controls.index(c) if c in self.controls else len(self.controls)
        for o in reversed(self.controls[:i]):
            if o.type in ("Window", "Frame") and o.x <= c.x and o.y <= c.y and \
                    c.x + c.w <= o.x + o.w and c.y + c.h <= o.y + o.h:
                return o
        return None

    def tab_order(self) -> list[TControl]:
        cs = [c for c in self.controls if c.type in FOCUSABLE]
        return sorted(cs, key=lambda c: (int(c.get("tab_index") or 0), self.controls.index(c)))

    def first_focus(self) -> TControl | None:
        return next((c for c in self.tab_order() if c.focusable), None)

    def at(self, x: int, y: int) -> TControl | None:
        for c in reversed(self.controls):
            if c.contains(x, y) and c.get("visible", True) is not False:
                return c
        for c in reversed(self.controls):
            if c.contains(x, y):
                return c
        return None

    def clamp(self, c: TControl) -> None:
        mw, mh = MIN_SIZE.get(c.type, (1, 1))
        if c.type in FIXED_HEIGHT:
            c.h = FIXED_HEIGHT[c.type]
        c.w = max(mw, min(c.w, self.cols))
        c.h = max(mh, min(c.h, self.rows))
        c.x = max(0, min(c.x, self.cols - c.w))
        c.y = max(0, min(c.y, self.rows - c.h))

    # ------------------------------------------------------------ validation
    def problems(self) -> list[str]:
        out = []
        seen: dict[str, str] = {}
        for c in self.controls:
            if not IDENT.match(c.name):
                out.append(f"{c.name}: a name must start with a letter and use only letters and digits "
                           f"(QBasic does not allow '_')")
            elif c.name.lower() in RESERVED:
                out.append(f"{c.name}: reserved word in BASIC / Pascal / C / assembly")
            if c.name.lower() in seen:
                out.append(f"{c.name}: the name is used twice")
            seen[c.name.lower()] = c.type
            if c.x < 0 or c.y < 0 or c.x + c.w > self.cols or c.y + c.h > self.rows:
                out.append(f"{c.name}: outside the {self.cols}x{self.rows} screen")
            if c.type == "MenuBar":
                for it in c.menu_items():
                    n = str(it.get("name", ""))
                    if it.get("text", "-") != "-" and n:
                        if not IDENT.match(n):
                            out.append(f"menu item {n}: invalid name")
                        elif n.lower() in seen:
                            out.append(f"menu item {n}: the name is used twice")
                        seen[n.lower()] = "MenuItem"
        if not IDENT.match(self.name):
            out.append(f"screen name {self.name!r} must start with a letter and use only letters and digits")
        return out

    # ------------------------------------------------------------ file
    def to_dict(self) -> dict:
        props = {k: v for k, v in self.props.items()}
        for k, v in SCREEN_DEFAULTS.items():
            props.setdefault(k, v)
        return {"format": FORMAT, "version": VERSION, "screen": props,
                "controls": [c.to_dict() for c in self.controls]}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=1, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict, path: Path | None = None) -> "TScreen":
        if d.get("format") not in (FORMAT, None):
            raise ValueError("not a RAD IDE text-mode form (.tform)")
        s = cls(dict(d.get("screen") or {}), [TControl.from_dict(c) for c in d.get("controls") or []], path)
        return s

    @classmethod
    def load(cls, path) -> "TScreen":
        path = Path(path)
        s = cls.from_dict(json.loads(path.read_text(encoding="utf-8")), path)
        if "name" not in s.props:
            s.props["name"] = path.stem
        return s

    def save(self, path=None) -> Path:
        p = Path(path or self.path)
        p.write_text(self.to_json() + "\n", encoding="utf-8")
        self.path = p
        return p

    def clone(self) -> "TScreen":
        return TScreen.from_dict(json.loads(self.to_json()), self.path)


def new_screen(name: str = "Screen1", cols: int = 80, rows: int = 25, sample: bool = True) -> TScreen:
    """A new screen; with *sample* a window with a label and OK / Cancel buttons."""
    s = TScreen({**SCREEN_DEFAULTS, "name": name, "cols": cols, "rows": rows})
    if sample:
        s.add("MenuBar", 0, 0, cols)
        s.add("StatusBar", 0, rows - 1, cols)
        ww, wh = 44, 11
        wx, wy = (cols - ww) // 2, max(2, (rows - wh) // 2)
        s.add("Window", wx, wy, ww, wh, text=" " + name + " ")
        s.add("Label", wx + 3, wy + 2, 30, text="Welcome to your DOS application!")
        s.add("Button", wx + 8, wy + wh - 3, 10, text="&OK")
        s.add("Button", wx + 25, wy + wh - 3, 12, text="&Cancel", cancel=True)
    return s


def load_project_screens(folder) -> list[TScreen]:
    """Every .tform of a folder (startup screen first when project.radproj names one)."""
    folder = Path(folder)
    screens = [TScreen.load(p) for p in sorted(folder.glob("*.tform"))]
    try:
        startup = json.loads((folder / "project.radproj").read_text(encoding="utf-8")).get("tui_startup", "")
    except (OSError, ValueError):
        startup = ""
    if startup:
        screens.sort(key=lambda s: 0 if s.path and s.path.stem.lower() == str(startup).lower() else 1)
    return screens
