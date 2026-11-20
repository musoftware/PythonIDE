"""Pure-Python Scripting.FileSystemObject for the VB6 interpreter.

CreateObject("Scripting.FileSystemObject") normally needs COM (pywin32); this
implements the commonly used subset so file I/O works everywhere:
FileExists, FolderExists, CreateFolder, DeleteFile, DeleteFolder, CopyFile, MoveFile,
GetFileName, GetBaseName, GetExtensionName, GetParentFolderName, BuildPath,
GetAbsolutePathName, OpenTextFile(path [, iomode [, create]]), CreateTextFile(path [, overwrite]),
and TextStream: ReadAll, ReadLine, Read(n), SkipLine, AtEndOfStream, Line, Write, WriteLine,
WriteBlankLines, Close. Text is UTF-8 (a UTF-8 BOM / UTF-16 BOM is detected when reading)."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from .vbinterp import EMPTY, err, to_bool, to_num, to_str

FOR_READING, FOR_WRITING, FOR_APPENDING = 1, 2, 8


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("mbcs" if os.name == "nt" else "latin-1", errors="replace")


class TextStream:
    vb_typename = "TextStream"

    def __init__(self, path: Path, mode: int):
        self.path, self.mode = path, mode
        self.closed = False
        self.line = 1
        if mode == FOR_READING:
            self._text = _read_text(path).replace("\r\n", "\n")
            self._pos = 0
            self._fh = None
        else:
            self._fh = open(path, "a" if mode == FOR_APPENDING else "w", encoding="utf-8", newline="")

    def _check(self, reading: bool):
        if self.closed:
            raise err(52, "Bad file name or number (the file is closed)")
        if reading != (self.mode == FOR_READING):
            raise err(54, "Bad file mode")

    def vb_get(self, name):
        if name == "atendofstream":
            self._check(True)
            return self._pos >= len(self._text)
        if name == "atendofline":
            self._check(True)
            return self._pos >= len(self._text) or self._text[self._pos] == "\n"
        if name == "line":
            return self.line
        if name in ("readall", "readline", "close", "skipline"):
            return self.vb_call(name, [])
        raise err(438, f"Object doesn't support property '{name}'")

    def vb_set(self, name, value):
        raise err(383, f"'{name}' is read-only")

    def vb_call(self, name, args):
        if name == "readall":
            self._check(True)
            out, self._pos = self._text[self._pos:], len(self._text)
            return out.replace("\n", "\r\n")
        if name in ("readline", "skipline"):
            self._check(True)
            if self._pos >= len(self._text):
                raise err(62, "Input past end of file")
            end = self._text.find("\n", self._pos)
            end = len(self._text) if end < 0 else end
            out, self._pos = self._text[self._pos:end], end + 1
            self.line += 1
            return out if name == "readline" else EMPTY
        if name == "read":
            self._check(True)
            n = int(to_num(args[0])) if args else 1
            out = self._text[self._pos:self._pos + n]
            self._pos += len(out)
            return out
        if name in ("write", "writeline"):
            self._check(False)
            text = to_str(args[0]) if args else ""
            self._fh.write(text + ("\r\n" if name == "writeline" else ""))
            return EMPTY
        if name == "writeblanklines":
            self._check(False)
            self._fh.write("\r\n" * int(to_num(args[0]) if args else 1))
            return EMPTY
        if name == "close":
            if self._fh is not None and not self.closed:
                self._fh.close()
            self.closed = True
            return EMPTY
        return self.vb_get(name)


class FileSystemObject:
    vb_typename = "FileSystemObject"

    def __init__(self, base: str | Path | None = None):
        self.base = Path(base) if base else Path.cwd()

    def _p(self, v) -> Path:
        p = Path(to_str(v))
        return p if p.is_absolute() else self.base / p

    def vb_get(self, name):
        return self.vb_call(name, [])

    def vb_set(self, name, value):
        raise err(438, f"Object doesn't support property '{name}'")

    def vb_call(self, name, args):
        a = list(args)
        if name == "fileexists":
            return self._p(a[0]).is_file()
        if name == "folderexists":
            return self._p(a[0]).is_dir()
        if name == "createfolder":
            self._p(a[0]).mkdir(parents=True, exist_ok=False)
            return EMPTY
        if name == "deletefile":
            p = self._p(a[0])
            if not p.is_file():
                raise err(53, f"File not found: {p}")
            p.unlink()
            return EMPTY
        if name == "deletefolder":
            shutil.rmtree(self._p(a[0]))
            return EMPTY
        if name == "copyfile":
            overwrite = to_bool(a[2]) if len(a) > 2 else True
            dst = self._p(a[1])
            if dst.exists() and not overwrite:
                raise err(58, "File already exists")
            shutil.copyfile(self._p(a[0]), dst)
            return EMPTY
        if name == "movefile":
            shutil.move(str(self._p(a[0])), str(self._p(a[1])))
            return EMPTY
        if name == "getfilename":
            return Path(to_str(a[0])).name
        if name == "getbasename":
            return Path(to_str(a[0])).stem
        if name == "getextensionname":
            return Path(to_str(a[0])).suffix.lstrip(".")
        if name == "getparentfoldername":
            return str(Path(to_str(a[0])).parent)
        if name == "buildpath":
            return str(Path(to_str(a[0])) / to_str(a[1]))
        if name == "getabsolutepathname":
            return str(self._p(a[0]).resolve())
        if name == "opentextfile":
            p = self._p(a[0])
            mode = int(to_num(a[1])) if len(a) > 1 and a[1] is not EMPTY else FOR_READING
            create = to_bool(a[2]) if len(a) > 2 and a[2] is not EMPTY else False
            if mode not in (FOR_READING, FOR_WRITING, FOR_APPENDING):
                raise err(5, "Invalid procedure call or argument")
            if not p.exists():
                if mode == FOR_READING or not create:
                    raise err(53, f"File not found: {p}")
                p.touch()
            return TextStream(p, mode)
        if name == "createtextfile":
            p = self._p(a[0])
            overwrite = to_bool(a[1]) if len(a) > 1 and a[1] is not EMPTY else True
            if p.exists() and not overwrite:
                raise err(58, "File already exists")
            return TextStream(p, FOR_WRITING)
        raise err(438, f"Object doesn't support this property or method: {name}")


class Dictionary:
    """Scripting.Dictionary: Add, Exists, Item (get/let, default member), Items, Keys, Remove, RemoveAll,
    Count, Key(old) = new, CompareMode (0 binary / 1 text), For Each over the keys. Keys keep their type
    (1 and "1" are different keys), as in VBScript."""
    vb_typename = "Dictionary"
    vb_default = "item"

    def __init__(self):
        self._data: dict = {}            # normalized key -> (key, item)
        self.comparemode = 0

    def _norm(self, k):
        from .vbinterp import EMPTY as _E
        if hasattr(k, "vb_get") and not isinstance(k, str):
            return ("obj", id(k))
        if k is _E:
            return ("s", "")
        if isinstance(k, bool):
            return ("n", -1 if k else 0)
        if isinstance(k, (int, float)):
            return ("n", float(k))
        s = to_str(k)
        return ("s", s.lower() if self.comparemode else s)

    def vb_items(self):
        return [k for k, _ in self._data.values()]

    def _array(self, values):
        from .vbinterp import VBArray
        arr = VBArray([(0, len(values) - 1)])
        for i, v in enumerate(values):
            arr.data[(i,)] = v
        return arr

    def vb_get(self, name):
        if name == "count":
            return len(self._data)
        if name == "comparemode":
            return self.comparemode
        if name in ("items", "keys", "removeall"):
            return self.vb_call(name, [])
        raise err(438, f"Object doesn't support property '{name}'")

    def vb_set(self, name, value):
        if name == "comparemode":
            if self._data:
                raise err(5, "Invalid procedure call or argument (CompareMode can only change while empty)")
            self.comparemode = int(to_num(value))
            return
        raise err(438, f"Object doesn't support property '{name}'")

    def vb_setitem(self, args, value):
        self.vb_setindexed("item", args, value)

    def vb_setindexed(self, name, args, value):
        if name == "item":
            k = self._norm(args[0])
            key = self._data[k][0] if k in self._data else args[0]
            self._data[k] = (key, value)
            return
        if name == "key":                      # d.Key("old") = "new"
            k = self._norm(args[0])
            if k not in self._data:
                raise err(32811, "Element not found")
            nk = self._norm(value)
            if nk in self._data and nk != k:
                raise err(457, "This key is already associated with an element of this collection")
            self._data = {(nk if kk == k else kk): ((value, it) if kk == k else (key, it))
                          for kk, (key, it) in self._data.items()}
            return
        raise err(438, f"Object doesn't support property '{name}'")

    def vb_call(self, name, args):
        a = list(args)
        if name == "add":
            k = self._norm(a[0])
            if k in self._data:
                raise err(457, "This key is already associated with an element of this collection")
            self._data[k] = (a[0], a[1] if len(a) > 1 else EMPTY)
            return EMPTY
        if name == "exists":
            return self._norm(a[0]) in self._data
        if name == "item":
            k = self._norm(a[0])
            if k not in self._data:          # reading a missing key adds it (VBScript behaviour)
                self._data[k] = (a[0], EMPTY)
            return self._data[k][1]
        if name == "items":
            return self._array([v for _, v in self._data.values()])
        if name == "keys":
            return self._array([k for k, _ in self._data.values()])
        if name == "remove":
            k = self._norm(a[0])
            if k not in self._data:
                raise err(32811, "Element not found")
            del self._data[k]
            return EMPTY
        if name == "removeall":
            self._data.clear()
            return EMPTY
        if name == "count":
            return len(self._data)
        raise err(438, f"Object doesn't support this property or method: {name}")


def create(progid: str, base=None):
    """Return an emulated object for *progid*, or None."""
    p = progid.strip().lower()
    if p == "scripting.filesystemobject":
        return FileSystemObject(base)
    if p == "scripting.dictionary":
        return Dictionary()
    return None
