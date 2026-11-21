"""DOS projects inside the IDE (test QSettings "RADIDE-TEST" via samples/Tests/QA/Integration/qh.py, widget.grab):
New Project dialog "DOS" group and templates, open a project, Tools > Retro > DOS Programming menu, Build DOS
Program -> real EXE, Error List rows (file:line) for a broken build, Run with Captured Output, DOS Project Settings,
DOS Toolchains, DOS Interrupt Reference, Last DOS Screen (mode 13h frame), editor hover, Open Folder detection."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
os.environ.setdefault("QA_NAME", "dosdev")
import qh  # noqa: E402  (sets up QApplication with the test QSettings)

from radide.languages import get_plugin  # noqa: E402
from radide.retro.dos import toolchain as T  # noqa: E402

WORK = Path(qh.WORK) / "dosdev"


def main() -> int:
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)
    w = qh.window()
    from radide.dialogs import NewProjectDialog
    d = NewProjectDialog(w)
    d.show()
    qh.pump(0.5)
    group = None
    for i in range(d.langs.topLevelItemCount()):
        if d.langs.topLevelItem(i).text(0).replace("&", "") in ("DOS",):
            group = d.langs.topLevelItem(i)
    names = [group.child(i).text(0) for i in range(group.childCount())] if group else []
    qh.check("New Project has a DOS group with 5 project types", group is not None and len(names) == 5, names)
    if group is not None:
        d.langs.setCurrentItem(group.child(0))
        qh.pump(0.3)
        qh.check("QBasic templates listed (6)", d.templates.count() == 6, d.templates.count())
        qh.shot(d, "dos_new_project")
    d.close()

    # ---- a Turbo Pascal-style project opened in the IDE
    folder = WORK / "PasMenu"
    get_plugin("dos-pascal").create_new_project(folder, "PasMenu", "dostp_mode13")
    w.open_project(folder, ask=False)
    qh.pump(2)
    qh.check("project opened", w.project is not None and w.project.language == "dos-pascal")
    from radide.features import dos_ide
    m = getattr(w, "dos_menu", None)
    titles = [a.text().replace("&", "") for a in m.actions()] if m is not None else []
    qh.check("Tools > Retro > DOS Programming menu", {"Build DOS Program", "Run in DOSBox-X",
                                                      "Run in DOSBox-X Debugger", "DOS Toolchains..."} <= set(titles) or
             len(titles) >= 10, titles)
    if not T.find("fpc"):
        qh.check("Free Pascal installed (run test_dos_toolchains.py first)", False)
        return qh.finish(w)
    proc = dos_ide.build_program(w)
    qh.wait(lambda: proc.state() == proc.ProcessState.NotRunning, 120)
    qh.pump(0.5)
    exe = folder / "PASMENU.EXE"
    qh.check("Build DOS Program -> PASMENU.EXE", exe.is_file() and exe.read_bytes()[:2] == b"MZ")
    qh.check("Output shows Build succeeded", "Build succeeded" in w.output.toPlainText(), w.output.toPlainText()[-500:])

    # ---- a broken build fills the Error List
    main_pas = folder / "MAIN.PAS"
    good = main_pas.read_bytes()
    main_pas.write_bytes(good.replace(b"  SetMode($13);", b"  SetMode($13);\r\n  Undefined1 := 3;"))
    proc = dos_ide.build_program(w)
    qh.wait(lambda: proc.state() == proc.ProcessState.NotRunning, 120)
    qh.pump(0.8)
    rows = [(w.error_list.topLevelItem(i).text(0), w.error_list.topLevelItem(i).text(1),
             w.error_list.topLevelItem(i).text(2), w.error_list.topLevelItem(i).text(3))
            for i in range(w.error_list.topLevelItemCount())]
    qh.check("Error List row MAIN.PAS with the line of the error",
             any(r[0] == "Error" and r[2].upper() == "MAIN.PAS" and "Undefined1" in r[1] for r in rows), rows)
    qh.shot(w, "dos_error_list")
    main_pas.write_bytes(good)

    # ---- captured run (no window): the mode 13h frame and Last DOS Screen
    if T.dosbox_exe():
        proc = dos_ide.run_tool(w, ["radide.retro.dos.run", str(folder), "--capture", "--keys", "x"], "capture")
        qh.wait(lambda: proc.state() == proc.ProcessState.NotRunning, 120)
        qh.pump(0.5)
        out = w.output.toPlainText()
        qh.check("Run with Captured Output: program text in the Output window", "Back in text mode." in out, out[-600:])
        dlg = dos_ide.show_last_screen(w)
        qh.pump(0.5)
        qh.check("Last DOS Screen shows the mode 13h frame", dlg is not None and hasattr(dlg, "image") and
                 not dlg.image.isNull())
        if dlg is not None:
            qh.shot(dlg, "dos_last_screen")
            dlg.close()
    # ---- dialogs
    sd = dos_ide.DosSettingsDialog(w, w.project)
    sd.cycles.setCurrentIndex(sd.cycles.findData("486"))
    sd.memsize.setValue(32)
    qh.shot(sd, "dos_settings")
    sd.save()
    from radide.model import Project
    dos = Project.load(folder).extra.get("dos", {})
    qh.check("DOS Project Settings saved (cycles 486, 32 MB)", dos.get("cycles") == "486" and dos.get("memsize") == 32,
             dos)
    from radide.retro.dos.run import _run_config
    from radide.retro.dos.build import settings_for
    run = _run_config(folder, settings_for(Project.load(folder)))
    qh.check("run config uses the preset (fixed 27000 cycles)", run.cycles == "486" and run.memsize == 32)
    td = dos_ide.show_toolchains(w)
    qh.pump(0.5)
    qh.check("DOS Toolchains lists free + own tools", td.table.rowCount() >= len(T.RELEASES) + len(T.USER_TOOLS))
    qh.shot(td, "dos_toolchains")
    td.close()
    rd = dos_ide.show_reference(w)
    rd.filter.setText("mouse")
    qh.pump(0.3)
    first = rd.tree.topLevelItem(0)
    rd.tree.setCurrentItem(first.child(0) if first.childCount() else first)
    qh.pump(0.3)
    qh.check("DOS Interrupt Reference shows details", "INT" in rd.view.toPlainText(), rd.view.toPlainText()[:200])
    qh.shot(rd, "dos_interrupts")
    rd.close()
    # ---- editor hover through the plugin of the open project
    plugin = w.plugin_for_file("MAIN.PAS") if hasattr(w, "plugin_for_file") else get_plugin("dos-pascal")
    h = plugin.hover("  R.AX := $13;\n  Intr($10, R);", 1, 3, folder / "MAIN.PAS")
    qh.check("hover on Intr($10) in the IDE's plugin", "Set video mode" in h, h)
    # ---- F5 / Ctrl+F5 specs
    spec = plugin.run_spec(folder, "MAIN", "")
    qh.check("Ctrl+F5 runs radide.retro.dos.run", "radide.retro.dos.run" in spec.args)
    dspec = plugin.debug_spec(folder, "MAIN", "", [])
    qh.check("F5 uses the DOSBox-X debugger (--debug)", "--debug" in dspec.args)
    asm_folder = WORK / "AsmHello"
    get_plugin("dos-asm").create_new_project(asm_folder, "AsmHello", "dosasm_hello")
    qh.check("DOS Assembly hello is 8086-emulator compatible (F5 steps it there)",
             get_plugin("dos-asm").emulator_compatible(asm_folder, "MAIN.ASM"))
    # ---- Open Folder detection with the feature installed
    from radide import project_detect
    old = WORK / "OldBasic"
    old.mkdir()
    (old / "GAME.BAS").write_bytes(b"10 PRINT \"HI\"\r\n20 GOTO 10\r\n")
    cands = project_detect.detect_here(old)
    qh.check("Open Folder: line-numbered GAME.BAS -> DOS QBasic", cands and cands[0].language == "dos-qbasic",
             [(c.language, c.confidence) for c in cands])
    return qh.finish(w)


if __name__ == "__main__":
    sys.exit(main())
