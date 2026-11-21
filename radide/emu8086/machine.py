"""The emulated PC around the CPU: memory map, interrupt vector table with ROM stubs, a minimal DOS (INT 20h /
21h), BIOS video (INT 10h, text mode 80x25 at B800:0000 and mode 13h at A000:0000), keyboard (INT 16h), clock
(INT 1Ah / INT 15h AH=86h) and the run control the debugger needs (breakpoints, step, step over, step out,
reverse step with an undo history).

    m = Machine()
    m.load(program)                   # a radide.emu8086.assembler.Program
    m.feed_keys("12\\r")              # keyboard input (ASCII; see push_key for scan codes)
    m.run(max_steps=1_000_000)        # -> stop reason: "exit" | "break" | "input" | "limit" | "error" | "halt"
    m.screen_text()                   # the 80x25 text screen
    m.output                          # everything written through DOS / BIOS teletype (like stdout)
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

from .cpu import AX, BP, BX, CF, CPU, CS, CX, DI, DS, DX, ES, IF, SI, SP, SS, ZF, CPUError
from .messages import text as _msg

ROM_SEG = 0xF000
BDA_SEG = 0x0040
COLS, ROWS = 80, 25
TEXT_BASE = 0xB8000
GFX_BASE = 0xA0000
TICK_US = 54925                       # one timer tick (18.2 Hz)
VIRTUAL_MHZ = 1.0                     # instructions per microsecond of emulated time

# ASCII -> PC/XT scan code (US layout) for keys pushed as text
_SCAN = {}
for _row, _keys in ((0x02, "1234567890-="), (0x10, "qwertyuiop[]"), (0x1E, "asdfghjkl;'`"), (0x2B, "\\zxcvbnm,./")):
    for _k, _ch in enumerate(_keys):
        _SCAN[_ch] = _row + _k
for _row, _keys in ((0x02, "!@#$%^&*()_+"), (0x10, "QWERTYUIOP{}"), (0x1E, 'ASDFGHJKL:"~'), (0x2B, "|ZXCVBNM<>?")):
    for _k, _ch in enumerate(_keys):
        _SCAN[_ch] = _row + _k
_SCAN.update({" ": 0x39, "\r": 0x1C, "\n": 0x1C, "\b": 0x0E, "\t": 0x0F, "\x1b": 0x01})
# named extended keys -> (scan, ascii)
KEYS = {"up": (0x48, 0), "down": (0x50, 0), "left": (0x4B, 0), "right": (0x4D, 0), "home": (0x47, 0),
        "end": (0x4F, 0), "pgup": (0x49, 0), "pgdn": (0x51, 0), "ins": (0x52, 0), "del": (0x53, 0),
        "esc": (0x01, 0x1B), "enter": (0x1C, 0x0D), "backspace": (0x0E, 0x08), "tab": (0x0F, 0x09),
        "space": (0x39, 0x20)}
for _i in range(10):
    KEYS[f"f{_i + 1}"] = (0x3B + _i, 0)

# the 16 CGA text colours (RGB)
CGA = [(0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170), (170, 0, 0), (170, 0, 170), (170, 85, 0),
       (170, 170, 170), (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255), (255, 85, 85),
       (255, 85, 255), (255, 255, 85), (255, 255, 255)]


def vga_palette() -> list:
    """Mode 13h default palette: 16 CGA colours, a grey ramp, then hue rings."""
    pal = list(CGA)
    for i in range(16):
        g = int(i * 255 / 15)
        pal.append((g, g, g))
    import colorsys
    for ring in range(3):
        sat_val = [(1.0, 1.0), (0.55, 1.0), (0.3, 1.0)][ring]
        for k in range(24):
            r, g, b = colorsys.hsv_to_rgb(k / 24, *sat_val)
            pal.append((int(r * 255), int(g * 255), int(b * 255)))
    for dim in (0.45, 0.25):
        for k in range(24):
            r, g, b = colorsys.hsv_to_rgb(k / 24, 1.0, dim)
            pal.append((int(r * 255), int(g * 255), int(b * 255)))
    while len(pal) < 256:
        pal.append((0, 0, 0))
    return pal[:256]


@dataclass
class StopInfo:
    reason: str                   # exit | break | step | input | limit | error | halt | pause
    message: str = ""
    code: int = 0


class Machine:
    HISTORY = 200_000

    def __init__(self):
        self.mem = bytearray(0x100000 + 0x10000)
        self.cpu = CPU(self.mem)
        self.cpu.hook = self._service
        self.cpu.port_in = self._port_in
        self.cpu.port_out = self._port_out
        self.program = None
        self.lang = "en"
        self.breakpoints: set[int] = set()        # linear addresses
        self.history: deque = deque(maxlen=self.HISTORY)
        self.record_history = True
        self.output = ""
        self.keys: deque = deque()                # (scan, ascii)
        self.exited = False
        self.exit_code = 0
        self.error = ""
        self.waiting = ""                         # "key" while an input service waits
        self.sleep_until_us = 0
        self.vtime_us = 0                         # emulated time (1 instruction = 1 us)
        self.clock_base = time.localtime()
        self.cursor = [0, 0]                      # row, col (page 0)
        self.cursor_visible = True
        self.video_mode = 3
        self.text_attr = 0x07
        self._line_buf: list | None = None        # INT 21h AH=0Ah in progress
        self._pending_ext = None                  # second byte of an extended key (INT 21h AH=01/07/08)
        self._retrying = False                    # the current service already waited for a key
        self.return_target = None                 # step over in progress: (linear, ss, sp)
        self.blink = True
        self.realtime = False                     # the IDE session paces INT 15h AH=86h waits in real time
        self.pending_sleep_us = 0
        self.log: list[str] = []                  # notes for the Output window (unsupported services ...)
        self.speaker = 0
        self.palette = vga_palette()
        self._last_tick_us = 0

    # ================================================================== loading
    def reset_memory(self) -> None:
        self.mem[:] = bytes(len(self.mem))
        m = self.mem
        # IVT: every vector -> ROM stub F000:(n*8)  "F1 n CF"
        for n in range(256):
            off = n * 8
            m[n * 4:n * 4 + 4] = bytes([off & 0xFF, off >> 8, ROM_SEG & 0xFF, ROM_SEG >> 8])
            a = (ROM_SEG << 4) + off
            if n == 0x08:                    # timer: tick, then INT 1Ch, then IRET
                m[a:a + 5] = bytes([0xF1, n, 0xCD, 0x1C, 0xCF])
            else:
                m[a:a + 3] = bytes([0xF1, n, 0xCF])
        # BIOS data area
        bda = BDA_SEG << 4
        m[bda + 0x10] = 0x21                 # equipment: 80x25 colour
        m[bda + 0x13:bda + 0x15] = (640).to_bytes(2, "little")
        m[bda + 0x49] = 3                    # video mode
        m[bda + 0x4A] = COLS
        m[bda + 0x84] = ROWS - 1
        # ROM: "IBM compatible" date and model bytes
        m[0xFFFF5:0xFFFFD] = b"11/21/26"
        m[0xFFFFE] = 0xFF
        self._clear_text(0, 0, ROWS - 1, COLS - 1, 0x07)

    def load(self, program) -> None:
        self.program = program
        self.reset_memory()
        self.cpu.__init__(self.mem)
        self.cpu.hook = self._service
        self.cpu.port_in = self._port_in
        self.cpu.port_out = self._port_out
        self.output = ""
        self.exited = False
        self.exit_code = 0
        self.error = ""
        self.waiting = ""
        self.history.clear()
        self.vtime_us = 0
        self._last_tick_us = 0
        self.sleep_until_us = 0
        self.cursor = [0, 0]
        self.cursor_visible = True
        self.video_mode = 3
        self._line_buf = None
        self._pending_ext = None
        self._retrying = False
        self.return_target = None
        self.log = []
        psp = program.load_seg
        self._make_psp(psp, program.end_linear >> 4)
        for lin, data in program.chunks:
            self.mem[lin:lin + len(data)] = data
        c = self.cpu
        c.s[CS] = program.entry_cs
        c.ip = program.entry_ip
        c.s[DS] = program.ds
        c.s[ES] = program.es
        c.s[SS] = program.ss
        c.r[SP] = program.sp
        c.flags = 0xF202                     # IF set
        if program.com:                      # RET from a COM program -> PSP:0 (INT 20h)
            c.r[SP] = (c.r[SP] - 2) & 0xFFFF
            self.mem[(c.s[SS] << 4) + c.r[SP]] = 0
            self.mem[(c.s[SS] << 4) + c.r[SP] + 1] = 0
        c.r[CX] = 0x00FF
        c.r[DX] = program.load_seg if not program.com else program.entry_cs
        c.r[SI] = c.ip
        c.r[DI] = c.r[SP]
        c.r[BP] = 0x091C
        c.undo = None

    def _make_psp(self, seg: int, end_para: int) -> None:
        a = seg << 4
        m = self.mem
        m[a:a + 2] = b"\xCD\x20"                       # INT 20h
        m[a + 2:a + 4] = (min(end_para, 0x9FFF) & 0xFFFF).to_bytes(2, "little")
        m[a + 0x2C:a + 0x2E] = b"\0\0"
        m[a + 0x50:a + 0x53] = b"\xCD\x21\xCB"        # INT 21h / RETF
        m[a + 0x80] = 0                                # empty command tail
        m[a + 0x81] = 0x0D

    # ================================================================== keyboard
    def push_key(self, scan: int, ascii_: int) -> None:
        self.keys.append((scan & 0xFF, ascii_ & 0xFF))
        if self.waiting == "key":
            self.waiting = ""

    def feed_keys(self, text: str) -> None:
        """Type *text* (\\r or \\n = Enter)."""
        for ch in text:
            if ch == "\n":
                ch = "\r"
            code = ord(ch) if ord(ch) < 256 else ord("?")
            self.push_key(_SCAN.get(ch, 0), code)

    def press(self, name: str) -> None:
        scan, ascii_ = KEYS[name.lower()]
        self.push_key(scan, ascii_)

    # ================================================================== screen helpers
    def _cell(self, row: int, col: int) -> int:
        return TEXT_BASE + (row * COLS + col) * 2

    def _put_cell(self, row: int, col: int, ch: int, attr: int | None) -> None:
        a = self._cell(row, col)
        self.cpu.write_linear(a, ch)
        if attr is not None:
            self.cpu.write_linear(a + 1, attr)

    def _clear_text(self, r1, c1, r2, c2, attr) -> None:
        for r in range(max(0, r1), min(ROWS - 1, r2) + 1):
            for c in range(max(0, c1), min(COLS - 1, c2) + 1):
                a = self._cell(r, c)
                if self.cpu.undo is not None:
                    self.cpu.write_linear(a, 0x20)
                    self.cpu.write_linear(a + 1, attr)
                else:
                    self.mem[a] = 0x20
                    self.mem[a + 1] = attr
        self.cpu.video_dirty = True

    def _scroll(self, lines, attr, r1, c1, r2, c2, up=True) -> None:
        r1, r2 = max(0, r1), min(ROWS - 1, r2)
        c1, c2 = max(0, c1), min(COLS - 1, c2)
        if r1 > r2 or c1 > c2:
            return
        height = r2 - r1 + 1
        if lines == 0 or lines >= height:
            self._clear_text(r1, c1, r2, c2, attr)
            return
        rows = range(r1, r2 - lines + 1) if up else range(r2, r1 + lines - 1, -1)
        for r in rows:
            src = r + lines if up else r - lines
            for c in range(c1, c2 + 1):
                s = self._cell(src, c)
                self._put_cell(r, c, self.mem[s], self.mem[s + 1])
        if up:
            self._clear_text(r2 - lines + 1, c1, r2, c2, attr)
        else:
            self._clear_text(r1, c1, r1 + lines - 1, c2, attr)

    def _teletype(self, ch: int, attr: int | None = None) -> None:
        """BIOS TTY output at the cursor (CR, LF, BS, BEL, TAB handled), scrolling at the bottom."""
        self.output += chr(ch) if ch < 128 else bytes([ch]).decode("cp437")
        if self.video_mode == 0x13:
            return
        row, col = self.cursor
        if ch == 0x0D:
            col = 0
        elif ch == 0x0A:
            row += 1
        elif ch == 0x08:
            col = max(0, col - 1)
        elif ch == 0x07:
            self.speaker += 1
        elif ch == 0x09:
            col = (col // 8 + 1) * 8
        else:
            self._put_cell(row, col, ch, attr)
            col += 1
        if col >= COLS:
            col = 0
            row += 1
        if row >= ROWS:
            self._scroll(1, 0x07, 0, 0, ROWS - 1, COLS - 1)
            row = ROWS - 1
        self.cursor = [row, col]
        self._sync_cursor_bda()

    def _sync_cursor_bda(self) -> None:
        a = (BDA_SEG << 4) + 0x50
        self.mem[a] = self.cursor[1]
        self.mem[a + 1] = self.cursor[0]

    def screen_text(self, trim: bool = True) -> str:
        lines = []
        for r in range(ROWS):
            row = bytes(self.mem[self._cell(r, c)] for c in range(COLS))
            s = row.decode("cp437").replace("\0", " ")
            lines.append(s.rstrip() if trim else s)
        while trim and lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)

    def cell(self, row: int, col: int) -> tuple[int, int]:
        a = self._cell(row, col)
        return self.mem[a], self.mem[a + 1]

    # ================================================================== services
    def _note(self, code: str, **args) -> None:
        msg = _msg(code, self.lang, **args)
        if msg not in self.log:
            self.log.append(msg)

    def _wait_key(self) -> bool:
        """True when a key is available, else mark the CPU to retry the service."""
        if self.keys:
            return True
        self.waiting = "key"
        self.cpu.retry = True
        return False

    def _service(self, n: int) -> None:
        try:
            self._service_inner(n)
        finally:
            self._retrying = self.cpu.retry

    def _service_inner(self, n: int) -> None:
        c = self.cpu
        ah = c.r[AX] >> 8
        if n == 0x21:
            self._int21(ah)
        elif n == 0x10:
            self._int10(ah)
        elif n == 0x16:
            self._int16(ah)
        elif n == 0x20:
            self._terminate(0)
        elif n == 0x1A:
            self._int1a(ah)
        elif n == 0x15:
            if ah == 0x86:                                   # wait CX:DX microseconds
                us = (c.r[CX] << 16) | c.r[DX]
                self.sleep_until_us = self.vtime_us + us
                self.vtime_us += us
                if self.realtime:
                    self.pending_sleep_us += us
                c.flags &= ~CF
            else:
                c.flags |= CF
                self.cpu.set8(4, 0x86)
        elif n == 0x08:
            a = (BDA_SEG << 4) + 0x6C
            t = int.from_bytes(self.mem[a:a + 4], "little") + 1
            for k, b in enumerate(t.to_bytes(4, "little")):
                self.cpu.write_linear(a + k, b)
        elif n == 0x00:
            self._fatal("R-DIV0", addr=f"{c.s[CS]:04X}:{c.ip:04X}")
        elif n == 0x11:
            c.r[AX] = int.from_bytes(self.mem[0x410:0x412], "little")
        elif n == 0x12:
            c.r[AX] = 640
        elif n in (0x1C, 0x03, 0x01, 0x04, 0x05, 0x33, 0x28, 0x2F):
            if n == 0x33:
                c.r[AX] = 0                               # no mouse driver
        else:
            self._note("R-INT", num=f"{n:02X}h", fn=f"{ah:02X}h")

    def _terminate(self, code: int) -> None:
        self.exited = True
        self.exit_code = code

    def _fatal(self, code: str, **args) -> None:
        self.error = _msg(code, self.lang, **args)
        self.exited = True
        self.exit_code = -1

    def _read_ascii(self, echo: bool) -> bool:
        """INT 21h AH=01/07/08: AL = next character (extended keys give 0, then the scan code)."""
        c = self.cpu
        if self._pending_ext is not None:
            c.set8(0, self._pending_ext)
            self._pending_ext = None
            return True
        if not self._wait_key():
            return False
        scan, ch = self.keys.popleft()
        if ch == 0:
            self._pending_ext = scan
        c.set8(0, ch)
        if echo and ch:
            self._teletype(ch)
        return True

    def _int21(self, ah: int) -> None:
        c = self.cpu
        al = c.r[AX] & 0xFF
        if ah == 0x01:
            self._read_ascii(True)
        elif ah == 0x02:
            ch = c.r[DX] & 0xFF
            self._teletype(ch)
            c.set8(0, ch)
        elif ah == 0x06:
            dl = c.r[DX] & 0xFF
            if dl == 0xFF:
                if self._pending_ext is not None or self.keys:
                    self._read_ascii(False)
                    c.flags &= ~ZF
                else:
                    c.set8(0, 0)
                    c.flags |= ZF
            else:
                self._teletype(dl)
                c.set8(0, dl)
        elif ah in (0x07, 0x08):
            self._read_ascii(False)
        elif ah == 0x09:
            seg, off = c.s[DS], c.r[DX]
            for _ in range(0x10000):
                ch = c.rb(seg, off)
                if ch == 0x24:                         # '$'
                    break
                self._teletype(ch)
                off = (off + 1) & 0xFFFF
            c.set8(0, 0x24)
        elif ah == 0x0A:
            self._buffered_input()
        elif ah == 0x0B:
            c.set8(0, 0xFF if (self.keys or self._pending_ext is not None) else 0)
        elif ah == 0x0C:                               # flush the keyboard buffer, then AL's function
            if not self._retrying:
                self.keys.clear()
                self._pending_ext = None
            if al in (0x01, 0x06, 0x07, 0x08, 0x0A):
                self._int21(al)
        elif ah == 0x0E:
            c.set8(0, 1)
        elif ah == 0x19:
            c.set8(0, 2)                               # drive C:
        elif ah == 0x25:
            n = al
            for k, b in enumerate(((c.r[DX]) & 0xFFFF).to_bytes(2, "little") + c.s[DS].to_bytes(2, "little")):
                c.write_linear(n * 4 + k, b)
        elif ah == 0x2A:
            t = self._now()
            c.r[CX] = t.tm_year
            c.r[DX] = (t.tm_mon << 8) | t.tm_mday
            c.set8(0, (t.tm_wday + 1) % 7)
        elif ah == 0x2C:
            t = self._now()
            hund = (self.vtime_us // 10000) % 100
            c.r[CX] = (t.tm_hour << 8) | t.tm_min
            c.r[DX] = (t.tm_sec << 8) | hund
        elif ah == 0x30:
            c.r[AX] = 0x0005                           # DOS 5.0
            c.r[BX] = 0
            c.r[CX] = 0
        elif ah == 0x35:
            c.r[BX] = c.rw(0, al * 4)
            c.s[ES] = c.rw(0, al * 4 + 2)
        elif ah == 0x40:                               # write to handle 1/2
            if c.r[BX] in (1, 2):
                for k in range(c.r[CX]):
                    self._teletype(c.rb(c.s[DS], c.r[DX] + k))
                c.r[AX] = c.r[CX]
                c.flags &= ~CF
            else:
                c.r[AX] = 6
                c.flags |= CF
        elif ah == 0x3F:                               # read from handle 0 (a line)
            if c.r[BX] != 0:
                c.r[AX] = 6
                c.flags |= CF
                return
            self._handle_read()
        elif ah == 0x4C:
            self._terminate(al)
        elif ah == 0x00:
            self._terminate(0)
        elif ah == 0x31:
            self._terminate(al)
        elif ah == 0x48:                               # allocate: give memory after the program
            c.r[AX] = 0x8000
            if c.r[BX] > 0x1000:
                c.r[BX] = 0x1000
                c.r[AX] = 8
                c.flags |= CF
            else:
                c.flags &= ~CF
        elif ah in (0x49, 0x4A):
            c.flags &= ~CF
        else:
            self._note("R-INT", num="21h", fn=f"{ah:02X}h")

    def _buffered_input(self) -> None:
        """INT 21h AH=0Ah: DS:DX -> [max][count][chars...CR]; line editing with Backspace."""
        c = self.cpu
        seg, off = c.s[DS], c.r[DX]
        maxlen = c.rb(seg, off)
        if self._line_buf is None:
            self._line_buf = []
        while True:
            if not self._wait_key():
                return
            scan, ch = self.keys.popleft()
            if ch == 0x0D:
                break
            if ch == 0x08:
                if self._line_buf:
                    self._line_buf.pop()
                    self._teletype(0x08)
                    self._teletype(0x20)
                    self._teletype(0x08)
                continue
            if ch == 0 or ch == 0x1B:
                continue
            if maxlen and len(self._line_buf) < maxlen - 1:
                self._line_buf.append(ch)
                self._teletype(ch)
            else:
                self.speaker += 1
        buf, self._line_buf = self._line_buf, None
        c.wb(seg, off + 1, len(buf))
        for k, ch in enumerate(buf):
            c.wb(seg, off + 2 + k, ch)
        c.wb(seg, off + 2 + len(buf), 0x0D)
        self._teletype(0x0D)
        c.retry = False

    def _handle_read(self) -> None:
        c = self.cpu
        if self._line_buf is None:
            self._line_buf = []
        while True:
            if not self._wait_key():
                return
            scan, ch = self.keys.popleft()
            if ch == 0x0D:
                break
            if ch == 0x08:
                if self._line_buf:
                    self._line_buf.pop()
                    for b in (8, 32, 8):
                        self._teletype(b)
                continue
            if ch:
                self._line_buf.append(ch)
                self._teletype(ch)
        data = bytes(self._line_buf) + b"\r\n"
        self._line_buf = None
        self._teletype(0x0D)
        self._teletype(0x0A)
        n = min(len(data), c.r[CX])
        for k in range(n):
            c.wb(c.s[DS], c.r[DX] + k, data[k])
        c.r[AX] = n
        c.flags &= ~CF

    def _now(self):
        base = time.mktime(self.clock_base)
        return time.localtime(base + self.vtime_us / 1_000_000)

    def _int1a(self, ah: int) -> None:
        c = self.cpu
        if ah == 0x00:
            t = self._now()
            secs = t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec + (self.vtime_us % 1_000_000) / 1_000_000
            ticks = int(secs * 18.2065)
            c.r[CX] = (ticks >> 16) & 0xFFFF
            c.r[DX] = ticks & 0xFFFF
            c.set8(0, 0)
        elif ah == 0x02:
            t = self._now()
            bcd = lambda v: ((v // 10) << 4) | (v % 10)  # noqa: E731
            c.r[CX] = (bcd(t.tm_hour) << 8) | bcd(t.tm_min)
            c.r[DX] = bcd(t.tm_sec) << 8
            c.flags &= ~CF
        elif ah == 0x04:
            t = self._now()
            bcd = lambda v: ((v // 10) << 4) | (v % 10)  # noqa: E731
            c.r[CX] = (bcd(t.tm_year // 100) << 8) | bcd(t.tm_year % 100)
            c.r[DX] = (bcd(t.tm_mon) << 8) | bcd(t.tm_mday)
            c.flags &= ~CF
        else:
            self._note("R-INT", num="1Ah", fn=f"{ah:02X}h")

    def _int16(self, ah: int) -> None:
        c = self.cpu
        if ah in (0x00, 0x10):
            if not self._wait_key():
                return
            scan, ch = self.keys.popleft()
            c.r[AX] = (scan << 8) | ch
        elif ah in (0x01, 0x11):
            if self.keys:
                scan, ch = self.keys[0]
                c.r[AX] = (scan << 8) | ch
                c.flags &= ~ZF
            else:
                c.flags |= ZF
        elif ah in (0x02, 0x12):
            c.set8(0, 0)
        else:
            self._note("R-INT", num="16h", fn=f"{ah:02X}h")

    def _int10(self, ah: int) -> None:
        c = self.cpu
        al = c.r[AX] & 0xFF
        bh, bl = c.r[BX] >> 8, c.r[BX] & 0xFF
        ch_, cl = c.r[CX] >> 8, c.r[CX] & 0xFF
        dh, dl = c.r[DX] >> 8, c.r[DX] & 0xFF
        if ah == 0x00:                                     # set video mode
            mode = al & 0x7F
            self.video_mode = 0x13 if mode == 0x13 else 3
            self.mem[(BDA_SEG << 4) + 0x49] = self.video_mode
            if not al & 0x80:
                if self.video_mode == 0x13:
                    for a in range(GFX_BASE, GFX_BASE + 64000):
                        if self.mem[a]:
                            c.write_linear(a, 0)
                else:
                    self._clear_text(0, 0, ROWS - 1, COLS - 1, 0x07)
            self.cursor = [0, 0]
            self._sync_cursor_bda()
            c.video_dirty = True
        elif ah == 0x01:
            self.cursor_visible = not (ch_ & 0x20)
        elif ah == 0x02:
            self.cursor = [min(dh, ROWS - 1), min(dl, COLS - 1)]
            self._sync_cursor_bda()
            c.video_dirty = True
        elif ah == 0x03:
            c.r[DX] = (self.cursor[0] << 8) | self.cursor[1]
            c.r[CX] = 0x0607 if self.cursor_visible else 0x2000
        elif ah == 0x05:
            pass                                           # only page 0
        elif ah in (0x06, 0x07):
            self._scroll(al, bh, ch_, cl, dh, dl, up=(ah == 0x06))
        elif ah == 0x08:
            ch, attr = self.cell(*self.cursor)
            c.r[AX] = (attr << 8) | ch
        elif ah in (0x09, 0x0A):
            if self.video_mode == 0x13:
                for _ in range(c.r[CX]):
                    self._teletype(al)
                return
            row, col = self.cursor
            for k in range(c.r[CX]):
                p = row * COLS + col + k
                if p >= ROWS * COLS:
                    break
                self._put_cell(p // COLS, p % COLS, al, bl if ah == 0x09 else None)
        elif ah == 0x0C:                                   # write pixel
            if self.video_mode == 0x13 and c.r[CX] < 320 and c.r[DX] < 200:
                a = GFX_BASE + c.r[DX] * 320 + c.r[CX]
                c.write_linear(a, al)                 # 256 colours: no XOR mode
        elif ah == 0x0D:
            if self.video_mode == 0x13 and c.r[CX] < 320 and c.r[DX] < 200:
                c.set8(0, self.mem[GFX_BASE + c.r[DX] * 320 + c.r[CX]])
        elif ah == 0x0E:
            if self.video_mode == 0x13:
                self.output += chr(al)
                return
            self._teletype(al)
        elif ah == 0x0F:
            c.r[AX] = (COLS << 8) | self.video_mode
            c.set8(7, 0)
        elif ah == 0x10:
            if al == 0x03:
                self.blink = bool(bl)
        elif ah == 0x11 or ah == 0x12 or ah == 0x1A:
            if ah == 0x1A:
                c.set8(0, 0x1A)
                c.r[BX] = 0x0008
        elif ah == 0x13:                                   # write string ES:BP
            row, col = dh, dl
            saved = list(self.cursor)
            self.cursor = [min(row, ROWS - 1), min(col, COLS - 1)]
            seg, off = c.s[ES], c.r[BP]
            attr = bl
            for k in range(c.r[CX]):
                if al & 2:
                    ch = c.rb(seg, off + 2 * k)
                    attr = c.rb(seg, off + 2 * k + 1)
                else:
                    ch = c.rb(seg, off + k)
                if ch in (7, 8, 10, 13):
                    self._teletype(ch)
                else:
                    self._teletype(ch, attr)
            if not al & 1:
                self.cursor = saved
                self._sync_cursor_bda()
        else:
            self._note("R-INT", num="10h", fn=f"{ah:02X}h")

    # ================================================================== ports
    def _port_in(self, port: int, w: int) -> int:
        if port == 0x60:
            return self.keys[0][0] if self.keys else 0
        if port == 0x64:
            return 0x01 if self.keys else 0
        if port == 0x61:
            return 0x20
        if port in (0x40, 0x41, 0x42):
            return (self.vtime_us >> 2) & 0xFF
        if port == 0x3DA:
            return (self.vtime_us // 100) & 0x09     # retrace bits toggle over time
        return 0xFF

    def _port_out(self, port: int, value: int, w: int) -> None:
        if port == 0x61 and value & 3 == 3:
            self.speaker += 1

    # ================================================================== run control
    def state(self) -> tuple:
        c = self.cpu
        return (tuple(c.r), tuple(c.s), c.ip, c.flags, tuple(self.cursor), self.video_mode, len(self.output),
                tuple(self.keys), self._pending_ext, None if self._line_buf is None else tuple(self._line_buf),
                self.exited, self.exit_code, self.vtime_us, self.cursor_visible, self.output)

    def _restore(self, st: tuple) -> None:
        c = self.cpu
        c.r[:] = list(st[0])
        c.s[:] = list(st[1])
        c.ip, c.flags = st[2], st[3]
        self.cursor = list(st[4])
        self.video_mode = st[5]
        self.keys = deque(st[7])
        self._pending_ext = st[8]
        self._line_buf = None if st[9] is None else list(st[9])
        self.exited, self.exit_code, self.vtime_us = st[10], st[11], st[12]
        self.cursor_visible = st[13]
        self.output = st[14]
        self.waiting = ""
        self._retrying = False
        self.return_target = None
        self._sync_cursor_bda()
        c.video_dirty = True

    def step(self) -> StopInfo | None:
        """Execute one instruction. Returns a StopInfo when the program cannot go on (exit, error, input)."""
        if self.exited:
            return StopInfo("exit", code=self.exit_code)
        c = self.cpu
        snap = None
        if self.record_history:
            snap = self.state()
            c.undo = []
        try:
            c.step()
        except CPUError as e:
            if snap is not None:
                self._rollback(snap, c.undo)
            c.undo = None
            self.error = _msg(e.code, self.lang, **e.args_)
            return StopInfo("error", self.error)
        if snap is not None:
            if c.retry and not c.undo and self.waiting:
                pass                                  # waiting for a key: nothing changed, no history entry
            else:
                self.history.append((snap, c.undo))
            c.undo = None
        self.vtime_us += 1
        if self.vtime_us - self._last_tick_us >= TICK_US:
            self._last_tick_us = self.vtime_us
            if c.flags & IF and not self.waiting and self._ivt_hooked(0x1C, 0x08):
                c.interrupt(0x08)
        if self.exited:
            if self.error:
                return StopInfo("error", self.error, -1)
            return StopInfo("exit", code=self.exit_code)
        if self.waiting:
            return StopInfo("input", _msg("R-INPUT", self.lang))
        if c.halted:
            c.halted = False
            self.exited = True
            return StopInfo("halt", _msg("R-HALT", self.lang, addr=f"{c.op_cs:04X}:{c.op_ip:04X}"))
        return None

    def _ivt_hooked(self, *vectors) -> bool:
        """Only fire the timer when the program installed its own INT 08h / 1Ch handler."""
        for n in vectors:
            if self.cpu.rw(0, n * 4 + 2) != ROM_SEG:
                return True
        return False

    def _rollback(self, snap, undo) -> None:
        for a, old in reversed(undo or []):
            self.mem[a] = old
        self._restore(snap)

    def step_back(self) -> bool:
        if not self.history:
            return False
        snap, undo = self.history.pop()
        self._rollback(snap, undo)
        return True

    def linear_ip(self) -> int:
        return ((self.cpu.s[CS] << 4) + self.cpu.ip) & 0xFFFFF

    def current_line(self):
        if self.program is None:
            return None
        return self.program.addr_line.get(self.linear_ip())

    def run(self, max_steps: int = 5_000_000, stop_at_line_change: bool = False, until=None,
            ignore_first_bp: bool = True) -> StopInfo:
        """Run until exit / breakpoint / input / *until*() / max_steps."""
        bps = self.breakpoints
        start_line = self.current_line() if stop_at_line_change else None
        first = True
        for _ in range(max_steps):
            lin = self.linear_ip()
            if bps and lin in bps and not (first and ignore_first_bp):
                return StopInfo("break")
            first = False
            info = self.step()
            if info is not None:
                return info
            if until is not None and until():
                return StopInfo("step")
            if stop_at_line_change:
                ln = self.program.addr_line.get(self.linear_ip()) if self.program else None
                if ln is not None and ln != start_line:
                    return StopInfo("step")
        return StopInfo("limit", _msg("R-LIMIT", self.lang, n=max_steps))

    # -- source-level stepping
    def _is_call_like(self) -> bool:
        lin = self.linear_ip()
        m = self.mem
        k = 0
        while m[lin + k] in (0x26, 0x2E, 0x36, 0x3E, 0xF0, 0xF2, 0xF3) and k < 4:
            k += 1
        op = m[lin + k]
        if op in (0xE8, 0x9A, 0xCD, 0xCC, 0xCE):
            return True
        if op == 0xFF and ((m[lin + k + 1] >> 3) & 7) in (2, 3):
            return True
        return False

    def step_into(self, limit: int = 2_000_000) -> StopInfo:
        """One source line (into calls). Code without a source line (ROM, interrupt handlers) is run through."""
        info = self.step()
        if info is not None:
            return info
        return self._run_to_source(limit)

    def _run_to_source(self, limit: int) -> StopInfo:
        if self.program is None or self.program.addr_line.get(self.linear_ip()) is not None:
            return StopInfo("step")
        return self.run(limit, until=lambda: self.linear_ip() in self.program.addr_line, ignore_first_bp=False)

    def step_over(self, limit: int = 5_000_000) -> StopInfo:
        """One source line; CALL / INT / far calls run until they return."""
        if not self._is_call_like():
            return self.step_into(limit)
        c = self.cpu
        sp0, ss0, cs0 = c.r[SP], c.s[SS], c.s[CS]
        info = self.step()
        if info is not None:
            return info
        dec = (sp0 - c.r[SP]) & 0xFFFF
        if dec not in (2, 4, 6):                   # INTO not taken, or the call changed the stack oddly
            return self._run_to_source(limit)
        ret_ip = c.rw(c.s[SS], c.r[SP])
        ret_cs = cs0 if dec == 2 else c.rw(c.s[SS], c.r[SP] + 2)
        self.return_target = (((ret_cs << 4) + ret_ip) & 0xFFFFF, ss0, sp0)
        return self.run_until_return(limit)

    def run_until_return(self, limit: int = 5_000_000) -> StopInfo:
        """Continue a step over (also after the program waited for a key inside the call)."""
        target, ss0, sp0 = self.return_target
        c = self.cpu

        def back():
            return self.linear_ip() == target and c.s[SS] == ss0 and c.r[SP] >= sp0
        info = self.run(limit, until=back, ignore_first_bp=True)
        if info.reason == "step":
            self.return_target = None
            return self._run_to_source(limit)
        return info

    def step_out(self, limit: int = 5_000_000) -> StopInfo:
        c = self.cpu
        sp0 = c.r[SP]

        def returned():
            op = self.mem[(((c.op_cs << 4) + c.op_ip)) & 0xFFFFF]
            return op in (0xC3, 0xC2, 0xCB, 0xCA, 0xCF) and c.r[SP] > sp0
        info = self.run(limit, until=returned)
        if info.reason == "step":
            return self._run_to_source(limit)
        return info

    def set_breakpoint_lines(self, lines) -> None:
        """lines: iterable of (file, line) -> breakpoints at the first address of each line."""
        self.breakpoints = set()
        if self.program is None:
            return
        for f, ln in lines:
            addrs = self.program.addresses_of(f, ln)
            if addrs:
                self.breakpoints.add(min(addrs))

    # ================================================================== views
    def registers(self) -> dict:
        c = self.cpu
        d = {n: c.r[i] for i, n in enumerate(("AX", "CX", "DX", "BX", "SP", "BP", "SI", "DI"))}
        d.update({n: c.s[i] for i, n in enumerate(("ES", "CS", "SS", "DS"))})
        d["IP"] = c.ip
        d["FLAGS"] = c.flags
        return d

    def read_var(self, var) -> list:
        """Elements of a VarInfo (at most 64)."""
        out = []
        for k in range(min(var.count, 64)):
            a = var.linear + k * var.size
            out.append(int.from_bytes(self.mem[a:a + var.size], "little"))
        return out

    def stack_words(self, n: int = 16) -> list:
        c = self.cpu
        return [(c.r[SP] + 2 * k) & 0xFFFF for k in range(n)], \
            [c.rw(c.s[SS], c.r[SP] + 2 * k) for k in range(n)]


def run_source(text: str, keys: str = "", max_steps: int = 2_000_000, filename: str = "main.asm") -> dict:
    """Assemble and run *text* headless. Returns {ok, errors, output, screen, exit_code, reason, machine}."""
    from .assembler import assemble
    prog = assemble(text, filename)
    if not prog.ok:
        return {"ok": False, "errors": [str(e) for e in prog.errors], "output": "", "screen": "",
                "exit_code": None, "reason": "asm", "machine": None, "program": prog}
    m = Machine()
    m.clock_base = time.struct_time((2026, 1, 1, 12, 0, 0, 3, 1, 0))
    m.load(prog)
    m.record_history = False
    m.feed_keys(keys)
    info = m.run(max_steps)
    return {"ok": info.reason == "exit", "errors": [], "output": m.output, "screen": m.screen_text(),
            "exit_code": m.exit_code if m.exited else None, "reason": info.reason, "message": info.message,
            "machine": m, "program": prog}
