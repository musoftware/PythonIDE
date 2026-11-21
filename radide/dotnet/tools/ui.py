"""Qt side of the .NET tools (radide/features/dotnet_tooling.py calls install(win)):

* Solution Explorer: Dependencies > Analyzers (analyzer assemblies > rules with their effective severity,
  source generators > generated files, read-only), with Visual Studio's context menus (Set severity,
  View Help, Show Generated Files, Configure Code Analysis ...)
* Analyze menu: Run Code Analysis (Error List), Code Cleanup (dotnet format) on document / project /
  solution, Configure Code Cleanup, Configure Code Analysis (.editorconfig editor), Remove and Sort Usings,
  Go To Decompiled Definition, Decompile Assembly
* Error List context menu: Copy, Show Error Help, Configure severity, Suppress in Source
* editor: .editorconfig indent settings, light-bulb entries (using / install package / add reference),
  context menu items
* Test Explorer: the .NET adapter (radide/dotnet/tools/testing.py), Debug Test (VSTEST_HOST_DEBUG + netcoredbg
  attach) and clickable stack-trace lines in Test Detail
"""
from __future__ import annotations

import os
import re
import threading
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, QProcess, QProcessEnvironment, QSettings, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QIcon, QKeySequence, QPainter, QPixmap, QTextCharFormat
from PyQt6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                             QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox,
                             QPushButton, QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import analyzers, cleanup, diagnostics, quickfix, sdk
from . import editorconfig as EC

ROLE = Qt.ItemDataRole.UserRole
OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"
DOTNET_EXTS = (".cs", ".vb", ".fs")
SEV_COLORS = {"error": "#E51400", "warning": "#F2A60D", "suggestion": "#1BA1E2", "silent": "#9E9E9E",
              "none": "#BDBDBD"}


# ============================================================================ small helpers
class _Bridge(QObject):
    done = pyqtSignal(object, object)


_bridge: _Bridge | None = None


def in_thread(work, then) -> None:
    """Run work() in a thread and then(result) on the GUI thread (exceptions arrive as the result)."""
    global _bridge
    if _bridge is None:
        _bridge = _Bridge()
        _bridge.done.connect(lambda cb, res: cb(res))

    def run():
        try:
            res = work()
        except Exception as e:  # noqa: BLE001
            res = e
        _bridge.done.emit(then, res)
    threading.Thread(target=run, daemon=True).start()


def _log(win, text: str) -> None:
    try:
        win.log(text)
    except Exception:  # noqa: BLE001
        print(text)


def _status(win, text: str, ms: int = 6000) -> None:
    try:
        win.statusBar().showMessage(text, ms)
    except Exception:  # noqa: BLE001
        pass


def _info(win, title: str, text: str) -> None:
    _log(win, text)
    if not OFFSCREEN:
        QMessageBox.information(win, title, text)


def _vs(win):
    sln = getattr(win, "sln", None)
    return sln if type(sln).__name__ == "VsSolution" else None


def _open_url(url: str) -> None:
    if not OFFSCREEN:
        QDesktopServices.openUrl(QUrl(url))


def sev_icon(sev: str, size: int = 14) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(SEV_COLORS.get(sev, "#9E9E9E"))
    p.setBrush(c)
    p.setPen(c.darker(130))
    if sev == "warning":
        from PyQt6.QtCore import QPointF
        from PyQt6.QtGui import QPolygonF
        p.drawPolygon(QPolygonF([QPointF(size / 2, 1), QPointF(size - 1, size - 2), QPointF(1, size - 2)]))
    elif sev in ("none", "silent"):
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(2, 2, size - 4, size - 4)
    else:
        p.drawEllipse(1, 1, size - 2, size - 2)
    p.end()
    return QIcon(pm)


def _current_editor(win):
    try:
        from ...features.formatting import _current_editor as cur
        return cur(win)
    except Exception:  # noqa: BLE001
        w = win.tabs.currentWidget() if getattr(win, "tabs", None) is not None else None
        return getattr(w, "editor", None)


def _editor_path(ed) -> Path | None:
    p = getattr(ed, "path", None)
    return Path(p) if p else None


def solution_project_files(win) -> list[Path]:
    sln = _vs(win)
    if sln is not None:
        return [Path(p.ms.path) for p in sln.all_projects() if getattr(p, "ms", None) is not None]
    proj = getattr(win, "project", None)
    folder = Path(getattr(proj, "folder", "") or ".")
    for pat in ("*.sln", "*.slnx"):
        for s in folder.glob(pat):
            return sdk.solution_projects(s)
    return sdk.find_projects(folder, 50) if proj is not None else []


def _vs_project(win, project_file: Path):
    sln = _vs(win)
    if sln is None:
        return None
    for p in sln.all_projects():
        if os.path.normcase(str(p.ms.path)) == os.path.normcase(str(project_file)):
            return p
    return None


def _reload_vs_project(win, project_file: Path) -> None:
    p = _vs_project(win, project_file)
    if p is None:
        return
    try:
        from ...foreign import vs_ui
        vs_ui._reload(win, p)
    except Exception:  # noqa: BLE001
        pass


def _append_output(win, text: str) -> None:
    fn = getattr(win, "_append_output", None)
    if callable(fn):
        try:
            fn(text)
            return
        except Exception:  # noqa: BLE001
            pass
    _log(win, text.rstrip("\n"))


def run_process(win, argv, cwd, title, on_done=None, env=None, show=True) -> QProcess:
    """argv in a QProcess, output into the Output window; on_done(exit code, full output)."""
    proc = QProcess(win)
    proc.setWorkingDirectory(str(cwd))
    e = QProcessEnvironment.systemEnvironment()
    for k, v in {**sdk.QUIET_ENV, **(env or {})}.items():
        e.insert(k, str(v))
    proc.setProcessEnvironment(e)
    proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    buf = []

    def read():
        t = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace").replace("\r\n", "\n")
        buf.append(t)
        _append_output(win, t)

    def finished(code, _st=None):
        if getattr(proc, "_rad_done", False):
            return
        proc._rad_done = True
        read()
        _log(win, f"========== {title}: {'done' if code == 0 else f'failed (exit code {code})'} ==========")
        if on_done is not None:
            try:
                on_done(int(code), "".join(buf))
            except Exception as ex:  # noqa: BLE001
                _log(win, f"*** {title}: {ex}")

    def error(err):
        if err == QProcess.ProcessError.FailedToStart:
            _log(win, f"*** {title}: cannot start {argv[0]}")
            finished(-1)
    proc.readyReadStandardOutput.connect(read)
    proc.finished.connect(finished)
    proc.errorOccurred.connect(error)
    if show:
        try:
            win.dock_output.show()
            win.dock_output.raise_()
        except Exception:  # noqa: BLE001
            pass
    _log(win, f"------ {title} ------\n> {' '.join(str(a) for a in argv)}")
    proc.start(str(argv[0]), [str(a) for a in argv[1:]])
    win._dn_procs = [p for p in getattr(win, "_dn_procs", []) if p.state() != QProcess.ProcessState.NotRunning]
    win._dn_procs.append(proc)
    return proc


def _set_modified_false(ed) -> None:
    for name in ("setModified", "_set_modified"):
        fn = getattr(ed, name, None)
        if callable(fn):
            try:
                fn(False)
                return
            except Exception:  # noqa: BLE001
                continue


def reload_open_editors(win, under: Path | None = None) -> list[str]:
    """Editors whose file changed on disk (and that have no unsaved edits) take the new text."""
    from ... import editkit
    changed, seen = [], set()
    eds = list(editkit.all_monaco_editors())
    tabs = getattr(win, "tabs", None)
    if tabs is not None:
        for i in range(tabs.count()):
            e = getattr(tabs.widget(i), "editor", None)
            if e is not None:
                eds.append(e)
    for ed in eds:
        p = _editor_path(ed)
        if p is None or id(ed) in seen:
            continue
        seen.add(id(ed))
        try:
            if under is not None:
                p.resolve().relative_to(Path(under).resolve())
        except (ValueError, OSError):
            continue
        try:
            if ed.isModified():
                continue
            disk = p.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        except (OSError, UnicodeDecodeError, RuntimeError, AttributeError):
            continue
        if disk != ed.text().replace("\r\n", "\n"):
            editkit.apply_text(ed, disk)
            _set_modified_false(ed)
            changed.append(str(p))
    return changed


def open_read_only(win, path: Path, line: int = 0):
    """Open a generated / decompiled file in a tab that cannot be edited."""
    ed = None
    try:
        ed = win.open_any_file(Path(path))
    except Exception as e:  # noqa: BLE001
        _log(win, f"*** cannot open {path}: {e}")
    if ed is not None:
        for name in ("setReadOnly",):
            fn = getattr(ed, name, None)
            if callable(fn):
                try:
                    fn(True)
                except Exception:  # noqa: BLE001
                    pass
        if line:
            try:
                ed.goto_line(max(0, line - 1))
            except Exception:  # noqa: BLE001
                pass
    return ed


# ============================================================================ Solution Explorer: Analyzers
_ANALYZERS: dict[str, dict] = {}          # project file (lower) -> analyzers.project_analyzers()
_LOADING: set[str] = set()


def _vs_set(item, kind, name, key, icon=None, win=None, tip=""):
    from ...foreign import vs_ui
    return vs_ui._set(item, kind, name, key, icon, win, tip)


def fill_analyzers(win, project, pi, key) -> None:
    ms = project.ms
    if not ms.is_sdk or ms.language not in ("C#", "VB", "F#"):
        return
    deps = None
    for i in range(pi.childCount()):
        d = pi.child(i).data(0, ROLE) or ("",)
        if d[0] == "foreign_deps":
            deps = pi.child(i)
            break
    if deps is None:
        return
    node = _vs_set(QTreeWidgetItem(deps, ["Analyzers"]), "dn_analyzers", str(ms.path), key, "SP_DirIcon", win,
                   "Analyzers and source generators used by this project")
    data = _ANALYZERS.get(str(ms.path).lower())
    if data is not None:
        populate_analyzers(win, node, project, data)
    else:
        ph = QTreeWidgetItem(node, ["Loading..."])
        ph.setData(0, ROLE, ("dn_info", "loading"))


def _find_nodes(win, kind: str, name: str) -> list:
    out = []
    tree = getattr(win, "solution", None)
    if tree is None:
        return out
    stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    while stack:
        it = stack.pop()
        d = it.data(0, ROLE) or ("",)
        if d[0] == kind and (len(d) < 2 or str(d[1]).lower() == name.lower()):
            out.append(it)
        stack.extend(it.child(i) for i in range(it.childCount()))
    return out


def load_analyzers(win, project, then=None, force: bool = False) -> None:
    path = str(project.ms.path)
    k = path.lower()
    if force:
        _ANALYZERS.pop(k, None)
    if k in _LOADING:
        return
    _LOADING.add(k)

    def done(res):
        _LOADING.discard(k)
        if isinstance(res, Exception):
            res = {"analyzers": [], "error": str(res), "generated": {}}
        _ANALYZERS[k] = res
        for node in _find_nodes(win, "dn_analyzers", path):
            try:
                populate_analyzers(win, node, project, res)
            except RuntimeError:
                continue
        if then is not None:
            then(res)
    in_thread(lambda: analyzers.project_analyzers(Path(path), log=lambda t: None), done)


def populate_analyzers(win, node, project, data) -> None:
    try:
        from ...features.solution_ui import PROJECT_ROLE
        key = node.data(0, PROJECT_ROLE)
    except Exception:  # noqa: BLE001
        key = None
    node.takeChildren()
    configured = EC.rule_severities(Path(project.folder) / "x.cs")
    gen = data.get("generated") or {}
    if data.get("error") and not data.get("analyzers"):
        it = QTreeWidgetItem(node, [f"(could not list the analyzers: {data['error']})"])
        it.setData(0, ROLE, ("dn_info", "error"))
        return
    for a in data.get("analyzers", []):
        an = _vs_set(QTreeWidgetItem(node, [a["name"]]), "dn_analyzer", a["path"], key, "SP_FileIcon", win,
                     f"{a['path']}\n{('Package: ' + a['package'] + ' ' + a.get('version', '')) if a.get('package') else a['source']}"
                     + (f"\n{a['error']}" if a.get("error") else ""))
        for r in a.get("rules", []):
            eff = EC.effective_severity(r["id"], r.get("category", ""), r.get("severity", ""), r.get("enabled", True),
                                        configured)
            text = f"{r['id']}: {r.get('title', '')}"
            ri = _vs_set(QTreeWidgetItem(an, [text]), "dn_rule",
                         "|".join([r["id"], r.get("category", ""), r.get("severity", ""),
                                   "1" if r.get("enabled", True) else "0", r.get("help", "")]), key, None, win,
                         f"{r['id']}  {r.get('title', '')}\nCategory: {r.get('category', '')}\nDefault severity: "
                         f"{EC.ROSLYN_TO_EC.get(r.get('severity', ''), r.get('severity', ''))}"
                         f"{'' if r.get('enabled', True) else ' (disabled by default)'}\n"
                         f"Effective severity: {eff}\n{r.get('help', '')}")
            ri.setIcon(0, sev_icon(eff))
        for g in a.get("generators", []):
            gi = _vs_set(QTreeWidgetItem(an, [g.rsplit(".", 1)[-1]]), "dn_generator", f"{a['name']}|{g}", key,
                         "SP_FileDialogDetailedView", win, f"Source generator {g}")
            files = (gen.get(a["name"]) or {}).get(g) or []
            for f in files:
                _vs_set(QTreeWidgetItem(gi, [Path(f).name]), "dn_genfile", str(f), key, "SP_FileIcon", win,
                        f"{f}\n(generated - read-only)")
            if not files:
                info = QTreeWidgetItem(gi, ["(no generated files - right-click > Show Generated Files)"])
                info.setData(0, ROLE, ("dn_info", "nofiles"))


def _project_by_path(win, path: str):
    p = _vs_project(win, Path(path))
    return p


def show_generated_files(win, project) -> None:
    proj = Path(project.ms.path)
    sln = _vs(win)
    cfg = sln.project_config(project)[0] if sln is not None else "Debug"
    try:
        win.save_all()
    except Exception:  # noqa: BLE001
        pass

    def done(code, _out):
        files = analyzers.generated_files(proj)
        n = sum(len(v) for g in files.values() for v in g.values())
        _log(win, f"{proj.stem}: {n} generated file(s) in obj (shown under Dependencies > Analyzers)")
        load_analyzers(win, project, force=True)
    run_process(win, analyzers.emit_generated_argv(proj, cfg), proj.parent, f"Show Generated Files ({proj.stem})",
                done)


def analyzer_menu(win, project, item, kind, name):
    m = QMenu(win)
    if kind == "dn_analyzers":
        m.addAction("Configure Code Analysis...", lambda: configure_code_analysis(win, project))
        m.addAction("Show Generated Files", lambda: show_generated_files(win, project))
        m.addAction("Refresh", lambda: load_analyzers(win, project, force=True))
        return m
    if kind == "dn_analyzer":
        m.addAction("Open Containing Folder", lambda: _explore(Path(name).parent))
        m.addAction("Copy Path", lambda: QApplication.clipboard().setText(name))
        return m
    if kind == "dn_rule":
        rid, cat, default, enabled, help_ = (name.split("|") + [""] * 5)[:5]
        sub = m.addMenu("Set severity")
        for sev in ["default"] + EC.SEVERITIES:
            a = sub.addAction(sev_icon(sev) if sev != "default" else QIcon(), EC.SEVERITY_TITLES[sev],
                              lambda s=sev, r=rid: set_rule_severity(win, project, r, s))
            a.setData(sev)
        m.addAction("View Help", lambda: _open_url(help_ or diagnostics.help_url(rid)))
        m.addAction("Copy", lambda: QApplication.clipboard().setText(item.text(0) if item is not None else rid))
        return m
    if kind == "dn_generator":
        m.addAction("Show Generated Files", lambda: show_generated_files(win, project))
        return m
    if kind == "dn_genfile":
        m.addAction("Open (read-only)", lambda: open_read_only(win, Path(name)))
        m.addAction("Open Containing Folder", lambda: _explore(Path(name).parent))
        return m
    m.deleteLater()
    return None


def _explore(folder) -> None:
    if folder and Path(folder).exists() and not OFFSCREEN:
        try:
            os.startfile(str(folder))          # noqa: S606 - Windows Explorer
        except OSError:
            pass


def editorconfig_target(win, near: Path | None = None) -> Path:
    """The .editorconfig Visual Studio edits: the nearest one, else one in the solution (or project) folder."""
    if near is not None:
        found = EC.files_for(Path(near))
        if found:
            return found[-1]
    sln = _vs(win)
    if sln is not None and getattr(sln, "file", None):
        return Path(sln.file).parent / ".editorconfig"
    if near is not None:
        p = sdk.project_for_file(Path(near))
        if p is not None:
            return p.parent / ".editorconfig"
        return Path(near).parent / ".editorconfig"
    proj = getattr(win, "project", None)
    return Path(getattr(proj, "folder", ".")) / ".editorconfig"


def set_rule_severity(win, project, rule_id: str, severity: str) -> Path:
    target = editorconfig_target(win, Path(project.folder) / "x.cs")
    section = EC.CS_SECTION if project.ms.language == "C#" else ("[*.vb]" if project.ms.language == "VB" else
                                                                   EC.DOTNET_SECTION)
    EC.set_severity(target, rule_id, severity, section)
    _log(win, f"{target}: {rule_id} severity = {severity}")
    data = _ANALYZERS.get(str(project.ms.path).lower())
    if data is not None:
        for node in _find_nodes(win, "dn_analyzers", str(project.ms.path)):
            try:
                expanded = _expanded_names(node)
                populate_analyzers(win, node, project, data)
                _restore_expanded(node, expanded)
            except RuntimeError:
                continue
    return target


def _expanded_names(node) -> set:
    out = set()
    stack = [node]
    while stack:
        it = stack.pop()
        if it.isExpanded():
            out.add(it.text(0))
        stack.extend(it.child(i) for i in range(it.childCount()))
    return out


def _restore_expanded(node, names: set) -> None:
    stack = [node]
    while stack:
        it = stack.pop()
        if it.text(0) in names:
            it.setExpanded(True)
        stack.extend(it.child(i) for i in range(it.childCount()))


def _on_expand(win, item) -> None:
    d = item.data(0, ROLE) or ("",)
    if d[0] != "dn_analyzers":
        return
    k = str(d[1]).lower()
    if k in _ANALYZERS or k in _LOADING:
        return
    project = _project_by_path(win, str(d[1]))
    if project is not None:
        load_analyzers(win, project)


# ============================================================================ Configure Code Analysis dialog
class EditorConfigDialog(QDialog):
    """Visual Studio's .editorconfig editor: Whitespace / Code Style / Analyzers."""

    def __init__(self, win, target: Path, project=None):
        super().__init__(win)
        self.win, self.target, self.project = win, Path(target), project
        self.setWindowTitle("Configure Code Analysis - .editorconfig")
        self.resize(900, 620)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.path_label = QLabel(f"File: {self.target}")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        top.addWidget(self.path_label, 1)
        b = QPushButton("Open as Text")
        b.clicked.connect(self._open_text)
        top.addWidget(b)
        lay.addLayout(top)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        self.combos: dict[tuple[str, str], QComboBox] = {}
        self._build_whitespace()
        self._build_style()
        self._build_analyzers()
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.pending: dict[str, str | None] = {}         # rule id -> severity (None = default)

    def _value(self, section, key):
        return EC.get_value(self.target, section, key) if self.target.is_file() else None

    def _combo(self, form, section, key, title, values):
        c = QComboBox()
        c.addItem("(not set)", None)
        for v in values:
            c.addItem(v, v)
        cur = self._value(section, key)
        if cur is not None:
            i = c.findData(cur)
            if i < 0:
                c.addItem(cur, cur)
                i = c.count() - 1
            c.setCurrentIndex(i)
        c.setProperty("orig", cur)
        form.addRow(title, c)
        self.combos[(section, key)] = c

    def _build_whitespace(self):
        w = QWidget()
        form = QFormLayout(w)
        form.addRow(QLabel("Applies to [*] (every file under this folder)"))
        for key, title, values in EC.WHITESPACE:
            self._combo(form, "[*]", key, title, values)
        self.tabs.addTab(w, "Whitespace")

    def _build_style(self):
        w = QWidget()
        form = QFormLayout(w)
        for key, title, values, section in EC.CODE_STYLE:
            self._combo(form, section, key, title, values)
        self.tabs.addTab(w, "Code Style")

    def _build_analyzers(self):
        w = QWidget()
        v = QVBoxLayout(w)
        row = QHBoxLayout()
        self.search = QLineEdit(placeholderText="Search rules (id, title or category)")
        self.search.textChanged.connect(self._filter)
        row.addWidget(self.search, 1)
        row.addWidget(QLabel("Severity of the selected rules:"))
        self.sev_combo = QComboBox()
        for s in ["default"] + EC.SEVERITIES:
            self.sev_combo.addItem(sev_icon(s) if s != "default" else QIcon(), EC.SEVERITY_TITLES[s], s)
        row.addWidget(self.sev_combo)
        apply_b = QPushButton("Set")
        apply_b.clicked.connect(self._set_selected)
        row.addWidget(apply_b)
        v.addLayout(row)
        self.rules = QTreeWidget()
        self.rules.setHeaderLabels(["ID", "Title", "Category", "Default", "Severity"])
        self.rules.setRootIsDecorated(False)
        self.rules.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.rules.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.rules.setSortingEnabled(True)
        v.addWidget(self.rules, 1)
        self.rules_note = QLabel("Loading the project's analyzers...")
        v.addWidget(self.rules_note)
        self.tabs.addTab(w, "Analyzers")
        if self.project is not None:
            data = _ANALYZERS.get(str(self.project.ms.path).lower())
            if data is not None:
                self._fill_rules(data)
            else:
                load_analyzers(self.win, self.project, then=lambda d: self._fill_rules(d) if self.isVisible() or
                               OFFSCREEN else None)
        else:
            self.rules_note.setText("Open a .NET project to list its analyzer rules.")

    def _fill_rules(self, data):
        try:
            self.rules.clear()
        except RuntimeError:
            return
        configured = EC.rule_severities(Path(self.project.folder) / "x.cs")
        n = 0
        self.rules.setSortingEnabled(False)
        seen = set()
        for a in data.get("analyzers", []):
            for r in a.get("rules", []):
                if r["id"] in seen:
                    continue
                seen.add(r["id"])
                eff = EC.effective_severity(r["id"], r.get("category", ""), r.get("severity", ""),
                                            r.get("enabled", True), configured)
                default = EC.ROSLYN_TO_EC.get(r.get("severity", ""), "") if r.get("enabled", True) else "none"
                it = QTreeWidgetItem([r["id"], r.get("title", ""), r.get("category", ""), default, eff])
                it.setIcon(4, sev_icon(eff))
                it.setData(0, ROLE, r)
                it.setToolTip(1, r.get("help", ""))
                self.rules.addTopLevelItem(it)
                n += 1
        self.rules.setSortingEnabled(True)
        self.rules.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.rules_note.setText(f"{n} rules from {len(data.get('analyzers', []))} analyzer assemblies. "
                                "Severities are written as dotnet_diagnostic.<ID>.severity.")

    def _filter(self, text):
        t = text.strip().lower()
        for i in range(self.rules.topLevelItemCount()):
            it = self.rules.topLevelItem(i)
            it.setHidden(bool(t) and not any(t in it.text(c).lower() for c in range(3)))

    def _set_selected(self):
        sev = self.sev_combo.currentData()
        for it in self.rules.selectedItems():
            r = it.data(0, ROLE) or {}
            self.pending[r.get("id", it.text(0))] = None if sev == "default" else sev
            shown = it.text(3) if sev == "default" else sev
            it.setText(4, shown)
            it.setIcon(4, sev_icon(shown))

    def _open_text(self):
        if not self.target.exists():
            EC.set_value(self.target, "[*]", "indent_style", "space")
        self.win.open_any_file(self.target)

    def apply(self) -> int:
        n = 0
        for (section, key), c in self.combos.items():
            val = c.currentData()
            if val != c.property("orig"):
                n += EC.set_value(self.target, section, key, val)
        lang = getattr(getattr(self.project, "ms", None), "language", "C#")
        section = EC.CS_SECTION if lang == "C#" else "[*.vb]" if lang == "VB" else EC.DOTNET_SECTION
        for rid, sev in self.pending.items():
            n += EC.set_severity(self.target, rid, sev, section)
        return n

    def accept(self):
        n = self.apply()
        _log(self.win, f"{self.target}: {n} setting(s) changed")
        if self.project is not None:
            data = _ANALYZERS.get(str(self.project.ms.path).lower())
            if data is not None:
                for node in _find_nodes(self.win, "dn_analyzers", str(self.project.ms.path)):
                    try:
                        populate_analyzers(self.win, node, self.project, data)
                    except RuntimeError:
                        pass
        super().accept()


def _active_vs_project(win):
    p = getattr(win, "project", None)
    return p if getattr(p, "ms", None) is not None else None


def configure_code_analysis(win, project=None, exec_: bool = True):
    project = project or _active_vs_project(win)
    near = Path(project.folder) / "x.cs" if project is not None else None
    dlg = EditorConfigDialog(win, editorconfig_target(win, near), project)
    win._dn_ec_dialog = dlg
    if exec_ and not OFFSCREEN:
        dlg.exec()
    return dlg


# ============================================================================ Code Cleanup / usings
def cleanup_profile() -> str:
    return str(QSettings().value("dotnet/cleanupProfile", "full") or "full")


def configure_code_cleanup(win):
    items = [cleanup.PROFILES[k][0] for k in cleanup.PROFILES]
    keys = list(cleanup.PROFILES)
    cur = keys.index(cleanup_profile()) if cleanup_profile() in keys else 0
    if OFFSCREEN:
        return cleanup_profile()
    text, ok = QInputDialog.getItem(win, "Configure Code Cleanup", "Profile used by Run Code Cleanup:", items, cur,
                                    False)
    if ok:
        QSettings().setValue("dotnet/cleanupProfile", keys[items.index(text)])
    return cleanup_profile()


def _cleanup_target(win, scope: str) -> tuple[Path | None, list[Path], Path | None]:
    """(project/solution to format, files to include, editor path) for a scope."""
    if scope == "document":
        ed = _current_editor(win)
        p = _editor_path(ed)
        if p is None or p.suffix.lower() not in DOTNET_EXTS:
            return None, [], None
        return sdk.project_for_file(p), [p], p
    if scope == "project":
        proj = _active_vs_project(win)
        if proj is not None:
            return Path(proj.ms.path), [], None
        ed = _current_editor(win)
        p = _editor_path(ed)
        return (sdk.project_for_file(p) if p else None), [], None
    sln = _vs(win)
    if sln is not None and getattr(sln, "file", None):
        return Path(sln.file), [], None
    return _cleanup_target(win, "project")


def code_cleanup(win, scope: str = "document", profile: str | None = None, then=None):
    """Analyze > Code Cleanup (Ctrl+K, Ctrl+E): dotnet format on the document / project / solution."""
    target, include, doc = _cleanup_target(win, scope)
    if target is None:
        _status(win, "Code Cleanup works on C# / VB documents and .NET projects")
        return None
    try:
        win.save_all()
    except Exception:  # noqa: BLE001
        pass
    profile = profile or cleanup_profile()
    argv = cleanup.format_argv(target, profile, include or None)
    folder = target.parent

    def done(code, out):
        changed = reload_open_editors(win, folder)
        msg = f"Code Cleanup ({cleanup.PROFILES.get(profile, ('', ''))[0]}): " + \
              (f"{len(changed)} open document(s) updated" if changed else "done")
        _status(win, msg, 8000)
        if then is not None:
            then(code, changed)
    return run_process(win, argv, folder, f"Code Cleanup {target.name}" + (f" ({doc.name})" if doc else ""), done)


def remove_and_sort_usings(win, ed=None, then=None):
    """Edit > IntelliSense > Remove and Sort Usings (Ctrl+R, Ctrl+G)."""
    ed = ed or _current_editor(win)
    path = _editor_path(ed)
    if path is None or path.suffix.lower() not in (".cs", ".vb"):
        _status(win, "Remove and Sort Usings works in C# and VB files")
        return
    text = ed.text()
    _status(win, "Removing unnecessary usings...", 20000)

    def done(res):
        if isinstance(res, Exception):
            _log(win, f"*** Remove and Sort Usings: {res}")
            return
        new, removed, err = res
        if err:
            _log(win, f"Remove and Sort Usings: {err}")
        if new is not None and new.replace("\r\n", "\n") != ed.text().replace("\r\n", "\n"):
            from ... import editkit
            editkit.apply_text(ed, new.replace("\r\n", "\n") if "\r\n" not in ed.text() else new)
        _status(win, f"Removed {len(removed)} unnecessary using directive(s)" + ("; sorted" if new else ""), 6000)
        if then is not None:
            then(new, removed, err)
    in_thread(lambda: cleanup.organize_usings(path, text), done)


# ============================================================================ Run Code Analysis -> Error List
def _diag_provider(win):
    if _vs(win) is None and not getattr(win, "_dn_diags_any", False):
        return []
    from ...tools import Diag
    out = []
    for d in getattr(win, "_dn_diags", []) or []:
        if d.severity not in ("Error", "Warning"):
            continue
        out.append(Diag(d.severity, d.row_message(), d.file, max(1, d.line)))
    return out


def run_code_analysis(win, scope: str = "solution", then=None):
    """Analyze > Run Code Analysis: a rebuild with every analyzer on; the diagnostics go to the Error List."""
    target, _inc, _doc = _cleanup_target(win, "solution" if scope == "solution" else "project")
    if target is None:
        _status(win, "Open a .NET solution or project first")
        return None
    try:
        win.save_all()
    except Exception:  # noqa: BLE001
        pass
    sln = _vs(win)
    cfg = getattr(sln, "configuration", "Debug") if sln is not None else "Debug"

    def done(code, out):
        diags = diagnostics.parse_build_output(out)
        win._dn_diags = diags
        win._dn_diags_any = True
        try:
            from ...tools import run_checks
            run_checks(win, show=True)
        except Exception as e:  # noqa: BLE001
            _log(win, f"*** Error List: {e}")
        e = sum(d.severity == "Error" for d in diags)
        w = sum(d.severity == "Warning" for d in diags)
        _log(win, f"Code Analysis: {e} error(s), {w} warning(s) - see the Error List")
        if then is not None:
            then(diags)
    return run_process(win, diagnostics.analysis_argv(target, cfg), target.parent, f"Run Code Analysis on {target.name}",
                       done)


# ---------------------------------------------------------------- Error List context menu
def _error_row(win, item) -> dict:
    if item is None:
        return {}
    msg, file, line = item.text(1), item.text(2), item.text(3)
    try:
        ln = int(line or 0)
    except ValueError:
        ln = 0
    return {"severity": item.text(0), "message": msg, "file": file, "line": ln, "id": diagnostics.diag_id(msg)}


def _abs_file(win, file: str) -> Path | None:
    if not file:
        return None
    p = Path(file)
    if p.is_absolute():
        return p
    proj = getattr(win, "project", None)
    return Path(proj.folder) / file if proj is not None else None


def error_list_menu(win, pos) -> QMenu | None:
    el = win.error_list
    item = el.itemAt(pos)
    row = _error_row(win, item)
    m = QMenu(win)
    m.addAction("Copy", lambda: QApplication.clipboard().setText(
        "\t".join(item.text(c) for c in range(el.columnCount())) if item is not None else ""))
    m.addSeparator()
    rid = row.get("id", "")
    a = m.addAction("Show Error Help", lambda: _open_url(diagnostics.help_url(rid)))
    a.setEnabled(bool(rid))
    sub = m.addMenu("Configure severity")
    sub.setEnabled(bool(rid))
    for sev in EC.SEVERITIES:
        sub.addAction(sev_icon(sev), EC.SEVERITY_TITLES[sev], lambda s=sev: configure_severity(win, row, s))
    sup = m.addMenu("Suppress")
    sup.setEnabled(bool(rid) and bool(row.get("file")) and row.get("line", 0) > 0)
    sup.addAction("In Source", lambda: suppress_in_source(win, row))
    sup.addAction("In Suppression File", lambda: suppress_in_file(win, row))
    m.addSeparator()
    m.addAction("Run Code Analysis on Solution", lambda: run_code_analysis(win, "solution"))
    for hook in list(getattr(win, "error_list_menu_hooks", []) or []):
        try:
            hook(m, item)
        except Exception:  # noqa: BLE001
            pass
    win._dn_error_menu = m
    return m


def configure_severity(win, row: dict, severity: str) -> Path | None:
    rid = row.get("id")
    if not rid:
        return None
    f = _abs_file(win, row.get("file", ""))
    target = editorconfig_target(win, f)
    ext = f.suffix.lower() if f is not None else ".cs"
    section = "[*.vb]" if ext == ".vb" else EC.CS_SECTION if ext in (".cs", "") else EC.DOTNET_SECTION
    EC.set_severity(target, rid, severity, section)
    _log(win, f"{target}: dotnet_diagnostic.{rid}.severity = {severity}")
    _status(win, f"{rid}: severity set to {severity} in {target.name}")
    return target


def _edit_file_lines(win, path: Path, fn) -> bool:
    from ... import editkit
    ed = editkit.find_editor(win, path)
    text = ed.text() if ed is not None else sdk.text(path)
    new = fn(text)
    if new is None or new == text:
        return False
    if ed is not None:
        editkit.apply_text(ed, new)
    else:
        crlf = "\r\n" in Path(path).read_text(encoding="utf-8-sig", errors="replace")
        Path(path).write_text(new.replace("\n", "\r\n") if crlf else new, encoding="utf-8", newline="")
    return True


def suppress_in_source(win, row: dict) -> bool:
    f = _abs_file(win, row.get("file", ""))
    rid, line = row.get("id"), int(row.get("line") or 0)
    if f is None or not rid or line <= 0:
        return False
    vb = f.suffix.lower() == ".vb"

    def change(text):
        lines = text.replace("\r\n", "\n").split("\n")
        if line > len(lines):
            return None
        ind = re.match(r"^\s*", lines[line - 1]).group(0)
        on, off = ((f"#Disable Warning {rid}", f"#Enable Warning {rid}") if vb else
                   (f"#pragma warning disable {rid}", f"#pragma warning restore {rid}"))
        lines[line - 1:line] = [ind + on, lines[line - 1], ind + off]
        return "\n".join(lines)
    ok = _edit_file_lines(win, f, change)
    if ok:
        _status(win, f"{rid} suppressed in source ({f.name}:{line})")
    return ok


def suppress_in_file(win, row: dict) -> Path | None:
    """[assembly: SuppressMessage(...)] in GlobalSuppressions.cs of the project (Visual Studio's file)."""
    f = _abs_file(win, row.get("file", ""))
    rid = row.get("id")
    if f is None or not rid:
        return None
    proj = sdk.project_for_file(f)
    if proj is None or proj.suffix.lower() != ".csproj":
        return None
    gs = proj.parent / "GlobalSuppressions.cs"
    text = sdk.text(gs) if gs.exists() else (
        "// This file is used by Code Analysis to maintain SuppressMessage\n"
        "// attributes that are applied to this project.\n"
        "// Project-level suppressions either have no target or are given\n"
        "// a specific target and scoped to a namespace, type, member, etc.\n\n"
        "using System.Diagnostics.CodeAnalysis;\n\n")
    msg = row.get("message", "").split(":", 1)[-1].strip().replace('"', "'")
    cat = "Style" if rid.upper().startswith("IDE") else "Usage"
    text = text.rstrip("\n") + "\n" + \
        f'[assembly: SuppressMessage("{cat}", "{rid}:{msg[:80]}", Justification = "<Pending>")]\n'
    gs.write_text(text, encoding="utf-8")
    _log(win, f"{rid} suppressed in {gs}")
    return gs


# ============================================================================ quick actions (light bulb)
def quick_action_provider(win, ed, line, col) -> list:
    path = _editor_path(ed)
    if path is None or path.suffix.lower() not in (".cs", ".vb"):
        return []
    from ...features.refactor import word_at
    text = ed.text()
    word, c1, c2 = word_at(text, line, col)
    if not word:
        return []
    fixes = quickfix.fixes_for(word, text, path, solution_projects=solution_project_files(win))
    return [(f.title, (lambda f=f: apply_fix(win, ed, f, line))) for f in fixes]


def apply_fix(win, ed, fix, line: int | None = None) -> None:
    from ... import editkit
    path = _editor_path(ed)
    vb = path is not None and path.suffix.lower() == ".vb"

    def add_using():
        if fix.namespace:
            editkit.apply_edits(ed, quickfix.using_edit(ed.text(), fix.namespace, vb))
    if fix.kind == "using":
        add_using()
    elif fix.kind == "qualify":
        from ...features.refactor import word_at
        ln = line if line is not None else ed.getCursorPosition()[0]
        lines = ed.text().split("\n")
        col = lines[ln].find(fix.type_name) if 0 <= ln < len(lines) else -1
        if col >= 0:
            w, c1, c2 = word_at(ed.text(), ln, col)
            editkit.apply_edits(ed, [[ln, c1, ln, c2, f"{fix.namespace}.{fix.type_name}"]])
    elif fix.kind == "project":
        proj = sdk.project_for_file(path)
        if proj is None:
            return
        add_project_reference(win, proj, Path(fix.project), then=lambda ok: ok and add_using())
    elif fix.kind == "package":
        proj = sdk.project_for_file(path)
        if proj is None:
            return
        run_process(win, [sdk.dotnet() or "dotnet", "add", str(proj), "package", fix.package], proj.parent,
                    f"dotnet add package {fix.package}",
                    lambda code, _o: code == 0 and (add_using(), _reload_vs_project(win, proj)))
    elif fix.kind == "search":
        search_nuget(win, path, fix.type_name)


def add_project_reference(win, project: Path, other: Path, then=None) -> None:
    """dotnet add reference for SDK projects, a direct <ProjectReference> edit for the others."""
    text = sdk.text(project)
    if "Sdk=" in text[:500] and sdk.dotnet():
        run_process(win, [sdk.dotnet(), "add", str(project), "reference", str(other)], project.parent,
                    f"Add reference {other.stem} -> {project.stem}",
                    lambda code, _o: (_reload_vs_project(win, project), then and then(code == 0)))
        return
    try:
        from ...foreign.msbuild import MSBuildProject
        ms = MSBuildProject.load(project)
        ms.add_project_reference(other)
        ms.save()
        _reload_vs_project(win, project)
        if then:
            then(True)
    except Exception as e:  # noqa: BLE001
        _log(win, f"*** cannot add the reference: {e}")
        if then:
            then(False)


def search_nuget(win, path: Path | None, term: str) -> None:
    proj = sdk.project_for_file(path) if path else None
    vp = _vs_project(win, proj) if proj else None
    if vp is not None:
        from ...foreign import vs_ui
        try:
            vs_ui.manage_packages(win, vp, search=term)
            return
        except TypeError:
            pass
        try:
            vs_ui.manage_packages(win, vp)
            return
        except Exception:  # noqa: BLE001
            pass
    _open_url(f"https://www.nuget.org/packages?q={term}")


# ============================================================================ decompiler
def _dotted_at(text: str, line: int, col: int) -> str:
    lines = text.split("\n")
    if not 0 <= line < len(lines):
        return ""
    s = lines[line]
    for m in re.finditer(r"[A-Za-z_][\w]*(?:\s*\.\s*[A-Za-z_]\w*)*", s):
        if m.start() <= col <= m.end():
            parts = re.sub(r"\s+", "", m.group(0)).split(".")
            # the part under the caret and everything before it
            upto = re.sub(r"\s+", "", s[m.start():max(col, m.start())])
            n = upto.count(".") + 1
            return ".".join(parts[:n])
    return ""


def decompile_candidates(win, ed) -> list[tuple[str, str, str]]:
    """[(namespace, type metadata name, assembly)] for the symbol under the caret."""
    path = _editor_path(ed)
    if path is None:
        return []
    line, col = ed.getCursorPosition()
    text = ed.text()
    dotted = _dotted_at(text, line, col)
    if not dotted:
        return []
    proj = sdk.project_for_file(path)
    idx = quickfix.index_for(proj)
    lines = text.split("\n")
    after = lines[line][col:] if 0 <= line < len(lines) else ""
    generic = bool(re.match(r"\w*\s*<", after))
    parts = dotted.split(".")
    out = []
    # a fully qualified name: System.Text.StringBuilder
    for i in range(len(parts) - 1, 0, -1):
        ns, name = ".".join(parts[:i]), parts[i]
        asm = idx.find_type(f"{ns}.{name}")
        if asm:
            out.append((ns, idx.raw_name(ns, name, generic), asm))
            return out
    word = parts[-1] if len(parts) == 1 else parts[0]
    visible = quickfix.file_usings(text, path, proj)
    cands = idx.lookup(word)
    vis = [c for c in cands if c[0] in visible] or cands
    for ns, asm in vis[:8]:
        out.append((ns, idx.raw_name(ns, word, generic), asm))
    return out


def ensure_decompiler(win, then) -> None:
    from .. import decompile
    if decompile.find_ilspycmd():
        then(True)
        return
    if not OFFSCREEN:
        ans = QMessageBox.question(win, "Decompiler", "ILSpy's command line (ilspycmd) is needed to show decompiled "
                                   "sources.\n\nInstall it now from nuget.org (dotnet tool, into "
                                   "%LOCALAPPDATA%\\RADIDE\\tools - no administrator rights)?")
        if ans != QMessageBox.StandardButton.Yes:
            then(False)
            return
    _log(win, "Installing ilspycmd (dotnet tool install --tool-path ...) ...")
    in_thread(lambda: decompile.ensure_ilspycmd(lambda t: None),
              lambda res: (_log(win, f"*** {res}") if isinstance(res, Exception) else _log(win, f"ilspycmd: {res}"),
                           then(not isinstance(res, Exception))))


def open_decompiled(win, assembly: str, type_name: str, then=None) -> None:
    from .. import decompile

    def go(ok):
        if not ok:
            return
        _status(win, f"Decompiling {type_name} ...", 30000)

        def done(res):
            if isinstance(res, Exception):
                _log(win, f"*** Decompile {type_name}: {res}")
                _status(win, f"Could not decompile {type_name}")
                if then:
                    then(None)
                return
            ed = open_read_only(win, res)
            _status(win, f"{type_name} [decompiled from {Path(assembly).name}]")
            if then:
                then(res)
            return ed
        in_thread(lambda: decompile.decompiled_file(assembly, type_name), done)
    ensure_decompiler(win, go)


def goto_decompiled_definition(win, ed=None, then=None) -> None:
    """Go To Definition into metadata: the type under the caret, decompiled (read-only tab)."""
    ed = ed or _current_editor(win)
    path = _editor_path(ed)
    if path is None or path.suffix.lower() not in (".cs", ".vb", ".fs"):
        _status(win, "Go To Decompiled Definition works in C# / VB / F# files")
        return
    cands = decompile_candidates(win, ed)
    if not cands:
        _status(win, "No framework or package type under the caret")
        if then:
            then(None)
        return
    pick = cands[0]
    if len(cands) > 1 and not OFFSCREEN:
        labels = [f"{ns}.{t}  ({Path(a).name})" for ns, t, a in cands]
        text, ok = QInputDialog.getItem(win, "Go To Decompiled Definition", "Type:", labels, 0, False)
        if not ok:
            return
        pick = cands[labels.index(text)]
    ns, t, asm = pick
    open_decompiled(win, asm, f"{ns}.{t}" if ns else t, then)


def decompile_assembly_dialog(win) -> None:
    if OFFSCREEN:
        return
    f, _ = QFileDialog.getOpenFileName(win, "Decompile Assembly", "", ".NET assemblies (*.dll *.exe)")
    if not f:
        return
    t, ok = QInputDialog.getText(win, "Decompile Assembly", "Type (full name, empty = the whole assembly):")
    if not ok:
        return
    open_decompiled(win, f, t.strip() or None)


# ============================================================================ Test Explorer: debug + links
class _AttachDap:
    """netcoredbg attach session factory (subclass made lazily: radide.dap imports Qt widgets)."""
    cls = None

    @classmethod
    def make(cls):
        if cls.cls is None:
            from ...dap import DapSession

            class AttachSession(DapSession):
                pid = 0
                skip_first_stop = True

                def _on_initialize(self, body, _msg):
                    self._request("attach", {"processId": int(self.pid), "justMyCode": True})

                def _on_stopped(self, reason):
                    # the testhost's own Debugger.Break() after attaching: not user code - continue
                    if self.skip_first_stop and reason in ("pause", "entry", "exception") and not self.paused:
                        self.skip_first_stop = False

                        def got(body, _m):
                            frames = body.get("stackFrames", [])
                            src = (frames[0].get("source") or {}).get("path", "") if frames else ""
                            if not src or "testhost" in src.lower():
                                self._request("continue", {"threadId": self.thread_id})
                            else:
                                DapSession._on_stopped(self, reason)
                        self._request("stackTrace", {"threadId": self.thread_id, "levels": 1}, got)
                        return
                    DapSession._on_stopped(self, reason)
            cls.cls = AttachSession
        return cls.cls


def debug_tests(explorer, adapter, keys) -> bool:
    """Debug the selected .NET tests: dotnet test with VSTEST_HOST_DEBUG=1 waits for a debugger; netcoredbg
    attaches to the testhost process with the editor's breakpoints; the results then come from the TRX file."""
    import time
    win = explorer.win
    from ...bridgedebug import find_netcoredbg
    if not find_netcoredbg():
        _status(win, "Debugging tests needs netcoredbg (%LOCALAPPDATA%\\RADIDE\\tools\\netcoredbg)", 8000)
        _log(win, "*** Debug Test: netcoredbg was not found - install it from the Debug menu (or run the tests)")
        return False
    if getattr(win, "session", None) is not None and win.session.running():
        _status(win, "A program is already running (Debug > Stop first)", 5000)
        return False
    try:
        win.save_all()
    except Exception:  # noqa: BLE001
        pass
    items = [explorer.items[k] for k in keys if k in explorer.items]
    plan = adapter.plan(items)
    if not plan.steps:
        return False
    step = plan.steps[0]
    if len(plan.steps) > 1:
        _log(win, "Debug Test: tests of several projects are selected - debugging the first project's tests")
        first = adapter._project_of(items[0])
        items = [i for i in items if adapter._project_of(i) == first]
        keys = [f"dotnet|{i.id}" for i in items]
    try:
        from ...foreign.vs_ui import _register_netcoredbg
        _register_netcoredbg()
    except Exception:  # noqa: BLE001
        from ...dap import ADAPTERS
        ADAPTERS.setdefault("netcoredbg", (lambda: [find_netcoredbg(), "--interpreter=vscode"],
                                           lambda prog, args, cwd, env: {}))
    bps = []
    try:
        win._sync_breakpoints()
    except Exception:  # noqa: BLE001
        pass
    try:
        from ...foreign.vs_ui import all_breakpoints
        bps = all_breakpoints(win) if _vs(win) is not None else []
    except Exception:  # noqa: BLE001
        bps = []
    if not bps:
        for f, ln, *rest in getattr(win, "_all_breakpoints", lambda: [])():
            bps.append((f, ln, *(rest[:1])))
    bps += explorer._editor_breakpoints()
    bps = [(os.path.normpath(str(Path(b[0]).resolve())), *b[1:]) for b in bps]
    for k in keys:
        it = explorer.items.get(k)
        if it is not None:
            it.state = "running"
            n = explorer.nodes.get(k)
            if n is not None:
                from ...features.test_explorer import state_icon
                n.setIcon(0, state_icon("running"))
    explorer._refresh_groups()
    win.output.clear()
    _log(win, f"------ Debug test: {', '.join(i.name for i in items)} ------")
    proc = QProcess(explorer)
    proc.setWorkingDirectory(str(step.cwd))
    env = QProcessEnvironment.systemEnvironment()
    for k, v in {**step.env, "VSTEST_HOST_DEBUG": "1"}.items():
        env.insert(k, str(v))
    proc.setProcessEnvironment(env)
    proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    state = {"session": None, "log": "", "done": False}

    def start_session(pid: int):
        S = _AttachDap.make()
        s = S("netcoredbg", "", [], Path(step.cwd), {}, bps, win)
        s.pid = pid
        s.break_on_exception = False
        s.output.connect(win._append_output)
        s.stopped.connect(win._on_stopped)
        s.resumed.connect(win._on_resumed)
        try:
            s.evalResult.connect(lambda txt: win.immediate.show_result(txt))
        except Exception:  # noqa: BLE001
            pass
        s.failed.connect(lambda err: _log(win, f"*** Error: {err}"))

        def dbg_finished(code):
            try:
                win._on_finished(code)
            except Exception:  # noqa: BLE001
                pass
            QTimer.singleShot(8000, lambda: proc.kill() if proc.state() != QProcess.ProcessState.NotRunning
                              else None)
        s.finished.connect(dbg_finished)
        win.session = s
        state["session"] = s
        s.start()
        _status(win, "Debugging test...")
        try:
            win._update_actions()
        except Exception:  # noqa: BLE001
            pass
        explorer.debug_session = s

    def read():
        t = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace").replace("\r\n", "\n")
        state["log"] += t
        _append_output(win, t)
        if state["session"] is None:
            m = re.search(r"Process Id:\s*(\d+),\s*Name:\s*testhost", state["log"])
            if m:
                start_session(int(m.group(1)))

    def finished(code, _st=None):
        if state["done"]:
            return
        state["done"] = True
        read()
        s = state["session"]
        if s is not None and s.running():
            try:
                s.stop()
            except Exception:  # noqa: BLE001
                pass
        live = [k for k in keys if k in explorer.items]
        explorer._run = (adapter, [explorer.items[k] for k in live], plan)
        explorer._run_log = state["log"]
        explorer._jobs = []
        explorer._cov_new = {}
        explorer._t0 = time.perf_counter()
        explorer._job_done()
        explorer.debug_finished = True
    proc.readyReadStandardOutput.connect(read)
    proc.finished.connect(finished)
    _log(win, "> " + " ".join(str(a) for a in step.argv) + "   (VSTEST_HOST_DEBUG=1)")
    proc.start(str(step.argv[0]), [str(a) for a in step.argv[1:]])
    explorer._debug_proc = proc
    explorer.debug_finished = False
    return True


_STACK = re.compile(r"(?:\bin\s+(?P<f1>[A-Za-z]:[^:\n]+?|/[^:\n]+?):line\s+(?P<l1>\d+))|"
                    r"(?:(?P<f2>[A-Za-z]:\\[^()\n]+?\.(?:cs|vb|fs))\((?P<l2>\d+)(?:,\d+)?\))")


def stack_links(text: str) -> list[tuple[int, int, str, int]]:
    """[(start, end, file, line)] of the source locations in a failure message / stack trace."""
    out = []
    for m in _STACK.finditer(text):
        f = m.group("f1") or m.group("f2")
        ln = int(m.group("l1") or m.group("l2"))
        g = "f1" if m.group("f1") else "f2"
        out.append((m.start(g), m.end("l1" if g == "f1" else "l2"), f.strip(), ln))
    return out


class _DetailClicks(QObject):
    def __init__(self, explorer):
        super().__init__(explorer)
        self.explorer = explorer

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.MouseButtonDblClick or (
                ev.type() == QEvent.Type.MouseButtonRelease and ev.modifiers() & Qt.KeyboardModifier.ControlModifier):
            det = self.explorer.detail
            cur = det.cursorForPosition(ev.position().toPoint())
            pos = cur.position()
            for s, e, f, ln in stack_links(det.toPlainText()):
                if s <= pos <= e:
                    open_stack_location(self.explorer.win, f, ln)
                    return True
        return False


def open_stack_location(win, file: str, line: int) -> None:
    from ...features.refactor import open_location
    if Path(file).is_file():
        open_location(win, file, max(0, line - 1))


def _patch_test_explorer() -> None:
    try:
        from ...features import test_explorer as TE
    except Exception:  # noqa: BLE001
        return
    cls = TE.TestExplorer
    if getattr(cls, "_dn_patched", False):
        return
    orig = cls._show_detail

    def _show_detail(self):
        orig(self)
        try:
            det = self.detail
            if not getattr(self, "_dn_clicks", None):
                self._dn_clicks = _DetailClicks(self)
                det.viewport().installEventFilter(self._dn_clicks)
                det.viewport().setMouseTracking(True)
            sels = []
            fmt = QTextCharFormat()
            fmt.setForeground(QColor("#1E88E5"))
            fmt.setFontUnderline(True)
            for s, e, _f, _ln in stack_links(det.toPlainText()):
                sel = QTextEdit.ExtraSelection()
                cur = det.textCursor()
                cur.setPosition(s)
                cur.setPosition(e, cur.MoveMode.KeepAnchor)
                sel.cursor = cur
                sel.format = fmt
                sels.append(sel)
            det.setExtraSelections(sels)
            if sels:
                det.setToolTip("Double-click (or Ctrl+click) a blue location to open it")
        except Exception:  # noqa: BLE001
            pass
    cls._show_detail = _show_detail
    cls._dn_patched = True


# ============================================================================ hooks into vs_ui
def _patch_vs_ui(win_ref: list) -> None:
    from ...foreign import vs_ui
    if getattr(vs_ui, "_dn_tools_patched", False):
        return
    vs_ui._dn_tools_patched = True
    orig_fill = vs_ui._fill_deps
    orig_menu = vs_ui.project_menu
    orig_sol_menu = vs_ui.solution_menu
    orig_activate = vs_ui.activate

    def _fill_deps(win, project, pi, key):
        orig_fill(win, project, pi, key)
        try:
            fill_analyzers(win, project, pi, key)
        except Exception as e:  # noqa: BLE001
            _log(win, f"*** Analyzers node: {e}")

    def project_menu(win, project, item, kind, name):
        if str(kind).startswith("dn_"):
            return analyzer_menu(win, project, item, kind, name)
        m = orig_menu(win, project, item, kind, name)
        if m is not None and kind == "project" and getattr(project, "ms", None) is not None and \
                project.ms.language != "C++":
            acts = m.actions()
            anchor = acts[-1] if acts else None
            sub = QMenu("Analyze and Code Cleanup", m)
            _analyze_items(win, sub, "project")
            m.insertMenu(anchor, sub) if anchor is not None else m.addMenu(sub)
            m.insertSeparator(anchor) if anchor is not None else None
        return m

    def solution_menu(win, sln, item):
        m = orig_sol_menu(win, sln, item)
        if m is not None:
            acts = m.actions()
            anchor = acts[-1] if acts else None
            sub = QMenu("Analyze and Code Cleanup", m)
            _analyze_items(win, sub, "solution")
            m.insertMenu(anchor, sub) if anchor is not None else m.addMenu(sub)
        return m

    def activate(win, project, item, kind, name):
        if kind == "dn_genfile":
            open_read_only(win, Path(name))
            return
        if kind in ("dn_analyzers", "dn_analyzer", "dn_generator") and item is not None:
            item.setExpanded(not item.isExpanded())
            return
        if kind in ("dn_rule", "dn_info"):
            return
        return orig_activate(win, project, item, kind, name)
    vs_ui._fill_deps = _fill_deps
    vs_ui.project_menu = project_menu
    vs_ui.solution_menu = solution_menu
    vs_ui.activate = activate


def _analyze_items(win, menu, scope: str) -> None:
    menu.addAction(f"Run Code Analysis on {'Solution' if scope == 'solution' else 'Project'}",
                   lambda: run_code_analysis(win, scope))
    menu.addAction(f"Run Code Cleanup on {'Solution' if scope == 'solution' else 'Project'}",
                   lambda: code_cleanup(win, scope))
    menu.addAction("Configure Code Analysis...", lambda: configure_code_analysis(win))
    if scope == "project":
        p = _active_vs_project(win)
        if p is not None:
            menu.addAction("Show Generated Files", lambda: show_generated_files(win, p))


# ============================================================================ menus
def _menu_named(win, name: str):
    for a in win.menuBar().actions():
        if a.text().replace("&", "") == name and a.menu() is not None:
            return a.menu()
    return None


def _build_analyze_menu(win) -> None:
    if getattr(win, "analyze_menu", None) is not None:
        return
    mb = win.menuBar()
    tools = next((a for a in mb.actions() if a.text().replace("&", "") == "Tools"), None)
    menu = QMenu("Analy&ze", win)
    if tools is not None:
        mb.insertMenu(tools, menu)
    else:
        mb.addMenu(menu)
    win.analyze_menu = menu

    def A(parent, text, slot, shortcut=None):
        a = QAction(text, win)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
            a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        a.triggered.connect(slot)
        parent.addAction(a)
        return a
    rca = menu.addMenu("Run Code &Analysis")
    win.a_dn_analysis = A(rca, "On &Solution", lambda: run_code_analysis(win, "solution"), "Alt+F11")
    A(rca, "On Current &Project", lambda: run_code_analysis(win, "project"))
    cc = menu.addMenu("Code &Cleanup")
    win.a_dn_cleanup = A(cc, "Run Code Cleanup on &Document", lambda: code_cleanup(win, "document"), "Ctrl+K, Ctrl+E")
    A(cc, "Run Code Cleanup on &Project", lambda: code_cleanup(win, "project"))
    A(cc, "Run Code Cleanup on &Solution", lambda: code_cleanup(win, "solution"))
    cc.addSeparator()
    A(cc, "&Configure Code Cleanup...", lambda: configure_code_cleanup(win))
    A(menu, "Configure Code Analysis (.&editorconfig)...", lambda: configure_code_analysis(win))
    menu.addSeparator()
    win.a_dn_usings = A(menu, "Remove and Sort &Usings", lambda: remove_and_sort_usings(win), "Ctrl+R, Ctrl+G")
    A(menu, "Go To &Decompiled Definition", lambda: goto_decompiled_definition(win))
    A(menu, "Decompile Assembly...", lambda: decompile_assembly_dialog(win))
    menu.addSeparator()
    A(menu, "Show Generated Files (Source Generators)",
      lambda: (_active_vs_project(win) and show_generated_files(win, _active_vs_project(win))) or None)
    edit = _menu_named(win, "Edit")
    if edit is not None:
        sub = edit.addMenu("IntelliSense")
        sub.addAction("Remove and Sort Usings\tCtrl+R, Ctrl+G", lambda: remove_and_sort_usings(win))
        sub.addAction("Sort Usings", lambda: _sort_only(win))


def _sort_only(win) -> None:
    ed = _current_editor(win)
    p = _editor_path(ed)
    if ed is None or p is None:
        return
    from ... import editkit
    ec = EC.effective(p)
    new = cleanup.sort_usings_text(ed.text(), ec.get("dotnet_sort_system_directives_first", "true") != "false")
    if new != ed.text():
        editkit.apply_text(ed, new)


def _install_error_list(win) -> None:
    el = getattr(win, "error_list", None)
    if el is None:
        return
    if el.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
        el.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    el.customContextMenuRequested.connect(
        lambda pos: (lambda m: m.exec(el.viewport().mapToGlobal(pos)) if m is not None and not OFFSCREEN else None)(
            error_list_menu(win, pos)))
    providers = win.__dict__.setdefault("diag_providers", [])
    providers.append(_diag_provider)


def _install_editor(win) -> None:
    from ... import editkit
    from ...features import refactor
    if quick_action_provider not in refactor.EXTRA_QUICK_ACTIONS:
        refactor.EXTRA_QUICK_ACTIONS.append(quick_action_provider)

    def editor_options(ed):
        try:
            if ed.window() is not win:
                return
            p = _editor_path(ed)
            if p is None or not EC.files_for(p):
                return
            opts = EC.editor_options(p)
            js = {k: v for k, v in opts.items() if k in ("tabSize", "insertSpaces", "indentSize")}
            if js:
                import json
                ed._js(f"try {{ radEditor.getModel().updateOptions({json.dumps(js)}); }} catch (e) {{}}")
                ed._dn_editorconfig = js
        except Exception:  # noqa: BLE001
            pass

    def on_menu(menu, ed):
        p = _editor_path(ed)
        if p is None or p.suffix.lower() not in DOTNET_EXTS:
            return
        menu.addSeparator()
        menu.addAction("Go To Decompiled Definition", lambda: goto_decompiled_definition(win, ed))
        menu.addAction("Remove and Sort Usings\tCtrl+R, Ctrl+G", lambda: remove_and_sort_usings(win, ed))
        menu.addAction("Run Code Cleanup\tCtrl+K, Ctrl+E", lambda: code_cleanup(win, "document"))

    def ready(ed):
        editor_options(ed)
        try:
            if ed.window() is win:
                ed.contextMenuAboutToShow.connect(lambda m, e=ed: on_menu(m, e))
        except Exception:  # noqa: BLE001
            pass
    editkit.READY.append(ready)
    editkit.COMMANDS["dnUsings"] = lambda ed, _l, _c: remove_and_sort_usings(win, ed)
    editkit.COMMANDS["dnCleanup"] = lambda ed, _l, _c: code_cleanup(win, "document")
    K = "monaco.KeyMod"
    try:
        editkit.add_action("radx.dnUsings", "Remove and Sort Usings",
                           f"[{K}.chord({K}.CtrlCmd | monaco.KeyCode.KeyR, {K}.CtrlCmd | monaco.KeyCode.KeyG)]",
                           "dnUsings", "")
        editkit.add_action("radx.dnCleanup", "Run Code Cleanup",
                           f"[{K}.chord({K}.CtrlCmd | monaco.KeyCode.KeyK, {K}.CtrlCmd | monaco.KeyCode.KeyE)]",
                           "dnCleanup", "")
    except Exception:  # noqa: BLE001
        pass


def install(win) -> None:
    try:
        from . import testing
        testing.install()
    except Exception as e:  # noqa: BLE001
        _log(win, f"*** .NET test adapter: {e}")
    _patch_test_explorer()
    _patch_vs_ui([win])
    try:
        win.solution.itemExpanded.connect(lambda it: _on_expand(win, it))
    except Exception:  # noqa: BLE001
        pass
    QTimer.singleShot(0, lambda: _build_analyze_menu(win))
    _install_error_list(win)
    _install_editor(win)
    win.dotnet_tools = __import__(__name__, fromlist=["install"])


__all__ = ["install", "fill_analyzers", "load_analyzers", "populate_analyzers", "configure_code_analysis",
           "EditorConfigDialog", "code_cleanup", "remove_and_sort_usings", "run_code_analysis", "error_list_menu",
           "configure_severity", "suppress_in_source", "suppress_in_file", "quick_action_provider", "apply_fix",
           "goto_decompiled_definition", "open_decompiled", "debug_tests", "stack_links", "run_process",
           "set_rule_severity", "show_generated_files", "in_thread"]
