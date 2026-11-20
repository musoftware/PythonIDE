"""Database Diagram designer (Databases workspace): tables as boxes, foreign keys as lines.

- every table of a connection (SQLite, MySQL/MariaDB, PostgreSQL) is a movable box with its columns
  (key icon = primary key, arrow = foreign key column, type, NOT NULL marked with ``*``);
- each foreign key is a line from the child column to the parent column (crow's foot = "many" end);
- **Auto Layout** places parents left of their children (layers by foreign-key depth); positions are saved
  in the project (``.radide/db-diagrams.json``);
- **New Table** (the Databases "New Table" dialog), **New Relationship** (drag from a column of the child
  table onto the referenced column of the parent table, or use the dialog), **Add Column**, **Delete** -
  every change is shown as SQL DDL first and applied only after OK; SQLite tables get their foreign key by
  the documented rebuild (``PRAGMA foreign_keys=OFF`` - create new table - copy - drop - rename - re-create
  indexes/triggers - ``foreign_key_check``) inside one transaction;
- Zoom (Ctrl+wheel, buttons, Fit), Export as PNG or SVG.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .databases import Column, ColumnDef, Database, DatabaseError, ForeignKey

LAYOUT_FILE = ".radide/db-diagrams.json"
ON_DELETE = ["NO ACTION", "CASCADE", "SET NULL", "RESTRICT", "SET DEFAULT"]


# ============================================================================ model
@dataclass
class TableInfo:
    name: str
    columns: list[Column] = field(default_factory=list)
    fks: list[ForeignKey] = field(default_factory=list)
    view: bool = False

    def pk(self) -> list[str]:
        return [c.name for c in sorted((c for c in self.columns if c.pk), key=lambda c: c.pk)]

    def fk_columns(self) -> set[str]:
        return {c for fk in self.fks for c in fk.columns}


def load_schema(db: Database, include_views: bool = False) -> dict[str, TableInfo]:
    out: dict[str, TableInfo] = {}
    for t in db.tables():
        out[t] = TableInfo(t, db.columns(t), db.foreign_keys(t))
    if include_views:
        for v in db.views():
            out[v] = TableInfo(v, db.columns(v), [], True)
    return out


def auto_layout(schema: dict[str, TableInfo], sizes: dict[str, tuple[float, float]] | None = None,
                gap_x: float = 90, gap_y: float = 40) -> dict[str, tuple[float, float]]:
    """Parents left, children right: column = longest foreign-key chain to a root; connected tables first."""
    sizes = sizes or {}
    parents = {t: {fk.ref_table for fk in info.fks if fk.ref_table in schema and fk.ref_table != t}
               for t, info in schema.items()}
    depth: dict[str, int] = {}

    def d(t, seen=()):
        if t in depth:
            return depth[t]
        if t in seen:
            return 0                                   # cycle
        v = 0 if not parents[t] else 1 + max(d(p, seen + (t,)) for p in parents[t])
        depth[t] = v
        return v
    for t in schema:
        d(t)
    linked = {t for t in schema if parents[t]} | {p for ps in parents.values() for p in ps}
    cols: dict[int, list[str]] = {}
    for t in sorted(schema, key=lambda n: n.lower()):
        if t in linked:
            cols.setdefault(depth[t], []).append(t)

    # order within a column by the average row of the parents (fewer crossings)
    row_of: dict[str, float] = {}
    for c in sorted(cols):
        if c > 0:
            cols[c].sort(key=lambda t: (sum(row_of.get(p, 0) for p in parents[t]) / max(1, len(parents[t])), t))
        for i, t in enumerate(cols[c]):
            row_of[t] = i
    pos: dict[str, tuple[float, float]] = {}
    x = 20.0
    for c in sorted(cols):
        y = 20.0
        width = max((sizes.get(t, (200, 100))[0] for t in cols[c]), default=200)
        for t in cols[c]:
            pos[t] = (x, y)
            y += sizes.get(t, (200, 100))[1] + gap_y
        x += width + gap_x
    # tables without relationships: a grid below / to the right
    rest = [t for t in sorted(schema, key=lambda n: n.lower()) if t not in linked]
    if rest:
        top = max((pos[t][1] + sizes.get(t, (200, 100))[1] for t in pos), default=-gap_y) + gap_y * 2 \
            if pos else 20.0
        per_row = max(3, len(cols) or 3)
        y, rx, row_h = top, 20.0, 0.0
        for i, t in enumerate(rest):
            if i and i % per_row == 0:
                y += row_h + gap_y
                rx, row_h = 20.0, 0.0
            w, h = sizes.get(t, (200, 100))
            pos[t] = (rx, y)
            rx += w + gap_x
            row_h = max(row_h, h)
    return pos


# ============================================================================ DDL
def fk_name(child: str, cols: list[str]) -> str:
    return re.sub(r"\W+", "_", f"fk_{child}_{'_'.join(cols)}").lower()[:60]


def fk_clause(db: Database, fk: ForeignKey, name: str = "") -> str:
    s = (f"CONSTRAINT {db.q(name)} " if name else "") + \
        f"FOREIGN KEY ({', '.join(db.q(c) for c in fk.columns)}) REFERENCES {db.q(fk.ref_table)} " \
        f"({', '.join(db.q(c) for c in fk.ref_columns)})"
    if fk.on_delete and fk.on_delete.upper() != "NO ACTION":
        s += f" ON DELETE {fk.on_delete.upper()}"
    if fk.on_update and fk.on_update.upper() != "NO ACTION":
        s += f" ON UPDATE {fk.on_update.upper()}"
    return s


def ddl_create_table(db: Database, table: str, cols: list[ColumnDef], fks: list[ForeignKey] = ()) -> str:
    sql = db.ddl_create_table(table, cols)
    if fks:
        extra = ",\n  ".join(fk_clause(db, fk) for fk in fks)
        i = sql.rstrip().rfind(")")
        sql = sql[:i].rstrip() + ",\n  " + extra + "\n)"
    return sql


def ddl_add_foreign_key(db: Database, table: str, fk: ForeignKey) -> list[str]:
    """Statements that add *fk* to the existing *table* (SQLite: table rebuild)."""
    if db.dialect != "sqlite":
        return [f"ALTER TABLE {db.q(table)} ADD {fk_clause(db, fk, fk_name(table, fk.columns))}"]
    create = db.create_sql(table)
    if not create:
        raise DatabaseError(f"cannot read the definition of {table}")
    tmp = f"{table}__radide_new"
    m = re.match(r"\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\"(?:[^\"]|\"\")+\"|`[^`]+`|\[[^\]]+\]|[^\s(]+)\s*\(",
                 create, re.I)
    if not m:
        raise DatabaseError(f"cannot parse the definition of {table}")
    body = create[m.end():]
    i = body.rstrip().rfind(")")
    body = body[:i].rstrip() + ",\n  " + fk_clause(db, fk) + "\n" + body[i:]
    new_create = f"CREATE TABLE {db.q(tmp)} (" + body
    cols = ", ".join(db.q(c.name) for c in db.columns(table))
    extra = [r[0] for r in db._rows("SELECT sql FROM sqlite_master WHERE tbl_name = ? AND type IN ('index', "
                                    "'trigger') AND sql IS NOT NULL", [table])]
    return ["PRAGMA foreign_keys = OFF", "BEGIN", new_create,
            f"INSERT INTO {db.q(tmp)} ({cols}) SELECT {cols} FROM {db.q(table)}",
            f"DROP TABLE {db.q(table)}", f"ALTER TABLE {db.q(tmp)} RENAME TO {db.q(table)}",
            *extra, "-- check: PRAGMA foreign_key_check", "COMMIT", "PRAGMA foreign_keys = ON"]


def apply_statements(db: Database, stmts: list[str]) -> None:
    """Run DDL statements; a failure rolls back (SQLite rebuild) and raises DatabaseError."""
    began = False
    try:
        for s in stmts:
            if s.startswith("-- check:"):
                bad = db._rows("PRAGMA foreign_key_check")
                if bad:
                    raise DatabaseError(f"{len(bad)} existing row(s) break the new foreign key (for example "
                                        f"rowid {bad[0][1]} of {bad[0][0]}) - fix the data first")
                continue
            if s.upper() == "BEGIN":
                began = True
            elif s.upper() == "COMMIT":
                began = False
            db._run(s)
    except Exception as e:
        if began:
            try:
                db._run("ROLLBACK")
            except Exception:  # noqa: BLE001
                pass
        if db.dialect == "sqlite":
            try:
                db._run("PRAGMA foreign_keys = ON")
            except Exception:  # noqa: BLE001
                pass
        raise e if isinstance(e, DatabaseError) else DatabaseError(str(e)) from e


# ============================================================================ layout file
def _layout_path(folder) -> Path | None:
    return Path(folder) / LAYOUT_FILE if folder else None


def load_positions(folder, key: str) -> dict[str, tuple[float, float]]:
    p = _layout_path(folder)
    try:
        data = json.loads(p.read_text(encoding="utf-8")) if p and p.is_file() else {}
        return {k: tuple(v) for k, v in (data.get(key) or {}).items()}
    except (OSError, ValueError, TypeError):
        return {}


def save_positions(folder, key: str, pos: dict[str, tuple[float, float]]) -> None:
    p = _layout_path(folder)
    if p is None:
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    except (OSError, ValueError):
        data = {}
    data[key] = {k: [round(v[0], 1), round(v[1], 1)] for k, v in pos.items()}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
        pass


# ============================================================================ UI
def _build():
    from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
    from PyQt6.QtGui import QAction, QBrush, QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
    from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGraphicsItem,
                                 QGraphicsObject, QGraphicsPathItem, QGraphicsScene, QGraphicsView, QLabel,
                                 QMenu, QMessageBox, QPlainTextEdit, QToolBar, QVBoxLayout, QWidget)
    from .. import theme

    ROW_H, HEAD_H, PAD = 20, 26, 8

    def col(token, fallback):
        try:
            return QColor(theme.color(token))
        except Exception:  # noqa: BLE001
            return QColor(fallback)

    class TableItem(QGraphicsObject):
        moved = pyqtSignal()

        def __init__(self, info: TableInfo):
            super().__init__()
            self.info = info
            self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                          QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                          QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.font = QFont("Segoe UI", 9)
            self.bold = QFont("Segoe UI", 9, QFont.Weight.Bold)
            fm, fb = QFontMetrics(self.font), QFontMetrics(self.bold)
            name_w = max([fm.horizontalAdvance(f"{c.name}{' *' if c.notnull else ''}") for c in info.columns] or [40])
            type_w = max([fm.horizontalAdvance((c.type or "").lower()) for c in info.columns] or [20])
            self.name_x = PAD + 18
            self.type_x = self.name_x + name_w + 16
            self.w = max(fb.horizontalAdvance(info.name) + 2 * PAD + 20, self.type_x + type_w + PAD, 150)
            self.h = HEAD_H + ROW_H * max(1, len(info.columns)) + 4
            self.drop_row = -1

        def boundingRect(self):
            return QRectF(-1, -1, self.w + 2, self.h + 2)

        def row_of(self, column: str) -> int:
            for i, c in enumerate(self.info.columns):
                if c.name.lower() == column.lower():
                    return i
            return -1

        def column_at(self, scene_pos) -> str:
            p = self.mapFromScene(scene_pos)
            i = int((p.y() - HEAD_H) // ROW_H)
            return self.info.columns[i].name if 0 <= i < len(self.info.columns) and p.y() >= HEAD_H else ""

        def anchor(self, column: str, right: bool) -> QPointF:
            i = max(0, self.row_of(column))
            return self.mapToScene(QPointF(self.w if right else 0, HEAD_H + ROW_H * i + ROW_H / 2))

        def paint(self, p: QPainter, _opt, _w=None):
            base, text = col("base", "#FFFFFF"), col("text", "#000000")
            head = col("accent", "#316AC5") if not self.info.view else col("muted", "#5A5A5A")
            border = col("highlight", "#316AC5") if self.isSelected() else col("border", "#A0AFC3")
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(border, 2 if self.isSelected() else 1))
            p.setBrush(QBrush(base))
            p.drawRoundedRect(QRectF(0, 0, self.w, self.h), 5, 5)
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.WindingFill)
            path.addRoundedRect(QRectF(0, 0, self.w, HEAD_H), 5, 5)
            path.addRect(QRectF(0, HEAD_H / 2, self.w, HEAD_H / 2))
            p.fillPath(path, head)
            p.setPen(col("accent_text", "#FFFFFF"))
            p.setFont(self.bold)
            p.drawText(QRectF(PAD, 0, self.w - 2 * PAD, HEAD_H), Qt.AlignmentFlag.AlignVCenter,
                       self.info.name + ("  (view)" if self.info.view else ""))
            fks = self.info.fk_columns()
            p.setFont(self.font)
            muted = col("muted", "#5A5A5A")
            for i, c in enumerate(self.info.columns):
                y = HEAD_H + ROW_H * i
                if i == self.drop_row:
                    p.fillRect(QRectF(1, y, self.w - 2, ROW_H), col("menu_sel", "#C1D2EE"))
                mark = "\U0001F511" if c.pk else ("→" if c.name in fks else "")
                p.setPen(col("note", "#806000") if c.pk else text)
                if mark:
                    p.drawText(QRectF(PAD - 2, y, 18, ROW_H), Qt.AlignmentFlag.AlignVCenter, mark)
                p.setPen(text)
                f = self.bold if c.pk else self.font
                p.setFont(f)
                p.drawText(QRectF(self.name_x, y, self.type_x - self.name_x, ROW_H), Qt.AlignmentFlag.AlignVCenter,
                           c.name + (" *" if c.notnull and not c.pk else ""))
                p.setFont(self.font)
                p.setPen(muted)
                p.drawText(QRectF(self.type_x, y, self.w - self.type_x - PAD, ROW_H), Qt.AlignmentFlag.AlignVCenter,
                           (c.type or "").lower())

        def itemChange(self, change, value):
            if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
                self.moved.emit()
            return super().itemChange(change, value)

    class RelationItem(QGraphicsPathItem):
        def __init__(self, child: TableItem, parent: TableItem, fk: ForeignKey):
            super().__init__()
            self.child, self.parent_t, self.fk = child, parent, fk
            self.setZValue(-1)
            self.setToolTip(f"{child.info.name}({', '.join(fk.columns)}) → "
                            f"{parent.info.name}({', '.join(fk.ref_columns)})"
                            + (f"\nON DELETE {fk.on_delete}" if fk.on_delete and fk.on_delete != "NO ACTION" else ""))
            self.update_path()

        def update_path(self):
            c, pt = self.child, self.parent_t
            right = c.sceneBoundingRect().center().x() < pt.sceneBoundingRect().center().x()
            a = c.anchor(self.fk.columns[0], right)
            ref = self.fk.ref_columns[0] if self.fk.ref_columns and self.fk.ref_columns[0] else \
                (pt.info.pk()[0] if pt.info.pk() else "")
            b = pt.anchor(ref, not right)
            if c is pt:                                  # self reference: a loop on the right
                a, b = c.anchor(self.fk.columns[0], True), c.anchor(ref, True)
                path = QPainterPath(a)
                path.cubicTo(a + QPointF(60, 0), b + QPointF(60, 0), b)
            a, b = c.anchor(self.fk.columns[0], right), pt.anchor(ref, not right)
            dx = max(40.0, abs(b.x() - a.x()) / 2)
            s = 1 if right else -1
            path = QPainterPath(a)
            path.cubicTo(a + QPointF(s * dx, 0), b - QPointF(s * dx, 0), b)
            self._ends(path, a, b, s, -s)

        def _ends(self, path, a, b, sa, sb):
            """Crow's foot at the child ("many"), a bar at the parent ("one"); s* = side the line leaves to."""
            for dy in (-6, 0, 6):
                path.moveTo(a + QPointF(sa * 12, 0))
                path.lineTo(a + QPointF(0, dy))
            path.moveTo(b + QPointF(sb * 8, -6))
            path.lineTo(b + QPointF(sb * 8, 6))
            self.setPath(path)
            self.setPen(QPen(col("accent", "#316AC5"), 1.6))

    class DiagramView(QGraphicsView):
        relationDropped = pyqtSignal(str, str, str, str)    # child, child col, parent, parent col

        def __init__(self, scene, parent=None):
            super().__init__(scene, parent)
            self.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            self.link_mode = False
            self._link_from = None
            self._rubber = None

        def wheelEvent(self, e):
            if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
                self.scale(f, f)
            else:
                super().wheelEvent(e)

        def _table_at(self, pos):
            for it in self.items(pos):
                if isinstance(it, TableItem):
                    return it
            return None

        def mousePressEvent(self, e):
            if self.link_mode and e.button() == Qt.MouseButton.LeftButton:
                t = self._table_at(e.position().toPoint())
                if t is not None:
                    sp = self.mapToScene(e.position().toPoint())
                    c = t.column_at(sp)
                    if c:
                        self._link_from = (t, c)
                        self._rubber = QGraphicsPathItem()
                        self._rubber.setPen(QPen(col("highlight", "#316AC5"), 1.5, Qt.PenStyle.DashLine))
                        self.scene().addItem(self._rubber)
                        return
            super().mousePressEvent(e)

        def mouseMoveEvent(self, e):
            if self._link_from is not None:
                t0, c0 = self._link_from
                a = t0.anchor(c0, True)
                b = self.mapToScene(e.position().toPoint())
                path = QPainterPath(a)
                path.lineTo(b)
                self._rubber.setPath(path)
                for it in self.scene().items():
                    if isinstance(it, TableItem):
                        r = it.row_of(it.column_at(b)) if it.sceneBoundingRect().contains(b) else -1
                        if r != it.drop_row:
                            it.drop_row = r
                            it.update()
                return
            super().mouseMoveEvent(e)

        def mouseReleaseEvent(self, e):
            if self._link_from is not None:
                t0, c0 = self._link_from
                self._link_from = None
                self.scene().removeItem(self._rubber)
                self._rubber = None
                for it in self.scene().items():
                    if isinstance(it, TableItem) and it.drop_row >= 0:
                        it.drop_row = -1
                        it.update()
                t1 = self._table_at(e.position().toPoint())
                if t1 is not None:
                    c1 = t1.column_at(self.mapToScene(e.position().toPoint()))
                    if c1:
                        self.relationDropped.emit(t0.info.name, c0, t1.info.name, c1)
                return
            super().mouseReleaseEvent(e)

    class SqlPreviewDialog(QDialog):
        def __init__(self, title, sql, parent=None, note=""):
            super().__init__(parent)
            self.setWindowTitle(title)
            self.resize(640, 380)
            lay = QVBoxLayout(self)
            lab = QLabel(note or "This SQL will be run on the database:")
            lab.setWordWrap(True)
            lay.addWidget(lab)
            ed = QPlainTextEdit(sql)
            ed.setReadOnly(True)
            ed.setFont(QFont("Consolas", 10))
            lay.addWidget(ed, 1)
            bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            bb.button(QDialogButtonBox.StandardButton.Ok).setText("Run")
            bb.accepted.connect(self.accept)
            bb.rejected.connect(self.reject)
            lay.addWidget(bb)

    class RelationDialog(QDialog):
        def __init__(self, schema: dict[str, TableInfo], parent=None, child="", ccol="", ptable="", pcol=""):
            super().__init__(parent)
            self.schema = schema
            self.setWindowTitle("New Relationship (Foreign Key)")
            form = QFormLayout(self)
            self.child, self.ccol, self.parent_t, self.pcol = QComboBox(), QComboBox(), QComboBox(), QComboBox()
            tables = [t for t, i in schema.items() if not i.view]
            self.child.addItems(tables)
            self.parent_t.addItems(tables)
            self.on_delete = QComboBox()
            self.on_delete.addItems(ON_DELETE)
            self.child.currentTextChanged.connect(lambda t: self._cols(self.ccol, t))
            self.parent_t.currentTextChanged.connect(lambda t: self._cols(self.pcol, t, True))
            form.addRow(QLabel("Each row of the <b>child</b> table points to one row of the <b>parent</b> table."))
            form.addRow("Child table (many):", self.child)
            form.addRow("Child column:", self.ccol)
            form.addRow("Parent table (one):", self.parent_t)
            form.addRow("Parent column:", self.pcol)
            form.addRow("On delete:", self.on_delete)
            bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            bb.accepted.connect(self.accept)
            bb.rejected.connect(self.reject)
            form.addRow(bb)
            self.child.setCurrentText(child or (tables[0] if tables else ""))
            self._cols(self.ccol, self.child.currentText())
            self.parent_t.setCurrentText(ptable or (tables[0] if tables else ""))
            self._cols(self.pcol, self.parent_t.currentText(), True)
            if ccol:
                self.ccol.setCurrentText(ccol)
            if pcol:
                self.pcol.setCurrentText(pcol)

        def _cols(self, box, table, pk_first=False):
            box.clear()
            info = self.schema.get(table)
            if info is None:
                return
            names = [c.name for c in info.columns]
            if pk_first:
                names = info.pk() + [n for n in names if n not in info.pk()]
            box.addItems(names)

        def fk(self) -> tuple[str, ForeignKey]:
            return self.child.currentText(), ForeignKey([self.ccol.currentText()], self.parent_t.currentText(),
                                                        [self.pcol.currentText()], self.on_delete.currentText())

    class DbDiagramWidget(QWidget):
        """The diagram tab. *db*: a connected adapter used only by this tab (GUI thread)."""
        changed = pyqtSignal()

        def __init__(self, db: Database, folder=None, key: str = "", title: str = "", parent=None, log=None):
            super().__init__(parent)
            self.db, self.folder, self.key = db, folder, key or db.info.name
            self.log = log or (lambda s: None)
            self.schema: dict[str, TableInfo] = {}
            self.items: dict[str, TableItem] = {}
            self.relations: list[RelationItem] = []
            lay = QVBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            tb = QToolBar()
            self.tb = tb
            tb.addAction("Refresh", self.reload)
            tb.addAction("Auto Layout", self.auto_layout)
            tb.addSeparator()
            tb.addAction("New Table...", self.new_table)
            self.a_link = QAction("New Relationship", self)
            self.a_link.setCheckable(True)
            self.a_link.setToolTip("Drag from a column of the child table onto the referenced column of the parent "
                                   "table (or click with nothing selected to use a dialog)")
            self.a_link.toggled.connect(self._link_mode)
            tb.addAction(self.a_link)
            tb.addAction("Relationship...", lambda: self.new_relation())
            tb.addSeparator()
            tb.addAction("Zoom In", lambda: self.view.scale(1.2, 1.2))
            tb.addAction("Zoom Out", lambda: self.view.scale(1 / 1.2, 1 / 1.2))
            tb.addAction("Fit", self.fit)
            tb.addSeparator()
            tb.addAction("Export Image...", self.export_image)
            self.info = QLabel()
            theme.role(self.info, "muted")
            lay.addWidget(tb)
            self.scene = QGraphicsScene(self)
            self.view = DiagramView(self.scene, self)
            self.view.relationDropped.connect(self._dropped)
            self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.view.customContextMenuRequested.connect(self._menu)
            lay.addWidget(self.view, 1)
            lay.addWidget(self.info)
            self._apply_theme()
            try:
                theme.manager().changed.connect(self._apply_theme)
            except Exception:  # noqa: BLE001
                pass
            self.reload()

        def _apply_theme(self, *_):
            self.view.setBackgroundBrush(QBrush(col("alt_base", "#F5F5F0")))
            for it in self.items.values():
                it.update()
            for r in self.relations:
                r.update_path()

        # ------------------------------------------------------------ build
        def reload(self):
            old = {n: (it.pos().x(), it.pos().y()) for n, it in self.items.items()}
            self.scene.clear()
            self.items.clear()
            self.relations.clear()
            try:
                self.schema = load_schema(self.db)
            except Exception as e:  # noqa: BLE001
                self.info.setText(f"Cannot read the schema: {e}")
                return
            for name, info in self.schema.items():
                it = TableItem(info)
                it.moved.connect(self._moved)
                self.scene.addItem(it)
                self.items[name] = it
            for name, info in self.schema.items():
                for fk in info.fks:
                    if fk.ref_table in self.items and fk.columns:
                        r = RelationItem(self.items[name], self.items[fk.ref_table], fk)
                        self.scene.addItem(r)
                        self.relations.append(r)
            saved = load_positions(self.folder, self.key)
            saved.update(old)
            known = [n for n in self.items if n in saved]
            if not known:
                self.auto_layout()
            else:                                         # new tables go in a row below the others
                for n in known:
                    self.items[n].setPos(*saved[n])
                bottom = max(saved[n][1] + self.items[n].h for n in known) + 40
                x = 20.0
                for n, it in self.items.items():
                    if n not in saved:
                        it.setPos(x, bottom)
                        x += it.w + 40
                self._save()
            self._update_info()

        def _update_info(self):
            nrel = len(self.relations)
            self.info.setText(f"  {len(self.items)} table(s), {nrel} relationship(s)  -  drag tables to move them;"
                              f" right-click for more")

        def auto_layout(self, keep=None):
            sizes = {n: (it.w, it.h) for n, it in self.items.items()}
            pos = auto_layout(self.schema, sizes)
            for n, it in self.items.items():
                if keep and n in keep:
                    it.setPos(*keep[n])
                else:
                    it.setPos(*pos.get(n, (0, 0)))
            self._save()
            self.fit()

        def fit(self):
            r = self.scene.itemsBoundingRect().adjusted(-20, -20, 20, 20)
            self.scene.setSceneRect(r)
            self.view.resetTransform()
            vp = self.view.viewport().size()
            if not self.view.isVisible() or vp.width() < 100 or vp.height() < 100 or r.isEmpty():
                return                                    # not laid out yet: showEvent fits again
            f = min(vp.width() / r.width(), vp.height() / r.height(), 1.0)   # never blow small diagrams up
            self.view.scale(f, f)
            self.view.centerOn(r.center())

        def showEvent(self, e):
            super().showEvent(e)
            if not getattr(self, "_fitted", False):
                self._fitted = True
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, self.fit)

        def _moved(self):
            for r in self.relations:
                r.update_path()
            self._save()

        def _save(self):
            save_positions(self.folder, self.key, {n: (it.pos().x(), it.pos().y()) for n, it in self.items.items()})

        def positions(self) -> dict[str, tuple[float, float]]:
            return {n: (it.pos().x(), it.pos().y()) for n, it in self.items.items()}

        # ------------------------------------------------------------ edit
        def run_sql(self, title: str, stmts: list[str], confirm: bool = True, note: str = "") -> bool:
            sql = ";\n".join(s for s in stmts if not s.startswith("-- check:")) + ";"
            if confirm and SqlPreviewDialog(title, sql, self, note).exec() != QDialog.DialogCode.Accepted:
                return False
            try:
                apply_statements(self.db, stmts)
            except DatabaseError as e:
                QMessageBox.warning(self, title, str(e))
                return False
            self.log(f"[diagram {self.key}] {sql}")
            self.reload()
            self.changed.emit()
            return True

        def new_table(self, confirm: bool = True):
            from ..features.databases import CreateTableDialog
            dlg = CreateTableDialog(self.db, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return None
            name = dlg.name.text().strip()
            sql = ddl_create_table(self.db, name, dlg.columns())
            if self.run_sql("New Table", [sql], confirm=False):
                return name
            return None

        def create_table(self, name: str, cols: list[ColumnDef], fks: list[ForeignKey] = (), confirm=True) -> bool:
            return self.run_sql("New Table", [ddl_create_table(self.db, name, cols, list(fks))], confirm)

        def add_relation(self, child: str, fk: ForeignKey, confirm: bool = True) -> bool:
            try:
                stmts = ddl_add_foreign_key(self.db, child, fk)
            except DatabaseError as e:
                QMessageBox.warning(self, "New Relationship", str(e))
                return False
            note = ("SQLite cannot add a foreign key to an existing table, so the table is rebuilt (its data is "
                    "copied) inside one transaction:") if self.db.dialect == "sqlite" else ""
            return self.run_sql("New Relationship", stmts, confirm, note)

        def new_relation(self, child="", ccol="", ptable="", pcol=""):
            dlg = RelationDialog(self.schema, self, child, ccol, ptable, pcol)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return False
            c, fk = dlg.fk()
            return self.add_relation(c, fk)

        def _link_mode(self, on):
            self.view.link_mode = on
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag if on else QGraphicsView.DragMode.RubberBandDrag)
            for it in self.items.values():
                it.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not on)
            self.info.setText("  Drag from the child's column to the parent's key column (Esc / button = done)"
                              if on else "")
            if not on:
                self._update_info()

        def _dropped(self, child, ccol, parent, pcol):
            self.a_link.setChecked(False)
            if child == parent and ccol == pcol:
                return
            self.new_relation(child, ccol, parent, pcol)

        def _menu(self, pos):
            sp = self.view.mapToScene(pos)
            t = next((it for it in self.view.items(pos) if isinstance(it, TableItem)), None)
            rel = next((it for it in self.view.items(pos) if isinstance(it, RelationItem)), None)
            m = QMenu(self)
            if t is not None:
                name = t.info.name
                c = t.column_at(sp)
                if c:
                    m.addAction(f"New relationship from {name}.{c}...", lambda: self.new_relation(name, c))
                m.addAction("Add Column...", lambda: self.add_column(name))
                m.addAction("Show CREATE SQL", lambda: SqlPreviewDialog(
                    name, self.db.create_sql(name) or "(not available)", self, "Definition:").exec())
                m.addSeparator()
                m.addAction(f"Delete table {name}...", lambda: self.drop_table(name))
            elif rel is not None:
                m.addAction(rel.toolTip().splitlines()[0]).setEnabled(False)
            else:
                m.addAction("New Table...", self.new_table)
                m.addAction("New Relationship...", lambda: self.new_relation())
                m.addAction("Auto Layout", self.auto_layout)
            m.exec(self.view.viewport().mapToGlobal(pos))

        def add_column(self, table):
            from PyQt6.QtWidgets import QCheckBox, QLineEdit
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Add Column to {table}")
            f = QFormLayout(dlg)
            name, typ, nn = QLineEdit(), QComboBox(), QCheckBox("Not null")
            typ.setEditable(True)
            typ.addItems(self.db.types or ["TEXT", "INTEGER"])
            f.addRow("Name:", name)
            f.addRow("Type:", typ)
            f.addRow("", nn)
            bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            bb.accepted.connect(dlg.accept)
            bb.rejected.connect(dlg.reject)
            f.addRow(bb)
            if dlg.exec() == QDialog.DialogCode.Accepted and name.text().strip():
                c = ColumnDef(name.text().strip(), typ.currentText(), notnull=nn.isChecked(),
                              default="0" if nn.isChecked() and "INT" in typ.currentText().upper() else
                              ("''" if nn.isChecked() else ""))
                self.run_sql("Add Column", [self.db.ddl_add_column(table, c)])

        def drop_table(self, table):
            self.run_sql("Delete Table", [f"DROP TABLE {self.db.q(table)}"],
                         note=f"<b>{table}</b> and all its rows will be deleted:")

        def export_image(self, path: str | None = None):
            if path is None:
                path, _ = QFileDialog.getSaveFileName(self, "Export Diagram", f"{self.key}-diagram.png",
                                                      "PNG image (*.png);;SVG drawing (*.svg)")
                if not path:
                    return None
            r = self.scene.itemsBoundingRect().adjusted(-20, -20, 20, 20)
            self.scene.clearSelection()
            if path.lower().endswith(".svg"):
                from PyQt6.QtSvg import QSvgGenerator
                gen = QSvgGenerator()
                gen.setFileName(path)
                gen.setSize(r.size().toSize())
                gen.setViewBox(QRectF(0, 0, r.width(), r.height()))
                gen.setTitle(f"{self.key} database diagram")
                p = QPainter(gen)
                self.scene.render(p, QRectF(0, 0, r.width(), r.height()), r)
                p.end()
            else:
                from PyQt6.QtGui import QImage
                img = QImage(int(r.width() * 2), int(r.height() * 2), QImage.Format.Format_ARGB32)
                img.fill(col("alt_base", "#F5F5F0"))
                p = QPainter(img)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                self.scene.render(p, QRectF(0, 0, img.width(), img.height()), r)
                p.end()
                img.save(path)
            return path

        def closeEvent(self, e):
            try:
                self.db.close()
            except Exception:  # noqa: BLE001
                pass
            super().closeEvent(e)

    return DbDiagramWidget


_W = None


def widget_class():
    global _W
    if _W is None:
        _W = _build()
    return _W


def open_diagram(panel, cid: str):
    """Databases panel: open the diagram tab of connection *cid* (its own connection, GUI thread)."""
    db = panel.db(cid)
    if db is None:
        return None
    try:
        own = db.clone()
        own.connect()
    except Exception as e:  # noqa: BLE001
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(panel, "Database Diagram", f"Cannot connect: {e}")
        return None
    m, c = panel._split_id(cid)
    folder = getattr(m, "folder", None)
    W = widget_class()
    log = getattr(panel, "log", None) or (lambda s: None)

    def make():
        w = W(own, folder, c.name, parent=None, log=log)
        w.changed.connect(lambda: panel.refresh_connection(cid, False))
        return w
    return panel._show(("diagram", cid), make, f"Diagram [{panel._label(cid)}]")


__all__ = ["TableInfo", "apply_statements", "auto_layout", "ddl_add_foreign_key", "ddl_create_table", "fk_clause",
           "load_positions", "load_schema", "open_diagram", "save_positions", "widget_class"]
