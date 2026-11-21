"""DOS Assembly (16-bit, MASM syntax) - New Project > DOS.

JWasm assembles the source straight into an MZ .EXE (``.model small``) or a .COM (``org 100h``); Ctrl+F5 runs it
in DOSBox-X. F5 (Debug): when RAD IDE's own 8086 emulator understands the program (radide/emu8086), it is stepped
there with the Registers / Flags / Memory / Stack views; otherwise DOSBox-X's debugger starts it (DEBUGBOX).
Project > DOS Settings > Debugger chooses: auto | emu8086 | dosbox.
"""
from __future__ import annotations

from pathlib import Path

from ..retro.dos.plugin import DosPluginBase


def _asm_lists():
    try:
        from .emu8086 import DIRECTIVES, INSTRUCTIONS, REGISTERS
        return sorted(set(INSTRUCTIONS) | set(DIRECTIVES)), list(REGISTERS)
    except Exception:  # noqa: BLE001
        return [], []


_KW, _REGS = _asm_lists()


class DosAsmPlugin(DosPluginBase):
    id = "dos-asm"
    display_name = "DOS Assembly (16-bit MASM)"
    code_ext = ".asm"
    kind = "asm"
    project_name_base = "DosAsm"
    line_comments = [";"]
    block_comment = None
    string_quotes = ["'", '"']
    keywords = _KW
    builtins = _REGS

    def module_template(self, name: str) -> str:
        return (f"; {name}.ASM - procedures included from MAIN.ASM with:  include {name}.ASM\r\n"
                f"{name.lower()}_hello proc\r\n        ret\r\n{name.lower()}_hello endp\r\n")

    # ------------------------------------------------------------ F5 in the 8086 emulator
    def emulator_compatible(self, folder: Path, main: str) -> bool:
        """True when radide/emu8086 assembles *main* without errors (then F5 steps it there)."""
        try:
            from ..emu8086.assembler import assemble
            src = (Path(folder) / main).read_text(encoding="cp437", errors="replace")
            prog = assemble(src, main, include_dir=Path(folder))
            return not prog.errors
        except Exception:  # noqa: BLE001
            return False

    def make_session(self, win, spec, debug: bool):
        project = getattr(win, "project", None)
        if not debug or project is None or project.language != self.id:
            return None
        from ..retro.dos.build import settings_for
        s = settings_for(project)
        choice = str(s.get("debugger", "auto"))
        if choice == "dosbox":
            return None
        folder = Path(project.folder)
        if choice == "auto" and not self.emulator_compatible(folder, s["main"]):
            return None
        try:
            from ..emu8086.ui import Emu8086Session
        except Exception:  # noqa: BLE001 - the emulator is optional
            return None
        bps = getattr(spec, "breakpoints", None)
        if bps is None:
            try:
                bps = win._all_breakpoints()
            except Exception:  # noqa: BLE001
                bps = []
        try:
            win.log("DOS Assembly: F5 steps the program in RAD IDE's 8086 emulator (DOS Settings > Debugger = "
                    "dosbox uses DOSBox-X's debugger instead).")
        except Exception:  # noqa: BLE001
            pass
        return Emu8086Session(win, folder, s["main"], True, bps)


PLUGIN = DosAsmPlugin()
