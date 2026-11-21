"""End-to-end QA of DOS development and the visual DOS / retro designers, as a user would do it in the real IDE
(qh.py harness: QSettings org "RADIDE-TEST", screenshots with widget.grab() only).

    python samples/Tests/Retro/DOSQA/qa_dos_e2e.py [phases]      # QA_LANG=ar QA_THEME=dark for Arabic + dark

phases (all by default):
  dos     File > New Project > DOS: one project per type (QBasic, Pascal, C, assembly .COM, batch) -> Tools > Retro >
          DOS Programming > Build DOS Program (real MZ / COM) -> Run with Captured Output (DOSBox-X, keys typed) ->
          Show Last DOS Screen; one real windowed Ctrl+F5-style run (python -m radide.retro.dos.run) that ends itself
  old     File > Open Folder on old QBasic / Turbo Pascal / Turbo C sources -> DOS project -> build -> run
  tui     New Project > DOS Text-Mode Forms App for FreeBASIC, Pascal, C and asm: the designer tab, add a TextBox and
          a Button with the toolbox, save (code regenerated), handler code, build, keyboard in DOSBox-X (Tab + typing +
          Enter on the new button) and mouse clicks (RADMOUSE) compared with the simulator; Build && Run in a
          DOSBox-X window (started, then stopped by us)
  ansi    the ANSI editor: draw, save .ans (SAUCE), reopen, same cells; .BIN round trip; PNG export
  game    Tools > Retro > Game Designers: Atari 2600 -> Stella, NES (2 screens) -> Mesen, Game Boy -> mGBA,
          DOS mode 13h -> DOSBox-X (Build && Run with the checks; emulators started, then stopped by us)
  i18n    the new menus are translated (Arabic run) and the strings seen are in ar.json
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
LANG = os.environ.get("QA_LANG", "")
THEME = os.environ.get("QA_THEME", "")
TAG = (LANG or "en") + ("_" + THEME if THEME else "")
os.environ.setdefault("QA_NAME", "dosqa_" + TAG)
import qh  # noqa: E402

from PyQt6.QtCore import QPointF, Qt  # noqa: E402
from PyQt6.QtGui import QMouseEvent  # noqa: E402
from PyQt6.QtWidgets import QInputDialog  # noqa: E402

WORK = Path(qh.WORK) / ("dosqa_" + TAG)
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)
ALL = ["dos", "old", "tui", "ansi", "game", "i18n"]
PHASES = [a for a in sys.argv[1:] if a in ALL] or ALL
ROOT = Path(qh.ROOT)

if LANG:
    from radide import i18n
    i18n.set_language(qh.app, LANG)
w = qh.window()
if THEME:
    from radide.features.workbench import set_theme
    set_theme(w, THEME.capitalize())
    qh.pump(0.5)

from radide.features import dos_ide  # noqa: E402
from radide.retro.dos import build as B  # noqa: E402
from radide.retro.dos import dosbox  # noqa: E402


def shot(widget, name):
    return qh.shot(widget, f"{TAG}_{name}")


def new_project(plugin_id: str, template_id: str, name: str):
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
    qh.app.processEvents()
    tids = [dlg.templates.item(k).data(Qt.ItemDataRole.UserRole) for k in range(dlg.templates.count())]
    assert template_id in tids, (template_id, tids)
    dlg.templates.setCurrentRow(tids.index(template_id))
    dlg.name.setText(name)
    dlg.location.setText(str(WORK))
    qh.app.processEvents()
    if dlg.solution_mode.findData("new") >= 0:
        dlg.solution_mode.setCurrentIndex(dlg.solution_mode.findData("new"))
    if template_id in ("dosqb_hello", "tui_c"):
        dlg.show()
        qh.pump(0.3)
        shot(dlg, f"newproject_{plugin_id}")
    project = create_project_from_dialog(w, dlg)
    dlg.deleteLater()
    qh.pump(1.5)
    return project


def menu_action(menu, english: str):
    from radide.i18n import english as en
    for a in menu.actions():
        if en(a, a.text()).replace("&", "") == english.replace("&", ""):
            return a
    return None


def wait_proc(proc, timeout=180):
    if proc is None:
        return False
    qh.wait(lambda: proc.state() == proc.ProcessState.NotRunning, timeout)
    qh.pump(0.4)
    return proc.state() == proc.ProcessState.NotRunning


def is_dos_program(path: Path) -> bool:
    data = path.read_bytes() if path.is_file() else b""
    if path.suffix.upper() == ".COM":
        return 0 < len(data) <= 65280
    return data[:2] == b"MZ" and b"PE\0\0" not in data[:0x400]


# ====================================================================== DOS projects
DOS_CASES = [("dos-qbasic", "dosqb_hello", "QbHello", "Ali~", "Welcome to DOS programming, Ali"),
             ("dos-pascal", "dostp_menu", "PasMenu", "1 2 3 4", "Goodbye"),
             ("dos-c", "dostc_hello", "CHello", "Ali~", "Welcome to DOS programming, Ali"),
             ("dos-asm", "dosasm_com", "AsmCom", "", "Hello from a .COM program"),
             ("dos-batch", "dosbat_hello", "BatHello", "", "Done.")]


def phase_dos():
    m = getattr(w, "dos_menu", None)
    qh.check("Tools > Retro > DOS Programming menu exists", m is not None)
    for plugin_id, tid, name, keys, want in DOS_CASES:
        project = new_project(plugin_id, tid, name)
        ok = project is not None and w.project is not None and w.project.language == plugin_id
        qh.check(f"[{name}] New Project > DOS > {tid} opens", ok, getattr(w.project, "language", None))
        if not ok:
            continue
        folder = Path(w.project.folder)
        s = B.settings_for(w.project)
        act = menu_action(m, "Build DOS Program")
        w.output.clear()
        act.trigger()
        wait_proc(getattr(w, "_dos_proc", None))
        out = w.output.toPlainText()
        if s["kind"] == "batch":
            qh.check(f"[{name}] build = GOTO / CALL check passes", "Traceback" not in out and
                     not [d for d in B.read_diagnostics(folder).get("diags", []) if d["severity"] == "Error"],
                     out[-400:])
        else:
            exe = folder / B.output_name(s)
            qh.check(f"[{name}] Build DOS Program -> real DOS program {exe.name}", is_dos_program(exe), out[-600:])
        # Run with Captured Output... (asks for the keys to type)
        orig = QInputDialog.getText
        QInputDialog.getText = staticmethod(lambda *a, **k: (keys, True))
        try:
            w.output.clear()
            menu_action(m, "Run with Captured Output...").trigger()
        finally:
            QInputDialog.getText = orig
        wait_proc(getattr(w, "_dos_proc", None), 120)
        qh.pump(0.6)
        out = w.output.toPlainText()
        qh.check(f"[{name}] runs in DOSBox-X: '{want}'", want.lower() in out.lower(), out[-700:])
        dlg = getattr(w, "_dos_screen", None)
        if dlg is not None and dlg.isVisible():
            shot(dlg, f"lastscreen_{name}")
            dlg.close()
        if plugin_id == "dos-qbasic":
            shot(w, "ide_dos_qbasic")
    # one real windowed run, like Ctrl+F5 (keep window off so that DOSBox-X closes when the program ends)
    folder = WORK / "AsmCom" / "AsmCom"
    if (folder / "project.radproj").is_file():
        from radide.model import Project
        p = Project.load(folder)
        p.extra.setdefault("dos", {})["keep_window"] = False
        p.save()
        from radide.languages import get_plugin
        args = list(get_plugin("dos-asm").run_spec(folder, "MAIN", "").args)
        qh.check("Ctrl+F5 spec runs radide.retro.dos.run", "radide.retro.dos.run" in args, args)
        t0 = time.time()
        r = subprocess.run([sys.executable, "-m", "radide.retro.dos.run", str(folder)], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=120)
        qh.check(f"windowed DOSBox-X run of AsmCom ends by itself ({time.time() - t0:.1f} s, exit {r.returncode})",
                 r.returncode == 0 and "Starting" in r.stdout, r.stdout[-500:] + r.stderr[-300:])


# ====================================================================== old sources
OLD = [("MoonLander", "dos-qbasic", "~~~~~~~~~~~~", "CRASH AT 100"), ("TurboPascalSort", "dos-pascal", "", "sorted"),
       ("TurboCStars", "dos-c", "xx", "Stars done.")]


def phase_old():
    from radide.features import open_detect
    from radide.single_instance import open_target
    open_detect.TEST_HOOK = lambda det: None          # the dialog's default choice ("create a project")
    for name, lang, keys, want in OLD:
        src = ROOT / "samples" / "Tests" / "Retro" / "DOSOldSources" / name
        dst = WORK / "old" / name
        shutil.copytree(src, dst)
        before = {p.name: p.read_bytes() for p in dst.iterdir() if p.is_file()}
        open_target(w, dst)
        qh.pump(2)
        ok = w.project is not None and w.project.language == lang
        qh.check(f"[old {name}] File > Open Folder -> {lang} project", ok, getattr(w.project, "language", None))
        if not ok:
            continue
        w.output.clear()
        dos_ide.build_program(w)
        wait_proc(getattr(w, "_dos_proc", None))
        s = B.settings_for(w.project)
        qh.check(f"[old {name}] builds unchanged sources with the free compiler", is_dos_program(dst / B.output_name(s))
                 and all((dst / n).read_bytes() == b for n, b in before.items()), w.output.toPlainText()[-600:])
        run = dosbox.DosRun(mounts=[("C", dst)], path=["Z:\\BIN", "Z:\\DOS"])
        r = dosbox.capture_text(run, dst, B.output_name(s), keys=keys, timeout=30, log=lambda *_a: None)
        text = r["stdout"] + "\n" + r["screen"]
        qh.check(f"[old {name}] runs in DOSBox-X: '{want}'", want.lower() in text.lower(), text[-500:])
        if name == "MoonLander":
            shot(w, "old_moonlander")
    open_detect.TEST_HOOK = None


# ====================================================================== text-mode forms
def mouse_ev(widget, kind, cell):
    r = widget.cell_rect(*cell)
    p = QPointF(r.center())
    buttons = Qt.MouseButton.NoButton if kind == QMouseEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton
    return QMouseEvent(kind, p, p, Qt.MouseButton.LeftButton, buttons, Qt.KeyboardModifier.NoModifier)


def draw(d, tool: str, a, b):
    row = next(i for i in range(d.toolbox.count()) if d.toolbox.item(i).data(Qt.ItemDataRole.UserRole) == tool)
    d.toolbox.setCurrentRow(row)
    cv = d.canvas
    cv.mousePressEvent(mouse_ev(cv, QMouseEvent.Type.MouseButtonPress, a))
    cv.mouseMoveEvent(mouse_ev(cv, QMouseEvent.Type.MouseMove, b))
    cv.mouseReleaseEvent(mouse_ev(cv, QMouseEvent.Type.MouseButtonRelease, b))
    return d.screen.controls[-1]


HANDLER = {"freebasic": '  TuiSetText Label1, "Hi " + TuiGetText$(txtName)',
           "pascal": "begin\n  TuiSetText(Label1, 'Hi ' + TuiGetText(txtName));\nend;",
           "c": '    char buf[64];\n    strcpy(buf, "Hi ");\n    strcat(buf, tui_get_text(txtName));\n'
                '    tui_set_text(Label1, buf);',
           "asm": "    mov bx, Label1\n    mov si, offset msg_hi\n    call tui_set_text"}


def phase_tui():
    from radide.retro.design.textmode import project as tp
    from radide.retro.design.textmode.buffer import CellBuffer
    from radide.retro.design.textmode.codegen.common import BEGIN, END
    from radide.retro.design.textmode.designer import TuiDesigner
    from radide.retro.design.textmode.model import load_project_screens
    from radide.retro.design.textmode.sim import Sim
    feat = getattr(w, "dos_designer", None)
    qh.check("Text-Mode (DOS) feature installed", feat is not None)
    for target in ("freebasic", "pascal", "c", "asm"):
        name = "Tui" + target.capitalize()
        new_project("dos-tuiforms", f"tui_{target}", name)
        folder = Path(w.project.folder) if w.project is not None else WORK / name
        ok = w.project is not None and (folder / "Main.tform").is_file()
        qh.check(f"[{target}] New Project > DOS Text-Mode Forms App", ok)
        if not ok:
            continue
        d = w.open_any_file(folder / "Main.tform")
        qh.pump(0.5)
        qh.check(f"[{target}] Main.tform opens in the designer (menu + window + buttons)",
                 isinstance(d, TuiDesigner) and {"MenuBar", "Window", "Button"} <=
                 {c.type for c in d.screen.controls})
        if not isinstance(d, TuiDesigner):
            continue
        win = next(c for c in d.screen.controls if c.type == "Window")
        tb = draw(d, "TextBox", (win.x + 3, win.y + 4), (win.x + 22, win.y + 4))
        d._prop_edited(tb, "name", "txtName")
        btn = draw(d, "Button", (win.x + 26, win.y + 4), (win.x + 36, win.y + 4))
        d._prop_edited(btn, "name", "btnHi")
        d._prop_edited(btn, "text", "&Hi")
        qh.check(f"[{target}] TextBox + Button drawn with the toolbox", tb.type == "TextBox" and btn.type == "Button"
                 and btn.name == "btnHi", (tb.type, btn.type, btn.name))
        if target == "c":
            shot(d, "tui_designer_c")
        d.save()
        qh.pump(0.3)
        d._code_for("btnHi", "Click")
        qh.pump(0.8)
        main = tp.main_file(folder)
        text = tp.read_dos_text(main)
        key = "btnHi_Click"
        qh.check(f"[{target}] double-click Click creates the handler in {main.name}",
                 f"USER CODE {key}" in text, text[:300])
        # the user's code (written into the file the editor shows)
        ed = w.tabs.currentWidget()
        lines, outl, inside = text.split("\n"), [], False
        for ln in lines:
            mm = BEGIN.match(ln)
            if mm and mm.group(1) == key:
                outl.append(ln)
                outl.extend(HANDLER[target].split("\n"))
                inside = True
                continue
            if inside:
                if END.match(ln):
                    inside = False
                    outl.append(ln)
                continue
            if target == "asm" and mm and mm.group(1) == "declarations":
                outl.append(ln)
                outl.append("msg_hi    db 'Hi there', 0")
                continue
            outl.append(ln)
        new = "\n".join(outl)
        if getattr(ed, "editor", None) is not None:
            ed.editor.setText(new)
            w.save_all()
        else:
            tp.write_dos_text(main, new)
        qh.pump(0.3)
        ok, exe = tp.build(folder, log=lambda *_a: None, download=False)
        qh.check(f"[{target}] builds (regenerated, user code kept)", ok and exe is not None and
                 "Hi" in tp.read_dos_text(main))
        if not ok:
            continue
        screens = load_project_screens(folder)

        def fire(h, sm):
            if h == "Button1_Click":
                sm.set_text(sm.ctl("Label1"), "You pressed OK!")
            elif h == "btnHi_Click":
                sm.set_text(sm.ctl("Label1"), "Hi there" if target == "asm" else
                            "Hi " + sm.get_text(sm.ctl("txtName")))
            elif h == "mnuAbout_Click":
                sm.msgbox("About", "Made with RAD IDE - Text-Mode Designer")

        def sim(keys=(), clicks=()):
            sm = Sim(screens, basic=tp.TARGETS[target][2] in ("basic", "pascal"))
            sm.on_fire = fire
            sm.start()
            for k in keys:
                sm.handle_key(k)
            for c in clicks:
                sm.click(*c)
            return sm.buf
        # keyboard: focus the text box (Tab order: it was drawn after the buttons -> Tab until there), type, Hi
        probe = Sim(screens, basic=tp.TARGETS[target][2] in ("basic", "pascal")).start()
        tabs = 0
        while probe.foc != probe.ctl("txtName") and tabs < 12:
            probe.handle_key(9)
            tabs += 1
        keys = [9] * tabs + [ord(ch) for ch in "Ali"] + [9]
        got = tp.capture(folder, exe.name, keys + [13], log=lambda *_a: None)
        want = sim(keys + [13])
        diff = want.diff(got) if got is not None else ["no SCREEN.BIN"]
        qh.check(f"[{target}] keyboard in DOSBox-X: Tab, type 'Ali', Tab, Enter on Hi = simulator", not diff,
                 (diff[:3], got.plain_text()[:900] if got else ""))
        if target != "asm":
            qh.check(f"[{target}] the label says 'Hi Ali'", got is not None and "Hi Ali" in got.plain_text())
        # mouse: click into the text box, click Hi (the label shows "Hi " + empty text), click File > About...
        clicks = [(btn.x + 2, btn.y)]
        data = dosbox.capture_clicks(dosbox.DosRun(mounts=[("C", folder)], cycles="max"), folder, exe.name, clicks,
                                     timeout=30, log=lambda *_a: None)
        want = sim(clicks=clicks)
        got = CellBuffer.from_bin(data, want.cols) if data else None
        diff = want.diff(got) if got is not None else ["no _MOUSE.BIN"]
        qh.check(f"[{target}] mouse click on Hi in DOSBox-X = simulator", not diff,
                 (diff[:3], got.plain_text()[:900] if got else ""))
        if target == "c" and got is not None:
            from radide.retro.design.textmode.glyphs import save_png
            save_png(got, str(Path(qh.SHOTS) / f"{TAG}_tui_dosbox_c_mouse.png"))
        # Build && Run (a real DOSBox-X window): started, still running after 3 s, then stopped by us
        if target == "freebasic":
            w.tabs.setCurrentWidget(d)
            feat.build_run()
            proc = feat.proc
            alive = qh.wait(lambda: "Starting" in w.output.toPlainText() or "DOSBox-X:" in w.output.toPlainText(),
                            90)
            qh.pump(3)
            running = proc is not None and proc.state() != proc.ProcessState.NotRunning
            qh.check("[freebasic] Build && Run opens the program in a DOSBox-X window", alive and running,
                     w.output.toPlainText()[-500:])
            if proc is not None:
                proc.kill()
                proc.waitForFinished(5000)
    # QuickBASIC 4.5 dialect: does FreeBASIC build it (the template text says so)?
    from radide.languages import get_plugin
    qf = WORK / "TuiQb45"
    get_plugin("dos-tuiforms").create_new_project(qf, "TuiQb45", "tui_quickbasic")
    log = []
    ok, _exe = tp.build(qf, log=log.append, download=False)
    text = " | ".join(log)
    qh.check("[quickbasic] QuickBASIC 4.5 dialect without your own BC.EXE: the build says why", ok or
             ("CALL INTERRUPT" in text and "BC.EXE" in text), text[-500:])
    qh.app.processEvents()
    return True


# ====================================================================== ANSI editor
def phase_ansi():
    from PyQt6.QtGui import QKeyEvent
    from radide.retro.design.textmode.ansi import load_art
    from radide.retro.design.textmode.ansieditor import AnsiEditor
    from radide.retro.design.textmode.glyphs import save_png
    feat = w.dos_designer
    feat.new_art()
    qh.pump(0.3)
    ed = w.tabs.currentWidget()
    qh.check("Tools > Retro > Text-Mode (DOS) > New ANSI Art opens the editor", isinstance(ed, AnsiEditor))
    if not isinstance(ed, AnsiEditor):
        return
    cv = ed.canvas
    ed.set_tool("Box")
    cv.mousePressEvent(mouse_ev(cv, QMouseEvent.Type.MouseButtonPress, (5, 3)))
    cv.mouseMoveEvent(mouse_ev(cv, QMouseEvent.Type.MouseMove, (30, 8)))
    cv.mouseReleaseEvent(mouse_ev(cv, QMouseEvent.Type.MouseButtonRelease, (30, 8)))
    ed.set_tool("Text")
    cv.mousePressEvent(mouse_ev(cv, QMouseEvent.Type.MouseButtonPress, (8, 5)))
    for ch in "RAD IDE":
        cv.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, ch))
    ed.set_tool("Fill")
    cv.mousePressEvent(mouse_ev(cv, QMouseEvent.Type.MouseButtonPress, (40, 15)))
    cv.mouseReleaseEvent(mouse_ev(cv, QMouseEvent.Type.MouseButtonRelease, (40, 15)))
    buf = cv.buf
    txt = buf.plain_text()
    qh.check("box, text and fill drawn with the mouse / keyboard", "RAD IDE" in txt and buf.get(5, 3)[0] != 0x20
             and buf.get(40, 15)[0] != 0x20, txt[:400])
    path = WORK / "ART.ANS"
    qh.check("Save as .ANS (with SAUCE)", ed.save(path) and path.is_file() and b"SAUCE00" in path.read_bytes())
    shot(ed, "ansi_editor")
    art = load_art(path)
    diff = buf.diff(art) if hasattr(buf, "diff") else ["no diff()"]
    qh.check(".ANS round trip keeps every cell (characters + colours)", not diff, diff[:4])
    binp = WORK / "ART.BIN"
    ed.save(binp)
    back = load_art(binp)
    qh.check(".BIN round trip keeps every cell", not buf.diff(back), buf.diff(back)[:4])
    png = WORK / "ART.PNG"
    save_png(buf, png)
    qh.check("Export PNG", png.is_file() and png.stat().st_size > 1000)
    w2 = w.open_any_file(path)
    qh.pump(0.3)
    qh.check("File > Open of the .ANS opens it in the ANSI editor", isinstance(w2, AnsiEditor) and
             not w2.canvas.buf.diff(buf) if isinstance(w2, AnsiEditor) else False)


# ====================================================================== game designers
GAMES = [("a2600", "Stella"), ("nes", "Mesen"), ("gb", "mGBA"), ("dos13h", "DOSBox-X")]


def phase_game():
    from radide.retro.design.game.ui import GameDesigner
    feat = getattr(w, "retro_designs", None)
    qh.check("Tools > Retro > Game Designers installed", feat is not None)
    if feat is None:
        return
    folder = WORK / "designs"
    folder.mkdir(exist_ok=True)
    for system, emu in GAMES:
        opts = {"screens": 2} if system == "nes" else {}
        d = feat.new_design(system, folder=folder, ask=False, **opts)
        qh.pump(0.5)
        if not isinstance(d, GameDesigner):
            d = w.tabs.currentWidget()
        ok = isinstance(d, GameDesigner)
        qh.check(f"[{system}] designer opens", ok, type(d).__name__)
        if not ok:
            continue
        doc = d.doc
        lay = doc.layers[0] if hasattr(doc, "layers") else None
        try:
            for x in range(2, 6):
                lay.set(x, 3, 1)
        except Exception as e:  # noqa: BLE001
            qh.check(f"[{system}] paint on the first layer", False, e)
        d.refresh_all()
        shot(d, f"game_{system}")
        res = d.build_and_run(run=True, wait=True, download=False)
        qh.pump(1.0)
        ok = bool(res) and res.get("ok")
        checks = res.get("checks") if res else None
        qh.check(f"[{system}] Build && Run: builds and passes its checks", ok and (not checks or all(
            (c[0] if isinstance(c, (list, tuple)) else getattr(c, "ok", True)) for c in checks)),
            {k: v for k, v in (res or {}).items() if k in ("ok", "missing", "checks", "warnings")})
        proc = (res or {}).get("process")
        if proc is not None:
            time.sleep(3)
            alive = proc.alive() if hasattr(proc, "alive") else proc.poll() is None
            pop = getattr(proc, "popen", None)
            qh.check(f"[{system}] {emu} starts with the program and keeps running", alive,
                     (getattr(pop, "returncode", None), getattr(proc, "command", None)))
            if hasattr(proc, "stop"):                     # radide.retro.emu RetroProcess
                proc.stop()
            else:
                proc.kill()
            qh.check(f"[{system}] {emu} stopped again", not (proc.alive() if hasattr(proc, "alive") else
                                                              proc.poll() is None))
        else:
            qh.check(f"[{system}] {emu} started", False, (res or {}).get("log", "")[-300:] if res else "")
    phase_game_names()


def phase_game_names():
    """Designs of two systems with the same default name (Screen1.a26scr, Screen1.m13scr) keep their generated
    files apart (DASM Screen1.asm and NASM SCREEN1.ASM are one file on Windows)."""
    from radide.retro.design.game import gen_dir
    folder = WORK / "designs"
    a, m = folder / "Screen1.a26scr", folder / "Screen1.m13scr"
    if a.is_file() and m.is_file():
        qh.check("same-name designs of two systems generate into different folders", gen_dir(a) != gen_dir(m),
                 (gen_dir(a), gen_dir(m)))


# ====================================================================== i18n
def phase_i18n():
    from radide.i18n import english, missing, shown
    menus = [getattr(w, "dos_menu", None), getattr(w.dos_designer, "menu", None) if getattr(w, "dos_designer", None)
             else None]
    feat = getattr(w, "retro_designs", None)
    if feat is not None and getattr(feat, "menu", None) is not None:
        menus.append(feat.menu)
    texts = []
    for m in menus:
        if m is None:
            continue
        for a in m.actions():
            if a.isSeparator() or not a.text():
                continue
            texts.append((english(a, a.text()), shown(a)))
    if LANG == "ar":
        untranslated = [e for e, s in texts if not any("\u0600" <= ch <= "\u06ff" for ch in s)]
        qh.check(f"Arabic: every DOS / designer menu item is translated ({len(texts)})", not untranslated,
                 untranslated)
        import re

        def user_data(t: str) -> bool:
            """Names the user chose, shown the same way for every language: Solution Explorer rows "Name  [type]",
            window titles "Name - RAD IDE", outline rows "[f] name", file paths."""
            return bool(re.search(r"  \[[^\]]+\]$| - RAD IDE$|^\[[a-z]\] |[\\/]|\.(tform|ans|bas|pas|c|asm|bat)\*?$",
                                  t, re.I))
        # the New Project rows of the retro development slice (another workflow) are reported, not judged here
        other = {"Atari 2600  (DASM)", "NES  (cc65 / ca65)", "Game Boy  (RGBDS)", "Assembly  (MASM)"}
        mine = [t for t in missing() if not user_data(t) and t not in other and any(
            k in t for k in ("DOS", "Text-Mode", "ANSI", "Splash", "QBasic", "Turbo", "Game Design", "Atari", "NES",
                             "Game Boy", "mode 13h", "Mode 13h", "DOSBox", "FreeBASIC", "Watcom", "Pascal"))]
        print("NOTE other slices' untranslated New Project rows:", sorted(other & set(missing())), flush=True)
        (Path(qh.OUT) / f"missing_{TAG}.txt").write_text(chr(10).join(missing()), encoding="utf-8")
        qh.check("Arabic: no DOS / designer string seen on screen is missing from ar.json", not mine, mine[:25])
    else:
        qh.check(f"DOS / designer menus present ({len(texts)} items)", len(texts) >= 20, texts)
    shot(w, "ide_final")


try:
    for ph in PHASES:
        print(f"===== phase {ph} ({TAG})", flush=True)
        try:
            globals()["phase_" + ph]()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            qh.check(f"phase {ph} crashed", False, e)
finally:
    sys.exit(qh.finish(w))
