"""Ring editor integration: the code outline in the Document Outline dock, and the Ring index warm-up.

The Document Outline dock (radide/features/doc_outline.py) shows the control tree of a form. When the current
tab is a code editor whose language plugin implements ``document_symbols`` (Ring: radide/languages/ring_intel.py
- packages, globals, functions, classes with their attributes and methods), the dock shows that outline instead;
a click jumps to the line. The outline follows the typing (refreshed 700 ms after the last edit).

The Ring IntelliSense index (radide/languages/ring_index.py) is read / built in a background thread at start-up
when a Ring project or file is opened, so the first completion list is instant.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QStackedWidget, QTreeWidget, QTreeWidgetItem

LINE_ROLE = Qt.ItemDataRole.UserRole
KIND_MARK = {"class": "C", "function": "f", "method": "m", "attribute": "a", "variable": "v", "constant": "K",
             "package": "P"}


def _symbols_of(ed) -> list[dict] | None:
    """The plugin's outline of the editor's text, or None when the plugin has none."""
    plugin = getattr(ed, "plugin", None)
    if plugin is None:
        return None
    fn = getattr(type(plugin), "document_symbols", None)
    if fn is None or getattr(fn, "__qualname__", "").split(".")[0] == "LanguagePlugin":
        return None
    try:
        return plugin.document_symbols(ed.text()) or []
    except Exception:  # noqa: BLE001 - the outline must never break the editor
        return []


class CodeOutline(QTreeWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.ed = None
        self.setHeaderHidden(True)
        self.setObjectName("CodeOutline")
        self.itemActivated.connect(self._jump)
        self.itemClicked.connect(self._jump)

    def show_symbols(self, ed, symbols: list[dict]) -> None:
        self.ed = ed
        expanded = {self.topLevelItem(i).text(0) for i in range(self.topLevelItemCount())
                    if self.topLevelItem(i).isExpanded()}
        first = self.topLevelItemCount() == 0
        self.clear()

        def add(parent, s):
            label = f"[{KIND_MARK.get(s.get('kind'), '?')}] {s.get('name')}"
            if s.get("detail"):
                label += f"  {s['detail']}"
            it = QTreeWidgetItem([label])
            it.setData(0, LINE_ROLE, int(s.get("line", 0)))
            it.setToolTip(0, f"{s.get('kind')} {s.get('name')} - line {int(s.get('line', 0)) + 1}")
            if parent is None:
                self.addTopLevelItem(it)
            else:
                parent.addChild(it)
            for k in s.get("children") or []:
                add(it, k)
            return it

        for s in symbols:
            it = add(None, s)
            if first or it.text(0) in expanded:
                it.setExpanded(True)

    def _jump(self, item, _col=0) -> None:
        if item is None or self.ed is None:
            return
        line = item.data(0, LINE_ROLE)
        if line is None:
            return
        try:
            self.ed.goto_line(int(line))
        except Exception:  # noqa: BLE001
            pass


def install(win) -> None:
    dock = getattr(win, "dock_outline", None)
    form_outline = getattr(win, "doc_outline", None)
    if dock is not None and form_outline is not None:
        _install_outline(win, dock, form_outline)
    _warm_up_later(win)


def _install_outline(win, dock, form_outline) -> None:
    stack = QStackedWidget()
    dock.setWidget(stack)            # re-parents the form outline into the stack
    stack.addWidget(form_outline)
    code = CodeOutline(win)
    stack.addWidget(code)
    win.code_outline = code
    timer = QTimer(win)
    timer.setSingleShot(True)
    timer.setInterval(700)
    state = {"ed": None}

    def current():
        from .editor_extras import current_editor
        try:
            return current_editor(win)
        except Exception:  # noqa: BLE001
            return None

    def refresh():
        ed = current()
        syms = _symbols_of(ed) if ed is not None else None
        if syms is None:
            stack.setCurrentWidget(form_outline)
            return
        code.show_symbols(ed, syms)
        stack.setCurrentWidget(code)

    def follow(*_):
        ed = current()
        if ed is not state["ed"]:
            old = state["ed"]
            if old is not None:
                try:
                    old.textEdited.disconnect(timer.start)
                except (TypeError, RuntimeError, AttributeError):
                    pass
            state["ed"] = ed
            if ed is not None and _symbols_of(ed) is not None:
                try:
                    ed.textEdited.connect(timer.start)
                except (TypeError, AttributeError):
                    pass
        refresh()

    timer.timeout.connect(refresh)
    win.tabs.currentChanged.connect(follow)
    win.refresh_code_outline = refresh
    follow()


def _warm_up_later(win) -> None:
    def go():
        try:
            proj = getattr(win, "project", None)
            lang = str(getattr(proj, "language", "") or "")
            if lang.startswith("ring"):
                from ..languages import ring_index
                if not ring_index.loaded():
                    ring_index.warm_up()
        except Exception:  # noqa: BLE001
            pass
    QTimer.singleShot(3000, go)
    try:
        sig = getattr(win, "projectOpened", None) or getattr(win, "projectChanged", None)
        if sig is not None:
            sig.connect(lambda *_: QTimer.singleShot(500, go))
    except Exception:  # noqa: BLE001
        pass
