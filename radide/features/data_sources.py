"""Data Sources window (Visual Basic 2005 "Data > Show Data Sources") - bind forms to real databases.

* **Add New Data Source...**: pick a connection of the Databases workspace (SQLite / MySQL / MariaDB /
  PostgreSQL, or an ODBC connection string when pyodbc is installed), tick tables / views or write a query.
  Every table becomes a data source of the form (typed: its columns, types and primary key are stored).
* **Drag a table onto the form**: a BindingNavigator (first / previous / position / next / last / add / delete /
  save) and a DataGridView - or, with the table's drop mode set to *Details*, a Label + TextBox / CheckBox per
  column.  Drag a single column for one Label + editor.  The designer shows real rows.
* Properties window: DataSource / DataMember / DisplayMember / ValueMember (Data category).
* Generated code: radide/databinding_sql.py (Fill / Update / AddNew / ... with parameterized SQL)."""
from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QMimeData, Qt, QTimer
from PyQt6.QtGui import QAction, QDrag, QKeySequence
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                             QMenu, QMessageBox, QPlainTextEdit, QPushButton, QRadioButton, QStyle,
                             QTableWidget, QTableWidgetItem, QTabWidget, QToolBar, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from .. import databinding_sql as DB
from .states import BlendPreview, current_view, follow_designer

ROLE = Qt.ItemDataRole.UserRole


def _std(widget, name: str):
    return widget.style().standardIcon(getattr(QStyle.StandardPixmap, name))


def _driver_ok(kind: str) -> bool:
    mod = DB.DRIVERS.get(kind)
    if not mod:
        return True
    try:
        __import__(mod)
        return True
    except ImportError:
        return False


# ====================================================================== connections / passwords
class Connections:
    """The Databases-workspace connections of the project a form belongs to, and their passwords."""

    def __init__(self, win):
        self.win = win
        self.session: dict[str, str] = {}           # snapshot key -> password typed here

    def panel(self):
        return getattr(self.win, "databases", None)

    def project_for(self, folder: Path):
        panel = self.panel()
        projects = panel._projects() if panel is not None else []
        if not projects and getattr(self.win, "project", None) is not None:
            projects = [self.win.project]
        folder = Path(folder).resolve()
        best = None
        for p in projects:
            try:
                pf = Path(p.folder).resolve()
            except (AttributeError, OSError):
                continue
            if folder == pf or pf in folder.parents:
                if best is None or len(str(pf)) > len(str(Path(best.folder).resolve())):
                    best = p
        return best

    def manager(self, folder: Path):
        from ..web_site.databases import ConnectionManager
        panel = self.panel()
        project = self.project_for(folder)
        if panel is not None:
            return panel.manager_for(project) if project is not None else panel.loose
        return ConnectionManager(project, None if project is not None else folder)

    @staticmethod
    def key(conn: dict) -> str:
        return json.dumps({k: conn.get(k) for k in ("kind", "host", "port", "user", "database", "odbc")},
                          sort_keys=True).lower()

    def known_password(self, conn: dict, folder: Path | None) -> str | None:
        """A password typed this session or remembered by the Databases workspace - never asks."""
        if conn.get("kind") == "sqlite":
            return ""
        k = self.key(conn)
        if k in self.session:
            return self.session[k]
        panel = self.panel()
        if panel is None:
            return None
        from ..web_site.databases import ConnectionInfo
        for m in list(getattr(panel, "managers", {}).values()) + [getattr(panel, "loose", None)]:
            if m is None:
                continue
            for c in m.connections:
                same = (c.kind == conn.get("kind") and c.host == conn.get("host") and c.user == conn.get("user")
                        and c.database == conn.get("database")
                        and c.effective_port() == int(conn.get("port") or c.effective_port()))
                if not same:
                    continue
                pw = panel.session_passwords.get(panel.conn_id(m, c.name))
                if pw is None and c.remember_password:
                    pw = panel.passwords.get(c, panel.key_folder(m.folder))
                if pw is not None:
                    return pw
        info = ConnectionInfo.from_dict(conn) if conn.get("kind") != "odbc" else None
        if info is not None and info.host in ("127.0.0.1", "localhost"):       # the IDE's local servers
            try:
                from ..web_site.dbservers import servers
                srv = servers().get(info.kind)
                if srv is not None and srv.initialized and srv.port == info.effective_port() and info.user == "radide":
                    return srv.password()
            except Exception:  # noqa: BLE001
                return None
        return None

    def password(self, parent, conn: dict, folder: Path | None, ask: bool = True) -> str | None:
        pw = self.known_password(conn, folder)
        if pw is not None or not ask:
            return pw
        if conn.get("kind") == "odbc" and "uid=" not in str(conn.get("odbc", "")).lower():
            return ""
        who = conn.get("user") or "the database"
        pw, ok = QInputDialog.getText(parent, f"Connect to {conn.get('name')}",
                                      f"Password for {who} ({conn.get('name')}):", QLineEdit.EchoMode.Password)
        if not ok:
            return None
        self.session[self.key(conn)] = pw
        return pw

    def open(self, parent, conn: dict, folder: Path | None):
        """A connected adapter (asks for the password); None when cancelled. Raises on errors."""
        pw = self.password(parent, conn, folder)
        if pw is None:
            return None
        try:
            return DB.open_db(conn, folder, pw)
        except Exception:
            self.session.pop(self.key(conn), None)
            raise


# ====================================================================== Add New Data Source
class AddDataSourceDialog(QDialog):
    """Data Source Configuration Wizard (one page): connection, then tables / views / a query."""

    def __init__(self, panel: "DataSourcesPanel", form_folder: Path):
        super().__init__(panel)
        self.panel, self.folder = panel, Path(form_folder)
        self.setWindowTitle("Add New Data Source")
        self.resize(560, 560)
        self.db = None
        self.conn: dict | None = None
        lay = QVBoxLayout(self)
        intro = QLabel("Choose a database connection, then the tables, views or a query the form shows. "
                       "Each one becomes a data source you can drag onto the form.")
        intro.setWordWrap(True)
        intro.setProperty("radRole", "note")
        lay.addWidget(intro)

        lay.addWidget(QLabel("<b>1. Which data connection?</b>"))
        self.r_conn = QRadioButton("Connection of the Databases workspace:")
        self.r_conn.setChecked(True)
        lay.addWidget(self.r_conn)
        row = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.setMinimumWidth(260)
        row.addWidget(self.combo, 1)
        b_new = QPushButton("New Connection...")
        b_new.setToolTip("Add a SQLite / MySQL / MariaDB / PostgreSQL connection (Databases workspace)")
        b_new.clicked.connect(self.new_connection)
        b_file = QPushButton("SQLite File...")
        b_file.setToolTip("Use an existing SQLite database file, or create a new one")
        b_file.clicked.connect(self.sqlite_file)
        row.addWidget(b_new)
        row.addWidget(b_file)
        lay.addLayout(row)
        self.r_odbc = QRadioButton("ODBC connection string:")
        lay.addWidget(self.r_odbc)
        self.odbc = QLineEdit()
        self.odbc.setPlaceholderText("DRIVER={SQL Server};SERVER=.\\SQLEXPRESS;DATABASE=Shop;Trusted_Connection=yes")
        self.odbc.textEdited.connect(lambda _t: self.r_odbc.setChecked(True))
        lay.addWidget(self.odbc)
        if not _driver_ok("odbc"):
            self.r_odbc.setEnabled(False)
            self.odbc.setEnabled(False)
            self.r_odbc.setText("ODBC connection string (needs pyodbc: pip install pyodbc)")
        row = QHBoxLayout()
        self.b_connect = QPushButton("Connect")
        self.b_connect.setDefault(True)
        self.b_connect.clicked.connect(self.connect_db)
        row.addWidget(self.b_connect)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setProperty("radRole", "muted")
        row.addWidget(self.status, 1)
        lay.addLayout(row)

        lay.addWidget(QLabel("<b>2. Choose your database objects</b>"))
        self.tabs = QTabWidget()
        self.objects = QTreeWidget()
        self.objects.setHeaderHidden(True)
        self.tabs.addTab(self.objects, "Tables and views")
        q = QWidget()
        fl = QFormLayout(q)
        self.q_name = QLineEdit()
        self.q_name.setPlaceholderText("e.g. CairoCustomers")
        self.q_sql = QPlainTextEdit()
        self.q_sql.setPlaceholderText("SELECT * FROM Customers WHERE City = 'Cairo'")
        self.q_table = QComboBox()
        self.q_table.setEditable(True)
        self.q_table.setToolTip("Rows edited through this query are saved to this table (needs its key)")
        self.q_key = QLineEdit()
        self.q_key.setPlaceholderText("Id  (empty = read-only)")
        fl.addRow("Name:", self.q_name)
        fl.addRow("SELECT:", self.q_sql)
        fl.addRow("Save to table:", self.q_table)
        fl.addRow("Key column(s):", self.q_key)
        self.tabs.addTab(q, "Query")
        lay.addWidget(self.tabs, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Finish")
        bb.accepted.connect(self.finish)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.created: list[dict] = []
        self.fill_connections()

    # ------------------------------------------------------------ connections
    def fill_connections(self, select: str = ""):
        self.combo.clear()
        m = self.panel.conns.manager(self.folder)
        for c in m.connections:
            ok = _driver_ok(c.kind)
            self.combo.addItem(f"{c.name}  ({c.describe(m.folder)})" + ("" if ok else "  - driver missing"), c.name)
        try:
            for p in m.detect_sqlite_files(20):
                self.combo.addItem(f"{p.name}  (SQLite file in the project)", f"file:{p}")
        except OSError:
            pass
        if select:
            i = self.combo.findData(select)
            if i >= 0:
                self.combo.setCurrentIndex(i)
        if not self.combo.count():
            self.status.setText("No connections yet: click New Connection... or SQLite File...")

    def new_connection(self):
        dbp = self.panel.conns.panel()
        if dbp is None:
            QMessageBox.information(self, "Add New Data Source", "The Databases workspace is not available.")
            return
        before = {c.name for c in self.panel.conns.manager(self.folder).connections}
        dbp.add_connection_dialog()
        after = [c.name for c in self.panel.conns.manager(self.folder).connections if c.name not in before]
        self.fill_connections(after[0] if after else "")
        self.r_conn.setChecked(True)

    def sqlite_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "SQLite database (existing or new)", str(self.folder / "data.db"),
                                              "SQLite (*.db *.sqlite *.sqlite3 *.db3);;All files (*.*)",
                                              options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:
            return
        from ..web_site.databases import SQLiteDatabase
        if not Path(path).exists():
            SQLiteDatabase(path).connect().close()
        m = self.panel.conns.manager(self.folder)
        info = m.add_sqlite(path)
        dbp = self.panel.conns.panel()
        if dbp is not None:
            try:
                dbp.refresh()
            except Exception:  # noqa: BLE001
                pass
        self.fill_connections(info.name)
        self.r_conn.setChecked(True)

    def current_conn(self) -> dict | None:
        if self.r_odbc.isChecked():
            text = self.odbc.text().strip()
            return DB.odbc_snapshot("Odbc", text) if text else None
        data = self.combo.currentData()
        if not data:
            return None
        m = self.panel.conns.manager(self.folder)
        if str(data).startswith("file:"):
            p = Path(str(data)[5:])
            info = m.add_sqlite(p)
        else:
            info = m.find(str(data))
        if info is None:
            return None
        return DB.snapshot(info, m.folder, self.folder)

    def connect_db(self) -> bool:
        conn = self.current_conn()
        if conn is None:
            self.status.setText("Choose a connection first.")
            return False
        if not _driver_ok(conn.get("kind", "")):
            self.status.setText(f"The Python driver for {DB.KIND_TITLES.get(conn['kind'])} is missing: "
                                f"pip install {DB.DRIVERS[conn['kind']]}")
            return False
        if self.db is not None:
            self.db.close()
            self.db = None
        try:
            db = self.panel.conns.open(self, conn, self.folder)
        except Exception as e:  # noqa: BLE001 - shown to the user
            self.status.setText(f"Cannot connect: {e}")
            return False
        if db is None:
            return False
        self.db, self.conn = db, conn
        self.objects.clear()
        self.q_table.clear()
        try:
            tables, views = db.tables(), db.views()
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Cannot read the tables: {e}")
            return False
        existing = {str(s.get("table")) for s in DB.sources(self.panel.view.doc.form)} if self.panel.view else set()
        for title, names, icon in (("Tables", tables, "SP_FileDialogDetailedView"),
                                   ("Views", views, "SP_FileDialogContentsView")):
            top = QTreeWidgetItem([f"{title} ({len(names)})"])
            top.setFlags(top.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.objects.addTopLevelItem(top)
            for n in names:
                it = QTreeWidgetItem([n + ("  (already a data source)" if n in existing else "")])
                it.setIcon(0, _std(self, icon))
                it.setData(0, ROLE, n)
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(0, Qt.CheckState.Unchecked)
                top.addChild(it)
            top.setExpanded(True)
        self.q_table.addItems([""] + tables)
        self.status.setText(f"Connected: {DB.KIND_TITLES.get(conn['kind'])} - {len(tables)} tables, "
                            f"{len(views)} views. Tick the ones the form needs.")
        return True

    def checked(self) -> list[str]:
        out = []
        for i in range(self.objects.topLevelItemCount()):
            top = self.objects.topLevelItem(i)
            for j in range(top.childCount()):
                it = top.child(j)
                if it.checkState(0) == Qt.CheckState.Checked:
                    out.append(str(it.data(0, ROLE)))
        return out

    def finish(self):
        if self.db is None and not self.connect_db():
            return
        form = self.panel.view.doc.form
        names = self.checked()
        sql = self.q_sql.toPlainText().strip()
        if not names and not sql:
            QMessageBox.information(self, "Add New Data Source", "Tick at least one table or view, or write a query.")
            return
        specs = []
        try:
            for n in names:
                cols, key = DB.table_columns(self.db, n)
                specs.append(dict(table=n, columns=cols, key=key, name=n))
            if sql:
                cols = DB.query_columns(self.db, sql)
                key = [k.strip() for k in self.q_key.text().replace(";", ",").split(",") if k.strip()]
                specs.append(dict(table=self.q_table.currentText().strip(), columns=cols, key=key, query=sql,
                                  name=self.q_name.text().strip() or "Query"))
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Add New Data Source", f"Cannot read the schema: {e}")
            return
        doc = self.panel.view.doc
        doc.checkpoint()
        for sp in specs:
            self.created.append(DB.make_source(form, self.conn, sp["table"], sp["columns"], sp["key"],
                                               sp.get("query", ""), sp["name"]))
        doc.set_modified()
        self.accept()

    def done(self, r):
        if self.db is not None:
            self.db.close()
            self.db = None
        super().done(r)


# ====================================================================== Configure / Preview
class ConfigureDialog(QDialog):
    """Edit a data source: filter / sort (SQL), query, table + key to save to, Fill on load."""

    def __init__(self, parent, src: dict):
        super().__init__(parent)
        self.src = src
        self.setWindowTitle(f"Configure {src['name']}")
        self.resize(520, 420)
        fl = QFormLayout(self)
        self.name = QLineEdit(src["name"])
        self.filter = QLineEdit(str(src.get("filter") or ""))
        self.filter.setPlaceholderText("City = 'Cairo'   (SQL WHERE, applied by Fill)")
        self.sort = QLineEdit(str(src.get("sort") or ""))
        self.sort.setPlaceholderText("Name ASC   (SQL ORDER BY)")
        self.query = QPlainTextEdit(str(src.get("query") or ""))
        self.query.setPlaceholderText("(empty = the whole table)")
        self.table = QLineEdit(str(src.get("table") or ""))
        self.key = QLineEdit(", ".join(src.get("key") or []))
        self.autofill = QCheckBox("Fill when the form opens (like VB's TableAdapter.Fill in Form_Load)")
        self.autofill.setChecked(bool(src.get("autofill", True)))
        fl.addRow("Name:", self.name)
        fl.addRow("Filter:", self.filter)
        fl.addRow("Sort:", self.sort)
        fl.addRow("Query:", self.query)
        fl.addRow("Table:", self.table)
        fl.addRow("Key column(s):", self.key)
        fl.addRow("", self.autofill)
        cols = QLabel("Columns: " + ", ".join(f"{c.get('name')} {c.get('type') or ''}".strip()
                                               for c in src.get("columns") or []))
        cols.setWordWrap(True)
        cols.setProperty("radRole", "muted")
        fl.addRow(cols)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        fl.addRow(bb)

    def values(self) -> dict:
        return {"name": self.name.text().strip(), "filter": self.filter.text().strip(),
                "sort": self.sort.text().strip(), "query": self.query.toPlainText().strip(),
                "table": self.table.text().strip(),
                "key": [k.strip() for k in self.key.text().replace(";", ",").split(",") if k.strip()],
                "autofill": self.autofill.isChecked()}


class PreviewDialog(QDialog):
    def __init__(self, parent, title: str, columns: list, rows: list):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 420)
        lay = QVBoxLayout(self)
        t = QTableWidget(len(rows), len(columns))
        t.setHorizontalHeaderLabels([str(c) for c in columns])
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                t.setItem(r, c, QTableWidgetItem(DB._txt(v)))
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        t.resizeColumnsToContents()
        lay.addWidget(t)
        info = QLabel(f"{len(rows)} row(s)" + (" (first rows only)" if len(rows) >= 500 else ""))
        info.setProperty("radRole", "muted")
        lay.addWidget(info)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


# ====================================================================== the window
class _NoForm:
    extra: dict = {}


def _refresh_preview(view) -> None:
    try:
        BlendPreview.of(view).refresh()
    except RuntimeError:            # the designer was closed meanwhile
        pass


class SourceTree(QTreeWidget):
    """Tables and columns that can be dragged onto the form designer."""

    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)

    def startDrag(self, _actions):
        it = self.currentItem()
        d = it.data(0, ROLE) if it is not None else None
        if not d or d[0] not in ("source", "column"):
            return
        mime = QMimeData()
        mime.setData(DB.MIME, json.dumps({"source": d[1], "column": d[2] if d[0] == "column" else ""}).encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(it.icon(0).pixmap(16, 16))
        drag.exec(Qt.DropAction.CopyAction)


class DataSourcesPanel(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.view = None
        self.conns = Connections(win)
        DB.PASSWORD_PROVIDER = lambda conn, folder: self.conns.known_password(conn, folder)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        tb = QToolBar()
        tb.setIconSize(tb.iconSize() * 0.8)
        self.a_add = tb.addAction(_std(self, "SP_FileDialogNewFolder"), "Add New Data Source...", self.add_source)
        self.a_config = tb.addAction(_std(self, "SP_FileDialogDetailedView"), "Configure Data Source...",
                                     self.configure)
        self.a_preview = tb.addAction(_std(self, "SP_FileDialogContentsView"), "Preview Data...", self.preview)
        self.a_refresh = tb.addAction(_std(self, "SP_BrowserReload"), "Refresh (re-read the columns and rows)",
                                      self.refresh_schema)
        self.a_remove = tb.addAction(_std(self, "SP_DialogDiscardButton"), "Remove Data Source", self.remove)
        lay.addWidget(tb)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.note.setProperty("radRole", "note")
        self.note.setContentsMargins(6, 4, 6, 4)
        lay.addWidget(self.note)
        self.tree = SourceTree(self)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.tree.itemDoubleClicked.connect(lambda it, _c: self.preview())
        self.tree.currentItemChanged.connect(lambda *_: self._enable())
        lay.addWidget(self.tree, 1)
        self.hint = QLabel("Drag a table onto the form for a DataGridView + navigator (right-click: Details for "
                           "labels and text boxes); drag a column for one field.")
        self.hint.setWordWrap(True)
        self.hint.setProperty("radRole", "muted")
        self.hint.setContentsMargins(6, 4, 6, 4)
        lay.addWidget(self.hint)
        self.bind(None)

    # ------------------------------------------------------------ follow the designer
    def bind(self, view) -> None:
        if view is not None and hasattr(view, "doc") and DB.sources(getattr(view.doc, "form", None) or _NoForm):
            # after the other preview layers (localization ...) have painted the designer
            QTimer.singleShot(0, lambda v=view: _refresh_preview(v))
        if view is self.view and view is not None:
            self.rebuild()
            return
        if self.view is not None:
            try:
                self.view.doc.structureChanged.disconnect(self.rebuild)
                self.view.doc.renamed.disconnect(self._renamed)
            except (TypeError, RuntimeError):
                pass
        self.view = view if view is not None and hasattr(view, "doc") and hasattr(view.doc, "form") else None
        if self.view is not None:
            self.view.doc.structureChanged.connect(self.rebuild)
            self.view.doc.renamed.connect(self._renamed)
            v = self.view
            if not getattr(v, "_db_rebuild_hooked", False):
                # the designer rebuilds its previews directly (zoom, theme, ...): show the rows again then
                v._db_rebuild_hooked = True
                orig = v.rebuild

                def rebuild(*a, _orig=orig, _v=v):
                    _orig(*a)
                    if DB.sources(_v.doc.form):
                        BlendPreview.of(_v).refresh()
                v.rebuild = rebuild
            if DB.sources(v.doc.form):                  # real rows in the designer as soon as it shows
                BlendPreview.of(v).refresh()
        self.rebuild()

    def _renamed(self, old: str, new: str) -> None:
        if self.view is not None:
            DB.rename_references(self.view.doc.form, old, new)

    @property
    def folder(self) -> Path:
        return Path(self.view.doc.path).parent

    def language(self) -> str:
        try:
            proj = getattr(self.win, "project", None)
            fn = getattr(proj, "form_language", None)
            if callable(fn):
                return fn(self.view.doc.form.name)
            return getattr(proj, "language", "") or ""
        except Exception:  # noqa: BLE001
            return ""

    def rebuild(self, *_a) -> None:
        cur = self.tree.currentItem()
        cur_key = cur.data(0, ROLE) if cur is not None else None
        self.tree.clear()
        if self.view is None:
            self.note.setText("Open a form designer to see its data sources.")
            self.note.show()
            self._enable()
            return
        lang = self.language()
        if lang and lang not in ("python-tk", "python-qt", "vb-basic"):
            self.note.setText(f"Data binding runs in Python (Tkinter / PySide6) and VB6 forms; {lang} forms ignore it.")
            self.note.show()
        else:
            self.note.hide()
        groups: dict[str, QTreeWidgetItem] = {}
        for src in DB.sources(self.view.doc.form):
            conn = src.get("connection") or {}
            gname = DB.ident(conn.get("name") or "Db") + "DataSet"
            g = groups.get(gname)
            if g is None:
                g = QTreeWidgetItem([gname])
                g.setIcon(0, _std(self, "SP_DriveHDIcon"))
                g.setToolTip(0, f"{DB.KIND_TITLES.get(conn.get('kind'), conn.get('kind'))}: "
                                f"{conn.get('path') or conn.get('database') or conn.get('odbc') or ''}")
                g.setData(0, ROLE, ("dataset", gname, ""))
                self.tree.addTopLevelItem(g)
                groups[gname] = g
            mode = "Details" if src.get("dropmode") == "details" else "DataGridView"
            ro = "  read-only" if DB.readonly(src) else ""
            it = QTreeWidgetItem([f"{src['name']}   [{mode}]{ro}"])
            it.setIcon(0, _std(self, "SP_FileDialogDetailedView"))
            it.setToolTip(0, (f"Query: {src.get('query')}" if src.get("query") else f"Table {src.get('table')}")
                          + f"\nDrag onto the form: {mode} (right-click to change)")
            it.setData(0, ROLE, ("source", src["name"], ""))
            g.addChild(it)
            for c in src.get("columns") or []:
                ci = QTreeWidgetItem([f"{c.get('name')}" + (f"   {c.get('type')}" if c.get("type") else "")
                                      + ("   (key)" if c.get("pk") else "")])
                ci.setIcon(0, _std(self, "SP_FileIcon"))
                ci.setData(0, ROLE, ("column", src["name"], str(c.get("name"))))
                it.addChild(ci)
            g.setExpanded(True)
            if cur_key and cur_key[1] == src["name"]:
                self.tree.setCurrentItem(it)
        if not self.tree.topLevelItemCount():
            self.note.setText("No data sources yet. Click Add New Data Source... to connect this form to a "
                              "database table.")
            self.note.show()
        self._enable()

    def _enable(self):
        on = self.view is not None
        src = self.current_source()
        self.a_add.setEnabled(on)
        for a in (self.a_config, self.a_preview, self.a_remove):
            a.setEnabled(on and src is not None)
        self.a_refresh.setEnabled(on)

    def current_source(self) -> dict | None:
        if self.view is None:
            return None
        it = self.tree.currentItem()
        d = it.data(0, ROLE) if it is not None else None
        if not d or d[0] not in ("source", "column"):
            return None
        return DB.find_source(self.view.doc.form, d[1])

    def _menu(self, pos):
        src = self.current_source()
        m = QMenu(self)
        if src is not None:
            g = m.addAction("Drop as DataGridView")
            g.setCheckable(True)
            g.setChecked(src.get("dropmode") != "details")
            g.triggered.connect(lambda: self.set_mode(src, "grid"))
            d = m.addAction("Drop as Details (labels and text boxes)")
            d.setCheckable(True)
            d.setChecked(src.get("dropmode") == "details")
            d.triggered.connect(lambda: self.set_mode(src, "details"))
            m.addAction("Add to Form", lambda: self.add_to_form(src))
            m.addSeparator()
            m.addAction("Preview Data...", self.preview)
            m.addAction("Configure Data Source...", self.configure)
            m.addAction("Remove", self.remove)
            m.addSeparator()
        m.addAction("Add New Data Source...", self.add_source).setEnabled(self.view is not None)
        m.exec(self.tree.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------ actions
    def _changed(self):
        doc = self.view.doc
        doc.set_modified()
        DB.clear_cache()
        self.rebuild()
        doc.structureChanged.emit()
        BlendPreview.of(self.view).refresh()

    def set_mode(self, src: dict, mode: str):
        src["dropmode"] = mode
        self.view.doc.set_modified()
        self.rebuild()

    def add_source(self):
        if self.view is None:
            return
        dlg = AddDataSourceDialog(self, self.folder)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.created:
            self._changed()
            self.win.log(f"Data sources added to {self.view.doc.form.name}: "
                         + ", ".join(s["name"] for s in dlg.created) + " - drag them onto the form.")

    def configure(self):
        src = self.current_source()
        if src is None:
            return
        dlg = ConfigureDialog(self, src)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        form = self.view.doc.form
        self.view.doc.checkpoint()
        new = v.pop("name")
        if new and new != src["name"]:
            if not new.isidentifier() or new.lower() in form.all_names() or DB.find_source(form, new):
                QMessageBox.warning(self, "Configure", f"'{new}' is not a valid unused name.")
                new = src["name"]
            else:
                old = src["name"]
                for c in form.controls:
                    for p in ("DataSource", "DataMember"):
                        val = str(c.props.get(p) or "")
                        if val == old:
                            c.props[p] = new
                        elif val.startswith(old + "."):
                            c.props[p] = new + val[len(old):]
                src["name"] = new
        query_changed = v["query"] != str(src.get("query") or "")
        src.update(v)
        if query_changed and v["query"]:
            try:
                db = self.conns.open(self, src["connection"], self.folder)
                if db is not None:
                    try:
                        src["columns"] = DB.query_columns(db, v["query"])
                    finally:
                        db.close()
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(self, "Configure", f"Cannot run the query: {e}")
        self._changed()

    def preview(self):
        src = self.current_source()
        if src is None:
            return
        pw = self.conns.password(self, src.get("connection") or {}, self.folder)
        if pw is None:
            return
        try:
            cols, rows = DB.fetch_rows(src, self.folder, pw, 500)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Preview Data", str(e))
            return
        PreviewDialog(self, f"Preview Data - {src['name']}", cols, rows).exec()

    def refresh_schema(self):
        """Read the columns of every table data source again and reload the designer's rows."""
        if self.view is None:
            return
        errors = []
        for src in DB.sources(self.view.doc.form):
            try:
                db = self.conns.open(self, src.get("connection") or {}, self.folder)
                if db is None:
                    continue
                try:
                    if src.get("query"):
                        src["columns"] = DB.query_columns(db, src["query"])
                    elif src.get("table"):
                        src["columns"], key = DB.table_columns(db, src["table"])
                        if key:
                            src["key"] = key
                finally:
                    db.close()
            except Exception as e:  # noqa: BLE001
                errors.append(f"{src.get('name')}: {e}")
        self._changed()
        if errors:
            QMessageBox.warning(self, "Refresh", "\n".join(errors))

    def remove(self):
        src = self.current_source()
        if src is None:
            return
        self.view.doc.checkpoint()
        DB.remove_source(self.view.doc.form, src["name"])
        self._changed()

    def add_to_form(self, src: dict, column: str = ""):
        """Like dragging the table onto the form's top-left free area."""
        if self.view is None:
            return []
        form = self.view.doc.form
        bottom = max([int(c.props.get("Top", 0)) + int(c.props.get("Height", 0))
                      for c in form.visual() if not c.parent] + [0])
        return drop_source(self.view, src, 12, bottom + 12 if bottom else 12, "", column)


# ====================================================================== drop on the designer
def drop_source(view, src: dict, x: int, y: int, parent: str = "", column: str = "") -> list:
    doc = view.doc
    doc.checkpoint()
    made = DB.layout_controls(doc.form, src, src.get("dropmode", "grid"), x, y, parent, column)
    for c in made:
        if c.parent == parent:
            try:
                doc._set_tab_page(c)
            except Exception:  # noqa: BLE001 - older document API
                pass
    try:
        doc._normalize()
        doc._relayout(emit=False)
    except Exception:  # noqa: BLE001
        pass
    doc.structureChanged.emit()
    doc.set_modified()
    tops = [c for c in made if c.parent == parent]
    if tops:
        doc.select_many(tops)
    BlendPreview.of(view).refresh()
    return made


def drop_on_designer(view, payload: str, pos) -> list:
    """Overlay.dropEvent: a table / column dragged from the Data Sources window."""
    try:
        d = json.loads(payload)
    except ValueError:
        return []
    src = DB.find_source(view.doc.form, str(d.get("source") or ""))
    if src is None:
        return []
    parent = view.overlay.container_at(pos, [])
    px, py = view.doc.form.client_origin(view.doc.form.find(parent) if parent else None)
    snap = lambda v: max(0, int(round(v / 8.0)) * 8)          # the designer's grid
    return drop_source(view, src, snap(pos.x() - px), snap(pos.y() - py), parent, str(d.get("column") or ""))


# ====================================================================== F5
def run_env(win, env: dict | None) -> dict | None:
    """F5 / Ctrl+F5: RADIDE_DB_<CONNECTION>_PASSWORD for the server connections of the project's forms whose
    password the IDE knows (typed this session, remembered by the Databases workspace, or a local server)."""
    project = getattr(win, "project", None)
    panel = getattr(win, "data_sources", None)
    if project is None or panel is None:
        return env
    import os
    folder = Path(project.folder)
    out = dict(env) if env is not None else dict(os.environ)
    for f in folder.glob("*.form"):
        try:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        for src in data.get("dbsources") or []:
            conn = (src.get("connection") or {}) if isinstance(src, dict) else {}
            if conn.get("kind") in (None, "sqlite"):
                continue
            key = "".join(ch if ch.isalnum() else "_" for ch in str(conn.get("name") or "")).upper()
            var = f"RADIDE_DB_{key}_PASSWORD"
            if var in out:
                continue
            pw = panel.conns.known_password(conn, folder)
            if pw is not None:
                out[var] = pw
    return out


# ====================================================================== install
def install(win) -> None:
    from .states import _add_dock
    panel = DataSourcesPanel(win)
    win.data_sources = panel
    dock = _add_dock(win, "Data Sources", panel, "dock_data_sources")
    tb_dock = getattr(win, "dock_toolbox", None)            # VB keeps it next to the Toolbox
    if tb_dock is not None:
        win.removeDockWidget(dock)
        win.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        win.tabifyDockWidget(tb_dock, dock)
        tb_dock.raise_()
    dock.hide()
    follow_designer(win, panel)

    def show():
        dock.show()
        dock.raise_()
        panel.bind(current_view(win))
    a_show = QAction("Show Data &Sources", win)
    a_show.setShortcut(QKeySequence("Shift+Alt+D"))
    a_show.triggered.connect(show)
    win.a_data_sources = a_show
    bar = win.menuBar()
    data_menu = next((a.menu() for a in bar.actions() if a.menu() is not None
                      and a.text().replace("&", "") == "Data"), None)
    if data_menu is None:
        data_menu = QMenu("D&ata", win)
        before = next((a for a in bar.actions() if a.text().replace("&", "") in ("Tools", "Window", "Help")), None)
        if before is not None:
            bar.insertMenu(before, data_menu)
        else:
            bar.addMenu(data_menu)
    data_menu.addAction(a_show)
    data_menu.addAction("Add &New Data Source...", lambda: (show(), panel.add_source()))
    data_menu.addAction("&Preview Data...", lambda: (show(), panel.preview()))
    data_menu.addAction("&Refresh Data Sources", lambda: (show(), panel.refresh_schema()))
