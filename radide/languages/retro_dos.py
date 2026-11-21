"""DOS Program (DOSBox-X) - old MS-DOS programs and games the user owns, and legacy DOS development.

* New Project > Retro > DOS Program: an existing DOS program folder (copy your game / application in), an 8086
  .COM in assembly (built by NASM on Windows), Turbo Pascal / Free Pascal, Turbo C / Open Watcom C or QBasic
  sources (built inside DOSBox-X with the compiler folder set in Project > DOS Settings).
* File > Open Folder on a folder of DOS executables offers "DOS program (DOSBox-X)" (radide/features/retro_emu.py).
* F5 / Ctrl+F5 run ``python -m radide.retro.emu dos <folder>``: RAD IDE writes ``.radide/dosbox-x.conf`` from the
  project's ``"dos"`` block (program, cycles, memory, machine, sound card, mounts) and starts DOSBox-X
  (downloaded on request: Tools > Retro Emulators...). Stop closes DOSBox-X.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from ..model import Project
from .base import LanguagePlugin, RunSpec

TEMPLATES = [
    ("dos_existing", "Existing DOS Program", "Run an MS-DOS program or game you own in DOSBox-X: copy its files into "
     "the project folder, pick the .EXE in Project > DOS Settings, press F5.", "SP_DriveFDIcon"),
    ("dos_asm", "DOS .COM in Assembly (NASM)", "An 8086 .COM program: NASM assembles it on Windows, F5 runs it in "
     "DOSBox-X.", "SP_ComputerIcon"),
    ("dos_pascal", "Turbo Pascal / Free Pascal", "A Pascal program built inside DOSBox-X with the DOS compiler folder "
     "you set (Turbo Pascal 7 or Free Pascal go32v2).", "SP_FileIcon"),
    ("dos_c", "Turbo C / Open Watcom C", "A C program built inside DOSBox-X with Turbo C / Borland C or Open Watcom.",
     "SP_FileIcon"),
    ("dos_qbasic", "QBasic / QuickBASIC", "A BASIC program run by QBASIC /RUN (your copy) or compiled by FreeBASIC "
     "for DOS.", "SP_FileIcon"),
]

ASM = """; {name} - an 8086 .COM program for DOS (RAD IDE: NASM builds it, F5 runs it in DOSBox-X)
        org 100h

start:  mov ah, 09h             ; DOS: print the $-terminated string at DS:DX
        mov dx, msg
        int 21h
        mov ah, 00h             ; BIOS: wait for a key
        int 16h
        mov ax, 4C00h           ; DOS: exit with code 0
        int 21h

msg     db 'Hello from {name}! Press a key...', 13, 10, '$'
"""
PASCAL = """program {name};
{{ Built inside DOSBox-X: set Project > DOS Settings > Toolchain folder to Turbo Pascal 7 or Free Pascal (go32v2). }}
uses Crt;
var i: Integer;
begin
  ClrScr;
  for i := 1 to 10 do
  begin
    TextColor(i);
    WriteLn('Hello from {name}, line ', i);
  end;
  WriteLn('Press a key...');
  ReadKey;
end.
"""
C = """/* {name} - built inside DOSBox-X with Turbo C (TCC) or Open Watcom (WCL): Project > DOS Settings */
#include <stdio.h>
#include <conio.h>

int main(void)
{{
    int i;
    for (i = 1; i <= 10; i++)
        printf("Hello from {name}, line %d\\n", i);
    printf("Press a key...");
    getch();
    return 0;
}}
"""
BASIC = """' {name} - run with QBASIC /RUN (your copy) or FreeBASIC for DOS: Project > DOS Settings
CLS
FOR i = 1 TO 10
    COLOR i
    PRINT "Hello from {name}, line"; i
NEXT i
PRINT "Press a key..."
DO: LOOP WHILE INKEY$ = ""
"""
README = """{name} - DOS Program (DOSBox-X)

Copy the files of an MS-DOS program or game you own into this folder (sub-folders are fine), then choose the
program to start in Project > DOS Settings (RAD IDE guesses it: GAME.EXE, the only .EXE, ...).
F5 starts it in DOSBox-X with the settings of project.radproj ("dos": cycles, memory, sound card, mounts).
Do not put games you do not own here.
"""
SOURCES = {"dos_asm": ("HELLO.ASM", ASM), "dos_pascal": ("MAIN.PAS", PASCAL), "dos_c": ("MAIN.C", C),
           "dos_qbasic": ("MAIN.BAS", BASIC)}
IDE_ROOT = str(Path(__file__).resolve().parents[2])


class RetroDosPlugin(LanguagePlugin):
    id = "retro-dos"
    display_name = "DOS Program (DOSBox-X)"
    code_ext = ".bat"
    case_sensitive = False
    line_comments = ["REM ", "::"]
    block_comment = None
    keywords = ["echo", "set", "if", "goto", "call", "for", "in", "do", "rem", "pause", "cd", "mount", "exit",
                "cls", "path", "errorlevel", "exist", "not", "shift"]
    builtins = []
    supports_debug = False
    has_forms = False
    project_name_base = "DosProgram"
    install_hint = ("DOSBox-X runs the program: Tools > Retro Emulators... downloads the official portable build "
                    "(GPL) on request.")

    # ------------------------------------------------------------ New Project
    def project_templates(self) -> list[tuple[str, str, str, str]]:
        return list(TEMPLATES)

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        template = template or "dos_existing"
        modules, startup = [], ""
        dos = {"program": "", "cycles": "auto", "machine": "svga_s3", "memsize": 16, "sound": "sb16"}
        safe = "".join(c for c in name if c.isalnum())[:8] or "PROGRAM"
        if template in SOURCES:
            fname, text = SOURCES[template]
            p = folder / fname
            if not p.exists():
                p.write_text(text.format(name=safe), encoding="utf-8", newline="\r\n")
            modules, startup, dos["program"] = [fname], fname, fname
            if template == "dos_qbasic":
                dos["cycles"] = "fixed 20000"
        else:
            r = folder / "README.txt"
            if not r.exists():
                r.write_text(README.format(name=name), encoding="utf-8")
            modules = ["README.txt"]
        project = Project(folder, name, self.id, [], startup, modules)
        project.extra["dos"] = dos
        project.save()
        return project

    # ------------------------------------------------------------ files
    def code_file(self, form_name: str) -> str:
        return form_name

    def designer_file(self, form_name: str) -> str:
        return form_name

    def generate_designer(self, form, user_code: str) -> str:
        return user_code

    def new_code(self, form, is_startup: bool) -> str:
        return ""

    def module_template(self, name: str) -> str:
        return "@echo off\nREM {} - a DOS batch file\n".format(name)

    def find_handler(self, code: str, name: str) -> int:
        return -1

    def add_handler(self, code: str, name: str, form, args=None):
        return code, 0

    # ------------------------------------------------------------ run
    def find_interpreter(self, configured: str = "") -> str:
        return sys.executable or "python"

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        target = Path(folder) / startup_form if startup_form and (Path(folder) / startup_form).is_file() \
            else Path(folder)
        env = {"PYTHONPATH": IDE_ROOT + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")}
        return RunSpec(sys.executable, ["-m", "radide.retro.emu", "dos", str(target)], Path(folder), env)

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str, breakpoints=None) -> RunSpec:
        return self.run_spec(folder, startup_form, interpreter)


PLUGIN = RetroDosPlugin()
