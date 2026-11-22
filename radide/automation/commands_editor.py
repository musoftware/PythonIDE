"""Code editor commands for both editors (Monaco in QtWebEngine and the built-in CodeEditor): read / replace
text, move the caret, type like a user, look at the IntelliSense list, run JavaScript in Monaco."""
from __future__ import annotations

import json
import time

from PyQt6.QtCore import QEventLoop, QTimer

from .registry import AutomationError, command
from .commands_core import pump

try:
    from PyQt6.QtTest import QTest
except ImportError:  # pragma: no cover
    QTest = None


def current_editor(ctx, file: str | None = None):
    win = ctx.win
    if file:
        form = win._form_for_file(file) if hasattr(win, "_form_for_file") else None
        if form:
            win.open_code(form)
            pump()
            return win.codeviews[form].editor
        win.open_module(file)
        pump()
        ed = win._editor_for_file(file)
        if ed is None:
            raise AutomationError(f"no editor for {file}")
        return ed
    w = win.tabs.currentWidget()
    ed = getattr(w, "editor", None) or (w if hasattr(w, "toPlainText") or hasattr(w, "text") else None)
    if ed is None:
        raise AutomationError(f"the current tab is not a code editor ({type(w).__name__})")
    return ed


def is_monaco(ed) -> bool:
    return type(ed).__name__ == "MonacoEditor"


def run_js(ed, code: str, timeout_ms: int = 5000):
    """Run JavaScript in a Monaco editor page and wait for its (JSON-able) value."""
    box = {}
    loop = QEventLoop()

    def got(v):
        box["v"] = v
        loop.quit()
    ed.page().runJavaScript(code, got)
    QTimer.singleShot(int(timeout_ms), loop.quit)
    loop.exec()
    if "v" not in box:
        raise AutomationError("JavaScript did not answer in time")
    return box["v"]


def wait_ready(ed, timeout_s: float = 20) -> bool:
    if not is_monaco(ed):
        return True
    end = time.monotonic() + timeout_s
    while not getattr(ed, "_ready", True) and time.monotonic() < end:
        pump(100)
    return bool(getattr(ed, "_ready", True))


@command("editor_text", doc="text of the current (or given file's) editor, its caret, modified flag, engine")
def _text(ctx, file: str | None = None):
    ed = current_editor(ctx, file)
    wait_ready(ed)
    try:
        line, col = ed.getCursorPosition()
    except Exception:  # noqa: BLE001
        line = col = -1
    return {"text": ed.text() if hasattr(ed, "text") else ed.toPlainText(), "line": line, "col": col,
            "modified": bool(ed.isModified()) if hasattr(ed, "isModified") else None,
            "engine": "monaco" if is_monaco(ed) else type(ed).__name__}


@command("editor_set_text", doc="replace the whole text of the editor (like select all + paste)")
def _set_text(ctx, text: str, file: str | None = None):
    ed = current_editor(ctx, file)
    wait_ready(ed)
    ed.selectAll()
    ed.replaceSelectedText(text) if hasattr(ed, "replaceSelectedText") else ed.setText(text)
    pump(100)
    return _text(ctx, None)


@command("editor_goto", doc="move the caret to line (1-based) / col (0-based)")
def _goto(ctx, line: int, col: int = 0, file: str | None = None):
    ed = current_editor(ctx, file)
    wait_ready(ed)
    ed.setCursorPosition(int(line) - 1, int(col)) if is_monaco(ed) or hasattr(ed, "setCursorPosition") \
        else ed.goto_line(int(line))
    ed.setFocus()
    pump(100)
    return list(ed.getCursorPosition()) if hasattr(ed, "getCursorPosition") else None


@command("editor_find", doc="line numbers (1-based) whose text contains needle")
def _find(ctx, needle: str, file: str | None = None):
    ed = current_editor(ctx, file)
    wait_ready(ed)
    text = ed.text() if hasattr(ed, "text") else ed.toPlainText()
    return [i + 1 for i, ln in enumerate(text.splitlines()) if needle in ln]


@command("editor_type", doc="type text at the caret like a user: key events into the built-in editor, "
                            "Monaco's 'type' command in Monaco (IntelliSense / auto-indent react to it)")
def _type(ctx, text: str, file: str | None = None, delay_ms: int = 0):
    ed = current_editor(ctx, file)
    wait_ready(ed)
    ed.setFocus()
    if is_monaco(ed):
        for chunk in (list(text) if delay_ms else [text]):
            run_js(ed, "window.radEditor.focus(); window.radEditor.trigger('keyboard', 'type', {text: %s}); true"
                   % json.dumps(chunk))
            if delay_ms:
                pump(delay_ms)
        pump(150)
    else:
        if QTest is None:
            raise AutomationError("PyQt6.QtTest missing")
        for chunk in (list(text) if delay_ms else [text]):
            QTest.keyClicks(ed, chunk)
            if delay_ms:
                pump(delay_ms)
        pump(100)
    return _text(ctx, None)


@command("editor_key", doc="a key in the editor: 'Return', 'Escape', 'Tab', 'Ctrl+Space' ...")
def _key(ctx, keys: str, file: str | None = None):
    ed = current_editor(ctx, file)
    wait_ready(ed)
    ed.setFocus()
    if is_monaco(ed):
        m = {"ctrl+space": "editor.action.triggerSuggest", "escape": "hideSuggestWidget",
             "tab": "acceptSelectedSuggestion", "return": None, "enter": None}
        k = keys.lower()
        if k in ("return", "enter"):
            run_js(ed, "window.radEditor.trigger('keyboard', 'type', {text: '\\n'}); true")
        elif k in m:
            run_js(ed, f"window.radEditor.trigger('keyboard', {json.dumps(m[k])}, {{}}); true")
        else:
            run_js(ed, f"window.radEditor.trigger('keyboard', {json.dumps(keys)}, {{}}); true")
    else:
        from .commands_widgets import send_keys
        send_keys(ed, keys)
    pump(150)
    return True


@command("completion", doc="the IntelliSense list as shown now: {visible, items[]} (Monaco: suggest widget)")
def _completion(ctx, file: str | None = None, wait_ms: int = 3000):
    ed = current_editor(ctx, file)
    wait_ready(ed)
    end = time.monotonic() + wait_ms / 1000
    while True:
        if is_monaco(ed):
            res = run_js(ed, """(function(){
              const w = document.querySelector('.editor-widget.suggest-widget');
              const vis = !!(w && w.offsetParent !== null && getComputedStyle(w).visibility !== 'hidden'
                            && w.classList.contains('visible'));
              const rows = w ? Array.from(w.querySelectorAll('.monaco-list-row .label-name'))
                                 .map(e => e.textContent) : [];
              return {visible: vis, items: rows};
            })()""")
        else:
            p = ed.popup
            res = {"visible": p.isVisible(), "items": [p.item(i).text() for i in range(min(p.count(), 200))]}
        if (res.get("visible") and res.get("items")) or time.monotonic() >= end:
            return res
        pump(100)


@command("monaco_js", doc="run JavaScript in the current Monaco editor page (needs the token)", token=True)
def _monaco_js(ctx, code: str, file: str | None = None):
    ed = current_editor(ctx, file)
    if not is_monaco(ed):
        raise AutomationError("the current editor is not Monaco")
    wait_ready(ed)
    return run_js(ed, code)


@command("editor_markers", doc="Monaco's problem markers of the current model [{line, message, severity}]")
def _markers(ctx, file: str | None = None):
    ed = current_editor(ctx, file)
    if not is_monaco(ed):
        return []
    wait_ready(ed)
    return run_js(ed, """monaco.editor.getModelMarkers({resource: window.radEditor.getModel().uri})
        .map(m => ({line: m.startLineNumber, message: m.message, severity: m.severity}))""")
