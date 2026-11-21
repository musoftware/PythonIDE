"""IDE test (qh harness, QSettings org RADIDE-TEST): Apollo AGC projects and legacy Fortran in the real window.

    python samples/Tests/Retro/AGC/test_ide_nasa.py

* menus Tools > Retro > Apollo AGC / Legacy Fortran, New Project templates of both languages
* F5 on HelloDSKY: the "Apollo AGC" dock with the DSKY, V16 N36, keys typed on the DSKY widget (V35E lamp test),
  a breakpoint on TICK stops with Locals (registers + SECS), F10, continue, stop
* an assembly error shows in the Error List after a check (diag provider), with file and line
* Ctrl+F5 on the Fortran 66 OrbitTable sample prints the orbit table; card deck and conversion windows
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "QA" / "Integration"))
os.environ.setdefault("QA_NAME", "nasa")
import qh  # noqa: E402
from qh import check, pump, shot, wait  # noqa: E402

from PyQt6.QtWidgets import QDialog  # noqa: E402

HERE = Path(__file__).resolve().parent
WORK = Path(qh.WORK) / "nasa"
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)
shutil.copytree(HERE / "HelloDSKY", WORK / "HelloDSKY")
shutil.copytree(HERE.parent / "LegacyFortran" / "OrbitTable", WORK / "OrbitTable",
                ignore=shutil.ignore_patterns("_build"))

w = qh.window()


def actions_of(*path: str) -> list[str]:
    menu = next(a.menu() for a in w.menuBar().actions() if a.text().replace("&", "") == path[0])
    for sub in path[1:]:
        menu = next((a.menu() for a in menu.actions() if a.menu() is not None and a.text().replace("&", "") == sub),
                    None)
        if menu is None:
            return []
    return [a.text().replace("&", "") for a in menu.actions()]


agc_menu = actions_of("Tools", "Retro", "Apollo AGC")
check("Tools > Retro > Apollo AGC menu", {"Open Apollo Source...", "Virtual AGC Toolchain...", "DSKY Panel",
                                          "DSKY Verbs, Nouns and Programs"} <= set(agc_menu), agc_menu)
check("Tools > Retro > Legacy Fortran menu", {"Card Deck View", "Convert to Free Form...", "Explain Legacy Constructs"}
      <= set(actions_of("Tools", "Retro", "Legacy Fortran")))

from radide.languages import get_plugin  # noqa: E402
check("New Project templates", [t[0] for t in get_plugin("agc-yul").project_templates()] == ["agc_hello", "agc_empty"]
      and [t[0] for t in get_plugin("fortran-legacy").project_templates()] == ["f66_orbits", "f77_hello"])
from radide import dialogs  # noqa: E402
groups = {g: ids for g, ids in dialogs.LANGUAGE_GROUPS}
check("New Project group lists the AGC and Fortran 66/77 languages",
      any("agc-yul" in ids for ids in groups.values()) and any("fortran-legacy" in ids for ids in groups.values()),
      groups.keys())

# ------------------------------------------------------------------ AGC project, F5
w.open_project(WORK / "HelloDSKY", ask=False)
pump(2)
check("HelloDSKY opened", w.project is not None and w.project.language == "agc-yul")
w.run_project(debug=True)
check("AGC session running", wait(lambda: w.session is not None and w.session.running(), 20))
s = w.session
check("session is the built-in emulator", type(s).__name__ == "AgcSession", type(s).__name__)
panel = getattr(w, "_agc_panel", None)
check("Apollo AGC dock shown", panel is not None and w._agc_dock.isVisible())
check("DSKY shows V16 N36", wait(lambda: s.machine.dsky.verb == "16" and s.machine.dsky.noun == "36", 10),
      s.machine.dsky.summary() if s.machine else "")
check("the clock runs in real time", wait(lambda: s.machine.dsky.r3 in ("+00100", "+00200", "+00300"), 6),
      s.machine.dsky.summary())
for k in ("VERB", "3", "5", "ENTR"):
    panel.dsky.keyPressed.emit(k)
    pump(0.3)
check("keys on the DSKY widget: V35E lamp test", wait(lambda: s.machine.dsky.r1 == "+88888", 5),
      s.machine.dsky.summary())
pump(0.5)
panel.refresh(True)
shot(w._agc_dock, "agc_dock_lamptest")
for k in ("VERB", "1", "6", "NOUN", "3", "6", "ENTR"):
    panel.dsky.keyPressed.emit(k)
    pump(0.25)
check("V16N36E back to the clock", wait(lambda: s.machine.dsky.r1 == "+00000", 5), s.machine.dsky.summary())
check("registers window filled", panel.registers.topLevelItemCount() > 5)

main_lines = (WORK / "HelloDSKY" / "MAIN.agc").read_text().splitlines()
tick = next(i for i, l in enumerate(main_lines, 1) if l.startswith("TICK "))
stops = []
s.stopped.connect(lambda info: stops.append(info))
s.set_breakpoint("MAIN.agc", tick, True)
check("breakpoint on TICK stops", wait(lambda: stops, 4) and stops[-1].line == tick and
      stops[-1].reason == "breakpoint", [(x.file, x.line, x.reason) for x in stops])
if stops:
    names = [v[0] for v in stops[-1].variables]
    check("Locals: A L Q Z + SECS", {"A", "L", "Q", "Z", "SECS"} <= set(names), names[:12])
    check("Locals window shows them", w.locals.topLevelItemCount() > 5)
    check("current line marked in MAIN.agc", getattr(w, "stopped_at", None) is not None)
    shot(w, "agc_breakpoint")
    n0 = len(stops)
    s.step_over()
    check("F10 steps to the next line", wait(lambda: len(stops) > n0, 3) and stops[-1].line == tick + 1,
          [(x.line, x.reason) for x in stops[-2:]])
    s.set_breakpoint("MAIN.agc", tick, False)
    s.cont()
    pump(1.2)
    check("continue runs again", not s.paused and s.running())
s.stop()
check("stop", wait(lambda: not s.running(), 5))

# Error List
kb = WORK / "HelloDSKY" / "KEYBOARD.agc"
text = kb.read_text()
kb.write_text(text.replace("                TS      KEY\n", "                TS      KEYZ\n", 1))
from radide.tools import run_checks  # noqa: E402
diags = run_checks(w)
bad = [d for d in diags if d.severity == "Error"]
check("assembly error in the Error List (diag provider)", any(d.file == "KEYBOARD.agc" and "KEYZ" in d.message
                                                              for d in bad), [(d.file, d.line, d.message) for d in diags][:5])
kb.write_text(text)
check("fixed again -> no errors", not [d for d in run_checks(w) if d.severity == "Error"])

# ------------------------------------------------------------------ Virtual AGC: yaYUL + yaAGC sessions
from radide.agc import toolchain  # noqa: E402
if toolchain.find("yayul") and toolchain.find("yaagc"):
    import json  # noqa: E402
    ya = WORK / "HelloYa"
    shutil.copytree(HERE / "HelloDSKY", ya)
    pj = json.loads((ya / "project.radproj").read_text())
    pj["agc"] = {"assembler": "yayul", "run": "yaagc", "port": 19871}
    (ya / "project.radproj").write_text(json.dumps(pj, indent=2))
    w.open_project(ya, ask=False)
    pump(2)
    w.run_project(debug=False)
    check("yaAGC session (run)", wait(lambda: w.session is not None and type(w.session).__name__ == "YaAgcSession",
                                      10))
    ys = w.session
    check("yaYUL built the rope", wait(lambda: (ya / "MAIN.agc.bin").exists(), 30))
    check("DSKY connected to yaAGC shows V16 N36", wait(lambda: getattr(ys, "_link", None) is not None and
                                                       ys._link.is_connected() and panel.dsky.model.verb == "16" and
                                                       panel.dsky.model.noun == "36", 30), panel.dsky.model.summary())
    for k in ("VERB", "3", "5", "ENTR"):
        panel.dsky.keyPressed.emit(k)
        pump(0.3)
    check("yaAGC: V35E from the DSKY widget", wait(lambda: panel.dsky.model.r1 == "+88888", 6),
          panel.dsky.model.summary())
    shot(w._agc_dock, "agc_dock_yaagc")
    ys.stop()
    wait(lambda: not ys.running(), 5)
    pump(1)
    pj["agc"]["port"] = 19872
    (ya / "project.radproj").write_text(json.dumps(pj, indent=2))
    w.open_project(ya, ask=False)
    pump(1.5)
    ystops = []
    w._all_breakpoints = lambda: [(str(ya / "MAIN.agc"), tick)]
    w.run_project(debug=True)
    ys2 = w.session
    ys2.stopped.connect(lambda info: ystops.append(info))
    check("yaAGC debug: breakpoint on TICK stops", wait(lambda: ystops, 25) and ystops[-1].line == tick and
          Path(ystops[-1].file).name.lower() == "main.agc", [(x.file, x.line) for x in ystops])
    if ystops:
        check("yaAGC debug: registers in Locals", {"A", "Q", "Z"} <= {v[0] for v in ystops[-1].variables},
              ystops[-1].variables[:5])
        n0 = len(ystops)
        ys2.step_over()
        check("yaAGC debug: next -> following line", wait(lambda: len(ystops) > n0, 10) and ystops[-1].line == tick + 1,
              [(x.line) for x in ystops])
    ys2.stop()
    wait(lambda: not ys2.running(), 5)
    del w._all_breakpoints
else:
    print("SKIP Virtual AGC IDE checks (python -m radide.agc.toolchain install)")

# reference dialog builds (modal exec patched away)
_exec = QDialog.exec
QDialog.exec = lambda self: (shot(self, "agc_reference"), 0)[1] if "Verbs" in self.windowTitle() else 0
from radide.features import retro_nasa  # noqa: E402
retro_nasa.dsky_reference(w)
QDialog.exec = _exec

# ------------------------------------------------------------------ legacy Fortran
w.open_project(WORK / "OrbitTable", ask=False)
pump(2)
check("OrbitTable opened", w.project is not None and w.project.language == "fortran-legacy")
w.run_project(debug=False)
check("Ctrl+F5 prints the orbit table", wait(lambda: "GEOSTATIONARY ORBIT" in w.output.toPlainText(), 90),
      w.output.toPlainText()[-800:])
wait(lambda: w.session is None or not w.session.running(), 20)
from radide.retro import legacy_fortran as lf  # noqa: E402
src = (WORK / "OrbitTable" / "ORBITS.f").read_text()
dlg = lf.card_deck_dialog(w, src, 23)
dlg.show()
pump(0.5)
shot(dlg, "fortran_card_deck")
from PyQt6.QtWidgets import QLabel  # noqa: E402
check("card deck window shows card 24 (a FORMAT with Hollerith)",
      any("Card 24 of" in lb.text() for lb in dlg.findChildren(QLabel)),
      [lb.text() for lb in dlg.findChildren(QLabel)])
dlg.close()
conv = lf.conversion_dialog(w, WORK / "OrbitTable" / "ORBITS.f", src)
conv.show()
pump(0.3)
shot(conv, "fortran_free_form")
from PyQt6.QtWidgets import QPlainTextEdit  # noqa: E402
texts = [v.toPlainText() for v in conv.findChildren(QPlainTextEdit)]
check("conversion window: diff + result", any("@@" in t for t in texts) and
      any(t.startswith("!") and "'CIRCULAR ORBITS OF EARTH'" in t for t in texts), [t[:80] for t in texts])
conv.close()
check("fixed-form provider: no errors in the sample", not [d for d in run_checks(w) if d.severity == "Error"])

qh.finish(w)
