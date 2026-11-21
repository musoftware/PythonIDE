"""Test Explorer (Test > Test Explorer, Ctrl+E, T) - discover, run and debug unit tests, with code coverage.

Every framework of radide/testing is found automatically in the active project's folder: Python pytest /
unittest, Jest / Vitest / node --test, go test, cargo test, dotnet test, PHPUnit, dart/flutter test, JUnit 5,
Ring and VB test conventions. The tree shows file > class/group > test with a coloured state and the
duration; the lower pane shows the failure message and output of the selected test, the whole run log and a
coverage summary. Double-click a test to open it at its line. Python tests can be debugged (debugpy:
breakpoints in the test and the code under test). "Run with Coverage" colours the editor's gutter
(green covered, red not covered, amber partly covered branches).
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QKeySequence, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QComboBox, QDockWidget, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu,
                             QPlainTextEdit, QSplitter, QTabWidget, QToolBar, QToolButton, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import editkit, testing
from .. import theme as _theme

ROLE = Qt.ItemDataRole.UserRole
STATE_TEXT = {"passed": "Passed", "failed": "Failed", "error": "Error", "skipped": "Skipped",
              "running": "Running", "unknown": "Not run"}


# ============================================================================ icons
def _col(token, fallback):
    try:
        return QColor(_theme.color(token))
    except Exception:  # noqa: BLE001
        return QColor(fallback)


def state_icon(state: str, size=14) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = {"passed": _col("success", "#087F23"), "failed": _col("error", "#C42B1C"), "error": _col("error", "#C42B1C"),
         "skipped": _col("note", "#806000"), "running": _col("accent", "#316AC5")}.get(state, _col("muted", "#888"))
    p.setPen(QPen(c, 1.4))
    p.setBrush(QBrush(c) if state in ("passed", "failed", "error", "running") else Qt.BrushStyle.NoBrush)
    p.drawEllipse(2, 2, size - 4, size - 4)
    p.setPen(QPen(QColor("#FFFFFF"), 1.6))
    if state == "passed":
        p.drawPolyline(*[_pt(x, y) for x, y in ((4.2, 7.2), (6.2, 9.4), (10, 4.8))])
    elif state in ("failed", "error"):
        p.drawLine(_pt(5, 5), _pt(9, 9))
        p.drawLine(_pt(9, 5), _pt(5, 9))
    elif state == "skipped":
        p.setPen(QPen(c, 1.6))
        p.drawLine(_pt(4.5, 7), _pt(9.5, 7))
    p.end()
    return QIcon(pm)


def _pt(x, y):
    from PyQt6.QtCore import QPointF
    return QPointF(x, y)


def tool_icon(kind: str, size=16) -> QIcon:
    """Small drawn icons (run all, run, run failed, debug, coverage, stop, refresh, flask)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    green, red, blue = _col("success", "#087F23"), _col("error", "#C42B1C"), _col("accent", "#316AC5")
    text = _col("text", "#000000")
    from PyQt6.QtGui import QPolygonF

    def tri(x, c):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawPolygon(QPolygonF([_pt(x, 3), _pt(x + 8, 8), _pt(x, 13)]))
    if kind == "runall":
        tri(1, green)
        tri(7, green)
    elif kind == "run":
        tri(4, green)
    elif kind == "runfailed":
        tri(2, green)
        p.setPen(QPen(red, 2))
        p.drawLine(_pt(10, 9), _pt(15, 14))
        p.drawLine(_pt(15, 9), _pt(10, 14))
    elif kind == "debug":
        p.setPen(QPen(text, 1.3))
        p.setBrush(_col("note", "#806000"))
        p.drawEllipse(4, 5, 8, 9)
        p.drawLine(_pt(8, 5), _pt(8, 14))
        for y in (7, 10, 13):
            p.drawLine(_pt(2, y), _pt(4.5, y))
            p.drawLine(_pt(11.5, y), _pt(14, y))
    elif kind == "coverage":
        p.setPen(Qt.PenStyle.NoPen)
        for i, c in enumerate((green, green, red, green)):
            p.setBrush(c)
            p.drawRect(2, 2 + i * 3, 3, 2)
            p.setBrush(_col("muted", "#888"))
            p.drawRect(7, 2 + i * 3, 7 - (i % 2) * 3, 2)
    elif kind == "stop":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(red)
        p.drawRect(3, 3, 10, 10)
    elif kind == "refresh":
        p.setPen(QPen(blue, 2))
        p.drawArc(3, 3, 10, 10, 30 * 16, 290 * 16)
        p.setBrush(blue)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygonF([_pt(10, 1), _pt(15, 4), _pt(10, 7)]))
    elif kind == "flask":
        p.setPen(QPen(text, 1.3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(QPolygonF([_pt(6, 2), _pt(10, 2), _pt(10, 6), _pt(14, 14), _pt(2, 14), _pt(6, 6)]))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(green)
        p.drawPolygon(QPolygonF([_pt(4.2, 10.5), _pt(11.8, 10.5), _pt(13, 13.2), _pt(3, 13.2)]))
    p.end()
    return QIcon(pm)


def _fmt_dur(d) -> str:
    if d is None:
        return ""
    if d < 0.001:
        return "< 1 ms"
    if d < 1:
        return f"{d * 1000:.0f} ms"
    return f"{d:.2f} s"


class _Sig(QObject):
    discovered = pyqtSignal(object, object, object)      # token, items|None, error text


# ============================================================================ the panel
class TestExplorer(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.root: Path | None = None
        self.adapters: list = []
        self.items: dict[str, testing.TestItem] = {}      # key -> item (key = adapter id + "|" + item id)
        self.nodes: dict[str, QTreeWidgetItem] = {}
        self.coverage: dict[str, testing.FileCoverage] = {}
        self.show_cov = True
        self._sig = _Sig()
        self._sig.discovered.connect(self._on_discovered)
        self._token = 0
        self.discovering = False
        self._proc: QProcess | None = None
        self._queue: list = []
        self._run_log = ""
        self._step_out = ""
        self._run = None
        self._t0 = 0.0
        self._build()
        _theme.changed.connect(lambda *_a: self._retheme())

    # ---------------------------------------------------------------- UI
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        tb = QToolBar()
        tb.setIconSize(QSize(16, 16))
        self.tb = tb

        def act(kind, text, slot, tip):
            a = QAction(tool_icon(kind), text, self)
            a.setToolTip(tip)
            a.triggered.connect(slot)
            a.setData(kind)
            tb.addAction(a)
            return a
        self.a_run_all = act("runall", "Run All", lambda: self.run(None), "Run All Tests (Ctrl+R, A)")
        self.a_run_sel = act("run", "Run", self.run_selected, "Run Selected Tests")
        self.a_run_failed = act("runfailed", "Run Failed", self.run_failed, "Run Failed Tests")
        self.a_debug = act("debug", "Debug", self.debug_selected, "Debug Selected Test (Python: debugpy)")
        self.a_cov = act("coverage", "Coverage", lambda: self.run(self._selected_or_none(), coverage=True),
                         "Run Selected (or All) Tests with Code Coverage")
        tb.addSeparator()
        self.a_stop = act("stop", "Stop", self.stop, "Stop the test run")
        self.a_refresh = act("refresh", "Refresh", lambda: self.discover(force=True), "Discover tests again")
        self.a_stop.setEnabled(False)
        lay.addWidget(tb)

        row = QHBoxLayout()
        row.setContentsMargins(4, 0, 4, 0)
        self.filter = QLineEdit(placeholderText="Search tests")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        self.state_filter = QComboBox()
        for t, d in (("All", ""), ("Failed", "failed"), ("Passed", "passed"), ("Not run", "unknown"),
                     ("Skipped", "skipped")):
            self.state_filter.addItem(t, d)
        self.state_filter.currentIndexChanged.connect(self._apply_filter)
        row.addWidget(self.filter, 1)
        row.addWidget(self.state_filter)
        lay.addLayout(row)
        self.summary = QLabel("")
        self.summary.setContentsMargins(6, 0, 6, 0)
        self.summary.setWordWrap(True)
        lay.addWidget(self.summary)

        split = QSplitter(Qt.Orientation.Vertical)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Test", "Duration"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setStretchLastSection(False)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.itemDoubleClicked.connect(self._open_item)
        self.tree.currentItemChanged.connect(lambda *_a: self._show_detail())
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        split.addWidget(self.tree)
        self.tabs = QTabWidget()
        self.detail = QPlainTextEdit(readOnly=True)
        self.detail.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log = QPlainTextEdit(readOnly=True)
        self.log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log.setMaximumBlockCount(20000)
        self.cov_tree = QTreeWidget()
        self.cov_tree.setHeaderLabels(["File", "Covered", "Lines", "Missed", "%"])
        self.cov_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3, 4):
            self.cov_tree.header().setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.cov_tree.header().setStretchLastSection(False)
        self.cov_tree.setRootIsDecorated(False)
        self.cov_tree.itemDoubleClicked.connect(self._open_cov)
        cov_box = QWidget()
        cl = QVBoxLayout(cov_box)
        cl.setContentsMargins(0, 0, 0, 0)
        crow = QHBoxLayout()
        self.cov_label = QLabel("Run with Coverage to measure which lines the tests execute.")
        self.cov_label.setWordWrap(True)
        self.cov_toggle = QToolButton()
        self.cov_toggle.setText("Show colours in the editor")
        self.cov_toggle.setCheckable(True)
        self.cov_toggle.setChecked(True)
        self.cov_toggle.toggled.connect(self.set_show_coverage)
        crow.addWidget(self.cov_toggle)
        crow.addStretch(1)
        cl.addWidget(self.cov_label)
        cl.addLayout(crow)
        cl.addWidget(self.cov_tree, 1)
        for f in (self.detail, self.log):
            from PyQt6.QtGui import QFont
            f.setFont(QFont("Consolas", 9))
        self.tabs.addTab(self.detail, "Test Detail")
        self.tabs.addTab(self.log, "Output")
        self.tabs.addTab(cov_box, "Coverage")
        split.addWidget(self.tabs)
        split.setSizes([320, 200])
        lay.addWidget(split, 1)
        self._update_summary()

    def _retheme(self):
        for a in self.tb.actions():
            if a.data():
                a.setIcon(tool_icon(a.data()))
        for key, node in self.nodes.items():
            it = self.items.get(key)
            if it is not None:
                node.setIcon(0, state_icon(it.state))
        self._refresh_groups()
        if self.coverage and self.show_cov:
            self._push_coverage()

    # ---------------------------------------------------------------- discovery
    def project_root(self) -> Path | None:
        p = getattr(self.win, "project", None)
        if p is None:
            return None
        folder = Path(p.folder)
        if (folder / "Cargo.toml").is_file():     # a cargo workspace member: test the whole workspace
            try:
                from ..rust_tools import workspace_root
                return workspace_root(folder)
            except Exception:  # noqa: BLE001
                return folder
        return folder

    def discover(self, force=False):
        root = self.project_root()
        if root is None:
            self.tree.clear()
            self.items.clear()
            self.nodes.clear()
            self.summary.setText("Open a project to see its tests.")
            return
        if not force and root == self.root and self.items:
            return
        self.root = root
        self._token += 1
        token = self._token
        self.discovering = True
        self.summary.setText("Discovering tests...")
        win = self.win

        def work():
            items, errs = [], []
            try:
                adapters = testing.adapters_for(root, win)
            except Exception as e:  # noqa: BLE001
                adapters, errs = [], [str(e)]
            for a in adapters:
                ok, hint = a.available()
                if not ok:
                    errs.append(f"{a.name}: {hint}")
                    continue
                try:
                    found = a.discover()
                except Exception as e:  # noqa: BLE001
                    errs.append(f"{a.name}: {e}")
                    continue
                for it in found:
                    it.framework = a.id
                items.append((a, found, hint))
            self._sig.discovered.emit(token, items, "\n".join(errs))
        threading.Thread(target=work, daemon=True).start()

    def _on_discovered(self, token, groups, errors):
        if token != self._token:
            return
        self.discovering = False
        old_states = {k: (it.state, it.duration, it.message, it.output) for k, it in self.items.items()}
        selected = set(self._selected_keys())
        current = self.tree.currentItem()
        current = current.data(0, ROLE) if current is not None else None
        self.adapters = [a for a, _f, _h in groups]
        self.items.clear()
        self.nodes.clear()
        self.tree.clear()
        notes = []
        for a, found, hint in groups:
            if hint:
                notes.append(f"{a.name}: {hint}")
            for it in found:
                key = f"{a.id}|{it.id}"
                if key in old_states and it.state == "unknown":
                    it.state, it.duration, it.message, it.output = old_states[key]
                self.items[key] = it
                self._add_node(key, it, a)
        self._refresh_groups()
        self.tree.expandToDepth(1 if len(self.adapters) > 1 else 0)
        for k in selected:                        # keep the selection over a refresh
            if k in self.nodes:
                self.nodes[k].setSelected(True)
        if current and current[0] == "test" and current[1] in self.nodes:
            self.tree.setCurrentItem(self.nodes[current[1]], 0,
                                     self.tree.selectionModel().SelectionFlag.NoUpdate)
        if errors:
            notes.append(errors)
        if notes:
            self.log.appendPlainText("\n".join(notes))
        if not self.items:
            self.summary.setText("No tests found." + (" " + errors.splitlines()[0] if errors else
                                 " Python: test_*.py (pytest/unittest) - JS: *.test.js - Go: *_test.go - "
                                 "C#: [Fact]/[Test] - PHP: *Test.php - Dart: test/*_test.dart - Java: @Test - "
                                 "Ring: test_*.ring with func test_* - VB: Test*.bas with Sub Test*()"))
        else:
            self._update_summary()
        self._apply_filter()

    def _group_node(self, key: str, text: str, parent: QTreeWidgetItem | None, tip="", data=None):
        node = self.nodes.get(key)
        if node is None:
            node = QTreeWidgetItem([text, ""])
            node.setData(0, ROLE, data or ("group", key))
            node.setToolTip(0, tip or text)
            if parent is None:
                self.tree.addTopLevelItem(node)
            else:
                parent.addChild(node)
            self.nodes[key] = node
        return node

    def _add_node(self, key, it, adapter):
        parent = None
        if len(self.adapters) > 1:
            parent = self._group_node(f"fw:{adapter.id}", adapter.name, None)
        if it.file:
            rel_ = testing.rel(self.root, it.file) if self.root else Path(it.file).name
            parent = self._group_node(f"file:{adapter.id}:{it.file}", rel_, parent, it.file,
                                      ("file", it.file))
        if it.suite and (not it.file or it.suite not in (testing.rel(self.root, it.file), Path(it.file).name)):
            parent = self._group_node(f"suite:{adapter.id}:{it.file}:{it.suite}", it.suite, parent)
        node = QTreeWidgetItem([it.name, _fmt_dur(it.duration)])
        node.setData(0, ROLE, ("test", key))
        node.setIcon(0, state_icon(it.state))
        node.setToolTip(0, it.id)
        if parent is None:
            self.tree.addTopLevelItem(node)
        else:
            parent.addChild(node)
        self.nodes[key] = node

    def _leaf_keys(self, node) -> list[str]:
        data = node.data(0, ROLE)
        if data and data[0] == "test":
            return [data[1]]
        out = []
        for i in range(node.childCount()):
            out += self._leaf_keys(node.child(i))
        return out

    def _refresh_groups(self):
        def walk(node):
            data = node.data(0, ROLE)
            if data and data[0] == "test":
                it = self.items[data[1]]
                return [it.state], (it.duration or 0.0)
            states, total = [], 0.0
            for i in range(node.childCount()):
                s, d = walk(node.child(i))
                states += s
                total += d
            agg = ("failed" if any(s in ("failed", "error") for s in states) else
                   "running" if "running" in states else
                   "passed" if states and all(s in ("passed", "skipped") for s in states) and "passed" in states else
                   "skipped" if states and all(s == "skipped" for s in states) else "unknown")
            node.setIcon(0, state_icon(agg))
            n = len(states)
            base = node.text(0).split("  (")[0]
            node.setText(0, f"{base}  ({n})")
            node.setText(1, _fmt_dur(total) if total else "")
            return states, total
        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))

    def _update_summary(self, elapsed: float | None = None):
        c = {"passed": 0, "failed": 0, "skipped": 0, "unknown": 0}
        for it in self.items.values():
            k = "failed" if it.state in ("failed", "error") else it.state if it.state in c else "unknown"
            c[k] += 1
        ok, bad, note, muted = (_theme.color(t) for t in ("success", "error", "note", "muted"))
        parts = [f"<b>{len(self.items)}</b> tests", f"<span style='color:{ok}'>✔ {c['passed']} passed</span>",
                 f"<span style='color:{bad}'>✖ {c['failed']} failed</span>"]
        if c["skipped"]:
            parts.append(f"<span style='color:{note}'>○ {c['skipped']} skipped</span>")
        if c["unknown"]:
            parts.append(f"<span style='color:{muted}'>{c['unknown']} not run</span>")
        if elapsed is not None:
            parts.append(f"{elapsed:.2f} s")
        self.summary.setText(" &nbsp; ".join(parts))
        self.counts = c

    def _apply_filter(self):
        text = self.filter.text().strip().lower()
        want = self.state_filter.currentData() or ""

        def walk(node) -> bool:
            data = node.data(0, ROLE)
            if data and data[0] == "test":
                it = self.items[data[1]]
                st = "failed" if it.state == "error" else it.state
                vis = (not text or text in it.name.lower() or text in it.id.lower()) and (not want or st == want)
            else:
                vis = False
                for i in range(node.childCount()):
                    vis = walk(node.child(i)) or vis
            node.setHidden(not vis)
            return vis
        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))

    # ---------------------------------------------------------------- selection helpers
    def _selected_keys(self) -> list[str]:
        keys = []
        for node in self.tree.selectedItems():
            for k in self._leaf_keys(node):
                if k not in keys:
                    keys.append(k)
        return keys

    def _selected_or_none(self):
        keys = self._selected_keys()
        return keys or None

    def run_selected(self):
        keys = self._selected_keys()
        if not keys:
            self.win.statusBar().showMessage("Select tests in the Test Explorer first (or use Run All)", 4000)
            return
        self.run(keys)

    def run_failed(self):
        keys = [k for k, it in self.items.items() if it.state in ("failed", "error")]
        if not keys:
            self.win.statusBar().showMessage("No failed tests", 3000)
            return
        self.run(keys)

    # ---------------------------------------------------------------- running
    def running(self) -> bool:
        return self._proc is not None and self._proc.state() != QProcess.ProcessState.NotRunning

    def run(self, keys=None, coverage=False):
        """keys None = every test. Several frameworks run one after the other."""
        if self.running():
            return
        if self.root is None or self.root != self.project_root():
            self.discover(force=True)
            QTimer.singleShot(300, lambda: self._wait_then(lambda: self.run(keys, coverage)))
            return
        try:
            self.win.save_all()
        except Exception:  # noqa: BLE001
            pass
        jobs = []
        for a in self.adapters:
            if keys is None:
                sel = None
            else:
                sel = [self.items[k] for k in keys if k in self.items and k.startswith(a.id + "|")]
                if not sel:
                    continue
            if coverage and not a.supports_coverage:
                self.log.appendPlainText(f"({a.name}: coverage is not supported - running without it)")
            jobs.append((a, sel, coverage and a.supports_coverage))
        if not jobs:
            return
        self.log.clear()
        self.tabs.setCurrentWidget(self.log)
        for k, it in self.items.items():
            if keys is None or k in keys:
                it.state, it.duration, it.message, it.output = "running", None, "", ""
                n = self.nodes.get(k)
                if n is not None:
                    n.setIcon(0, state_icon("running"))
                    n.setText(1, "")
        self._refresh_groups()
        self._jobs = jobs
        self._run_keys = keys
        self._t0 = time.perf_counter()
        self._cov_new = {}
        self._set_running(True)
        self._next_job()

    def _wait_then(self, fn, tries=60):
        if self.items or tries <= 0:
            fn()
        else:
            QTimer.singleShot(250, lambda: self._wait_then(fn, tries - 1))

    def _set_running(self, on):
        for a in (self.a_run_all, self.a_run_sel, self.a_run_failed, self.a_debug, self.a_cov, self.a_refresh):
            a.setEnabled(not on)
        self.a_stop.setEnabled(on)
        if on:
            self.summary.setText("Running tests...")

    def _next_job(self):
        if not self._jobs:
            self._finish_run()
            return
        a, sel, cov = self._jobs.pop(0)
        if isinstance(a, testing.JavaAdapter) and not (a.root / "pom.xml").exists():
            if not a.ensure_jar(self.log.appendPlainText):
                self._mark_unreported(a, sel, "the JUnit console launcher could not be downloaded")
                self._next_job()
                return
        try:
            plan = a.plan(sel, coverage=cov)
        except Exception as e:  # noqa: BLE001
            self._mark_unreported(a, sel, f"cannot run: {e}")
            self._next_job()
            return
        self._run = (a, sel, plan)
        self._queue = list(plan.steps)
        self._run_log = ""
        self._next_step()

    def _next_step(self):
        if not self._queue:
            self._job_done()
            return
        step = self._queue.pop(0)
        self.log.appendPlainText(f"> {' '.join(str(x) for x in step.argv)}")
        proc = QProcess(self)
        proc.setWorkingDirectory(str(step.cwd))
        env = QProcessEnvironment.systemEnvironment()
        for k, v in (step.env or {}).items():
            env.insert(k, str(v))
        proc.setProcessEnvironment(env)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda p=proc: self._read(p))
        proc.finished.connect(lambda code, _st, p=proc: self._step_finished(p, code))
        proc.errorOccurred.connect(lambda err, p=proc: self._step_error(p, err))
        self._proc = proc
        self._step_out = ""
        proc.start(str(step.argv[0]), [str(x) for x in step.argv[1:]])

    def _read(self, proc):
        text = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace").replace("\r\n", "\n")
        self._run_log += text
        self._step_out += text
        visible = "\n".join(l for l in text.split("\n") if testing.MARK not in l)
        if visible:
            self.log.moveCursor(self.log.textCursor().MoveOperation.End)
            self.log.insertPlainText(visible)

    def _step_error(self, proc, err):
        if err == QProcess.ProcessError.FailedToStart:
            self.log.appendPlainText(f"*** could not start {proc.program()}")
            self._step_finished(proc, -1)

    def _step_finished(self, proc, code):
        if proc is not self._proc or getattr(proc, "_rad_done", False):
            return
        proc._rad_done = True
        self._read(proc)
        self.log.appendPlainText(f"(exit code {code})")
        if getattr(self, "_stopping", False):
            self._queue.clear()
            self._jobs = []
        elif code != 0 and self._queue and self._run is not None and \
                isinstance(self._run[0], testing.JavaAdapter) and "javac" in proc.program().lower():
            self._queue.clear()                    # compile error: no test step
        QTimer.singleShot(0, self._next_step)

    def _job_done(self):
        a, sel, plan = self._run
        try:
            results = plan.parse(self._run_log)
        except Exception as e:  # noqa: BLE001
            results = []
            self.log.appendPlainText(f"*** cannot read the results: {e}")
        mine = [it for k, it in self.items.items() if k.startswith(a.id + "|")]
        pairs, rest = testing.match_results(mine, results, a.root)
        seen = set()
        by_item: dict[int, list] = {}
        for it, r in pairs:
            by_item.setdefault(id(it), []).append((it, r))
        for lst in by_item.values():
            it = lst[0][0]
            states = [r.state for _i, r in lst]
            it.state = ("failed" if "failed" in states else "error" if "error" in states else
                        "passed" if "passed" in states else states[0])
            durs = [r.duration for _i, r in lst if r.duration is not None]
            it.duration = sum(durs) if durs else None
            it.message = "\n\n".join(r.message for _i, r in lst if r.message)
            it.output = "\n".join(r.output for _i, r in lst if r.output)
            if lst[0][1].line and not it.line:
                it.line = lst[0][1].line
            seen.add(f"{a.id}|{it.id}")
        for r in rest:                                    # tests found only by running (parametrized, subtests)
            if not r.id and not r.name:
                continue
            it = testing.TestItem(id=r.id or r.name, name=r.name or r.id.split("::")[-1], file=r.file, line=r.line,
                                  framework=a.id, state=r.state, duration=r.duration, message=r.message,
                                  output=r.output)
            key = f"{a.id}|{it.id}"
            self.items[key] = it
            self._add_node(key, it, a)
            seen.add(key)
        self._mark_unreported(a, sel, "no result (see the Output tab)", seen)
        for k in seen:
            n = self.nodes.get(k)
            it = self.items[k]
            if n is not None:
                n.setIcon(0, state_icon(it.state))
                n.setText(1, _fmt_dur(it.duration))
        try:
            cov = plan.coverage()
        except Exception as e:  # noqa: BLE001
            cov = {}
            self.log.appendPlainText(f"*** cannot read the coverage: {e}")
        if cov:
            self._cov_new.update(cov)
        self._next_job()

    def _mark_unreported(self, a, sel, why, seen=()):
        keys = [f"{a.id}|{i.id}" for i in sel] if sel else [k for k in self.items if k.startswith(a.id + "|")]
        tail = "\n".join(self._run_log.strip().splitlines()[-30:]) if self._run_log else ""
        for k in keys:
            if k in seen or k not in self.items:
                continue
            it = self.items[k]
            if it.state == "running":
                if getattr(self, "_stopping", False):
                    it.state, it.message = "unknown", "stopped"
                else:
                    it.state = "error"
                    it.message = f"{why}\n\n{tail}"
                n = self.nodes.get(k)
                if n is not None:
                    n.setIcon(0, state_icon(it.state))

    def _finish_run(self):
        self._proc = None
        self._stopping = False
        self._set_running(False)
        for it in self.items.values():
            if it.state == "running":
                it.state = "unknown"
        self._refresh_groups()
        elapsed = time.perf_counter() - self._t0
        self._update_summary(elapsed)
        self._apply_filter()
        if self._cov_new:
            self.coverage = self._cov_new
            self._fill_coverage()
            self._push_coverage()
            self.tabs.setCurrentIndex(2)
        failed = self.counts.get("failed", 0)
        msg = (f"Tests: {self.counts['passed']} passed, {failed} failed" +
               (f", {self.counts['skipped']} skipped" if self.counts.get("skipped") else "") + f" ({elapsed:.1f} s)")
        self.win.statusBar().showMessage(msg, 8000)
        try:
            self.win.log(f"[tests] {msg}")
        except Exception:  # noqa: BLE001
            pass
        # select the first failed test so its message shows
        if failed:
            for k, it in self.items.items():
                if it.state in ("failed", "error") and k in self.nodes:
                    self.tree.setCurrentItem(self.nodes[k])
                    if not self._cov_new:
                        self.tabs.setCurrentIndex(0)
                    break
        self._show_detail()
        self.finished_run = True

    def stop(self):
        if self.running():
            self._stopping = True
            self._proc.kill()

    # ---------------------------------------------------------------- details / navigation
    def _show_detail(self):
        node = self.tree.currentItem()
        if node is None:
            return
        data = node.data(0, ROLE)
        if not data or data[0] != "test":
            keys = self._leaf_keys(node)
            failed = [self.items[k] for k in keys if self.items[k].state in ("failed", "error")]
            self.detail.setPlainText(f"{node.text(0)}\n{len(keys)} test(s), {len(failed)} failed" +
                                     "".join(f"\n  ✖ {it.name}" for it in failed))
            return
        it = self.items[data[1]]
        lines = [f"{it.name}", f"{STATE_TEXT.get(it.state, it.state)}" + (f"  ({_fmt_dur(it.duration)})"
                                                                          if it.duration is not None else ""),
                 f"Id: {it.id}"]
        if it.file:
            lines.append(f"Source: {it.file}" + (f" line {it.line}" if it.line else ""))
        if it.message:
            lines += ["", "Message:", it.message]
        if it.output:
            lines += ["", "Output:", it.output]
        self.detail.setPlainText("\n".join(lines))

    def _open_item(self, node, _col=0):
        data = node.data(0, ROLE)
        if not data:
            return
        if data[0] == "test":
            it = self.items[data[1]]
            if it.file:
                from .refactor import open_location
                open_location(self.win, it.file, max(0, (it.line or 1) - 1))
        elif data[0] == "file":
            from .refactor import open_location
            open_location(self.win, data[1], 0)

    def _menu(self, pos):
        node = self.tree.itemAt(pos)
        m = QMenu(self)
        m.addAction(tool_icon("run"), "Run", self.run_selected)
        dbg = m.addAction(tool_icon("debug"), "Debug", self.debug_selected)
        dbg.setEnabled(self._can_debug())
        m.addAction(tool_icon("coverage"), "Run with Coverage", lambda: self.run(self._selected_or_none(), True))
        m.addSeparator()
        if node is not None:
            m.addAction("Go to Test", lambda: self._open_item(node))
        m.addAction("Copy Details", lambda: __import__("PyQt6.QtWidgets", fromlist=["QApplication"])
                    .QApplication.clipboard().setText(self.detail.toPlainText()))
        m.exec(self.tree.viewport().mapToGlobal(pos))

    # ---------------------------------------------------------------- debug
    def _can_debug(self) -> bool:
        keys = self._selected_keys()
        return bool(keys) and all(k.startswith("python|") for k in keys)

    def debug_selected(self):
        keys = self._selected_keys()
        if not keys:
            self.win.statusBar().showMessage("Select the test to debug", 4000)
            return
        if not all(k.startswith("python|") for k in keys):
            self.win.statusBar().showMessage("Debug Test works for Python tests (debugpy); run the others", 6000)
            return
        a = next((x for x in self.adapters if x.id == "python"), None)
        if a is None:
            return
        win = self.win
        if win.session is not None and win.session.running():
            win.statusBar().showMessage("A program is already running (Debug > Stop first)", 5000)
            return
        try:
            win.save_all()
        except Exception:  # noqa: BLE001
            pass
        plan = a.plan([self.items[k] for k in keys], debug=True)
        from ..dap import DapSession
        bps = []
        try:
            win._sync_breakpoints()
        except Exception:  # noqa: BLE001
            pass
        for f, ln, *rest in getattr(win, "_all_breakpoints", lambda: [])():
            bps.append((f, ln, *(rest[:1])))
        bps += self._editor_breakpoints()
        import os
        env = dict(os.environ)
        env.update(plan.debug_env)
        s = DapSession("debugpy", plan.debug_program, plan.debug_args, a.root.resolve(), env, bps, win)
        s.launch_args["python"] = [plan.debug_python]
        s.launch_args["justMyCode"] = True
        s.launch_args["purpose"] = ["debug-test"]
        s.break_on_exception = False
        win.output.clear()
        win.log(f"------ Debug test: {', '.join(self.items[k].name for k in keys)} ------")
        s.output.connect(win._append_output)
        s.stopped.connect(win._on_stopped)
        s.resumed.connect(win._on_resumed)
        s.evalResult.connect(lambda txt: win.immediate.show_result(txt))
        s.failed.connect(lambda err: win.log(f"*** Error: {err}"))
        self._debug_keys = keys
        self._debug_plan = plan

        def finished(code):
            win._on_finished(code)
            keys[:] = [k for k in keys if k in self.items]      # a refresh may have run meanwhile
            self._run = (a, [self.items[k] for k in keys], plan)
            self._run_log = ""
            for k in keys:
                self.items[k].state = "running"
            self._jobs = []
            self._cov_new = {}
            self._t0 = time.perf_counter()
            self._job_done()
        s.finished.connect(finished)
        win.session = s
        s.start()
        win.statusBar().showMessage("Debugging test...")
        try:
            win._update_actions()
        except Exception:  # noqa: BLE001
            pass
        self.debug_session = s

    def _editor_breakpoints(self) -> list:
        """Breakpoints set in test files opened outside the project's own forms/modules (tests/ folder)."""
        out = []
        for ed in editkit.all_monaco_editors():
            try:
                if ed.window() is not self.win:
                    continue
                for ln in ed.breakpoints():
                    out.append((str(Path(ed.path).resolve()), ln + 1))
            except Exception:  # noqa: BLE001
                continue
        return out

    # ---------------------------------------------------------------- coverage
    def _fill_coverage(self):
        self.cov_tree.clear()
        tot_c = tot_s = 0
        root = self.root
        ok, bad, note = _col("success", "#087F23"), _col("error", "#C42B1C"), _col("note", "#806000")
        for path, fc in sorted(self.coverage.items()):
            n = fc.statements
            c = len(fc.covered)
            tot_c += c
            tot_s += n
            pct = fc.percent
            row = QTreeWidgetItem([testing.rel(root, path) if root else path, str(c), str(n), str(len(fc.missed)),
                                   f"{pct:.0f}%"])
            row.setData(0, ROLE, path)
            row.setForeground(4, QBrush(ok if pct >= 80 else note if pct >= 50 else bad))
            for col in (1, 2, 3, 4):
                row.setTextAlignment(col, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.cov_tree.addTopLevelItem(row)
        total = 100.0 * tot_c / tot_s if tot_s else 0.0
        self.cov_label.setText(f"<b>{total:.1f}%</b> of {tot_s} statements covered in {len(self.coverage)} file(s)"
                               " &nbsp; (green = run by a test, red = never run, amber = a branch was not taken)")
        self.total_coverage = total

    def _open_cov(self, row, _col=0):
        path = row.data(0, ROLE)
        if path:
            fc = self.coverage.get(path)
            first = min(fc.missed) - 1 if fc and fc.missed else 0
            from .refactor import open_location
            open_location(self.win, path, first)

    def coverage_for(self, path) -> testing.FileCoverage | None:
        try:
            return self.coverage.get(str(Path(path).resolve()))
        except OSError:
            return None

    def _push_coverage(self):
        for ed in editkit.all_monaco_editors():
            if ed.window() is self.win:
                editkit.set_coverage(ed, self.coverage_for(ed.path) if self.show_cov else None)

    def set_show_coverage(self, on: bool):
        self.show_cov = bool(on)
        if self.cov_toggle.isChecked() != self.show_cov:
            self.cov_toggle.setChecked(self.show_cov)
        a = getattr(self.win, "a_show_coverage", None)
        if a is not None and a.isChecked() != self.show_cov:
            a.setChecked(self.show_cov)
        self._push_coverage()

    def clear_coverage(self):
        self.coverage = {}
        self.cov_tree.clear()
        self.cov_label.setText("Coverage cleared.")
        self._push_coverage()


# ============================================================================ install
def install(win) -> None:
    editkit.install_monaco()
    panel = TestExplorer(win)
    dock = QDockWidget("Test Explorer", win)
    dock.setObjectName("TestExplorer")
    dock.setWidget(panel)
    panel.setMinimumWidth(220)
    win.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
    try:
        win.tabifyDockWidget(win.dock_toolbox, dock)
        win.dock_toolbox.raise_()
    except Exception:  # noqa: BLE001
        pass
    dock.hide()
    win.dock_tests = dock
    win.test_explorer = panel
    dock.visibilityChanged.connect(lambda vis: vis and panel.discover())

    def show():
        dock.show()
        dock.raise_()
        panel.discover()

    # Test menu (Visual Studio): placed before Tools
    mb = win.menuBar()
    tools = next((a for a in mb.actions() if a.text().replace("&", "") == "Tools"), None)
    from PyQt6.QtWidgets import QMenu as _QMenu
    menu = _QMenu("Te&st", win)
    if tools is not None:
        mb.insertMenu(tools, menu)
    else:
        mb.addMenu(menu)
    win.test_menu = menu

    def A(text, slot, shortcut=None, icon=None):
        a = QAction(text, win)
        if icon:
            a.setIcon(tool_icon(icon))
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
            a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        a.triggered.connect(slot)
        menu.addAction(a)
        return a
    A("Test E&xplorer", show, "Ctrl+E, T", "flask")
    menu.addSeparator()
    A("Run &All Tests", lambda: (show(), panel.run(None)), "Ctrl+R, A", "runall")
    A("Run &Failed Tests", lambda: (show(), panel.run_failed()), None, "runfailed")
    A("&Debug Selected Test", lambda: (show(), panel.debug_selected()), None, "debug")
    A("Run All Tests with &Coverage", lambda: (show(), panel.run(None, coverage=True)), None, "coverage")
    A("Run Tests in Current &File", lambda: (show(), _run_current_file(win, panel)), "Ctrl+R, T", "run")
    menu.addSeparator()
    sc = A("&Show Code Coverage Colouring", lambda on=False: None)
    sc.setCheckable(True)
    sc.setChecked(True)
    sc.toggled.connect(panel.set_show_coverage)
    win.a_show_coverage = sc
    A("C&lear Coverage Results", panel.clear_coverage)
    A("&Refresh Tests", lambda: (show(), panel.discover(force=True)), None, "refresh")

    # coverage colours for editors opened after a run
    editkit.READY.append(lambda ed: editkit.set_coverage(ed, panel.coverage_for(ed.path))
                         if ed.window() is win and panel.coverage and panel.show_cov else None)

    # VS Code / Agent layouts: a "Testing" entry in the Activity Bar
    try:
        from . import workbench
        workbench.register_view("tests", "Testing", icon=tool_icon("flask"), factory=lambda w: w.dock_tests,
                                modes=("vscode",), area="side", order=45, tooltip="Testing (Test Explorer)")
    except Exception:  # noqa: BLE001
        pass

    # re-discover when another project/solution becomes active
    def poll():
        try:
            if dock.isVisible() and panel.project_root() != panel.root and not panel.running():
                panel.discover(force=True)
        except RuntimeError:
            timer.stop()
    timer = QTimer(win)
    timer.timeout.connect(poll)
    timer.start(2000)


def _run_current_file(win, panel):
    from .formatting import _current_editor
    ed = _current_editor(win)
    if ed is None or not getattr(ed, "path", None):
        panel.run(None)
        return
    target = str(Path(ed.path).resolve()).lower()

    def go():
        keys = [k for k, it in panel.items.items() if it.file and str(Path(it.file).resolve()).lower() == target]
        if keys:
            panel.run(keys)
        else:
            win.statusBar().showMessage("No tests in the current file", 4000)
    if not panel.items:
        panel.discover(force=True)
        panel._wait_then(go)
    else:
        go()
