"""CPU view (OllyDbg style) + live assembly editor, in the real IDE window (qh.py harness, QSettings RADIDE-TEST).

1. NasmLoop (NASM, Windows x64, gdb): the editor's jump arrows / register highlighting, F5 to a breakpoint, the CPU
   view comes up with its four panes filled and in sync; F8 / F7 / F2 + F9 / Ctrl+G / Assemble (mov r9, 1 really
   runs) / comment + label persistence / search for command and strings / stack return-address annotation /
   Ctrl+F9 / flag bit click / inline values and register hover data in the editor.
2. Emu8086Loop (RAD IDE's 8086 emulator): the same view over the emulator: panes, F7, F4 run to cursor, F2 + F9,
   Ctrl+F9 stops on RET, inline values, loop arrow.

Screenshots (widget.grab) in Arabic + dark theme by default (QA_LANG / QA_THEME change it).
Needs the WinLibs toolchain for part 1 (nasm, gcc, gdb >= 14); part 1 is skipped without it.
Run:  python samples/Tests/Assembly/SmartCpuView/test_cpu_view.py
"""
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ.setdefault("QA_NAME", "SmartCpuView")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import app, check, pump, shot, wait  # noqa: E402

LANG = os.environ.get("QA_LANG", "ar")
THEME = os.environ.get("QA_THEME", "dark")
TAG = (LANG or "en") + ("_" + THEME if THEME else "")
WORK = Path(qh.WORK) / ("smart_cpu_" + TAG)
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)
for name in ("NasmLoop", "Emu8086Loop"):
    shutil.copytree(HERE / name, WORK / name)

if LANG:
    from radide import i18n
    i18n.set_language(app, LANG)
w = qh.window()
if THEME:
    from radide.features.workbench import set_theme
    set_theme(w, THEME.capitalize())
    pump(0.5)

from radide import nativedbg as nd  # noqa: E402
from radide.asm_intel.cpuview.notes import CpuNotes  # noqa: E402
from radide.bridgedebug import find_gdb  # noqa: E402

hub = w.cpu_view
cpu = hub.view
check("CPU dock + Debug > Windows > CPU action (Alt+C)", hub.dock is not None and wait(lambda: hasattr(w, "a_cpu_view"), 5)
      and w.a_cpu_view.shortcut().toString() == "Alt+C")


def line_of(path, text):
    return next(i for i, x in enumerate(Path(path).read_text(encoding="utf-8").splitlines()) if text in x)


def js(ed, code, timeout=5.0):
    box = []
    ed.page().runJavaScript(code, box.append)
    wait(lambda: box, timeout)
    return box[0] if box else None


def key(seq, pane=None):
    cpu.handle_key(pane or cpu.disasm.table, seq, seq if len(seq) == 1 else "")


def pc():
    return cpu.snap.pc if cpu.snap is not None else None


def row_where(pred):
    return next((i for i, r in enumerate(cpu.disasm.rows) if pred(r)), None)


def wait_stop_after(old_pc, timeout=25):
    return wait(lambda: w.session is not None and getattr(nd.dap_of(w.session) or w.session, "paused", False)
                and cpu.snap is not None and cpu.snap.pc != old_pc and cpu.disasm.pc == cpu.snap.pc, timeout)


def stop_session():
    s = w.session
    if s is not None:
        try:
            s.stop()
        except Exception as e:  # noqa: BLE001
            print("stop:", e)
    wait(lambda: w.session is None, 20)


# ====================================================================== 1. NASM under gdb
gdb, nasm = find_gdb(), nd.find_nasm()
if not (gdb and nasm):
    print(f"SKIP part 1: toolchain missing (gdb={gdb!r} nasm={nasm!r})")
else:
    proj = WORK / "NasmLoop"
    src = proj / "main.asm"
    w.open_project(proj / "project.radproj", ask=False)
    pump(1.5)
    ed = w._editor_for_file("main.asm")
    check("NasmLoop opened, main.asm editor", ed is not None and w.project is not None)
    wait(lambda: getattr(ed, "_ready", False), 30)
    wait(lambda: getattr(ed, "_radcpu", {}).get("arrows"), 15)
    st = getattr(ed, "_radcpu", {})
    L_JNZ, L_NEXT = line_of(src, "jnz  .next"), line_of(src, ".next:")
    check("editor: jump arrow computed for the loop (jnz .next)",
          any(a["src"] == L_JNZ and a["dst"] == L_NEXT and a["kind"] == "jcc" for a in st.get("arrows", [])),
          st.get("arrows"))
    check("editor: call arrow (call show -> show:)",
          any(a["kind"] == "call" and a["dst"] == line_of(src, "show:") for a in st.get("arrows", [])))
    jsa = js(ed, "JSON.stringify({a: window.radCpuState ? radCpuState.arrows.length : -1, "
                 "d: window.radCpuState ? (radCpuState.drawn || 0) : -1})")
    check("editor page: arrows pushed to the gutter canvas", jsa and '"a":2' in jsa, jsa)
    L_ADD = line_of(src, "add  rax, [rbx]")
    ed.setCursorPosition(L_ADD, 10)
    js(ed, f"radEditor.setPosition({{lineNumber: {L_ADD + 1}, column: 11}}); 1")
    pump(0.3)
    hi = js(ed, "JSON.stringify({fam: radCpuState.fam, n: radCpuState.hiCount || 0})")
    check("editor: caret on rax highlights its reads / writes in main", hi and '"fam":"rax"' in hi and
          int(hi.split('"n":')[1].rstrip("}")) >= 3, hi)

    # ---- F5 to a breakpoint on "add rax, [rbx]"
    ed.toggle_breakpoint(L_ADD)
    pump(0.2)
    w.run_project(debug=True)
    ok = wait(lambda: w.session is not None and cpu.snap is not None and cpu.disasm.rows and cpu.disasm.pc is not None,
              120)
    check("F5: stopped, CPU view shown at the first stop of an assembly program", ok and hub.dock.isVisible(),
          f"session={w.session} dock={hub.dock.isVisible()} last={cpu.last_message}")
    hub.dock.setFloating(True)                       # a big CPU window for the screenshots
    hub.dock.resize(1400, 780)
    if qh.REAL:
        hub.dock.move(-3000, 60)                     # real display: keep it off-screen like the main window
    pump(0.3)
    if ok:
        wait(lambda: cpu.stack.rows and cpu.dump.data and cpu.regs.values.get("rip"), 15)
        check("panes filled: disassembly / registers / dump / stack",
              len(cpu.disasm.rows) > 10 and "rax" in cpu.regs.values and len(cpu.dump.data) == 256
              and len(cpu.stack.rows) > 10, f"{len(cpu.disasm.rows)} {list(cpu.regs.values)[:5]} "
                                            f"{len(cpu.dump.data)} {len(cpu.stack.rows)}")
        cur = row_where(lambda r: r.address == pc())
        check("current instruction highlighted (add rax, [rbx])", cur is not None and
              cpu.disasm.rows[cur].text.startswith("add rax") and "➤" in cpu.disasm.table.item(cur, 0).text(),
              cur is not None and cpu.disasm.rows[cur].text)
        check("registers pane matches the snapshot (rip == pc)", cpu.regs.values.get("rip") == pc())
        check("stack pane starts around rsp", any(a == cpu.snap.sp for a, _v in cpu.stack.rows))
        jnz = row_where(lambda r: r.mnemonic in ("jne", "jnz"))
        check("disassembly: loop jump target inside the listing (arrow drawn)", jnz is not None and
              cpu.disasm.rows[jnz].target == cpu.disasm.rows[cur].address)
        shot(cpu, f"cpu_native_{TAG}")

        # ---- F8: the panes follow
        rax0 = cpu.regs.values.get("rax")
        p0 = pc()
        key("F8")
        check("F8 (step over): new pc, disassembly + registers in sync", wait_stop_after(p0) and
              cpu.regs.values.get("rip") == pc(), f"pc={pc()} p0={p0}")
        wait(lambda: cpu.regs.values.get("rax") != rax0, 10)
        check("rax = 3 after the first add, shown as changed (red)", cpu.regs.values.get("rax") == 3 and
              "rax" in cpu.regs.changed(), cpu.regs.values.get("rax"))
        wait(lambda: L_ADD in (getattr(ed, "_radcpu", {}).get("inline") or {}), 10)
        inl = (ed._radcpu.get("inline") or {}).get(L_ADD, "")
        check("editor: inline values after the executed line (rax=0x3 rbx=...)", inl.startswith("rax=0x3") and
              "rbx=" in inl, ed._radcpu.get("inline"))
        check("editor: register hover data with the live value", ed._radcpu.get("regs", {}).get("rax", {})
              .get("hex", "").endswith("3") and "eax" in ed._radcpu["regs"], list(ed._radcpu.get("regs", {}))[:5])
        jsi = js(ed, "JSON.stringify(Object.keys(radCpuState.inline))")
        check("editor page: inline decoration pushed", jsi and str(L_ADD) in jsi, jsi)
        js(ed, f"radEditor.setPosition({{lineNumber: {L_ADD + 1}, column: 11}}); 1")
        pump(0.5)
        shot(ed, f"editor_native_{TAG}")             # arrows, inline values, rax highlighted (QA_REAL=1 shows it)
        p0 = pc()
        key("F7")
        check("F7 (step into): next instruction", wait_stop_after(p0))

        # ---- F2 on "mov [total], rax", remove the line breakpoint, F9
        ed.toggle_breakpoint(L_ADD)
        pump(0.3)
        tgt = row_where(lambda r: r.mnemonic == "mov" and "[rip" in r.op_str and r.op_str.endswith("rax"))
        check("found 'mov [total], rax' in the disassembly", tgt is not None)
        if tgt is not None:
            addr = cpu.disasm.rows[tgt].address
            cpu.disasm.table.setCurrentCell(tgt, 3)
            key("F2")
            check("F2: address breakpoint set (red address cell)", addr in hub.backend.breakpoints() and
                  "●" in cpu.disasm.table.item(tgt, 0).text())
            p0 = pc()
            key("F9")
            check("F9: runs to the F2 breakpoint", wait(lambda: pc() == addr and cpu.disasm.pc == addr, 25), hex(pc() or 0))
            check("loop finished: rax = 3+5+7+9 = 24", wait(lambda: cpu.regs.values.get("rax") == 24, 5),
                  cpu.regs.values.get("rax"))
            cpu.disasm.table.setCurrentCell(tgt, 3)
            key("F2")
            check("F2 again removes it", addr not in hub.backend.breakpoints())
            # ---- Assemble (Space): mov r9, 0 -> mov r9, 1
            r9row = row_where(lambda r: r.mnemonic == "mov" and r.op_str.startswith("r9"))
            cpu.disasm.table.setCurrentCell(r9row, 3)
            ok_asm = cpu.assemble("mov r9, 1")
            check("Assemble: 'mov r9, 1' written over 'mov r9, 0'", ok_asm and wait(
                lambda: any(r.text in ("mov r9, 1", "mov r9d, 1") for r in cpu.disasm.rows), 10),
                [r.text for r in cpu.disasm.rows if "r9" in r.text])
            for _ in range(2):
                p0 = pc()
                key("F8")
                wait_stop_after(p0)
            check("the assembled instruction runs: r9 = 1", wait(lambda: cpu.regs.values.get("r9") == 1, 10),
                  cpu.regs.values.get("r9"))
            bad = cpu.assemble("mov r9, nosuchlabel")
            check("Assemble error explained (no write)", not bad and "nosuchlabel" in cpu.last_message,
                  cpu.last_message)

        # ---- Ctrl+G
        cpu.goto_expression("table", "dump")
        check("Ctrl+G 'table' in the dump: 03 00 .. 05 00 ..", wait(
            lambda: cpu.dump.data[:16] == bytes.fromhex("0300000000000000 0500000000000000"), 10),
            cpu.dump.data[:16].hex(" "))
        cpu.goto_expression("show")
        check("Ctrl+G 'show' in the disassembly", wait(lambda: cpu.disasm.current() is not None and
                                                       cpu.disasm.label_of(cpu.disasm.current().address) == "show", 10),
              cpu.disasm.current() and cpu.disasm.current().text)
        cpu.goto_expression("no_such_symbol_xyz")
        check("Ctrl+G error explained", wait(lambda: "no_such_symbol_xyz" in cpu.last_message, 10), cpu.last_message)
        # ---- comment / label persistence
        a_show = cpu.disasm.current_address()
        cpu.comment("prints the total", a_show)
        cpu.label("print_total", a_show)
        npath = proj / ".radide" / "cpu_notes.json"
        n2 = CpuNotes(npath, cpu.notes.program)
        st_a = hub.backend.static(a_show)
        check("comment + label saved in <project>/.radide/cpu_notes.json (static address)",
              npath.is_file() and n2.comments.get(st_a) == "prints the total" and n2.labels.get(st_a) == "print_total",
              f"{npath} {n2.comments} {n2.labels}")
        r = row_where(lambda r: r.address == a_show)
        check("label + comment shown in the disassembly", r is not None and "print_total" in
              cpu.disasm.table.item(r, 1).text() and "prints the total" in cpu.disasm.table.item(r, 4).text())
        call_row = row_where(lambda r: r.kind == "call" and r.target == a_show)
        check("calls to it show the user label", call_row is None or "print_total" in cpu.disasm.table.item(call_row, 3).text())
        cpu.disasm.origin()
        # ---- search
        found = cpu.search_command("call", show=False)
        check("Search for command 'call'", wait(lambda: found and any("call" in t for _a, t, _c in found), 15), found)
        strs = []
        cpu.search_strings(show=False, done=lambda out: strs.append(out))
        check("Search for all referenced strings finds 'Sum of the table'",
              wait(lambda: strs, 20) and any("Sum of the table" in c for _a, _t, c in strs[0]), strs)
        # ---- F7 into call show: the stack shows the return address
        wait(lambda: cpu.disasm.rows and any(r.address == pc() for r in cpu.disasm.rows), 5)
        cur = row_where(lambda r: r.address == pc())
        if cur is not None and cpu.disasm.rows[cur].kind != "call":
            callr = row_where(lambda r: r.kind == "call" and r.address > pc())
            if callr is not None:
                p0 = pc()
                cpu.run_to(cpu.disasm.rows[callr].address)
                check("F4: run to cursor (call show)", wait(lambda: pc() == cpu.disasm.rows[callr].address, 20))
        ret_addr = pc() + next(r.size for r in cpu.disasm.rows if r.address == pc())
        p0 = pc()
        key("F7")
        check("F7 into 'call show'", wait_stop_after(p0) and pc() == a_show, f"{hex(pc() or 0)} {hex(a_show)}")
        check("stack: return address annotated", wait(lambda: any(v == ret_addr and cpu.stack.comments.get(a)
                                                                  for a, v in cpu.stack.rows), 10),
              [(hex(a), hex(v), cpu.stack.comments.get(a)) for a, v in cpu.stack.rows[:6]])
        shot(cpu, f"cpu_native_stack_{TAG}")
        # ---- flag bit click
        zf0 = (cpu.snap.flags >> 6) & 1
        cpu.regs.flag_buttons["ZF"].click()
        check("flag bit click toggles ZF in the program", wait(lambda: ((cpu.snap.flags >> 6) & 1) != zf0, 10))
        # ---- Ctrl+F9
        p0 = pc()
        key("Ctrl+F9")
        check("Ctrl+F9 (execute till return): back in main after the call", wait(lambda: pc() == ret_addr, 25),
              f"{hex(pc() or 0)} want {hex(ret_addr)}")
        shot(w, f"ide_native_{TAG}")
    stop_session()
    check("session end clears the CPU view and the inline values", wait(lambda: cpu.backend is None, 10) and
          not (getattr(ed, "_radcpu", {}).get("inline")))

# ====================================================================== 2. the 8086 emulator
proj = WORK / "Emu8086Loop"
src = proj / "main.asm"
w.open_project(proj / "project.radproj", ask=False)
pump(1.5)
ed = w._editor_for_file("main.asm")
wait(lambda: getattr(ed, "_ready", False), 30)
wait(lambda: getattr(ed, "_radcpu", {}).get("arrows"), 15)
L_LOOP, L_NEXT = line_of(src, "loop add_next"), line_of(src, "add_next:")
check("8086 editor: loop arrow (loop add_next)", any(a["src"] == L_LOOP and a["dst"] == L_NEXT and a["kind"] == "loop"
                                                     for a in getattr(ed, "_radcpu", {}).get("arrows", [])))
w.run_project(debug=True)
check("8086: paused at the first instruction", wait(lambda: w.session is not None and getattr(w.session, "paused", False),
                                                     20))
hub.dock.show()
hub.dock.raise_()
hub.dock.setFloating(True)
hub.dock.resize(1400, 780)
ok = wait(lambda: cpu.snap is not None and cpu.snap.bits == 16 and cpu.disasm.rows and cpu.disasm.pc is not None, 15)
check("8086: CPU view panes filled (16-bit)", ok and "ax" in cpu.regs.values and cpu.stack.rows and cpu.dump.data,
      f"{cpu.snap and cpu.snap.bits} {list(cpu.regs.values)[:4]}")
if ok:
    cur = row_where(lambda r: r.address == pc())
    check("8086: current instruction is 'mov ax, ...' at CS:IP", cur is not None and cpu.disasm.rows[cur].mnemonic == "mov"
          and ":" in cpu.disasm.table.item(cur, 1).text())
    lp = row_where(lambda r: r.kind == "loop")
    check("8086: LOOP target = add_next (label shown)", lp is not None and
          cpu.disasm.label_of(cpu.disasm.rows[lp].target) == "add_next" and "add_next" in cpu.disasm.table.item(lp, 3).text())
    p0 = pc()
    key("F7")
    check("8086: F7 steps one instruction", wait_stop_after(p0) and cpu.regs.values.get("ax") == w.session.machine.cpu.r[0])
    tgt = row_where(lambda r: r.mnemonic == "mov" and r.op_str.endswith("ax") and "ptr" in r.op_str)
    check("8086: found 'mov total, ax'", tgt is not None)
    if tgt is not None:
        addr = cpu.disasm.rows[tgt].address
        cpu.disasm.table.setCurrentCell(tgt, 3)
        key("F4")
        check("8086: F4 runs to the cursor", wait(lambda: pc() == addr, 15), hex(pc() or 0))
        check("8086: AX = 10+20+30+40 = 100", wait(lambda: cpu.regs.values.get("ax") == 100, 5), cpu.regs.values.get("ax"))
        wait(lambda: (getattr(ed, "_radcpu", {}).get("inline") or {}), 10)
        inl = getattr(ed, "_radcpu", {}).get("inline") or {}
        check("8086 editor: inline values (ax=...)", any("ax=" in v for v in inl.values()), inl)
        callr = row_where(lambda r: r.kind == "call")
        cpu.disasm.table.setCurrentCell(callr, 3)
        key("F2")
        caddr = cpu.disasm.rows[callr].address
        key("F9")
        check("8086: F2 + F9 stop on the CALL", wait(lambda: pc() == caddr, 15), hex(pc() or 0))
        p0 = pc()
        key("F7")
        wait_stop_after(p0)
        key("Ctrl+F9")
        check("8086: Ctrl+F9 stops on the RET of show", wait(lambda: w.session.machine.mem[pc()] == 0xC3, 15),
              hex(pc() or 0))
        check("8086: stack shows the return address", any(cpu.stack.comments.get(a) for a, _v in cpu.stack.rows),
              [(hex(a), hex(v), cpu.stack.comments.get(a)) for a, v in cpu.stack.rows[:5]])
        cpu.goto_expression("msg", "dump")
        check("8086: Ctrl+G 'msg' in the dump", wait(lambda: cpu.dump.data.startswith(b"Total = $"), 5),
              cpu.dump.data[:12])
        sel = row_where(lambda r: r.address == pc())
        cpu.disasm.table.setCurrentCell(sel, 3)
        cpu.binary_edit(text="90")                      # RET -> NOP ... then write it back
        check("8086: binary edit writes the byte", wait(lambda: w.session.machine.mem[pc()] == 0x90, 5))
        cpu.binary_edit(pc(), "C3")
        wait(lambda: w.session.machine.mem[pc()] == 0xC3, 5)
    shot(cpu, f"cpu_8086_{TAG}")
stop_session()
qh.finish(w)
