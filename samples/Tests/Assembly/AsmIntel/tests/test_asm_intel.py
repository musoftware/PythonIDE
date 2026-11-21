"""Unit tests of the assembly IntelliSense (radide/asm_intel) - no Qt, no IDE.

Run:  python samples/Tests/Assembly/AsmIntel/tests/test_asm_intel.py      (or with pytest)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLE = HERE.parent
ROOT = SAMPLE.parents[3]
sys.path.insert(0, str(ROOT))

from radide.asm_intel import apis, directives, engine, index, isa, monarch, snippets  # noqa: E402
from radide.asm_intel.plugin import AsmPluginOverlay, overlay_for  # noqa: E402

NASM = SAMPLE / "nasm" / "main.asm"
INC = SAMPLE / "nasm" / "mathlib.inc"
MASM = SAMPLE / "masm" / "hello32.asm"
FASM = SAMPLE / "fasm" / "hello.fasm"
GAS_ATT = SAMPLE / "gas" / "hello_linux.s"
GAS_INTEL = SAMPLE / "gas" / "hello_win.S"


def text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def pos(src: str, needle: str, offset: int = 0) -> tuple[int, int]:
    """(line, col) of the first occurrence of *needle* (+offset characters)."""
    i = src.index(needle) + offset
    line = src.count("\n", 0, i)
    col = i - (src.rfind("\n", 0, i) + 1)
    return line, col


def labels(items) -> set[str]:
    return {c.name for c in items}


# ---------------------------------------------------------------------------- tables
def test_tables():
    assert len(isa.INSTRUCTIONS) > 700
    for m in ("mov", "lea", "jne", "cmovge", "setz", "addps", "vaddps", "vfmadd231pd", "pshufb", "fld", "popcnt"):
        assert m in isa.INSTRUCTIONS, m
    assert isa.INSTRUCTIONS["jz"].alias_of == "je"
    assert "ZF" in isa.INSTRUCTIONS["je"].flags
    assert isa.att_base("movq") == "mov" and isa.att_base("movzbl") == "movzx" and isa.att_base("addl") == "add"
    assert isa.register("%rax").size == 64 and isa.register("r8d").family == "r8"
    assert "rax" not in isa.registers_for(32) and "eax" in isa.registers_for(32)
    assert apis.lookup("MessageBoxA").dll == "user32"
    assert apis.lookup("__imp_ExitProcess").name == "ExitProcess"
    assert apis.lookup("_MessageBoxA@16").name == "MessageBoxA"
    assert apis.lookup("MessageBoxW").params[1][0] == "LPCWSTR"
    mb = apis.lookup("MessageBoxA")
    assert apis.arg_locations(mb, "win64") == ["rcx", "rdx", "r8", "r9"]
    assert apis.arg_locations(apis.lookup("CreateWindowExA"), "win64")[4] == "[rsp+20h]"
    assert apis.arg_locations(apis.lookup("pow"), "win64") == ["xmm0", "xmm1"]
    assert apis.arg_locations(mb, "sysv")[0] == "rdi"
    assert apis.arg_locations(mb, "x86")[0] == "push #4"
    assert "ret 16" in apis.convention(mb, "x86")
    assert "cdecl" in apis.convention(apis.lookup("printf"), "x86")
    for d in ("nasm", "masm", "fasm", "gas"):
        assert directives.directive_names(d), d
        assert snippets.snippets(d, "win64") and snippets.snippets(d, "x86")


# ---------------------------------------------------------------------------- dialect detection / parser
def test_dialects():
    assert index.detect_dialect(NASM, text(NASM)) == "nasm"
    assert index.detect_dialect(MASM, text(MASM)) == "masm"
    assert index.detect_dialect(FASM, text(FASM)) == "fasm"
    assert index.detect_dialect(GAS_ATT, text(GAS_ATT)) == "gas"
    assert index.detect_dialect(GAS_INTEL, text(GAS_INTEL)) == "gas"
    assert index.gas_syntax(text(GAS_ATT)) == "att" and index.gas_syntax(text(GAS_INTEL)) == "intel"

    class P:
        id = "asm-masm-console"
    # a loose file: the text decides (the plugin is only the first one registered for .asm)
    assert index.detect_dialect(NASM, text(NASM), P()) == "nasm"
    assert index.detect_dialect(Path("x.asm"), "", P()) == "masm"         # no clue in the text: the plugin
    import tempfile
    with tempfile.TemporaryDirectory() as d:                              # inside a project: the plugin wins
        (Path(d) / "project.radproj").write_text('{"name": "T", "language": "asm-x"}', encoding="utf-8")
        f = Path(d) / "main.asm"
        f.write_text(text(NASM), encoding="utf-8")
        assert index.detect_dialect(f, text(NASM), P()) == "masm"
        (Path(d) / "project.radproj").write_text('{"name": "T", "language": "asm-fasm"}', encoding="utf-8")
        assert index.detect_dialect(f, text(NASM), P()) == "fasm"           # project setting first
    assert index.abi_of(text(NASM), "nasm") == "win64"
    assert index.abi_of(text(MASM), "masm") == "x86"
    assert index.abi_of(text(GAS_ATT), "gas") == "sysv"
    assert index.code_bits("org 100h\nmov ah, 9\nint 21h", "nasm") == 16


def test_parser():
    m = index.parse(text(NASM), "nasm", str(NASM))
    by = {s.full: s for s in m.symbols}
    assert by["main"].kind == "proc"                 # global main
    assert by["main.loop"].kind == "local"
    assert by["show_message"].kind == "label"
    assert by["STD_OUTPUT_HANDLE"].kind == "const"
    assert by["message"].kind == "data" and '"Hello from NASM!"' in by["message"].detail
    assert by["POINT"].kind == "struct" and by["POINT.x"].kind == "field"
    assert "MessageBoxA" in m.externs and ("mathlib.inc", 10) in m.includes
    assert by["main"].doc.startswith("Program entry point")
    mi = index.parse(text(INC), "nasm")
    sq = next(s for s in mi.symbols if s.name == "SQUARE")
    assert sq.kind == "macro" and sq.params == ["%1", "%2"] and sq.end_line > sq.line
    mm = index.parse(text(MASM), "masm")
    add2 = next(s for s in mm.symbols if s.name == "AddTwo")
    assert add2.kind == "proc" and add2.params == ["a", "b"] and add2.end_line > add2.line
    assert any(s.kind == "var" and s.name == "tries" and s.parent == "ShowTwice" for s in mm.symbols)
    assert any(s.kind == "field" and s.name == "left" and s.parent == "RECT2" for s in mm.symbols)
    mf = index.parse(text(FASM), "fasm")
    assert {"ExitProcess", "MessageBox"} <= set(mf.externs)
    assert any(s.full == "ShowGreeting.next" for s in mf.symbols)
    assert any(s.kind == "macro" and s.name == "show_box" and s.params == ["text", "caption"] for s in mf.symbols)
    mg = index.parse(text(GAS_ATT), "gas")
    assert any(s.name == "_start" and s.kind == "proc" for s in mg.symbols)
    assert any(s.name == "syscall3" and s.kind == "macro" and s.params == ["num", "a", "b", "c"] for s in mg.symbols)
    assert any(s.name == ".Lagain" and s.full == ".Lagain" for s in mg.symbols)
    assert any(s.name == "msg" and s.kind == "data" for s in mg.symbols)


# ---------------------------------------------------------------------------- completions
def test_completions_nasm():
    src = text(NASM)
    # mnemonic position: an empty line inside main
    lines = src.split("\n")
    ln = lines.index("    call    show_message")
    items = engine.completions(src, ln, 4, NASM)
    names = labels(items)
    assert {"mov", "vaddps", "SQUARE", "CLAMP", "section", "%define"} <= names, names & {"SQUARE"}
    assert any(c.kind == "snippet" and c.name == "call64" and c.snippet for c in items)
    assert "pushad" not in names                        # not encodable in 64-bit code
    # operand position after "call": labels, externs and Win32 APIs (auto extern)
    items = engine.completions(src, ln, len("    call    "), NASM)
    names = labels(items)
    assert {"show_message", "main", "MessageBoxA", "ExitProcess", "CreateFileA"} <= names
    cf = next(c for c in items if c.name == "CreateFileA")
    assert cf.edits and cf.edits[0]["text"] == "extern CreateFileA\n"
    mb = next(c for c in items if c.name == "MessageBoxA")
    assert not mb.edits                                 # already declared
    # local label inside main (".loop") and registers / data / constants as operands
    jl = lines.index("    jl      .loop")
    items = engine.completions(src, jl, len("    jl      ."), NASM)
    assert ".loop" in labels(items)
    mv = lines.index("    mov     ecx, STD_OUTPUT_HANDLE")
    names = labels(engine.completions(src, mv, len("    mov     ecx, "), NASM))
    assert {"rax", "r9d", "xmm0", "STD_OUTPUT_HANDLE", "message", "line_len", "MAX_COUNT", "qword"} <= names
    # struc fields
    probe = src + "\n    mov eax, [origin + POINT."
    items = engine.completions(probe, probe.count("\n"), len("    mov eax, [origin + POINT."), NASM)
    assert {"POINT.x", "POINT.y"} <= labels(items)
    # %-directives only after %
    probe = src + "\n%de"
    names = labels(engine.completions(probe, probe.count("\n"), 3, NASM))
    assert "%define" in names and "mov" not in names
    # nothing inside comments
    cl = lines.index("    sub     rsp, 40                 ; shadow space (32) + alignment (8)")
    assert engine.completions(src, cl, len(lines[cl]) - 2, NASM) == []


def test_completions_other_dialects():
    src = text(MASM)
    lines = src.split("\n")
    ln = lines.index("    mov     tries, 0")
    names = labels(engine.completions(src, ln, len("    mov     "), MASM))
    assert {"tries", "szText", "counter", "dword ptr", "offset", "eax", "MB_OK"} <= names
    assert "a" not in names                           # AddTwo's parameter is out of scope here
    names = labels(engine.completions(src, ln, 4, MASM))
    assert {".if", "invoke", "proc", "program32"} <= names
    probe = src.replace("    mov     counter, eax", "    mov     eax, area.")
    pl, pc = pos(probe, "area.", 5)
    assert {"area.left", "area.top"} <= labels(engine.completions(probe, pl, pc, MASM))
    src = text(GAS_ATT)
    lines = src.split("\n")
    ln = lines.index("    decl    %ebx")
    items = engine.completions(src, ln, len("    decl    %e"), GAS_ATT)
    assert "%ebx" in labels(items) and "%eax" in labels(items) and "%rax" not in labels(items)   # "%e" typed
    names = labels(engine.completions(src, ln, 4, GAS_ATT))
    assert {"movq", "addl", ".globl", ".asciz", "syscall3"} <= names
    src = text(FASM)
    lines = src.split("\n")
    ln = lines.index("    invoke  ExitProcess, 0")
    names = labels(engine.completions(src, ln, len("    invoke  "), FASM))
    assert {"ExitProcess", "MessageBox", "ShowGreeting"} <= names


# ---------------------------------------------------------------------------- hover
def test_hover():
    src = text(NASM)
    h = engine.hover(src, *pos(src, "lea     eax", 1), NASM)
    assert "**LEA**" in h and "intel.com" in h
    h = engine.hover(src, *pos(src, "jl      .loop", 1), NASM)
    assert "SF<>OF" in h and "reads SF OF" in h
    h = engine.hover(src, *pos(src, "mov     rbx, rax", 9), NASM)
    assert "**RBX**" in h and "callee-saved" in h
    h = engine.hover(src, *pos(src, "call    MessageBoxA", 10), NASM)
    assert "MessageBoxA(HWND hWnd" in h and "`rcx`" in h and "shadow space" in h and "learn.microsoft.com" in h
    h = engine.hover(src, *pos(src, "SQUARE  eax", 2), NASM)
    assert "macro" in h and "mathlib.inc" in h and "dest = src * src" in h
    h = engine.hover(src, *pos(src, "default rel", 2), NASM)
    assert "RIP-relative" in h and "nasm.us" in h
    h = engine.hover(src, *pos(src, "equ 40h", 5), NASM)
    assert "= 64" in h and "0x40" in h
    h = engine.hover(src, *pos(src, "call    show_message", 10), NASM)
    assert "show_message" in h and "Shows the greeting" in h
    msrc = text(MASM)
    h = engine.hover(msrc, *pos(msrc, "invoke  MessageBoxA", 10), MASM)
    assert "stdcall" in h and "push #4" in h
    gsrc = text(GAS_ATT)
    h = engine.hover(gsrc, *pos(gsrc, "decl", 1), GAS_ATT)
    assert "**DEC**" in h and "AT&T" in h
    h = engine.hover(gsrc, *pos(gsrc, "%rdi", 2), GAS_ATT)
    assert "**RDI**" in h
    h = engine.hover(text(GAS_INTEL), *pos(text(GAS_INTEL), "call    printf", 10), GAS_INTEL)
    assert "printf" in h and "Microsoft x64" in h


# ---------------------------------------------------------------------------- signature help
def test_signatures():
    src = text(NASM)
    sig = engine.calltip(src, *pos(src, "lea     r8, [title]", 12), NASM)   # before call MessageBoxA
    assert isinstance(sig, dict) and sig["label"].startswith("MessageBoxA(") and sig["activeParameter"] == 2
    sig = engine.calltip(src, *pos(src, "mov     r8d, line_len", 12), NASM)  # before WriteConsoleA
    assert sig["label"].startswith("WriteConsoleA(") and sig["activeParameter"] == 2
    sig = engine.calltip(src, *pos(src, "SQUARE  eax, esi", 13), NASM)
    assert sig["label"].startswith("SQUARE") and sig["activeParameter"] == 1
    sig = engine.calltip(src, *pos(src, "cmp     esi, 3", 13), NASM)
    assert sig["label"].startswith("CMP") and sig["activeParameter"] == 1
    msrc = text(MASM)
    sig = engine.calltip(msrc, *pos(msrc, "invoke  MessageBoxA, 0, addr szText,", 34), MASM)
    assert sig["label"].startswith("MessageBoxA(") and sig["activeParameter"] == 1
    sig = engine.calltip(msrc, *pos(msrc, "invoke  AddTwo, 2,", 18), MASM)
    assert sig["label"] == "AddTwo a, b" and sig["activeParameter"] == 1
    push_src = "bits 32\nsection .text\nf:\n    push 0\n    push cap\n    push txt\n    push 0\n    call _MessageBoxA@16\n"
    sig = engine.calltip(push_src, 5, 9, None, dialect="nasm")
    assert sig["label"].startswith("MessageBoxA(") and sig["activeParameter"] == 1
    gsrc = text(GAS_ATT)
    sig = engine.calltip(gsrc, *pos(gsrc, "movq    $\\num, %rax", 12), GAS_ATT)
    assert sig["label"].startswith("MOV") and "AT&T" in sig["documentation"]


# ---------------------------------------------------------------------------- definition / references / outline
def test_definition_references():
    src = text(NASM)
    d = engine.definition(src, *pos(src, "SQUARE  eax", 2), NASM)
    assert d and Path(d[0]).name == "mathlib.inc" and d[1] == 8
    d = engine.definition(src, *pos(src, "jl      .loop", 10), NASM)
    assert d == (str(NASM), src.split("\n").index(".loop:"))
    d = engine.definition(src, *pos(src, '%include "mathlib.inc"', 12), NASM)
    assert d and Path(d[0]).name == "mathlib.inc" and d[1] == 0
    d = engine.definition(src, *pos(src, "mov     ecx, STD_OUTPUT_HANDLE", 15), NASM)
    assert d == (str(NASM), 17)
    refs = engine.references(src, *pos(src, "call    show_message", 10), NASM)
    assert len([r for r in refs if Path(r[0]) == NASM]) == 2
    refs = engine.references(src, *pos(src, ".loop:", 1), NASM)
    assert len(refs) == 2
    refs = engine.references(src, *pos(src, "SQUARE  eax", 2), NASM)
    files = {Path(r[0]).name for r in refs}
    assert files == {"main.asm", "mathlib.inc"}
    msrc = text(MASM)
    refs = engine.references(msrc, *pos(msrc, "mov     tries, 0", 9), MASM)
    assert len(refs) == 4                                  # LOCAL tries + 3 uses
    refs = engine.references(msrc, *pos(msrc, "szTitle     BYTE", 1), MASM)
    assert len(refs) == 3


def test_outline_folding():
    syms = engine.document_symbols(text(NASM), NASM)
    names = [s["name"] for s in syms]
    assert ".data" in names and ".text" in names
    text_sec = next(s for s in syms if s["name"] == ".text")
    main = next(c for c in text_sec["children"] if c["name"] == "main")
    assert main["kind"] == "function" and main["children"][0]["name"] == ".loop"
    syms = engine.document_symbols(text(MASM), MASM)
    code = next(s for s in syms if s["name"].lower() == ".code")
    add2 = next(c for c in code["children"] if c["name"] == "AddTwo")
    assert {c["name"] for c in add2["children"]} == {"a", "b"}
    folds = engine.folding_ranges(text(INC), INC)
    assert any(f["start"] == 8 and f["end"] == 11 for f in folds)          # %macro SQUARE ... %endmacro
    assert any(f["start"] == 2 for f in folds)                               # %ifndef ... %endif
    folds = engine.folding_ranges(text(MASM), MASM)
    src = text(MASM).split("\n")
    p0 = src.index("AddTwo PROC a:DWORD, b:DWORD")
    assert any(f["start"] == p0 and f["end"] == src.index("AddTwo ENDP") for f in folds)
    folds = engine.folding_ranges(text(FASM), FASM)
    assert any(f["start"] == text(FASM).split("\n").index("proc ShowGreeting count") for f in folds)
    folds = engine.folding_ranges(text(NASM), NASM)
    assert any(f["kind"] == "comment" and f["start"] == 0 for f in folds)


# ---------------------------------------------------------------------------- Monaco grammar / overlay
def test_monarch_and_overlay():
    for d in ("nasm", "masm", "fasm", "gas"):
        spec = monarch.language_spec(d, d == "gas")
        json.dumps(spec)                                      # JSON-safe for radRegisterMonarch
        assert spec["id"] == f"rad-asm-{d}" and "mov" in spec["monarch"]["instructions"]
        assert spec["conf"]["comments"]["lineComment"] in (";", "#")

    class Base:
        id = "c-bridge"
        keywords = ["int"]
        line_comments = ["//"]

        def completions(self, *a, **k):
            return []
    ov = overlay_for(Base(), NASM)
    assert isinstance(ov, AsmPluginOverlay) and ov.id == "c-bridge" and ov.line_comments == [";"]
    assert ov.monaco_language(NASM)["id"] == "rad-asm-nasm"
    assert ov.document_symbols(text(NASM))
    assert overlay_for(Base(), Path("x.c")) is None
    assert overlay_for(ov, NASM) is None                      # already assembly-aware
    assert "mov" in labels(ov.completions(text(NASM), 40, 4, NASM))
    assert overlay_for(Base(), SAMPLE / "nasm" / "mathlib.inc") is not None   # .inc next to .asm files


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            import traceback
            traceback.print_exc()
            print(f"FAIL {t.__name__}: {e}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main())
