"""Build > Build Native Exe (radide/features/installer.py) and the note after a normal build of a GUI Bridge
application (radide/features/solution_ui.py).

    .venv\\Scripts\\python samples/Tests/Native/test_build_native_ui.py [scratch folder]

Offscreen IDE; QSettings "RADIDE-TEST" is cleared before and after; only widget.grab() pictures.
A copy of samples/Tests/Native/Rust/FormsDemo is opened, Build Native Exe runs (wait=True) and the exe is
checked (native, standalone, starts and shows Form1; only that process is touched). In Arabic the menu item
and the note are translated. Exit code = number of failures."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["RADIDE_NO_BROWSER"] = "1"

from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv[:1])
QSettings().clear()
QSettings().sync()

SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="radide_build_native_ui_"))
SCRATCH.mkdir(parents=True, exist_ok=True)
results: list[tuple[str, bool, str]] = []


def ok(name: str, cond, detail: str = "") -> bool:
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""), flush=True)
    return bool(cond)


def pump(n=10):
    for _ in range(n):
        app.processEvents()


def main() -> int:
    import winauto as w
    from radide.app import MainWindow
    from radide import i18n
    from radide.features.solution_ui import bridge_build_note
    from radide.languages import get_plugin
    from radide.model import Project
    for name in ("information", "warning", "critical"):
        setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
    proj = SCRATCH / "RustDemo"
    shutil.rmtree(proj, ignore_errors=True)
    shutil.copytree(HERE / "Rust" / "FormsDemo", proj)
    win = MainWindow()
    try:
        win.resize(1200, 800)
        win.show()
        pump(30)
        win.open_project(proj, ask=False)
        pump(30)
        ok("project opened", win.project is not None and Path(win.project.folder).resolve() == proj.resolve())
        a = getattr(win, "a_build_native", None)
        menu = next((x.menu() for x in win.menuBar().actions() if x.menu() is not None
                     and x.text().replace("&", "") == "Build"), None)
        ok("Build > Build Native Exe exists", a is not None and menu is not None and a in menu.actions())
        win.grab().save(str(SCRATCH / "ide.png"))
        pub = win.publisher
        logs: list[str] = []
        orig = win.log
        win.log = lambda t, *aa, **kk: (logs.append(str(t)), orig(t, *aa, **kk))
        t = pub.build_native(wait=True)
        pump(20)
        ok("build ran", t is not None)
        res, err = getattr(pub, "last_native", (None, "not run"))
        ok("Build Native Exe succeeded", res is not None and not err, err + "\n" + "\n".join(logs[-15:]))
        if res is not None:
            exe = Path(res.dist) / res.exe
            ok("native kind, one exe", res.kind == "native" and exe.is_file() and
               [p.name for p in Path(res.dist).iterdir() if p.name.lower() != "readme.md"] == [exe.name])
            ok("success line in the Output", any("Build Native Exe succeeded" in s for s in logs))
            ok("into the project's Publish\\build\\dist", (proj / "Publish" / "build" / "dist") in exe.parents)
            p = w.start(exe)
            f = None
            try:
                f = w.form_window(p.pid, "Form1")
                ok("the exe shows Form1 without the IDE", f)
            finally:
                ok("the exe closes", w.stop(p, f))
        pr = Project.load(proj)
        note = bridge_build_note(pr, get_plugin("rust-bridge"))
        ok("note after a normal build", "Build Native Exe" in note and "F5" in note, note)
        lib = Project.load(proj)
        lib.forms = []
        ok("no note for a project without forms", bridge_build_note(lib, get_plugin("rust-bridge")) == "")
        ok("no note for Python", bridge_build_note(pr, get_plugin("python-tk")) == "")
        from radide.features.ui_language import apply_language
        apply_language(win, "ar", notify=False)
        pump(20)
        ok("Arabic menu item", "أصلي" in i18n.shown(a), i18n.shown(a))
        ok("Arabic note", "F5" in bridge_build_note(pr, get_plugin("rust-bridge")) and
           "ملاحظة" in bridge_build_note(pr, get_plugin("rust-bridge")))
        win.grab().save(str(SCRATCH / "ide_ar.png"))
        apply_language(win, "en", notify=False)
        pump(10)
    finally:
        win.close()
        pump(10)
        QSettings().clear()
        QSettings().sync()
    failed = [n for n, good, _ in results if not good]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed   (pictures: {SCRATCH})")
    for n in failed:
        print("  FAILED:", n)
    return len(failed)


if __name__ == "__main__":
    sys.exit(main())
