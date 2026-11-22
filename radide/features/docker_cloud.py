"""Docker and cloud deploy in the IDE (engines: radide/deploy/docker.py, radide/deploy/cloud.py).

* Tools > Docker (and Site > Docker): Generate Dockerfile / compose / Dev Container..., the Docker panel
  (containers, images, compose services, logs, start / stop / restart / remove, build, run, compose up / down),
  Lint Dockerfile (built-in + hadolint + docker build --check).
* The Publish dialog (radide/features/web_tools.py) gets a "Cloud / Git / SSH" tab: Vercel, Netlify, GitHub Pages,
  Azure App Service, AWS (Elastic Beanstalk / S3), Render, Railway and SSH servers - each with Preview, Dry run,
  a read-only sign-in check and clear "sign in first" messages. Site > Deploy to Cloud / Git / SSH... opens it
  (a stand-alone window for projects that are not web sites).
* VS Code / Agent layouts: a "Docker" view (workbench.register_view).

Main-window members added: win.docker_cloud (DockerCloud), win.dock_docker, win.publish_dialog_hooks (list).
Nothing is installed without the user pressing a button, and the IDE never signs in to anybody's account.
"""
from __future__ import annotations

import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QDesktopServices, QFont
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFileDialog, QFormLayout,
                             QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QMenu, QMessageBox,
                             QPlainTextEdit, QPushButton, QSpinBox, QSplitter, QTabWidget, QToolButton, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import theme
from ..deploy import cloud
from ..deploy import docker as dk


# ====================================================================== helpers
def _settings(win):
    s = getattr(win, "settings", None)
    if s is not None:
        return s
    from ..app import ide_settings
    return ide_settings()


def _project_folder(win) -> Path | None:
    p = getattr(win, "project", None)
    return Path(p.folder) if p is not None else None


def _mono(w):
    f = QFont("Consolas")
    f.setStyleHint(QFont.StyleHint.Monospace)
    w.setFont(f)
    return w


def _note(text: str = "", role: str = "note") -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    lab.setOpenExternalLinks(True)
    theme.role(lab, role)
    return lab


def _log(win, text: str):
    try:
        win.log(text)
    except Exception:  # noqa: BLE001
        pass


class _Sig(QObject):
    line = pyqtSignal(str)
    done = pyqtSignal(object)
    status = pyqtSignal(object)


def _thread(fn, on_done=None, on_line=None) -> _Sig:
    """Runs fn(log) in a worker thread; results come back on the UI thread through Qt signals."""
    sig = _Sig()
    if on_done:
        sig.done.connect(on_done)
    if on_line:
        sig.line.connect(on_line)

    def work():
        try:
            res = fn(sig.line.emit)
        except Exception as ex:  # noqa: BLE001 - shown to the user
            res = ex
        sig.done.emit(res)
    threading.Thread(target=work, daemon=True).start()
    return sig


def open_terminal_with(win, command: str):
    """Show the Terminal with the sign-in command typed in (the user presses Enter - we never sign in)."""
    try:
        from .terminal import show_terminal
        show_terminal(win)
        win.terminal.input.setText(command)
        win.terminal.input.setFocus()
    except Exception:  # noqa: BLE001
        QMessageBox.information(win, "Sign in", f"Run this in a terminal:\n\n{command}")


# ====================================================================== Generate dialog
class DockerGenerateDialog(QDialog):
    """Docker > Generate Dockerfile / compose / Dev Container."""

    def __init__(self, win, folder: Path | None = None, parent=None):
        super().__init__(parent or win)
        self.win = win
        self.setWindowTitle("Generate Docker Files")
        self.resize(1000, 720)
        self.folder = Path(folder) if folder else (_project_folder(win) or Path.cwd())
        self.edits: dict[str, QPlainTextEdit] = {}
        self._dirty = False

        self.f_folder = QLineEdit(str(self.folder))
        b_folder = QPushButton("Browse...")
        self.detected = _note("", "muted")
        self.f_stack = QComboBox()
        for k in dk.TEMPLATES:
            self.f_stack.addItem(dk.STACK_LABELS[k], k)
        self.f_port = QSpinBox(minimum=0, maximum=65535, specialValueText="default")
        self.f_db = QComboBox()
        for k, lab in (("none", "None"), ("postgres", "PostgreSQL 16"), ("mysql", "MySQL 8.4"),
                       ("mariadb", "MariaDB 11"), ("redis", "Redis 7"), ("mongo", "MongoDB 8")):
            self.f_db.addItem(lab, k)
        self.f_python = QComboBox()
        self.f_python.addItems(["3.13", "3.12", "3.11", "3.10"])
        self.f_python.setCurrentText("3.12")
        self.f_node = QComboBox()
        self.f_node.addItems(["22", "20", "24"])
        self.f_php = QComboBox()
        self.f_php.addItems(["8.4", "8.3", "8.2", "8.1"])
        self.f_php.setCurrentText("8.3")
        self.f_compose = QCheckBox("compose.yaml")
        self.f_compose.setChecked(True)
        self.f_dev = QCheckBox(".devcontainer/devcontainer.json")
        self.f_dev.setChecked(True)
        self.f_watch = QCheckBox("Live sync (docker compose watch)")
        self.f_watch.setChecked(True)
        self.f_over = QCheckBox("Overwrite existing files (a .bak copy is kept)")

        form = QFormLayout()
        row = QHBoxLayout()
        row.addWidget(self.f_folder, 1)
        row.addWidget(b_folder)
        form.addRow("Project folder:", row)
        form.addRow("", self.detected)
        form.addRow("Project type:", self.f_stack)
        form.addRow("Port:", self.f_port)
        form.addRow("Database service:", self.f_db)
        vers = QHBoxLayout()
        for lab, w in (("Python", self.f_python), ("Node", self.f_node), ("PHP", self.f_php)):
            vers.addWidget(QLabel(lab))
            vers.addWidget(w)
        vers.addStretch(1)
        form.addRow("Versions:", vers)
        files = QHBoxLayout()
        for w in (self.f_compose, self.f_dev, self.f_watch):
            files.addWidget(w)
        files.addStretch(1)
        form.addRow("Also generate:", files)
        form.addRow("", self.f_over)

        self.tabs = QTabWidget()
        self.issues = QTreeWidget()
        self.issues.setHeaderLabels(["Line", "Level", "Code", "Message", "Linter"])
        self.issues.setRootIsDecorated(False)
        self.issues.setColumnWidth(3, 520)
        self.lint_note = _note("", "muted")
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.tabs)
        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(self.lint_note)
        ll.addWidget(self.issues)
        split.addWidget(lw)
        split.setSizes([480, 160])

        self.b_lint = QPushButton("Lint")
        self.b_hadolint = QPushButton("Get hadolint")
        self.b_hadolint.setToolTip(f"Download hadolint {dk.HADOLINT_VERSION} (GitHub release, sha256 verified) into "
                                   f"{dk.tools_root() / 'hadolint'}")
        self.b_hadolint.setVisible(not dk.hadolint_path())
        self.b_write = QPushButton("Write Files")
        self.b_write.setDefault(True)
        self.b_build = QPushButton("Write and Build Image")
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        bottom = QHBoxLayout()
        for b in (self.b_lint, self.b_hadolint, self.b_write, self.b_build):
            bottom.addWidget(b)
        bottom.addStretch(1)
        bottom.addWidget(bb)
        self.status = _note("", "muted")
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(split, 1)
        lay.addWidget(self.status)
        lay.addLayout(bottom)

        b_folder.clicked.connect(self._browse)
        self.f_folder.editingFinished.connect(self._detect)
        for w in (self.f_stack, self.f_db, self.f_python, self.f_node, self.f_php):
            w.currentIndexChanged.connect(self._regen)
        self.f_port.valueChanged.connect(self._regen)
        for w in (self.f_compose, self.f_dev, self.f_watch):
            w.toggled.connect(self._regen)
        self.b_lint.clicked.connect(self.lint)
        self.b_hadolint.clicked.connect(self._get_hadolint)
        self.b_write.clicked.connect(lambda: self.write())
        self.b_build.clicked.connect(lambda: self.write(build=True))
        self._detect()

    # ------------------------------------------------------------------ generation
    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Project folder", self.f_folder.text())
        if d:
            self.f_folder.setText(d)
            self._detect()

    def _detect(self):
        self.folder = Path(self.f_folder.text().strip() or ".")
        st = dk.detect_stack(self.folder)
        self.stack = st
        if st.supported:
            self.detected.setText(f"Detected: <b>{st.label}</b> ({st.reason})")
            theme.role(self.detected, "muted")
            i = self.f_stack.findData(st.kind)
            self.f_stack.blockSignals(True)
            self.f_stack.setCurrentIndex(max(i, 0))
            self.f_stack.blockSignals(False)
        else:
            self.detected.setText(f"<b>{st.label}</b>: {st.reason} You can still choose a type below.")
            theme.role(self.detected, "note")
        self._regen()

    def options(self) -> dk.DockerOptions:
        return dk.DockerOptions(port=self.f_port.value(), database=self.f_db.currentData(),
                                python=self.f_python.currentText(), node=self.f_node.currentText(),
                                php=self.f_php.currentText(), compose=self.f_compose.isChecked(),
                                devcontainer=self.f_dev.isChecked(), watch=self.f_watch.isChecked())

    def current_stack(self) -> dk.Stack:
        kind = self.f_stack.currentData()
        if self.stack.kind == kind:
            return self.stack
        return dk._finish(self.folder, dk.Stack(kind, reason="chosen by you"))

    def _regen(self, *_):
        try:
            files = dk.generate(self.folder, self.current_stack(), self.options())
        except (ValueError, OSError) as ex:
            files = {}
            self.status.setText(str(ex))
        cur = self.tabs.tabText(self.tabs.currentIndex()) if self.tabs.count() else ""
        self.tabs.clear()
        self.edits = {}
        for rel, text in files.items():
            ed = _mono(QPlainTextEdit())
            ed.setPlainText(text)
            ed.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            exists = (self.folder / rel).exists()
            self.tabs.addTab(ed, rel + ("  (exists)" if exists else ""))
            self.edits[rel] = ed
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == cur:
                self.tabs.setCurrentIndex(i)
        existing = [r for r in files if (self.folder / r).exists()]
        self.status.setText(("Existing files are kept unless 'Overwrite' is ticked: " + ", ".join(existing))
                            if existing else "Edit the files above if you like, then press Write Files.")

    def files(self) -> dict[str, str]:
        return {rel: ed.toPlainText() for rel, ed in self.edits.items()}

    # ------------------------------------------------------------------ lint / write
    def lint(self, use_docker: bool | None = None):
        text = self.files().get("Dockerfile", "")
        self.issues.clear()
        issues = dk.lint_builtin(text)
        notes = ["built-in checker"]
        tmp_dir = self.folder
        hl = dk.hadolint_path()
        import tempfile
        with tempfile.TemporaryDirectory(prefix="radide-lint-") as td:
            p = Path(td) / "Dockerfile"
            p.write_text(text, encoding="utf-8")
            if hl:
                issues += dk.lint_hadolint(p, hl) or []
                notes.append("hadolint")
            else:
                notes.append("hadolint not installed")
        if use_docker is None:
            use_docker = bool(dk.find_cli()) and (self.folder / "Dockerfile").is_file() and \
                (self.folder / "Dockerfile").read_text(encoding="utf-8", errors="replace") == text
        if use_docker:
            d = dk.lint_docker_check(tmp_dir)
            if d is not None:
                issues += d
                notes.append("docker build --check")
        for i in issues:
            it = QTreeWidgetItem([str(i.line), i.level, i.code, i.message, i.source])
            if i.level in ("error", "warning"):
                it.setForeground(1, QBrush(QColor(theme.color("error" if i.level == "error" else "note"))))
            self.issues.addTopLevelItem(it)
        msg = f"{len(issues)} issue(s) - ran: {', '.join(notes)}."
        if not issues:
            msg = "No problems found - ran: " + ", ".join(notes) + "."
        self.lint_note.setText(msg)
        return issues

    def _get_hadolint(self):
        self.b_hadolint.setEnabled(False)
        self.lint_note.setText("Downloading hadolint ...")

        def done(res):
            self.b_hadolint.setEnabled(True)
            if isinstance(res, str) and res:
                self.b_hadolint.setVisible(False)
                self.lint()
            else:
                self.lint_note.setText(f"hadolint was not installed: {res}")
        _thread(lambda log: dk.install_hadolint(log), done, lambda s: _log(self.win, "[docker] " + s))

    def write(self, build: bool = False) -> list[str]:
        files = self.files()
        if not files:
            return []
        written, skipped = dk.write_files(self.folder, files, overwrite=self.f_over.isChecked())
        msg = f"Wrote {', '.join(written) or 'nothing'}" + (f"; kept existing {', '.join(skipped)}" if skipped else "")
        self.status.setText(msg + ".")
        _log(self.win, f"[docker] {self.folder}: {msg}")
        self._regen()
        if build:
            dc = getattr(self.win, "docker_cloud", None)
            if dc is not None:
                dc.show_panel()
                dc.panel.build(self.folder)
        return written


# ====================================================================== Docker panel
class DockerPanel(QWidget):
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win
        self.cli: dk.DockerCli | None = None
        self.proc: QProcess | None = None
        self._folder_override: Path | None = None

        self.state = _note("Docker: not checked yet", "muted")
        self.b_refresh = QToolButton(text="Refresh")
        self.b_gen = QToolButton(text="Generate Files...")
        self.b_build = QToolButton(text="Build")
        self.b_run = QToolButton(text="Run")
        self.b_up = QToolButton(text="Compose Up")
        self.b_down = QToolButton(text="Compose Down")
        self.b_lint = QToolButton(text="Lint")
        self.b_stop = QToolButton(text="Stop Job")
        self.b_stop.setEnabled(False)
        self.only = QCheckBox("This project only")
        self.only.setToolTip("Show only containers of this project's compose file / image")
        bar = QHBoxLayout()
        for b in (self.b_refresh, self.b_gen, self.b_build, self.b_run, self.b_up, self.b_down, self.b_lint,
                  self.b_stop):
            b.setAutoRaise(True)
            bar.addWidget(b)
        bar.addStretch(1)
        bar.addWidget(self.only)

        self.containers = QTreeWidget()
        self.containers.setHeaderLabels(["Name", "Image", "State", "Status", "Ports"])
        self.containers.setRootIsDecorated(False)
        self.containers.setColumnWidth(0, 200)
        self.containers.setColumnWidth(1, 200)
        self.containers.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.images = QTreeWidget()
        self.images.setHeaderLabels(["Image", "ID", "Size", "Created"])
        self.images.setRootIsDecorated(False)
        self.images.setColumnWidth(0, 260)
        self.images.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.compose = QTreeWidget()
        self.compose.setHeaderLabels(["Service", "Container", "State", "Ports"])
        self.compose.setRootIsDecorated(False)
        self.output = _mono(QPlainTextEdit(readOnly=True))
        self.output.setMaximumBlockCount(5000)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.containers, "Containers")
        self.tabs.addTab(self.images, "Images")
        self.tabs.addTab(self.compose, "Compose")
        self.tabs.addTab(self.output, "Output / Logs")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.addWidget(self.state)
        lay.addLayout(bar)
        lay.addWidget(self.tabs, 1)

        self.b_refresh.clicked.connect(self.refresh)
        self.b_gen.clicked.connect(lambda: DockerGenerateDialog(self.win, self.folder()).exec())
        self.b_build.clicked.connect(lambda: self.build())
        self.b_run.clicked.connect(lambda: self.run_image())
        self.b_up.clicked.connect(lambda: self.compose_up())
        self.b_down.clicked.connect(lambda: self.compose_down())
        self.b_lint.clicked.connect(lambda: self.lint())
        self.b_stop.clicked.connect(self.stop_job)
        self.only.toggled.connect(lambda _c: self.refresh())
        self.containers.customContextMenuRequested.connect(self._container_menu)
        self.containers.itemDoubleClicked.connect(lambda it, _c: self.logs(it.data(0, Qt.ItemDataRole.UserRole)))
        self.images.customContextMenuRequested.connect(self._image_menu)
        self._set_enabled(False)

    # ------------------------------------------------------------------ state
    def folder(self) -> Path | None:
        return self._folder_override or _project_folder(self.win)

    def _set_enabled(self, ok: bool, compose: bool = False):
        for b in (self.b_build, self.b_run, self.b_lint):
            b.setEnabled(ok)
        self.b_up.setEnabled(ok and compose)
        self.b_down.setEnabled(ok and compose)
        self.b_lint.setEnabled(True)

    def refresh(self):
        self.state.setText("Checking Docker ...")

        def work(_log):
            cli = dk.find_cli(refresh=True)
            ok, msg = dk.daemon_status(cli) if cli else (False, dk.DOCKER_INSTALL_HINT)
            data = {"cli": cli, "ok": ok, "msg": msg, "containers": [], "images": [], "compose": []}
            if ok:
                data["containers"] = dk.list_containers(cli)
                data["images"] = dk.list_images(cli)
                f = self.folder()
                cf = dk.find_compose_file(f) if f else ""
                data["compose_file"] = cf
                if cf:
                    data["compose"] = dk.compose_ps(f, cf, cli)
            return data
        _thread(work, self._on_refresh)

    def _on_refresh(self, data):
        if isinstance(data, Exception):
            self.state.setText(f"Docker: {data}")
            return
        self.cli = data["cli"]
        theme.role(self.state, "success" if data["ok"] else "note")
        self.state.setText(("Docker: " if data["ok"] else "") + data["msg"])
        cf = data.get("compose_file", "")
        self._set_enabled(bool(data["ok"]), bool(cf))
        f = self.folder()
        tag_prefix = dk.image_tag_for(f).split(":")[0] if f else ""
        compose_names = {c.get("Name", "") for c in data["compose"]}
        self.containers.clear()
        for c in data["containers"]:
            name = c.get("Names", "")
            if self.only.isChecked() and not (name in compose_names or c.get("Image", "").startswith(tag_prefix)):
                continue
            it = QTreeWidgetItem([name, c.get("Image", ""), c.get("State", ""), c.get("Status", ""),
                                  c.get("Ports", "")])
            it.setData(0, Qt.ItemDataRole.UserRole, c.get("ID", name))
            self.containers.addTopLevelItem(it)
        self.images.clear()
        for im in data["images"]:
            ref = f"{im.get('Repository', '')}:{im.get('Tag', '')}"
            if self.only.isChecked() and not ref.startswith(tag_prefix):
                continue
            it = QTreeWidgetItem([ref, im.get("ID", ""), im.get("Size", ""), im.get("CreatedSince", "")])
            it.setData(0, Qt.ItemDataRole.UserRole, ref if "<none>" not in ref else im.get("ID", ""))
            self.images.addTopLevelItem(it)
        self.compose.clear()
        for s in data["compose"]:
            ports = s.get("Ports") or ", ".join(f"{p.get('PublishedPort')}->{p.get('TargetPort')}"
                                                for p in (s.get("Publishers") or []) if p.get("PublishedPort"))
            self.compose.addTopLevelItem(QTreeWidgetItem([s.get("Service", ""), s.get("Name", ""),
                                                          s.get("State", ""), str(ports)]))
        self.tabs.setTabText(2, f"Compose ({cf})" if cf else "Compose")

    # ------------------------------------------------------------------ jobs (streamed into Output)
    def run_job(self, argv: list[str], cwd: Path | None = None, title: str = "", on_finished=None) -> bool:
        if not argv:
            return False
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.information(self, "Docker", "Another Docker job is running - stop it first.")
            return False
        self.tabs.setCurrentWidget(self.output)
        self.output.appendPlainText(f"\n> {' '.join(argv)}" + (f"   (in {cwd})" if cwd else ""))
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        if cwd:
            p.setWorkingDirectory(str(cwd))
        p.readyReadStandardOutput.connect(
            lambda: self.output.appendPlainText(bytes(p.readAllStandardOutput()).decode("utf-8", "replace")
                                                .rstrip("\n")))

        def fin(code, _status):
            self.output.appendPlainText(f"[{title or argv[1]} finished with exit code {code}]")
            self.b_stop.setEnabled(False)
            self.proc = None
            if on_finished:
                on_finished(code)
            self.refresh()
        p.finished.connect(fin)
        p.errorOccurred.connect(lambda e: self.output.appendPlainText(f"[cannot start {argv[0]}: {e.name}]"))
        p.start(argv[0], argv[1:])
        self.proc = p
        self.b_stop.setEnabled(True)
        return True

    def stop_job(self):
        if self.proc is not None:
            self.proc.kill()

    def _need(self) -> dk.DockerCli | None:
        cli = self.cli
        if cli is None and "cli" not in dk._CLI_CACHE:
            # find_cli runs `docker --version` / `docker compose version`, which take up to ~40 s while Docker
            # Desktop starts or hangs: never in the UI thread (the action crawler found the IDE frozen here).
            # The panel's refresh() is detecting it in the background already; start that if it is not.
            self.state.setText("Looking for Docker ...")
            if not getattr(self, "_finding_cli", False):
                self._finding_cli = True

                def found(c):
                    self._finding_cli = False
                    if not isinstance(c, Exception) and self.cli is None:
                        self.cli = c
                _thread(lambda _log: dk.find_cli(), found)
            QMessageBox.information(self, "Docker", "Still looking for the Docker command line - "
                                                    "try again in a moment.")
            return None
        cli = cli or dk.find_cli()          # cached: instant
        if cli is None:
            QMessageBox.information(self, "Docker", dk.DOCKER_INSTALL_HINT)
        return cli

    def build(self, folder: Path | None = None) -> bool:
        cli, folder = self._need(), Path(folder) if folder else self.folder()
        if cli is None or folder is None:
            return False
        if not (folder / "Dockerfile").is_file():
            if QMessageBox.question(self, "Docker", "There is no Dockerfile yet. Generate one?") == \
                    QMessageBox.StandardButton.Yes:
                DockerGenerateDialog(self.win, folder).exec()
            if not (folder / "Dockerfile").is_file():
                return False
        return self.run_job(dk.build_cmd(cli, folder), folder, "build")

    def run_image(self, image: str = "") -> bool:
        cli, folder = self._need(), self.folder()
        if cli is None:
            return False
        image = image or (dk.image_tag_for(folder) if folder else "")
        st = dk.detect_stack(folder) if folder else dk.Stack("unknown", 0)
        cport = {"php": 80, "laravel": 80, "codeigniter": 80, "static": 80, "node-static": 80}.get(st.kind, st.port)
        text, ok = QInputDialog.getText(self, "Run image", f"Run {image}\nHost port -> container port:",
                                        text=f"{cport if cport != 80 else 8080}:{cport}" if cport else "")
        if not ok:
            return False
        hp = cp = 0
        try:
            if ":" in text:
                a, b = text.split(":", 1)
                hp, cp = int(a or 0), int(b or 0)
        except ValueError:
            QMessageBox.information(self, "Run image", "Write the ports as HOST:CONTAINER, e.g. 8080:80.")
            return False
        if hp and not dk.port_free(hp):
            alt = dk.free_port_near(hp)
            QMessageBox.information(self, "Port in use", f"Port {hp} is already used by another program"
                                    + (f" - using {alt} instead." if alt else "."))
            hp = alt or hp
        name = "radide-" + image.split(":")[0].replace("/", "-")
        started = self.run_job(dk.run_cmd(cli, image, hp, cp, name=name), None, "run")
        if started and hp:
            QTimer.singleShot(4000, lambda: QDesktopServices.openUrl(QUrl(f"http://127.0.0.1:{hp}/")))
        return started

    def compose_up(self) -> bool:
        cli, folder = self._need(), self.folder()
        if cli is None or folder is None:
            return False
        cf = dk.find_compose_file(folder)
        if not cf or not cli.compose:
            QMessageBox.information(self, "Docker", "No compose file (or no docker compose) for this project.")
            return False
        for port in dk.busy_compose_ports(folder, cf):
            # another program (or container) already listens there: offer a free port instead
            alt = dk.free_port_near(port)
            if alt and QMessageBox.question(
                    self, "Port in use", f"Port {port} is already used by another program.\n\nUse port {alt} "
                    f"instead (changes the ports line of {cf})?") == QMessageBox.StandardButton.Yes:
                dk.change_compose_host_port(folder, cf, port, alt)
                self.output.appendPlainText(f"[{cf}: host port {port} -> {alt}]")
            else:
                self.output.appendPlainText(f"[warning: port {port} is in use - compose up may fail]")
        return self.run_job(dk.compose_up_cmd(cli, cf), folder, "compose up")

    def compose_down(self) -> bool:
        cli, folder = self._need(), self.folder()
        if cli is None or folder is None:
            return False
        cf = dk.find_compose_file(folder)
        return bool(cf) and self.run_job(dk.compose_down_cmd(cli, cf), folder, "compose down")

    def lint(self) -> list:
        folder = self.folder()
        if folder is None or not (folder / "Dockerfile").is_file():
            QMessageBox.information(self, "Lint", "This project has no Dockerfile yet (Generate Files...).")
            return []
        issues, notes = dk.lint(folder, use_docker=bool(self.cli))
        self.tabs.setCurrentWidget(self.output)
        self.output.appendPlainText(f"\nLint {folder / 'Dockerfile'} ({', '.join(notes)}):")
        for i in issues:
            self.output.appendPlainText("  " + str(i))
        if not issues:
            self.output.appendPlainText("  no problems found")
        return issues

    def logs(self, container: str, follow: bool = False):
        cli = self._need()
        if cli and container:
            self.run_job(dk.logs_cmd(cli, container, follow=follow), None, "logs")

    def container_action(self, action: str, container: str, name: str = "") -> bool:
        cli = self._need()
        if cli is None or not container:
            return False
        if action in ("stop", "rm", "kill", "restart"):
            verb = {"rm": "Remove", "stop": "Stop", "kill": "Kill", "restart": "Restart"}[action]
            if QMessageBox.question(self, "Docker", f"{verb} container '{name or container}'?") != \
                    QMessageBox.StandardButton.Yes:
                return False
        return self.run_job(dk.container_action_cmd(cli, action, container), None, action)

    def _container_menu(self, pos):
        it = self.containers.itemAt(pos)
        if it is None:
            return
        cid, name, state = it.data(0, Qt.ItemDataRole.UserRole), it.text(0), it.text(2)
        m = QMenu(self)
        if state != "running":
            m.addAction("Start", lambda: self.container_action("start", cid, name))
        else:
            m.addAction("Stop", lambda: self.container_action("stop", cid, name))
            m.addAction("Restart", lambda: self.container_action("restart", cid, name))
        m.addAction("Logs", lambda: self.logs(cid))
        m.addAction("Follow Logs", lambda: self.logs(cid, follow=True))
        port = _first_host_port(it.text(4))
        if port:
            m.addAction(f"Open http://localhost:{port}/",
                        lambda: QDesktopServices.openUrl(QUrl(f"http://localhost:{port}/")))
        m.addSeparator()
        m.addAction("Remove", lambda: self.container_action("rm", cid, name))
        m.exec(self.containers.viewport().mapToGlobal(pos))

    def _image_menu(self, pos):
        it = self.images.itemAt(pos)
        if it is None:
            return
        ref = it.data(0, Qt.ItemDataRole.UserRole)
        m = QMenu(self)
        m.addAction("Run...", lambda: self.run_image(ref))
        m.addSeparator()

        def remove():
            cli = self._need()
            if cli and QMessageBox.question(self, "Docker", f"Remove image '{ref}'?") == \
                    QMessageBox.StandardButton.Yes:
                self.run_job(cli.cmd("rmi", ref), None, "rmi")
        m.addAction("Remove", remove)
        m.exec(self.images.viewport().mapToGlobal(pos))


def _first_host_port(ports: str) -> int:
    import re
    m = re.search(r":(\d+)->", ports or "")
    return int(m.group(1)) if m else 0


# ====================================================================== Cloud deploy panel
class CloudDeployPanel(QWidget):
    """Deploy profiles for Vercel / Netlify / GitHub Pages / Azure / AWS / Render / Railway / SSH."""

    def __init__(self, win, project, parent=None):
        super().__init__(parent)
        self.win = win
        self.project = project
        self.folder = Path(project.folder)
        self.profiles = cloud.load_profiles(project)
        self._cur = -1
        self._fields: dict[str, QWidget] = {}
        self._cancel: threading.Event | None = None
        self._busy = False

        self.list = QListWidget()
        b_new = QPushButton("New")
        menu = QMenu(b_new)
        for t in cloud.TARGETS.values():
            menu.addAction(t.label, lambda tid=t.id: self.add_profile(tid))
        b_new.setMenu(menu)
        b_dup, b_del = QPushButton("Duplicate"), QPushButton("Delete")
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>Deploy profiles</b>"))
        left.addWidget(self.list, 1)
        row = QHBoxLayout()
        for b in (b_new, b_dup, b_del):
            row.addWidget(b)
        left.addLayout(row)
        lw = QWidget()
        lw.setLayout(left)

        self.head = QLabel()
        self.head.setTextFormat(Qt.TextFormat.RichText)
        self.head.setOpenExternalLinks(True)
        self.tool_state = _note("", "muted")
        self.form_host = QWidget()
        self.form = QFormLayout(self.form_host)
        self.log = _mono(QPlainTextEdit(readOnly=True))
        self.log.setMaximumBlockCount(5000)
        self.result = _note("", "muted")

        self.b_signin = QPushButton("Check Sign-in")
        self.b_signin.setToolTip("Runs a read-only status command (whoami / account show). Never signs in.")
        self.b_terminal = QPushButton("Sign in (Terminal)...")
        self.b_terminal.setToolTip("Opens the Terminal with the sign-in command typed in - you press Enter")
        self.b_preview = QPushButton("Preview")
        self.b_preview.setToolTip("Shows the commands and files - nothing runs")
        self.b_dry = QPushButton("Dry Run")
        self.b_dry.setToolTip("Runs the deploy in dry-run mode (az --dryrun, aws --dryrun, git push --dry-run, "
                              "SFTP plan ...) - nothing changes on the server")
        self.b_deploy = QPushButton("Deploy")
        self.b_cancel = QPushButton("Cancel")
        self.b_cancel.setEnabled(False)
        self.b_install = QPushButton("Install CLI")
        self.b_config = QPushButton("Generate Config")
        self.b_config.setToolTip("Writes vercel.json / netlify.toml / render.yaml / railway.json when missing")
        self.b_open = QPushButton("Open Site")
        btns = QHBoxLayout()
        for b in (self.b_signin, self.b_terminal, self.b_preview, self.b_dry, self.b_deploy, self.b_cancel,
                  self.b_install, self.b_config, self.b_open):
            btns.addWidget(b)
        btns.addStretch(1)

        right = QVBoxLayout()
        right.addWidget(self.head)
        right.addWidget(self.tool_state)
        right.addWidget(self.form_host)
        right.addLayout(btns)
        right.addWidget(self.result)
        right.addWidget(self.log, 1)
        rw = QWidget()
        rw.setLayout(right)
        split = QSplitter()
        split.addWidget(lw)
        split.addWidget(rw)
        split.setSizes([200, 780])
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(split)

        b_dup.clicked.connect(self.duplicate_profile)
        b_del.clicked.connect(self.delete_profile)
        self.list.currentRowChanged.connect(self._on_select)
        self.b_signin.clicked.connect(self.check_signin)
        self.b_terminal.clicked.connect(self.signin_terminal)
        self.b_preview.clicked.connect(self.preview)
        self.b_dry.clicked.connect(lambda: self.start(dry_run=True))
        self.b_deploy.clicked.connect(lambda: self.start(dry_run=False))
        self.b_cancel.clicked.connect(self.cancel)
        self.b_install.clicked.connect(self.install_cli)
        self.b_config.clicked.connect(self.generate_config)
        self.b_open.clicked.connect(self.open_site)
        self._fill_list()
        if self.profiles:
            self.list.setCurrentRow(0)
        else:
            self._show_empty()

    # ------------------------------------------------------------------ profiles
    def _fill_list(self):
        self.list.blockSignals(True)
        self.list.clear()
        for p in self.profiles:
            self.list.addItem(f"{p.name}  ({cloud.TARGETS[p.target].label})")
        self.list.blockSignals(False)

    def _show_empty(self):
        self._clear_form()
        self.head.setText("<b>Deploy to the cloud, a git host or your own server</b>")
        self.tool_state.setText("Press New and choose a target: Vercel, Netlify, GitHub Pages, Azure App Service, "
                                "AWS, Render, Railway or an SSH server.")
        for b in (self.b_signin, self.b_terminal, self.b_preview, self.b_dry, self.b_deploy, self.b_install,
                  self.b_config, self.b_open):
            b.setEnabled(False)

    def current(self) -> cloud.DeployProfile | None:
        return self.profiles[self._cur] if 0 <= self._cur < len(self.profiles) else None

    def _unique(self, base: str) -> str:
        names = {p.name for p in self.profiles}
        if base not in names:
            return base
        i = 2
        while f"{base} {i}" in names:
            i += 1
        return f"{base} {i}"

    def add_profile(self, tid: str) -> cloud.DeployProfile:
        self._store()
        t = cloud.TARGETS[tid]
        p = cloud.DeployProfile(name=self._unique(t.label.split(" (")[0]), target=tid)
        for f in t.fields:
            if f.default not in ("", None) and f.kind != "password":
                p.options[f.key] = f.default
        if tid in ("ghpages", "ssh", "aws") and (self.folder / "package.json").is_file():
            p.build_cmd = "npm run build"
        self.profiles.append(p)
        self._fill_list()
        self.list.setCurrentRow(len(self.profiles) - 1)
        self.save()
        return p

    def duplicate_profile(self):
        p = self.current()
        if p is None:
            return
        self._store()
        q = cloud.DeployProfile.from_dict(p.to_dict())
        q.name = self._unique(p.name)
        self.profiles.append(q)
        self._fill_list()
        self.list.setCurrentRow(len(self.profiles) - 1)

    def delete_profile(self):
        p = self.current()
        if p is None or QMessageBox.question(self, "Deploy", f"Delete the profile '{p.name}'?") != \
                QMessageBox.StandardButton.Yes:
            return
        for f in cloud.TARGETS[p.target].fields:
            if f.kind == "password":
                self._set_secret(p, f.key, None)
        del self.profiles[self._cur]
        self._cur = -1
        self._fill_list()
        self.save()
        if self.profiles:
            self.list.setCurrentRow(0)
        else:
            self._show_empty()

    # ------------------------------------------------------------------ secrets (user settings, never the project)
    def _secret_key(self, p, key) -> str:
        return f"deploy:{p.name}:{key}"

    def _get_secret(self, p, key) -> str:
        from ..web_site import publish as pub
        k = self._secret_key(p, key)
        cache = self.__dict__.setdefault("_secret_cache", {})
        if k in cache:
            return cache[k]
        return pub.get_password(_settings(self.win), self.folder, k) or ""

    def _set_secret(self, p, key, value):
        from ..web_site import publish as pub
        k = self._secret_key(p, key)
        self.__dict__.setdefault("_secret_cache", {})[k] = value or ""
        pub.set_password(_settings(self.win), self.folder, k, value or None)

    def secrets(self, p) -> dict:
        return {f.key: self._get_secret(p, f.key) for f in cloud.TARGETS[p.target].fields if f.kind == "password"}

    # ------------------------------------------------------------------ form
    def _clear_form(self):
        while self.form.rowCount():
            self.form.removeRow(0)
        self._fields = {}

    def _on_select(self, row: int):
        self._store()
        self._cur = row
        p = self.current()
        if p is None:
            self._show_empty()
            return
        t = cloud.TARGETS[p.target]
        self._clear_form()
        docs = f' - <a href="{t.docs}">docs</a>' if t.docs else ""
        self.head.setText(f"<b>{t.label}</b>{docs}")
        ok, status = t.available()
        theme.role(self.tool_state, "success" if ok else "note")
        self.tool_state.setText(status)

        def add(key, label, w):
            self._fields[key] = w
            self.form.addRow(label, w)
        add("name", "Profile name:", QLineEdit(p.name))
        folder = QLineEdit(p.folder)
        folder.setPlaceholderText(f"(auto: {cloud.output_dir(self.folder).relative_to(self.folder).as_posix()}"
                                  if cloud.output_dir(self.folder) != self.folder else "(auto: the project folder)")
        add("folder", "Folder to deploy:", folder)
        add("build_cmd", "Build command:", QLineEdit(p.build_cmd, placeholderText="(optional) npm run build"))
        prod = QCheckBox("Production deploy")
        prod.setChecked(bool(p.production))
        add("production", "", prod)
        add("site_url", "Site URL:", QLineEdit(p.site_url, placeholderText="https://... (opened after deploying)"))
        for f in t.fields:
            if f.kind == "bool":
                w = QCheckBox(f.label)
                w.setChecked(bool(p.options.get(f.key, f.default)))
                label = ""
            elif f.kind == "choice":
                w = QComboBox()
                w.setEditable(True)
                w.addItems([str(c) for c in f.choices])
                w.setCurrentText(str(p.options.get(f.key, f.default) or ""))
                label = f.label + ":"
            elif f.kind == "int":
                w = QSpinBox(minimum=0, maximum=65535)
                w.setValue(int(p.options.get(f.key, f.default) or 0))
                label = f.label + ":"
            elif f.kind == "multiline":
                w = QPlainTextEdit(str(p.options.get(f.key, "")))
                w.setPlaceholderText(f.placeholder)
                w.setMaximumHeight(70)
                label = f.label + ":"
            elif f.kind == "password":
                w = QLineEdit(self._get_secret(p, f.key), echoMode=QLineEdit.EchoMode.Password)
                w.setPlaceholderText(f.placeholder or "(kept in your user settings, not in the project)")
                label = f.label + ":"
            else:
                w = QLineEdit(str(p.options.get(f.key, f.default) or ""))
                w.setPlaceholderText(f.placeholder)
                label = f.label + ":"
            if f.tip:
                w.setToolTip(f.tip)
            add("opt:" + f.key, label, w)
        for b in (self.b_signin, self.b_preview, self.b_dry, self.b_deploy, self.b_config, self.b_open):
            b.setEnabled(not self._busy)
        self.b_terminal.setEnabled(bool(t.signin_cmd))
        self.b_install.setVisible(t.npm)
        self.b_install.setEnabled(t.npm and not t.tool())
        self.b_config.setEnabled(bool(t.config_files(p, self.folder)) if p.target != "render" or
                                 dk.detect_stack(self.folder).supported else False)

    def _store(self):
        p = self.current()
        if p is None or not self._fields or getattr(self, "_closed", False):
            return
        f = self._fields
        old_name = p.name
        p.name = f["name"].text().strip() or p.name
        p.folder = f["folder"].text().strip()
        p.build_cmd = f["build_cmd"].text().strip()
        p.production = f["production"].isChecked()
        p.site_url = f["site_url"].text().strip()
        for fd in cloud.TARGETS[p.target].fields:
            w = f.get("opt:" + fd.key)
            if w is None:
                continue
            if fd.kind == "bool":
                p.options[fd.key] = w.isChecked()
            elif fd.kind == "choice":
                p.options[fd.key] = w.currentText().strip()
            elif fd.kind == "int":
                p.options[fd.key] = w.value()
            elif fd.kind == "multiline":
                p.options[fd.key] = w.toPlainText()
            elif fd.kind == "password":
                if old_name != p.name:
                    self._set_secret(cloud.DeployProfile(name=old_name, target=p.target), fd.key, None)
                self._set_secret(p, fd.key, w.text())
            else:
                p.options[fd.key] = w.text().strip()
        if 0 <= self._cur < self.list.count():
            self.list.item(self._cur).setText(f"{p.name}  ({cloud.TARGETS[p.target].label})")

    def save(self, final: bool = False):
        """Stores the form and writes the profiles. final=True when the window closes: later signals emitted
        while Qt destroys the widgets must not store half-destroyed fields (e.g. clear a saved password)."""
        self._store()
        if final:
            self._closed = True
        try:
            cloud.save_profiles(self.project, self.profiles)
        except OSError as ex:
            _log(self.win, f"[deploy] cannot save the profiles: {ex}")

    # ------------------------------------------------------------------ actions
    def _append(self, text: str):
        self.log.appendPlainText(text)

    def preview(self) -> str:
        self._store()
        p = self.current()
        if p is None:
            return ""
        text = cloud.preview_text(p, self.folder, self.secrets(p))
        self.log.setPlainText(text)
        self.result.setText("Preview only - nothing was run.")
        theme.role(self.result, "muted")
        return text

    def _busy_ui(self, busy: bool):
        self._busy = busy
        for b in (self.b_signin, self.b_preview, self.b_dry, self.b_deploy, self.b_install, self.b_config):
            b.setEnabled(not busy)
        self.b_cancel.setEnabled(busy)

    def check_signin(self):
        self._store()
        p = self.current()
        if p is None:
            return
        st = cloud.TARGETS[p.target].signin_check(p, self.folder)
        if st is None:
            self.result.setText("This target has no sign-in check (or its tool is missing) - see the status above.")
            return
        self._run([st], "Sign-in check", lambda r: "Signed in - ready to deploy." if r.ok else r.message)

    def signin_terminal(self):
        p = self.current()
        if p is not None:
            open_terminal_with(self.win, cloud.TARGETS[p.target].signin_command())

    def start(self, dry_run: bool = False, confirm: bool = True):
        self._store()
        p = self.current()
        if p is None or self._busy:
            return None
        self.save()
        t = cloud.TARGETS[p.target]
        if not dry_run and confirm and QMessageBox.question(
                self, "Deploy", f"Deploy '{p.name}' to {t.label} now?") != QMessageBox.StandardButton.Yes:
            return None
        try:
            steps = cloud.plan(p, self.folder, dry_run, self.secrets(p))
        except cloud.DeployError as ex:
            self.result.setText(str(ex))
            theme.role(self.result, "error")
            return None
        return self._run(steps, "Dry run" if dry_run else "Deploy", None, dry_run=dry_run)

    def _run(self, steps, title, fmt=None, dry_run: bool = False):
        self.log.clear()
        self._append(f"{title}: {len(steps)} step(s)")
        self._busy_ui(True)
        self.result.setText(f"{title} running ...")
        theme.role(self.result, "muted")
        self._cancel = threading.Event()
        cancel = self._cancel

        def work(log):
            return cloud.execute(steps, log, cancel)

        def done(res):
            self._busy_ui(False)
            if isinstance(res, Exception):
                res = cloud.DeployResult(False, str(res))
            res.dry_run = dry_run
            if res.ok and dry_run:
                res.message = "Dry run finished - nothing was changed."
            msg = fmt(res) if fmt else res.message
            self.result.setText(msg)
            theme.role(self.result, "success" if res.ok else "error")
            self._append(("OK: " if res.ok else "FAILED: ") + msg)
            _log(self.win, f"[deploy] {title}: {msg}")
            p = self.current()
            if res.hostkey and p is not None:
                key, fp = res.hostkey
                if QMessageBox.question(self, "Trust this server?",
                                        f"The SSH server's host key is new:\n{fp}\n\nTrust it and continue?") == \
                        QMessageBox.StandardButton.Yes:
                    p.options["host_key"] = key
                    w = self._fields.get("opt:host_key")
                    if w is not None:
                        w.setText(key)
                    self.save()
                    QTimer.singleShot(0, lambda: self.start(dry_run=dry_run, confirm=False))
            elif res.signin_needed and p is not None:
                self.result.setText(msg + " (press 'Sign in (Terminal)...')")
            if res.ok and res.url and not dry_run and p is not None and not p.site_url:
                p.site_url = res.url
                w = self._fields.get("site_url")
                if w is not None:
                    w.setText(res.url)
                self.save()
            self.last_result = res
        self._sig = _thread(work, done, self._append)
        return self._sig

    def cancel(self):
        if self._cancel is not None:
            self._cancel.set()

    def install_cli(self):
        p = self.current()
        if p is None:
            return
        t = cloud.TARGETS[p.target]
        if QMessageBox.question(self, "Install CLI", f"Install the {t.cli_name} CLI with npm into "
                                f"{cloud.npm_cli_dir(t.id)} (nothing global changes)?") != \
                QMessageBox.StandardButton.Yes:
            return
        self._busy_ui(True)
        self.log.clear()

        def done(res):
            self._busy_ui(False)
            ok = isinstance(res, list) and res
            self.result.setText(f"{t.cli_name} installed: {res[0]}" if ok else f"Install failed: {res}")
            theme.role(self.result, "success" if ok else "error")
            self._on_select(self._cur)
        _thread(lambda log: cloud.install_npm_cli(t.id, log), done, self._append)

    def generate_config(self):
        self._store()
        p = self.current()
        if p is None:
            return
        files = cloud.TARGETS[p.target].config_files(p, self.folder)
        written, skipped = dk.write_files(self.folder, files, overwrite=False)
        self.result.setText((f"Wrote {', '.join(written)}." if written else "") +
                            (f" Kept existing {', '.join(skipped)}." if skipped else ""))
        theme.role(self.result, "muted")

    def open_site(self):
        self._store()
        p = self.current()
        if p is not None and p.site_url:
            QDesktopServices.openUrl(QUrl(p.site_url))


class CloudDeployDialog(QDialog):
    """Stand-alone window for projects that are not web sites (the Publish dialog has the same panel)."""

    def __init__(self, win, project, parent=None):
        super().__init__(parent or win)
        self.setWindowTitle(f"Deploy - {project.name}")
        self.resize(980, 680)
        self.panel = CloudDeployPanel(win, project, self)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(self.panel, 1)
        lay.addWidget(bb)

    def done(self, r):  # noqa: D401 - keep the profiles when closing
        try:
            self.panel.save(final=True)
        except Exception:  # noqa: BLE001
            pass
        super().done(r)


def extend_publish_dialog(dlg) -> None:
    """Hook for PublishDialog (web_tools.py): puts the FTP/SFTP/folder page and the Cloud / Git / SSH page in tabs."""
    lay = dlg.layout()
    item = lay.itemAt(0) if lay is not None else None
    page = item.widget() if item is not None else None
    if page is None or getattr(dlg, "publish_tabs", None) is not None:
        return
    tabs = QTabWidget(dlg)
    lay.removeWidget(page)
    tabs.addTab(page, "FTP / SFTP / Folder")
    panel = CloudDeployPanel(dlg.win, dlg.project, tabs)
    tabs.addTab(panel, "Cloud / Git / SSH")
    lay.insertWidget(0, tabs, 1)
    file_buttons = [getattr(dlg, n, None) for n in ("b_test", "b_preview", "b_publish", "b_force", "b_cancel",
                                                    "b_reset", "b_open")]
    tabs.currentChanged.connect(lambda i: [b.setVisible(i == 0) for b in file_buttons if b is not None])
    dlg.publish_tabs = tabs
    dlg.cloud_panel = panel
    dlg.finished.connect(lambda _r: panel.save(final=True))


# ====================================================================== feature object
class DockerCloud(QObject):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.panel = DockerPanel(win)
        d = QDockWidget("Docker", win)
        d.setObjectName("dock_docker")
        d.setWidget(self.panel)
        win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d)
        try:
            win.tabifyDockWidget(win.dock_output, d)
        except Exception:  # noqa: BLE001
            pass
        d.hide()
        d.visibilityChanged.connect(lambda vis: vis and self.panel.cli is None and self.panel.refresh())
        self.dock = d
        win.dock_docker = d

    def show_panel(self):
        self.dock.show()
        self.dock.raise_()
        self.panel.refresh()

    def generate(self):
        return DockerGenerateDialog(self.win, _project_folder(self.win)).exec()

    def deploy(self, standalone: bool | None = None):
        """Site > Deploy to Cloud / Git / SSH: the Publish dialog's Cloud tab for web sites, else a window."""
        proj = getattr(self.win, "project", None)
        if proj is None:
            QMessageBox.information(self.win, "Deploy", "Open a project first.")
            return None
        tools = getattr(self.win, "web_tools", None)
        is_site = False
        try:
            from ..web_site.project import is_website
            is_site = is_website(proj)
        except Exception:  # noqa: BLE001
            pass
        if not standalone and tools is not None and is_site:
            dlg = tools.publish()
            if dlg is not None and getattr(dlg, "publish_tabs", None) is not None:
                dlg.publish_tabs.setCurrentIndex(1)
                return dlg
        dlg = CloudDeployDialog(self.win, proj)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dlg.show()
        return dlg

    def build_menus(self):
        win = self.win
        mb = win.menuBar()
        tools = next((a.menu() for a in mb.actions() if a.text().replace("&", "") == "Tools" and a.menu()), None)
        targets = [m for m in (tools, getattr(win, "site_menu", None)) if m is not None]
        for i, menu in enumerate(targets):
            menu.addSeparator()
            sub = menu.addMenu("&Docker")
            sub.addAction("&Generate Dockerfile / Compose / Dev Container...", self.generate)
            sub.addAction("Docker &Panel", self.show_panel)
            sub.addAction("&Build Image", lambda: (self.show_panel(), self.panel.build()))
            sub.addAction("Compose &Up", lambda: (self.show_panel(), self.panel.compose_up()))
            sub.addAction("Compose &Down", lambda: (self.show_panel(), self.panel.compose_down()))
            sub.addAction("&Lint Dockerfile", lambda: (self.show_panel(), self.panel.lint()))
            menu.addAction("Deploy to Cloud / Git / SSH...", self.deploy)
        try:
            from . import workbench
            workbench.register_view("docker", "Docker", icon="toolbox", factory=lambda w: getattr(w, "dock_docker",
                                                                                                    None),
                                    modes=("vscode", "agent"), area="panel", order=95, tooltip="Docker")
        except Exception as ex:  # noqa: BLE001
            _log(win, f"[docker] workbench view: {ex}")


def install(win) -> None:
    hooks = getattr(win, "publish_dialog_hooks", None)
    if hooks is None:
        hooks = []
        win.publish_dialog_hooks = hooks
    if extend_publish_dialog not in hooks:
        hooks.append(extend_publish_dialog)
    win.docker_cloud = DockerCloud(win)
    # after every feature is installed (the web workspace creates the Site menu)
    QTimer.singleShot(0, win.docker_cloud.build_menus)
