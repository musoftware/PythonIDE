"""IDE integration of the advanced Flutter designer (docs/FLUTTER_DESIGNER.md, CONTRACTS 10.6).

* ``*.fscreen.json`` files open in ``radide.flutterdesign.designer.FlutterDesigner`` (File > Open, Solution
  Explorer "Screens" node, Open Folder ...); Save / Save All save them and regenerate their Dart code.
* Project > **Add New Screen...** (Flutter projects): blank screen, a template (login, sign-up, shop ...) or a
  screen imported from a Dart file (package:analyzer importer).
* New Project > Mobile > **Flutter App (visual designer)** (``flutter_designer`` template of the Flutter plugin):
  a project made of designed screens - see ``build_designer_project``.
* Double-clicking an event in the designer creates the handler in ``lib/screens/<screen>_events.dart`` and opens
  it at that line (VB style). Edit > Undo / Redo / Cut / Copy / Paste / Delete act on the current screen.
The old VB-style absolute-position Flutter forms (``.form``, CONTRACTS 10.1) are untouched and keep working.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QTreeWidgetItem,
                             QVBoxLayout)

from ..flutterdesign import model as M

ROLE = Qt.ItemDataRole.UserRole
EXT = M.SCREEN_EXT


def _is_screen(path) -> bool:
    return str(path).lower().endswith(EXT)


# ================================================================== new project (Flutter plugin template)
def blank_screen(name: str, app_bar: bool = True, title: str | None = None) -> M.Screen:
    scr = M.Screen.new(name)
    tree = scr.tree
    if app_bar:
        tree["slots"]["appBar"]["slots"]["title"]["props"]["data"] = title or name
    else:
        tree["slots"].pop("appBar", None)
    return scr


def build_designer_project(plugin, folder: Path, name: str):
    """New Project > Mobile > Flutter App (visual designer): screens/Login + screens/Home (designed screens, no
    .form files), lib/main.dart starting on the login screen. Uses the template gallery when it is installed."""
    from ..model import Project
    folder = Path(folder)
    (folder / "lib").mkdir(parents=True, exist_ok=True)
    (folder / "screens").mkdir(exist_ok=True)
    project = Project(folder, name, plugin.id)
    project.extra["mobile"] = {"device": "chrome"}
    project.extra["designer"] = "widget-tree"
    project.save()
    plugin.write_project_files(project)          # pubspec.yaml etc. first (templates register their assets)
    made = []
    try:
        from ..flutterdesign import templates as TP
        if any(t.id == "login" for t in TP.list_templates()):
            scr, _p = TP.instantiate("login", folder, "Login", "/login")
            made.append(scr)
    except Exception:  # noqa: BLE001 - templates are optional
        made = []
    if not made:
        login = blank_screen("Login", app_bar=False)
        login.tree["slots"]["body"] = M.new_node("SafeArea", login)
        login.tree["slots"]["body"]["slots"] = {"child": M.new_node("Center", login)}
        login.tree["slots"]["body"]["slots"]["child"]["slots"] = {"child": M.new_node("Text", login, props={
            "data": "Welcome", "style": {"fontSize": 32, "fontWeight": "FontWeight.bold"}})}
        login.save(folder / "screens" / f"Login{EXT}")
    if not (folder / "screens" / f"Home{EXT}").exists():
        home = blank_screen("Home", title="Home")
        home.save(folder / "screens" / f"Home{EXT}")
    project.startup = "Login"                    # the app starts on this screen (flutter.py write_project_files)
    plugin.write_project_files(project)
    project.save()
    return project


# ======================================================================================= new screen dialog
class NewScreenDialog(QDialog):
    """Name + where to start: blank, a template of the gallery, or an existing Dart file."""

    def __init__(self, parent, folder: Path):
        super().__init__(parent)
        self.setWindowTitle("Add New Screen")
        self.resize(720, 520)
        self.folder = Path(folder)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        i = 1
        while (self.folder / "screens" / f"Screen{i}{EXT}").exists():
            i += 1
        self.name = QLineEdit(f"Screen{i}")
        self.route = QLineEdit()
        self.route.setPlaceholderText("/" + M.snake(self.name.text()))
        self.name.textChanged.connect(lambda t: self.route.setPlaceholderText("/" + M.snake(M.class_name(t))))
        form.addRow("Name", self.name)
        form.addRow("Route", self.route)
        lay.addLayout(form)
        lay.addWidget(QLabel("Start from"))
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setIconSize(QSize(96, 160))
        self.list.setGridSize(QSize(150, 210))
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setWordWrap(True)
        self.list.setProperty("i18n_skip_items", False)
        lay.addWidget(self.list, 1)
        self.desc = QLabel("")
        self.desc.setWordWrap(True)
        lay.addWidget(self.desc)
        self._add("blank", "Blank screen", "Scaffold with an app bar", None)
        self._add("blank_noappbar", "Blank (no app bar)", "Scaffold with a SafeArea body - full-bleed designs", None)
        self._add("import", "Import from Dart...", "Turn a build() method of an existing .dart file into a "
                                                   "designable screen (unknown code is kept verbatim)", None)
        try:
            from ..flutterdesign import templates as TP
            for t in TP.list_templates():
                self._add("tpl:" + t.id, t.title, t.description, t.thumbnail)
        except Exception:  # noqa: BLE001
            pass
        self.list.currentItemChanged.connect(lambda it, _p: self.desc.setText(it.toolTip() if it else ""))
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        self.list.setCurrentRow(0)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _add(self, key, title, desc, thumb):
        it = QListWidgetItem(title)
        it.setData(ROLE, key)
        it.setToolTip(desc)
        if thumb is not None and Path(thumb).exists():
            pm = QPixmap(str(thumb))
            if not pm.isNull():
                it.setIcon(QIcon(pm.scaled(96, 160, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)))
        elif key.startswith("tpl:"):            # no picture shipped: draw the template with the Qt preview
            try:
                from ..flutterdesign import qtpreview as Q
                from ..flutterdesign import templates as TP
                scr = TP.get(key[4:]).load()
                img = Q.render_image(scr, 390, 650, scale=0.25, folder=TP.HERE / "assets")
                it.setIcon(QIcon(QPixmap.fromImage(img)))
            except Exception:  # noqa: BLE001
                pass
        else:
            from ..flutterdesign import iconfont
            it.setIcon(iconfont.icon({"blank": "Icons.web_asset", "blank_noappbar": "Icons.crop_portrait",
                                      "import": "Icons.file_download"}.get(key, "Icons.phone_android"), 64,
                                     "#FF3F51B5"))
        self.list.addItem(it)

    def choice(self) -> str:
        it = self.list.currentItem()
        return it.data(ROLE) if it else "blank"

    def screen_name(self) -> str:
        return M.class_name(self.name.text().strip() or "Screen1")

    def route_value(self) -> str | None:
        r = self.route.text().strip()
        return (r if r.startswith("/") else "/" + r) if r else None


# ============================================================================================ manager
class FlutterDesignerManager:
    def __init__(self, win):
        self.win = win
        self.editors: dict[str, object] = {}

    @staticmethod
    def _alive(ed) -> bool:
        try:
            ed.isVisible()
            return True
        except RuntimeError:
            return False

    def _views(self):
        return [e for e in self.editors.values() if self._alive(e)]

    def current(self):
        from ..flutterdesign.designer import FlutterDesigner
        try:
            w = self.win.tabs.currentWidget()
        except RuntimeError:
            return None
        return w if isinstance(w, FlutterDesigner) else None

    def _project_folder_of(self, path: Path) -> Path | None:
        from ..flutterdesign.designer import find_project_folder
        f = find_project_folder(path)
        if f is not None:
            return f
        prj = getattr(self.win, "project", None)
        if prj is not None:
            try:
                path.resolve().relative_to(Path(prj.folder).resolve())
                return Path(prj.folder)
            except ValueError:
                pass
        return None

    # ---- open / save
    def open_screen(self, path):
        from ..flutterdesign.designer import FlutterDesigner
        win = self.win
        path = Path(path).resolve()
        key = str(path).lower()
        ed = self.editors.get(key)
        if ed is not None and (not self._alive(ed) or win.tabs.indexOf(ed) < 0):
            self.editors.pop(key, None)
            ed = None
        if ed is None:
            try:
                ed = FlutterDesigner(path, project_folder=self._project_folder_of(path))
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(win, "Flutter Designer", f"Cannot open {path.name}:\n{e}")
                return None
            ed.setToolTip(str(path))
            ed.modifiedChanged.connect(lambda _m, e=ed: self._title(e))
            ed.openCode.connect(self._open_code)
            ed.message.connect(lambda t: win.statusBar().showMessage(t, 6000))
            ed.saved.connect(lambda _p: self._after_save())
            upd = getattr(win, "_update_actions", None)
            if callable(upd):
                ed.undo_stack.indexChanged.connect(lambda _i: win._update_actions())
                ed.selectionChanged.connect(lambda _s: win._update_actions())
            self.editors[key] = ed
        win._show_tab(ed, path.name)
        self._title(ed)
        return ed

    def _title(self, ed):
        i = self.win.tabs.indexOf(ed)
        if i >= 0:
            self.win.tabs.setTabText(i, ed.path.name + ("*" if ed.is_modified() else ""))

    def _after_save(self):
        try:
            self.win._fill_solution()
        except Exception:  # noqa: BLE001
            pass

    def _open_code(self, path, line: int):
        win = self.win
        ed = None
        try:
            prj = win.project
            if prj is not None and Path(path).resolve().parent == Path(prj.folder).resolve():
                ed = win._editor_for_file(Path(path).name)
        except Exception:  # noqa: BLE001
            ed = None
        if ed is None:
            opener = getattr(win, "open_file", None)
            try:
                ed = opener(path, line) if callable(opener) and win.project is not None else win.open_any_file(path)
            except TypeError:
                ed = win.open_any_file(path)
        if ed is None:
            return
        try:
            if hasattr(ed, "goto_line"):
                ed.goto_line(max(0, line - 1))
            elif hasattr(ed, "setCursorPosition"):
                ed.setCursorPosition(max(0, line - 1), 4)
            ed.setFocus()
        except Exception:  # noqa: BLE001
            pass

    def save_screens(self):
        for ed in self._views():
            if ed.is_modified():
                ed.save()

    def any_modified(self) -> bool:
        return any(e.is_modified() for e in self._views())

    # ---- commands
    def add_screen(self):
        win = self.win
        prj = win.project
        folder = Path(prj.folder) if prj is not None else None
        if folder is None:
            path, _f = QFileDialog.getSaveFileName(win, "New Flutter screen", f"Screen1{EXT}",
                                                   f"Flutter screen (*{EXT})")
            if not path:
                return None
            name = M.class_name(Path(path).name[:-len(EXT)] if path.lower().endswith(EXT) else Path(path).stem)
            blank_screen(name).save(path)
            return self.open_screen(path)
        dlg = NewScreenDialog(win, folder)
        if not dlg.exec():
            return None
        return self.create_screen(folder, dlg.choice(), dlg.screen_name(), dlg.route_value())

    def create_screen(self, folder: Path, choice: str, name: str, route: str | None = None, dart_file=None):
        win = self.win
        folder = Path(folder)
        path = folder / "screens" / f"{name}{EXT}"
        if path.exists() and not choice.startswith("tpl:"):
            QMessageBox.warning(win, "Add New Screen", f"{path.name} already exists.")
            return None
        try:
            if choice.startswith("tpl:"):
                from ..flutterdesign import templates as TP
                _scr, path = TP.instantiate(choice[4:], folder, name, route)
            elif choice == "import":
                scr = self._import_dart(folder, dart_file)
                if scr is None:
                    return None
                scr.data["name"] = name
                if route:
                    scr.data["route"] = route
                scr.save(path)
            else:
                scr = blank_screen(name, app_bar=choice == "blank")
                if choice == "blank_noappbar":
                    body = M.new_node("SafeArea", scr)
                    body["slots"] = {"child": M.new_node("Column", scr)}
                    scr.tree["slots"]["body"] = body
                if route:
                    scr.data["route"] = route
                scr.save(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(win, "Add New Screen", f"Cannot create the screen:\n{e}")
            return None
        self._regenerate(folder)
        try:
            win._fill_solution()
        except Exception:  # noqa: BLE001
            pass
        win.log(f"[flutter designer] created {path.relative_to(folder) if path.is_relative_to(folder) else path}")
        return self.open_screen(path)

    def _import_dart(self, folder: Path, dart_file=None) -> M.Screen | None:
        win = self.win
        if dart_file is None:
            dart_file, _f = QFileDialog.getOpenFileName(win, "Import a Flutter screen", str(folder / "lib"),
                                                        "Dart (*.dart)")
            if not dart_file:
                return None
        from ..flutterdesign import importer
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            res = importer.import_file(dart_file)
        except Exception as e:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(win, "Import", f"The Dart file could not be imported:\n{e}")
            return None
        QApplication.restoreOverrideCursor()
        if not res.screens:
            QMessageBox.information(win, "Import", "No build() method with a widget tree was found.")
            return None
        data = res.screens[0]
        if len(res.screens) > 1:
            names = [s.get("name", "?") for s in res.screens]
            dlg = QDialog(win)
            dlg.setWindowTitle("Import - choose the screen")
            lay = QVBoxLayout(dlg)
            cb = QComboBox()
            cb.addItems(names)
            lay.addWidget(cb)
            bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            bb.accepted.connect(dlg.accept)
            bb.rejected.connect(dlg.reject)
            lay.addWidget(bb)
            if not dlg.exec():
                return None
            data = res.screens[cb.currentIndex()]
        if res.report:
            text = "\n".join(f"{lvl}: {t}" for lvl, t in res.report[:200])
            win.log("[flutter designer] import report:\n" + text)
        return M.Screen(data)

    def import_dart_screen(self):
        prj = self.win.project
        if prj is None:
            QMessageBox.information(self.win, "Import", "Open or create a Flutter project first.")
            return None
        folder = Path(prj.folder)
        scr = self._import_dart(folder)
        if scr is None:
            return None
        base = M.class_name(scr.name)
        name, i = base, 2
        while (folder / "screens" / f"{name}{EXT}").exists():
            name, i = f"{base}{i}", i + 1
        scr.data["name"] = name
        path = folder / "screens" / f"{name}{EXT}"
        scr.save(path)
        self._regenerate(folder)
        try:
            self.win._fill_solution()
        except Exception:  # noqa: BLE001
            pass
        return self.open_screen(path)

    def _regenerate(self, folder: Path):
        """Write the project files (main.dart gets the designed routes) of RAD IDE Flutter projects."""
        prj = self.win.project
        try:
            if prj is not None and prj.language == "flutter" and Path(prj.folder).resolve() == folder.resolve():
                from ..languages import get_plugin
                get_plugin("flutter").write_project_files(prj)
            elif (folder / "pubspec.yaml").exists():
                from ..flutterdesign import codegen
                codegen.write_all(folder)
        except Exception as e:  # noqa: BLE001
            self.win.log(f"[flutter designer] code generation: {e}")

    # ---- solution explorer
    def add_tree_nodes(self):
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
            if not data or not isinstance(data, tuple) or data[0] != "project":
                continue
            key = it.data(0, PROJECT_ROLE)
            st = getattr(win, "_pstates", {}).get(key)
            prj = st["project"] if st else win.project
            if prj is None:
                continue
            screens = M.find_screens(prj.folder)
            if not screens or any((it.child(i).data(0, ROLE) or ("",))[0] == "fscreens"
                                  for i in range(it.childCount())):
                continue
            node = QTreeWidgetItem(it, ["Screens"])
            node.setData(0, ROLE, ("fscreens", str(prj.folder)))
            node.setData(0, PROJECT_ROLE, key)
            from ..flutterdesign import iconfont
            node.setIcon(0, iconfont.icon("Icons.phone_android", 16, "#FF02569B"))
            for p in screens:
                si = QTreeWidgetItem(node, [p.name])
                si.setData(0, ROLE, ("fscreen", str(p)))
                si.setData(0, PROJECT_ROLE, key)
                si.setToolTip(0, "Flutter screen - double-click to open the visual designer")
                si.setIcon(0, iconfont.icon("Icons.web_asset", 16, "#FF3F51B5"))
            node.setExpanded(True)

    def on_tree_dclick(self, item, _col):
        data = item.data(0, ROLE)
        if data and isinstance(data, tuple) and data[0] == "fscreen":
            self.open_screen(Path(data[1]))

    # ---- edit menu routing
    def edit(self, op: str):
        ed = self.current()
        if ed is None:
            return
        w = QApplication.focusWidget()
        if isinstance(w, (QLineEdit, QPlainTextEdit)) or (isinstance(w, QComboBox) and w.isEditable()):
            return                                   # the IDE's own handler edits the text field
        {"undo": ed.undo, "redo": ed.redo, "cut": ed.cut_selected, "copy": ed.copy_selected,
         "paste": ed.paste, "delete": ed.delete_selected}[op]()

    def open_start_screen(self):
        prj = self.win.project
        if prj is None or getattr(prj, "language", "") != "flutter" or prj.forms:
            return
        if any(self._alive(e) and self.win.tabs.indexOf(e) >= 0 for e in self.editors.values()):
            return
        screens = M.find_screens(prj.folder)
        if screens:
            first = next((p for p in screens if p.name.lower().startswith("login")), screens[0])
            self.open_screen(first)

    # ---- wrapping the window
    def wrap(self):
        win = self.win
        orig_open_any = win.open_any_file
        orig_open_module = win.open_module
        orig_save_all = win.save_all
        orig_any_modified = win._any_modified
        orig_fill = win._fill_solution
        orig_open_project = getattr(win, "open_project", None)

        def open_any_file(path, *a, **k):
            if _is_screen(path):
                return self.open_screen(Path(path))
            return orig_open_any(path, *a, **k)

        def open_module(filename, *a, **k):
            if _is_screen(filename) and win.project is not None:
                return self.open_screen(Path(win.project.folder) / filename)
            return orig_open_module(filename, *a, **k)

        def save_all(*a, **k):
            self.save_screens()
            return orig_save_all(*a, **k)

        def any_modified(*a, **k):
            return self.any_modified() or orig_any_modified(*a, **k)

        def fill_solution(*a, **k):
            r = orig_fill(*a, **k)
            try:
                self.add_tree_nodes()
            except Exception as e:  # noqa: BLE001
                win.log(f"[flutter designer] {e}")
            return r

        win.open_any_file = open_any_file
        win.open_module = open_module
        win.save_all = save_all
        win._any_modified = any_modified
        win._fill_solution = fill_solution
        if callable(orig_open_project):
            def open_project(*a, **k):
                r = orig_open_project(*a, **k)
                QTimer.singleShot(0, self._safe_start)
                return r
            win.open_project = open_project
        orig_update = getattr(win, "_update_actions", None)
        if callable(orig_update):
            def update_actions(*a, **k):
                r = orig_update(*a, **k)
                ed = self.current()
                if ed is not None:            # Edit menu commands of the current screen designer
                    st = ed.undo_stack
                    win.a_undo.setEnabled(st.canUndo())
                    win.a_redo.setEnabled(st.canRedo())
                    sel = bool(ed.selected) and ed.selected != ed.screen.tree.get("id")
                    for act in (win.a_cut, win.a_copy, win.a_delete):
                        act.setEnabled(sel)
                    win.a_paste.setEnabled(True)
                return r
            win._update_actions = update_actions
        win.open_flutter_screen = self.open_screen
        win.add_flutter_screen = self.add_screen
        win.flutter_designer = self
        QTimer.singleShot(0, self._wrap_open_file)

    def _safe_start(self):
        try:
            self.open_start_screen()
        except Exception as e:  # noqa: BLE001
            self.win.log(f"[flutter designer] {e}")

    def _wrap_open_file(self):
        win = self.win
        orig = getattr(win, "open_file", None)
        if not callable(orig) or getattr(orig, "_rad_fscreen", False):
            return

        def open_file(path, *a, **k):
            p = Path(path)
            if not p.is_absolute() and getattr(win, "project", None) is not None:
                p = Path(win.project.folder) / p
            if _is_screen(p):
                return self.open_screen(p)
            return orig(path, *a, **k)
        open_file._rad_fscreen = True
        win.open_file = open_file


def _project_menu(win):
    for a in win.menuBar().actions():
        if a.text().replace("&", "") == "Project" and a.menu() is not None:
            return a.menu()
    return None


def _project_resources(win, what: str) -> None:
    """Project > Flutter Assets / Fonts / App Theme (radide/flutterdesign/asset_dialogs.py). After a change the
    project files are regenerated (pubspec assets/fonts, lib/theme/app_theme.dart wired into main.dart)."""
    prj = getattr(win, "project", None)
    if prj is None or getattr(prj, "language", "") != "flutter":
        QMessageBox.information(win, "Flutter", "Open a Flutter project first.")
        return
    from ..flutterdesign import asset_dialogs as AD
    folder = Path(prj.folder)
    if what == "assets":
        changed = True
        AD.open_asset_manager(win, folder)
    elif what == "fonts":
        e = AD.pick_font(win, folder)
        changed = bool(e)
        if e:
            try:
                win.log(f"[flutter] font {e.get('family')} ({e.get('source')}) added to the project")
            except Exception:  # noqa: BLE001
                pass
    else:
        changed = AD.edit_theme(win, folder)
    if not changed:
        return
    try:
        from ..languages import get_plugin
        get_plugin("flutter").write_project_files(prj)
    except Exception:  # noqa: BLE001 - the dialogs already wrote their own files
        pass


def install(win) -> None:
    mgr = FlutterDesignerManager(win)
    mgr.wrap()
    m = _project_menu(win)
    if m is not None:
        acts = m.actions()
        before = next((a for a in acts if a.text().replace("&", "").startswith("Add Existing")), None)
        act = QAction("Add New &Screen (Flutter designer)...", win)
        act.triggered.connect(lambda _c=False: mgr.add_screen())
        act.setObjectName("actAddFlutterScreen")
        imp = QAction("Import Flutter Screen from &Dart...", win)
        imp.triggered.connect(lambda _c=False: mgr.import_dart_screen())
        res_acts = []
        for text, fn in (("Flutter Assets...", lambda: _project_resources(win, "assets")),
                         ("Flutter Fonts (Google Fonts)...", lambda: _project_resources(win, "fonts")),
                         ("Flutter App Theme...", lambda: _project_resources(win, "theme"))):
            ra = QAction(text, win)
            ra.triggered.connect(lambda _c=False, fn=fn: fn())
            res_acts.append(ra)
        for a in (act, imp, *res_acts):
            m.insertAction(before, a) if before is not None else m.addAction(a)

        def visible():
            prj = getattr(win, "project", None)
            on = prj is not None and getattr(prj, "language", "") == "flutter"
            for a in (act, imp, *res_acts):
                a.setVisible(on)
        m.aboutToShow.connect(visible)
        win.act_add_flutter_screen = act
    try:
        win.solution.itemDoubleClicked.connect(mgr.on_tree_dclick)
    except Exception:  # noqa: BLE001
        pass
    for attr, op in (("a_undo", "undo"), ("a_redo", "redo"), ("a_cut", "cut"), ("a_copy", "copy"),
                     ("a_paste", "paste"), ("a_delete", "delete")):
        a = getattr(win, attr, None)
        if a is not None:
            a.triggered.connect(lambda _c=False, op=op: mgr.edit(op))
    try:
        from .command_palette import register_command
        register_command("flutter.newScreen", "Flutter: Add New Screen (visual designer)...", mgr.add_screen,
                         "Project")
        register_command("flutter.importScreen", "Flutter: Import Screen from Dart...", mgr.import_dart_screen,
                         "Project")
        register_command("flutter.assets", "Flutter: Project Assets...",
                         lambda: _project_resources(win, "assets"), "Project")
        register_command("flutter.fonts", "Flutter: Add Google Font...",
                         lambda: _project_resources(win, "fonts"), "Project")
        register_command("flutter.theme", "Flutter: App Theme...",
                         lambda: _project_resources(win, "theme"), "Project")
    except Exception:  # noqa: BLE001
        pass
