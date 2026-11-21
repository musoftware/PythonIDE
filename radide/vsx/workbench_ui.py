"""IDE side of the extension host's workbench services (radide/vsx/host/workbench.js, services.js).

``WorkbenchUI(svc)`` is created by ``VsxService`` (host_ide.py) and gives the VS Code APIs that used to be
no-op mocks a real UI in RAD IDE:

  * ``vscode.diff`` / ``vscode.changes``: a Diff tab (the Monaco diff editor of editor_extras.DiffView) whose
    right side is editable; virtual documents (FileSystemProvider / content provider schemes) stay in sync with
    the extension host (diff/changed, diff/setText, diff/save). The ``editor/title`` menu items of extensions
    whose ``when`` clause is true (e.g. Claude Code's Accept / Reject Proposed Changes) are toolbar buttons.
  * ``window.tabGroups``: the current tab is reported (tabs/active), closing a Diff tab is reported
    (tabs/closed); the host can close / activate tabs (tabs/close, tabs/activate).
  * virtual documents shown with ``showTextDocument``: an editable temp copy whose edits and Ctrl+S go back
    to the extension (editor/setText, editor/saved).
  * ``window.createTerminal``: an "Extension Terminals" dock - one tab per terminal (process or
    Pseudoterminal), an input line, double-click a line for terminal link providers, terminal profiles.
  * ``window.registerUriHandler``: Extensions > "Open Extension URI..." delivers radide://publisher.name/...
  * ``window.registerFileDecorationProvider``: badge / tooltip / colour on the editor tabs.
  * ``onDidChangeTextEditorVisibleRanges`` / ``TextEditor.options``: Monaco scroll / options.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from PyQt6 import sip
from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QAction, QColor, QFont, QTextCursor
from PyQt6.QtWidgets import (QApplication, QDockWidget, QHBoxLayout, QInputDialog, QLineEdit, QPlainTextEdit,
                             QTabWidget, QToolButton, QVBoxLayout, QWidget)

from . import when as W

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][A-Za-z0-9]|\x1b[=>78DEHM]")


def _alive(obj) -> bool:
    try:
        return obj is not None and not sip.isdeleted(obj)
    except TypeError:
        return obj is not None


# ============================================================================ diff tabs
def _diff_view_class():
    from ..features.editor_extras import DiffView

    class VsxDiffView(DiffView):
        """A Diff tab opened by vscode.diff: virtual sides are synchronised with the extension host."""

        def __init__(self, wb: "WorkbenchUI", diff_id: str, left, right, language: str, info: dict):
            super().__init__(wb.win, left, right, language)
            self.wb = wb
            self.diff_id = diff_id
            self.vsx_info = info
            self.virtual = {"left": bool(info["left"].get("virtual")), "right": bool(info["right"].get("virtual"))}
            self._title_actions: list = []
            self.toolbar.addSeparator()
            self._sep = self.toolbar.actions()[-1]
            self.refresh_title_actions()

        # ---------------------------------------------------------------- sync with the host
        def _on_changed(self, side, text):
            if self.virtual.get(side) and "\r\n" not in (self.vsx_info[side].get("text") or ""):
                text = text.replace("\r\n", "\n")            # keep the document's line ends (Monaco may report CRLF)
            changed = (self.left if side == "left" else self.right).text != text
            super()._on_changed(side, text)
            if self.virtual.get(side) and changed:
                self.modified[side] = False                  # saved through the extension, never on close
                self._update_titles()
                self.wb.notify("diff/changed", {"id": self.diff_id, "side": side, "text": text})

        def save_side(self, side: str) -> bool:
            if self.virtual.get(side) and side == "right":
                self.wb.request("diff/save", {"id": self.diff_id})
                return True
            return super().save_side(side)

        def maybe_close(self) -> bool:
            ok = super().maybe_close()
            if ok:
                QTimer.singleShot(0, lambda: self.wb.diff_maybe_closed(self))
            return ok

        # ---------------------------------------------------------------- editor/title menu items
        def context(self) -> dict:
            ctx = self.wb.svc.context_for(None)
            uri = self.vsx_info["right"].get("uri") or ""
            scheme = uri.split(":", 1)[0] if ":" in uri[2:] or not re.match(r"^[a-zA-Z]:", uri) else "file"
            if self.vsx_info["right"].get("path"):
                scheme = "file"
            ctx.update({"resourceScheme": scheme, "resource": uri, "resourceFilename": Path(self.vsx_info["right"].get("title") or "").name,
                        "isInDiffEditor": True, "textCompareEditorVisible": True, "textCompareEditorActive": True,
                        "activeEditor": "workbench.editors.textDiffEditor", "editorTextFocus": True,
                        "resourceLangId": self.language, "editorLangId": self.language})
            return ctx

        def refresh_title_actions(self):
            if not _alive(self):
                return
            items = self.wb.title_menu_items(self.context())
            if [(a.objectName()[len("vsxTitle:"):], a.text()) for a in self._title_actions] == items:
                return                                      # unchanged (context keys change often)
            for a in self._title_actions:
                self.toolbar.removeAction(a)
                a.setParent(None)
            self._title_actions = []
            for cmd, title in items:
                a = QAction(title, self)
                a.setToolTip(f"{title}  ({cmd})")
                a.setObjectName("vsxTitle:" + cmd)
                a.triggered.connect(lambda _c=False, cmd=cmd: self.run_title_command(cmd))
                self.toolbar.insertAction(self._sep, a)
                self._title_actions.append(a)

        def title_commands(self) -> list[str]:
            return [a.objectName()[len("vsxTitle:"):] for a in self._title_actions]

        def run_title_command(self, cmd: str):
            self.wb.svc.execute(cmd, [{"$uri": self.vsx_info["right"].get("uri")}])

    return VsxDiffView


# ============================================================================ extension terminals
class TermView(QWidget):
    def __init__(self, panel: "TerminalsPanel", info: dict):
        super().__init__()
        self.panel = panel
        self.info = info
        self.id = info["id"]
        self.exited = False
        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.setFont(QFont("Consolas", 9))
        self.out.setMaximumBlockCount(20000)
        self.out.setUndoRedoEnabled(False)
        self.out.mouseDoubleClickEvent = self._double_click
        self.input = QLineEdit()
        self.input.setFont(QFont("Consolas", 9))
        self.input.setPlaceholderText("Type and press Enter (sent to the terminal)   Ctrl+C: interrupt")
        self.input.returnPressed.connect(self.submit)
        bar = QHBoxLayout()
        bar.setContentsMargins(2, 2, 2, 0)

        def btn(text, tip, slot):
            b = QToolButton(text=text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            bar.addWidget(b)
            return b
        btn("Ctrl+C", "Send Ctrl+C", lambda: self.send("\x03"))
        btn("Clear", "Clear the output", self.out.clear)
        btn("Kill", "Close this terminal", lambda: panel.close_view(self))
        bar.addStretch(1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        lay.addLayout(bar)
        lay.addWidget(self.out, 1)
        lay.addWidget(self.input)

    def send(self, text: str):
        if not self.exited:
            self.panel.wb.notify("terminal/input", {"id": self.id, "text": text})

    def submit(self):
        line = self.input.text()
        self.input.clear()
        nl = "\r" if self.info.get("pty") else ("\r\n" if sys.platform == "win32" else "\n")
        self.send(line + nl)

    def write(self, data: str):
        text = ANSI.sub("", data).replace("\r\n", "\n")
        text = re.sub(r"[^\n]*\r(?!\n)", "", text)       # carriage return without newline: overwrite the line
        text = text.replace("\x07", "")
        cur = self.out.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        cur.insertText(text)
        self.out.setTextCursor(cur)
        self.out.ensureCursorVisible()

    def _double_click(self, ev):
        cur = self.out.cursorForPosition(ev.pos())
        line = cur.block().text()
        self.panel.wb.request("terminal/link", {"id": self.id, "line": line})
        QPlainTextEdit.mouseDoubleClickEvent(self.out, ev)


class TerminalsPanel(QWidget):
    def __init__(self, wb: "WorkbenchUI"):
        super().__init__()
        self.wb = wb
        self.views: dict[str, TermView] = {}
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(lambda i: self.close_view(self.tabs.widget(i)))
        self.tabs.currentChanged.connect(self._current)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.tabs)
        self.dock = None

    def ensure_dock(self) -> QDockWidget:
        if self.dock is None:
            win = self.wb.win
            d = QDockWidget("Extension Terminals", win)
            d.setObjectName("VsxExtensionTerminals")
            d.setWidget(self)
            win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d)
            other = getattr(win, "dock_terminal", None) or getattr(win, "dock_output", None)
            if other is not None:
                try:
                    win.tabifyDockWidget(other, d)
                except Exception:  # noqa: BLE001
                    pass
            d.hide()
            self.dock = d
        return self.dock

    def _current(self, i):
        w = self.tabs.widget(i)
        if isinstance(w, TermView):
            self.wb.notify("terminal/focused", {"id": w.id})

    def create(self, p: dict):
        self.ensure_dock()
        v = TermView(self, p)
        self.views[p["id"]] = v
        self.tabs.addTab(v, p.get("name") or "Terminal")

    def show(self, tid: str, preserve_focus: bool = False):
        v = self.views.get(tid)
        if v is None:
            return
        d = self.ensure_dock()
        d.show()
        d.raise_()
        self.tabs.setCurrentWidget(v)
        if not preserve_focus:
            v.input.setFocus()

    def hide_term(self, tid: str):
        if self.dock is not None and self.tabs.count() <= 1:
            self.dock.hide()

    def write(self, tid: str, data: str):
        v = self.views.get(tid)
        if v is not None:
            v.write(data)

    def rename(self, tid: str, name: str):
        v = self.views.get(tid)
        if v is not None:
            self.tabs.setTabText(self.tabs.indexOf(v), name)

    def exited(self, tid: str, code):
        v = self.views.get(tid)
        if v is not None:
            v.exited = True
            v.write(f"\n[the terminal process exited{'' if code is None else f' with code {code}'}]\n")
            v.input.setEnabled(False)

    def remove(self, tid: str):
        v = self.views.pop(tid, None)
        if v is not None:
            i = self.tabs.indexOf(v)
            if i >= 0:
                self.tabs.removeTab(i)
            v.deleteLater()

    def close_view(self, v):
        if not isinstance(v, TermView):
            return
        if not v.exited:
            self.wb.notify("terminal/closed", {"id": v.id})
        self.remove(v.id)

    def view(self, tid=None) -> TermView | None:
        if tid and tid in self.views:
            return self.views[tid]
        w = self.tabs.currentWidget()
        return w if isinstance(w, TermView) else None


# ============================================================================ visible ranges (Monaco -> host)
class _VsxEditorBridge(QObject):
    """Published to Monaco as ``radvsx``: scroll position of the editor for TextEditor.visibleRanges."""

    def __init__(self, editor):
        super().__init__()
        self.ed = editor

    @pyqtSlot(str)
    def visibleRanges(self, js):  # noqa: N802
        wb = WorkbenchUI.current
        if wb is None:
            return
        try:
            ranges = json.loads(js)
        except ValueError:
            return
        wb.visible_ranges(self.ed, ranges)


# ============================================================================ the service
class WorkbenchUI:
    current: "WorkbenchUI | None" = None

    def __init__(self, svc):
        self.svc = svc
        self.win = svc.win
        self.diffs: dict = {}
        self.terminals = TerminalsPanel(self)
        self.fs_schemes: set[str] = set()
        self._deco_timer = None
        WorkbenchUI.current = self
        try:
            from ..monaco_editor import MonacoEditor
            MonacoEditor.channel_objects["radvsx"] = _VsxEditorBridge
        except Exception:  # noqa: BLE001
            pass
        tabs = getattr(self.win, "tabs", None)
        if tabs is not None:
            tabs.currentChanged.connect(self._current_changed)
        self._register_handlers()
        self._register_palette()

    # ---------------------------------------------------------------- plumbing
    def notify(self, method, params):
        if self.svc.host.running():
            self.svc.host.notify(method, params)

    def request(self, method, params, cb=None, timeout_ms=None):
        if self.svc.host.running():
            self.svc.host.request(method, params, cb, timeout_ms=timeout_ms)
        elif cb is not None:
            cb(None)

    def _register_handlers(self):
        H = self.svc.host.handlers

        def later(fn):
            def h(params, reply):
                QTimer.singleShot(0, lambda: reply(fn(params)))
            return h
        H["window/showDiff"] = later(self.show_diff)
        H["tabs/close"] = later(self.close_tab)
        H["tabs/activate"] = later(self.activate_tab)

    def _register_palette(self):
        try:
            from ..features import command_palette as cp
            cp.register_command("vsx.openUri", "Open Extension URI...", self.ask_uri, "Extensions")
            cp.register_command("vsx.newTerminalProfile", "New Extension Terminal from Profile...", self.ask_profile, "Extensions")
        except Exception:  # noqa: BLE001
            pass

    def handle(self, method: str, p: dict) -> bool:
        fn = getattr(self, "_n_" + method.replace("/", "_"), None)
        if fn is None:
            return False
        fn(p)
        return True

    def reset(self):
        """the host stopped: its diffs / terminals are gone"""
        for tid in list(self.terminals.views):
            self.terminals.exited(tid, None)
        self.diffs.clear()

    # ---------------------------------------------------------------- tabs
    def _widget_editor(self, w):
        if w is None:
            return None
        if w in self.svc._editors:
            return w
        ed = getattr(w, "editor", None)
        return ed if ed is not None and ed in self.svc._editors else None

    def _current_changed(self, _i=None):
        tabs = getattr(self.win, "tabs", None)
        w = tabs.currentWidget() if tabs is not None else None
        if w is not None and getattr(w, "diff_id", None) in self.diffs:
            self.notify("tabs/active", {"kind": "diff", "id": w.diff_id})
            return
        ed = self._widget_editor(w)
        if ed is not None:
            self.notify("tabs/active", {"kind": "text", "path": str(Path(ed.path).resolve())})
            self.refresh_tab_decorations()
            return
        self.notify("tabs/active", {"kind": "none"})

    def _tab_of_path(self, path: str):
        tabs = getattr(self.win, "tabs", None)
        if tabs is None:
            return -1
        key = os.path.normcase(str(Path(path).resolve()))
        for i in range(tabs.count()):
            ed = self._widget_editor(tabs.widget(i)) or getattr(tabs.widget(i), "editor", None)
            p = getattr(ed, "path", None) if ed is not None else getattr(tabs.widget(i), "path", None)
            if p and os.path.normcase(str(Path(p).resolve())) == key:
                return i
        return -1

    def close_tab(self, p: dict):
        tabs = getattr(self.win, "tabs", None)
        if tabs is None:
            return False
        if p.get("diffId"):
            v = self.diffs.pop(p["diffId"], None)
            if v is None or not _alive(v):
                return True
            i = tabs.indexOf(v)
            if i >= 0:
                tabs.removeTab(i)
            v.deleteLater()
            return True
        i = self._tab_of_path(p.get("path") or "")
        if i < 0:
            return True
        closer = getattr(self.win, "_close_tab", None)
        if callable(closer):
            closer(i)
        else:
            tabs.removeTab(i)
        return self._tab_of_path(p.get("path") or "") < 0

    def activate_tab(self, p: dict):
        tabs = getattr(self.win, "tabs", None)
        if tabs is None:
            return False
        if p.get("diffId"):
            v = self.diffs.get(p["diffId"])
            if v is not None and tabs.indexOf(v) >= 0:
                tabs.setCurrentWidget(v)
                return True
            return False
        i = self._tab_of_path(p.get("path") or "")
        if i >= 0:
            tabs.setCurrentIndex(i)
            return True
        if p.get("path") and Path(p["path"]).is_file():
            return self.svc.open_path(p["path"]) is not None
        return False

    # ---------------------------------------------------------------- diffs
    def show_diff(self, p: dict):
        from ..features.editor_extras import DiffSide, _language
        cls = _diff_view_class()
        L, R = p.get("left") or {}, p.get("right") or {}

        def side(s, editable):
            path = Path(s["path"]) if s.get("path") else None
            ed = self.svc.editor_for(path) if path is not None else None
            text = s.get("text") or ""
            if ed is not None and editable:
                try:
                    text = ed.text()
                except Exception:  # noqa: BLE001
                    pass
            return DiffSide(text.replace("\r\n", "\n"), s.get("title") or "", path if not s.get("virtual") else None,
                            bool(editable), ed if editable else None, "\r\n" in (s.get("text") or ""))
        left = side(L, bool(L.get("editable")))
        right = side(R, bool(R.get("editable")))
        lang = p.get("language") or _language(Path(R.get("title") or "x.txt"))
        lang = {"typescriptreact": "typescript", "javascriptreact": "javascript", "shellscript": "shell",
                "plaintext": "plaintext"}.get(lang, lang)
        view = cls(self, p["id"], left, right, lang, p)
        self.diffs[p["id"]] = view
        title = p.get("title") or f"{left.title} ↔ {right.title}"
        tabs = self.win.tabs
        prev = tabs.currentWidget()
        if hasattr(self.win, "_show_tab"):
            self.win._show_tab(view, title)
        else:
            tabs.setCurrentIndex(tabs.addTab(view, title))
        tabs.setTabToolTip(tabs.indexOf(view), f"{title}\n{L.get('uri')}  ↔  {R.get('uri')}")
        if p.get("preserveFocus") and prev is not None and prev is not view:
            view.setFocus()
        self._current_changed()
        return True

    def diff_maybe_closed(self, view):
        tabs = getattr(self.win, "tabs", None)
        if tabs is not None and tabs.indexOf(view) >= 0:
            return
        if self.diffs.pop(view.diff_id, None) is not None:
            self.notify("tabs/closed", {"diffId": view.diff_id})
        view.deleteLater()

    def _n_diff_setText(self, p):
        v = self.diffs.get(p.get("id"))
        if v is None or not _alive(v):
            return
        if p.get("side") == "left":
            v.set_texts(left=p.get("text") or "")
        else:
            v.set_texts(right=p.get("text") or "")

    def title_menu_items(self, ctx: dict) -> list[tuple[str, str]]:
        cmds = self.svc._contributed_commands()
        out = []
        for ext in self.svc.extensions:
            for m in (ext.contributes.get("menus") or {}).get("editor/title", []) or []:
                if not isinstance(m, dict) or m.get("command") not in cmds:
                    continue
                try:
                    ok = W.evaluate(m.get("when"), ctx)
                except Exception:  # noqa: BLE001
                    ok = False
                if ok and m["command"] not in [c for c, _t in out]:
                    from .host_ide import codicons
                    out.append((m["command"], codicons(cmds[m["command"]]["title"])))
        return out

    def context_changed(self):
        for v in list(self.diffs.values()):
            if _alive(v):
                v.refresh_title_actions()

    # ---------------------------------------------------------------- virtual documents in editors
    def _n_editor_setText(self, p):
        ed = self.svc.editor_for(p.get("path") or "")
        if ed is None:
            return
        try:
            if ed.text() != (p.get("text") or ""):
                ed.setText(p.get("text") or "")
        except Exception:  # noqa: BLE001
            pass

    def _n_editor_saved(self, p):
        ed = self.svc.editor_for(p.get("path") or "")
        if ed is not None:
            try:
                Path(p["path"]).write_text(ed.text(), "utf-8")
                ed.setModified(False)
            except (OSError, RuntimeError):
                pass

    def _n_editor_options(self, p):
        ed = self.svc.editor_for(p.get("path") or "")
        if ed is None:
            return
        opts = {"tabSize": int(p.get("tabSize") or 4), "insertSpaces": bool(p.get("insertSpaces", True))}
        ed._js(f"try{{radEditor.getModel().updateOptions({json.dumps(opts)});}}catch(e){{}}")
        if p.get("lineNumbers") is not None:
            ln = {0: "off", 1: "on", 2: "relative", 3: "interval"}.get(int(p["lineNumbers"]), "on")
            ed._js(f"try{{radEditor.updateOptions({{lineNumbers: {json.dumps(ln)}}});}}catch(e){{}}")

    def hook_editor(self, ed):
        """Monaco scroll -> editor/visibleRanges (TextEditor.visibleRanges / onDidChangeTextEditorVisibleRanges)."""
        ed._js("(function(){if(window.__vsxVis||!window.radEditor)return;window.__vsxVis=1;let t=null;"
               "function send(){t=null;const o=window.radChannel&&radChannel.objects&&radChannel.objects.radvsx;"
               "if(!o)return;o.visibleRanges(JSON.stringify(radEditor.getVisibleRanges().map(r=>[r.startLineNumber-1,"
               "r.endLineNumber-1])));}radEditor.onDidScrollChange(()=>{if(!t)t=setTimeout(send,120);});"
               "radEditor.onDidLayoutChange(()=>{if(!t)t=setTimeout(send,120);});setTimeout(send,300);})();")

    def visible_ranges(self, ed, ranges):
        if not self.svc.host.running():
            return
        try:
            path = str(Path(ed.path).resolve())
        except (OSError, AttributeError, RuntimeError):
            return
        self.notify("editor/visibleRanges", {"path": path, "ranges": ranges})

    # ---------------------------------------------------------------- terminals
    def _n_terminal_create(self, p):
        self.terminals.create(p)

    def _n_terminal_write(self, p):
        self.terminals.write(p.get("id"), p.get("data") or "")

    def _n_terminal_show(self, p):
        self.terminals.show(p.get("id"), bool(p.get("preserveFocus")))

    def _n_terminal_hide(self, p):
        self.terminals.hide_term(p.get("id"))

    def _n_terminal_rename(self, p):
        self.terminals.rename(p.get("id"), p.get("name") or "")

    def _n_terminal_exit(self, p):
        self.terminals.exited(p.get("id"), p.get("code"))

    def _n_terminal_dispose(self, p):
        self.terminals.remove(p.get("id"))

    # legacy notification of older hosts
    def _n_terminal_sendText(self, p):
        pass

    def terminal_command(self, cmd: str, tid=None):
        v = self.terminals.view(tid)
        if v is None:
            return None
        if cmd.endswith("selectAll"):
            v.out.selectAll()
        elif cmd.endswith("copySelection"):
            v.out.copy()
        elif cmd.endswith("clearSelection"):
            c = v.out.textCursor()
            c.clearSelection()
            v.out.setTextCursor(c)
        elif cmd.endswith(".clear"):
            v.out.clear()
        return True

    def ask_profile(self):
        def got(profiles):
            if not profiles:
                self.svc.status("No extension contributes a terminal profile")
                return
            names = [f"{x['title']}  ({x['ext']})" for x in profiles]
            name, ok = QInputDialog.getItem(self.win, "New Terminal", "Terminal profile:", names, 0, False)
            if ok and name in names:
                self.request("terminal/newFromProfile", {"id": profiles[names.index(name)]["id"]})
        if not self.svc.host.running() and not self.svc.start():
            return
        self.request("terminal/profiles", {}, got)

    # ---------------------------------------------------------------- URIs
    def handle_uri(self, uri: str, cb=None):
        """Deliver <scheme>://publisher.name/path?query to that extension's registerUriHandler handler."""
        if not self.svc.host.running() and not self.svc.start():
            if cb is not None:
                cb({"ok": False, "error": "the extension host is not running"})
            return
        self.request("uri/handle", {"uri": uri}, cb or (lambda r: r and not r.get("ok") and self.svc.status(
            f"Open URI: {r.get('error')}", 8000)), timeout_ms=60000)

    def ask_uri(self):
        text, ok = QInputDialog.getText(self.win, "Open Extension URI", "URI (radide://publisher.extension/path?query):")
        if ok and text.strip():
            self.handle_uri(text.strip())

    # ---------------------------------------------------------------- file decorations (editor tabs)
    def _n_decorations_fileChanged(self, p):
        if self._deco_timer is None:
            self._deco_timer = QTimer()
            self._deco_timer.setSingleShot(True)
            self._deco_timer.setInterval(200)
            self._deco_timer.timeout.connect(self.refresh_tab_decorations)
        self._deco_timer.start()

    def refresh_tab_decorations(self):
        tabs = getattr(self.win, "tabs", None)
        if tabs is None or not self.svc.host.running():
            return
        paths = {}
        for i in range(tabs.count()):
            ed = self._widget_editor(tabs.widget(i))
            if ed is not None:
                paths[str(Path(ed.path).resolve())] = tabs.widget(i)
        if not paths:
            return

        def got(res):
            if not isinstance(res, dict):
                return
            for p, w in paths.items():
                i = tabs.indexOf(w)
                if i < 0:
                    continue
                d = res.get(p)
                base = tabs.tabToolTip(i).split("\n[")[0]
                if d:
                    extra = " ".join(x for x in (d.get("badge"), d.get("tooltip")) if x)
                    tabs.setTabToolTip(i, f"{base}\n[{extra}]" if extra else base)
                    col = d.get("color") or ""
                    if col.startswith("#"):
                        tabs.tabBar().setTabTextColor(i, QColor(col))
                else:
                    tabs.setTabToolTip(i, base)
        self.request("decorations/file", {"paths": list(paths)}, got)

    def file_decorations(self, paths: list, cb):
        self.request("decorations/file", {"paths": list(paths)}, cb)

    # ---------------------------------------------------------------- misc notifications
    def _n_fs_registered(self, p):
        self.fs_schemes.add(p.get("scheme") or "")

    def _n_workspace_foldersUpdated(self, p):  # noqa: N802
        self.svc.log("workspace.updateWorkspaceFolders: " + ", ".join(p.get("folders") or []))

    # ---------------------------------------------------------------- built-in commands the IDE runs
    def exec_command(self, cmd: str, args: list):
        """-> True when handled, None when not this module's command."""
        win = self.win
        if cmd.startswith("workbench.action.terminal."):
            return self.terminal_command(cmd, args[0] if args else None)
        if cmd == "vscode.openFolder" and args:
            folder = Path(str(args[0]))
            try:
                from ..features.open_detect import open_folder_detect
                open_folder_detect(win, folder)
            except Exception:  # noqa: BLE001
                if callable(getattr(win, "open_project", None)):
                    win.open_project(folder)
            return True
        if cmd in ("revealInExplorer", "revealFileInOS") and args:
            p = args[0].get("path") if isinstance(args[0], dict) else str(args[0])
            if not p:
                return True
            if cmd == "revealInExplorer":
                d = getattr(win, "dock_solution", None)
                if d is not None:
                    d.show()
                    d.raise_()
                self.svc.status(str(p), 5000)
                return True
            if os.environ.get("RADIDE_NO_BROWSER"):        # tests: never start other programs
                return True
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", str(Path(p))])  # noqa: S603,S607
            else:
                subprocess.Popen(["xdg-open", str(Path(p).parent)])  # noqa: S603,S607
            return True
        if cmd in ("workbench.action.focusFirstEditorGroup", "workbench.action.focusActiveEditorGroup"):
            tabs = getattr(win, "tabs", None)
            w = tabs.currentWidget() if tabs is not None else None
            if w is not None:
                w.setFocus()
            return True
        if cmd in ("workbench.action.lockEditorGroup", "workbench.action.unlockEditorGroup",
                   "workbench.action.moveEditorToNewWindow", "workbench.action.copyEditorToNewWindow",
                   "workbench.action.splitEditor", "workbench.action.splitEditorRight",
                   "workbench.action.moveEditorToNextGroup", "workbench.action.moveEditorToPreviousGroup",
                   "workbench.action.newGroupRight", "workbench.action.focusSecondEditorGroup",
                   "workbench.action.joinAllGroups", "workbench.action.evenEditorWidths",
                   "workbench.action.toggleMaximizeEditorGroup"):
            return True                                 # one editor group / one window in RAD IDE
        if cmd.endswith(".focus") or cmd.startswith("workbench.view.extension."):
            return self._focus_view(cmd)
        if cmd in ("workbench.action.openSettings", "workbench.action.openGlobalSettings",
                   "workbench.action.openSettingsJson", "workbench.action.openSettings2"):
            if cmd == "workbench.action.openSettingsJson":
                try:
                    from . import contrib_configuration
                    path = contrib_configuration.settings_path()
                    if not path.exists():
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text("{}\n", "utf-8")
                    self.svc.open_path(str(path))
                    return True
                except Exception:  # noqa: BLE001
                    return None
            return None                                 # contrib_keybindings: Tools > Options...
        if cmd == "workbench.action.reopenClosedEditor":
            return True
        return None

    def _focus_view(self, cmd: str):
        svc = self.svc
        if cmd.startswith("workbench.view.extension."):
            container = cmd[len("workbench.view.extension."):]
            for ext in svc.extensions:
                views = (ext.contributes.get("views") or {}).get(container)
                if isinstance(views, list) and views:
                    vid = next((v.get("id") for v in views if isinstance(v, dict) and v.get("id")), None)
                    if vid:
                        return self._focus_view(vid + ".focus")
            return None
        vid = cmd[:-len(".focus")]
        if vid in svc.contributed_webview_views() or vid in (svc.webviews.providers if hasattr(svc.webviews, "providers") else {}):
            svc.webviews.show_view(vid)
            return True
        for ext in svc.extensions:
            for views in (ext.contributes.get("views") or {}).values():
                for v in views if isinstance(views, list) else []:
                    if isinstance(v, dict) and v.get("id") == vid:
                        if v.get("type") == "webview":
                            svc.webviews.show_view(vid)
                        else:
                            svc.show_view(vid)
                        return True
        return None


__all__ = ["WorkbenchUI", "TerminalsPanel", "ANSI"]
