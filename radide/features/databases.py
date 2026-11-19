"""Databases workspace (WebMatrix "Databases") - docs/CONTRACTS.md section 8.3.

* **Databases** dock: the connections of every open project (``project.radproj`` "databases") and SQLite
  files found in the project folders; tables and views as a tree; right-click menus for everything.
* Document tabs: **table data** (editable grid: edit cells, new row, delete rows, set NULL, filter, sort,
  pages), **schema** (columns, indexes, foreign keys, CREATE statement, add/drop column), **SQL query**
  (run all / selection, several result grids, messages with errors and line numbers, open/save .sql).
* Dialogs: connection (SQLite / MySQL / PostgreSQL, test, remember password encrypted in the IDE settings),
  create table, add column, import CSV. Export table to CSV / SQL, whole database to SQL.
* **Open in Adminer**: the bundled Adminer (radide/web/adminer/) served by ``php -S`` on a private port and
  logged in automatically - shown in the web Preview dock when there is one, else in a tab.

Engine (no Qt): ``radide/web_site/databases.py``. Other features can use ``win.databases`` (DatabasesPanel):
``add_sqlite(path, project=None)``, ``open_table(conn, table)``, ``open_query(conn, sql="")``,
``open_adminer(conn)``, ``connection(name)``.
"""
from __future__ import annotations

import atexit
import re
from pathlib import Path

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QRegularExpression, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (QAction, QBrush, QColor, QCursor, QDesktopServices, QFont, QKeySequence, QSyntaxHighlighter,
                         QTextCharFormat)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QDockWidget, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QInputDialog,
                             QLabel, QLineEdit, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox,
                             QSplitter, QStackedWidget, QStyle, QTableView, QTableWidget, QTableWidgetItem,
                             QTabWidget, QToolBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..web_site import databases as D

ROLE = Qt.ItemDataRole.UserRole
NULL_BRUSH = QBrush(QColor("#9A9A9A"))
ERROR_COLOR = "#B00020"


def _std_icon(w, name):
    return w.style().standardIcon(getattr(QStyle.StandardPixmap, name))


def _wait_cursor():
    class _W:
        def __enter__(self):
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

        def __exit__(self, *a):
            QApplication.restoreOverrideCursor()
    return _W()


# =============================================================================== SQL highlighter
SQL_KEYWORDS = """select from where and or not insert into values update set delete create table drop alter add
column primary key foreign references index unique view trigger begin commit rollback transaction join left right
inner outer full cross on group by order having limit offset as distinct union all exists in is null like between
case when then else end default autoincrement auto_increment integer int text real blob varchar char numeric
decimal boolean date datetime timestamp pragma explain with recursive returning if replace rename to cascade
asc desc count sum avg min max serial bigint double precision constraint check collate escape glob vacuum
analyze attach detach database schema show use""".split()


class SqlHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)

        def fmt(color, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            f.setFontItalic(italic)
            return f
        self.rules = [
            (QRegularExpression(r"\b(" + "|".join(SQL_KEYWORDS) + r")\b",
                                QRegularExpression.PatternOption.CaseInsensitiveOption), fmt("#0000FF", True)),
            (QRegularExpression(r"\b\d+(\.\d+)?\b"), fmt("#098658")),
            (QRegularExpression(r"'([^']|'')*'"), fmt("#A31515")),
            (QRegularExpression(r"\"[^\"]*\"|`[^`]*`"), fmt("#795E26")),
            (QRegularExpression(r"--[^\n]*"), fmt("#008000", italic=True)),
        ]
        self.comment = fmt("#008000", italic=True)

    def highlightBlock(self, text):
        for rx, f in self.rules:
            it = rx.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), f)
        # /* ... */ across lines
        self.setCurrentBlockState(0)
        start = 0 if self.previousBlockState() == 1 else text.find("/*")
        while start >= 0:
            end = text.find("*/", start + 2 if self.previousBlockState() != 1 or start else 0)
            if end < 0:
                self.setCurrentBlockState(1)
                self.setFormat(start, len(text) - start, self.comment)
                break
            self.setFormat(start, end + 2 - start, self.comment)
            start = text.find("/*", end + 2)


# =============================================================================== grid model
class TableModel(QAbstractTableModel):
    """One page of a table, editable in place: setData = UPDATE, insert_row = INSERT, delete_rows = DELETE.
    Errors go to the ``error`` signal (and the edit is refused)."""
    error = pyqtSignal(str)
    loaded = pyqtSignal()

    def __init__(self, db: D.Database, table: str, page_size: int = 200, parent=None):
        super().__init__(parent)
        self.db = db
        self.table = table
        self.page_size = page_size
        self.offset = 0
        self.where = ""
        self.order_by = ""
        self.descending = False
        self.data_: D.TableData | None = None

    # ------------------------------------------------------------------ loading
    def load(self) -> bool:
        try:
            data = self.db.select(self.table, self.page_size, self.offset, self.order_by, self.descending, self.where)
        except D.DatabaseError as e:
            self.error.emit(str(e))
            return False
        self.beginResetModel()
        self.data_ = data
        self.endResetModel()
        self.loaded.emit()
        return True

    @property
    def columns(self) -> list[D.Column]:
        return self.data_.columns if self.data_ else []

    @property
    def total(self) -> int:
        return self.data_.total if self.data_ else 0

    @property
    def editable(self) -> bool:
        return bool(self.data_ and self.data_.editable)

    def page_count(self) -> int:
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    def page(self) -> int:
        return self.offset // self.page_size + 1

    def go_page(self, page: int) -> None:
        page = max(1, min(page, self.page_count()))
        self.offset = (page - 1) * self.page_size
        self.load()

    # ------------------------------------------------------------------ Qt model
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or not self.data_ else len(self.data_.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or not self.data_ else len(self.data_.columns)

    def value(self, row: int, col: int):
        return self.data_.rows[row][col]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not self.data_:
            return None
        v = self.data_.rows[index.row()][index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            return D.display_value(v)
        if role == Qt.ItemDataRole.EditRole:
            return "" if v is None else (D.display_value(v) if isinstance(v, (bytes, bytearray, memoryview)) else str(v))
        if role == Qt.ItemDataRole.ForegroundRole and v is None:
            return NULL_BRUSH
        if role == Qt.ItemDataRole.FontRole and v is None:
            f = QFont()
            f.setItalic(True)
            return f
        if role == Qt.ItemDataRole.TextAlignmentRole and isinstance(v, (int, float)) and not isinstance(v, bool):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ToolTipRole and isinstance(v, str) and len(v) > 60:
            return v[:2000]
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if not self.data_:
            return None
        if orientation == Qt.Orientation.Horizontal:
            c = self.data_.columns[section]
            if role == Qt.ItemDataRole.DisplayRole:
                mark = " ▲" if c.name == self.order_by and not self.descending else (
                    " ▼" if c.name == self.order_by else "")
                return ("\U0001F511 " if c.pk else "") + c.name + mark
            if role == Qt.ItemDataRole.ToolTipRole:
                bits = [c.type or "(no type)"]
                if c.pk:
                    bits.append("primary key")
                if c.autoinc:
                    bits.append("auto")
                if c.notnull:
                    bits.append("not null")
                if c.default is not None:
                    bits.append(f"default {c.default}")
                return f"{c.name}: " + ", ".join(bits)
        elif role == Qt.ItemDataRole.DisplayRole:
            return str(self.offset + section + 1)
        return None

    def flags(self, index):
        f = super().flags(index)
        if index.isValid() and self.editable:
            v = self.data_.rows[index.row()][index.column()]
            if not isinstance(v, (bytes, bytearray, memoryview)):
                f |= Qt.ItemFlag.ItemIsEditable
        return f

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid() or not self.editable:
            return False
        r, c = index.row(), index.column()
        col = self.data_.columns[c]
        old = self.data_.rows[r][c]
        if value is None:
            new = None
        else:
            if old is not None and str(value) == str(old):
                return False
            new = self.db.coerce(col, str(value))
        return self._update(r, {col.name: new})

    def set_null(self, index) -> bool:
        if not index.isValid():
            return False
        col = self.data_.columns[index.column()]
        if col.notnull:
            self.error.emit(f"{col.name} cannot be NULL")
            return False
        return self._update(index.row(), {col.name: None})

    def _update(self, r: int, values: dict) -> bool:
        key = self.data_.keys[r]
        try:
            self.db.update_row(self.table, key, values)
        except D.DatabaseError as e:
            self.error.emit(str(e))
            return False
        self._refresh_row(r, key, values)
        return True

    def _refresh_row(self, r: int, key: dict, values: dict) -> None:
        """Show the stored values (types/defaults/triggers applied by the database) without moving rows."""
        names = self.data_.column_names
        new_key = {k: values.get(k, v) for k, v in key.items()} if D.KEY_ALIAS not in key else key
        try:
            where, params = self.db._key_where(new_key)
            cols = ", ".join(self.db.q(n) for n in names)
            rows = self.db._rows(f"SELECT {cols} FROM {self.db.q(self.table)} WHERE {where}", params)
        except D.DatabaseError:
            rows = []
        if rows and D.KEY_ALIAS not in key:
            self.data_.rows[r] = list(rows[0])
            pk = [k for k in key]
            self.data_.keys[r] = {k: self.data_.rows[r][names.index(k)] for k in pk if k in names}
            self.dataChanged.emit(self.index(r, 0), self.index(r, len(names) - 1))
        else:
            self.load()                         # ctid changes after an update: read the page again

    def insert_row(self, values: dict) -> bool:
        try:
            self.db.insert_row(self.table, values)
        except D.DatabaseError as e:
            self.error.emit(str(e))
            return False
        # show the last page (where a new row normally is)
        self.load()
        if self.total > self.offset + self.page_size and not self.order_by:
            self.go_page(self.page_count())
        return True

    def delete_rows(self, rows: list[int]) -> int:
        keys = [self.data_.keys[r] for r in sorted(set(rows)) if 0 <= r < len(self.data_.keys)]
        if not keys:
            return 0
        try:
            n = self.db.delete_rows(self.table, keys)
        except D.DatabaseError as e:
            self.error.emit(str(e))
            self.load()
            return 0
        self.load()
        if self.offset and self.offset >= self.total:
            self.go_page(self.page_count())
        return n

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        if not self.data_ or column < 0:
            return
        self.order_by = self.data_.columns[column].name
        self.descending = order == Qt.SortOrder.DescendingOrder
        self.offset = 0
        self.load()


# =============================================================================== row dialog
class RowDialog(QDialog):
    """New row: one field per column; empty = the column's default (or auto value), NULL box = NULL."""

    def __init__(self, columns: list[D.Column], parent=None, title="New Row"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.columns = columns
        self.edits: dict[str, tuple[QLineEdit, QCheckBox]] = {}
        form = QFormLayout()
        for c in columns:
            e = QLineEdit()
            hint = "auto" if c.autoinc else (f"default {c.default}" if c.default is not None else
                                             ("required" if c.notnull else "empty = NULL"))
            e.setPlaceholderText(hint)
            null = QCheckBox("NULL")
            null.setEnabled(not c.notnull)
            null.toggled.connect(lambda on, e=e: e.setEnabled(not on))
            row = QHBoxLayout()
            row.addWidget(e, 1)
            row.addWidget(null)
            lab = f"{c.name} ({c.type})" if c.type else c.name
            form.addRow(("\U0001F511 " if c.pk else "") + lab + ":", row)
            self.edits[c.name] = (e, null)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(QLabel("Leave a field empty to use the column's default value."))
        lay.addWidget(bb)
        self.resize(460, min(700, 120 + 32 * len(columns)))

    def set_text(self, name: str, text: str) -> None:
        self.edits[name][0].setText(text)

    def values(self, db: D.Database) -> dict:
        out = {}
        for c in self.columns:
            e, null = self.edits[c.name]
            if null.isChecked():
                out[c.name] = None
            elif e.text() != "":
                out[c.name] = db.coerce(c, e.text())
        return out


# =============================================================================== table data view
class TableDataView(QWidget):
    """Document tab with the data of one table (WebMatrix "Data" view)."""

    def __init__(self, panel: "DatabasesPanel", conn: str, db: D.Database, table: str):
        super().__init__()
        self.panel, self.conn, self.db, self.table = panel, conn, db, table
        self.model = TableModel(db, table, int(panel.settings_value("databases/page_size", 200) or 200), self)
        self.model.error.connect(self._error)
        self.model.loaded.connect(self._update_status)
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setSortingEnabled(False)
        self.view.horizontalHeader().setSectionsClickable(True)
        self.view.horizontalHeader().sectionClicked.connect(self._sort_by)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                  | QAbstractItemView.EditTrigger.EditKeyPressed
                                  | QAbstractItemView.EditTrigger.AnyKeyPressed)
        self.view.setAlternatingRowColors(True)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._menu)
        self.view.verticalHeader().setDefaultSectionSize(22)

        tb = QToolBar()
        tb.setIconSize(tb.iconSize() * 0.8)
        self.a_refresh = tb.addAction(_std_icon(self, "SP_BrowserReload"), "Refresh", self.refresh)
        self.a_refresh.setShortcut(QKeySequence("F5"))
        self.a_refresh.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.addAction(self.a_refresh)
        tb.addSeparator()
        self.a_new = tb.addAction(_std_icon(self, "SP_FileDialogNewFolder"), "New Row", self.new_row)
        self.a_del = tb.addAction(_std_icon(self, "SP_TrashIcon"), "Delete", self.delete_selected)
        self.a_del.setShortcut(QKeySequence("Ctrl+Delete"))
        self.a_del.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.addAction(self.a_del)
        self.a_null = tb.addAction("Set NULL", self.set_null)
        tb.addSeparator()
        tb.addAction("Schema", lambda: panel.open_schema(conn, table))
        tb.addAction("Query", lambda: panel.open_query(conn, f"SELECT * FROM {db.q(table)}"))
        tb.addAction("Export CSV...", lambda: panel.export_csv(conn, table))
        tb.addSeparator()
        tb.addWidget(QLabel(" Filter (WHERE): "))
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("e.g. Price > 10 AND Name LIKE 'A%'  (Enter)")
        self.filter.setMinimumWidth(220)
        self.filter.returnPressed.connect(self.apply_filter)
        tb.addWidget(self.filter)
        bar = QToolBar()
        self.a_first = bar.addAction("|<", lambda: self.model.go_page(1))
        self.a_prev = bar.addAction("<", lambda: self.model.go_page(self.model.page() - 1))
        self.page_label = QLabel()
        bar.addWidget(self.page_label)
        self.a_next = bar.addAction(">", lambda: self.model.go_page(self.model.page() + 1))
        self.a_last = bar.addAction(">|", lambda: self.model.go_page(self.model.page_count()))
        bar.addWidget(QLabel("  Rows per page: "))
        self.size = QComboBox()
        self.size.addItems(["50", "100", "200", "500", "1000"])
        self.size.setCurrentText(str(self.model.page_size))
        self.size.currentTextChanged.connect(self._page_size)
        bar.addWidget(self.size)
        self.status = QLabel()
        self.status.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(tb)
        lay.addWidget(self.view, 1)
        row = QHBoxLayout()
        row.addWidget(bar)
        row.addWidget(self.status, 1)
        lay.addLayout(row)
        self.model.load()
        self.view.resizeColumnsToContents()
        for i in range(self.model.columnCount()):
            if self.view.columnWidth(i) > 320:
                self.view.setColumnWidth(i, 320)

    def refresh(self):
        self.model.load()

    def apply_filter(self):
        self.model.where = self.filter.text().strip()
        self.model.offset = 0
        self.model.load()

    def _page_size(self, text):
        try:
            self.model.page_size = max(1, int(text))
        except ValueError:
            return
        self.model.offset = 0
        self.model.load()
        self.panel.set_setting("databases/page_size", self.model.page_size)

    def _sort_by(self, col):
        m = self.model
        name = m.columns[col].name if 0 <= col < len(m.columns) else ""
        desc = (not m.descending) if name == m.order_by else False
        m.sort(col, Qt.SortOrder.DescendingOrder if desc else Qt.SortOrder.AscendingOrder)

    def _update_status(self):
        m = self.model
        first = m.offset + 1 if m.rowCount() else 0
        self.page_label.setText(f"  Page {m.page()} of {m.page_count()}  ")
        ro = "" if m.editable else "  (read-only view)"
        self.status.setStyleSheet("")
        self.status.setText(f"  Rows {first}-{m.offset + m.rowCount()} of {m.total}{ro}")
        for a in (self.a_new, self.a_del, self.a_null):
            a.setEnabled(m.editable)
        self.a_prev.setEnabled(m.page() > 1)
        self.a_first.setEnabled(m.page() > 1)
        self.a_next.setEnabled(m.page() < m.page_count())
        self.a_last.setEnabled(m.page() < m.page_count())

    def _error(self, text):
        self.status.setStyleSheet(f"color: {ERROR_COLOR};")
        self.status.setText("  " + text)
        self.panel.log(f"[{self.conn}] {self.table}: {text}")

    def selected_rows(self) -> list[int]:
        return sorted({i.row() for i in self.view.selectionModel().selectedIndexes()})

    def new_row(self, values: dict | None = None):
        if values is None:
            dlg = RowDialog(self.model.columns, self, f"New Row - {self.table}")
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return False
            values = dlg.values(self.db)
        return self.model.insert_row(values)

    def delete_selected(self, confirm: bool = True):
        rows = self.selected_rows()
        if not rows:
            return 0
        if confirm and QMessageBox.question(self, "Delete rows", f"Delete {len(rows)} row(s) from {self.table}?") \
                != QMessageBox.StandardButton.Yes:
            return 0
        n = self.model.delete_rows(rows)
        if n:
            self.status.setText(f"  {n} row(s) deleted - {self.model.total} left")
        return n

    def set_null(self):
        for i in self.view.selectionModel().selectedIndexes():
            self.model.set_null(i)

    def _menu(self, pos):
        m = QMenu(self)
        ix = self.view.indexAt(pos)
        if ix.isValid():
            m.addAction("Copy", lambda: QApplication.clipboard().setText(
                "\n".join("\t".join(self.model.data(self.model.index(r, c)) or "" for c in sorted(
                    {i.column() for i in self.view.selectedIndexes()})) for r in self.selected_rows())))
            m.addAction("Set to NULL", self.set_null).setEnabled(self.model.editable)
            m.addSeparator()
        m.addAction("New Row...", self.new_row).setEnabled(self.model.editable)
        m.addAction("Delete Selected Rows", self.delete_selected).setEnabled(self.model.editable and ix.isValid())
        m.addSeparator()
        m.addAction("Refresh", self.refresh)
        m.exec(self.view.viewport().mapToGlobal(pos))


# =============================================================================== schema view
class SchemaView(QWidget):
    def __init__(self, panel: "DatabasesPanel", conn: str, db: D.Database, table: str):
        super().__init__()
        self.panel, self.conn, self.db, self.table = panel, conn, db, table
        tb = QToolBar()
        tb.addAction(_std_icon(self, "SP_BrowserReload"), "Refresh", self.refresh)
        tb.addSeparator()
        self.a_add = tb.addAction("Add Column...", self.add_column)
        self.a_drop = tb.addAction("Drop Column", self.drop_column)
        tb.addSeparator()
        tb.addAction("Data", lambda: panel.open_table(conn, table))
        tb.addAction("Export SQL...", lambda: panel.export_sql(conn, table))
        self.cols = QTableWidget(0, 6)
        self.cols.setHorizontalHeaderLabels(["Column", "Type", "Primary Key", "Not Null", "Default", "Auto"])
        self.cols.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.cols.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cols.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.cols.horizontalHeader().setStretchLastSection(True)
        self.idx = QTreeWidget()
        self.idx.setHeaderLabels(["Index / Foreign key", "Columns", "Details"])
        self.idx.setRootIsDecorated(False)
        self.sql = QPlainTextEdit()
        self.sql.setReadOnly(True)
        self.sql.setFont(QFont("Consolas", 10))
        SqlHighlighter(self.sql.document())
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.cols)
        split.addWidget(self.idx)
        split.addWidget(self.sql)
        split.setSizes([300, 120, 160])
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(tb)
        lay.addWidget(split, 1)
        self.refresh()

    def refresh(self):
        try:
            cols = self.db.columns(self.table)
            view = self.db.is_view(self.table)
            ixs = [] if view else self.db.indexes(self.table)
            fks = [] if view else self.db.foreign_keys(self.table)
            create = self.db.create_sql(self.table)
        except D.DatabaseError as e:
            self.sql.setPlainText(f"-- error: {e}")
            return
        self.a_add.setEnabled(not view)
        self.a_drop.setEnabled(not view)
        self.cols.setRowCount(len(cols))
        for r, c in enumerate(cols):
            vals = [c.name, c.type, f"yes ({c.pk})" if c.pk > 1 or sum(1 for x in cols if x.pk) > 1 else
                    ("yes" if c.pk else ""), "yes" if c.notnull else "", "" if c.default is None else c.default,
                    "yes" if c.autoinc else ""]
            for k, v in enumerate(vals):
                self.cols.setItem(r, k, QTableWidgetItem(v))
        self.idx.clear()
        for ix in ixs:
            QTreeWidgetItem(self.idx, [ix.name, ", ".join(ix.columns),
                                       "primary key" if ix.primary else ("unique" if ix.unique else "index")])
        for fk in fks:
            QTreeWidgetItem(self.idx, ["FOREIGN KEY", ", ".join(fk.columns),
                                       f"-> {fk.ref_table}({', '.join(fk.ref_columns)})"
                                       + (f" ON DELETE {fk.on_delete}" if fk.on_delete and fk.on_delete != "NO ACTION"
                                          else "")])
        self.sql.setPlainText(create)

    def add_column(self):
        dlg = AddColumnDialog(self.db, self.table, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                sql = self.db.add_column(self.table, dlg.column())
            except D.DatabaseError as e:
                QMessageBox.warning(self, "Add Column", str(e))
                return
            self.panel.log(f"[{self.conn}] {sql}")
            self.refresh()
            self.panel.table_changed(self.conn, self.table)

    def drop_column(self):
        r = self.cols.currentRow()
        if r < 0:
            return
        name = self.cols.item(r, 0).text()
        if QMessageBox.question(self, "Drop Column", f"Drop column {name} from {self.table}? Its data is lost.") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            sql = self.db.drop_column(self.table, name)
        except D.DatabaseError as e:
            QMessageBox.warning(self, "Drop Column", str(e))
            return
        self.panel.log(f"[{self.conn}] {sql}")
        self.refresh()
        self.panel.table_changed(self.conn, self.table)


# =============================================================================== query view
class QueryView(QWidget):
    """SQL window: editor + results (one grid per result set) + messages."""

    def __init__(self, panel: "DatabasesPanel", conn: str, db: D.Database, sql: str = ""):
        super().__init__()
        self.panel, self.conn, self.db = panel, conn, db
        self.path: Path | None = None
        self.results: list[D.Result] = []
        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setPlaceholderText("Type SQL here.  F5 / Ctrl+Enter = run (the selection only, if any).")
        self.editor.setPlainText(sql)
        SqlHighlighter(self.editor.document())
        tb = QToolBar()
        a = tb.addAction(_std_icon(self, "SP_MediaPlay"), "Run", self.run)
        a.setShortcuts([QKeySequence("F5"), QKeySequence("Ctrl+Return"), QKeySequence("Ctrl+Enter")])
        a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.addAction(a)
        tb.addSeparator()
        tb.addAction(_std_icon(self, "SP_DialogOpenButton"), "Open .sql...", self.open_file)
        tb.addAction(_std_icon(self, "SP_DialogSaveButton"), "Save .sql...", self.save_file)
        tb.addSeparator()
        self.stop_on_error = QCheckBox("Stop on first error")
        self.stop_on_error.setChecked(True)
        tb.addWidget(self.stop_on_error)
        tb.addWidget(QLabel(f"   Connection: {conn}  ({db.info.describe(panel.base_of(conn))})"))
        self.tabs = QTabWidget()
        self.messages = QPlainTextEdit()
        self.messages.setReadOnly(True)
        self.messages.setFont(QFont("Consolas", 9))
        self.tabs.addTab(self.messages, "Messages")
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.editor)
        split.addWidget(self.tabs)
        split.setSizes([220, 320])
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(tb)
        lay.addWidget(split, 1)

    def sql_to_run(self) -> tuple[str, int]:
        cur = self.editor.textCursor()
        if cur.hasSelection():
            doc = self.editor.document()
            first = doc.findBlock(cur.selectionStart()).blockNumber()
            return cur.selectedText().replace(" ", "\n"), first
        return self.editor.toPlainText(), 0

    def run(self) -> list[D.Result]:
        sql, line_offset = self.sql_to_run()
        if not sql.strip():
            return []
        with _wait_cursor():
            results = self.db.execute(sql, stop_on_error=self.stop_on_error.isChecked())
        for r in results:
            r.line += line_offset
        self.show_results(results)
        if any(not re.match(r"\s*(SELECT|PRAGMA|SHOW|EXPLAIN|WITH|DESCRIBE|VALUES)\b", r.statement, re.IGNORECASE)
               for r in results if r.ok):
            self.panel.refresh_connection(self.conn)        # tables may have changed
        return results

    def show_results(self, results: list[D.Result]):
        self.results = results
        while self.tabs.count() > 1:
            w = self.tabs.widget(1)
            self.tabs.removeTab(1)
            w.deleteLater()
        lines = []
        err = None
        for n, r in enumerate(results, 1):
            lines.append(r.message())
            if r.error and err is None:
                err = r
            if r.is_query:
                grid = QTableWidget(len(r.rows), len(r.columns))
                grid.setHorizontalHeaderLabels(r.columns)
                grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                for i, row in enumerate(r.rows):
                    for j, v in enumerate(row):
                        it = QTableWidgetItem(D.display_value(v))
                        if v is None:
                            it.setForeground(NULL_BRUSH)
                        grid.setItem(i, j, it)
                grid.resizeColumnsToContents()
                self.tabs.addTab(grid, f"Result {n} ({len(r.rows)}{'+' if r.truncated else ''})")
        self.messages.setPlainText("\n".join(lines) or "Nothing to run.")
        if err is not None:
            self.messages.appendHtml(f"<p style='color:{ERROR_COLOR}'><b>Error</b> in the statement at line "
                                     f"{err.line}:<br>{_html(err.error)}<br><code>{_html(err.statement[:300])}</code></p>")
            self.tabs.setCurrentIndex(0)
            self._goto_line(err.line)
        elif self.tabs.count() > 1:
            self.tabs.setCurrentIndex(self.tabs.count() - 1 if len(results) == 1 else 1)
        else:
            self.tabs.setCurrentIndex(0)

    def _goto_line(self, line: int):
        block = self.editor.document().findBlockByNumber(max(0, line - 1))
        if block.isValid():
            cur = self.editor.textCursor()
            cur.setPosition(block.position())
            self.editor.setTextCursor(cur)

    def open_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open SQL script", str(self.panel.base_of(self.conn) or ""),
                                           "SQL (*.sql);;All files (*.*)")
        if f:
            self.path = Path(f)
            self.editor.setPlainText(D._read_text_file(self.path))

    def save_file(self):
        f, _ = QFileDialog.getSaveFileName(self, "Save SQL script", str(self.path or self.panel.base_of(self.conn)
                                                                        or ""), "SQL (*.sql)")
        if f:
            self.path = Path(f)
            self.path.write_text(self.editor.toPlainText(), encoding="utf-8")


def _html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")


# =============================================================================== dialogs
class CreateTableDialog(QDialog):
    """New Table: name + column grid (name, type, PK, auto, not null, unique, default) + SQL preview."""
    HEAD = ["Name", "Type", "Primary Key", "Auto Increment", "Not Null", "Unique", "Default"]

    def __init__(self, db: D.Database, parent=None, name: str = ""):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("New Table")
        self.name = QLineEdit(name or "NewTable")
        self.grid = QTableWidget(0, len(self.HEAD))
        self.grid.setHorizontalHeaderLabels(self.HEAD)
        self.grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.grid.horizontalHeader().setStretchLastSection(True)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas", 9))
        SqlHighlighter(self.preview.document())
        self.error = QLabel()
        self.error.setStyleSheet(f"color: {ERROR_COLOR};")
        add = QPushButton("Add Column")
        add.clicked.connect(lambda: self.add_column())
        rem = QPushButton("Remove Column")
        rem.clicked.connect(self.remove_column)
        up = QPushButton("Up")
        up.clicked.connect(lambda: self._move(-1))
        down = QPushButton("Down")
        down.clicked.connect(lambda: self._move(1))
        btns = QHBoxLayout()
        for b in (add, rem, up, down):
            btns.addWidget(b)
        btns.addStretch(1)
        self.bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.bb.button(QDialogButtonBox.StandardButton.Ok).setText("Create")
        self.bb.accepted.connect(self._accept)
        self.bb.rejected.connect(self.reject)
        form = QFormLayout()
        form.addRow("Table name:", self.name)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(self.grid, 1)
        lay.addLayout(btns)
        lay.addWidget(QLabel("SQL:"))
        lay.addWidget(self.preview)
        lay.addWidget(self.error)
        lay.addWidget(self.bb)
        self.name.textChanged.connect(self.update_preview)
        self.grid.itemChanged.connect(self.update_preview)
        auto_type = {"sqlite": "INTEGER", "mysql": "INT", "postgresql": "integer"}.get(db.dialect, "INTEGER")
        text_type = {"sqlite": "TEXT", "mysql": "VARCHAR(255)", "postgresql": "text"}.get(db.dialect, "TEXT")
        self.add_column(D.ColumnDef("Id", auto_type, pk=True, autoinc=True))
        self.add_column(D.ColumnDef("Name", text_type, notnull=True))
        self.resize(780, 520)
        self.update_preview()

    def add_column(self, c: D.ColumnDef | None = None):
        c = c or D.ColumnDef(f"Column{self.grid.rowCount() + 1}",
                             {"mysql": "VARCHAR(255)", "postgresql": "text"}.get(self.db.dialect, "TEXT"))
        self.grid.blockSignals(True)
        r = self.grid.rowCount()
        self.grid.insertRow(r)
        self.grid.setItem(r, 0, QTableWidgetItem(c.name))
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(self.db.types)
        combo.setCurrentText(c.type)
        combo.currentTextChanged.connect(self.update_preview)
        self.grid.setCellWidget(r, 1, combo)
        for k, on in ((2, c.pk), (3, c.autoinc), (4, c.notnull), (5, c.unique)):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            it.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
            self.grid.setItem(r, k, it)
        d = QTableWidgetItem(c.default)
        d.setToolTip("Default value: 0, abc (quoted for you), 'text', CURRENT_TIMESTAMP, (expression)")
        self.grid.setItem(r, 6, d)
        self.grid.blockSignals(False)
        self.update_preview()

    def remove_column(self):
        r = self.grid.currentRow()
        if r >= 0:
            self.grid.removeRow(r)
            self.update_preview()

    def _move(self, delta: int):
        r = self.grid.currentRow()
        defs = self.columns()
        t = r + delta
        if r < 0 or not (0 <= t < len(defs)):
            return
        defs[r], defs[t] = defs[t], defs[r]
        self.grid.setRowCount(0)
        for c in defs:
            self.add_column(c)
        self.grid.setCurrentCell(t, 0)

    def columns(self) -> list[D.ColumnDef]:
        out = []
        for r in range(self.grid.rowCount()):
            def chk(k):
                it = self.grid.item(r, k)
                return it is not None and it.checkState() == Qt.CheckState.Checked
            name = self.grid.item(r, 0).text().strip() if self.grid.item(r, 0) else ""
            combo = self.grid.cellWidget(r, 1)
            default = self.grid.item(r, 6).text() if self.grid.item(r, 6) else ""
            out.append(D.ColumnDef(name, combo.currentText().strip() if combo else "TEXT", chk(2), chk(4), chk(3),
                                   chk(5), default))
        return out

    def sql(self) -> str:
        return self.db.ddl_create_table(self.name.text().strip(), self.columns())

    def update_preview(self, *_):
        try:
            self.preview.setPlainText(self.sql())
            self.error.setText("")
            ok = True
        except D.DatabaseError as e:
            self.preview.setPlainText("")
            self.error.setText(str(e))
            ok = False
        self.bb.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)

    def _accept(self):
        try:
            self.sql()
        except D.DatabaseError as e:
            self.error.setText(str(e))
            return
        self.accept()


class AddColumnDialog(QDialog):
    def __init__(self, db: D.Database, table: str, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle(f"Add Column - {table}")
        self.name = QLineEdit()
        self.type = QComboBox()
        self.type.setEditable(True)
        self.type.addItems(db.types)
        self.type.setCurrentText({"mysql": "VARCHAR(255)", "postgresql": "text"}.get(db.dialect, "TEXT"))
        self.notnull = QCheckBox("Not Null (needs a default when the table has rows)")
        self.unique = QCheckBox("Unique")
        self.unique.setVisible(db.dialect != "sqlite")      # SQLite cannot ADD a UNIQUE column
        self.default = QLineEdit()
        self.default.setPlaceholderText("none  (0, text, 'text', CURRENT_TIMESTAMP ...)")
        self.preview = QLabel()
        self.preview.setStyleSheet("font-family: Consolas;")
        self.preview.setWordWrap(True)
        form = QFormLayout(self)
        form.addRow("Name:", self.name)
        form.addRow("Type:", self.type)
        form.addRow("", self.notnull)
        form.addRow("", self.unique)
        form.addRow("Default:", self.default)
        form.addRow("SQL:", self.preview)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.table = table
        for w in (self.name, self.default):
            w.textChanged.connect(self._preview)
        self.type.currentTextChanged.connect(self._preview)
        self.notnull.toggled.connect(self._preview)
        self.unique.toggled.connect(self._preview)
        self.resize(480, 260)
        self._preview()

    def column(self) -> D.ColumnDef:
        return D.ColumnDef(self.name.text().strip(), self.type.currentText().strip(), False,
                           self.notnull.isChecked(), False, self.unique.isChecked(), self.default.text())

    def _preview(self, *_):
        self.preview.setText(self.db.ddl_add_column(self.table, self.column()) if self.name.text().strip() else "")


class ConnectionDialog(QDialog):
    """Add / edit a connection: SQLite file (existing or new), MySQL or PostgreSQL server."""

    def __init__(self, panel: "DatabasesPanel", info: D.ConnectionInfo | None = None, base: Path | None = None,
                 parent=None):
        super().__init__(parent)
        self.panel = panel
        self.base = base
        self.setWindowTitle("Database Connection")
        self.kind = QComboBox()
        for k, label in D.KINDS.items():
            avail = "" if D.driver_available(k) else f"  (needs {D.ADAPTERS[k].install_hint})"
            self.kind.addItem(label + avail, k)
        self.name = QLineEdit()
        self.stack = QStackedWidget()
        # sqlite page
        sp = QWidget()
        sf = QFormLayout(sp)
        self.path = QLineEdit()
        self.path.setPlaceholderText("App_Data/site.db")
        browse = QPushButton("Open...")
        browse.clicked.connect(self._browse)
        new = QPushButton("New...")
        new.clicked.connect(self._new_file)
        row = QHBoxLayout()
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        row.addWidget(new)
        sf.addRow("Database file:", row)
        sf.addRow("", QLabel("A file that does not exist yet is created when you connect."))
        # server page
        vp = QWidget()
        vf = QFormLayout(vp)
        self.host = QLineEdit("127.0.0.1")
        self.port = QSpinBox()
        self.port.setRange(0, 65535)
        self.port.setSpecialValueText("default")
        self.user = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.database = QComboBox()
        self.database.setEditable(True)
        self.schema = QLineEdit()
        self.schema.setPlaceholderText("public")
        self.remember = QCheckBox("Remember the password (in the IDE settings, never in the project)")
        store = panel.passwords
        self.remember_note = QLabel("Encrypted for your Windows account (DPAPI)." if store.secure else
                                    "Warning: only obfuscated on this system - anyone with your settings file "
                                    "can read it.")
        self.remember_note.setWordWrap(True)
        self.remember_note.setStyleSheet("color: #666;" if store.secure else f"color: {ERROR_COLOR};")
        vf.addRow("Server:", self.host)
        vf.addRow("Port:", self.port)
        vf.addRow("User:", self.user)
        vf.addRow("Password:", self.password)
        vf.addRow("Database:", self.database)
        self.schema_label = QLabel("Schema:")
        vf.addRow(self.schema_label, self.schema)
        vf.addRow("", self.remember)
        vf.addRow("", self.remember_note)
        self.stack.addWidget(sp)
        self.stack.addWidget(vp)
        self.status = QLabel()
        self.status.setWordWrap(True)
        test = QPushButton("Test Connection")
        test.clicked.connect(self.test)
        list_db = QPushButton("List Databases")
        list_db.clicked.connect(self.list_databases)
        self.list_db = list_db
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        top = QFormLayout()
        top.addRow("Type:", self.kind)
        top.addRow("Name:", self.name)
        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.stack)
        brow = QHBoxLayout()
        brow.addWidget(test)
        brow.addWidget(list_db)
        brow.addStretch(1)
        lay.addLayout(brow)
        lay.addWidget(self.status)
        lay.addWidget(bb)
        self.kind.currentIndexChanged.connect(self._kind_changed)
        if info is not None:
            self.kind.setCurrentIndex(max(0, self.kind.findData(info.kind)))
            self.name.setText(info.name)
            self.path.setText(info.path)
            self.host.setText(info.host)
            self.port.setValue(info.port or 0)
            self.user.setText(info.user)
            self.database.setCurrentText(info.database)
            self.schema.setText(info.schema)
            self.remember.setChecked(info.remember_password)
            if info.needs_password:
                self.password.setText(panel.passwords.get(info, panel.key_folder(base)) or "")
        self._kind_changed()
        self.resize(560, 360)

    def _kind_changed(self, *_):
        k = self.kind.currentData()
        self.stack.setCurrentIndex(0 if k == "sqlite" else 1)
        self.schema.setVisible(k == "postgresql")
        self.schema_label.setVisible(k == "postgresql")
        self.list_db.setVisible(k != "sqlite")
        if k == "mysql" and not self.user.text():
            self.user.setText("root")
        if k == "postgresql" and self.user.text() in ("", "root"):
            self.user.setText("postgres")

    def _browse(self):
        f, _ = QFileDialog.getOpenFileName(self, "SQLite database", str(self.base or ""),
                                           "SQLite (*.db *.sqlite *.sqlite3 *.db3 *.sdb);;All files (*.*)")
        if f:
            self.path.setText(f)
            if not self.name.text():
                self.name.setText(Path(f).stem)

    def _new_file(self):
        start = str((self.base / "App_Data" / "site.db") if self.base else "site.db")
        f, _ = QFileDialog.getSaveFileName(self, "New SQLite database", start, "SQLite (*.db *.sqlite)")
        if f:
            self.path.setText(f)
            if not self.name.text():
                self.name.setText(Path(f).stem)

    def info(self) -> D.ConnectionInfo:
        k = self.kind.currentData()
        name = self.name.text().strip() or (Path(self.path.text()).stem if k == "sqlite" else
                                            (self.database.currentText() or k))
        return D.ConnectionInfo(name, k, self.path.text().strip(), self.host.text().strip() or "127.0.0.1",
                                self.port.value(), self.user.text().strip(), self.database.currentText().strip(),
                                self.schema.text().strip(), {}, self.remember.isChecked() and k != "sqlite")

    def _open(self) -> D.Database:
        info = self.info()
        if info.kind == "sqlite" and not info.path:
            raise D.DatabaseError("Choose a database file")
        return D.open_database(info, self.base, self.password.text())

    def test(self) -> bool:
        try:
            with _wait_cursor():
                db = self._open()
                ver = db.server_version()
                n = len(db.tables())
                db.close()
        except D.DatabaseError as e:
            self.status.setStyleSheet(f"color: {ERROR_COLOR};")
            self.status.setText(str(e))
            return False
        self.status.setStyleSheet("color: #087f23;")
        self.status.setText(f"Connected: {ver}, {n} table(s).")
        return True

    def list_databases(self):
        info = self.info()
        info.database = info.database if info.kind == "mysql" else (info.database or "postgres")
        if info.kind == "mysql":
            info.database = ""
        try:
            with _wait_cursor():
                db = D.open_database(info, self.base, self.password.text())
                names = db.databases()
                db.close()
        except D.DatabaseError as e:
            self.status.setStyleSheet(f"color: {ERROR_COLOR};")
            self.status.setText(str(e))
            return
        cur = self.database.currentText()
        self.database.clear()
        self.database.addItems(names)
        self.database.setCurrentText(cur or (names[0] if names else ""))
        self.status.setStyleSheet("")
        self.status.setText(f"{len(names)} database(s).")

    def _accept(self):
        info = self.info()
        if info.kind == "sqlite" and not info.path:
            self.status.setText("Choose a database file")
            return
        self.accept()


class ImportCsvDialog(QDialog):
    def __init__(self, db: D.Database, parent=None, table: str = "", path: str = ""):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Import CSV")
        self.file = QLineEdit(path)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        self.table = QComboBox()
        self.table.setEditable(True)
        try:
            self.table.addItems(db.tables())
        except D.DatabaseError:
            pass
        self.table.setCurrentText(table)
        self.header = QCheckBox("First row has the column names")
        self.header.setChecked(True)
        self.delim = QComboBox()
        for label, d in (("Detect", None), ("Comma ,", ","), ("Semicolon ;", ";"), ("Tab", "\t"), ("Pipe |", "|")):
            self.delim.addItem(label, d)
        self.empty_null = QCheckBox("Empty cells are NULL")
        self.empty_null.setChecked(True)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas", 9))
        self.preview.setMaximumHeight(150)
        row = QHBoxLayout()
        row.addWidget(self.file, 1)
        row.addWidget(browse)
        form = QFormLayout(self)
        form.addRow("CSV file:", row)
        form.addRow("Into table:", self.table)
        form.addRow("", QLabel("A new table name creates the table (column types are guessed)."))
        form.addRow("Delimiter:", self.delim)
        form.addRow("", self.header)
        form.addRow("", self.empty_null)
        form.addRow("Preview:", self.preview)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Import")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.file.textChanged.connect(self._preview)
        self.resize(560, 420)
        self._preview()

    def _browse(self):
        f, _ = QFileDialog.getOpenFileName(self, "CSV file", "", "CSV (*.csv *.txt *.tsv);;All files (*.*)")
        if f:
            self.file.setText(f)
            if not self.table.currentText():
                self.table.setCurrentText(re.sub(r"\W+", "_", Path(f).stem))

    def _preview(self, *_):
        p = Path(self.file.text())
        try:
            text = D._read_text_file(p) if p.is_file() else ""
        except OSError:
            text = ""
        self.preview.setPlainText("\n".join(text.splitlines()[:8]))

    def options(self) -> dict:
        return dict(table=self.table.currentText().strip(), path=Path(self.file.text().strip()),
                    header=self.header.isChecked(), delimiter=self.delim.currentData(),
                    empty_as_null=self.empty_null.isChecked())


# =============================================================================== Adminer tab
class AdminerTab(QWidget):
    """Adminer in a QWebEngineView (used when there is no web Preview dock)."""

    def __init__(self, url: str):
        super().__init__()
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        self.view = QWebEngineView()
        tb = QToolBar()
        tb.addAction(_std_icon(self, "SP_ArrowBack"), "Back", self.view.back)
        tb.addAction(_std_icon(self, "SP_ArrowForward"), "Forward", self.view.forward)
        tb.addAction(_std_icon(self, "SP_BrowserReload"), "Reload", self.view.reload)
        self.address = QLineEdit()
        self.address.setReadOnly(True)
        tb.addWidget(self.address)
        tb.addAction("Open in Browser", lambda: QDesktopServices.openUrl(self.view.url()))
        self.view.urlChanged.connect(lambda u: self.address.setText(u.toString()))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(tb)
        lay.addWidget(self.view, 1)
        self.load(url)

    def load(self, url: str):
        self.view.setUrl(QUrl(url))


# =============================================================================== the panel
KIND_CONN, KIND_TABLE, KIND_VIEW, KIND_FOLDER, KIND_DETECTED, KIND_PROJECT = range(6)


class DatabasesPanel(QWidget):
    """The Databases dock."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        settings = getattr(win, "settings", None)
        self.passwords = D.PasswordStore(settings if settings is not None else _MemSettings())
        self.open_dbs: dict[str, D.Database] = {}         # conn id -> connected adapter
        self.session_passwords: dict[str, str] = {}       # conn id -> password typed this session
        self.adminer: D.AdminerServer | None = None
        self.adminer_tab: AdminerTab | None = None
        self.views: dict[tuple, QWidget] = {}             # (kind, conn id, name) -> document widget
        self._query_no = 0
        self.managers: dict[str, D.ConnectionManager] = {}  # project key -> manager
        self.loose: D.ConnectionManager = D.ConnectionManager(None, None)   # connections without a project

        tb = QToolBar()
        tb.setIconSize(tb.iconSize() * 0.8)
        add = QAction(_std_icon(self, "SP_FileDialogNewFolder"), "New", self)
        menu = QMenu(self)
        menu.addAction("New SQLite Database...", self.new_sqlite_dialog)
        menu.addAction("Add Connection (SQLite / MySQL / PostgreSQL)...", self.add_connection_dialog)
        add.setMenu(menu)
        add.triggered.connect(self.add_connection_dialog)
        tb.addAction(add)
        tb.addAction(_std_icon(self, "SP_BrowserReload"), "Refresh", self.refresh)
        self.a_query = tb.addAction(_std_icon(self, "SP_FileDialogDetailedView"), "New Query",
                                    lambda: self._with_conn(self.open_query))
        self.a_table = tb.addAction(_std_icon(self, "SP_FileDialogListView"), "New Table",
                                    lambda: self._with_conn(self.create_table_dialog))
        self.a_adminer = tb.addAction(_std_icon(self, "SP_ComputerIcon"), "Open in Adminer",
                                      lambda: self._with_conn(self.open_adminer))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self._dclick)
        self.tree.itemExpanded.connect(self._expanded)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setStyleSheet("color: #555; padding: 2px;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(tb)
        lay.addWidget(self.tree, 1)
        lay.addWidget(self.info)
        self.refresh()

    # ------------------------------------------------------------------ helpers
    def log(self, text: str):
        try:
            self.win.log(text)
        except Exception:  # noqa: BLE001
            pass

    def settings_value(self, key, default=None):
        s = getattr(self.win, "settings", None)
        return s.value(key, default) if s is not None else default

    def set_setting(self, key, value):
        s = getattr(self.win, "settings", None)
        if s is not None:
            s.setValue(key, value)

    def _projects(self) -> list:
        fn = getattr(self.win, "projects", None)
        try:
            ps = list(fn()) if callable(fn) else []
        except Exception:  # noqa: BLE001
            ps = []
        if not ps and getattr(self.win, "project", None) is not None:
            ps = [self.win.project]
        return ps

    def _pkey(self, project) -> str:
        return str(Path(project.folder).resolve()).lower()

    def manager_for(self, project) -> D.ConnectionManager:
        if project is None:
            return self.loose
        k = self._pkey(project)
        m = self.managers.get(k)
        if m is None or m.project is not project:
            m = self.managers[k] = D.ConnectionManager(project)
        return m

    @staticmethod
    def conn_id(manager: D.ConnectionManager, name: str) -> str:
        return f"{manager.folder or ''}|{name}".lower()

    def _split_id(self, cid: str) -> tuple[D.ConnectionManager, D.ConnectionInfo] | None:
        for m in list(self.managers.values()) + [self.loose]:
            for c in m.connections:
                if self.conn_id(m, c.name) == cid:
                    return m, c
        return None

    def connection(self, name: str, project=None) -> str | None:
        """The id of a connection by name (in ``project`` or any open project)."""
        ms = [self.manager_for(project)] if project is not None else list(self.managers.values()) + [self.loose]
        for m in ms:
            c = m.find(name)
            if c is not None:
                return self.conn_id(m, c.name)
        return None

    def base_of(self, cid: str) -> Path | None:
        s = self._split_id(cid)
        return s[0].folder if s else None

    @staticmethod
    def key_folder(base) -> Path | None:
        return Path(base) if base else None

    def _resolve(self, conn) -> str:
        """Accept a connection id or a connection name."""
        if self._split_id(conn) is not None:
            return conn
        cid = self.connection(conn)
        if cid is None:
            raise D.DatabaseError(f"No connection named {conn!r}")
        return cid

    # ------------------------------------------------------------------ tree
    def refresh(self):
        """Rebuild the tree from the open projects (keeps connections that are open)."""
        expanded = {self._item_key(it) for it in self._all_items() if it.isExpanded()}
        self.tree.clear()
        projects = self._projects()
        keys = {self._pkey(p) for p in projects}
        for k in list(self.managers):
            if k not in keys:
                m = self.managers.pop(k)
                for c in m.connections:
                    self._close_db(self.conn_id(m, c.name))
        groups = [(p, self.manager_for(p)) for p in projects]
        if self.loose.connections:
            groups.append((None, self.loose))
        multi = len(groups) > 1
        for p, m in groups:
            m.load() if p is not None else None
            parent = self.tree.invisibleRootItem()
            if multi:
                parent = QTreeWidgetItem(self.tree, [p.name if p is not None else "Other connections"])
                parent.setData(0, ROLE, (KIND_PROJECT, ""))
                parent.setIcon(0, _std_icon(self, "SP_DirIcon"))
                f = parent.font(0)
                f.setBold(True)
                parent.setFont(0, f)
                parent.setExpanded(True)
            for c in m.connections:
                self._add_conn_item(parent, m, c)
            for path in m.detect_sqlite_files():
                it = QTreeWidgetItem(parent, [f"{path.name}  (found in project)"])
                it.setData(0, ROLE, (KIND_DETECTED, str(path)))
                it.setToolTip(0, f"{path}\nDouble-click to add it to the project's connections")
                it.setIcon(0, _std_icon(self, "SP_FileIcon"))
                it.setData(1, ROLE, (p.folder if p is not None else None))
        for it in self._all_items():
            if self._item_key(it) in expanded:
                it.setExpanded(True)
        n = sum(len(m.connections) for _p, m in groups)
        self.info.setText("No project open - connections added now are kept for this session only."
                          if not projects else f"{n} connection(s). Double-click a table to edit its data.")

    def _add_conn_item(self, parent, m: D.ConnectionManager, c: D.ConnectionInfo):
        cid = self.conn_id(m, c.name)
        it = QTreeWidgetItem(parent, [c.name])
        it.setData(0, ROLE, (KIND_CONN, cid))
        it.setToolTip(0, c.describe(m.folder))
        it.setIcon(0, _std_icon(self, "SP_DriveHDIcon"))
        it.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        if cid in self.open_dbs:
            self._fill_conn(it)
        return it

    def _all_items(self):
        stack = [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]
        while stack:
            it = stack.pop()
            yield it
            stack += [it.child(i) for i in range(it.childCount())]

    @staticmethod
    def _item_key(it) -> tuple:
        d = it.data(0, ROLE) or (None, "")
        return (d[0], d[1], it.text(0))

    def conn_item(self, cid: str):
        for it in self._all_items():
            d = it.data(0, ROLE)
            if d and d[0] == KIND_CONN and d[1] == cid:
                return it
        return None

    def _fill_conn(self, it) -> bool:
        cid = it.data(0, ROLE)[1]
        db = self.db(cid)
        if db is None:
            return False
        try:
            tables, views = db.tables(), db.views()
        except D.DatabaseError as e:
            self.log(f"[databases] {e}")
            return False
        it.takeChildren()
        tf = QTreeWidgetItem(it, [f"Tables ({len(tables)})"])
        tf.setData(0, ROLE, (KIND_FOLDER, cid))
        tf.setIcon(0, _std_icon(self, "SP_DirIcon"))
        for t in tables:
            x = QTreeWidgetItem(tf, [t])
            x.setData(0, ROLE, (KIND_TABLE, cid))
            x.setIcon(0, _std_icon(self, "SP_FileDialogListView"))
        if views:
            vf = QTreeWidgetItem(it, [f"Views ({len(views)})"])
            vf.setData(0, ROLE, (KIND_FOLDER, cid))
            vf.setIcon(0, _std_icon(self, "SP_DirIcon"))
            for v in views:
                x = QTreeWidgetItem(vf, [v])
                x.setData(0, ROLE, (KIND_VIEW, cid))
                x.setIcon(0, _std_icon(self, "SP_FileDialogContentsView"))
        tf.setExpanded(True)
        it.setToolTip(0, it.toolTip(0).split("\n")[0] + f"\n{db.server_version()}")
        return True

    def refresh_connection(self, cid: str):
        it = self.conn_item(cid)
        if it is not None and cid in self.open_dbs:
            self._fill_conn(it)
            it.setExpanded(True)

    def table_changed(self, cid: str, table: str):
        v = self.views.get(("data", cid, table))
        if isinstance(v, TableDataView):
            v.model.load()
        self.refresh_connection(cid)

    def _expanded(self, it):
        d = it.data(0, ROLE)
        if d and d[0] == KIND_CONN and it.childCount() == 0:
            if not self._fill_conn(it):
                it.setExpanded(False)

    def _selected(self):
        it = self.tree.currentItem()
        if it is None:
            return None, None
        d = it.data(0, ROLE)
        return it, d

    def _with_conn(self, fn):
        it, d = self._selected()
        cid = None
        if d and d[0] in (KIND_CONN, KIND_TABLE, KIND_VIEW, KIND_FOLDER):
            cid = d[1]
        if cid is None:
            ids = [self.conn_id(m, c.name) for m in list(self.managers.values()) + [self.loose] for c in m.connections]
            if len(ids) == 1:
                cid = ids[0]
        if cid is None:
            QMessageBox.information(self, "Databases", "Select a connection first (or add one with New).")
            return
        fn(cid)

    def _dclick(self, it, _col):
        d = it.data(0, ROLE)
        if not d:
            return
        if d[0] in (KIND_TABLE, KIND_VIEW):
            self.open_table(d[1], it.text(0))
        elif d[0] == KIND_DETECTED:
            self.add_detected(it)

    # ------------------------------------------------------------------ connections
    def db(self, cid: str, ask: bool = True) -> D.Database | None:
        """The connected adapter of a connection (asks for the password if needed)."""
        cid = self._resolve(cid)
        db = self.open_dbs.get(cid)
        if db is not None:
            return db
        m, c = self._split_id(cid)
        pw = ""
        if c.needs_password:
            pw = self.session_passwords.get(cid)
            if pw is None and c.remember_password:
                pw = self.passwords.get(c, self.key_folder(m.folder))
            if pw is None:
                if not ask:
                    return None
                pw, ok = QInputDialog.getText(self, f"Connect to {c.name}", f"Password for {c.describe()}:",
                                              QLineEdit.EchoMode.Password)
                if not ok:
                    return None
        try:
            with _wait_cursor():
                db = D.open_database(c, m.folder, pw)
        except D.DatabaseError as e:
            self.session_passwords.pop(cid, None)
            QMessageBox.warning(self, f"Connect to {c.name}", str(e))
            return None
        if c.needs_password:
            self.session_passwords[cid] = pw
        self.open_dbs[cid] = db
        self.log(f"[databases] connected to {c.describe(m.folder)} ({db.server_version()})")
        return db

    def _close_db(self, cid: str):
        db = self.open_dbs.pop(cid, None)
        if db is not None:
            db.close()
        for key in [k for k in self.views if k[1] == cid]:
            w = self.views.pop(key)
            i = self.win.tabs.indexOf(w) if hasattr(self.win, "tabs") else -1
            if i >= 0:
                self.win.tabs.removeTab(i)
            w.deleteLater()

    def disconnect(self, cid: str):
        self._close_db(cid)
        it = self.conn_item(cid)
        if it is not None:
            it.takeChildren()
            it.setExpanded(False)

    def _target_manager(self) -> D.ConnectionManager:
        p = getattr(self.win, "project", None)
        it, d = self._selected()
        if d and d[0] == KIND_PROJECT:
            for m in self.managers.values():
                if m.project is not None and m.project.name == it.text(0):
                    return m
        if d and d[0] in (KIND_CONN, KIND_TABLE, KIND_VIEW, KIND_FOLDER):
            s = self._split_id(d[1])
            if s:
                return s[0]
        return self.manager_for(p)

    def add_connection(self, info: D.ConnectionInfo, password: str = "", project=None,
                       manager: D.ConnectionManager | None = None) -> str:
        m = manager or (self.manager_for(project) if project is not None else self._target_manager())
        info = m.add(info)
        cid = self.conn_id(m, info.name)
        if info.needs_password:
            self.session_passwords[cid] = password
            if info.remember_password:
                self.passwords.set(info, password, self.key_folder(m.folder))
        self.refresh()
        return cid

    def add_sqlite(self, path, project=None, name: str = "") -> str:
        """Add (and create if missing) a SQLite file as a connection; returns its id."""
        m = self.manager_for(project) if project is not None else self._target_manager()
        target = Path(path).resolve()
        for c in m.connections:
            if c.kind == "sqlite" and c.resolved_path(m.folder).resolve() == target:
                return self.conn_id(m, c.name)
        return self.add_connection(D.ConnectionInfo(name or target.stem, "sqlite", str(target)), manager=m)

    def add_detected(self, it):
        path = Path(it.data(0, ROLE)[1])
        folder = it.data(1, ROLE)
        m = self.loose
        for mm in self.managers.values():
            if folder is not None and mm.folder is not None and Path(folder) == mm.folder:
                m = mm
        cid = self.add_connection(D.ConnectionInfo(path.stem, "sqlite", str(path)), manager=m)
        ci = self.conn_item(cid)
        if ci is not None:
            ci.setExpanded(True)
            self.tree.setCurrentItem(ci)
        return cid

    def add_connection_dialog(self, info: D.ConnectionInfo | None = None):
        m = self._target_manager()
        dlg = ConnectionDialog(self, info, m.folder, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        return self.add_connection(dlg.info(), dlg.password.text(), manager=m)

    def new_sqlite_dialog(self):
        m = self._target_manager()
        start = (m.folder / "App_Data" / "site.db") if m.folder else Path("site.db")
        f, _ = QFileDialog.getSaveFileName(self, "New SQLite database", str(start), "SQLite (*.db *.sqlite)")
        if not f:
            return None
        D.SQLiteDatabase(f).connect().close()           # creates the file
        cid = self.add_sqlite(f)
        it = self.conn_item(cid)
        if it is not None:
            it.setExpanded(True)
        return cid

    def edit_connection(self, cid: str):
        m, c = self._split_id(cid)
        dlg = ConnectionDialog(self, c, m.folder, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new = dlg.info()
        self._close_db(cid)
        m.replace(c.name, new)
        ncid = self.conn_id(m, new.name)
        if new.needs_password:
            self.session_passwords[ncid] = dlg.password.text()
            if new.remember_password:
                self.passwords.set(new, dlg.password.text(), self.key_folder(m.folder))
            else:
                self.passwords.forget(new, self.key_folder(m.folder))
        self.refresh()

    def remove_connection(self, cid: str, confirm: bool = True):
        m, c = self._split_id(cid)
        if confirm and QMessageBox.question(self, "Remove connection",
                                            f"Remove the connection {c.name} from the project?\n"
                                            "(The database itself is not deleted.)") != QMessageBox.StandardButton.Yes:
            return
        self._close_db(cid)
        self.passwords.forget(c, self.key_folder(m.folder))
        m.remove(c.name)
        self.refresh()

    # ------------------------------------------------------------------ documents
    def _show(self, key: tuple, factory, title: str):
        w = self.views.get(key)
        tabs = getattr(self.win, "tabs", None)
        if w is not None and tabs is not None and tabs.indexOf(w) < 0:
            self.views.pop(key, None)
            w.deleteLater()
            w = None
        if w is None:
            w = factory()
            self.views[key] = w
        show = getattr(self.win, "_show_tab", None)
        if callable(show):
            show(w, title)
        elif tabs is not None:
            i = tabs.indexOf(w)
            tabs.setCurrentIndex(i if i >= 0 else tabs.addTab(w, title))
        return w

    def _label(self, cid: str) -> str:
        s = self._split_id(cid)
        return s[1].name if s else cid

    def open_table(self, conn, table: str):
        cid = self._resolve(conn)
        db = self.db(cid)
        if db is None:
            return None
        return self._show(("data", cid, table), lambda: TableDataView(self, cid, db, table),
                          f"{table} [{self._label(cid)}]")

    def open_schema(self, conn, table: str):
        cid = self._resolve(conn)
        db = self.db(cid)
        if db is None:
            return None
        return self._show(("schema", cid, table), lambda: SchemaView(self, cid, db, table),
                          f"{table} [Schema - {self._label(cid)}]")

    def open_query(self, conn, sql: str = ""):
        cid = self._resolve(conn)
        db = self.db(cid)
        if db is None:
            return None
        self._query_no += 1
        n = self._query_no
        return self._show(("query", cid, n), lambda: QueryView(self, cid, db, sql), f"SQLQuery{n} [{self._label(cid)}]")

    # ------------------------------------------------------------------ table operations
    def create_table_dialog(self, conn, name: str = ""):
        cid = self._resolve(conn)
        db = self.db(cid)
        if db is None:
            return None
        dlg = CreateTableDialog(db, self, name)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        table = dlg.name.text().strip()
        try:
            sql = db.create_table(table, dlg.columns())
        except D.DatabaseError as e:
            QMessageBox.warning(self, "New Table", str(e))
            return None
        self.log(f"[{self._label(cid)}] {sql}")
        self.refresh_connection(cid)
        self.open_table(cid, table)
        return table

    def add_column_dialog(self, conn, table: str):
        v = self.open_schema(conn, table)
        if v is not None:
            v.add_column()

    def drop_table(self, conn, table: str, confirm: bool = True) -> bool:
        cid = self._resolve(conn)
        db = self.db(cid)
        if db is None:
            return False
        if confirm and QMessageBox.question(self, "Delete table", f"Delete {table} and all its data?") \
                != QMessageBox.StandardButton.Yes:
            return False
        try:
            sql = db.drop_table(table)
        except D.DatabaseError as e:
            QMessageBox.warning(self, "Delete table", str(e))
            return False
        self.log(f"[{self._label(cid)}] {sql}")
        for kind in ("data", "schema"):
            w = self.views.pop((kind, cid, table), None)
            if w is not None:
                i = self.win.tabs.indexOf(w)
                if i >= 0:
                    self.win.tabs.removeTab(i)
                w.deleteLater()
        self.refresh_connection(cid)
        return True

    def rename_table(self, conn, table: str):
        cid = self._resolve(conn)
        db = self.db(cid)
        if db is None:
            return
        new, ok = QInputDialog.getText(self, "Rename table", "New name:", text=table)
        if not ok or not new.strip() or new.strip() == table:
            return
        try:
            sql = db.rename_table(table, new.strip())
        except D.DatabaseError as e:
            QMessageBox.warning(self, "Rename table", str(e))
            return
        self.log(f"[{self._label(cid)}] {sql}")
        self.refresh_connection(cid)

    def export_csv(self, conn, table: str, path=None):
        cid = self._resolve(conn)
        db = self.db(cid)
        if db is None:
            return 0
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, f"Export {table} to CSV",
                                                  str((self.base_of(cid) or Path.cwd()) / f"{table}.csv"),
                                                  "CSV (*.csv)")
            if not path:
                return 0
        try:
            with _wait_cursor():
                n = db.export_csv(table, Path(path))
        except (D.DatabaseError, OSError) as e:
            QMessageBox.warning(self, "Export CSV", str(e))
            return 0
        self.log(f"[{self._label(cid)}] exported {n} row(s) of {table} to {path}")
        return n

    def export_sql(self, conn, table: str | None = None, path=None):
        cid = self._resolve(conn)
        db = self.db(cid)
        if db is None:
            return 0
        if path is None:
            stem = table or self._label(cid)
            path, _ = QFileDialog.getSaveFileName(self, f"Export {stem} to SQL",
                                                  str((self.base_of(cid) or Path.cwd()) / f"{stem}.sql"), "SQL (*.sql)")
            if not path:
                return 0
        try:
            with _wait_cursor():
                n = db.export_sql(table, Path(path))
        except (D.DatabaseError, OSError) as e:
            QMessageBox.warning(self, "Export SQL", str(e))
            return 0
        self.log(f"[{self._label(cid)}] exported {n} table(s) to {path}")
        return n

    def import_csv_dialog(self, conn, table: str = ""):
        cid = self._resolve(conn)
        db = self.db(cid)
        if db is None:
            return 0
        dlg = ImportCsvDialog(db, self, table)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return 0
        o = dlg.options()
        if not o["table"] or not o["path"].is_file():
            QMessageBox.warning(self, "Import CSV", "Choose a CSV file and a table")
            return 0
        try:
            with _wait_cursor():
                n = db.import_csv(o["table"], o["path"], header=o["header"], create=True,
                                  delimiter=o["delimiter"], empty_as_null=o["empty_as_null"])
        except (D.DatabaseError, OSError) as e:
            QMessageBox.warning(self, "Import CSV", str(e))
            return 0
        self.log(f"[{self._label(cid)}] imported {n} row(s) into {o['table']}")
        self.table_changed(cid, o["table"])
        self.open_table(cid, o["table"])
        return n

    # ------------------------------------------------------------------ Adminer
    def adminer_server(self) -> D.AdminerServer:
        if self.adminer is None:
            php = ""
            s = getattr(self.win, "settings", None)
            if s is not None:
                php = s.value("interpreter/php-web", "") or s.value("interpreter/php", "") or ""
            self.adminer = D.AdminerServer(php)
            atexit.register(self.adminer.stop)
        return self.adminer

    def adminer_url(self, conn=None) -> str:
        srv = self.adminer_server()
        if conn is None:
            return srv.url_for(None)
        cid = self._resolve(conn)
        m, c = self._split_id(cid)
        pw = ""
        if c.needs_password:
            if self.db(cid) is None:              # makes sure we know the password
                raise D.DatabaseError("Not connected")
            pw = self.session_passwords.get(cid, "")
        return srv.url_for(c, m.folder, pw)

    def open_adminer(self, conn=None, in_tab: bool = False):
        try:
            with _wait_cursor():
                url = self.adminer_url(conn)
        except D.DatabaseError as e:
            QMessageBox.warning(self, "Adminer", str(e))
            return None
        self.log(f"[databases] Adminer: {self.adminer.base_url}")
        preview = getattr(self.win, "web_preview", None)
        if not in_tab and preview is not None and hasattr(preview, "open_url"):
            preview.open_url(url)
            if hasattr(preview, "show_dock"):
                preview.show_dock()
            return preview
        try:
            if self.adminer_tab is None or self.win.tabs.indexOf(self.adminer_tab) < 0:
                self.adminer_tab = AdminerTab(url)
            else:
                self.adminer_tab.load(url)
        except ImportError:
            QDesktopServices.openUrl(QUrl(url))
            return None
        self.win._show_tab(self.adminer_tab, "Adminer")
        return self.adminer_tab

    def shutdown(self):
        for cid in list(self.open_dbs):
            db = self.open_dbs.pop(cid)
            db.close()
        if self.adminer is not None:
            self.adminer.stop()

    # ------------------------------------------------------------------ context menu
    def _menu(self, pos):
        it = self.tree.itemAt(pos)
        m = QMenu(self)
        d = it.data(0, ROLE) if it is not None else None
        kind = d[0] if d else None
        if kind in (KIND_TABLE, KIND_VIEW):
            cid, t = d[1], it.text(0)
            m.addAction("Open Data", lambda: self.open_table(cid, t))
            m.addAction("Schema", lambda: self.open_schema(cid, t))
            m.addAction("New Query", lambda: self.open_query(cid, f"SELECT * FROM {self.db(cid).q(t)}"))
            m.addSeparator()
            if kind == KIND_TABLE:
                m.addAction("Add Column...", lambda: self.add_column_dialog(cid, t))
                m.addAction("Import CSV...", lambda: self.import_csv_dialog(cid, t))
            m.addAction("Export to CSV...", lambda: self.export_csv(cid, t))
            m.addAction("Export to SQL...", lambda: self.export_sql(cid, t))
            m.addSeparator()
            if kind == KIND_TABLE:
                m.addAction("Rename...", lambda: self.rename_table(cid, t))
            m.addAction("Delete", lambda: self.drop_table(cid, t))
        elif kind in (KIND_CONN, KIND_FOLDER):
            cid = d[1]
            m.addAction("New Query", lambda: self.open_query(cid))
            m.addAction("New Table...", lambda: self.create_table_dialog(cid))
            m.addAction("Import CSV into New Table...", lambda: self.import_csv_dialog(cid))
            m.addAction("Export Database to SQL...", lambda: self.export_sql(cid))
            m.addSeparator()
            m.addAction("Open in Adminer", lambda: self.open_adminer(cid))
            m.addAction("Open in Adminer (new tab)", lambda: self.open_adminer(cid, in_tab=True))
            m.addSeparator()
            m.addAction("Refresh", lambda: (self.refresh_connection(cid) if cid in self.open_dbs else None))
            if kind == KIND_CONN:
                if cid in self.open_dbs:
                    m.addAction("Disconnect", lambda: self.disconnect(cid))
                m.addAction("Properties...", lambda: self.edit_connection(cid))
                m.addAction("Remove Connection", lambda: self.remove_connection(cid))
        elif kind == KIND_DETECTED:
            m.addAction("Add to Project Connections", lambda: self.add_detected(it))
        else:
            m.addAction("New SQLite Database...", self.new_sqlite_dialog)
            m.addAction("Add Connection...", self.add_connection_dialog)
            m.addAction("Adminer (login page)", lambda: self.open_adminer(None))
            m.addAction("Refresh", self.refresh)
        m.exec(self.tree.viewport().mapToGlobal(pos))


class _MemSettings(dict):
    def value(self, k, d=None):
        return self.get(k, d)

    def setValue(self, k, v):
        self[k] = v

    def remove(self, k):
        self.pop(k, None)


# =============================================================================== install
def install(win) -> None:
    panel = DatabasesPanel(win)
    win.databases = panel
    dock = QDockWidget("Databases", win)
    dock.setObjectName("Databases")
    dock.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
    tb_dock = getattr(win, "dock_toolbox", None)
    if tb_dock is not None:
        win.tabifyDockWidget(tb_dock, dock)
        tb_dock.raise_()
    win.dock_databases = dock

    def show_databases():
        dock.show()
        dock.raise_()
        panel.refresh()
    a = QAction("&Databases", win)
    a.setShortcut(QKeySequence("Ctrl+Alt+D"))
    a.triggered.connect(show_databases)
    win.a_databases = a

    def menu_named(title):
        return next((x.menu() for x in win.menuBar().actions()
                     if x.menu() is not None and x.text().replace("&", "") == title), None)
    view = menu_named("View")
    if view is not None:
        view.addAction(a)
    tools = menu_named("Tools")
    if tools is not None:
        sub = tools.addMenu("&Databases")
        sub.addAction(a)
        sub.addAction("New SQLite Database...", lambda: (show_databases(), panel.new_sqlite_dialog()))
        sub.addAction("Add Connection...", lambda: (show_databases(), panel.add_connection_dialog()))
        sub.addAction("New Query", lambda: panel._with_conn(panel.open_query))
        sub.addAction("Open in Adminer", lambda: panel._with_conn(panel.open_adminer))

    # the web workspace (installed after us) creates win.site_menu: add our entries there too
    def add_to_site_menu():
        sm = getattr(win, "site_menu", None)
        if sm is not None and not getattr(win, "_db_site_menu", False):
            win._db_site_menu = True
            sm.addSeparator()
            sm.addAction(a)
            sm.addAction("Open Database in Adminer", lambda: panel._with_conn(panel.open_adminer))
    QTimer.singleShot(0, add_to_site_menu)

    # follow the open projects (open / close / add to solution all refill Solution Explorer)
    orig_fill = win._fill_solution

    def fill_solution(*a, **k):
        r = orig_fill(*a, **k)
        try:
            panel.refresh()
        except Exception as e:  # noqa: BLE001 - never break the Solution Explorer
            win.log(f"[databases] {e}")
        return r
    win._fill_solution = fill_solution

    app = QApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(panel.shutdown)
    win.destroyed.connect(lambda *_: panel.shutdown())
