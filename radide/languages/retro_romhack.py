"""ROM Hacking Project - work on your own ROM / disk image with patches, character tables and notes
(radide/retro/rom, docs/RETRO.md "ROM workbench").

* New Project > Retro > ROM Hacking Project: choose the clean ROM afterwards (Project > ROM Hacking > Set Source
  ROM...) or start from the "Demo ROM" template (a tiny homebrew NES image written by RAD IDE).
* Build (Build > Build Project, or F5 / Ctrl+F5) applies the enabled patches in order to a fresh copy of the
  clean ROM and writes build/<name>_patched.<ext>; the original file is never written.
* F5 / Ctrl+F5 then starts the emulator of the system (radide/retro/emu, Tools > Retro > Emulators).
* The Patch Manager (Project > ROM Hacking > Patch Manager) orders / enables patches, adds IPS / BPS / UPS files
  and turns the edits of the working copy into a new patch.
"""
from __future__ import annotations

import sys
from pathlib import Path

from ..model import Project
from .base import LanguagePlugin, RunSpec

NOTES = """# {name} - ROM hacking notes

* Source ROM: set it with Project > ROM Hacking > Set Source ROM... (copied into rom/ or referenced).
* Patches (patches/) are applied in the order of the Patch Manager when you Build.
* Character tables (tables/*.tbl) make the hex editor's text column show the game's text.
* Build writes build/; the original ROM is never changed.

## Addresses

| Offset | What |
|--------|------|
|        |      |

## To do

- [ ]
"""

TABLE = """; {name}.tbl - character table (hex=text). Example: plain ASCII letters and digits.
; /FF=<end> marks an end-of-string code, *FE=<br> a line break.
"""


class RomHackPlugin(LanguagePlugin):
    id = "retro-romhack"
    display_name = "ROM Hacking Project"
    code_ext = ".tbl"
    case_sensitive = True
    line_comments = [";", "#"]
    block_comment = None
    string_quotes = []
    keywords = []
    builtins = []
    supports_debug = False
    has_forms = False
    project_name_base = "RomHack"
    install_hint = "Nothing to install. An emulator for Run can be downloaded from Tools > Retro."

    def project_templates(self) -> list[tuple[str, str, str, str]]:
        return [("romhack_empty", "ROM Hacking Project", "Your own ROM, disk or tape image + patches, tables and "
                 "notes. Build makes the patched copy; Run starts the emulator.", "SP_DriveFDIcon"),
                ("romhack_demo", "ROM Hacking Project (Demo ROM)", "Starts with a tiny homebrew NES ROM written by "
                 "RAD IDE (no game data) and an example IPS patch - to learn the tools.", "SP_MediaPlay")]

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from ..retro.rom.project import new_project
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        rp = new_project(folder, name)
        notes = folder / "notes.md"
        if not notes.exists():
            notes.write_text(NOTES.format(name=name), encoding="utf-8")
        tbl = folder / "tables" / "ascii.tbl"
        if not tbl.exists():
            body = TABLE.format(name="ascii") + "".join(f"{c:02X}={chr(c)}\n" for c in range(0x20, 0x7F))
            tbl.parent.mkdir(parents=True, exist_ok=True)
            tbl.write_text(body, encoding="utf-8")
        rp.tables = ["tables/ascii.tbl"]
        if template == "romhack_demo":
            from ..retro.rom import synth
            from ..retro.rom.patches import ips_create
            src = folder / "rom" / "demo.nes"
            src.parent.mkdir(parents=True, exist_ok=True)
            clean = synth.nes_rom()
            src.write_bytes(clean)
            rp.set_rom(src, copy=True)
            mod = bytearray(clean)
            msg = b"HELLO FROM RAD IDE"
            at = clean.find(msg)
            mod[at:at + len(msg)] = b"PATCHED BY RAD IDE"
            patch = folder / "patches" / "001_message.ips"
            patch.write_bytes(ips_create(clean, bytes(mod)))
            rp.add_patch(patch, "changes the message text")
        rp.output = f"build/{name}_patched{Path(rp.rom).suffix if rp.rom else '.bin'}"
        rp.save()
        project = Project(folder, name, self.id, [], "rom.json", ["notes.md", "tables/ascii.tbl"])
        project.save()
        return project

    # ------------------------------------------------------------------ files
    def code_file(self, form_name: str) -> str:
        return form_name

    def designer_file(self, form_name: str) -> str:
        return form_name

    def generate_designer(self, form, user_code: str) -> str:
        return user_code

    def new_code(self, form, is_startup: bool) -> str:
        return ""

    def module_template(self, name: str) -> str:
        return TABLE.format(name=name)

    def find_handler(self, code: str, name: str) -> int:
        return -1

    def add_handler(self, code: str, name: str, form, args=None):
        return code, 0

    # ------------------------------------------------------------------ build / run
    def find_interpreter(self, configured: str = "") -> str:
        return sys.executable or "python"

    def build_command(self, folder: Path, project=None) -> str:
        from ..retro.pycmd import module_command    # runs from the project folder without PYTHONPATH
        return module_command("radide.retro.rom", "build", Path(folder))

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        root = Path(__file__).resolve().parents[2]
        import os
        env = dict(os.environ)
        env["PYTHONPATH"] = str(root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        return RunSpec(sys.executable, ["-u", "-m", "radide.retro.rom", "run", str(Path(folder))], Path(folder), env)

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str, breakpoints) -> RunSpec:
        return self.run_spec(folder, startup_form, interpreter)

    def document_symbols(self, code: str) -> list[dict]:
        out = []
        for i, line in enumerate(code.splitlines()):
            s = line.strip()
            if s and not s.startswith((";", "#")) and "=" in s:
                key, _eq, val = s.partition("=")
                out.append({"name": f"{key.lstrip('/*$')} = {val[:20]}", "kind": "constant", "line": i,
                            "detail": "", "children": []})
        return out[:2000]


PLUGIN = RomHackPlugin()
