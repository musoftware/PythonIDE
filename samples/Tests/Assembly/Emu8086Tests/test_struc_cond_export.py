"""8086 emulator: STRUC / ENDS, conditional assembly (IF / IFE / IFDEF / IFNDEF / IFB / IFNB / IFIDN / IFDIF,
ELSEIF..., ELSE, ENDIF) and the export to DOS .COM / MZ .EXE files.

The exported files are checked byte by byte against the MZ / COM rules and loaded back the way DOS loads them
(radide.emu8086.dosexe.load_dos_file, at load segments different from the assembler's) and run in the
emulator: the output must equal the output of the program run from source. That covers every sample in
samples/Tests/Assembly/Emu8086* plus a program with far pointers and several segments.

Run:  python samples/Tests/Assembly/Emu8086Tests/test_struc_cond_export.py      (or with pytest)
"""
import os
import struct
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from radide.emu8086 import dosexe                       # noqa: E402
from radide.emu8086.assembler import assemble           # noqa: E402
from radide.emu8086.machine import Machine, run_source  # noqa: E402

SAMPLES = HERE.parent


def run(src, keys=""):
    r = run_source(src, keys=keys)
    assert not r["errors"], r["errors"]
    return r


def var(r, name):
    v = next(x for x in r["program"].variables if x.name.lower() == name.lower())
    return r["machine"].read_var(v)


def errors(src):
    return [e.code for e in assemble(src).errors]


EXE_HEAD = ".model small\n.stack 100h\n.data\n"
EXE_CODE = ".code\nmain proc\n    mov ax, @data\n    mov ds, ax\n"
EXE_END = "    mov ax, 4C00h\n    int 21h\nmain endp\nend main\n"


# ---------------------------------------------------------------- STRUC
def test_struc_fields_and_instances():
    src = EXE_HEAD + """point struc
  x   dw 0
  y   dw 5
  tag db 'P'
  pad db 3 dup (?)
point ends
p1   point <10, 20, 'A'>
p2   point <>
pts  point 3 dup (<1, 2>)
res  dw 8 dup (0)
""" + EXE_CODE + """    mov ax, p1.y
    mov res, ax              ; 20
    mov ax, p2.y
    mov res+2, ax            ; 5 (default)
    mov bx, offset pts
    mov ax, [bx].y
    mov res+4, ax            ; 2
    mov ax, (point ptr [bx+8]).x
    mov res+6, ax            ; 1 (second element: 8 bytes further)
    mov res+8, point.tag     ; 4 (field offset)
    mov res+10, size point   ; 8
    mov res+12, length pts   ; 3
    mov res+14, size pts     ; 24
    mov al, p1.tag
    mov dl, al
    mov ah, 2
    int 21h
    mov p2.tag, 'Z'
    mov dl, p2.tag
    int 21h
""" + EXE_END
    r = run(src)
    assert r["output"] == "AZ", r["output"]
    assert var(r, "res") == [20, 5, 2, 1, 4, 8, 3, 24], var(r, "res")


def test_struc_nested_and_string_field():
    src = EXE_HEAD + """name8 struc
  txt db 8 dup ('.')
  fin db '$'
name8 ends
person struc
  nm  name8 <>
  age db 0
person ends
who person <>
""" + EXE_CODE + """    mov who.age, 42
    mov al, who.age
    mov ah, 0
    lea dx, who.nm
    mov ah, 9
    int 21h
""" + EXE_END
    r = run(src)
    assert r["output"] == "........", repr(r["output"])
    p = r["program"]
    assert next(v for v in p.variables if v.name == "who").offset == 0


def test_struc_errors():
    assert "E-STRUC-OPEN" in errors(".model small\n.data\ns struc\n a db 0\n.code\nmain:\n mov ax, 1\nend main\n")


# ---------------------------------------------------------------- conditional assembly
def test_conditionals():
    src = EXE_HEAD + """DEBUG equ 1
LEVEL = 3
res dw 10 dup (0)
""" + EXE_CODE + """IF DEBUG
    mov res, 1
ELSE
    mov res, 99
ENDIF
IFE DEBUG
    mov res+2, 99
ELSE
    mov res+2, 2
ENDIF
IFDEF LEVEL
    mov res+4, 3
ENDIF
IFNDEF NOT_THERE
    mov res+6, 4
ENDIF
IF LEVEL GT 5
    mov res+8, 99
ELSEIF LEVEL EQ 3
    mov res+8, 5
ELSE
    mov res+8, 98
ENDIF
IF 0
  IF 1
    mov res+10, 99
  ENDIF
ELSE
  IFDEF DEBUG
    mov res+10, 6
  ENDIF
ENDIF
IFIDNI <abc>, <ABC>
    mov res+12, 7
ENDIF
IFDIF <abc>, <abd>
    mov res+14, 8
ENDIF
""" + EXE_END
    r = run(src)
    assert var(r, "res")[:8] == [1, 2, 3, 4, 5, 6, 7, 8], var(r, "res")


def test_conditionals_in_macros():
    src = EXE_HEAD + "res dw 4 dup (0)\n" + """.code
store macro where, value
IFB <value>
    mov where, 77
ELSE
    mov where, value
ENDIF
endm
main proc
    mov ax, @data
    mov ds, ax
    store res
    store res+2, 5
""" + EXE_END
    r = run(src)
    assert var(r, "res")[:2] == [77, 5], var(r, "res")


def test_conditional_errors():
    assert "E-COND" in errors("org 100h\nendif\nmov ax, 1\nret\n")
    assert "E-COND-OPEN" in errors("org 100h\nif 1\nmov ax, 1\nret\n")


# ---------------------------------------------------------------- export
def check_mz(data: bytes):
    assert data[:2] == b"MZ"
    cblp, cp, nrel, hparas, minalloc, maxalloc, ss, sp, _cs, ip, cs, lfarlc = struct.unpack_from("<12H", data, 2)
    size = (cp - 1) * 512 + cblp if cblp else cp * 512
    assert size == len(data), (size, len(data))
    assert lfarlc == 0x1C and hparas * 16 >= 0x1C + 4 * nrel and maxalloc == 0xFFFF
    img = len(data) - hparas * 16
    for k in range(nrel):
        off, seg = struct.unpack_from("<HH", data, lfarlc + 4 * k)
        assert seg * 16 + off + 2 <= img
    return nrel, ip, cs, ss, sp


def run_loaded(data, name, keys="", load_seg=0x0900):
    m = Machine()
    m.load(dosexe.load_dos_file(data, name, load_seg))
    m.record_history = False
    m.feed_keys(keys)
    info = m.run(2_000_000)
    return m, info


def test_export_all_samples():
    keys = {"Emu8086StringReverse": "RAD IDE\r", "Emu8086InputNumber": "1x2a34\r"}
    seen = 0
    for d in sorted(SAMPLES.glob("Emu8086*")):
        src = d / "main.asm"
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8")
        prog = assemble(text, str(src))
        ref = run_source(text, keys=keys.get(d.name, ""), filename=str(src))
        if prog.com:
            data = dosexe.com_image(prog)
            assert data[:1] != b"MZ"
        else:
            data = dosexe.mz_image(text, str(src))
            check_mz(data)
        for seg in (0x0900, 0x2345):
            m, info = run_loaded(data, src.name, keys.get(d.name, ""), seg)
            assert info.reason == ref["reason"], (d.name, info.reason, ref["reason"])
            assert m.output == ref["output"], (d.name, seg, m.output, ref["output"])
        seen += 1
    assert seen >= 9


def test_export_com_bytes():
    prog = assemble("org 100h\nmov ah, 9\nmov dx, offset msg\nint 21h\nret\nmsg db 'Hi$'\n")
    data = dosexe.com_image(prog)
    assert data == bytes.fromhex("B409 BA0801 CD21 C3") + b"Hi$", data.hex(" ")


def test_export_far_pointers_and_segments():
    src = """.model small
.stack 200h
.data
msg  db 'far call ok', 13, 10, '$'
fptr dd far_print          ; segment:offset of a procedure (two words: the segment needs a fixup)
.code
main proc
    mov ax, @data
    mov ds, ax
    call far ptr far_print
    call dword ptr fptr
    mov ax, seg msg
    mov es, ax
    mov ax, 4C00h
    int 21h
main endp
far_print proc far
    mov dx, offset msg
    mov ah, 9
    int 21h
    retf
far_print endp
end main
"""
    ref = run_source(src)
    assert ref["output"] == "far call ok\r\n" * 2, ref
    data = dosexe.mz_image(src)
    nrel, ip, cs, ss, sp = check_mz(data)
    assert nrel >= 4, nrel                  # mov ax,@data / call far / dd segment / mov ax,seg msg
    assert sp == 0x200
    for seg in (0x0800, 0x1234, 0x4000):
        m, info = run_loaded(data, "far.exe", "", seg)
        assert info.reason == "exit" and m.output == ref["output"], (seg, m.output)


def test_export_file_and_errors():
    tmp = Path(tempfile.mkdtemp())
    src = tmp / "hello.asm"
    src.write_text("org 100h\nmov ah, 2\nmov dl, 'A'\nint 21h\nret\n", encoding="utf-8")
    out = dosexe.export_file(src)
    assert out.name == "hello.com" and out.read_bytes()[:2] == b"\xB4\x02"
    exe_src = tmp / "prog.asm"
    exe_src.write_text(EXE_HEAD + "x dw 1\n" + EXE_CODE + EXE_END, encoding="utf-8")
    out = dosexe.export_file(exe_src)
    assert out.name == "prog.exe" and out.read_bytes()[:2] == b"MZ"
    try:
        dosexe.export_file(exe_src, kind="com")
        raise AssertionError("an EXE program exported as COM")
    except dosexe.ExportError as e:
        assert "E-EXPORT-COM" in str(e)


def test_structs_sample():
    r = run((SAMPLES / "Emu8086Structs" / "main.asm").read_text(encoding="utf-8"))
    assert r["output"] == ("Students of the 8086 course\r\nAli     91 A\r\nMona    78 C\r\nOmar    85 B\r\n"
                           "Sara    96 A\r\nAverage mark: 87\r\nBest student: Sara    \r\n"), repr(r["output"])


def test_export_button():
    """The 8086 Emulator dock's Export... button writes the file of the active program."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    test_export_button.app = QApplication.instance() or QApplication([])     # the panel needs one
    from radide.emu8086.ui import Emu8086Panel
    tmp = Path(tempfile.mkdtemp())
    src = tmp / "structs.asm"
    src.write_text((SAMPLES / "Emu8086Structs" / "main.asm").read_text(encoding="utf-8"), encoding="utf-8")
    panel = Emu8086Panel()
    assert panel.b_export.menu() is not None and len(panel.b_export.menu().actions()) == 3
    out = panel.export_dos("", source=src)
    assert out is not None and out.name == "structs.exe" and "Exported structs.exe" in panel.status.text()
    m, info = run_loaded(out.read_bytes(), out.name)
    assert "Best student: Sara" in m.output


if __name__ == "__main__":
    failed = 0
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FAIL", name, repr(e)[:400])
    print(f"\n{len(tests) - failed} / {len(tests)} passed")
    print("RESULT", "OK" if not failed else "FAIL")
    sys.exit(1 if failed else 0)
