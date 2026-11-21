"""The extension host inside RAD IDE: editors, UI and language features for VS Code extensions with code.

``install(win)`` (radide/features/vsx_host.py) creates ``win.vsx_host`` (a ``VsxService``) which
  * starts ``node radide/vsx/host/main.js`` (bridge.py) with the enabled extensions that have a "main"
    entry, restarts it on "Reload" (radide.vsx.on_reload_requested) and stops it with the window;
  * mirrors every Monaco editor into the host (document/open|change|save|close, active editor, selection);
  * shows the UI the extensions ask for: messages (with buttons), quick picks, input boxes, open / save
    dialogs, output channels (an "Extension Output" dock), status bar items, progress, terminals
    (the IDE terminal), snippets, decorations;
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
                             QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QPlainTextEdit, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

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
        self.host.notification.connect(self._on_notification)
        self.host.stderr.connect(lambda t: self.output.append(self.HOST_CHANNEL, t))
        self.host.stopped.connect(self._on_stopped)
        self.host.started.connect(self._on_started)
        self._register_handlers()

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
        out = []
        try:
            for st in self.win.project_states():
                f = str(Path(st["project"].folder).resolve())
                if f not in out:
                    out.append(f)
        except Exception:  # noqa: BLE001
            pass
        proj = getattr(self.win, "project", None)
        if proj is not None and not out:
            out.append(str(Path(proj.folder).resolve()))
        return out

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
            API_LEVEL = "1.90.0"
        try:
            from ..monaco_editor import MONACO_LANG
            languages = sorted(set(MONACO_LANG.values()))
        except Exception:  # noqa: BLE001
            languages = []
        params = {"extensions": [{"id": e.id, "path": str(e.path), "packageJSON": e.package_json} for e in self.extensions],
                  "workspaceFolders": self.folders(), "settings": self.settings(), "storageRoot": self._storage_root(),
                  "appRoot": str(Path(__file__).resolve().parents[1]), "language": lang, "apiVersion": API_LEVEL,
                  "themeKind": kind, "languages": languages}
        self._synced.clear()
        self._active_sent = None                 # a new host knows nothing: send the active editor again
        ok = self.host.start(params, node)
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

    def _on_started(self, res):
        if not res:
            self.log("extension host: initialize failed")
            return
        self.log(f"extension host running (pid {res.get('pid')}, node {res.get('node')})")

    def _on_stopped(self, code):
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
        self._apply_lang_config(ed)
        self._render_diags(_key(ed.path))
        self._wrap(ed)

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
                return w
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
        ctx = dict(self.context)
        ed = ed or self.active_editor()
        if ed is not None:
            p = Path(ed.path)
            lang = editor_lang(ed)
            sel = getattr(ed, "_selection", (0, 0, 0, 0)) or (0, 0, 0, 0)
            ctx.update({"editorLangId": lang, "resourceLangId": lang, "resourceExtname": p.suffix.lower(),
                        "resourceFilename": p.name, "resourcePath": str(p), "resourceScheme": "file",
                        "editorTextFocus": True, "editorFocus": True, "textInputFocus": True,
                        "editorHasSelection": not (sel[0] == sel[2] and sel[1] == sel[3]),
                        "editorReadonly": bool(getattr(ed, "_readonly", False)), "editorIsOpen": True,
                        "resourceDirname": str(p.parent), "isFileSystemResource": True})
        s = getattr(self.win, "session", None)
        try:
            ctx["inDebugMode"] = bool(s is not None and s.running())
        except Exception:  # noqa: BLE001
            ctx["inDebugMode"] = False
        ctx.update({"isWindows": os.name == "nt", "isLinux": False, "isMac": False, "isWeb": False,
                    "workspaceFolderCount": len(self.folders()), "workbenchState": "folder" if self.folders() else "empty",
                    "extensionHostKind": "local"})
        return ctx

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
            def enabled(info=info):
                ctx = self.context_for()
                return W.evaluate(info["when"], ctx) and W.evaluate(info["enablement"], ctx)
            cp.register_command(cid, info["title"], lambda cid=cid: self.execute(cid), info["category"], enabled=enabled)
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
        items = []
        cmds = self._contributed_commands()
        try:
            from . import list_enabled
            exts = list_enabled()
        except Exception:  # noqa: BLE001
            exts = []
        ctx = self.context_for(ed)
        for ext in exts:
            for m in (ext.contributes.get("menus") or {}).get("editor/context", []) or []:
                if isinstance(m, dict) and m.get("command") in cmds and W.evaluate(m.get("when"), ctx):
                    items.append(m["command"])
        if not items:
            return
        menu.addSeparator()
        for cid in items:
            menu.addAction(codicons(cmds[cid]["title"]), lambda cid=cid: self.execute(cid))

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
                from . import contrib_keybindings as KB
                if KB.is_monaco_command(cmd):
                    ed = self.active_editor()
                    if ed is not None:
                        ed._js(f"radEditor.focus(); radEditor.trigger('vsx', {json.dumps(cmd)}, "
                               f"{json.dumps(args[0] if args else {})});")
                        return True
                    return None
                return True if KB.run_command(win, cmd, args) else None
            except Exception as e:  # noqa: BLE001
                self.log(f"command {cmd}: {e}")
                return None
        H["commands/executeIde"] = later(exec_ide)
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

    def _n_terminal_create(self, p):
        self.terminals[p["id"]] = dict(p)
        if p.get("pty"):
            self.output.ensure(f"Terminal: {p.get('name')}")

    def _terminal_widget(self):
        t = getattr(self.win, "terminal", None)
        if t is None:
            return None
        try:
            from ..features.terminal import show_terminal
            show_terminal(self.win)
        except Exception:  # noqa: BLE001
            pass
        return t

    def _n_terminal_sendText(self, p):
        info = self.terminals.get(p["id"], {})
        t = self._terminal_widget()
        if t is None:
            self.log(f"terminal: {p.get('text')}")
            return
        if info.get("cwd") and not info.get("_cd"):
            info["_cd"] = True
            t.run_command(f'cd /d "{info["cwd"]}"' if os.name == "nt" else f'cd "{info["cwd"]}"')
        for line in (p.get("text") or "").splitlines() or [""]:
            t.run_command(line)

    def _n_terminal_show(self, p):
        info = self.terminals.get(p["id"], {})
        if info.get("pty"):
            self.show_output(f"Terminal: {info.get('name')}")
        else:
            self._terminal_widget()

    def _n_terminal_write(self, p):
        info = self.terminals.get(p["id"], {})
        self.output.append(f"Terminal: {info.get('name', p['id'])}",
                           re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", (p.get("data") or "").replace("\r\n", "\n")))

    def _n_terminal_dispose(self, p):
        self.terminals.pop(p["id"], None)

    def _n_editor_setSelection(self, p):
        ed = self.editor_for(p.get("path") or "")
        if ed is not None:
            l1, c1, l2, c2 = p["selection"]
            ed.setSelection(l1, c1, l2, c2)

    def _n_editor_reveal(self, p):
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

    def _setup_views(self):
        views = self.contributed_views()
        if not views:
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

    def show_view(self, view_id: str):
        dock = self._view_dock(view_id)
        dock.show()
        dock.raise_()
        tree = dock.widget()
        if tree.topLevelItemCount() == 0:
            self._load_children(view_id, tree, None)

    def _view_dock(self, view_id: str) -> QDockWidget:
        self._view_docks = getattr(self, "_view_docks", {})
        d = self._view_docks.get(view_id)
        if d is not None:
            return d
        title = self.contributed_views().get(view_id, view_id)
        d = QDockWidget(title, self.win)
        d.setObjectName("vsxView_" + re.sub(r"\W+", "_", view_id))
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.itemExpanded.connect(lambda it, v=view_id, t=tree: self._expand(v, t, it))
        tree.itemActivated.connect(lambda it, _c=0: self._activate_item(it))
        tree.itemClicked.connect(lambda it, _c=0: self._activate_item(it))
        d.setWidget(tree)
        self.win.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, d)
        d.hide()
        self._view_docks[view_id] = d
        return d

    def _load_children(self, view_id, tree, parent_item):
        if not self.host.running():
            return
        handle = parent_item.data(0, Qt.ItemDataRole.UserRole) if parent_item is not None else None

        def got(items):
            try:
                if parent_item is not None:
                    parent_item.takeChildren()
                else:
                    tree.clear()
            except RuntimeError:
                return
            for it in items or []:
                label = codicons(it.get("label") or "")
                if it.get("description"):
                    label += "   " + codicons(it["description"])
                node = QTreeWidgetItem([label])
                node.setData(0, Qt.ItemDataRole.UserRole, it.get("handle"))
                node.setData(0, Qt.ItemDataRole.UserRole + 1, it.get("command"))
                node.setData(0, Qt.ItemDataRole.UserRole + 2, it.get("path"))
                node.setToolTip(0, it.get("tooltip") or "")
                if it.get("collapsible"):
                    node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                (parent_item.addChild if parent_item is not None else tree.addTopLevelItem)(node)
                if it.get("collapsible") == 2:
                    node.setExpanded(True)
        self.before_request()
        self.host.request("tree/children", {"viewId": view_id, "handle": handle}, got, timeout_ms=15000)

    def _expand(self, view_id, tree, item):
        if not item.data(0, Qt.ItemDataRole.UserRole + 3):
            item.setData(0, Qt.ItemDataRole.UserRole + 3, True)
            self._load_children(view_id, tree, item)

    def _activate_item(self, item):
        cmd = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if isinstance(cmd, dict) and cmd.get("command"):
            self.execute(cmd["command"], cmd.get("arguments") or [])
        elif item.data(0, Qt.ItemDataRole.UserRole + 2):
            self.open_path(item.data(0, Qt.ItemDataRole.UserRole + 2))

    def _n_tree_registered(self, p):
        vid = p.get("viewId")
        if vid in self.contributed_views():
            d = self._view_dock(vid)
            if d.isVisible():
                self._load_children(vid, d.widget(), None)

    def _n_tree_changed(self, p):
        d = getattr(self, "_view_docks", {}).get(p.get("viewId"))
        if d is not None and d.isVisible():
            self._load_children(p["viewId"], d.widget(), None)

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

    # workspace folders follow the solution
    for sig_name in ("projectOpened", "solutionOpened"):
        sig = getattr(win, sig_name, None)
        if sig is not None:
            try:
                sig.connect(lambda *_a: svc.host.running() and svc.host.notify("workspace/folders", {"folders": svc.folders()}))
            except Exception:  # noqa: BLE001
                pass
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
    QTimer.singleShot(1500, svc.start)          # after the IDE is up (extensions do not slow the start)
    return svc


__all__ = ["VsxService", "install", "codicons", "QuickPickDialog", "InputDialog", "OutputPanel"]
