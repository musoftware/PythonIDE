"""Python programs packed as .exe (PyInstaller, py2exe, cx_Freeze) -> RAD IDE project.

1. Extraction - PyInstaller CArchive + PYZ (the pyinstxtractor-ng algorithm, implemented here), py2exe
   PYTHONSCRIPT resource + embedded library, cx_Freeze library.zip.  Entry scripts get a valid .pyc header.
2. Decompilation of the main script, matching the program's Python version:
   pycdc (Decompyle++, when present in %LOCALAPPDATA%\\RADIDE\\tools or on PATH), decompyle3 / uncompyle6
   (Python <= 3.8, when installed), otherwise the built-in bytecode decompiler below (CPython 3.11 - 3.13:
   straight-line code, if/elif/else, for/while, break/continue, lambdas, f-strings, imports, functions,
   classes).  It must run on the same Python version as the bytecode: another installed interpreter of that
   version is used through ``py -X.Y`` when needed.  Functions it cannot rebuild keep a disassembly in
   comments (and are rewritten by AI when allowed).
3. The recovered source goes through the existing Python importer (radide/importers/python_import.py):
   the program is captured (windows + widgets with their real geometry) and becomes .form files plus a
   python-tk / python-qt project with the original callbacks as event handlers.

This file also runs stand-alone (``python pyexe.py --decompile in.pyc out.py``) inside an interpreter
of the bytecode's version.  Only for programs you wrote, own, or may legally analyse.
"""
from __future__ import annotations

import dis
import marshal
import re
import shutil
import struct
import sys
import types
import zlib
from pathlib import Path

if __name__ not in ("__main__", "__decompile__"):
    from .base import ImportResult, find_tool
    from .dotnet import ai_rewrite, run_tool, say, set_form_code, set_startup

COOKIE = b"MEI\x0c\x0b\x0a\x0b\x0e"
MAGIC_BY_VERSION = {(3, 6): 3379, (3, 7): 3394, (3, 8): 3413, (3, 9): 3425, (3, 10): 3439, (3, 11): 3495,
                    (3, 12): 3531, (3, 13): 3571, (3, 14): 3627}
VERSION_BY_MAGIC = {}
for _v, _m in MAGIC_BY_VERSION.items():
    VERSION_BY_MAGIC[_m] = _v
SKIP_SCRIPTS = re.compile(r"^(pyi_rth_|pyiboot|pyimod|_pyi_|pyi-)", re.I)
STD_PREFIXES = ("PyInstaller", "pyimod", "pkg_resources", "setuptools", "_distutils_hack", "importlib_metadata",
                "zipp", "jaraco", "more_itertools", "packaging", "typing_extensions", "pywin32", "win32", "PIL",
                "numpy", "pandas", "PyQt5", "PyQt6", "PySide2", "PySide6", "shiboken", "tkinter", "certifi",
                "charset_normalizer", "idna", "urllib3", "requests", "six", "dateutil", "pytz", "yaml",
                "customtkinter", "darkdetect", "ttkbootstrap", "pygame", "kivy", "wx", "matplotlib", "scipy",
                "cryptography", "cffi", "psutil", "colorama", "attr", "attrs", "platformdirs", "tomli",
                "jinja2", "markupsafe", "click", "pyparsing", "bs4", "soupsieve", "lxml", "openpyxl", "et_xmlfile",
                "docx", "reportlab", "sqlalchemy", "greenlet", "serial", "pyautogui", "pynput", "keyboard",
                "mouse", "win10toast", "plyer", "comtypes", "pythoncom", "pywintypes")


# ============================================================================ extraction
class Extracted:
    def __init__(self):
        self.version: tuple[int, int] | None = None
        self.magic: bytes | None = None
        self.scripts: list[Path] = []        # entry scripts (.pyc with header)
        self.modules: dict[str, Path] = {}   # module name -> .pyc
        self.files: list[Path] = []          # other bundled files (data, dlls)
        self.notes: list[str] = []
        self.encrypted = False


def _magic_for(version) -> bytes | None:
    if version and tuple(version[:2]) in MAGIC_BY_VERSION:
        return struct.pack("<H", MAGIC_BY_VERSION[tuple(version[:2])]) + b"\r\n"
    return None


def _pyc_header(magic: bytes) -> bytes:
    return magic + b"\0" * 12          # 3.7+: magic, flags, 8 bytes (mtime+size or hash)


def _safe_rel(name: str) -> str:
    name = name.replace("\\", "/").lstrip("/")
    parts = [p for p in name.split("/") if p not in ("", ".", "..")]
    return "/".join(parts) or "unnamed"


def extract_pyinstaller(path: Path, out: Path) -> Extracted:
    ex = Extracted()
    data = path.read_bytes()
    pos = data.rfind(COOKIE)
    if pos < 0:
        ex.notes.append("PyInstaller cookie not found")
        return ex
    size = len(data)
    # 2.1+: magic(8) lengthofPackage toc tocLen pyver pylibname(64)  -> 88 bytes; 2.0: 24 bytes
    if data[pos + 24:pos + 24 + 64].strip(b"\0").lower().startswith(b"python"):
        cookie_size = 88
        _m, length, toc, toc_len, pyver, _lib = struct.unpack("!8sIIii64s", data[pos:pos + 88])
    else:
        cookie_size = 24
        _m, length, toc, toc_len, pyver = struct.unpack("!8siiii", data[pos:pos + 24])
    ex.version = (pyver // 100, pyver % 100) if pyver >= 100 else (pyver // 10, pyver % 10)
    tail = size - pos - cookie_size
    overlay = size - (length + tail)
    toc_pos = overlay + toc
    entries = []
    p = toc_pos
    while p < toc_pos + toc_len:
        (entry_size,) = struct.unpack("!i", data[p:p + 4])
        if entry_size <= 0:
            break
        name_len = entry_size - 18
        e_pos, c_size, u_size, c_flag, typ, name = struct.unpack(f"!IIIBc{name_len}s", data[p + 4:p + entry_size])
        name = name.rstrip(b"\0").decode("utf-8", "replace")
        entries.append((name, overlay + e_pos, c_size, u_size, c_flag, typ.decode("latin-1")))
        p += entry_size
    out.mkdir(parents=True, exist_ok=True)
    pyz_list = []
    raw_scripts = []
    for name, e_pos, c_size, _u, c_flag, typ in entries:
        blob = data[e_pos:e_pos + c_size]
        if c_flag:
            try:
                blob = zlib.decompress(blob)
            except zlib.error:
                ex.notes.append(f"could not decompress {name}")
                continue
        rel = _safe_rel(name)
        if typ == "s":
            raw_scripts.append((rel, blob))
            continue
        if typ in ("z", "Z"):
            dest = out / (rel + (".pyz" if not rel.endswith(".pyz") else ""))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
            pyz_list.append(dest)
            continue
        if typ in ("m", "M"):
            dest = out / "_modules" / (rel.replace(".", "/") + ".pyc")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
            ex.modules[rel] = dest
            if ex.magic is None and blob[2:4] == b"\r\n":
                ex.magic = blob[:4]
            continue
        dest = out / "_files" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
        ex.files.append(dest)
    for pyz in pyz_list:
        _extract_pyz(pyz, out / "_pyz", ex)
    if ex.magic is None:
        ex.magic = _magic_for(ex.version)
    elif ex.version is None or tuple(ex.version) != VERSION_BY_MAGIC.get(struct.unpack("<H", ex.magic[:2])[0]):
        v = VERSION_BY_MAGIC.get(struct.unpack("<H", ex.magic[:2])[0])
        if v:
            ex.version = v
    for rel, blob in raw_scripts:
        if SKIP_SCRIPTS.match(Path(rel).name):
            continue
        dest = out / (rel + ".pyc")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_pyc_header(ex.magic or b"\0\0\r\n") + blob)
        ex.scripts.append(dest)
    return ex


def _extract_pyz(pyz: Path, out: Path, ex: Extracted) -> None:
    data = pyz.read_bytes()
    if data[:4] != b"PYZ\0":
        return
    magic = data[4:8]
    if ex.magic is None:
        ex.magic = magic
    (toc_pos,) = struct.unpack("!i", data[8:12])
    try:
        toc = marshal.loads(data[toc_pos:])
    except Exception:  # noqa: BLE001 - another Python version's marshal format
        ex.notes.append(f"{pyz.name}: table of contents not readable by this Python ({sys.version.split()[0]})")
        return
    if isinstance(toc, dict):
        toc = list(toc.items())
    out.mkdir(parents=True, exist_ok=True)
    for item in toc:
        try:
            name, meta = item
            if isinstance(name, bytes):
                name = name.decode("utf-8", "replace")
            ispkg, pos, length = meta[0], meta[1], meta[2]
        except (TypeError, ValueError):
            continue
        blob = data[pos:pos + length]
        try:
            blob = zlib.decompress(blob)
        except zlib.error:
            ex.encrypted = True
            continue
        rel = name.replace(".", "/") + ("/__init__.pyc" if ispkg == 1 else ".pyc")
        dest = out / _safe_rel(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_pyc_header(magic) + blob)
        ex.modules[name] = dest
    if ex.encrypted:
        ex.notes.append("the PYZ archive is encrypted (PyInstaller --key); library modules were not extracted")


def extract_py2exe(path: Path, out: Path) -> Extracted:
    ex = Extracted()
    try:
        import pefile
        pe = pefile.PE(str(path))
        blob = None
        for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
            if entry.name is not None and str(entry.name) == "PYTHONSCRIPT":
                res = entry.directory.entries[0].directory.entries[0].data.struct
                blob = pe.get_data(res.OffsetToData, res.Size)
        pe.close()
    except Exception as e:  # noqa: BLE001
        ex.notes.append(f"py2exe resource not readable: {e}")
        return ex
    if blob is None:
        ex.notes.append("no PYTHONSCRIPT resource")
        return ex
    _magic_hdr, _opt, _unbuf, code_len = struct.unpack("<iiii", blob[:16])
    rest = blob[16:]
    end = rest.find(b"\0")
    code_blob = rest[end + 1:end + 1 + code_len] if code_len else rest[end + 1:]
    try:
        codes = marshal.loads(code_blob)
    except Exception:  # noqa: BLE001
        ex.notes.append("py2exe code objects were written by another Python version")
        return ex
    ex.version = sys.version_info[:2]
    ex.magic = _magic_for(ex.version)
    out.mkdir(parents=True, exist_ok=True)
    for co in codes if isinstance(codes, (list, tuple)) else [codes]:
        if isinstance(co, types.CodeType) and not co.co_filename.startswith("<"):
            name = Path(co.co_filename).stem or "main"
            if name.startswith("boot_common"):
                continue
            dest = out / f"{name}.pyc"
            dest.write_bytes(_pyc_header(ex.magic) + marshal.dumps(co))
            ex.scripts.append(dest)
    _extract_zip_lib(path, out, ex)
    return ex


def _extract_zip_lib(zip_path: Path, out: Path, ex: Extracted, main_hint: str = "") -> None:
    import zipfile
    try:
        z = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError):
        return
    with z:
        for n in z.namelist():
            if not n.endswith(".pyc"):
                continue
            dest = out / "_lib" / _safe_rel(n)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(n))
            mod = n[:-4].replace("/", ".").removesuffix(".__init__")
            ex.modules[mod] = dest
            if ex.magic is None:
                ex.magic = dest.read_bytes()[:4]
                ex.version = VERSION_BY_MAGIC.get(struct.unpack("<H", ex.magic[:2])[0])
            if mod.endswith("__main__") and (not main_hint or mod.lower().startswith(main_hint.lower())
                                             or mod == "__main__"):
                ex.scripts.append(dest)


def extract_cxfreeze(path: Path, out: Path) -> Extracted:
    ex = Extracted()
    for lib in (path.parent / "lib" / "library.zip", path.parent / "library.zip"):
        if lib.exists():
            _extract_zip_lib(lib, out, ex, path.stem)
            break
    else:
        ex.notes.append("library.zip not found next to the program (lib/library.zip)")
    return ex


# ============================================================================ interpreters & decompilers
def interpreter_for(version) -> str | None:
    """A Python executable of *version* (major, minor)."""
    if version is None:
        return None
    if tuple(sys.version_info[:2]) == tuple(version):
        return sys.executable
    py = shutil.which("py")
    if py:
        rc, out = run_tool([py, f"-{version[0]}.{version[1]}", "-c", "import sys; print(sys.executable)"],
                           timeout=30)
        if rc == 0 and out.strip() and Path(out.strip().splitlines()[-1]).exists():
            return out.strip().splitlines()[-1]
    for name in (f"python{version[0]}.{version[1]}", f"python{version[0]}{version[1]}"):
        p = shutil.which(name)
        if p:
            return p
    return None


def decompile_pyc(pyc: Path, version, out_py: Path, progress=None) -> tuple[str | None, str, list[str]]:
    """(source or None, tool used, notes)."""
    notes: list[str] = []
    pycdc = find_tool("pycdc")
    if pycdc:
        say(progress, f"Decompiling {pyc.name} with pycdc ...")
        rc, out = run_tool([pycdc, str(pyc)], timeout=300)
        if rc == 0 and out.strip() and _compiles(out):
            return out, "pycdc", notes
        notes.append("pycdc could not decompile it completely" + (f": {out.strip()[-200:]}" if out else ""))
    if version and tuple(version) <= (3, 8):
        for mod in ("decompyle3", "uncompyle6"):
            interp = interpreter_for(version) or sys.executable
            rc, out = run_tool([sys.executable, "-m", mod, str(pyc)], timeout=300)
            if rc == 0 and _compiles(out):
                return out, mod, notes
            if "No module named" in out:
                notes.append(f"{mod} is not installed (pip install {mod}) - it decompiles Python {version[0]}."
                             f"{version[1]} programs")
            del interp
    if version and (3, 11) <= tuple(version) <= (3, 13):
        interp = interpreter_for(version)
        if interp is None:
            notes.append(f"Python {version[0]}.{version[1]} is not installed - the built-in decompiler must run "
                         "on the program's Python version (install it from python.org, then retry)")
            return None, "", notes
        say(progress, f"Decompiling {pyc.name} (built-in decompiler, Python {version[0]}.{version[1]}) ...")
        if Path(interp).resolve() == Path(sys.executable).resolve():
            try:
                src, failed = decompile_file(pyc)
            except Exception as e:  # noqa: BLE001
                return None, "", notes + [f"built-in decompiler failed: {e}"]
        else:
            rc, log = run_tool([interp, "-I", __file__, "--decompile", str(pyc), str(out_py)], timeout=300)
            if rc != 0 or not out_py.exists():
                return None, "", notes + [f"built-in decompiler failed: {log[-300:]}"]
            src = out_py.read_text(encoding="utf-8")
            failed = re.findall(r"^\s*# DECOMPILE-FAILED: (\S+)", src, re.M)
        if failed:
            notes.append("functions kept as disassembly: " + ", ".join(failed))
        return src, "built-in decompiler", notes
    notes.append(f"no decompiler for Python {version[0]}.{version[1]} here - put pycdc.exe (Decompyle++) in "
                 "%LOCALAPPDATA%\\RADIDE\\tools" if version else "unknown Python version")
    return None, "", notes


def _compiles(src: str) -> bool:
    try:
        compile(src, "<decompiled>", "exec")
        return True
    except (SyntaxError, ValueError):
        return False


# ============================================================================ built-in decompiler (3.11-3.13)
class Unsupported(Exception):
    pass


class X:
    """An expression on the simulated stack."""
    __slots__ = ("code", "prec", "kind", "extra")

    def __init__(self, code, prec=20, kind="", extra=None):
        self.code, self.prec, self.kind, self.extra = code, prec, kind, extra

    def __repr__(self):
        return f"X({self.code!r})"


NULL = X("<NULL>", kind="null")
BIN_PREC = {"**": 14, "*": 12, "@": 12, "/": 12, "//": 12, "%": 12, "+": 11, "-": 11, "<<": 10, ">>": 10,
            "&": 9, "^": 8, "|": 7}
CMP_PREC = 6


def wrap(x: X, need: int, right=False) -> str:
    if x.prec < need or (right and x.prec == need):
        return f"({x.code})"
    return x.code


def const_repr(v) -> str:
    if isinstance(v, types.CodeType):
        return f"<code {v.co_name}>"
    if isinstance(v, frozenset):
        return "frozenset(" + repr(set(v)) + ")" if v else "frozenset()"
    if isinstance(v, float) and v != v:
        return "float('nan')"
    return repr(v)


class FuncDecompiler:
    def __init__(self, co: types.CodeType, top: "ModuleDecompiler", kind: str = "function"):
        self.co = co
        self.top = top
        self.kind = kind
        self.ins = [i for i in dis.get_instructions(co) if i.opname not in ("CACHE", "EXTENDED_ARG")]
        self.idx = {i.offset: k for k, i in enumerate(self.ins)}
        self.globals_written: set[str] = set()
        if co.co_exceptiontable:
            raise Unsupported("try/except/with")

    def index(self, offset) -> int:
        if offset in self.idx:
            return self.idx[offset]
        for k, i in enumerate(self.ins):
            if i.offset >= offset:
                return k
        return len(self.ins)

    # ------------------------------------------------------------------ blocks
    def run(self) -> list[str]:
        lines = self.block(0, len(self.ins), [], None)
        while lines and lines[-1].strip() in ("return None", "return"):
            lines.pop()
        return lines

    def block(self, start: int, end: int, stack: list, loop, no_loop_at: int | None = None) -> list[str]:
        """Statements of instructions [start, end).  loop = (head_offset, end_offset, kind) or None."""
        out: list[str] = []
        i = start
        while i < end:
            ins = self.ins[i]
            op = ins.opname
            # ---- while loops: an instruction targeted by a later JUMP_BACKWARD inside this block
            if ins.is_jump_target and op not in ("FOR_ITER",) and not stack and i != no_loop_at:
                got = self._try_while(i, end, out)
                if got is not None:
                    i = got
                    continue
            if op in ("RESUME", "NOP", "COPY_FREE_VARS", "MAKE_CELL", "PUSH_NULL", "TO_BOOL",
                      "NOT_TAKEN", "RETURN_GENERATOR"):
                if op == "PUSH_NULL":
                    stack.append(NULL)
                i += 1
                continue
            if op.startswith("POP_JUMP_IF") or op in ("POP_JUMP_FORWARD_IF_FALSE", "POP_JUMP_FORWARD_IF_TRUE",
                                                      "POP_JUMP_FORWARD_IF_NONE", "POP_JUMP_FORWARD_IF_NOT_NONE"):
                i = self._cond(i, end, stack, out, loop)
                continue
            if op in ("JUMP_FORWARD", "JUMP", "JUMP_NO_INTERRUPT") and ins.argval > ins.offset:
                if loop and ins.argval >= loop[1]:
                    if stack and stack[-1].kind == "iter":
                        stack.pop()
                    out.append("break")
                    i += 1
                    continue
                raise Unsupported(f"jump at {ins.offset}")
            if op in ("JUMP_BACKWARD", "JUMP_BACKWARD_NO_INTERRUPT", "JUMP", "JUMP_NO_INTERRUPT") and \
                    ins.argval <= ins.offset:
                if loop and (ins.argval == loop[0] or ins.argval in loop[3]):
                    if i != loop[4]:
                        out.append("continue")
                    i += 1
                    continue
                raise Unsupported(f"backward jump at {ins.offset}")
            if op == "GET_ITER":
                it = stack.pop()
                stack.append(X(it.code, it.prec, "iterable"))
                i += 1
                continue
            if op == "FOR_ITER":
                i = self._for(i, end, stack, out)
                continue
            stmt = self.step(ins, stack)
            if stmt is not None:
                out.extend(stmt if isinstance(stmt, list) else [stmt])
            i += 1
        return out

    def _try_while(self, i: int, end: int, out: list) -> int | None:
        """A while loop starting at instruction i, or None."""
        head = self.ins[i].offset
        # while <cond>:   head: cond; POP_JUMP_IF_x END; body...; cond; POP_JUMP_IF_x END; JUMP_BACKWARD body
        k = i
        while k < end and not self.ins[k].opname.startswith("POP_JUMP_IF") and k - i < 40:
            if self.ins[k].opname in ("STORE_FAST", "STORE_NAME", "STORE_GLOBAL", "STORE_ATTR", "POP_TOP",
                                      "RETURN_VALUE", "RETURN_CONST", "STORE_SUBSCR") or                     self.ins[k].opname.startswith("JUMP"):
                k = end
                break
            k += 1
        if k < end and self.ins[k].argval > self.ins[k].offset:
            t = self.index(self.ins[k].argval)
            if 0 < t <= end and self.ins[t - 1].opname.startswith("JUMP_BACKWARD") and                     self.ins[t - 1].argval in (head, self.ins[k + 1].offset):
                body_start = self.ins[k + 1].offset
                ncond = k - i + 1
                body_end = t - 1
                tail = self.ins[body_end - ncond:body_end]
                headc = self.ins[i:k + 1]
                if len(tail) == ncond and all(a.opname == b.opname and a.argval == b.argval
                                              for a, b in zip(tail, headc)):
                    body_end -= ncond
                elif self.ins[t - 1].argval != head:
                    return None
                stack: list = []
                pre = self.block(i, k, stack, None)
                if pre or len(stack) != 1:
                    return None
                cond = self._jump_cond(self.ins[k], stack.pop(), True)
                body = self.block(k + 1, body_end, [], (head, self.ins[t].offset if t < len(self.ins) else
                                                        self.ins[t - 1].offset + 2, "while", {body_start}, -1))
                out.append(f"while {cond}:")
                out.extend("    " + ln for ln in (body or ["pass"]))
                return t
        # while True:   head: body...; JUMP_BACKWARD head   (breaks jump past the loop)
        jb = None
        for q in range(i + 1, end):
            if self.ins[q].opname.startswith("JUMP_BACKWARD") and self.ins[q].argval == head:
                jb = q
        if jb is None:
            return None
        end_off = self.ins[jb + 1].offset if jb + 1 < len(self.ins) else self.ins[jb].offset + 2
        body = self.block(i, jb + 1, [], (head, end_off, "while", set(), jb), no_loop_at=i)
        out.append("while True:")
        out.extend("    " + ln for ln in (body or ["pass"]))
        return jb + 1

    def _jump_cond(self, ins, x: X, negate_to_run: bool) -> str:
        """Condition under which execution falls through (does NOT jump)."""
        op = ins.opname
        if "IF_NOT_NONE" in op:
            return f"{wrap(x, CMP_PREC)} is None"
        if "IF_NONE" in op:
            return f"{wrap(x, CMP_PREC)} is not None"
        if "IF_FALSE" in op:
            return x.code
        return self.negate(x)

    @staticmethod
    def negate(x: X) -> str:
        if x.kind == "not":
            return x.extra.code
        m = re.fullmatch(r"(.+?) (==|!=|is not|is|not in|in|<=|>=|<|>) (.+)", x.code)
        if m and x.prec == CMP_PREC and m.group(2) in ("==", "!=", "is", "is not", "in", "not in"):
            inv = {"==": "!=", "!=": "==", "is": "is not", "is not": "is", "in": "not in", "not in": "in"}
            return f"{m.group(1)} {inv[m.group(2)]} {m.group(3)}"
        return f"not {wrap(x, 5)}"

    def _chain(self, i, end, ins, cond, loop):
        """Merge 'if a and b' / 'if a or b' jump chains into one condition."""
        target = self.index(ins.argval)
        while True:
            k = i + 1
            while k < end and not self.ins[k].opname.startswith("POP_JUMP_IF"):
                if self.ins[k].opname.startswith(("STORE", "JUMP", "RETURN", "FOR_ITER", "POP_TOP")) or                         self.ins[k].is_jump_target and k != i + 1:
                    return cond, i, ins, target
                k += 1
            if k >= end or k == i + 1:
                return cond, i, ins, target
            st: list = []
            try:
                pre = self.block(i + 1, k, st, loop)
            except (Unsupported, IndexError):
                return cond, i, ins, target
            if pre or len(st) != 1:
                return cond, i, ins, target
            nxt = self.ins[k]
            c2 = self._jump_cond(nxt, st[0], True)
            p = lambda c: f"({c})" if " or " in c else c   # noqa: E731
            if nxt.argval == ins.argval:                       # a and b: both skip the body
                cond = f"{p(cond)} and {p(c2)}"
            elif ins.argval == self.ins[k + 1].offset if k + 1 < len(self.ins) else False:
                # a or b: the first jump goes straight into the body when a is true
                first = self._negate_text(cond)
                cond = f"{first} or {c2}"
            else:
                return cond, i, ins, target
            i, ins, target = k, nxt, self.index(nxt.argval)

    @staticmethod
    def _negate_text(c: str) -> str:
        if c.startswith("not ") and " and " not in c and " or " not in c:
            return c[4:]
        return f"not ({c})"

    def _cond(self, i: int, end: int, stack: list, out: list, loop) -> int:
        ins = self.ins[i]
        x = stack.pop()
        target = self.index(ins.argval)
        # a and b / a or b (value kept: COPY 1 before the jump, POP_TOP after it)
        if x.kind == "copy" and i + 1 < end and self.ins[i + 1].opname == "POP_TOP":
            sub: list = []
            pre = self.block(i + 2, target, sub, loop)
            if pre or len(sub) != 1:
                raise Unsupported("boolean expression")
            opname = "and" if "FALSE" in ins.opname else "or"
            prec = 4 if opname == "and" else 3
            stack.pop()                       # the original value under the copy
            stack.append(X(f"{wrap(x.extra, prec)} {opname} {wrap(sub[0], prec, True)}", prec))
            return target
        if ins.argval < ins.offset:
            raise Unsupported("backward conditional jump")
        cond = self._jump_cond(ins, x, True)
        if not stack:
            cond, i, ins, target = self._chain(i, end, ins, cond, loop)
        body_end = target
        else_end = None
        last = self.ins[target - 1] if target - 1 > i else None
        if last is not None and last.opname in ("JUMP_FORWARD", "JUMP", "JUMP_NO_INTERRUPT") and \
                last.argval > last.offset and not (loop and last.argval >= loop[1]):
            else_end = self.index(last.argval)
            body_end = target - 1
        # ternary: body leaves one value and no statements
        if else_end is not None:
            s1: list = list(stack)
            try:
                b1 = self.block(i + 1, body_end, s1, loop)
            except Unsupported:
                b1 = None
            if b1 == [] and len(s1) == len(stack) + 1:
                s2: list = list(stack)
                b2 = self.block(target, else_end, s2, loop)
                if b2 == [] and len(s2) == len(stack) + 1:
                    stack.append(X(f"{wrap(s1[-1], 2)} if {cond} else {wrap(s2[-1], 1)}", 1))
                    return else_end
        body = self.block(i + 1, body_end, [s for s in stack if s.kind == "iter"], loop)
        if else_end is not None:
            other = self.block(target, min(else_end, end), [s for s in stack if s.kind == "iter"], loop)
            out.append(f"if {cond}:")
            out.extend("    " + ln for ln in (body or ["pass"]))
            if len(other) >= 1 and other[0].startswith("if ") and not any(
                    ln.startswith(("else:", "elif ")) is False and not ln.startswith(" ") and ln != other[0]
                    and not ln.startswith(("elif ", "else:")) for ln in other[1:]):
                out.append("el" + other[0])
                out.extend(other[1:])
            else:
                out.append("else:")
                out.extend("    " + ln for ln in (other or ["pass"]))
            return min(else_end, end)
        out.append(f"if {cond}:")
        out.extend("    " + ln for ln in (body or ["pass"]))
        return target

    def _for(self, i: int, end: int, stack: list, out: list) -> int:
        ins = self.ins[i]
        it = stack.pop()
        end_idx = self.index(ins.argval)
        # loop variable(s)
        k = i + 1
        target, k = self._store_target(k)
        loop_end_off = ins.argval
        # 3.12: FOR_ITER -> END_FOR (pops 2); 3.13: END_FOR + POP_TOP / POP_ITER
        after = end_idx
        while after < len(self.ins) and self.ins[after].opname in ("END_FOR", "POP_TOP", "POP_ITER") and \
                after < end_idx + 2:
            after += 1
        last = end_idx - 1
        body = self.block(k, last + 1, [X("<iter>", kind="iter")], (ins.offset, self.ins[after].offset
                                                                     if after < len(self.ins) else loop_end_off + 4,
                                                                     "for", set(), last))
        out.append(f"for {target} in {it.code}:")
        out.extend("    " + ln for ln in (body or ["pass"]))
        return after

    def _store_target(self, k: int) -> tuple[str, int]:
        ins = self.ins[k]
        if ins.opname in ("STORE_FAST", "STORE_NAME", "STORE_GLOBAL", "STORE_DEREF"):
            if ins.opname == "STORE_GLOBAL":
                self.globals_written.add(ins.argval)
            return ins.argval, k + 1
        if ins.opname == "UNPACK_SEQUENCE":
            names = []
            k += 1
            for _ in range(ins.arg):
                n, k = self._store_target(k)
                names.append(n)
            return ", ".join(names), k
        if ins.opname == "STORE_FAST_STORE_FAST":
            a, b = ins.argval
            return f"{a}, {b}", k + 1
        raise Unsupported(f"loop target {ins.opname}")

    # ------------------------------------------------------------------ one instruction
    def step(self, ins, st: list):
        op, arg, val = ins.opname, ins.arg, ins.argval
        if op in ("LOAD_CONST", "RETURN_CONST", "LOAD_SMALL_INT"):
            if isinstance(val, types.CodeType):
                st.append(X(val.co_name, kind="code", extra=val))
            else:
                st.append(X(const_repr(val), 20 if not isinstance(val, (int, float)) or val >= 0 else 13))
            if op == "RETURN_CONST":
                return self._return(st.pop())
            return None
        if op in ("LOAD_FAST", "LOAD_FAST_CHECK", "LOAD_FAST_BORROW", "LOAD_NAME", "LOAD_DEREF", "LOAD_CLASSDEREF",
                  "LOAD_FROM_DICT_OR_DEREF", "LOAD_FROM_DICT_OR_GLOBALS", "LOAD_CLOSURE", "LOAD_FAST_AND_CLEAR"):
            if op == "LOAD_FAST_AND_CLEAR":
                raise Unsupported("comprehension")
            st.append(X(val))
            return None
        if op in ("LOAD_FAST_LOAD_FAST", "LOAD_FAST_BORROW_LOAD_FAST_BORROW"):
            st.append(X(val[0]))
            st.append(X(val[1]))
            return None
        if op == "LOAD_GLOBAL":
            if ins.argrepr.startswith("NULL"):
                if sys.version_info >= (3, 13):
                    st.append(X(val))
                    st.append(NULL)
                else:
                    st.append(NULL)
                    st.append(X(val))
            else:
                st.append(X(val))
            return None
        if op == "LOAD_ATTR":
            obj = st.pop()
            code = f"{wrap(obj, 20)}.{val}"
            if ins.argrepr.startswith("NULL|self") or (arg is not None and arg & 1 and sys.version_info >= (3, 12)):
                st.append(X(code))
                st.append(NULL)
            else:
                st.append(X(code))
            return None
        if op == "LOAD_METHOD":
            obj = st.pop()
            st.append(NULL)
            st.append(X(f"{wrap(obj, 20)}.{val}"))
            return None
        if op == "LOAD_SUPER_ATTR":
            st.pop()
            st.pop()
            st.pop()
            st.append(X(f"super().{val}"))
            if arg & 1:
                st.append(NULL)
            return None
        if op in ("STORE_FAST", "STORE_NAME", "STORE_GLOBAL", "STORE_DEREF"):
            v = st.pop()
            if op == "STORE_GLOBAL":
                self.globals_written.add(val)
            return self._assign(val, v)
        if op == "STORE_FAST_STORE_FAST":
            a, b = st.pop(), st.pop()
            return [self._assign(val[0], a), self._assign(val[1], b)]
        if op == "STORE_FAST_LOAD_FAST":
            line = self._assign(val[0], st.pop())
            st.append(X(val[1]))
            return line
        if op == "STORE_ATTR":
            obj = st.pop()
            v = st.pop()
            return self._assign(f"{wrap(obj, 20)}.{val}", v)
        if op == "STORE_SUBSCR":
            key = st.pop()
            obj = st.pop()
            v = st.pop()
            return self._assign(f"{wrap(obj, 20)}[{key.code}]", v)
        if op == "STORE_SLICE":
            stop, start, obj, v = st.pop(), st.pop(), st.pop(), st.pop()
            return f"{wrap(obj, 20)}[{self._slice_part(start)}:{self._slice_part(stop)}] = {v.code}"
        if op in ("DELETE_FAST", "DELETE_NAME", "DELETE_GLOBAL"):
            return f"del {val}"
        if op == "DELETE_ATTR":
            return f"del {wrap(st.pop(), 20)}.{val}"
        if op == "DELETE_SUBSCR":
            key = st.pop()
            obj = st.pop()
            return f"del {wrap(obj, 20)}[{key.code}]"
        if op == "POP_TOP":
            v = st.pop()
            if v.kind in ("iter", "null"):
                return None
            if v.kind == "import":
                return None
            return v.code
        if op == "COPY":
            src = st[-arg]
            st.append(X(src.code, src.prec, "copy", src))
            return None
        if op == "SWAP":
            st[-1], st[-arg] = st[-arg], st[-1]
            return None
        if op in ("RETURN_VALUE",):
            return self._return(st.pop())
        if op == "BINARY_OP":
            b, a = st.pop(), st.pop()
            sym = ins.argrepr
            if sym.endswith("=") and sym not in ("==",):
                st.append(X(f"{a.code} {sym} {b.code}", 0, "aug", (a, sym, b)))
                return None
            p = BIN_PREC.get(sym, 11)
            if sym == "**":
                st.append(X(f"{wrap(a, p + 1)} ** {wrap(b, p)}", p))
            else:
                st.append(X(f"{wrap(a, p)} {sym} {wrap(b, p, True)}", p))
            return None
        if op in ("BINARY_SUBSCR",):
            key, obj = st.pop(), st.pop()
            st.append(X(f"{wrap(obj, 20)}[{key.code}]"))
            return None
        if op == "BINARY_SLICE":
            stop, start, obj = st.pop(), st.pop(), st.pop()
            st.append(X(f"{wrap(obj, 20)}[{self._slice_part(start)}:{self._slice_part(stop)}]"))
            return None
        if op == "BUILD_SLICE":
            parts = [st.pop() for _ in range(arg)][::-1]
            st.append(X(":".join(self._slice_part(p) for p in parts), kind="slice"))
            return None
        if op == "COMPARE_OP":
            b, a = st.pop(), st.pop()
            sym = ins.argrepr.replace("bool(", "").rstrip(")")
            st.append(X(f"{wrap(a, CMP_PREC + 1)} {sym} {wrap(b, CMP_PREC + 1)}", CMP_PREC))
            return None
        if op == "IS_OP":
            b, a = st.pop(), st.pop()
            st.append(X(f"{wrap(a, CMP_PREC + 1)} {'is not' if arg else 'is'} {wrap(b, CMP_PREC + 1)}", CMP_PREC))
            return None
        if op == "CONTAINS_OP":
            b, a = st.pop(), st.pop()
            st.append(X(f"{wrap(a, CMP_PREC + 1)} {'not in' if arg else 'in'} {wrap(b, CMP_PREC + 1)}", CMP_PREC))
            return None
        if op == "UNARY_NOT":
            a = st.pop()
            st.append(X(f"not {wrap(a, 5)}", 5, "not", a))
            return None
        if op == "UNARY_NEGATIVE":
            a = st.pop()
            st.append(X(f"-{wrap(a, 13)}", 13))
            return None
        if op == "UNARY_INVERT":
            a = st.pop()
            st.append(X(f"~{wrap(a, 13)}", 13))
            return None
        if op in ("BUILD_LIST", "BUILD_TUPLE", "BUILD_SET"):
            items = [st.pop() for _ in range(arg)][::-1]
            body = ", ".join(x.code for x in items)
            if op == "BUILD_LIST":
                st.append(X(f"[{body}]", kind="list"))
            elif op == "BUILD_TUPLE":
                st.append(X(f"({body}{',' if len(items) == 1 else ''})", kind="tuple"))
            else:
                st.append(X("{" + body + "}" if items else "set()"))
            return None
        if op in ("LIST_EXTEND", "SET_UPDATE"):
            seq = st.pop()
            base = st[-arg]
            inner = seq.code
            if seq.code.startswith("(") and seq.code.endswith(")"):
                inner = seq.code[1:-1].rstrip(",")
            elif seq.code.startswith("frozenset("):
                inner = seq.code[len("frozenset({"):-2]
            else:
                inner = "*" + wrap(seq, 20)
            b = base.code[1:-1]
            st[-arg] = X(("[" if op == "LIST_EXTEND" else "{") + (b + ", " if b else "") + inner +
                         ("]" if op == "LIST_EXTEND" else "}"), kind=base.kind)
            return None
        if op == "LIST_TO_TUPLE":
            x = st.pop()
            st.append(X("(" + x.code[1:-1] + ("," if x.code.count(",") == 0 and x.code != "[]" else "") + ")"))
            return None
        if op == "BUILD_MAP":
            items = [st.pop() for _ in range(2 * arg)][::-1]
            pairs = [f"{items[j].code}: {items[j + 1].code}" for j in range(0, len(items), 2)]
            st.append(X("{" + ", ".join(pairs) + "}", kind="dict"))
            return None
        if op == "BUILD_CONST_KEY_MAP":
            keys = st.pop()
            vals = [st.pop() for _ in range(arg)][::-1]
            knames = eval(keys.code)          # a tuple constant
            st.append(X("{" + ", ".join(f"{k!r}: {v.code}" for k, v in zip(knames, vals)) + "}", kind="dict"))
            return None
        if op == "DICT_UPDATE" or op == "DICT_MERGE":
            other = st.pop()
            base = st[-arg]
            b = base.code[1:-1]
            st[-arg] = X("{" + (b + ", " if b else "") + "**" + wrap(other, 20) + "}", kind="dict")
            return None
        if op == "MAP_ADD":
            raise Unsupported("dict comprehension")
        if op in ("LIST_APPEND", "SET_ADD"):
            raise Unsupported("comprehension")
        if op == "FORMAT_VALUE":
            spec = st.pop() if (arg & 0x04) else None
            v = st.pop()
            conv = {0: "", 1: "!s", 2: "!r", 3: "!a"}[arg & 3]
            st.append(X("", kind="fpart", extra=(v, conv, spec)))
            return None
        if op in ("FORMAT_SIMPLE", "FORMAT_WITH_SPEC", "CONVERT_VALUE"):
            if op == "CONVERT_VALUE":
                v = st.pop()
                st.append(X(v.code, v.prec, "conv", (v, {1: "!s", 2: "!r", 3: "!a"}.get(arg, ""))))
                return None
            spec = st.pop() if op == "FORMAT_WITH_SPEC" else None
            v = st.pop()
            conv = ""
            if v.kind == "conv":
                v, conv = v.extra
            st.append(X("", kind="fpart", extra=(v, conv, spec)))
            return None
        if op == "BUILD_STRING":
            parts = [st.pop() for _ in range(arg)][::-1]
            st.append(X(self._fstring(parts)))
            return None
        if op == "KW_NAMES":
            self._kw = val
            return None
        if op in ("CALL", "CALL_KW", "PRECALL", "CALL_FUNCTION_EX"):
            if op == "PRECALL":
                return None
            return self._call(ins, st)
        if op == "MAKE_FUNCTION":
            code = st.pop()
            fn = X(code.code, kind="func", extra={"code": code.extra, "defaults": None, "kwdefaults": None})
            if sys.version_info < (3, 13):
                if arg & 0x08:
                    st.pop()                         # closure
                if arg & 0x04:
                    st.pop()                         # annotations
                if arg & 0x02:
                    fn.extra["kwdefaults"] = st.pop()
                if arg & 0x01:
                    fn.extra["defaults"] = st.pop()
            st.append(self._function_value(fn))
            return None
        if op == "SET_FUNCTION_ATTRIBUTE":
            fn = st.pop()
            v = st.pop()
            if arg == 0x01:
                fn.extra["defaults"] = v
            elif arg == 0x02:
                fn.extra["kwdefaults"] = v
            st.append(self._function_value(fn))
            return None
        if op == "LOAD_BUILD_CLASS":
            st.append(X("__build_class__", kind="buildclass"))
            return None
        if op == "IMPORT_NAME":
            fromlist = st.pop()
            level = st.pop()
            lvl = int(level.code) if level.code.isdigit() else 0
            st.append(X(val, kind="import", extra={"name": val, "level": lvl, "fromlist": fromlist.code,
                                                  "items": []}))
            return None
        if op == "IMPORT_FROM":
            mod = st[-1]
            st.append(X(val, kind="importfrom", extra=(mod, val)))
            return None
        if op == "CALL_INTRINSIC_1":
            if ins.argrepr == "INTRINSIC_IMPORT_STAR":
                mod = st.pop()
                return f"from {'.' * mod.extra['level']}{mod.extra['name']} import *"
            if ins.argrepr == "INTRINSIC_UNARY_POSITIVE":
                a = st.pop()
                st.append(X(f"+{wrap(a, 13)}", 13))
                return None
            if ins.argrepr == "INTRINSIC_LIST_TO_TUPLE":
                x = st.pop()
                st.append(X("tuple(" + x.code + ")"))
                return None
            raise Unsupported(ins.argrepr)
        if op == "UNPACK_SEQUENCE":
            raise Unsupported("tuple unpacking")
        if op in ("RAISE_VARARGS",):
            if arg == 0:
                return "raise"
            exc = st.pop() if arg >= 1 else None
            return f"raise {exc.code}"
        if op in ("GET_AWAITABLE", "YIELD_VALUE", "SEND", "SETUP_ANNOTATIONS", "BEFORE_WITH", "PUSH_EXC_INFO",
                  "LOAD_ASSERTION_ERROR"):
            raise Unsupported(op)
        raise Unsupported(op)

    def _slice_part(self, x: X) -> str:
        return "" if x.code == "None" else x.code

    def _fstring(self, parts) -> str:
        out = []
        for p in parts:
            if p.kind == "fpart":
                v, conv, spec = p.extra
                inner = v.code
                if inner.startswith("{"):
                    inner = " " + inner
                s = ""
                if spec is not None:
                    s = ":" + (eval(spec.code) if spec.code[:1] in "'\"" else spec.code)
                out.append("{" + inner + conv + s + "}")
            else:
                try:
                    lit = eval(p.code)
                except Exception:  # noqa: BLE001
                    lit = p.code
                out.append(str(lit).replace("{", "{{").replace("}", "}}"))
        body = "".join(out)
        q = '"' if '"' not in body else "'"
        body = body.replace("\\", "\\\\").replace("\n", "\\n")
        return f"f{q}{body}{q}"

    def _assign(self, target: str, v: X) -> str | list[str]:
        if v.kind == "aug":
            a, sym, b = v.extra
            if a.code == target:
                return f"{target} {sym} {b.code}"
            return f"{target} = {a.code} {sym[:-1]} {b.code}"
        if v.kind == "import":
            info = v.extra
            name = info["name"]
            dots = "." * info["level"]
            if target == name.split(".")[0] and not dots:
                return f"import {name}"
            return f"import {dots}{name} as {target}" if not dots else f"from {dots} import {name} as {target}"
        if v.kind == "importfrom":
            mod, item = v.extra
            imp = mod.extra
            return f"from {'.' * imp['level']}{imp['name']} import {item if item == target else item + ' as ' + target}"
        if v.kind == "func":
            return self._def_lines(target, v)
        if v.kind == "class":
            return self._class_lines(target, v)
        return f"{target} = {v.code}"

    def _return(self, v: X):
        if self.kind == "lambda":
            self.lambda_value = v.code
            return None
        if v.code == "None":
            return "return None"
        return f"return {v.code}"

    def _function_value(self, fn: X) -> X:
        co = fn.extra["code"]
        if co.co_name == "<lambda>":
            return X(f"lambda{self.top.signature(co, fn.extra, lambda_=True)}: "
                     f"{self.top.lambda_body(co)}", 0, "lambda")
        if co.co_name in ("<genexpr>", "<listcomp>", "<setcomp>", "<dictcomp>"):
            return X(co.co_name, kind="genexpr", extra=co)
        if co.co_name.startswith("<"):
            raise Unsupported(co.co_name)
        return fn

    def _def_lines(self, name: str, fn: X) -> list[str]:
        co = fn.extra["code"]
        sig = self.top.signature(co, fn.extra)
        body = self.top.function_body(co)
        return [f"def {name}({sig}):"] + ["    " + ln for ln in body] + [""]

    def _class_lines(self, name: str, cls: X) -> list[str]:
        co, bases = cls.extra
        body = self.top.class_body(co)
        b = f"({', '.join(bases)})" if bases else ""
        return [f"class {name}{b}:"] + ["    " + ln for ln in body] + [""]

    def _call(self, ins, st: list):
        op = ins.opname
        if op == "CALL_FUNCTION_EX":
            kwargs = st.pop() if ins.arg & 1 else None
            args = st.pop()
            func = st.pop()
            if st and st[-1] is NULL:
                st.pop()
            parts = []
            if args.code not in ("()",):
                parts.append("*" + wrap(args, 20))
            if kwargs is not None:
                parts.append("**" + wrap(kwargs, 20))
            st.append(X(f"{wrap(func, 20)}({', '.join(parts)})"))
            return None
        n = ins.arg
        kw = ()
        if op == "CALL_KW":
            kw = eval(st.pop().code)
        elif getattr(self, "_kw", None):
            kw = self._kw
            self._kw = None
        args = [st.pop() for _ in range(n)][::-1]
        # 3.12: [NULL, func] or [func, self]; 3.13: [func, NULL] or [func, self]
        a, b = st.pop(), st.pop()
        if sys.version_info >= (3, 13):
            func, selfx = b, a
        else:
            func, selfx = (a, None) if b is NULL else (b, a)
            if b is not NULL:
                func, selfx = b, a
        if func is NULL:
            func, selfx = selfx, None
        if selfx is not None and selfx is not NULL and func.kind != "buildclass":
            args = [selfx] + args           # unbound call through the method slot
            if func.code.endswith("." + func.code.split(".")[-1]):
                args = args[1:]             # obj.method(...) - the bound object is not an argument
        if func.kind == "buildclass":
            code = args[0].extra["code"]
            name = eval(args[1].code)
            bases = [x.code for x in args[2:len(args) - len(kw)]] + \
                [f"{k}={v.code}" for k, v in zip(kw, args[len(args) - len(kw):])]
            st.append(X(name, kind="class", extra=(code, bases)))
            return None
        if func.kind == "genexpr" and len(args) == 1:
            st.append(X(self.top.genexpr(func.extra, args[0])))
            return None
        pos = args[:len(args) - len(kw)] if kw else args
        kws = args[len(args) - len(kw):] if kw else []
        parts = [x.code for x in pos] + [f"{k}={v.code}" for k, v in zip(kw, kws)]
        st.append(X(f"{wrap(func, 20)}({', '.join(parts)})"))
        return None


class ModuleDecompiler:
    def __init__(self):
        self.failed: list[str] = []

    def module(self, co: types.CodeType) -> str:
        try:
            lines = self.body(co, "module")
        except Exception as e:  # noqa: BLE001 - any bytecode pattern we do not rebuild
            # module level not rebuildable: keep its functions and a disassembly
            self.failed.append("<module>")
            lines = [f"# DECOMPILE-FAILED: <module> ({e})"] + self._dis_comment(co)
            for c in co.co_consts:
                if isinstance(c, types.CodeType) and c.co_name != "<lambda>":
                    try:
                        lines += [f"def {c.co_name}({self.signature(c, {})}):"] + \
                            ["    " + ln for ln in self.function_body(c)] + [""]
                    except Exception:  # noqa: BLE001
                        pass
        return "\n".join(self._merge_imports(lines)).rstrip() + "\n"

    def body(self, co, kind) -> list[str]:
        fd = FuncDecompiler(co, self, kind)
        lines = fd.run()
        flat = []
        for ln in lines:
            if isinstance(ln, list):
                flat += ln
            else:
                flat.append(ln)
        if kind == "function" and fd.globals_written:
            flat.insert(0, "global " + ", ".join(sorted(fd.globals_written)))
        return flat

    def function_body(self, co) -> list[str]:
        try:
            lines = self.body(co, "function")
            lines = self._merge_imports(lines)
            return lines or ["pass"]
        except Exception as e:  # noqa: BLE001
            self.failed.append(co.co_qualname if hasattr(co, "co_qualname") else co.co_name)
            return [f"# DECOMPILE-FAILED: {co.co_name} ({e}) - disassembly:"] + self._dis_comment(co) + \
                ["raise NotImplementedError(" + repr(f"{co.co_name} could not be decompiled") + ")"]

    def class_body(self, co) -> list[str]:
        try:
            lines = self.body(co, "class")
        except Exception as e:  # noqa: BLE001
            self.failed.append(co.co_name)
            return [f"# DECOMPILE-FAILED: class body ({e})", "pass"]
        out = []
        for ln in lines:
            if isinstance(ln, str) and re.match(r"(__module__|__qualname__|__firstlineno__|__static_attributes__|"
                                                r"__classcell__)\s*=", ln):
                continue
            if isinstance(ln, str) and ln.startswith("return "):
                continue
            out.append(ln)
        return self._merge_imports(out) or ["pass"]

    def genexpr(self, co, iterable: X) -> str:
        """(elt for x in it if cond) from a <genexpr>/<listcomp> code object."""
        fd = FuncDecompiler(co, self, "genexpr")
        ins = fd.ins
        fi = [k for k, i in enumerate(ins) if i.opname == "FOR_ITER"]
        if len(fi) != 1:
            raise Unsupported("nested comprehension")
        target, k = fd._store_target(fi[0] + 1)
        stop = next((j for j in range(k, len(ins)) if ins[j].opname in ("YIELD_VALUE", "LIST_APPEND", "SET_ADD",
                                                                          "MAP_ADD")), None)
        if stop is None:
            raise Unsupported("comprehension")
        conds, seg = [], k
        for j in range(k, stop):
            if ins[j].opname.startswith("POP_JUMP_IF"):
                st: list = []
                if fd.block(seg, j, st, None) or len(st) != 1:
                    raise Unsupported("comprehension condition")
                conds.append(fd._jump_cond(ins[j], st[0], True))
                seg = j + 1
        st = []
        if fd.block(seg, stop, st, None):
            raise Unsupported("comprehension element")
        if ins[stop].opname == "MAP_ADD":
            if len(st) != 2:
                raise Unsupported("dict comprehension")
            elt = f"{st[0].code}: {st[1].code}"
        else:
            if len(st) != 1:
                raise Unsupported("comprehension element")
            elt = st[0].code
        it = iterable.code
        if it.startswith("iter(") and it.endswith(")"):
            it = it[5:-1]
        body = f"{elt} for {target} in {it}" + "".join(f" if {c}" for c in conds)
        opn, cls = {"<genexpr>": ("(", ")"), "<listcomp>": ("[", "]"), "<setcomp>": ("{", "}"),
                    "<dictcomp>": ("{", "}")}[co.co_name]
        return opn + body + cls

    def lambda_body(self, co) -> str:
        fd = FuncDecompiler(co, self, "lambda")
        fd.lambda_value = None
        lines = fd.block(0, len(fd.ins), [], None)
        if fd.lambda_value is None or lines:
            raise Unsupported("lambda")
        return fd.lambda_value

    def signature(self, co, extra, lambda_=False) -> str:
        n = co.co_argcount
        kwonly = co.co_kwonlyargcount
        names = list(co.co_varnames)
        pos = names[:n]
        defaults = []
        d = extra.get("defaults") if extra else None
        if d is not None:
            txt = d.code
            try:
                defaults = [repr(x) for x in eval(txt)] if txt.startswith("(") and "lambda" not in txt and \
                    "<" not in txt else _split_tuple(txt)
            except Exception:  # noqa: BLE001
                defaults = _split_tuple(txt)
        parts = []
        for k, name in enumerate(pos):
            j = k - (n - len(defaults))
            parts.append(f"{name}={defaults[j]}" if j >= 0 else name)
        idx = n
        flags = co.co_flags
        if flags & 0x04:
            parts.append("*" + names[n + kwonly])
        elif kwonly:
            parts.append("*")
        kwd = {}
        kd = extra.get("kwdefaults") if extra else None
        if kd is not None and kd.code.startswith("{"):
            try:
                kwd = eval(kd.code)
            except Exception:  # noqa: BLE001
                kwd = {}
        for name in names[idx:idx + kwonly]:
            parts.append(f"{name}={kwd[name]!r}" if name in kwd else name)
        if flags & 0x08:
            parts.append("**" + names[n + kwonly + (1 if flags & 0x04 else 0)])
        s = ", ".join(parts)
        return (" " + s if s else "") if lambda_ else s

    @staticmethod
    def _dis_comment(co) -> list[str]:
        out = []
        for ins in dis.get_instructions(co):
            if ins.opname in ("CACHE", "RESUME"):
                continue
            out.append(f"#   {ins.offset:4} {ins.opname:<20} {ins.argrepr}")
        return out[:400]

    @staticmethod
    def _merge_imports(lines) -> list[str]:
        """Join consecutive 'from X import a' lines of the same module."""
        final: list[str] = []
        for ln in lines:
            m = re.match(r"from (\S+) import (.+)$", ln)
            if m and final:
                pm = re.match(r"from (\S+) import (.+)$", final[-1])
                if pm and pm.group(1) == m.group(1) and m.group(2) != "*" and pm.group(2) != "*":
                    final[-1] = f"from {m.group(1)} import {pm.group(2)}, {m.group(2)}"
                    continue
            final.append(ln)
        return final


def _split_tuple(txt: str) -> list[str]:
    inner = txt.strip()
    if inner.startswith("(") and inner.endswith(")"):
        inner = inner[1:-1]
    parts, depth, cur = [], 0, ""
    for ch in inner:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def decompile_code(co: types.CodeType) -> tuple[str, list[str]]:
    md = ModuleDecompiler()
    src = md.module(co)
    return src, md.failed


def decompile_file(pyc: Path) -> tuple[str, list[str]]:
    data = Path(pyc).read_bytes()
    co = marshal.loads(data[16:])
    return decompile_code(co)


# ============================================================================ backend API
def can_handle(info) -> bool:
    return getattr(info, "kind", "") in ("pyinstaller", "py2exe", "cxfreeze")


def _user_modules(ex: Extracted) -> list[str]:
    std = set(getattr(sys, "stdlib_module_names", ()))
    out = []
    for name in ex.modules:
        top = name.split(".")[0]
        if top in std or top.startswith("_") or top.startswith(STD_PREFIXES) or name in ("__main__",):
            continue
        out.append(name)
    return sorted(out)


def run(path, info, workdir, progress=None, ai_translate: bool = False):
    path, workdir = Path(path), Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    res = ImportResult()
    kind = getattr(info, "kind", "")
    say(progress, f"Extracting the {kind} archive ...")
    xdir = workdir / "extracted"
    if kind == "pyinstaller":
        ex = extract_pyinstaller(path, xdir)
    elif kind == "py2exe":
        ex = extract_py2exe(path, xdir)
    else:
        ex = extract_cxfreeze(path, xdir)
    for n in ex.notes:
        res.add("warn", n)
    if not ex.scripts:
        res.add("error", "No Python entry script found in the program.")
        return res
    ver = ex.version
    vtxt = f"{ver[0]}.{ver[1]}" if ver else "?"
    res.resources["python_version"] = vtxt
    res.add("exact", f"Extracted {len(ex.scripts)} entry script(s), {len(ex.modules)} module(s) and "
                     f"{len(ex.files)} data file(s) (Python {vtxt}).")
    src_dir = workdir / "python"
    src_dir.mkdir(parents=True, exist_ok=True)
    res.source_dir = src_dir
    main_src = None
    main_name = ""
    scripts = sorted(ex.scripts, key=lambda p: (p.stem.lower() != path.stem.lower(), p.stem))
    for pyc in scripts:
        name = re.sub(r"\W", "_", pyc.stem.replace("__main__", "").strip("_")) or path.stem
        src, tool, notes = decompile_pyc(pyc, ver, src_dir / f"{name}.py", progress)
        for n in notes:
            res.add("warn", n)
        if src is None:
            res.add("missing", f"{pyc.name}: could not be decompiled.")
            continue
        failed = re.findall(r"^\s*# DECOMPILE-FAILED: (\S+)", src, re.M)
        (src_dir / f"{name}.py").write_text(src, encoding="utf-8")
        res.add("exact" if not failed else "rules",
                f"{name}.py: source rebuilt with {tool}" + (f" ({len(failed)} part(s) kept as disassembly)"
                                                            if failed else ""))
        if main_src is None:
            main_src, main_name = src, name
    # the program's own modules (not the standard library / well-known packages)
    for mod in _user_modules(ex)[:40]:
        pyc = ex.modules[mod]
        rel = mod.replace(".", "/") + ".py"
        src, tool, _notes = decompile_pyc(pyc, ver, src_dir / rel, None)
        if src:
            (src_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            (src_dir / rel).write_text(src, encoding="utf-8")
            res.modules.append((rel, src, "python"))
            res.add("exact", f"module {mod}: source rebuilt ({tool})")
        else:
            res.add("missing", f"module {mod}: not decompiled")
    if main_src is None:
        return res
    if ai_translate and "# DECOMPILE-FAILED" in main_src:
        new, who = ai_rewrite(main_src, "Python with some functions given only as CPython bytecode disassembly "
                                        "(in comments)",
                              "Rebuild the functions marked DECOMPILE-FAILED from their disassembly; keep the rest.",
                              progress)
        if new and _compiles(new):
            main_src = new
            (src_dir / f"{main_name}.py").write_text(main_src, encoding="utf-8")
            res.add("ai", f"{main_name}.py: functions rebuilt from bytecode by AI ({who}).")
        else:
            res.add("warn", f"AI rebuild not used - {who}")
    return _to_project(src_dir / f"{main_name}.py", main_src, res, workdir, progress)


def _to_project(script: Path, source: str, res, workdir: Path, progress):
    """Run the existing Python importer on the recovered source and copy its forms/code into *res*."""
    from ..python_import import detect_toolkit, import_python_program
    toolkit = detect_toolkit(source)
    if not toolkit:
        res.modules.insert(0, (script.name, source, "python"))
        res.resources["startup"] = ""
        res.add("info", "No Tkinter/Qt window code found: the program becomes a Python module (console program "
                        "or another GUI toolkit).")
        return res
    say(progress, "Capturing the program's windows (Python importer) ...")
    dest = workdir / "pyproject"
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    rep = import_python_program(script, dest, sys.executable)
    for w in rep.warnings:
        res.add("warn", w)
    if rep.project is None:
        res.modules.insert(0, (script.name, source, "python"))
        res.add("missing", "The windows could not be captured - the recovered source is kept as a module.")
        return res
    proj = rep.project
    from ...languages import get_plugin
    plugin = get_plugin(proj.language)
    for fname in proj.forms:
        fd = __import__("json").loads((dest / f"{fname}.form").read_text(encoding="utf-8"))
        res.forms.append((fname, fd))
        code_path = dest / plugin.code_file(fname)
        if code_path.exists():
            code = _add_module_globals(code_path.read_text(encoding="utf-8"), source)
            code_path.write_text(code, encoding="utf-8")
            set_form_code(res, fname, code, proj.language)
    set_startup(res, proj.startup)
    res.resources["form_code_language"] = proj.language
    res.add("exact", f"{rep.forms} window(s) captured with {rep.controls} control(s); {rep.handlers} event "
                     f"handler(s) connected to the original callbacks (Python importer, {proj.language}).")
    return res


def _add_module_globals(code: str, source: str) -> str:
    """Module-level variables of the original program used through 'global x' in the moved callbacks
    (count = 0 ...) are defined at the top of the form's code file too."""
    import ast
    try:
        tree = ast.parse(code)
        orig = ast.parse(source)
    except SyntaxError:
        return code
    used = {n for node in ast.walk(tree) if isinstance(node, ast.Global) for n in node.names}
    defined = {t.id for node in tree.body if isinstance(node, ast.Assign) for t in node.targets
               if isinstance(t, ast.Name)}
    lines = []
    for node in orig.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in used and name not in defined and isinstance(node.value, (ast.Constant, ast.List, ast.Dict,
                                                                                  ast.Tuple, ast.Set)):
                lines.append(ast.unparse(node))
                defined.add(name)
    if not lines:
        return code
    idx = code.find("\n\n\nclass ")
    block = "\n# variables of the original program\n" + "\n".join(lines) + "\n"
    return code[:idx] + "\n" + block + code[idx:] if idx >= 0 else block + code


# ============================================================================ stand-alone mode
def _main(argv):
    if len(argv) >= 3 and argv[0] == "--decompile":
        src, failed = decompile_file(Path(argv[1]))
        Path(argv[2]).write_text(src, encoding="utf-8")
        return 0
    print("usage: pyexe.py --decompile in.pyc out.py")
    return 2


if __name__ in ("__main__", "__decompile__"):
    sys.exit(_main(sys.argv[1:]))
