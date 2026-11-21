"""Component packages: every control of the designer is a self-describing package (docs/COMPONENTS.md).

A package is a folder::

    StarRating/
        component.json        manifest: name, version, Toolbox category, icon, properties (type, default,
                              editor), events, methods, default size, kind, targets (runtimes)
        icon.png              Toolbox icon (optional)
        designer.py           how it is drawn on the design surface (optional - default renderer otherwise)
        editors.py            custom Properties window editors (optional)
        runtime/<module>.py   one runtime per target language / toolkit (python-tk, python-qt, ...)
        help.md               F1 help (optional)

Where packages are found (later sources win when two packages have the same name):

1. ``builtin``   - ``radide/components/builtin/*`` (the IDE's own controls; ``targets: {"*": {"native": true}}``)
2. ``extension`` - enabled extensions that contribute ``"components": [{"folder": "..."}]``
3. ``user``      - ``%APPDATA%\\RADIDE\\components\\*`` (``RADIDE_COMPONENTS_DIR`` overrides it); .radcomp
   installs go here
4. ``project``   - ``<project>/.radide/components/*`` (components that travel with one project)
5. ``dev``       - folders listed in ``RADIDE_COMPONENT_PATH`` (packages being developed, hot reloaded)

Built-in names (and the mobile controls) can only be replaced by a package that says
``"overrideBuiltin": true``. Between two non-built-in packages the higher source wins, then the higher
version; the loser is listed in :attr:`Registry.conflicts`.

``radide.controls.CONTROL_TYPES`` stays the API every generator, the designer and the Properties window use:
the registry builds the built-in types (:func:`builtin_control_types`) and adds/removes the other packages'
types there (:meth:`Registry.apply`).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import traceback
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from . import proptypes
from .schema import SCHEMA, SCHEMA_VERSION, validate_manifest, version_key

MANIFEST = "component.json"
PACKAGE_EXT = ".radcomp"
API_VERSION = "1.0"
BUILTIN_DIR = Path(__file__).resolve().parent / "builtin"
SOURCES = ("builtin", "extension", "user", "project", "dev")
SOURCE_RANK = {s: i for i, s in enumerate(SOURCES)}
SOURCE_LABEL = {"builtin": "Built-in", "extension": "Extension", "user": "Installed", "project": "Project",
                "dev": "Development"}
MISSING_CATEGORY = "__missing__"
# Toolbox group order (VS 2005); other categories follow alphabetically, "General" last
CATEGORY_ORDER = ["Common Controls", "Containers", "Menus & Toolbars", "Data", "Components", "Dialogs",
                  "Reporting"]


class ComponentError(Exception):
    pass


# ============================================================================ locations
def user_components_dir(create: bool = True) -> Path:
    env = os.environ.get("RADIDE_COMPONENTS_DIR")
    d = Path(env) if env else Path(os.environ.get("APPDATA") or Path.home() / ".config") / "RADIDE" / "components"
    if create:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    return d


def project_components_dir(project_folder) -> Path:
    return Path(project_folder) / ".radide" / "components"


def dev_dirs() -> list[Path]:
    return [Path(p) for p in os.environ.get("RADIDE_COMPONENT_PATH", "").split(os.pathsep) if p.strip()]


# ============================================================================ package
@dataclass(eq=False)
class ComponentPackage:
    name: str
    version: str
    path: Path | None                 # package folder (None = made in code, e.g. mobile controls)
    manifest: dict
    source: str = "builtin"           # builtin | extension | user | project | dev
    origin: str = ""                  # extension id / project folder
    errors: list = field(default_factory=list)
    _modules: dict = field(default_factory=dict, repr=False)   # "designer"/"editors" -> (mtime, module)

    # ---------------------------------------------------------------- manifest data
    @property
    def builtin(self) -> bool:
        return self.source == "builtin"

    @property
    def display_name(self) -> str:
        return str(self.manifest.get("displayName") or self.name)

    @property
    def description(self) -> str:
        return str(self.manifest.get("description") or "")

    @property
    def category(self) -> str:
        return str(self.manifest.get("category") or "General")

    @property
    def publisher(self) -> str:
        return str(self.manifest.get("publisher") or "")

    @property
    def order(self) -> float:
        try:
            return float(self.manifest.get("order", 1000))
        except (TypeError, ValueError):
            return 1000.0

    def file(self, key: str) -> Path | None:
        rel = self.manifest.get(key)
        if not rel or self.path is None:
            return None
        p = self.path / str(rel)
        return p if p.is_file() else None

    @property
    def icon_path(self) -> Path | None:
        return self.file("icon")

    @property
    def help_path(self) -> Path | None:
        return self.file("help")

    @property
    def targets(self) -> dict:
        t = self.manifest.get("targets") or {}
        return t if isinstance(t, dict) else {}

    def runtime(self, target: str) -> dict | None:
        """The runtime entry for language plugin *target* ({"native": True} for built-ins), or None. Lookup
        (radide/components/targets.py): the id, its toolkit family, ``python`` for every Python toolkit,
        ``bridge``, the renderer's runtime (vb-basic and GUI Bridge languages -> python-tk), then ``*``."""
        from .targets import resolve
        r = resolve(self, target)
        return r.entry if r else None

    def supports(self, target: str) -> bool:
        return self.runtime(target) is not None

    def runtime_files(self, target: str) -> list[Path]:
        rt = self.runtime(target) or {}
        out = []
        for rel in ([rt["file"]] if rt.get("file") else []) + list(rt.get("files") or []):
            p = self.path / rel if self.path else None
            if p is not None and p.is_file():
                out.append(p)
        return out

    def summary(self) -> str:
        where = SOURCE_LABEL.get(self.source, self.source)
        if self.source == "extension" and self.origin:
            where += f" ({self.origin})"
        return f"{self.display_name} {self.version} - {where}"

    # ---------------------------------------------------------------- python parts (designer / editors)
    def module(self, key: str):
        """The package's designer.py / editors.py module (re-imported when the file changed), or None."""
        if self.builtin and key in self._modules:      # built-ins are not hot reloaded: no stat() per call
            return self._modules[key][1]
        path = self.file(key)
        if path is None:
            return None
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return None
        cached = self._modules.get(key)
        if cached and cached[0] == mtime:
            return cached[1]
        modname = f"radcomp_{_slug(self.name)}_{key}_{hashlib.md5(str(path).encode()).hexdigest()[:8]}"
        try:
            spec = importlib.util.spec_from_file_location(modname, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[modname] = mod
            spec.loader.exec_module(mod)
        except Exception:  # noqa: BLE001 - a broken package must not break the IDE
            self.errors.append(f"{path.name}: {traceback.format_exc(limit=3)}")
            self._modules[key] = (mtime, None)
            return None
        self._modules[key] = (mtime, mod)
        return mod

    def designer_module(self):
        return self.module("designer")

    def editors_module(self):
        return self.module("editors")

    def editor(self, editor_id: str):
        mod = self.editors_module()
        eds = getattr(mod, "EDITORS", None) if mod is not None else None
        return eds.get(editor_id) if isinstance(eds, dict) else None

    def watched_files(self) -> list[Path]:
        if self.path is None or self.builtin:
            return []
        try:
            return [p for p in self.path.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        except OSError:
            return []


def _slug(s: str) -> str:
    return re.sub(r"\W", "_", s).lower()


# ============================================================================ manifest -> ControlType
def _propdef(p: dict):
    from ..controls import DOCKS, PropDef
    raw = str(p.get("type") or "str")
    kind = proptypes.normalize(raw)
    choices = tuple(p.get("choices") or ())
    if not choices and p.get("choicesFrom"):
        choices = _choices_from(str(p["choicesFrom"]))
    if raw.lower() == "dock" and not choices:
        choices = DOCKS
    if kind == "alignment" and not choices:
        choices = proptypes.ALIGNMENTS
    default = p["default"] if "default" in p else proptypes.default_for(kind)
    meta = {k: v for k, v in p.items() if k not in ("name", "type", "default", "description", "category",
                                                    "choices", "editor")}
    return PropDef(str(p["name"]), kind, json.loads(json.dumps(default)), str(p.get("description") or ""),
                   choices, str(p.get("category") or "Misc"), str(p.get("editor") or ""), meta or None)


def _choices_from(spec: str) -> tuple:
    """``"radide.mobile.material_icons:icon_names"`` -> the values that function returns (a long or computed
    enum list a manifest does not repeat; only modules of the IDE itself)."""
    mod_name, _, fn_name = spec.partition(":")
    if not mod_name.startswith("radide.") or not fn_name:
        return ()
    try:
        import importlib
        return tuple(str(x) for x in getattr(importlib.import_module(mod_name), fn_name)())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return ()


# property names whose change makes the designer build a new preview widget (TextBox Multiline: QLineEdit ->
# QPlainTextEdit); a manifest property says "rebuildPreview": true (radide/document.py reads this set)
REBUILD_PROPS: set = set()


def control_type_of(pkg: ComponentPackage):
    """The ControlType of a package (manifest -> catalogue entry)."""
    from ..controls import ControlType
    m = pkg.manifest
    kind = m.get("kind", "visual")
    extra = [_propdef(p) for p in m.get("properties") or [] if isinstance(p, dict) and p.get("name")]
    REBUILD_PROPS.update(d.name for d in extra if d.meta and d.meta.get("rebuildPreview"))
    events = [str(e["name"]) for e in m.get("events") or [] if isinstance(e, dict) and e.get("name")]
    de = m.get("defaultEvent")
    if de:                                    # the default event comes first (double-click in the designer)
        if de in events:
            events.remove(de)
        events.insert(0, de)
    size = m.get("defaultSize") or ([0, 0] if kind == "nonvisual" else [100, 30])
    overrides = tuple((k, v) for k, v in (m.get("overrides") or {}).items())
    methods = tuple(dict(x) for x in m.get("methods") or [] if isinstance(x, dict) and x.get("name"))
    return ControlType(pkg.name, str(m.get("prefix") or pkg.name), (int(size[0]), int(size[1])), events, extra,
                       has_text=bool(m.get("hasText", True)), container=kind == "container",
                       nonvisual=kind == "nonvisual", common_events=bool(m.get("commonEvents", True)),
                       description=pkg.description, overrides=overrides, package=pkg,
                       category=pkg.category, methods=methods)


def _event_meta(pkg: ComponentPackage) -> None:
    from ..controls import EVENT_ARGS, EVENT_HELP
    for e in pkg.manifest.get("events") or []:
        if not isinstance(e, dict) or not e.get("name"):
            continue
        if e.get("description"):
            EVENT_HELP.setdefault(e["name"], e["description"])
        if e.get("args") in ("mouse", "key", "cancel"):
            EVENT_ARGS.setdefault(e["name"], e["args"])


def missing_type(name: str):
    """Placeholder ControlType for a control whose package is not installed (the form still opens; its
    properties are kept as they are)."""
    from ..controls import ControlType
    return ControlType(name, name, (100, 30), [], [], has_text=False, common_events=False,
                       description=f"Component package '{name}' is not installed: install it (Tools > Component "
                                   f"Packages) to edit and run this control. Its saved properties are kept.",
                       category=MISSING_CATEGORY)


def is_missing(type_name: str) -> bool:
    from ..controls import CONTROL_TYPES
    t = CONTROL_TYPES.get(type_name)
    return t is not None and t.category == MISSING_CATEGORY


# ============================================================================ reading packages
def read_package(folder, source: str = "user", origin: str = "") -> ComponentPackage:
    """Read and validate one package folder (errors are kept in ``pkg.errors``; a package whose manifest
    cannot be read raises ComponentError)."""
    folder = Path(folder)
    mp = folder / MANIFEST
    if not mp.is_file():
        raise ComponentError(f"{MANIFEST} not found in {folder}")
    try:
        data = json.loads(mp.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise ComponentError(f"{mp}: not valid JSON: {e}") from None
    errs = validate_manifest(data, folder, API_VERSION)
    if not isinstance(data, dict) or not isinstance(data.get("name"), str) or \
            not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", data.get("name", "")):
        raise ComponentError(f"{mp}: invalid manifest:\n- " + "\n- ".join(errs or ["'name' is required"]))
    return ComponentPackage(data["name"], str(data.get("version") or "0"), folder, data, source, origin, errs)


def _package_folders(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    if (root / MANIFEST).is_file():
        return [root]
    try:
        return [d for d in sorted(root.iterdir(), key=lambda p: p.name.lower())
                if d.is_dir() and (d / MANIFEST).is_file()]
    except OSError:
        return []


_BUILTIN: dict | None = None


def builtin_packages() -> dict[str, ComponentPackage]:
    global _BUILTIN
    if _BUILTIN is None:
        pkgs = []
        for d in _package_folders(BUILTIN_DIR):
            try:
                pkgs.append(read_package(d, "builtin"))
            except ComponentError as e:          # a broken built-in manifest: report, keep going
                print(f"[components] {e}", file=sys.stderr)
        pkgs.sort(key=lambda p: (p.order, p.name.lower()))
        _BUILTIN = {p.name: p for p in pkgs}
    return _BUILTIN


def builtin_control_types() -> dict:
    """The built-in desktop control types in Toolbox order (called by radide.controls while it is imported)."""
    out = {}
    for name, pkg in builtin_packages().items():
        if pkg.manifest.get("mobile"):
            continue
        out[name] = control_type_of(pkg)
        _event_meta(pkg)
    return out


def builtin_mobile_types() -> dict:
    """The built-in mobile control types (``"mobile": true`` packages: AppBar, BottomNav, ... - radide/mobile)
    in Toolbox order (called by radide.mobile.controls while it is imported)."""
    out = {}
    for name, pkg in builtin_packages().items():
        if pkg.manifest.get("mobile"):
            out[name] = control_type_of(pkg)
            _event_meta(pkg)
    return out


# ============================================================================ registry
class Registry:
    def __init__(self):
        self.packages: dict[str, ComponentPackage] = {}      # winners (non-built-in + built-in)
        self.shadowed: list[ComponentPackage] = []
        self.conflicts: list[str] = []
        self.broken: list[tuple[str, str]] = []             # (folder, error)
        self.project_folders: list[Path] = []
        self._registered: set[str] = set()                  # names this registry put into CONTROL_TYPES
        self._replaced: dict = {}                           # overridden built-in name -> original ControlType
        self._listeners: list = []
        self._lock = threading.RLock()
        self._stamp: dict = {}
        self.loaded = False

    # ---------------------------------------------------------------- listeners
    def on_change(self, fn) -> None:
        """fn() runs after packages were (re)loaded, installed or removed."""
        if fn not in self._listeners:
            self._listeners.append(fn)

    def _changed(self) -> None:
        for fn in list(self._listeners):
            try:
                fn()
            except Exception:  # noqa: BLE001
                traceback.print_exc()

    # ---------------------------------------------------------------- discovery
    def _candidates(self) -> list[ComponentPackage]:
        found: list[ComponentPackage] = []
        self.broken = []

        def scan(root: Path, source: str, origin: str = ""):
            for d in _package_folders(root):
                try:
                    found.append(read_package(d, source, origin))
                except ComponentError as e:
                    self.broken.append((str(d), str(e)))

        try:
            from .. import extensions as ext_mod
            for ext in ext_mod.installed():
                if not ext.enabled:
                    continue
                for item in (ext.contributes.get("components") or []):
                    if isinstance(item, dict) and item.get("folder"):
                        scan(ext.path / item["folder"], "extension", ext.id)
        except Exception as e:  # noqa: BLE001
            self.broken.append(("extensions", str(e)))
        scan(user_components_dir(), "user")
        for pf in self.project_folders:
            scan(project_components_dir(pf), "project", str(pf))
        for d in dev_dirs():
            scan(d, "dev")
        return found

    def discover(self) -> None:
        """Find every package again and update CONTROL_TYPES."""
        with self._lock:
            builtin = builtin_packages()
            winners: dict[str, ComponentPackage] = {}
            self.shadowed, self.conflicts = [], []
            for pkg in self._candidates():
                key = pkg.name
                if key in builtin and not pkg.manifest.get("overrideBuiltin"):
                    self.conflicts.append(f"{pkg.name} ({pkg.summary()}) ignored: a built-in control has that "
                                          f"name (set \"overrideBuiltin\": true to replace it)")
                    self.shadowed.append(pkg)
                    continue
                old = winners.get(key)
                if old is None:
                    winners[key] = pkg
                    continue
                better = (SOURCE_RANK[pkg.source], version_key(pkg.version)) > \
                         (SOURCE_RANK[old.source], version_key(old.version))
                win, lose = (pkg, old) if better else (old, pkg)
                winners[key] = win
                self.shadowed.append(lose)
                self.conflicts.append(f"{key}: using {win.summary()}, not {lose.summary()}")
            self.packages = dict(builtin)
            self.packages.update(winners)
            self.loaded = True
            self.apply()
            self._stamp = self._snapshot()
        self._changed()

    def ensure_loaded(self) -> None:
        if not self.loaded:
            self.discover()

    def set_project(self, folder) -> None:
        """The active project changed: its .radide/components are loaded (others' are dropped)."""
        folders = [Path(folder).resolve()] if folder else []
        if folders != self.project_folders or not self.loaded:
            self.project_folders = folders
            self.discover()

    def add_project(self, folder) -> None:
        f = Path(folder).resolve()
        if f not in self.project_folders:
            self.project_folders.append(f)
            self.discover()

    # ---------------------------------------------------------------- CONTROL_TYPES
    def apply(self) -> None:
        from .. import controls as C
        try:
            from ..usercontrols import USER_CONTROLS
        except ImportError:
            USER_CONTROLS = {}
        mobile = set()
        try:
            from ..mobile.controls import MOBILE_CONTROL_TYPES
            mobile = set(MOBILE_CONTROL_TYPES)
        except ImportError:
            pass
        builtin = builtin_packages()
        want = {n: p for n, p in self.packages.items() if not p.builtin}
        # drop what is no longer there (an open form keeps working with a "missing" placeholder)
        for name in list(self._registered):
            if name not in want:
                if name in self._replaced:
                    C.CONTROL_TYPES[name] = self._replaced.pop(name)
                else:
                    C.CONTROL_TYPES[name] = missing_type(name)
                self._registered.discard(name)
        for name, pkg in want.items():
            if name in USER_CONTROLS:
                self.conflicts.append(f"{name}: the project's user control of that name is used, not "
                                      f"{pkg.summary()}")
                continue
            if name in mobile and not pkg.manifest.get("overrideBuiltin"):
                self.conflicts.append(f"{name}: a mobile control has that name")
                continue
            if (name in builtin or name in mobile) and name not in self._replaced:
                self._replaced[name] = C.CONTROL_TYPES.get(name)
            try:
                C.CONTROL_TYPES[name] = control_type_of(pkg)
            except Exception as e:  # noqa: BLE001
                pkg.errors.append(f"cannot build the control type: {e}")
                continue
            _event_meta(pkg)
            self._registered.add(name)

    # ---------------------------------------------------------------- queries
    def get(self, name: str) -> ComponentPackage | None:
        self.ensure_loaded()
        return self.packages.get(name)

    def all(self, include_builtin: bool = True) -> list[ComponentPackage]:
        self.ensure_loaded()
        return [p for p in self.packages.values() if include_builtin or not p.builtin]

    # ---------------------------------------------------------------- hot reload
    def _snapshot(self) -> dict:
        stamp = {}
        roots = [user_components_dir(False), *dev_dirs(), *(project_components_dir(f) for f in self.project_folders)]
        for r in roots:
            try:
                stamp[str(r)] = tuple(sorted(p.name for p in r.iterdir())) if r.is_dir() else ()
            except OSError:
                pass
        for pkg in self.packages.values():
            for f in pkg.watched_files():
                try:
                    stamp[str(f)] = f.stat().st_mtime
                except OSError:
                    pass
        return stamp

    def reload_if_changed(self) -> bool:
        """Development: rediscover when a package file was added, changed or removed. True = reloaded."""
        if not self.loaded:
            return False
        if self._snapshot() == self._stamp:
            return False
        self.discover()
        return True

    def watch_paths(self) -> list[str]:
        """Folders and files a QFileSystemWatcher should watch for hot reload."""
        out = {str(user_components_dir(False))}
        out |= {str(d) for d in dev_dirs()} | {str(project_components_dir(f)) for f in self.project_folders}
        for pkg in self.packages.values():
            if pkg.path is not None and not pkg.builtin:
                out.add(str(pkg.path))
                out |= {str(f) for f in pkg.watched_files() if f.suffix in (".json", ".py", ".md", ".png", ".svg")}
        return sorted(p for p in out if Path(p).exists())


REGISTRY = Registry()


# ============================================================================ module-level helpers
def package_of(type_name: str) -> ComponentPackage | None:
    """The package of a control type (built-ins included), or None (mobile controls, user controls)."""
    from ..controls import CONTROL_TYPES
    t = CONTROL_TYPES.get(type_name)
    pkg = getattr(t, "package", None) if t is not None else None
    return pkg if isinstance(pkg, ComponentPackage) else None


def is_component_type(type_name: str) -> bool:
    """True for a control type that comes from a non-built-in component package."""
    pkg = package_of(type_name)
    return pkg is not None and not pkg.builtin


def help_file(type_name: str) -> str:
    pkg = package_of(type_name)
    p = pkg.help_path if pkg is not None and not pkg.builtin else None
    return str(p) if p else ""


def event_help(type_name: str, event: str) -> str:
    pkg = package_of(type_name)
    if pkg is not None:
        for e in pkg.manifest.get("events") or []:
            if isinstance(e, dict) and e.get("name") == event and e.get("description"):
                return str(e["description"])
    return ""


def ensure_types(d: dict, folder) -> None:
    """Called by Form.load: unknown control types -> load the folder's project components, and placeholders
    for the ones still unknown (the package is not installed)."""
    from ..controls import CONTROL_TYPES
    try:
        types = {c.get("type") for c in d.get("controls", []) if isinstance(c, dict)}
    except AttributeError:
        return
    unknown = {t for t in types if isinstance(t, str) and t not in CONTROL_TYPES}
    if not unknown:
        return
    REGISTRY.ensure_loaded()
    if folder is not None and project_components_dir(folder).is_dir():
        REGISTRY.add_project(folder)
    for t in unknown:
        if t not in CONTROL_TYPES and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
            try:                                     # a user control of the folder is registered later
                from ..usercontrols import USER_CONTROLS
                if t in USER_CONTROLS:
                    continue
            except ImportError:
                pass
            if folder is not None and (Path(folder) / f"{t}.form").is_file():
                continue
            CONTROL_TYPES[t] = missing_type(t)


def used_packages(forms) -> list[ComponentPackage]:
    out, seen = [], set()
    for f in forms:
        for c in getattr(f, "controls", []):
            if c.type in seen:
                continue
            seen.add(c.type)
            pkg = package_of(c.type)
            if pkg is not None and not pkg.builtin:
                out.append(pkg)
    return out


def copy_runtimes(project_folder, forms, target_of) -> list[str]:
    """Copy the runtime files of the packages the *forms* use into the project folder (when missing or
    changed). *target_of(form)* gives the form's language plugin id. Returns the copied file names."""
    copied = []
    folder = Path(project_folder)
    for f in forms:
        target = target_of(f)
        for pkg in used_packages([f]):
            for src in pkg.runtime_files(target):
                rel = src.relative_to(pkg.path / Path((pkg.runtime(target) or {}).get("file", "x")).parent) \
                    if src.is_relative_to(pkg.path / Path((pkg.runtime(target) or {}).get("file", "x")).parent) \
                    else Path(src.name)
                dst = folder / rel
                try:
                    if dst.is_file() and dst.read_bytes() == src.read_bytes():
                        continue
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
                    copied.append(str(rel))
                except OSError:
                    pass
    return copied


# ============================================================================ install / export
def _extract(source: Path, tmp: Path) -> Path:
    if source.is_dir():
        return source
    if not zipfile.is_zipfile(source):
        raise ComponentError(f"not a component package (.radcomp / .zip): {source}")
    root = tmp.resolve()
    with zipfile.ZipFile(source) as z:
        total = 0
        for info in z.infolist():
            target = (root / info.filename).resolve()
            if root not in target.parents and target != root:
                raise ComponentError(f"unsafe path in the package: {info.filename}")
            total += info.file_size
            if total > 100 * 1024 * 1024:
                raise ComponentError("the package is too large (more than 100 MB unpacked)")
        z.extractall(root)
    if (root / MANIFEST).is_file():
        return root
    subs = [d for d in root.iterdir() if d.is_dir() and (d / MANIFEST).is_file()]
    if len(subs) == 1:
        return subs[0]
    raise ComponentError(f"no {MANIFEST} in the package")


def install_package(source, scope: str = "user", project_folder=None, allow_downgrade: bool = False,
                    reload: bool = True) -> ComponentPackage:
    """Install a package (.radcomp / .zip / folder) for the user (``scope="user"``) or into a project
    (``scope="project"``: ``<project>/.radide/components``). Raises ComponentError (invalid manifest, a
    newer version already installed, a built-in name)."""
    source = Path(source)
    with tempfile.TemporaryDirectory(prefix="radcomp_") as tmp:
        root = _extract(source, Path(tmp))
        pkg = read_package(root, scope)
        if pkg.errors:
            raise ComponentError("invalid component package:\n- " + "\n- ".join(pkg.errors))
        if pkg.name in builtin_packages() and not pkg.manifest.get("overrideBuiltin"):
            raise ComponentError(f"'{pkg.name}' is the name of a built-in control")
        if scope == "project":
            if project_folder is None:
                raise ComponentError("open a project first")
            base = project_components_dir(project_folder)
        else:
            base = user_components_dir()
        dest = base / pkg.name
        if (dest / MANIFEST).is_file():
            try:
                old = read_package(dest, scope)
                if version_key(old.version) > version_key(pkg.version) and not allow_downgrade:
                    raise ComponentError(f"{pkg.name} {old.version} is already installed (newer than "
                                         f"{pkg.version})")
            except ComponentError as e:
                if "already installed" in str(e):
                    raise
            shutil.rmtree(dest, ignore_errors=True)
        base.mkdir(parents=True, exist_ok=True)
        shutil.copytree(root, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
    if scope == "project" and project_folder is not None:
        f = Path(project_folder).resolve()
        if f not in REGISTRY.project_folders:
            REGISTRY.project_folders.append(f)
    if reload:
        REGISTRY.discover()
    return read_package(dest, scope)


def uninstall_package(name: str, scope: str = "user", project_folder=None, reload: bool = True) -> None:
    base = project_components_dir(project_folder) if scope == "project" else user_components_dir()
    dest = base / name
    if not (dest / MANIFEST).is_file():
        raise ComponentError(f"{name} is not installed ({scope})")
    shutil.rmtree(dest, ignore_errors=False)
    if reload:
        REGISTRY.discover()


def export_package(folder, dest_file) -> Path:
    """Zip a package folder into a .radcomp file (validated first)."""
    folder = Path(folder)
    pkg = read_package(folder, "dev")
    if pkg.errors:
        raise ComponentError("fix the manifest first:\n- " + "\n- ".join(pkg.errors))
    dest = Path(dest_file)
    if dest.suffix.lower() not in (PACKAGE_EXT, ".zip"):
        dest = dest.with_suffix(PACKAGE_EXT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc" and ".git" not in p.parts:
                z.write(p, p.relative_to(folder).as_posix())
    return dest


def new_package(folder, name: str, category: str = "Custom", targets=("python-tk", "python-qt")) -> Path:
    """Create a minimal package skeleton (component.json, runtimes, help.md) to start from."""
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ComponentError(f"'{name}' is not a valid control name")
    d = Path(folder) / name
    if d.exists():
        raise ComponentError(f"{d} already exists")
    (d / "runtime").mkdir(parents=True)
    mod = _slug(name)
    m = {"schemaVersion": SCHEMA_VERSION, "name": name, "version": "1.0.0", "description": f"The {name} control.",
         "category": category, "defaultSize": [120, 30], "kind": "visual", "hasText": True,
         "properties": [{"name": "Value", "type": "int", "default": 0, "category": "Behavior",
                         "description": "The current value."}],
         "events": [{"name": "ValueChanged", "description": "The Value property changed."}],
         "methods": [], "targets": {}, "help": "help.md"}
    if "python-tk" in targets:
        m["targets"]["python-tk"] = {"file": f"runtime/{mod}_tk.py", "class": name}
        (d / "runtime" / f"{mod}_tk.py").write_text(_TK_SKELETON.replace("{Name}", name), encoding="utf-8")
    if "python-qt" in targets:
        m["targets"]["python-qt"] = {"file": f"runtime/{mod}_qt.py", "class": name}
        (d / "runtime" / f"{mod}_qt.py").write_text(_QT_SKELETON.replace("{Name}", name), encoding="utf-8")
    (d / MANIFEST).write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    (d / "help.md").write_text(f"# {name}\n\nDescribe the control, its properties and events here.\n",
                               encoding="utf-8")
    return d


_TK_SKELETON = '''"""{Name} - python-tk runtime (component package)."""
import tkinter as tk


class {Name}(tk.Label):
    def __init__(self, master, Value=0, Text="", **props):
        super().__init__(master, text=Text or "{Name}")
        self._handlers = {}
        self._value = Value

    def rad_bind(self, event, callback):
        self._handlers[event] = callback

    def _raise(self, event, *args):
        fn = self._handlers.get(event)
        if fn is not None:
            fn(*args)

    @property
    def Value(self):
        return self._value

    @Value.setter
    def Value(self, v):
        self._value = v
        self._raise("ValueChanged")
'''

_QT_SKELETON = '''"""{Name} - python-qt (PySide6) runtime (component package)."""
from PySide6.QtWidgets import QLabel


class {Name}(QLabel):
    def __init__(self, parent=None, Value=0, Text="", **props):
        super().__init__(Text or "{Name}", parent)
        self._handlers = {}
        self._value = Value

    def rad_bind(self, event, callback):
        self._handlers[event] = callback

    def _raise(self, event, *args):
        fn = self._handlers.get(event)
        if fn is not None:
            fn(*args)

    @property
    def Value(self):
        return self._value

    @Value.setter
    def Value(self, v):
        self._value = v
        self._raise("ValueChanged")
'''


__all__ = ["MANIFEST", "PACKAGE_EXT", "API_VERSION", "SCHEMA", "SCHEMA_VERSION", "SOURCES", "CATEGORY_ORDER",
           "ComponentError", "ComponentPackage", "Registry", "REGISTRY", "read_package", "builtin_packages",
           "builtin_control_types", "builtin_mobile_types", "REBUILD_PROPS", "control_type_of", "missing_type", "is_missing", "package_of",
           "is_component_type", "help_file", "event_help", "ensure_types", "used_packages", "copy_runtimes",
           "install_package", "uninstall_package", "export_package", "new_package", "user_components_dir",
           "project_components_dir", "dev_dirs", "validate_manifest", "version_key"]
