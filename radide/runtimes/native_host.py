"""The native GUI Bridge host (radide/runtimes/native/radbridge/radbridge.c): F5 of every GUI Bridge language with
Win32 forms (radforms) instead of the Python / Tk host radide/runtimes/bridge.py. No Qt here.

    radbridge.exe <forms.radf> [--build "<cmd>"] -- <program> [args]      same protocol, same arguments

* the host is built ONCE (not per project) with MinGW-w64 from radforms.c + every control module + radbridge.c,
  into %LOCALAPPDATA%\\RADIDE\\radbridge\\<hash of the sources>\\radbridge.exe. F5 never waits for it: when it is
  not built yet, start_build() builds it in the background and that run uses the Python host;
* the form description of the project (radforms_gen.description: all forms, the startup form) is written at F5 to
  <project>/_build/radnative/forms.radf; images stay files (RAD_BASE_DIR = the project folder);
* radide/languages/bridgebase.py run_spec uses it (radbridge_spec) when the project can run natively.

Python host instead (always correct, never silent - the reason is printed in the Output window):
  project.radproj "nativeHost": false, forms that radforms cannot draw (radforms_gen.unsupported), forms of
  several languages in one program, no MinGW-w64 (Build > Build Native Exe installs it), or not Windows.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "native" / "radbridge" / "radbridge.c"
LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RADIDE" / "radbridge"
FORMS_DIR = "_build/radnative"
KEY = "nativeHost"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_LOCK = threading.Lock()
_BUILDING: threading.Thread | None = None
LAST_ERROR = ""


def _sources() -> list[Path]:
    from ..deploy.native import radforms_gen as rg
    mods = rg.modules_for(set(rg.module_classes()))
    return [Path(rg.RADFORMS_C), Path(rg.RADFORMS_H), *map(Path, mods), SOURCE]


def version() -> str:
    h = hashlib.sha1()
    for p in _sources():
        h.update(p.name.encode() + b"|")
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def host_path() -> Path:
    return LOCAL / version() / "radbridge.exe"


def is_built() -> bool:
    try:
        return host_path().is_file()
    except OSError:
        return False


def mingw_ready() -> bool:
    try:
        from ..deploy.native.win32_c import find_tool
        return bool(find_tool("gcc")) and os.name == "nt"
    except Exception:  # noqa: BLE001
        return False


def build(log=None) -> Path | None:
    """Compile radbridge.exe (a few seconds); None on failure (LAST_ERROR has the reason)."""
    global LAST_ERROR
    log = log or (lambda _s: None)
    from ..deploy.native import _ffi
    from ..deploy.native import radforms_gen as rg
    with _LOCK:
        exe = host_path()
        if exe.is_file():
            return exe
        try:
            tc = _ffi.mingw(log)
        except Exception as e:  # noqa: BLE001
            LAST_ERROR = f"MinGW-w64: {e}"
            return None
        work = _ffi.fresh(exe.parent / "work")
        env = _ffi.tool_env(Path(tc["cc"]).parent)
        mods = rg.modules_for(set(rg.module_classes()))
        objs = []
        out: list[str] = []
        try:
            for src in [rg.RADFORMS_C, *mods]:
                o = work / (Path(src).stem + ".o")
                if _ffi.run([tc["cc"], *_ffi.RF_CFLAGS, "-I", str(rg.RADFORMS_DIR), str(src), "-o", str(o)], work,
                            out.append, env) != 0:
                    raise RuntimeError(f"{Path(src).name} did not compile")
                objs.append(str(o))
            (work / "_radmodules.c").write_text(rg.modules_source(mods), encoding="utf-8")
            mo = work / "_radmodules.o"
            if _ffi.run([tc["cc"], *_ffi.RF_CFLAGS, "-I", str(rg.RADFORMS_DIR), str(work / "_radmodules.c"), "-o",
                         str(mo)], work, out.append, env) != 0:
                raise RuntimeError("_radmodules.c did not compile")
            # Common Controls 6 + DPI awareness + UTF-8 code page, like the native exes
            from types import SimpleNamespace
            cfg = SimpleNamespace(numeric_version=lambda: "1.0.0.0", exe_base=lambda: "radbridge",
                                  app_name="RAD IDE forms host", publisher="Musoftware", version="1.0.0")
            rc = rg.write_resources(work / "res", None, work, cfg, out.append, gui=False)
            res = rg.compile_resources(tc["windres"], rc, out.append)
            tmp = work / "radbridge.exe"
            cmd = [tc["cc"], "-std=gnu99", "-Os", "-s", "-mconsole",
                   "-ffunction-sections", "-Wl,--gc-sections", "-I", str(rg.RADFORMS_DIR), str(SOURCE), str(mo),
                   *objs, str(res), "-static", *(f"-l{x}" for x in _ffi.WIN_LIBS), "-lm", "-o", str(tmp)]
            if _ffi.run(cmd, work, out.append, env) != 0 or not tmp.is_file():
                raise RuntimeError("radbridge.c did not link")
        except Exception as e:  # noqa: BLE001
            LAST_ERROR = f"{e}\n" + "\n".join(ln for ln in out if not ln.startswith("> "))[-3000:]
            log("Native forms host: " + LAST_ERROR)
            return None
        shutil.copy2(tmp, exe)
        shutil.rmtree(work, ignore_errors=True)
        LAST_ERROR = ""
        return exe


def start_build() -> None:
    """Build the host in the background (once); F5 meanwhile uses the Python host."""
    global _BUILDING
    if is_built() or not mingw_ready() or (_BUILDING is not None and _BUILDING.is_alive()):
        return
    _BUILDING = threading.Thread(target=build, daemon=True, name="radbridge-build")
    _BUILDING.start()


# ====================================================================== projects
def why_not(folder: Path, project, plugin) -> str:
    """'' when the project's forms can be drawn by radbridge, else the reason (shown in the Output window)."""
    if os.name != "nt":
        return "not Windows"
    if os.environ.get("RADIDE_NATIVE_HOST") == "0":
        return "turned off (RADIDE_NATIVE_HOST=0)"
    if project.extra.get(KEY) is False or str(project.extra.get(KEY, "")).lower() in ("false", "0", "python"):
        return f'project.radproj says "{KEY}": false'
    if not project.forms:
        return "a console program (no forms)"
    if any(project.form_language(n) != plugin.id for n in project.forms):
        return "the program has forms of several languages (the Python host runs them together)"
    try:
        from ..deploy.native import radforms_gen as rg
        reasons = rg.unsupported(project, Path(folder), plugin.id)
    except Exception as e:  # noqa: BLE001
        return f"the forms could not be read ({e})"
    if reasons:
        return "radforms cannot draw: " + "; ".join(reasons[:3])
    if not mingw_ready():
        return "MinGW-w64 is not installed (Build > Build Native Exe installs it)"
    if not is_built():
        start_build()
        return "the native forms host is being built (the next F5 uses it)"
    return ""


def write_forms(folder: Path, project) -> Path:
    from ..deploy.native import radforms_gen as rg
    text, _images = rg.description(project, Path(folder), project.name)
    out = Path(folder) / FORMS_DIR / "forms.radf"
    out.parent.mkdir(parents=True, exist_ok=True)
    gi = out.parent / ".gitignore"
    if not gi.exists():
        gi.write_text("*\n", encoding="utf-8")
    out.write_bytes(text.encode("utf-8"))
    return out


def radbridge_args(forms: Path, build: str | None, program: list[str]) -> list[str]:
    return [str(forms), *(["--build", build] if build else []), "--", *program]
