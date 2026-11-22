"""Remote development (VS Code "Remote - SSH / WSL / Dev Containers" style).

File > Open Remote:
  * Connect to SSH Host...  host, port, user, password / private key (+ passphrase) / SSH agent; secrets go to the
    Windows Credential Manager (keyring) when "Remember" is ticked, never to the settings file.  Unknown host
    keys are shown with their SHA256 fingerprint and must be accepted once (saved to RADIDE's known_hosts).
  * Open WSL Folder...  a distribution + folder; files through \\\\wsl$, commands through `wsl -d <distro>`.
  * Open Folder in Dev Container...  a folder with .devcontainer/devcontainer.json; the container is started
    (built the first time) with the docker CLI and every command runs through `docker exec`.
The **Remote Explorer** dock shows the remote folder (lazy tree, path bar, New File/Folder, Rename, Delete,
Upload, Download, Refresh), opens files in editor tabs (SSH files are cached under
%LOCALAPPDATA%\\RADIDE\\remote\\cache and uploaded on Save, with a conflict check), runs Run / Build / any
command on the remote side with the output in the Output window, searches the remote folder (grep on the
remote side, Python fallback), and opens a **remote terminal** as a tab of the Terminal dock.  A polling
watcher reloads open files and refreshes expanded folders when they change on the remote side.
Backends: radide/remote/*.
"""
from __future__ import annotations

import os
import posixpath
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QTextCursor
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget,
                             QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu,
                             QMessageBox, QPlainTextEdit, QPushButton, QRadioButton, QSpinBox, QSplitter,
                             QStyle, QTabWidget, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import theme
from ..remote import profiles
from ..remote.base import RemoteError, norm

ROLE = Qt.ItemDataRole.UserRole
MAX_OPEN = 8 * 1024 * 1024
POLL_SECONDS = 3.0


# ============================================================================ async helper
class _Relay(QObject):
    sig = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.sig.connect(self._dispatch)
        self.pending = 0

    def _dispatch(self, payload):
        self.pending -= 1
        cb, value = payload
        if cb is not None:
            try:
                cb(value)
            except Exception as e:  # noqa: BLE001
                print(f"[remote] callback failed: {e}")


_RELAY: _Relay | None = None


def relay() -> _Relay:
    global _RELAY
    if _RELAY is None:
        _RELAY = _Relay()
    return _RELAY


def run_async(fn, on_ok=None, on_err=None) -> None:
    """Run fn() in a thread; on_ok(result) / on_err(exception) run on the Qt thread."""
    r = relay()
    r.pending += 1

    def work():
        try:
            payload = (on_ok, fn())
        except Exception as e:  # noqa: BLE001
            payload = (on_err, e)
        try:
            r.sig.emit(payload)
        except RuntimeError:
            pass
    threading.Thread(target=work, daemon=True, name="radide-remote").start()


def wait_idle(timeout: float = 30) -> bool:
    """Tests: process events until every run_async job has delivered its result."""
    t0 = time.monotonic()
    while relay().pending > 0 and time.monotonic() - t0 < timeout:
        QApplication.processEvents()
        time.sleep(0.01)
    QApplication.processEvents()
    return relay().pending == 0


class _TextRelay(QObject):
    text = pyqtSignal(str)
    done = pyqtSignal(int)


# ============================================================================ prompts (overridable in tests)
def _answers(win) -> dict:
    return win.__dict__.setdefault("_remote_answers", {})


def ask(win, key: str, title: str, text: str, buttons=("Yes", "No"), default=0, detail: str = "") -> str:
    """Ask the user; returns the chosen button text. Tests set win._remote_answers[key]."""
    ans = _answers(win)
    if key in ans:
        return ans[key]
    box = QMessageBox(win)
    box.setWindowTitle(title)
    box.setText(text)
    if detail:
        box.setDetailedText(detail)
    made = [box.addButton(b, QMessageBox.ButtonRole.AcceptRole if i == 0 else QMessageBox.ButtonRole.RejectRole)
            for i, b in enumerate(buttons)]
    box.setDefaultButton(made[default])
    box.exec()
    clicked = box.clickedButton()
    return clicked.text() if clicked is not None else buttons[-1]


def tell(win, title: str, text: str, error: bool = False) -> None:
    win.log(f"[remote] {title}: {text}")
    if "_remote_answers" in win.__dict__:          # tests: no modal boxes
        win.__dict__.setdefault("_remote_messages", []).append((title, text))
        return
    (QMessageBox.warning if error else QMessageBox.information)(win, title, text)


# ============================================================================ session
class RemoteSession(QObject):
    """One connection (SSH host, WSL distro or Dev Container) and everything opened through it."""
    _ids = 0

    def __init__(self, win, fs, profile: dict | None = None, dc=None):
        super().__init__(win)
        RemoteSession._ids += 1
        self.id = RemoteSession._ids
        self.win, self.fs, self.profile, self.dc = win, fs, profile, dc
        self.views: dict[str, RemoteFileView] = {}
        self.stop_flag = threading.Event()
        self.running = False
        from ..remote.watcher import PollingWatcher
        self.watcher = PollingWatcher(fs, POLL_SECONDS, self)
        self.watcher.fileChanged.connect(self._on_file_changed)
        self.watcher.dirChanged.connect(lambda p: explorer(win).refresh_dir(self, p))
        self.watcher.failed.connect(lambda m: win.log(f"[remote] {self.label}: watcher: {m}"))
        self.watcher.start()

    @property
    def label(self) -> str:
        return self.fs.label

    @property
    def kind(self) -> str:
        return self.fs.kind

    # ---------------------------------------------------------------- saved commands
    def _cmd_key(self) -> str:
        return f"remote/cmds/{self.fs.key}"

    def command(self, which: str) -> str:
        if self.profile is not None and self.profile.get(f"{which}_cmd"):
            return self.profile[f"{which}_cmd"]
        return str(profiles.settings().value(f"{self._cmd_key()}/{which}", "") or "")

    def set_command(self, which: str, cmd: str) -> None:
        if self.profile is not None:
            self.profile[f"{which}_cmd"] = cmd
            profiles.update_host(self.profile, **{f"{which}_cmd": cmd})
        profiles.settings().setValue(f"{self._cmd_key()}/{which}", cmd)

    # ---------------------------------------------------------------- files
    def cache_file(self, rpath: str) -> Path:
        lp = self.fs.local_path(rpath)
        return Path(lp) if lp is not None else profiles.cache_path(self.fs.key, rpath)

    def open_file(self, rpath: str, line: int | None = None, on_open=None) -> None:
        rpath = norm(rpath)
        v = self.views.get(rpath)
        if v is not None and self.win.tabs.indexOf(v) >= 0:
            self.win.tabs.setCurrentWidget(v)
            if line:
                v.editor.goto_line(line - 1)
            if on_open:
                on_open(v)
            return
        self.win.statusBar().showMessage(f"Opening {rpath} ...", 3000)

        def load():
            e = self.fs.stat(rpath)
            if e is None:
                raise RemoteError(f"{rpath} does not exist")
            if e.is_dir:
                raise RemoteError(f"{rpath} is a folder")
            if e.size > MAX_OPEN:
                raise RemoteError(f"{rpath} is {e.size:,} bytes - too big for the editor; use Download")
            return e, self.fs.read(rpath)

        def done(res):
            e, data = res
            if b"\x00" in data[:8192]:
                tell(self.win, "Remote", f"{posixpath.basename(rpath)} is a binary file - use Download.")
                return
            view = RemoteFileView(self, rpath, data, e)
            self.views[rpath] = view
            self.watcher.watch_file(rpath, e)
            self.win._show_tab(view, view.title())
            i = self.win.tabs.indexOf(view)
            if i >= 0:
                self.win.tabs.setTabToolTip(i, f"{self.label}:{rpath}")
            if line:
                view.editor.goto_line(line - 1)
            if on_open:
                on_open(view)
        run_async(load, done, lambda ex: tell(self.win, "Open remote file", str(ex), True))

    def forget_view(self, view) -> None:
        if self.views.get(view.rpath) is view:
            del self.views[view.rpath]
            self.watcher.unwatch_file(view.rpath)

    def _on_file_changed(self, rpath: str, exists: bool) -> None:
        v = self.views.get(rpath)
        if v is not None:
            v.on_remote_changed(exists)

    # ---------------------------------------------------------------- commands
    def run_command(self, cmd: str, title: str = "Run", cwd: str | None = None) -> bool:
        """Run *cmd* on the remote side; output goes to the Output window. False if one is running."""
        win = self.win
        if self.running:
            tell(win, "Remote", f"A command is still running on {self.label} (Stop it first).")
            return False
        cwd = cwd or explorer(win).current_folder(self) or self.fs.root
        self.running = True
        self.stop_flag.clear()
        try:
            win.dock_output.show()
            win.dock_output.raise_()
        except AttributeError:
            pass
        win.log(f"------ {title} on {self.label}: {cmd}   (in {cwd}) ------")
        tr = _TextRelay(self)
        buf = {"s": ""}
        t0 = time.monotonic()

        def on_text(s):
            buf["s"] += s.replace("\r\n", "\n")
            *lines, buf["s"] = buf["s"].split("\n")
            for ln in lines:
                win.log(ln)

        def on_done(code):
            if buf["s"]:
                win.log(buf["s"])
            self.running = False
            state = "stopped" if code == -1 and self.stop_flag.is_set() else f"exit code {code}"
            win.log(f"------ {title} finished ({state}, {time.monotonic() - t0:.1f} s) ------")
            win.statusBar().showMessage(f"{title} on {self.label}: {state}", 5000)
            self.last_exit = code
        tr.text.connect(on_text)
        tr.done.connect(on_done)

        def work():
            try:
                code = self.fs.exec_stream(cmd, cwd, tr.text.emit, self.stop_flag.is_set)
            except Exception as e:  # noqa: BLE001
                tr.text.emit(f"*** {e}\n")
                code = -2
            try:
                tr.done.emit(code)
            except RuntimeError:
                pass
        threading.Thread(target=work, daemon=True, name="radide-remote-run").start()
        return True

    def stop_command(self) -> None:
        self.stop_flag.set()

    # ---------------------------------------------------------------- close
    def close(self) -> None:
        self.stop_flag.set()
        self.watcher.stop()
        for v in list(self.views.values()):
            v.detach()
        try:
            self.fs.close()
        except Exception:  # noqa: BLE001
            pass


def sessions(win) -> dict[int, RemoteSession]:
    return win.__dict__.setdefault("remote_sessions", {})


def current_session(win) -> RemoteSession | None:
    w = win.tabs.currentWidget() if hasattr(win, "tabs") else None
    if isinstance(w, RemoteFileView) and w.session is not None:
        return w.session
    ex = win.__dict__.get("remote_explorer")
    s = ex.selected_session() if ex is not None else None
    if s is not None:
        return s
    ss = list(sessions(win).values())
    return ss[-1] if ss else None


def add_session(win, s: RemoteSession) -> RemoteSession:
    sessions(win)[s.id] = s
    ex = explorer(win)
    ex.add_session(s)
    win.dock_remote.show()
    win.dock_remote.raise_()
    win.log(f"[remote] connected: {s.label}  (folder {s.fs.root})")
    win.statusBar().showMessage(f"Connected to {s.label}", 5000)
    _update_actions(win)
    return s


def close_session(win, s: RemoteSession, ask_save: bool = True) -> bool:
    mods = [v for v in s.views.values() if v.editor.isModified()]
    if mods and ask_save:
        a = ask(win, "close_session", "Remote", f"Save changes to {len(mods)} remote file(s) before "
                f"disconnecting from {s.label}?", ("Save", "Discard", "Cancel"))
        if a == "Cancel":
            return False
        if a == "Save" and not all(v.save() for v in mods):
            return False
    for v in list(s.views.values()):
        i = win.tabs.indexOf(v)
        if i >= 0:
            win.tabs.removeTab(i)
    term = win.__dict__.get("_remote_terms", {}).pop(s.id, None)
    if term is not None:
        term.close_shell()
        tabs = win.__dict__.get("_remote_term_tabs")
        if tabs is not None and tabs.indexOf(term) >= 0:
            tabs.removeTab(tabs.indexOf(term))
    s.close()
    sessions(win).pop(s.id, None)
    explorer(win).remove_session(s)
    win.log(f"[remote] disconnected: {s.label}")
    _update_actions(win)
    return True


# ============================================================================ editor tab
class RemoteFileView(QWidget):
    """An editor tab for a remote file. save() uploads (save_current/save_all call it)."""

    def __init__(self, session: RemoteSession, rpath: str, data: bytes, entry):
        super().__init__()
        self.session, self.rpath = session, rpath
        self.base_sig = (round(entry.mtime, 3), entry.size)
        self.remote_changed = False
        try:
            text = data.decode("utf-8")
            self.encoding = "utf-8"
        except UnicodeDecodeError:
            text = data.decode("cp1252", errors="replace")
            self.encoding = "cp1252"
        self.newline = "\r\n" if "\r\n" in text else "\n"
        self.path = session.cache_file(rpath)
        if session.fs.local_path(rpath) is None:            # SSH: keep an offline copy in the cache
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_bytes(data)
            except OSError:
                pass
        from ..editor import make_editor
        try:
            from ..web_site.project import file_plugin
            plugin = file_plugin(Path(posixpath.basename(rpath)))
        except Exception:  # noqa: BLE001
            from ..languages import get_plugin
            plugin = get_plugin("python-tk")
        self.editor = make_editor(plugin, self.path)
        self.editor.setText(text.replace("\r\n", "\n") if self.newline == "\r\n" else text)
        self.editor.setModified(False)
        self.editor.modificationChanged.connect(lambda _m: self._update_title())
        self.banner = QLabel()
        theme.role(self.banner, "banner")
        self.banner.hide()
        self.where = QLabel(f"  {session.label}  :  {rpath}")
        theme.role(self.where, "muted")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.where)
        lay.addWidget(self.banner)
        lay.addWidget(self.editor, 1)
        self.setToolTip(f"{session.label}:{rpath}")

    def title(self) -> str:
        tag = {"ssh": "SSH", "wsl": "WSL", "devcontainer": "Container"}.get(self.session.kind, "Remote") \
            if self.session is not None else "Remote"
        return f"{posixpath.basename(self.rpath)} [{tag}]" + ("*" if self.editor.isModified() else "")

    def _update_title(self):
        tabs = self.session.win.tabs if self.session is not None else None
        if tabs is not None and tabs.indexOf(self) >= 0:
            tabs.setTabText(tabs.indexOf(self), self.title())

    def _show_banner(self, text: str):
        self.banner.setText(text)
        self.banner.setVisible(bool(text))

    def save(self) -> bool:
        s = self.session
        if s is None:
            return False
        win = s.win
        text = self.editor.text()
        if self.newline == "\r\n":
            text = text.replace("\r\n", "\n").replace("\n", "\r\n")
        data = text.encode(self.encoding, errors="replace")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            cur = s.fs.stat(self.rpath)
            if cur is not None and (round(cur.mtime, 3), cur.size) != self.base_sig:
                QApplication.restoreOverrideCursor()
                a = ask(win, "save_conflict", "Remote file changed",
                        f"{self.rpath} was changed on {s.label} after you opened it.\n"
                        "Overwrite it with your version?", ("Overwrite", "Cancel"), default=1)
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                if a != "Overwrite":
                    return False
            s.fs.write(self.rpath, data)
            e = s.fs.stat(self.rpath)
        except Exception as ex:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            tell(win, "Save remote file", f"Cannot upload {self.rpath}: {ex}\n(Your text stays in the editor.)",
                 True)
            return False
        QApplication.restoreOverrideCursor()
        if s.fs.local_path(self.rpath) is None:
            try:
                self.path.write_bytes(data)
            except OSError:
                pass
        if e is not None:
            self.base_sig = (round(e.mtime, 3), e.size)
            s.watcher.set_baseline(self.rpath, e)
        self.remote_changed = False
        self._show_banner("")
        self.editor.setModified(False)
        self._update_title()
        win.statusBar().showMessage(f"Uploaded {self.rpath} to {s.label}", 4000)
        return True

    def reload(self) -> None:
        s = self.session
        if s is None:
            return

        def load():
            return s.fs.stat(self.rpath), s.fs.read(self.rpath)

        def done(res):
            e, data = res
            text = data.decode(self.encoding, errors="replace")
            self.editor.setText(text.replace("\r\n", "\n") if self.newline == "\r\n" else text)
            self.editor.setModified(False)
            if e is not None:
                self.base_sig = (round(e.mtime, 3), e.size)
            self.remote_changed = False
            self._show_banner("")
            self._update_title()
            s.win.statusBar().showMessage(f"Reloaded {self.rpath}", 3000)
        run_async(load, done, lambda ex: tell(s.win, "Reload", str(ex), True))

    def on_remote_changed(self, exists: bool) -> None:
        s = self.session
        if not exists:
            self._show_banner("  The file was deleted on the remote side. Save to create it again.")
            return
        if not self.editor.isModified():
            s.win.log(f"[remote] {self.rpath} changed on {s.label} - reloaded")
            self.reload()
        else:
            self.remote_changed = True
            self._show_banner("  This file changed on the remote side. Saving will ask before overwriting; "
                              "File > Open Remote > Reload discards your edits.")

    def maybe_close(self) -> bool:
        if self.session is not None and self.editor.isModified():
            a = ask(self.session.win, "close_tab", "Remote", f"Save changes to {self.rpath} on "
                    f"{self.session.label}?", ("Save", "Discard", "Cancel"))
            if a == "Cancel" or (a == "Save" and not self.save()):
                return False
        if self.session is not None:
            self.session.forget_view(self)
        return True

    def detach(self) -> None:
        if self.session is not None:
            self.session.forget_view(self)
        self.session = None


# ============================================================================ remote terminal
class RemoteTerminal(QWidget):
    def __init__(self, win, session: RemoteSession):
        super().__init__()
        from .terminal import ANSI, HistoryLine
        self._ansi = ANSI
        self.win, self.session = win, session
        self.shell = None
        self.where = QLabel(session.label)
        theme.role(self.where, "muted")
        bar = QHBoxLayout()
        bar.setContentsMargins(2, 2, 2, 0)
        for text, tip, slot in (("Restart", "Start a new remote shell", self.restart),
                                ("Stop (Ctrl+C)", "Interrupt the running command", self.interrupt),
                                ("Clear", "Clear (Ctrl+L)", lambda: self.out.clear())):
            b = QToolButton(text=text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addWidget(self.where, 1)
        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.setFont(QFont("Consolas", 9))
        self.out.setMaximumBlockCount(10000)
        self.input = HistoryLine(self)
        self.input.setFont(QFont("Consolas", 9))
        self.input.setPlaceholderText(f"Command on {session.label}  (Up/Down: history, Ctrl+C: stop)")
        self.input.returnPressed.connect(self.submit)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        lay.addLayout(bar)
        lay.addWidget(self.out, 1)
        lay.addWidget(self.input)
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._poll)

    def start(self):
        self.close_shell()
        s = self.session
        cwd = explorer(self.win).current_folder(s) or s.fs.root
        try:
            self.shell = s.fs.open_shell(cwd)
        except Exception as e:  # noqa: BLE001
            self.append(f"*** Cannot open a shell on {s.label}: {e}\n")
            return
        self.append(f"--- shell on {s.label} in {cwd} ---\n")
        self.where.setText(f"{s.label}  {cwd}")
        self.timer.start()

    def restart(self):
        self.start()

    def close_shell(self):
        self.timer.stop()
        if self.shell is not None:
            self.shell.close()
            self.shell = None

    def interrupt(self):
        if self.shell is None:
            return
        from ..remote.process import ProcessShell
        if isinstance(self.shell, ProcessShell):         # no terminal: restart the shell
            self.append("^C (shell restarted)\n")
            self.start()
        else:
            self.shell.interrupt()

    def run_command(self, cmd: str):
        if self.shell is None:
            self.start()
        self.input.add(cmd)
        from ..remote.process import ProcessShell
        if self.shell is None or isinstance(self.shell, ProcessShell):     # a PTY shell echoes by itself
            self.append(f"$ {cmd}\n")
        if self.shell is not None:
            try:
                self.shell.write((cmd + "\n").encode("utf-8"))
            except Exception as e:  # noqa: BLE001
                self.append(f"*** {e}\n")

    def submit(self):
        cmd = self.input.text()
        self.input.clear()
        if cmd.strip() in ("clear", "cls"):
            self.out.clear()
            self.input.add(cmd.strip())
            return
        self.run_command(cmd)

    def _poll(self):
        if self.shell is None:
            return
        try:
            data = self.shell.poll()
        except Exception:  # noqa: BLE001
            data = None
        if data is None:
            self.timer.stop()
            self.shell = None
            self.append("\n--- remote shell ended; press Enter to start a new one ---\n")
            return
        if data:
            text = data.decode("utf-8", errors="replace")
            self.append(self._ansi.sub("", text).replace("\r\n", "\n").replace("\r", ""))

    def append(self, text: str):
        self.out.moveCursor(QTextCursor.MoveOperation.End)
        self.out.insertPlainText(text)
        self.out.moveCursor(QTextCursor.MoveOperation.End)

    def text(self) -> str:
        return self.out.toPlainText()


def open_terminal(win, s: RemoteSession | None = None) -> RemoteTerminal | None:
    """A remote shell as a tab of the Terminal dock (the local terminal stays the first tab)."""
    s = s or current_session(win)
    if s is None:
        tell(win, "Remote Terminal", "Connect to a remote host first (File > Open Remote).")
        return None
    terms = win.__dict__.setdefault("_remote_terms", {})
    term = terms.get(s.id)
    tabs = win.__dict__.get("_remote_term_tabs")
    if tabs is None:
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setTabsClosable(True)
        dock = getattr(win, "dock_terminal", None)
        if dock is not None and getattr(win, "terminal", None) is not None:
            tabs.addTab(win.terminal, "Local")
            dock.setWidget(tabs)
            tabs.tabBar().setTabButton(0, tabs.tabBar().ButtonPosition.RightSide, None)
        else:                                            # no Terminal feature: own dock
            dock = QDockWidget("Remote Terminal", win)
            dock.setObjectName("RemoteTerminal")
            dock.setWidget(tabs)
            win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
            win.tabifyDockWidget(win.dock_output, dock)
            win.dock_terminal_remote = dock
        win._remote_term_tabs = tabs
        win._remote_term_dock = dock

        def close_tab(i):
            w = tabs.widget(i)
            if isinstance(w, RemoteTerminal):
                w.close_shell()
                tabs.removeTab(i)
                for k, v in list(terms.items()):
                    if v is w:
                        del terms[k]
        tabs.tabCloseRequested.connect(close_tab)
    if term is None or tabs.indexOf(term) < 0:
        term = RemoteTerminal(win, s)
        terms[s.id] = term
        tabs.addTab(term, {"ssh": "SSH: ", "wsl": "", "devcontainer": ""}.get(s.kind, "") + s.label)
        term.start()
    tabs.setCurrentWidget(term)
    win._remote_term_dock.show()
    win._remote_term_dock.raise_()
    term.input.setFocus()
    return term


# ============================================================================ explorer dock
class RemoteExplorer(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        st = self.style()
        self.icon_dir = st.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self.icon_file = st.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        self.icon_host = st.standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon)
        tb = QHBoxLayout()
        tb.setContentsMargins(2, 2, 2, 2)
        tb.setSpacing(2)

        def btn(text, tip, slot):
            b = QToolButton(text=text)
            b.setToolTip(tip)
            b.setAutoRaise(True)
            b.clicked.connect(slot)
            tb.addWidget(b)
            return b
        btn("Connect", "File > Open Remote (SSH host, WSL folder, Dev Container)", self._connect_menu)
        btn("Refresh", "Reload the selected folder", self.refresh_selected)
        btn("Terminal", "Open a shell on the remote side in the Terminal dock", lambda: open_terminal(win))
        btn("Run", "Run the saved Run command on the remote side (output in Output)", lambda: run_saved(win, "run"))
        btn("Build", "Run the saved Build command on the remote side", lambda: run_saved(win, "build"))
        btn("Command...", "Run any command in the selected remote folder", lambda: run_prompt(win))
        btn("Stop", "Stop the running remote command", lambda: (current_session(win) or _Null()).stop_command())
        tb.addStretch(1)
        self.status = QLabel("Not connected. Use Connect or File > Open Remote.")
        theme.role(self.status, "muted")
        self.status.setWordWrap(True)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Remote folder - type a path and press Enter")
        self.path_edit.returnPressed.connect(self._go_path)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.tree.itemExpanded.connect(self._expanded)
        self.tree.itemCollapsed.connect(self._collapsed)
        self.tree.itemActivated.connect(self._activated)
        self.tree.currentItemChanged.connect(lambda *_: self._sync_path())
        # search
        self.q = QLineEdit()
        self.q.setPlaceholderText("Search the remote folder")
        self.q.returnPressed.connect(self.search)
        self.glob = QLineEdit()
        self.glob.setPlaceholderText("*.py, *.js")
        self.glob.setMaximumWidth(110)
        self.case = QCheckBox("Aa")
        self.case.setToolTip("Match case")
        self.regex = QCheckBox(".*")
        self.regex.setToolTip("Regular expression")
        sb = QHBoxLayout()
        sb.setContentsMargins(2, 0, 2, 0)
        for w in (self.q, self.glob, self.case, self.regex):
            sb.addWidget(w)
        go = QPushButton("Find")
        go.clicked.connect(self.search)
        sb.addWidget(go)
        self.results = QTreeWidget()
        self.results.setHeaderHidden(True)
        self.results.itemActivated.connect(self._open_hit)
        self.result_label = QLabel("")
        theme.role(self.result_label, "muted")
        bottom = QWidget()
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addLayout(sb)
        bl.addWidget(self.result_label)
        bl.addWidget(self.results, 1)
        top = QWidget()
        tl = QVBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(2)
        tl.addLayout(tb)
        tl.addWidget(self.status)
        tl.addWidget(self.path_edit)
        tl.addWidget(self.tree, 1)
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(top)
        split.addWidget(bottom)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(split)

    # ---------------------------------------------------------------- items
    def _session_item(self, s) -> QTreeWidgetItem | None:
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if (it.data(0, ROLE) or (None,))[0] == s.id:
                return it
        return None

    def add_session(self, s) -> None:
        it = QTreeWidgetItem(self.tree, [f"{s.label}   {s.fs.root}"])
        it.setIcon(0, self.icon_host)
        it.setData(0, ROLE, (s.id, s.fs.root, True))
        it.setToolTip(0, f"{s.label}:{s.fs.root}")
        QTreeWidgetItem(it, ["(loading...)"])
        self.tree.setCurrentItem(it)
        it.setExpanded(True)
        self._update_status()

    def remove_session(self, s) -> None:
        it = self._session_item(s)
        if it is not None:
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(it))
        self._update_status()

    def _update_status(self):
        n = len(sessions(self.win))
        self.status.setText(f"{n} remote connection(s). Double-click a file to edit it; right-click for more."
                            if n else "Not connected. Use Connect or File > Open Remote.")

    def selected_session(self):
        it = self.tree.currentItem()
        d = it.data(0, ROLE) if it is not None else None
        return sessions(self.win).get(d[0]) if d else None

    def current_folder(self, s) -> str:
        it = self.tree.currentItem()
        d = it.data(0, ROLE) if it is not None else None
        if not d or d[0] != s.id:
            return s.fs.root
        return d[1] if d[2] else posixpath.dirname(d[1])

    def _sync_path(self):
        s = self.selected_session()
        if s is not None:
            self.path_edit.setText(self.current_folder(s))

    def _fill(self, item: QTreeWidgetItem, s, path: str) -> None:
        def done(entries):
            if self._session_item(s) is None:
                return
            expanded = {item.child(i).data(0, ROLE)[1] for i in range(item.childCount())
                        if item.child(i).data(0, ROLE) and item.child(i).isExpanded()}
            item.takeChildren()
            for e in sorted(entries, key=lambda x: (not x.is_dir, x.name.lower())):
                c = QTreeWidgetItem(item, [e.name])
                c.setData(0, ROLE, (s.id, e.path, e.is_dir))
                c.setIcon(0, self.icon_dir if e.is_dir else self.icon_file)
                c.setToolTip(0, e.path + ("" if e.is_dir else f"  ({e.size:,} bytes)"))
                if e.is_dir:
                    QTreeWidgetItem(c, ["(loading...)"])
                    if e.path in expanded:
                        c.setExpanded(True)
            if not entries:
                ph = QTreeWidgetItem(item, ["(empty)"])
                ph.setDisabled(True)
            s.watcher.watch_dir(path)

        def failed(ex):
            item.takeChildren()
            QTreeWidgetItem(item, [f"(error: {ex})"])
        run_async(lambda: s.fs.listdir(path), done, failed)

    def _expanded(self, item):
        d = item.data(0, ROLE)
        s = sessions(self.win).get(d[0]) if d else None
        if s is not None and d[2]:
            self._fill(item, s, d[1])

    def _collapsed(self, item):
        d = item.data(0, ROLE)
        s = sessions(self.win).get(d[0]) if d else None
        if s is not None:
            s.watcher.unwatch_dir(d[1])

    def _activated(self, item, _col=0):
        d = item.data(0, ROLE)
        s = sessions(self.win).get(d[0]) if d else None
        if s is not None and not d[2]:
            s.open_file(d[1])

    def find_item(self, s, path: str) -> QTreeWidgetItem | None:
        top = self._session_item(s)
        if top is None:
            return None
        stack = [top]
        while stack:
            it = stack.pop()
            d = it.data(0, ROLE)
            if d and d[1] == path:
                return it
            stack.extend(it.child(i) for i in range(it.childCount()))
        return None

    def refresh_dir(self, s, path: str) -> None:
        it = self.find_item(s, path)
        if it is not None and it.isExpanded():
            self._fill(it, s, path)

    def refresh_selected(self):
        it = self.tree.currentItem()
        if it is None:
            return
        d = it.data(0, ROLE)
        if d and not d[2]:
            it = it.parent()
            d = it.data(0, ROLE) if it is not None else None
        s = sessions(self.win).get(d[0]) if d else None
        if s is not None:
            it.setExpanded(True)
            self._fill(it, s, d[1])

    def _go_path(self):
        s = self.selected_session() or current_session(self.win)
        if s is None:
            return
        path = norm(self.path_edit.text().strip() or s.fs.root)

        def ok(e):
            if e is None or not e.is_dir:
                tell(self.win, "Remote", f"{path} is not a folder on {s.label}")
                return
            s.fs.root = path
            top = self._session_item(s)
            top.setText(0, f"{s.label}   {path}")
            top.setData(0, ROLE, (s.id, path, True))
            self.tree.setCurrentItem(top)
            top.setExpanded(True)
            self._fill(top, s, path)
            if s.profile is not None:
                profiles.update_host(s.profile, folder=path)
        run_async(lambda: s.fs.stat(path), ok, lambda ex: tell(self.win, "Remote", str(ex), True))

    def _connect_menu(self):
        m = self.win.__dict__.get("remote_menu")
        if m is not None:
            m.exec(self.cursor().pos())

    # ---------------------------------------------------------------- context menu
    def _menu(self, pos):
        it = self.tree.itemAt(pos)
        d = it.data(0, ROLE) if it is not None else None
        s = sessions(self.win).get(d[0]) if d else None
        m = QMenu(self)
        if s is None:
            m.addAction("Connect to SSH Host...", lambda: connect_ssh_dialog(self.win))
            m.addAction("Open WSL Folder...", lambda: open_wsl_dialog(self.win))
            m.addAction("Open Folder in Dev Container...", lambda: open_devcontainer_dialog(self.win))
            m.exec(self.tree.viewport().mapToGlobal(pos))
            return
        path, is_dir = d[1], d[2]
        folder = path if is_dir else posixpath.dirname(path)
        if not is_dir:
            m.addAction("Open", lambda: s.open_file(path))
            m.addAction("Download...", lambda: download(self.win, s, path))
            m.addSeparator()
        m.addAction("New File...", lambda: self.new_item(s, folder, False))
        m.addAction("New Folder...", lambda: self.new_item(s, folder, True))
        m.addAction("Upload Files...", lambda: upload(self.win, s, folder))
        if it.parent() is not None:
            m.addAction("Rename...", lambda: self.rename(s, path))
            m.addAction("Delete", lambda: self.delete(s, path, is_dir))
        m.addSeparator()
        m.addAction("Open Terminal Here", lambda: open_terminal(self.win, s))
        m.addAction("Run Command Here...", lambda: run_prompt(self.win, s, folder))
        m.addAction("Search in Folder...", lambda: (self.path_edit.setText(folder), self.q.setFocus()))
        m.addAction("Copy Path", lambda: QApplication.clipboard().setText(path))
        m.addAction("Refresh", self.refresh_selected)
        if it.parent() is None:
            m.addSeparator()
            m.addAction("Set Run / Build Commands...", lambda: set_commands_dialog(self.win, s))
            if s.dc is not None:
                m.addAction("Stop Container", lambda: stop_container(self.win, s))
            m.addAction("Disconnect", lambda: close_session(self.win, s))
        m.exec(self.tree.viewport().mapToGlobal(pos))

    def new_item(self, s, folder: str, is_dir: bool, name: str | None = None):
        if name is None:
            name, ok = QInputDialog.getText(self.win, "New Folder" if is_dir else "New File", "Name:")
            if not ok or not name.strip():
                return
        name = name.strip()
        path = s.fs.join(folder, name)

        def work():
            if s.fs.exists(path):
                raise RemoteError(f"{path} already exists")
            if is_dir:
                s.fs.mkdir(path)
            else:
                s.fs.mkdir(posixpath.dirname(path))
                s.fs.write(path, b"")
            return path

        def done(p):
            self.refresh_dir(s, folder)
            if not is_dir:
                s.open_file(p)
        run_async(work, done, lambda ex: tell(self.win, "Remote", str(ex), True))

    def rename(self, s, path: str, new_name: str | None = None):
        if new_name is None:
            new_name, ok = QInputDialog.getText(self.win, "Rename", "New name:", text=posixpath.basename(path))
            if not ok or not new_name.strip() or new_name == posixpath.basename(path):
                return
        new = s.fs.join(posixpath.dirname(path), new_name.strip())

        def done(_r):
            v = s.views.pop(path, None)
            if v is not None:
                s.watcher.unwatch_file(path)
                v.rpath = new
                s.views[new] = v
                s.watcher.watch_file(new, s.fs.stat(new))
                v.where.setText(f"  {s.label}  :  {new}")
                v._update_title()
            self.refresh_dir(s, posixpath.dirname(path))
        run_async(lambda: s.fs.rename(path, new), done, lambda ex: tell(self.win, "Rename", str(ex), True))

    def delete(self, s, path: str, is_dir: bool):
        what = "the folder and everything in it" if is_dir else "the file"
        if ask(self.win, "delete", "Delete", f"Delete {what}\n{path}\non {s.label}? This cannot be undone.",
               ("Delete", "Cancel"), default=1) != "Delete":
            return
        run_async(lambda: s.fs.remove(path), lambda _r: self.refresh_dir(s, posixpath.dirname(path)),
                  lambda ex: tell(self.win, "Delete", str(ex), True))

    # ---------------------------------------------------------------- search
    def search(self, s=None):
        s = s if isinstance(s, RemoteSession) else (self.selected_session() or current_session(self.win))
        text = self.q.text()
        if s is None or not text:
            return
        folder = norm(self.path_edit.text().strip() or s.fs.root)
        self.results.clear()
        self.result_label.setText(f"Searching {folder} on {s.label} ...")
        t0 = time.monotonic()

        def done(hits):
            self.results.clear()
            by_file: dict[str, QTreeWidgetItem] = {}
            for h in hits:
                f = by_file.get(h.path)
                if f is None:
                    f = QTreeWidgetItem(self.results, [h.path])
                    f.setData(0, ROLE, (s.id, h.path, 0))
                    f.setIcon(0, self.icon_file)
                    by_file[h.path] = f
                c = QTreeWidgetItem(f, [f"{h.line}: {h.text}"])
                c.setData(0, ROLE, (s.id, h.path, h.line))
            self.results.expandAll()
            self.result_label.setText(f"{len(hits)} match(es) in {len(by_file)} file(s) "
                                      f"({time.monotonic() - t0:.1f} s)")
            self.last_hits = hits
        run_async(lambda: s.fs.search(text, folder, self.glob.text(), self.regex.isChecked(),
                                      self.case.isChecked()),
                  done, lambda ex: self.result_label.setText(f"Search failed: {ex}"))

    def _open_hit(self, item, _col=0):
        d = item.data(0, ROLE)
        s = sessions(self.win).get(d[0]) if d else None
        if s is not None:
            s.open_file(d[1], line=d[2] or None)


class _Null:
    def stop_command(self):
        pass


def explorer(win) -> RemoteExplorer:
    return win.remote_explorer


# ============================================================================ actions
def download(win, s: RemoteSession, rpath: str, target: str | None = None):
    if target is None:
        target, _ = QFileDialog.getSaveFileName(win, "Download", posixpath.basename(rpath))
        if not target:
            return

    def work():
        data = s.fs.read(rpath)
        Path(target).write_bytes(data)
        return len(data)
    run_async(work, lambda n: win.log(f"[remote] downloaded {rpath} -> {target} ({n:,} bytes)"),
              lambda ex: tell(win, "Download", str(ex), True))


def upload(win, s: RemoteSession, folder: str, files: list[str] | None = None):
    if files is None:
        files, _ = QFileDialog.getOpenFileNames(win, f"Upload to {s.label}:{folder}")
        if not files:
            return

    def work():
        done = []
        for f in files:
            dest = s.fs.join(folder, Path(f).name)
            s.fs.write(dest, Path(f).read_bytes())
            done.append(dest)
        return done

    def ok(done):
        win.log(f"[remote] uploaded {len(done)} file(s) to {s.label}:{folder}")
        explorer(win).refresh_dir(s, folder)
    run_async(work, ok, lambda ex: tell(win, "Upload", str(ex), True))


def run_prompt(win, s: RemoteSession | None = None, cwd: str | None = None, cmd: str | None = None):
    s = s or current_session(win)
    if s is None:
        tell(win, "Remote", "Connect to a remote host first (File > Open Remote).")
        return False
    if cmd is None:
        last = str(profiles.settings().value("remote/last_command", "") or "")
        cmd, ok = QInputDialog.getText(win, "Run Remote Command", f"Command on {s.label}:", text=last)
        if not ok or not cmd.strip():
            return False
        profiles.settings().setValue("remote/last_command", cmd)
    return s.run_command(cmd, "Command", cwd)


def run_saved(win, which: str, s: RemoteSession | None = None):
    """Run / Build with the session's saved command (asks for it the first time)."""
    s = s or current_session(win)
    if s is None:
        tell(win, "Remote", "Connect to a remote host first (File > Open Remote).")
        return False
    cmd = s.command(which)
    if not cmd:
        guess = guess_command(s, which)
        cmd, ok = QInputDialog.getText(win, f"Remote {which.title()} Command",
                                       f"{which.title()} command on {s.label} (saved for next time):", text=guess)
        if not ok or not cmd.strip():
            return False
        s.set_command(which, cmd.strip())
    return s.run_command(cmd, which.title(), s.fs.root)


def guess_command(s: RemoteSession, which: str) -> str:
    try:
        names = {e.name for e in s.fs.listdir(s.fs.root)}
    except Exception:  # noqa: BLE001
        names = set()
    if which == "build":
        for f, c in (("Makefile", "make"), ("package.json", "npm run build"), ("Cargo.toml", "cargo build"),
                     ("go.mod", "go build ./..."), ("pom.xml", "mvn -q package"), ("CMakeLists.txt",
                     "cmake -B build && cmake --build build"), ("composer.json", "composer install")):
            if f in names:
                return c
        return "make"
    for f, c in (("main.py", "python3 main.py"), ("app.py", "python3 app.py"), ("manage.py",
                 "python3 manage.py runserver"), ("package.json", "npm start"), ("Cargo.toml", "cargo run"),
                 ("go.mod", "go run ."), ("index.php", "php -S 0.0.0.0:8000"), ("main.rb", "ruby main.rb")):
        if f in names:
            return c
    return ""


def set_commands_dialog(win, s: RemoteSession):
    d = QDialog(win)
    d.setWindowTitle(f"Run / Build on {s.label}")
    run_e, build_e = QLineEdit(s.command("run") or guess_command(s, "run")), \
        QLineEdit(s.command("build") or guess_command(s, "build"))
    f = QFormLayout(d)
    f.addRow("Run command:", run_e)
    f.addRow("Build command:", build_e)
    note = QLabel(f"Both run in {s.fs.root} on the remote side; output goes to the Output window.")
    theme.role(note, "muted")
    f.addRow(note)
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    bb.accepted.connect(d.accept)
    bb.rejected.connect(d.reject)
    f.addRow(bb)
    if d.exec():
        s.set_command("run", run_e.text().strip())
        s.set_command("build", build_e.text().strip())


def stop_container(win, s: RemoteSession):
    if s.dc is None:
        return
    dc = s.dc
    close_session(win, s)
    run_async(lambda: dc.stop(), lambda out: win.log(f"[remote] container {dc.container_name} stopped"),
              lambda ex: win.log(f"[remote] {ex}"))


# ============================================================================ SSH connect
class SSHDialog(QDialog):
    def __init__(self, win, host: dict | None = None):
        super().__init__(win)
        self.setWindowTitle("Connect to SSH Host")
        self.saved = profiles.load_hosts()
        try:
            from ..remote.ssh import ssh_config_hosts
            self.config_hosts = ssh_config_hosts()
        except Exception:  # noqa: BLE001
            self.config_hosts = {}
        self.pick = QComboBox()
        self.pick.addItem("(new connection)", None)
        for h in self.saved:
            self.pick.addItem(f"{profiles.host_id(h)}  {h.get('folder') or ''}", ("saved", h))
        for alias, c in self.config_hosts.items():
            self.pick.addItem(f"{alias}  (~/.ssh/config)", ("config", {"host": c["hostname"], "user": c["user"],
                                                                       "port": c["port"], "auth": "key" if c[
                                                                           "identityfile"] else "agent",
                                                                       "key_file": c["identityfile"]}))
        self.pick.currentIndexChanged.connect(self._picked)
        self.host = QLineEdit()
        self.host.setPlaceholderText("example.com or 192.168.1.10")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(22)
        self.user = QLineEdit(os.environ.get("USERNAME", "").lower())
        self.r_pw, self.r_key, self.r_agent = QRadioButton("Password"), QRadioButton("Private key"), \
            QRadioButton("SSH agent / default keys")
        self.r_pw.setChecked(True)
        ab = QHBoxLayout()
        for r in (self.r_pw, self.r_key, self.r_agent):
            ab.addWidget(r)
            r.toggled.connect(self._auth_changed)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_file = QLineEdit()
        keys = profiles.default_key_files()
        if keys:
            self.key_file.setText(keys[0])
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        kb = QHBoxLayout()
        kb.addWidget(self.key_file, 1)
        kb.addWidget(browse)
        self.passphrase = QLineEdit()
        self.passphrase.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase.setPlaceholderText("only if the key is encrypted")
        self.remember = QCheckBox("Remember the password / passphrase in Windows Credential Manager")
        if not profiles.keyring_available():
            self.remember.setEnabled(False)
            self.remember.setText("No credential store available - the password will be asked every time")
        self.folder = QLineEdit("~")
        self.folder.setToolTip("Remote folder to open (~ = home)")
        f = QFormLayout(self)
        f.addRow("Saved:", self.pick)
        f.addRow("Host:", self.host)
        f.addRow("Port:", self.port)
        f.addRow("User:", self.user)
        f.addRow("Sign in with:", ab)
        f.addRow("Password:", self.password)
        f.addRow("Key file:", kb)
        f.addRow("Passphrase:", self.passphrase)
        f.addRow("", self.remember)
        f.addRow("Folder:", self.folder)
        note = QLabel("The server needs SFTP and a POSIX shell (Linux, macOS, BSD).")
        theme.role(note, "muted")
        f.addRow(note)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        bb.addButton("Connect", QDialogButtonBox.ButtonRole.AcceptRole).setDefault(True)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)
        if host:
            self._load(host)
        elif self.saved:
            self.pick.setCurrentIndex(1)
        self._auth_changed()

    def _browse(self):
        f, _ = QFileDialog.getOpenFileName(self, "Private key", str(Path.home() / ".ssh"))
        if f:
            self.key_file.setText(f)

    def _picked(self, i):
        d = self.pick.itemData(i)
        if d:
            self._load(d[1])

    def _load(self, h: dict):
        self.host.setText(h.get("host", ""))
        self.port.setValue(int(h.get("port") or 22))
        self.user.setText(h.get("user", ""))
        auth = h.get("auth", "password")
        {"password": self.r_pw, "key": self.r_key}.get(auth, self.r_agent).setChecked(True)
        if h.get("key_file"):
            self.key_file.setText(h["key_file"])
        self.folder.setText(h.get("folder") or "~")
        self.remember.setChecked(bool(h.get("remember")))
        self.password.setText(profiles.get_secret(h, "password") if auth == "password" else "")
        self.passphrase.setText(profiles.get_secret(h, "passphrase") if auth == "key" else "")

    def _auth_changed(self, *_):
        self.password.setEnabled(self.r_pw.isChecked())
        self.key_file.setEnabled(self.r_key.isChecked())
        self.passphrase.setEnabled(self.r_key.isChecked())

    def _accept(self):
        if not self.host.text().strip() or not self.user.text().strip():
            QMessageBox.warning(self, "Connect", "Enter the host and the user name.")
            return
        self.accept()

    def result_host(self) -> tuple[dict, str, str]:
        auth = "password" if self.r_pw.isChecked() else ("key" if self.r_key.isChecked() else "agent")
        h = {"host": self.host.text().strip(), "port": self.port.value(), "user": self.user.text().strip(),
             "auth": auth, "key_file": self.key_file.text().strip() if auth == "key" else "",
             "folder": self.folder.text().strip() or "~", "remember": self.remember.isChecked()}
        old = next((x for x in self.saved if profiles.host_id(x) == profiles.host_id(h)), {})
        for k in ("run_cmd", "build_cmd"):
            if old.get(k):
                h[k] = old[k]
        return h, self.password.text() if auth == "password" else "", self.passphrase.text() if auth == "key" \
            else ""


def connect_ssh_dialog(win, host: dict | None = None):
    d = SSHDialog(win, host)
    if d.exec():
        h, pw, pp = d.result_host()
        connect_ssh(win, h, pw, pp)


def connect_ssh(win, host: dict, password: str = "", passphrase: str = "", on_done=None, trust=None) -> None:
    """Connect in the background; asks about unknown host keys; adds the session to the Remote Explorer."""
    from ..remote.ssh import SSHFS, UnknownHostKey, fingerprint
    if host.get("auth") == "password" and not password:
        password = profiles.get_secret(host, "password")
    if host.get("auth") == "key" and not passphrase:
        passphrase = profiles.get_secret(host, "passphrase")
    fs = SSHFS(host["host"], host["user"], int(host.get("port") or 22), password=password,
               key_file=host.get("key_file", "") if host.get("auth") == "key" else "", passphrase=passphrase,
               root=host.get("folder") or "", use_agent=host.get("auth") == "agent")
    win.statusBar().showMessage(f"Connecting to {fs.label} ...")
    win.log(f"[remote] connecting to {fs.label} ...")

    def ok(_r):
        if host.get("remember"):
            if host.get("auth") == "password":
                profiles.set_secret(host, password, "password")
            elif host.get("auth") == "key":
                profiles.set_secret(host, passphrase, "passphrase")
        profiles.save_host(host)
        s = add_session(win, RemoteSession(win, fs, dict(host)))
        if on_done:
            on_done(s)

    def err(ex):
        win.statusBar().clearMessage()
        if isinstance(ex, UnknownHostKey):
            a = ask(win, "host_key", "Unknown host key",
                    f"The authenticity of {ex.hostname} can't be established.\n\n{ex.key.get_name()} key "
                    f"fingerprint:\n{fingerprint(ex.key)}\n\nTrust this host and connect?", ("Trust and Connect",
                                                                                             "Cancel"), default=1)
            if a == "Trust and Connect":
                connect_ssh(win, host, password, passphrase, on_done, trust=ex.key)
            return
        tell(win, "SSH", str(ex), True)
        if on_done:
            on_done(None)
    run_async(lambda: fs.connect(trust=trust), ok, err)


# ============================================================================ WSL
def open_wsl_dialog(win, distro: str | None = None, folder: str | None = None, on_done=None):
    from ..remote import wsl
    ds = wsl.distros()
    if not ds:
        tell(win, "WSL", wsl.status_text())
        return
    if distro is None:
        d = QDialog(win)
        d.setWindowTitle("Open WSL Folder")
        combo = QComboBox()
        for x in ds:
            combo.addItem(x["name"] + ("  (default)" if x["default"] else "") + f"  {x['state']}", x["name"])
        fold = QLineEdit("~")
        browse = QPushButton("Browse...")

        def br():
            start = f"\\\\wsl$\\{combo.currentData()}\\"
            p = QFileDialog.getExistingDirectory(d, "WSL folder", start)
            parsed = wsl.parse_unc(p) if p else None
            if parsed:
                fold.setText(parsed[1])
        browse.clicked.connect(br)
        row = QHBoxLayout()
        row.addWidget(fold, 1)
        row.addWidget(browse)
        f = QFormLayout(d)
        f.addRow("Distribution:", combo)
        f.addRow("Folder:", row)
        note = QLabel("Files are opened through \\\\wsl$; terminal, Run, Build and Search run inside the "
                      "distribution (wsl -d).")
        note.setWordWrap(True)
        theme.role(note, "muted")
        f.addRow(note)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        f.addRow(bb)
        if not d.exec():
            return
        distro, folder = combo.currentData(), fold.text().strip()

    def work():
        fs = wsl.WSLFS(distro, "" if folder in (None, "", "~") else folder)
        if not fs.is_dir(fs.root):
            raise RemoteError(f"{fs.root} is not a folder in {distro}")
        return fs

    def ok(fs):
        radproj = wsl.unc_path(distro, fs.root)
        if (radproj / "project.radproj").is_file() or any(radproj.glob("*.radsln")):
            if ask(win, "wsl_project", "WSL", f"{fs.root} holds a RAD IDE project. Open it as a project "
                   "(designer, F5 ...) instead of a remote folder?", ("Open as Project", "Remote Folder")) \
                    == "Open as Project":
                win.open_project(radproj)
                return
        s = add_session(win, RemoteSession(win, fs))
        if on_done:
            on_done(s)
    run_async(work, ok, lambda ex: tell(win, "WSL", str(ex), True))


# ============================================================================ Dev Containers
def open_devcontainer_dialog(win, folder: str | None = None, on_done=None, confirm: bool = True):
    from ..remote.devcontainer import DevContainer, DevContainerFS, docker_status, find_config
    if folder is None:
        start = str(win.project.folder) if getattr(win, "project", None) is not None else ""
        folder = QFileDialog.getExistingDirectory(win, "Folder with .devcontainer", start)
        if not folder:
            return
    if find_config(folder) is None:
        tell(win, "Dev Container", f"{folder} has no .devcontainer/devcontainer.json.\nCreate one, for example:\n"
             '{ "name": "My app", "image": "mcr.microsoft.com/devcontainers/python:3.12" }')
        return
    try:
        dc = DevContainer(folder)
    except RemoteError as e:
        tell(win, "Dev Container", str(e), True)
        return
    ok_docker, msg = docker_status()
    if not ok_docker:
        tell(win, "Dev Container", f"{msg}\n\nWithout Docker the folder can still be opened as a normal "
             "local folder; commands cannot run in the container.", True)
        return
    if confirm:
        notes = "\n".join("- " + u for u in dc.unsupported())
        if ask(win, "dc_start", "Dev Container", f"Open '{dc.name}' in a container?\nRAD IDE will run these "
               f"docker commands (container {dc.container_name}):" + (f"\n\nNotes:\n{notes}" if notes else ""),
               ("Start", "Cancel"), detail="\n\n".join(dc.plan())) != "Start":
            return
    try:
        win.dock_output.show()
        win.dock_output.raise_()
    except AttributeError:
        pass
    tr = _TextRelay(win)
    buf = {"s": ""}

    def on_text(t):
        buf["s"] += t
        *lines, buf["s"] = buf["s"].split("\n")
        for ln in lines:
            win.log("[devcontainer] " + ln.rstrip("\r"))
    tr.text.connect(on_text)
    win.log(f"[devcontainer] starting {dc.name} ...")
    win.statusBar().showMessage(f"Starting dev container {dc.name} ...")

    def ok(_name):
        win.__dict__.setdefault("_remote_started_containers", set()).add(dc.container_name)
        s = add_session(win, RemoteSession(win, DevContainerFS(dc), dc=dc))
        if on_done:
            on_done(s)

    def err(ex):
        tell(win, "Dev Container", str(ex), True)
        if on_done:
            on_done(None)
    run_async(lambda: dc.up(tr.text.emit), ok, err)


# ============================================================================ menus / install
def _update_actions(win):
    has = bool(sessions(win))
    for a in win.__dict__.get("_remote_session_actions", []):
        a.setEnabled(has)


def _fill_recent(win, m: QMenu):
    m.clear()
    hosts = profiles.load_hosts()
    if not hosts:
        a = m.addAction("(no saved hosts)")
        a.setEnabled(False)
        return
    for h in hosts[:12]:
        m.addAction(f"{profiles.host_id(h)}   {h.get('folder') or ''}",
                    lambda h=h: connect_ssh(win, h) if (h.get("auth") != "password" or profiles.get_secret(h))
                    else connect_ssh_dialog(win, h))
    m.addSeparator()
    fm = m.addMenu("Forget")
    for h in hosts[:12]:
        fm.addAction(profiles.host_id(h), lambda h=h: profiles.forget_host(h))


def _disconnect_current(win):
    s = current_session(win)
    if s is not None:
        close_session(win, s)


def _reload_current(win):
    w = win.tabs.currentWidget()
    if isinstance(w, RemoteFileView):
        w.reload()


class RemoteDocuments:
    """DocumentProvider (radide/extension_points.py): Save All also saves the modified remote files. Remote
    files open from the Remote Explorer, and closing the IDE asks about them in its own question (the remote
    closeEvent below), so they do not count for the IDE's closing question."""

    def __init__(self, win):
        self.win = win

    def can_open(self, path) -> bool:
        return False

    def open_document(self, path):
        return None

    def save_documents(self) -> None:
        for s in list(sessions(self.win).values()):
            for v in list(s.views.values()):
                if v.editor.isModified():
                    v.save()

    def has_modified_documents(self) -> bool:
        return False


def install(win) -> None:
    win.remote_explorer = RemoteExplorer(win)
    d = QDockWidget("Remote Explorer", win)
    d.setObjectName("RemoteExplorer")
    d.setWidget(win.remote_explorer)
    win.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, d)
    sol = getattr(win, "dock_solution", None)
    if sol is not None:
        win.tabifyDockWidget(sol, d)
        sol.raise_()
    d.hide()
    win.dock_remote = d

    m = QMenu("Open &Remote", win)
    win.remote_menu = m
    a_ssh = m.addAction("Connect to &SSH Host...", lambda: connect_ssh_dialog(win))
    recent = m.addMenu("Recent SSH &Hosts")
    recent.aboutToShow.connect(lambda: _fill_recent(win, recent))
    m.addAction("Open &WSL Folder...", lambda: open_wsl_dialog(win))
    m.addAction("Open Folder in &Dev Container...", lambda: open_devcontainer_dialog(win))
    m.addSeparator()
    m.addAction("Remote &Explorer", lambda: (d.show(), d.raise_()))
    acts = [m.addAction("Remote &Terminal", lambda: open_terminal(win)),
            m.addAction("&Run on Remote", lambda: run_saved(win, "run")),
            m.addAction("&Build on Remote", lambda: run_saved(win, "build")),
            m.addAction("Run Remote &Command...", lambda: run_prompt(win)),
            m.addAction("Sto&p Remote Command", lambda: (current_session(win) or _Null()).stop_command()),
            m.addAction("Reload Remote File", lambda: _reload_current(win)),
            m.addAction("&Disconnect", lambda: _disconnect_current(win))]
    win._remote_session_actions = acts
    a_ssh.setToolTip("Edit files, run commands and open a shell on an SSH server")
    fm = getattr(win, "file_menu", None)
    if fm is not None:
        before = None
        opened = getattr(win, "a_open_file", None)
        actions = fm.actions()
        if opened in actions and actions.index(opened) + 1 < len(actions):
            before = actions[actions.index(opened) + 1]
        if before is not None:
            fm.insertMenu(before, m)
        else:
            fm.addMenu(m)
    view = next((x.menu() for x in win.menuBar().actions() if x.text().replace("&", "") == "View"), None)
    if view is not None:
        va = QAction("Remote E&xplorer", win)
        va.triggered.connect(lambda: (d.show(), d.raise_()))
        view.addAction(va)
    _update_actions(win)
    try:
        from . import workbench
        workbench.register_view("remote", "Remote Explorer", icon="globe", factory=lambda w: w.dock_remote,
                                modes=("vscode",), area="side", order=85,
                                tooltip="Remote Explorer (SSH, WSL, Dev Containers)")
    except Exception as e:  # noqa: BLE001
        win.log(f"[remote] workbench view: {e}")

    win.extension_points.add_document_provider(RemoteDocuments(win))       # Save All (radide/extension_points.py)

    orig_close = win.closeEvent

    def close_event(e):
        mods = [v for s in sessions(win).values() for v in s.views.values() if v.editor.isModified()]
        if mods:
            a = ask(win, "close_ide", "Remote", f"Save changes to {len(mods)} remote file(s)?",
                    ("Save", "Discard", "Cancel"))
            if a == "Cancel" or (a == "Save" and not all(v.save() for v in mods)):
                e.ignore()
                return
            for v in mods:
                v.editor.setModified(False)
        orig_close(e)
        if e.isAccepted():
            shutdown(win)
    win.closeEvent = close_event


def shutdown(win) -> None:
    """Close every connection; stop the dev containers this IDE started (docker stop, not removed)."""
    for t in list(win.__dict__.get("_remote_terms", {}).values()):
        t.close_shell()
    for s in list(sessions(win).values()):
        dc = s.dc
        s.close()
        if dc is not None and dc.container_name in win.__dict__.get("_remote_started_containers", set()):
            try:
                dc.stop()
            except Exception:  # noqa: BLE001
                pass
    sessions(win).clear()


__all__ = ["RemoteSession", "RemoteFileView", "RemoteTerminal", "RemoteExplorer", "connect_ssh",
           "connect_ssh_dialog", "open_wsl_dialog", "open_devcontainer_dialog", "open_terminal", "run_saved",
           "run_prompt", "close_session", "sessions", "current_session", "wait_idle", "shutdown"]
