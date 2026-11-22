"""The real IDE (radide.app.MainWindow), offscreen, for the IntelliSense / designer / debugger checks.

One MainWindow per process (QSettings organization RADIDE-TEST-QA, cleared before and after). Monaco runs in
QtWebEngine; its suggest widget is read from the page DOM (no screen capture). Modal dialogs that would block
the test are closed by a timer."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .common import APP, ORG

_HOST = None


class IdeHost:
    def __init__(self):
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --log-level=3")
        import PyQt6.QtWebEngineWidgets  # noqa: F401 - must be imported before QApplication
        from PyQt6.QtCore import QCoreApplication, QSettings, QTimer
        from PyQt6.QtWidgets import QApplication
        QCoreApplication.setOrganizationName(ORG)
        QCoreApplication.setApplicationName(APP)
        self.app = QApplication.instance() or QApplication(["radide-qa"])
        QSettings().clear()
        from radide.app import MainWindow
        self.killer = QTimer()
        self.killer.timeout.connect(self._close_modals)
        self.killer.start(300)
        self.closed_dialogs: list[str] = []
        self.w = MainWindow()
        self.w.resize(1400, 900)
        self.w.show()
        self.pump(3)

    def _close_modals(self):
        from PyQt6.QtWidgets import QApplication
        m = QApplication.activeModalWidget()
        if m is not None and m is not self.w:
            try:
                txt = m.windowTitle()
                lab = getattr(m, "text", None)
                if callable(lab):
                    txt += ": " + lab()
                self.closed_dialogs.append(txt[:300])
            except Exception:  # noqa: BLE001
                pass
            m.close()

    # ------------------------------------------------------------ event loop helpers
    def pump(self, sec: float = 0.5):
        t = time.time()
        while time.time() - t < sec:
            self.app.processEvents()
            time.sleep(0.02)

    def wait(self, cond, timeout: float = 20.0) -> bool:
        t = time.time()
        while time.time() - t < timeout:
            self.app.processEvents()
            try:
                if cond():
                    return True
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.05)
        return False

    def js(self, ed, expr: str, timeout: float = 10.0):
        box = {}
        ed.page().runJavaScript(f"(function(){{try{{return {expr};}}catch(e){{return 'ERR:'+e;}}}})()",
                                lambda v: box.setdefault("v", v))
        self.wait(lambda: "v" in box, timeout)
        return box.get("v")

    def capture(self, ed, fn_name: str, *args, timeout: float = 25.0):
        """Call ed._complete / _signature / _hover; return what it sends to radResolve (waits for async
        language-server answers)."""
        sent = []
        orig = ed._js
        mark = f"radResolve({args[0]},"
        ed._js = lambda code: sent.append(code) if code.startswith(mark) else orig(code)
        try:
            getattr(ed, fn_name)(*args)
            self.wait(lambda: bool(sent), timeout)
        finally:
            ed._js = orig
        for code in sent:
            payload = code[len("radResolve("):].split(",", 1)[1].rsplit(");", 1)[0]
            try:
                return json.loads(payload)
            except ValueError:
                return payload
        return None

    # ------------------------------------------------------------ projects
    def open_project(self, folder: Path):
        w = self.w
        try:
            if getattr(w, "sln", None) is not None:
                w.save_all()
                w.close_solution()
        except Exception:  # noqa: BLE001
            pass
        self.pump(0.5)
        w.open_project(Path(folder), ask=False)
        self.pump(2)
        return w.project

    def close(self):
        try:
            if getattr(self.w, "session", None) is not None:
                self.w.stop_project()
            self.w.save_all()
            self.w.close_solution()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.w.close()
        except Exception:  # noqa: BLE001
            pass
        self.pump(1)
        from PyQt6.QtCore import QSettings
        QSettings().clear()


def host() -> IdeHost:
    global _HOST
    if _HOST is None:
        _HOST = IdeHost()
    return _HOST


def editor_for_form(h: IdeHost, form="Form1", control="Button1", event="Click"):
    """Double-click on the control (goto_event) and return (editor, body line index, handler)."""
    w = h.w
    doc = w._doc(form)
    owner = next((c for c in doc.form.controls if c.name == control), None)
    w.goto_event(form, owner, event)
    h.pump(1)
    ed = w.codeviews[form].editor
    h.wait(lambda: getattr(ed, "_ready", True), 40)
    h.pump(1)
    fp = w.plugin_for_form(form)
    handler = fp.handler_for(doc.form, owner, event)
    line = fp.find_handler(ed.text(), handler)
    return ed, line, handler
