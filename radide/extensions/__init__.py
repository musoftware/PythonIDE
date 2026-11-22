"""RAD IDE extensions: install, enable/disable, uninstall and load third-party add-ons.

An extension is a folder with a ``radide-extension.json`` manifest (see docs/PLUGIN_API.md). Installed
extensions live in ``%APPDATA%\\RADIDE\\extensions\\<id>`` (override with the environment variable
``RADIDE_EXTENSIONS_DIR``); which ones are disabled is stored in ``extensions.json`` in that folder.

Loading happens in two steps, both called by ``radide.features.install_all``:

* ``preload()`` - before the built-in features: registers declarative contributions (themes, language
  plugins, AI providers) so the Options dialog, menus and New Project see them;
* ``activate_all(win)`` - after the built-in features: imports each enabled extension's ``main`` module and
  calls ``activate(api)`` (or ``install(win)``, the feature-module contract).

Every step of every extension is isolated: an exception is recorded in ``Extension.errors`` and written to
the Output window, the other extensions and the IDE keep working. ``RADIDE_SAFE_MODE=1`` skips all
extensions. Extensions run Python code with the user's permissions: install only trusted ones.
"""
from __future__ import annotations

import copy
import importlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

MANIFEST = "radide-extension.json"
API_VERSION = "1.0"
ID_RX = re.compile(r"^[a-z0-9][a-z0-9_-]*(\.[a-z0-9][a-z0-9_-]*)+$")
VERSION_RX = re.compile(r"^\d+(\.\d+){0,3}([-+][0-9A-Za-z.-]+)?$")
# "components": [{"folder": "components/StarRating"}] - component packages (docs/COMPONENTS.md)
CONTRIBUTION_KINDS = ("themes", "languages", "aiProviders", "toolbox", "snippets", "components")


class ExtensionError(Exception):
    pass


# ============================================================================ locations / state
def extensions_dir() -> Path:
    env = os.environ.get("RADIDE_EXTENSIONS_DIR")
    if env:
        d = Path(env)
    else:
        from ..paths import roaming_dir      # <install>\settings for a portable build
        d = roaming_dir() / "extensions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _state_path() -> Path:
    return extensions_dir() / "extensions.json"


def _read_state() -> dict:
    try:
        data = json.loads(_state_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_state(state: dict) -> None:
    p = _state_path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def safe_mode() -> bool:
    return os.environ.get("RADIDE_SAFE_MODE", "").strip().lower() in ("1", "true", "yes")


# ============================================================================ manifest
@dataclass
class Extension:
    id: str
    name: str
    version: str
    path: Path
    manifest: dict
    enabled: bool = True
    errors: list = field(default_factory=list)
    active: bool = False              # main module activated in this session
    module: object = None
    api: object = None
    registered: dict = field(default_factory=dict)   # kind -> [names] registered by this extension

    @property
    def description(self) -> str:
        return str(self.manifest.get("description", ""))

    @property
    def author(self) -> str:
        a = self.manifest.get("author", "")
        return a.get("name", "") if isinstance(a, dict) else str(a)

    @property
    def contributes(self) -> dict:
        c = self.manifest.get("contributes") or {}
        return c if isinstance(c, dict) else {}

    def summary(self) -> str:
        parts = []
        for kind in CONTRIBUTION_KINDS:
            items = self.contributes.get(kind) or []
            if items:
                parts.append(f"{len(items)} {kind}")
        if self.manifest.get("main"):
            parts.append("code")
        return ", ".join(parts) or "nothing"


def validate_manifest(data, folder: Path | None = None) -> list[str]:
    """Problems of a manifest (empty list = valid)."""
    errs = []
    if not isinstance(data, dict):
        return ["the manifest must be a JSON object"]
    ext_id = data.get("id")
    if not isinstance(ext_id, str) or not ID_RX.match(ext_id):
        errs.append("'id' must look like 'publisher.name' (lower case letters, digits, '-', '_', dots)")
    if not isinstance(data.get("name"), str) or not data.get("name", "").strip():
        errs.append("'name' is required")
    if not isinstance(data.get("version"), str) or not VERSION_RX.match(data.get("version", "")):
        errs.append("'version' must look like 1.0.0")
    main = data.get("main")
    if main is not None:
        if not isinstance(main, str) or not main.endswith(".py") or ".." in Path(main).parts:
            errs.append("'main' must be a .py file inside the extension")
        elif folder is not None and not (folder / main).is_file():
            errs.append(f"'main' file not found: {main}")
    contrib = data.get("contributes", {})
    if not isinstance(contrib, dict):
        errs.append("'contributes' must be an object")
        contrib = {}
    for kind, items in contrib.items():
        if kind not in CONTRIBUTION_KINDS:
            errs.append(f"unknown contribution '{kind}' (known: {', '.join(CONTRIBUTION_KINDS)})")
            continue
        if not isinstance(items, list):
            errs.append(f"contributes.{kind} must be a list")
            continue
        for it in items:
            if not isinstance(it, dict):
                errs.append(f"contributes.{kind}: every entry must be an object")
                continue
            for key in ("file", "module", "folder"):
                rel = it.get(key)
                if rel is None:
                    continue
                if not isinstance(rel, str) or ".." in Path(rel).parts or Path(rel).is_absolute():
                    errs.append(f"contributes.{kind}: '{key}' must be a relative path inside the extension")
                elif folder is not None and not (folder / rel).exists():
                    errs.append(f"contributes.{kind}: not found: {rel}")
            if kind == "themes" and not isinstance(it.get("name"), str):
                errs.append("contributes.themes: each theme needs a 'name'")
    eng = data.get("engines", {})
    if isinstance(eng, dict) and isinstance(eng.get("radide"), str):
        m = re.match(r"\s*>=?\s*(\d+)\.(\d+)", eng["radide"])
        if m and (int(m.group(1)), int(m.group(2))) > tuple(int(x) for x in API_VERSION.split(".")):
            errs.append(f"needs RAD IDE extension API {eng['radide']} (this IDE has {API_VERSION})")
    return errs


def read_manifest(folder: Path) -> dict:
    p = Path(folder) / MANIFEST
    if not p.is_file():
        raise ExtensionError(f"{MANIFEST} not found in {folder}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except ValueError as e:
        raise ExtensionError(f"{MANIFEST} is not valid JSON: {e}") from None
    errs = validate_manifest(data, Path(folder))
    if errs:
        raise ExtensionError("invalid extension manifest:\n- " + "\n- ".join(errs))
    return data


def _find_root(folder: Path) -> Path:
    """The folder that holds the manifest (the folder itself or its only sub-folder)."""
    if (folder / MANIFEST).is_file():
        return folder
    subs = [p for p in folder.iterdir() if p.is_dir() and not p.name.startswith((".", "__MACOSX"))]
    for s in subs:
        if (s / MANIFEST).is_file():
            return s
    raise ExtensionError(f"no {MANIFEST} found in {folder}")


# ============================================================================ registry
_EXTS: dict[str, Extension] = {}
_listeners: list = []


def on_change(fn) -> None:
    """fn() is called after an extension was installed, enabled, disabled or removed."""
    _listeners.append(fn)


def _changed() -> None:
    for fn in list(_listeners):
        try:
            fn()
        except Exception:  # noqa: BLE001
            traceback.print_exc()


def scan() -> list[Extension]:
    """Read every installed extension (keeps the runtime state of known ones)."""
    state = _read_state()
    disabled = set(state.get("disabled", []))
    found = {}
    for d in sorted(extensions_dir().iterdir(), key=lambda p: p.name.lower()):
        if not d.is_dir() or not (d / MANIFEST).is_file():
            continue
        try:
            data = read_manifest(d)
        except ExtensionError as e:
            ext = Extension(d.name, d.name, "?", d, {}, enabled=False, errors=[str(e)])
            found[d.name] = ext
            continue
        old = _EXTS.get(data["id"])
        ext = Extension(data["id"], data["name"], data["version"], d, data, data["id"] not in disabled)
        if old is not None and old.path == d:
            ext.active, ext.module, ext.api, ext.registered = old.active, old.module, old.api, old.registered
            ext.errors = old.errors if old.version == ext.version else []
        found[ext.id] = ext
    _EXTS.clear()
    _EXTS.update(found)
    return list(_EXTS.values())


def installed() -> list[Extension]:
    return list(_EXTS.values()) if _EXTS else scan()


def get(ext_id: str) -> Extension | None:
    if not _EXTS:
        scan()
    return _EXTS.get(ext_id)


# ============================================================================ install / uninstall
def install_from_folder(src, overwrite: bool = True) -> Extension:
    src = _find_root(Path(src))
    data = read_manifest(src)
    dest = extensions_dir() / data["id"]
    old = get(data["id"])
    if dest.exists():
        if not overwrite:
            raise ExtensionError(f"extension {data['id']} is already installed")
        if old is not None:
            _deactivate(old)
        shutil.rmtree(dest, onerror=_force_remove)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    (dest / ".installed-from").write_text(str(src), encoding="utf-8")
    scan()
    ext = _EXTS[data["id"]]
    _changed()
    return ext


def install_from_zip(zip_path) -> Extension:
    zip_path = Path(zip_path)
    if not zipfile.is_zipfile(zip_path):
        raise ExtensionError(f"not a zip file: {zip_path}")
    with tempfile.TemporaryDirectory(prefix="radext_") as tmp:
        root = Path(tmp).resolve()
        with zipfile.ZipFile(zip_path) as z:
            total = 0
            for info in z.infolist():
                target = (root / info.filename).resolve()
                if root not in target.parents and target != root:      # zip-slip guard
                    raise ExtensionError(f"unsafe path in zip: {info.filename}")
                total += info.file_size
                if total > 200 * 1024 * 1024:
                    raise ExtensionError("the zip is too large (more than 200 MB unpacked)")
            z.extractall(root)
        ext = install_from_folder(root)
    (ext.path / ".installed-from").write_text(str(zip_path), encoding="utf-8")
    return ext


def install_from_git(url: str, ref: str | None = None) -> Extension:
    url = url.strip()
    if not re.match(r"^(https://|http://|ssh://|git@|file://)", url) and not Path(url).exists():
        raise ExtensionError("use an https://, ssh://, git@ or file:// URL (or a local repository folder)")
    git = shutil.which("git")
    if git is None:
        raise ExtensionError("git was not found in PATH")
    with tempfile.TemporaryDirectory(prefix="radext_git_") as tmp:
        dest = Path(tmp) / "repo"
        cmd = [git, "clone", "--depth", "1", "--quiet"]
        if ref:
            cmd += ["--branch", ref]
        cmd += ["--", url, str(dest)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0"),
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if p.returncode != 0:
            raise ExtensionError(f"git clone failed:\n{(p.stderr or p.stdout).strip()}")
        ext = install_from_folder(dest)
    (ext.path / ".installed-from").write_text(url, encoding="utf-8")
    return ext


def install(source: str) -> Extension:
    """Install from a folder, a .zip file or a git URL."""
    s = str(source).strip()
    p = Path(s)
    if p.is_dir():
        try:
            _find_root(p)
            return install_from_folder(p)
        except ExtensionError:
            if not (p / ".git").exists():
                raise
    if p.is_file() and p.suffix.lower() in (".zip", ".radext"):
        return install_from_zip(p)
    return install_from_git(s)


def _force_remove(func, path, _exc):
    try:
        os.chmod(path, 0o700)
        func(path)
    except OSError:
        pass


def uninstall(ext_id: str) -> None:
    ext = get(ext_id)
    if ext is None:
        raise ExtensionError(f"extension {ext_id} is not installed")
    _deactivate(ext)
    shutil.rmtree(ext.path, onerror=_force_remove)
    state = _read_state()
    state["disabled"] = [i for i in state.get("disabled", []) if i != ext_id]
    _write_state(state)
    _EXTS.pop(ext_id, None)
    _changed()


def set_enabled(ext_id: str, enabled: bool, win=None) -> Extension:
    """Enable or disable; with *win* the change is applied at once (activate / deactivate)."""
    ext = get(ext_id)
    if ext is None:
        raise ExtensionError(f"extension {ext_id} is not installed")
    state = _read_state()
    disabled = [i for i in state.get("disabled", []) if i != ext_id]
    if not enabled:
        disabled.append(ext_id)
    state["disabled"] = disabled
    _write_state(state)
    ext.enabled = enabled
    if win is not None:
        if enabled:
            if not ext.registered:
                _register_contributions(ext, win)
            _activate(ext, win)
        else:
            _deactivate(ext)
    _changed()
    return ext


# ============================================================================ contributions
def _log(win, text: str) -> None:
    try:
        if win is not None:
            win.log(text)
            return
    except Exception:  # noqa: BLE001
        pass
    sys.stderr.write(text + "\n")


def _fail(ext: Extension, what: str, win=None) -> None:
    msg = f"[extension {ext.id}] {what} failed:\n{traceback.format_exc()}"
    ext.errors.append(msg)
    _log(win, msg)


def register_theme(name: str, data: dict, owner: str = "") -> str:
    """Add a colour theme. *data*: {"base": "Dark", "colors": {token: "#rrggbb"}, "code": {...},
    "chrome": {...}, "monaco": "vs-dark", "dark": true}. Missing tokens come from the base theme."""
    from .. import theme as T
    base = data.get("base", "Dark")
    if base not in T.THEMES:
        raise ExtensionError(f"unknown base theme {base!r}")
    if name in T.THEMES and name in ("Light", "Blue", "Dark", "High Contrast", "System"):
        raise ExtensionError(f"'{name}' is a built-in theme name")
    t = copy.deepcopy(T.THEMES[base])
    colors = data.get("colors", {})
    unknown = [k for k in colors if k not in t]
    if unknown:
        raise ExtensionError(f"unknown theme tokens: {', '.join(sorted(unknown))}")
    for k, v in colors.items():
        if not isinstance(v, str) or not re.match(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$", v):
            raise ExtensionError(f"theme token {k}: colour must be #RRGGBB, got {v!r}")
        t[k] = v
    for part in ("code", "chrome"):
        if isinstance(data.get(part), dict):
            t[part] = dict(t[part], **data[part])
    if "monaco" in data:
        t["monaco"] = str(data["monaco"])
    if "dark" in data:
        t["dark"] = bool(data["dark"])
    t["_extension"] = owner
    T.THEMES[name] = t
    if name not in T.THEME_NAMES:
        T.THEME_NAMES.append(name)
    return name


def unregister_theme(name: str) -> None:
    from .. import theme as T
    if name in T.THEMES and T.THEMES[name].get("_extension"):
        was_current = T.current_name() == name
        T.THEMES.pop(name, None)
        if name in T.THEME_NAMES:
            T.THEME_NAMES.remove(name)
        if was_current:
            T.apply("Light")


def _load_module(ext: Extension, rel: str, suffix: str):
    path = ext.path / rel
    safe = re.sub(r"\W", "_", ext.id)
    modname = f"radide_ext_{safe}.{suffix}" if suffix else f"radide_ext_{safe}"
    if suffix and f"radide_ext_{safe}" not in sys.modules:
        pkg_spec = importlib.util.spec_from_loader(f"radide_ext_{safe}", loader=None, is_package=True)
        pkg = importlib.util.module_from_spec(pkg_spec)
        pkg.__path__ = [str(ext.path)]
        sys.modules[f"radide_ext_{safe}"] = pkg
    spec = importlib.util.spec_from_file_location(modname, str(path),
                                                  submodule_search_locations=None if suffix else [str(ext.path)])
    if spec is None or spec.loader is None:
        raise ExtensionError(f"cannot load {rel}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(modname, None)
        raise
    return mod


def _register_contributions(ext: Extension, win=None) -> None:
    c = ext.contributes
    reg = ext.registered
    for th in c.get("themes", []):
        try:
            data = th
            if th.get("file"):
                data = dict(json.loads((ext.path / th["file"]).read_text(encoding="utf-8-sig")), **{
                    k: v for k, v in th.items() if k not in ("file", "name")})
            name = register_theme(th["name"], data, ext.id)
            reg.setdefault("themes", []).append(name)
        except Exception:  # noqa: BLE001
            _fail(ext, f"theme {th.get('name')!r}", win)
    for lang in c.get("languages", []):
        try:
            mod = _load_module(ext, lang["module"], "lang_" + re.sub(r"\W", "_", Path(lang["module"]).stem))
            from ..languages import LanguagePlugin, _PLUGINS, all_plugins
            all_plugins()
            plugin = getattr(mod, "PLUGIN", None)
            if not isinstance(plugin, LanguagePlugin):
                raise ExtensionError(f"{lang['module']} must define PLUGIN = <LanguagePlugin subclass>()")
            if plugin.id in _PLUGINS and plugin.id not in reg.get("languages", []):
                raise ExtensionError(f"a language with id {plugin.id!r} already exists")
            _PLUGINS[plugin.id] = plugin
            reg.setdefault("languages", []).append(plugin.id)
        except Exception:  # noqa: BLE001
            _fail(ext, f"language {lang.get('module')!r}", win)
    for prov in c.get("aiProviders", []):
        try:
            mod = _load_module(ext, prov["module"], "ai_" + re.sub(r"\W", "_", Path(prov["module"]).stem))
            from .. import ai
            items = getattr(mod, "PROVIDERS", None) or [getattr(mod, "PROVIDER", None)]
            for p in items:
                if p is None or not getattr(p, "id", ""):
                    raise ExtensionError(f"{prov['module']} must define PROVIDER (an ai Provider instance)")
                ai.register(p)
                reg.setdefault("aiProviders", []).append(p.id)
        except Exception:  # noqa: BLE001
            _fail(ext, f"AI provider {prov.get('module')!r}", win)


def _unregister_contributions(ext: Extension) -> None:
    reg = ext.registered
    for name in reg.get("themes", []):
        try:
            unregister_theme(name)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
    if reg.get("languages"):
        try:
            from ..languages import _PLUGINS
            for pid in reg["languages"]:
                _PLUGINS.pop(pid, None)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
    if reg.get("aiProviders"):
        try:
            _prov = importlib.import_module(__name__.rsplit(".", 1)[0] + ".ai.providers")
            for pid in reg["aiProviders"]:
                _prov._providers.pop(pid, None)
            if getattr(_prov, "_hub", None) is not None:
                _prov._hub.providers_changed.emit()
        except Exception:  # noqa: BLE001
            traceback.print_exc()
    ext.registered = {}


# ============================================================================ activation
def _activate(ext: Extension, win) -> None:
    if ext.active or not ext.enabled or not ext.manifest.get("main"):
        return
    from .api import ExtensionAPI
    try:
        mod = _load_module(ext, ext.manifest["main"], "")
        api = ExtensionAPI(win, ext)
        ext.module, ext.api = mod, api
        if callable(getattr(mod, "activate", None)):
            mod.activate(api)
        elif callable(getattr(mod, "install", None)):
            mod.install(win)
        else:
            raise ExtensionError(f"{ext.manifest['main']} defines neither activate(api) nor install(win)")
        ext.active = True
        _log(win, f"[extensions] {ext.name} {ext.version} activated")
    except Exception:  # noqa: BLE001 - a broken extension must not stop the IDE
        _fail(ext, "activation", win)
        if ext.api is not None:
            try:
                ext.api._dispose()
            except Exception:  # noqa: BLE001
                pass


def _deactivate(ext: Extension) -> None:
    win = getattr(ext.api, "win", None)
    if ext.active and ext.module is not None and callable(getattr(ext.module, "deactivate", None)):
        try:
            ext.module.deactivate()
        except Exception:  # noqa: BLE001
            _fail(ext, "deactivate()", win)
    if ext.api is not None:
        try:
            ext.api._dispose()
        except Exception:  # noqa: BLE001
            _fail(ext, "cleanup", win)
    _unregister_contributions(ext)
    safe = re.sub(r"\W", "_", ext.id)
    for name in [m for m in sys.modules if m == f"radide_ext_{safe}" or m.startswith(f"radide_ext_{safe}.")]:
        sys.modules.pop(name, None)
    ext.active, ext.module, ext.api = False, None, None


def preload(win=None) -> None:
    """Register themes / languages / AI providers of enabled extensions (before the IDE features)."""
    if safe_mode():
        _log(win, "[extensions] safe mode: extensions are not loaded")
        return
    try:
        exts = scan()
    except Exception:  # noqa: BLE001
        _log(win, f"[extensions] cannot read the extensions folder:\n{traceback.format_exc()}")
        return
    for ext in exts:
        if ext.enabled and not ext.registered:
            try:
                _register_contributions(ext, win)
            except Exception:  # noqa: BLE001
                _fail(ext, "contributions", win)


def activate_all(win) -> None:
    """Run the code of every enabled extension (after the IDE features are installed)."""
    if safe_mode():
        return
    for ext in installed():
        if ext.enabled:
            _activate(ext, win)
        for e in ext.errors:
            if "[extension" not in e:
                _log(win, f"[extension {ext.id}] {e}")


def load(ext_id: str, win) -> Extension | None:
    """Apply an installed, enabled extension now (contributions + code) - used right after installing."""
    ext = get(ext_id)
    if ext is None or not ext.enabled or safe_mode():
        return ext
    if not ext.registered:
        _register_contributions(ext, win)
    _activate(ext, win)
    return ext


def toolbox_items(ext: Extension) -> list[dict]:
    return [t for t in ext.contributes.get("toolbox", []) if isinstance(t, dict)]


def add_toolbox_control(win, ext: Extension, item: dict) -> str:
    """Copy a user control shipped by an extension into the current project (it then appears in the
    Toolbox like any user control). *item*: {"name": "StarRating", "folder": "controls/StarRating"}; the
    folder holds <name>.form and <name>.<ext> code files for the languages it supports."""
    project = getattr(win, "project", None)
    if project is None:
        raise ExtensionError("open a project first")
    name = item.get("name") or ""
    src = ext.path / item.get("folder", "")
    form_file = src / f"{name}.form"
    if not form_file.is_file():
        raise ExtensionError(f"{form_file} not found")
    from ..languages import get_plugin
    plugin = get_plugin(project.language)
    code_file = src / plugin.code_file(name)
    if not code_file.is_file():
        raise ExtensionError(f"this control has no code for {plugin.display_name or plugin.id} "
                             f"({plugin.code_file(name)} missing)")
    dest_form = project.form_path(name)
    if dest_form.exists():
        raise ExtensionError(f"the project already has {dest_form.name}")
    shutil.copyfile(form_file, dest_form)
    shutil.copyfile(code_file, project.folder / plugin.code_file(name))
    from .. import usercontrols as uc
    from ..model import Form
    form = Form.load(dest_form)
    uc.register(name, form.to_dict(), dest_form)
    (project.folder / plugin.designer_file(name)).write_text(
        plugin.generate_designer(form, code_file.read_text(encoding="utf-8")), encoding="utf-8")
    if name not in project.forms:
        project.forms.append(name)
    project.save()
    feat = getattr(win, "user_controls", None)
    if feat is not None and hasattr(feat, "refresh_toolbox"):
        feat.refresh_toolbox()
    return name


__all__ = ["MANIFEST", "API_VERSION", "Extension", "ExtensionError", "extensions_dir", "validate_manifest",
           "read_manifest", "scan", "installed", "get", "install", "install_from_folder", "install_from_zip",
           "install_from_git", "uninstall", "set_enabled", "register_theme", "unregister_theme", "preload",
           "activate_all", "load", "on_change", "safe_mode", "toolbox_items", "add_toolbox_control"]
