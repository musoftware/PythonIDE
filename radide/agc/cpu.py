"""An original Apollo Guidance Computer (Block II) CPU emulator for RAD IDE.

Written for teaching and debugging small AGC programs inside the IDE (registers A / L / Q / Z, the banks, the
I/O channels, the timers TIME1-TIME5 with their interrupts, KEYRUPT for the DSKY). It is not cycle-exact and
does not model the IMU, the radars, parity, the night watchman or the flight-program specific hardware; big
flight programs run in yaAGC from Virtual AGC instead (radide/agc/yaagc.py).

Words are 15-bit ones' complement (bit 15 = sign). A and Q are 16 bits wide: bit 16 is the true sign and an
overflow shows as bit 16 != bit 15.

    cpu = AgcCpu(prog.rope)
    cpu.on_channel = lambda ch, value: ...      # output channel writes (DSKY, lamps)
    cpu.step()  /  cpu.run_mct(n)               # one instruction / about n memory cycles (11.7 us each)
    cpu.press_key(code)                         # DSKY key: channel 15 + KEYRUPT1
"""
from __future__ import annotations

from .isa import INTERRUPTS

MCT_SECONDS = 11.71875e-6             # one memory cycle time
MCT_PER_CS = 853                      # memory cycles per centisecond (timer tick)

A, L, Q, EB, FB, Z, BB, ZERO = range(8)
ARUPT, LRUPT, QRUPT, ZRUPT, BBRUPT, BRUPT = 0o10, 0o11, 0o12, 0o15, 0o16, 0o17
CYR, SR, CYL, EDOP = 0o20, 0o21, 0o22, 0o23
TIME2, TIME1, TIME3, TIME4, TIME5, TIME6 = 0o24, 0o25, 0o26, 0o27, 0o30, 0o31

INT_T6, INT_T5, INT_T3, INT_T4, INT_KEY1, INT_KEY2, INT_UP, INT_DOWN, INT_RADAR, INT_HAND = range(1, 11)


# ---------------------------------------------------------------------------- word arithmetic
def sx(w: int) -> int:
    """15-bit word -> 16-bit (copy the sign into bit 16)."""
    w &= 0o77777
    return w | ((w & 0o40000) << 1)


def ovc(a: int) -> int:
    """16-bit -> 15-bit, overflow corrected (the sign comes from bit 16)."""
    return (a & 0o37777) | ((a >> 1) & 0o40000)


def overflow(a: int) -> int:
    """+1 positive overflow, -1 negative overflow, 0 none (16-bit value)."""
    s1, s2 = (a >> 15) & 1, (a >> 14) & 1
    if s1 == s2:
        return 0
    return 1 if s1 == 0 else -1


def add16(a: int, b: int) -> int:
    s = (a & 0xFFFF) + (b & 0xFFFF)
    if s > 0xFFFF:
        s = (s + 1) & 0xFFFF
    return s


def add15(a: int, b: int) -> int:
    s = (a & 0o77777) + (b & 0o77777)
    if s > 0o77777:
        s = (s + 1) & 0o77777
    return s


def to_int(w: int) -> int:
    """15-bit ones' complement word -> Python int (-0 -> 0)."""
    w &= 0o77777
    return -((~w) & 0o77777) if w & 0o40000 else w


def to_int16(a: int) -> int:
    a &= 0xFFFF
    return -((~a) & 0xFFFF) if a & 0x8000 else a


def from_int(v: int) -> int:
    """Python int (|v| <= 16383) -> 15-bit word."""
    if v >= 0:
        return v & 0o37777
    return (~(-v)) & 0o77777


def is_neg(w: int) -> bool:
    return bool(w & 0o40000)


class AgcCpu:
    def __init__(self, rope=None):
        self.rope = rope if rope is not None else [[0] * 0o2000 for _ in range(36)]
        self.on_channel = None                 # callable(channel, value) after an output-channel write
        self.reset()

    # ------------------------------------------------------------------ state
    def reset(self) -> None:
        self.erasable = [[0] * 0o400 for _ in range(8)]
        self.channels = {0o30: 0o77777, 0o31: 0o77777, 0o32: 0o77777, 0o33: 0o77777}
        self.erasable[0][Z] = 0o4000
        self.extend = False                    # next instruction is an extracode
        self.index = 0                         # INDEX value added to the next instruction
        self.index_pending = False
        self.inhibit = True                    # GOJAM leaves interrupts inhibited
        self.in_rupt = False
        self.pending: set[int] = set()
        self.pending_word: int | None = None   # RESUME: the next instruction word (BRUPT)
        self.mct = 0                           # memory cycles executed
        self._tick = 0
        self.instructions = 0
        self.halted = False
        self.last_z = 0o4000
        self.last_word = 0

    # registers
    @property
    def Z(self) -> int:
        return self.erasable[0][Z] & 0o7777

    @Z.setter
    def Z(self, v: int) -> None:
        self.erasable[0][Z] = v & 0o7777

    def reg(self, n: int) -> int:
        return self.erasable[0][n]

    def ebank(self) -> int:
        return (self.erasable[0][EB] >> 8) & 7

    def fbank(self) -> int:
        b = (self.erasable[0][FB] >> 10) & 0o37
        if b >= 0o30 and self.channels.get(7, 0) & 0o100:
            b += 0o10
        return b

    def location(self, addr: int | None = None) -> tuple[str, int, int]:
        """("E" | "F", bank, offset) of a 12-bit address (default: Z) with the current banks."""
        a = self.Z if addr is None else addr & 0o7777
        if a < 0o1400:
            return ("E", a // 0o400, a % 0o400)
        if a < 0o2000:
            return ("E", self.ebank(), a - 0o1400)
        if a < 0o4000:
            return ("F", self.fbank(), a - 0o2000)
        if a < 0o6000:
            return ("F", 2, a - 0o4000)
        return ("F", 3, a - 0o6000)

    # ------------------------------------------------------------------ memory
    def read(self, addr: int) -> int:
        """15-bit (A, Q: 16-bit) contents of a 12-bit address."""
        a = addr & 0o7777
        if a < 0o10:
            if a == ZERO:
                return 0
            return self.erasable[0][a] & (0xFFFF if a in (A, Q) else 0o77777)
        kind, bank, off = self.location(a)
        if kind == "E":
            return self.erasable[bank][off] & 0o77777
        if bank >= len(self.rope):
            return 0
        return self.rope[bank][off] & 0o77777

    def read16(self, addr: int) -> int:
        """Contents as a 16-bit value (A and Q as they are, other words sign-extended)."""
        a = addr & 0o7777
        v = self.read(a)
        return v if a in (A, Q) else sx(v)

    def write(self, addr: int, value: int) -> None:
        """Store a value (16-bit values are overflow-corrected except into A and Q)."""
        a = addr & 0o7777
        if a >= 0o2000:
            return                              # fixed memory is read-only
        if a in (A, Q):
            self.erasable[0][a] = value & 0xFFFF
            return
        v = ovc(value) if value > 0o77777 else value & 0o77777
        if a < 0o10:
            if a == ZERO:
                return
            if a == EB:
                self.erasable[0][EB] = v & 0o3400
                self.erasable[0][BB] = (self.erasable[0][FB] & 0o76000) | ((v >> 8) & 7)
            elif a == FB:
                self.erasable[0][FB] = v & 0o76000
                self.erasable[0][BB] = (v & 0o76000) | (self.erasable[0][BB] & 7)
            elif a == BB:
                self.erasable[0][BB] = v & 0o76007
                self.erasable[0][FB] = v & 0o76000
                self.erasable[0][EB] = (v & 7) << 8
            elif a == Z:
                self.erasable[0][Z] = v & 0o7777
            else:
                self.erasable[0][a] = v
            return
        if a == CYR:
            v = ((v >> 1) | ((v & 1) << 14)) & 0o77777
        elif a == SR:
            v = (v >> 1) | (v & 0o40000)
        elif a == CYL:
            v = ((v << 1) | (v >> 14)) & 0o77777
        elif a == EDOP:
            v = (v >> 7) & 0o177
        kind, bank, off = self.location(a)
        self.erasable[bank][off] = v

    def fetch_word(self, addr: int) -> int:
        return self.read(addr) & 0o77777

    # ------------------------------------------------------------------ channels
    def read_channel(self, ch: int) -> int:
        if ch == 1:
            return self.erasable[0][L] & 0o77777
        if ch == 2:
            return self.erasable[0][Q] & 0xFFFF
        return self.channels.get(ch, 0) & 0o77777

    def write_channel(self, ch: int, value: int) -> None:
        if ch == 1:
            self.write(L, value)
            return
        if ch == 2:
            self.erasable[0][Q] = value & 0xFFFF
            return
        v = ovc(value) if value > 0o77777 else value & 0o77777
        self.channels[ch] = v
        if self.on_channel is not None:
            try:
                self.on_channel(ch, v)
            except Exception:  # noqa: BLE001 - a display must never stop the CPU
                pass

    def press_key(self, code: int) -> None:
        """A main-DSKY key: channel 15 = code, KEYRUPT1."""
        self.channels[0o15] = code & 0o37
        self.pending.add(INT_KEY1)

    def set_pro(self, pressed: bool) -> None:
        """The PRO key is channel 32 bit 14 (0 while pressed)."""
        v = self.channels.get(0o32, 0o77777)
        self.channels[0o32] = (v & ~0o20000) if pressed else (v | 0o20000)

    # ------------------------------------------------------------------ execution
    def run_mct(self, n: int, stop=None) -> str | None:
        """Run about *n* memory cycles. *stop()* is checked before each instruction (breakpoints);
        returns "stop" when it fired, None otherwise."""
        end = self.mct + n
        while self.mct < end:
            if stop is not None and stop():
                return "stop"
            self.step()
        return None

    def step(self) -> None:
        """One instruction (plus a pending interrupt afterwards)."""
        self.last_z = self.Z
        if self.pending_word is not None:
            word = self.pending_word
            self.pending_word = None
        else:
            word = self.fetch_word(self.Z)
        self.Z = self.Z + 1
        if self.index_pending:
            word = add15(word, self.index)
            self.index_pending = False
        self.last_word = word
        cycles = self._execute(word)
        self.instructions += 1
        self._advance(cycles)
        self._service_interrupts()

    def _advance(self, cycles: int) -> None:
        self.mct += cycles
        self._tick += cycles
        while self._tick >= MCT_PER_CS:
            self._tick -= MCT_PER_CS
            self._centisecond()

    def _counter_inc(self, reg: int, rupt: int | None) -> None:
        v = (self.erasable[0][reg] + 1) & 0o77777
        if v == 0o40000:                       # overflow out of 14 bits
            v = 0
            if rupt is not None:
                self.pending.add(rupt)
            elif reg == TIME1:
                self.erasable[0][TIME2] = (self.erasable[0][TIME2] + 1) & 0o37777
        self.erasable[0][reg] = v

    def _centisecond(self) -> None:
        self._counter_inc(TIME1, None)
        self._counter_inc(TIME3, INT_T3)
        self._counter_inc(TIME4, INT_T4)
        self._counter_inc(TIME5, INT_T5)

    def _service_interrupts(self) -> None:
        if not self.pending or self.inhibit or self.in_rupt or self.extend or self.index_pending:
            return
        if self.pending_word is not None or overflow(self.erasable[0][A]):
            return
        n = min(self.pending)
        self.pending.discard(n)
        self.erasable[0][ZRUPT] = self.Z
        self.erasable[0][BRUPT] = self.fetch_word(self.Z)
        self.Z = INTERRUPTS[n][1]
        self.in_rupt = True
        self._advance(3)

    # ------------------------------------------------------------------ instructions
    def _execute(self, word: int) -> int:
        ext = self.extend
        self.extend = False
        op = (word >> 12) & 7
        qc = (word >> 10) & 3
        k12 = word & 0o7777
        k10 = word & 0o1777
        r = self.erasable[0]
        if not ext:
            if op == 0:
                if k12 == 3:                   # RELINT
                    self.inhibit = False
                    return 1
                if k12 == 4:                   # INHINT
                    self.inhibit = True
                    return 1
                if k12 == 6:                   # EXTEND
                    self.extend = True
                    return 1
                if k12 < 3:                    # TC A / L / Q run the register as the next instruction; the
                    self.pending_word = self.read(k12) & 0o77777   # word is read before Q changes, so
                r[Q] = self.Z                  # RETURN (TC Q) runs "TC <return address>"
                self.Z = k12                   # TC K
                return 1
            if op == 1:
                if qc == 0:                    # CCS K
                    v = self.read(k10)
                    if k10 in (A, Q):
                        v = ovc(v)
                    self.write(k10, v if k10 not in (A, Q) else self.read(k10))
                    if v == 0:
                        r[A] = 0
                        self.Z += 1
                    elif v == 0o77777:
                        r[A] = 0
                        self.Z += 3
                    elif v & 0o40000:
                        r[A] = ((~v) & 0o37777) - 1
                        self.Z += 2
                    else:
                        r[A] = v - 1
                    return 2
                self.Z = k12                   # TCF K
                return 1
            if op == 2:
                if qc == 0:                    # DAS K (encoded K+1)
                    self._das(k10 - 1)
                    return 3
                if qc == 1:                    # LXCH K
                    t = self.read(k10)
                    self.write(k10, r[L])
                    r[L] = ovc(t) if k10 in (A, Q) else t
                    return 2
                if qc == 2:                    # INCR K
                    self._incr(k10, 1)
                    return 2
                v = add16(r[A], self.read16(k10))   # ADS K
                r[A] = v
                self.write(k10, v)
                return 2
            if op == 3:                        # CA K
                r[A] = self.read16(k12)
                return 2
            if op == 4:                        # CS K
                r[A] = (~self.read16(k12)) & 0xFFFF
                return 2
            if op == 5:
                if qc == 0:
                    if k10 == 0o17:            # RESUME
                        self.Z = r[ZRUPT]
                        self.pending_word = r[BRUPT] & 0o77777
                        self.in_rupt = False
                        return 2
                    self.index = self.read(k10) & 0o77777 if k10 not in (A, Q) else ovc(self.read(k10))
                    self.index_pending = True  # INDEX K
                    return 2
                if qc == 1:                    # DXCH K (encoded K+1)
                    self._dxch(k10 - 1)
                    return 3
                if qc == 2:                    # TS K
                    a = r[A]
                    o = overflow(a)
                    if k10 == A:
                        if o:
                            r[A] = 1 if o > 0 else 0xFFFE
                            self.Z += 1
                        return 2
                    if o:
                        self.write(k10, ovc(a))
                        r[A] = 1 if o > 0 else 0xFFFE
                        if k10 != Z:
                            self.Z += 1
                    else:
                        self.write(k10, a if k10 == Q else ovc(a))
                    return 2
                t = self.read16(k10)           # XCH K
                self.write(k10, r[A])
                r[A] = t
                return 2
            if op == 6:                        # AD K
                r[A] = add16(r[A], self.read16(k12))
                return 2
            r[A] = r[A] & self.read16(k12)     # MASK K
            return 2
        # ------------------------------------------------------- extracodes
        if op == 0:
            pc = (word >> 9) & 7
            ch = word & 0o777
            if pc == 0:                        # READ
                r[A] = sx(self.read_channel(ch)) if ch != 2 else self.read_channel(ch)
            elif pc == 1:                      # WRITE
                self.write_channel(ch, r[A])
            elif pc == 2:                      # RAND
                r[A] = r[A] & sx(self.read_channel(ch))
            elif pc == 3:                      # WAND
                r[A] = r[A] & sx(self.read_channel(ch))
                self.write_channel(ch, r[A])
            elif pc == 4:                      # ROR
                r[A] = r[A] | sx(self.read_channel(ch))
            elif pc == 5:                      # WOR
                r[A] = r[A] | sx(self.read_channel(ch))
                self.write_channel(ch, r[A])
            elif pc == 6:                      # RXOR
                r[A] = (r[A] ^ sx(self.read_channel(ch))) & 0xFFFF
            else:                              # EDRUPT
                self.erasable[0][ZRUPT] = self.Z
                self.Z = 0
                self.in_rupt = True
            return 2
        if op == 1:
            if qc == 0:                        # DV K
                self._dv(k10)
                return 6
            if r[A] in (0, 0xFFFF):            # BZF K
                self.Z = k12
            return 1
        if op == 2:
            if qc == 0:                        # MSU K
                k = self.read(k10) & 0o77777
                a = ovc(r[A])
                diff = (k - a) & 0o77777       # two's complement difference
                if diff & 0o40000:
                    diff = (diff - 1) & 0o77777    # -> ones' complement
                r[A] = sx(diff)
                return 2
            if qc == 1:                        # QXCH K
                t = self.read16(k10) if k10 not in (A, Q) else self.read(k10)
                self.write(k10, r[Q])
                r[Q] = t
                return 2
            if qc == 2:                        # AUG K
                v = self.read16(k10)
                self.write(k10, add16(v, 0xFFFE if v & 0x8000 else 1))
                return 2
            v = self.read16(k10)               # DIM K
            if v not in (0, 0xFFFF):
                self.write(k10, add16(v, 1 if v & 0x8000 else 0xFFFE))
            return 2
        if op == 3:                            # DCA K (encoded K+1)
            k = (k12 - 1) & 0o7777
            r[L] = ovc(self.read(k + 1)) if (k + 1) in (A, Q) else self.read(k + 1)
            r[A] = self.read16(k)
            return 3
        if op == 4:                            # DCS K (encoded K+1)
            k = (k12 - 1) & 0o7777
            lo = ovc(self.read(k + 1)) if (k + 1) in (A, Q) else self.read(k + 1)
            r[L] = (~lo) & 0o77777
            r[A] = (~self.read16(k)) & 0xFFFF
            return 3
        if op == 5:                            # INDEX K (extended: 12-bit address, keeps EXTEND)
            self.index = self.read(k12) & 0o77777 if k12 not in (A, Q) else ovc(self.read(k12))
            self.index_pending = True
            self.extend = True
            return 2
        if op == 6:
            if qc == 0:                        # SU K
                r[A] = add16(r[A], (~self.read16(k10)) & 0xFFFF)
                return 2
            a = r[A]                           # BZMF K
            if a in (0, 0xFFFF) or a & 0x8000:
                self.Z = k12
            return 1
        self._mp(k12)                          # MP K
        return 3

    # ------------------------------------------------------------------ helpers
    def _incr(self, k: int, d: int) -> None:
        if k in (A, Q):
            self.erasable[0][k] = add16(self.erasable[0][k], d)
            return
        v = self.read(k)
        nv = add15(v, d)
        if v == 0o37777 and d == 1:            # counters: +max + 1 overflows to +0
            nv = 0
        self.write(k, nv)

    def _das(self, k: int) -> None:
        r = self.erasable[0]
        lo = to_int(r[L] & 0o77777) + to_int(self.read(k + 1))
        carry = 0
        if lo > 0o37777:
            lo -= 0o40000
            carry = 1
        elif lo < -0o37777:
            lo += 0o40000
            carry = -1
        hi = to_int16(r[A] if r[A] <= 0xFFFF else 0) + to_int(self.read(k)) + carry
        o = 0
        if hi > 0o37777:
            hi -= 0o40000
            o = 1
        elif hi < -0o37777:
            hi += 0o40000
            o = -1
        self.write(k + 1, from_int(lo))
        self.write(k, from_int(hi))
        r[A] = 1 if o > 0 else (0xFFFE if o < 0 else 0)
        r[L] = 0

    def _dxch(self, k: int) -> None:
        r = self.erasable[0]
        hi, lo = self.read16(k), self.read(k + 1)
        self.write(k, r[A])
        self.write(k + 1, r[L])
        r[A] = hi
        r[L] = ovc(lo) if (k + 1) in (A, Q) else lo & 0o77777

    def _mp(self, k: int) -> None:
        r = self.erasable[0]
        a = to_int(ovc(r[A]))
        b = to_int(self.read(k) if k not in (A, Q) else ovc(self.read(k)))
        p = a * b
        sign = -1 if p < 0 else 1
        m = abs(p)
        hi, lo = m >> 14, m & 0o37777
        if sign < 0:
            r[A] = sx(from_int(-hi)) if hi else 0xFFFF
            r[L] = from_int(-lo) if lo else 0o77777
        else:
            r[A] = hi
            r[L] = lo

    def _dv(self, k: int) -> None:
        r = self.erasable[0]
        a = to_int(ovc(r[A]))
        lo = to_int(r[L] & 0o77777)
        dividend = a * 0o40000 + lo
        d = to_int(self.read(k))
        if d == 0 or abs(a) >= abs(d):
            r[A] = sx(0o37777 if (dividend >= 0) == (d >= 0) else 0o40000)
            r[L] = from_int(abs(a)) if dividend >= 0 else from_int(-abs(a))
            return
        q = abs(dividend) // abs(d)
        rem = abs(dividend) - q * abs(d)
        if (dividend < 0) != (d < 0):
            q = -q
        if dividend < 0:
            rem = -rem
        r[A] = sx(from_int(max(-0o37777, min(0o37777, q))))
        r[L] = from_int(rem)

    # ------------------------------------------------------------------ inspection
    def registers(self) -> dict[str, int]:
        r = self.erasable[0]
        return {"A": r[A] & 0xFFFF, "L": r[L] & 0o77777, "Q": r[Q] & 0xFFFF, "Z": self.Z, "EB": r[EB],
                "FB": r[FB], "BB": r[BB], "ARUPT": r[ARUPT], "LRUPT": r[LRUPT], "QRUPT": r[QRUPT],
                "ZRUPT": r[ZRUPT], "BRUPT": r[BRUPT], "TIME1": r[TIME1], "TIME2": r[TIME2], "TIME3": r[TIME3],
                "TIME4": r[TIME4], "TIME5": r[TIME5]}

    def read_erasable(self, bank: int, off: int) -> int:
        return self.erasable[bank & 7][off & 0o377]


def octal(v: int, digits: int = 5) -> str:
    return f"{v:0{digits}o}"


def decimal(w: int) -> str:
    """A 15-bit word as a signed decimal (ones' complement; -0 shows as -0)."""
    w &= 0o77777
    if w == 0o77777:
        return "-0"
    return str(to_int(w))


__all__ = ["AgcCpu", "MCT_SECONDS", "MCT_PER_CS", "add15", "add16", "decimal", "from_int", "octal", "ovc", "sx",
           "to_int", "to_int16"]
