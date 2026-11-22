"""VS Code editor commands on RAD IDE's Monaco editors.

Monaco is VS Code's editor: ``editor.trigger(source, id, args)`` runs its editor actions (editor.action.*), editor
commands (cursor*, editor.fold, deleteLeft, acceptSelectedSuggestion ...) and the core commands (type, paste,
cut, compositionType, cursorMove, editorScroll ...) with the same ids and argument shapes as VS Code
(reference/monaco_commands.json lists the ids the bundled Monaco 0.52 has). This module adds what VS Code
implements outside src/vs/editor and Monaco therefore lacks:

* option toggles of the workbench (toggleWordWrap, toggleMinimap, toggleRenderWhitespace,
  toggleRenderControlCharacter, toggleStickyScroll), applied to every editor like the VS Code setting;
* window zoom (workbench.action.zoomIn / Out / Reset) as the editor font zoom of every editor;
* a few editor commands newer than the bundle (editor.action.insertFinalNewLine, reverseLines, gotoOffset ...),
  written as Monaco edits;
* ``default:*`` aliases (VS Code's ids for the type / paste handlers).
``run(ed, id, args)`` executes one; ``handles(id)``; ``EDITOR_IDS`` for coverage. No Qt import."""
from __future__ import annotations

import json
from pathlib import Path

REF = Path(__file__).resolve().parent / "reference"

ALIASES = {"default:type": "type", "default:paste": "paste", "default:cut": "cut",
           "default:compositionStart": "compositionStart", "default:compositionEnd": "compositionEnd",
           "default:compositionType": "compositionType", "default:replacePreviousChar": "replacePreviousChar"}

_TOGGLES = {
    # id: JS expression computing the new options from `o` (EditorOption enum) and `e` (editor)
    "editor.action.toggleWordWrap": "({wordWrap: e.getOption(o.wordWrap) === 'off' ? 'on' : 'off'})",
    "editor.action.toggleMinimap": "({minimap: {enabled: !e.getOption(o.minimap).enabled}})",
    "editor.action.toggleRenderWhitespace": "({renderWhitespace: e.getOption(o.renderWhitespace) !== 'none' ? 'none' : 'all'})",
    "editor.action.toggleRenderControlCharacter": "({renderControlCharacters: !e.getOption(o.renderControlCharacters)})",
    "editor.action.toggleStickyScroll": "({stickyScroll: {enabled: !e.getOption(o.stickyScroll).enabled}})",
    "editor.action.toggleColumnSelection": "({columnSelection: !e.getOption(o.columnSelection)})",
    "editor.action.toggleMultiCursorModifier": "({multiCursorModifier: e.getOption(o.multiCursorModifier) === 'altKey' ? 'ctrlCmd' : 'alt'})",
}
_ZOOM = {"workbench.action.zoomIn": "editor.action.fontZoomIn", "workbench.action.zoomOut": "editor.action.fontZoomOut",
         "workbench.action.zoomReset": "editor.action.fontZoomReset"}
_JS_EDITS = {
    # VS Code 1.10x editor commands the Monaco bundle does not have yet
    "editor.action.insertFinalNewLine": """
      const m = e.getModel(); const n = m.getLineCount(); const last = m.getLineContent(n);
      if (last.length) e.executeEdits('vsx', [{range: new monaco.Range(n, last.length + 1, n, last.length + 1), text: m.getEOL()}]);""",
    "editor.action.reverseLines": """
      const m = e.getModel(); const sels = e.getSelections();
      const edits = sels.map((s) => { let a = s.startLineNumber, b = s.endLineNumber;
        if (a === b) { a = 1; b = m.getLineCount(); }
        if (b > a && s.endColumn === 1 && s.endLineNumber > s.startLineNumber) b--;
        const lines = []; for (let i = a; i <= b; i++) lines.push(m.getLineContent(i));
        return {range: new monaco.Range(a, 1, b, m.getLineMaxColumn(b)), text: lines.reverse().join(m.getEOL())}; });
      e.executeEdits('vsx', edits);""",
    "editor.action.hideHover": "e.trigger('vsx', 'editor.action.hideHover', {}); const h = e.getContribution('editor.contrib.hover'); if (h && h.hideContentHover) h.hideContentHover();",
    "editor.action.hideLongLineWarningHover": "",
}
_NEEDS_ARG = {"editor.action.gotoOffset"}


def _monaco_ids() -> set:
    try:
        return set(json.loads((REF / "monaco_commands.json").read_text("utf-8"))["commands"])
    except (OSError, ValueError, KeyError):
        return set()


MONACO_IDS: set = _monaco_ids()
EDITOR_IDS = set(_TOGGLES) | set(_ZOOM) | set(_JS_EDITS) | set(ALIASES) | _NEEDS_ARG


def handles(cid: str) -> bool:
    return cid in EDITOR_IDS or cid in MONACO_IDS


def _all_editors(win) -> list:
    svc = getattr(win, "vsx_host", None)
    out = []
    try:
        out = list(svc.live_editors()) if svc is not None and hasattr(svc, "live_editors") else []
    except Exception:  # noqa: BLE001
        out = []
    if not out:
        tabs = getattr(win, "tabs", None)
        for i in range(tabs.count() if tabs is not None else 0):
            ed = getattr(tabs.widget(i), "editor", None)
            if ed is not None and hasattr(ed, "_js"):
                out.append(ed)
    return out


def run(ed, cid: str, args=None, win=None) -> bool:
    """Run a VS Code editor command on Monaco editor *ed* (the active one). True when it was sent."""
    a0 = args[0] if isinstance(args, list) and args else (args if isinstance(args, dict) else None)
    targets = _all_editors(win) if win is not None and (cid in _TOGGLES or cid in _ZOOM) else []
    if ed is not None and ed not in targets:
        targets.insert(0, ed)
    if not targets or not all(hasattr(t, "_js") for t in targets):
        return False
    if cid in _TOGGLES:
        expr = _TOGGLES[cid]
        # computed once on the active editor, applied to all (one setting in VS Code)
        js_get = f"(function(){{const e = radEditor, o = monaco.editor.EditorOption; return JSON.stringify({expr});}})()"
        first = targets[0]

        def apply(opts):
            try:
                o = json.loads(opts) if isinstance(opts, str) else None
            except ValueError:
                o = None
            if not isinstance(o, dict):
                return
            for t in targets:
                t._js(f"radEditor.updateOptions({json.dumps(o)});")
        page = first.page() if getattr(first, "_ready", False) and callable(getattr(first, "page", None)) else None
        if page is not None:
            page.runJavaScript(js_get, apply)
        else:
            for t in targets:
                t._js(f"(function(){{const e = radEditor, o = monaco.editor.EditorOption; e.updateOptions({expr});}})();")
        return True
    if cid in _ZOOM:
        targets[0]._js(f"radEditor.trigger('vsx', {json.dumps(_ZOOM[cid])}, null);")      # EditorZoom is global
        return True
    if cid in _JS_EDITS:
        body = _JS_EDITS[cid]
        if body:
            ed._js(f"(function(){{const e = radEditor; {body} }})();")
        return True
    if cid == "editor.action.gotoOffset":
        off = (a0 or {}).get("offset") if isinstance(a0, dict) else a0
        if isinstance(off, int):
            ed._js(f"(function(){{const e = radEditor; const p = e.getModel().getPositionAt({off}); e.setPosition(p);"
                   f" e.revealPositionInCenter(p); e.focus();}})();")
        return True
    mid = ALIASES.get(cid, cid)
    source = "keyboard" if mid in ("type", "compositionType", "replacePreviousChar") else "vsx"
    ed._js(f"radEditor.focus(); radEditor.trigger({json.dumps(source)}, {json.dumps(mid)}, {json.dumps(a0)});")
    return True


__all__ = ["run", "handles", "MONACO_IDS", "EDITOR_IDS", "ALIASES"]
