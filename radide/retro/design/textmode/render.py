"""Reference renderer: a TScreen -> CellBuffer, exactly what the generated DOS program shows.

The generated runtimes (FreeBASIC / QBasic, Pascal, C, asm) draw the same cells, so the designer is
WYSIWYG and the tests compare a B800 dump of the running program with ``render(screen)``.

Two layers, like the runtimes:

* the **static layer** (``render_static``): desktop background (fill character or ANSI art), windows, frames,
  separators, the menu bar, list box borders and button shadows. The code generators store it as
  run-length data, so the runtime only copies it to the screen.
* the **faces** of the live controls (``draw_face``): labels, buttons, text boxes, check boxes, option buttons,
  list box items, progress bars and status bars, drawn on top in z-order with their run-time state
  (text, value, selection, focus).
"""
from __future__ import annotations

from pathlib import Path

from .buffer import CellBuffer
from .cp437 import attr as mkattr, encode
from .model import DYNAMIC_TYPES, TControl, TScreen, hot_split

CHECK_ON, CHECK_OFF = "[X] ", "[ ] "
OPT_ON, OPT_OFF = "(*) ", "( ) "
PROGRESS_FULL, PROGRESS_EMPTY = 0xDB, 0xB0
DISABLED_FORE = 8


def _bg(a: int) -> int:
    return (a >> 4) & 7


def hot_attr(c: TControl, base: int) -> int:
    return (base & 0xF0) | (int(c.get("hot")) & 15)


def focus_attr(c: TControl) -> int:
    return mkattr(int(c.get("focus_fore")), int(c.get("focus_back")), bool(c.get("blink")))


def control_attrs(c: TControl, focused: bool) -> tuple[int, int]:
    """(normal attribute, hot attribute) a control is drawn with."""
    a = c.attr()
    if not c.get("enabled", True):
        a = (a & 0xF0) | DISABLED_FORE
        return a, a
    if focused and c.type in ("Button", "TextBox", "CheckBox", "Option"):
        a = focus_attr(c)
    if c.type in ("Label", "Button", "CheckBox", "Option", "StatusBar"):
        return a, hot_attr(c, a)
    return a, a


def title_x(c: TControl, title: str) -> int:
    align = c.get("title_align") or "center"
    if align == "left":
        return c.x + 2
    if align == "right":
        return c.x + c.w - 2 - len(title)
    return c.x + (c.w - len(title)) // 2


def inner_list_rect(c: TControl) -> tuple[int, int, int, int]:
    if (c.get("border") or "none") != "none":
        return c.x + 1, c.y + 1, max(0, c.w - 2), max(0, c.h - 2)
    return c.x, c.y, c.w, c.h


def menu_layout(c: TControl) -> list[tuple[int, str, str, int]]:
    """Menu bar titles: [(x of the title cell, display text, mask, hotkey)] - each title is " text "."""
    out = []
    x = c.x + 1
    for m in c.get("menus") or []:
        t, mask, key = hot_split(str(m.get("text", "")))
        out.append((x, t, mask, key))
        x += len(t) + 2
    return out


def dropdown_geometry(c: TControl, index: int) -> tuple[int, int, int, int, int]:
    """(x, y, w, h, text width) of the drop-down box of menu *index*."""
    menus = c.get("menus") or []
    items = menus[index].get("items") or []
    tw = 4
    for it in items:
        t = hot_split(str(it.get("text", "")))[0]
        sc = str(it.get("shortcut", "") or "")
        tw = max(tw, len(t) + (len(sc) + 2 if sc else 0))
    w = tw + 4
    h = len(items) + 2
    x = menu_layout(c)[index][0]
    return x, c.y + 1, w, h, tw


# ------------------------------------------------------------------ art files
def load_art(path, cols: int, rows: int) -> CellBuffer | None:
    try:
        from .ansi import load_art as _load
        b = _load(Path(path), cols)
    except (OSError, ValueError):
        return None
    if b.cols != cols or b.rows != rows:
        b = b.resized(cols, rows)
    return b


def resolve(screen: TScreen, rel: str) -> Path | None:
    if not rel:
        return None
    p = Path(rel)
    if not p.is_absolute() and screen.path is not None:
        p = screen.path.parent / p
    return p if p.exists() else None


# ------------------------------------------------------------------ static layer
def render_static(screen: TScreen) -> CellBuffer:
    cols, rows = screen.cols, screen.rows
    buf = CellBuffer(cols, rows, int(screen.get("back_char")) & 0xFF, screen.back_attr())
    art = resolve(screen, str(screen.get("background") or ""))
    if art is not None:
        b = load_art(art, cols, rows)
        if b is not None:
            buf = b
    for c in screen.controls:
        if not c.get("visible", True):
            continue
        draw_static(buf, c)
    return buf


def draw_static(buf: CellBuffer, c: TControl) -> None:
    a = c.attr()
    t = c.type
    if t in ("Window", "Frame"):
        style = c.get("border") or "single"
        buf.box(c.x, c.y, c.w, c.h, style, a, fill=True)
        title = str(c.get("text") or "")
        if title and style != "none" and c.w > 4:
            title = title[:c.w - 4]
            buf.text(title_x(c, title), c.y, title, a)
        if c.get("shadow"):
            buf.shadow(c.x, c.y, c.w, c.h)
    elif t == "Separator":
        double = (c.get("style") or "single") == "double"
        line = 0xCD if double else 0xC4
        ends = {x: (buf.get(x, c.y)[0] if buf.inside(x, c.y) else 0) for x in (c.x, c.x + c.w - 1)}
        buf.fill(c.x, c.y, c.w, 1, line, a)
        if c.get("joined") and c.w >= 2:
            # join with the border under the ends: single / double sides
            for x, d in ((c.x, "r"), (c.x + c.w - 1, "l")):
                ch = ends[x]
                side_double = ch in (0xBA, 0xC9, 0xBB, 0xC8, 0xBC, 0xCC, 0xB9, 0xC7, 0xB6)
                if d == "r":
                    code = (0xCC if side_double else 0xC6) if double else (0xC7 if side_double else 0xC3)
                else:
                    code = (0xB9 if side_double else 0xB5) if double else (0xB6 if side_double else 0xB4)
                buf.put(x, c.y, code, a)
    elif t == "MenuBar":
        buf.fill(c.x, c.y, c.w, 1, 0x20, a)
        ha = hot_attr(c, a)
        for x, text, mask, _k in menu_layout(c):
            buf.hot_text(x, c.y, " " + text + " ", "0" + mask + "0", a, ha)
    elif t == "ListBox":
        style = c.get("border") or "single"
        if style != "none":
            buf.box(c.x, c.y, c.w, c.h, style, a)
    elif t == "Button":
        if c.get("shadow"):
            for xx in range(c.x + 1, c.x + c.w + 1):
                if buf.inside(xx, c.y + 1):
                    buf.put(xx, c.y + 1, 0xDF, _bg(buf.get(xx, c.y + 1)[1]) << 4)
            if buf.inside(c.x + c.w, c.y):
                buf.put(c.x + c.w, c.y, 0xDC, _bg(buf.get(c.x + c.w, c.y)[1]) << 4)


# ------------------------------------------------------------------ faces
class State:
    """Run-time state of the live controls (what the generated program keeps in its arrays)."""

    def __init__(self, screen: TScreen):
        self.text: dict[str, str] = {}
        self.value: dict[str, int] = {}
        self.top: dict[str, int] = {}
        for c in screen.controls:
            if c.type in ("Label", "Button", "TextBox", "CheckBox", "Option", "StatusBar"):
                self.text[c.name] = str(c.get("text") or "")
            if c.type in ("CheckBox", "Option"):
                self.value[c.name] = 1 if c.get("value") else 0
            elif c.type == "ListBox":
                n = len(c.get("items") or [])
                self.value[c.name] = max(-1, min(int(c.get("list_index") or 0), n - 1))
                self.top[c.name] = 0
            elif c.type == "ProgressBar":
                self.value[c.name] = int(c.get("value") or 0)


def draw_face(buf: CellBuffer, c: TControl, st: State | None = None, focused: bool = False,
              designed: bool = True) -> None:
    """The live part of *c*. *designed* = the text still holds the design-time & / ~ markers."""
    if not c.get("visible", True) or c.type not in DYNAMIC_TYPES:
        return
    a, ha = control_attrs(c, focused)
    raw = st.text.get(c.name, str(c.get("text") or "")) if st else str(c.get("text") or "")
    t = c.type
    if t in ("Label", "Button", "CheckBox", "Option", "StatusBar"):
        if designed:
            text, mask, _k = hot_split(raw, "~" if t == "StatusBar" else "&")
        else:
            text, mask = raw, ""
        if t == "Label":
            text, mask = text[:c.w], mask[:c.w]
            align = c.get("align") or "left"
            pad = 0 if align == "left" else ((c.w - len(text)) // 2 if align == "center" else c.w - len(text))
            text, mask = " " * pad + text, "0" * pad + mask
        elif t == "Button":
            text, mask = text[:c.w], mask[:c.w]
            pad = (c.w - len(text)) // 2
            text, mask = " " * pad + text, "0" * pad + mask
        elif t in ("CheckBox", "Option"):
            v = st.value.get(c.name, 0) if st else (1 if c.get("value") else 0)
            prefix = (CHECK_ON if v else CHECK_OFF) if t == "CheckBox" else (OPT_ON if v else OPT_OFF)
            text, mask = prefix + text, "0000" + mask
        buf.hot_text(c.x, c.y, text, mask, a, ha, c.w)
    elif t == "TextBox":
        text = "*" * len(raw) if c.get("password") else raw
        if focused and len(text) >= c.w:
            text = text[len(text) - c.w + 1:]
        buf.text(c.x, c.y, text, a, c.w)
    elif t == "ListBox":
        items = [str(i) for i in (c.get("items") or [])]
        ix, iy, iw, ih = inner_list_rect(c)
        sel = st.value.get(c.name, 0) if st else int(c.get("list_index") or 0)
        top = st.top.get(c.name, 0) if st else 0
        if sel >= 0:
            if sel < top:
                top = sel
            if sel >= top + ih:
                top = sel - ih + 1
        if st:
            st.top[c.name] = top
        sa = mkattr(int(c.get("sel_fore")), int(c.get("sel_back")))
        if not c.get("enabled", True):
            sa = a
        for r in range(ih):
            k = top + r
            s = items[k] if 0 <= k < len(items) else ""
            buf.text(ix, iy + r, s, sa if k == sel and k < len(items) else a, iw)
    elif t == "ProgressBar":
        v = st.value.get(c.name, 0) if st else int(c.get("value") or 0)
        mx = max(1, int(c.get("max") or 100))
        v = max(0, min(v, mx))
        full = v * c.w // mx
        for i in range(c.w):
            buf.put(c.x + i, c.y, PROGRESS_FULL if i < full else PROGRESS_EMPTY, a)


def render(screen: TScreen, focus: str | None = "auto", state: State | None = None) -> CellBuffer:
    """The screen as the running program shows it right after start-up (*focus* "auto" = the first control
    in tab order has the focus, like the runtime; None = no focus, a control name = that control)."""
    buf = render_static(screen)
    if focus == "auto":
        f = screen.first_focus()
        focus = f.name if f else None
    st = state or State(screen)
    for c in screen.controls:
        if c.type in DYNAMIC_TYPES:
            draw_face(buf, c, st, focused=(focus is not None and c.name == focus))
    return buf


def draw_dropdown(buf: CellBuffer, bar: TControl, index: int, selected: int = -1) -> None:
    """An open menu: the title highlighted and the drop-down box (what the runtime draws)."""
    a = bar.attr()
    sa = mkattr(int(bar.get("sel_fore")), int(bar.get("sel_back")))
    lay = menu_layout(bar)
    if not (0 <= index < len(lay)):
        return
    tx, text, mask, _k = lay[index]
    buf.hot_text(tx, bar.y, " " + text + " ", "0" + mask + "0", sa, hot_attr(bar, sa))
    x, y, w, h, tw = dropdown_geometry(bar, index)
    buf.box(x, y, w, h, "single", a, fill=True)
    items = (bar.get("menus") or [])[index].get("items") or []
    for k, it in enumerate(items):
        yy = y + 1 + k
        if str(it.get("text", "")) == "-":
            buf.put(x, yy, 0xC3, a)
            buf.fill(x + 1, yy, w - 2, 1, 0xC4, a)
            buf.put(x + w - 1, yy, 0xB4, a)
            continue
        t, m, _ = hot_split(str(it.get("text", "")))
        sc = str(it.get("shortcut", "") or "")
        line = " " + t.ljust(tw - len(sc)) + sc + " "
        lm = "0" + m.ljust(tw - len(sc), "0") + "0" * (len(sc) + 1)
        ia = sa if k == selected else a
        buf.hot_text(x + 1, yy, line, lm, ia, hot_attr(bar, ia), w - 2)


def msgbox_geometry(cols: int, rows: int, title: str, text: str) -> tuple[int, int, int, int]:
    w = max(len(text) + 4, len(title) + 6, 12)
    w = min(w, cols)
    h = 6
    return (cols - w) // 2, (rows - h) // 2, w, h


MSGBOX_ATTR = 0x70         # black on light grey
MSGBOX_BUTTON = 0x2F       # white on green


def draw_msgbox(buf: CellBuffer, title: str, text: str) -> None:
    x, y, w, h = msgbox_geometry(buf.cols, buf.rows, title, text)
    buf.box(x, y, w, h, "double", MSGBOX_ATTR, fill=True)
    if title:
        t = " " + title[:w - 6] + " "
        buf.text(x + (w - len(t)) // 2, y, t, MSGBOX_ATTR)
    buf.text(x + 2, y + 2, text[:w - 4], MSGBOX_ATTR)
    buf.text(x + (w - 6) // 2, y + 4, "  OK  ", MSGBOX_BUTTON)


def designer_render(screen: TScreen) -> CellBuffer:
    """What the designer canvas shows: the run-time look without focus."""
    return render(screen, focus=None)


def splash_buffer(screen: TScreen) -> CellBuffer | None:
    p = resolve(screen, str(screen.get("splash") or ""))
    return load_art(p, screen.cols, screen.rows) if p else None


__all__ = ["render", "render_static", "draw_face", "draw_static", "draw_dropdown", "draw_msgbox", "State",
           "menu_layout", "dropdown_geometry", "inner_list_rect", "designer_render", "splash_buffer",
           "msgbox_geometry", "encode"]
