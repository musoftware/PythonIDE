"""IDE test of the Assembly integration part (QSettings organisation "RADIDE-TEST", cleared at the end):

1. Open Folder in place on NasmLoose (open_detect.open_inplace with the detected candidate): a foreign Assembly
   project with one run target; Ctrl+F5 builds it in the IDE state folder and the Output window shows its line.
2. RadAsmProject opens through its Hello.rap (foreign format "radasm").
3. Dos8086Loose: the 8086 target's session is the 8086 emulator session (Emu8086Session).
4. The Assembly course: the lesson viewer opens lesson 1 and "جرّبه" creates an asm-nasm project.
Pictures with widget.grab() (never the whole screen) in %TEMP%\\radide-asm-integration.

    python samples/Tests/Assembly/OpenFolder/test_ide_open.py
"""
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402
try:                                       # the Monaco editor needs it before the QApplication
    import PyQt6.QtWebEngineWidgets as _web  # noqa: E402
    del _web
except ImportError:
    pass

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv)
OUT = Path(tempfile.gettempdir()) / "radide-asm-integration"
OUT.mkdir(parents=True, exist_ok=True)
results: dict[str, bool] = {}


def check(name, ok, detail=""):
    results[name] = bool(ok)
    print(f"{'ok  ' if ok else 'FAIL'} {name}" + (f"  ({detail})" if detail else ""))


def pump(seconds=0.5, until=None):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        if until is not None and until():
            return True
        time.sleep(0.02)
    return until() if until is not None else True


win = None
try:
    from radide.app import MainWindow
    from radide.features.open_detect import open_inplace
    from radide.project_detect import detect

    win = MainWindow()
    win.resize(1300, 850)
    win.show()
    pump(1)

    # 1. NASM folder in place + Ctrl+F5
    det = detect(HERE / "NasmLoose")
    cand = [c for c in det.candidates() if c.kind == "asm"]
    ok = open_inplace(win, HERE / "NasmLoose", cand)
    p = win.project
    check("NasmLoose opened in place", ok and p is not None and getattr(p, "foreign", False) and
          p.adapter.kind == "asm", p and p.name)
    check("NasmLoose: run target + modules", p is not None and len(p.adapter.targets) == 1 and
          "macros.inc" in p.modules, p and [t.name for t in p.adapter.targets])
    win.output.clear()
    win.run_project(debug=False)
    done = pump(90, lambda: "6 * 7 = 42" in win.output.toPlainText())
    check("NasmLoose: Ctrl+F5 builds and runs", done, win.output.toPlainText()[-300:])
    pump(1)
    try:
        win.grab().save(str(OUT / "nasm_folder_in_place.png"))
    except Exception:  # noqa: BLE001
        pass
    if win.session is not None and win.session.running():
        win.stop_project()

    # 2. RadASM project file
    det = detect(HERE / "RadAsmProject")
    cand = [c for c in det.candidates() if c.kind == "asm"]
    ok = open_inplace(win, HERE / "RadAsmProject", cand)
    p = win.project
    check("RadASM project opened through Hello.rap", ok and p is not None and p.name == "Hello" and
          p.adapter.native.suffix == ".rap", p and str(p.adapter.native))

    # 3. 8086 folder -> emulator session
    det = detect(HERE / "Dos8086Loose")
    cand = [c for c in det.candidates() if c.kind == "asm"]
    ok = open_inplace(win, HERE / "Dos8086Loose", cand)
    p = win.project
    check("Dos8086Loose opened in place (emu target)", ok and p is not None and p.adapter.targets and
          p.adapter.targets[0].kind == "emu")
    try:
        from radide.languages import get_plugin
        s = get_plugin(p.language).make_session(win, None, False)
        check("8086 target runs in the emulator session", type(s).__name__ == "Emu8086Session", type(s).__name__)
        if s is not None:
            s.start() if hasattr(s, "start") else None
            pump(10, lambda: "8086 loose folder" in win.output.toPlainText() or not s.running())
            try:
                s.stop()
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        check("8086 target runs in the emulator session", False, repr(e))

    # 4. the course: viewer + "جرّبه"
    from radide import tutorials as T
    course = T.course("assembly")
    check("course assembly: 16 lessons", course is not None and len(course.lessons) == 16)
    les = course.lesson("01-intro")
    b = next(x for x in les.blocks() if x.role == "run")
    dest = Path(tempfile.mkdtemp(prefix="asmtry-"))
    try:
        proj = T.make_project(b, dest / "Lesson")
        check("جرّبه: asm-nasm project", proj is not None and proj.language == "asm-nasm" and
              (dest / "Lesson" / "main.asm").read_text(encoding="utf-8").strip() == b.code.strip())
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    try:
        from radide.tutorials.html import lesson_body
        html = lesson_body(les)
        check("lesson HTML has the try button and NASM highlighting", "radAct('try'" in html and "مثال Assembly" in html)
    except Exception as e:  # noqa: BLE001
        check("lesson HTML", False, repr(e))
finally:
    if win is not None:
        try:
            win.stop_project()
        except Exception:  # noqa: BLE001
            pass
        win._confirm_close_project = lambda: True
        win.close()
    pump(0.5)
    QSettings("RADIDE-TEST", "RADIDE-TEST").clear()
    QSettings().clear()

failed = [k for k, v in results.items() if not v]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
