"""Import a program from an .exe / .dll - shared definitions (docs/CONTRACTS.md 10.3 / 10.4).

    info = identify(path)                    # BinaryInfo(kind, details)
    backend = pick_backend(info)             # first backend module whose can_handle(info) is True
    result = backend.run(path, info, workdir, progress, ai_translate)   # -> ImportResult

Backends are modules of this package: dotnet, vb6, pyexe, java, electron (exe-managed) and native
(exe-core, the fallback for every PE file).  Each exposes ``can_handle(info) -> bool`` and
``run(path, info, workdir, progress, ai_translate) -> ImportResult``.

Only for programs you wrote, own, or are allowed to analyse (the wizard shows that notice).
"""
from __future__ import annotations

import importlib
import mmap
import os
import re
import shutil
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# ----------------------------------------------------------------------------- kinds
KINDS = {
    "dotnet": ".NET assembly (C# / VB.NET)",
    "vb6": "Visual Basic 5/6 program",
    "pyinstaller": "Python program packed with PyInstaller",
    "py2exe": "Python program packed with py2exe",
    "cxfreeze": "Python program packed with cx_Freeze",
    "nuitka": "Python program compiled with Nuitka",
    "delphi": "Delphi / C++Builder / Lazarus program",
    "autoit": "AutoIt script compiled to .exe",
    "ahk": "AutoHotkey script compiled to .exe",
    "electron": "Electron app (JavaScript)",
    "nwjs": "NW.js app (JavaScript)",
    "java": "Java program (jar or exe wrapper)",
    "installer": "Setup program (installer)",
    "native": "Native program (C / C++ / other compiled language)",
    "unknown": "Unknown file",
}

# report levels used in ImportResult.report
LEVELS = ("exact", "rules", "ai", "missing", "info", "warn", "error")
LEVEL_TEXT = {"exact": "Recovered exactly", "rules": "Translated by rules", "ai": "Translated by AI",
              "missing": "Not recovered", "info": "Info", "warn": "Warning", "error": "Error"}

Progress = Callable[[str], None]


@dataclass
class BinaryInfo:
    kind: str                                    # one of KINDS
    details: dict = field(default_factory=dict)  # bits, machine, imports, markers, version, ...
    path: Path | None = None

    @property
    def label(self) -> str:
        return KINDS.get(self.kind, self.kind)

    def summary(self) -> list[tuple[str, str]]:
        """(name, value) rows for the identification page."""
        d = self.details
        rows = [("Type", self.label)]
        for key, title in (("format", "Format"), ("machine", "CPU"), ("subsystem", "Subsystem"),
                           ("compiler", "Compiler / packer"), ("python_version", "Python version"),
                           ("dotnet_runtime", ".NET runtime"), ("gui", "GUI framework"),
                           ("managed_dll", "Managed assembly"), ("asar", "app.asar"),
                           ("vb_mode", "VB code"), ("product", "Product"), ("file_version", "Version"),
                           ("company", "Company")):
            v = d.get(key)
            if v not in (None, "", [], {}):
                rows.append((title, str(v)))
        if d.get("markers"):
            rows.append(("Markers found", ", ".join(d["markers"][:12])))
        if d.get("dlls"):
            rows.append(("Imports from", ", ".join(d["dlls"][:14]) + (" ..." if len(d["dlls"]) > 14 else "")))
        return rows


@dataclass
class ImportResult:
    forms: list = field(default_factory=list)       # [(name, form_dict)] - neutral .form JSON (model.Form)
    modules: list = field(default_factory=list)     # [(name, code, language)] - language: "python",
    #   "csharp", "c", "javascript", "java", "vb6", "text", ... or a plugin id; name may carry an extension
    resources: dict = field(default_factory=dict)   # strings, version, icons [(name, bytes)], files, ...
    report: list = field(default_factory=list)      # [(level, text)] - level in LEVELS
    source_dir: Path | None = None                  # recovered source tree (kept in the project's _original)
    # recovered event code: {form: {"<control>.<Event>" | ".<Event>": [action, ...]}} - see render_actions
    #   (an action may also be a plain str = a Python line, used as-is for Python targets)
    handlers: dict = field(default_factory=dict)

    def add(self, level: str, text: str) -> None:
        self.report.append((level if level in LEVELS else "info", text))

    def merge(self, other: "ImportResult") -> None:
        self.forms += other.forms
        self.modules += other.modules
        for k, v in other.resources.items():
            self.resources.setdefault(k, v)
        self.report += other.report
        for f, h in other.handlers.items():
            self.handlers.setdefault(f, {}).update(h)
        self.source_dir = self.source_dir or other.source_dir


# ----------------------------------------------------------------------------- tools
def tools_dir() -> Path:
    """%LOCALAPPDATA%\\RADIDE\\tools - private folder for downloaded decompilers."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "RADIDE" / "tools"


def find_tool(*names: str) -> str | None:
    """A tool on PATH or in tools_dir() (searched two levels deep)."""
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    root = tools_dir()
    if root.is_dir():
        for n in names:
            for cand in (root / n, *root.glob(f"*/{n}"), *root.glob(f"*/*/{n}")):
                if cand.is_file():
                    return str(cand)
            for ext in (".exe", ".cmd", ".bat", ".jar", ".py"):
                for cand in (root / (n + ext), *root.glob(f"*/{n}{ext}"), *root.glob(f"*/*/{n}{ext}")):
                    if cand.is_file():
                        return str(cand)
    return None


def safe_name(text: str, fallback: str = "Item") -> str:
    """An identifier from any text ('&Open file...' -> 'OpenFile')."""
    words = re.findall(r"[A-Za-z0-9]+", str(text or "").replace("&", ""))
    s = "".join(w[:1].upper() + w[1:] for w in words)[:32]
    if not s:
        return fallback
    return s if not s[0].isdigit() else fallback + s


# ----------------------------------------------------------------------------- backends
BACKENDS = ("dotnet", "vb6", "pyexe", "java", "electron", "native")


def backend_modules() -> list:
    """Importable backend modules, in priority order (native = fallback, always last)."""
    out = []
    for name in BACKENDS:
        try:
            out.append(importlib.import_module(f"{__package__}.{name}"))
        except Exception:  # noqa: BLE001 - a backend that is missing or broken is skipped
            continue
    return out


def pick_backend(info: BinaryInfo):
    for mod in backend_modules():
        try:
            if mod.can_handle(info):
                return mod
        except Exception:  # noqa: BLE001
            continue
    return None


def ai_translate(source: str, source_lang: str, target_lang: str = "python", context: str = "",
                 progress: Progress | None = None, timeout: float = 240) -> tuple[str | None, str]:
    """Translate *source* with the user's default AI provider (CONTRACTS 9.1).
    Works from a worker thread.  Returns (code or None, provider label or error)."""
    try:
        from ... import ai
        p, model = ai.default("edit")
        ok, why = p.available()
        if not ok:
            return None, f"AI provider {p.name} not available: {why}"
        prompt = (f"Translate this {source_lang} into simple, readable {target_lang}. "
                  "Keep the behaviour, use clear names, no explanations - answer with ONE code block.\n"
                  + (f"\nContext:\n{context}\n" if context else "") + f"\n```\n{source}\n```")
        if progress:
            progress(f"Asking AI ({p.name}{' / ' + model if model else ''}) ...")
        job = p.chat([ai.Message("user", prompt)], model=model or None,
                     system="You convert decompiled or legacy code into clean modern code.")
        text = ai.run_sync(job, timeout=timeout)
        blocks = ai.extract_code_blocks(text)
        code = blocks[0][1] if blocks else text
        return code.strip("\n").rstrip() + "\n", f"{p.name}{' / ' + model if model else ''}"
    except Exception as e:  # noqa: BLE001 - reported, rules are used instead
        return None, f"AI translation failed: {e}"


# ----------------------------------------------------------------------------- identify
_PYI_COOKIE = b"MEI\x0c\x0b\x0a\x0b\x0e"
_DOTNET_BUNDLE_SIG = bytes.fromhex("8b1202b96a612038727b930214d7a03213f5b9e6efae3318ee3b2dce24b36aae")
_MACHINES = {0x14C: "x86 (32-bit)", 0x8664: "x64 (64-bit)", 0xAA64: "ARM64", 0x1C0: "ARM", 0x1C4: "ARM Thumb-2"}
_SUBSYSTEMS = {2: "Windows GUI", 3: "Console", 1: "Native", 9: "Windows CE", 10: "EFI"}

# (marker bytes, label) found anywhere in the file
_MARKERS = [
    (b"PyInstaller", "PyInstaller"), (_PYI_COOKIE, "PyInstaller cookie"), (b"pyi-runtime-tmpdir", "PyInstaller"),
    (b"PYTHONSCRIPT", "py2exe"), (b"py2exe", "py2exe"), (b"cx_Freeze", "cx_Freeze"),
    (b"__nuitka", "Nuitka"), (b"NUITKA_ONEFILE", "Nuitka onefile"), (b"nuitka", "Nuitka"),
    (b"AU3!EA06", "AutoIt v3 script"), (b"AU3!EA05", "AutoIt v3 script"), (b"AutoIt v3", "AutoIt"),
    (b">AUTOHOTKEY SCRIPT<", "AutoHotkey script"), (b"AutoHotkey", "AutoHotkey"),
    (b"Embarcadero Delphi", "Delphi"), (b"Borland", "Borland"), (b"TPF0", "Delphi form (DFM)"),
    (b"FPC ", "Free Pascal"), (b"Lazarus", "Lazarus"),
    (b"Inno Setup", "Inno Setup"), (b"Nullsoft", "NSIS installer"), (b"InstallShield", "InstallShield"),
    (b"WixBundle", "WiX bundle"),
    (b"launch4j", "Launch4j (Java)"), (b"Launch4j", "Launch4j (Java)"), (b"exe4j", "exe4j (Java)"),
    (b"jsmooth", "JSmooth (Java)"), (b"META-INF/MANIFEST.MF", "jar inside"),
    (b"electron.asar", "Electron"), (b"ELECTRON_RUN_AS_NODE", "Electron"), (b"nw.dll", "NW.js"),
    (b"Go build ID", "Go"), (b"runtime.gopanic", "Go"), (b"rust_panic", "Rust"), (b"/rustc/", "Rust"),
    (b"libgcc", "MinGW / GCC"), (b"GCC: (", "GCC"), (b"Mingw-w64", "MinGW-w64"),
    (b"System.Windows.Forms", "WinForms"), (b"PresentationFramework", "WPF"),
    (b"Qt5Core", "Qt 5"), (b"Qt6Core", "Qt 6"), (b"wxWidgets", "wxWidgets"),
    (b"hostfxr", ".NET apphost"), (_DOTNET_BUNDLE_SIG, ".NET single-file bundle"),
]


def _scan_markers(path: Path, limit: int = 400 * 1024 * 1024) -> list[str]:
    found: list[str] = []
    size = path.stat().st_size
    if size == 0:
        return found
    with open(path, "rb") as fh:
        with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            n = min(size, limit)
            for marker, label in _MARKERS:
                if label in found:
                    continue
                if mm.find(marker, 0, n) >= 0:
                    found.append(label)
    return found


def _pe_version_info(pe) -> dict:
    out = {}
    try:
        for fi in getattr(pe, "FileInfo", None) or []:
            for entry in fi:
                for st in getattr(entry, "StringTable", None) or []:
                    for k, v in st.entries.items():
                        k = k.decode("utf-8", "replace") if isinstance(k, bytes) else str(k)
                        v = v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)
                        if v.strip():
                            out[k] = v.strip()
    except Exception:  # noqa: BLE001
        pass
    return out


def _is_clr(pe) -> bool:
    try:
        import pefile
        d = pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR"]]
        return bool(d.VirtualAddress and d.Size)
    except Exception:  # noqa: BLE001
        return False


def _pyinstaller_version(path: Path) -> str:
    """Python version from the PyInstaller cookie at the end of the archive."""
    size = path.stat().st_size
    with open(path, "rb") as fh:
        fh.seek(max(0, size - 64 * 1024))
        tail = fh.read()
    i = tail.rfind(_PYI_COOKIE)
    if i < 0:
        return ""
    cookie = tail[i:i + 88]
    try:      # magic[8], len, toc, toclen, pyvers (big-endian ints), pylibname[64]
        pyvers = struct.unpack("!i", cookie[20:24])[0]
    except struct.error:
        return ""
    if pyvers >= 100:
        return f"{pyvers // 100}.{pyvers % 100}"
    return f"{pyvers // 10}.{pyvers % 10}"


def _dotnet_bundle_offset(path: Path) -> int:
    """Header offset of a .NET single-file bundle (0 = a plain apphost: the signature is only a placeholder)."""
    data = path.read_bytes()
    i = data.find(_DOTNET_BUNDLE_SIG)
    if i < 8:
        return 0
    return struct.unpack_from("<q", data, i - 8)[0]


def _find_vb5(data: bytes) -> int:
    return data.find(b"VB5!")


def identify(path) -> BinaryInfo:
    """Work out what kind of program *path* is (fast; never runs it)."""
    path = Path(path)
    d: dict = {"size": path.stat().st_size if path.exists() else 0}
    if not path.is_file():
        return BinaryInfo("unknown", {"error": "file not found"}, path)
    with open(path, "rb") as fh:
        head = fh.read(4096)
    low = path.name.lower()
    # ---- not PE files
    if low.endswith(".asar") or (head[:4] == b"\x04\x00\x00\x00" and low.endswith(".asar")):
        return BinaryInfo("electron", {**d, "format": "asar archive", "asar": str(path)}, path)
    if head[:4] == b"PK\x03\x04":
        d["format"] = "ZIP archive"
        if low.endswith((".jar", ".war")):
            return BinaryInfo("java", {**d, "format": "Java archive (.jar)", "jar": str(path)}, path)
        return BinaryInfo("unknown", d, path)
    if head[:4] == b"\xca\xfe\xba\xbe" and low.endswith(".class"):
        return BinaryInfo("java", {**d, "format": "Java class file"}, path)
    if head[:2] != b"MZ":
        return BinaryInfo("unknown", {**d, "format": "not a Windows program (no MZ header)"}, path)

    try:
        import pefile
    except ImportError:
        return BinaryInfo("unknown", {**d, "error": "pefile is not installed (pip install pefile)"}, path)
    try:
        pe = pefile.PE(str(path), fast_load=True)
        pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR"]])
    except Exception as e:  # noqa: BLE001
        return BinaryInfo("unknown", {**d, "format": "MZ file", "error": f"not a valid PE file: {e}"}, path)
    try:
        return _identify_pe(path, pe, d)
    finally:
        pe.close()


def _identify_pe(path: Path, pe, d: dict) -> BinaryInfo:
    import pefile
    fh = pe.FILE_HEADER
    d["machine"] = _MACHINES.get(fh.Machine, hex(fh.Machine))
    d["bits"] = 64 if pe.OPTIONAL_HEADER.Magic == 0x20B else 32
    d["subsystem"] = _SUBSYSTEMS.get(pe.OPTIONAL_HEADER.Subsystem, str(pe.OPTIONAL_HEADER.Subsystem))
    d["is_dll"] = bool(fh.Characteristics & 0x2000)
    d["format"] = ("PE32+ " if d["bits"] == 64 else "PE32 ") + ("DLL" if d["is_dll"] else "executable")
    d["sections"] = [s.Name.rstrip(b"\x00").decode("latin-1") for s in pe.sections]
    dlls, imports = [], {}
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []) or []:
        name = entry.dll.decode("latin-1")
        dlls.append(name)
        imports[name] = [(i.name.decode("latin-1") if i.name else f"#{i.ordinal}") for i in entry.imports]
    d["dlls"] = dlls
    d["import_count"] = sum(len(v) for v in imports.values())
    exp = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    d["exports"] = [(s.name.decode("latin-1") if s.name else f"#{s.ordinal}") for s in exp.symbols] if exp else []
    ver = _pe_version_info(pe)
    d["version_info"] = ver
    d["product"] = ver.get("ProductName", "")
    d["file_version"] = ver.get("FileVersion", ver.get("ProductVersion", ""))
    d["company"] = ver.get("CompanyName", "")
    rtypes = []
    for e in getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None).entries if hasattr(pe, "DIRECTORY_ENTRY_RESOURCE") else []:
        if e.name is not None:
            rtypes.append(str(e.name))
        else:
            rtypes.append(str(pefile.RESOURCE_TYPE.get(e.struct.Id, e.struct.Id)).replace("RT_", ""))
    d["resource_types"] = rtypes
    markers = _scan_markers(path)
    d["markers"] = markers
    low_dlls = {x.lower() for x in dlls}
    overlay = pe.get_overlay_data_start_offset()
    d["overlay"] = (d["size"] - overlay) if overlay else 0
    folder = path.parent

    def has(*labels):
        return any(lb in markers for lb in labels)

    # ---- .NET (CLR header in this file, or an apphost next to its managed .dll)
    if _is_clr(pe):
        d["compiler"] = ".NET (CLR header)"
        d["gui"] = "WinForms" if has("WinForms") else "WPF" if has("WPF") else ""
        d["managed_dll"] = str(path)
        return BinaryInfo("dotnet", d, path)
    if has(".NET apphost", ".NET single-file bundle"):
        side = path.with_suffix(".dll")
        d["dotnet_runtime"] = "apphost"
        if side.is_file():
            try:
                spe = pefile.PE(str(side), fast_load=True)
                if _is_clr(spe):
                    d["managed_dll"] = str(side)
                spe.close()
            except Exception:  # noqa: BLE001
                pass
        if has(".NET single-file bundle") and _dotnet_bundle_offset(path) > 0:
            d["compiler"] = ".NET single-file bundle"
            d["bundle"] = True
        else:
            d["compiler"] = ".NET apphost"
        if d.get("managed_dll") or d.get("bundle"):
            try:
                text = Path(d.get("managed_dll") or path).read_bytes()
                d["gui"] = ("WinForms" if b"System.Windows.Forms" in text else
                            "WPF" if b"PresentationFramework" in text else "")
            except OSError:
                pass
            return BinaryInfo("dotnet", d, path)
    # ---- Visual Basic 5/6
    vbdll = next((x for x in dlls if x.lower() in ("msvbvm60.dll", "msvbvm50.dll", "vb40032.dll")), None)
    if vbdll:
        d["compiler"] = f"Visual Basic ({vbdll})"
        data = path.read_bytes()
        off = _find_vb5(data)
        d["vb5_header"] = off
        vb_imports = imports.get(vbdll, [])
        native_hint = any(n.startswith("__vba") for n in vb_imports)
        d["vb_mode"] = "native code" if native_hint and "ProcCallEngine" not in vb_imports else "P-code"
        return BinaryInfo("vb6", d, path)
    # ---- Python packers
    if has("PyInstaller", "PyInstaller cookie"):
        d["compiler"] = "PyInstaller"
        d["python_version"] = _pyinstaller_version(path)
        d["python_dll"] = next((x for x in dlls if re.match(r"python\d+\.dll", x, re.I)), "")
        return BinaryInfo("pyinstaller", d, path)
    if has("py2exe") or "PYTHONSCRIPT" in rtypes:
        d["compiler"] = "py2exe"
        return BinaryInfo("py2exe", d, path)
    if has("cx_Freeze") or (folder / "lib" / "library.zip").exists():
        d["compiler"] = "cx_Freeze"
        return BinaryInfo("cxfreeze", d, path)
    if has("Nuitka", "Nuitka onefile"):
        d["compiler"] = "Nuitka"
        return BinaryInfo("nuitka", d, path)
    # ---- Electron / NW.js
    asar = folder / "resources" / "app.asar"
    if asar.is_file() or (folder / "resources" / "app").is_dir() and has("Electron"):
        d["compiler"] = "Electron"
        d["asar"] = str(asar) if asar.is_file() else str(folder / "resources" / "app")
        return BinaryInfo("electron", d, path)
    if has("Electron") and (folder / "resources").is_dir():
        d["compiler"] = "Electron"
        return BinaryInfo("electron", d, path)
    if (folder / "package.nw").exists() or ("nw.dll" in low_dlls) or (has("NW.js") and (folder / "nw.dll").exists()):
        d["compiler"] = "NW.js"
        d["package_nw"] = str(folder / "package.nw") if (folder / "package.nw").exists() else ""
        return BinaryInfo("nwjs", d, path)
    # ---- Java wrappers (Launch4j/exe4j/JSmooth: jar appended or next to the exe)
    if has("Launch4j (Java)", "exe4j (Java)", "JSmooth (Java)") or (d["overlay"] and has("jar inside")):
        d["compiler"] = next(m for m in markers if "(Java)" in m or m == "jar inside")
        d["jar_in_overlay"] = bool(d["overlay"] and has("jar inside"))
        return BinaryInfo("java", d, path)
    # ---- script compilers
    if has("AutoIt v3 script") or (has("AutoIt") and "RCDATA" in rtypes):
        d["compiler"] = "AutoIt v3"
        return BinaryInfo("autoit", d, path)
    if has("AutoHotkey script"):
        d["compiler"] = "AutoHotkey"
        return BinaryInfo("ahk", d, path)
    # ---- installers (identified, imported as native: resources only)
    if has("Inno Setup", "NSIS installer", "InstallShield", "WiX bundle"):
        d["compiler"] = next(m for m in markers if m in ("Inno Setup", "NSIS installer", "InstallShield", "WiX bundle"))
        return BinaryInfo("installer", d, path)
    # ---- Delphi / C++Builder / Lazarus
    sect = set(d["sections"])
    if has("Delphi form (DFM)") and (has("Delphi", "Borland", "Free Pascal", "Lazarus") or {"CODE", "DATA"} & sect
                                     or "DVCLAL" in rtypes or "PACKAGEINFO" in rtypes):
        d["compiler"] = ("Lazarus / Free Pascal" if has("Lazarus", "Free Pascal") else "Delphi / C++Builder")
        return BinaryInfo("delphi", d, path)
    # ---- plain native
    comp = []
    try:
        rich = pe.parse_rich_header()
    except Exception:  # noqa: BLE001
        rich = None
    if rich:
        comp.append("Microsoft Visual C++")
    for lb in ("Go", "Rust", "MinGW-w64", "MinGW / GCC", "GCC"):
        if lb in markers and not any(lb in c for c in comp):
            comp.append(lb)
    if "Qt 5" in markers or "Qt 6" in markers or any(x.lower().startswith(("qt5", "qt6")) for x in dlls):
        d["gui"] = "Qt"
    elif "wxWidgets" in markers:
        d["gui"] = "wxWidgets"
    elif "DIALOG" in rtypes or "user32.dll" in low_dlls:
        d["gui"] = "Win32 API" + (" (dialog resources)" if "DIALOG" in rtypes else "")
    d["compiler"] = " / ".join(comp[:2]) or "unknown compiler"
    return BinaryInfo("native", d, path)


# ----------------------------------------------------------------------------- handler actions
# Backends describe recovered event-handler code as neutral actions; the wizard renders them in the
# target language.  ImportResult.handlers = {form: {"<control>.<Event>" | ".<Event>" (form) |
# "<menu item>.Click": [action, ...]}}.  An action is a tuple:
#   ("comment", text)                 ("python", code line - used as-is for Python targets)
#   ("msgbox", text, title, kind)     kind: info | warning | error | question
#   ("set_text", control, expr)       ("get_text", var, control)
#   ("list_add", control, expr)       ("list_clear", control)
#   ("set_check", control, expr)      ("get_check", var, control)
#   ("enable", control, expr)         ("assign", var, expr)
#   ("title", expr)  ("close",)  ("show_form", form)  ("beep",)  ("open", expr)
# expr: ("str", s) | ("int", n) | ("var", name) | ("fmt", c_format, [expr...]) | ("concat", [expr...])
#       | ("call", "int"|"float"|"len"|"str", [expr]) | ("binop", "+"|"-"|"*", expr, expr)
#       | ("raw", python expression)

def _py_expr(e) -> str:
    if not isinstance(e, tuple):
        return repr(e)
    k = e[0]
    if k == "str":
        return repr(e[1])
    if k == "int":
        return str(int(e[1]))
    if k in ("var", "raw"):
        return str(e[1])
    if k == "fmt":
        fmt = re.sub(r"%l?l?[uxi]", "%d", re.sub(r"%(ls|S|hs)", "%s", e[1]))
        args = [_py_expr(a) for a in e[2]]
        return f"{fmt!r} % ({', '.join(args)},)" if args else repr(fmt)
    if k == "concat":
        return " + ".join(_py_expr(a) for a in e[1]) or "''"
    if k == "call":
        return f"{e[1]}({', '.join(_py_expr(a) for a in e[2])})"
    if k == "binop":
        return f"{_py_expr(e[2])} {e[1]} {_py_expr(e[3])}"
    return repr(e)


def _vb_str(s: str) -> str:
    return '"' + str(s).replace('"', '""') + '"'


def _vb_expr(e) -> str:
    if not isinstance(e, tuple):
        return _vb_str(e)
    k = e[0]
    if k == "str":
        return _vb_str(e[1])
    if k == "int":
        return str(int(e[1]))
    if k == "var":
        return str(e[1])
    if k == "raw":
        return f"({e[1]})"
    if k == "fmt":
        parts, args = re.split(r"%[-+ 0#]*\d*(?:\.\d+)?(?:l|ll|h)?[sdiuxXfgcS]", e[1]), list(e[2])
        out = []
        for i, p in enumerate(parts):
            if p:
                out.append(_vb_str(p))
            if i < len(parts) - 1:
                out.append(_vb_expr(args[i]) if i < len(args) else '""')
        return " & ".join(out) or '""'
    if k == "concat":
        return " & ".join(_vb_expr(a) for a in e[1]) or '""'
    if k == "call":
        fn = {"int": "Val", "float": "Val", "len": "Len", "str": "CStr"}.get(e[1], e[1])
        return f"{fn}({', '.join(_vb_expr(a) for a in e[2])})"
    if k == "binop":
        return f"{_vb_expr(e[2])} {e[1]} {_vb_expr(e[3])}"
    return _vb_str(str(e))


def _ctrl_types(form_dict: dict | None) -> dict:
    return {c["props"].get("Name"): c["type"] for c in (form_dict or {}).get("controls", [])}


# the python-qt plugin generates PySide6 code (radide/languages/python_qt.py): handlers use the same binding
QT_BINDING = "PySide6"


def render_actions(actions: list, language: str, form_dict: dict | None = None,
                   comment: str = "#") -> list[str]:
    """Body lines (without indentation) for one handler in *language* (a plugin id)."""
    types = _ctrl_types(form_dict)
    actions = [("python", a) if isinstance(a, str) else a for a in actions]
    out: list[str] = []
    if language in ("python-tk", "python-qt"):
        qt = language == "python-qt"
        for a in actions:
            k = a[0]
            if k == "comment":
                out.append(f"# {a[1]}")
            elif k == "python":
                out.append(a[1])
            elif k == "msgbox":
                text, title, kind = _py_expr(a[1]), _py_expr(a[2]), a[3] if len(a) > 3 else "info"
                if qt:
                    fn = {"warning": "warning", "error": "critical", "question": "question"}.get(kind, "information")
                    out += [f"from {QT_BINDING}.QtWidgets import QMessageBox", f"QMessageBox.{fn}(self, {title}, {text})"]
                else:
                    fn = {"warning": "showwarning", "error": "showerror", "question": "askyesno"}.get(kind, "showinfo")
                    out += ["from tkinter import messagebox", f"messagebox.{fn}({title}, {text})"]
            elif k == "set_text":
                c, v, t = a[1], _py_expr(a[2]), types.get(a[1], "Label")
                if qt:
                    out.append(f"self.{c}.setPlainText({v})" if t == "TextBox" and _multiline(form_dict, c)
                               else f"self.{c}.setText({v})")
                elif t == "TextBox" and _multiline(form_dict, c):
                    out += [f"self.{c}.delete('1.0', 'end')", f"self.{c}.insert('1.0', {v})"]
                elif t in ("TextBox", "ComboBox"):
                    out.append(f"self.{c}_var.set({v})")
                else:
                    out.append(f"self.{c}.config(text={v})")
            elif k == "get_text":
                var, c, t = a[1], a[2], types.get(a[2], "TextBox")
                if qt:
                    out.append(f"{var} = self.{c}.toPlainText()" if _multiline(form_dict, c) else
                               f"{var} = self.{c}.currentText()" if t == "ComboBox" else f"{var} = self.{c}.text()")
                elif t == "TextBox" and _multiline(form_dict, c):
                    out.append(f"{var} = self.{c}.get('1.0', 'end-1c')")
                elif t in ("TextBox", "ComboBox"):
                    out.append(f"{var} = self.{c}_var.get()")
                else:
                    out.append(f"{var} = self.{c}.cget('text')")
            elif k == "list_add":
                c, v = a[1], _py_expr(a[2])
                if qt:
                    out.append(f"self.{c}.addItem({v})")
                elif types.get(c) == "ComboBox":
                    out.append(f"self.{c}['values'] = (*self.{c}['values'], {v})")
                else:
                    out.append(f"self.{c}.insert('end', {v})")
            elif k == "list_clear":
                c = a[1]
                out.append(f"self.{c}.clear()" if qt else
                           f"self.{c}['values'] = ()" if types.get(c) == "ComboBox" else f"self.{c}.delete(0, 'end')")
            elif k == "set_check":
                out.append(f"self.{a[1]}.setChecked(bool({_py_expr(a[2])}))" if qt else
                           f"self.{a[1]}_var.set(bool({_py_expr(a[2])}))")
            elif k == "get_check":
                out.append(f"{a[1]} = self.{a[2]}.isChecked()" if qt else f"{a[1]} = self.{a[2]}_var.get()")
            elif k == "enable":
                out.append(f"self.{a[1]}.setEnabled(bool({_py_expr(a[2])}))" if qt else
                           f"self.{a[1]}.config(state='normal' if {_py_expr(a[2])} else 'disabled')")
            elif k == "assign":
                out.append(f"{a[1]} = {_py_expr(a[2])}")
            elif k == "title":
                out.append(f"self.setWindowTitle({_py_expr(a[1])})" if qt else f"self.root.title({_py_expr(a[1])})")
            elif k == "close":
                out.append("self.close()" if qt else "self.root.destroy()")
            elif k == "show_form":
                f = a[1]
                out += [f"from {f} import {f}", f"self._{f} = {f}()" if qt else f"{f}(self.root)"]
                if qt:
                    out.append(f"self._{f}.show()")
            elif k == "beep":
                out.append("QApplication.beep()" if qt else "self.root.bell()")
                if qt:
                    out.insert(len(out) - 1, f"from {QT_BINDING}.QtWidgets import QApplication")
            elif k == "open":
                out += ["import os", f"os.startfile({_py_expr(a[1])})"]
        return _dedupe_imports(out)
    if language == "vb-basic":
        for a in actions:
            k = a[0]
            if k == "comment":
                out.append(f"' {a[1]}")
            elif k == "python":
                out.append(f"' (Python) {a[1]}")
            elif k == "msgbox":
                icon = {"warning": "vbExclamation", "error": "vbCritical", "question": "vbQuestion + vbYesNo"}.get(
                    a[3] if len(a) > 3 else "info", "vbInformation")
                out.append(f"MsgBox {_vb_expr(a[1])}, {icon}, {_vb_expr(a[2])}")
            elif k == "set_text":
                prop = "Text" if types.get(a[1]) in ("TextBox", "ComboBox") else "Caption"
                out.append(f"{a[1]}.{prop} = {_vb_expr(a[2])}")
            elif k == "get_text":
                prop = "Text" if types.get(a[2], "TextBox") in ("TextBox", "ComboBox") else "Caption"
                out.append(f"{a[1]} = {a[2]}.{prop}")
            elif k == "list_add":
                out.append(f"{a[1]}.AddItem {_vb_expr(a[2])}")
            elif k == "list_clear":
                out.append(f"{a[1]}.Clear")
            elif k == "set_check":
                out.append(f"{a[1]}.Value = IIf({_vb_expr(a[2])}, 1, 0)")
            elif k == "get_check":
                out.append(f"{a[1]} = ({a[2]}.Value = 1)")
            elif k == "enable":
                out.append(f"{a[1]}.Enabled = {_vb_expr(a[2])}")
            elif k == "assign":
                out.append(f"{a[1]} = {_vb_expr(a[2])}")
            elif k == "title":
                out.append(f"Me.Caption = {_vb_expr(a[1])}")
            elif k == "close":
                out.append("Unload Me")
            elif k == "show_form":
                out.append(f"{a[1]}.Show vbModal")
            elif k == "beep":
                out.append("Beep")
            elif k == "open":
                out.append(f"Shell \"explorer \" & {_vb_expr(a[1])}")
        names = list(dict.fromkeys(a[1] for a in actions if a[0] in ("assign", "get_text", "get_check")))
        return ([f"Dim {', '.join(names)}"] if names else []) + out
    # other languages: a readable description as comments (the AI can translate it later)
    return [f"{comment} {describe_action(a)}" for a in actions]


def _multiline(form_dict, name) -> bool:
    for c in (form_dict or {}).get("controls", []):
        if c["props"].get("Name") == name:
            return bool(c["props"].get("Multiline"))
    return False


def _dedupe_imports(lines: list[str]) -> list[str]:
    seen, out = set(), []
    for ln in lines:
        if ln.startswith(("from ", "import ")):
            if ln in seen:
                continue
            seen.add(ln)
        out.append(ln)
    return out


def describe_action(a) -> str:
    """One readable line for an action (reports, comments in non-Python targets)."""
    if isinstance(a, str):
        return a
    k = a[0]
    if k in ("comment", "python"):
        return str(a[1])
    args = ", ".join(_py_expr(x) if isinstance(x, tuple) else str(x) for x in a[1:])
    return f"{k}({args})"
