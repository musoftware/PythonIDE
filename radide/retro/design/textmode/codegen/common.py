"""What every code generator shares: the screens flattened into run-time tables (``build_app``) and the
user code regions that survive regeneration (``read_regions`` / ``Regions``). No Qt in here.

The generated program keeps one table of live controls (labels, buttons, text boxes, check boxes, option
buttons, list boxes, progress bars, status bars, menu bars) for all screens, one table of menus and menu
items, and per screen the static layer as run-length data (count, character, attribute) - see render.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..buffer import CellBuffer
from ..cp437 import attr as mkattr, encode
from ..model import EVENT_CODES, FOCUSABLE, TControl, TScreen, hot_split
from ..render import (dropdown_geometry, focus_attr, hot_attr, inner_list_rect, menu_layout,
                      render_static, splash_buffer)

TYPE_CODES = {"Label": 1, "Button": 2, "TextBox": 3, "CheckBox": 4, "Option": 5, "ListBox": 6, "ProgressBar": 7,
              "StatusBar": 8, "MenuBar": 9}
EV_BITS = {"Click": 1, "Change": 2, "KeyPress": 4, "Load": 1}
LIST_CAPACITY = 32               # list boxes keep room for items added at run time (AddItem)
# characters BASIC's PRINT treats as control codes (beep, tab, line feed, ...): replaced by look-alikes
BASIC_UNSAFE = {7: 0xF9, 9: 0x6F, 10: 0xDB, 11: 0x6F, 12: 0x2B, 13: 0x0E, 28: 0x4C, 29: 0xC4, 30: 0x5E, 31: 0x76}


@dataclass
class Ctl:
    index: int
    c: TControl
    code: int
    screen: int
    a: int = 7
    ha: int = 7
    fa: int = 7
    fha: int = 7
    sa: int = 7
    sha: int = 7
    text: bytes = b""
    mask: str = ""
    hotkey: int = 0
    value: int = 0
    max: int = 0
    flag: int = 0               # Label: align 0/1/2 ; TextBox: password ; ListBox: has border
    tab: int = 0                # rank in tab order (1..), 0 = not focusable
    group: int = 0
    events: int = 0
    items: list = field(default_factory=list)
    first_item: int = 0
    capacity: int = 0
    inner: tuple = (0, 0, 0, 0)

    @property
    def name(self) -> str:
        return self.c.name

    @property
    def x(self) -> int:
        return self.c.x

    @property
    def y(self) -> int:
        return self.c.y

    @property
    def w(self) -> int:
        return self.c.w

    @property
    def h(self) -> int:
        return self.c.h

    @property
    def visible(self) -> int:
        return 1 if self.c.get("visible", True) else 0

    @property
    def enabled(self) -> int:
        return 1 if self.c.get("enabled", True) else 0


@dataclass
class Menu:
    index: int
    screen: int
    bar: int                    # Ctl index of the menu bar
    title_x: int
    title: bytes                # " File "
    mask: str
    hotkey: int
    box: tuple                  # dropdown x, y, w, h
    first_item: int
    count: int


@dataclass
class Item:
    index: int
    menu: int
    line: bytes                 # " Open...   F3 " (width = box width - 2)
    mask: str
    sep: bool
    hotkey: int
    name: str                   # menu item name (handler <name>_Click) or ""


@dataclass
class Handler:
    key: str                    # language-neutral name: btnOK_Click / Main_Load / mnuExit_Click
    kind: str                   # "control" | "menu" | "screen"
    target: int                 # Ctl / Item / screen index
    event: str
    owner: str                  # control / menu item / screen name


@dataclass
class Scr:
    index: int
    s: TScreen
    runs: list
    esc_quits: int
    cancel: int
    events: int
    bar: int
    menu_first: int
    menu_last: int
    buffer: CellBuffer
    splash_runs: list | None = None
    splash_seconds: int = 0

    @property
    def name(self) -> str:
        return self.s.name


@dataclass
class App:
    cols: int
    rows: int
    screens: list[Scr]
    ctls: list[Ctl]
    menus: list[Menu]
    items: list[Item]
    handlers: list[Handler]
    warnings: list[str]
    n_items: int = 0            # list box item slots (sum of capacities)

    def ctl_handlers(self) -> list[Handler]:
        return [h for h in self.handlers if h.kind == "control"]

    def menu_handlers(self) -> list[Handler]:
        return [h for h in self.handlers if h.kind == "menu"]

    def screen_handlers(self) -> list[Handler]:
        return [h for h in self.handlers if h.kind == "screen"]

    def splash(self) -> Scr | None:
        return next((s for s in self.screens if s.splash_runs), None)


def _txt(s: str, safe_basic: bool) -> bytes:
    b = encode(s)
    if safe_basic:
        b = bytes(BASIC_UNSAFE.get(x, x) for x in b)
    return b


def build_app(screens: list[TScreen], basic: bool = False) -> App:
    """Flatten *screens* (startup first) into the run-time tables. *basic*: replace the characters BASIC's
    PRINT cannot show."""
    if not screens:
        raise ValueError("the project has no screens (.tform)")
    warnings: list[str] = []
    cols, rows = screens[0].cols, screens[0].rows
    names: dict[str, str] = {}
    for s in screens:
        for p in s.problems():
            warnings.append(f"{s.name}: {p}")
        if (s.cols, s.rows) != (cols, rows):
            warnings.append(f"{s.name}: every screen of a program uses the same size; {cols}x{rows} is used")
        for n in [s.name] + [c.name for c in s.controls] + sorted(s.menu_item_names()):
            if n.lower() in names and names[n.lower()] != s.name:
                warnings.append(f"{n}: the name is used on two screens ({names[n.lower()]} and {s.name})")
            names.setdefault(n.lower(), s.name)
    ctls: list[Ctl] = []
    menus: list[Menu] = []
    items: list[Item] = []
    handlers: list[Handler] = []
    scrs: list[Scr] = []
    slot = 1
    for si, s in enumerate(screens, 1):
        if (s.cols, s.rows) != (cols, rows):
            s = s.clone()
            s.props["cols"], s.props["rows"] = cols, rows
        buf = render_static(s)
        if basic:
            buf.chars[:] = bytes(BASIC_UNSAFE.get(x, x) for x in buf.chars)
        first_menu = len(menus) + 1
        bar_index = 0
        cancel = 0
        groups: dict[str, int] = {}
        order = {c.name: r for r, c in enumerate(s.tab_order(), 1)}
        live = [c for c in s.controls if c.type in TYPE_CODES]
        for c in live:
            i = len(ctls) + 1
            k = Ctl(i, c, TYPE_CODES[c.type], si)
            k.a, k.ha = c.attr(), hot_attr(c, c.attr()) if c.type in ("Label", "Button", "CheckBox", "Option",
                                                                       "StatusBar", "MenuBar") else c.attr()
            if c.type in ("Button", "TextBox", "CheckBox", "Option"):
                k.fa = focus_attr(c)
                k.fha = hot_attr(c, k.fa) if c.type != "TextBox" else k.fa
            else:
                k.fa, k.fha = k.a, k.ha
            if c.type in ("ListBox", "MenuBar"):
                k.sa = mkattr(int(c.get("sel_fore")), int(c.get("sel_back")))
                k.sha = hot_attr(c, k.sa) if c.type == "MenuBar" else k.sa
                k.fha = k.sha
            raw = str(c.get("text") or "")
            if c.type in ("Label", "Button", "CheckBox", "Option", "StatusBar"):
                t, m, key = hot_split(raw, "~" if c.type == "StatusBar" else "&")
                k.text, k.mask, k.hotkey = _txt(t, basic), m, (key if c.type != "StatusBar" else 0)
                if c.type == "Label":
                    k.hotkey = 0
            elif c.type == "TextBox":
                k.text = _txt(raw, basic)
                k.max = max(1, min(int(c.get("max_length") or 40), 120))
                k.flag = 1 if c.get("password") else 0
            if c.type == "Label":
                k.flag = {"left": 0, "center": 1, "right": 2}.get(c.get("align") or "left", 0)
            if c.type in ("CheckBox", "Option"):
                k.value = 1 if c.get("value") else 0
            if c.type == "Option":
                g = str(c.get("group") or "1")
                k.group = groups.setdefault(g, len(groups) + 1)
            if c.type == "ListBox":
                k.items = [_txt(str(x), basic) for x in (c.get("items") or [])]
                k.capacity = max(LIST_CAPACITY, len(k.items))
                k.first_item = slot
                slot += k.capacity
                k.value = max(-1, min(int(c.get("list_index") or 0), len(k.items) - 1))
                k.flag = 1 if (c.get("border") or "single") != "none" else 0
                k.inner = inner_list_rect(c)
            if c.type == "ProgressBar":
                k.value = int(c.get("value") or 0)
                k.max = max(1, int(c.get("max") or 100))
            if c.type in FOCUSABLE and c.get("visible", True) and c.get("enabled", True):
                k.tab = order.get(c.name, 0)
            elif c.type in FOCUSABLE:
                k.tab = order.get(c.name, 0)          # can become focusable when shown / enabled at run time
            for ev in c.events():
                if ev in EV_BITS and ev in ("Click", "Change", "KeyPress"):
                    k.events |= EV_BITS[ev]
                    handlers.append(Handler(f"{c.name}_{ev}", "control", i, ev, c.name))
            if c.type == "Button" and c.get("cancel") and not cancel:
                cancel = i
            if c.type == "MenuBar":
                if bar_index:
                    warnings.append(f"{s.name}: only the first menu bar is used")
                else:
                    bar_index = i
                    for mi, (tx, t, m, key) in enumerate(menu_layout(c)):
                        menu = c.get("menus")[mi]
                        bx, by, bw, bh, tw = dropdown_geometry(c, mi)
                        mn = Menu(len(menus) + 1, si, i, tx, _txt(" " + t + " ", basic), "0" + m + "0", key,
                                  (bx, by, bw, bh), len(items) + 1, len(menu.get("items") or []))
                        menus.append(mn)
                        for it in menu.get("items") or []:
                            txt = str(it.get("text", ""))
                            if txt == "-":
                                items.append(Item(len(items) + 1, mn.index, b"", "", True, 0, ""))
                                continue
                            t2, m2, key2 = hot_split(txt)
                            sc = str(it.get("shortcut", "") or "")
                            line = " " + t2.ljust(tw - len(sc)) + sc + " "
                            lm = "0" + m2.ljust(tw - len(sc), "0") + "0" * (len(sc) + 1)
                            nm = str(it.get("name", "") or "")
                            items.append(Item(len(items) + 1, mn.index, _txt(line, basic), lm, False, key2, nm))
                            if nm:
                                handlers.append(Handler(f"{nm}_Click", "menu", len(items), "Click", nm))
                        if bx + bw > cols or by + bh > rows:
                            warnings.append(f"{s.name}: menu {t} does not fit on the screen")
            ctls.append(k)
        sev = 0
        for ev in ("Load", "KeyPress"):
            if ev in (s.get("events") or []):
                sev |= 1 if ev == "Load" else 4
                handlers.append(Handler(f"{s.name}_{ev}", "screen", si, ev, s.name))
        sp = splash_buffer(s) if si == 1 else None
        if sp is not None and basic:
            sp.chars[:] = bytes(BASIC_UNSAFE.get(x, x) for x in sp.chars)
        scrs.append(Scr(si, s, buf.rle(), 1 if s.get("esc_quits") else 0, cancel, sev, bar_index,
                        first_menu if len(menus) >= first_menu else 0, len(menus) if len(menus) >= first_menu else 0,
                        buf, sp.rle() if sp is not None else None, int(s.get("splash_seconds") or 0)))
    return App(cols, rows, scrs, ctls, menus, items, handlers, warnings, max(1, slot - 1))


def ev_code(ev: str) -> int:
    return EVENT_CODES[ev]


# ------------------------------------------------------------------ user code regions
BEGIN = re.compile(r"^[ \t]*(?:'|;|\{|/\*|//)\s*>>> USER CODE ([A-Za-z0-9_]+)")
END = re.compile(r"^[ \t]*(?:'|;|\{|/\*|//)\s*<<< END USER CODE")


def read_regions(text: str) -> dict[str, str]:
    """{key: body} of every user code region of a generated file (body = the lines between the markers)."""
    out: dict[str, str] = {}
    key = None
    body: list[str] = []
    for line in (text or "").splitlines():
        if key is None:
            m = BEGIN.match(line)
            if m:
                key = m.group(1)
                body = []
        elif END.match(line):
            out[key] = "\n".join(body)
            key = None
        else:
            body.append(line)
    return out


class Regions:
    """Builds the regions of a new file, re-using the user's code of the old one."""

    def __init__(self, old_text: str, comment: tuple[str, str]):
        self.old = read_regions(old_text)
        self.cm = comment
        self.used: set[str] = set()
        self.defaults: dict[str, str] = {}

    def begin(self, key: str) -> str:
        a, b = self.cm
        return f"{a}>>> USER CODE {key} (kept when the screens are regenerated){b}"

    def end(self) -> str:
        a, b = self.cm
        return f"{a}<<< END USER CODE{b}"

    def region(self, key: str, default: str) -> str:
        self.used.add(key)
        self.defaults[key] = default
        body = self.old.get(key, default)
        return f"{self.begin(key)}\n{body}\n{self.end()}" if body != "" else f"{self.begin(key)}\n{self.end()}"

    def has_code(self, key: str) -> bool:
        body = self.old.get(key)
        return body is not None and body.strip() != "" and body != self.defaults.get(key)

    def orphans(self, line_comment: str) -> str:
        """Handlers whose control / event was removed: their code is kept, commented out."""
        keep = self.old.get("orphaned", "")
        parts = [keep] if keep.strip() else []
        for k, body in self.old.items():
            if k in self.used or k == "orphaned" or not body.strip():
                continue
            if all(not ln.strip() or ln.strip().startswith(line_comment.strip()) for ln in body.splitlines()):
                continue
            parts.append(f"{line_comment}--- {k} (its control or event no longer exists) ---")
            parts.extend(f"{line_comment}{ln}" for ln in body.splitlines())
        self.used.add("orphaned")
        return f"{self.begin('orphaned')}\n" + ("\n".join(parts) + "\n" if parts else "") + self.end()


def chunks(seq, n: int):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def line_of(text: str, pattern: str) -> int:
    """0-based line of the first match of *pattern* (regex, case-insensitive), -1 = none."""
    rx = re.compile(pattern, re.I | re.M)
    m = rx.search(text)
    return text.count("\n", 0, m.start()) if m else -1
