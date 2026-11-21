"""An AGC "machine" for RAD IDE: CPU + DSKY + the assembled program (source line <-> address).

Used by the IDE session (radide/agc/session.py), the headless runner (``python -m radide.agc``) and the tests.

    m = AgcMachine.from_file(Path("MAIN.agc"))
    m.run_seconds(1.5)
    m.keys("V35E")            # V VERB  N NOUN  E ENTR  R RSET  C CLR  K KEY REL  P PRO  + -  digits
    m.dsky.summary()
"""
from __future__ import annotations

from pathlib import Path

from . import assembler
from .cpu import MCT_SECONDS, AgcCpu
from .dsky_model import DskyModel
from .isa import KEY_CODES

KEY_LETTERS = {"V": "VERB", "N": "NOUN", "E": "ENTR", "R": "RSET", "C": "CLR", "K": "KEY REL", "+": "+", "-": "-"}


class AgcMachine:
    def __init__(self, program: assembler.Program | None = None, rope=None):
        self.program = program
        self.cpu = AgcCpu(rope if rope is not None else (program.rope if program else None))
        self.dsky = DskyModel()
        self.listeners: list = []           # callable(channel, value)
        self.cpu.on_channel = self._channel
        self.breakpoints: set[tuple[str, int]] = set()     # (file name lower, line)
        self._bp_addrs: set[tuple[str, int, int]] = set()

    @classmethod
    def from_file(cls, path: Path, texts: dict | None = None) -> "AgcMachine":
        return cls(assembler.assemble_file(Path(path), texts))

    @classmethod
    def from_bin(cls, data: bytes) -> "AgcMachine":
        return cls(None, assembler.load_bin(data))

    # ------------------------------------------------------------------ I/O
    def _channel(self, ch: int, value: int) -> None:
        self.dsky.channel(ch, value)
        for fn in list(self.listeners):
            fn(ch, value)

    def press(self, name: str) -> None:
        """Press one DSKY key by name ("VERB", "5", "ENTR", "PRO" ...)."""
        name = name.upper()
        if name == "PRO":
            self.cpu.set_pro(True)
            return
        self.cpu.press_key(KEY_CODES[name])

    def release_pro(self) -> None:
        self.cpu.set_pro(False)

    def keys(self, seq: str, gap: float = 0.15) -> None:
        """Type a key sequence like "V16N36E" and run *gap* seconds after every key."""
        for ch in seq.replace(" ", "").upper():
            if ch == "P":
                self.press("PRO")
                self.run_seconds(gap)
                self.release_pro()
            else:
                self.press(KEY_LETTERS.get(ch, ch))
            self.run_seconds(gap)

    # ------------------------------------------------------------------ running
    def run_seconds(self, seconds: float, stop=None) -> str | None:
        return self.cpu.run_mct(int(seconds / MCT_SECONDS), stop)

    def current_line(self):
        """(file, line) of the instruction at Z, or None (no source there)."""
        if self.program is None:
            return None
        return self.program.line_of.get(self.cpu.location())

    def set_breakpoint_lines(self, lines) -> None:
        self.breakpoints = {(Path(f).name.lower(), int(n)) for f, n in lines}
        self._bp_addrs = set()
        if self.program is None:
            return
        for key, loc in self.program.addr_of_line.items():
            if key in self.breakpoints:
                self._bp_addrs.add((loc.kind, loc.bank, loc.off))

    def at_breakpoint(self) -> bool:
        return bool(self._bp_addrs) and self.cpu.location() in self._bp_addrs and self.cpu.pending_word is None

    def symbol_value(self, name: str):
        """(Loc, 15-bit value) of an erasable / fixed symbol, or None."""
        if self.program is None:
            return None
        loc = self.program.symbols.get(name) or next((v for k, v in self.program.symbols.items()
                                                      if k.upper() == name.upper()), None)
        if loc is None:
            return None
        if loc.kind == "E":
            return loc, self.cpu.read_erasable(loc.bank, loc.off)
        if loc.kind == "F":
            return loc, self.cpu.rope[loc.bank][loc.off]
        return loc, loc.off


def run_cli(argv: list[str]) -> int:
    """python -m radide.agc FILE.agc [--seconds S] [--keys SEQ] [--bin OUT] [--listing]"""
    import argparse
    ap = argparse.ArgumentParser(prog="python -m radide.agc", description="Assemble and run an AGC program "
                                 "in RAD IDE's emulator; prints the DSKY.")
    ap.add_argument("source")
    ap.add_argument("--seconds", type=float, default=1.5, help="seconds to run before typing the keys")
    ap.add_argument("--keys", default="", help='DSKY keys, e.g. "V35E" or "V16N36E"')
    ap.add_argument("--after", type=float, default=1.0, help="seconds to run after the keys")
    ap.add_argument("--bin", default="", help="also write the yaYUL-compatible rope image")
    ap.add_argument("--listing", action="store_true", help="print the listing")
    ap.add_argument("--assemble-only", action="store_true")
    ap.add_argument("--lang", default="en")
    a = ap.parse_args(argv)
    src = Path(a.source)
    if src.suffix.lower() == ".bin":
        m = AgcMachine.from_bin(src.read_bytes())
    else:
        prog = assembler.assemble_file(src)
        for d in prog.warnings:
            print(f"{Path(d.file).name}:{d.line}: Warning: {d.text(a.lang)}")
        for d in prog.errors:
            print(f"{Path(d.file).name}:{d.line}: Error: {d.text(a.lang)}")
        print(f"Assembled {src.name}: {prog.words()} words, {len(prog.errors)} error(s), "
              f"{len(prog.warnings)} warning(s)")
        if a.listing:
            print(prog.listing_text())
        if a.bin and prog.ok:
            Path(a.bin).write_bytes(prog.to_bin())
            print(f"Rope image: {a.bin}")
        if not prog.ok:
            return 2
        if a.assemble_only:
            return 0
        m = AgcMachine(prog)
    m.run_seconds(a.seconds)
    if a.keys:
        print("DSKY before keys:", m.dsky.summary())
        m.keys(a.keys)
        m.run_seconds(a.after)
    print("DSKY:", m.dsky.summary())
    return 0


__all__ = ["AgcMachine", "run_cli"]
