"""IDE hooks for 3D scenes: ``.scene3d`` files open in the 3D scene view (radide/games3d/editor.py), Save All
saves them, F5 saves them first, and Project > "Add 3D Scene..." creates a new one.  Installed by
radide/features/games3d.py (wraps win.open_module / open_any_file / save_all / _any_modified like the 2D scene
designer in radide/features/game_designer.py).
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QInputDialog, QMessageBox

from .editor import Scene3DEditor
from .model import EXT, default_scene, safe_name


class Scenes3D:
    def __init__(self, win):
        self.win = win
        self.editors: dict[str, Scene3DEditor] = {}
        self._wrap()
        try:
            menu = next(a.menu() for a in win.menuBar().actions() if a.menu() is not None and
                        a.text().replace("&", "") == "Project")
            self.a_add = menu.addAction("Add 3D &Scene...", self.new_scene)
            self.a_add.setToolTip("Add a new .scene3d file to a 3D game project (Ursina / Godot 3D)")
            menu.aboutToShow.connect(lambda: self.a_add.setVisible(self.is_3d_project()))
        except StopIteration:
            self.a_add = None

    # ------------------------------------------------------------ helpers
    def is_3d_project(self) -> bool:
        p = self.win.project
        if p is None:
            return False
        try:
            from ..languages import get_plugin
            if getattr(get_plugin(p.language), "scene3d", False):
                return True
        except Exception:  # noqa: BLE001
            pass
        return any(str(m).lower().endswith(EXT) for m in getattr(p, "modules", []) or [])

    @staticmethod
    def _alive(ed) -> bool:
        try:
            ed.isVisible()
            return True
        except RuntimeError:
            return False

    def save_all(self) -> None:
        for ed in list(self.editors.values()):
            if self._alive(ed) and ed.is_modified():
                ed.save()

    # ------------------------------------------------------------ wrapping
    # DocumentProvider (radide/extension_points.py): File > Open, Solution Explorer, Save All, closing question
    def can_open(self, path: Path) -> bool:
        return Path(path).suffix.lower() == EXT

    def open_document(self, path: Path) -> Scene3DEditor | None:
        return self.open_scene(Path(path))

    def save_documents(self) -> None:
        self.save_all()

    def has_modified_documents(self) -> bool:
        return any(self._alive(e) and e.is_modified() for e in self.editors.values())

    def _wrap(self) -> None:
        win = self.win
        win.extension_points.add_document_provider(self)
        orig_run = getattr(win, "run_project", None)
        if callable(orig_run):
            def run_project(*a, **k):
                self.save_all()
                return orig_run(*a, **k)
            win.run_project = run_project
        win.open_scene3d = self.open_scene
        win.scenes3d = self

    # ------------------------------------------------------------ opening
    def open_scene(self, path: Path) -> Scene3DEditor | None:
        win = self.win
        path = Path(path).resolve()
        key = str(path).lower()
        ed = self.editors.get(key)
        if ed is not None and (not self._alive(ed) or win.tabs.indexOf(ed) < 0):
            self.editors.pop(key, None)
            ed = None
        if ed is None:
            try:
                ed = Scene3DEditor(path, log=win.log)
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(win, "3D Scene", f"Cannot open {path.name}:\n{e}")
                return None
            ed.setToolTip(str(path))
            ed.modifiedChanged.connect(lambda _m, e=ed: self._title(e))
            ed.saved.connect(lambda p: win.log(f"[3D scene] saved {Path(p).name} and regenerated its code"))
            self.editors[key] = ed
        win._show_tab(ed, path.name)
        self._title(ed)
        ed.view.setFocus()
        return ed

    def _title(self, ed) -> None:
        i = self.win.tabs.indexOf(ed)
        if i >= 0:
            self.win.tabs.setTabText(i, ed.path.name + ("*" if ed.is_modified() else ""))

    def new_scene(self) -> Scene3DEditor | None:
        win = self.win
        if win.project is None:
            return None
        name, ok = QInputDialog.getText(win, "Add 3D Scene", "Scene name:", text="Scene2")
        if not ok or not name.strip():
            return None
        name = safe_name(name.strip(), "Scene2")
        folder = Path(win.project.folder)
        path = folder / f"{name}{EXT}"
        if path.exists():
            QMessageBox.information(win, "Add 3D Scene", f"{path.name} already exists.")
            return self.open_scene(path)
        default_scene(name, "empty").save(path)
        if f"{name}{EXT}" not in win.project.modules:
            win.project.modules.append(f"{name}{EXT}")
            win.project.save()
        ed = self.open_scene(path)
        if ed is not None:
            ed.save()                      # writes the generated designer file / .tscn too
        try:
            win._fill_solution()
        except Exception:  # noqa: BLE001
            pass
        return ed


def install(win) -> Scenes3D:
    return Scenes3D(win)


__all__ = ["Scenes3D", "install"]
