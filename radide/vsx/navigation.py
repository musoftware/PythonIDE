"""VS Code's editor navigation history and "Reopen Closed Editor" for RAD IDE's editor tabs.

* History (workbench.action.navigateBack / navigateForward / navigateLast / navigateToLastEditLocation): a
  location (file, line) is recorded when another editor becomes active and when the cursor jumps more than
  ``JUMP`` lines inside one (VS Code's editorNavigationHistory records the same "significant" moves); going
  back / forward opens the file and puts the cursor there.
* Closed editors (workbench.action.reopenClosedEditor, Ctrl+Shift+T): the files of editor tabs that disappear
  are stacked; reopening opens the last one at its last line.
``install(win)`` (radide/vsx/host_ide.py) creates ``win.vsx_nav``. No Qt import at module level."""
from __future__ import annotations

from pathlib import Path

JUMP = 10
LIMIT = 50


def _tab_editor(w):
    ed = getattr(w, "editor", None)
    return ed if ed is not None and getattr(ed, "path", None) else None


class Navigation:
    def __init__(self, win):
        self.win = win
        self.back: list[tuple[str, int]] = []
        self.forward: list[tuple[str, int]] = []
        self.closed: list[tuple[str, int]] = []
        self.edits: list[tuple[str, int]] = []
        self._cur: tuple[str, int] | None = None
        self._moving = False
        self._open: dict[str, int] = {}

    # ------------------------------------------------------------------ recording
    def _here(self):
        tabs = getattr(self.win, "tabs", None)
        ed = _tab_editor(tabs.currentWidget()) if tabs is not None else None
        if ed is None:
            return None
        cur = getattr(ed, "_cursor", None)
        line = cur[0] if cur else 0
        return (str(Path(ed.path).resolve()), int(line))

    def note(self) -> None:
        """Current editor / cursor changed (tab switch, cursor event)."""
        here = self._here()
        if here is None:
            return
        self._open[here[0]] = here[1]
        if self._moving:
            self._cur = here
            return
        prev = self._cur
        if prev is not None and (prev[0] != here[0] or abs(prev[1] - here[1]) > JUMP):
            self.back.append(prev)
            del self.back[:-LIMIT]
            self.forward.clear()
        self._cur = here

    def note_edit(self) -> None:
        here = self._here()
        if here is not None and (not self.edits or self.edits[-1] != here):
            self.edits.append(here)
            del self.edits[:-LIMIT]

    def tabs_changed(self) -> None:
        """Files whose tabs are gone -> the closed-editor stack."""
        tabs = getattr(self.win, "tabs", None)
        if tabs is None:
            return
        now = set()
        for i in range(tabs.count()):
            ed = _tab_editor(tabs.widget(i))
            if ed is not None:
                try:
                    now.add(str(Path(ed.path).resolve()))
                except OSError:
                    pass
        for p in list(self._open):
            if p not in now:
                self.closed.append((p, self._open.pop(p)))
                del self.closed[:-LIMIT]
        for p in now:
            self._open.setdefault(p, 0)
        self.note()

    # ------------------------------------------------------------------ going places
    def go(self, loc) -> bool:
        if not loc:
            return False
        path, line = loc
        if not Path(path).is_file():
            return False
        self._moving = True
        try:
            from ..features.command_palette import open_path
            open_path(self.win, Path(path), line + 1)
        finally:
            self._moving = False
        self._cur = (path, line)
        return True

    def navigate_back(self) -> bool:
        here = self._here()
        while self.back:
            loc = self.back.pop()
            if here is not None:
                self.forward.append(here)
            if self.go(loc):
                return True
        return False

    def navigate_forward(self) -> bool:
        here = self._here()
        while self.forward:
            loc = self.forward.pop()
            if here is not None:
                self.back.append(here)
            if self.go(loc):
                return True
        return False

    def navigate_last(self) -> bool:
        if self.back:
            loc = self.back[-1]
            here = self._here()
            if here is not None:
                self.back.append(here)
            return self.go(loc)
        return False

    def last_edit(self) -> bool:
        return self.go(self.edits[-1]) if self.edits else False

    def reopen_closed(self) -> bool:
        while self.closed:
            if self.go(self.closed.pop()):
                return True
        return False


def install(win) -> Navigation:
    nav = Navigation(win)
    win.vsx_nav = nav
    tabs = getattr(win, "tabs", None)
    if tabs is not None:
        tabs.currentChanged.connect(lambda *_: nav.tabs_changed())
        try:
            tabs.tabBar().tabCloseRequested.connect(lambda *_: __import__("PyQt6.QtCore", fromlist=["QTimer"])
                                                    .QTimer.singleShot(0, nav.tabs_changed))
        except Exception:  # noqa: BLE001
            pass
    try:
        from .. import monaco_editor as ME
        ME.SELECTION_LISTENERS.append(lambda _ed: nav.note())
    except Exception:  # noqa: BLE001
        pass
    from PyQt6.QtCore import QTimer
    t = QTimer(win)
    t.setInterval(1000)
    t.timeout.connect(nav.tabs_changed)            # tabs closed programmatically (removeTab) too
    t.start()
    nav._timer = t
    return nav


__all__ = ["Navigation", "install"]
