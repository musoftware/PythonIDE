"""Windows shell integration for RAD IDE - per user (HKCU), no administrator rights.

    register(options)   file associations, "Open with", Explorer context menus, Start Menu / Desktop
                        shortcuts and an entry in Settings > Apps (Uninstall)
    unregister()        removes exactly what register() created and restores every value it replaced
    status()            what is registered (and for which launcher)

Every key/value written is recorded in a manifest (HKCU\\Software\\RADIDE\\ShellIntegration, value
"Manifest", JSON): unregister() deletes only values that still hold what RAD IDE wrote, restores the
previous data of values it replaced, and removes only the keys it created (when empty).

Default handler only for the IDE's own types (.radsln, .radproj, .radext; .form / .scene / .scene3d
only when no other program owns them). Source files only get an entry in <ext>\\OpenWithProgids,
so the "Open with" menu lists RAD IDE without taking over any existing default.

Tests: set RADIDE_SHELL_ROOT (e.g. "Software\\RADIDE-TEST-Shell\\Classes") and RADIDE_SHELL_SHORTCUTS
(a scratch folder): every key then goes under the parent of that root and the shortcuts into that
folder - the real HKCU\\Software\\Classes is never touched.

The launcher is <repo>\\.venv\\Scripts\\pythonw.exe "<repo>\\radide\\launch.pyw" "%1" (no console
window), or the frozen RAD IDE exe of an installer build. An installer calls
``RADIDE.exe --register --quiet --no-uninstall-entry`` after installing and ``--unregister --quiet``
before uninstalling (see ``inno_lines``) - one source of truth for the keys.

No Qt imports here (also runs from the Uninstall entry without starting the IDE)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

APP = "RAD IDE"
PROG = "RADIDE"
PUBLISHER = "Musoftware"
URL = "https://musoftwares.com"
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ASSETS = HERE / "assets"
ICON = ASSETS / "radide.ico"
LAUNCH_SCRIPT = HERE / "launch.pyw"

REAL_CLASSES = "Software\\Classes"
ENV_ROOT = "RADIDE_SHELL_ROOT"
ENV_SHORTCUTS = "RADIDE_SHELL_SHORTCUTS"

OPTIONS = ("file_assoc", "open_with", "context_menu", "start_menu", "desktop")
DEFAULT_OPTIONS = {"file_assoc": True, "open_with": True, "context_menu": True, "start_menu": True,
                   "desktop": False, "uninstall_entry": True}
OPTION_LABELS = {
    "file_assoc": "File associations for RAD IDE files (.radsln, .radproj, .form ...)",
    "open_with": "\"Open with\" RAD IDE for source and text files",
    "context_menu": "Explorer context menus (Open with RAD IDE, Open folder in RAD IDE)",
    "start_menu": "Start Menu shortcut",
    "desktop": "Desktop shortcut",
}

# the IDE's own file types: (extension, ProgID suffix, description, icon file, take the default even
# when another program already owns the extension (the previous value is restored on unregister))
OWN_TYPES = [
    (".radsln", "Solution", "RAD IDE Solution", "solution.ico", True),
    (".radproj", "Project", "RAD IDE Project", "project.ico", True),
    (".radext", "Extension", "RAD IDE Extension Package", "extension.ico", True),
    (".form", "Form", "RAD IDE Form", "form.ico", False),
    (".scene", "Scene", "RAD IDE Game Scene", "scene.ico", False),
    (".scene3d", "Scene3D", "RAD IDE 3D Scene", "scene.ico", False),
]
SOURCE_PROGID = PROG + ".SourceFile"

# "Open with" only (never the default); the language plugins' extensions are added (open_with_extensions)
OPEN_WITH_BASE = (
    ".py .pyw .pyi .ipynb .txt .text .md .markdown .rst .log .csv .tsv .json .jsonc .xml .xaml .yaml .yml "
    ".toml .ini .cfg .conf .properties .env .editorconfig .gitignore .html .htm .xhtml .css .scss .sass .less "
    ".js .mjs .cjs .ts .tsx .jsx .vue .svelte .php .phtml .blade .twig .sql .sh .bash .bat .cmd .ps1 .psm1 "
    ".c .h .cpp .hpp .cc .cxx .hxx .cs .vb .fs .fsx .java .kt .kts .groovy .gradle .scala .go .rs .rb .lua "
    ".pl .pm .r .dart .swift .m .gd .ring .rh .f90 .f .for .pas .pp .inc .dpr .dpk .lpr .lpi .dfm .lfm .asm "
    ".vbp .vbg .frm .bas .cls .ctl .dsr .sln .slnx .csproj .vbproj .fsproj .vcxproj .props .targets .dproj "
    ".groupproj .pro .pri .ui .qml .code-workspace .cmake .mk .makefile .dockerfile .svg .rpt .resx .manifest"
).split()


# ----------------------------------------------------------------------------------- target
class Target:
    """Where register() writes. The default is the real per-user location; ``Target.from_env()``
    honours RADIDE_SHELL_ROOT / RADIDE_SHELL_SHORTCUTS (tests)."""

    def __init__(self, classes: str = REAL_CLASSES, base: str | None = None,
                 shortcuts: str | Path | None = "", notify: bool | None = None):
        self.classes = classes.strip("\\")
        self.test = self.classes.lower() != REAL_CLASSES.lower()
        if base is None:
            base = self.classes.rsplit("\\", 1)[0] if self.test else "Software"
        self.base = base.strip("\\")
        if self.test:
            self.manifest_key = f"{self.base}\\RADIDE\\ShellIntegration"
            self.uninstall_key = f"{self.base}\\Uninstall\\RADIDE"
            self.capabilities_key = f"{self.base}\\RADIDE\\Capabilities"
            self.registered_apps_key = f"{self.base}\\RegisteredApplications"
        else:
            self.manifest_key = "Software\\RADIDE\\ShellIntegration"
            self.uninstall_key = "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\RADIDE"
            self.capabilities_key = "Software\\RADIDE\\Capabilities"
            self.registered_apps_key = "Software\\RegisteredApplications"
        if shortcuts == "":            # default: the real folders (a test target without a folder: none)
            self.start_menu = None if self.test else _start_menu_dir()
            self.desktop = None if self.test else _desktop_dir()
        elif shortcuts is None:
            self.start_menu = self.desktop = None
        else:
            self.start_menu = Path(shortcuts) / "StartMenu"
            self.desktop = Path(shortcuts) / "Desktop"
        self.notify = (not self.test) if notify is None else notify

    @classmethod
    def from_env(cls) -> "Target":
        root = os.environ.get(ENV_ROOT, "").strip()
        if not root or root.strip("\\").lower() == REAL_CLASSES.lower():
            return cls()
        sc = os.environ.get(ENV_SHORTCUTS, "").strip()
        return cls(root, shortcuts=sc or None)

    def cls(self, sub: str) -> str:
        return f"{self.classes}\\{sub}"

    def __repr__(self):
        return f"Target(classes={self.classes!r}, test={self.test})"


def _known_folder(csidl: int) -> Path | None:
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf) == 0 and buf.value:
            return Path(buf.value)
    except Exception:  # noqa: BLE001
        pass
    return None


def _start_menu_dir() -> Path:
    return _known_folder(0x0002) or Path(os.environ.get("APPDATA", str(Path.home()))) / \
        "Microsoft" / "Windows" / "Start Menu" / "Programs"


def _desktop_dir() -> Path:
    return _known_folder(0x0010) or Path.home() / "Desktop"


# ----------------------------------------------------------------------------------- launcher / icons
def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def launcher() -> tuple[str, list[str]]:
    """(program, leading arguments) that start RAD IDE without a console window."""
    if frozen():          # RADIDE.exe (radide/paths.py makes sys.executable a real Python for the IDE's children)
        return getattr(sys, "_radide_exe", None) or sys.executable, []
    for cand in (REPO / ".venv" / "Scripts" / "pythonw.exe", Path(sys.executable).with_name("pythonw.exe")):
        if cand.is_file():
            return str(cand), [str(LAUNCH_SCRIPT)]
    return sys.executable, [str(LAUNCH_SCRIPT)]


def _q(s: str) -> str:
    return f'"{s}"'


def command(*args: str) -> str:
    exe, lead = launcher()
    return " ".join([_q(exe), *(_q(a) for a in lead), *args])


def open_command(arg: str = "%1") -> str:
    return command(_q(arg))


def icon_path(name: str = "radide.ico") -> str:
    ensure_icons()
    p = ASSETS / name
    return str(p if p.is_file() else ICON)


def ensure_icons(folder: Path = ASSETS) -> bool:
    """radide.ico and the file type icons (drawn with Pillow when missing)."""
    names = ["radide.ico"] + sorted({t[3] for t in OWN_TYPES}) + ["source.ico"]
    if all((folder / n).is_file() for n in names):
        return True
    try:
        make_icons(folder)
        return True
    except Exception:  # noqa: BLE001 - Pillow missing: the keys still work (the exe icon is used)
        return False


def make_icons(folder: Path = ASSETS) -> None:
    from PIL import Image, ImageDraw, ImageFont
    folder.mkdir(parents=True, exist_ok=True)
    S = 256

    def font(size):
        for f in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def app_icon():
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((8, 8, S - 8, S - 8), 44, fill=(22, 78, 160, 255))
        d.rounded_rectangle((8, 8, S - 8, 74), 44, fill=(60, 132, 222, 255))      # a form's title bar
        d.rectangle((8, 50, S - 8, 74), fill=(60, 132, 222, 255))
        for i, c in enumerate(((236, 92, 72), (246, 190, 64), (104, 196, 96))):
            d.ellipse((S - 92 + i * 26 - 26, 30, S - 92 + i * 26 - 8, 48), fill=c + (255,))
        d.text((S // 2, 165), "R", font=font(150), fill=(255, 255, 255, 255), anchor="mm")
        d.rectangle((52, 224, 204, 232), fill=(246, 190, 64, 255))                # a cursor / text line
        return im

    def doc_icon(letter, colour):
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        fold = 60
        d.polygon([(40, 12), (S - 40 - fold, 12), (S - 40, 12 + fold), (S - 40, S - 12), (40, S - 12)],
                  fill=(250, 250, 250, 255), outline=(120, 130, 145, 255))
        d.polygon([(S - 40 - fold, 12), (S - 40, 12 + fold), (S - 40 - fold, 12 + fold)],
                  fill=(205, 212, 222, 255), outline=(120, 130, 145, 255))
        for y in (100, 124, 148):
            d.rectangle((64, y, S - 64, y + 8), fill=(200, 206, 216, 255))
        d.rounded_rectangle((24, 150, 150, 246), 20, fill=colour + (255,))
        d.text((87, 197), letter, font=font(80), fill=(255, 255, 255, 255), anchor="mm")
        return im

    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    app_icon().save(folder / "radide.ico", sizes=sizes)
    for name, letter, colour in (("solution.ico", "S", (104, 33, 122)), ("project.ico", "P", (22, 78, 160)),
                                 ("extension.ico", "X", (0, 122, 94)), ("form.ico", "F", (200, 90, 20)),
                                 ("scene.ico", "G", (180, 40, 60)), ("source.ico", "R", (60, 132, 222))):
        doc_icon(letter, colour).save(folder / name, sizes=sizes)


# ----------------------------------------------------------------------------------- extensions
def own_extensions() -> list[str]:
    return [t[0] for t in OWN_TYPES]


def open_with_extensions() -> list[str]:
    exts = set(OPEN_WITH_BASE)
    try:                                       # every language plugin's code file extension
        from .languages import code_extensions
        exts.update(e.lower() for e in code_extensions() if e)
    except Exception:  # noqa: BLE001 - plugins need Qt; the base list is enough
        pass
    own = set(own_extensions())
    return sorted(e for e in exts if e.startswith(".") and e not in own and e not in (".exe", ".dll", ".lnk"))


# ----------------------------------------------------------------------------------- registry primitives
def _winreg():
    import winreg
    return winreg


def _get(key: str, name: str):
    """(data, type) or None."""
    w = _winreg()
    try:
        with w.OpenKey(w.HKEY_CURRENT_USER, key, 0, w.KEY_READ) as k:
            data, typ = w.QueryValueEx(k, name)
            return data, typ
    except OSError:
        return None


def _key_exists(key: str) -> bool:
    w = _winreg()
    try:
        w.CloseKey(w.OpenKey(w.HKEY_CURRENT_USER, key, 0, w.KEY_READ))
        return True
    except OSError:
        return False


def _key_empty(key: str) -> bool:
    w = _winreg()
    try:
        with w.OpenKey(w.HKEY_CURRENT_USER, key, 0, w.KEY_READ) as k:
            subkeys, values, _ = w.QueryInfoKey(k)
            return subkeys == 0 and values == 0
    except OSError:
        return False


def _enc(data):
    return {"hex": data.hex()} if isinstance(data, (bytes, bytearray)) else data


def _dec(data):
    return bytes.fromhex(data["hex"]) if isinstance(data, dict) and "hex" in data else data


class _Writer:
    """Writes values and records everything in the manifest structure."""

    def __init__(self):
        self.keys: list[str] = []          # keys this run created (parents first)
        self.values: list[list] = []       # [key, name, type, data, previous [type, data] | None]

    def ensure_key(self, key: str) -> None:
        w = _winreg()
        parts = key.split("\\")
        for i in range(1, len(parts) + 1):
            sub = "\\".join(parts[:i])
            if not _key_exists(sub):
                w.CloseKey(w.CreateKeyEx(w.HKEY_CURRENT_USER, sub, 0, w.KEY_WRITE))
                self.keys.append(sub)

    def set(self, key: str, name: str, data, typ: int | None = None, overwrite: bool = True) -> bool:
        """Write HKCU\\<key>\\<name>. A different existing value is replaced only when *overwrite*
        (its data is recorded and restored by unregister); an identical one is left alone."""
        w = _winreg()
        if typ is None:
            typ = w.REG_DWORD if isinstance(data, int) else w.REG_SZ
        cur = _get(key, name)
        if cur is not None:
            if cur[0] == data and cur[1] == typ:
                return False
            if not overwrite:
                return False
        self.ensure_key(key)
        with w.OpenKey(w.HKEY_CURRENT_USER, key, 0, w.KEY_WRITE) as k:
            w.SetValueEx(k, name, 0, typ, data)
        prev = None if cur is None else [cur[1], _enc(cur[0])]
        self.values.append([key, name, typ, _enc(data), prev])
        return True


# ----------------------------------------------------------------------------------- manifest
def _read_manifest(t: Target) -> dict | None:
    v = _get(t.manifest_key, "Manifest")
    if not v:
        return None
    try:
        m = json.loads(v[0])
        return m if isinstance(m, dict) else None
    except ValueError:
        return None


def _write_manifest(t: Target, m: dict) -> list[str]:
    w = _winreg()
    created = []
    parts = t.manifest_key.split("\\")
    for i in range(1, len(parts) + 1):
        sub = "\\".join(parts[:i])
        if not _key_exists(sub):
            w.CloseKey(w.CreateKeyEx(w.HKEY_CURRENT_USER, sub, 0, w.KEY_WRITE))
            created.append(sub)
    m["manifest_keys"] = list(dict.fromkeys(m.get("manifest_keys", []) + created))
    with w.OpenKey(w.HKEY_CURRENT_USER, t.manifest_key, 0, w.KEY_WRITE) as k:
        w.SetValueEx(k, "Manifest", 0, w.REG_SZ, json.dumps(m, indent=None))
    return created


def _delete_manifest(t: Target, m: dict) -> None:
    w = _winreg()
    try:
        with w.OpenKey(w.HKEY_CURRENT_USER, t.manifest_key, 0, w.KEY_WRITE) as k:
            w.DeleteValue(k, "Manifest")
    except OSError:
        pass
    for key in reversed(m.get("manifest_keys", [])):
        if _key_empty(key):
            try:
                w.DeleteKey(w.HKEY_CURRENT_USER, key)
            except OSError:
                pass


# ----------------------------------------------------------------------------------- shortcuts
def create_shortcut(path: Path, target: str, args: str = "", workdir: str = "", icon: str = "",
                    description: str = "") -> bool:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import win32com.client  # type: ignore[import-not-found]
        sh = win32com.client.Dispatch("WScript.Shell")
        lnk = sh.CreateShortcut(str(path))
        lnk.TargetPath, lnk.Arguments, lnk.WorkingDirectory = target, args, workdir
        if icon:
            lnk.IconLocation = icon
        lnk.Description = description
        lnk.Save()
        return path.is_file()
    except Exception:  # noqa: BLE001 - no pywin32: PowerShell's WScript.Shell
        pass
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:RADIDE_LNK);"
          "$s.TargetPath=$env:RADIDE_LNK_TARGET;$s.Arguments=$env:RADIDE_LNK_ARGS;"
          "$s.WorkingDirectory=$env:RADIDE_LNK_DIR;if($env:RADIDE_LNK_ICON){$s.IconLocation=$env:RADIDE_LNK_ICON};"
          "$s.Description=$env:RADIDE_LNK_DESC;$s.Save()")
    env = dict(os.environ, RADIDE_LNK=str(path), RADIDE_LNK_TARGET=target, RADIDE_LNK_ARGS=args,
               RADIDE_LNK_DIR=workdir, RADIDE_LNK_ICON=icon, RADIDE_LNK_DESC=description)
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-Command", ps], env=env, capture_output=True, timeout=60,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return False
    return path.is_file()


# ----------------------------------------------------------------------------------- register
def _notify() -> None:
    try:
        import ctypes
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)    # SHCNE_ASSOCCHANGED
    except Exception:  # noqa: BLE001
        pass


def plan(options: dict | None = None, target: Target | None = None) -> list[tuple]:
    """Every value register() would write: (key, name, data, overwrite)."""
    t = target or Target.from_env()
    o = dict(DEFAULT_OPTIONS, **(options or {}))
    ico = icon_path()
    exe, _lead = launcher()
    out: list[tuple] = []

    def add(key, name, data, overwrite=True):
        out.append((key, name, data, overwrite))

    def progid(pid: str, desc: str, icon: str):
        k = t.cls(pid)
        add(k, "", desc)
        add(k, "FriendlyTypeName", desc)
        add(k + "\\DefaultIcon", "", icon)
        add(k + "\\Application", "ApplicationName", APP)
        add(k + "\\Application", "ApplicationCompany", PUBLISHER)
        add(k + "\\Application", "ApplicationIcon", ico)
        add(k + "\\shell", "", "open")
        add(k + "\\shell\\open", "FriendlyAppName", APP)
        add(k + "\\shell\\open", "Icon", ico)
        add(k + "\\shell\\open\\command", "", open_command())

    caps: dict[str, str] = {}
    if o.get("file_assoc"):
        done = set()
        for ext, suffix, desc, icon, strong in OWN_TYPES:
            pid = f"{PROG}.{suffix}"
            if pid not in done:
                progid(pid, desc, icon_path(icon))
                done.add(pid)
            add(t.cls(ext), "", pid, overwrite=strong)
            add(t.cls(ext + "\\OpenWithProgids"), pid, "")
            caps[ext] = pid
    if o.get("open_with"):
        progid(SOURCE_PROGID, "Source file", icon_path("source.ico"))
        for ext in open_with_extensions():
            add(t.cls(ext + "\\OpenWithProgids"), SOURCE_PROGID, "")
            caps[ext] = SOURCE_PROGID
    if frozen() and (o.get("file_assoc") or o.get("open_with")):     # the installed exe: Applications\RADIDE.exe
        app = t.cls("Applications\\" + Path(exe).name)
        add(app, "FriendlyAppName", APP)
        add(app + "\\DefaultIcon", "", ico)
        add(app + "\\shell\\open\\command", "", open_command())
        for ext in caps:
            add(app + "\\SupportedTypes", ext, "")
    if caps:                                     # Settings > Default apps knows RAD IDE
        add(t.capabilities_key, "ApplicationName", APP)
        add(t.capabilities_key, "ApplicationDescription",
            "RAD IDE - a Visual Basic style IDE for Python and many other languages")
        add(t.capabilities_key, "ApplicationIcon", ico)
        for ext, pid in caps.items():
            add(t.capabilities_key + "\\FileAssociations", ext, pid)
        add(t.registered_apps_key, APP, t.capabilities_key)
    if o.get("context_menu"):
        for sub, text, arg in (("*\\shell\\RADIDE", "Open with RAD IDE", "%1"),
                               ("Directory\\shell\\RADIDE", "Open folder in RAD IDE", "%1"),
                               ("Directory\\Background\\shell\\RADIDE", "Open folder in RAD IDE", "%V")):
            add(t.cls(sub), "", text)
            add(t.cls(sub), "Icon", ico)
            add(t.cls(sub + "\\command"), "", open_command(arg))
    if o.get("uninstall_entry"):
        u = t.uninstall_key
        add(u, "DisplayName", APP)
        add(u, "DisplayIcon", ico)
        add(u, "Publisher", PUBLISHER)
        add(u, "URLInfoAbout", URL)
        add(u, "HelpLink", URL)
        add(u, "Comments", "Windows integration: file associations, Explorer menus and shortcuts")
        add(u, "InstallLocation", str(REPO if not frozen() else Path(exe).parent))
        add(u, "UninstallString", command("--unregister"))
        add(u, "QuietUninstallString", command("--unregister", "--quiet"))
        add(u, "NoModify", 1)
        add(u, "NoRepair", 1)
    return out


def shortcut_plan(options: dict | None = None, target: Target | None = None) -> list[Path]:
    t = target or Target.from_env()
    o = dict(DEFAULT_OPTIONS, **(options or {}))
    out = []
    if o.get("start_menu") and t.start_menu is not None:
        out.append(t.start_menu / f"{APP}.lnk")
    if o.get("desktop") and t.desktop is not None:
        out.append(t.desktop / f"{APP}.lnk")
    return out


def register(options: dict | None = None, target: Target | None = None) -> dict:
    """Register RAD IDE with Windows for the current user. Re-registering first undoes the previous
    registration (so moved repositories / changed options are clean). Returns status()."""
    if sys.platform != "win32":
        raise OSError("Windows shell integration is only available on Windows")
    t = target or Target.from_env()
    o = dict(DEFAULT_OPTIONS, **{k: bool(v) for k, v in (options or {}).items()})
    if _read_manifest(t) is not None:
        unregister(t, notify=False)
    wr = _Writer()
    files: list[str] = []
    m = {"version": 1, "app": APP, "options": o, "launcher": open_command(), "time": time.strftime("%Y-%m-%d %H:%M:%S"),
         "keys": wr.keys, "values": wr.values, "files": files, "test": t.test}
    try:
        for key, name, data, overwrite in plan(o, t):
            wr.set(key, name, data, overwrite=overwrite)
        exe, lead = launcher()
        for lnk in shortcut_plan(o, t):
            if lnk.exists():                 # someone else's shortcut (an installer...): left alone
                continue
            if create_shortcut(lnk, exe, " ".join(_q(a) for a in lead), str(REPO if lead else Path(exe).parent),
                               icon_path(), "RAD IDE - Visual Basic style IDE"):
                files.append(str(lnk))
    finally:
        _write_manifest(t, m)
        if t.notify:
            _notify()
    return status(t)


def unregister(target: Target | None = None, notify: bool | None = None) -> dict:
    """Undo register(): values that still hold RAD IDE's data are deleted (or get their previous data
    back), keys RAD IDE created are removed when empty, its shortcuts are deleted."""
    if sys.platform != "win32":
        raise OSError("Windows shell integration is only available on Windows")
    t = target or Target.from_env()
    m = _read_manifest(t)
    removed = {"values": 0, "restored": 0, "keys": 0, "files": 0, "kept": 0}
    if m is None:
        return {**status(t), "removed": removed}
    w = _winreg()
    for key, name, typ, data, prev in reversed(m.get("values", [])):
        cur = _get(key, name)
        if cur is None:
            continue
        if cur[0] != _dec(data) or cur[1] != typ:          # changed by someone else since: keep it
            removed["kept"] += 1
            continue
        try:
            with w.OpenKey(w.HKEY_CURRENT_USER, key, 0, w.KEY_WRITE) as k:
                if prev is None:
                    w.DeleteValue(k, name)
                    removed["values"] += 1
                else:
                    w.SetValueEx(k, name, 0, prev[0], _dec(prev[1]))
                    removed["restored"] += 1
        except OSError:
            pass
    for key in sorted(m.get("keys", []), key=lambda k: k.count("\\"), reverse=True):
        if _key_empty(key):
            try:
                w.DeleteKey(w.HKEY_CURRENT_USER, key)
                removed["keys"] += 1
            except OSError:
                pass
    for f in m.get("files", []):
        try:
            Path(f).unlink()
            removed["files"] += 1
        except OSError:
            pass
    _delete_manifest(t, m)
    for key in sorted(m.get("keys", []), key=lambda k: k.count("\\"), reverse=True):
        if _key_empty(key):                  # parents that held only the manifest key
            try:
                w.DeleteKey(w.HKEY_CURRENT_USER, key)
                removed["keys"] += 1
            except OSError:
                pass
    if (t.notify if notify is None else notify):
        _notify()
    return {**status(t), "removed": removed}


def status(target: Target | None = None) -> dict:
    t = target or Target.from_env()
    m = _read_manifest(t) if sys.platform == "win32" else None
    cur = open_command()
    if m is None:
        return {"registered": False, "options": {}, "launcher": "", "current_launcher": cur, "stale": False,
                "values": 0, "keys": 0, "files": [], "test": t.test, "time": ""}
    return {"registered": True, "options": m.get("options", {}), "launcher": m.get("launcher", ""),
            "current_launcher": cur, "stale": m.get("launcher", "") != cur, "values": len(m.get("values", [])),
            "keys": len(m.get("keys", [])), "files": list(m.get("files", [])), "test": t.test,
            "time": m.get("time", "")}


# ----------------------------------------------------------------------------------- installer / pythonw helpers
def inno_lines(exe: str = "RADIDE.exe") -> list[str]:
    """[Run] / [UninstallRun] lines for an Inno Setup script of the RAD IDE itself: the installed exe
    writes (and removes) exactly the keys above, so there is one source of truth."""
    return ["[Run]",
            f'Filename: "{{app}}\\{exe}"; Parameters: "--register --quiet --no-uninstall-entry"; '
            'Flags: runhidden waituntilterminated; StatusMsg: "Registering file types..."',
            "", "[UninstallRun]",
            f'Filename: "{{app}}\\{exe}"; Parameters: "--unregister --quiet"; Flags: runhidden waituntilterminated; '
            'RunOnceId: "RADIDEUnregister"']


def no_console_children() -> None:
    """Under pythonw (no console) every console child process (git, compilers, language servers) would
    flash its own console window: start them with CREATE_NO_WINDOW unless they ask for a console.
    (QProcess already does this when the parent has no console.)"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        if ctypes.windll.kernel32.GetConsoleWindow():
            return
    except Exception:  # noqa: BLE001
        return
    if getattr(subprocess.Popen, "_radide_no_console", False):
        return
    orig = subprocess.Popen.__init__
    NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10)
    DETACHED = getattr(subprocess, "DETACHED_PROCESS", 0x8)
    NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    def init(self, *a, **k):
        flags = k.get("creationflags", 0) or 0
        if not flags & (NEW_CONSOLE | DETACHED | NO_WINDOW):
            k["creationflags"] = flags | NO_WINDOW
        orig(self, *a, **k)
    subprocess.Popen.__init__ = init
    subprocess.Popen._radide_no_console = True


# ----------------------------------------------------------------------------------- command line
def _say(text: str, quiet: bool, error: bool = False) -> None:
    if quiet:
        return
    out = sys.stderr if error else sys.stdout
    if out is not None and sys.__stdout__ is not None:      # a console (pythonw: __stdout__ is None)
        try:
            out.write(text + "\n")
            out.flush()
            return
        except Exception:  # noqa: BLE001
            pass
    try:                                       # pythonw (the Uninstall entry): a message box
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, APP, 0x10 if error else 0x40)
    except Exception:  # noqa: BLE001
        pass


def describe(st: dict) -> str:
    if not st.get("registered"):
        return "RAD IDE is not registered with Windows."
    on = [k for k in OPTIONS if st.get("options", {}).get(k)]
    text = f"RAD IDE is registered with Windows ({st['values']} values, {len(st['files'])} shortcuts; {', '.join(on)})."
    if st.get("stale"):
        text += "\nIt was registered for another location: register again."
    return text


def cli(register_: bool = False, unregister_: bool = False, show_status: bool = False, quiet: bool = False,
        desktop: bool | None = None, uninstall_entry: bool = True, only: str | None = None,
        if_owner: bool = False) -> int:
    """``python -m radide --register / --unregister / --status``. *only* (``--shell-options a,b``): register
    exactly these OPTIONS (the RAD IDE installer's tasks), the others off. *if_owner* (``--if-owner``, the
    installer's uninstaller): unregister only when the registration points at this launcher, never a
    registration made by another copy (a source checkout, a portable folder)."""
    if unregister_ and if_owner and status().get("stale"):
        _say("RAD IDE's Windows integration belongs to another copy of RAD IDE: kept.", quiet)
        return 0
    try:
        if register_:
            prev = status().get("options") or {}
            opts = {k: prev.get(k, DEFAULT_OPTIONS[k]) for k in OPTIONS}
            if only is not None:
                chosen = {s.strip() for s in only.replace(";", ",").split(",") if s.strip()}
                opts = {k: k in chosen for k in OPTIONS}
            if desktop is not None:
                opts["desktop"] = desktop
            opts["uninstall_entry"] = uninstall_entry
            st = register(opts)
            _say(describe(st), quiet)
        elif unregister_:
            st = unregister()
            r = st.get("removed", {})
            _say(f"RAD IDE's Windows integration was removed ({r.get('values', 0)} values deleted, "
                 f"{r.get('restored', 0)} restored, {r.get('files', 0)} shortcuts).", quiet)
        else:
            _say(describe(status()), quiet)
        return 0
    except Exception as e:  # noqa: BLE001
        _say(f"Windows integration failed: {e}", quiet, error=True)
        return 1


__all__ = ["register", "unregister", "status", "plan", "shortcut_plan", "Target", "OPTIONS", "DEFAULT_OPTIONS",
           "OPTION_LABELS", "OWN_TYPES", "open_with_extensions", "launcher", "open_command", "ensure_icons",
           "make_icons", "inno_lines", "no_console_children", "cli", "describe"]
