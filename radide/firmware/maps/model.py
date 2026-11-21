"""Calibration map definitions: data types, axes, maps, map packs (JSON / CSV). Pure Python + numpy.

A :class:`MapDef` describes one calibration table inside a binary: where its values are (file offset), the data
type and byte order of a cell, the table shape (``cols`` x ``rows``, X varies fastest when ``order`` is "row"),
the conversion to physical units (``phys = raw * factor + offset``) and its two axes (:class:`AxisDef`). An axis
is either stored in the binary (``address``), a list of fixed values, or just the cell index.

A :class:`MapPack` is the project's list of maps (+ the ECU address of file offset 0, ``base_address``, used
when importing / exporting ASAP2 addresses). It saves as JSON (``*.maps.json``) and CSV.
"""
from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

# name -> (numpy kind, size, min, max)
DTYPES: dict[str, tuple[str, int, float, float]] = {
    "u8": ("u1", 1, 0, 0xFF), "s8": ("i1", 1, -0x80, 0x7F),
    "u16": ("u2", 2, 0, 0xFFFF), "s16": ("i2", 2, -0x8000, 0x7FFF),
    "u32": ("u4", 4, 0, 0xFFFFFFFF), "s32": ("i4", 4, -0x80000000, 0x7FFFFFFF),
    "f32": ("f4", 4, -3.4e38, 3.4e38), "f64": ("f8", 8, -1.7e308, 1.7e308),
}
DTYPE_LABELS = {"u8": "8-bit unsigned", "s8": "8-bit signed", "u16": "16-bit unsigned", "s16": "16-bit signed",
                "u32": "32-bit unsigned", "s32": "32-bit signed", "f32": "32-bit float", "f64": "64-bit float"}
ENDIANS = ("le", "be")


def dtype_size(dt: str) -> int:
    return DTYPES[dt][1]


def np_dtype(dt: str, endian: str = "le") -> np.dtype:
    kind, size, _lo, _hi = DTYPES[dt]
    return np.dtype(kind if size == 1 else ("<" if endian == "le" else ">") + kind)


def is_float(dt: str) -> bool:
    return dt.startswith("f")


def read_array(data, offset: int, count: int, dt: str, endian: str = "le") -> np.ndarray:
    """*count* cells of type *dt* at *offset* as a float64 array (cells past the end of the data read as 0)."""
    size = dtype_size(dt)
    raw = bytes(data[offset:offset + count * size]) if offset >= 0 else b""
    if len(raw) < count * size:
        raw = raw + bytes(count * size - len(raw))
    return np.frombuffer(raw, dtype=np_dtype(dt, endian), count=count).astype(np.float64)


def encode_array(values, dt: str, endian: str = "le") -> bytes:
    """Raw cell values -> bytes (integers are rounded and clamped to the type's range)."""
    arr = np.asarray(values, dtype=np.float64).ravel()
    _k, _s, lo, hi = DTYPES[dt]
    if not is_float(dt):
        arr = np.clip(np.rint(np.nan_to_num(arr)), lo, hi)
    return arr.astype(np_dtype(dt, endian)).tobytes()


def fmt_hex(v: int) -> str:
    return f"0x{v:X}"


def parse_int(text) -> int:
    if isinstance(text, (int, np.integer)):
        return int(text)
    s = str(text).strip().replace("_", "")
    if s.lower().startswith("0x"):
        return int(s, 16)
    if s.lower().endswith("h") and all(c in "0123456789abcdefABCDEF" for c in s[:-1]):
        return int(s[:-1], 16)
    if s.startswith("$"):
        return int(s[1:], 16)
    return int(float(s))


@dataclass
class AxisDef:
    """One axis of a map: stored in the binary (``address``), fixed ``values``, or the cell index."""
    name: str = ""
    address: int | None = None
    count: int = 0
    dtype: str = "u16"
    endian: str = "le"
    factor: float = 1.0
    offset: float = 0.0
    unit: str = ""
    values: list[float] | None = None          # fixed physical values (A2L FIX_AXIS, CSV)
    step: int = 0                              # bytes between cells (0 = the cell size)

    @property
    def stored(self) -> bool:
        return self.address is not None and self.count > 0

    def nbytes(self) -> int:
        return self.count * dtype_size(self.dtype) if self.stored else 0

    def raw(self, data) -> np.ndarray:
        return read_array(data, int(self.address), self.count, self.dtype, self.endian) if self.stored else \
            np.zeros(0)

    def phys(self, data, n: int | None = None) -> np.ndarray:
        n = self.count if n is None or n <= 0 else n
        if self.stored:
            return self.raw(data) * self.factor + self.offset
        if self.values:
            v = list(self.values)[:n]
            return np.array(v + [v[-1] if v else 0.0] * (n - len(v)), dtype=np.float64)
        return np.arange(n, dtype=np.float64)

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v not in (None, "", 0) or k in ("factor",) or k == "count"}

    @classmethod
    def from_dict(cls, d: dict | None) -> "AxisDef":
        d = dict(d or {})
        if d.get("address") is not None:
            d["address"] = parse_int(d["address"])
        known = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        return cls(**known)


@dataclass
class MapDef:
    """A calibration table: a VALUE (1x1), a CURVE (cols x 1) or a MAP (cols x rows)."""
    name: str
    address: int
    cols: int = 1
    rows: int = 1
    dtype: str = "u8"
    endian: str = "le"
    order: str = "row"                         # "row": X fastest (row by row); "col": Y fastest
    factor: float = 1.0
    offset: float = 0.0
    unit: str = ""
    x_axis: AxisDef = field(default_factory=AxisDef)
    y_axis: AxisDef = field(default_factory=AxisDef)
    folder: str = ""
    description: str = ""
    source: str = ""                           # "finder", "a2l", "ini", "csv", "manual"
    lower: float | None = None
    upper: float | None = None
    digits: int | None = None

    # ------------------------------------------------------------------ geometry
    @property
    def kind(self) -> str:
        if self.cols <= 1 and self.rows <= 1:
            return "value"
        return "curve" if self.rows <= 1 else "map"

    @property
    def cells(self) -> int:
        return max(1, self.cols) * max(1, self.rows)

    @property
    def cell_size(self) -> int:
        return dtype_size(self.dtype)

    def nbytes(self) -> int:
        return self.cells * self.cell_size

    @property
    def end(self) -> int:
        return self.address + self.nbytes()

    def ranges(self) -> list[tuple[int, int]]:
        """File ranges [start, end) of the values and the stored axes."""
        out = [(self.address, self.end)]
        for ax in (self.x_axis, self.y_axis):
            if ax.stored:
                out.append((int(ax.address), int(ax.address) + ax.nbytes()))
        return out

    def span(self) -> tuple[int, int]:
        r = self.ranges()
        return min(s for s, _ in r), max(e for _, e in r)

    # ------------------------------------------------------------------ values
    def raw(self, data) -> np.ndarray:
        """Raw cell values as a (rows, cols) float array, whatever the storage order."""
        flat = read_array(data, self.address, self.cells, self.dtype, self.endian)
        r, c = max(1, self.rows), max(1, self.cols)
        return flat.reshape(c, r).T.copy() if self.order == "col" else flat.reshape(r, c)

    def phys(self, data) -> np.ndarray:
        return self.raw(data) * self.factor + self.offset

    def to_raw(self, phys) -> np.ndarray:
        f = self.factor if self.factor else 1.0
        return (np.asarray(phys, dtype=np.float64) - self.offset) / f

    def encode_phys(self, phys) -> bytes:
        """(rows, cols) physical values -> the bytes of the value block."""
        raw = self.to_raw(phys)
        r, c = max(1, self.rows), max(1, self.cols)
        raw = np.asarray(raw).reshape(r, c)
        flat = raw.T.ravel() if self.order == "col" else raw.ravel()
        return encode_array(flat, self.dtype, self.endian)

    def quantize(self, phys) -> np.ndarray:
        """What *phys* becomes once written (rounded to the raw resolution, clamped to the type)."""
        r, c = max(1, self.rows), max(1, self.cols)
        b = self.encode_phys(np.asarray(phys, dtype=np.float64).reshape(r, c))
        flat = np.frombuffer(b, dtype=np_dtype(self.dtype, self.endian)).astype(np.float64)
        raw = flat.reshape(c, r).T if self.order == "col" else flat.reshape(r, c)
        return raw * self.factor + self.offset

    def x_values(self, data) -> np.ndarray:
        return self.x_axis.phys(data, max(1, self.cols))

    def y_values(self, data) -> np.ndarray:
        return self.y_axis.phys(data, max(1, self.rows))

    def summary(self) -> str:
        dims = {"value": "value", "curve": f"{self.cols}", "map": f"{self.cols}x{self.rows}"}[self.kind]
        return f"{self.name}  {fmt_hex(self.address)}  {dims}  {self.dtype}{'' if self.cell_size == 1 else ' ' + self.endian.upper()}"

    # ------------------------------------------------------------------ (de)serialisation
    def to_dict(self) -> dict:
        d = {"name": self.name, "address": fmt_hex(self.address), "cols": self.cols, "rows": self.rows,
             "dtype": self.dtype, "endian": self.endian, "order": self.order, "factor": self.factor,
             "offset": self.offset, "unit": self.unit, "folder": self.folder, "description": self.description,
             "source": self.source}
        for k in ("lower", "upper", "digits"):
            if getattr(self, k) is not None:
                d[k] = getattr(self, k)
        for key, ax in (("x_axis", self.x_axis), ("y_axis", self.y_axis)):
            if ax.stored or ax.values or ax.name or ax.unit:
                a = ax.to_dict()
                if ax.address is not None:
                    a["address"] = fmt_hex(int(ax.address))
                d[key] = a
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MapDef":
        d = dict(d)
        x = AxisDef.from_dict(d.pop("x_axis", None))
        y = AxisDef.from_dict(d.pop("y_axis", None))
        d["address"] = parse_int(d.get("address", 0))
        known = {k: d[k] for k in cls.__dataclass_fields__ if k in d and k not in ("x_axis", "y_axis")}
        m = cls(**known)
        m.x_axis, m.y_axis = x, y
        return m

    def copy(self) -> "MapDef":
        return MapDef.from_dict(json.loads(json.dumps(self.to_dict())))


@dataclass
class MapPack:
    """The maps of one binary / project (``*.maps.json``)."""
    name: str = "Map pack"
    maps: list[MapDef] = field(default_factory=list)
    base_address: int = 0                      # ECU address of file offset 0 (A2L import / export)
    description: str = ""
    path: Path | None = None

    def __iter__(self):
        return iter(self.maps)

    def __len__(self) -> int:
        return len(self.maps)

    def get(self, name: str) -> MapDef | None:
        return next((m for m in self.maps if m.name == name), None)

    def add(self, m: MapDef, replace: bool = True) -> MapDef:
        old = self.get(m.name)
        if old is not None:
            if replace:
                self.maps[self.maps.index(old)] = m
                return m
            base, i = m.name, 2
            while self.get(f"{base}_{i}") is not None:
                i += 1
            m.name = f"{base}_{i}"
        self.maps.append(m)
        return m

    def remove(self, name: str) -> bool:
        m = self.get(name)
        if m is None:
            return False
        self.maps.remove(m)
        return True

    def folders(self) -> list[str]:
        return sorted({m.folder for m in self.maps})

    def at(self, offset: int) -> MapDef | None:
        """The map whose values or axes contain file *offset*."""
        for m in self.maps:
            if any(s <= offset < e for s, e in m.ranges()):
                return m
        return None

    def to_dict(self) -> dict:
        return {"format": "radide-mappack", "version": 1, "name": self.name, "description": self.description,
                "base_address": fmt_hex(self.base_address), "maps": [m.to_dict() for m in self.maps]}

    @classmethod
    def from_dict(cls, d: dict) -> "MapPack":
        return cls(name=d.get("name", "Map pack"), description=d.get("description", ""),
                   base_address=parse_int(d.get("base_address", 0) or 0),
                   maps=[MapDef.from_dict(m) for m in d.get("maps", [])])

    def save(self, path=None) -> Path:
        p = Path(path) if path else self.path
        if p is None:
            raise ValueError("no file name")
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        self.path = p
        return p

    @classmethod
    def load(cls, path) -> "MapPack":
        p = Path(path)
        pack = cls.from_dict(json.loads(p.read_text(encoding="utf-8")))
        pack.path = p
        return pack


def pack_path_for(binary) -> Path:
    """The map pack saved next to a binary: ``<file>.maps.json``."""
    p = Path(binary)
    return p.with_name(p.name + ".maps.json")


# ====================================================================== CSV
CSV_FIELDS = ["name", "folder", "address", "cols", "rows", "dtype", "endian", "order", "factor", "offset", "unit",
              "x_name", "x_address", "x_dtype", "x_endian", "x_factor", "x_offset", "x_unit", "x_values",
              "y_name", "y_address", "y_dtype", "y_endian", "y_factor", "y_offset", "y_unit", "y_values",
              "description"]


def pack_to_csv(pack: MapPack) -> str:
    out = io.StringIO()
    w = csv.DictWriter(out, CSV_FIELDS, lineterminator="\n")
    w.writeheader()
    for m in pack.maps:
        row = {"name": m.name, "folder": m.folder, "address": fmt_hex(m.address), "cols": m.cols, "rows": m.rows,
               "dtype": m.dtype, "endian": m.endian, "order": m.order, "factor": _num(m.factor),
               "offset": _num(m.offset), "unit": m.unit, "description": m.description}
        for p, ax in (("x", m.x_axis), ("y", m.y_axis)):
            row[f"{p}_name"] = ax.name
            row[f"{p}_address"] = fmt_hex(int(ax.address)) if ax.address is not None else ""
            row[f"{p}_dtype"], row[f"{p}_endian"] = ax.dtype, ax.endian
            row[f"{p}_factor"], row[f"{p}_offset"], row[f"{p}_unit"] = _num(ax.factor), _num(ax.offset), ax.unit
            row[f"{p}_values"] = " ".join(_num(v) for v in ax.values) if ax.values else ""
        w.writerow(row)
    return out.getvalue()


def _num(v) -> str:
    v = float(v)
    return str(int(v)) if v.is_integer() and abs(v) < 1e15 else repr(v)


def pack_from_csv(text: str, name: str = "CSV import") -> MapPack:
    pack = MapPack(name=name)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    for row in csv.DictReader(io.StringIO(text), dialect=dialect):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        if not row.get("name") or not row.get("address"):
            continue
        cols, rows = int(row.get("cols") or 1), int(row.get("rows") or 1)
        m = MapDef(name=row["name"], address=parse_int(row["address"]), cols=cols, rows=rows,
                   dtype=row.get("dtype") or "u8", endian=row.get("endian") or "le", order=row.get("order") or "row",
                   factor=float(row.get("factor") or 1), offset=float(row.get("offset") or 0),
                   unit=row.get("unit", ""), folder=row.get("folder", ""), description=row.get("description", ""),
                   source="csv")
        for p, n in (("x", cols), ("y", rows)):
            ax = AxisDef(name=row.get(f"{p}_name", ""), dtype=row.get(f"{p}_dtype") or m.dtype,
                         endian=row.get(f"{p}_endian") or m.endian, factor=float(row.get(f"{p}_factor") or 1),
                         offset=float(row.get(f"{p}_offset") or 0), unit=row.get(f"{p}_unit", ""))
            if row.get(f"{p}_address"):
                ax.address, ax.count = parse_int(row[f"{p}_address"]), n
            elif row.get(f"{p}_values"):
                ax.values = [float(v) for v in row[f"{p}_values"].replace(";", " ").split()]
                ax.count = len(ax.values)
            setattr(m, f"{p}_axis", ax)
        if m.dtype not in DTYPES:
            continue
        pack.add(m, replace=False)
    return pack


# ====================================================================== one map <-> text (Excel)
def map_to_tsv(m: MapDef, data, with_axes: bool = True, digits: int | None = None) -> str:
    z = m.phys(data)
    x, y = m.x_values(data), m.y_values(data)
    fmt = (lambda v: fmt_value(v, digits))
    lines = []
    if with_axes and m.kind != "value":
        lines.append("\t".join([""] + [fmt(v) for v in x]) if m.kind == "map" else "\t".join(fmt(v) for v in x))
    for r in range(z.shape[0]):
        cells = [fmt(v) for v in z[r]]
        if with_axes and m.kind == "map":
            cells.insert(0, fmt(y[r]))
        lines.append("\t".join(cells))
    return "\n".join(lines) + "\n"


def fmt_value(v: float, digits: int | None = None) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    if digits is not None:
        return f"{v:.{digits}f}"
    if float(v).is_integer() and abs(v) < 1e12:
        return str(int(v))
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def parse_tsv(text: str) -> list[list[float | None]]:
    """Excel / text grid -> rows of numbers (blank or non-numeric cells -> None). Accepts a decimal comma."""
    out = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not line.strip():
            continue
        sep = "\t" if "\t" in line else (";" if ";" in line else None)
        cells = line.split(sep) if sep else line.split()
        row = []
        for c in cells:
            c = c.strip().replace(" ", "")
            if c.count(",") == 1 and "." not in c:
                c = c.replace(",", ".")
            try:
                row.append(float(c))
            except ValueError:
                row.append(None)
        out.append(row)
    return out
