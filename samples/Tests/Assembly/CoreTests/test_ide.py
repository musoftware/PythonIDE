"""IDE test (QSettings organisation RADIDE-TEST, cleared at the end):
New Project dialog shows the Assembly group + templates; an Assembly form project opens with its designer;
saving a broken .asm puts the NASM error into the Error List; Tools > Assembly Toolchains... opens;
picture of the designer with widget.grab()."""
import shutil
import sys
import tempfile
from pathlib import Path

WORK = Path(tempfile.gettempdir()) / "radide-asm-tests"     # projects are created here

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))      # the RAD IDE folder
from PyQt6.QtCore import QCoreApplication, QSettings
from PyQt6.QtWidgets import QApplication

QCoreApplication.setOrganizationName("RADIDE-TEST-ASM")
QCoreApplication.setApplicationName("RADIDE-TEST-ASM")
app = QApplication(sys.argv)
out = WORK
results = {}
try:
    from radide.app import MainWindow
    from radide.dialogs import NewProjectDialog
    from PyQt6.QtCore import Qt

    # 1. New Project dialog
    dlg = NewProjectDialog()
    found = {}
    for i in range(dlg.langs.topLevelItemCount()):
        g = dlg.langs.topLevelItem(i)
        if g.text(0) == "Assembly":
            for j in range(g.childCount()):
                c = g.child(j)
                pid = c.data(0, Qt.ItemDataRole.UserRole)
                dlg.langs.setCurrentItem(c)
                app.processEvents()
                found[pid] = [dlg.templates.item(k).text() for k in range(dlg.templates.count())]
                if pid == "asm-nasm":
                    dlg.grab().save(str(out / "ide_new_project.png"))
    print("New Project / Assembly:", found)
    results["new_project"] = "asm-nasm" in found and any("GUI Bridge" in t for t in found["asm-nasm"]) and \
        {"asm-fasm", "asm-masm", "asm-gas"} <= set(found)
    dlg.close()

    # 2. open a form project
    from radide.languages import get_plugin
    proj = out / "ide_projects" / "AsmForms"
    shutil.rmtree(proj.parent, ignore_errors=True)
    get_plugin("asm-nasm").create_new_project(proj, "AsmForms", "nasm_forms")
    win = MainWindow()
    win.resize(1300, 850)
    win.show()
    app.processEvents()
    win.open_project(proj / "project.radproj", ask=False) if (proj / "project.radproj").exists() else None
    for _ in range(30):
        app.processEvents()
    results["opened"] = win.project is not None and win.project.language == "asm-nasm"
    print("opened:", win.project and win.project.name, win.project and win.project.language)
    try:
        win.grab().save(str(out / "ide_asm_form.png"))
    except Exception as e:  # noqa: BLE001
        print("grab failed", e)

    # 3. Error List from the diag provider
    from radide import tools
    code = proj / "Form1.asm"
    text = code.read_text(encoding="utf-8")
    code.write_text(text.replace("    inc rax\n", "    movzx rax, 5, 6\n", 1), encoding="utf-8")
    bad_line = next(i for i, l in enumerate(code.read_text(encoding="utf-8").splitlines(), 1) if "movzx rax, 5, 6" in l)
    diags = tools.run_checks(win, show=True)
    rows = [(win.error_list.topLevelItem(i).text(1), win.error_list.topLevelItem(i).text(2),
             win.error_list.topLevelItem(i).text(3)) for i in range(win.error_list.topLevelItemCount())]
    print("Error List:", rows)
    results["error_list"] = any(r[1] == "Form1.asm" and r[2] == str(bad_line) for r in rows)
    code.write_text(text, encoding="utf-8")

    # 4. Tools > Assembly Toolchains...
    from radide.features.asm_build_ui import AsmToolchainsDialog
    d = AsmToolchainsDialog(win)
    d.show()
    app.processEvents()
    d.grab().save(str(out / "ide_asm_toolchains.png"))
    results["toolchains_dialog"] = d.table.rowCount() >= 9 and d.settings_box is not None
    d.close()
    results["menu"] = hasattr(win, "a_asm_toolchains")
    win.close()
finally:
    s = QSettings("RADIDE-TEST-ASM", "RADIDE-TEST-ASM")
    s.clear()
    s.sync()
print(results)
print("RESULT", "OK" if results and all(results.values()) else "FAIL")
