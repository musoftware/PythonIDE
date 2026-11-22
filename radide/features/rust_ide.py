"""First-class Rust in the IDE (with radide/lsp.py + rust-analyzer, radide/foreign/cargo_project.py and
radide/languages/rust_cargo.py).

* Error List: rust-analyzer diagnostics (cargo check / clippy on save, live rustc errors) of every file of
  the workspace - also files that are not open - with "[clippy::lint]" / "[rustc E0308]" tags;
* inlay hints (types, parameter names, chained types) in Monaco, refreshed when the analyzer is ready;
* "Rust" tool bar: the run target combo (bins, examples, tests, benches - Ctrl+F5 / F5 run the chosen one)
  and a reload button (Cargo.toml changed);
* Tools > Rust Settings...: rust-analyzer status / install (rustup component add rust-analyzer rust-src),
  check on save with clippy or check, inlay hints, format on save with rustfmt;
* status bar: rust-analyzer progress (indexing, building proc macros, cargo check ...).
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
                             QPushButton, QToolBar, QVBoxLayout)

from .. import rust_tools as rt

DIAG_SEVERITY = {"error": "Error", "warning": "Warning"}


# ============================================================================ helpers
def cargo_adapter(project):
    """The CargoAdapter of a Cargo project (in place) or a Rust (Cargo) RAD project, else None."""
    if project is None:
        return None
    a = getattr(project, "adapter", None)
    if a is not None and getattr(a, "kind", "") == "cargo":
        return a
    if getattr(project, "language", "") == "rust-cargo":
        try:
            from ..languages.rust_cargo import _adapter
            return _adapter(Path(project.folder))
        except Exception:  # noqa: BLE001
            return None
    return None


def is_rust_project(project) -> bool:
    return cargo_adapter(project) is not None


def _rel_for(win, path: str) -> str:
    p = Path(path)
    if win.project is not None:
        try:
            return p.resolve().relative_to(Path(win.project.folder).resolve()).as_posix()
        except ValueError:
            pass
    return str(p)


# ============================================================================ diagnostics -> Error List
def _diag_rows(win) -> list:
    from ..tools import Diag
    out = []
    for path, diags in sorted(getattr(win, "rust_diags", {}).items()):
        f = _rel_for(win, path)
        for d in diags:
            sev = DIAG_SEVERITY.get(d.get("severity"))
            if sev is None:
                continue
            msg = (d.get("message") or "").splitlines()[0] if d.get("message") else ""
            tag = " ".join(str(x) for x in (d.get("source"), d.get("code")) if x)
            out.append(Diag(sev, f"{msg}  [{tag}]" if tag else msg, f, int(d.get("line", 0)) + 1))
    return out


def lsp_diag_provider(win) -> list:
    """tools.run_checks hook: the language-server diagnostics join the plugin checks."""
    rows = _diag_rows(win)
    win._rust_err_keys = {(d.severity, d.message, d.file, d.line) for d in rows}
    return rows


def render_errors(win) -> None:
    """Replace the rust-analyzer rows of the Error List (keeps the other rows), update the title."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QTreeWidgetItem
    el = getattr(win, "error_list", None)
    if el is None:
        return
    old = getattr(win, "_rust_err_keys", set())
    for i in reversed(range(el.topLevelItemCount())):
        it = el.topLevelItem(i)
        key = (it.text(0), it.text(1), it.text(2), int(it.text(3) or 0) if it.text(3).isdigit() else 0)
        if key in old:
            el.takeTopLevelItem(i)
    rows = _diag_rows(win)
    for d in rows:
        it = QTreeWidgetItem([d.severity, d.message, d.file, str(d.line)])
        colour = {"Error": Qt.GlobalColor.darkRed, "Warning": Qt.GlobalColor.darkYellow}.get(d.severity)
        if colour is not None:
            it.setForeground(0, colour)
        el.addTopLevelItem(it)
    win._rust_err_keys = {(d.severity, d.message, d.file, d.line) for d in rows}
    errors = sum(el.topLevelItem(i).text(0) == "Error" for i in range(el.topLevelItemCount()))
    warnings = sum(el.topLevelItem(i).text(0) == "Warning" for i in range(el.topLevelItemCount()))
    try:
        win.dock_errors.setWindowTitle(f"Error List ({errors} errors, {warnings} warnings)")
    except Exception:  # noqa: BLE001
        pass


def _on_error_dclick(win, item) -> None:
    """Nested paths (src/lib.rs) of Rust (Cargo) RAD projects: tools._goto only knows top-level files."""
    if win.project is None or callable(getattr(win.sln, "editor_for_file", None)):
        return
    f = item.text(2)
    if not f or Path(f).is_absolute() or "/" not in f:
        return
    p = Path(win.project.folder) / f
    if p.is_file() and callable(getattr(win, "open_file", None)):
        try:
            win.open_file(p, int(item.text(3) or 1))
        except Exception:  # noqa: BLE001
            pass


# ============================================================================ language server events
class _Hub(QObject):
    refresh = pyqtSignal()


def _rust_editors(win, client=None) -> list:
    out = []
    for ed in list(getattr(win, "_lsp_editors", {}).values()):
        try:
            if ed.language_id() == "rust" and (client is None or ed.lsp is client):
                out.append(ed)
        except RuntimeError:          # deleted editor
            continue
    return out


def _hook_client(win, client) -> None:
    if client is None or getattr(client, "_rad_rust", False):
        return
    client._rad_rust = True

    def on_diags(path, diags):
        store = win.__dict__.setdefault("rust_diags", {})
        if diags:
            store[os.path.normcase(str(Path(path).resolve()))] = diags
        else:
            store.pop(os.path.normcase(str(Path(path).resolve())), None)
        if not getattr(win, "_rust_render_pending", False):
            win._rust_render_pending = True

            def go():
                win._rust_render_pending = False
                render_errors(win)
            QTimer.singleShot(250, go)

    def on_note(method, params):
        params = params or {}
        if method == "experimental/serverStatus":
            if params.get("quiescent"):
                for ed in _rust_editors(win, client):
                    ed.refresh_inlay_hints()
                health = params.get("health", "ok")
                msg = params.get("message") or ""
                win.statusBar().showMessage(f"rust-analyzer: ready{' - ' + msg if health != 'ok' and msg else ''}",
                                            4000)
        elif method.endswith("inlayHint/refresh"):
            for ed in _rust_editors(win, client):
                ed.refresh_inlay_hints()
        elif method == "$/progress":
            v = params.get("value") or {}
            if v.get("kind") in ("begin", "report"):
                t = v.get("title") or getattr(client, "_rad_progress_title", "")
                if v.get("kind") == "begin":
                    client._rad_progress_title = t
                text = " ".join(x for x in (t, v.get("message") or "",
                                            f"{v['percentage']}%" if v.get("percentage") is not None else "") if x)
                win.statusBar().showMessage(f"rust-analyzer: {text}", 3000)
    client.diagnostics.connect(on_diags)
    client.notification.connect(on_note)


def _wrap_lsp_manager(win) -> None:
    mgr = getattr(win, "lsp_manager", None)
    if mgr is None or getattr(mgr, "_rad_rust_wrapped", False):
        return
    mgr._rad_rust_wrapped = True
    orig = mgr.client_for

    def client_for(language, root):
        c = orig(language, root)
        if c is not None and language == "rust":
            _hook_client(win, c)
        elif c is None and language == "rust" and not getattr(win, "_rust_ra_warned", False):
            win._rust_ra_warned = True
            win.log("Rust: rust-analyzer is not installed - IntelliSense uses keywords only. "
                    "Tools > Rust Settings... > Install, or: " + rt.INSTALL_HINT)
        return c
    mgr.client_for = client_for


def _inlay_enabled(ed) -> bool:
    try:
        return ed.language_id() != "rust" or rt.inlay_hints_enabled()
    except Exception:  # noqa: BLE001
        return True


def push_settings(win) -> None:
    """New Rust settings -> running rust-analyzers (workspace/didChangeConfiguration) + editors."""
    mgr = getattr(win, "lsp_manager", None)
    for (lang, _root), c in list(getattr(mgr, "clients", {}).items()) if mgr else []:
        if lang == "rust" and c is not None and c.running():
            c._notify("workspace/didChangeConfiguration", {"settings": {"rust-analyzer": rt.ra_settings()}})
    for ed in _rust_editors(win):
        ed.refresh_inlay_hints()


# ============================================================================ target combo
class TargetBar(QToolBar):
    def __init__(self, win):
        super().__init__("Rust", win)
        self.setObjectName("RustToolBar")
        self.win = win
        self.addWidget(QLabel(" Rust target: "))
        self.combo = QComboBox()
        self.combo.setMinimumWidth(220)
        self.combo.setToolTip("What F5 (debug) and Ctrl+F5 (run) start: a bin, an example, a test or a bench")
        self.combo.activated.connect(self._chosen)
        self.addWidget(self.combo)
        self.addAction("Reload", self.reload).setToolTip("Read Cargo.toml again (new targets / members)")
        self.addAction("Clippy", lambda: self._cmd("cargo clippy")).setToolTip("cargo clippy (lint)")
        self.addAction("Test", lambda: self._cmd("cargo test")).setToolTip("cargo test")
        self._project = None

    def _cmd(self, label: str) -> None:
        a = cargo_adapter(self.win.project)
        if a is None:
            return
        from ..foreign._others_base import run_steps
        for lb, steps in a.commands():
            if lb.startswith(label):
                run_steps(self.win, steps, lb)
                return

    def sync(self) -> None:
        p = self.win.project
        a = cargo_adapter(p)
        self.setVisible(a is not None)
        self.toggleViewAction().setVisible(a is not None)
        self.combo.blockSignals(True)
        self.combo.clear()
        if a is not None:
            for t in a.targets:
                self.combo.addItem(t.name, t.name)
            i = self.combo.findData(p.startup)
            if i < 0 and a.targets:
                i = 0
            self.combo.setCurrentIndex(i)
        self.combo.blockSignals(False)
        self._project = p

    def _chosen(self, _i=0) -> None:
        p = self.win.project
        name = self.combo.currentData()
        if p is None or not name:
            return
        p.startup = name
        try:
            p.save()
        except Exception:  # noqa: BLE001
            pass
        try:
            from ..foreign._others_base import install_native_menu
            install_native_menu(self.win)
        except Exception:  # noqa: BLE001
            pass
        try:
            self.win._fill_solution()
        except Exception:  # noqa: BLE001
            pass
        self.win.statusBar().showMessage(f"Rust target: {name}", 3000)

    def reload(self) -> None:
        p = self.win.project
        a = getattr(p, "adapter", None)
        if a is not None and getattr(a, "kind", "") == "cargo":
            a.meta = rt.cargo_metadata(a.root, refresh=True)
            if a.package is not None:
                name = a.package.get("name")
                a.package = next((x for x in a.meta.get("packages", []) if x.get("name") == name), a.package)
            a.info = []
            a.scan()
            p.modules = list(a.modules)
        elif p is not None and getattr(p, "language", "") == "rust-cargo":
            from ..languages.rust_cargo import RustCargoPlugin
            rt.cargo_metadata(p.folder, refresh=True)
            RustCargoPlugin.refresh_modules(p)
            p.save()
        try:
            self.win._fill_solution()
        except Exception:  # noqa: BLE001
            pass
        self.sync()


# ============================================================================ settings dialog
class _Installer(QObject):
    done = pyqtSignal(bool, str)


class RustSettingsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Rust Settings")
        self.resize(560, 300)
        s = win.settings
        self.ra = QLabel()
        self.ra.setWordWrap(True)
        self.install_btn = QPushButton("Install rust-analyzer + rust-src")
        self.install_btn.clicked.connect(self._install)
        self.check = QComboBox()
        self.check.addItem("cargo clippy (lints + errors)", "clippy")
        self.check.addItem("cargo check (errors only, faster)", "check")
        self.check.setCurrentIndex(max(0, self.check.findData(rt.check_command())))
        self.hints = QCheckBox("Show inlay hints (types, parameter names)")
        self.hints.setChecked(rt.inlay_hints_enabled())
        self.fmt = QCheckBox("Format on save with rustfmt")
        self.fmt.setChecked(s.value("format/on_save", False) in (True, "true")
                            and s.value("format/on_save/rust", True) in (True, "true"))
        self.dbg = QLabel()
        self.dbg.setWordWrap(True)
        form = QFormLayout()
        row = QHBoxLayout()
        row.addWidget(self.ra, 1)
        row.addWidget(self.install_btn)
        form.addRow("rust-analyzer:", row)
        form.addRow("Check on save:", self.check)
        form.addRow("", self.hints)
        form.addRow("", self.fmt)
        form.addRow("Debugger:", self.dbg)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addStretch(1)
        lay.addWidget(bb)
        self._inst = _Installer(self)
        self._inst.done.connect(self._installed)
        self._refresh()

    def _refresh(self) -> None:
        ra = rt.rust_analyzer(True)
        src = "rust-src installed" if rt.rust_src_installed() else "rust-src missing (std completions need it)"
        self.ra.setText(f"{ra}  ({src})" if ra else f"not installed - {rt.INSTALL_HINT}")
        self.install_btn.setEnabled(not ra or not rt.rust_src_installed())
        why = rt.debug_missing()
        self.dbg.setText("gdb on the x86_64-pc-windows-gnu build (breakpoints, locals, call stack)" if not why
                         else f"unavailable: {why}")

    def _install(self) -> None:
        self.install_btn.setEnabled(False)
        self.ra.setText("installing (rustup component add rust-analyzer rust-src)...")
        lines: list[str] = []
        from .. import progress
        task = progress.track("Installing rust-analyzer", self.win)     # status-bar progress

        def line(text):
            lines.append(text)
            task.reporter.log(str(text))

        def work():
            ok = False
            try:
                ok = rt.install_rust_analyzer(line)
            finally:
                task.complete(ok)
            self._inst.done.emit(ok, "\n".join(lines))
        threading.Thread(target=work, daemon=True).start()

    def _installed(self, ok: bool, text: str) -> None:
        self.win.log(text)
        self._refresh()
        if ok:
            self.win.log("rust-analyzer installed - reopen Rust files (or the project) to start it.")

    def accept(self) -> None:
        s = self.win.settings
        s.setValue("rust/checkCommand", self.check.currentData())
        s.setValue("rust/inlayHints", self.hints.isChecked())
        if self.fmt.isChecked():
            s.setValue("format/on_save", True)
            s.setValue("format/on_save/rust", True)
        else:
            s.setValue("format/on_save/rust", False)
        a = getattr(self.win, "a_format_on_save", None)
        if a is not None:
            a.setChecked(s.value("format/on_save", False) in (True, "true"))
        push_settings(self.win)
        super().accept()


def show_settings(win) -> RustSettingsDialog:
    dlg = RustSettingsDialog(win)
    dlg.show()
    return dlg


# ============================================================================ save -> cargo check / clippy
def notify_saved(win) -> int:
    """textDocument/didSave for every Rust editor whose file was written since the last call: rust-analyzer
    runs its check on save (cargo clippy / cargo check) only after didSave. Returns how many were sent."""
    n = 0
    for ed in _rust_editors(win):
        try:
            lsp = ed.lsp
            if lsp is None or not lsp.running():
                continue
            p = Path(str(ed.path))
            mtime = p.stat().st_mtime if p.is_file() else None
            if mtime is None or ed.isModified() or getattr(ed, "_rad_saved_mtime", None) == mtime:
                continue
            ed._rad_saved_mtime = mtime
            lsp.did_change(p, ed.text())
            lsp.did_save(p)
            n += 1
        except (RuntimeError, OSError):
            continue
    return n


def _hook_saves(win) -> None:
    def later(*_a):
        QTimer.singleShot(250, lambda: notify_saved(win))
    for name in ("a_save", "a_save_file"):
        act = getattr(win, name, None)
        if act is not None:
            act.triggered.connect(later)
    for name in ("save_all", "save_current"):
        orig = getattr(win, name, None)
        if not callable(orig):
            continue

        def wrapped(*a, _orig=orig, **kw):
            res = _orig(*a, **kw)
            later()
            return res
        setattr(win, name, wrapped)


# ============================================================================ hooks
def on_cargo_opened(win) -> None:
    """Called by cargo_project.open_cargo after the projects are shown."""
    bar = getattr(win, "rust_bar", None)
    if bar is not None:
        bar.sync()
    if not rt.rust_analyzer():
        win.log("Rust: rust-analyzer is not installed (" + rt.INSTALL_HINT + ") - Tools > Rust Settings...")


def install(win) -> None:
    win.rust_diags = {}
    providers = win.__dict__.setdefault("diag_providers", [])
    providers.append(lsp_diag_provider)
    try:
        from ..monaco_editor import MonacoEditor
        MonacoEditor.inlay_hints_enabled = staticmethod(_inlay_enabled)
    except ImportError:
        pass
    bar = TargetBar(win)
    win.addToolBar(bar)
    bar.setVisible(False)
    bar.toggleViewAction().setVisible(False)
    win.rust_bar = bar
    try:
        win.error_list.itemDoubleClicked.connect(lambda it, _c: _on_error_dclick(win, it))
    except Exception:  # noqa: BLE001
        pass
    win.extension_points.on("project_activated", lambda: QTimer.singleShot(0, bar.sync), "rust bar")
    def clear_diagnostics() -> None:
        win.rust_diags = {}
        win._rust_err_keys = set()
    win.extension_points.on("projects_reset", clear_diagnostics, "rust")
    tools = next((a.menu() for a in win.menuBar().actions()
                  if a.menu() is not None and a.text().replace("&", "") == "Tools"), None)
    if tools is not None:
        win.a_rust_settings = tools.addAction("Rust Settings...", lambda: show_settings(win))
    _hook_saves(win)
    QTimer.singleShot(0, lambda: _wrap_lsp_manager(win))     # lsp_support installs win.lsp_manager first
    _wrap_lsp_manager(win)
