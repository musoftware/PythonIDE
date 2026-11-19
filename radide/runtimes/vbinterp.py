"""Interpreter for the VB6-compatible BASIC dialect (see vbparse.py).

UI objects (forms, controls) are provided by the host through the small
object protocol: vb_get(name), vb_set(name, value), vb_call(name, args),
and optional vb_default (default property name).
"""
from __future__ import annotations

import datetime as _dt
import math
import random
import re
import time

from .vbparse import Module, Proc, parse_expression


# ============================================================================ errors / control flow
class VBRuntimeError(Exception):
    def __init__(self, number, description, line=0, module=""):
        super().__init__(description)
        self.number, self.description, self.line, self.module = number, description, line, module


class _Exit(Exception):
    def __init__(self, what):
        self.what = what


class _Goto(Exception):
    def __init__(self, label):
        self.label = label


class _Resume(Exception):
    def __init__(self, target):
        self.target = target


class EndProgram(Exception):
    pass


def err(number, msg):
    return VBRuntimeError(number, msg)


# ============================================================================ values
class Empty:
    _inst = None

    def __new__(cls):
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst

    def __repr__(self):
        return "Empty"


EMPTY = Empty()


class Nothing:
    def __repr__(self):
        return "Nothing"


NOTHING = Nothing()


class Cell:
    __slots__ = ("value", "typ")

    def __init__(self, value=EMPTY, typ="variant"):
        self.value, self.typ = value, typ


def default_for(typ: str):
    typ = (typ or "variant").lower()
    if typ.startswith("new:"):
        return None                     # created by caller
    if typ in ("integer", "long", "single", "double", "currency", "byte", "decimal", "longlong"):
        return 0
    if typ == "string":
        return ""
    if typ == "boolean":
        return False
    if typ == "date":
        return _dt.datetime(1899, 12, 30)
    if typ in ("object", "form", "control", "collection") or typ[0].isupper():
        return NOTHING
    return EMPTY


def coerce(value, typ: str):
    typ = (typ or "variant").lower()
    if typ in ("integer", "long", "byte", "longlong"):
        return vb_round(to_num(value))
    if typ in ("single", "double", "currency", "decimal"):
        return float(to_num(value))
    if typ == "string":
        return to_str(value)
    if typ == "boolean":
        return to_bool(value)
    return value


class VBArray:
    def __init__(self, bounds: list[tuple[int, int]], typ="variant"):
        self.bounds = bounds
        self.typ = typ
        self.data = {}

    def _key(self, idx):
        if len(idx) != len(self.bounds):
            raise err(9, "Subscript out of range")
        key = []
        for i, (lo, hi) in zip(idx, self.bounds):
            i = vb_round(to_num(i))
            if not lo <= i <= hi:
                raise err(9, "Subscript out of range")
            key.append(i)
        return tuple(key)

    def get(self, idx):
        k = self._key(idx)
        if k not in self.data:
            return default_for(self.typ)
        return self.data[k]

    def set(self, idx, value):
        self.data[self._key(idx)] = coerce(value, self.typ)

    def items(self):
        if len(self.bounds) != 1:
            return [self.data.get(k, default_for(self.typ)) for k in sorted(self.data)]
        lo, hi = self.bounds[0]
        return [self.data.get((i,), default_for(self.typ)) for i in range(lo, hi + 1)]

    def redim(self, bounds, preserve):
        old = self.data
        self.bounds = bounds
        self.data = {}
        if preserve:
            for k, v in old.items():
                try:
                    self.data[self._key(k)] = v
                except VBRuntimeError:
                    pass


class Collection:
    def __init__(self):
        self.items: list = []
        self.keys: dict = {}

    def vb_get(self, name):
        if name == "count":
            return len(self.items)
        raise err(438, f"Object doesn't support property '{name}'")

    def vb_call(self, name, args):
        if name == "add":
            item = args[0]
            key = args[1] if len(args) > 1 and args[1] is not EMPTY else None
            self.items.append(item)
            if key is not None:
                self.keys[to_str(key).lower()] = item
            return EMPTY
        if name == "item":
            return self._item(args[0])
        if name == "remove":
            k = args[0]
            if isinstance(k, str):
                item = self.keys.pop(k.lower())
                self.items.remove(item)
            else:
                self.items.pop(int(k) - 1)
            return EMPTY
        if name == "count":
            return len(self.items)
        raise err(438, f"Object doesn't support method '{name}'")

    def _item(self, k):
        if isinstance(k, str):
            if k.lower() not in self.keys:
                raise err(5, "Invalid procedure call or argument")
            return self.keys[k.lower()]
        i = int(to_num(k))
        if not 1 <= i <= len(self.items):
            raise err(9, "Subscript out of range")
        return self.items[i - 1]

    vb_default = "item"


class UDT:
    """Instance of a user-defined Type."""

    def __init__(self, name, members):
        self._name = name
        self._fields = {m.lower(): default_for(t) for m, t in members}

    def vb_get(self, name):
        if name in self._fields:
            return self._fields[name]
        raise err(438, f"'{name}' is not a member of {self._name}")

    def vb_set(self, name, value):
        self._fields[name] = value


class ErrObject:
    def __init__(self):
        self.number, self.description, self.source = 0, "", ""

    def vb_get(self, name):
        return {"number": self.number, "description": self.description, "source": self.source}.get(name, EMPTY)

    def vb_set(self, name, value):
        setattr(self, name, value)

    def vb_call(self, name, args):
        if name == "clear":
            self.number, self.description = 0, ""
            return EMPTY
        if name == "raise":
            raise err(int(to_num(args[0])), to_str(args[2]) if len(args) > 2 else "Application-defined error")
        return self.vb_get(name)

    vb_default = "number"


# ============================================================================ conversions
def vb_round(x):
    """VB rounds half to even (banker's rounding) when converting to Integer."""
    return int(round(x)) if not isinstance(x, int) else x


def to_num(v):
    if isinstance(v, bool):
        return -1 if v else 0
    if isinstance(v, (int, float)):
        return v
    if v is EMPTY or v is None:
        return 0
    if isinstance(v, _dt.datetime):
        d = v - _dt.datetime(1899, 12, 30)
        return d.days + d.seconds / 86400
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            raise err(13, "Type mismatch")
        try:
            if s.lower().startswith("&h"):
                return int(s[2:], 16)
            f = float(s)
            return int(f) if f.is_integer() and "." not in s and "e" not in s.lower() else f
        except ValueError:
            raise err(13, f"Type mismatch: \"{v}\" is not a number") from None
    if hasattr(v, "vb_get"):
        return to_num(default_value(v))
    raise err(13, "Type mismatch")


def to_str(v):
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return "True" if v else "False"
    if v is EMPTY or v is None:
        return ""
    if isinstance(v, float):
        if v.is_integer() and abs(v) < 1e15:
            return str(int(v))
        return repr(round(v, 15)).rstrip("0").rstrip(".") if "e" not in repr(v) else repr(v)
    if isinstance(v, _dt.datetime):
        if v.hour == v.minute == v.second == 0:
            return v.strftime("%d/%m/%Y")
        return v.strftime("%d/%m/%Y %H:%M:%S")
    if hasattr(v, "vb_get"):
        return to_str(default_value(v))
    return str(v)


def to_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False
    return to_num(v) != 0


def default_value(obj):
    name = getattr(obj, "vb_default", None)
    if name is None:
        raise err(438, "Object doesn't support this property or method")
    if isinstance(obj, Collection):
        return obj
    return obj.vb_get(name)


def is_numeric_like(v):
    if isinstance(v, (int, float, bool)):
        return True
    if isinstance(v, str):
        try:
            to_num(v)
            return True
        except VBRuntimeError:
            return False
    return False


def vb_compare(a, b, text_mode=False):
    if hasattr(a, "vb_get") and not isinstance(a, Collection):
        a = default_value(a)
    if hasattr(b, "vb_get") and not isinstance(b, Collection):
        b = default_value(b)
    if isinstance(a, str) and isinstance(b, str):
        if text_mode:
            a, b = a.lower(), b.lower()
        return (a > b) - (a < b)
    if a is EMPTY and isinstance(b, str):
        a = ""
    if b is EMPTY and isinstance(a, str):
        b = ""
    if isinstance(a, str) and isinstance(b, str):
        return (a > b) - (a < b)
    if isinstance(a, str) and not is_numeric_like(a) or isinstance(b, str) and not is_numeric_like(b):
        sa, sb = to_str(a), to_str(b)
        return (sa > sb) - (sa < sb)
    x, y = to_num(a), to_num(b)
    return (x > y) - (x < y)


def vb_like(s, pattern):
    rx = ""
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            rx += ".*"
        elif c == "?":
            rx += "."
        elif c == "#":
            rx += r"\d"
        elif c == "[":
            j = pattern.find("]", i)
            body = pattern[i + 1:j]
            rx += "[" + ("^" + body[1:] if body.startswith("!") else body) + "]"
            i = j
        else:
            rx += re.escape(c)
        i += 1
    return re.fullmatch(rx, s, re.S) is not None


def vb_format(value, fmt=""):
    fmt = to_str(fmt)
    low = fmt.lower()
    if isinstance(value, _dt.datetime) or low in ("short date", "long date", "short time", "long time",
                                                   "general date") or any(t in low for t in ("yy", "dd", "nn", "hh")):
        d = value if isinstance(value, _dt.datetime) else to_date(value)
        named = {"short date": "%d/%m/%Y", "long date": "%A, %d %B %Y", "short time": "%H:%M",
                 "long time": "%H:%M:%S", "general date": "%d/%m/%Y %H:%M:%S"}
        if low in named:
            return d.strftime(named[low])
        out = fmt
        for a, b in (("yyyy", "%Y"), ("yy", "%y"), ("mmmm", "%B"), ("mmm", "%b"), ("dddd", "%A"),
                     ("ddd", "%a"), ("dd", "%d"), ("hh", "%H"), ("nn", "%M"), ("ss", "%S"), ("mm", "%m"),
                     ("AM/PM", "%p")):
            out = re.sub(re.escape(a), b, out, flags=re.I)
        return d.strftime(out)
    if not fmt:
        return to_str(value)
    n = to_num(value)
    if low in ("currency",):
        return f"{n:,.2f}"
    if low in ("fixed",):
        return f"{n:.2f}"
    if low in ("standard",):
        return f"{n:,.2f}"
    if low in ("percent",):
        return f"{n * 100:.2f}%"
    if low in ("general number",):
        return to_str(value)
    pct = fmt.endswith("%")
    core = fmt.rstrip("%")
    m = re.match(r"([^0#,.]*)([0#,]*)(?:\.([0#]*))?(.*)", core)
    if not m:
        return to_str(value)
    prefix, ip, dp, suffix = m.groups()
    dec = len(dp or "")
    if pct:
        n *= 100
    s = f"{n:,.{dec}f}" if "," in ip else f"{n:.{dec}f}"
    zeros = ip.replace(",", "").count("0")
    int_part = s.split(".")[0].lstrip("-")
    if len(int_part.replace(",", "")) < zeros:
        s = ("-" if n < 0 else "") + int_part.replace(",", "").zfill(zeros) + (("." + s.split(".")[1]) if dec else "")
    if dp and dp.endswith("#"):
        s = s.rstrip("0").rstrip(".") if "." in s else s
    return prefix + s + suffix + ("%" if pct else "")


def to_date(v):
    if isinstance(v, _dt.datetime):
        return v
    if isinstance(v, (int, float)):
        return _dt.datetime(1899, 12, 30) + _dt.timedelta(days=float(v))
    s = to_str(v).strip()
    for f in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S",
              "%d/%m/%Y %H:%M:%S", "%H:%M:%S", "%H:%M", "%m/%d/%Y %I:%M:%S %p", "%I:%M:%S %p"):
        try:
            return _dt.datetime.strptime(s, f)
        except ValueError:
            continue
    raise err(13, f"Type mismatch: \"{s}\" is not a date")


# ============================================================================ builtins
COLORS = {"vbblack": 0x0, "vbred": 0xFF, "vbgreen": 0xFF00, "vbyellow": 0xFFFF, "vbblue": 0xFF0000,
          "vbmagenta": 0xFF00FF, "vbcyan": 0xFFFF00, "vbwhite": 0xFFFFFF}
CONSTANTS = {
    "vbcrlf": "\r\n", "vbnewline": "\r\n", "vbcr": "\r", "vblf": "\n", "vbtab": "\t",
    "vbnullstring": "", "vbnullchar": "\0", "vbback": "\b",
    "vbokonly": 0, "vbokcancel": 1, "vbabortretryignore": 2, "vbyesnocancel": 3, "vbyesno": 4,
    "vbretrycancel": 5, "vbcritical": 16, "vbquestion": 32, "vbexclamation": 48, "vbinformation": 64,
    "vbdefaultbutton1": 0, "vbdefaultbutton2": 256, "vbdefaultbutton3": 512,
    "vbok": 1, "vbcancel": 2, "vbabort": 3, "vbretry": 4, "vbignore": 5, "vbyes": 6, "vbno": 7,
    "vbunchecked": 0, "vbchecked": 1, "vbgrayed": 2, "vbmodal": 1, "vbmodeless": 0,
    "vbtextcompare": 1, "vbbinarycompare": 0, "vbkeyreturn": 13, "vbkeyescape": 27, "vbkeyspace": 32,
    "vbkeyback": 8, "vbkeytab": 9, "vbkeydelete": 46, "vbkeyleft": 37, "vbkeyup": 38, "vbkeyright": 39,
    "vbkeydown": 40, "vbleftbutton": 1, "vbrightbutton": 2, "vbmiddlebutton": 4,
    "vbshiftmask": 1, "vbctrlmask": 2, "vbaltmask": 4, "vbuppercase": 1, "vblowercase": 2,
    "vbpropercase": 3, "vbformcontrolmenu": 0, "vbformcode": 1, "vbappwindows": 2,
    "vbsunday": 1, "vbmonday": 2, "vbusesystemdayofweek": 0, **COLORS,
}


def _mid(s, start, length=None):
    s = to_str(s)
    start = int(to_num(start))
    if start < 1:
        raise err(5, "Invalid procedure call or argument")
    if length is None or length is EMPTY:
        return s[start - 1:]
    return s[start - 1:start - 1 + int(to_num(length))]


def _instr(*a):
    if len(a) >= 3 and not isinstance(a[0], str) and is_numeric_like(a[0]) and not isinstance(a[1], (int, float)):
        start, s, sub = int(to_num(a[0])), to_str(a[1]), to_str(a[2])
        text = len(a) > 3 and to_num(a[3]) == 1
    else:
        start, s, sub = 1, to_str(a[0]), to_str(a[1])
        text = len(a) > 2 and to_num(a[2]) == 1
    if text:
        s, sub = s.lower(), sub.lower()
    return s.find(sub, start - 1) + 1


def _instrrev(s, sub, start=-1, *_):
    s, sub = to_str(s), to_str(sub)
    end = len(s) if start in (-1, EMPTY) else int(to_num(start))
    return s.rfind(sub, 0, end) + 1


def _val(s):
    m = re.match(r"\s*([-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?)", to_str(s).replace(" ", ""))
    if not m:
        return 0
    f = float(m.group(1))
    return int(f) if f.is_integer() and "." not in m.group(1) else f


def _cint(v):
    return vb_round(to_num(v))


def _split(s, delim=" ", limit=-1, *_):
    s, delim = to_str(s), to_str(delim)
    parts = s.split(delim) if delim else [s]
    if limit not in (-1, EMPTY) and int(to_num(limit)) > 0:
        n = int(to_num(limit))
        parts = s.split(delim, n - 1)
    arr = VBArray([(0, len(parts) - 1)], "string")
    for i, p in enumerate(parts):
        arr.data[(i,)] = p
    return arr


def _join(arr, delim=" "):
    return to_str(delim).join(to_str(x) for x in (arr.items() if isinstance(arr, VBArray) else arr))


def _array(*items):
    arr = VBArray([(0, len(items) - 1)])
    for i, v in enumerate(items):
        arr.data[(i,)] = v
    return arr


def _ubound(arr, dim=1):
    if not isinstance(arr, VBArray):
        raise err(13, "Type mismatch (UBound needs an array)")
    return arr.bounds[int(to_num(dim)) - 1][1]


def _lbound(arr, dim=1):
    if not isinstance(arr, VBArray):
        raise err(13, "Type mismatch (LBound needs an array)")
    return arr.bounds[int(to_num(dim)) - 1][0]


def _strconv(s, mode, *_):
    s, mode = to_str(s), int(to_num(mode))
    return s.upper() if mode == 1 else s.lower() if mode == 2 else s.title() if mode == 3 else s


def _iif(c, a, b):
    return a if to_bool(c) else b


def _datepart_add(interval, n, d):
    d = to_date(d)
    n = to_num(n)
    iv = to_str(interval).lower()
    if iv == "d" or iv == "y" or iv == "w":
        return d + _dt.timedelta(days=n)
    if iv == "ww":
        return d + _dt.timedelta(weeks=n)
    if iv == "h":
        return d + _dt.timedelta(hours=n)
    if iv == "n":
        return d + _dt.timedelta(minutes=n)
    if iv == "s":
        return d + _dt.timedelta(seconds=n)
    if iv in ("m", "q", "yyyy"):
        months = int(n) * (3 if iv == "q" else 12 if iv == "yyyy" else 1)
        y, m = divmod(d.month - 1 + months, 12)
        import calendar
        day = min(d.day, calendar.monthrange(d.year + y, m + 1)[1])
        return d.replace(year=d.year + y, month=m + 1, day=day)
    raise err(5, "Invalid procedure call or argument")


def _datediff(interval, a, b, *_):
    a, b = to_date(a), to_date(b)
    iv = to_str(interval).lower()
    delta = b - a
    if iv in ("d", "y", "w"):
        return delta.days
    if iv == "ww":
        return delta.days // 7
    if iv == "h":
        return int(delta.total_seconds() // 3600)
    if iv == "n":
        return int(delta.total_seconds() // 60)
    if iv == "s":
        return int(delta.total_seconds())
    if iv == "m":
        return (b.year - a.year) * 12 + b.month - a.month
    if iv == "yyyy":
        return b.year - a.year
    if iv == "q":
        return ((b.year - a.year) * 12 + b.month - a.month) // 3
    raise err(5, "Invalid procedure call or argument")



# ---------------------------------------------------------------- RadCall (RAD Hub, docs/CONTRACTS.md)
def vb_to_json(v):
    """VB value -> JSON-able Python value."""
    if v is EMPTY or v is NOTHING or v is None:
        return None
    if isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, VBArray):
        return [vb_to_json(x) for x in v.items()]
    if isinstance(v, Collection):
        if v.keys and len(v.keys) == len(v.items):
            return {k: vb_to_json(x) for k, x in v.keys.items()}
        return [vb_to_json(x) for x in v.items]
    if isinstance(v, UDT):
        return {k: vb_to_json(x) for k, x in v._fields.items()}
    if isinstance(v, _dt.datetime):
        return v.isoformat(sep=" ")
    return to_str(v)


def json_to_vb(v):
    """JSON value -> VB value (list -> 0-based array, object -> keyed Collection)."""
    if v is None:
        return EMPTY
    if isinstance(v, list):
        return _array(*[json_to_vb(x) for x in v])
    if isinstance(v, dict):
        c = Collection()
        for k, x in v.items():
            c.vb_call("add", [json_to_vb(x), str(k)])
        return c
    return v


def _radcall_module():
    import sys
    mod = sys.modules.get("radcall")
    if mod is None or not hasattr(mod, "radcall"):
        import importlib.util
        from pathlib import Path
        path = Path(__file__).resolve().parent / "clients" / "python" / "radcall.py"
        spec = importlib.util.spec_from_file_location("radcall", str(path))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["radcall"] = mod
        spec.loader.exec_module(mod)
    return mod


def _radcall(name, *args):
    """RadCall("Module.Function", args...) - call a function written in another language."""
    rc = _radcall_module()
    try:
        return json_to_vb(rc.radcall(to_str(name), *[vb_to_json(a) for a in args]))
    except rc.RadCallError as e:
        raise err(440, f"RadCall error: {e}") from None


BUILTINS = {
    "len": lambda s: len(to_str(s)) if not isinstance(s, VBArray) else len(s.items()),
    "left": lambda s, n: to_str(s)[:int(to_num(n))],
    "right": lambda s, n: to_str(s)[len(to_str(s)) - int(to_num(n)):] if int(to_num(n)) else "",
    "mid": _mid, "ucase": lambda s: to_str(s).upper(), "lcase": lambda s: to_str(s).lower(),
    "trim": lambda s: to_str(s).strip(" "), "ltrim": lambda s: to_str(s).lstrip(" "),
    "rtrim": lambda s: to_str(s).rstrip(" "), "instr": _instr, "instrrev": _instrrev,
    "replace": lambda s, a, b, *r: to_str(s).replace(to_str(a), to_str(b)),
    "space": lambda n: " " * int(to_num(n)),
    "string": lambda n, c: (to_str(c)[:1] if isinstance(c, str) else chr(int(to_num(c)))) * int(to_num(n)),
    "strreverse": lambda s: to_str(s)[::-1], "strcomp": lambda a, b, m=0: vb_compare(a, b, to_num(m) == 1),
    "strconv": _strconv, "chr": lambda n: chr(int(to_num(n))), "chrw": lambda n: chr(int(to_num(n))),
    "asc": lambda s: ord(to_str(s)[0]) if to_str(s) else 0, "ascw": lambda s: ord(to_str(s)[0]),
    "str": lambda v: (" " if to_num(v) >= 0 else "") + to_str(to_num(v)), "cstr": to_str, "val": _val,
    "cint": _cint, "clng": _cint, "cbyte": _cint, "cdbl": lambda v: float(to_num(v)),
    "csng": lambda v: float(to_num(v)), "ccur": lambda v: round(float(to_num(v)), 4),
    "cbool": to_bool, "cdate": to_date, "cvar": lambda v: v, "cdec": lambda v: float(to_num(v)),
    "int": lambda v: math.floor(to_num(v)), "fix": lambda v: int(to_num(v)),
    "abs": lambda v: abs(to_num(v)), "sgn": lambda v: (to_num(v) > 0) - (to_num(v) < 0),
    "sqr": lambda v: math.sqrt(to_num(v)), "exp": lambda v: math.exp(to_num(v)),
    "log": lambda v: math.log(to_num(v)), "sin": lambda v: math.sin(to_num(v)),
    "cos": lambda v: math.cos(to_num(v)), "tan": lambda v: math.tan(to_num(v)),
    "atn": lambda v: math.atan(to_num(v)),
    "round": lambda v, d=0: round(to_num(v), int(to_num(d))) if int(to_num(d)) else vb_round(to_num(v)),
    "rnd": lambda *a: random.random(), "hex": lambda v: format(int(to_num(v)), "X"),
    "oct": lambda v: format(int(to_num(v)), "o"),
    "isnumeric": lambda v: is_numeric_like(v) and not (isinstance(v, str) and v.strip() == ""),
    "isempty": lambda v: v is EMPTY, "isnull": lambda v: v is None, "isarray": lambda v: isinstance(v, VBArray),
    "isobject": lambda v: hasattr(v, "vb_get") or v is NOTHING, "isdate": lambda v: _is_date(v),
    "isnothing": lambda v: v is NOTHING,
    "typename": lambda v: _typename(v), "vartype": lambda v: _vartype(v),
    "ubound": _ubound, "lbound": _lbound, "split": _split, "join": _join, "array": _array,
    "iif": _iif, "format": vb_format, "format$": vb_format,
    "formatnumber": lambda v, d=2, *_: f"{to_num(v):,.{int(to_num(d))}f}",
    "formatcurrency": lambda v, d=2, *_: f"{to_num(v):,.{int(to_num(d))}f}",
    "formatpercent": lambda v, d=2, *_: f"{to_num(v) * 100:.{int(to_num(d))}f}%",
    "now": lambda: _dt.datetime.now().replace(microsecond=0),
    "date": lambda: _dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
    "time": lambda: _dt.datetime(1899, 12, 30).replace(hour=_dt.datetime.now().hour,
                                                       minute=_dt.datetime.now().minute,
                                                       second=_dt.datetime.now().second),
    "timer": lambda: round(time.time() - time.mktime(_dt.date.today().timetuple()), 2),
    "year": lambda d: to_date(d).year, "month": lambda d: to_date(d).month, "day": lambda d: to_date(d).day,
    "hour": lambda d: to_date(d).hour, "minute": lambda d: to_date(d).minute,
    "second": lambda d: to_date(d).second, "weekday": lambda d, *_: (to_date(d).weekday() + 1) % 7 + 1,
    "dateserial": lambda y, m, d: _dt.datetime(int(to_num(y)), int(to_num(m)), int(to_num(d))),
    "timeserial": lambda h, m, s: _dt.datetime(1899, 12, 30, int(to_num(h)), int(to_num(m)), int(to_num(s))),
    "dateadd": _datepart_add, "datediff": _datediff, "datevalue": to_date, "timevalue": to_date,
    "monthname": lambda m, abbr=False: _dt.date(2000, int(to_num(m)), 1).strftime("%b" if to_bool(abbr) else "%B"),
    "weekdayname": lambda w, abbr=False, *_: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday",
                                               "Friday", "Saturday"][int(to_num(w)) - 1][:3 if to_bool(abbr) else None],
    "rgb": lambda r, g, b: int(to_num(r)) + int(to_num(g)) * 256 + int(to_num(b)) * 65536,
    "qbcolor": lambda n: [0x0, 0x800000, 0x8000, 0x808000, 0x80, 0x800080, 0x8080, 0xC0C0C0, 0x808080,
                          0xFF0000, 0xFF00, 0xFFFF00, 0xFF, 0xFF00FF, 0xFFFF, 0xFFFFFF][int(to_num(n))],
    "environ": lambda n: __import__("os").environ.get(to_str(n), ""),
    "nz": lambda v, d="": d if v is None or v is EMPTY else v,
    "radcall": _radcall,
}


def _is_date(v):
    try:
        to_date(v)
        return True
    except VBRuntimeError:
        return False


def _typename(v):
    if isinstance(v, bool):
        return "Boolean"
    if isinstance(v, int):
        return "Long" if abs(v) > 32767 else "Integer"
    if isinstance(v, float):
        return "Double"
    if isinstance(v, str):
        return "String"
    if isinstance(v, _dt.datetime):
        return "Date"
    if v is EMPTY:
        return "Empty"
    if v is NOTHING:
        return "Nothing"
    if isinstance(v, VBArray):
        return _typename(default_for(v.typ)) + "()"
    return getattr(v, "vb_typename", type(v).__name__)


def _vartype(v):
    return {"Empty": 0, "Integer": 2, "Long": 3, "Double": 5, "Date": 7, "String": 8, "Boolean": 11,
            "Nothing": 9}.get(_typename(v), 9)


# ============================================================================ frames
class Frame:
    def __init__(self, proc: Proc | None, module: "ModuleState", me=None):
        self.proc = proc
        self.module = module
        self.locals: dict[str, Cell] = {}
        self.with_stack: list = []
        self.on_error = "0"           # "0" | "next" | label
        self.err_resume = None        # (index list) for Resume
        self.line = proc.line if proc else 0
        self.me = me
        self.gosub: list = []


class ModuleState:
    """Runtime state of a parsed module (a form's code or a .bas module)."""

    def __init__(self, mod: Module, is_form: bool):
        self.mod = mod
        self.name = mod.name
        self.is_form = is_form
        self.vars: dict[str, Cell] = {}
        self.consts: dict[str, object] = {}
        self.types: dict[str, list] = {}
        self.public: set[str] = set()


# ============================================================================ interpreter
class Interpreter:
    def __init__(self, host=None):
        self.host = host                    # UI host: msgbox, inputbox, doevents, forms...
        self.modules: dict[str, ModuleState] = {}
        self.globals: dict[str, Cell] = {}
        self.global_procs: dict[str, tuple[ModuleState, Proc]] = {}
        self.objects: dict[str, object] = {}   # forms, App, Screen ... by lower-case name
        self.err = ErrObject()
        self.stack: list[Frame] = []
        self.trace = None                   # debugger hook: trace(frame, line)
        self.output = print
        self.builtins = dict(BUILTINS)
        self.builtins.update({
            "msgbox": self._msgbox, "inputbox": self._inputbox, "doevents": self._doevents,
            "randomize": lambda *a: random.seed(), "createobject": self._createobject,
            "loadpicture": lambda *a: to_str(a[0]) if a else "",
        })

    # ------------------------------------------------------------ loading
    def load_module(self, mod: Module, is_form=False, me=None) -> ModuleState:
        st = ModuleState(mod, is_form)
        self.modules[mod.name.lower()] = st
        frame = Frame(None, st, me)
        for decl in mod.decls:
            kind = decl[0]
            if kind == "const":
                for name, expr in decl[2]:
                    st.consts[name] = self.eval(expr, frame)
                    if decl[3] or not is_form:
                        self.globals.setdefault(name, Cell(st.consts[name]))
            elif kind == "dim":
                for name, bounds, typ in decl[2]:
                    cell = Cell(self._new_value(bounds, typ, frame), self._base_type(typ))
                    st.vars[name] = cell
                    if decl[3] and not is_form:
                        self.globals[name] = cell
                        st.public.add(name)
            elif kind == "type":
                st.types[decl[2].lower()] = decl[3]
                self.types_global()[decl[2].lower()] = decl[3]
            elif kind == "enum":
                for name, expr in decl[3]:
                    val = self.eval(expr, frame) if not isinstance(expr, int) else expr
                    self.globals[name] = Cell(val)
        for pname, proc in mod.procs.items():
            if proc.public and not is_form:
                self.global_procs[pname] = (st, proc)
        return st

    def types_global(self):
        if not hasattr(self, "_types"):
            self._types = {}
        return self._types

    @staticmethod
    def _base_type(typ):
        return (typ or "variant").replace("new:", "").lower()

    def _new_value(self, bounds, typ, frame):
        base = self._base_type(typ)
        if bounds is not None:
            if not bounds:
                return VBArray([(0, -1)], base)           # dynamic array: Dim a()
            bl = []
            for lo, hi in bounds:
                bl.append((int(to_num(self.eval(lo, frame))) if lo is not None else 0,
                           int(to_num(self.eval(hi, frame)))))
            return VBArray(bl, base)
        if (typ or "").startswith("new:"):
            return self._instantiate(base)
        if base in self.types_global():
            return UDT(base, self.types_global()[base])
        return default_for(base)

    def _instantiate(self, cls):
        if cls == "collection":
            return Collection()
        if cls in self.types_global():
            return UDT(cls, self.types_global()[cls])
        if self.host is not None:
            obj = self.host.new_object(cls)
            if obj is not None:
                return obj
        raise err(429, f"ActiveX component can't create object: {cls}")

    # ------------------------------------------------------------ host services
    def _msgbox(self, prompt="", buttons=0, title=""):
        if self.host is None:
            self.output(to_str(prompt))
            return 1
        return self.host.msgbox(to_str(prompt), int(to_num(buttons)) if buttons is not EMPTY else 0,
                                to_str(title) if title is not EMPTY else "")

    def _inputbox(self, prompt="", title="", default="", *_):
        if self.host is None:
            return to_str(default)
        return self.host.inputbox(to_str(prompt), to_str(title), to_str(default))

    def _doevents(self):
        if self.host is not None:
            self.host.doevents()
        return 0

    def _createobject(self, progid, *_):
        if self.host is not None:
            obj = self.host.create_object(to_str(progid))
            if obj is not None:
                return obj
        raise err(429, f"ActiveX component can't create object: {progid}")

    # ------------------------------------------------------------ calling
    def find_proc(self, name: str, frame: Frame | None):
        name = name.lower()
        if frame is not None and name in frame.module.mod.procs:
            return frame.module, frame.module.mod.procs[name]
        return self.global_procs.get(name)

    def call_proc(self, st: ModuleState, proc: Proc, args: list, arg_cells=None, me=None):
        frame = Frame(proc, st, me)
        for i, p in enumerate(proc.params):
            if p.paramarray:
                rest = args[i:]
                frame.locals[p.name] = Cell(_array(*rest))
                break
            if i < len(args) and args[i] is not _MISSING:
                cell = arg_cells[i] if (arg_cells and p.byref and arg_cells[i] is not None) else Cell(args[i])
                frame.locals[p.name] = cell
            elif p.optional or p.default is not None:
                frame.locals[p.name] = Cell(self.eval(p.default, frame) if p.default is not None else EMPTY)
            else:
                raise err(449, f"Argument not optional: {p.name} (calling {proc.display or proc.name})")
        if proc.kind in ("function", "get"):
            frame.locals[proc.name.split(":")[-1]] = Cell(EMPTY)
        self.stack.append(frame)
        try:
            self.run_block(proc.body, frame, top=True)
        except _Exit as e:
            if e.what not in ("sub", "function", "property"):
                raise
        finally:
            self.stack.pop()
        if proc.kind in ("function", "get"):
            return frame.locals[proc.name.split(":")[-1]].value
        return EMPTY

    def call_by_name(self, module_name: str, proc_name: str, args=(), me=None, arg_cells=None):
        """Called by the UI host to run an event handler. Returns (found, value)."""
        st = self.modules.get(module_name.lower())
        if st is None or proc_name.lower() not in st.mod.procs:
            return False, None
        proc = st.mod.procs[proc_name.lower()]
        return True, self.call_proc(st, proc, list(args), arg_cells, me)

    # ------------------------------------------------------------ blocks / statements
    def run_block(self, stmts: list, frame: Frame, top=False):
        i = 0
        labels = None
        while i < len(stmts):
            st = stmts[i]
            try:
                self.exec(st, frame)
                i += 1
            except _Goto as g:
                if labels is None:
                    labels = {s[2]: n for n, s in enumerate(stmts) if s[0] == "label"}
                if g.label in labels:
                    i = labels[g.label] + 1
                    continue
                raise
            except _Resume as r:
                if not top:
                    raise
                if r.target == "next" and frame.err_resume is not None:
                    i = frame.err_resume + 1
                elif r.target == "" and frame.err_resume is not None:
                    i = frame.err_resume
                else:
                    raise _Goto(r.target) from None
                frame.err_resume = None
            except VBRuntimeError as e:
                if not e.line:
                    e.line = frame.line
                    e.module = frame.module.name
                self.err.number, self.err.description = e.number, e.description
                if frame.on_error == "next":
                    i += 1
                    continue
                if frame.on_error not in ("0", "") and top:
                    if labels is None:
                        labels = {s[2]: n for n, s in enumerate(stmts) if s[0] == "label"}
                    label = frame.on_error
                    if label in labels:
                        frame.err_resume = i
                        frame.on_error = "0"        # errors inside the handler propagate
                        i = labels[label] + 1
                        continue
                raise

    def exec(self, st, frame: Frame):
        kind = st[0]
        frame.line = st[1]
        if self.trace is not None and kind not in ("label", "nop"):
            self.trace(frame, st[1])
        m = getattr(self, "x_" + kind, None)
        if m is None:
            raise err(0, f"statement '{kind}' is not supported")
        m(st, frame)

    def x_nop(self, st, frame):
        pass

    def x_label(self, st, frame):
        pass

    def x_dim(self, st, frame):
        for name, bounds, typ in st[2]:
            if frame.proc is None:
                frame.module.vars[name] = Cell(self._new_value(bounds, typ, frame), self._base_type(typ))
            else:
                frame.locals[name] = Cell(self._new_value(bounds, typ, frame), self._base_type(typ))

    def x_const(self, st, frame):
        for name, expr in st[2]:
            frame.locals[name] = Cell(self.eval(expr, frame))

    def x_redim(self, st, frame):
        for name, bounds, typ in st[2]:
            cell = self.lookup_cell(name, frame)
            bl = [(int(to_num(self.eval(lo, frame))) if lo is not None else 0, int(to_num(self.eval(hi, frame))))
                  for lo, hi in bounds]
            if cell is None:
                frame.locals[name] = Cell(VBArray(bl, self._base_type(typ)))
            elif isinstance(cell.value, VBArray):
                cell.value.redim(bl, st[3])
            else:
                cell.value = VBArray(bl, self._base_type(typ))

    def x_erase(self, st, frame):
        for name in st[2]:
            cell = self.lookup_cell(name, frame)
            if cell is not None and isinstance(cell.value, VBArray):
                cell.value.data = {}

    def x_assign(self, st, frame):
        self.assign(st[2], self.eval(st[3], frame), frame)

    def x_set(self, st, frame):
        self.assign(st[2], self.eval(st[3], frame, want_object=True), frame, is_set=True)

    def x_callstmt(self, st, frame):
        self.eval(st[2], frame, statement=True)

    def x_if(self, st, frame):
        for cond, body in st[2]:
            if to_bool(self.eval(cond, frame)):
                self.run_block(body, frame)
                return
        self.run_block(st[3], frame)

    def x_select(self, st, frame):
        subject = self.eval(st[2], frame)
        for tests, body in st[3]:
            for t in tests:
                if t[0] == "eq" and vb_compare(subject, self.eval(t[1], frame)) == 0:
                    break
                if t[0] == "range" and vb_compare(subject, self.eval(t[1], frame)) >= 0 \
                        and vb_compare(subject, self.eval(t[2], frame)) <= 0:
                    break
                if t[0] == "is":
                    c = vb_compare(subject, self.eval(t[2], frame))
                    if {"=": c == 0, "<>": c != 0, "<": c < 0, ">": c > 0, "<=": c <= 0, ">=": c >= 0}[t[1]]:
                        break
            else:
                continue
            self.run_block(body, frame)
            return
        self.run_block(st[4], frame)

    def x_for(self, st, frame):
        _, line, var, start, stop, step, body = st
        cell = self.lookup_cell(var, frame, create=True)
        cell.value = self.eval(start, frame)
        end = to_num(self.eval(stop, frame))
        inc = to_num(self.eval(step, frame)) if step is not None else 1
        try:
            while (to_num(cell.value) <= end) if inc >= 0 else (to_num(cell.value) >= end):
                self.run_block(body, frame)
                cell.value = to_num(cell.value) + inc
                frame.line = line
        except _Exit as e:
            if e.what != "for":
                raise

    def x_foreach(self, st, frame):
        _, line, var, coll, body = st
        cell = self.lookup_cell(var, frame, create=True)
        c = self.eval(coll, frame, want_object=True)
        if isinstance(c, VBArray):
            items = c.items()
        elif isinstance(c, Collection):
            items = list(c.items)
        elif hasattr(c, "vb_items"):
            items = c.vb_items()
        else:
            raise err(13, "For Each needs an array or a collection")
        try:
            for item in items:
                cell.value = item
                self.run_block(body, frame)
        except _Exit as e:
            if e.what != "for":
                raise

    def x_do(self, st, frame):
        _, line, pre, post, body = st

        def check(c):
            if c is None:
                return True
            v = to_bool(self.eval(c[1], frame))
            return v if c[0] == "while" else not v
        try:
            while check(pre):
                self.run_block(body, frame)
                frame.line = line
                if not check(post):
                    break
                if self.host is not None:
                    self.host.tick()
        except _Exit as e:
            if e.what not in ("do", "while"):
                raise

    def x_with(self, st, frame):
        frame.with_stack.append(self.eval(st[2], frame, want_object=True))
        try:
            self.run_block(st[3], frame)
        finally:
            frame.with_stack.pop()

    def x_exit(self, st, frame):
        raise _Exit(st[2])

    def x_end(self, st, frame):
        raise EndProgram()

    def x_stop(self, st, frame):
        if self.host is not None:
            self.host.stop_statement(frame)

    def x_goto(self, st, frame):
        raise _Goto(st[2])

    def x_gosub(self, st, frame):
        raise err(0, "GoSub is not supported")

    def x_return(self, st, frame):
        raise err(0, "Return (GoSub) is not supported")

    def x_onerror(self, st, frame):
        frame.on_error = st[2]
        frame.on_error_label = st[2]
        if st[2] == "0":
            self.err.number, self.err.description = 0, ""

    def x_resume(self, st, frame):
        self.err.number, self.err.description = 0, ""
        frame.on_error = getattr(frame, "on_error_label", "0")
        raise _Resume(st[2])

    def x_debugprint(self, st, frame):
        _, line, what, args, seps = st
        if what not in ("print", "assert"):
            if what == "assert" and args and not to_bool(self.eval(args[0], frame)):
                self.host and self.host.stop_statement(frame)
            return
        parts = [to_str(self.eval(a, frame)) for a in args]
        sep = "\t" if seps and seps[0] == "," else ""
        self.output(sep.join(parts))

    def x_unload(self, st, frame):
        obj = self.eval(st[2], frame, want_object=True)
        if hasattr(obj, "vb_call"):
            obj.vb_call("unload", [])

    def x_loadform(self, st, frame):
        obj = self.eval(st[2], frame, want_object=True)
        if hasattr(obj, "vb_call"):
            obj.vb_call("load", [])

    # ------------------------------------------------------------ variables
    def lookup_cell(self, name: str, frame: Frame, create=False):
        if name in frame.locals:
            return frame.locals[name]
        if name in frame.module.vars:
            return frame.module.vars[name]
        if name in self.globals:
            return self.globals[name]
        for st in self.modules.values():           # Public variables of other modules
            if name in st.public:
                return st.vars[name]
        if create:
            cell = Cell(EMPTY)
            (frame.locals if frame.proc else frame.module.vars)[name] = cell
            return cell
        return None

    def assign(self, target, value, frame, is_set=False):
        kind = target[0]
        if kind == "name":
            name = target[2]
            cell = self.lookup_cell(name, frame)
            if cell is None:
                obj = self._resolve_object(name, frame)
                if obj is not None and hasattr(obj, "vb_set"):    # Text1 = "x"  (default property)
                    obj.vb_set(getattr(obj, "vb_default", "text"), value)
                    return
                cell = self.lookup_cell(name, frame, create=True)
            if not is_set and hasattr(cell.value, "vb_set") and not hasattr(value, "vb_get") \
                    and getattr(cell.value, "vb_default", None) and not isinstance(cell.value, (Collection, UDT)):
                cell.value.vb_set(cell.value.vb_default, value)
                return
            cell.value = coerce(value, cell.typ) if not is_set else value
            return
        if kind == "member":
            obj = self.eval(target[2], frame, want_object=True)
            if not hasattr(obj, "vb_set"):
                raise err(424, f"Object required to set '{target[4]}'")
            obj.vb_set(target[3], value)
            return
        if kind == "call":
            base = target[2]
            args = [self.eval(a, frame) for a in target[3]]
            if base[0] == "name":
                cell = self.lookup_cell(base[2], frame)
                if cell is not None and isinstance(cell.value, VBArray):
                    cell.value.set(args, value)
                    return
                if base[2] == "mid" and len(target[3]) >= 2:     # Mid(s, i, n) = "x"
                    var = target[3][0]
                    s = to_str(self.eval(var, frame))
                    start = int(to_num(args[1])) - 1
                    n = int(to_num(args[2])) if len(args) > 2 else len(to_str(value))
                    rep = to_str(value)[:n]
                    self.assign(var, s[:start] + rep + s[start + len(rep):], frame)
                    return
                obj = self._resolve_object(base[2], frame)
                if obj is not None and hasattr(obj, "vb_setitem"):
                    obj.vb_setitem(args, value)
                    return
            obj = self.eval(base, frame, want_object=True)
            if isinstance(obj, VBArray):
                obj.set(args, value)
                return
            if hasattr(obj, "vb_setitem"):
                obj.vb_setitem(args, value)
                return
            if base[0] == "member":                     # obj.List(i) = "x"
                parent = self.eval(base[2], frame, want_object=True)
                if hasattr(parent, "vb_setindexed"):
                    parent.vb_setindexed(base[3], args, value)
                    return
            raise err(13, "Cannot assign to this expression")
        raise err(0, "invalid assignment target")

    def _resolve_object(self, name, frame):
        me = frame.me or (self.stack[-1].me if self.stack else None)
        if me is not None and hasattr(me, "vb_has") and me.vb_has(name):
            return me.vb_get(name)
        return self.objects.get(name)

    # ------------------------------------------------------------ expressions
    def eval(self, e, frame: Frame, want_object=False, statement=False):
        if e is None:
            return EMPTY
        k = e[0]
        if k == "num":
            return e[2]
        if k == "str":
            return e[2]
        if k == "bool":
            return e[2]
        if k == "date":
            return to_date(e[2])
        if k == "nothing":
            return NOTHING
        if k == "empty":
            return EMPTY
        if k == "missing":
            return _MISSING
        if k == "paren":
            return self.eval(e[2], frame)
        if k == "me":
            me = frame.me
            if me is None:
                raise err(91, "Me is only valid inside a form")
            return me
        if k == "new":
            return self._instantiate(e[2])
        if k == "withobj":
            if not frame.with_stack:
                raise err(91, "'.' used outside a With block")
            return frame.with_stack[-1]
        if k == "name":
            return self._eval_name(e, frame, want_object)
        if k == "member":
            obj = self.eval(e[2], frame, want_object=True)
            if obj is NOTHING or obj is EMPTY:
                raise err(91, f"Object variable not set (using .{e[4]})")
            if isinstance(obj, UDT) or hasattr(obj, "vb_get"):
                try:
                    v = obj.vb_get(e[3])
                except VBRuntimeError:
                    if hasattr(obj, "vb_call") and statement:
                        return obj.vb_call(e[3], [])
                    raise
                return v
            raise err(424, f"Object required (.{e[4]})")
        if k == "call":
            return self._eval_call(e, frame, statement)
        if k == "unop":
            v = self.eval(e[3], frame)
            if e[2] == "-":
                return -to_num(v)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                return not to_bool(v)
            return ~int(to_num(v))
        if k == "binop":
            return self._binop(e, frame)
        if k == "typeof":
            obj = self.eval(e[2], frame, want_object=True)
            return getattr(obj, "vb_typename", type(obj).__name__).lower() == e[3]
        raise err(0, f"expression '{k}' is not supported")

    def _eval_name(self, e, frame, want_object):
        name = e[2]
        cell = self.lookup_cell(name, frame)
        if cell is not None:
            return cell.value
        if name in frame.module.consts:
            return frame.module.consts[name]
        if name in CONSTANTS:
            return CONSTANTS[name]
        obj = self._resolve_object(name, frame)
        if obj is not None:
            return obj
        if name == "err":
            return self.err
        found = self.find_proc(name, frame)
        if found is not None:                          # call without parentheses: x = MyFunc
            return self.call_proc(found[0], found[1], [], me=frame.me)
        if name in self.builtins:
            return self.builtins[name]()
        if self.host is not None:
            obj = self.host.global_object(name)
            if obj is not None:
                return obj
        raise err(0, f"Variable not defined: '{e[3] if len(e) > 3 else name}'")

    def _args(self, nodes, frame):
        vals, cells = [], []
        for a in nodes:
            if a[0] == "missing":
                vals.append(_MISSING)
                cells.append(None)
            elif a[0] == "name":
                cell = self.lookup_cell(a[2], frame)
                vals.append(cell.value if cell is not None else self.eval(a, frame))
                cells.append(cell)
            elif a[0] == "named":
                vals.append(self.eval(a[3], frame))
                cells.append(None)
            else:
                vals.append(self.eval(a, frame))
                cells.append(None)
        return vals, cells

    def _eval_call(self, e, frame, statement):
        target, arg_nodes = e[2], e[3]
        if target[0] == "name":
            name = target[2]
            cell = self.lookup_cell(name, frame)
            # inside Function F, "F(args)" is a recursive call (bare "F" is the return value)
            if cell is not None and arg_nodes and frame.proc is not None \
                    and frame.proc.name.split(":")[-1] == name and not isinstance(cell.value, VBArray):
                cell = None
            if cell is not None:
                v = cell.value
                args, _ = self._args(arg_nodes, frame)
                if isinstance(v, VBArray):
                    return v.get(args)
                if hasattr(v, "vb_call") and getattr(v, "vb_default", None):
                    return v.vb_call(v.vb_default, args)
                if not arg_nodes:
                    return v
                raise err(13, f"'{name}' is not an array")
            found = self.find_proc(name, frame)
            if found is not None:
                args, cells = self._args(arg_nodes, frame)
                return self.call_proc(found[0], found[1], args, cells, me=frame.me)
            obj = self._resolve_object(name, frame)
            if obj is not None:                       # control array:  Text1(0)
                args, _ = self._args(arg_nodes, frame)
                if hasattr(obj, "vb_index"):
                    return obj.vb_index(args)
                if hasattr(obj, "vb_call") and getattr(obj, "vb_default", None):
                    return obj.vb_call(obj.vb_default, args)
            if name in self.builtins:
                args, _ = self._args(arg_nodes, frame)
                args = [EMPTY if a is _MISSING else a for a in args]
                try:
                    return self.builtins[name](*args)
                except TypeError as ex:
                    raise err(450, f"Wrong number of arguments for {name}: {ex}") from None
                except (ValueError, ZeroDivisionError, OverflowError, IndexError) as ex:
                    raise err(5, f"Invalid procedure call or argument ({name}): {ex}") from None
            if self.host is not None:
                obj = self.host.global_object(name)
                if obj is not None and arg_nodes:
                    args, _ = self._args(arg_nodes, frame)
                    if hasattr(obj, "vb_index"):
                        return obj.vb_index(args)
                elif obj is not None:
                    return obj
            raise err(35, f"Sub or Function not defined: '{target[3] if len(target) > 3 else name}'")
        if target[0] == "member":
            obj = self.eval(target[2], frame, want_object=True)
            args, cells = self._args(arg_nodes, frame)
            args = [EMPTY if a is _MISSING else a for a in args]
            if obj is NOTHING or obj is EMPTY:
                raise err(91, f"Object variable not set (calling .{target[4]})")
            if isinstance(obj, ModuleProxy):
                return obj.call(target[3], args, cells)
            if hasattr(obj, "vb_call"):
                return obj.vb_call(target[3], args)
            raise err(424, f"Object required (.{target[4]})")
        base = self.eval(target, frame, want_object=True)
        args, _ = self._args(arg_nodes, frame)
        if isinstance(base, VBArray):
            return base.get(args)
        if hasattr(base, "vb_call") and getattr(base, "vb_default", None):
            return base.vb_call(base.vb_default, args)
        raise err(13, "Type mismatch (not an array or function)")

    def _binop(self, e, frame):
        op = e[2]
        a = self.eval(e[3], frame, want_object=op == "is")
        b = self.eval(e[4], frame, want_object=op == "is")
        if op == "&":
            return to_str(a) + to_str(b)
        if op == "+":
            if isinstance(a, str) and isinstance(b, str):
                return a + b
            if isinstance(a, _dt.datetime) or isinstance(b, _dt.datetime):
                return to_date(to_num(a) + to_num(b))
            if isinstance(a, str) and not is_numeric_like(a) or isinstance(b, str) and not is_numeric_like(b):
                return to_str(a) + to_str(b)
            return to_num(a) + to_num(b)
        if op == "-":
            if isinstance(a, _dt.datetime) and isinstance(b, _dt.datetime):
                return to_num(a) - to_num(b)
            if isinstance(a, _dt.datetime):
                return to_date(to_num(a) - to_num(b))
            return to_num(a) - to_num(b)
        if op == "*":
            return to_num(a) * to_num(b)
        if op == "/":
            d = to_num(b)
            if d == 0:
                raise err(11, "Division by zero")
            r = to_num(a) / d
            return int(r) if isinstance(r, float) and r.is_integer() and abs(r) < 1e15 else r
        if op == "\\":
            d = vb_round(to_num(b))
            if d == 0:
                raise err(11, "Division by zero")
            return int(vb_round(to_num(a)) / d)
        if op == "mod":
            d = vb_round(to_num(b))
            if d == 0:
                raise err(11, "Division by zero")
            x = vb_round(to_num(a))
            return int(math.fmod(x, d))
        if op == "^":
            r = to_num(a) ** to_num(b)
            return int(r) if isinstance(r, float) and r.is_integer() and abs(r) < 1e15 else r
        if op in ("=", "<>", "<", ">", "<=", ">="):
            c = vb_compare(a, b)
            return {"=": c == 0, "<>": c != 0, "<": c < 0, ">": c > 0, "<=": c <= 0, ">=": c >= 0}[op]
        if op == "like":
            return vb_like(to_str(a), to_str(b))
        if op == "is":
            return a is b
        if op in ("and", "or", "xor", "eqv", "imp"):
            if isinstance(a, bool) and isinstance(b, bool):
                return {"and": a and b, "or": a or b, "xor": a != b, "eqv": a == b, "imp": (not a) or b}[op]
            x, y = int(to_num(a)), int(to_num(b))
            return {"and": x & y, "or": x | y, "xor": x ^ y, "eqv": ~(x ^ y), "imp": (~x) | y}[op]
        raise err(0, f"operator {op} is not supported")

    # ------------------------------------------------------------ debugger helpers
    def evaluate_text(self, text: str, frame: Frame):
        return self.eval(parse_expression(text), frame)

    def frame_variables(self, frame: Frame) -> list[tuple[str, str, str]]:
        out = []
        for name, cell in frame.locals.items():
            out.append((name, _typename(cell.value), _repr(cell.value)))
        for name, cell in frame.module.vars.items():
            out.append((f"{frame.module.name}.{name}", _typename(cell.value), _repr(cell.value)))
        return out


def _repr(v):
    if isinstance(v, str):
        return '"' + v.replace("\n", "\\n")[:200] + '"'
    if isinstance(v, VBArray):
        return f"Array({', '.join(_repr(x) for x in v.items()[:20])}{', ...' if len(v.items()) > 20 else ''})"
    if isinstance(v, Collection):
        return f"Collection ({len(v.items)} items)"
    if isinstance(v, UDT):
        return "{" + ", ".join(f"{k}: {_repr(x)}" for k, x in v._fields.items()) + "}"
    if hasattr(v, "vb_typename"):
        return getattr(v, "vb_name", v.vb_typename)
    return to_str(v)


class _Missing:
    def __repr__(self):
        return "<missing>"


_MISSING = _Missing()


class ModuleProxy:
    """Module1.SomeSub / Module1.Var access."""

    def __init__(self, interp: Interpreter, st: ModuleState):
        self.interp, self.st = interp, st
        self.vb_typename = "Module"

    def vb_get(self, name):
        if name in self.st.vars:
            return self.st.vars[name].value
        if name in self.st.mod.procs:
            return self.interp.call_proc(self.st, self.st.mod.procs[name], [])
        raise err(438, f"'{name}' is not a member of {self.st.name}")

    def vb_set(self, name, value):
        if name in self.st.vars:
            self.st.vars[name].value = value
            return
        raise err(438, f"'{name}' is not a member of {self.st.name}")

    def call(self, name, args, cells=None):
        if name in self.st.mod.procs:
            return self.interp.call_proc(self.st, self.st.mod.procs[name], args, cells)
        return self.vb_get(name)

    def vb_call(self, name, args):
        return self.call(name, args)
