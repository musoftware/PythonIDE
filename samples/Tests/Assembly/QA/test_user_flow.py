"""Assembly QA: the IDE driven the way a user works (offscreen, QSettings organisation RADIDE-TEST, cleared).

    python samples/Tests/Assembly/QA/test_user_flow.py [phase ...]

Phases (default: all):
  newproj   File > New Project dialog -> every console template -> Ctrl+F5 -> answer on the Program Input bar
  forms     the NASM form template: designer opens, Ctrl+F5 builds, the handler answers a button click
  errors    a broken main.asm: the Error List row after Ctrl+F5 (file + line)
  intel     completion / hover / go to definition of the plugin on main.asm
  debug     F5 with an editor breakpoint on a NASM console project: stop, Registers / Disassembly / Memory,
            F10, continue to the end (the program reads stdin)
  cdebug    F5 on a C (GUI Bridge) project with a breakpoint in Form1_Load: regression of the gdb path
  emu       8086 emulator project: F5 paused, F10, registers panel
  help      Help > Help Files (CHM) lists the Assembly course; Tutorials view lists the course
  regress   C / C++ / Fortran / Rust (GUI Bridge) new projects still build
  look      Arabic UI + dark theme screenshots (widget.grab) of an assembly project with the debugger windows
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
OUT = Path(os.environ.get("QA_OUT") or Path(tempfile.gettempdir()) / "radide-asm-qa")
SHOTS = OUT / "shots"
WORK = OUT / "work"
SHOTS.mkdir(parents=True, exist_ok=True)
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True, exist_ok=True)

__import__("PyQt6.QtWebEngineWidgets")  # WebEngine before QApplication
from PyQt6.QtCore import QCoreApplication, QSettings, Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST-asmqa")
app = QApplication(sys.argv[:1])
QSettings().clear()
LANG = os.environ.get("ASMQA_LANG", "")
if LANG:
    QSettings().setValue("options/ui_language", LANG)
MSGS = []
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
for _n in ("warning", "critical", "information"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, _n=_n, **k: (MSGS.append((_n, [str(x)[:300] for x in a[1:3]])),
                                                                   QMessageBox.StandardButton.Ok)[1]))
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:900]}]"), flush=True)
    return bool(cond)


def pump(sec=0.5):
    t = time.time()
    while time.time() - t < sec:
        app.processEvents()
        time.sleep(0.01)


def wait(pred, timeout=30.0):
    t = time.time()
    while time.time() - t < timeout:
        app.processEvents()
        try:
            if pred():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.03)
    return False


def shot(widget, name):
    p = SHOTS / f"{name}.png"
    widget.grab().save(str(p))
    print("SHOT", p, flush=True)


_WIN = []


def window():
    if _WIN:
        return _WIN[0]
    from radide.app import MainWindow
    if LANG:                                  # like radide/__main__.py does with the saved language
        from radide import i18n
        i18n.set_language(app, LANG)
    w = MainWindow()
    w.resize(1500, 950)
    w.show()
    pump(3)
    _WIN.append(w)
    return w


def new_project(w, plugin_id, template_id, name):
    """File > New Project with the real dialog (language + template + name + location)."""
    from radide.dialogs import NewProjectDialog
    from radide.features.solution_ui import create_project_from_dialog
    dlg = NewProjectDialog(w)
    item = None
    for i in range(dlg.langs.topLevelItemCount()):
        g = dlg.langs.topLevelItem(i)
        for j in range(g.childCount()):
            if g.child(j).data(0, Qt.ItemDataRole.UserRole) == plugin_id:
                item = g.child(j)
    assert item is not None, plugin_id
    dlg.langs.setCurrentItem(item)
    app.processEvents()
    tids = [dlg.templates.item(k).data(Qt.ItemDataRole.UserRole) for k in range(dlg.templates.count())]
    assert template_id in tids, (template_id, tids)
    dlg.templates.setCurrentRow(tids.index(template_id))
    dlg.name.setText(name)
    dlg.location.setText(str(WORK))
    app.processEvents()
    if dlg.solution_mode.findData("new") >= 0:
        dlg.solution_mode.setCurrentIndex(dlg.solution_mode.findData("new"))
    project = create_project_from_dialog(w, dlg)
    dlg.deleteLater()
    pump(1.5)
    return project


def run(w, debug=False, answer=None, timeout=180):
    """Ctrl+F5 / F5; *answer*: line typed into the Program Input bar when the program waits."""
    w.output.clear()
    w.run_project(debug=debug)
    if answer is not None:
        ok = wait(lambda: getattr(w, "dock_program_input", None) is not None and w.dock_program_input.isVisible()
                  and w.session is not None and any(m in w.output.toPlainText() for m in ("Build succeeded", "------ Run:")),
                  timeout)
        if ok:
            pump(1.5)                       # the prompt
            bar = w.dock_program_input.widget()
            bar.edit.setText(answer)
            bar.send()
    wait(lambda: w.session is None, timeout)
    return w.output.toPlainText()


def error_rows(w):
    el = w.error_list
    return [tuple(el.topLevelItem(i).text(c) for c in range(el.columnCount())) for i in range(el.topLevelItemCount())]


# ------------------------------------------------------------------------------------------------ phases
def p_newproj():
    from radide.asm import toolchain as tc
    w = window()
    has_vs = bool(tc.find_masm("x64"))
    cases = [("asm-nasm", "nasm_console_x64"), ("asm-nasm", "nasm_console_x86"),
             ("asm-fasm", "fasm_console_x64"), ("asm-fasm", "fasm_console_x86"),
             ("asm-gas", "gas_console_x64"), ("asm-gas", "gas_console_x64_intel")]
    if has_vs:
        cases += [("asm-masm", "masm_console_x64"), ("asm-masm", "masm_console_x86")]
    for pid, tid in cases:
        name = "Q" + "".join(x.title() for x in tid.split("_"))
        project = new_project(w, pid, tid, name)
        check(f"{tid}: New Project opens it", project is not None and w.project is not None
              and w.project.language == pid, w.project and w.project.language)
        out = run(w, False, "7")
        tail = out[-700:]
        check(f"{tid}: Ctrl+F5 builds", "Build succeeded" in out and "Build failed" not in out, tail)
        after = out.split("Build succeeded", 1)[-1]
        check(f"{tid}: program read '7' from the Program Input bar and ended", any(
            n in after for n in ("49", "343", "= 14", "= 28", "= 107", "= 6")), after[-500:])
        print("   output:", after.strip().replace("\n", " | ")[:300])
        if tid == "nasm_console_x64":
            shot(w, "newproj_nasm_x64_run")


def p_forms():
    w = window()
    new_project(w, "asm-nasm", "nasm_forms", "QAsmForms")
    pump(2)
    check("forms: project has Form1 and opened", w.project is not None and "Form1" in w.project.forms,
          w.project and w.project.forms)
    shot(w, "forms_designer")
    folder = Path(w.project.folder)
    # build like Ctrl+F5 does, then click btnAdd through the real bridge host
    from radide.asm.build import Builder
    logs = []
    ok = Builder(folder, log=logs.append).build()
    check("forms: build", ok, "\n".join(logs)[-600:])
    r = subprocess.run([sys.executable, str(ROOT / "samples/Tests/Assembly/CoreTests/test_form_bridge.py"), str(folder)],
                       capture_output=True, text=True, timeout=180, cwd=str(ROOT))
    check("forms: btnAdd_Click handler runs in the bridge window", r.returncode == 0 and "OK" in r.stdout,
          (r.stdout + r.stderr)[-600:])


def p_errors():
    w = window()
    new_project(w, "asm-nasm", "nasm_console_x64", "QAsmErrors")
    main = Path(w.project.folder) / "main.asm"
    lines = main.read_text(encoding="utf-8").splitlines()
    idx = next(i for i, ln in enumerate(lines) if ln.strip().startswith("mov ") or ln.strip().startswith("lea "))
    lines.insert(idx, "    mov rax, rbx, rcx")
    main.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        w.reload_module("main.asm") if hasattr(w, "reload_module") else None
    except Exception:  # noqa: BLE001
        pass
    out = run(w, False, None, 120)
    pump(1)
    rows = error_rows(w)
    check("errors: Ctrl+F5 reports Build failed", "Build failed" in out or "error" in out.lower(), out[-400:])
    check("errors: Error List row main.asm at the broken line",
          any("main.asm" in r and str(idx + 1) in r for r in rows), rows)
    shot(w, "errors_error_list")


def p_intel():
    w = window()
    new_project(w, "asm-nasm", "nasm_console_x64", "QAsmIntel")
    folder = Path(w.project.folder)
    from radide.languages import get_plugin
    plugin = get_plugin("asm-nasm")
    main = folder / "main.asm"
    src = main.read_text(encoding="utf-8")
    lines = src.splitlines()
    # (0-based line / column, like the editor calls them)
    probe = src.rstrip("\n") + "\n    mo"
    comps = plugin.completions(probe, len(probe.splitlines()) - 1, 6, main)
    labels = [c.name for c in comps]
    check("intel: completion 'mo' offers mov/movzx", any(x.lower().startswith("mov") for x in labels), labels[:20])
    call_line = next(i for i, ln in enumerate(lines) if "call" in ln and "printf" in ln)
    h = plugin.hover(src, call_line, lines[call_line].index("printf") + 2, main)
    check("intel: hover on printf shows a signature", h and "printf" in h, h)
    mov_line = next(i for i, ln in enumerate(lines) if ln.strip().startswith("mov "))
    h2 = plugin.hover(src, mov_line, lines[mov_line].index("mov") + 1, main)
    check("intel: hover on mov describes the instruction", h2 and len(h2) > 10, h2)
    import re
    target = None
    for i, ln in enumerate(lines):
        m = re.match(r"\s*(\w+)\s*:?\s+(?:d[bwdq]|resb|resq|equ)\b", ln)
        if m:
            lab = m.group(1)
            use = next((j for j, l2 in enumerate(lines) if j > i and re.search(rf"\b{lab}\b", l2)), None)
            if use is not None:
                target = (i, lab, use)
                break
    if check("intel: template has a data label used in code", target):
        i, lab, use = target
        d = plugin.definition(src, use, lines[use].index(lab) + 1, main)
        check(f"intel: go to definition of {lab} -> line {i + 1}", d and d[1] == i, d)
    tip = plugin.calltip(src.rstrip("\n") + "\n    mov r8, 0", len(lines), 9, main)
    print("   calltip:", str(tip)[:200])
    w.open_module("main.asm") if hasattr(w, "open_module") else None
    pump(3)
    shot(w, "intel_editor")


def p_debug():
    w = window()
    new_project(w, "asm-nasm", "nasm_console_x64", "QAsmDebug")
    folder = Path(w.project.folder)
    lines = (folder / "main.asm").read_text(encoding="utf-8").splitlines()
    bp = next(i for i, ln in enumerate(lines) if "call" in ln and "printf" in ln)     # 0-based
    w.open_module("main.asm")
    pump(3)
    mv = w.modviews.get("main.asm")
    check("debug: main.asm open in the editor", mv is not None, list(w.modviews))
    mv.editor.set_breakpoints({bp})
    stops = []
    orig = w._on_stopped
    w._on_stopped = lambda info: (stops.append(info), orig(info))
    w.output.clear()
    w.run_project(debug=True)
    ok = wait(lambda: stops or w.session is None, 180)
    info = stops[-1] if stops else None
    check("debug: F5 stops on the editor breakpoint in main.asm",
          ok and info is not None and Path(info.file).name == "main.asm" and info.line == bp + 1,
          (info and (info.file, info.line)) or w.output.toPlainText()[-800:])
    hub = getattr(w, "native_debug", None)
    if info is not None and hub is not None:
        hub.docks["registers"].show()
        hub.docks["registers"].raise_()
        rv = hub.views["registers"]
        check("debug: Registers window filled", wait(lambda: "rip" in rv.values, 15), list(rv.values)[:10])
        hub.show_disassembly()
        dv = hub.views["disassembly"]
        check("debug: Disassembly window has the current instruction", wait(lambda: dv.instrs and dv.pc is not None, 15))
        hub.show_memory("$rsp")
        mem = hub.views["memory"]
        check("debug: Memory window reads $rsp", wait(lambda: mem.base is not None and len(mem.data) > 0, 15))
        pump(0.5)
        shot(w, "debug_nasm_stopped")
        n0 = len(stops)
        w.session.step_over()
        check("debug: F10 moves to the next line", wait(lambda: len(stops) > n0, 20) and stops[-1].line > bp + 1,
              stops[-1].line if stops else None)
        mv.editor.set_breakpoints(set())
        w.session.set_breakpoint("main.asm", bp + 1, False)
        w.session.cont()
    # the template reads a number with scanf: under F5 its stdin is the Program Input bar too
    dock = getattr(w, "dock_program_input", None)
    check("debug: Program Input bar shown under F5", dock is not None and dock.isVisible())
    wait(lambda: "Enter a number" in w.output.toPlainText(), 20)
    if dock is not None:
        dock.widget().edit.setText("7")
        dock.widget().send()
    ended = wait(lambda: w.session is None, 25)
    out = w.output.toPlainText()
    check("debug: program read 7 from the bar under F5 and ended", ended and "7 squared is 49" in out, out[-600:])
    if not ended:
        w.stop_project()
        wait(lambda: w.session is None, 15)
    w._on_stopped = orig


def p_cdebug():
    w = window()
    new_project(w, "c-bridge", "windows", "QCDebug")
    folder = Path(w.project.folder)
    code = folder / "Form1.c"
    if not code.exists():
        check("cdebug: Form1.c exists", False, list(folder.iterdir()))
        return
    stops = []
    orig = w._on_stopped
    w._on_stopped = lambda info: (stops.append(info), orig(info))
    # add a Load handler line with a breakpoint
    from radide.languages import get_plugin
    plugin = get_plugin("c-bridge")
    print("c-bridge handlers:", plugin.handlers_in_project(folder, w.project) if hasattr(plugin, "handlers_in_project")
          else "?")
    w.output.clear()
    w.run_project(debug=False)
    ok = wait(lambda: "Build succeeded" in w.output.toPlainText() or "rror" in w.output.toPlainText()
              or w.session is None, 180)
    pump(3)
    out = w.output.toPlainText()
    check("cdebug: C project Ctrl+F5 builds and starts (regression)", ok and "rror" not in out and "Traceback" not in out,
          out[-600:])
    w.stop_project()
    wait(lambda: w.session is None, 20)
    # a statement in Form1_Load with a breakpoint (F5 attaches gdb before the Load event runs)
    code.write_text(code.read_text(encoding="utf-8").replace(
        "    /* runs when the form is shown */", "    /* runs when the form is shown */\n    rad_set(\"Form1\", \"Text\", \"QA\");"),
        encoding="utf-8")
    src = code.read_text(encoding="utf-8").splitlines()
    bp = next(i for i, ln in enumerate(src) if "rad_set(" in ln)
    w.open_module("Form1.c") if "Form1.c" in getattr(w.project, "modules", []) else w.open_code("Form1") \
        if hasattr(w, "open_code") else None
    pump(2)
    ed = (w.modviews.get("Form1.c") or w.codeviews.get("Form1"))
    if ed is not None:
        ed.editor.setText(code.read_text(encoding="utf-8"))
        ed.editor.set_breakpoints({bp})
    else:
        w.breakpoints["Form1.c"] = {bp}
    w.output.clear()
    w.run_project(debug=True)
    ok = wait(lambda: stops or w.session is None, 180)
    out = w.output.toPlainText()
    check("cdebug: C project F5 stops on the breakpoint in Form1_Load (regression)",
          ok and stops and Path(stops[-1].file).name == "Form1.c" and stops[-1].line == bp + 1,
          (stops and (stops[-1].file, stops[-1].line)) or out[-700:])
    hub = getattr(w, "native_debug", None)
    if stops and hub is not None:
        hub.docks["registers"].show()
        rv = hub.views["registers"]
        check("cdebug: Registers window works for C too", wait(lambda: "rip" in rv.values, 15))
    w.stop_project()
    wait(lambda: w.session is None, 20)
    w._on_stopped = orig


def p_emu():
    w = window()
    new_project(w, "emu8086", next(iter(_emu_templates())), "QEmu")
    stops = []
    orig = w._on_stopped
    w._on_stopped = lambda info: (stops.append(info), orig(info))
    w.run_project(debug=True)
    check("emu: F5 pauses on the first instruction", wait(lambda: stops, 30), w.output.toPlainText()[-300:])
    n = len(stops)
    if stops:
        w.session.step_over()
        check("emu: F10 steps", wait(lambda: len(stops) > n, 10) and stops[-1].line != stops[n - 1].line,
              [s.line for s in stops])
    pump(1)
    shot(w, "emu_paused")
    w.stop_project()
    wait(lambda: w.session is None, 10)
    w._on_stopped = orig


def _emu_templates():
    from radide.languages import get_plugin
    p = get_plugin("emu8086")
    return [t[0] for t in p.project_templates()]


def p_help():
    w = window()
    from radide.features import tutorials as TU
    files = [f for f, _t in TU.chm_files()]
    check("help: Help Files (CHM) lists RADIDE_ASSEMBLY_ar.chm", "RADIDE_ASSEMBLY_ar.chm" in files, files)
    menu = getattr(w, "tutorials_chm_menu", None)
    if menu is not None:
        menu.aboutToShow.emit()
        texts = [a.text() for a in menu.actions()]
        check("help: the menu has an Assembly entry", any("ssembly" in t or "أسمبل" in t or "التجميع" in t for t in texts),
              texts)
    from radide import tutorials as T
    ids = [c.id for c in T.courses()]
    check("help: Tutorials has the assembly course", "assembly" in ids, ids)
    TU.show_tutorials(w, "assembly")
    pump(3)
    shot(w, "tutorials_assembly")


def p_regress():
    from radide.languages import get_plugin
    from radide.model import Project
    from radide.workspace import create_project
    for pid in ("c-bridge", "cpp-bridge", "fortran-bridge", "rust-bridge"):
        folder = WORK / f"Reg_{pid.replace('-', '_')}"
        shutil.rmtree(folder, ignore_errors=True)
        plugin = get_plugin(pid)
        create_project(folder, "Reg" + pid.split("-")[0].title(), pid)
        project = Project.load(folder)
        try:
            spec = plugin.run_spec(folder, project.startup, sys.executable)
            cmd = plugin.build_command(folder, Project.load(folder))
        except Exception as e:  # noqa: BLE001
            check(f"regress: {pid} run spec", False, e)
            continue
        if not cmd:
            check(f"regress: {pid} has a build command", False)
            continue
        r = subprocess.run(cmd, shell=True, cwd=str(folder), env=spec.env, capture_output=True, text=True, timeout=600)
        check(f"regress: {pid} new project builds", r.returncode == 0, (r.stdout + r.stderr)[-800:])


def p_look():
    w = window()
    try:
        from radide.features.workbench import set_theme
        set_theme(w, "Dark")
    except Exception as e:  # noqa: BLE001
        check("look: dark theme", False, e)
    new_project(w, "asm-nasm", "nasm_console_x64", "QAsmLook")
    w.open_module("main.asm")
    pump(3)
    hub = getattr(w, "native_debug", None)
    if hub is not None:
        hub.docks["registers"].show()
        hub.docks["disassembly"].show()
    pump(1)
    shot(w, f"look_{LANG or 'en'}_dark")
    from radide import i18n
    menus = [i18n.shown(a) for a in w.menuBar().actions()]
    if LANG == "ar":
        check("look: Arabic menus", any(any("\u0600" <= ch <= "\u06ff" for ch in t) for t in menus), menus)
        texts = []
        for a in w.menuBar().actions():
            m = a.menu()
            if m is not None:
                m.aboutToShow.emit()
                texts += [i18n.shown(x) for x in m.actions()]
                for x in m.actions():
                    if x.menu() is not None:
                        x.menu().aboutToShow.emit()
                        texts += [i18n.shown(y) for y in x.menu().actions()]
        asm_en = [t for t in texts if any(k in t for k in ("Assembly", "Registers", "Disassembly", "Memory 1",
                                                         "Instruction", "8086"))
                  and not any("؀" <= ch <= "ۿ" for ch in t)]
        check("look: assembly menu entries are translated", not asm_en, asm_en)
    if hub is not None:
        shot(hub.docks["registers"], f"look_{LANG or 'en'}_registers")


def p_tutor():
    """Tutorials view: an 'asm run' block of the Assembly course runs with "جرّبه" (try it)."""
    w = window()
    from radide.features import tutorials as TU
    from radide import tutorials as T
    from radide.tutorials.html import tryable
    course = next(c for c in T.courses() if c.id == "assembly")
    found = None
    for les in course.lessons:
        panel = TU.show_tutorials(w, "assembly", les.id)
        pump(1)
        for n, b in panel.blocks.items():
            if b.lang == "asm" and not b.gui and tryable(b) and not b.reads_stdin():     # has the button
                found = (les.id, n)
                break
        if found:
            break
    if not check("tutor: a runnable 'asm run' block exists", found):
        return
    shot(w, "tutor_lesson")
    w.output.clear()
    ok = panel.try_block(found[1])
    check(f"tutor: جرّبه opens the block of {found[0]} as an asm-nasm project", ok and w.project is not None
          and w.project.language == "asm-nasm", w.project and w.project.language)
    wait(lambda: w.session is not None, 10)
    wait(lambda: w.session is None, 180)
    out = w.output.toPlainText()
    check("tutor: the block builds and runs", "Build succeeded" in out and "exited with code 0" in out, out[-500:])


def p_openfolder():
    """File > Open Folder on loose NASM / GNU as folders (no project file): opened in place, F5 stops on a
    breakpoint, the program ends with its output."""
    _open_folder("NasmLoose", "hello.asm", "call printf", "6 * 7 = 42")
    _open_folder("GasLoose", "hello.s", "call printf", "GNU as loose folder: 2026")
    _open_folder("NasmLooseInput", "input.asm", "call scanf", "Twice 21 is 42", answer="21")


def _open_folder(name, file, bp_text, expect, answer=None):
    w = window()
    from radide.features.open_detect import open_inplace
    from radide.project_detect import detect
    src = ROOT / "samples/Tests/Assembly/OpenFolder" / name
    if not src.is_dir():
        src = Path(__file__).resolve().parent / name
    folder = WORK / name
    shutil.copytree(src, folder)
    cand = [c for c in detect(folder).candidates() if c.kind == "asm"]
    check(f"openfolder {name}: detected as Assembly", cand, [c.kind for c in detect(folder).candidates()])
    ok = open_inplace(w, folder, cand)
    check(f"openfolder {name}: opened in place", ok and w.project is not None and getattr(w.project, "foreign", False))
    lines = (folder / file).read_text(encoding="utf-8").splitlines()
    bp = next(i for i, ln in enumerate(lines) if bp_text in ln)
    w.open_module(file)
    pump(2)
    mv = w.modviews.get(file)
    if mv is not None:
        mv.editor.set_breakpoints({bp})
    stops = []
    orig = w._on_stopped
    w._on_stopped = lambda info: (stops.append(info), orig(info))
    w.output.clear()
    w.run_project(debug=True)
    wait(lambda: stops or w.session is None, 180)
    check(f"openfolder {name}: F5 stops on the breakpoint in {file}",
          stops and Path(stops[-1].file).name == file and stops[-1].line == bp + 1,
          (stops and (stops[-1].file, stops[-1].line)) or w.output.toPlainText()[-2500:])
    if stops:
        w.session.set_breakpoint(file, bp + 1, False)
        if mv is not None:
            mv.editor.set_breakpoints(set())
        w.session.cont()
    if answer is not None:
        dock = getattr(w, "dock_program_input", None)
        check(f"openfolder {name}: Program Input bar shown under F5", dock is not None and dock.isVisible())
        if dock is not None:
            dock.widget().edit.setText(answer)
            dock.widget().send()
    wait(lambda: w.session is None, 30)
    check(f"openfolder {name}: the program ends with its output", expect in w.output.toPlainText(),
          w.output.toPlainText()[-400:])
    if w.session is not None:
        w.stop_project()
        wait(lambda: w.session is None, 10)
    w._on_stopped = orig
    if answer is not None:                                   # Ctrl+F5 with the Program Input bar
        out = run(w, False, answer, 120)
        check(f"openfolder {name}: Ctrl+F5 reads the Program Input bar", expect in out, out[-400:])


PHASES = {"newproj": p_newproj, "forms": p_forms, "errors": p_errors, "intel": p_intel, "debug": p_debug,
          "cdebug": p_cdebug, "emu": p_emu, "help": p_help, "regress": p_regress, "look": p_look,
          "tutor": p_tutor, "openfolder": p_openfolder}

if __name__ == "__main__":
    chosen = sys.argv[1:] or list(PHASES)
    try:
        for ph in chosen:
            print(f"######## {ph}", flush=True)
            try:
                PHASES[ph]()
            except Exception:  # noqa: BLE001
                import traceback
                check(f"{ph}: no exception", False, traceback.format_exc())
        if _WIN:
            import re
            errs = [ln for ln in _WIN[0].output.toPlainText().splitlines() if re.search(r"Traceback", ln)]
            check("no Traceback in the Output window", not errs, errs[:5])
    finally:
        ok = sum(1 for _, c in RESULTS if c)
        print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}", flush=True)
        print("MSGS:", MSGS[:10], flush=True)
        try:
            if _WIN:
                _WIN[0].close()
                pump(1)
        except Exception:  # noqa: BLE001
            pass
        QSettings().clear()
        QSettings().sync()
        sys.stdout.flush()
        os._exit(0 if RESULTS and ok == len(RESULTS) else 1)
