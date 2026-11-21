"""The editor's project-context bar like Visual Studio's navigation bar (Qt; the no-Qt model is context.ProjectContext).

When a C# / VB file belongs to a Shared Project (compiled by every consuming project) or to a multi-targeted
project, a combo above the editor picks the context - "WinApp (net8.0-windows)", "FxConsole (net48)",
"MyLib (netstandard2.0)" ... - and the code that the selected context does not compile (#if / #elif / #else /
#endif with that context's DefineConstants for the active solution configuration) is greyed out, in both
editors (Monaco and the built-in one). A VS project's own files with #if blocks are greyed for their single
context too (no combo then, like VS).

``CONTEXT_HOOKS``: callables(editor, context, symbols) run when the context changes (e.g. to pass the context
to a language server that supports project contexts).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor, QTextCursor
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QTextEdit, QWidget

from . import context as CX
from . import model as SH
from .context import ProjectContext
from . import preprocessor as PP

CONTEXT_HOOKS: list = []
INACTIVE_COLOR = "#9a9a9a"


def _norm(p) -> str:
    return os.path.normcase(str(Path(p).resolve()))


def _vs_solution(win):
    try:
        from ...foreign.vs_solution import VsSolution
    except ImportError:
        return None
    return win.sln if isinstance(getattr(win, "sln", None), VsSolution) else None


def shared_projects(win) -> list:
    """Shared projects of the open .sln/.slnx (cached per solution; ui.refresh clears the cache)."""
    sln = _vs_solution(win)
    if sln is None or sln.model is None:
        return []
    cached = getattr(win, "_dotnet_shared", None)
    if cached is not None and getattr(win, "_dotnet_shared_sln", None) is sln:
        return cached
    try:
        found = SH.solution_shared_projects(sln.model)
    except (OSError, ValueError):
        found = []
    win._dotnet_shared, win._dotnet_shared_sln = found, sln
    return found


def contexts_for_file(win, path) -> list[ProjectContext]:
    """Project contexts of a file of the open Visual Studio solution ([] when none applies)."""
    sln = _vs_solution(win)
    return CX.solution_contexts(sln, path, shared_projects(win)) if sln is not None else []


# ============================================================================ greying
def _extra_selection_patch(editor) -> None:
    """The built-in editor rebuilds its extra selections (caret line, braces) itself: append ours."""
    if getattr(editor, "_rad_inactive_patched", False):
        return
    orig = editor.setExtraSelections

    def patched(sels, _orig=orig, _ed=editor):
        _orig(list(sels) + list(getattr(_ed, "_rad_inactive_sels", [])))
    editor.setExtraSelections = patched
    editor._rad_inactive_patched = True


def grey_out(editor, ranges: list[tuple[int, int]]) -> None:
    """Show *ranges* (0-based inclusive lines) of *editor* as inactive code."""
    editor._rad_inactive_ranges = list(ranges)
    if hasattr(editor, "_js"):                       # Monaco
        decos = [[a + 1, b + 1] for a, b in ranges]
        editor._js("(function(){var ed=window.radEditor;if(!ed||!window.monaco)return;"
                   "if(!document.getElementById('radInactiveCss')){var s=document.createElement('style');"
                   "s.id='radInactiveCss';s.textContent='.radInactiveCode{opacity:0.45 !important}';"
                   "document.head.appendChild(s);}"
                   f"var R={json.dumps(decos)};"
                   "window._radInactive=ed.deltaDecorations(window._radInactive||[],R.map(function(d){"
                   "return {range:new monaco.Range(d[0],1,d[1],1),"
                   "options:{isWholeLine:true,inlineClassName:'radInactiveCode',"
                   "hoverMessage:{value:'Inactive in this project context'}}};}));})();")
        return
    if not hasattr(editor, "setExtraSelections") or not hasattr(editor, "document"):
        return
    _extra_selection_patch(editor)
    sels = []
    doc = editor.document()
    for a, b in ranges:
        first, last = doc.findBlockByNumber(a), doc.findBlockByNumber(b)
        if not first.isValid():
            continue
        c = QTextCursor(first)
        if last.isValid():
            c.setPosition(last.position() + max(0, last.length() - 1), QTextCursor.MoveMode.KeepAnchor)
        else:
            c.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        s = QTextEdit.ExtraSelection()
        s.format.setForeground(QColor(INACTIVE_COLOR))
        s.cursor = c
        sels.append(s)
    editor._rad_inactive_sels = sels
    refresh = getattr(editor, "_highlight_current", None)
    if callable(refresh):
        refresh()
    else:
        editor.setExtraSelections([])


# ============================================================================ the bar
class ContextBar(QWidget):
    """The project-context combo shown above an editor."""

    def __init__(self, view, editor, path: Path):
        super().__init__(view)
        self.setObjectName("projectContextBar")
        self.view, self.editor, self.path = view, editor, Path(path)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 1, 2, 1)
        lay.setSpacing(4)
        self.icon = QLabel("⧉")          # two joined squares: the shared-project glyph
        self.icon.setToolTip("Project context")
        self.combo = QComboBox()
        self.combo.setObjectName("projectContextCombo")
        self.combo.setToolTip("Project context: the project (and target framework) that the editor uses for "
                              "IntelliSense and for greying out inactive #if code")
        self.combo.setMinimumContentsLength(24)
        self.combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.symbols_label = QLabel("")
        self.symbols_label.setStyleSheet("color: gray")
        lay.addWidget(self.icon)
        lay.addWidget(self.combo)
        lay.addWidget(self.symbols_label, 1)
        self.contexts: list[ProjectContext] = []


_CHOICES: dict[str, str] = {}        # file -> last chosen context label (per IDE session)


def current_context(view) -> ProjectContext | None:
    st = getattr(view, "_rad_ctx_state", None)
    if not st or not st["contexts"]:
        return None
    return st["contexts"][min(st["index"], len(st["contexts"]) - 1)]


def apply_context(view, index: int | None = None) -> list[tuple[int, int]]:
    """Grey the editor of *view* for its selected (or *index*) context; returns the inactive ranges."""
    st = getattr(view, "_rad_ctx_state", None)
    if not st or not st["contexts"]:
        return []
    if index is not None:
        st["index"] = max(0, min(index, len(st["contexts"]) - 1))
        _CHOICES[_norm(view.path)] = st["contexts"][st["index"]].label
    ctx = st["contexts"][st["index"]]
    try:
        syms = ctx.symbols()
    except Exception:  # noqa: BLE001 - an odd project file: no greying
        syms = {}
    ctx.active_symbols = list(syms.keys()) if isinstance(syms, dict) else list(syms)
    editor = view.editor
    try:
        text = editor.text()
    except Exception:  # noqa: BLE001
        text = ""
    ranges = PP.inactive_ranges(text, syms, ctx.language) if PP.has_conditionals(text) else []
    grey_out(editor, ranges)
    bar = st.get("bar")
    if bar is not None:
        shown = [s for s in ctx.active_symbols if s not in ("CONFIG", "PLATFORM", "_MyType") and
                 not s.endswith("_OR_GREATER")][:8]
        bar.symbols_label.setText("  " + ", ".join(shown))
        bar.symbols_label.setToolTip("Preprocessor symbols of this context:\n" + ", ".join(ctx.active_symbols))
        if bar.combo.currentIndex() != st["index"]:
            bar.combo.blockSignals(True)
            bar.combo.setCurrentIndex(st["index"])
            bar.combo.blockSignals(False)
    for hook in list(CONTEXT_HOOKS):
        try:
            hook(editor, ctx, syms)
        except Exception as e:  # noqa: BLE001
            print(f"[project context] hook failed: {e}")
    return ranges


def attach(win, view) -> bool:
    """Give *view* (an editor tab: has .editor and .path) its project context. True when it has one."""
    editor = getattr(view, "editor", None)
    path = getattr(view, "path", None)
    if editor is None or path is None:
        return False
    try:
        ctxs = contexts_for_file(win, path)
    except Exception as e:  # noqa: BLE001
        print(f"[project context] {e}")
        ctxs = []
    st = getattr(view, "_rad_ctx_state", None)
    if not ctxs:
        if st and st.get("bar") is not None:
            st["bar"].hide()
        return False
    labels = [c.label for c in ctxs]
    want = _CHOICES.get(_norm(path))
    index = labels.index(want) if want in labels else (st["index"] if st and st["index"] < len(ctxs) else 0)
    needs_bar = len(ctxs) > 1 or ctxs[0].shared is not None
    if st is None:
        st = {"contexts": ctxs, "index": index, "bar": None}
        view._rad_ctx_state = st
        timer = QTimer(view)
        timer.setSingleShot(True)
        timer.setInterval(400)
        timer.timeout.connect(lambda v=view: apply_context(v))
        st["timer"] = timer
        sig = getattr(editor, "textChanged", None) or getattr(editor, "textEdited", None)
        if sig is not None:
            try:
                sig.connect(timer.start)
            except (TypeError, RuntimeError):
                pass
    st["contexts"], st["index"] = ctxs, index
    bar = st.get("bar")
    if needs_bar and bar is None:
        lay = view.layout()
        if lay is not None and hasattr(lay, "insertWidget"):
            bar = ContextBar(view, editor, Path(path))
            lay.insertWidget(0, bar)
            bar.combo.currentIndexChanged.connect(lambda i, v=view: i >= 0 and apply_context(v, i))
            st["bar"] = bar
    if bar is not None:
        bar.setVisible(needs_bar)
        bar.combo.blockSignals(True)
        bar.combo.clear()
        for c in ctxs:
            bar.combo.addItem(c.label)
        bar.combo.setCurrentIndex(index)
        bar.combo.blockSignals(False)
        bar.contexts = ctxs
    apply_context(view)
    return True


def _safe_attach(win, w) -> None:
    try:
        attach(win, w)
    except RuntimeError:          # the tab was closed meanwhile
        pass


def install(win) -> None:
    if getattr(win, "_dotnet_ctx_installed", False):
        return
    win._dotnet_ctx_installed = True

    def on_tab(_i=None):
        w = win.tabs.currentWidget()
        if w is not None:
            QTimer.singleShot(0, lambda w=w: _safe_attach(win, w))
    try:
        win.tabs.currentChanged.connect(on_tab)
    except AttributeError:
        pass


def refresh_all(win) -> None:
    """Re-evaluate every open editor (after the configuration or the projects changed)."""
    tabs = getattr(win, "tabs", None)
    if tabs is None:
        return
    for i in range(tabs.count()):
        w = tabs.widget(i)
        if getattr(w, "_rad_ctx_state", None) is not None:
            _safe_attach(win, w)


__all__ = ["ProjectContext", "contexts_for_file", "attach", "apply_context", "current_context", "grey_out",
           "install", "refresh_all", "CONTEXT_HOOKS", "shared_projects"]
