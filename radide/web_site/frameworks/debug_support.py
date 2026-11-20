"""F5 for the backend frameworks whose debugger attaches to the running server process.

- ASP.NET Core: the DevServer runs ``dotnet bin/Debug/<tfm>/<App>.dll`` (after ``dotnet build``); when it listens,
  **netcoredbg** attaches to that process over DAP (radide.bridgedebug.AttachDap, "coreclr" attach by processId).
- Spring Boot: ``mvnw spring-boot:run`` forks the application JVM with
  ``-agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=127.0.0.1:<port>``; radide.jdwp_engine.JdwpSession
  connects, sets the breakpoints when the classes load and resumes the VM.

The session object is put into ``win.session`` like every other debugger, wired the way radide/web_site/debug.py
does it, so F9 / F10 / F11 / Locals / Call Stack / Watch / Stop work unchanged. Stopping the debugger stops the
site; stopping the site ends the debug session.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSlot


class _Attacher(QObject):
    """Lives in the GUI thread: DevServer signals (emitted from worker threads) reach these slots queued."""

    def __init__(self, win, make_session, label: str):
        super().__init__(win)
        self.win = win
        self.make_session = make_session
        self.label = label
        self.srv = None
        self.session = None

    @pyqtSlot()
    def on_ready(self):
        srv = self.srv
        if srv is None or self.session is not None:
            return
        if srv.backend_error:
            self.win.log(f"*** {self.label}: the site did not start - no debugger ({srv.backend_error})")
            return
        proc = getattr(srv, "_proc", None)
        pid = proc.pid if proc is not None else 0
        s = self.make_session(pid)
        if s is None:
            return
        self.session = s
        s.stopped.connect(self.on_paused)          # before _wire: the file is open when _on_stopped marks the line
        from ..debug import _wire
        _wire(self.win, s)
        self.win.session = s
        s.finished.connect(self.on_session_end)
        s.start()
        self.win._update_actions()
        self.win.log(f"[debug] {self.label} attached (pid {pid}) - set breakpoints with F9")

    def on_paused(self, info):
        f = getattr(info, "file", "")
        if f and self.win._editor_for_file(f) is None and Path(f).exists():
            opener = getattr(self.win, "open_file", None)
            if callable(opener):
                opener(f, getattr(info, "line", None))

    @pyqtSlot(str)
    def on_log(self, text: str):
        if "Listening for transport dt_socket" in text and self.session is None:
            QTimer.singleShot(200, self.on_ready)

    @pyqtSlot(int)
    def on_session_end(self, _code=0):
        srv = self.srv
        if srv is not None and getattr(self.win, "web_server", None) is srv:
            from ...features import web_workspace as ww
            QTimer.singleShot(0, lambda: getattr(self.win, "web_server", None) is srv and ww.stop_website(self.win))

    @pyqtSlot()
    def on_stopped(self):
        s = self.session
        if s is not None and self.win.session is s and s.running():
            QTimer.singleShot(0, s.stop)


def _prepare(win, project):
    from ...features import web_workspace as ww
    if win.session is not None and win.session.running():
        return None
    if getattr(win, "web_server", None) is not None:
        ww.stop_website(win)
    win._sync_breakpoints()
    win.output.clear()
    win.locals.clear()
    win.callstack.clear()
    win.dock_output.show()
    win.dock_output.raise_()
    return ww


def debug_aspnet(win, plugin, project, path=None):
    """F5 on an ASP.NET Core site. Returns True when the debug run started, None to just run the site."""
    from .aspnet import dotnet_exe, find_netcoredbg
    dbg = find_netcoredbg()
    if not dbg:
        win.log("[debug] netcoredbg was not found (%LOCALAPPDATA%\\RADIDE\\tools\\netcoredbg) - running without "
                "the debugger.")
        return None
    ww = _prepare(win, project)
    if ww is None:
        return True
    folder = Path(project.folder).resolve()
    bps = win._all_breakpoints()
    dotnet = dotnet_exe() or "dotnet"

    def make(pid):
        from ...bridgedebug import AttachDap
        if not pid:
            return None
        s = AttachDap([dbg, "--interpreter=vscode"], "coreclr",
                      {"type": "coreclr", "request": "attach", "processId": pid, "justMyCode": True},
                      folder, None, bps, win)
        s.break_on_exception = win.settings.value("debug/break_on_exception", True) in (True, "true")
        return s

    win.log(f"------ Debug ASP.NET Core site '{project.name}' (dotnet build + netcoredbg attach) ------")
    att = _Attacher(win, make, "netcoredbg")
    hook = lambda _srv, _spec: plugin.debug_spec(folder, dotnet)      # noqa: E731
    srv = ww.run_website(win, project, debug=False, path=path, backend_hook=hook)
    if srv is None:
        return True
    att.srv = srv
    srv.backendReady.connect(att.on_ready)
    srv.stopped.connect(att.on_stopped)
    win.statusBar().showMessage(f"Building and starting {project.name} for debugging...")
    return True


def debug_spring(win, plugin, project, path=None):
    """F5 on a Spring Boot site: JDWP (radide/jdwp_engine.py)."""
    from ...bridgedebug import free_port
    ww = _prepare(win, project)
    if ww is None:
        return True
    folder = Path(project.folder).resolve()
    bps = win._all_breakpoints()
    port = free_port()

    def make(_pid):
        from ...jdwp_engine import JdwpSession
        s = JdwpSession(port, folder, bps, win)
        s.break_on_exception = False
        return s

    win.log(f"------ Debug Spring Boot site '{project.name}' (JDWP on 127.0.0.1:{port}) ------")
    att = _Attacher(win, make, "JDWP")

    def hook(srv, _spec):
        return plugin.debug_backend(srv, port)

    srv = ww.run_website(win, project, debug=False, path=path, backend_hook=hook)
    if srv is None:
        return True
    att.srv = srv
    srv.log.connect(att.on_log)          # the JVM waits (suspend=y) after "Listening for transport dt_socket"
    srv.stopped.connect(att.on_stopped)
    win.statusBar().showMessage(f"Starting {project.name} under the Java debugger...")
    return True


__all__ = ["debug_aspnet", "debug_spring"]
