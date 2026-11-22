"""Fortran 66 / 77 (fixed form) - console programs for old NASA and scientific code, built with
``gfortran -std=legacy -ffixed-form`` (radide/retro/legacy_fortran.py). The modern Fortran plugin
(fortran_bridge.py, .f90 + GUI Bridge) is untouched; this one owns the fixed-form extension ``.f``.

* New Project > Retro > Fortran 66/77: "Orbit Table" (an original Fortran 66 style program: circular orbits,
  Kepler's equation, arithmetic IF, computed GO TO, Hollerith FORMATs) or "Hello, Fortran 77".
* The editor shows rulers at columns 5 / 6 / 72, the continuation column and the label field coloured and the
  sequence numbers (73-80) greyed; hover explains the column and legacy statements.
* Project "fortran": {"preset": "legacy" | "f66" | "dec" | "strict", "flags": "..."} picks the gfortran options.
* Tools > Retro > Legacy Fortran: Card Deck View (the line as an IBM 029 punched card), Convert to Free Form (diff
  preview), Explain Legacy Constructs.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from ..model import Project
from .base import Completion, LanguagePlugin, RunSpec

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "Tests" / "Retro" / "LegacyFortran" / "OrbitTable"

HELLO = """C     {name} - A FORTRAN 77 PROGRAM IN FIXED FORM (COLUMNS 7-72).
C     F5 BUILDS IT WITH GFORTRAN -STD=LEGACY -FFIXED-FORM AND RUNS IT.
      PROGRAM HELLO
      INTEGER I
      REAL X
      WRITE (6,100)
  100 FORMAT (1X, 'HELLO FROM FORTRAN 77')
      DO 10 I = 1, 5
         X = SQRT(REAL(I))
         WRITE (6,110) I, X
  110    FORMAT (1X, 'SQRT(', I1, ') = ', F8.5)
   10 CONTINUE
      END
"""


class LegacyFortranPlugin(LanguagePlugin):
    id = "fortran-legacy"
    display_name = "Fortran 66/77 (fixed form, gfortran -std=legacy)"
    code_ext = ".f"
    case_sensitive = False
    line_comments = ["!"]
    block_comment = None
    string_quotes = ["'"]
    string_escapes = False
    supports_debug = False
    has_forms = False
    project_name_base = "Fortran77_"
    install_hint = "gfortran from MinGW-w64 (%LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64\\bin) or MSYS2."
    keywords = """PROGRAM SUBROUTINE FUNCTION BLOCK DATA END CALL RETURN STOP PAUSE CONTINUE GO TO IF THEN ELSE
        DO ASSIGN DIMENSION COMMON EQUIVALENCE EXTERNAL INTRINSIC IMPLICIT INTEGER REAL DOUBLE PRECISION COMPLEX
        LOGICAL CHARACTER PARAMETER SAVE ENTRY FORMAT READ WRITE PRINT OPEN CLOSE REWIND""".split()
    builtins = """ABS IABS SQRT EXP ALOG ALOG10 SIN COS TAN ATAN ATAN2 MOD AMOD MAX0 MIN0 AMAX1 AMIN1 FLOAT IFIX
        INT NINT SIGN DBLE SNGL""".split()

    def project_templates(self):
        return [("f66_orbits", "Orbit Table (Fortran 66)", "An original 1960s-style program: circular orbit speeds "
                 "and periods, an elliptic orbit with Kepler's equation, arithmetic IF, computed GO TO and Hollerith "
                 "FORMATs - with card sequence numbers in columns 73-80.", "SP_DriveHDIcon"),
                ("f77_hello", "Hello, Fortran 77", "A small fixed-form console program.", "rad:console")]

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        if (template or "f66_orbits") == "f66_orbits" and (SAMPLE / "ORBITS.f").is_file():
            target = folder / "ORBITS.f"
            if not target.exists():
                target.write_bytes((SAMPLE / "ORBITS.f").read_bytes())
            main, preset = "ORBITS.f", "f66"
        else:
            main, preset = "HELLO.f", "legacy"
            target = folder / main
            if not target.exists():
                target.write_text(HELLO.format(name=name.upper()), encoding="utf-8")
        project = Project(folder, name, self.id, [], Path(main).stem, [main])
        project.extra["fortran"] = {"preset": preset, "flags": ""}
        project.save()
        return project

    # ------------------------------------------------------------ code files
    def code_file(self, form_name: str) -> str:
        return form_name if Path(form_name).suffix.lower() in (".f", ".for", ".f77") else f"{form_name}.f"

    def designer_file(self, form_name: str) -> str:
        return self.code_file(form_name)

    def generate_designer(self, form, user_code: str) -> str:
        return user_code

    def new_code(self, form, is_startup: bool) -> str:
        return ""

    def module_template(self, name: str) -> str:
        return (f"C     {name.upper()} - SUBPROGRAMS (COMPILED WITH THE OTHER .F FILES OF THE PROJECT)\n"
                f"      SUBROUTINE {name.upper()[:6]}\n      RETURN\n      END\n")

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s+(SUBROUTINE|FUNCTION)\s+{re.escape(name)}\b", re.I)

    def add_handler(self, code: str, name: str, form, args=None):
        text = code.rstrip() + f"\n      SUBROUTINE {name.upper()}\n      RETURN\n      END\n"
        return text, len(text.splitlines()) - 2

    # ------------------------------------------------------------ run
    def find_interpreter(self, configured: str = "") -> str:
        return sys.executable or "python"

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        # started in the project folder: radide must be importable from there (python -m radide....)
        import os
        from ..paths import python_root
        env = dict(os.environ, PYTHONPATH=str(python_root()) + os.pathsep + os.environ.get("PYTHONPATH", ""))
        return RunSpec(sys.executable, ["-m", "radide.retro.legacy_fortran", "run", str(Path(folder))], Path(folder),
                       env)

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str, breakpoints) -> RunSpec:
        return self.run_spec(folder, startup_form, interpreter)

    # ------------------------------------------------------------ editor
    def monaco_language(self, path) -> dict | None:
        from ..retro.legacy_fortran import FIXED_EXT, monaco_language
        if path and Path(str(path)).suffix.lower() not in FIXED_EXT + ("",):
            return None
        return monaco_language()

    def hover(self, code, line, col, path=None, names=None) -> str:
        from ..retro import legacy_fortran as lf
        lines = code.splitlines()
        if line >= len(lines):
            return ""
        text = lines[line]
        out = [f"*column {col + 1}*: {lf.column_note(text, col + 1)}"]
        for ln, kind, en, ar in lf.analyze(code):
            if ln == line and kind != "implicit":
                try:
                    from ..i18n import language
                    out.append(ar if language() == "ar" else en)
                except Exception:  # noqa: BLE001
                    out.append(en)
        return "  \n".join(out)

    def document_symbols(self, code: str) -> list[dict]:
        out = []
        for i, raw in enumerate(code.splitlines()):
            if raw[:1] in ("C", "c", "*", "!"):
                continue
            m = re.match(r"^\s{6,}(?:(?:REAL|INTEGER|DOUBLE\s+PRECISION|LOGICAL|COMPLEX|CHARACTER\S*)\s+)?"
                         r"(PROGRAM|SUBROUTINE|FUNCTION|BLOCK\s+DATA)\s*(\w*)", raw, re.I)
            if m:
                out.append({"name": f"{m.group(1).upper()} {m.group(2).upper()}".strip(), "kind": "function",
                            "line": i, "detail": "", "children": []})
        return out

    def completions(self, code, line, col, path=None, names=None):
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(b, "function", "intrinsic") for b in self.builtins]
        seen = {c.name for c in out}
        for w in re.findall(r"\b[A-Z][A-Z0-9]{1,5}\b", code.upper()):
            if w not in seen:
                seen.add(w)
                out.append(Completion(w, "variable"))
        return out


PLUGIN = LegacyFortranPlugin()
