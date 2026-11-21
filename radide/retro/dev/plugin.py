"""Shared base of the retro language plugins (radide/languages/retro_*.py).

A retro project is an ordinary RAD project without forms: its sources are modules, ``extra["retro"]`` says the
system and how to build (radide/retro/dev/build.py). F5 / Ctrl+F5 run ``python -m radide.retro.dev.run`` in the
Output window: build (Error List rows from ``_build/diagnostics.json``, radide/features/retro_dev.py), then the
ROM in an emulator. Editor support: radide/retro/dev/intel.py.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from ...languages.base import LanguagePlugin, RunSpec
from ...model import Project
from .intel import RetroIntel, mnemonics, registers


class RetroPluginBase(RetroIntel, LanguagePlugin):
    system = "atari2600"
    cpu = "6502"
    dialect = "dasm"
    has_forms = False
    supports_debug = False
    asm_intel = False                      # not x86: radide/features/retro_dev.py keeps the x86 overlay away
    retro_dev = True
    case_sensitive = False
    line_comments = [";"]
    block_comment = None
    string_quotes = ['"', "'"]
    project_name_base = "RetroGame"
    install_hint = ""

    @property
    def keywords(self) -> list[str]:              # type: ignore[override]
        from .intel import DIRECTIVES
        return mnemonics(self.cpu) + [d.lower() for d in DIRECTIVES.get(self.dialect, [])]

    @property
    def builtins(self) -> list[str]:              # type: ignore[override]
        return registers(self.cpu)

    @property
    def tool_names(self) -> list[str]:
        return {"dasm": ["dasm"], "ca65": ["ca65", "ld65", "cl65"], "rgbds": ["rgbasm", "rgblink", "rgbfix"],
                "sjasmplus": ["sjasmplus"]}[self.dialect]

    # ------------------------------------------------------------ New Project
    def project_templates(self) -> list[tuple[str, str, str, str]]:
        from .templates import TEMPLATES
        return [(t.id, t.title, t.description, t.icon) for t in TEMPLATES.get(self.id, [])]

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        from .templates import BY_ID, TEMPLATES, render
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        t = BY_ID.get(template) or TEMPLATES[self.id][0]
        for fname, text in t.files:
            p = folder / render(fname, name)
            if not p.exists():
                p.write_text(render(text, name), encoding="utf-8")
        mods = [render(m, name) for m in (t.modules or [f for f, _ in t.files])]
        main = render(t.settings.get("main", mods[0] if mods else ""), name)
        project = Project(folder, name, self.id, [], Path(main).stem, mods)
        settings = {k: (render(v, name) if isinstance(v, str) else v) for k, v in t.settings.items()}
        project.extra["retro"] = settings
        if not (folder / ".gitignore").exists():
            (folder / ".gitignore").write_text("_build/\n*.o\n", encoding="utf-8")
        project.save()
        return project

    # ------------------------------------------------------------ files (no forms)
    def code_file(self, form_name: str) -> str:
        return form_name if Path(form_name).suffix else f"{form_name}{self.code_ext}"

    def designer_file(self, form_name: str) -> str:
        return self.code_file(form_name)

    def generate_designer(self, form, user_code: str) -> str:
        return user_code

    def new_code(self, form, is_startup: bool) -> str:
        return ""

    def module_template(self, name: str) -> str:
        inc = {"dasm": f'include "{name}{self.code_ext}"', "ca65": f'(ca65 assembles every .s file; .import / '
               f'.export share labels)', "rgbds": f'INCLUDE "{name}{self.code_ext}" (or let rgblink link it)',
               "sjasmplus": f'INCLUDE "{name}{self.code_ext}"'}[self.dialect]
        return f"; {name}{self.code_ext} - {inc}\n"

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*{re.escape(name)}:?(\s|$)")

    def add_handler(self, code: str, name: str, form, args=None):
        text = code.rstrip() + f"\n\n{name}:\n"
        return text, len(text.splitlines())

    # ------------------------------------------------------------ run
    def find_interpreter(self, configured: str = "") -> str:
        return sys.executable or "python"

    def build_command(self, folder: Path, project: Project) -> str | None:
        return f'"{sys.executable}" -m radide.retro.dev.build "{Path(folder)}"'

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        import os
        from ...languages.bridgebase import IDE_ROOT
        env = dict(os.environ, PYTHONPATH=str(IDE_ROOT), PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
        return RunSpec(sys.executable, ["-u", "-m", "radide.retro.dev.run", str(folder)], Path(folder), env)

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str, breakpoints) -> RunSpec:
        return self.run_spec(folder, startup_form, interpreter)
