"""Build step of Build > Publish: turn a project into a folder with a runnable program.

Kinds (PublishConfig.build_kind, "auto" picks from the startup form's language):

  pyinstaller  Python Tk / Qt / pygame / Kivy / Arcade - PyInstaller one-folder build with the project's own
               .venv (or a private build venv made from the configured Python, so nothing is installed into
               the user's global Python); version resource, icon, data files, optional update check.
  vbrun        VB6 / BASIC - the bundled VB interpreter frozen with PyInstaller + the project files.
  bridge       GUI Bridge languages (C, C++, Rust, Fortran, Go, C#, Java, JS, ...) - the language's own build,
               then the bridge host frozen with PyInstaller; native programs get their MinGW DLLs copied.
  ring2exe     RingQt - ring2exe -dist -allruntime -gui -qt.
  flutter      flutter build windows --release.
  folder       an already built program folder (prebuilt_dir + prebuilt_exe).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ..model import Project
from . import tools
from .config import PublishConfig, resolve

from ..paths import python_root as _python_root  # noqa: E402
IDE_ROOT = _python_root()   # a real Python imports radide from here (not _internal in a release build)

SKIP_DIRS = {".venv", "venv", "env", "__pycache__", ".git", ".hg", ".svn", ".radide", ".radide_backup", "build",
             "dist", "node_modules", ".dart_tool", "target", "bin", "obj", ".idea", ".vscode", ".pytest_cache"}
SKIP_FILES_PY = {".py", ".pyc", ".pyo", ".form", ".radproj", ".radsln", ".iss", ".spec"}
SKIP_NAMES = {"publish.json", "project.radproj"}

# modules the frozen VB / bridge host never needs (keeps the program small)
HOST_EXCLUDES = ["PyQt6", "PyQt5", "PySide6", "PySide2", "jedi", "parso", "numpy", "matplotlib", "pygame", "kivy",
                 "capstone", "pefile", "paramiko", "keyring", "pygments", "IPython", "pytest", "setuptools"]
PY_EXCLUDES = ["pytest", "IPython"]


class BuildError(Exception):
    pass


@dataclass
class BuildResult:
    dist: Path                       # folder with the whole program
    exe: str                         # main exe, relative to dist
    kind: str
    notes: list[str] = field(default_factory=list)      # e.g. "the user's PC needs Node.js"
    python_based: bool = False       # radupdate.py was compiled in


# ------------------------------------------------------------------ helpers
def startup_language(project: Project) -> str:
    if project.startup:
        return project.form_languages.get(project.startup, project.language)
    return project.language


def detect_kind(project: Project, cfg: PublishConfig) -> str:
    if cfg.build_kind and cfg.build_kind != "auto":
        return cfg.build_kind
    lang = startup_language(project)
    if getattr(cfg, "prefer_native", True):
        from .native import builder_for
        if builder_for(lang) is not None:
            return "native"
    return fallback_kind(lang)


def fallback_kind(lang: str) -> str:
    """The kind used without a native builder (and when a native build falls back)."""
    if lang.startswith("python") or lang in ("pygame", "kivy", "python-arcade"):
        return "pyinstaller"
    if lang == "vb-basic":
        return "vbrun"
    if lang.startswith("ring"):
        return "ring2exe"
    if lang == "flutter":
        return "flutter"
    if lang in ("asm-nasm", "asm-fasm", "asm-masm", "asm-gas"):
        return "asm"
    if lang.endswith("-bridge") or lang in ("javascript", "typescript", "php"):
        return "bridge"
    if lang == "rust-cargo":
        return "cargo"
    return "folder"


KIND_NAMES = {
    "auto": "Automatic (from the project's language)",
    "native": "Native exe without Python (smallest)",
    "pyinstaller": "Python program (PyInstaller)",
    "vbrun": "VB6 program (bundled VB runtime)",
    "bridge": "GUI Bridge program (language build + bridge host)",
    "ring2exe": "Ring program (ring2exe)",
    "flutter": "Flutter Windows app (flutter build windows)",
    "asm": "Assembly program (console exe as built; forms through the bridge host)",
    "folder": "Already built program folder",
    "cargo": "Rust program (cargo build --release)",
}


def run(cmd, cwd: Path, log, env=None, shell=False) -> int:
    shown = cmd if isinstance(cmd, str) else " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd)
    log(f"> {shown}")
    p = subprocess.Popen(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace", env=env, shell=shell, creationflags=tools.NO_WINDOW)
    assert p.stdout is not None
    for line in p.stdout:
        log(line.rstrip("\n"))
    return p.wait()


def out_root(folder: Path, cfg: PublishConfig) -> Path:
    return resolve(folder, cfg.output_dir or "Publish") or folder / "Publish"


def data_entries(folder: Path, cfg: PublishConfig, skip_ext=SKIP_FILES_PY) -> list[Path]:
    """Top-level files/folders of the project the program may read at run time (images, data, ...)."""
    out_dir = out_root(folder, cfg).resolve()
    items = []
    for p in sorted(Path(folder).iterdir()):
        if p.name.startswith(("_radide", ".")) or p.name in SKIP_NAMES:
            continue
        if p.is_dir():
            if p.name in SKIP_DIRS or p.resolve() == out_dir:
                continue
            items.append(p)
        elif p.suffix.lower() not in skip_ext:
            items.append(p)
    return items


def make_icon(folder: Path, cfg: PublishConfig, gen: Path, log) -> Path | None:
    """The configured icon as .ico (PNG/JPG/BMP are converted with Pillow)."""
    src = resolve(folder, cfg.icon)
    if not src:
        return None
    if not src.is_file():
        log(f"Icon not found: {src}")
        return None
    if src.suffix.lower() == ".ico":
        return src
    try:
        from PIL import Image
    except ImportError:
        log("Pillow is not installed: the icon must be an .ico file")
        return None
    gen.mkdir(parents=True, exist_ok=True)
    ico = gen / "app.ico"
    img = Image.open(src).convert("RGBA")
    side = max(img.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    square.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return ico


def version_file(cfg: PublishConfig, gen: Path) -> Path:
    """PyInstaller version resource: publisher, product and version in the exe's Properties > Details."""
    nums = tuple(int(n) for n in cfg.numeric_version().split("."))
    exe = cfg.exe_base() + ".exe"

    def s(k, v):
        return f"StringStruct({k!r}, {str(v)!r})"
    strings = [s("CompanyName", cfg.publisher or cfg.app_name), s("FileDescription", cfg.app_name),
               s("FileVersion", cfg.version), s("InternalName", cfg.exe_base()), s("OriginalFilename", exe),
               s("ProductName", cfg.app_name), s("ProductVersion", cfg.version),
               s("LegalCopyright", f"(c) {cfg.publisher}" if cfg.publisher else "")]
    text = (f"VSVersionInfo(\n  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, "
            f"OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),\n"
            f"  kids=[StringFileInfo([StringTable('040904B0', [{', '.join(strings)}])]),\n"
            f"        VarFileInfo([VarStruct('Translation', [1033, 1200])])]\n)\n")
    gen.mkdir(parents=True, exist_ok=True)
    p = gen / "version_info.txt"
    p.write_text(text, encoding="utf-8")
    return p


def copy_tree(src: Path, dst: Path, skip_ext: set[str] = frozenset()) -> None:
    def ignore(d, names):
        return [n for n in names if n in SKIP_DIRS or n == "Publish" or n.startswith("_radide")
                or Path(n).suffix.lower() in skip_ext]
    shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True)


def project_python(folder: Path, interpreter: str, log) -> str:
    """The project's .venv python (PyInstaller installed into it), else a private build env."""
    for rel in ((".venv", "Scripts", "python.exe"), (".venv", "bin", "python")):
        p = Path(folder).joinpath(*rel)
        if p.is_file():
            log(f"Using the project's virtual environment: {p}")
            if not tools.ensure_pyinstaller(str(p), log):
                raise BuildError("PyInstaller could not be installed into the project's .venv")
            return str(p)
    base = interpreter or tools.ide_python()
    if tools.has_pyinstaller(base) and Path(base).resolve().parent.parent == (IDE_ROOT / ".venv").resolve():
        return base             # the IDE's own .venv already has PyInstaller
    py = tools.build_env_python(base, log)
    if not py:
        raise BuildError(f"No Python with PyInstaller (base interpreter: {base})")
    return py


# ------------------------------------------------------------------ PyInstaller (shared)
def pyinstaller(python: str, script: Path, folder: Path, cfg: PublishConfig, work: Path, log, *,
                paths=(), datas=(), hidden=(), excludes=(), hooks=(), icon=None, collect=()) -> Path:
    dist = work / "dist"
    args = [python, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--name", cfg.exe_base(),
            "--distpath", str(dist), "--workpath", str(work / "work"), "--specpath", str(work),
            "--version-file", str(version_file(cfg, work / "gen"))]
    args.append("--console" if cfg.console else "--windowed")
    for p in paths:
        args += ["--paths", str(p)]
    sep = ";" if os.name == "nt" else ":"
    for src, dst in datas:
        args += ["--add-data", f"{src}{sep}{dst}"]
    for h in hidden:
        args += ["--hidden-import", h]
    for e in excludes:
        args += ["--exclude-module", e]
    for h in hooks:
        args += ["--runtime-hook", str(h)]
    for c in collect:                       # "data:<pkg>" / "bin:<pkg>" = only the package's data / DLLs
        kind, _, pkg = c.rpartition(":")
        args += [{"data": "--collect-data", "bin": "--collect-binaries"}.get(kind, "--collect-all"), pkg]
    if icon:
        args += ["--icon", str(icon)]
    args.append(str(script))
    env = dict(os.environ, PYTHONUTF8="1")
    env.pop("PYTHONPATH", None)
    if run(args, folder, log, env=env) != 0:
        raise BuildError("PyInstaller failed (see the output above)")
    out = dist / cfg.exe_base()
    if not (out / (cfg.exe_base() + ".exe")).is_file() and not (out / cfg.exe_base()).is_file():
        raise BuildError(f"PyInstaller did not create {out}")
    return out


def _update_args(cfg: PublishConfig, gen: Path):
    if not (cfg.update.enabled and cfg.update.url):
        return [], [], []
    from .update import write_python_files
    mod, hook = write_python_files(cfg, gen)
    return [mod.parent], ["radupdate"], [hook] if hook else []


DB_DRIVERS = {"mysql": ["pymysql"], "postgresql": ["psycopg", "psycopg_binary", "psycopg_c", "psycopg_pool"],
              "odbc": ["pyodbc"]}


def unused_db_drivers(folder: Path, project: Project) -> list[str]:
    """Database driver packages the data-binding runtime only imports for a connection kind the project's forms
    do not use (Data Sources, radide/databinding_sql.py) - excluded from PyInstaller, unless the project's own
    code imports them.  A SQLite-only program would otherwise carry psycopg + numpy + cryptography (~50 MB)."""
    kinds: set[str] = set()
    for name in project.forms:
        try:
            data = json.loads(project.form_path(name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []                   # cannot tell: exclude nothing
        for src in data.get("dbsources") or []:
            kinds.add(str((src.get("connection") or {}).get("kind", "")))
    code = ""
    for p in Path(folder).glob("*.py"):
        if not p.name.endswith("_designer.py"):
            try:
                code += p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
    out = []
    for kind, mods in DB_DRIVERS.items():
        if kind not in kinds:
            out += [m for m in mods if f"import {m}" not in code and f"from {m}" not in code]
    return out


# ------------------------------------------------------------------ kinds
def build_python(folder: Path, project: Project, cfg: PublishConfig, work: Path, interpreter: str, log) -> BuildResult:
    from ..languages import get_plugin
    lang = startup_language(project)
    plugin = get_plugin(lang)
    script = folder / plugin.code_file(project.startup) if project.startup else None
    if script is None or not script.is_file():
        cands = [folder / n for n in ("main.py", "app.py", f"{project.name}.py")]
        script = next((c for c in cands if c.is_file()), None)
    if script is None:
        raise BuildError("No startup file: set the startup form (Project > Properties)")
    python = project_python(folder, interpreter, log)
    gen = work / "gen"
    upaths, uhidden, uhooks = _update_args(cfg, gen)
    hidden = [Path(m).stem for m in project.modules if m.endswith(".py")]
    # every top-level module of the project: games load their scenes with importlib (rad3d.load_scene ->
    # "Scene1_designer", pygame / arcade scenes), which PyInstaller cannot see ("No module named 'Scene1_designer'")
    hidden += [f.stem for f in Path(folder).glob("*.py") if f.stem.isidentifier() and f.stem != "setup"]
    for f in project.forms:
        try:
            fp = get_plugin(project.form_languages.get(f, project.language))
            hidden += [Path(fp.code_file(f)).stem, Path(fp.designer_file(f)).stem]
        except (KeyError, AttributeError):
            pass
    datas = [(p, p.name if p.is_dir() else ".") for p in data_entries(folder, cfg)]
    collect = []
    if lang == "kivy":
        # PyInstaller's own hook-kivy brings the modules + SDL2/GLEW DLLs; --collect-all kivy failed on
        # kivy.garden (its __path__ is a str, pkgutil.iter_modules raises "path must be None or list")
        collect.append("data:kivy")
    elif lang == "python-ursina":
        # Panda3D loads its display module (libpandagl.dll) and etc/Config.prc at run time - PyInstaller does not
        # see them; ursina needs its built-in models / textures / fonts ("No graphics pipe is available!")
        collect += ["data:ursina", "data:panda3d", "bin:panda3d"]
    out = pyinstaller(python, script, folder, cfg, work, log, paths=[folder, *upaths], datas=datas,
                      hidden=sorted(set(hidden) | set(uhidden)),
                      excludes=PY_EXCLUDES + unused_db_drivers(folder, project), hooks=uhooks,
                      icon=make_icon(folder, cfg, gen, log), collect=collect)
    return BuildResult(out, cfg.exe_base() + ".exe", "pyinstaller", python_based=True)


LAUNCH_VB = '''"""RAD IDE published VB6 program: the bundled VB runtime runs the project files in .\\app."""
import os
import sys

APP = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "app")
os.chdir(APP)
from radide.runtimes import vbrun  # noqa: E402

vbrun.main([APP])
'''

LAUNCH_BRIDGE = '''"""RAD IDE published GUI Bridge program: the bridge host draws the forms, the program runs in .\\app."""
import json
import os
import sys

APP = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "app")
os.chdir(APP)
with open(os.path.join(APP, "_radlaunch.json"), encoding="utf-8") as f:
    CFG = json.load(f)
os.environ["RAD_HANDLERS"] = CFG.get("handlers", "")
os.environ["PATH"] = APP + os.pathsep + os.environ.get("PATH", "")
from radide.runtimes import bridge  # noqa: E402

bridge.main([APP, "--"] + [a.replace("{app}", APP) for a in CFG["program"]])
'''


def _host_build(folder: Path, cfg: PublishConfig, work: Path, launcher: str, log) -> Path:
    gen = work / "gen"
    gen.mkdir(parents=True, exist_ok=True)
    script = gen / f"{cfg.exe_base()}_launcher.py"
    script.write_text(launcher, encoding="utf-8")
    upaths, uhidden, uhooks = _update_args(cfg, gen)
    py = tools.ide_python()
    if not tools.ensure_pyinstaller(py, log):
        raise BuildError("PyInstaller is not installed in the IDE's Python")
    hidden = ["radide.runtimes.vbrun", "radide.runtimes.vbfso", "radide.languages.python_tk",
              "radide.languages._refs", *uhidden,
              # the generated Tk designer code is exec'd at run time: PyInstaller cannot see its imports
              "tkinter.ttk", "tkinter.font", "tkinter.filedialog", "tkinter.colorchooser", "tkinter.messagebox",
              "tkinter.simpledialog", "tkinter.scrolledtext"]
    # the built-in controls are component packages (component.json + runtime/*.py read from disk): without
    # them radide.controls has no control types and the program stops with KeyError: 'DataGridView'
    pkg_root = Path(__file__).resolve().parents[1]
    datas = [(pkg_root / "components" / "builtin", "radide/components/builtin")]
    return pyinstaller(py, script, folder, cfg, work, log, paths=[IDE_ROOT, *upaths], hidden=hidden, datas=datas,
                       excludes=HOST_EXCLUDES, hooks=uhooks, icon=make_icon(folder, cfg, gen, log))


def build_vbrun(folder: Path, project: Project, cfg: PublishConfig, work: Path, interpreter: str, log) -> BuildResult:
    out = _host_build(folder, cfg, work, LAUNCH_VB, log)
    copy_tree(folder, out / "app", skip_ext={".iss", ".spec"})
    return BuildResult(out, cfg.exe_base() + ".exe", "vbrun", python_based=True)


def _pe_imports(path: Path) -> list[str]:
    try:
        import pefile
    except ImportError:
        return []
    try:
        pe = pefile.PE(str(path), fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
        names = [e.dll.decode("ascii", "replace") for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])]
        pe.close()
        return names
    except Exception:  # noqa: BLE001 - not a PE file
        return []


def copy_runtime_dlls(exe: Path, search: list[Path], dest: Path, log) -> list[str]:
    """Copy the DLLs *exe* needs that live in toolchain folders (libgcc, libstdc++, libgfortran ...)."""
    copied, todo, seen = [], [exe], set()
    while todo:
        cur = todo.pop()
        for dll in _pe_imports(cur):
            key = dll.lower()
            if key in seen:
                continue
            seen.add(key)
            for d in search:
                cand = d / dll
                if cand.is_file():
                    shutil.copy2(cand, dest / cand.name)
                    copied.append(cand.name)
                    todo.append(cand)
                    break
    if copied:
        log("Runtime DLLs copied: " + ", ".join(copied))
    return copied


def build_bridge(folder: Path, project: Project, cfg: PublishConfig, work: Path, interpreter: str, log) -> BuildResult:
    from ..languages import get_plugin
    plugin = get_plugin(startup_language(project))
    if not plugin.tool():
        raise BuildError(f"{plugin.display_name}: the compiler/interpreter was not found. {plugin.install_hint}")
    plugin.prepare(folder, project)
    build = plugin.build_command(folder, project)
    if build:
        if run(build, folder, log, shell=True) != 0:
            raise BuildError(f"The {plugin.display_name} build failed")
    program = plugin.run_command(folder, project)
    roots = {str(folder), str(Path(folder).resolve())}
    rel, notes = [], []
    for i, a in enumerate(program):
        a = str(a)
        for r in sorted(roots, key=len, reverse=True):
            if a.lower().startswith(r.lower()):
                a = "{app}" + a[len(r):]
                break
        rel.append(a)
        if i == 0 and not a.startswith("{app}"):
            notes.append(f"The user's PC needs {Path(a).stem} ({plugin.display_name} runtime) installed and on PATH.")
            rel[0] = Path(a).name if Path(a).is_absolute() else a
    if not project.forms and rel and rel[0].startswith("{app}") and str(program[0]).lower().endswith(".exe") \
            and Path(str(program[0])).is_file():
        # a console program (no forms, its own main) needs no bridge host: the windowed launcher would hide its
        # output and its exit code - publish the compiled exe itself (+ the toolchain DLLs it imports)
        return _publish_console_exe(Path(str(program[0])), plugin, cfg, work, log, notes)
    out = _host_build(folder, cfg, work, LAUNCH_BRIDGE, log)
    app = out / "app"
    copy_tree(folder, app)
    base = Path(folder).resolve()
    for a in program:                   # build outputs often live in skipped folders (bin, obj, target)
        p = Path(str(a))
        if not p.is_absolute() or not p.exists() or not str(p.resolve()).lower().startswith(str(base).lower()):
            continue
        src_dir = p.resolve().parent if p.is_file() else p.resolve()
        if src_dir != base:
            shutil.copytree(src_dir, app / src_dir.relative_to(base), dirs_exist_ok=True)
        elif p.is_file():
            shutil.copy2(p, app / p.name)
    if rel[0].startswith("{app}"):      # a native program: copy the toolchain DLLs it needs
        app_exe = app / rel[0][len("{app}"):].lstrip("\\/")
        search = []
        gcc = getattr(plugin, "gcc", None)
        if callable(gcc) and gcc():
            search.append(Path(gcc()).parent)
        search += [Path(p) for p in os.environ.get("PATH", "").split(os.pathsep)
                   if p and "mingw" in p.lower() and Path(p).is_dir()]
        if app_exe.is_file():
            copy_runtime_dlls(app_exe, search, app_exe.parent, log)
    handlers = ",".join(plugin.handlers_in_project(folder, project))
    (app / "_radlaunch.json").write_text(json.dumps({"program": rel, "handlers": handlers}, indent=2),
                                         encoding="utf-8")
    return BuildResult(out, cfg.exe_base() + ".exe", "bridge", notes, python_based=True)


def _publish_console_exe(exe: Path, plugin, cfg: PublishConfig, work: Path, log, notes) -> BuildResult:
    """A GUI Bridge language's console program: the language's own exe, renamed to the app name."""
    out = work / "dist" / cfg.exe_base()
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    target = out / (cfg.exe_base() + ".exe")
    shutil.copy2(exe, target)
    search = []
    gcc = getattr(plugin, "gcc", None)
    if callable(gcc) and gcc():
        search.append(Path(gcc()).parent)
    search += [Path(p) for p in os.environ.get("PATH", "").split(os.pathsep)
               if p and "mingw" in p.lower() and Path(p).is_dir()]
    copy_runtime_dlls(target, search, out, log)
    log(f"Console program: {target.name} ({target.stat().st_size:,} bytes) - no bridge host, no Python")
    return BuildResult(out, target.name, "console", list(notes), python_based=False)


# Ring library file (load "...") -> ring2exe runtime libraries (ring/tools/ring2exe/libs/*.ring)
RING_LIBS = {"guilib.ring": ["qt"], "lightguilib.ring": ["lightguilib"], "qtcore.ring": ["qtcore"],
             "sqlitelib.ring": ["sqlite"], "httplib.ring": ["httplib"], "raylib.ring": ["raylib"],
             "mysqllib.ring": ["mysql"], "odbclib.ring": ["odbc"], "postgresqllib.ring": ["postgresql"],
             "openssllib.ring": ["openssl"], "internetlib.ring": ["internetlib"], "libcurl.ring": ["libcurl"],
             "jsonlib.ring": ["jsonlib"], "cjson.ring": ["jsonlib"], "sockets.ring": ["sockets"],
             "threads.ring": ["threads"], "stbimage.ring": ["stbimage"], "libuv.ring": ["libuv"],
             "libui.ring": ["libui"], "consolecolors.ring": ["consolecolors"], "murmurhashlib.ring": ["murmurhash"],
             "fastpro.ring": ["fastpro"], "freeglut.ring": ["freeglut"], "allegro.ring": ["allegro"],
             "gamelib.ring": ["allegro"], "gameengine.ring": ["allegro"],
             # the standard library loads the database / internet extensions
             "stdlib.ring": ["odbc", "mysql", "sqlite", "internetlib", "openssl", "postgresql"]}
RING_PURE = {"stdlibcore.ring", "stdfunctions.ring", "stdlibclasses.ring", "matrixlib.ring", "csvlib.ring",
             "objectslib.ring", "naturallib.ring", "naturalsyntaxon.ring", "naturalsyntaxoff.ring", "codegenlib.ring"}
RING_GUI_LIBS = {"qt", "lightguilib", "raylib", "allegro", "freeglut", "libui"}


def ring2exe_options(folder: Path, main: str) -> list[str]:
    """ring2exe options for a project: only the runtime libraries its files load (instead of -allruntime, which
    copies every Ring extension: ~320 MB) and -gui only for GUI programs, so console / web programs keep their
    console.  An unknown extension falls back to -allruntime."""
    import re as _re
    libs, seen, todo, unknown = {"cruntime"}, set(), [Path(folder) / main], False
    while todo:
        f = todo.pop()
        if f in seen or not f.is_file():
            continue
        seen.add(f)
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in _re.finditer(r'^\s*load\s+(?:package\s+)?["\']([^"\']+)["\']', text, _re.I | _re.M):
            name = m.group(1).replace("\\", "/")
            local = (f.parent / name)
            if local.is_file() and not name.startswith("/"):
                todo.append(local.resolve())
                continue
            base = name.rsplit("/", 1)[-1].lower()
            if base in RING_LIBS:
                libs.update(RING_LIBS[base])
            elif base not in RING_PURE:
                unknown = True
    if unknown:
        return ["-dist", "-allruntime", "-gui", "-qt"]
    opts = ["-dist"] + [f"-{n}" for n in sorted(libs)]
    if libs & RING_GUI_LIBS:
        opts.append("-gui")
    return opts


def build_ring(folder: Path, project: Project, cfg: PublishConfig, work: Path, interpreter: str, log) -> BuildResult:
    from ..languages import get_plugin
    plugin = get_plugin(startup_language(project))
    ring = interpreter or plugin.find_interpreter("")
    ring2exe = Path(ring).with_name("ring2exe.exe") if ring else None
    if not ring2exe or not ring2exe.is_file():
        raise BuildError("ring2exe.exe was not found next to ring.exe (install Ring from ring-lang.net)")
    main = plugin.run_spec(folder, project.startup, ring).args[0]          # writes _radide_run.ring
    named = folder / f"{cfg.exe_base()}.ring"
    if named.exists() and named.name != main:
        raise BuildError(f"{named.name} already exists: choose another exe name")
    shutil.copy2(folder / main, named)
    opts = ring2exe_options(folder, main)
    log("ring2exe options: " + " ".join(opts))
    try:
        if run([str(ring2exe), named.name, *opts], folder, log) != 0:
            raise BuildError("ring2exe failed")
    finally:
        named.unlink(missing_ok=True)
    target = folder / "target" / "windows"
    exe = target / (cfg.exe_base() + ".exe")
    if not exe.is_file():
        found = list(target.glob("*.exe")) if target.is_dir() else []
        if not found:
            raise BuildError(f"ring2exe did not create {exe}")
        exe = found[0]
    out = work / "dist" / cfg.exe_base()
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(target, out)
    for p in data_entries(folder, cfg, skip_ext={".ring", ".form", ".radproj", ".iss"}):
        if p.is_dir():
            shutil.copytree(p, out / p.name, dirs_exist_ok=True)
        else:
            shutil.copy2(p, out / p.name)
    return BuildResult(out, exe.name, "ring2exe")


def build_flutter(folder: Path, project: Project, cfg: PublishConfig, work: Path, interpreter: str, log) -> BuildResult:
    from ..languages.flutter import flutter_exe
    fl = interpreter or flutter_exe()
    if not fl:
        raise BuildError("The Flutter SDK was not found (flutter.bat)")
    if not (folder / "windows").is_dir():      # designer / mobile projects have no Windows runner yet
        log("No windows/ folder: adding the Windows desktop runner (flutter create --platforms=windows .)")
        if run([fl, "create", "--platforms=windows", "."], folder, log, shell=fl.lower().endswith(".bat")) != 0:
            raise BuildError("flutter create --platforms=windows failed")
    if run([fl, "build", "windows", "--release"], folder, log, shell=fl.lower().endswith(".bat")) != 0:
        raise BuildError("flutter build windows failed")
    rel = next((p for p in (folder / "build" / "windows").glob("*/runner/Release") if p.is_dir()), None) \
        or folder / "build" / "windows" / "runner" / "Release"
    exes = list(rel.glob("*.exe")) if rel.is_dir() else []
    if not exes:
        raise BuildError(f"No exe in {rel}")
    out = work / "dist" / cfg.exe_base()
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(rel, out)
    return BuildResult(out, exes[0].name, "flutter")


def build_cargo(folder: Path, project: Project, cfg: PublishConfig, work: Path, interpreter: str, log) -> BuildResult:
    """A plain Rust (Cargo) project: ``cargo build --release`` and the binary of the startup target ("bin: name",
    else the package name) copied under the app name. No Python inside."""
    import re as _re
    from ..languages import get_plugin
    cargo = get_plugin("rust-cargo").tool() or shutil.which("cargo")
    if not cargo:
        raise BuildError("cargo was not found - install Rust from https://rustup.rs")
    if run([cargo, "build", "--release"], folder, log) != 0:
        raise BuildError("cargo build --release failed")
    m = _re.match(r"\s*bin:\s*(\S+)", project.startup or "")
    names = [m.group(1)] if m else []
    toml = Path(folder) / "Cargo.toml"
    pm = _re.search(r'(?ms)^\[package\].*?^name\s*=\s*"([^"]+)"', toml.read_text(encoding="utf-8")) \
        if toml.is_file() else None
    if pm:
        names.append(pm.group(1))
    release = Path(folder) / "target" / "release"
    exe = next((release / f"{n}.exe" for n in names if (release / f"{n}.exe").is_file()), None) or \
        next(iter(sorted(release.glob("*.exe"))), None)
    if exe is None:
        raise BuildError(f"cargo built no .exe in {release}")
    out = work / "dist" / cfg.exe_base()
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    target = out / (cfg.exe_base() + ".exe")
    shutil.copy2(exe, target)
    log(f"Rust program: {target.name} ({target.stat().st_size:,} bytes) from {exe.name}")
    return BuildResult(out, target.name, "cargo")


def build_folder(folder: Path, project: Project, cfg: PublishConfig, work: Path, interpreter: str, log) -> BuildResult:
    src = resolve(folder, cfg.prebuilt_dir)
    if not src or not src.is_dir():
        raise BuildError("Choose the folder of the already built program (Build tab)")
    exe = cfg.prebuilt_exe or next((p.name for p in src.glob("*.exe")), "")
    if not exe or not (src / exe).is_file():
        raise BuildError("Choose the program's main .exe")
    return BuildResult(src, exe, "folder")


def build_asm(folder: Path, project: Project, cfg: PublishConfig, work: Path, interpreter: str, log) -> BuildResult:
    """Assembly (NASM / FASM / MASM / GNU as): a console program is the exe the assembler + linker made (no Python
    inside); a project with forms is a GUI Bridge program (bridge host + the assembled exe)."""
    if project.forms:
        return build_bridge(folder, project, cfg, work, interpreter, log)
    from ..languages import get_plugin
    plugin = get_plugin(startup_language(project))
    if not plugin.tool():
        raise BuildError(f"{plugin.display_name}: the assembler was not found. {plugin.install_hint}")
    env = dict(os.environ, PYTHONPATH=str(IDE_ROOT))
    if run(plugin.build_command(folder, project), folder, log, env=env, shell=True) != 0:
        raise BuildError(f"The {plugin.display_name} build failed")
    if plugin.settings(project).get("output") == "dll":
        raise BuildError("A class library (DLL) is not a program: reference it from an app project instead")
    built = Path(folder) / "_radapp.exe"
    if not built.is_file():
        raise BuildError("The build did not create _radapp.exe")
    out = work / "dist" / cfg.exe_base()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    exe = out / (cfg.exe_base() + ".exe")
    shutil.copy2(built, exe)
    from ..asm import toolchain as tc
    gcc = tc.mingw("gcc")
    copy_runtime_dlls(exe, [Path(gcc).parent] if gcc else [], out, log)
    for item in data_entries(folder, cfg, skip_ext=SKIP_FILES_PY | {".asm", ".s", ".inc", ".nasm", ".fasm", ".obj",
                                                                    ".o", ".lst", ".exe", ".gitignore"}):
        if item.name.startswith("_build"):
            continue
        (copy_tree(item, out / item.name) if item.is_dir() else shutil.copy2(item, out / item.name))
    return BuildResult(out, exe.name, "asm", ["Console program: run it from a command prompt."])


def build_native(folder: Path, project: Project, cfg: PublishConfig, work: Path, interpreter: str, log) -> BuildResult:
    """A small native exe (radide/deploy/native); falls back to vbrun / bridge with the reasons logged."""
    from .native import NativeUnsupported, builder_for
    lang = startup_language(project)
    mod = builder_for(lang)
    reasons = ["no native builder for " + lang] if mod is None else list(mod.check(folder, project, cfg))
    if not reasons:
        try:
            log(f"Native build: {getattr(mod, 'NAME', mod.__name__)}")
            return mod.build(folder, project, cfg, work, log)
        except NativeUnsupported as e:
            reasons = e.reasons
    kind = fallback_kind(lang)
    log("Native build not possible, using " + KIND_NAMES.get(kind, kind) + ":")
    for r in reasons:
        log("  - " + r)
    return BUILDERS[kind](folder, project, cfg, work, interpreter, log)


BUILDERS = {"native": build_native, "pyinstaller": build_python, "vbrun": build_vbrun, "bridge": build_bridge, "ring2exe": build_ring,
            "flutter": build_flutter, "folder": build_folder, "asm": build_asm, "cargo": build_cargo}


def build(folder: Path, cfg: PublishConfig, log=print, interpreter: str = "") -> BuildResult:
    folder = Path(folder).resolve()
    project = Project.load(folder)
    kind = detect_kind(project, cfg)
    if kind not in BUILDERS:
        raise BuildError(f"Unknown build kind: {kind}")
    work = out_root(folder, cfg) / "build"
    work.mkdir(parents=True, exist_ok=True)
    log(f"------ Build ({KIND_NAMES.get(kind, kind)}): {project.name}")
    res = BUILDERS[kind](folder, project, cfg, work, interpreter, log)
    for item in cfg.extra_files:
        p = resolve(folder, item)
        if p and p.is_dir():
            shutil.copytree(p, res.dist / p.name, dirs_exist_ok=True)
        elif p and p.is_file():
            shutil.copy2(p, res.dist / p.name)
        else:
            log(f"Extra file not found: {item}")
    return res


def is_64bit(exe: Path) -> bool:
    try:
        with open(exe, "rb") as f:
            data = f.read(4096)
        off = int.from_bytes(data[0x3C:0x40], "little")
        machine = int.from_bytes(data[off + 4:off + 6], "little")
        return machine in (0x8664, 0xAA64)
    except (OSError, ValueError):
        return sys.maxsize > 2 ** 32


__all__ = ["BUILDERS", "BuildError", "BuildResult", "KIND_NAMES", "build", "copy_runtime_dlls", "data_entries",
           "detect_kind", "is_64bit", "make_icon", "out_root", "startup_language", "version_file"]
