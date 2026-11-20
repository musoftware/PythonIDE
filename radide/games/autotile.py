"""Auto-tiling (terrain sets) for the tilemap editor of the scene designer.

A *terrain* says which tiles of a tileset draw one kind of ground (grass, water, wall ...) for every
combination of neighbours, so you just paint "grass" and the edges and corners pick themselves::

    scene.assets["terrains"] = {"grass": {"tileset": "ground", "mode": "16" | "47",
                                          "tiles": {"<mask>": tile index, ...}, "name": "Grass"}}

* mode "16": the 4 side neighbours, mask = N 1 + E 2 + S 4 + W 8 (16 tiles). The standard layout
  ``rad16`` puts tile *mask* at index *mask* (a 4 x 4 sheet).
* mode "47" (blob): the 8 neighbours, N 1, NE 2, E 4, SE 8, S 16, SW 32, W 64, NW 128; a corner counts
  only when both of its sides are the same terrain, which leaves 47 different tiles. The standard layout
  ``rad47`` lists them in increasing mask order, 8 per row (``BLOB47``).

A cell belongs to a terrain when its tile is one of the terrain's tiles, so the map itself is the only
state; painting / erasing re-computes the cell and its 8 neighbours. ``make_template(...)`` draws a
ready-to-use terrain tileset (PNG) in the standard layout.

The pure functions work without Qt (tests, scripts); the Terrains dialog and the Tiles tab controls are
at the end (Qt).
"""
from __future__ import annotations

from pathlib import Path

N, NE, E, SE, S, SW, W, NW = 1, 2, 4, 8, 16, 32, 64, 128
_DIRS8 = ((0, -1, N), (1, -1, NE), (1, 0, E), (1, 1, SE), (0, 1, S), (-1, 1, SW), (-1, 0, W), (-1, -1, NW))
_DIRS4 = ((0, -1, 1), (1, 0, 2), (0, 1, 4), (-1, 0, 8))


def reduce47(mask: int) -> int:
    """Drop the corner bits whose two sides are not both set (blob rule)."""
    m = mask & (N | E | S | W)
    for corner, a, b in ((NE, N, E), (SE, S, E), (SW, S, W), (NW, N, W)):
        if mask & corner and mask & a and mask & b:
            m |= corner
    return m


BLOB47 = sorted({reduce47(m) for m in range(256)})
assert len(BLOB47) == 47
MODES = {"16": "16 tiles (sides only)", "47": "47 tiles (blob: sides and corners)"}


def standard_tiles(mode: str) -> dict[str, int]:
    """mask -> tile index of the standard layout (rad16 / rad47)."""
    if str(mode) == "47":
        return {str(m): i for i, m in enumerate(BLOB47)}
    return {str(m): m for m in range(16)}


def new_terrain(tileset: str, mode: str = "47", name: str = "") -> dict:
    return {"tileset": tileset, "mode": str(mode), "tiles": standard_tiles(mode), "name": name or "Terrain"}


def terrain_tiles(terrain: dict) -> set[int]:
    return {int(v) for v in (terrain.get("tiles") or {}).values() if int(v) >= 0}


def mask_at(data: list, c: int, r: int, member, mode: str) -> int:
    """The neighbour mask of cell (c, r); *member(c, r)* tells whether a cell is this terrain."""
    m = 0
    if str(mode) == "47":
        for dx, dy, bit in _DIRS8:
            if member(c + dx, r + dy):
                m |= bit
        return reduce47(m)
    for dx, dy, bit in _DIRS4:
        if member(c + dx, r + dy):
            m |= bit
    return m


def tile_for(terrain: dict, mask: int) -> int:
    """The tile for a mask (missing masks fall back to the fullest tile of the terrain)."""
    tiles = terrain.get("tiles") or {}
    if str(mask) in tiles:
        return int(tiles[str(mask)])
    mode = str(terrain.get("mode", "47"))
    full = 255 if mode == "47" else 15
    if mode == "47" and str(mask & (N | E | S | W)) in tiles:
        return int(tiles[str(mask & (N | E | S | W))])
    if str(full) in tiles:
        return int(tiles[str(full)])
    return int(next(iter(tiles.values()), 0))


def _grid(layer):
    data = layer.data if hasattr(layer, "data") else layer
    return data


def _member_fn(data, tiles: set[int], edge_is_terrain: bool = True):
    rows = len(data)

    def member(c, r):
        if r < 0 or r >= rows or c < 0 or c >= len(data[r]):
            return edge_is_terrain        # the map edge continues the terrain (no border at the edge)
        return data[r][c] in tiles
    return member


def retile_cells(layer, terrain: dict, cells, edge_is_terrain: bool | None = None) -> list[tuple[int, int]]:
    """Re-compute the tiles of *cells* that are this terrain; returns the cells that changed."""
    data = _grid(layer)
    tiles = terrain_tiles(terrain)
    if edge_is_terrain is None:            # terrain "edge": does the map edge continue the terrain?
        edge_is_terrain = bool(terrain.get("edge", True))
    member = _member_fn(data, tiles, edge_is_terrain)
    mode = str(terrain.get("mode", "47"))
    changed = []
    for c, r in cells:
        if 0 <= r < len(data) and 0 <= c < len(data[r]) and data[r][c] in tiles:
            t = tile_for(terrain, mask_at(data, c, r, member, mode))
            if data[r][c] != t:
                data[r][c] = t
                changed.append((c, r))
    return changed


def _around(cells) -> set[tuple[int, int]]:
    out = set()
    for c, r in cells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                out.add((c + dx, r + dy))
    return out


def paint(layer, terrain: dict, cells, erase: bool = False, edge_is_terrain: bool | None = None) -> list[tuple[int, int]]:
    """Paint (or erase) terrain on *cells* and fix the edges around them; returns every changed cell."""
    data = _grid(layer)
    tiles = terrain_tiles(terrain)
    if not tiles:
        return []
    fill = tile_for(terrain, 255 if str(terrain.get("mode", "47")) == "47" else 15)
    changed = set()
    for c, r in cells:
        if 0 <= r < len(data) and 0 <= c < len(data[r]):
            new = -1 if erase else (data[r][c] if data[r][c] in tiles else fill)
            if data[r][c] != new:
                data[r][c] = new
                changed.add((c, r))
    changed |= set(retile_cells(data, terrain, sorted(_around(cells)), edge_is_terrain))
    return sorted(changed)


def retile(layer, terrain: dict, edge_is_terrain: bool | None = None) -> list[tuple[int, int]]:
    """Re-compute every cell of the terrain on the whole layer (after editing the terrain's tiles)."""
    data = _grid(layer)
    cells = [(c, r) for r in range(len(data)) for c in range(len(data[r]))]
    return retile_cells(data, terrain, cells, edge_is_terrain)


def rect_cells(a, b) -> list[tuple[int, int]]:
    return [(c, r) for r in range(min(a[1], b[1]), max(a[1], b[1]) + 1)
            for c in range(min(a[0], b[0]), max(a[0], b[0]) + 1)]


def fill_cells(data, cell, tiles: set[int]) -> list[tuple[int, int]]:
    """The 4-connected region of *cell* (same tile, or same 'is this terrain')."""
    c0, r0 = cell
    if not (0 <= r0 < len(data) and 0 <= c0 < len(data[r0])):
        return []
    inside = data[r0][c0] in tiles
    target = data[r0][c0]
    seen, stack, out = set(), [cell], []
    while stack:
        c, r = stack.pop()
        if (c, r) in seen or not (0 <= r < len(data) and 0 <= c < len(data[r])):
            continue
        seen.add((c, r))
        v = data[r][c]
        if (v in tiles) != inside or (not inside and v != target):
            continue
        out.append((c, r))
        stack += [(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)]
    return out


def apply_tool(scene, layer, terrain_id: str, tool: str, cell, end_cell=None) -> list[tuple[int, int]]:
    """A tile tool (paint / erase / rect / fill) of the scene designer in terrain mode."""
    terrain = (scene.assets.get("terrains") or {}).get(terrain_id)
    if not terrain or cell is None:
        return []
    erase = tool == "erase"
    if tool in ("paint", "erase"):
        cells = [cell]
    elif tool == "rect":
        cells = rect_cells(cell, end_cell or cell)
    elif tool == "fill":
        cells = fill_cells(layer.data, cell, terrain_tiles(terrain))
    else:
        return []
    return paint(layer, terrain, cells, erase=erase)


# ====================================================================== template tileset (Qt drawing)
def make_template(path, mode: str = "47", tile: int = 32, color: str = "#5DBB4A", edge: str = "#2F6E2A",
                  under: str = "") -> Path:
    """Draw a terrain tileset in the standard layout (16 tiles 4 x 4, or 47 tiles 8 x 6) and save it as PNG.
    *color* fills the terrain, *edge* outlines its borders, *under* (optional) fills outside the borders."""
    from PyQt6.QtCore import QPointF, QRectF, Qt
    from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
    mode = str(mode)
    masks = BLOB47 if mode == "47" else list(range(16))
    cols = 8 if mode == "47" else 4
    rows = -(-len(masks) // cols)
    img = QImage(cols * tile, rows * tile, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    fill, line = QColor(color), QColor(edge)
    hi = fill.lighter(125)
    b = max(2.0, tile / 8)                  # border width
    for i, m in enumerate(masks):
        if mode == "16":
            full = m
            m8 = (N if m & 1 else 0) | (E if m & 2 else 0) | (S if m & 4 else 0) | (W if m & 8 else 0)
            m8 = reduce47(m8 | NE | SE | SW | NW)
        else:
            full = m
            m8 = m
        x0, y0 = (i % cols) * tile, (i // cols) * tile
        cell = QRectF(x0, y0, tile, tile)
        if under:
            p.fillRect(cell, QColor(under))
        n, e, s, w = (bool(m8 & N), bool(m8 & E), bool(m8 & S), bool(m8 & W))
        # the terrain area: inset on sides without a neighbour, rounded outer corners
        inset = b
        r = QRectF(x0 + (0 if w else inset), y0 + (0 if n else inset),
                   tile - (0 if w else inset) - (0 if e else inset), tile - (0 if n else inset) - (0 if s else inset))
        rad = tile / 4
        outline = QPainterPath()
        outline.moveTo(r.left() + (0 if (n or w) else rad), r.top())
        outline.lineTo(r.right() - (0 if (n or e) else rad), r.top())
        if not (n or e):
            outline.quadTo(QPointF(r.right(), r.top()), QPointF(r.right(), r.top() + rad))
        outline.lineTo(r.right(), r.bottom() - (0 if (s or e) else rad))
        if not (s or e):
            outline.quadTo(QPointF(r.right(), r.bottom()), QPointF(r.right() - rad, r.bottom()))
        outline.lineTo(r.left() + (0 if (s or w) else rad), r.bottom())
        if not (s or w):
            outline.quadTo(QPointF(r.left(), r.bottom()), QPointF(r.left(), r.bottom() - rad))
        outline.lineTo(r.left(), r.top() + (0 if (n or w) else rad))
        if not (n or w):
            outline.quadTo(QPointF(r.left(), r.top()), QPointF(r.left() + rad, r.top()))
        outline.closeSubpath()
        p.fillPath(outline, fill)
        # a few lighter specks so repeated tiles look like ground
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(hi)
        for k in range(3):
            sx = x0 + tile * (0.25 + 0.25 * k)
            sy = y0 + tile * (0.3 + 0.2 * ((k + full) % 3))
            if r.contains(QPointF(sx, sy)):
                p.drawEllipse(QPointF(sx, sy), tile / 16, tile / 16)
        # outline on the open sides
        pen = QPen(line, b / 1.5)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        if not n:
            p.drawLine(QPointF(r.left() + (0 if w else rad), r.top()), QPointF(r.right() - (0 if e else rad), r.top()))
        if not s:
            p.drawLine(QPointF(r.left() + (0 if w else rad), r.bottom()), QPointF(r.right() - (0 if e else rad), r.bottom()))
        if not w:
            p.drawLine(QPointF(r.left(), r.top() + (0 if n else rad)), QPointF(r.left(), r.bottom() - (0 if s else rad)))
        if not e:
            p.drawLine(QPointF(r.right(), r.top() + (0 if n else rad)), QPointF(r.right(), r.bottom() - (0 if s else rad)))
        for ok, (cx, cy, sx, sy) in ((not (n or w), (r.left(), r.top(), 1, 1)), (not (n or e), (r.right(), r.top(), -1, 1)),
                                     (not (s or e), (r.right(), r.bottom(), -1, -1)), (not (s or w), (r.left(), r.bottom(), 1, -1))):
            if ok:
                cp = QPainterPath()
                cp.moveTo(cx, cy + sy * rad)
                cp.quadTo(QPointF(cx, cy), QPointF(cx + sx * rad, cy))
                p.drawPath(cp)
        # inner corners (blob): a notch where both sides continue but the diagonal does not
        if mode == "47":
            nb = b          # the notch continues the inset edges of the two side neighbours
            for has, sx, sy in (((n and e and not m8 & NE), 1, 0), ((s and e and not m8 & SE), 1, 1),
                                ((s and w and not m8 & SW), 0, 1), ((n and w and not m8 & NW), 0, 0)):
                if not has:
                    continue
                nx = x0 + tile - nb if sx else x0
                ny = y0 + tile - nb if sy else y0
                nr = QRectF(nx, ny, nb, nb)
                if under:
                    p.fillRect(nr, QColor(under))
                else:
                    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                    p.fillRect(nr, Qt.GlobalColor.transparent)
                    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                p.setPen(QPen(line, b / 1.5))
                ix = nx if sx else nx + nb          # the inner vertical side of the notch
                iy = ny + nb if not sy else ny      # the inner horizontal side
                p.drawLine(QPointF(ix, ny), QPointF(ix, ny + nb))
                p.drawLine(QPointF(nx, iy), QPointF(nx + nb, iy))
    p.end()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path))
    return path


# ====================================================================== Qt: Terrains dialog + Tiles tab row
def install_ui(editor, tiles_layout) -> None:
    """Add the 'Terrain' row (auto-tile brush) under the tile palette of the scene designer."""
    from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton

    row = QHBoxLayout()
    row.addWidget(QLabel("Terrain:"))
    combo = QComboBox()
    combo.setToolTip("Auto-tile brush: paint a terrain and its edges / corners choose themselves.\n"
                     "(none) paints the single tile picked in the palette.")
    combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(6)
    row.addWidget(combo, 1)
    btn = QPushButton("Terrains...")
    btn.setToolTip("Make terrain sets (16-tile or 47-tile blob) from a tileset, or draw a template tileset")
    row.addWidget(btn)
    tiles_layout.addLayout(row)
    editor.autotile_terrain = ""
    editor.terrain_combo = combo

    def refresh():
        cur = editor.autotile_terrain
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("(none)", "")
        for tid, t in (editor.scene.assets.get("terrains") or {}).items():
            combo.addItem(f"{t.get('name') or tid}  ({t.get('mode', '47')})", tid)
        i = combo.findData(cur)
        combo.setCurrentIndex(max(0, i))
        editor.autotile_terrain = combo.currentData() or ""
        combo.blockSignals(False)

    def picked(_i):
        editor.autotile_terrain = combo.currentData() or ""
        if editor.autotile_terrain and editor.canvas.tool in ("select",):
            editor.set_tool("paint")
    combo.currentIndexChanged.connect(picked)
    btn.clicked.connect(lambda: TerrainsDialog(editor).exec() and refresh())
    editor.refresh_terrains = refresh
    try:
        editor.assetsChanged.connect(refresh)
    except (AttributeError, TypeError):
        pass
    refresh()


def _terrains_dialog_class():
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
                                 QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton,
                                 QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout)
    from .. import theme

    class TerrainsDialogQt(QDialog):
        """List of terrains: name, tileset, mode and the tile of every neighbour mask."""

        def __init__(self, editor):
            super().__init__(editor)
            self.editor = editor
            self.setWindowTitle("Terrains (auto-tiling)")
            self.resize(640, 520)
            self.terrains = {k: dict(v, tiles=dict(v.get("tiles") or {}))
                             for k, v in (editor.scene.assets.get("terrains") or {}).items()}
            lay = QHBoxLayout(self)
            left = QVBoxLayout()
            self.list = QListWidget()
            left.addWidget(self.list, 1)
            for text, slot in (("New...", self.new), ("Template tileset...", self.template), ("Delete", self.delete)):
                b = QPushButton(text)
                b.clicked.connect(slot)
                left.addWidget(b)
            lay.addLayout(left, 1)
            right = QVBoxLayout()
            form = QFormLayout()
            self.name = QLineEdit()
            self.tileset = QComboBox()
            self.tileset.addItems(editor.scene.asset_ids("tilesets"))
            self.mode = QComboBox()
            for k, label in MODES.items():
                self.mode.addItem(label, k)
            form.addRow("Name:", self.name)
            form.addRow("Tileset:", self.tileset)
            form.addRow("Mode:", self.mode)
            right.addLayout(form)
            std = QPushButton("Use the standard layout")
            std.setToolTip("rad16: tile = mask (4 x 4).  rad47: the 47 blob tiles in mask order, 8 per row.")
            std.clicked.connect(self.standard)
            right.addWidget(std)
            self.table = QTableWidget(0, 3)
            self.table.setHorizontalHeaderLabels(["Mask", "Neighbours", "Tile"])
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.table.verticalHeader().hide()
            right.addWidget(self.table, 1)
            right.addWidget(theme.role(QLabel(
                "Paint with the terrain chosen in the Tiles tab (Paint / Rect / Fill / Erase work as usual). "
                "Edit a Tile number to use another tile of the tileset for that neighbour combination."), "muted"))
            self.retile = QPushButton("Re-tile the active layer now")
            self.retile.clicked.connect(self.retile_layer)
            right.addWidget(self.retile)
            bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            bb.accepted.connect(self.ok)
            bb.rejected.connect(self.reject)
            right.addWidget(bb)
            lay.addLayout(right, 2)
            self.list.currentTextChanged.connect(self.show_terrain)
            self.name.editingFinished.connect(self.store)
            self.tileset.currentIndexChanged.connect(lambda _i: self.store())
            self.mode.currentIndexChanged.connect(lambda _i: self.mode_changed())
            self.table.itemChanged.connect(self.tile_changed)
            self._cur = ""
            self.refresh_list()
            self._QMessageBox, self._QInputDialog, self._QColorDialog = QMessageBox, QInputDialog, QColorDialog
            self._spin = QSpinBox

        # ---- list
        def refresh_list(self, select: str = ""):
            self.list.blockSignals(True)
            self.list.clear()
            self.list.addItems(list(self.terrains))
            self.list.blockSignals(False)
            items = self.list.findItems(select, Qt.MatchFlag.MatchExactly) if select else []
            if items:
                self.list.setCurrentItem(items[0])
            elif self.list.count():
                self.list.setCurrentRow(0)
            else:
                self.show_terrain("")

        def new(self):
            ts = self.editor.scene.asset_ids("tilesets")
            if not ts:
                self._QMessageBox.information(self, "Terrains", "Import a tileset first, or use 'Template tileset...'.")
                return
            tid, ok = self._QInputDialog.getText(self, "New terrain", "Terrain id (grass, water, wall ...):")
            tid = (tid or "").strip()
            if not ok or not tid.isidentifier():
                return
            self.terrains[tid] = new_terrain(ts[0], "47", tid.capitalize())
            self.refresh_list(tid)

        def template(self):
            """Draw a template terrain tileset, import it and make a terrain that uses it."""
            tid, ok = self._QInputDialog.getText(self, "Template tileset", "Terrain id:", text="grass")
            tid = (tid or "").strip()
            if not ok or not tid.isidentifier():
                return
            mode, ok = self._QInputDialog.getItem(self, "Template tileset", "Mode:", list(MODES.values()), 1, False)
            if not ok:
                return
            mode = "16" if mode.startswith("16") else "47"
            col = self._QColorDialog.getColor(Qt.GlobalColor.darkGreen, self, "Terrain colour")
            color = col.name() if col.isValid() else "#5DBB4A"
            edge = col.darker(170).name() if col.isValid() else "#2F6E2A"
            size, ok = self._QInputDialog.getInt(self, "Template tileset", "Tile size (px):",
                                                 self.editor.grid_size()[0], 8, 256)
            if not ok:
                return
            path = self.editor.base_dir / "assets" / f"terrain_{tid}_{mode}.png"
            make_template(path, mode, size, color, edge)
            aid = self.editor.import_tileset(None, path=str(path), tile_w=size, tile_h=size)
            self.tileset.blockSignals(True)
            self.tileset.clear()
            self.tileset.addItems(self.editor.scene.asset_ids("tilesets"))
            self.tileset.blockSignals(False)
            self.terrains[tid] = new_terrain(aid or "", mode, tid.capitalize())
            self.refresh_list(tid)

        def delete(self):
            if self._cur in self.terrains:
                del self.terrains[self._cur]
                self.refresh_list()

        # ---- one terrain
        def show_terrain(self, tid: str):
            self._cur = tid
            t = self.terrains.get(tid)
            for w in (self.name, self.tileset, self.mode, self.table, self.retile):
                w.setEnabled(t is not None)
            self.table.blockSignals(True)
            self.table.setRowCount(0)
            if t is not None:
                self.name.setText(t.get("name") or tid)
                self.tileset.blockSignals(True)
                self.tileset.setCurrentIndex(max(0, self.tileset.findText(t.get("tileset", ""))))
                self.tileset.blockSignals(False)
                self.mode.blockSignals(True)
                self.mode.setCurrentIndex(max(0, self.mode.findData(str(t.get("mode", "47")))))
                self.mode.blockSignals(False)
                masks = BLOB47 if str(t.get("mode")) == "47" else list(range(16))
                for m in masks:
                    r = self.table.rowCount()
                    self.table.insertRow(r)
                    a = QTableWidgetItem(str(m))
                    a.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    names = [nm for nm, bit in (("N", N), ("NE", NE), ("E", E), ("SE", SE), ("S", S), ("SW", SW),
                                                ("W", W), ("NW", NW))
                             if (m & bit if str(t.get("mode")) == "47" else
                                 m & {N: 1, E: 2, S: 4, W: 8}.get(bit, 0))]
                    b = QTableWidgetItem(" ".join(names) or "(alone)")
                    b.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    c = QTableWidgetItem(str((t.get("tiles") or {}).get(str(m), "")))
                    self.table.setItem(r, 0, a)
                    self.table.setItem(r, 1, b)
                    self.table.setItem(r, 2, c)
            self.table.blockSignals(False)

        def store(self):
            t = self.terrains.get(self._cur)
            if t is not None:
                t["name"] = self.name.text().strip() or self._cur
                t["tileset"] = self.tileset.currentText()

        def mode_changed(self):
            t = self.terrains.get(self._cur)
            if t is not None and str(t.get("mode")) != self.mode.currentData():
                t["mode"] = self.mode.currentData()
                t["tiles"] = standard_tiles(t["mode"])
                self.show_terrain(self._cur)

        def standard(self):
            t = self.terrains.get(self._cur)
            if t is not None:
                t["tiles"] = standard_tiles(t.get("mode", "47"))
                self.show_terrain(self._cur)

        def tile_changed(self, item):
            t = self.terrains.get(self._cur)
            if t is None or item.column() != 2:
                return
            mask = self.table.item(item.row(), 0).text()
            try:
                t.setdefault("tiles", {})[mask] = int(item.text())
            except ValueError:
                t.setdefault("tiles", {}).pop(mask, None)

        def retile_layer(self):
            self.store()
            ed, t = self.editor, self.terrains.get(self._cur)
            ly = ed.active_layer()
            if t is None or ly is None or ly.type != "tiles":
                return
            ed.change("Re-tile terrain", lambda: (ed.scene.assets.__setitem__("terrains", self.terrains),
                                                  retile(ly, t)))

        def ok(self):
            self.store()
            ed = self.editor
            ed.change("Terrains", lambda: ed.scene.assets.__setitem__("terrains", self.terrains), structural=True)
            self.accept()

    return TerrainsDialogQt


def TerrainsDialog(editor):  # noqa: N802 - a dialog factory (keeps Qt out of the module import)
    return _terrains_dialog_class()(editor)


__all__ = ["BLOB47", "MODES", "reduce47", "standard_tiles", "new_terrain", "mask_at", "tile_for", "paint",
           "retile", "retile_cells", "apply_tool", "make_template", "install_ui", "TerrainsDialog"]
