"""ECU / Firmware Project - work on a firmware or control-unit dump (.bin / .hex / .s19 ...) with the original
kept read-only, a working copy, versions, checksum blocks and a build (radide/firmware/project,
docs/FIRMWARE.md "ECU projects").

* New Project > Firmware > ECU / Firmware Project: choose the original afterwards (Project > ECU Project >
  Set Original...), or start from "ECU Project (Demo Firmware)" - a synthetic 64 KB image written by RAD IDE
  (no manufacturer data) with three checksum blocks and three calibration maps.
* Build (Build > Build Project, F5 / Ctrl+F5) = the working copy with corrected checksums -> build/<name>_mod.bin
  (or .hex / .s19) + a modification report.  The original file is never written.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ..model import Project
from .base import LanguagePlugin, RunSpec

NOTES = """# {name} - ECU project notes

* Original: Project > ECU Project > Set Original... (copied into original/ and kept read-only, SHA-256 checked
  before every build).
* Edit the working copy (work/) in the hex editor or the map editor; save named versions with notes
  (Project > ECU Project > Versions).
* Checksums: Project > ECU Project > Checksums (blocks, finder, profiles).  Verify every profile against your
  own original - presets are generic algorithms, not manufacturer specifications.
* Build writes build/ and a modification report; the original is never changed.

Edits to vehicle software can affect safety, warranty and emissions legality.  Keep the original and follow
local laws.

## Changes

| Version | What | Why |
|---------|------|-----|
|         |      |     |
"""


class FirmwareEcuPlugin(LanguagePlugin):
    id = "firmware-ecu"
    display_name = "ECU / Firmware Project"
    code_ext = ".ecuprofile"
    case_sensitive = True
    line_comments = ["#"]
    block_comment = None
    string_quotes = ['"']
    keywords = []
    builtins = []
    supports_debug = False
    has_forms = False
    project_name_base = "EcuProject"
    install_hint = "Nothing to install."

    def project_templates(self) -> list[tuple[str, str, str, str]]:
        return [("ecu_empty", "ECU / Firmware Project", "A firmware or control-unit dump (.bin .hex .s19 ...): "
                 "read-only original, working copy, versions, checksum blocks, Build with a report.",
                 "SP_DriveHDIcon"),
                ("ecu_demo", "ECU Project (Demo Firmware)", "Starts with a synthetic 64 KB image written by RAD IDE "
                 "(no vehicle data) with checksum blocks and calibration maps - to learn the tools.",
                 "SP_MediaPlay")]

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from ..firmware.project.model import new_project
        folder = Path(folder)
        ep = new_project(folder, name)
        notes = folder / "notes.md"
        if not notes.exists():
            notes.write_text(NOTES.format(name=name), encoding="utf-8")
        files = ["notes.md"]
        if template == "ecu_demo":
            from ..firmware.project import synth
            src = folder / "original" / "demo_ecu.bin"
            src.parent.mkdir(parents=True, exist_ok=True)
            if not src.exists():
                src.write_bytes(synth.image())
            ep.set_original(src, copy=True)
            ep.checksums = synth.demo_blocks()
            pack = folder / "maps" / "demo_ecu.maps.json"
            pack.parent.mkdir(parents=True, exist_ok=True)
            pack.write_text(json.dumps({"format": "radide-mappack", "version": 1, "name": "Demo maps",
                                        "base_address": "0x0", "maps": synth.demo_maps()}, indent=2),
                            encoding="utf-8")
            ep.maps = ep.rel(pack)
            from ..firmware.checksum.blocks import save_profile
            prof = save_profile(folder / "profiles" / "demo_ecu.ecuprofile.json", ep.checksums, "Demo ECU",
                                "Checksum blocks of the synthetic demo image", synth.SIZE)
            files.append(ep.rel(prof))
        ep.save()
        project = Project(folder, name, self.id, [], "ecu.json", files)
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
        return "# checksum / project notes\n"

    def find_handler(self, code: str, name: str) -> int:
        return -1

    def add_handler(self, code: str, name: str, form, args=None):
        return code, 0

    # ------------------------------------------------------------------ build / run
    def find_interpreter(self, configured: str = "") -> str:
        return sys.executable or "python"

    def build_command(self, folder: Path, project=None) -> str:
        from ..retro.pycmd import module_command    # runs from the project folder without PYTHONPATH
        return module_command("radide.firmware.project", "build", Path(folder))

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        import os
        from ..paths import python_root
        root = python_root()
        env = dict(os.environ)
        env["PYTHONPATH"] = str(root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        return RunSpec(sys.executable, ["-u", "-m", "radide.firmware.project", "build", str(Path(folder))],
                       Path(folder), env)

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str, breakpoints) -> RunSpec:
        return self.run_spec(folder, startup_form, interpreter)


PLUGIN = FirmwareEcuPlugin()
