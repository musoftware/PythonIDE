"""Apollo AGC Program - assembly language of the Apollo Guidance Computer in the yaYUL syntax of Virtual AGC.

* New Project > Retro > Apollo AGC Program: "Hello DSKY" (clock on V16 N36 + a tiny keyboard handler) or an
  empty program with the interrupt vectors. Tools > Retro > Apollo AGC > Open Apollo Source... downloads the
  public-domain Comanche055 (Apollo 11 command module) / Luminary099 (lunar module) source on request.
* F5 assembles MAIN.agc with RAD IDE's built-in assembler (basic instructions + extracodes; errors go to the
  Error List) and runs it in RAD IDE's AGC emulator with the DSKY panel, breakpoints, F10 / F11 stepping,
  registers A / L / Q / Z and the erasable memory window (radide/agc/session.py). Programs with interpretive
  code (the flight programs) build with yaYUL and run in yaAGC + the same DSKY panel once Virtual AGC is
  installed (Tools > Retro > Apollo AGC > Virtual AGC Toolchain..., radide/agc/toolchain.py).
* Highlighting, IntelliSense with descriptions, hover (instructions, pseudo-ops, interpretive opcodes,
  registers, channels, V/N/P numbers in comments), F12 across the files of the program, outline by log section
  (radide/agc/intel.py).
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from ..model import Project
from .base import Completion, LanguagePlugin, RunSpec

EXAMPLES = Path(__file__).resolve().parent.parent / "agc" / "examples"

TEMPLATES = [
    ("agc_hello", "Hello DSKY (clock + keyboard)", "An original AGC program: VERB 16 NOUN 36 shows the time since "
     "start, VERB 35 ENTR tests the lamps, RSET clears OPR ERR. Runs in the built-in emulator and with yaYUL / "
     "yaAGC.", "SP_ComputerIcon"),
    ("agc_empty", "Empty AGC Program", "The interrupt vectors, the register names and an idle main loop - "
     "start from scratch.", "SP_FileIcon"),
]

EMPTY_MAIN = """# MAIN.agc - {name}: an Apollo Guidance Computer program (yaYUL syntax).
# F5: assemble and debug in RAD IDE's AGC emulator (DSKY panel, F10 / F11, registers A L Q Z).
# LABEL in column 1, then OPCODE and OPERAND; "#" starts a comment. Numbers are octal unless they
# contain 8 / 9 or end with D.

# Like the real hardware, RAD IDE's emulator restarts the AGC when the software stops "breathing":
#   NIGHT WATCHMAN - NEWJOB (address 67) not touched for 0.64 s
#   RUPT LOCK      - no interrupt for 140 ms (here T3RUPT comes every centisecond)
#   TC TRAP        - no TC / TCF for 5 ms, or nothing else but TC / TCF
# (Project "agc": {{"alarms": false}} turns these checks off in the emulator.)

A               EQUALS  0
L               EQUALS  1
Q               EQUALS  2
Z               EQUALS  5
ZERO            EQUALS  7
ARUPT           EQUALS  10
TIME3           EQUALS  26
NEWJOB          EQUALS  67

                SETLOC  100             # erasable variables
COUNT           ERASE                   # counted by the main loop
TICKS           ERASE                   # counted by T3RUPT (centiseconds)

                SETLOC  4000            # fixed-fixed memory: interrupt vectors (4 words each)
                INHINT                  # 4000 GOJAM: power on
                TCF     START
                NOOP
                NOOP
                RESUME                  # 4004 T6RUPT
                NOOP
                NOOP
                NOOP
                RESUME                  # 4010 T5RUPT
                NOOP
                NOOP
                NOOP
                DXCH    ARUPT           # 4014 T3RUPT: save A and L
                TCF     T3HAND
                NOOP
                NOOP
                RESUME                  # 4020 T4RUPT
                NOOP
                NOOP
                NOOP
                RESUME                  # 4024 KEYRUPT1
                NOOP
                NOOP
                NOOP

START           CA      ZERO
                TS      COUNT
                TS      TICKS
                CAF     T3LOAD          # first T3RUPT in a centisecond
                TS      TIME3
                RELINT
LOOP            CA      NEWJOB          # keep the Night Watchman happy
                INCR    COUNT           # watch COUNT and TICKS in the Erasable Memory window (F10 to step)
                TCF     LOOP

T3HAND          CAF     T3LOAD          # TIME3 overflows again in a centisecond
                TS      TIME3
                INCR    TICKS
                DXCH    ARUPT           # restore A and L
                RESUME

T3LOAD          OCT     37777
"""


def agc_settings(project) -> dict:
    s = {"assembler": "auto", "run": "emulator", "port": 19697, "yayul_args": ""}
    extra = (getattr(project, "extra", {}) or {}).get("agc")
    if isinstance(extra, dict):
        s.update({k: v for k, v in extra.items() if v is not None})
    return s


class AgcPlugin(LanguagePlugin):
    id = "agc-yul"
    display_name = "Apollo AGC Program (yaYUL)"
    code_ext = ".agc"
    case_sensitive = True
    line_comments = ["#"]
    block_comment = None
    string_quotes = []
    supports_debug = True
    has_forms = False
    project_name_base = "Apollo"
    install_hint = ("Nothing to install for the built-in assembler and emulator. Flight programs (interpretive "
                    "code) need Virtual AGC: Tools > Retro > Apollo AGC > Virtual AGC Toolchain...")

    @property
    def keywords(self):                     # type: ignore[override]
        from ..agc import isa
        return sorted(isa.all_opcodes() | set(isa.PSEUDO_DOCS))

    @property
    def builtins(self):                     # type: ignore[override]
        from ..agc import isa
        return sorted(isa.REGISTERS)

    # ------------------------------------------------------------ New Project
    def project_templates(self) -> list[tuple[str, str, str, str]]:
        return list(TEMPLATES)

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        modules = []
        if (template or "agc_hello") == "agc_hello" and (EXAMPLES / "hello_dsky").is_dir():
            for src in sorted((EXAMPLES / "hello_dsky").glob("*.agc")):
                dst = folder / src.name
                if not dst.exists():
                    shutil.copyfile(src, dst)
                modules.append(src.name)
            modules.sort(key=lambda n: (n != "MAIN.agc", n))
        else:
            main = folder / "MAIN.agc"
            if not main.exists():
                main.write_text(EMPTY_MAIN.format(name=name), encoding="utf-8")
            modules = ["MAIN.agc"]
        project = Project(folder, name, self.id, [], "MAIN", modules)
        project.extra["agc"] = {"assembler": "auto", "run": "emulator"}
        project.save()
        return project

    # ------------------------------------------------------------ code files
    def code_file(self, form_name: str) -> str:
        return form_name if form_name.lower().endswith(".agc") else f"{form_name}.agc"

    def designer_file(self, form_name: str) -> str:
        return self.code_file(form_name)

    def generate_designer(self, form, user_code: str) -> str:
        return user_code

    def new_code(self, form, is_startup: bool) -> str:
        return ""

    def module_template(self, name: str) -> str:
        return (f"# {name}.agc - a log section. Include it from MAIN.agc with the line:\n"
                f"# ${name}.agc\n# (it is assembled where that line is: SETLOC / BANK decide where it goes)\n\n")

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^{re.escape(name)}\s")

    def add_handler(self, code: str, name: str, form, args=None):
        text = code.rstrip() + f"\n\n{name:<16}CA      Q\n                RETURN\n"
        return text, len(text.splitlines()) - 2

    def on_file_removed(self, code: str, filename: str) -> str:
        rx = re.compile(rf"^\s*\${re.escape(filename)}\b.*$", re.I)
        return "\n".join(l for l in code.splitlines() if not rx.match(l)) + "\n"

    # ------------------------------------------------------------ run / debug
    def find_interpreter(self, configured: str = "") -> str:
        return sys.executable or "python"

    def startup_file(self, folder: Path, startup: str = "") -> str:
        folder = Path(folder)
        s = (startup or "MAIN").replace("\\", "/")
        name = s if s.lower().endswith(".agc") else s + ".agc"
        if (folder / name).exists():
            return name
        for cand in ("MAIN.agc", "main.agc"):
            if (folder / cand).exists():
                return cand
        files = sorted(folder.glob("*.agc"))
        return files[0].name if files else name

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        f = self.startup_file(folder, startup_form)
        # started in the project folder: radide must be importable from there (python -m radide....)
        import os
        from ..paths import python_root
        env = dict(os.environ, PYTHONPATH=str(python_root()) + os.pathsep + os.environ.get("PYTHONPATH", ""))
        return RunSpec(sys.executable, ["-m", "radide.agc", f, "--seconds", "3"], Path(folder), env)

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str, breakpoints) -> RunSpec:
        spec = self.run_spec(folder, startup_form, interpreter)
        spec.breakpoints = list(breakpoints or [])
        return spec

    def make_session(self, win, spec, debug: bool):
        """MainWindow._make_session hook: the built-in emulator + DSKY, or yaYUL / yaAGC (project setting)."""
        project = getattr(win, "project", None)
        if project is None or project.language != self.id:
            return None
        from ..agc.session import make_session
        bps = getattr(spec, "breakpoints", None)
        if bps is None:
            try:
                bps = win._all_breakpoints()
            except Exception:  # noqa: BLE001
                bps = []
        folder = Path(project.folder)
        return make_session(win, folder, self.startup_file(folder, project.startup), debug, bps,
                            agc_settings(project))

    # ------------------------------------------------------------ editor support
    def completions(self, code, line, col, path=None, names=None):
        try:
            from ..agc import intel
            return intel.completions(code, line, col, path)
        except Exception:  # noqa: BLE001 - IntelliSense must never break typing
            return [Completion(k, "keyword") for k in self.keywords]

    def hover(self, code, line, col, path=None, names=None) -> str:
        try:
            from ..agc import intel
            return intel.hover(code, line, col, path)
        except Exception:  # noqa: BLE001
            return ""

    def definition(self, code, line, col, path=None, names=None):
        try:
            from ..agc import intel
            return intel.definition(code, line, col, path)
        except Exception:  # noqa: BLE001
            return None

    def references(self, code, line, col, path=None, names=None):
        try:
            from ..agc import intel
            return intel.references(code, line, col, path)
        except Exception:  # noqa: BLE001
            return None

    def document_symbols(self, code: str) -> list[dict]:
        try:
            from ..agc import intel
            return intel.document_symbols(code)
        except Exception:  # noqa: BLE001
            return []

    def folding_ranges(self, code, path=None):
        from ..agc import intel
        return intel.folding_ranges(code)

    def monaco_language(self, path) -> dict | None:
        if path and Path(str(path)).suffix.lower() not in (".agc", ""):
            return None
        from ..agc import intel
        return intel.monaco_language()


PLUGIN = AgcPlugin()
