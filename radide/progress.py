"""Progress for every operation that is expected to take time (the IDE's standing rule).

One shared, non-blocking API.  The work runs off the GUI thread; the GUI shows a progress indicator
only when the work is still running after ``DELAY_MS`` (no flicker for quick tasks).

    from radide import progress

    # background task -> the status bar of the main window (VS-style, several tasks at once)
    progress.run_task(work, title="Installing Prettier", parent=win, on_done=done, on_error=failed)

    # user-initiated blocking task -> a modal dialog; returns the result (or raises / progress.Cancelled)
    result = progress.run_blocking(win, "Creating ASP.NET Core project", work, cancellable=True)

    def work(p: progress.Reporter):           # runs in a worker thread
        p.set_total(3)                         # determinate (0 = busy / indeterminate)
        p.step("dotnet new mvc")               # step N/M + status line
        p.update(bytes_done, bytes_total, text="Downloading node.zip")
        p.log("a line of tool output")         # parsed for "42%" when no total is known
        if p.cancelled: return                 # or p.check() -> raises Cancelled

    # an existing QProcess (QProcess is already asynchronous): only the indicator
    task = progress.track_process(proc, "npm install", parent=win)
    task.reporter.log(line)                    # feed the lines the caller already reads

Helpers: ``download(url, dest, reporter)`` (bytes / Content-Length), ``run_command(cmd, reporter)``
(subprocess with its output lines fed to the reporter, cancellable), ``percent_in(line)``.

Presentation:
* ``mode="dialog"`` - ProgressDialog: title, status line, bar, elapsed time, optional log, Cancel.
* ``mode="status"`` - StatusProgress, installed into the main window's status bar (``install_status_progress``):
  the newest task's bar + "N tasks"; a click lists every running task with its own Cancel.
Every update crosses threads through Qt signals and is coalesced (at most one repaint per event-loop pass),
so a worker can report every chunk of a download.  Widgets carry accessibleName / accessibleDescription.
"""
from __future__ import annotations

import re
import subprocess
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QElapsedTimer, QEventLoop, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QPlainTextEdit,
                             QProgressBar, QPushButton, QToolButton, QVBoxLayout, QWidget)

DELAY_MS = 400            # tasks that finish sooner never show anything
_PERCENT = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d+)?)\s?%")
_N_OF_M = re.compile(r"\b(\d+)\s*/\s*(\d+)\b")


class Cancelled(Exception):
    """Raised by Reporter.check() / run_blocking() when the user cancelled the task."""


def _t(text: str) -> str:
    """The IDE's UI translation (Arabic ...) for texts the automatic setter patch does not cover."""
    try:
        from .i18n import tr
        return tr(text)
    except Exception:   # noqa: BLE001 - never fail a progress update over a translation
        return text


def percent_in(line: str) -> int | None:
    """The last 'NN%' of a tool's output line (git, pip, npm, ollama, dotnet, curl ...), else None."""
    found = _PERCENT.findall(line or "")
    if not found:
        return None
    v = float(found[-1])
    return int(v) if 0 <= v <= 100 else None


def fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def fmt_elapsed(ms: int) -> str:
    s = int(ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


# ===================================================================== reporter (worker side)
class Reporter:
    """Thread-safe handle the work function uses to report progress.  All methods may be called from any thread."""

    def __init__(self, task: "Task"):
        self._task = task
        self._lock = threading.Lock()
        self.value = 0
        self.total = 0          # 0 = indeterminate
        self.text = ""
        self.parse_percent = True
        self._cancel = threading.Event()

    # --- state
    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def check(self):
        """Raise Cancelled when the user pressed Cancel (call it between steps)."""
        if self._cancel.is_set():
            raise Cancelled()

    def set_total(self, total: int, text: str | None = None):
        self.update(0, total, text)

    def update(self, value: int | None = None, total: int | None = None, text: str | None = None):
        with self._lock:
            if total is not None:
                self.total = max(0, int(total))
            if value is not None:
                self.value = max(0, int(value))
            if text is not None:
                self.text = str(text)
        self._task._dirty()

    def step(self, text: str | None = None, n: int = 1):
        """Advance one step of a known total (step N/M) and show text."""
        with self._lock:
            self.value += n
            if text is not None:
                self.text = str(text)
        self._task._dirty()

    def set_text(self, text: str):
        self.update(text=text)

    def log(self, line: str):
        """A line of output: shown in the dialog's log; 'NN%' becomes the progress when no total was set."""
        line = str(line).rstrip("\r\n")
        if self.parse_percent and self.total in (0, 100):
            pct = percent_in(line)
            if pct is not None:
                with self._lock:
                    self.total, self.value = 100, pct
        if line.strip():
            with self._lock:
                self.text = line.strip()[:200]
        self._task._line(line)
        self._task._dirty()

    __call__ = log           # a Reporter can be passed where a log(str) callback is expected

    def bytes(self, done: int, total: int, name: str = ""):
        """Download progress: 'name  3.2 MB / 10.0 MB'."""
        label = f"{name}  " if name else ""
        label += f"{fmt_bytes(done)} / {fmt_bytes(total)}" if total else fmt_bytes(done)
        self.update(done, total or 0, label)

    def snapshot(self) -> tuple[int, int, str]:
        with self._lock:
            return self.value, self.total, self.text


# ===================================================================== task (GUI side)
class Task(QObject):
    """One unit of work with its progress state.  Lives in the GUI thread; signals are emitted there."""
    changed = pyqtSignal()                 # progress / text changed (coalesced)
    line = pyqtSignal(str)                 # a log line
    finished = pyqtSignal(object, object)  # result, error (error is Cancelled() when cancelled)
    _wake = pyqtSignal()                   # worker -> GUI (queued)
    _line_sig = pyqtSignal(str)
    _done_sig = pyqtSignal(object, object)

    def __init__(self, title: str, cancellable: bool = False, parent=None, on_cancel=None):
        super().__init__(parent)
        self.title = title
        self.cancellable = cancellable or on_cancel is not None
        self.on_cancel = on_cancel
        self.reporter = Reporter(self)
        self.done = False
        self.result = None
        self.error = None
        self.shown = False                 # a UI was actually shown (after DELAY_MS)
        self._pending = False
        self._plock = threading.Lock()
        self.clock = QElapsedTimer()
        self.clock.start()
        self._wake.connect(self._flush, Qt.ConnectionType.QueuedConnection)
        self.lines: list[str] = []         # the log so far (a dialog shown after DELAY_MS starts with it)
        self.line.connect(self._keep)
        self._line_sig.connect(self.line, Qt.ConnectionType.QueuedConnection)
        self._done_sig.connect(self._finish, Qt.ConnectionType.QueuedConnection)

    # --- worker side (any thread)
    def _dirty(self):
        with self._plock:
            if self._pending:
                return
            self._pending = True
        self._wake.emit()

    def _line(self, text: str):
        self._line_sig.emit(text)

    def _flush(self):
        with self._plock:
            self._pending = False
        self.changed.emit()

    # --- GUI side
    def _keep(self, text: str):
        self.lines.append(text)
        if len(self.lines) > 5000:
            del self.lines[:1000]

    def elapsed_ms(self) -> int:
        return int(self.clock.elapsed())

    def cancel(self):
        if self.done or not self.cancellable:
            return
        self.reporter._cancel.set()
        self.reporter.set_text(_t("Cancelling..."))
        if self.on_cancel is not None:
            try:
                self.on_cancel()
            except Exception:   # noqa: BLE001 - cancelling must never raise into the GUI
                pass

    def complete(self, result=None, error=None):
        """Finish the task (GUI thread or worker thread)."""
        if threading.current_thread() is threading.main_thread():
            self._finish(result, error)
        else:
            self._done_sig.emit(result, error)

    def _finish(self, result, error):
        if self.done:
            return
        self.done = True
        if error is None and self.reporter.cancelled:
            error = Cancelled()
        self.result, self.error = result, error
        self.finished.emit(result, error)


# ===================================================================== dialog presentation
class ProgressDialog(QDialog):
    """Modal-ish progress window: title, status line, bar, elapsed time, optional log and Cancel."""

    def __init__(self, task: Task, parent=None, show_log: bool = False):
        super().__init__(parent)
        self.task = task
        self.setObjectName("ProgressDialog")
        self.setWindowTitle(_t(task.title))
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        self.head = QLabel(_t(task.title))
        f = self.head.font()
        f.setBold(True)
        self.head.setFont(f)
        self.head.setWordWrap(True)
        lay.addWidget(self.head)
        self.status = QLabel(_t("Please wait..."))
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status.setAccessibleName(_t("Progress status"))
        lay.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(True)
        self.bar.setAccessibleName(_t(task.title))
        lay.addWidget(self.bar)
        row = QHBoxLayout()
        self.elapsed = QLabel("0:00")
        self.elapsed.setAccessibleName(_t("Elapsed time"))
        row.addWidget(self.elapsed)
        row.addStretch(1)
        self.b_details = QPushButton("Details")
        self.b_details.setCheckable(True)
        self.b_details.setAccessibleName(_t("Show output"))
        row.addWidget(self.b_details)
        self.b_cancel = QPushButton("Cancel")
        self.b_cancel.setAccessibleName(_t("Cancel") + " " + _t(task.title))
        self.b_cancel.setVisible(task.cancellable)
        self.b_cancel.clicked.connect(self._cancel)
        row.addWidget(self.b_cancel)
        lay.addLayout(row)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setAccessibleName(_t("Output"))
        self.log.setMinimumHeight(180)
        self.log.setVisible(show_log)
        self.b_details.setChecked(show_log)
        self.b_details.toggled.connect(self._details)
        lay.addWidget(self.log, 1)
        if task.lines:
            self.log.setPlainText("\n".join(task.lines))
        task.changed.connect(self.refresh)
        task.line.connect(self._append)
        self._tick = QTimer(self, interval=500)
        self._tick.timeout.connect(self._update_elapsed)
        self._tick.start()
        self.refresh()

    def _details(self, on: bool):
        self.log.setVisible(on)
        self.adjustSize()

    def _append(self, text: str):
        self.log.appendPlainText(text)

    def _cancel(self):
        self.b_cancel.setEnabled(False)
        self.task.cancel()

    def _update_elapsed(self):
        self.elapsed.setText(fmt_elapsed(self.task.elapsed_ms()))

    def refresh(self):
        value, total, text = self.task.reporter.snapshot()
        _apply(self.bar, value, total)
        if text:
            self.status.setText(text)
        title = _t(self.task.title)
        desc = f"{title}: {text}" if text else title
        if total:
            desc += f" ({_percent(value, total)}%)"
        self.bar.setAccessibleDescription(desc)
        self._update_elapsed()

    def reject(self):                       # Esc = Cancel (never closes a task that cannot be cancelled)
        if self.task.cancellable and not self.task.done:
            self._cancel()

    def closeEvent(self, e):
        if not self.task.done:
            e.ignore()
            self.reject()
        else:
            super().closeEvent(e)


def _percent(value: int, total: int) -> int:
    return int(min(100, max(0, value * 100 // total))) if total else 0


def _apply(bar: QProgressBar, value: int, total: int):
    if total <= 0:
        if bar.maximum() != 0:
            bar.setRange(0, 0)
        return
    if total > 2_000_000_000:               # QProgressBar is int32: scale bytes
        value, total = value // 1024, total // 1024
    if bar.maximum() != total:
        bar.setRange(0, total)
    bar.setValue(min(value, total))


# ===================================================================== status-bar presentation
class StatusProgress(QWidget):
    """Status-bar widget (bottom of the main window): the newest task's bar + name, '+N' when more run;
    a click shows every running task with its own bar, status and Cancel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusProgress")
        self.tasks: list[Task] = []
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(6)
        self.label = QToolButton()
        self.label.setAutoRaise(True)
        self.label.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.label.setAccessibleName(_t("Background tasks"))
        self.label.clicked.connect(self.toggle_popup)
        lay.addWidget(self.label)
        self.bar = QProgressBar()
        self.bar.setFixedWidth(140)
        self.bar.setMaximumHeight(14)
        self.bar.setTextVisible(False)
        self.bar.setAccessibleName(_t("Background task progress"))
        lay.addWidget(self.bar)
        self.popup: QFrame | None = None
        self._rows: dict[int, tuple] = {}
        self._tick = QTimer(self, interval=1000)
        self._tick.timeout.connect(self.refresh)
        self.hide()

    def add(self, task: Task):
        self.tasks.append(task)
        task.changed.connect(self.refresh)
        task.finished.connect(lambda *_a, t=task: self.remove(t))
        self._tick.start()
        self.refresh()

    def remove(self, task: Task):
        if task in self.tasks:
            self.tasks.remove(task)
        self._rows.pop(id(task), None)
        if not self.tasks:
            self._tick.stop()
        self.refresh()

    def refresh(self):
        if not self.tasks:
            self.hide()
            if self.popup is not None:
                self.popup.hide()
            return
        t = self.tasks[-1]
        value, total, text = t.reporter.snapshot()
        _apply(self.bar, value, total)
        more = f"  (+{len(self.tasks) - 1})" if len(self.tasks) > 1 else ""
        pct = f" {_percent(value, total)}%" if total else ""
        self.label.setText(f"{t.title}{pct}{more}")
        tip = "\n".join(f"{x.title}: {x.reporter.snapshot()[2] or '...'}  [{fmt_elapsed(x.elapsed_ms())}]"
                        for x in self.tasks)
        self.label.setToolTip(tip + "\n\nClick to see every running task")
        self.bar.setAccessibleDescription(tip)
        self.label.setAccessibleDescription(tip)
        self.show()
        if self.popup is not None and self.popup.isVisible():
            self._fill_popup()

    # --- the task list
    def toggle_popup(self):
        if self.popup is not None and self.popup.isVisible():
            self.popup.hide()
            return
        if self.popup is None:
            self.popup = QFrame(self.window(), Qt.WindowType.Popup)
            self.popup.setObjectName("StatusProgressPopup")
            self.popup.setFrameShape(QFrame.Shape.StyledPanel)
            self.popup.setAccessibleName(_t("Running tasks"))
            QVBoxLayout(self.popup)
        self._rows.clear()
        self._fill_popup()
        self.popup.adjustSize()
        pos = self.mapToGlobal(self.rect().topLeft())
        self.popup.move(pos.x(), pos.y() - self.popup.sizeHint().height() - 4)
        self.popup.show()

    def _fill_popup(self):
        lay = self.popup.layout()
        alive = {id(t) for t in self.tasks}
        if set(self._rows) != alive:
            while lay.count():
                w = lay.takeAt(0).widget()
                if w is not None:
                    w.deleteLater()
            self._rows.clear()
            for t in self.tasks:
                box = QWidget()
                bl = QVBoxLayout(box)
                bl.setContentsMargins(6, 4, 6, 4)
                head = QHBoxLayout()
                name = QLabel(f"<b>{_t(t.title)}</b>")
                head.addWidget(name, 1)
                el = QLabel("")
                head.addWidget(el)
                if t.cancellable:
                    b = QPushButton("Cancel")
                    b.setAccessibleName(_t("Cancel") + " " + _t(t.title))
                    b.clicked.connect(t.cancel)
                    head.addWidget(b)
                bl.addLayout(head)
                bar = QProgressBar()
                bar.setMinimumWidth(320)
                bar.setAccessibleName(_t(t.title))
                bl.addWidget(bar)
                st = QLabel("")
                st.setWordWrap(True)
                bl.addWidget(st)
                lay.addWidget(box)
                self._rows[id(t)] = (t, bar, st, el)
        for t, bar, st, el in self._rows.values():
            value, total, text = t.reporter.snapshot()
            _apply(bar, value, total)
            st.setText(text or "...")
            el.setText(fmt_elapsed(t.elapsed_ms()))
        self.popup.adjustSize()


def install_status_progress(win: QMainWindow) -> StatusProgress:
    """Put the background-task indicator into win's status bar (idempotent)."""
    sp = getattr(win, "status_progress", None)
    if isinstance(sp, StatusProgress):
        return sp
    sp = StatusProgress(win)
    win.statusBar().addPermanentWidget(sp)
    win.status_progress = sp
    return sp


def _main_window(parent=None) -> QMainWindow | None:
    w = parent.window() if isinstance(parent, QWidget) else None
    if isinstance(w, QMainWindow) and isinstance(getattr(w, "status_progress", None), StatusProgress):
        return w
    app = QApplication.instance()
    if app is None:
        return None
    act = app.activeWindow()
    cands = ([act.window()] if act is not None else []) + list(app.topLevelWidgets())
    for c in cands:
        if isinstance(c, QMainWindow) and isinstance(getattr(c, "status_progress", None), StatusProgress):
            return c
    return None


# ===================================================================== presenting a task
_live: set[Task] = set()          # keeps running tasks (and their threads' QObjects) alive


def present(task: Task, parent=None, mode: str = "status", show_log: bool = False, delay_ms: int = DELAY_MS):
    """Show task's progress after delay_ms if it is still running.  mode: 'status' or 'dialog'."""
    _live.add(task)
    task.finished.connect(lambda *_a: _live.discard(task))

    def show():
        if task.done:
            return
        task.shown = True
        if mode == "dialog":
            dlg = ProgressDialog(task, parent if isinstance(parent, QWidget) else None, show_log=show_log)
            dlg.setWindowModality(Qt.WindowModality.ApplicationModal if parent is None
                                  else Qt.WindowModality.WindowModal)
            task.dialog = dlg
            task.finished.connect(lambda *_a: (dlg.hide(), dlg.deleteLater()))
            dlg.show()
        else:
            win = _main_window(parent)
            if win is not None:
                win.status_progress.add(task)
            elif isinstance(parent, QWidget):           # no IDE window (a standalone dialog): small dialog
                dlg = ProgressDialog(task, parent, show_log=show_log)
                dlg.setWindowModality(Qt.WindowModality.NonModal)
                task.dialog = dlg
                task.finished.connect(lambda *_a: (dlg.hide(), dlg.deleteLater()))
                dlg.show()
    if delay_ms <= 0:
        show()
    else:
        QTimer.singleShot(delay_ms, show)
    return task


def run_task(fn, title: str, parent=None, *, mode: str = "status", cancellable: bool = False, on_done=None,
             on_error=None, on_finished=None, total: int = 0, show_log: bool = False, delay_ms: int = DELAY_MS,
             pass_reporter: bool = True) -> Task:
    """Run fn(reporter) (or fn() with pass_reporter=False) in a worker thread; non-blocking.

    on_done(result) / on_error(exception) / on_finished(result, error) are called in the GUI thread.
    A cancelled task calls on_error(Cancelled()) (or nothing when only on_done is given)."""
    task = Task(title, cancellable)
    if total:
        task.reporter.total = total

    def finished(result, error):
        if on_finished is not None:
            on_finished(result, error)
        if error is None:
            if on_done is not None:
                on_done(result)
        elif on_error is not None:
            on_error(error)
        elif not isinstance(error, Cancelled) and on_finished is None:
            import traceback
            traceback.print_exception(type(error), error, error.__traceback__)
    task.finished.connect(finished)

    def work():
        try:
            res = fn(task.reporter) if pass_reporter else fn()
        except BaseException as e:   # noqa: BLE001 - reported in the GUI thread
            task.complete(None, e)
        else:
            task.complete(res, None)
    present(task, parent, mode, show_log, delay_ms)
    th = threading.Thread(target=work, daemon=True, name=f"task:{title[:40]}")
    task.thread = th
    th.start()
    return task


def run_blocking(parent, title: str, fn, *, cancellable: bool = False, total: int = 0, show_log: bool = False,
                 delay_ms: int = DELAY_MS, pass_reporter: bool = True, mode: str = "dialog"):
    """For code that needs the result now: run fn(reporter) in a worker thread, keep the GUI responsive
    (nested event loop, user input blocked by the modal progress dialog), return the result or raise its
    error (Cancelled when the user cancelled)."""
    loop = QEventLoop()
    task = run_task(fn, title, parent, mode=mode, cancellable=cancellable, total=total, show_log=show_log,
                    delay_ms=delay_ms, pass_reporter=pass_reporter, on_finished=lambda *_a: loop.quit())
    if not task.done:
        app = QApplication.instance()
        cursor = app is not None and delay_ms > 0
        if cursor:
            QApplication.setOverrideCursor(Qt.CursorShape.BusyCursor)
        try:
            loop.exec()
        finally:
            if cursor:
                QApplication.restoreOverrideCursor()
    if task.error is not None:
        raise task.error
    return task.result


def track_process(proc, title: str, parent=None, *, cancellable: bool = True, total: int = 0,
                  delay_ms: int = DELAY_MS, mode: str = "status") -> Task:
    """Progress for an already asynchronous QProcess.  The caller keeps reading its output and may feed
    lines to task.reporter.log(line) (NN% is parsed) or call task.reporter.step(...).  Cancel kills it."""
    task = Task(title, cancellable, on_cancel=(proc.kill if cancellable else None))
    if total:
        task.reporter.total = total
    proc.finished.connect(lambda *_a: task.complete(proc.exitCode(), None))
    proc.errorOccurred.connect(lambda e: task.complete(None, RuntimeError(proc.errorString()))
                               if e == proc.ProcessError.FailedToStart else None)
    present(task, parent, mode, False, delay_ms)
    return task


def track(title: str, parent=None, *, cancellable: bool = False, total: int = 0, delay_ms: int = DELAY_MS,
          mode: str = "status", on_cancel=None) -> Task:
    """A progress indicator for asynchronous work the caller drives itself (threads, QProcess chains,
    network callbacks): call task.reporter.* while it runs and task.complete() when it ends."""
    task = Task(title, cancellable, on_cancel=on_cancel)
    if total:
        task.reporter.total = total
    present(task, parent, mode, False, delay_ms)
    return task


# ===================================================================== worker helpers
def download(url: str, dest, reporter: Reporter | None = None, timeout: float = 60, headers: dict | None = None,
             chunk: int = 1 << 16) -> Path:
    """Download url to dest with byte progress (Content-Length) and Cancel (removes the partial file)."""
    import urllib.request
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "RADIDE", **(headers or {})})
    part = dest.with_name(dest.name + ".part")
    name = dest.name
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r, open(part, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            last = 0.0
            while True:
                if reporter is not None and reporter.cancelled:
                    raise Cancelled()
                b = r.read(chunk)
                if not b:
                    break
                f.write(b)
                done += len(b)
                now = time.monotonic()
                if reporter is not None and (now - last > 0.1 or done == total):
                    last = now
                    reporter.bytes(done, total, name)
        part.replace(dest)
    except BaseException:
        try:
            part.unlink()
        except OSError:
            pass
        raise
    return dest


def run_command(cmd, reporter: Reporter | None = None, *, cwd=None, env=None, timeout: float | None = None,
                shell: bool = False, creationflags: int | None = None) -> subprocess.CompletedProcess:
    """subprocess.run replacement for worker threads: stdout+stderr lines go to reporter.log (NN% parsed),
    Cancel terminates the process.  Returns CompletedProcess(stdout=all output, stderr='')."""
    import os
    if creationflags is None:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    p = subprocess.Popen(cmd, cwd=cwd, env=env, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                         creationflags=creationflags)
    out: list[str] = []
    start = time.monotonic()

    def watchdog():
        while p.poll() is None:
            if (reporter is not None and reporter.cancelled) or (timeout and time.monotonic() - start > timeout):
                try:
                    p.kill()
                except OSError:
                    pass
                return
            time.sleep(0.1)
    threading.Thread(target=watchdog, daemon=True).start()
    for line in p.stdout:
        out.append(line)
        if reporter is not None:
            reporter.log(line)
    p.wait()
    if reporter is not None and reporter.cancelled:
        raise Cancelled()
    if timeout and time.monotonic() - start > timeout and p.returncode != 0:
        raise subprocess.TimeoutExpired(cmd, timeout, "".join(out))
    return subprocess.CompletedProcess(cmd, p.returncode, "".join(out), "")


def n_of_m(line: str) -> tuple[int, int] | None:
    """'(3/10)' / 'Step 3/10' in a tool's output -> (3, 10)."""
    m = _N_OF_M.search(line or "")
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if 0 < b and a <= b:
            return a, b
    return None
