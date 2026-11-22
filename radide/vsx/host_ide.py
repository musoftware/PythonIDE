"""The extension host inside RAD IDE: editors, UI and language features for VS Code extensions with code.

``install(win)`` (radide/features/vsx_host.py) creates ``win.vsx_host`` (a ``VsxService``) which
  * starts ``node radide/vsx/host/main.js`` (bridge.py) with the enabled extensions that have a "main"
    entry, restarts it on "Reload" (radide.vsx.on_reload_requested) and stops it with the window;
  * mirrors every Monaco editor into the host (document/open|change|save|close, active editor, selection);
  * shows the UI the extensions ask for: messages (with buttons), quick picks, input boxes, open / save
    dialogs, output channels (an "Extension Output" dock), status bar items, progress, terminals
    (the "Extension Terminals" dock), snippets, decorations, diff tabs, tab groups, URI handlers (workbench_ui.py);
  * applies workspace edits, saves documents, keeps VS Code settings (contrib_configuration) in sync;
  * routes language features: editors whose language has extension providers get a CompositeClient in
    ``editor.lsp`` (lsp_client.py) - completion, hover, definition, signature help, formatting, code actions,
    rename, inlay hints - and extension diagnostics as Monaco markers;
  * contributed commands go to the Command Palette (when / enablement honoured), "editor/context" menu items
    to the editor's context menu, keybindings reach the host through contrib_keybindings.COMMAND_HANDLERS;
  * contributed debuggers: F5 / Debug > "Debug with Extension Debugger" (debuggers.py);
  * a language-server extension that cannot run in the host falls back to the IDE's LSP client
    (lsp_fallback.py).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import weakref
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox, QDockWidget,
                             QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                             QPlainTextEdit, QToolButton, QVBoxLayout, QWidget)

from . import when as W
from .bridge import VsxHost, find_node
from .lsp_client import CompositeClient, ProviderIndex, editor_lang

CODICONS = {"check": "✓", "error": "⊗", "warning": "⚠", "info": "ⓘ", "sync": "⟳", "sync~spin": "⟳", "loading~spin": "⟳",
            "gear": "⚙", "smiley": "☺", "bell": "🔔", "close": "✕", "add": "+", "play": "▶", "debug-alt": "▶",
            "debug-start": "▶", "run": "▶", "stop": "■", "search": "⌕", "arrow-up": "↑", "arrow-down": "↓",
            "arrow-left": "←", "arrow-right": "→", "circle-filled": "●", "circle-outline": "○", "star": "☆",
            "star-full": "★", "heart": "♥", "pass": "✓", "pass-filled": "✓", "x": "✕", "flame": "♨",
            "zap": "⚡", "rocket": "↗", "lock": "🔒", "key": "⚿", "file": "□", "folder": "▭", "edit": "✎",
            "pencil": "✎", "trash": "⌫", "refresh": "⟳", "home": "⌂", "tools": "⚒", "symbol-method": "ƒ",
            "bracket": "{}", "json": "{}", "code": "</>", "terminal": ">_", "cloud": "☁", "globe": "🌐",
            "account": "👤", "copilot": "✦", "sparkle": "✦", "lightbulb": "💡", "megaphone": "📣"}
_ICON_RX = re.compile(r"\$\(([a-z0-9\-~]+)\)")


def codicons(text: str) -> str:
    return _ICON_RX.sub(lambda m: CODICONS.get(m.group(1), ""), text or "").strip()


def _portable() -> bool:
    try:
        from .. import paths
        return bool(paths.portable())
    except Exception:  # noqa: BLE001
        return False


def _key(p) -> str:
    try:
        return str(Path(p).resolve()).lower()
    except (OSError, ValueError):
        return str(p).lower()


# ============================================================================ dialogs
class QuickPickDialog(QDialog):
    def __init__(self, parent, items: list, title: str = "", placeholder: str = "", many: bool = False, value: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title or "Quick Pick")
        self.resize(560, 380)
        self.items = items
        self.many = many
        lay = QVBoxLayout(self)
        self.filter = QLineEdit(value)
        self.filter.setPlaceholderText(placeholder or "Type to filter")
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for i, it in enumerate(items):
            label = codicons(str(it.get("label") or ""))
            if it.get("kind") == -1:
                li = QListWidgetItem(f"── {label} ──")
                li.setFlags(Qt.ItemFlag.NoItemFlags)
            else:
                extra = "  —  " + codicons(it["description"]) if it.get("description") else ""
                li = QListWidgetItem(label + extra + ("\n    " + codicons(it["detail"]) if it.get("detail") else ""))
                if many:
                    li.setFlags(li.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    li.setCheckState(Qt.CheckState.Checked if it.get("picked") else Qt.CheckState.Unchecked)
            li.setData(Qt.ItemDataRole.UserRole, i)
            self.list.addItem(li)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(self.filter)
        lay.addWidget(self.list, 1)
        lay.addWidget(bb)
        self.filter.textChanged.connect(self._filter)
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        self.filter.returnPressed.connect(self.accept)
        self._filter(value)

    def _filter(self, text):
        t = text.lower()
        first = None
        for i in range(self.list.count()):
            li = self.list.item(i)
            hide = bool(t) and t not in li.text().lower()
            li.setHidden(hide)
            if not hide and first is None and li.flags() & Qt.ItemFlag.ItemIsEnabled:
                first = li
        if first is not None:
            self.list.setCurrentItem(first)

    def result_value(self):
        if self.many:
            return [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())
                    if self.list.item(i).checkState() == Qt.CheckState.Checked]
        li = self.list.currentItem()
        return li.data(Qt.ItemDataRole.UserRole) if li is not None and not li.isHidden() else None


class InputDialog(QDialog):
    def __init__(self, parent, title="", prompt="", value="", placeholder="", password=False, message=""):
        super().__init__(parent)
        self.setWindowTitle(title or "Input")
        self.resize(460, 140)
        lay = QVBoxLayout(self)
        if prompt:
            lab = QLabel(prompt)
            lab.setWordWrap(True)
            lay.addWidget(lab)
        self.edit = QLineEdit(value)
        self.edit.setPlaceholderText(placeholder)
        if password:
            self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        lay.addWidget(self.edit)
        if message:
            m = QLabel(message)
            m.setStyleSheet("color: #d13438;")
            m.setWordWrap(True)
            lay.addWidget(m)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.edit.selectAll()


class OutputPanel(QWidget):
    """'Extension Output': one text per output channel (like VS Code's Output view)."""
    MAX = 400_000

    def __init__(self):
        super().__init__()
        self.texts: dict[str, str] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Channel:"))
        self.combo = QComboBox()
        self.combo.setMinimumWidth(220)
        bar.addWidget(self.combo)
        clear = QToolButton(text="Clear")
        clear.clicked.connect(lambda: self.clear(self.combo.currentText()))
        bar.addWidget(clear)
        bar.addStretch(1)
        lay.addLayout(bar)
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setFont(QFont("Consolas", 9))
        self.view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        lay.addWidget(self.view, 1)
        self.combo.currentTextChanged.connect(self._show)

    def ensure(self, name: str):
        if name not in self.texts:
            self.texts[name] = ""
            self.combo.addItem(name)

    def append(self, name: str, text: str):
        self.ensure(name)
        t = self.texts[name] + text
        if len(t) > self.MAX:
            t = t[-self.MAX:]
        self.texts[name] = t
        if self.combo.currentText() == name:
            sb = self.view.verticalScrollBar()
            at_end = sb.value() >= sb.maximum() - 4
            self.view.moveCursor(self.view.textCursor().MoveOperation.End)
            self.view.insertPlainText(text)
            if at_end:
                sb.setValue(sb.maximum())

    def replace(self, name: str, text: str):
        self.ensure(name)
        self.texts[name] = text
        if self.combo.currentText() == name:
            self._show(name)

    def clear(self, name: str):
        if name in self.texts:
            self.texts[name] = ""
            if self.combo.currentText() == name:
                self.view.clear()

    def select(self, name: str):
        self.ensure(name)
        self.combo.setCurrentText(name)

    def remove(self, name: str):
        if name in self.texts:
            del self.texts[name]
            i = self.combo.findText(name)
            if i >= 0:
                self.combo.removeItem(i)

    def _show(self, name):
        self.view.setPlainText(self.texts.get(name, ""))
        self.view.moveCursor(self.view.textCursor().MoveOperation.End)


# ============================================================================ the service
class VsxService(QObject):
    HOST_CHANNEL = "Extension Host"

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.host = VsxHost(self)
        self.index = ProviderIndex()
        self.host_commands: set[str] = set()
        self.context: dict = {}
        self.lang_configs: dict = {}
        self.deco_types: dict = {}
        self.diags: dict[str, dict] = {}            # path key -> {owner: [ide diags]}
        self.status_items: dict[str, QToolButton] = {}
        self.terminals: dict[str, dict] = {}
        self.unsupported: list[tuple[str, str]] = []
        self.activation: dict[str, str] = {}         # id -> "active" | error
        self.extensions: list = []
        self._editors: "weakref.WeakSet" = weakref.WeakSet()
        self._synced: dict[str, str] = {}
        self._versions: dict[str, int] = {}
        self._palette_ids: list[str] = []
        self._active_sent = None
        self._fallback_done: set[str] = set()
        self.output = OutputPanel()
        self.dock = None
        from .webview_ui import WebviewManager
        self.webviews = WebviewManager(self)
        from .views_ui import ViewsUI
        self.views = ViewsUI(self)                  # view containers, tree views, view/title + view/item menus
        self._view_docks = self.views.docks
        from . import context_keys
        context_keys.install(self)                  # focus tracking for editorFocus / sideBarFocus / focusedView ...
        self.host.notification.connect(self._on_notification)
        self.host.stderr.connect(lambda t: self.output.append(self.HOST_CHANNEL, t))
        self.host.stopped.connect(self._on_stopped)
        self.host.started.connect(self._on_started)
        self._register_handlers()
        from .workbench_ui import WorkbenchUI
        self.workbench = WorkbenchUI(self)          # diffs, tabs, extension terminals, URIs, file decorations

    # ------------------------------------------------------------ logging / UI helpers
    def log(self, text: str):
        self.output.append(self.HOST_CHANNEL, text.rstrip("\n") + "\n")

    def show_output(self, name: str | None = None):
        if name:
            self.output.select(name)
        if self.dock is not None:
            self.dock.show()
            self.dock.raise_()

    def status(self, text: str, ms: int = 5000):
        try:
            self.win.statusBar().showMessage(text, ms)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------ lifecycle
    def code_extensions(self) -> list:
        try:
            from . import list_enabled
            return [e for e in list_enabled() if e.main and e.path]
        except Exception as e:  # noqa: BLE001
            self.log(f"cannot list extensions: {e}")
            return []

    def folders(self) -> list[str]:
        """The workspace folders VS Code would have: the folder of an explicit solution (.radsln, a foreign .sln /
        .vbg ...) first, then every project folder outside it; a bare project / Open Folder workspace / web site
        is its own folder. The active project's folder leads when there is no solution folder."""
        win = self.win
        projects = []
        try:
            projects = [st["project"] for st in win.project_states()]
        except Exception:  # noqa: BLE001
            pass
        proj = getattr(win, "project", None)
        if proj is not None and proj not in projects:
            projects.insert(0, proj)
        elif proj is not None:
            projects.remove(proj)
            projects.insert(0, proj)
        out: list[str] = []

        def add(p):
            try:
                f = str(Path(p).resolve())
            except (OSError, TypeError, ValueError):
                return
            if f and os.path.isdir(f) and os.path.normcase(f) not in {os.path.normcase(x) for x in out}:
                out.append(f)
        sln = getattr(win, "sln", None)
        sfile = getattr(sln, "file", None) if sln is not None else None
        if sfile and not getattr(sln, "implicit", False):
            add(Path(sfile).parent)
        for p in projects:
            folder = getattr(p, "folder", None)
            if folder is None:
                continue
            try:
                rf = Path(folder).resolve()
            except OSError:
                continue
            if any(Path(o) == rf or Path(o) in rf.parents for o in out):
                continue                        # inside the solution folder: already part of the workspace
            add(rf)
        return out

    def sync_folders(self):
        """Called when the project set may have changed. Like VS Code: going from no folder to a folder (VS Code
        reloads the window) or changing the first folder (rootPath / the cwd extensions captured at activation,
        e.g. Claude Code's session folder) restarts the extension host; other changes fire
        onDidChangeWorkspaceFolders."""
        try:
            new = self.folders()
        except Exception:  # noqa: BLE001
            return
        old = getattr(self, "_last_folders", None)
        self._last_folders = new
        if old is None or old == new:
            return
        if not self.host.running():
            return                              # start() sends the folders
        first_changed = (old[:1] != new[:1])
        if first_changed and new:
            self.log(f"workspace folder is now {new[0]}: restarting the extension host (VS Code reloads the window)")
            QTimer.singleShot(0, self.restart)
            return
        self.host.notify("workspace/folders", {"folders": new})

    def root_for(self, editor) -> Path:
        f = self.folders()
        if f:
            return Path(f[0])
        try:
            return Path(editor.path).resolve().parent
        except (OSError, AttributeError):
            return Path.cwd()

    def settings(self) -> dict:
        out = {}
        try:
            tab = int(self.win.settings.value("options/tab_width", 4) or 4)
            out.update({"editor.tabSize": tab, "editor.insertSpaces": True})
        except Exception:  # noqa: BLE001
            pass
        try:
            from . import contrib_configuration
            out.update(contrib_configuration.load())
        except Exception:  # noqa: BLE001
            pass
        try:                                     # workspace settings (.vscode/settings.json) win over user settings
            from .user_keybindings import strip_jsonc
            f = self.folders()
            ws = Path(f[0]) / ".vscode" / "settings.json" if f else None
            if ws is not None and ws.is_file():
                data = json.loads(strip_jsonc(ws.read_text("utf-8")))
                if isinstance(data, dict):
                    out.update(data)
        except Exception:  # noqa: BLE001
            pass
        return out

    def _storage_root(self) -> str:
        try:
            from .package import vsx_root
            p = vsx_root() / ".storage"
        except Exception:  # noqa: BLE001
            p = Path(tempfile.gettempdir()) / "radide-vsx-storage"
        p.mkdir(parents=True, exist_ok=True)
        return str(p)

    def start(self) -> bool:
        self.extensions = self.code_extensions()
        self._register_palette()
        if not self.extensions:
            return False
        node = find_node()
        if not node:
            self.log("Node.js was not found: extension code cannot run (install Node.js 18+). "
                     "Language servers of extensions run through the IDE's LSP client instead.")
            for e in self.extensions:
                self._lsp_fallback(e)
            return False
        try:
            from .. import i18n
            lang = i18n.language() or "en"
        except Exception:  # noqa: BLE001
            lang = "en"
        try:
            from .. import theme as TH
            kind = 2 if TH.is_dark() else 1
        except Exception:  # noqa: BLE001
            kind = 2
        try:
            from . import API_LEVEL
        except Exception:  # noqa: BLE001
            API_LEVEL = "1.147.0"
        try:
            from ..monaco_editor import MONACO_LANG
            languages = sorted(set(MONACO_LANG.values()))
        except Exception:  # noqa: BLE001
            languages = []
        params = {"extensions": [{"id": e.id, "path": str(e.path), "packageJSON": e.package_json} for e in self.extensions],
                  "workspaceFolders": self.folders(), "settings": self.settings(), "storageRoot": self._storage_root(),
                  "appRoot": self._app_root(), "language": lang, "apiVersion": API_LEVEL,
                  "themeKind": kind, "languages": languages, "portable": _portable(),
                  "webviewBase": self.webviews.server.base, "webviewOrigin": self.webviews.server.origin}
        self._synced.clear()
        self._active_sent = None                 # a new host knows nothing: send the active editor again
        self._last_folders = list(params["workspaceFolders"])
        ok = self.host.start(params, node, env=self._agent_env())
        if not ok:
            self.log("the extension host could not be started")
            return False
        self.log(f"extension host starting ({len(self.extensions)} extension(s) with code, node {node})")
        try:
            self._setup_views()
        except Exception as e:  # noqa: BLE001
            self.log(f"views: {e}")
        for ed in list(self._editors):          # documents already open
            self._open_doc(ed)
        return True

    def _app_root(self) -> str:
        """vscode.env.appRoot. VS Code ships ripgrep at <appRoot>/node_modules/@vscode/ripgrep/bin/rg[.exe] and
        extensions look for it there (Todo Tree, search extensions): when ripgrep is installed (PATH or a VS Code
        installation) a small app root in the extensions folder carries a copy; otherwise RAD IDE's folder."""
        default = str(Path(__file__).resolve().parents[1])
        try:
            import shutil as _sh
            import sys as _sys
            exe = "rg.exe" if _sys.platform == "win32" else "rg"
            src = _sh.which("rg")
            if not src and _sys.platform == "win32":
                for base in (os.environ.get("LOCALAPPDATA", ""), os.environ.get("ProgramFiles", "")):
                    for vs in ("Programs/Microsoft VS Code", "Microsoft VS Code"):
                        c = Path(base) / vs / "resources/app/node_modules/@vscode/ripgrep/bin" / exe
                        if base and c.is_file():
                            src = str(c)
                            break
            if not src:
                return default
            src = str(Path(src).resolve())              # (WinGet's rg is a symbolic link)
            from .package import vsx_root
            root = vsx_root() / ".app"
            dst = root / "node_modules" / "@vscode" / "ripgrep" / "bin" / exe
            if not dst.is_file() or dst.stat().st_size != Path(src).stat().st_size:
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    os.link(src, dst)
                except OSError:
                    _sh.copy2(src, dst)
            (root / "product.json").write_text('{"nameShort": "RAD IDE", "nameLong": "RAD IDE", "applicationName": "radide"}',
                                               "utf-8")
            return str(root)
        except Exception as e:  # noqa: BLE001
            self.log(f"appRoot: {e}")
            return default

    def _agent_env(self) -> dict:
        """Environment of the extension host - and so of the CLIs extensions start (Claude Code ...): how to
        build / run RAD IDE projects headless (radide/agent_cli.py) and where the workspace is."""
        env = {}
        try:
            from ..agent_cli import cli_hint
            env["RADIDE_CLI"] = cli_hint()
        except Exception:  # noqa: BLE001
            pass
        f = self.folders()
        if f:
            env["RADIDE_WORKSPACE"] = f[0]
        return env

    def stop(self):
        self.host.stop()
        for btn in self.status_items.values():
            try:
                self.win.statusBar().removeWidget(btn)
                btn.deleteLater()
            except Exception:  # noqa: BLE001
                pass
        self.status_items.clear()
        self.index.update([])
        self.host_commands.clear()
        for ed in list(self._editors):
            self._wrap(ed)
        for k in list(self.diags):
            self.diags[k] = {}
            self._render_diags(k)

    def restart(self):
        self.stop()
        self.start()

    def start_if_idle(self) -> bool:
        """Start the host unless it already runs (the delayed start-up start, and after an install)."""
        if self.host.running():
            return False
        return self.start()

    def extension_added(self, ext, on: bool = True) -> None:
        """An extension with code was installed / enabled while the IDE runs. VS Code activates it at once: with no
        extension host running yet (the first code extension of this session) start one now instead of waiting for
        the next IDE start; a running host keeps the "Reload" banner (restarting it would end the other extensions'
        sessions)."""
        if not on or not getattr(ext, "main", None) or self.host.running() or os.environ.get("RADIDE_NO_VSX"):
            return
        t = getattr(self, "_added_timer", None)
        if t is None:
            t = self._added_timer = QTimer(self)
            t.setSingleShot(True)
            t.setInterval(250)                   # one start for an extension and its dependencies / pack
            t.timeout.connect(self._start_after_install)
        t.start()

    def _start_after_install(self) -> None:
        if self.host.running() or not self.start():
            return
        self.log("extension host started for the newly installed extension(s): "
                 + ", ".join(e.id for e in self.extensions))
        try:
            from .. import vsx
            vsx.clear_restart([e.id for e in self.extensions])
        except Exception:  # noqa: BLE001
            pass

    def _on_started(self, res):
        if not res:
            self.log("extension host: initialize failed")
            return
        self.log(f"extension host running (pid {res.get('pid')}, node {res.get('node')})")
        if getattr(self, "_ide_diag_files", None):
            self.host.notify("diagnostics/ide", {"files": self._ide_diag_files})

    def push_ide_diagnostics(self, diags) -> None:
        """The Error List's diagnostics (tools.run_checks) -> vscode.languages.getDiagnostics in the host."""
        files: dict = {}
        proj = getattr(self.win, "project", None)
        base = Path(proj.folder) if proj is not None else None
        for d in diags or []:
            f = str(getattr(d, "file", "") or "")
            if not f:
                continue
            p = Path(f)
            if not p.is_absolute() and base is not None:
                p = base / p
            try:
                key = str(p.resolve())
            except OSError:
                key = str(p)
            files.setdefault(key, []).append({"line": int(getattr(d, "line", 1) or 1), "severity": str(d.severity),
                                              "message": str(d.message), "source": "RAD IDE"})
        old = getattr(self, "_ide_diag_files", {}) or {}
        for k in old:                         # files whose problems are gone: an empty list clears them
            files.setdefault(k, [])
        self._ide_diag_files = {k: v for k, v in files.items() if v}
        if self.host.running():
            self.host.notify("diagnostics/ide", {"files": files})

    def _on_stopped(self, code):
        try:
            self.webviews.reset()
            self.views.reset()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.workbench.reset()
        except Exception:  # noqa: BLE001
            pass
        if not self.host._stopping:
            self.log(f"extension host exited ({code})")

    # ------------------------------------------------------------ editors
    def editor_ready(self, ed):
        if ed in self._editors:
            self._open_doc(ed)
            return
        self._editors.add(ed)
        path = str(ed.path)
        timer = QTimer(ed)
        timer.setSingleShot(True)
        timer.setInterval(150)
        timer.timeout.connect(lambda e=ed: self.sync_text(e.path, e.text()))
        ed.textEdited.connect(timer.start)
        ed.modificationChanged.connect(lambda m, e=ed: (not m) and self._saved(e))
        ed.destroyed.connect(lambda _o=None, p=path: self._closed(p))
        ed.languageChanged.connect(lambda _l, e=ed: QTimer.singleShot(0, lambda: self._language_changed(e)))
        ed.contextMenuAboutToShow.connect(lambda m, e=ed: self._context_menu(e, m))
        if not getattr(ed, "_rad_def_hook", False):
            ed._rad_def_hook = True
            ed.definitionRequested.connect(lambda line, col, e=ed: self._definition(e, line, col))
        self._open_doc(ed)
        try:                                     # what the editor loaded: later changes on disk are external
            st = Path(ed.path).resolve().stat()
            self.__dict__.setdefault("_disk_stamps", {})[os.path.normcase(str(Path(ed.path).resolve()))] = \
                (st.st_mtime_ns, st.st_size)
        except (OSError, TypeError):
            pass
        self._apply_lang_config(ed)
        self._render_diags(_key(ed.path))
        self._wrap(ed)
        try:
            self.workbench.hook_editor(ed)
        except Exception:  # noqa: BLE001
            pass

    def _alive(self, ed) -> bool:
        try:
            ed.text()
            return True
        except RuntimeError:
            return False

    def live_editors(self) -> list:
        return [e for e in list(self._editors) if self._alive(e)]

    def editor_for(self, path):
        k = _key(path)
        for e in self.live_editors():
            if _key(e.path) == k:
                return e
        try:
            from ..editkit import find_editor
            return find_editor(self.win, path)
        except Exception:  # noqa: BLE001
            return None

    def _open_doc(self, ed):
        if not self.host.running():
            return
        k = _key(ed.path)
        text = ed.text()
        self._versions[k] = self._versions.get(k, 0) + 1
        self._synced[k] = text
        self.host.notify("document/open", {"path": str(Path(ed.path).resolve()), "languageId": editor_lang(ed),
                                           "version": self._versions[k], "text": text,
                                           "dirty": bool(ed.isModified())})

    def sync_text(self, path, text):
        if not self.host.running():
            return
        k = _key(path)
        if self._synced.get(k) == text:
            return
        if k not in self._synced:
            ed = self.editor_for(path)
            if ed is not None:
                self._open_doc(ed)
                return
        self._synced[k] = text
        self._versions[k] = self._versions.get(k, 0) + 1
        self.host.notify("document/change", {"path": str(Path(path).resolve()), "version": self._versions[k],
                                             "text": text, "dirty": True})

    def _saved(self, ed):
        if self.host.running():
            self.sync_text(ed.path, ed.text())
            self.host.notify("document/save", {"path": str(Path(ed.path).resolve())})

    def _closed(self, path):
        k = _key(path)
        self._synced.pop(k, None)
        if self.host.running():
            self.host.notify("document/close", {"path": str(Path(path).resolve())})

    def _language_changed(self, ed):
        if not self._alive(ed):
            return
        if self.host.running():
            self.host.notify("document/close", {"path": str(Path(ed.path).resolve())})
            self._synced.pop(_key(ed.path), None)
            self._open_doc(ed)
        self._apply_lang_config(ed)
        self._wrap(ed)

    def active_editor(self):
        w = QApplication.focusWidget()
        while w is not None:
            if w in self._editors:
                if w.isVisible():                   # (a hidden tab keeps the focus widget sometimes)
                    return w
                break
            w = w.parentWidget()
        tabs = getattr(self.win, "tabs", None)
        cur = tabs.currentWidget() if tabs is not None else None
        ed = getattr(cur, "editor", None)
        if ed is not None and ed in self._editors:
            return ed
        return None

    def before_request(self):
        """Tell the host which editor is active (and its selection) before a command / feature request."""
        ed = self.active_editor()
        if ed is None or not self.host.running():
            return
        self.sync_text(ed.path, ed.text())
        sel = list(getattr(ed, "_selection", (0, 0, 0, 0)) or (0, 0, 0, 0))
        if sel[0] == sel[2] and sel[1] == sel[3]:
            cur = getattr(ed, "_cursor", (0, 0))
            sel = [cur[0], cur[1], cur[0], cur[1]]
        state = (_key(ed.path), tuple(sel))
        if state != self._active_sent:
            self._active_sent = state
            self.host.notify("editor/active", {"path": str(Path(ed.path).resolve()), "selection": sel})

    def check_disk_changes(self) -> list:
        """Files changed on disk by another program (an AI agent's Write tool, git, a formatter): an open editor
        without unsaved changes shows the new text (VS Code reloads such editors silently); one with unsaved
        changes keeps them and says so. Code files of open forms are left to features/file_integrity.py (it asks
        "Reload?" like Visual Studio). Returns the paths reloaded."""
        stamps = self.__dict__.setdefault("_disk_stamps", {})
        try:                                     # keybindings.json edited (in an editor or outside): re-bind
            from . import user_keybindings
            kp = user_keybindings.path()
            ks = kp.stat().st_mtime_ns if kp.exists() else 0
            if stamps.get("<keybindings>", ks) != ks:
                from . import contrib_runtime
                contrib_runtime.refresh()
            stamps["<keybindings>"] = ks
        except Exception:  # noqa: BLE001
            pass
        covered = set()
        fi = getattr(self.win, "file_integrity", None)
        if fi is not None:
            try:
                for name in set(self.win.docs) | set(self.win.codeviews):
                    for _k, p in fi.files_of(name):
                        covered.add(os.path.normcase(str(Path(p).resolve())))
            except Exception:  # noqa: BLE001
                pass
        out = []
        for ed in self.live_editors():
            try:
                path = Path(ed.path).resolve()
                key = os.path.normcase(str(path))
                st = path.stat()
                stamp = (st.st_mtime_ns, st.st_size)
            except (OSError, AttributeError, TypeError):
                continue
            old = stamps.get(key)
            stamps[key] = stamp
            if old is None or old == stamp or key in covered:
                continue
            try:
                text = path.read_text("utf-8").replace("\r\n", "\n")
            except (OSError, UnicodeError):
                continue
            if text == ed.text():
                continue
            if ed.isModified():
                self.status(f"{path.name} changed on disk - your unsaved changes are kept", 6000)
                continue
            cur = tuple(getattr(ed, "_cursor", (0, 0)))
            bps = set(getattr(ed, "_breakpoints", set()) or set())
            ed.setText(text)
            try:
                if bps and hasattr(ed, "_push_breakpoints"):
                    ed._breakpoints.update(b for b in bps if b < text.count("\n") + 1)
                    ed._push_breakpoints()
                ed.setCursorPosition(min(cur[0], text.count("\n")), cur[1])
            except Exception:  # noqa: BLE001
                pass
            ed.setModified(False)
            if self.host.running():
                self.sync_text(ed.path, text)
            out.append(str(path))
        return out

    def on_editor_selection(self, ed):
        """Monaco cursor / selection moved: tell the host (debounced) - onDidChangeTextEditorSelection."""
        if ed not in self._editors or not self.host.running():
            return
        self._sel_pending = ed
        t = getattr(self, "_sel_timer", None)
        if t is None:
            t = self._sel_timer = QTimer(self)
            t.setSingleShot(True)
            t.setInterval(120)
            t.timeout.connect(self._flush_selection)
        t.start()

    def _flush_selection(self):
        ed = getattr(self, "_sel_pending", None)
        self._sel_pending = None
        if ed is None or not self._alive(ed) or ed is not self.active_editor() or not self.host.running():
            return
        self.before_request()                    # the host knows the document and that it is the active editor
        sel = list(getattr(ed, "_selection", (0, 0, 0, 0)) or (0, 0, 0, 0))
        if sel[0] == sel[2] and sel[1] == sel[3]:
            cur = getattr(ed, "_cursor", (0, 0))
            sel = [cur[0], cur[1], cur[0], cur[1]]
        key = (_key(ed.path), tuple(sel))
        if key == getattr(self, "_sel_sent", None):
            return
        self._sel_sent = key
        self.host.notify("editor/selection", {"path": str(Path(ed.path).resolve()), "selection": sel})

    def _wrap(self, ed):
        """Put a CompositeClient in editor.lsp when extension providers serve this editor (or take it away)."""
        if not self._alive(ed):
            return
        lang = ed.language_id()
        cur = getattr(ed, "_lsp", None)
        want = self.host.running() and bool(self.index.kinds(editor_lang(ed), str(ed.path)))
        if want and not isinstance(cur, CompositeClient):
            ed._lsp = CompositeClient(self, ed, real=cur)      # keep Monaco's own services (no radSetLspActive)
        elif not want and isinstance(cur, CompositeClient):
            ed._lsp = cur.real
        comp = ed._lsp if isinstance(ed._lsp, CompositeClient) else None
        if comp is not None:
            trig = ((comp.capabilities.get("completionProvider") or {}).get("triggerCharacters")) or []
            if trig:
                ed._js(f"radSetTriggers({json.dumps(lang)}, {json.dumps(list(trig))});")

    def _definition(self, ed, line, col):
        client = getattr(ed, "lsp", None)

        def fallback():
            try:
                from ..tools import goto_definition
                goto_definition(self.win)
            except Exception:  # noqa: BLE001
                pass
        if client is None:
            fallback()
            return

        def done(res):
            if not res:
                fallback()
                return
            path, target = res
            self.open_path(path, [target, 0, target, 0])
        client.definition(ed.path, line, col, done)

    # ------------------------------------------------------------ opening files
    def open_path(self, path, selection=None):
        win = self.win
        p = Path(path)
        line = selection[0] + 1 if selection else None
        ed = None
        try:
            if callable(getattr(win, "open_file", None)) and getattr(win, "project", None) is not None:
                r = win.open_file(p, line)
                ed = r if hasattr(r, "goto_line") else None
            elif callable(getattr(win, "open_any_file", None)):
                r = win.open_any_file(p)
                ed = r if hasattr(r, "goto_line") else None
        except Exception as e:  # noqa: BLE001
            self.log(f"cannot open {p}: {e}")
        ed = ed or self.editor_for(p)
        if ed is not None and selection:
            try:
                ed.goto_line(selection[0])
                ed.setSelection(selection[0], selection[1], selection[2], selection[3])
            except Exception:  # noqa: BLE001
                pass
        return ed

    # ------------------------------------------------------------ language configuration / decorations
    def _apply_lang_config(self, ed):
        cfg = self.lang_configs.get(editor_lang(ed))
        if cfg is None:
            return
        ed._js("(function(c,l){function rv(v){if(Array.isArray(v))return v.map(rv);if(v&&typeof v==='object'){"
               "if(v.$regex!==undefined)return new RegExp(v.$regex,v.flags||'');const o={};for(const k in v)o[k]=rv(v[k]);"
               "return o;}return v;}try{monaco.languages.setLanguageConfiguration(l,rv(c));}catch(e){console.error("
               "'vsx language configuration: '+e);}})(" + json.dumps(cfg) + "," + json.dumps(ed.language_id()) + ");")

    def _decorate(self, ed, key: str, ranges: list):
        opts = self.deco_types.get(key, {})
        css = []
        style = []
        for k, v in opts.items():
            if isinstance(v, (str, int, float)) and k not in ("isWholeLine", "overviewRulerColor"):
                prop = re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), k)
                style.append(f"{prop}: {v}")
        css.append(f".{key} {{ {'; '.join(style)} }}")
        after = opts.get("after") or {}
        if after.get("contentText"):
            css.append(f".{key}-after::after {{ content: {json.dumps(after['contentText'])}; "
                       f"color: {after.get('color') or 'gray'}; margin-left: 1em; }}")
        whole = bool(opts.get("isWholeLine"))
        decos = []
        for r in ranges:
            l1, c1, l2, c2 = r["range"]
            o = {"range": [l1 + 1, c1 + 1, l2 + 1, c2 + 1], "options": {("className" if whole else "inlineClassName"): key}}
            if r.get("hover"):
                o["options"]["hoverMessage"] = {"value": r["hover"]}
            if r.get("after") or after.get("contentText"):
                o["options"]["afterContentClassName"] = key + "-after"
            if whole:
                o["options"]["isWholeLine"] = True
            decos.append(o)
        ed._js("(function(css,key,d){let s=document.getElementById('vsx-'+key);if(!s){s=document.createElement('style');"
               "s.id='vsx-'+key;document.head.appendChild(s);}s.textContent=css;window.vsxDeco=window.vsxDeco||{};"
               "const list=d.map(x=>({range:new monaco.Range(x.range[0],x.range[1],x.range[2],x.range[3]),options:x.options}));"
               "window.vsxDeco[key]=radEditor.deltaDecorations(window.vsxDeco[key]||[],list);})("
               + json.dumps("\n".join(css)) + "," + json.dumps(key) + "," + json.dumps(decos) + ");")

    # ------------------------------------------------------------ diagnostics
    def _render_diags(self, k: str):
        ed = None
        for e in self.live_editors():
            if _key(e.path) == k:
                ed = e
                break
        if ed is None:
            return
        items = [d for lst in self.diags.get(k, {}).values() for d in lst]
        sev = {"error": 8, "warning": 4, "info": 2, "hint": 1}
        markers = [{"startLineNumber": d["line"] + 1, "startColumn": d["col"] + 1, "endLineNumber": d["endLine"] + 1,
                    "endColumn": d["endCol"] + 1, "message": d["message"], "severity": sev.get(d["severity"], 2),
                    "source": d.get("source") or "", "code": str(d.get("code") or "")} for d in items]
        ed._js(f"monaco.editor.setModelMarkers(radEditor.getModel(), 'vsx', {json.dumps(markers)});")

    def diagnostics_for(self, path) -> list:
        return [d for lst in self.diags.get(_key(path), {}).values() for d in lst]

    # ------------------------------------------------------------ commands
    def context_for(self, ed=None) -> dict:
        """Context keys for when clauses (radide/vsx/context_keys.py) - setContext values win."""
        from . import context_keys
        return context_keys.compute(self, ed)

    def _contributed_commands(self) -> dict:
        out = {}
        try:
            from . import list_enabled
            exts = list_enabled()
        except Exception:  # noqa: BLE001
            exts = []
        for ext in exts:
            if not ext.main:
                continue
            palette_when = {m.get("command"): m.get("when") for m in (ext.contributes.get("menus") or {}).get(
                "commandPalette", []) if isinstance(m, dict)}
            for c in ext.contributes_list("commands"):
                if isinstance(c, dict) and isinstance(c.get("command"), str):
                    title = c.get("title")
                    title = title.get("value") if isinstance(title, dict) else str(title or c["command"])
                    cat = c.get("category")
                    cat = cat.get("value") if isinstance(cat, dict) else str(cat or "")
                    out[c["command"]] = {"title": title, "category": cat or ext.label, "ext": ext.id,
                                         "when": palette_when.get(c["command"]), "enablement": c.get("enablement")}
        return out

    def _register_palette(self):
        try:
            from ..features import command_palette as cp
        except Exception:  # noqa: BLE001
            return
        for cid in self._palette_ids:
            cp.unregister_command(cid)
        self._palette_ids = []
        for cid, info in self._contributed_commands().items():
            def visible(info=info):
                # VS Code's Command Palette lists a command only while its commandPalette `when` and its
                # `enablement` (precondition) hold (commandsQuickAccess: menu actions that are enabled)
                ctx = self.context_for()
                return W.evaluate(info["when"], ctx) and W.evaluate(info["enablement"], ctx)
            cp.register_command(cid, info["title"], lambda cid=cid: self.execute(cid), info["category"],
                                visible=visible)
            self._palette_ids.append(cid)

    def execute(self, command: str, args=None, cb=None):
        """Run an extension command (starting the host when needed)."""
        if not self.host.running():
            if not self.start():
                self.status(f"The command '{command}' needs the extension host (Node.js)")
                return
        self.before_request()

        def done(res):
            if cb is not None:
                cb(res)
        self.host.request("commands/execute", {"command": command, "args": args or []}, done)

    def handles_command(self, command: str, args=None) -> bool:
        """contrib_keybindings.COMMAND_HANDLERS: keybindings of extension commands."""
        if command in self.host_commands or command in self._contributed_commands():
            self.execute(command, args if isinstance(args, list) else ([args] if args is not None else []))
            return True
        return False

    def _context_menu(self, ed, menu):
        """editor/context of extensions (groups, submenus, enablement); a command gets the resource URI."""
        from . import menus as M
        ctx = self.context_for(ed)
        uri = self.workbench.virtual_uri(str(ed.path)) or Path(ed.path).resolve().as_uri()
        tmp = QMenu()
        n = M.fill_menu(self, tmp, "editor/context", ctx, lambda cid: self.execute(cid, [{"$uri": uri}]))
        if not n:
            tmp.deleteLater()
            return
        menu.addSeparator()
        for a in list(tmp.actions()):
            a.setParent(menu)
            menu.addAction(a)
        menu._vsx_tmp = tmp

    # ------------------------------------------------------------ host -> IDE requests
    def _register_handlers(self):
        H = self.host.handlers
        win = self.win

        def later(fn):
            def h(params, reply):
                QTimer.singleShot(0, lambda: reply(fn(params)))
            return h

        def now(fn):
            return lambda params, reply: reply(fn(params))

        def message(p):
            sev = p.get("severity", "info")
            text = str(p.get("message") or "")
            items = list(p.get("items") or [])
            if not items and not p.get("modal"):
                self.status(text, 8000)
                self.output.append("Notifications", f"[{sev}] {text}\n")
                return None
            box = QMessageBox(win)
            box.setWindowTitle("RAD IDE")
            box.setIcon({"error": QMessageBox.Icon.Critical, "warning": QMessageBox.Icon.Warning}.get(
                sev, QMessageBox.Icon.Information))
            box.setText(text)
            if p.get("detail"):
                box.setInformativeText(str(p["detail"]))
            buttons = [box.addButton(str(t), QMessageBox.ButtonRole.AcceptRole) for t in items]
            if not items:
                box.addButton(QMessageBox.StandardButton.Ok)
            else:
                box.addButton(QMessageBox.StandardButton.Cancel if p.get("modal") else QMessageBox.StandardButton.Close)
            box.exec()
            clicked = box.clickedButton()
            return buttons.index(clicked) if clicked in buttons else None
        H["window/showMessage"] = lambda p, reply: (reply(None), message(p)) if not p.get("items") and not p.get("modal") \
            else QTimer.singleShot(0, lambda: reply(message(p)))

        def quick_pick(p):
            dlg = QuickPickDialog(win, p.get("items") or [], p.get("title") or "", p.get("placeHolder") or "",
                                  bool(p.get("canPickMany")), p.get("value") or "")
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return None
            return dlg.result_value()
        H["window/showQuickPick"] = later(quick_pick)

        def input_box(p):
            dlg = InputDialog(win, p.get("title") or "", p.get("prompt") or "", p.get("value") or "",
                              p.get("placeHolder") or "", bool(p.get("password")), p.get("validationMessage") or "")
            return dlg.edit.text() if dlg.exec() == QDialog.DialogCode.Accepted else None
        H["window/showInputBox"] = later(input_box)

        def open_dialog(p):
            start = p.get("defaultUri") or (self.folders()[0] if self.folders() else "")
            title = p.get("title") or p.get("openLabel") or "Open"
            if p.get("canSelectFolders") and not p.get("canSelectFiles", True):
                d = QFileDialog.getExistingDirectory(win, title, start)
                return [d] if d else None
            flt = ";;".join(f"{k} ({' '.join('*.' + x for x in v)})" for k, v in (p.get("filters") or {}).items()) or "All files (*)"
            if p.get("canSelectMany"):
                files, _ = QFileDialog.getOpenFileNames(win, title, start, flt)
                return files or None
            f, _ = QFileDialog.getOpenFileName(win, title, start, flt)
            return [f] if f else None
        H["window/showOpenDialog"] = later(open_dialog)

        def save_dialog(p):
            flt = ";;".join(f"{k} ({' '.join('*.' + x for x in v)})" for k, v in (p.get("filters") or {}).items()) or "All files (*)"
            f, _ = QFileDialog.getSaveFileName(win, p.get("title") or "Save", p.get("defaultUri") or "", flt)
            return f or None
        H["window/showSaveDialog"] = later(save_dialog)

        def show_doc(p):
            path = p.get("path")
            if not path and p.get("tempPath"):                      # virtual document: an editable temp copy
                tmp = Path(p["tempPath"])                            # (edits / Ctrl+S go back to the extension)
                tmp.parent.mkdir(parents=True, exist_ok=True)
                if p.get("uri"):                                     # resourceScheme / editor/title use the real URI
                    self.workbench._virtual = getattr(self.workbench, "_virtual", {})
                    self.workbench._virtual[str(tmp.resolve()).lower()] = p["uri"]
                ed = self.editor_for(tmp)
                if ed is None or not tmp.exists():
                    tmp.write_text(p.get("content") or "", "utf-8")
                elif ed.text() != (p.get("content") or ""):
                    ed.setText(p.get("content") or "")
                ed = self.open_path(str(tmp), p.get("selection"))
                if ed is not None and p.get("readOnly") and hasattr(ed, "setReadOnly"):
                    ed.setReadOnly(True)
                return True
            if not path and p.get("content") is not None:          # virtual document: a read-only temp copy
                name = re.sub(r"[^\w.\-]+", "_", (p.get("uri") or "document").split("/")[-1]) or "document"
                tmp = Path(self._storage_root()) / "virtual" / name
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(p["content"], "utf-8")
                path = str(tmp)
            if path:
                self.open_path(path, p.get("selection"))
            return True
        H["window/showTextDocument"] = later(show_doc)

        def apply_edit(p):
            from .. import editkit
            changes = {}
            for item in p.get("edits") or []:
                changes.setdefault(item["path"], []).extend(
                    [e["range"][0], e["range"][1], e["range"][2], e["range"][3], e["text"]] for e in item.get("edits") or [])
            for f in p.get("files") or []:
                try:
                    op = f.get("op")
                    if op == "create":
                        t = Path(f["to"])
                        if not t.exists() or (f.get("options") or {}).get("overwrite"):
                            t.parent.mkdir(parents=True, exist_ok=True)
                            t.write_text(f.get("contents") or "", "utf-8")
                    elif op == "delete":
                        t = Path(f["from"])
                        if t.is_file():
                            t.unlink()
                    elif op == "rename":
                        a, b = Path(f["from"]), Path(f["to"])
                        if a.exists() and (not b.exists() or (f.get("options") or {}).get("overwrite")):
                            os.replace(a, b)
                except OSError as e:
                    self.log(f"workspace edit: {e}")
            if changes:
                editkit.apply_workspace_edit(win, changes=changes)
            return True
        H["workspace/applyEdit"] = now(apply_edit)

        def save(p):
            ed = self.editor_for(p.get("path") or "")
            if ed is None:
                return True
            tabs = getattr(win, "tabs", None)
            if tabs is not None:
                for i in range(tabs.count()):
                    w = tabs.widget(i)
                    if getattr(w, "editor", None) is ed:
                        tabs.setCurrentWidget(w)
                        return bool(win.save_current())
            try:
                Path(ed.path).write_text(ed.text(), "utf-8")
                ed.setModified(False)
                return True
            except OSError:
                return False
        H["workspace/save"] = later(save)
        H["workspace/saveAll"] = later(lambda p: bool(win.save_all()) if callable(getattr(win, "save_all", None)) else False)

        def set_language(p):
            ed = self.editor_for(p.get("path") or "")
            if ed is not None and hasattr(ed, "set_language"):
                ed.set_language(p.get("language"))
            return True
        H["workspace/setLanguage"] = later(set_language)

        def config_update(p):
            from . import contrib_configuration
            contrib_configuration.set_values({p["key"]: None if p.get("remove") else p.get("value")})
            return True
        H["configuration/update"] = now(config_update)

        def exec_ide(p):
            cmd = p.get("command") or ""
            args = p.get("args") or []
            if cmd == "workbench.action.reloadWindow":
                QTimer.singleShot(100, self.restart)
                return True
            if cmd in ("workbench.action.output.toggleOutput", "workbench.panel.output.focus"):
                self.show_output()
                return True
            try:
                r = self.workbench.exec_command(cmd, args)
                if r is not None:
                    return r
            except Exception as e:  # noqa: BLE001
                self.log(f"command {cmd}: {e}")
            try:
                from . import contrib_keybindings as KB
                if KB.is_monaco_command(cmd):
                    from . import editor_commands as EC
                    ed = self.active_editor()
                    if ed is not None and EC.run(ed, cmd, args, win=win):
                        return True
                    return None
                # unknown here too: the host rejects ids VS Code does not know ("command 'x' not found")
                return True if KB.run_command(win, cmd, args, fallback=False) else {"$notFound": True}
            except Exception as e:  # noqa: BLE001
                self.log(f"command {cmd}: {e}")
                return None

        def exec_ide_async(params, reply):
            def go():
                from .ide_commands import Deferred
                try:
                    r = exec_ide(params)
                except Exception as e:  # noqa: BLE001
                    self.log(f"command {params.get('command')}: {e}")
                    r = None
                if isinstance(r, Deferred):
                    try:
                        r.fn(reply)
                    except Exception as e:  # noqa: BLE001
                        self.log(f"command {params.get('command')}: {e}")
                        reply(None)
                else:
                    reply(r)
            QTimer.singleShot(0, go)
        H["commands/executeIde"] = exec_ide_async
        H["env/clipboardRead"] = now(lambda p: QApplication.clipboard().text())
        H["env/clipboardWrite"] = now(lambda p: QApplication.clipboard().setText(p.get("text") or "") or True)
        H["env/openExternal"] = now(lambda p: QDesktopServices.openUrl(QUrl(p.get("uri") or "")))

        def insert_snippet(p):
            ed = self.editor_for(p.get("path") or "")
            if ed is None:
                return False
            r = p.get("range")
            sel = (f"radEditor.setSelection(new monaco.Range({r[0] + 1},{r[1] + 1},{r[2] + 1},{r[3] + 1}));"
                   if r else "")
            ed._js(f"{sel} radEditor.focus(); radEditor.getContribution('snippetController2').insert("
                   f"{json.dumps(p.get('snippet') or '')});")
            return True
        H["editor/insertSnippet"] = now(insert_snippet)
        H["debug/start"] = later(lambda p: self.debug_start(config=p.get("config"), folder=p.get("folder")))

        def custom_request(p, reply):
            s = getattr(win, "session", None)
            if s is not None and getattr(s, "vsx_session_id", None) == p.get("sessionId") and hasattr(s, "custom_request"):
                s.custom_request(p.get("command"), p.get("args") or {}, reply)
            else:
                reply(None)
        H["debug/customRequest"] = custom_request
        H["debug/stop"] = later(lambda p: win.stop_project() if callable(getattr(win, "stop_project", None)) else None)

    # ------------------------------------------------------------ host notifications
    def _on_notification(self, method: str, p: dict):
        try:
            if method.startswith("webview") and self.webviews.handle(method, p):
                return
            if method.startswith("tree/") and self.views.handle(method, p):
                return
            if self.workbench.handle(method, p):
                return
            fn = getattr(self, "_n_" + method.replace("/", "_"), None)
            if fn is not None:
                fn(p)
        except Exception as e:  # noqa: BLE001 - one bad notification must not stop the others
            self.log(f"[{method}] {e}")

    def _n_output_create(self, p):
        self.output.ensure(p["channel"])

    def _n_output_append(self, p):
        self.output.append(p["channel"], p.get("text") or "")

    def _n_output_replace(self, p):
        self.output.replace(p["channel"], p.get("text") or "")

    def _n_output_clear(self, p):
        self.output.clear(p["channel"])

    def _n_output_show(self, p):
        self.show_output(p["channel"])

    def _n_output_hide(self, p):
        # OutputChannel.hide(): hide the Output view when it shows that channel
        if self.dock is not None and self.output.combo.currentText() == p.get("channel"):
            self.dock.hide()

    def _n_output_dispose(self, p):
        self.output.remove(p.get("channel") or "")

    def _n_statusBar_set(self, p):
        sb = self.win.statusBar()
        btn = self.status_items.get(p["id"])
        if btn is None:
            btn = QToolButton()
            btn.setAutoRaise(True)
            btn.setObjectName("vsxStatusItem")
            (sb.addWidget if p.get("alignment") == 1 else sb.addPermanentWidget)(btn)
            self.status_items[p["id"]] = btn
            btn.clicked.connect(lambda _c=False, b=btn: self._status_clicked(b))
        btn.setText(codicons(p.get("text") or ""))
        btn.setToolTip(p.get("tooltip") or p.get("name") or "")
        btn.setProperty("vsxCommand", p.get("command"))
        color = p.get("color") or ""
        btn.setStyleSheet(f"color: {color};" if color.startswith("#") else "")
        btn.setVisible(bool(p.get("visible")) and bool(btn.text()))

    def _status_clicked(self, btn):
        cmd = btn.property("vsxCommand")
        if isinstance(cmd, dict) and cmd.get("command"):
            self.execute(cmd["command"], cmd.get("arguments") or [])

    def _n_statusBar_remove(self, p):
        btn = self.status_items.pop(p["id"], None)
        if btn is not None:
            self.win.statusBar().removeWidget(btn)
            btn.deleteLater()

    def _n_diagnostics_set(self, p):
        path = p.get("path")
        if not path:
            return
        k = _key(path)
        d = self.diags.setdefault(k, {})
        if p.get("diagnostics"):
            d[p["owner"]] = p["diagnostics"]
        else:
            d.pop(p["owner"], None)
        self._render_diags(k)

    def _n_providers_changed(self, p):
        self.index.update(p.get("providers") or [])
        for ed in self.live_editors():
            self._wrap(ed)

    def _n_commands_registered(self, p):
        self.host_commands.add(p["id"])

    def _n_commands_unregistered(self, p):
        self.host_commands.discard(p["id"])

    def _n_context_set(self, p):
        self.context[str(p.get("key"))] = p.get("value")
        if not getattr(self, "_ctx_timer", None):
            self._ctx_timer = QTimer(self)
            self._ctx_timer.setSingleShot(True)
            self._ctx_timer.setInterval(50)
            self._ctx_timer.timeout.connect(self._context_changed)
        self._ctx_timer.start()

    def _context_changed(self):
        for fn in (self.workbench.context_changed, self.views.context_changed):
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                self.log(f"context: {e}")

    def _n_languages_setConfiguration(self, p):
        self.lang_configs[p["language"]] = p.get("config") or {}
        for ed in self.live_editors():
            if editor_lang(ed) == p["language"]:
                self._apply_lang_config(ed)

    def _n_window_progress(self, p):
        if p.get("op") == "start":
            self._progress = getattr(self, "_progress", {})
            self._progress[p["id"]] = p.get("title") or ""
            self.status(f"⟳ {p.get('title') or ''}", 0)
        elif p.get("op") == "report":
            t = getattr(self, "_progress", {}).get(p["id"], "")
            msg = p.get("message") or ""
            self.status(f"⟳ {t}{': ' if t and msg else ''}{msg}", 0)
        else:
            getattr(self, "_progress", {}).pop(p["id"], None)
            self.win.statusBar().clearMessage()

    def _n_window_setStatusBarMessage(self, p):
        if p.get("text"):
            self.status(codicons(p["text"]), int(p.get("timeout") or 0))
        else:
            self.win.statusBar().clearMessage()

    def _n_editor_setSelection(self, p):
        if not p.get("path"):
            return
        ed = self.editor_for(p.get("path") or "")
        if ed is not None:
            l1, c1, l2, c2 = p["selection"]
            ed.setSelection(l1, c1, l2, c2)

    def _n_editor_reveal(self, p):
        if not p.get("path"):
            return
        ed = self.editor_for(p.get("path") or "")
        if ed is not None:
            ed._js(f"radReveal({int(p.get('line') or 0)});")

    def _n_decorations_type(self, p):
        self.deco_types[p["key"]] = p.get("options") or {}

    def _n_decorations_disposeType(self, p):
        self.deco_types.pop(p["key"], None)
        for ed in self.live_editors():
            ed._js(f"if(window.vsxDeco&&window.vsxDeco[{json.dumps(p['key'])}])"
                   f"radEditor.deltaDecorations(window.vsxDeco[{json.dumps(p['key'])}],[]);")

    def _n_editor_decorations(self, p):
        ed = self.editor_for(p.get("path") or "")
        if ed is not None:
            self._decorate(ed, p["key"], p.get("ranges") or [])

    # ------------------------------------------------------------ tree views (contributes.views)
    def contributed_views(self) -> dict:
        """view id -> title of the views the enabled extensions with code contribute."""
        out = {}
        for ext in self.extensions:
            for _container, views in (ext.contributes.get("views") or {}).items():
                for v in views if isinstance(views, list) else []:
                    if isinstance(v, dict) and v.get("id") and v.get("type", "tree") == "tree":
                        out[v["id"]] = str(v.get("name") or v["id"])
        return out

    def contributed_webview_views(self) -> dict:
        """view id -> title of the webview views (type "webview") the enabled extensions contribute;
        a view whose `when` is false right now is left out when another view of the extension is shown."""
        out = {}
        for ext in self.extensions:
            mine = {}
            for container, views in (ext.contributes.get("views") or {}).items():
                for v in views if isinstance(views, list) else []:
                    if isinstance(v, dict) and v.get("id") and v.get("type") == "webview":
                        ok = True
                        if v.get("when"):
                            try:
                                ok = bool(W.evaluate(v["when"], self.context))
                            except Exception:  # noqa: BLE001
                                ok = True
                        name = str(v.get("name") or "") or self._container_title(ext, container) or v["id"]
                        mine[v["id"]] = (name, ok)
            shown = {k: n for k, (n, ok) in mine.items() if ok} or {k: n for k, (n, _ok) in mine.items()}
            out.update(shown)
        return out

    @staticmethod
    def _container_title(ext, container: str) -> str:
        for lst in (ext.contributes.get("viewsContainers") or {}).values():
            for c in lst if isinstance(lst, list) else []:
                if isinstance(c, dict) and c.get("id") == container:
                    return str(c.get("title") or "")
        return ""

    def _setup_views(self):
        views = self.contributed_views()
        wviews = self.contributed_webview_views()
        if not views and not wviews:
            return
        try:
            from ..i18n import tr
        except Exception:  # noqa: BLE001
            def tr(t):
                return t
        menu = getattr(self, "_views_menu", None)
        if menu is None:
            view = next((a.menu() for a in self.win.menuBar().actions()
                         if a.menu() and a.text().replace("&", "") in ("View", tr("View"))), None)
            if view is None:
                return
            menu = self._views_menu = view.addMenu(tr("Extension Views"))
        menu.clear()
        for vid, title in views.items():
            menu.addAction(title, lambda vid=vid: self.show_view(vid))
        for vid, title in wviews.items():
            menu.addAction(title, lambda vid=vid: self.webviews.show_view(vid))
        try:
            self.views.register_containers()
        except Exception as e:  # noqa: BLE001
            self.log(f"views: {e}")

    def show_view(self, view_id: str):
        """Show a contributed view (tree or webview) in its container's area."""
        if not self.views.show_view(view_id):
            self.views.tree_dock(view_id).show()

    def _view_dock(self, view_id: str) -> QDockWidget:
        return self.views.tree_dock(view_id)

    def _activate_item(self, item):
        self.views.activate(None, item)

    def _n_extension_activated(self, p):
        self.activation[p["id"]] = "active"

    def _n_extension_activationFailed(self, p):
        self.activation[p["id"]] = p.get("error") or "failed"
        self.status(f"Extension {p['id']} failed to activate (see View > Extension Output)", 8000)
        ext = next((e for e in self.extensions if e.id == p["id"]), None)
        if ext is not None:
            self._lsp_fallback(ext)

    def _n_host_ready(self, p):
        n = sum(1 for e in p.get("extensions") or [] if e.get("active"))
        self.status(f"Extension host: {n} extension(s) active", 4000)

    def _n_host_unsupported(self, p):
        self.unsupported.append((p.get("ext", ""), p.get("api", "")))

    # ------------------------------------------------------------ LSP fallback
    def _lsp_fallback(self, ext):
        if ext.id in self._fallback_done:
            return
        mode = "auto"
        try:
            mode = str(self.win.settings.value("vsx/lsp_fallback", "auto") or "auto")
        except Exception:  # noqa: BLE001
            pass
        if mode == "never":
            return
        self._fallback_done.add(ext.id)
        from . import lsp_fallback
        langs = lsp_fallback.register(ext, self.log)
        if not langs:
            return
        mgr = getattr(self.win, "lsp_manager", None)
        if mgr is not None:                      # forget "no server" answers cached for these languages
            from ..lsp import server_key
            keys = {server_key(lang) for lang in langs}
            for k in [k for k, c in mgr.clients.items() if c is None and k[0] in keys]:
                mgr.clients.pop(k, None)
        for ed in self.live_editors():
            if editor_lang(ed) in langs and getattr(ed, "lsp", None) is None and mgr is not None:
                ed.languageChanged.emit(ed.language_id())     # lsp_support attaches the new server

    # ------------------------------------------------------------ debugging
    def debug_types(self) -> list[dict]:
        from . import debuggers
        return debuggers.contributed()

    def _breakpoints(self) -> list:
        """(absolute path, 1-based line[, condition]) of the project breakpoints and of every open editor."""
        bps = []
        proj = getattr(self.win, "project", None)
        base = Path(proj.folder) if proj is not None else None
        try:
            for b in self.win._all_breakpoints():
                f = Path(b[0])
                if not f.is_absolute() and base is not None:
                    f = base / f
                bps.append((str(f.resolve()), b[1], *b[2:3]))
        except Exception:  # noqa: BLE001
            pass
        have = {(b[0].lower(), b[1]) for b in bps}
        for ed in self.live_editors():
            try:
                for line in ed.breakpoints():            # editor lines are 0-based
                    k = (str(Path(ed.path).resolve()).lower(), line + 1)
                    if k not in have:
                        bps.append((str(Path(ed.path).resolve()), line + 1))
                        have.add(k)
            except Exception:  # noqa: BLE001
                continue
        return bps

    def should_debug_with_extension(self, ed) -> bool:
        if ed is None:
            return False
        from . import debuggers
        folder = self.folders()[0] if self.folders() else str(Path(ed.path).resolve().parent)
        types = {d["type"] for d in debuggers.contributed()}
        if any(c.get("type") in types for c in debuggers.launch_configurations(folder)):
            return True
        if not debuggers.for_language(editor_lang(ed)):
            return False
        proj = getattr(self.win, "project", None)
        if proj is None:
            return True
        try:          # a project with its own debugger keeps F5 (Debug > Debug with Extension Debugger stays)
            return not self.win.run_plugin().supports_debug
        except Exception:  # noqa: BLE001
            return False

    def debug_start(self, config=None, folder=None, ed=None, debug_type=None) -> bool:
        from . import debuggers
        win = self.win
        ed = ed or self.active_editor()
        file = str(Path(ed.path).resolve()) if ed is not None else ""
        folder = folder or (self.folders()[0] if self.folders() else (str(Path(file).parent) if file else ""))
        if config is None:
            types = {d["type"] for d in debuggers.contributed()}
            confs = [c for c in debuggers.launch_configurations(folder) if c.get("type") in types]
            if confs:
                config = confs[0]
        if config is None and debug_type is None and ed is not None:
            cands = debuggers.for_language(editor_lang(ed))
            if cands:
                debug_type = cands[0]["type"]
        dtype = (config or {}).get("type") or debug_type
        if not dtype:
            self.status("No extension debugger for this file")
            return False
        if ed is not None:
            self.before_request()
        res = None
        if self.host.running() or self.start():
            sel = getattr(ed, "_selection", (0, 0, 0, 0)) if ed is not None else (0, 0, 0, 0)
            res = self.host.request_sync("debug/resolve", {"type": dtype, "config": config, "folder": folder,
                                                           "file": file, "line": sel[0]}, 120000)
            if not res:
                self.log("debug: the extension host did not answer")
                return False
            if res.get("cancelled"):
                return False
            if res.get("error"):
                self.log(f"debug: {res['error']}")
                QMessageBox.warning(win, "Debug", res["error"])
                return False
            config, adapter, sid = res["config"], res["adapter"], res.get("sessionId", "")
        else:                                              # no host: declarative adapter only
            entry = next((d for d in debuggers.contributed() if d["type"] == dtype and d["contribution"].get("program")), None)
            argv = debuggers.declared_executable(entry) if entry else None
            if not argv:
                self.status(f"The debugger '{dtype}' needs the extension host (Node.js)")
                return False
            if config is None:
                init = entry["contribution"].get("initialConfigurations") or [{"type": dtype, "request": "launch",
                                                                               "name": dtype}]
                config = dict(init[0])
            config = debuggers.substitute(config, folder, file)
            adapter, sid = {"kind": "executable", "command": argv[0], "args": argv[1:]}, ""
        s = debuggers.make_session(dtype, config, adapter, Path(folder or "."), self._breakpoints(), win, sid)
        if s is None:
            self.log(f"debug: cannot start the adapter {adapter}")
            return False
        self._wire_session(s, config)
        return True

    def _wire_session(self, s, config):
        win = self.win
        try:
            if getattr(win, "session", None) is not None and win.session.running():
                win.stop_project()
        except Exception:  # noqa: BLE001
            pass
        try:
            win.output.clear()
            win.dock_output.show()
            win.dock_output.raise_()
            win.log(f"------ Debug ({s.debug_type}): {config.get('name', '')} ------")
            s.output.connect(win._append_output)
            s.stopped.connect(win._on_stopped)
            s.resumed.connect(win._on_resumed)
            from ..tools import on_eval_result
            s.evalResult.connect(lambda txt: on_eval_result(win, txt) or win.immediate.show_result(txt))
            s.finished.connect(lambda code, s=s: win._on_finished(code, s))
            s.failed.connect(lambda err: win.log(f"*** Error: {err}"))
        except AttributeError:
            s.output.connect(lambda t: self.output.append("Debug Console", t))
        sid = s.vsx_session_id
        if sid and self.host.running():
            self.host.notify("debug/sessionStarted", {"sessionId": sid, "config": config})
            s.finished.connect(lambda _c, sid=sid: self.host.running() and self.host.notify(
                "debug/sessionTerminated", {"sessionId": sid}))
        win.session = s
        s.start()
        for fn in ("_set_run_state", "_update_actions"):
            f = getattr(win, fn, None)
            if callable(f):
                try:
                    f("Running...") if fn == "_set_run_state" else f()
                except Exception:  # noqa: BLE001
                    pass

    def _custom_event(self, session, event, body):
        sid = getattr(session, "vsx_session_id", "")
        if sid and self.host.running():
            self.host.notify("debug/customEvent", {"sessionId": sid, "event": event, "body": body})


# ============================================================================ install
def install(win) -> VsxService:
    svc = VsxService(win)
    win.vsx_host = svc
    d = QDockWidget("Extension Output", win)
    d.setObjectName("VsxExtensionOutput")
    d.setWidget(svc.output)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d)
    other = getattr(win, "dock_output", None)
    if other is not None:
        try:
            win.tabifyDockWidget(other, d)
        except Exception:  # noqa: BLE001
            pass
    d.hide()
    svc.dock = d
    try:
        from ..i18n import tr
    except Exception:  # noqa: BLE001
        def tr(s):
            return s
    try:
        from ..features import command_palette as cp
        cp.register_command("vsx.showExtensionOutput", tr("Show Extension Output"), lambda: svc.show_output(), "Extensions")
        cp.register_command("vsx.restartExtensionHost", tr("Restart Extension Host"), svc.restart, "Extensions")
        cp.register_command("vsx.debugWithExtension", tr("Debug with Extension Debugger"),
                            lambda: svc.debug_start(), "Debug")
    except Exception:  # noqa: BLE001
        pass
    try:                                       # View menu
        view = next((a.menu() for a in win.menuBar().actions() if a.menu() and a.text().replace("&", "") in ("View", tr("View"))), None)
        if view is not None:
            view.addAction(tr("Extension Output"), lambda: svc.show_output())
        dbg = next((a.menu() for a in win.menuBar().actions() if a.menu() and a.text().replace("&", "") in ("Debug", tr("Debug"))), None)
        if dbg is not None:
            dbg.addAction(tr("Debug with Extension Debugger"), lambda: svc.debug_start())
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..monaco_editor import MonacoEditor
        MonacoEditor.ready_hooks.append(lambda ed: svc.editor_ready(ed) if ed.window() is win else None)
    except ImportError:
        pass
    try:
        from . import contrib_keybindings
        contrib_keybindings.COMMAND_HANDLERS.append(svc.handles_command)
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import contrib_configuration

        def changed(ch, svc=svc):
            if svc.host.running():
                svc.host.notify("configuration/changed", {"settings": svc.settings(), "keys": list(ch)})
        contrib_configuration.ON_CHANGED.append(changed)
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import debuggers
        debuggers.CUSTOM_EVENT_HOOKS.append(svc._custom_event)
    except Exception:  # noqa: BLE001
        pass
    try:
        from .. import vsx
        vsx.on_reload_requested.connect(lambda: QTimer.singleShot(0, svc.restart))
        vsx.on_installed.connect(svc.extension_added)       # the first code extension: start the host now
        vsx.on_enabled.connect(svc.extension_added)
        vsx.on_changed.connect(lambda: QTimer.singleShot(0, svc._register_palette))
    except Exception:  # noqa: BLE001
        pass

    # F5: an extension debugger for files the project cannot debug itself
    orig_run = getattr(win, "run_project", None)
    if callable(orig_run):
        def run_project(debug: bool = True, _orig=orig_run):
            try:
                s = getattr(win, "session", None)
                if debug and not (s is not None and s.running()):
                    ed = svc.active_editor()
                    if svc.should_debug_with_extension(ed) and svc.debug_start(ed=ed):
                        return None
            except Exception as e:  # noqa: BLE001 - never break F5
                svc.log(f"debug: {e}")
            return _orig(debug)
        win.run_project = run_project

    try:                                        # the Error List's problems reach getDiagnostics (agents check their work)
        from .. import tools as _tools
        _orig_checks = _tools.run_checks

        def run_checks(w, show=False, _orig=_orig_checks):
            res = _orig(w, show)
            if w is win:
                try:
                    svc.push_ide_diagnostics(res)
                except Exception as e:  # noqa: BLE001
                    svc.log(f"diagnostics: {e}")
            return res
        _tools.run_checks = run_checks
    except Exception:  # noqa: BLE001
        pass
    # workspace folders follow the solution (MainWindow has no "opened" signal: open_project / close_solution /
    # foreign projects / Open Folder all end in a changed project set, which a cheap poll notices)
    try:
        from .. import monaco_editor as _me
        _me.SELECTION_LISTENERS.append(svc.on_editor_selection)
    except Exception:  # noqa: BLE001
        pass
    try:                                        # go back / forward, reopen closed editor (navigation.py)
        from . import navigation
        navigation.install(win)
    except Exception as e:  # noqa: BLE001
        svc.log(f"navigation: {e}")
    svc._disk_timer = QTimer(win)                # files changed on disk -> open editors (check_disk_changes)
    svc._disk_timer.setInterval(1200)
    svc._disk_timer.timeout.connect(svc.check_disk_changes)
    svc._disk_timer.start()
    svc._folders_timer = QTimer(win)
    svc._folders_timer.setInterval(700)
    svc._folders_timer.timeout.connect(svc.sync_folders)
    svc._folders_timer.start()
    try:
        from .. import theme as TH
        TH.changed.connect(lambda _n: svc.host.running() and svc.host.notify(
            "theme/changed", {"kind": 2 if TH.is_dark() else 1}))
    except Exception:  # noqa: BLE001
        pass

    orig_close = win.closeEvent

    def close_event(e, _orig=orig_close):
        _orig(e)
        if e.isAccepted():
            svc.stop()
    win.closeEvent = close_event
    if os.environ.get("RADIDE_NO_VSX"):          # headless agent commands (radide/agent_cli.py)
        svc._folders_timer.stop()
        return svc
    try:                                        # AI agents: offer the RAD IDE context file (agent_context.py)
        from . import agent_context
        agent_context.install(win)
    except Exception as e:  # noqa: BLE001
        svc.log(f"agent context: {e}")
    QTimer.singleShot(1500, svc.start_if_idle)  # after the IDE is up (extensions do not slow the start)
    return svc


__all__ = ["VsxService", "install", "codicons", "QuickPickDialog", "InputDialog", "OutputPanel"]
