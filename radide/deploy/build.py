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

IDE_ROOT = Path(__file__).resolve().parents[2]

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
    if lang.startswith("python") or lang in ("pygame", "kivy", "python-arcade"):
        return "pyinstaller"
    if lang == "vb-basic":
        return "vbrun"
    if lang.startswith("ring"):
        return "ring2exe"
    if lang == "flutter":
        return "flutter"
    if lang.endswith("-bridge") or lang in ("javascript", "typescript", "php"):
        return "bridge"
    return "folder"


KIND_NAMES = {
    "auto": "Automatic (from the project's language)",
    "pyinstaller": "Python program (PyInstaller)",
    "vbrun": "VB6 program (bundled VB runtime)",
    "bridge": "GUI Bridge program (language build + bridge host)",
    "ring2exe": "Ring program (ring2exe)",
    "flutter": "Flutter Windows app (flutter build windows)",
    "folder": "Already built program folder",
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
    for c in collect:
        args += ["--collect-all", c]
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
    for f in project.forms:
        try:
            fp = get_plugin(project.form_languages.get(f, project.language))
            hidden += [Path(fp.code_file(f)).stem, Path(fp.designer_file(f)).stem]
        except (KeyError, AttributeError):
            pass
    datas = [(p, p.name if p.is_dir() else ".") for p in data_entries(folder, cfg)]
    collect = []
    if lang == "kivy":
        collect.append("kivy")
    out = pyinstaller(python, script, folder, cfg, work, log, paths=[folder, *upaths], datas=datas,
                      hidden=sorted(set(hidden) | set(uhidden)), excludes=PY_EXCLUDES, hooks=uhooks,
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
              "radide.languages._refs", *uhidden]
    return pyinstaller(py, script, folder, cfg, work, log, paths=[IDE_ROOT, *upaths], hidden=hidden,
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
    try:
        if run([str(ring2exe), named.name, "-dist", "-allruntime", "-gui", "-qt"], folder, log) != 0:
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


def build_folder(folder: Path, project: Project, cfg: PublishConfig, work: Path, interpreter: str, log) -> BuildResult:
    src = resolve(folder, cfg.prebuilt_dir)
    if not src or not src.is_dir():
        raise BuildError("Choose the folder of the already built program (Build tab)")
    exe = cfg.prebuilt_exe or next((p.name for p in src.glob("*.exe")), "")
    if not exe or not (src / exe).is_file():
        raise BuildError("Choose the program's main .exe")
    return BuildResult(src, exe, "folder")


BUILDERS = {"pyinstaller": build_python, "vbrun": build_vbrun, "bridge": build_bridge, "ring2exe": build_ring,
            "flutter": build_flutter, "folder": build_folder}


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
