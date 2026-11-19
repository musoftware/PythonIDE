"""Project > Manage Packages... - a NuGet-style package manager dialog.

Works for every language whose plugin sets ``package_manager``
(radide.languages.base.PackageManager, docs/CONTRACTS.md section 3).
Commands are argv lists run with QProcess in the project folder. Placeholders:
``{name}``, ``{version}``, ``{query}`` and ``{interpreter}`` (the interpreter the
IDE uses for that language, e.g. the project's Python for pip).
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTabWidget,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
VERSION_RX = re.compile(r"^v?\d+(?:[.\-+~_]?[0-9A-Za-z]+)*$")
NAME_RX = re.compile(r"^[A-Za-z0-9_@][\w.\-/@:+]*$")
HEADER_WORDS = {"package", "packages", "name", "project", "top-level", "id", "version", "versions",
                "installed", "available", "warning", "error", "info", "note", "usage", "found", "the",
                "command", "requested", "resolved", "directory", "using"}


# ===================================================================== helpers
def parse_packages(text: str) -> list[tuple[str, str, str]]:
    """Best-effort parse of a package tool's list/search output.
    Returns (name, version, description) rows. Understands pip freeze/list,
    npm (name@version), gem/pip-index "name (version)", cargo 'name = "ver"',
    tables with '|' and plain "name version description" columns."""
    rows: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = ANSI.sub("", raw).strip()
        if not line or set(line) <= set("-=+|_ *"):
            continue
        line = re.sub(r"^[\s─-╿`+\\|>*-]+", "", line).strip()
        if not line or line.endswith(":"):
            continue
        name = ver = desc = ""
        m = None
        if "|" in line:
            cells = [c.strip() for c in line.split("|")]
            name = cells[0]
            ver = next((c for c in cells[1:] if VERSION_RX.match(c)), "")
            desc = cells[1] if len(cells) > 1 and cells[1] != ver else ""
        elif (m := re.match(r"^([^\s=]+)\s*===?\s*(\S+)\s*(.*)$", line)):
            name, ver, desc = m.groups()
        elif (m := re.match(r'^([^\s=]+)\s*=\s*"([^"]+)"\s*(?:#\s*(.*))?$', line)):
            name, ver, desc = m.group(1), m.group(2), m.group(3) or ""
        elif (m := re.match(r"^(@?[^\s@]+)@(\S+)\s*(.*)$", line)):
            name, ver, desc = m.groups()
        elif (m := re.match(r"^(\S+)\s+\(([^)]*)\)\s*(.*)$", line)):
            name, desc = m.group(1), m.group(3)
            ver = m.group(2).split(",")[0].replace("default:", "").strip()
        else:
            toks = line.split()
            name = toks[0]
            if len(toks) > 1:
                if not VERSION_RX.match(toks[1]):
                    continue
                ver, desc = toks[1], " ".join(t for t in toks[2:] if not VERSION_RX.match(t))
        name = name.strip().strip(",;")
        if re.match(r"^(?:[A-Za-z]:[\\/]|/)", desc.strip()):
            continue            # "my-app@1.0.0 C:\path" - the project itself (npm ls), not a dependency
        if not name or not NAME_RX.match(name) or name.lower() in HEADER_WORDS:
            continue
        if ver and not VERSION_RX.match(ver):
            ver = ""
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        rows.append((name, ver, desc.strip()))
    return rows


def available_versions(text: str) -> list[str]:
    """'Available versions: 1.2, 1.1' (pip index versions) -> ['1.2', '1.1']."""
    m = re.search(r"Available versions:\s*(.+)", ANSI.sub("", text))
    return [v.strip() for v in m.group(1).split(",") if v.strip()] if m else []


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def update_requirements(path: Path, name: str, version: str | None) -> None:
    """Add/replace (version given) or remove (None) *name* in a requirements.txt."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    out, done = [], False
    for ln in lines:
        m = re.match(r"^\s*([A-Za-z0-9][\w.\-]*)", ln)
        if m and not ln.lstrip().startswith("#") and _norm(m.group(1)) == _norm(name):
            if version is not None and not done:
                out.append(f"{name}=={version}" if version else name)
                done = True
            continue
        out.append(ln)
    if version is not None and not done:
        out.append(f"{name}=={version}" if version else name)
    path.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")


def project_languages(win) -> list:
    """Plugins used by the open project (project language first)."""
    from ..languages import all_plugins, get_plugin
    if win.plugin is None:
        return []
    out = [win.plugin]
    ids = set(getattr(win.project, "form_languages", {}).values())
    finder = getattr(__import__("radide.languages", fromlist=["x"]), "plugin_for_file", None)
    if finder is not None:
        for mod in win.project.modules:
            try:
                p = finder(mod, win.plugin.id)
                ids.add(p.id if hasattr(p, "id") else str(p))
            except Exception:  # noqa: BLE001
                pass
    known = {p.id for p in all_plugins()}
    for pid in sorted(ids):
        if pid in known and pid != win.plugin.id:
            out.append(get_plugin(pid))
    return out


def plugin_interpreter(win, plugin) -> str:
    """The language's configured / detected interpreter (not a project venv)."""
    try:
        return plugin.find_interpreter(win.settings.value(f"interpreter/{plugin.id}", "") or "")
    except Exception:  # noqa: BLE001
        return ""


def is_python(plugin) -> bool:
    return plugin is not None and str(getattr(plugin, "id", "")).startswith("python")


def venv_python(folder: Path) -> str:
    from ..app import project_venv_python
    return project_venv_python(folder)


class ElidedLabel(QLabel):
    """One line of text elided in the middle (long paths), full text in the tool tip."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full = ""
        self.setMinimumWidth(80)
        self.set_full_text(text)

    def set_full_text(self, text: str):
        self._full = text
        self.setToolTip(text)
        self._elide()

    def full_text(self) -> str:
        return self._full

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._elide()

    def _elide(self):
        w = max(40, self.width() - 4)
        super().setText(self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideMiddle, w))


def resolve_tool(tool: str, interpreter: str) -> str:
    """Find a package tool: absolute path, PATH, or next to the language's interpreter."""
    if not tool:
        return ""
    if tool in ("{interpreter}", "{python}"):
        return interpreter
    if os.path.isabs(tool):
        return tool if Path(tool).exists() else ""
    found = shutil.which(tool)
    if found:
        return found
    if interpreter:
        base = Path(interpreter).parent
        for ext in ("", ".exe", ".cmd", ".bat"):
            cand = base / f"{tool}{ext}"
            if cand.is_file():
                return str(cand)
    return ""


def build_argv(cmd: list[str], pm, interpreter: str, name: str = "", version: str = "",
               query: str = "") -> list[str]:
    """Fill placeholders. With an empty version, a "{version}" argument (and an option
    such as "--version" right before it) is dropped, and "{name}=={version}" style
    arguments become just the name."""
    out: list[str] = []
    for arg in cmd:
        if "{version}" in arg and not version:
            if arg.strip() == "{version}":
                if out and out[-1].startswith("-"):
                    out.pop()
                continue
            arg = re.sub(r"[=@:<>~^ ]*\{version\}", "", arg)
            if not arg:
                continue
        arg = (arg.replace("{name}", name).replace("{version}", version).replace("{query}", query)
               .replace("{interpreter}", interpreter).replace("{python}", interpreter))
        out.append(arg)
    if out and cmd[0] not in ("{interpreter}", "{python}") and not os.path.isabs(out[0]):
        resolved = resolve_tool(out[0], interpreter)
        if resolved:
            out[0] = resolved
    # .cmd / .bat tools (npm.cmd, composer.bat) are started directly: QProcess quotes their
    # arguments correctly, wrapping them in "cmd /c" would not
    return out


# ------------------------------------------------------------------ RingPM (local files)
def _ringpm_home(tool_path: str) -> Path | None:
    if not tool_path:
        return None
    home = Path(tool_path).parent.parent / "tools" / "ringpm"
    return home if home.exists() else None


def _ring_field(text: str, key: str) -> str:
    m = re.search(rf":{key}\s*=\s*\"([^\"]*)\"", text, re.I)
    return m.group(1) if m else ""


def ringpm_installed(tool_path: str) -> list[tuple[str, str, str]] | None:
    """RingPM prints package ids with console colours, which are lost through a pipe -
    so read its packages folder directly."""
    home = _ringpm_home(tool_path)
    if home is None or not (home / "packages").exists():
        return None
    rows = []
    for info in sorted((home / "packages").glob("*/package.ring")):
        t = info.read_text(encoding="utf-8", errors="replace")
        rows.append((_ring_field(t, "folder") or info.parent.name, _ring_field(t, "version"),
                     _ring_field(t, "description") or _ring_field(t, "name")))
    return rows


def ringpm_search(tool_path: str, query: str) -> list[tuple[str, str, str]] | None:
    home = _ringpm_home(tool_path)
    reg = home / "registry" / "registry.ring" if home else None
    if reg is None or not reg.exists():
        return None
    text = reg.read_text(encoding="utf-8", errors="replace")
    q = query.lower().split()
    rows = []
    for m in re.finditer(r":name\s*=\s*\"([^\"]*)\"\s*,\s*:description\s*=\s*\"([^\"]*)\"", text, re.I):
        name, desc = m.groups()
        if not q or any(w in name.lower() or w in desc.lower() for w in q):
            rows.append((name, "", desc))
    return rows


NATIVE_LIST = {"ringpm": ringpm_installed}
NATIVE_SEARCH = {"ringpm": ringpm_search}


# ===================================================================== process runner
class CommandRunner(QObject):
    """Runs argv lists one after the other (QProcess), streaming output."""
    output = pyqtSignal(str)
    busyChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proc: QProcess | None = None
        self.queue: list[tuple[list[str], str, object]] = []
        self._buf = b""

    def busy(self) -> bool:
        return self.proc is not None

    def run(self, argv: list[str], cwd: str, done=None, quiet: bool = False,
            env: dict[str, str] | None = None) -> None:
        """done(exit_code, full_output) is called when the command ends. *quiet*: the output is
        not streamed to the log (listings) - only the command line and a failure are shown.
        *env*: extra environment variables (PackageManager.env)."""
        self.queue.append((argv, cwd, done, quiet, env))
        if self.proc is None:
            self._next()

    def _next(self):
        if not self.queue:
            self.busyChanged.emit(False)
            return
        argv, cwd, done, quiet, extra_env = self.queue.pop(0)
        self._quiet = quiet
        self._buf = b""
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.setWorkingDirectory(cwd)
        env = QProcessEnvironment.systemEnvironment()
        for k, v in (("PYTHONIOENCODING", "utf-8"), ("PIP_DISABLE_PIP_VERSION_CHECK", "1"),
                     ("NO_COLOR", "1"), ("PIP_NO_INPUT", "1"), ("DOTNET_CLI_TELEMETRY_OPTOUT", "1")):
            env.insert(k, v)
        for k, v in (extra_env or {}).items():
            env.insert(k, v)
        p.setProcessEnvironment(env)
        p.readyReadStandardOutput.connect(self._read)
        p.finished.connect(lambda code, _st, d=done: self._finished(code, d))
        p.errorOccurred.connect(lambda err, d=done, a=argv: self._error(err, a, d))
        self.proc = p
        self.busyChanged.emit(True)
        self.output.emit(f"> {' '.join(_q(a) for a in argv)}\n")
        p.start(argv[0], argv[1:])

    @staticmethod
    def _decode(data: bytes) -> str:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("mbcs" if sys.platform == "win32" else "latin-1", errors="replace")

    def _read(self):
        if self.proc is None:
            return
        data = bytes(self.proc.readAllStandardOutput())
        self._buf += data
        if getattr(self, "_quiet", False):
            return
        self.output.emit(ANSI.sub("", self._decode(data)).replace("\r\n", "\n").replace("\r", "\n"))

    def _finished(self, code, done):
        if self.proc is None:
            return
        self._read()
        text = ANSI.sub("", self._decode(self._buf)).replace("\r\n", "\n")
        self.proc.deleteLater()
        self.proc = None
        if getattr(self, "_quiet", False):
            if code != 0:
                tail = "\n".join(text.strip().splitlines()[-6:])
                self.output.emit(f"{tail}\n[failed, exit code {code}]\n")
        else:
            self.output.emit(f"[exit code {code}]\n")
        if done is not None:
            done(code, text)
        self._next()

    def _error(self, err, argv, done):
        if err != QProcess.ProcessError.FailedToStart or self.proc is None:
            return
        self.output.emit(f"*** Cannot start {argv[0]}\n")
        self.proc.deleteLater()
        self.proc = None
        if done is not None:
            done(-1, "")
        self._next()

    def stop(self):
        self.queue.clear()
        if self.proc is not None:
            self.proc.kill()

    def wait(self, msecs: int = 120_000) -> None:
        """Block until the queue is empty (used by tests and scripts)."""
        from PyQt6.QtCore import QCoreApplication, QElapsedTimer
        t = QElapsedTimer()
        t.start()
        while (self.proc is not None or self.queue) and t.elapsed() < msecs:
            if self.proc is not None:
                self.proc.waitForFinished(100)
            QCoreApplication.processEvents()
        QCoreApplication.processEvents()


def _q(a: str) -> str:
    return f'"{a}"' if " " in a else a


def _short(path: str) -> str:
    """A long interpreter path shortened for the info lines (the full one is in the log)."""
    if len(path) <= 70:
        return path
    p = Path(path)
    return f"{p.anchor}...\\{p.parent.parent.name}\\{p.parent.name}\\{p.name}"


# ===================================================================== dialog
class PackagesDialog(QDialog):
    def __init__(self, win, plugin=None):
        super().__init__(win)
        self.win = win
        self.setWindowTitle(f"Manage Packages - {win.project.name}")
        self.resize(820, 600)
        self.plugins = [p for p in project_languages(win)]
        self.runner = CommandRunner(self)
        self.runner.output.connect(self._log)
        self.runner.busyChanged.connect(self._on_busy)

        self.lang = QComboBox()
        for p in self.plugins:
            pm = p.package_manager
            self.lang.addItem(f"{p.display_name}  -  {pm.name if pm else 'no package manager'}", p.id)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.btn_init = QPushButton("Create Manifest")
        self.btn_init.clicked.connect(self.create_manifest)
        top = QHBoxLayout()
        top.addWidget(QLabel("Language:"))
        top.addWidget(self.lang, 1)
        top.addWidget(self.btn_init)
        # Python: packages go into the project's own virtual environment (.venv) by default
        self.env = QComboBox()
        self.env.addItem("Project virtual environment (.venv) - recommended", "venv")
        self.env.addItem("Global interpreter (shared by every project)", "global")
        self.env.setToolTip("The project's .venv keeps its packages separate from other projects. It is "
                            "created on the first install; Run and Debug then use it automatically.")
        self.env_label = QLabel("Install into:")
        env_row = QHBoxLayout()
        env_row.addWidget(self.env_label)
        env_row.addWidget(self.env, 1)
        self.folder_lbl = ElidedLabel()
        self.folder_lbl.setProperty("radRole", "muted")

        # --- Browse tab
        self.query = QLineEdit(placeholderText="Search packages (Enter)")
        self.query.returnPressed.connect(self.search)
        self.btn_search = QPushButton("Search")
        self.btn_search.clicked.connect(self.search)
        self.btn_web = QPushButton("Open Website")
        self.btn_web.clicked.connect(self.open_website)
        srow = QHBoxLayout()
        srow.addWidget(self.query, 1)
        srow.addWidget(self.btn_search)
        srow.addWidget(self.btn_web)
        self.search_hint = QLabel()
        self.search_hint.setWordWrap(True)
        self.search_hint.setProperty("radRole", "muted")
        self.results = QTreeWidget()
        self.results.setHeaderLabels(["Package", "Version", "Description"])
        self.results.setColumnWidth(0, 220)
        self.results.setColumnWidth(1, 90)
        self.results.setRootIsDecorated(False)
        self.results.currentItemChanged.connect(self._pick_result)
        self.name = QLineEdit(placeholderText="package name")
        self.version = QComboBox()
        self.version.setEditable(True)
        self.version.setMinimumWidth(140)
        self.version.lineEdit().setPlaceholderText("latest")
        self.btn_install = QPushButton("Install")
        self.btn_install.clicked.connect(self.install)
        irow = QHBoxLayout()
        irow.addWidget(QLabel("Package:"))
        irow.addWidget(self.name, 1)
        irow.addWidget(QLabel("Version:"))
        irow.addWidget(self.version)
        irow.addWidget(self.btn_install)
        browse = QWidget()
        bl = QVBoxLayout(browse)
        bl.addLayout(srow)
        bl.addWidget(self.search_hint)
        bl.addWidget(self.results, 1)
        bl.addLayout(irow)

        # --- Installed tab
        self.installed = QTreeWidget()
        self.installed.setHeaderLabels(["Package", "Version", "Description"])
        self.installed.setColumnWidth(0, 260)
        self.installed.setRootIsDecorated(False)
        self.installed.setSortingEnabled(True)
        self.installed.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.installed.itemDoubleClicked.connect(self._installed_to_browse)
        self.filter = QLineEdit(placeholderText="Filter")
        self.filter.textChanged.connect(self._apply_filter)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh_installed)
        self.btn_uninstall = QPushButton("Uninstall")
        self.btn_uninstall.clicked.connect(self.uninstall)
        self.btn_update = QPushButton("Update...")
        self.btn_update.setToolTip("Install another version of the selected package")
        self.btn_update.clicked.connect(lambda: self._installed_to_browse(self.installed.currentItem()))
        brow = QHBoxLayout()
        brow.addWidget(self.filter, 1)
        brow.addWidget(self.btn_refresh)
        brow.addWidget(self.btn_update)
        brow.addWidget(self.btn_uninstall)
        inst = QWidget()
        il = QVBoxLayout(inst)
        il.addWidget(self.installed, 1)
        il.addLayout(brow)

        self.tabs = QTabWidget()
        self.tabs.addTab(browse, "Browse")
        self.tabs.addTab(inst, "Installed")

        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.setFont(QFont("Consolas", 9))
        self.out.setMaximumBlockCount(5000)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.runner.stop)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        self.status = QLabel()
        bottom = QHBoxLayout()
        bottom.addWidget(self.status, 1)
        bottom.addWidget(self.btn_stop)
        bottom.addWidget(close)

        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.tabs)
        split.addWidget(self.out)
        split.setSizes([400, 160])
        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addLayout(env_row)
        lay.addWidget(self.info)
        lay.addWidget(self.folder_lbl)
        lay.addWidget(split, 1)
        lay.addLayout(bottom)

        self.lang.currentIndexChanged.connect(lambda _i: self._on_language())
        self.env.currentIndexChanged.connect(lambda _i: self._on_env())
        if plugin is not None and plugin in self.plugins:
            self.lang.setCurrentIndex(self.plugins.index(plugin))
        self._on_language()

    # ------------------------------------------------------------ state
    @property
    def plugin(self):
        return self.plugins[self.lang.currentIndex()] if self.plugins else None

    @property
    def pm(self):
        return self.plugin.package_manager if self.plugin else None

    def folder(self) -> Path:
        return self.win.project.folder

    def _env_key(self) -> str:
        return "packages/env/" + str(self.folder()).replace("\\", "/").replace("/", "|")

    def uses_venv(self) -> bool:
        return is_python(self.plugin) and self.env.currentData() == "venv"

    def base_interpreter(self) -> str:
        return plugin_interpreter(self.win, self.plugin)

    def interpreter(self) -> str:
        """Python with "Install into: .venv": the venv's python ("" until it is created)."""
        if self.uses_venv():
            return venv_python(self.folder())
        return self.base_interpreter()

    def _on_env(self):
        if not getattr(self, "_env_loading", False):
            self.win.settings.setValue(self._env_key(), self.env.currentData())
        self._on_language()

    def tool_path(self) -> str:
        if self.uses_venv() and not self.interpreter():
            return self.base_interpreter()              # pip of the venv-to-be (created on install)
        return resolve_tool(self.pm.tool, self.interpreter()) if self.pm else ""

    def manifest_path(self) -> Path | None:
        return self.folder() / self.pm.manifest if self.pm and self.pm.manifest else None

    def _on_language(self):
        pm = self.pm
        py = is_python(self.plugin)
        self.env.setVisible(py)
        self.env_label.setVisible(py)
        if py:
            self._env_loading = True
            saved = str(self.win.settings.value(self._env_key(), "") or "")
            if not saved:       # an existing .venv or a new project: venv; old projects keep the global one
                saved = "venv"
            self.env.setCurrentIndex(max(0, self.env.findData(saved)))
            self._env_loading = False
        self.folder_lbl.set_full_text(f"Project folder: {self.folder()}")
        self.search_hint.setText(self._search_hint())
        self.results.clear()
        self.installed.clear()
        self.version.clear()
        if pm is None:
            self.info.setText(f"<b>{self.plugin.display_name if self.plugin else 'This project'}</b> has no "
                              "package manager. Libraries can be added as code modules "
                              "(Project &gt; Add Existing Item...).")
            for w in (self.btn_init, self.btn_search, self.btn_web, self.btn_install, self.btn_refresh,
                      self.btn_uninstall, self.btn_update):
                w.setEnabled(False)
            return
        tool = self.tool_path()
        interp = self.interpreter()
        from html import escape
        from .. import theme
        err, note = theme.color("error"), theme.color("note")
        lines = [f"<b>{pm.name}</b>: " + (escape(_short(tool)) if tool else
                                          f"<span style='color:{err}'>'{pm.tool}' was not found "
                                          "(install it or set the path in Tools &gt; Options)</span>")]
        if self.uses_venv():
            if interp:
                lines.append("Environment: project <b>.venv</b> (Run and Debug use it too)")
            else:
                lines.append(f"Environment: <span style='color:{note}'>no .venv yet - it is created with "
                             f"{escape(_short(self.base_interpreter()) or 'Python')} on the first install</span>")
        elif "{interpreter}" in " ".join(pm.install_cmd or []) and interp:
            own = Path(interp).resolve() == Path(sys.executable).resolve()
            lines.append(f"Interpreter: {escape(_short(interp))}" +
                         ("  <i>(the IDE's own Python - packages are shared with the IDE)</i>" if own else
                          "  <i>(global - shared by every project)</i>"))
        mp = self.manifest_path()
        if mp is not None:
            lines.append(f"Manifest: {pm.manifest} " + ("(found)" if mp.exists() else
                                                         f"<span style='color:{note}'>(missing - it is created "
                                                         "on the first install)</span>"))
        self.info.setText("<br>".join(lines))
        ok = bool(tool)
        self.btn_init.setVisible(mp is not None)
        self.btn_init.setEnabled(ok and mp is not None and not mp.exists())
        self.btn_search.setEnabled(ok and (bool(pm.search_cmd) or self._native_search() is not None)
                                   or bool(pm.search_url))
        self.btn_web.setEnabled(bool(pm.search_url))
        self.btn_install.setEnabled(ok and bool(pm.install_cmd))
        self.btn_uninstall.setEnabled(ok and bool(pm.uninstall_cmd))
        self.btn_update.setEnabled(ok and bool(pm.install_cmd))
        self.btn_refresh.setEnabled(ok)
        if ok and self.uses_venv() and not interp:
            self._fill_installed([])
            self._log("No project .venv yet: the Installed list is empty until the first install.\n")
        elif ok:
            self.refresh_installed()

    def _search_hint(self) -> str:
        pm = self.pm
        if pm is None:
            return ""
        if is_python(self.plugin):
            return ("Type the exact package name (for example <b>requests</b>) and press Enter: pip shows the "
                    "versions you can install. Open Website searches pypi.org by keyword.")
        if pm.search_cmd:
            return "Type a package name or keyword and press Enter."
        return "Open Website to find packages, then type the name below and Install."

    def _native_key(self) -> str:
        return Path(self.pm.tool).stem.lower() if self.pm else ""

    def _native_search(self):
        return NATIVE_SEARCH.get(self._native_key())

    def _on_busy(self, busy: bool):
        self.btn_stop.setEnabled(busy)
        self.status.setText("Working..." if busy else "")

    def _log(self, text: str):
        self.out.moveCursor(self.out.textCursor().MoveOperation.End)
        self.out.insertPlainText(text)
        self.out.ensureCursorVisible()

    def _argv(self, cmd, **kw) -> list[str]:
        return build_argv(cmd, self.pm, self.interpreter() or self.base_interpreter(), **kw)

    def _run(self, cmd, done=None, quiet: bool = False, **kw):
        argv = self._argv(cmd, **kw)
        if not argv:
            return
        self.runner.run(argv, str(self.folder()), done, quiet, env=getattr(self.pm, "env", None))

    def ensure_venv(self, then) -> None:
        """Create <project>/.venv with the chosen Python when it is missing, then call *then*."""
        if not self.uses_venv() or self.interpreter():
            then()
            return
        base = self.base_interpreter()
        if not base:
            QMessageBox.warning(self, "Virtual environment", "No Python interpreter was found to create the "
                                "project's .venv (Tools > Options > Languages).")
            return
        self._log("Creating the project's virtual environment (.venv)...\n")

        def done(code, _text):
            if code == 0 and self.interpreter():
                self._log(f"Created .venv ({_short(self.interpreter())})\n")
                self.win.log(f"[packages] created {self.folder() / '.venv'}")
                self._on_language()
                then()
            else:
                self.status.setText("Could not create the .venv (see the log)")
        from ..app import real_python
        self.runner.run([real_python(base), "-m", "venv", ".venv"], str(self.folder()), done, True)

    # ------------------------------------------------------------ installed
    def refresh_installed(self):
        pm = self.pm
        if pm is None:
            return
        native = NATIVE_LIST.get(self._native_key())
        rows = native(self.tool_path()) if native else None
        if rows is not None:
            self._fill_installed(rows)
            return
        if not pm.list_cmd:
            mp = self.manifest_path()
            if mp is not None and mp.exists():
                self._fill_installed(parse_packages(mp.read_text(encoding="utf-8", errors="replace")))
            return
        self._run(pm.list_cmd, lambda code, text: self._fill_installed(parse_packages(text), log=True)
                  if code == 0 else None, quiet=True)

    def _fill_installed(self, rows, log: bool = False):
        if log:
            self._log(f"{len(rows)} package(s) installed in this environment.\n")
        self.installed.setSortingEnabled(False)
        self.installed.clear()
        for name, ver, desc in rows:
            QTreeWidgetItem(self.installed, [name, ver, desc])
        self.installed.setSortingEnabled(True)
        self.tabs.setTabText(1, f"Installed ({len(rows)})")
        self._apply_filter(self.filter.text())

    def installed_packages(self) -> dict[str, str]:
        out = {}
        for i in range(self.installed.topLevelItemCount()):
            it = self.installed.topLevelItem(i)
            out[it.text(0)] = it.text(1)
        return out

    def _apply_filter(self, text: str):
        t = text.lower()
        for i in range(self.installed.topLevelItemCount()):
            it = self.installed.topLevelItem(i)
            it.setHidden(bool(t) and t not in it.text(0).lower())

    def _installed_to_browse(self, item):
        if item is None:
            return
        self.name.setText(item.text(0))
        self.version.setEditText(item.text(1))
        self.tabs.setCurrentIndex(0)
        if self.pm and self.pm.search_cmd:
            self.query.setText(item.text(0))
            self.search()

    # ------------------------------------------------------------ browse
    def search(self):
        pm, q = self.pm, self.query.text().strip()
        if pm is None:
            return
        native = self._native_search()
        if native is not None:
            rows = native(self.tool_path(), q)
            if rows is not None:
                self._fill_results(rows, [])
                return
        if pm.search_cmd and self.tool_path():
            if not q and "{query}" in " ".join(pm.search_cmd):
                return
            self._run(pm.search_cmd, lambda code, text: self._fill_results(parse_packages(text),
                                                                           available_versions(text)),
                      quiet=True, query=q)
        elif pm.search_url:
            self.open_website()

    def _fill_results(self, rows, versions):
        self.results.clear()
        for name, ver, desc in rows:
            it = QTreeWidgetItem(self.results, [name, ver, desc])
            it.setData(0, Qt.ItemDataRole.UserRole, versions if len(rows) == 1 else [])
        self.status.setText(f"{len(rows)} package(s) found" if rows else "No packages found")
        if rows:
            self.results.setCurrentItem(self.results.topLevelItem(0))

    def _pick_result(self, item, _prev=None):
        if item is None:
            return
        self.name.setText(item.text(0))
        versions = item.data(0, Qt.ItemDataRole.UserRole) or ([item.text(1)] if item.text(1) else [])
        self.version.clear()
        self.version.addItem("")          # "" = latest
        self.version.addItems(versions)

    def open_website(self):
        if self.pm and self.pm.search_url:
            webbrowser.open(self.pm.search_url.replace("{query}", quote_plus(self.query.text().strip())))

    # ------------------------------------------------------------ install / uninstall
    def create_manifest(self, then=None):
        pm, mp = self.pm, self.manifest_path()
        if pm is None or mp is None or mp.exists():
            if then:
                then()
            return
        if pm.init_cmd:
            def done(code, _text):
                self._on_language_info()
                if code == 0 and then:
                    then()
            self._run(pm.init_cmd, done, name=self.win.project.name)
        else:
            mp.write_text("", encoding="utf-8")
            self._on_language_info()
            if then:
                then()

    def _on_language_info(self):
        mp = self.manifest_path()
        self.btn_init.setEnabled(bool(mp is not None and not mp.exists() and self.tool_path()))
        if mp is not None:
            self.info.setText(re.sub(r"Manifest: [^<]*(?:<span[^>]*>[^<]*</span>)?",
                                     f"Manifest: {self.pm.manifest} " + ("(found)" if mp.exists() else "(missing)"),
                                     self.info.text()))

    def install(self, name: str | None = None, version: str | None = None):
        pm = self.pm
        name = (name if isinstance(name, str) else self.name.text()).strip()
        version = (version if isinstance(version, str) else self.version.currentText()).strip()
        if pm is None or not pm.install_cmd or not name:
            return
        if not re.match(r"^[\w@./:+\-\[\],]+$", name):
            QMessageBox.warning(self, "Install", f"'{name}' is not a valid package name.")
            return
        self.ensure_venv(lambda: self.create_manifest(then=lambda: self._run(
            pm.install_cmd, lambda code, text: self._after_change(code, name, version, True, text),
            quiet=True, name=name, version=version)))

    def uninstall(self, name: str | None = None):
        pm = self.pm
        if pm is None or not pm.uninstall_cmd:
            return
        if not isinstance(name, str):
            it = self.installed.currentItem()
            if it is None:
                return
            name = it.text(0)
            if QMessageBox.question(self, "Uninstall", f"Uninstall '{name}'?") != QMessageBox.StandardButton.Yes:
                return
        self._run(pm.uninstall_cmd, lambda code, text: self._after_change(code, name, "", False, text),
                  quiet=True, name=name)

    def _after_change(self, code: int, name: str, version: str, installed: bool, text: str = ""):
        if code != 0:
            self.status.setText(f"{'Install' if installed else 'Uninstall'} of {name} failed (exit code {code})")
            return
        summary = next((ln.strip() for ln in reversed(text.splitlines())
                        if ln.strip().lower().startswith(("successfully", "requirement already satisfied"))), "")
        self._log((summary or f"{name} {'installed' if installed else 'uninstalled'}") + "\n")
        self.status.setText(f"{name} {'installed' if installed else 'uninstalled'}")
        self.win.log(f"[packages] {self.pm.name}: {name} {'installed' if installed else 'uninstalled'}")
        mp = self.manifest_path()
        sync = mp is not None and mp.name.lower() == "requirements.txt"

        def refreshed(_code=0, text=""):
            if text:
                self._fill_installed(parse_packages(text))
            if sync:
                ver = next((v for n, v in self.installed_packages().items() if _norm(n) == _norm(name)), version)
                update_requirements(mp, name, ver if installed else None)
                self._on_language_info()
        if self.pm.list_cmd and not NATIVE_LIST.get(self._native_key()):
            self._run(self.pm.list_cmd, refreshed, quiet=True)
        else:
            self.refresh_installed()
            refreshed()

    def closeEvent(self, e):
        self.runner.stop()
        super().closeEvent(e)


# ===================================================================== install
def manage_packages(win, plugin=None):
    if not win.project:
        QMessageBox.information(win, "Manage Packages", "Open a project first.")
        return None
    langs = project_languages(win)
    if not any(p.package_manager for p in langs):
        QMessageBox.information(win, "Manage Packages",
                                f"{win.plugin.display_name} has no package manager.\n\n"
                                "Add libraries as code modules with Project > Add Existing Item...")
        return None
    dlg = PackagesDialog(win, plugin)
    win._packages_dialog = dlg
    dlg.show()
    return dlg


def install(win) -> None:
    proj = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Project"), None)
    if proj is None:
        return
    proj.addSeparator()
    a = proj.addAction("Manage &Packages...", lambda: manage_packages(win))
    a.setObjectName("actManagePackages")
    win.a_manage_packages = a


__all__ = ["PackagesDialog", "manage_packages", "parse_packages", "build_argv", "update_requirements",
           "resolve_tool", "CommandRunner"]
