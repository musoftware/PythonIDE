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

Order: providers are asked **latest registered first**, like the outermost wrapper used to be; solution
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


class ExtensionPoints:
    def __init__(self, log: Callable[[str], None] | None = None):
        self._log = log or print
        self._documents: list[DocumentProvider] = []
        self._solution: list[tuple[str, Callable[[], None]]] = []
        self._after_save: list[tuple[str, Callable[[], None]]] = []

    # ------------------------------------------------------------ registration
    def add_document_provider(self, provider: DocumentProvider) -> None:
        missing = [m for m in _PROVIDER_METHODS if not callable(getattr(provider, m, None))]
        if missing:
            raise TypeError(f"{type(provider).__name__} is not a DocumentProvider: missing {', '.join(missing)}")
        if provider not in self._documents:
            self._documents.append(provider)

    def remove_document_provider(self, provider: DocumentProvider) -> None:
        if provider in self._documents:
            self._documents.remove(provider)

    def document_providers(self) -> list[DocumentProvider]:
        """Latest registered first (the order they are asked in)."""
        return list(reversed(self._documents))

    def add_solution_contributor(self, fn: Callable[[], None], name: str = "") -> None:
        """*fn()* adds nodes to Solution Explorer after MainWindow filled it (called on every refill)."""
        self._solution.append((name or getattr(fn, "__qualname__", "solution contributor"), fn))

    def add_save_listener(self, fn: Callable[[], None], name: str = "") -> None:
        """*fn()* runs at the end of every File > Save All, also when the save failed or there is no project
        (e.g. copy a runtime file into the projects that now need it)."""
        self._after_save.append((name or getattr(fn, "__qualname__", "save listener"), fn))

    # ------------------------------------------------------------ what MainWindow calls
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

    def after_save_all(self) -> None:
        self._run_all(self._after_save, "after Save All")

    def _run_all(self, fns: list[tuple[str, Callable[[], None]]], what: str) -> None:
        for name, fn in fns:
            try:
                fn()
            except Exception:  # noqa: BLE001 - logged; the other features still run
                self._log(f"[{name}] {what} failed:\n{traceback.format_exc()}")

    def _report(self, provider, method: str) -> None:
        self._log(f"[{type(provider).__name__}.{method}] failed:\n{traceback.format_exc()}")
