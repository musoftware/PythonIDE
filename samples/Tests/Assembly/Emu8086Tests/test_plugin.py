"""The emu8086 language plugin without a window: templates, run spec, completions, hover, outline, Go to
Definition, and the 16-bit source detector used by Open Folder.

Run:  python samples/Tests/Assembly/Emu8086Tests/test_plugin.py      (or with pytest)
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from radide.emu8086.detect import is_dos16_source  # noqa: E402
from radide.languages import get_plugin, plugin_for_file  # noqa: E402

CODE = """.model small
.data
msg db 'hi$'
count dw 3
.code
main proc
    mov ax, @data
    mov ds, ax
again:
    dec count
    jnz again
    mov ah, 4Ch
    int 21h
main endp
end main
"""


def test_registration():
    p = get_plugin("emu8086")
    assert p.code_ext == ".asm" and not p.case_sensitive and p.supports_debug and not p.has_forms
    assert plugin_for_file("main.asm", "emu8086") is p             # the project language wins for .asm
    assert {t[0] for t in p.project_templates()} == {"asm86_com", "asm86_exe", "asm86_inc", "asm86_colors",
                                                     "asm86_game"}


def test_create_and_run_spec():
    p = get_plugin("emu8086")
    with tempfile.TemporaryDirectory() as d:
        proj = p.create_new_project(Path(d) / "A", "A", "asm86_exe")
        assert proj.modules == ["main.asm"] and proj.startup == "main"
        spec = p.run_spec(Path(d) / "A", "main", "")
        assert spec.args[-1] == "main.asm" and "radide.emu8086" in spec.args


def test_intellisense():
    p = get_plugin("emu8086")
    names = {c.name for c in p.completions(CODE, 9, 4, Path("main.asm"))}
    assert {"mov", "loop", "ax", "msg", "count", "again", "main", "PRINT_NUM"} <= names
    assert "add dest, src" in p.hover("    add ax, bx", 0, 5, Path("x.asm"))
    assert "DOS" in p.hover("    int 21h", 0, 9, Path("x.asm"))
    assert "count" in p.hover(CODE, 9, 9, Path("main.asm"))          # a variable: its definition
    assert p.definition(CODE, 10, 9, Path("main.asm")) == ("main.asm", 8)
    outline = {(s["name"], s["kind"]) for s in p.document_symbols(CODE)}
    assert {("msg", "variable"), ("main", "function"), ("again", "label")} <= outline


def test_detector():
    assert is_dos16_source(CODE)
    assert is_dos16_source("org 100h\nmov ah, 9\nint 21h\nret\n")
    assert not is_dos16_source("bits 64\nsection .text\nglobal main\nmain:\n  mov rax, 1\n  ret\n")
    assert not is_dos16_source(".386\n.model flat, stdcall\ninvoke ExitProcess, 0\n")


if __name__ == "__main__":
    fails = 0
    for fn in (test_registration, test_create_and_run_spec, test_intellisense, test_detector):
        try:
            fn()
            print("PASS", fn.__name__)
        except AssertionError as e:
            fails += 1
            print("FAIL", fn.__name__, e)
    print(f"failures: {fails}")
    sys.exit(1 if fails else 0)
