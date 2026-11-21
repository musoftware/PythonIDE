"""Source-line debugging for FASM and MASM programs (radide/asm/linetable.py).

For the FASM x64 / x86 console templates (format PE / PE64: FASM writes the exe itself) and the MASM x64 / x86
templates (ml64 / ml + link.exe, skipped without Visual Studio):

* the build leaves _build/dwarf.ok and the exe has .debug_info / .debug_line naming main.asm;
* the plugin's debug_info() says "line_info": "dwarf" (F5 then lets gdb handle the breakpoints) and
  nativedbg's AsmLineMap sees the DWARF lines;
* gdb: a breakpoint on a source line resolves to main.asm, the program stops there with the input read from a
  file, `info line *$pc` names the line, the frame has the procedure's name, and the program still prints the
  right result (the added sections do not break the exe; ASLR of link.exe programs is handled by gdb);
* parser units: the MASM listing with INVOKE (/Sa "*") and macro lines, the .fas reader, the DWARF encoder.

    python samples/Tests/Assembly/CoreTests/test_linetables.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.asm import linetable as lt                   # noqa: E402
from radide.asm import toolchain as tc                    # noqa: E402
from radide.asm.build import Builder, read_diagnostics    # noqa: E402
from radide.languages import get_plugin                   # noqa: E402
from radide.model import Project                          # noqa: E402

WORK = Path(tempfile.gettempdir()) / "radide-asm-tests" / "linetables"
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


GDB = tc.mingw("gdb")
OBJDUMP = tc.mingw("objdump")
CASES = [  # template, the line to break on (text it contains), expected output after input 5
    ("fasm_console_x64", "cinvoke printf, fmt_twice", "5 + 5 = 10"),
    ("fasm_console_x86", "cinvoke printf, fmt_twice", "5 + 5 = 10"),
    ("masm_console_x64", "call printf", "5 cubed is 125"),
    ("masm_console_x86", "invoke printf, addr fmt_cube", "5 cubed is 125"),
]


def gdb_lines(folder: Path, line: int) -> str:
    (folder / "in.txt").write_text("5\n", encoding="utf-8")
    r = subprocess.run([GDB, "-batch", "-ex", f"break main.asm:{line}", "-ex", "run < in.txt", "-ex", "info line *$pc",
                        "-ex", "bt 1", "-ex", "kill", str(folder / "_radapp.exe")], cwd=folder, capture_output=True,
                       text=True, errors="replace", timeout=120)
    return r.stdout + r.stderr


for tid, needle, expect in CASES:
    plugin_id = "asm-masm" if tid.startswith("masm") else "asm-fasm"
    if tid.startswith("masm") and not tc.find_masm("x64" if tid.endswith("x64") else "x86"):
        print(f"SKIP {tid}: Visual Studio with the C++ tools (ml / ml64) was not found")
        continue
    folder = WORK / tid
    shutil.rmtree(folder, ignore_errors=True)
    plugin = get_plugin(plugin_id)
    plugin.create_new_project(folder, "Lines" + tid.split("_")[0].title(), tid)
    logs = []
    ok = Builder(folder, log=logs.append).build()
    check(f"{tid}: build", ok, "" if ok else "\n".join(logs[-10:]) + str(read_diagnostics(folder)))
    if not ok:
        continue
    check(f"{tid}: _build/dwarf.ok", (folder / "_build" / "dwarf.ok").is_file())
    info = plugin.debug_info(Project.load(folder))
    check(f"{tid}: debug_info line_info = dwarf", info.get("line_info") == "dwarf", str(info.get("line_info")))
    dl = subprocess.run([OBJDUMP, "--dwarf=decodedline", str(folder / "_radapp.exe")], capture_output=True,
                        text=True).stdout
    check(f"{tid}: .debug_line names main.asm", "main.asm" in dl and dl.count("main.asm") > 5)
    from radide.nativedbg import has_dwarf_lines
    check(f"{tid}: F5 sees the DWARF lines (nativedbg.has_dwarf_lines)",
          has_dwarf_lines(OBJDUMP, folder / "_radapp.exe", [folder / "main.asm"]))
    r = subprocess.run([str(folder / "_radapp.exe")], input="5\n", capture_output=True, text=True, timeout=30,
                       cwd=folder)
    check(f"{tid}: the exe still runs ({expect})", r.returncode == 0 and expect in r.stdout, r.stdout.strip()[-80:])
    src = (folder / "main.asm").read_text(encoding="utf-8").splitlines()
    line = next(i + 1 for i, s in enumerate(src) if needle in s)
    out = gdb_lines(folder, line)
    check(f"{tid}: gdb break main.asm:{line} resolves to the source", f"file main.asm, line {line}." in out,
          next((x for x in out.splitlines() if x.startswith("Breakpoint 1 at")), out[-200:]))
    check(f"{tid}: stops there (info line *$pc)", f'Line {line} of "main.asm"' in out,
          next((x for x in out.splitlines() if x.startswith("Line ")), ""))
    fn = "start" if tid.startswith("fasm") else "main"
    check(f"{tid}: the frame is named after the procedure ({fn})", f"#0  {fn} () at main.asm:{line}" in out or
          f"{fn} () at main.asm:{line}" in out, next((x for x in out.splitlines() if x.startswith("#0")), ""))

# ---------------------------------------------------------------- F10 in the IDE's debug session (DAP)
def f10_session(folder: Path, first: str, then: list[str]) -> tuple[bool, str]:
    """Break on the line containing *first*, press F10 len(then) times: each stop must be on the next line
    containing then[i] (FASM cinvoke / MASM INVOKE lines move ESP / RSP: gdb's own 'next' would stop inside
    the called function)."""
    import time
    from PyQt6.QtCore import QCoreApplication
    from radide import nativedbg as nd
    app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])
    src = folder / "main.asm"
    lines = src.read_text(encoding="utf-8").splitlines()
    want = [next(i + 1 for i, s in enumerate(lines) if t in s) for t in [first] + then]
    s = nd.asm_debug_session(None, folder / "_radapp.exe", [], folder, None, sources=[src],
                             breakpoints=[(str(src), want[0], "")])
    stops = []
    s.stopped.connect(stops.append)
    s.start()

    def wait(n, timeout=40):
        end = time.time() + timeout
        while time.time() < end and len(stops) < n:
            app.processEvents()
            time.sleep(0.02)
        return len(stops) >= n
    got = []
    for k in range(len(want)):
        if not wait(k + 1):
            break
        got.append(stops[-1].line)
        if k + 1 < len(want):
            s.step_over()
    s.stop()
    end = time.time() + 3
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)
    return got == want, f"stops {got}, expected {want}"


for tid, first, then in (("fasm_console_x64", "cinvoke puts, hello", ["cinvoke printf, ask", "cinvoke fflush, 0"]),
                         ("masm_console_x86", "invoke puts, addr hello", ["invoke printf, addr ask",
                                                                          "invoke fflush, 0"])):
    folder = WORK / tid
    if (folder / "_radapp.exe").is_file() and GDB:
        ok, detail = f10_session(folder, first, then)
        check(f"{tid}: F10 steps over the calls of a line (IDE debug session)", ok, detail)

# ---------------------------------------------------------------- parser units
LISTING = """Microsoft (R) Macro Assembler Version 14.44.35228.0\t    11/21/26 15:41:29
main.asm\t\t\t\t\t\t     Page 1 - 1


\t\t\t\tshow macro x
\t\t\t\t    mov eax, x
\t\t\t\t    endm
 00000000\t\t\t.code
 00000000\t\t\tmain proc
\t\t\t\t    invoke puts, addr hello
 00000000  68 00000000 R   *\t    push   OFFSET hello
 00000005  E8 00000000 E   *\t    call   puts
 0000000A  83 C4 04\t   *\t    add    esp, 000000004h
 0000000D  B8 00000001\t\t    mov eax, 1
\t\t\t\t    show 7
 00000012  B8 00000007\t     1\t    mov eax, 7
 00000017  C3\t\t\t    ret
 00000018\t\t\tmain endp
"""
SOURCE = ["show macro x", "    mov eax, x", "    endm", ".code", "main proc", "    invoke puts, addr hello",
          "    mov eax, 1", "    show 7", "    ret", "main endp"]
rows, procs = lt.parse_masm_listing(LISTING, SOURCE)
firsts = [(ln, off) for k, (ln, off, _n) in enumerate(rows) if k == 0 or rows[k - 1][0] != ln]
check("MASM listing: INVOKE code (*) and macro lines belong to their source line",
      firsts == [(6, 0x0), (7, 0xD), (8, 0x12), (9, 0x17)] and procs == {"main": 0} and
      [n for _l, _o, n in rows] == [5, 5, 3, 5, 5, 1], f"{rows} {procs}")
check("map: _name / name@N lookups", lt.map_address({"_main": 0x401000, "_f@8": 0x401010}, "main") == 0x401000 and
      lt.map_address({"_f@8": 0x401010}, "f") == 0x401010)
u = lt.Unit("a.asm", "C:/x", ["a.asm"], rows=[(1, 3, (None, 0x1000)), (1, 5, (None, 0x1004))], low=(None, 0x1000),
            high=(None, 0x1008), functions=[("f", (None, 0x1000), (None, 0x1008))])
blobs = lt.to_bytes(lt.encode_units([u], 8))
check("DWARF encoder: unit lengths match the section sizes",
      int.from_bytes(blobs[".debug_info"][:4], "little") + 4 == len(blobs[".debug_info"]) and
      int.from_bytes(blobs[".debug_line"][:4], "little") + 4 == len(blobs[".debug_line"]))
gas = lt.gas_source([lt.Unit("a.asm", "C:/x", ["a.asm"], rows=[(1, 3, ("sym", 0))], low=("sym", 0),
                             high=("sym", 4))], 64)
check("DWARF as GNU as source: relocations against the symbol", ".quad sym+0" in gas and ".secrel32 Lrad_line0" in gas)
fas = WORK / "fasm_console_x64" / "_build" / "main.fas"
if fas.is_file():
    info = lt.parse_fas(fas)
    check(".fas reader: rows of main.asm with addresses in the image", info is not None and
          any(r.file.endswith("main.asm") and r.address >= 0x400000 for r in info.rows),
          f"{len(info.rows) if info else 0} rows")

passed = sum(1 for _n, ok in results if ok)
print(f"\n{passed} / {len(results)} checks passed")
print("RESULT", "OK" if passed == len(results) else "FAIL")
sys.exit(0 if passed == len(results) else 1)
