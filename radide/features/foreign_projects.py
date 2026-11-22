"""File > Open dispatcher for FOREIGN project formats (projects of other IDEs,
opened in place - the native files stay authoritative, no project.radproj is
written into the user's folder).

Registry API (used by every foreign adapter, see radide/foreign/*):

    from radide.features.foreign_projects import register_format
    register_format([".vbp"], opener, "Visual Basic 6 project",
                    folder_probe=None, name="vb6")

* ``extensions``   - iterable of lower-case suffixes (".sln") or exact file
                     names ("CMakeLists.txt", "pom.xml").
* ``opener``       - ``opener(win, path: Path) -> bool``; returns True when the
                     project was opened (False/None = declined, next format).
* ``description``  - text for the File > Open filter and the dialogs.
* ``folder_probe`` - optional ``probe(folder: Path) -> Path | None``: when the
                     user opens a FOLDER, the probe may return the native
                     project file inside it (then ``opener`` is called with it).
* ``priority``     - higher wins when several formats claim the same file.

``open_foreign(win, path)`` dispatches a file or folder; ``file_filter()``
returns a Qt file-dialog filter with every registered format.

Hooks for foreign projects (all optional, looked up with getattr):
* ``project.fill_solution_tree(win, project_item, name)`` - draw the project's own Solution
  Explorer subtree (radide/features/solution_ui.py ``_fill_project``).
* ``project.build_solution_menu(win, item, kind, name)`` / ``solution.build_solution_menu(...)``
  -> QMenu or None - the Solution Explorer context menu.
* tree items whose kind starts with "foreign" are activated through
  ``project.on_tree_activate(win, item, kind, name)`` (see ``on_tree_activate`` below).
* ``solution.build_solution(win, only=None, wait=False)`` - Build > Build Solution.
* ``solution.editor_for_file(win, file)`` -> editor or None - MainWindow._editor_for_file.
* ``plugin.make_session(win, spec, debug)`` - Run/Debug (MainWindow._make_session).
* ``register_form_binding(kind, factory)`` - native form files in the designer (see below)."""
from __future__ import annotations

import contextlib
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass
class ForeignFormat:
    name: str
    extensions: tuple
    opener: Callable
    description: str
    folder_probe: Optional[Callable] = None
    priority: int = 0
    extra: dict = field(default_factory=dict)

    def matches(self, path: Path) -> bool:
        low = path.name.lower()
        for ext in self.extensions:
            e = ext.lower()
            if e.startswith("."):
                if low.endswith(e):
                    return True
            elif low == e:
                return True
        return False


_FORMATS: list[ForeignFormat] = []


def register_format(extensions, opener, description: str = "", *,
                    folder_probe=None, priority: int = 0, name: str = "", **extra) -> ForeignFormat:
    """Register (or replace, same name) a foreign project format."""
    if isinstance(extensions, str):
        extensions = [extensions]
    exts = tuple(str(e).lower() if str(e).startswith(".") else str(e) for e in extensions)
    nm = name or (exts[0] if exts else description) or "format"
    fmt = ForeignFormat(nm, exts, opener, description or nm, folder_probe, priority, dict(extra))
    for i, f in enumerate(_FORMATS):
        if f.name == nm:
            _FORMATS[i] = fmt
            break
    else:
        _FORMATS.append(fmt)
    _FORMATS.sort(key=lambda f: -f.priority)
    return fmt


def unregister_format(name: str) -> None:
    _FORMATS[:] = [f for f in _FORMATS if f.name != name]


def formats() -> list[ForeignFormat]:
    _ensure_builtin()
    return list(_FORMATS)


def find_format(path) -> Optional[ForeignFormat]:
    _ensure_builtin()
    p = Path(path)
    for f in _FORMATS:
        if f.matches(p):
            return f
    return None


def probe_folder(folder) -> Optional[tuple]:
    """(format, project file) for a folder holding a foreign project, else None.
    A folder that already is a RAD IDE project (project.radproj / .radsln) is
    never claimed."""
    _ensure_builtin()
    folder = Path(folder)
    try:
        if (folder / "project.radproj").exists() or any(folder.glob("*.radsln")):
            return None
    except OSError:
        return None
    for f in _FORMATS:
        if f.folder_probe is None:
            continue
        try:
            hit = f.folder_probe(folder)
        except Exception:  # noqa: BLE001 - a broken probe must not stop the others
            traceback.print_exc()
            hit = None
        if hit:
            return f, Path(hit)
    return None


def is_foreign(path) -> bool:
    p = Path(path)
    if p.is_dir():
        return probe_folder(p) is not None
    return find_format(p) is not None


def open_foreign(win, path, ask: bool = True) -> bool:
    """Open a foreign project file (or a folder containing one) in place. *ask* = False: do not
    ask to save the open solution first (File > Recent, tests)."""
    _ensure_builtin()
    p = Path(path)
    cands: list = []
    if p.is_dir():
        hit = probe_folder(p)
        if hit:
            cands = [hit]
    else:
        cands = [(f, p) for f in _FORMATS if f.matches(p)]
    skip = (win.no_save_questions() if not ask and callable(getattr(win, "no_save_questions", None))
            else contextlib.nullcontext())              # opened without asking: no "Save changes?" either
    with skip:
        for fmt, target in cands:
            try:
                if fmt.opener(win, target):
                    return True
            except Exception:  # noqa: BLE001
                msg = f"[foreign:{fmt.name}] failed to open {target}:\n{traceback.format_exc()}"
                try:
                    win.log(msg)
                except Exception:  # noqa: BLE001
                    print(msg)
    return False


def file_filter(patterns_only: bool = False) -> str:
    """Qt filter string: 'All foreign projects (...);;<desc> (*.ext);;...'.
    *patterns_only*: just the space-separated patterns of every registered format."""
    _ensure_builtin()
    parts, allpat = [], []
    for f in _FORMATS:
        pats = " ".join(("*" + e) if e.startswith(".") else e for e in f.extensions)
        if not pats:
            continue
        parts.append(f"{f.description} ({pats})")
        allpat.append(pats)
    if patterns_only:
        return " ".join(allpat)
    head = f"All foreign projects ({' '.join(allpat)})" if allpat else ""
    return ";;".join([x for x in [head, *parts, "All files (*)"] if x])


# ---------------------------------------------------------------- form bindings
# A foreign project that finds a native form (WinForms Form1.cs + Form1.Designer.cs, a VB6 .frm,
# a Delphi .dfm ...) asks the registry for a binding: an object with the FormBinding interface of
# radide/foreign/_others_base.py (load() -> Form, write(form) -> notes, code_path, name, native).
#     register_form_binding("winforms-cs", factory)
#     factory(name: str, designer: Path, code: Path, project) -> binding | None
# kinds used by the Visual Studio adapter: "winforms-cs", "winforms-vb".
_FORM_BINDINGS: dict[str, Callable] = {}


def register_form_binding(kind: str, factory: Callable) -> None:
    _FORM_BINDINGS[kind] = factory


def form_binding(kind: str, name: str, designer: Path, code: Path, project=None):
    """A binding for a native form, or None when no adapter handles *kind* (or it declines)."""
    _ensure_builtin()
    f = _FORM_BINDINGS.get(kind)
    if f is None:
        return None
    try:
        return f(name, Path(designer), Path(code), project)
    except Exception:  # noqa: BLE001 - a broken binding: the files stay plain code files
        traceback.print_exc()
        return None


# ---------------------------------------------------------------- Solution Explorer hooks
def on_tree_activate(win, item, kind: str, name) -> None:
    """Double-click on a Solution Explorer item whose kind starts with "foreign" (called by
    MainWindow._on_solution_dclick). The project (or solution) that owns the item handles it:
    ``project.on_tree_activate(win, item, kind, name)``."""
    from .solution_ui import PROJECT_ROLE
    key = item.data(0, PROJECT_ROLE) if item is not None else None
    st = win._pstates.get(key) if key else None
    owner = st["project"] if st else win.sln
    handler = getattr(owner, "on_tree_activate", None) or getattr(win.sln, "on_tree_activate", None)
    if callable(handler):
        handler(win, item, kind, name)
    elif kind == "foreign_file" and name:
        win.open_any_file(Path(name))


# ---------------------------------------------------------------- built-ins
_BUILTIN_DONE = False


def _ensure_builtin() -> None:
    """Import the foreign adapters so they register themselves (each adapter
    module calls register_format at import time or exposes register())."""
    global _BUILTIN_DONE
    if _BUILTIN_DONE:
        return
    _BUILTIN_DONE = True
    import importlib
    import pkgutil
    try:
        from .. import foreign as pkg
    except Exception:  # noqa: BLE001
        return
    for mod in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda m: m.name):
        if mod.name.startswith("_"):
            continue
        try:
            m = importlib.import_module(f"{pkg.__name__}.{mod.name}")
            reg = getattr(m, "register", None)
            if callable(reg):
                reg()
        except Exception:  # noqa: BLE001
            traceback.print_exc()


def install(win) -> None:
    win._foreign_open = lambda path, ask=True: open_foreign(win, path, ask)
    try:                                      # Visual Studio: configuration / platform combos
        from ..foreign.vs_solution import install_ui
        install_ui(win)
    except Exception:  # noqa: BLE001
        win.log(f"[foreign projects] {traceback.format_exc()}")
    try:                                      # VB6 (.vbp) opened in place: write-back on save, VB6 tree
        from ..foreign.vb6_project import install_hooks
        install_hooks(win)
    except Exception:  # noqa: BLE001
        win.log(f"[foreign projects] {traceback.format_exc()}")
