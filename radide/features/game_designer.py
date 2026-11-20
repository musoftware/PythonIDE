"""Scene designer for game projects (CONTRACTS 10.2 / 10.4) - the IDE side.

* `.scene` files of game projects (plugins with `is_game = True`, e.g. pygame / godot) open in the
  scene designer tab (radide/games/scene_editor.py) - from the Solution Explorer ("Scenes" under the
  project), File > Open File, or the Game menu.
* Game menu: New Scene, Open Scene, Play (F5), Import Tileset, Sprite Sheet / Animations, Game Assets.
* "Game Assets" dock (images with thumbnails, sprite sheets, tilesets, sounds with Play).
* Double-click a sprite -> its handler in <Scene>.py opens in the code editor (VB style);
  Save / Save All / F5 save the scenes; Edit > Undo/Redo/Cut/Copy/Paste/Delete work in the designer.
"""
from __future__ import annotations

import re
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QDockWidget, QInputDialog, QLineEdit, QMessageBox, QPlainTextEdit, \
    QTreeWidgetItem

from ..games.asset_browser import AssetBrowser
from ..games.scene_editor import SceneEditor

ROLE = Qt.ItemDataRole.UserRole


# ====================================================================== helpers
def _plugin_of(win, project=None):
    project = project or win.project
    if project is None:
        return None
    try:
        return win._state_for(project)["plugin"]
    except Exception:  # noqa: BLE001
        return win.plugin


def is_game_project(win, project=None) -> bool:
    project = project or win.project
    if project is None:
        return False
    plugin = _plugin_of(win, project)
    extra = getattr(project, "extra", None) or {}
    return bool(getattr(plugin, "is_game", False) or "scenes" in extra or
                getattr(project, "language", "") in ("pygame", "godot"))


def project_scenes(project) -> list[str]:
    folder = Path(project.folder)
    try:
        from ..games.codegen import project_scenes as gen_scenes
        return gen_scenes(folder)
    except Exception:  # noqa: BLE001
        names = [str(s) for s in (getattr(project, "extra", {}) or {}).get("scenes", [])]
        names += [p.stem for p in sorted(folder.glob("*.scene")) if p.stem not in names]
        return [n for n in names if (folder / f"{n}.scene").exists()]


class IDEHost:
    """How a scene editor reaches the IDE: the code editors, Run, the Output window."""

    def __init__(self, win):
        self.win = win

    def _open_editor(self, path: Path):
        win = self.win
        ed = None
        if win.project is not None and path.parent.resolve() == Path(win.project.folder).resolve():
            ed = win._editor_for_file(path.name)
        if ed is None:
            ed = win.open_any_file(path)
        return ed

    def _open_text(self, path: Path):
        """The text of an already open editor for *path* (None = not open)."""
        win = self.win
        views = list(getattr(win, "modviews", {}).values()) + list(getattr(win, "codeviews", {}).values())
        for i in range(win.tabs.count()):
            views.append(win.tabs.widget(i))
        for v in views:
            p = getattr(v, "path", None)
            ed = getattr(v, "editor", None)
            if p is not None and ed is not None:
                try:
                    if Path(p).resolve() == path.resolve():
                        return ed
                except OSError:
                    continue
        if win.project is not None and path.name in getattr(win, "modviews", {}) and \
                path.parent.resolve() == Path(win.project.folder).resolve():
            return win.modviews[path.name].editor
        return None

    def get_code(self, path: Path) -> str:
        ed = self._open_text(path)
        if ed is not None:
            return ed.text()
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def show_code(self, path: Path, code: str | None, line: int) -> None:
        win = self.win
        if line < 0:                      # silent update (rename): the open editor or the file
            ed = self._open_text(path)
            if ed is not None and code is not None:
                self._replace(ed, code)
            elif code is not None:
                path.write_text(code, encoding="utf-8")
            return
        if not path.exists():
            path.write_text(code or "", encoding="utf-8")
            code = None
            self._add_module(path)
        ed = self._open_editor(path)
        if ed is None:
            if code is not None:
                path.write_text(code, encoding="utf-8")
            return
        if code is not None:
            self._replace(ed, code)
        try:
            ed.goto_line(line)
        except Exception:  # noqa: BLE001
            pass
        try:
            win._update_actions()
        except Exception:  # noqa: BLE001
            pass

    def _add_module(self, path: Path) -> None:
        win = self.win
        p = win.project
        if p is not None and path.parent.resolve() == Path(p.folder).resolve() and path.name not in p.modules:
            p.modules.append(path.name)
            p.save()
            win._fill_solution()

    @staticmethod
    def _replace(ed, code: str) -> None:
        if ed.text() == code:
            return
        line, col = ed.getCursorPosition()
        ed.beginUndoAction()
        ed.selectAll()
        ed.replaceSelectedText(code)
        ed.endUndoAction()
        ed.setCursorPosition(min(line, max(0, ed.lines() - 1)), col)

    def play(self, editor) -> bool:
        win = self.win
        if win.project is None:
            return False
        if win.session is not None and win.session.running():
            win.stop_project()                       # Play again = restart with the edited scene
        win.run_project(debug=False)                 # like Ctrl+F5: the game runs at full speed
        return True

    def log(self, text: str) -> None:
        self.win.log(text)


# ====================================================================== the feature
class GameDesigner:
    def __init__(self, win):
        self.win = win
        self.host = IDEHost(win)
        self.editors: dict[str, SceneEditor] = {}
        self.browser = AssetBrowser()
        self.dock = QDockWidget("Game Assets", win)
        self.dock.setObjectName("dock_game_assets")
        self.dock.setWidget(self.browser)
        win.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock)
        try:
            win.tabifyDockWidget(win.dock_toolbox, self.dock)
        except Exception:  # noqa: BLE001
            pass
        self.dock.hide()
        self._make_menu()
        self._wrap()
        win.tabs.currentChanged.connect(self._on_tab)
        win.solution.itemDoubleClicked.connect(self._on_tree_dclick)

    # ---------------------------------------------------------------- menu
    def _make_menu(self) -> None:
        win = self.win
        mb = win.menuBar()
        self.menu = m = mb.addMenu("Ga&me")
        before = next((a for a in mb.actions() if a.text().replace("&", "") in ("Tools", "Window", "Help")), None)
        if before is not None:
            mb.insertMenu(before, m)
        m.addAction("New Scene...", self.new_scene_dialog)
        self.open_menu = m.addMenu("Open Scene")
        self.open_menu.aboutToShow.connect(self._fill_open_menu)
        m.addSeparator()
        m.addAction("Play Scene (Ctrl+F5)", lambda: self.current() and self.current().play())
        m.addSeparator()
        m.addAction("Import Tileset...", lambda: self.current() and self.current().import_tileset())
        m.addAction("Sprite Sheet and Animations...", lambda: self.current() and self.current().edit_spritesheet(None))
        m.addAction("Add Sprite from Image...", lambda: self.current() and self.current().import_image())
        m.addAction("Import Sound...", self.browser.import_sound)
        m.addSeparator()
        m.addAction("Game Assets Window", self.show_assets)
        m.addAction("Check Scene", self.check_scene)
        m.addSeparator()
        self.a_export_godot = m.addAction("Export to Godot...", lambda: self.export_godot())
        self.a_export_godot.setToolTip("Make a Godot 4 project from this pygame game (scenes, art, behaviours; "
                                       "the Python handlers become GDScript funcs to translate)")
        m.aboutToShow.connect(self._update_menu)
        self.menu.menuAction().setVisible(False)

    def _update_menu(self) -> None:
        cur = self.current() is not None
        for a in self.menu.actions():
            t = a.text()
            if t.startswith(("Play", "Import Tileset", "Sprite Sheet", "Add Sprite", "Import Sound", "Check")):
                a.setEnabled(cur)
        self.open_menu.setEnabled(self.win.project is not None)
        self.a_export_godot.setEnabled(self.win.project is not None and is_game_project(self.win) and
                                       getattr(_plugin_of(self.win), "id", "") != "godot")

    def _fill_open_menu(self) -> None:
        self.open_menu.clear()
        p = self.win.project
        names = project_scenes(p) if p is not None else []
        for n in names:
            self.open_menu.addAction(f"{n}.scene", lambda n=n: self.open_scene(Path(p.folder) / f"{n}.scene"))
        if not names:
            self.open_menu.addAction("(no scenes)").setEnabled(False)

    def update_visibility(self) -> None:
        game = is_game_project(self.win)
        self.menu.menuAction().setVisible(game or bool(self.current()))
        if not game and self.current() is None and self.dock.isVisible():
            self.dock.hide()            # a non-game project: give the left panel back to the Toolbox
            tb = getattr(self.win, "dock_toolbox", None)
            if tb is not None and tb.isVisible():
                tb.raise_()

    def show_assets(self) -> None:
        self.dock.show()
        self.dock.raise_()

    def export_godot(self, dest=None):
        """Game > Export to Godot...: a Godot 4 project next to this one (<Name>_Godot), imported once with
        Godot when it is installed. Returns the folder (None = not exported)."""
        win = self.win
        p = win.project
        if p is None or not is_game_project(win) or getattr(_plugin_of(win), "id", "") == "godot":
            return None
        win.save_all()
        from PyQt6.QtGui import QGuiApplication
        from ..games import godot_export
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            out, report = godot_export.export_from_pygame(Path(p.folder), dest)
            exe = godot_export.godot_exe()
            if exe:
                r = godot_export.import_assets(out, exe)
                text = (r.stdout or "") + (r.stderr or "")
                errs = [ln.strip() for ln in text.splitlines() if "ERROR" in ln]
                report.append(f"Godot imported the project: {len(errs) or 'no'} error line(s)")
                report += errs[:20]
            else:
                report.append("Godot was not found: open the folder with Godot 4 (it imports the assets)")
        except Exception as e:  # noqa: BLE001
            win.log(f"*** Export to Godot failed: {e}")
            return None
        finally:
            QGuiApplication.restoreOverrideCursor()
        win.log(f"------ Export to Godot: {out} ------")
        for line in report:
            win.log("  " + line)
        win.log("  Open it with File > Open Project (project.radproj) or in Godot (project.godot).")
        try:
            win.dock_output.show()
            win.dock_output.raise_()
        except Exception:  # noqa: BLE001
            pass
        return out

    def check_scene(self) -> None:
        ed = self.current()
        if ed is None:
            return
        probs = ed.problems()
        QMessageBox.information(self.win, "Check Scene", "The scene has no problems." if not probs else
                                "Problems:\n\n" + "\n".join(f"- {p}" for p in probs))

    # ---------------------------------------------------------------- wrapping the window
    def _wrap(self) -> None:
        win = self.win
        orig_open_module = win.open_module
        orig_open_any = win.open_any_file
        orig_save_all = win.save_all
        orig_any_modified = win._any_modified
        orig_fill = win._fill_solution
        orig_open_project = win.open_project
        orig_activate = win.activate_project

        def open_module(filename, *a, **k):
            if str(filename).lower().endswith(".scene") and win.project is not None:
                return self.open_scene(Path(win.project.folder) / filename)
            return orig_open_module(filename, *a, **k)

        def open_any_file(path, *a, **k):
            if Path(path).suffix.lower() == ".scene":
                return self.open_scene(Path(path))
            return orig_open_any(path, *a, **k)

        def save_all(*a, **k):
            self.save_scenes()
            return orig_save_all(*a, **k)

        def any_modified(*a, **k):
            return any(self._alive(e) and e.is_modified() for e in self.editors.values()) or \
                orig_any_modified(*a, **k)

        def fill_solution(*a, **k):
            r = orig_fill(*a, **k)
            try:
                self._add_tree_scenes()
            except Exception as e:  # noqa: BLE001
                win.log(f"[game designer] {e}")
            return r

        def open_project(*a, **k):
            r = orig_open_project(*a, **k)
            try:
                self.update_visibility()
                self._open_start_scene()
            except Exception as e:  # noqa: BLE001
                win.log(f"[game designer] {e}")
            return r

        def activate_project(*a, **k):
            r = orig_activate(*a, **k)
            self.update_visibility()
            return r

        win.open_module = open_module
        win.open_any_file = open_any_file
        win.save_all = save_all
        win._any_modified = any_modified
        win._fill_solution = fill_solution
        win.open_project = open_project
        win.activate_project = activate_project
        win.open_scene = self.open_scene
        win.scene_editors = self.editors
        win.game_designer = self
        # Edit menu + Save All also reach the scene designer
        for attr, op in (("a_undo", "undo"), ("a_redo", "redo"), ("a_cut", "cut"), ("a_copy", "copy"),
                         ("a_paste", "paste"), ("a_delete", "delete"), ("a_select_all", "select_all")):
            act = getattr(win, attr, None)
            if act is not None:
                act.triggered.connect(lambda _c=False, op=op: self._edit(op))
        if getattr(win, "a_save", None) is not None:
            win.a_save.triggered.connect(lambda _c=False: self.save_scenes())

    @staticmethod
    def _alive(ed) -> bool:
        try:
            ed.isVisible()
            return True
        except RuntimeError:
            return False

    def current(self) -> SceneEditor | None:
        try:
            w = self.win.tabs.currentWidget()
        except RuntimeError:            # the main window is being destroyed (an undo stack still signals)
            return None
        return w if isinstance(w, SceneEditor) else None

    def _edit(self, op: str) -> None:
        ed = self.current()
        if ed is None or isinstance(QApplication.focusWidget(), (QLineEdit, QPlainTextEdit)):
            return
        ed.edit_op(op)
        self._update_actions()

    def save_scenes(self) -> None:
        for ed in list(self.editors.values()):
            if self._alive(ed) and ed.is_modified():
                ed.save()

    # ---------------------------------------------------------------- opening
    def open_scene(self, path: Path) -> SceneEditor | None:
        win = self.win
        path = Path(path).resolve()
        key = str(path).lower()
        ed = self.editors.get(key)
        if ed is not None and (not self._alive(ed) or win.tabs.indexOf(ed) < 0):
            self.editors.pop(key, None)
            ed = None
        if ed is None:
            if not path.exists() and not path.parent.is_dir():
                QMessageBox.warning(win, "Scene", f"The folder of {path.name} does not exist.")
                return None
            plugin = _plugin_of(win)
            ext = plugin.code_ext if plugin is not None and getattr(plugin, "is_game", False) and \
                getattr(plugin, "code_ext", "") else ".py"
            try:
                ed = SceneEditor(path, host=self.host, code_ext=ext,
                                 plugin=plugin if getattr(plugin, "is_game", False) else None)
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(win, "Scene", f"Cannot open {path.name}:\n{e}")
                return None
            ed.setToolTip(str(path))
            ed.modifiedChanged.connect(lambda _m, e=ed: self._title(e))
            ed.selectionChanged.connect(self._update_actions)
            ed.undo_stack.indexChanged.connect(lambda _i: self._update_actions())
            ed.saved.connect(lambda e=ed: self._after_save(e))
            self.editors[key] = ed
        win._show_tab(ed, path.name)
        self._title(ed)
        self._on_tab()
        ed.canvas.setFocus()
        return ed

    def _title(self, ed) -> None:
        i = self.win.tabs.indexOf(ed)
        if i >= 0:
            self.win.tabs.setTabText(i, ed.path.name + ("*" if ed.is_modified() else ""))

    def _after_save(self, ed) -> None:
        """The generated code follows the scene (<Scene>_designer.py for pygame)."""
        win = self.win
        plugin = _plugin_of(win)
        try:
            hook = getattr(plugin, "on_scene_saved", None)
            if callable(hook):
                hook(ed.base_dir, ed.path.stem)
            elif getattr(plugin, "id", "") == "pygame" or (ed.code_ext == ".py" and is_game_project(win)):
                from ..games.codegen import sync_scene
                sync_scene(ed.base_dir, ed.path.stem)
        except Exception as e:  # noqa: BLE001
            win.log(f"[scene {ed.path.name}] code generation: {e}")

    def _open_start_scene(self) -> None:
        win = self.win
        if win.project is None or not is_game_project(win) or self.current() is not None:
            return
        names = project_scenes(win.project)
        extra = getattr(win.project, "extra", {}) or {}
        start = (extra.get("game") or {}).get("start_scene") if isinstance(extra.get("game"), dict) else None
        name = start if start in names else (names[0] if names else None)
        if name:
            self.open_scene(Path(win.project.folder) / f"{name}.scene")

    def new_scene_dialog(self) -> SceneEditor | None:
        win = self.win
        if win.project is None:
            QMessageBox.information(win, "New Scene", "Open or create a game project first.")
            return None
        existing = set(project_scenes(win.project))
        k = len(existing) + 1
        while f"Level{k}" in existing:
            k += 1
        name, ok = QInputDialog.getText(win, "New Scene", "Scene name:", text=f"Level{k}")
        if not ok:
            return None
        return self.new_scene(name.strip())

    def new_scene(self, name: str) -> SceneEditor | None:
        win = self.win
        if not re.match(r"^[A-Za-z_]\w*$", name or ""):
            QMessageBox.warning(win, "New Scene", f"'{name}' is not a valid name.")
            return None
        folder = Path(win.project.folder)
        path = folder / f"{name}.scene"
        if path.exists():
            return self.open_scene(path)
        from ..games.model import Scene
        sc = Scene.new(name)
        cur = self.current()
        if cur is not None:             # same window size / look as the scene being edited
            sc.width, sc.height, sc.background, sc.fps, sc.gravity = (cur.scene.width, cur.scene.height,
                                                                     cur.scene.background, cur.scene.fps,
                                                                     cur.scene.gravity)
            sc.layers[0].resize(-(-sc.width // 32), -(-sc.height // 32))
        sc.save(path)
        extra = win.project.extra
        scenes = list(extra.get("scenes") or [])
        if name not in scenes:
            scenes.append(name)
        extra["scenes"] = scenes
        plugin = _plugin_of(win)
        hook = getattr(plugin, "on_scene_saved", None)
        try:
            if callable(hook):
                hook(folder, name)
            elif getattr(plugin, "id", "") == "pygame" or is_game_project(win):
                from ..games.codegen import sync_scene
                sync_scene(folder, name)
        except Exception as e:  # noqa: BLE001
            win.log(f"[new scene] {e}")
        code = f"{name}{plugin.code_ext if plugin is not None and getattr(plugin, 'is_game', False) else '.py'}"
        if callable(getattr(plugin, "scene_code_file", None)):
            code = plugin.scene_code_file(name)
        if not (folder / code).exists() and callable(getattr(plugin, "new_scene_code", None)):
            try:
                (folder / code).write_text(plugin.new_scene_code(sc.to_dict()), encoding="utf-8")
            except Exception as e:  # noqa: BLE001
                win.log(f"[new scene] {e}")
        if (folder / code).exists() and code not in win.project.modules:
            win.project.modules.append(code)
        win.project.save()
        win._fill_solution()
        return self.open_scene(path)

    # ---------------------------------------------------------------- solution explorer
    def _add_tree_scenes(self) -> None:
        win = self.win
        try:
            from .solution_ui import PROJECT_ROLE
        except ImportError:
            return
        tree = win.solution
        stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
        while stack:
            it = stack.pop()
            stack.extend(it.child(i) for i in range(it.childCount()))
            data = it.data(0, ROLE)
            if not data or data[0] != "project":
                continue
            key = it.data(0, PROJECT_ROLE)
            st = getattr(win, "_pstates", {}).get(key)
            project = st["project"] if st else None
            if project is None or not is_game_project(win, project):
                continue
            if any(it.child(i).text(0).split()[0].lower().endswith(".scene") for i in range(it.childCount())):
                continue
            pos = 1 if it.childCount() and (it.child(0).data(0, ROLE) or ("",))[0] == "references" else 0
            for n in reversed(project_scenes(project)):
                si = QTreeWidgetItem([f"{n}.scene"])
                si.setData(0, ROLE, ("scene", f"{n}.scene"))
                si.setData(0, PROJECT_ROLE, key)
                si.setToolTip(0, "Game scene - double-click to open the scene designer")
                si.setIcon(0, win.style().standardIcon(win.style().StandardPixmap.SP_DesktopIcon))
                it.insertChild(pos, si)

    def _on_tree_dclick(self, item, _col) -> None:
        data = item.data(0, ROLE)
        if data and data[0] == "scene" and self.win.project is not None:
            self.open_scene(Path(self.win.project.folder) / data[1])

    # ---------------------------------------------------------------- tabs
    def _on_tab(self, *_a) -> None:
        ed = self.current()
        self.browser.set_editor(ed)
        if ed is not None:
            if not self.dock.isVisible():
                self.dock.show()
            self.dock.raise_()
            if self.dock.width() > 340 and not self.dock.isFloating():     # leave room for the level
                try:
                    self.win.resizeDocks([self.dock], [260], Qt.Orientation.Horizontal)
                except Exception:  # noqa: BLE001
                    pass
            if not getattr(ed, "_ide_fitted", False):       # first time: show the whole level
                ed._ide_fitted = True
                QTimer.singleShot(0, ed.fit_view)
            try:
                self.win.properties.set_document(None, self.win.plugin)
            except Exception:  # noqa: BLE001
                pass
        self.update_visibility()
        self._update_actions()

    def _update_actions(self) -> None:
        ed = self.current()
        if ed is None:
            return
        win = self.win
        sel = bool(ed.canvas.selected_names())
        for attr, on in (("a_undo", ed.undo_stack.canUndo()), ("a_redo", ed.undo_stack.canRedo()),
                         ("a_cut", sel), ("a_copy", sel), ("a_delete", sel), ("a_paste", True),
                         ("a_select_all", True)):
            a = getattr(win, attr, None)
            if a is not None:
                a.setEnabled(on)


def install(win) -> None:
    GameDesigner(win)
