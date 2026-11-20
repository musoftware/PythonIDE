"""``Declare Function/Sub ... Lib "..."`` for the BASIC interpreter (Win32 API through ctypes).

Marshalling follows VB6:

* ``ByVal x As Long/Integer/Byte/Single/Double/Boolean/Currency/LongPtr`` -> the C value
  (a Long that does not fit in 32 bits, e.g. a 64-bit handle, is passed pointer-sized);
* ``ByRef x As <number>`` -> pointer to a temporary; the variable receives the new value after the call;
* ``ByVal s As String`` -> pointer to an ANSI copy of the string. Like VB6 the buffer is copied back into
  the variable after the call, so ``buf = String$(260, 0): GetWindowsDirectory buf, 260`` works.
  ``vbNullString`` (or ``ByVal 0&``) passes NULL;
* ``ByRef t As <user-defined Type>`` -> pointer to a C struct built from the Type (fixed-length strings,
  nested Types and fixed arrays supported); fields are copied back after the call;
* ``As Any`` -> decided from the value (number, string, Type);
* return types: Long/Integer/Byte/Boolean/Single/Double/Currency/LongPtr/String/Sub.

``Err.LastDllError`` is set after every call (``GetLastError``). Callbacks (``AddressOf``) are not supported.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

ANSI = "mbcs" if os.name == "nt" else "latin-1"
_SIMPLE = {
    "long": ctypes.c_long, "integer": ctypes.c_short, "byte": ctypes.c_ubyte, "boolean": ctypes.c_int,
    "single": ctypes.c_float, "double": ctypes.c_double, "longptr": ctypes.c_ssize_t,
    "longlong": ctypes.c_longlong, "currency": ctypes.c_longlong, "date": ctypes.c_double,
}
_STRUCT_SIMPLE = dict(_SIMPLE, boolean=ctypes.c_short)    # VB Boolean inside a Type is 2 bytes
_libs: dict[str, object] = {}


class NullString(str):
    """vbNullString: an empty string that is passed to DLLs as NULL."""


NULL_STRING = NullString("")


def _load_lib(name: str, folder: str | None):
    key = name.lower()
    if key in _libs:
        return _libs[key]
    from .vbinterp import err
    if os.name != "nt":
        raise err(48, f"Error in loading DLL: {name} (Declare needs Windows)")
    cands = [name]
    if not Path(name).suffix:
        cands.insert(0, name + ".dll")
    if folder:
        cands = [str(Path(folder) / c) for c in cands if (Path(folder) / c).exists()] + cands
    last = None
    for c in cands:
        try:
            lib = ctypes.WinDLL(c, use_last_error=True)
            _libs[key] = lib
            return lib
        except OSError as e:
            last = e
    raise err(48, f"Error in loading DLL: {name} ({last})")


class DeclaredProc:
    def __init__(self, decl, interp):
        self.decl = decl
        self.it = interp
        self._fn = None
        self._structs: dict[str, type] = {}

    # ------------------------------------------------------------ setup
    def _function(self):
        if self._fn is None:
            from .vbinterp import err
            folder = getattr(self.it.host, "folder", None) or getattr(self.it, "folder", None)
            lib = _load_lib(self.decl.lib, str(folder) if folder else None)
            alias = self.decl.alias
            try:
                fn = lib[int(alias[1:])] if alias.startswith("#") else getattr(lib, alias)
            except (AttributeError, ValueError):
                raise err(453, f"Specified DLL function not found: {alias} in {self.decl.lib}") from None
            fn.restype = self._restype()
            self._fn = fn
        return self._fn

    def _restype(self):
        t = (self.decl.ret or "variant").lower()
        if self.decl.kind == "sub" or t == "void":
            return None
        if t == "string":
            return ctypes.c_char_p
        if t in _SIMPLE:
            return _SIMPLE[t]
        return ctypes.c_ssize_t

    # ------------------------------------------------------------ structs
    def struct_for(self, type_name: str):
        type_name = type_name.lower()
        if type_name in self._structs:
            return self._structs[type_name]
        from .vbinterp import err
        members = self.it.types_global().get(type_name)
        if members is None:
            raise err(458, f"Type '{type_name}' cannot be passed to a DLL")
        fields = []
        for m in members:
            name, typ = m[0].lower(), (m[1] or "variant").lower()
            ct = self._ctype_for_field(typ)
            if len(m) > 2 and m[2]:
                count = 1
                for lo, hi in m[2]:
                    lo_v = self.it.eval(lo, self.it.const_frame()) if lo is not None else 0
                    count *= int(self.it.eval(hi, self.it.const_frame())) - int(lo_v) + 1
                ct = ct * count
            fields.append((name, ct))
        st = type(f"VB_{type_name}", (ctypes.Structure,), {"_fields_": fields})
        self._structs[type_name] = st
        return st

    def _ctype_for_field(self, typ):
        if typ.startswith("string*"):
            return ctypes.c_char * int(typ[7:])
        if typ in _STRUCT_SIMPLE:
            return _STRUCT_SIMPLE[typ]
        if typ in self.it.types_global():
            return self.struct_for(typ)
        if typ == "string":
            return ctypes.c_char_p
        return ctypes.c_ssize_t

    def _fill_struct(self, s, udt):
        from .vbinterp import UDT, VBArray, to_num, to_str
        for name, ct in s._fields_:
            v = udt._fields.get(name)
            typ = udt._types.get(name, "variant")
            if isinstance(v, UDT):
                self._fill_struct(getattr(s, name), v)
            elif isinstance(v, VBArray):
                arr = getattr(s, name)
                for i, x in enumerate(v.items()[:len(arr)]):
                    if isinstance(x, UDT):
                        self._fill_struct(arr[i], x)
                    else:
                        arr[i] = float(to_num(x)) if isinstance(arr[i], float) else int(to_num(x))
            elif typ.startswith("string*"):
                getattr(s, name).value = to_str(v).encode(ANSI, errors="replace")[:ct._length_]
            elif ct is ctypes.c_char_p:
                setattr(s, name, to_str(v).encode(ANSI, errors="replace"))
            elif ct in (ctypes.c_float, ctypes.c_double):
                setattr(s, name, float(to_num(v)))
            elif typ == "currency":
                setattr(s, name, int(round(float(to_num(v)) * 10000)))
            else:
                setattr(s, name, int(to_num(v)) if not isinstance(v, bool) else (-1 if v else 0))

    def _read_struct(self, s, udt):
        from .vbinterp import UDT, VBArray, coerce
        for name, ct in s._fields_:
            v = udt._fields.get(name)
            typ = udt._types.get(name, "variant")
            raw = getattr(s, name)
            if isinstance(v, UDT):
                self._read_struct(raw, v)
            elif isinstance(v, VBArray):
                keys = [(i,) for i in range(v.bounds[0][0], v.bounds[0][1] + 1)] if len(v.bounds) == 1 else sorted(v.data)
                for i, k in enumerate(keys[:len(raw)]):
                    cur = v.get(list(k))
                    if isinstance(cur, UDT):
                        self._read_struct(raw[i], cur)
                    else:
                        v.data[k] = coerce(raw[i], v.typ)
            elif typ.startswith("string*"):
                b = bytes(raw)
                udt._fields[name] = coerce(b.decode(ANSI, errors="replace").replace("\0", " ")
                                           if b.strip(b"\0") else " " * len(b), typ)
            elif ct is ctypes.c_char_p:
                udt._fields[name] = (raw or b"").decode(ANSI, errors="replace")
            elif typ == "currency":
                udt._fields[name] = raw / 10000
            elif typ == "boolean":
                udt._fields[name] = raw != 0
            else:
                udt._fields[name] = raw

    # ------------------------------------------------------------ call
    def call(self, args, cells):
        from .vbinterp import EMPTY, NOTHING, UDT, _MISSING, coerce, err, to_num, to_str
        fn = self._function()
        params = self.decl.params
        if len(args) > len(params):
            raise err(450, f"Wrong number of arguments for {self.decl.name}")
        c_args, post = [], []
        for i, p in enumerate(params):
            v = args[i] if i < len(args) else _MISSING
            cell = cells[i] if cells and i < len(cells) else None
            if v is _MISSING:
                if not p.optional:
                    raise err(449, f"Argument not optional: {p.name} (calling {self.decl.name})")
                v = self.it.eval(p.default, self.it.const_frame()) if p.default is not None else 0
            typ = (p.typ or "any").lower()
            if typ == "variant":
                typ = "any"
            if isinstance(v, UDT):
                st = self.struct_for(v._name)()
                self._fill_struct(st, v)
                c_args.append(ctypes.byref(st))
                post.append(lambda st=st, v=v: self._read_struct(st, v))
                continue
            if typ == "string" or (typ == "any" and isinstance(v, str)):
                if isinstance(v, NullString) or (not isinstance(v, str) and (v is EMPTY or v is NOTHING or to_num(v) == 0)):
                    c_args.append(None)
                    continue
                s = to_str(v)
                raw = s.encode(ANSI, errors="replace")
                buf = ctypes.create_string_buffer(raw, len(raw) + 1)
                c_args.append(buf)
                if cell is not None:
                    post.append(lambda buf=buf, cell=cell, n=len(raw):
                                setattr(cell, "value", coerce(buf.raw[:n].decode(ANSI, errors="replace"), cell.typ)))
                continue
            if typ == "any":
                if v is EMPTY or v is NOTHING or v is None:
                    c_args.append(ctypes.c_ssize_t(0))
                    continue
                typ = "double" if isinstance(v, float) else "longptr" if not p.byref else "long"
            ct = _SIMPLE.get(typ)
            if ct is None:
                raise err(458, f"{self.decl.name}: parameter type '{p.typ}' is not supported in Declare")
            n = to_num(v)
            if typ == "currency":
                n = int(round(float(n) * 10000))
            elif ct in (ctypes.c_float, ctypes.c_double):
                n = float(n)
            else:
                n = int(n)
                if ct is ctypes.c_long and not -2**31 <= n < 2**32:
                    ct = ctypes.c_ssize_t
                elif ct is ctypes.c_long and n >= 2**31:
                    n -= 2**32
            if p.byref:
                box = ct(n)
                c_args.append(ctypes.byref(box))
                if cell is not None:
                    def back(box=box, cell=cell, typ=typ):
                        val = box.value
                        if typ == "currency":
                            val = val / 10000
                        elif typ == "boolean":
                            val = val != 0
                        cell.value = coerce(val, cell.typ)
                    post.append(back)
            else:
                c_args.append(ct(n))
        try:
            result = fn(*c_args)
        except OSError as e:          # access violation etc. are reported as VB errors
            raise err(49, f"{self.decl.name}: {e}") from None
        finally:
            try:
                self.it.err.lastdllerror = ctypes.get_last_error()
            except Exception:  # noqa: BLE001
                pass
        for f in post:
            f()
        if self.decl.kind == "sub":
            return EMPTY
        rt = (self.decl.ret or "").lower()
        if rt == "string":
            return (result or b"").decode(ANSI, errors="replace")
        if rt == "boolean":
            return result != 0
        if rt == "currency":
            return result / 10000
        return result
