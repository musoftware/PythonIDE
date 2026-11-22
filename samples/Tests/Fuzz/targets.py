"""Parser fuzz targets: seeds (valid sample files of the repo or generated ones), how one input is run,
and which exceptions count as a clean, handled error (everything else is a finding).

A target's run(data, case) gets the raw input bytes and an empty folder to put files in; it must only
read / write inside *case*.  allowed() is called in the worker (imports stay out of the parent).
"""
from __future__ import annotations

import io
import json
import random
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SAMPLES = ROOT / "samples"


@dataclass
class Target:
    name: str
    kind: str                                   # bytes | text | json
    seeds: Callable[[], list[tuple[str, bytes]]]
    run: Callable[[bytes, Path], None]
    allowed: Callable[[], tuple] = lambda: (ValueError,)
    setup: Callable[[], None] = lambda: None
    tokens: list[bytes] = field(default_factory=list)
    nest: Callable[[int], bytes] | None = None   # a deeply nested input of the format
    generate: Callable[[random.Random], bytes] | None = None   # an input made from scratch
    timeout: float = 10.0
    seeds_must_load: bool = True                 # False: a seed may also fail cleanly (e.g. random programs)
    refuse: Callable[[], list[tuple[str, bytes]]] = list   # inputs that MUST fail cleanly (handled)


TARGETS: dict[str, Target] = {}


def target(**kw):
    def deco(run):
        t = Target(run=run, **kw)
        TARGETS[t.name] = t
        return run
    return deco


def files(patterns: list[str], limit: int = 6, max_size: int = 300_000) -> list[tuple[str, bytes]]:
    """Small sample files of the repo (deterministic order; samples/HelloSolution is never touched)."""
    out = []
    for pat in patterns:
        for p in sorted(SAMPLES.glob(pat)):
            if "HelloSolution" in p.parts or "_build" in p.parts or not p.is_file():
                continue
            try:
                if p.stat().st_size > max_size:
                    continue
                out.append((str(p.relative_to(ROOT)), p.read_bytes()))
            except OSError:
                continue
            if len(out) >= limit:
                return out
    return out


def _qt_app():
    from PyQt6.QtCore import QCoreApplication
    from PyQt6.QtWidgets import QApplication
    QCoreApplication.setOrganizationName("RADIDE-TEST-FUZZ")
    QCoreApplication.setApplicationName("RADIDE-TEST-FUZZ")
    if QApplication.instance() is None:
        import PyQt6.QtWebEngineWidgets  # noqa: F401
        globals()["_APP"] = QApplication(["fuzz"])


def _text(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", "replace")


# ============================================================================================ .form
def _form_seeds():
    s = files(["Examples/Python/*/Form1.form", "Tests/Designer/**/*.form", "Examples/*/*/*.form"], 8)
    return s


def _form_allowed():
    return (ValueError,)


@target(name="form", kind="json", seeds=_form_seeds, allowed=_form_allowed, setup=_qt_app,
        nest=lambda d: b'{"props":{},"controls":[' + b"[" * d + b"]" * d + b"]}",
        generate=lambda rng: json.dumps({"props": {}, "controls": [
            {"type": rng.choice(["Button", "Panel", "TabControl", "RmPanel", "Nope", 3, None]),
             "props": {"Name": rng.choice(["a", "", None, 5]), "Parent": rng.choice(["", "a", "b", None, 7]),
                       "Left": rng.choice([0, -5, "x", None, 2 ** 70, 1.5])}}
            for _ in range(rng.randint(0, 6))]}).encode())
def run_form(data: bytes, case: Path) -> None:
    from radide.model import Form
    p = case / "Form1.form"
    p.write_bytes(data)
    f = Form.load(p)
    f.ordered()
    for c in f.visual():
        f.abs_pos(c)
        f.descendants(c)
    d = f.to_dict()
    json.dumps(d)
    f.save(case / "Form2.form")
    Form.load(case / "Form2.form")


# ============================================================================================ .radproj / .radsln
@target(name="radproj", kind="json",
        seeds=lambda: files(["Examples/Python/*/project.radproj", "Tests/VB6/*/project.radproj",
                             "Examples/*/*/project.radproj"], 6),
        nest=lambda d: b'{"name":"x","language":"python-tk","forms":' + b"[" * d + b"]" * d + b"}")
def run_radproj(data: bytes, case: Path) -> None:
    from radide.model import Project
    (case / "project.radproj").write_bytes(data)
    p = Project.load(case)
    p.save()
    Project.load(case)


@target(name="radsln", kind="json",
        seeds=lambda: files(["Tests/All/**/*.radsln", "Tests/Solutions/**/*.radsln"], 5),
        nest=lambda d: b'{"name":"x","projects":' + b"[" * d + b"]" * d + b"}")
def run_radsln(data: bytes, case: Path) -> None:
    from radide.solution import Solution
    p = case / "S.radsln"
    p.write_bytes(data)
    s = Solution.load(p)
    s.save(case / "S2.radsln")


# ============================================================================================ VB6
VB_TOKENS = [b"Begin VB.Form F\r\n", b"End\r\n", b"BeginProperty Font\r\n", b"EndProperty\r\n",
             b"Begin VB.CommandButton C\r\n", b'Caption = "x"\r\n', b"Left = 999999999999\r\n",
             b"Index = -1\r\n", b'Object = "{00000000-0000-0000-0000-000000000000}#1.0#0"; "x.ocx"\r\n',
             b'Picture = "Form1.frx":0000\r\n', b"Attribute VB_Name = \"x\"\r\n", b"Sub X()\r\n", b"End Sub\r\n",
             b"If x Then\r\n", b"End If\r\n", b"For i = 1 To 2\r\n", b"Next\r\n", b"_\r\n", b"(", b")", b'"']


@target(name="vb6_frm", kind="text", tokens=VB_TOKENS,
        seeds=lambda: files(["VB6Business/**/*.frm", "Tests/VB6Compat/**/*.frm", "HelloVB/*.frm",
                             "Tests/Native/VB6/*/*.frm"], 8),
        nest=lambda d: b"VERSION 5.00\r\nBegin VB.Form F\r\n" + b"Begin VB.PictureBox P\r\n" * d + b"End\r\n" * (d + 1))
def run_vb6_frm(data: bytes, case: Path) -> None:
    from radide.foreign.frm_writer import load_form, parse_frm
    from radide.foreign.vb6_project import decode_vb
    text, _enc = decode_vb(data)
    parse_frm(text)
    p = case / "Form1.frm"
    p.write_bytes(data)
    load_form(text, p, case / "cache")


@target(name="vb6_vbp", kind="text", tokens=[b"Form=Form1.frm\r\n", b"Module=M; M.bas\r\n", b"Startup=\"x\"\r\n",
                                             b"[MS Transaction Server]\r\n", b"=", b";"],
        seeds=lambda: files(["Tests/**/*.vbp", "VB6Business/**/*.vbp"], 6))
def run_vb6_vbp(data: bytes, case: Path) -> None:
    from radide.foreign.vb6_project import VbpFile
    p = case / "P.vbp"
    p.write_bytes(data)
    v = VbpFile(p)
    v.entries()
    for k in ("Name", "Startup", "Form", "Module", "Class", "Reference", "Object"):
        v.get(k)
        v.values(k)
    v.set("Title", "Fuzz")
    v.add_file("Form", "New.frm")
    v.save()


def _vb_allowed():
    from radide.runtimes.vbinterp import VBRuntimeError
    from radide.runtimes.vbparse import VBSyntaxError
    return (VBSyntaxError, VBRuntimeError)


@target(name="vb6_bas", kind="text", tokens=VB_TOKENS, allowed=_vb_allowed,
        seeds=lambda: files(["Tests/VB6/**/*.bas", "Tests/VB6Compat/**/*.bas", "VB6Business/**/*.bas",
                             "Tests/VB6/**/*.cls"], 8),
        nest=lambda d: b"Sub Main()\r\nx = " + b"(" * d + b"1" + b")" * d + b"\r\nEnd Sub\r\n")
def run_vb6_bas(data: bytes, case: Path) -> None:
    from radide.runtimes.vbparse import parse_module
    parse_module(_text(data), "Module1", "Module1.bas")


# ============================================================================================ VB interpreter
_VB_EXPR = ["1", "0", "-1", "2147483647", "-32768", "1.5", '"a"', '""', "x", "y", "s", "arr(1)", "Len(s)",
            "Mid$(s, 2, 1)", "CInt(x)", "CLng(y)", "x \\ y", "x Mod y", "x / y", "x ^ y", "Not x", "x And y",
            "x Or y", "x Xor y", "s & x", "Val(s)", "Str$(x)", "UBound(arr)", "LBound(arr)", "Asc(s)",
            "Chr$(65)", "Abs(x)", "Sgn(y)", "Int(1.5)", "Fix(-1.5)", "Left$(s, x)", "Right$(s, 2)", "InStr(s, \"a\")",
            "Replace(s, \"a\", \"b\")", "Split(s, \",\")(0)", "IIf(x > y, x, y)", "x = y", "x <> y", "s Like \"a*\"",
            "CDbl(s)", "Hex$(x)", "Oct$(y)", "Space$(3)", "String$(3, \"z\")", "Format$(x, \"0.00\")",
            "DateSerial(2000, x, 1)", "Nothing", "Empty", "Null", "IsNumeric(s)", "TypeName(x)", "Array(1, 2)(0)",
            "LCase$(s)", "UCase$(s)", "Trim$(s)", "Sqr(Abs(x))", "Log(Abs(x) + 1)", "Exp(1)", "Round(1.25, 1)",
            "CBool(x)", "CStr(y)", "CByte(x)", "CDate(\"2000-01-01\")", "Year(Now)", "Timer", "Rnd"]
_VB_STMT = ["x = {e}", "y = {e}", "s = {e}", "arr({i}) = {e}", "Print {e}", "Debug.Print {e}", "ReDim arr({i})",
            "ReDim Preserve arr({i})", "If {e} Then x = {e} Else y = {e}", "Erase arr", "s = s & {e}",
            "Call Helper({e})", "x = Helper({e})", "On Error Resume Next", "On Error GoTo 0", "Err.Raise {i}",
            "Err.Clear", "Set c = New Collection", "c.Add {e}", "x = c.Count", "x = c({i})", "c.Remove {i}",
            "Exit Sub", "GoTo L1", "Mid$(s, 1, 1) = \"q\"", "Dim d As Double: d = {e}", "Const K = {e}",
            "Select Case {e}\n Case 1: x = 2\n Case Else: y = 3\n End Select", "With c\n x = .Count\n End With",
            "Do While x < {i}\n x = x + 1\n Loop", "For i = 1 To {i}\n y = y + i\n Next i",
            "For Each v In arr\n s = s & v\n Next", "While x < 3\n x = x + 1\n Wend", "u.a = {e}", "x = u.a",
            "GoSub G1", "Static z As Integer", "LSet s = {e}", "Swap x, y", "x = {e}: y = {e}"]


def _vb_program(rng: random.Random) -> bytes:
    lines = ["Type UT", "  a As Variant", "End Type", "Dim x As Variant, y As Variant, s As String",
             "Dim arr() As Variant, c As Collection, i As Long, v As Variant, u As UT", "",
             "Function Helper(p)", "  Helper = p", "End Function", "", "Sub Main()", "  ReDim arr(3)",
             "  s = \"a,b\": x = 1: y = 2"]
    for _ in range(rng.randint(1, 25)):
        st = rng.choice(_VB_STMT)
        while "{e}" in st or "{i}" in st:
            st = st.replace("{e}", rng.choice(_VB_EXPR), 1).replace("{i}", str(rng.choice([0, 1, 2, 3, -1, 5, 100])), 1)
        lines.append("  " + st)
    lines += ["L1:", "  Exit Sub", "G1:", "  Return", "End Sub"]
    return "\r\n".join(lines).encode()


class _StepLimit(Exception):
    pass


def _vbinterp_allowed():
    from radide.runtimes.vbinterp import EndProgram, VBRuntimeError
    from radide.runtimes.vbparse import VBSyntaxError
    return (VBSyntaxError, VBRuntimeError, EndProgram, _StepLimit)


def _strip_dangerous(src: str) -> str:
    """No Declare (would call real Windows APIs), no Shell / CreateObject / Kill / SendKeys."""
    import re
    return re.sub(r"(?im)^.*\b(Declare|Shell|CreateObject|GetObject|SendKeys|Kill|RmDir|MkDir|ChDir|ChDrive|"
                  r"SaveSetting|DeleteSetting|FileCopy|Name\s+\S+\s+As)\b.*$", "", src)


@target(name="vbinterp", kind="text", tokens=[t.encode() + b"\r\n" for t in _VB_STMT[:20]], allowed=_vbinterp_allowed,
        seeds=lambda: files(["Tests/VB6/LanguageFeatures/Main.bas", "Tests/VB6Compat/ParserAndLanguage/*.bas"], 3)
        + [(f"generated{i}", _vb_program(random.Random(i))) for i in range(5)],
        generate=_vb_program, timeout=15.0, seeds_must_load=False)
def run_vbinterp(data: bytes, case: Path) -> None:
    from radide.runtimes.vbinterp import Interpreter
    from radide.runtimes.vbparse import parse_module
    src = _strip_dangerous(_text(data))
    mod = parse_module(src, "Module1", "Module1.bas")
    it = Interpreter()
    out: list[str] = []
    it.output = lambda s="": out.append(str(s)[:1000])
    steps = [0]

    def trace(frame, line):
        steps[0] += 1
        if steps[0] > 200_000:
            raise _StepLimit("step budget used up (the program loops)")
    it.trace = trace
    for nm in ("shell", "createobject", "getobject", "sendkeys", "kill", "msgbox", "inputbox"):
        it.builtins[nm] = lambda *a, **k: 0
    it.load_module(mod)
    procs = {p.lower() for p in getattr(mod, "procs", {})} if isinstance(getattr(mod, "procs", None), dict) else set()
    if not procs or "main" in procs:
        it.call_by_name("Module1", "Main", [])


# ============================================================================================ WinForms designer files
def _winforms(data: bytes, case: Path, ext: str) -> None:
    from radide.foreign import winforms_cs
    winforms_cs._SESSIONS.clear()
    p = case / f"Form1.Designer.{ext}"
    p.write_bytes(data)
    f = winforms_cs.load_form(p)
    f.to_dict()


CS_TOKENS = [b"this.button1 = new System.Windows.Forms.Button();\r\n", b"this.Controls.Add(this.button1);\r\n",
             b"this.button1.Location = new System.Drawing.Point(-1, 99999999);\r\n", b"{", b"}", b"(", b")", b"\"",
             b"/*", b"*/", b"@\"", b"this.SuspendLayout();\r\n", b"((System.ComponentModel.ISupportInitialize)(x)).BeginInit();"]


@target(name="winforms_cs", kind="text", tokens=CS_TOKENS, setup=_qt_app,
        seeds=lambda: files(["Tests/**/*.Designer.cs", "Examples/**/*.Designer.cs"], 6),
        # nested parentheses, then d unclosed "class X {" lines (finding the class was quadratic)
        nest=lambda d: (b"partial class Form1 {\r\nvoid InitializeComponent() {\r\nthis.Text = " + b"(" * d + b"\"x\"" +
                        b")" * d + b";\r\n}\r\n}\r\n") if d < 5000 else b"partial class Form1 {\r\n" * d)
def run_winforms_cs(data: bytes, case: Path) -> None:
    _winforms(data, case, "cs")


@target(name="winforms_vb", kind="text", setup=_qt_app,
        tokens=[b"Me.Button1 = New System.Windows.Forms.Button()\r\n", b"Me.Controls.Add(Me.Button1)\r\n", b"(", b")",
                b"\"", b"'", b"End Sub\r\n", b"_\r\n"],
        seeds=lambda: files(["Tests/**/*.Designer.vb", "Examples/**/*.Designer.vb"], 5),
        # d unclosed "Sub X(" lines: every line continues the statement and no "End Sub" follows
        # (both were quadratic: 1 MB took minutes)
        nest=lambda d: b"Partial Class Form1\r\n" + b"  Private Sub InitializeComponent(\r\n" * d + b"End Class\r\n")
def run_winforms_vb(data: bytes, case: Path) -> None:
    _winforms(data, case, "vb")


# ============================================================================================ Delphi / Lazarus
def _dfm_allowed():
    from radide.foreign.pascal_forms import DfmError
    return (ValueError, DfmError)


def _dfm(data: bytes, lazarus: bool) -> None:
    from radide.foreign import pascal_forms as pf
    text = pf.binary_dfm_to_text(data) if pf.is_binary_dfm(data) else _text(data)
    root = pf.parse_dfm(text)
    pf.dfm_to_form(root, lazarus=lazarus)
    pf.render(text, root)


DFM_TOKENS = [b"object Button1: TButton\r\n", b"end\r\n", b"  Caption = 'x'\r\n", b"  Left = 99999999999\r\n",
              b"  Items.Strings = (\r\n", b"  )\r\n", b"<", b">", b"item\r\n", b"{", b"}", b"#39", b"'", b"inherited ",
              b"inline ", b"[", b"]"]


@target(name="dfm", kind="text", tokens=DFM_TOKENS, allowed=_dfm_allowed,
        seeds=lambda: files(["Tests/ForeignProjects/**/*.dfm"], 5),
        nest=lambda d: b"object F: TForm\r\n" + b"object P: TPanel\r\n" * d + b"end\r\n" * (d + 1))
def run_dfm(data: bytes, case: Path) -> None:
    _dfm(data, False)


@target(name="lfm", kind="text", tokens=DFM_TOKENS, allowed=_dfm_allowed,
        seeds=lambda: files(["Tests/ForeignProjects/**/*.lfm"], 3),
        nest=lambda d: b"object F: TForm\r\n  Caption = " + b"(" * d + b")" * d + b"\r\nend\r\n")
def run_lfm(data: bytes, case: Path) -> None:
    _dfm(data, True)


# ============================================================================================ PE files
def _pe_seeds():
    out = []
    for p in sorted((SAMPLES / "Tests/PE/MfcResources/prebuilt").glob("*.pe")):
        out.append((p.name, p.read_bytes()))
    import os
    sysdir = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    for n in ("whoami.exe", "where.exe", "choice.exe", "timeout.exe"):
        p = sysdir / n
        try:
            if p.is_file() and p.stat().st_size < 200_000:
                out.append((n, p.read_bytes()))
        except OSError:
            pass
    return out


@target(name="pe", kind="bytes", seeds=_pe_seeds, timeout=20.0)
def run_pe(data: bytes, case: Path) -> None:
    from radide.pe import resources as R
    from radide.pe.document import PeDocument
    from radide.pe.image import PEImage
    img = PEImage(data)
    img.imports()
    img.exports()
    img.relocations()
    img.overlay()
    entries = R.read_tree(img)
    for e in entries[:200]:
        _parse_res(R, e)
    doc = PeDocument(bytes(data))
    doc.replace_all_resources(doc.resources)          # forces a rebuild of the .rsrc section
    out, _notes = doc.build()
    img2 = PEImage(out)
    R.read_tree(img2)


def _parse_res(R, e) -> None:
    t = e.type
    data = e.data
    fn = {5: "dialog", 4: "menu", 9: "accel", 16: "version", 241: "toolbar", 240: "dlginit"}.get(t)
    if fn == "dialog":
        R.build_dialog(R.parse_dialog(data))
    elif fn == "menu":
        R.build_menu(R.parse_menu(data))
    elif fn == "accel":
        R.build_accel(R.parse_accel(data))
    elif fn == "version":
        R.build_version(R.parse_version(data))
    elif fn == "toolbar":
        R.build_toolbar(R.parse_toolbar(data))
    elif fn == "dlginit":
        R.build_dlginit(R.parse_dlginit(data))
    elif t == 6 and isinstance(e.name, int):
        R.parse_string_block(data, e.name)
    elif t in (14, 12):
        R.group_entries(data)


def _res_blob_seeds():
    """Real resource blobs of the prebuilt MFC programs, prefixed by a type byte."""
    out = []
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from radide.pe import resources as R
        from radide.pe.image import PEImage
        for name, data in _pe_seeds()[:2]:
            for e in R.read_tree(PEImage(data)):
                if e.type in (4, 5, 6, 9, 16, 240, 241, 14) and len(out) < 24:
                    out.append((f"{name}:{e.type}:{e.name}", bytes([e.type % 256]) + e.data))
    except Exception:  # noqa: BLE001
        pass
    return out


@target(name="pe_resources", kind="bytes", seeds=_res_blob_seeds)
def run_pe_resources(data: bytes, case: Path) -> None:
    from radide.pe import resources as R
    if not data:
        return
    t, blob = data[0], data[1:]

    class E:
        pass
    e = E()
    e.type, e.data, e.name = t, blob, 7
    _parse_res(R, e)


# ============================================================================================ ROMs
def _rom_seeds():
    import sys
    sys.path.insert(0, str(ROOT))
    from radide.retro.rom import synth as S
    out = [("x.nes", S.nes_rom()), ("x.gb", S.gb_rom()), ("x.gba", S.gba_rom()), ("x.sfc", S.snes_rom(size_kb=64)),
           ("x.md", S.genesis_rom(size_kb=64)), ("x.a26", S.a26_rom()), ("x.a78", S.a78_rom())]
    for n in ("tap", "tzx", "sna", "t64", "prg", "com", "ips", "bps", "sms", "fds", "crt", "d64", "exe", "z80"):
        out.append((f"empty.{n}", b""))
    return [(n, n.encode() + b"\0" + d) for n, d in out]


@target(name="rom", kind="bytes", seeds=_rom_seeds)
def run_rom(data: bytes, case: Path) -> None:
    """Input = file name, NUL, ROM bytes (the extension chooses the detector)."""
    import importlib
    D = importlib.import_module("radide.retro.rom.detect")
    from radide.retro.rom.formats import copy_text
    name, _, rom = data.partition(b"\0")
    fname = name.decode("latin-1")[:40] or "x.bin"
    info = D.detect(rom, fname)
    D.emu_system(info)
    try:
        D.fix_checksum(rom, fname)
    except ValueError:              # "no checksum to fix for ...": a normal answer
        pass
    for fmt in ("hex", "hexcompact", "c", "asm", "base64", "text"):
        try:
            copy_text(rom[:4096], fmt)
        except ValueError:
            pass


# ============================================================================================ firmware
def _fw_seeds():
    import sys
    sys.path.insert(0, str(ROOT))
    from radide.firmware.formats import elf, ihex, srec
    from radide.firmware.formats.memmap import MemoryMap
    m = MemoryMap()
    m.add(0x8000, bytes(range(256)) * 2)
    m.add(0x20000, b"RADIDE" * 10)
    m.start = 0x8000
    return [("fw.hex", ihex.dumps(m).encode()), ("fw.s19", srec.dumps(m).encode()), ("fw.elf", elf.dumps(m)),
            ("fw32.hex", ihex.dumps(m, width=32).encode())]


@target(name="firmware", kind="text", seeds=_fw_seeds,
        tokens=[b":020000040800F2\n", b":00000001FF\n", b"S9030000FC\n", b"S00F000068656C6C6F202020202000003C\n",
                b":10", b"S3", b"\x7fELF"])
def run_firmware(data: bytes, case: Path) -> None:
    from radide.firmware import formats as F
    for fmt in ("ihex", "srec", "elf", "bin", ""):
        try:
            m = F.load_bytes(data, "fw.bin", 0, fmt)
        except ValueError:
            continue
        for out in ("ihex", "srec", "bin"):
            if sum(len(s.data) for s in m.segments) < 4_000_000 and \
                    (not m.segments or max(s.end for s in m.segments) - min(s.address for s in m.segments) < 16_000_000):
                F.dumps(m, out)


# ============================================================================================ A2L / TunerStudio ini
@target(name="a2l", kind="text", seeds=lambda: files(["Tests/Firmware/Maps/*.a2l"], 2),
        tokens=[b"/begin CHARACTERISTIC x \"\" MAP 0x1000 L 0 C 0 1\n", b"/end CHARACTERISTIC\n", b"/begin ",
                b"/end ", b"\"", b"/*", b"*/", b"0x", b"FIX_AXIS_PAR_DIST", b"COM_AXIS", b"RECORD_LAYOUT"],
        nest=lambda d: b"/begin PROJECT P \"\"\n" + b"/begin MODULE M \"\"\n" * d + b"/end MODULE\n" * d + b"/end PROJECT\n")
def run_a2l(data: bytes, case: Path) -> None:
    from radide.firmware.maps.a2l import parse_a2l
    parse_a2l(_text(data), bytes(range(256)) * 64)
    parse_a2l(_text(data))


def _ini_seed() -> bytes:
    return b"""[MegaTune]\n signature = "fuzz"\n[Constants]\n endianness = little\n page = 1\n
 reqFuel = scalar, U16, 0, "ms", 0.1, 0, 0, 25.5, 1\n veTable = array, U08, 2, [4x4], "%", 1, 0, 0, 255, 0\n
 rpmBins = array, U08, 18, [4], "RPM", 100, 0, 100, 25500, 0\n#if LAMBDA\n afr = scalar, U08, 30, "", 0.1, 0\n#else\n
 afr = scalar, U08, 31, "", 0.1, 0\n#endif\n[TableEditor]\n table = veTbl, veMap, "VE", 1\n xBins = rpmBins\n zBins = veTable\n"""


@target(name="tsini", kind="text", seeds=lambda: [("ts.ini", _ini_seed())],
        tokens=[b"[4x4]", b"array, U08, ", b"scalar, S32, ", b"#if X\n", b"#endif\n", b"{", b"}", b"\"", b";"])
def run_tsini(data: bytes, case: Path) -> None:
    from radide.firmware.maps.tsini import parse_ini
    parse_ini(_text(data), include_scalars=True)


def _msq_allowed():
    from xml.etree.ElementTree import ParseError
    return (ValueError, ParseError)


@target(name="msq", kind="text", allowed=_msq_allowed, tokens=[b"<constant name=\"x\">", b"</constant>", b"<", b">", b"&"],
        seeds=lambda: [("t.msq", b'<?xml version="1.0"?>\n<msq xmlns="http://www.msefi.com/:msq"><page>'
                                 b'<constant name="reqFuel" units="ms">8.5</constant>'
                                 b'<constant cols="1" name="veTable" rows="2">\n 50 60\n 70 80\n</constant>'
                                 b'<constant name="nCyl">"4"</constant></page></msq>')],
        nest=lambda d: b"<msq>" + b"<a>" * d + b"</a>" * d + b"</msq>")
def run_msq(data: bytes, case: Path) -> None:
    from radide.firmware.maps.tsini import msq_values
    text = _text(data)
    if text.lstrip().startswith("<"):
        msq_values(text)


# ============================================================================================ Jupyter
@target(name="ipynb", kind="json", seeds=lambda: files(["Examples/Python/DataNotebook/*.ipynb",
                                                         "Tests/DataScience/**/*.ipynb"], 2),
        nest=lambda d: b'{"cells":[{"cell_type":"code","source":' + b"[" * d + b"]" * d + b'}],"nbformat":4}')
def run_ipynb(data: bytes, case: Path) -> None:
    from radide.notebook.model import Notebook
    p = case / "n.ipynb"
    p.write_bytes(data)
    nb = Notebook.load(p)
    nb.dumps()
    nb.save(case / "n2.ipynb")
    Notebook.load(case / "n2.ipynb")


# ============================================================================================ VS Code extensions
def _pkg_seed() -> dict:
    return {"name": "fuzz-ext", "publisher": "radide", "version": "1.0.0", "displayName": "%displayName%",
            "engines": {"vscode": "^1.80.0"}, "main": "./out/extension.js", "activationEvents": ["onLanguage:x"],
            "contributes": {"commands": [{"command": "fuzz.hello", "title": "%cmd%", "icon": "$(play)"}],
                            "languages": [{"id": "fuzz", "extensions": [".fz"], "configuration": "./lang.json"}],
                            "grammars": [{"language": "fuzz", "scopeName": "source.fz", "path": "./g.json"}],
                            "keybindings": [{"command": "fuzz.hello", "key": "ctrl+alt+h", "when": "editorTextFocus"}],
                            "configuration": {"title": "Fuzz", "properties": {"fuzz.x": {"type": "boolean"}}},
                            "themes": [{"label": "T", "uiTheme": "vs-dark", "path": "./t.json"}],
                            "menus": {"editor/title": [{"command": "fuzz.hello", "when": "true"}]},
                            "viewsContainers": {"activitybar": [{"id": "fz", "title": "F", "icon": "i.svg"}]},
                            "views": {"fz": [{"id": "fz.v", "name": "V"}]}}}


def _vsxm_allowed():
    from radide.vsx.package import VsixError
    return (ValueError, VsixError)


@target(name="vsx_manifest", kind="json", seeds=lambda: [("package.json", json.dumps(_pkg_seed(), indent=1).encode())],
        allowed=_vsxm_allowed, refuse=lambda: files(["Examples/NodeWeb/*/package.json"], 2))
def run_vsx_manifest(data: bytes, case: Path) -> None:
    from radide.vsx import package as P
    d = case / "ext"
    d.mkdir()
    (d / "package.json").write_bytes(data)
    (d / "package.nls.json").write_text('{"displayName": "Fuzz", "cmd": {"message": "Hello"}}', encoding="utf-8")
    P.read_manifest(d)


def _vsix_allowed():
    from radide.vsx.package import VsixError
    return (ValueError, VsixError)


def _vsix_seed(evil: bool = False) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("extension.vsixmanifest", "<PackageManifest/>")
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("extension/package.json", json.dumps(_pkg_seed()))
        z.writestr("extension/package.nls.json", '{"displayName": "Fuzz"}')
        z.writestr("extension/out/extension.js", "exports.activate = () => {};\n" * 20)
        if evil:
            z.writestr("extension/../../evil.txt", "x")
            z.writestr("extension/C:/evil2.txt", "x")
            z.writestr("extension/sub/../../../evil3.txt", "x")
    return bio.getvalue()


@target(name="vsix", kind="bytes", allowed=_vsix_allowed,
        seeds=lambda: [("fuzz.vsix", _vsix_seed())], refuse=lambda: [("evil.vsix", _vsix_seed(True))])
def run_vsix(data: bytes, case: Path) -> None:
    from radide.vsx import package as P
    p = case / "x.vsix"
    p.write_bytes(data)
    P.read_vsix_manifest(p)
    P.safe_extract(p, case / "out")


def names() -> list[str]:
    return list(TARGETS)
