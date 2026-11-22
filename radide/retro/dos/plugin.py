"""DosPluginBase - the shared part of the DOS language plugins (radide/languages/dos_*.py).

A DOS project is a plain RAD project (project.radproj, no forms): ``modules`` lists the source files, ``startup``
is the main file and the ``"dos"`` entry holds the DOS settings (build.settings_for). Build / Run go through
``python -m radide.retro.dos.run`` (output in the Output window, the program in a DOSBox-X window); Build Solution
uses ``build_command``. Editor support (completions, hover, signature help, outline, F12) comes from
radide/retro/dos/reference.py and intel.py.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from ...languages.base import Completion, LanguagePlugin, RunSpec
from ...model import Project

from ...paths import python_root as _python_root  # noqa: E402
IDE_ROOT = _python_root()   # a real Python imports radide from here (not _internal in a release build)


class DosPluginBase(LanguagePlugin):
    kind = "qbasic"
    has_forms = False
    supports_debug = True
    project_name_base = "DosApp"
    case_sensitive = False
    install_hint = ("RAD IDE downloads the free compiler (official build, SHA-256 checked) on the first build; "
                    "DOSBox-X runs the program. Tools > DOS Toolchains...")
    dos_project = True                   # radide/features/dos_ide.py

    # ------------------------------------------------------------ tools
    @property
    def tool_names(self) -> list[str]:
        from .toolchain import COMPILER_FOR_KIND
        c = COMPILER_FOR_KIND.get(self.kind, "")
        return [c] if c else ["dosbox-x"]

    def tool(self) -> str:
        """The compiler (downloaded) or, when it is missing, its download URL note (still "installable")."""
        from .toolchain import COMPILER_FOR_KIND, RELEASES, dosbox_exe, find
        c = COMPILER_FOR_KIND.get(self.kind, "")
        if not c:
            return dosbox_exe() or "DOSBox-X (downloaded on first run)"
        return find(c) or f"{RELEASES[c].title} (downloaded on first build)"

    def find_interpreter(self, configured: str = "") -> str:
        return sys.executable or "python"

    # ------------------------------------------------------------ New Project
    def project_templates(self) -> list[tuple[str, str, str, str]]:
        from .templates import for_kind
        return [(t.id, t.title, t.description, t.icon) for t in for_kind(self.kind)]

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from .templates import BY_ID, create_files, for_kind
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        t = BY_ID.get(template) or for_kind(self.kind)[0]
        files = create_files(folder, name, t)
        mains = [f for f in files if f.upper().endswith(self.code_ext.upper())]
        project = Project(folder, name, self.id, [], Path(mains[0]).stem if mains else "", files)
        dos = {"kind": self.kind}
        dos.update(t.settings)
        project.extra["dos"] = dos
        if not (folder / ".gitignore").exists():
            (folder / ".gitignore").write_text("_build/\n*.EXE\n*.COM\n*.OBJ\n*.o\nCWSDPMI.EXE\n_OUT.TXT\n"
                                               "_SCREEN.TXT\n_SCR13.RAW\n", encoding="utf-8")
        project.save()
        return project

    # ------------------------------------------------------------ code files (no forms)
    def code_file(self, form_name: str) -> str:
        return form_name if form_name.lower().endswith(self.code_ext.lower()) else f"{form_name}{self.code_ext}"

    def designer_file(self, form_name: str) -> str:
        return self.code_file(form_name)

    def generate_designer(self, form, user_code: str) -> str:
        return user_code

    def new_code(self, form, is_startup: bool) -> str:
        return ""

    def find_handler(self, code: str, name: str) -> int:
        import re
        return self._find_line(code, rf"\b{re.escape(name)}\b", re.I)

    def add_handler(self, code, name, form, args=None):
        return code, 0

    # ------------------------------------------------------------ build / run
    def build_command(self, folder: Path, project: Project) -> str | None:
        from ..pycmd import module_command          # the IDE runs it from the project folder, no PYTHONPATH
        return module_command("radide.retro.dos.build", Path(folder))

    def _env(self) -> dict:
        return dict(os.environ, PYTHONPATH=str(IDE_ROOT), PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        return RunSpec(sys.executable, ["-u", "-m", "radide.retro.dos.run", str(Path(folder))], Path(folder),
                       self._env())

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str, breakpoints) -> RunSpec:
        spec = RunSpec(sys.executable, ["-u", "-m", "radide.retro.dos.run", str(Path(folder)), "--debug"],
                       Path(folder), self._env())
        spec.breakpoints = list(breakpoints or [])                  # type: ignore[attr-defined]
        return spec

    def make_session(self, win, spec, debug: bool):
        """F5 on a DOS Assembly project whose code the 8086 emulator understands: step it there (visual
        registers / memory); otherwise None = the normal session (DOSBox-X, its debugger when F5)."""
        return None

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        from . import intel
        return intel.completions(self.kind, code, line, col) or [Completion(k, "keyword") for k in self.keywords]

    def hover(self, code, line, col, path, names=None) -> str:
        from . import intel
        return intel.hover(self.kind, code, line, col)

    def calltip(self, code, line, col, path, names=None) -> str:
        from . import intel
        return intel.calltip(self.kind, code, line, col)

    def document_symbols(self, code: str) -> list[dict]:
        from . import intel
        return intel.symbols(self.kind, code)

    def definition(self, code, line, col, path, names=None):
        from . import intel
        hit = intel.definition(self.kind, code, line, col)
        return (str(path), hit) if hit is not None else None


__all__ = ["DosPluginBase"]
