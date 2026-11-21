"""PE / MFC Resource Workbench inside the IDE (qh.py harness: QSettings org RADIDE-TEST, offscreen,
screenshots only through widget.grab(), RADIDE_NO_BROWSER=1).

    .venv\\Scripts\\python samples\\Tests\\PE\\MfcResources\\qa_pe_workbench_ide.py

  1  Tools menu entry; opening an .exe routes to the workbench tab (not the text editor).
  2  Dialog designer: caption via properties, move a control, add / delete a control, undo / redo.
  3  Double-click a button -> its MFC handler disassembly in the Code tab.
  4  Menu, string table, version, accelerator editors (Apply).
  5  MFC Events tab: classes / entries listed, retarget Button1 -> Button2's handler.
  6  Code tab: Edit Instruction (same size OK, larger refused), patch list, revert.
  7  Save As (new file + original untouched), run the saved exe: new caption, Button1 runs Button2's handler.
  8  .rc export / import; Arabic UI (translated tabs) + screenshot.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QA_NAME", "pe_workbench")
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
sys.path.insert(0, str(HERE))
import qh  # noqa: E402
from qh import check, pump  # noqa: E402

WORK = Path(qh.WORK) / "pe_workbench"
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True, exist_ok=True)
EXE = WORK / "MiniMfc32.exe"
shutil.copy2(HERE / "prebuilt" / "MiniMfc32.pe", EXE)
ORIGINAL = EXE.read_bytes()

w = qh.window()
from radide.pe import mfc as M  # noqa: E402
from radide.pe import resources as R  # noqa: E402
from radide.pe.document import EditError  # noqa: E402
from radide.pe.ui import PeWorkbench  # noqa: E402

# 1 ---------------------------------------------------------------- menu + open
tools = next(a.menu() for a in w.menuBar().actions() if a.text().replace("&", "") == "Tools")
check("Tools > PE / MFC Resource Workbench...", any("PE / MFC Resource" in a.text().replace("&", "")
                                                    for a in tools.actions()))
w.open_any_file(EXE)
pump(1)
wb = w.tabs.currentWidget()
check("opening the .exe shows the workbench tab", isinstance(wb, PeWorkbench), type(wb).__name__)
check("tab title", w.tabs.tabText(w.tabs.currentIndex()).startswith("MiniMfc32.exe [PE]"))
check("banner: x86 EXE + message maps", "x86 EXE" in wb.banner.text() and "MFC message maps" in wb.banner.text())

# 2 ---------------------------------------------------------------- designer
check("select dialog 101", wb.select_resource(R.RT_DIALOG, 101))
pump(0.3)
de = wb.dlg_editor
check("designer shows 15 controls + owner class", len(de.canvas.items_) == 15 and de.owner.currentText() == "CMainDlg",
      de.owner.currentText())
de.canvas.select(-1)
pump(0.1)
de.f_text.setText("QA Caption")
de.apply_props()
check("dialog caption edited", wb.doc.dialog(101, 0x409).title == "QA Caption")
idx = next(i for i, c in enumerate(de.d.controls) if c.id == 1001)
de._geometry(idx, 170, 12, 80, 18)
c = next(c for c in wb.doc.dialog(101, 0x409).controls if c.id == 1001)
check("control moved / resized", (c.x, c.y, c.cx, c.cy) == (170, 12, 80, 18))
de.canvas.select(idx)
pump(0.1)
de.f_text.setText("QA &Button")
de.apply_props()
check("control caption edited", any(c.text == "QA &Button" for c in wb.doc.dialog(101, 0x409).controls))
n = len(wb.doc.dialog(101, 0x409).controls)
de.add_control("CheckBox")
check("control added", len(wb.doc.dialog(101, 0x409).controls) == n + 1)
de.delete_control()
check("control deleted", len(wb.doc.dialog(101, 0x409).controls) == n)
wb.undo()
check("undo restores the deleted control", len(wb.doc.dialog(101, 0x409).controls) == n + 1)
wb.redo()
check("redo", len(wb.doc.dialog(101, 0x409).controls) == n)
check("modified marker in the tab", w.tabs.tabText(w.tabs.indexOf(wb)).endswith("*"))
qh.shot(wb, "pe_designer")

# 3 ---------------------------------------------------------------- double-click -> handler code
wb.select_resource(R.RT_DIALOG, 101)
pump(0.2)
idx = next(i for i, c in enumerate(wb.dlg_editor.d.controls) if c.id == 1001)
wb.dlg_editor._activated(idx)
pump(0.3)
check("double-click shows handler code", wb.tabs.currentWidget() is wb.code_tab and
      "CMainDlg::" in wb.code_view.toPlainText().splitlines()[0], wb.code_view.toPlainText()[:120])
check("functions list filled", wb.funcs.topLevelItemCount() > 50)
check("callers list mentions the message map", any("message map" in wb.xrefs_list.item(i).text()
                                                   for i in range(wb.xrefs_list.count())))
qh.shot(wb, "pe_code")

# 4 ---------------------------------------------------------------- other editors
wb.select_resource(R.RT_MENU, 102)
pump(0.2)
me = wb.menu_editor
top = me.tree.topLevelItem(0)
top.child(0).setText(0, "&Hi from QA\tCtrl+H")
me.apply()
check("menu edited", wb.doc.menu(102, 0x409).items[0].children[0].text.startswith("&Hi from QA"))
check("menu shows MFC handler column", "CMainDlg::" in me.tree.topLevelItem(0).child(0).text(3))
wb.select_resource(R.RT_STRING, 126)
pump(0.2)
se = wb.str_editor
for r in range(se.table.rowCount()):
    if se.table.item(r, 0).text() == "2002":
        se.table.item(r, 1).setText("QA string")
se._apply()
check("string table edited", wb.doc.string(2002, 0x409) == "QA string")
wb.select_resource(R.RT_VERSION, 1)
pump(0.2)
wb.ver_file.setText("3.1.0.0")
wb.ver_editor._apply()
check("version edited", wb.doc.version()[1].file_version == (3, 1, 0, 0))
wb.select_resource(R.RT_ACCELERATOR, 103)
pump(0.2)
wb.acc_editor.add_row(["Ctrl+Shift+Q", "40002"])
wb.acc_editor._apply()
check("accelerator added", any(a.cmd == 40002 and a.key == ord("Q")
                               for a in R.parse_accel(wb.doc.get(R.RT_ACCELERATOR, 103).data)))
wb.select_resource(R.RT_GROUP_ICON, 104)
pump(0.2)
check("icon preview", wb.stack.currentWidget() is wb.img_panel and wb.img_panel.view.pixmap() is not None
      and not wb.img_panel.view.pixmap().isNull())
ico = wb.export_entry(wb.current_entry(), str(WORK / "app.ico"))
check("icon exported", ico is not None and ico.read_bytes()[:4] == b"\0\0\1\0")

# 5 ---------------------------------------------------------------- MFC tab + retarget
wb.tabs.setCurrentWidget(wb.mfc_tab)
pump(0.3)
labels = [wb.mfc_tree.topLevelItem(i).text(0) for i in range(wb.mfc_tree.topLevelItemCount())]
check("MFC classes listed", "CMainDlg" in labels and "CAboutDlg" in labels, labels)
main = next(m for m in wb.maps() if m.class_name == "CMainDlg")
e1 = next(e for e in main.entries if e.id == 1001 and e.msg == M.WM_COMMAND)
e2 = next(e for e in main.entries if e.id == 1002 and e.msg == M.WM_COMMAND)
check("retarget Button1 -> Button2 handler", wb.retarget_dialog(e1, e2.pfn))
main = next(m for m in wb.maps() if m.class_name == "CMainDlg")
check("entry now points at Button2's handler", next(e for e in main.entries if e.id == 1001).pfn == e2.pfn)
qh.shot(wb, "pe_mfc")

# 6 ---------------------------------------------------------------- instruction edit
wb.show_code(e2.pfn)
first = wb.doc.analysis().listing(e2.pfn)[0]
ok = wb.edit_instruction(first.va, f"{first.mnemonic} {first.op_str}", 1)
check("edit instruction (same size)", ok and wb.patch_list.count() >= 2)
try:
    wb.doc.plan_instruction_patch(first.va, "\n".join(["nop"] * (first.size + 3)), 1)
    check("larger edit refused", False)
except EditError as ex:
    check("larger edit refused", "same-size or smaller" in str(ex))
n_p = len(wb.doc.patches)
wb.patch_list.setCurrentRow(wb.patch_list.count() - 1)
wb._revert()
check("revert patch", len(wb.doc.patches) == n_p - 1)

# 7 ---------------------------------------------------------------- save + run
out, notes = wb.save_to(WORK / "MiniMfc32_edited.exe")
check("saved as a new file, original untouched", out.is_file() and EXE.read_bytes() == ORIGINAL)
check("tab no longer modified", not w.tabs.tabText(w.tabs.indexOf(wb)).endswith("*"))
if sys.platform == "win32":
    from winrun import App
    app = App(out)
    try:
        check("edited exe runs with the new caption", app.ok and app.title() == "QA Caption",
              app.title() if app.ok else "no window")
        if app.ok:
            app.click(1001)
            check("Button1 runs Button2's handler with the edited string", app.item_text(1004) == "QA string",
                  app.item_text(1004))
    finally:
        app.close()

# 8 ---------------------------------------------------------------- rc + Arabic
rcp = wb.export_rc(str(WORK / "rc"))
check(".rc exported", rcp is not None and rcp.is_file() and (WORK / "rc" / "res").is_dir())
before = {e.key: e.data for e in wb.doc.resources}
check(".rc imported back unchanged", wb.import_rc(str(rcp)) and {e.key: e.data for e in wb.doc.resources} == before)

from radide import i18n  # noqa: E402
i18n.set_language(qh.app, "ar")
pump(0.5)
check("Arabic: workbench tabs translated", i18n.tr("Resources") == "الموارد" and
      i18n.tr("Edit Instruction...").startswith("تعديل التعليمة"))
check("Arabic: catalog has the workbench strings", i18n.tr("Retarget Handler...") != "Retarget Handler..." and
      i18n.tr("MFC Events") == "أحداث MFC")
wb.tabs.setCurrentIndex(0)
wb.select_resource(R.RT_DIALOG, 101)
pump(0.3)
qh.shot(wb, "pe_designer_ar")
i18n.set_language(qh.app, "en")
pump(0.3)
qh.finish(w)
