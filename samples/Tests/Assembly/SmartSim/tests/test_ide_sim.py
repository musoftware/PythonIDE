"""Assembly Checks window in the real IDE (qh.py harness: offscreen, QSettings "RADIDE-TEST", cleared afterwards).

1. Debug > Assembly Checks menu (Check by Running Ctrl+Shift+F5, Explain This Line Ctrl+Shift+F1, What-If ...).
2. A buggy NASM file opened with File > Open: Check by Running -> the Findings list, the bilingual details,
   Monaco markers with their own owner (rad-asm-sim), Error List rows (sim.*), the Program Output tab.
3. Explain This Line on the cursor line (before -> after values, flags, the jump prediction) in English, then in
   the Arabic UI (findings and explanation in Arabic first).
4. The What-If console and its flags table; the editor context menu entries; an 8086 file.

Screenshots (widget.grab only) go to %TEMP%/radide-qa/shots/asm_sim_*.png.
Run:  python samples/Tests/Assembly/SmartSim/tests/test_ide_sim.py
"""
import os
import re
import shutil
import sys
from pathlib import Path

os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ.setdefault("QA_NAME", "SmartSim")
HERE = Path(__file__).resolve().parent
SAMPLE = HERE.parent
sys.path.insert(0, str(SAMPLE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, shot, wait  # noqa: E402

WORK = Path(qh.WORK) / "asm_sim"
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)
for name in ("stack_imbalance.asm", "buffer_overflow.asm", "dos_div_zero.asm"):
    shutil.copy(SAMPLE / "buggy" / name, WORK / name)
ARABIC = re.compile(r"[؀-ۿ]")

w = qh.window()
from PyQt6.QtWidgets import QMenu  # noqa: E402

from radide import i18n  # noqa: E402
from radide.features import asm_smart_sim as S  # noqa: E402


def js(ed, code, timeout=8.0):
    box = []
    ed.page().runJavaScript(code, box.append)
    wait(lambda: box, timeout)
    return box[0] if box else None


def line_of(path, text):
    return next(i for i, x in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1) if text in x)


# ---------------------------------------------------------------- 1. menu
debug = next(a.menu() for a in w.menuBar().actions() if a.menu() is not None and
             a.text().replace("&", "") in ("Debug", i18n.tr("Debug")))
sub = next((a.menu() for a in debug.actions() if a.menu() is not None and a.menu().objectName() == "AsmChecksMenu"),
           None)
check("Debug > Assembly Checks submenu", sub is not None)
check("Check by Running = Ctrl+Shift+F5", w.a_asm_check_run.shortcut().toString() == "Ctrl+Shift+F5",
      w.a_asm_check_run.shortcut().toString())
check("Explain This Line = Ctrl+Shift+F1", w.a_asm_explain.shortcut().toString() == "Ctrl+Shift+F1",
      w.a_asm_explain.shortcut().toString())
check("What-If Console / Check This Procedure / Check Selection actions",
      all(hasattr(w, n) for n in ("a_asm_whatif", "a_asm_check_proc", "a_asm_check_sel")))

# ---------------------------------------------------------------- 2. check a buggy file
src = WORK / "stack_imbalance.asm"
ed = w.open_any_file(src)
check("buggy NASM file opened in Monaco", ed is not None)
wait(lambda: getattr(ed, "_ready", False), 40)
pump(0.5)
w.a_asm_check_run.trigger()                    # the real menu action (runs in a worker thread)
panel = w.asm_checks
check("Assembly Checks window shown", panel.dock.isVisible())
ok = wait(lambda: panel.result is not None and not panel._busy, 60)
res = panel.result
L_RET = line_of(src, "EXPECT: sim.stack_imbalance")
check("Check by Running: stack imbalance found at the ret line", ok and any(
    f.rule == "sim.stack_imbalance" and f.line == L_RET for f in res.findings), res and res.findings)
check("Findings list filled (line + message)", panel.tree.topLevelItemCount() >= 1 and
      panel.tree.topLevelItem(0).text(1) == str(L_RET), panel.tree.topLevelItemCount())
html = panel.details.toHtml()
check("details: what happened + how to fix, English and Arabic", "What happened?" in html and "How to fix" in html
      and ARABIC.search(html), html[:300])
mk = js(ed, "JSON.stringify(monaco.editor.getModelMarkers({owner: 'rad-asm-sim'}).map(m => [m.startLineNumber, m.code, m.severity]))")
check("Monaco markers with owner rad-asm-sim at the ret line", mk and f"[{L_RET}," in mk and "sim.stack_imbalance" in mk, mk)
rows = [w.error_list.topLevelItem(i) for i in range(w.error_list.topLevelItemCount())]
check("Error List row sim.stack_imbalance with file and line", any(
    r.text(1).startswith("sim.stack_imbalance") and r.text(3) == str(L_RET) for r in rows),
    [(r.text(1), r.text(3)) for r in rows])
check("diag provider keeps the rows while the text is unchanged", any(
    d.message.startswith("sim.stack_imbalance") for d in panel.diag_rows()))
panel.dock.setFloating(True)
panel.dock.resize(1100, 620)
pump(0.3)
shot(panel.dock, "asm_sim_findings_en")

# ---------------------------------------------------------------- 3. explain this line
L_ADD = line_of(src, "add eax, ecx")
ed.setCursorPosition(L_ADD - 1, 6)
pump(0.2)
panel.sp_iter.setValue(2)
w.a_asm_explain.trigger()
ok = wait(lambda: not panel._busy and "EAX" in panel.explain.toPlainText(), 60)
txt = panel.explain.toPlainText()
check("Explain This Line: execution 2 of 10, EAX 10 -> 19 (adds ECX = 9)", ok and "EAX: 0xa (10) -> 0x13 (19)" in txt,
      txt[:500])
check("Explain: flags with reasons + the Arabic block", "because" in txt and ARABIC.search(txt), txt[:300])
check("Explain: status shows the execution number", "execution 2 of 10" in panel.status.text(), panel.status.text())
shot(panel.dock, "asm_sim_explain_en")

# ---------------------------------------------------------------- 4. what-if
panel.cb_bits.setCurrentIndex(1)
panel.ed_code.setPlainText("add eax, ebx\ncmp eax, 10\njle small\nsub eax, 10\nsmall:")
panel.ed_values.setText("eax=5 ebx=7")
panel.b_whatif.click()
ok = wait(lambda: not panel._busy and panel.flags_table.rowCount() == 7, 30)
wt = panel.whatif_out.toPlainText()
check("What-If: steps explained and the jump prediction", ok and "12 <= 10 is false" in wt and "EAX" in wt, wt[:400])
check("What-If: flags table (CF ZF SF OF PF AF DF) with meanings", panel.flags_table.rowCount() == 7 and
      panel.flags_table.item(0, 0).text() == "CF" and len(panel.flags_table.item(0, 2).text()) > 20)
shot(panel.dock, "asm_sim_whatif_en")

# ---------------------------------------------------------------- context menu
m = QMenu()
S._context_menu(ed, m, w)
names = [a.text() for a in m.actions()]
check("editor context menu: Explain This Line / Check by Running / Check This Procedure",
      {"Explain This Line", "Check by Running", "Check This Procedure"} <= set(names), names)

# ---------------------------------------------------------------- buffer overflow + check this procedure
src2 = WORK / "buffer_overflow.asm"
ed2 = w.open_any_file(src2)
wait(lambda: getattr(ed2, "_ready", False), 40)
pump(0.3)
res2 = panel.run_check(wait=True)
L_W = line_of(src2, "EXPECT: sim.buffer_overflow")
check("buffer overflow found, it names the damaged variable 'limit'", any(
    f.rule == "sim.buffer_overflow" and f.line == L_W and "limit" in f.message() for f in res2.findings),
    [(f.rule, f.line, f.message()) for f in res2.findings])
check("Program Output tab shows what the program printed", "limit = " in panel.output.toPlainText(),
      panel.output.toPlainText()[:200])
rows = [w.error_list.topLevelItem(i).text(1) for i in range(w.error_list.topLevelItemCount())]
check("Error List: the previous file's sim rows were replaced", not any("stack_imbalance" in r for r in rows), rows)

# ---------------------------------------------------------------- 8086 file
src3 = WORK / "dos_div_zero.asm"
ed3 = w.open_any_file(src3)
wait(lambda: getattr(ed3, "_ready", False), 40)
pump(0.3)
res3 = panel.run_check(wait=True)
check("8086 file: divide by zero found by the 8086 emulator", res3.engine == "emu8086" and any(
    f.rule == "sim.div_zero" and f.line == line_of(src3, "EXPECT") for f in res3.findings),
    [(f.rule, f.line) for f in res3.findings])

# ---------------------------------------------------------------- Arabic UI
i18n.set_language(qh.app, "ar")
pump(0.5)
panel.show_result(res2)
check("Arabic UI: findings in Arabic", ARABIC.search(panel.tree.topLevelItem(0).text(2)),
      panel.tree.topLevelItem(0).text(2))
check("Arabic UI: details Arabic first (rtl)", panel.details.toHtml().find("rtl") >= 0 and
      ARABIC.search(panel.details.toPlainText()[:80]), panel.details.toPlainText()[:120])
panel.tabs.setCurrentIndex(0)
pump(0.3)
shot(panel.dock, "asm_sim_findings_ar")
w.tabs.setCurrentWidget(next(w.tabs.widget(i) for i in range(w.tabs.count())
                             if w.tabs.widget(i) is ed2 or getattr(w.tabs.widget(i), "editor", None) is ed2))
pump(0.3)
ed2.setCursorPosition(line_of(src2, "cmp ecx, 12") - 1, 4)
panel.sp_iter.setValue(0)
info = panel.explain_line(wait=True)
txt = panel.explain.toPlainText()
check("Arabic UI: the explanation starts in Arabic (last 'cmp ecx, 12' -> jb not taken)",
      ARABIC.search(txt[:200]) and info["ok"] and info["count"] == 12 and "لن يقفز" in txt, txt[:300])
shot(panel.dock, "asm_sim_explain_ar")
i18n.set_language(qh.app, "en")
pump(0.3)
qh.finish(w)
