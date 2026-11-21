"""VB6 data controls, bound controls, bound grids, DataEnvironment and DataReport for radide/runtimes/vbrun.py.

* ``DataControl`` - the intrinsic **Data** control (DAO: DatabaseName + RecordSource) and the **ADO Data
  Control** (Adodc: ConnectionString + RecordSource), drawn as a caption bar with |< < > >| buttons.  It opens
  its recordset after Form_Load (VB6 order) or on ``Refresh``; controls with ``DataSource = "Data1"`` and a
  ``DataField`` show the current record and are written back on ``Update`` / ``UpdateRecord`` / navigation.
* Grids (DataGrid / DBGrid / MSFlexGrid / MSHFlexGrid shown as DataGridView) bound to a data control in the
  designer (DBGrid keeps that link in the .frx "Bindings" blob) or with ``Set Grid.DataSource = rs`` in code are
  filled with the recordset.
* ``DataEnvironment`` (.Dsr): connections (``DataEnvironment1.Connection1``), commands
  (``DataEnvironment1.Command1 [params]``) and their recordsets (``DataEnvironment1.rsCommand1``).
* ``DataReport`` (.Dsr): ``DataReport1.Show`` opens a window with the rows of its DataMember command.
Databases go through radide/runtimes/vbado.py.
"""
from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from . import vbado
from .vbinterp import EMPTY, NOTHING, err, to_bool, to_str

DATA_CLASSES = ("vb.data", "msadodclib.adodc")
GRID_TYPES = ("DataGridView",)


def _text_prop(vc) -> str:
    return {"Label": "caption", "CheckBox": "value", "RadioButton": "value", "Button": "caption"}.get(vc.type,
                                                                                                   "text")


def fill_grid(vc, rs) -> None:
    """Show all rows of *rs* in a DataGridView control (keeps the current position)."""
    w = vc.w
    try:
        if rs is None or not rs.State:
            w.Clear()
            return
        cols = list(rs._cols) or ["Column1"]
        w.SetColumns(cols)
        w.Clear()
        for row in rs._rows:
            w.AddRow(*["" if v is None else to_str(v) for v in row])
    except tk.TclError:
        pass


class _GridLink:
    """Keeps a grid filled while its recordset changes (requery, add, delete)."""

    def __init__(self, vc, rs):
        self.vc, self.rs = vc, rs
        self.sig = None
        rs._bindings.append(self)
        self(rs)

    def __call__(self, rs):
        if getattr(self.vc, "_grid_link", None) is not self:
            return
        sig = (id(rs._rows), len(rs._rows), tuple(rs._cols), rs.State)
        if sig != self.sig:
            self.sig = sig
            fill_grid(self.vc, rs)


def set_datasource(vc, value) -> None:
    """``Set Grid.DataSource = rs`` / ``= Adodc1`` / ``= DataEnvironment1``."""
    if isinstance(value, DataControl):
        value.add_grid(vc)
        return
    if isinstance(value, DataEnvironment):
        member = getattr(vc, "_datamember", "") or ""
        rs = value.recordset_for(member) if member else None
        if rs is not None:
            vc._grid_link = _GridLink(vc, rs)
        return
    if isinstance(value, vbado.Recordset):
        vc._grid_link = _GridLink(vc, value)
        return
    if value is NOTHING or value is EMPTY or value is None:
        vc._grid_link = None
        fill_grid(vc, None)
        return
    raise err(13, "Type mismatch (DataSource needs a Recordset or a data control)")


# ============================================================================ Data / Adodc
class DataControl:
    vb_typename = "Data"
    vb_default = "caption"

    def __init__(self, vf, vc, block, kind: str):
        self.vf, self.vc, self.kind = vf, vc, kind               # kind: "dao" | "ado"
        self.name = vc.name
        self.vb_name = vc.name
        self.vb_typename = "Adodc" if kind == "ado" else "Data"
        g = (lambda k, d="": block.get(k, d)) if block is not None else (lambda k, d="": d)
        self.props = {
            "databasename": to_str(g("DatabaseName", "")), "recordsource": to_str(g("RecordSource", "")),
            "connect": to_str(g("Connect", "Access")), "readonly": bool(g("ReadOnly", 0)),
            "exclusive": bool(g("Exclusive", 0)), "connectionstring": to_str(g("ConnectString", "")),
            "commandtype": g("CommandType", 8), "username": to_str(g("UserName", "")),
            "password": to_str(g("Password", "")), "eofaction": g("EOFAction", 0), "bofaction": g("BOFAction", 0),
            "recordsettype": g("RecordsetType", 1), "defaultcursortype": 0, "options": 0,
        }
        cap = g("Caption", vc.name)
        self.caption = to_str(cap) if isinstance(cap, str) else vc.name
        self.rs = None
        self.db = None
        self.conn = None
        self.bound: list = []                 # (VBControl, field name)
        self.grids: list = []
        self._build_bar()

    # -- the navigation bar
    def _build_bar(self):
        try:
            w = self.vc.w
            w.configure(text=self.caption, anchor="center", relief="ridge", bd=1)
            for txt, side, rx, act in (("|<", "w", 0.0, self.move_first), ("<", "w", None, self.move_prev),
                                       (">", "e", None, self.move_next), (">|", "e", 1.0, self.move_last)):
                b = tk.Button(w, text=txt, command=act, padx=0, pady=0, bd=1, font=("Segoe UI", 7))
                if txt == "|<":
                    b.place(relx=0, rely=0, relheight=1, width=20)
                elif txt == "<":
                    b.place(x=20, rely=0, relheight=1, width=20)
                elif txt == ">":
                    b.place(relx=1, x=-40, rely=0, relheight=1, width=20)
                else:
                    b.place(relx=1, x=-20, rely=0, relheight=1, width=20)
        except (tk.TclError, AttributeError):
            pass

    def _nav(self, fn):
        if self.rs is None or not self.rs.State:
            return
        try:
            self._save_bound()
            fn()
        except Exception as ex:  # noqa: BLE001
            self.vf.runtime.runtime_error(ex) if hasattr(ex, "number") else None

    def move_first(self):
        self._nav(self.rs.MoveFirst if self.rs else None)

    def move_last(self):
        self._nav(self.rs.MoveLast if self.rs else None)

    def move_next(self):
        def go():
            if not self.rs.EOF:
                self.rs.MoveNext()
            if self.rs.EOF and self.rs.RecordCount:
                self.rs.MoveLast()
        self._nav(go)

    def move_prev(self):
        def go():
            if not self.rs.BOF:
                self.rs.MovePrevious()
            if self.rs.BOF and self.rs.RecordCount:
                self.rs.MoveFirst()
        self._nav(go)

    # -- binding
    def add_bound(self, vc, field: str):
        self.bound.append((vc, field))

    def add_grid(self, vc):
        if vc not in self.grids:
            self.grids.append(vc)
        if self.rs is not None:
            vc._grid_link = _GridLink(vc, self.rs)

    def _show_current(self, rs):
        if rs is not self.rs:
            return
        for vc, field in self.bound:
            try:
                if not rs.State or (rs.EOF or rs.BOF) and rs._mode != 2:
                    v = ""
                else:
                    v = rs._field(field).Value
                    v = "" if v is None else v
                if vc.type == "CheckBox":
                    v = 1 if to_bool(v or 0) else 0
                vc.vb_set(_text_prop(vc), v)
            except Exception:  # noqa: BLE001
                pass

    def _pull(self, rs):
        """Bound control values -> the record being edited / added (before Update)."""
        if rs is not self.rs or not rs._mode:
            return
        for vc, field in self.bound:
            try:
                i = rs._index(field)
                val = vc.vb_get(_text_prop(vc))
                cur = rs._edit.get(i) if i in rs._edit else (None if rs._mode == 2 else rs._current_row()[i])
                if rs._mode == 2 or to_str(val) != to_str(cur if cur is not None else ""):
                    if rs._mode == 2 and to_str(val) == "" and i not in rs._edit:
                        continue
                    rs._edit[i] = val
            except Exception:  # noqa: BLE001
                pass

    def _save_bound(self):
        rs = self.rs
        if rs is None or not rs.State or self.props["readonly"] or not rs._table:
            return
        if rs._mode == 0 and not (rs.EOF or rs.BOF):
            changed = False
            for vc, field in self.bound:
                try:
                    v = rs._field(field).Value
                    if to_str(vc.vb_get(_text_prop(vc))) != to_str(v if v is not None else ""):
                        changed = True
                        break
                except Exception:  # noqa: BLE001
                    pass
            if not changed:
                return
            rs._mode, rs._edit = 1, {}
        if rs._mode:
            rs.Update()

    # -- opening
    def refresh(self):
        old = self.rs
        if old is not None:
            old._bindings = [b for b in old._bindings if b is not self._show_current]
        src = self.props["recordsource"]
        if self.kind == "dao":
            path = self.props["databasename"]
            if not path:
                raise err(3024, f"Couldn't find file '' ({self.name}.DatabaseName is empty)")
            if self.db is None or getattr(self.db, "_path", None) != path:
                if self.db is not None:
                    self.db.Close()
                self.db = vbado.Database(path, self.vf.runtime.folder, self.props["connect"],
                                         self.props["readonly"])
                self.db._path = path
            if not src:
                self.rs = None
                return
            self.rs = self.db.OpenRecordset(src)
        else:
            cs = self.props["connectionstring"]
            if self.conn is None or self.conn.ConnectionString != cs or not self.conn.State:
                self.conn = vbado.Connection(cs)
                self.conn._base = self.vf.runtime.folder
                self.conn.Open(None, self.props["username"] or None, self.props["password"] or None)
            if not src:
                self.rs = None
                return
            rs = vbado.Recordset()
            ct = int(self.props["commandtype"] or 8)
            rs.Open(src, self.conn, 1, 1 if self.props["readonly"] else 3, 2 if ct == 2 else None)
            self.rs = rs
        self._wire()

    def _wire(self):
        rs = self.rs
        rs._bindings.append(self._show_current)
        rs._pre_update.append(self._pull)
        for g in self.grids:
            g._grid_link = _GridLink(g, rs)
        self._show_current(rs)

    def auto_open(self):
        """After Form_Load: open when the program did not (VB6 opens data controls after the Load event)."""
        if self.rs is not None:
            return
        if not self.props["recordsource"] or (self.kind == "dao" and not self.props["databasename"]) or (
                self.kind == "ado" and not self.props["connectionstring"]):
            return
        try:
            self.refresh()
        except Exception as ex:  # noqa: BLE001
            if hasattr(ex, "number"):
                self.vf.runtime.runtime_error(ex)
            else:
                raise

    # -- protocol
    def vb_get(self, name):
        if name == "recordset":
            if self.rs is None and self.props["recordsource"]:
                self.refresh()
            return self.rs if self.rs is not None else NOTHING
        if name == "database":
            return self.db if self.db is not None else NOTHING
        if name == "caption":
            return self.caption
        if name in ("name",):
            return self.name
        if name in self.props:
            return self.props[name]
        if name in ("refresh", "updaterecord", "updatecontrols"):
            return self.vb_call(name, [])
        return self.vc.vb_get(name)

    def vb_set(self, name, value):
        if name == "recordset":
            self.rs = value if isinstance(value, vbado.Recordset) else None
            if self.rs is not None:
                self._wire()
            return
        if name == "caption":
            self.caption = to_str(value)
            try:
                self.vc.w.configure(text=self.caption)
            except tk.TclError:
                pass
            return
        if name in self.props:
            self.props[name] = value if name in ("commandtype", "eofaction", "bofaction") else (
                to_bool(value) if name in ("readonly", "exclusive") else to_str(value))
            return
        self.vc.vb_set(name, value)

    def vb_call(self, name, args):
        if name == "refresh":
            self.refresh()
            return EMPTY
        if name == "updaterecord":
            self._save_bound()
            return EMPTY
        if name == "updatecontrols":
            if self.rs is not None:
                self._show_current(self.rs)
            return EMPTY
        if name in ("recordset", "database", "caption", "name") or name in self.props:
            return self.vb_get(name)
        return self.vc.vb_call(name, args)


# ============================================================================ install on a form
def _frx_binding(block, frm_path: Path, names: set) -> str:
    """DBGrid / DataGrid designer binding stored in the .frx ("Bindings" = name of the data control)."""
    v = block.get("Bindings")
    if not isinstance(v, tuple):
        return ""
    try:
        data = (frm_path.parent / v[1]).read_bytes() if v[1] else b""
        off = int(v[2])
    except (OSError, ValueError, TypeError, IndexError):
        return ""
    chunk = data[off:off + 120]
    for m in re.finditer(rb"[\x01-\x40]([A-Za-z_][A-Za-z0-9_]{0,63})", chunk):
        s = m.group(1).decode("ascii", "replace")
        if s.lower() in names and len(s) == m.group(0)[0]:
            return s
    return ""


def install(vf) -> list:
    """Data controls and bindings of a native VB6 form (after its controls exist, before Form_Load).
    Returns the data controls (opened by ``after_load``)."""
    rt = vf.runtime
    if rt.native is None:
        return []
    nf = rt.native.forms.get(vf.name.lower())
    if nf is None:
        return []
    from ..foreign.frm_writer import parse_frm
    doc = parse_frm(nf.text)
    if doc.root is None:
        return []
    blocks = list(doc.controls())
    datas = {}
    for b in blocks:
        cls = b.cls.lower()
        if cls in DATA_CLASSES:
            vc = vf.controls.get(b.neutral_name.lower())
            if vc is None:
                continue
            dc = DataControl(vf, vc, b, "dao" if cls == "vb.data" else "ado")
            vf.controls[b.neutral_name.lower()] = dc
            datas[b.name.lower()] = dc
            if b.index is not None and b.name.lower() in vf.controls:
                arr = vf.controls[b.name.lower()]
                if hasattr(arr, "items"):
                    arr.items[b.index] = dc
    names = set(datas)
    for b in blocks:
        src = b.get("DataSource")
        vc = vf.controls.get(b.neutral_name.lower())
        if vc is None or isinstance(vc, DataControl):
            continue
        if getattr(vc, "type", "") in GRID_TYPES:
            if isinstance(src, str) and src.lower() in datas:
                datas[src.lower()].add_grid(vc)
            elif names:
                link = _frx_binding(b, nf.path, names)
                if link:
                    datas[link.lower()].add_grid(vc)
            dm = b.get("DataMember")
            if isinstance(dm, str):
                vc._datamember = dm
            continue
        field = b.get("DataField")
        if isinstance(src, str) and src.lower() in datas and isinstance(field, str) and field:
            datas[src.lower()].add_bound(vc, field)
    return list(datas.values())


def after_load(datas: list) -> None:
    for dc in datas:
        dc.auto_open()


# ============================================================================ DataEnvironment / DataReport
def _dsr_blocks(text: str):
    """(header props, [(block name, props)]) of a .Dsr designer file (props: lower-case key -> raw value)."""
    from ..foreign.frm_writer import parse_frm
    doc = parse_frm(text)
    if doc.root is None:
        return {}, []
    head = {p.key.lower(): p.value for p in doc.root.props}
    out = []
    for pb in doc.root.pblocks:
        out.append((pb.name, {p.key.lower(): p.value for p in pb.props}))
    return head, out


class _DECommand:
    def __init__(self, name, text, ctype, conn):
        self.name, self.text, self.ctype, self.conn = name, text, ctype, conn


class DataEnvironment:
    vb_typename = "DataEnvironment"

    def __init__(self, runtime, name: str, text: str):
        self.runtime, self.name, self.vb_name = runtime, name, name
        head, blocks = _dsr_blocks(text)
        self.connections: dict[str, vbado.Connection] = {}
        self.conn_src: dict[str, str] = {}
        self.commands: dict[str, _DECommand] = {}
        self.recordsets: dict[str, vbado.Recordset] = {}
        for bname, p in blocks:
            if bname.lower().startswith("connection") and "connectionname" in p:
                self.conn_src[str(p["connectionname"]).lower()] = (str(p["connectionname"]),
                                                                   to_str(p.get("connectionsource", "")))
            elif bname.lower().startswith("recordset") and "commandname" in p:
                self.commands[str(p["commandname"]).lower()] = _DECommand(
                    str(p["commandname"]), to_str(p.get("commandtext", "")), int(p.get("commandtype", 1) or 1),
                    str(p.get("activeconnectionname", "") or ""))

    def connection(self, key: str) -> vbado.Connection:
        key = key.lower()
        c = self.connections.get(key)
        if c is None:
            disp, src = self.conn_src[key]
            c = vbado.Connection(src)
            c._base = self.runtime.folder
            self.connections[key] = c
        if not c.State:
            c.Open()
        return c

    def run_command(self, key: str, args=()):
        cmd = self.commands[key.lower()]
        conn = self.connection(cmd.conn or next(iter(self.conn_src), ""))
        rs = self.recordsets.get(cmd.name.lower())
        if rs is not None and rs.State:
            rs.Close()
        rs = rs or vbado.Recordset()
        sql = cmd.text
        if cmd.ctype == 2 or (cmd.ctype != 1 and re.fullmatch(r"[\w.\[\] ]+", sql or "") and not
                              re.match(r"\s*select\b", sql, re.I)):
            sql = f"SELECT * FROM [{sql.split('.')[-1].strip('[]')}]"
        if args:
            c = vbado.Command()
            c._conn = conn
            c.CommandText = sql
            sql = c._sql([a for a in args])
        rs.Open(sql, conn, 1, 3)
        self.recordsets[cmd.name.lower()] = rs
        return rs

    def recordset_for(self, member: str):
        key = member.lower()
        if key in self.recordsets and self.recordsets[key].State:
            return self.recordsets[key]
        if key in self.commands:
            return self.run_command(key)
        return None

    def vb_get(self, name):
        if name in self.conn_src:
            return self.connection(name)
        if name.startswith("rs") and name[2:] in self.commands:
            rs = self.recordsets.get(name[2:])
            if rs is None:
                rs = vbado.Recordset()
                self.recordsets[name[2:]] = rs
                conn = self.commands[name[2:]].conn or next(iter(self.conn_src), "")
                rs._conn = self.connection(conn) if conn else None
                rs.Source = self.commands[name[2:]].text
            return rs
        if name in self.commands:
            self.run_command(name)
            return EMPTY
        if name == "name":
            return self.name
        if name == "connections":
            return [self.connection(k) for k in self.conn_src]
        raise err(438, f"DataEnvironment doesn't support '{name}'")

    def vb_set(self, name, value):
        raise err(438, f"DataEnvironment property '{name}' is read-only")

    def vb_call(self, name, args):
        if name in self.commands:
            self.run_command(name, args)
            return EMPTY
        v = self.vb_get(name)
        if args and getattr(v, "vb_default", None):          # DataEnvironment1.rsCommand1!Name
            return v.vb_call(v.vb_default, args)
        return v


class DataReport:
    vb_typename = "DataReport"

    def __init__(self, runtime, name: str, text: str):
        self.runtime, self.name, self.vb_name = runtime, name, name
        head, _blocks = _dsr_blocks(text)
        self.caption = to_str(head.get("caption", name)) if isinstance(head.get("caption", ""), str) else name
        self.datasource = to_str(head.get("datasource", "")) if isinstance(head.get("datasource"), str) else ""
        self.datamember = to_str(head.get("datamember", "")) if isinstance(head.get("datamember"), str) else ""
        self.win = None

    def _rs(self):
        de = self.runtime.interp.objects.get(self.datasource.lower()) if self.datasource else None
        if isinstance(de, DataEnvironment) and self.datamember:
            return de.recordset_for(self.datamember)
        return None

    def show(self):
        rs = self._rs()
        master = self.runtime.root
        if master is None:
            master = self.runtime.root = tk.Tk()
        win = tk.Toplevel(master)
        win.title(self.caption)
        win.geometry("760x480")
        cols = list(rs._cols) if rs is not None else ["(no data)"]
        tv = ttk.Treeview(win, columns=[f"c{i}" for i in range(len(cols))], show="headings")
        for i, c in enumerate(cols):
            tv.heading(f"c{i}", text=c)
            tv.column(f"c{i}", width=max(60, 700 // max(1, len(cols))))
        if rs is not None:
            for row in rs._rows:
                tv.insert("", "end", values=["" if v is None else to_str(v) for v in row])
        sb = ttk.Scrollbar(win, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tv.pack(fill="both", expand=True)
        print(f"[VB6] {self.name}.Show: Data Report shown as a table of {self.datasource}.{self.datamember} "
              f"({len(rs._rows) if rs is not None else 0} rows); report layout is not rendered", flush=True)
        self.win = win

    def vb_get(self, name):
        if name == "caption":
            return self.caption
        if name in ("datamember", "datasource"):
            return getattr(self, name)
        if name in ("show", "refresh", "hide", "printreport", "exportreport"):
            return self.vb_call(name, [])
        if name == "name":
            return self.name
        raise err(438, f"DataReport doesn't support '{name}'")

    def vb_set(self, name, value):
        if name == "caption":
            self.caption = to_str(value)
        elif name in ("datamember", "datasource"):
            setattr(self, name, to_str(getattr(value, "name", value)))
        elif name in ("windowstate", "topmargin", "bottommargin", "leftmargin", "rightmargin", "reportwidth"):
            pass
        else:
            raise err(438, f"DataReport doesn't support property '{name}'")

    def vb_call(self, name, args):
        if name == "show":
            self.show()
        elif name in ("hide", "unload"):
            if self.win is not None:
                self.win.destroy()
                self.win = None
        elif name in ("refresh", "printreport", "exportreport"):
            pass
        else:
            return self.vb_get(name)
        return EMPTY


def load_designers(runtime) -> None:
    """DataEnvironment / DataReport designers (.Dsr) of a native project -> global objects."""
    native = runtime.native
    if native is None:
        return
    from ..foreign.vb6_project import decode_vb
    reports = []
    for it in native.items:
        if it.kind != "Designer" or not it.path.is_file():
            continue
        try:
            text = decode_vb(it.path.read_bytes())[0]
        except OSError:
            continue
        m = re.search(r"^\s*Begin\s+\{([0-9A-Fa-f-]+)\}\s+(\w+)", text, re.M)
        if not m:
            continue
        guid, name = m.group(1).upper(), m.group(2)
        try:
            if guid.startswith("C0E45035"):
                runtime.interp.objects[name.lower()] = DataEnvironment(runtime, name, text)
            elif guid.startswith("78E93846"):
                reports.append((name, text))
        except Exception as ex:  # noqa: BLE001
            print(f"[VB6] designer {it.rel} could not be read: {ex}", flush=True)
    for name, text in reports:
        runtime.interp.objects[name.lower()] = DataReport(runtime, name, text)
