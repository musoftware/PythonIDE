"""Native Win32 builds of C / C++ / Fortran GUI Bridge projects with MinGW-w64 + radforms.

The project's own code is compiled unchanged: radforms (radide/runtimes/native/radforms) implements the
GUI Bridge client API of radgui.h / radgui.hpp / radgui.f90 in process, so the forms are drawn by Win32
inside the exe instead of a frozen Python/Tk host. The result is one small static exe (no Python, no
MinGW DLLs): the form description, manifest (visual styles, per-monitor DPI, UTF-8), icon, version
resource and the images of the forms are embedded as resources.

    C        gcc  -Os  user .c files + generated _radnative_main.c + radforms.c
    C++      g++  -Os  user .cpp files + generated _radnative_main.cpp (+ radforms.c compiled as C)
    Fortran  gfortran -Os  radgui.f90 (native variant: stdin/stdout replaced by radforms calls) + user
             modules + the usual generated main program (+ radforms.c)

Console programs (no form, a module with its own main / program) are compiled alone as console exes.
The toolchain is found like the C plugin finds it (PATH, %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64, MSYS2
...); when there is none, WinLibs (the official GitHub release of brechtsanders/winlibs_mingw, SHA-256
checked) is downloaded into %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64 - portable, no admin rights.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path

from . import NativeUnsupported
from . import radforms_gen as rg

LANGS = ("c-bridge", "cpp-bridge", "fortran-bridge")
NAME = "native Win32 exe (MinGW-w64 + radforms)"

CLIENTS = Path(__file__).resolve().parents[2] / "runtimes" / "clients" / "c"
RADGUI_F90 = Path(__file__).resolve().parents[2] / "runtimes" / "radgui.f90"

# no -fdata-sections: on PE it moves zero-initialised statics from .bss into .data (file size)
SIZE_FLAGS = ["-Os", "-s", "-ffunction-sections", "-Wl,--gc-sections", "-fno-ident", "-Wl,--build-id=none"]
WIN_LIBS = ["-lcomctl32", "-lcomdlg32", "-lgdi32", "-lole32", "-luuid", "-lshell32"]
SOURCE_EXT = {".c", ".h", ".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx", ".f90", ".f95", ".f03", ".f", ".for",
              ".mod", ".o", ".obj", ".exe", ".pdb", ".ilk", ".res", ".rc", ".form", ".radproj", ".radsln", ".iss",
              ".spec", ".py", ".pyc"}


def _plugin(lang: str):
    from ...languages import get_plugin
    return get_plugin(lang)


# ------------------------------------------------------------------ toolchain
WINLIBS_API = "https://api.github.com/repos/brechtsanders/winlibs_mingw/releases/latest"
WINLIBS_ASSET = re.compile(r"^winlibs-x86_64-posix-seh-gcc-[\d.]+-mingw-w64ucrt-[\w.]+-r\d+\.zip$")


def find_tool(name: str) -> str:
    from ...languages.c_bridge import find_native
    return find_native([name])


def _toolchains() -> Path:
    from ...languages.bridgebase import toolchains_root
    return toolchains_root()


def download_winlibs(log=print) -> bool:
    """Download the latest WinLibs (GCC + MinGW-w64, UCRT, no LLVM) from its official GitHub release
    into %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64. The zip must match the SHA-256 GitHub publishes."""
    import hashlib
    try:
        req = urllib.request.Request(WINLIBS_API, headers={"User-Agent": "RAD-IDE", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            rel = json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError) as e:
        log(f"WinLibs: cannot read the release list ({e})")
        return False
    assets = rel.get("assets") or []
    zips = [a for a in assets if WINLIBS_ASSET.match(a.get("name", ""))]
    if not zips:
        log("WinLibs: no matching zip in the latest release")
        return False
    asset = zips[0]
    sha = str(asset.get("digest") or "")
    sha = sha.split(":", 1)[1] if sha.startswith("sha256:") else ""
    if not sha:                                   # older releases: a .sha256 file next to the zip
        side = next((a for a in assets if a.get("name") == asset["name"] + ".sha256"), None)
        if side:
            try:
                with urllib.request.urlopen(urllib.request.Request(side["browser_download_url"],
                                                                   headers={"User-Agent": "RAD-IDE"}), timeout=30) as r:
                    sha = r.read().decode("ascii", "replace").split()[0]
            except (OSError, IndexError):
                sha = ""
    if not re.fullmatch(r"[0-9a-fA-F]{64}", sha):
        log("WinLibs: the release has no SHA-256 for the zip - not downloading it")
        return False
    root = _toolchains()
    tmp = root / "_download" / asset["name"]
    tmp.parent.mkdir(parents=True, exist_ok=True)
    url = asset["browser_download_url"]
    if not url.startswith("https://github.com/brechtsanders/winlibs_mingw/releases/download/"):
        log(f"WinLibs: unexpected download address {url}")
        return False
    log(f"Downloading {url} ({int(asset.get('size', 0)) // (1 << 20)} MB) ...")
    h = hashlib.sha256()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "RAD-IDE"}), timeout=120) as r, \
                open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
                f.write(chunk)
    except OSError as e:
        tmp.unlink(missing_ok=True)
        log(f"WinLibs download failed: {e}")
        return False
    if h.hexdigest().lower() != sha.lower():
        tmp.unlink(missing_ok=True)
        log("WinLibs: SHA-256 mismatch - the file was removed")
        return False
    log("SHA-256 OK, unpacking ...")
    with zipfile.ZipFile(tmp) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in Path(name).parts or ":" in name:
                log(f"unsafe path in the archive: {name}")
                return False
        z.extractall(root)                       # the zip holds mingw64/...
    tmp.unlink(missing_ok=True)
    (root / "mingw64" / "RADIDE-SOURCE.json").write_text(json.dumps({"url": url, "sha256": sha}, indent=1),
                                                         encoding="utf-8")
    return bool(find_tool("gcc"))


def toolchain(lang: str, log=print) -> dict[str, str]:
    """{"cc": gcc, "driver": gcc|g++|gfortran, "windres": windres} from one bin folder (downloaded if missing)."""
    driver_name = {"c-bridge": "gcc", "cpp-bridge": "g++", "fortran-bridge": "gfortran"}[lang]
    driver = find_tool(driver_name)
    if not driver:
        log(f"{driver_name} was not found: installing WinLibs (MinGW-w64) ...")
        download_winlibs(log)
        driver = find_tool(driver_name)
    if not driver:
        raise NativeUnsupported(f"{driver_name} (MinGW-w64) was not found and could not be downloaded")
    bindir = Path(driver).parent
    exe = ".exe" if os.name == "nt" else ""
    cc = bindir / ("gcc" + exe)
    windres = bindir / ("windres" + exe)
    if not cc.is_file() or not windres.is_file():
        raise NativeUnsupported(f"{bindir} has no gcc / windres next to {driver_name}")
    return {"cc": str(cc), "driver": driver, "windres": str(windres)}


# ------------------------------------------------------------------ project scanning
def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _sources(folder: Path, project, plugin) -> dict[str, str]:
    files = list(plugin.form_files(project)) + [m for m in plugin.module_files(project)]
    return {f: _read(folder / f) for f in files if (folder / f).is_file()}


_RADCALL = re.compile(r"""\b(?:radcall|rad::hub)\s*\(\s*(["'])([^"']*)\1""", re.I)
_RADCALL_ANY = re.compile(r"\b(?:radcall|rad::hub)\s*\(", re.I)
_RADHUB = re.compile(r"\brad::invoke\s*\(")


def _code_only(text: str, fortran: bool) -> str:
    """Source without comments (good enough for the checks: '!' / '//' inside strings are rare)."""
    if fortran:
        return "\n".join(line.split("!", 1)[0] if line.count("'") % 2 == 0 and line.count('"') % 2 == 0
                         and "!" in line and ("'" not in line.split("!", 1)[1] and '"' not in line.split("!", 1)[1])
                         else line for line in text.splitlines())
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def _radfuncs(folder: Path, project, plugin) -> dict[str, list[str]]:
    """{module stem: [RADFUNC names]} of the project's C / C++ modules."""
    out = {}
    if plugin.id == "fortran-bridge":
        return out
    for m in plugin.module_files(project):
        names = plugin.radfuncs(_read(folder / m))
        if names:
            out[Path(m).stem] = names
    return out


def check(folder, project, cfg) -> list[str]:
    folder = Path(folder)
    from ..build import startup_language
    lang = startup_language(project)
    if lang not in LANGS:
        return [f"{lang} is not a C / C++ / Fortran project"]
    plugin = _plugin(lang)
    reasons = rg.unsupported(project, folder, lang)
    srcs = _sources(folder, project, plugin)
    reasons += rg.code_reasons(srcs)
    try:
        proxies = plugin.proxy_sources(folder, project)
    except Exception:  # noqa: BLE001
        proxies = []
    if proxies:
        reasons.append("the project references other projects (RAD Hub): not possible in one native exe")
    funcs = _radfuncs(folder, project, plugin)
    for f, text in srcs.items():
        text = _code_only(text, lang == "fortran-bridge")
        literal = _RADCALL.findall(text)
        if _RADHUB.search(text) or len(literal) < len(_RADCALL_ANY.findall(text)):
            reasons.append(f"{f}: radcall with a computed name (RAD Hub) cannot be checked for a native exe")
        for _q, target in literal:
            mod, _, fn = target.partition(".")
            if fn not in funcs.get(mod, []):
                reasons.append(f"{f}: radcall(\"{target}\") needs RAD Hub (only this project's RADFUNCs work natively)")
    if getattr(cfg, "update", None) is not None and cfg.update.enabled and cfg.update.url:
        pass                     # the update check is Python based: noted by build(), not a reason to fall back
    return reasons


# ------------------------------------------------------------------ generated mains
def c_main(plugin, handlers: list[str], funcs: dict[str, list[str]], cpp: bool) -> str:
    void = "()" if cpp else "(void)"
    L = ["/* AUTO-GENERATED by RAD IDE - native main program (radforms; do not edit) */",
         '#include "radforms.h"', ""]
    L += [f"void {h}{void};" for h in handlers]
    for names in funcs.values():
        L += [f"RADFUNC({n});" for n in names]
    L += ["", "static int rad_ieq(const char *a, const char *b)", "{",
          "    for (; *a && *b; a++, b++) {",
          "        int x = *a >= 'A' && *a <= 'Z' ? *a + 32 : *a, y = *b >= 'A' && *b <= 'Z' ? *b + 32 : *b;",
          "        if (x != y) return 0;", "    }", "    return *a == *b;", "}", "",
          "static int rad_dispatch(const char *key)", "{"]
    seen = set()
    for h in handlers:
        if h.lower() in seen:
            continue
        seen.add(h.lower())
        L.append(f'    if (rad_ieq(key, "{h}")) {{ {h}(); return 1; }}')
    L += ["    (void)rad_ieq;" if not handlers else "", "    return 0;", "}", "", "int main(void)", "{",
          f'    rad_handlers("{",".join(handlers)}");']
    for mod, names in funcs.items():
        L += [f'    rad_register("{mod}.{n}", {n});' for n in names]
    L += ["    return rad_run(rad_dispatch);", "}", ""]
    return "\n".join(L)


F_NATIVE_IO = '''  subroutine rad_readline(line, ok)
    character(len=*), intent(out) :: line
    logical, intent(out) :: ok
    line = rad_cstr(c_rad_line_in())
    ok = .true.
  end subroutine rad_readline
'''
F_NATIVE_SEND = '''  subroutine rad_send(text)
    character(len=*), intent(in) :: text
    call c_rad_line_out(text // c_null_char)
  end subroutine rad_send

  ! native exe: the names of the program's handlers (only these events are reported)
  subroutine rad_native_handlers(csv)
    character(len=*), intent(in) :: csv
    call c_rad_handlers(trim(csv) // c_null_char)
  end subroutine rad_native_handlers
'''
F_NATIVE_NUM = '''  real(8) function rad_num(text)
    character(len=*), intent(in) :: text
    rad_num = c_rad_num(trim(text) // c_null_char)
  end function rad_num
'''
F_NATIVE_STR = '''  function rad_str(x) result(s)
    real(8), intent(in) :: x
    character(len=:), allocatable :: s
    s = rad_cstr(c_rad_str(real(x, c_double)))
  end function rad_str
'''
F_NATIVE_IFACE = '''    ! native exe: the GUI Bridge protocol runs in process (radforms.c)
    function c_rad_line_in() bind(C, name='rad_line_in') result(p)
      import :: c_ptr
      type(c_ptr) :: p
    end function c_rad_line_in
    subroutine c_rad_line_out(line) bind(C, name='rad_line_out')
      import :: c_char
      character(kind=c_char), dimension(*), intent(in) :: line
    end subroutine c_rad_line_out
    subroutine c_rad_handlers(csv) bind(C, name='rad_handlers')
      import :: c_char
      character(kind=c_char), dimension(*), intent(in) :: csv
    end subroutine c_rad_handlers
    function c_rad_num(text) bind(C, name='rad_num') result(x)
      import :: c_char, c_double
      character(kind=c_char), dimension(*), intent(in) :: text
      real(c_double) :: x
    end function c_rad_num
    function c_rad_str(x) bind(C, name='rad_str') result(p)
      import :: c_double, c_ptr
      real(c_double), value :: x
      type(c_ptr) :: p
    end function c_rad_str
'''


def _replace_proc(text: str, kind: str, name: str, new: str) -> str:
    rx = re.compile(rf"^[ \t]*(?:[\w()]+[ \t]+)?{kind}[ \t]+{name}\b.*?^[ \t]*end[ \t]+{kind}[ \t]+{name}[ \t]*\n",
                    re.I | re.M | re.S)
    out, n = rx.subn(lambda _m: new, text, count=1)
    if n != 1:
        raise NativeUnsupported(f"radgui.f90 changed: cannot find {kind} {name} for the native variant")
    return out


def fortran_native_module(src: str | None = None) -> str:
    """radgui.f90 with its stdin/stdout layer replaced by radforms calls (same module name and API)."""
    text = src if src is not None else RADGUI_F90.read_text(encoding="utf-8")
    text = _replace_proc(text, "subroutine", "rad_readline", F_NATIVE_IO)
    text = _replace_proc(text, "subroutine", "rad_send", F_NATIVE_SEND)
    text = _replace_proc(text, "function", "rad_num", F_NATIVE_NUM)
    text = _replace_proc(text, "function", "rad_str", F_NATIVE_STR)
    text = re.sub(r"(use, intrinsic :: iso_c_binding, only:)([^\n]*)", lambda m: m.group(1) + m.group(2) +
                  ("" if "c_double" in m.group(2) else ", c_double"), text, count=1)
    i = text.lower().find("  end interface")
    if i < 0:
        raise NativeUnsupported("radgui.f90 changed: no interface block for the native variant")
    text = text[:i] + F_NATIVE_IFACE + text[i:]
    return "! AUTO-GENERATED by RAD IDE from radgui.f90 - native exe variant (radforms)\n" + text


def fortran_main(plugin, project, handlers: list[str]) -> str:
    _name, text = plugin.main_source(project)
    call = f"  call rad_native_handlers('{','.join(handlers)}')\n"
    i = text.find("  do while (rad_next_event())")
    if i < 0:
        raise NativeUnsupported("unexpected Fortran main program (no event loop)")
    return text[:i] + call + text[i:]


# ------------------------------------------------------------------ build
def _run(cmd: list[str], cwd: Path, log, env=None) -> int:
    from ..build import run
    return run(cmd, cwd, log, env=env)


def _copy_data(folder: Path, cfg, dist: Path, log):
    from ..build import data_entries
    for p in data_entries(folder, cfg, skip_ext=SOURCE_EXT):
        if p.name.lower().startswith(("_rad", "radgui.")) or p.name in ("_build", "vcpkg_installed", "Publish"):
            continue
        if p.is_dir():
            shutil.copytree(p, dist / p.name, dirs_exist_ok=True)
        else:
            shutil.copy2(p, dist / p.name)


def build(folder, project, cfg, work, log):
    from ..build import BuildError, BuildResult, make_icon, startup_language
    folder = Path(folder).absolute()     # not resolve(): a deep project builds through its short alias (paths.short_alias)
    lang = startup_language(project)
    plugin = _plugin(lang)
    tc = toolchain(lang, log)
    env = dict(os.environ, PATH=str(Path(tc["driver"]).parent) + os.pathsep + os.environ.get("PATH", ""))
    nat = Path(work) / "native"
    if nat.exists():
        shutil.rmtree(nat, ignore_errors=True)
    nat.mkdir(parents=True, exist_ok=True)
    dist = Path(work) / "dist" / cfg.exe_base()
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True)
    exe = dist / (cfg.exe_base() + ".exe")
    console = plugin.console_program(project)
    notes = []
    if cfg.update.enabled and cfg.update.url:
        notes.append("The automatic update check is not part of native builds.")
        log("Note: the update check (Python) is not included in a native exe")

    # resources: manifest, version, icon (+ the forms and their images)
    rc = rg.write_resources(nat, project, folder, cfg, log, gui=not console,
                            icon=make_icon(folder, cfg, nat / "icon", log))
    res = rg.compile_resources(tc["windres"], rc, log)

    for name in ("radgui.h", "radgui.hpp"):
        shutil.copy2(CLIENTS / name, nat / name)
    shutil.copy2(rg.RADFORMS_H, nat / "radforms.h")
    # MinGW links default-manifest.o (asInvoker, no visual styles) when it finds one: an empty object of
    # that name found first through -B keeps our manifest the only one
    from ._ffi import nomanifest_dir                     # a folder without spaces (gcc -B + ld)
    nomf = nomanifest_dir(nat)
    nomf.mkdir(parents=True, exist_ok=True)
    (nomf / "empty.c").write_text("/* replaces MinGW's default-manifest.o */\n", encoding="utf-8")
    if _run([tc["cc"], "-c", str(nomf / "empty.c"), "-o", str(nomf / "default-manifest.o")], nat, log, env) != 0:
        raise BuildError("gcc does not work (see the output above)")
    flags = ["-B", str(nomf) + os.sep] + SIZE_FLAGS + (["-mconsole"] if console else ["-mwindows"])
    inc = ["-I", str(nat), "-I", str(folder)]
    objs = [str(res)]
    if not console:
        rf_obj = nat / "radforms.o"
        cmd = [tc["cc"], "-std=gnu99", "-c", "-Os", "-ffunction-sections", "-fno-asynchronous-unwind-tables", "-Wall", "-I", str(nat), str(rg.RADFORMS_C), "-o", str(rf_obj)]
        if _run(cmd, nat, log, env) != 0:
            raise BuildError("radforms.c did not compile (see the output above)")
        objs.append(str(rf_obj))
        mods = rg.modules_for(rg.project_types(project))       # control modules the forms use
        if mods:
            (nat / "_radmodules.c").write_text(rg.modules_source(mods), encoding="utf-8")
            for src in [*mods, nat / "_radmodules.c"]:
                o = nat / (Path(src).stem + ".o")
                if _run([tc["cc"], "-std=gnu99", "-c", "-Os", "-ffunction-sections", "-fno-asynchronous-unwind-tables",
                         "-I", str(nat), "-I", str(rg.MODULES_DIR), str(src), "-o", str(o)], nat, log, env) != 0:
                    raise BuildError(f"{Path(src).name} did not compile (see the output above)")
                objs.append(str(o))

    handlers = plugin.handlers_in_project(folder, project)
    srcs: list[str]
    if lang == "fortran-bridge":
        mods = plugin.module_files(project)
        try:
            mods += [p for p in plugin.proxy_sources(folder, project) if p not in mods]
        except Exception:  # noqa: BLE001
            pass
        user = [str(folder / s) for s in plugin.ordered_sources(folder, mods + plugin.form_files(project))]
        moddir = nat / "mod"
        moddir.mkdir(exist_ok=True)
        if console:
            srcs = user
        else:
            (nat / "radgui.f90").write_text(fortran_native_module(), encoding="utf-8")
            (nat / "_radnative_main.f90").write_text(fortran_main(plugin, project, handlers), encoding="utf-8")
            srcs = [str(nat / "radgui.f90")] + user + [str(nat / "_radnative_main.f90")]
        cmd = [tc["driver"], *flags, "-J", str(moddir), "-I", str(moddir), "-o", str(exe), *srcs, *objs, "-static"]
    else:
        cpp = lang == "cpp-bridge"
        user = [str(folder / s) for s in plugin.module_files(project) + plugin.form_files(project)
                if s.lower().endswith(plugin.code_ext)]
        if console:
            srcs = user
        else:
            main = nat / ("_radnative_main" + plugin.code_ext)
            main.write_text(c_main(plugin, handlers, _radfuncs(folder, project, plugin), cpp), encoding="utf-8")
            srcs = user + [str(main)]
        cflags, lflags = plugin._vcpkg_flags(folder, "gcc")
        std = ["-std=gnu++17"] if cpp else ["-std=gnu11", "-fno-asynchronous-unwind-tables"]
        cmd = [tc["driver"], *std, *flags, *inc, *(cflags.split() if cflags else []), "-o", str(exe), *srcs, *objs,
               *(lflags.split() if lflags else []), "-static"]
        if any("winsock" in _read(Path(s)).lower() or "ws2tcpip" in _read(Path(s)).lower() for s in srcs):
            cmd.append("-lws2_32")
    cmd += ([] if console else WIN_LIBS) + ["-lm"]
    if _run(cmd, folder, log, env) != 0:
        raise BuildError(f"The native {plugin.display_name.split(' (')[0]} build failed (see the output above)")
    if not exe.is_file():
        raise BuildError(f"{exe.name} was not created")
    _copy_data(folder, cfg, dist, log)
    size = exe.stat().st_size
    log(f"Native exe: {exe.name} {size // 1024} KB ({size:,} bytes) - no Python, no extra DLLs")
    return BuildResult(dist, exe.name, "native", notes)


__all__ = ["LANGS", "NAME", "build", "c_main", "check", "download_winlibs", "fortran_main", "fortran_native_module",
           "toolchain"]
