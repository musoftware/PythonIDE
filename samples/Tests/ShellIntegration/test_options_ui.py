"""Tools > Options > Environment > Windows integration (radide/features/shell_integration_ui.py):
the group, Register / Unregister buttons (against the TEST registry root), Apply re-registering
changed choices, the single-window setting and the Arabic translations.

    .venv\\Scripts\\python samples\\Tests\\ShellIntegration\\test_options_ui.py [scratch folder]"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import winreg
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
BASE = "Software\\RADIDE-TEST-ShellUI"
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "radide-shell-ui"
os.environ["RADIDE_SHELL_ROOT"] = BASE + "\\Classes"
os.environ["RADIDE_SHELL_SHORTCUTS"] = str(SCRATCH / "ui_shortcuts")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

__import__("PyQt6.QtWebEngineWidgets")              # before QApplication
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv[:1])
QSettings().clear()

from radide import shell_integration as S  # noqa: E402
from radide.app import MainWindow  # noqa: E402
from radide.features.settings import OptionsDialog  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""), flush=True)


def getv(key, name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as h:
            return winreg.QueryValueEx(h, name)[0]
    except OSError:
        return None


def tree_exists():
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CURRENT_USER, BASE))
        return True
    except OSError:
        return False


msgs = []
QMessageBox.information = staticmethod(lambda *a, **k: msgs.append(a[2] if len(a) > 2 else a))
QMessageBox.warning = staticmethod(lambda *a, **k: msgs.append(("warning", a[2] if len(a) > 2 else a)))

check("test root only", S.Target.from_env().test and not tree_exists())
win = MainWindow()
dlg = OptionsDialog(win)
check("group present with 5 choices + single window", len(getattr(dlg, "shell_checks", {})) == 5
      and dlg.shell_single.isChecked() and dlg.shell_status.text() == "Status: not registered."
      and not dlg.shell_unregister.isEnabled(), dlg.shell_status.text())
check("defaults: everything but the Desktop shortcut",
      all(dlg.shell_checks[k].isChecked() for k in ("file_assoc", "open_with", "context_menu", "start_menu"))
      and not dlg.shell_checks["desktop"].isChecked())
dlg.shell_checks["open_with"].setChecked(False)
dlg.shell_register.click()
st = S.status()
check("Register writes the choices (test root)", st["registered"] and not st["options"]["open_with"]
      and getv(BASE + "\\Classes\\.radsln", "") == "RADIDE.Solution"
      and getv(BASE + "\\Classes\\.txt\\OpenWithProgids", "RADIDE.SourceFile") is None
      and (SCRATCH / "ui_shortcuts" / "StartMenu" / "RAD IDE.lnk").is_file(), str(st)[:300])
check("status label + Unregister enabled", dlg.shell_status.text().startswith("Status: registered (")
      and dlg.shell_unregister.isEnabled(), dlg.shell_status.text())
dlg.shell_checks["open_with"].setChecked(True)
dlg.shell_single.setChecked(False)
dlg.apply()
check("Apply re-registers changed choices",
      getv(BASE + "\\Classes\\.txt\\OpenWithProgids", "RADIDE.SourceFile") == "" and S.status()["options"]["open_with"])
check("single-window setting saved", str(win.settings.value("options/single_instance")).lower() == "false"
      and str(win.settings.value("options/shell_open_with")).lower() == "true")
dlg.shell_unregister.click()
check("Unregister removes everything", not S.status()["registered"] and getv(BASE + "\\Classes\\.radsln", "") is None
      and not (SCRATCH / "ui_shortcuts" / "StartMenu" / "RAD IDE.lnk").exists()
      and dlg.shell_status.text() == "Status: not registered.")
check("no warnings", not [m for m in msgs if isinstance(m, tuple)], str(msgs))
dlg.deleteLater()

from radide import i18n  # noqa: E402
i18n.set_language(app, "ar")
want = ["Windows integration", "Open files in the running RAD IDE window", "Register", "Unregister",
        "Start Menu shortcut", "Desktop shortcut", "Status: not registered."] + list(S.OPTION_LABELS.values())
missing = [s for s in want if i18n.tr(s) == s]
pat = i18n.tr("Status: registered (12 registry values, 1 shortcuts).")
check("Arabic translations", not missing and pat.startswith("الحالة") and "12" in pat, f"{missing} {pat}")
i18n.set_language(app, "en")

# leave nothing behind
assert BASE.startswith("Software\\RADIDE-TEST")
check("test tree removed by Unregister", not tree_exists())
shutil.rmtree(SCRATCH / "ui_shortcuts", ignore_errors=True)
win._confirm_close_project = lambda: True
win.close()
QSettings().clear()
failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} passed", flush=True)
os._exit(1 if failed else 0)
