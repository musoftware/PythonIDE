"""VB6 file I/O for the BASIC interpreter.

Statements (parsed by vbparse, executed through Interpreter.x_*): ``Open path For Input|Output|Append|
Binary|Random [Access ...] As #n [Len = reclen]``, ``Close [#n, ...]``, ``Reset``, ``Print #n, ...``
(``;`` / ``,`` print zones, ``Spc(n)``, ``Tab(n)``), ``Write #n, ...``, ``Input #n, a, b``,
``Line Input #n, s``, ``Get #n, [pos], var``, ``Put #n, [pos], var``, ``Seek #n, pos``, ``Name a As b``.
Functions: ``FreeFile EOF LOF Loc Seek Input(n, #f) Dir Kill MkDir RmDir ChDir ChDrive CurDir FileCopy
FileLen FileDateTime GetAttr SetAttr``.

Text files are written in the ANSI code page (like VB6: ``mbcs`` on Windows) and read as UTF-8 when
they are valid UTF-8 (BOM aware), otherwise ANSI. Binary/Random records use VB6's layouts
(Integer 2, Long 4, Single 4, Double 8, Byte 1, Boolean 2, Currency 8, Date 8, String * n = n bytes,
variable String = its bytes in Binary mode or a 2-byte length + bytes in Random mode, Variant = 2-byte
VarType + data, user-defined Types field by field).
"""
from __future__ import annotations

import datetime as _dt
import fnmatch
import os
import shutil
import struct
from pathlib import Path

ANSI = "mbcs" if os.name == "nt" else "latin-1"
ZONE = 14
VB_ATTR = {"normal": 0, "readonly": 1, "hidden": 2, "system": 4, "volume": 8, "directory": 16, "archive": 32}
_EPOCH = _dt.datetime(1899, 12, 30)


class Spc:
    def __init__(self, n):
        self.n = n


class Tab:
    def __init__(self, n=None):
        self.n = n


def _decode(data: bytes) -> str:
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode(ANSI, errors="replace")


class VBFile:
    def __init__(self, num: int, path: Path, mode: str, reclen: int | None):
        self.num, self.path, self.mode, self.reclen = num, path, mode, reclen or 128
        self.col = 0                       # current print column (0-based)
        self.text = ""
        self.pos = 0
        self.fh = None
        if mode == "input":
            self.text = _decode(path.read_bytes()).replace("\r\n", "\n").replace("\r", "\n")
        elif mode in ("output", "append"):
            self.fh = open(path, "wb" if mode == "output" else "ab")
        else:                              # binary / random
            if not path.exists():
                path.touch()
            self.fh = open(path, "r+b")

    def close(self):
        if self.fh is not None:
            self.fh.close()
            self.fh = None


class FileManager:
    """Open files of one interpreter (file numbers 1..511)."""

    def __init__(self, interp):
        self.it = interp
        self.files: dict[int, VBFile] = {}
        self._dir_iter: list[str] | None = None

    # ------------------------------------------------------------ helpers
    def _err(self, number, msg):
        from .vbinterp import err
        return err(number, msg)

    def _num(self, v) -> int:
        from .vbinterp import to_num
        return int(to_num(v))

    def _str(self, v) -> str:
        from .vbinterp import to_str
        return to_str(v)

    def get(self, num) -> VBFile:
        n = self._num(num)
        f = self.files.get(n)
        if f is None:
            raise self._err(52, "Bad file name or number")
        return f

    def _path(self, p) -> Path:
        return Path(self._str(p))

    # ------------------------------------------------------------ open / close
    def open(self, path, mode, num, reclen=None):
        n = self._num(num)
        if not 1 <= n <= 511:
            raise self._err(52, "Bad file name or number")
        if n in self.files:
            raise self._err(55, "File already open")
        p = self._path(path)
        mode = (mode or "random").lower()
        if mode not in ("input", "output", "append", "binary", "random"):
            raise self._err(54, "Bad file mode")
        if mode == "input" and not p.is_file():
            raise self._err(53, f"File not found: {p}")
        try:
            self.files[n] = VBFile(n, p, mode, self._num(reclen) if reclen is not None else None)
        except FileNotFoundError:
            raise self._err(76, f"Path not found: {p}") from None
        except PermissionError:
            raise self._err(75, f"Path/File access error: {p}") from None

    def close(self, nums=()):
        targets = [self._num(n) for n in nums] if nums else list(self.files)
        for n in targets:
            f = self.files.pop(n, None)
            if f is not None:
                f.close()

    def close_all(self):
        self.close()

    # ------------------------------------------------------------ text output
    def _write_text(self, f: VBFile, text: str):
        if f.mode not in ("output", "append"):
            raise self._err(54, "Bad file mode")
        f.fh.write(text.replace("\r\n", "\n").replace("\n", "\r\n").encode(ANSI, errors="replace"))
        nl = text.rfind("\n")
        f.col = len(text) - nl - 1 if nl >= 0 else f.col + len(text)

    @staticmethod
    def print_text(value, to_str) -> str:
        """VB's Print formatting: numbers get a leading space (sign) and a trailing space."""
        if isinstance(value, bool):
            return "True" if value else "False"
        if isinstance(value, (int, float)):
            s = to_str(value)
            return (s if s.startswith("-") else " " + s) + " "
        if value is None:
            return "Null"
        return to_str(value)

    def print_items(self, num, items, to_str):
        """items: list of (value | Spc | Tab | None, sep)."""
        f = self.get(num)
        out_newline = True
        if not items:
            self._write_text(f, "\n")
            return
        for value, sep in items:
            if isinstance(value, Spc):
                self._write_text(f, " " * max(0, self._num(value.n)))
            elif isinstance(value, Tab):
                if value.n is None:
                    self._write_text(f, " " * (ZONE - f.col % ZONE))
                else:
                    col = max(1, self._num(value.n)) - 1
                    if col < f.col:
                        self._write_text(f, "\n")
                    self._write_text(f, " " * (col - f.col))
            elif value is not None:
                self._write_text(f, self.print_text(value, to_str))
            if sep == ",":
                self._write_text(f, " " * (ZONE - f.col % ZONE))
            out_newline = sep == ""
        if out_newline:
            self._write_text(f, "\n")

    def write_items(self, num, values, trailing_sep: bool):
        from .vbinterp import EMPTY, to_str
        f = self.get(num)
        parts = []
        for v in values:
            if hasattr(v, "vb_get") and getattr(v, "vb_default", None):     # rs!Field -> its value
                v = v.vb_get(v.vb_default)
            if isinstance(v, bool):
                parts.append("#TRUE#" if v else "#FALSE#")
            elif isinstance(v, (int, float)):
                parts.append(to_str(v))
            elif isinstance(v, _dt.datetime):
                parts.append("#" + (v.strftime("%Y-%m-%d") if v.hour == v.minute == v.second == 0 and v.date() != _EPOCH.date()
                                    else v.strftime("%Y-%m-%d %H:%M:%S")) + "#")
            elif v is None:
                parts.append("#NULL#")
            elif v is EMPTY:
                parts.append("")
            else:
                parts.append('"' + to_str(v) + '"')
        self._write_text(f, ",".join(parts) + ("," if trailing_sep else "\n"))

    # ------------------------------------------------------------ text input
    def _need_input(self, f: VBFile):
        if f.mode == "binary":
            data = f.fh.read()
            f.mode = "binary-text"
            f.text = _decode(data).replace("\r\n", "\n")
            f.pos = 0
        if f.mode not in ("input", "binary-text"):
            raise self._err(54, "Bad file mode")

    def line_input(self, num) -> str:
        f = self.get(num)
        self._need_input(f)
        if f.pos >= len(f.text):
            raise self._err(62, "Input past end of file")
        end = f.text.find("\n", f.pos)
        end = len(f.text) if end < 0 else end
        out = f.text[f.pos:end]
        f.pos = end + 1
        return out

    def input_field(self, num):
        """Next field for Input #: returns (text, quoted)."""
        f = self.get(num)
        self._need_input(f)
        t = f.text
        while f.pos < len(t) and t[f.pos] in " \t\n":
            f.pos += 1
        if f.pos >= len(t):
            raise self._err(62, "Input past end of file")
        if t[f.pos] == '"':
            end = t.find('"', f.pos + 1)
            end = len(t) if end < 0 else end
            out = t[f.pos + 1:end]
            f.pos = end + 1
            while f.pos < len(t) and t[f.pos] in " \t":
                f.pos += 1
            if f.pos < len(t) and t[f.pos] in ",\n":
                f.pos += 1
            return out, True
        end = f.pos
        while end < len(t) and t[end] not in ",\n":
            end += 1
        out = t[f.pos:end].strip()
        f.pos = end + 1
        return out, False

    @staticmethod
    def field_value(text: str, quoted: bool):
        """Variant value of an Input # field."""
        if quoted:
            return text
        up = text.upper()
        if up == "#TRUE#":
            return True
        if up == "#FALSE#":
            return False
        if up == "#NULL#":
            return None
        if text.startswith("#") and text.endswith("#") and len(text) > 2:
            try:
                return _dt.datetime.fromisoformat(text[1:-1])
            except ValueError:
                return text
        if text == "":
            from .vbinterp import EMPTY
            return EMPTY
        try:
            f = float(text)
            return int(f) if f.is_integer() and "." not in text and "e" not in text.lower() else f
        except ValueError:
            return text

    def input_chars(self, n, num) -> str:
        f = self.get(num)
        n = self._num(n)
        if f.mode in ("binary", "random"):
            return f.fh.read(n).decode(ANSI, errors="replace")
        self._need_input(f)
        if f.pos + n > len(f.text):
            raise self._err(62, "Input past end of file")
        out = f.text[f.pos:f.pos + n]
        f.pos += n
        return out

    # ------------------------------------------------------------ status
    def eof(self, num) -> bool:
        f = self.get(num)
        if f.mode in ("input", "binary-text"):
            return f.pos >= len(f.text)
        if f.fh is None:
            return True
        if f.mode in ("binary", "random") and hasattr(f, "short_read"):
            return f.short_read          # VB: True once a Get could not read a whole record
        cur = f.fh.tell()
        f.fh.seek(0, 2)
        end = f.fh.tell()
        f.fh.seek(cur)
        return cur >= end

    def lof(self, num) -> int:
        f = self.get(num)
        if f.fh is not None:
            f.fh.flush()
        return f.path.stat().st_size

    def loc(self, num) -> int:
        f = self.get(num)
        if f.mode in ("input", "binary-text"):
            return max(1, (f.pos + 127) // 128) if f.pos else 0
        if f.fh is None:
            return 0
        pos = f.fh.tell()
        return pos // f.reclen if f.mode == "random" else pos

    def seek_pos(self, num) -> int:
        f = self.get(num)
        if f.mode in ("input", "binary-text"):
            return f.pos + 1
        pos = f.fh.tell()
        return pos // f.reclen + 1 if f.mode == "random" else pos + 1

    def seek(self, num, pos):
        f = self.get(num)
        p = self._num(pos)
        if p < 1:
            raise self._err(63, "Bad record number")
        if f.mode in ("binary", "random"):
            f.fh.seek((p - 1) * f.reclen if f.mode == "random" else p - 1)
        elif f.mode in ("input", "binary-text"):
            f.pos = p - 1

    def freefile(self, rng=0) -> int:
        start = 256 if rng not in (None, 0, "") and self._num(rng) == 1 else 1
        for n in range(start, start + 255):
            if n not in self.files:
                return n
        raise self._err(67, "Too many files")

    # ------------------------------------------------------------ binary Get / Put
    def _position(self, f: VBFile, pos):
        if f.mode not in ("binary", "random"):
            raise self._err(54, "Bad file mode")
        if pos is not None:
            p = self._num(pos)
            if p < 1:
                raise self._err(63, "Bad record number")
            f.fh.seek((p - 1) * f.reclen if f.mode == "random" else p - 1)

    def put(self, num, pos, value, typ):
        f = self.get(num)
        self._position(f, pos)
        start = f.fh.tell()
        data = self.pack(value, typ, f.mode == "random")
        f.fh.write(data)
        if f.mode == "random" and len(data) < f.reclen and pos is not None:
            f.fh.seek(start + f.reclen)

    def get_value(self, num, pos, current, typ):
        f = self.get(num)
        self._position(f, pos)
        self._short = False
        v = self.unpack(f.fh, current, typ, f.mode == "random")
        f.short_read = self._short
        return v

    def pack(self, v, typ, random_mode=False) -> bytes:
        from .vbinterp import UDT, VBArray, to_num, to_str
        typ = (typ or "variant").lower()
        if isinstance(v, UDT):
            return b"".join(self.pack(v._fields[k], v._types[k], random_mode) for k in v._order)
        if isinstance(v, VBArray):
            return b"".join(self.pack(x, v.typ, random_mode) for x in v.items())
        if typ.startswith("string*"):
            n = int(typ[7:])
            return to_str(v).encode(ANSI, errors="replace")[:n].ljust(n, b" ")
        if typ == "string":
            b = to_str(v).encode(ANSI, errors="replace")
            return (struct.pack("<H", len(b)) if random_mode else b"") + b
        if typ == "integer":
            return struct.pack("<h", int(to_num(v)))
        if typ == "long":
            return struct.pack("<i", int(to_num(v)))
        if typ == "byte":
            return struct.pack("<B", int(to_num(v)) & 0xFF)
        if typ == "boolean":
            return struct.pack("<h", -1 if to_num(v) else 0)
        if typ == "single":
            return struct.pack("<f", float(to_num(v)))
        if typ == "double":
            return struct.pack("<d", float(to_num(v)))
        if typ == "currency":
            return struct.pack("<q", int(round(float(to_num(v)) * 10000)))
        if typ == "date":
            return struct.pack("<d", float(to_num(v)))
        # Variant: VarType + data
        if isinstance(v, bool):
            return struct.pack("<hh", 11, -1 if v else 0)
        if isinstance(v, int):
            return struct.pack("<hi", 3, v) if -2**31 <= v < 2**31 else struct.pack("<hd", 5, float(v))
        if isinstance(v, float):
            return struct.pack("<hd", 5, v)
        if isinstance(v, _dt.datetime):
            return struct.pack("<hd", 7, float(to_num(v)))
        b = to_str(v).encode(ANSI, errors="replace")
        return struct.pack("<hH", 8, len(b)) + b

    def unpack(self, fh, current, typ, random_mode=False):
        from .vbinterp import UDT, VBArray, to_date, to_str

        def rd(n):
            data = fh.read(n)
            if len(data) < n:
                self._short = True
            return data.ljust(n, b"\0")

        typ = (typ or "variant").lower()
        if isinstance(current, UDT):
            for k in current._order:
                current._fields[k] = self.unpack(fh, current._fields[k], current._types[k], random_mode)
            return current
        if isinstance(current, VBArray):
            keys = sorted(current.data) if len(current.bounds) != 1 else \
                [(i,) for i in range(current.bounds[0][0], current.bounds[0][1] + 1)]
            for k in keys:
                cur = current.data.get(k) if k in current.data else current.get(list(k))
                current.data[k] = self.unpack(fh, cur, current.typ, random_mode)
            return current
        if typ.startswith("string*"):
            n = int(typ[7:])
            return rd(n).decode(ANSI, errors="replace")
        if typ == "string":
            if random_mode:
                (n,) = struct.unpack("<H", rd(2))
            else:
                n = len(to_str(current).encode(ANSI, errors="replace"))
            return fh.read(n).decode(ANSI, errors="replace")
        fixed = {"integer": "<h", "long": "<i", "byte": "<B", "single": "<f", "double": "<d"}
        if typ in fixed:
            return struct.unpack(fixed[typ], rd(struct.calcsize(fixed[typ])))[0]
        if typ == "boolean":
            return struct.unpack("<h", rd(2))[0] != 0
        if typ == "currency":
            return struct.unpack("<q", rd(8))[0] / 10000
        if typ == "date":
            return to_date(struct.unpack("<d", rd(8))[0])
        (vt,) = struct.unpack("<h", rd(2))
        if vt == 11:
            return struct.unpack("<h", rd(2))[0] != 0
        if vt == 2:
            return struct.unpack("<h", rd(2))[0]
        if vt == 3:
            return struct.unpack("<i", rd(4))[0]
        if vt in (4,):
            return struct.unpack("<f", rd(4))[0]
        if vt == 5:
            return struct.unpack("<d", rd(8))[0]
        if vt == 7:
            return to_date(struct.unpack("<d", rd(8))[0])
        if vt == 8:
            (n,) = struct.unpack("<H", rd(2))
            return fh.read(n).decode(ANSI, errors="replace")
        from .vbinterp import EMPTY
        return EMPTY

    # ------------------------------------------------------------ file system functions
    def dir(self, pattern=None, attrs=0):
        from .vbinterp import EMPTY
        if pattern is None or pattern is EMPTY:
            if self._dir_iter is None:
                raise self._err(5, "Invalid procedure call or argument")
            return self._dir_iter.pop(0) if self._dir_iter else ""
        pattern = self._str(pattern)
        attrs = 0 if attrs is EMPTY else self._num(attrs)
        if attrs & 8:                      # vbVolume
            return ""
        p = Path(pattern) if pattern else Path("*")
        if pattern.endswith(("\\", "/")) or (p.is_dir() and not any(c in pattern for c in "*?")):
            folder, mask = (p, "*") if pattern.endswith(("\\", "/")) else (p.parent, p.name)
        else:
            folder, mask = p.parent, p.name
        names = []
        try:
            entries = sorted(os.listdir(folder if str(folder) else "."), key=str.lower)
        except OSError:
            entries = []
        for name in entries:
            if not fnmatch.fnmatch(name.lower(), mask.lower()):
                continue
            full = (folder / name)
            if full.is_dir():
                if attrs & 16:
                    names.append(name)
                continue
            fa = self._attrs(full)
            if fa & 2 and not attrs & 2 or fa & 4 and not attrs & 4:
                continue
            names.append(name)
        self._dir_iter = names
        return names.pop(0) if names else ""

    @staticmethod
    def _attrs(path: Path) -> int:
        try:
            if os.name == "nt":
                a = os.stat(path).st_file_attributes  # type: ignore[attr-defined]
                return a & 0x3F
        except (OSError, AttributeError):
            pass
        a = 16 if path.is_dir() else 0
        if path.exists() and not os.access(path, os.W_OK):
            a |= 1
        return a

    def kill(self, pattern):
        p = self._path(pattern)
        if any(c in p.name for c in "*?"):
            hits = [x for x in (p.parent if str(p.parent) else Path(".")).iterdir()
                    if x.is_file() and fnmatch.fnmatch(x.name.lower(), p.name.lower())]
            if not hits:
                raise self._err(53, "File not found")
            for x in hits:
                x.unlink()
            return
        if not p.is_file():
            raise self._err(53, f"File not found: {p}")
        p.unlink()

    def mkdir(self, path):
        p = self._path(path)
        if p.exists():
            raise self._err(75, f"Path/File access error: {p}")
        p.mkdir()

    def rmdir(self, path):
        p = self._path(path)
        if not p.is_dir():
            raise self._err(76, f"Path not found: {p}")
        if any(p.iterdir()):
            raise self._err(75, f"Path/File access error (folder not empty): {p}")
        p.rmdir()

    def chdir(self, path):
        p = self._path(path)
        if not p.is_dir():
            raise self._err(76, f"Path not found: {p}")
        os.chdir(p)

    def curdir(self, *_):
        return os.getcwd()

    def filecopy(self, src, dst):
        s = self._path(src)
        if not s.is_file():
            raise self._err(53, f"File not found: {s}")
        shutil.copyfile(s, self._path(dst))

    def filelen(self, path):
        p = self._path(path)
        if not p.is_file():
            raise self._err(53, f"File not found: {p}")
        return p.stat().st_size

    def filedatetime(self, path):
        p = self._path(path)
        if not p.exists():
            raise self._err(53, f"File not found: {p}")
        return _dt.datetime.fromtimestamp(p.stat().st_mtime).replace(microsecond=0)

    def getattr_(self, path):
        p = self._path(path)
        if not p.exists():
            raise self._err(53, f"File not found: {p}")
        return self._attrs(p)

    def setattr_(self, path, attrs):
        p = self._path(path)
        a = self._num(attrs)
        if os.name == "nt":
            import ctypes
            if not ctypes.windll.kernel32.SetFileAttributesW(str(p), a or 0x80):
                raise self._err(75, f"Path/File access error: {p}")
        else:
            mode = p.stat().st_mode
            os.chmod(p, mode & ~0o222 if a & 1 else mode | 0o200)

    def rename(self, old, new):
        o, n = self._path(old), self._path(new)
        if not o.exists():
            raise self._err(53, f"File not found: {o}")
        if n.exists():
            raise self._err(58, "File already exists")
        os.rename(o, n)

    def builtins(self) -> dict:
        from .vbinterp import EMPTY
        return {
            "freefile": lambda r=0: self.freefile(r), "eof": self.eof, "lof": self.lof, "loc": self.loc,
            "seek": self.seek_pos, "input": self.input_chars,
            "dir": lambda p=EMPTY, a=0: self.dir(p, a), "kill": self.kill, "mkdir": self.mkdir,
            "rmdir": self.rmdir, "chdir": self.chdir, "chdrive": lambda d: os.chdir(self._str(d)[:1] + ":\\"),
            "curdir": self.curdir, "filecopy": self.filecopy, "filelen": self.filelen,
            "filedatetime": self.filedatetime, "getattr": self.getattr_, "setattr": self.setattr_,
            "reset": lambda: self.close(), "spc": Spc, "tab": lambda n=None: Tab(None if n is EMPTY else n),
        }
