"""Extension points of the main window: how a feature takes part in what the IDE does without replacing
MainWindow's methods.

The old way - ``orig = win.save_all; win.save_all = wrapper`` - built a hidden chain whose order was the
alphabetical order of the feature files, and one wrapper that forgot to call ``orig`` silently switched off
every wrapper below it. A feature now registers an object (or a function) here once, and MainWindow calls
the extension points at fixed places:

====================  =====================================  ==========================================
extension point       MainWindow calls it in                 replaces wrapping of
====================  =====================================  ==========================================
DocumentProvider      open_any_file, open_module, save_all,  open_any_file, open_module, save_all,
                      _any_modified                          _any_modified
save listener         save_all (at the end, always)          save_all (work after the save)
solution contributor  _fill_solution (after the tree)        _fill_solution
====================  =====================================  ==========================================

Order: providers are asked by **priority** (EDITOR, then BINARY_VIEWER, then FALLBACK), and within one
priority **latest registered first**, like the outermost wrapper used to be. A file's own editor (image
editor, text-mode designer ...) always wins over a viewer that takes any binary file (ROM workbench, hex
view) - that order used to be forced with QTimer.singleShot re-wrapping. Solution
contributors run in registration order (the order their wrappers added nodes). A provider that raises is
logged to the Output window and never stops the IDE or the other providers.
"""
from __future__ import annotations

import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class DocumentProvider(Protocol):
    """A feature with its own editor for some files (image editor, report designer, notebook ...)."""

    def can_open(self, path: Path) -> bool:
        """True when *path* is one of this editor's files (File > Open, Solution Explorer)."""

    def open_document(self, path: Path):
        """Open *path* (or bring its tab to the front) and return the editor widget, None when it failed."""

    def save_documents(self) -> bool | None:
        """Save every modified document of this editor (File > Save All). False = a save failed."""

    def has_modified_documents(self) -> bool:
        """True when a document of this editor has unsaved changes (the closing question)."""


_PROVIDER_METHODS = ("can_open", "open_document", "save_documents", "has_modified_documents")

# named events of the window's lifecycle: ExtensionPoints.on(name, fn) / MainWindow emits them
EVENTS = {
    "project_opening": "open_project(folder) starts, before anything is loaded - fn(folder: Path)",
    "project_opened": "open_project returned (also when it was cancelled or the folder is a foreign project)",
    "project_activated": "activate_project returned: self.project may be another project of the solution",
    "projects_reset": "_reset starts: the documents / state of the open solution are about to be dropped",
    "actions_updated": "_update_actions finished: features set the state of their own / the Edit commands",
    "designer_opening": "open_designer(name) starts - fn(name)",
    "designer_opened": "the designer of a form is open (not after a load error) - fn(name)",
    "form_opened": "open_designer / open_code succeeded - fn(name, newly_loaded: bool)",
    "form_load_failed": "a .form could not be loaded - fn(name, error); without a handler the error is raised",
    "form_saving": "_save_form(name) is about to write the form - fn(name)",
    "form_saved": "_save_form finished - fn(name, completed: bool) (False: it raised, e.g. disk full)",
    "project_saving": "_save_active_project is about to write the active project",
    "project_saved": "_save_active_project finished - fn(completed: bool)",
    "file_saved": "save_current (File > Save <file>) finished - fn(ok: bool)",
    "designer_menu": "the designer's right-click menu is built - fn(form_name, menu, control or None)",
    "editor_menu": "a code editor's right-click menu is built - fn(menu, form_name or None)",
    "code_view_requested": "_codeview(name) returned the code editor (new or cached) - fn(name, codeview)",
    "module_view_shown": "open_module showed a module editor - fn(filename, moduleview)",
    "title_updated": "_update_title finished",
    "layout_restored": "restoreState (the dock layout) was applied",
    "output_logged": "a line went to the Output window - fn(text); errors here go to stderr, not the Output",
}

EDITOR = 0            # the editor of a file type (.png, .rpt.json, .scene, .tform ...)
BINARY_VIEWER = -10   # a viewer for a family of binary files (ROM workbench: .nes, .gb, patches ...)
FALLBACK = -20        # takes whatever binary file nobody else wants (generic hex view)


class ExtensionPoints:
    def __init__(self, log: Callable[[str], None] | None = None):
        self._log = log or print
        self._documents: list[tuple[int, DocumentProvider]] = []
        self._solution: list[tuple[str, Callable[[], None]]] = []
        self._after_save: list[tuple[str, Callable[[bool], None]]] = []
        self._before_save: list[tuple[str, Callable[[], None]]] = []
        self._close_guards: list[tuple[str, Callable[[], bool]]] = []
        self._shutdown: list[tuple[str, Callable[[], None]]] = []
        self._events: dict[str, list[tuple[str, Callable]]] = {name: [] for name in EVENTS}
        self._logged: set[tuple] = set()           # (handler, step, error) already in the Output window
        self._properties: list[tuple[str, Callable[[object], bool]]] = []

    # ------------------------------------------------------------ registration
    def add_document_provider(self, provider: DocumentProvider, priority: int = EDITOR) -> None:
        missing = [m for m in _PROVIDER_METHODS if not callable(getattr(provider, m, None))]
        if missing:
            raise TypeError(f"{type(provider).__name__} is not a DocumentProvider: missing {', '.join(missing)}")
        if all(p is not provider for _, p in self._documents):
            self._documents.append((priority, provider))

    def remove_document_provider(self, provider: DocumentProvider) -> None:
        self._documents = [(pr, p) for pr, p in self._documents if p is not provider]

    def document_providers(self) -> list[DocumentProvider]:
        """The order they are asked in: higher priority first, then latest registered first."""
        indexed = list(enumerate(self._documents))
        indexed.sort(key=lambda t: (-t[1][0], -t[0]))
        return [p for _, (_, p) in indexed]

    def add_solution_contributor(self, fn: Callable[[], None], name: str = "") -> None:
        """*fn()* adds nodes to Solution Explorer after MainWindow filled it (called on every refill)."""
        self._solution.append((name or getattr(fn, "__qualname__", "solution contributor"), fn))

    def add_save_listener(self, fn: Callable[[bool], None], name: str = "",
                          before: Callable[[], None] | None = None) -> None:
        """*fn(ok)* runs at the end of every File > Save All (the Save All command, Ctrl+S and every caller of
        MainWindow.save_all), also when the save failed (ok False) or there is no project - e.g. copy a runtime
        file into the projects that now need it, run the checks after a successful save. *before()* runs
        before anything is saved (e.g. remember the designer state to compare afterwards)."""
        label = name or getattr(fn, "__qualname__", "save listener")
        self._after_save.append((label, fn))
        if before is not None:
            self._before_save.append((label, before))

    def add_close_guard(self, fn: Callable[[], bool], name: str = "") -> None:
        """*fn()* is asked when the IDE is about to close, before the save question; False keeps the IDE
        open (e.g. "agent tasks are still running - stop them and close?"). The latest registered guard is
        asked first; the first False stops the close. A guard that raises is logged and does not block it."""
        self._close_guards.append((name or getattr(fn, "__qualname__", "close guard"), fn))

    def add_shutdown_step(self, fn: Callable[[], None], name: str = "") -> None:
        """*fn()* runs once the IDE has accepted to close (stop servers, save layout ...), in registration order."""
        self._shutdown.append((name or getattr(fn, "__qualname__", "shutdown step"), fn))

    def on(self, event: str, fn: Callable, name: str = "") -> None:
        """Run *fn* (with the event's arguments, see EVENTS) every time MainWindow emits *event*; handlers
        run in registration order and one that raises is logged. An unknown event name is a ValueError."""
        if event not in EVENTS:
            raise ValueError(f"unknown event '{event}' - one of: {', '.join(EVENTS)}")
        self._events[event].append((name or getattr(fn, "__qualname__", event), fn))

    def has_handlers(self, event: str) -> bool:
        return bool(self._events[event])

    def add_properties_dialog(self, fn: Callable[[object], bool], name: str = "") -> None:
        """*fn(project)* may show its own Project > Properties for that project and return True (a VB6 mirror
        project shows the VB6 dialog); False lets the next one / the window's dialog show. Latest first."""
        self._properties.append((name or getattr(fn, "__qualname__", "properties dialog"), fn))

    # ------------------------------------------------------------ what MainWindow calls
    def emit(self, event: str, *args) -> None:
        if event == "output_logged":            # its errors must not go back to the Output (endless loop)
            for _name, fn in self._events[event]:
                try:
                    fn(*args)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
            return
        self._run_all(self._events[event], event, *args)

    def show_properties(self, project) -> bool:
        """True when a feature showed its own Project > Properties for *project*."""
        for name, fn in reversed(self._properties):
            try:
                if fn(project):
                    return True
            except Exception:  # noqa: BLE001 - the window's own dialog still shows
                self._log(f"[{name}] properties dialog failed:\n{traceback.format_exc()}")
        return False

    def confirm_close(self) -> bool:
        for name, fn in reversed(self._close_guards):
            try:
                if fn() is False:
                    return False
            except Exception:  # noqa: BLE001 - a broken guard must not make the IDE impossible to close
                self._log(f"[{name}] close guard failed:\n{traceback.format_exc()}")
        return True

    def shutdown(self) -> None:
        self._run_all(self._shutdown, "shutdown")

    def open_document(self, path: Path) -> tuple[bool, object]:
        """(True, editor) when a provider took *path*; (False, None) when it is nobody's."""
        for p in self.document_providers():
            try:
                if not p.can_open(path):
                    continue
            except Exception:  # noqa: BLE001 - a broken provider must not stop File > Open of other files
                self._report(p, "can_open")
                continue
            try:
                return True, p.open_document(Path(path))
            except Exception:  # noqa: BLE001 - its file: nobody else should open it in a wrong editor
                self._report(p, "open_document")
                return True, None
        return False, None

    def save_documents(self) -> bool:
        """Save All of every provider. False when one of them failed (the caller keeps the IDE open)."""
        ok = True
        for p in self.document_providers():
            try:
                if p.save_documents() is False:
                    ok = False
            except Exception:  # noqa: BLE001
                self._report(p, "save_documents")
                ok = False
        return ok

    def any_modified(self) -> bool:
        for p in self.document_providers():
            try:
                if p.has_modified_documents():
                    return True
            except Exception:  # noqa: BLE001
                self._report(p, "has_modified_documents")
        return False

    def fill_solution(self) -> None:
        self._run_all(self._solution, "Solution Explorer nodes")    # one feature must not empty the tree

    def before_save_all(self) -> None:
        self._run_all(self._before_save, "before Save All")

    def after_save_all(self, ok: bool) -> None:
        self._run_all(self._after_save, "after Save All", ok)

    def _run_all(self, fns: list, what: str, *args) -> None:
        for name, fn in fns:
            try:
                fn(*args)
            except Exception as e:  # noqa: BLE001 - logged; the other features still run
                key = (name, what, type(e).__name__, str(e))
                if key in self._logged:           # actions_updated runs very often: the same error once
                    continue
                self._logged.add(key)
                self._log(f"[{name}] {what} failed:\n{traceback.format_exc()}")

    def _report(self, provider, method: str) -> None:
        self._log(f"[{type(provider).__name__}.{method}] failed:\n{traceback.format_exc()}")
