"""Firmware / ECU Analysis project - study a firmware image (.bin .ori .hex .s19 .elf ...) without changing it
(radide/firmware/analysis, docs/FIRMWARE.md "Formats and analysis").

* New Project > Firmware > Firmware / ECU Analysis: choose the file afterwards (Project > Firmware Analysis >
  Set Original...) or start from "Firmware Analysis (Synthetic ARM Image)" - a synthetic Cortex-M image written
  by RAD IDE (no vehicle or manufacturer data).
* The original is copied into original/, set read-only and its SHA-256 recorded; it is never modified.
* Build (Build > Build Project, F5 / Ctrl+F5) verifies the original and writes build/analysis.txt (format,
  memory map, CPU and base address guesses, entropy regions, fill areas, identification strings).
* Project > Firmware Analysis > Analyze opens the analysis view (entropy graph, strings, disassembly with cross
  references, Analyze in Ghidra).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from ..model import Project
from .base import LanguagePlugin, RunSpec


class FirmwareAnalysisPlugin(LanguagePlugin):
    id = "firmware-analysis"
    display_name = "Firmware / ECU Analysis"
    code_ext = ".labels"
    case_sensitive = True
    line_comments = ["#"]
    block_comment = None
    string_quotes = ['"']
    keywords = []
    builtins = []
    supports_debug = False
    has_forms = False
    project_name_base = "FirmwareAnalysis"
    install_hint = "Nothing to install. Ghidra (optional) adds decompiled C."

    def project_templates(self) -> list[tuple[str, str, str, str]]:
        return [("fwa_empty", "Firmware / ECU Analysis", "Study a firmware image (.bin .ori .hex .s19 .elf): "
                 "read-only original with SHA-256, memory map, CPU / base address guess, entropy, strings, "
                 "disassembly and Ghidra.", "SP_FileDialogContentsView"),
                ("fwa_demo", "Firmware Analysis (Synthetic ARM Image)", "Starts with a synthetic Cortex-M image "
                 "written by RAD IDE (no vehicle or manufacturer data) - to learn the analysis tools.",
                 "SP_MediaPlay")]

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from ..firmware.analysis.project import new_project
        folder = Path(folder)
        fp = new_project(folder, name)
        files = ["notes.md", "labels.json"]
        if template == "fwa_demo":
            from ..firmware.analysis.synth import make_image
            im = make_image("arm-thumb", seed=3)
            src = folder / "samples_in" / "synthetic_cortex_m.bin"
            src.parent.mkdir(parents=True, exist_ok=True)
            src.write_bytes(im.bytes())
            fp.set_original(src)
            try:
                src.unlink()
                src.parent.rmdir()
            except OSError:
                pass
            from ..firmware.analysis.project import Label
            labs = [Label(im.entry, "reset_handler", "reset vector", "func")]
            labs += [Label(t.address, t.name, f"{t.kind} {t.rows}x{t.cols}", "table") for t in im.tables[:8]]
            fp.save_labels(labs)
            fp.save()
        project = Project(folder, name, self.id, [], "firmware.json", files)
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
        return f"# {name} - notes\n"

    def find_handler(self, code: str, name: str) -> int:
        return -1

    def add_handler(self, code: str, name: str, form, args=None):
        return code, 0

    # ------------------------------------------------------------------ build / run
    def find_interpreter(self, configured: str = "") -> str:
        return sys.executable or "python"

    def build_command(self, folder: Path, project=None) -> str:
        from ..retro.pycmd import module_command
        return module_command("radide.firmware.analysis", "build", Path(folder))

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        from ..paths import python_root
        root = python_root()
        env = dict(os.environ)
        env["PYTHONPATH"] = str(root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        return RunSpec(sys.executable, ["-u", "-m", "radide.firmware.analysis", "build", str(Path(folder))],
                       Path(folder), env)

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str, breakpoints) -> RunSpec:
        return self.run_spec(folder, startup_form, interpreter)

    def document_symbols(self, code: str) -> list[dict]:
        out = []
        try:
            data = json.loads(code)
        except ValueError:
            return out
        if isinstance(data, list):
            for i, x in enumerate(data[:2000]):
                if isinstance(x, dict) and x.get("name"):
                    out.append({"name": f"{x.get('address', '')} {x['name']}", "kind": "constant", "line": i,
                                "detail": x.get("comment", ""), "children": []})
        return out


PLUGIN = FirmwareAnalysisPlugin()
