"""Short entry points to the firmware disassembler for other slices (the workbench adapters look for
``radide.firmware.disasm.disassemble`` and ``find_ghidra``). The implementation lives in
radide/firmware/analysis/disasm.py and radide/firmware/analysis/ghidra.py."""
from __future__ import annotations

from ..analysis.disasm import (Line, XrefIndex, build_xrefs, disassemble as disassemble_map, listing,
                               supported, unsupported_reason)
from ..analysis.ghidra import analyze as ghidra_analyze, find_ghidra
from ..formats.memmap import MemoryMap

__all__ = ["Line", "XrefIndex", "build_xrefs", "disassemble", "disassemble_map", "listing", "supported",
           "unsupported_reason", "ghidra_analyze", "find_ghidra"]


def disassemble(data: bytes, base: int, arch: str, start: int, count: int = 400) -> list[tuple[int, str, str, str]]:
    """[(address, hex bytes, mnemonic, operands)] for *count* instructions from address *start* of *data* loaded
    at *base*. Raises ValueError for a CPU without a Capstone decoder (the caller shows Ghidra instead)."""
    mm = MemoryMap.from_bytes(bytes(data), base)
    if start < base:
        start = base + start
    lines = disassemble_map(mm, arch, start, max(16, count * 6), max_lines=count)
    return [(ln.address, ln.raw.hex(" "), ln.mnemonic, ln.ops) for ln in lines]
