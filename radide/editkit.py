"""Editor helpers shared by Format Document, the refactoring UI and code coverage.

* ``apply_text(ed, new_text)`` / ``apply_edits(ed, edits)`` change a code editor (Monaco or the built-in
  one) with the smallest edits, as ONE undo step, and keep the Python mirror / language server in sync.
* ``apply_workspace_edit(win, edit)`` applies an LSP WorkspaceEdit to open editors and files on disk.
* ``find_editor(win, path)`` - the open editor of a file (or None).
* ``set_coverage(ed, fc)`` - covered / uncovered / partial line colours in Monaco's gutter.
* Monaco extension: every editor gets a ``radx`` QWebChannel object; JavaScript actions call
  ``COMMANDS[name](editor, line, col)`` (F2 Rename, Ctrl+. Quick Actions, Shift+F12 References ...)
  and providers call ``REQUESTS[kind](editor, req, payload)`` which answer with ``resolve(ed, req, value)``.
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSlot

COMMANDS: dict = {}          # name -> callable(editor, line, col)
REQUESTS: dict = {}          # kind -> callable(editor, req, payload_json)
# Monaco actions added to every editor: (id, label, keybinding JS expression or "", command name, menu group)
ACTIONS: list = []
FORMAT_LANGS: set = set()    # Monaco languages whose Format Document goes through REQUESTS["format"]

JS = r"""
(function () {
  if (window.radx) return;
  const ed = window.radEditor;
  const waiting = new Map(); let next = 1;
  const obj = () => window.radChannel && window.radChannel.objects.radx;
  window.radx = {
    ask(kind, payload) { return new Promise(res => { const id = next++; waiting.set(id, res);
      const o = obj(); if (!o) { waiting.delete(id); res(null); return; }
      o.request(id, kind, JSON.stringify(payload || {})); }); },
    resolve(id, v) { const r = waiting.get(id); if (r) { waiting.delete(id); r(v); } },
    cmd(name) { const p = ed.getPosition(); const o = obj();
      if (o) o.command(name, p ? p.lineNumber - 1 : 0, p ? p.column - 1 : 0); },
    actions: {}, fmt: {},
    addAction(id, label, keys, name, group) {
      if (this.actions[id]) return;
      this.actions[id] = ed.addAction({ id: id, label: label, keybindings: keys || [],
        contextMenuGroupId: group || undefined, run: () => window.radx.cmd(name) });
    },
    // one undo step: [[l1, c1, l2, c2, text], ...] (0-based)
    apply(edits) {
      const m = ed.getModel();
      // Python already holds the new text: no echo (a late echo could overwrite a newer Python change)
      if (window.radMute) radMute(true);
      try {
        ed.pushUndoStop();
        ed.executeEdits('radx', edits.map(e => ({ range: new monaco.Range(e[0] + 1, e[1] + 1, e[2] + 1, e[3] + 1),
                                                 text: e[4], forceMoveMarkers: true })));
        ed.pushUndoStop();
      } finally { if (window.radMute) radMute(false); }
      return m.getVersionId();
    },
    registerFormat(langs) {
      langs.forEach(lang => {
        if (this.fmt[lang]) return;
        this.fmt[lang] = monaco.languages.registerDocumentFormattingEditProvider(lang, {
          displayName: 'RAD IDE formatter',
          provideDocumentFormattingEdits: async (model) => {
            if (model !== ed.getModel()) return [];
            const edits = await window.radx.ask('format', { lang: lang });
            if (!edits) return [];
            return edits.map(e => ({ range: new monaco.Range(e[0] + 1, e[1] + 1, e[2] + 1, e[3] + 1), text: e[4] }));
          } });
      });
    },
    unregisterFormat(langs) {
      langs.forEach(lang => { if (this.fmt[lang]) { this.fmt[lang].dispose(); delete this.fmt[lang]; } });
    },
    covDecos: [],
    coverage(c, colors) {
      if (!document.getElementById('radx-cov-style')) {
        const st = document.createElement('style'); st.id = 'radx-cov-style'; document.head.appendChild(st);
      }
      const st = document.getElementById('radx-cov-style');
      colors = colors || {};
      st.textContent = '.radx-cov-c{background:' + (colors.c || '#2EA043') + ';width:4px !important;margin-left:2px}' +
        '.radx-cov-m{background:' + (colors.m || '#E5534B') + ';width:4px !important;margin-left:2px}' +
        '.radx-cov-p{background:' + (colors.p || '#D29922') + ';width:4px !important;margin-left:2px}' +
        '.radx-cov-ml{background:' + (colors.ml || 'rgba(229,83,75,0.10)') + '}' +
        '.radx-cov-pl{background:' + (colors.pl || 'rgba(210,153,34,0.10)') + '}';
      const d = [];
      if (c) {
        const add = (lines, cls, line, ruler) => (lines || []).forEach(l => d.push({
          range: new monaco.Range(l, 1, l, 1), options: { isWholeLine: true, linesDecorationsClassName: cls,
            className: line || undefined, overviewRuler: ruler ? { color: ruler, position: 1 } : undefined,
            hoverMessage: undefined } }));
        add(c.c, 'radx-cov-c', null, null);
        add(c.m, 'radx-cov-m', 'radx-cov-ml', colors.m || '#E5534B');
        add(c.p, 'radx-cov-p', 'radx-cov-pl', colors.p || '#D29922');
      }
      this.covDecos = ed.deltaDecorations(this.covDecos, d);
    },
  };
})();
"""


class RadxBridge(QObject):
    """Published to Monaco as ``radx`` (see MonacoEditor.channel_objects)."""

    def __init__(self, editor):
        super().__init__()
        self.ed = editor

    @pyqtSlot(str, int, int)
    def command(self, name, line, col):
        fn = COMMANDS.get(name)
        if fn is None:
            return
        try:
            self.ed._cursor = (line, col)
            fn(self.ed, line, col)
        except Exception as e:  # noqa: BLE001 - never break the editor
            _log(self.ed, f"[{name}] {e}")

    @pyqtSlot(int, str, str)
    def request(self, req, kind, payload):
        fn = REQUESTS.get(kind)
        if fn is None:
            resolve(self.ed, req, None)
            return
        try:
            fn(self.ed, req, payload)
        except Exception as e:  # noqa: BLE001
            _log(self.ed, f"[{kind}] {e}")
            resolve(self.ed, req, None)


def _log(ed, text):
    w = ed.window() if hasattr(ed, "window") else None
    if w is not None and hasattr(w, "log"):
        w.log(text)
    else:
        print(text)


def resolve(ed, req: int, value) -> None:
    js(ed, f"window.radx && radx.resolve({int(req)}, {json.dumps(value)});")


def js(ed, code: str) -> None:
    if hasattr(ed, "_js"):
        ed._js(code)


def is_monaco(ed) -> bool:
    return hasattr(ed, "_js") and hasattr(ed, "_text")


_installed = False


def install_monaco() -> None:
    """Register the radx object and the per-editor JavaScript (idempotent)."""
    global _installed
    if _installed:
        return
    try:
        from .monaco_editor import MonacoEditor
    except ImportError:
        return
    _installed = True
    if hasattr(MonacoEditor, "channel_objects"):
        MonacoEditor.channel_objects["radx"] = RadxBridge
    MonacoEditor.ready_hooks.append(_on_ready)


def _on_ready(ed) -> None:
    ed._js(JS)
    for aid, label, keys, name, group in ACTIONS:
        ed._js(f"radx.addAction({json.dumps(aid)}, {json.dumps(label)}, {keys or '[]'}, {json.dumps(name)}, "
               f"{json.dumps(group)});")
    if FORMAT_LANGS:
        ed._js(f"radx.registerFormat({json.dumps(sorted(FORMAT_LANGS))});")
    for hook in list(READY):
        try:
            hook(ed)
        except Exception as e:  # noqa: BLE001
            print(f"[editkit] ready hook failed: {e}")


READY: list = []             # callables(editor) after the radx JavaScript is in place


def add_action(aid: str, label: str, keys_js: str, name: str, group: str = "") -> None:
    """A Monaco action (command palette F1, keybinding, optional context-menu group) on every editor."""
    ACTIONS.append((aid, label, keys_js, name, group))
    for ed in all_monaco_editors():
        ed._js(f"radx.addAction({json.dumps(aid)}, {json.dumps(label)}, {keys_js or '[]'}, {json.dumps(name)}, "
               f"{json.dumps(group)});")


def register_format_languages(langs) -> None:
    new = set(langs) - FORMAT_LANGS
    if not new:
        return
    FORMAT_LANGS.update(new)
    for ed in all_monaco_editors():
        ed._js(f"radx.registerFormat({json.dumps(sorted(new))});")


def sync_format_languages(langs) -> None:
    """Exactly *langs* use REQUESTS["format"]; the others go back to Monaco's / no formatter."""
    langs = set(langs)
    gone = FORMAT_LANGS - langs
    FORMAT_LANGS.clear()
    FORMAT_LANGS.update(langs)
    for ed in all_monaco_editors():
        ed._js(f"window.radx && (radx.unregisterFormat({json.dumps(sorted(gone))}), "
               f"radx.registerFormat({json.dumps(sorted(langs))}));")


def all_monaco_editors() -> list:
    try:
        from PyQt6.QtWidgets import QApplication

        from .monaco_editor import MonacoEditor
    except ImportError:
        return []
    out = []
    for w in QApplication.allWidgets():
        if isinstance(w, MonacoEditor) and getattr(w, "_ready", False):
            out.append(w)
    return out


# ============================================================================ text edits
def _offsets(text: str) -> list[int]:
    out = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            out.append(i + 1)
    return out


def diff_edits(old: str, new: str) -> list[list]:
    """Minimal line-based edits turning *old* into *new*: [[l1, c1, l2, c2, text], ...] (0-based),
    non-overlapping, in document order (Monaco applies them against the original text)."""
    a = old.split("\n")
    b = new.split("\n")
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    edits = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        rep = b[j1:j2]
        if i1 < i2:                               # replace / delete whole lines i1..i2-1
            if i2 < len(a):
                edits.append([i1, 0, i2, 0, "".join(x + "\n" for x in rep)])
            else:                                 # touches the last line: no newline after it
                if i1 > 0 and not rep:
                    edits.append([i1 - 1, len(a[i1 - 1]), i2 - 1, len(a[i2 - 1]), ""])
                else:
                    edits.append([i1, 0, i2 - 1, len(a[i2 - 1]), "\n".join(rep)])
        else:                                     # insert before line i1
            if i1 < len(a):
                edits.append([i1, 0, i1, 0, "".join(x + "\n" for x in rep)])
            else:
                last = len(a) - 1
                edits.append([last, len(a[last]), last, len(a[last]), "".join("\n" + x for x in rep)])
    merged: list[list] = []
    for e in edits:                               # touching edits -> one (no same-position ambiguity)
        if merged and (merged[-1][2], merged[-1][3]) == (e[0], e[1]):
            merged[-1] = [merged[-1][0], merged[-1][1], e[2], e[3], merged[-1][4] + e[4]]
        else:
            merged.append(e)
    return merged


def apply_edits_to_text(text: str, edits: list[list]) -> str:
    offs = _offsets(text)
    lines = text.split("\n")

    def off(l, c):
        if l >= len(offs):
            return len(text)
        return offs[l] + min(c, len(lines[l]))
    out = text
    for l1, c1, l2, c2, new in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
        s, e = off(l1, c1), off(l2, c2)
        out = out[:s] + new + out[e:]
    return out


def lsp_edits(text_edits: list[dict]) -> list[list]:
    """LSP TextEdit[] -> [[l1, c1, l2, c2, text]]."""
    out = []
    for te in text_edits or []:
        r = te.get("range") or {}
        s, e = r.get("start", {}), r.get("end", {})
        # editors and apply_workspace_edit work with "\n" (CRLF files get their CRLF back when written);
        # servers send whole-file edits with the CRLF they read from disk
        out.append([s.get("line", 0), s.get("character", 0), e.get("line", 0), e.get("character", 0),
                    te.get("newText", "").replace("\r\n", "\n")])
    return out


def apply_edits(ed, edits: list[list]) -> bool:
    """Apply edits to an open editor as one undo step. True when the text changed."""
    if not edits:
        return False
    old = ed.text()
    new = apply_edits_to_text(old, edits)
    if new == old:
        return False
    if is_monaco(ed):
        ed._text = new                                  # the mirror first: saving right after must see it
        ed._js(f"window.radx ? radx.apply({json.dumps(edits)}) : radEditor.executeEdits('radx', "
               f"{json.dumps(edits)}.map(e => ({{range: new monaco.Range(e[0]+1, e[1]+1, e[2]+1, e[3]+1), text: e[4]}})));")
        ed._set_modified(True)
        try:
            ed.textEdited.emit()
        except Exception:  # noqa: BLE001
            pass
        if getattr(ed, "lsp", None) is not None:
            ed.lsp.did_change(ed.path, new)
        return True
    # built-in editor (QScintilla / QPlainTextEdit): replace the whole text inside one undo action
    line, col = ed.getCursorPosition() if hasattr(ed, "getCursorPosition") else (0, 0)
    if hasattr(ed, "beginUndoAction"):
        ed.beginUndoAction()
    try:
        if hasattr(ed, "selectAll") and hasattr(ed, "replaceSelectedText"):
            ed.selectAll()
            ed.replaceSelectedText(new)
        else:
            ed.setText(new)
    finally:
        if hasattr(ed, "endUndoAction"):
            ed.endUndoAction()
    try:
        ed.setCursorPosition(min(line, new.count("\n")), col)
    except Exception:  # noqa: BLE001
        pass
    return True


def apply_text(ed, new_text: str) -> bool:
    return apply_edits(ed, diff_edits(ed.text(), new_text))


# ============================================================================ files / workspace edits
def _key(p) -> str:
    try:
        return str(Path(p).resolve()).lower()
    except OSError:
        return str(p).lower()


def find_editor(win, path):
    """The open code editor of *path* (any project of the solution, or a loose file), else None."""
    k = _key(path)
    ed = getattr(win, "_lsp_editors", {}).get(k)
    if ed is not None:
        try:
            ed.text()
            return ed
        except RuntimeError:
            pass
    tabs = getattr(win, "tabs", None)
    if tabs is not None:
        for i in range(tabs.count()):
            w = tabs.widget(i)
            e = getattr(w, "editor", None)
            if e is not None and getattr(e, "path", None) is not None and _key(e.path) == k:
                return e
    for e in all_monaco_editors():
        if _key(e.path) == k:
            return e
    return None


def uri_path(uri: str) -> str:
    from PyQt6.QtCore import QUrl
    return QUrl(uri).toLocalFile() if uri.startswith("file:") else uri


def workspace_changes(edit: dict) -> dict[str, list[list]]:
    """LSP WorkspaceEdit -> {abs path: [[l1, c1, l2, c2, text]]} (changes and documentChanges)."""
    out: dict[str, list] = {}
    for uri, tes in (edit or {}).get("changes", {}).items() if (edit or {}).get("changes") else []:
        out.setdefault(uri_path(uri), []).extend(lsp_edits(tes))
    for dc in (edit or {}).get("documentChanges") or []:
        if "textDocument" in dc:
            out.setdefault(uri_path(dc["textDocument"]["uri"]), []).extend(lsp_edits(dc.get("edits", [])))
    return out


def file_text(win, path) -> str:
    ed = find_editor(win, path)
    if ed is not None:
        return ed.text()
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def apply_workspace_edit(win, edit: dict | None = None, changes: dict | None = None) -> list[str]:
    """Apply to open editors (one undo step each) or straight to the files. Returns changed paths."""
    changes = changes if changes is not None else workspace_changes(edit or {})
    done = []
    for path, edits in changes.items():
        if not edits:
            continue
        ed = find_editor(win, path)
        if ed is not None:
            if apply_edits(ed, edits):
                done.append(path)
            continue
        p = Path(path)
        try:
            raw = p.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        crlf = "\r\n" in text
        new = apply_edits_to_text(text.replace("\r\n", "\n"), edits)
        if crlf:
            new = new.replace("\n", "\r\n")
        if new != text:
            p.write_text(new, encoding="utf-8", newline="")
            done.append(path)
    # resource operations (create / rename / delete files) from documentChanges
    for dc in (edit or {}).get("documentChanges") or []:
        kind = dc.get("kind")
        try:
            if kind == "create":
                p = Path(uri_path(dc["uri"]))
                if not p.exists():
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text("", encoding="utf-8")
                    done.append(str(p))
            elif kind == "rename":
                a, b = Path(uri_path(dc["oldUri"])), Path(uri_path(dc["newUri"]))
                if a.exists() and not b.exists():
                    a.rename(b)
                    done.append(str(b))
            elif kind == "delete":
                p = Path(uri_path(dc["uri"]))
                if p.is_file():
                    p.unlink()
                    done.append(str(p))
        except OSError:
            continue
    return done


# ============================================================================ coverage colours
def coverage_colors() -> dict:
    try:
        from . import theme
        dark = theme.is_dark()
        ok, bad, note = theme.color("success"), theme.color("error"), theme.color("note")
    except Exception:  # noqa: BLE001
        dark, ok, bad, note = False, "#2EA043", "#E5534B", "#D29922"

    def rgba(hexc, a):
        hexc = hexc.lstrip("#")
        r, g, b = int(hexc[0:2], 16), int(hexc[2:4], 16), int(hexc[4:6], 16)
        return f"rgba({r},{g},{b},{a})"
    return {"c": ok, "m": bad, "p": note, "ml": rgba(bad, 0.16 if dark else 0.09),
            "pl": rgba(note, 0.16 if dark else 0.09)}


def set_coverage(ed, fc) -> None:
    """fc: radide.testing.FileCoverage or None (clear)."""
    if not is_monaco(ed):
        return
    data = None if fc is None else {"c": sorted(fc.covered - fc.partial), "m": sorted(fc.missed),
                                    "p": sorted(fc.partial)}
    ed._js(f"window.radx && radx.coverage({json.dumps(data)}, {json.dumps(coverage_colors())});")


__all__ = ["COMMANDS", "REQUESTS", "READY", "install_monaco", "add_action", "register_format_languages",
           "apply_edits", "apply_text", "diff_edits", "apply_edits_to_text", "lsp_edits", "find_editor",
           "workspace_changes", "apply_workspace_edit", "file_text", "set_coverage", "resolve", "js",
           "all_monaco_editors", "is_monaco"]
