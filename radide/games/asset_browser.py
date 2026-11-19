"""Game Assets dock: images (thumbnails), sprite sheets, tilesets and sounds of the current scene,
plus the image/sound files of the project folder that the scene does not use yet.

Double-click an image or sprite sheet -> a sprite in the middle of the view (or drag it onto the
canvas); a tileset -> used by the selected tile layer; a sound -> plays it."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QMimeData, QSize, Qt, QUrl
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QMenu, QMessageBox, QToolButton, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import theme
from .canvas import ASSET_MIME

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
SOUND_EXT = {".wav", ".ogg", ".mp3", ".flac"}
GROUPS = (("images", "Images"), ("spritesheets", "Sprite sheets"), ("tilesets", "Tilesets"), ("sounds", "Sounds"))
ROLE = Qt.ItemDataRole.UserRole


class _AssetTree(QTreeWidget):
    def mimeData(self, items):
        md = QMimeData()
        data = items[0].data(0, ROLE) if items else None
        if data and data[0] in ("images", "spritesheets", "file"):
            md.setData(ASSET_MIME, f"{data[0]}:{data[1]}".encode("utf-8"))
        return md

    def mimeTypes(self):
        return [ASSET_MIME]


class AssetBrowser(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = None
        self._player = None
        self._effect = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        bar = QHBoxLayout()
        bar.setSpacing(2)

        def tb(text, slot, tip):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.setAutoRaise(True)
            b.clicked.connect(slot)
            bar.addWidget(b)
            return b
        self.b_import = tb("Import", self._import_menu, "Import an image, sprite sheet, tileset or sound")
        self.b_add = tb("Add", self.add_selected, "Add the selected image / sprite sheet as a sprite")
        self.b_edit = tb("Edit", self.edit_selected, "Edit the sprite sheet animations / tileset")
        self.b_play = tb("Play", self.play_selected, "Play the selected sound")
        self.b_remove = tb("Remove", self.remove_selected, "Remove the asset from the scene")
        bar.addStretch(1)
        lay.addLayout(bar)
        self.tree = _AssetTree()
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(QSize(40, 40))
        self.tree.setDragEnabled(True)
        self.tree.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        self.tree.itemDoubleClicked.connect(self._activate)
        self.tree.currentItemChanged.connect(self._update_buttons)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        lay.addWidget(self.tree, 1)
        self.hint = theme.role(QLabel("Open a .scene file to see its assets."), "muted")
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)
        self.setMinimumWidth(160)
        self.refresh()

    def sizeHint(self):
        return QSize(250, 400)

    # ---------------------------------------------------------------- binding
    def set_editor(self, editor) -> None:
        if self.editor is editor:
            return
        if self.editor is not None:
            try:
                self.editor.assetsChanged.disconnect(self.refresh)
            except (TypeError, RuntimeError):
                pass
        self.editor = editor
        if editor is not None:
            editor.assetsChanged.connect(self.refresh)
        self.refresh()

    def _thumb(self, pm: QPixmap | None, src=None) -> QIcon:
        if pm is None or pm.isNull():
            return QIcon()
        if src is not None:
            pm = pm.copy(*src)
        return QIcon(pm.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))

    def refresh(self) -> None:
        self.tree.clear()
        ed = self.editor
        self.setEnabled(ed is not None)
        self.hint.setVisible(ed is None)
        if ed is None:
            return
        a = ed.scene.assets
        used_files = set()
        for kind, label in GROUPS:
            group = QTreeWidgetItem([f"{label} ({len(a.get(kind, {}))})"])
            group.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.tree.addTopLevelItem(group)
            for aid, val in a.get(kind, {}).items():
                path = val if isinstance(val, str) else (val or {}).get("image", "")
                used_files.add(str(ed.resolve(path)).lower())
                it = QTreeWidgetItem([aid])
                it.setData(0, ROLE, (kind, aid))
                if kind == "images":
                    it.setIcon(0, self._thumb(ed.pixmap(path)))
                    it.setToolTip(0, path)
                elif kind == "spritesheets":
                    pm = ed.pixmap(path)
                    fw, fh = int(val.get("frame_w") or 32), int(val.get("frame_h") or 32)
                    it.setIcon(0, self._thumb(pm, (0, 0, fw, fh)))
                    it.setText(0, f"{aid}   [{', '.join(val.get('animations', {})) or 'no animations'}]")
                    it.setToolTip(0, f"{path}  frames {fw}x{fh}")
                elif kind == "tilesets":
                    it.setIcon(0, self._thumb(ed.pixmap(path)))
                    it.setText(0, f"{aid}   [{val.get('tile_w')}x{val.get('tile_h')}]")
                    it.setToolTip(0, path)
                else:
                    it.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_MediaVolume))
                    it.setToolTip(0, path)
                group.addChild(it)
            group.setExpanded(True)
        # project files not used by the scene yet
        files = []
        root = ed.base_dir
        if root and root.is_dir():
            for p in sorted(root.rglob("*")):
                if len(files) > 300:
                    break
                if p.suffix.lower() in IMAGE_EXT | SOUND_EXT and p.is_file() and \
                        not any(part.startswith(".") or part in ("build", "dist", "__pycache__", ".venv")
                                for part in p.relative_to(root).parts[:-1]) and str(p).lower() not in used_files:
                    files.append(p)
        if files:
            group = QTreeWidgetItem([f"Project files ({len(files)})"])
            group.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.tree.addTopLevelItem(group)
            for p in files:
                rel = p.relative_to(root).as_posix()
                it = QTreeWidgetItem([rel])
                it.setData(0, ROLE, ("file", rel))
                if p.suffix.lower() in IMAGE_EXT:
                    it.setIcon(0, self._thumb(ed.pixmap(rel)))
                else:
                    it.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_MediaVolume))
                group.addChild(it)
            group.setExpanded(True)
        self._update_buttons()

    def _current(self):
        it = self.tree.currentItem()
        return it.data(0, ROLE) if it is not None else None

    def _update_buttons(self, *_a) -> None:
        d = self._current()
        kind = d[0] if d else None
        is_sound_file = kind == "file" and Path(d[1]).suffix.lower() in SOUND_EXT
        self.b_add.setEnabled(kind in ("images", "spritesheets") or (kind == "file" and not is_sound_file))
        self.b_edit.setEnabled(kind in ("spritesheets", "tilesets"))
        self.b_play.setEnabled(kind == "sounds" or is_sound_file)
        self.b_remove.setEnabled(kind in ("images", "spritesheets", "tilesets", "sounds"))

    # ---------------------------------------------------------------- actions
    def select_asset(self, kind: str, aid: str) -> bool:
        for i in range(self.tree.topLevelItemCount()):
            g = self.tree.topLevelItem(i)
            for j in range(g.childCount()):
                if g.child(j).data(0, ROLE) == (kind, aid):
                    self.tree.setCurrentItem(g.child(j))
                    return True
        return False

    def _activate(self, item, _col=0) -> None:
        d = item.data(0, ROLE)
        if not d or self.editor is None:
            return
        kind, aid = d
        if kind in ("images", "spritesheets"):
            self.editor.add_from_asset(kind, aid)
        elif kind == "tilesets":
            self.editor.use_tileset(aid)
        elif kind == "sounds":
            self.play_selected()
        elif kind == "file":
            if Path(aid).suffix.lower() in SOUND_EXT:
                self.play_selected()
            else:
                self.editor.add_from_asset("file", aid)

    def add_selected(self) -> None:
        it = self.tree.currentItem()
        if it is not None:
            self._activate(it)

    def edit_selected(self) -> None:
        d = self._current()
        if d and self.editor is not None:
            if d[0] == "spritesheets":
                self.editor.edit_spritesheet(d[1])
            elif d[0] == "tilesets":
                self.editor.import_tileset(edit_id=d[1])

    def remove_selected(self) -> None:
        d = self._current()
        if d and self.editor is not None and d[0] != "file":
            self.editor.remove_asset(d[0], d[1])

    def play_selected(self) -> None:
        d = self._current()
        if not d or self.editor is None:
            return
        path = self.editor.scene.assets.get("sounds", {}).get(d[1]) if d[0] == "sounds" else d[1]
        if path:
            self.play_file(self.editor.resolve(path))

    def play_file(self, path: Path) -> None:
        try:
            from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect
        except ImportError:
            QMessageBox.information(self, "Play", "Qt Multimedia is not available.")
            return
        url = QUrl.fromLocalFile(str(path))
        if path.suffix.lower() == ".wav":
            self._effect = QSoundEffect(self)
            self._effect.setSource(url)
            self._effect.play()
            return
        if self._player is None:
            self._player = QMediaPlayer(self)
            self._audio = QAudioOutput(self)
            self._player.setAudioOutput(self._audio)
        self._player.setSource(url)
        self._player.play()

    def _import_menu(self) -> None:
        if self.editor is None:
            return
        m = QMenu(self)
        m.addAction("Image...", self.editor.import_image)
        m.addAction("Sprite sheet...", lambda: self.editor.edit_spritesheet(None))
        m.addAction("Tileset...", self.editor.import_tileset)
        m.addAction("Sound...", self.import_sound)
        m.exec(self.b_import.mapToGlobal(self.b_import.rect().bottomLeft()))

    def import_sound(self) -> None:
        if self.editor is None:
            return
        f, _ = QFileDialog.getOpenFileName(self, "Import sound", str(self.editor.base_dir),
                                           "Sounds (*.wav *.ogg *.mp3 *.flac)")
        if f:
            self.editor.add_asset_file("sounds", f)

    def _menu(self, pos) -> None:
        it = self.tree.itemAt(pos)
        if it is not None:
            self.tree.setCurrentItem(it)
        m = QMenu(self)
        for b in (self.b_add, self.b_edit, self.b_play, self.b_remove):
            if b.isEnabled():
                m.addAction(b.text(), b.click)
        m.addSeparator()
        m.addAction("Import...", self._import_menu)
        m.exec(self.tree.viewport().mapToGlobal(pos))
