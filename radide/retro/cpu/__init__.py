"""CPU instruction tables and disassemblers written for RAD IDE (no Qt in here).

* ``m6502``  - MOS 6502 / 6507 / 2A03 (Atari 2600 / 7800 / 8-bit, NES, C64), with the NMOS undocumented opcodes
* ``sm83``   - Sharp SM83 (Game Boy / Game Boy Color)
* ``z80``    - Zilog Z80 (ZX Spectrum, MSX, Master System), CB / ED / DD / FD / DDCB / FDCB prefixes
* ``hwregs`` - hardware register names + descriptions (TIA / RIOT, PPU / APU, GB I/O, VIC-II / SID / CIA, ZX ports)
* ``disasm`` - code / data separation by recursive tracing, labels, comments and re-assemblable source for DASM,
  ca65, RGBDS and sjasmplus
* ``romfmt`` - ROM / program file formats (2600 .bin, iNES .nes, Game Boy .gb, C64 .prg, ZX .tap / raw .bin)

Every table here was typed from the public CPU data sheets / programming manuals; the descriptions are our own.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Instr:
    """One decoded instruction."""
    addr: int
    size: int
    mnemonic: str              # lower case, e.g. "lda", "ld", "jr"
    operand: str               # display operand with "{t}" where a target label goes ("" = none)
    target: int | None = None  # address the operand refers to (jump / call / memory), None = immediate / none
    kind: str = ""             # "" | "jump" | "jumpind" | "branch" | "call" | "return" | "stop"
    undocumented: bool = False
    raw: bytes = b""
    cycles: str = ""
    # how the operand value must be written for the assembler to choose the same encoding:
    #   "abs16" = a 16-bit absolute that must not shrink to zero page, "zp" = zero page, "" = no constraint
    width: str = ""
    mode: str = ""             # CPU-specific addressing mode name (6502: "abs", "zpx", ...)

    @property
    def is_flow_end(self) -> bool:
        return self.kind in ("jump", "jumpind", "return", "stop")


CPUS = ("6502", "sm83", "z80")


def decoder(cpu: str):
    """The module that decodes *cpu*: has ``decode(mem, addr, base, undocumented=False) -> Instr | None``."""
    if cpu in ("6502", "6507", "2a03"):
        from . import m6502
        return m6502
    if cpu == "sm83":
        from . import sm83
        return sm83
    if cpu == "z80":
        from . import z80
        return z80
    raise KeyError(cpu)
