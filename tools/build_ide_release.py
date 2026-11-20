"""Build a Windows release of RAD IDE itself (not of a user program).

    python tools/build_ide_release.py [--version X.Y.Z] [--out dist/release] [--no-installer] [--no-zip]
                                      [--work build/release] [--reuse] [--iscc PATH]

Output (in --out):
    RADIDE-X.Y.Z-setup-win64.exe      Inno Setup installer (per user by default, "all users" optional)
    RADIDE-X.Y.Z-portable-win64.zip   the --onedir build + portable.flag (settings in .\\settings, no registry)
    SHA256SUMS.txt
and the plain onedir in <work>/dist/RADIDE.

How it is put together
  * PyInstaller --onedir --windowed (RADIDE.exe, icon radide/assets/radide.ico) from tools/radide_frozen_main.py.
    Every module of the radide package is a hidden import, and afterwards the WHOLE radide tree (data files
    found by scanning - web/monaco, tutorials, i18n, runtimes, templates, ... - and the .py sources) is copied
    to _internal/radide, so ``Path(__file__).parent`` lookups work unchanged and the helper scripts that the
    IDE runs with a real Python (runtimes, language bridges) exist on disk. docs/ goes to _internal/docs.
  * Packages only user programs need (pygame, kivy, ursina/panda3d, PySide6, numpy, tkinter, pylsp,
    debugpy, ipykernel, black/ruff, PyInstaller...) are excluded: the frozen IDE runs user projects, language
    servers, debug adapters and kernels with a real Python found at start-up (radide/paths.py).
  * Inno Setup: ISCC from radide/deploy/tools.py (portable copy in %LOCALAPPDATA%\\RADIDE\\tools, a normal
    installation, PATH; downloaded when missing) or --iscc.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PKG = REPO / "radide"
NAME = "RADIDE"
APP = "RAD IDE"
PUBLISHER = "Musoftware"
URL = "https://musoftwares.com"
GITHUB = "https://github.com/musoftware/PythonIDE"
APP_ID = "{{6C2E8F4A-3B71-4D0E-9A5C-7F1D2E8B4A90}"      # fixed: upgrades replace the previous version
ICON = PKG / "assets" / "radide.ico"
ENTRY = REPO / "tools" / "radide_frozen_main.py"
TOP_FILES = ["LICENSE", "THIRD_PARTY_NOTICES.md", "README.md", "CHANGELOG.md"]

# never bundled into the frozen IDE (user programs get them from the real Python)
EXCLUDES = ["tkinter", "_tkinter", "turtle", "turtledemo", "idlelib", "kivy", "kivy_deps", "kivy_garden",
            "ursina", "panda3d", "direct", "simplepbr", "gltf", "pygame", "pymunk", "arcade", "pyglet",
            "PySide6", "shiboken6", "PyQt5", "PySide2", "numpy", "pandas", "matplotlib", "scipy", "cv2",
            "IPython", "ipykernel", "ipywidgets", "notebook", "jupyterlab", "pylsp", "pylsp_rope", "rope",
            "debugpy", "black", "ruff", "pytest", "_pytest", "PyInstaller", "pyftpdlib", "pypdf", "torch",
            "tensorflow", "sympy", "decompyle3", "uncompyle6", "lib2to3", "test", "unittest.test"]
# third-party packages whose data files / plugin modules the IDE needs at run time (when installed)
COLLECT_DATA = ["jedi", "parso", "barcode", "nbformat", "jsonschema_specifications", "pygments", "qrcode"]
COLLECT_SUBMODULES = ["pygments", "markdown", "keyring.backends", "jupyter_client", "zmq", "pycrdt",
                      "paramiko", "openpyxl", "PIL"]
COLLECT_ALL = ["capstone"]
# radide sub-folders that are data / scripts for other processes, not IDE modules
NOT_MODULES = {"runtime", "runtimes", "clients", "tutorials", "web", "templates", "tests", "help", "assets"}
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", "node_modules", ".git", ".venv", "venv",
             "bin", "obj", "dist", "build", ".radide_backup"}
SKIP_EXT = {".pyc", ".pyo"}


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def ide_version() -> str:
    m = re.search(r'__version__\s*=\s*"([^"]+)"', (PKG / "__init__.py").read_text(encoding="utf-8"))
    return m.group(1) if m else "0.0.0"


def numeric(version: str) -> tuple[int, int, int, int]:
    nums = [int(x) for x in re.findall(r"\d+", version)[:4]]
    return tuple((nums + [0, 0, 0, 0])[:4])  # type: ignore[return-value]


# ----------------------------------------------------------------------------------- PyInstaller
def radide_modules() -> list[str]:
    """Every importable module of the radide package (directories with __init__.py)."""
    mods = []
    for py in sorted(PKG.rglob("*.py")):
        rel = py.relative_to(REPO)
        parts = rel.parts[:-1]
        if any(p in SKIP_DIRS or p in NOT_MODULES for p in parts):
            continue
        if not all((REPO.joinpath(*parts[:i + 1]) / "__init__.py").is_file() for i in range(len(parts))):
            continue
        name = ".".join(parts + ((py.stem,) if py.stem != "__init__" else ()))
        if re.fullmatch(r"[A-Za-z_][\w.]*", name) and not name.endswith("__main__"):
            mods.append(name)
    return mods


def installed(dist: str, python: str) -> bool:
    r = subprocess.run([python, "-c", f"import importlib.util,sys; sys.exit(0 if importlib.util.find_spec({dist!r}) else 1)"],
                       capture_output=True)
    return r.returncode == 0


def version_file(path: Path, version: str) -> Path:
    v = numeric(version)
    path.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={v}, prodvers={v}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
                    date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{PUBLISHER}'),
      StringStruct('FileDescription', '{APP}'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', '{NAME}'),
      StringStruct('LegalCopyright', '(c) 2026 {PUBLISHER} ({URL}) - MIT License'),
      StringStruct('OriginalFilename', '{NAME}.exe'),
      StringStruct('ProductName', '{APP}'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""", encoding="utf-8")
    return path


def ensure_icon() -> Path:
    if ICON.is_file():
        return ICON
    sys.path.insert(0, str(REPO))
    from radide.shell_integration import ensure_icons       # draws the icons with Pillow
    ensure_icons()
    return ICON


def pyinstaller(work: Path, version: str, python: str) -> Path:
    dist, build = work / "dist", work / "build"
    args = [python, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed", "--name", NAME,
            "--icon", str(ensure_icon()), "--distpath", str(dist), "--workpath", str(build),
            "--specpath", str(work), "--paths", str(REPO), "--contents-directory", "_internal",
            "--version-file", str(version_file(work / "version_info.txt", version)), "--log-level", "WARN"]
    for m in EXCLUDES:
        args += ["--exclude-module", m]
    for m in radide_modules():
        args += ["--hidden-import", m]
    args += ["--hidden-import", "PyQt6.QtWebEngineWidgets", "--hidden-import", "PyQt6.QtWebEngineCore",
             "--hidden-import", "PyQt6.QtWebChannel", "--hidden-import", "PyQt6.Qsci",
             "--hidden-import", "PyQt6.QtNetwork", "--hidden-import", "PyQt6.QtSvg",
             "--hidden-import", "PyQt6.QtPrintSupport"]
    for pkg in COLLECT_DATA:
        if installed(pkg, python):
            args += ["--collect-data", pkg]
    for pkg in COLLECT_SUBMODULES:
        if installed(pkg.split(".")[0], python):
            args += ["--collect-submodules", pkg]
    for pkg in COLLECT_ALL:
        if installed(pkg, python):
            args += ["--collect-all", pkg]
    args.append(str(ENTRY))
    log(f"PyInstaller ({len(args)} arguments) ...")
    t = time.time()
    r = subprocess.run(args, cwd=str(work))
    if r.returncode != 0:
        raise SystemExit(f"PyInstaller failed ({r.returncode})")
    log(f"PyInstaller done in {time.time() - t:.0f} s")
    return dist / NAME


def _copytree(src: Path, dst: Path, skip_dirs=SKIP_DIRS) -> int:
    n = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        out = dst / Path(root).relative_to(src)
        out.mkdir(parents=True, exist_ok=True)
        for f in files:
            if Path(f).suffix.lower() in SKIP_EXT:
                continue
            shutil.copy2(Path(root) / f, out / f)
            n += 1
    return n


def add_resources(onedir: Path, version: str) -> None:
    internal = onedir / "_internal"
    # radide: every file (data found by scanning + .py sources for helper processes); package dirs that
    # are only data/test material of the repo itself are skipped
    n = _copytree(PKG, internal / "radide", SKIP_DIRS | {"tests"})
    log(f"radide tree: {n} files -> _internal/radide")
    if (REPO / "docs").is_dir():
        n = _copytree(REPO / "docs", internal / "docs")
        log(f"docs: {n} files -> _internal/docs")
    for f in TOP_FILES:
        if (REPO / f).is_file():
            shutil.copy2(REPO / f, onedir / f)
            shutil.copy2(REPO / f, internal / f)
    samples = onedir / "samples"
    for s in sorted((REPO / "samples").glob("Hello*")):
        if s.is_dir():
            _copytree(s, samples / s.name)
    log(f"samples: {', '.join(p.name for p in sorted(samples.iterdir())) if samples.is_dir() else '-'}")
    (onedir / "VERSION.txt").write_text(version + "\n", encoding="utf-8")


def prune_qt(onedir: Path) -> None:
    """Drop what the IDE never loads: QtWebEngine's debug resources, the QML tree (no QML in the IDE) and
    the Qt DLLs that no PyQt6 module, Qt plugin or QtWebEngineProcess imports (PE import tables, pefile)."""
    qt = onedir / "_internal" / "PyQt6" / "Qt6"
    if not qt.is_dir():
        return
    freed = 0
    for p in list(qt.rglob("*.debug.pak")) + list(qt.rglob("*.debug.bin")):
        freed += p.stat().st_size
        p.unlink()
    if (qt / "qml").is_dir():
        freed += sum(p.stat().st_size for p in (qt / "qml").rglob("*") if p.is_file())
        shutil.rmtree(qt / "qml")
    try:
        import pefile
    except ImportError:
        log(f"Qt pruned: {freed / 1048576:.0f} MB (pefile missing: DLLs kept)")
        return
    bin_dir = qt / "bin"
    dlls = {p.name.lower(): p for p in bin_dir.glob("*.dll")}

    def imports(p: Path) -> set[str]:
        try:
            pe = pefile.PE(str(p), fast_load=True)
            pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                                                   pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"]])
            names = {e.dll.decode(errors="replace").lower() for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])}
            names |= {e.dll.decode(errors="replace").lower() for e in getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", [])}
            pe.close()
            return names
        except Exception:  # noqa: BLE001
            return set(dlls)              # unreadable: keep everything it might need
    roots = list((onedir / "_internal" / "PyQt6").glob("*.pyd")) + list((qt / "plugins").rglob("*.dll")) \
        + list(qt.rglob("*.exe"))
    keep: set[str] = set()
    todo = [r for r in roots]
    while todo:
        for name in imports(todo.pop()):
            if name in dlls and name not in keep:
                keep.add(name)
                todo.append(dlls[name])
    for name, p in dlls.items():
        if name.startswith("qt6") and name not in keep:
            freed += p.stat().st_size
            p.unlink()
    log(f"Qt pruned: {freed / 1048576:.0f} MB")


def check_onedir(onedir: Path) -> list[str]:
    """Things a working build must contain."""
    need = [onedir / f"{NAME}.exe", onedir / "_internal" / "radide" / "web" / "monaco",
            onedir / "_internal" / "radide" / "i18n" / "ar.json", onedir / "_internal" / "radide" / "assets" / "radide.ico"]
    missing = [str(p.relative_to(onedir)) for p in need if not p.exists()]
    we = list((onedir / "_internal").rglob("QtWebEngineProcess.exe"))
    if not we:
        missing.append("QtWebEngineProcess.exe")
    if not list((onedir / "_internal").rglob("qtwebengine_resources.pak")):
        missing.append("qtwebengine_resources.pak")
    return missing


# ----------------------------------------------------------------------------------- portable zip
def portable_zip(onedir: Path, out: Path, version: str) -> Path:
    z = out / f"{NAME}-{version}-portable-win64.zip"
    if z.exists():
        z.unlink()
    log(f"zip -> {z.name} ...")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, _dirs, files in os.walk(onedir):
            for f in files:
                p = Path(root) / f
                zf.write(p, f"{NAME}/{p.relative_to(onedir).as_posix()}")
        zf.writestr(f"{NAME}/portable.flag",
                    "RAD IDE portable mode: settings are kept in the 'settings' folder next to RADIDE.exe\r\n"
                    "(not in the registry) and nothing is registered with Windows automatically.\r\n"
                    "Delete this file to use the normal per-user settings.\r\n")
    return z


# ----------------------------------------------------------------------------------- Inno Setup
def find_iscc(given: str = "") -> str:
    if given:
        return given
    sys.path.insert(0, str(REPO))
    from radide.deploy import tools
    iscc = tools.find_iscc()
    for root in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", "")):
        for ver in ("7", "6"):
            p = Path(root) / f"Inno Setup {ver}" / "ISCC.exe"
            if not iscc and root and p.is_file():
                iscc = str(p)
    return iscc or tools.install_innosetup(log)


def _iss(s: str) -> str:
    return s.replace('"', '""')


def iss_text(onedir: Path, out: Path, version: str, iscc: str) -> str:
    langs = [("english", "compiler:Default.isl")]
    if (Path(iscc).parent / "Languages" / "Arabic.isl").is_file():
        langs.append(("arabic", "compiler:Languages\\Arabic.isl"))
    v4 = ".".join(map(str, numeric(version)))
    L = ["; RAD IDE installer - generated by tools/build_ide_release.py", "[Setup]",
         f"AppId={APP_ID}", f"AppName={APP}", f"AppVersion={version}", f"AppVerName={APP} {version}",
         f"AppPublisher={PUBLISHER}", f"AppPublisherURL={URL}", f"AppSupportURL={GITHUB}/issues",
         f"AppUpdatesURL={GITHUB}/releases", f"AppCopyright=(c) 2026 {PUBLISHER}",
         f"DefaultDirName={{autopf}}\\{NAME}", f"DefaultGroupName={APP}", "DisableProgramGroupPage=yes",
         "PrivilegesRequired=lowest", "PrivilegesRequiredOverridesAllowed=dialog commandline",
         f"LicenseFile={REPO / 'LICENSE'}", f"OutputDir={out}", f"OutputBaseFilename={NAME}-{version}-setup-win64",
         f"SetupIconFile={ICON}", f"UninstallDisplayIcon={{app}}\\{NAME}.exe", f"UninstallDisplayName={APP} {version}",
         "Compression=lzma2/max", "SolidCompression=yes", "LZMANumBlockThreads=4",
         "ArchitecturesAllowed=x64compatible", "ArchitecturesInstallIn64BitMode=x64compatible",
         "WizardStyle=modern", "ShowLanguageDialog=auto", "CloseApplications=yes", "UsedUserAreasWarning=no",
         f"VersionInfoVersion={v4}", f"VersionInfoProductVersion={v4}", f"VersionInfoCompany={PUBLISHER}",
         f"VersionInfoDescription={APP} Setup", f"VersionInfoProductName={APP}",
         f"VersionInfoCopyright=(c) 2026 {PUBLISHER}", "",
         "[Languages]"]
    L += [f'Name: "{n}"; MessagesFile: "{f}"' for n, f in langs]
    L += ["", "[CustomMessages]",
          "english.Integration=Windows integration:",
          "english.AssocTask=Associate RAD IDE files (.radsln, .radproj, .radext, .form ...)",
          'english.ExplorerTask=Add "Open with RAD IDE" to Explorer (files and folders)',
          "english.Registering=Registering RAD IDE with Windows...",
          "english.Launch=Launch RAD IDE"]
    if len(langs) > 1:
        L += ["arabic.Integration=التكامل مع ويندوز:",
              "arabic.AssocTask=ربط ملفات RAD IDE (.radsln و .radproj و .radext و .form ...)",
              'arabic.ExplorerTask=إضافة "Open with RAD IDE" إلى مستكشف الملفات (الملفات والمجلدات)',
              "arabic.Registering=جارٍ تسجيل RAD IDE في ويندوز...",
              "arabic.Launch=تشغيل RAD IDE"]
    L += ["", "[Tasks]",
          'Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; '
          "Flags: unchecked",
          'Name: "assoc"; Description: "{cm:AssocTask}"; GroupDescription: "{cm:Integration}"',
          'Name: "explorer"; Description: "{cm:ExplorerTask}"; GroupDescription: "{cm:Integration}"',
          "", "[Files]",
          f'Source: "{onedir}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs',
          "", "[Icons]",
          f'Name: "{{group}}\\{APP}"; Filename: "{{app}}\\{NAME}.exe"; WorkingDir: "{{app}}"',
          f'Name: "{{group}}\\{{cm:UninstallProgram,{APP}}}"; Filename: "{{uninstallexe}}"',
          f'Name: "{{autodesktop}}\\{APP}"; Filename: "{{app}}\\{NAME}.exe"; WorkingDir: "{{app}}"; Tasks: desktopicon',
          ""]
    # [Run] --register per chosen task / [UninstallRun] --unregister: one source of truth for the keys
    sys.path.insert(0, str(REPO))
    from radide.shell_integration import inno_lines
    shell = inno_lines(f"{NAME}.exe", tasks={"assoc and not explorer": "file_assoc",
                                             "explorer and not assoc": "open_with,context_menu",
                                             "assoc and explorer": "file_assoc,open_with,context_menu"},
                       status_msg="{cm:Registering}", if_owner=True)
    cut = shell.index("[UninstallRun]")
    L += shell[:cut - 1]
    L += [f'Filename: "{{app}}\\{NAME}.exe"; Description: "{{cm:Launch}}"; Flags: nowait postinstall skipifsilent',
          "", *shell[cut:],
          "", "[UninstallDelete]",
          '; __pycache__ folders written by the helper scripts that a real Python runs from _internal\\radide',
          'Type: filesandordirs; Name: "{app}\\_internal"', ""]
    return "\r\n".join(L)


def build_setup(onedir: Path, out: Path, work: Path, version: str, iscc_given: str = "") -> Path:
    iscc = find_iscc(iscc_given)
    if not iscc or not Path(iscc).is_file():
        raise SystemExit("Inno Setup (ISCC.exe) not found - install it or pass --iscc")
    iss = work / f"{NAME}.iss"
    iss.write_text(iss_text(onedir.resolve(), out.resolve(), version, iscc), encoding="utf-8-sig")
    log(f"ISCC {iscc} ...")
    t = time.time()
    r = subprocess.run([iscc, "/Q", str(iss)])
    if r.returncode != 0:
        raise SystemExit(f"ISCC failed ({r.returncode}); script: {iss}")
    log(f"setup done in {time.time() - t:.0f} s")
    return out / f"{NAME}-{version}-setup-win64.exe"


# ----------------------------------------------------------------------------------- main
def sha256sums(files: list[Path], out: Path) -> Path:
    lines = []
    for f in files:
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        lines.append(f"{h.hexdigest()}  {f.name}")
    p = out / "SHA256SUMS.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the RAD IDE Windows release (setup + portable zip).")
    ap.add_argument("--version", default=ide_version(), help="X.Y.Z (default: radide.__version__)")
    ap.add_argument("--out", default=str(REPO / "dist" / "release"))
    ap.add_argument("--work", default="", help="PyInstaller work folder (default: <out>/../build-ide)")
    ap.add_argument("--python", default=sys.executable, help="Python with the IDE's requirements + PyInstaller")
    ap.add_argument("--no-installer", action="store_true")
    ap.add_argument("--no-zip", action="store_true")
    ap.add_argument("--reuse", action="store_true", help="skip PyInstaller, reuse <work>/dist/RADIDE")
    ap.add_argument("--iscc", default="")
    a = ap.parse_args(argv)
    version = a.version.lstrip("vV")
    if not re.fullmatch(r"\d+\.\d+\.\d+([.-][0-9A-Za-z.-]+)?", version):
        ap.error(f"bad version {a.version!r} (expected X.Y.Z)")
    out = Path(a.out).resolve()
    work = Path(a.work).resolve() if a.work else out.parent / "build-ide"
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    log(f"RAD IDE {version}: out={out} work={work}")
    onedir = work / "dist" / NAME
    if not (a.reuse and (onedir / f"{NAME}.exe").is_file()):
        onedir = pyinstaller(work, version, a.python)
    add_resources(onedir, version)
    prune_qt(onedir)
    missing = check_onedir(onedir)
    if missing:
        raise SystemExit(f"the build is incomplete, missing: {', '.join(missing)}")
    artifacts = []
    if not a.no_zip:
        artifacts.append(portable_zip(onedir, out, version))
    if not a.no_installer:
        artifacts.append(build_setup(onedir, out, work, version, a.iscc))
    if artifacts:
        sums = sha256sums(artifacts, out)
        artifacts.append(sums)
    size = sum(p.stat().st_size for p in onedir.rglob("*") if p.is_file())
    log(f"onedir {onedir} ({size / 1048576:.1f} MB)")
    for p in artifacts:
        log(f"{p} ({p.stat().st_size / 1048576:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
