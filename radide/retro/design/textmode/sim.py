"""A Python model of the generated program's run-time: the same tables, drawing and event loop as the
BASIC / Pascal / C / asm runtimes, step by step. No Qt in here.

Used by the designer's Test Run (try the screens without DOS) and by the tests, which feed the same keys to
the real program (8086 emulator / DOSBox-X) and to ``Sim`` and compare the screens.

Key codes (as in the runtimes): ASCII 1..255, or 256 + scan code for extended keys (arrows, F-keys,
Alt+letter). ``KEY`` has names for the common ones.
"""
from __future__ import annotations

from .buffer import CellBuffer
from .codegen.common import App, build_app

KEY = {"tab": 9, "shift+tab": 256 + 15, "enter": 13, "esc": 27, "space": 32, "backspace": 8,
       "up": 256 + 72, "down": 256 + 80, "left": 256 + 75, "right": 256 + 77, "f10": 256 + 68,
       "home": 256 + 71, "end": 256 + 79}
ALT_SCAN = {c: 16 + i for i, c in enumerate("QWERTYUIOP")}
ALT_SCAN.update({c: 30 + i for i, c in enumerate("ASDFGHJKL")})
ALT_SCAN.update({c: 44 + i for i, c in enumerate("ZXCVBNM")})
ALT_SCAN.update({c: 120 + i for i, c in enumerate("1234567890")})
ASCII_SCAN: dict[int, int] = {}
for _row, _chars in ((0x10, "qwertyuiop"), (0x1E, "asdfghjkl"), (0x2C, "zxcvbnm"), (0x02, "1234567890")):
    for _k, _ch in enumerate(_chars):
        ASCII_SCAN[ord(_ch)] = _row + _k
        ASCII_SCAN[ord(_ch.upper())] = _row + _k
ASCII_SCAN.update({32: 0x39, 13: 0x1C, 8: 0x0E, 9: 0x0F, 27: 0x01})


def alt(letter: str) -> int:
    return 256 + ALT_SCAN[letter.upper()]


def key_bios(k: int) -> tuple[int, int]:
    """(scan, ascii) a BIOS keyboard buffer holds for key code *k*."""
    if k >= 256:
        return k - 256, 0
    return ASCII_SCAN.get(k, 0), k


def _alt_key(k: int) -> int:
    s = k - 256
    for c, sc in ALT_SCAN.items():
        if sc == s:
            return ord(c)
    return 0


class Sim:
    def __init__(self, screens, basic: bool = False, app: App | None = None):
        self.app = app = app or build_app(screens, basic=basic)
        n = len(app.ctls)
        self.n = n

        def col(attr):
            return [0] + [getattr(c, attr) for c in app.ctls]
        self.t, self.s, self.x, self.y = col("code"), col("screen"), col("x"), col("y")
        self.w, self.h, self.a, self.ha = col("w"), col("h"), col("a"), col("ha")
        self.fa, self.fha, self.sa = col("fa"), col("fha"), col("sa")
        self.v, self.m, self.o, self.k = col("value"), col("max"), col("tab"), col("hotkey")
        self.r, self.e, self.vis, self.en = col("group"), col("events"), col("visible"), col("enabled")
        self.flag, self.first, self.cap = col("flag"), col("first_item"), col("capacity")
        self.count = [0] + [len(c.items) for c in app.ctls]
        self.p = [0] * (n + 1)
        self.tx = [b""] + [bytes(c.text) for c in app.ctls]
        self.hm = [""] + [c.mask for c in app.ctls]
        self.items: dict[int, bytes] = {c.first_item + i: it for c in app.ctls for i, it in enumerate(c.items)}
        self.handlers = {}
        for h in app.handlers:
            if h.kind == "control":
                self.handlers[("c", h.target, {"Click": 1, "Change": 2, "KeyPress": 3}[h.event])] = h.key
            elif h.kind == "menu":
                self.handlers[("m", h.target)] = h.key
            else:
                self.handlers[("s", h.target, 4 if h.event == "Load" else 3)] = h.key
        self.buf = CellBuffer(app.cols, app.rows)
        self.cur = 0
        self.foc = 0
        self.running = True
        self.key = 0
        self.fired: list[str] = []
        self.on_fire = None                     # callable(handler key, sim) - the Test Run's stand-in for code
        self.menu: list[int] | None = None      # [menu, item] while a drop-down is open
        self.msg: tuple[str, str] | None = None
        self.cursor: tuple[int, int] | None = None

    # ------------------------------------------------------------ helpers
    def ctl(self, name: str) -> int:
        for c in self.app.ctls:
            if c.name.lower() == name.lower():
                return c.index
        raise KeyError(name)

    def _fire(self, key: tuple) -> None:
        h = self.handlers.get(key)
        if h:
            self.fired.append(h)
            if self.on_fire is not None:
                self.on_fire(h, self)

    def fire(self, i: int, ev: int) -> None:
        self._fire(("c", i, ev))

    def put(self, x: int, y: int, s: bytes, mask: str, w: int, a: int, h: int) -> None:
        if w <= 0:
            return
        t = bytes(s[:w]).ljust(w, b" ")
        for i, ch in enumerate(t):
            if 0 <= x + i < self.buf.cols:
                self.buf.put(x + i, y, ch, h if i < len(mask) and mask[i] == "1" else a)

    def box(self, x: int, y: int, w: int, h: int, a: int, dbl: bool) -> None:
        self.buf.box(x, y, w, h, "double" if dbl else "single", a, fill=True)

    def blit(self, runs) -> None:
        x = y = 0
        for n, c, a in runs:
            for i in range(n):
                self.buf.put(x + i, y, c, a)
            x += n
            if x >= self.buf.cols:
                x = 0
                y += 1

    # ------------------------------------------------------------ drawing (= TuiFace)
    def face(self, i: int) -> None:
        if not self.vis[i] or self.t[i] == 9:
            return
        t = self.t[i]
        a, h = self.a[i], self.ha[i]
        if not self.en[i]:
            a = (a & 0xF0) | 8
            h = a
        elif i == self.foc and 2 <= t <= 5:
            a, h = self.fa[i], self.fha[i]
        x, y, w = self.x[i], self.y[i], self.w[i]
        tx, hm = self.tx[i], self.hm[i]
        if t == 1:
            s, m = tx[:w], hm[:w]
            p = (w - len(s)) // 2 if self.flag[i] == 1 else (w - len(s) if self.flag[i] == 2 else 0)
            self.put(x, y, b" " * p + s, "0" * p + m, w, a, h)
        elif t == 2:
            s, m = tx[:w], hm[:w]
            p = (w - len(s)) // 2
            self.put(x, y, b" " * p + s, "0" * p + m, w, a, h)
        elif t == 3:
            s = b"*" * len(tx) if self.flag[i] else tx
            if i == self.foc and len(s) >= w:
                s = s[len(s) - w + 1:]
            self.put(x, y, s, "", w, a, a)
        elif t in (4, 5):
            pre = (b"[X] " if self.v[i] else b"[ ] ") if t == 4 else (b"(*) " if self.v[i] else b"( ) ")
            self.put(x, y, pre + tx, "0000" + hm, w, a, h)
        elif t == 6:
            ix, iy, iw, ih = x, y, w, self.h[i]
            if self.flag[i]:
                ix, iy, iw, ih = ix + 1, iy + 1, iw - 2, ih - 2
            sel, tp = self.v[i], self.p[i]
            if sel >= 0:
                if sel < tp:
                    tp = sel
                if sel >= tp + ih:
                    tp = sel - ih + 1
            self.p[i] = tp
            sa = self.sa[i] if self.en[i] else a
            for r in range(ih):
                k = tp + r
                s = self.items.get(self.first[i] + k, b"") if k < self.count[i] else b""
                b = sa if k == sel and k < self.count[i] else a
                self.put(ix, iy + r, s, "", iw, b, b)
        elif t == 7:
            mx = max(1, self.m[i])
            v = max(0, min(self.v[i], mx))
            f = v * w // mx
            self.put(x, y, bytes([0xDB]) * f + bytes([0xB0]) * (w - f), "", w, a, a)
        elif t == 8:
            self.put(x, y, tx, hm, w, a, h)

    def update_cursor(self) -> None:
        i = self.foc
        if i and self.t[i] == 3:
            p = min(len(self.tx[i]), self.w[i] - 1)
            self.cursor = (self.x[i] + p, self.y[i])
        else:
            self.cursor = None

    def redraw(self) -> None:
        self.blit(self.app.screens[self.cur - 1].runs)
        for i in range(1, self.n + 1):
            if self.s[i] == self.cur:
                self.face(i)
        self.update_cursor()
        if self.menu is not None:
            self.draw_menu(*self.menu)
        if self.msg is not None:
            self.draw_msgbox(*self.msg)

    def splash(self) -> bool:
        sp = self.app.splash()
        if sp is None:
            return False
        self.blit(sp.splash_runs)
        return True

    # ------------------------------------------------------------ run-time API
    def can_focus(self, j: int) -> bool:
        return self.o[j] > 0 and bool(self.vis[j]) and bool(self.en[j])

    def show_screen(self, s: int) -> None:
        self.cur = s
        self.foc = 0
        best = 0
        for i in range(1, self.n + 1):
            if self.s[i] == s and self.can_focus(i) and (best == 0 or self.o[i] < self.o[best]):
                best = i
        self.foc = best
        self.redraw()
        if self.app.screens[s - 1].events & 1:
            self._fire(("s", s, 4))

    def start(self) -> "Sim":
        self.show_screen(1)
        return self

    def focus(self, i: int) -> None:
        o = self.foc
        self.foc = i
        if o and o != i:
            self.face(o)
        if i:
            self.face(i)
        self.update_cursor()

    def next(self, d: int) -> None:
        c = self.o[self.foc] if self.foc else 0
        best = wrap = 0
        for j in range(1, self.n + 1):
            if self.s[j] != self.cur or not self.can_focus(j):
                continue
            oj = self.o[j]
            if d > 0:
                if oj > c and (best == 0 or oj < self.o[best]):
                    best = j
                if wrap == 0 or oj < self.o[wrap]:
                    wrap = j
            else:
                if oj < c and (best == 0 or oj > self.o[best]):
                    best = j
                if wrap == 0 or oj > self.o[wrap]:
                    wrap = j
        best = best or wrap
        if best:
            self.focus(best)

    def activate(self, i: int) -> None:
        t = self.t[i]
        if t in (2, 6):
            self.fire(i, 1)
        elif t == 4:
            self.v[i] = 1 - self.v[i]
            self.face(i)
            self.fire(i, 1)
        elif t == 5:
            for j in range(1, self.n + 1):
                if self.t[j] == 5 and self.s[j] == self.s[i] and self.r[j] == self.r[i] and j != i and self.v[j]:
                    self.v[j] = 0
                    self.face(j)
            self.v[i] = 1
            self.face(i)
            self.fire(i, 1)

    def list_move(self, i: int, d: int) -> None:
        n = self.count[i]
        if n == 0:
            return
        v = max(0, min(self.v[i] + d, n - 1))
        if v != self.v[i]:
            self.v[i] = v
            self.face(i)
            self.fire(i, 2)

    def set_text(self, i: int, s) -> None:
        self.tx[i] = s.encode("cp437", "replace") if isinstance(s, str) else bytes(s)
        self.hm[i] = ""
        if self.s[i] == self.cur:
            self.face(i)
            self.update_cursor()

    def get_text(self, i: int) -> str:
        return self.tx[i].decode("cp437")

    def set_value(self, i: int, v: int) -> None:
        if self.t[i] == 5 and v:
            for j in range(1, self.n + 1):
                if self.t[j] == 5 and self.s[j] == self.s[i] and self.r[j] == self.r[i]:
                    self.v[j] = 0
            self.v[i] = 1
        else:
            self.v[i] = v
        if self.s[i] == self.cur:
            self.redraw()

    def msgbox(self, title: str, text: str) -> None:
        self.msg = (title, text)
        self.redraw()

    def draw_msgbox(self, title: str, text: str) -> None:
        from .render import draw_msgbox
        draw_msgbox(self.buf, title, text)
        self.cursor = None

    # ------------------------------------------------------------ events
    def handle_key(self, k: int) -> None:
        if self.msg is not None:
            if k in (13, 27, 32):
                self.msg = None
                self.redraw()
            return
        if self.menu is not None:
            self.menu_key(k)
            return
        self.key = k
        i = self.foc
        if i and self.e[i] & 4:
            self.fire(i, 3)
        if self.key == 0:
            return
        if self.app.screens[self.cur - 1].events & 4:
            self._fire(("s", self.cur, 3))
        k = self.key
        if k == 0:
            return
        i = self.foc
        t = self.t[i] if i else 0
        if t == 3:
            if k == 8:
                if self.tx[i]:
                    self.tx[i] = self.tx[i][:-1]
                    self.face(i)
                    self.update_cursor()
                    if self.e[i] & 2:
                        self.fire(i, 2)
                return
            if 32 <= k < 256:
                if len(self.tx[i]) < self.m[i]:
                    self.tx[i] += bytes([k])
                    self.face(i)
                    self.update_cursor()
                    if self.e[i] & 2:
                        self.fire(i, 2)
                return
        scr = self.app.screens[self.cur - 1]
        if k == 9:
            self.next(1)
        elif k == 256 + 15:
            self.next(-1)
        elif k in (256 + 80, 256 + 77):
            self.list_move(i, 1) if t == 6 else self.next(1)
        elif k in (256 + 72, 256 + 75):
            self.list_move(i, -1) if t == 6 else self.next(-1)
        elif k == 13:
            if t == 3:
                self.next(1)
            elif i:
                self.activate(i)
        elif k == 32:
            if i and t != 6:
                self.activate(i)
        elif k == 27:
            if scr.cancel:
                self.activate(scr.cancel)
            elif scr.esc_quits:
                self.running = False
        elif k == 256 + 68:
            if scr.menu_first:
                self.open_menu(scr.menu_first)
        else:
            h = _alt_key(k) if k > 256 else 0
            if h:
                for m in self.app.menus:
                    if m.screen == self.cur and m.hotkey == h:
                        self.open_menu(m.index)
                        return
            if not h and k < 256 and t != 3:
                h = ord(chr(k).upper()) if chr(k).isascii() else k
            if h:
                for j in range(1, self.n + 1):
                    if self.s[j] == self.cur and self.k[j] == h and self.can_focus(j):
                        self.focus(j)
                        if self.t[j] in (2, 4, 5):
                            self.activate(j)
                        return

    def click(self, x: int, y: int) -> None:
        if self.msg is not None:
            self.msg = None
            self.redraw()
            return
        if self.menu is not None:
            self.menu_click(x, y)
            return
        scr = self.app.screens[self.cur - 1]
        b = scr.bar
        if b and y == self.y[b]:
            for m in self.app.menus:
                if m.screen == self.cur and m.title_x <= x < m.title_x + len(m.title):
                    self.open_menu(m.index)
                    return
            return
        for j in range(self.n, 0, -1):
            if self.s[j] == self.cur and self.can_focus(j) and \
                    self.x[j] <= x < self.x[j] + self.w[j] and self.y[j] <= y < self.y[j] + self.h[j]:
                self.focus(j)
                if self.t[j] == 6:
                    iy, ih = self.y[j], self.h[j]
                    if self.flag[j]:
                        iy, ih = iy + 1, ih - 2
                    r = y - iy
                    if 0 <= r < ih and self.p[j] + r < self.count[j]:
                        if self.v[j] != self.p[j] + r:
                            self.v[j] = self.p[j] + r
                            self.face(j)
                            if self.e[j] & 2:
                                self.fire(j, 2)
                        self.fire(j, 1)
                elif self.t[j] != 3:
                    self.activate(j)
                return

    # ------------------------------------------------------------ menus (= TuiMenu, as a state machine)
    def step(self, m: int, it: int, d: int) -> int:
        mn = self.app.menus[m - 1]
        n = mn.count
        if n == 0:
            return -1
        k = it
        for _ in range(n):
            k += d
            if k < 0:
                k = n - 1
            if k >= n:
                k = 0
            if not self.app.items[mn.first_item + k - 1].sep:
                return k
        return -1

    def open_menu(self, m: int) -> None:
        self.menu = [m, self.step(m, -1, 1)]
        self.redraw()

    def draw_menu(self, m: int, it: int) -> None:
        mn = self.app.menus[m - 1]
        b = self.app.screens[mn.screen - 1].bar
        self.put(mn.title_x, self.y[b], mn.title, mn.mask, len(mn.title), self.sa[b], self.fha[b])
        x, y, w, h = mn.box
        self.box(x, y, w, h, self.a[b], False)
        for k in range(mn.count):
            item = self.app.items[mn.first_item + k - 1]
            if item.sep:
                self.put(x, y + 1 + k, bytes([0xC3]) + bytes([0xC4]) * (w - 2) + bytes([0xB4]), "", w,
                         self.a[b], self.a[b])
            elif k == it:
                self.put(x + 1, y + 1 + k, item.line, item.mask, w - 2, self.sa[b], self.fha[b])
            else:
                self.put(x + 1, y + 1 + k, item.line, item.mask, w - 2, self.a[b], self.ha[b])

    def _close_menu(self, fire: int = 0) -> None:
        self.menu = None
        self.redraw()
        if fire:
            self._fire(("m", fire))

    def menu_key(self, k: int) -> None:
        m, it = self.menu
        scr = self.app.screens[self.cur - 1]
        mn = self.app.menus[m - 1]
        if k in (27, 256 + 68):
            return self._close_menu()
        if k == 256 + 75:
            m = m - 1 if m - 1 >= scr.menu_first else scr.menu_last
            self.menu = [m, self.step(m, -1, 1)]
        elif k == 256 + 77:
            m = m + 1 if m + 1 <= scr.menu_last else scr.menu_first
            self.menu = [m, self.step(m, -1, 1)]
        elif k == 256 + 72:
            self.menu = [m, self.step(m, it, -1)]
        elif k == 256 + 80:
            self.menu = [m, self.step(m, it, 1)]
        elif k == 13:
            if it >= 0:
                return self._close_menu(mn.first_item + it)
            return
        else:
            h = 0
            if k > 256:
                h = _alt_key(k)
                for m2 in range(scr.menu_first, scr.menu_last + 1):
                    if h and self.app.menus[m2 - 1].hotkey == h:
                        self.menu = [m2, self.step(m2, -1, 1)]
                        h = 0
                        self.redraw()
                        return
            elif k < 256:
                h = ord(chr(k).upper()) if chr(k).isascii() else k
            if h:
                for k2 in range(mn.count):
                    item = self.app.items[mn.first_item + k2 - 1]
                    if item.hotkey == h and not item.sep:
                        return self._close_menu(mn.first_item + k2)
            return
        self.redraw()

    def menu_click(self, x: int, y: int) -> None:
        m, it = self.menu
        scr = self.app.screens[self.cur - 1]
        mn = self.app.menus[m - 1]
        b = scr.bar
        if y == self.y[b]:
            for m2 in range(scr.menu_first, scr.menu_last + 1):
                t = self.app.menus[m2 - 1]
                if t.title_x <= x < t.title_x + len(t.title):
                    self.menu = [m2, self.step(m2, -1, 1)]
                    self.redraw()
                    return
            return self._close_menu()
        bx, by, bw, bh = mn.box
        if bx < x < bx + bw - 1 and by < y < by + bh - 1:
            j = mn.first_item + y - by - 1
            if not self.app.items[j - 1].sep:
                return self._close_menu(j)
            return
        self._close_menu()
