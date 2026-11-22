"""Small PE edits for Node.js single executable applications (no third-party tools):

* strip_signature(path)      remove the Authenticode signature (it is invalid after any edit)
* add_resources(path, items) add / replace resources with the Windows resource update API
                             (BeginUpdateResourceW / UpdateResourceW / EndUpdateResourceW)
* res_file_entries(res)      the resources of a .res file (windres -O res), to copy them into an exe
* flip_fuse(path, fuse)      "<fuse>:0" -> "<fuse>:1" (the SEA sentinel postject flips)
* set_gui_subsystem(path)    IMAGE_SUBSYSTEM_WINDOWS_GUI: no console window when the exe is started
"""
from __future__ import annotations

import ctypes
import struct
from ctypes import wintypes as wt
from pathlib import Path

RT_RCDATA = 10


def _pe_offsets(data: bytes) -> tuple[int, bool]:
    """(offset of the optional header, is PE32+)."""
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE file")
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    return opt, magic == 0x20B


def strip_signature(path: Path) -> bool:
    p = Path(path)
    data = bytearray(p.read_bytes())
    opt, plus = _pe_offsets(data)
    sec_dir = opt + (144 if plus else 128)          # data directory 4 = IMAGE_DIRECTORY_ENTRY_SECURITY
    off, size = struct.unpack_from("<II", data, sec_dir)
    if not off or not size:
        return False
    struct.pack_into("<II", data, sec_dir, 0, 0)
    if off + size >= len(data) - 8:                 # the certificate table is the end of the file
        del data[off:]
    p.write_bytes(bytes(data))
    return True


def set_gui_subsystem(path: Path) -> None:
    p = Path(path)
    data = bytearray(p.read_bytes())
    opt, _plus = _pe_offsets(data)
    struct.pack_into("<H", data, opt + 68, 2)        # Subsystem = IMAGE_SUBSYSTEM_WINDOWS_GUI
    p.write_bytes(bytes(data))


def flip_fuse(path: Path, fuse: str) -> None:
    p = Path(path)
    data = p.read_bytes()
    want = (fuse + ":0").encode("ascii")
    i = data.find(want)
    if i < 0:
        if data.find((fuse + ":1").encode("ascii")) >= 0:
            return
        raise ValueError("the SEA fuse was not found in the Node.js binary")
    with open(p, "r+b") as f:
        f.seek(i + len(want) - 1)
        f.write(b"1")


def _k32():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.BeginUpdateResourceW.argtypes = [wt.LPCWSTR, wt.BOOL]
    k.BeginUpdateResourceW.restype = wt.HANDLE
    k.UpdateResourceW.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, wt.WORD, ctypes.c_void_p, wt.DWORD]
    k.UpdateResourceW.restype = wt.BOOL
    k.EndUpdateResourceW.argtypes = [wt.HANDLE, wt.BOOL]
    k.EndUpdateResourceW.restype = wt.BOOL
    return k


def _id(v):
    """int -> MAKEINTRESOURCE, str -> wide string (kept alive by the caller)."""
    if isinstance(v, int):
        return ctypes.c_void_p(v), None
    buf = ctypes.create_unicode_buffer(v)
    return ctypes.cast(buf, ctypes.c_void_p), buf


def add_resources(path: Path, items: list[tuple[int | str, int | str, int, bytes]]) -> None:
    """items: (type, name, language, data); same type/name/language replaces."""
    k = _k32()
    h = k.BeginUpdateResourceW(str(path), False)
    if not h:
        raise OSError(f"BeginUpdateResource failed ({ctypes.get_last_error()})")
    keep = []
    try:
        for typ, name, lang, data in items:
            t, tb = _id(typ)
            n, nb = _id(name)
            buf = ctypes.create_string_buffer(data, len(data))
            keep += [tb, nb, buf]
            if not k.UpdateResourceW(h, t, n, lang, buf, len(data)):
                raise OSError(f"UpdateResource failed ({ctypes.get_last_error()})")
    except Exception:
        k.EndUpdateResourceW(h, True)
        raise
    if not k.EndUpdateResourceW(h, False):
        raise OSError(f"EndUpdateResource failed ({ctypes.get_last_error()})")


def _res_id(data: bytes, i: int):
    if struct.unpack_from("<H", data, i)[0] == 0xFFFF:
        return struct.unpack_from("<H", data, i + 2)[0], i + 4
    j = i
    while struct.unpack_from("<H", data, j)[0] != 0:
        j += 2
    return data[i:j].decode("utf-16-le"), j + 2


def res_file_entries(res: Path) -> list[tuple[int | str, int | str, int, bytes]]:
    """Entries of a 32-bit .res file (the first, empty entry is skipped)."""
    data = Path(res).read_bytes()
    out, i = [], 0
    while i + 8 <= len(data):
        size, hsize = struct.unpack_from("<II", data, i)
        typ, j = _res_id(data, i + 8)
        name, j = _res_id(data, j)
        j = (j + 3) & ~3
        _dver, _mflags, lang = struct.unpack_from("<IHH", data, j)
        body = data[i + hsize:i + hsize + size]
        if not (typ == 0 and name == 0):
            out.append((typ, name, lang, body))
        i = (i + hsize + size + 3) & ~3
    return out


__all__ = ["RT_RCDATA", "add_resources", "flip_fuse", "res_file_entries", "set_gui_subsystem", "strip_signature"]
