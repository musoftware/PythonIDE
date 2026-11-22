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
               ".dpr": "pascal", ".lpr": "pascal", ".dpk": "pascal", ".pp": "pascal",   # Delphi / Lazarus
               ".r": "r", ".sql": "sql", ".json": "json", ".html": "html", ".css": "css", ".md": "markdown",
               ".sh": "shell", ".bat": "bat", ".xml": "xml", ".yaml": "yaml", ".yml": "yaml",
               # web files (section 8.6): each id maps to a language server in radide/lsp.py
               ".htm": "html", ".xhtml": "html", ".shtml": "html", ".phtml": "php", ".php3": "php",
               ".php4": "php", ".php5": "php", ".phps": "php", ".inc": "php", ".scss": "scss", ".less": "less",
               ".jsx": "javascript", ".cjs": "javascript", ".tsx": "typescript", ".mts": "typescript",
               ".cts": "typescript", ".jsonc": "json", ".webmanifest": "json", ".svg": "xml",
               ".twig": "twig", ".cshtml": "razor", ".hbs": "handlebars", ".ini": "ini", ".toml": "ini",
               ".dockerfile": "dockerfile", ".graphql": "graphql", ".vue": "html"}

# "Language Mode" choices offered in the editor menu (Open as PHP / HTML / ...)
LANGUAGE_CHOICES = [("PHP", "php"), ("HTML", "html"), ("CSS", "css"), ("SCSS", "scss"), ("Less", "less"),
                    ("JavaScript", "javascript"), ("TypeScript", "typescript"), ("JSON", "json"),
                    ("XML", "xml"), ("Markdown", "markdown"), ("SQL", "sql"), ("Python", "python"),
                    ("YAML", "yaml"), ("Shell", "shell"), ("Batch", "bat"), ("Plain Text", "plaintext")]
_OVERRIDES_KEY = "editor/languageOverrides"
# exact file names (lower-case) -> Monaco language id ("cargo.lock" -> "toml"): VS Code extensions'
# contributes.languages[].filenames (radide/vsx/contrib_languages.py); checked before MONACO_LANG
MONACO_FILENAMES: dict[str, str] = {}


def _settings():
    from PyQt6.QtCore import QCoreApplication, QSettings
    org = QCoreApplication.organizationName()        # same rule as radide.app.ide_settings()
    if org.upper().startswith("RADIDE-TEST"):
        return QSettings(org, QCoreApplication.applicationName() or org)
    from .paths import qsettings      # an INI file in <install>\settings for a portable build
    return qsettings()


def _path_key(path: Path) -> str:
    try:
        return str(Path(path).resolve()).lower()
    except OSError:
        return str(path).lower()


def language_overrides() -> dict[str, str]:
    """path -> Monaco language id chosen with "Open as ..." (remembered in QSettings)."""
    try:
        data = json.loads(_settings().value(_OVERRIDES_KEY, "{}") or "{}")
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError):
        return {}


def set_language_override(path: Path, lang: str | None) -> None:
    data = language_overrides()
    if lang:
        data[_path_key(path)] = lang
    else:
        data.pop(_path_key(path), None)
    _settings().setValue(_OVERRIDES_KEY, json.dumps(data))


def language_for_path(path: Path) -> str:
    """Monaco language id for a file: the user's "Open as" choice, else by extension ("custom" if unknown)."""
    lang = language_overrides().get(_path_key(path))
    if lang:
        return lang
    p = Path(path)
    if p.name.lower() in MONACO_FILENAMES:
        return MONACO_FILENAMES[p.name.lower()]
    if p.name.lower() == "dockerfile":
        return "dockerfile"
    return MONACO_LANG.get(p.suffix.lower(), "custom")

KIND = {"snippet": 27, "keyword": 17, "function": 1, "method": 0, "class": 5, "variable": 4, "property": 9,
        "module": 8, "control": 4, "event": 10, "param": 4, "instance": 4, "statement": 17}



# fn(editor) called when the cursor / selection of a Monaco editor changes (radide/vsx/host_ide.py forwards it to
# the extension host: window.onDidChangeTextEditorSelection, Claude Code's selection_changed)
SELECTION_LISTENERS: list = []


def _selection_changed(ed) -> None:
    for fn in list(SELECTION_LISTENERS):
        try:
            fn(ed)
        except Exception:  # noqa: BLE001 - a listener must never break the editor
            pass

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

    @pyqtSlot(str)
    def jsTextDelta(self, payload):
        """Big files: one change {"off", "del", "text", "len"} instead of the whole text (perf round 7)."""
        self.ed._on_js_delta(payload)

    @pyqtSlot(int, int)
    def jsCursor(self, line, col):
        self.ed._cursor = (line, col)
        _selection_changed(self.ed)

    @pyqtSlot(int, int, int, int)
    def jsSelection(self, l1, c1, l2, c2):
        self.ed._selection = (l1, c1, l2, c2)
        _selection_changed(self.ed)

    @pyqtSlot(int)
    def jsToggleBreakpoint(self, line):
        self.ed.toggle_breakpoint(line)

    @pyqtSlot(int, int, int)
    def jsComplete(self, req, line, col):
        self.ed._complete(req, line, col)

    @pyqtSlot(int, int, int)
    def jsSignature(self, req, line, col):
        self.ed._signature(req, line, col)

    @pyqtSlot(int, str, int, int, int, int)
    def jsHover(self, req, word, x, y, line=-1, col=-1):
        self.ed._hover(req, word, x, y, line, col)

    @pyqtSlot(int, int, int)
    def jsInlayHints(self, req, l1, l2):
        self.ed._inlay_hints(req, l1, l2)

    @pyqtSlot(int, int, int)
    def jsContextMenu(self, line, x, y):
        self.ed._context_menu(line, x, y)

    @pyqtSlot(int, int)
    def jsDefinition(self, line, col):
        self.ed.definitionRequested.emit(line, col)

    # AI (radide/features/ai_editor.py): ghost-text completions and Ctrl+I inline edit
    @pyqtSlot(int, int, int, bool)
    def jsInlineComplete(self, req, line, col, explicit):
        self.ed._inline_complete(req, line, col, explicit)

    @pyqtSlot(int)
    def jsInlineCancel(self, req):
        h = MonacoEditor.inline_cancel
        if h is not None:
            try:
                h(self.ed, req)
            except Exception:  # noqa: BLE001
                pass

    @pyqtSlot(int, int, int)
    def jsInlineEdit(self, x, y, h):
        self.ed.inlineEditRequested.emit(x, y, h)


class MonacoEditor(QWebEngineView):
    # callables(editor) run once each editor's page is ready (radide/features/lsp_support.py attaches servers)
    ready_hooks: list = []
    # name -> factory(editor) -> QObject published to JavaScript as window.radChannel.objects[name]
    # (radide/editkit.py: refactoring / format / coverage commands from Monaco)
    channel_objects: dict = {}
    # extra completion sources merged with the language server's items (radide/features/php_frameworks.py:
    # Laravel routes / views / config ...): fn(editor, line, col) -> list[item dict] | None. Server items with
    # the same label are dropped; an item with "exclusive": True means "only the extra items here".
    completion_providers: list = []
    # plugin overlays: fn(plugin, path) -> plugin-like object | None. The first non-None result replaces the
    # editor's plugin for that one file (radide/asm_intel/plugin.py: assembly IntelliSense for .asm / .s files
    # opened by any project's plugin). A plugin may also offer monaco_language(path) -> {"id", "monarch", "conf",
    # "folding", "triggers"} for a full Monarch grammar (radRegisterMonarch in radide/web/editor.html).
    plugin_overlays: list = []
    # AI inline completions (set by radide/features/ai_editor.py):
    #   inline_provider(editor, req, line, col, explicit) -> later editor.resolve_inline(req, text)
    #   inline_cancel(editor, req)
    inline_provider = None
    inline_cancel = None

    inlineEditRequested = pyqtSignal(int, int, int)   # Ctrl+I: caret x, y, line height (editor pixels)
    breakpointToggled = pyqtSignal(int, bool)
    languageChanged = pyqtSignal(str)        # new Monaco language id ("Open as PHP", ...)
    contextMenuAboutToShow = pyqtSignal(object)
    modificationChanged = pyqtSignal(bool)
    hoverWord = pyqtSignal(str, object)
    definitionRequested = pyqtSignal(int, int)
    textEdited = pyqtSignal()

    def __init__(self, plugin, path: Path, parent=None):
        super().__init__(parent)
        for _overlay in list(MonacoEditor.plugin_overlays):
            try:
                _wrapped = _overlay(plugin, Path(path))
            except Exception as e:  # noqa: BLE001 - an overlay must never break the editor
                print(f"[monaco] plugin overlay failed: {e}")
                _wrapped = None
            if _wrapped is not None:
                plugin = _wrapped
                break
        self.plugin = plugin
        self.path = Path(path)
        self._spec_cache = None                  # plugin.monaco_language(path), see _custom_spec
        self.names: dict[str, str] = {}
        self._lsp = None                     # radide.lsp.LspClient (optional), see the lsp property
        self._lang_override = language_overrides().get(_path_key(self.path))   # "Open as ..." choice
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
        self._extra_objects = {}
        for _name, _factory in list(MonacoEditor.channel_objects.items()):
            try:
                self._extra_objects[_name] = _factory(self)
                self._channel.registerObject(_name, self._extra_objects[_name])
            except Exception as e:  # noqa: BLE001 - an extension must never break the editor
                print(f"[monaco] channel object {_name} failed: {e}")
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
            self._register_custom(self.page().runJavaScript)
        self.page().runJavaScript(f"radSetText({json.dumps(self._text)}, {json.dumps(self.language_id())});"
                                  f"radSetReadOnly({json.dumps(self._readonly)});")
        for code in self._pending:
            self.page().runJavaScript(code)
        self._pending.clear()
        self._push_breakpoints()
        for hook in list(MonacoEditor.ready_hooks):
            try:
                hook(self)
            except Exception as e:  # noqa: BLE001 - a hook must never break the editor
                print(f"[monaco] ready hook failed: {e}")

    # ------------------------------------------------------------ language server / language mode
    @property
    def lsp(self):
        return self._lsp

    @lsp.setter
    def lsp(self, client):
        """Attach (or detach with None) a radide.lsp.LspClient. Monaco's built-in workers for the
        same language are switched off while a server is attached, and the server's completion
        trigger characters are used."""
        self._lsp = client
        lang = self.language_id()
        self._js(f"radSetLspActive({json.dumps(lang)}, {json.dumps(client is not None)});")
        if client is None:
            return
        if getattr(client, "_initialized", False):
            self._push_triggers(client)
        elif hasattr(client, "ready"):
            client.ready.connect(lambda c=client: self._push_triggers(c) if self._lsp is c else None)

    def _push_triggers(self, client):
        trig = ((getattr(client, "capabilities", None) or {}).get("completionProvider") or {}).get("triggerCharacters")
        if trig:
            self._js(f"radSetTriggers({json.dumps(self.language_id())}, {json.dumps(list(trig))});")

    def set_language(self, lang: str | None, remember: bool = True) -> None:
        """Change the language of this file ("Open as PHP"); None = back to automatic (by extension).
        The language server is detached and languageChanged is emitted so a new one can attach."""
        if remember:
            set_language_override(self.path, lang)
        self._lang_override = lang
        old = self._lsp
        if old is not None:
            try:
                old.did_close(self.path)
            except Exception:  # noqa: BLE001
                pass
            self._js(f"radSetLspActive({json.dumps(self.language_id())}, false);")
            self._lsp = None
        new = self.language_id()
        if self.language() == "custom":
            self._register_custom(self._js)
        self._diagnostics = []
        self._js(f"radSetMarkers([]); radSetLanguage({json.dumps(new)});")
        self.languageChanged.emit(new)

    def _on_js_delta(self, payload: str):
        """Apply one change of a big model to the Python copy. Offsets are UTF-16 code units, so a text with
        characters outside the BMP (or any mismatch) asks JavaScript for the whole text instead."""
        try:
            d = json.loads(payload)
            if getattr(self, "_resync", False):
                return                                   # the whole text is on its way
            old = self._text
            off, n, ins = int(d["off"]), int(d["del"]), str(d["text"])
            new = old[:off] + ins + old[off + n:]
            if len(old.encode("utf-16-le")) != 2 * len(old) or len(new.encode("utf-16-le")) != 2 * int(d["len"]):
                raise ValueError("delta does not apply")
        except Exception:  # noqa: BLE001 - fall back to the whole text
            self._resync = True
            self.page().runJavaScript("window.radSendFullText && window.radSendFullText();")
            return
        self._on_js_text(new)

    def _on_js_text(self, text: str):
        self._resync = False
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
        lang = getattr(self, "_lang_override", None)
        if lang:
            return lang
        if self._custom_spec():                  # the plugin's own Monarch grammar (assembly ...)
            return "custom"
        if self.path.name.lower() in MONACO_FILENAMES:
            return MONACO_FILENAMES[self.path.name.lower()]
        if self.path.name.lower() == "dockerfile":
            return "dockerfile"
        return MONACO_LANG.get(self.path.suffix.lower(), "custom")

    def language_id(self) -> str:
        lang = self.language()
        if lang == "custom":
            spec = self._custom_spec()
            return spec["id"] if spec else f"rad-{self.plugin.id}"
        return lang

    def _custom_spec(self) -> dict | None:
        """plugin.monaco_language(path) (cached): a full Monarch grammar for this file, or None."""
        if getattr(self, "_spec_cache", None) is None:
            spec = None
            fn = getattr(self.plugin, "monaco_language", None)
            if callable(fn):
                try:
                    spec = fn(self.path)
                except Exception as e:  # noqa: BLE001 - fall back to the simple tokenizer
                    print(f"[monaco] monaco_language failed: {e}")
                    spec = None
            self._spec_cache = spec if isinstance(spec, dict) and spec.get("id") else False
        return self._spec_cache or None

    def _register_custom(self, run) -> None:
        spec = self._custom_spec()
        if spec:
            run(f"radRegisterMonarch({json.dumps(spec)});")
        else:
            run(f"radRegisterLanguage({json.dumps(self._monarch())});")

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
        _selection_changed(self)

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
    LSP_COMPLETION_WAIT_MS = 3000         # then the plugin's completions are shown without the server's

    def _complete(self, req: int, line: int, col: int):
        items = []
        extra = self._extra_completions(line, col)
        if any(i.get("exclusive") for i in extra):      # e.g. inside route('...'): no need to wait for the server
            self._js(f"radResolve({req}, {json.dumps(extra)});")
            return
        try:
            if self.lsp is not None and self.lsp.running():
                answered = []

                def late(req=req, line=line, col=col):
                    # the server did not answer in time (csharp-ls loading the project, a busy server): the
                    # language's own completions now; the late answer is ignored (Monaco already has this request)
                    if answered:
                        return
                    answered.append(True)
                    try:
                        items = self._plugin_items(line, col)
                    except Exception:  # noqa: BLE001 - completion must never break typing
                        items = []
                    self._js(f"radResolve({req}, {json.dumps(self._final_items(extra, items))});")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(self.LSP_COMPLETION_WAIT_MS, late)

                def got(res, req=req, line=line, col=col):
                    if answered:
                        return
                    answered.append(True)
                    if isinstance(res, dict):                 # a raw CompletionList
                        res = res.get("items") or []
                    res = [i for i in (res or []) if isinstance(i, dict) and i.get("label")]
                    try:
                        if not res:
                            # the server is still indexing (rust-analyzer, ...) or found nothing: the language's
                            # own completions instead of an empty list
                            res = self._plugin_items(line, col)
                        else:
                            # the IDE's own API of the language (GUI Bridge helpers like msgbox / set / get,
                            # control names) next to the server's items
                            have = {i.get("label") for i in res}
                            res += [i for i in self._plugin_items(line, col, ("function", "control", "snippet"))
                                    if i["label"] not in have]
                    except Exception as e:  # noqa: BLE001 - completion must never break typing
                        print(f"[monaco] plugin completions failed: {e}")
                    self._js(f"radResolve({req}, {json.dumps(self._final_items(extra, res))});")
                self.lsp.completion(self.path, self._text, line, col, got)
                return
            items = self._plugin_items(line, col)
        except Exception:  # noqa: BLE001 - completion must never break typing
            items = []
        self._js(f"radResolve({req}, {json.dumps(self._final_items(extra, items))});")

    def _plugin_items(self, line: int, col: int, kinds: tuple | None = None) -> list[dict]:
        """The language plugin's completions as Monaco items (kinds: only these Completion kinds)."""
        items = []
        for c in self.plugin.completions(self._text, line, col, self.path, self.names)[:400]:
            if kinds is not None and c.kind not in kinds:
                continue
            item = {"label": c.name, "kind": KIND.get(c.kind, 18), "detail": c.detail or c.kind}
            # optional fields (radide/asm_intel AsmCompletion): docs, snippets, sort key, extra edits
            for attr, key in (("doc", "documentation"), ("insert", "insertText"), ("sort", "sortText")):
                val = getattr(c, attr, None)
                if val:
                    item[key] = val
            if getattr(c, "snippet", False):
                item["snippet"] = True
            if getattr(c, "edits", None):
                item["additionalTextEdits"] = c.edits
            items.append(item)
        return items

    def _extra_completions(self, line: int, col: int) -> list[dict]:
        out: list[dict] = []
        for fn in list(MonacoEditor.completion_providers):
            try:
                out += fn(self, line, col) or []
            except Exception as e:  # noqa: BLE001 - completion must never break typing
                print(f"[monaco] completion provider failed: {e}")
        return out

    def _final_items(self, extra: list[dict], items) -> list[dict]:
        merged = self._merge_completions(extra, items)
        try:
            if self.language() == "python":
                merged = self.rank_private_last(merged)
        except Exception:  # noqa: BLE001 - completion must never break typing
            pass
        return merged

    @staticmethod
    def rank_private_last(items: list[dict]) -> list[dict]:
        """Python: after "self." the form's controls / members come first, then _private names, dunders last
        (Monaco orders by sortText - "_" sorts before lower-case letters, so __annotations__ ... led the list).
        Every item gets a sortText (Monaco falls back to the label when only some have one); the order inside each
        group stays the server's / plugin's."""
        for it in items or []:
            label = it.get("label")
            name = (label.get("label") if isinstance(label, dict) else str(label or "")).strip()
            if name.startswith("__") and name.endswith("__") and len(name) > 4:
                group = "2"
            elif name.startswith("_"):
                group = "1"
            else:
                group = "0"
            it["sortText"] = group + str(it.get("sortText") or name)
        return items

    @staticmethod
    def _merge_completions(extra: list[dict], items) -> list[dict]:
        if not extra:
            return items or []
        if any(i.get("exclusive") for i in extra):
            return extra
        labels = {i.get("label") for i in extra}
        return extra + [i for i in (items or []) if i.get("label") not in labels]

    def _signature(self, req: int, line: int, col: int):
        lsp = self.lsp
        if lsp is not None and lsp.running() and hasattr(lsp, "signature_info") and (getattr(lsp, "capabilities", None) or {}).get("signatureHelpProvider"):
            try:          # language server: real signatures with parameter docs
                lsp.did_change(self.path, self._text)
                answered = []

                def got(res, req=req, line=line, col=col):
                    if answered:
                        return
                    answered.append(True)
                    if res:
                        self._js(f"radResolve({req}, {json.dumps(res)});")
                    else:       # no answer (rust-analyzer without Cargo.toml / still indexing): the plugin's calltip
                        self._plugin_signature(req, line, col)
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(self.LSP_COMPLETION_WAIT_MS, lambda: got(None))      # the server is silent
                lsp.signature_info(self.path, line, col, got)
                return
            except Exception:  # noqa: BLE001 - fall back to the plugin's calltip
                pass
        self._plugin_signature(req, line, col)

    def _plugin_signature(self, req: int, line: int, col: int):
        tip = ""
        try:
            tip = self.plugin.calltip(self._text, line, col, self.path, self.names) or ""
        except Exception:  # noqa: BLE001
            tip = ""
        if isinstance(tip, dict):         # {label, documentation, parameters, activeParameter} (assembly ...)
            self._js(f"radResolve({req}, {json.dumps(tip)});")
            return
        tip = re.sub(r"<[^>]+>", "", tip)
        self._js(f"radResolve({req}, {json.dumps(tip)});")

    def _hover(self, req: int, word: str, x: int, y: int, line: int = -1, col: int = -1):
        self.hoverWord.emit(word, self.mapToGlobal(QPoint(x, y)))
        lsp = self.lsp
        if line >= 0 and lsp is not None and lsp.running() and (getattr(lsp, "capabilities", None) or {}).get("hoverProvider"):
            try:          # language server hover: signature + documentation (markdown)
                answered = []

                def got(text, req=req, line=line, col=col):
                    if answered:
                        return
                    answered.append(True)
                    if not text:    # the server has nothing (no workspace yet, indexing): the plugin's own hover
                        try:
                            text = self.plugin.hover(self._text, line, col, self.path, self.names) or ""
                        except Exception:  # noqa: BLE001 - hover must never break the editor
                            text = ""
                    self._js(f"radResolve({req}, {json.dumps(text or None)});")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(self.LSP_COMPLETION_WAIT_MS, lambda: got(None))      # the server is silent
                lsp.hover(self.path, line, col, got)
                return
            except Exception:  # noqa: BLE001
                pass
        text = ""
        if line >= 0:
            try:          # the plugin's own hover (Ring: radide/languages/ring_intel.py)
                text = self.plugin.hover(self._text, line, col, self.path, self.names) or ""
            except Exception:  # noqa: BLE001 - hover must never break the editor
                text = ""
        self._js(f"radResolve({req}, {json.dumps(text or None)});")

    # inlay hints: callable(editor) -> bool decides per editor (radide/features/rust_ide.py: Rust setting)
    inlay_hints_enabled = None

    def _inlay_hints(self, req: int, l1: int, l2: int):
        lsp = self.lsp
        on = MonacoEditor.inlay_hints_enabled
        try:
            ok = lsp is not None and lsp.running() and hasattr(lsp, "inlay_hints") and (on is None or on(self))
        except Exception:  # noqa: BLE001
            ok = False
        if not ok:
            self._js(f"radResolve({req}, []);")
            return
        lsp.did_change(self.path, self._text)
        lines = self._text.split("\n")          # the range must stay inside the document (rust-analyzer rejects
        last = max(0, len(lines) - 1)           # "line N col 0" past the last line)
        end_col = 0
        if l2 > last:
            l2, end_col = last, len(lines[last].encode("utf-16-le")) // 2
        lsp.inlay_hints(self.path, min(l1, last), l2,
                        lambda hints: self._js(f"radResolve({req}, {json.dumps(hints or [])});"), end_col)

    def refresh_inlay_hints(self) -> None:
        self._js("if (window.radRefreshInlayHints) radRefreshInlayHints();")

    # ------------------------------------------------------------ AI inline completions
    def _inline_complete(self, req: int, line: int, col: int, explicit: bool):
        h = MonacoEditor.inline_provider
        if h is None:
            self.resolve_inline(req, None)
            return
        try:
            h(self, req, line, col, explicit)
        except Exception as e:  # noqa: BLE001 - completion must never break typing
            print(f"[monaco] inline completion failed: {e}")
            self.resolve_inline(req, None)

    def resolve_inline(self, req: int, text: str | None) -> None:
        self._js(f"radResolve({req}, {json.dumps(text or None)});")

    def set_inline_enabled(self, on: bool, delay_ms: int = 0) -> None:
        self._js(f"radSetInline({json.dumps(bool(on))}, {int(delay_ms)});")

    def trigger_inline_suggest(self) -> None:
        self._js("radInlineSuggest();")

    def offset_of(self, line: int, col: int) -> int:
        lines = self._text.split("\n")
        line = max(0, min(line, len(lines) - 1))
        return sum(len(x) + 1 for x in lines[:line]) + min(col, len(lines[line]))

    def smart_complete(self, auto=False):
        self._js("radEditor.trigger('rad', 'editor.action.triggerSuggest', {});")

    def show_calltip(self):
        self._js("radEditor.trigger('rad', 'editor.action.triggerParameterHints', {});")

    def set_diagnostics(self, diags: list[dict]) -> None:
        """diags: [{line, col, endLine, endCol, message, severity: 'error'|'warning'|'info'}] (0-based).
        Kept in ``_diagnostics``: the quick fixes (radide/quickfix) read which names are unresolved."""
        self._diagnostics = list(diags or [])
        self._js(f"radSetMarkers({json.dumps(diags)});")

    # ------------------------------------------------------------ context menu
    def contextMenuEvent(self, e):
        pass          # Monaco shows its own; ours comes from jsContextMenu

    def emmet_expand(self):
        self._js("radEditor.focus(); radEmmetExpand(true);")

    def add_language_menu(self, menu: QMenu) -> QMenu:
        """'Open as PHP' + a 'Language Mode' submenu (choose the language of this file)."""
        cur = self.language_id()
        if cur != "php":
            menu.addAction("Open as PHP", lambda: self.set_language("php"))
        sub = menu.addMenu("Language Mode")
        auto = sub.addAction("Auto Detect (by extension)", lambda: self.set_language(None))
        auto.setCheckable(True)
        auto.setChecked(not self._lang_override)
        sub.addSeparator()
        for title, lid in LANGUAGE_CHOICES:
            a = sub.addAction(title, lambda lid=lid: self.set_language(lid))
            a.setCheckable(True)
            a.setChecked(lid == cur)
        return sub

    def _context_menu(self, line: int, x: int, y: int):
        m = QMenu(self)
        for text, cmd in (("Cut", "cut"), ("Copy", "copy"), ("Paste", "paste")):
            m.addAction(text, getattr(self, cmd))
        m.addSeparator()
        m.addAction("Go to Definition", lambda: self.definitionRequested.emit(*self._cursor))
        m.addAction("Format Document", lambda: self._js("radEditor.trigger('rad', 'editor.action.formatDocument');"))
        if self.language_id() in ("html", "php", "css", "scss", "less"):
            m.addAction("Emmet: Expand Abbreviation\tTab", self.emmet_expand)
        m.addSeparator()
        self.add_language_menu(m)
        m.addAction("Command Palette...", lambda: self._js("radEditor.focus(); radEditor.trigger('rad', 'editor.action.quickCommand');"))
        self.contextMenuAboutToShow.emit(m)
        m.exec(self.mapToGlobal(QPoint(x, y)))


def _component_members(editor, line: int, col: int) -> list[dict]:
    """IntelliSense members of component package controls (radide/components/intellisense.py)."""
    from .components.intellisense import monaco_completions
    return monaco_completions(editor, line, col)


MonacoEditor.completion_providers.append(_component_members)
