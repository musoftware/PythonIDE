"""A small 6502 + Atari 2600 bus simulator for the lesson checker of the retro-games course (original code).

It runs a cartridge image built by DASM long enough to check what a lesson promises:

* scanlines per frame (counted between two VSYNC starts; WSYNC ends a 76-cycle line),
* the RAM ($80-$FF) after N frames, the last value written to each TIA register,
* the joystick / fire button can be held (SWCHA / INPT4) to test game logic.

Only the documented 6502 instructions are executed (decimal mode included); the opcode table comes from
radide.retro.cpu.m6502.  The TIA is not drawn - only its registers are recorded.  RIOT timers are modelled
(TIM1T / TIM8T / TIM64T / T1024T, INTIM, TIMINT).  Cycle counts are the documented ones (page-cross and
taken-branch penalties included), which is all a 2600 kernel's timing depends on.
"""
from __future__ import annotations

from radide.retro.cpu.m6502 import OPCODES

TIA_NAMES = {0x00: "VSYNC", 0x01: "VBLANK", 0x02: "WSYNC", 0x06: "COLUP0", 0x07: "COLUP1", 0x08: "COLUPF",
             0x09: "COLUBK", 0x0A: "CTRLPF", 0x0D: "PF0", 0x0E: "PF1", 0x0F: "PF2", 0x10: "RESP0",
             0x11: "RESP1", 0x1B: "GRP0", 0x1C: "GRP1", 0x20: "HMP0", 0x21: "HMP1", 0x2A: "HMOVE",
             0x2B: "HMCLR", 0x04: "NUSIZ0", 0x05: "NUSIZ1", 0x15: "AUDC0", 0x17: "AUDF0", 0x19: "AUDV0"}


class Halt(Exception):
    pass


class Atari2600:
    def __init__(self, rom: bytes):
        if len(rom) not in (2048, 4096):
            raise ValueError(f"only 2K / 4K cartridges are simulated (this one is {len(rom)} bytes)")
        self.rom = rom
        self.ram = bytearray(128)
        self.tia: dict[str, int] = {}
        self.tia_writes: dict[str, int] = {}
        self.swcha = 0xFF                 # joysticks: all directions released
        self.inpt4 = 0x80                 # fire button released
        self.cycles = 0
        self.a = self.x = self.y = 0
        self.sp = 0xFD
        self.p = 0x24
        self.timer = 0xFF
        self.timer_shift = 10
        self.timer_sub = 0
        self.timer_expired = False
        self.vsync_on = False
        self.frame_starts: list[int] = []
        self.pc = self.read(0xFFFC) | (self.read(0xFFFD) << 8)

    # ------------------------------------------------------------------ bus
    def _tick_timer(self, n: int) -> None:
        if self.timer_expired:
            self.timer = (self.timer - n) & 0xFF
            return
        self.timer_sub += n
        step = 1 << self.timer_shift
        while self.timer_sub >= step:
            self.timer_sub -= step
            if self.timer == 0:
                self.timer_expired = True
                self.timer = 0xFF
                rest, self.timer_sub = self.timer_sub, 0
                self.timer = (self.timer - rest) & 0xFF
                return
            self.timer -= 1

    def read(self, addr: int) -> int:
        addr &= 0x1FFF
        if addr & 0x1000:
            return self.rom[addr & (len(self.rom) - 1)]
        if not addr & 0x80:                              # TIA reads
            r = addr & 0x0F
            if r == 0x0C:
                return self.inpt4
            return 0x80 if r == 0x0D else 0
        if not addr & 0x200:
            return self.ram[addr & 0x7F]
        r = addr & 0x07                                  # RIOT
        if r == 0:
            return self.swcha
        if r in (4, 6):
            return self.timer
        if r in (5, 7):
            return 0x80 if self.timer_expired else 0
        return 0xFF if r == 2 else 0

    def write(self, addr: int, v: int) -> None:
        addr &= 0x1FFF
        if addr & 0x1000:
            return
        if not addr & 0x80:
            r = addr & 0x3F
            name = TIA_NAMES.get(r, f"TIA${r:02X}")
            self.tia[name] = v
            self.tia_writes[name] = self.tia_writes.get(name, 0) + 1
            if r == 0x02:                                # WSYNC: wait for the end of the line
                rest = (76 - self.cycles % 76) % 76
                self.cycles += rest
                self._tick_timer(rest)
            elif r == 0x00:
                on = bool(v & 2)
                if on and not self.vsync_on:
                    self.frame_starts.append(self.cycles)
                self.vsync_on = on
            return
        if not addr & 0x200:
            self.ram[addr & 0x7F] = v
            return
        r = addr & 0x1F
        if r in (0x14, 0x15, 0x16, 0x17):
            self.timer = v
            self.timer_shift = {0x14: 0, 0x15: 3, 0x16: 6, 0x17: 10}[r]
            self.timer_sub = 0
            self.timer_expired = False

    # ------------------------------------------------------------------ CPU helpers
    def _flag(self, bit: int, on) -> None:
        self.p = (self.p | bit) if on else (self.p & ~bit & 0xFF)

    def _nz(self, v: int) -> int:
        v &= 0xFF
        self._flag(0x80, v & 0x80)
        self._flag(0x02, v == 0)
        return v

    def _push(self, v: int) -> None:
        self.write(0x100 | self.sp, v)
        self.sp = (self.sp - 1) & 0xFF

    def _pull(self) -> int:
        self.sp = (self.sp + 1) & 0xFF
        return self.read(0x100 | self.sp)

    def _addr(self, mode: str):
        pc = self.pc
        lo = self.read(pc + 1)
        hi = self.read(pc + 2)
        cross = False
        if mode == "zp":
            return lo, False
        if mode == "zpx":
            return (lo + self.x) & 0xFF, False
        if mode == "zpy":
            return (lo + self.y) & 0xFF, False
        if mode == "abs":
            return lo | hi << 8, False
        if mode in ("absx", "absy"):
            base = lo | hi << 8
            a = (base + (self.x if mode == "absx" else self.y)) & 0xFFFF
            return a, (a & 0xFF00) != (base & 0xFF00)
        if mode == "indx":
            z = (lo + self.x) & 0xFF
            return self.read(z) | self.read((z + 1) & 0xFF) << 8, False
        if mode == "indy":
            base = self.read(lo) | self.read((lo + 1) & 0xFF) << 8
            a = (base + self.y) & 0xFFFF
            return a, (a & 0xFF00) != (base & 0xFF00)
        if mode == "ind":
            ptr = lo | hi << 8
            return self.read(ptr) | self.read((ptr & 0xFF00) | ((ptr + 1) & 0xFF)) << 8, cross
        raise ValueError(mode)

    def _adc(self, v: int) -> None:
        c = self.p & 1
        if self.p & 0x08:                                # decimal mode
            lo = (self.a & 0x0F) + (v & 0x0F) + c
            hi = (self.a >> 4) + (v >> 4)
            if lo > 9:
                lo += 6
                hi += 1
            self._flag(0x40, (~(self.a ^ v) & (self.a ^ (hi << 4)) & 0x80))
            if hi > 9:
                hi += 6
            self._flag(0x01, hi > 15)
            self.a = self._nz(((hi << 4) | (lo & 0x0F)) & 0xFF)
            return
        r = self.a + v + c
        self._flag(0x40, (~(self.a ^ v) & (self.a ^ r) & 0x80))
        self._flag(0x01, r > 0xFF)
        self.a = self._nz(r)

    def _sbc(self, v: int) -> None:
        if self.p & 0x08:
            c = self.p & 1
            lo = (self.a & 0x0F) - (v & 0x0F) - (1 - c)
            hi = (self.a >> 4) - (v >> 4)
            if lo < 0:
                lo += 10
                hi -= 1
            r = self.a - v - (1 - c)
            self._flag(0x40, ((self.a ^ v) & (self.a ^ r) & 0x80))
            if hi < 0:
                hi += 10
            self._flag(0x01, r >= 0)
            self.a = self._nz(((hi << 4) | (lo & 0x0F)) & 0xFF)
            return
        self._adc(v ^ 0xFF)

    def _cmp(self, reg: int, v: int) -> None:
        r = reg - v
        self._flag(0x01, r >= 0)
        self._nz(r)

    # ------------------------------------------------------------------ one instruction
    def step(self) -> None:
        opc = self.read(self.pc)
        op = OPCODES[opc]
        if op.undocumented:
            raise Halt(f"undocumented opcode ${opc:02X} at ${self.pc:04X}")
        m, mode = op.mnemonic, op.mode
        size = {"imp": 1, "acc": 1, "imm": 2, "zp": 2, "zpx": 2, "zpy": 2, "indx": 2, "indy": 2, "rel": 2}.get(mode, 3)
        cyc = int(op.cycles[0]) if op.cycles[0].isdigit() else 2
        nxt = (self.pc + size) & 0xFFFF
        if mode == "rel":
            off = self.read(self.pc + 1)
            target = (nxt + (off - 256 if off >= 128 else off)) & 0xFFFF
            cond = {"bpl": not self.p & 0x80, "bmi": bool(self.p & 0x80), "bvc": not self.p & 0x40,
                    "bvs": bool(self.p & 0x40), "bcc": not self.p & 1, "bcs": bool(self.p & 1),
                    "bne": not self.p & 2, "beq": bool(self.p & 2)}[m]
            if cond:
                cyc += 1 + ((target & 0xFF00) != (nxt & 0xFF00))
                nxt = target
            self.pc = nxt
            self._spend(cyc)
            return
        addr = None
        val = None
        if mode == "imm":
            val = self.read(self.pc + 1)
        elif mode not in ("imp", "acc"):
            addr, cross = self._addr(mode)
            if cross and op.cycles.endswith("+"):
                cyc += 1
        self.pc = nxt

        def rd():
            return val if val is not None else self.read(addr)

        if m == "lda":
            self.a = self._nz(rd())
        elif m == "ldx":
            self.x = self._nz(rd())
        elif m == "ldy":
            self.y = self._nz(rd())
        elif m == "sta":
            self.write(addr, self.a)
        elif m == "stx":
            self.write(addr, self.x)
        elif m == "sty":
            self.write(addr, self.y)
        elif m == "adc":
            self._adc(rd())
        elif m == "sbc":
            self._sbc(rd())
        elif m == "and":
            self.a = self._nz(self.a & rd())
        elif m == "ora":
            self.a = self._nz(self.a | rd())
        elif m == "eor":
            self.a = self._nz(self.a ^ rd())
        elif m == "cmp":
            self._cmp(self.a, rd())
        elif m == "cpx":
            self._cmp(self.x, rd())
        elif m == "cpy":
            self._cmp(self.y, rd())
        elif m == "bit":
            v = rd()
            self._flag(0x80, v & 0x80)
            self._flag(0x40, v & 0x40)
            self._flag(0x02, (self.a & v) == 0)
        elif m in ("asl", "lsr", "rol", "ror"):
            v = self.a if mode == "acc" else self.read(addr)
            c = self.p & 1
            if m == "asl":
                self._flag(1, v & 0x80)
                v = v << 1
            elif m == "lsr":
                self._flag(1, v & 1)
                v = v >> 1
            elif m == "rol":
                self._flag(1, v & 0x80)
                v = (v << 1) | c
            else:
                self._flag(1, v & 1)
                v = (v >> 1) | (c << 7)
            v = self._nz(v)
            if mode == "acc":
                self.a = v
            else:
                self.write(addr, v)
        elif m in ("inc", "dec"):
            v = self._nz(self.read(addr) + (1 if m == "inc" else -1))
            self.write(addr, v)
        elif m in ("inx", "dex"):
            self.x = self._nz(self.x + (1 if m == "inx" else -1))
        elif m in ("iny", "dey"):
            self.y = self._nz(self.y + (1 if m == "iny" else -1))
        elif m == "tax":
            self.x = self._nz(self.a)
        elif m == "tay":
            self.y = self._nz(self.a)
        elif m == "txa":
            self.a = self._nz(self.x)
        elif m == "tya":
            self.a = self._nz(self.y)
        elif m == "tsx":
            self.x = self._nz(self.sp)
        elif m == "txs":
            self.sp = self.x
        elif m == "pha":
            self._push(self.a)
        elif m == "php":
            self._push(self.p | 0x30)
        elif m == "pla":
            self.a = self._nz(self._pull())
        elif m == "plp":
            self.p = (self._pull() & 0xEF) | 0x20
        elif m == "jmp":
            self.pc = addr
        elif m == "jsr":
            ret = (self.pc - 1) & 0xFFFF
            self._push(ret >> 8)
            self._push(ret & 0xFF)
            self.pc = addr
        elif m == "rts":
            lo = self._pull()
            self.pc = ((self._pull() << 8) | lo) + 1 & 0xFFFF
        elif m == "rti":
            self.p = (self._pull() & 0xEF) | 0x20
            lo = self._pull()
            self.pc = (self._pull() << 8) | lo
        elif m in ("clc", "sec"):
            self._flag(1, m == "sec")
        elif m in ("cld", "sed"):
            self._flag(8, m == "sed")
        elif m in ("cli", "sei"):
            self._flag(4, m == "sei")
        elif m == "clv":
            self._flag(0x40, False)
        elif m == "nop":
            pass
        elif m == "brk":
            raise Halt(f"BRK at ${(self.pc - 1) & 0xFFFF:04X}")
        else:
            raise Halt(f"instruction {m} not simulated")
        self._spend(cyc)

    def _spend(self, cyc: int) -> None:
        self.cycles += cyc
        self._tick_timer(cyc)

    # ------------------------------------------------------------------ runs
    def run_frames(self, frames: int, limit_cycles: int = 3_000_000) -> None:
        """Run until *frames* complete frames have started after the first VSYNC (or the cycle limit)."""
        while len(self.frame_starts) < frames + 1 and self.cycles < limit_cycles:
            self.step()

    def scanlines(self) -> list[int]:
        s = self.frame_starts
        return [round((b - a) / 76) for a, b in zip(s, s[1:])]

    def ram_at(self, addr: int) -> int:
        return self.ram[addr & 0x7F]


__all__ = ["Atari2600", "Halt"]
