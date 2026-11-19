"""Expression Blend for the form designer (CONTRACTS 8.7) - sample data and data binding ("Data" panel).

Model, in the .form:
``"datasources": [{"name": "People", "file": "people.json", "root": ""}]`` (JSON: a list of records, or an
object holding one - "root" is an optional dotted path to it; CSV: a header row and records) and
``"bindings": [{"control": "ListBox1", "property": "Items", "source": "People", "field": "name"}]``.
Properties: Text (and Checked / Value) take the field of the current record; Items (ListBox, ComboBox)
the field of every record; Rows (DataGridView, ListView) the comma separated fields (empty = all).

Generated code (python-tk / python-qt): ``self.People = _DataSource(...)`` (Records, Count, Position,
Current, Fields, Load(), MoveFirst/Next/Previous/Last(), Value(field)), the bindings applied in __init__,
selecting an item of a bound list moves the source's Position (master / detail), and ``Refresh()``
reloads the files and applies the bindings again.

IDE: the "Data" dock lists data sources and bindings; the designer shows design-time sample values."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView,
                             QLabel, QListWidget, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
                             QToolButton, QVBoxLayout, QWidget)

from .states import COMMON_RT, RESERVED_NAMES, BlendPreview, _add_dock, follow_designer, is_python

BIND_PROPS = {"Items": ("ListBox", "ComboBox"), "Rows": ("DataGridView", "ListView"),
              "Value": ("NumericUpDown", "TrackBar", "ProgressBar"), "Checked": ("CheckBox", "RadioButton")}
NO_TEXT = ("ListBox", "PictureBox", "Panel", "TreeView", "ListView", "DataGridView", "TabControl", "ActiveX",
           "ProgressBar", "TrackBar")

DATA_RT = r'''

def _rad_records(data, root=""):
    """Records (dicts) of JSON data: a list, or the first list inside an object; root = dotted path."""
    for part in [p for p in str(root or "").split(".") if p]:
        if isinstance(data, dict):
            data = data.get(part)
        elif isinstance(data, list) and part.isdigit() and int(part) < len(data):
            data = data[int(part)]
        else:
            data = None
    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        data = lists[0] if lists else [data]
    if not isinstance(data, list):
        return []
    return [r if isinstance(r, dict) else {"value": r} for r in data]


def _rad_field(record, field):
    """record["a"]["b"] for field "a.b"; an empty field = the record's only (or "value") field."""
    if record is None:
        return None
    field = str(field or "").strip()
    if not field or field == "*":
        if isinstance(record, dict) and record:
            return record.get("value", next(iter(record.values())))
        return record
    cur = record
    for part in field.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return None
    return cur


def _rad_text(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, (dict, list)):
        return _json.dumps(v, ensure_ascii=False)
    return str(v)


def _rad_convert(prop, v):
    if prop == "Value":
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return 0
    if prop == "Checked":
        return v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "yes", "on")
    return _rad_text(v)


class _DataSource:
    """A data source (JSON or CSV file): Records, Count, Position, Current, Fields, Load(),
    MoveFirst() / MoveNext() / MovePrevious() / MoveLast(), Value(field[, record])."""

    def __init__(self, owner, name, path, fmt="", root="", on_move=None):
        self.Name, self.Path, self.Root = name, path, root
        self.Format = (fmt or ("csv" if str(path).lower().endswith(".csv") else "json")).lower()
        self.Records, self.Error = [], ""
        self._pos, self._on_move = 0, on_move
        self.Load()

    def Load(self):
        try:
            if self.Format == "csv":
                with open(self.Path, newline="", encoding="utf-8-sig") as f:
                    self.Records = [dict(r) for r in _csv.DictReader(f)]
            else:
                with open(self.Path, encoding="utf-8-sig") as f:
                    self.Records = _rad_records(_json.load(f), self.Root)
            self.Error = ""
        except (OSError, ValueError) as e:
            self.Records, self.Error = [], str(e)
        self._pos = max(0, min(self._pos, len(self.Records) - 1))
        return self

    @property
    def Count(self):
        return len(self.Records)

    @property
    def Fields(self):
        out = []
        for r in self.Records:
            out += [k for k in r if k not in out]
        return out

    @property
    def Position(self):
        return self._pos

    @Position.setter
    def Position(self, index):
        index = max(0, min(int(index), len(self.Records) - 1)) if self.Records else 0
        if index != self._pos:
            self._pos = index
            if self._on_move is not None:
                self._on_move()

    @property
    def Current(self):
        return self.Records[self._pos] if self.Records else None

    def Value(self, field, record=None):
        return _rad_field(self.Current if record is None else record, field)

    def MoveFirst(self):
        self.Position = 0

    def MoveLast(self):
        self.Position = len(self.Records) - 1

    def MoveNext(self):
        self.Position = self._pos + 1

    def MovePrevious(self):
        self.Position = self._pos - 1


class _Bindings:
    """Control.Property <- source.field bindings; Refresh() applies them."""

    def __init__(self, owner, io, items):
        self._o, self._io = owner, io
        self.Items = [tuple(b) for b in items]
        for ctrl, prop, src, _field in self.Items:
            if prop == "Items":
                io.on_select(ctrl, lambda i, s=src: self._select(s, i))

    def _select(self, src, index):
        ds = getattr(self._o, src, None)
        if ds is not None and ds.Position != index:
            ds.Position = index

    def Refresh(self, source=None, lists=True):
        for ctrl, prop, src, field in self.Items:
            if source and src != source:
                continue
            ds = getattr(self._o, src, None)
            if ds is None:
                continue
            if prop == "Items":
                if lists:
                    self._io.set_items(ctrl, [_rad_text(ds.Value(field, r)) for r in ds.Records])
            elif prop == "Rows":
                if lists:
                    cols = [f.strip() for f in str(field or "").split(",") if f.strip()] or ds.Fields
                    self._io.set_rows(ctrl, cols, [[_rad_text(ds.Value(c, r)) for c in cols] for r in ds.Records])
            else:
                self._io.set(ctrl, prop, _rad_convert(prop, ds.Value(field)))
'''

METHODS = [
    "",
    "    def Refresh(self, reload=True):",
    "        \"\"\"Reload the data sources (JSON / CSV files) and apply the data bindings again.\"\"\"",
    "        if reload:",
    "            for ds in self._datasources:",
    "                ds.Load()",
    "        self._bindings.Refresh()",
    "",
    "    RefreshBindings = Refresh",
]


# ====================================================================== model
def datasources(form) -> list[dict]:
    v = form.extra.get("datasources")
    if not isinstance(v, list):
        v = []
        form.extra["datasources"] = v
    return v


def bindings(form) -> list[dict]:
    v = form.extra.get("bindings")
    if not isinstance(v, list):
        v = []
        form.extra["bindings"] = v
    return v


def bindable_props(ctrl) -> list[str]:
    out = [p for p, types in BIND_PROPS.items() if ctrl.type in types]
    if "Text" in ctrl.props and ctrl.type not in NO_TEXT:
        out.insert(0, "Text")
    return out


def for_code(form) -> tuple[list[dict], list[tuple]]:
    """Valid data sources and bindings for code generation."""
    ctrls = {c.name: c for c in form.visual()}
    taken = {n.lower() for n in ctrls} | {form.name.lower()}
    sources, names = [], set()
    for ds in form.extra.get("datasources") or []:
        name, file = str(ds.get("name") or ""), str(ds.get("file") or "")
        if (not name.isidentifier() or name in names or name.lower() in taken or not file
                or name in RESERVED_NAMES):
            continue
        names.add(name)
        sources.append({"name": name, "file": file.replace("\\", "/"), "root": str(ds.get("root") or ""),
                        "format": str(ds.get("format") or "")})
    binds = []
    for b in form.extra.get("bindings") or []:
        c = ctrls.get(str(b.get("control") or ""))
        prop, src = str(b.get("property") or ""), str(b.get("source") or "")
        if c is None or src not in names or prop not in bindable_props(c):
            continue
        binds.append((c.name, prop, src, str(b.get("field") or "")))
    return sources, binds


def init_lines(sources: list[dict], binds: list[tuple], indent: str) -> list[str]:
    out = []
    for ds in sources:
        n = ds["name"]
        out.append(indent + f"self.{n} = _DataSource(self, {n!r}, self._res({ds['file']!r}), {ds['format']!r}, "
                            f"{ds['root']!r}, on_move=lambda: self._bindings.Refresh({n!r}, False))")
    out.append(indent + f"self._datasources = [{', '.join('self.' + ds['name'] for ds in sources)}]")
    out.append(indent + f"self._bindings = _Bindings(self, self._rad, {[list(b) for b in binds]!r})")
    out.append(indent + "self._bindings.Refresh()")
    return out


# ------------------------------------------------------------------ design time
def _design_ns() -> dict:
    ns: dict = {}
    exec(compile(COMMON_RT + DATA_RT, "<blend-data-runtime>", "exec"), ns)    # noqa: S102 - our constant
    return ns


DATA = _design_ns()
_CACHE: dict = {}


def load_source(folder: Path, ds: dict):
    """The design-time _DataSource of *ds* (cached by file time), or None."""
    path = Path(folder) / str(ds.get("file") or "")
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    key = (str(path), mtime, str(ds.get("root") or ""), str(ds.get("format") or ""))
    src = _CACHE.get(key)
    if src is None:
        src = DATA["_DataSource"](None, str(ds.get("name")), str(path), str(ds.get("format") or ""),
                                  str(ds.get("root") or ""))
        if len(_CACHE) > 64:
            _CACHE.clear()
        _CACHE[key] = src
    return src


def sample_props(doc, ctrl) -> dict:
    """Design-time sample values of the bound properties of *ctrl* (from the first record)."""
    form = doc.form
    binds = [b for b in form.extra.get("bindings") or [] if b.get("control") == ctrl.name]
    if not binds:
        return {}
    srcs = {str(d.get("name")): d for d in form.extra.get("datasources") or []}
    out = {}
    for b in binds:
        ds = srcs.get(str(b.get("source")))
        src = load_source(doc.path.parent, ds) if ds else None
        if src is None or not src.Records:
            continue
        prop, field = b.get("property"), b.get("field") or ""
        text = DATA["_rad_text"]
        if prop == "Items":
            out["Items"] = ";".join(text(src.Value(field, r)).replace(";", ",") for r in src.Records)
        elif prop == "Rows":
            cols = [f.strip() for f in str(field).split(",") if f.strip()] or src.Fields
            rows = ";".join("|".join(text(src.Value(c, r)).replace(";", ",").replace("|", "/") for c in cols)
                            for r in src.Records)
            out["Columns"] = ";".join(cols)
            out["Items" if ctrl.type == "ListView" else "Rows"] = rows
        elif prop in ("Text", "Value", "Checked"):
            out[prop] = DATA["_rad_convert"](prop, src.Value(field, src.Records[0]))
    return out


SAMPLE = [
    {"Name": "Amira Hassan", "Email": "amira@example.com", "Age": 29, "City": "Cairo", "Active": True},
    {"Name": "Omar Khaled", "Email": "omar@example.com", "Age": 34, "City": "Alexandria", "Active": True},
    {"Name": "Lina Farouk", "Email": "lina@example.com", "Age": 22, "City": "Giza", "Active": False},
    {"Name": "Youssef Adel", "Email": "youssef@example.com", "Age": 41, "City": "Luxor", "Active": True},
    {"Name": "Nour Samir", "Email": "nour@example.com", "Age": 27, "City": "Aswan", "Active": True},
    {"Name": "Karim Mostafa", "Email": "karim@example.com", "Age": 38, "City": "Mansoura", "Active": False},
    {"Name": "Sara Ibrahim", "Email": "sara@example.com", "Age": 31, "City": "Tanta", "Active": True},
    {"Name": "Hany Fathy", "Email": "hany@example.com", "Age": 45, "City": "Suez", "Active": True},
]


def new_sample_data(form, folder: Path) -> dict:
    """Blend's "New Sample Data": SampleDataN.json in the project + a data source for it."""
    taken = {str(d.get("name")).lower() for d in datasources(form)} | set(form.all_names())
    i = 1
    while f"sampledata{i}" in taken or (Path(folder) / f"SampleData{i}.json").exists():
        i += 1
    name = f"SampleData{i}"
    (Path(folder) / f"{name}.json").write_text(json.dumps(SAMPLE, indent=2, ensure_ascii=False), encoding="utf-8")
    ds = {"name": name, "file": f"{name}.json"}
    datasources(form).append(ds)
    return ds


def add_file_source(form, folder: Path, file: Path) -> dict:
    """A data source for *file* (copied into the project when it lives elsewhere)."""
    folder, file = Path(folder).resolve(), Path(file).resolve()
    try:
        rel = file.relative_to(folder)
    except ValueError:
        target = folder / "data" / file.name
        target.parent.mkdir(exist_ok=True)
        if not target.exists():
            shutil.copy2(file, target)
        rel = target.relative_to(folder)
    base = "".join(ch if ch.isalnum() else "_" for ch in file.stem) or "Data"
    if not base[0].isalpha():
        base = "Data" + base
    base = base[0].upper() + base[1:]
    taken = {str(d.get("name")) for d in datasources(form)} | {n.lower() for n in form.all_names()}
    name, i = base, 1
    while name in taken or name.lower() in taken:
        i += 1
        name = f"{base}{i}"
    ds = {"name": name, "file": rel.as_posix()}
    datasources(form).append(ds)
    return ds


# ====================================================================== Data panel
class DataPanel(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.view = None
        self._filling = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.note.setStyleSheet("color:#806000;")
        lay.addWidget(self.note)
        lay.addWidget(QLabel("<b>Data sources</b>"))
        self.sources = QListWidget()
        self.sources.setMaximumHeight(90)
        self.sources.currentRowChanged.connect(self._on_source)
        lay.addWidget(self.sources)
        row = QHBoxLayout()
        self.btn_sample = QToolButton(text="New Sample Data")
        self.btn_sample.clicked.connect(self.new_sample)
        self.btn_file = QToolButton(text="Add JSON / CSV...")
        self.btn_file.clicked.connect(self.add_file)
        self.btn_rm_src = QToolButton(text="Remove")
        self.btn_rm_src.clicked.connect(self.remove_source)
        self.btn_reload = QToolButton(text="Reload")
        self.btn_reload.clicked.connect(self.reload)
        for b in (self.btn_sample, self.btn_file, self.btn_rm_src, self.btn_reload):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.records = QTableWidget(0, 0)
        self.records.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.records.setMaximumHeight(140)
        lay.addWidget(self.records)
        lay.addWidget(QLabel("<b>Bindings</b>"))
        self.binds = QTableWidget(0, 4)
        self.binds.setHorizontalHeaderLabels(["Control", "Property", "Source", "Field"])
        self.binds.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.binds.verticalHeader().hide()
        self.binds.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.binds.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        lay.addWidget(self.binds, 1)
        row = QHBoxLayout()
        self.ctrl_label = QLabel("")
        self.prop = QComboBox()
        self.src = QComboBox()
        self.src.currentIndexChanged.connect(self._fill_fields)
        self.field = QComboBox()
        self.field.setEditable(True)
        self.btn_bind = QPushButton("Bind")
        self.btn_bind.setToolTip("Bind the selected control's property to the field of the data source")
        self.btn_bind.clicked.connect(self.add_binding)
        self.btn_unbind = QToolButton(text="Remove")
        self.btn_unbind.clicked.connect(self.remove_binding)
        row.addWidget(self.ctrl_label)
        row.addWidget(self.prop)
        row.addWidget(QLabel("<-"))
        row.addWidget(self.src)
        row.addWidget(self.field, 1)
        row.addWidget(self.btn_bind)
        row.addWidget(self.btn_unbind)
        lay.addLayout(row)
        self.chk_samples = QCheckBox("Show sample data in the designer")
        self.chk_samples.setChecked(True)
        self.chk_samples.toggled.connect(self._on_samples)
        lay.addWidget(self.chk_samples)
        self.bind(None)

    def bind(self, view) -> None:
        if view is self.view and view is not None:
            return
        if self.view is not None:
            try:
                self.view.doc.selectionChanged.disconnect(self._on_selection)
                self.view.doc.structureChanged.disconnect(self.rebuild)
            except (TypeError, RuntimeError):
                pass
        self.view = view
        if view is not None:
            view.doc.selectionChanged.connect(self._on_selection)
            view.doc.structureChanged.connect(self.rebuild)
            self.chk_samples.setChecked(BlendPreview.of(view).samples)
        self.rebuild()

    @property
    def folder(self) -> Path:
        return self.view.doc.path.parent

    def rebuild(self, *_a) -> None:
        on = self.view is not None
        for w in self.findChildren(QWidget):
            if w is not self.note:
                w.setEnabled(on)
        if not on:
            self.note.setText("Open a form designer to bind it to data.")
            self.sources.clear()
            self.binds.setRowCount(0)
            self.records.setRowCount(0)
            return
        self.note.setText("" if is_python(self.win, self.view) else
                          "Data bindings run in Python (Tkinter / PySide6) forms; this language ignores them.")
        self._filling = True
        row = self.sources.currentRow()
        self.sources.clear()
        form = self.view.doc.form
        for ds in datasources(form):
            src = load_source(self.folder, ds)
            info = (f"{src.Count} records" if src is not None and not src.Error
                    else (src.Error if src is not None else "file not found"))
            self.sources.addItem(f"{ds.get('name')}  -  {ds.get('file')}  ({info})")
        if self.sources.count():
            self.sources.setCurrentRow(min(max(row, 0), self.sources.count() - 1))
        cur = self.src.currentText()
        self.src.clear()
        self.src.addItems([str(d.get("name")) for d in datasources(form)])
        if cur:
            self.src.setCurrentText(cur)
        self.binds.setRowCount(0)
        for b in bindings(form):
            r = self.binds.rowCount()
            self.binds.insertRow(r)
            for c, k in enumerate(("control", "property", "source", "field")):
                self.binds.setItem(r, c, QTableWidgetItem(str(b.get(k, ""))))
        self._filling = False
        self._on_source()
        self._on_selection()

    def _source(self) -> dict | None:
        r = self.sources.currentRow()
        lst = datasources(self.view.doc.form) if self.view is not None else []
        return lst[r] if 0 <= r < len(lst) else None

    def _on_source(self, *_a) -> None:
        if self._filling or self.view is None:
            return
        ds = self._source()
        src = load_source(self.folder, ds) if ds else None
        if src is None:
            self.records.setRowCount(0)
            self.records.setColumnCount(0)
            return
        fields = src.Fields
        recs = src.Records[:100]
        self.records.setColumnCount(len(fields))
        self.records.setHorizontalHeaderLabels(fields)
        self.records.setRowCount(len(recs))
        for r, rec in enumerate(recs):
            for c, f in enumerate(fields):
                self.records.setItem(r, c, QTableWidgetItem(DATA["_rad_text"](rec.get(f))))

    def _fill_fields(self, *_a) -> None:
        if self.view is None:
            return
        name = self.src.currentText()
        ds = next((d for d in datasources(self.view.doc.form) if str(d.get("name")) == name), None)
        src = load_source(self.folder, ds) if ds else None
        cur = self.field.currentText()
        self.field.clear()
        self.field.addItems(src.Fields if src is not None else [])
        if cur:
            self.field.setCurrentText(cur)

    def _on_selection(self, *_a) -> None:
        if self.view is None:
            return
        ctrl = self.view.doc.selected
        self.prop.clear()
        if ctrl is None or ctrl.ctype.nonvisual:
            self.ctrl_label.setText("(select a control)")
            self.btn_bind.setEnabled(False)
            return
        self.ctrl_label.setText(f"{ctrl.name}.")
        self.prop.addItems(bindable_props(ctrl))
        self.btn_bind.setEnabled(bool(self.prop.count()) and bool(self.src.count()))
        self._fill_fields()

    def _on_samples(self, on: bool) -> None:
        if self.view is not None:
            bp = BlendPreview.of(self.view)
            bp.samples = bool(on)
            bp.refresh()

    # ------------------------------------------------------------ edits
    def _edit(self, fn):
        doc = self.view.doc
        doc.checkpoint()
        res = fn()
        doc.set_modified()
        self.rebuild()
        BlendPreview.of(self.view).refresh()
        return res

    def new_sample(self) -> None:
        if self.view is not None:
            ds = self._edit(lambda: new_sample_data(self.view.doc.form, self.folder))
            self.win.log(f"Sample data source '{ds['name']}' created: {self.folder / ds['file']}")

    def add_file(self) -> None:
        if self.view is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Add Data Source", str(self.folder),
                                              "Data files (*.json *.csv);;All files (*.*)")
        if path:
            self._edit(lambda: add_file_source(self.view.doc.form, self.folder, Path(path)))

    def remove_source(self) -> None:
        ds = self._source()
        if ds is None:
            return
        form = self.view.doc.form

        def do():
            datasources(form).remove(ds)
            form.extra["bindings"] = [b for b in bindings(form) if b.get("source") != ds.get("name")]
        self._edit(do)

    def reload(self) -> None:
        _CACHE.clear()
        if self.view is not None:
            self.rebuild()
            BlendPreview.of(self.view).refresh()

    def add_binding(self) -> None:
        if self.view is None:
            return
        ctrl = self.view.doc.selected
        prop, src, field = self.prop.currentText(), self.src.currentText(), self.field.currentText().strip()
        if ctrl is None or not prop or not src:
            return
        if prop != "Rows" and not field:
            QMessageBox.information(self, "Bind", "Choose the field of the data source.")
            return
        form = self.view.doc.form

        def do():
            lst = [b for b in bindings(form) if not (b.get("control") == ctrl.name and b.get("property") == prop)]
            lst.append({"control": ctrl.name, "property": prop, "source": src, "field": field})
            form.extra["bindings"] = lst
        self._edit(do)

    def remove_binding(self) -> None:
        r = self.binds.currentRow()
        if self.view is None or r < 0:
            return
        form = self.view.doc.form
        self._edit(lambda: bindings(form).pop(r) if r < len(bindings(form)) else None)


def install(win) -> None:
    panel = DataPanel(win)
    win.data_panel = panel
    _add_dock(win, "Data", panel, "dock_data")
    follow_designer(win, panel)
