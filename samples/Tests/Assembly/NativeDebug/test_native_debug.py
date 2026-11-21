"""Native debugger test (radide/nativedbg.py + radide/features/native_debug.py), in the real IDE window:

1. sum.asm (NASM, Windows x64): a breakpoint on an .asm line (line table from the NASM listing),
   instruction stepping, the Registers window (rax changes and is shown red), the Memory window
   (the bytes of the data label "values"), the Disassembly window (arrow, address breakpoint),
   the Stack window.
2. sum_gas.s (GNU as, gcc -g): gdb's own DWARF breakpoint on the .s line, instruction step.
3. arrays.c (gcc -g -O0): Registers, Disassembly with the C source in between, Memory of &table,
   Step Into Instruction.

Needs the WinLibs toolchain (%LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64: gcc, nasm, gdb >= 14).
Run:  python samples/Tests/Assembly/NativeDebug/test_native_debug.py
"""
import os
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import shutil  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
__import__("PyQt6.QtWebEngineWidgets")
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST-NativeDebug")
app = QApplication(sys.argv[:1])
QSettings().clear()

from radide import nativedbg as nd  # noqa: E402
from radide.app import MainWindow  # noqa: E402
from radide.dap import DapSession  # noqa: E402
from radide.bridgedebug import find_gdb, gdb_env  # noqa: E402
from radide.features import native_debug  # noqa: E402

results = []
ERRORS = []


def _hook(*exc):                      # an exception in a Qt slot: report it (instead of PyQt's abort)
    import traceback
    ERRORS.append("".join(traceback.format_exception(*exc)))
    print(ERRORS[-1], file=sys.stderr, flush=True)


sys.excepthook = _hook
SHOTS = Path(os.environ.get("RADIDE_SHOTS", tempfile.gettempdir())) / "radide_native_debug"


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  - {detail}" if detail else ""), flush=True)


def wait(cond, timeout=30.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.02)
    return False


def pump(sec=0.3):
    wait(lambda: False, sec)


def close_boxes():
    m = QApplication.activeModalWidget()
    if m is not None:
        m.close()


killer = QTimer()
killer.timeout.connect(close_boxes)
killer.start(300)

# ---------------------------------------------------------------- build the programs in a temp copy
gdb = find_gdb()
tc = Path(gdb).parent if gdb else None
nasm = nd.find_nasm()
gcc = str(tc / "gcc.exe") if tc and (tc / "gcc.exe").exists() else shutil.which("gcc")
if not (gdb and nasm and gcc):
    print(f"SKIP: toolchain missing (gdb={gdb!r} nasm={nasm!r} gcc={gcc!r})")
    sys.exit(0)
W = Path(tempfile.mkdtemp(prefix="radide_natdbg_"))
for f in ("sum.asm", "sum_gas.s", "arrays.c", "waits.asm"):
    shutil.copy(HERE / f, W / f)
env = dict(os.environ, PATH=str(tc) + os.pathsep + os.environ.get("PATH", ""))
for argv in ([nasm, "-f", "win64", "-o", "sum.obj", "sum.asm"], [gcc, "-o", "sum.exe", "sum.obj"],
             [gcc, "-s", "-o", "sum_stripped.exe", "sum.obj"],
             [nasm, "-f", "win64", "-o", "waits.obj", "waits.asm"], [gcc, "-o", "waits.exe", "waits.obj"],
             [gcc, "-g", "-O0", "-o", "sum_gas.exe", "sum_gas.s"], [gcc, "-g", "-O0", "-o", "arrays.exe", "arrays.c"]):
    r = subprocess.run(argv, cwd=W, env=env, capture_output=True, text=True)
    if r.returncode:
        print("build failed:", argv, r.stdout, r.stderr)
        sys.exit(1)
check("build sum.exe / waits.exe / sum_gas.exe / arrays.exe", True)


def line_of(file, text):
    return next(i for i, ln in enumerate((W / file).read_text().splitlines(), 1) if text in ln)


win = MainWindow()
win.resize(1400, 900)
win.show()
pump(1.5)
hub = win.native_debug
stops = []
orig = win._on_stopped
win._on_stopped = lambda info: (stops.append(info), orig(info))
check("Debug > Windows has Registers / Memory 1 / Disassembly / Stack",
      all(hub.docks[k].toggleViewAction() in win.findChildren(type(hub.docks[k].toggleViewAction()))
          for k in hub.docks) and hasattr(win, "a_step_into_instruction"))

# ---------------------------------------------------------------- 1. NASM
lm = nd.AsmLineMap.build(W / "sum.exe", [W / "sum.asm"])
BP = line_of("sum.asm", "add  rax, [rbx]")
check("NASM line table built", bool(lm) and lm.address_for(W / "sum.asm", BP) is not None, f"notes={lm.notes}")
s = nd.asm_debug_session(win, W / "sum.exe", cwd=W, sources=[W / "sum.asm"], breakpoints=[("sum.asm", BP, "")])
native_debug.start_session(win, s, "sum.exe")
ok = wait(lambda: stops, 40)
info = stops[-1] if stops else None
check("stops on the .asm breakpoint line", ok and Path(info.file).name == "sum.asm" and info.line == BP,
      f"{info and (info.file, info.line, info.reason)}")
check("Locals shows the registers (assembly)", any(v[0] == "rax" for v in (info.variables if info else [])))
hub.docks["registers"].show()
hub.docks["registers"].raise_()
rv = hub.views["registers"]
wait(lambda: "rax" in rv.values, 15)
rax0 = rv.values.get("rax", ("", None))[1]
check("Registers window: rax / rip / eflags", rax0 is not None and "rip" in rv.values and "eflags" in rv.values,
      f"rax={rax0}")
flags_item = next((rv.groups["Flags"].child(i) for i in range(rv.groups["Flags"].childCount())), None) \
    if "Flags" in rv.groups else None
check("eflags decoded as bits (CF ZF SF OF ...)", flags_item is not None and flags_item.childCount() >= 9
      and {flags_item.child(i).text(0) for i in range(flags_item.childCount())} >= {"CF", "ZF", "SF", "OF"})
n0 = len(stops)
hub.step(True)                                         # add rax, [rbx]  -> rax = 11
wait(lambda: len(stops) > n0, 15)
wait(lambda: rv.values.get("rax", ("", None))[1] != rax0, 10)
rax1 = rv.values.get("rax", ("", None))[1]
check("Step Over Instruction: next .asm line", stops[-1].line == BP + 1, f"line={stops[-1].line}")
check("rax changed after the step (11)", rax1 == 11, f"rax={rax1}")
rax_item = next((rv.groups["General"].child(i) for i in range(rv.groups["General"].childCount())
                 if rv.groups["General"].child(i).text(0) == "rax"), None)
check("changed register shown red", rax_item is not None and rax_item.foreground(1).color() == native_debug._changed_color())
# edit a register: rdx = 0x1234
d = nd.dap_of(win.session)
done = []
nd.set_register(d, "rdx", "0x1234", lambda t, ok2: done.append(ok2))
wait(lambda: done, 10)
hub.refresh_all()
wait(lambda: rv.values.get("rdx", ("", None))[1] == 0x1234, 10)
check("register edited (rdx = 0x1234)", rv.values.get("rdx", ("", None))[1] == 0x1234, f"{done} {rv.values.get('rdx')}")
# memory window: the bytes of the label "values"
hub.show_memory("values")
mv = hub.views["memory"]
wait(lambda: mv.data, 10)
check("Memory window: bytes of the label 'values'", mv.data[:16] == bytes.fromhex("0B00000000000000 1600000000000000"),
      mv.data[:16].hex(" "))
mv.group.setCurrentIndex(3)
pump(0.2)
check("Memory 8-byte grouping shows 000000000000000B", "000000000000000B" in mv.view.toPlainText())
# disassembly window
hub.docks["disassembly"].show()
hub.docks["disassembly"].raise_()
dv = hub.views["disassembly"]
wait(lambda: dv.instrs and dv.pc is not None, 10)
pc_rows = [dv.tree.topLevelItem(i) for i in range(dv.tree.topLevelItemCount()) if "➤" in dv.tree.topLevelItem(i).text(0)]
check("Disassembly: arrow on the current instruction (Intel syntax)",
      len(pc_rows) == 1 and "rbx" in pc_rows[0].text(3) and "%" not in pc_rows[0].text(3),
      f"{pc_rows and pc_rows[0].text(3)} pc={dv.pc} {[(hex(i['address']), i['text']) for i in dv.instrs[:6]]}")
src_rows = [dv.tree.topLevelItem(i).text(3) for i in range(dv.tree.topLevelItemCount())
            if dv.tree.topLevelItem(i).text(1) == ""]
check("Disassembly: .asm source lines interleaved", any("sum.asm:" in t for t in src_rows), str(src_rows[:3]))
# address breakpoint on "mov [total], rax" (after the loop), continue
target = next((i["address"] for i in dv.instrs if i["text"].startswith("mov") and "rax" in i["text"]
               and "QWORD PTR" in i["text"]), None)
win.session.set_breakpoint("sum.asm", BP, False)       # remove the loop breakpoint
pump(0.3)
dv.toggle_bp(target)
check("address breakpoint set in the Disassembly window", target in nd.address_breakpoints(win.session))
n0 = len(stops)
win.session.cont()
wait(lambda: len(stops) > n0, 15)
check("continue stops on the address breakpoint (line of mov [total], rax)",
      len(stops) > n0 and stops[-1].line == line_of("sum.asm", "mov  [total], rax"), f"line={stops[-1].line}")
wait(lambda: rv.values.get("rax", ("", None))[1] == 110, 10)
check("rax = 110 after the loop", rv.values.get("rax", ("", None))[1] == 110)
hub.docks["stack"].show()
hub.docks["stack"].raise_()
sv = hub.views["stack"]
wait(lambda: sv.tree.topLevelItemCount() > 8, 10)
check("Stack window: rows from RSP", any("RSP" in sv.tree.topLevelItem(i).text(0) for i in range(sv.tree.topLevelItemCount())))
SHOTS.mkdir(parents=True, exist_ok=True)
for k in ("registers", "disassembly", "memory", "stack"):
    hub.docks[k].show()
    hub.docks[k].raise_()
    pump(0.3)
    hub.views[k].grab().save(str(SHOTS / f"asm_{k}.png"))
win.stop_project()
wait(lambda: win.session is None, 15)
check("session ends, windows cleared", win.session is None and not rv.values)

# ---------------------------------------------------------------- 2. GNU as (DWARF)
stops.clear()
GBP = line_of("sum_gas.s", "add  rax, [rbx]")
from radide.bridgedebug import find_gdb as _fg  # noqa: E402
s = DapSession("gdb", str(W / "sum_gas.exe"), [], W, gdb_env(_fg()), [("sum_gas.s", GBP, "")], win)
s.argv = [_fg(), "-i", "dap"]
s.break_on_exception = False
native_debug.start_session(win, s, "sum_gas.exe")
wait(lambda: stops, 40)
check("GAS: stops on the .s line (DWARF)", stops and Path(stops[-1].file).name == "sum_gas.s" and stops[-1].line == GBP,
      stops and f"{stops[-1].file}:{stops[-1].line}")
wait(lambda: "rax" in rv.values, 10)
r0 = rv.values.get("rax", ("", None))[1]
n0 = len(stops)
hub.step(False)
wait(lambda: len(stops) > n0, 15)
wait(lambda: rv.values.get("rax", ("", None))[1] != r0, 10)
check("GAS: Step Into Instruction changes rax", rv.values.get("rax", ("", None))[1] == 11)
win.stop_project()
wait(lambda: win.session is None, 15)

# ---------------------------------------------------------------- 3. C
stops.clear()
CBP = line_of("arrays.c", "sum += p[i];")
s = DapSession("gdb", str(W / "arrays.exe"), [], W, gdb_env(_fg()), [("arrays.c", CBP, "")], win)
s.argv = [_fg(), "-i", "dap"]
s.break_on_exception = False
native_debug.start_session(win, s, "arrays.exe")
wait(lambda: stops, 40)
check("C: stops on the breakpoint", stops and Path(stops[-1].file).name == "arrays.c" and stops[-1].line == CBP)
hub.docks["registers"].raise_()
wait(lambda: "rip" in rv.values, 10)
check("C: Registers window filled", "rax" in rv.values and "rsp" in rv.values)
hub.show_disassembly()
wait(lambda: dv.instrs and dv.pc is not None, 10)
c_src = [dv.tree.topLevelItem(i).text(3) for i in range(dv.tree.topLevelItemCount()) if dv.tree.topLevelItem(i).text(1) == ""]
check("C: Disassembly shows the C source lines", any("arrays.c:" in t and "sum" in t for t in c_src), str(c_src[:3]))
hub.show_memory("&table")
wait(lambda: mv.base is not None and mv.data[:8] == (11).to_bytes(8, "little"), 10)
check("C: Memory window at &table", mv.data[:8] == (11).to_bytes(8, "little"), mv.data[:16].hex(" "))
pc0 = dv.pc
n0 = len(stops)
hub.step(False)
wait(lambda: len(stops) > n0, 15)
wait(lambda: dv.pc is not None and dv.pc != pc0, 10)
check("C: Step Into Instruction moves the pc by one instruction", dv.pc is not None and dv.pc != pc0
      and any(i["address"] == dv.pc for i in dv.instrs))
hub.views["disassembly"].grab().save(str(SHOTS / "c_disassembly.png"))
win.stop_project()
wait(lambda: win.session is None, 15)

# ---------------------------------------------------------------- 4. attach to a running assembly program
stops.clear()
ABP = line_of("waits.asm", "add  rax, rcx")
proc = subprocess.Popen([str(W / "waits.exe")], cwd=W, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
time.sleep(0.5)
s = nd.asm_attach_dap([_fg(), "-i", "dap"], {"pid": proc.pid, "program": str(W / "waits.exe")}, W, gdb_env(_fg()),
                      [("waits.asm", ABP, "")], W / "waits.exe", [W / "waits.asm"], None, win)
configured = []
s.configured.connect(lambda: configured.append(1))
native_debug.start_session(win, s, "attach waits.exe")
wait(lambda: configured and s.slide_known, 30)
pump(0.5)
proc.stdin.write(b"\n")
proc.stdin.flush()
wait(lambda: stops, 30)
check("attach: stops on the .asm line (line table, attached)", stops and Path(stops[-1].file).name == "waits.asm"
      and stops[-1].line == ABP, stops and f"{stops[-1].file}:{stops[-1].line}")
wait(lambda: rv.values.get("rcx", ("", None))[1] == 3, 10)
check("attach: Registers window shows rcx = 3", rv.values.get("rcx", ("", None))[1] == 3)
win.stop_project()
wait(lambda: win.session is None, 15)
try:
    proc.kill()
except OSError:
    pass

# ---------------------------------------------------------------- 5. no symbols / no line table: entry point
stops.clear()
s = nd.asm_debug_session(win, W / "sum_stripped.exe", cwd=W, sources=[W / "sum.asm"], breakpoints=[])
check("stripped program: no line table, stop at entry", not s.linemap and s.stop_at_entry, str(s.linemap.notes))
native_debug.start_session(win, s, "sum_stripped.exe")
wait(lambda: stops, 40)
check("stripped program: stops at the entry point (no source)", stops and stops[-1].file == "" and
      getattr(stops[-1], "pc", None) is not None, stops and f"{stops[-1].file!r} pc={getattr(stops[-1], 'pc', None)}")
wait(lambda: hub.docks["disassembly"].isVisible() and dv.pc is not None, 10)
check("Disassembly window comes up at the entry point", hub.docks["disassembly"].isVisible() and dv.pc == stops[-1].pc)
n0 = len(stops)
hub.step(False)
wait(lambda: len(stops) > n0, 15)
check("stripped program: Step Into Instruction", len(stops) > n0 and stops[-1].pc != stops[n0 - 1].pc)
win.stop_project()
wait(lambda: win.session is None, 15)

# ---------------------------------------------------------------- 6. F5 of a RAD IDE NASM project (Assembly core build)
try:
    from radide.languages.asm_nasm import NasmPlugin
except Exception as e:  # noqa: BLE001 - the Assembly core slice is not installed
    NasmPlugin = None
    print(f"SKIP F5 of a NASM project: {e}")
if NasmPlugin is not None:
    import json  # noqa: E402
    P = W / "AsmProject"
    P.mkdir()
    shutil.copy(HERE / "sum.asm", P / "sum.asm")
    (P / "project.radproj").write_text(json.dumps({
        "name": "AsmProject", "language": "asm-nasm", "forms": [], "startup": "", "modules": ["sum.asm"],
        "asm": {"assembler": "nasm", "arch": "x64", "linker": "gcc", "entry": "main", "debug": True}}), "utf-8")
    plugin = NasmPlugin()
    spec = plugin.run_spec(P, "", sys.executable)
    stops.clear()
    out = []
    s = nd.asm_console_session(win, plugin, spec, True, breakpoints=[("sum.asm", BP, "")])
    s.output.connect(out.append)
    ended = []
    s.finished.connect(lambda c: ended.append(c))
    native_debug.start_session(win, s, "AsmProject")
    wait(lambda: stops or ended, 120)
    check("F5 NASM project: build (DWARF lines) + stop on the .asm line",
          stops and Path(stops[-1].file).name == "sum.asm" and stops[-1].line == BP,
          stops and f"{stops[-1].file}:{stops[-1].line}" or "".join(out)[-600:])
    n0 = len(stops)
    if stops:
        win.session.step_over()
        wait(lambda: len(stops) > n0, 15)
        check("F5 NASM project: F10 goes to the next line", len(stops) > n0 and stops[-1].line == BP + 1)
        win.session.set_breakpoint("sum.asm", BP, False)
        pump(0.3)
        win.session.cont()
    wait(lambda: ended, 30)
    check("F5 NASM project: program output reaches the IDE and it ends", ended and "Sum = 110" in "".join(out),
          "".join(out)[-300:])
    wait(lambda: win.session is None, 10)

win.close()
pump(0.5)
QSettings().clear()
shutil.rmtree(W, ignore_errors=True)
check("no exceptions in the windows' callbacks", not ERRORS, ERRORS and ERRORS[0][-400:])
failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} passed" + (f"; FAILED: {failed}" if failed else ""))
print(f"screenshots: {SHOTS}")
sys.exit(1 if failed else 0)
