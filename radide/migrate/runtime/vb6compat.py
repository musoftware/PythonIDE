"""VB6 compatibility helpers for programs migrated from Visual Basic 6 by RAD IDE.

Copied into the migrated project (it does not need the IDE).  The translated code uses plain Python and
the toolkit's own API wherever the meaning is the same, and these helpers where VB6 behaves differently
from Python: Val/CStr/CInt (VB conversions and banker's rounding), MsgBox/InputBox (return codes),
Mid/InStr (1-based), Open/Print #/Line Input # (file channels), Collection (1-based), Err, App, and a
few generic control helpers (vb_get / vb_set / vb_call) used for control arrays.

Works with both Tkinter and PySide6 (detected at call time).
"""
from __future__ import annotations

import datetime as _dt
import glob as _glob
import math as _math
import os as _os
import random as _random
import shutil as _shutil
import subprocess as _subprocess
import sys as _sys

try:
    import vb6format as _vbformat
except ImportError:                       # pragma: no cover - vb6format.py ships next to this file
    _vbformat = None

# ----------------------------------------------------------------------------- constants
vbCrLf = vbNewLine = "\n"          # Tk / Qt widgets show "\n" as a line break (VB6 used CR LF)
vbCr, vbLf, vbTab, vbNullString, vbNullChar, vbBack = "\r", "\n", "\t", "", "\0", "\b"
vbOKOnly, vbOKCancel, vbAbortRetryIgnore, vbYesNoCancel, vbYesNo, vbRetryCancel = 0, 1, 2, 3, 4, 5
vbCritical, vbQuestion, vbExclamation, vbInformation = 16, 32, 48, 64
vbDefaultButton1, vbDefaultButton2, vbDefaultButton3 = 0, 256, 512
vbOK, vbCancel, vbAbort, vbRetry, vbIgnore, vbYes, vbNo = 1, 2, 3, 4, 5, 6, 7
vbBlack, vbRed, vbGreen, vbYellow = 0x0, 0xFF, 0xFF00, 0xFFFF
vbBlue, vbMagenta, vbCyan, vbWhite = 0xFF0000, 0xFF00FF, 0xFFFF00, 0xFFFFFF
vbUnchecked, vbChecked, vbGrayed = 0, 1, 2
vbModal, vbModeless = 1, 0
vbBinaryCompare, vbTextCompare = 0, 1
vbKeyReturn, vbKeyEscape, vbKeyBack, vbKeyTab, vbKeySpace, vbKeyDelete = 13, 27, 8, 9, 32, 46
vbKeyLeft, vbKeyUp, vbKeyRight, vbKeyDown = 37, 38, 39, 40
vbUpperCase, vbLowerCase, vbProperCase = 1, 2, 3
vbSunday, vbMonday = 1, 2
vbString, vbInteger, vbLong, vbDouble = 8, 2, 3, 5
True_, False_ = True, False


def _qt() -> bool:
    return "PySide6" in _sys.modules and "tkinter" not in _sys.modules or \
        ("PySide6" in _sys.modules and _qt_app() is not None)


def _qt_app():
    try:
        from PySide6.QtWidgets import QApplication
        return QApplication.instance()
    except Exception:  # noqa: BLE001
        return None


# ----------------------------------------------------------------------------- conversions
def CStr(v) -> str:
    """VB6 CStr: True -> "True", 3.0 -> "3", None (Empty) -> ""."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, float):
        if v.is_integer() and abs(v) < 1e15:
            return str(int(v))
        return format(v, ".15g")
    if isinstance(v, _dt.datetime):
        return _vbformat.general_date(v) if _vbformat else str(v)
    return str(v)


def Str(v) -> str:
    s = CStr(v)
    return s if s.startswith("-") or not _is_number(v) else " " + s


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def Val(s):
    """VB6 Val: the number at the start of the text ("12abc" -> 12, "" -> 0); never raises."""
    if _is_number(s):
        return s
    if isinstance(s, bool):
        return -1 if s else 0
    t = str(s or "").replace(" ", "").replace("\t", "")
    if t[:2].lower() == "&h":
        h = ""
        for ch in t[2:]:
            if ch in "0123456789abcdefABCDEF":
                h += ch
            else:
                break
        return int(h, 16) if h else 0
    num, seen_dot, seen_e = "", False, False
    for i, ch in enumerate(t):
        if ch.isdigit():
            num += ch
        elif ch in "+-" and (i == 0 or (num and num[-1] in "eE")):
            num += ch
        elif ch == "." and not seen_dot and not seen_e:
            num += ch
            seen_dot = True
        elif ch in "eEdD" and num and not seen_e and num[-1].isdigit():
            num += "e"
            seen_e = True
        else:
            break
    while num and num[-1] in "+-eE.":
        num = num[:-1]
    if not num or num in "+-":
        return 0
    try:
        return float(num) if (seen_dot or seen_e) else int(num)
    except ValueError:
        return 0


def _num(v):
    if v is None or v == "":
        return 0
    if isinstance(v, bool):
        return -1 if v else 0
    if _is_number(v):
        return v
    s = str(v).strip()
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            raise VBError(13, "Type mismatch") from None


def CInt(v) -> int:
    """Banker's rounding like VB6 (2.5 -> 2, 3.5 -> 4)."""
    return int(round(_num(v)))


CLng = CByte = CInt


def CDbl(v) -> float:
    return float(_num(v))


CSng = CCur = CDec = CDbl


def CBool(v) -> bool:
    if isinstance(v, str):
        if v.strip().lower() in ("true", "false"):
            return v.strip().lower() == "true"
    return bool(_num(v))


def CVar(v):
    return v


def CDate(v):
    if isinstance(v, _dt.datetime):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y", "%H:%M:%S",
                "%H:%M", "%d %B %Y", "%B %d, %Y"):
        try:
            return _dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise VBError(13, "Type mismatch")


def Int(v):
    return int(_math.floor(_num(v)))


def Fix(v):
    return int(_math.trunc(_num(v)))


def Round(v, digits: int = 0):
    r = round(_num(v), int(digits))
    return int(r) if digits == 0 else r


def Sgn(v) -> int:
    v = _num(v)
    return (v > 0) - (v < 0)


def Sqr(v):
    return _math.sqrt(_num(v))


def Exp(v):
    return _math.exp(_num(v))


def Log(v):
    return _math.log(_num(v))


def Sin(v):
    return _math.sin(_num(v))


def Cos(v):
    return _math.cos(_num(v))


def Tan(v):
    return _math.tan(_num(v))


def Atn(v):
    return _math.atan(_num(v))


def Hex(v) -> str:
    return format(int(_num(v)) & 0xFFFFFFFF if _num(v) < 0 else int(_num(v)), "X")


def Oct(v) -> str:
    return format(int(_num(v)), "o")


def IsNumeric(v) -> bool:
    if _is_number(v):
        return True
    try:
        float(str(v).strip())
        return str(v).strip() != ""
    except ValueError:
        return False


def IsEmpty(v) -> bool:
    return v is None


def IsNull(v) -> bool:
    return v is None


def IsArray(v) -> bool:
    return isinstance(v, (list, tuple))


def IsDate(v) -> bool:
    try:
        CDate(v)
        return True
    except VBError:
        return False


def IIf(cond, a, b):
    return a if cond else b


def Choose(index, *options):
    i = int(_num(index))
    return options[i - 1] if 1 <= i <= len(options) else None


def RGB(r, g, b) -> int:
    return (int(r) & 255) + (int(g) & 255) * 256 + (int(b) & 255) * 65536


_QB = [0x000000, 0x800000, 0x008000, 0x808000, 0x000080, 0x800080, 0x008080, 0xC0C0C0, 0x808080, 0xFF0000,
       0x00FF00, 0xFFFF00, 0x0000FF, 0xFF00FF, 0x00FFFF, 0xFFFFFF]


def QBColor(i) -> int:
    c = _QB[int(i) & 15]          # table above is RRGGBB; VB colours are &HBBGGRR
    return ((c >> 16) & 255) + (c & 0xFF00) + ((c & 255) << 16)


def to_css(color) -> str:
    """A VB colour (int &HBBGGRR, or "#RRGGBB") as "#RRGGBB" for Tk / Qt."""
    if isinstance(color, str):
        return color
    n = int(color)
    if n & 0x80000000:             # system colour
        return "#F0F0F0"
    return f"#{n & 0xFF:02X}{(n >> 8) & 0xFF:02X}{(n >> 16) & 0xFF:02X}"


def from_css(text) -> int:
    t = str(text or "")
    if t.startswith("#") and len(t) >= 7:
        return int(t[1:3], 16) + int(t[3:5], 16) * 256 + int(t[5:7], 16) * 65536
    return 0


def px(twips) -> int:
    """Twips (VB6 default ScaleMode) -> pixels (96 dpi)."""
    return int(round(_num(twips) / 15))


def twips(pixels) -> int:
    return int(_num(pixels)) * 15


# ----------------------------------------------------------------------------- strings
def Len(v) -> int:
    return len(v) if isinstance(v, (list, tuple)) else len(CStr(v))


def Left(s, n) -> str:
    return CStr(s)[:max(0, int(n))]


def Right(s, n) -> str:
    n = int(n)
    return CStr(s)[-n:] if n > 0 else ""


def Mid(s, start, length=None) -> str:
    s, i = CStr(s), max(1, int(start)) - 1
    return s[i:] if length is None else s[i:i + max(0, int(length))]


def InStr(*a) -> int:
    """InStr([start,] text, find [, compare]) - 1-based, 0 when not found."""
    if a and _is_number(a[0]) and len(a) >= 3:
        start, s, find = int(a[0]), CStr(a[1]), CStr(a[2])
        compare = a[3] if len(a) > 3 else 0
    else:
        start, s, find = 1, CStr(a[0]), CStr(a[1])
        compare = a[2] if len(a) > 2 else 0
    if compare == vbTextCompare:
        s, find = s.lower(), find.lower()
    return s.find(find, max(0, start - 1)) + 1


def InStrRev(s, find, start=-1, compare=0) -> int:
    s, find = CStr(s), CStr(find)
    if compare == vbTextCompare:
        s, find = s.lower(), find.lower()
    end = len(s) if start in (-1, None) else int(start)
    return s.rfind(find, 0, end) + 1


def Replace(s, find, repl, start=1, count=-1, compare=0) -> str:
    s = CStr(s)[int(start) - 1:]
    if compare == vbTextCompare and find:
        import re
        return re.sub(re.escape(CStr(find)), lambda _m: CStr(repl), s, count=0 if count < 0 else count,
                      flags=re.I)
    return s.replace(CStr(find), CStr(repl), -1 if count is None else count)


def Split(s, delim=" ", limit=-1, compare=0) -> list:
    s = CStr(s)
    if s == "":
        return []
    return s.split(delim, -1 if limit is None or limit < 0 else limit - 1)


def Join(items, delim=" ") -> str:
    return CStr(delim).join(CStr(x) for x in items)


def UCase(s) -> str:
    return CStr(s).upper()


def LCase(s) -> str:
    return CStr(s).lower()


def Trim(s) -> str:
    return CStr(s).strip(" ")


def LTrim(s) -> str:
    return CStr(s).lstrip(" ")


def RTrim(s) -> str:
    return CStr(s).rstrip(" ")


def Space(n) -> str:
    return " " * max(0, int(n))


def String(n, ch) -> str:
    c = chr(ch) if _is_number(ch) else CStr(ch)[:1]
    return c * max(0, int(n))


def StrReverse(s) -> str:
    return CStr(s)[::-1]


def StrComp(a, b, compare=0) -> int:
    a, b = CStr(a), CStr(b)
    if compare == vbTextCompare:
        a, b = a.lower(), b.lower()
    return (a > b) - (a < b)


def StrConv(s, mode) -> str:
    s = CStr(s)
    return s.upper() if mode == vbUpperCase else s.lower() if mode == vbLowerCase else s.title()


def Chr(n) -> str:
    return chr(int(n))


ChrW = Chr


def Asc(s) -> int:
    s = CStr(s)
    if not s:
        raise VBError(5, "Invalid procedure call or argument")
    return ord(s[0])


AscW = Asc


def Format(value, fmt="") -> str:
    if _vbformat is None:
        return CStr(value)
    return _vbformat.vb_format(value, fmt, CStr, _num, CDate)


def FormatNumber(value, digits=2) -> str:
    return f"{_num(value):,.{int(digits)}f}"


def FormatCurrency(value, digits=2) -> str:
    return "$" + FormatNumber(value, digits)


def Like(s, pattern) -> bool:
    import fnmatch
    return fnmatch.fnmatchcase(CStr(s), CStr(pattern).replace("#", "[0-9]"))


# ----------------------------------------------------------------------------- arrays
def Array(*items) -> list:
    return list(items)


def UBound(a, dim=1) -> int:
    for _ in range(int(dim) - 1):
        a = a[0]
    return len(a) - 1


def LBound(_a, _dim=1) -> int:
    return 0


def dim_array(default, *uppers):
    """Dim a(10) / a(3, 4): VB upper bounds are inclusive."""
    if not uppers:
        return []
    n = int(_num(uppers[0])) + 1
    if len(uppers) == 1:
        return [default for _ in range(n)]
    return [dim_array(default, *uppers[1:]) for _ in range(n)]


def redim(old, default, *uppers, preserve=False):
    new = dim_array(default, *uppers)
    if preserve and old:
        for i in range(min(len(old), len(new))):
            new[i] = old[i]
    return new


def vb_for(start, stop, step=1):
    """For i = start To stop Step step (non-integer steps)."""
    i = start
    if step == 0:
        raise VBError(5, "Step 0")
    while (i <= stop) if step > 0 else (i >= stop):
        yield i
        i += step


class Collection:
    """VB6 Collection (1-based; optional string keys)."""

    def __init__(self):
        self._items: list = []
        self._keys: list = []

    def Add(self, item, key=None, before=None, after=None):
        k = None if key is None else str(key).lower()
        if k is not None and k in self._keys:
            raise VBError(457, "This key is already associated with an element of this collection")
        pos = len(self._items)
        if before is not None:
            pos = self._index(before)
        elif after is not None:
            pos = self._index(after) + 1
        self._items.insert(pos, item)
        self._keys.insert(pos, k)

    def _index(self, key) -> int:
        if isinstance(key, str):
            try:
                return self._keys.index(key.lower())
            except ValueError:
                raise VBError(5, "Invalid procedure call or argument") from None
        i = int(key) - 1
        if not 0 <= i < len(self._items):
            raise VBError(9, "Subscript out of range")
        return i

    def Item(self, key):
        return self._items[self._index(key)]

    __call__ = Item

    def Remove(self, key):
        i = self._index(key)
        del self._items[i]
        del self._keys[i]

    @property
    def Count(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(list(self._items))

    def __len__(self):
        return len(self._items)


# ----------------------------------------------------------------------------- errors
class VBError(Exception):
    def __init__(self, number=0, description="", source=""):
        super().__init__(description or f"Error {number}")
        self.number, self.description, self.source = number, description, source


_ERRNO = {ZeroDivisionError: (11, "Division by zero"), FileNotFoundError: (53, "File not found"),
          PermissionError: (70, "Permission denied"), IndexError: (9, "Subscript out of range"),
          KeyError: (5, "Invalid procedure call or argument"), OverflowError: (6, "Overflow"),
          ValueError: (13, "Type mismatch"), TypeError: (13, "Type mismatch"),
          AttributeError: (438, "Object doesn't support this property or method"), OSError: (75, "Path/File access error")}


class _Err:
    Number = 0
    Description = ""
    Source = ""

    def set(self, exc: BaseException) -> None:
        if isinstance(exc, VBError):
            self.Number, self.Description, self.Source = exc.number, exc.description or str(exc), exc.source
            return
        for cls, (n, d) in _ERRNO.items():
            if isinstance(exc, cls):
                self.Number, self.Description = n, d
                break
        else:
            self.Number, self.Description = 1000, str(exc)
        self.Source = type(exc).__name__

    def Clear(self) -> None:
        self.Number, self.Description, self.Source = 0, "", ""

    def Raise(self, number, source="", description=""):
        raise VBError(int(number), str(description), str(source))


Err = _Err()


# ----------------------------------------------------------------------------- dialogs
def MsgBox(prompt="", buttons=0, title="") -> int:
    """Shows a message box; returns vbOK / vbYes / vbNo / vbCancel / vbRetry like VB6."""
    prompt, title = CStr(prompt), CStr(title) or App.Title
    kind = int(buttons) & 7
    icon = int(buttons) & 0x70
    if _qt_app() is not None:
        from PySide6.QtWidgets import QMessageBox as Q
        B = Q.StandardButton
        btns = {0: B.Ok, 1: B.Ok | B.Cancel, 2: B.Abort | B.Retry | B.Ignore, 3: B.Yes | B.No | B.Cancel,
                4: B.Yes | B.No, 5: B.Retry | B.Cancel}.get(kind, B.Ok)
        fn = {16: Q.critical, 32: Q.question, 48: Q.warning}.get(icon, Q.information)
        r = fn(None, title, prompt, btns)
        return {B.Ok: vbOK, B.Cancel: vbCancel, B.Abort: vbAbort, B.Retry: vbRetry, B.Ignore: vbIgnore,
                B.Yes: vbYes, B.No: vbNo}.get(r, vbOK)
    from tkinter import messagebox as m
    ic = {16: "error", 32: "question", 48: "warning"}.get(icon, "info")
    if kind == 0:
        {"error": m.showerror, "warning": m.showwarning}.get(ic, m.showinfo)(title, prompt)
        return vbOK
    if kind == 1:
        return vbOK if m.askokcancel(title, prompt, icon=ic) else vbCancel
    if kind == 3:
        r = m.askyesnocancel(title, prompt, icon=ic)
        return vbCancel if r is None else vbYes if r else vbNo
    if kind == 4:
        return vbYes if m.askyesno(title, prompt, icon=ic) else vbNo
    if kind in (2, 5):
        return vbRetry if m.askretrycancel(title, prompt, icon=ic) else vbCancel
    m.showinfo(title, prompt)
    return vbOK


def InputBox(prompt="", title="", default="") -> str:
    """Returns the typed text, or "" when the user cancels (like VB6)."""
    prompt, title = CStr(prompt), CStr(title) or App.Title
    if _qt_app() is not None:
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(None, title, prompt, text=CStr(default))
        return text if ok else ""
    from tkinter import simpledialog
    r = simpledialog.askstring(title, prompt, initialvalue=CStr(default))
    return r if r is not None else ""


def DoEvents() -> None:
    app = _qt_app()
    if app is not None:
        app.processEvents()
        return
    try:
        import tkinter
        root = tkinter._default_root
        if root is not None:
            root.update()
    except Exception:  # noqa: BLE001
        pass


def Beep() -> None:
    app = _qt_app()
    if app is not None:
        app.beep()
        return
    try:
        import tkinter
        if tkinter._default_root is not None:
            tkinter._default_root.bell()
    except Exception:  # noqa: BLE001
        print("\a", end="")


def End() -> None:
    """VB6 End: stops the program."""
    app = _qt_app()
    if app is not None:
        app.quit()
        return
    raise SystemExit(0)


def Shell(path, _style=1) -> int:
    return _subprocess.Popen(str(path), shell=True).pid


# ----------------------------------------------------------------------------- date / time
def Now():
    return _dt.datetime.now().replace(microsecond=0)


def Date():
    return _dt.datetime.combine(_dt.date.today(), _dt.time())


def Time():
    t = _dt.datetime.now().time().replace(microsecond=0)
    return _dt.datetime.combine(_dt.date(1899, 12, 30), t)


def Timer() -> float:
    n = _dt.datetime.now()
    return n.hour * 3600 + n.minute * 60 + n.second + n.microsecond / 1e6


def Year(d):
    return CDate(d).year


def Month(d):
    return CDate(d).month


def Day(d):
    return CDate(d).day


def Hour(d):
    return CDate(d).hour


def Minute(d):
    return CDate(d).minute


def Second(d):
    return CDate(d).second


def Weekday(d, first=1):
    return (CDate(d).isoweekday() % 7 - (int(first) - 1)) % 7 + 1


def DateSerial(y, m, d):
    return _dt.datetime(int(y), 1, 1) + _dt.timedelta(days=0) if False else \
        _dt.datetime(int(y) + (int(m) - 1) // 12, (int(m) - 1) % 12 + 1, 1) + _dt.timedelta(days=int(d) - 1)


def TimeSerial(h, m, s):
    return _dt.datetime(1899, 12, 30) + _dt.timedelta(hours=int(h), minutes=int(m), seconds=int(s))


_IV = {"d": "days", "y": "days", "w": "days", "ww": "weeks", "h": "hours", "n": "minutes", "s": "seconds"}


def DateAdd(interval, n, d):
    d, iv, n = CDate(d), str(interval).lower(), int(_num(n))
    if iv in ("yyyy", "q", "m"):
        months = n * (12 if iv == "yyyy" else 3 if iv == "q" else 1)
        y, m = divmod(d.month - 1 + months, 12)
        import calendar
        day = min(d.day, calendar.monthrange(d.year + y, m + 1)[1])
        return d.replace(year=d.year + y, month=m + 1, day=day)
    return d + _dt.timedelta(**{_IV.get(iv, "days"): n})


def DateDiff(interval, a, b):
    a, b, iv = CDate(a), CDate(b), str(interval).lower()
    if iv == "yyyy":
        return b.year - a.year
    if iv == "m":
        return (b.year - a.year) * 12 + b.month - a.month
    secs = (b - a).total_seconds()
    div = {"d": 86400, "y": 86400, "w": 604800, "ww": 604800, "h": 3600, "n": 60, "s": 1}.get(iv, 86400)
    return int(secs // div)


# ----------------------------------------------------------------------------- files
class _App:
    @property
    def Path(self) -> str:
        main = _sys.modules.get("__main__")
        f = getattr(main, "__file__", None) or (_sys.argv[0] if _sys.argv and _sys.argv[0] else "")
        return _os.path.dirname(_os.path.abspath(f)) if f else _os.getcwd()

    @property
    def EXEName(self) -> str:
        main = _sys.modules.get("__main__")
        f = getattr(main, "__file__", None) or "app"
        return _os.path.splitext(_os.path.basename(f))[0]

    Title = "Project1"
    PrevInstance = False
    Major, Minor, Revision = 1, 0, 0


App = _App()


def Environ(name) -> str:
    return _os.environ.get(str(name), "")


def Command() -> str:
    return " ".join(_sys.argv[1:])


def CurDir(_drive="") -> str:
    return _os.getcwd()


def ChDir(path) -> None:
    _os.chdir(str(path))


def MkDir(path) -> None:
    _os.mkdir(str(path))


def RmDir(path) -> None:
    _os.rmdir(str(path))


def Kill(pattern) -> None:
    hits = _glob.glob(str(pattern))
    if not hits:
        raise VBError(53, "File not found")
    for f in hits:
        _os.remove(f)


def FileCopy(src, dst) -> None:
    _shutil.copyfile(str(src), str(dst))


def Name(old, new) -> None:
    _os.rename(str(old), str(new))


def FileLen(path) -> int:
    return _os.path.getsize(str(path))


_dir_state: list = []


def Dir(pattern=None, _attributes=0) -> str:
    """Dir("C:\\x\\*.txt") then Dir() for the next match; "" at the end."""
    global _dir_state
    if pattern is not None:
        p = str(pattern)
        if _os.path.isdir(p):
            p = _os.path.join(p, "*")
        _dir_state = sorted(_os.path.basename(f) for f in _glob.glob(p))
    return _dir_state.pop(0) if _dir_state else ""


class _Channel:
    def __init__(self, path, mode):
        self.path, self.mode = str(path), mode
        self.pos = 0
        if mode == "input":
            with open(self.path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
                self.data = f.read().replace("\r\n", "\n")
            self.f = None
        else:
            self.f = open(self.path, {"output": "w", "append": "a", "binary": "r+b", "random": "r+b"}.get(mode, "w"),
                          encoding=None if mode in ("binary", "random") else "utf-8",
                          newline=None if mode in ("binary", "random") else "\r\n")
            self.data = ""

    def eof(self) -> bool:
        return self.pos >= len(self.data) if self.mode == "input" else True

    def line(self) -> str:
        if self.eof():
            raise VBError(62, "Input past end of file")
        end = self.data.find("\n", self.pos)
        end = len(self.data) if end < 0 else end
        s = self.data[self.pos:end]
        self.pos = end + 1
        return s

    def field(self):
        d, i = self.data, self.pos
        while i < len(d) and d[i] in " \t":
            i += 1
        if i >= len(d):
            raise VBError(62, "Input past end of file")
        if d[i] == '"':
            j = d.find('"', i + 1)
            j = len(d) if j < 0 else j
            val = d[i + 1:j]
            i = j + 1
            while i < len(d) and d[i] not in ",\n":
                i += 1
        else:
            j = i
            while j < len(d) and d[j] not in ",\n":
                j += 1
            raw = d[i:j].strip()
            val = raw
            if raw.startswith("#") and raw.endswith("#"):
                val = raw.strip("#")
            elif IsNumeric(raw):
                val = Val(raw)
            elif raw.upper() in ("#TRUE#", "#FALSE#"):
                val = raw.upper() == "#TRUE#"
            i = j
        if i < len(d) and d[i] in ",\n":
            i += 1
        self.pos = i
        return val


_channels: dict = {}


def FreeFile() -> int:
    n = 1
    while n in _channels:
        n += 1
    return n


def FileOpen(number, path, mode="input") -> None:
    n = int(number)
    if n in _channels:
        raise VBError(55, "File already open")
    try:
        _channels[n] = _Channel(path, str(mode).lower())
    except FileNotFoundError:
        raise VBError(53, "File not found") from None


def _ch(number) -> _Channel:
    try:
        return _channels[int(number)]
    except KeyError:
        raise VBError(52, "Bad file name or number") from None


def FileClose(*numbers) -> None:
    for n in (numbers or list(_channels)):
        ch = _channels.pop(int(n), None)
        if ch is not None and ch.f is not None:
            ch.f.close()


Reset = FileClose


def _print_text(items) -> str:
    out = ""
    for value, sep in items:
        if value is not None:
            out += Str(value) if _is_number(value) else CStr(value)
        if sep == ",":
            out += " " * (14 - len(out) % 14)
    return out


def FilePrint(number, *items, newline=True) -> None:
    """Print #n, a; b, c  -> items as (value, separator) pairs; newline=False for a trailing ; or ,"""
    ch = _ch(number)
    ch.f.write(_print_text(items) + ("\n" if newline else ""))


def FileWrite(number, *values) -> None:
    """Write #n, a, b  -> "text",12,#TRUE#"""
    parts = []
    for v in values:
        if isinstance(v, bool):
            parts.append("#TRUE#" if v else "#FALSE#")
        elif _is_number(v):
            parts.append(CStr(v))
        elif v is None:
            parts.append("")
        else:
            parts.append('"' + CStr(v) + '"')
    _ch(number).f.write(",".join(parts) + "\n")


def LineInput(number) -> str:
    return _ch(number).line()


def FileInput(number):
    return _ch(number).field()


def EOF(number) -> bool:
    return _ch(number).eof()


def LOF(number) -> int:
    ch = _ch(number)
    return len(ch.data) if ch.mode == "input" else _os.path.getsize(ch.path)


# ----------------------------------------------------------------------------- controls (generic)
def _is_qt_widget(w) -> bool:
    return type(w).__module__.startswith("PySide6")


def vb_get(w, prop):
    """Read a VB6 property of a Tk or Qt widget (used for control arrays and rare properties)."""
    p = str(prop).lower()
    if hasattr(w, "SetCell") and hasattr(w, "Columns") and p in ("rows", "cols", "fixedrows", "fixedcols"):
        return {"rows": w.RowCount + 1, "cols": len(w.Columns), "fixedrows": 1, "fixedcols": 0}[p]
    if _is_qt_widget(w):
        cls = type(w).__name__
        if p in ("text", "caption"):
            if cls == "QPlainTextEdit":
                return w.toPlainText()
            if cls == "QComboBox":
                return w.currentText()
            if cls == "QGroupBox":
                return w.title()
            if cls == "QListWidget":
                it = w.currentItem()
                return it.text() if it else ""
            return w.text() if hasattr(w, "text") else ""
        if p == "value":
            if cls == "QCheckBox":
                return 1 if w.isChecked() else 0
            if cls == "QRadioButton":
                return w.isChecked()
            return w.value() if hasattr(w, "value") else 0
        if p == "enabled":
            return w.isEnabled()
        if p == "visible":
            return w.isVisible()
        if p in ("left", "top", "width", "height"):
            g = w.geometry()
            return {"left": g.x(), "top": g.y(), "width": g.width(), "height": g.height()}[p] * 15
        if p == "listcount":
            return w.count()
        if p == "listindex":
            return w.currentRow() if cls == "QListWidget" else w.currentIndex()
        if p == "tag":
            return getattr(w, "_vb_tag", "")
        if p == "interval":
            return w.interval()
        return getattr(w, prop)
    import tkinter as tk
    cls = w.winfo_class() if hasattr(w, "winfo_class") else type(w).__name__
    if p in ("text", "caption"):
        if cls == "Entry" or cls == "TCombobox":
            return w.get()
        if cls == "Text":
            return w.get("1.0", "end-1c")
        if cls == "Listbox":
            sel = w.curselection()
            return w.get(sel[0]) if sel else ""
        return w.cget("text")
    if p == "value":
        if cls in ("Checkbutton", "Radiobutton"):
            var = w.cget("variable")
            v = w.getvar(str(var)) if str(var) else 0
            if cls == "Radiobutton":
                return str(v) == str(w.cget("value"))
            return 1 if v in (1, True, "1") else 0
        if cls == "TProgressbar":
            return w["value"]
        return w.get() if hasattr(w, "get") else 0
    if p == "enabled":
        try:
            return str(w.cget("state")) != "disabled"
        except tk.TclError:
            return True
    if p == "visible":
        return bool(w.winfo_ismapped())
    if p in ("left", "top", "width", "height"):
        info = w.place_info()
        key = {"left": "x", "top": "y", "width": "width", "height": "height"}[p]
        return int(info.get(key, 0) or 0) * 15
    if p == "listcount":
        return w.size() if cls == "Listbox" else len(w.cget("values"))
    if p == "listindex":
        if cls == "Listbox":
            sel = w.curselection()
            return sel[0] if sel else -1
        return w.current()
    if p == "tag":
        return getattr(w, "_vb_tag", "")
    if p in ("backcolor", "forecolor"):
        return from_css(w.cget("bg" if p == "backcolor" else "fg"))
    return getattr(w, prop)


def vb_set(w, prop, value) -> None:
    """Set a VB6 property of a Tk or Qt widget (positions/sizes are in twips like VB6)."""
    p = str(prop).lower()
    if hasattr(w, "SetCell") and hasattr(w, "Columns") and p in ("rows", "cols", "fixedrows", "fixedcols",
                                                                 "formatstring", "colwidth"):
        if p == "cols":
            n = max(1, int(value))
            w.SetColumns((list(w.Columns) + [f"Column{i + 1}" for i in range(len(w.Columns), n)])[:n])
        elif p == "rows":
            want = max(0, int(value) - 1)
            while w.RowCount < want:
                w.AddRow()
            while w.RowCount > want:
                w.RemoveRow(w.RowCount - 1)
        elif p == "formatstring":
            heads = [h.lstrip("<^>").strip() for h in str(value).split(";")[0].split("|")]
            w.SetColumns(heads)
        return None
    if _is_qt_widget(w):
        cls = type(w).__name__
        if p in ("text", "caption"):
            v = CStr(value)
            if cls == "QPlainTextEdit":
                w.setPlainText(v)
            elif cls == "QComboBox":
                w.setCurrentText(v)
            elif cls == "QGroupBox":
                w.setTitle(v)
            elif hasattr(w, "setText"):
                w.setText(v)
        elif p == "value":
            if cls in ("QCheckBox", "QRadioButton"):
                w.setChecked(bool(value))
            elif hasattr(w, "setValue"):
                w.setValue(int(value))
        elif p == "enabled":
            w.setEnabled(bool(value))
        elif p == "visible":
            w.setVisible(bool(value))
        elif p in ("left", "top", "width", "height"):
            g = w.geometry()
            vals = {"left": g.x(), "top": g.y(), "width": g.width(), "height": g.height()}
            vals[p] = px(value)
            w.setGeometry(vals["left"], vals["top"], vals["width"], vals["height"])
        elif p in ("backcolor", "forecolor"):
            role = "background-color" if p == "backcolor" else "color"
            w.setStyleSheet(f"{role}: {to_css(value)};")
        elif p == "listindex":
            (w.setCurrentRow if cls == "QListWidget" else w.setCurrentIndex)(int(value))
        elif p == "tag":
            w._vb_tag = value
        elif p == "interval":
            w.setInterval(int(value))
        else:
            setattr(w, prop, value)
        return
    import tkinter as tk
    cls = w.winfo_class() if hasattr(w, "winfo_class") else type(w).__name__
    if p in ("text", "caption"):
        v = CStr(value)
        if cls == "Entry" or cls == "TCombobox":
            w.delete(0, "end")
            w.insert(0, v)
        elif cls == "Text":
            w.delete("1.0", "end")
            w.insert("1.0", v)
        else:
            w.config(text=v)
    elif p == "value":
        if cls in ("Checkbutton", "Radiobutton"):
            var = str(w.cget("variable"))
            if cls == "Radiobutton":
                if value:
                    w.setvar(var, w.cget("value"))
            else:
                w.setvar(var, bool(int(_num(value))))
        elif cls == "TProgressbar":
            w["value"] = value
        else:
            w.set(value)
    elif p == "enabled":
        try:
            w.config(state="normal" if value else "disabled")
        except tk.TclError:
            pass
    elif p == "visible":
        if value:
            info = getattr(w, "_vb_place", None)
            if info:
                w.place(**info)
        else:
            if w.winfo_manager() == "place":
                w._vb_place = {k: v for k, v in w.place_info().items() if k != "in"}
            w.place_forget()
    elif p in ("left", "top", "width", "height"):
        key = {"left": "x", "top": "y", "width": "width", "height": "height"}[p]
        w.place_configure(**{key: px(value)})
    elif p in ("backcolor", "forecolor"):
        w.config(**{"bg" if p == "backcolor" else "fg": to_css(value)})
    elif p == "listindex":
        if cls == "Listbox":
            w.selection_clear(0, "end")
            if int(value) >= 0:
                w.selection_set(int(value))
                w.see(int(value))
        else:
            w.current(int(value))
    elif p == "tag":
        w._vb_tag = value
    else:
        setattr(w, prop, value)


def _grid_call(w, m, args):
    if m == "textmatrix":
        r, c = int(args[0]), int(args[1])
        return (list(w.Columns)[c] if c < len(w.Columns) else "") if r == 0 else w.GetCell(r - 1, c)
    if m == "additem":
        cells = str(args[0]).split("	")
        w.AddRow(*cells)
        return None
    if m == "removeitem":
        w.RemoveRow(int(args[0]) - 1)
        return None
    if m == "clear":
        w.Clear()
        return None
    if m == "colwidth":
        return int(w.column(f"c{int(args[0])}", "width")) * 15
    raise AttributeError(m)


def vb_call(w, method, *args):
    """AddItem / RemoveItem / Clear / SetFocus / List(i) on a Tk or Qt widget."""
    m = str(method).lower()
    if hasattr(w, "SetCell") and hasattr(w, "Columns") and m in ("textmatrix", "additem", "removeitem", "clear",
                                                                 "colwidth"):
        return _grid_call(w, m, args)
    if _is_qt_widget(w):
        cls = type(w).__name__
        if m == "additem":
            if len(args) > 1 and hasattr(w, "insertItem"):
                return w.insertItem(int(args[1]), CStr(args[0]))
            return w.addItem(CStr(args[0]))
        if m == "removeitem":
            return w.takeItem(int(args[0])) if cls == "QListWidget" else w.removeItem(int(args[0]))
        if m == "clear":
            return w.clear()
        if m == "setfocus":
            return w.setFocus()
        if m == "list":
            return w.item(int(args[0])).text() if cls == "QListWidget" else w.itemText(int(args[0]))
        if m == "refresh":
            return w.update()
        return getattr(w, method)(*args)
    cls = w.winfo_class()
    if m == "additem":
        if cls == "Listbox":
            return w.insert("end" if len(args) < 2 else int(args[1]), CStr(args[0]))
        vals = list(w.cget("values"))
        vals.insert(len(vals) if len(args) < 2 else int(args[1]), CStr(args[0]))
        return w.config(values=vals)
    if m == "removeitem":
        if cls == "Listbox":
            return w.delete(int(args[0]))
        vals = list(w.cget("values"))
        del vals[int(args[0])]
        return w.config(values=vals)
    if m == "clear":
        if cls == "Listbox":
            return w.delete(0, "end")
        if cls == "Entry" or cls == "TCombobox":
            return w.delete(0, "end")
        if cls == "Text":
            return w.delete("1.0", "end")
        return w.config(values=())
    if m == "setfocus":
        return w.focus_set()
    if m == "list":
        return w.get(int(args[0])) if cls == "Listbox" else w.cget("values")[int(args[0])]
    if m == "refresh":
        return w.update_idletasks()
    return getattr(w, method)(*args)


# ----------------------------------------------------------------------------- random numbers
def Rnd(_n=None) -> float:
    return _random.random()


def Randomize(seed=None) -> None:
    _random.seed(seed)


# ----------------------------------------------------------------------------- databases / COM objects
def CreateObject(progid, _server=""):
    """ADODB.Connection / Recordset / Command and DAO.DBEngine from vbado.py (works with Access .mdb files
    without a 64-bit driver); Scripting.Dictionary; any other ProgID through pywin32."""
    p = str(progid).strip()
    if p.lower() == "scripting.dictionary":
        return {}
    try:
        import vbado as _vbado
        obj = _vbado.create(p, _os.path.dirname(_os.path.abspath(_sys.argv[0] or ".")))
        if obj is not None:
            return obj
    except ImportError:
        pass
    import win32com.client  # type: ignore  # pip install pywin32
    return win32com.client.Dispatch(p)


def OpenDatabase(name, options=None, read_only=None, connect=None):
    """DAO OpenDatabase (vbado.py)."""
    import vbado as _vbado
    return _vbado.open_database(name, options, read_only, connect,
                                base=_os.path.dirname(_os.path.abspath(_sys.argv[0] or ".")))


def _grid_cell_set(g, r, c, value):
    cols = list(g.Columns)
    while len(cols) <= c:
        cols.append(f"Column{len(cols) + 1}")
    if len(cols) != len(g.Columns):
        g.SetColumns(cols)
    if r == 0:
        cols[c] = str(value)
        g.Columns = cols
        g.heading(f"c{c}", text=cols[c])
        return
    while g.RowCount < r:
        g.AddRow()
    g.SetCell(r - 1, c, str(value))


def vb_setindexed(obj, member, args, value) -> None:
    """obj.Member(i) = value (rs.Fields(0) = x, li.SubItems(1) = x, Grid.TextMatrix(r, c) = x)."""
    m = str(member).lower()
    if hasattr(obj, "SetCell") and hasattr(obj, "Columns"):          # MSFlexGrid migrated to the grid widget
        if m == "textmatrix":
            return _grid_cell_set(obj, int(args[0]), int(args[1]), value)
        if m == "colwidth":
            try:
                obj.column(f"c{int(args[0])}", width=max(0, int(float(value) / 15)))
            except Exception:  # noqa: BLE001
                pass
            return None
        if m in ("colalignment", "rowheight", "coldata", "rowdata"):
            return None
    if hasattr(obj, "vb_setindexed"):
        return obj.vb_setindexed(str(member).lower(), list(args), value)
    target = getattr(obj, member)
    key = args[0] if len(args) == 1 else tuple(args)
    if hasattr(target, "__setitem__"):
        target[key] = value
        return None
    setter = getattr(obj, "Set" + member, None)
    if callable(setter):
        return setter(*args, value)
    raise TypeError(f"{member}(...) cannot be assigned")


try:                                       # adOpenStatic, adLockOptimistic, dbOpenDynaset ... (ADO / DAO)
    import vbado as _vbado_consts
    globals().update({k: v for k, v in _vbado_consts.CANONICAL_CONSTANTS.items() if k not in globals()})
except ImportError:
    pass
