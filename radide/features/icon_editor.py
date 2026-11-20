"""Icon / Image Editor and project Resources (VB 2005 / Visual Studio style).

* File > New > Icon / Image...  and Tools > Image Editor: draw .ico (16..256, multi-size), .cur, .png, .bmp.
  Image files opened from Solution Explorer / File > Open File open in the editor.
* Project > Resources: strings, images, icons and files of the project (Resources/resources.json) with
  generated ``resources.py`` for Python projects.
* Image / Icon properties in the Properties window show the *Select Resource* dialog (pick from the project
  resources, import, or draw a new icon).
* Image > Set as Form Icon / Set as Application Icon (project.radproj "icon" + publish.json icon used by
  Build > Publish / installers).
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog, QInputDialog, QLineEdit, QMessageBox,
                             QPlainTextEdit, QTreeWidgetItem)

from ..imaging import IMAGE_EXTS
from ..imaging.editor import FILTER_OPEN, IconEditor, NewImageDialog
from ..imaging.resource_editor import ResourceEditor, SelectResourceDialog
from ..imaging.resources import FOLDER, ProjectResources

ROLE = Qt.ItemDataRole.UserRole
PICTURE_PROPS = ("icon", "image", "picture", "backgroundimage")


def _rel(win, path: Path) -> str | None:
    """*path* relative to the active project (posix), None when it is outside."""
    if win.project is None:
        return None
    try:
        return Path(path).resolve().relative_to(Path(win.project.folder).resolve()).as_posix()
    except ValueError:
        return None


class ImageFeature:
    def __init__(self, win):
        self.win = win
        self.editors: dict[str, IconEditor] = {}
        self.res_editor: ResourceEditor | None = None
        self._last_form: str | None = None
        self._make_menus()
        self._wrap()
        self._patch_properties()
        win.tabs.currentChanged.connect(self._on_tab)
        try:
            win.solution.itemDoubleClicked.connect(self._on_tree_dclick)
        except Exception:  # noqa: BLE001
            pass

    # ---------------------------------------------------------------- menus
    def _menu(self, title: str):
        mb = self.win.menuBar()
        return next((a.menu() for a in mb.actions() if a.menu() is not None and
                     a.text().replace("&", "") == title), None)

    def _make_menus(self) -> None:
        win = self.win
        fm = getattr(win, "file_menu", None) or self._menu("File")
        if fm is not None:
            act = next((a for a in fm.actions() if a.menu() is not None and
                        a.text().replace("&", "").startswith("Recent")), None)
            sub = fm.addMenu("New I&mage")
            if act is not None:
                fm.insertMenu(act, sub)
            sub.addAction("Icon (.ico)...", lambda: self.new_image("icon"))
            sub.addAction("Cursor (.cur)...", lambda: self.new_image("cursor"))
            sub.addAction("Image (.png / .bmp)...", lambda: self.new_image("png"))
        tm = self._menu("Tools")
        if tm is not None:
            m = tm.addMenu("&Image Editor")
            self.image_menu = m
            m.addAction("New Icon...", lambda: self.new_image("icon"))
            m.addAction("New Image...", lambda: self.new_image("png"))
            m.addAction("Open Image...", self.open_dialog)
            m.addSeparator()
            self.a_form_icon = m.addAction("Set as Form Icon", lambda: self.set_form_icon())
            self.a_app_icon = m.addAction("Set as Application Icon", lambda: self.set_app_icon())
            self.a_add_res = m.addAction("Add to Project Resources", lambda: self.add_current_to_resources())
            m.aboutToShow.connect(self._update_menu)
        pm = self._menu("Project")
        if pm is not None:
            pm.addSeparator()
            pm.addAction("&Resources...", self.open_resources)

    def _update_menu(self) -> None:
        ed = self.current()
        inside = ed is not None and ed.doc.path is not None and _rel(self.win, ed.doc.path) is not None
        for a in (self.a_form_icon, self.a_app_icon, self.a_add_res):
            a.setEnabled(inside)

    # ---------------------------------------------------------------- window wrapping
    def _wrap(self) -> None:
        win = self.win
        orig_open_any = win.open_any_file
        orig_save_all = win.save_all
        orig_any_modified = win._any_modified
        orig_fill = win._fill_solution

        def open_any_file(path, *a, **k):
            if Path(path).suffix.lower() in IMAGE_EXTS:
                return self.open_image(Path(path))
            return orig_open_any(path, *a, **k)

        def save_all(*a, **k):
            self.save_documents()
            return orig_save_all(*a, **k)

        def any_modified(*a, **k):
            return any(self._alive(e) and e.is_modified() for e in self._docs()) or orig_any_modified(*a, **k)

        def fill_solution(*a, **k):
            r = orig_fill(*a, **k)
            try:
                self._add_tree_nodes()
            except Exception as e:  # noqa: BLE001
                win.log(f"[image editor] {e}")
            return r

        win.open_any_file = open_any_file
        win.save_all = save_all
        win._any_modified = any_modified
        win._fill_solution = fill_solution
        win.open_image = self.open_image
        win.image_editor = self
        for attr, op in (("a_undo", "undo"), ("a_redo", "redo"), ("a_cut", "cut"), ("a_copy", "copy"),
                         ("a_paste", "paste"), ("a_delete", "delete"), ("a_select_all", "select_all")):
            act = getattr(win, attr, None)
            if act is not None:
                act.triggered.connect(lambda _c=False, op=op: self._edit(op))
        if getattr(win, "a_save", None) is not None:
            win.a_save.triggered.connect(lambda _c=False: self.save_documents())

    def _patch_properties(self) -> None:
        """Image / Icon properties: the Select Resource dialog instead of a bare file dialog."""
        from .. import properties as props_mod
        cls = props_mod.PropertiesPanel
        if getattr(cls, "_rad_res_patched", False):
            cls._rad_res_feature = self
            return
        orig = cls._pick_file
        feature = self
        cls._rad_res_feature = feature

        def _pick_file(panel, name: str) -> None:
            f = getattr(cls, "_rad_res_feature", None)
            doc = getattr(panel, "doc", None)
            if f is None or doc is None or name.lower() not in PICTURE_PROPS:
                return orig(panel, name)
            current = str(panel._props_dict().get(name) or "")
            value = f.select_resource(Path(doc.path).parent, current, name, panel)
            if value is not None and value != current:
                panel._set(name, value)
                panel._refresh_values()

        cls._pick_file = _pick_file
        cls._rad_res_patched = True

    def select_resource(self, folder: Path, current: str, prop: str = "Image", parent=None) -> str | None:
        dlg = SelectResourceDialog(folder, current, prop, parent or self.win, edit_image=self.open_image)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        self._refresh_res_editor()
        return dlg.value

    # ---------------------------------------------------------------- documents
    @staticmethod
    def _alive(w) -> bool:
        try:
            w.isVisible()
            return True
        except RuntimeError:
            return False

    def _docs(self):
        out = [e for e in self.editors.values() if self._alive(e)]
        if self.res_editor is not None and self._alive(self.res_editor):
            out.append(self.res_editor)
        return out

    def current(self) -> IconEditor | None:
        try:
            w = self.win.tabs.currentWidget()
        except RuntimeError:
            return None
        return w if isinstance(w, IconEditor) else None

    def _on_tab(self, *_a) -> None:
        try:
            d = self.win._current_designer()
        except Exception:  # noqa: BLE001
            d = None
        if d is not None:
            name = next((n for n, v in getattr(self.win, "designers", {}).items() if v is d), None)
            if name:
                self._last_form = name

    def _edit(self, op: str) -> None:
        ed = self.current()
        if ed is None or isinstance(QApplication.focusWidget(), (QLineEdit, QPlainTextEdit)):
            return
        ed.edit_op(op)

    def save_documents(self) -> None:
        for d in self._docs():
            if d.is_modified() and (not isinstance(d, IconEditor) or d.doc.path is not None):
                d.save()

    def _title(self, w) -> None:
        i = self.win.tabs.indexOf(w)
        if i >= 0:
            name = "Resources" if isinstance(w, ResourceEditor) else w.path.name
            self.win.tabs.setTabText(i, name + ("*" if w.is_modified() else ""))

    def _register(self, ed: IconEditor, key: str) -> IconEditor:
        ed.modifiedChanged.connect(lambda _m, e=ed: self._title(e))
        ed.saved.connect(lambda e=ed: self._after_save(e))
        self.editors[key] = ed
        return ed

    def open_image(self, path: Path) -> IconEditor | None:
        win = self.win
        path = Path(path).resolve()
        key = str(path).lower()
        ed = self.editors.get(key)
        if ed is not None and (not self._alive(ed) or win.tabs.indexOf(ed) < 0):
            self.editors.pop(key, None)
            ed = None
        if ed is None:
            try:
                ed = IconEditor(path=path)
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(win, "Image Editor", f"Cannot open {path.name}:\n{e}")
                return None
            ed.setToolTip(str(path))
            self._register(ed, key)
        win._show_tab(ed, path.name)
        self._title(ed)
        ed.canvas.setFocus()
        return ed

    def open_dialog(self) -> None:
        start = str(self.win.project.folder) if self.win.project is not None else ""
        f, _ = QFileDialog.getOpenFileName(self.win, "Open Image", start, FILTER_OPEN)
        if f:
            self.open_image(Path(f))

    def new_image(self, kind: str = "icon", name: str | None = None, folder: Path | None = None,
                  ask: bool = True) -> IconEditor | None:
        """A new icon / cursor / image. In a project it is saved straight into Resources/ (and added to the
        project resources); without a project it stays untitled until Save As."""
        win = self.win
        dlg = NewImageDialog(win, kind)
        if name:
            dlg.name.setText(name)
        if ask and dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        doc = dlg.make_document()
        stem = Path(dlg.name.text().strip() or "Image1").stem
        ed = IconEditor(doc)
        if folder is None and win.project is not None:
            folder = Path(win.project.folder) / FOLDER
        if folder is not None:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{stem}{dlg.extension()}"
            i = 2
            while path.exists():
                path = folder / f"{stem}{i}{dlg.extension()}"
                i += 1
            doc.save(path)
            if win.project is not None and _rel(win, path):
                self.add_to_resources(path)
            key = str(path.resolve()).lower()
        else:
            key = f"untitled:{id(ed)}"
        self._register(ed, key)
        win._show_tab(ed, ed.path.name)
        self._title(ed)
        return ed

    def _after_save(self, ed: IconEditor) -> None:
        old = next((k for k, v in self.editors.items() if v is ed), None)
        new = str(ed.doc.path.resolve()).lower()
        if old != new:
            self.editors.pop(old, None)
            self.editors[new] = ed
        ed.setToolTip(str(ed.doc.path))
        self._title(ed)
        self._refresh_res_editor()
        try:
            self.win.statusBar().showMessage(f"Saved {ed.doc.path.name}", 3000)
        except Exception:  # noqa: BLE001
            pass

    # ---------------------------------------------------------------- resources
    def open_resources(self) -> ResourceEditor | None:
        win = self.win
        if win.project is None:
            QMessageBox.information(win, "Resources", "Open a project first.")
            return None
        folder = Path(win.project.folder)
        ed = self.res_editor
        if ed is not None and (not self._alive(ed) or win.tabs.indexOf(ed) < 0 or
                               Path(ed.res.folder).resolve() != folder.resolve()):
            self.res_editor = ed = None
        if ed is None:
            ed = ResourceEditor(folder, open_image=self.open_image)
            ed.open_file = lambda p: win.open_any_file(p)
            ed.modifiedChanged.connect(lambda _m, e=ed: self._title(e))
            ed.saved.connect(lambda: self._after_res_save())
            self.res_editor = ed
        win._show_tab(ed, "Resources")
        self._title(ed)
        return ed

    def _refresh_res_editor(self) -> None:
        ed = self.res_editor
        if ed is not None and self._alive(ed):
            ed.refresh_from_disk()

    def _after_res_save(self) -> None:
        self._add_generated_module()

    def _add_generated_module(self) -> None:
        """resources.py shows in Solution Explorer (a module of the project; nothing imports it until the
        user writes ``import resources``)."""
        p = self.win.project
        if p is None or not (Path(p.folder) / "resources.py").exists():
            return
        if "resources.py" not in p.modules and str(p.language).startswith("python"):
            p.modules.append("resources.py")
            p.save()
            try:
                self.win._fill_solution()
            except Exception:  # noqa: BLE001
                pass

    def add_to_resources(self, path: Path, name: str | None = None) -> str | None:
        win = self.win
        if win.project is None:
            return None
        res = ProjectResources.load(win.project.folder)
        r = res.add_file(path, name=name)
        res.save()
        self._add_generated_module()
        self._refresh_res_editor()
        return r.name

    def add_current_to_resources(self) -> None:
        ed = self.current()
        if ed is None or ed.doc.path is None:
            return
        if ed.is_modified():
            ed.save()
        n = self.add_to_resources(ed.doc.path)
        if n:
            self.win.log(f"Added {ed.doc.path.name} to the project resources as '{n}'")

    # ---------------------------------------------------------------- icons of the form / application
    def _image_rel(self, path: Path | None) -> str | None:
        ed = self.current()
        if path is None:
            if ed is None or ed.doc.path is None:
                return None
            if ed.is_modified():
                ed.save()
            path = ed.doc.path
        rel = _rel(self.win, path)
        if rel is None:
            QMessageBox.information(self.win, "Icon", "Save the image inside the project folder first "
                                                      f"(for example in {FOLDER}/).")
        return rel

    def set_form_icon(self, path: Path | None = None, form: str | None = None, ask: bool = True) -> bool:
        """Form.Icon = the image (saved inside the project); the form's designer code is regenerated."""
        win = self.win
        if win.project is None:
            return False
        rel = self._image_rel(path)
        if rel is None:
            return False
        forms = list(win.project.forms)
        if not forms:
            QMessageBox.information(win, "Icon", "The project has no forms.")
            return False
        if form is None:
            default = self._last_form if self._last_form in forms else (win.project.startup or forms[0])
            if ask and len(forms) > 1:
                form, ok = QInputDialog.getItem(win, "Set as Form Icon", "Form:", forms,
                                                forms.index(default) if default in forms else 0, False)
                if not ok:
                    return False
            else:
                form = default
        doc = win._doc(form)
        doc.set_prop(None, "Icon", rel)
        win._save_form(form)
        win.log(f"{form}.Icon = {rel}")
        return True

    def set_app_icon(self, path: Path | None = None) -> bool:
        """The application icon: project.radproj "icon" and the Publish / installer icon (publish.json)."""
        win = self.win
        p = win.project
        if p is None:
            return False
        rel = self._image_rel(path)
        if rel is None:
            return False
        p.extra["icon"] = rel
        p.save()
        try:
            from ..deploy import config as dcfg
            cfg = dcfg.load(Path(p.folder), p.name)
            cfg.icon = rel
            dcfg.save(Path(p.folder), cfg)
        except Exception as e:  # noqa: BLE001
            win.log(f"[image editor] publish settings: {e}")
        win.log(f"Application icon = {rel} (Build > Publish / installer use it)")
        return True

    # ---------------------------------------------------------------- Solution Explorer
    def _add_tree_nodes(self) -> None:
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
            if project is None or getattr(project, "kind", "app") == "website" or \
                    callable(getattr(project, "fill_solution_tree", None)):     # foreign projects: own tree
                continue
            if any((it.child(i).data(0, ROLE) or ("",))[0] == "resources" for i in range(it.childCount())):
                continue
            pos = 1 if it.childCount() and (it.child(0).data(0, ROLE) or ("",))[0] == "references" else 0
            ri = QTreeWidgetItem(["Resources"])
            ri.setData(0, ROLE, ("resources", str(project.folder)))
            ri.setData(0, PROJECT_ROLE, key)
            ri.setToolTip(0, "Project resources: strings, images, icons, files - double-click to open")
            ri.setIcon(0, win.style().standardIcon(win.style().StandardPixmap.SP_DirIcon))
            res = ProjectResources.load(project.folder)
            for _k, r in res.pictures():
                ci = QTreeWidgetItem([r.file])
                ci.setData(0, ROLE, ("resource_file", str(res.res_dir / r.file)))
                ci.setData(0, PROJECT_ROLE, key)
                ci.setToolTip(0, f"{r.name} - double-click to edit in the Image Editor")
                ri.addChild(ci)
            it.insertChild(pos, ri)

    def _on_tree_dclick(self, item, _col) -> None:
        data = item.data(0, ROLE)
        if not data:
            return
        if data[0] == "resources":
            key = item.data(0, Qt.ItemDataRole.UserRole + 10)
            st = getattr(self.win, "_pstates", {}).get(key)
            if st and st.get("project") is not None and st["project"] is not self.win.project:
                try:
                    self.win.activate_project(st["project"])
                except Exception:  # noqa: BLE001
                    pass
            self.open_resources()
        elif data[0] == "resource_file":
            self.open_image(Path(data[1]))


def install(win) -> None:
    win.image_feature = ImageFeature(win)
