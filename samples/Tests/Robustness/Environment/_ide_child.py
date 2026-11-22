"""Child process of test_env_save_crash.py: a real RAD IDE main window (offscreen) doing one step.

    python _ide_child.py <mode> <project folder> [args]

modes
  edit-and-hang   open the project, change Form1's code and its designer (a Button's Text, a new Label),
                  write the recovery snapshot (tools.autosave), print READY and wait to be killed
  restore         open the project with RADIDE_TEST_RECOVERY_ANSWER set; print a JSON report of what came back
  startup         like a fresh start without a project: offer_at_startup(); JSON report
  save-all        restore + File > Save All; JSON report (recovery folder gone?)
  save-full       edit, then Save All while the disk is "full" (ENOSPC injected); JSON report
  close-discard   edit, snapshot, close the project with "Discard"; JSON report
  save-loop       Form.save / Project.save of two alternating versions forever (killed by the parent)
"""
from __future__ import annotations

import errno
import json
import os
import sys
import time
from pathlib import Path

mode, folder = sys.argv[1], Path(sys.argv[2])
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
MARK = "# recovered-edit مرحبا"

if mode == "save-loop":
    from radide.model import Form, Project
    proj = Project.load(folder)
    path = folder / "Form1.form"
    forms = []
    for v in ("A", "B"):
        f = Form()                           # always the same two versions (never grows from run to run)
        f.props["Name"] = f.props["Text"] = "Form1"
        for i in range(400):                 # a big form: a write takes a while
            c = f.add("Button", 8 + i % 40, 8 + i // 40 * 30)
            c.props["Name"] = f"btn{v}{i}"
            c.props["Text"] = f"{v} زر {i} " + "x" * 60
        forms.append(f)
    print("READY", flush=True)
    i = 0
    while True:
        forms[i % 2].save(path)
        proj.modules = [f"mod{'AB'[i % 2]}.py"]
        proj.save()
        i += 1

import PyQt6.QtWebEngineWidgets  # noqa: E402,F401
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST-ENV")
QCoreApplication.setApplicationName("RADIDE-TEST-ENV")
app = QApplication(sys.argv[:1])
QSettings().clear()
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard
                                    if "Save changes" in str(a[2] if len(a) > 2 else "") else
                                    QMessageBox.StandardButton.Yes)
for _n in ("warning", "critical", "information"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))

from radide.app import MainWindow  # noqa: E402
from radide.features import recovery  # noqa: E402

win = MainWindow()
win.show()
report: dict = {"mode": mode}


def pump(n=5):
    for _ in range(n):
        app.processEvents()


def edit():
    win.open_project(folder, ask=False)
    pump()
    win.open_designer("Form1")
    doc = win._doc("Form1")
    btn = doc.form.find("Button1")
    doc.set_prop(btn, "Text", "Edited زر")
    doc.add_control("Label", 40, 120)
    win.open_code("Form1")
    ed = win._editor_for_file(win.plugin.code_file("Form1"))
    ed.setText(ed.text() + "\n" + MARK + "\n")
    pump()
    report["dirty"] = bool(doc.modified and ed.isModified())


def state():
    doc = win.docs.get("Form1")
    ed = win._editor_for_file(win.plugin.code_file("Form1")) if win.project else None
    btn = doc.form.find("Button1") if doc else None
    return {"doc_modified": bool(doc and doc.modified),
            "button_text": btn.props.get("Text") if btn else None,
            "labels": [c.name for c in doc.form.controls if c.type == "Label"] if doc else [],
            "code_has_mark": bool(ed and MARK in ed.text()),
            "code_modified": bool(ed and ed.isModified()),
            "recovery_exists": recovery.set_dir(folder).exists(),
            "log": win.output.toPlainText()[-2000:]}


if mode == "edit-and-hang":
    edit()
    from radide.tools import autosave
    autosave(win)
    report["snapshot"] = sorted(p.relative_to(recovery.set_dir(folder)).as_posix()
                                for p in recovery.set_dir(folder).rglob("*") if p.is_file())
    print("REPORT " + json.dumps(report, ensure_ascii=False), flush=True)
    print("READY", flush=True)
    while True:
        time.sleep(1)
elif mode in ("restore", "save-all"):
    win.open_project(folder, ask=False)
    pump(10)
    report.update(state())
    if mode == "save-all":
        report["saved"] = win.save_all()
        pump()
        report["after_save"] = state()
elif mode == "startup":
    report["opened"] = recovery.offer_at_startup(win)
    pump(10)
    report.update(state())
elif mode == "save-full":
    edit()
    import radide.safeio as sio

    def full(*_a, **_k):
        raise OSError(errno.ENOSPC, "No space left on device")
    sio.os.fsync = full
    report["saved"] = win.save_all()
    report.update(state())
    win.option = lambda name, default=None: False if name == "confirm_unsaved" else default
    report["close_allowed"] = win._confirm_close_project()
elif mode == "close-discard":
    edit()
    from radide.tools import autosave
    autosave(win)
    report["before"] = recovery.set_dir(folder).exists()
    report["close_allowed"] = win._confirm_close_project()
    report["after"] = recovery.set_dir(folder).exists()
print("REPORT " + json.dumps(report, ensure_ascii=False), flush=True)
sys.stdout.flush()
os._exit(0)
