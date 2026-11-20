"""Resources designer (Project > Resources) and the VS 2005 style *Select Resource* dialog that the
Properties window shows for Image / Icon properties."""
from __future__ import annotations

import shutil
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QImage, QPixmap
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout,
                             QHeaderView, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                             QPushButton, QRadioButton, QStackedWidget, QTableWidget, QTableWidgetItem,
                             QToolBar, QVBoxLayout, QWidget)

from .. import theme
from .resources import FOLDER, KINDS, ProjectResources

TITLES = {"strings": "Strings", "images": "Images", "icons": "Icons", "files": "Files"}
PICTURE_FILTER = "Pictures (*.png *.gif *.jpg *.jpeg *.bmp *.ico *.cur);;All files (*)"


def load_picture(path: Path, size: int = 64) -> QPixmap:
    """A thumbnail of any picture resource (.ico/.cur through radide.imaging.ico: largest frame)."""
    img = QImage()
    try:
        if path.suffix.lower() in (".ico", ".cur"):
            from . import ico
            frames, _c = ico.load(path)
            best = max(frames, key=lambda f: f.size[0])
            img = ico.pil_to_qimage(best.image)
        else:
            img = QImage(str(path))
    except Exception:  # noqa: BLE001
        img = QImage()
    if img.isNull():
        pm = QPixmap(size, size)
        pm.fill(QColor(theme.color("alt_base")))
        return pm
    mode = (Qt.TransformationMode.FastTransformation if img.width() <= size
            else Qt.TransformationMode.SmoothTransformation)
    return QPixmap.fromImage(img.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, mode))


# ---------------------------------------------------------------------- Resources designer
class ResourceEditor(QWidget):
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()

    def __init__(self, project_folder: Path, open_image=None, new_image=None, parent=None):
        """*open_image(path)* opens a picture in the Icon / Image Editor; *new_image(kind, path)* creates a
        new picture there (kind "icon" | "png")."""
        super().__init__(parent)
        self.res = ProjectResources.load(project_folder)
        self.open_image = open_image
        self.new_image = new_image
        self._modified = False
        self._loading = False
        self._build()
        self.reload_lists()

    @property
    def path(self) -> Path:
        return self.res.json_path

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        tb = QToolBar()
        self.kind = QComboBox()
        for k in KINDS:
            self.kind.addItem(TITLES[k], k)
        self.kind.setToolTip("Resource type (Ctrl+1 .. Ctrl+4)")
        tb.addWidget(QLabel(" "))
        tb.addWidget(self.kind)
        tb.addSeparator()
        self.a_add = tb.addAction("Add Resource", self.add)
        self.a_add_file = tb.addAction("Add Existing File...", self.add_existing)
        self.a_new_pic = tb.addAction("Add New Image...", self.add_new_picture)
        tb.addSeparator()
        tb.addAction("Edit", self.edit_current)
        tb.addAction("Rename", self.rename_current)
        tb.addAction("Remove", self.remove_current)
        tb.addSeparator()
        tb.addAction("Save", self.save)
        lay.addWidget(tb)
        hint = QLabel(f"Saved in {FOLDER}/resources.json. Python projects get resources.py: "
                      "<code>import resources as R</code> - <code>R.strings.Name</code>, "
                      "<code>R.images.Name</code>, <code>R.photo(\"Name\")</code> (tk), "
                      "<code>R.pixmap(\"Name\")</code> (Qt).")
        hint.setWordWrap(True)
        theme.role(hint, "help")
        lay.addWidget(hint)
        self.stack = QStackedWidget()
        self.strings = QTableWidget(0, 3)
        self.strings.setHorizontalHeaderLabels(["Name", "Value", "Comment"])
        self.strings.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.strings.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.strings.itemChanged.connect(self._on_string_changed)
        self.stack.addWidget(self.strings)
        self.lists: dict[str, QListWidget] = {}
        for k in ("images", "icons"):
            lw = QListWidget()
            lw.setViewMode(QListWidget.ViewMode.IconMode)
            lw.setIconSize(QSize(64, 64))
            lw.setGridSize(QSize(110, 104))
            lw.setResizeMode(QListWidget.ResizeMode.Adjust)
            lw.setMovement(QListWidget.Movement.Static)
            lw.itemDoubleClicked.connect(lambda _it: self.edit_current())
            lw.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            lw.customContextMenuRequested.connect(lambda pos, w=lw: self._menu(w, pos))
            self.lists[k] = lw
            self.stack.addWidget(lw)
        self.files = QTableWidget(0, 3)
        self.files.setHorizontalHeaderLabels(["Name", "File", "Comment"])
        self.files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.files.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.files.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.files.itemDoubleClicked.connect(lambda _it: self.edit_current())
        self.stack.addWidget(self.files)
        lay.addWidget(self.stack, 1)
        self.kind.currentIndexChanged.connect(self._on_kind)
        self._on_kind()

    def current_kind(self) -> str:
        return self.kind.currentData()

    def _on_kind(self) -> None:
        k = self.current_kind()
        self.stack.setCurrentIndex(KINDS.index(k))
        self.a_add.setText("Add String" if k == "strings" else "Add Existing File...")
        self.a_add_file.setVisible(k == "strings")
        self.a_new_pic.setVisible(k in ("images", "icons"))
        self.a_new_pic.setText("Add New Icon..." if k == "icons" else "Add New Image...")

    # ---------------------------------------------------------------- lists
    def reload_lists(self) -> None:
        self._loading = True
        self.strings.setRowCount(0)
        for r in self.res.strings:
            row = self.strings.rowCount()
            self.strings.insertRow(row)
            for c, v in enumerate((r.name, r.value, r.comment)):
                self.strings.setItem(row, c, QTableWidgetItem(v))
        for k, lw in self.lists.items():
            lw.clear()
            for r in getattr(self.res, k):
                it = QListWidgetItem(QIcon(load_picture(self.res.res_dir / r.file)), r.name)
                it.setToolTip(f"{FOLDER}/{r.file}")
                it.setData(Qt.ItemDataRole.UserRole, r.name)
                lw.addItem(it)
        self.files.setRowCount(0)
        for r in self.res.files:
            row = self.files.rowCount()
            self.files.insertRow(row)
            for c, v in enumerate((r.name, f"{FOLDER}/{r.file}", r.comment)):
                it = QTableWidgetItem(v)
                it.setData(Qt.ItemDataRole.UserRole, r.name)
                self.files.setItem(row, c, it)
        self._loading = False

    def _on_string_changed(self, it: QTableWidgetItem) -> None:
        if self._loading:
            return
        row, col = it.row(), it.column()
        if row >= len(self.res.strings):
            return
        r = self.res.strings[row]
        text = it.text()
        if col == 0:
            if text != r.name:
                new = self.res.rename(r.name, text or "String")
                if new != text:
                    self._loading = True
                    it.setText(new)
                    self._loading = False
        elif col == 1:
            r.value = text
        else:
            r.comment = text
        self.set_modified(True)

    def _menu(self, lw, pos) -> None:
        m = QMenu(self)
        m.addAction("Open in Image Editor", self.edit_current)
        m.addAction("Rename", self.rename_current)
        m.addAction("Remove", self.remove_current)
        m.addAction("Copy Path", self.copy_path)
        m.exec(lw.mapToGlobal(pos))

    def selected_name(self) -> str | None:
        k = self.current_kind()
        if k == "strings":
            row = self.strings.currentRow()
            return self.res.strings[row].name if 0 <= row < len(self.res.strings) else None
        if k == "files":
            it = self.files.item(self.files.currentRow(), 0)
            return it.data(Qt.ItemDataRole.UserRole) if it else None
        it = self.lists[k].currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    # ---------------------------------------------------------------- commands
    def add(self) -> None:
        if self.current_kind() == "strings":
            self.res.add_string("String1", "")
            self.set_modified(True)
            self.reload_lists()
            self.strings.setCurrentCell(self.strings.rowCount() - 1, 1)
            self.strings.editItem(self.strings.item(self.strings.rowCount() - 1, 1))
        else:
            self.add_existing()

    def add_existing(self, files: list[str] | None = None) -> list:
        k = self.current_kind()
        if files is None:
            filt = PICTURE_FILTER if k in ("images", "icons") else "All files (*)"
            files, _ = QFileDialog.getOpenFileNames(self, "Add Existing File", str(self.res.folder), filt)
        added = []
        for f in files or []:
            added.append(self.res.add_file(f, kind=None if k == "strings" else k))
        if added:
            self.set_modified(True)
            self.reload_lists()
        return added

    def add_new_picture(self) -> None:
        k = self.current_kind()
        name, ok = QInputDialog.getText(self, "New " + ("Icon" if k == "icons" else "Image"), "Name:",
                                        text="Icon1" if k == "icons" else "Image1")
        if not ok or not name.strip():
            return
        ext = ".ico" if k == "icons" else ".png"
        self.res.res_dir.mkdir(parents=True, exist_ok=True)
        path = self.res.res_dir / f"{Path(name.strip()).stem}{ext}"
        from .document import ImageDocument
        doc = ImageDocument.new_icon((16, 32, 48, 256)) if k == "icons" else ImageDocument.new_image(64, 64)
        if not path.exists():
            doc.save(path)
        self.res.add_file(path, name=name.strip(), kind=k)
        self.set_modified(True)
        self.save()
        self.reload_lists()
        if callable(self.open_image):
            self.open_image(path)

    def edit_current(self) -> None:
        name = self.selected_name()
        if not name:
            return
        k, r = self.res.find(name)
        if k == "strings":
            return
        p = self.res.res_dir / r.file
        if k in ("images", "icons") and callable(self.open_image):
            self.open_image(p)
        elif callable(getattr(self, "open_file", None)):
            self.open_file(p)

    def rename_current(self) -> None:
        name = self.selected_name()
        if not name:
            return
        new, ok = QInputDialog.getText(self, "Rename Resource", "New name:", text=name)
        if ok and new.strip() and new.strip() != name:
            self.res.rename(name, new.strip())
            self.set_modified(True)
            self.reload_lists()

    def remove_current(self) -> None:
        name = self.selected_name()
        if not name:
            return
        k, r = self.res.find(name)
        delete = False
        if r.file:
            ans = QMessageBox.question(self, "Remove Resource", f"Remove '{name}'.\n\nAlso delete the file "
                                       f"{FOLDER}/{r.file}?", QMessageBox.StandardButton.Yes |
                                       QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            if ans == QMessageBox.StandardButton.Cancel:
                return
            delete = ans == QMessageBox.StandardButton.Yes
        self.res.remove(name, delete)
        self.set_modified(True)
        self.reload_lists()

    def copy_path(self) -> None:
        from PyQt6.QtWidgets import QApplication
        name = self.selected_name()
        hit = self.res.find(name) if name else None
        if hit and hit[1].file:
            QApplication.clipboard().setText(self.res.project_path(hit[1]))

    # ---------------------------------------------------------------- document protocol
    def is_modified(self) -> bool:
        return self._modified

    def set_modified(self, m: bool) -> None:
        if m != self._modified:
            self._modified = m
            self.modifiedChanged.emit(m)

    def save(self) -> bool:
        try:
            self.res.save()
        except OSError as e:
            QMessageBox.warning(self, "Resources", f"Cannot save the resources:\n{e}")
            return False
        self.set_modified(False)
        self.saved.emit()
        return True

    def maybe_close(self) -> bool:
        if not self._modified:
            return True
        r = QMessageBox.question(self, "Resources", "Save changes to the project resources?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save:
            return self.save()
        return r == QMessageBox.StandardButton.Discard

    def refresh_from_disk(self) -> None:
        if not self._modified:
            self.res = ProjectResources.load(self.res.folder)
            self.reload_lists()


# ---------------------------------------------------------------------- Select Resource dialog
class SelectResourceDialog(QDialog):
    """Like VS 2005: *Local resource* (a file copied into the project) or *Project resource file*
    (pick from Resources/resources.json, Import... adds to it). ``value`` is the path to store in the
    property (relative to the project) or "" for (none)."""

    def __init__(self, project_folder: Path, current: str = "", prop: str = "Image", parent=None,
                 edit_image=None):
        super().__init__(parent)
        self.setWindowTitle("Select Resource")
        self.folder = Path(project_folder)
        self.res = ProjectResources.load(self.folder)
        self.value = current or ""
        self.edit_image = edit_image
        self.resize(560, 380)
        lay = QVBoxLayout(self)
        body = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Resource context"))
        self.r_local = QRadioButton("Local resource:")
        left.addWidget(self.r_local)
        lb = QHBoxLayout()
        b_imp_local = QPushButton("Import...")
        b_imp_local.clicked.connect(self.import_local)
        b_clear = QPushButton("Clear")
        b_clear.clicked.connect(self.clear)
        lb.addWidget(b_imp_local)
        lb.addWidget(b_clear)
        lb.addStretch(1)
        left.addLayout(lb)
        self.r_project = QRadioButton(f"Project resource file:  {FOLDER}/resources.json")
        left.addWidget(self.r_project)
        self.list = QListWidget()
        self.list.setIconSize(QSize(24, 24))
        self.list.currentItemChanged.connect(self._on_pick)
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        left.addWidget(self.list, 1)
        pb = QHBoxLayout()
        b_imp = QPushButton("Import...")
        b_imp.setToolTip("Add a picture to the project resources")
        b_imp.clicked.connect(self.import_project)
        pb.addWidget(b_imp)
        if callable(edit_image):
            b_new = QPushButton("New Icon...")
            b_new.setToolTip("Draw a new icon in the Icon Editor (added to the resources)")
            b_new.clicked.connect(self.new_icon)
            pb.addWidget(b_new)
        pb.addStretch(1)
        left.addLayout(pb)
        body.addLayout(left, 1)
        right = QVBoxLayout()
        self.preview = QLabel()
        self.preview.setFixedSize(200, 200)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        theme.role(self.preview, "sample")
        right.addWidget(self.preview)
        self.path_lbl = QLabel()
        self.path_lbl.setWordWrap(True)
        theme.role(self.path_lbl, "muted")
        right.addWidget(self.path_lbl)
        right.addStretch(1)
        body.addLayout(right)
        lay.addLayout(body, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.r_project.toggled.connect(lambda on: self.list.setEnabled(on))
        self.fill()
        names = {self.res.project_path(r): r.name for _k, r in self.res.pictures()}
        if self.value in names or not self.value:
            self.r_project.setChecked(True)
            self._select(names.get(self.value))
        else:
            self.r_local.setChecked(True)
            self.list.setEnabled(False)
        self._show(self.value)

    def fill(self) -> None:
        self.list.clear()
        none = QListWidgetItem("(none)")
        none.setData(Qt.ItemDataRole.UserRole, "")
        self.list.addItem(none)
        for _k, r in self.res.pictures():
            it = QListWidgetItem(QIcon(load_picture(self.res.res_dir / r.file, 24)), r.name)
            it.setData(Qt.ItemDataRole.UserRole, self.res.project_path(r))
            it.setToolTip(self.res.project_path(r))
            self.list.addItem(it)

    def _select(self, name: str | None) -> None:
        for i in range(self.list.count()):
            it = self.list.item(i)
            if (name is None and i == 0) or it.text() == name:
                self.list.setCurrentRow(i)
                return

    def _on_pick(self, it, _prev=None) -> None:
        if it is not None and self.r_project.isChecked():
            self.value = it.data(Qt.ItemDataRole.UserRole)
            self._show(self.value)

    def _show(self, rel: str) -> None:
        if rel:
            p = self.folder / rel
            self.preview.setPixmap(load_picture(p, 190))
            self.path_lbl.setText(rel + ("" if p.exists() else "  (missing)"))
        else:
            self.preview.clear()
            self.preview.setText("(none)")
            self.path_lbl.setText("")

    def import_local(self, path: str | None = None) -> None:
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Import local resource", str(self.folder), PICTURE_FILTER)
        if not path:
            return
        src = Path(path)
        try:
            rel = src.resolve().relative_to(self.folder.resolve())
        except ValueError:
            dst = self.folder / FOLDER / src.name
            dst.parent.mkdir(exist_ok=True)
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            rel = dst.relative_to(self.folder)
        self.value = rel.as_posix()
        self.r_local.setChecked(True)
        self._show(self.value)

    def import_project(self, path: str | None = None) -> None:
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Import to project resources", str(self.folder),
                                                  PICTURE_FILTER)
        if not path:
            return
        r = self.res.add_file(path)
        self.res.save()
        self.fill()
        self.r_project.setChecked(True)
        self._select(r.name)

    def new_icon(self) -> None:
        name, ok = QInputDialog.getText(self, "New Icon", "Name:", text="AppIcon")
        if not ok or not name.strip():
            return
        from .document import ImageDocument
        p = self.folder / FOLDER / f"{Path(name.strip()).stem}.ico"
        p.parent.mkdir(exist_ok=True)
        if not p.exists():
            ImageDocument.new_icon((16, 32, 48, 256)).save(p)
        r = self.res.add_file(p, name=name.strip(), kind="icons")
        self.res.save()
        self.value = self.res.project_path(r)
        self.accept()
        self.edit_image(p)

    def clear(self) -> None:
        self.value = ""
        self._show("")


__all__ = ["ResourceEditor", "SelectResourceDialog", "load_picture"]
