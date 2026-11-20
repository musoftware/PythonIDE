"""Refactoring on top of the Language Servers (radide/lsp.py): Edit > Refactor.

  Rename Symbol (F2)            textDocument/rename -> preview of every change in every file -> Apply
  Quick Actions (Ctrl+.)        textDocument/codeAction: quick fixes, refactorings, organize imports
  Extract Method / Variable     the server's refactor.extract actions (pylsp-rope, typescript, rust-analyzer...)
                                then the new name is asked and renamed in place
  Find All References (Shift+F12)  textDocument/references -> "Find All References" dock (double-click = go)

Without a language server: Rename works on whole words of the current file (with preview) and
references are a whole-word search of the project's files. Edits are applied to open editors as one
undo step and to closed files on disk.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QDockWidget, QHBoxLayout, QInputDialog, QLabel,
                             QMenu, QPlainTextEdit, QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from .. import editkit

DEFAULT_EXTRACT_NAMES = ("extracted_method", "extracted_variable", "newFunction", "newLocal", "new_function",
                         "new_var", "newMethod", "extracted", "fun_name", "var_name", "new_local")
WORD = re.compile(r"[A-Za-z_؀-ۿ][\w؀-ۿ]*")
CODE_EXT = {".py", ".pyw", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".cs", ".java", ".go", ".rs", ".php", ".dart",
            ".rb", ".lua", ".ring", ".bas", ".c", ".h", ".cpp", ".hpp", ".pas", ".f90", ".ps1", ".pl"}


# ============================================================================ helpers
def _uri(path) -> str:
    return Path(path).resolve().as_uri()


def word_at(text: str, line: int, col: int) -> tuple[str, int, int]:
    lines = text.split("\n")
    if not 0 <= line < len(lines):
        return "", col, col
    s = lines[line]
    for m in WORD.finditer(s):
        if m.start() <= col <= m.end():
            return m.group(0), m.start(), m.end()
    return "", col, col


def _client(ed):
    c = getattr(ed, "lsp", None)
    if c is None or not hasattr(c, "_request"):
        return None
    try:
        return c if c.running() else None
    except RuntimeError:
        return None


def _request(ed, method, params, cb):
    """LSP request with error text: cb(result, error_message)."""
    c = _client(ed)
    c.did_change(ed.path, ed.text())
    c.last_error = ""

    def done(res):
        cb(res, getattr(c, "last_error", "") if res is None else "")
    c._request(method, params, done)


def _pos(ed, line, col):
    return {"textDocument": {"uri": _uri(ed.path)}, "position": {"line": line, "character": col}}


def _status(win, text, ms=6000):
    try:
        win.statusBar().showMessage(text, ms)
    except RuntimeError:
        pass


def open_location(win, path, line: int, col: int = 0):
    """Open *path* at 0-based line/col in the IDE."""
    ed = editkit.find_editor(win, path)
    if ed is None and callable(getattr(win, "open_file", None)):
        try:
            ed = win.open_file(Path(path), line + 1)
        except Exception:  # noqa: BLE001
            ed = None
    if ed is None and callable(getattr(win, "open_any_file", None)):
        ed = win.open_any_file(Path(path))
    if ed is None:
        return None
    try:
        for i in range(win.tabs.count()):
            if getattr(win.tabs.widget(i), "editor", None) is ed:
                win.tabs.setCurrentIndex(i)
                break
        ed.setCursorPosition(line, col)
        ed.ensureLineVisible(line)
        ed.setFocus()
    except Exception:  # noqa: BLE001
        pass
    return ed


def _caret_global(ed, then):
    """then(QPoint) - global position under the caret (Monaco asks the page)."""
    if editkit.is_monaco(ed):
        def got(v):
            try:
                x, y, h = (v or [0, 0, 18])
            except (TypeError, ValueError):
                x, y, h = 0, 0, 18
            then(ed.mapToGlobal(QPoint(int(x), int(y) + int(h))))
        ed.page().runJavaScript("window.radCaretPoint ? radCaretPoint() : [0, 0, 18]", got)
        return
    try:
        r = ed.cursorRect()
        then(ed.mapToGlobal(r.bottomLeft()))
    except Exception:  # noqa: BLE001
        then(ed.mapToGlobal(QPoint(40, 40)))


# ============================================================================ preview dialog
class ChangesPreview(QDialog):
    """Every change of a refactoring, per file and line, with check boxes - like Visual Studio's preview."""

    def __init__(self, win, title: str, changes: dict[str, list], parent=None):
        super().__init__(parent or win)
        self.win = win
        self.setWindowTitle(title)
        self.resize(820, 520)
        self.changes = changes
        lay = QVBoxLayout(self)
        n = sum(len(v) for v in changes.values())
        head = QLabel(f"<b>{n}</b> change(s) in <b>{len(changes)}</b> file(s). Uncheck what should stay as it is.")
        lay.addWidget(head)
        split = QSplitter(Qt.Orientation.Vertical)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Change", "Line"])
        self.tree.setColumnWidth(0, 640)
        self.diff = QPlainTextEdit()
        self.diff.setReadOnly(True)
        self.diff.setFont(QFont("Consolas", 9))
        split.addWidget(self.tree)
        split.addWidget(self.diff)
        split.setSizes([300, 180])
        lay.addWidget(split, 1)
        self._texts = {}
        root = getattr(getattr(win, "project", None), "folder", None)
        for path, edits in sorted(changes.items()):
            text = editkit.file_text(win, path)
            self._texts[path] = text
            lines = text.split("\n")
            try:
                shown = os.path.relpath(path, root) if root else path
            except ValueError:
                shown = path
            fi = QTreeWidgetItem(self.tree, [f"{shown}  ({len(edits)})", ""])
            fi.setFlags(fi.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            fi.setCheckState(0, Qt.CheckState.Checked)
            fi.setData(0, Qt.ItemDataRole.UserRole, path)
            fi.setExpanded(True)
            for i, e in enumerate(sorted(edits, key=lambda e: (e[0], e[1]))):
                old = lines[e[0]] if e[0] < len(lines) else ""
                new_line = old[:e[1]] + e[4] + old[e[3]:] if e[0] == e[2] else e[4]
                ci = QTreeWidgetItem(fi, [f"{old.strip()}   →   {new_line.strip()}", str(e[0] + 1)])
                ci.setFlags(ci.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                ci.setCheckState(0, Qt.CheckState.Checked)
                ci.setData(0, Qt.ItemDataRole.UserRole, (path, e))
                ci.setToolTip(0, f"line {e[0] + 1}: {old}")
        self.tree.currentItemChanged.connect(self._show)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.apply_btn = box.addButton("Apply", QDialogButtonBox.ButtonRole.AcceptRole)
        self.apply_btn.setDefault(True)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addWidget(box)
        if self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def _show(self, item, _prev=None):
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        path = data if isinstance(data, str) else data[0]
        import difflib
        old = self._texts.get(path, "")
        new = editkit.apply_edits_to_text(old, self.changes.get(path, []))
        diff = difflib.unified_diff(old.split("\n"), new.split("\n"), Path(path).name, Path(path).name + " (new)",
                                    lineterm="", n=1)
        self.diff.setPlainText("\n".join(diff))

    def selected(self) -> dict[str, list]:
        out: dict[str, list] = {}
        for i in range(self.tree.topLevelItemCount()):
            fi = self.tree.topLevelItem(i)
            for j in range(fi.childCount()):
                ci = fi.child(j)
                if ci.checkState(0) == Qt.CheckState.Checked:
                    path, e = ci.data(0, Qt.ItemDataRole.UserRole)
                    out.setdefault(path, []).append(e)
        return out


def preview_and_apply(win, title: str, changes: dict[str, list], force_preview=True) -> list[str]:
    if not changes:
        return []
    norm = {}
    for path, edits in changes.items():       # whole-file edits (jedi) -> the lines that really change
        text = editkit.file_text(win, path)
        new_text = editkit.apply_edits_to_text(text, edits)
        if new_text != text:
            norm[path] = editkit.diff_edits(text, new_text)
    changes = norm
    if not changes:
        _status(win, f"{title}: nothing to change")
        return []
    if force_preview:
        dlg = ChangesPreview(win, title, changes)
        win._refactor_preview = dlg               # tests can reach it
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return []
        changes = dlg.selected()
    done = editkit.apply_workspace_edit(win, changes=changes)
    _status(win, f"{title}: {len(done)} file(s) changed")
    return done


# ============================================================================ rename
def rename_symbol(win, ed, line=None, col=None, new_name: str | None = None, preview=True):
    if ed is None:
        return
    if line is None:
        line, col = ed.getCursorPosition()
    old, c1, _c2 = word_at(ed.text(), line, col)
    if not old:
        _status(win, "Rename: put the cursor on a name first")
        return
    if new_name is None:
        new_name, ok = QInputDialog.getText(win, "Rename", f"New name for '{old}':", text=old)
        if not ok or not new_name.strip() or new_name.strip() == old:
            return
        new_name = new_name.strip()
    if _client(ed) is None:
        _rename_local(win, ed, old, new_name, preview)
        return
    _status(win, f"Renaming '{old}' to '{new_name}'...", 3000)

    title = f"Rename '{old}' to '{new_name}'"

    def got(res, err):
        if err:
            _status(win, f"Rename: {err}", 8000)
            win.log(f"[rename] {err}")
            return
        changes = editkit.workspace_changes(res) if res else {}

        # some servers (pylsp/jedi) rename only in the files they have open: the references (which
        # do search the whole project) complete the change in the other files
        def got_refs(refs, _err):
            merged = _merge_references(win, changes, refs or [], old, new_name)
            if not merged:
                _rename_local(win, ed, old, new_name, preview)
                return
            preview_and_apply(win, title, merged, force_preview=preview)
        _request(ed, "textDocument/references", {**_pos(ed, line, c1), "context": {"includeDeclaration": True}},
                 got_refs)
    _request(ed, "textDocument/rename", {**_pos(ed, line, c1), "newName": new_name}, got)


SKIP_PARTS = {".radide_backup", ".venv", "venv", "node_modules", "__pycache__", ".git", "site-packages", "_deleted"}


def _skipped(path) -> bool:
    """Backups, environments and dependencies are never refactored."""
    return bool(SKIP_PARTS & {p.lower() for p in Path(path).parts})


def _merge_references(win, changes: dict, refs: list, old: str, new: str) -> dict:
    """Rename edits (normalised to minimal line edits) + reference locations in files the rename missed."""
    out: dict[str, list] = {}
    changes = {p: e for p, e in changes.items() if not _skipped(p)}
    refs = [r for r in refs if not _skipped(editkit.uri_path(r.get("uri", "")))]
    for path, edits in changes.items():
        text = editkit.file_text(win, path)
        new_text = editkit.apply_edits_to_text(text, edits)
        if new_text != text:
            out[path] = editkit.diff_edits(text, new_text)
    done = {editkit._key(p) for p in changes}
    for loc in refs:
        path = editkit.uri_path(loc.get("uri", ""))
        if not path or editkit._key(path) in done:
            continue
        r = loc.get("range", {})
        s, e = r.get("start", {}), r.get("end", {})
        lines = editkit.file_text(win, path).splitlines()
        ln = s.get("line", -1)
        if not 0 <= ln < len(lines) or s.get("line") != e.get("line"):
            continue
        if lines[ln][s.get("character", 0):e.get("character", 0)] != old:
            continue
        edit = [ln, s.get("character", 0), ln, e.get("character", 0), new]
        if edit not in out.setdefault(path, []):
            out[path].append(edit)
    return {p: v for p, v in out.items() if v}


def _rename_local(win, ed, old, new, preview=True):
    """No language server: whole-word rename in this file (VB: case-insensitive)."""
    flags = 0
    if Path(str(getattr(ed, "path", ""))).suffix.lower() in (".bas", ".frm", ".cls", ".ring"):
        flags = re.I
    rx = re.compile(rf"(?<![\w]){re.escape(old)}(?![\w])", flags)
    edits = []
    for n, s in enumerate(ed.text().split("\n")):
        for m in rx.finditer(s):
            edits.append([n, m.start(), n, m.end(), new])
    if not edits:
        _status(win, f"'{old}' was not found")
        return
    preview_and_apply(win, f"Rename '{old}' to '{new}' (this file)", {str(ed.path): edits}, force_preview=preview)


# ============================================================================ code actions
def _diags_for(ed, line1, line2):
    c = _client(ed)
    raw = (getattr(c, "raw_diagnostics", {}) or {}).get(_uri(ed.path), []) if c else []
    if not raw and c is not None:            # the uri may be spelled differently (drive letter case)
        key = str(Path(ed.path).resolve()).lower()
        for u, ds in (getattr(c, "raw_diagnostics", {}) or {}).items():
            if editkit._key(editkit.uri_path(u)) == key:
                raw = ds
                break
    return [d for d in raw if d.get("range", {}).get("start", {}).get("line", -1) <= line2
            and d.get("range", {}).get("end", {}).get("line", -1) >= line1]


def _selection(ed, line, col):
    l1, c1, l2, c2 = getattr(ed, "_selection", (line, col, line, col))
    if (l1, c1) == (l2, c2):
        try:
            l1, c1, l2, c2 = ed.getSelection()
        except Exception:  # noqa: BLE001
            l1, c1, l2, c2 = line, col, line, col
    if (l2, c2) < (l1, c1):
        l1, c1, l2, c2 = l2, c2, l1, c1
    if l1 < 0:
        l1, c1, l2, c2 = line, col, line, col
    return l1, c1, l2, c2


def request_code_actions(win, ed, line, col, cb, only=None):
    l1, c1, l2, c2 = _selection(ed, line, col)
    ctx = {"diagnostics": _diags_for(ed, l1, l2), "triggerKind": 1}
    if only:
        ctx["only"] = list(only)
    params = {"textDocument": {"uri": _uri(ed.path)},
              "range": {"start": {"line": l1, "character": c1}, "end": {"line": l2, "character": c2}},
              "context": ctx}
    _request(ed, "textDocument/codeAction", params, lambda res, err: cb(res or [], err))


def run_code_action(win, ed, action: dict, after=None):
    """Apply a CodeAction or Command (resolve first when it has neither edit nor command)."""
    c = _client(ed)
    if c is None:
        return
    if "edit" not in action and "command" not in action and action.get("data") is not None:
        def resolved(res, err):
            if res:
                run_code_action(win, ed, res, after)
            else:
                _status(win, f"{action.get('title', 'Action')}: {err or 'nothing to do'}")
        _request(ed, "codeAction/resolve", action, resolved)
        return
    if action.get("edit"):
        changes = editkit.workspace_changes(action["edit"])
        preview_and_apply(win, action.get("title", "Code action"), changes, force_preview=len(changes) > 1)
        if after:
            after()
    cmd = action.get("command")
    if isinstance(cmd, str):                  # a bare Command
        cmd = {"command": cmd, "arguments": action.get("arguments", [])}
    if cmd:
        win._refactor_after_edit = after
        _request(ed, "workspace/executeCommand", {"command": cmd["command"], "arguments": cmd.get("arguments", [])},
                 lambda res, err: _status(win, f"{action.get('title', '')}: {err}", 8000) if err else None)
    elif not action.get("edit"):
        _status(win, f"{action.get('title', 'Action')}: nothing to apply")


def quick_actions(win, ed, line=None, col=None):
    if ed is None:
        return
    if line is None:
        line, col = ed.getCursorPosition()
    if _client(ed) is None:
        menu = QMenu(win)
        menu.addAction("Rename...", lambda: rename_symbol(win, ed, line, col))
        menu.addAction("Find All References", lambda: find_references(win, ed, line, col))
        _caret_global(ed, lambda p: menu.exec(p))
        return

    def got(actions, err):
        menu = QMenu(win)
        win._refactor_menu = menu
        groups = {"quickfix": [], "refactor": [], "source": [], "": []}
        for a in actions:
            kind = a.get("kind", "") if isinstance(a, dict) else ""
            key = next((k for k in ("quickfix", "refactor", "source") if kind.startswith(k)), "")
            groups[key].append(a)
        titles = {"quickfix": "Quick Fixes", "refactor": "Refactorings", "source": "Source Actions", "": "Actions"}
        any_ = False
        for key in ("quickfix", "refactor", "source", ""):
            if not groups[key]:
                continue
            if any_:
                menu.addSeparator()
            sec = menu.addAction(titles[key])
            sec.setEnabled(False)
            for a in groups[key]:
                act = menu.addAction(("★ " if a.get("isPreferred") else "    ") + a.get("title", "?"))
                if a.get("disabled"):
                    act.setEnabled(False)
                    act.setToolTip(a["disabled"].get("reason", ""))
                act.triggered.connect(lambda _=False, a=a: run_code_action(win, ed, a))
            any_ = True
        if any_:
            menu.addSeparator()
        menu.addAction("Rename Symbol...\tF2", lambda: rename_symbol(win, ed, line, col))
        menu.addAction("Find All References\tShift+F12", lambda: find_references(win, ed, line, col))
        if not actions:
            _status(win, err or "No quick fixes or refactorings here (select code to extract it)")
        _caret_global(ed, lambda p: menu.exec(p) if not getattr(win, "_refactor_no_exec", False) else None)
    request_code_actions(win, ed, line, col, got)


def extract(win, ed, what: str, name: str | None = None):
    """what: "method" | "variable" (pylsp-rope, typescript-language-server, rust-analyzer ...)."""
    if ed is None:
        return
    line, col = ed.getCursorPosition()
    l1, c1, l2, c2 = _selection(ed, line, col)
    if (l1, c1) == (l2, c2):
        _status(win, f"Extract {what}: select the code to extract first")
        return
    if _client(ed) is None:
        _status(win, f"Extract {what} needs a language server for {ed.language_id() if hasattr(ed, 'language_id') else 'this language'}")
        return
    words = {"method": ("method", "function"), "variable": ("variable", "constant", "local")}[what]

    def got(actions, err):
        cands = [a for a in actions if isinstance(a, dict) and any(w in a.get("title", "").lower() for w in words)
                 and "similar" not in a.get("title", "").lower() and "global" not in a.get("title", "").lower()]
        if not cands:
            _status(win, f"Extract {what}: the language server offers nothing here" + (f" ({err})" if err else ""))
            return
        new = name
        if new is None:
            new, ok = QInputDialog.getText(win, f"Extract {what.title()}", f"Name of the new {what}:",
                                           text="new_" + what if what == "variable" else "new_function")
            if not ok or not new.strip():
                return
            new = new.strip()
        before = ed.text()

        def after():
            _rename_generated(win, ed, before, new)
        run_code_action(win, ed, cands[0], after)
    request_code_actions(win, ed, line, col, got, only=["refactor.extract"])


def _rename_generated(win, ed, before: str, new: str):
    """After an extract: rename the server's default name (extracted_method, newFunction ...) to *new*."""
    text = ed.text()
    if text == before:
        return
    old_words = set(WORD.findall(before))
    for cand in [*DEFAULT_EXTRACT_NAMES, *sorted(set(WORD.findall(text)) - old_words)]:
        if cand in old_words or cand == new:
            continue
        m = re.search(rf"\b{re.escape(cand)}\b", text)
        if not m:
            continue
        ln = text.count("\n", 0, m.start())
        cl = m.start() - (text.rfind("\n", 0, m.start()) + 1)
        rename_symbol(win, ed, ln, cl, new_name=new, preview=False)
        return


def _apply_edit_request(win):
    """workspace/applyEdit from a server (executeCommand of a refactoring)."""
    def handler(_client_obj, params):
        edit = (params or {}).get("edit") or {}
        changes = editkit.workspace_changes(edit)
        done = editkit.apply_workspace_edit(win, edit, changes)
        after = getattr(win, "_refactor_after_edit", None)
        win._refactor_after_edit = None
        if after:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, after)
        _status(win, f"{(params or {}).get('label') or 'Refactoring'}: {len(done)} file(s) changed")
        return {"applied": True}
    return handler


# ============================================================================ references
class ReferencesPanel(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self.title = QLabel("Find All References: put the cursor on a name and press Shift+F12")
        row.addWidget(self.title, 1)
        clear = QPushButton("Clear")
        clear.clicked.connect(lambda: (self.tree.clear(), self.title.setText("Find All References")))
        row.addWidget(clear)
        lay.addLayout(row)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Code", "File", "Line"])
        self.tree.setColumnWidth(0, 520)
        self.tree.setColumnWidth(1, 220)
        self.tree.itemActivated.connect(self._go)
        lay.addWidget(self.tree, 1)

    def show_refs(self, name: str, locs: list[tuple[str, int, int]], how: str = ""):
        self.tree.clear()
        files: dict[str, list] = {}
        for p, ln, col in locs:
            files.setdefault(p, []).append((ln, col))
        root = getattr(getattr(self.win, "project", None), "folder", None)
        for p, items in sorted(files.items()):
            text = editkit.file_text(self.win, p).split("\n")
            try:
                shown = os.path.relpath(p, root) if root else p
            except ValueError:
                shown = p
            fi = QTreeWidgetItem(self.tree, [f"{shown} ({len(items)})", "", ""])
            f = fi.font(0)
            f.setBold(True)
            fi.setFont(0, f)
            fi.setExpanded(True)
            for ln, col in sorted(items):
                code = text[ln].strip() if ln < len(text) else ""
                ci = QTreeWidgetItem(fi, [code, Path(p).name, str(ln + 1)])
                ci.setData(0, Qt.ItemDataRole.UserRole, (p, ln, col))
        self.title.setText(f"<b>'{name}'</b>: {len(locs)} reference(s) in {len(files)} file(s){how}")

    def _go(self, item, _col=0):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            open_location(self.win, data[0], data[1], data[2])


def _panel(win) -> ReferencesPanel:
    dock = getattr(win, "dock_references", None)
    if dock is None:
        panel = ReferencesPanel(win)
        dock = QDockWidget("Find All References", win)
        dock.setObjectName("FindAllReferences")
        dock.setWidget(panel)
        win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        try:
            win.tabifyDockWidget(win.dock_output, dock)
        except Exception:  # noqa: BLE001
            pass
        win.dock_references = dock
        win.references_panel = panel
    dock.show()
    dock.raise_()
    return dock.widget()


def find_references(win, ed, line=None, col=None):
    if ed is None:
        return
    if line is None:
        line, col = ed.getCursorPosition()
    name, c1, _c2 = word_at(ed.text(), line, col)
    if not name:
        _status(win, "Find All References: put the cursor on a name first")
        return
    if _client(ed) is None:
        plugin = getattr(ed, "plugin", None)
        try:                   # the plugin's own references (Ring: comments and strings skipped)
            own = plugin.references(ed.text(), line, c1, Path(str(ed.path)), getattr(ed, "names", None)) \
                if plugin is not None and hasattr(plugin, "references") else None
        except Exception:  # noqa: BLE001
            own = None
        if own is not None:
            _panel(win).show_refs(name, own)
            return
        _panel(win).show_refs(name, _text_refs(win, ed, name), " (text search: no language server)")
        return

    def got(res, err):
        if res is None:
            _status(win, f"References: {err or 'none'}")
            _panel(win).show_refs(name, _text_refs(win, ed, name), " (text search)")
            return
        locs = []
        for loc in res:
            r = loc.get("range", {}).get("start", {})
            locs.append((editkit.uri_path(loc.get("uri", "")), r.get("line", 0), r.get("character", 0)))
        _panel(win).show_refs(name, locs)
    _request(ed, "textDocument/references", {**_pos(ed, line, c1), "context": {"includeDeclaration": True}}, got)


def _text_refs(win, ed, name):
    flags = re.I if Path(str(ed.path)).suffix.lower() in (".bas", ".ring", ".frm", ".cls") else 0
    rx = re.compile(rf"(?<![\w]){re.escape(name)}(?![\w])", flags)
    files = []
    folder = getattr(getattr(win, "project", None), "folder", None)
    if folder is not None:
        for dirpath, dirs, fns in os.walk(folder):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__",
                                                                           "bin", "obj", "target", "build")]
            files += [Path(dirpath) / f for f in fns if Path(f).suffix.lower() in CODE_EXT]
            if len(files) > 2000:
                break
    else:
        files = [Path(ed.path)]
    out = []
    for f in files:
        for n, s in enumerate(editkit.file_text(win, f).split("\n")):
            for m in rx.finditer(s):
                out.append((str(f), n, m.start()))
    return out


# ============================================================================ install
def _current_editor(win):
    try:
        cv = win._current_code()
    except Exception:  # noqa: BLE001
        cv = None
    if cv is not None and getattr(cv, "editor", None) is not None:
        return cv.editor
    w = win.tabs.currentWidget() if getattr(win, "tabs", None) is not None else None
    return getattr(w, "editor", None)


def install(win) -> None:
    editkit.install_monaco()
    try:
        from ..lsp import LspClient
        LspClient.request_handlers["workspace/applyEdit"] = _apply_edit_request(win)
    except ImportError:
        pass
    editkit.COMMANDS["rename"] = lambda ed, l, c: rename_symbol(win, ed, l, c)
    editkit.COMMANDS["codeActions"] = lambda ed, l, c: quick_actions(win, ed, l, c)
    editkit.COMMANDS["references"] = lambda ed, l, c: find_references(win, ed, l, c)
    editkit.COMMANDS["extractMethod"] = lambda ed, l, c: extract(win, ed, "method")
    editkit.COMMANDS["extractVariable"] = lambda ed, l, c: extract(win, ed, "variable")
    K = "monaco.KeyMod"
    editkit.add_action("radx.rename", "Rename Symbol...", "[monaco.KeyCode.F2]", "rename", "1_modification")
    editkit.add_action("radx.quickActions", "Quick Actions and Refactorings...",
                       f"[{K}.CtrlCmd | monaco.KeyCode.Period]", "codeActions", "1_modification")
    editkit.add_action("radx.references", "Find All References", f"[{K}.Shift | monaco.KeyCode.F12]",
                       "references", "navigation")
    editkit.add_action("radx.extractMethod", "Extract Method...", f"[{K}.CtrlCmd | {K}.Shift | monaco.KeyCode.KeyM]",
                       "extractMethod", "1_modification")
    editkit.add_action("radx.extractVariable", "Extract Variable...", "[]", "extractVariable", "1_modification")

    edit = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Edit"), None)
    if edit is not None:
        sub = edit.addMenu("Re&factor")
        win.refactor_menu = sub
        for text, fn in (("&Rename...\tF2", lambda: rename_symbol(win, _current_editor(win))),
                         ("&Quick Actions and Refactorings...\tCtrl+.", lambda: quick_actions(win, _current_editor(win))),
                         (None, None),
                         ("Extract &Method...\tCtrl+Shift+M", lambda: extract(win, _current_editor(win), "method")),
                         ("Extract &Variable...", lambda: extract(win, _current_editor(win), "variable")),
                         (None, None),
                         ("Find All &References\tShift+F12", lambda: find_references(win, _current_editor(win)))):
            if text is None:
                sub.addSeparator()
            else:
                a = QAction(text, win)
                a.triggered.connect(fn)
                sub.addAction(a)
    view = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "View"), None)
    if view is not None:
        view.addAction("Find All References Window", lambda: _panel(win))

    # editor right-click menu: Rename / Quick Actions / References (built-in and Monaco editors)
    def on_menu(menu, ed):
        first = menu.actions()[0] if menu.actions() else None
        acts = [QAction("Rename...\tF2", menu), QAction("Quick Actions and Refactorings...\tCtrl+.", menu),
                QAction("Find All References\tShift+F12", menu)]
        acts[0].triggered.connect(lambda: rename_symbol(win, ed))
        acts[1].triggered.connect(lambda: quick_actions(win, ed))
        acts[2].triggered.connect(lambda: find_references(win, ed))
        for a in acts:
            menu.insertAction(first, a)
        menu.insertSeparator(first)
    editkit.READY.append(lambda ed: ed.contextMenuAboutToShow.connect(lambda m, e=ed: on_menu(m, e))
                         if ed.window() is win else None)


__all__ = ["rename_symbol", "quick_actions", "extract", "find_references", "ChangesPreview", "ReferencesPanel",
           "preview_and_apply", "open_location"]
