"""Integrated terminal (View > Terminal, Ctrl+`): a QProcess-based shell
(Command Prompt, PowerShell or Git Bash) running in the project folder, with an
input line, command history (Up/Down) and Ctrl+C to stop the running command."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt
from PyQt6.QtGui import QAction, QFont, QKeySequence, QTextCursor
from PyQt6.QtWidgets import (QComboBox, QDockWidget, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                             QToolButton, QVBoxLayout, QWidget)

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")
MAX_HISTORY = 200


def available_shells() -> list[tuple[str, list[str], bool]]:
    """(label, argv, echoes_input) of the shells found on this machine."""
    shells: list[tuple[str, list[str], bool]] = []
    if sys.platform == "win32":
        comspec = os.environ.get("COMSPEC") or shutil.which("cmd.exe") or "cmd.exe"
        shells.append(("Command Prompt", [comspec, "/K", "chcp 65001>nul"], True))
        ps = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
        if ps:
            shells.append(("PowerShell", [ps, "-NoLogo", "-NoProfile", "-NoExit", "-Command", "-"], False))
        pwsh = shutil.which("pwsh.exe")
        if pwsh and pwsh != ps:
            shells.append(("PowerShell 7", [pwsh, "-NoLogo", "-NoProfile", "-NoExit", "-Command", "-"], False))
        for bash in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"):
            if Path(bash).exists():
                shells.append(("Git Bash", [bash, "--login"], False))
                break
    else:
        sh = os.environ.get("SHELL") or shutil.which("bash") or "/bin/sh"
        shells.append((Path(sh).name, [sh], False))
    return shells


def child_pids(pid: int) -> list[int]:
    """Direct children of *pid* (Windows: Toolhelp snapshot, no extra tools)."""
    if sys.platform != "win32":
        try:
            out = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True).stdout
            return [int(x) for x in out.split()]
        except OSError:
            return []
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]
    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)          # TH32CS_SNAPPROCESS
    if not snap or snap == wintypes.HANDLE(-1).value:
        return []
    out = []
    try:
        e = PROCESSENTRY32W()
        e.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = k32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            if e.th32ParentProcessID == pid and e.th32ProcessID != pid:
                name = e.szExeFile.lower()
                if name not in ("conhost.exe",):
                    out.append(int(e.th32ProcessID))
            ok = k32.Process32NextW(snap, ctypes.byref(e))
    finally:
        k32.CloseHandle(snap)
    return out


def kill_tree(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


class HistoryLine(QLineEdit):
    """Input line with Up/Down history and Ctrl+C / Ctrl+L."""

    def __init__(self, term: "TerminalWidget"):
        super().__init__()
        self.term = term
        self.history: list[str] = []
        self.pos = 0
        self._draft = ""

    def add(self, cmd: str):
        if cmd and (not self.history or self.history[-1] != cmd):
            self.history.append(cmd)
            del self.history[:-MAX_HISTORY]
        self.pos = len(self.history)
        self._draft = ""

    def keyPressEvent(self, e):
        k, mods = e.key(), e.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        if k == Qt.Key.Key_Up:
            self.older()
            return
        if k == Qt.Key.Key_Down:
            self.newer()
            return
        if ctrl and k == Qt.Key.Key_C and not self.hasSelectedText():
            self.term.interrupt()
            return
        if ctrl and k == Qt.Key.Key_L:
            self.term.out.clear()
            return
        super().keyPressEvent(e)

    def older(self):
        if not self.history:
            return
        if self.pos == len(self.history):
            self._draft = self.text()
        self.pos = max(0, self.pos - 1)
        self.setText(self.history[self.pos])

    def newer(self):
        if self.pos >= len(self.history):
            return
        self.pos += 1
        self.setText(self.history[self.pos] if self.pos < len(self.history) else self._draft)


class TerminalWidget(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.proc: QProcess | None = None
        self.shells = available_shells()
        self.echoes = True
        self.cwd = ""
        self.shell = QComboBox()
        for label, _argv, _e in self.shells:
            self.shell.addItem(label)
        saved = win.settings.value("terminal/shell", "") or ""
        if saved and self.shell.findText(saved) >= 0:
            self.shell.setCurrentIndex(self.shell.findText(saved))
        self.shell.currentIndexChanged.connect(lambda _i: self.restart())
        self.where = QLabel()
        self.where.setProperty("radRole", "muted")

        def btn(text, tip, slot):
            b = QToolButton(text=text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            return b
        bar = QHBoxLayout()
        bar.setContentsMargins(2, 2, 2, 0)
        bar.addWidget(QLabel("Shell:"))
        bar.addWidget(self.shell)
        bar.addWidget(btn("Restart", "Start a new shell in the project folder", self.restart))
        bar.addWidget(btn("Stop (Ctrl+C)", "Stop the running command", self.interrupt))
        bar.addWidget(btn("Clear", "Clear the terminal (Ctrl+L)", lambda: self.out.clear()))
        bar.addWidget(self.where, 1)
        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.setFont(QFont("Consolas", 9))
        self.out.setMaximumBlockCount(10000)
        self.out.setUndoRedoEnabled(False)
        self.input = HistoryLine(self)
        self.input.setFont(QFont("Consolas", 9))
        self.input.setPlaceholderText("Type a command and press Enter  (Up/Down: history, Ctrl+C: stop)")
        self.input.returnPressed.connect(self.submit)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        lay.addLayout(bar)
        lay.addWidget(self.out, 1)
        lay.addWidget(self.input)
        hist = win.settings.value("terminal/history", []) or []
        self.input.history = [hist] if isinstance(hist, str) else list(hist)
        self.input.pos = len(self.input.history)

    # ------------------------------------------------------------ process
    def folder(self) -> str:
        if self.win.project is not None:
            return str(self.win.project.folder)
        return str(Path.home())

    def running(self) -> bool:
        return self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning

    def start(self, folder: str | None = None):
        self.stop()
        if not self.shells:
            self.append("*** No shell found\n")
            return
        label, argv, self.echoes = self.shells[max(0, self.shell.currentIndex())]
        self.cwd = folder or self.folder()
        self.where.setText(self.cwd)
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.setWorkingDirectory(self.cwd)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("TERM", "dumb")
        p.setProcessEnvironment(env)
        p.readyReadStandardOutput.connect(self._read)
        p.finished.connect(lambda code, _s, pp=p: self._finished(pp, code))
        self.proc = p
        self.append(f"--- {label} in {self.cwd} ---\n")
        p.start(argv[0], argv[1:])
        if not p.waitForStarted(5000):
            self.append(f"*** Cannot start {argv[0]}\n")
            self.proc = None
            return
        if "powershell" in argv[0].lower() or "pwsh" in argv[0].lower():
            self._write("[Console]::OutputEncoding = [Text.Encoding]::UTF8; $OutputEncoding = [Text.Encoding]::UTF8;"
                        " $ProgressPreference = 'SilentlyContinue'")

    def restart(self):
        self.win.settings.setValue("terminal/shell", self.shell.currentText())
        self.start()

    def stop(self):
        p, self.proc = self.proc, None
        if p is not None and p.state() != QProcess.ProcessState.NotRunning:
            try:
                p.finished.disconnect()
            except TypeError:
                pass
            pid = int(p.processId() or 0)
            if pid:
                kill_tree(pid)
            p.kill()
            p.waitForFinished(3000)
        if p is not None:
            p.deleteLater()

    def interrupt(self):
        """Ctrl+C: kill the command running inside the shell (the shell stays)."""
        if not self.running():
            return
        kids = child_pids(int(self.proc.processId() or 0))
        for pid in kids:
            kill_tree(pid)
        self.append("^C\n" if kids else "^C (nothing running)\n")

    def _write(self, line: str):
        if self.running():
            self.proc.write((line + "\r\n" if sys.platform == "win32" else line + "\n").encode("utf-8"))

    def submit(self):
        cmd = self.input.text()
        self.input.clear()
        self.input.add(cmd.strip())
        self.win.settings.setValue("terminal/history", self.input.history[-50:])
        if cmd.strip().lower() in ("cls", "clear"):
            self.out.clear()
            cmd = ""
        if not self.running():
            self.start()
        if not self.echoes:
            self.append(f"{self.shell.currentText()[:2].upper()}> {cmd}\n")
        self._write(cmd)

    def run_command(self, cmd: str):
        """Run a command in the terminal (used by other features)."""
        if not self.running():
            self.start()
        self.input.add(cmd)
        if not self.echoes:
            self.append(f"> {cmd}\n")
        self._write(cmd)

    @staticmethod
    def _decode(data: bytes) -> str:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("mbcs" if sys.platform == "win32" else "latin-1", errors="replace")

    def _read(self):
        if self.proc is None:
            return
        text = self._decode(bytes(self.proc.readAllStandardOutput()))
        self.append(ANSI.sub("", text).replace("\r\n", "\n").replace("\r", ""))

    def _finished(self, p, code):
        if p is self.proc:
            self._read()
            self.append(f"\n--- shell exited (code {code}); press Enter to start a new one ---\n")
            self.proc = None
            p.deleteLater()

    def append(self, text: str):
        self.out.moveCursor(QTextCursor.MoveOperation.End)
        self.out.insertPlainText(text)
        self.out.moveCursor(QTextCursor.MoveOperation.End)
        self.out.ensureCursorVisible()

    def on_project_changed(self):
        if self.running() and self.cwd != self.folder():
            self.start()


def show_terminal(win):
    t = win.terminal
    win.dock_terminal.show()
    win.dock_terminal.raise_()
    if not t.running():
        t.start()
    t.input.setFocus()


def install(win) -> None:
    win.terminal = TerminalWidget(win)
    d = QDockWidget("Terminal", win)
    d.setObjectName("Terminal")
    d.setWidget(win.terminal)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d)
    win.tabifyDockWidget(win.dock_output, d)
    win.dock_output.raise_()
    win.dock_terminal = d
    a = QAction("&Terminal", win)
    a.setShortcut(QKeySequence("Ctrl+`"))
    a.triggered.connect(lambda: show_terminal(win))
    win.a_terminal = a
    view = next((x.menu() for x in win.menuBar().actions() if x.text().replace("&", "") == "View"), None)
    if view is not None:
        view.addSeparator()
        view.addAction(a)
    # follow the open project (start lazily when the dock is first shown)
    d.visibilityChanged.connect(lambda vis: vis and not win.terminal.running() and win.terminal.start())
    orig_open = win.open_project

    def open_project(*args, **kw):
        r = orig_open(*args, **kw)
        try:
            win.terminal.on_project_changed()
        except Exception:  # noqa: BLE001 - never break opening a project
            pass
        return r
    win.open_project = open_project
    orig_close = win.closeEvent

    def close_event(e):
        orig_close(e)
        if e.isAccepted():
            win.terminal.stop()
    win.closeEvent = close_event


__all__ = ["TerminalWidget", "available_shells", "child_pids", "show_terminal"]
