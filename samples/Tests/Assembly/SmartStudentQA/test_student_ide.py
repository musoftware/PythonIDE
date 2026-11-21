"""Beginner-student QA of the smart assembly editor in the real IDE (Arabic UI + dark theme by default).

qh.py harness: offscreen (QA_REAL=1 for a real off-screen window, which renders Monaco in the screenshots),
QSettings "RADIDE-TEST" cleared afterwards, screenshots only with widget.grab() in %TEMP%/radide-qa/shots.

1. NasmHello: the student types the program line by line in Monaco. The red squiggle appears while typing
   (before the program is finished), the hover explains in Arabic (why / how to fix), Ctrl+. offers the fixes
   (also the new "reserve shadow space" one), Problems Explained lists everything.
   "Check by Running" on the half-fixed program finds the runtime problems (value instead of address, alignment,
   shadow space) with Arabic details; after all fixes the squiggles are gone, Ctrl+F5 builds and runs it (output in
   the IDE) and Check by Running is clean.
2. NasmAverage (fixed): Explain This Line (2nd pass of 'add eax, [r10]'), What-If (200 + 100 in AL), then F5 with a
   breakpoint on 'jnz .again': CPU view, "jump is taken" in Arabic, editor inline values + the taken arrow.
3. Emu8086Grade: squiggles of the emu8086-style mistakes, quick fixes, then F5 in the 8086 emulator with the CPU
   view (16-bit panes, F7, inline values, the 'jae ok' arrow).
Run:  python samples/Tests/Assembly/SmartStudentQA/test_student_ide.py
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ.setdefault("QA_NAME", "SmartStudentQA")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
sys.path.insert(0, str(HERE))
import qh  # noqa: E402
from qh import app, check, pump, shot, wait  # noqa: E402

from student_programs import fixed_text  # noqa: E402

LANG = os.environ.get("QA_LANG", "ar")
THEME = os.environ.get("QA_THEME", "dark")
TAG = (LANG or "en") + ("_" + THEME if THEME else "")
ARABIC = re.compile(r"[؀-ۿ]")
WORK = Path(qh.WORK) / ("student_" + TAG)
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)
for name in ("NasmHello", "MasmSum", "NasmAverage", "Emu8086Grade"):
    shutil.copytree(HERE / name, WORK / name)

from radide import i18n  # noqa: E402

if LANG:
    i18n.set_language(app, LANG)
w = qh.window()
if THEME:
    from radide.features.workbench import set_theme
    set_theme(w, THEME.capitalize())
    pump(0.5)

from radide import nativedbg as nd  # noqa: E402
from radide.features import asm_smart_lint as L  # noqa: E402

AR = LANG == "ar"


def js(ed, code, timeout=8.0):
    box = []
    ed.page().runJavaScript(code, box.append)
    wait(lambda: box, timeout)
    return box[0] if box else None


def markers(ed, owner="radAsmLint"):
    raw = js(ed, f"JSON.stringify(monaco.editor.getModelMarkers({{owner: '{owner}'}}).map(m => "
                 "[m.startLineNumber, m.code, m.message, m.severity]))")
    try:
        return json.loads(raw or "[]")
    except ValueError:
        return []


def codes(ed):
    return {(m[1], m[0]) for m in markers(ed)}


def lang_text(s):
    return bool(ARABIC.search(s or "")) if AR else bool(s)


def stop_session():
    s = w.session
    if s is not None:
        try:
            s.stop()
        except Exception as e:  # noqa: BLE001
            print("stop:", e)
    wait(lambda: w.session is None, 20)


def open_project(name):
    stop_session()
    w.open_project(WORK / name / "project.radproj", ask=False)
    pump(1.5)
    ed = w._editor_for_file("main.asm") or w.open_any_file(WORK / name / "main.asm")
    wait(lambda: getattr(ed, "_ready", False), 40)
    wait(lambda: js(ed, "!!window.__radAsmLint"), 20)
    return ed


def fix_all(ed, rounds=20):
    """Apply quick fixes the way the Problems panel's Fix button does, until no fixable error / warning is left."""
    for _ in range(rounds):
        fixable = [i for i in L.lint_editor(ed) if i.severity in ("error", "warning") and i.fixes]
        if not fixable:
            return
        L.apply_fix(ed, fixable[0].fixes[0])
        pump(0.2)


# ====================================================================== 1. NasmHello typed line by line
buggy = (HERE / "NasmHello" / "main.asm").read_text(encoding="utf-8").split("\n")
(WORK / "NasmHello" / "main.asm").write_text("", encoding="utf-8")
ed = open_project("NasmHello")
check("NasmHello: empty main.asm open in Monaco with the analyzer", ed is not None and L.is_lint_editor(ed))
L_MOVRDX = next(i for i, s in enumerate(buggy) if "mov rdx, eax" in s)
seen_while_typing = False
for i, line in enumerate(buggy):
    text = line + ("\n" if i < len(buggy) - 1 else "")
    js(ed, "(() => { const m = radEditor.getModel(); const n = m.getLineCount(); const c = m.getLineMaxColumn(n);"
           f" radEditor.executeEdits('type', [{{range: new monaco.Range(n, c, n, c), text: {json.dumps(text)}}}]);"
           " return 1; })()")
    pump(0.05)
    if i == L_MOVRDX + 1:                 # the student is still typing: squiggle on 'mov rdx, eax' already?
        seen_while_typing = wait(lambda: ("ASM101", L_MOVRDX + 1) in codes(ed), 8)
check("while typing: red squiggle ASM101 on 'mov rdx, eax' before the program is finished", seen_while_typing,
      sorted(codes(ed)))
wait(lambda: ("ASM102", 21) in codes(ed), 15)
got = codes(ed)
for rule_id, line in (("ASM509", 14), ("ASM501", 15), ("ASM502", 15), ("ASM101", 18), ("ASM102", 21)):
    check(f"NasmHello squiggle {rule_id} on line {line}", (rule_id, line) in got, sorted(got))
mk = markers(ed)
check("squiggle messages follow the UI language (Arabic)", all(lang_text(m[2]) for m in mk), [m[2] for m in mk][:3])
hov = json.loads(js(ed, "JSON.stringify(radAsmLintHover(13, 6))") or "[]")
check("hover on 'mov rcx, [msg]' explains why + how to fix + Learn more",
      hov and ("لماذا" in hov[0] and "كيف أصلحه" in hov[0] and "اعرف المزيد" in hov[0] if AR else "Why" in hov[0]),
      hov[:1])
check("hover suggests lea rcx, [msg]", hov and "lea" in hov[0].lower(), hov[:1])
acts = json.loads(js(ed, "JSON.stringify(radAsmLintActions(14))") or "[]")
check("Ctrl+. on 'call printf' offers 'reserve shadow space' (sub rsp, 40 / add rsp, 40)",
      any("sub rsp, 40" in a for a in acts), acts)
js(ed, "radEditor.setPosition({lineNumber: 14, column: 6}); radEditor.revealLine(14); 1")
pump(0.5)
shot(w, f"student_nasm_typed_{TAG}")
panel = w.show_asm_problems()
pump(0.5)
check("Problems Explained lists the student's mistakes", panel.list.count() >= 5, panel.list.count())
i509 = next((k for k, it in enumerate(panel.issues) if it.rule == "ASM509"), 0)
panel.list.setCurrentRow(i509)
pump(0.3)
body = panel.text.toPlainText()
check("Problems panel: Arabic why / how to fix + instruction reference", lang_text(body) and "lea" in body.lower(),
      body[:300])
shot(w._asm_lint_dock, f"student_problems_{TAG}")

# ---- half fixed (the red squiggles fixed with Ctrl+.), then Check by Running
for ln in (L_MOVRDX, 20):
    js(ed, f"radAsmLintApplyFix({ln}, 0)")
    pump(0.3)
check("Ctrl+. fixes applied: movsxd rdx, eax and dword [a]", wait(
    lambda: "movsxd rdx, eax" in ed.text() and "mov dword [a], 0" in ed.text(), 8), ed.text())
check("no red squiggle left (only warnings)", wait(lambda: not [m for m in markers(ed) if m[3] == 8], 10),
      markers(ed))
w.save_all()
w.a_asm_check_run.trigger()
sim = w.asm_checks
ok = wait(lambda: sim.result is not None and not sim._busy, 90)
res = sim.result
rules = {f.rule for f in (res.findings if res else [])}
check("Check by Running finds: value instead of address, unaligned RSP, no shadow space",
      ok and {"sim.bad_pointer_arg", "sim.misaligned_call", "sim.no_shadow_space"} <= rules,
      (res and res.status, sorted(rules), res and res.note_en))
html = sim.details.toHtml()
check("runtime finding details in Arabic (what happened + fix)", lang_text(sim.details.toPlainText()), html[:300])
sim.dock.setFloating(True)
sim.dock.resize(1150, 650)
if qh.REAL:
    sim.dock.move(-3000, 80)
pump(0.4)
shot(sim.dock, f"student_check_run_{TAG}")
check("runtime markers in the editor (owner rad-asm-sim)", markers(ed, "rad-asm-sim"), markers(ed, "rad-asm-sim"))

# ---- all fixes, build + run, clean check
fix_all(ed)
left = [i for i in L.lint_editor(ed) if i.severity in ("error", "warning")]
check("after the quick fixes: no errors / warnings", not left, [(i.rule, i.line + 1) for i in left])
check("squiggles cleared in the editor", wait(lambda: not [m for m in markers(ed) if m[3] in (4, 8)], 10),
      markers(ed))
w.save_all()
w.output.clear()
w.run_project(debug=False)
ok = wait(lambda: "a + b = 12" in w.output.toPlainText(), 120)
check("Ctrl+F5: the fixed program builds and prints 'My name is Ahmed' / 'a + b = 12'",
      ok and "My name is Ahmed" in w.output.toPlainText(), w.output.toPlainText()[-800:])
stop_session()
res = sim.run_check(wait=True)
check("Check by Running on the fixed program: clean",
      res is not None and not [f for f in res.findings if f.severity in ("error", "warning")],
      res and [(f.rule, f.line) for f in res.findings])

# ====================================================================== 1b. MasmSum (MASM, 32-bit)
ed = open_project("MasmSum")
wait(lambda: ("ASM104", 29) in codes(ed), 15)
got = codes(ed)
for rule_id, line in (("ASM304", 20), ("ASM507", 28), ("ASM104", 29)):
    check(f"MasmSum squiggle {rule_id} on line {line}", (rule_id, line) in got, sorted(got))
check("MASM squiggle messages in the UI language", all(lang_text(m[2]) for m in markers(ed)), markers(ed))
acts = json.loads(js(ed, "JSON.stringify(radAsmLintActions(19))") or "[]")
check("Ctrl+. on the unbalanced ret offers 'pop ebx'", any("pop ebx" in a for a in acts), acts)
shot(w, f"student_masm_squiggles_{TAG}")
fix_all(ed)
L_300 = next(i for i, s in enumerate(ed.text().split("\n")) if "mov al, 300" in s)
js(ed, f"radEditor.executeEdits('type', [{{range: new monaco.Range({L_300 + 1}, 1, {L_300 + 2}, 1), text: ''}}]); 1")
check("MASM: pop ebx / add esp, 8 added, no squiggles left", wait(
    lambda: "pop ebx" in ed.text() and "add esp, 8" in ed.text() and
    not [m for m in markers(ed) if m[3] in (4, 8)], 10), (markers(ed), ed.text()))
w.save_all()
w.output.clear()
w.run_project(debug=False)
check("Ctrl+F5: the fixed MASM program builds (ml + link) and prints 'sum = 55'",
      wait(lambda: "sum = 55" in w.output.toPlainText(), 120), w.output.toPlainText()[-800:])
stop_session()

# ====================================================================== 2. NasmAverage: explain, what-if, CPU view
(WORK / "NasmAverage" / "main.asm").write_text(fixed_text("NasmAverage"), encoding="utf-8")
src = WORK / "NasmAverage" / "main.asm"
lines = src.read_text(encoding="utf-8").splitlines()
ed = open_project("NasmAverage")
wait(lambda: markers(ed) is not None, 5)
pump(1.0)
check("NasmAverage (fixed): no error / warning squiggles", not [m for m in markers(ed) if m[3] in (4, 8)],
      markers(ed))
L_ADD = next(i for i, s in enumerate(lines) if s.strip() == "add eax, [r10]")
ed.setCursorPosition(L_ADD, 6)
pump(0.2)
sim.sp_iter.setValue(2)
w.a_asm_explain.trigger()
ok = wait(lambda: not sim._busy and "EAX" in sim.explain.toPlainText(), 60)
txt = sim.explain.toPlainText()
check("Explain This Line: 2nd pass of 'add eax, [r10]' (EAX 10 -> 30) in Arabic",
      ok and "(10) -> 0x1e (30)" in txt and lang_text(txt), txt[:500])
shot(sim.dock, f"student_explain_{TAG}")
sim.cb_bits.setCurrentIndex(1)
sim.ed_code.setPlainText("mov al, 200\nadd al, 100\njc too_big\nmov bl, al\ntoo_big:")
sim.ed_values.setText("")
sim.b_whatif.click()
ok = wait(lambda: not sim._busy and sim.flags_table.rowCount() == 7, 30)
wt = sim.whatif_out.toPlainText()
check("What-If: 200 + 100 overflows AL (44, CF=1) and the jc is predicted taken, in Arabic",
      ok and "44" in wt and lang_text(wt), wt[:600])
shot(sim.dock, f"student_whatif_{TAG}")
sim.dock.setFloating(False)
sim.dock.hide()

hub = w.cpu_view
cpu = hub.view
L_JNZ = next(i for i, s in enumerate(lines) if s.strip() == "jnz .again")
L_AGAIN = next(i for i, s in enumerate(lines) if s.strip() == ".again:")
wait(lambda: getattr(ed, "_radcpu", {}).get("arrows"), 15)
check("editor jump arrow: jnz .again -> .again", any(
    a["src"] == L_JNZ and a["dst"] == L_AGAIN for a in getattr(ed, "_radcpu", {}).get("arrows", [])),
    getattr(ed, "_radcpu", {}).get("arrows"))
gdb_ok = bool(nd.find_nasm())
ed.toggle_breakpoint(L_JNZ)
pump(0.2)
w.run_project(debug=True)
ok = wait(lambda: w.session is not None and cpu.snap is not None and cpu.disasm.rows and cpu.disasm.pc is not None,
          120)
check("F5: stops on the breakpoint, the CPU view opens", ok and hub.dock.isVisible(),
      f"session={w.session} last={getattr(cpu, 'last_message', '')}")
if ok:
    hub.dock.setFloating(True)
    hub.dock.resize(1400, 780)
    if qh.REAL:
        hub.dock.move(-3000, 60)
    wait(lambda: cpu.disasm.rows and cpu.disasm.rows[0] is not None, 5)
    cur = next((r for r in cpu.disasm.rows if r.address == cpu.snap.pc), None)
    check("CPU view: current instruction is the jnz", cur is not None and cur.mnemonic in ("jne", "jnz"),
          cur and cur.text)
    info = cpu.disasm.info.text()
    check("CPU info line: jump is taken (in the UI language)", ("القفزة ستُنفَّذ" in info) if AR
          else ("Jump is taken" in info), info[:300])
    wait(lambda: (getattr(ed, "_radcpu", {}).get("taken") or {}).get("line") == L_JNZ, 10)
    tk = getattr(ed, "_radcpu", {}).get("taken")
    check("editor: the jnz arrow is marked taken", tk == {"line": L_JNZ, "taken": True}, tk)
    regs = cpu.regs.values
    check("registers pane: rbx = 2 (the counter after the first print)", regs.get("rbx") == 2, regs.get("rbx"))
    shot(cpu, f"student_cpu_native_{TAG}")
    # F8: the jnz runs (inline values are written for each line that ran before a stop)
    p0 = cpu.snap.pc
    cpu.handle_key(cpu.disasm.table, "F8", "")
    wait(lambda: cpu.snap is not None and cpu.snap.pc != p0 and cpu.disasm.pc == cpu.snap.pc, 25)
    check("F8: the taken jnz lands on .again (mov edx, ebx)", any(
        r.address == cpu.snap.pc and r.text.startswith("mov edx, ebx") for r in cpu.disasm.rows),
        [r.text for r in cpu.disasm.rows if r.address == cpu.snap.pc])
    wait(lambda: L_JNZ in (getattr(ed, "_radcpu", {}).get("inline") or {}), 10)
    inl = getattr(ed, "_radcpu", {}).get("inline") or {}
    check("editor: inline value after the jnz line (ZF=0)", "ZF=0" in inl.get(L_JNZ, ""), inl)
    check("editor page renders it ('; ZF=0' decoration in the DOM) + current-line highlight", wait(
        lambda: js(ed, "document.querySelectorAll('.rad-cpu-inline').length") and
        js(ed, "radEditor.getModel().getAllDecorations().some(d => d.options.className === 'rad-cur-line' && "
               f"d.range.startLineNumber === {L_AGAIN + 2})"), 10))
    pump(1.0)
    shot(w, f"student_ide_debug_{TAG}")
stop_session()
ed.toggle_breakpoint(L_JNZ)
if hub.dock.isFloating():
    hub.dock.setFloating(False)

# ====================================================================== 3. Emu8086Grade
ed = open_project("Emu8086Grade")
wait(lambda: len(markers(ed)) >= 4, 15)
got = codes(ed)
for rule_id, line in (("ASM601", 12), ("ASM605", 24), ("ASM602", 26), ("ASM102", 26)):
    check(f"Emu8086Grade squiggle {rule_id} on line {line}", (rule_id, line) in got, sorted(got))
hov = json.loads(js(ed, "JSON.stringify(radAsmLintHover(25, 6))") or "[]")
check("hover on the last line: 'no DOS exit' explained with mov ah, 4Ch / int 21h",
      any("4Ch" in h for h in hov) and all(lang_text(h) for h in hov), hov[:2])
shot(w, f"student_emu_squiggles_{TAG}")
fix_all(ed)
check("emu8086 quick fixes: DS loaded, '$' added, DOS exit added", wait(
    lambda: "mov ds, ax" in ed.text() and "'$'" in ed.text() and "mov ah, 4Ch" in ed.text(), 5), ed.text())
check("after word ptr: 'BX is used before it gets a value' (ASM401)", wait(
    lambda: any(m[1] == "ASM401" for m in markers(ed)), 10), markers(ed))
L_BX = next(i for i, s in enumerate(ed.text().split("\n")) if "[bx]" in s)
js(ed, f"radEditor.executeEdits('type', [{{range: new monaco.Range({L_BX + 1}, 1, {L_BX + 2}, 1), text: ''}}]); 1")
pump(0.3)                                              # the student deletes the wrong line (Monaco edit)
check("no squiggles left", wait(lambda: not [m for m in markers(ed) if m[3] in (4, 8)], 10), markers(ed))
w.save_all()
elines = ed.text().split("\n")
L_JAE = next(i for i, s in enumerate(elines) if s.strip() == "jae ok")
L_OK = next(i for i, s in enumerate(elines) if s.strip() == "ok:")
wait(lambda: getattr(ed, "_radcpu", {}).get("arrows"), 15)
check("8086 editor arrow: jae ok -> ok:", any(a["src"] == L_JAE and a["dst"] == L_OK
                                             for a in getattr(ed, "_radcpu", {}).get("arrows", [])),
      getattr(ed, "_radcpu", {}).get("arrows"))
w.run_project(debug=True)
check("8086: paused at the first instruction", wait(lambda: w.session is not None and
                                                    getattr(w.session, "paused", False), 30))
hub.dock.show()
hub.dock.raise_()
hub.dock.setFloating(True)
hub.dock.resize(1400, 780)
if qh.REAL:
    hub.dock.move(-3000, 60)
ok = wait(lambda: cpu.snap is not None and cpu.snap.bits == 16 and cpu.disasm.rows and cpu.disasm.pc is not None, 20)
check("8086: CPU view panes filled (16-bit)", ok and "ax" in cpu.regs.values and cpu.stack.rows and cpu.dump.data)
if ok:
    for _ in range(2):                             # mov ax, @data / mov ds, ax
        p0 = cpu.snap.pc
        cpu.handle_key(cpu.disasm.table, "F7", "")
        wait(lambda: cpu.snap.pc != p0 and cpu.disasm.pc == cpu.snap.pc, 15)
    check("8086: F7 x2 -> DS = AX = the data segment", cpu.regs.values.get("ds") == cpu.regs.values.get("ax") and
          cpu.regs.values.get("ds"), (cpu.regs.values.get("ds"), cpu.regs.values.get("ax")))
    wait(lambda: getattr(ed, "_radcpu", {}).get("inline"), 10)
    inl = getattr(ed, "_radcpu", {}).get("inline") or {}
    check("8086 editor: inline values (ds=...)", any("ds=" in v or "ax=" in v for v in inl.values()), inl)
    pump(1.0)
    check("8086: a zero register / stack word is not shown as a pointer to DS:0 ('<ask>')",
          cpu.reg_comment("bx", 0) == "" and not [c for a, c in cpu.stack.comments.items()
                                                    if dict(cpu.stack.rows).get(a) == 0],
          (cpu.reg_comment("bx", 0), cpu.stack.comments))
    fail_var = next((v for v in w.session.program.variables if v.name.lower() == "fail"), None)
    off = fail_var.linear - (cpu.snap.segs.get("ds", 0) << 4) if fail_var is not None else -1
    check("8086: a real offset still gets its label (DX = offset of 'fail' -> <fail>)",
          off > 0 and cpu.reg_comment("dx", off) == "<fail>", (off, off > 0 and cpu.reg_comment("dx", off)))
    shot(cpu, f"student_cpu_8086_{TAG}")
stop_session()
if hub.dock.isFloating():
    hub.dock.setFloating(False)
qh.finish(w)
