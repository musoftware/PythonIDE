"""The game scene designer: a document tab for `<Scene>.scene` files of game projects.

    [toolbar: Play | Select Paint Erase Rect Fill | Sprite Text Area | Sheet Tileset | grid snap ...]
    [ canvas (level, grid, camera)          | Layers / Tiles tabs          ]
    [                                       | Properties (scene inspector) ]
    [status: cursor, cell, tile, zoom]

Everything edits the neutral Scene model (radide/games/model.py); every change is one undo step
(snapshots of the scene JSON - scenes are small).  Double-click a sprite opens/creates its handler
in `<Scene>.py` (VB style); Play saves and runs the game through the IDE (F5).

The editor talks to the IDE through a *host* (see FileHost) so it also works on its own (tests).
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from PyQt6.QtCore import QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QPixmap, QUndoCommand, QUndoStack
from PyQt6.QtWidgets import (QApplication, QComboBox, QFileDialog, QGraphicsView, QHBoxLayout, QHeaderView, QLabel,
                             QMessageBox, QPushButton, QScrollArea, QSplitter, QTabWidget, QToolBar, QToolButton,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import theme
from .canvas import TOOLS, SceneCanvas
from .inspector import Inspector
from .model import (DEFAULT_TILE, EVENT_ARGS, Layer, Scene, SceneObject, default_event, handler_name,
                    rename_in_code, validate)
from .tiles import IMAGE_FILTER, TilePalette, TilesetDialog

CLIP_KEY = "radide-scene-objects"
ZOOMS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]


# ====================================================================== handlers in <Scene>.py
def find_handler_line(code: str, name: str) -> int:
    """0-based line of `def name(` / `func name(` / `function name(` (JS) / `func name args` (Ring), or -1."""
    for i, line in enumerate(code.splitlines()):
        if re.match(rf"^\s*(def|func|function)\s+{re.escape(name)}\s*(\(|\s|$)", line, re.I):
            return i
    return -1


def ensure_handler(code: str, name: str, args: str = "", ext: str = ".py",
                   scene_class: str | None = None) -> tuple[str, int, bool]:
    """Find or add the handler *name*.  Returns (code, 0-based line of its body, added?).

    Python: a module-level `def name(args):` - or a method of `class <scene_class>` when the scene
    code is written as a class.  GDScript (.gd): `func name(args):`."""
    i = find_handler_line(code, name)
    if i >= 0:
        return code, i + 1, False
    lines = code.rstrip("\n").split("\n") if code.strip() else []
    if ext == ".gd":
        lines += ["", "", f"func {name}({args}):", "\tpass"]
        return "\n".join(lines) + "\n", len(lines) - 1, True
    if ext in (".js", ".ring"):         # HTML5 Canvas (radide/games/html5.py) / Ring (radide/games/ring_game.py)
        from . import html5, ring_game
        mod = html5 if ext == ".js" else ring_game
        new, body = mod.add_handler(code, name, mod.EVENT_ARGS.get(name.rpartition("_")[2], ""))
        return new, body, True
    cls = None
    if scene_class:
        cls = next((k for k, ln in enumerate(lines) if re.match(rf"^class\s+{re.escape(scene_class)}\b.*:\s*$", ln)),
                   None)
    if cls is not None:
        end = cls + 1
        while end < len(lines) and (not lines[end].strip() or lines[end][:1] in (" ", "\t")):
            end += 1
        while end > cls + 1 and not lines[end - 1].strip():
            end -= 1
        sig = f"    def {name}(self{', ' + args if args else ''}):"
        lines[end:end] = ["", sig, "        pass"]
        return "\n".join(lines) + "\n", end + 2, True
    # module level: above a trailing `if __name__ == "__main__":` block when there is one
    main = next((k for k, ln in enumerate(lines) if re.match(r"^if\s+__name__\s*==", ln)), None)
    stub = [f"def {name}({args}):", "    pass"]
    try:            # the same "# Player: touches another object (other)" line as the generated handlers
        from .codegen import EVENT_DOCS
        owner, _, event = name.rpartition("_")
        if EVENT_DOCS.get(event):
            stub.insert(0, f"# {owner if owner != 'Scene' else 'the scene'}: {EVENT_DOCS[event]}")
    except ImportError:
        pass
    if main is None:
        lines += ["", ""] + stub
        return "\n".join(lines) + "\n", len(lines) - 1, True
    at = main
    while at > 0 and not lines[at - 1].strip():
        at -= 1
    lines[at:at] = ["", ""] + stub + [""]
    return "\n".join(lines) + "\n", at + 1 + len(stub), True


class FileHost:
    """Default host: reads/writes the scene code file on disk (used when there is no IDE)."""

    def __init__(self):
        self.shown: tuple | None = None            # (path, line) of the last handler shown

    def get_code(self, path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def show_code(self, path: Path, code: str | None, line: int) -> None:
        if code is not None:
            path.write_text(code, encoding="utf-8")
        self.shown = (path, line)

    def play(self, editor) -> bool:
        return False

    def log(self, text: str) -> None:
        print(text)


class _Snapshot(QUndoCommand):
    def __init__(self, editor, before: dict, after: dict, text: str):
        super().__init__(text)
        self.editor, self.before, self.after = editor, before, after
        self._first = True

    def redo(self):
        if self._first:
            self._first = False
            return
        self.editor.restore(self.after)

    def undo(self):
        self.editor.restore(self.before)


# ====================================================================== the editor
class SceneEditor(QWidget):
    modifiedChanged = pyqtSignal(bool)
    assetsChanged = pyqtSignal()
    selectionChanged = pyqtSignal()
    playRequested = pyqtSignal()
    saved = pyqtSignal()

    def __init__(self, path, host=None, code_ext: str = ".py", parent=None, plugin=None):
        super().__init__(parent)
        self.path = Path(path)
        self.plugin = plugin          # the game language plugin (scene_code_file, new_scene_code ...)
        self.base_dir = self.path.parent
        self.host = host or FileHost()
        self.code_ext = code_ext
        if self.path.exists():
            self.scene = Scene.load(self.path)
        else:
            self.scene = Scene.new(re.sub(r"\W", "_", self.path.stem) or "Scene1")
        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(lambda clean: self.modifiedChanged.emit(not clean))
        self._pending: dict | None = None
        self._pixmaps: dict[str, tuple[float, QPixmap | None]] = {}
        self.current_tile = 0
        self.show_collision = True
        self.snap = True
        follow_layer, _o = self.scene.find(self.scene.camera.get("follow") or "")
        self._active = follow_layer.name if follow_layer is not None else next(
            (ly.name for ly in reversed(self.scene.layers) if ly.type == "sprites"),
            self.scene.layers[0].name if self.scene.layers else "")
        self._inspector_pending = False
        self._build_ui()
        self.canvas.rebuild()
        self.refresh_layers()
        self.refresh_palette()
        QTimer.singleShot(0, self.fit_view)

    # ---------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        tb = self.toolbar = QToolBar()
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        sp = self.style().StandardPixmap
        self.a_play = tb.addAction(self.style().standardIcon(sp.SP_MediaPlay), "Play", self.play)
        self.a_play.setToolTip("Save and run the game (like Ctrl+F5; F5 runs it with the debugger)")
        tb.addSeparator()
        self.tool_actions: dict[str, QAction] = {}
        group = QActionGroup(self)
        for tool, label, key, tip in (("select", "Select", "V", "Select, move, resize and rotate objects"),
                                      ("paint", "Paint", "B", "Paint tiles (right-click picks a tile)"),
                                      ("erase", "Erase", "E", "Erase tiles"),
                                      ("rect", "Rect", "R", "Fill a rectangle of tiles"),
                                      ("fill", "Fill", "G", "Bucket fill an area of tiles")):
            a = tb.addAction(label, lambda t=tool: self.set_tool(t))
            a.setCheckable(True)
            a.setToolTip(f"{tip} ({key})")
            group.addAction(a)
            self.tool_actions[tool] = a
        self.tool_actions["select"].setChecked(True)
        tb.addSeparator()
        add = QToolButton()
        add.setText("Add")
        add.setToolTip("Add a sprite, text or area")
        add.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        from PyQt6.QtWidgets import QMenu
        m = QMenu(add)
        m.addAction("Sprite from image...", self.import_image)
        m.addAction("Text", lambda: self.add_object("text"))
        m.addAction("Area (trigger zone)", lambda: self.add_object("area"))
        m.addAction("Particle emitter", lambda: __import__("radide.games.particles", fromlist=["add_emitter"])
                    .add_emitter(self))
        m.addAction("Particle Editor...", lambda: __import__("radide.games.particles", fromlist=["ParticleEditor"])
                    .ParticleEditor(self).exec())
        m.addSeparator()
        m.addAction("Tile layer", lambda: self.add_layer("tiles"))
        m.addAction("Sprite layer", lambda: self.add_layer("sprites"))
        m.addAction("UI layer", lambda: self.add_layer("ui"))
        add.setMenu(m)
        tb.addWidget(add)
        tb.addAction("Sprite Sheet...", lambda: self.edit_spritesheet(None)).setToolTip(
            "Import a sprite sheet and make animations")
        tb.addAction("Tileset...", self.import_tileset).setToolTip("Import a tileset image for the tile layers")
        tb.addSeparator()
        self.a_undo = tb.addAction(self.style().standardIcon(sp.SP_ArrowBack), "", self.undo_stack.undo)
        self.a_undo.setToolTip("Undo (Ctrl+Z)")
        self.a_redo = tb.addAction(self.style().standardIcon(sp.SP_ArrowForward), "", self.undo_stack.redo)
        self.a_redo.setToolTip("Redo (Ctrl+Y)")
        self.undo_stack.canUndoChanged.connect(self.a_undo.setEnabled)
        self.undo_stack.canRedoChanged.connect(self.a_redo.setEnabled)
        self.a_undo.setEnabled(False)
        self.a_redo.setEnabled(False)
        tb.addAction("Front", lambda: self.reorder(True)).setToolTip("Bring to front")
        tb.addAction("Back", lambda: self.reorder(False)).setToolTip("Send to back")
        tb.addSeparator()
        # toggled(bool), not addAction(text, slot): that connects triggered() WITHOUT the checked state, so
        # clicking Grid / Snap / Collision raised "missing 1 required positional argument: 'on'" (action crawler)
        self.a_grid = tb.addAction("Grid")
        self.a_grid.setCheckable(True)
        self.a_grid.setChecked(True)
        self.a_grid.toggled.connect(self._toggle_grid)
        self.a_snap = tb.addAction("Snap")
        self.a_snap.setCheckable(True)
        self.a_snap.setChecked(True)
        self.a_snap.toggled.connect(lambda on: setattr(self, "snap", on))
        self.a_snap.setToolTip("Snap to the tile grid (hold Alt to place freely)")
        self.a_coll = tb.addAction("Collision")
        self.a_coll.setCheckable(True)
        self.a_coll.setChecked(True)
        self.a_coll.toggled.connect(self._toggle_collision)
        self.a_coll.setToolTip("Show the collision tile layers in red")
        self.zoom_box = QComboBox()
        self.zoom_box.setEditable(False)
        for z in ZOOMS:
            self.zoom_box.addItem(f"{int(z * 100)}%", z)
        self.zoom_box.setCurrentIndex(ZOOMS.index(1.0))
        self.zoom_box.activated.connect(lambda i: self.canvas.set_zoom(self.zoom_box.itemData(i)))
        tb.addWidget(self.zoom_box)
        tb.addAction("Fit", self.fit_view).setToolTip("Zoom to show the whole level")
        lay.addWidget(tb)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.canvas = SceneCanvas(self)
        split.addWidget(self.canvas)
        side = QSplitter(Qt.Orientation.Vertical)
        self.side_tabs = QTabWidget()
        # layers
        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(2, 2, 2, 2)
        self.layers = QTreeWidget()
        self.layers.setHeaderLabels(["Layer", "Show", "Lock", "Collide"])
        self.layers.setRootIsDecorated(False)
        hdr = self.layers.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.layers.currentItemChanged.connect(self._on_layer_row)
        self.layers.itemChanged.connect(self._on_layer_item)
        ll.addWidget(self.layers, 1)
        row = QHBoxLayout()
        for text, slot, tip in (("+Tiles", lambda: self.add_layer("tiles"), "New tile layer"),
                                ("+Sprites", lambda: self.add_layer("sprites"), "New sprite layer"),
                                ("+UI", lambda: self.add_layer("ui"), "New UI layer (score, buttons)"),
                                ("▲", lambda: self.move_layer(1), "Move the layer up (drawn later)"),
                                ("▼", lambda: self.move_layer(-1), "Move the layer down"),
                                ("✕", self.delete_layer, "Delete the layer")):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.setAutoRaise(True)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        row.setSpacing(1)
        ll.addLayout(row)
        self.side_tabs.addTab(lw, "Layers")
        # tiles
        tw = QWidget()
        tl = QVBoxLayout(tw)
        tl.setContentsMargins(2, 2, 2, 2)
        self.tileset_label = theme.role(QLabel(""), "muted")
        self.tileset_label.setWordWrap(True)        # a long tileset name must not widen the panel
        tl.addWidget(self.tileset_label)
        self.palette = TilePalette()
        self.palette.tileSelected.connect(self._on_tile_picked)
        psa = QScrollArea()
        psa.setWidget(self.palette)
        tl.addWidget(psa, 1)
        trow = QHBoxLayout()
        b = QPushButton("Tileset...")
        b.clicked.connect(self.import_tileset)
        trow.addWidget(b)
        for tool in ("paint", "erase", "rect", "fill"):
            tbtn = QToolButton()
            tbtn.setDefaultAction(self.tool_actions[tool])
            trow.addWidget(tbtn)
        trow.addStretch(1)
        tl.addLayout(trow)
        try:                                            # Terrain row: auto-tiling brush (radide/games/autotile.py)
            from .autotile import install_ui as _install_autotile
            _install_autotile(self, tl)
        except Exception:  # noqa: BLE001 - the designer works without it
            self.autotile_terrain = ""
        self.side_tabs.addTab(tw, "Tiles")
        side.addWidget(self.side_tabs)
        self.inspector = Inspector(self)
        side.addWidget(self.inspector)
        side.setSizes([260, 420])
        split.addWidget(side)
        side.setMinimumWidth(290)                   # room for the Tiles tab buttons (no overlap)
        self.canvas.setMinimumWidth(200)
        split.setCollapsible(0, False)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        split.setSizes([900, 330])
        self._split = split
        self._sized = False
        lay.addWidget(split, 1)
        self.status = theme.role(QLabel(""), "muted")
        self.status.setContentsMargins(6, 2, 6, 2)
        lay.addWidget(self.status)

    # ---------------------------------------------------------------- files / assets
    def resolve(self, path: str) -> Path:
        p = Path(path or "")
        return p if p.is_absolute() else self.base_dir / p

    def pixmap(self, path: str | None) -> QPixmap | None:
        if not path:
            return None
        p = self.resolve(path)
        try:
            mt = p.stat().st_mtime
        except OSError:
            return None
        hit = self._pixmaps.get(str(p))
        if hit is not None and hit[0] == mt:
            return hit[1]
        pm = QPixmap(str(p))
        pm = None if pm.isNull() else pm
        self._pixmaps[str(p)] = (mt, pm)
        return pm

    def rel_asset_path(self, path) -> str:
        """Copy a file into <scene folder>/assets when it is outside the project; return its
        project-relative path (posix)."""
        p = Path(path)
        if not p.is_absolute():
            return p.as_posix()
        try:
            return p.resolve().relative_to(self.base_dir.resolve()).as_posix()
        except ValueError:
            dest_dir = self.base_dir / "assets"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / p.name
            if not dest.exists() or dest.read_bytes() != p.read_bytes():
                k = 2
                while dest.exists() and dest.read_bytes() != p.read_bytes():
                    dest = dest_dir / f"{p.stem}{k}{p.suffix}"
                    k += 1
                shutil.copyfile(p, dest)
            return dest.relative_to(self.base_dir).as_posix()

    def add_asset_file(self, kind: str, path, asset_id: str | None = None, **extra) -> str:
        """Register an image / sound / tileset / sprite sheet file as a scene asset; returns its id."""
        rel = self.rel_asset_path(path)
        aid = asset_id or self.scene.unique_asset_id(kind, Path(rel).stem)

        def do():
            if kind in ("images", "sounds"):
                self.scene.assets.setdefault(kind, {})[aid] = rel
            else:
                self.scene.assets.setdefault(kind, {})[aid] = {"image": rel, **extra}
        self.change(f"Import {kind[:-1]}", do, structural=True)
        return aid

    def remove_asset(self, kind: str, aid: str) -> None:
        def do():
            self.scene.assets.get(kind, {}).pop(aid, None)
            for ly in self.scene.layers:
                if kind == "tilesets" and ly.tileset == aid:
                    ly.tileset = ""
                for o in ly.objects:
                    if kind == "images" and o.image == aid:
                        o.image = ""
                    if kind == "spritesheets" and o.spritesheet == aid:
                        o.spritesheet, o.animation = "", ""
                    for b in o.behaviours:
                        if kind == "sounds" and b.get("sound") == aid:
                            b["sound"] = ""
        self.change(f"Remove {kind[:-1]}", do, structural=True)

    def import_image(self) -> str | None:
        f, _ = QFileDialog.getOpenFileName(self, "Sprite image", str(self.base_dir), IMAGE_FILTER)
        if not f:
            return None
        aid = self.add_asset_file("images", f)
        self.add_from_asset("images", aid)
        return aid

    def import_tileset(self, edit_id: str | None = None, *, path: str | None = None, tile_w: int | None = None,
                       tile_h: int | None = None) -> str | None:
        """Import (or edit) a tileset.  With *path* given no dialog is shown (tests, scripts)."""
        if isinstance(edit_id, bool):            # QAction.triggered(checked)
            edit_id = None
        old = self.scene.assets.get("tilesets", {}).get(edit_id or "", {})
        if path is None:
            dlg = TilesetDialog(self, str(self.resolve(old["image"])) if old else "",
                                old.get("tile_w", DEFAULT_TILE), old.get("tile_h", DEFAULT_TILE), edit_id or "")
            if not dlg.exec():
                return None
            path, tile_w, tile_h, aid = dlg.values()
        else:
            aid = edit_id or ""
        rel = self.rel_asset_path(path)
        aid = aid or edit_id or self.scene.unique_asset_id("tilesets", Path(rel).stem)
        tw, th = int(tile_w or DEFAULT_TILE), int(tile_h or DEFAULT_TILE)

        def do():
            self.scene.assets.setdefault("tilesets", {})[aid] = {"image": rel, "tile_w": tw, "tile_h": th}
            ly = self.active_layer()
            if ly is None or ly.type != "tiles":
                ly = next((x for x in self.scene.layers if x.type == "tiles" and not x.tileset), None)
            if ly is None:
                ly = Layer(self.scene.unique_layer_name("Tiles"), "tiles")
                self.scene.layers.insert(0, ly)
            self._attach_tileset(ly, aid)
            self._active = ly.name
        self.change("Import tileset", do, structural=True)
        self.side_tabs.setCurrentIndex(1)
        return aid

    def _attach_tileset(self, ly: Layer, aid: str) -> None:
        ly.tileset = aid
        tw, th = self.scene.tile_size(ly)
        if not ly.data or all(v < 0 for r in ly.data for v in r):
            ly.data = []
            ly.resize(-(-self.scene.width // tw), -(-self.scene.height // th))

    def use_tileset(self, aid: str, layer: Layer | None = None) -> None:
        ly = layer or self.active_layer()

        def do():
            target = ly
            if target is None or target.type != "tiles":
                target = next((x for x in self.scene.layers if x.type == "tiles"), None)
                if target is None:
                    target = Layer(self.scene.unique_layer_name("Tiles"), "tiles")
                    self.scene.layers.insert(0, target)
            self._attach_tileset(target, aid or "")
            self._active = target.name
        self.change("Tileset", do, structural=True)

    def edit_spritesheet(self, sheet_id: str | None = None, *, sheet: dict | None = None) -> str | None:
        """Sprite sheet + animations dialog (or, with *sheet* given, store it without a dialog)."""
        if isinstance(sheet_id, bool):
            sheet_id = None
        if sheet is None:
            from .animation_editor import SpriteSheetDialog
            cur = self.scene.assets.get("spritesheets", {}).get(sheet_id or "")
            dlg = SpriteSheetDialog(cur, sheet_id or "", resolve=self.pixmap, base_dir=str(self.base_dir), parent=self)
            if sheet_id:
                dlg.sid.setReadOnly(True)
            if not dlg.exec():
                return None
            new_id, sheet = dlg.result_sheet()
        else:
            new_id = sheet_id or Path(sheet.get("image", "sheet")).stem
        if not sheet.get("image"):
            return None
        sheet = dict(sheet, image=self.rel_asset_path(self.resolve(sheet["image"]))
                     if Path(sheet["image"]).is_absolute() else sheet["image"])
        sid = sheet_id or (new_id if new_id not in self.scene.assets.get("spritesheets", {})
                           else self.scene.unique_asset_id("spritesheets", new_id))

        def do():
            self.scene.assets.setdefault("spritesheets", {})[sid] = sheet
            for _ly, o in self.scene.objects():
                if o.spritesheet == sid and o.animation not in sheet.get("animations", {}):
                    o.animation = next(iter(sheet.get("animations", {})), "")
        self.change("Sprite sheet", do, structural=True)
        return sid

    # ---------------------------------------------------------------- layers
    def active_layer(self) -> Layer | None:
        return self.scene.layer(self._active) or (self.scene.layers[-1] if self.scene.layers else None)

    def set_active_layer(self, name: str) -> None:
        if self.scene.layer(name) is not None and name != self._active:
            self._active = name
            self.refresh_layers()
            self.refresh_palette()
            self.canvas.viewport().update()
            self._schedule_inspector()

    def refresh_layers(self) -> None:
        self.layers.blockSignals(True)
        self.layers.clear()
        cur = None
        for ly in reversed(self.scene.layers):
            n = f"{len(ly.objects)} objects" if ly.type != "tiles" else                 f"{ly.cols}x{ly.rows} tiles, tileset '{ly.tileset or '-'}'"
            it = QTreeWidgetItem([f"{ly.name} ({ly.type})", "", "", ""])
            it.setToolTip(0, f"{ly.name}: {ly.type} layer, {n}")
            it.setData(0, Qt.ItemDataRole.UserRole, ly.name)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(1, Qt.CheckState.Checked if ly.visible else Qt.CheckState.Unchecked)
            it.setCheckState(2, Qt.CheckState.Checked if ly.locked else Qt.CheckState.Unchecked)
            it.setCheckState(3, Qt.CheckState.Checked if ly.collision else Qt.CheckState.Unchecked)
            self.layers.addTopLevelItem(it)
            if ly.name == self._active:
                cur = it
        if cur is not None:
            self.layers.setCurrentItem(cur)
        self.layers.blockSignals(False)

    def _on_layer_row(self, cur, _prev) -> None:
        if cur is not None:
            self.set_active_layer(cur.data(0, Qt.ItemDataRole.UserRole))

    def _on_layer_item(self, item, col) -> None:
        ly = self.scene.layer(item.data(0, Qt.ItemDataRole.UserRole))
        if ly is None or col not in (1, 2, 3):
            return
        on = item.checkState(col) == Qt.CheckState.Checked
        attr = {1: "visible", 2: "locked", 3: "collision"}[col]
        if getattr(ly, attr) != on:
            QTimer.singleShot(0, lambda: self.change(f"Layer {attr}", lambda: setattr(ly, attr, on)))

    def add_layer(self, ltype: str) -> Layer:
        base = {"tiles": "Tiles", "sprites": "Sprites", "ui": "UI"}[ltype]
        ly = Layer(self.scene.unique_layer_name(base), ltype)
        if ltype == "tiles":
            ref = next((x for x in self.scene.layers if x.type == "tiles" and x.tileset), None)
            if ref is not None:
                ly.tileset = ref.tileset
                ly.resize(ref.cols, ref.rows)
            else:
                ly.resize(-(-self.scene.width // DEFAULT_TILE), -(-self.scene.height // DEFAULT_TILE))

        def do():
            act = self.scene.layer(self._active)
            idx = self.scene.layers.index(act) + 1 if act is not None else len(self.scene.layers)
            self.scene.layers.insert(idx, ly)
            self._active = ly.name
        self.change("Add layer", do, structural=True)
        return ly

    def delete_layer(self) -> None:
        ly = self.active_layer()
        if ly is None or len(self.scene.layers) <= 1:
            return
        if (ly.objects or any(v >= 0 for r in ly.data for v in r)) and QApplication.instance() and \
                self.isVisible() and QMessageBox.question(
                    self, "Delete layer", f"Delete layer '{ly.name}' and everything on it?") != \
                QMessageBox.StandardButton.Yes:
            return

        def do():
            i = self.scene.layers.index(ly)
            self.scene.layers.remove(ly)
            self._active = self.scene.layers[max(0, i - 1)].name
        self.change("Delete layer", do, structural=True)

    def move_layer(self, delta: int) -> None:
        ly = self.active_layer()
        if ly is None:
            return
        i = self.scene.layers.index(ly)
        j = i + delta
        if 0 <= j < len(self.scene.layers):
            self.change("Move layer", lambda: self.scene.layers.insert(j, self.scene.layers.pop(i)), structural=True)

    def rename_layer(self, ly: Layer, new: str) -> bool:
        if not new or self.scene.layer(new) is not None:
            return False

        def do():
            ly.name = new
            self._active = new
        self.change("Rename layer", do, structural=True)
        return True

    # ---------------------------------------------------------------- tiles
    def refresh_palette(self) -> None:
        ly = self.active_layer()
        if ly is None or ly.type != "tiles":
            ly = next((x for x in self.scene.layers if x.type == "tiles"), None)
        ts = self.scene.assets.get("tilesets", {}).get(ly.tileset) if ly is not None else None
        if ts:
            self.palette.set_tileset(self.pixmap(ts.get("image")), int(ts.get("tile_w") or 32),
                                     int(ts.get("tile_h") or 32))
            self.tileset_label.setText(f"Layer '{ly.name}' - tileset '{ly.tileset}' "
                                       f"({ts.get('tile_w')}x{ts.get('tile_h')}). Tile {self.current_tile}")
        else:
            self.palette.set_tileset(None, 32, 32)
            self.tileset_label.setText("Select a tile layer and import a tileset." if ly is None else
                                       f"Layer '{ly.name}' has no tileset yet.")
        self.palette.current = self.current_tile
        self.palette.update()

    def _on_tile_picked(self, idx: int) -> None:
        self.current_tile = idx
        if self.canvas.tool in ("select", "erase"):
            self.set_tool("paint")
        self.refresh_palette()

    def set_current_tile(self, idx: int) -> None:
        self.current_tile = idx
        self.refresh_palette()

    def grid_size(self) -> tuple[int, int]:
        ly = self.active_layer()
        if ly is None or ly.type != "tiles":
            ly = next((x for x in self.scene.layers if x.type == "tiles" and x.tileset), None)
        return self.scene.tile_size(ly) if ly is not None else (DEFAULT_TILE, DEFAULT_TILE)

    def snap_size(self) -> int:
        if not self.snap or QApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier:
            return 0
        return self.grid_size()[0]

    def set_tool(self, tool: str) -> None:
        if tool not in TOOLS:
            return
        self.canvas.tool = tool
        self.tool_actions[tool].setChecked(True)
        if tool == "select":
            self.canvas.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.canvas.viewport().unsetCursor()
        else:
            self.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.canvas.scene().clearSelection()
            self.canvas.viewport().setCursor(Qt.CursorShape.CrossCursor)
            ly = self.active_layer()
            if ly is None or ly.type != "tiles":
                t = next((x for x in reversed(self.scene.layers) if x.type == "tiles"), None)
                if t is not None:
                    self.set_active_layer(t.name)
            self.side_tabs.setCurrentIndex(1)
        self.canvas.viewport().update()

    # ---------------------------------------------------------------- undo machinery
    def begin_edit(self) -> None:
        if self._pending is None:
            self._pending = self.scene.to_dict()

    def commit_pending(self, text: str) -> bool:
        before, self._pending = self._pending, None
        if before is None:
            return False
        after = self.scene.to_dict()
        if before == after:
            return False
        self.undo_stack.push(_Snapshot(self, before, after, text))
        self.refresh_layers()
        self.inspector.refresh_values()
        return True

    def change(self, text: str, fn, structural: bool = False) -> bool:
        """Run *fn* (which edits self.scene) as one undo step and refresh the views."""
        if self._pending is not None:
            self.commit_pending("Edit")
        self.begin_edit()
        fn()
        changed = self.commit_pending(text)
        self.canvas.rebuild()
        self.refresh_layers()
        self.refresh_palette()
        if structural:
            self.assetsChanged.emit()
            self._schedule_inspector()
        else:
            self.inspector.refresh_values()
        return changed

    def restore(self, data: dict) -> None:
        self.scene = Scene.from_dict(data)
        if self.scene.layer(self._active) is None and self.scene.layers:
            self._active = self.scene.layers[-1].name
        self.canvas.rebuild()
        self.refresh_layers()
        self.refresh_palette()
        self.assetsChanged.emit()
        self._schedule_inspector()

    def undo(self) -> None:
        self.undo_stack.undo()

    def redo(self) -> None:
        self.undo_stack.redo()

    def _schedule_inspector(self) -> None:
        if not self._inspector_pending:
            self._inspector_pending = True
            QTimer.singleShot(0, self._rebuild_inspector)

    def _rebuild_inspector(self) -> None:
        self._inspector_pending = False
        try:
            self.inspector.rebuild()
        except RuntimeError:
            pass

    # ---------------------------------------------------------------- selection
    def selected_objects(self) -> list[SceneObject]:
        out = []
        for n in self.canvas.selected_names():
            _ly, o = self.scene.find(n)
            if o is not None:
                out.append(o)
        return out

    def select(self, names) -> None:
        self.canvas.select_names([names] if isinstance(names, str) else names)

    def on_selection_changed(self) -> None:
        objs = self.selected_objects()
        if objs:
            ly, _o = self.scene.find(objs[0].name)
            if ly is not None and ly.name != self._active:
                self._active = ly.name
                self.refresh_layers()
        self.selectionChanged.emit()
        self._schedule_inspector()

    def on_live_change(self) -> None:
        self.inspector.refresh_values()

    def on_cursor(self, x: float, y: float, cell) -> None:
        txt = f"X {int(x)}  Y {int(y)}"
        if cell is not None:
            ly = self.active_layer()
            txt += f"   cell {cell[0]},{cell[1]}  tile {ly.get(*cell) if ly else -1}"
        txt += f"   zoom {int(self.canvas.zoom * 100)}%   tool: {self.canvas.tool}"
        self.status.setText(txt)

    def on_zoom_changed(self, z: float) -> None:
        i = self.zoom_box.findData(z)
        if i < 0:
            self.zoom_box.setItemText(self.zoom_box.currentIndex(), f"{int(z * 100)}%")
        else:
            self.zoom_box.setCurrentIndex(i)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if not self._sized and self.width() > 600:
            self._sized = True
            side = min(360, max(260, self.width() // 4))
            self._split.setSizes([self.width() - side, side])
            QTimer.singleShot(0, self.fit_view)

    def fit_view(self) -> None:
        ww, wh = self.scene.world_size()
        vp = self.canvas.viewport().rect()
        if vp.width() < 50 or vp.height() < 50:
            return
        z = min((vp.width() - 40) / max(1, ww), (vp.height() - 40) / max(1, wh))
        z = max(0.1, min(4.0, z))
        self.canvas.set_zoom(z)
        self.canvas.centerOn(QPointF(ww / 2, wh / 2))

    def _toggle_grid(self, on: bool) -> None:
        self.canvas.show_grid = on
        self.canvas.viewport().update()

    def _toggle_collision(self, on: bool) -> None:
        self.show_collision = on
        for it in self.canvas.tile_items.values():
            it.update()

    # ---------------------------------------------------------------- objects
    def _object_layer(self) -> Layer:
        ly = self.active_layer()
        if ly is not None and ly.type in ("sprites", "ui") and not ly.locked:
            return ly
        ly = next((x for x in reversed(self.scene.layers) if x.type == "sprites" and not x.locked), None)
        if ly is None:
            ly = Layer(self.scene.unique_layer_name("Sprites"), "sprites")
            self.scene.layers.append(ly)
        return ly

    def add_object(self, kind: str = "sprite", pos: QPointF | None = None, *, image: str = "",
                   spritesheet: str = "", name: str = "", w: float | None = None, h: float | None = None,
                   layer: str | None = None) -> SceneObject:
        """Add a sprite / text / area (centred on *pos*, default: the middle of the view)."""
        pos = pos if pos is not None else self.canvas.view_center()
        base = name or {"text": "Label", "area": "Area"}.get(kind) or (image or spritesheet or "Sprite").capitalize()
        o = SceneObject(name=name or self.scene.unique_name(base), kind=kind)
        if kind == "sprite":
            o.image, o.spritesheet = image, spritesheet
            pm, fw, fh = None, None, None
            if spritesheet:
                sh = self.scene.assets.get("spritesheets", {}).get(spritesheet, {})
                fw, fh = sh.get("frame_w", 32), sh.get("frame_h", 32)
                o.animation = next(iter(sh.get("animations", {})), "")
            elif image:
                pm = self.pixmap(self.scene.assets.get("images", {}).get(image))
            o.w = w or fw or (pm.width() if pm else 32)
            o.h = h or fh or (pm.height() if pm else 32)
        elif kind == "text":
            o.text, o.w, o.h = "Score: 0", w or 160, h or 32
            o.props = {"ForeColor": "#FFFFFF", "FontSize": 24}
        else:
            o.w, o.h = w or 64, h or 64
        g = self.snap_size()
        o.x, o.y = pos.x() - o.w / 2, pos.y() - o.h / 2
        if g:
            o.x, o.y = round(o.x / g) * g, round(o.y / g) * g

        def do():
            ly = self.scene.layer(layer) if layer else None
            ly = ly or (self.scene.layer("UI") if kind == "text" and self.active_layer() and
                        self.active_layer().type == "tiles" else None) or self._object_layer()
            o.z = max((x.z for x in ly.objects), default=-1) + 1
            ly.objects.append(o)
            self._active = ly.name
        self.change(f"Add {kind}", do, structural=True)
        self.set_tool("select")
        self.select([o.name])
        return o

    def add_from_asset(self, kind: str, aid: str, pos: QPointF | None = None) -> SceneObject | None:
        if kind == "file":
            aid = self.add_asset_file("images", aid)
            kind = "images"
        if kind == "images" and aid in self.scene.assets.get("images", {}):
            return self.add_object("sprite", pos, image=aid)
        if kind == "spritesheets" and aid in self.scene.assets.get("spritesheets", {}):
            return self.add_object("sprite", pos, spritesheet=aid)
        return None

    def set_image(self, objs, aid: str) -> None:
        def do():
            for o in objs:
                o.image = aid
                if aid:
                    o.spritesheet, o.animation = "", ""
        self.change("Image", do, structural=True)

    def set_spritesheet(self, objs, sid: str) -> None:
        sheet = self.scene.assets.get("spritesheets", {}).get(sid, {})

        def do():
            for o in objs:
                o.spritesheet = sid
                if sid:
                    o.image = ""
                    o.animation = next(iter(sheet.get("animations", {})), "")
                    o.w, o.h = sheet.get("frame_w", o.w), sheet.get("frame_h", o.h)
                else:
                    o.animation = ""
        self.change("Sprite sheet", do, structural=True)

    def add_behaviour(self, objs, btype: str) -> None:
        def do():
            for o in objs:
                if o.behaviour(btype) is None:
                    o.add_behaviour(btype)
        self.change("Add behaviour", do, structural=True)

    def remove_behaviour(self, o: SceneObject, index: int) -> None:
        if 0 <= index < len(o.behaviours):
            self.change("Remove behaviour", lambda: o.behaviours.pop(index), structural=True)

    def rename_object(self, o: SceneObject, new: str) -> bool:
        new = new.strip()
        if not re.match(r"^[A-Za-z_]\w*$", new) or new in self.scene.names() or self.scene.layer(new):
            if self.isVisible():
                QMessageBox.warning(self, "Rename", f"'{new}' is not a valid, unused name.")
            self._schedule_inspector()
            return False
        old = o.name

        def do():
            o.name = new
            if self.scene.camera.get("follow") == old:
                self.scene.camera["follow"] = new
        self.change("Rename", do, structural=True)
        self.select([new])
        code = self.host.get_code(self.code_path)
        if code and re.search(rf"\b{re.escape(old)}_", code):
            self.host.show_code(self.code_path, rename_in_code(code, old, new), -1)
        return True

    def nudge(self, dx: float, dy: float) -> None:
        objs = self.selected_objects()
        if objs:
            self.change("Nudge", lambda: [(setattr(o, "x", o.x + dx), setattr(o, "y", o.y + dy)) for o in objs])

    def reorder(self, front: bool) -> None:
        objs = self.selected_objects()
        if not objs:
            return

        def do():
            for o in objs:
                ly, _ = self.scene.find(o.name)
                zs = [x.z for x in ly.objects if x is not o] or [0]
                o.z = max(zs) + 1 if front else min(zs) - 1
        self.change("Bring to front" if front else "Send to back", do)

    def delete_selected(self) -> None:
        names = set(self.canvas.selected_names())
        if not names:
            return

        def do():
            for ly in self.scene.layers:
                ly.objects = [o for o in ly.objects if o.name not in names]
            if self.scene.camera.get("follow") in names:
                self.scene.camera["follow"] = None
        self.change("Delete", do, structural=True)

    def copy_selected(self) -> bool:
        objs = self.selected_objects()
        if not objs:
            return False
        QApplication.clipboard().setText(json.dumps({CLIP_KEY: [o.to_dict() for o in objs]}, indent=1))
        return True

    def paste(self) -> list[str]:
        try:
            data = json.loads(QApplication.clipboard().text() or "{}")
            items = data.get(CLIP_KEY) if isinstance(data, dict) else None
        except ValueError:
            items = None
        if not items:
            return []
        g = self.snap_size() or 16
        new = []
        taken_pos = {(o.x, o.y) for _ly, o in self.scene.objects()}

        def do():
            ly = self._object_layer()
            for d in items:
                o = SceneObject.from_dict(d)
                o.name = self.scene.unique_name(o.name)
                while (o.x, o.y) in taken_pos:
                    o.x, o.y = o.x + g, o.y + g
                taken_pos.add((o.x, o.y))
                ly.objects.append(o)
                new.append(o.name)
            self._active = ly.name
        self.change("Paste", do, structural=True)
        self.set_tool("select")
        self.select(new)
        return new

    def edit_op(self, op: str) -> None:
        if op == "undo":
            self.undo()
        elif op == "redo":
            self.redo()
        elif op == "copy":
            self.copy_selected()
        elif op == "cut":
            if self.copy_selected():
                self.delete_selected()
        elif op == "paste":
            self.paste()
        elif op == "delete":
            self.delete_selected()
        elif op == "duplicate":
            if self.copy_selected():
                self.paste()
        elif op == "select_all":
            ly = self.active_layer()
            objs = ly.objects if ly is not None and ly.type != "tiles" else [o for _l, o in self.scene.objects()]
            self.select([o.name for o in objs])

    # ---------------------------------------------------------------- code (VB-style handlers)
    @property
    def code_path(self) -> Path:
        fn = getattr(self.plugin, "scene_code_file", None)
        if callable(fn):
            try:
                return self.base_dir / fn(self.path.stem)
            except Exception:  # noqa: BLE001
                pass
        return self.base_dir / f"{self.path.stem}{self.code_ext}"

    def code_text(self) -> str:
        try:
            return self.host.get_code(self.code_path)
        except OSError:
            return ""

    @staticmethod
    def has_handler(code: str, name: str) -> bool:
        return find_handler_line(code, name) >= 0

    def open_handler(self, obj: SceneObject | None, event: str) -> tuple[str, int]:
        name = handler_name(self.scene, obj, event)
        code = self.code_text()
        fresh = not code.strip()
        if fresh:            # a new <Scene>.py / .gd starts from the language's template (imports, help)
            try:
                gen = getattr(self.plugin, "new_scene_code", None)
                if callable(gen):
                    code = gen(self.scene.to_dict())
                elif self.code_ext == ".py":
                    from .codegen import new_scene_code
                    code = new_scene_code(self.scene.to_dict(), handlers=[])
            except Exception:  # noqa: BLE001
                code = ""
        new, line, added = ensure_handler(code, name, EVENT_ARGS.get(event, ""), self.code_ext,
                                          scene_class=self.path.stem)
        added = added or (fresh and bool(new.strip()))
        self.host.show_code(self.code_path, new if added else None, line)
        if added:
            self._schedule_inspector()          # the event turns bold
        return name, line

    def open_named_handler(self, name: str, args: str = "") -> int:
        """Open / create a handler by name (timers: Timer1_Tick)."""
        code = self.code_text()
        new, line, added = ensure_handler(code, name, args, self.code_ext, scene_class=self.path.stem)
        self.host.show_code(self.code_path, new if added else None, line)
        return line

    def add_timer(self, *_a, interval: int = 1000) -> str:
        timers = self.scene.extra.setdefault("timers", [])
        taken = {t.get("name") for t in timers} | self.scene.names()
        k = 1
        while f"Timer{k}" in taken:
            k += 1
        name = f"Timer{k}"
        self.change("Add timer", lambda: timers.append({"name": name, "interval": int(interval), "enabled": True}),
                    structural=True)
        return name

    def remove_timer(self, index: int) -> None:
        timers = self.scene.extra.get("timers") or []
        if 0 <= index < len(timers):
            self.change("Remove timer", lambda: timers.pop(index), structural=True)

    def open_default_handler(self, obj: SceneObject | None) -> tuple[str, int]:
        return self.open_handler(obj, default_event(obj))

    # ---------------------------------------------------------------- document
    def is_modified(self) -> bool:
        return not self.undo_stack.isClean()

    def problems(self) -> list[str]:
        return validate(self.scene)

    def save(self) -> bool:
        if self._pending is not None:
            self.commit_pending("Edit")
        self.scene.save(self.path)
        self.undo_stack.setClean()
        probs = self.problems()
        if probs:
            self.host.log(f"[scene {self.path.name}] " + "; ".join(probs))
        self.saved.emit()
        return True

    def maybe_close(self) -> bool:
        if not self.is_modified():
            return True
        r = QMessageBox.question(self, "Scene", f"Save changes to {self.path.name}?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Cancel:
            return False
        if r == QMessageBox.StandardButton.Save:
            return self.save()
        return True

    def play(self) -> None:
        self.save()
        if not self.host.play(self):
            self.playRequested.emit()
