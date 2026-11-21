"""Built-in SLEIGH disassembly (pypcode + vendored community modules) - core tests, no Qt, synthetic bytes only.

    python samples/Tests/Firmware/Sleigh/test_sleigh_core.py

Covers: vendored modules (licence + source README), first-use compilation of C166 and RL78 with pypcode's SLEIGH
compiler, the backend choice (Capstone / SLEIGH), synthetic images for 8051, V850, PowerPC VLE and C166 (prologue
mnemonics, every call lands on a function entry, every calibration-table reference found), C166 DPP paging and
EXTP / EXTS prefixes, [Rw] addressing, 8051 indexed table reads, hand-assembled RH850 / RL78 / M16C / MCS-96 /
HCS08 / HCS12X instructions, p-code listing, the CLI, the workbench short API, fallback without pypcode and
SLEIGH in place of a missing Capstone, references from two threads.
"""
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.firmware.formats import MemoryMap  # noqa: E402
from radide.firmware.analysis import disasm, sleigh, sleigh_build  # noqa: E402
from radide.firmware.analysis.synth import make_image  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:400]}]"), flush=True)
    return bool(cond)


def test_vendor():
    for name, url in (("C166", "github.com/keyhana/c166-ghidra-module"), ("RL78", "github.com/xyzz/ghidra-rl78")):
        d = sleigh_build.VENDOR / name
        lic = (d / "LICENSE").read_text(encoding="utf-8", errors="replace") if (d / "LICENSE").is_file() else ""
        readme = (d / "README.md").read_text(encoding="utf-8") if (d / "README.md").is_file() else ""
        check(f"vendor {name}: MIT LICENSE + README with source URL and commit",
              "MIT License" in lic and url in readme and "Commit" in readme)
        out = sleigh_build.build(name)
        check(f"vendor {name}: compiled with pypcode's sleigh into the cache",
              any(out.glob("*.sla")) and str(sleigh_build.cache_root()) in str(out), out)
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    check("THIRD_PARTY_NOTICES lists pypcode, Ghidra SLEIGH, C166 and RL78 modules",
          all(k in notices for k in ("pypcode", "Ghidra", "keyhana/c166-ghidra-module", "xyzz/ghidra-rl78")))
    fixed = sleigh_build._fix_export_order("X: [r+] is r { local a:3 = f(r); export *:2 a; r = r + 2; }\n"
                                           "Y: [r+] is r & r=0 { export *:2 r; r = r + 2; }\n")
    check("export-order fix keeps the pre-increment address",
          "r = r + 2; export *:2 a;" in fixed and "local _ea:2 = r; r = r + 2; export *:2 _ea;" in fixed, fixed)


def test_backends():
    for a in ("8051", "v850", "rh850", "ppc-vle", "c166", "st10", "rl78", "m16c", "r8c", "m32c", "mcs96", "hcs08",
              "hcs12x"):
        check(f"backend {a}: sleigh", disasm.backend(a) == "sleigh", disasm.backend(a))
    for a in ("arm-thumb", "ppc", "tricore", "hc12"):
        check(f"backend {a}: capstone (unchanged)", disasm.backend(a) == "capstone", disasm.backend(a))


FIRST = {"8051": "push", "v850": "add", "ppc-vle": "e_stwu", "c166": "push"}
CALLS = {"8051": "lcall", "v850": "jarl", "ppc-vle": "e_bl", "c166": "calla"}


def test_synth():
    for a in ("8051", "v850", "ppc-vle", "c166"):
        im = make_image(a, seed=2)
        mm = MemoryMap.from_bytes(im.bytes(), im.base)
        f = im.functions[5]
        lines = disasm.disassemble(mm, a, f, 0x80)
        valid = sum(1 for ln in lines if not ln.mnemonic.startswith("."))
        check(f"{a}: synthetic function decodes", valid == len(lines) and len(lines) >= 8,
              disasm.listing(mm, a, f, 0x40)[:400])
        check(f"{a}: prologue '{FIRST[a]}'", lines[0].mnemonic == FIRST[a], lines[0].mnemonic)
        # every call in the code goes to a function entry, every function ends with a return
        code = disasm.disassemble(mm, a, im.functions[0], im.base + im.code_end - im.functions[0], 10 ** 6)
        calls = [ln for ln in code if ln.mnemonic == CALLS[a]]
        entries = set(im.functions)
        bad = [(hex(ln.address), ln.target) for ln in calls if not ln.call or ln.target not in entries]
        check(f"{a}: {len(calls)} calls, all with call flag + target at a function entry", calls and not bad,
              bad[:5])
        rets = sum(1 for ln in code if ln.ret)
        check(f"{a}: returns found ({rets} for {len(im.functions)} functions)", rets >= len(im.functions), rets)
        conds = [ln for ln in code if ln.target is not None and not ln.call]
        if a != "v850":             # the synthetic V850 code has no conditional branches
            check(f"{a}: conditional branch targets are instruction starts",
                  conds and all(any(x.address == ln.target for x in code) for ln in conds[:200]), len(conds))
        start = im.base + (0x200 if a == "c166" else 0x100)
        idx = disasm.build_xrefs(mm, a, [(start, im.base + im.code_end)])
        full = sum(1 for t, srcs in im.xrefs.items() if set(srcs) <= {s for s, _k in idx.to(t)})
        check(f"{a}: every calibration-table reference found ({len(im.xrefs)} tables)", full == len(im.xrefs),
              f"{full}/{len(im.xrefs)}")
        called = [fn for fn in im.functions[1:] if any(k == "call" for _s, k in idx.to(fn))]
        check(f"{a}: call xrefs", len(called) >= 10, len(called))
        text = disasm.listing(mm, a, f, 0x40)
        check(f"{a}: listing has labels / refs", "sub_" in text, text[:300])


def _lines(arch, data, base=0, n=8, length=None, start=None):
    mm = MemoryMap.from_bytes(bytes(data), base)
    return disasm.disassemble(mm, arch, base if start is None else start, length or len(data), max_lines=n)


def test_c166():
    img = bytearray(0x20000)
    prog = bytes([0xE6, 0x02, 0x05, 0x00,        # mov DPP2,#5
                  0xF2, 0xF3, 0x70, 0xA0,        # mov r3,0xA070 -> DPP2 page 5 -> 0x16070
                  0xD7, 0x40, 0x03, 0x00,        # extp #3,#1
                  0xF2, 0xF3, 0x70, 0x20,        # mov r3,0x2070 -> page 3 -> 0xE070
                  0xF2, 0xF3, 0x70, 0x20,        # mov r3,0x2070 -> (prefix done) DPP0 = 0 -> 0x2070
                  0xD7, 0x00, 0x01, 0x00,        # exts #1,#1
                  0xF2, 0xF3, 0x70, 0x20,        # mov r3,0x2070 -> segment 1 -> 0x12070
                  0xE6, 0xF4, 0x00, 0x41,        # mov r4,#0x4100
                  0xA8, 0x54,                    # mov r5,[r4] -> DPP1 = 1 -> 0x4100
                  0xDA, 0x01, 0x34, 0x12,        # calls 1,0x1234
                  0xCB, 0x00])                   # ret
    img[0x100:0x100 + len(prog)] = prog
    ls = _lines("c166", img, 0, 11, len(prog), start=0x100)
    got = [(ln.mnemonic, ln.refs) for ln in ls]
    check("c166: mov DPP2,#5 decoded", ls[0].mnemonic == "mov" and "0xfe04" in ls[0].ops.lower(),
          (ls[0].mnemonic, ls[0].ops))
    check("c166: DPP2 page 5 -> ref 0x16070", 0x16070 in ls[1].refs, got[1])
    check("c166: EXTP #3 -> ref 0xE070", ls[2].mnemonic == "extp" and 0xE070 in ls[3].refs, got[2:4])
    check("c166: after EXTP's one instruction DPP0 again -> 0x2070", 0x2070 in ls[4].refs, got[4])
    check("c166: EXTS #1 -> ref 0x12070", ls[5].mnemonic == "exts" and 0x12070 in ls[6].refs, got[5:7])
    check("c166: MOV r4,#0x4100 + MOV r5,[r4] -> ref on both", 0x4100 in ls[7].refs and 0x4100 in ls[8].refs,
          got[7:9])
    check("c166: CALLS 1,0x1234 -> call 0x11234", ls[9].mnemonic == "calls" and ls[9].call and
          ls[9].target == 0x11234, (ls[9].mnemonic, ls[9].target))
    check("c166: RET is a return", ls[10].mnemonic == "ret" and ls[10].ret)
    check("c166: alias st10", _lines("st10", img[0x100:0x110], 0x100, 3)[0].mnemonic == "mov")


def test_8051_table():
    data = bytes([0x90, 0x02, 0x00,     # mov dptr,#0x200
                  0xE8,                 # mov a,r0     (index unknown)
                  0x93,                 # movc a,@a+dptr
                  0x02, 0x00, 0x00]) + bytes(0x300)
    ls = _lines("8051", data, 0, 4)
    check("8051: indexed MOVC -> table base 0x200 on MOVC and MOV DPTR",
          0x200 in ls[2].refs and 0x200 in ls[0].refs, [(ln.mnemonic, ln.ops, ln.refs) for ln in ls])
    check("8051: LJMP 0 is a jump to 0", ls[3].mnemonic == "ljmp" and ls[3].target == 0 and not ls[3].call)


HAND = [
    ("rh850", 0, [0x50, 0x1A, 0x80, 0xFF, 0x1C, 0x00, 0x7F, 0x00], [("add", None, False, False),
                                                                    ("jarl", 0x1E, True, False),
                                                                    ("jmp", None, False, True)]),
    ("rl78", 0, [0x30, 0x34, 0x12, 0xFD, 0x20, 0x00, 0xED, 0x00, 0x00, 0xD7],
     [("movw", None, False, False), ("call", 0x20, True, False), ("br", 0x0, False, False),
      ("ret", None, False, True)]),
    ("m16c", 0, [0x75, 0xC0, 0x34, 0x12, 0xFD, 0x20, 0x00, 0x00, 0x04, 0xF3],
     [("mov.w:g", None, False, False), ("jsr.a", 0x20, True, False), ("nop", None, False, False),
      ("rts", None, False, True)]),
    ("mcs96", 0x2000, [0xA1, 0x34, 0x12, 0x30, 0xEF, 0x10, 0x00, 0xFD, 0xF0],
     [("ld", None, False, False), ("lcall", 0x2017, True, False), ("nop", None, False, False),
      ("ret", None, False, True)]),
    ("hcs08", 0x8000, [0x45, 0x80, 0x40, 0xCD, 0x80, 0x20, 0x9D, 0x81],
     [("ldhx", None, False, False), ("jsr", 0x8020, True, False), ("nop", None, False, False),
      ("rts", None, False, True)]),
    ("hcs12x", 0xC000, [0xCE, 0xC0, 0x40, 0x16, 0xC0, 0x20, 0xA7, 0x3D],
     [("ldx", None, False, False), ("jsr", "any", True, False), ("nop", None, False, False),
      ("rts", None, False, True)]),
]


def test_hand():
    for arch, base, data, want in HAND:
        ls = _lines(arch, bytes(data) + bytes(0x40), base, len(want), len(data))
        got = [(ln.mnemonic, ln.target, ln.call, ln.ret) for ln in ls]
        ok = len(ls) == len(want) and all(g[0] == w[0] and (w[1] == "any" or g[1] == w[1]) and g[2] == w[2] and
                                          g[3] == w[3] for g, w in zip(got, want))
        check(f"{arch}: hand-assembled instructions, targets, call / return", ok, got)


def test_pcode_cli_api(tmp: Path):
    im = make_image("v850", seed=2)
    mm = MemoryMap.from_bytes(im.bytes(), im.base)
    t = disasm.pcode_listing(mm, "v850", im.functions[0], 6)
    check("p-code listing (V850): instructions + p-code ops", "jmp" in t.lower() or "st.w" in t and "=" in t, t[:300])
    ls = disasm.disassemble(mm, "v850", im.functions[0], 0x10, pcode=True)
    check("Line.pcode filled on request", ls and ls[0].pcode and not disasm.disassemble(mm, "v850", im.functions[0],
                                                                                       0x10)[0].pcode)
    try:
        disasm.pcode_listing(mm, "arm-thumb", 0, 2)
        check("p-code for a Capstone CPU raises", False)
    except ValueError:
        check("p-code for a Capstone CPU raises", True)
    img = tmp / "c166.bin"
    c = make_image("c166", seed=4)
    img.write_bytes(c.bytes())
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    r = subprocess.run([sys.executable, "-m", "radide.firmware.analysis", "disasm", str(img), "--arch", "c166",
                        "--base", "0", "--start", hex(c.functions[0]), "--length", "0x40"], capture_output=True,
                       text=True, env=env, cwd=str(ROOT), timeout=120)
    check("cli disasm --arch c166", r.returncode == 0 and "push" in r.stdout and "sub_" in r.stdout,
          r.stdout[:300] + r.stderr[-300:])
    r = subprocess.run([sys.executable, "-m", "radide.firmware.analysis", "disasm", str(img), "--arch", "c166",
                        "--base", "0", "--start", hex(c.functions[0]), "--length", "0x10", "--pcode"],
                       capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=120)
    check("cli disasm --pcode", r.returncode == 0 and "=" in r.stdout, r.stdout[:300] + r.stderr[-300:])
    t = c.tables[2]
    r = subprocess.run([sys.executable, "-m", "radide.firmware.analysis", "xrefs", str(img), hex(t.address),
                        "--arch", "c166", "--base", "0"], capture_output=True, text=True, env=env, cwd=str(ROOT),
                       timeout=300)
    check("cli xrefs --arch c166", r.returncode == 0 and all(f"0x{s:08X}" in r.stdout for s in c.xrefs.get(t.address,
                                                                                                         [])),
          r.stdout[-300:] + r.stderr[-300:])
    from radide.firmware.disasm import disassemble as short
    for a in ("8051", "v850", "c166", "ppc-vle"):
        im = make_image(a)
        rows = short(im.bytes(), im.base, a, im.functions[0], 10)
        check(f"radide.firmware.disasm.disassemble ({a}, workbench API)", len(rows) == 10 and
              rows[0][0] == im.functions[0] and rows[0][2] == FIRST[a], rows[:2])
    from radide.firmware.ui import adapters as A
    im = make_image("c166")
    rows = A.disassemble(im.bytes(), im.base, "c166", im.functions[0], 12)
    check("workbench adapter: C166 no longer says 'use Ghidra'", rows and rows[0][2] == "push", rows[:2])


def test_fallbacks():
    saved = sleigh._pc
    try:
        sleigh._pc = None
        check("without pypcode: c166 unsupported", not disasm.supported("c166"))
        check("without pypcode: reason says pip install pypcode", "pip install pypcode" in
              disasm.unsupported_reason("c166"), disasm.unsupported_reason("c166"))
        check("without pypcode: Capstone CPUs still work", disasm.supported("arm-thumb"))
    finally:
        sleigh._pc = saved
    saved_cs = disasm._cs
    try:
        disasm._cs = None
        check("without Capstone: tricore through SLEIGH", disasm.backend("tricore") == "sleigh",
              disasm.backend("tricore"))
        im = make_image("tricore", seed=2)
        mm = MemoryMap.from_bytes(im.bytes(), im.base)
        ls = disasm.disassemble(mm, "tricore", im.functions[3], 0x80)
        check("without Capstone: tricore listing has ret", any(ln.ret for ln in ls), [ln.mnemonic for ln in ls][:12])
    finally:
        disasm._cs = saved_cs


def test_threads():
    im = make_image("c166", seed=6)
    mm = MemoryMap.from_bytes(im.bytes(), im.base)
    out = {}

    def job():
        out["idx"] = disasm.build_xrefs(mm, "c166", [(im.base + 0x200, im.base + im.code_end)])
    th = threading.Thread(target=job)
    th.start()
    for f in im.functions[:40]:
        disasm.disassemble(mm, "c166", f, 0x40)
    th.join(120)
    idx = out.get("idx")
    full = sum(1 for t, srcs in im.xrefs.items() if idx and set(srcs) <= {s for s, _k in idx.to(t)})
    check("xrefs in a worker thread while the UI thread disassembles", idx is not None and full == len(im.xrefs),
          f"{full}/{len(im.xrefs)}")


def main():
    if not sleigh.available():
        print("SKIP: pypcode is not installed (pip install pypcode)")
        return 0
    with tempfile.TemporaryDirectory() as td:
        test_vendor()
        test_backends()
        test_synth()
        test_c166()
        test_8051_table()
        test_hand()
        test_pcode_cli_api(Path(td))
        test_fallbacks()
        test_threads()
    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
