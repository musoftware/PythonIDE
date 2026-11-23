"""OllyDbg-style CPU view + the live assembly editor (the IDE side of radide/asm_intel/cpuview).

* **Debug > Windows > CPU** (Alt+C): one dock with four synchronised panes - disassembly (jump arrows, current
  instruction, breakpoints, labels and comments of the user, "jump is taken" info line), registers (flag bits you
  can click, changed values in red, FPU / SSE pages), dump (hex / ASCII, edit bytes) and stack (return addresses
  and strings). It works for every gdb session (assembly, C, C++, Rust: radide/nativedbg.py) and for RAD IDE's
  8086 emulator (radide/emu8086). Keys while it has the focus: F2 F4 F7 F8 F9 Ctrl+F9 Ctrl+G Space Ctrl+E ; : Enter.
  It comes up by itself at the first stop of an assembly program (Debug > "CPU View at First Stop").
* **Assembly editors**: jump arrows in the gutter, read / write highlighting of the register under the caret, and
  while debugging inline values after each executed line, the arrow of the current conditional jump coloured by
  "taken / not taken", and a hover with the register's live value (radide/asm_intel/cpuview/editor_live.py).

Docs: docs/ASSEMBLY.md ("CPU view"). Test: samples/Tests/Assembly/SmartCpuView/test_cpu_view.py.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QDockWidget


class CpuHub(QObject):
    def __init__(self, win):
        super().__init__(win)
        from ..asm_intel.cpuview.editor_live import LiveSession
        from ..asm_intel.cpuview.panes import CpuView
        self.win = win
        self.view = CpuView(win)
        self.dock = QDockWidget("CPU", win)
        self.dock.setObjectName("CpuView")
        self.dock.setWidget(self.view)
        self.backend = None
        self.live = LiveSession()
        self._auto_for = None
        self.dock.visibilityChanged.connect(lambda vis: vis and self.refresh_view())

    # ------------------------------------------------------------ debugger events
    def _backend(self):
        from ..asm_intel.cpuview.backend import backend_for
        self.backend = backend_for(self.win, self.backend)
        return self.backend

    def refresh_view(self, new_stop: bool = False):
        be = self._backend()
        if be is None or not be.alive():
            return
        self.view.attach(be)
        self.view.refresh(new_stop=new_stop)

    def on_stopped(self, info):
        be = self._backend()
        if be is None or not be.alive():
            return
        be.on_stopped()
        s = self.win.session
        if s is not self._auto_for:
            self._auto_for = s
            if self._auto_show() and self._is_assembly(be) and not self.dock.isVisible():
                self.dock.show()
                self.dock.raise_()
                if not self.dock.isFloating():
                    try:
                        self.win.resizeDocks([self.dock], [max(320, int(self.win.height() * 0.45))],
                                             Qt.Orientation.Vertical)
                    except Exception:  # noqa: BLE001
                        pass
        if self.dock.isVisible():
            QTimer.singleShot(0, lambda: self.refresh_view(new_stop=True))
        self._live(be)

    def _is_assembly(self, be) -> bool:
        if be.kind == "emu8086":
            return False                     # the 8086 emulator has its own dock; the CPU view is one click away
        d = getattr(be, "d", None)
        return getattr(d, "linemap", None) is not None

    def _auto_show(self) -> bool:
        try:
            v = self.win.settings.value("asm/cpuViewAtFirstStop", True)
        except Exception:  # noqa: BLE001
            return True
        return v in (True, "true", "1", 1)

    def _live(self, be):
        at = getattr(self.win, "stopped_at", None)
        if not at:
            return
        ed, line = at
        from ..asm_intel.cpuview.editor_live import is_asm_editor
        from ..asm_intel.cpuview.texts import lang
        if not is_asm_editor(ed):
            return

        def got(snap):
            if snap is not None:
                try:
                    self.live.on_stop(ed, line, snap, lang())
                except RuntimeError:
                    pass
        be.snapshot(got)

    def on_resumed(self):
        self.view.stale()

    def on_finished(self):
        if self.win.session is None:
            self.view.clear()
            self.live.finish()
            self.backend = None


# ====================================================================== editors
_timers: dict = {}


def on_editor_ready(ed) -> None:
    from ..asm_intel.cpuview import editor_live as L
    if not L.is_asm_editor(ed):
        return
    try:
        L.inject(ed)
        L.push_static(ed)
        t = QTimer(ed)
        t.setSingleShot(True)
        t.setInterval(450)
        t.timeout.connect(lambda: L.push_static(ed))
        ed.textEdited.connect(t.start)
        _timers[id(ed)] = t
    except Exception as e:  # noqa: BLE001 - never break the editor
        print(f"[cpu view] editor hook: {e}")


# ====================================================================== install
def install(win) -> None:
    hub = CpuHub(win)
    win.cpu_view = hub
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, hub.dock)
    hub.dock.hide()

    ep = win.extension_points          # the CPU view never breaks debugging: its errors are logged
    ep.on("debug_paused", lambda info: hub.on_stopped(info), "cpu view")
    ep.on("debug_resumed", lambda: hub.on_resumed(), "cpu view")
    ep.on("program_finished", lambda _code, _session: hub.on_finished(), "cpu view")

    try:
        from ..monaco_editor import MonacoEditor
        if on_editor_ready not in MonacoEditor.ready_hooks:
            MonacoEditor.ready_hooks.append(on_editor_ready)
    except ImportError:                       # no QtWebEngine
        pass
    QTimer.singleShot(90, lambda: _build_menu(win, hub))     # after native_debug's Debug > Windows entries


def _build_menu(win, hub):
    menu = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") in ("Debug", "تصحيح")), None)
    if menu is None:
        return
    windows = next((a.menu() for a in menu.actions() if a.menu() is not None
                    and a.text().replace("&", "") == "Windows"), None)
    act = hub.dock.toggleViewAction()
    act.setText("CPU (OllyDbg Style)")
    act.setShortcut(QKeySequence("Alt+C"))
    (windows or menu).addAction(act)
    win.a_cpu_view = act
    auto = QAction("CPU View at First Stop", win, checkable=True)
    auto.setChecked(hub._auto_show())
    auto.toggled.connect(lambda on: win.settings.setValue("asm/cpuViewAtFirstStop", on))
    menu.addAction(auto)
    win.a_cpu_view_auto = auto


__all__ = ["install", "CpuHub", "on_editor_ready"]
