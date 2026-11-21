"""A small cycle-counting 6502 interpreter (official opcodes, binary arithmetic) and two probes built on it:

* :class:`Atari2600Probe` - runs a 4K 2600 ROM headless and records, per scan line, the TIA writes with the CPU
  cycle they land on (WSYNC halts the CPU to the next line like the real TIA). The designer uses it to check a
  generated kernel: lines per frame, the playfield / graphics values of each line and cycle budgets.
* :class:`NESProbe` - runs an NROM ``.nes`` image with a minimal PPU (VRAM / palette writes through $2006 /
  $2007, OAM DMA, NMI each "frame", controller 1) to check what a generated loader puts on screen.

Neither is an emulator for playing: no TIA video / audio output, no PPU rendering, no decimal mode.
"""
from __future__ import annotations

_RMW = {"ASL", "LSR", "ROL", "ROR", "INC", "DEC"}
_STORE = {"STA", "STX", "STY"}
OPS = {
    "ADC": {"imm": 0x69, "zp": 0x65, "zpx": 0x75, "abs": 0x6D, "abx": 0x7D, "aby": 0x79, "izx": 0x61, "izy": 0x71},
    "AND": {"imm": 0x29, "zp": 0x25, "zpx": 0x35, "abs": 0x2D, "abx": 0x3D, "aby": 0x39, "izx": 0x21, "izy": 0x31},
    "ASL": {"acc": 0x0A, "zp": 0x06, "zpx": 0x16, "abs": 0x0E, "abx": 0x1E},
    "BCC": {"rel": 0x90}, "BCS": {"rel": 0xB0}, "BEQ": {"rel": 0xF0}, "BMI": {"rel": 0x30},
    "BNE": {"rel": 0xD0}, "BPL": {"rel": 0x10}, "BVC": {"rel": 0x50}, "BVS": {"rel": 0x70},
    "BIT": {"zp": 0x24, "abs": 0x2C}, "BRK": {"imp": 0x00},
    "CLC": {"imp": 0x18}, "CLD": {"imp": 0xD8}, "CLI": {"imp": 0x58}, "CLV": {"imp": 0xB8},
    "CMP": {"imm": 0xC9, "zp": 0xC5, "zpx": 0xD5, "abs": 0xCD, "abx": 0xDD, "aby": 0xD9, "izx": 0xC1, "izy": 0xD1},
    "CPX": {"imm": 0xE0, "zp": 0xE4, "abs": 0xEC}, "CPY": {"imm": 0xC0, "zp": 0xC4, "abs": 0xCC},
    "DEC": {"zp": 0xC6, "zpx": 0xD6, "abs": 0xCE, "abx": 0xDE}, "DEX": {"imp": 0xCA}, "DEY": {"imp": 0x88},
    "EOR": {"imm": 0x49, "zp": 0x45, "zpx": 0x55, "abs": 0x4D, "abx": 0x5D, "aby": 0x59, "izx": 0x41, "izy": 0x51},
    "INC": {"zp": 0xE6, "zpx": 0xF6, "abs": 0xEE, "abx": 0xFE}, "INX": {"imp": 0xE8}, "INY": {"imp": 0xC8},
    "JMP": {"abs": 0x4C, "ind": 0x6C}, "JSR": {"abs": 0x20},
    "LDA": {"imm": 0xA9, "zp": 0xA5, "zpx": 0xB5, "abs": 0xAD, "abx": 0xBD, "aby": 0xB9, "izx": 0xA1, "izy": 0xB1},
    "LDX": {"imm": 0xA2, "zp": 0xA6, "zpy": 0xB6, "abs": 0xAE, "aby": 0xBE},
    "LDY": {"imm": 0xA0, "zp": 0xA4, "zpx": 0xB4, "abs": 0xAC, "abx": 0xBC},
    "LSR": {"acc": 0x4A, "zp": 0x46, "zpx": 0x56, "abs": 0x4E, "abx": 0x5E}, "NOP": {"imp": 0xEA},
    "ORA": {"imm": 0x09, "zp": 0x05, "zpx": 0x15, "abs": 0x0D, "abx": 0x1D, "aby": 0x19, "izx": 0x01, "izy": 0x11},
    "PHA": {"imp": 0x48}, "PHP": {"imp": 0x08}, "PLA": {"imp": 0x68}, "PLP": {"imp": 0x28},
    "ROL": {"acc": 0x2A, "zp": 0x26, "zpx": 0x36, "abs": 0x2E, "abx": 0x3E},
    "ROR": {"acc": 0x6A, "zp": 0x66, "zpx": 0x76, "abs": 0x6E, "abx": 0x7E},
    "RTI": {"imp": 0x40}, "RTS": {"imp": 0x60},
    "SBC": {"imm": 0xE9, "zp": 0xE5, "zpx": 0xF5, "abs": 0xED, "abx": 0xFD, "aby": 0xF9, "izx": 0xE1, "izy": 0xF1},
    "SEC": {"imp": 0x38}, "SED": {"imp": 0xF8}, "SEI": {"imp": 0x78},
    "STA": {"zp": 0x85, "zpx": 0x95, "abs": 0x8D, "abx": 0x9D, "aby": 0x99, "izx": 0x81, "izy": 0x91},
    "STX": {"zp": 0x86, "zpy": 0x96, "abs": 0x8E}, "STY": {"zp": 0x84, "zpx": 0x94, "abs": 0x8C},
    "TAX": {"imp": 0xAA}, "TAY": {"imp": 0xA8}, "TSX": {"imp": 0xBA}, "TXA": {"imp": 0x8A},
    "TXS": {"imp": 0x9A}, "TYA": {"imp": 0x98},
}
_BASE = {"imm": 2, "zp": 3, "zpx": 4, "zpy": 4, "abs": 4, "abx": 4, "aby": 4, "izx": 6, "izy": 5, "acc": 2,
         "imp": 2, "rel": 2, "ind": 5}
_SPECIAL = {"PHA": 3, "PHP": 3, "PLA": 4, "PLP": 4, "RTS": 6, "RTI": 6, "JSR": 6, "BRK": 7}


def _cycles(m: str, mode: str) -> int:
    if m in _SPECIAL:
        return _SPECIAL[m]
    if m == "JMP":
        return 3 if mode == "abs" else 5
    if m in _RMW and mode != "acc":
        return {"zp": 5, "zpx": 6, "abs": 6, "abx": 7}[mode]
    if m in _STORE:
        return {"abx": 5, "aby": 5, "izy": 6}.get(mode, _BASE[mode])
    return _BASE[mode]


TABLE: dict[int, tuple[str, str, int]] = {}
for _m, _modes in OPS.items():
    for _mode, _op in _modes.items():
        TABLE[_op] = (_m, _mode, _cycles(_m, _mode))


class CPUError(Exception):
    pass


class CPU6502:
    C, Z, I, D, B, U, V, N = 1, 2, 4, 8, 16, 32, 64, 128

    def __init__(self, read, write):
        self.read, self.write = read, write
        self.a = self.x = self.y = 0
        self.sp = 0xFD
        self.p = 0x24
        self.pc = 0
        self.cycles = 0
        self.end = 0                       # cycle count at which the current instruction ends

    def reset(self) -> None:
        self.pc = self.read(0xFFFC) | (self.read(0xFFFD) << 8)
        self.sp = 0xFD
        self.p = 0x24

    # -------------------------------------------------- helpers
    def _nz(self, v: int) -> int:
        v &= 0xFF
        self.p = (self.p & ~(self.Z | self.N)) | (self.Z if v == 0 else 0) | (v & 0x80)
        return v

    def _push(self, v: int) -> None:
        self.write(0x100 | self.sp, v & 0xFF)
        self.sp = (self.sp - 1) & 0xFF

    def _pull(self) -> int:
        self.sp = (self.sp + 1) & 0xFF
        return self.read(0x100 | self.sp)

    def _w16(self, a: int) -> int:
        return self.read(a & 0xFFFF) | (self.read((a + 1) & 0xFFFF) << 8)

    def irq_nmi(self, vector: int = 0xFFFA) -> None:
        self._push(self.pc >> 8)
        self._push(self.pc)
        self._push((self.p | self.U) & ~self.B)
        self.p |= self.I
        self.pc = self._w16(vector)
        self.cycles += 7

    # -------------------------------------------------- execution
    def step(self) -> int:
        op = self.read(self.pc)
        ent = TABLE.get(op)
        if ent is None:
            raise CPUError(f"illegal opcode ${op:02X} at ${self.pc:04X}")
        m, mode, cyc = ent
        pc = (self.pc + 1) & 0xFFFF
        addr = None
        extra = 0
        if mode == "imm":
            addr = pc
            pc += 1
        elif mode == "zp":
            addr = self.read(pc)
            pc += 1
        elif mode == "zpx":
            addr = (self.read(pc) + self.x) & 0xFF
            pc += 1
        elif mode == "zpy":
            addr = (self.read(pc) + self.y) & 0xFF
            pc += 1
        elif mode in ("abs", "abx", "aby"):
            base = self.read(pc) | (self.read(pc + 1) << 8)
            pc += 2
            idx = self.x if mode == "abx" else self.y if mode == "aby" else 0
            addr = (base + idx) & 0xFFFF
            if idx and (base & 0xFF00) != (addr & 0xFF00) and m not in _STORE and m not in _RMW:
                extra = 1
        elif mode == "izx":
            z = (self.read(pc) + self.x) & 0xFF
            pc += 1
            addr = self.read(z) | (self.read((z + 1) & 0xFF) << 8)
        elif mode == "izy":
            z = self.read(pc)
            pc += 1
            base = self.read(z) | (self.read((z + 1) & 0xFF) << 8)
            addr = (base + self.y) & 0xFFFF
            if (base & 0xFF00) != (addr & 0xFF00) and m not in _STORE:
                extra = 1
        elif mode == "ind":
            ptr = self.read(pc) | (self.read(pc + 1) << 8)
            pc += 2
            addr = self.read(ptr) | (self.read((ptr & 0xFF00) | ((ptr + 1) & 0xFF)) << 8)
        elif mode == "rel":
            off = self.read(pc)
            pc += 1
            addr = (pc + (off - 256 if off & 0x80 else off)) & 0xFFFF
        self.pc = pc & 0xFFFF
        self.end = self.cycles + cyc + extra
        cyc += extra + self._exec(m, mode, addr)
        self.cycles += cyc
        return cyc

    def _exec(self, m: str, mode: str, addr) -> int:          # noqa: C901 - one branch per instruction
        r = self.read
        if m == "LDA":
            self.a = self._nz(r(addr))
        elif m == "LDX":
            self.x = self._nz(r(addr))
        elif m == "LDY":
            self.y = self._nz(r(addr))
        elif m == "STA":
            self.write(addr, self.a)
        elif m == "STX":
            self.write(addr, self.x)
        elif m == "STY":
            self.write(addr, self.y)
        elif m in ("ADC", "SBC"):
            v = r(addr)
            if m == "SBC":
                v ^= 0xFF
            s = self.a + v + (self.p & 1)
            ov = (~(self.a ^ v) & (self.a ^ s) & 0x80)
            self.p = (self.p & ~(self.C | self.V)) | (self.C if s > 0xFF else 0) | (self.V if ov else 0)
            self.a = self._nz(s)
        elif m == "AND":
            self.a = self._nz(self.a & r(addr))
        elif m == "ORA":
            self.a = self._nz(self.a | r(addr))
        elif m == "EOR":
            self.a = self._nz(self.a ^ r(addr))
        elif m in ("CMP", "CPX", "CPY"):
            reg = {"CMP": self.a, "CPX": self.x, "CPY": self.y}[m]
            v = r(addr)
            self.p = (self.p & ~self.C) | (self.C if reg >= v else 0)
            self._nz(reg - v)
        elif m == "BIT":
            v = r(addr)
            self.p = (self.p & ~(self.Z | self.V | self.N)) | (v & 0xC0) | (0 if self.a & v else self.Z)
        elif m in _RMW:
            v = self.a if mode == "acc" else r(addr)
            c = self.p & 1
            if m == "ASL":
                c, v = v >> 7, v << 1
            elif m == "LSR":
                c, v = v & 1, v >> 1
            elif m == "ROL":
                c, v = v >> 7, (v << 1) | c
            elif m == "ROR":
                c, v = v & 1, (v >> 1) | (c << 7)
            elif m == "INC":
                c, v = c, v + 1
            else:
                c, v = c, v - 1
            if m not in ("INC", "DEC"):
                self.p = (self.p & ~self.C) | c
            v = self._nz(v)
            if mode == "acc":
                self.a = v
            else:
                self.write(addr, v)
        elif mode == "rel":
            flag = {"BCC": (self.C, 0), "BCS": (self.C, 1), "BEQ": (self.Z, 1), "BNE": (self.Z, 0),
                    "BMI": (self.N, 1), "BPL": (self.N, 0), "BVC": (self.V, 0), "BVS": (self.V, 1)}[m]
            if bool(self.p & flag[0]) == bool(flag[1]):
                extra = 1 + (1 if (addr & 0xFF00) != (self.pc & 0xFF00) else 0)
                self.pc = addr
                self.end += extra
                return extra
        elif m == "JMP":
            self.pc = addr
        elif m == "JSR":
            ret = (self.pc - 1) & 0xFFFF
            self._push(ret >> 8)
            self._push(ret)
            self.pc = addr
        elif m == "RTS":
            self.pc = ((self._pull() | (self._pull() << 8)) + 1) & 0xFFFF
        elif m == "RTI":
            self.p = (self._pull() | self.U) & ~self.B
            self.pc = self._pull() | (self._pull() << 8)
        elif m == "BRK":
            self.pc = (self.pc + 1) & 0xFFFF
            self._push(self.pc >> 8)
            self._push(self.pc)
            self._push(self.p | self.B | self.U)
            self.p |= self.I
            self.pc = self._w16(0xFFFE)
        elif m == "PHA":
            self._push(self.a)
        elif m == "PHP":
            self._push(self.p | self.B | self.U)
        elif m == "PLA":
            self.a = self._nz(self._pull())
        elif m == "PLP":
            self.p = (self._pull() | self.U) & ~self.B
        elif m in ("TAX", "TAY", "TXA", "TYA", "TSX"):
            v = {"TAX": self.a, "TAY": self.a, "TXA": self.x, "TYA": self.y, "TSX": self.sp}[m]
            v = self._nz(v)
            if m in ("TAX", "TSX"):
                self.x = v
            elif m == "TAY":
                self.y = v
            else:
                self.a = v
        elif m == "TXS":
            self.sp = self.x
        elif m in ("INX", "DEX"):
            self.x = self._nz(self.x + (1 if m == "INX" else -1))
        elif m in ("INY", "DEY"):
            self.y = self._nz(self.y + (1 if m == "INY" else -1))
        elif m in ("CLC", "SEC", "CLI", "SEI", "CLV", "CLD", "SED"):
            bit = {"C": self.C, "I": self.I, "V": self.V, "D": self.D}[m[2]]
            self.p = (self.p | bit) if m[0] == "S" else (self.p & ~bit)
        return 0


# ====================================================================== Atari 2600
TIA_NAMES = {0x00: "VSYNC", 0x01: "VBLANK", 0x02: "WSYNC", 0x04: "NUSIZ0", 0x05: "NUSIZ1", 0x06: "COLUP0",
             0x07: "COLUP1", 0x08: "COLUPF", 0x09: "COLUBK", 0x0A: "CTRLPF", 0x0B: "REFP0", 0x0C: "REFP1",
             0x0D: "PF0", 0x0E: "PF1", 0x0F: "PF2", 0x10: "RESP0", 0x11: "RESP1", 0x12: "RESM0", 0x13: "RESM1",
             0x14: "RESBL", 0x1B: "GRP0", 0x1C: "GRP1", 0x1D: "ENAM0", 0x1E: "ENAM1", 0x1F: "ENABL", 0x20: "HMP0",
             0x21: "HMP1", 0x22: "HMM0", 0x23: "HMM1", 0x24: "HMBL", 0x2A: "HMOVE", 0x2B: "HMCLR", 0x2C: "CXCLR"}
CYCLES_PER_LINE = 76


class Atari2600Probe:
    """Run a 2K / 4K ROM; ``run_frames(n)`` returns, per frame (VSYNC to VSYNC), the list of scan lines with the
    register state at the end of each line and the TIA writes made during it as (name, CPU cycle in the line at
    which the store landed). Lines are 76 CPU cycles; WSYNC halts the CPU until the line ends, a line that runs
    out of cycles without WSYNC just ends ("auto" lines). The RIOT timer (TIM1T / TIM8T / TIM64T / T1024T,
    INTIM) is emulated; the joystick reads as released."""

    def __init__(self, rom: bytes):
        if len(rom) not in (2048, 4096):
            raise ValueError("2K or 4K ROM expected")
        self.rom = bytes(rom) * (4096 // len(rom))
        self.ram = bytearray(128)
        self.regs: dict[str, int] = {}
        self.cpu = CPU6502(self._read, self._write)
        self.cpu.reset()
        self.line_start = 0              # cpu cycle at which the current line began
        self.cur_writes: list[tuple[str, int]] = []
        self.lines: list[dict] = []      # finished lines of the current frame
        self.done_frames: list[list[dict]] = []
        self.auto_lines = 0              # lines that ended without WSYNC
        self.in_frame = False
        self.timer = (0, 0, 1024)        # (value written, cycle written, interval)

    # -------------------------------------------------- RIOT timer
    def _intim(self) -> int:
        v, at, iv = self.timer
        el = self.cpu.cycles - at
        ticks = el // iv
        if ticks <= v:
            return v - ticks
        return (0xFF - (el - (v + 1) * iv)) & 0xFF        # after expiry: counts every cycle

    # -------------------------------------------------- bus
    def _read(self, a: int) -> int:
        a &= 0x1FFF
        if a & 0x1000:
            return self.rom[a & 0xFFF]
        if a & 0x80 and not a & 0x200:
            return self.ram[a & 0x7F]
        if a & 0x200:
            r = a & 0x2FF
            if r == 0x280:
                return 0xFF                                # SWCHA: no direction pressed
            if (r & 0x285) == 0x284:
                return self._intim()
            return 0
        return 0x80 if (a & 0x0F) == 0x0C else 0           # INPT4: fire not pressed

    def _close_line(self, wsync: bool) -> None:
        self.lines.append({"regs": dict(self.regs), "writes": self.cur_writes, "wsync": wsync})
        self.cur_writes = []
        self.line_start += CYCLES_PER_LINE
        if not wsync:
            self.auto_lines += 1

    def _catch_up(self, at: int) -> None:
        while at - self.line_start > CYCLES_PER_LINE:
            self._close_line(False)

    def _write(self, a: int, v: int) -> None:
        a &= 0x1FFF
        if a & 0x1000:
            return
        if a & 0x80 and not a & 0x200:
            self.ram[a & 0x7F] = v & 0xFF
            return
        if a & 0x200:
            if (a & 0x294) == 0x294:                        # TIM1T / TIM8T / TIM64T / T1024T
                self.timer = (v & 0xFF, self.cpu.end, (1, 8, 64, 1024)[a & 3])
                self._catch_up(self.cpu.end)
                self.cur_writes.append((("TIM1T", "TIM8T", "TIM64T", "T1024T")[a & 3], self.cpu.end - self.line_start))
            return
        reg = TIA_NAMES.get(a & 0x3F)
        if reg is None:
            return
        land_abs = self.cpu.end                             # a store lands on its last cycle
        self._catch_up(land_abs)
        if reg == "VSYNC" and v & 2 and not self.regs.get("VSYNC", 0) & 2:
            if self.in_frame:
                self.done_frames.append(self.lines)
            self.lines, self.in_frame = [], True
        self.regs[reg] = v & 0xFF
        self.cur_writes.append((reg, land_abs - self.line_start))
        if reg == "WSYNC":
            self._close_line(True)                          # the CPU halts until this line ends
            self.cpu.cycles = self.line_start - (self.cpu.end - self.cpu.cycles)

    def run_frames(self, n: int = 2, max_steps: int = 2_000_000) -> list[list[dict]]:
        steps = 0
        while len(self.done_frames) < n and steps < max_steps:
            self.cpu.step()
            self._catch_up(self.cpu.cycles)
            steps += 1
        return self.done_frames


# ====================================================================== NES (NROM)
class NESProbe:
    """Load an iNES NROM image; ``run(frames)`` executes with an NMI every *cycles_per_frame* CPU cycles once the
    program enables NMIs ($2000 bit 7). ``vram`` holds the name tables ($2000-$2FFF) and ``palette`` 32 bytes."""

    def __init__(self, image: bytes):
        if image[:4] != b"NES\x1a":
            raise ValueError("not an iNES file")
        prg_banks, chr_banks = image[4], image[5]
        self.vertical = bool(image[6] & 1)
        prg = image[16:16 + prg_banks * 16384]
        self.prg = prg if len(prg) == 32768 else prg * 2
        self.chr = image[16 + prg_banks * 16384:16 + prg_banks * 16384 + chr_banks * 8192]
        self.ram = bytearray(2048)
        self.vram = bytearray(0x1000)           # $2000-$2FFF (4 name tables, mirrored by the probe)
        self.palette = bytearray(32)
        self.oam = bytearray(256)
        self.ctrl = 0
        self.mask = 0
        self.addr = 0
        self.latch = False
        self.scroll = [0, 0]
        self.pad = 0                            # buttons held: bit 7 A ... bit 0 Right (read order A first)
        self._shift = 0
        self.cpu = CPU6502(self._read, self._write)
        self.cpu.reset()
        self.nmis = 0

    def _nt(self, a: int) -> int:
        a = (a - 0x2000) & 0x0FFF
        table, off = a // 0x400, a % 0x400
        table = (table & 1) if self.vertical else (table >> 1)
        return table * 0x400 + off

    def _read(self, a: int) -> int:
        if a < 0x2000:
            return self.ram[a & 0x7FF]
        if a < 0x4000:
            r = a & 7
            if r == 2:
                self.latch = False
                return 0x80
            return 0
        if a == 0x4016:
            v = (self._shift >> 7) & 1
            self._shift = (self._shift << 1) & 0xFF
            return v | 0x40
        if a >= 0x8000:
            return self.prg[a - 0x8000]
        return 0

    def _write(self, a: int, v: int) -> None:
        if a < 0x2000:
            self.ram[a & 0x7FF] = v
        elif a < 0x4000:
            r = a & 7
            if r == 0:
                self.ctrl = v
            elif r == 1:
                self.mask = v
            elif r == 5:
                self.scroll[1 if self.latch else 0] = v
                self.latch = not self.latch
            elif r == 6:
                if not self.latch:
                    self.addr = (self.addr & 0x00FF) | ((v & 0x3F) << 8)
                else:
                    self.addr = (self.addr & 0xFF00) | v
                self.latch = not self.latch
            elif r == 7:
                a2 = self.addr & 0x3FFF
                if a2 >= 0x3F00:
                    i = a2 & 0x1F
                    if i in (0x10, 0x14, 0x18, 0x1C):
                        i -= 0x10
                    self.palette[i] = v & 0x3F
                elif a2 >= 0x2000:
                    self.vram[self._nt(a2)] = v
                self.addr = (self.addr + (32 if self.ctrl & 4 else 1)) & 0x3FFF
        elif a == 0x4014:
            base = v << 8
            for i in range(256):
                self.oam[i] = self._read(base + i)
        elif a == 0x4016:
            if v & 1:
                self._shift = self.pad

    def nametable(self, n: int) -> bytes:
        return bytes(self.vram[n * 0x400:n * 0x400 + 960])

    def attributes(self, n: int) -> bytes:
        return bytes(self.vram[n * 0x400 + 960:n * 0x400 + 1024])

    def run(self, frames: int = 1, cycles_per_frame: int = 29780, max_cycles: int = 60_000_000) -> int:
        """Run until *frames* NMIs were delivered (or the cycle limit). Returns the NMIs delivered."""
        start_nmis = self.nmis
        next_nmi = self.cpu.cycles + cycles_per_frame
        while self.nmis - start_nmis < frames and self.cpu.cycles < max_cycles:
            self.cpu.step()
            if self.cpu.cycles >= next_nmi:
                next_nmi = self.cpu.cycles + cycles_per_frame
                if self.ctrl & 0x80:
                    self.cpu.irq_nmi(0xFFFA)
                    self.nmis += 1
        return self.nmis - start_nmis
