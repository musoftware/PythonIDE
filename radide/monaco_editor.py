"""Code editor based on Monaco (the VS Code editor) inside QtWebEngine.

Drop-in replacement for radide.editor.CodeEditor: the same synchronous API is
kept by mirroring the text and cursor on the Python side (Monaco sends every
change through QWebChannel). IntelliSense, signature help and hover come from
the language plugin (and from a Language Server when one is attached via
radide.lsp). Monaco itself provides folding, minimap, multi-cursor, find/
replace, bracket matching, Arabic/bidi rendering, etc.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QMenu

HTML = Path(__file__).resolve().parent / "web" / "editor.html"

MONACO_LANG = {".py": "python", ".pyw": "python", ".js": "javascript", ".mjs": "javascript",
               ".ts": "typescript", ".cs": "csharp", ".java": "java", ".c": "c", ".h": "c",
               ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp", ".rs": "rust", ".go": "go", ".php": "php",
               ".rb": "ruby", ".pl": "perl", ".lua": "lua", ".dart": "dart", ".ps1": "powershell",
               ".bas": "vb", ".frm": "vb", ".pas": "pascal", ".kt": "kotlin", ".swift": "swift",
               ".r": "r", ".sql": "sql", ".json": "json", ".html": "html", ".css": "css", ".md": "markdown",
               ".sh": "shell", ".bat": "bat", ".xml": "xml", ".yaml": "yaml", ".yml": "yaml"}

KIND = {"keyword": 17, "function": 1, "method": 0, "class": 5, "variable": 4, "property": 9,
        "module": 8, "control": 4, "event": 10, "param": 4, "instance": 4, "statement": 17}


class _Bridge(QObject):
    """Object published to JavaScript as `rad`."""
    def __init__(self, editor: "MonacoEditor"):
        super().__init__()
        self.ed = editor

    @pyqtSlot()
    def jsReady(self):
        self.ed._on_ready()

    @pyqtSlot(str)
    def jsTextChanged(self, text):
        self.ed._on_js_text(text)

    @pyqtSlot(int, int)
    def jsCursor(self, line, col):
        self.ed._cursor = (line, col)

    @pyqtSlot(int, int, int, int)
    def jsSelection(self, l1, c1, l2, c2):
        self.ed._selection = (l1, c1, l2, c2)

    @pyqtSlot(int)
    def jsToggleBreakpoint(self, line):
        self.ed.toggle_breakpoint(line)

    @pyqtSlot(int, int, int)
    def jsComplete(self, req, line, col):
        self.ed._complete(req, line, col)

    @pyqtSlot(int, int, int)
    def jsSignature(self, req, line, col):
        self.ed._signature(req, line, col)

    @pyqtSlot(int, str, int, int)
    def jsHover(self, req, word, x, y):
        self.ed._hover(req, word, x, y)

    @pyqtSlot(int, int, int)
    def jsContextMenu(self, line, x, y):
        self.ed._context_menu(line, x, y)

    @pyqtSlot(int, int)
    def jsDefinition(self, line, col):
        self.ed.definitionRequested.emit(line, col)


class MonacoEditor(QWebEngineView):
    breakpointToggled = pyqtSignal(int, bool)
    contextMenuAboutToShow = pyqtSignal(object)
    modificationChanged = pyqtSignal(bool)
    hoverWord = pyqtSignal(str, object)
    definitionRequested = pyqtSignal(int, int)
    textEdited = pyqtSignal()

    def __init__(self, plugin, path: Path, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.path = Path(path)
        self.names: dict[str, str] = {}
        self.lsp = None                      # radide.lsp.LspClient (optional)
        self._text = ""
        self._modified = False
        self._ready = False
        self._pending: list[str] = []
        self._cursor = (0, 0)
        self._selection = (0, 0, 0, 0)
        self._breakpoints: set[int] = set()
        self._current: int | None = None
        self._readonly = False
        self._undo_group = 0
        self._bridge = _Bridge(self)
        self._channel = QWebChannel(self)
        self._channel.registerObject("rad", self._bridge)
        self.page().setWebChannel(self._channel)
        self.page().javaScriptConsoleMessage = self._console
        self.load(QUrl.fromLocalFile(str(HTML)))

    # ------------------------------------------------------------ JS plumbing
    def _console(self, level, message, line, source):  # noqa: D401 - Qt override
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            print(f"[monaco] {message} ({source}:{line})")

    def _js(self, code: str):
        if self._ready:
            self.page().runJavaScript(code)
        else:
            self._pending.append(code)

    def _on_ready(self):
        self._ready = True
        lang = self.language()
        if lang == "custom":
            self.page().runJavaScript(f"radRegisterLanguage({json.dumps(self._monarch())});")
        self.page().runJavaScript(f"radSetText({json.dumps(self._text)}, {json.dumps(self.language_id())});"
                                  f"radSetReadOnly({json.dumps(self._readonly)});")
        for code in self._pending:
            self.page().runJavaScript(code)
        self._pending.clear()
        self._push_breakpoints()

    def _on_js_text(self, text: str):
        if text == self._text:
            return
        self._text = text
        if not self._modified:
            self._modified = True
            self.modificationChanged.emit(True)
        self.textEdited.emit()
        if self.lsp is not None:
            self.lsp.did_change(self.path, text)

    def language(self) -> str:
        return MONACO_LANG.get(self.path.suffix.lower(), "custom")

    def language_id(self) -> str:
        lang = self.language()
        return f"rad-{self.plugin.id}" if lang == "custom" else lang

    def _monarch(self) -> dict:
        """A Monarch tokenizer built from the plugin's syntax settings (Ring, Fortran, ...)."""
        p = self.plugin
        return {"id": f"rad-{p.id}", "keywords": list(p.keywords), "builtins": list(p.builtins),
                "lineComments": list(p.line_comments), "block": list(p.block_comment or []),
                "quotes": list(p.string_quotes), "ignoreCase": not p.case_sensitive}

    # ------------------------------------------------------------ CodeEditor-compatible API
    def text(self, line: int | None = None) -> str:
        if line is None:
            return self._text
        lines = self._text.split("\n")
        return lines[line] if 0 <= line < len(lines) else ""

    def setText(self, text: str) -> None:
        self._text = text.replace("\r\n", "\n")
        self._breakpoints.clear()
        self._js(f"radSetText({json.dumps(self._text)}, {json.dumps(self.language_id())});")
        self._push_breakpoints()
        self._set_modified(True)
        if self.lsp is not None:
            self.lsp.did_change(self.path, self._text)

    setPlainText = setText

    def toPlainText(self) -> str:
        return self._text

    def isModified(self) -> bool:
        return self._modified

    def setModified(self, v: bool) -> None:
        self._set_modified(v)

    def _set_modified(self, v: bool):
        if v != self._modified:
            self._modified = v
            self.modificationChanged.emit(v)

    def lines(self) -> int:
        return self._text.count("\n") + 1

    def blockCount(self) -> int:
        return self.lines()

    def getCursorPosition(self) -> tuple[int, int]:
        return self._cursor

    def setCursorPosition(self, line: int, col: int) -> None:
        self._cursor = (line, col)
        self._js(f"radSetCursor({line}, {col});")

    def setSelection(self, l1, c1, l2, c2) -> None:
        self._selection = (l1, c1, l2, c2)
        self._cursor = (l2, c2)
        self._js(f"radSetSelection({l1}, {c1}, {l2}, {c2});")

    def selectedText(self) -> str:
        l1, c1, l2, c2 = self._selection
        if (l1, c1) == (l2, c2):
            return ""
        lines = self._text.split("\n")
        if l1 == l2:
            return lines[l1][c1:c2] if l1 < len(lines) else ""
        out = [lines[l1][c1:]] + lines[l1 + 1:l2] + [lines[l2][:c2]]
        return "\n".join(out)

    def textCursor(self):
        ed = self

        class _Cur:
            def selectedText(self):
                return ed.selectedText()

            def hasSelection(self):
                return bool(ed.selectedText())
        return _Cur()

    def _replace_range(self, l1, c1, l2, c2, new: str):
        lines = self._text.split("\n")
        start = sum(len(x) + 1 for x in lines[:l1]) + c1
        end = sum(len(x) + 1 for x in lines[:l2]) + c2
        self._text = self._text[:start] + new + self._text[end:]
        self._js(f"radReplace({l1}, {c1}, {l2}, {c2}, {json.dumps(new)});")
        nl = new.split("\n")
        self._cursor = (l1 + len(nl) - 1, (c1 if len(nl) == 1 else 0) + len(nl[-1]))
        self._selection = (*self._cursor, *self._cursor)
        self._set_modified(True)
        if self.lsp is not None:
            self.lsp.did_change(self.path, self._text)

    def replaceSelectedText(self, text: str) -> None:
        l1, c1, l2, c2 = self._selection
        if (l1, c1) == (l2, c2):
            l1, c1 = l2, c2 = self._cursor
        if (l2, c2) < (l1, c1):
            l1, c1, l2, c2 = l2, c2, l1, c1
        self._replace_range(l1, c1, l2, c2, text)

    insert = replaceSelectedText
    insertPlainText = replaceSelectedText

    def removeSelectedText(self) -> None:
        self.replaceSelectedText("")

    def beginUndoAction(self):
        self._undo_group += 1

    def endUndoAction(self):
        self._undo_group = max(0, self._undo_group - 1)

    def ensureLineVisible(self, line: int) -> None:
        self._js(f"radReveal({line});")

    def centerCursor(self):
        self._js(f"radReveal({self._cursor[0]});")

    def goto_line(self, line: int) -> None:
        text = self.text(line)
        if text.strip() == "pass":
            start = len(text) - len(text.lstrip())
            self.setSelection(line, start, line, len(text))
        else:
            self.setCursorPosition(line, len(text))
        self.ensureLineVisible(line)
        self.setFocus()

    def setReadOnly(self, ro: bool) -> None:
        self._readonly = ro
        self._js(f"radSetReadOnly({json.dumps(ro)});")

    def isReadOnly(self) -> bool:
        return self._readonly

    def undo(self):
        self._js("radEditor.trigger('rad', 'undo');")

    def redo(self):
        self._js("radEditor.trigger('rad', 'redo');")

    def cut(self):
        self._js("radEditor.focus(); document.execCommand('cut');")

    def copy(self):
        self._js("radEditor.focus(); document.execCommand('copy');")

    def paste(self):
        self._js("radEditor.focus(); radEditor.trigger('keyboard', 'editor.action.clipboardPasteAction');")

    def selectAll(self):
        n = self.lines() - 1
        self.setSelection(0, 0, n, len(self.text(n)))

    def setFocus(self, *a):
        super().setFocus(*a)
        self._js("radEditor.focus();")

    def set_words(self, extra):
        pass

    def set_names(self, names: dict[str, str]) -> None:
        self.names = dict(names)

    # ------------------------------------------------------------ breakpoints / debug line
    def _push_breakpoints(self):
        self._js(f"radSetBreakpoints({json.dumps(sorted(self._breakpoints))});")

    def toggle_breakpoint(self, line: int | None = None) -> None:
        if line is None:
            line = self._cursor[0]
        on = line not in self._breakpoints
        if on:
            marks = tuple(self.plugin.line_comments) or ("#",)
            n = line
            while n < self.lines() and (not self.text(n).strip() or self.text(n).strip().startswith(marks)):
                n += 1
            if n < self.lines():
                line = n
            on = line not in self._breakpoints
        (self._breakpoints.add if on else self._breakpoints.discard)(line)
        self._push_breakpoints()
        self.breakpointToggled.emit(line, on)

    def breakpoints(self) -> list[int]:
        return sorted(self._breakpoints)

    def set_breakpoints(self, lines) -> None:
        self._breakpoints = set(lines)
        self._push_breakpoints()

    def set_current_line(self, line: int | None) -> None:
        self._current = line
        self._js(f"radSetCurrentLine({-1 if line is None else line});")
        if line is not None:
            self._cursor = (line, 0)

    # ------------------------------------------------------------ IntelliSense
    def _complete(self, req: int, line: int, col: int):
        items = []
        try:
            if self.lsp is not None and self.lsp.running():
                self.lsp.completion(self.path, self._text, line, col,
                                    lambda res: self._js(f"radResolve({req}, {json.dumps(res)});"))
                return
            for c in self.plugin.completions(self._text, line, col, self.path, self.names)[:400]:
                items.append({"label": c.name, "kind": KIND.get(c.kind, 18), "detail": c.detail or c.kind})
        except Exception:  # noqa: BLE001 - completion must never break typing
            items = []
        self._js(f"radResolve({req}, {json.dumps(items)});")

    def _signature(self, req: int, line: int, col: int):
        tip = ""
        try:
            tip = self.plugin.calltip(self._text, line, col, self.path, self.names) or ""
        except Exception:  # noqa: BLE001
            tip = ""
        tip = re.sub(r"<[^>]+>", "", tip)
        self._js(f"radResolve({req}, {json.dumps(tip)});")

    def _hover(self, req: int, word: str, x: int, y: int):
        self.hoverWord.emit(word, self.mapToGlobal(QPoint(x, y)))
        self._js(f"radResolve({req}, null);")

    def smart_complete(self, auto=False):
        self._js("radEditor.trigger('rad', 'editor.action.triggerSuggest', {});")

    def show_calltip(self):
        self._js("radEditor.trigger('rad', 'editor.action.triggerParameterHints', {});")

    def set_diagnostics(self, diags: list[dict]) -> None:
        """diags: [{line, col, endLine, endCol, message, severity: 'error'|'warning'|'info'}] (0-based)."""
        self._js(f"radSetMarkers({json.dumps(diags)});")

    # ------------------------------------------------------------ context menu
    def contextMenuEvent(self, e):
        pass          # Monaco shows its own; ours comes from jsContextMenu

    def _context_menu(self, line: int, x: int, y: int):
        m = QMenu(self)
        for text, cmd in (("Cut", "cut"), ("Copy", "copy"), ("Paste", "paste")):
            m.addAction(text, getattr(self, cmd))
        m.addSeparator()
        m.addAction("Go to Definition", lambda: self.definitionRequested.emit(*self._cursor))
        m.addAction("Format Document", lambda: self._js("radEditor.trigger('rad', 'editor.action.formatDocument');"))
        m.addAction("Command Palette...", lambda: self._js("radEditor.focus(); radEditor.trigger('rad', 'editor.action.quickCommand');"))
        self.contextMenuAboutToShow.emit(m)
        m.exec(self.mapToGlobal(QPoint(x, y)))
