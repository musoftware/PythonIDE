"""DOS Text-Mode Forms App - New Project > DOS (radide/retro/design/textmode, docs/RETRO.md).

Draw DOS text-mode screens (windows, buttons, text boxes, check boxes, option buttons, list boxes, menus, status
bars ...) in the Text-Mode Designer; RAD IDE generates the program and its small run-time in the chosen language:

    QBasic / FreeBASIC   LOCATE / COLOR / PRINT, INKEY$, mouse via GETMOUSE (QuickBASIC: INT 33h)
    Pascal               Free Pascal (i8086-msdos) / Turbo Pascal 7, Crt unit
    C                    OpenWatcom / Turbo C / DJGPP, direct B800h video writes, conio
    16-bit assembly      a .COM program writing to B800h, INT 16h keyboard, INT 33h mouse

The new project is a normal DOS project of the dosdev slice (language dos-qbasic / dos-pascal / dos-c / dos-asm):
its compiler is downloaded on the first build and the program runs in DOSBox-X. This plugin only creates it (and
is the project language when that DOS kind is not available).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from ..model import Project
from .base import LanguagePlugin, RunSpec

TEMPLATES = [
    ("tui_freebasic", "Forms App - QBasic / FreeBASIC",
     "A text-mode forms program in QBasic syntax, built with FreeBASIC -lang qb (DOS) and run in DOSBox-X. "
     "Menu bar, window, label, OK / Cancel buttons, status bar.", "SP_FileDialogListView"),
    ("tui_pascal", "Forms App - Pascal (Crt)",
     "The same forms program in Turbo Pascal style (Crt unit), built with Free Pascal for 16-bit DOS.",
     "SP_FileDialogDetailedView"),
    ("tui_c", "Forms App - C (OpenWatcom / Turbo C)",
     "The forms program in C: direct video memory at B800h, conio keys, INT 33h mouse; OpenWatcom builds a DOS "
     ".EXE.", "SP_ComputerIcon"),
    ("tui_asm", "Forms App - 16-bit Assembly (.COM)",
     "The forms program in 16-bit assembly (MASM / TASM / JWasm syntax): a .COM file that writes to B800h and "
     "reads INT 16h / INT 33h.", "SP_DriveHDIcon"),
    ("tui_quickbasic", "Forms App - QuickBASIC 4.5 (your own copy)",
     "QuickBASIC 4.5 dialect (CALL INTERRUPT for the mouse). Needs your own QB.EXE / BC.EXE (Tools > Retro > "
     "DOS Programming > DOS Toolchains): FreeBASIC has no CALL INTERRUPT, so choose the QBasic / FreeBASIC app to "
     "build without them.",
     "SP_FileDialogListView"),
    ("tui_qbasic", "Forms App - QBasic 1.1 (keyboard only)",
     "Plain QBasic 1.1 dialect (no mouse, no COMMAND$): runs in your own QBASIC.EXE; FreeBASIC builds it too.",
     "SP_FileDialogListView"),
]
from ..paths import python_root as _python_root  # noqa: E402
IDE_ROOT = _python_root()   # a real Python imports radide from here (not _internal in a release build)


class DosTuiFormsPlugin(LanguagePlugin):
    id = "dos-tuiforms"
    display_name = "DOS Text-Mode Forms App"
    code_ext = ".tform"
    has_forms = False
    supports_debug = False
    case_sensitive = False
    line_comments = []
    project_name_base = "DosForms"
    install_hint = ("RAD IDE downloads the free compiler of the chosen language on the first build and runs the "
                    "program in DOSBox-X (Tools > DOS Toolchains...).")

    def project_templates(self) -> list[tuple[str, str, str, str]]:
        return list(TEMPLATES)

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from ..retro.design.textmode.project import create
        target = (template or "tui_freebasic").replace("tui_", "", 1)
        return create(Path(folder), name, target if target else "freebasic")

    # ------------------------------------------------------------ no forms / code files of its own
    def code_file(self, form_name: str) -> str:
        return form_name if form_name.lower().endswith(".tform") else f"{form_name}.tform"

    def designer_file(self, form_name: str) -> str:
        return self.code_file(form_name)

    def generate_designer(self, form, user_code: str) -> str:
        return user_code

    def new_code(self, form, is_startup: bool) -> str:
        return ""

    def find_handler(self, code: str, name: str) -> int:
        return -1

    def add_handler(self, code, name, form, args=None):
        return code, 0

    # ------------------------------------------------------------ build / run (fallback language only)
    def find_interpreter(self, configured: str = "") -> str:
        return sys.executable or "python"

    def _env(self) -> dict:
        return dict(os.environ, PYTHONPATH=str(IDE_ROOT), PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")

    def build_command(self, folder: Path, project: Project) -> str | None:
        return f'"{sys.executable}" -m radide.retro.design.textmode.project build "{Path(folder)}"'

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        return RunSpec(sys.executable, ["-u", "-m", "radide.retro.design.textmode.project", "run", str(Path(folder))],
                       Path(folder), self._env())


PLUGIN = DosTuiFormsPlugin()
